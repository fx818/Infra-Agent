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

    # 4. Generate correct multi-file Terraform
    terraform_files = _generate_terraform_files(payload.nodes, payload.region)

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
        terraform_files_json=json.dumps({"files": terraform_files}),
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

    # 1. Fetch and verify ownership
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.user_id == current_user.id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # 2. Update project metadata
    project.name = payload.name
    project.description = payload.description or f"Drag & drop project with {len(payload.nodes)} services"

    # 3. Build architecture graph
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

    # 4. Build visual graph for ReactFlow rendering
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

    # 5. Regenerate correct multi-file Terraform
    terraform_files = _generate_terraform_files(payload.nodes, payload.region)

    # 6. Find existing latest architecture and update it (or create if missing)
    arch_result = await db.execute(
        select(Architecture)
        .where(Architecture.project_id == project_id)
        .order_by(Architecture.version.desc())
    )
    latest_arch = arch_result.scalars().first()

    if latest_arch:
        # Create a new version row (same as AI edit workflow)
        new_version = latest_arch.version + 1
        new_arch = Architecture(
            project_id=project_id,
            version=new_version,
            intent_json=latest_arch.intent_json,  # preserve intent
            graph_json=json.dumps(graph_data),
            terraform_files_json=json.dumps({"files": terraform_files}),
            cost_json=latest_arch.cost_json,  # preserve existing cost estimate
            visual_json=json.dumps(visual_data),
        )
        db.add(new_arch)
    else:
        # First-time architecture for this project
        new_arch = Architecture(
            project_id=project_id,
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
            terraform_files_json=json.dumps({"files": terraform_files}),
            cost_json=json.dumps({
                "estimated_monthly_cost": 0,
                "currency": "USD",
                "breakdown": [],
            }),
            visual_json=json.dumps(visual_data),
        )
        db.add(new_arch)

    await db.commit()
    await db.refresh(project)
    return project


