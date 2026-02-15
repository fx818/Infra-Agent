"""
Deployment API routes — deploy, destroy, status.
"""

import json
import logging
import traceback
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.models.architecture import Architecture
from app.models.deployment import Deployment
from app.models.project import Project
from app.models.user import User
from app.schemas.deployment import DeploymentResponse, DeployRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/projects", tags=["deployment"])


async def _get_user_project(
    project_id: int, db: AsyncSession, current_user: User,
) -> Project:
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.user_id == current_user.id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


async def _prepare_workspace(project_id: int, db: AsyncSession):
    """
    Ensure Terraform files from the architecture are written to the workspace.
    Returns the (arch, workspace_dir) tuple.
    """
    from app.services.terraform.workspace_manager import WorkspaceManager

    # Load architecture and its terraform files
    result = await db.execute(
        select(Architecture)
        .where(Architecture.project_id == project_id)
        .order_by(Architecture.version.desc())
        .limit(1)
    )
    arch = result.scalar_one_or_none()
    if not arch:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No architecture found. Generate one first.",
        )

    print(f"[DEPLOY] Architecture found: version={arch.version}, "
          f"tf_json_type={type(arch.terraform_files_json).__name__}, "
          f"tf_json_len={len(str(arch.terraform_files_json or '')) }")

    # Parse terraform files from the stored JSON
    tf_files = {}
    if arch.terraform_files_json:
        try:
            tf_data = (
                json.loads(arch.terraform_files_json)
                if isinstance(arch.terraform_files_json, str)
                else arch.terraform_files_json
            )
            print(f"[DEPLOY] tf_data keys: {list(tf_data.keys()) if isinstance(tf_data, dict) else type(tf_data)}")
            tf_files = tf_data.get("files", {})
            print(f"[DEPLOY] tf_files: {list(tf_files.keys())} ({len(tf_files)} files)")
        except (json.JSONDecodeError, AttributeError) as e:
            print(f"[DEPLOY] ERROR parsing terraform JSON: {e}")

    if not tf_files:
        detail = "No Terraform files found in the architecture. Regenerate the architecture."
        print(f"[DEPLOY] ABORT: {detail}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
        )

    # Write files to workspace
    workspace_mgr = WorkspaceManager()
    workspace_dir = workspace_mgr.write_terraform_files(project_id, tf_files)
    print(f"[DEPLOY] Workspace prepared at {workspace_dir} with {len(tf_files)} files")

    return arch, workspace_dir


async def _run_terraform_sync(
    action: str,
    workspace_dir,
    deployment: Deployment,
    project: Project,
    db: AsyncSession,
):
    """Run terraform init + action synchronously and update the DB."""
    from app.services.terraform.executor import TerraformExecutor

    executor = TerraformExecutor()
    print(f"[DEPLOY] terraform binary: {executor.terraform_binary}")

    # 1) terraform init
    print(f"[DEPLOY] Running terraform init in {workspace_dir}...")
    init_code, init_output = await executor.init(workspace_dir)
    print(f"[DEPLOY] terraform init exit_code={init_code}")
    if init_output:
        print(f"[DEPLOY] terraform init output ({len(init_output)} chars):")
        for line in init_output.split('\n')[:20]:
            print(f"  | {line}")

    if init_code != 0:
        deployment.status = "failed"
        deployment.logs = init_output
        deployment.error_message = "terraform init failed"
        deployment.completed_at = datetime.now(timezone.utc)
        project.status = "failed"
        await db.commit()
        await db.refresh(deployment)
        print(f"[DEPLOY] FAILED at init stage")
        return deployment

    # 2) terraform plan / apply / destroy
    print(f"[DEPLOY] Running terraform {action}...")
    if action == "apply":
        code, output = await executor.apply(workspace_dir)
    elif action == "destroy":
        code, output = await executor.destroy(workspace_dir)
    else:
        code, output = await executor.plan(workspace_dir)

    combined_logs = f"{init_output}\n{'='*60}\n{output}"

    print(f"[DEPLOY] terraform {action} exit_code={code}")
    if output:
        print(f"[DEPLOY] terraform {action} output ({len(output)} chars):")
        for line in output.split('\n')[:30]:
            print(f"  | {line}")

    if code == 0 and action == "destroy":
        deployment.status = "destroyed"
    elif code == 0:
        deployment.status = "success"
    else:
        deployment.status = "failed"
    deployment.logs = combined_logs
    deployment.error_message = None if code == 0 else f"terraform {action} failed (exit {code})"
    deployment.completed_at = datetime.now(timezone.utc)

    if code == 0:
        if action == "apply":
            project.status = "deployed"
        elif action == "destroy":
            project.status = "destroyed"
        else:
            project.status = "ready"
    else:
        project.status = "failed"

    await db.commit()
    await db.commit()
    await db.refresh(deployment)
    print(f"[DEPLOY] Final status: {deployment.status}")
    return deployment


