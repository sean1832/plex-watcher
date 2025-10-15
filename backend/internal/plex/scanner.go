package plex

import (
	"context"
	"fmt"
	"log"
	"path/filepath"
	"sort"
	"strings"
	"time"
)

// Scanner manages Plex library scanning operations.
// It maintains a mapping of filesystem paths to Plex library sections
// and provides intelligent path-to-section matching using suffix-based resolution.
type Scanner struct {
	api PlexAPI

	// sections maps section title to section metadata
	sections map[string]SectionRoot

	// roots contains all library root paths sorted by length (longest first)
	// This enables proper matching for nested library structures
	roots []SectionRoot
}

// NewScanner creates a new Scanner instance.
// It fetches all library sections from the Plex server and builds
// an optimized lookup structure for path-to-section matching.
func NewScanner(ctx context.Context, api PlexAPI) (*Scanner, error) {
	sections, err := api.ListSections(ctx)
	if err != nil {
		return nil, fmt.Errorf("failed to list libraries: %w", err)
	}
	if len(sections) <= 0 {
		return nil, fmt.Errorf("0 section found")
	}

	// Build section map by title
	sectionMap := make(map[string]SectionRoot)
	for _, section := range sections {
		sectionMap[section.SectionTitle] = section
	}

	// Sort roots by path length (longest first) for proper nested matching
	roots := make([]SectionRoot, len(sections))
	copy(roots, sections)
	sort.Slice(roots, func(i, j int) bool {
		return len(roots[i].RootPath) > len(roots[j].RootPath)
	})

	// Log discovered sections
	for _, root := range roots {
		log.Printf("Found Plex section: '%s' (%s) at %s",
			root.SectionTitle, root.SectionType, root.RootPath)
	}

	return &Scanner{
		api:      api,
		sections: sectionMap,
		roots:    roots,
	}, nil
}

// GetMediaType determines whether a path belongs to a movie or TV show library.
// It uses both filesystem structure analysis and section metadata for accurate detection.
//
// For deleted paths (where filesystem checks aren't possible), it uses heuristics:
//   - Checks for "Season X" patterns in path structure
//   - Falls back to section type detection
//
// For existing paths, it verifies the section type directly.
func (s *Scanner) GetMediaType(path string, isDeleted bool) (MediaType, error) {
	// For deleted paths, use heuristic analysis
	if isDeleted {
		return s.getMediaTypeForDeleted(path)
	}

	// For existing paths, find the section and use its type
	section, err := s.findSection(path)
	if err != nil {
		return "", fmt.Errorf("failed to determine media type: %w", err)
	}

	return section.SectionType, nil
}

// getMediaTypeForDeleted uses path structure heuristics to determine media type
// when the file/directory no longer exists on disk.
func (s *Scanner) getMediaTypeForDeleted(path string) (MediaType, error) {
	// Normalize path for comparison
	normalizedPath := filepath.Clean(path)
	pathParts := strings.Split(normalizedPath, string(filepath.Separator))

	// Check for TV show patterns: "Season X" folders
	for _, part := range pathParts {
		partLower := strings.ToLower(part)
		if strings.HasPrefix(partLower, "season") {
			// Check if there's a digit after "season"
			if len(partLower) > 6 { // "season" is 6 chars
				remainingPart := partLower[6:]
				// Trim spaces and check for digits
				remainingPart = strings.TrimSpace(remainingPart)
				if len(remainingPart) > 0 && isDigit(remainingPart[0]) {
					// This looks like a TV show structure
					// Try to verify with section detection
					section, err := s.findSection(path)
					if err == nil && section.SectionType == MediaTypeShow {
						return MediaTypeShow, nil
					}
					// Even if section detection fails, trust the heuristic
					return MediaTypeShow, nil
				}
			}
		}
	}

	// Try section-based detection as fallback
	section, err := s.findSection(path)
	if err != nil {
		// If we can't find the section, use path heuristics
		log.Printf("Warning: Could not find section for deleted path '%s', using heuristics", path)

		// Additional heuristic: check for any "season" mention in path
		pathLower := strings.ToLower(normalizedPath)
		if strings.Contains(pathLower, "season") {
			return MediaTypeShow, nil
		}

		// Default to movie if no clear indicators
		return MediaTypeMovie, nil
	}

	return section.SectionType, nil
}

