"""
Tool Registry — auto-discovers and registers all AWS service tools.

Usage:
    registry = ToolRegistry()
    tools = registry.get_openai_tools()       # for LLM
    tool  = registry.get_tool_by_name("create_ec2_instance")
    result = tool.execute(params)
"""

import importlib
import inspect
import logging
import pkgutil
from typing import Any

from app.tools.base import BaseTool

logger = logging.getLogger(__name__)

# Sub-packages that contain tool definitions
_TOOL_PACKAGES = [
    "app.tools.compute",
    "app.tools.networking",
    "app.tools.storage",
    "app.tools.databases",
    "app.tools.messaging",
    "app.tools.security",
    "app.tools.monitoring",
    "app.tools.devops",
    "app.tools.analytics",
    "app.tools.application",
]


class ToolRegistry:
    """Central registry that discovers and manages all AWS service tools."""

    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}
        self._discover()

    # ── Discovery ───────────────────────────────────────────────

    def _discover(self) -> None:
        """Auto-discover tool classes from all sub-packages."""
        for package_name in _TOOL_PACKAGES:
            try:
                package = importlib.import_module(package_name)
            except ModuleNotFoundError:
                logger.warning("Tool package not found: %s", package_name)
                continue

            # Walk modules inside the package
            package_path = getattr(package, "__path__", None)
            if not package_path:
                continue

            for _importer, module_name, _is_pkg in pkgutil.iter_modules(package_path):
                full_name = f"{package_name}.{module_name}"
                try:
                    module = importlib.import_module(full_name)
                except Exception as e:
                    logger.warning("Failed to import tool module %s: %s", full_name, e)
                    continue

                # Find all BaseTool subclasses in this module
                for _attr_name, obj in inspect.getmembers(module, inspect.isclass):
                    if issubclass(obj, BaseTool) and obj is not BaseTool and obj.name:
                        self._register(obj())

        # Also import standalone tools (connect_services, etc.)
        try:
            from app.tools.connect_services import ConnectServicesTool
            self._register(ConnectServicesTool())
        except Exception as e:
            logger.warning("Failed to import ConnectServicesTool: %s", e)

        logger.info("ToolRegistry: loaded %d tools", len(self._tools))

    def _register(self, tool: BaseTool) -> None:
        if tool.name in self._tools:
            logger.warning("Duplicate tool name: %s — skipping", tool.name)
            return
        self._tools[tool.name] = tool

    # ── Public API ──────────────────────────────────────────────

    def get_all_tools(self) -> list[BaseTool]:
        """Return all registered tool instances."""
        return list(self._tools.values())

    def get_tool_by_name(self, name: str) -> BaseTool | None:
        """Look up a tool by its unique name."""
        return self._tools.get(name)

    def get_tools_by_category(self, category: str) -> list[BaseTool]:
        """Return all tools in a given category."""
        return [t for t in self._tools.values() if t.category == category]

    def get_openai_tools(self) -> list[dict[str, Any]]:
        """Return all tools formatted for the OpenAI tools parameter."""
        return [t.to_openai_tool() for t in self._tools.values()]

    def get_relevant_openai_tools(
        self,
        user_prompt: str,
        max_tools: int = 20,
    ) -> list[dict[str, Any]]:
        """Return a filtered set of tools most relevant to the user prompt.

        Uses keyword matching to identify relevant categories, then returns
        up to `max_tools` tools. Always includes connect_services and
        core tools (compute, networking, storage).
        """
        prompt_lower = user_prompt.lower()

        # Map keywords → categories
        _KEYWORD_TO_CATEGORIES: dict[str, list[str]] = {
            "lambda": ["compute", "monitoring"],
            "serverless": ["compute", "messaging", "databases"],
            "api": ["compute", "networking", "application"],
            "api gateway": ["application", "compute"],
            "ec2": ["compute", "networking"],
            "instance": ["compute", "networking"],
            "container": ["compute", "networking"],
            "ecs": ["compute", "networking"],
            "fargate": ["compute", "networking"],
            "docker": ["compute", "networking"],
            "s3": ["storage"],
            "storage": ["storage"],
            "bucket": ["storage"],
            "database": ["databases"],
            "rds": ["databases"],
            "dynamo": ["databases"],
            "postgre": ["databases"],
            "mysql": ["databases"],
            "redis": ["databases"],
            "cache": ["databases"],
            "elastic": ["databases", "analytics"],
            "sqs": ["messaging"],
            "sns": ["messaging"],
            "queue": ["messaging"],
            "notification": ["messaging"],
            "event": ["messaging"],
            "kinesis": ["messaging", "analytics"],
            "vpc": ["networking"],
            "network": ["networking"],
            "load balancer": ["networking"],
            "alb": ["networking"],
            "cloudfront": ["networking"],
            "cdn": ["networking"],
            "route53": ["networking"],
            "dns": ["networking"],
            "domain": ["networking"],
            "iam": ["security"],
            "auth": ["security"],
            "cognito": ["security"],
            "security": ["security"],
            "kms": ["security"],
            "encrypt": ["security"],
            "waf": ["security"],
            "monitor": ["monitoring"],
            "cloudwatch": ["monitoring"],
            "alarm": ["monitoring"],
            "log": ["monitoring"],
            "cicd": ["devops"],
            "pipeline": ["devops", "analytics"],
            "codepipeline": ["devops"],
            "codebuild": ["devops"],
            "deploy": ["devops"],
            "glue": ["analytics"],
            "athena": ["analytics"],
            "redshift": ["analytics"],
            "analytics": ["analytics"],
            "data": ["analytics", "storage"],
            "web": ["compute", "networking", "storage"],
            "website": ["compute", "networking", "storage"],
            "static": ["storage", "networking"],
            "microservice": ["compute", "networking", "messaging"],
        }

        # Always include these categories (core infra)
        matched_categories: set[str] = {"compute", "networking"}

        for keyword, categories in _KEYWORD_TO_CATEGORIES.items():
            if keyword in prompt_lower:
                matched_categories.update(categories)

        # Collect tools from matched categories
        selected: list[BaseTool] = []
        for tool in self._tools.values():
            if tool.category in matched_categories or tool.name == "connect_services":
                selected.append(tool)

        # Cap at max_tools — prioritize: connect_services first, then alphabetical
        selected.sort(key=lambda t: (0 if t.name == "connect_services" else 1, t.name))
        selected = selected[:max_tools]

        logger.info(
            "ToolRegistry: selected %d/%d tools for prompt (categories: %s)",
            len(selected), len(self._tools), ", ".join(sorted(matched_categories)),
        )

        return [t.to_openai_tool() for t in selected]

    def get_categories(self) -> list[str]:
        """Return sorted list of unique categories."""
        return sorted({t.category for t in self._tools.values()})

    def __len__(self) -> int:
        return len(self._tools)

    def __repr__(self) -> str:
        return f"<ToolRegistry tools={len(self._tools)}>"
