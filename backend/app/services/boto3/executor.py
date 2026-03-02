"""
Boto3 Executor â€” provisions and destroys AWS resources via the Python SDK.

Replaces the old TerraformExecutor. Instead of running terraform CLI commands,
this executor directly calls boto3 APIs to create/delete resources.
"""

import asyncio
import json
import logging
import pathlib
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

    # Valid AWS-managed Config rule sourceIdentifiers - loaded from aws_config_rules.md.
    # To add/remove rules, edit that file (one "- RULE_NAME" bullet per line).
    VALID_CONFIG_RULE_IDS: frozenset[str] = frozenset(
        line.strip()[2:].strip()  # strip the leading "- "
        for line in (pathlib.Path(__file__).parent / "aws_config_rules.md").read_text(encoding="utf-8").splitlines()
        if line.strip().startswith("- ")
    )

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
        self._rds_subnet_group_cache: str | None = None  # cached so we don't recreate it per-call
        self._default_subnets_cache: list[str] | None = None  # default VPC subnet IDs
        self._default_sg_cache: list[str] | None = None       # default VPC security group IDs

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
            "Instances[0].InstanceId" â†’ response["Instances"][0]["InstanceId"]
            "DBInstance.DBInstanceIdentifier" â†’ response["DBInstance"]["DBInstanceIdentifier"]
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
          - A nested dict of service â†’ list of ops: {"ec2": [{...}], "s3": [{...}]}

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

    async def _ensure_rds_networking(
        self,
        project_name: str,
        _log: Callable,
    ) -> str:
        """
        Ensure a DB subnet group (â‰¥2 subnets in different AZs) exists and return its name.

        Steps:
          1. Return cached name if already done this deployment.
          2. Return existing RDS subnet group if one with our name already exists in AWS.
          3. Find/restore/create a VPC.
          4. Ensure â‰¥2 subnets exist across different AZs (create them if needed).
          5. Create the DB subnet group.
        """
        import re as _re

        if self._rds_subnet_group_cache:
            return self._rds_subnet_group_cache

        raw = f"{project_name}-db-subnet-grp" if project_name else "infra-agent-db-subnet-grp"
        sg_name = _re.sub(r"[^a-z0-9\-]", "-", raw.lower())[:255].strip("-")

        ec2 = self._get_client("ec2")
        rds = self._get_client("rds")

        # â”€â”€ 1. Reuse existing subnet group â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        try:
            resp = await asyncio.to_thread(
                rds.describe_db_subnet_groups, DBSubnetGroupName=sg_name
            )
            if resp.get("DBSubnetGroups"):
                _log(f"  â„¹ DB subnet group '{sg_name}' already exists â€” reusing.\n")
                self._rds_subnet_group_cache = sg_name
                return sg_name
        except Exception:
            pass

        # â”€â”€ 2. Find default VPC â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        vpc_id: str | None = None
        try:
            vpcs = await asyncio.to_thread(
                ec2.describe_vpcs,
                Filters=[{"Name": "isDefault", "Values": ["true"]}],
            )
            if vpcs["Vpcs"]:
                vpc_id = vpcs["Vpcs"][0]["VpcId"]
                _log(f"  â„¹ Using default VPC {vpc_id}\n")
        except Exception as e:
            _log(f"  âš  Could not query VPCs: {e}\n")

        # â”€â”€ 3. Restore or create VPC â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        if not vpc_id:
            _log("  ðŸ”§ No default VPC found â€” attempting to restore default VPC...\n")
            try:
                result = await asyncio.to_thread(ec2.create_default_vpc)
                vpc_id = result["Vpc"]["VpcId"]
                _log(f"  âœ“ Default VPC restored: {vpc_id}\n")
            except Exception as e:
                _log(f"  âš  Could not restore default VPC ({e}) â€” creating custom VPC...\n")

        if not vpc_id:
            vpc_resp = await asyncio.to_thread(ec2.create_vpc, CidrBlock="10.42.0.0/16")
            vpc_id = vpc_resp["Vpc"]["VpcId"]
            for attr, val in [("EnableDnsHostnames", True), ("EnableDnsSupport", True)]:
                await asyncio.to_thread(
                    ec2.modify_vpc_attribute, VpcId=vpc_id, **{attr: {"Value": val}}
                )
            await asyncio.to_thread(
                ec2.create_tags,
                Resources=[vpc_id],
                Tags=[
                    {"Key": "Name", "Value": f"{project_name}-vpc"},
                    {"Key": "CreatedBy", "Value": "infra-agent"},
                ],
            )
            _log(f"  âœ“ Created custom VPC {vpc_id} (10.42.0.0/16)\n")

        # â”€â”€ 4. Ensure â‰¥2 subnets in different AZs â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        subnets_resp = await asyncio.to_thread(
            ec2.describe_subnets,
            Filters=[{"Name": "vpc-id", "Values": [vpc_id]}],
        )
        existing = subnets_resp.get("Subnets", [])
        covered_azs: set[str] = {s["AvailabilityZone"] for s in existing}
        subnet_ids: list[str] = [s["SubnetId"] for s in existing]

        azs_resp = await asyncio.to_thread(
            ec2.describe_availability_zones,
            Filters=[{"Name": "state", "Values": ["available"]}],
        )
        all_azs = [az["ZoneName"] for az in azs_resp["AvailabilityZones"]]

        spare_cidrs = ["10.42.1.0/24", "10.42.2.0/24", "10.42.3.0/24", "10.42.4.0/24"]
        cidr_idx = 0

        for az in all_azs:
            if len(covered_azs) >= 2 and len(subnet_ids) >= 2:
                break
            if az in covered_azs:
                continue
            if cidr_idx >= len(spare_cidrs):
                break
            try:
                sub_resp = await asyncio.to_thread(
                    ec2.create_default_subnet, AvailabilityZone=az
                )
                sub_id = sub_resp["Subnet"]["SubnetId"]
            except Exception:
                sub_resp = await asyncio.to_thread(
                    ec2.create_subnet,
                    VpcId=vpc_id,
                    CidrBlock=spare_cidrs[cidr_idx],
                    AvailabilityZone=az,
                )
                sub_id = sub_resp["Subnet"]["SubnetId"]
                cidr_idx += 1
            subnet_ids.append(sub_id)
            covered_azs.add(az)
            _log(f"  âœ“ Created subnet {sub_id} in {az}\n")

        if len(subnet_ids) < 2:
            raise RuntimeError(
                f"Could not obtain â‰¥2 subnets in different AZs (found {len(subnet_ids)})"
            )

        # â”€â”€ 5. Create DB subnet group â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        _log(f"  ðŸ”§ Creating DB subnet group '{sg_name}'...\n")
        await asyncio.to_thread(
            rds.create_db_subnet_group,
            DBSubnetGroupName=sg_name,
            DBSubnetGroupDescription=f"Auto-created by Infra-Agent for {project_name}",
            SubnetIds=subnet_ids[:6],
            Tags=[{"Key": "CreatedBy", "Value": "infra-agent"}],
        )
        _log(f"  âœ“ DB subnet group '{sg_name}' ready\n")
        self._rds_subnet_group_cache = sg_name
        return sg_name

    async def _get_default_vpc_subnet_ids(self, _log: Callable) -> list[str]:
        """Return subnet IDs from the default VPC (result cached per executor instance)."""
        if self._default_subnets_cache is not None:
            return self._default_subnets_cache
        ec2 = self._get_client("ec2")
        try:
            vpcs = await asyncio.to_thread(
                ec2.describe_vpcs,
                Filters=[{"Name": "isDefault", "Values": ["true"]}],
            )
            if not vpcs["Vpcs"]:
                self._default_subnets_cache = []
                return []
            vpc_id = vpcs["Vpcs"][0]["VpcId"]
            subnets = await asyncio.to_thread(
                ec2.describe_subnets,
                Filters=[{"Name": "vpc-id", "Values": [vpc_id]}],
            )
            ids = [s["SubnetId"] for s in subnets.get("Subnets", [])]
            self._default_subnets_cache = ids
            _log(f"  \u2139 Resolved default VPC subnets: {ids}\n")
        except Exception as e:
            _log(f"  \u26a0 Could not fetch default VPC subnets: {e}\n")
            self._default_subnets_cache = []
        return self._default_subnets_cache

    async def _get_default_security_group_ids(self, _log: Callable) -> list[str]:
        """Return the default security group ID(s) for the default VPC (cached)."""
        if self._default_sg_cache is not None:
            return self._default_sg_cache
        ec2 = self._get_client("ec2")
        try:
            vpcs = await asyncio.to_thread(
                ec2.describe_vpcs,
                Filters=[{"Name": "isDefault", "Values": ["true"]}],
            )
            if not vpcs["Vpcs"]:
                self._default_sg_cache = []
                return []
            vpc_id = vpcs["Vpcs"][0]["VpcId"]
            sgs = await asyncio.to_thread(
                ec2.describe_security_groups,
                Filters=[
                    {"Name": "vpc-id", "Values": [vpc_id]},
                    {"Name": "group-name", "Values": ["default"]},
                ],
            )
            ids = [sg["GroupId"] for sg in sgs.get("SecurityGroups", [])]
            self._default_sg_cache = ids
            _log(f"  \u2139 Resolved default security groups: {ids}\n")
        except Exception as e:
            _log(f"  \u26a0 Could not fetch default security groups: {e}\n")
            self._default_sg_cache = []
        return self._default_sg_cache

    @staticmethod
    def _resolve_network_placeholders(obj: Any, subnet_ids: list[str], sg_ids: list[str]) -> None:
        """
        Recursively walk a params dict and replace network placeholder strings:
        - A string value matching a subnet placeholder becomes the list of subnet IDs.
        - A string value matching a SG placeholder becomes the list of SG IDs.
        - List elements that are placeholder strings are expanded in-place.
        """
        _SUBNET_PH = {"__DEFAULT_SUBNETS__", "__DEFAULT_SUBNET_IDS__", "__SUBNETS__", "__VPC_SUBNETS__"}
        _SG_PH = {"__DEFAULT_SECURITY_GROUPS__", "__DEFAULT_SG__", "__SECURITY_GROUPS__", "__SG_IDS__"}

        if isinstance(obj, dict):
            for k, v in list(obj.items()):
                if isinstance(v, str):
                    if v in _SUBNET_PH:
                        obj[k] = subnet_ids
                    elif v in _SG_PH:
                        obj[k] = sg_ids
                elif isinstance(v, list):
                    new_list: list = []
                    for item in v:
                        if isinstance(item, str) and item in _SUBNET_PH:
                            new_list.extend(subnet_ids)
                        elif isinstance(item, str) and item in _SG_PH:
                            new_list.extend(sg_ids)
                        else:
                            Boto3Executor._resolve_network_placeholders(item, subnet_ids, sg_ids)
                            new_list.append(item)
                    obj[k] = new_list
                elif isinstance(v, dict):
                    Boto3Executor._resolve_network_placeholders(v, subnet_ids, sg_ids)
        elif isinstance(obj, list):
            for item in obj:
                if isinstance(item, (dict, list)):
                    Boto3Executor._resolve_network_placeholders(item, subnet_ids, sg_ids)

    @staticmethod
    def _sanitize_s3_name(name: str) -> str:
        """Return a valid S3 bucket name (lowercase, alphanumeric/hyphens, 3-63 chars)."""
        import re
        name = name.lower()
        name = re.sub(r"[^a-z0-9\-]", "-", name)      # replace invalid chars with -
        name = re.sub(r"-{2,}", "-", name).strip("-")   # collapse multiple hyphens
        return name[:63] if len(name) >= 3 else name + "bucket"

    @staticmethod
    def _sanitize_apprunner_name(name: str) -> str:
        """Return a valid App Runner service name: [A-Za-z0-9][A-Za-z0-9-_]{3,39}, max 40 chars."""
        import re
        name = re.sub(r"[^A-Za-z0-9\-_]", "-", name)   # replace invalid chars
        name = re.sub(r"-{2,}", "-", name).strip("-")
        if not name or not name[0].isalnum():
            name = "svc-" + name
        return name[:40]

    @staticmethod
    def _sanitize_cfn_stack_name(name: str) -> str:
        """Return a valid CloudFormation stack name: [a-zA-Z][-a-zA-Z0-9]*, max 128 chars."""
        import re
        name = re.sub(r"[^a-zA-Z0-9\-]", "-", name)    # underscores â†’ hyphens, etc.
        name = re.sub(r"-{2,}", "-", name).strip("-")
        if not name or not name[0].isalpha():
            name = "stack-" + name
        return name[:128]

    @staticmethod
    def _fix_cloudfront_params(cfg: dict) -> dict:
        """
        Fix common CloudFront parameter errors produced by the LLM:
        1. CachedMethods at top level of DefaultCacheBehavior â†’ move inside AllowedMethods.
        2. Tags at top level of create_distribution params â†’ switch to create_distribution_with_tags.
        """
        params = cfg.get("params", {})
        dist_cfg = params.get("DistributionConfig", {})
        dcb = dist_cfg.get("DefaultCacheBehavior", {})

        # Fix 1: move CachedMethods inside AllowedMethods
        if "CachedMethods" in dcb and isinstance(dcb.get("AllowedMethods"), dict):
            cached = dcb.pop("CachedMethods")
            dcb["AllowedMethods"]["CachedMethods"] = cached

        # Fix 2: MinTTL is required when ForwardedValues is used (legacy mode)
        if "ForwardedValues" in dcb and "MinTTL" not in dcb:
            dcb["MinTTL"] = 0

        # Fix 3: Tags not accepted by create_distribution; use create_distribution_with_tags
        if "Tags" in params and cfg.get("action") == "create_distribution":
            tags = params.pop("Tags")
            cfg["action"] = "create_distribution_with_tags"
            cfg["params"] = {
                "DistributionConfigWithTags": {
                    "DistributionConfig": dist_cfg,
                    "Tags": tags,
                }
            }
            # resource_id_path needs updating since response key stays the same
        return cfg

    @staticmethod
    async def _repair_failed_config(
        cfg: dict,
        error_code: str,
        error_msg: str,
        llm: Any,
        _log: Callable,
    ) -> "dict | None":
        """
        Ask the LLM to return a fixed version of the failed boto3 params.
        Returns a patched copy of cfg, or None if repair is not possible.
        """
        # Errors that cannot be fixed by adjusting params alone
        _skip_codes = {
            "AccessDenied", "UnauthorizedAccess", "InvalidClientTokenId",
            "AuthFailure", "ServiceQuotaExceededException", "LimitExceededException",
            "RequestLimitExceeded", "InsufficientInstanceCapacity",
            "ResourceNotFoundException", "NotFoundException",
        }
        if error_code in _skip_codes:
            return None

        service = cfg.get("service", "")
        action = cfg.get("action", "")
        params = cfg.get("params", {})

        system_prompt = (
            "You are an AWS boto3 API expert. A boto3 call failed. "
            "Return ONLY a JSON object with a single key \"params\" containing the corrected parameters. "
            "Rules:\n"
            "- Only change what is necessary to fix the specific error\n"
            "- Keep all ARNs, names, and IDs exactly as provided unless they are the direct cause of the error\n"
            "- If the error cannot be fixed by changing parameters (e.g. a dependency is missing), return {\"params\": null}\n"
            "- Do not add explanations — return only valid JSON"
        )
        user_prompt = (
            f"Service: {service}\nAction: {action}\n"
            f"Error Code: {error_code}\nError Message: {error_msg}\n\n"
            f"Original params:\n{json.dumps(params, indent=2)}\n\n"
            "Return the fixed params as {\"params\": {...}}."
        )

        try:
            result = await llm.generate(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.1,
            )
            if isinstance(result, dict) and result.get("params") is not None:
                return {**cfg, "params": result["params"]}
        except Exception as _e:
            _log(f"  LLM repair call error: {_e}\n")
        return None

    async def deploy(
        self,
        configs: list[dict[str, Any]],
        log_callback: Callable[[str], None] | None = None,
        project_name: str = "",
        llm: Any = None,
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

            # Auto-provision VPC + subnets + DB subnet group for RDS cluster if none specified
            if cfg.get("service") == "rds" and cfg.get("action") == "create_db_cluster":
                params = cfg.get("params", {})
                if "DBSubnetGroupName" not in params:
                    _log("  ðŸ”§ No DB subnet group specified â€” auto-provisioning networking...\n")
                    try:
                        sg = await self._ensure_rds_networking(project_name, _log)
                        params["DBSubnetGroupName"] = sg
                        cfg["params"] = params
                    except Exception as net_err:
                        _log(f"  âš  Auto-networking failed: {net_err}\n")

            # DocumentDB: fix reserved MasterUsername + auto-provision subnet group
            if cfg.get("service") == "docdb" and cfg.get("action") == "create_db_cluster":
                params = cfg.get("params", {})
                _docdb_reserved = {"admin", "root", "master", "postgres", "oracle",
                                   "user", "rdsadmin", "administrator", "dbadmin"}
                if params.get("MasterUsername", "").lower() in _docdb_reserved:
                    params["MasterUsername"] = "docdbuser"
                    _log("  ðŸ”§ Reserved DocDB username replaced with 'docdbuser'\n")
                if "DBSubnetGroupName" not in params:
                    _log("  ðŸ”§ No DB subnet group for DocDB â€” auto-provisioning networking...\n")
                    try:
                        sg = await self._ensure_rds_networking(project_name, _log)
                        params["DBSubnetGroupName"] = sg
                        cfg["params"] = params
                    except Exception as net_err:
                        _log(f"  âš  Auto-networking failed: {net_err}\n")
                cfg["params"] = params

            # Sanitize S3 bucket names â€” no underscores, max 63 chars, lowercase
            if cfg.get("service") == "s3" and cfg.get("action") == "create_bucket":
                params = cfg.get("params", {})
                if "Bucket" in params:
                    params["Bucket"] = self._sanitize_s3_name(params["Bucket"])
                # us-east-1 must NOT have CreateBucketConfiguration (InvalidLocationConstraint)
                if self.region_name == "us-east-1":
                    params.pop("CreateBucketConfiguration", None)
                cfg["params"] = params

            # Sanitize App Runner service names â€” max 40 chars, [A-Za-z0-9][A-Za-z0-9-_]{3,39}
            if cfg.get("service") == "apprunner" and cfg.get("action") == "create_service":
                params = cfg.get("params", {})
                if "ServiceName" in params:
                    params["ServiceName"] = self._sanitize_apprunner_name(params["ServiceName"])
                    cfg["params"] = params

            # Sanitize CloudFormation stack names â€” [a-zA-Z][-a-zA-Z0-9]* (no underscores)
            if cfg.get("service") == "cloudformation" and cfg.get("action") == "create_stack":
                params = cfg.get("params", {})
                if "StackName" in params:
                    original = params["StackName"]
                    params["StackName"] = self._sanitize_cfn_stack_name(params["StackName"])
                    # Also update delete_params if they reference the same name
                    if cfg.get("delete_params", {}).get("StackName") == original:
                        cfg["delete_params"]["StackName"] = params["StackName"]
                    if cfg.get("waiter_params", {}).get("StackName") == original:
                        cfg["waiter_params"]["StackName"] = params["StackName"]
                    cfg["params"] = params
                # Fix empty Resources â€” CloudFormation requires at least one resource
                try:
                    body = params.get("TemplateBody", "{}")
                    tmpl = json.loads(body) if isinstance(body, str) else body
                    if not tmpl.get("Resources"):
                        tmpl["Resources"] = {
                            "InfraAgentPlaceholder": {
                                "Type": "AWS::CloudFormation::WaitConditionHandle",
                            }
                        }
                        params["TemplateBody"] = json.dumps(tmpl)
                        cfg["params"] = params
                except Exception:
                    pass

            # CloudTrail: Tags is not a valid create_trail param â€” strip and apply after creation
            if cfg.get("service") == "cloudtrail" and cfg.get("action") == "create_trail":
                params = cfg.get("params", {})
                pending_tags = params.pop("Tags", None)
                if pending_tags:
                    cfg["_pending_tags"] = pending_tags
                    cfg["params"] = params

            # CodePipeline: artifactStore.location must match [a-zA-Z0-9\-\.]+
            if cfg.get("service") == "codepipeline" and cfg.get("action") == "create_pipeline":
                import re as _re_cp
                params = cfg.get("params", {})
                pipeline = params.get("pipeline", {})
                store = pipeline.get("artifactStore", {})
                if "location" in store:
                    loc = _re_cp.sub(r"[^a-zA-Z0-9\-\.]", "-", store["location"])
                    loc = _re_cp.sub(r"-{2,}", "-", loc).strip("-")
                    store["location"] = loc
                    pipeline["artifactStore"] = store
                    params["pipeline"] = pipeline
                    cfg["params"] = params

            # Fix CloudFront param structure errors
            if cfg.get("service") == "cloudfront":
                cfg = self._fix_cloudfront_params(cfg)
            # Resolve subnet / security-group placeholder strings anywhere in params.
            # LLMs often emit __DEFAULT_SUBNETS__ as a string where a list is required.
            _params_str = json.dumps(cfg.get("params", {}))
            _SUBNET_MARKERS = ("__DEFAULT_SUBNETS__", "__DEFAULT_SUBNET_IDS__", "__SUBNETS__", "__VPC_SUBNETS__")
            _SG_MARKERS = ("__DEFAULT_SECURITY_GROUPS__", "__DEFAULT_SG__", "__SECURITY_GROUPS__", "__SG_IDS__")
            if any(m in _params_str for m in _SUBNET_MARKERS + _SG_MARKERS):
                _log("  \U0001f527 Resolving network placeholders (subnets/security groups)...\n")
                _sn_ids = await self._get_default_vpc_subnet_ids(_log)
                _sg_ids = await self._get_default_security_group_ids(_log)
                self._resolve_network_placeholders(cfg["params"], _sn_ids, _sg_ids)
            # Validate AWS Config managed rule identifiers â€” skip hallucinated rule names
            if cfg.get("service") == "config" and cfg.get("action") == "put_config_rule":
                rule = cfg.get("params", {}).get("ConfigRule", {})
                source = rule.get("Source", {})
                identifier = source.get("SourceIdentifier", "")
                if source.get("Owner") == "AWS" and identifier not in self.VALID_CONFIG_RULE_IDS:
                    _log(
                        f"  âš  Skipping Config rule '{identifier}' â€” not a valid AWS managed rule identifier.\n"
                        f"    (LLM hallucination â€” no such managed rule exists in AWS Config.)\n"
                    )
                    deployed.append({
                        "service": cfg.get("service", "config"),
                        "action": "put_config_rule",
                        "label": cfg.get("label", identifier),
                        "status": "skipped",
                        "error_message": f"Invalid AWS Config managed rule identifier: {identifier}",
                    })
                    continue

            service = cfg.get("service", "unknown")
            action = cfg.get("action", "unknown")
            label = cfg.get("label", f"{service}.{action}")
            _log(f"[{i}/{len(configs)}] Creating {label} via {service}.{action}...\n")

            # Retry budget for transient IAM propagation errors ("Role is not valid" etc.)
            _iam_retry_attempts = 3
            _iam_retry_delay = 15  # seconds between retries

            try:
                _last_iam_err: Exception | None = None
                result = None
                for _attempt in range(_iam_retry_attempts):
                    try:
                        result = await self._execute_call(cfg)
                        _last_iam_err = None
                        break
                    except ClientError as _ce:
                        _emsg = _ce.response["Error"].get("Message", "")
                        _ecode = _ce.response["Error"].get("Code", "")
                        _iam_transient = (
                            "Role is not valid" in _emsg
                            or "role" in _emsg.lower() and "valid" in _emsg.lower()
                            or _ecode in ("InvalidParameterException",) and "role" in _emsg.lower()
                        )
                        if _iam_transient and _attempt < _iam_retry_attempts - 1:
                            _log(f"  \u26a0 IAM role not yet propagated \u2014 retrying in {_iam_retry_delay}s (attempt {_attempt + 1}/{_iam_retry_attempts})...\n")
                            await asyncio.sleep(_iam_retry_delay)
                            _last_iam_err = _ce
                            continue
                        raise  # not an IAM transient error, or last attempt
                if _last_iam_err is not None:
                    raise _last_iam_err
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
                _log(f"  âœ“ Created {label} (ID: {resource_id or 'N/A'})\n")

                # Update last_resource_id for __RESOLVE_PREV__ in subsequent configs
                if resource_id:
                    last_resource_id = resource_id

                # CloudTrail: apply tags via add_tags (not supported in create_trail)
                if service == "cloudtrail" and cfg.get("_pending_tags") and resource_id:
                    try:
                        ct = self._get_client("cloudtrail")
                        await asyncio.to_thread(
                            ct.add_tags,
                            ResourceId=resource_id,
                            TagsList=cfg["_pending_tags"],
                        )
                        _log(f"  âœ“ Tags applied to {label}\n")
                    except Exception as te:
                        _log(f"  âš  Could not tag {label}: {te}\n")

                # IAM role/policy propagation: AWS takes ~10 s to make a new role usable
                if service == "iam" and action in ("create_role", "attach_role_policy", "put_role_policy"):
                    _log(f"  â³ Waiting 10 s for IAM changes to propagate...\n")
                    await asyncio.sleep(10)

                # Wait for resource if waiter is specified
                if cfg.get("waiter"):
                    _log(f"  â³ Waiting for {label} to be ready...\n")
                    try:
                        await self._wait_for(service, cfg["waiter"], cfg.get("waiter_params", {}))
                        _log(f"  âœ“ {label} is ready.\n")
                    except Exception as we:
                        _log(f"  âš  Waiter warning: {we}\n")

            except ClientError as e:
                error_code = e.response["Error"]["Code"]
                error_msg = e.response["Error"]["Message"]

                # Treat "already exists" errors as idempotent success
                _already_exists_codes = {
                    "AlreadyExistsException",
                    "ResourceAlreadyExistsException",
                    "BucketAlreadyOwnedByYou",
                    "BucketAlreadyExists",
                    "EntityAlreadyExists",
                    "DBClusterAlreadyExistsFault",
                    "DBInstanceAlreadyExists",
                    "DBSubnetGroupAlreadyExists",
                    "InvalidChangeBatch",  # Route53 record already exists
                }
                if error_code in _already_exists_codes:
                    _log(f"  â„¹ {label} already exists â€” treating as success.\n")
                    deployed.append({
                        "service": service,
                        "action": action,
                        "label": label,
                        "resource_id": None,
                        "resource_type": cfg.get("resource_type", service),
                        "delete_action": cfg.get("delete_action"),
                        "delete_params_key": cfg.get("delete_params_key"),
                        "delete_params": cfg.get("delete_params"),
                        "status": "created",
                        "response_summary": {"note": "already existed"},
                    })
                    continue

                _log(f"  âœ— FAILED: [{error_code}] {error_msg}\n")
                if llm is not None:
                    _log(f"  \U0001f916 Attempting LLM-assisted repair for {label}...\n")
                    _fixed = await self._repair_failed_config(cfg, error_code, error_msg, llm, _log)
                    if _fixed is not None:
                        try:
                            result = await self._execute_call(_fixed)
                            resource_id = None
                            if _fixed.get("resource_id_path") and result:
                                try:
                                    resource_id = self._extract_resource_id(result, _fixed["resource_id_path"])
                                except Exception:
                                    pass
                            _log(f"  \u2713 Repaired and created {label} (ID: {resource_id or 'N/A'})\n")
                            deployed.append({
                                "service": service, "action": action, "label": label,
                                "resource_id": resource_id,
                                "resource_type": cfg.get("resource_type", service),
                                "delete_action": cfg.get("delete_action"),
                                "delete_params_key": cfg.get("delete_params_key"),
                                "delete_params": cfg.get("delete_params"),
                                "status": "created",
                                "response_summary": self._summarize_response(result),
                            })
                            if resource_id:
                                last_resource_id = resource_id
                            continue
                        except Exception as _re:
                            _log(f"  \u2717 Repair attempt also failed: {_re}\n")
                    else:
                        _log(f"  \u2139 LLM could not suggest a fix for this error type.\n")
                deployed.append({
                    "service": service,
                    "action": action,
                    "label": label,
                    "status": "failed",
                    "error_code": error_code,
                    "error_message": error_msg,
                })
            except (BotoCoreError, Exception) as e:
                _log(f"  \u2717 FAILED: {str(e)}\n")
                if llm is not None:
                    _log(f"  \U0001f916 Attempting LLM-assisted repair for {label}...\n")
                    _fixed = await self._repair_failed_config(cfg, "Exception", str(e), llm, _log)
                    if _fixed is not None:
                        try:
                            result = await self._execute_call(_fixed)
                            resource_id = None
                            if _fixed.get("resource_id_path") and result:
                                try:
                                    resource_id = self._extract_resource_id(result, _fixed["resource_id_path"])
                                except Exception:
                                    pass
                            _log(f"  \u2713 Repaired and created {label} (ID: {resource_id or 'N/A'})\n")
                            deployed.append({
                                "service": service, "action": action, "label": label,
                                "resource_id": resource_id,
                                "resource_type": cfg.get("resource_type", service),
                                "delete_action": cfg.get("delete_action"),
                                "delete_params_key": cfg.get("delete_params_key"),
                                "delete_params": cfg.get("delete_params"),
                                "status": "created",
                                "response_summary": self._summarize_response(result),
                            })
                            if resource_id:
                                last_resource_id = resource_id
                            continue
                        except Exception as _re:
                            _log(f"  \u2717 Repair attempt also failed: {_re}\n")
                    else:
                        _log(f"  \u2139 LLM could not suggest a fix for this error type.\n")
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
        Processes in reverse order (last created â†’ first deleted).
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
                _log(f"[{i}/{len(records)}] Skipping {label} â€” no delete action configured.\n")
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
                _log(f"  âœ“ Destroyed {label}\n")
                results.append({**record, "destroy_status": "destroyed"})

            except ClientError as e:
                error_msg = e.response["Error"]["Message"]
                _log(f"  âœ— FAILED: {error_msg}\n")
                results.append({**record, "destroy_status": "failed", "destroy_error": error_msg})
            except Exception as e:
                _log(f"  âœ— FAILED: {str(e)}\n")
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
            _log(f"  ðŸ—‘ Emptying S3 bucket {resource_id}...\n")
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
                _log(f"  âš  Bucket cleanup warning: {e}\n")

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
