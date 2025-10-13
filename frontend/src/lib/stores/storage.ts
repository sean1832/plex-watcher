export function createStorage<T>(key: string, defaultValue: T, debounceMs = 200) {
	let currentValue: T = defaultValue;
	let saveTimer: number | undefined;

	// load existing value from localStorage
	if (typeof window !== 'undefined') {
		try {
			const stored = localStorage.getItem(key);
			if (stored !== null) {
				currentValue = JSON.parse(stored) as T;
			}
		} catch (error) {
			console.error(`Failed to load ${key} from localStorage:`, error);
		}
	}

	function get(): T {
		return currentValue;
	}

	function set(value: T) {
		currentValue = value;
		// Debounce saving to localStorage
		if (typeof window !== 'undefined') {
			clearTimeout(saveTimer);
			saveTimer = window.setTimeout(() => {
				try {
					localStorage.setItem(key, JSON.stringify(currentValue));
				} catch (error) {
					console.error(`Failed to save ${key} to localStorage:`, error);
				}
			}, debounceMs);
		}
	}

	function clear(): void {
		currentValue = defaultValue;
		if (typeof window !== 'undefined') {
			try {
				localStorage.removeItem(key);
			} catch (error) {
				console.error(`Failed to remove ${key} from localStorage:`, error);
			}
		}
	}
	return { get, set, clear };
}
