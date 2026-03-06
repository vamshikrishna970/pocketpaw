"""WebMCP tool discovery from browser pages."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from .models import WebMCPToolDef

if TYPE_CHECKING:
    from playwright.async_api import Page

logger = logging.getLogger(__name__)

# JavaScript to discover imperative WebMCP tools registered via navigator.modelContext
_DISCOVER_IMPERATIVE_JS = """
() => {
    if (!navigator.modelContext || typeof navigator.modelContext.getTools !== 'function') {
        return [];
    }
    try {
        const tools = navigator.modelContext.getTools();
        return tools.map(t => ({
            name: t.name || '',
            description: t.description || '',
            inputSchema: t.inputSchema || {},
            source: 'imperative'
        }));
    } catch (e) {
        return [];
    }
}
"""

# JavaScript to discover declarative WebMCP tools from forms with toolname attribute
_DISCOVER_DECLARATIVE_JS = """
() => {
    const forms = document.querySelectorAll('form[toolname]');
    return Array.from(forms).map(form => {
        const inputs = form.querySelectorAll('input, select, textarea');
        const properties = {};
        const required = [];

        for (const input of inputs) {
            const name = input.name || input.id;
            if (!name) continue;

            const prop = { type: 'string' };
            if (input.type === 'number') prop.type = 'number';
            if (input.type === 'checkbox') prop.type = 'boolean';
            if (input.placeholder) prop.description = input.placeholder;

            properties[name] = prop;
            if (input.required) required.push(name);
        }

        return {
            name: form.getAttribute('toolname') || '',
            description: form.getAttribute('tooldescription') || form.title || '',
            inputSchema: {
                type: 'object',
                properties: properties,
                required: required
            },
            source: 'declarative'
        };
    });
}
"""


class WebMCPDiscovery:
    """Discovers WebMCP tools exposed by a web page."""

    @staticmethod
    async def discover(page: Page) -> list[WebMCPToolDef]:
        """Discover all WebMCP tools on the current page.

        Checks both the imperative API (navigator.modelContext.getTools())
        and declarative API (forms with toolname attribute).

        Args:
            page: Playwright Page instance

        Returns:
            List of discovered WebMCP tool definitions
        """
        tools: list[WebMCPToolDef] = []

        # Discover imperative tools
        try:
            imperative_raw: list[dict[str, Any]] = await page.evaluate(_DISCOVER_IMPERATIVE_JS)
            for raw in imperative_raw:
                if raw.get("name"):
                    tools.append(
                        WebMCPToolDef(
                            name=raw["name"],
                            description=raw.get("description", ""),
                            input_schema=raw.get("inputSchema", {}),
                            source="imperative",
                        )
                    )
        except Exception as e:
            logger.debug("WebMCP imperative discovery failed: %s", e)

        # Discover declarative tools
        try:
            declarative_raw: list[dict[str, Any]] = await page.evaluate(_DISCOVER_DECLARATIVE_JS)
            for raw in declarative_raw:
                if raw.get("name"):
                    tools.append(
                        WebMCPToolDef(
                            name=raw["name"],
                            description=raw.get("description", ""),
                            input_schema=raw.get("inputSchema", {}),
                            source="declarative",
                        )
                    )
        except Exception as e:
            logger.debug("WebMCP declarative discovery failed: %s", e)

        if tools:
            logger.info("Discovered %d WebMCP tool(s) on %s", len(tools), page.url)

        return tools
