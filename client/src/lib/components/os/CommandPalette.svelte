<!-- CommandPalette.svelte — ⌘K command palette overlay.
     Updated: 2026-03-22 — liquid-glass + Lucide icons.
-->
<script lang="ts">
  import { onMount, onDestroy } from "svelte";
  import Search from "@lucide/svelte/icons/search";
  import MessageSquare from "@lucide/svelte/icons/message-square";
  import Bot from "@lucide/svelte/icons/bot";
  import LayoutGrid from "@lucide/svelte/icons/layout-grid";
  import FolderOpen from "@lucide/svelte/icons/folder-open";
  import Brain from "@lucide/svelte/icons/brain";
  import Settings from "@lucide/svelte/icons/settings";

  let { onClose }: { onClose: () => void } = $props();

  import type { Component } from "svelte";

  type Action = {
    id: string;
    icon: Component;
    label: string;
    shortcut?: string;
  };

  const QUICK_ACTIONS: Action[] = [
    { id: "new-chat", icon: MessageSquare, label: "New Chat Session", shortcut: "⌘N" },
    { id: "spawn-agent", icon: Bot, label: "Spawn Agent", shortcut: "" },
    { id: "create-pocket", icon: LayoutGrid, label: "Create Pocket", shortcut: "" },
    { id: "open-files", icon: FolderOpen, label: "Open Files", shortcut: "" },
    { id: "memory-browser", icon: Brain, label: "Open Memory Browser", shortcut: "" },
    { id: "settings", icon: Settings, label: "Settings", shortcut: "⌘," },
  ];

  let searchQuery = $state("");
  let selectedIndex = $state(0);
  let inputEl: HTMLInputElement | null = null;

  let filteredActions = $derived(
    searchQuery.trim() === ""
      ? QUICK_ACTIONS
      : QUICK_ACTIONS.filter((a) =>
          a.label.toLowerCase().includes(searchQuery.toLowerCase())
        )
  );

  // Reset selection when filter changes
  $effect(() => {
    // Accessing filteredActions in the effect body triggers reactivity
    void filteredActions;
    selectedIndex = 0;
  });

  function handleKeydown(e: KeyboardEvent) {
    if (e.key === "Escape") {
      onClose();
      return;
    }
    if (e.key === "ArrowDown") {
      e.preventDefault();
      selectedIndex = Math.min(selectedIndex + 1, filteredActions.length - 1);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      selectedIndex = Math.max(selectedIndex - 1, 0);
    } else if (e.key === "Enter") {
      e.preventDefault();
      const action = filteredActions[selectedIndex];
      if (action) executeAction(action.id);
    }
  }

  function executeAction(id: string) {
    console.log("[CommandPalette] execute:", id);
    onClose();
  }

  onMount(() => {
    inputEl?.focus();
    window.addEventListener("keydown", handleKeydown);
  });

  onDestroy(() => {
    window.removeEventListener("keydown", handleKeydown);
  });
</script>

<!-- Backdrop: acts as a close target -->
<button
  class="palette-backdrop"
  onclick={onClose}
  onkeydown={(e) => { if (e.key === "Escape") onClose(); }}
  aria-label="Close command palette"
  tabindex="-1"
></button>

<!-- Modal -->
<div
  class="palette-modal liquid-glass"
  role="dialog"
  aria-label="Command palette"
  aria-modal="true"
