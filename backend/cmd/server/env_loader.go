package main

import (
	"log"
	"os"
	"strconv"
	"strings"

	"github.com/joho/godotenv"
)

type serverConfig struct {
	Extensions  []string
	Concurrency int
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
		log.Println("INFO: using .env file as environment variable.")
	}
	concurrency := tryLoadEnvInt("CONCURRENCY_LIMIT", 10)
	exts := tryLoadEnvStringList("SUPPORTED_EXTENSIONS", defaultExts)

	return serverConfig{
		Concurrency: concurrency,
		Extensions:  exts,
	}
}

func tryLoadEnvInt(key string, defaultVal int) int {
	valStr := os.Getenv(key)
	result := defaultVal
	if valStr != "" {
		v, err := strconv.Atoi(valStr)
		if err != nil {
			log.Printf("Invalid '%s' value '%s'. Using default value '%d'. Error: '%v'", key, valStr, defaultVal, err)
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
			log.Printf("'%s' was set but resulted in an empty list. Using default extensions", key)
		} else {
			result = items
		}
	}

	return result
}
