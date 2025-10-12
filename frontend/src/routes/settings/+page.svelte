<script lang="ts">
	import { config } from '$lib/stores/config.svelte';
	import { testBackendConnection, testPlexConnection } from '$lib/api/endpoints';
	import Button from "$lib/components/ui/button/button.svelte";
	import Input from "$lib/components/ui/input/input.svelte";
	import Separator from "$lib/components/ui/separator/separator.svelte";
	import RefreshIcon from '@lucide/svelte/icons/refresh-cw';
	import ServerIcon from '@lucide/svelte/icons/server';
	import KeyIcon from '@lucide/svelte/icons/key';
	import TimerIcon from '@lucide/svelte/icons/timer';
	import DatabaseIcon from '@lucide/svelte/icons/database';
	import CheckIcon from '@lucide/svelte/icons/check';
	import XIcon from '@lucide/svelte/icons/x';

	// Local state bound to inputs
	let backendUrl = $state(config.backendUrl);
	let plexServerUrl = $state(config.plexServerUrl);
	let plexToken = $state(config.plexToken);
	let cooldownInterval = $state(config.cooldownInterval);
	
	// Test states
	let isTestingBackend = $state(false);
	let backendTestResult = $state<'success' | 'error' | null>(null);
	
	let isTestingPlex = $state(false);
	let plexTestResult = $state<'success' | 'error' | null>(null);
	
	// Save state
	let isSaving = $state(false);
	let saveSuccess = $state(false);

	async function testBackend() {
		isTestingBackend = true;
		backendTestResult = null;
		
		try {
			// Create a temporary API client for testing without affecting global state
			const { createApiClient } = await import('$lib/api/client');
			const tempClient = createApiClient({ baseUrl: backendUrl });
			
			// Use the temporary client to test connectivity
			const result = await tempClient.healthCheck();
			backendTestResult = result ? 'success' : 'error';
		} catch {
			backendTestResult = 'error';
		} finally {
			isTestingBackend = false;
		}
	}

	async function testPlex() {
		isTestingPlex = true;
		plexTestResult = null;
		
		try {
			const result = await testPlexConnection(plexServerUrl, plexToken);
			plexTestResult = result ? 'success' : 'error';
		} catch {
			plexTestResult = 'error';
		} finally {
			isTestingPlex = false;
		}
	}

	async function saveSettings() {
		isSaving = true;
		saveSuccess = false;
		
		try {
			// Check if backend URL changed
			const urlChanged = backendUrl !== config.backendUrl;
			
			// Update config store (automatically persists to localStorage)
			config.backendUrl = backendUrl;
			config.plexServerUrl = plexServerUrl;
			config.plexToken = plexToken;
			config.cooldownInterval = cooldownInterval;
			
			// If backend URL changed, force refresh connection status
			if (urlChanged) {
				await config.loadFromBackend(true);
			}
			
			saveSuccess = true;
			
			// Clear success message after 3 seconds
			setTimeout(() => {
				saveSuccess = false;
			}, 3000);
		} finally {
			isSaving = false;
		}
	}

	function cancel() {
		// Reset to current config values
		backendUrl = config.backendUrl;
		plexServerUrl = config.plexServerUrl;
		plexToken = config.plexToken;
		cooldownInterval = config.cooldownInterval;
		
		// Navigate back
		window.location.href = '/';
	}
	
	// Check if there are unsaved changes
	let hasChanges = $derived(
		backendUrl !== config.backendUrl ||
		plexServerUrl !== config.plexServerUrl ||
		plexToken !== config.plexToken ||
		cooldownInterval !== config.cooldownInterval
	);
</script>

