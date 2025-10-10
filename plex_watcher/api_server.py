# GET /status, GET /events, GET /paths
# POST /add_path, POST /start, POST /stop, POST /scan
# TODO: implement authentication (API key or token)


from typing import List

from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse

from plex_watcher.core.plex_watcher_service import PlexWatcherService


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

    @app.post("/scan", description="Scan a specific directory")
    async def scan_directories(paths: List[str]):
        if not paths:
            raise HTTPException(status_code=400, detail="Path parameter is required.")
        errors = []
        for path in paths:
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
    uvicorn.run(app, host="0.0.0.0", port=8000)
