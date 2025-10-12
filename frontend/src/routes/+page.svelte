<script lang="ts">
	import { onMount } from 'svelte';
	import { config } from '$lib/stores/config.svelte';
	import { startWatcher, stopWatcher } from '$lib/api/endpoints';
	import { ApiError } from '$lib/api/client';
	import PathManager from '$lib/components/PathManager.svelte';
	import type { WatchedPath } from '$lib/types/path-manager';
	import { Button } from '$lib/components/ui/button';
	import StatusIndicator from '$lib/components/StatusIndicator.svelte';

	let pathManager: PathManager;
	
	// Convert config paths to WatchedPath format
	let paths = $state<WatchedPath[]>(
		config.watchedPaths.map(dir => ({
			id: crypto.randomUUID(),
			directory: dir,
			enabled: true
		}))
	);

	// Sync paths with config when they change
	function handleUpdate(updatedPaths: WatchedPath[]) {
		console.log('handleUpdate called with:', updatedPaths);
		
		// Extract enabled directories
		const enabledDirs = updatedPaths
			.filter(p => p.enabled)
			.map(p => p.directory);
		
		console.log('Enabled directories:', enabledDirs);
		
		// Update config (will auto-persist)
		config.watchedPaths = enabledDirs;
		
		// Update local paths state to trigger reactivity
		paths = updatedPaths;
	}

	let backendStatus = $state<'online' | 'offline' | 'connecting'>(
		config.backendStatus === 'unknown' ? 'connecting' : config.backendStatus
	);
	let plexStatus = $state<'online' | 'offline' | 'connecting'>(
		config.plexStatus === 'unknown' ? 'connecting' : config.plexStatus
	);
	let watchStatus = $state<'stopped' | 'watching' | 'error'>(
		config.isWatching ? 'watching' : 'stopped'
	);
	let isStarting = $state(false);
	let isStopping = $state(false);
	let isRefreshing = $state(false);
	let errorMessage = $state<string | null>(null);

	// Load initial status from backend
	onMount(async () => {
		isRefreshing = true;
		backendStatus = 'connecting';
		plexStatus = 'connecting';
		errorMessage = null;

		try {
			// Fetch backend status (including paths and watch status)
			const backendStatusResp = await config.loadFromBackend(true); // Force refresh
			if (backendStatusResp) {
				backendStatus = 'online';
				watchStatus = backendStatusResp.is_watching ? 'watching' : 'stopped';
				paths = backendStatusResp.paths.map(dir => ({
					id: crypto.randomUUID(),
					directory: dir,
					enabled: true
				}));
			} else {
				// Fallback to stored status if API fails but was previously known
				backendStatus = config.backendStatus === 'unknown' ? 'offline' : config.backendStatus;
			}

			// Independently fetch Plex status
			const plexStatusResp = await config.testPlex();
			plexStatus = plexStatusResp;

		} catch (error) {
			console.error('Failed to load initial status:', error);
			backendStatus = 'offline';
			plexStatus = 'offline';
			config.backendStatus = 'offline'; // Persist offline status
			config.plexStatus = 'offline';
			errorMessage = 'Failed to connect to services. Please check your configuration.';
		} finally {
			isRefreshing = false;
		}
	});

	async function startWatching() {
		if (!config.isValid()) {
			errorMessage = 'Please configure Plex server settings first';
			watchStatus = 'error';
			return;
		}

		isStarting = true;
		errorMessage = null;
		
		try {
			// Get enabled paths
			const enabledPaths = paths
				.filter(p => p.enabled)
				.map(p => p.directory);
			
			if (enabledPaths.length === 0) {
				errorMessage = 'Please add at least one directory to watch';
				watchStatus = 'error';
				return;
			}

			// Update config with current paths
			config.watchedPaths = enabledPaths;
			
			// Start watcher with complete configuration
			const response = await startWatcher(config.toStartRequest());
			
			if (response.status === 'success') {
				watchStatus = 'watching';
				backendStatus = 'online';
				
				// Force reload status to ensure sync
				await config.loadFromBackend(true);
			} else {
				errorMessage = response.message;
				watchStatus = 'error';
			}
		} catch (error) {
			console.error('Failed to start watcher:', error);
			
			if (error instanceof ApiError) {
				errorMessage = error.message;
				
				if (error.statusCode === 0) {
					backendStatus = 'offline';
				}
			} else {
				errorMessage = 'Failed to start watcher. Please check your configuration.';
			}
			
			watchStatus = 'error';
		} finally {
			isStarting = false;
		}
	}

	async function stopWatching() {
		isStopping = true;
		errorMessage = null;
		
		try {
			const response = await stopWatcher();
			
			if (response.status === 'success') {
				watchStatus = 'stopped';
				
				// Force reload status to ensure sync
				await config.loadFromBackend(true);
			} else {
				errorMessage = response.message;
				watchStatus = 'error';
			}
		} catch (error) {
			console.error('Failed to stop watcher:', error);
			
			if (error instanceof ApiError) {
				errorMessage = error.message;
				
				if (error.statusCode === 0) {
					backendStatus = 'offline';
				}
			} else {
				errorMessage = 'Failed to stop watcher.';
			}
			
			watchStatus = 'error';
		} finally {
			isStopping = false;
		}
	}

	async function refreshBackendStatus() {
		if (isRefreshing) return; // Prevent double-refresh
		
		isRefreshing = true;
		backendStatus = 'connecting';
		errorMessage = null;
		
		try {
			// Force reload status from backend (bypass cache)
			const status = await config.loadFromBackend(true);
			
			if (status) {
				backendStatus = 'online';
				watchStatus = status.is_watching ? 'watching' : 'stopped';
				
				// Update paths from backend
				paths = status.paths.map(dir => ({
					id: crypto.randomUUID(),
					directory: dir,
					enabled: true
				}));
				console.log('Backend status refreshed successfully');
			} else {
				backendStatus = config.backendStatus === 'unknown' ? 'offline' : config.backendStatus;
			}
		} catch (error) {
			console.error('Failed to refresh backend status:', error);
			backendStatus = 'offline';
			config.backendStatus = 'offline';
			errorMessage = 'Failed to refresh backend status. Please check your connection.';
		} finally {
			isRefreshing = false;
		}
	}

	async function refreshPlexStatus() {
		if (isRefreshing) return; // Prevent double-refresh
		
		isRefreshing = true;
		plexStatus = 'connecting';
		errorMessage = null;
		
		try {
			// Test Plex connection status
			const plexStatusResp = await config.testPlex();
			plexStatus = plexStatusResp;
			console.log('Plex status refreshed successfully:', plexStatusResp);
		} catch (error) {
			console.error('Failed to refresh Plex status:', error);
			plexStatus = 'offline';
			config.plexStatus = 'offline';
			errorMessage = 'Failed to refresh Plex status. Please check your connection.';
		} finally {
			isRefreshing = false;
		}
	}

	let disableStart = $derived(
		isStarting ||
		watchStatus === 'watching' ||
		backendStatus !== 'online' ||
		paths.filter(p => p.enabled).length === 0
	);
	
	let disableStop = $derived(
		isStopping ||
		watchStatus !== 'watching' ||
		backendStatus !== 'online'
	);

