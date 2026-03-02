"""Create RDS Instance tool — provisions via boto3."""
from typing import Any
from app.tools.base import BaseTool, ToolResult, ToolNode, ToolNodeConfig


class CreateRDSInstanceTool(BaseTool):
    name = "create_rds_instance"
    description = "Create an Amazon RDS database instance (MySQL, PostgreSQL, MariaDB, SQL Server, Oracle)."
    category = "databases"
    parameters = {
        "type": "object",
        "properties": {
            "db_id": {"type": "string"}, "label": {"type": "string"},
            "engine": {"type": "string", "description": "'mysql', 'postgres', 'mariadb', 'sqlserver-ex', 'oracle-ee'.", "default": "postgres"},
            "engine_version": {"type": "string", "default": "16.3"},
            "instance_class": {"type": "string", "default": "db.t3.micro"},
            "allocated_storage": {"type": "integer", "default": 20},
            "multi_az": {"type": "boolean", "default": False},
            "db_name": {"type": "string", "default": "appdb"},
            "username": {"type": "string", "default": "admin"},
        },
        "required": ["db_id", "label"],
    }

    def execute(self, params: dict[str, Any]) -> ToolResult:
        did = params["db_id"]
        label = params.get("label", did)
        engine = params.get("engine", "postgres")
        configs = [{
            "service": "rds",
            "action": "create_db_instance",
            "params": {
                "DBInstanceIdentifier": f"__PROJECT__-{did}",
                "Engine": engine,
                "EngineVersion": params.get("engine_version", "16.3"),
                "DBInstanceClass": params.get("instance_class", "db.t3.micro"),
                "AllocatedStorage": params.get("allocated_storage", 20),
                "DBName": params.get("db_name", "appdb"),
                "MasterUsername": params.get("username", "admin"),
                "MasterUserPassword": "ChangeMe123!",
                "MultiAZ": params.get("multi_az", False),
                "StorageEncrypted": True,
                "PubliclyAccessible": False,
                "BackupRetentionPeriod": 7,
                "Tags": [{"Key": "Name", "Value": f"__PROJECT__-{did}"}],
            },
            "label": label,
            "resource_type": "aws_rds",
            "resource_id_path": "DBInstance.DBInstanceIdentifier",
            "delete_action": "delete_db_instance",
            "delete_params": {
                "DBInstanceIdentifier": f"__PROJECT__-{did}",
                "SkipFinalSnapshot": True,
                "DeleteAutomatedBackups": True,
            },
            "waiter": "db_instance_available",
            "waiter_params": {"DBInstanceIdentifier": f"__PROJECT__-{did}"},
        }]
        return ToolResult(
            node=ToolNode(id=did, type="aws_rds", label=label,
                          config=ToolNodeConfig(engine=engine, instance_type=params.get("instance_class", "db.t3.micro"))),
            boto3_config={"rds": configs},
        )
