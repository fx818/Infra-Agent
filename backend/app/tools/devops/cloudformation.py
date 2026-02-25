"""DevOps tools: CloudFormation, SSM, CodePipeline, CodeBuild, CodeCommit, CodeDeploy, ECR, CodeArtifact."""
from typing import Any
from app.tools.base import BaseTool, ToolResult, ToolNode, ToolNodeConfig


class CreateCloudFormationStackTool(BaseTool):
    name = "create_cloudformation_stack"
    description = "Create an AWS CloudFormation stack for IaC orchestration."
    category = "devops"
    parameters = {
        "type": "object",
        "properties": {
            "stack_id": {"type": "string"}, "label": {"type": "string"},
            "template_url": {"type": "string", "description": "S3 URL of the CloudFormation template.", "default": ""},
        },
        "required": ["stack_id", "label"],
    }

    def execute(self, params: dict[str, Any]) -> ToolResult:
        sid = params["stack_id"]
        tf_code = f'''resource "aws_cloudformation_stack" "{sid}" {{
  name = "${{var.project_name}}-{sid}"
  template_body = jsonencode({{
    AWSTemplateFormatVersion = "2010-09-09"
    Description = "{params.get('label', sid)}"
    Resources = {{}}
  }})
  tags = {{ Name = "${{var.project_name}}-{sid}" }}
}}
'''
        return ToolResult(
            node=ToolNode(id=sid, type="aws_cloudformation", label=params.get("label", sid), config=ToolNodeConfig()),
            terraform_code={"devops.tf": tf_code},
        )


class CreateSSMParameterTool(BaseTool):
    name = "create_ssm_parameter"
    description = "Create an AWS Systems Manager Parameter Store parameter for configuration management."
    category = "devops"
    parameters = {
        "type": "object",
        "properties": {
            "param_id": {"type": "string"}, "label": {"type": "string"},
            "param_type": {"type": "string", "description": "'String', 'StringList', 'SecureString'.", "default": "String"},
            "value": {"type": "string", "default": "placeholder"},
        },
        "required": ["param_id", "label"],
    }

    def execute(self, params: dict[str, Any]) -> ToolResult:
        pid = params["param_id"]
        tf_code = f'''resource "aws_ssm_parameter" "{pid}" {{
  name  = "/${{var.project_name}}/{pid}"
  type  = "{params.get('param_type', 'String')}"
  value = "{params.get('value', 'placeholder')}"
  tags = {{ Name = "${{var.project_name}}-{pid}" }}
}}
'''
        return ToolResult(
            node=ToolNode(id=pid, type="aws_ssm", label=params.get("label", pid), config=ToolNodeConfig()),
            terraform_code={"devops.tf": tf_code},
        )


class CreateCodePipelineTool(BaseTool):
    name = "create_codepipeline"
    description = "Create an AWS CodePipeline for CI/CD automation."
    category = "devops"
    parameters = {
        "type": "object",
        "properties": {
            "pipeline_id": {"type": "string"}, "label": {"type": "string"},
        },
        "required": ["pipeline_id", "label"],
    }

    def execute(self, params: dict[str, Any]) -> ToolResult:
        pid = params["pipeline_id"]
        tf_code = f'''resource "aws_codepipeline" "{pid}" {{
  name     = "${{var.project_name}}-{pid}"
  role_arn = aws_iam_role.{pid}_pipeline_role.arn

  artifact_store {{
    location = aws_s3_bucket.{pid}_artifacts.id
    type     = "S3"
  }}

  stage {{
    name = "Source"
    action {{
      name             = "Source"
      category         = "Source"
      owner            = "AWS"
      provider         = "CodeCommit"
      version          = "1"
      output_artifacts = ["source"]
      configuration = {{ RepositoryName = "${{var.project_name}}", BranchName = "main" }}
    }}
  }}

  stage {{
    name = "Build"
    action {{
      name            = "Build"
      category        = "Build"
      owner           = "AWS"
      provider        = "CodeBuild"
      version         = "1"
      input_artifacts = ["source"]
      configuration = {{ ProjectName = "${{var.project_name}}-build" }}
    }}
  }}
}}

resource "aws_s3_bucket" "{pid}_artifacts" {{
  bucket = "${{var.project_name}}-{pid}-artifacts"
}}

resource "aws_iam_role" "{pid}_pipeline_role" {{
  name = "${{var.project_name}}-{pid}-pipeline-role"
  assume_role_policy = jsonencode({{
    Version = "2012-10-17"
    Statement = [{{ Action = "sts:AssumeRole", Effect = "Allow", Principal = {{ Service = "codepipeline.amazonaws.com" }} }}]
  }})
}}
'''
        return ToolResult(
            node=ToolNode(id=pid, type="aws_codepipeline", label=params.get("label", pid), config=ToolNodeConfig()),
            terraform_code={"devops.tf": tf_code},
        )


