<script lang="ts">
  import { explorerStore } from "$lib/stores/explorer.svelte";
  import Search from "@lucide/svelte/icons/search";
  import Sparkles from "@lucide/svelte/icons/sparkles";
  import X from "@lucide/svelte/icons/x";
  import { cn } from "$lib/utils";
  import { onMount } from "svelte";

  let searchInputRef = $state<HTMLInputElement | null>(null);

  onMount(() => {
    function handleFocusSearch() {
      searchInputRef?.focus();
    }
    window.addEventListener("explorer:focus-search", handleFocusSearch);
    return () => window.removeEventListener("explorer:focus-search", handleFocusSearch);
  });

  const resultCountText = $derived.by(() => {
    const total = explorerStore.totalItemCount;
    const fileCount = explorerStore.files.length;
    if (explorerStore.searchQuery.trim()) {
      return `${total} of ${fileCount}`;
    }
    return "";
  });

  function handleInput(e: Event) {
    const value = (e.currentTarget as HTMLInputElement).value;
    explorerStore.setSearchQuery(value);
    if (explorerStore.semanticSearchEnabled && value.trim()) {
      explorerStore.debouncedSemanticSearch(value);
    }
  }
</script>

<div class="flex h-8 shrink-0 items-center gap-1.5 border-b border-border px-2">
  <!-- Semantic search toggle -->
  <button
    type="button"
    title={explorerStore.semanticSearchEnabled ? "Semantic search (AI)" : "Name search"}
    class={cn(
      "flex h-5 shrink-0 items-center rounded px-1 text-[10px] font-medium transition-colors",
      explorerStore.semanticSearchEnabled
        ? "bg-primary/15 text-primary"
        : "text-muted-foreground hover:text-foreground",
    )}
    onclick={() => {
      explorerStore.semanticSearchEnabled = !explorerStore.semanticSearchEnabled;
      if (explorerStore.semanticSearchEnabled && explorerStore.searchQuery.trim()) {
        explorerStore.debouncedSemanticSearch(explorerStore.searchQuery);
      } else {
        explorerStore.semanticResults = [];
      }
    }}
  >
    <Sparkles class="h-3 w-3" />
  </button>

  <!-- Search input -->
  <div class="relative flex min-w-0 flex-1 items-center">
    <Search class="pointer-events-none absolute left-2 h-3.5 w-3.5 text-muted-foreground" />
    <input
      bind:this={searchInputRef}
      type="text"
      placeholder={explorerStore.semanticSearchEnabled ? "Search by meaning..." : "Filter files..."}
      value={explorerStore.searchQuery}
      oninput={handleInput}
      class={cn(
        "h-6 w-full rounded-md border border-border bg-background pl-7 text-xs text-foreground outline-none transition-all placeholder:text-muted-foreground",
        "focus:border-ring focus:ring-1 focus:ring-ring/50",
        explorerStore.semanticSearchEnabled && "border-primary/30",
        resultCountText ? "pr-20" : "pr-7",
      )}
    />
    {#if resultCountText}
      <span class="absolute right-7 text-[10px] text-muted-foreground">{resultCountText}</span>
    {/if}
    {#if explorerStore.searchQuery}
      <button
        type="button"
        class="absolute right-1.5 rounded-sm p-0.5 text-muted-foreground hover:text-foreground"
        onclick={() => {
          explorerStore.setSearchQuery("");
          explorerStore.semanticResults = [];
        }}
      >
        <X class="h-3 w-3" />
      </button>
    {/if}
  </div>
</div>
