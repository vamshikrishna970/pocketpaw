<!-- ChatPill.svelte — Floating chat pill that expands in-place.
     Updated: 2026-03-22 — Expands into a chat panel inline (like Interacly),
     does NOT navigate to a separate tab. Slides up from the bottom.
-->
<script lang="ts">
  import { onMount, tick } from "svelte";
  import ArrowUp from "@lucide/svelte/icons/arrow-up";
  import Mic from "@lucide/svelte/icons/mic";
  import Video from "@lucide/svelte/icons/video";
  import Phone from "@lucide/svelte/icons/phone";
  import X from "@lucide/svelte/icons/x";
  import Sparkles from "@lucide/svelte/icons/sparkles";

  let expanded = $state(false);
  let inputValue = $state("");
  let isTyping = $state(false);
  let chatEl: HTMLDivElement | null = null;
  let inputEl: HTMLInputElement | null = null;

  type Message = { id: string; role: "user" | "agent"; text: string };
  let messages = $state<Message[]>([]);

  const RESPONSES = [
    "Got it. I'm on it — I'll update you when this is done.",
    "Great idea. Let me research that and come back with a structured plan.",
    "Sure, I'll configure that right now. You should see the results in a few seconds.",
    "I've noted that. Want me to create a Pocket for this or add it to an existing one?",
    "Interesting. I'll analyze that and give you a detailed breakdown shortly.",
    "On it. I've spawned a research agent to dig into this. Check your Pockets in a minute.",
  ];

  async function scrollChat() {
    await tick();
    if (chatEl) chatEl.scrollTop = chatEl.scrollHeight;
  }

  async function sendMessage() {
    const text = inputValue.trim();
    if (!text || isTyping) return;
    inputValue = "";
    messages = [...messages, { id: `u${Date.now()}`, role: "user", text }];
    await scrollChat();
    isTyping = true;
    await scrollChat();
    await new Promise((r) => setTimeout(r, 600 + Math.random() * 600));
    messages = [...messages, {
      id: `a${Date.now()}`, role: "agent",
      text: RESPONSES[Math.floor(Math.random() * RESPONSES.length)],
    }];
    isTyping = false;
    await scrollChat();
  }

  function handleKey(e: KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); }
    if (e.key === "Escape" && expanded) { expanded = false; }
  }

  function handlePillClick() {
    expanded = true;
    tick().then(() => inputEl?.focus());
  }

  function collapse() {
    expanded = false;
  }
</script>

