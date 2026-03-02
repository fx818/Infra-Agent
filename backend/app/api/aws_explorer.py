"""
AWS Infrastructure Explorer API — discover all AWS resources across regions.

Provides endpoints to list AWS regions and discover resources in each region,
including resources NOT created by this application (e.g., resources from the
AWS Console, CLI, or other tools).
"""

import logging
from typing import Annotated, Any

import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from fastapi import APIRouter, Depends, HTTPException

from app.api.auth import get_current_user
from app.core.config import settings
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/aws", tags=["aws-explorer"])


def _get_boto_session(region: str = "us-east-1") -> boto3.Session:
    """Create a boto3 session with the configured AWS credentials."""
    kwargs: dict[str, Any] = {"region_name": region}
    if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
        kwargs["aws_access_key_id"] = settings.AWS_ACCESS_KEY_ID
        kwargs["aws_secret_access_key"] = settings.AWS_SECRET_ACCESS_KEY
    return boto3.Session(**kwargs)


# ── Helper: per-service resource discovery ──────────────────────────

def _list_ec2_instances(session: boto3.Session) -> list[dict]:
    """List EC2 instances."""
    ec2 = session.client("ec2")
    resources = []
    try:
        resp = ec2.describe_instances()
        for reservation in resp.get("Reservations", []):
            for inst in reservation.get("Instances", []):
                name = ""
                for tag in inst.get("Tags", []):
                    if tag["Key"] == "Name":
                        name = tag["Value"]
                        break
                resources.append({
                    "id": inst["InstanceId"],
                    "name": name or inst["InstanceId"],
                    "type": inst.get("InstanceType", ""),
                    "state": inst.get("State", {}).get("Name", ""),
                    "launch_time": str(inst.get("LaunchTime", "")),
                })
    except (ClientError, NoCredentialsError) as e:
        logger.warning("EC2 listing failed: %s", e)
    return resources


def _list_s3_buckets(session: boto3.Session) -> list[dict]:
    """List S3 buckets (global resource)."""
    s3 = session.client("s3")
    resources = []
    try:
        resp = s3.list_buckets()
        for bucket in resp.get("Buckets", []):
            resources.append({
                "id": bucket["Name"],
                "name": bucket["Name"],
                "type": "Bucket",
                "state": "available",
                "launch_time": str(bucket.get("CreationDate", "")),
            })
    except (ClientError, NoCredentialsError) as e:
        logger.warning("S3 listing failed: %s", e)
    return resources


def _list_lambda_functions(session: boto3.Session) -> list[dict]:
    """List Lambda functions."""
    lam = session.client("lambda")
    resources = []
    try:
        resp = lam.list_functions()
        for fn in resp.get("Functions", []):
            resources.append({
                "id": fn["FunctionArn"],
                "name": fn["FunctionName"],
                "type": fn.get("Runtime", "N/A"),
                "state": fn.get("State", "Active"),
                "launch_time": str(fn.get("LastModified", "")),
            })
    except (ClientError, NoCredentialsError) as e:
        logger.warning("Lambda listing failed: %s", e)
    return resources


def _list_rds_instances(session: boto3.Session) -> list[dict]:
    """List RDS database instances."""
    rds = session.client("rds")
    resources = []
    try:
        resp = rds.describe_db_instances()
        for db in resp.get("DBInstances", []):
            resources.append({
                "id": db["DBInstanceIdentifier"],
                "name": db["DBInstanceIdentifier"],
                "type": db.get("DBInstanceClass", ""),
                "state": db.get("DBInstanceStatus", ""),
                "launch_time": str(db.get("InstanceCreateTime", "")),
            })
    except (ClientError, NoCredentialsError) as e:
        logger.warning("RDS listing failed: %s", e)
    return resources


def _list_ecs_clusters(session: boto3.Session) -> list[dict]:
    """List ECS clusters and services."""
    ecs = session.client("ecs")
    resources = []
    try:
        clusters_resp = ecs.list_clusters()
        cluster_arns = clusters_resp.get("clusterArns", [])
        if cluster_arns:
            details = ecs.describe_clusters(clusters=cluster_arns)
            for cluster in details.get("clusters", []):
                resources.append({
                    "id": cluster["clusterArn"],
                    "name": cluster["clusterName"],
                    "type": f"{cluster.get('runningTasksCount', 0)} tasks",
                    "state": cluster.get("status", ""),
                    "launch_time": "",
                })
    except (ClientError, NoCredentialsError) as e:
        logger.warning("ECS listing failed: %s", e)
    return resources


