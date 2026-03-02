"""Create EKS Cluster tool — provisions via boto3."""
import json
from typing import Any
from app.tools.base import BaseTool, ToolResult, ToolNode, ToolNodeConfig


class CreateEKSClusterTool(BaseTool):
    name = "create_eks_cluster"
    description = (
        "Create an Amazon EKS (Elastic Kubernetes Service) cluster with managed node groups. "
        "Ideal for running Kubernetes workloads at scale."
    )
    category = "compute"
    parameters = {
        "type": "object",
        "properties": {
            "cluster_id": {"type": "string", "description": "Unique identifier (e.g., 'k8s_cluster')."},
            "label": {"type": "string", "description": "Human-readable label."},
            "kubernetes_version": {"type": "string", "description": "Kubernetes version.", "default": "1.29"},
            "node_instance_type": {"type": "string", "description": "Instance type for worker nodes.", "default": "t3.medium"},
            "desired_nodes": {"type": "integer", "description": "Desired number of worker nodes.", "default": 2},
            "min_nodes": {"type": "integer", "description": "Minimum nodes.", "default": 1},
            "max_nodes": {"type": "integer", "description": "Maximum nodes.", "default": 4},
        },
        "required": ["cluster_id", "label"],
    }

    def execute(self, params: dict[str, Any]) -> ToolResult:
        cid = params["cluster_id"]
        label = params.get("label", cid)
        k8s_ver = params.get("kubernetes_version", "1.29")
        inst_type = params.get("node_instance_type", "t3.medium")
        desired = params.get("desired_nodes", 2)
        mn = params.get("min_nodes", 1)
        mx = params.get("max_nodes", 4)

        configs = [
            # 1. EKS cluster IAM role
            {
                "service": "iam",
                "action": "create_role",
                "params": {
                    "RoleName": f"__PROJECT__-{cid}-cluster-role",
                    "AssumeRolePolicyDocument": json.dumps({
                        "Version": "2012-10-17",
                        "Statement": [{"Action": "sts:AssumeRole", "Effect": "Allow", "Principal": {"Service": "eks.amazonaws.com"}}],
                    }),
                },
                "label": f"{label} — Cluster Role",
                "resource_type": "aws_iam_role",
                "resource_id_path": "Role.Arn",
                "delete_action": "delete_role",
                "delete_params": {"RoleName": f"__PROJECT__-{cid}-cluster-role"},
            },
            {
                "service": "iam",
                "action": "attach_role_policy",
                "params": {
                    "RoleName": f"__PROJECT__-{cid}-cluster-role",
                    "PolicyArn": "arn:aws:iam::aws:policy/AmazonEKSClusterPolicy",
                },
                "label": f"{label} — Cluster Policy",
                "resource_type": "aws_iam_policy_attachment",
                "is_support": True,
                "delete_action": "detach_role_policy",
                "delete_params": {"RoleName": f"__PROJECT__-{cid}-cluster-role", "PolicyArn": "arn:aws:iam::aws:policy/AmazonEKSClusterPolicy"},
            },
            # 2. Node group IAM role
            {
                "service": "iam",
                "action": "create_role",
                "params": {
                    "RoleName": f"__PROJECT__-{cid}-node-role",
                    "AssumeRolePolicyDocument": json.dumps({
                        "Version": "2012-10-17",
                        "Statement": [{"Action": "sts:AssumeRole", "Effect": "Allow", "Principal": {"Service": "ec2.amazonaws.com"}}],
                    }),
                },
                "label": f"{label} — Node Role",
                "resource_type": "aws_iam_role",
                "resource_id_path": "Role.Arn",
                "delete_action": "delete_role",
                "delete_params": {"RoleName": f"__PROJECT__-{cid}-node-role"},
            },
            {
                "service": "iam",
                "action": "attach_role_policy",
                "params": {"RoleName": f"__PROJECT__-{cid}-node-role", "PolicyArn": "arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy"},
                "label": f"{label} — Worker Policy", "resource_type": "aws_iam_policy_attachment", "is_support": True,
                "delete_action": "detach_role_policy",
                "delete_params": {"RoleName": f"__PROJECT__-{cid}-node-role", "PolicyArn": "arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy"},
            },
            {
                "service": "iam",
                "action": "attach_role_policy",
                "params": {"RoleName": f"__PROJECT__-{cid}-node-role", "PolicyArn": "arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy"},
                "label": f"{label} — CNI Policy", "resource_type": "aws_iam_policy_attachment", "is_support": True,
                "delete_action": "detach_role_policy",
                "delete_params": {"RoleName": f"__PROJECT__-{cid}-node-role", "PolicyArn": "arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy"},
            },
            {
                "service": "iam",
                "action": "attach_role_policy",
                "params": {"RoleName": f"__PROJECT__-{cid}-node-role", "PolicyArn": "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"},
                "label": f"{label} — ECR Policy", "resource_type": "aws_iam_policy_attachment", "is_support": True,
                "delete_action": "detach_role_policy",
                "delete_params": {"RoleName": f"__PROJECT__-{cid}-node-role", "PolicyArn": "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"},
            },
            # 3. Create EKS cluster
            {
                "service": "eks",
                "action": "create_cluster",
                "params": {
                    "name": f"__PROJECT__-{cid}",
                    "version": k8s_ver,
                    "roleArn": f"__RESOLVE__:iam:create_role:{cid}-cluster-role:Role.Arn",
                    "resourcesVpcConfig": {"subnetIds": "__DEFAULT_SUBNETS__"},
                    "tags": {"Name": f"__PROJECT__-{cid}"},
                },
                "label": label,
                "resource_type": "aws_eks_cluster",
                "resource_id_path": "cluster.arn",
                "delete_action": "delete_cluster",
                "delete_params": {"name": f"__PROJECT__-{cid}"},
                "waiter": "cluster_active",
            },
            # 4. Create node group
            {
                "service": "eks",
                "action": "create_nodegroup",
                "params": {
                    "clusterName": f"__PROJECT__-{cid}",
                    "nodegroupName": f"__PROJECT__-{cid}-nodes",
                    "nodeRole": f"__RESOLVE__:iam:create_role:{cid}-node-role:Role.Arn",
                    "subnets": "__DEFAULT_SUBNETS__",
                    "instanceTypes": [inst_type],
                    "scalingConfig": {"desiredSize": desired, "minSize": mn, "maxSize": mx},
                },
                "label": f"{label} — Node Group",
                "resource_type": "aws_eks_node_group",
                "resource_id_path": "nodegroup.nodegroupArn",
                "delete_action": "delete_nodegroup",
                "delete_params": {"clusterName": f"__PROJECT__-{cid}", "nodegroupName": f"__PROJECT__-{cid}-nodes"},
                "waiter": "nodegroup_active",
            },
        ]

        return ToolResult(
            node=ToolNode(id=cid, type="aws_eks", label=label,
                          config=ToolNodeConfig(instance_type=inst_type, extra={"kubernetes_version": k8s_ver, "desired_nodes": desired})),
            boto3_config={"eks": configs},
        )
