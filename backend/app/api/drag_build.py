"""
Drag Build API — save drag-and-drop canvas as a project with architecture.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.models.project import Project
from app.models.architecture import Architecture
from app.models.user import User
from app.schemas.project import ProjectResponse

import json

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
                "id": n.id,
                "type": "awsService",
                "position": n.position,
                "data": {"label": n.label, "service_type": n.type},
                "style": {},
            }
            for n in payload.nodes
        ],
        "edges": [
            {
                "id": e.id,
                "source": e.source,
                "target": e.target,
                "label": e.label,
                "animated": True,
                "style": {},
            }
            for e in payload.edges
        ],
    }

    # 4. Generate basic terraform stubs
    terraform_stubs = _generate_terraform_stubs(payload.nodes, payload.region)

    architecture = Architecture(
        project_id=project.id,
        version=1,
        intent_json=json.dumps({
            "app_type": "custom",
            "scale": "medium",
            "latency_requirement": "standard",
            "storage_type": "mixed",
            "realtime": False,
            "constraints": [],
        }),
        graph_json=json.dumps(graph_data),
        terraform_files_json=json.dumps({"files": {"main.tf": terraform_stubs}}),
        cost_json=json.dumps({
            "estimated_monthly_cost": 0,
            "currency": "USD",
            "breakdown": [],
        }),
        visual_json=json.dumps(visual_data),
    )
    db.add(architecture)

    await db.commit()
    await db.refresh(project)
    return project


def _generate_terraform_stubs(nodes: list[CanvasNode], region: str) -> str:
    """Generate basic Terraform stub code from canvas nodes."""
    lines = [
        f'provider "aws" {{',
        f'  region = "{region}"',
        f'}}',
        '',
    ]

    for node in nodes:
        clean_id = node.id.replace("-", "_")
        svc = node.type.replace("aws_", "")

        if svc == "ec2":
            lines += [
                f'resource "aws_instance" "{clean_id}" {{',
                f'  ami           = "ami-0c02fb55956c7d316"  # Amazon Linux 2',
                f'  instance_type = "{node.config.get("instance_type", "t3.micro")}"',
                f'  tags = {{ Name = "{node.label}" }}',
                f'}}',
                '',
            ]
        elif svc == "s3":
            lines += [
                f'resource "aws_s3_bucket" "{clean_id}" {{',
                f'  bucket = "{clean_id.replace("_", "-")}-bucket"',
                f'  tags = {{ Name = "{node.label}" }}',
                f'}}',
                '',
            ]
        elif svc in ("rds", "aurora"):
            lines += [
                f'resource "aws_db_instance" "{clean_id}" {{',
                f'  engine         = "{node.config.get("engine", "postgres")}"',
                f'  instance_class = "{node.config.get("instance_type", "db.t3.micro")}"',
                f'  allocated_storage = 20',
                f'  tags = {{ Name = "{node.label}" }}',
                f'}}',
                '',
            ]
        elif svc == "lambda":
            lines += [
                f'resource "aws_lambda_function" "{clean_id}" {{',
                f'  function_name = "{clean_id}"',
                f'  runtime       = "{node.config.get("runtime", "python3.12")}"',
                f'  handler       = "index.handler"',
                f'  role          = aws_iam_role.lambda_role.arn',
                f'  tags = {{ Name = "{node.label}" }}',
                f'}}',
                '',
            ]
        elif svc == "vpc":
            lines += [
                f'resource "aws_vpc" "{clean_id}" {{',
                f'  cidr_block = "10.0.0.0/16"',
                f'  tags = {{ Name = "{node.label}" }}',
                f'}}',
                '',
            ]
        elif svc == "sqs":
            lines += [
                f'resource "aws_sqs_queue" "{clean_id}" {{',
                f'  name = "{clean_id}"',
                f'  tags = {{ Name = "{node.label}" }}',
                f'}}',
                '',
            ]
        elif svc == "sns":
            lines += [
                f'resource "aws_sns_topic" "{clean_id}" {{',
                f'  name = "{clean_id}"',
                f'  tags = {{ Name = "{node.label}" }}',
                f'}}',
                '',
            ]
        elif svc == "dynamodb":
            lines += [
                f'resource "aws_dynamodb_table" "{clean_id}" {{',
                f'  name         = "{clean_id}"',
                f'  billing_mode = "PAY_PER_REQUEST"',
                f'  hash_key     = "id"',
                f'  attribute {{ name = "id"  type = "S" }}',
                f'  tags = {{ Name = "{node.label}" }}',
                f'}}',
                '',
            ]
        elif svc == "elb":
            lines += [
                f'resource "aws_lb" "{clean_id}" {{',
                f'  name               = "{clean_id.replace("_", "-")}"',
                f'  load_balancer_type = "application"',
                f'  tags = {{ Name = "{node.label}" }}',
                f'}}',
                '',
            ]
        elif svc == "cloudfront":
            lines += [
                f'resource "aws_cloudfront_distribution" "{clean_id}" {{',
                f'  enabled = true',
                f'  # Configure origin and cache behavior',
                f'  tags = {{ Name = "{node.label}" }}',
                f'}}',
                '',
            ]
        else:
            lines += [
                f'# TODO: Configure {node.type} - {node.label}',
                f'# Service: {svc}',
                '',
            ]

    return '\n'.join(lines)
