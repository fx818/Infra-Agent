"""Create Elastic Beanstalk Application tool."""
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

    def execute(self, params: dict[str, Any]) -> ToolResult:
        aid = params["app_id"]
        label = params.get("label", aid)
        platform = params.get("platform", "python-3.11")
        inst = params.get("instance_type", "t3.small")

        tf_code = f'''resource "aws_elastic_beanstalk_application" "{aid}" {{
  name        = "${{var.project_name}}-{aid}"
  description = "{label}"
}}

resource "aws_elastic_beanstalk_environment" "{aid}_env" {{
  name                = "${{var.project_name}}-{aid}-env"
  application         = aws_elastic_beanstalk_application.{aid}.name
  solution_stack_name = "64bit Amazon Linux 2023 v4.0.0 running Python 3.11"

  setting {{
    namespace = "aws:autoscaling:launchconfiguration"
    name      = "InstanceType"
    value     = "{inst}"
  }}

  setting {{
    namespace = "aws:elasticbeanstalk:environment"
    name      = "EnvironmentType"
    value     = "{params.get('environment_type', 'LoadBalanced')}"
  }}

  tags = {{ Name = "${{var.project_name}}-{aid}" }}
}}
'''
        return ToolResult(
            node=ToolNode(id=aid, type="aws_elastic_beanstalk", label=label,
                          config=ToolNodeConfig(instance_type=inst, extra={"platform": platform})),
            terraform_code={"compute.tf": tf_code},
        )
