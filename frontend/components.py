"""UI components for the Plex Watcher frontend."""

import streamlit as st

from frontend.models import ApiResponse, BackendStatus


def render_status_indicator(status: BackendStatus):
    """
    Render the current status indicator.

    Args:
        status: Current backend status
    """
    if not status.is_connected:
        st.error("🔴 Backend Disconnected")
        st.caption("Unable to connect to the Plex Watcher backend API")
        return

    if status.is_watching:
        st.success("🟢 Watching Active")
        if status.server:
            st.caption(f"Connected to: {status.server}")
        if status.paths:
            st.caption(f"Monitoring {len(status.paths)} path(s)")
    else:
        st.warning("🟡 Watching Stopped")
        st.caption("Click 'Start Watching' to begin monitoring")


def render_configuration_form() -> dict:
    """
    Render the Plex configuration form.

    Returns:
        Dictionary with form values: {server_url, token, interval}
    """
    st.subheader("Plex Configuration")

    with st.form("config_form", clear_on_submit=False):
        server_url = st.text_input(
            "Plex Server URL",
            value=st.session_state.get("plex_server_url", ""),
            placeholder="http://localhost:32400",
            help="URL of your Plex Media Server",
        )

        token = st.text_input(
            "Plex Token",
            value=st.session_state.get("plex_token", ""),
            type="password",
            placeholder="Your Plex authentication token",
            help="Authentication token for your Plex server",
        )

        interval = st.number_input(
            "Scan Cooldown (seconds)",
            min_value=1,
            value=st.session_state.get("poll_interval", 30),
            help="Minimum time between automatic scans of the same path",
        )

        submitted = st.form_submit_button("Save Configuration", use_container_width=True)

        if submitted:
            return {
                "server_url": server_url,
                "token": token,
                "interval": interval,
                "submitted": True,
            }

    return {
        "server_url": st.session_state.get("plex_server_url", ""),
        "token": st.session_state.get("plex_token", ""),
        "interval": st.session_state.get("poll_interval", 30),
        "submitted": False,
    }


def render_path_manager(status: BackendStatus):
    """
    Render the path management interface with add and remove capabilities.

    Args:
        status: Current backend status with paths

    Returns:
        Dictionary with action ("add" or "remove") and path, or None
    """
    st.subheader("Watched Paths")

    # Display currently configured paths from backend with remove buttons
    if status.is_connected and status.paths:
        st.info(f"**Currently watching {len(status.paths)} path(s):**")

        # Display each path with a remove button
        for idx, path in enumerate(status.paths):
            col1, col2 = st.columns([5, 1])

            with col1:
                st.text(f"📁 {path}")

            with col2:
                # Use unique key for each button
                if st.button(
                    "🗑️", key=f"remove_path_{idx}", help="Remove this path", width="stretch"
                ):
                    return {"action": "remove", "path": path}

        st.caption("💡 Tip: Remove paths before stopping the watcher for a clean restart")
    else:
        st.caption("No paths configured yet. Add a path below to get started.")

    # Add new path form
    with st.form("add_path_form", clear_on_submit=True):
        st.caption("**Add a new path to watch**")
        new_path = st.text_input(
            "Directory Path",
            placeholder="Example: /media/movies or F:/Media/TV Shows",
            label_visibility="collapsed",
            help="Enter the absolute path to a directory you want to monitor",
        )

        col1, col2 = st.columns([3, 1])
        with col1:
            st.caption("The path must exist on the backend server")
        with col2:
            add_button = st.form_submit_button(
                "➕ Add Path", use_container_width=True, type="primary"
            )

        if add_button and new_path:
            return {"action": "add", "path": new_path.strip()}

    return None


def render_watch_controls(is_watching: bool, is_connected: bool):
    """
    Render start/stop watching controls.

    Args:
        is_watching: Whether currently watching
        is_connected: Whether backend is connected

    Returns:
        Action string: "start", "stop", or None
    """
    col1, col2 = st.columns(2)

    with col1:
        start_disabled = not is_connected or is_watching
        if st.button(
            "▶️ Start Watching",
            use_container_width=True,
            disabled=start_disabled,
            type="primary",
        ):
            return "start"

    with col2:
        stop_disabled = not is_connected or not is_watching
        if st.button(
            "⏹️ Stop Watching",
            use_container_width=True,
            disabled=stop_disabled,
        ):
            return "stop"

    return None


