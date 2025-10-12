# Plex-Watcher Copilot Instructions

## Project Overview

Plex-Watcher is a monorepo containing a Python backend service that monitors filesystem changes and triggers Plex library updates, plus a SvelteKit frontend for web UI control. The backend can run standalone via CLI or as a FastAPI server controlled by the frontend.

## General Instructions

- Provide clear, concise code
- Follow existing code style and conventions
- Prioritize readability and maintainability
- Use type hints and docstrings
- Write modular, testable functions and classes
- Avoid unnecessary complexity; prefer simple solutions
- Ensure proper error handling and logging
- Do not write bunch of .md files after done, just focus on code and tests

## Architecture & Key Concepts

### Backend Structure (`backend/`)

- **Entry points**: `cli.py` (standalone watcher) and `api_server.py` (FastAPI server for frontend)
- **Core services** (`backend/core/`):
  - `PlexWatcherService`: Orchestrates observer, handler, and scanner; manages configuration and threading
  - `PlexWatcherHandler`: Watchdog event handler that queues changes with cooldown-based debouncing (prevents scan spam)
  - `PlexScanner`: Interacts with Plex API to trigger library updates for specific paths
  - `PlexPath`: Critical path translation layer - converts between host filesystem paths and Plex container/library paths using fuzzy suffix matching

### Path Translation Pattern

**The `PlexPath` class is central to the architecture.** Plex servers often run in Docker with mounted volumes (e.g., `/media/movies` in container vs `/mnt/storage/movies` on host). `PlexPath._convert_to_plex_path()` uses longest-suffix matching to intelligently map host paths to Plex library roots. When working with paths:

- Always create `PlexPath` instances for validation before scanning
- Use `validate=False` only when you trust the input is already a Plex path
- The `_roots` list (from `PlexScanner._roots`) contains `(Path, LibrarySection)` tuples sorted longest-first

### Debouncing & Cooldown Strategy

File changes are queued in `PlexWatcherHandler._pending_paths` (set of strings) and scanned after `cooldown` seconds of inactivity. This batches rapid file operations (e.g., copying entire seasons) into single scans per show/movie folder. The timer resets on each new event.

### Environment Variables (Docker/Config)

- `MEDIA_ROOT`: Base path for relative path resolution in Docker context (default: `/media`)
- `CONFIG_PATH`: JSON config file location for persistence across restarts (default: `config.json`)
- `API_HOST`, `API_PORT`: FastAPI server binding (defaults: `0.0.0.0:8000`)

### Frontend Structure (`frontend/`)

- **Framework**: SvelteKit 2.x with Svelte 5.x (runes syntax)
- **Styling**: Tailwind CSS 4.x with Vite plugin
- **Components**: UI components in `src/lib/components/`, reusable utilities in `src/lib/utils.ts`
- **Current state**: Minimal skeleton (NavBar with mode toggle); backend API integration not yet implemented

## Frontend Plans and Deployment

### Svelte-Based Web UI

The frontend will be a SvelteKit-based reactive web UI, designed to be lightweight, efficient, and deployable independently of the backend. Key features include:

- **Dashboard**: Displays the current status of the backend server. Users can manually refresh to fetch the latest status (no real-time updates to minimize API calls).
- **Path Management**: Provides a clear and intuitive interface for adding or removing paths to watch. Users can also manually trigger scans for specific directories.

### Deployment Preferences

- **Frontend**: Preferred deployment is via OpenRC in an LXC container for simplicity and performance. Docker deployment is also supported.
- **Backend**: Preferred deployment is via Docker. Systemd or OpenRC can also be used for environments where Docker is not available.

Both frontend and backend should prioritize:

- Lightweight and efficient design
- Simplicity and clarity in both UI and architecture
- High performance, leveraging Svelte's strengths for the frontend

### Authentication

Authentication is not a priority at the moment but will be implemented later. Future updates to the instructions will include details on integrating authentication mechanisms.

## Development Workflows

### Backend Development

```bash
# Install in editable mode (from project root)
pip install -e backend/

# Run CLI directly
plex-watcher -p /path/to/media -s http://localhost:32400 -t YOUR_TOKEN -i 10

# Run API server
plex-watcher-apibackend
# or: python backend/api_server.py

# Run tests with coverage
pytest --cov=backend --cov-report=html
# View coverage: htmlcov/index.html
```

### Frontend Development

```bash
cd frontend
npm install
npm run dev          # Dev server at localhost:5173
npm run build        # Production build
npm run check        # Type checking with svelte-check
npm run lint         # ESLint + Prettier
```

