"""Tests for WebMCP browser integration."""

from __future__ import annotations

from unittest.mock import AsyncMock

from pocketpaw.browser.snapshot import AccessibilityNode, SnapshotGenerator
from pocketpaw.browser.webmcp.discovery import WebMCPDiscovery
from pocketpaw.browser.webmcp.executor import WebMCPExecutor
from pocketpaw.browser.webmcp.models import WebMCPToolDef

# --- WebMCPToolDef ---


class TestWebMCPToolDef:
    def test_defaults(self):
        tool = WebMCPToolDef(name="search", description="Search the site")
        assert tool.name == "search"
        assert tool.description == "Search the site"
        assert tool.input_schema == {}
        assert tool.source == "imperative"

    def test_declarative_source(self):
        tool = WebMCPToolDef(
            name="add_to_cart",
            description="Add item",
            input_schema={"type": "object", "properties": {"id": {"type": "string"}}},
            source="declarative",
        )
        assert tool.source == "declarative"
        assert "id" in tool.input_schema["properties"]


# --- WebMCPDiscovery ---


class TestWebMCPDiscovery:
    async def test_discover_imperative_tools(self):
        page = AsyncMock()
        page.url = "https://example.com"
        page.evaluate = AsyncMock(
            side_effect=[
                # First call: imperative discovery
                [
                    {
                        "name": "search",
                        "description": "Search products",
                        "inputSchema": {
                            "type": "object",
                            "properties": {"query": {"type": "string"}},
                        },
                        "source": "imperative",
                    }
                ],
                # Second call: declarative discovery
                [],
            ]
        )

        tools = await WebMCPDiscovery.discover(page)
        assert len(tools) == 1
        assert tools[0].name == "search"
        assert tools[0].source == "imperative"
        assert tools[0].description == "Search products"

    async def test_discover_declarative_tools(self):
        page = AsyncMock()
        page.url = "https://example.com"
        page.evaluate = AsyncMock(
            side_effect=[
                # First call: imperative discovery
                [],
                # Second call: declarative discovery
                [
                    {
                        "name": "login",
                        "description": "Log in to the site",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "username": {"type": "string"},
                                "password": {"type": "string"},
                            },
                            "required": ["username", "password"],
                        },
                        "source": "declarative",
                    }
                ],
            ]
        )

        tools = await WebMCPDiscovery.discover(page)
        assert len(tools) == 1
        assert tools[0].name == "login"
        assert tools[0].source == "declarative"

    async def test_discover_no_webmcp(self):
        page = AsyncMock()
        page.url = "https://example.com"
        page.evaluate = AsyncMock(return_value=[])

        tools = await WebMCPDiscovery.discover(page)
        assert tools == []

    async def test_discover_handles_js_error(self):
        page = AsyncMock()
        page.url = "https://example.com"
        page.evaluate = AsyncMock(side_effect=Exception("JS error"))

        tools = await WebMCPDiscovery.discover(page)
        assert tools == []

    async def test_discover_skips_nameless_tools(self):
        page = AsyncMock()
        page.url = "https://example.com"
        page.evaluate = AsyncMock(
            side_effect=[
                [{"name": "", "description": "No name", "inputSchema": {}}],
                [],
            ]
        )

        tools = await WebMCPDiscovery.discover(page)
        assert tools == []

    async def test_discover_both_types(self):
        page = AsyncMock()
        page.url = "https://example.com"
        page.evaluate = AsyncMock(
            side_effect=[
                [{"name": "api_tool", "description": "API", "inputSchema": {}}],
                [{"name": "form_tool", "description": "Form", "inputSchema": {}}],
            ]
        )

        tools = await WebMCPDiscovery.discover(page)
        assert len(tools) == 2
        assert tools[0].name == "api_tool"
        assert tools[0].source == "imperative"
        assert tools[1].name == "form_tool"
        assert tools[1].source == "declarative"


# --- WebMCPExecutor ---


