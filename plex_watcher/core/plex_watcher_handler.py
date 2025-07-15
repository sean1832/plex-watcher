import threading
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

        # queue up all file-paths that need scanning
        self._pending_paths: set[str] = set()
        self._timer: Optional[threading.Timer] = None

    def _do_scan(self):
        # scan every outstanding path, then clear the queue
        for path in self._pending_paths:
            logger.info(f"SCANNING: {path}")
            self.scanner.scan_section(path)
        self._pending_paths.clear()

        # signal ready again
        logger.info("Waiting for changes…")

    def _schedule_scan(self, path: str):
        # add to queue
        self._pending_paths.add(path)

        # reset timer so we only fire once, cooldown after the last event
        if self._timer and self._timer.is_alive():
            self._timer.cancel()

        self._timer = threading.Timer(self.cooldown, self._do_scan)
        self._timer.daemon = True
        self._timer.start()

    def _is_valid_file(self, path: str) -> bool:
        return any(path.endswith(ext) for ext in ALLOWED_EXTENSIONS)

    def _handle_event(self, path: str, verb: str):
        if path in self._pending_paths:
            return  # already scheduled

        logger.info(f"{verb}: {path}")
        # debounce + queue
        self._schedule_scan(path)

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
