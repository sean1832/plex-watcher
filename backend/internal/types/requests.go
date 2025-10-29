package types

type RequestStart struct {
	ServerUrl   string     `json:"server_url"`
	Token       string     `json:"token"`
	WatchedDirs []WatchDir `json:"watched_dirs"` // TODO: Update frontend
	Cooldown    int        `json:"cooldown"`     // seconds; used as debounce
}

type RequestScan struct {
	ServerUrl string   `json:"server_url"`
	Token     string   `json:"token"`
	Paths     []string `json:"paths"`
}

type WatchDir struct {
	Path    string  `json:"path"`    // absolute path to watch
	Service service `json:"service"` // which service this dir is for (plex, audiobookshelf, etc)
	Enabled bool    `json:"enabled"` // whether this dir is enabled for watching
}

type service string

const (
	ServicePlex           service = "plex"
	ServiceAudiobookshelf service = "audiobookshelf"
)
