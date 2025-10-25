package main

import (
	"context"
	"log"
	"net/http"
	"plex-watcher-backend/internal/api"
)

// TODO: implement middleware CORS

func main() {
	var port int = 8000
	api := api.NewAPI(context.Background(), 4) // limit to 4 concurrent scans

	mux := http.NewServeMux() // <-- create a new server mux (control the traffic). Request multiplexer
	mux.HandleFunc("/", api.Root)
	mux.HandleFunc("GET /status", api.GetStatus)
	mux.HandleFunc("GET /prob-plex", api.ProbPlex)
	mux.HandleFunc("POST /start", api.Start)
	mux.HandleFunc("POST /stop", api.Stop)
	mux.HandleFunc("POST /scan", api.Scan)

	log.Printf("Server listening to port 0.0.0.0:%v...\n", port)
	http.ListenAndServe(":8000", mux)
}
