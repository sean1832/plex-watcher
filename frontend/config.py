"""Configuration management for Plex Watcher frontend."""

import os
from pathlib import Path

from dotenv import load_dotenv, set_key

# Load environment variables from .env file
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)


class Config:
    """Application configuration loaded from environment variables."""

    # Backend API Configuration
    API_ENDPOINT: str = os.getenv("API_ENDPOINT", "http://localhost:7799")

    # Plex Server Configuration
    PLEX_SERVER_URL: str = os.getenv("PLEX_SERVER_URL", "http://localhost:32400")
    PLEX_TOKEN: str = os.getenv("PLEX_TOKEN", "")

    # Polling Configuration
    DEFAULT_POLL_INTERVAL: int = int(os.getenv("DEFAULT_POLL_INTERVAL", "30"))

    # UI Configuration
    AUTO_REFRESH_INTERVAL: int = int(os.getenv("AUTO_REFRESH_INTERVAL", "5"))
    ENABLE_AUTO_REFRESH: bool = os.getenv("ENABLE_AUTO_REFRESH", "false").lower() == "true"


# Singleton config instance
config = Config()


def update_env_file(key: str, value: str) -> bool:
    """
    Update a key in the .env file.

    Args:
        key: Environment variable key
        value: New value to set

    Returns:
        True if successful, False otherwise
    """
    try:
        # Ensure .env file exists
        if not env_path.exists():
            env_path.touch()

        # Update the .env file
        set_key(env_path, key, value)

        # Reload environment variables
        load_dotenv(dotenv_path=env_path, override=True)

        # Update the config class attribute
        if hasattr(Config, key):
            setattr(Config, key, value)

        return True
    except Exception as e:
        print(f"Error updating .env file: {e}")
        return False
