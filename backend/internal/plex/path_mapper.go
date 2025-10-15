package plex

import (
	"path/filepath"
	"strings"
)

// MapToPlexPath returns the Plex-visible path for a given local path,
// using longest suffix matching on path components (case-insensitive).
// It also returns the matched Plex root. If no root matches, ok=false.
func mapToPlexPath(localPath string, plexRoots []string) (mapped string, matchedRoot string, ok bool) {
	localParts := splitPathParts(localPath)
	if len(localParts) == 0 {
		return "", "", false // <-- cannot split
	}
	localLower := toLower(localParts)

	var (
		bestRoot     string
		bestK        int
		bestChildren []string
	)

	for _, root := range plexRoots {
		rootParts := splitPathParts(root)
		if len(rootParts) == 0 {
			continue // <-- cannot split plex root, proceed to next root
		}
		rootLower := toLower(rootParts)

		maxK := min(len(rootParts), len(localParts))
		// try longest surfix -> shortest
		for k := maxK; k >= 1; k-- {
			suffix := rootLower[len(rootLower)-1:] // last k part of the root
			// slide this suffix across the local path
			for idx := 0; idx <= len(localLower)-k; idx++ {
				if equalString(localLower[idx:idx+k], suffix) {
					children := localParts[idx+k:]
					if k > bestK {
						bestRoot = root
						bestK = k
						bestChildren = children
					}
					break // found a match at this k; try a longer k for this root earlier
				}
			}
			if bestK == k {
				break // cannot beat k for this root
			}
		}
	}
	if bestRoot == "" {
		return "", "", false
	}

	// join using os-native seperators for the mapped results
	mapped = filepath.Join(append([]string{
		filepath.Clean(bestRoot),
	}, bestChildren...)...)
	return mapped, bestRoot, true
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

// min returns the smaller of two integers.
func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}