async def _run_terraform_stream(
    action: str,
    workspace_dir,
    deployment: Deployment,
    project: Project,
    db: AsyncSession,
):
    """Run terraform init + action and stream output."""
    from app.services.terraform.executor import TerraformExecutor

    executor = TerraformExecutor()
    yield f"Starting deployment (id={deployment.id})...\n"
    yield f"Terraform binary: {executor.terraform_binary}\n"

    # 1) Init
    yield f"Running terraform init in {workspace_dir}...\n"
    full_logs = ""
    
    # We can stream init too, but for simplicity let's just run it quickly (usually fast)
    # or stream it if we want full fidelity. Let's stream it.
    init_cmd = ["init", "-no-color"]
    async for line in executor.execute_stream(init_cmd, workspace_dir):
        yield line
        full_logs += line

    # Check if init failed (heuristic: check for error in logs or use a separate check)
    # Since execute_stream yields lines, we don't get a return code easily unless we change the signature.
    # The modified execute_stream yields "[ERROR] ..." on failure.
    if "[ERROR] Command failed" in full_logs:
        deployment.status = "failed"
        deployment.logs = full_logs
        deployment.completed_at = datetime.now(timezone.utc)
        project.status = "failed"
        await db.commit()
        yield "\nTerraform init failed.\n"
        return

    # 2) Action (plan/apply/destroy)
    yield f"\nRunning terraform {action}...\n"
    cmd = [action, "-auto-approve", "-no-color", "-input=false"]
    if action == "plan":
        cmd = ["plan", "-no-color", "-input=false"]

    async for line in executor.execute_stream(cmd, workspace_dir):
        yield line
        full_logs += line

    # Determine final status
    if "[ERROR] Command failed" in full_logs:
        deployment.status = "failed"
        project_status = "failed"
        yield "\nDeployment failed.\n"
    else:
        deployment.status = "deployed" if action == "apply" else "destroyed" if action == "destroy" else "ready"
        project_status = deployment.status
        yield "\nDeployment successful.\n"

    deployment.logs = full_logs
    deployment.completed_at = datetime.now(timezone.utc)
    project.status = project_status
    await db.commit()


