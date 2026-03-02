"""Create Lightsail Instance tool — provisions via boto3."""
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
        label = params.get("label", iid)
        blueprint = params.get("blueprint_id", "amazon_linux_2")
        bundle = params.get("bundle_id", "nano_3_0")

        configs = [{
            "service": "lightsail",
            "action": "create_instances",
            "params": {
                "instanceNames": [f"__PROJECT__-{iid}"],
                "availabilityZone": "__REGION__a",
                "blueprintId": blueprint,
                "bundleId": bundle,
                "tags": [{"key": "Name", "value": f"__PROJECT__-{iid}"}],
            },
            "label": label,
            "resource_type": "aws_lightsail_instance",
            "resource_id_path": "operations[0].resourceName",
            "delete_action": "delete_instance",
            "delete_params": {"instanceName": f"__PROJECT__-{iid}"},
        }]

        return ToolResult(
            node=ToolNode(id=iid, type="aws_lightsail", label=label,
                          config=ToolNodeConfig(extra={"blueprint": blueprint})),
            boto3_config={"lightsail": configs},
        )
