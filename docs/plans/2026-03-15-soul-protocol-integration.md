# Soul Protocol Integration Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Integrate soul-protocol into PocketPaw so the agent has persistent identity, psychology-informed memory, emotional state, OCEAN personality, and portable `.soul` files.

**Architecture:** Soul Protocol becomes an optional feature activated via `soul_enabled=true`. When enabled, a `SoulManager` singleton births/awakens a `Soul` at startup, swaps `SoulBootstrapProvider` into `AgentContextBuilder` for system prompt generation, injects soul tools into `_instantiate_all_tools()` for all backends, and feeds `soul.observe()` on every conversation turn. The existing `paw/` module has `SoulBridge`, `SoulBootstrapProvider`, and four tools already built, so this plan wires them into the main pipeline.

**Edge cases handled:**
1. **Corrupt/encrypted .soul file** -- SoulManager catches `SoulCorruptError`/`SoulEncryptedError` on awaken, backs up the corrupt file, and births a fresh soul with a warning log.
2. **Concurrent observe() calls** -- An `asyncio.Lock` in SoulManager serializes observe() calls so two rapid messages don't race on the Soul instance.
3. **Periodic auto-save** -- A background task saves the soul every 5 minutes (configurable) so a crash doesn't lose all state since startup.
4. **Runtime settings toggle** -- `reset_router()` also tears down or initializes the soul manager when `soul_enabled` changes mid-session.
5. **Multiple sessions feeding one soul** -- The observe lock serializes all sessions. The soul is designed to be a single persistent identity, so this is intentional, but the lock prevents state corruption.
6. **Large soul files over time** -- soul-protocol has built-in memory consolidation via `soul.reflect()`. We call it periodically alongside auto-save to keep memory lean.

**Tech Stack:** soul-protocol (PyPI), pydantic, asyncio, existing PocketPaw protocols

---

### Task 1: Add soul-protocol as an optional dependency

**Files:**
- Modify: `pyproject.toml:66-220` (optional-dependencies section)

**Step 1: Add the `[soul]` extra**

After the `memory` extra (line ~97), add:

```toml
soul = [
    "soul-protocol[engine]>=0.2.3",
]
```

In the `all-tools` list (around line 177), add:

```toml
    # soul
    "soul-protocol[engine]>=0.2.3",
```

In the `all` list (around line 202), add the same line.

**Step 2: Install and verify**

Run: `uv sync --dev && uv pip install "soul-protocol[engine]"`
Then: `uv run python -c "from soul_protocol import Soul; print('ok')"`
Expected: `ok`

**Step 3: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "feat: add soul-protocol as optional dependency"
```

---

### Task 2: Add soul config fields to Settings

**Files:**
- Modify: `src/pocketpaw/config.py` (Settings class, after `owner_id` field ~line 697)

**Step 1: Add soul settings fields**

```python
    # Soul Protocol
    soul_enabled: bool = Field(
        default=False,
        description="Enable soul-protocol for persistent AI identity, memory, and emotion",
    )
    soul_name: str = Field(
        default="Paw",
        description="Name for the soul identity",
    )
    soul_archetype: str = Field(
        default="The Helpful Assistant",
        description="Soul archetype (e.g. 'The Coding Expert', 'The Compassionate Creator')",
    )
    soul_persona: str = Field(
        default="",
        description="Custom persona description for the soul (empty = auto-generated)",
    )
    soul_values: list[str] = Field(
        default_factory=lambda: ["helpfulness", "precision", "privacy"],
        description="Core values for the soul identity",
    )
    soul_ocean: dict[str, float] = Field(
        default_factory=lambda: {
            "openness": 0.7,
            "conscientiousness": 0.85,
            "extraversion": 0.5,
            "agreeableness": 0.8,
            "neuroticism": 0.2,
        },
        description="OCEAN Big Five personality traits (0.0-1.0)",
    )
    soul_communication: dict[str, str] = Field(
        default_factory=lambda: {"warmth": "medium", "verbosity": "low"},
        description="Communication style settings for the soul",
    )
    soul_path: str = Field(
        default="",
        description="Path to .soul file (empty = ~/.pocketpaw/soul/)",
    )
    soul_auto_save_interval: int = Field(
        default=300,
        description="Auto-save soul state interval in seconds (0 = disabled)",
    )
```

**Step 2: Verify**

Run: `uv run ruff check src/pocketpaw/config.py`
Expected: no errors

**Step 3: Commit**

```bash
git add src/pocketpaw/config.py
git commit -m "feat: add soul-protocol settings to config"
```

---

### Task 3: Create the SoulManager singleton

**Files:**
- Create: `src/pocketpaw/soul/__init__.py`
- Create: `src/pocketpaw/soul/manager.py`
- Test: `tests/test_soul_manager.py`

SoulManager owns the Soul lifecycle, SoulBridge, SoulBootstrapProvider, and tool instances. Lazy singleton via `get_soul_manager()`. Includes concurrency lock, corrupt file recovery, and periodic auto-save.

**Step 1: Write the failing test**

```python
# tests/test_soul_manager.py
"""Tests for SoulManager lifecycle."""
import asyncio

