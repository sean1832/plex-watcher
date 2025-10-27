package main

import (
	"log/slog"
	"os"
	"strconv"
	"strings"

	"github.com/joho/godotenv"
)

type serverConfig struct {
	Extensions  []string
	Concurrency int
	Origins     []string
	LogLevel    slog.Level
}

var defaultExts = []string{
	".mp4",
	".mkv",
	".avi",
	".mov",
	".divx",
	".mp3",
	".m4a",
	".flac",
	".wma",
}

// load environment variables from a .env file or the system environment
func loadEnv(envpath string) serverConfig {
	err := godotenv.Load(envpath)
	if err == nil {
		slog.Info("Using .env file as environment variable.")
	}
	concurrency := tryLoadEnvInt("CONCURRENCY_LIMIT", 10)
	exts := tryLoadEnvStringList("SUPPORTED_EXTENSIONS", defaultExts)
	origins := tryLoadEnvStringList("ALLOWED_ORIGINS", []string{"*"})
	logLevel := parseLogLevel(os.Getenv("LOG_LEVEL"), slog.LevelInfo)

	return serverConfig{
		Concurrency: concurrency,
		Extensions:  exts,
		Origins:     origins,
		LogLevel:    logLevel,
	}
}

// parseLogLevel converts a string log level to slog.Level
// Returns defaultLevel if the string is empty or invalid
func parseLogLevel(levelStr string, defaultLevel slog.Level) slog.Level {
	if levelStr == "" {
		return defaultLevel
	}

	switch strings.ToUpper(strings.TrimSpace(levelStr)) {
	case "DEBUG":
		return slog.LevelDebug
	case "INFO":
		return slog.LevelInfo
	case "WARN", "WARNING":
		return slog.LevelWarn
	case "ERROR":
		return slog.LevelError
	default:
		slog.Warn(
			"Invalid log level in env var. Using default.",
			slog.String("invalid_value", levelStr),
			slog.String("default_value", defaultLevel.String()),
		)
		return defaultLevel
	}
}

func tryLoadEnvInt(key string, defaultVal int) int {
	valStr := os.Getenv(key)
	result := defaultVal
	if valStr != "" {
		v, err := strconv.Atoi(valStr)
		if err != nil {
			slog.Warn(
				"Invalid integer value for env var. Using default.",
				slog.String("key", key),
				slog.String("invalid_value", valStr),
				slog.Int("default_value", defaultVal),
				slog.Any("error", err),
			)
		} else {
			result = v
		}
	}
	return result
}

func tryLoadEnvStringList(key string, defaultVal []string) []string {
	valStr := os.Getenv(key)
	result := defaultVal

	if valStr != "" {
		var items []string
		rawItems := strings.SplitSeq(valStr, ",")
		for item := range rawItems {
			// trim spaces
			trimmed := strings.TrimSpace(item)
			if trimmed != "" {
				items = append(items, trimmed)
			}
		}
		if len(items) == 0 {
			slog.Warn(
				"Env var was set but resulted in an empty list. Using default.",
				slog.String("key", key),
				slog.String("original_value", valStr),
				slog.Any("default_value", defaultVal),
			)
		} else {
			result = items
		}
	}

	return result
}
