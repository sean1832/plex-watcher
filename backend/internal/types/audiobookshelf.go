package types

type AbsLibraryResponse struct {
	Libraries []AbsLibrary `json:"libraries"`
}

type AbsLibrary struct {
	Id        string          `json:"id"`
	Name      string          `json:"name"`
	MediaType string          `json:"mediaType"`
	Folders   []libraryFolder `json:"folders"`
}

type libraryFolder struct {
	Id       string `json:"id"`
	FullPath string `json:"fullPath"`
}
