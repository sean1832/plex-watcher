/**
 * API Client - Centralized HTTP client for backend communication
 *
 * This module provides a type-safe, maintainable wrapper around fetch API
 * with automatic error handling, request/response transformation, and
 * configuration management.
 */

export interface ApiResponse<T = unknown> {
	status: 'success' | 'error';
	message: string;
	data?: T;
	details?: string[];
}

export class ApiError extends Error {
	constructor(
		message: string,
		public statusCode?: number,
		public details?: string[]
	) {
		super(message);
		this.name = 'ApiError';
	}

	toString() {
		const parts = [this.message, this.details?.join('; ')].filter(Boolean);
		return `${this.name}${this.statusCode ? ` ${this.statusCode}` : ''}: ${parts.join(' | ')}`;
	}
}

export interface ApiClientConfig {
	baseUrl: string;
	timeout?: number;
	headers?: Record<string, string>;
}

/**
 * Create a configured API client instance
 */
export function createApiClient(config: ApiClientConfig) {
	const { baseUrl, timeout = 10000, headers = {} } = config;

	/**
	 * Generic fetch wrapper with error handling and timeout
	 */
	async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
		const controller = new AbortController();
		const timeoutId = setTimeout(() => controller.abort(), timeout);

		try {
			const url = `${baseUrl}${endpoint}`;
			const response = await fetch(url, {
				...options,
				signal: controller.signal,
				headers: {
					'Content-Type': 'application/json',
					...headers,
					...options.headers
				}
			});

			clearTimeout(timeoutId);

			// Handle HTTP errors
			if (!response.ok) {
				const errorText = await response.text();
				let errorMessage = `HTTP ${response.status}: ${response.statusText}`;

				try {
					const errorJson = JSON.parse(errorText);
					errorMessage = errorJson.message || errorJson.detail || errorMessage;
				} catch {
					// If not JSON, use raw text
					if (errorText) errorMessage = errorText;
				}

				throw new ApiError(errorMessage, response.status);
			}

			// Parse JSON response
			const data = await response.json();
			return data as T;
		} catch (error) {
			clearTimeout(timeoutId);

			// Handle abort (timeout)
			if (error instanceof DOMException && error.name === 'AbortError') {
				throw new ApiError('Request timeout', 408);
			}

			// Handle network errors
			if (error instanceof TypeError) {
				throw new ApiError('Network error - unable to reach server', 0);
			}

			// Re-throw ApiError as-is
			if (error instanceof ApiError) {
				throw error;
			}

			// Unknown error
			throw new ApiError(error instanceof Error ? error.message : 'Unknown error occurred');
		}
	}

	return {
		/**
		 * GET request
		 */
		async get<T>(endpoint: string, options?: RequestInit): Promise<T> {
			return request<T>(endpoint, { ...options, method: 'GET' });
		},

		/**
		 * POST request with JSON body
		 */
		async post<T>(endpoint: string, body?: unknown, options?: RequestInit): Promise<T> {
			return request<T>(endpoint, {
				...options,
				method: 'POST',
				body: body ? JSON.stringify(body) : undefined
			});
		},

		/**
		 * PUT request with JSON body
		 */
		async put<T>(endpoint: string, body?: unknown, options?: RequestInit): Promise<T> {
			return request<T>(endpoint, {
				...options,
				method: 'PUT',
				body: body ? JSON.stringify(body) : undefined
			});
		},

		/**
		 * DELETE request
		 */
		async delete<T>(endpoint: string, options?: RequestInit): Promise<T> {
			return request<T>(endpoint, { ...options, method: 'DELETE' });
		},

		/**
		 * Health check - lightweight test of backend connectivity
		 */
		async healthCheck(): Promise<boolean> {
			try {
				await request('/status', { method: 'GET' });
				return true;
			} catch {
				return false;
			}
		}
	};
}

/**
 * Default API client instance (can be reconfigured)
 * Uses browser localStorage to persist baseUrl
 */
let apiClient = createApiClient({
	baseUrl:
		typeof window !== 'undefined'
			? localStorage.getItem('backend_url') || 'http://localhost:8000'
			: 'http://localhost:8000'
});

/**
 * Get the current API client instance
 */
export function getApiClient() {
	return apiClient;
}

/**
 * Reconfigure the API client (e.g., when user changes backend URL)
 */
export function configureApiClient(config: Partial<ApiClientConfig>) {
	const currentBaseUrl =
		typeof window !== 'undefined'
			? localStorage.getItem('backend_url') || 'http://localhost:8000'
			: 'http://localhost:8000';

	apiClient = createApiClient({
		baseUrl: config.baseUrl || currentBaseUrl,
		timeout: config.timeout,
		headers: config.headers
	});

	// Persist to localStorage
	if (typeof window !== 'undefined' && config.baseUrl) {
		localStorage.setItem('backend_url', config.baseUrl);
	}

	return apiClient;
}
