"""Create Outpost tool — provisions via boto3."""
from typing import Any
from app.tools.base import BaseTool, ToolResult, ToolNode, ToolNodeConfig


class CreateOutpostTool(BaseTool):
    name = "create_outpost"
    description = "Reference an AWS Outpost for running AWS infrastructure on-premises. Creates an Outpost site configuration."
    category = "compute"
    parameters = {
        "type": "object",
        "properties": {
            "outpost_id": {"type": "string", "description": "Unique identifier."},
            "label": {"type": "string"},
            "site_name": {"type": "string", "description": "Physical site name.", "default": "on-prem-dc"},
        },
        "required": ["outpost_id", "label"],
    }

    def execute(self, params: dict[str, Any]) -> ToolResult:
        oid = params["outpost_id"]
        label = params.get("label", oid)
        site_name = params.get("site_name", "on-prem-dc")

        # Outposts require physical hardware — just list existing ones
        configs = [{
            "service": "outposts",
            "action": "list_outposts",
            "params": {},
            "label": label,
            "resource_type": "aws_outposts",
            "is_lookup": True,
        }]

        return ToolResult(
            node=ToolNode(id=oid, type="aws_outposts", label=label,
                          config=ToolNodeConfig(extra={"site_name": site_name})),
            boto3_config={"outposts": configs},
        )
