package main

import (
	"context"
	"log"
	"net/http"
	"plexwatcher/internal/api"
	"plexwatcher/internal/response"
	"strconv"
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
			log.Printf("Origin '%s' not allowed", origin)
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

func main() {
	port := 8080
	conf := loadEnv(".env")
	log.Println("========== SERVER CONFIG ==========")
	log.Printf("ConcurrencyLimit: %d", conf.Concurrency)
	log.Printf("SupportedExtensions: %v", conf.Extensions)
	log.Printf("AllowedOrigins: %v", conf.Origins)
	log.Println("===================================")

	api := api.NewAPI(context.Background(), conf.Concurrency, conf.Extensions)

	mux := http.NewServeMux() // <-- create a new server mux (control the traffic). Request multiplexer
	mux.HandleFunc("/", api.Root)
	mux.HandleFunc("GET /status", api.GetStatus)
	mux.HandleFunc("GET /prob-plex", api.ProbPlex)
	mux.HandleFunc("POST /start", api.Start)
	mux.HandleFunc("POST /stop", api.Stop)
	mux.HandleFunc("POST /scan", api.Scan)

	log.Printf("Server listening to port 0.0.0.0:%v ...\n", port)
	http.ListenAndServe(":"+strconv.Itoa(port), corsMiddleware(mux, conf.Origins))
}
