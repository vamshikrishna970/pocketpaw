# automations/evaluator.py — Trigger evaluation logic.
# Created: 2026-03-28 — Checks if rules should fire based on conditions.

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from ee.automations.models import AutomationRule, TriggerType

if TYPE_CHECKING:
    from ee.fabric.store import FabricStore


_OPERATORS = {
    "lt": lambda a, b: a < b,
    "gt": lambda a, b: a > b,
    "eq": lambda a, b: a == b,
    "gte": lambda a, b: a >= b,
    "lte": lambda a, b: a <= b,
    "ne": lambda a, b: a != b,
}


async def evaluate_threshold(rule: AutomationRule, fabric_store: "FabricStore") -> bool:
    """Check if any Fabric object of the configured type has a property crossing the threshold."""
    cfg = rule.trigger_config
    object_type = cfg.get("object_type")
    prop_name = cfg.get("property")
    operator = cfg.get("operator", "lt")
    threshold_value = cfg.get("value")

    if not object_type or not prop_name or threshold_value is None:
        return False

    op_fn = _OPERATORS.get(operator)
    if op_fn is None:
        return False

    from ee.fabric.models import FabricQuery
    result = await fabric_store.query(FabricQuery(type_name=object_type, limit=1000))

    for obj in result.objects:
        raw = obj.properties.get(prop_name)
        if raw is None:
            continue
        try:
            if op_fn(float(raw), float(threshold_value)):
                return True
        except (TypeError, ValueError):
            if operator == "eq" and str(raw) == str(threshold_value):
                return True
    return False


def evaluate_schedule(rule: AutomationRule, now: datetime | None = None) -> bool:
    """Check if cron expression matches current time. Requires croniter."""
    cron_expr = rule.trigger_config.get("cron")
    if not cron_expr:
        return False
    if now is None:
        now = datetime.now()
    now_minute = now.replace(second=0, microsecond=0)
    try:
        from croniter import croniter
        return bool(croniter.match(cron_expr, now_minute))
    except (ImportError, Exception):
        return False


def evaluate_data_change(rule: AutomationRule, event: dict[str, Any]) -> bool:
    """Check if an incoming data event matches the rule."""
    cfg = rule.trigger_config
    expected_type = cfg.get("object_type")
    expected_op = cfg.get("on")
    if not expected_type:
        return False

    actual_type = event.get("object_type") or event.get("type")
    actual_op = event.get("on") or event.get("operation") or event.get("event")

    if not actual_type or expected_type.lower() != actual_type.lower():
        return False
    if expected_op and actual_op and expected_op.lower() != actual_op.lower():
        return False
    return True


def evaluate_event(rule: AutomationRule, event: dict[str, Any]) -> bool:
    """Check if a system event matches the rule."""
    cfg = rule.trigger_config
    expected_name = cfg.get("event_name")
    expected_connector = cfg.get("connector")
    if not expected_name:
        return False

    actual_name = event.get("event_name") or event.get("name")
    if not actual_name or expected_name.lower() != actual_name.lower():
        return False

    if expected_connector:
        actual_connector = event.get("connector")
        if not actual_connector or expected_connector.lower() != actual_connector.lower():
            return False
    return True


async def check_all_rules(
    rules: list[AutomationRule],
    fabric_store: "FabricStore | None" = None,
    event: dict[str, Any] | None = None,
    now: datetime | None = None,
) -> list[AutomationRule]:
    """Evaluate all enabled rules and return those that should fire."""
    should_fire: list[AutomationRule] = []
    for rule in rules:
        if not rule.enabled:
            continue
        fired = False
        if rule.trigger_type == TriggerType.SCHEDULE:
            fired = evaluate_schedule(rule, now=now)
        elif rule.trigger_type == TriggerType.THRESHOLD and fabric_store:
            fired = await evaluate_threshold(rule, fabric_store)
        elif rule.trigger_type == TriggerType.DATA_CHANGE and event:
            fired = evaluate_data_change(rule, event)
        elif rule.trigger_type == TriggerType.EVENT and event:
            fired = evaluate_event(rule, event)
        if fired:
            should_fire.append(rule)
    return should_fire
