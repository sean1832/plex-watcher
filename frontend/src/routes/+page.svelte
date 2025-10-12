<script lang="ts">
	import PathManager from '$lib/components/PathManager.svelte';
	import type { WatchedPath } from '$lib/types/path-manager';
	import { Button } from '$lib/components/ui/button';
	import StatusIndicator from '$lib/components/StatusIndicator.svelte';
	import ManualScanner from '$lib/components/ManualScanner.svelte';

	let pathManager: PathManager;
	let paths = $state<WatchedPath[]>([
		{ id: crypto.randomUUID(), directory: '/media/movies', enabled: true },
		{ id: crypto.randomUUID(), directory: '/media/tv-shows', enabled: false }
	]);

	function handleUpdate(updatedPaths: WatchedPath[]) {
		console.log('Paths updated:', updatedPaths);
	}

	let connectionStatus = $state<'online' | 'offline' | 'connecting'>('online');
	let watchStatus = $state<'stopped' | 'watching' | 'error'>('stopped');

	function startWatching() {
		watchStatus = 'watching';
		// TODO: send command to backend to start watching
	}
	function stopWatching() {
		watchStatus = 'stopped';
		// TODO: send command to backend to stop watching
	}

	let disableStart = $derived(connectionStatus !== 'online')
	let disableStop = $derived(connectionStatus !== 'online')

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
					<StatusIndicator watchStatus={watchStatus} connectionStatus={connectionStatus}/>
				</div>
			</div>
			

			<PathManager bind:this={pathManager} bind:paths onUpdate={handleUpdate} />
		</div>
		
		<!-- Actions -->
		<div class="flex gap-2">
			<Button variant="default" onclick={startWatching} disabled={disableStart}>Start</Button>
			<Button variant="outline" onclick={stopWatching} disabled={disableStop}>Stop</Button>
		</div>

	</div>
</main>
