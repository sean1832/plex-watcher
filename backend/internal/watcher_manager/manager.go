package watcher_manager

import (
	"context"
	"errors"
	"plexwatcher/internal/fs_watcher"
	"plexwatcher/internal/types"
	"sync"
	"time"
)

type Manager struct {
	mutex   sync.Mutex
	watcher *fs_watcher.FsWatcher
	cancel  context.CancelFunc
	running bool
}

func NewManager() *Manager {
	return &Manager{
		running: false,
	}
}

func (m *Manager) Start(req types.RequestStart, handler func(fs_watcher.Event)) error {
	m.mutex.Lock()
	defer m.mutex.Unlock()

	if m.running {
		return errors.New("watcher is already running")
	}
	if len(req.WatchedDirs) == 0 {
		return errors.New("no watch_dir provided")
	}
	debounce := time.Duration(req.Cooldown) * time.Second
	if debounce < 0 {
		debounce = 0
	}

	cfg := fs_watcher.Config{
		Dirs:           req.WatchedDirs,
		Recursive:      true,
		DebounceWindow: debounce,
		Handler:        handler,
	}
	watcher, err := fs_watcher.NewPlexWatcher(cfg)
	if err != nil {
		return err
	}
	ctx, cancel := context.WithCancel(context.Background())
	if err := watcher.Start(ctx); err != nil {
		cancel()
		return err
	}

	m.watcher = watcher
	m.cancel = cancel
	m.running = true
	return nil
}

func (m *Manager) Stop() error {
	m.mutex.Lock()
	defer m.mutex.Unlock()

	if !m.running {
		return errors.New("watcher not running")
	}

	// cancel user context (if watcher observes it) and stop the watcher
	if m.cancel != nil {
		m.cancel()
	}
	err := m.watcher.Stop()
	m.cancel = nil
	m.running = false
	return err
}

// Status returns the current status of the watcher
func (m *Manager) Status() (bool, []types.WatchDir, int) {
	m.mutex.Lock()
	defer m.mutex.Unlock()
	if m.watcher == nil {
		return false, nil, 0
	}
	return m.running, // is running
		m.watcher.GetConfig().Dirs, // paths being watched
		int(m.watcher.GetConfig().DebounceWindow.Seconds()) // cooldown in seconds
}
