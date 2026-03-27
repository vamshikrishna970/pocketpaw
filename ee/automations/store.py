# automations/store.py — Async SQLite store for automation rules.
# Created: 2026-03-28

from __future__ import annotations

import json
import aiosqlite
from datetime import datetime
from pathlib import Path
from typing import Any

from ee.automations.models import AutomationRule, TriggerType


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS automation_rules (
    id TEXT PRIMARY KEY,
    pocket_id TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    enabled INTEGER DEFAULT 1,
    trigger_type TEXT NOT NULL,
    trigger_config TEXT DEFAULT '{}',
    action_template TEXT DEFAULT '{}',
    last_fired TEXT,
    fire_count INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_rules_pocket ON automation_rules(pocket_id);
CREATE INDEX IF NOT EXISTS idx_rules_enabled ON automation_rules(enabled);
"""


class AutomationsStore:
    """Async SQLite store for automation rules."""

    def __init__(self, db_path: str | Path) -> None:
        self._db_path = str(db_path)
        self._initialized = False

    async def _ensure_schema(self) -> None:
        if self._initialized:
            return
        async with aiosqlite.connect(self._db_path) as db:
            await db.executescript(SCHEMA_SQL)
            await db.commit()
        self._initialized = True

    def _conn(self) -> aiosqlite.Connection:
        return aiosqlite.connect(self._db_path)

    async def create_rule(
        self, pocket_id: str, name: str, trigger_type: TriggerType,
        trigger_config: dict[str, Any], action_template: dict[str, Any],
        description: str = "", enabled: bool = True,
    ) -> AutomationRule:
        rule = AutomationRule(
            pocket_id=pocket_id, name=name, description=description,
            enabled=enabled, trigger_type=trigger_type,
            trigger_config=trigger_config, action_template=action_template,
        )
        await self._ensure_schema()
        async with self._conn() as db:
            await db.execute(
                "INSERT INTO automation_rules (id, pocket_id, name, description, enabled, trigger_type, trigger_config, action_template) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (rule.id, pocket_id, name, description, 1 if enabled else 0,
                 trigger_type.value, json.dumps(trigger_config), json.dumps(action_template)),
            )
            await db.commit()
        return rule

    async def get_rule(self, rule_id: str) -> AutomationRule | None:
        await self._ensure_schema()
        async with self._conn() as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM automation_rules WHERE id = ?", (rule_id,)) as cur:
                row = await cur.fetchone()
                return self._row_to_rule(row) if row else None

    async def list_rules(self, pocket_id: str | None = None, enabled_only: bool = False) -> list[AutomationRule]:
        conditions: list[str] = []
        params: list[Any] = []
        if pocket_id:
            conditions.append("pocket_id = ?")
            params.append(pocket_id)
        if enabled_only:
            conditions.append("enabled = 1")
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        await self._ensure_schema()
        async with self._conn() as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(f"SELECT * FROM automation_rules {where} ORDER BY created_at DESC", params) as cur:
                return [self._row_to_rule(row) async for row in cur]

    async def update_rule(self, rule_id: str, **fields: Any) -> AutomationRule | None:
        rule = await self.get_rule(rule_id)
        if not rule:
            return None

        sets = ["updated_at = datetime('now')"]
        params: list[Any] = []
        for k, v in fields.items():
            if v is not None:
                if k in ("trigger_config", "action_template"):
                    sets.append(f"{k} = ?")
                    params.append(json.dumps(v))
                elif k == "enabled":
                    sets.append("enabled = ?")
                    params.append(1 if v else 0)
                else:
                    sets.append(f"{k} = ?")
                    params.append(v)
        params.append(rule_id)

        await self._ensure_schema()
        async with self._conn() as db:
            await db.execute(f"UPDATE automation_rules SET {', '.join(sets)} WHERE id = ?", params)
            await db.commit()
        return await self.get_rule(rule_id)

    async def delete_rule(self, rule_id: str) -> bool:
        await self._ensure_schema()
        async with self._conn() as db:
            cursor = await db.execute("DELETE FROM automation_rules WHERE id = ?", (rule_id,))
            await db.commit()
            return cursor.rowcount > 0

    async def enable_rule(self, rule_id: str) -> AutomationRule | None:
        return await self.update_rule(rule_id, enabled=True)

    async def disable_rule(self, rule_id: str) -> AutomationRule | None:
        return await self.update_rule(rule_id, enabled=False)

    async def mark_fired(self, rule_id: str) -> AutomationRule | None:
        await self._ensure_schema()
        async with self._conn() as db:
            await db.execute(
                "UPDATE automation_rules SET last_fired = datetime('now'), fire_count = fire_count + 1, updated_at = datetime('now') WHERE id = ?",
                (rule_id,),
            )
            await db.commit()
        return await self.get_rule(rule_id)

    def _row_to_rule(self, row: Any) -> AutomationRule:
        last_fired = None
        if row["last_fired"]:
            try:
                last_fired = datetime.fromisoformat(row["last_fired"])
            except ValueError:
                pass
        return AutomationRule(
            id=row["id"], pocket_id=row["pocket_id"], name=row["name"],
            description=row["description"] or "", enabled=bool(row["enabled"]),
            trigger_type=TriggerType(row["trigger_type"]),
            trigger_config=json.loads(row["trigger_config"]) if row["trigger_config"] else {},
            action_template=json.loads(row["action_template"]) if row["action_template"] else {},
            last_fired=last_fired, fire_count=row["fire_count"] or 0,
        )