def render_scan_form():
    """
    Render the manual scan form.

    Returns:
        Dictionary with scan request or None
    """
    st.subheader("Manual Scan")
    st.caption("Trigger an immediate scan of specific directories")

    with st.form("scan_form", clear_on_submit=True):
        paths_input = st.text_area(
            "Directory Paths",
            placeholder="/media/movies\n/media/tv",
            help="Enter one path per line",
            height=100,
        )

        scan_button = st.form_submit_button("🔍 Scan Now", use_container_width=True)

        if scan_button and paths_input:
            paths = [p.strip() for p in paths_input.splitlines() if p.strip()]
            if paths:
                return {"paths": paths}

    return None


def render_api_response(response: ApiResponse):
    """
    Render an API response message.

    Args:
        response: ApiResponse object to display
    """
    if response.is_success:
        st.success(response.message)
    else:
        st.error(response.message)
        if response.details:
            with st.expander("Error Details"):
                for detail in response.details:
                    st.text(f"• {detail}")


def render_backend_info(status: BackendStatus):
    """
    Render detailed backend information.

    Args:
        status: Current backend status
    """
    with st.expander("Backend Details"):
        col1, col2 = st.columns(2)

        with col1:
            st.metric("Status", "Connected" if status.is_connected else "Disconnected")
            st.metric("Watching", "Yes" if status.is_watching else "No")

        with col2:
            st.metric("Monitored Paths", len(status.paths))
            st.metric("Cooldown", f"{status.cooldown}s" if status.cooldown else "N/A")

        if status.server:
            st.text(f"Server: {status.server}")


def render_settings_sidebar():
    """
    Render application settings in the sidebar.

    Returns:
        Dictionary with settings and actions
    """
    with st.sidebar:
        st.header("⚙️ Settings")

        # Connection Settings Section
        st.subheader("🔌 Backend Connection")

        # Get current status
        current_status = st.session_state.get("backend_status")
        is_connected = current_status and current_status.is_connected if current_status else False

        # Connection status indicator
        if is_connected:
            st.success("✅ Connected")
        else:
            st.error("❌ Disconnected")

        # API endpoint input
        from frontend.config import config

        # Initialize endpoint in session state if not exists
        if "api_endpoint" not in st.session_state:
            st.session_state.api_endpoint = config.API_ENDPOINT

        endpoint = st.text_input(
            "API Endpoint",
            value=st.session_state.api_endpoint,
            placeholder="http://localhost:7799",
            help="Backend API server URL",
        )

        # Test connection button
        col1, col2 = st.columns(2)

        with col1:
            test_btn = st.button(
                "🔍 Test",
                use_container_width=True,
                help="Test connection without saving",
            )

        with col2:
            reconnect_btn = st.button(
                "🔄 Reconnect",
                use_container_width=True,
                help="Test and save new endpoint",
                type="primary",
            )

        # Handle test/reconnect actions
        action = None
        if test_btn:
            action = {"type": "test_connection", "endpoint": endpoint}
        elif reconnect_btn:
            action = {"type": "reconnect", "endpoint": endpoint}

        # Display last connection test result
        if "last_connection_test" in st.session_state and st.session_state.last_connection_test:
            result = st.session_state.last_connection_test
            if result.get("success"):
                st.success(result.get("message", "Connection successful"))
            else:
                st.error(result.get("message", "Connection failed"))

        st.divider()

        # Auto-refresh Settings
        st.subheader("🔄 Auto-refresh")

        auto_refresh = st.checkbox(
            "Enable auto-refresh",
            value=st.session_state.get("auto_refresh_enabled", False),
            help="Automatically refresh the status at regular intervals",
        )

        if auto_refresh:
            refresh_interval = st.slider(
                "Refresh Interval (seconds)",
                min_value=2,
                max_value=30,
                value=st.session_state.get("refresh_interval", 5),
                help="How often to refresh the status",
            )
        else:
            refresh_interval = 5

        return {
            "auto_refresh_enabled": auto_refresh,
            "refresh_interval": refresh_interval,
            "api_endpoint": endpoint,
            "action": action,
        }