class CreateCodeBuildProjectTool(BaseTool):
    name = "create_codebuild_project"
    description = "Create an AWS CodeBuild project for building and testing code."
    category = "devops"
    parameters = {
        "type": "object",
        "properties": {
            "build_id": {"type": "string"}, "label": {"type": "string"},
            "compute_type": {"type": "string", "default": "BUILD_GENERAL1_SMALL"},
            "image": {"type": "string", "default": "aws/codebuild/amazonlinux2-x86_64-standard:5.0"},
        },
        "required": ["build_id", "label"],
    }

    def execute(self, params: dict[str, Any]) -> ToolResult:
        bid = params["build_id"]
        tf_code = f'''resource "aws_codebuild_project" "{bid}" {{
  name         = "${{var.project_name}}-{bid}"
  service_role = aws_iam_role.{bid}_build_role.arn

  artifacts {{ type = "NO_ARTIFACTS" }}

  environment {{
    compute_type    = "{params.get('compute_type', 'BUILD_GENERAL1_SMALL')}"
    image           = "{params.get('image', 'aws/codebuild/amazonlinux2-x86_64-standard:5.0')}"
    type            = "LINUX_CONTAINER"
  }}

  source {{ type = "NO_SOURCE", buildspec = "version: 0.2\\nphases:\\n  build:\\n    commands:\\n      - echo Build started" }}
  tags = {{ Name = "${{var.project_name}}-{bid}" }}
}}

resource "aws_iam_role" "{bid}_build_role" {{
  name = "${{var.project_name}}-{bid}-role"
  assume_role_policy = jsonencode({{
    Version = "2012-10-17"
    Statement = [{{ Action = "sts:AssumeRole", Effect = "Allow", Principal = {{ Service = "codebuild.amazonaws.com" }} }}]
  }})
}}
'''
        return ToolResult(
            node=ToolNode(id=bid, type="aws_codebuild", label=params.get("label", bid), config=ToolNodeConfig()),
            terraform_code={"devops.tf": tf_code},
        )


class CreateCodeCommitRepoTool(BaseTool):
    name = "create_codecommit_repo"
    description = "Create an AWS CodeCommit Git repository."
    category = "devops"
    parameters = {
        "type": "object",
        "properties": {
            "repo_id": {"type": "string"}, "label": {"type": "string"},
            "default_branch": {"type": "string", "default": "main"},
        },
        "required": ["repo_id", "label"],
    }

    def execute(self, params: dict[str, Any]) -> ToolResult:
        rid = params["repo_id"]
        tf_code = f'''resource "aws_codecommit_repository" "{rid}" {{
  repository_name = "${{var.project_name}}-{rid}"
  description     = "{params.get('label', rid)}"
  default_branch  = "{params.get('default_branch', 'main')}"
  tags = {{ Name = "${{var.project_name}}-{rid}" }}
}}
'''
        return ToolResult(
            node=ToolNode(id=rid, type="aws_codecommit", label=params.get("label", rid), config=ToolNodeConfig()),
            terraform_code={"devops.tf": tf_code},
        )


class CreateCodeDeployAppTool(BaseTool):
    name = "create_codedeploy_app"
    description = "Create an AWS CodeDeploy application for deployment automation."
    category = "devops"
    parameters = {
        "type": "object",
        "properties": {
            "deploy_id": {"type": "string"}, "label": {"type": "string"},
            "compute_platform": {"type": "string", "description": "'Server', 'Lambda', 'ECS'.", "default": "Server"},
        },
        "required": ["deploy_id", "label"],
    }

    def execute(self, params: dict[str, Any]) -> ToolResult:
        did = params["deploy_id"]
        tf_code = f'''resource "aws_codedeploy_app" "{did}" {{
  name             = "${{var.project_name}}-{did}"
  compute_platform = "{params.get('compute_platform', 'Server')}"
}}
'''
        return ToolResult(
            node=ToolNode(id=did, type="aws_codedeploy", label=params.get("label", did), config=ToolNodeConfig()),
            terraform_code={"devops.tf": tf_code},
        )


class CreateECRRepositoryTool(BaseTool):
    name = "create_ecr_repository"
    description = "Create an Amazon ECR container image repository."
    category = "devops"
    parameters = {
        "type": "object",
        "properties": {
            "ecr_id": {"type": "string"}, "label": {"type": "string"},
            "scan_on_push": {"type": "boolean", "default": True},
        },
        "required": ["ecr_id", "label"],
    }

    def execute(self, params: dict[str, Any]) -> ToolResult:
        eid = params["ecr_id"]
        tf_code = f'''resource "aws_ecr_repository" "{eid}" {{
  name = "${{var.project_name}}-{eid}"
  image_scanning_configuration {{ scan_on_push = {str(params.get('scan_on_push', True)).lower()} }}
  tags = {{ Name = "${{var.project_name}}-{eid}" }}
}}
'''
        return ToolResult(
            node=ToolNode(id=eid, type="aws_ecr", label=params.get("label", eid), config=ToolNodeConfig()),
            terraform_code={"devops.tf": tf_code},
        )


class CreateCodeArtifactRepoTool(BaseTool):
    name = "create_codeartifact_repo"
    description = "Create an AWS CodeArtifact repository for package management (npm, PyPI, Maven)."
    category = "devops"
    parameters = {
        "type": "object",
        "properties": {
            "ca_id": {"type": "string"}, "label": {"type": "string"},
            "domain": {"type": "string", "default": "my-domain"},
        },
        "required": ["ca_id", "label"],
    }

    def execute(self, params: dict[str, Any]) -> ToolResult:
        cid = params["ca_id"]
        domain = params.get("domain", "my-domain")
        tf_code = f'''resource "aws_codeartifact_domain" "{cid}_domain" {{
  domain = "{domain}"
}}

resource "aws_codeartifact_repository" "{cid}" {{
  repository = "${{var.project_name}}-{cid}"
  domain     = aws_codeartifact_domain.{cid}_domain.domain
}}
'''
        return ToolResult(
            node=ToolNode(id=cid, type="aws_codeartifact", label=params.get("label", cid), config=ToolNodeConfig()),
            terraform_code={"devops.tf": tf_code},
        )
