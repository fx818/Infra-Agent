"""
Deployment API routes — deploy, destroy, status, with structured error classification.
"""

import json
import logging
import re
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


# ── Error classification ────────────────────────────────────────────

_ERROR_PATTERNS: list[tuple[str, str, list[str]]] = [
    # (category, human explanation, [regex patterns])
    (
        "PERMISSION_DENIED",
        "AWS credentials are missing, expired, or lack the required permissions.",
        [
            r"AccessDenied",
            r"UnauthorizedAccess",
            r"InvalidClientTokenId",
            r"SignatureDoesNotMatch",
            r"is not authorized to perform",
            r"Access Denied",
            r"AuthFailure",
            r"ExpiredToken",
            r"security token.*invalid",
            r"NoCredentialProviders",
            r"no valid credential sources",
        ],
    ),
    (
        "INVALID_CONFIG",
        "The Terraform configuration has syntax or validation errors.",
        [
            r"Error: Invalid",
            r"Error: Missing required argument",
            r"Error: Unsupported argument",
            r"Error: Unsupported block type",
            r"Error: Expected",
            r"Error: Unexpected",
            r"Reference to undeclared",
            r"A managed resource.*has not been declared",
            r"Blocks of type.*are not expected",
            r"Incorrect attribute value type",
            r"Invalid value for",
            r"Extra characters after interpolation",
            r"interpolation expression",
            r"closing brace to end",
            r"Error: Argument or block definition required",
            r"Error: Unclosed configuration block",
            r"configuration must be valid",
            r"Error:.*not expected here",
            r"Error: Invalid expression",
            r"Error: Invalid string literal",
        ],
    ),
    (
        "RESOURCE_LIMIT",
        "An AWS service quota or resource limit has been reached.",
        [
            r"LimitExceeded",
            r"ResourceLimitExceeded",
            r"limit.*exceeded",
            r"quota.*exceeded",
            r"Too Many Requests",
            r"you have reached.*limit",
            r"VcpuLimitExceeded",
            r"InstanceLimitExceeded",
        ],
    ),
    (
        "RESOURCE_CONFLICT",
        "A resource with the same name or configuration already exists.",
        [
            r"already exists",
            r"AlreadyExistsException",
            r"EntityAlreadyExists",
            r"BucketAlreadyExists",
            r"BucketAlreadyOwnedByYou",
            r"ResourceConflict",
            r"ConflictException",
            r"DuplicateResource",
        ],
    ),
    (
        "PROVIDER_ERROR",
        "Terraform provider initialization or version error.",
        [
            r"Failed to install provider",
            r"provider.*not available",
            r"Incompatible provider version",
            r"Error: Failed to query available provider packages",
            r"Could not retrieve the list of available versions",
            r"registry.terraform.io.*connection",
        ],
    ),
    (
        "STATE_ERROR",
        "Terraform state file is corrupted or locked.",
        [
            r"Error: Error locking state",
            r"state.*locked",
            r"Error loading state",
            r"state.*corruption",
            r"backend.*error",
        ],
    ),
    (
        "NETWORK_ERROR",
        "Network connectivity issue when reaching AWS or Terraform registry.",
        [
            r"dial tcp.*timeout",
            r"connection refused",
            r"no such host",
            r"TLS handshake timeout",
            r"Could not connect",
            r"network.*unreachable",
            r"RequestError.*send request",
        ],
    ),
    (
        "DEPENDENCY_ERROR",
        "A resource depends on another resource that failed or doesn't exist.",
        [
            r"Error: Reference to undeclared",
            r"depends on.*that does not exist",
            r"depends_on.*invalid",
            r"A managed resource.*has not been declared",
            r"ResourceNotFoundException",
            r"object has no attribute",
        ],
    ),
]

