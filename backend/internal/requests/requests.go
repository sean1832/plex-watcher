package requests

type StartRequest struct {
	ServerUrl string   `json:"server_url"`
	Token     string   `json:"token"`
	Paths     []string `json:"paths"`
	Cooldown  int      `json:"cooldown"` // seconds; used as debounce
}

type ScanRequest struct {
	ServerUrl string   `json:"server_url"`
	Token     string   `json:"token"`
	Paths     []string `json:"paths"`
}

type ListSectionsRequest struct {
	ServerUrl string `json:"server_url"`
	Token     string `json:"token"`
}
