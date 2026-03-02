"""Create Load Balancer tool — provisions via boto3."""
from typing import Any
from app.tools.base import BaseTool, ToolResult, ToolNode, ToolNodeConfig


class CreateLoadBalancerTool(BaseTool):
    name = "create_load_balancer"
    description = "Create an Elastic Load Balancer (ALB or NLB) with target groups and listeners for distributing traffic."
    category = "networking"
    parameters = {
        "type": "object",
        "properties": {
            "lb_id": {"type": "string"}, "label": {"type": "string"},
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
        label = params.get("label", lid)
        lb_type = params.get("type", "application")
        configs = [
            {
                "service": "elbv2",
                "action": "create_load_balancer",
                "params": {
                    "Name": f"__PROJECT__-{lid}",
                    "Subnets": "__DEFAULT_SUBNETS__",
                    "Scheme": "internal" if params.get("internal", False) else "internet-facing",
                    "Type": lb_type,
                    "Tags": [{"Key": "Name", "Value": f"__PROJECT__-{lid}"}],
                },
                "label": label,
                "resource_type": f"aws_{'alb' if lb_type == 'application' else 'nlb'}",
                "resource_id_path": "LoadBalancers[0].LoadBalancerArn",
                "delete_action": "delete_load_balancer",
                "delete_params_key": "LoadBalancerArn",
                "waiter": "load_balancer_available",
            },
            {
                "service": "elbv2",
                "action": "create_target_group",
                "params": {
                    "Name": f"__PROJECT__-{lid}-tg",
                    "Protocol": "HTTP",
                    "Port": params.get("target_port", 80),
                    "VpcId": "__DEFAULT_VPC__",
                    "HealthCheckPath": params.get("health_check_path", "/"),
                    "HealthyThresholdCount": 3,
                    "UnhealthyThresholdCount": 3,
                },
                "label": f"{label} — Target Group",
                "resource_type": "aws_lb_target_group",
                "resource_id_path": "TargetGroups[0].TargetGroupArn",
                "delete_action": "delete_target_group",
                "delete_params_key": "TargetGroupArn",
            },
            {
                "service": "elbv2",
                "action": "create_listener",
                "params": {
                    "LoadBalancerArn": "__RESOLVE_PREV_0__",
                    "Protocol": "HTTP",
                    "Port": params.get("listener_port", 80),
                    "DefaultActions": [{"Type": "forward", "TargetGroupArn": "__RESOLVE_PREV_1__"}],
                },
                "label": f"{label} — Listener",
                "resource_type": "aws_lb_listener",
                "resource_id_path": "Listeners[0].ListenerArn",
                "delete_action": "delete_listener",
                "delete_params_key": "ListenerArn",
            },
        ]
        return ToolResult(
            node=ToolNode(id=lid, type=f"aws_{'alb' if lb_type == 'application' else 'nlb'}", label=label,
                          config=ToolNodeConfig(extra={"lb_type": lb_type})),
            boto3_config={"elbv2": configs},
        )
