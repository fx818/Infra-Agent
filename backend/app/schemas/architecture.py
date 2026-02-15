"""
Pydantic schemas for Architecture entities.
"""

from typing import Any

from pydantic import BaseModel, Field


class IntentOutput(BaseModel):
    """Structured output from the Intent Agent."""
    app_type: str = Field(..., description="Type of application (e.g. web_api, data_pipeline, static_site)")
    scale: str = Field(..., description="Expected scale: small, medium, large, enterprise")
    latency_requirement: str = Field(default="moderate", description="low, moderate, high")
    storage_type: str = Field(default="object", description="object, relational, key_value, document")
    realtime: bool = Field(default=False, description="Whether realtime features are needed")
    constraints: list[str] = Field(default_factory=list, description="Any additional constraints")


class NodeConfig(BaseModel):
    """Configuration for an architecture node.

    All fields accept Any because the LLM may return strings, ints, or
    other JSON primitives unpredictably.  Data is stored as a JSON blob.
    """
    runtime: Any = None
    memory: Any = None
    instance_type: Any = None
    engine: Any = None
    capacity: Any = None
    extra: dict[str, Any] = Field(default_factory=dict)


class ArchitectureNode(BaseModel):
    """A single node in the architecture graph."""
    id: str = Field(..., description="Unique identifier for the node")
    type: str = Field(..., description="AWS resource type (e.g. aws_lambda, aws_apigatewayv2)")
    label: str = Field(default="", description="Human-readable label")
    config: NodeConfig = Field(default_factory=NodeConfig)


class ArchitectureEdge(BaseModel):
    """An edge connecting two nodes in the architecture graph."""
    source: str = Field(..., alias="from", description="Source node ID")
    target: str = Field(..., alias="to", description="Target node ID")
    label: str = Field(default="", description="Edge label/description")

    model_config = {"populate_by_name": True}


class ArchitectureGraph(BaseModel):
    """Complete architecture graph with nodes and edges."""
    nodes: list[ArchitectureNode] = Field(default_factory=list)
    edges: list[ArchitectureEdge] = Field(default_factory=list)


class TerraformFileMap(BaseModel):
    """Map of Terraform file names to their contents."""
    files: dict[str, str] = Field(
        default_factory=dict,
        description="Map of filename → file content, e.g. {'main.tf': '...'}"
    )


class ArchitectureResponse(BaseModel):
    """Full architecture response returned to the frontend."""
    id: int
    project_id: int
    version: int
    intent: IntentOutput | None = None
    graph: ArchitectureGraph
    terraform_files: TerraformFileMap | None = None
    cost: "CostEstimate | None" = None
    visual: "VisualGraph | None" = None

    model_config = {"from_attributes": True}


# ── Visual Graph (React Flow compatible) ─────────────────────

class VisualNode(BaseModel):
    """React Flow compatible node."""
    id: str
    type: str = "default"
    position: dict[str, float] = Field(default_factory=lambda: {"x": 0, "y": 0})
    data: dict[str, Any] = Field(default_factory=dict)
    style: dict[str, Any] = Field(default_factory=dict)


class VisualEdge(BaseModel):
    """React Flow compatible edge."""
    id: str
    source: str
    target: str
    label: str = ""
    animated: bool = False
    style: dict[str, Any] = Field(default_factory=dict)


class VisualGraph(BaseModel):
    """React Flow compatible graph."""
    nodes: list[VisualNode] = Field(default_factory=list)
    edges: list[VisualEdge] = Field(default_factory=list)


# ── Cost Estimation ──────────────────────────────────────────

class CostBreakdown(BaseModel):
    """Cost breakdown per service."""
    service: str
    estimated_monthly_cost: float
    details: str = ""


class CostEstimate(BaseModel):
    """Total cost estimation result."""
    estimated_monthly_cost: float
    currency: str = "USD"
    breakdown: list[CostBreakdown] = Field(default_factory=list)


# Rebuild forward references
ArchitectureResponse.model_rebuild()
