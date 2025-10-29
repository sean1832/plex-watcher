package api

import (
	"encoding/json"
	"log/slog"
	"net/http"
	"path/filepath"
	"plexwatcher/internal/http/response"
	"plexwatcher/internal/services/audiobookshelf"
	"plexwatcher/internal/services/plex"
	"plexwatcher/internal/types"
	"strings"
)

// Manually trigger stateless a scan for specified paths
func (h *Handler) scan(w http.ResponseWriter, r *http.Request) {
	var req types.RequestScan
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		response.WriteError(w, err.Error(), http.StatusBadRequest)
		slog.Error("failed to decode scan request", "error", err)
		return
	}

	// Get Plex config from service_configs
	if plexConfig, ok := req.ServiceConfigs[types.ServicePlex]; ok {
		logger := slog.With("service", types.ServicePlex)
		plexClient, err := plex.NewPlexClient(plexConfig.ServerUrl, plexConfig.Token)
		if err != nil {
			response.WriteError(w, err.Error(), http.StatusBadRequest)
			logger.Error("failed to create Plex client", "error", err)
			return
		}
		scanner, err := plex.NewScanner(h.Context, plexClient)
		if err != nil {
			response.WriteError(w, err.Error(), http.StatusBadRequest)
			logger.Error("failed to create Plex scanner", "error", err)
			return
		}
		handlePlexManualScan(h, scanner, &req, logger)
		response.WriteSuccess(w, "scanned triggered", nil, http.StatusOK)
	}

	if absConfig, ok := req.ServiceConfigs[types.ServiceAudiobookshelf]; ok {
		logger := slog.With("service", types.ServiceAudiobookshelf)
		absConfig, err := audiobookshelf.NewClient(absConfig.ServerUrl, absConfig.Token)
		if err != nil {
			response.WriteError(w, err.Error(), http.StatusBadRequest)
			logger.Error("failed to create audiobookshelf client", "error", err)
			return
		}
		manager, err := audiobookshelf.NewLibraryManager(h.Context, absConfig)
		if err != nil {
			response.WriteError(w, err.Error(), http.StatusBadRequest)
			logger.Error("failed to create audiobookshelf library manager", "error", err)
			return
		}
		handleAbsManualScan(h, manager, &req, logger)
		response.WriteSuccess(w, "scanned triggered", nil, http.StatusOK)
	}
}

func handleAbsManualScan(h *Handler, libManager *audiobookshelf.LibraryManager, req *types.RequestScan, logger *slog.Logger) {
	logger.Info("trigger manual scans", "path_count", len(req.Paths))
	for _, path := range req.Paths {
		targetDir := filepath.ToSlash(filepath.Dir(path))

		go func(path string, manager *audiobookshelf.LibraryManager) {
			h.scanSemaphore <- struct{}{}
			defer func() { <-h.scanSemaphore }()
			if err := manager.ScanPath(h.Context, path); err != nil {
				logger.Error("scan failed", "path", path, "error", err)
			} else {
				logger.Info("scan completed", "path", path)
			}
		}(targetDir, libManager)
	}
}

func handlePlexManualScan(h *Handler, scanner *plex.Scanner, req *types.RequestScan, logger *slog.Logger) {

	logger.Info("triggering manual scans", "path_count", len(req.Paths))

	for _, path := range req.Paths {
		// map to plex path first
		plexPath, section := scanner.MapToPlexPath(path)
		if section == nil {
			logger.Warn("failed to map to any plex library path, skipping scan", "path", path)
			continue
		}

		ext := strings.ToLower(filepath.Ext(path))
		var targetDir string
		if ext == "" {
			// case 1: no extension, assume it is a dir
			// use as is
			targetDir = plexPath
		} else if ensureExtAllowed(path, h.allowedExtensions) {
			// case 2: has an allowed extension. Assume it is a valid file.
			// scan parent directory
			targetDir = filepath.Dir(plexPath)
		} else {
			// case 3: invalid extension. skip.
			logger.Warn("disallowed extension found, skipping scan", "path", path, "extension", ext)
			continue
		}

		targetDir = filepath.ToSlash(targetDir)

		// Trigger scan immediately - no deduplication for manual scans
		go func(p string, s *plex.Scanner) {
			h.scanSemaphore <- struct{}{}        // acquire a token
			defer func() { <-h.scanSemaphore }() // release the token
			if section, err := s.ScanPath(h.Context, p); err != nil {
				logger.Error("scan failed", "path", p, "error", err)
			} else {
				logger.Info("scan completed", "path", p, "section", section.SectionTitle)
			}
		}(targetDir, scanner)
	}
}
