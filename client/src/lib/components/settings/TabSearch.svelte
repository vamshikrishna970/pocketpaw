<script lang="ts">
  import { settingsStore, connectionStore } from "$lib/stores";
  import { Switch } from "$lib/components/ui/switch";
  import { Search, Database, Loader2, RefreshCw } from "@lucide/svelte";
  import { toast } from "svelte-sonner";
  import { cn } from "$lib/utils";

  let searchEnabled = $derived(Boolean(settingsStore.settings?.search_enabled));
  let geminiApiKey = $state(String(settingsStore.settings?.search_gemini_api_key ?? ""));
  let embeddingModel = $derived(
    String(settingsStore.settings?.search_embedding_model ?? "gemini-embedding-2-preview"),
  );
  let dimensions = $derived(Number(settingsStore.settings?.search_embedding_dimensions ?? 768));
  let vectorBackend = $derived(String(settingsStore.settings?.search_vector_backend ?? "auto"));
  let autoEnrich = $derived(Boolean(settingsStore.settings?.search_auto_enrich));
  let maxFileSizeMb = $derived(Number(settingsStore.settings?.search_max_file_size_mb ?? 50));

  let stats = $state<{ total_files: number; total_chunks: number } | null>(null);
  let statsLoading = $state(false);
  let indexing = $state(false);
  let indexPath = $state("");

  async function toggleSearch(checked: boolean) {
    try {
      await settingsStore.update({ search_enabled: checked });
      toast.success(`Semantic search ${checked ? "enabled" : "disabled"}`);
    } catch {
      toast.error("Failed to update search setting");
    }
  }

  async function toggleAutoEnrich(checked: boolean) {
    try {
      await settingsStore.update({ search_auto_enrich: checked });
      toast.success(`Auto-enrichment ${checked ? "enabled" : "disabled"}`);
    } catch {
      toast.error("Failed to update setting");
    }
  }

  async function saveApiKey() {
    try {
      await settingsStore.update({ search_gemini_api_key: geminiApiKey });
      toast.success("Gemini API key saved");
    } catch {
      toast.error("Failed to save API key");
    }
  }

  async function updateDimensions(value: number) {
    try {
      await settingsStore.update({ search_embedding_dimensions: value });
      toast.success(`Embedding dimensions set to ${value}`);
    } catch {
      toast.error("Failed to update dimensions");
    }
  }

  async function updateBackend(value: string) {
    try {
      await settingsStore.update({ search_vector_backend: value });
      toast.success(`Vector backend set to ${value}`);
    } catch {
      toast.error("Failed to update backend");
    }
  }

  async function loadStats() {
    statsLoading = true;
    try {
      const client = connectionStore.getClient();
      stats = await client.getSearchStats();
    } catch {
      stats = null;
    } finally {
      statsLoading = false;
    }
  }

  async function triggerIndex() {
    if (!indexPath.trim()) return;
    indexing = true;
    try {
      const client = connectionStore.getClient();
      await client.triggerIndex(indexPath.trim());
      toast.success(`Indexing started for ${indexPath}`);
      indexPath = "";
    } catch {
      toast.error("Failed to start indexing");
    } finally {
      indexing = false;
    }
  }

  // Load stats on mount
  $effect(() => {
    if (searchEnabled) loadStats();
  });
</script>

