<script lang="ts">
  import CircleXIcon from '@lucide/svelte/icons/circle-x';
  import CircleCheckIcon from '@lucide/svelte/icons/circle-check';
  import Loader2Icon from '@lucide/svelte/icons/loader-2';
  import AlertTriangleIcon from '@lucide/svelte/icons/alert-triangle';
  import CircleDotIcon from '@lucide/svelte/icons/circle-dot';
  import CircleIcon from '@lucide/svelte/icons/circle';
	import Button from './ui/button/button.svelte';

  interface Props {
    backendState: 'online' | 'offline' | 'connecting';
    plexState?: 'online' | 'offline' | 'connecting';
    watchStatus: 'watching' | 'stopped' | 'error';
    onRefreshBackend?: () => void | Promise<void>;
    onRefreshPlex?: () => void | Promise<void>;
  }
  let { backendState = 'offline', plexState = 'offline', watchStatus = 'stopped', onRefreshBackend, onRefreshPlex }: Props = $props();
  
  let isRefreshingBackend = $state(false);
  let isRefreshingPlex = $state(false);
  
  async function handleRefreshBackend() {
    if (!onRefreshBackend || isRefreshingBackend) return;
    
    isRefreshingBackend = true;
    try {
      await onRefreshBackend();
    } finally {
      isRefreshingBackend = false;
    }
  }

  async function handleRefreshPlex() {
    if (!onRefreshPlex || isRefreshingPlex) return;
    
    isRefreshingPlex = true;
    try {
      await onRefreshPlex();
    } finally {
      isRefreshingPlex = false;
    }
  }
</script>

<div class="flex items-center text-sm">
  <!--API Backend Connection-->
  <Button variant="ghost" class="p-2 hover:bg-accent" onclick={handleRefreshBackend} disabled={isRefreshingBackend || backendState === 'connecting'}>
    {#if backendState === 'online'}
      <div class="flex items-center">
        <CircleCheckIcon class="inline h-5 w-5 text-green-600 mr-1" />
        <span class="text-green-600 font-semibold">Backend Online</span>
      </div>
    {:else if backendState === 'offline'}
      <div class="flex items-center">
        <CircleXIcon class="inline h-5 w-5 text-destructive mr-1" />
        <span class="text-destructive font-semibold">Backend Offline</span>
      </div>
    {:else if backendState === 'connecting'}
      <div class="flex items-center">
        <Loader2Icon class="inline h-5 w-5 text-yellow-600 mr-1 animate-spin" />
        <span class="text-yellow-600 font-semibold">Connecting...</span>
      </div>
    {/if}
  </Button>

  <!--Vertical Divider-->
  <div class="my-2 border-l h-6 mx-4"></div>

  <!--Plex Server Connection-->
  <Button variant="ghost" class="p-2 hover:bg-accent" onclick={handleRefreshPlex} disabled={isRefreshingPlex || plexState === 'connecting'}>
    {#if plexState === 'online'}
      <div class="flex items-center">
        <CircleCheckIcon class="inline h-5 w-5 text-green-600 mr-1" />
        <span class="text-green-600 font-semibold">Plex Online</span>
      </div>
    {:else if plexState === 'offline'}
      <div class="flex items-center">
        <CircleXIcon class="inline h-5 w-5 text-destructive mr-1" />
        <span class="text-destructive font-semibold">Plex Offline</span>
      </div>
    {:else if plexState === 'connecting'}
      <div class="flex items-center">
        <Loader2Icon class="inline h-5 w-5 text-yellow-600 mr-1 animate-spin" />
        <span class="text-yellow-600 font-semibold">Connecting...</span>
      </div>
    {/if}
  </Button>


  <!--Vertical Divider-->
  <div class="my-2 border-l h-6 mx-4"></div>

  <!--Watch Status-->
  <div>
    {#if watchStatus === 'watching'}
      <div class="flex items-center">
        <CircleDotIcon class="inline h-5 w-5 text-green-600 mr-1" />
        <span class="text-green-600 font-semibold">Watching</span>
      </div>
    {:else if watchStatus === 'stopped'}
      <div class="flex items-center">
        <CircleIcon class="inline h-5 w-5 text-muted-foreground mr-1" />
        <span class="text-muted-foreground font-semibold">Stopped</span>
      </div>
    {:else if watchStatus === 'error'}
      <div class="flex items-center">
        <AlertTriangleIcon class="inline h-5 w-5 text-destructive mr-1" />
        <span class="text-destructive font-semibold">Error</span>
      </div>
    {/if}
  </div>
</div>
