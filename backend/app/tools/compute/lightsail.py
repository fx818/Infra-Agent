"""Create Lightsail Instance tool."""
from typing import Any
from app.tools.base import BaseTool, ToolResult, ToolNode, ToolNodeConfig


class CreateLightsailInstanceTool(BaseTool):
    name = "create_lightsail_instance"
    description = "Create an Amazon Lightsail instance — simple VPS for small applications, blogs, dev environments."
    category = "compute"
    parameters = {
        "type": "object",
        "properties": {
            "instance_id": {"type": "string", "description": "Unique identifier."},
            "label": {"type": "string"},
            "blueprint_id": {"type": "string", "description": "OS/app blueprint (e.g., 'amazon_linux_2', 'ubuntu_22_04', 'wordpress').", "default": "amazon_linux_2"},
            "bundle_id": {"type": "string", "description": "Instance plan (e.g., 'nano_3_0', 'micro_3_0', 'small_3_0').", "default": "nano_3_0"},
        },
        "required": ["instance_id", "label"],
    }

    def execute(self, params: dict[str, Any]) -> ToolResult:
        iid = params["instance_id"]
        tf_code = f'''resource "aws_lightsail_instance" "{iid}" {{
  name              = "${{var.project_name}}-{iid}"
  availability_zone = "${{var.region}}a"
  blueprint_id      = "{params.get('blueprint_id', 'amazon_linux_2')}"
  bundle_id         = "{params.get('bundle_id', 'nano_3_0')}"
  tags = {{ Name = "${{var.project_name}}-{iid}" }}
}}
'''
        return ToolResult(
            node=ToolNode(id=iid, type="aws_lightsail", label=params.get("label", iid),
                          config=ToolNodeConfig(extra={"blueprint": params.get("blueprint_id", "amazon_linux_2")})),
            terraform_code={"compute.tf": tf_code},
        )
