package api

import (
	"log/slog"
	"net/http"
	"plexwatcher/internal/http/response"
)

// stop the watcher
func (h *Handler) stop(w http.ResponseWriter, r *http.Request) {
	if err := h.Watcher.Stop(); err != nil {
		response.WriteError(w, err.Error(), http.StatusInternalServerError)
		slog.Error("failed to stop Plex watcher", "error", err)
		return
	}
	slog.Info("plex watcher stopped.")
	response.WriteSuccess(w, "watcher stopped", nil, http.StatusOK)
}