_FIX_SUGGESTIONS: dict[str, str] = {
    "PERMISSION_DENIED": (
        "🔧 How to fix:\n"
        "1. Check that your AWS Access Key ID and Secret Access Key are correct in Settings\n"
        "2. Ensure the IAM user/role has sufficient permissions (try AdministratorAccess for testing)\n"
        "3. If using temporary credentials, ensure they haven't expired\n"
        "4. Check that the AWS region is correct"
    ),
    "INVALID_CONFIG": (
        "🔧 How to fix:\n"
        "1. Try regenerating the architecture — this is usually a code generation issue\n"
        "2. Check the Terraform code in the Architecture tab for syntax errors\n"
        "3. Common issues: missing required arguments, wrong value types, invalid references"
    ),
    "RESOURCE_LIMIT": (
        "🔧 How to fix:\n"
        "1. Request a service quota increase in the AWS Console\n"
        "2. Delete unused resources in the same region\n"
        "3. Try deploying in a different AWS region"
    ),
    "RESOURCE_CONFLICT": (
        "🔧 How to fix:\n"
        "1. The resource may already exist from a previous deployment — try destroying first\n"
        "2. Change the project name to avoid naming conflicts\n"
        "3. Delete the conflicting resource manually in the AWS Console"
    ),
    "PROVIDER_ERROR": (
        "🔧 How to fix:\n"
        "1. Check your internet connection\n"
        "2. Try deploying again — this is often a transient issue\n"
        "3. If the issue persists, check if registry.terraform.io is accessible"
    ),
    "STATE_ERROR": (
        "🔧 How to fix:\n"
        "1. Wait a few minutes and try again (state lock may expire)\n"
        "2. If the state is corrupted, you may need to destroy and re-deploy from scratch\n"
        "3. Check the Monitoring tab for partially created resources"
    ),
    "NETWORK_ERROR": (
        "🔧 How to fix:\n"
        "1. Check your internet connection\n"
        "2. Check if a firewall or proxy is blocking outbound connections\n"
        "3. Try again in a few minutes — this may be a transient issue"
    ),
    "DEPENDENCY_ERROR": (
        "🔧 How to fix:\n"
        "1. Try regenerating the architecture — this is a code generation issue\n"
        "2. Resources may be referencing other resources that don't exist in the config"
    ),
}


