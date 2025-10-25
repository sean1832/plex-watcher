package plex

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"path/filepath"
	"strconv"
	"time"
)

type PlexAPI interface {
	ListSections(ctx context.Context) ([]SectionRoot, error)
	ScanSectionPath(ctx context.Context, sectionKey int, path *string) error
}

// PlexClient is a client for interacting with the Plex Media Server API.
type PlexClient struct {
	BaseURL   *url.URL
	Token     string
	HTTP      *http.Client
	UserAgent string // optional, can be empty
}

// NewPlexClient creates a new PlexClient with the given base URL and token.
func NewPlexClient(base, token string) (*PlexClient, error) {
	if base == "" {
		return nil, fmt.Errorf("base URL is empty")
	}

	parsedURL, err := url.Parse(base)
	if err != nil {
		return nil, fmt.Errorf("invalid base URL: %w", err)
	}

	// Ensure we have a scheme and host after parsing
	if parsedURL.Scheme == "" || parsedURL.Host == "" {
		return nil, fmt.Errorf("invalid base URL, missing scheme or host: %s", base)
	}
	return &PlexClient{
		BaseURL: parsedURL,
		Token:   token,
		HTTP: &http.Client{
			Timeout: 30 * time.Second,
		},
		UserAgent: "PlexWatcherClient/1.0",
	}, nil
}

func (pc *PlexClient) buildURL(parts []string, q url.Values) *url.URL {
	u := *pc.BaseURL // copy
	u.Path, _ = url.JoinPath(pc.BaseURL.Path, parts...)
	if q == nil {
		q = url.Values{}
	}
	if pc.Token != "" {
		q.Set("X-Plex-Token", pc.Token)
	}
	u.RawQuery = q.Encode()
	return &u
}

func (pc *PlexClient) newRequest(ctx context.Context, method string, u *url.URL, body io.Reader) (*http.Request, error) {
	req, err := http.NewRequestWithContext(ctx, method, u.String(), body)
	if err != nil {
		return nil, fmt.Errorf("error making request context: %v", err)
	}
	if pc.UserAgent != "" {
		req.Header.Set("User-Agent", pc.UserAgent)
	}
	// accept response as JSON
	req.Header.Set("accept", "application/json")

	return req, nil
}

// ======================
// PUBLIC API
// ======================

// List all root libraries. (use this to get section keys for further operations)
func (pc *PlexClient) ListSections(ctx context.Context) ([]SectionRoot, error) {
	// ENDPOINT: /library/sections
	u := pc.buildURL([]string{"library", "sections"}, nil)

	req, err := pc.newRequest(ctx, http.MethodGet, u, nil)
	if err != nil {
		return nil, err
	}

	res, err := pc.HTTP.Do(req) // <-- make request, get response
	if err != nil {
		return nil, err
	}
	defer res.Body.Close() // <-- finally: close body

	if res.StatusCode < 200 || res.StatusCode >= 300 {
		b, _ := io.ReadAll(io.LimitReader(res.Body, 4<<10)) // <-- only return 4096 bytes of message
		return nil, fmt.Errorf("plex list libraries: http %d: %s", res.StatusCode, string(b))
	}

	var resData ListSectionResponse // define to match plex schema
	err = json.NewDecoder(res.Body).Decode(&resData)
	if err != nil {
		return nil, fmt.Errorf("plex list libraries: decode: %w", err)
	}
	sections := make([]SectionRoot, 0, len(resData.MediaContainer.Directory)) // <-- create a section root array
	for _, d := range resData.MediaContainer.Directory {
		id, err := strconv.Atoi(d.Key)
		if err != nil {
			return nil, fmt.Errorf("plex list library: failed to convert SectionKey to interger")
		}
		var mediaType MediaType
		switch d.Type {
		case "movie":
			mediaType = MediaTypeMovie
		case "show":
			mediaType = MediaTypeShow
		default:
			return nil, fmt.Errorf("plex list library: unkown or unsupported media type: %s", d.Type)
		}

		rootPath := ""
		if len(d.Location) > 0 {
			rootPath = filepath.Clean(d.Location[0].Path)
		}

		sections = append(sections, SectionRoot{
			SectionKey:   id,
			SectionTitle: d.Title,
			SectionType:  mediaType,
			RootPath:     rootPath,
		})
	}

	return sections, nil
}

// scans a specific path in a library section, or the entire section if path is nil or empty.
func (pc *PlexClient) ScanSectionPath(ctx context.Context, sectionKey int, path *string) error {
	// ENDPOINT: /library/sections/id/refresh?path=xxx
	query := url.Values{}
	if path != nil && *path != "" {
		query.Set("path", *path)
	} else {
		query.Set("force", "1") // <-- if path is not set, scan entire section instead
	}

	u := pc.buildURL([]string{"library", "sections", strconv.Itoa(sectionKey), "refresh"}, query)
	req, err := pc.newRequest(ctx, http.MethodPost, u, nil)
	if err != nil {
		return err
	}

	res, err := pc.HTTP.Do(req)
	if err != nil {
		return err
	}
	defer res.Body.Close()

	if res.StatusCode < 200 || res.StatusCode >= 300 {
		b, _ := io.ReadAll(io.LimitReader(res.Body, 4<<10)) // <-- only return 4096 bytes of message
		return fmt.Errorf("plex refresh section %d: http %d: %s", sectionKey, res.StatusCode, string(b))
	}

	// treat non-error as success
	return nil
}
