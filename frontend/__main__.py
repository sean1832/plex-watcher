"""
Entry point for running the frontend via streamlit.
This allows: streamlit run -m frontend
"""

import sys
from pathlib import Path

# Get the path to app.py
app_path = Path(__file__).parent / "app.py"

# Tell the user how to run it properly
print(f"To run the Plex Watcher frontend, use:")
print(f"  streamlit run {app_path}")
print()
print("Or navigate to the frontend directory and run:")
print("  streamlit run app.py")
sys.exit(0)