def _list_dynamodb_tables(session: boto3.Session) -> list[dict]:
    """List DynamoDB tables."""
    ddb = session.client("dynamodb")
    resources = []
    try:
        resp = ddb.list_tables()
        for table_name in resp.get("TableNames", []):
            resources.append({
                "id": table_name,
                "name": table_name,
                "type": "Table",
                "state": "active",
                "launch_time": "",
            })
    except (ClientError, NoCredentialsError) as e:
        logger.warning("DynamoDB listing failed: %s", e)
    return resources


def _list_sqs_queues(session: boto3.Session) -> list[dict]:
    """List SQS queues."""
    sqs = session.client("sqs")
    resources = []
    try:
        resp = sqs.list_queues()
        for url in resp.get("QueueUrls", []):
            name = url.split("/")[-1]
            resources.append({
                "id": url,
                "name": name,
                "type": "Queue",
                "state": "active",
                "launch_time": "",
            })
    except (ClientError, NoCredentialsError) as e:
        logger.warning("SQS listing failed: %s", e)
    return resources


def _list_sns_topics(session: boto3.Session) -> list[dict]:
    """List SNS topics."""
    sns = session.client("sns")
    resources = []
    try:
        resp = sns.list_topics()
        for topic in resp.get("Topics", []):
            arn = topic["TopicArn"]
            name = arn.split(":")[-1]
            resources.append({
                "id": arn,
                "name": name,
                "type": "Topic",
                "state": "active",
                "launch_time": "",
            })
    except (ClientError, NoCredentialsError) as e:
        logger.warning("SNS listing failed: %s", e)
    return resources


def _list_cloudfront_distributions(session: boto3.Session) -> list[dict]:
    """List CloudFront distributions."""
    cf = session.client("cloudfront")
    resources = []
    try:
        resp = cf.list_distributions()
        dist_list = resp.get("DistributionList", {})
        for dist in dist_list.get("Items", []):
            resources.append({
                "id": dist["Id"],
                "name": dist.get("DomainName", dist["Id"]),
                "type": "Distribution",
                "state": dist.get("Status", ""),
                "launch_time": str(dist.get("LastModifiedTime", "")),
            })
    except (ClientError, NoCredentialsError) as e:
        logger.warning("CloudFront listing failed: %s", e)
    return resources


def _list_elasticache_clusters(session: boto3.Session) -> list[dict]:
    """List ElastiCache clusters."""
    ec = session.client("elasticache")
    resources = []
    try:
        resp = ec.describe_cache_clusters()
        for cluster in resp.get("CacheClusters", []):
            resources.append({
                "id": cluster["CacheClusterId"],
                "name": cluster["CacheClusterId"],
                "type": cluster.get("Engine", ""),
                "state": cluster.get("CacheClusterStatus", ""),
                "launch_time": str(cluster.get("CacheClusterCreateTime", "")),
            })
    except (ClientError, NoCredentialsError) as e:
        logger.warning("ElastiCache listing failed: %s", e)
    return resources


def _list_api_gateways(session: boto3.Session) -> list[dict]:
    """List API Gateway REST APIs and HTTP APIs."""
    resources = []
    # REST APIs (v1)
    try:
        apigw = session.client("apigateway")
        resp = apigw.get_rest_apis()
        for api in resp.get("items", []):
            resources.append({
                "id": api["id"],
                "name": api.get("name", api["id"]),
                "type": "REST API",
                "state": "active",
                "launch_time": str(api.get("createdDate", "")),
            })
    except (ClientError, NoCredentialsError) as e:
        logger.warning("API Gateway v1 listing failed: %s", e)
    # HTTP APIs (v2)
    try:
        apigw2 = session.client("apigatewayv2")
        resp = apigw2.get_apis()
        for api in resp.get("Items", []):
            resources.append({
                "id": api["ApiId"],
                "name": api.get("Name", api["ApiId"]),
                "type": f"HTTP API ({api.get('ProtocolType', '')})",
                "state": "active",
                "launch_time": str(api.get("CreatedDate", "")),
            })
    except (ClientError, NoCredentialsError) as e:
        logger.warning("API Gateway v2 listing failed: %s", e)
    return resources


