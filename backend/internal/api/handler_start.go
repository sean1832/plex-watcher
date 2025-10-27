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

	response.WriteSuccess(w, "watcher started", nil, http.StatusOK)
}

func (h *Handler) handleDirUpdate(e fs_watcher.Event) {
	logger := slog.With("path", e.Path)

	if e.Err != nil {
		logger.Error("watcher error", "error", e.Err)
		return
	}

	// Filter: only process files with allowed extensions
	// Directories have no extension and are automatically skipped
	ext := strings.ToLower(filepath.Ext(e.Path))
	if ext == "" {
		logger.Debug("skipping directory or extensionless file", "path", e.Path)
		return
	}
	if !ensureExtAllowed(e.Path, h.allowedExtensions) {
		logger.Debug("disallowed extension, skipping event", "extension", ext)
		return
	}

	if h.scanner == nil {
		logger.Warn("scanner not initialized, skipping event")
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
	case e.Op&fsnotify.Chmod == fsnotify.Chmod:
		eventType = "CHMOD"
	default:
		eventType = "UNKNOWN"
	}

	// First, map to Plex path to get section info
	_, section := h.scanner.MapToPlexPath(e.Path)
	if section == nil {
		logger.Warn("path does not map to any Plex library path, skipping scan")
		return
	}

	// Calculate scan target on LOCAL path first (like Python does)
	// This gets us to the item root (movie folder or show folder)
	localScanTarget := h.scanner.GetScanPath(e.Path, section.SectionType)

	// Now map the calculated target to Plex path
	plexScanTarget, mappedSection := h.scanner.MapToPlexPath(localScanTarget)
	if mappedSection == nil || plexScanTarget == "" {
		logger.Warn("failed to map scan target to Plex path, skipping scan",
			"local_scan_target", localScanTarget)
		return
	}
	targetDir := filepath.ToSlash(plexScanTarget) // normalize to forward slashes for Plex

	logger.Info("file event detected, queuing scan", "scan_target", targetDir, "event", eventType)

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
