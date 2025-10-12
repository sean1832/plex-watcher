<script lang="ts">
  import CircleXIcon from '@lucide/svelte/icons/circle-x';
  import CircleCheckIcon from '@lucide/svelte/icons/circle-check';
  import Loader2Icon from '@lucide/svelte/icons/loader-2';
  import AlertTriangleIcon from '@lucide/svelte/icons/alert-triangle';
  import CircleDotIcon from '@lucide/svelte/icons/circle-dot';
  import CircleIcon from '@lucide/svelte/icons/circle';
	import Button from './ui/button/button.svelte';

  interface Props {
    connectionStatus: 'online' | 'offline' | 'connecting';
    watchStatus: 'watching' | 'stopped' | 'error';
    onRefresh?: () => void | Promise<void>;
  }
  let { connectionStatus = 'offline', watchStatus = 'stopped', onRefresh }: Props = $props();
  
  let isRefreshing = $state(false);
  
  async function handleRefresh() {
    if (!onRefresh || isRefreshing) return;
    
    isRefreshing = true;
    try {
      await onRefresh();
    } finally {
      isRefreshing = false;
    }
  }
</script>

<div class="flex items-center text-sm">
  <!--Server Connection-->
  <Button variant="ghost" class="p-2 hover:bg-accent" onclick={handleRefresh} disabled={isRefreshing || connectionStatus === 'connecting'}>
    {#if connectionStatus === 'online'}
      <div class="flex items-center">
        <CircleCheckIcon class="inline h-5 w-5 text-green-600 mr-1" />
        <span class="text-green-600 font-semibold">Server Online</span>
      </div>
    {:else if connectionStatus === 'offline'}
      <div class="flex items-center">
        <CircleXIcon class="inline h-5 w-5 text-destructive mr-1" />
        <span class="text-destructive font-semibold">Server Offline</span>
      </div>
    {:else if connectionStatus === 'connecting'}
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
