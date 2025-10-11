import argparse
import sys
from pathlib import Path

import watchdog.observers
from plexapi.server import PlexServer

from backend import __version__, logger
from backend.core.plex_scanner import PlexScanner
from backend.core.plex_watcher_handler import PlexWatcherHandler

# usage example
# plex-watcher --path /path/to/watch1 --path /path/to/watch2 --server http://localhost:32400 --token YOUR_PLEX_TOKEN --interval 10


def main():
    # Set up basic logging

    # Argument parser setup
    parser = argparse.ArgumentParser(description="Plex Watcher")
    parser.add_argument("-v", "--version", action="version", version=f"plex-watcher v{__version__}")
    parser.add_argument("-p", "--path", action="append", help="Path to watch")
    parser.add_argument("-s", "--server", type=str, help="Plex server URL")
    parser.add_argument("-t", "--token", type=str, help="Plex token")
    parser.add_argument(
        "-i", "--interval", type=int, default=10, help="Polling interval in seconds"
    )
    args = parser.parse_args()

    if not args.path or not args.server or not args.token:
        parser.error("All arguments --path, --server, and --token are required.")

    # setup Plex server connection
    try:
        observer = watchdog.observers.Observer()
        paths = [Path(p).resolve() for p in args.path]
        server = PlexServer(baseurl=args.server, token=args.token)
        interval = args.interval

        handler = PlexWatcherHandler(PlexScanner(plex=server), observer, cooldown=interval)
        for path in paths:
            if not path.exists():
                logger.warning(f"Path '{path}' does not exist. Skipping.")
                continue
            observer.schedule(handler, str(path), recursive=True)
            logger.info(f"Watching: {path}")
    except Exception as e:
        logger.exception(f"Error initializing Plex Watcher: {e}")
        sys.exit(1)

    try:
        observer.start()
        logger.info("Plex Watcher started. Press Ctrl+C to stop.")
        observer.join()  # wait for ctrl+c
    except KeyboardInterrupt:
        logger.info("Ctrl+C received, shutting down…")
    except Exception as e:
        logger.exception(f"Unexpected error during runtime: {e}")
    finally:
        observer.stop()
        observer.join()
        logger.info("Plex Watcher stopped.")


if __name__ == "__main__":
    main()
