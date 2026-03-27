# automations/models.py — AutomationRule and TriggerType models.
# Created: 2026-03-28

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from ee.fabric.models import _gen_id


class TriggerType(StrEnum):
    SCHEDULE = "schedule"
    DATA_CHANGE = "data_change"
    THRESHOLD = "threshold"
    EVENT = "event"


class AutomationRule(BaseModel):
    """A rule that triggers an action when conditions are met.

    trigger_config examples:
      schedule:     {"cron": "0 9 * * MON"}
      threshold:    {"object_type": "Inventory", "property": "quantity", "operator": "lt", "value": 10}
      data_change:  {"object_type": "Order", "on": "create"}
      event:        {"event_name": "connector_synced", "connector": "stripe"}
    """

    id: str = Field(default_factory=lambda: _gen_id("rul"))
    pocket_id: str
    name: str
    description: str = ""
    enabled: bool = True
    trigger_type: TriggerType
    trigger_config: dict[str, Any] = Field(default_factory=dict)
    action_template: dict[str, Any] = Field(default_factory=dict)
    last_fired: datetime | None = None
    fire_count: int = 0
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
