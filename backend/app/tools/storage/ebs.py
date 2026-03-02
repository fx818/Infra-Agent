"""Storage tools: EBS, EFS, FSx, Backup, Glacier, Storage Gateway — provisions via boto3."""
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
        label = params.get("label", vid)
        configs = [{
            "service": "ec2",
            "action": "create_volume",
            "params": {
                "AvailabilityZone": "__REGION__a",
                "Size": params.get("size_gb", 100),
                "VolumeType": params.get("volume_type", "gp3"),
                "Iops": params.get("iops", 3000),
                "TagSpecifications": [{"ResourceType": "volume", "Tags": [{"Key": "Name", "Value": f"__PROJECT__-{vid}"}]}],
            },
            "label": label,
            "resource_type": "aws_ebs_volume",
            "resource_id_path": "VolumeId",
            "delete_action": "delete_volume",
            "delete_params_key": "VolumeId",
        }]
        return ToolResult(
            node=ToolNode(id=vid, type="aws_ebs", label=label,
                          config=ToolNodeConfig(capacity=params.get("size_gb", 100))),
            boto3_config={"ec2": configs},
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
        label = params.get("label", eid)
        configs = [{
            "service": "efs",
            "action": "create_file_system",
            "params": {
                "PerformanceMode": params.get("performance_mode", "generalPurpose"),
                "Encrypted": params.get("encrypted", True),
                "Tags": [{"Key": "Name", "Value": f"__PROJECT__-{eid}"}],
            },
            "label": label,
            "resource_type": "aws_efs",
            "resource_id_path": "FileSystemId",
            "delete_action": "delete_file_system",
            "delete_params_key": "FileSystemId",
        }]
        return ToolResult(
            node=ToolNode(id=eid, type="aws_efs", label=label, config=ToolNodeConfig()),
            boto3_config={"efs": configs},
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
        },
        "required": ["fsx_id", "label"],
    }

    def execute(self, params: dict[str, Any]) -> ToolResult:
        fid = params["fsx_id"]
        label = params.get("label", fid)
        fs_type = params.get("fs_type", "LUSTRE")
        configs = [{
            "service": "fsx",
            "action": "create_file_system",
            "params": {
                "FileSystemType": fs_type,
                "StorageCapacity": params.get("storage_capacity", 1200),
                "SubnetIds": "__DEFAULT_SUBNETS__",
                "Tags": [{"Key": "Name", "Value": f"__PROJECT__-{fid}"}],
            },
            "label": label,
            "resource_type": "aws_fsx",
            "resource_id_path": "FileSystem.FileSystemId",
            "delete_action": "delete_file_system",
            "delete_params_key": "FileSystemId",
        }]
        return ToolResult(
            node=ToolNode(id=fid, type="aws_fsx", label=label,
                          config=ToolNodeConfig(capacity=params.get("storage_capacity", 1200))),
            boto3_config={"fsx": configs},
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
        label = params.get("label", bid)
        configs = [
            {
                "service": "backup",
                "action": "create_backup_vault",
                "params": {
                    "BackupVaultName": f"__PROJECT__-{bid}-vault",
                    "BackupVaultTags": {"Name": f"__PROJECT__-{bid}-vault"},
                },
                "label": f"{label} — Vault",
                "resource_type": "aws_backup_vault",
                "resource_id_path": "BackupVaultName",
                "delete_action": "delete_backup_vault",
                "delete_params": {"BackupVaultName": f"__PROJECT__-{bid}-vault"},
            },
            {
                "service": "backup",
                "action": "create_backup_plan",
                "params": {
                    "BackupPlan": {
                        "BackupPlanName": f"__PROJECT__-{bid}",
                        "Rules": [{
                            "RuleName": f"{bid}-daily",
                            "TargetBackupVaultName": f"__PROJECT__-{bid}-vault",
                            "ScheduleExpression": params.get("schedule", "cron(0 5 ? * * *)"),
                            "Lifecycle": {"DeleteAfterDays": params.get("retention_days", 30)},
                        }],
                    },
                    "BackupPlanTags": {"Name": f"__PROJECT__-{bid}"},
                },
                "label": label,
                "resource_type": "aws_backup_plan",
                "resource_id_path": "BackupPlanId",
                "delete_action": "delete_backup_plan",
                "delete_params_key": "BackupPlanId",
            },
        ]
        return ToolResult(
            node=ToolNode(id=bid, type="aws_backup", label=label, config=ToolNodeConfig()),
            boto3_config={"backup": configs},
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
        label = params.get("label", vid)
        configs = [{
            "service": "glacier",
            "action": "create_vault",
            "params": {"vaultName": f"__PROJECT__-{vid}"},
            "label": label,
            "resource_type": "aws_glacier_vault",
            "resource_id_path": "location",
            "delete_action": "delete_vault",
            "delete_params": {"vaultName": f"__PROJECT__-{vid}"},
        }]
        return ToolResult(
            node=ToolNode(id=vid, type="aws_glacier", label=label, config=ToolNodeConfig()),
            boto3_config={"glacier": configs},
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
        label = params.get("label", gid)
        # Storage Gateway requires physical appliance — this is a lookup/reference
        configs = [{
            "service": "storagegateway",
            "action": "list_gateways",
            "params": {},
            "label": label,
            "resource_type": "aws_storage_gateway",
            "is_lookup": True,
        }]
        return ToolResult(
            node=ToolNode(id=gid, type="aws_storage_gateway", label=label, config=ToolNodeConfig()),
            boto3_config={"storagegateway": configs},
        )
