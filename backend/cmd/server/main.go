package main

import (
	"context"
	"log/slog"
	"net/http"
	"os"
	"plexwatcher/internal/api"
	"strconv"

	"github.com/lmittmann/tint"
)

var Version = "dev"

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
		"version", Version,
		"log_level", conf.LogLevel.String(),
		"concurrency", conf.Concurrency,
		"extensions", conf.Extensions,
		"origins", conf.Origins,
	)

	handler := api.NewHandler(context.Background(), conf.Concurrency, conf.Extensions)

	mux := http.NewServeMux() // <-- create a new server mux (control the traffic). Request multiplexer
	handler.RegisterRoutes(mux)

	slog.Info("Server listening", "port", port)
	http.ListenAndServe(":"+strconv.Itoa(port), api.WithCORS(mux, conf.Origins))
}
