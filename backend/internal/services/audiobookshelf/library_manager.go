package audiobookshelf

import (
	"context"
	"fmt"
	"path/filepath"
	"plexwatcher/internal/types"
	"strings"
)

type LibraryManager struct {
	Client    *AbsClient
	Libraries []types.AbsLibrary
}

func NewLibraryManager(ctx context.Context, client *AbsClient) (*LibraryManager, error) {
	libs, _, err := client.ListLibraries(ctx)
	if err != nil {
		return nil, fmt.Errorf("failed to list libraries: %w", err)
	}
	return &LibraryManager{
		Client:    client,
		Libraries: libs,
	}, nil
}

func (lm *LibraryManager) GetLibraryByPath(path string) (*types.AbsLibrary, error) {
	if len(lm.Libraries) == 1 {
		return &lm.Libraries[0], nil // only one library, return it
	}

	// normalize path for comparison
	normalized := filepath.ToSlash(filepath.Clean(path))
	lower := strings.ToLower(normalized)

	var longestMatch string
	var matchedLibrary *types.AbsLibrary

	for i := range lm.Libraries {
		lib := &lm.Libraries[i]
		for _, libPath := range lib.Folders {
			// normalize library path
			libNormalized := filepath.ToSlash(filepath.Clean(libPath.FullPath))
			libLower := strings.ToLower(libNormalized)

			if strings.HasPrefix(lower, libLower) {
				// This check ensures we match a full directory name, not just a partial one.
				// e.g., it prevents "/media/audiobooks-new" from matching "/media/audiobooks"
				// The path must either be an exact match or be followed by a path separator.
				isExactMatch := len(libLower) == len(lower)
				isSubPath := len(lower) > len(libLower) && lower[len(libLower)] == '/'
				if isExactMatch || isSubPath {
					// If this match is more specific (longer) than the previous best, update it.
					if len(libLower) > len(longestMatch) {
						longestMatch = libLower
						matchedLibrary = lib
					}
				}
			}
		}
	}
	if matchedLibrary != nil {
		return matchedLibrary, nil
	}
	return nil, fmt.Errorf("no library found containing path: %s", path)
}

func (lm *LibraryManager) ScanPath(ctx context.Context, path string) error {
	lib, err := lm.GetLibraryByPath(path)
	if err != nil {
		return fmt.Errorf("scan path: %w", err)
	}
	code, err := lm.Client.ScanLibrary(ctx, lib.Id)
	if err != nil {
		return fmt.Errorf("scan library: (%d) %w", code, err)
	}
	return nil
}
