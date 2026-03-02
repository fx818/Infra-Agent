"""
Drag Build API — save drag-and-drop canvas as a project with architecture.
Now generates boto3 config instead of Terraform HCL.
"""

import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.models.project import Project
from app.models.architecture import Architecture
from app.models.user import User
from app.schemas.project import ProjectResponse

router = APIRouter(prefix="/drag-build", tags=["drag-build"])


# ── Schemas ──────────────────────────────────────────────────────────

class CanvasNode(BaseModel):
    id: str
    type: str  # aws_ec2, aws_s3, etc.
    label: str
    position: dict = Field(default_factory=lambda: {"x": 0, "y": 0})
    config: dict = Field(default_factory=dict)


class CanvasEdge(BaseModel):
    id: str
    source: str
    target: str
    label: str = ""


class DragBuildSaveRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    region: str = "us-east-1"
    nodes: list[CanvasNode]
    edges: list[CanvasEdge]


# ── Routes ───────────────────────────────────────────────────────────

@router.post("/save", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def save_drag_build(
    payload: DragBuildSaveRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Project:
    """Save a drag-and-drop canvas as a new project with architecture."""

    if not payload.nodes:
        raise HTTPException(status_code=400, detail="Canvas must have at least one service node")

    # 1. Create the project
    project = Project(
        user_id=current_user.id,
        name=payload.name,
        description=payload.description or f"Drag & drop project with {len(payload.nodes)} services",
        region=payload.region,
        source="drag_built",
        status="ready",
    )
    db.add(project)
    await db.flush()  # get project.id

    # 2. Build architecture graph from canvas data
    graph_data = {
        "nodes": [
            {"id": n.id, "type": n.type, "label": n.label, "config": n.config}
            for n in payload.nodes
        ],
        "edges": [
            {"source": e.source, "target": e.target, "label": e.label}
            for e in payload.edges
        ],
    }

    # 3. Build visual graph for ReactFlow rendering
    visual_data = {
        "nodes": [
            {
                "id": n.id, "type": "awsService", "position": n.position,
                "data": {"label": n.label, "service_type": n.type}, "style": {},
            }
            for n in payload.nodes
        ],
        "edges": [
            {
                "id": e.id, "source": e.source, "target": e.target,
                "label": e.label, "animated": True, "style": {},
            }
            for e in payload.edges
        ],
    }

    # 4. Generate boto3 config from canvas nodes
    boto3_config = _generate_boto3_config(payload.nodes, payload.region)

    architecture = Architecture(
        project_id=project.id,
        version=1,
        intent_json=json.dumps({
            "app_type": "custom", "scale": "medium",
            "latency_requirement": "standard", "storage_type": "mixed",
            "realtime": False, "constraints": [],
        }),
        graph_json=json.dumps(graph_data),
        terraform_files_json=json.dumps({"files": boto3_config}),
        cost_json=json.dumps({
            "estimated_monthly_cost": 0, "currency": "USD", "breakdown": [],
        }),
        visual_json=json.dumps(visual_data),
    )
    db.add(architecture)

    await db.commit()
    await db.refresh(project)
    return project


@router.put("/update/{project_id}", response_model=ProjectResponse)
async def update_drag_build(
    project_id: int,
    payload: DragBuildSaveRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Project:
    """Update an existing drag-build project — project metadata + architecture."""
    from sqlalchemy import select

    if not payload.nodes:
        raise HTTPException(status_code=400, detail="Canvas must have at least one service node")

    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.user_id == current_user.id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    project.name = payload.name
    project.description = payload.description or f"Drag & drop project with {len(payload.nodes)} services"

    graph_data = {
        "nodes": [{"id": n.id, "type": n.type, "label": n.label, "config": n.config} for n in payload.nodes],
        "edges": [{"source": e.source, "target": e.target, "label": e.label} for e in payload.edges],
    }
    visual_data = {
        "nodes": [{"id": n.id, "type": "awsService", "position": n.position,
                   "data": {"label": n.label, "service_type": n.type}, "style": {}} for n in payload.nodes],
        "edges": [{"id": e.id, "source": e.source, "target": e.target,
                   "label": e.label, "animated": True, "style": {}} for e in payload.edges],
    }

    boto3_config = _generate_boto3_config(payload.nodes, payload.region)

    arch_result = await db.execute(
        select(Architecture).where(Architecture.project_id == project_id)
        .order_by(Architecture.version.desc())
    )
    latest_arch = arch_result.scalars().first()

    if latest_arch:
        new_arch = Architecture(
            project_id=project_id, version=latest_arch.version + 1,
            intent_json=latest_arch.intent_json,
            graph_json=json.dumps(graph_data),
            terraform_files_json=json.dumps({"files": boto3_config}),
            cost_json=latest_arch.cost_json,
            visual_json=json.dumps(visual_data),
        )
    else:
        new_arch = Architecture(
            project_id=project_id, version=1,
            intent_json=json.dumps({
                "app_type": "custom", "scale": "medium",
                "latency_requirement": "standard", "storage_type": "mixed",
                "realtime": False, "constraints": [],
            }),
            graph_json=json.dumps(graph_data),
            terraform_files_json=json.dumps({"files": boto3_config}),
            cost_json=json.dumps({"estimated_monthly_cost": 0, "currency": "USD", "breakdown": []}),
            visual_json=json.dumps(visual_data),
        )
    db.add(new_arch)

    await db.commit()
    await db.refresh(project)
    return project


# ── Boto3 config generator ───────────────────────────────────────────

def _generate_boto3_config(nodes: list[CanvasNode], region: str) -> dict:
    """
    Generate boto3 API call configs from canvas nodes.
    Returns a dict of service -> list of operation configs.
    """
    configs: dict[str, list] = {}

    def _add(service: str, op: dict):
        configs.setdefault(service, []).append(op)

    for node in nodes:
        rid = node.id.replace("-", "_")
        rname = node.label.lower().replace(" ", "-").replace("_", "-")
        svc = node.type.replace("aws_", "").lower()

        if svc == "ec2":
            itype = node.config.get("instance_type", "t3.micro")
            _add("ec2", {
                "action": "run_instances", "label": node.label,
                "resource_type": "aws_ec2_instance",
                "resource_id_path": "Instances[0].InstanceId",
                "params": {
                    "ImageId": "ami-0c02fb55956c7d316", "InstanceType": itype,
                    "MinCount": 1, "MaxCount": 1,
                    "TagSpecifications": [{"ResourceType": "instance", "Tags": [
                        {"Key": "Name", "Value": f"__PROJECT__-{rname}"},
                    ]}],
                },
                "delete_action": "terminate_instances",
                "delete_params": {"InstanceIds": ["__RESOURCE_ID__"]},
            })

        elif svc in ("ecs", "fargate"):
            memory = str(node.config.get("memory", 512))
            cpu = str(node.config.get("cpu", 256))
            image = node.config.get("image", "nginx:latest")
            port = node.config.get("container_port", 80)
            _add("ecs", {"action": "create_cluster", "label": f"{node.label} — Cluster",
                "resource_type": "aws_ecs_cluster", "resource_id_path": "cluster.clusterArn",
                "params": {"clusterName": f"__PROJECT__-{rid}",
                    "tags": [{"key": "Name", "value": f"__PROJECT__-{rid}"}]},
                "delete_action": "delete_cluster", "delete_params": {"cluster": f"__PROJECT__-{rid}"}})
            _add("iam", {"action": "create_role", "label": f"{node.label} — ECS Role",
                "resource_type": "aws_iam_role", "resource_id_path": "Role.Arn",
                "params": {"RoleName": f"__PROJECT__-{rid}-exec",
                    "AssumeRolePolicyDocument": json.dumps({
                        "Version": "2012-10-17",
                        "Statement": [{"Action": "sts:AssumeRole", "Effect": "Allow",
                            "Principal": {"Service": "ecs-tasks.amazonaws.com"}}],
                    })},
                "delete_action": "delete_role", "delete_params": {"RoleName": f"__PROJECT__-{rid}-exec"}})
            _add("ecs", {"action": "register_task_definition", "label": f"{node.label} — Task",
                "resource_type": "aws_ecs_task_definition",
                "resource_id_path": "taskDefinition.taskDefinitionArn",
                "params": {"family": f"__PROJECT__-{rid}", "networkMode": "awsvpc",
                    "requiresCompatibilities": ["FARGATE"], "cpu": cpu, "memory": memory,
                    "executionRoleArn": "__RESOLVE_PREV__",
                    "containerDefinitions": [{"name": rid, "image": image,
                        "cpu": int(cpu), "memory": int(memory), "essential": True,
                        "portMappings": [{"containerPort": port, "protocol": "tcp"}]}]},
                "delete_action": "deregister_task_definition",
                "delete_params": {"taskDefinition": "__RESOURCE_ID__"}})

        elif svc == "lambda":
            runtime = node.config.get("runtime", "python3.12")
            _add("iam", {"action": "create_role", "label": f"{node.label} — Role",
                "resource_type": "aws_iam_role", "resource_id_path": "Role.Arn",
                "params": {"RoleName": f"__PROJECT__-{rid}-role",
                    "AssumeRolePolicyDocument": json.dumps({
                        "Version": "2012-10-17",
                        "Statement": [{"Action": "sts:AssumeRole", "Effect": "Allow",
                            "Principal": {"Service": "lambda.amazonaws.com"}}],
                    })},
                "delete_action": "delete_role", "delete_params": {"RoleName": f"__PROJECT__-{rid}-role"}})
            _add("lambda", {"action": "create_function", "label": node.label,
                "resource_type": "aws_lambda_function",
                "resource_id_path": "FunctionArn",
                "params": {"FunctionName": f"__PROJECT__-{rid}", "Runtime": runtime,
                    "Handler": "index.handler", "Role": "__RESOLVE_PREV__",
                    "Code": {"ZipFile": b"placeholder"},
                    "Tags": {"Name": f"__PROJECT__-{rid}"}},
                "delete_action": "delete_function",
                "delete_params": {"FunctionName": f"__PROJECT__-{rid}"}})

        elif svc == "s3":
            _add("s3", {"action": "create_bucket", "label": node.label,
                "resource_type": "aws_s3_bucket", "resource_id_path": "Location",
                "params": {"Bucket": f"__PROJECT__-{rname}",
                    "CreateBucketConfiguration": {"LocationConstraint": "__REGION__"}},
                "delete_action": "delete_bucket",
                "delete_params": {"Bucket": f"__PROJECT__-{rname}"}})

        elif svc in ("rds", "aurora"):
            engine = node.config.get("engine", "postgres")
            iclass = node.config.get("instance_type", "db.t3.micro")
            _add("rds", {"action": "create_db_instance", "label": node.label,
                "resource_type": "aws_rds_instance",
                "resource_id_path": "DBInstance.DBInstanceIdentifier",
                "params": {"DBInstanceIdentifier": f"__PROJECT__-{rname}",
                    "Engine": engine, "DBInstanceClass": iclass,
                    "AllocatedStorage": 20, "MasterUsername": "admin",
                    "MasterUserPassword": "changeme123!",
                    "Tags": [{"Key": "Name", "Value": f"__PROJECT__-{rname}"}]},
                "delete_action": "delete_db_instance",
                "delete_params": {"DBInstanceIdentifier": f"__PROJECT__-{rname}",
                    "SkipFinalSnapshot": True},
                "waiter": "db_instance_available",
                "waiter_params": {"DBInstanceIdentifier": f"__PROJECT__-{rname}"}})

        elif svc == "dynamodb":
            _add("dynamodb", {"action": "create_table", "label": node.label,
                "resource_type": "aws_dynamodb_table",
                "resource_id_path": "TableDescription.TableArn",
                "params": {"TableName": f"__PROJECT__-{rname}",
                    "BillingMode": "PAY_PER_REQUEST",
                    "KeySchema": [{"AttributeName": "id", "KeyType": "HASH"}],
                    "AttributeDefinitions": [{"AttributeName": "id", "AttributeType": "S"}],
                    "Tags": [{"Key": "Name", "Value": f"__PROJECT__-{rname}"}]},
                "delete_action": "delete_table",
                "delete_params": {"TableName": f"__PROJECT__-{rname}"}})

        elif svc == "elasticache":
            engine = node.config.get("engine", "redis")
            itype = node.config.get("instance_type", "cache.t3.micro")
            _add("elasticache", {"action": "create_cache_cluster", "label": node.label,
                "resource_type": "aws_elasticache_cluster",
                "resource_id_path": "CacheCluster.CacheClusterId",
                "params": {"CacheClusterId": f"__PROJECT__-{rname}", "Engine": engine,
                    "CacheNodeType": itype, "NumCacheNodes": 1,
                    "Tags": [{"Key": "Name", "Value": f"__PROJECT__-{rname}"}]},
                "delete_action": "delete_cache_cluster",
                "delete_params": {"CacheClusterId": f"__PROJECT__-{rname}"}})

        elif svc == "vpc":
            _add("ec2", {"action": "create_vpc", "label": node.label,
                "resource_type": "aws_vpc", "resource_id_path": "Vpc.VpcId",
                "params": {"CidrBlock": "10.0.0.0/16",
                    "TagSpecifications": [{"ResourceType": "vpc", "Tags": [
                        {"Key": "Name", "Value": f"__PROJECT__-{rname}"}]}]},
                "delete_action": "delete_vpc",
                "delete_params": {"VpcId": "__RESOURCE_ID__"}})
            _add("ec2", {"action": "create_internet_gateway", "label": f"{node.label} — IGW",
                "resource_type": "aws_internet_gateway",
                "resource_id_path": "InternetGateway.InternetGatewayId",
                "params": {"TagSpecifications": [{"ResourceType": "internet-gateway", "Tags": [
                    {"Key": "Name", "Value": f"__PROJECT__-{rname}-igw"}]}]},
                "delete_action": "delete_internet_gateway",
                "delete_params": {"InternetGatewayId": "__RESOURCE_ID__"}})

        elif svc in ("elb", "alb", "nlb"):
            _add("elbv2", {"action": "create_load_balancer", "label": node.label,
                "resource_type": "aws_lb",
                "resource_id_path": "LoadBalancers[0].LoadBalancerArn",
                "params": {"Name": f"__PROJECT__-{rname}", "Type": "application",
                    "Scheme": "internet-facing",
                    "Tags": [{"Key": "Name", "Value": f"__PROJECT__-{rname}"}]},
                "delete_action": "delete_load_balancer",
                "delete_params": {"LoadBalancerArn": "__RESOURCE_ID__"}})

        elif svc == "security_group":
            _add("ec2", {"action": "create_security_group", "label": node.label,
                "resource_type": "aws_security_group",
                "resource_id_path": "GroupId",
                "params": {"GroupName": f"__PROJECT__-{rname}",
                    "Description": f"Security group for {rname}",
                    "TagSpecifications": [{"ResourceType": "security-group", "Tags": [
                        {"Key": "Name", "Value": f"__PROJECT__-{rname}"}]}]},
                "delete_action": "delete_security_group",
                "delete_params": {"GroupId": "__RESOURCE_ID__"}})

        elif svc == "sqs":
            _add("sqs", {"action": "create_queue", "label": node.label,
                "resource_type": "aws_sqs_queue", "resource_id_path": "QueueUrl",
                "params": {"QueueName": f"__PROJECT__-{rname}",
                    "tags": {"Name": f"__PROJECT__-{rname}"}},
                "delete_action": "delete_queue",
                "delete_params": {"QueueUrl": "__RESOURCE_ID__"}})

        elif svc == "sns":
            _add("sns", {"action": "create_topic", "label": node.label,
                "resource_type": "aws_sns_topic", "resource_id_path": "TopicArn",
                "params": {"Name": f"__PROJECT__-{rname}",
                    "Tags": [{"Key": "Name", "Value": f"__PROJECT__-{rname}"}]},
                "delete_action": "delete_topic",
                "delete_params": {"TopicArn": "__RESOURCE_ID__"}})

        elif svc == "cloudfront":
            _add("cloudfront", {"action": "create_distribution", "label": node.label,
                "resource_type": "aws_cloudfront_distribution",
                "resource_id_path": "Distribution.Id",
                "params": {"DistributionConfig": {
                    "CallerReference": f"__PROJECT__-{rid}",
                    "Comment": node.label, "Enabled": True,
                    "DefaultRootObject": "index.html",
                    "Origins": {"Quantity": 1, "Items": [
                        {"Id": f"{rid}-origin", "DomainName": "example.com",
                         "CustomOriginConfig": {"HTTPPort": 80, "HTTPSPort": 443,
                            "OriginProtocolPolicy": "http-only"}}]},
                    "DefaultCacheBehavior": {
                        "TargetOriginId": f"{rid}-origin",
                        "ViewerProtocolPolicy": "redirect-to-https",
                        "ForwardedValues": {"QueryString": False,
                            "Cookies": {"Forward": "none"}},
                        "MinTTL": 0},
                    "ViewerCertificate": {"CloudFrontDefaultCertificate": True},
                    "Restrictions": {"GeoRestriction": {"RestrictionType": "none", "Quantity": 0}},
                }},
                "delete_action": "delete_distribution",
                "delete_params": {"Id": "__RESOURCE_ID__"}})

        elif svc in ("apigatewayv2", "api_gateway"):
            _add("apigatewayv2", {"action": "create_api", "label": node.label,
                "resource_type": "aws_apigatewayv2",
                "resource_id_path": "ApiId",
                "params": {"Name": f"__PROJECT__-{rname}", "ProtocolType": "HTTP",
                    "Tags": {"Name": f"__PROJECT__-{rname}"}},
                "delete_action": "delete_api",
                "delete_params": {"ApiId": "__RESOURCE_ID__"}})

        elif svc == "route53":
            _add("route53", {"action": "create_hosted_zone", "label": node.label,
                "resource_type": "aws_route53_zone",
                "resource_id_path": "HostedZone.Id",
                "params": {"Name": rname, "CallerReference": f"__PROJECT__-{rid}"},
                "delete_action": "delete_hosted_zone",
                "delete_params": {"Id": "__RESOURCE_ID__"}})

        elif svc in ("iam_role", "iam"):
            _add("iam", {"action": "create_role", "label": node.label,
                "resource_type": "aws_iam_role", "resource_id_path": "Role.Arn",
                "params": {"RoleName": f"__PROJECT__-{rname}",
                    "AssumeRolePolicyDocument": json.dumps({
                        "Version": "2012-10-17",
                        "Statement": [{"Action": "sts:AssumeRole", "Effect": "Allow",
                            "Principal": {"Service": "ec2.amazonaws.com"}}],
                    })},
                "delete_action": "delete_role",
                "delete_params": {"RoleName": f"__PROJECT__-{rname}"}})

        elif svc == "eks":
            _add("iam", {"action": "create_role", "label": f"{node.label} — EKS Role",
                "resource_type": "aws_iam_role", "resource_id_path": "Role.Arn",
                "params": {"RoleName": f"__PROJECT__-{rid}-eks-role",
                    "AssumeRolePolicyDocument": json.dumps({
                        "Version": "2012-10-17",
                        "Statement": [{"Action": "sts:AssumeRole", "Effect": "Allow",
                            "Principal": {"Service": "eks.amazonaws.com"}}],
                    })},
                "delete_action": "delete_role",
                "delete_params": {"RoleName": f"__PROJECT__-{rid}-eks-role"}})
            _add("eks", {"action": "create_cluster", "label": node.label,
                "resource_type": "aws_eks_cluster",
                "resource_id_path": "cluster.name",
                "params": {"name": f"__PROJECT__-{rname}",
                    "roleArn": "__RESOLVE_PREV__",
                    "resourcesVpcConfig": {"subnetIds": [], "securityGroupIds": []}},
                "delete_action": "delete_cluster",
                "delete_params": {"name": f"__PROJECT__-{rname}"}})

        elif svc == "ebs":
            size = node.config.get("capacity", 20)
            _add("ec2", {"action": "create_volume", "label": node.label,
                "resource_type": "aws_ebs_volume",
                "resource_id_path": "VolumeId",
                "params": {"AvailabilityZone": f"__REGION__a", "Size": int(size) if size else 20,
                    "VolumeType": "gp3",
                    "TagSpecifications": [{"ResourceType": "volume", "Tags": [
                        {"Key": "Name", "Value": f"__PROJECT__-{rname}"}]}]},
                "delete_action": "delete_volume",
                "delete_params": {"VolumeId": "__RESOURCE_ID__"}})

        elif svc == "eventbridge":
            _add("events", {"action": "create_event_bus", "label": node.label,
                "resource_type": "aws_eventbridge_bus",
                "resource_id_path": "EventBusArn",
                "params": {"Name": f"__PROJECT__-{rname}",
                    "Tags": [{"Key": "Name", "Value": f"__PROJECT__-{rname}"}]},
                "delete_action": "delete_event_bus",
                "delete_params": {"Name": f"__PROJECT__-{rname}"}})

        elif svc == "kinesis":
            _add("kinesis", {"action": "create_stream", "label": node.label,
                "resource_type": "aws_kinesis_stream",
                "resource_id_path": "StreamARN",
                "params": {"StreamName": f"__PROJECT__-{rname}",
                    "StreamModeDetails": {"StreamMode": "ON_DEMAND"},
                    "Tags": {"Name": f"__PROJECT__-{rname}"}},
                "delete_action": "delete_stream",
                "delete_params": {"StreamName": f"__PROJECT__-{rname}",
                    "EnforceConsumerDeletion": True}})

        elif svc == "cognito":
            _add("cognito-idp", {"action": "create_user_pool", "label": node.label,
                "resource_type": "aws_cognito_user_pool",
                "resource_id_path": "UserPool.Id",
                "params": {"PoolName": f"__PROJECT__-{rname}",
                    "AutoVerifiedAttributes": ["email"],
                    "UserPoolTags": {"Name": f"__PROJECT__-{rname}"}},
                "delete_action": "delete_user_pool",
                "delete_params": {"UserPoolId": "__RESOURCE_ID__"}})

        elif svc == "secrets_manager":
            _add("secretsmanager", {"action": "create_secret", "label": node.label,
                "resource_type": "aws_secretsmanager_secret",
                "resource_id_path": "ARN",
                "params": {"Name": f"__PROJECT__-{rname}",
                    "Description": f"Secret for {node.label}",
                    "Tags": [{"Key": "Name", "Value": f"__PROJECT__-{rname}"}]},
                "delete_action": "delete_secret",
                "delete_params": {"SecretId": f"__PROJECT__-{rname}",
                    "ForceDeleteWithoutRecovery": True}})

        elif svc == "cloudwatch":
            _add("cloudwatch", {"action": "put_dashboard", "label": node.label,
                "resource_type": "aws_cloudwatch_dashboard",
                "resource_id_path": "DashboardValidationMessages",
                "params": {"DashboardName": f"__PROJECT__-{rname}",
                    "DashboardBody": json.dumps({
                        "widgets": [{"type": "text", "x": 0, "y": 0,
                            "width": 6, "height": 3,
                            "properties": {"markdown": f"# {node.label}"}}]})},
                "delete_action": "delete_dashboards",
                "delete_params": {"DashboardNames": [f"__PROJECT__-{rname}"]}})

        elif svc == "ecr":
            _add("ecr", {"action": "create_repository", "label": node.label,
                "resource_type": "aws_ecr_repository",
                "resource_id_path": "repository.repositoryArn",
                "params": {"repositoryName": f"__PROJECT__-{rname}",
                    "imageScanningConfiguration": {"scanOnPush": True},
                    "tags": [{"Key": "Name", "Value": f"__PROJECT__-{rname}"}]},
                "delete_action": "delete_repository",
                "delete_params": {"repositoryName": f"__PROJECT__-{rname}",
                    "force": True}})

        elif svc == "redshift":
            itype = node.config.get("instance_type", "dc2.large")
            _add("redshift", {"action": "create_cluster", "label": node.label,
                "resource_type": "aws_redshift_cluster",
                "resource_id_path": "Cluster.ClusterIdentifier",
                "params": {"ClusterIdentifier": f"__PROJECT__-{rname}",
                    "NodeType": itype, "NumberOfNodes": 1,
                    "MasterUsername": "admin", "MasterUserPassword": "Changeme123!",
                    "DBName": "default",
                    "Tags": [{"Key": "Name", "Value": f"__PROJECT__-{rname}"}]},
                "delete_action": "delete_cluster",
                "delete_params": {"ClusterIdentifier": f"__PROJECT__-{rname}",
                    "SkipFinalClusterSnapshot": True}})

        elif svc == "transit_gateway":
            _add("ec2", {"action": "create_transit_gateway", "label": node.label,
                "resource_type": "aws_transit_gateway",
                "resource_id_path": "TransitGateway.TransitGatewayId",
                "params": {"Description": f"Transit Gateway for {node.label}",
                    "TagSpecifications": [{"ResourceType": "transit-gateway", "Tags": [
                        {"Key": "Name", "Value": f"__PROJECT__-{rname}"}]}]},
                "delete_action": "delete_transit_gateway",
                "delete_params": {"TransitGatewayId": "__RESOURCE_ID__"}})

        elif svc == "nat_gateway":
            _add("ec2", {"action": "create_nat_gateway", "label": node.label,
                "resource_type": "aws_nat_gateway",
                "resource_id_path": "NatGateway.NatGatewayId",
                "params": {"SubnetId": "__REQUIRES_SUBNET__",
                    "TagSpecifications": [{"ResourceType": "natgateway", "Tags": [
                        {"Key": "Name", "Value": f"__PROJECT__-{rname}"}]}]},
                "delete_action": "delete_nat_gateway",
                "delete_params": {"NatGatewayId": "__RESOURCE_ID__"}})

        # Default: unsupported service — just log it
        else:
            _add("_unsupported", {"action": "noop", "label": f"{node.label} (unsupported: {node.type})",
                "resource_type": node.type, "params": {}})

    return configs