class TestWebMCPExecutor:
    async def test_execute_imperative_tool(self):
        page = AsyncMock()
        page.evaluate = AsyncMock(return_value={"result": "Item added to cart"})

        tools = [
            WebMCPToolDef(
                name="add_to_cart",
                description="Add item",
                input_schema={},
                source="imperative",
            )
        ]

        result = await WebMCPExecutor.execute(page, "add_to_cart", {"product_id": "123"}, tools)
        assert result == "Item added to cart"

    async def test_execute_declarative_tool(self):
        page = AsyncMock()
        page.evaluate = AsyncMock(return_value={"result": "Form submitted successfully"})

        tools = [WebMCPToolDef(name="search", description="Search", source="declarative")]

        result = await WebMCPExecutor.execute(page, "search", {"q": "test"}, tools)
        assert result == "Form submitted successfully"

    async def test_execute_returns_json_result(self):
        page = AsyncMock()
        page.evaluate = AsyncMock(return_value={"result": {"items": [1, 2, 3], "total": 3}})

        tools = [WebMCPToolDef(name="list_items", description="List")]

        result = await WebMCPExecutor.execute(page, "list_items", {}, tools)
        assert '"items"' in result
        assert '"total": 3' in result

    async def test_execute_tool_not_found(self):
        page = AsyncMock()
        tools = [WebMCPToolDef(name="other_tool", description="Other")]

        result = await WebMCPExecutor.execute(page, "missing_tool", {}, tools)
        assert "Error" in result
        assert "not available" in result

    async def test_execute_tool_returns_error(self):
        page = AsyncMock()
        page.evaluate = AsyncMock(return_value={"error": "Permission denied"})

        tools = [WebMCPToolDef(name="restricted", description="Restricted")]

        result = await WebMCPExecutor.execute(page, "restricted", {}, tools)
        assert "Error" in result
        assert "Permission denied" in result

    async def test_execute_handles_exception(self):
        page = AsyncMock()
        page.evaluate = AsyncMock(side_effect=RuntimeError("Page crashed"))

        tools = [WebMCPToolDef(name="crash", description="Crash")]

        result = await WebMCPExecutor.execute(page, "crash", {}, tools)
        assert "Error" in result
        assert "Page crashed" in result


# --- Snapshot WebMCP integration ---


class TestSnapshotWebMCP:
    def test_snapshot_with_webmcp_tools(self):
        gen = SnapshotGenerator()
        tree = AccessibilityNode(role="WebArea", name="", children=[])
        tools = [
            WebMCPToolDef(
                name="search",
                description="Search products",
                input_schema={
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                },
            ),
            WebMCPToolDef(
                name="add_to_cart",
                description="Add item to cart",
                input_schema={
                    "type": "object",
                    "properties": {
                        "product_id": {"type": "string"},
                        "quantity": {"type": "number"},
                    },
                },
            ),
        ]

        text, _ = gen.generate(tree, title="Shop", url="https://shop.com", webmcp_tools=tools)

        assert "--- WebMCP Tools ---" in text
        assert 'search(query: string) — "Search products"' in text
        assert 'add_to_cart(product_id: string, quantity: number) — "Add item to cart"' in text

    def test_snapshot_without_webmcp_tools(self):
        gen = SnapshotGenerator()
        tree = AccessibilityNode(role="WebArea", name="", children=[])

        text, _ = gen.generate(tree, title="Page", webmcp_tools=None)
        assert "WebMCP" not in text

    def test_snapshot_empty_webmcp_tools(self):
        gen = SnapshotGenerator()
        tree = AccessibilityNode(role="WebArea", name="", children=[])

        text, _ = gen.generate(tree, title="Page", webmcp_tools=[])
        assert "WebMCP" not in text

    def test_snapshot_tool_without_description(self):
        gen = SnapshotGenerator()
        tree = AccessibilityNode(role="WebArea", name="", children=[])
        tools = [WebMCPToolDef(name="ping", description="")]

        text, _ = gen.generate(tree, webmcp_tools=tools)
        assert "- ping()" in text
        assert "—" not in text.split("ping()")[1].split("\n")[0]

    def test_snapshot_tool_without_params(self):
        gen = SnapshotGenerator()
        tree = AccessibilityNode(role="WebArea", name="", children=[])
        tools = [WebMCPToolDef(name="status", description="Get status")]

        text, _ = gen.generate(tree, webmcp_tools=tools)
        assert 'status() — "Get status"' in text
