"""AWS ElastiCache tool."""
from typing import Any
from app.tools.base import BaseTool, ToolResult, ToolNode, ToolNodeConfig


class CreateElastiCacheTool(BaseTool):
    name = "create_elasticache"
    description = (
        "Create an Amazon ElastiCache cluster (Redis or Memcached) for in-memory caching, "
        "session management, pub/sub, and real-time leaderboards."
    )
    category = "databases"
    parameters = {
        "type": "object",
        "properties": {
            "cache_id": {"type": "string", "description": "Unique identifier (e.g., 'session_cache')."},
            "label": {"type": "string", "description": "Human-readable label."},
            "engine": {"type": "string", "description": "redis or memcached.", "default": "redis"},
            "node_type": {"type": "string", "description": "Instance type.", "default": "cache.t3.micro"},
            "num_nodes": {"type": "integer", "description": "Number of cache nodes.", "default": 1},
            "vpc_id": {"type": "string", "description": "VPC ID to deploy into.", "default": "main_vpc"},
        },
        "required": ["cache_id", "label"],
    }

    def execute(self, params: dict[str, Any]) -> ToolResult:
        cid = params["cache_id"]
        engine = params.get("engine", "redis")
        node_type = params.get("node_type", "cache.t3.micro")
        num_nodes = params.get("num_nodes", 1)
        vpc_ref = params.get("vpc_id", "main_vpc")

        port = 6379 if engine == "redis" else 11211

        tf_code = f'''
resource "aws_elasticache_subnet_group" "{cid}_subnet_group" {{
  name       = "${{var.project_name}}-{cid}-subnet"
  subnet_ids = [aws_subnet.{vpc_ref}_private_0.id]
}}

resource "aws_elasticache_cluster" "{cid}" {{
  cluster_id           = "${{var.project_name}}-{cid}"
  engine               = "{engine}"
  node_type            = "{node_type}"
  num_cache_nodes      = {num_nodes}
  parameter_group_name = "default.{engine}7"
  port                 = {port}
  subnet_group_name    = aws_elasticache_subnet_group.{cid}_subnet_group.name
  tags                 = {{ Name = "${{var.project_name}}-{cid}" }}
}}
'''
        return ToolResult(
            node=ToolNode(id=cid, type="aws_elasticache", label=params.get("label", cid),
                          config=ToolNodeConfig(extra={"engine": engine, "node_type": node_type})),
            terraform_code={"databases.tf": tf_code},
        )
