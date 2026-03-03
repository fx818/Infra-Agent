"""
Deployment API routes — deploy, destroy, status, with structured error classification.
Now uses Boto3Executor instead of Terraform CLI.
"""

import json
import logging
import re
import traceback
import asyncio
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.core.security import decrypt_credentials
from app.models.architecture import Architecture
from app.models.deployment import Deployment
from app.models.project import Project
from app.models.user import User
from app.schemas.deployment import DeploymentResponse, DeployRequest

logger = logging.getLogger(__name__)


# ── Error classification ────────────────────────────────────────────

_ERROR_PATTERNS: list[tuple[str, str, list[str]]] = [
    (
        "PERMISSION_DENIED",
        "AWS credentials are missing, expired, or lack the required permissions.",
        [
            r"AccessDenied", r"UnauthorizedAccess", r"InvalidClientTokenId",
            r"SignatureDoesNotMatch", r"is not authorized to perform",
            r"Access Denied", r"AuthFailure", r"ExpiredToken",
            r"security token.*invalid", r"NoCredentialProviders",
            r"no valid credential sources",
        ],
    ),
    (
        "INVALID_CONFIG",
        "The resource configuration has validation errors.",
        [
            r"InvalidParameter", r"ValidationError", r"MalformedPolicy",
            r"InvalidInput", r"ParamValidationError", r"Invalid value",
        ],
    ),
    (
        "RESOURCE_LIMIT",
        "An AWS service quota or resource limit has been reached.",
        [
            r"LimitExceeded", r"ResourceLimitExceeded", r"limit.*exceeded",
            r"quota.*exceeded", r"Too Many Requests",
            r"VcpuLimitExceeded", r"InstanceLimitExceeded",
        ],
    ),
    (
        "RESOURCE_CONFLICT",
        "A resource with the same name or configuration already exists.",
        [
            r"already exists", r"AlreadyExistsException",
            r"EntityAlreadyExists", r"BucketAlreadyExists",
            r"BucketAlreadyOwnedByYou", r"ResourceConflict",
            r"ConflictException", r"DuplicateResource",
        ],
    ),
    (
        "DEPENDENCY_ERROR",
        "A resource depends on another resource that failed or doesn't exist.",
        [
            r"ResourceNotFoundException", r"NoSuchEntity", r"NoSuchBucket",
            r"NotFoundException", r"does not exist",
        ],
    ),
    (
        "NETWORK_ERROR",
        "Network connectivity issue when reaching AWS.",
        [
            r"ConnectTimeoutError", r"EndpointConnectionError",
            r"ConnectionError", r"connection refused",
            r"Could not connect", r"network.*unreachable",
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
        "2. Check the architecture configuration for invalid parameter values\n"
        "3. Common issues: missing required arguments, wrong value types"
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
    "DEPENDENCY_ERROR": (
        "🔧 How to fix:\n"
        "1. Try regenerating the architecture — this is a code generation issue\n"
        "2. Resources may be referencing other resources that don't exist"
    ),
    "NETWORK_ERROR": (
        "🔧 How to fix:\n"
        "1. Check your internet connection\n"
        "2. Check if a firewall or proxy is blocking outbound connections\n"
        "3. Try again in a few minutes — this may be a transient issue"
    ),
}


def _classify_deploy_error(output: str) -> tuple[str, str]:
    """Classify a deployment error output into a category and provide explanation."""
    if not output:
        return "Deployment failed", "No output was captured from the deployment process."

    error_lines = [l.strip() for l in output.splitlines() if "error" in l.lower() or "Error" in l]
    error_text = "\n".join(error_lines[-20:]) if error_lines else output[-2000:]

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

    fix_suggestion = _FIX_SUGGESTIONS.get(matched_category, "🔧 Try regenerating the architecture and deploying again.")
    short_msg = f"[{matched_category}] {matched_explanation}"
    details = (
        f"## Error Category: {matched_category}\n\n"
        f"{matched_explanation}\n\n"
        f"### Error Details\n```\n{error_text[:1500]}\n```\n\n"
        f"### Suggested Fix\n{fix_suggestion}"
    )
    return short_msg, details


router = APIRouter(prefix="/projects", tags=["deployment"])


async def _get_user_project(project_id: int, db: AsyncSession, current_user: User) -> Project:
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.user_id == current_user.id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


def _get_aws_credentials(current_user: User) -> dict:
    """Extract AWS credentials from the user's encrypted settings."""
    if not current_user.aws_credentials_encrypted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="AWS credentials not configured. Please set them in Settings.",
        )
    try:
        return json.loads(decrypt_credentials(current_user.aws_credentials_encrypted))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to decrypt AWS credentials: {e}",
        )


