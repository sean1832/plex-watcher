package api

import (
	"context"
	"encoding/json"
	"log/slog"
	"net/http"
	"os"
	"sync"

	"plexwatcher/internal/plex"
	"plexwatcher/internal/types"
	"plexwatcher/internal/watcher_manager"
)

type Handler struct {
	Watcher *watcher_manager.Manager
	Context context.Context

	scanner           *plex.Scanner
	scanSemaphore     chan struct{}   // limit concurrent scans
	activeScansMutex  sync.Mutex      // protect activeScans map
	activeScans       map[string]bool // track paths currently being scanned
	allowedExtensions []string
	cachePath         string // cache for watchlist
}

// NewHandler creates a new API handler with the specified concurrency limit for scans.
func NewHandler(ctx context.Context, concurrency int, allowedExtensions []string, cachePath string) *Handler {
	if concurrency <= 0 {
		concurrency = 1 // at least 1
		slog.Warn("concurrency must be at least 1, defaulting to 1")
	}

	h := &Handler{
		Watcher:           watcher_manager.NewManager(),
		Context:           ctx,
		scanSemaphore:     make(chan struct{}, concurrency), // limit to specified concurrent scans
		activeScans:       make(map[string]bool),            // initialize deduplication map
		allowedExtensions: allowedExtensions,
		cachePath:         cachePath,
	}
	// Load watchlist from cache if it exists (paths only, no credentials)
	if cachePath != "" {
		if cacheData, err := os.ReadFile(cachePath); err == nil {
			var cache types.WatchlistCache
			if err := json.Unmarshal(cacheData, &cache); err == nil {
				slog.Info("watchlist cache found",
					"paths", cache.Paths,
					"cooldown", cache.Cooldown)
				// Note: Cache only contains paths/cooldown for reference.
				// User must call /start with credentials to actually start the watcher.
			} else {
				slog.Warn("failed to unmarshal cache, ignoring", "error", err)
			}
		} else if !os.IsNotExist(err) {
			slog.Warn("failed to read cache file", "error", err)
		}
	}

	return h
}

// RegisterRoutes sets up the HTTP routes for the API.
func (h *Handler) RegisterRoutes(mux *http.ServeMux) {
	mux.HandleFunc("/", h.root)
	mux.HandleFunc("/status", h.status)
	mux.HandleFunc("/start", h.start)
	mux.HandleFunc("/stop", h.stop)
	mux.HandleFunc("/scan", h.scan)
	mux.HandleFunc("/prob-plex", h.probPlex)
	mux.HandleFunc("/cache", h.cache)
}

func (h *Handler) root(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "text/plain")
	w.WriteHeader(http.StatusOK)
	w.Write([]byte("Server is operational. Use endpoint /start, /stop, /scan, /status, /prob-plex.\n"))
}
