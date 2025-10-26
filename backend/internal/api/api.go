package api

import (
	"context"
	"encoding/json"
	"log"
	"net/http"
	"path/filepath"
	"strings"
	"sync"

	"plexwatcher/internal/fs_watcher"
	"plexwatcher/internal/plex"
	"plexwatcher/internal/response"
	"plexwatcher/internal/types"
	"plexwatcher/internal/watcher_manager"

	"github.com/fsnotify/fsnotify"
)

type api struct {
	Watcher *watcher_manager.Manager
	Context context.Context

	scanner           *plex.Scanner
	scanSemaphore     chan struct{}   // limit concurrent scans
	activeScansMutex  sync.Mutex      // protect activeScans map
	activeScans       map[string]bool // track paths currently being scanned
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
		activeScans:       make(map[string]bool),            // initialize deduplication map
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
	running, paths, cooldown := api.Watcher.Status()
	status := "stopped"
	if running {
		status = "running"
	}
	log.Printf("Plex watcher status: %s, paths: %v, cooldown: %ds", status, paths, cooldown)

	var serverURL *string
	if api.scanner != nil {
		url := api.scanner.GetPlexClient().BaseURL.String()
		serverURL = &url
	}

	resp := types.StatusResponse{
		IsWatching: running,
		Paths:      paths,
		Server:     serverURL,
		Cooldown:   cooldown,
	}
	response.WriteSuccess(w, "success retrieving status", resp, http.StatusOK)
}

func (api *api) ProbPlex(w http.ResponseWriter, r *http.Request) {
	// list plex sections
	if r.Method != http.MethodGet {
		response.WriteError(w, "method not allowed, expected GET", http.StatusMethodNotAllowed)
		return
	}

	// get URL query param
	params := r.URL.Query()
	serverUrl := params.Get("server_url")
	if serverUrl == "" {
		response.WriteError(w, "missing 'server_url' query parameter", http.StatusBadRequest)
		log.Println("missing 'server_url' query parameter")
		return
	}

	token := params.Get("token")
	if token == "" {
		response.WriteError(w, "missing 'token' query parameter", http.StatusBadRequest)
		log.Println("missing 'token' query parameter")
		return
	}

	// create plex client
	plexClient, err := plex.NewPlexClient(serverUrl, token)
	if err != nil {
		response.WriteError(w, err.Error(), http.StatusBadRequest)
		log.Printf("failed to create Plex client: %v", err)
		return
	}
	scanner, err := plex.NewScanner(api.Context, plexClient)
	if err != nil {
		response.WriteError(w, err.Error(), http.StatusBadRequest)
		log.Printf("failed to create Plex scanner: %v", err)
		return
	}

	sections := scanner.GetAllSections()

	log.Printf("Plex server at %s has %d library sections", serverUrl, len(sections))

	response.WriteSuccess(w, "success hitting plex server & retreived library sections", sections, http.StatusOK)
}

// Start the watcher with provided configuration
func (api *api) Start(w http.ResponseWriter, r *http.Request) {
	var req types.RequestStart
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		response.WriteError(w, err.Error(), http.StatusBadRequest)
		log.Printf("failed to decode start request: %v", err)
		return
	}
	plexClient, err := plex.NewPlexClient(req.ServerUrl, req.Token)
	if err != nil {
		response.WriteError(w, err.Error(), http.StatusBadRequest)
		log.Printf("failed to create Plex client: %v", err)
		return
	}
	// initialize scanner
	api.scanner, err = plex.NewScanner(api.Context, plexClient)
	if err != nil {
		response.WriteError(w, err.Error(), http.StatusBadRequest)
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
		response.WriteError(w, err.Error(), http.StatusBadRequest)
		log.Printf("failed to start Plex watcher: %v", err)
		return
	}

	log.Printf("Plex watcher started. [dirs=%v, cooldown=%ds]", req.Paths, req.Cooldown)

	response.WriteSuccess(w, "watcher started", nil, http.StatusOK)
}

