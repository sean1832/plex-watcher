# GET /status
# POST /start, POST /stop, POST /scan
# TODO: implement authentication (API key or token)

import os
from pathlib import Path
from typing import List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from plexapi.server import PlexServer
from pydantic import BaseModel

from backend import logger
from backend.core.plex_watcher_service import PlexWatcherService


class StartRequest(BaseModel):
    """Request model for start endpoint."""

    server_url: str
    token: str
    paths: List[str]
    cooldown: int = 30


class ScanRequest(BaseModel):
    """Request model for scan endpoint."""

    server_url: str
    token: str
    paths: List[str]


def router(service: PlexWatcherService) -> FastAPI:
    app = FastAPI(title="Plex Watcher API")

    # Configure CORS for frontend communication
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",  # Vite dev server
            "http://localhost:4173",  # Vite preview server
            "http://127.0.0.1:5173",
            "http://127.0.0.1:4173",
        ],
        allow_credentials=True,
        allow_methods=["*"],  # Allow all methods (GET, POST, etc.)
        allow_headers=["*"],  # Allow all headers
    )

    @app.get("/")
    async def root():
        # redirect to /status
        return RedirectResponse(url="/status")

    @app.get("/status", description="Get current status of the Plex Watcher")
    async def get_status():
        return service.get_status()

    @app.get("/plex_test", description="Test connection to Plex server")
    async def test_plex_connection(server_url: str, token: str) -> bool:
        try:
            plex = PlexServer(server_url, token)
            plex.account()  # Test connection
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Plex server: {e}")
            return False

    @app.post("/start", description="Configure and start the watcher")
    async def start_watcher(request: StartRequest):
        """
        Start the Plex Watcher with complete configuration.

        This endpoint accepts the full configuration including server URL, token,
        paths, and cooldown.

        The watcher will be stopped if already running, then reconfigured and
        restarted with the new settings.
        """
        try:
            # Stop watcher if running
            if service.is_watching:
                service.stop()

            # Update configuration atomically
            service.update_configuration(
                server_url=request.server_url,
                token=request.token,
                paths=request.paths,
                cooldown=request.cooldown,
            )

            # Start watcher
            service.start()
            logger.info("Watcher configured and started successfully.")
            return {"message": "Watcher started successfully."}
        except FileNotFoundError as fnf:
            logger.error(f"Path not found: {fnf}")
            raise HTTPException(status_code=400, detail=f"Path not found: {str(fnf)}")
        except Exception as e:
            logger.error(f"Error starting watcher: {e}")
            raise HTTPException(status_code=500, detail=f"Error starting watcher: {str(e)}")

    @app.post("/restart", description="Restart the watcher with existing configuration")
    async def restart():
        try:
            if service.is_watching:
                service.stop()
            service.start()
            return {"message": "Watcher restarted successfully."}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error restarting watcher: {str(e)}")

    @app.post("/stop", description="Stop watching directories")
    async def stop_watching():
        try:
            service.stop()
            return {"message": "Stopped watching directories."}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error stopping watcher: {str(e)}")

    @app.post("/scan", description="Scan a specific directory")
    async def scan_directories(request: ScanRequest):
        if not request.paths:
            raise HTTPException(status_code=400, detail="Path parameter is required.")
        errors = PlexWatcherService.scan_paths(
            paths=request.paths, server_url=request.server_url, token=request.token
        )

        if len(errors) > 0:
            raise HTTPException(status_code=500, detail={"errors": errors})
        return {"message": "Scanned directories successfully."}

    return app


def main():
    import argparse

    import uvicorn

    parser = argparse.ArgumentParser(description="Plex Watcher API Server")
    parser.add_argument(
        "-H",
        "--host",
        type=str,
        default=os.getenv("API_HOST", "0.0.0.0"),
        help="Host to run the API server on",
    )
    parser.add_argument(
        "-P",
        "--port",
        type=int,
        default=int(os.getenv("API_PORT", "8000")),
        help="Port to run the API server on",
    )
    args = parser.parse_args()

    config_path = Path(os.getenv("CONFIG_PATH", "config.json")).resolve()
    if config_path.exists():
        service = PlexWatcherService.load_config(config_path)
        logger.info(f"Loaded configuration from {config_path}")
    else:
        service = PlexWatcherService()
        logger.info("No configuration file found, starting with default settings.")
    app = router(service)
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
