"""WebMCP tool executor for invoking tools on browser pages."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

from .models import WebMCPToolDef

if TYPE_CHECKING:
    from playwright.async_api import Page

logger = logging.getLogger(__name__)

# JavaScript to call an imperative WebMCP tool via navigator.modelContext
_CALL_IMPERATIVE_JS = """
async (args) => {
    const { toolName, input } = args;
    if (!navigator.modelContext || typeof navigator.modelContext.callTool !== 'function') {
        return { error: 'WebMCP not available on this page' };
    }
    try {
        const result = await navigator.modelContext.callTool(toolName, input);
        return { result: result };
    } catch (e) {
        return { error: e.message || String(e) };
    }
}
"""

# JavaScript to submit a declarative WebMCP form
_CALL_DECLARATIVE_JS = """
async (args) => {
    const { toolName, input } = args;
    const form = document.querySelector(`form[toolname="${toolName}"]`);
    if (!form) {
        return { error: `No form found with toolname="${toolName}"` };
    }
    try {
        for (const [key, value] of Object.entries(input)) {
            const field = form.querySelector(`[name="${key}"], [id="${key}"]`);
            if (field) {
                if (field.type === 'checkbox') {
                    field.checked = Boolean(value);
                } else {
                    field.value = value;
                }
                field.dispatchEvent(new Event('input', { bubbles: true }));
                field.dispatchEvent(new Event('change', { bubbles: true }));
            }
        }
        form.submit();
        return { result: 'Form submitted successfully' };
    } catch (e) {
        return { error: e.message || String(e) };
    }
}
"""


class WebMCPExecutor:
    """Executes WebMCP tool calls on browser pages."""

    @staticmethod
    async def execute(
        page: Page,
        tool_name: str,
        tool_input: dict[str, Any],
        available_tools: list[WebMCPToolDef],
    ) -> str:
        """Execute a WebMCP tool on the current page.

        Args:
            page: Playwright Page instance
            tool_name: Name of the tool to invoke
            tool_input: Input parameters for the tool
            available_tools: List of currently available WebMCP tools (from discovery)

        Returns:
            Result string from the tool execution
        """
        # Find the tool in available tools
        tool_def = next((t for t in available_tools if t.name == tool_name), None)
        if tool_def is None:
            return f"Error: WebMCP tool '{tool_name}' not available on this page"

        logger.info("Executing WebMCP tool '%s' (source=%s)", tool_name, tool_def.source)

        try:
            if tool_def.source == "declarative":
                result = await page.evaluate(
                    _CALL_DECLARATIVE_JS,
                    {"toolName": tool_name, "input": tool_input},
                )
            else:
                result = await page.evaluate(
                    _CALL_IMPERATIVE_JS,
                    {"toolName": tool_name, "input": tool_input},
                )

            if isinstance(result, dict) and "error" in result:
                return f"Error: WebMCP tool '{tool_name}' failed: {result['error']}"

            # Format result for the agent
            if isinstance(result, dict) and "result" in result:
                value = result["result"]
                if isinstance(value, dict | list):
                    return json.dumps(value, indent=2)
                return str(value)

            return str(result)

        except Exception as e:
            return f"Error: WebMCP tool '{tool_name}' failed: {e}"
