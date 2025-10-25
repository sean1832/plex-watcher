# Plex-Watcher Copilot Instructions

## Project Overview

Plex-Watcher is a monorepo containing a **Go backend** service that monitors filesystem changes and triggers Plex library updates, plus a **SvelteKit 5 frontend** for web UI control. The backend runs as an HTTP API server that the frontend communicates with.

**Key architectural shift**: This project was recently rewritten from Python to Go. The backend is now a high-performance Go service using native fsnotify for filesystem watching.

## General Guidelines

- Write clear, idiomatic code following language-specific best practices
- Prioritize simplicity over cleverness
- Focus on code and tests - avoid generating documentation files unless requested
- Log appropriately (structured logging for production, descriptive messages for debugging)

## Architecture & Components

### Backend (`backend/` - Go 1.25+)

**Entry point**: `cmd/server/main.go` - HTTP API server on port 8000

**Core components**:
- **`internal/api/api.go`**: REST API layer with endpoints for start/stop/scan/status. Uses **semaphore pattern** (`scanSemaphore`) to limit concurrent Plex API calls (default: 4)
- **`internal/watcher_manager/manager.go`**: Lifecycle manager for filesystem watcher with mutex-protected state
- **`internal/fs_watcher/fs_watcher.go`**: Filesystem observer using `fsnotify` with **debounce/batching** logic to prevent scan spam during bulk file operations
- **`internal/plex/scanner.go`**: Orchestrates Plex library scans with intelligent path-to-section matching using **longest-prefix matching**
- **`internal/plex/path_mapper.go`**: **Critical** - Maps local filesystem paths to Plex server paths using **longest-suffix matching** (handles Docker volume mounts)
- **`internal/plex/api.go`**: Low-level HTTP client for Plex API (`/library/sections`, `/library/sections/{id}/refresh`)

### Frontend (`frontend/` - SvelteKit 2.x + Svelte 5.x)

- **Framework**: SvelteKit with **Svelte 5 runes** (`$state`, `$derived`, `$effect` - NOT `$:` or stores)
- **Styling**: Tailwind CSS 4.x + shadcn-svelte components (see `src/lib/components/ui/`)
- **API Client**: Type-safe wrapper in `src/lib/api/` with `ApiError` class for error handling
- **State Management**: `src/lib/stores/config.svelte.ts` - reactive config store with localStorage persistence
- **Current status**: Functional UI with API integration; backend connection status probing implemented

## Critical Path Translation Logic

**Problem**: Plex servers often run in Docker with mounted volumes. Example:
- Host path: `/mnt/storage/movies/Inception/Inception.mkv`
- Plex container path: `/media/movies/Inception/Inception.mkv`

**Solution (`path_mapper.go`)**: 
- Uses **longest-suffix matching** on path components (case-insensitive)
- Splits paths into parts, tries matching last K components of Plex roots against local path
- Handles nested library structures by trying longest matches first
- Returns mapped path + matched root, or `ok=false` if no match

**Usage pattern**:
```go
plexPath, matchedRoot, ok := scanner.MapToPlexPath(localPath)
if !ok {
    log.Printf("path %s does not map to any Plex library", localPath)
    return
}
// Use plexPath for Plex API calls
```

## Filesystem Watching & Debouncing

**Debounce strategy** (`fs_watcher.go`):
- Events accumulated in `pending` map (path -> combined ops)
- Timer resets on each new event during `DebounceWindow` (configurable seconds)
- Flush triggered after inactivity period expires
- Prevents spam when copying entire seasons/movie collections

**Recursive watching**:
- When `Recursive: true`, watcher automatically adds new subdirectories via `addRecursive()`
- Triggered on `fsnotify.Create` events for directories

**Event filtering** (`api.go:handleDirUpdate`):
- Ignores `CHMOD` events (no content change)
- Logs event type: CREATE/WRITE/REMOVE/RENAME
- Maps path via `scanner.MapToPlexPath()` before scanning

## Media Type Detection

**TV Show heuristics** (`scanner.go:getMediaTypeForDeleted`):
1. Scans path parts for "Season X" pattern (case-insensitive)
2. Verifies digit follows "season" prefix
3. Strips "Season X" folders via `getShowRootPath()` to scan at show level
4. Falls back to section type detection or defaults to movie

**Why**: Deleted paths can't be checked on disk, so heuristics detect show vs movie structure.

## Development Workflows

### Backend Development

```bash
cd backend

# Build (creates bin/ directory)
go build -o bin/ ./...

# Run server directly
go run cmd/server/main.go
# Server listens on 0.0.0.0:8000

# Run with VS Code task (preferred)
# Use: Tasks: Run Task > "go: build backend"

# Format and vet
go fmt ./...
go vet ./...

# Check dependencies
go mod tidy
go mod verify
```

