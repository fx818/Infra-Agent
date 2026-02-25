"""Create Outpost tool."""
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
        tf_code = f'''# AWS Outposts — configuration reference
# Note: Outposts require physical hardware provisioning via AWS console.
# This resource references the outpost for use by other services.

data "aws_outposts_outposts" "{oid}" {{}}

output "{oid}_outpost_arns" {{
  value = data.aws_outposts_outposts.{oid}.arns
}}
'''
        return ToolResult(
            node=ToolNode(id=oid, type="aws_outposts", label=params.get("label", oid),
                          config=ToolNodeConfig(extra={"site_name": params.get("site_name", "on-prem-dc")})),
            terraform_code={"compute.tf": tf_code},
        )
