<script lang="ts">
  import { connectionStore } from "$lib/stores/connection.svelte";
  import type { SemanticSearchResult } from "$lib/api/client";
  import Search from "@lucide/svelte/icons/search";
  import FileText from "@lucide/svelte/icons/file-text";
  import FileCode from "@lucide/svelte/icons/file-code";
  import ImageIcon from "@lucide/svelte/icons/image";
  import Music from "@lucide/svelte/icons/music";
  import Video from "@lucide/svelte/icons/video";
  import File from "@lucide/svelte/icons/file";
  import Loader from "@lucide/svelte/icons/loader-circle";
  import X from "@lucide/svelte/icons/x";
  import { cn } from "$lib/utils";

  let query = $state("");
  let results = $state<SemanticSearchResult[]>([]);
  let loading = $state(false);
  let tookMs = $state(0);
  let searchMode = $state<"hybrid" | "metadata" | "content">("hybrid");
  let activeFilter = $state<string | null>(null);
  let focusedIndex = $state(-1);
  let searchInputRef = $state<HTMLInputElement | null>(null);
  let debounceTimer: ReturnType<typeof setTimeout> | null = null;

  const filterChips = [
    { label: "All", value: null },
    { label: "Code", value: "code" },
    { label: "Text", value: "text" },
    { label: "Images", value: "image" },
    { label: "Audio", value: "audio" },
    { label: "Video", value: "video" },
    { label: "Docs", value: "pdf" },
  ] as const;

  const modeOptions = [
    { label: "Both", value: "hybrid" },
    { label: "Files", value: "metadata" },
    { label: "Contents", value: "content" },
  ] as const;

  async function doSearch() {
    if (!query.trim()) {
      results = [];
      return;
    }
    let client;
    try {
      client = connectionStore.getClient();
    } catch {
      return;
    }
    loading = true;
    try {
      const resp = await client.semanticSearch(query, {
        top_k: 20,
        mode: searchMode,
        file_types: activeFilter ?? undefined,
      });
      results = resp.results;
      tookMs = resp.took_ms;
    } catch (e) {
      console.error("Search failed:", e);
      results = [];
    } finally {
      loading = false;
    }
  }

  function handleInput() {
    if (debounceTimer) clearTimeout(debounceTimer);
    debounceTimer = setTimeout(doSearch, 500);
  }

  function getFileIcon(result: SemanticSearchResult) {
    const chunkType = String(result.metadata.chunk_type ?? "");
    const ext = String(result.metadata.extension ?? "");
    if (chunkType === "code" || ["py", "js", "ts", "rs", "go"].includes(ext))
      return FileCode;
    if (chunkType === "image") return ImageIcon;
    if (chunkType === "audio") return Music;
    if (chunkType === "video") return Video;
    if (chunkType === "text" || chunkType === "structured") return FileText;
    return File;
  }

  function handleKeydown(e: KeyboardEvent) {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      focusedIndex = Math.min(focusedIndex + 1, results.length - 1);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      focusedIndex = Math.max(focusedIndex - 1, -1);
    } else if (e.key === "Escape") {
      query = "";
      results = [];
      focusedIndex = -1;
    }
  }
</script>

<div class="flex h-full flex-col">
  <!-- Search header -->
  <div class="flex flex-col gap-2 border-b border-border p-3">
    <div class="relative flex items-center">
      <Search class="pointer-events-none absolute left-2.5 h-4 w-4 text-muted-foreground" />
      <input
        bind:this={searchInputRef}
        type="text"
        placeholder="Search by meaning..."
        bind:value={query}
        oninput={handleInput}
        onkeydown={handleKeydown}
        class={cn(
          "h-8 w-full rounded-md border border-border bg-background pl-8 pr-8 text-sm text-foreground outline-none",
          "placeholder:text-muted-foreground focus:border-ring focus:ring-1 focus:ring-ring/50",
        )}
      />
      {#if query}
        <button
          type="button"
          class="absolute right-2 text-muted-foreground hover:text-foreground"
          onclick={() => {
            query = "";
            results = [];
          }}
        >
          <X class="h-3.5 w-3.5" />
        </button>
      {/if}
    </div>

    <!-- Filter chips -->
    <div class="flex flex-wrap items-center gap-1">
      {#each filterChips as chip}
        <button
          type="button"
          class={cn(
            "rounded-full px-2 py-0.5 text-[10px] font-medium transition-colors",
            activeFilter === chip.value
              ? "bg-primary text-primary-foreground"
              : "bg-muted text-muted-foreground hover:text-foreground",
          )}
          onclick={() => {
            activeFilter = chip.value;
            if (query.trim()) doSearch();
          }}
        >
          {chip.label}
        </button>
      {/each}

      <span class="mx-1 h-3 w-px bg-border"></span>

      {#each modeOptions as opt}
        <button
          type="button"
          class={cn(
            "rounded-full px-2 py-0.5 text-[10px] font-medium transition-colors",
            searchMode === opt.value
              ? "bg-accent text-accent-foreground"
              : "text-muted-foreground hover:text-foreground",
          )}
          onclick={() => {
            searchMode = opt.value;
            if (query.trim()) doSearch();
          }}
        >
          {opt.label}
        </button>
      {/each}
    </div>
  </div>

  <!-- Results -->
  <div class="flex-1 overflow-y-auto">
    {#if loading}
      <div class="flex items-center justify-center gap-2 p-8 text-muted-foreground">
        <Loader class="h-4 w-4 animate-spin" />
        <span class="text-sm">Searching...</span>
      </div>
    {:else if results.length > 0}
      <div class="px-1 py-1">
        <div class="px-2 py-1 text-[10px] text-muted-foreground">
          {results.length} results in {tookMs.toFixed(0)}ms
        </div>
        {#each results as result, i}
          {@const Icon = getFileIcon(result)}
          <button
            type="button"
            class={cn(
              "flex w-full items-start gap-2 rounded-md px-2 py-1.5 text-left transition-colors",
              focusedIndex === i ? "bg-accent" : "hover:bg-muted/50",
            )}
            onfocus={() => (focusedIndex = i)}
          >
            <Icon class="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
            <div class="min-w-0 flex-1">
              <div class="flex items-center gap-2">
                <span class="truncate text-xs font-medium text-foreground">
                  {result.metadata.file_name ?? result.id}
                </span>
                <span
                  class={cn(
                    "shrink-0 rounded px-1 py-px text-[9px] font-medium",
                    result.score >= 0.9
                      ? "bg-green-500/15 text-green-600 dark:text-green-400"
                      : result.score >= 0.7
                        ? "bg-yellow-500/15 text-yellow-600 dark:text-yellow-400"
                        : "bg-muted text-muted-foreground",
                  )}
                >
                  {(result.score * 100).toFixed(0)}%
                </span>
              </div>
              <div class="truncate text-[10px] text-muted-foreground">
                {result.metadata.file_path ?? ""}
              </div>
              {#if result.metadata.content_preview}
                <div class="mt-0.5 truncate text-[10px] text-muted-foreground/70">
                  {result.metadata.content_preview}
                </div>
              {/if}
            </div>
          </button>
        {/each}
      </div>
    {:else if query.trim()}
      <div class="p-8 text-center text-sm text-muted-foreground">No results found</div>
    {:else}
      <div class="p-8 text-center text-sm text-muted-foreground">
        Type to search files by meaning
      </div>
    {/if}
  </div>
</div>
