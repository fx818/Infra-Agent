"""
Architecture API routes — generate, edit, cost, and retrieve architectures.
"""

import json
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from openai import AuthenticationError, APIConnectionError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.models.architecture import Architecture
from app.models.chat import ChatMessage
from app.models.project import Project
from app.models.user import User
from app.schemas.architecture import (
    ArchitectureGraph,
    ArchitectureResponse,
    CostEstimate,
    IntentOutput,
    TerraformFileMap,
    VisualGraph,
)
from app.schemas.chat import ChatMessageResponse
from app.schemas.project import ProjectEditRequest, ProjectGenerateRequest
from app.services.ai.architecture_agent import ArchitectureAgent
from app.services.ai.cost_agent import CostAgent
from app.services.ai.edit_agent import EditAgent
from app.services.ai.intent_agent import IntentAgent
from app.services.ai.terraform_agent import TerraformAgent
from app.services.ai.tool_agent import ToolAgent
from app.services.ai.visual_agent import VisualAgent
from app.services.terraform.workspace_manager import WorkspaceManager
from app.utils.validators import sanitize_terraform_files, validate_architecture_graph

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/projects", tags=["architecture"])


async def _get_user_project(
    project_id: int,
    db: AsyncSession,
    current_user: User,
) -> Project:
    """Helper to fetch a user-owned project or raise 404."""
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.user_id == current_user.id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


def _parse_json(data: Any) -> Any:
    """Helper to ensure we have a dict/list from JSON columns."""
    if isinstance(data, str):
        try:
            return json.loads(data)
        except (json.JSONDecodeError, TypeError):
            return data
    return data


def _get_llm_provider_for_user(user: User) -> BaseLLMProvider:
    """Create an LLM provider configured with the user's settings."""
    from app.core.security import decrypt_credentials
    from app.services.ai.base import OpenAICompatibleProvider

    llm_prefs = user.llm_preferences or {}
    api_key_encrypted = user.llm_api_key_encrypted
    
    if not api_key_encrypted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="LLM API Key not configured. Please go to Settings > AI Configuration to set up your API key.",
        )

    api_key = decrypt_credentials(api_key_encrypted)

    return OpenAICompatibleProvider(
        api_key=api_key,
        base_url=llm_prefs.get("base_url"),
        model=llm_prefs.get("model"),
    )


