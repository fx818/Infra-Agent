"""Create ECS Service tool."""
from typing import Any
from app.tools.base import BaseTool, ToolResult, ToolNode, ToolNodeConfig


class CreateECSServiceTool(BaseTool):
    name = "create_ecs_service"
    description = (
        "Create an Amazon ECS (Elastic Container Service) cluster with a Fargate service "
        "and task definition. Ideal for running containerized applications, microservices, "
        "and long-running processes."
    )
    category = "compute"
    parameters = {
        "type": "object",
        "properties": {
            "service_id": {"type": "string", "description": "Unique identifier (e.g., 'api_service')."},
            "label": {"type": "string", "description": "Human-readable label."},
            "cpu": {"type": "integer", "description": "Task CPU units (256, 512, 1024, 2048, 4096).", "default": 256},
            "memory": {"type": "integer", "description": "Task memory in MB.", "default": 512},
            "container_port": {"type": "integer", "description": "Container port to expose.", "default": 80},
            "desired_count": {"type": "integer", "description": "Number of tasks to run.", "default": 2},
            "image": {"type": "string", "description": "Docker image URI.", "default": "nginx:latest"},
        },
        "required": ["service_id", "label"],
    }

    def execute(self, params: dict[str, Any]) -> ToolResult:
        sid = params["service_id"]
        label = params.get("label", sid)
        cpu = params.get("cpu", 256)
        memory = params.get("memory", 512)
        port = params.get("container_port", 80)
        count = params.get("desired_count", 2)
        image = params.get("image", "nginx:latest")

        tf_code = f'''resource "aws_ecs_cluster" "{sid}_cluster" {{
  name = "${{var.project_name}}-{sid}"
}}

resource "aws_ecs_task_definition" "{sid}_task" {{
  family                   = "${{var.project_name}}-{sid}"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "{cpu}"
  memory                   = "{memory}"
  execution_role_arn       = aws_iam_role.{sid}_execution_role.arn

  container_definitions = jsonencode([{{
    name      = "{sid}"
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
        "awslogs-group"         = "/ecs/${{var.project_name}}-{sid}"
        "awslogs-region"        = var.region
        "awslogs-stream-prefix" = "ecs"
      }}
    }}
  }}])
}}

resource "aws_ecs_service" "{sid}" {{
  name            = "${{var.project_name}}-{sid}"
  cluster         = aws_ecs_cluster.{sid}_cluster.id
  task_definition = aws_ecs_task_definition.{sid}_task.arn
  desired_count   = {count}
  launch_type     = "FARGATE"

  network_configuration {{
    assign_public_ip = true
    subnets          = [for s in aws_subnet.public : s.id]
  }}
}}

resource "aws_iam_role" "{sid}_execution_role" {{
  name = "${{var.project_name}}-{sid}-exec-role"
  assume_role_policy = jsonencode({{
    Version = "2012-10-17"
    Statement = [{{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {{ Service = "ecs-tasks.amazonaws.com" }}
    }}]
  }})
}}

resource "aws_iam_role_policy_attachment" "{sid}_exec_policy" {{
  role       = aws_iam_role.{sid}_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}}

resource "aws_cloudwatch_log_group" "{sid}_logs" {{
  name              = "/ecs/${{var.project_name}}-{sid}"
  retention_in_days = 14
}}
'''
        return ToolResult(
            node=ToolNode(
                id=sid, type="aws_ecs", label=label,
                config=ToolNodeConfig(memory=memory, extra={"cpu": cpu, "container_port": port, "desired_count": count, "image": image}),
            ),
            terraform_code={"compute.tf": tf_code},
        )
