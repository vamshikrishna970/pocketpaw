<!-- PocketsPanel.svelte — Pockets workspace browser + detail view for the Agent OS.
     Updated: 2026-03-22 — Pocket detail page with widget canvas.
     AI sidebar has Back + New Chat buttons for conversation management.
-->
<script lang="ts">
  import { onMount, tick } from "svelte";
  import LayoutGrid from "@lucide/svelte/icons/layout-grid";
  import Target from "@lucide/svelte/icons/target";
  import Brain from "@lucide/svelte/icons/brain";
  import FlaskConical from "@lucide/svelte/icons/flask-conical";
  import BarChart3 from "@lucide/svelte/icons/bar-chart-3";
  import Layers from "@lucide/svelte/icons/layers";
  import Plus from "@lucide/svelte/icons/plus";
  import Clock from "@lucide/svelte/icons/clock";
  import Sparkles from "@lucide/svelte/icons/sparkles";
  import ArrowUp from "@lucide/svelte/icons/arrow-up";
  import Wand2 from "@lucide/svelte/icons/wand-2";
  import Puzzle from "@lucide/svelte/icons/puzzle";
  import Workflow from "@lucide/svelte/icons/workflow";
  import Globe from "@lucide/svelte/icons/globe";
  import Shield from "@lucide/svelte/icons/shield";
  import TrendingUp from "@lucide/svelte/icons/trending-up";
  import Users from "@lucide/svelte/icons/users";
  import Zap from "@lucide/svelte/icons/zap";
  import ArrowLeft from "@lucide/svelte/icons/arrow-left";
  import MessageSquarePlus from "@lucide/svelte/icons/message-square-plus";
  import Activity from "@lucide/svelte/icons/activity";
  import ListTodo from "@lucide/svelte/icons/list-todo";
  import DollarSign from "@lucide/svelte/icons/dollar-sign";
  import StickyNote from "@lucide/svelte/icons/sticky-note";
  import Settings from "@lucide/svelte/icons/settings";
  import Store from "@lucide/svelte/icons/store";
  import ShoppingCart from "@lucide/svelte/icons/shopping-cart";
  import Package from "@lucide/svelte/icons/package";
  import CalendarDays from "@lucide/svelte/icons/calendar-days";
  import MessageCircle from "@lucide/svelte/icons/message-circle";
  import CreditCard from "@lucide/svelte/icons/credit-card";
  import Truck from "@lucide/svelte/icons/truck";
  import Star from "@lucide/svelte/icons/star";
  import Maximize2 from "@lucide/svelte/icons/maximize-2";
  import GripVertical from "@lucide/svelte/icons/grip-vertical";
  import type { Component } from "svelte";

  // --- AI chat state ---
  type AiMessage = { id: string; role: "user" | "agent"; text: string };
  let aiMessages = $state<AiMessage[]>([]);
  let aiInput = $state("");
  let aiTyping = $state(false);
  let aiChatEl: HTMLDivElement | null = null;

  const AI_RESPONSES_GRID = [
    "I'll create a new Pocket for that. Give me a sec — setting up the widgets and data sources.",
    "Done — your new Pocket is ready. I added 4 widgets: metrics overview, task board, activity feed, and a notes panel.",
    "Great idea. I've created a Research pocket with web search monitoring, competitor profiles, and a summary dashboard.",
    "Created! I connected it to your GitHub and Linear accounts. It'll pull in issues, PRs, and sprint progress automatically.",
  ];

  const AI_RESPONSES_DETAIL = [
    "Done — I added a new widget to this Pocket. You can drag it to reposition.",
    "Updated the layout. I moved the charts to the top row and expanded the task board.",
    "I've connected that data source. The widget will start populating in a moment.",
    "Removed the widget and reorganized the remaining ones to fill the space.",
    "Good call. I swapped the bar chart for a line chart — better for time-series data.",
  ];

  async function scrollAiChat() {
    await tick();
    if (aiChatEl) aiChatEl.scrollTop = aiChatEl.scrollHeight;
  }

  async function sendAiMessage() {
    const text = aiInput.trim();
    if (!text || aiTyping) return;
    aiInput = "";
    aiMessages = [...aiMessages, { id: `u${Date.now()}`, role: "user", text }];
    await scrollAiChat();
    aiTyping = true;
    await scrollAiChat();
    await new Promise((r) => setTimeout(r, 800 + Math.random() * 800));
    const responses = selectedPocket ? AI_RESPONSES_DETAIL : AI_RESPONSES_GRID;
    aiMessages = [...aiMessages, {
      id: `a${Date.now()}`, role: "agent",
      text: responses[Math.floor(Math.random() * responses.length)],
    }];
    aiTyping = false;
    await scrollAiChat();
  }

  function handleAiKey(e: KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendAiMessage(); }
  }

  function handleSuggestion(text: string) {
    aiInput = text;
    sendAiMessage();
  }

  function newChat() {
    aiMessages = [];
    aiInput = "";
  }

  // --- Resizable AI sidebar ---
  let aiW = $state(260);
  let sidebarDragging = $state(false);
  let sidebarDragStart = { mx: 0, w: 0 };

  function onSidebarResizeDown(e: PointerEvent) {
    e.preventDefault();
    sidebarDragging = true;
    sidebarDragStart = { mx: e.clientX, w: aiW };
    window.addEventListener("pointermove", onSidebarResizeMove);
    window.addEventListener("pointerup", onSidebarResizeUp);
  }
  function onSidebarResizeMove(e: PointerEvent) {
    aiW = Math.max(200, Math.min(450, sidebarDragStart.w - (e.clientX - sidebarDragStart.mx)));
  }
  function onSidebarResizeUp() {
    sidebarDragging = false;
    window.removeEventListener("pointermove", onSidebarResizeMove);
    window.removeEventListener("pointerup", onSidebarResizeUp);
  }

  // --- Categories ---
  type Category = { id: string; label: string; icon: Component };
  const CATEGORIES: Category[] = [
    { id: "all", label: "All Pockets", icon: LayoutGrid },
    { id: "mission", label: "Mission Control", icon: Target },
    { id: "deep-work", label: "Deep Work", icon: Brain },
    { id: "research", label: "Research", icon: FlaskConical },
    { id: "data", label: "Data & Metrics", icon: BarChart3 },
    { id: "business", label: "Business", icon: Store },
    { id: "custom", label: "Custom", icon: Layers },
  ];
  let activeCategory = $state("all");

  // --- Pockets data ---
  type Widget = { id: string; name: string; icon: Component; color: string; span: string };
  type Pocket = {
    id: string; name: string; description: string; type: string;
    icon: Component; color: string; widgets: Widget[];
    lastActive: string; active?: boolean;
  };

  const MOCK_POCKETS: Pocket[] = [
    { id: "p1", name: "Mission Control", description: "Agent crew status, tasks, costs, and activity feed", type: "mission", icon: Target, color: "#0A84FF", lastActive: "Just now", active: true, widgets: [
      { id: "w1", name: "Agent Crew", icon: Users, color: "#30D158", span: "col-span-1" },
      { id: "w2", name: "Active Tasks", icon: ListTodo, color: "#FF9F0A", span: "col-span-1" },
      { id: "w3", name: "Activity Feed", icon: Activity, color: "#5E5CE6", span: "col-span-1" },
      { id: "w4", name: "Soul State", icon: Brain, color: "#BF5AF2", span: "col-span-1" },
      { id: "w5", name: "Cost Tracker", icon: DollarSign, color: "#0A84FF", span: "col-span-1" },
      { id: "w6", name: "Quick Notes", icon: StickyNote, color: "#64D2FF", span: "col-span-1" },
    ]},
    { id: "p2", name: "Deep Work", description: "Focused task execution with code editor and terminal", type: "deep-work", icon: Brain, color: "#BF5AF2", lastActive: "2 hours ago", widgets: [
      { id: "w7", name: "Code Editor", icon: Layers, color: "#BF5AF2", span: "col-span-2" },
      { id: "w8", name: "Terminal", icon: Zap, color: "#30D158", span: "col-span-1" },
      { id: "w9", name: "Task Context", icon: ListTodo, color: "#FF9F0A", span: "col-span-1" },
      { id: "w10", name: "File Browser", icon: LayoutGrid, color: "#0A84FF", span: "col-span-2" },
    ]},
    { id: "p3", name: "Competitive Analysis", description: "Competitor monitoring, pricing tracker, market trends", type: "research", icon: FlaskConical, color: "#30D158", lastActive: "Yesterday", widgets: [
      { id: "w11", name: "Web Monitor", icon: Globe, color: "#0A84FF", span: "col-span-1" },
      { id: "w12", name: "Pricing Tracker", icon: DollarSign, color: "#FF9F0A", span: "col-span-1" },
      { id: "w13", name: "Competitor Profiles", icon: Users, color: "#30D158", span: "col-span-1" },
      { id: "w14", name: "Trend Charts", icon: TrendingUp, color: "#FF453A", span: "col-span-2" },
      { id: "w15", name: "Research Notes", icon: StickyNote, color: "#64D2FF", span: "col-span-1" },
    ]},
    { id: "p4", name: "API Metrics", description: "Request latency, error rates, usage by endpoint", type: "data", icon: BarChart3, color: "#FF9F0A", lastActive: "5 hours ago", widgets: [
      { id: "w16", name: "Latency Chart", icon: Activity, color: "#0A84FF", span: "col-span-2" },
      { id: "w17", name: "Error Rates", icon: Shield, color: "#FF453A", span: "col-span-1" },
      { id: "w18", name: "Usage by Endpoint", icon: BarChart3, color: "#FF9F0A", span: "col-span-3" },
    ]},
    { id: "p5", name: "Launch Tracker", description: "Product Hunt prep, social copy, launch checklist", type: "mission", icon: TrendingUp, color: "#FF453A", lastActive: "3 days ago", widgets: [
      { id: "w19", name: "Launch Checklist", icon: ListTodo, color: "#30D158", span: "col-span-1" },
      { id: "w20", name: "Social Copy", icon: Globe, color: "#0A84FF", span: "col-span-1" },
      { id: "w21", name: "Timeline", icon: Clock, color: "#FF9F0A", span: "col-span-1" },
      { id: "w22", name: "Analytics Preview", icon: TrendingUp, color: "#FF453A", span: "col-span-1" },
    ]},
    { id: "p6", name: "Soul Protocol Research", description: "Spec drafts, competitor protocols, academic papers", type: "research", icon: Globe, color: "#5E5CE6", lastActive: "1 day ago", widgets: [
      { id: "w23", name: "Spec Editor", icon: Layers, color: "#5E5CE6", span: "col-span-2" },
      { id: "w24", name: "Paper Library", icon: FlaskConical, color: "#BF5AF2", span: "col-span-1" },
      { id: "w25", name: "Comparison Matrix", icon: BarChart3, color: "#0A84FF", span: "col-span-3" },
    ]},
    { id: "p7", name: "Security Audit", description: "Vulnerability scan results, compliance checklist, pen test logs", type: "custom", icon: Shield, color: "#FF6482", lastActive: "4 days ago", widgets: [
      { id: "w26", name: "Scan Results", icon: Shield, color: "#FF6482", span: "col-span-2" },
      { id: "w27", name: "Compliance", icon: ListTodo, color: "#30D158", span: "col-span-1" },
      { id: "w28", name: "Pen Test Logs", icon: Activity, color: "#FF9F0A", span: "col-span-1" },
      { id: "w29", name: "Risk Matrix", icon: BarChart3, color: "#FF453A", span: "col-span-2" },
    ]},
    { id: "p8", name: "Hiring Pipeline", description: "Candidate tracking, interview notes, team capacity", type: "custom", icon: Users, color: "#64D2FF", lastActive: "1 week ago", widgets: [
      { id: "w30", name: "Candidates", icon: Users, color: "#64D2FF", span: "col-span-2" },
      { id: "w31", name: "Interview Notes", icon: StickyNote, color: "#FF9F0A", span: "col-span-1" },
      { id: "w32", name: "Team Capacity", icon: BarChart3, color: "#30D158", span: "col-span-1" },
    ]},
    // --- Realistic business pockets ---
    { id: "p9", name: "Brew & Co. HQ", description: "Full business dashboard — revenue, orders, inventory, staff, reviews", type: "business", icon: Store, color: "#C4813D", lastActive: "Just now", active: true, widgets: [
      { id: "w40", name: "Revenue Today", icon: DollarSign, color: "#30D158", span: "col-span-1" },
      { id: "w41", name: "Live Orders", icon: ShoppingCart, color: "#0A84FF", span: "col-span-2" },
      { id: "w42", name: "Weekly Sales", icon: TrendingUp, color: "#C4813D", span: "col-span-2" },
      { id: "w43", name: "Inventory Alerts", icon: Package, color: "#FF9F0A", span: "col-span-1" },
      { id: "w44", name: "Staff On Shift", icon: CalendarDays, color: "#5E5CE6", span: "col-span-1" },
      { id: "w45", name: "Customer Reviews", icon: Star, color: "#FEBC2E", span: "col-span-1" },
      { id: "w46", name: "Support Tickets", icon: MessageCircle, color: "#FF453A", span: "col-span-1" },
      { id: "w47", name: "Website Traffic", icon: Globe, color: "#0A84FF", span: "col-span-2" },
      { id: "w48", name: "Top Products", icon: Package, color: "#30D158", span: "col-span-1" },
    ]},
    { id: "p10", name: "Brew Online Store", description: "E-commerce metrics — conversions, cart abandonment, shipping", type: "business", icon: ShoppingCart, color: "#0A84FF", lastActive: "30 min ago", widgets: [
      { id: "w50", name: "Store Overview", icon: Store, color: "#0A84FF", span: "col-span-1" },
      { id: "w51", name: "Recent Orders", icon: CreditCard, color: "#30D158", span: "col-span-2" },
      { id: "w52", name: "Conversion Funnel", icon: TrendingUp, color: "#BF5AF2", span: "col-span-2" },
      { id: "w53", name: "Shipping Status", icon: Truck, color: "#FF9F0A", span: "col-span-1" },
      { id: "w54", name: "Abandoned Carts", icon: ShoppingCart, color: "#FF453A", span: "col-span-1" },
      { id: "w55", name: "Product Performance", icon: BarChart3, color: "#0A84FF", span: "col-span-2" },
    ]},
    { id: "p11", name: "Brew Finances", description: "P&L, expenses, payroll, tax prep — connected to QuickBooks", type: "business", icon: CreditCard, color: "#30D158", lastActive: "2 hours ago", widgets: [
      { id: "w60", name: "P&L Summary", icon: DollarSign, color: "#30D158", span: "col-span-2" },
      { id: "w61", name: "Monthly Expenses", icon: BarChart3, color: "#FF453A", span: "col-span-1" },
      { id: "w62", name: "Payroll", icon: Users, color: "#5E5CE6", span: "col-span-1" },
      { id: "w63", name: "Accounts Receivable", icon: CreditCard, color: "#0A84FF", span: "col-span-1" },
      { id: "w64", name: "Cash Flow", icon: TrendingUp, color: "#30D158", span: "col-span-2" },
      { id: "w65", name: "Tax Deadlines", icon: CalendarDays, color: "#FF9F0A", span: "col-span-1" },
    ]},
  ];

  // --- Widget display data (same system as DesktopWidgets) ---
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
    "Agent Crew": { type: "stats", stats: [
      { label: "Active", value: "3", trend: "+1" }, { label: "Idle", value: "2" }, { label: "Tasks Done", value: "14" },
    ]},
    "Active Tasks": { type: "table", headers: ["Task", "Status", "Agent"], rows: [
      { cells: ["Fix auth bug", "In Progress", "Claude"], status: "#FF9F0A" },
      { cells: ["Write tests", "Queued", "—"], status: "#5E5CE6" },
      { cells: ["Deploy v0.5", "Blocked", "—"], status: "#FF453A" },
      { cells: ["Update docs", "Done", "Sonnet"], status: "#30D158" },
    ]},
    "Activity Feed": { type: "activity", items: [
      { text: "Agent deployed fix to staging", time: "2m", dot: "#30D158" },
      { text: "Memory indexed 3 new docs", time: "8m", dot: "#BF5AF2" },
      { text: "Guardian blocked rm -rf", time: "15m", dot: "#FF453A" },
      { text: "Soul mood → focused", time: "22m", dot: "#5E5CE6" },
      { text: "Cost alert: $5 budget", time: "1h", dot: "#FF9F0A" },
    ]},
    "Soul State": { type: "stats", stats: [
      { label: "Mood", value: "Focused" }, { label: "Energy", value: "72%" },
      { label: "Bond", value: "Captain ★★★" }, { label: "Memories", value: "1,247" },
    ]},
    "Cost Tracker": { type: "chart", bars: [
      { label: "Mon", value: 35 }, { label: "Tue", value: 52 }, { label: "Wed", value: 41 },
      { label: "Thu", value: 68 }, { label: "Fri", value: 45 }, { label: "Sat", value: 22 }, { label: "Sun", value: 15 },
    ]},
    "Quick Notes": { type: "stats", stats: [
      { label: "Notes", value: "12" }, { label: "Last Edit", value: "3m ago" },
    ]},
    "Code Editor": { type: "stats", stats: [
      { label: "Open Files", value: "4" }, { label: "Language", value: "Python" }, { label: "Lines", value: "2,840" },
    ]},
    "Terminal": { type: "activity", items: [
      { text: "$ uv run pytest — 14 passed", time: "1m", dot: "#30D158" },
      { text: "$ git push origin dev", time: "5m", dot: "#0A84FF" },
      { text: "$ ruff check . — clean", time: "8m", dot: "#30D158" },
    ]},
    "Task Context": { type: "stats", stats: [
      { label: "Current", value: "Fix auth flow" }, { label: "Branch", value: "fix/auth" }, { label: "Files", value: "3 changed" },
    ]},
    "File Browser": { type: "table", headers: ["Name", "Size", "Modified"], rows: [
      { cells: ["src/auth.py", "4.2 KB", "2m ago"], status: "#0A84FF" },
      { cells: ["tests/test_auth.py", "1.8 KB", "5m ago"], status: "#30D158" },
      { cells: ["config.json", "890 B", "1h ago"], status: "#FF9F0A" },
    ]},
    "Web Monitor": { type: "activity", items: [
      { text: "OpenClaw released v4.2", time: "1h", dot: "#FF453A" },
      { text: "Cowork pricing page updated", time: "3h", dot: "#FF9F0A" },
      { text: "NanoClaw hit 23K stars", time: "6h", dot: "#0A84FF" },
    ]},
    "Pricing Tracker": { type: "table", headers: ["Product", "Price", "Change"], rows: [
      { cells: ["Cowork", "$20/mo", "+$5"], status: "#FF9F0A" },
      { cells: ["Interpreter", "$20/mo", "—"], status: "#5E5CE6" },
      { cells: ["Cursor", "$20/mo", "—"], status: "#0A84FF" },
    ]},
    "Competitor Profiles": { type: "stats", stats: [
      { label: "Tracking", value: "5" }, { label: "Alerts", value: "2 new" }, { label: "Last Scan", value: "1h ago" },
    ]},
    "Trend Charts": { type: "chart", bars: [
      { label: "Jan", value: 20 }, { label: "Feb", value: 35 }, { label: "Mar", value: 55 },
      { label: "Apr", value: 48 }, { label: "May", value: 72 }, { label: "Jun", value: 90 },
    ]},
    "Research Notes": { type: "stats", stats: [
      { label: "Notes", value: "8" }, { label: "Sources", value: "14" }, { label: "Tags", value: "6" },
    ]},
    "Latency Chart": { type: "chart", bars: [
      { label: "p50", value: 42 }, { label: "p75", value: 85 }, { label: "p90", value: 150 },
      { label: "p95", value: 240 }, { label: "p99", value: 380 },
    ]},
    "Error Rates": { type: "stats", stats: [
      { label: "5xx", value: "0.2%", trend: "-0.1%" }, { label: "4xx", value: "1.4%" }, { label: "Uptime", value: "99.8%" },
    ]},
    "Usage by Endpoint": { type: "table", headers: ["Endpoint", "Calls", "Avg ms"], rows: [
      { cells: ["/api/chat", "4,201", "42ms"], status: "#0A84FF" },
      { cells: ["/api/sessions", "1,803", "18ms"], status: "#30D158" },
      { cells: ["/api/memory", "892", "65ms"], status: "#FF9F0A" },
      { cells: ["/api/tools", "341", "120ms"], status: "#FF453A" },
    ]},
    "Launch Checklist": { type: "table", headers: ["Item", "Status"], rows: [
      { cells: ["README updated", "Done"], status: "#30D158" },
      { cells: ["Social copy ready", "Done"], status: "#30D158" },
      { cells: ["HN post drafted", "In Progress"], status: "#FF9F0A" },
      { cells: ["Demo video", "Queued"], status: "#5E5CE6" },
    ]},
    "Social Copy": { type: "stats", stats: [
      { label: "Tweets", value: "5 ready" }, { label: "HN Post", value: "Draft" }, { label: "Reddit", value: "3 subs" },
    ]},
    "Timeline": { type: "activity", items: [
      { text: "Prep week starts", time: "Day 1", dot: "#0A84FF" },
      { text: "Launch on HN", time: "Day 8", dot: "#FF453A" },
      { text: "Reddit + Twitter", time: "Day 9", dot: "#5E5CE6" },
      { text: "Feedback collection", time: "Day 15", dot: "#30D158" },
    ]},
    "Analytics Preview": { type: "chart", bars: [
      { label: "Views", value: 80 }, { label: "Clicks", value: 45 }, { label: "Stars", value: 60 }, { label: "Forks", value: 25 },
    ]},
    "Spec Editor": { type: "stats", stats: [
      { label: "Sections", value: "12" }, { label: "Words", value: "7,500" }, { label: "Status", value: "v0.2.2" },
    ]},
    "Paper Library": { type: "stats", stats: [
      { label: "Papers", value: "14" }, { label: "Cited", value: "8" }, { label: "Unread", value: "3" },
    ]},
    "Comparison Matrix": { type: "table", headers: ["Protocol", "Memory", "Identity", "Storage"], rows: [
      { cells: ["Soul Protocol", "5-tier", "DID", "Arweave"], status: "#5E5CE6" },
      { cells: ["MemGPT", "2-tier", "None", "Local"], status: "#FF9F0A" },
      { cells: ["Zep", "Vector", "None", "Cloud"], status: "#0A84FF" },
    ]},
    "Scan Results": { type: "table", headers: ["Issue", "Severity", "Status"], rows: [
      { cells: ["Path traversal", "Critical", "Fixed"], status: "#FF453A" },
      { cells: ["Race condition", "High", "Fixed"], status: "#FF9F0A" },
      { cells: ["PII exposure", "Medium", "Open"], status: "#FF9F0A" },
      { cells: ["CORS config", "Low", "Accepted"], status: "#30D158" },
    ]},
    "Compliance": { type: "stats", stats: [
      { label: "Passed", value: "18/22" }, { label: "Failed", value: "2" }, { label: "Pending", value: "2" },
    ]},
    "Pen Test Logs": { type: "activity", items: [
      { text: "SQL injection test — blocked", time: "1d", dot: "#30D158" },
      { text: "XSS payload — sanitized", time: "1d", dot: "#30D158" },
      { text: "Auth bypass attempt — blocked", time: "2d", dot: "#30D158" },
    ]},
    "Risk Matrix": { type: "chart", bars: [
      { label: "Crit", value: 10 }, { label: "High", value: 25 }, { label: "Med", value: 45 },
      { label: "Low", value: 70 }, { label: "Info", value: 90 },
    ]},
    "Candidates": { type: "table", headers: ["Name", "Role", "Stage"], rows: [
      { cells: ["Alex M.", "Frontend", "Interview"], status: "#0A84FF" },
      { cells: ["Sarah K.", "Backend", "Offer"], status: "#30D158" },
      { cells: ["James L.", "DevOps", "Screen"], status: "#FF9F0A" },
    ]},
    "Interview Notes": { type: "stats", stats: [
      { label: "Completed", value: "6" }, { label: "Scheduled", value: "3" }, { label: "Avg Score", value: "4.2/5" },
    ]},
    "Team Capacity": { type: "chart", bars: [
      { label: "Eng", value: 85 }, { label: "Design", value: 60 }, { label: "PM", value: 40 }, { label: "QA", value: 70 },
    ]},
    // --- Brew & Co. HQ ---
    "Revenue Today": { type: "stats", stats: [
      { label: "Revenue", value: "$4,820", trend: "+18%" },
      { label: "Orders", value: "127" },
      { label: "Avg Ticket", value: "$37.95" },
      { label: "vs Yesterday", value: "+$640", trend: "+15%" },
    ]},
    "Live Orders": { type: "table", headers: ["Order", "Items", "Total", "Status"], rows: [
      { cells: ["#1847", "2× Latte, 1× Croissant", "$18.50", "Preparing"], status: "#FF9F0A" },
      { cells: ["#1846", "1× Cold Brew, 1× Muffin", "$12.75", "Ready"], status: "#30D158" },
      { cells: ["#1845", "3× Espresso", "$13.50", "Delivered"], status: "#0A84FF" },
      { cells: ["#1844", "1× Matcha, 2× Bagel", "$22.00", "Preparing"], status: "#FF9F0A" },
      { cells: ["#1843", "1× Drip Coffee", "$4.50", "Picked Up"], status: "#30D158" },
      { cells: ["#1842", "2× Cappuccino, 1× Cake", "$26.00", "Online — Pending"], status: "#5E5CE6" },
    ]},
    "Weekly Sales": { type: "chart", bars: [
      { label: "Mon", value: 62, color: "#C4813D" },
      { label: "Tue", value: 71, color: "#C4813D" },
      { label: "Wed", value: 55, color: "#C4813D" },
      { label: "Thu", value: 83, color: "#C4813D" },
      { label: "Fri", value: 95, color: "#C4813D" },
      { label: "Sat", value: 100, color: "#C4813D" },
      { label: "Sun", value: 78, color: "#C4813D" },
    ]},
    "Inventory Alerts": { type: "table", headers: ["Item", "Stock", "Action"], rows: [
      { cells: ["Oat Milk", "2 cartons", "Reorder NOW"], status: "#FF453A" },
      { cells: ["Croissants", "12 left", "Order by 4pm"], status: "#FF9F0A" },
      { cells: ["Cold Brew Kegs", "1 remaining", "Supplier notified"], status: "#FF9F0A" },
      { cells: ["Cup Sleeves", "~50", "OK for today"], status: "#30D158" },
    ]},
    "Staff On Shift": { type: "table", headers: ["Name", "Role", "Shift", "Status"], rows: [
      { cells: ["Maria G.", "Barista Lead", "7am–3pm", "On Floor"], status: "#30D158" },
      { cells: ["James T.", "Barista", "7am–3pm", "On Break"], status: "#FF9F0A" },
      { cells: ["Priya K.", "Cashier", "8am–4pm", "On Floor"], status: "#30D158" },
      { cells: ["Alex R.", "Kitchen", "6am–2pm", "On Floor"], status: "#30D158" },
      { cells: ["Sam L.", "Barista", "2pm–10pm", "Starts 2pm"], status: "#5E5CE6" },
    ]},
    "Customer Reviews": { type: "activity", items: [
      { text: "★★★★★ \"Best oat latte in the city\" — Google", time: "1h", dot: "#FEBC2E" },
      { text: "★★★★☆ \"Great vibes, slow wifi\" — Yelp", time: "3h", dot: "#FEBC2E" },
      { text: "★★★★★ \"Love the new matcha!\" — Instagram", time: "5h", dot: "#FEBC2E" },
      { text: "★★★☆☆ \"Pastries were stale today\" — Google", time: "1d", dot: "#FF9F0A" },
      { text: "★★★★★ \"My go-to spot, always consistent\" — Yelp", time: "2d", dot: "#FEBC2E" },
    ]},
    "Support Tickets": { type: "table", headers: ["Ticket", "Issue", "Priority"], rows: [
      { cells: ["#312", "Online order never arrived", "High"], status: "#FF453A" },
      { cells: ["#311", "Wrong item in pickup bag", "Medium"], status: "#FF9F0A" },
      { cells: ["#310", "Loyalty points not syncing", "Low"], status: "#5E5CE6" },
      { cells: ["#309", "Gift card balance issue", "Medium"], status: "#FF9F0A" },
    ]},
    "Website Traffic": { type: "chart", bars: [
      { label: "Mon", value: 45, color: "#0A84FF" },
      { label: "Tue", value: 52, color: "#0A84FF" },
      { label: "Wed", value: 48, color: "#0A84FF" },
      { label: "Thu", value: 61, color: "#0A84FF" },
      { label: "Fri", value: 78, color: "#0A84FF" },
      { label: "Sat", value: 92, color: "#0A84FF" },
      { label: "Sun", value: 67, color: "#0A84FF" },
    ]},
    "Top Products": { type: "stats", stats: [
      { label: "#1 Oat Latte", value: "34 sold" },
      { label: "#2 Cold Brew", value: "28 sold" },
      { label: "#3 Croissant", value: "22 sold" },
      { label: "#4 Matcha", value: "18 sold" },
    ]},
    // --- Brew Online Store ---
    "Store Overview": { type: "stats", stats: [
      { label: "Online Orders", value: "43", trend: "+12%" },
      { label: "Revenue", value: "$1,890" },
      { label: "Avg Order", value: "$43.95" },
      { label: "Return Rate", value: "2.1%" },
    ]},
    "Recent Orders": { type: "table", headers: ["Order", "Customer", "Items", "Total", "Status"], rows: [
      { cells: ["#ONL-892", "Sarah M.", "2× Beans, 1× Mug", "$68.00", "Shipped"], status: "#0A84FF" },
      { cells: ["#ONL-891", "David K.", "1× Gift Box", "$45.00", "Processing"], status: "#FF9F0A" },
      { cells: ["#ONL-890", "Lisa W.", "3× Beans", "$72.00", "Delivered"], status: "#30D158" },
      { cells: ["#ONL-889", "Tom H.", "1× Subscription", "$29.00", "Active"], status: "#30D158" },
      { cells: ["#ONL-888", "Amy C.", "2× Merch", "$54.00", "Shipped"], status: "#0A84FF" },
    ]},
    "Conversion Funnel": { type: "chart", bars: [
      { label: "Visit", value: 100, color: "#BF5AF2" },
      { label: "Browse", value: 68, color: "#BF5AF2" },
      { label: "Cart", value: 35, color: "#BF5AF2" },
      { label: "Checkout", value: 22, color: "#BF5AF2" },
      { label: "Purchase", value: 18, color: "#BF5AF2" },
    ]},
    "Shipping Status": { type: "stats", stats: [
      { label: "In Transit", value: "12" },
      { label: "Delivered Today", value: "8" },
      { label: "Returns", value: "1" },
      { label: "Avg Delivery", value: "2.4 days" },
    ]},
    "Abandoned Carts": { type: "stats", stats: [
      { label: "Open Carts", value: "23", trend: "-5" },
      { label: "Recovery Emails", value: "8 sent" },
      { label: "Recovered", value: "$180" },
      { label: "Cart Value", value: "$1,240" },
    ]},
    "Product Performance": { type: "table", headers: ["Product", "Sold", "Revenue", "Trend"], rows: [
      { cells: ["Single Origin Beans", "89", "$2,670", "↑ 12%"], status: "#30D158" },
      { cells: ["Holiday Gift Box", "34", "$1,530", "↑ 45%"], status: "#30D158" },
      { cells: ["Brew & Co. Mug", "56", "$1,120", "→ 0%"], status: "#5E5CE6" },
      { cells: ["Cold Brew Kit", "21", "$840", "↓ 8%"], status: "#FF453A" },
      { cells: ["Monthly Sub", "18", "$522", "↑ 22%"], status: "#30D158" },
    ]},
    // --- Brew Finances ---
    "P&L Summary": { type: "stats", stats: [
      { label: "Revenue MTD", value: "$48,200", trend: "+22%" },
      { label: "COGS", value: "$18,400" },
      { label: "Gross Margin", value: "61.8%" },
      { label: "Net Profit", value: "$12,600", trend: "+$2,100" },
      { label: "Operating Exp", value: "$17,200" },
    ]},
    "Monthly Expenses": { type: "chart", bars: [
      { label: "Rent", value: 85, color: "#FF453A" },
      { label: "Payroll", value: 100, color: "#FF453A" },
      { label: "COGS", value: 72, color: "#FF9F0A" },
      { label: "Utils", value: 25, color: "#FF9F0A" },
      { label: "Mktg", value: 30, color: "#5E5CE6" },
      { label: "Tech", value: 15, color: "#0A84FF" },
    ]},
    "Payroll": { type: "table", headers: ["Name", "Role", "Hrs/wk", "Rate"], rows: [
      { cells: ["Maria G.", "Lead Barista", "40", "$22/hr"], status: "#30D158" },
      { cells: ["James T.", "Barista", "32", "$18/hr"], status: "#30D158" },
      { cells: ["Priya K.", "Cashier", "40", "$17/hr"], status: "#30D158" },
      { cells: ["Alex R.", "Kitchen", "40", "$19/hr"], status: "#30D158" },
      { cells: ["Sam L.", "Barista PT", "24", "$18/hr"], status: "#5E5CE6" },
    ]},
    "Accounts Receivable": { type: "stats", stats: [
      { label: "Outstanding", value: "$3,200" },
      { label: "Overdue", value: "$800", trend: "2 invoices" },
      { label: "Collected MTD", value: "$12,400" },
    ]},
    "Cash Flow": { type: "chart", bars: [
      { label: "Jan", value: 40, color: "#30D158" },
      { label: "Feb", value: 55, color: "#30D158" },
      { label: "Mar", value: 48, color: "#30D158" },
      { label: "Apr", value: 72, color: "#30D158" },
      { label: "May", value: 65, color: "#30D158" },
      { label: "Jun", value: 88, color: "#30D158" },
    ]},
    "Tax Deadlines": { type: "activity", items: [
      { text: "Q1 estimated tax payment", time: "Apr 15", dot: "#FF453A" },
      { text: "Sales tax filing — CA", time: "Apr 30", dot: "#FF9F0A" },
      { text: "Payroll tax deposit", time: "May 15", dot: "#FF9F0A" },
      { text: "Q2 estimated tax payment", time: "Jun 15", dot: "#5E5CE6" },
    ]},
  };

  function getWidgetDisplay(name: string): WidgetDisplay {
    return WIDGET_DISPLAY[name] || { type: "stats", stats: [{ label: "Status", value: "OK" }] };
  }

  // --- Pocket detail state ---
  let selectedPocket = $state<Pocket | null>(null);
  let selectedWidget = $state<Widget | null>(null);

  function openPocket(pocket: Pocket) {
    selectedPocket = pocket;
    selectedWidget = null;
    newChat();
  }

  function closePocket() {
    selectedPocket = null;
    selectedWidget = null;
    newChat();
  }

  function openWidget(widget: Widget) {
    selectedWidget = widget;
    newChat();
  }

  function closeWidget() {
    selectedWidget = null;
    newChat();
  }

  let filteredPockets = $derived(
    activeCategory === "all"
      ? MOCK_POCKETS
      : MOCK_POCKETS.filter(p => p.type === activeCategory)
  );

  let visible = $state(false);
  onMount(() => { requestAnimationFrame(() => { visible = true; }); });
