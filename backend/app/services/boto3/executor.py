"""
Boto3 Executor — provisions and destroys AWS resources via the Python SDK.

Replaces the old TerraformExecutor. Instead of running terraform CLI commands,
this executor directly calls boto3 APIs to create/delete resources.
"""

import asyncio
import json
import logging
from typing import Any, AsyncIterator, Callable

import boto3
from botocore.exceptions import ClientError, BotoCoreError

logger = logging.getLogger(__name__)


class Boto3Executor:
    """
    Executes boto3 API calls to provision and destroy AWS resources.

    Each resource is defined by a config dict:
    {
        "service": "ec2",
        "action": "run_instances",
        "params": {...},
        "delete_action": "terminate_instances",
        "delete_params_key": "InstanceIds",
        "resource_id_path": "Instances[0].InstanceId",
        "waiter": "instance_running",          # optional
        "delete_waiter": "instance_terminated", # optional
    }
    """

    def __init__(
        self,
        aws_access_key_id: str,
        aws_secret_access_key: str,
        region_name: str = "us-east-1",
        project_name: str = "",
    ) -> None:
        self.aws_access_key_id = aws_access_key_id
        self.aws_secret_access_key = aws_secret_access_key
        self.region_name = region_name
        self.project_name = project_name
        self._clients: dict[str, Any] = {}

    def _get_client(self, service: str) -> Any:
        """Get or create a boto3 client for the given service."""
        if service not in self._clients:
            self._clients[service] = boto3.client(
                service,
                aws_access_key_id=self.aws_access_key_id,
                aws_secret_access_key=self.aws_secret_access_key,
                region_name=self.region_name,
            )
        return self._clients[service]

    @staticmethod
    def _extract_resource_id(response: dict, path: str) -> str | None:
        """
        Extract a resource ID from a boto3 response using a dot/bracket path.

        Examples:
            "Instances[0].InstanceId" → response["Instances"][0]["InstanceId"]
            "DBInstance.DBInstanceIdentifier" → response["DBInstance"]["DBInstanceIdentifier"]
        """
        import re
        current = response
        for part in re.split(r'\.', path):
            bracket = re.match(r'(\w+)\[(\d+)\]', part)
            if bracket:
                key, idx = bracket.group(1), int(bracket.group(2))
                current = current[key][idx]
            else:
                current = current[part]
        return str(current) if current is not None else None

    @staticmethod
    def flatten_configs(configs: dict[str, Any] | list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Normalize configs to a flat list.

        Accepts either:
          - A flat list of config dicts (already normalized)
          - A nested dict of service → list of ops: {"ec2": [{...}], "s3": [{...}]}

        Returns a flat list where each dict has a 'service' key.
        """
        if isinstance(configs, list):
            return configs

        flat: list[dict[str, Any]] = []
        for service, ops in configs.items():
            if service.startswith("_"):
                continue  # skip _unsupported etc.
            if isinstance(ops, list):
                for op in ops:
                    entry = {"service": service, **op}
                    flat.append(entry)
            elif isinstance(ops, dict):
                flat.append({"service": service, **ops})
        return flat

    async def _get_account_id(self) -> str:
        """Fetch the AWS account ID via STS."""
        try:
            sts = self._get_client("sts")
            resp = await asyncio.to_thread(sts.get_caller_identity)
            return resp["Account"]
        except Exception:
            return "UNKNOWN"

    @staticmethod
    def _replace_placeholders(obj: Any, replacements: dict[str, str]) -> None:
        """Recursively replace placeholder strings in-place."""
        if isinstance(obj, dict):
            for k, v in obj.items():
                if isinstance(v, str):
                    for ph, val in replacements.items():
                        v = v.replace(ph, val)
                    obj[k] = v
                elif isinstance(v, (dict, list)):
                    Boto3Executor._replace_placeholders(v, replacements)
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                if isinstance(item, str):
                    for ph, val in replacements.items():
                        item = item.replace(ph, val)
                    obj[i] = item
                elif isinstance(item, (dict, list)):
                    Boto3Executor._replace_placeholders(item, replacements)

    @staticmethod
    def _sanitize_s3_name(name: str) -> str:
        """Return a valid S3 bucket name (lowercase, alphanumeric/hyphens, 3-63 chars)."""
        import re
        name = name.lower()
        name = re.sub(r"[^a-z0-9\-]", "-", name)      # replace invalid chars with -
        name = re.sub(r"-{2,}", "-", name).strip("-")   # collapse multiple hyphens
        return name[:63] if len(name) >= 3 else name + "bucket"

    async def deploy(
        self,
        configs: list[dict[str, Any]],
        log_callback: Callable[[str], None] | None = None,
        project_name: str = "",
    ) -> list[dict[str, Any]]:
        """
        Deploy resources by executing boto3 API calls.

        Args:
            configs: List of boto3 config dicts (from tool results).
            log_callback: Optional callback for streaming log lines.
            project_name: Project name for tagging.

        Returns:
            List of deployed resource records with IDs/ARNs.
        """
        deployed: list[dict[str, Any]] = []

        def _log(msg: str) -> None:
            if log_callback:
                log_callback(msg)
            logger.info(msg)

        # Resolve AWS account ID from STS and replace placeholder literals in all configs
        import copy
        configs = copy.deepcopy(configs)
        account_id = await self._get_account_id()
        account_placeholders = {
            "<account-id>": account_id,
            "{account_id}": account_id,
            "__ACCOUNT_ID__": account_id,
        }
        self._replace_placeholders(configs, account_placeholders)

        _log(f"Starting deployment of {len(configs)} resource(s)...\n")

        last_resource_id: str | None = None   # tracks the most recently created resource ID

        for i, cfg in enumerate(configs, 1):
            # Resolve the __RESOLVE_PREV__ placeholder with the last successfully created resource ID
            if last_resource_id and "__RESOLVE_PREV__" in json.dumps(cfg):
                self._replace_placeholders(cfg, {"__RESOLVE_PREV__": last_resource_id})

            # Sanitize S3 bucket names — bucket names may not contain underscores or be > 63 chars
            if cfg.get("service") == "s3" and cfg.get("action") == "create_bucket":
                params = cfg.get("params", {})
                if "Bucket" in params:
                    params["Bucket"] = self._sanitize_s3_name(params["Bucket"])
                    cfg["params"] = params

            service = cfg.get("service", "unknown")
            action = cfg.get("action", "unknown")
            label = cfg.get("label", f"{service}.{action}")
            _log(f"[{i}/{len(configs)}] Creating {label} via {service}.{action}...\n")

            try:
                result = await self._execute_call(cfg)
                resource_id = None

                if cfg.get("resource_id_path") and result:
                    try:
                        resource_id = self._extract_resource_id(result, cfg["resource_id_path"])
                    except (KeyError, IndexError, TypeError) as e:
                        logger.warning("Could not extract resource ID: %s", e)

                record = {
                    "service": service,
                    "action": action,
                    "label": label,
                    "resource_id": resource_id,
                    "resource_type": cfg.get("resource_type", service),
                    "delete_action": cfg.get("delete_action"),
                    "delete_params_key": cfg.get("delete_params_key"),
                    "delete_params": cfg.get("delete_params"),
                    "status": "created",
                    "response_summary": self._summarize_response(result),
                }
                deployed.append(record)
                _log(f"  ✓ Created {label} (ID: {resource_id or 'N/A'})\n")

                # Update last_resource_id for __RESOLVE_PREV__ in subsequent configs
                if resource_id:
                    last_resource_id = resource_id

                # IAM role/policy propagation: AWS takes ~10 s to make a new role usable
                if service == "iam" and action in ("create_role", "attach_role_policy", "put_role_policy"):
                    _log(f"  ⏳ Waiting 10 s for IAM changes to propagate...\n")
                    await asyncio.sleep(10)

                # Wait for resource if waiter is specified
                if cfg.get("waiter"):
                    _log(f"  ⏳ Waiting for {label} to be ready...\n")
                    try:
                        await self._wait_for(service, cfg["waiter"], cfg.get("waiter_params", {}))
                        _log(f"  ✓ {label} is ready.\n")
                    except Exception as we:
                        _log(f"  ⚠ Waiter warning: {we}\n")

            except ClientError as e:
                error_code = e.response["Error"]["Code"]
                error_msg = e.response["Error"]["Message"]
                _log(f"  ✗ FAILED: [{error_code}] {error_msg}\n")
                deployed.append({
                    "service": service,
                    "action": action,
                    "label": label,
                    "status": "failed",
                    "error_code": error_code,
                    "error_message": error_msg,
                })
            except (BotoCoreError, Exception) as e:
                _log(f"  ✗ FAILED: {str(e)}\n")
                deployed.append({
                    "service": service,
                    "action": action,
                    "label": label,
                    "status": "failed",
                    "error_message": str(e),
                })

        succeeded = sum(1 for r in deployed if r["status"] == "created")
        _log(f"\nDeployment complete: {succeeded}/{len(configs)} resources created.\n")

        return deployed

    async def destroy(
        self,
        resource_records: list[dict[str, Any]],
        log_callback: Callable[[str], None] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Destroy resources by calling their delete actions.
        Processes in reverse order (last created → first deleted).
        """
        results: list[dict[str, Any]] = []

        def _log(msg: str) -> None:
            if log_callback:
                log_callback(msg)
            logger.info(msg)

        # Reverse order for proper dependency teardown
        records = list(reversed(resource_records))
        _log(f"Starting destruction of {len(records)} resource(s)...\n")

        for i, record in enumerate(records, 1):
            label = record.get("label", "unknown")
            delete_action = record.get("delete_action")
            resource_id = record.get("resource_id")

            if not delete_action:
                _log(f"[{i}/{len(records)}] Skipping {label} — no delete action configured.\n")
                results.append({**record, "destroy_status": "skipped"})
                continue

            _log(f"[{i}/{len(records)}] Destroying {label}...\n")

            try:
                service = record.get("service", "unknown")
                client = self._get_client(service)

                # Build delete params
                # Use `or {}` rather than a default to handle explicit null stored in JSON
                delete_params = record.get("delete_params") or {}
                if record.get("delete_params_key") and resource_id:
                    delete_params[record["delete_params_key"]] = (
                        [resource_id] if record["delete_params_key"].endswith("s")
                        or record["delete_params_key"].endswith("Ids")
                        else resource_id
                    )

                # Special pre-delete cleanup
                await self._pre_delete_cleanup(service, record, client, _log)

                # Execute delete
                fn = getattr(client, delete_action)
                await asyncio.to_thread(fn, **delete_params)
                _log(f"  ✓ Destroyed {label}\n")
                results.append({**record, "destroy_status": "destroyed"})

            except ClientError as e:
                error_msg = e.response["Error"]["Message"]
                _log(f"  ✗ FAILED: {error_msg}\n")
                results.append({**record, "destroy_status": "failed", "destroy_error": error_msg})
            except Exception as e:
                _log(f"  ✗ FAILED: {str(e)}\n")
                results.append({**record, "destroy_status": "failed", "destroy_error": str(e)})

        succeeded = sum(1 for r in results if r.get("destroy_status") == "destroyed")
        _log(f"\nDestruction complete: {succeeded}/{len(records)} resources destroyed.\n")

        return results

    async def destroy_single(
        self, resource_record: dict[str, Any]
    ) -> tuple[bool, str]:
        """Destroy a single resource. Returns (success, message)."""
        results = await self.destroy([resource_record])
        if results and results[0].get("destroy_status") == "destroyed":
            return True, f"Successfully destroyed {resource_record.get('label', 'resource')}"
        error = results[0].get("destroy_error", "Unknown error") if results else "No result"
        return False, f"Failed to destroy: {error}"

    async def _execute_call(self, cfg: dict[str, Any]) -> dict:
        """Execute a single boto3 API call in a thread."""
        service = cfg["service"]
        action = cfg["action"]
        params = cfg.get("params", {})

        client = self._get_client(service)
        fn = getattr(client, action)
        result = await asyncio.to_thread(fn, **params)
        return result

    async def _wait_for(
        self, service: str, waiter_name: str, params: dict
    ) -> None:
        """Wait for a resource using a boto3 waiter."""
        client = self._get_client(service)
        waiter = client.get_waiter(waiter_name)
        await asyncio.to_thread(
            waiter.wait,
            **params,
            WaiterConfig={"Delay": 10, "MaxAttempts": 60},
        )

    async def _pre_delete_cleanup(
        self,
        service: str,
        record: dict[str, Any],
        client: Any,
        _log: Callable,
    ) -> None:
        """Service-specific pre-delete cleanup (e.g., empty S3 buckets)."""
        resource_id = record.get("resource_id", "")

        if service == "s3" and record.get("delete_action") == "delete_bucket":
            _log(f"  🗑 Emptying S3 bucket {resource_id}...\n")
            try:
                s3 = boto3.resource(
                    "s3",
                    aws_access_key_id=self.aws_access_key_id,
                    aws_secret_access_key=self.aws_secret_access_key,
                    region_name=self.region_name,
                )
                bucket = s3.Bucket(resource_id)
                await asyncio.to_thread(bucket.objects.all().delete)
                await asyncio.to_thread(bucket.object_versions.all().delete)
            except Exception as e:
                _log(f"  ⚠ Bucket cleanup warning: {e}\n")

    @staticmethod
    def _summarize_response(response: dict | None) -> dict:
        """Create a slim summary of a boto3 response (remove metadata)."""
        if not response:
            return {}
        try:
            summary = {k: v for k, v in response.items() if k != "ResponseMetadata"}
            text = json.dumps(summary, default=str)
            if len(text) > 5000:
                text = text[:5000]
            return json.loads(text) if text.startswith("{") else {"raw": text}
        except Exception:
            return {}
