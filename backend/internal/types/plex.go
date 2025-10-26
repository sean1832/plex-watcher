package types

// =================================
// media types
// =================================

type MediaType string

const (
	MediaTypeMovie MediaType = "movie"
	MediaTypeShow  MediaType = "show"
)

// =================================
// section root
// =================================

// SectionRoot represents a Plex library section with its key, title, type, and root path.
type SectionRoot struct {
	SectionKey   int       `json:"section_key"`
	SectionTitle string    `json:"section_title"`
	SectionType  MediaType `json:"section_type"` // "movie" or "show"
	RootPath     string    `json:"root_path"`    // normalized abs path
}

// ================================
// media container
// ================================
type ListSectionResponse struct {
	MediaContainer mediaContainer `json:"MediaContainer"`
}

type mediaContainer struct {
	Size      int         `json:"size"`
	Directory []directory `json:"Directory"`
}

type directory struct {
	Key      string     `json:"key"`
	Title    string     `json:"title"`
	Type     string     `json:"type"`
	Location []location `json:"Location"`
}

type location struct {
	Id   int    `json:"id"`
	Path string `json:"path"`
}
