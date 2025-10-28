package types

// =================================
// media types
// =================================

type PlexMediaType string

const (
	MediaTypeMovie PlexMediaType = "movie"
	MediaTypeShow  PlexMediaType = "show"
)

// =================================
// section root
// =================================

// PlexSection represents a Plex library section with its key, title, type, and root path.
type PlexSection struct {
	SectionKey   int           `json:"section_key"`
	SectionTitle string        `json:"section_title"`
	SectionType  PlexMediaType `json:"section_type"` // "movie" or "show"
	RootPath     string        `json:"root_path"`    // normalized abs path
}

// ================================
// media container
// ================================
type PlexListSectionResponse struct {
	MediaContainer plexMediaContainer `json:"MediaContainer"`
}

type plexMediaContainer struct {
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
