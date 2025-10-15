# Plex Watcher Backend (Go)

A high-performance Go backend service for monitoring filesystem changes and triggering Plex library updates.

## Overview

This backend provides a robust API for managing Plex library scans. It intelligently maps filesystem paths to Plex library sections and handles both movie and TV show libraries with proper path resolution.

## Architecture

### Core Components

#### `PlexClient` (`api.go`)
- **Purpose**: Low-level interface to Plex API using the plexgo SDK
- **Key Methods**:
  - `ListLibraries(ctx)` - Fetches all library sections from Plex server
  - `RefreshSection(ctx, sectionKey, path)` - Triggers a library scan for a specific path

#### `Scanner` (`scanner.go`)
- **Purpose**: High-level scanning logic with intelligent path-to-section matching
- **Key Features**:
  - Longest-prefix matching for nested library structures
  - Media type detection (movie vs. TV show)
  - Path normalization for show-level scanning
  - Heuristic analysis for deleted paths

#### `SectionRoot` (`types.go`)
- **Purpose**: Represents a Plex library section with its metadata
- **Fields**:
  - `SectionKey` - Numeric section identifier
  - `SectionTitle` - Human-readable library name
  - `SectionType` - `MediaType` enum (movie/show)
  - `RootPath` - Absolute path to library root

### Path Translation

The scanner uses **longest-prefix matching** to map filesystem paths to Plex sections:

1. All library roots are sorted by path length (longest first)
2. For each path, the scanner finds the first root that contains it
3. This handles nested libraries correctly (e.g., `/media/movies` vs `/media/movies/4k`)

### Media Type Detection

The scanner determines media type using multiple strategies:

**For existing paths:**
- Direct section type lookup

**For deleted paths (heuristic mode):**
1. Checks for "Season X" pattern in path structure
2. Falls back to section detection if possible
3. Defaults to movie type if no clear indicators

### Show-Level Scanning

For TV shows, the scanner automatically strips "Season X" folders:
- Input: `/media/shows/Breaking Bad/Season 1/episode.mkv`
- Scan path: `/media/shows/Breaking Bad`

This ensures Plex scans the entire show, not just one season.

## Usage

### Creating a Scanner

```go
import (
    "context"
    "github.com/LukeHagar/plexgo"
    "plex-watcher-backend/internal/plex"
)

// Initialize Plex SDK
sdk := plexgo.New(
    plexgo.WithSecurity("YOUR_PLEX_TOKEN"),
    plexgo.WithServerURL("http://localhost:32400"),
)

// Create API client
client := plex.NewPlexClient(sdk, "http://localhost:32400", "YOUR_TOKEN", nil)

// Create scanner
ctx := context.Background()
scanner, err := plex.NewScanner(ctx, client)
if err != nil {
    log.Fatal(err)
}
```

### Scanning a Path

```go
import "time"

// Determine media type
mediaType, err := scanner.GetMediaType("/media/movies/Inception/Inception.mkv", false)
if err != nil {
    log.Fatal(err)
}

// Get optimal scan path (parent dir for movies, show root for TV)
scanPath := scanner.GetScanPath("/media/movies/Inception/Inception.mkv", mediaType)

// Trigger scan with cooldown
err = scanner.ScanPath(ctx, scanPath, 500*time.Millisecond)
if err != nil {
    log.Fatal(err)
}
```

### Handling Deleted Files

```go
// For deleted paths, use heuristic detection
mediaType, err := scanner.GetMediaType(
    "/media/shows/Breaking Bad/Season 1/deleted.mkv", 
    true, // isDeleted = true
)
```

## Design Patterns

### Error Handling
- All errors are wrapped with context using `fmt.Errorf` with `%w`
- Errors include helpful diagnostic information (available roots, etc.)
- Logging at appropriate levels (info for operations, warning for issues)

### Performance Optimizations
1. **Pre-sorted roots** - Avoids repeated sorting on each lookup
2. **Map-based section lookup** - O(1) title-based retrieval
3. **Minimal filesystem calls** - Path operations use string manipulation where possible

### Code Style
- **Clarity over cleverness** - Straightforward logic, minimal abstractions
- **Self-documenting** - Clear function/variable names, comprehensive comments
- **Idiomatic Go** - Follows standard Go conventions and patterns

## Testing

```bash
# Run all tests
go test ./internal/plex/...

# Run with coverage
go test -cover ./internal/plex/...

# Verbose output
go test -v ./internal/plex/...
```

## Building

```bash
# Build the server
go build -o bin/server ./cmd/server

# Run the server
./bin/server
```

## Docker Deployment

See `docker-compose.yml` for containerized deployment configuration.

## Dependencies

- `github.com/LukeHagar/plexgo` - Official Plex Go SDK

## Future Enhancements

- [ ] Filesystem watcher integration
- [ ] Batch scanning with debouncing
- [ ] Configuration file support
- [ ] Graceful shutdown handling
- [ ] Prometheus metrics
