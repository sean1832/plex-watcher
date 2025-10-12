# GET /status
# POST /start, POST /stop, POST /scan
# TODO: implement authentication (API key or token)

import os
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
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

    paths: List[str]


def router(service: PlexWatcherService) -> FastAPI:
    app = FastAPI(title="Plex Watcher API")

    @app.get("/")
    async def root():
        # redirect to /status
        return RedirectResponse(url="/status")

    @app.get("/status", description="Get current status of the Plex Watcher")
    async def get_status():
        return service.get_status()

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
            return {
                "status": "success",
                "message": "Watcher started successfully.",
            }
        except FileNotFoundError as fnf:
            logger.error(f"Path not found: {fnf}")
            return {"status": "error", "message": str(fnf)}
        except Exception as e:
            logger.error(f"Error starting watcher: {e}")
            return {"status": "error", "message": str(e)}
    
    @app.post("/restart", description="Restart the watcher with existing configuration")
    async def restart():
        try:
            if service.is_watching:
                service.stop()
            service.start()
            return {"status": "success", "message": "Watcher restarted successfully."}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    @app.post("/stop", description="Stop watching directories")
    async def stop_watching():
        try:
            service.stop()
            return {"status": "success", "message": "Stopped watching directories."}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    @app.post("/scan", description="Scan a specific directory")
    async def scan_directories(request: ScanRequest):
        if not request.paths:
            raise HTTPException(status_code=400, detail="Path parameter is required.")
        errors = []
        for path in request.paths:
            try:
                service.scan_path(path)
            except FileNotFoundError as fnf:
                errors.append(str(fnf))
                continue
            except Exception as e:
                errors.append(f"Error scanning '{path}': {e}")
                continue

        if errors:
            return {
                "status": "error",
                "message": "Some errors occurred during scanning.",
                "details": errors,
            }
        return {"status": "success", "message": "Scanned directories successfully."}

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
