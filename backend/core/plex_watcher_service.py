import os
from pathlib import Path
from threading import Lock
from typing import Optional

import watchdog.observers
from plexapi.server import PlexServer

from backend import logger
from backend.core.plex_path import PlexPath
from backend.core.plex_scanner import PlexScanner
from backend.core.plex_watcher_handler import PlexWatcherHandler


class PlexWatcherService:
    def __init__(self) -> None:
        self.observer = watchdog.observers.Observer()
        self.paths: set[Path] = set()
        self.server: Optional[PlexServer] = None
        self.handler: Optional[PlexWatcherHandler] = None
        self.scanner: Optional[PlexScanner] = None
        self.cooldown: int = 30  # default interval in seconds
        self.is_watching: bool = False
        self._lock = Lock()  # Thread safety for state changes

        self._CONFIG_PATH = Path(os.getenv("CONFIG_PATH", "config.json")).resolve()
        self._MEDIA_ROOT = Path(os.getenv("MEDIA_ROOT", "/media")).resolve()

    def write_config(self) -> None:
        """Write the current configuration to a file."""
        import json

        config = {
            "paths": [str(p) for p in self.paths],
            "server": self.server._baseurl if self.server else None,
            "token": self.server._token if self.server else None,
            "cooldown": self.cooldown,
        }
        # Ensure the config directory exists
        self._CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with self._CONFIG_PATH.open("w") as f:
            json.dump(config, f, indent=4)

        logger.info(f"Configuration written to {self._CONFIG_PATH}")

    @classmethod
    def load_config(cls, config_path: Path) -> "PlexWatcherService":
        """Load configuration from a file and return a configured PlexWatcherService."""
        import json

        with config_path.open("r") as f:
            config = json.load(f)

        service = cls()
        if "server" in config and "token" in config and config["server"] and config["token"]:
            service.configure(config["server"], config["token"], config.get("cooldown", 30))
        for path in config.get("paths", []):
            service.add_path(path)

        logger.info("Plex Watcher Service loaded from config.")
        return service

    def get_status(self) -> dict:
        return {
            "is_watching": self.is_watching,
            "paths": [str(p) for p in self.paths],
            "server": self.server._baseurl if self.server else None,
            "cooldown": self.cooldown,
        }

    def configure(self, server_url: str, token: str, interval: int) -> None:
        self.server = PlexServer(baseurl=server_url, token=token)
        self.cooldown = interval
        self.scanner = PlexScanner(plex=self.server)
        self.handler = PlexWatcherHandler(self.scanner, self.observer, cooldown=self.cooldown)
        self.is_watching = False
        logger.info(
            f"Plex Watcher Service configured. Plex Server: {self.server._baseurl}, Cooldown: {self.cooldown}s"
        )

    def add_path(self, path: str) -> None:
        p = Path(self._MEDIA_ROOT, path).resolve()
        if not p.exists():
            raise FileNotFoundError(f"Path '{p}' does not exist.")
        self.paths.add(p)
        logger.info(f"Added path to watch list: {p}")

    def remove_path(self, path: str) -> None:
        """Remove a path from the watch list."""
        p = Path(self._MEDIA_ROOT, path).resolve()
        if p in self.paths:
            self.paths.discard(p)
            logger.info(f"Removed path from watch list: {p}")
        else:
            raise ValueError(f"Path '{p}' is not in the watch list.")

    def start(self) -> None:
        with self._lock:
            if not self.server or not self.handler:
                raise RuntimeError("PlexWatcherService is not configured. Call configure() first.")
            if not self.paths:
                raise RuntimeError("No paths configured. Call add_path() first.")
            if self.is_watching:
                return  # already watching
            for path in self.paths:
                self.observer.schedule(self.handler, str(path), recursive=True)
            self.observer.start()
            self.is_watching = True
            logger.info(f"Plex Watcher started. Watching ({len(self.paths)}) paths.")

    def stop(self) -> None:
        with self._lock:
            if not self.is_watching:
                return  # not watching

            # Stop the handler first to cleanup timers
            if self.handler:
                self.handler.stop()

            self.observer.stop()
            self.observer.join()
            self.is_watching = False

            # Create a new observer for potential restart
            self.observer = watchdog.observers.Observer()
            logger.info("Plex Watcher stopped.")

    def restart(self) -> None:
        self.stop()
        self.start()

    def scan_path(self, path: str) -> None:
        if not self.scanner:
            raise RuntimeError("PlexWatcherService is not configured. Call configure() first.")
        p = Path(self._MEDIA_ROOT, path).resolve()
        if not p.exists():
            raise FileNotFoundError(f"Path '{p}' does not exist.")
        self.scanner.scan_section(PlexPath(self.scanner._roots, p))
        logger.info(f"Manual scan initiated for path: {p}")
