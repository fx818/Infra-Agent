"""Create ECS Service tool — uses shared VPC infrastructure across multiple services."""
from typing import Any
from app.tools.base import BaseTool, ToolResult, ToolNode, ToolNodeConfig


# Fargate valid CPU → memory ranges (MiB)
_FARGATE_VALID = {
    256:  [512, 1024, 2048],
    512:  list(range(1024, 4097, 1024)),
    1024: list(range(2048, 8193, 1024)),
    2048: list(range(4096, 16385, 1024)),
    4096: list(range(8192, 30721, 1024)),
    8192: list(range(16384, 61441, 4096)),
    16384: list(range(32768, 122881, 8192)),
}

# Shared VPC terraform — written once, deduplicated at workspace level
_SHARED_ECS_NETWORKING = '''# ============================================================
# Shared ECS Networking (used by all ECS services)
# ============================================================
data "aws_availability_zones" "ecs_azs" {
  state = "available"
}

resource "aws_vpc" "shared_ecs_vpc" {
  cidr_block           = "10.100.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags = {
    Name = join("-", [var.project_name, "ecs-vpc"])
  }
}

resource "aws_internet_gateway" "shared_ecs_igw" {
  vpc_id = aws_vpc.shared_ecs_vpc.id
  tags = {
    Name = join("-", [var.project_name, "ecs-igw"])
  }
}

resource "aws_subnet" "shared_ecs_subnet_a" {
  vpc_id                  = aws_vpc.shared_ecs_vpc.id
  cidr_block              = "10.100.1.0/24"
  availability_zone       = data.aws_availability_zones.ecs_azs.names[0]
  map_public_ip_on_launch = true
  tags = {
    Name = join("-", [var.project_name, "ecs-subnet-a"])
  }
}

resource "aws_subnet" "shared_ecs_subnet_b" {
  vpc_id                  = aws_vpc.shared_ecs_vpc.id
  cidr_block              = "10.100.2.0/24"
  availability_zone       = data.aws_availability_zones.ecs_azs.names[1]
  map_public_ip_on_launch = true
  tags = {
    Name = join("-", [var.project_name, "ecs-subnet-b"])
  }
}

resource "aws_route_table" "shared_ecs_rt" {
  vpc_id = aws_vpc.shared_ecs_vpc.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.shared_ecs_igw.id
  }
  tags = {
    Name = join("-", [var.project_name, "ecs-rt"])
  }
}

resource "aws_route_table_association" "shared_ecs_rta_a" {
  subnet_id      = aws_subnet.shared_ecs_subnet_a.id
  route_table_id = aws_route_table.shared_ecs_rt.id
}

resource "aws_route_table_association" "shared_ecs_rta_b" {
  subnet_id      = aws_subnet.shared_ecs_subnet_b.id
  route_table_id = aws_route_table.shared_ecs_rt.id
}
# ============================================================
'''


def _valid_fargate_combo(cpu: int, memory: int) -> tuple[int, int]:
    """Snap to the nearest valid Fargate CPU/memory pair."""
    valid_cpus = sorted(_FARGATE_VALID.keys())
    actual_cpu = min(valid_cpus, key=lambda c: abs(c - cpu))
    valid_mems = _FARGATE_VALID[actual_cpu]
    actual_mem = min(valid_mems, key=lambda m: abs(m - memory))
    if actual_mem < valid_mems[0]:
        actual_mem = valid_mems[0]
    return actual_cpu, actual_mem


