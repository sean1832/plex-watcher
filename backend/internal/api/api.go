package api

import (
	"context"
	"encoding/json"
	"log"
	"net/http"

	"plex-watcher-backend/internal/fs_watcher"
	"plex-watcher-backend/internal/plex"
	"plex-watcher-backend/internal/requests"
	"plex-watcher-backend/internal/watcher_manager"

	"github.com/fsnotify/fsnotify"
)

type API struct {
	Watcher *watcher_manager.Manager
	Context context.Context

	scanner       *plex.Scanner
	scanSemaphore chan struct{} // limit concurrent scans
}

// NewAPI creates a new API instance with the specified concurrency limit for scans.
func NewAPI(ctx context.Context, concurrency int) *API {
	return &API{
		Watcher:       watcher_manager.NewManager(),
		Context:       ctx,
		scanSemaphore: make(chan struct{}, concurrency), // limit to specified concurrent scans
	}
}

func (api *API) Root(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	w.Write([]byte(`{"status": "ok", "message": "Plex Watcher API is running"}`))
}

// GetStatus returns the current status of the watcher
func (api *API) GetStatus(w http.ResponseWriter, r *http.Request) {
	running := api.Watcher.Status()
	status := "stopped"
	if running {
		status = "running"
	}
	writeJSON(w, http.StatusOK, map[string]string{
		"status": status,
	})
}

func (api *API) ProbPlex(w http.ResponseWriter, r *http.Request) {
	// list plex sections
	if r.Body == nil {
		http.Error(w, "missing request body", http.StatusBadRequest)
		return
	}
	var req requests.ListSectionsRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}

	// create plex client
	plexClient, err := plex.NewPlexClient(req.ServerUrl, req.Token)
	if err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}
	scanner, err := plex.NewScanner(api.Context, plexClient)
	if err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}

	sections := scanner.GetAllSections()

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	json.NewEncoder(w).Encode(map[string]interface{}{
		"status":   "ok",
		"sections": sections,
	})
}

// Start the watcher with provided configuration
func (api *API) Start(w http.ResponseWriter, r *http.Request) {
	var req requests.StartRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}
	plexClient, err := plex.NewPlexClient(req.ServerUrl, req.Token)
	if err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}
	// initialize scanner
	api.scanner, err = plex.NewScanner(api.Context, plexClient)
	if err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}

	// start watcher
	if err := api.Watcher.Start(req, api.handleDirUpdate); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}

	writeJSON(w, http.StatusOK, map[string]string{
		"status": "started",
	})
}

// Stop the watcher
func (api *API) Stop(w http.ResponseWriter, r *http.Request) {
	if err := api.Watcher.Stop(); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}
	writeJSON(w, http.StatusOK, map[string]string{
		"status": "stopped",
	})
}

// Manually trigger stateless a scan for specified paths
func (api *API) Scan(w http.ResponseWriter, r *http.Request) {
	var req requests.ScanRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}
	plexClient, err := plex.NewPlexClient(req.ServerUrl, req.Token)
	if err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}
	scanner, err := plex.NewScanner(api.Context, plexClient)
	if err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}
	// trigger scans for each path
	for _, path := range req.Paths {
		plexPath, _, ok := scanner.MapToPlexPath(path)
		if !ok {
			log.Printf("path %s does not map to any Plex library path, skipping scan", path)
			continue
		}

		go func(p string, s *plex.Scanner) {
			api.scanSemaphore <- struct{}{}        // acquire a token
			defer func() { <-api.scanSemaphore }() // release the token
			if err := s.ScanPath(api.Context, p); err != nil {
				log.Printf("scan failed for %s: %v", p, err)
			} else {
				log.Printf("scan completed for %s", p)
			}
		}(plexPath, scanner)
	}
	writeJSON(w, http.StatusOK, map[string]string{
		"status": "scan triggered",
	})
}

// ====================
// plex-watcher action
// ====================

func (api *API) handleDirUpdate(e fs_watcher.Event) {
	if e.Err != nil {
		log.Printf("watcher error: %v", e.Err)
		return
	}

	if api.scanner == nil {
		log.Printf("scanner not initialized, skipping event for %s", e.Path)
		return
	}

	// ignore CHMOD events (no content change)
	if e.Op&fsnotify.Chmod == fsnotify.Chmod {
		log.Printf("[CHMOD] %s (ignored)", e.Path)
		return
	}

	// log event type
	var eventType string
	switch {
	case e.Op&fsnotify.Create == fsnotify.Create:
		eventType = "CREATE"
	case e.Op&fsnotify.Write == fsnotify.Write:
		eventType = "WRITE"
	case e.Op&fsnotify.Remove == fsnotify.Remove:
		eventType = "REMOVE"
	case e.Op&fsnotify.Rename == fsnotify.Rename:
		eventType = "RENAME"
	default:
		eventType = "UNKNOWN"
	}

	plexPath, _, ok := api.scanner.MapToPlexPath(e.Path)
	if !ok {
		log.Printf("path %s does not map to any Plex library path, skipping scan", e.Path)
		return
	}

	log.Printf("[%s] %s", eventType, plexPath)

	// trigger plex scan
	go func(path string) {
		api.scanSemaphore <- struct{}{}        // acquire a token
		defer func() { <-api.scanSemaphore }() // release the token

		if err := api.scanner.ScanPath(api.Context, plexPath); err != nil {
			log.Printf("failed to scan path %s: %v", plexPath, err)
		} else {
			log.Printf("scan triggered for path: %s", plexPath)
		}
	}(e.Path)
}

// ===================
// Helper functions
// ===================

func writeJSON(writer http.ResponseWriter, code int, data map[string]string) {
	writer.Header().Set("Content-Type", "application/json")
	writer.WriteHeader(code)
	json.NewEncoder(writer).Encode(data)
}
