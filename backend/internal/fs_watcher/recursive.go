package fs_watcher

import (
	"log/slog"
	"os"
	"path/filepath"
	"sync"
	"sync/atomic"
)

// add subdirs recursivesly with a root path
// Uses parallel directory traversal for better performance on large directory trees
func (pw *FsWatcher) watchSubtree(root string) error {
	// Collect all directories first (fast - just filesystem scan)
	var dirs []string
	err := filepath.WalkDir(root, func(path string, d os.DirEntry, err error) error {
		if err != nil {
			slog.Debug("error accessing path during scan, skipping", "path", path, "error", err)
			if d != nil && d.IsDir() {
				return filepath.SkipDir
			}
			return nil
		}
		if d.IsDir() {
			dirs = append(dirs, path)
		}
		return nil
	})
	if err != nil {
		return err
	}

	slog.Debug("directories discovered, adding watches", "count", len(dirs), "root", root)

	// add watches in parallel (slow - syscalls)
	var wg sync.WaitGroup
	workerCount := 32 // workers for syscall-bound operations
	var addedCount int64
	var failCount int64

	// Create work chunks
	chunkSize := (len(dirs) + workerCount - 1) / workerCount

	for i := 0; i < workerCount; i++ {
		start := i * chunkSize
		if start >= len(dirs) {
			break
		}
		end := start + chunkSize
		if end > len(dirs) {
			end = len(dirs)
		}

		wg.Add(1)
		go func(chunk []string) {
			defer wg.Done()
			localAdded := 0
			localFailed := 0
			for _, dir := range chunk {
				if err := pw.watcher.Add(dir); err != nil {
					slog.Debug("failed to add watch", "path", dir, "error", err)
					localFailed++
				} else {
					localAdded++
				}
			}
			atomic.AddInt64(&addedCount, int64(localAdded))
			atomic.AddInt64(&failCount, int64(localFailed))
		}(dirs[start:end])
	}

	wg.Wait()

	if failCount > 0 {
		slog.Warn("some watches failed to add", "added", addedCount, "failed", failCount, "root", root)
	} else {
		slog.Debug("completed adding watches", "directories", addedCount, "root", root)
	}

	return nil
}
