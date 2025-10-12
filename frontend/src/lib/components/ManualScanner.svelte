<script lang="ts">
	import Button from "./ui/button/button.svelte";
	import Textarea from "./ui/textarea/textarea.svelte";

</script>

<div>
  <h2 class="text-3xl font-bold mb-4 text-center">MANUAL SCANNER</h2>
  <label for="paths" class="block text-sm mb-2">Media Paths</label>
  <Textarea placeholder="/media/movies/Avatar (2009)" id="paths" class="h-64 font-mono"/>
  <lable class="text-sm text-muted-foreground mt-2 block">You can enter multiple paths, each on a new line.</lable>
  <Button class="mt-4 w-full font-semibold" variant="default">Scan now</Button>
</div>