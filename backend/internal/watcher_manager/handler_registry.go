package watcher_manager

import (
	"fmt"
	"path/filepath"
	"plexwatcher/internal/fs_watcher"
	"plexwatcher/internal/types"
	"strings"
	"sync"
)

// handlerRegistry maps services to their event handlers
type handlerRegistry struct {
	handler map[types.ServiceType]fs_watcher.Handler
	mu      sync.Mutex
}

func NewHandlerRegistry() *handlerRegistry {
	return &handlerRegistry{
		handler: make(map[types.ServiceType]fs_watcher.Handler),
	}
}

func (r *handlerRegistry) Register(service types.ServiceType, handler fs_watcher.Handler) {
	r.mu.Lock()
	defer r.mu.Unlock()
	r.handler[service] = handler
}

func (r *handlerRegistry) Get(service types.ServiceType) (fs_watcher.Handler, bool) {
	r.mu.Lock()
	defer r.mu.Unlock()
	h, ok := r.handler[service]
	return h, ok
}

func (r *handlerRegistry) Dispatch(event fs_watcher.Event, watchDirs []types.WatchDir) error {
	service := findServiceForPath(event.Path, watchDirs)
	if service == "" {
		return fmt.Errorf("no service found for path: %s", event.Path)
	}
	handler, ok := r.Get(service)
	if !ok {
		return fmt.Errorf("no handler registered for service %s (path: %s)", service, event.Path)
	}

	handler(event)
	return nil
}

// findServiceForPath finds which service owns this path (longest prefix match)
func findServiceForPath(eventPath string, watchDirs []types.WatchDir) types.ServiceType {
	normalized := filepath.Clean(eventPath)
	lower := strings.ToLower(normalized)

	var longestMatch string
	var matchedService types.ServiceType

	for _, dir := range watchDirs {
		if !dir.Enabled {
			continue
		}
		watchPath := strings.ToLower(filepath.Clean(dir.Path))
		if strings.HasPrefix(lower, watchPath) {
			if len(watchPath) > len(longestMatch) {
				longestMatch = watchPath
				matchedService = dir.Service
			}
		}
	}
	return matchedService
}
