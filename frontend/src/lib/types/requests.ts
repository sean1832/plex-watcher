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
}

// get status response types
export interface StatusResponse {
	is_watching: boolean;
	paths: string[];
	server: string | null;
	cooldown: number;
}