</script>


<main class="min-h-screen">
	<div class="container mx-auto max-w-7xl space-y-6 px-4 py-8">
		<!-- Header -->
		<div class="space-y-2">
			<h1 class="text-3xl font-bold tracking-tight">Plex Watcher</h1>
			<p class="text-muted-foreground">
				Manage watched directories and automatically update your Plex library
			</p>
		</div>

		<!-- Separator -->
		<hr class="border-t" />

		<!-- Path Manager Section -->
		<div class="space-y-4">
			<div class="flex items-center justify-between">
				<h2 class="text-xl font-semibold">Watched Directories</h2>
				<div class="flex gap-2">
					<!-- Status -->
					<StatusIndicator 
						watchStatus={watchStatus} 
						plexState={plexStatus}
						backendState={backendStatus} 
						onRefreshBackend={refreshBackendStatus}
						onRefreshPlex={refreshPlexStatus}
					/>
				</div>
			</div>
			
			{#if errorMessage}
				<div class="rounded-lg border border-red-200 bg-red-50 dark:border-red-900/50 dark:bg-red-900/10 p-4">
					<p class="text-sm text-red-800 dark:text-red-200">{errorMessage}</p>
				</div>
			{/if}

			<PathManager bind:this={pathManager} bind:paths onUpdate={handleUpdate} />
		</div>
		
		<!-- Actions -->
		<div class="flex gap-2">
			<Button variant="default" onclick={startWatching} disabled={disableStart}>
				{isStarting ? 'Starting...' : 'Start Watching'}
			</Button>
			<Button variant="outline" onclick={stopWatching} disabled={disableStop}>
				{isStopping ? 'Stopping...' : 'Stop Watching'}
			</Button>
		</div>

	</div>
</main>
