/* eslint-disable @typescript-eslint/no-unused-vars */
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
	return client.get<StatusResponse>('/status');
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
	return client.post<ApiResponse>('/start', config);
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
	return client.post<ApiResponse>('/stop');
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
 * await scanPaths(['/movies/New Movie (2024)', '/tv/New Show']);
 * ```
 */
export async function scanPaths(paths: string[]): Promise<ApiResponse> {
	const client = getApiClient();
	const request: ScanRequest = { paths };
	return client.post<ApiResponse>('/scan', request);
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
 * Note: This currently tests backend connectivity only.
 * For true Plex server validation, the backend would need a dedicated
 * /test-plex endpoint that validates credentials without starting the watcher.
 *
 * @param _serverUrl - Plex server URL (unused, kept for API compatibility)
 * @param _token - Plex authentication token (unused, kept for API compatibility)
 * @returns true if backend is reachable
 */
export async function testPlexConnection(_serverUrl: string, _token: string): Promise<boolean> {
	const client = getApiClient();
	const param = new URLSearchParams({ server_url: _serverUrl, token: _token });
	const endpoint = `/plex_test?${param.toString()}`;
	try {
		const isConnected = await client.get<boolean>(endpoint);
		return isConnected;
	} catch (error) {
		console.error('Plex connection test failed:', error);
		return false;
	}
}
