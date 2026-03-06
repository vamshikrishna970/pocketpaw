# Browser automation module for PocketPaw
# Changes: Added exports for snapshot, driver, and session components
#
# This module provides Playwright-based browser automation with semantic
# accessibility tree snapshots for AI agent control.
"""Browser automation module for PocketPaw."""

from .driver import BrowserDriver, NavigationResult
from .session import BrowserSession, BrowserSessionManager, get_browser_session_manager
from .snapshot import AccessibilityNode, RefMap, SnapshotGenerator
from .webmcp import WebMCPDiscovery, WebMCPExecutor, WebMCPToolDef

__all__ = [
    # Snapshot
    "RefMap",
    "AccessibilityNode",
    "SnapshotGenerator",
    # Driver
    "BrowserDriver",
    "NavigationResult",
    # Session
    "BrowserSession",
    "BrowserSessionManager",
    "get_browser_session_manager",
    # WebMCP
    "WebMCPDiscovery",
    "WebMCPExecutor",
    "WebMCPToolDef",
]
