from dataclasses import dataclass

import pandas as pd
import requests
import streamlit as st

API_ENDPOINT = "http://localhost:7799"


@dataclass
class BackendStatus:
    is_connected: bool
    is_watching: bool
    paths: list[str]
    server: str | None
    cooldown: int

    def to_dict(self):
        return {
            "is_connected": self.is_connected,
            "is_watching": self.is_watching,
            "paths": self.paths,
            "server": self.server,
            "cooldown": self.cooldown,
        }

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            is_connected=True,
            is_watching=data.get("is_watching", False),
            paths=data.get("paths", []),
            server=data.get("server"),
            cooldown=data.get("cooldown", 0),
        )


def start():
    response = requests.post(
        f"{API_ENDPOINT}/start",
        params={
            "server_url": st.session_state.plex_url,
            "token": st.session_state.plex_token,
            "interval": st.session_state.poll_interval,
        },
    )
    if response.status_code == 200:
        return response.json()
    return {"error": "Unable to start watching"}


def stop():
    response = requests.post(f"{API_ENDPOINT}/stop")
    if response.status_code == 200:
        return response.json()
    return {"error": "Unable to stop watching"}


def scan(paths):
    response = requests.post(f"{API_ENDPOINT}/scan", json={"paths": paths})
    if response.status_code == 200:
        return response.json()
    return {"error": "Unable to scan paths"}


def get_status() -> BackendStatus | dict[str, str]:
    # get status from backend API
    try:
        response = requests.get(f"{API_ENDPOINT}/status", timeout=2)
        if response.status_code == 200:
            return BackendStatus.from_dict(response.json())
        return {"error": "Unable to fetch status"}
    except requests.ConnectionError:
        return {"error": f"Unable to connect to backend API endpoint {API_ENDPOINT}/status"}
    except requests.Timeout:
        return {"error": "Request timed out"}
    except requests.RequestException as e:
        return {"error": str(e)}


def display_basic_params():
    st.text_input("Plex Server URL", placeholder="http://localhost:32400")
    st.text_input("Plex Token", type="password", placeholder="Your Plex Token")
    st.number_input("Polling Interval (seconds)", min_value=1, value=10)


def display_watchlist():
    st.text("Watchlist")
    df = pd.DataFrame(
        [
            {"Absolute Path": "/media/movies", "Watch": False},  # todo: mockup
            {"Absolute Path": "/media/tv", "Watch": False},  # todo: mockup
        ]
    )

    edited_df = st.data_editor(df, num_rows="dynamic", width="stretch")


def display_start_stop_buttons():
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Start Watching", width="stretch"):
            start()

    with col2:
        if st.button("Stop Watching", width="stretch"):
            stop()


def display_status(status: BackendStatus):
    if status.is_watching:
        st.text("🟢 Watching")
    else:
        st.text("🔴 Stopped")


def watch_tab(tab):
    with tab:
        display_basic_params()
        display_watchlist()
        display_start_stop_buttons()


def scan_tab(tab):
    with tab:
        st.text("Scan Specific Directories")
        paths = st.text_area("Enter paths to scan, one per line").splitlines()
        if st.button("Scan", width="stretch"):
            result = scan(paths)
            if result.get("status") == "success":
                st.success(result.get("message"))
            else:
                st.error(result.get("message"))
                if "details" in result:
                    for detail in result["details"]:
                        st.write(f"- {detail}")


if __name__ == "__main__":
    st.set_page_config(page_title="Plex Watcher", page_icon="📺", layout="centered")
    st.title("📺 Plex Watcher")
    st.markdown("Monitor your Plex server for new content automatically.")
    status = get_status()
    if isinstance(status, dict) and "error" in status:
        st.error(status["error"])
    elif isinstance(status, BackendStatus):
        if not status.is_connected:
            st.warning("Not connected to Plex Watcher backend")
        display_status(status)
    tab1, tab2 = st.tabs(["Watch", "Scan"])
    watch_tab(tab1)
    scan_tab(tab2)
    if st.button("Refresh", width="stretch"):
        st.rerun()
