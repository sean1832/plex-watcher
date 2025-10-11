"""State management for the Streamlit application."""

import time

import streamlit as st

from frontend.config import config
from frontend.models import BackendStatus


def init_session_state():
    """Initialize session state variables with default values."""
    # Configuration state
    if "plex_server_url" not in st.session_state:
        st.session_state.plex_server_url = config.PLEX_SERVER_URL

    if "plex_token" not in st.session_state:
        st.session_state.plex_token = config.PLEX_TOKEN

    if "poll_interval" not in st.session_state:
        st.session_state.poll_interval = config.DEFAULT_POLL_INTERVAL

    # UI state
    if "auto_refresh_enabled" not in st.session_state:
        st.session_state.auto_refresh_enabled = config.ENABLE_AUTO_REFRESH

    if "refresh_interval" not in st.session_state:
        st.session_state.refresh_interval = config.AUTO_REFRESH_INTERVAL

    # Backend status cache
    if "backend_status" not in st.session_state:
        st.session_state.backend_status = BackendStatus.disconnected()

    # Last operation result
    if "last_operation" not in st.session_state:
        st.session_state.last_operation = None

    # Fetch control - prevents unnecessary fetches
    if "last_fetch_time" not in st.session_state:
        st.session_state.last_fetch_time = 0.0

    if "fetch_cooldown" not in st.session_state:
        st.session_state.fetch_cooldown = 2.0  # Minimum 2 seconds between fetches

    if "needs_refresh" not in st.session_state:
        st.session_state.needs_refresh = True  # Initial fetch needed


def update_config(server_url: str, token: str, interval: int):
    """
    Update configuration in session state.

    Args:
        server_url: Plex server URL
        token: Plex authentication token
        interval: Polling interval in seconds
    """
    st.session_state.plex_server_url = server_url
    st.session_state.plex_token = token
    st.session_state.poll_interval = interval


def update_backend_status(status: BackendStatus):
    """
    Update backend status in session state.

    Args:
        status: New backend status
    """
    st.session_state.backend_status = status
    st.session_state.last_fetch_time = time.time()
    st.session_state.needs_refresh = False


def get_backend_status() -> BackendStatus:
    """
    Get current backend status from session state.

    Returns:
        Current BackendStatus
    """
    return st.session_state.backend_status


def should_fetch_status() -> bool:
    """
    Determine if we should fetch status from backend.

    Uses smart throttling to prevent excessive API calls while ensuring
    fresh data when needed.

    Returns:
        True if status should be fetched, False to use cached data
    """
    # Always fetch if explicitly requested
    if st.session_state.needs_refresh:
        return True

    # Check cooldown - don't fetch if we just fetched recently
    time_since_last_fetch = time.time() - st.session_state.last_fetch_time
    if time_since_last_fetch < st.session_state.fetch_cooldown:
        return False

    # If auto-refresh is enabled, fetch based on refresh interval
    if st.session_state.auto_refresh_enabled:
        return time_since_last_fetch >= st.session_state.refresh_interval

    # Otherwise, use cached data (user must manually refresh)
    return False


def mark_needs_refresh():
    """Mark that status needs to be refreshed on next render."""
    st.session_state.needs_refresh = True


def set_last_operation(operation: dict):
    """
    Store the last operation result.

    Args:
        operation: Dictionary with operation details
    """
    st.session_state.last_operation = operation


def get_last_operation() -> dict:
    """
    Get the last operation result.

    Returns:
        Last operation dictionary or None
    """
    return st.session_state.last_operation


def clear_last_operation():
    """Clear the last operation from state."""
    st.session_state.last_operation = None


def update_settings(settings: dict):
    """
    Update UI settings in session state.

    Args:
        settings: Dictionary with settings to update
    """
    for key, value in settings.items():
        st.session_state[key] = value
