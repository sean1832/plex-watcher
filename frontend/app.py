"""
Plex Watcher Frontend Application

A Streamlit-based web interface for monitoring and managing the Plex Watcher service.
This application provides an intuitive UI for configuring paths to watch, starting/stopping
the monitoring service, and manually triggering scans.
"""

# TODO: remove path from list
# TODO: display api error responses messages in UI

import sys
import time
from pathlib import Path

import streamlit as st

# Add project root to Python path to enable 'from frontend...' imports
# This ensures the app works when run as: streamlit run frontend/app.py
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from frontend.api_client import get_api_client, run_async  # noqa: E402
from frontend.components import (  # noqa: E402
    render_api_response,
    render_backend_info,
    render_configuration_form,
    render_path_manager,
    render_scan_form,
    render_settings_sidebar,
    render_status_indicator,
    render_watch_controls,
)
from frontend.state import (  # noqa: E402
    get_backend_status,
    init_session_state,
    should_fetch_status,
    update_backend_status,
    update_config,
    update_settings,
)


def fetch_and_update_status(force: bool = False):
    """
    Fetch status from backend and update session state.

    Uses smart throttling to prevent excessive API calls.

    Args:
        force: If True, bypass throttling and fetch immediately
    """
    # Check if we should fetch (unless forced)
    if not force and not should_fetch_status():
        return  # Use cached data

    api_client = get_api_client()
    status = run_async(api_client.get_status(use_cache=not force))
    update_backend_status(status)


def handle_configuration_submit(config_data: dict):
    """
    Handle configuration form submission.

    Args:
        config_data: Configuration form data
    """
    # Config is saved to session state, no API call needed
    update_config(
        config_data["server_url"],
        config_data["token"],
        config_data["interval"],
    )
    st.success("✅ Configuration saved!")


def handle_watch_action(action: str):
    """
    Handle start/stop watching actions.

    Args:
        action: "start" or "stop"
    """
    api_client = get_api_client()

    if action == "start":
        # Get current config from session state
        server_url = st.session_state.plex_server_url
        token = st.session_state.plex_token
        interval = st.session_state.poll_interval

        # Validate configuration
        if not server_url or not token:
            st.error("Please configure Plex server URL and token first!")
            return

        with st.spinner("Starting watcher..."):
            response = run_async(api_client.start_watching(server_url, token, interval))
            render_api_response(response)

            # Refresh status after operation
            if response.is_success:
                time.sleep(0.5)  # Brief delay for backend to update
                fetch_and_update_status(force=True)

    elif action == "stop":
        with st.spinner("Stopping watcher..."):
            response = run_async(api_client.stop_watching())
            render_api_response(response)

            # Refresh status after operation
            if response.is_success:
                time.sleep(0.5)  # Brief delay for backend to update
                fetch_and_update_status(force=True)


def handle_path_action(path_action: dict):
    """
    Handle adding or removing a path.

    Args:
        path_action: Path action dictionary with 'action' and 'path' keys
    """
    if not path_action:
        return

    api_client = get_api_client()
    action = path_action.get("action")
    path = path_action.get("path")

    if not path:
        st.error("Path is required")
        return

    if action == "add":
        with st.spinner(f"Adding path: {path}"):
            response = run_async(api_client.add_path(path))
            render_api_response(response)

            # Refresh status after operation
            if response.is_success:
                time.sleep(0.5)  # Brief delay for backend to update
                fetch_and_update_status(force=True)

    elif action == "remove":
        with st.spinner(f"Removing path: {path}"):
            response = run_async(api_client.remove_path(path))
            render_api_response(response)

            # Refresh status after operation
            if response.is_success:
                time.sleep(0.5)  # Brief delay for backend to update
                fetch_and_update_status(force=True)


def handle_scan_request(scan_data: dict):
    """
    Handle manual scan request.

    Args:
        scan_data: Scan form data
    """
    if scan_data:
        api_client = get_api_client()
        paths = scan_data["paths"]

        with st.spinner(f"Scanning {len(paths)} path(s)..."):
            response = run_async(api_client.scan_paths(paths))
            render_api_response(response)


