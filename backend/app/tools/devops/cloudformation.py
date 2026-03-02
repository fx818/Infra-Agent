"""DevOps tools — provisions via boto3."""
import json
from typing import Any
from app.tools.base import BaseTool, ToolResult, ToolNode, ToolNodeConfig


def _iam_role_config(name: str, label: str, service: str) -> dict:
    return {
        "service": "iam", "action": "create_role",
        "params": {
            "RoleName": name,
            "AssumeRolePolicyDocument": json.dumps({
                "Version": "2012-10-17",
                "Statement": [{"Action": "sts:AssumeRole", "Effect": "Allow",
                               "Principal": {"Service": service}}],
            }),
        },
        "label": f"{label} — Role", "resource_type": "aws_iam_role",
        "resource_id_path": "Role.Arn",
        "delete_action": "delete_role", "delete_params": {"RoleName": name},
    }


class CreateCloudFormationStackTool(BaseTool):
    name = "create_cloudformation_stack"
    description = "Create an AWS CloudFormation stack."
    category = "devops"
    parameters = {"type": "object", "properties": {
        "stack_id": {"type": "string"}, "label": {"type": "string"},
    }, "required": ["stack_id", "label"]}

    def execute(self, params: dict[str, Any]) -> ToolResult:
        sid = params["stack_id"]; label = params.get("label", sid)
        configs = [{"service": "cloudformation", "action": "create_stack",
            "params": {"StackName": f"__PROJECT__-{sid}",
                "TemplateBody": json.dumps({"AWSTemplateFormatVersion": "2010-09-09", "Description": label, "Resources": {}}),
                "Tags": [{"Key": "Name", "Value": f"__PROJECT__-{sid}"}]},
            "label": label, "resource_type": "aws_cloudformation",
            "resource_id_path": "StackId",
            "delete_action": "delete_stack", "delete_params": {"StackName": f"__PROJECT__-{sid}"},
            "waiter": "stack_create_complete", "waiter_params": {"StackName": f"__PROJECT__-{sid}"}}]
        return ToolResult(node=ToolNode(id=sid, type="aws_cloudformation", label=label, config=ToolNodeConfig()), boto3_config={"cloudformation": configs})


class CreateSSMParameterTool(BaseTool):
    name = "create_ssm_parameter"
    description = "Create an AWS SSM Parameter Store parameter."
    category = "devops"
    parameters = {"type": "object", "properties": {
        "param_id": {"type": "string"}, "label": {"type": "string"},
        "param_type": {"type": "string", "default": "String"},
        "value": {"type": "string", "default": "placeholder"},
    }, "required": ["param_id", "label"]}

    def execute(self, params: dict[str, Any]) -> ToolResult:
        pid = params["param_id"]; label = params.get("label", pid)
        configs = [{"service": "ssm", "action": "put_parameter",
            "params": {"Name": f"/__PROJECT__/{pid}", "Type": params.get("param_type", "String"),
                "Value": params.get("value", "placeholder"),
                "Tags": [{"Key": "Name", "Value": f"__PROJECT__-{pid}"}]},
            "label": label, "resource_type": "aws_ssm_parameter",
            "resource_id_path": "Version",
            "delete_action": "delete_parameter", "delete_params": {"Name": f"/__PROJECT__/{pid}"}}]
        return ToolResult(node=ToolNode(id=pid, type="aws_ssm", label=label, config=ToolNodeConfig()), boto3_config={"ssm": configs})