### Docker Deployment

```bash
cd backend
docker build -t plex-watcher-backend .
docker-compose up -d
```

**Key Docker considerations:**

- `user: "1036:100"` must match host UID:GID for file access permissions
- Mount media as `:ro` (read-only) for safety
- `MEDIA_ROOT` environment variable determines path resolution base

## Testing Conventions

### Test Structure

- **Unit tests** (`tests/unit/`): Mock external dependencies (Plex API, filesystem)
- **Integration tests** (`tests/integration/`): Test full workflows with real filesystem fixtures
- **Fixtures** (`tests/conftest.py`): Shared mocks (`mock_plex_server`, `mock_movie_section`, `mock_roots`) and temp directories

### Key Testing Patterns

```python
# Always use mock_roots fixture for PlexPath tests
def test_path_conversion(mock_roots, sample_movie_structure):
    movie_file = sample_movie_structure / "Inception" / "Inception.mkv"
    plex_path = PlexPath(mock_roots, movie_file)
    assert plex_path.exists()

# Mock PlexServer API calls to avoid real network requests
@pytest.fixture
def mock_plex_server():
    server = Mock(spec=PlexServer)
    server._baseurl = "http://localhost:32400"
    # ... setup library sections
```

### Running Tests

```bash
pytest                          # All tests
pytest tests/unit/              # Unit tests only
pytest -m integration           # Integration tests only
pytest -k "test_path"           # Pattern matching
pytest --cov-report=term-missing  # Show uncovered lines
```

## Code Conventions

### Python

- **Logging**: Use `backend.logger` (already configured in `__init__.py`), not print statements
- **Type hints**: Required for function signatures (see `PlexScanner.get_type() -> Literal["movie", "show"]`)
- **Error handling**: Raise specific exceptions with context (e.g., `ValueError(f"No Plex section found for '{directory}'")`)
- **Threading**: Use locks (`threading.Lock`) when accessing shared state (see `PlexWatcherHandler._lock`, `PlexWatcherService._lock`)

### Frontend (Svelte 5)

- **Runes syntax**: Use `$state`, `$derived`, `$effect` for reactivity (not `$:` or stores)
- **Component structure**: Script tag first, then markup, then styles
- **Styling**: Use Tailwind utility classes; custom components in `src/lib/components/ui/`
- **Imports**: Use `$lib` alias for lib imports (e.g., `import { foo } from '$lib/utils'`)

### Styling with shadcn-svelte

For UI components, this project uses `shadcn-svelte` for consistent and reusable styling. All components should follow this pattern to maintain a cohesive design system. For example:

- Use `shadcn-svelte` components for buttons, toggles, and other interactive elements.
- Ensure that custom components extend or integrate with `shadcn-svelte` styles where applicable.

Refer to the `ModeToggle.svelte` component in `src/lib/components/ui/button/` for an example of how to implement this styling approach.

## API Design (FastAPI Backend)

### Current Endpoints

- `GET /status`: Returns watcher state (is_watching, paths, server, cooldown)
- `POST /start`: Configure and start watcher (params: server_url, token, interval)
- `POST /stop`: Stop watching
- `POST /add_path` / `POST /remove_path`: Manage watched directories
- `POST /scan`: Manually trigger scan for specific paths (accepts `ScanRequest` with path list)

### Adding New Endpoints

1. Define Pydantic models for request bodies (see `ScanRequest`)
2. Add route to `router()` function in `api_server.py`
3. Use `service.method()` to interact with `PlexWatcherService`
4. Return consistent JSON: `{"status": "success/error", "message": "...", "details": [...]}`

## Common Gotchas

1. **Path resolution in Docker**: Always test path mappings with `PlexPath` - suffix matching can fail if Plex library roots overlap
2. **Cooldown timing**: Lower cooldown = faster scans but more CPU; typical range 5-30s
3. **Allowed extensions**: Only files matching `ALLOWED_EXTENSIONS` in `consts.py` trigger scans
4. **Section type detection**: `PlexScanner.get_type()` determines movie vs show; affects how `_get_media_root()` calculates scan paths (shows strip "Season X" folder)
5. **Frontend-backend integration**: Not yet implemented - API calls, state management, and error handling need to be added

## Key Files Reference

- `backend/core/plex_path.py`: Path translation logic (150+ lines, complex suffix matching)
- `backend/core/plex_watcher_handler.py`: Event handling and debouncing (150+ lines)
- `tests/conftest.py`: Test fixtures and mocks (140+ lines)
- `backend/docker-compose.yml`: Deployment configuration with volume mounts and env vars
