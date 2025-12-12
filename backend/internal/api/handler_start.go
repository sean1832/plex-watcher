package api

import (
	"encoding/json"
	"log/slog"
	"net/http"
	"os"
	"path/filepath"
	"plexwatcher/internal/fs_watcher"
	"plexwatcher/internal/plex"
	"plexwatcher/internal/response"
	"plexwatcher/internal/types"
	"strings"

	"github.com/fsnotify/fsnotify"
)

// start the watcher with provided configuration
func (h *Handler) start(w http.ResponseWriter, r *http.Request) {
	var req types.RequestStart
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		response.WriteError(w, err.Error(), http.StatusBadRequest)
		slog.Error("failed to decode start request", "error", err)
		return
	}
	plexClient, err := plex.NewPlexClient(req.ServerUrl, req.Token)
	if err != nil {
		response.WriteError(w, err.Error(), http.StatusBadRequest)
		slog.Error("failed to create Plex client", "error", err)
		return
	}
	// initialize scanner
	h.scanner, err = plex.NewScanner(h.Context, plexClient)
	if err != nil {
		response.WriteError(w, err.Error(), http.StatusBadRequest)
		slog.Error("failed to create Plex scanner", "error", err)
		return
	}

	// log all root sections
	for _, section := range h.scanner.GetAllSections() {
		slog.Info("Plex section",
			"title", section.SectionTitle,
			"type", section.SectionType,
			"path", section.RootPath,
		)
	}

	// start watcher
	if err := h.Watcher.Start(req, h.handleDirUpdate); err != nil {
		response.WriteError(w, err.Error(), http.StatusBadRequest)
		slog.Error("failed to start Plex watcher", "error", err)
		return
	}
	slog.Info("plex watcher started.",
		"server", req.ServerUrl,
		"dir", req.Paths,
		"cooldown", req.Cooldown,
	)

	// Save paths/cooldown to cache (no credentials for security)
	if h.cachePath != "" {
		cache := types.WatchlistCache{
			Paths:    req.Paths,
			Cooldown: req.Cooldown,
		}
		cacheData, err := json.MarshalIndent(cache, "", "  ")
		if err != nil {
			slog.Error("JSON marshaling failed; skipping cache", "error", err)
		} else if err := os.WriteFile(h.cachePath, cacheData, 0644); err != nil {
			slog.Error("failed to write cache file", "error", err, "filepath", h.cachePath)
		} else {
			slog.Info("watchlist cached to file", "filepath", h.cachePath)
		}
	}

	response.WriteSuccess(w, "watcher started", nil, http.StatusOK)
}

func (h *Handler) handleDirUpdate(e fs_watcher.Event) {
	logger := slog.With("path", e.Path, "op", e.Op.String())

	if e.Err != nil {
		logger.Error("watcher error", "error", e.Err)
		return
	}

	// Log event type early for debugging
	eventType := getEventType(e.Op)
	logger.Debug("received fs event", "event", eventType)

	// Check if this is a delete/remove event - path won't exist anymore
	isDeleteEvent := e.Op&fsnotify.Remove == fsnotify.Remove

	// For delete events, we can't stat the path - handle separately
	if isDeleteEvent {
		logger.Info("delete event detected, queuing scan", "event", eventType)
		h.handleDeleteEvent(e, logger)
		return
	}

	// For non-delete events, stat the path to check if it exists and get info
	info, err := os.Stat(e.Path)
	if os.IsNotExist(err) {
		// Path doesn't exist - this can happen with RENAME events on the old path
		// Treat it like a delete event (the item was moved/renamed away)
		logger.Info("path no longer exists, treating as delete event", "event", eventType)
		h.handleDeleteEvent(e, logger)
		return
	}
	if err != nil {
		logger.Error("failed to stat path, skipping", "error", err)
		return
	}

	// directory vs file
	isDirectory := info.IsDir()
	if isDirectory {
		if e.Op&fsnotify.Create == fsnotify.Create || e.Op&fsnotify.Rename == fsnotify.Rename {
			logger.Info("directory change detected, queuing scan", "event", eventType)
			// proceed to scan logic below
		} else {
			logger.Debug("skipping non-creation directory event", "event", eventType)
			return
		}
	} else {
		ext := strings.ToLower(filepath.Ext(e.Path))
		if ext == "" {
			logger.Debug("file has no extension, skipping", "event", eventType)
			return
		}
		if !ensureExtAllowed(e.Path, h.allowedExtensions) {
			logger.Debug("file extension not allowed, skipping", "extension", ext, "event", eventType)
			return
		}
	}

	if h.scanner == nil {
		logger.Warn("scanner not initialized, skipping event")
		return
	}

	// First, map to Plex path to get section info
	_, section := h.scanner.MapToPlexPath(e.Path)
	if section == nil {
		logger.Warn("path does not map to any Plex library path, skipping scan")
		return
	}

	var localScanTarget string
	if isDirectory {
		// For directory events (e.g., cut/paste of a folder), scan the directory itself
		// Don't call GetScanPath which would navigate up the path hierarchy
		localScanTarget = e.Path
		logger.Debug("directory event: using path directly as scan target", "localScanTarget", localScanTarget)
	} else {
		// For file events, calculate scan target to get to item root (movie folder or show folder)
		localScanTarget = h.scanner.GetScanPath(e.Path, section.SectionType)
		logger.Debug("file event: calculated scan target", "localScanTarget", localScanTarget)
	}

	h.triggerScan(localScanTarget, eventType, logger)
}