<div class="pill-container">
  <div class="pill-wrapper liquid-glass" class:pill-expanded={expanded}>
    <!-- Expanded: chat history -->
    {#if expanded}
      <div class="expanded-header">
        <button class="collapse-btn" onclick={collapse} aria-label="Close">
          <X size={14} strokeWidth={2} />
        </button>
      </div>

      <div class="chat-area" bind:this={chatEl}>
        {#if messages.length === 0}
          <div class="chat-empty">
            <img class="chat-empty-avatar" src="/paw-avatar.png" alt="" />
            <p class="chat-empty-text">What can I help you with?</p>
          </div>
        {:else}
          {#each messages as msg (msg.id)}
            <div class={msg.role === "user" ? "msg msg-user" : "msg msg-agent"}>
              {#if msg.role === "agent"}
                <img class="msg-avatar" src="/paw-avatar.png" alt="" />
              {/if}
              <div class={msg.role === "user" ? "msg-bubble bubble-user" : "msg-bubble bubble-agent"}>
                {msg.text}
              </div>
            </div>
          {/each}
          {#if isTyping}
            <div class="msg msg-agent">
              <img class="msg-avatar" src="/paw-avatar.png" alt="" />
              <div class="msg-bubble bubble-agent typing-bubble">
                <span class="typing-dot"></span><span class="typing-dot"></span><span class="typing-dot"></span>
              </div>
            </div>
          {/if}
        {/if}
      </div>
    {/if}

    <!-- Input bar — always visible -->
    <div class="input-bar" class:input-bar-expanded={expanded}>
      {#if !expanded}
        <!-- Collapsed: clickable pill -->
        <button class="pill-face" onclick={handlePillClick}>
          <img class="mascot-avatar" src="/paw-avatar.png" alt="" aria-hidden="true" />
          <span class="pill-text">What you want to accomplish today?</span>
          <div class="pill-actions">
            <span class="action-icon"><Mic size={16} strokeWidth={1.8} /></span>
            <span class="action-icon"><Video size={16} strokeWidth={1.8} /></span>
            <span class="action-icon"><Phone size={16} strokeWidth={1.8} /></span>
          </div>
        </button>
      {:else}
        <!-- Expanded: real input -->
        <img class="input-avatar" src="/paw-avatar.png" alt="" aria-hidden="true" />
        <input
          bind:this={inputEl}
          class="chat-input"
          type="text"
          placeholder="Ask anything..."
          bind:value={inputValue}
          onkeydown={handleKey}
          disabled={isTyping}
          autocomplete="off"
          spellcheck="false"
        />
        <span class="action-icon-sm"><Mic size={15} strokeWidth={1.8} /></span>
        <button class="send-btn" disabled={!inputValue.trim() || isTyping} onclick={sendMessage}>
          <ArrowUp size={15} strokeWidth={2} />
        </button>
      {/if}
    </div>
  </div>
</div>

<!-- Backdrop when expanded -->
{#if expanded}
  <button class="backdrop" onclick={collapse} aria-label="Close chat" tabindex="-1"></button>
{/if}

<style>
  .pill-container {
    position: fixed;
    bottom: 32px;
    left: 50%;
    transform: translateX(-50%);
    z-index: 200;
    width: 100%;
    max-width: 580px;
    padding: 0 20px;
  }

  .pill-wrapper {
    border-radius: 16px;
    overflow: hidden;
    transition: all 250ms cubic-bezier(0.16, 1, 0.3, 1);
  }

  .pill-expanded {
    border-radius: 20px;
  }

  /* ---- Collapsed pill face ---- */
  .pill-face {
    display: flex;
    align-items: center;
    gap: 12px;
    width: 100%;
    height: 52px;
    padding: 0 14px 0 8px;
    background: none;
    border: none;
    cursor: text;
    font-family: inherit;
  }

  .mascot-avatar {
    width: 36px; height: 36px; border-radius: 50%;
    border: 2px solid rgba(255,255,255,0.60);
    flex-shrink: 0; object-fit: cover;
    box-shadow: 0 2px 8px rgba(0,0,0,0.25);
  }

  .pill-text {
    font-size: 14px; color: rgba(255,255,255,0.40);
    font-weight: 400; flex: 1; text-align: left;
    transition: color 0.2s;
  }
  .pill-face:hover .pill-text { color: rgba(255,255,255,0.65); }

  .pill-actions { display: flex; align-items: center; gap: 4px; flex-shrink: 0; }
  .action-icon {
    display: flex; align-items: center; justify-content: center;
    width: 30px; height: 30px; border-radius: 50%;
    color: rgba(255,255,255,0.35);
    transition: color 0.15s, background 0.15s;
  }
  .action-icon:hover { color: rgba(255,255,255,0.75); background: rgba(255,255,255,0.08); }

  /* ---- Expanded header ---- */
  .expanded-header {
    display: flex; justify-content: flex-end;
    padding: 8px 10px 0;
  }
  .collapse-btn {
    width: 26px; height: 26px; border-radius: 6px; border: none; background: none;
    display: flex; align-items: center; justify-content: center;
    color: rgba(255,255,255,0.40); cursor: pointer;
    transition: color 0.12s, background 0.12s;
  }
  .collapse-btn:hover { color: rgba(255,255,255,0.80); background: rgba(255,255,255,0.08); }

  /* ---- Chat area ---- */
  .chat-area {
    height: 50vh;
    max-height: 420px;
    overflow-y: auto;
    padding: 8px 14px 12px;
    display: flex;
    flex-direction: column;
    gap: 10px;
    scrollbar-width: none;
  }
  .chat-area::-webkit-scrollbar { display: none; }

  .chat-empty {
    flex: 1; display: flex; flex-direction: column;
    align-items: center; justify-content: center; gap: 12px;
  }
  .chat-empty-avatar {
    width: 48px; height: 48px; border-radius: 50%;
    object-fit: cover; opacity: 0.7;
  }
  .chat-empty-text {
    font-size: 14px; color: rgba(255,255,255,0.45); margin: 0;
  }

  .msg { display: flex; align-items: flex-end; gap: 8px; }
  .msg-user { flex-direction: row-reverse; }
  .msg-avatar {
    width: 22px; height: 22px; border-radius: 50%;
    object-fit: cover; flex-shrink: 0; margin-bottom: 2px;
  }
  .msg-bubble {
    max-width: 80%; padding: 9px 13px;
    font-size: 13px; line-height: 1.5;
    color: rgba(255,255,255,0.88); border-radius: 14px;
  }
  .bubble-user {
    background: rgba(10,132,255,0.15); border: 1px solid rgba(10,132,255,0.18);
    border-radius: 14px 14px 4px 14px;
  }
  .bubble-agent {
    background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.08);
    border-radius: 14px 14px 14px 4px;
  }
  .typing-bubble {
    display: flex; align-items: center; gap: 4px; padding: 10px 14px;
  }
  .typing-dot {
    width: 5px; height: 5px; border-radius: 50%; background: rgba(255,255,255,0.35);
    animation: dot-bounce 1.2s ease-in-out infinite;
  }
  .typing-dot:nth-child(2) { animation-delay: 0.15s; }
  .typing-dot:nth-child(3) { animation-delay: 0.30s; }
  @keyframes dot-bounce {
    0%, 80%, 100% { transform: translateY(0); opacity: 0.35; }
    40% { transform: translateY(-3px); opacity: 0.8; }
  }

  /* ---- Expanded input bar ---- */
  .input-bar {
    display: flex;
    align-items: center;
  }
  .input-bar-expanded {
    gap: 8px;
    padding: 6px 8px 8px 10px;
    border-top: 1px solid rgba(255,255,255,0.06);
  }

  .input-avatar {
    width: 28px; height: 28px; border-radius: 50%;
    border: 1.5px solid rgba(255,255,255,0.40);
    object-fit: cover; flex-shrink: 0;
  }

  .chat-input {
    flex: 1; background: none; border: none; outline: none;
    font-size: 14px; font-family: inherit;
    color: rgba(255,255,255,0.85); caret-color: #0A84FF;
    height: 36px;
  }
  .chat-input::placeholder { color: rgba(255,255,255,0.35); }
  .chat-input:disabled { opacity: 0.5; }

  .action-icon-sm {
    display: flex; align-items: center; justify-content: center;
    width: 28px; height: 28px; border-radius: 50%;
    color: rgba(255,255,255,0.35); cursor: pointer;
    transition: color 0.12s;
  }
  .action-icon-sm:hover { color: rgba(255,255,255,0.70); }

  .send-btn {
    width: 30px; height: 30px; border-radius: 50%; border: none;
    background: rgba(255,255,255,0.20); color: rgba(255,255,255,0.80);
    display: flex; align-items: center; justify-content: center;
    cursor: pointer; flex-shrink: 0; transition: background 0.12s, opacity 0.12s;
  }
  .send-btn:hover:not(:disabled) { background: rgba(255,255,255,0.30); }
  .send-btn:disabled { opacity: 0.3; cursor: not-allowed; }

  /* ---- Backdrop ---- */
  .backdrop {
    position: fixed; inset: 0; z-index: 199;
    background: transparent; border: none; cursor: default;
  }
</style>
