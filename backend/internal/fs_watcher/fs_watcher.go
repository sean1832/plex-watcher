package fs_watcher

import (
	"context"
	"errors"
	"fmt"
	"log"
	"os"
	"path/filepath"
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
type Handler func(Event)

// Config controls plexWatcher behaviour
type Config struct {
	Dirs []string

	// Recursive causes the watcher to also watch all subdirs
	Recursive bool

	// DebounceWindow groups rapid bursts of event into one.
	// Set to 0 to disable debounce
	DebounceWindow time.Duration

	// Hnadler receives events. Must be non-nil.
	Handler Handler

	// Logger is used for internal diagnostics. If nil, logs to the standard logger.
	Logger *log.Logger
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

func (pw *PlexWatcher) Start(ctx context.Context) error {
	pw.mutex.Lock()
	defer pw.mutex.Unlock()

	if pw.closed {
		return errors.New("watcher already closed")
	}
	if pw.started {
		return errors.New("watcher already started")
	}
	// validate and add directories
	for _, dir := range pw.cfg.Dirs {
		if err := ensureDirExists(dir); err != nil {
			return err
		}
		if pw.cfg.Recursive {
			if err := pw.addRecursive(dir); err != nil {
				return err
			}
		} else {
			if err := pw.watcher.Add(dir); err != nil {
				return fmt.Errorf("watcher.Add(%s): %w", dir, err)
			}
		}
	}

	pw.started = true
	pw.waitGroup.Add(1)
	go pw.run(ctx)
	return nil
}

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
	_ = pw.watcher.Close()
	pw.waitGroup.Wait()
	return nil
}

// run pumps events/errors, does optional debouncing, and handles recursive add-on-new-dir.
func (pw *PlexWatcher) run(ctx context.Context) {
	defer pw.waitGroup.Done()

	logf := func(format string, args ...any) {
		if pw.cfg.Logger != nil {
			pw.cfg.Logger.Printf(format, args...)
		} else {
			log.Printf(format, args...)
		}
	}

	var (
		debounce = pw.cfg.DebounceWindow
		timer    *time.Timer
		pending  = make(map[string]fsnotify.Op) // path -> accumulated ops
		flushCh  = make(chan struct{}, 1)
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

	// start a helper goroutine to flush when asked
	if debounce > 0 {
		go func() {
			for range flushCh {
				flush()
			}
		}()
	}

	for {
		select {
		case <-pw.stop:
			// final flush
			if debounce > 0 {
				flush()
			}
			return
		case <-ctx.Done():
			if debounce > 0 {
				flush()
			}
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
						logf("failed to add new subdir %q: %v", event.Name, err)
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
			if timer == nil {
				timer = time.NewTimer(debounce)
			} else {
				if !timer.Stop() {
					select {
					case <-timer.C: // drain if needed
					default:
					}
				}
				timer.Reset(debounce)
			}

			go func(t *time.Timer) {
				<-t.C
				select {
				case flushCh <- struct{}{}:
				default:
				}
			}(timer)
		}
	}

}

// ====================
// private functions
// ====================

// add subdirs recursivesly with a root path
func (pw *PlexWatcher) addRecursive(root string) error {
	return filepath.WalkDir(root, func(path string, d os.DirEntry, err error) error {
		if err != nil {
			return err
		}
		if d.IsDir() {
			if err := pw.watcher.Add(path); err != nil {
				return fmt.Errorf("watcher.Add(%s): %w", path, err)
			}
		}
		return nil
	})
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
