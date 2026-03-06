"""WebMCP browser integration for structured website interaction."""

from .discovery import WebMCPDiscovery
from .executor import WebMCPExecutor
from .models import WebMCPToolDef

__all__ = ["WebMCPDiscovery", "WebMCPExecutor", "WebMCPToolDef"]