class CreateECSServiceTool(BaseTool):
    name = "create_ecs_service"
    description = (
        "Create an Amazon ECS Fargate service with cluster, task definition, IAM role, "
        "CloudWatch logs, and security group. Multiple ECS services share a single VPC."
    )
    category = "compute"
    parameters = {
        "type": "object",
        "properties": {
            "service_id": {
                "type": "string",
                "description": "Unique identifier for this service (e.g. 'api_service', 'worker').",
            },
            "label": {"type": "string", "description": "Human-readable label."},
            "cpu": {
                "type": "integer",
                "description": "Task CPU units. Valid: 256, 512, 1024, 2048, 4096.",
                "default": 256,
            },
            "memory": {
                "type": "integer",
                "description": "Task memory in MiB. Must be compatible with cpu.",
                "default": 512,
            },
            "container_port": {
                "type": "integer",
                "description": "Port the container listens on.",
                "default": 80,
            },
            "desired_count": {
                "type": "integer",
                "description": "Number of task replicas.",
                "default": 2,
            },
            "image": {
                "type": "string",
                "description": "Docker image URI.",
                "default": "nginx:latest",
            },
        },
        "required": ["service_id", "label"],
    }

    def execute(self, params: dict[str, Any]) -> ToolResult:
        sid = params["service_id"]
        label = params.get("label", sid)
        cpu = int(params.get("cpu", 256))
        memory = int(params.get("memory", 512))
        cpu, memory = _valid_fargate_combo(cpu, memory)
        port = params.get("container_port", 80)
        count = params.get("desired_count", 2)
        image = params.get("image", "nginx:latest")

        # Service-specific safe name for AWS resources (hyphens, no underscores)
        safe_sid = sid.lower().replace("_", "-")

        # Service-specific resources only — shared VPC is written via compute_shared.tf
        service_tf = f'''
# --- ECS Service: {safe_sid} ---
resource "aws_security_group" "{sid}_sg" {{
  name        = join("-", [var.project_name, "{safe_sid}", "sg"])
  description = "Security group for {safe_sid} ECS service"
  vpc_id      = aws_vpc.shared_ecs_vpc.id

  ingress {{
    from_port   = {port}
    to_port     = {port}
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }}

  egress {{
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }}

  tags = {{
    Name = join("-", [var.project_name, "{safe_sid}", "sg"])
  }}
}}

resource "aws_ecs_cluster" "{sid}_cluster" {{
  name = join("-", [var.project_name, "{safe_sid}"])
}}

resource "aws_iam_role" "{sid}_exec_role" {{
  name = join("-", [var.project_name, "{safe_sid}", "exec-role"])
  assume_role_policy = jsonencode({{
    Version = "2012-10-17"
    Statement = [{{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = {{ Service = "ecs-tasks.amazonaws.com" }}
    }}]
  }})
}}

resource "aws_iam_role_policy_attachment" "{sid}_exec_policy" {{
  role       = aws_iam_role.{sid}_exec_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}}

resource "aws_cloudwatch_log_group" "{sid}_logs" {{
  name              = "/ecs/{safe_sid}"
  retention_in_days = 14
}}

resource "aws_ecs_task_definition" "{sid}_task" {{
  family                   = join("-", [var.project_name, "{safe_sid}"])
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "{cpu}"
  memory                   = "{memory}"
  execution_role_arn       = aws_iam_role.{sid}_exec_role.arn

  container_definitions = jsonencode([{{
    name      = "{safe_sid}"
    image     = "{image}"
    cpu       = {cpu}
    memory    = {memory}
    essential = true
    portMappings = [{{
      containerPort = {port}
      hostPort      = {port}
      protocol      = "tcp"
    }}]
    logConfiguration = {{
      logDriver = "awslogs"
      options = {{
        "awslogs-group"         = "/ecs/{safe_sid}"
        "awslogs-region"        = var.region
        "awslogs-stream-prefix" = "ecs"
      }}
    }}
  }}])
}}

resource "aws_ecs_service" "{sid}" {{
  name            = join("-", [var.project_name, "{safe_sid}"])
  cluster         = aws_ecs_cluster.{sid}_cluster.id
  task_definition = aws_ecs_task_definition.{sid}_task.arn
  desired_count   = {count}
  launch_type     = "FARGATE"

  network_configuration {{
    assign_public_ip = true
    subnets          = [aws_subnet.shared_ecs_subnet_a.id, aws_subnet.shared_ecs_subnet_b.id]
    security_groups  = [aws_security_group.{sid}_sg.id]
  }}
}}
'''

        return ToolResult(
            node=ToolNode(
                id=sid,
                type="aws_ecs",
                label=label,
                config=ToolNodeConfig(
                    memory=memory,
                    extra={"cpu": cpu, "container_port": port, "desired_count": count, "image": image},
                ),
            ),
            terraform_code={
                "compute_shared.tf": _SHARED_ECS_NETWORKING,
                "compute.tf": service_tf,
            },
        )
