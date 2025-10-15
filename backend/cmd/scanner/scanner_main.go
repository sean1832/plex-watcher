package main

import (
	"context"
	"log"
	"time"

	"plex-watcher-backend/internal/plex"
)

// Example demonstrates how to use the Plex scanner
func main() {
	// Configuration
	plexURL := "http://URL:32400"
	plexToken := "TOKEN"

	// Create API client
	client, err := plex.NewPlexClient(plexURL, plexToken)
	if err != nil {
		log.Fatal(err.Error())
	}

	// Create scanner (fetches and caches all library sections)
	ctx := context.Background()
	scanner, err := plex.NewScanner(ctx, client)
	if err != nil {
		log.Fatalf("Failed to create scanner: %v", err)
	}

	// Example 1: Scan a movie file
	log.Println("\n=== Example 1: Scanning a movie ===")
	moviePath := "/media/movies/10,000 BC (2008)/10,000 BC (2008).mkv"
	scanMovie(ctx, scanner, moviePath)

	// // Example 2: Scan a TV show episode
	// log.Println("\n=== Example 2: Scanning a TV show episode ===")
	// showPath := "/media/shows/Breaking Bad/Season 1/S01E01.mkv"
	// scanTVShow(ctx, scanner, showPath)

	// // Example 3: Handle deleted file
	// log.Println("\n=== Example 3: Handling deleted file ===")
	// deletedPath := "/media/shows/The Office/Season 5/S05E10.mkv"
	// handleDeletedFile(ctx, scanner, deletedPath)

	// // Example 4: List all sections
	// log.Println("\n=== Example 4: List all sections ===")
	// listAllSections(scanner)
}

// scanMovie demonstrates scanning a movie file
func scanMovie(ctx context.Context, scanner *plex.Scanner, localPath string) {
	// convert localPath -> plexPath
	plexPath, _, ok := scanner.MapToPlexPath(localPath)
	if !ok {
		log.Fatalf("Failed to map localPath: %s to remote path on plex server", localPath)
	}

	// Determine media type
	mediaType, err := scanner.GetMediaType(plexPath, false)
	if err != nil {
		log.Printf("Failed to determine media type: %v", err)
		return
	}
	log.Printf("Media type: %s", mediaType)

	// Get optimal scan path (for movies, this is the parent directory)
	scanPath := scanner.GetScanPath(plexPath, mediaType)
	log.Printf("Scan path: %s", scanPath)

	// Trigger scan with 500ms cooldown
	err = scanner.ScanPath(ctx, scanPath, 500*time.Millisecond)
	if err != nil {
		log.Printf("Failed to scan: %v", err)
		return
	}

	log.Printf("Successfully scanned movie at: %s", scanPath)
}

// scanTVShow demonstrates scanning a TV show episode
func scanTVShow(ctx context.Context, scanner *plex.Scanner, filePath string) {
	// Determine media type
	mediaType, err := scanner.GetMediaType(filePath, false)
	if err != nil {
		log.Printf("Failed to determine media type: %v", err)
		return
	}
	log.Printf("Media type: %s", mediaType)

	// Get optimal scan path (for shows, this strips "Season X" folders)
	scanPath := scanner.GetScanPath(filePath, mediaType)
	log.Printf("Scan path: %s (note: Season folder stripped)", scanPath)

	// Trigger scan
	err = scanner.ScanPath(ctx, scanPath, 500*time.Millisecond)
	if err != nil {
		log.Printf("Failed to scan: %v", err)
		return
	}

	log.Printf("Successfully scanned show at: %s", scanPath)
}

// handleDeletedFile demonstrates handling a deleted file
func handleDeletedFile(ctx context.Context, scanner *plex.Scanner, filePath string) {
	// For deleted files, use heuristic detection
	mediaType, err := scanner.GetMediaType(filePath, true)
	if err != nil {
		log.Printf("Failed to determine media type: %v", err)
		return
	}
	log.Printf("Media type (heuristic): %s", mediaType)

	// Get scan path
	scanPath := scanner.GetScanPath(filePath, mediaType)
	log.Printf("Scan path: %s", scanPath)

	// Note: For deleted files, you might want to skip scanning
	// or handle differently based on your use case
	log.Printf("Would scan path: %s (skipping for deleted file example)", scanPath)
}

// listAllSections demonstrates listing all discovered sections
func listAllSections(scanner *plex.Scanner) {
	sections := scanner.GetAllSections()
	log.Printf("Found %d library sections:", len(sections))

	for _, section := range sections {
		log.Printf("  - %s (%s): %s [Key: %d]",
			section.SectionTitle,
			section.SectionType,
			section.RootPath,
			section.SectionKey,
		)
	}
}
