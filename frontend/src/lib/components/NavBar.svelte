<script lang="ts">
  import ModeToggle from "./ui/button/ModeToggle.svelte";
  import Logo from "$lib/assets/favicon.svg";
	import Separator from "./ui/separator/separator.svelte";
	import Button from "./ui/button/button.svelte";
  import SettingsIcon from '@lucide/svelte/icons/settings-2';
</script>

<nav>
  <div class="sticky flex items-center justify-center h-16 px-4">
    <div class="flex items-center justify-between w-full max-w-7xl">
      <a href="/">
        <img src={Logo} alt="Logo" class="h-10 w-10" />
      </a>
      <div class="flex items-center space-x-4">
        <Button variant="secondary" href="/scan">Manual Scanner</Button>
        <ModeToggle />
        <Button variant="outline" href="/settings">
          <SettingsIcon class="h-5 w-5" />
          <span class="sr-only">Settings</span>
        </Button>
        
      </div>
    </div>
  </div>
  <Separator />
</nav>