<div class="flex flex-col gap-6">
  <div class="flex items-center gap-2">
    <Search class="h-4 w-4 text-muted-foreground" strokeWidth={1.75} />
    <h3 class="text-sm font-semibold text-foreground">Search & Indexing</h3>
  </div>

  <!-- Enable toggle -->
  <div class="flex items-center justify-between rounded-lg border border-border bg-card p-3">
    <div>
      <p class="text-sm font-medium text-foreground">Enable Semantic Search</p>
      <p class="text-xs text-muted-foreground">
        Search files by meaning using Gemini embeddings
      </p>
    </div>
    <Switch checked={searchEnabled} onCheckedChange={toggleSearch} />
  </div>

  {#if searchEnabled}
    <!-- Gemini API Key -->
    <div class="flex flex-col gap-2 rounded-lg border border-border bg-card p-3">
      <label for="gemini-key" class="text-sm font-medium text-foreground">Gemini API Key</label>
      <div class="flex gap-2">
        <input
          id="gemini-key"
          type="password"
          placeholder="Enter API key..."
          bind:value={geminiApiKey}
          class={cn(
            "h-8 flex-1 rounded-md border border-border bg-background px-2.5 text-xs text-foreground outline-none",
            "placeholder:text-muted-foreground focus:border-ring focus:ring-1 focus:ring-ring/50",
          )}
        />
        <button
          type="button"
          class="h-8 rounded-md bg-primary px-3 text-xs font-medium text-primary-foreground hover:bg-primary/90"
          onclick={saveApiKey}
        >
          Save
        </button>
      </div>
    </div>

    <!-- Vector Backend -->
    <div class="flex flex-col gap-2 rounded-lg border border-border bg-card p-3">
      <label for="vector-backend" class="text-sm font-medium text-foreground">
        Vector Backend
      </label>
      <select
        id="vector-backend"
        value={vectorBackend}
        onchange={(e) => updateBackend(e.currentTarget.value)}
        class={cn(
          "h-8 rounded-md border border-border bg-background px-2 text-xs text-foreground outline-none",
          "focus:border-ring focus:ring-1 focus:ring-ring/50",
        )}
      >
        <option value="auto">Auto (recommended)</option>
        <option value="chroma">ChromaDB</option>
        <option value="zvec">zvec (Linux/macOS)</option>
      </select>
    </div>

    <!-- Embedding Dimensions -->
    <div class="flex flex-col gap-2 rounded-lg border border-border bg-card p-3">
      <label for="dimensions" class="text-sm font-medium text-foreground">
        Embedding Dimensions
      </label>
      <select
        id="dimensions"
        value={String(dimensions)}
        onchange={(e) => updateDimensions(Number(e.currentTarget.value))}
        class={cn(
          "h-8 rounded-md border border-border bg-background px-2 text-xs text-foreground outline-none",
          "focus:border-ring focus:ring-1 focus:ring-ring/50",
        )}
      >
        <option value="768">768 (default)</option>
        <option value="1536">1536</option>
        <option value="3072">3072</option>
      </select>
    </div>

    <!-- Auto-enrich -->
    <div class="flex items-center justify-between rounded-lg border border-border bg-card p-3">
      <div>
        <p class="text-sm font-medium text-foreground">Auto-Enrich Agent Context</p>
        <p class="text-xs text-muted-foreground">
          Automatically include relevant files in agent context
        </p>
      </div>
      <Switch checked={autoEnrich} onCheckedChange={toggleAutoEnrich} />
    </div>

    <!-- Index controls -->
    <div class="flex flex-col gap-3 rounded-lg border border-border bg-card p-3">
      <div class="flex items-center gap-2">
        <Database class="h-4 w-4 text-muted-foreground" strokeWidth={1.75} />
        <span class="text-sm font-medium text-foreground">Index Management</span>
      </div>

      {#if stats}
        <div class="flex gap-4 text-xs text-muted-foreground">
          <span>{stats.total_files} files indexed</span>
          <span>{stats.total_chunks} chunks</span>
        </div>
      {/if}

      <div class="flex gap-2">
        <input
          type="text"
          placeholder="Directory path to index..."
          bind:value={indexPath}
          class={cn(
            "h-8 flex-1 rounded-md border border-border bg-background px-2.5 text-xs text-foreground outline-none",
            "placeholder:text-muted-foreground focus:border-ring focus:ring-1 focus:ring-ring/50",
          )}
        />
        <button
          type="button"
          disabled={indexing || !indexPath.trim()}
          class={cn(
            "flex h-8 items-center gap-1.5 rounded-md bg-primary px-3 text-xs font-medium text-primary-foreground hover:bg-primary/90",
            "disabled:opacity-50 disabled:cursor-not-allowed",
          )}
          onclick={triggerIndex}
        >
          {#if indexing}
            <Loader2 class="h-3 w-3 animate-spin" />
          {/if}
          Index
        </button>
      </div>

      <button
        type="button"
        class="flex items-center gap-1.5 self-start text-xs text-muted-foreground hover:text-foreground"
        onclick={loadStats}
      >
        <RefreshCw class={cn("h-3 w-3", statsLoading && "animate-spin")} />
        Refresh stats
      </button>
    </div>
  {/if}
</div>