>
  <!-- Search input -->
  <div class="palette-search-row">
    <span class="search-icon" aria-hidden="true">
      <Search size={16} strokeWidth={1.5} />
    </span>
    <input
      bind:this={inputEl}
      bind:value={searchQuery}
      class="palette-input"
      type="text"
      placeholder="Search or type a command..."
      autocomplete="off"
      spellcheck="false"
      aria-label="Search commands"
    />
    <kbd class="palette-esc-hint">ESC</kbd>
  </div>

  <div class="palette-divider"></div>

  <!-- Quick actions list -->
  <div class="palette-section-label">Quick Actions</div>
  <ul class="palette-list" role="listbox" aria-label="Quick actions">
    {#each filteredActions as action, i}
      <li
        class={i === selectedIndex ? "palette-item palette-item-selected" : "palette-item"}
        role="option"
        aria-selected={i === selectedIndex}
        onmouseenter={() => { selectedIndex = i; }}
        onclick={() => executeAction(action.id)}
      >
        <span class="action-icon" aria-hidden="true">
          {#if action.icon}
            {@const Icon = action.icon}
            <Icon size={16} strokeWidth={1.8} />
          {/if}
        </span>
        <span class="action-label">{action.label}</span>
        {#if action.shortcut}
          <kbd class="action-shortcut">{action.shortcut}</kbd>
        {/if}
      </li>
    {/each}
    {#if filteredActions.length === 0}
      <li class="palette-empty">No commands match &ldquo;{searchQuery}&rdquo;</li>
    {/if}
  </ul>
</div>

<style>
  /* Backdrop — dark overlay behind the modal */
  .palette-backdrop {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.50);
    z-index: 800;
    animation: backdrop-in 0.12s ease;
    border: none;
    padding: 0;
    cursor: default;
  }

  @keyframes backdrop-in {
    from { opacity: 0; }
    to { opacity: 1; }
  }

  /* Modal */
  .palette-modal {
    position: fixed;
    top: 18%;
    left: 50%;
    transform: translateX(-50%);
    width: 520px;
    max-height: 400px;
    /* liquid-glass class handles glass effect */
    border-radius: 14px;
    box-shadow: 0 24px 80px rgba(0, 0, 0, 0.6), 0 4px 16px rgba(0, 0, 0, 0.4);
    z-index: 810;
    overflow: hidden;
    display: flex;
    flex-direction: column;
    animation: modal-in 0.14s cubic-bezier(0.32, 0.72, 0, 1);
  }

  @keyframes modal-in {
    from {
      opacity: 0;
      transform: translateX(-50%) translateY(-8px) scale(0.97);
    }
    to {
      opacity: 1;
      transform: translateX(-50%) translateY(0) scale(1);
    }
  }

  /* Search row */
  .palette-search-row {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 14px 16px 12px;
  }

  .search-icon {
    flex-shrink: 0;
    display: flex;
    align-items: center;
  }

  .palette-input {
    flex: 1;
    background: none;
    border: none;
    outline: none;
    font-size: 15px;
    font-family: inherit;
    color: rgba(255, 255, 255, 0.88);
    caret-color: #0A84FF;
  }

  .palette-input::placeholder {
    color: rgba(255, 255, 255, 0.30);
  }

  .palette-esc-hint {
    font-size: 10px;
    font-family: "SF Mono", "JetBrains Mono", monospace;
    color: rgba(255, 255, 255, 0.25);
    background: rgba(255, 255, 255, 0.07);
    border: 1px solid rgba(255, 255, 255, 0.10);
    border-radius: 4px;
    padding: 2px 5px;
    flex-shrink: 0;
  }

  .palette-divider {
    height: 1px;
    background: rgba(255, 255, 255, 0.07);
    flex-shrink: 0;
  }

  .palette-section-label {
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: rgba(255, 255, 255, 0.28);
    padding: 10px 16px 4px;
    flex-shrink: 0;
  }

  /* Items list */
  .palette-list {
    list-style: none;
    margin: 0;
    padding: 0 6px 8px;
    overflow-y: auto;
    flex: 1;
  }

  .palette-item {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 9px 12px;
    border-radius: 8px;
    cursor: pointer;
    transition: background 0.1s ease;
  }

  .palette-item:hover {
    background: rgba(255, 255, 255, 0.07);
  }

  .palette-item-selected {
    background: rgba(10, 132, 255, 0.14);
  }

  .palette-item-selected:hover {
    background: rgba(10, 132, 255, 0.18);
  }

  .action-icon {
    font-size: 16px;
    width: 20px;
    text-align: center;
    flex-shrink: 0;
    opacity: 0.75;
  }

  .action-label {
    flex: 1;
    font-size: 14px;
    color: rgba(255, 255, 255, 0.80);
  }

  .palette-item-selected .action-label {
    color: rgba(255, 255, 255, 0.95);
  }

  .action-shortcut {
    font-size: 11px;
    font-family: "SF Mono", "JetBrains Mono", monospace;
    color: rgba(255, 255, 255, 0.30);
    background: rgba(255, 255, 255, 0.06);
    border: 1px solid rgba(255, 255, 255, 0.09);
    border-radius: 5px;
    padding: 2px 6px;
    flex-shrink: 0;
  }

  .palette-empty {
    padding: 20px 16px;
    text-align: center;
    font-size: 13px;
    color: rgba(255, 255, 255, 0.28);
  }
</style>