def _classify_terraform_error(output: str) -> tuple[str, str]:
    """
    Classify a terraform error output into a category and provide a human-readable explanation.

    Returns:
        (error_message_short, error_details_long)
    """
    if not output:
        return "Deployment failed", "No output was captured from the terraform process."

    # Extract the actual error lines
    error_lines = []
    for line in output.splitlines():
        stripped = line.strip()
        if stripped.startswith("Error:") or stripped.startswith("│") or "error" in stripped.lower():
            error_lines.append(stripped)

    error_text = "\n".join(error_lines[-20:]) if error_lines else output[-2000:]

    # Classify
    matched_category = "UNKNOWN"
    matched_explanation = "An unexpected error occurred during deployment."

    for category, explanation, patterns in _ERROR_PATTERNS:
        for pattern in patterns:
            if re.search(pattern, output, re.IGNORECASE):
                matched_category = category
                matched_explanation = explanation
                break
        if matched_category != "UNKNOWN":
            break

    # Build detailed message
    fix_suggestion = _FIX_SUGGESTIONS.get(matched_category, "🔧 Try regenerating the architecture and deploying again.")

    # Short message
    short_msg = f"[{matched_category}] {matched_explanation}"

    # Detailed message with context
    details = (
        f"## Error Category: {matched_category}\n\n"
        f"{matched_explanation}\n\n"
        f"### Error Details\n"
        f"```\n{error_text[:1500]}\n```\n\n"
        f"### Suggested Fix\n"
        f"{fix_suggestion}"
    )

    return short_msg, details

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
        short_err, detailed_err = _classify_terraform_error(init_output)
        deployment.status = "failed"
        deployment.logs = init_output
        deployment.error_message = short_err
        deployment.completed_at = datetime.now(timezone.utc)
        project.status = "failed"
        await db.commit()
        await db.refresh(deployment)
        # Attach error_details as a transient attribute for API response
        deployment._error_details = detailed_err
        print(f"[DEPLOY] FAILED at init stage: {short_err}")
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

    # ── Auto-recovery attempt (one shot) ────────────────────────
    if code != 0 and action == "apply":
        from app.services.terraform.error_recovery import ErrorRecoveryAgent

        recovery_agent = ErrorRecoveryAgent()
        short_err, _ = _classify_terraform_error(output)
        category = short_err.split("]")[0].strip("[") if "]" in short_err else "UNKNOWN"

        print(f"[DEPLOY] Apply failed (category={category}) — attempting auto-recovery...")
        combined_logs += "\n\n" + "="*60 + "\n[AUTO-RECOVERY] Analysing failure and attempting fix...\n" + "="*60 + "\n"

        try:
            recovered, recovery_desc = await recovery_agent.recover(
                error_category=category,
                error_output=combined_logs,
                workspace_dir=workspace_dir,
                project_id=deployment.project_id,
                db=db,
            )
        except Exception as recovery_exc:
            recovered = False
            recovery_desc = f"Recovery agent error: {recovery_exc}"
            print(f"[DEPLOY] Recovery agent exception: {recovery_exc}")

        combined_logs += f"\n[AUTO-RECOVERY] {recovery_desc}\n"

        if recovered:
            print(f"[DEPLOY] Recovery applied — retrying terraform apply...")
            combined_logs += "\n" + "="*60 + "\n[AUTO-RECOVERY] Retrying terraform init + apply...\n" + "="*60 + "\n"

            retry_init_code, retry_init_out = await executor.init(workspace_dir)
            combined_logs += retry_init_out + "\n"

            if retry_init_code == 0:
                retry_code, retry_out = await executor.apply(workspace_dir)
                combined_logs += retry_out + "\n"

                if retry_code == 0:
                    code = 0  # Mark overall as success
                    combined_logs += "\n[AUTO-RECOVERY] ✓ Retry succeeded — deployment recovered!\n"
                    print("[DEPLOY] ✓ Auto-recovery retry SUCCEEDED!")
                else:
                    combined_logs += "\n[AUTO-RECOVERY] ✗ Retry also failed. Proceeding to rollback.\n"
                    print("[DEPLOY] ✗ Auto-recovery retry also failed.")
            else:
                combined_logs += "\n[AUTO-RECOVERY] ✗ Retry init failed. Proceeding to rollback.\n"
                print("[DEPLOY] ✗ Auto-recovery retry init failed.")
        else:
            print(f"[DEPLOY] No recovery possible: {recovery_desc}")

    # ── Auto-rollback on failed apply (only if still failing) ─────
    has_partial_resources = False
    if code != 0 and action == "apply":
        # Check if any resources were actually created (partial deployment)
        try:
            state_code, state_output = await executor.state_list(workspace_dir)
            resource_lines = [l.strip() for l in state_output.splitlines() if l.strip()] if state_code == 0 else []
            if resource_lines:
                has_partial_resources = True
                combined_logs += f"\n[PARTIAL DEPLOY] {len(resource_lines)} resource(s) were created before failure.\n"
                print(f"[DEPLOY] Partial deployment detected: {len(resource_lines)} resource(s) exist in state")
        except Exception as state_exc:
            print(f"[DEPLOY] Could not check state: {state_exc}")

        print("[DEPLOY] Apply failed — running auto-rollback (terraform destroy)...")
        combined_logs += "\n\n" + "="*60 + "\n[AUTO-ROLLBACK] Apply failed. Cleaning up partial resources...\n" + "="*60 + "\n"
        rollback_code, rollback_output = await executor.destroy(workspace_dir)
        combined_logs += rollback_output
        if rollback_code == 0:
            combined_logs += "\n[AUTO-ROLLBACK] ✓ Cleanup successful — all partial resources destroyed."
            has_partial_resources = False  # Rollback succeeded, no more partials
            print("[DEPLOY] Auto-rollback succeeded.")
        else:
            combined_logs += "\n[AUTO-ROLLBACK] ✗ Cleanup incomplete — some resources may still exist. Use per-resource destroy in Monitoring tab."
            print("[DEPLOY] Auto-rollback FAILED — some partial resources may remain.")

    if code == 0 and action == "destroy":
        deployment.status = "destroyed"
    elif code == 0:
        deployment.status = "success"
    elif has_partial_resources:
        deployment.status = "partial_deployed"
    else:
        deployment.status = "failed"
    deployment.logs = combined_logs
    if code != 0:
        short_err, detailed_err = _classify_terraform_error(combined_logs)
        deployment.error_message = short_err
        deployment._error_details = detailed_err
    else:
        deployment.error_message = None
        deployment._error_details = None
    deployment.completed_at = datetime.now(timezone.utc)

    if code == 0:
        if action == "apply":
            project.status = "deployed"
        elif action == "destroy":
            project.status = "destroyed"
        else:
            project.status = "ready"
    elif has_partial_resources:
        project.status = "partial_deployed"
    else:
        project.status = "failed"

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
        "error_details": _classify_terraform_error(deployment.logs or "")[1] if deployment.status == "failed" and deployment.logs else None,
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
    if "[ERROR] Command failed" in full_logs and action == "apply":
        # ── Auto-recovery attempt (streaming) ─────────────────────
        from app.services.terraform.error_recovery import ErrorRecoveryAgent

        yield "\n[AUTO-RECOVERY] Analysing failure and attempting fix...\n"

        recovery_agent = ErrorRecoveryAgent()
        short_err, _ = _classify_terraform_error(full_logs)
        category = short_err.split("]")[0].strip("[") if "]" in short_err else "UNKNOWN"

        try:
            recovered, recovery_desc = await recovery_agent.recover(
                error_category=category,
                error_output=full_logs,
                workspace_dir=workspace_dir,
                project_id=deployment.project_id,
                db=db,
            )
        except Exception as recovery_exc:
            recovered = False
            recovery_desc = f"Recovery agent error: {recovery_exc}"

        yield f"[AUTO-RECOVERY] {recovery_desc}\n"

        if recovered:
            yield "\n[AUTO-RECOVERY] Retrying terraform init + apply...\n"
            # Re-init
            async for line in executor.execute_stream(["init", "-no-color"], workspace_dir):
                yield line
                full_logs += line
            # Re-apply
            retry_failed = False
            async for line in executor.execute_stream(cmd, workspace_dir):
                yield line
                full_logs += line
                if "[ERROR] Command failed" in line:
                    retry_failed = True

            if not retry_failed and "[ERROR] Command failed" not in full_logs.split("[AUTO-RECOVERY] Retrying")[-1]:
                deployment.status = "deployed"
                project_status = "deployed"
                yield "\n[AUTO-RECOVERY] ✓ Retry succeeded — deployment recovered!\n"
            else:
                # Check for partial resources after retry failure
                try:
                    state_code, state_output = await executor.state_list(workspace_dir)
                    state_resources = [l.strip() for l in state_output.splitlines() if l.strip()] if state_code == 0 else []
                    if state_resources:
                        deployment.status = "partial_deployed"
                        project_status = "partial_deployed"
                        yield f"\n[PARTIAL DEPLOY] {len(state_resources)} resource(s) created before failure.\n"
                    else:
                        deployment.status = "failed"
                        project_status = "failed"
                except Exception:
                    deployment.status = "failed"
                    project_status = "failed"
                yield "\n[AUTO-RECOVERY] ✗ Retry also failed.\n"
                yield "\nDeployment failed.\n"
        else:
            # No recovery — check for partial resources
            try:
                state_code, state_output = await executor.state_list(workspace_dir)
                state_resources = [l.strip() for l in state_output.splitlines() if l.strip()] if state_code == 0 else []
                if state_resources:
                    deployment.status = "partial_deployed"
                    project_status = "partial_deployed"
                    yield f"\n[PARTIAL DEPLOY] {len(state_resources)} resource(s) created before failure.\n"
                else:
                    deployment.status = "failed"
                    project_status = "failed"
            except Exception:
                deployment.status = "failed"
                project_status = "failed"
            yield "\nDeployment failed.\n"
    elif "[ERROR] Command failed" in full_logs:
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
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
            "Transfer-Encoding": "chunked",
            "Connection": "keep-alive",
        },
    )


