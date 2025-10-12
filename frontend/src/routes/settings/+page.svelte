<script lang="ts">
	import Button from "$lib/components/ui/button/button.svelte";
	import Input from "$lib/components/ui/input/input.svelte";
	import Separator from "$lib/components/ui/separator/separator.svelte";
	import RefreshIcon from '@lucide/svelte/icons/refresh-cw';
	import ServerIcon from '@lucide/svelte/icons/server';
	import KeyIcon from '@lucide/svelte/icons/key';
	import TimerIcon from '@lucide/svelte/icons/timer';
	import DatabaseIcon from '@lucide/svelte/icons/database';

	let backendUrl = $state('http://localhost:8000');
	let plexServerUrl = $state('http://localhost:32400');
	let plexToken = $state('');
	let cooldownInterval = $state(10);
	let isTestingBackend = $state(false);
	let isTestingPlex = $state(false);

	function testBackendConnection() {
		isTestingBackend = true;
		// TODO: Implement actual API call
		setTimeout(() => {
			isTestingBackend = false;
		}, 1000);
	}

	function testPlexConnection() {
		isTestingPlex = true;
		// TODO: Implement actual API call
		setTimeout(() => {
			isTestingPlex = false;
		}, 1000);
	}

	function saveSettings() {
		// TODO: Implement save functionality (cookies)
		console.log('Settings saved:', { backendUrl, plexServerUrl, plexToken, cooldownInterval });
	}
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
								onclick={testBackendConnection}
								disabled={isTestingBackend}
							>
								<RefreshIcon class={`h-4 w-4 ${isTestingBackend ? 'animate-spin' : ''}`} />
								<span class="sr-only">Test Connection</span>
							</Button>
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
								onclick={testPlexConnection}
								disabled={isTestingPlex || !plexToken}
							>
								<RefreshIcon class={`h-4 w-4 ${isTestingPlex ? 'animate-spin' : ''}`} />
								<span class="sr-only">Test Connection</span>
							</Button>
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
		<div class="flex justify-end gap-3 pt-4">
			<Button variant="outline" onclick={() => window.location.href = '/'}>
				Cancel
			</Button>
			<Button onclick={saveSettings}>
				Save Settings
			</Button>
		</div>
	</div>
</main>