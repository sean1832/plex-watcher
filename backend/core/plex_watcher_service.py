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

    def add_path(self, path: str) -> None:
        """Add a new path to watch."""
        p = Path(self._MEDIA_ROOT, path).resolve()
        if not p.exists():
            raise FileNotFoundError(f"Path '{p}' does not exist.")
        self.paths.add(p)
        logger.info(f"Added path to watch: {p}")

    def configure(self, server_url: str, token: str, interval: int) -> None:
        """Configure scanner and handler with Plex server credentials."""
        self.server = PlexServer(baseurl=server_url, token=token)
        self.cooldown = interval
        self.scanner = PlexScanner(plex=self.server)
        self.handler = PlexWatcherHandler(self.scanner, self.observer, cooldown=self.cooldown)
        logger.info(
            f"Plex Watcher Service configured. Plex Server: {self.server._baseurl}, Cooldown: {self.cooldown}s"
        )

    def update_configuration(
        self, server_url: str, token: str, paths: list[str], cooldown: int
    ) -> None:
        """
        Update complete configuration atomically.

        It accepts the full configuration and applies all
        changes at once, ensuring consistency.

        Args:
            server_url: Plex server URL
            token: Plex authentication token
            paths: List of paths to watch (will replace existing paths)
            cooldown: Debounce cooldown in seconds

        Raises:
            FileNotFoundError: If any path doesn't exist
        """
        # Validate all paths first (fail fast before changing state)
        validated_paths = set()
        for path in paths:
            p = Path(self._MEDIA_ROOT, path).resolve()
            if not p.exists():
                raise FileNotFoundError(f"Path '{p}' does not exist.")
            validated_paths.add(p)

        # Configure server and scanner
        self.server = PlexServer(baseurl=server_url, token=token)
        self.cooldown = cooldown
        self.scanner = PlexScanner(plex=self.server)

        # Update handler with new cooldown (create new handler to avoid timer issues)
        self.handler = PlexWatcherHandler(self.scanner, self.observer, cooldown=self.cooldown)

        # Replace paths atomically
        self.paths = validated_paths

        logger.info(
            f"Configuration updated: Server={self.server._baseurl}, "
            f"Paths={len(self.paths)}, Cooldown={self.cooldown}s"
        )

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
            self.write_config()

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
        """Restart the watcher with the current configuration."""
        self.stop()
        self.start()

    @staticmethod
    def scan_paths(paths: list[str], server_url: str, token: str) -> list[str]:
        """Manually scan multiple paths immediately."""
        if len(paths) == 0:
            logger.info("No paths provided for manual scan.")
            return []

        media_root = Path(os.getenv("MEDIA_ROOT", "/media")).resolve()
        plex = PlexServer(baseurl=server_url, token=token)
        scanner = PlexScanner(plex=plex)
        logger.info(f"Starting manual scan for {len(paths)} paths.")
        errors = []
        for path in paths:
            try:
                p = Path(media_root, path).resolve()
                if not p.exists():
                    raise FileNotFoundError(f"Path '{p}' does not exist.")
                logger.info(f"Manual scan initiated for path: {p}")
                scanner.scan_section(PlexPath.from_path(scanner._roots, p))
            except FileNotFoundError as fnf:
                logger.error(fnf)
                errors.append(str(fnf))
                continue
            except Exception as e:
                logger.error(f"Unhandled error for '{path}': {e}")
                errors.append(f"Unhandled error for {path}: {e}")
                continue
        logger.info("Manual scan completed.")
        return errors
