import threading
from pathlib import Path
from typing import Optional

import watchdog.events
from watchdog.observers.api import BaseObserver

from plex_watcher import logger
from plex_watcher.core.consts import ALLOWED_EXTENSIONS
from plex_watcher.core.plex_scanner import PlexScanner

# https://github.com/pushingkarmaorg/python-plexapi


class PlexWatcherHandler(watchdog.events.FileSystemEventHandler):
    def __init__(self, scanner: PlexScanner, observer: BaseObserver, cooldown: int):
        super().__init__()
        self.scanner = scanner
        self.observer = observer
        self.cooldown = cooldown

        # queue up all media root that need scanning
        self._pending_paths: set[str] = set()
        self._timer: Optional[threading.Timer] = None

    def _do_scan(self):
        # scan every outstanding path, then clear the queue
        for path in self._pending_paths:
            self.scanner.scan_section(path)
        self._pending_paths.clear()

        # signal ready again
        logger.info("Waiting for changes...")

    def _schedule_scan(self, path: str):
        # add to queue
        self._pending_paths.add(path)

        # reset timer so we only fire once, cooldown after the last event
        if self._timer and self._timer.is_alive():
            self._timer.cancel()

        self._timer = threading.Timer(self.cooldown, self._do_scan)
        self._timer.daemon = True
        self._timer.start()

    def _get_media_root(self, path: str) -> str:
        """
        For any file or folder event, return the top-level item folder
        directly under its Plex section root.
        e.g.
          /.../TV-Show/Anime/Naruto/Season 1/... -> .../TV-Show/Anime/Naruto
          /.../Movie/Inception/Inception.mp4    -> .../Movie/Inception
        """
        p = Path(path).resolve()
        if not p.is_dir():
            p = p.parent

        # find which Plex library root this lives in
        for plex_root, _ in self.scanner._roots:
            try:
                rel = p.relative_to(plex_root)
            except ValueError:
                continue

            # if there's at least one subfolder under the section,
            # that's your item root
            if rel.parts:
                return str(plex_root / rel.parts[0])

            # (rare) file directly in the library root -> just scan that dir
            return str(plex_root)

        # fallback: scan the directory itself
        return str(p)

    def _is_valid_file(self, path: str) -> bool:
        return any(path.endswith(ext) for ext in ALLOWED_EXTENSIONS)

    def _handle_event(self, path: str, verb: str):
        # 1) find the local "media root" folder
        local_item = Path(self._get_media_root(path)).resolve()

        # 2) immediately turn it into the Plex path
        plex_item = self.scanner._auto_map_to_plex(local_item)

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
                self._handle_event(path, "CREATED")
        return super().on_created(event)

    def on_modified(self, event):
        path = str(event.src_path)
        if not event.is_directory and self._is_valid_file(path):
            self._handle_event(path, "MODIFIED")
        return super().on_modified(event)

    def on_deleted(self, event):
        path = str(event.src_path)
        if not event.is_directory and self._is_valid_file(path):
            self._handle_event(path, "DELETED")
        return super().on_deleted(event)

    def on_moved(self, event):
        dest = str(event.dest_path)
        if not event.is_directory and self._is_valid_file(dest):
            self._handle_event(dest, "MOVED")
        return super().on_moved(event)
