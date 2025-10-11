"""Data models for the Plex Watcher frontend."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class BackendStatus:
    """Represents the current status of the Plex Watcher backend."""

    is_connected: bool
    is_watching: bool
    paths: list[str]
    server: Optional[str]
    cooldown: int

    @classmethod
    def from_api_response(cls, data: dict) -> "BackendStatus":
        """Create a BackendStatus from API response data."""
        return cls(
            is_connected=True,
            is_watching=data.get("is_watching", False),
            paths=data.get("paths", []),
            server=data.get("server"),
            cooldown=data.get("cooldown", 0),
        )

    @classmethod
    def disconnected(cls) -> "BackendStatus":
        """Create a disconnected status."""
        return cls(
            is_connected=False,
            is_watching=False,
            paths=[],
            server=None,
            cooldown=0,
        )


@dataclass
class WatchPath:
    """Represents a path to be watched."""

    path: str
    enabled: bool = True

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {"path": self.path, "enabled": self.enabled}

    @classmethod
    def from_dict(cls, data: dict) -> "WatchPath":
        """Create from dictionary."""
        return cls(path=data["path"], enabled=data.get("enabled", True))


@dataclass
class ApiResponse:
    """Represents a generic API response."""

    status: str
    message: str
    details: Optional[list[str]] = None

    @property
    def is_success(self) -> bool:
        """Check if the response indicates success."""
        return self.status == "success"

    @classmethod
    def from_dict(cls, data: dict) -> "ApiResponse":
        """Create from API response dictionary."""
        return cls(
            status=data.get("status", "error"),
            message=data.get("message", "Unknown error"),
            details=data.get("details"),
        )
