/**
 * API Endpoints - Type-safe functions for all backend API calls
 *
 * This module provides a clean interface to interact with the Plex-Watcher
 * backend API. Each function corresponds to an API endpoint and includes
 * proper TypeScript types for requests and responses.
 */

import { getApiClient, type ApiResponse } from './client';
import type { StartRequest, ScanRequest, StatusResponse } from '$lib/types/requests';

/**
 * Get current status of the Plex Watcher
 *
 * @returns Current watcher status including paths, server info, and state
 * @throws {ApiError} If request fails
 */
export async function getStatus(): Promise<StatusResponse> {
	const client = getApiClient();
	const response = await client.get<{ code: number; message: string; data: StatusResponse }>(
		'/status'
	);
	return response.data;
}

/**
 * Start the Plex Watcher with complete configuration
 *
 * This endpoint configures and starts the watcher in a single operation.
 * If the watcher is already running, it will be stopped and reconfigured.
 *
 * @param config - Complete watcher configuration
 * @returns Success/error response
 * @throws {ApiError} If configuration is invalid or startup fails
 *
 * @example
 * ```ts
 * await startWatcher({
 *   server_url: 'http://localhost:32400',
 *   token: 'your-plex-token',
 *   paths: ['/movies', '/tv'],
 *   cooldown: 30
 * });
 * ```
 */
export async function startWatcher(config: StartRequest): Promise<ApiResponse> {
	const client = getApiClient();
	const response = await client.post<{ code: number; message: string; data?: unknown }>(
		'/start',
		config
	);
	return {
		status: response.code >= 200 && response.code < 300 ? 'success' : 'error',
		message: response.message,
		data: response.data
	};
}

/**
 * Stop the Plex Watcher
 *
 * Stops watching directories and shuts down the file observer.
 * Configuration is preserved and can be restarted later.
 *
 * @returns Success/error response
 * @throws {ApiError} If stop operation fails
 */
export async function stopWatcher(): Promise<ApiResponse> {
	const client = getApiClient();
	const response = await client.post<{ code: number; message: string; data?: unknown }>('/stop');
	return {
		status: response.code >= 200 && response.code < 300 ? 'success' : 'error',
		message: response.message,
		data: response.data
	};
}

/**
 * Manually scan specific directories
 *
 * Triggers an immediate Plex library scan for the specified paths.
 * Useful for manual refresh without waiting for file changes.
 *
 * @param paths - Array of directory paths to scan
 * @returns Success/error response with details of any failures
 * @throws {ApiError} If scan request fails
 *
 * @example
 * ```ts
 * await scanPaths({ paths: ['/movies', '/tv'], server_url: 'http://localhost:32400', token: 'your-plex-token' });
 * ```
 */
export async function scanPaths(config: ScanRequest): Promise<ApiResponse> {
	// Ensure paths array is provided
	if (!config.paths || config.paths.length === 0) {
		throw new Error('At least one path must be specified for scanning.');
	}
	const client = getApiClient();
	const response = await client.post<{ code: number; message: string; data?: unknown }>(
		'/scan',
		config
	);
	return {
		status: response.code >= 200 && response.code < 300 ? 'success' : 'error',
		message: response.message,
		data: response.data
	};
}

/**
 * Test backend connectivity
 *
 * Lightweight health check to verify the backend is reachable.
 * Does not require authentication or configuration.
 *
 * @returns true if backend is reachable, false otherwise
 */
export async function testBackendConnection(): Promise<boolean> {
	const client = getApiClient();
	return client.healthCheck();
}

/**
 * Test Plex server connectivity
 *
 * Tests if the Plex server is reachable and credentials are valid by fetching library sections.
 *
 * @param serverUrl - Plex server URL
 * @param token - Plex authentication token
 * @returns true if Plex server is reachable and credentials are valid
 */
export async function testPlexConnection(serverUrl: string, token: string): Promise<boolean> {
	const client = getApiClient();
	const params = new URLSearchParams({ server_url: serverUrl, token: token });
	const endpoint = `/prob-plex?${params.toString()}`;
	try {
		const response = await client.get<{ code: number; message: string; data: unknown }>(endpoint);
		// Consider it successful if we get a 2xx response with data
		return response.code >= 200 && response.code < 300 && response.data !== null;
	} catch (error) {
		console.error('Plex connection test failed:', error);
		return false;
	}
}
