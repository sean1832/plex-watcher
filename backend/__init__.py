__version__ = "0.0.1"
import logging
import os
from pathlib import Path

# Load .env file if present (before any other imports that use environment variables)
# This must happen before logging configuration so LOG_LEVEL can be read
try:
    from dotenv import load_dotenv
    
    # Look for .env in backend directory
    backend_dir = Path(__file__).parent
    dotenv_path = backend_dir / ".env"
    
    if dotenv_path.exists():
        load_dotenv(dotenv_path=dotenv_path)
        print(f"[INFO] Loaded .env file from {dotenv_path}")
    else:
        # Try parent directory (project root)
        project_root = backend_dir.parent
        dotenv_path = project_root / ".env"
        if dotenv_path.exists():
            load_dotenv(dotenv_path=dotenv_path)
            print(f"[INFO] Loaded .env file from {dotenv_path}")
except ImportError:
    # python-dotenv not installed, skip .env file loading
    # System environment variables will still work (Docker compatibility)
    pass

# Configure logging based on environment variable
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)