class CreateCodePipelineTool(BaseTool):
    name = "create_codepipeline"
    description = "Create an AWS CodePipeline for CI/CD."
    category = "devops"
    parameters = {"type": "object", "properties": {
        "pipeline_id": {"type": "string"}, "label": {"type": "string"},
    }, "required": ["pipeline_id", "label"]}

    def execute(self, params: dict[str, Any]) -> ToolResult:
        pid = params["pipeline_id"]; label = params.get("label", pid)
        role_name = f"__PROJECT__-{pid}-pipeline-role"
        configs = [
            _iam_role_config(role_name, label, "codepipeline.amazonaws.com"),
            {"service": "s3", "action": "create_bucket",
             "params": {"Bucket": f"__PROJECT__-{pid}-artifacts", "CreateBucketConfiguration": {"LocationConstraint": "__REGION__"}},
             "label": f"{label} — Artifacts", "resource_type": "aws_s3_bucket",
             "resource_id_path": "Location", "delete_action": "delete_bucket",
             "delete_params": {"Bucket": f"__PROJECT__-{pid}-artifacts"}},
            {"service": "codepipeline", "action": "create_pipeline",
             "params": {"pipeline": {"name": f"__PROJECT__-{pid}", "roleArn": "__RESOLVE_PREV_0__",
                 "artifactStore": {"type": "S3", "location": f"__PROJECT__-{pid}-artifacts"},
                 "stages": [
                     {"name": "Source", "actions": [{"name": "Source", "actionTypeId": {"category": "Source", "owner": "AWS", "provider": "CodeCommit", "version": "1"},
                      "outputArtifacts": [{"name": "source"}], "configuration": {"RepositoryName": "__PROJECT__", "BranchName": "main"}}]},
                     {"name": "Build", "actions": [{"name": "Build", "actionTypeId": {"category": "Build", "owner": "AWS", "provider": "CodeBuild", "version": "1"},
                      "inputArtifacts": [{"name": "source"}], "configuration": {"ProjectName": f"__PROJECT__-build"}}]}]}},
             "label": label, "resource_type": "aws_codepipeline",
             "resource_id_path": "pipeline.name", "delete_action": "delete_pipeline",
             "delete_params": {"name": f"__PROJECT__-{pid}"}},
        ]
        return ToolResult(node=ToolNode(id=pid, type="aws_codepipeline", label=label, config=ToolNodeConfig()), boto3_config={"codepipeline": configs})


class CreateCodeBuildProjectTool(BaseTool):
    name = "create_codebuild_project"
    description = "Create an AWS CodeBuild project."
    category = "devops"
    parameters = {"type": "object", "properties": {
        "build_id": {"type": "string"}, "label": {"type": "string"},
        "compute_type": {"type": "string", "default": "BUILD_GENERAL1_SMALL"},
        "image": {"type": "string", "default": "aws/codebuild/amazonlinux2-x86_64-standard:5.0"},
    }, "required": ["build_id", "label"]}

    def execute(self, params: dict[str, Any]) -> ToolResult:
        bid = params["build_id"]; label = params.get("label", bid)
        role_name = f"__PROJECT__-{bid}-build-role"
        configs = [
            _iam_role_config(role_name, label, "codebuild.amazonaws.com"),
            {"service": "codebuild", "action": "create_project",
             "params": {"name": f"__PROJECT__-{bid}", "serviceRole": "__RESOLVE_PREV__",
                 "artifacts": {"type": "NO_ARTIFACTS"},
                 "environment": {"computeType": params.get("compute_type", "BUILD_GENERAL1_SMALL"),
                     "image": params.get("image", "aws/codebuild/amazonlinux2-x86_64-standard:5.0"), "type": "LINUX_CONTAINER"},
                 "source": {"type": "NO_SOURCE", "buildspec": "version: 0.2\nphases:\n  build:\n    commands:\n      - echo Build"},
                 "tags": [{"key": "Name", "value": f"__PROJECT__-{bid}"}]},
             "label": label, "resource_type": "aws_codebuild",
             "resource_id_path": "project.arn", "delete_action": "delete_project",
             "delete_params": {"name": f"__PROJECT__-{bid}"}},
        ]
        return ToolResult(node=ToolNode(id=bid, type="aws_codebuild", label=label, config=ToolNodeConfig()), boto3_config={"codebuild": configs})


class CreateCodeCommitRepoTool(BaseTool):
    name = "create_codecommit_repo"
    description = "Create an AWS CodeCommit Git repository."
    category = "devops"
    parameters = {"type": "object", "properties": {
        "repo_id": {"type": "string"}, "label": {"type": "string"},
    }, "required": ["repo_id", "label"]}

    def execute(self, params: dict[str, Any]) -> ToolResult:
        rid = params["repo_id"]; label = params.get("label", rid)
        configs = [{"service": "codecommit", "action": "create_repository",
            "params": {"repositoryName": f"__PROJECT__-{rid}", "repositoryDescription": label,
                "tags": {"Name": f"__PROJECT__-{rid}"}},
            "label": label, "resource_type": "aws_codecommit",
            "resource_id_path": "repositoryMetadata.repositoryId",
            "delete_action": "delete_repository", "delete_params": {"repositoryName": f"__PROJECT__-{rid}"}}]
        return ToolResult(node=ToolNode(id=rid, type="aws_codecommit", label=label, config=ToolNodeConfig()), boto3_config={"codecommit": configs})


