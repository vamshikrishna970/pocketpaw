# DirectREST YAML engine — reads connector YAML definitions and executes REST actions.
# Created: 2026-03-27 — Primary adapter. One YAML per service.

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from pocketpaw.connectors.protocol import (
    ActionResult,
    ActionSchema,
    ConnectionResult,
    ConnectorStatus,
    SyncResult,
    TrustLevel,
)


@dataclass
class ConnectorDef:
    """Parsed connector YAML definition."""
    name: str
    display_name: str
    type: str = "generic"
    icon: str = "plug"
    auth: dict[str, Any] = field(default_factory=dict)
    actions: list[dict[str, Any]] = field(default_factory=list)
    sync: dict[str, Any] = field(default_factory=dict)


def parse_connector_yaml(path: Path) -> ConnectorDef:
    """Parse a connector YAML file into a ConnectorDef."""
    with open(path) as f:
        raw = yaml.safe_load(f)

    return ConnectorDef(
        name=raw.get("name", path.stem),
        display_name=raw.get("display_name", raw.get("name", path.stem)),
        type=raw.get("type", "generic"),
        icon=raw.get("icon", "plug"),
        auth=raw.get("auth", {}),
        actions=raw.get("actions", []),
        sync=raw.get("sync", {}),
    )


class DirectRESTAdapter:
    """Connector adapter that reads YAML definitions and executes REST actions.

    Each YAML file defines one service (Stripe, Square, etc.) with:
    - auth config (api_key, oauth, basic, bearer)
    - actions (REST endpoints with params and response schemas)
    - sync config (table mapping, schedule)
    """

    def __init__(self, definition: ConnectorDef) -> None:
        self._def = definition
        self._credentials: dict[str, str] = {}
        self._connected = False

    @property
    def name(self) -> str:
        return self._def.name

    @property
    def display_name(self) -> str:
        return self._def.display_name

    async def connect(self, pocket_id: str, config: dict[str, Any]) -> ConnectionResult:
        """Store credentials and mark as connected."""
        # Extract credentials from config
        for cred in self._def.auth.get("credentials", []):
            key = cred["name"]
            if key in config:
                self._credentials[key] = config[key]
            elif cred.get("required", False):
                return ConnectionResult(
                    success=False,
                    connector_name=self.name,
                    status=ConnectorStatus.ERROR,
                    message=f"Missing required credential: {key}",
                )

        self._connected = True
        tables = []
        if self._def.sync.get("table"):
            tables.append(self._def.sync["table"])

        return ConnectionResult(
            success=True,
            connector_name=self.name,
            status=ConnectorStatus.CONNECTED,
            message=f"Connected to {self.display_name}",
            tables_created=tables,
        )

    async def disconnect(self, pocket_id: str) -> bool:
        self._credentials.clear()
        self._connected = False
        return True

    async def actions(self) -> list[ActionSchema]:
        """Convert YAML action definitions to ActionSchema list."""
        schemas = []
        for act in self._def.actions:
            params = {}
            for key, val in act.get("params", {}).items():
                params[key] = val
            for key, val in act.get("body", {}).items():
                params[key] = val

            schemas.append(ActionSchema(
                name=act["name"],
                description=act.get("description", ""),
                method=act.get("method", "GET"),
                parameters=params,
                trust_level=TrustLevel(act.get("trust_level", "confirm")),
            ))
        return schemas

    async def execute(self, action: str, params: dict[str, Any]) -> ActionResult:
        """Execute a REST action. In production this would make HTTP calls."""
        if not self._connected:
            return ActionResult(success=False, error="Not connected")

        # Find the action definition
        act_def = None
        for a in self._def.actions:
            if a["name"] == action:
                act_def = a
                break

        if not act_def:
            return ActionResult(success=False, error=f"Unknown action: {action}")

        # In a real implementation, this would:
        # 1. Build the URL with params
        # 2. Add auth headers from self._credentials
        # 3. Make the HTTP request
        # 4. Parse and return the response
        # For now, return a placeholder indicating the action would be called
        return ActionResult(
            success=True,
            data={"action": action, "method": act_def.get("method", "GET"), "params": params},
            records_affected=0,
        )

    async def sync(self, pocket_id: str) -> SyncResult:
        """Sync data from the external service into pocket.db."""
        if not self._connected:
            return SyncResult(success=False, connector_name=self.name, error="Not connected")

        if not self._def.sync:
            return SyncResult(success=False, connector_name=self.name, error="No sync config")

        # In production: call the list action, map response to pocket.db table
        return SyncResult(
            success=True,
            connector_name=self.name,
            records_synced=0,
        )

    async def schema(self) -> dict[str, Any]:
        """Return the sync table schema."""
        return {
            "table": self._def.sync.get("table", f"{self.name}_data"),
            "mapping": self._def.sync.get("mapping", {}),
            "schedule": self._def.sync.get("schedule", "manual"),
        }
