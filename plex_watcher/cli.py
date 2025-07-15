import argparse
import time
from pathlib import Path

import watchdog.observers
from plexapi.server import PlexServer

from plex_watcher import __version__
from plex_watcher.core.plex_scanner import PlexScanner
from plex_watcher.core.plex_watcher_handler import PlexWatcherHandler

# usage example
# plex-watcher --path /path/to/watch1 --path /path/to/watch2 --server http://localhost:32400 --token YOUR_PLEX_TOKEN --interval 10


def main():
    parser = argparse.ArgumentParser(description="Plex Watcher")
    parser.add_argument("-v", "--version", action="version", version=f"plex-watcher v{__version__}")
    parser.add_argument("-p", "--path", action="append", help="Path to watch")
    parser.add_argument("-s", "--server", type=str, help="Plex server URL")
    parser.add_argument("-t", "--token", type=str, help="Plex token")
    parser.add_argument(
        "-i", "--interval", type=int, default=30, help="Polling interval in seconds"
    )
    args = parser.parse_args()

    if not args.path or not args.server or not args.token:
        parser.error("All arguments --path, --server, and --token are required.")

    observer = watchdog.observers.Observer()
    try:
        paths = [Path(p).resolve() for p in args.path]
        server = PlexServer(baseurl=args.server, token=args.token)
        interval = args.interval

        handler = PlexWatcherHandler(PlexScanner(plex=server), observer)
        for path in paths:
            if not path.exists():
                print(f"Path '{path}' does not exist. Skipping.")
                continue
            observer.schedule(handler, str(path), recursive=True)
            print(f"Watching: {path}")

        observer.start()
        print("Plex Watcher started. Press Ctrl+C to stop.")
        print("Waiting for changes...")

        try:
            while True:
                time.sleep(interval)
                print("Watching for changes...")
        except KeyboardInterrupt:
            observer.stop()
            print("\nStopping Plex Watcher...")
    except Exception as e:
        print(f"Error: {e}")
        print("Exiting...")
        exit(1)
    finally:
        observer.stop()
        observer.join()


if __name__ == "__main__":
    main()
