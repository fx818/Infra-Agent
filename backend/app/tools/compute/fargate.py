"""Create Fargate Profile tool — provisions via boto3."""
import json
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

        configs = [
            {
                "service": "iam",
                "action": "create_role",
                "params": {
                    "RoleName": f"__PROJECT__-{pid}-fargate-role",
                    "AssumeRolePolicyDocument": json.dumps({
                        "Version": "2012-10-17",
                        "Statement": [{"Action": "sts:AssumeRole", "Effect": "Allow", "Principal": {"Service": "eks-fargate-pods.amazonaws.com"}}],
                    }),
                },
                "label": f"{label} — Fargate Role",
                "resource_type": "aws_iam_role",
                "resource_id_path": "Role.Arn",
                "delete_action": "delete_role",
                "delete_params": {"RoleName": f"__PROJECT__-{pid}-fargate-role"},
            },
            {
                "service": "iam",
                "action": "attach_role_policy",
                "params": {
                    "RoleName": f"__PROJECT__-{pid}-fargate-role",
                    "PolicyArn": "arn:aws:iam::aws:policy/AmazonEKSFargatePodExecutionRolePolicy",
                },
                "label": f"{label} — Fargate Policy",
                "resource_type": "aws_iam_policy_attachment",
                "is_support": True,
                "delete_action": "detach_role_policy",
                "delete_params": {"RoleName": f"__PROJECT__-{pid}-fargate-role", "PolicyArn": "arn:aws:iam::aws:policy/AmazonEKSFargatePodExecutionRolePolicy"},
            },
            {
                "service": "eks",
                "action": "create_fargate_profile",
                "params": {
                    "clusterName": f"__PROJECT__-{cluster_id}",
                    "fargateProfileName": f"__PROJECT__-{pid}",
                    "podExecutionRoleArn": f"__RESOLVE__:iam:create_role:{pid}-fargate-role:Role.Arn",
                    "subnets": "__DEFAULT_SUBNETS__",
                    "selectors": [{"namespace": namespace}],
                },
                "label": label,
                "resource_type": "aws_eks_fargate_profile",
                "resource_id_path": "fargateProfile.fargateProfileArn",
                "delete_action": "delete_fargate_profile",
                "delete_params": {"clusterName": f"__PROJECT__-{cluster_id}", "fargateProfileName": f"__PROJECT__-{pid}"},
            },
        ]

        return ToolResult(
            node=ToolNode(id=pid, type="aws_fargate", label=label,
                          config=ToolNodeConfig(extra={"cluster_id": cluster_id, "namespace": namespace})),
            boto3_config={"eks": configs},
            edges=[{"from": cluster_id, "to": pid, "label": "fargate profile"}],
        )
