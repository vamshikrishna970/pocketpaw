<!-- DesktopWidgets.svelte — Pinned widgets on the home desktop.
     Updated: 2026-03-22 — Multiple widget types: stats, chart, table, activity.
     Each widget renders differently based on its display type.
-->
<script lang="ts">
  import { onMount } from "svelte";
  import X from "@lucide/svelte/icons/x";
  import ExternalLink from "@lucide/svelte/icons/external-link";
  import GripVertical from "@lucide/svelte/icons/grip-vertical";
  import Target from "@lucide/svelte/icons/target";
  import Brain from "@lucide/svelte/icons/brain";
  import BarChart3 from "@lucide/svelte/icons/bar-chart-3";
  import Activity from "@lucide/svelte/icons/activity";
  import DollarSign from "@lucide/svelte/icons/dollar-sign";
  import ListTodo from "@lucide/svelte/icons/list-todo";
  import Users from "@lucide/svelte/icons/users";
  import Shield from "@lucide/svelte/icons/shield";
  import TrendingUp from "@lucide/svelte/icons/trending-up";
  import Globe from "@lucide/svelte/icons/globe";
  import StickyNote from "@lucide/svelte/icons/sticky-note";
  import Cpu from "@lucide/svelte/icons/cpu";
  import Clock from "@lucide/svelte/icons/clock";
  import Zap from "@lucide/svelte/icons/zap";
  import type { Component } from "svelte";

  export type PinnedWidget = {
    id: string;
    name: string;
    pocketName: string;
    icon: string;
    color: string;
    x: number;
    y: number;
    w: number;     // 1 = normal, 2 = wide
    h: number;
  };

  let {
    widgets = [],
    onUnpin,
    onOpenPocket,
  }: {
    widgets: PinnedWidget[];
    onUnpin: (id: string) => void;
    onOpenPocket: (pocketName: string) => void;
  } = $props();

  const ICON_MAP: Record<string, Component> = {
    target: Target, brain: Brain, "bar-chart-3": BarChart3,
    activity: Activity, "dollar-sign": DollarSign, "list-todo": ListTodo,
    users: Users, shield: Shield, "trending-up": TrendingUp,
    globe: Globe, "sticky-note": StickyNote, cpu: Cpu, clock: Clock, zap: Zap,
  };

  function getIcon(key: string): Component {
    return ICON_MAP[key] || Activity;
  }

  // --- Drag ---
  let draggingId = $state<string | null>(null);
  let dragOffset = { x: 0, y: 0 };
  let dragPos = $state({ x: 0, y: 0 });

  function onDragStart(e: PointerEvent, widget: PinnedWidget) {
    const el = (e.currentTarget as HTMLElement).closest(".desktop-widget") as HTMLElement;
    if (!el) return;
    e.preventDefault();
    draggingId = widget.id;
    const rect = el.getBoundingClientRect();
    dragOffset = { x: e.clientX - rect.left, y: e.clientY - rect.top };
    dragPos = { x: rect.left, y: rect.top };
    window.addEventListener("pointermove", onDragMove);
    window.addEventListener("pointerup", onDragEnd);
  }
  function onDragMove(e: PointerEvent) { dragPos = { x: e.clientX - dragOffset.x, y: e.clientY - dragOffset.y }; }
  function onDragEnd() { draggingId = null; window.removeEventListener("pointermove", onDragMove); window.removeEventListener("pointerup", onDragEnd); }

  // --- Widget display types and mock data ---
  type DisplayType = "stats" | "chart" | "table" | "activity";
  type StatItem = { label: string; value: string; trend?: string };
  type ChartBar = { label: string; value: number; color?: string };
  type TableRow = { cells: string[]; status?: string };
  type ActivityItem = { text: string; time: string; dot: string };

  type WidgetDisplay = {
    type: DisplayType;
    stats?: StatItem[];
    bars?: ChartBar[];
    headers?: string[];
    rows?: TableRow[];
    items?: ActivityItem[];
  };

  const WIDGET_DISPLAY: Record<string, WidgetDisplay> = {
    "Agent Crew": {
      type: "stats",
      stats: [
        { label: "Active", value: "3", trend: "+1" },
        { label: "Idle", value: "2" },
        { label: "Tasks Done", value: "14" },
      ],
    },
    "Cost Tracker": {
      type: "chart",
      bars: [
        { label: "Mon", value: 35, color: "#0A84FF" },
        { label: "Tue", value: 52, color: "#0A84FF" },
        { label: "Wed", value: 41, color: "#0A84FF" },
        { label: "Thu", value: 68, color: "#0A84FF" },
        { label: "Fri", value: 45, color: "#0A84FF" },
        { label: "Sat", value: 22, color: "#0A84FF" },
        { label: "Sun", value: 15, color: "#0A84FF" },
      ],
    },
    "Active Tasks": {
      type: "table",
      headers: ["Task", "Status", "Agent", "Priority"],
      rows: [
        { cells: ["Fix auth bug", "In Progress", "Claude", "High"], status: "#FF9F0A" },
        { cells: ["Write e2e tests", "Queued", "—", "Medium"], status: "#5E5CE6" },
        { cells: ["Deploy v0.5", "Blocked", "—", "Critical"], status: "#FF453A" },
        { cells: ["Update API docs", "Done", "Sonnet", "Low"], status: "#30D158" },
        { cells: ["Review PR #47", "In Progress", "Opus", "High"], status: "#FF9F0A" },
        { cells: ["Migrate DB schema", "Queued", "—", "Medium"], status: "#5E5CE6" },
      ],
    },
    "Latency Chart": {
      type: "chart",
      bars: [
        { label: "p50", value: 42 },
        { label: "p75", value: 85 },
        { label: "p90", value: 150 },
        { label: "p95", value: 240 },
        { label: "p99", value: 380 },
      ],
    },
    "Activity Feed": {
      type: "activity",
      items: [
        { text: "Agent deployed fix to staging", time: "2m ago", dot: "#30D158" },
        { text: "Memory indexed 3 new documents", time: "8m ago", dot: "#BF5AF2" },
        { text: "Guardian blocked rm -rf command", time: "15m ago", dot: "#FF453A" },
        { text: "Soul mood shifted to focused", time: "22m ago", dot: "#5E5CE6" },
        { text: "Cost alert: $5 daily budget reached", time: "1h ago", dot: "#FF9F0A" },
        { text: "PR #623 merged to dev branch", time: "1.5h ago", dot: "#0A84FF" },
        { text: "Spawned research agent for market scan", time: "2h ago", dot: "#30D158" },
      ],
    },
    "Soul State": {
      type: "stats",
      stats: [
        { label: "Mood", value: "Focused" },
        { label: "Energy", value: "72%" },
        { label: "Bond", value: "Captain ★★★" },
        { label: "Memories", value: "1,247" },
      ],
    },
    "System": {
      type: "stats",
      stats: [
        { label: "Uptime", value: "4d 7h" },
        { label: "CPU", value: "12%", trend: "-3%" },
        { label: "Memory", value: "2.1 GB" },
        { label: "Requests", value: "8,402" },
      ],
    },
    "Competitors": {
      type: "table",
      headers: ["Name", "Price", "Users", "Change"],
      rows: [
        { cells: ["OpenClaw", "Free", "320K ★", "—"], status: "#30D158" },
        { cells: ["Cowork", "$20/mo", "~50K", "+$5"], status: "#FF9F0A" },
        { cells: ["Open Interpreter", "$20/mo", "~30K", "—"], status: "#5E5CE6" },
        { cells: ["NanoClaw", "Free", "22K ★", "New"], status: "#0A84FF" },
        { cells: ["Aider", "Free", "18K ★", "+2K"], status: "#30D158" },
      ],
    },
  };

  function getDisplay(name: string): WidgetDisplay {
    return WIDGET_DISPLAY[name] || { type: "stats", stats: [{ label: "Status", value: "OK" }] };
  }

  function getWidgetWidth(widget: PinnedWidget): string {
    if (widget.w >= 3) return "500px";
    if (widget.w >= 2) return "360px";
    return "240px";
  }
