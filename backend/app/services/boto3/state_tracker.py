"""
State Tracker — stores and retrieves deployed resource records in the DB.

Replaces the old StateManager that read terraform.tfstate files.
Resource state is stored as JSON on the Deployment model's resource_state_json field.
"""

import json
import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class StateTracker:
    """
    Tracks deployed AWS resources in the database.

    Instead of terraform.tfstate files on disk, resource records are stored
    as JSON in the deployment's `resource_state_json` field.

    Usage:
        tracker = StateTracker(db)
        tracker.save_resources(deployment, resources)
        resources = tracker.get_resources(deployment)
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def save_resources(
        self,
        deployment,
        resources: list[dict[str, Any]],
    ) -> None:
        """Save deployed resource records to a deployment (synchronous — caller must commit)."""
        deployment.resource_state_json = json.dumps(resources, default=str)
        logger.info(
            "Saved %d resource records for deployment %d",
            len(resources),
            deployment.id,
        )

    def get_resources(self, deployment) -> list[dict[str, Any]]:
        """Get deployed resources from a deployment's stored state."""
        if not deployment or not deployment.resource_state_json:
            return []

        try:
            raw = deployment.resource_state_json
            resources = json.loads(raw) if isinstance(raw, str) else raw
            if not isinstance(resources, list):
                return []
            return resources
        except (json.JSONDecodeError, TypeError):
            return []

    def get_created_resources(self, deployment) -> list[dict[str, Any]]:
        """Get only successfully created resources from a deployment."""
        resources = self.get_resources(deployment)
        return [r for r in resources if r.get("status") == "created"]

    def clear_resources(self, deployment) -> None:
        """Clear resource state from a deployment (caller must commit)."""
        deployment.resource_state_json = None
        logger.info("Cleared resource state for deployment %d", deployment.id)

    def has_resources(self, deployment) -> bool:
        """Check if a deployment has any tracked resources."""
        return len(self.get_resources(deployment)) > 0
