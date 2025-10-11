"""Launcher script for Plex Watcher Frontend."""

import subprocess
import sys
from pathlib import Path


def main():
    """Launch the Streamlit frontend application."""
    # Get the path to app.py
    app_path = Path(__file__).parent / "app.py"

    # Run streamlit with the app
    cmd = [sys.executable, "-m", "streamlit", "run", str(app_path)] + sys.argv[1:]

    try:
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        print("\nShutting down Plex Watcher Frontend...")
        sys.exit(0)
    except subprocess.CalledProcessError as e:
        sys.exit(e.returncode)


if __name__ == "__main__":
    main()
