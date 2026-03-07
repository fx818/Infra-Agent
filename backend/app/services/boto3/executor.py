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

import re

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
    async def _find_available_cidr(
        ec2_client: Any,
        vpc_id: str,
        vpc_cidr: str,
        existing_cidrs: set[str],
        _log: Callable,
    ) -> str | None:
        """
        Find an available /24 CIDR within the VPC's address space that does
        not overlap with any existing subnets.

        Falls back to a set of common private ranges if the VPC CIDR can't be
        parsed.
        """
        import ipaddress

        try:
            # Parse the VPC network (e.g. "10.0.0.0/16" → network object)
            vpc_net = ipaddress.ip_network(vpc_cidr, strict=False)
        except (ValueError, TypeError):
            # If VPC CIDR is unparsable, try common fallback ranges
            vpc_net = None

        # Build set of existing networks for overlap checks
        _existing_nets = set()
        for c in existing_cidrs:
            try:
                _existing_nets.add(ipaddress.ip_network(c, strict=False))
            except (ValueError, TypeError):
                pass

        def _overlaps(candidate: "ipaddress.IPv4Network") -> bool:
            return any(candidate.overlaps(n) for n in _existing_nets)

        if vpc_net:
            # Iterate /24 subnets within the VPC CIDR
            for subnet_candidate in vpc_net.subnets(new_prefix=24):
                cidr_str = str(subnet_candidate)
                if cidr_str not in existing_cidrs and not _overlaps(subnet_candidate):
                    return cidr_str
        else:
            # Fallback: try 10.0.{100..254}.0/24
            for third_octet in range(100, 255):
                _c = f"10.0.{third_octet}.0/24"
                try:
                    _cn = ipaddress.ip_network(_c)
                    if _c not in existing_cidrs and not _overlaps(_cn):
                        return _c
                except (ValueError, TypeError):
                    pass

        return None

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
        # ── Fast-reject: errors that cannot be fixed by tweaking params ──────
        _skip_codes = {
            # Auth / permissions
            "AccessDenied", "AccessDeniedException", "UnauthorizedAccess",
            "InvalidClientTokenId", "AuthFailure", "ExpiredToken",
            "SignatureDoesNotMatch",
            # Quota / limits — exact codes
            "ServiceQuotaExceededException", "LimitExceededException",
            "RequestLimitExceeded", "TooManyRequestsException", "Throttling",
            "InsufficientInstanceCapacity",
            # Not-found (dependency missing — params alone can't fix it)
            "ResourceNotFoundException", "NotFoundException",
        }
        if error_code in _skip_codes:
            return None

        # Also skip AWS-specific "LimitExceeded" codes that follow a pattern
        # e.g. VpcLimitExceeded, InternetGatewayLimitExceeded, AddressLimitExceeded …
        _lower_code = error_code.lower()
        if "limitexceeded" in _lower_code or "quotaexceeded" in _lower_code:
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
            "- If the error is about a duplicate / already-existing resource, try adjusting the name/identifier\n"
            "- If the error cannot be fixed by changing parameters (e.g. a dependency is missing), return {\"params\": null}\n"
            "- Do not add explanations — return only valid JSON"
        )
        user_prompt = (
            f"Service: {service}\nAction: {action}\n"
            f"Error Code: {error_code}\nError Message: {error_msg}\n\n"
            f"Original params:\n{json.dumps(params, indent=2, default=str)}\n\n"
            "Return the fixed params as {{\"params\": {{...}}}}."
        )

        try:
            # Wrap in asyncio.wait_for to avoid hanging if the LLM is unresponsive
            result = await asyncio.wait_for(
                llm.generate(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    temperature=0.1,
                ),
                timeout=30,
            )
            if isinstance(result, dict) and result.get("params") is not None:
                fixed_params = result["params"]
                # Sanity check: the LLM must return a dict for params
                if not isinstance(fixed_params, dict):
                    _log(f"  ⚠ LLM returned non-dict params ({type(fixed_params).__name__}) — skipping.\n")
                    return None
                return {**cfg, "params": fixed_params}
            elif isinstance(result, dict) and result.get("params") is None:
                # LLM explicitly said it can't fix this
                return None
            else:
                _log(f"  ⚠ LLM returned unexpected shape — skipping repair.\n")
                return None

        except asyncio.TimeoutError:
            _log(f"  ⚠ LLM repair timed out (30s) — skipping.\n")
            return None
        except ValueError as _ve:
            # llm.generate() raised ValueError when it couldn't parse the response as
            # JSON. The raw LLM text is in the exception message — try to extract
            # {"params": ...} from it directly using brace matching.
            raw = str(_ve)
            # Remove the error prefix to get closer to the raw content
            _prefix = "LLM response is not valid JSON: "
            _raw_content = raw[raw.index(_prefix) + len(_prefix):] if _prefix in raw else raw

            marker = _raw_content.find('"params"')
            if marker == -1:
                marker = _raw_content.find("'params'")
            if marker != -1:
                obj_start = _raw_content.rfind('{', 0, marker)
                if obj_start != -1:
                    depth = 0
                    for _i in range(obj_start, len(_raw_content)):
                        if _raw_content[_i] == '{':
                            depth += 1
                        elif _raw_content[_i] == '}':
                            depth -= 1
                            if depth == 0:
                                _candidate = _raw_content[obj_start:_i + 1]
                                # Try direct parse, then with trailing comma cleanup
                                for _attempt_str in [_candidate, re.sub(r',\s*([}\]])', r'\1', _candidate)]:
                                    try:
                                        _extracted = json.loads(_attempt_str)
                                        if isinstance(_extracted, dict) and isinstance(_extracted.get("params"), dict):
                                            return {**cfg, "params": _extracted["params"]}
                                    except json.JSONDecodeError:
                                        pass
                                break
            _log(f"  ⚠ LLM repair parse error: {str(_ve)[:120]}\n")
        except Exception as _e:
            _log(f"  ⚠ LLM repair call failed: {str(_e)[:120]}\n")
        return None

    # ── Reuse-Existing-Resource Fallback ─────────────────────────────────
    # Mapping of (service, action) → async function that returns an existing resource ID
    # Used when resource creation fails with a limit/quota exceeded error.

    async def _find_existing_resource(
        self,
        cfg: dict,
        error_code: str,
        _log: Callable,
    ) -> dict | None:
        """
        When a resource limit/quota is exceeded, try to find and reuse an
        existing AWS resource of the same type.

        Returns a dict with ``resource_id`` and ``reused: True`` on success,
        or ``None`` if no suitable existing resource was found.
        """
        service = cfg.get("service", "")
        action = cfg.get("action", "")
        params = cfg.get("params", {})
        label = cfg.get("label", f"{service}.{action}")

        try:
            # ---- EC2: VPC ------------------------------------------------
            if service == "ec2" and action == "create_vpc":
                ec2 = self._get_client("ec2")
                resp = await asyncio.to_thread(
                    ec2.describe_vpcs,
                    Filters=[{"Name": "state", "Values": ["available"]}],
                )
                vpcs = resp.get("Vpcs", [])
                if vpcs:
                    default = [v for v in vpcs if v.get("IsDefault")]
                    chosen = (default or vpcs)[0]
                    vpc_id = chosen["VpcId"]
                    _log(f"  ♻ Reusing existing VPC: {vpc_id}\n")
                    return {"resource_id": vpc_id, "reused": True}

            # ---- EC2: Subnet ---------------------------------------------
            elif service == "ec2" and action == "create_subnet":
                ec2 = self._get_client("ec2")
                vpc_id = params.get("VpcId")
                filters: list[dict] = [{"Name": "state", "Values": ["available"]}]
                if vpc_id:
                    filters.append({"Name": "vpc-id", "Values": [vpc_id]})
                resp = await asyncio.to_thread(ec2.describe_subnets, Filters=filters)
                subnets = resp.get("Subnets", [])
                if subnets:
                    az = params.get("AvailabilityZone")
                    if az:
                        matched = [s for s in subnets if s.get("AvailabilityZone") == az]
                        chosen = matched[0] if matched else subnets[0]
                    else:
                        chosen = subnets[0]
                    subnet_id = chosen["SubnetId"]
                    _log(f"  ♻ Reusing existing subnet: {subnet_id} (AZ: {chosen.get('AvailabilityZone', '?')})\n")
                    return {"resource_id": subnet_id, "reused": True}

            # ---- EC2: Security Group -------------------------------------
            elif service == "ec2" and action == "create_security_group":
                ec2 = self._get_client("ec2")
                vpc_id = params.get("VpcId")
                filters = []
                if vpc_id:
                    filters.append({"Name": "vpc-id", "Values": [vpc_id]})
                resp = await asyncio.to_thread(ec2.describe_security_groups, Filters=filters)
                sgs = resp.get("SecurityGroups", [])
                if sgs:
                    default_sg = [s for s in sgs if s.get("GroupName") == "default"]
                    chosen = (default_sg or sgs)[0]
                    sg_id = chosen["GroupId"]
                    _log(f"  ♻ Reusing existing security group: {sg_id} ({chosen.get('GroupName', '')})\n")
                    return {"resource_id": sg_id, "reused": True}

            # ---- EC2: Internet Gateway -----------------------------------
            elif service == "ec2" and action == "create_internet_gateway":
                ec2 = self._get_client("ec2")
                resp = await asyncio.to_thread(ec2.describe_internet_gateways)
                igws = resp.get("InternetGateways", [])
                if igws:
                    igw_id = igws[0]["InternetGatewayId"]
                    _log(f"  ♻ Reusing existing Internet Gateway: {igw_id}\n")
                    return {"resource_id": igw_id, "reused": True}

            # ---- EC2: Elastic IP -----------------------------------------
            elif service == "ec2" and action == "allocate_address":
                ec2 = self._get_client("ec2")
                resp = await asyncio.to_thread(ec2.describe_addresses)
                addrs = resp.get("Addresses", [])
                unassociated = [a for a in addrs if not a.get("AssociationId")]
                if unassociated:
                    eip = unassociated[0]
                    alloc_id = eip.get("AllocationId", "")
                    _log(f"  ♻ Reusing unassociated Elastic IP: {alloc_id} ({eip.get('PublicIp', '')})\n")
                    return {"resource_id": alloc_id, "reused": True}

            # ---- EC2: NAT Gateway ----------------------------------------
            elif service == "ec2" and action == "create_nat_gateway":
                ec2 = self._get_client("ec2")
                resp = await asyncio.to_thread(
                    ec2.describe_nat_gateways,
                    Filter=[{"Name": "state", "Values": ["available"]}],
                )
                ngws = resp.get("NatGateways", [])
                if ngws:
                    ngw_id = ngws[0]["NatGatewayId"]
                    _log(f"  ♻ Reusing existing NAT Gateway: {ngw_id}\n")
                    return {"resource_id": ngw_id, "reused": True}

            # ---- EC2: Route Table ----------------------------------------
            elif service == "ec2" and action == "create_route_table":
                ec2 = self._get_client("ec2")
                vpc_id = params.get("VpcId")
                filters = []
                if vpc_id:
                    filters.append({"Name": "vpc-id", "Values": [vpc_id]})
                resp = await asyncio.to_thread(ec2.describe_route_tables, Filters=filters)
                rts = resp.get("RouteTables", [])
                if rts:
                    main = [r for r in rts for a in r.get("Associations", []) if a.get("Main")]
                    chosen = (main or rts)[0]
                    rt_id = chosen["RouteTableId"]
                    _log(f"  ♻ Reusing existing route table: {rt_id}\n")
                    return {"resource_id": rt_id, "reused": True}

            # ---- EC2: Network ACL ----------------------------------------
            elif service == "ec2" and action == "create_network_acl":
                ec2 = self._get_client("ec2")
                vpc_id = params.get("VpcId")
                filters = []
                if vpc_id:
                    filters.append({"Name": "vpc-id", "Values": [vpc_id]})
                resp = await asyncio.to_thread(ec2.describe_network_acls, Filters=filters)
                nacls = resp.get("NetworkAcls", [])
                if nacls:
                    default_nacl = [n for n in nacls if n.get("IsDefault")]
                    chosen = (default_nacl or nacls)[0]
                    nacl_id = chosen["NetworkAclId"]
                    _log(f"  ♻ Reusing existing Network ACL: {nacl_id}\n")
                    return {"resource_id": nacl_id, "reused": True}

            # ---- RDS: DB Subnet Group ------------------------------------
            elif service == "rds" and action == "create_db_subnet_group":
                rds = self._get_client("rds")
                resp = await asyncio.to_thread(rds.describe_db_subnet_groups)
                groups = resp.get("DBSubnetGroups", [])
                if groups:
                    grp_name = groups[0]["DBSubnetGroupName"]
                    _log(f"  ♻ Reusing existing DB subnet group: {grp_name}\n")
                    return {"resource_id": grp_name, "reused": True}

            # ---- ElastiCache: Cache Subnet Group -------------------------
            elif service == "elasticache" and action == "create_cache_subnet_group":
                ec = self._get_client("elasticache")
                resp = await asyncio.to_thread(ec.describe_cache_subnet_groups)
                groups = resp.get("CacheSubnetGroups", [])
                if groups:
                    grp_name = groups[0]["CacheSubnetGroupName"]
                    _log(f"  ♻ Reusing existing cache subnet group: {grp_name}\n")
                    return {"resource_id": grp_name, "reused": True}

            # ---- EFS: File System ----------------------------------------
            elif service == "efs" and action == "create_file_system":
                efs = self._get_client("efs")
                resp = await asyncio.to_thread(efs.describe_file_systems)
                fss = resp.get("FileSystems", [])
                available = [f for f in fss if f.get("LifeCycleState") == "available"]
                if available:
                    fs_id = available[0]["FileSystemId"]
                    _log(f"  ♻ Reusing existing EFS: {fs_id}\n")
                    return {"resource_id": fs_id, "reused": True}

        except Exception as e:
            _log(f"  ⚠ Could not find existing {label} to reuse: {str(e)[:100]}\n")

        return None

    @staticmethod
    def _is_limit_exceeded_error(error_code: str) -> bool:
        """Return True if the AWS error code indicates a limit/quota was exceeded."""
        _exact = {
            "ServiceQuotaExceededException", "LimitExceededException",
            "RequestLimitExceeded", "InsufficientInstanceCapacity",
        }
        if error_code in _exact:
            return True
        _lc = error_code.lower()
        return "limitexceeded" in _lc or "quotaexceeded" in _lc

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
        _llm_disabled = False  # set True if LLM auth fails once — don't retry every resource

        # ── Cross-resource reference tracking ────────────────────────────────
        _ref_map: dict[str, str] = {}      # tool_node_id → resource_id
        _vpc_id: str | None = None         # most recently created/reused VPC ID
        _first_public_subnet: str | None = None  # first public subnet
        _ssm_resolved: str | None = None   # last SSM parameter lookup result

        for i, cfg in enumerate(configs, 1):
            # Resolve the __RESOLVE_PREV__ placeholder with the last successfully created resource ID
            if last_resource_id and "__RESOLVE_PREV__" in json.dumps(cfg):
                self._replace_placeholders(cfg, {"__RESOLVE_PREV__": last_resource_id})

            # ── Resolve cross-resource reference placeholders ────────────────
            _cfg_str = json.dumps(cfg)
            _cross_replacements: dict[str, str] = {}
            if "__VPC_ID__" in _cfg_str and _vpc_id:
                _cross_replacements["__VPC_ID__"] = _vpc_id
            if "__SSM_RESOLVED__" in _cfg_str and _ssm_resolved:
                _cross_replacements["__SSM_RESOLVED__"] = _ssm_resolved
            if "__FIRST_PUBLIC_SUBNET__" in _cfg_str and _first_public_subnet:
                _cross_replacements["__FIRST_PUBLIC_SUBNET__"] = _first_public_subnet
            # __RESOLVE_REF__:node_id  →  look up node_id in _ref_map
            for _ref_match in re.finditer(r'__RESOLVE_REF__:([^"\\]+)', _cfg_str):
                _ref_key = _ref_match.group(1)
                if _ref_key in _ref_map:
                    _cross_replacements[f"__RESOLVE_REF__:{_ref_key}"] = _ref_map[_ref_key]
                elif _vpc_id:
                    # Fallback: if the ref looks like it targets a VPC, use the known VPC
                    _cross_replacements[f"__RESOLVE_REF__:{_ref_key}"] = _vpc_id
            if _cross_replacements:
                self._replace_placeholders(cfg, _cross_replacements)

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

            # Strip MapPublicIpOnLaunch from create_subnet (not a valid param)
            if cfg.get("service") == "ec2" and cfg.get("action") == "create_subnet":
                params = cfg.get("params", {})
                _map_pub_ip = params.pop("MapPublicIpOnLaunch", None)
                if _map_pub_ip is not None:
                    cfg["_map_public_ip"] = bool(_map_pub_ip)

                # ── Fix CIDR conflicts when reusing an existing VPC ──────────
                # The LLM-generated CIDR may overlap with subnets already in the
                # VPC.  Detect the conflict and pick a free /24 from the VPC's
                # CIDR block.
                _sub_vpc = params.get("VpcId") or _vpc_id
                _sub_cidr = params.get("CidrBlock", "")
                if _sub_vpc and _sub_cidr:
                    try:
                        _sub_ec2 = self._get_client("ec2")
                        _sub_resp = await asyncio.to_thread(
                            _sub_ec2.describe_subnets,
                            Filters=[{"Name": "vpc-id", "Values": [_sub_vpc]}],
                        )
                        _existing_cidrs = {
                            s["CidrBlock"] for s in _sub_resp.get("Subnets", [])
                        }
                        if _sub_cidr in _existing_cidrs:
                            # Get VPC CIDR to know the address space
                            _vpc_resp = await asyncio.to_thread(
                                _sub_ec2.describe_vpcs, VpcIds=[_sub_vpc]
                            )
                            _vpc_cidr = _vpc_resp["Vpcs"][0]["CidrBlock"] if _vpc_resp.get("Vpcs") else ""
                            _new_cidr = await self._find_available_cidr(
                                _sub_ec2, _sub_vpc, _vpc_cidr, _existing_cidrs, _log
                            )
                            if _new_cidr:
                                _log(f"  🔧 CIDR {_sub_cidr} conflicts — using {_new_cidr} instead.\n")
                                params["CidrBlock"] = _new_cidr
                    except Exception as _cidr_err:
                        _log(f"  ⚠ Could not check/fix subnet CIDR: {_cidr_err}\n")

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


            # Sanitize DynamoDB table names - [a-zA-Z0-9_.-]+
            if cfg.get("service") == "dynamodb" and cfg.get("action") == "create_table":
                params = cfg.get("params", {})
                if "TableName" in params:
                    _tn = params["TableName"].replace(" ", "-")
                    _tn = re.sub(r"[^a-zA-Z0-9_\-.]", "-", _tn)
                    _tn = re.sub(r"-+", "-", _tn).strip("-") or "table"
                    params["TableName"] = _tn[:255]
                    for _sk in ("delete_params", "waiter_params"):
                        if cfg.get(_sk, {}).get("TableName"):
                            cfg[_sk]["TableName"] = params["TableName"]
                    cfg["params"] = params

            # Sanitize RDS identifiers - [a-zA-Z][a-zA-Z0-9-]*, max 63 chars
            if cfg.get("service") == "rds" and cfg.get("action") in (
                "create_db_instance", "create_db_cluster"
            ):
                params = cfg.get("params", {})
                for _id_key in ("DBInstanceIdentifier", "DBClusterIdentifier"):
                    if _id_key in params:
                        _di = re.sub(r"[^a-zA-Z0-9\-]", "-", params[_id_key])
                        _di = re.sub(r"-+", "-", _di).strip("-") or "db"
                        _di = _di[:63]
                        if _di and not _di[0].isalpha():
                            _di = "db-" + _di
                        params[_id_key] = _di
                        for _sub in ("delete_params", "waiter_params"):
                            if cfg.get(_sub, {}).get(_id_key):
                                cfg[_sub][_id_key] = _di
                cfg["params"] = params

            # Sanitize ElastiCache cluster IDs - [a-z][a-z0-9-]*, max 50 chars
            if cfg.get("service") == "elasticache" and cfg.get("action") == "create_cache_cluster":
                params = cfg.get("params", {})
                if "CacheClusterId" in params:
                    _cc = re.sub(r"[^a-z0-9\-]", "-", params["CacheClusterId"].lower())
                    _cc = re.sub(r"-+", "-", _cc).strip("-") or "cache"
                    _cc = _cc[:50]
                    if _cc and not _cc[0].isalpha():
                        _cc = "c-" + _cc
                    params["CacheClusterId"] = _cc
                    # Propagate sanitized ID to ALL dependent param dicts
                    for _sk in ("delete_params", "waiter_params"):
                        if cfg.get(_sk, {}).get("CacheClusterId"):
                            cfg[_sk]["CacheClusterId"] = _cc
                    cfg["params"] = params

            # Sanitize ECS cluster/service names - [a-zA-Z0-9_-]+
            if cfg.get("service") == "ecs":
                params = cfg.get("params", {})
                for _nk in ("clusterName", "serviceName"):
                    if _nk in params:
                        _cn = re.sub(r"[^a-zA-Z0-9_\-]", "-", params[_nk])
                        _cn = re.sub(r"-+", "-", _cn).strip("-") or "cluster"
                        params[_nk] = _cn[:255]
                        if cfg.get("delete_params", {}).get(_nk):
                            cfg["delete_params"][_nk] = params[_nk]
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

            # ── EC2: always create a fresh key pair so the user always has the PEM ──
            if cfg.get("service") == "ec2" and cfg.get("action") == "run_instances":
                import re as _re_kp
                params = cfg.get("params", {})
                # Use LLM-supplied KeyName if present, otherwise auto-generate one
                _existing_kn = params.get("KeyName", "").strip()
                _base = _existing_kn or f"{project_name or 'infra'}-{cfg.get('label', 'instance')}"
                _kp_name = _re_kp.sub(r"[^a-zA-Z0-9\-_]", "-", _base)[:200].strip("-")
                if not _kp_name.endswith("-key"):
                    _kp_name += "-key"
                _ec2_kp = self._get_client("ec2")

                async def _create_kp_fresh(name: str) -> dict:
                    """Create key pair, deleting first if it already exists."""
                    try:
                        return await asyncio.to_thread(
                            _ec2_kp.create_key_pair,
                            KeyName=name, KeyType="rsa", KeyFormat="pem",
                        )
                    except ClientError as _ce:
                        if _ce.response["Error"]["Code"] == "InvalidKeyPair.Duplicate":
                            _log(f"  \u21bb Key pair '{name}' exists — replacing to obtain fresh PEM...\n")
                            # Delete existing key and recreate to get the key material
                            await asyncio.to_thread(_ec2_kp.delete_key_pair, KeyName=name)
                            return await asyncio.to_thread(
                                _ec2_kp.create_key_pair,
                                KeyName=name, KeyType="rsa", KeyFormat="pem",
                            )
                        raise

                _log(f"  \U0001f511 Creating EC2 key pair '{_kp_name}'...\n")
                try:
                    _kp_resp = await _create_kp_fresh(_kp_name)
                    cfg["_key_pair_name"] = _kp_name
                    cfg["_key_pair_id"] = _kp_resp.get("KeyPairId", "")
                    cfg["_key_material"] = _kp_resp.get("KeyMaterial", "")
                    params["KeyName"] = _kp_name
                    cfg["params"] = params
                    _log(f"  \u2713 Key pair ready: {_kp_name} (ID: {cfg['_key_pair_id']})\n")
                except Exception as _kp_err:
                    _log(f"  \u26a0 Could not create key pair: {_kp_err} — instance will launch without a key\n")

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
                # Don't persist lookup-only or support-only (no delete) records
                # -- they aren't real provisioned resources and clutter destroy.
                _skip_persist = (
                    cfg.get("is_lookup")
                    or (cfg.get("is_support") and not cfg.get("delete_action"))
                )
                if not _skip_persist:
                    deployed.append(record)
                _log(f"  âœ“ Created {label} (ID: {resource_id or 'N/A'})\n")

                # EC2: store key pair fields now; SSH instructions logged AFTER waiter (real IP needed)
                if service == "ec2" and action == "run_instances" and cfg.get("_key_pair_name"):
                    record["key_pair_name"] = cfg["_key_pair_name"]
                    record["key_pair_id"] = cfg.get("_key_pair_id", "")
                    record["key_material"] = cfg.get("_key_material", "")  # PEM (empty if key pre-existed)
                    _inst_list = (result or {}).get("Instances", [{}])
                    _inst = _inst_list[0] if _inst_list else {}
                    # IP is usually empty here; will be refreshed after instance_running waiter
                    record["public_ip"] = _inst.get("PublicIpAddress", "")
                    record["public_dns"] = _inst.get("PublicDnsName", "")

                # Update last_resource_id for __RESOLVE_PREV__ in subsequent configs
                if resource_id:
                    last_resource_id = resource_id

                # ── Update cross-resource reference maps ─────────────────────
                if resource_id:
                    _node_id = cfg.get("_tool_node_id")
                    if _node_id:
                        _ref_map[_node_id] = resource_id
                    if action == "create_vpc":
                        _vpc_id = resource_id
                    if action == "create_subnet" and "public" in label.lower():
                        if not _first_public_subnet:
                            _first_public_subnet = resource_id
                    if cfg.get("is_lookup") and service == "ssm":
                        _ssm_resolved = resource_id  # SSM returns param value as resource_id

                # ── Execute post_create actions (e.g. VPC modify_vpc_attribute) ──
                if cfg.get("post_create") and resource_id:
                    for _pc in cfg["post_create"]:
                        _pc_action = _pc.get("action")
                        _pc_tmpl = _pc.get("params_template", {})
                        _pc_params: dict[str, Any] = {}
                        for _pk, _pv in _pc_tmpl.items():
                            if _pv == "__RESOURCE_ID__":
                                _pc_params[_pk] = resource_id
                            elif _pv == "__VPC_ID__" and _vpc_id:
                                _pc_params[_pk] = _vpc_id
                            else:
                                _pc_params[_pk] = _pv
                        try:
                            _pc_client = self._get_client(service)
                            await asyncio.to_thread(getattr(_pc_client, _pc_action), **_pc_params)
                            _log(f"  \u2713 Post-create: {_pc_action}\n")
                        except Exception as _pc_err:
                            _log(f"  \u26a0 Post-create {_pc_action} failed: {_pc_err}\n")

                # ── Apply MapPublicIpOnLaunch via modify_subnet_attribute ─────
                if action == "create_subnet" and resource_id and cfg.get("_map_public_ip"):
                    try:
                        _sub_ec2 = self._get_client("ec2")
                        await asyncio.to_thread(
                            _sub_ec2.modify_subnet_attribute,
                            SubnetId=resource_id,
                            MapPublicIpOnLaunch={"Value": True},
                        )
                        _log(f"  \u2713 Enabled auto-assign public IP for {resource_id}\n")
                    except Exception as _mpl_err:
                        _log(f"  \u26a0 Could not enable MapPublicIpOnLaunch: {_mpl_err}\n")

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
                        await self._wait_for_with_progress(
                            service, cfg["waiter"], cfg.get("waiter_params", {}), label, _log
                        )
                        _log(f"  âœ“ {label} is ready.\n")
                    except Exception as we:
                        _log(f"  âš  Waiter warning: {we}\n")

                # EC2: ensure instance is running before describing, so public IP is available
                if service == "ec2" and action == "run_instances" and resource_id and record.get("key_pair_name"):
                    # If no waiter was configured, explicitly wait for instance_running now
                    if not cfg.get("waiter"):
                        _log(f"  ⏳ Waiting for EC2 instance {resource_id} to reach running state...\n")
                        try:
                            await self._wait_for("ec2", "instance_running", {"InstanceIds": [resource_id]})
                            _log(f"  ✓ Instance {resource_id} is running.\n")
                        except Exception as _we:
                            _log(f"  ⚠ Waiter warning: {_we}\n")
                    # Now describe to get the real public IP/DNS
                    try:
                        _ec2_desc = self._get_client("ec2")
                        _desc_r = await asyncio.to_thread(
                            _ec2_desc.describe_instances, InstanceIds=[resource_id]
                        )
                        _rdesc = _desc_r["Reservations"][0]["Instances"][0]
                        record["public_ip"] = _rdesc.get("PublicIpAddress", "") or record.get("public_ip", "")
                        record["public_dns"] = _rdesc.get("PublicDnsName", "") or record.get("public_dns", "")
                    except Exception as _di_err:
                        _log(f"  ⚠ Could not refresh instance details: {_di_err}\n")
                    _kp = record["key_pair_name"]
                    _kf = f"{_kp}.pem"
                    _pub_ip = record.get("public_ip", "")
                    _pub_dns = record.get("public_dns", "")
                    _host = _pub_dns or _pub_ip or "<check AWS Console for public IP>"
                    _log(f"\n  🔑 Key pair  : {_kp}\n")
                    _log(f"  🌍 Public IP : {_pub_ip or '(not yet assigned — check EC2 Console)'}\n")
                    if _pub_dns:
                        _log(f"  🌐 Public DNS: {_pub_dns}\n")
                    if record.get("key_material"):
                        _log(f"  📥 Download PEM from Deploy tab, then:  chmod 400 {_kf}\n")
                    _log(f"  📡 SSH (Amazon Linux) : ssh -i \"{_kf}\" ec2-user@{_host}\n")
                    _log(f"  📡 SSH (Ubuntu)       : ssh -i \"{_kf}\" ubuntu@{_host}\n\n")

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
                    "InvalidChangeBatch",       # Route53 record already exists
                    "InvalidGroup.Duplicate",   # Security Group duplicate
                    "ClusterAlreadyExistsFault",
                    "TableAlreadyExists",
                    "ResourceInUseException",
                    "StreamAlreadyExists",
                }
                if error_code in _already_exists_codes:
                    _log(f"  ℹ {label} already exists — treating as success.\n")

                    # ── Try to resolve the actual resource ID so __RESOLVE_PREV__
                    #    and delete_params work correctly for downstream resources.
                    _existing_id: str | None = None
                    try:
                        if service == "ec2" and action == "create_security_group":
                            _sg_ec2 = self._get_client("ec2")
                            _sg_name = cfg.get("params", {}).get("GroupName", "")
                            _sg_vpc = cfg.get("params", {}).get("VpcId", "") or _vpc_id or ""
                            _sg_filters: list[dict] = []
                            if _sg_name:
                                _sg_filters.append({"Name": "group-name", "Values": [_sg_name]})
                            if _sg_vpc:
                                _sg_filters.append({"Name": "vpc-id", "Values": [_sg_vpc]})
                            if _sg_filters:
                                _sg_resp = await asyncio.to_thread(
                                    _sg_ec2.describe_security_groups, Filters=_sg_filters
                                )
                                _sg_list = _sg_resp.get("SecurityGroups", [])
                                if _sg_list:
                                    _existing_id = _sg_list[0]["GroupId"]
                                    _log(f"  ℹ Resolved existing security group: {_existing_id}\n")
                        elif service == "s3" and action == "create_bucket":
                            _existing_id = cfg.get("params", {}).get("Bucket")
                        elif service == "dynamodb" and action == "create_table":
                            _existing_id = cfg.get("params", {}).get("TableName")
                        elif service == "rds" and action == "create_db_instance":
                            _existing_id = cfg.get("params", {}).get("DBInstanceIdentifier")
                        elif service == "rds" and action == "create_db_cluster":
                            _existing_id = cfg.get("params", {}).get("DBClusterIdentifier")
                        elif service == "iam" and action == "create_role":
                            _existing_id = cfg.get("params", {}).get("RoleName")
                            # Try to get the ARN
                            try:
                                _iam_c = self._get_client("iam")
                                _role_resp = await asyncio.to_thread(
                                    _iam_c.get_role, RoleName=_existing_id
                                )
                                _existing_id = _role_resp["Role"]["Arn"]
                            except Exception:
                                pass
                    except Exception as _lookup_err:
                        _log(f"  ⚠ Could not look up existing resource ID: {_lookup_err}\n")

                    if _existing_id:
                        last_resource_id = _existing_id
                        _node_id = cfg.get("_tool_node_id")
                        if _node_id:
                            _ref_map[_node_id] = _existing_id
                        if action == "create_vpc":
                            _vpc_id = _existing_id
                        if action == "create_subnet" and "public" in label.lower():
                            if not _first_public_subnet:
                                _first_public_subnet = _existing_id

                    deployed.append({
                        "service": service,
                        "action": action,
                        "label": label,
                        "resource_id": _existing_id,
                        "resource_type": cfg.get("resource_type", service),
                        "delete_action": cfg.get("delete_action"),
                        "delete_params_key": cfg.get("delete_params_key"),
                        "delete_params": cfg.get("delete_params"),
                        "status": "created",
                        "response_summary": {"note": "already existed"},
                    })
                    continue

                # ── Limit/quota exceeded fallback: reuse existing resource ──
                if self._is_limit_exceeded_error(error_code):
                    _log(f"  ⚠ Limit exceeded: [{error_code}] {error_msg}\n")
                    _log(f"  🔍 Searching for an existing {label} to reuse...\n")
                    _existing = await self._find_existing_resource(cfg, error_code, _log)
                    if _existing is not None:
                        deployed.append({
                            "service": service,
                            "action": action,
                            "label": label,
                            "resource_id": _existing["resource_id"],
                            "resource_type": cfg.get("resource_type", service),
                            "delete_action": None,       # don't delete reused resources
                            "delete_params_key": None,
                            "delete_params": None,
                            "status": "created",
                            "response_summary": {"note": f"reused existing (limit exceeded: {error_code})"},
                        })
                        if _existing["resource_id"]:
                            last_resource_id = _existing["resource_id"]
                            # Update cross-resource reference maps for reused resources
                            _reused_id = _existing["resource_id"]
                            _node_id = cfg.get("_tool_node_id")
                            if _node_id:
                                _ref_map[_node_id] = _reused_id
                            if action == "create_vpc":
                                _vpc_id = _reused_id
                            if action == "create_subnet" and "public" in label.lower():
                                if not _first_public_subnet:
                                    _first_public_subnet = _reused_id
                        continue
                    else:
                        _log(f"  ℹ No suitable existing resource found to reuse.\n")

                _log(f"  ✗ FAILED: [{error_code}] {error_msg}\n")
                if llm is not None and not _llm_disabled:
                    _log(f"  🤖 Attempting LLM-assisted repair for {label}...\n")
                    try:
                        _fixed = await self._repair_failed_config(cfg, error_code, error_msg, llm, _log)
                    except Exception as _repair_err:
                        _llm_disabled = True
                        _log(f"  ⚠ LLM repair unavailable ({str(_repair_err)[:80]}) — disabling for remaining resources.\n")
                        _fixed = None
                    if _fixed is not None:
                        try:
                            result = await self._execute_call(_fixed)
                            resource_id = None
                            if _fixed.get("resource_id_path") and result:
                                try:
                                    resource_id = self._extract_resource_id(result, _fixed["resource_id_path"])
                                except Exception:
                                    pass
                            _log(f"  ✓ Repaired and created {label} (ID: {resource_id or 'N/A'})\n")
                            deployed.append({
                                "service": service, "action": action, "label": label,
                                "resource_id": resource_id,
                                "resource_type": cfg.get("resource_type", service),
                                "delete_action": _fixed.get("delete_action") or cfg.get("delete_action"),
                                "delete_params_key": _fixed.get("delete_params_key") or cfg.get("delete_params_key"),
                                "delete_params": _fixed.get("delete_params") or cfg.get("delete_params"),
                                "status": "created",
                                "response_summary": self._summarize_response(result),
                            })
                            if resource_id:
                                last_resource_id = resource_id
                                # Update cross-ref maps for repaired resources
                                _node_id = cfg.get("_tool_node_id")
                                if _node_id:
                                    _ref_map[_node_id] = resource_id
                                if action == "create_vpc":
                                    _vpc_id = resource_id
                                if action == "create_subnet" and "public" in label.lower():
                                    if not _first_public_subnet:
                                        _first_public_subnet = resource_id
                            continue
                        except ClientError as _re:
                            _re_code = _re.response["Error"]["Code"]
                            _re_msg = _re.response["Error"]["Message"]
                            _log(f"  ✗ Repair attempt also failed: [{_re_code}] {_re_msg}\n")
                        except Exception as _re:
                            _log(f"  ✗ Repair attempt also failed: {_re}\n")
                    else:
                        _log(f"  ℹ LLM could not suggest a fix for this error type.\n")

                # ── Last-resort fallback: try to reuse an existing resource ──
                # For certain resource types (subnets, SGs), if both LLM repair
                # and the initial attempt failed, try to find one to reuse.
                if service == "ec2" and action in ("create_subnet", "create_security_group"):
                    _log(f"  🔍 Searching for an existing {label} to reuse...\n")
                    _fallback = await self._find_existing_resource(cfg, error_code, _log)
                    if _fallback is not None:
                        deployed.append({
                            "service": service,
                            "action": action,
                            "label": label,
                            "resource_id": _fallback["resource_id"],
                            "resource_type": cfg.get("resource_type", service),
                            "delete_action": None,
                            "delete_params_key": None,
                            "delete_params": None,
                            "status": "created",
                            "response_summary": {"note": f"reused existing (after {error_code})"},
                        })
                        if _fallback["resource_id"]:
                            last_resource_id = _fallback["resource_id"]
                            _reused_id = _fallback["resource_id"]
                            _node_id = cfg.get("_tool_node_id")
                            if _node_id:
                                _ref_map[_node_id] = _reused_id
                            if action == "create_subnet" and "public" in label.lower():
                                if not _first_public_subnet:
                                    _first_public_subnet = _reused_id
                        continue

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
                if llm is not None and not _llm_disabled:
                    _log(f"  🤖 Attempting LLM-assisted repair for {label}...\n")
                    try:
                        _fixed = await self._repair_failed_config(cfg, "Exception", str(e), llm, _log)
                    except Exception as _repair_err:
                        _llm_disabled = True
                        _log(f"  ⚠ LLM repair unavailable ({str(_repair_err)[:80]}) — disabling for remaining resources.\n")
                        _fixed = None
                    if _fixed is not None:
                        try:
                            result = await self._execute_call(_fixed)
                            resource_id = None
                            if _fixed.get("resource_id_path") and result:
                                try:
                                    resource_id = self._extract_resource_id(result, _fixed["resource_id_path"])
                                except Exception:
                                    pass
                            _log(f"  ✓ Repaired and created {label} (ID: {resource_id or 'N/A'})\n")
                            deployed.append({
                                "service": service, "action": action, "label": label,
                                "resource_id": resource_id,
                                "resource_type": cfg.get("resource_type", service),
                                "delete_action": _fixed.get("delete_action") or cfg.get("delete_action"),
                                "delete_params_key": _fixed.get("delete_params_key") or cfg.get("delete_params_key"),
                                "delete_params": _fixed.get("delete_params") or cfg.get("delete_params"),
                                "status": "created",
                                "response_summary": self._summarize_response(result),
                            })
                            if resource_id:
                                last_resource_id = resource_id
                                _node_id = cfg.get("_tool_node_id")
                                if _node_id:
                                    _ref_map[_node_id] = resource_id
                                if action == "create_vpc":
                                    _vpc_id = resource_id
                                if action == "create_subnet" and "public" in label.lower():
                                    if not _first_public_subnet:
                                        _first_public_subnet = resource_id
                            continue
                        except Exception as _re:
                            _log(f"  ✗ Repair attempt also failed: {_re}\n")
                    else:
                        _log(f"  ℹ LLM could not suggest a fix for this error type.\n")
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

        # Filter out records that have no delete action (lookups, support-only,
        # reused resources).  They are not owned by this deployment.
        deletable = [r for r in records if r.get("delete_action")]
        skipped = [r for r in records if not r.get("delete_action")]
        for sr in skipped:
            _label = sr.get("label", "unknown")
            _summary = sr.get("response_summary") or {}
            _note = _summary.get("note", "") if isinstance(_summary, dict) else ""
            if "reused" in _note:
                _log(f"  ↳ Skipping {_label} — reused resource (not owned by this deployment).\n")
            # else: silently skip lookups / support records
            results.append({**sr, "destroy_status": "skipped"})

        _log(f"Starting destruction of {len(deletable)} resource(s)...\n")

        for i, record in enumerate(deletable, 1):
            label = record.get("label", "unknown")
            delete_action = record.get("delete_action")
            resource_id = record.get("resource_id")

            _log(f"[{i}/{len(deletable)}] Destroying {label}...\n")

            try:
                service = record.get("service", "unknown")
                client = self._get_client(service)

                # ── If resource_id is missing, try to resolve it ─────────────
                if not resource_id:
                    try:
                        if service == "ec2" and delete_action == "delete_security_group":
                            # Try finding the SG by name from the original create params
                            _dp = record.get("delete_params") or {}
                            _sg_name = _dp.get("GroupName") or ""
                            if _sg_name:
                                _sg_resp = await asyncio.to_thread(
                                    client.describe_security_groups,
                                    Filters=[{"Name": "group-name", "Values": [_sg_name]}],
                                )
                                _sg_list = _sg_resp.get("SecurityGroups", [])
                                if _sg_list:
                                    resource_id = _sg_list[0]["GroupId"]
                                    _log(f"  ℹ Resolved {label} → {resource_id}\n")
                    except Exception:
                        pass
                    if not resource_id:
                        _log(f"  ⚠ Skipping {label} — no resource ID available.\n")
                        results.append({**record, "destroy_status": "skipped", "destroy_error": "No resource ID"})
                        continue

                # Build delete params
                # Use `or {}` rather than a default to handle explicit null stored in JSON
                delete_params = record.get("delete_params") or {}
                if record.get("delete_params_key") and resource_id:
                    delete_params[record["delete_params_key"]] = (
                        [resource_id] if record["delete_params_key"].endswith("s")
                        or record["delete_params_key"].endswith("Ids")
                        else resource_id
                    )

                # Replace __RESOURCE_ID__ placeholder with the real resource_id.
                # delete_params are stored verbatim from the config template, so
                # the placeholder must be substituted before calling the AWS API.
                if resource_id and delete_params and "__RESOURCE_ID__" in json.dumps(delete_params):
                    params_str = json.dumps(delete_params)
                    params_str = params_str.replace('"__RESOURCE_ID__"', json.dumps(resource_id))
                    delete_params = json.loads(params_str)

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
        _log(f"\nDestruction complete: {succeeded}/{len(deletable)} resources destroyed.\n")

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
        """Wait for a resource using a boto3 waiter (no progress logging)."""
        client = self._get_client(service)
        waiter = client.get_waiter(waiter_name)
        await asyncio.to_thread(
            waiter.wait,
            **params,
            WaiterConfig={"Delay": 10, "MaxAttempts": 60},
        )

    async def _wait_for_with_progress(
        self,
        service: str,
        waiter_name: str,
        params: dict,
        label: str,
        _log: Callable,
        delay: int = 10,
        max_attempts: int = 60,
        progress_interval: int = 30,
    ) -> None:
        """
        Wait for a resource with periodic progress log messages.

        Runs the boto3 waiter in a thread while the async loop fires a
        '⏳ Still waiting...' log line every `progress_interval` seconds
        so the user never sees a silent hang on slow resources (e.g.
        ElastiCache Redis, RDS, EKS which can take 5-10 minutes).
        """
        client = self._get_client(service)
        waiter = client.get_waiter(waiter_name)

        # Wrap synchronous waiter.wait in a future so we can race it with a progress ticker
        loop = asyncio.get_event_loop()
        waiter_future = loop.run_in_executor(
            None,
            lambda: waiter.wait(**params, WaiterConfig={"Delay": delay, "MaxAttempts": max_attempts}),
        )

        elapsed = 0
        while True:
            done, _ = await asyncio.wait({waiter_future}, timeout=progress_interval)
            if done:
                # Re-raise any exception from the waiter
                waiter_future.result()
                return
            elapsed += progress_interval
            _log(f"  ⏳ Still waiting for {label}... ({elapsed}s elapsed)\n")

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


        # IGW must be detached from its VPC before it can be deleted
        if service == "ec2" and record.get("delete_action") == "delete_internet_gateway" and resource_id:
            try:
                resp = await asyncio.to_thread(
                    client.describe_internet_gateways,
                    InternetGatewayIds=[resource_id],
                )
                igws = resp.get("InternetGateways", [])
                if igws:
                    for attachment in igws[0].get("Attachments", []):
                        vpc_id = attachment.get("VpcId")
                        if vpc_id:
                            _log(f"  ↩ Detaching IGW {resource_id} from VPC {vpc_id}...\n")
                            await asyncio.to_thread(
                                client.detach_internet_gateway,
                                InternetGatewayId=resource_id,
                                VpcId=vpc_id,
                            )
            except ClientError as e:
                _log(f"  ⚠ IGW detach warning: {e.response['Error']['Message']}\n")
            except Exception as e:
                _log(f"  ⚠ IGW detach warning: {e}\n")

        # Security Groups — revoke all rules before deletion to avoid dependency errors
        if service == "ec2" and record.get("delete_action") == "delete_security_group" and resource_id:
            try:
                resp = await asyncio.to_thread(
                    client.describe_security_groups,
                    GroupIds=[resource_id],
                )
                sgs = resp.get("SecurityGroups", [])
                if sgs:
                    sg = sgs[0]
                    if sg.get("IpPermissions"):
                        await asyncio.to_thread(
                            client.revoke_security_group_ingress,
                            GroupId=resource_id,
                            IpPermissions=sg["IpPermissions"],
                        )
                    if sg.get("IpPermissionsEgress"):
                        await asyncio.to_thread(
                            client.revoke_security_group_egress,
                            GroupId=resource_id,
                            IpPermissions=sg["IpPermissionsEgress"],
                        )
            except ClientError:
                pass
            except Exception:
                pass

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