import pytest


def _has_soul_protocol() -> bool:
    try:
        import soul_protocol  # noqa: F401
        return True
    except ImportError:
        return False


pytestmark = pytest.mark.skipif(
    not _has_soul_protocol(), reason="soul-protocol not installed"
)


@pytest.fixture(autouse=True)
def _reset_soul():
    from pocketpaw.soul.manager import _reset_manager
    _reset_manager()
    yield
    _reset_manager()


@pytest.fixture
def soul_settings(tmp_path):
    from pocketpaw.config import Settings
    return Settings(
        soul_enabled=True,
        soul_name="TestSoul",
        soul_archetype="The Test Helper",
        soul_path=str(tmp_path / "test.soul"),
        soul_auto_save_interval=0,  # disable auto-save in tests
    )


class TestSoulManager:
    async def test_initialize_births_new_soul(self, soul_settings):
        from pocketpaw.soul.manager import SoulManager
        mgr = SoulManager(soul_settings)
        await mgr.initialize()
        assert mgr.soul is not None
        assert mgr.soul.name == "TestSoul"
        assert mgr.bridge is not None
        assert mgr.bootstrap_provider is not None

    async def test_save_and_reawaken(self, soul_settings, tmp_path):
        from pocketpaw.soul.manager import SoulManager, _reset_manager
        mgr = SoulManager(soul_settings)
        await mgr.initialize()
        await mgr.save()
        assert (tmp_path / "test.soul").exists()

        _reset_manager()
        mgr2 = SoulManager(soul_settings)
        await mgr2.initialize()
        assert mgr2.soul.name == "TestSoul"

    async def test_observe_does_not_raise(self, soul_settings):
        from pocketpaw.soul.manager import SoulManager
        mgr = SoulManager(soul_settings)
        await mgr.initialize()
        await mgr.observe("Hello", "Hi there!")

    async def test_get_tools_returns_four(self, soul_settings):
        from pocketpaw.soul.manager import SoulManager
        mgr = SoulManager(soul_settings)
        await mgr.initialize()
        tools = mgr.get_tools()
        assert len(tools) == 4
        names = {t.name for t in tools}
        assert names == {"soul_remember", "soul_recall", "soul_edit_core", "soul_status"}

    async def test_corrupt_soul_file_falls_back_to_birth(self, soul_settings, tmp_path):
        """Edge case #1: corrupt .soul file should not crash, should birth fresh."""
        from pocketpaw.soul.manager import SoulManager
        # Write garbage to the soul file
        soul_file = tmp_path / "test.soul"
        soul_file.write_text("this is not a valid soul file")

        mgr = SoulManager(soul_settings)
        await mgr.initialize()
        # Should have birthed a new soul instead of crashing
        assert mgr.soul is not None
        assert mgr.soul.name == "TestSoul"
        # Corrupt file should be backed up
        backup = tmp_path / "test.soul.corrupt"
        assert backup.exists()

    async def test_concurrent_observe_is_serialized(self, soul_settings):
        """Edge case #2: concurrent observe() calls don't race."""
        from pocketpaw.soul.manager import SoulManager
        mgr = SoulManager(soul_settings)
        await mgr.initialize()

        # Fire 10 concurrent observe calls
        tasks = [
            mgr.observe(f"msg {i}", f"reply {i}")
            for i in range(10)
        ]
        await asyncio.gather(*tasks)
        # Should not raise any exceptions

    async def test_shutdown_saves_and_stops_autosave(self, soul_settings, tmp_path):
        """Edge case #3: shutdown persists state and cancels auto-save."""
        from pocketpaw.config import Settings
        from pocketpaw.soul.manager import SoulManager

        settings = Settings(
            soul_enabled=True,
            soul_name="ShutdownTest",
            soul_path=str(tmp_path / "shutdown.soul"),
            soul_auto_save_interval=1,  # 1 second for fast test
        )
        mgr = SoulManager(settings)
        await mgr.initialize()
        mgr.start_auto_save()

        await mgr.observe("test", "test reply")
        await mgr.shutdown()

        assert (tmp_path / "shutdown.soul").exists()
        assert mgr._auto_save_task is None or mgr._auto_save_task.done()
```

**Step 2: Run to verify failure**

Run: `uv run pytest tests/test_soul_manager.py -v`
Expected: FAIL (ImportError)

**Step 3: Create the package**

```python
# src/pocketpaw/soul/__init__.py
"""Soul Protocol integration for PocketPaw."""
```

```python
# src/pocketpaw/soul/manager.py
"""SoulManager -- lifecycle management for the Soul instance.

Edge cases handled:
- Corrupt/encrypted .soul files: backs up and births fresh soul
- Concurrent observe(): serialized via asyncio.Lock
- Periodic auto-save: background task prevents data loss on crash
- Graceful shutdown: saves state and cancels auto-save task
"""