def _list_apprunner_services(session: boto3.Session) -> list[dict]:
    """List App Runner services."""
    ar = session.client("apprunner")
    resources = []
    try:
        resp = ar.list_services()
        for svc in resp.get("ServiceSummaryList", []):
            resources.append({
                "id": svc["ServiceArn"],
                "name": svc.get("ServiceName", ""),
                "type": "App Runner",
                "state": svc.get("Status", ""),
                "launch_time": str(svc.get("CreatedAt", "")),
            })
    except (ClientError, NoCredentialsError) as e:
        logger.warning("App Runner listing failed: %s", e)
    return resources


def _list_vpcs(session: boto3.Session) -> list[dict]:
    """List VPCs."""
    ec2 = session.client("ec2")
    resources = []
    try:
        resp = ec2.describe_vpcs()
        for vpc in resp.get("Vpcs", []):
            name = ""
            for tag in vpc.get("Tags", []):
                if tag["Key"] == "Name":
                    name = tag["Value"]
                    break
            resources.append({
                "id": vpc["VpcId"],
                "name": name or vpc["VpcId"],
                "type": vpc.get("CidrBlock", ""),
                "state": vpc.get("State", ""),
                "launch_time": "",
            })
    except (ClientError, NoCredentialsError) as e:
        logger.warning("VPC listing failed: %s", e)
    return resources


def _list_load_balancers(session: boto3.Session) -> list[dict]:
    """List Elastic Load Balancers (v2)."""
    elbv2 = session.client("elbv2")
    resources = []
    try:
        resp = elbv2.describe_load_balancers()
        for lb in resp.get("LoadBalancers", []):
            resources.append({
                "id": lb["LoadBalancerArn"],
                "name": lb.get("LoadBalancerName", ""),
                "type": lb.get("Type", ""),
                "state": lb.get("State", {}).get("Code", ""),
                "launch_time": str(lb.get("CreatedTime", "")),
            })
    except (ClientError, NoCredentialsError) as e:
        logger.warning("ELB listing failed: %s", e)
    return resources


# ── Service registry ────────────────────────────────────────────────

SERVICE_FETCHERS: dict[str, tuple[str, callable]] = {
    "EC2": ("server", _list_ec2_instances),
    "S3": ("hard-drive", _list_s3_buckets),
    "Lambda": ("zap", _list_lambda_functions),
    "RDS": ("database", _list_rds_instances),
    "ECS": ("container", _list_ecs_clusters),
    "DynamoDB": ("table", _list_dynamodb_tables),
    "SQS": ("mail", _list_sqs_queues),
    "SNS": ("bell", _list_sns_topics),
    "CloudFront": ("globe", _list_cloudfront_distributions),
    "ElastiCache": ("cpu", _list_elasticache_clusters),
    "API Gateway": ("network", _list_api_gateways),
    "App Runner": ("play", _list_apprunner_services),
    "VPC": ("shield", _list_vpcs),
    "Load Balancer": ("git-merge", _list_load_balancers),
}


# ── API Endpoints ───────────────────────────────────────────────────