@router.get("/{project_id}/resources")
async def list_deployed_resources(
    project_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """
    List all resources currently tracked in the Terraform state for a project.
    Returns resource addresses usable for targeted destroy.
    """
    from app.services.terraform.workspace_manager import WorkspaceManager
    from app.services.terraform.executor import TerraformExecutor

    await _get_user_project(project_id, db, current_user)

    workspace_mgr = WorkspaceManager()
    workspace_dir = workspace_mgr.get_workspace_path(project_id)

    if not workspace_dir.exists():
        return {"project_id": project_id, "resources": [], "message": "No workspace found — deploy first."}

    # Check if there's a state file
    state_file = workspace_dir / "terraform.tfstate"
    if not state_file.exists():
        return {"project_id": project_id, "resources": [], "message": "No state file — deploy first."}

    executor = TerraformExecutor()
    code, output = await executor.state_list(workspace_dir)

    if code != 0:
        return {
            "project_id": project_id,
            "resources": [],
            "error": f"terraform state list failed: {output[:500]}",
        }

    addresses = [line.strip() for line in output.splitlines() if line.strip()]
    resources = [
        {
            "address": addr,
            "type": addr.split(".")[0] if "." in addr else addr,
            "name": addr.split(".", 1)[1] if "." in addr else addr,
        }
        for addr in addresses
    ]

    return {"project_id": project_id, "resources": resources, "total": len(resources)}


@router.post("/{project_id}/resource/destroy")
async def destroy_single_resource(
    project_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    payload: dict,
) -> dict:
    """
    Destroy a single Terraform-managed resource by its state address.

    Body: { "resource_address": "aws_ecs_service.main" }
    """
    from app.services.terraform.workspace_manager import WorkspaceManager
    from app.services.terraform.executor import TerraformExecutor

    resource_address = (payload or {}).get("resource_address", "").strip()
    if not resource_address:
        raise HTTPException(status_code=400, detail="resource_address is required")

    await _get_user_project(project_id, db, current_user)

    workspace_mgr = WorkspaceManager()
    workspace_dir = workspace_mgr.get_workspace_path(project_id)

    if not workspace_dir.exists():
        raise HTTPException(status_code=400, detail="No workspace found — deploy first.")

    executor = TerraformExecutor()

    try:
        print(f"[DEPLOY] Destroying single resource: {resource_address} in project {project_id}")
        code, output = await executor.destroy_target(workspace_dir, resource_address)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    success = code == 0
    return {
        "project_id": project_id,
        "resource_address": resource_address,
        "success": success,
        "return_code": code,
        "output": output,
        "message": f"{'✓ Resource destroyed successfully.' if success else '✗ Destroy failed.'} Address: {resource_address}",
    }


@router.post("/{project_id}/resources/batch-destroy")
async def destroy_multiple_resources(
    project_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    payload: dict,
) -> dict:
    """
    Destroy multiple Terraform-managed resources by their state addresses, one by one.

    Body: { "resource_addresses": ["aws_ecs_service.main", "aws_alb.main", ...] }

    Returns a list of per-resource results so the frontend can display progress.
    """
    from app.services.terraform.workspace_manager import WorkspaceManager
    from app.services.terraform.executor import TerraformExecutor

    addresses: list[str] = (payload or {}).get("resource_addresses", [])
    if not addresses:
        raise HTTPException(status_code=400, detail="resource_addresses list is required and must not be empty")
    if len(addresses) > 50:
        raise HTTPException(status_code=400, detail="Cannot destroy more than 50 resources in a single batch")

    await _get_user_project(project_id, db, current_user)

    workspace_mgr = WorkspaceManager()
    workspace_dir = workspace_mgr.get_workspace_path(project_id)

    if not workspace_dir.exists():
        raise HTTPException(status_code=400, detail="No workspace found — deploy first.")

    executor = TerraformExecutor()
    results = []
    overall_success = True

    for addr in addresses:
        try:
            print(f"[DEPLOY] Batch destroy: {addr} in project {project_id}")
            code, output = await executor.destroy_target(workspace_dir, addr)
            success = code == 0
            if not success:
                overall_success = False
            results.append({
                "resource_address": addr,
                "success": success,
                "return_code": code,
                "output": output,
            })
        except ValueError as e:
            overall_success = False
            results.append({
                "resource_address": addr,
                "success": False,
                "return_code": -1,
                "output": str(e),
            })
        except Exception as e:
            overall_success = False
            results.append({
                "resource_address": addr,
                "success": False,
                "return_code": -1,
                "output": f"Unexpected error: {str(e)}",
            })

    succeeded = sum(1 for r in results if r["success"])
    failed = len(results) - succeeded

    return {
        "project_id": project_id,
        "overall_success": overall_success,
        "total": len(results),
        "succeeded": succeeded,
        "failed": failed,
        "results": results,
    }