async def _load_boto3_config(project_id: int, db: AsyncSession) -> tuple:
    """Load boto3 config from the latest architecture."""
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

    # Parse boto3 config from stored JSON (column is still called terraform_files_json for backward compat)
    boto3_configs = {}
    if arch.terraform_files_json:
        try:
            raw = json.loads(arch.terraform_files_json) if isinstance(arch.terraform_files_json, str) else arch.terraform_files_json
            # The stored format may be {"files": {...}} (old) or direct boto3 config
            boto3_configs = raw.get("files", raw) if isinstance(raw, dict) else {}
        except (json.JSONDecodeError, AttributeError) as e:
            print(f"[DEPLOY] ERROR parsing config JSON: {e}")

    if not boto3_configs:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No infrastructure configuration found. Regenerate the architecture.",
        )

    return arch, boto3_configs


def _sanitize_project_name(name: str) -> str:
    """Return a version of the project name safe to embed in any AWS resource name.

    Most AWS services accept only [a-zA-Z0-9-] (or a subset).  Project names
    entered by users may include spaces, parentheses, underscores, etc., so we
    strip everything to alphanumeric + hyphen here rather than letting individual
    service calls fail at the AWS API.
    """
    import re as _re
    name = name.strip().lower().replace(" ", "-").replace("_", "-")
    name = _re.sub(r"[^a-z0-9\-]", "", name)      # strip anything not alphanumeric/-
    name = _re.sub(r"-+", "-", name).strip("-")   # collapse runs of hyphens
    return name[:40] or "project"                  # cap length; never empty


def _resolve_config_placeholders(
    configs: list[dict], project_name: str, region: str,
) -> list[dict]:
    """Replace __PROJECT__, __REGION__ placeholders in config params."""
    import copy

    safe_project = _sanitize_project_name(project_name)
    resolved = []
    for cfg in configs:
        cfg = copy.deepcopy(cfg)
        _replace_in_obj(cfg, {"__PROJECT__": safe_project, "__REGION__": region})
        resolved.append(cfg)
    return resolved


