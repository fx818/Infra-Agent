"""Create EKS Cluster tool."""
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

        tf_code = f'''resource "aws_eks_cluster" "{cid}" {{
  name     = "${{var.project_name}}-{cid}"
  role_arn = aws_iam_role.{cid}_role.arn
  version  = "{k8s_ver}"

  vpc_config {{
    subnet_ids = [for s in aws_subnet.public : s.id]
  }}

  tags = {{ Name = "${{var.project_name}}-{cid}" }}
}}

resource "aws_eks_node_group" "{cid}_nodes" {{
  cluster_name    = aws_eks_cluster.{cid}.name
  node_group_name = "${{var.project_name}}-{cid}-nodes"
  node_role_arn   = aws_iam_role.{cid}_node_role.arn
  subnet_ids      = [for s in aws_subnet.public : s.id]
  instance_types  = ["{inst_type}"]

  scaling_config {{
    desired_size = {desired}
    min_size     = {mn}
    max_size     = {mx}
  }}
}}

resource "aws_iam_role" "{cid}_role" {{
  name = "${{var.project_name}}-{cid}-cluster-role"
  assume_role_policy = jsonencode({{
    Version = "2012-10-17"
    Statement = [{{ Action = "sts:AssumeRole", Effect = "Allow", Principal = {{ Service = "eks.amazonaws.com" }} }}]
  }})
}}

resource "aws_iam_role_policy_attachment" "{cid}_cluster_policy" {{
  role       = aws_iam_role.{cid}_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSClusterPolicy"
}}

resource "aws_iam_role" "{cid}_node_role" {{
  name = "${{var.project_name}}-{cid}-node-role"
  assume_role_policy = jsonencode({{
    Version = "2012-10-17"
    Statement = [{{ Action = "sts:AssumeRole", Effect = "Allow", Principal = {{ Service = "ec2.amazonaws.com" }} }}]
  }})
}}

resource "aws_iam_role_policy_attachment" "{cid}_worker_policy" {{
  role       = aws_iam_role.{cid}_node_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy"
}}

resource "aws_iam_role_policy_attachment" "{cid}_cni_policy" {{
  role       = aws_iam_role.{cid}_node_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy"
}}

resource "aws_iam_role_policy_attachment" "{cid}_ecr_policy" {{
  role       = aws_iam_role.{cid}_node_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
}}
'''
        return ToolResult(
            node=ToolNode(id=cid, type="aws_eks", label=label,
                          config=ToolNodeConfig(instance_type=inst_type, extra={"kubernetes_version": k8s_ver, "desired_nodes": desired})),
            terraform_code={"compute.tf": tf_code},
        )
