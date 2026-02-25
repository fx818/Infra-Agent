"""Create Load Balancer tool."""
from typing import Any
from app.tools.base import BaseTool, ToolResult, ToolNode, ToolNodeConfig


class CreateLoadBalancerTool(BaseTool):
    name = "create_load_balancer"
    description = "Create an Elastic Load Balancer (ALB or NLB) with target groups and listeners for distributing traffic."
    category = "networking"
    parameters = {
        "type": "object",
        "properties": {
            "lb_id": {"type": "string"},
            "label": {"type": "string"},
            "type": {"type": "string", "description": "'application' (ALB) or 'network' (NLB).", "default": "application"},
            "internal": {"type": "boolean", "default": False},
            "listener_port": {"type": "integer", "default": 80},
            "target_port": {"type": "integer", "default": 80},
            "health_check_path": {"type": "string", "default": "/"},
        },
        "required": ["lb_id", "label"],
    }

    def execute(self, params: dict[str, Any]) -> ToolResult:
        lid = params["lb_id"]
        lb_type = params.get("type", "application")
        tf_code = f'''resource "aws_lb" "{lid}" {{
  name               = "${{var.project_name}}-{lid}"
  internal           = {str(params.get('internal', False)).lower()}
  load_balancer_type = "{lb_type}"
  subnets            = [for s in aws_subnet.public : s.id]
  tags = {{ Name = "${{var.project_name}}-{lid}" }}
}}

resource "aws_lb_target_group" "{lid}_tg" {{
  name     = "${{var.project_name}}-{lid}-tg"
  port     = {params.get('target_port', 80)}
  protocol = "HTTP"
  vpc_id   = aws_vpc.main_vpc.id
  health_check {{
    path                = "{params.get('health_check_path', '/')}"
    healthy_threshold   = 3
    unhealthy_threshold = 3
  }}
}}

resource "aws_lb_listener" "{lid}_listener" {{
  load_balancer_arn = aws_lb.{lid}.arn
  port              = {params.get('listener_port', 80)}
  protocol          = "HTTP"
  default_action {{
    type             = "forward"
    target_group_arn = aws_lb_target_group.{lid}_tg.arn
  }}
}}
'''
        return ToolResult(
            node=ToolNode(id=lid, type=f"aws_{'alb' if lb_type == 'application' else 'nlb'}", label=params.get("label", lid),
                          config=ToolNodeConfig(extra={"lb_type": lb_type})),
            terraform_code={"networking.tf": tf_code},
        )
