package api

import (
	"encoding/json"
	"log/slog"
	"net/http"
	"path/filepath"
	"plexwatcher/internal/fs_watcher"
	"plexwatcher/internal/http/response"
	"plexwatcher/internal/services/audiobookshelf"
	"plexwatcher/internal/services/plex"
	"plexwatcher/internal/types"
)

// start the watcher with provided configuration
func (h *Handler) start(w http.ResponseWriter, r *http.Request) {
	var req types.RequestStart
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		response.WriteError(w, err.Error(), http.StatusBadRequest)
		slog.Error("failed to decode start request", "error", err)
		return
	}

	// Initialize Plex if configured
	if plexConfig, ok := req.ServiceConfigs[types.ServicePlex]; ok {
		plexClient, err := plex.NewPlexClient(plexConfig.ServerUrl, plexConfig.Token)
		if err != nil {
			response.WriteError(w, err.Error(), http.StatusBadRequest)
			slog.Error("failed to create Plex client", "error", err)
			return
		}
		// initialize scanner
		h.plex, err = plex.NewScanner(h.Context, plexClient)
		if err != nil {
			response.WriteError(w, err.Error(), http.StatusBadRequest)
			slog.Error("failed to create Plex scanner", "error", err)
			return
		}

		// log all root sections
		for _, section := range h.plex.GetAllSections() {
			slog.Info("Plex section",
				"title", section.SectionTitle,
				"type", section.SectionType,
				"path", section.RootPath,
			)
		}
		slog.Info("Plex service initialized", "server", plexConfig.ServerUrl)
	}

	// Initialize Audiobookshelf if configured
	if absConfig, ok := req.ServiceConfigs[types.ServiceAudiobookshelf]; ok {
		absClient, err := audiobookshelf.NewClient(absConfig.ServerUrl, absConfig.Token)
		if err != nil {
			response.WriteError(w, err.Error(), http.StatusBadRequest)
			slog.Error("failed to create Audiobookshelf client", "error", err)
			return
		}
		// initialize lib manager
		h.abs, err = audiobookshelf.NewLibraryManager(h.Context, absClient)
		if err != nil {
			response.WriteError(w, err.Error(), http.StatusBadRequest)
			slog.Error("failed to create Audiobookshelf library manager", "error", err)
			return
		}

		// log all lib
		for _, lib := range h.abs.Libraries {
			slog.Info("audiobookshelf libraries",
				"title", lib.Name,
				"id", lib.Id,
				"paths", lib.Folders,
			)
		}

		slog.Info("audiobookshelf service initialized", "server", absConfig.ServerUrl)
	}

	// start watcher
	h.Watcher.RegisterHandler(types.ServicePlex, h.handlePlexUpdate)
	h.Watcher.RegisterHandler(types.ServiceAudiobookshelf, h.handleAbsUpdate)
	if err := h.Watcher.Start(req); err != nil {
		response.WriteError(w, err.Error(), http.StatusBadRequest)
		slog.Error("failed to start watcher", "error", err)
		return
	}
	slog.Info("watcher started",
		"dirs", req.WatchedDirs,
		"cooldown", req.Cooldown,
	)

	response.WriteSuccess(w, "watcher started", nil, http.StatusOK)
}

func (h *Handler) handleAbsUpdate(e fs_watcher.Event) {
	logger := slog.With("path", e.Path, "service", types.ServiceAudiobookshelf)

	if !validateEventAndExtension(e, h.allowedExtensions, logger) {
		return
	}

	if h.abs == nil {
		logger.Warn("audiobookshelf scanner not initialized, skipping event")
		return
	}

	eventType := getEventType(e.Op)
	targetDir := filepath.ToSlash(filepath.Dir(e.Path))
	logger.Debug("file event detected, queuing scan", "scan_target", targetDir, "event", eventType)

	// Check if this path is already being scanned (deduplication)
	h.activeScansMutex.Lock()
	if h.activeScans[targetDir] {
		h.activeScansMutex.Unlock()
		return
	}
	// Mark this path as being scanned
	h.activeScans[targetDir] = true
	h.activeScansMutex.Unlock()

	// trigger abs scan
	go func(path string) {
		h.scanSemaphore <- struct{}{}        // acquire a token
		defer func() { <-h.scanSemaphore }() // release the token
		if err := h.abs.ScanPath(h.Context, path); err != nil {
			slog.Error("audiobookshelf scan failed", "path", path, "error", err)
		} else {
			slog.Info("audiobookshelf scan succeeded", "path", path)
		}
	}(targetDir)
}

func (h *Handler) handlePlexUpdate(e fs_watcher.Event) {
	logger := slog.With("path", e.Path, "service", types.ServicePlex)

	if !validateEventAndExtension(e, h.allowedExtensions, logger) {
		return
	}

	if h.plex == nil {
		logger.Warn("scanner not initialized, skipping event")
		return
	}

	eventType := getEventType(e.Op)

	// First, map to Plex path to get section info
	_, section := h.plex.MapToPlexPath(e.Path)
	if section == nil {
		logger.Warn("path does not map to any Plex library path, skipping scan")
		return
	}

	// Calculate scan target on LOCAL path first (like Python does)
	// This gets us to the item root (movie folder or show folder)
	localScanTarget := h.plex.GetScanPath(e.Path, section.SectionType)

	// Now map the calculated target to Plex path
	plexScanTarget, mappedSection := h.plex.MapToPlexPath(localScanTarget)
	if mappedSection == nil || plexScanTarget == "" {
		logger.Warn("failed to map scan target to Plex path, skipping scan",
			"local_scan_target", localScanTarget)
		return
	}
	targetDir := filepath.ToSlash(plexScanTarget) // normalize to forward slashes for Plex

	logger.Debug("file event detected, queuing scan", "scan_target", targetDir, "event", eventType)

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

		if section, err := h.plex.ScanPath(h.Context, p); err != nil {
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
