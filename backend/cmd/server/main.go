package main

import (
	"log"
	"net/http"
)

type StartRequest struct {
	ServerUrl string   `json:"server_url"`
	Token     string   `json:"token"`
	Paths     []string `json:"paths"`
	Cooldown  int      `json:"cooldown"`
}

type ScanRequest struct {
	ServerUrl string   `json:"server_url"`
	Token     string   `json:"token"`
	Paths     []string `json:"paths"`
}

// TODO: implement middleware CORS

func main() {
	var port int = 8000

	mux := http.NewServeMux() // <-- create a new server mux (control the traffic). Request multiplexer
	mux.HandleFunc("GET /status", handleGetStatus)
	mux.HandleFunc("GET /prob-plex", handleProbPlex)
	mux.HandleFunc("POST /start", handleStartWatching)
	mux.HandleFunc("POST /stop", handleStopWatching)
	mux.HandleFunc("POST /scan", handleScan)

	log.Printf("Server listening to port %v...\n", port)
	http.ListenAndServe(":8000", mux)
}

func handleGetStatus(w http.ResponseWriter, r *http.Request) {
	// TODO: implement status endpoint
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	w.Write([]byte(`{"status": "ok", "message": "Not implemented yet"}`))
}

func handleProbPlex(w http.ResponseWriter, r *http.Request) {
	// TODO: implement Plex connectivity check
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	w.Write([]byte(`{"status": "ok", "message": "Not implemented yet"}`))
}

func handleStartWatching(w http.ResponseWriter, r *http.Request) {
	// TODO: implement start watching endpoint
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	w.Write([]byte(`{"status": "ok", "message": "Not implemented yet"}`))
}

func handleStopWatching(w http.ResponseWriter, r *http.Request) {
	// TODO: implement stop watching endpoint
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	w.Write([]byte(`{"status": "ok", "message": "Not implemented yet"}`))
}

func handleScan(w http.ResponseWriter, r *http.Request) {
	// TODO: implement manual scan endpoint
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	w.Write([]byte(`{"status": "ok", "message": "Not implemented yet"}`))
}
