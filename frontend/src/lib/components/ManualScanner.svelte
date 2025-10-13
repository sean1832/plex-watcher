<script lang="ts">
	import { createStorage } from "$lib/stores/storage";
	import { onMount } from "svelte";
	import Button from "./ui/button/button.svelte";
	import Textarea from "./ui/textarea/textarea.svelte";
  const placeholderText = 
`# Enter one media path per line. For example:

/media/movies/Avatar (2009)
/media/movies/Inception (2010)
/media/tv-shows/Breaking Bad/Season 1`

  // presistent storage for textarea content
  const storage = createStorage<string>("manualScannerPaths", "");

  let rawContent = "";
  let hydrated = false;

  onMount(() => {
    rawContent = storage.get();
    hydrated = true;
  });

  // update storage whenever rawContent changes (after hydration)
  $: if (hydrated) storage.set(rawContent); 

  function parsePaths(input: string): string[] {
    return input
      .split("\n")
      .map(line => line.trim())
      .filter(line => line.length > 0);
  }
  $: paths = parsePaths(rawContent);

  
  export let onScanSubmit: ((paths: string[]) => void | Promise<void>) | undefined = undefined; 
  function handleSubmit(){
    if (onScanSubmit) {
      onScanSubmit(paths);
    } else {
      console.log("Scan submitted but no custom handler provided. Paths:", paths);
    }
  }
</script>

<div>
  <label for="paths" class="block text-sm mb-2">Media Paths</label>
  <Textarea id="paths" placeholder={placeholderText} class="h-64 font-mono" bind:value={rawContent} />
  
  <div class="flex justify-between ">
    <label for="paths" class="text-sm mt-2 text-muted-foreground">
      {paths.length} path(s) entered
    </label>
    <div class="flex gap-3">
      <Button class="mt-4 ml-2 font-semibold" variant="outline" onclick={() => rawContent = ""}>Clear</Button>
      <Button class="mt-4 font-semibold" variant="default" onclick={handleSubmit}>Scan now</Button>
    </div>
    
  </div>
  
  
</div>
