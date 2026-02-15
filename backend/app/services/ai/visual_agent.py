"""
Visual Mapping Agent — converts architecture graphs to React Flow layouts.
"""

import json
import logging

from app.schemas.architecture import ArchitectureGraph, VisualGraph
from app.services.ai.base import BaseLLMProvider, get_llm_provider
from app.utils.prompt_loader import load_prompt

logger = logging.getLogger(__name__)

# ── Service tier mapping for layout ─────────────────────────────
_SERVICE_TIERS: dict[str, int] = {
    "aws_route53": 0,
    "aws_cloudfront": 0,
    "aws_apigatewayv2": 1,
    "aws_lambda": 2,
    "aws_ecs": 2,
    "aws_sqs": 2,
    "aws_sns": 2,
    "aws_dynamodb": 3,
    "aws_rds": 3,
    "aws_s3": 3,
    "aws_elasticache": 3,
    "aws_vpc": 4,
    "aws_security_group": 4,
    "aws_iam_role": 4,
}

# ── Service visual styles ───────────────────────────────────────
_SERVICE_STYLES: dict[str, dict[str, str]] = {
    "aws_apigatewayv2": {"background": "#FF9900", "border": "2px solid #CC7A00", "icon": "🌐"},
    "aws_lambda": {"background": "#FF9900", "border": "2px solid #CC7A00", "icon": "λ"},
    "aws_dynamodb": {"background": "#3B48CC", "border": "2px solid #2D3799", "icon": "📊"},
    "aws_rds": {"background": "#3B48CC", "border": "2px solid #2D3799", "icon": "🗄️"},
    "aws_s3": {"background": "#3F8624", "border": "2px solid #2D6B1A", "icon": "📦"},
    "aws_sqs": {"background": "#FF4F8B", "border": "2px solid #CC3F6F", "icon": "📨"},
    "aws_sns": {"background": "#FF4F8B", "border": "2px solid #CC3F6F", "icon": "📢"},
    "aws_ecs": {"background": "#FF9900", "border": "2px solid #CC7A00", "icon": "🐳"},
    "aws_elasticache": {"background": "#3B48CC", "border": "2px solid #2D3799", "icon": "⚡"},
    "aws_cloudfront": {"background": "#8C4FFF", "border": "2px solid #6B3DCC", "icon": "🌍"},
    "aws_vpc": {"background": "#248814", "border": "2px solid #1A6610", "icon": "🔒"},
    "aws_iam_role": {"background": "#DD344C", "border": "2px solid #B02A3D", "icon": "🔑"},
    "aws_security_group": {"background": "#DD344C", "border": "2px solid #B02A3D", "icon": "🛡️"},
    "aws_route53": {"background": "#8C4FFF", "border": "2px solid #6B3DCC", "icon": "🌎"},
}


class VisualAgent:
    """
    Converts an architecture graph into a React Flow-compatible
    visual layout with positioned nodes and styled edges.

    Uses a deterministic layout algorithm first.
    Optionally uses the LLM for more sophisticated layouts.
    """

    def __init__(self, llm: BaseLLMProvider | None = None) -> None:
        self.llm = llm or get_llm_provider()
        self.system_prompt = load_prompt("visual_agent_prompt.md")

    async def run(
        self,
        graph: ArchitectureGraph,
        use_llm: bool = False,
    ) -> VisualGraph:
        """
        Convert architecture graph to a visual layout.

        Args:
            graph: The architecture graph to visualize.
            use_llm: If True, use LLM for positioning. Else deterministic.

        Returns:
            VisualGraph compatible with React Flow.
        """
        if use_llm:
            return await self._layout_with_llm(graph)
        return self._layout_deterministic(graph)

    def _layout_deterministic(self, graph: ArchitectureGraph) -> VisualGraph:
        """Generate a deterministic tiered layout."""
        logger.info("VisualAgent: deterministic layout for %d nodes", len(graph.nodes))

        # Group nodes by tier
        tiers: dict[int, list] = {}
        for node in graph.nodes:
            tier = _SERVICE_TIERS.get(node.type, 2)
            tiers.setdefault(tier, []).append(node)

        visual_nodes = []
        node_width = 180
        h_gap = 220
        v_gap = 150

        for tier_idx in sorted(tiers.keys()):
            tier_nodes = tiers[tier_idx]
            # Center this tier's nodes
            total_width = len(tier_nodes) * h_gap
            start_x = (800 - total_width) // 2 + 100

            for i, node in enumerate(tier_nodes):
                style_info = _SERVICE_STYLES.get(node.type, {
                    "background": "#666",
                    "border": "2px solid #444",
                    "icon": "☁️",
                })

                visual_nodes.append({
                    "id": node.id,
                    "type": "default",
                    "position": {"x": start_x + i * h_gap, "y": 80 + tier_idx * v_gap},
                    "data": {
                        "label": f"{style_info.get('icon', '☁️')} {node.label or node.id}",
                        "service_type": node.type,
                        "config_summary": json.dumps(node.config.model_dump(), default=str)[:100],
                    },
                    "style": {
                        "background": style_info.get("background", "#666"),
                        "border": style_info.get("border", "2px solid #444"),
                        "borderRadius": "8px",
                        "padding": "10px",
                        "color": "white",
                        "fontWeight": "bold",
                        "width": f"{node_width}px",
                    },
                })

        visual_edges = []
        for edge in graph.edges:
            visual_edges.append({
                "id": f"edge_{edge.source}_{edge.target}",
                "source": edge.source,
                "target": edge.target,
                "label": edge.label,
                "animated": True,
                "style": {"stroke": "#888", "strokeWidth": 2},
            })

        return VisualGraph(**{"nodes": visual_nodes, "edges": visual_edges})

    async def _layout_with_llm(self, graph: ArchitectureGraph) -> VisualGraph:
        """Use the LLM for more sophisticated layout positioning."""
        logger.info("VisualAgent: LLM layout for %d nodes", len(graph.nodes))

        graph_dict = graph.model_dump(by_alias=True)
        user_prompt = (
            f"## Architecture Graph\n\n"
            f"```json\n{json.dumps(graph_dict, indent=2)}\n```\n\n"
            f"Create a visually appealing React Flow layout for this architecture."
        )

        result = await self.llm.generate(
            system_prompt=self.system_prompt,
            user_prompt=user_prompt,
            temperature=0.3,
        )

        return VisualGraph(**result)
