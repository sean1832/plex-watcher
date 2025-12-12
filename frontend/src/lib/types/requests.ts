// start request types
export interface StartRequest {
	server_url: string;
	token: string;
	paths: string[];
	cooldown: number;
}

// scan request types
export interface ScanRequest {
	paths: string[];
	server_url: string;
	token: string;
}

// get status response types
export interface StatusResponse {
	is_watching: boolean;
	paths: string[];
	server: string | null;
	cooldown: number;
}

// cached watchlist response types
export interface WatchlistCache {
	paths: string[];
	cooldown: number;
}
