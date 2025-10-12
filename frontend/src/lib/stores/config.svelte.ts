/**
 * Configuration Store - Reactive state management with persistence
 *
 * This store manages application configuration using Svelte 5 runes for
 * reactivity and localStorage for persistence across sessions.
 *
 * Usage:
 * ```ts
 * import { config } from '$lib/stores/config.svelte';
 *
 * // Read values
 * console.log(config.backendUrl);
 *
 * // Update values (automatically persists)
 * config.backendUrl = 'http://new-backend:8000';
 *
 * // Load from backend
 * await config.loadFromBackend();
 * ```
 */

import { configureApiClient } from '$lib/api/client';
import { getStatus } from '$lib/api/endpoints';
import type { StatusResponse } from '$lib/types/requests';

interface ConfigState {
	// Backend connection
	backendUrl: string;

	// Plex server settings
	plexServerUrl: string;
	plexToken: string;

	// Watcher settings
	cooldownInterval: number;
	watchedPaths: string[];

	// Runtime state (not persisted)
	isWatching: boolean;
	lastSync: Date | null;

	// Connection cache (not persisted)
	connectionStatus: 'online' | 'offline' | 'unknown';
	lastBackendUrl: string | null;
}

const DEFAULT_CONFIG: ConfigState = {
	backendUrl: 'http://localhost:8000',
	plexServerUrl: 'http://localhost:32400',
	plexToken: '',
	cooldownInterval: 30,
	watchedPaths: [],
	isWatching: false,
	lastSync: null,
	connectionStatus: 'unknown',
	lastBackendUrl: null
};

const STORAGE_KEY = 'plex-watcher-config';
const PERSISTED_KEYS: (keyof ConfigState)[] = [
	'backendUrl',
	'plexServerUrl',
	'plexToken',
	'cooldownInterval',
	'watchedPaths'
];

/**
 * Load configuration from localStorage
 */
function loadFromStorage(): Partial<ConfigState> {
	if (typeof window === 'undefined') return {};

	try {
		const stored = localStorage.getItem(STORAGE_KEY);
		if (!stored) return {};

		return JSON.parse(stored);
	} catch (error) {
		console.error('Failed to load config from localStorage:', error);
		return {};
	}
}

/**
 * Save configuration to localStorage
 */
function saveToStorage(state: ConfigState) {
	if (typeof window === 'undefined') return;

	try {
		// Only persist specific keys
		const toPersist: Record<string, unknown> = {};
		for (const key of PERSISTED_KEYS) {
			toPersist[key] = state[key];
		}

		localStorage.setItem(STORAGE_KEY, JSON.stringify(toPersist));
	} catch (error) {
		console.error('Failed to save config to localStorage:', error);
	}
}

/**
 * Create the reactive configuration store
 */
function createConfigStore() {
	// Initialize state with defaults + localStorage
	const initialState = { ...DEFAULT_CONFIG, ...loadFromStorage() };
	let state = $state<ConfigState>(initialState);

	// Configure API client with initial backend URL
	configureApiClient({ baseUrl: state.backendUrl });

	return {
		// Reactive getters
		get backendUrl() {
			return state.backendUrl;
		},
		get plexServerUrl() {
			return state.plexServerUrl;
		},
		get plexToken() {
			return state.plexToken;
		},
		get cooldownInterval() {
			return state.cooldownInterval;
		},
		get watchedPaths() {
			return state.watchedPaths;
		},
		get isWatching() {
			return state.isWatching;
		},
		get lastSync() {
			return state.lastSync;
		},
		get connectionStatus() {
			return state.connectionStatus;
		},

		// Reactive setters (with auto-persistence)
		set backendUrl(value: string) {
			state.backendUrl = value;
			configureApiClient({ baseUrl: value });
			saveToStorage(state);
		},

		set plexServerUrl(value: string) {
			state.plexServerUrl = value;
			saveToStorage(state);
		},

		set plexToken(value: string) {
			state.plexToken = value;
			saveToStorage(state);
		},

		set cooldownInterval(value: number) {
			state.cooldownInterval = Math.max(5, Math.min(300, value));
			saveToStorage(state);
		},

		set watchedPaths(value: string[]) {
			state.watchedPaths = value;
			saveToStorage(state);
		},

		set isWatching(value: boolean) {
			state.isWatching = value;
			// Don't persist runtime state
		},

		set lastSync(value: Date | null) {
			state.lastSync = value;
			// Don't persist runtime state
		},

		set connectionStatus(value: 'online' | 'offline' | 'unknown') {
			state.connectionStatus = value;
			// Don't persist runtime state
		},

		/**
		 * Check if backend URL has changed since last check
		 */
		hasBackendUrlChanged(): boolean {
			return state.lastBackendUrl !== state.backendUrl;
		},

		/**
		 * Load current configuration from backend
		 * Updates local state to match backend reality
		 *
		 * @param force - Force refresh even if cached
		 */
		async loadFromBackend(force = false): Promise<StatusResponse | null> {
			// Skip if we have a cached connection and URL hasn't changed
			if (!force && state.connectionStatus === 'online' && !this.hasBackendUrlChanged()) {
				console.log('Using cached connection status');
				return null;
			}

			try {
				const status = await getStatus();

				// Update local state
				state.isWatching = status.is_watching;
				state.watchedPaths = status.paths;
				state.plexServerUrl = status.server || state.plexServerUrl;
				state.cooldownInterval = status.cooldown || state.cooldownInterval;
				state.lastSync = new Date();
				state.connectionStatus = 'online';
				state.lastBackendUrl = state.backendUrl;

				// Persist updated paths
				saveToStorage(state);

				return status;
			} catch (error) {
				console.error('Failed to load config from backend:', error);
				state.connectionStatus = 'offline';
				state.lastBackendUrl = state.backendUrl;
				return null;
			}
		},

		/**
		 * Reset configuration to defaults
		 */
		reset() {
			state = { ...DEFAULT_CONFIG };
			saveToStorage(state);
			configureApiClient({ baseUrl: DEFAULT_CONFIG.backendUrl });
		},

		/**
		 * Get all configuration as plain object (for API calls)
		 */
		toStartRequest() {
			return {
				server_url: state.plexServerUrl,
				token: state.plexToken,
				paths: state.watchedPaths,
				cooldown: state.cooldownInterval
			};
		},

		/**
		 * Check if configuration is valid for starting
		 */
		isValid(): boolean {
			return !!(
				state.plexServerUrl &&
				state.plexToken &&
				state.watchedPaths.length > 0 &&
				state.cooldownInterval >= 5 &&
				state.cooldownInterval <= 300
			);
		}
	};
}

/**
 * Global configuration store instance
 */
export const config = createConfigStore();
