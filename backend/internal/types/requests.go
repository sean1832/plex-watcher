package types

type RequestStart struct {
	ServerUrl string   `json:"server_url"`
	Token     string   `json:"token,omitempty"`
	Paths     []string `json:"paths"`
	Cooldown  int      `json:"cooldown"` // seconds; used as debounce
}

type RequestScan struct {
	ServerUrl string   `json:"server_url"`
	Token     string   `json:"token"`
	Paths     []string `json:"paths"`
}

// WatchlistCache stores only non-sensitive watcher config for persistence
type WatchlistCache struct {
	Paths    []string `json:"paths"`
	Cooldown int      `json:"cooldown"`
}
