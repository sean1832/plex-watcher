package fs_watcher

import (
	"context"
	"errors"
	"fmt"
	"log/slog"
	"os"
	"path/filepath"
	"sync"
	"sync/atomic"
	"time"

	"github.com/fsnotify/fsnotify"
)

// Event is a thin wrapper over fsnotify.Event, extend later without breaking API
type Event struct {
	Path string
	Op   fsnotify.Op
	Err  error
}

// Handler is called for each event (or error) received from fsnotify.
// In other words, actions to be taken on each event are defined by the user via this handler.
type Handler func(Event)

// Config controls plexWatcher behaviour
type Config struct {
	Dirs []string `json:"dirs"`

	// Recursive causes the watcher to also watch all subdirs
	Recursive bool `json:"recursive"`

	// DebounceWindow groups rapid bursts of event into one.
	// Set to 0 to disable debounce
	DebounceWindow time.Duration

	// Hnadler receives events. Must be non-nil.
	Handler Handler
}

type PlexWatcher struct {
	cfg     Config
	watcher *fsnotify.Watcher

	mutex   sync.Mutex
	started bool
	closed  bool

	waitGroup sync.WaitGroup
	stop      chan struct{} // closed to signal shutdown
}

// Create a new watcher. Call Start(ctx) to start watching.
func NewPlexWatcher(cfg Config) (*PlexWatcher, error) {
	if len(cfg.Dirs) == 0 {
		return nil, errors.New("no directories provided")
	}
	if cfg.Handler == nil {
		return nil, errors.New("handler must be provided")
	}
	watcher, err := fsnotify.NewWatcher()
	if err != nil {
		return nil, fmt.Errorf("fsnotify.NewWatcher: %w", err)
	}
	pw := &PlexWatcher{
		cfg:     cfg,
		watcher: watcher,
		stop:    make(chan struct{}),
	}
	return pw, nil
}

// ====================
// getters
// ====================

// GetConfig returns the current configuration of the PlexWatcher.
func (pw *PlexWatcher) GetConfig() Config {
	pw.mutex.Lock()
	defer pw.mutex.Unlock()
	return pw.cfg
}

// ====================
// public functions
// ====================

// Start begins watching the configured directories.
func (pw *PlexWatcher) Start(ctx context.Context) error {
	pw.mutex.Lock()
	defer pw.mutex.Unlock()

	if pw.closed {
		return errors.New("watcher already closed")
	}
	if pw.started {
		return errors.New("watcher already started")
	}
	// add only the top-level dirs first. This will be expanded if Recursive is set.
	for _, dir := range pw.cfg.Dirs {
		if err := ensureDirExists(dir); err != nil {
			return err
		}
		if err := pw.watcher.Add(dir); err != nil {
			return fmt.Errorf("watcher.Add(%s): %w", dir, err)
		}
	}

	// start the main run loop
	pw.started = true
	pw.waitGroup.Add(1)
	go pw.run(ctx)

	// launch background goroutine to add subdirs if Recursive is set
	if pw.cfg.Recursive {
		for _, dir := range pw.cfg.Dirs {
			go func(dirToScan string) {
				slog.Info("starting recursive directory watch setup in background", "path", dirToScan)
				startTime := time.Now()
				if err := pw.addRecursive(dirToScan); err != nil {
					slog.Error("failed to perform recursive watch setup", "path", dirToScan, "error", err)
				} else {
					elapsed := time.Since(startTime)
					slog.Info("completed recursive directory watch setup",
						"path", dirToScan,
						"elapsed", elapsed.String())
				}
			}(dir)
		}
		slog.Info("recursive watching initiated in background - watcher is ready")
	}

	return nil
}

// Stop stops watching and releases resources.
func (pw *PlexWatcher) Stop() error {
	pw.mutex.Lock()
	if pw.closed {
		pw.mutex.Unlock()
		return nil
	}
	pw.closed = true
	close(pw.stop) // signal run loop to exit
	pw.mutex.Unlock()

	// closing the fsnotify watcher unblocks <-Events and <-Errors
	pw.waitGroup.Wait()
	return nil
}

// run pumps events/errors, does optional debouncing, and handles recursive add-on-new-dir.
func (pw *PlexWatcher) run(ctx context.Context) {
	defer pw.waitGroup.Done()
	defer pw.watcher.Close()

	var (
		debounce = pw.cfg.DebounceWindow
		timer    *time.Timer
		pending  = make(map[string]fsnotify.Op) // path -> accumulated ops
	)

	flush := func() {
		if len(pending) == 0 {
			return
		}
		for p, op := range pending {
			pw.cfg.Handler(Event{
				Path: p,
				Op:   op,
			})
		}
		pending = make(map[string]fsnotify.Op)
	}

	// Initialize timer as stopped if debouncing is enabled
	if debounce > 0 {
		timer = time.NewTimer(debounce)
		if !timer.Stop() {
			<-timer.C
		}
	}

	for {
		select {
		case <-pw.stop:
			// Stop timer and do final flush
			if timer != nil {
				if !timer.Stop() {
					select {
					case <-timer.C:
					default:
					}
				}
			}
			flush()
			return
		case <-ctx.Done():
			// Stop timer and do final flush
			if timer != nil {
				if !timer.Stop() {
					select {
					case <-timer.C:
					default:
					}
				}
			}
			flush()
			return
		case err, ok := <-pw.watcher.Errors:
			if !ok {
				return
			}
			pw.cfg.Handler(Event{Err: err})
		case event, ok := <-pw.watcher.Events:
			if !ok {
				return
			}

			if pw.cfg.Recursive && event.Op&fsnotify.Create == fsnotify.Create {
				if isDir(event.Name) {
					if err := pw.addRecursive(event.Name); err != nil {
						slog.Error("failed to add new subdir", "path", event.Name, "error", err)
					}
				}
			}

			if debounce <= 0 {
				pw.cfg.Handler(Event{Path: event.Name, Op: event.Op})
				continue
			}

			// accumulate
			combined := pending[event.Name] | event.Op
			pending[event.Name] = combined

			// (re)arm timer
			if !timer.Stop() {
				select {
				case <-timer.C: // drain if needed
				default:
				}
			}
			timer.Reset(debounce)
		case <-timer.C:
			// Timer expired - flush accumulated events
			flush()
		}
	}
}

// ====================
// private functions
// ====================

// add subdirs recursivesly with a root path
// Uses parallel directory traversal for better performance on large directory trees
func (pw *PlexWatcher) addRecursive(root string) error {
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

// =====================
// utilities
// =====================

func ensureDirExists(p string) error {
	info, err := os.Stat(p)
	if err != nil {
		if os.IsNotExist(err) {
			return fmt.Errorf("directory not exist: %s", p)
		}
		return fmt.Errorf("stat %s: %w", p, err)
	}
	if !info.IsDir() {
		return fmt.Errorf("path is not a directory: %s", p)
	}
	return nil
}

func isDir(p string) bool {
	stat, err := os.Stat(p)
	return err == nil && stat.IsDir()
}