// handleDeleteEvent handles delete/remove events where the path no longer exists
func (h *Handler) handleDeleteEvent(e fs_watcher.Event, logger *slog.Logger) {
	if h.scanner == nil {
		logger.Warn("scanner not initialized, skipping event")
		return
	}

	// For deleted paths, we can't stat to determine if it was a file or directory
	_, section := h.scanner.MapToPlexPath(e.Path)
	if section == nil {
		logger.Warn("path does not map to any Plex library path, skipping scan")
		return
	}

	// For delete events, we want to scan the exact path that was deleted
	// This tells Plex to refresh that specific location and remove the deleted item
	// We use the path directly, not GetScanPath which would navigate to parent
	localScanTarget := e.Path
	logger.Debug("delete event: using deleted path as scan target", "localScanTarget", localScanTarget)

	h.triggerScan(localScanTarget, "REMOVE", logger)
}

// triggerScan maps a local path to Plex path and triggers the scan
func (h *Handler) triggerScan(localScanTarget string, eventType string, logger *slog.Logger) {
	// Map the target to Plex path
	plexScanTarget, mappedSection := h.scanner.MapToPlexPath(localScanTarget)
	logger.Debug("mapped to plex path", "localScanTarget", localScanTarget, "plexScanTarget", plexScanTarget)
	if mappedSection == nil || plexScanTarget == "" {
		logger.Warn("failed to map scan target to Plex path, skipping scan",
			"local_scan_target", localScanTarget)
		return
	}
	targetDir := filepath.ToSlash(plexScanTarget) // normalize to forward slashes for Plex

	logger.Info("queuing scan", "scan_target", targetDir, "event", eventType)

	// Check if this path is already being scanned (deduplication)
	h.activeScansMutex.Lock()
	if h.activeScans[targetDir] {
		h.activeScansMutex.Unlock()
		return
	}
	// Mark this path as being scanned
	h.activeScans[targetDir] = true
	h.activeScansMutex.Unlock()

	// trigger plex scan
	go func(p string) {
		h.scanSemaphore <- struct{}{} // acquire a token
		defer func() {
			<-h.scanSemaphore // release the token

			// recover from any panic in ScanPath to avoid leaving activeScans locked
			if r := recover(); r != nil {
				slog.Error("panic during ScanPath", "scan_target", p, "panic", r)
			}

			// Ensure we remove from active scans map
			h.activeScansMutex.Lock()
			delete(h.activeScans, p)
			h.activeScansMutex.Unlock()
		}()

		section, err := h.scanner.ScanPath(h.Context, p)
		if err != nil {
			slog.Error("scan failed", "scan_target", p, "error", err)
		} else {
			slog.Info("scan triggered", "scan_target", p, "section", section.SectionTitle)
		}
	}(targetDir)
}
