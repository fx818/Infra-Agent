"""Create AWS Batch Job tool."""
from typing import Any
from app.tools.base import BaseTool, ToolResult, ToolNode, ToolNodeConfig


class CreateBatchJobTool(BaseTool):
    name = "create_batch_job"
    description = "Create an AWS Batch compute environment and job queue for batch processing workloads."
    category = "compute"
    parameters = {
        "type": "object",
        "properties": {
            "batch_id": {"type": "string", "description": "Unique identifier."},
            "label": {"type": "string"},
            "compute_type": {"type": "string", "description": "'FARGATE' or 'EC2'.", "default": "FARGATE"},
            "max_vcpus": {"type": "integer", "default": 16},
        },
        "required": ["batch_id", "label"],
    }

    def execute(self, params: dict[str, Any]) -> ToolResult:
        bid = params["batch_id"]
        ctype = params.get("compute_type", "FARGATE")
        vcpus = params.get("max_vcpus", 16)
        tf_code = f'''resource "aws_batch_compute_environment" "{bid}" {{
  compute_environment_name = "${{var.project_name}}-{bid}"
  type                     = "MANAGED"
  compute_resources {{
    type      = "{ctype}"
    max_vcpus = {vcpus}
    subnets   = [for s in aws_subnet.public : s.id]
    security_group_ids = []
  }}
  service_role = aws_iam_role.{bid}_batch_role.arn
}}

resource "aws_batch_job_queue" "{bid}_queue" {{
  name     = "${{var.project_name}}-{bid}-queue"
  state    = "ENABLED"
  priority = 1
  compute_environment_order {{
    order               = 1
    compute_environment = aws_batch_compute_environment.{bid}.arn
  }}
}}

resource "aws_iam_role" "{bid}_batch_role" {{
  name = "${{var.project_name}}-{bid}-batch-role"
  assume_role_policy = jsonencode({{
    Version = "2012-10-17"
    Statement = [{{ Action = "sts:AssumeRole", Effect = "Allow", Principal = {{ Service = "batch.amazonaws.com" }} }}]
  }})
}}

resource "aws_iam_role_policy_attachment" "{bid}_batch_policy" {{
  role       = aws_iam_role.{bid}_batch_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSBatchServiceRole"
}}
'''
        return ToolResult(
            node=ToolNode(id=bid, type="aws_batch", label=params.get("label", bid),
                          config=ToolNodeConfig(extra={"compute_type": ctype, "max_vcpus": vcpus})),
            terraform_code={"compute.tf": tf_code},
        )
