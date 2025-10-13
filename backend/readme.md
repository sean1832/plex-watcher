# Plex-Watcher Backend

Backend API service for Plex-Watcher. Built with FastAPI.

## Features

- RESTful API to interact with Plex-Watcher.
- Independent of the frontend, allowing for flexible deployment.
- Supports both `.env` file and system environment variables (Docker-compatible).

## Configuration

### Environment Variables

The backend can be configured using environment variables. Priority order:

1. **System environment variables** (highest priority - Docker)
2. **`.env` file** (for local development)
3. **Default values** (lowest priority)

Available environment variables:

| Variable       | Default                     | Description                                                    |
| -------------- | --------------------------- | -------------------------------------------------------------- |
| `API_HOST`     | `0.0.0.0`                   | Host to bind the API server                                    |
| `API_PORT`     | `8000`                      | Port to bind the API server                                    |
| `LOG_LEVEL`    | `INFO`                      | Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)          |
| `MEDIA_ROOT`   | `/media`                    | Base path for media files (used in Docker for path resolution) |
| `CONFIG_PATH`  | `config.json`               | Path to the configuration JSON file                            |
| `CORS_ORIGINS` | `http://localhost:5173,...` | Comma-separated list of allowed CORS origins                   |

### Using .env File (Local Development)

For local development or non-Docker deployments:

1. Copy the example environment file:

   ```bash
   cp .env.example .env
   ```

2. Edit `.env` with your preferred settings:

   ```env
   API_HOST=0.0.0.0
   API_PORT=8000
   LOG_LEVEL=DEBUG
   MEDIA_ROOT=/path/to/your/media
   CONFIG_PATH=/path/to/config.json
   CORS_ORIGINS=http://localhost:5173,http://localhost:4173
   ```

3. Start the backend service (the `.env` file will be automatically loaded):
   ```bash
   plex-watcher-apibackend
   ```

**Note:** The `.env` file is automatically loaded from either:

- The `backend/` directory
- The project root directory

## Installation

### Docker (Recommended)

Docker deployment uses system environment variables. Create a `docker-compose.yml` file:

```yaml
version: "3.8"

services:
  backend:
    image: sean1832/plex-watcher-backend:latest
    container_name: plex-watcher-backend
    ports:
      - "7788:8000"
    environment:
      - API_HOST=0.0.0.0
      - API_PORT=8000
      - LOG_LEVEL=INFO
      - MEDIA_ROOT=/media
      - CONFIG_PATH=/config/config.json
      - CORS_ORIGINS=* # <-- Adjust this for security in production (comma-separated list)
    user: "1036:100" # <-- UID:GID. Must match the user running docker on your host system.
    volumes:
      # Mount your media directories to watch as read-only
      - /path/to/your/media:/media:ro # <-- this should be your media root which contains Movies, TV Shows, etc.
      - /path/to/your/config:/config
    restart: unless-stopped
    networks:
      - plex-watcher-network

networks:
  plex-watcher-network:
    driver: bridge
```

Adjust the paths in the `docker-compose.yml` file as needed, then start the service:

```bash
docker-compose up -d
```

### Local Deployment

Recommended for LXC containers or local machines for direct deployment without Docker.

1. Download latest release:

```bash
VERSION=$(curl -s "https://api.github.com/repos/sean1832/plex-watcher/releases/latest" | grep '"tag_name":' | sed -E 's/.*"([^"]+)".*/\1/')
curl -L -O "https://github.com/sean1832/plex-watcher/releases/download/$VERSION/plex_watcher_backend-$VERSION-py3-none-any.whl"
```

2. Install the downloaded wheel file:

```bash
python -m venv venv
source ./venv/bin/activate  # On Windows: .\venv\Scripts\activate
pip install plex_watcher_backend-$VERSION-py3-none-any.whl
```

3. Create a `.env` file in your working directory (see [Configuration](#configuration) above):

```bash
cp .env.example .env
# Edit .env with your settings
```

4. Start the backend service:

```bash
plex-watcher-apibackend
```

The service will automatically load settings from the `.env` file.

## Development

For development with editable installation:

```bash
# From project root
pip install -e backend/

# Create .env file
cp backend/.env.example backend/.env
# Edit backend/.env as needed

# Run the API server
plex-watcher-apibackend
```

## Command Line Options

You can override environment variables using command line arguments:

```bash
plex-watcher-apibackend --host 127.0.0.1 --port 9000
```

Available options:

- `-H`, `--host`: API server host (overrides `API_HOST`)
- `-P`, `--port`: API server port (overrides `API_PORT`)