@router.post("/{project_id}/deploy", response_model=DeploymentResponse)
async def deploy_project(
    project_id: int,
    payload: DeployRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Deployment:
    """
    Trigger a Terraform deployment (plan/apply).
    Runs synchronously — Celery workers are optional.
    """
    print(f"\n{'='*60}")
    print(f"[DEPLOY] === Deploy request: project_id={project_id}, action={payload.action} ===")
    print(f"{'='*60}")

    project = await _get_user_project(project_id, db, current_user)

    if payload.action not in ("plan", "apply"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid action: {payload.action}. Use 'plan' or 'apply'.",
        )

    # Prepare workspace (writes .tf files to disk)
    try:
        arch, workspace_dir = await _prepare_workspace(project_id, db)
    except HTTPException:
        raise
    except Exception as e:
        print(f"[DEPLOY] ERROR in _prepare_workspace: {e}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to prepare workspace: {str(e)}",
        )

    # Create deployment record
    deployment = Deployment(
        project_id=project_id,
        architecture_version=arch.version,
        action=payload.action,
        status="running",
        started_at=datetime.now(timezone.utc),
    )
    db.add(deployment)
    project.status = "deploying"
    await db.commit()
    await db.refresh(deployment)

    print(f"[DEPLOY] Deployment record created: id={deployment.id}")

    # Run terraform synchronously
    try:
        deployment = await _run_terraform_sync(
            payload.action, workspace_dir, deployment, project, db
        )
    except Exception as e:
        print(f"[DEPLOY] EXCEPTION in _run_terraform_sync: {e}")
        traceback.print_exc()
        deployment.status = "failed"
        deployment.error_message = str(e)
        deployment.logs = f"Internal error: {str(e)}\n\n{traceback.format_exc()}"
        deployment.completed_at = datetime.now(timezone.utc)
        project.status = "failed"
        await db.commit()
        await db.refresh(deployment)

    print(f"[DEPLOY] === Deploy complete: status={deployment.status} ===\n")
    return deployment


@router.post("/{project_id}/destroy", response_model=DeploymentResponse)
async def destroy_project(
    project_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Deployment:
    """Trigger Terraform destroy synchronously."""
    print(f"\n{'='*60}")
    print(f"[DEPLOY] === Destroy request: project_id={project_id} ===")
    print(f"{'='*60}")

    project = await _get_user_project(project_id, db, current_user)

    try:
        arch, workspace_dir = await _prepare_workspace(project_id, db)
    except HTTPException:
        raise
    except Exception as e:
        print(f"[DEPLOY] ERROR in _prepare_workspace: {e}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to prepare workspace: {str(e)}",
        )

    deployment = Deployment(
        project_id=project_id,
        architecture_version=arch.version,
        action="destroy",
        status="running",
        started_at=datetime.now(timezone.utc),
    )
    db.add(deployment)
    project.status = "destroying"
    await db.commit()
    await db.refresh(deployment)

    print(f"[DEPLOY] Deployment record created: id={deployment.id}")

    try:
        deployment = await _run_terraform_sync(
            "destroy", workspace_dir, deployment, project, db
        )
    except Exception as e:
        print(f"[DEPLOY] EXCEPTION in _run_terraform_sync: {e}")
        traceback.print_exc()
        deployment.status = "failed"
        deployment.error_message = str(e)
        deployment.logs = f"Internal error: {str(e)}\n\n{traceback.format_exc()}"
        deployment.completed_at = datetime.now(timezone.utc)
        project.status = "failed"
        await db.commit()
        await db.refresh(deployment)

    print(f"[DEPLOY] === Destroy complete: status={deployment.status} ===\n")
    return deployment


@router.get("/{project_id}/status")
async def get_deployment_status(
    project_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """Get the latest deployment status for a project."""
    await _get_user_project(project_id, db, current_user)

    result = await db.execute(
        select(Deployment)
        .where(Deployment.project_id == project_id)
        .order_by(Deployment.created_at.desc())
        .limit(1)
    )
    deployment = result.scalar_one_or_none()
    if not deployment:
        return {"status": "no_deployments", "project_id": project_id}

    return {
        "id": deployment.id,
        "project_id": project_id,
        "architecture_version": deployment.architecture_version,
        "action": deployment.action,
        "status": deployment.status,
        "logs": deployment.logs,
        "error_message": deployment.error_message,
        "started_at": str(deployment.started_at) if deployment.started_at else None,
        "completed_at": str(deployment.completed_at) if deployment.completed_at else None,
    }


@router.get("/{project_id}/deployments", response_model=list[DeploymentResponse])
async def list_deployments(
    project_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[Deployment]:
    """List all deployments for a project."""
    await _get_user_project(project_id, db, current_user)

    result = await db.execute(
        select(Deployment)
        .where(Deployment.project_id == project_id)
        .order_by(Deployment.created_at.desc())
    )
    return list(result.scalars().all())


async def _run_terraform_stream(
    action: str,
    workspace_dir,
    deployment: Deployment,
    project: Project,
    db: AsyncSession,
):
    """Run terraform init + action and stream output."""
    from app.services.terraform.executor import TerraformExecutor

    executor = TerraformExecutor()
    yield f"Starting deployment (id={deployment.id})...\n"
    yield f"Terraform binary: {executor.terraform_binary}\n"

    # 1) Init
    yield f"Running terraform init in {workspace_dir}...\n"
    full_logs = ""
    
    init_cmd = ["init", "-no-color"]
    async for line in executor.execute_stream(init_cmd, workspace_dir):
        yield line
        full_logs += line

    if "[ERROR] Command failed" in full_logs:
        deployment.status = "failed"
        deployment.logs = full_logs
        deployment.completed_at = datetime.now(timezone.utc)
        project.status = "failed"
        await db.commit()
        yield "\nTerraform init failed.\n"
        return

    # 2) Action (plan/apply/destroy)
    yield f"\nRunning terraform {action}...\n"
    cmd = [action, "-auto-approve", "-no-color", "-input=false"]
    if action == "plan":
        cmd = ["plan", "-no-color", "-input=false"]

    async for line in executor.execute_stream(cmd, workspace_dir):
        yield line
        full_logs += line

    # Determine final status
    if "[ERROR] Command failed" in full_logs:
        deployment.status = "failed"
        project_status = "failed"
        yield "\nDeployment failed.\n"
    else:
        deployment.status = "deployed" if action == "apply" else "destroyed" if action == "destroy" else "ready"
        project_status = deployment.status
        yield "\nDeployment successful.\n"

    deployment.logs = full_logs
    deployment.completed_at = datetime.now(timezone.utc)
    project.status = project_status
    await db.commit()


@router.post("/{project_id}/deploy/stream")
async def deploy_project_stream(
    project_id: int,
    payload: DeployRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Trigger a Terraform deployment and stream logs in real-time.
    """
    from fastapi.responses import StreamingResponse

    project = await _get_user_project(project_id, db, current_user)
    
    # Prepare workspace
    try:
        arch, workspace_dir = await _prepare_workspace(project_id, db)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Create record
    deployment = Deployment(
        project_id=project_id,
        architecture_version=arch.version,
        action=payload.action,
        status="running",
        started_at=datetime.now(timezone.utc),
    )
    db.add(deployment)
    project.status = "deploying"
    await db.commit()
    await db.refresh(deployment)

    return StreamingResponse(
        _run_terraform_stream(payload.action, workspace_dir, deployment, project, db),
        media_type="text/plain"
    )
