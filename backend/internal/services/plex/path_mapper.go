package plex

import (
	"path/filepath"
	"plexwatcher/internal/types"
	"strings"
)

// MapToPlexPath returns the Plex-visible path for a given local path,
// using longest suffix matching on path components (case-insensitive).
// It also returns the matched Plex root. If no root matches, ok=false.
func mapToPlexPath(localPath string, sectionRoots []types.PlexSection) (mapped string, matchedRoot *types.PlexSection) {
	localParts := splitPathParts(localPath)
	if len(localParts) == 0 {
		return "", nil // <-- cannot split
	}
	localLower := toLower(localParts)

	var (
		bestK           int
		bestChildren    []string
		bestSectionRoot types.PlexSection
	)

	for _, root := range sectionRoots {
		if root.RootPath == "" {
			continue
		}
		rootParts := splitPathParts(root.RootPath)
		if len(rootParts) == 0 {
			continue // <-- cannot split plex root, proceed to next root
		}
		rootLower := toLower(rootParts)

		maxK := len(rootParts)
		for k := maxK; k >= 1; k-- {
			suffix := rootLower[len(rootLower)-k:] // last k part of the root
			// slide this suffix across the local path
			for idx := 0; idx <= len(localLower)-k; idx++ {
				if equalString(localLower[idx:idx+k], suffix) {
					children := localParts[idx+k:]
					if k > bestK {
						bestK = k
						bestChildren = children
						bestSectionRoot = root
					}
					break // found the best match for this k; no need to check shorter substrings
				}
			}
			if bestK == k {
				break // longest possible k for this root; move to the next root
			}
		}
	}

	if bestSectionRoot.RootPath == "" {
		return "", nil
	}

	// join using os-native seperators for the mapped results
	mapped = filepath.Join(append([]string{
		filepath.Clean(bestSectionRoot.RootPath),
	}, bestChildren...)...)

	// normalize to forward slashes for Plex compatibility (Plex expects Unix-style paths)
	mapped = filepath.ToSlash(mapped)

	return mapped, &bestSectionRoot
}

func splitPathParts(p string) []string {
	p = filepath.Clean(p)
	if p == "." || p == string(filepath.Separator) {
		return nil
	}

	delims := func(r rune) bool {
		// treat both as delimiters
		return r == '/' || r == '\\'
	}
	parts := strings.FieldsFunc(p, delims)
	// filter out empties
	out := make([]string, 0, len(parts))
	for _, s := range parts {
		if s != "" && s != string(filepath.Separator) {
			out = append(out, s)
		}
	}
	return out
}

func toLower(xs []string) []string {
	out := make([]string, len(xs))
	for i, s := range xs {
		out[i] = strings.ToLower(s)
	}
	return out
}

// equal checks if two string slices are equal.
func equalString(a, b []string) bool {
	if len(a) != len(b) {
		return false
	}
	for i := range a {
		if a[i] != b[i] {
			return false
		}
	}
	return true
}