def _replace_in_obj(obj, replacements: dict):
    """Recursively replace placeholder strings in dicts/lists."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, str):
                for placeholder, value in replacements.items():
                    v = v.replace(placeholder, value)
                obj[k] = v
            elif isinstance(v, (dict, list)):
                _replace_in_obj(v, replacements)
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            if isinstance(item, str):
                for placeholder, value in replacements.items():
                    item = item.replace(placeholder, value)
                obj[i] = item
            elif isinstance(item, (dict, list)):
                _replace_in_obj(item, replacements)


async def _run_boto3_deploy(
    action: str,
    boto3_configs: dict,
    deployment: Deployment,
    project: Project,
    current_user: User,
    db: AsyncSession,
):
    """Run boto3 deploy/destroy synchronously and update the DB."""
    from app.services.boto3.executor import Boto3Executor
    from app.services.boto3.state_tracker import StateTracker

    aws_creds = _get_aws_credentials(current_user)
    region = aws_creds.get("region") or project.region or "us-east-1"
    safe_name = project.name.lower().replace(" ", "-").replace("_", "-")
    safe_name = "".join(c for c in safe_name if c.isalnum() or c == "-")

    executor = Boto3Executor(
        aws_access_key_id=aws_creds.get("aws_access_key_id"),
        aws_secret_access_key=aws_creds.get("aws_secret_access_key"),
        region_name=region,
        project_name=safe_name,
    )
    state_tracker = StateTracker(db)
    combined_logs = ""

    # Flatten nested config dict into flat list and resolve placeholders
    flat_configs = Boto3Executor.flatten_configs(boto3_configs)
    flat_configs = _resolve_config_placeholders(flat_configs, safe_name, region)

    def log_cb(line: str):
        nonlocal combined_logs
        combined_logs += line + "\n"
        print(f"  | {line}")

    try:
        if action == "apply":
            print(f"[DEPLOY] Running boto3 deploy for project {project.id}...")
            log_cb("=== Starting AWS resource provisioning ===")
            deployed_resources = await executor.deploy(flat_configs, log_cb)

            # Only track resources that were actually created
            created_resources = [r for r in deployed_resources if r.get("status") == "created"]
            created_count = len(created_resources)
            total_count = len(deployed_resources)
            log_cb(f"=== Provisioning complete: {created_count}/{total_count} resources created ===")

            if created_resources:
                state_tracker.save_resources(deployment, created_resources)

            if created_count == 0:
                deployment.status = "failed"
                deployment.error_message = f"All {total_count} resource(s) failed to provision. Check logs for details."
                await db.execute(
                    update(Project).where(Project.id == project.id).values(status="failed")
                )
            elif created_count < total_count:
                deployment.status = "partial_deployed"
                await db.execute(
                    update(Project).where(Project.id == project.id).values(status="partial_deployed")
                )
            else:
                deployment.status = "success"
                await db.execute(
                    update(Project).where(Project.id == project.id).values(status="deployed")
                )

        elif action == "destroy":
            print(f"[DEPLOY] Running boto3 destroy for project {project.id}...")
            log_cb("=== Starting AWS resource destruction ===")

            # Load previously deployed resources from DB
            resource_records = state_tracker.get_resources(deployment)

            if resource_records:
                results = await executor.destroy(resource_records, log_cb)
                failed_count = sum(1 for r in results if r.get("destroy_status") == "failed")
                state_tracker.clear_resources(deployment)
                if failed_count > 0:
                    log_cb(f"=== Destruction complete with {failed_count} error(s) — check logs ===")
                else:
                    log_cb("=== Destruction complete ===")
            else:
                log_cb("No deployed resources found in state — infrastructure may already be destroyed.")

            deployment.status = "destroyed"
            await db.execute(
                update(Project).where(Project.id == project.id).values(status="destroyed")
            )

        else:
            # Plan — just validate the config (dry run)
            log_cb("=== Validating infrastructure configuration ===")
            log_cb(f"Configuration contains {len(flat_configs)} operation(s)")
            for cfg in flat_configs:
                log_cb(f"  • {cfg.get('label', cfg.get('service', '?'))}.{cfg.get('action', '?')}")
            log_cb("=== Validation complete (plan mode — no resources created) ===")
            deployment.status = "success"
            await db.execute(
                update(Project).where(Project.id == project.id).values(status="ready")
            )

    except Exception as e:
        error_msg = str(e)
        tb = traceback.format_exc()
        combined_logs += f"\n\nERROR: {error_msg}\n{tb}"
        short_err, detailed_err = _classify_deploy_error(combined_logs)
        deployment.status = "failed"
        deployment.error_message = short_err
        deployment.error_details = detailed_err
        await db.execute(
            update(Project).where(Project.id == project.id).values(status="failed")
        )
        print(f"[DEPLOY] FAILED: {error_msg}")

    deployment.logs = combined_logs
    if deployment.status != "running":
        deployment.completed_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(deployment)
    print(f"[DEPLOY] Final status: {deployment.status}")
    return deployment


@router.post("/{project_id}/deploy", response_model=DeploymentResponse)
async def deploy_project(
    project_id: int,
    payload: DeployRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Deployment:
    """Trigger an AWS deployment (plan/apply) using boto3."""
    print(f"\n{'='*60}")
    print(f"[DEPLOY] === Deploy request: project_id={project_id}, action={payload.action} ===")
    print(f"{'='*60}")

    project = await _get_user_project(project_id, db, current_user)

    if payload.action not in ("plan", "apply"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Invalid action: {payload.action}. Use 'plan' or 'apply'.")

    try:
        arch, boto3_configs = await _load_boto3_config(project_id, db)
    except HTTPException:
        raise
    except Exception as e:
        print(f"[DEPLOY] ERROR loading config: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to load config: {e}")

    deployment = Deployment(
        project_id=project_id, architecture_version=arch.version,
        action=payload.action, status="running",
        started_at=datetime.now(timezone.utc),
    )
    db.add(deployment)
    await db.execute(
        update(Project).where(Project.id == project_id).values(status="deploying")
    )
    await db.commit()
    await db.refresh(deployment)

    print(f"[DEPLOY] Deployment record created: id={deployment.id}")

    try:
        deployment = await _run_boto3_deploy(
            payload.action, boto3_configs, deployment, project, current_user, db
        )
    except Exception as e:
        print(f"[DEPLOY] EXCEPTION: {e}")
        traceback.print_exc()
        deployment.status = "failed"
        deployment.error_message = str(e)
        deployment.logs = f"Internal error: {e}\n\n{traceback.format_exc()}"
        deployment.completed_at = datetime.now(timezone.utc)
        await db.execute(
            update(Project).where(Project.id == project_id).values(status="failed")
        )
        await db.commit()
        await db.refresh(deployment)

    print(f"[DEPLOY] === Deploy complete: status={deployment.status} ===\n")
    return deployment


@router.post("/{project_id}/deploy/stream")
async def deploy_project_stream(
    project_id: int,
    payload: DeployRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Stream-deploy: same as /deploy but returns an SSE text stream of logs."""
    project = await _get_user_project(project_id, db, current_user)

    if payload.action not in ("plan", "apply"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid action: {payload.action}. Use 'plan' or 'apply'.",
        )

    try:
        arch, boto3_configs = await _load_boto3_config(project_id, db)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load config: {e}")

    deployment = Deployment(
        project_id=project_id,
        architecture_version=arch.version,
        action=payload.action,
        status="running",
        started_at=datetime.now(timezone.utc),
    )
    db.add(deployment)
    await db.execute(
        update(Project).where(Project.id == project_id).values(status="deploying")
    )
    await db.commit()
    await db.refresh(deployment)

    async def _stream():
        from app.services.boto3.executor import Boto3Executor
        from app.services.boto3.state_tracker import StateTracker

        aws_creds = _get_aws_credentials(current_user)
        region = aws_creds.get("region") or project.region or "us-east-1"
        safe_name = project.name.lower().replace(" ", "-").replace("_", "-")
        safe_name = "".join(c for c in safe_name if c.isalnum() or c == "-")

        executor = Boto3Executor(
            aws_access_key_id=aws_creds.get("aws_access_key_id"),
            aws_secret_access_key=aws_creds.get("aws_secret_access_key"),
            region_name=region,
            project_name=safe_name,
        )
        state_tracker = StateTracker(db)
        combined_logs = ""

        # Build per-user LLM provider for in-loop repair (silently skip if not configured)
        _deploy_llm = None
        try:
            from app.services.ai.base import OpenAICompatibleProvider
            from app.core.security import decrypt_credentials as _dc_llm
            _llm_prefs = current_user.llm_preferences or {}
            if current_user.llm_api_key_encrypted:
                _deploy_llm = OpenAICompatibleProvider(
                    api_key=_dc_llm(current_user.llm_api_key_encrypted),
                    base_url=_llm_prefs.get("base_url"),
                    model=_llm_prefs.get("model"),
                )
        except Exception:
            pass  # No LLM configured — repair will be skipped silently

        flat_configs = Boto3Executor.flatten_configs(boto3_configs)
        flat_configs = _resolve_config_placeholders(flat_configs, safe_name, region)

        log_queue: asyncio.Queue[str | None] = asyncio.Queue()

        def log_cb(line: str):
            nonlocal combined_logs
            combined_logs += line + "\n"
            log_queue.put_nowait(line + "\n")

        async def _run_deploy():
            nonlocal combined_logs
            new_project_status = "failed"
            try:
                if payload.action == "apply":
                    log_cb("=== Starting AWS resource provisioning ===")
                    deployed_resources = await executor.deploy(flat_configs, log_cb, llm=_deploy_llm)

                    # Only track resources that were actually created
                    created_resources = [r for r in deployed_resources if r.get("status") == "created"]
                    created_count = len(created_resources)
                    total_count = len(deployed_resources)
                    log_cb(f"=== Provisioning complete: {created_count}/{total_count} resources created ===")

                    if created_resources:
                        state_tracker.save_resources(deployment, created_resources)

                    if created_count == 0:
                        deployment.status = "failed"
                        deployment.error_message = f"All {total_count} resource(s) failed to provision. Check logs for details."
                        new_project_status = "failed"
                    elif created_count < total_count:
                        deployment.status = "partial_deployed"
                        new_project_status = "partial_deployed"
                    else:
                        deployment.status = "success"
                        new_project_status = "deployed"
                else:
                    log_cb("=== Validating infrastructure configuration ===")
                    log_cb(f"Configuration contains {len(flat_configs)} operation(s)")
                    for cfg in flat_configs:
                        log_cb(f"  • {cfg.get('label', cfg.get('service', '?'))}.{cfg.get('action', '?')}")
                    log_cb("=== Validation complete (plan mode — no resources created) ===")
                    deployment.status = "success"
                    new_project_status = "ready"
            except Exception as e:
                error_msg = str(e)
                tb = traceback.format_exc()
                combined_logs += f"\n\nERROR: {error_msg}\n{tb}"
                short_err, detailed_err = _classify_deploy_error(combined_logs)
                deployment.status = "failed"
                deployment.error_message = short_err
                deployment.error_details = detailed_err
                new_project_status = "failed"
                log_cb(f"[ERROR] {error_msg}")
            finally:
                deployment.logs = combined_logs
                deployment.completed_at = datetime.now(timezone.utc)
                # Use a direct SQL UPDATE for project status to guarantee it is
                # persisted even when this runs inside an asyncio.create_task().
                await db.execute(
                    update(Project)
                    .where(Project.id == project_id)
                    .values(status=new_project_status)
                )
                await db.commit()
                print(f"[STREAM-DEPLOY] project_id={project_id} status set to '{new_project_status}' and committed.")
                log_queue.put_nowait(None)  # sentinel

        task = asyncio.create_task(_run_deploy())

        while True:
            item = await log_queue.get()
            if item is None:
                break
            # SSE format: each message is "data: {line}\n\n"
            # Strip trailing newline from item before wrapping so we don't double-newline
            yield f"data: {item.rstrip()}\n\n"
            await asyncio.sleep(0)  # yield control so uvicorn flushes this chunk immediately

        await task  # ensure cleanup

    return StreamingResponse(
        _stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",          # disables nginx/proxy buffering
            "Connection": "keep-alive",
        },
    )


