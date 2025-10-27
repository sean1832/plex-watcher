package api

import (
	"path/filepath"
	"strings"
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
