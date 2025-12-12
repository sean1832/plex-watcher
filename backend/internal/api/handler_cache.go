package api

import (
	"encoding/json"
	"log/slog"
	"net/http"
	"os"
	"plexwatcher/internal/response"
	"plexwatcher/internal/types"
)

// cache returns the cached watchlist configuration if it exists
func (h *Handler) cache(w http.ResponseWriter, r *http.Request) {
	if h.cachePath == "" {
		response.WriteError(w, "cache not configured", http.StatusNotFound)
		return
	}

	cacheData, err := os.ReadFile(h.cachePath)
	if os.IsNotExist(err) {
		response.WriteError(w, "no cache found", http.StatusNotFound)
		return
	}
	if err != nil {
		response.WriteError(w, "failed to read cache", http.StatusInternalServerError)
		slog.Error("failed to read cache file", "error", err)
		return
	}

	var cache types.WatchlistCache
	if err := json.Unmarshal(cacheData, &cache); err != nil {
		response.WriteError(w, "invalid cache format", http.StatusInternalServerError)
		slog.Error("failed to unmarshal cache", "error", err)
		return
	}

	response.WriteSuccess(w, "cache retrieved", cache, http.StatusOK)
}