// ScanPath triggers a Plex library scan for the specified path.
// It automatically determines the appropriate section and applies
// a cooldown period to avoid API rate limits.
func (s *Scanner) ScanPath(ctx context.Context, path string, cooldown time.Duration) error {
	section, err := s.findSection(path)
	if err != nil {
		return fmt.Errorf("failed to scan path: %w", err)
	}

	// Apply cooldown to avoid rate limits
	if cooldown > 0 {
		time.Sleep(cooldown)
	}

	// Trigger the refresh with the specific path
	pathStr := path
	err = s.api.ScanSectionPath(ctx, section.SectionKey, &pathStr)
	if err != nil {
		return fmt.Errorf("failed to refresh section '%s': %w", section.SectionTitle, err)
	}

	log.Printf("Scanned section '%s' for path: %s", section.SectionTitle, path)
	return nil
}

// GetScanPath returns the optimal path to scan based on media type.
// For TV shows, it strips "Season X" folders to scan at the show level.
// For movies, it returns the parent directory.
func (s *Scanner) GetScanPath(path string, mediaType MediaType) string {
	cleanPath := filepath.Clean(path)

	// For shows, we want to scan at the show level (not season level)
	if mediaType == MediaTypeShow {
		return s.getShowRootPath(cleanPath)
	}

	// For movies, scan the parent directory (movie folder)
	return filepath.Dir(cleanPath)
}

// getShowRootPath strips "Season X" folders from the path to get the show root.
func (s *Scanner) getShowRootPath(path string) string {
	pathParts := strings.Split(path, string(filepath.Separator))

	// Walk backwards through path parts to find and remove "Season X"
	var cleanParts []string
	for _, part := range pathParts {
		partLower := strings.ToLower(part)
		// Skip parts that look like season folders
		if strings.HasPrefix(partLower, "season") && len(partLower) > 6 {
			remaining := strings.TrimSpace(partLower[6:])
			if len(remaining) > 0 && isDigit(remaining[0]) {
				continue // Skip this part
			}
		}
		cleanParts = append(cleanParts, part)
	}

	return filepath.Join(cleanParts...)
}

// findSection locates the Plex library section that contains the given path.
// It uses longest-prefix matching to handle nested library structures correctly.
func (s *Scanner) findSection(path string) (*SectionRoot, error) {
	cleanPath := filepath.Clean(path)

	// Try to match against each root (already sorted longest-first)
	for _, root := range s.roots {
		// Check if path is within this root
		relPath, err := filepath.Rel(root.RootPath, cleanPath)
		if err != nil {
			continue // Not related to this root
		}

		// If the relative path doesn't start with "..", it's a child of this root
		if !strings.HasPrefix(relPath, "..") {
			return &root, nil
		}
	}

	// No matching section found - provide helpful debug info
	var availableRoots []string
	for _, root := range s.roots {
		availableRoots = append(availableRoots, root.RootPath)
	}

	return nil, fmt.Errorf(
		"no Plex section found for path '%s'. "+
			"Path does not match any configured library root. "+
			"Available roots: %v",
		path, availableRoots,
	)
}

// GetSectionByTitle retrieves a section by its title.
func (s *Scanner) GetSectionByTitle(title string) (*SectionRoot, bool) {
	section, ok := s.sections[title]
	return &section, ok
}

// GetAllSections returns all discovered library sections.
func (s *Scanner) GetAllSections() []SectionRoot {
	sections := make([]SectionRoot, 0, len(s.roots))
	sections = append(sections, s.roots...)
	return sections
}

// MapToPlexPath maps a local filesystem path to path existed on remote plex server
func (s *Scanner) MapToPlexPath(localPath string) (mapped string, matchedRoot string, ok bool) {
	if len(s.roots) == 0 {
		return "", "", false
	}

	roots := make([]string, 0, len(s.roots))
	for _, r := range s.roots {
		if r.RootPath != "" {
			roots = append(roots, r.RootPath)
		}
	}

	return mapToPlexPath(localPath, roots)
}

// isDigit checks if a byte represents an ASCII digit.
func isDigit(b byte) bool {
	return b >= '0' && b <= '9'
}
