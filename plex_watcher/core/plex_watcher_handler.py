import time
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

    def _is_valid_file(self, path: str) -> bool:
        return any(path.endswith(ext) for ext in ALLOWED_EXTENSIONS)

    def _ready(self):
        logger.info("Waiting for changes...")

    def _schedule_ready(self):
        """Schedule a call to _ready after cooldown."""
        time.sleep(self.cooldown)
        self._ready()
    
    def _handle_event(self, event, verb: str):
        path = str(event.src_path)
        logger.info(f"{verb}: {path}")
        self.scanner.scan_section(path)
        self._schedule_ready()

    def on_created(self, event):
        # If it's a new directory, start watching it (and its subfolders)
        path = str(event.src_path)
        if event.is_directory:
            self.observer.schedule(self, path, recursive=True)
            logger.info(f"Watching new directory: {path}")
            return super().on_created(event)

        if self._is_valid_file(path):
            self._handle_event(event, "CREATED")
        return super().on_created(event)

    def on_modified(self, event):
        if not event.is_directory:
            path = str(event.src_path)
            if self._is_valid_file(path):
                self._handle_event(event, "MODIFIED")
        return super().on_modified(event)

    def on_deleted(self, event):
        if not event.is_directory:
            path = str(event.src_path)
            if self._is_valid_file(path):
                self._handle_event(event, "DELETED")                
        return super().on_deleted(event)

    def on_moved(self, event):
        if not event.is_directory:
            dest = str(event.dest_path)
            if self._is_valid_file(dest):
                self._handle_event(event, "MOVED")
        return super().on_moved(event)
