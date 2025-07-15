import watchdog.events
from watchdog.observers.api import BaseObserver

from plex_watcher.core.consts import ALLOWED_EXTENSIONS
from plex_watcher.core.plex_scanner import PlexScanner

# https://github.com/pushingkarmaorg/python-plexapi


class PlexWatcherHandler(watchdog.events.FileSystemEventHandler):
    def __init__(self, scanner: PlexScanner, observer: BaseObserver):
        super().__init__()
        self.scanner = scanner
        self.observer = observer

    def _is_valid_file(self, path: str) -> bool:
        return any(path.endswith(ext) for ext in ALLOWED_EXTENSIONS)

    def on_created(self, event):
        # If it's a new directory, start watching it (and its subfolders)
        path = str(event.src_path)
        if event.is_directory:
            self.observer.schedule(self, path, recursive=True)
            print(f"Watching new directory: {path}")
            return super().on_created(event)

        if self._is_valid_file(path):
            print(f"New file created: {path}")
            self.scanner.scan_section(path)
        return super().on_created(event)

    def on_modified(self, event):
        # If it's a new directory, start watching it (and its subfolders)
        path = str(event.src_path)
        if event.is_directory:
            self.observer.schedule(self, path, recursive=True)
            print(f"Watching new directory: {path}")
            return super().on_modified(event)

        if self._is_valid_file(path):
            print(f"File modified: {path}")
            self.scanner.scan_section(path)
        return super().on_modified(event)

    def on_deleted(self, event):
        # If it's a new directory, start watching it (and its subfolders)
        path = str(event.src_path)
        if event.is_directory:
            self.observer.schedule(self, path, recursive=True)
            print(f"Watching new directory: {path}")
            return super().on_deleted(event)

        if self._is_valid_file(path):
            print(f"File deleted: {path}")
            self.scanner.scan_section(path)
        return super().on_deleted(event)

    def on_moved(self, event):
        # If it's a new directory, start watching it (and its subfolders)
        path = str(event.dest_path)
        if event.is_directory:
            self.observer.schedule(self, path, recursive=True)
            print(f"Watching new directory: {path}")
            return super().on_moved(event)
        if self._is_valid_file(path):
            print(f"File moved: {event.src_path} to {path}")
            self.scanner.scan_section(path)
        return super().on_moved(event)