@router.post("/{project_id}/destroy", response_model=DeploymentResponse)
async def destroy_project(
    project_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Deployment:
    """Destroy all deployed AWS resources using boto3."""
    print(f"\n{'='*60}")
    print(f"[DEPLOY] === Destroy request: project_id={project_id} ===")
    print(f"{'='*60}")

    project = await _get_user_project(project_id, db, current_user)

    # Find latest successful deployment to get its resource state
    dep_result = await db.execute(
        select(Deployment)
        .where(Deployment.project_id == project_id,
               Deployment.status.in_(["success", "deployed", "partial_deployed"]))
        .order_by(Deployment.created_at.desc())
        .limit(1)
    )
    prev_deployment = dep_result.scalar_one_or_none()

    try:
        arch, boto3_configs = await _load_boto3_config(project_id, db)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load config: {e}")

    deployment = Deployment(
        project_id=project_id, architecture_version=arch.version,
        action="destroy", status="running",
        started_at=datetime.now(timezone.utc),
    )
    # Copy resource state from prev deployment for the destroy to use
    if prev_deployment and prev_deployment.resource_state_json:
        deployment.resource_state_json = prev_deployment.resource_state_json

    db.add(deployment)
    await db.execute(
        update(Project).where(Project.id == project_id).values(status="destroying")
    )
    await db.commit()
    await db.refresh(deployment)

    try:
        deployment = await _run_boto3_deploy(
            "destroy", boto3_configs, deployment, project, current_user, db
        )
    except Exception as e:
        print(f"[DEPLOY] EXCEPTION: {e}")
        traceback.print_exc()
        deployment.status = "failed"
        deployment.error_message = str(e)
        deployment.logs = f"Internal error: {e}\n\n{traceback.format_exc()}"
        deployment.completed_at = datetime.now(timezone.utc)
        await db.execute(
            update(Project).where(Project.id == project_id).values(status="failed")
        )
        await db.commit()
        await db.refresh(deployment)

    # After a successful destroy, clear the original deploy deployment's state too
    # so that /resources returns empty and Monitoring shows no resources.
    if deployment.status == "destroyed" and prev_deployment and prev_deployment.resource_state_json is not None:
        prev_deployment.resource_state_json = None
        await db.commit()

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
        select(Deployment).where(Deployment.project_id == project_id)
        .order_by(Deployment.created_at.desc()).limit(1)
    )
    deployment = result.scalar_one_or_none()
    if not deployment:
        return {"status": "no_deployments", "project_id": project_id}

    return {
        "id": deployment.id, "project_id": project_id,
        "architecture_version": deployment.architecture_version,
        "action": deployment.action, "status": deployment.status,
        "logs": deployment.logs, "error_message": deployment.error_message,
        "error_details": _classify_deploy_error(deployment.logs or "")[1] if deployment.status == "failed" and deployment.logs else None,
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
        select(Deployment).where(Deployment.project_id == project_id)
        .order_by(Deployment.created_at.desc())
    )
    return list(result.scalars().all())


