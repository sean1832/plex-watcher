package api

import (
	"encoding/json"
	"log/slog"
	"net/http"
	"path/filepath"
	"plexwatcher/internal/http/response"
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
	plexClient, err := plex.NewPlexClient(req.ServerUrl, req.Token)
	if err != nil {
		response.WriteError(w, err.Error(), http.StatusBadRequest)
		slog.Error("failed to create Plex client", "error", err)
		return
	}
	scanner, err := plex.NewScanner(h.Context, plexClient)
	if err != nil {
		response.WriteError(w, err.Error(), http.StatusBadRequest)
		slog.Error("failed to create Plex scanner", "error", err)
		return
	}
	// trigger scans for each path
	uniquePaths := make(map[string]bool) // deduplicate scan paths
	scanPaths := []string{}

	for _, path := range req.Paths {

		// map to plex path first
		plexPath, section := scanner.MapToPlexPath(path)
		if section == nil {
			slog.Warn("failed to map to any plex library path, skipping scan", "path", path)
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
			slog.Warn("disallowed extension found, skipping scan", "path", path, "extension", ext)
			continue
		}

		targetDir = filepath.ToSlash(targetDir)

		// Deduplicate: only add if not already in the map
		if !uniquePaths[targetDir] {
			uniquePaths[targetDir] = true
			scanPaths = append(scanPaths, targetDir)
		} else {
			slog.Debug("duplicate scan path detected and skipped", "path", targetDir)
		}
	}

	slog.Info("triggering scans for unique paths", "unique", len(scanPaths), "requested", len(req.Paths))

	// Now trigger scans for unique paths
	for _, targetDir := range scanPaths {
		go func(p string, s *plex.Scanner) {
			h.scanSemaphore <- struct{}{}        // acquire a token
			defer func() { <-h.scanSemaphore }() // release the token
			if section, err := s.ScanPath(h.Context, p); err != nil {
				slog.Error("scan failed", "path", p, "error", err)
			} else {
				slog.Info("scan completed", "path", p, "section", section.SectionTitle)
			}
		}(targetDir, scanner)
	}
	response.WriteSuccess(w, "scanned triggered", nil, http.StatusOK)
}