@router.post("/{project_id}/generate", response_model=ArchitectureResponse)
async def generate_architecture(
    project_id: int,
    payload: ProjectGenerateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """
    Full generation pipeline: NL → Intent → Architecture → Terraform → Cost → Visual.
    """
    project = await _get_user_project(project_id, db, current_user)

    # Update project status
    project.status = "generating"
    project.natural_language_input = payload.natural_language_input
    await db.commit()

    try:
        # Configure LLM for this user
        llm = _get_llm_provider_for_user(current_user)

        # 1. Tool Agent — uses LLM tool-calling to build architecture + terraform in one step
        tool_agent = ToolAgent(llm=llm)
        agent_result = await tool_agent.run(
            user_prompt=payload.natural_language_input,
            region=project.region,
            project_name=project.name,
        )

        graph = agent_result["graph"]
        terraform_files = agent_result["terraform"]

        # 2. Validate architecture
        errors = validate_architecture_graph(graph)
        if errors:
            logger.warning("Architecture validation warnings: %s", errors)

        # 3. Sanitize Terraform
        is_safe, issues = sanitize_terraform_files(terraform_files.files)
        if not is_safe:
            logger.warning("Terraform sanitization issues: %s", issues)

        # 4. Build a lightweight intent for backwards compat with the DB schema
        intent = IntentOutput(
            app_type="tool_generated",
            scale="medium",
            latency_requirement="moderate",
            storage_type="object",
            realtime=False,
            constraints=[],
        )

        # 5. Cost Agent
        cost_agent = CostAgent(llm=llm)
        cost = await cost_agent.run(graph, scale=intent.scale)

        # 6. Visual Agent
        visual_agent = VisualAgent(llm=llm)
        visual = await visual_agent.run(graph)

        # 7. Write Terraform files to workspace
        workspace_mgr = WorkspaceManager()
        workspace_mgr.write_terraform_files(project_id, terraform_files.files)

        # 8. Get current version
        result = await db.execute(
            select(Architecture)
            .where(Architecture.project_id == project_id)
            .order_by(Architecture.version.desc())
        )
        latest = result.scalars().first()
        new_version = (latest.version + 1) if latest else 1

        # 9. Save architecture
        architecture = Architecture(
            project_id=project_id,
            version=new_version,
            intent_json=intent.model_dump(),
            graph_json=graph.model_dump(by_alias=True),
            terraform_files_json=terraform_files.model_dump(),
            cost_json=cost.model_dump(),
            visual_json=visual.model_dump(),
        )
        db.add(architecture)

        # Save chat messages
        user_msg = ChatMessage(
            project_id=project_id,
            role="user",
            content=payload.natural_language_input,
            architecture_version=new_version,
        )
        assistant_msg = ChatMessage(
            project_id=project_id,
            role="assistant",
            content=(
                f"Generated architecture v{new_version} with {len(graph.nodes)} AWS services "
                f"using {agent_result.get('tool_calls_count', 0)} tool calls.\n\n"
                f"{agent_result.get('summary', '')}"
            ),
            architecture_version=new_version,
        )
        db.add_all([user_msg, assistant_msg])

        project.status = "ready"
        await db.commit()
        await db.refresh(architecture)

        return {
            "id": architecture.id,
            "project_id": project_id,
            "version": new_version,
            "intent": intent.model_dump(),
            "graph": graph.model_dump(by_alias=True),
            "terraform_files": terraform_files.model_dump(),
            "cost": cost.model_dump(),
            "visual": visual.model_dump(),
        }

    except HTTPException:
        raise
    except AuthenticationError as e:
        project.status = "failed"
        await db.commit()
        logger.error(f"LLM Authentication Failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="LLM Authentication Failed. Please check your API Key in Settings.",
        )
    except APIConnectionError as e:
        project.status = "failed"
        await db.commit()
        logger.error(f"LLM Connection Failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to connect to LLM provider. Please check your Base URL and internet connection.",
        )
    except Exception as e:
        project.status = "failed"
        await db.commit()
        logger.exception("Architecture generation failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Generation failed: {str(e)}",
        )


@router.post("/{project_id}/edit", response_model=ArchitectureResponse)
async def edit_architecture(
    project_id: int,
    payload: ProjectEditRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Architecture:
    """
    Edit existing architecture: Edit → Terraform Regen → Cost → Visual → Version++.
    """
    project = await _get_user_project(project_id, db, current_user)

    # Get latest architecture
    result = await db.execute(
        select(Architecture)
        .where(Architecture.project_id == project_id)
        .order_by(Architecture.version.desc())
    )
    latest = result.scalars().first()
    if not latest:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No architecture exists. Generate one first.",
        )

    current_graph = ArchitectureGraph(**_parse_json(latest.graph_json))
    current_intent_raw = _parse_json(latest.intent_json)
    current_intent = IntentOutput(**current_intent_raw) if current_intent_raw else None

    project.status = "generating"
    await db.commit()

    try:
        # Configure LLM for this user
        llm = _get_llm_provider_for_user(current_user)

        # 1. Edit Agent
        edit_agent = EditAgent(llm=llm)
        modified_graph = await edit_agent.run(current_graph, payload.modification_prompt)

        # 2. Validate
        errors = validate_architecture_graph(modified_graph)
        if errors:
            logger.warning("Modified architecture validation warnings: %s", errors)

        # 3. Regenerate Terraform
        tf_agent = TerraformAgent(llm=llm)
        terraform_files = await tf_agent.run(modified_graph, region=project.region, project_name=project.name)

        # 4. Sanitize
        is_safe, issues = sanitize_terraform_files(terraform_files.files)
        if not is_safe:
            logger.warning("Terraform sanitization issues: %s", issues)

        # 5. Cost
        cost_agent = CostAgent(llm=llm)
        scale = current_intent.scale if current_intent else "medium"
        cost = await cost_agent.run(modified_graph, scale=scale)

        # 6. Visual
        visual_agent = VisualAgent(llm=llm)
        visual = await visual_agent.run(modified_graph)

        # 7. Write files
        workspace_mgr = WorkspaceManager()
        workspace_mgr.write_terraform_files(project_id, terraform_files.files)

        # 8. Save new version
        new_version = latest.version + 1
        architecture = Architecture(
            project_id=project_id,
            version=new_version,
            intent_json=latest.intent_json,
            graph_json=modified_graph.model_dump(by_alias=True),
            terraform_files_json=terraform_files.model_dump(),
            cost_json=cost.model_dump(),
            visual_json=visual.model_dump(),
        )
        db.add(architecture)

        # Chat messages
        user_msg = ChatMessage(
            project_id=project_id, role="user",
            content=payload.modification_prompt, architecture_version=new_version,
        )
        assistant_msg = ChatMessage(
            project_id=project_id, role="assistant",
            content=f"Updated architecture to v{new_version}.",
            architecture_version=new_version,
        )
        db.add_all([user_msg, assistant_msg])

        project.status = "ready"
        await db.commit()
        await db.refresh(architecture)

        # Map to response schema
        return {
            "id": architecture.id,
            "project_id": architecture.project_id,
            "version": architecture.version,
            "intent": _parse_json(architecture.intent_json),
            "graph": _parse_json(architecture.graph_json),
            "terraform_files": _parse_json(architecture.terraform_files_json),
            "cost": _parse_json(architecture.cost_json),
            "visual": _parse_json(architecture.visual_json),
        }

    except HTTPException:
        raise
    except AuthenticationError as e:
        project.status = "failed"
        await db.commit()
        logger.error(f"LLM Authentication Failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="LLM Authentication Failed. Please check your API Key in Settings.",
        )
    except APIConnectionError as e:
        project.status = "failed"
        await db.commit()
        logger.error(f"LLM Connection Failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to connect to LLM provider. Please check your Base URL and internet connection.",
        )
    except Exception as e:
        project.status = "failed"
        await db.commit()
        logger.exception("Architecture edit failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Edit failed: {str(e)}",
        )


@router.get("/{project_id}/architecture", response_model=ArchitectureResponse)
async def get_architecture(
    project_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Architecture:
    """Get the latest architecture for a project."""
    await _get_user_project(project_id, db, current_user)

    result = await db.execute(
        select(Architecture)
        .where(Architecture.project_id == project_id)
        .order_by(Architecture.version.desc())
    )
    arch = result.scalars().first()
    if not arch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No architecture found")

    graph_data = _parse_json(arch.graph_json)
    visual_data = _parse_json(arch.visual_json)

    # Fallback: If visual layout is missing but graph exists, generate it on the fly
    if not visual_data and graph_data:
        try:
            llm = _get_llm_provider_for_user(current_user)
            visual_agent = VisualAgent(llm=llm)
            # We need to wrap graph_data in ArchitectureGraph for the agent
            temp_graph = ArchitectureGraph(**graph_data)
            generated_visual = await visual_agent.run(temp_graph)
            visual_data = generated_visual.model_dump()
            
            # Optional: Persist this back to DB so we don't re-generate next time
            arch.visual_json = visual_data
            await db.commit()
        except Exception as e:
            logger.error(f"Failed to generate fallback visual data: {e}")

    return {
        "id": arch.id,
        "project_id": arch.project_id,
        "version": arch.version,
        "intent": _parse_json(arch.intent_json),
        "graph": graph_data,
        "terraform_files": _parse_json(arch.terraform_files_json),
        "cost": _parse_json(arch.cost_json),
        "visual": visual_data,
    }

@router.get("/{project_id}/cost")
async def get_cost(
    project_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """Get the latest cost estimate for a project."""
    await _get_user_project(project_id, db, current_user)

    result = await db.execute(
        select(Architecture)
        .where(Architecture.project_id == project_id)
        .order_by(Architecture.version.desc())
    )
    arch = result.scalars().first()
    if not arch or not arch.cost_json:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No cost estimate found")

    return json.loads(arch.cost_json)


@router.get("/{project_id}/messages", response_model=list[ChatMessageResponse])
async def get_chat_history(
    project_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list:
    """Get chat history for a project."""
    await _get_user_project(project_id, db, current_user)

    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.project_id == project_id)
        .order_by(ChatMessage.created_at.asc())
    )
    return list(result.scalars().all())
