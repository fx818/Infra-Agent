"""Create EBS Volume, EFS Filesystem, FSx, Backup, Glacier, Storage Gateway tools."""
from typing import Any
from app.tools.base import BaseTool, ToolResult, ToolNode, ToolNodeConfig


class CreateEBSVolumeTool(BaseTool):
    name = "create_ebs_volume"
    description = "Create an Amazon EBS volume for persistent block storage."
    category = "storage"
    parameters = {
        "type": "object",
        "properties": {
            "volume_id": {"type": "string"}, "label": {"type": "string"},
            "size_gb": {"type": "integer", "default": 100},
            "volume_type": {"type": "string", "description": "'gp3', 'gp2', 'io1', 'io2', 'st1', 'sc1'.", "default": "gp3"},
            "iops": {"type": "integer", "default": 3000},
        },
        "required": ["volume_id", "label"],
    }

    def execute(self, params: dict[str, Any]) -> ToolResult:
        vid = params["volume_id"]
        tf_code = f'''resource "aws_ebs_volume" "{vid}" {{
  availability_zone = "${{var.region}}a"
  size              = {params.get('size_gb', 100)}
  type              = "{params.get('volume_type', 'gp3')}"
  iops              = {params.get('iops', 3000)}
  tags = {{ Name = "${{var.project_name}}-{vid}" }}
}}
'''
        return ToolResult(
            node=ToolNode(id=vid, type="aws_ebs", label=params.get("label", vid),
                          config=ToolNodeConfig(capacity=params.get("size_gb", 100))),
            terraform_code={"storage.tf": tf_code},
        )


class CreateEFSFilesystemTool(BaseTool):
    name = "create_efs_filesystem"
    description = "Create an Amazon EFS file system for shared, scalable file storage."
    category = "storage"
    parameters = {
        "type": "object",
        "properties": {
            "efs_id": {"type": "string"}, "label": {"type": "string"},
            "performance_mode": {"type": "string", "default": "generalPurpose"},
            "encrypted": {"type": "boolean", "default": True},
        },
        "required": ["efs_id", "label"],
    }

    def execute(self, params: dict[str, Any]) -> ToolResult:
        eid = params["efs_id"]
        tf_code = f'''resource "aws_efs_file_system" "{eid}" {{
  performance_mode = "{params.get('performance_mode', 'generalPurpose')}"
  encrypted        = {str(params.get('encrypted', True)).lower()}
  tags = {{ Name = "${{var.project_name}}-{eid}" }}
}}
'''
        return ToolResult(
            node=ToolNode(id=eid, type="aws_efs", label=params.get("label", eid), config=ToolNodeConfig()),
            terraform_code={"storage.tf": tf_code},
        )


class CreateFSxFilesystemTool(BaseTool):
    name = "create_fsx_filesystem"
    description = "Create an Amazon FSx file system (Lustre, Windows, ONTAP, or OpenZFS)."
    category = "storage"
    parameters = {
        "type": "object",
        "properties": {
            "fsx_id": {"type": "string"}, "label": {"type": "string"},
            "fs_type": {"type": "string", "description": "'LUSTRE', 'WINDOWS', 'ONTAP', 'OPENZFS'.", "default": "LUSTRE"},
            "storage_capacity": {"type": "integer", "default": 1200},
            "subnet_ref": {"type": "string", "default": "aws_subnet.private_0.id"},
        },
        "required": ["fsx_id", "label"],
    }

    def execute(self, params: dict[str, Any]) -> ToolResult:
        fid = params["fsx_id"]
        fs_type = params.get("fs_type", "LUSTRE")
        tf_resource = "aws_fsx_lustre_file_system" if fs_type == "LUSTRE" else "aws_fsx_windows_file_system"
        tf_code = f'''resource "{tf_resource}" "{fid}" {{
  storage_capacity = {params.get('storage_capacity', 1200)}
  subnet_ids       = [{params.get('subnet_ref', 'aws_subnet.private_0.id')}]
  tags = {{ Name = "${{var.project_name}}-{fid}" }}
}}
'''
        return ToolResult(
            node=ToolNode(id=fid, type="aws_fsx", label=params.get("label", fid),
                          config=ToolNodeConfig(capacity=params.get("storage_capacity", 1200))),
            terraform_code={"storage.tf": tf_code},
        )


