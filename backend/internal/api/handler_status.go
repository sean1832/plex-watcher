package api

import (
	"log/slog"
	"net/http"
	"plexwatcher/internal/http/response"
	"plexwatcher/internal/types"
)

// status returns the current status of the watcher
func (h *Handler) status(w http.ResponseWriter, r *http.Request) {
	running, paths, cooldown := h.Watcher.Status()
	status := "stopped"
	if running {
		status = "running"
	}

	slog.Info(
		"Plex watcher status",
		slog.String("status", status),
		slog.Any("paths", paths),
		slog.Int("cooldown", cooldown),
	)

	var serverURL *string
	if h.plex != nil {
		url := h.plex.GetPlexClient().BaseURL.String()
		serverURL = &url
	}

	resp := types.StatusResponse{
		IsWatching: running,
		Paths:      paths,
		Server:     serverURL,
		Cooldown:   cooldown,
	}
	response.WriteSuccess(w, "success retrieving status", resp, http.StatusOK)
}
