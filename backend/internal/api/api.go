package api

import (
	"context"
	"encoding/json"
	"log"
	"net/http"
	"path/filepath"
	"strings"

	"plex-watcher-backend/internal/fs_watcher"
	"plex-watcher-backend/internal/plex"
	"plex-watcher-backend/internal/requests"
	"plex-watcher-backend/internal/watcher_manager"

	"github.com/fsnotify/fsnotify"
)

type api struct {
	Watcher *watcher_manager.Manager
	Context context.Context

	scanner           *plex.Scanner
	scanSemaphore     chan struct{} // limit concurrent scans
	allowedExtensions []string
}

// NewAPI creates a new API instance with the specified concurrency limit for scans.
func NewAPI(ctx context.Context, concurrency int, allowedExtensions []string) *api {
	if concurrency <= 0 {
		concurrency = 1 // at least 1
		log.Printf("concurrency must be at least 1, defaulting to 1")
	}
	return &api{
		Watcher:           watcher_manager.NewManager(),
		Context:           ctx,
		scanSemaphore:     make(chan struct{}, concurrency), // limit to specified concurrent scans
		allowedExtensions: allowedExtensions,
	}
}

func (api *api) Root(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	w.Write([]byte(`{"status": "ok", "message": "Plex Watcher API is running"}`))
}

// GetStatus returns the current status of the watcher
func (api *api) GetStatus(w http.ResponseWriter, r *http.Request) {
	running := api.Watcher.Status()
	status := "stopped"
	if running {
		status = "running"
	}
	log.Printf("Plex watcher status: %s", status)
	writeJSON(w, http.StatusOK, map[string]string{
		"status": status,
	})
}

func (api *api) ProbPlex(w http.ResponseWriter, r *http.Request) {
	// list plex sections
	if r.Body == nil {
		http.Error(w, "missing request body", http.StatusBadRequest)
		log.Println("missing request body")
		return
	}
	var req requests.ListSectionsRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		log.Printf("failed to decode list sections request: %v", err)
		return
	}

	// create plex client
	plexClient, err := plex.NewPlexClient(req.ServerUrl, req.Token)
	if err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		log.Printf("failed to create Plex client: %v", err)
		return
	}
	scanner, err := plex.NewScanner(api.Context, plexClient)
	if err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		log.Printf("failed to create Plex scanner: %v", err)
		return
	}

	sections := scanner.GetAllSections()

	log.Printf("Plex server at %s has %d library sections", req.ServerUrl, len(sections))

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	json.NewEncoder(w).Encode(map[string]interface{}{
		"status":   "ok",
		"sections": sections,
	})
}

// Start the watcher with provided configuration
func (api *api) Start(w http.ResponseWriter, r *http.Request) {
	var req requests.StartRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		log.Printf("failed to decode start request: %v", err)
		return
	}
	plexClient, err := plex.NewPlexClient(req.ServerUrl, req.Token)
	if err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		log.Printf("failed to create Plex client: %v", err)
		return
	}
	// initialize scanner
	api.scanner, err = plex.NewScanner(api.Context, plexClient)
	if err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		log.Printf("failed to create Plex scanner: %v", err)
		return
	}

	// log all root sections
	log.Println("============== Plex Library Sections ==============")
	for _, section := range api.scanner.GetAllSections() {
		log.Printf("Plex section: '%s' (%s) at %s",
			section.SectionTitle, section.SectionType, section.RootPath)
	}
	log.Println("===================================================")

	// start watcher
	if err := api.Watcher.Start(req, api.handleDirUpdate); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		log.Printf("failed to start Plex watcher: %v", err)
		return
	}

	log.Printf("Plex watcher started. [dirs=%v, cooldown=%ds]", req.Paths, req.Cooldown)

	writeJSON(w, http.StatusOK, map[string]string{
		"status": "started",
	})
}

// Stop the watcher
func (api *api) Stop(w http.ResponseWriter, r *http.Request) {
	if err := api.Watcher.Stop(); err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		log.Printf("failed to stop Plex watcher: %v", err)
		return
	}
	log.Println("Plex watcher stopped.")
	writeJSON(w, http.StatusOK, map[string]string{
		"status": "stopped",
	})
}

// Manually trigger stateless a scan for specified paths
func (api *api) Scan(w http.ResponseWriter, r *http.Request) {
	var req requests.ScanRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		log.Printf("failed to decode scan request: %v", err)
		return
	}
	plexClient, err := plex.NewPlexClient(req.ServerUrl, req.Token)
	if err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		log.Printf("failed to create Plex client: %v", err)
		return
	}
	scanner, err := plex.NewScanner(api.Context, plexClient)
	if err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		log.Printf("failed to create Plex scanner: %v", err)
		return
	}
	// trigger scans for each path
	for _, path := range req.Paths {
		// Filter: only process paths with allowed extensions
		ext := strings.ToLower(filepath.Ext(path))
		if ext == "" || !ensureExtAllowed(path, api.allowedExtensions) {
			continue
		}

		plexPath, _, ok := scanner.MapToPlexPath(path)
		if !ok {
			log.Printf("path %s does not map to any Plex library path, skipping scan", path)
			continue
		}
		targetDir := filepath.Dir(plexPath)     // scan the parent directory
		targetDir = filepath.ToSlash(targetDir) // normalize to forward slashes for Plex

		go func(p string, s *plex.Scanner) {
			api.scanSemaphore <- struct{}{}        // acquire a token
			defer func() { <-api.scanSemaphore }() // release the token
			if section, err := s.ScanPath(api.Context, p); err != nil {
				log.Printf("scan failed for %s: %v", p, err)
			} else {
				log.Printf("scan completed for '%s': %s", section.SectionTitle, p)
			}
		}(targetDir, scanner)
	}
	writeJSON(w, http.StatusOK, map[string]string{
		"status": "scan triggered",
	})
}

// ====================
// plex-watcher action
// ====================

func (api *api) handleDirUpdate(e fs_watcher.Event) {
	if e.Err != nil {
		log.Printf("watcher error: %v", e.Err)
		return
	}

	// Filter: only process paths with allowed extensions (skips .txt, .nfo, etc.)
	// This automatically filters directories since they have no extension
	ext := strings.ToLower(filepath.Ext(e.Path))
	if ext == "" || !ensureExtAllowed(e.Path, api.allowedExtensions) {
		log.Printf("skipping event for path with invalid extension: %s", e.Path)
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
	targetDir := filepath.Dir(plexPath)     // scan the parent directory
	targetDir = filepath.ToSlash(targetDir) // normalize to forward slashes for Plex

	log.Printf("[%s] %s", eventType, targetDir)

	// trigger plex scan
	go func(p string) {
		api.scanSemaphore <- struct{}{}        // acquire a token
		defer func() { <-api.scanSemaphore }() // release the token

		if section, err := api.scanner.ScanPath(api.Context, p); err != nil {
			log.Printf("failed to scan path %s: %v", p, err)
		} else {
			log.Printf("scan triggered for '%s': %s", section.SectionTitle, p)
		}
	}(targetDir)
}

// ===================
// Helper functions
// ===================

func writeJSON(writer http.ResponseWriter, code int, data map[string]string) {
	writer.Header().Set("Content-Type", "application/json")
	writer.WriteHeader(code)
	json.NewEncoder(writer).Encode(data)
}

func ensureExtAllowed(path string, allowedExts []string) bool {
	ext := strings.ToLower(filepath.Ext(path))
	for _, allowExt := range allowedExts {
		if ext == allowExt {
			return true
		}
	}
	return false
}
