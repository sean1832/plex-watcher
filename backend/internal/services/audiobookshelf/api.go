package audiobookshelf

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"plexwatcher/internal/http/request"
	"plexwatcher/internal/types"
	"time"
)

type AbsClient struct {
	BaseURL *url.URL
	ApiKey  string
	HTTP    *http.Client
}

func NewClient(baseUrl string, apiKey string) (*AbsClient, error) {
	u, err := url.Parse(baseUrl)
	if err != nil {
		return nil, fmt.Errorf("invalid base URL %v", err)
	}

	return &AbsClient{
		BaseURL: u,
		ApiKey:  apiKey,
		HTTP: &http.Client{
			Timeout: 30 * time.Second,
		},
	}, nil
}

func (c *AbsClient) ScanLibrary(ctx context.Context, id string) (int, error) {
	u := c.buildURL([]string{"api", "libraries", id, "scan"}, nil)
	req, err := c.requestWithAuth(ctx, http.MethodPost, u, nil)
	if err != nil {
		return http.StatusInternalServerError, err
	}
	resp, err := c.HTTP.Do(req)
	if err != nil {
		return http.StatusInternalServerError, fmt.Errorf("error making request '%s': %v", u.String(), err)
	}
	defer resp.Body.Close()
	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		b, _ := io.ReadAll(io.LimitReader(resp.Body, 4<<10)) // <-- only return 4096 bytes of message
		return resp.StatusCode, fmt.Errorf("http %d: %s", resp.StatusCode, string(b))
	}

	return http.StatusOK, nil
}

func (c *AbsClient) ListLibraries(ctx context.Context) ([]types.AbsLibrary, int, error) {
	u := c.buildURL([]string{"api", "libraries"}, nil)
	req, err := c.requestWithAuth(ctx, http.MethodGet, u, nil)
	if err != nil {
		return nil, http.StatusInternalServerError, err
	}
	resp, err := c.HTTP.Do(req)
	if err != nil {
		return nil, http.StatusInternalServerError, fmt.Errorf("error making request '%s': %v", u.String(), err)
	}
	defer resp.Body.Close()
	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		b, _ := io.ReadAll(io.LimitReader(resp.Body, 4<<10)) // <-- only return 4096 bytes of message
		return nil, resp.StatusCode, fmt.Errorf("http %d: %s", resp.StatusCode, string(b))
	}

	var respData types.AbsLibraryResponse
	err = json.NewDecoder(resp.Body).Decode(&respData)
	if err != nil {
		return nil, http.StatusInternalServerError, fmt.Errorf("audiobookshelf failed to decode json response data: %s", err)
	}
	return respData.Libraries, resp.StatusCode, nil
}

// ======================
// UTILS
// ======================

func (c *AbsClient) requestWithAuth(ctx context.Context, method string, u *url.URL, body io.Reader) (*http.Request, error) {
	r, err := request.NewRequest(ctx, method, u, body)
	if err != nil {
		return nil, err
	}
	// authorization header
	// see doc: https://www.audiobookshelf.org/guides/api-keys#authentication-header
	r.Header.Set("Authorization", fmt.Sprintf("Bearer %s", c.ApiKey))
	return r, nil
}

func (c *AbsClient) buildURL(parts []string, q url.Values) *url.URL {
	u := *c.BaseURL // copy
	u.Path, _ = url.JoinPath(c.BaseURL.Path, parts...)
	if q == nil {
		q = url.Values{}
	}
	u.RawQuery = q.Encode()
	return &u
}
