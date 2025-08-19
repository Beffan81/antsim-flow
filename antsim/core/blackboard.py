# FILE: antsim/core/blackboard.py
"""Blackboard system for unified agent state management."""

import json
import logging
from typing import Dict, Any, Optional, List
from copy import deepcopy

logger = logging.getLogger(__name__)


class Blackboard:
    """Unified state space for agents with diff tracking and JSON serialization."""

    def __init__(self, agent_id: int):
        """Initialize blackboard for an agent.

        Args:
            agent_id: Unique identifier for the agent
        """
        self.agent_id = agent_id
        self._data: Dict[str, Any] = {}
        self._previous_data: Dict[str, Any] = {}
        self._changes: Dict[str, Any] = {}
        self._subscribers: Dict[str, List[callable]] = {}

        # Initialize with basic agent info
        self._data["agent_id"] = agent_id
        self._data["cycle"] = 0

        logger.info("Blackboard initialized for agent %s", agent_id)

    def get(self, key: str, default: Any = None) -> Any:
        """Get value from blackboard.

        Args:
            key: Key to retrieve
            default: Default value if key not found

        Returns:
            Value associated with key or default
        """
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set value in blackboard.

        Args:
            key: Key to set
            value: Value to store (must be JSON serializable)

        Raises:
            ValueError: If value is not JSON serializable
        """
        # Validate JSON serializable
        try:
            json.dumps(value)
        except (TypeError, ValueError) as e:
            raise ValueError(f"Value for key '{key}' must be JSON serializable: {e}")

        # Track change if value differs
        if key not in self._data or self._data[key] != value:
            old = self._data.get(key)
            self._changes[key] = {"old": old, "new": value}
            self._data[key] = value

            # Notify subscribers
            self._notify_subscribers(key, value)

    def update(self, data: Dict[str, Any]) -> None:
        """Update multiple values at once.

        Args:
            data: Dictionary of key-value pairs to update
        """
        for key, value in data.items():
            self.set(key, value)

    def diff(self) -> Dict[str, Any]:
        """Get all changes since last commit.

        Returns:
            Dictionary of changes with old/new values
        """
        return deepcopy(self._changes)

    def commit(self) -> Dict[str, Any]:
        """Commit current state and return changes.

        Returns:
            Dictionary of committed changes
        """
        changes = self.diff()
        self._previous_data = deepcopy(self._data)
        self._changes.clear()

        if changes:
            logger.debug(
                "Blackboard commit for agent %s: %d changes", self.agent_id, len(changes)
            )

        return changes

    def rollback(self) -> None:
        """Rollback to previous committed state."""
        self._data = deepcopy(self._previous_data)
        self._changes.clear()
        logger.info("Blackboard rollback for agent %s", self.agent_id)

    def subscribe(self, key: str, callback: callable) -> None:
        """Subscribe to changes for a specific key.

        Args:
            key: Key to watch for changes
            callback: Function to call when key changes
        """
        if key not in self._subscribers:
            self._subscribers[key] = []
        self._subscribers[key].append(callback)

    def _notify_subscribers(self, key: str, value: Any) -> None:
        """Notify subscribers of key changes."""
        if key in self._subscribers:
            for callback in self._subscribers[key]:
                try:
                    callback(self.agent_id, key, value)
                except Exception as e:
                    logger.error("Subscriber callback error: %s", e, exc_info=True)

    def to_dict(self) -> Dict[str, Any]:
        """Export entire blackboard state as dictionary.

        Returns:
            Complete state dictionary
        """
        return deepcopy(self._data)

    def from_dict(self, data: Dict[str, Any]) -> None:
        """Import state from dictionary.

        Args:
            data: State dictionary to import
        """
        self._data = deepcopy(data)
        self._changes.clear()
        logger.info("Blackboard state imported for agent %s", self.agent_id)

    def clear(self) -> None:
        """Clear all data except agent_id."""
        agent_id = self._data.get("agent_id")
        self._data.clear()
        if agent_id is not None:
            self._data["agent_id"] = agent_id
        self._changes.clear()

    def keys(self) -> List[str]:
        """Get all keys in blackboard."""
        return list(self._data.keys())

    def has(self, key: str) -> bool:
        """Check if key exists in blackboard."""
        return key in self._data

    def remove(self, key: str) -> Any:
        """Remove key from blackboard.

        Args:
            key: Key to remove

        Returns:
            Removed value or None
        """
        if key in self._data:
            value = self._data.pop(key)
            self._changes[key] = {"old": value, "new": None, "removed": True}
            return value
        return None

    def __repr__(self) -> str:
        """String representation."""
        return f"Blackboard(agent_id={self.agent_id}, keys={len(self._data)}, changes={len(self._changes)})"
