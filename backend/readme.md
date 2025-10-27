# Plex Watcher Backend

Monitors filesystem changes and auto-scans Plex libraries. Debounces bulk operations, maps Docker paths, handles TV shows intelligently.

## Overview

A lightweight Go service that watches your media directories and automatically triggers Plex library scans when files change.

## Features
- **Smart path mapping** - Handles Docker volume mounts (host paths -> container paths)
- **Debounced scanning** - Batches rapid changes to avoid spamming Plex during bulk operations
- **Concurrent control** - Limits parallel Plex API calls to prevent server overload

Perfect for Docker deployments where Plex sees different paths than your filesystem watcher.

## Quick Start

**Docker Compose (Recommended)**

see [docker-compose.yml](docker-compose.yml)

```bash
docker-compose up -d
```

**Docker**
```bash
docker run -d \
  -p 7788:8080 \
  -v /path/to/media:/media:ro \
  -e CONCURRENCY_LIMIT=10 \
  -e SUPPORTED_EXTENSIONS=.mp4,.mkv,.avi,.mov \
  --user 1036:100 \
  sean1832/plexwatcher-backend:latest
```

**Native**
```bash
go build -o bin/server ./cmd/server
./bin/server  # Listens on :8080
```

> [!TIP]
> You can test if the backend is working after starting it:
> ```bash
> curl http://localhost:7788/status
> ```
> You should see a JSON response with the watcher's status.

## API

| Endpoint     | Method | Body                                     | What It Does                         |
| ------------ | ------ | ---------------------------------------- | ------------------------------------ |
| `/start`     | POST   | `{server_url, token, paths[], cooldown}` | Start watching directories           |
| `/stop`      | POST   | -                                        | Stop watcher                         |
| `/scan`      | POST   | `{server_url, token, paths[]}`           | Manual scan                          |
| `/status`    | GET    | -                                        | Watcher status                       |
| `/prob-plex` | GET    | -                                        | Test Plex connection, list libraries |

**Example Start Request**
```json
{
  "server_url": "http://plex:32400",
  "token": "YOUR_PLEX_TOKEN",
  "paths": ["/media/Movies", "/media/TV Shows"],
  "cooldown": 10
}
```

## Config (Environment Variables)

```bash
CONCURRENCY_LIMIT=10           # Max parallel Plex API calls
SUPPORTED_EXTENSIONS=.mp4,.mkv # File types to trigger scans
```

## How It Works

1. **Watches** filesystem with `fsnotify`
2. **Debounces** events (batch changes within cooldown window)
3. **Maps** local paths to Plex paths (handles Docker mounts via suffix matching)
4. **Scans** correct Plex library section (TV shows auto-strip season folders)