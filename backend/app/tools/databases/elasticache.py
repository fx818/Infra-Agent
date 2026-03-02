"""AWS ElastiCache tool — provisions via boto3."""
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
        label = params.get("label", cid)
        engine = params.get("engine", "redis")
        node_type = params.get("node_type", "cache.t3.micro")
        num_nodes = params.get("num_nodes", 1)
        safe_cid = cid.lower().replace("_", "-")
        port = 6379 if engine == "redis" else 11211

        configs = [{
            "service": "elasticache",
            "action": "create_cache_cluster",
            "params": {
                "CacheClusterId": f"__PROJECT__-{safe_cid}",
                "Engine": engine,
                "CacheNodeType": node_type,
                "NumCacheNodes": num_nodes,
                "Port": port,
                "Tags": [{"Key": "Name", "Value": f"__PROJECT__-{safe_cid}"}],
            },
            "label": label,
            "resource_type": "aws_elasticache",
            "resource_id_path": "CacheCluster.CacheClusterId",
            "delete_action": "delete_cache_cluster",
            "delete_params": {"CacheClusterId": f"__PROJECT__-{safe_cid}"},
            "waiter": "cache_cluster_available",
            "waiter_params": {"CacheClusterId": f"__PROJECT__-{safe_cid}"},
        }]

        return ToolResult(
            node=ToolNode(id=cid, type="aws_elasticache", label=label,
                          config=ToolNodeConfig(extra={"engine": engine, "node_type": node_type})),
            boto3_config={"elasticache": configs},
        )