class CreateCodeDeployAppTool(BaseTool):
    name = "create_codedeploy_app"
    description = "Create an AWS CodeDeploy application."
    category = "devops"
    parameters = {"type": "object", "properties": {
        "deploy_id": {"type": "string"}, "label": {"type": "string"},
        "compute_platform": {"type": "string", "default": "Server"},
    }, "required": ["deploy_id", "label"]}

    def execute(self, params: dict[str, Any]) -> ToolResult:
        did = params["deploy_id"]; label = params.get("label", did)
        configs = [{"service": "codedeploy", "action": "create_application",
            "params": {"applicationName": f"__PROJECT__-{did}",
                "computePlatform": params.get("compute_platform", "Server"),
                "tags": [{"Key": "Name", "Value": f"__PROJECT__-{did}"}]},
            "label": label, "resource_type": "aws_codedeploy",
            "resource_id_path": "applicationId",
            "delete_action": "delete_application", "delete_params": {"applicationName": f"__PROJECT__-{did}"}}]
        return ToolResult(node=ToolNode(id=did, type="aws_codedeploy", label=label, config=ToolNodeConfig()), boto3_config={"codedeploy": configs})


class CreateECRRepositoryTool(BaseTool):
    name = "create_ecr_repository"
    description = "Create an Amazon ECR container image repository."
    category = "devops"
    parameters = {"type": "object", "properties": {
        "ecr_id": {"type": "string"}, "label": {"type": "string"},
        "scan_on_push": {"type": "boolean", "default": True},
    }, "required": ["ecr_id", "label"]}

    def execute(self, params: dict[str, Any]) -> ToolResult:
        eid = params["ecr_id"]; label = params.get("label", eid)
        configs = [{"service": "ecr", "action": "create_repository",
            "params": {"repositoryName": f"__PROJECT__-{eid}",
                "imageScanningConfiguration": {"scanOnPush": params.get("scan_on_push", True)},
                "tags": [{"Key": "Name", "Value": f"__PROJECT__-{eid}"}]},
            "label": label, "resource_type": "aws_ecr",
            "resource_id_path": "repository.repositoryArn",
            "delete_action": "delete_repository", "delete_params": {"repositoryName": f"__PROJECT__-{eid}", "force": True}}]
        return ToolResult(node=ToolNode(id=eid, type="aws_ecr", label=label, config=ToolNodeConfig()), boto3_config={"ecr": configs})


class CreateCodeArtifactRepoTool(BaseTool):
    name = "create_codeartifact_repo"
    description = "Create an AWS CodeArtifact repository."
    category = "devops"
    parameters = {"type": "object", "properties": {
        "ca_id": {"type": "string"}, "label": {"type": "string"},
        "domain": {"type": "string", "default": "my-domain"},
    }, "required": ["ca_id", "label"]}

    def execute(self, params: dict[str, Any]) -> ToolResult:
        cid = params["ca_id"]; label = params.get("label", cid)
        domain = params.get("domain", "my-domain")
        configs = [
            {"service": "codeartifact", "action": "create_domain",
             "params": {"domain": domain}, "label": f"{label} — Domain",
             "resource_type": "aws_codeartifact_domain", "resource_id_path": "domain.arn",
             "delete_action": "delete_domain", "delete_params": {"domain": domain}},
            {"service": "codeartifact", "action": "create_repository",
             "params": {"domain": domain, "repository": f"__PROJECT__-{cid}"},
             "label": label, "resource_type": "aws_codeartifact_repo",
             "resource_id_path": "repository.arn", "delete_action": "delete_repository",
             "delete_params": {"domain": domain, "repository": f"__PROJECT__-{cid}"}},
        ]
        return ToolResult(node=ToolNode(id=cid, type="aws_codeartifact", label=label, config=ToolNodeConfig()), boto3_config={"codeartifact": configs})
