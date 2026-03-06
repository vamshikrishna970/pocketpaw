# WebMCP Browser Integration Design

**Date:** 2026-03-06
**Issue:** #156
**Priority:** Low (experimental, Chrome Canary only)

## Overview

Add WebMCP support to PocketPaw's browser module, enabling structured tool calls on websites that expose them via the WebMCP API, with fallback to the existing accessibility tree approach.

## Architecture

Hybrid enhancement inside the existing `browser/` module. A new `browser/webmcp/` subpackage handles discovery and execution, surfaced through `BrowserDriver` and `BrowserTool`.

## New Files

- `browser/webmcp/__init__.py` — exports
- `browser/webmcp/models.py` — `WebMCPToolDef` dataclass
- `browser/webmcp/discovery.py` — `WebMCPDiscovery`: detects imperative and declarative WebMCP tools via `page.evaluate()`
- `browser/webmcp/executor.py` — `WebMCPExecutor`: invokes WebMCP tools by name with structured input

## Modified Files

- `browser/driver.py` — `NavigationResult` gains `webmcp_tools: list[WebMCPToolDef]`. `_take_snapshot()` runs discovery when enabled.
- `browser/snapshot.py` — `SnapshotGenerator` appends `--- WebMCP Tools ---` section.
- `tools/builtin/browser.py` — `BrowserTool` gains `webmcp` action.
- `config.py` — New setting `webmcp_enabled: bool = False`.

## Data Flow

1. User sets `POCKETPAW_WEBMCP_ENABLED=true`
2. `BrowserDriver.navigate(url)` loads page, calls `WebMCPDiscovery.discover(page)`
3. Discovery returns `list[WebMCPToolDef]`, stored on `NavigationResult.webmcp_tools`
4. Snapshot includes tool listing — agent sees available structured actions
5. Agent calls `{"action": "webmcp", "tool_name": "...", "input": {...}}`
6. `BrowserTool` delegates to `WebMCPExecutor.execute(page, tool_name, input)`
7. Executor returns result string

## Error Handling

- `navigator.modelContext` missing → empty tools list, no error
- Tool invocation fails → `"Error: WebMCP tool '<name>' failed: <message>"`
- Tool not found → `"Error: WebMCP tool '<name>' not available on this page"`

## Config

- `webmcp_enabled: bool = False` — opt-in, default off (experimental)
- Env var: `POCKETPAW_WEBMCP_ENABLED=true`