def render_watch_tab():
    """Render the Watch tab content."""

    # Configuration form (doesn't trigger rerun)
    config_data = render_configuration_form()
    if config_data["submitted"]:
        handle_configuration_submit(config_data)
        # No rerun needed - config saved to session state

    st.divider()
    # Path management (triggers rerun on action)
    status = get_backend_status()
    path_action = render_path_manager(status)
    if path_action:
        handle_path_action(path_action)
        st.rerun()  # Rerun to show updated paths

    # Watch controls (triggers rerun on action)
    st.subheader("Control")
    action = render_watch_controls(status.is_watching, status.is_connected)
    if action:
        handle_watch_action(action)
        st.rerun()  # Rerun to show updated status


def render_scan_tab():
    """Render the Scan tab content."""
    st.header("🔍 Manual Scan")

    scan_data = render_scan_form()
    if scan_data:
        handle_scan_request(scan_data)


def handle_connection_action(action: dict):
    """
    Handle connection test and reconnect actions.

    Args:
        action: Dictionary with action type and endpoint
    """
    if not action:
        return

    action_type = action.get("type")
    endpoint = action.get("endpoint", "").strip()

    if not endpoint:
        st.session_state.last_connection_test = {
            "success": False,
            "message": "❌ Please enter a valid endpoint URL",
        }
        return

    api_client = get_api_client()

    if action_type == "test_connection":
        # Test connection without saving
        with st.spinner(f"Testing connection to {endpoint}..."):
            success, message = run_async(api_client.test_connection(endpoint))
            st.session_state.last_connection_test = {
                "success": success,
                "message": message,
            }

    elif action_type == "reconnect":
        # Test connection and save if successful
        with st.spinner(f"Testing connection to {endpoint}..."):
            success, message = run_async(api_client.test_connection(endpoint))

            if success:
                # Update the API client endpoint
                api_client.update_endpoint(endpoint)

                # Update session state
                st.session_state.api_endpoint = endpoint

                # Update .env file
                from frontend.config import update_env_file

                if update_env_file("API_ENDPOINT", endpoint):
                    st.session_state.last_connection_test = {
                        "success": True,
                        "message": f"✅ Connected and saved to .env: {endpoint}",
                    }
                    # Force status refresh
                    fetch_and_update_status(force=True)
                else:
                    st.session_state.last_connection_test = {
                        "success": True,
                        "message": f"✅ Connected (but failed to save to .env): {endpoint}",
                    }
            else:
                st.session_state.last_connection_test = {
                    "success": False,
                    "message": message,
                }


def main():
    """Main application entry point."""
    # Page configuration
    st.set_page_config(
        page_title="Plex Watcher",
        page_icon="📺",
        layout="centered",
        initial_sidebar_state="auto",
    )

    # Initialize session state
    init_session_state()

    # Fetch status FIRST (before sidebar) so connection indicator is accurate
    # Use smart throttling - only fetches when needed
    fetch_and_update_status()

    # Render settings sidebar and get settings/actions
    settings = render_settings_sidebar()

    # Handle connection actions first (test/reconnect)
    if settings.get("action"):
        handle_connection_action(settings["action"])
        st.rerun()  # Rerun to show updated status

    # Update other settings
    update_settings(settings)

    # Main header
    st.title("📺 Plex Watcher")
    st.markdown("Monitor your Plex server for new content automatically.")

    # Get status for display (already fetched above)
    status = get_backend_status()

    # Status indicator
    render_status_indicator(status)

    # Backend info (collapsible)
    if status.is_connected:
        render_backend_info(status)

    # Tabs for different sections
    tab1, tab2 = st.tabs(["⚙️ Watch", "🔍 Scan"])

    with tab1:
        render_watch_tab()

    with tab2:
        render_scan_tab()

    # Auto-refresh logic
    if settings["auto_refresh_enabled"]:
        st.caption(f"🔄 Auto-refreshing every {settings['refresh_interval']} seconds...")
        time.sleep(settings["refresh_interval"])
        st.rerun()
    else:
        # Manual refresh button at bottom
        st.divider()
        if st.button("🔄 Refresh Status", width="stretch"):
            fetch_and_update_status(force=True)
            st.rerun()


if __name__ == "__main__":
    main()
