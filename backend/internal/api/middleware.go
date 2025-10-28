package api

import (
	"log/slog"
	"net/http"
	"plexwatcher/internal/http/response"
)

// WithCORS adds CORS headers to all responses
func WithCORS(next http.Handler, allowedOrigins []string) http.Handler {
	// efficient lookup table, otherwise array is fine
	allowedOriginsMap := make(map[string]bool)
	for _, origin := range allowedOrigins {
		allowedOriginsMap[origin] = true
	}

	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		origin := r.Header.Get("Origin") // <- get the origin from the req

		// handle non-browser requests (empty origin), e.g. curl, postman
		// these don't need CROS header, just pass through

		if origin == "" {
			next.ServeHTTP(w, r)
			return
		}

		if !allowedOriginsMap[origin] && !allowedOriginsMap["*"] { // '*' allows all
			slog.Warn("Origin not allowed", "origin", origin)
			response.WriteError(w, "origin not allowed", http.StatusForbidden)
			return
		}

		w.Header().Set("Access-Control-Allow-Origin", origin)
		w.Header().Add("Vary", "Origin")
		w.Header().Set("Access-Control-Allow-Methods", "GET, POST")
		w.Header().Set("Access-Control-Allow-Headers", "Content-Type, Authorization")

		// Handle preflight requests
		if r.Method == "OPTIONS" {
			w.WriteHeader(http.StatusOK)
			return
		}

		next.ServeHTTP(w, r)
	})
}