// Stop the watcher
func (api *api) Stop(w http.ResponseWriter, r *http.Request) {
	if err := api.Watcher.Stop(); err != nil {
		response.WriteError(w, err.Error(), http.StatusInternalServerError)
		log.Printf("failed to stop Plex watcher: %v", err)
		return
	}
	log.Println("Plex watcher stopped.")
	response.WriteSuccess(w, "watcher stopped", nil, http.StatusOK)
}

// Manually trigger stateless a scan for specified paths
func (api *api) Scan(w http.ResponseWriter, r *http.Request) {
	var req types.RequestScan
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		response.WriteError(w, err.Error(), http.StatusBadRequest)
		log.Printf("failed to decode scan request: %v", err)
		return
	}
	plexClient, err := plex.NewPlexClient(req.ServerUrl, req.Token)
	if err != nil {
		response.WriteError(w, err.Error(), http.StatusBadRequest)
		log.Printf("failed to create Plex client: %v", err)
		return
	}
	scanner, err := plex.NewScanner(api.Context, plexClient)
	if err != nil {
		response.WriteError(w, err.Error(), http.StatusBadRequest)
		log.Printf("failed to create Plex scanner: %v", err)
		return
	}
	// trigger scans for each path
	uniquePaths := make(map[string]bool) // deduplicate scan paths
	scanPaths := []string{}

	for _, path := range req.Paths {

		// map to plex path first
		plexPath, _, ok := scanner.MapToPlexPath(path)
		if !ok {
			log.Printf("path %s does not map to any Plex library path, skipping scan", path)
			continue
		}

		ext := strings.ToLower(filepath.Ext(path))
		var targetDir string
		if ext == "" {
			// case 1: no extension, assume it is a dir
			// use as is
			targetDir = plexPath
		} else if ensureExtAllowed(path, api.allowedExtensions) {
			// case 2: has an allowed extension. Assume it is a valid file.
			// scan parent directory
			targetDir = filepath.Dir(plexPath)
		} else {
			// case 3: invalid extension. skip.
			log.Printf("file path %s has disallowed extension %s, skipping scan", path, ext)
			continue
		}

		targetDir = filepath.ToSlash(targetDir)

		// Deduplicate: only add if not already in the map
		if !uniquePaths[targetDir] {
			uniquePaths[targetDir] = true
			scanPaths = append(scanPaths, targetDir)
		} else {
			log.Printf("duplicate scan path detected and skipped: %s", targetDir)
		}
	}

	log.Printf("triggering scans for %d unique paths (from %d requested)", len(scanPaths), len(req.Paths))

	// Now trigger scans for unique paths
	for _, targetDir := range scanPaths {
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
	response.WriteSuccess(w, "scanned triggered", nil, http.StatusOK)
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
		//log.Printf("skipping event for path with invalid extension: %s", e.Path)
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

	// Check if this path is already being scanned (deduplication)
	api.activeScansMutex.Lock()
	if api.activeScans[targetDir] {
		//log.Printf("scan already in progress for %s, skipping duplicate", targetDir)
		api.activeScansMutex.Unlock()
		return
	}
	// Mark this path as being scanned
	api.activeScans[targetDir] = true
	api.activeScansMutex.Unlock()

	// trigger plex scan
	go func(p string) {
		api.scanSemaphore <- struct{}{}        // acquire a token
		defer func() { <-api.scanSemaphore }() // release the token

		if section, err := api.scanner.ScanPath(api.Context, p); err != nil {
			log.Printf("failed to scan path %s: %v", p, err)
		} else {
			log.Printf("scan triggered for '%s': %s", section.SectionTitle, p)
		}

		// Remove from active scans when done
		api.activeScansMutex.Lock()
		delete(api.activeScans, p)
		api.activeScansMutex.Unlock()
	}(targetDir)
}

// ===================
// Helper functions
// ===================

func ensureExtAllowed(path string, allowedExts []string) bool {
	ext := strings.ToLower(filepath.Ext(path))
	for _, allowExt := range allowedExts {
		if ext == allowExt {
			return true
		}
	}
	return false
}
