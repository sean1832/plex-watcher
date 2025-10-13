<script lang="ts">
  import ManualScanner from "$lib/components/ManualScanner.svelte";
  import { scanPaths } from "$lib/api/endpoints";
  import {config} from "$lib/stores/config.svelte";
  import { ApiError } from "$lib/api/client";
  import { toast } from "svelte-sonner";
	import Sonner from "$lib/components/ui/sonner/sonner.svelte";

  async function handleScanSubmit(paths: string[]) {
    const promise = scanPaths(config.toScanRequest(paths));
    toast.promise(promise, {
      loading: 'Initiating scan...',
      success: 'Scanned successfully!',
      error: (e: unknown) => {
        console.error('Scan error:', e);
        if (e instanceof ApiError) {
          return `Scan Error: ${e.message || 'Unknown error'}`;
        }else if (e instanceof Error) {
          return `Scan Error: ${e.message}`;
        }else{
          return `Scan Error: An unexpected error occurred`;
        }
      },
      duration: 10000,
    });
  }

</script>

<main class="min-h-screen bg-background flex items-center justify-center">
  <div class="mx-auto max-w-7xl px-4 py-8 w-full">
    <h2 class="text-3xl font-bold mb-4 text-center">MANUAL SCANNER</h2>
    <ManualScanner onScanSubmit={handleScanSubmit} />
    <Sonner position='bottom-center' />
  </div>
</main>