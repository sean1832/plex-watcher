<script lang="ts">
	import { Button } from "$lib/components/ui/button";
	import { Input } from "$lib/components/ui/input";
	import { Checkbox } from "$lib/components/ui/checkbox";
	import * as Table from "$lib/components/ui/table";
	import TrashIcon from "@lucide/svelte/icons/trash-2";
	import PlusIcon from "@lucide/svelte/icons/plus";
	import FolderIcon from "@lucide/svelte/icons/folder";
	import type { WatchedPath } from "$lib/types/path-manager";

	interface Props {
		/** Initial paths to display in the grid */
		paths?: WatchedPath[];
		/** Callback when paths are updated */
		onUpdate?: (paths: WatchedPath[]) => void;
	}

	let { paths = $bindable([]), onUpdate }: Props = $props();

	// Internal state for managing paths
	let pathsState = $state<WatchedPath[]>(paths);
	let newPath = $state("");
	let editingId = $state<string | null>(null);
	let editingValue = $state("");

	// Sync external paths prop with internal state
	$effect(() => {
		pathsState = [...paths];
	});

	// Notify parent when paths change
	function notifyUpdate() {
		if (onUpdate) {
			onUpdate([...pathsState]);
		}
	}

	// Add new path
	function addPath() {
		if (!newPath.trim()) return;

		const newPathObj: WatchedPath = {
			id: crypto.randomUUID(),
			directory: newPath.trim(),
			enabled: true,
		};

		pathsState = [...pathsState, newPathObj];
		newPath = "";
		notifyUpdate();
	}

	// Remove path by id
	function removePath(id: string) {
		pathsState = pathsState.filter((p) => p.id !== id);
		notifyUpdate();
	}

	// Toggle enabled state
	function toggleEnabled(id: string) {
		pathsState = pathsState.map((p) => (p.id === id ? { ...p, enabled: !p.enabled } : p));
		notifyUpdate();
	}

	// Start editing a path
	function startEdit(id: string, currentPath: string) {
		editingId = id;
		editingValue = currentPath;
	}

	// Save edited path
	function saveEdit(id: string) {
		if (!editingValue.trim()) {
			cancelEdit();
			return;
		}

		pathsState = pathsState.map((p) => (p.id === id ? { ...p, directory: editingValue.trim() } : p));
		editingId = null;
		editingValue = "";
		notifyUpdate();
	}

	// Cancel editing
	function cancelEdit() {
		editingId = null;
		editingValue = "";
	}

	// Handle keyboard events for editing
	function handleEditKeydown(e: KeyboardEvent, id: string) {
		if (e.key === "Enter") {
			saveEdit(id);
		} else if (e.key === "Escape") {
			cancelEdit();
		}
	}

	// Handle keyboard event for adding new path
	function handleAddKeydown(e: KeyboardEvent) {
		if (e.key === "Enter") {
			addPath();
		}
	}

	// Public API: Get all paths
	export function getPaths(): WatchedPath[] {
		return [...pathsState];
	}

	// Public API: Set paths
	export function setPaths(newPaths: WatchedPath[]) {
		pathsState = [...newPaths];
		notifyUpdate();
	}

	// Public API: Clear all paths
	export function clearPaths() {
		pathsState = [];
		notifyUpdate();
	}

	// Public API: Add a single path programmatically
	export function addPathProgrammatically(directory: string, enabled: boolean = true) {
		const newPathObj: WatchedPath = {
			id: crypto.randomUUID(),
			directory: directory.trim(),
			enabled,
		};
		pathsState = [...pathsState, newPathObj];
		notifyUpdate();
	}
</script>

<div class="space-y-4">
	<!-- Add new path section -->
	<div class="flex gap-2">
		<div class="relative flex-1">
			<FolderIcon class="text-muted-foreground pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2" />
			<Input
				bind:value={newPath}
				placeholder="Enter directory path (e.g., /media/movies)"
				class="pl-9"
				onkeydown={handleAddKeydown}
			/>
		</div>
		<Button onclick={addPath} disabled={!newPath.trim()}>
			<PlusIcon />
			Add Path
		</Button>
	</div>

	<!-- Paths table -->
	<div class="border-border rounded-md border">
		<Table.Root>
			<Table.Header>
				<Table.Row>
					<Table.Head class="w-[80px]">
						<div class="ml-2">
							Enabled
						</div>
					</Table.Head>
					<Table.Head>Directory</Table.Head>
					<Table.Head class="w-[100px] text-right">
						<div class="mr-2">
							Actions
						</div>
					</Table.Head>
				</Table.Row>
			</Table.Header>
			<Table.Body>
				{#if pathsState.length === 0}
					<Table.Row>
						<Table.Cell colspan={3} class="text-muted-foreground h-32 text-center">
							No watched paths configured. Add a directory to get started.
						</Table.Cell>
					</Table.Row>
				{:else}
					{#each pathsState as path (path.id)}
						<Table.Row>
							<Table.Cell>
								<div class="ml-2">
									<Checkbox
										checked={path.enabled}
										onCheckedChange={() => toggleEnabled(path.id)}
										aria-label="Enable watching this path"
										class="cursor-pointer"
									/>
								</div>
							</Table.Cell>
							<Table.Cell class="font-mono text-sm">
								{#if editingId === path.id}
									<Input
										bind:value={editingValue}
										onkeydown={(e) => handleEditKeydown(e, path.id)}
										onblur={() => saveEdit(path.id)}
										class="font-mono text-sm"
										autofocus
									/>
								{:else}
									<button
										class="hover:text-foreground text-muted-foreground w-full cursor-pointer text-left transition-colors"
										onclick={() => startEdit(path.id, path.directory)}
										title="Click to edit"
									>
										{path.directory}
									</button>
								{/if}
							</Table.Cell>
							<Table.Cell class="text-right">
								<Button
									variant="ghost"
									size="icon-sm"
									onclick={() => removePath(path.id)}
									aria-label="Remove path"
								>
									<TrashIcon class="text-destructive size-4" />
								</Button>
							</Table.Cell>
						</Table.Row>
					{/each}
				{/if}
			</Table.Body>
		</Table.Root>
	</div>

	<!-- Summary -->
	{#if pathsState.length > 0}
		<div class="text-muted-foreground text-sm">
			Total: {pathsState.length} {pathsState.length === 1 ? "path" : "paths"}
			({pathsState.filter((p) => p.enabled).length} enabled)
		</div>
	{/if}
</div>
