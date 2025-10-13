# Plex-Watcher Frontend

Frontend application for Plex-Watcher. Built with SvelteKit.

## Features

- User-friendly interface to monitor and manage your Plex server.
- Independent of the backend, allowing for flexible deployment.
- Manual partial scanning.

## Installation

### Local Deployment

Recommended for LXC containers or local machines for direct deployment without docker.
Node.js and npm are required.

1. Download latest release

```bash
VERSION=$(curl -s "https://api.github.com/repos/sean1832/plex-watcher/releases/latest" | grep '"tag_name":' | sed -E 's/.*"([^"]+)".*/\1/')
curl -L -O "https://github.com/sean1832/plex-watcher/releases/download/$VERSION/frontend-build.zip"
```

2. Unzip the downloaded file

```bash
unzip frontend-build.zip -d plex-watcher-frontend
```

3. Deploy the contents of the `plex-watcher-frontend` directory to your web server.

```bash
node plex-watcher-frontend
```

> Access the app at `http://0.0.0.0:3000` or `http://localhost:3000` after starting the server.

### Docker
Comming soon...

