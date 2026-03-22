<!-- UserMenu.svelte — User avatar dropdown.
     Updated: 2026-03-22 — Lucide icons, darker glass bg.
-->
<script lang="ts">
  import { onMount, onDestroy } from "svelte";
  import Settings from "@lucide/svelte/icons/settings";
  import Key from "@lucide/svelte/icons/key";
  import Radio from "@lucide/svelte/icons/radio";
  import LogOut from "@lucide/svelte/icons/log-out";

  let { onClose }: { onClose: () => void } = $props();
  let menuEl: HTMLDivElement | null = null;

  function handleGlobalClick(e: MouseEvent) {
    if (menuEl && !menuEl.contains(e.target as Node)) onClose();
  }

  onMount(() => { setTimeout(() => { window.addEventListener("mousedown", handleGlobalClick); }, 50); });
  onDestroy(() => { window.removeEventListener("mousedown", handleGlobalClick); });

  function handleAction(action: string) {
    console.log("[UserMenu] action:", action);
    onClose();
  }
</script>

<div class="user-menu liquid-glass" bind:this={menuEl} role="menu" aria-label="User menu">
  <div class="user-identity">
    <div class="user-avatar-sm">P</div>
    <div class="user-info">
      <span class="user-name">Captain</span>
      <span class="user-email">captain@pocketpaw.ai</span>
    </div>
  </div>

  <div class="menu-divider"></div>

  <button class="menu-item" role="menuitem" onclick={() => handleAction("settings")}>
    <span class="menu-icon"><Settings size={15} strokeWidth={1.8} /></span>
    Settings
  </button>
  <button class="menu-item" role="menuitem" onclick={() => handleAction("api-keys")}>
    <span class="menu-icon"><Key size={15} strokeWidth={1.8} /></span>
    API Keys
  </button>
  <button class="menu-item" role="menuitem" onclick={() => handleAction("channels")}>
    <span class="menu-icon"><Radio size={15} strokeWidth={1.8} /></span>
    Channels
  </button>

  <div class="menu-divider"></div>

  <button class="menu-item menu-item-muted" role="menuitem" onclick={() => handleAction("sign-out")}>
    <span class="menu-icon"><LogOut size={15} strokeWidth={1.8} /></span>
    Sign Out
  </button>
</div>

<style>
  .user-menu {
    position: fixed;
    top: 36px;
    right: 12px;
    width: 220px;
    border-radius: 12px;
    box-shadow: 0 16px 56px rgba(0, 0, 0, 0.6), 0 2px 8px rgba(0, 0, 0, 0.4);
    padding: 6px;
    z-index: 900;
    animation: menu-appear 0.12s ease-out;
    background-color: rgba(0, 0, 0, 0.55) !important;
  }

  @keyframes menu-appear {
    from { opacity: 0; transform: translateY(-4px) scale(0.98); }
    to { opacity: 1; transform: translateY(0) scale(1); }
  }

  .user-identity {
    display: flex; align-items: center; gap: 10px;
    padding: 10px 12px 8px;
  }
  .user-avatar-sm {
    width: 32px; height: 32px; border-radius: 50%;
    background: linear-gradient(135deg, #0A84FF, #5B5BD6);
    display: flex; align-items: center; justify-content: center;
    font-size: 13px; font-weight: 600; color: white; flex-shrink: 0;
  }
  .user-info { display: flex; flex-direction: column; gap: 1px; min-width: 0; }
  .user-name { font-size: 13px; font-weight: 600; color: rgba(255,255,255,0.90); }
  .user-email {
    font-size: 11px; color: rgba(255,255,255,0.38);
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  }

  .menu-divider { height: 1px; background: rgba(255,255,255,0.08); margin: 4px 0; }

  .menu-item {
    display: flex; align-items: center; gap: 10px;
    width: 100%; padding: 8px 12px; background: none; border: none;
    border-radius: 8px; color: rgba(255,255,255,0.75);
    font-size: 13px; font-family: inherit; text-align: left; cursor: pointer;
    transition: background 0.12s, color 0.12s;
  }
  .menu-item:hover { background: rgba(255,255,255,0.10); color: rgba(255,255,255,0.95); }

  .menu-icon { display: flex; align-items: center; color: rgba(255,255,255,0.50); flex-shrink: 0; }
  .menu-item:hover .menu-icon { color: rgba(255,255,255,0.80); }

  .menu-item-muted { color: rgba(255,255,255,0.45); }
  .menu-item-muted:hover { background: rgba(255,255,255,0.07); color: rgba(255,255,255,0.65); }
  .menu-item-muted .menu-icon { color: rgba(255,255,255,0.35); }
</style>
