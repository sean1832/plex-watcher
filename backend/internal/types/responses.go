package types

type ResponseSuccess struct {
	Code    int    `json:"code"`
	Message string `json:"message,omitempty"`
	Data    any    `json:"data,omitempty"`
}

type ResponseError struct {
	Code    int    `json:"code"`
	Message string `json:"message,omitempty"`
}

// ========================
// Response content
// ========================

// StatusResponse represents the status of the Plex watcher.
type StatusResponse struct {
	IsWatching bool     `json:"is_watching"`
	Paths      []string `json:"paths"`
	Server     *string  `json:"server,omitempty"`
	Cooldown   int      `json:"cooldown"`
}
