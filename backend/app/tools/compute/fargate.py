"""Create Fargate Profile tool."""
from typing import Any
from app.tools.base import BaseTool, ToolResult, ToolNode, ToolNodeConfig


class CreateFargateProfileTool(BaseTool):
    name = "create_fargate_profile"
    description = (
        "Create an AWS Fargate profile for ECS or EKS. Fargate removes the need to "
        "manage EC2 instances — containers run serverlessly."
    )
    category = "compute"
    parameters = {
        "type": "object",
        "properties": {
            "profile_id": {"type": "string", "description": "Unique identifier."},
            "label": {"type": "string", "description": "Human-readable label."},
            "cluster_id": {"type": "string", "description": "EKS cluster ID this profile belongs to."},
            "namespace": {"type": "string", "description": "Kubernetes namespace to run on Fargate.", "default": "default"},
        },
        "required": ["profile_id", "label", "cluster_id"],
    }

    def execute(self, params: dict[str, Any]) -> ToolResult:
        pid = params["profile_id"]
        label = params.get("label", pid)
        cluster_id = params["cluster_id"]
        namespace = params.get("namespace", "default")

        tf_code = f'''resource "aws_eks_fargate_profile" "{pid}" {{
  cluster_name           = aws_eks_cluster.{cluster_id}.name
  fargate_profile_name   = "${{var.project_name}}-{pid}"
  pod_execution_role_arn = aws_iam_role.{pid}_fargate_role.arn
  subnet_ids             = [for s in aws_subnet.private : s.id]

  selector {{
    namespace = "{namespace}"
  }}
}}

resource "aws_iam_role" "{pid}_fargate_role" {{
  name = "${{var.project_name}}-{pid}-fargate-role"
  assume_role_policy = jsonencode({{
    Version = "2012-10-17"
    Statement = [{{ Action = "sts:AssumeRole", Effect = "Allow", Principal = {{ Service = "eks-fargate-pods.amazonaws.com" }} }}]
  }})
}}

resource "aws_iam_role_policy_attachment" "{pid}_fargate_policy" {{
  role       = aws_iam_role.{pid}_fargate_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSFargatePodExecutionRolePolicy"
}}
'''
        return ToolResult(
            node=ToolNode(id=pid, type="aws_fargate", label=label,
                          config=ToolNodeConfig(extra={"cluster_id": cluster_id, "namespace": namespace})),
            terraform_code={"compute.tf": tf_code},
            edges=[{"from": cluster_id, "to": pid, "label": "fargate profile"}],
        )