from __future__ import annotations

import asyncio
import logging
import shutil
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pocketpaw.config import Settings
    from pocketpaw.paw.soul_bridge import SoulBootstrapProvider, SoulBridge
    from pocketpaw.tools.protocol import BaseTool

logger = logging.getLogger(__name__)

_manager: SoulManager | None = None


def get_soul_manager() -> SoulManager | None:
    """Return the global SoulManager, or None if not initialized."""
    return _manager


def _reset_manager() -> None:
    """Reset singleton (for tests)."""
    global _manager
    _manager = None


class SoulManager:
    """Manages the Soul instance lifecycle."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self.soul: Any = None
        self.bridge: SoulBridge | None = None
        self.bootstrap_provider: SoulBootstrapProvider | None = None
        self._initialized = False
        self._observe_lock = asyncio.Lock()  # Edge case #2: serialize observe()
        self._auto_save_task: asyncio.Task | None = None
        self._observe_count = 0

    @property
    def soul_dir(self) -> Path:
        if self._settings.soul_path:
            p = Path(self._settings.soul_path)
            return p.parent if p.suffix == ".soul" else p
        from pocketpaw.config import get_config_dir
        return get_config_dir() / "soul"

    @property
    def soul_file(self) -> Path:
        if self._settings.soul_path:
            p = Path(self._settings.soul_path)
            if p.suffix == ".soul":
                return p
            return p / f"{self._settings.soul_name.lower()}.soul"
        return self.soul_dir / f"{self._settings.soul_name.lower()}.soul"

    async def initialize(self) -> None:
        """Birth or awaken the soul."""
        if self._initialized:
            return

        try:
            from soul_protocol import Soul
        except ImportError:
            logger.warning(
                "soul-protocol not installed. Install with: pip install pocketpaw[soul]"
            )
            return

        from pocketpaw.paw.soul_bridge import SoulBootstrapProvider, SoulBridge

        self.soul_dir.mkdir(parents=True, exist_ok=True)

        soul_path = self.soul_file
        if soul_path.exists():
            self.soul = await self._try_awaken(Soul, soul_path)
        else:
            self.soul = await self._birth_soul(Soul)

        # Fallback: if awaken returned None (corrupt file), birth fresh
        if self.soul is None:
            self.soul = await self._birth_soul(Soul)

        self.bridge = SoulBridge(self.soul)
        self.bootstrap_provider = SoulBootstrapProvider(self.soul)
        self._initialized = True

        global _manager
        _manager = self

        logger.info("Soul initialized: %s", self.soul.name)

    async def _try_awaken(self, soul_cls: type, soul_path: Path) -> Any | None:
        """Attempt to awaken a soul from file.

        Edge case #1: if the file is corrupt or encrypted, back it up
        and return None so the caller can birth a fresh soul.
        """
        try:
            logger.info("Awakening soul from %s", soul_path)
            return await soul_cls.awaken(soul_path)
        except Exception as exc:
            # Catch SoulCorruptError, SoulEncryptedError, and any other failure
            logger.warning(
                "Failed to awaken soul from %s: %s. Backing up and birthing fresh soul.",
                soul_path,
                exc,
            )
            backup_path = soul_path.with_suffix(".soul.corrupt")
            try:
                shutil.copy2(soul_path, backup_path)
                logger.info("Corrupt soul backed up to %s", backup_path)
            except OSError:
                logger.warning("Could not back up corrupt soul file")
            return None

    async def _birth_soul(self, soul_cls: type) -> Any:
        """Birth a new soul from settings."""
        s = self._settings
        persona = s.soul_persona or (
            f"I am {s.soul_name}, a persistent AI companion. "
            f"I value {', '.join(s.soul_values)}."
        )
        logger.info("Birthing new soul: %s", s.soul_name)
        return await soul_cls.birth(
            name=s.soul_name,
            archetype=s.soul_archetype,
            values=s.soul_values,
            persona=persona,
            ocean=s.soul_ocean if s.soul_ocean else None,
            communication=s.soul_communication if s.soul_communication else None,
        )

    async def observe(self, user_input: str, agent_output: str) -> None:
        """Record a conversation turn (serialized via lock).

        Edge case #2: multiple sessions or rapid messages can call observe()
        concurrently. The lock ensures the Soul's internal state isn't corrupted.
        """
        if self.bridge is None:
            return
        async with self._observe_lock:
            await self.bridge.observe(user_input, agent_output)
            self._observe_count += 1

    async def save(self) -> None:
        """Persist the soul to disk."""
        if self.soul is None:
            return
        try:
            await self.soul.export(self.soul_file)
            logger.debug("Soul saved to %s", self.soul_file)
        except Exception:
            logger.exception("Failed to save soul")

    def start_auto_save(self) -> None:
        """Start the periodic auto-save background task.

        Edge case #3: prevents data loss if the process crashes.
        Also runs memory consolidation via soul.reflect() to keep
        memory lean over time (edge case #6).
        """
        interval = self._settings.soul_auto_save_interval
        if interval <= 0 or self._auto_save_task is not None:
            return
        self._auto_save_task = asyncio.create_task(
            self._auto_save_loop(interval), name="soul-auto-save"
        )

    async def _auto_save_loop(self, interval: int) -> None:
        """Periodically save soul state and consolidate memory."""
        while True:
            await asyncio.sleep(interval)
            try:
                await self.save()
                # Edge case #6: consolidate memory periodically to keep .soul files lean
                if self.soul is not None and self._observe_count >= 10:
                    try:
                        await self.soul.reflect()
                        self._observe_count = 0
                        logger.debug("Soul memory consolidation complete")
                    except Exception:
                        logger.debug("Soul reflect() failed (non-fatal)", exc_info=True)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.debug("Soul auto-save failed (non-fatal)", exc_info=True)

    async def shutdown(self) -> None:
        """Save state and stop auto-save task. Called on AgentLoop.stop()."""
        # Cancel auto-save task
        if self._auto_save_task is not None and not self._auto_save_task.done():
            self._auto_save_task.cancel()
            try:
                await self._auto_save_task
            except asyncio.CancelledError:
                pass
            self._auto_save_task = None

        # Final save
        await self.save()
        logger.info("Soul shut down and saved")

    def get_tools(self) -> list[BaseTool]:
        """Return the four soul tools."""
        if self.soul is None:
            return []
        from pocketpaw.paw.tools import (
            SoulEditCoreTool,
            SoulRecallTool,
            SoulRememberTool,
            SoulStatusTool,
        )
        return [
            SoulRememberTool(self.soul),
            SoulRecallTool(self.soul),
            SoulEditCoreTool(self.soul),
            SoulStatusTool(self.soul),
        ]
```

**Step 4: Run tests**

Run: `uv run pytest tests/test_soul_manager.py -v`
Expected: PASS (or skipped if soul-protocol not installed)

**Step 5: Commit**

```bash
git add src/pocketpaw/soul/ tests/test_soul_manager.py
git commit -m "feat: add SoulManager with concurrency, auto-save, and corrupt file recovery"
```

---

### Task 4: Wire SoulManager into AgentLoop

**Files:**
- Modify: `src/pocketpaw/agents/loop.py`

This is the core wiring task. Four integration points: startup, observe after response, auto-save lifecycle, and shutdown. Also handles edge case #4 (runtime settings toggle) via `reset_router()`.

**Step 1: Add `_soul_manager` field to `__init__`**

At the end of `AgentLoop.__init__()` (after `self._active_tasks`), add:

```python
        # Soul Protocol (optional)
        self._soul_manager: Any = None  # SoulManager | None
```

**Step 2: Initialize soul in `start()`**

In `AgentLoop.start()`, after `settings = Settings.load()` (line 102) and before the GC task spawn (line 106), add:

```python
        # Initialize Soul if enabled
        if settings.soul_enabled:
            try:
                from pocketpaw.soul.manager import SoulManager

                self._soul_manager = SoulManager(settings)
                await self._soul_manager.initialize()
                if self._soul_manager.bootstrap_provider:
                    self.context_builder.bootstrap = self._soul_manager.bootstrap_provider
                self._soul_manager.start_auto_save()
            except Exception:
                logger.exception("Soul initialization failed, continuing without soul")
                self._soul_manager = None
```

**Step 3: Add soul observe + state emission after response storage**

In `_process_message_inner()`, after the auto-learn block (around line 698, after `t.add_done_callback(self._background_tasks.discard)`), add:

```python
                # Soul observation: feed turn for personality/memory evolution
                if self._soul_manager is not None and not cancelled:
                    t = asyncio.create_task(
                        self._soul_observe_and_emit(
                            message.content, full_response, session_key
                        )
                    )
                    self._background_tasks.add(t)
                    t.add_done_callback(self._background_tasks.discard)
```

**Step 4: Add the helper method to AgentLoop**

After `_auto_learn()` at the bottom of the class, add:

```python
    async def _soul_observe_and_emit(
        self, user_input: str, agent_output: str, session_key: str
    ) -> None:
        """Observe interaction and emit soul state event."""
        if self._soul_manager is None:
            return
        try:
            await self._soul_manager.observe(user_input, agent_output)
            soul = self._soul_manager.soul
            if soul is not None:
                state = soul.state
                await self.bus.publish_system(
                    SystemEvent(
                        event_type="soul_state",
                        data={
                            "mood": getattr(state, "mood", None),
                            "energy": getattr(state, "energy", None),
                            "session_key": session_key,
                        },
                    )
                )
        except Exception:
            logger.debug("Soul observation failed (non-fatal)", exc_info=True)
```

**Step 5: Handle shutdown in `stop()`**

In `AgentLoop.stop()`, before `logger.info("... Agent Loop stopped")`, add:

```python
        # Persist soul state and stop auto-save
        if self._soul_manager is not None:
            try:
                await self._soul_manager.shutdown()
            except Exception:
                logger.exception("Failed to shut down soul")
```

**Step 6: Handle runtime toggle in `reset_router()`**

Find the `reset_router()` method in AgentLoop. After the existing router reset logic, add soul toggle handling:

```python
        # Edge case #4: handle soul_enabled toggle at runtime
        settings = Settings.load()
        if settings.soul_enabled and self._soul_manager is None:
            try:
                from pocketpaw.soul.manager import SoulManager

                self._soul_manager = SoulManager(settings)
                # Can't await in sync method -- schedule initialization
                asyncio.create_task(self._initialize_soul_runtime())
            except Exception:
                logger.debug("Soul runtime init failed", exc_info=True)
        elif not settings.soul_enabled and self._soul_manager is not None:
            # Soul was disabled -- schedule teardown
            asyncio.create_task(self._teardown_soul_runtime())
```

Add the two helper methods:

```python
    async def _initialize_soul_runtime(self) -> None:
        """Initialize soul when enabled at runtime (edge case #4)."""
        if self._soul_manager is None:
            return
        try:
            await self._soul_manager.initialize()
            if self._soul_manager.bootstrap_provider:
                self.context_builder.bootstrap = self._soul_manager.bootstrap_provider
            self._soul_manager.start_auto_save()
        except Exception:
            logger.exception("Soul runtime initialization failed")
            self._soul_manager = None

    async def _teardown_soul_runtime(self) -> None:
        """Tear down soul when disabled at runtime (edge case #4)."""
        if self._soul_manager is None:
            return
        try:
            await self._soul_manager.shutdown()
        except Exception:
            logger.debug("Soul runtime teardown failed", exc_info=True)
        self._soul_manager = None
        # Restore default bootstrap provider
        from pocketpaw.bootstrap.default_provider import DefaultBootstrapProvider
        self.context_builder.bootstrap = DefaultBootstrapProvider()
```

**Step 7: Verify**

Run: `uv run ruff check src/pocketpaw/agents/loop.py`
Expected: no errors

**Step 8: Commit**

```bash
git add src/pocketpaw/agents/loop.py
git commit -m "feat: wire soul-protocol into agent loop with auto-save and runtime toggle"
```

---

### Task 5: Inject soul tools into the tool bridge

**Files:**
- Modify: `src/pocketpaw/agents/tool_bridge.py`

Soul tools need to be discoverable by all backends (OpenAI Agents, Google ADK, Codex CLI, OpenCode, Copilot). The tool_bridge's `_instantiate_all_tools()` is the single point where all builtin tools are collected.

**Step 1: Modify `_instantiate_all_tools()` to include soul tools**

At the end of `_instantiate_all_tools()` (before `return tools`), add:

```python
    # Inject soul tools if soul is active
    try:
        from pocketpaw.soul.manager import get_soul_manager

        soul_mgr = get_soul_manager()
        if soul_mgr is not None:
            tools.extend(soul_mgr.get_tools())
    except Exception:
        pass  # Soul not available
```

**Step 2: Verify**

Run: `uv run ruff check src/pocketpaw/agents/tool_bridge.py`
Expected: no errors

**Step 3: Commit**

```bash
git add src/pocketpaw/agents/tool_bridge.py
git commit -m "feat: inject soul tools into tool bridge for all backends"
```

---

### Task 6: Add soul tool instructions to INSTRUCTIONS.md template

**Files:**
- Modify: `src/pocketpaw/bootstrap/default_provider.py` (`_DEFAULT_INSTRUCTIONS` string)

For the Claude SDK backend, tools are described in the system prompt. We need to add soul tool descriptions so the agent knows how to use them.

**Step 1: Add soul tools section to `_DEFAULT_INSTRUCTIONS`**

After the `### Health & Diagnostics` section (around line 146), add:

```python
### Soul (requires soul-protocol)
- `soul_remember '{"content": "User prefers dark mode", "importance": 7}'` — store persistent memory
- `soul_recall '{"query": "user preferences"}'` — search soul memories by relevance
- `soul_edit_core '{"persona": "I am Paw, warm and curious.", "human": "Developer who likes Python"}'` — edit core identity
- `soul_status '{}'` — check mood, energy, and active knowledge domains

**Soul tools are only available when soul-protocol is enabled** (`POCKETPAW_SOUL_ENABLED=true`).
Use soul_remember proactively when you learn important facts about the user or project.
```

**Step 2: Verify**

Run: `uv run ruff check src/pocketpaw/bootstrap/default_provider.py`
Expected: no errors

**Step 3: Commit**

```bash
git add src/pocketpaw/bootstrap/default_provider.py
git commit -m "feat: add soul tool instructions to system prompt template"
```

---

### Task 7: Add REST API endpoint for soul status

**Files:**
- Create: `src/pocketpaw/api/v1/soul.py`
- Modify: `src/pocketpaw/api/v1/__init__.py` (add to `_V1_ROUTERS`)

**Step 1: Create the soul API router**

```python
# src/pocketpaw/api/v1/soul.py
"""Soul Protocol API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from pocketpaw.api.deps import require_scope

router = APIRouter(tags=["Soul"], dependencies=[Depends(require_scope("settings:read"))])


@router.get("/soul/status")
async def get_soul_status():
    """Return current soul state (mood, energy, personality, domains)."""
    from pocketpaw.soul.manager import get_soul_manager

    mgr = get_soul_manager()
    if mgr is None or mgr.soul is None:
        return {"enabled": False}

    soul = mgr.soul
    state = soul.state
    result: dict = {
        "enabled": True,
        "name": soul.name,
        "mood": getattr(state, "mood", None),
        "energy": getattr(state, "energy", None),
        "social_battery": getattr(state, "social_battery", None),
        "observe_count": mgr._observe_count,
    }

    if hasattr(soul, "self_model") and soul.self_model:
        try:
            images = soul.self_model.get_active_self_images(limit=5)
            result["domains"] = [
                {"domain": img.domain, "confidence": img.confidence}
                for img in images
            ]
        except Exception:
            pass

    return result


@router.post("/soul/export")
async def export_soul():
    """Save the current soul to its .soul file."""
    from pocketpaw.soul.manager import get_soul_manager

    mgr = get_soul_manager()
    if mgr is None or mgr.soul is None:
        return {"error": "Soul not enabled"}

    await mgr.save()
    return {"path": str(mgr.soul_file), "status": "exported"}
```

**Step 2: Register in v1 router aggregator**

In `src/pocketpaw/api/v1/__init__.py`, add to `_V1_ROUTERS` list:

```python
    ("pocketpaw.api.v1.soul", "router", "Soul"),
```

**Step 3: Verify**

Run: `uv run ruff check src/pocketpaw/api/v1/soul.py`
Expected: no errors

**Step 4: Commit**

```bash
git add src/pocketpaw/api/v1/soul.py src/pocketpaw/api/v1/__init__.py
git commit -m "feat: add soul status and export REST API endpoints"
```

---

### Task 8: Add soul settings to dashboard WebSocket handler

**Files:**
- Modify: `src/pocketpaw/dashboard_ws.py` (settings action handler, ~line 330)

**Step 1: Add soul fields to the settings handler**

In the `elif action == "settings":` block in `dashboard_ws.py`, after the existing settings handling, add:

```python
                    # Soul Protocol
                    if "soul_enabled" in data:
                        settings.soul_enabled = bool(data["soul_enabled"])
                    if data.get("soul_name"):
                        settings.soul_name = data["soul_name"]
                    if data.get("soul_archetype"):
                        settings.soul_archetype = data["soul_archetype"]
                    if "soul_persona" in data:
                        settings.soul_persona = data.get("soul_persona", "")
                    if "soul_auto_save_interval" in data:
                        val = data["soul_auto_save_interval"]
                        if isinstance(val, int | float) and 0 <= val <= 3600:
                            settings.soul_auto_save_interval = int(val)
```

**Step 2: Commit**

```bash
git add src/pocketpaw/dashboard_ws.py
git commit -m "feat: handle soul settings in dashboard WebSocket handler"
```

---

### Task 9: Add Soul Protocol section to dashboard settings UI

**Files:**
- Modify: `src/pocketpaw/frontend/js/app.js` (sections list, settings data, search index)
- Modify: `src/pocketpaw/frontend/templates/components/modals/settings.html`
- Modify: `src/pocketpaw/frontend/js/websocket.js` (saveSettings serialization)

**Step 1: Add section definition to `app.js`**

In the `settingsSections` array (~line 54), add:

```javascript
    { id: 'soul', label: 'Soul', icon: 'sparkles' },
```

**Step 2: Add settings data fields to `app.js`**

In the `settings` object (~line 75), add:

```javascript
    soulEnabled: false,
    soulName: 'Paw',
    soulArchetype: 'The Helpful Assistant',
    soulPersona: '',
    soulAutoSaveInterval: 300,
```

**Step 3: Add search index entries to `app.js`**

In the `_SETTINGS_INDEX` array (~line 868), add:

```javascript
    { section: 'soul', sectionLabel: 'Soul', label: 'Enable Soul Protocol', hint: 'soul identity personality memory emotion' },
    { section: 'soul', sectionLabel: 'Soul', label: 'Soul Name', hint: 'soul name identity' },
    { section: 'soul', sectionLabel: 'Soul', label: 'Archetype', hint: 'soul archetype personality role' },
    { section: 'soul', sectionLabel: 'Soul', label: 'Auto-Save Interval', hint: 'soul save persist crash' },
```

**Step 4: Add HTML section to `settings.html`**

Add before the closing `</div>` of the settings content area:

```html
<!-- Soul Protocol -->
<div x-show="settingsSection === 'soul' && settingsSearchResults.length === 0" class="space-y-4">
  <h3 class="text-[14px] font-semibold text-white/80 mb-3">Soul Protocol</h3>
  <p class="text-[11px] text-white/40 -mt-1 mb-3">Persistent AI identity with psychology-informed memory, OCEAN personality, and emotional state.</p>

  <!-- Enable -->
  <div>
    <label class="flex items-start gap-2.5 cursor-pointer group">
      <input type="checkbox" x-model="settings.soulEnabled" @change="saveSettings()" class="mt-0.5 accent-[var(--accent-color)] w-4 h-4" />
      <div class="flex flex-col">
        <span class="text-[13px] font-medium group-hover:text-white transition-colors">Enable Soul Protocol</span>
        <span class="text-[11px] text-white/50 mt-0.5">Give the agent persistent identity, memory, and emotion</span>
      </div>
    </label>
  </div>

  <!-- Conditional sub-fields -->
  <div x-show="settings.soulEnabled" x-transition class="flex flex-col gap-3.5 pl-2 border-l-2 border-[var(--accent-color)]/30 ml-1">
    <!-- Soul Name -->
    <div class="flex flex-col gap-1.5">
      <label class="text-[12px] font-medium text-[var(--text-secondary)] uppercase tracking-wide">Soul Name</label>
      <input type="text" x-model="settings.soulName" @change="saveSettings()" placeholder="Paw" class="w-full bg-black/30 border border-[var(--glass-border)] rounded-[10px] py-2 px-3 text-[13px] text-white focus:outline-none focus:border-[var(--accent-color)] focus:bg-black/40 transition-all placeholder-white/40" />
    </div>

    <!-- Archetype -->
    <div class="flex flex-col gap-1.5">
      <label class="text-[12px] font-medium text-[var(--text-secondary)] uppercase tracking-wide">Archetype</label>
      <input type="text" x-model="settings.soulArchetype" @change="saveSettings()" placeholder="The Helpful Assistant" class="w-full bg-black/30 border border-[var(--glass-border)] rounded-[10px] py-2 px-3 text-[13px] text-white focus:outline-none focus:border-[var(--accent-color)] focus:bg-black/40 transition-all placeholder-white/40" />
      <span class="text-[11px] text-white/40">e.g. "The Coding Expert", "The Compassionate Creator"</span>
    </div>

    <!-- Persona -->
    <div class="flex flex-col gap-1.5">
      <label class="text-[12px] font-medium text-[var(--text-secondary)] uppercase tracking-wide">Custom Persona</label>
      <textarea x-model="settings.soulPersona" @change="saveSettings()" placeholder="Leave empty for auto-generated persona" rows="3" class="w-full bg-black/30 border border-[var(--glass-border)] rounded-[10px] py-2 px-3 text-[13px] text-white focus:outline-none focus:border-[var(--accent-color)] focus:bg-black/40 transition-all placeholder-white/40 resize-y"></textarea>
    </div>

    <!-- Auto-Save Interval -->
    <div class="flex flex-col gap-1.5">
      <label class="text-[12px] font-medium text-[var(--text-secondary)] uppercase tracking-wide">Auto-Save Interval (seconds)</label>
      <input type="number" x-model.number="settings.soulAutoSaveInterval" @change="saveSettings()" min="0" max="3600" placeholder="300" class="w-full bg-black/30 border border-[var(--glass-border)] rounded-[10px] py-2 px-3 text-[13px] text-white focus:outline-none focus:border-[var(--accent-color)] focus:bg-black/40 transition-all placeholder-white/40" />
      <span class="text-[11px] text-white/40">How often to auto-save soul state (0 = disabled, default 300 = 5 minutes)</span>
    </div>
  </div>
</div>
```

**Step 5: Add WebSocket serialization to `websocket.js`**

In the `saveSettings()` method (~line 192), add to the `this.send('settings', { ... })` object:

```javascript
        soul_enabled: settings.soulEnabled,
        soul_name: settings.soulName,
        soul_archetype: settings.soulArchetype,
        soul_persona: settings.soulPersona,
        soul_auto_save_interval: settings.soulAutoSaveInterval,
```

**Step 6: Commit**

```bash
git add src/pocketpaw/frontend/
git commit -m "feat: add Soul Protocol section to dashboard settings UI"
```

---

### Task 10: Write integration tests

**Files:**
- Create: `tests/test_soul_integration.py`

**Step 1: Write the tests**

```python
# tests/test_soul_integration.py
"""Integration tests: soul-protocol + PocketPaw wiring."""
import pytest


def _has_soul_protocol() -> bool:
    try:
        import soul_protocol  # noqa: F401
        return True
    except ImportError:
        return False


pytestmark = pytest.mark.skipif(
    not _has_soul_protocol(), reason="soul-protocol not installed"
)


class TestSoulIntegration:
    async def test_bootstrap_provider_generates_prompt(self):
        from soul_protocol import Soul
        from pocketpaw.paw.soul_bridge import SoulBootstrapProvider

        soul = await Soul.birth(
            name="IntegTest",
            archetype="Test Agent",
            persona="I am a test agent.",
        )
        provider = SoulBootstrapProvider(soul)
        ctx = await provider.get_context()

        assert ctx.name == "IntegTest"
        assert len(ctx.identity) > 0

    async def test_bridge_observe_and_recall(self):
        from soul_protocol import Soul
        from pocketpaw.paw.soul_bridge import SoulBridge

        soul = await Soul.birth(name="BridgeTest", persona="Test.")
        bridge = SoulBridge(soul)

        await bridge.observe("What is Python?", "Python is a programming language.")
        results = await bridge.recall("Python")
        assert isinstance(results, list)

    async def test_manager_full_lifecycle(self, tmp_path):
        from pocketpaw.config import Settings
        from pocketpaw.soul.manager import SoulManager, _reset_manager

        _reset_manager()
        settings = Settings(
            soul_enabled=True,
            soul_name="LifecycleTest",
            soul_archetype="The Tester",
            soul_path=str(tmp_path / "lifecycle.soul"),
            soul_auto_save_interval=0,
        )

        mgr = SoulManager(settings)
        await mgr.initialize()
        assert mgr.soul.name == "LifecycleTest"

        await mgr.observe("test input", "test output")
        await mgr.save()
        assert (tmp_path / "lifecycle.soul").exists()

        # Re-awaken
        _reset_manager()
        mgr2 = SoulManager(settings)
        await mgr2.initialize()
        assert mgr2.soul.name == "LifecycleTest"
        _reset_manager()

    async def test_soul_tools_injected_into_tool_bridge(self, tmp_path):
        """When soul is active, tool_bridge discovers soul tools."""
        from pocketpaw.config import Settings
        from pocketpaw.soul.manager import SoulManager, _reset_manager

        _reset_manager()
        settings = Settings(
            soul_enabled=True,
            soul_name="ToolTest",
            soul_path=str(tmp_path / "tools.soul"),
            soul_auto_save_interval=0,
        )
        mgr = SoulManager(settings)
        await mgr.initialize()

        from pocketpaw.agents.tool_bridge import _instantiate_all_tools

        tools = _instantiate_all_tools(backend="openai_agents")
        tool_names = {t.name for t in tools}
        assert "soul_remember" in tool_names
        assert "soul_recall" in tool_names
        assert "soul_edit_core" in tool_names
        assert "soul_status" in tool_names

        _reset_manager()

    async def test_corrupt_file_recovery_end_to_end(self, tmp_path):
        """Corrupt .soul file triggers backup + fresh birth."""
        from pocketpaw.config import Settings
        from pocketpaw.soul.manager import SoulManager, _reset_manager

        _reset_manager()
        soul_file = tmp_path / "corrupt.soul"
        soul_file.write_bytes(b"CORRUPT DATA HERE")

        settings = Settings(
            soul_enabled=True,
            soul_name="RecoveryTest",
            soul_path=str(soul_file),
            soul_auto_save_interval=0,
        )
        mgr = SoulManager(settings)
        await mgr.initialize()

        # Should have recovered
        assert mgr.soul is not None
        assert mgr.soul.name == "RecoveryTest"

        # Corrupt file backed up
        assert (tmp_path / "corrupt.soul.corrupt").exists()

        _reset_manager()
```

**Step 2: Run the tests**

Run: `uv run pytest tests/test_soul_integration.py -v`
Expected: PASS

**Step 3: Commit**

```bash
git add tests/test_soul_integration.py
git commit -m "test: add soul-protocol integration tests including edge cases"
```

---

### Task 11: Update CLAUDE.md

**Files:**
- Modify: `CLAUDE.md`

**Step 1: Add soul subsystem to Architecture > Key Subsystems**

After the **Config** bullet, add:

```markdown
- **Soul** (`soul/`) -- Optional soul-protocol integration for persistent AI identity, psychology-informed memory, OCEAN personality, emotional state, and portable `.soul` files. Enable via `soul_enabled=true`. SoulManager handles lifecycle (birth/awaken/save), auto-saves periodically, recovers from corrupt files, and wires SoulBootstrapProvider into the system prompt. Soul tools (`soul_remember`, `soul_recall`, `soul_edit_core`, `soul_status`) auto-register with all backends when active. Can be toggled at runtime via the dashboard settings.
```

**Step 2: Add env vars to Key Conventions**

After the existing env vars note, add:

```markdown
- **Soul config**: `POCKETPAW_SOUL_ENABLED=true`, `POCKETPAW_SOUL_NAME`, `POCKETPAW_SOUL_ARCHETYPE`, `POCKETPAW_SOUL_PATH`, `POCKETPAW_SOUL_AUTO_SAVE_INTERVAL`
```

**Step 3: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: document soul-protocol integration in CLAUDE.md"
```
