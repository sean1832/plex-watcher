package types

type RequestStart struct {
	ServiceConfigs map[ServiceType]ServiceConfig `json:"service_configs"` // credentials per service
	WatchedDirs    []WatchDir                    `json:"watched_dirs"`
	Cooldown       int                           `json:"cooldown"` // seconds; used as debounce
}

type RequestScan struct {
	ServiceConfigs map[ServiceType]ServiceConfig `json:"service_configs"` // credentials per service
	Paths          []string                      `json:"paths"`
}

type ServiceConfig struct {
	ServerUrl string `json:"server_url"`
	Token     string `json:"token"`
}

type WatchDir struct {
	Path    string      `json:"path"`    // absolute path to watch
	Service ServiceType `json:"service"` // which service this dir is for (plex, audiobookshelf, etc)
	Enabled bool        `json:"enabled"` // whether this dir is enabled for watching
}

type ServiceType string

const (
	ServicePlex           ServiceType = "plex"
	ServiceAudiobookshelf ServiceType = "audiobookshelf"
)

/*
{
  "service_configs": {
    "plex": {
      "server_url": "http://host:32400",
      "token": "xxx"
    },
    "audiobookshelf": {
      "server_url": "http://host:13378",
      "token": "yyy"
    }
  },
  "watched_dirs": [
    {"path": "/media/tv-shows", "service": "plex", "enabled": true},
    {"path": "/media/audiobooks", "service": "audiobookshelf", "enabled": true}
  ],
  "cooldown": 5
}
*/