**No tests yet** - test files (`*_test.go`) don't exist in this codebase.

### Frontend Development

```powershell
cd frontend

# Install dependencies
npm install

# Dev server (localhost:5173 with HMR)
npm run dev

# Production build (outputs to build/)
npm run build

# Preview production build
npm run preview

# Type checking + linting
npm run check        # svelte-check for type safety
npm run lint         # ESLint + Prettier
npm run format       # Auto-format with Prettier
```

### API Endpoints Reference

**Base URL**: `http://localhost:8000`

| Endpoint | Method | Body | Description |
|----------|--------|------|-------------|
| `/` | GET | - | Health check (returns `{"status": "ok"}`) |
| `/status` | GET | - | Returns watcher status |
| `/prob-plex` | GET | `ListSectionsRequest` | Lists all Plex library sections |
| `/start` | POST | `StartRequest` | Start watching with config |
| `/stop` | POST | - | Stop watcher |
| `/scan` | POST | `ScanRequest` | Manually trigger scan for paths |

**Request types** (see `backend/internal/requests/requests.go`):
```go
type StartRequest struct {
    ServerUrl string   `json:"server_url"`
    Token     string   `json:"token"`
    Paths     []string `json:"paths"`
    Cooldown  int      `json:"cooldown"` // debounce seconds
}
```

## Code Conventions

### Go Backend

- **Error handling**: Return errors with context using `fmt.Errorf("action failed: %w", err)`
- **Logging**: Use `log.Printf()` with descriptive messages (TODO: structured logging not yet implemented)
- **Concurrency**: Use mutexes (`sync.Mutex`) for shared state (see `Manager.mutex`, `api.scanSemaphore`)
- **HTTP responses**: Use `writeJSON()` helper in `api.go` for consistent JSON output
- **Path normalization**: Always use `filepath.Clean()` before comparisons

### Svelte 5 Frontend

- **Runes syntax**: `$state` (reactive vars), `$derived` (computed), `$effect` (side effects)
- **Component structure**: `<script>` → markup → `<style>` (if needed)
- **API calls**: Use `src/lib/api/endpoints.ts` functions, not raw fetch
- **Error handling**: Catch `ApiError` instances, display via toast (svelte-sonner)
- **Imports**: Use `$lib` alias: `import { config } from '$lib/stores/config.svelte'`

### TypeScript Types Sync

Keep frontend types (`frontend/src/lib/types/requests.ts`) in sync with Go structs (`backend/internal/requests/requests.go`). Note JSON naming:
- Go: `ServerUrl string \`json:"server_url"\``
- TS: `server_url: string`

## Common Gotchas

1. **Path mapping failures**: If `MapToPlexPath()` returns `ok=false`, the local path doesn't match any Plex library root. Verify Plex sections via `/prob-plex` endpoint.

2. **Concurrent scan limits**: API enforces max 4 concurrent scans via semaphore. Additional scans block until slots available - prevents overwhelming Plex server.

3. **Debounce timing**: Low `cooldown` (< 5s) causes rapid scans during bulk operations. Typical range: 10-30 seconds.

4. **Recursive watching overhead**: Watching large directory trees (thousands of subdirs) can consume significant memory with fsnotify. Consider watching parent directories only.

5. **CORS not implemented**: TODO in `cmd/server/main.go` - frontend must run on same origin or use proxy during development.

6. **Case sensitivity**: Path matching in `path_mapper.go` is case-insensitive (uses `strings.ToLower`), but filesystem operations respect OS case sensitivity.

## Key Files to Understand

- `backend/internal/plex/path_mapper.go` (140 lines): Suffix matching algorithm with sliding window
- `backend/internal/fs_watcher/fs_watcher.go` (270 lines): Debounce logic and recursive watching
- `backend/internal/plex/scanner.go` (257 lines): Section matching and TV show path normalization
- `frontend/src/lib/api/client.ts` (198 lines): API error handling and timeout management
- `frontend/src/lib/stores/config.svelte.ts` (304 lines): Reactive config with persistence

## Deployment Preferences

- **Backend**: Preferred via Docker (TODO: Dockerfile not yet created). Can run as native binary.
- **Frontend**: Build with `npm run build`, deploy with Node.js adapter (`node build/index.js`)
- **LXC/OpenRC**: Alternative deployment for lightweight containers (see frontend README)
- **No authentication**: Currently open API - authentication planned for future

## TODO Items

From code grep:
- `cmd/server/main.go:10`: Implement CORS middleware
- No test files exist yet - consider adding `*_test.go` files for critical paths
