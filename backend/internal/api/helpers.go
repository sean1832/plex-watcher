package api

import (
	"log/slog"
	"path/filepath"
	"plexwatcher/internal/fs_watcher"
	"strings"

	"github.com/fsnotify/fsnotify"
)

func ensureExtAllowed(path string, allowedExts []string) bool {
	ext := strings.ToLower(filepath.Ext(path))
	for _, allowExt := range allowedExts {
		if ext == allowExt {
			return true
		}
	}
	return false
}

// validateEventAndExtension performs common validation for filesystem events
// Returns true if the event should be processed, false if it should be skipped
func validateEventAndExtension(e fs_watcher.Event, allowedExts []string, logger *slog.Logger) bool {
	if e.Err != nil {
		logger.Error("watcher error", "error", e.Err)
		return false
	}

	// Filter: only process files with allowed extensions
	// Directories have no extension and are automatically skipped
	ext := strings.ToLower(filepath.Ext(e.Path))
	if ext == "" {
		logger.Debug("skipping directory or extensionless file", "path", e.Path)
		return false
	}
	if !ensureExtAllowed(e.Path, allowedExts) {
		logger.Debug("disallowed extension, skipping event", "extension", ext)
		return false
	}

	return true
}

// getEventType returns a string representation of the fsnotify operation
func getEventType(op fsnotify.Op) string {
	switch {
	case op&fsnotify.Create == fsnotify.Create:
		return "CREATE"
	case op&fsnotify.Write == fsnotify.Write:
		return "WRITE"
	case op&fsnotify.Remove == fsnotify.Remove:
		return "REMOVE"
	case op&fsnotify.Rename == fsnotify.Rename:
		return "RENAME"
	case op&fsnotify.Chmod == fsnotify.Chmod:
		return "CHMOD"
	default:
		return "UNKNOWN"
	}
}
