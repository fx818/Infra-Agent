"""
Connect Services Tool — utility tool for the LLM to define edges between services.
"""

from typing import Any

from app.tools.base import BaseTool, ToolResult, ToolNode, ToolNodeConfig


class ConnectServicesTool(BaseTool):
    """Allows the LLM to define a connection (edge) between two provisioned services."""

    name = "connect_services"
    description = (
        "Define a connection/dependency between two AWS services in the architecture. "
        "Use this after creating services to specify how they interact (e.g., "
        "an API Gateway routes to a Lambda, a Lambda writes to DynamoDB, etc.)."
    )
    category = "utility"
    parameters = {
        "type": "object",
        "properties": {
            "from_service_id": {
                "type": "string",
                "description": "The ID of the source service (the one initiating the connection).",
            },
            "to_service_id": {
                "type": "string",
                "description": "The ID of the target service (the one receiving the connection).",
            },
            "relationship": {
                "type": "string",
                "description": "Description of the relationship (e.g., 'invokes', 'reads from', 'writes to', 'routes to', 'publishes to').",
            },
        },
        "required": ["from_service_id", "to_service_id", "relationship"],
    }

    def execute(self, params: dict[str, Any]) -> ToolResult:
        """Return a ToolResult with only edge information, no node."""
        return ToolResult(
            node=ToolNode(id="_edge_", type="_edge_", label="connection"),
            edges=[{
                "from": params["from_service_id"],
                "to": params["to_service_id"],
                "label": params.get("relationship", "connects to"),
            }],
            metadata={"is_edge_only": True},
        )
