"""
Base Tool — abstract class, ToolResult, and OpenAI function-calling converter.

Every AWS service tool inherits from BaseTool and implements execute().
The ToolRegistry auto-discovers all subclasses and exposes them to the LLM.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ── Tool Result ─────────────────────────────────────────────────

class ToolNodeConfig(BaseModel):
    """Configuration snapshot returned by a tool execution."""
    runtime: Any = None
    memory: Any = None
    instance_type: Any = None
    engine: Any = None
    capacity: Any = None
    extra: dict[str, Any] = Field(default_factory=dict)


class ToolNode(BaseModel):
    """Architecture node produced by a tool call."""
    id: str
    type: str
    label: str
    config: ToolNodeConfig = Field(default_factory=ToolNodeConfig)


class ToolEdge(BaseModel):
    """Suggested edge produced by a tool call."""
    source: str = Field(..., alias="from")
    target: str = Field(..., alias="to")
    label: str = ""

    model_config = {"populate_by_name": True}


@dataclass
class ToolResult:
    """Result of executing a single tool call.

    Attributes:
        node: The architecture node created by the tool.
        terraform_code: Dict mapping filename → Terraform HCL snippet.
        edges: Optional list of edges the tool suggests.
        metadata: Any extra information (e.g. tags, notes).
    """
    node: ToolNode
    terraform_code: dict[str, str] = field(default_factory=dict)
    edges: list[dict[str, str]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "node": self.node.model_dump(by_alias=True),
            "terraform_code": self.terraform_code,
            "edges": self.edges,
            "metadata": self.metadata,
        }


# ── Base Tool ───────────────────────────────────────────────────

class BaseTool(ABC):
    """Abstract base class for all AWS service tools.

    Subclasses MUST set:
        name        – unique tool identifier, e.g. "create_ec2_instance"
        description – natural-language description for the LLM
        category    – grouping category, e.g. "compute"
        parameters  – JSON Schema dict describing input parameters
    """

    name: str = ""
    description: str = ""
    category: str = ""
    parameters: dict[str, Any] = {}

    @abstractmethod
    def execute(self, params: dict[str, Any]) -> ToolResult:
        """Execute the tool with the given parameters and return a ToolResult."""
        ...

    # ── OpenAI function-calling format ──────────────────────────

    def to_openai_tool(self) -> dict[str, Any]:
        """Convert this tool to the OpenAI function-calling schema."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name!r} category={self.category!r}>"
