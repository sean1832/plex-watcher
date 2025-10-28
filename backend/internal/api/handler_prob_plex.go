package api

import (
	"log"
	"log/slog"
	"net/http"
	"plexwatcher/internal/http/response"
	"plexwatcher/internal/services/plex"
)

func (h *Handler) probPlex(w http.ResponseWriter, r *http.Request) {
	// list plex sections
	if r.Method != http.MethodGet {
		response.WriteError(w, "method not allowed, expected GET", http.StatusMethodNotAllowed)
		return
	}

	// get URL query param
	params := r.URL.Query()
	serverUrl := params.Get("server_url")
	if serverUrl == "" {
		response.WriteError(w, "missing 'server_url' query parameter", http.StatusBadRequest)
		log.Println("missing 'server_url' query parameter")
		return
	}

	token := params.Get("token")
	if token == "" {
		response.WriteError(w, "missing 'token' query parameter", http.StatusBadRequest)
		log.Println("missing 'token' query parameter")
		return
	}

	// create plex client
	plexClient, err := plex.NewPlexClient(serverUrl, token)
	if err != nil {
		response.WriteError(w, err.Error(), http.StatusBadRequest)
		slog.Error("failed to create PlexClient", "error", err)
		return
	}
	scanner, err := plex.NewScanner(h.Context, plexClient)
	if err != nil {
		response.WriteError(w, err.Error(), http.StatusBadRequest)
		slog.Error("failed to create PlexScanner", "error", err)
		return
	}

	sections := scanner.GetAllSections()

	slog.Info("plex server library section detected", "server", serverUrl, "sections", len(sections))

	response.WriteSuccess(w, "success hitting plex server & retreived library sections", sections, http.StatusOK)
}