<main class="min-h-screen bg-background">
	<div class="container mx-auto max-w-7xl px-4 py-8 space-y-8">
		<!-- Header -->
		<div class="space-y-1">
			<h1 class="text-4xl font-bold tracking-tight">Settings</h1>
			<p class="text-muted-foreground">
				Configure your Plex-Watcher backend and Plex Media Server connections
			</p>
		</div>

		<Separator />

		<!-- Settings Cards -->
		<div class="grid gap-6">
			<!-- Backend Configuration Card -->
			<div class="rounded-lg border bg-card p-6 shadow-sm">
				<div class="flex items-center gap-3 mb-6">
					<div class="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
						<DatabaseIcon class="h-5 w-5 text-primary" />
					</div>
					<div>
						<h2 class="text-xl font-semibold">Backend Configuration</h2>
						<p class="text-sm text-muted-foreground">Connect to the Plex-Watcher backend API</p>
					</div>
				</div>

				<div class="space-y-4">
					<div class="space-y-2">
						<label for="backend-url" class="text-sm font-medium leading-none">
							Backend API URL
						</label>
						<div class="flex gap-2">
							<Input
								id="backend-url"
								type="url"
								bind:value={backendUrl}
								placeholder="http://localhost:8000"
								class="flex-1"
							/>
							<Button
								variant="secondary"
								size="icon"
								onclick={testBackend}
								disabled={isTestingBackend}
							>
								<RefreshIcon class={`h-4 w-4 ${isTestingBackend ? 'animate-spin' : ''}`} />
								<span class="sr-only">Test Connection</span>
							</Button>
							{#if backendTestResult === 'success'}
								<div class="flex items-center justify-center w-10 h-10 rounded-md bg-green-100 dark:bg-green-900/20">
									<CheckIcon class="h-4 w-4 text-green-600 dark:text-green-400" />
								</div>
							{:else if backendTestResult === 'error'}
								<div class="flex items-center justify-center w-10 h-10 rounded-md bg-red-100 dark:bg-red-900/20">
									<XIcon class="h-4 w-4 text-red-600 dark:text-red-400" />
								</div>
							{/if}
						</div>
						<p class="text-xs text-muted-foreground">
							The URL where your Plex-Watcher backend service is running
						</p>
					</div>
				</div>
			</div>

			<!-- Plex Server Configuration Card -->
			<div class="rounded-lg border bg-card p-6 shadow-sm">
				<div class="flex items-center gap-3 mb-6">
					<div class="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
						<ServerIcon class="h-5 w-5 text-primary" />
					</div>
					<div>
						<h2 class="text-xl font-semibold">Plex Media Server</h2>
						<p class="text-sm text-muted-foreground">Configure your Plex server connection</p>
					</div>
				</div>

				<div class="space-y-4">
					<div class="space-y-2">
						<label for="plex-server" class="text-sm font-medium leading-none">
							Server URL
						</label>
						<div class="flex gap-2">
							<Input
								id="plex-server"
								type="url"
								bind:value={plexServerUrl}
								placeholder="http://localhost:32400"
								class="flex-1"
							/>
							<Button
								variant="secondary"
								size="icon"
								onclick={testPlex}
								disabled={isTestingPlex || !plexToken}
							>
								<RefreshIcon class={`h-4 w-4 ${isTestingPlex ? 'animate-spin' : ''}`} />
								<span class="sr-only">Test Connection</span>
							</Button>
							{#if plexTestResult === 'success'}
								<div class="flex items-center justify-center w-10 h-10 rounded-md bg-green-100 dark:bg-green-900/20">
									<CheckIcon class="h-4 w-4 text-green-600 dark:text-green-400" />
								</div>
							{:else if plexTestResult === 'error'}
								<div class="flex items-center justify-center w-10 h-10 rounded-md bg-red-100 dark:bg-red-900/20">
									<XIcon class="h-4 w-4 text-red-600 dark:text-red-400" />
								</div>
							{/if}
						</div>
						<p class="text-xs text-muted-foreground">
							The URL of your Plex Media Server (e.g., http://localhost:32400)
						</p>
					</div>

					<div class="space-y-2">
						<label for="plex-token" class="text-sm font-medium leading-none flex items-center gap-2">
							<KeyIcon class="h-4 w-4" />
							Authentication Token
						</label>
						<Input
							id="plex-token"
							type="password"
							bind:value={plexToken}
							placeholder="Enter your Plex token"
						/>
						<p class="text-xs text-muted-foreground">
							Required for API authentication. Find your token in Plex settings or server logs
						</p>
					</div>
				</div>
			</div>

			<!-- Watcher Configuration Card -->
			<div class="rounded-lg border bg-card p-6 shadow-sm">
				<div class="flex items-center gap-3 mb-6">
					<div class="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
						<TimerIcon class="h-5 w-5 text-primary" />
					</div>
					<div>
						<h2 class="text-xl font-semibold">Watcher Settings</h2>
						<p class="text-sm text-muted-foreground">Fine-tune the file watcher behavior</p>
					</div>
				</div>

				<div class="space-y-4">
					<div class="space-y-2">
						<label for="cooldown-interval" class="text-sm font-medium leading-none">
							Cooldown Interval (seconds)
						</label>
						<div class="flex items-center gap-4">
							<Input
								id="cooldown-interval"
								type="number"
								bind:value={cooldownInterval}
								min="5"
								max="300"
								placeholder="10"
								class="w-32"
							/>
						</div>
						<p class="text-xs text-muted-foreground">
							Delay after file changes before triggering Plex scan (5-300 seconds recommended)
						</p>
					</div>
				</div>
			</div>
		</div>

		<!-- Action Buttons -->
		<div class="flex justify-between items-center gap-3 pt-4">
			{#if saveSuccess}
				<div class="flex items-center gap-2 text-sm text-green-600 dark:text-green-400">
					<CheckIcon class="h-4 w-4" />
					<span>Settings saved successfully</span>
				</div>
			{:else}
				<div></div>
			{/if}
			
			<div class="flex gap-3">
				<Button variant="outline" onclick={cancel}>
					Cancel
				</Button>
				<Button onclick={saveSettings} disabled={isSaving || !hasChanges}>
					{isSaving ? 'Saving...' : 'Save Settings'}
				</Button>
			</div>
		</div>
	</div>
</main>