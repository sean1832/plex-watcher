package main

import (
	"context"
	"log"
	"net/http"
	"plexwatcher/internal/api"
	"strconv"
)

// TODO: implement middleware CORS

func main() {
	port := 8080
	conf := loadEnv(".env")
	log.Println("========== SERVER CONFIG ==========")
	log.Printf("ConcurrencyLimit: %d", conf.Concurrency)
	log.Printf("SupportedExtensions: %v", conf.Extensions)
	log.Println("===================================")

	api := api.NewAPI(context.Background(), conf.Concurrency, conf.Extensions)

	mux := http.NewServeMux() // <-- create a new server mux (control the traffic). Request multiplexer
	mux.HandleFunc("/", api.Root)
	mux.HandleFunc("GET /status", api.GetStatus)
	mux.HandleFunc("GET /prob-plex", api.ProbPlex)
	mux.HandleFunc("POST /start", api.Start)
	mux.HandleFunc("POST /stop", api.Stop)
	mux.HandleFunc("POST /scan", api.Scan)

	log.Printf("Server listening to port 0.0.0.0:%v...\n", port)
	http.ListenAndServe(":"+strconv.Itoa(port), mux)
}
