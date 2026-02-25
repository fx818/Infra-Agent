"""Create RDS Instance tool."""
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
        engine = params.get("engine", "postgres")
        tf_code = f'''resource "aws_db_instance" "{did}" {{
  identifier           = "${{var.project_name}}-{did}"
  engine               = "{engine}"
  engine_version       = "{params.get('engine_version', '16.3')}"
  instance_class       = "{params.get('instance_class', 'db.t3.micro')}"
  allocated_storage    = {params.get('allocated_storage', 20)}
  db_name              = "{params.get('db_name', 'appdb')}"
  username             = "{params.get('username', 'admin')}"
  password             = var.db_password
  multi_az             = {str(params.get('multi_az', False)).lower()}
  skip_final_snapshot  = true
  storage_encrypted    = true
  tags = {{ Name = "${{var.project_name}}-{did}" }}
}}

variable "db_password" {{
  type      = string
  sensitive = true
  default   = "ChangeMe123!"
}}
'''
        return ToolResult(
            node=ToolNode(id=did, type="aws_rds", label=params.get("label", did),
                          config=ToolNodeConfig(engine=engine, instance_type=params.get("instance_class", "db.t3.micro"))),
            terraform_code={"database.tf": tf_code},
        )
