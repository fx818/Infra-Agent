"""
Terraform State Manager — reads and manages terraform.tfstate.
"""

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class StateManager:
    """
    Manages Terraform state files for project workspaces.

    Reads terraform.tfstate to extract deployed resource information,
    and provides hooks for future drift detection.
    """

    def get_state(self, workspace_dir: Path) -> dict[str, Any] | None:
        """
        Read and parse the terraform.tfstate file.

        Args:
            workspace_dir: Project workspace directory.

        Returns:
            Parsed state dict, or None if no state file exists.
        """
        state_file = workspace_dir / "terraform.tfstate"
        if not state_file.exists():
            logger.debug("No state file found at %s", state_file)
            return None

        try:
            content = state_file.read_text(encoding="utf-8")
            state = json.loads(content)
            logger.info("Read state file: %d resources", len(state.get("resources", [])))
            return state
        except (json.JSONDecodeError, IOError) as e:
            logger.error("Failed to read state file: %s", e)
            return None

    def get_resources(self, workspace_dir: Path) -> list[dict[str, Any]]:
        """
        Extract deployed resources from the state file.

        Returns:
            List of resource dicts with type, name, and attributes.
        """
        state = self.get_state(workspace_dir)
        if not state:
            return []

        resources = []
        for resource in state.get("resources", []):
            for instance in resource.get("instances", []):
                resources.append({
                    "type": resource.get("type", ""),
                    "name": resource.get("name", ""),
                    "provider": resource.get("provider", ""),
                    "attributes": instance.get("attributes", {}),
                })

        return resources

    def get_outputs(self, workspace_dir: Path) -> dict[str, Any]:
        """
        Extract outputs from the state file.

        Returns:
            Dict of output name → value.
        """
        state = self.get_state(workspace_dir)
        if not state:
            return {}

        outputs = {}
        for name, output in state.get("outputs", {}).items():
            outputs[name] = output.get("value")

        return outputs

    def has_state(self, workspace_dir: Path) -> bool:
        """Check if a terraform state file exists in the workspace."""
        return (workspace_dir / "terraform.tfstate").exists()

    def detect_drift(self, workspace_dir: Path) -> dict[str, Any]:
        """
        Placeholder for drift detection.

        Future implementation: compare state with actual AWS resources.

        Returns:
            Drift report dict.
        """
        logger.info("Drift detection not yet implemented")
        return {
            "drift_detected": False,
            "message": "Drift detection is a future feature.",
            "resources_checked": 0,
        }