@router.get("/{project_id}/resources")
async def list_deployed_resources(
    project_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """List all resources tracked in the deployment state for a project."""
    from app.services.boto3.state_tracker import StateTracker

    await _get_user_project(project_id, db, current_user)
    state_tracker = StateTracker(db)

    dep_result = await db.execute(
        select(Deployment)
        .where(Deployment.project_id == project_id,
               Deployment.status.in_(["success", "deployed", "partial_deployed"]))
        .order_by(Deployment.created_at.desc()).limit(1)
    )
    deployment = dep_result.scalar_one_or_none()
    if not deployment:
        return {"project_id": project_id, "resources": [], "message": "No deployed resources found."}

    resources = state_tracker.get_resources(deployment)
    # Only show resources that were actually created (not failed provisioning attempts)
    resources = [r for r in resources if r.get("status") == "created"]
    formatted = [
        {"address": f"{r.get('resource_type', 'unknown')}.{r.get('label', 'resource')}",
         "type": r.get("resource_type", "unknown"),
         "name": r.get("label", "unknown"),
         "resource_id": r.get("resource_id", ""),
         "service": r.get("service", "")}
        for r in resources
    ]
    if not formatted:
        return {"project_id": project_id, "resources": [], "message": "No deployed resources found."}
    return {"project_id": project_id, "resources": formatted, "total": len(formatted)}


@router.post("/{project_id}/resource/destroy")
async def destroy_single_resource(
    project_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    payload: dict,
) -> dict:
    """Destroy a single deployed resource by its resource ID."""
    from app.services.boto3.executor import Boto3Executor
    from app.services.boto3.state_tracker import StateTracker

    resource_address = (payload or {}).get("resource_address", "").strip()
    if not resource_address:
        raise HTTPException(status_code=400, detail="resource_address is required")

    project = await _get_user_project(project_id, db, current_user)
    aws_creds = _get_aws_credentials(current_user)
    executor = Boto3Executor(
        aws_access_key_id=aws_creds.get("aws_access_key_id"),
        aws_secret_access_key=aws_creds.get("aws_secret_access_key"),
        region_name=aws_creds.get("region") or project.region or "us-east-1",
    )

    state_tracker = StateTracker(db)
    dep_result = await db.execute(
        select(Deployment)
        .where(Deployment.project_id == project_id,
               Deployment.status.in_(["success", "deployed", "partial_deployed"]))
        .order_by(Deployment.created_at.desc()).limit(1)
    )
    deployment = dep_result.scalar_one_or_none()
    if not deployment:
        raise HTTPException(status_code=400, detail="No deployment found.")

    resources = state_tracker.get_resources(deployment)
    target = None
    for r in resources:
        addr = f"{r.get('resource_type', '')}.{r.get('label', '')}"
        if addr == resource_address or r.get("resource_id") == resource_address:
            target = r
            break

    if not target:
        raise HTTPException(status_code=404, detail=f"Resource not found: {resource_address}")

    try:
        await executor.destroy_single(target)
        # Remove from state
        remaining = [r for r in resources if r != target]
        state_tracker.save_resources(deployment, remaining)
        await db.commit()
        return {"project_id": project_id, "resource_address": resource_address,
                "success": True, "message": "✓ Resource destroyed successfully."}
    except Exception as e:
        return {"project_id": project_id, "resource_address": resource_address,
                "success": False, "message": f"✗ Destroy failed: {e}"}


@router.post("/{project_id}/resources/batch-destroy")
async def destroy_multiple_resources(
    project_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    payload: dict,
) -> dict:
    """Destroy multiple deployed resources."""
    from app.services.boto3.executor import Boto3Executor
    from app.services.boto3.state_tracker import StateTracker

    addresses: list[str] = (payload or {}).get("resource_addresses", [])
    if not addresses:
        raise HTTPException(status_code=400, detail="resource_addresses list is required")
    if len(addresses) > 50:
        raise HTTPException(status_code=400, detail="Max 50 resources per batch")

    project = await _get_user_project(project_id, db, current_user)
    aws_creds = _get_aws_credentials(current_user)
    executor = Boto3Executor(
        aws_access_key_id=aws_creds.get("aws_access_key_id"),
        aws_secret_access_key=aws_creds.get("aws_secret_access_key"),
        region_name=aws_creds.get("region") or project.region or "us-east-1",
    )

    state_tracker = StateTracker(db)
    dep_result = await db.execute(
        select(Deployment)
        .where(Deployment.project_id == project_id,
               Deployment.status.in_(["success", "deployed", "partial_deployed"]))
        .order_by(Deployment.created_at.desc()).limit(1)
    )
    deployment = dep_result.scalar_one_or_none()
    if not deployment:
        raise HTTPException(status_code=400, detail="No deployment found.")

    resources = state_tracker.get_resources(deployment)
    results = []
    destroyed_addrs = set()

    for addr in addresses:
        target = None
        for r in resources:
            r_addr = f"{r.get('resource_type', '')}.{r.get('label', '')}"
            if r_addr == addr or r.get("resource_id") == addr:
                target = r
                break
        if not target:
            results.append({"resource_address": addr, "success": False, "output": "Resource not found"})
            continue
        try:
            await executor.destroy_single(target)
            destroyed_addrs.add(id(target))
            results.append({"resource_address": addr, "success": True, "output": "Destroyed"})
        except Exception as e:
            results.append({"resource_address": addr, "success": False, "output": str(e)})

    # Update state
    remaining = [r for r in resources if id(r) not in destroyed_addrs]
    state_tracker.save_resources(deployment, remaining)
    await db.commit()

    succeeded = sum(1 for r in results if r["success"])
    return {
        "project_id": project_id, "overall_success": succeeded == len(results),
        "total": len(results), "succeeded": succeeded,
        "failed": len(results) - succeeded, "results": results,
    }


# ── EC2 Key Pair helpers ────────────────────────────────────────────

@router.get("/{project_id}/ec2-keys")
async def list_ec2_keys(
    project_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """Return EC2 instances that have an associated key pair from the latest deployment."""
    from app.services.boto3.state_tracker import StateTracker

    await _get_user_project(project_id, db, current_user)
    state_tracker = StateTracker(db)

    dep_result = await db.execute(
        select(Deployment)
        .where(
            Deployment.project_id == project_id,
            Deployment.status.in_(["success", "deployed", "partial_deployed"]),
        )
        .order_by(Deployment.created_at.desc())
        .limit(1)
    )
    deployment = dep_result.scalar_one_or_none()
    if not deployment:
        return {"project_id": project_id, "keys": []}

    resources = state_tracker.get_resources(deployment)
    keys = []
    for r in resources:
        if r.get("service") == "ec2" and r.get("action") == "run_instances" and r.get("key_pair_name"):
            keys.append({
                "instance_id": r.get("resource_id", ""),
                "label": r.get("label", ""),
                "key_pair_name": r["key_pair_name"],
                "key_pair_id": r.get("key_pair_id", ""),
                "has_pem": bool(r.get("key_material")),
                "public_ip": r.get("public_ip", ""),
                "public_dns": r.get("public_dns", ""),
            })
    return {"project_id": project_id, "keys": keys}


@router.get("/{project_id}/ec2-key/{key_pair_name}/download")
async def download_ec2_key_pem(
    project_id: int,
    key_pair_name: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Download the PEM file for an EC2 key pair created during deployment."""
    from app.services.boto3.state_tracker import StateTracker
    from fastapi.responses import Response

    await _get_user_project(project_id, db, current_user)
    state_tracker = StateTracker(db)

    dep_result = await db.execute(
        select(Deployment)
        .where(
            Deployment.project_id == project_id,
            Deployment.status.in_(["success", "deployed", "partial_deployed"]),
        )
        .order_by(Deployment.created_at.desc())
        .limit(1)
    )
    deployment = dep_result.scalar_one_or_none()
    if not deployment:
        raise HTTPException(status_code=404, detail="No deployment found for this project.")

    resources = state_tracker.get_resources(deployment)
    for r in resources:
        if r.get("key_pair_name") == key_pair_name and r.get("key_material"):
            pem_content = r["key_material"]
            return Response(
                content=pem_content.encode("utf-8"),
                media_type="application/x-pem-file",
                headers={
                    "Content-Disposition": f'attachment; filename="{key_pair_name}.pem"',
                    "Content-Type": "application/x-pem-file",
                },
            )

    raise HTTPException(
        status_code=404,
        detail=f"PEM key material not found for '{key_pair_name}'. "
               "Key may have been created before this feature was added, or it already existed.",
    )
