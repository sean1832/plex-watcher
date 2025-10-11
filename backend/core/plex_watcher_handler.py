import threading
from pathlib import Path
from typing import Literal, Optional

import watchdog.events
from watchdog.observers.api import BaseObserver

from backend import logger
from backend.core.consts import ALLOWED_EXTENSIONS
from backend.core.plex_path import PlexPath
from backend.core.plex_scanner import PlexScanner

# https://github.com/pushingkarmaorg/python-plexapi


class PlexWatcherHandler(watchdog.events.FileSystemEventHandler):
    def __init__(self, scanner: PlexScanner, observer: BaseObserver, cooldown: int):
        super().__init__()
        self.scanner = scanner
        self.observer = observer
        self.cooldown = cooldown

        # queue up all media root that need scanning (store as strings for easy comparison)
        self._pending_paths: set[str] = set()
        self._timer: Optional[threading.Timer] = None
        self._lock = threading.Lock()  # Thread safety for pending paths and timer

    def _do_scan(self):
        # scan every outstanding path, then clear the queue
        with self._lock:
            paths_to_scan = list(self._pending_paths)
            self._pending_paths.clear()

        for path_str in paths_to_scan:
            try:
                # Convert string back to PlexPath for scanning
                plex_path = PlexPath(self.scanner._roots, Path(path_str))
                self.scanner.scan_section(plex_path)
            except Exception as e:
                logger.error(f"Error scanning '{path_str}': {e}")

        # signal ready again
        logger.info("Waiting for changes...")

    def _schedule_scan(self, path: str):
        # add to queue (store as string)
        with self._lock:
            self._pending_paths.add(path)

            # reset timer so we only fire once, cooldown after the last event
            if self._timer and self._timer.is_alive():
                self._timer.cancel()

            self._timer = threading.Timer(self.cooldown, self._do_scan)
            self._timer.daemon = True
            self._timer.start()

    def stop(self):
        """Stop the handler and cleanup resources."""
        with self._lock:
            if self._timer and self._timer.is_alive():
                self._timer.cancel()
                self._timer = None
            self._pending_paths.clear()

    def __del__(self):
        """Cleanup timer on deletion."""
        try:
            if hasattr(self, "_timer") and self._timer and self._timer.is_alive():
                self._timer.cancel()
        except Exception:
            pass  # Ignore errors during cleanup

    def _get_media_root(self, path: str, media_type: Literal["movie", "show"]) -> str:
        """
        Return the top-level item folder under its Plex section root:
        - movie:  .../Movie/Inception/Inception.mp4  -> .../Movie/Inception
        - show: .../TV-Show/Anime/Naruto/Season 1/E01.mp4 -> .../TV-Show/Anime/Naruto
        """
        p = Path(path)

        # if it's a file, start from its parent folder
        if not p.is_dir():
            p = p.parent

        if media_type == "movie":
            # the movie’s folder is exactly where the file lives
            item_root = p

        elif media_type == "show":
            # skip over “Season X” and land in the show’s main folder
            item_root = p.parent

        else:
            # fallback: just scan whatever folder you’ve got
            item_root = p

        return str(item_root)

    def _is_valid_file(self, path: str) -> bool:
        return any(path.endswith(ext) for ext in ALLOWED_EXTENSIONS)

    def _handle_event(self, path: str, verb: str, media_type: Literal["movie", "show"]):
        # 1) find the local "media root" folder
        local_item = Path(self._get_media_root(path, media_type)).resolve()

        # 2) immediately turn it into the Plex path
        plex_item = PlexPath(self.scanner._roots, local_item)

        if str(plex_item) in self._pending_paths:
            return

        logger.info(f"{verb}: {path}")
        self._schedule_scan(str(plex_item))

    def on_created(self, event):
        if event.is_directory:
            # watch new folders too
            new_dir = str(event.src_path)
            self.observer.schedule(self, new_dir, recursive=True)
            logger.info(f"Watching new directory: {new_dir}")
        else:
            path = str(event.src_path)
            if self._is_valid_file(path):
                remote_path = PlexPath(self.scanner._roots, Path(path).resolve())
                self._handle_event(path, "CREATED", self.scanner.get_type(remote_path))
        return super().on_created(event)

    def on_modified(self, event):
        path = str(event.src_path)
        if not event.is_directory and self._is_valid_file(path):
            remote_path = PlexPath(self.scanner._roots, Path(path).resolve())
            self._handle_event(path, "MODIFIED", self.scanner.get_type(remote_path))
        return super().on_modified(event)

    def on_deleted(self, event):
        if event.is_directory:
            return super().on_deleted(event)
        path = str(event.src_path)
        if self._is_valid_file(path):
            # Use validate=False for deleted files since they no longer exist
            remote_path = PlexPath(self.scanner._roots, Path(path).resolve(), validate=False)
            self._handle_event(path, "DELETED", self.scanner.get_type(remote_path))

        return super().on_deleted(event)

    def on_moved(self, event):
        dest = str(event.dest_path)
        remote_path = PlexPath(self.scanner._roots, Path(dest).resolve())
        if not event.is_directory and self._is_valid_file(dest):
            self._handle_event(dest, "MOVED", self.scanner.get_type(remote_path))
        return super().on_moved(event)