@router.get("/regions")
async def list_aws_regions(
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """Return a list of all available AWS regions."""
    try:
        session = _get_boto_session()
        ec2 = session.client("ec2")
        resp = ec2.describe_regions()
        regions = sorted([r["RegionName"] for r in resp.get("Regions", [])])
        return {"regions": regions}
    except (ClientError, NoCredentialsError) as e:
        raise HTTPException(status_code=500, detail=f"Failed to list regions: {e}")


@router.get("/resources")
async def list_aws_resources(
    current_user: Annotated[User, Depends(get_current_user)],
    region: str = "us-east-1",
) -> dict:
    """
    Discover all AWS resources in a given region.

    Returns resources grouped by service type.
    """
    try:
        session = _get_boto_session(region)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AWS session error: {e}")

    results: dict[str, Any] = {
        "region": region,
        "services": [],
        "total_resources": 0,
    }

    for service_name, (icon, fetcher) in SERVICE_FETCHERS.items():
        try:
            resources = fetcher(session)
        except Exception as e:
            logger.warning("Failed to list %s in %s: %s", service_name, region, e)
            resources = []

        if resources:
            results["services"].append({
                "name": service_name,
                "icon": icon,
                "count": len(resources),
                "resources": resources,
            })
            results["total_resources"] += len(resources)

    # Sort services by count (most resources first)
    results["services"].sort(key=lambda s: s["count"], reverse=True)

    return results


# ── Per-service delete functions ────────────────────────────────────

def _delete_ec2_instance(session: boto3.Session, resource_id: str) -> str:
    ec2 = session.client("ec2")
    ec2.terminate_instances(InstanceIds=[resource_id])
    return f"EC2 instance {resource_id} termination initiated"


def _delete_s3_bucket(session: boto3.Session, resource_id: str) -> str:
    s3 = session.resource("s3")
    bucket = s3.Bucket(resource_id)
    # Must empty bucket before deleting
    bucket.objects.all().delete()
    bucket.object_versions.all().delete()
    bucket.delete()
    return f"S3 bucket {resource_id} deleted"


def _delete_lambda_function(session: boto3.Session, resource_id: str) -> str:
    lam = session.client("lambda")
    # resource_id might be ARN or name — extract name if ARN
    name = resource_id.split(":")[-1] if ":" in resource_id else resource_id
    lam.delete_function(FunctionName=name)
    return f"Lambda function {name} deleted"


def _delete_rds_instance(session: boto3.Session, resource_id: str) -> str:
    rds = session.client("rds")
    rds.delete_db_instance(
        DBInstanceIdentifier=resource_id,
        SkipFinalSnapshot=True,
        DeleteAutomatedBackups=True,
    )
    return f"RDS instance {resource_id} deletion initiated"


def _delete_ecs_cluster(session: boto3.Session, resource_id: str) -> str:
    ecs = session.client("ecs")
    # Must stop all services and tasks first
    services = ecs.list_services(cluster=resource_id).get("serviceArns", [])
    for svc_arn in services:
        ecs.update_service(cluster=resource_id, service=svc_arn, desiredCount=0)
        ecs.delete_service(cluster=resource_id, service=svc_arn, force=True)
    # Stop running tasks
    tasks = ecs.list_tasks(cluster=resource_id).get("taskArns", [])
    for task_arn in tasks:
        ecs.stop_task(cluster=resource_id, task=task_arn)
    ecs.delete_cluster(cluster=resource_id)
    return f"ECS cluster {resource_id} deleted"


def _delete_dynamodb_table(session: boto3.Session, resource_id: str) -> str:
    ddb = session.client("dynamodb")
    ddb.delete_table(TableName=resource_id)
    return f"DynamoDB table {resource_id} deletion initiated"


def _delete_sqs_queue(session: boto3.Session, resource_id: str) -> str:
    sqs = session.client("sqs")
    sqs.delete_queue(QueueUrl=resource_id)
    return f"SQS queue deleted"


def _delete_sns_topic(session: boto3.Session, resource_id: str) -> str:
    sns = session.client("sns")
    sns.delete_topic(TopicArn=resource_id)
    return f"SNS topic deleted"


def _delete_cloudfront_distribution(session: boto3.Session, resource_id: str) -> str:
    cf = session.client("cloudfront")
    # Must disable before deleting
    config_resp = cf.get_distribution_config(Id=resource_id)
    etag = config_resp["ETag"]
    config = config_resp["DistributionConfig"]
    if config.get("Enabled"):
        config["Enabled"] = False
        cf.update_distribution(Id=resource_id, DistributionConfig=config, IfMatch=etag)
        return f"CloudFront distribution {resource_id} disabled (must wait then delete)"
    cf.delete_distribution(Id=resource_id, IfMatch=etag)
    return f"CloudFront distribution {resource_id} deleted"


def _delete_elasticache_cluster(session: boto3.Session, resource_id: str) -> str:
    ec = session.client("elasticache")
    ec.delete_cache_cluster(CacheClusterId=resource_id)
    return f"ElastiCache cluster {resource_id} deletion initiated"


def _delete_api_gateway(session: boto3.Session, resource_id: str) -> str:
    # Try v2 first (HTTP API), then v1 (REST API)
    try:
        apigw2 = session.client("apigatewayv2")
        apigw2.delete_api(ApiId=resource_id)
        return f"HTTP API {resource_id} deleted"
    except ClientError:
        pass
    apigw = session.client("apigateway")
    apigw.delete_rest_api(restApiId=resource_id)
    return f"REST API {resource_id} deleted"


def _delete_apprunner_service(session: boto3.Session, resource_id: str) -> str:
    ar = session.client("apprunner")
    ar.delete_service(ServiceArn=resource_id)
    return f"App Runner service deletion initiated"


def _delete_vpc(session: boto3.Session, resource_id: str) -> str:
    ec2 = session.client("ec2")
    # Delete dependent resources first
    # Internet gateways
    igws = ec2.describe_internet_gateways(
        Filters=[{"Name": "attachment.vpc-id", "Values": [resource_id]}]
    ).get("InternetGateways", [])
    for igw in igws:
        ec2.detach_internet_gateway(InternetGatewayId=igw["InternetGatewayId"], VpcId=resource_id)
        ec2.delete_internet_gateway(InternetGatewayId=igw["InternetGatewayId"])
    # Subnets
    subnets = ec2.describe_subnets(
        Filters=[{"Name": "vpc-id", "Values": [resource_id]}]
    ).get("Subnets", [])
    for subnet in subnets:
        ec2.delete_subnet(SubnetId=subnet["SubnetId"])
    # Route tables (non-main)
    rts = ec2.describe_route_tables(
        Filters=[{"Name": "vpc-id", "Values": [resource_id]}]
    ).get("RouteTables", [])
    for rt in rts:
        is_main = any(a.get("Main") for a in rt.get("Associations", []))
        if not is_main:
            ec2.delete_route_table(RouteTableId=rt["RouteTableId"])
    # Security groups (non-default)
    sgs = ec2.describe_security_groups(
        Filters=[{"Name": "vpc-id", "Values": [resource_id]}]
    ).get("SecurityGroups", [])
    for sg in sgs:
        if sg["GroupName"] != "default":
            ec2.delete_security_group(GroupId=sg["GroupId"])
    ec2.delete_vpc(VpcId=resource_id)
    return f"VPC {resource_id} and its dependencies deleted"


def _delete_load_balancer(session: boto3.Session, resource_id: str) -> str:
    elbv2 = session.client("elbv2")
    elbv2.delete_load_balancer(LoadBalancerArn=resource_id)
    return f"Load balancer deletion initiated"


SERVICE_DELETERS: dict[str, callable] = {
    "EC2": _delete_ec2_instance,
    "S3": _delete_s3_bucket,
    "Lambda": _delete_lambda_function,
    "RDS": _delete_rds_instance,
    "ECS": _delete_ecs_cluster,
    "DynamoDB": _delete_dynamodb_table,
    "SQS": _delete_sqs_queue,
    "SNS": _delete_sns_topic,
    "CloudFront": _delete_cloudfront_distribution,
    "ElastiCache": _delete_elasticache_cluster,
    "API Gateway": _delete_api_gateway,
    "App Runner": _delete_apprunner_service,
    "VPC": _delete_vpc,
    "Load Balancer": _delete_load_balancer,
}


# ── Delete endpoint ─────────────────────────────────────────────────

from pydantic import BaseModel


class ResourceDeleteItem(BaseModel):
    service: str
    resource_id: str
    resource_name: str = ""


class ResourceDeleteRequest(BaseModel):
    region: str = "us-east-1"
    resources: list[ResourceDeleteItem]


@router.post("/resources/delete")
async def delete_aws_resources(
    payload: ResourceDeleteRequest,
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """
    Delete one or more AWS resources.

    Accepts a list of resources with their service type and ID.
    Returns per-resource success/failure results.
    """
    try:
        session = _get_boto_session(payload.region)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AWS session error: {e}")

    results = []
    for item in payload.resources:
        deleter = SERVICE_DELETERS.get(item.service)
        if not deleter:
            results.append({
                "resource_id": item.resource_id,
                "resource_name": item.resource_name,
                "service": item.service,
                "success": False,
                "message": f"No delete handler for service: {item.service}",
            })
            continue

        try:
            message = deleter(session, item.resource_id)
            results.append({
                "resource_id": item.resource_id,
                "resource_name": item.resource_name,
                "service": item.service,
                "success": True,
                "message": message,
            })
            logger.info("Deleted %s resource %s (%s)", item.service, item.resource_id, item.resource_name)
        except (ClientError, NoCredentialsError, Exception) as e:
            results.append({
                "resource_id": item.resource_id,
                "resource_name": item.resource_name,
                "service": item.service,
                "success": False,
                "message": str(e),
            })
            logger.error("Failed to delete %s/%s: %s", item.service, item.resource_id, e)

    succeeded = sum(1 for r in results if r["success"])
    failed = sum(1 for r in results if not r["success"])

    return {
        "total": len(results),
        "succeeded": succeeded,
        "failed": failed,
        "results": results,
    }