class CreateBackupPlanTool(BaseTool):
    name = "create_backup_plan"
    description = "Create an AWS Backup plan with a backup vault for automated resource backups."
    category = "storage"
    parameters = {
        "type": "object",
        "properties": {
            "backup_id": {"type": "string"}, "label": {"type": "string"},
            "schedule": {"type": "string", "description": "Cron expression.", "default": "cron(0 5 ? * * *)"},
            "retention_days": {"type": "integer", "default": 30},
        },
        "required": ["backup_id", "label"],
    }

    def execute(self, params: dict[str, Any]) -> ToolResult:
        bid = params["backup_id"]
        tf_code = f'''resource "aws_backup_vault" "{bid}_vault" {{
  name = "${{var.project_name}}-{bid}-vault"
}}

resource "aws_backup_plan" "{bid}" {{
  name = "${{var.project_name}}-{bid}"
  rule {{
    rule_name         = "{bid}-daily"
    target_vault_name = aws_backup_vault.{bid}_vault.name
    schedule          = "{params.get('schedule', 'cron(0 5 ? * * *)')}"
    lifecycle {{ delete_after = {params.get('retention_days', 30)} }}
  }}
}}
'''
        return ToolResult(
            node=ToolNode(id=bid, type="aws_backup", label=params.get("label", bid), config=ToolNodeConfig()),
            terraform_code={"storage.tf": tf_code},
        )


class CreateGlacierVaultTool(BaseTool):
    name = "create_glacier_vault"
    description = "Create an Amazon S3 Glacier vault for long-term archival storage."
    category = "storage"
    parameters = {
        "type": "object",
        "properties": {
            "vault_id": {"type": "string"}, "label": {"type": "string"},
        },
        "required": ["vault_id", "label"],
    }

    def execute(self, params: dict[str, Any]) -> ToolResult:
        vid = params["vault_id"]
        tf_code = f'''resource "aws_glacier_vault" "{vid}" {{
  name = "${{var.project_name}}-{vid}"
  tags = {{ Name = "${{var.project_name}}-{vid}" }}
}}
'''
        return ToolResult(
            node=ToolNode(id=vid, type="aws_glacier", label=params.get("label", vid), config=ToolNodeConfig()),
            terraform_code={"storage.tf": tf_code},
        )


class CreateStorageGatewayTool(BaseTool):
    name = "create_storage_gateway"
    description = "Create an AWS Storage Gateway for hybrid cloud storage integration."
    category = "storage"
    parameters = {
        "type": "object",
        "properties": {
            "gw_id": {"type": "string"}, "label": {"type": "string"},
            "gateway_type": {"type": "string", "description": "'FILE_S3', 'FILE_FSX_SMB', 'STORED', 'CACHED', 'VTL'.", "default": "FILE_S3"},
        },
        "required": ["gw_id", "label"],
    }

    def execute(self, params: dict[str, Any]) -> ToolResult:
        gid = params["gw_id"]
        tf_code = f'''# Storage Gateway requires a VM/appliance activation.
# This creates the gateway resource reference.
resource "aws_storagegateway_gateway" "{gid}" {{
  gateway_name       = "${{var.project_name}}-{gid}"
  gateway_timezone   = "GMT"
  gateway_type       = "{params.get('gateway_type', 'FILE_S3')}"
  tags = {{ Name = "${{var.project_name}}-{gid}" }}
}}
'''
        return ToolResult(
            node=ToolNode(id=gid, type="aws_storage_gateway", label=params.get("label", gid), config=ToolNodeConfig()),
            terraform_code={"storage.tf": tf_code},
        )