def _generate_terraform_files(nodes: list[CanvasNode], region: str) -> dict[str, str]:
    """
    Generate correct, deployable Terraform files from canvas nodes.
    Returns a dict of filename -> content (multi-file structure).
    All boolean attributes use proper HCL booleans (true/false, never strings).
    """
    safe_region = region or "us-east-1"

    # ── providers.tf ──────────────────────────────────────────────
    providers_tf = f'''terraform {{
  required_version = ">= 1.3"
  required_providers {{
    aws = {{
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }}
  }}
}}

provider "aws" {{
  region = var.region
}}
'''

    # ── variables.tf ──────────────────────────────────────────────
    variables_tf = f'''variable "region" {{
  type    = string
  default = "{safe_region}"
}}

variable "project_name" {{
  type    = string
  default = "infra-agent-project"
}}
'''

    # ── outputs.tf ────────────────────────────────────────────────
    outputs: list[str] = []

    # ── Resource blocks grouped by file ───────────────────────────
    compute_blocks:     list[str] = []
    storage_blocks:     list[str] = []
    networking_blocks:  list[str] = []
    database_blocks:    list[str] = []
    messaging_blocks:   list[str] = []
    security_blocks:    list[str] = []
    cdn_blocks:         list[str] = []

    for node in nodes:
        rid = node.id.replace("-", "_")
        rname = node.label.lower().replace(" ", "-").replace("_", "-")
        svc = node.type.replace("aws_", "").lower()

        if svc == "ec2":
            itype = node.config.get("instance_type", "t3.micro")
            compute_blocks.append(f'''resource "aws_instance" "{rid}" {{
  ami           = "ami-0c02fb55956c7d316"
  instance_type = "{itype}"

  tags = {{
    Name    = "{rname}"
    Project = var.project_name
  }}
}}''')
            outputs.append(f'''output "{rid}_public_ip" {{
  value = aws_instance.{rid}.public_ip
}}''')

        elif svc in ("ecs", "fargate"):
            memory = node.config.get("memory", 512)
            cpu = node.config.get("cpu", 256)
            image = node.config.get("image", "nginx:latest")
            port = node.config.get("container_port", 80)
            compute_blocks.append(f'''resource "aws_ecs_cluster" "{rid}_cluster" {{
  name = "${{var.project_name}}-{rid}"
  tags = {{ Project = var.project_name }}
}}

resource "aws_cloudwatch_log_group" "{rid}_logs" {{
  name              = "/ecs/${{var.project_name}}-{rid}"
  retention_in_days = 14
}}

resource "aws_iam_role" "{rid}_exec_role" {{
  name = "${{var.project_name}}-{rid}-exec"
  assume_role_policy = jsonencode({{
    Version = "2012-10-17"
    Statement = [{{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = {{ Service = "ecs-tasks.amazonaws.com" }}
    }}]
  }})
}}

resource "aws_iam_role_policy_attachment" "{rid}_exec_policy" {{
  role       = aws_iam_role.{rid}_exec_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}}

resource "aws_ecs_task_definition" "{rid}_task" {{
  family                   = "${{var.project_name}}-{rid}"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = {cpu}
  memory                   = {memory}
  execution_role_arn       = aws_iam_role.{rid}_exec_role.arn

  container_definitions = jsonencode([
    {{
      name      = "{rid}"
      image     = "{image}"
      cpu       = {cpu}
      memory    = {memory}
      essential = true
      portMappings = [{{
        containerPort = {port}
        protocol      = "tcp"
      }}]
      logConfiguration = {{
        logDriver = "awslogs"
        options = {{
          "awslogs-group"         = "/ecs/${{var.project_name}}-{rid}"
          "awslogs-region"        = var.region
          "awslogs-stream-prefix" = "ecs"
        }}
      }}
    }}
  ])
}}''')

        elif svc == "lambda":
            runtime = node.config.get("runtime", "python3.12")
            compute_blocks.append(f'''resource "aws_iam_role" "{rid}_role" {{
  name = "${{var.project_name}}-{rid}"
  assume_role_policy = jsonencode({{
    Version = "2012-10-17"
    Statement = [{{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = {{ Service = "lambda.amazonaws.com" }}
    }}]
  }})
}}

resource "aws_iam_role_policy_attachment" "{rid}_basic" {{
  role       = aws_iam_role.{rid}_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}}

resource "aws_lambda_function" "{rid}" {{
  function_name = "${{var.project_name}}-{rid}"
  runtime       = "{runtime}"
  handler       = "index.handler"
  role          = aws_iam_role.{rid}_role.arn
  filename      = "{rid}.zip"

  tags = {{ Project = var.project_name }}
}}''')
            outputs.append(f'''output "{rid}_arn" {{
  value = aws_lambda_function.{rid}.arn
}}''')

        elif svc == "s3":
            bucket_name = f'${{var.project_name}}-{rname}'
            storage_blocks.append(f'''resource "aws_s3_bucket" "{rid}" {{
  bucket = "{bucket_name}"

  tags = {{
    Name    = "{rname}"
    Project = var.project_name
  }}
}}

resource "aws_s3_bucket_versioning" "{rid}_versioning" {{
  bucket = aws_s3_bucket.{rid}.id
  versioning_configuration {{
    status = "Enabled"
  }}
}}

resource "aws_s3_bucket_public_access_block" "{rid}_pab" {{
  bucket                  = aws_s3_bucket.{rid}.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}}''')
            outputs.append(f'''output "{rid}_bucket" {{
  value = aws_s3_bucket.{rid}.bucket
}}''')

        elif svc in ("rds", "aurora"):
            engine = node.config.get("engine", "postgres")
            iclass = node.config.get("instance_type", "db.t3.micro")
            database_blocks.append(f'''resource "aws_db_instance" "{rid}" {{
  identifier           = "${{var.project_name}}-{rname}"
  engine               = "{engine}"
  instance_class       = "{iclass}"
  allocated_storage    = 20
  username             = "admin"
  password             = "changeme123!"
  skip_final_snapshot  = true
  publicly_accessible  = false
  multi_az             = false

  tags = {{
    Name    = "{rname}"
    Project = var.project_name
  }}
}}''')
            outputs.append(f'''output "{rid}_endpoint" {{
  value = aws_db_instance.{rid}.endpoint
}}''')

        elif svc == "dynamodb":
            database_blocks.append(f'''resource "aws_dynamodb_table" "{rid}" {{
  name         = "${{var.project_name}}-{rname}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "id"

  attribute {{
    name = "id"
    type = "S"
  }}

  tags = {{
    Name    = "{rname}"
    Project = var.project_name
  }}
}}''')

        elif svc == "elasticache":
            engine = node.config.get("engine", "redis")
            itype = node.config.get("instance_type", "cache.t3.micro")
            database_blocks.append(f'''resource "aws_elasticache_cluster" "{rid}" {{
  cluster_id           = "${{var.project_name}}-{rname}"
  engine               = "{engine}"
  node_type            = "{itype}"
  num_cache_nodes      = 1
  parameter_group_name = "default.{engine}6.x" if engine == "redis" else "default.{engine}1.4"
  port                 = 6379

  tags = {{
    Name    = "{rname}"
    Project = var.project_name
  }}
}}''')

        elif svc == "vpc":
            networking_blocks.append(f'''resource "aws_vpc" "{rid}" {{
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {{
    Name    = "{rname}"
    Project = var.project_name
  }}
}}

resource "aws_internet_gateway" "{rid}_igw" {{
  vpc_id = aws_vpc.{rid}.id
  tags   = {{ Name = "{rname}-igw", Project = var.project_name }}
}}

resource "aws_subnet" "{rid}_public_1" {{
  vpc_id                  = aws_vpc.{rid}.id
  cidr_block              = "10.0.1.0/24"
  availability_zone       = "${{var.region}}a"
  map_public_ip_on_launch = true
  tags                    = {{ Name = "{rname}-public-1", Project = var.project_name }}
}}

resource "aws_subnet" "{rid}_public_2" {{
  vpc_id                  = aws_vpc.{rid}.id
  cidr_block              = "10.0.2.0/24"
  availability_zone       = "${{var.region}}b"
  map_public_ip_on_launch = true
  tags                    = {{ Name = "{rname}-public-2", Project = var.project_name }}
}}

resource "aws_subnet" "{rid}_private_1" {{
  vpc_id            = aws_vpc.{rid}.id
  cidr_block        = "10.0.3.0/24"
  availability_zone = "${{var.region}}a"
  tags              = {{ Name = "{rname}-private-1", Project = var.project_name }}
}}

resource "aws_subnet" "{rid}_private_2" {{
  vpc_id            = aws_vpc.{rid}.id
  cidr_block        = "10.0.4.0/24"
  availability_zone = "${{var.region}}b"
  tags              = {{ Name = "{rname}-private-2", Project = var.project_name }}
}}''')

        elif svc in ("elb", "alb", "nlb"):
            networking_blocks.append(f'''resource "aws_lb" "{rid}" {{
  name               = "${{var.project_name}}-{rname}"
  internal           = false
  load_balancer_type = "application"
  tags               = {{ Name = "{rname}", Project = var.project_name }}
}}''')
            outputs.append(f'''output "{rid}_dns" {{
  value = aws_lb.{rid}.dns_name
}}''')

        elif svc == "security_group":
            security_blocks.append(f'''resource "aws_security_group" "{rid}" {{
  name        = "${{var.project_name}}-{rname}"
  description = "Security group for {rname}"

  ingress {{
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }}

  egress {{
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }}

  tags = {{ Name = "{rname}", Project = var.project_name }}
}}''')

        elif svc in ("sqs",):
            messaging_blocks.append(f'''resource "aws_sqs_queue" "{rid}" {{
  name                      = "${{var.project_name}}-{rname}"
  delay_seconds             = 0
  message_retention_seconds = 86400

  tags = {{ Name = "{rname}", Project = var.project_name }}
}}''')

        elif svc in ("sns",):
            messaging_blocks.append(f'''resource "aws_sns_topic" "{rid}" {{
  name = "${{var.project_name}}-{rname}"
  tags = {{ Name = "{rname}", Project = var.project_name }}
}}''')

        elif svc == "cloudfront":
            cdn_blocks.append(f'''# NOTE: CloudFront requires an existing origin. Update origin_domain_name below.
resource "aws_cloudfront_distribution" "{rid}" {{
  enabled             = true
  default_root_object = "index.html"

  origin {{
    domain_name = "example.com"  # TODO: replace with actual origin
    origin_id   = "{rid}-origin"
  }}

  default_cache_behavior {{
    allowed_methods        = ["GET", "HEAD"]
    cached_methods         = ["GET", "HEAD"]
    target_origin_id       = "{rid}-origin"
    viewer_protocol_policy = "redirect-to-https"

    forwarded_values {{
      query_string = false
      cookies {{
        forward = "none"
      }}
    }}
  }}

  restrictions {{
    geo_restriction {{
      restriction_type = "none"
    }}
  }}

  viewer_certificate {{
    cloudfront_default_certificate = true
  }}

  tags = {{ Name = "{rname}", Project = var.project_name }}
}}''')
            outputs.append(f'''output "{rid}_domain" {{
  value = aws_cloudfront_distribution.{rid}.domain_name
}}''')

        else:
            # Generic placeholder for unrecognised service types
            compute_blocks.append(f'# TODO: {node.type} ({node.label}) — add Terraform resource here')

    # Build file map
    files: dict[str, str] = {
        "providers.tf": providers_tf,
        "variables.tf": variables_tf,
    }

    def _join(blocks: list[str]) -> str:
        return "\n\n".join(blocks)

    if compute_blocks:
        files["compute.tf"] = _join(compute_blocks)
    if storage_blocks:
        files["storage.tf"] = _join(storage_blocks)
    if database_blocks:
        files["database.tf"] = _join(database_blocks)
    if networking_blocks:
        files["networking.tf"] = _join(networking_blocks)
    if messaging_blocks:
        files["messaging.tf"] = _join(messaging_blocks)
    if security_blocks:
        files["security.tf"] = _join(security_blocks)
    if cdn_blocks:
        files["cdn.tf"] = _join(cdn_blocks)
    if outputs:
        files["outputs.tf"] = "\n\n".join(outputs)

    return files

