"""WebMCP tool definition model."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class WebMCPToolDef:
    """A tool exposed by a website via the WebMCP API.

    Attributes:
        name: Tool name (e.g. "add_to_cart")
        description: Human-readable description
        input_schema: JSON Schema for the tool's input parameters
        source: How the tool was discovered ("imperative" or "declarative")
    """

    name: str
    description: str
    input_schema: dict[str, Any] = field(default_factory=dict)
    source: str = "imperative"
