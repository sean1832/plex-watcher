package fs_watcher

import (
	"context"
	"log/slog"
	"time"

	"github.com/fsnotify/fsnotify"
)

// eventLoop pumps events/errors, does optional debouncing, and handles recursive add-on-new-dir.
func (pw *FsWatcher) eventLoop(ctx context.Context) {
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
					if err := pw.watchSubtree(event.Name); err != nil {
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
