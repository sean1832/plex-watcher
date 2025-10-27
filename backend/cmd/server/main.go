package main

import (
	"context"
	"log/slog"
	"net/http"
	"os"
	"plexwatcher/internal/api"
	"plexwatcher/internal/response"
	"strconv"

	"github.com/lmittmann/tint"
)

// corsMiddleware adds CORS headers to all responses
func corsMiddleware(next http.Handler, allowedOrigins []string) http.Handler {
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

// configureLogger sets up the logger with the specified level
// This can be called multiple times to reconfigure logging
func configureLogger(level slog.Level) {
	handler := tint.NewHandler(os.Stdout, &tint.Options{
		AddSource:  false,
		Level:      level,
		TimeFormat: "2006/01/02 15:04:05", // magic date `2006/01/02 15:04:05`
	})

	logger := slog.New(handler)
	slog.SetDefault(logger)
}

func init() {
	// Bootstrap with INFO level - sufficient to log env parsing
	// Will be reconfigured in main() after reading .env
	configureLogger(slog.LevelInfo)
}

func main() {
	port := 8080

	// Load config from .env (uses bootstrap logger)
	conf := loadEnv(".env")

	// Reconfigure logger with level from .env
	configureLogger(conf.LogLevel)

	slog.Info(
		"Server started",
		"log_level", conf.LogLevel.String(),
		"concurrency", conf.Concurrency,
		"extensions", conf.Extensions,
		"origins", conf.Origins,
	)

	api := api.NewAPI(context.Background(), conf.Concurrency, conf.Extensions)

	mux := http.NewServeMux() // <-- create a new server mux (control the traffic). Request multiplexer
	mux.HandleFunc("/", api.Root)
	mux.HandleFunc("GET /status", api.GetStatus)
	mux.HandleFunc("GET /prob-plex", api.ProbPlex)
	mux.HandleFunc("POST /start", api.Start)
	mux.HandleFunc("POST /stop", api.Stop)
	mux.HandleFunc("POST /scan", api.Scan)

	slog.Info("Server listening", "port", port)
	http.ListenAndServe(":"+strconv.Itoa(port), corsMiddleware(mux, conf.Origins))
}
