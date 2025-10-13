"""
Environment configuration module for Plex Watcher Backend.

This module handles loading environment variables from .env files (if present)
and system environment variables (for Docker compatibility).

Priority order:
1. System environment variables (highest priority - for Docker)
2. .env file variables
3. Default values (lowest priority)
"""

import os
from pathlib import Path
from typing import Optional


def get_env_str(key: str, default: str = "") -> str:
    """Get string environment variable."""
    return os.getenv(key, default)


def get_env_int(key: str, default: int = 0) -> int:
    """Get integer environment variable."""
    value = os.getenv(key)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def get_env_bool(key: str, default: bool = False) -> bool:
    """Get boolean environment variable."""
    value = os.getenv(key)
    if value is None:
        return default
    return value.lower() in ("true", "1", "yes", "on")


def get_env_path(key: str, default: Optional[str] = None) -> Path:
    """Get Path environment variable."""
    value = os.getenv(key, default)
    if value is None:
        raise ValueError(f"Environment variable '{key}' is required but not set.")
    return Path(value).resolve()


class EnvironmentConfig:
    """
    Centralized environment configuration for Plex Watcher Backend.
    
    Loads from .env file (if present) and system environment variables.
    System environment variables always take precedence (for Docker compatibility).
    """

    def __init__(self):
        # API Server Configuration
        self.api_host: str = get_env_str("API_HOST", "0.0.0.0")
        self.api_port: int = get_env_int("API_PORT", 8000)
        
        # Logging Configuration
        self.log_level: str = get_env_str("LOG_LEVEL", "INFO")
        
        # Media and Config Paths
        self.media_root: str = get_env_str("MEDIA_ROOT", "/media")
        self.config_path: Path = Path(get_env_str("CONFIG_PATH", "config.json")).resolve()
        
        # CORS Configuration (comma-separated origins)
        cors_origins_str = get_env_str(
            "CORS_ORIGINS",
            "http://localhost:5173,http://localhost:4173,http://127.0.0.1:5173,http://127.0.0.1:4173"
        )
        self.cors_origins: list[str] = [
            origin.strip() for origin in cors_origins_str.split(",") if origin.strip()
        ]

    def __repr__(self) -> str:
        return (
            f"EnvironmentConfig("
            f"api_host={self.api_host!r}, "
            f"api_port={self.api_port}, "
            f"log_level={self.log_level!r}, "
            f"media_root={self.media_root!r}, "
            f"config_path={self.config_path}, "
            f"cors_origins={self.cors_origins!r})"
        )


# Global configuration instance
_config: Optional[EnvironmentConfig] = None


def get_config() -> EnvironmentConfig:
    """
    Get the global environment configuration instance.
    
    This ensures we only parse environment variables once.
    """
    global _config
    if _config is None:
        _config = EnvironmentConfig()
    return _config


def reload_config() -> EnvironmentConfig:
    """
    Force reload of environment configuration.
    
    Useful for testing or when environment variables change at runtime.
    """
    global _config
    _config = EnvironmentConfig()
    return _config
