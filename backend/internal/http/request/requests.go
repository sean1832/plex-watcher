package request

import (
	"context"
	"fmt"
	"io"
	"net/http"
	"net/url"
)

func NewRequest(ctx context.Context, method string, u *url.URL, body io.Reader) (*http.Request, error) {
	req, err := http.NewRequestWithContext(ctx, method, u.String(), body)
	if err != nil {
		return nil, fmt.Errorf("error making request context: %v", err)
	}
	req.Header.Set("User-Agent", "MediaWatcher/1.0")

	// accept response as JSON
	req.Header.Set("accept", "application/json")

	return req, nil
}