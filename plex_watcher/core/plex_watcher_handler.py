import watchdog.events

from plex_watcher.core.consts import ALLOWED_EXTENSIONS
from plex_watcher.core.plex_scanner import PlexScanner

# https://github.com/pushingkarmaorg/python-plexapi


class PlexWatcherHandler(watchdog.events.FileSystemEventHandler):
    def __init__(self, scanner: PlexScanner):
        super().__init__()
        self.scanner = scanner

    def _is_valid_file(self, path: str) -> bool:
        return any(path.endswith(ext) for ext in ALLOWED_EXTENSIONS)

    def on_created(self, event):
        path = str(event.src_path)
        if not event.is_directory and self._is_valid_file(path):
            print(f"New file created: {path}")
            self.scanner.scan_partial(path)
        return super().on_created(event)

    def on_modified(self, event):
        path = str(event.src_path)
        if not event.is_directory and self._is_valid_file(path):
            print(f"File modified: {path}")
            self.scanner.scan_partial(path)
        return super().on_modified(event)

    def on_deleted(self, event) -> None:
        path = str(event.src_path)
        if not event.is_directory and self._is_valid_file(path):
            print(f"File deleted: {path}")
            self.scanner.scan_partial(path)
        return super().on_deleted(event)

    def on_moved(self, event) -> None:
        path = str(event.src_path)
        if not event.is_directory and self._is_valid_file(path):
            print(f"File moved from {path} to {event.dest_path}")
            self.scanner.scan_partial(path)
        return super().on_moved(event)