</script>

{#if widgets.length > 0}
  <div class="desktop-widgets">
    {#each widgets as widget (widget.id)}
      {@const Icon = getIcon(widget.icon)}
      {@const display = getDisplay(widget.name)}
      <div
        class="desktop-widget liquid-glass"
        class:is-dragging={draggingId === widget.id}
        style={draggingId === widget.id
          ? `position:fixed;left:${dragPos.x}px;top:${dragPos.y}px;z-index:999;width:${getWidgetWidth(widget)};`
          : `width:${getWidgetWidth(widget)};`}
      >
        <div class="widget-head">
          <div class="widget-icon" style="color:{widget.color}">
            <Icon size={14} strokeWidth={1.8} />
          </div>
          <div class="widget-titles">
            <span class="widget-name">{widget.name}</span>
            <span class="widget-pocket">{widget.pocketName}</span>
          </div>
          <div class="widget-actions">
            <button class="widget-grip" onpointerdown={(e) => onDragStart(e, widget)} title="Drag"><GripVertical size={12} strokeWidth={1.5} /></button>
            <button class="widget-action" onclick={() => onOpenPocket(widget.pocketName)} title="Open Pocket"><ExternalLink size={12} strokeWidth={1.8} /></button>
            <button class="widget-action widget-unpin" onclick={() => onUnpin(widget.id)} title="Unpin"><X size={12} strokeWidth={2} /></button>
          </div>
        </div>

        <div class="widget-content">
          <!-- STATS -->
          {#if display.type === "stats" && display.stats}
            {#each display.stats as item}
              <div class="widget-stat">
                <span class="stat-label">{item.label}</span>
                <div class="stat-value-row">
                  <span class="stat-value">{item.value}</span>
                  {#if item.trend}
                    <span class="stat-trend" class:trend-up={item.trend.startsWith("+")} class:trend-down={item.trend.startsWith("-")}>{item.trend}</span>
                  {/if}
                </div>
              </div>
            {/each}

          <!-- CHART (bar) -->
          {:else if display.type === "chart" && display.bars}
            <div class="chart-container">
              {#each display.bars as bar}
                <div class="chart-col">
                  <div class="chart-bar-wrap">
                    <div class="chart-bar" style="height:{bar.value}%;background:{bar.color || widget.color}"></div>
                  </div>
                  <span class="chart-label">{bar.label}</span>
                </div>
              {/each}
            </div>

          <!-- TABLE -->
          {:else if display.type === "table" && display.rows}
            {#if display.headers}
              <div class="table-header">
                {#each display.headers as h}
                  <span class="table-th">{h}</span>
                {/each}
              </div>
            {/if}
            {#each display.rows as row}
              <div class="table-row">
                {#each row.cells as cell, i}
                  <span class="table-td" class:table-td-first={i === 0}>
                    {#if i === 0 && row.status}
                      <span class="table-dot" style="background:{row.status}"></span>
                    {/if}
                    {cell}
                  </span>
                {/each}
              </div>
            {/each}

          <!-- ACTIVITY FEED -->
          {:else if display.type === "activity" && display.items}
            {#each display.items as item}
              <div class="activity-row">
                <span class="activity-dot" style="background:{item.dot}"></span>
                <span class="activity-text">{item.text}</span>
                <span class="activity-time">{item.time}</span>
              </div>
            {/each}
          {/if}
        </div>

        <div class="widget-accent" style="background:{widget.color}"></div>
      </div>
    {/each}
  </div>
{/if}

<style>
  .desktop-widgets {
    position: absolute;
    top: 44px; left: 0; right: 0; bottom: 80px;
    z-index: 10; padding: 16px 24px;
    display: flex; flex-wrap: wrap; gap: 12px;
    align-content: flex-start;
    pointer-events: none;
  }

  .desktop-widget {
    border-radius: 14px; overflow: hidden;
    display: flex; flex-direction: column;
    pointer-events: auto;
    transition: transform 0.15s, box-shadow 0.15s;
    cursor: default;
  }
  .desktop-widget:hover { transform: translateY(-2px); box-shadow: 0 12px 40px rgba(0,0,0,0.3); }
  .desktop-widget.is-dragging { cursor: grabbing; opacity: 0.92; box-shadow: 0 20px 60px rgba(0,0,0,0.5); }

  .widget-head { display: flex; align-items: center; gap: 8px; padding: 12px 12px 8px; }
  .widget-icon {
    width: 28px; height: 28px; border-radius: 8px;
    display: flex; align-items: center; justify-content: center;
    background: rgba(255,255,255,0.06); flex-shrink: 0;
  }
  .widget-titles { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 1px; }
  .widget-name { font-size: 12px; font-weight: 600; color: rgba(255,255,255,0.88); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .widget-pocket { font-size: 10px; color: rgba(255,255,255,0.35); }

  .widget-actions { display: flex; align-items: center; gap: 2px; opacity: 0; transition: opacity 0.12s; }
  .desktop-widget:hover .widget-actions { opacity: 1; }
  .widget-grip, .widget-action {
    width: 22px; height: 22px; border-radius: 5px; border: none; background: none;
    display: flex; align-items: center; justify-content: center;
    color: rgba(255,255,255,0.40); cursor: pointer; transition: color 0.12s, background 0.12s;
  }
  .widget-grip { cursor: grab; }
  .widget-grip:hover, .widget-action:hover { color: rgba(255,255,255,0.80); background: rgba(255,255,255,0.08); }
  .widget-unpin:hover { color: rgba(255,100,90,0.90); background: rgba(255,70,60,0.12); }

  .widget-content { padding: 4px 12px 12px; }

  /* ---- Stats ---- */
  .widget-stat { display: flex; align-items: center; justify-content: space-between; padding: 4px 0; }
  .stat-label { font-size: 11px; color: rgba(255,255,255,0.45); }
  .stat-value-row { display: flex; align-items: center; gap: 5px; }
  .stat-value { font-size: 13px; font-weight: 600; color: rgba(255,255,255,0.88); font-family: "SF Mono", "JetBrains Mono", monospace; }
  .stat-trend { font-size: 10px; font-weight: 500; padding: 1px 4px; border-radius: 4px; }
  .trend-up { color: #30D158; background: rgba(48,209,88,0.12); }
  .trend-down { color: #FF453A; background: rgba(255,69,58,0.12); }

  /* ---- Chart (bar) ---- */
  .chart-container {
    display: flex; align-items: flex-end; gap: 4px;
    height: 80px; padding-top: 4px;
  }
  .chart-col {
    flex: 1; display: flex; flex-direction: column; align-items: center; gap: 4px;
    height: 100%;
  }
  .chart-bar-wrap {
    flex: 1; width: 100%; display: flex; align-items: flex-end;
  }
  .chart-bar {
    width: 100%; border-radius: 3px 3px 0 0;
    min-height: 3px; opacity: 0.7;
    transition: opacity 0.12s;
  }
  .desktop-widget:hover .chart-bar { opacity: 1; }
  .chart-label {
    font-size: 9px; color: rgba(255,255,255,0.35);
    font-family: "SF Mono", "JetBrains Mono", monospace;
  }

  /* ---- Table ---- */
  .table-header {
    display: flex; gap: 4px; padding: 0 0 4px;
    border-bottom: 1px solid rgba(255,255,255,0.06);
    margin-bottom: 2px;
  }
  .table-th {
    flex: 1; font-size: 10px; font-weight: 600; text-transform: uppercase;
    letter-spacing: 0.04em; color: rgba(255,255,255,0.30);
  }
  .table-row {
    display: flex; gap: 4px; padding: 4px 0;
    border-bottom: 1px solid rgba(255,255,255,0.04);
  }
  .table-row:last-child { border-bottom: none; }
  .table-td {
    flex: 1; font-size: 11px; color: rgba(255,255,255,0.65);
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    display: flex; align-items: center; gap: 5px;
  }
  .table-td-first { font-weight: 500; color: rgba(255,255,255,0.80); }
  .table-dot { width: 5px; height: 5px; border-radius: 50%; flex-shrink: 0; }

  /* ---- Activity feed ---- */
  .activity-row {
    display: flex; align-items: flex-start; gap: 8px;
    padding: 4px 0;
  }
  .activity-dot { width: 5px; height: 5px; border-radius: 50%; margin-top: 5px; flex-shrink: 0; }
  .activity-text { flex: 1; font-size: 11px; color: rgba(255,255,255,0.65); line-height: 1.4; }
  .activity-time {
    font-size: 10px; color: rgba(255,255,255,0.30); flex-shrink: 0;
    font-family: "SF Mono", "JetBrains Mono", monospace;
  }

  .widget-accent { height: 2px; opacity: 0.4; }
</style>
