package api

import (
	"encoding/json"
	"log/slog"
	"net/http"
	"path/filepath"
	"plexwatcher/internal/fs_watcher"
	"plexwatcher/internal/plex"
	"plexwatcher/internal/response"
	"plexwatcher/internal/types"
	"strings"

	"github.com/fsnotify/fsnotify"
)

// Start the watcher with provided configuration
func (h *Handler) Start(w http.ResponseWriter, r *http.Request) {
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

	response.WriteSuccess(w, "watcher started", nil, http.StatusOK)
}

func (h *Handler) handleDirUpdate(e fs_watcher.Event) {
	logger := slog.With("path", e.Path)

	if e.Err != nil {
		logger.Error("watcher error", "error", e.Err)
		return
	}

	// Filter: only process paths with allowed extensions (skips .txt, .nfo, etc.)
	// This automatically filters directories since they have no extension
	ext := strings.ToLower(filepath.Ext(e.Path))
	if ext == "" || !ensureExtAllowed(e.Path, h.allowedExtensions) {
		logger.Debug("invalid extension, skipping event")
		return
	}

	if h.scanner == nil {
		logger.Warn("scanner not initialized, skipping event")
		return
	}

	// ignore CHMOD events (no content change)
	if e.Op&fsnotify.Chmod == fsnotify.Chmod {
		logger.Debug("file event ignored.", "event", "CHMOD")
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

	plexPath, section := h.scanner.MapToPlexPath(e.Path)
	if section == nil {
		logger.Warn("path does not map to any Plex library path, skipping scan")
		return
	}

	var targetDir string
	if section.SectionType == types.MediaTypeShow {
		// if show; skip `season x` folder.
		// show is structured as `title/season x/s01e01.mkv`
		targetDir = filepath.Dir(filepath.Dir(plexPath))
		logger.Debug("Path identified as show.", "scan_target", targetDir)
	} else {
		targetDir = filepath.Dir(plexPath) // scan the parent directory
		logger.Debug("Path identified as movie.", "scan_target", targetDir)
	}

	targetDir = filepath.ToSlash(targetDir) // normalize to forward slashes for Plex

	logger.Info("file event accepted, queuing scan", "scan_target", targetDir, "event", eventType)

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
		h.scanSemaphore <- struct{}{}        // acquire a token
		defer func() { <-h.scanSemaphore }() // release the token

		if section, err := h.scanner.ScanPath(h.Context, p); err != nil {
			slog.Error("scan failed", "scan_target", targetDir, "error", err)
		} else {
			slog.Info("scan triggered", "scan_target", targetDir, "section", section.SectionTitle)
		}

		// Remove from active scans when done
		h.activeScansMutex.Lock()
		delete(h.activeScans, p)
		h.activeScansMutex.Unlock()
	}(targetDir)
}
