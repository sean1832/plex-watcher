package fs_watcher

import (
	"context"
	"errors"
	"fmt"
	"log/slog"
	"plexwatcher/internal/types"
	"sync"
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
	Dirs []types.WatchDir `json:"dirs"`

	// Recursive causes the watcher to also watch all subdirs
	Recursive bool `json:"recursive"`

	// DebounceWindow groups rapid bursts of event into one.
	// Set to 0 to disable debounce
	DebounceWindow time.Duration

	// Hnadler receives events. Must be non-nil.
	Handler Handler
}

type FsWatcher struct {
	cfg     Config
	watcher *fsnotify.Watcher

	mutex   sync.Mutex
	started bool
	closed  bool

	waitGroup sync.WaitGroup
	stop      chan struct{} // closed to signal shutdown
}

// Create a new watcher. Call Start(ctx) to start watching.
func NewPlexWatcher(cfg Config) (*FsWatcher, error) {
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
	pw := &FsWatcher{
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
func (pw *FsWatcher) GetConfig() Config {
	pw.mutex.Lock()
	defer pw.mutex.Unlock()
	return pw.cfg
}

// ====================
// public functions
// ====================

// Start begins watching the configured directories.
func (pw *FsWatcher) Start(ctx context.Context) error {
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
		if !dir.Enabled {
			slog.Debug("skipping disabled watch dir", "path", dir.Path)
			continue
		}
		if err := ensureDirExists(dir.Path); err != nil {
			return err
		}
		if err := pw.watcher.Add(dir.Path); err != nil {
			return fmt.Errorf("watcher.Add(%s): %w", dir.Path, err)
		}
	}

	// start the main run loop
	pw.started = true
	pw.waitGroup.Add(1)
	go pw.eventLoop(ctx)

	// launch background goroutine to add subdirs if Recursive is set
	if pw.cfg.Recursive {
		for _, dir := range pw.cfg.Dirs {
			if !dir.Enabled {
				continue
			}
			go func(dirToScan string) {
				slog.Info("starting recursive directory watch setup in background", "path", dirToScan)
				startTime := time.Now()
				if err := pw.watchSubtree(dirToScan); err != nil {
					slog.Error("failed to perform recursive watch setup", "path", dirToScan, "error", err)
				} else {
					elapsed := time.Since(startTime)
					slog.Info("completed recursive directory watch setup",
						"path", dirToScan,
						"elapsed", elapsed.String())
				}
			}(dir.Path)
		}
		slog.Info("recursive watching initiated in background - watcher is ready")
	}

	return nil
}

// Stop stops watching and releases resources.
func (pw *FsWatcher) Stop() error {
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
