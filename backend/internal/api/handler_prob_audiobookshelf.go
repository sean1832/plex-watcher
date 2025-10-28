package api

import (
	"context"
	"log/slog"
	"net/http"
	"plexwatcher/internal/http/response"
	"plexwatcher/internal/services/audiobookshelf"
)

func (h *Handler) probAudiobookshelf(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		response.WriteError(w, "method not allowed, expected GET", http.StatusMethodNotAllowed)
		return
	}

	param := r.URL.Query()
	server_url := param.Get("server_url")
	if server_url == "" {
		response.WriteError(w, "missing 'server_url' query parameter", http.StatusBadRequest)
		return
	}

	api_key := param.Get("api_key")
	if api_key == "" {
		response.WriteError(w, "missing 'api_key' query parameter", http.StatusBadRequest)
		return
	}

	c, err := audiobookshelf.NewClient(server_url, api_key)
	if err != nil {
		response.WriteError(w, "failed to create audiobookshelf api client", http.StatusInternalServerError)
		slog.Error("failed to create audiobookshelf api client", "error", err)
		return
	}
	ctx := context.Background()
	libs, status, err := c.ListLibraries(ctx)
	if err != nil {
		response.WriteError(w, "failed to list library", status)
		slog.Error("failed list list audiobookshelf library", "error", err, "http_status", status)
		return
	}

	// successfully retrieved libs
	for _, lib := range libs {
		folders := make([]string, len(lib.Folders))
		for _, folder := range lib.Folders {
			folders = append(folders, folder.FullPath)
		}
		slog.Info("audiobookshelf library", "name", lib.Name, "id", lib.Id, "folders", folders)
	}

	response.WriteSuccess(w, "success hitting audiobookshellf server & retreived libraries", libs, http.StatusOK)
}
