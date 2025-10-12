/**
 * Type definitions for PathManager component
 */

/**
 * Represents a watched directory path in the Plex-Watcher system
 */
export interface WatchedPath {
	/** Unique identifier for the path (typically a UUID) */
	id: string;

	/** Full filesystem path to the directory being watched */
	directory: string;

	/** Whether watching is enabled for this path */
	enabled: boolean;
}

/**
 * Props for the PathManager component
 */
export interface PathManagerProps {
	/** Initial paths to display (bindable) */
	paths?: WatchedPath[];

	/** Callback invoked when paths are updated */
	onUpdate?: (paths: WatchedPath[]) => void;
}

/**
 * PathManager component instance methods
 */
export interface PathManagerMethods {
	/** Get all current paths */
	getPaths(): WatchedPath[];

	/** Replace all paths with new array */
	setPaths(paths: WatchedPath[]): void;

	/** Remove all paths */
	clearPaths(): void;

	/** Add a single path programmatically */
	addPathProgrammatically(directory: string, enabled?: boolean): void;
}

/**
 * Helper type for creating new paths
 */
export type CreateWatchedPath = Omit<WatchedPath, 'id'>;

/**
 * Backend API response format for paths
 * (Based on Plex-Watcher API)
 */
export interface BackendPathsResponse {
	status: string;
	paths: string[];
	is_watching: boolean;
}

/**
 * Utility functions for working with WatchedPath objects
 */
export class WatchedPathUtils {
	/**
	 * Create a new WatchedPath with auto-generated ID
	 */
	static create(directory: string, enabled: boolean = true): WatchedPath {
		return {
			id: crypto.randomUUID(),
			directory: directory.trim(),
			enabled
		};
	}

	/**
	 * Convert backend API paths to WatchedPath format
	 */
	static fromBackendPaths(paths: string[]): WatchedPath[] {
		return paths.map((path) => this.create(path, true));
	}

	/**
	 * Convert WatchedPath array to backend API format (enabled paths only)
	 */
	static toBackendPaths(paths: WatchedPath[]): string[] {
		return paths.filter((p) => p.enabled).map((p) => p.directory);
	}

	/**
	 * Validate a path object
	 */
	static isValid(path: unknown): path is WatchedPath {
		if (typeof path !== 'object' || path === null) {
			return false;
		}

		const obj = path as Record<string, unknown>;
		return (
			typeof obj.id === 'string' &&
			typeof obj.directory === 'string' &&
			typeof obj.enabled === 'boolean'
		);
	}

	/**
	 * Export paths to JSON string
	 */
	static toJSON(paths: WatchedPath[]): string {
		return JSON.stringify(paths, null, 2);
	}

	/**
	 * Import paths from JSON string
	 */
	static fromJSON(json: string): WatchedPath[] {
		const parsed = JSON.parse(json);

		if (!Array.isArray(parsed)) {
			throw new Error('Invalid JSON: Expected an array');
		}

		const paths = parsed.filter((item) => this.isValid(item));

		if (paths.length !== parsed.length) {
			console.warn(`Filtered out ${parsed.length - paths.length} invalid paths`);
		}

		return paths;
	}

	/**
	 * Get only enabled paths
	 */
	static getEnabled(paths: WatchedPath[]): WatchedPath[] {
		return paths.filter((p) => p.enabled);
	}

	/**
	 * Get only disabled paths
	 */
	static getDisabled(paths: WatchedPath[]): WatchedPath[] {
		return paths.filter((p) => !p.enabled);
	}

	/**
	 * Toggle enable state for all paths
	 */
	static toggleAll(paths: WatchedPath[], enabled?: boolean): WatchedPath[] {
		const targetState = enabled ?? !paths.every((p) => p.enabled);
		return paths.map((p) => ({ ...p, enabled: targetState }));
	}

	/**
	 * Remove duplicate paths (by directory)
	 */
	static deduplicate(paths: WatchedPath[]): WatchedPath[] {
		const seen = new Set<string>();
		return paths.filter((path) => {
			if (seen.has(path.directory)) {
				return false;
			}
			seen.add(path.directory);
			return true;
		});
	}

	/**
	 * Sort paths alphabetically by directory
	 */
	static sort(paths: WatchedPath[]): WatchedPath[] {
		return [...paths].sort((a, b) => a.directory.localeCompare(b.directory));
	}

	/**
	 * Find path by ID
	 */
	static findById(paths: WatchedPath[], id: string): WatchedPath | undefined {
		return paths.find((p) => p.id === id);
	}

	/**
	 * Find path by directory
	 */
	static findByDirectory(paths: WatchedPath[], directory: string): WatchedPath | undefined {
		return paths.find((p) => p.directory === directory);
	}
}
