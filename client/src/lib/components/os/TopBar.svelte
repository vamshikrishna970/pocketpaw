<!-- TopBar.svelte — Transparent top navigation bar for the Agent OS.
     Updated: 2026-03-22 — Home button, Lucide icons throughout.
-->
<script lang="ts">
  import Plus from "@lucide/svelte/icons/plus";
  import Home from "@lucide/svelte/icons/home";

  type Tab = "pockets" | "files" | "chat";

  let {
    activeTab,
    onTabChange,
    onLogoClick,
    onPlusClick,
    onAvatarClick,
    onHome,
  }: {
    activeTab: Tab | null;
    onTabChange: (tab: Tab) => void;
    onLogoClick: () => void;
    onPlusClick: () => void;
    onAvatarClick: () => void;
    onHome: () => void;
  } = $props();

  const TABS: { id: Tab; label: string }[] = [
    { id: "pockets", label: "Pockets" },
    { id: "files", label: "Files" },
    { id: "chat", label: "Chat" },
  ];
</script>

<header class="topbar">
  <!-- Left: Logo -->
  <div class="topbar-left">
    <button class="logo-btn" onclick={onLogoClick} aria-label="PocketPaw menu" aria-haspopup="true">
      <img class="logo-paw" src="/paw-avatar.png" alt="" aria-hidden="true" />
      <span class="logo-text">PocketPaw</span>
    </button>
  </div>

  <!-- Center: Home + Navigation tabs -->
  <nav class="topbar-center" aria-label="Main navigation">
    <button
      class={activeTab === null ? "tab-btn tab-home tab-active liquid-glass" : "tab-btn tab-home"}
      onclick={onHome}
      aria-label="Home"
      title="Home"
    >
      <Home size={14} strokeWidth={2} />
    </button>
    {#each TABS as tab}
      <button
        class={activeTab === tab.id ? "tab-btn tab-active liquid-glass" : "tab-btn"}
        onclick={() => onTabChange(tab.id)}
        aria-current={activeTab === tab.id ? "page" : undefined}
      >
        {tab.label}
      </button>
    {/each}
  </nav>

  <!-- Right: Actions -->
  <div class="topbar-right">
    <button class="plus-btn" onclick={onPlusClick} aria-label="Open command palette" title="Command Palette (⌘K)">
      <Plus size={14} strokeWidth={2} />
    </button>
    <button class="avatar-btn" onclick={onAvatarClick} aria-label="User menu" aria-haspopup="true">
      <span class="avatar-initial">P</span>
    </button>
  </div>
</header>

<style>
  .topbar {
    position: relative;
    z-index: 100;
    display: flex;
    align-items: center;
    justify-content: space-between;
    height: 32px;
    padding: 0 12px;
    background: transparent;
  }

  /* ---- Logo ---- */
  .topbar-left {
    display: flex;
    align-items: center;
    flex: 1;
  }

  .logo-btn {
    display: flex;
    align-items: center;
    gap: 6px;
    background: none;
    border: none;
    padding: 4px 6px;
    border-radius: 6px;
    cursor: pointer;
    transition: background 0.15s ease;
    text-shadow: 0 1px 4px rgba(0, 0, 0, 0.6);
  }

  .logo-btn:hover {
    background: rgba(255, 255, 255, 0.07);
  }

  .logo-paw {
    width: 20px;
    height: 20px;
    border-radius: 50%;
    object-fit: cover;
  }

  .logo-text {
    font-size: 13px;
    font-weight: 600;
    color: rgba(255, 255, 255, 0.85);
    letter-spacing: -0.01em;
  }

  /* ---- Tabs: glass pill on active ---- */
  .topbar-center {
    display: flex;
    align-items: center;
    gap: 6px;
    position: absolute;
    left: 50%;
    transform: translateX(-50%);
  }

  .tab-btn {
    background: none;
    border: none;
    padding: 4px 14px;
    border-radius: 100px;
    font-size: 13px;
    font-weight: 400;
    font-family: inherit;
    color: rgba(255, 255, 255, 0.60);
    cursor: pointer;
    transition: color 0.2s ease, background 0.2s ease, border-color 0.2s ease,
                box-shadow 0.2s ease, backdrop-filter 0.2s ease;
    text-shadow: 0 1px 4px rgba(0, 0, 0, 0.5);
    position: relative;
    border: 1px solid transparent;
  }

  .tab-btn:hover {
    color: rgba(255, 255, 255, 0.85);
  }

  /* Active tab: glass pill capsule */
  .tab-active {
    color: rgba(255, 255, 255, 0.95);
    font-weight: 500;
    /* liquid-glass class handles glass effect */
  }

  /* ---- Right actions ---- */
  .topbar-right {
    display: flex;
    align-items: center;
    gap: 10px;
    flex: 1;
    justify-content: flex-end;
  }

  .plus-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 24px;
    height: 24px;
    background: rgba(255, 255, 255, 0.08);
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 50%;
    color: rgba(255, 255, 255, 0.70);
    cursor: pointer;
    transition: color 0.15s ease, background 0.15s ease, border-color 0.15s ease;
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
  }

  .plus-btn:hover {
    color: rgba(255, 255, 255, 0.95);
    background: rgba(255, 255, 255, 0.14);
    border-color: rgba(255, 255, 255, 0.22);
  }

  .avatar-btn {
    width: 22px;
    height: 22px;
    border-radius: 50%;
    border: 1.5px solid rgba(255, 255, 255, 0.25);
    background: linear-gradient(135deg, #0A84FF 0%, #5B5BD6 100%);
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    transition: transform 0.15s ease, box-shadow 0.15s ease;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.35);
    padding: 0;
    overflow: hidden;
  }

  .avatar-btn:hover {
    transform: scale(1.08);
    box-shadow: 0 3px 12px rgba(0, 0, 0, 0.45);
  }

  .avatar-initial {
    font-size: 10px;
    font-weight: 600;
    color: white;
    text-shadow: none;
    line-height: 1;
  }
</style>
