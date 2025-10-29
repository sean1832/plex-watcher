package api

import (
	"context"
	"log/slog"
	"net/http"
	"sync"

	"plexwatcher/internal/services/audiobookshelf"
	"plexwatcher/internal/services/plex"
	"plexwatcher/internal/watcher_manager"
)

type Handler struct {
	Watcher *watcher_manager.Manager
	Context context.Context

	plex              *plex.Scanner
	abs               *audiobookshelf.LibraryManager
	scanSemaphore     chan struct{}   // limit concurrent scans
	activeScansMutex  sync.Mutex      // protect activeScans map
	activeScans       map[string]bool // track paths currently being scanned
	allowedExtensions []string
}

// NewHandler creates a new API handler with the specified concurrency limit for scans.
func NewHandler(ctx context.Context, concurrency int, allowedExtensions []string) *Handler {
	if concurrency <= 0 {
		concurrency = 1 // at least 1
		slog.Warn("concurrency must be at least 1, defaulting to 1")
	}
	return &Handler{
		Watcher:           watcher_manager.NewManager(),
		Context:           ctx,
		scanSemaphore:     make(chan struct{}, concurrency), // limit to specified concurrent scans
		activeScans:       make(map[string]bool),            // initialize deduplication map
		allowedExtensions: allowedExtensions,
	}
}

// RegisterRoutes sets up the HTTP routes for the API.
func (h *Handler) RegisterRoutes(mux *http.ServeMux) {
	mux.HandleFunc("/", h.root)
	mux.HandleFunc("/status", h.status)
	mux.HandleFunc("/start", h.start)
	mux.HandleFunc("/stop", h.stop)
	mux.HandleFunc("/scan", h.scan)
	mux.HandleFunc("/prob-plex", h.probPlex)
	mux.HandleFunc("/prob-abs", h.probAudiobookshelf)
}

func (h *Handler) root(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "text/plain")
	w.WriteHeader(http.StatusOK)
	w.Write([]byte("Server is operational. Use endpoint /start, /stop, /scan, /status, /prob-plex.\n"))
}
