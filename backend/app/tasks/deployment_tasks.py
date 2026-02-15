"""
Celery tasks for Terraform deployment operations.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from app.tasks.celery_app import celery_app
from app.services.terraform.executor import TerraformExecutor
from app.services.terraform.workspace_manager import WorkspaceManager
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
                f"terraform_logs:{project_id}",
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


@celery_app.task(bind=True, name="tasks.terraform_apply")
def run_terraform_apply(self, project_id: int, deployment_id: int) -> dict:
    """
    Celery task: run terraform init + apply for a project.

    Args:
        project_id: Project ID.
        deployment_id: Deployment record ID for status tracking.

    Returns:
        Result dict with status, return_code, and output.
    """
    logger.info("Starting terraform apply for project %d, deployment %d", project_id, deployment_id)

    workspace_mgr = WorkspaceManager()
    executor = TerraformExecutor()
    workspace_dir = workspace_mgr.get_workspace_path(project_id)

    if not workspace_dir.exists():
        return {"status": "failed", "error": "Workspace not found"}

    def log_callback(line: str):
        _publish_log(project_id, line)

    # Run init
    _publish_log(project_id, "=== Running terraform init ===")
    init_code, init_output = _run_async(executor.init(workspace_dir, log_callback))

    if init_code != 0:
        return {
            "status": "failed",
            "error": "terraform init failed",
            "return_code": init_code,
            "output": init_output,
        }

    # Run apply
    _publish_log(project_id, "=== Running terraform apply ===")
    apply_code, apply_output = _run_async(executor.apply(workspace_dir, log_callback))

    result = {
        "status": "success" if apply_code == 0 else "failed",
        "return_code": apply_code,
        "output": f"{init_output}\n---\n{apply_output}",
    }

    _publish_log(project_id, f"=== Terraform apply finished: {result['status']} ===")
    return result


@celery_app.task(bind=True, name="tasks.terraform_destroy")
def run_terraform_destroy(self, project_id: int, deployment_id: int) -> dict:
    """
    Celery task: run terraform destroy for a project.

    Args:
        project_id: Project ID.
        deployment_id: Deployment record ID for status tracking.

    Returns:
        Result dict with status, return_code, and output.
    """
    logger.info("Starting terraform destroy for project %d, deployment %d", project_id, deployment_id)

    workspace_mgr = WorkspaceManager()
    executor = TerraformExecutor()
    workspace_dir = workspace_mgr.get_workspace_path(project_id)

    if not workspace_dir.exists():
        return {"status": "failed", "error": "Workspace not found"}

    def log_callback(line: str):
        _publish_log(project_id, line)

    _publish_log(project_id, "=== Running terraform destroy ===")
    destroy_code, destroy_output = _run_async(executor.destroy(workspace_dir, log_callback))

    result = {
        "status": "success" if destroy_code == 0 else "failed",
        "return_code": destroy_code,
        "output": destroy_output,
    }

    _publish_log(project_id, f"=== Terraform destroy finished: {result['status']} ===")
    return result


@celery_app.task(bind=True, name="tasks.terraform_plan")
def run_terraform_plan(self, project_id: int, deployment_id: int) -> dict:
    """
    Celery task: run terraform init + plan for a project.

    Returns:
        Result dict with plan output.
    """
    logger.info("Starting terraform plan for project %d", project_id)

    workspace_mgr = WorkspaceManager()
    executor = TerraformExecutor()
    workspace_dir = workspace_mgr.get_workspace_path(project_id)

    if not workspace_dir.exists():
        return {"status": "failed", "error": "Workspace not found"}

    def log_callback(line: str):
        _publish_log(project_id, line)

    # Run init
    init_code, init_output = _run_async(executor.init(workspace_dir, log_callback))
    if init_code != 0:
        return {"status": "failed", "error": "terraform init failed", "output": init_output}

    # Run plan
    plan_code, plan_output = _run_async(executor.plan(workspace_dir, log_callback))

    return {
        "status": "success" if plan_code == 0 else "failed",
        "return_code": plan_code,
        "output": plan_output,
    }
