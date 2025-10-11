# GET /status,
# POST /add_path, POST /start, POST /stop, POST /scan
# TODO: implement authentication (API key or token)


from typing import List

from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from plex_watcher import logger
from plex_watcher.core.plex_watcher_service import PlexWatcherService


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

    @app.post("/start", description="Start watching")
    async def start_watching(server_url: str, token: str, interval: int):
        try:
            service.configure(server_url, token, interval)
            service.start()
            return {"status": "success", "message": "Started watching directories."}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    @app.post("/stop", description="Stop watching directories")
    async def stop_watching():
        try:
            service.stop()
            return {"status": "success", "message": "Stopped watching directories."}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    @app.post("/add_path", description="Add a path to watch")
    async def add_path(path: str):
        try:
            service.add_path(path)
            logger.info(f"Added path to watch: {path}")
            return {"status": "success", "message": f"Added path: {path}"}
        except FileNotFoundError as fnf:
            logger.error(f"File not found: {fnf}")
            return {"status": "error", "message": str(fnf)}
        except Exception as e:
            logger.error(f"Error adding path: {e}")
            return {"status": "error", "message": str(e)}

    @app.post("/remove_path", description="Remove a path from watch list")
    async def remove_path(path: str):
        try:
            service.remove_path(path)
            logger.info(f"Removed path from watch: {path}")
            return {"status": "success", "message": f"Removed path: {path}"}
        except ValueError as ve:
            logger.error(f"Path not found: {ve}")
            return {"status": "error", "message": str(ve)}
        except Exception as e:
            logger.error(f"Error removing path: {e}")
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


if __name__ == "__main__":
    import uvicorn

    service = PlexWatcherService()
    app = router(service)
    uvicorn.run(app, host="0.0.0.0", port=7799)
