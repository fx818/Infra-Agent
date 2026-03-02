"""Create Elastic Beanstalk Application tool — provisions via boto3."""
from typing import Any
from app.tools.base import BaseTool, ToolResult, ToolNode, ToolNodeConfig


class CreateElasticBeanstalkAppTool(BaseTool):
    name = "create_elastic_beanstalk_app"
    description = (
        "Create an AWS Elastic Beanstalk application and environment. "
        "Simplifies deploying web applications with automatic scaling, "
        "load balancing, and monitoring."
    )
    category = "compute"
    parameters = {
        "type": "object",
        "properties": {
            "app_id": {"type": "string", "description": "Unique identifier."},
            "label": {"type": "string", "description": "Human-readable label."},
            "platform": {"type": "string", "description": "Platform (e.g., 'python-3.11', 'node-18', 'docker').", "default": "python-3.11"},
            "instance_type": {"type": "string", "default": "t3.small"},
            "environment_type": {"type": "string", "description": "'SingleInstance' or 'LoadBalanced'.", "default": "LoadBalanced"},
        },
        "required": ["app_id", "label"],
    }

    # Map of short platform names to EB solution stack names
    _PLATFORM_MAP = {
        "python-3.11": "64bit Amazon Linux 2023 v4.0.0 running Python 3.11",
        "python-3.12": "64bit Amazon Linux 2023 v4.1.0 running Python 3.12",
        "node-18": "64bit Amazon Linux 2023 v6.0.0 running Node.js 18",
        "docker": "64bit Amazon Linux 2023 v4.0.0 running Docker",
    }

    def execute(self, params: dict[str, Any]) -> ToolResult:
        aid = params["app_id"]
        label = params.get("label", aid)
        platform = params.get("platform", "python-3.11")
        inst = params.get("instance_type", "t3.small")
        env_type = params.get("environment_type", "LoadBalanced")

        configs = [
            {
                "service": "elasticbeanstalk",
                "action": "create_application",
                "params": {
                    "ApplicationName": f"__PROJECT__-{aid}",
                    "Description": label,
                    "Tags": [{"Key": "Name", "Value": f"__PROJECT__-{aid}"}],
                },
                "label": f"{label} — Application",
                "resource_type": "aws_elastic_beanstalk_application",
                "resource_id_path": "Application.ApplicationName",
                "delete_action": "delete_application",
                "delete_params": {"ApplicationName": f"__PROJECT__-{aid}", "TerminateEnvByForce": True},
            },
            {
                "service": "elasticbeanstalk",
                "action": "create_environment",
                "params": {
                    "ApplicationName": f"__PROJECT__-{aid}",
                    "EnvironmentName": f"__PROJECT__-{aid}-env",
                    "SolutionStackName": self._PLATFORM_MAP.get(platform, platform),
                    "OptionSettings": [
                        {"Namespace": "aws:autoscaling:launchconfiguration", "OptionName": "InstanceType", "Value": inst},
                        {"Namespace": "aws:elasticbeanstalk:environment", "OptionName": "EnvironmentType", "Value": env_type},
                    ],
                    "Tags": [{"Key": "Name", "Value": f"__PROJECT__-{aid}"}],
                },
                "label": label,
                "resource_type": "aws_elastic_beanstalk_environment",
                "resource_id_path": "EnvironmentId",
                "delete_action": "terminate_environment",
                "delete_params_key": "EnvironmentName",
            },
        ]

        return ToolResult(
            node=ToolNode(id=aid, type="aws_elastic_beanstalk", label=label,
                          config=ToolNodeConfig(instance_type=inst, extra={"platform": platform})),
            boto3_config={"elasticbeanstalk": configs},
        )