</script>

<div class={visible ? "pockets-panel pockets-visible liquid-glass glass-noise" : "pockets-panel liquid-glass glass-noise"}>
  <div class="body">
    {#if !selectedPocket}
      <!-- ========== GRID VIEW ========== -->
      <aside class="sidebar">
        <div class="nav-section">
          {#each CATEGORIES as cat}
            {@const Icon = cat.icon}
            <button class={activeCategory === cat.id ? "nav-item nav-active" : "nav-item"} onclick={() => activeCategory = cat.id}>
              <Icon size={15} strokeWidth={1.8} /><span>{cat.label}</span>
            </button>
          {/each}
        </div>
        <div class="nav-label">Quick Create</div>
        <div class="nav-section">
          <button class="nav-item nav-create" onclick={() => handleSuggestion("Create a new Mission Control pocket")}>
            <Plus size={14} strokeWidth={2} /><span>New Pocket</span>
          </button>
        </div>
      </aside>

      <main class="content">
        <div class="pocket-grid">
          {#each filteredPockets as pocket}
            {@const Icon = pocket.icon}
            <button class="pocket-card" onclick={() => openPocket(pocket)}>
              <div class="pocket-header">
                <div class="pocket-icon" style="background:{pocket.color}18;color:{pocket.color}">
                  <Icon size={20} strokeWidth={1.8} />
                </div>
                {#if pocket.active}
                  <span class="pocket-live-dot"></span>
                {/if}
              </div>
              <div class="pocket-body">
                <h3 class="pocket-name">{pocket.name}</h3>
                <p class="pocket-desc">{pocket.description}</p>
              </div>
              <div class="pocket-footer">
                <span class="pocket-widgets"><Puzzle size={11} strokeWidth={1.8} /> {pocket.widgets.length} widgets</span>
                <span class="pocket-time"><Clock size={11} strokeWidth={1.8} /> {pocket.lastActive}</span>
              </div>
            </button>
          {/each}

          <button class="pocket-card pocket-card-new" onclick={() => handleSuggestion("Create a new pocket for")}>
            <div class="new-pocket-inner">
              <Plus size={24} strokeWidth={1.5} />
              <span>Create Pocket</span>
            </div>
          </button>
        </div>
      </main>
    {:else}
      <!-- ========== DETAIL VIEW ========== -->
      {@const PocketIcon = selectedPocket.icon}
      <main class="detail-view">
        {#if !selectedWidget}
          <!-- Pocket toolbar -->
          <header class="detail-toolbar">
            <button class="detail-back" onclick={closePocket}><ArrowLeft size={16} strokeWidth={2} /></button>
            <div class="detail-title-group">
              <div class="detail-icon" style="background:{selectedPocket.color}18;color:{selectedPocket.color}">
                <PocketIcon size={16} strokeWidth={1.8} />
              </div>
              <h2 class="detail-title">{selectedPocket.name}</h2>
              {#if selectedPocket.active}<span class="detail-live">Live</span>{/if}
            </div>
            <div class="detail-actions">
              <button class="detail-action-btn" title="Settings"><Settings size={14} strokeWidth={1.8} /></button>
              <button class="detail-action-btn" title="Fullscreen"><Maximize2 size={14} strokeWidth={1.8} /></button>
            </div>
          </header>

          <!-- Widget canvas — clickable cards -->
          <div class="widget-canvas">
            {#each selectedPocket.widgets as widget}
              {@const WIcon = widget.icon}
              {@const display = getWidgetDisplay(widget.name)}
              <button class="widget-card {widget.span}" onclick={() => openWidget(widget)}>
                <div class="widget-header">
                  <div class="widget-icon" style="color:{widget.color}"><WIcon size={14} strokeWidth={1.8} /></div>
                  <span class="widget-name">{widget.name}</span>
                  <span class="widget-grip"><GripVertical size={12} strokeWidth={1.5} /></span>
                </div>
                <div class="widget-body">
                  {#if display.type === "stats" && display.stats}
                    {#each display.stats as item}
                      <div class="wstat-row">
                        <span class="wstat-label">{item.label}</span>
                        <div class="wstat-val-row">
                          <span class="wstat-value">{item.value}</span>
                          {#if item.trend}<span class="wstat-trend" class:wt-up={item.trend.startsWith("+")} class:wt-down={item.trend.startsWith("-")}>{item.trend}</span>{/if}
                        </div>
                      </div>
                    {/each}
                  {:else if display.type === "chart" && display.bars}
                    <div class="wchart">
                      {#each display.bars as bar}
                        <div class="wchart-col"><div class="wchart-bar-wrap"><div class="wchart-bar" style="height:{bar.value}%;background:{bar.color || widget.color}"></div></div><span class="wchart-label">{bar.label}</span></div>
                      {/each}
                    </div>
                  {:else if display.type === "table" && display.rows}
                    {#if display.headers}<div class="wtable-head">{#each display.headers as h}<span class="wtable-th">{h}</span>{/each}</div>{/if}
                    {#each display.rows as row}<div class="wtable-row">{#each row.cells as cell, i}<span class="wtable-td" class:wtable-td-first={i === 0}>{#if i === 0 && row.status}<span class="wtable-dot" style="background:{row.status}"></span>{/if}{cell}</span>{/each}</div>{/each}
                  {:else if display.type === "activity" && display.items}
                    {#each display.items as item}<div class="wact-row"><span class="wact-dot" style="background:{item.dot}"></span><span class="wact-text">{item.text}</span><span class="wact-time">{item.time}</span></div>{/each}
                  {/if}
                </div>
              </button>
            {/each}
          </div>
        {:else}
          <!-- ========== SINGLE WIDGET DETAIL ========== -->
          {@const WDIcon = selectedWidget.icon}
          {@const wDisplay = getWidgetDisplay(selectedWidget.name)}
          <header class="detail-toolbar">
            <button class="detail-back" onclick={closeWidget}><ArrowLeft size={16} strokeWidth={2} /></button>
            <div class="detail-title-group">
              <div class="detail-icon" style="background:{selectedWidget.color}18;color:{selectedWidget.color}">
                <WDIcon size={16} strokeWidth={1.8} />
              </div>
              <h2 class="detail-title">{selectedWidget?.name}</h2>
              <span class="detail-source">{selectedPocket.name}</span>
            </div>
            <div class="detail-actions">
              <button class="detail-action-btn" title="Pin to Desktop"><Target size={14} strokeWidth={1.8} /></button>
              <button class="detail-action-btn" title="Settings"><Settings size={14} strokeWidth={1.8} /></button>
              <button class="detail-action-btn" title="Fullscreen"><Maximize2 size={14} strokeWidth={1.8} /></button>
            </div>
          </header>

          <div class="widget-detail-body">
            <!-- Expanded widget content -->
            {#if wDisplay.type === "stats" && wDisplay.stats}
              <div class="wd-stats-grid">
                {#each wDisplay.stats as item}
                  <div class="wd-stat-card">
                    <span class="wd-stat-label">{item.label}</span>
                    <span class="wd-stat-value">{item.value}</span>
                    {#if item.trend}
                      <span class="wd-stat-trend" class:wt-up={item.trend.startsWith("+")} class:wt-down={item.trend.startsWith("-")}>{item.trend}</span>
                    {/if}
                  </div>
                {/each}
              </div>

            {:else if wDisplay.type === "chart" && wDisplay.bars}
              <div class="wd-chart">
                {#each wDisplay.bars as bar}
                  <div class="wd-chart-col">
                    <div class="wd-chart-bar-wrap">
                      <div class="wd-chart-bar" style="height:{bar.value}%;background:{bar.color || selectedWidget.color}"></div>
                    </div>
                    <span class="wd-chart-label">{bar.label}</span>
                    <span class="wd-chart-val">{bar.value}</span>
                  </div>
                {/each}
              </div>

            {:else if wDisplay.type === "table" && wDisplay.rows}
              <div class="wd-table">
                {#if wDisplay.headers}
                  <div class="wd-table-head">
                    {#each wDisplay.headers as h}<span class="wd-th">{h}</span>{/each}
                  </div>
                {/if}
                {#each wDisplay.rows as row}
                  <div class="wd-table-row">
                    {#each row.cells as cell, i}
                      <span class="wd-td" class:wd-td-first={i === 0}>
                        {#if i === 0 && row.status}<span class="wd-td-dot" style="background:{row.status}"></span>{/if}
                        {cell}
                      </span>
                    {/each}
                  </div>
                {/each}
              </div>

            {:else if wDisplay.type === "activity" && wDisplay.items}
              <div class="wd-activity">
                {#each wDisplay.items as item}
                  <div class="wd-act-row">
                    <span class="wd-act-dot" style="background:{item.dot}"></span>
                    <span class="wd-act-text">{item.text}</span>
                    <span class="wd-act-time">{item.time}</span>
                  </div>
                {/each}
              </div>
            {/if}
          </div>
        {/if}
      </main>
    {/if}

    <div class="sidebar-resize-handle" onpointerdown={onSidebarResizeDown}></div>

    <!-- ========== AI Sidebar (shared between views) ========== -->
    <aside class="ai-sidebar" style="width:{aiW}px">
      <!-- Back + New Chat controls -->
      {#if aiMessages.length > 0}
        <div class="ai-controls">
          <button class="ai-ctrl-btn" onclick={newChat} title="New conversation">
            <MessageSquarePlus size={14} strokeWidth={1.8} />
            <span>New</span>
          </button>
        </div>
      {/if}

      {#if aiMessages.length === 0}
        {#if selectedWidget}
          <!-- Widget detail context -->
          <div class="ai-section">
            <div class="ai-section-label">This widget</div>
            <button class="ai-suggestion" onclick={() => handleSuggestion(`Filter ${selectedWidget?.name} data by date range`)}>
              <Wand2 size={14} strokeWidth={1.8} /><span>Filter by date</span>
            </button>
            <button class="ai-suggestion" onclick={() => handleSuggestion(`Export ${selectedWidget?.name} data as CSV`)}>
              <Zap size={14} strokeWidth={1.8} /><span>Export as CSV</span>
            </button>
            <button class="ai-suggestion" onclick={() => handleSuggestion(`Add a new column to ${selectedWidget?.name}`)}>
              <LayoutGrid size={14} strokeWidth={1.8} /><span>Add column</span>
            </button>
            <button class="ai-suggestion" onclick={() => handleSuggestion(`Change ${selectedWidget?.name} chart type to line chart`)}>
              <TrendingUp size={14} strokeWidth={1.8} /><span>Change chart type</span>
            </button>
            <button class="ai-suggestion" onclick={() => handleSuggestion(`Set up alerts when ${selectedWidget?.name} values change significantly`)}>
              <Shield size={14} strokeWidth={1.8} /><span>Set up alerts</span>
            </button>
            <button class="ai-suggestion" onclick={() => handleSuggestion(`Pin ${selectedWidget?.name} to my desktop`)}>
              <Target size={14} strokeWidth={1.8} /><span>Pin to desktop</span>
            </button>
          </div>
        {:else if selectedPocket}
          <!-- Pocket detail context -->
          <div class="ai-section">
            <div class="ai-section-label">Edit this pocket</div>
            <button class="ai-suggestion" onclick={() => handleSuggestion("Add a new chart widget to this pocket")}>
              <Wand2 size={14} strokeWidth={1.8} /><span>Add a widget</span>
            </button>
            <button class="ai-suggestion" onclick={() => handleSuggestion("Rearrange widgets — put the most important ones at the top")}>
              <LayoutGrid size={14} strokeWidth={1.8} /><span>Rearrange layout</span>
            </button>
            <button class="ai-suggestion" onclick={() => handleSuggestion("Connect a new data source to this pocket")}>
              <Workflow size={14} strokeWidth={1.8} /><span>Connect data source</span>
            </button>
            <button class="ai-suggestion" onclick={() => handleSuggestion("Remove unused widgets and clean up this pocket")}>
              <Zap size={14} strokeWidth={1.8} /><span>Clean up pocket</span>
            </button>
          </div>
        {:else}
          <!-- Grid view suggestions -->
          <div class="ai-section">
            <div class="ai-section-label">Describe your workspace</div>
            <p class="ai-hint">Tell me what you need and I'll build a Pocket with the right widgets and data.</p>
          </div>
          <div class="ai-section">
            <div class="ai-section-label">Suggestions</div>
            <button class="ai-suggestion" onclick={() => handleSuggestion("Build me a competitive analysis workspace that monitors 3 competitors")}>
              <Wand2 size={14} strokeWidth={1.8} /><span>Competitive analysis</span>
            </button>
            <button class="ai-suggestion" onclick={() => handleSuggestion("Create a sprint dashboard connected to GitHub and Linear")}>
              <Workflow size={14} strokeWidth={1.8} /><span>Sprint dashboard</span>
            </button>
            <button class="ai-suggestion" onclick={() => handleSuggestion("Set up a content calendar for our launch across Twitter, HN, and Reddit")}>
              <Globe size={14} strokeWidth={1.8} /><span>Content calendar</span>
            </button>
            <button class="ai-suggestion" onclick={() => handleSuggestion("Build a customer feedback tracker from Slack and email")}>
              <Users size={14} strokeWidth={1.8} /><span>Feedback tracker</span>
            </button>
            <button class="ai-suggestion" onclick={() => handleSuggestion("Create a cost monitoring pocket for all my AI API usage")}>
              <Zap size={14} strokeWidth={1.8} /><span>Cost monitoring</span>
            </button>
          </div>
        {/if}
      {:else}
        <!-- Chat thread -->
        <div class="ai-chat-area" bind:this={aiChatEl}>
          {#each aiMessages as msg (msg.id)}
            <div class={msg.role === "user" ? "ai-msg ai-msg-user" : "ai-msg ai-msg-agent"}>
              {#if msg.role === "agent"}
                <div class="ai-msg-avatar"><Sparkles size={10} strokeWidth={2} /></div>
              {/if}
              <div class={msg.role === "user" ? "ai-msg-bubble ai-bubble-user" : "ai-msg-bubble ai-bubble-agent"}>
                {msg.text}
              </div>
            </div>
          {/each}
          {#if aiTyping}
            <div class="ai-msg ai-msg-agent">
              <div class="ai-msg-avatar"><Sparkles size={10} strokeWidth={2} /></div>
              <div class="ai-msg-bubble ai-bubble-agent ai-typing-bubble">
                <span class="ai-typing-dot"></span><span class="ai-typing-dot"></span><span class="ai-typing-dot"></span>
              </div>
            </div>
          {/if}
        </div>
      {/if}

      <div class="ai-input-area">
        <div class="ai-input-row liquid-glass">
          <input
            class="ai-input" type="text"
            placeholder={selectedPocket ? "Edit this pocket..." : "Describe a pocket to create..."}
            bind:value={aiInput} onkeydown={handleAiKey}
            disabled={aiTyping} autocomplete="off" spellcheck="false"
          />
          <button class="ai-send-btn" disabled={!aiInput.trim() || aiTyping} onclick={sendAiMessage}>
            <ArrowUp size={14} strokeWidth={2} />
          </button>
        </div>
      </div>
    </aside>
  </div>
</div>

<style>
  .pockets-panel {
    position: fixed; top: 32px; left: 0; right: 0; bottom: 0;
    z-index: 50; display: flex; flex-direction: column;
    overflow: hidden; opacity: 0; transition: opacity 200ms ease;
    border-top: 1px solid rgba(255,255,255,0.06);
  }
  .pockets-visible { opacity: 1; }
  .body { display: flex; flex: 1; min-height: 0; }

  /* ---- Category sidebar ---- */
  .sidebar {
    width: 180px; flex-shrink: 0;
    border-right: 1px solid rgba(255,255,255,0.06);
    padding: 12px 8px; overflow-y: auto;
    display: flex; flex-direction: column; gap: 4px;
    scrollbar-width: none;
  }
  .sidebar::-webkit-scrollbar { display: none; }
  .nav-label {
    font-size: 11px; font-weight: 600; text-transform: uppercase;
    letter-spacing: 0.06em; color: rgba(255,255,255,0.32);
    padding: 14px 10px 5px;
  }
  .nav-section { display: flex; flex-direction: column; gap: 2px; }
  .nav-item {
    display: flex; align-items: center; gap: 9px;
    padding: 8px 10px; border-radius: 7px; border: none; background: none;
    color: rgba(255,255,255,0.65); font-size: 13px; font-family: inherit;
    text-align: left; cursor: pointer; transition: color 0.12s, background 0.12s;
  }
  .nav-item:hover { color: rgba(255,255,255,0.90); background: rgba(255,255,255,0.06); }
  .nav-active { color: rgba(255,255,255,0.95); background: rgba(255,255,255,0.10); font-weight: 500; }
  .nav-create { color: #0A84FF; }
  .nav-create:hover { color: #3da1ff; background: rgba(10,132,255,0.08); }

  /* ---- Grid view ---- */
  .content {
    flex: 1; min-width: 0; overflow-y: auto; padding: 16px;
    scrollbar-width: thin; scrollbar-color: rgba(255,255,255,0.10) transparent;
  }
  .content::-webkit-scrollbar { width: 4px; }
  .content::-webkit-scrollbar-track { background: transparent; }
  .content::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.10); border-radius: 2px; }

  .pocket-grid {
    display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 12px;
  }
  .pocket-card {
    display: flex; flex-direction: column;
    border: 1px solid rgba(255,255,255,0.08); background: rgba(255,255,255,0.04);
    border-radius: 12px; padding: 16px;
    cursor: pointer; font-family: inherit; text-align: left;
    transition: background 0.15s, border-color 0.15s, transform 0.15s;
  }
  .pocket-card:hover { background: rgba(255,255,255,0.08); border-color: rgba(255,255,255,0.14); transform: translateY(-1px); }
  .pocket-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
  .pocket-icon { width: 40px; height: 40px; border-radius: 10px; display: flex; align-items: center; justify-content: center; }
  .pocket-live-dot { width: 8px; height: 8px; border-radius: 50%; background: #30D158; animation: pulse-dot 2s ease-in-out infinite; }
  @keyframes pulse-dot { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }
  .pocket-body { flex: 1; margin-bottom: 12px; }
  .pocket-name { font-size: 14px; font-weight: 600; color: rgba(255,255,255,0.90); margin: 0 0 4px; }
  .pocket-desc { font-size: 12px; color: rgba(255,255,255,0.45); line-height: 1.4; margin: 0; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
  .pocket-footer { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
  .pocket-widgets, .pocket-time { display: flex; align-items: center; gap: 4px; font-size: 11px; color: rgba(255,255,255,0.35); }
  .pocket-card-new { border-style: dashed; border-color: rgba(255,255,255,0.12); background: transparent; min-height: 160px; justify-content: center; align-items: center; }
  .pocket-card-new:hover { border-color: rgba(10,132,255,0.30); background: rgba(10,132,255,0.04); }
  .new-pocket-inner { display: flex; flex-direction: column; align-items: center; gap: 8px; color: rgba(255,255,255,0.40); font-size: 13px; font-weight: 500; }
  .pocket-card-new:hover .new-pocket-inner { color: #0A84FF; }

  /* ---- Detail view ---- */
  .detail-view { flex: 1; min-width: 0; display: flex; flex-direction: column; overflow: hidden; }

  .detail-toolbar {
    display: flex; align-items: center; gap: 10px;
    height: 42px; padding: 0 14px; flex-shrink: 0;
    border-bottom: 1px solid rgba(255,255,255,0.06);
  }
  .detail-back {
    width: 28px; height: 28px; border-radius: 7px; border: none; background: none;
    display: flex; align-items: center; justify-content: center;
    color: rgba(255,255,255,0.55); cursor: pointer; transition: color 0.12s, background 0.12s;
  }
  .detail-back:hover { color: rgba(255,255,255,0.90); background: rgba(255,255,255,0.08); }
  .detail-title-group { display: flex; align-items: center; gap: 8px; flex: 1; }
  .detail-icon { width: 26px; height: 26px; border-radius: 7px; display: flex; align-items: center; justify-content: center; }
  .detail-title { font-size: 14px; font-weight: 600; color: rgba(255,255,255,0.90); margin: 0; }
  .detail-live {
    font-size: 10px; font-weight: 600; color: #30D158;
    background: rgba(48,209,88,0.12); padding: 2px 7px; border-radius: 6px;
  }
  .detail-actions { display: flex; gap: 4px; }
  .detail-action-btn {
    width: 28px; height: 28px; border-radius: 6px; border: none; background: none;
    display: flex; align-items: center; justify-content: center;
    color: rgba(255,255,255,0.45); cursor: pointer; transition: color 0.12s, background 0.12s;
  }
  .detail-action-btn:hover { color: rgba(255,255,255,0.80); background: rgba(255,255,255,0.08); }

  /* Widget canvas */
  .widget-canvas {
    flex: 1; overflow-y: auto; padding: 14px;
    display: grid; grid-template-columns: repeat(3, 1fr);
    gap: 10px; align-content: start;
    scrollbar-width: thin; scrollbar-color: rgba(255,255,255,0.10) transparent;
  }
  .widget-canvas::-webkit-scrollbar { width: 4px; }
  .widget-canvas::-webkit-scrollbar-track { background: transparent; }
  .widget-canvas::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.10); border-radius: 2px; }

  .col-span-1 { grid-column: span 1; }
  .col-span-2 { grid-column: span 2; }
  .col-span-3 { grid-column: span 3; }

  .widget-card {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 10px; padding: 12px; min-height: 120px;
    display: flex; flex-direction: column;
    transition: border-color 0.12s;
  }
  .widget-card:hover { border-color: rgba(255,255,255,0.14); }

  .widget-header { display: flex; align-items: center; gap: 7px; margin-bottom: 10px; }
  .widget-icon { display: flex; flex-shrink: 0; }
  .widget-name { font-size: 11px; font-weight: 600; color: rgba(255,255,255,0.55); text-transform: uppercase; letter-spacing: 0.04em; flex: 1; }
  .widget-grip {
    opacity: 0; color: rgba(255,255,255,0.30); cursor: grab;
    border: none; background: none; padding: 0;
    transition: opacity 0.12s;
  }
  .widget-card:hover .widget-grip { opacity: 1; }

  .widget-body { flex: 1; padding-top: 2px; }

  /* Widget: stats */
  .wstat-row { display: flex; align-items: center; justify-content: space-between; padding: 3px 0; }
  .wstat-label { font-size: 11px; color: rgba(255,255,255,0.45); }
  .wstat-val-row { display: flex; align-items: center; gap: 5px; }
  .wstat-value { font-size: 12px; font-weight: 600; color: rgba(255,255,255,0.85); font-family: "SF Mono", "JetBrains Mono", monospace; }
  .wstat-trend { font-size: 9px; font-weight: 500; padding: 1px 4px; border-radius: 3px; }
  .wt-up { color: #30D158; background: rgba(48,209,88,0.12); }
  .wt-down { color: #FF453A; background: rgba(255,69,58,0.12); }

  /* Widget: chart */
  .wchart { display: flex; align-items: flex-end; gap: 4px; height: 70px; padding-top: 4px; }
  .wchart-col { flex: 1; display: flex; flex-direction: column; align-items: center; gap: 3px; height: 100%; }
  .wchart-bar-wrap { flex: 1; width: 100%; display: flex; align-items: flex-end; }
  .wchart-bar { width: 100%; border-radius: 3px 3px 0 0; min-height: 3px; opacity: 0.6; transition: opacity 0.12s; }
  .widget-card:hover .wchart-bar { opacity: 1; }
  .wchart-label { font-size: 9px; color: rgba(255,255,255,0.30); font-family: "SF Mono", "JetBrains Mono", monospace; }

  /* Widget: table */
  .wtable-head { display: flex; gap: 4px; padding-bottom: 4px; border-bottom: 1px solid rgba(255,255,255,0.06); margin-bottom: 2px; }
  .wtable-th { flex: 1; font-size: 9px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em; color: rgba(255,255,255,0.28); }
  .wtable-row { display: flex; gap: 4px; padding: 3px 0; border-bottom: 1px solid rgba(255,255,255,0.03); }
  .wtable-row:last-child { border-bottom: none; }
  .wtable-td { flex: 1; font-size: 11px; color: rgba(255,255,255,0.60); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; display: flex; align-items: center; gap: 4px; }
  .wtable-td-first { font-weight: 500; color: rgba(255,255,255,0.80); }
  .wtable-dot { width: 5px; height: 5px; border-radius: 50%; flex-shrink: 0; }

  /* Widget: activity */
  .wact-row { display: flex; align-items: flex-start; gap: 7px; padding: 3px 0; }
  .wact-dot { width: 5px; height: 5px; border-radius: 50%; margin-top: 4px; flex-shrink: 0; }
  .wact-text { flex: 1; font-size: 11px; color: rgba(255,255,255,0.60); line-height: 1.35; }
  .wact-time { font-size: 9px; color: rgba(255,255,255,0.28); flex-shrink: 0; font-family: "SF Mono", "JetBrains Mono", monospace; }

  /* ---- Resize handle ---- */
  .sidebar-resize-handle {
    width: 5px; flex-shrink: 0; cursor: col-resize;
    position: relative; z-index: 5; margin: 0 -2px; transition: background 0.15s;
  }
  .sidebar-resize-handle:hover { background: rgba(255,255,255,0.08); }

  /* ---- AI Sidebar ---- */
  .ai-sidebar {
    flex-shrink: 0; border-left: 1px solid rgba(255,255,255,0.06);
    display: flex; flex-direction: column; overflow: hidden;
  }

  /* Back + New controls */
  .ai-controls {
    display: flex; align-items: center; justify-content: flex-end;
    padding: 8px 10px; gap: 6px;
    border-bottom: 1px solid rgba(255,255,255,0.06);
  }
  .ai-ctrl-btn {
    display: flex; align-items: center; gap: 5px;
    padding: 5px 10px; border-radius: 6px; border: none;
    background: rgba(255,255,255,0.06); color: rgba(255,255,255,0.60);
    font-size: 12px; font-family: inherit; cursor: pointer;
    transition: color 0.12s, background 0.12s;
  }
  .ai-ctrl-btn:hover { color: rgba(255,255,255,0.90); background: rgba(255,255,255,0.12); }

  .ai-section { padding: 16px 14px; display: flex; flex-direction: column; gap: 4px; }
  .ai-section-label {
    font-size: 11px; font-weight: 600; text-transform: uppercase;
    letter-spacing: 0.06em; color: rgba(255,255,255,0.35); padding: 0 6px 6px;
  }
  .ai-hint { font-size: 13px; color: rgba(255,255,255,0.50); line-height: 1.5; margin: 0; padding: 0 6px 8px; }
  .ai-suggestion {
    display: flex; align-items: center; gap: 10px;
    padding: 9px 10px; border-radius: 8px; border: none; background: none;
    color: rgba(255,255,255,0.60); font-size: 13px; font-family: inherit;
    text-align: left; cursor: pointer; transition: color 0.12s, background 0.12s;
  }
  .ai-suggestion:hover { color: rgba(255,255,255,0.95); background: rgba(255,255,255,0.07); }

  /* AI Chat */
  .ai-chat-area {
    flex: 1; overflow-y: auto; padding: 12px;
    display: flex; flex-direction: column; gap: 10px; scrollbar-width: none;
  }
  .ai-chat-area::-webkit-scrollbar { display: none; }
  .ai-msg { display: flex; align-items: flex-end; gap: 6px; }
  .ai-msg-user { flex-direction: row-reverse; }
  .ai-msg-avatar {
    width: 20px; height: 20px; border-radius: 6px;
    background: linear-gradient(135deg, rgba(10,132,255,0.25), rgba(191,90,242,0.25));
    display: flex; align-items: center; justify-content: center;
    color: #0A84FF; flex-shrink: 0; margin-bottom: 1px;
  }
  .ai-msg-bubble { max-width: 85%; padding: 8px 12px; font-size: 13px; line-height: 1.5; color: rgba(255,255,255,0.85); border-radius: 10px; }
  .ai-bubble-user { background: rgba(10,132,255,0.15); border: 1px solid rgba(10,132,255,0.18); border-radius: 10px 10px 4px 10px; }
  .ai-bubble-agent { background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.08); border-radius: 10px 10px 10px 4px; }
  .ai-typing-bubble { display: flex; align-items: center; gap: 3px; padding: 9px 12px; }
  .ai-typing-dot { width: 5px; height: 5px; border-radius: 50%; background: rgba(255,255,255,0.35); animation: ai-dot-bounce 1.2s ease-in-out infinite; }
  .ai-typing-dot:nth-child(2) { animation-delay: 0.15s; }
  .ai-typing-dot:nth-child(3) { animation-delay: 0.30s; }
  @keyframes ai-dot-bounce { 0%, 80%, 100% { transform: translateY(0); opacity: 0.35; } 40% { transform: translateY(-3px); opacity: 0.8; } }

  /* AI Input */
  .ai-input-area { margin-top: auto; padding: 12px 12px 14px; }
  .ai-input-row {
    display: flex; align-items: center; gap: 8px;
    border-radius: 12px; padding: 0 8px 0 14px; height: 42px;
    border: 1px solid rgba(255,255,255,0.18) !important;
    background-color: rgba(255,255,255,0.08) !important;
  }
  .ai-input-row:focus-within { border-color: rgba(255,255,255,0.30) !important; background-color: rgba(255,255,255,0.12) !important; }
  .ai-input { flex: 1; background: none; border: none; outline: none; font-size: 13px; font-family: inherit; color: rgba(255,255,255,0.85); }
  .ai-input::placeholder { color: rgba(255,255,255,0.40); }
  .ai-send-btn {
    width: 28px; height: 28px; border-radius: 50%; border: none;
    background: rgba(255,255,255,0.20); color: rgba(255,255,255,0.80);
    display: flex; align-items: center; justify-content: center;
    cursor: pointer; flex-shrink: 0; transition: background 0.12s;
  }
  .ai-send-btn:hover { background: rgba(255,255,255,0.32); }
  .ai-send-btn:disabled { opacity: 0.3; cursor: not-allowed; }

  /* ---- Widget detail view ---- */
  .detail-source {
    font-size: 11px; color: rgba(255,255,255,0.40);
    background: rgba(255,255,255,0.06);
    padding: 2px 8px; border-radius: 6px;
  }

  .widget-detail-body {
    flex: 1; overflow-y: auto; padding: 20px;
    scrollbar-width: thin; scrollbar-color: rgba(255,255,255,0.10) transparent;
  }
  .widget-detail-body::-webkit-scrollbar { width: 4px; }
  .widget-detail-body::-webkit-scrollbar-track { background: transparent; }
  .widget-detail-body::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.10); border-radius: 2px; }

  /* Expanded stats — card grid */
  .wd-stats-grid {
    display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
    gap: 12px;
  }
  .wd-stat-card {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 10px; padding: 16px;
    display: flex; flex-direction: column; gap: 4px;
  }
  .wd-stat-card:hover { border-color: rgba(255,255,255,0.14); }
  .wd-stat-label { font-size: 12px; color: rgba(255,255,255,0.45); }
  .wd-stat-value {
    font-size: 22px; font-weight: 700; color: rgba(255,255,255,0.90);
    font-family: "SF Mono", "JetBrains Mono", monospace;
    letter-spacing: -0.02em;
  }
  .wd-stat-trend { font-size: 12px; font-weight: 500; padding: 2px 6px; border-radius: 5px; width: fit-content; }

  /* Expanded chart — taller, with values */
  .wd-chart {
    display: flex; align-items: flex-end; gap: 8px;
    height: 220px; padding: 10px 0;
  }
  .wd-chart-col {
    flex: 1; display: flex; flex-direction: column; align-items: center; gap: 6px;
    height: 100%;
  }
  .wd-chart-bar-wrap { flex: 1; width: 100%; display: flex; align-items: flex-end; }
  .wd-chart-bar {
    width: 100%; border-radius: 4px 4px 0 0; min-height: 4px; opacity: 0.75;
    transition: opacity 0.15s;
  }
  .wd-chart-bar:hover { opacity: 1; }
  .wd-chart-label { font-size: 11px; color: rgba(255,255,255,0.45); font-weight: 500; }
  .wd-chart-val {
    font-size: 10px; color: rgba(255,255,255,0.35);
    font-family: "SF Mono", "JetBrains Mono", monospace;
  }

  /* Expanded table */
  .wd-table { width: 100%; }
  .wd-table-head {
    display: flex; gap: 4px; padding: 8px 12px;
    border-bottom: 1px solid rgba(255,255,255,0.08);
    background: rgba(255,255,255,0.03); border-radius: 8px 8px 0 0;
  }
  .wd-th {
    flex: 1; font-size: 11px; font-weight: 600; text-transform: uppercase;
    letter-spacing: 0.05em; color: rgba(255,255,255,0.35);
  }
  .wd-table-row {
    display: flex; gap: 4px; padding: 10px 12px;
    border-bottom: 1px solid rgba(255,255,255,0.04);
    transition: background 0.10s;
  }
  .wd-table-row:hover { background: rgba(255,255,255,0.04); }
  .wd-table-row:last-child { border-bottom: none; }
  .wd-td {
    flex: 1; font-size: 13px; color: rgba(255,255,255,0.65);
    display: flex; align-items: center; gap: 6px;
  }
  .wd-td-first { font-weight: 500; color: rgba(255,255,255,0.88); }
  .wd-td-dot { width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0; }

  /* Expanded activity */
  .wd-activity { display: flex; flex-direction: column; gap: 2px; }
  .wd-act-row {
    display: flex; align-items: flex-start; gap: 10px;
    padding: 10px 8px; border-radius: 8px;
    transition: background 0.10s;
  }
  .wd-act-row:hover { background: rgba(255,255,255,0.04); }
  .wd-act-dot { width: 7px; height: 7px; border-radius: 50%; margin-top: 5px; flex-shrink: 0; }
  .wd-act-text { flex: 1; font-size: 13px; color: rgba(255,255,255,0.70); line-height: 1.45; }
  .wd-act-time {
    font-size: 11px; color: rgba(255,255,255,0.35); flex-shrink: 0;
    font-family: "SF Mono", "JetBrains Mono", monospace;
  }
</style>
