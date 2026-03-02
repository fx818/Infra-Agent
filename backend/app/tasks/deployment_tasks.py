"""
Celery tasks for Boto3 deployment operations.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone

from app.tasks.celery_app import celery_app
from app.services.boto3.executor import Boto3Executor
from app.core.config import settings

logger = logging.getLogger(__name__)

# Redis pub/sub for log streaming
try:
    import redis
    redis_client = redis.Redis.from_url(settings.REDIS_URL)
except Exception:
    redis_client = None
    logger.warning("Redis not available — log streaming disabled")


def _publish_log(project_id: int, line: str) -> None:
    """Publish a log line to Redis pub/sub for WebSocket streaming."""
    if redis_client:
        try:
            redis_client.publish(
                f"deploy_logs:{project_id}",
                json.dumps({"line": line, "timestamp": datetime.now(timezone.utc).isoformat()}),
            )
        except Exception as e:
            logger.debug("Failed to publish log: %s", e)


def _run_async(coro):
    """Run an async function from a sync Celery task."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(bind=True, name="tasks.boto3_deploy")
def run_boto3_deploy(self, project_id: int, deployment_id: int, boto3_configs: dict, aws_credentials: dict) -> dict:
    """
    Celery task: deploy AWS resources using boto3.

    Args:
        project_id: Project ID.
        deployment_id: Deployment record ID for status tracking.
        boto3_configs: The merged boto3 config dict from the architecture.
        aws_credentials: Dict with aws_access_key_id, aws_secret_access_key, region.

    Returns:
        Result dict with status and deployed resources.
    """
    logger.info("Starting boto3 deploy for project %d, deployment %d", project_id, deployment_id)

    executor = Boto3Executor(
        aws_access_key_id=aws_credentials.get("aws_access_key_id"),
        aws_secret_access_key=aws_credentials.get("aws_secret_access_key"),
        region_name=aws_credentials.get("region", "us-east-1"),
    )

    def log_callback(line: str):
        _publish_log(project_id, line)

    _publish_log(project_id, "=== Starting boto3 deployment ===")

    try:
        deployed_resources = _run_async(executor.deploy(boto3_configs, log_callback))
        _publish_log(project_id, f"=== Boto3 deployment finished: success ({len(deployed_resources)} resources) ===")
        return {
            "status": "success",
            "resources": deployed_resources,
        }
    except Exception as e:
        _publish_log(project_id, f"=== Boto3 deployment failed: {e} ===")
        return {
            "status": "failed",
            "error": str(e),
        }


@celery_app.task(bind=True, name="tasks.boto3_destroy")
def run_boto3_destroy(self, project_id: int, deployment_id: int, resource_records: list, aws_credentials: dict) -> dict:
    """
    Celery task: destroy AWS resources using boto3.

    Args:
        project_id: Project ID.
        deployment_id: Deployment record ID for status tracking.
        resource_records: List of resource record dicts from the state tracker.
        aws_credentials: Dict with aws_access_key_id, aws_secret_access_key, region.

    Returns:
        Result dict with status.
    """
    logger.info("Starting boto3 destroy for project %d, deployment %d", project_id, deployment_id)

    executor = Boto3Executor(
        aws_access_key_id=aws_credentials.get("aws_access_key_id"),
        aws_secret_access_key=aws_credentials.get("aws_secret_access_key"),
        region_name=aws_credentials.get("region", "us-east-1"),
    )

    def log_callback(line: str):
        _publish_log(project_id, line)

    _publish_log(project_id, "=== Starting boto3 destroy ===")

    try:
        _run_async(executor.destroy(resource_records, log_callback))
        _publish_log(project_id, "=== Boto3 destroy finished: success ===")
        return {"status": "success"}
    except Exception as e:
        _publish_log(project_id, f"=== Boto3 destroy failed: {e} ===")
        return {"status": "failed", "error": str(e)}
