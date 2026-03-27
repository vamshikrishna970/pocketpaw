# Tests for ee/automations — rules, store, evaluator.
# Created: 2026-03-28

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from ee.automations.models import AutomationRule, TriggerType
from ee.automations.store import AutomationsStore
from ee.automations.evaluator import (
    check_all_rules, evaluate_data_change, evaluate_event,
    evaluate_schedule, evaluate_threshold,
)


@pytest.fixture
def store(tmp_path: Path) -> AutomationsStore:
    return AutomationsStore(tmp_path / "test.db")


def _mock_fabric(objects: list[dict]) -> Any:
    from ee.fabric.models import FabricObject, FabricQueryResult
    objs = [FabricObject(type_id="t1", type_name="Inventory", properties=p) for p in objects]
    mock = MagicMock()
    mock.query = AsyncMock(return_value=FabricQueryResult(objects=objs, total=len(objs)))
    return mock


# --- Store ---

class TestStore:
    @pytest.mark.asyncio
    async def test_create_and_get(self, store):
        rule = await store.create_rule("p1", "Low stock", TriggerType.THRESHOLD,
            {"object_type": "Inventory", "property": "qty", "operator": "lt", "value": 10}, {})
        assert rule.id.startswith("rul-")
        fetched = await store.get_rule(rule.id)
        assert fetched is not None
        assert fetched.name == "Low stock"

    @pytest.mark.asyncio
    async def test_list_filter(self, store):
        await store.create_rule("p1", "A", TriggerType.SCHEDULE, {"cron": "* * * * *"}, {})
        await store.create_rule("p2", "B", TriggerType.SCHEDULE, {"cron": "* * * * *"}, {})
        assert len(await store.list_rules(pocket_id="p1")) == 1

    @pytest.mark.asyncio
    async def test_enable_disable(self, store):
        rule = await store.create_rule("p1", "X", TriggerType.EVENT, {}, {})
        disabled = await store.disable_rule(rule.id)
        assert disabled is not None and not disabled.enabled
        enabled = await store.enable_rule(rule.id)
        assert enabled is not None and enabled.enabled

    @pytest.mark.asyncio
    async def test_mark_fired(self, store):
        rule = await store.create_rule("p1", "X", TriggerType.EVENT, {}, {})
        fired = await store.mark_fired(rule.id)
        assert fired is not None and fired.fire_count == 1 and fired.last_fired is not None
        fired2 = await store.mark_fired(rule.id)
        assert fired2 is not None and fired2.fire_count == 2

    @pytest.mark.asyncio
    async def test_delete(self, store):
        rule = await store.create_rule("p1", "X", TriggerType.EVENT, {}, {})
        assert await store.delete_rule(rule.id) is True
        assert await store.get_rule(rule.id) is None
        assert await store.delete_rule("ghost") is False


# --- Evaluator ---

class TestThreshold:
    @pytest.mark.asyncio
    async def test_lt_fires(self):
        assert await evaluate_threshold(
            AutomationRule(pocket_id="p1", name="t", trigger_type=TriggerType.THRESHOLD,
                trigger_config={"object_type": "Inventory", "property": "qty", "operator": "lt", "value": 10},
                action_template={}),
            _mock_fabric([{"qty": 5}]),
        ) is True

    @pytest.mark.asyncio
    async def test_lt_no_fire(self):
        assert await evaluate_threshold(
            AutomationRule(pocket_id="p1", name="t", trigger_type=TriggerType.THRESHOLD,
                trigger_config={"object_type": "Inventory", "property": "qty", "operator": "lt", "value": 10},
                action_template={}),
            _mock_fabric([{"qty": 15}]),
        ) is False

    @pytest.mark.asyncio
    async def test_gt_fires(self):
        assert await evaluate_threshold(
            AutomationRule(pocket_id="p1", name="t", trigger_type=TriggerType.THRESHOLD,
                trigger_config={"object_type": "Inventory", "property": "qty", "operator": "gt", "value": 50},
                action_template={}),
            _mock_fabric([{"qty": 100}]),
        ) is True

    @pytest.mark.asyncio
    async def test_missing_config(self):
        assert await evaluate_threshold(
            AutomationRule(pocket_id="p1", name="t", trigger_type=TriggerType.THRESHOLD,
                trigger_config={}, action_template={}),
            _mock_fabric([{"qty": 5}]),
        ) is False


class TestDataChange:
    def test_fires(self):
        rule = AutomationRule(pocket_id="p1", name="t", trigger_type=TriggerType.DATA_CHANGE,
            trigger_config={"object_type": "Order", "on": "create"}, action_template={})
        assert evaluate_data_change(rule, {"object_type": "Order", "on": "create"}) is True

    def test_wrong_type(self):
        rule = AutomationRule(pocket_id="p1", name="t", trigger_type=TriggerType.DATA_CHANGE,
            trigger_config={"object_type": "Order", "on": "create"}, action_template={})
        assert evaluate_data_change(rule, {"object_type": "Invoice", "on": "create"}) is False


class TestEvent:
    def test_fires(self):
        rule = AutomationRule(pocket_id="p1", name="t", trigger_type=TriggerType.EVENT,
            trigger_config={"event_name": "connector_synced", "connector": "stripe"}, action_template={})
        assert evaluate_event(rule, {"event_name": "connector_synced", "connector": "stripe"}) is True

    def test_wrong_connector(self):
        rule = AutomationRule(pocket_id="p1", name="t", trigger_type=TriggerType.EVENT,
            trigger_config={"event_name": "connector_synced", "connector": "stripe"}, action_template={})
        assert evaluate_event(rule, {"event_name": "connector_synced", "connector": "shopify"}) is False


class TestCheckAllRules:
    @pytest.mark.asyncio
    async def test_threshold_fires(self):
        rule = AutomationRule(pocket_id="p1", name="t", trigger_type=TriggerType.THRESHOLD,
            trigger_config={"object_type": "Inv", "property": "qty", "operator": "lt", "value": 10},
            action_template={})
        fired = await check_all_rules([rule], fabric_store=_mock_fabric([{"qty": 3}]))
        assert len(fired) == 1

    @pytest.mark.asyncio
    async def test_skips_disabled(self):
        rule = AutomationRule(pocket_id="p1", name="t", trigger_type=TriggerType.THRESHOLD,
            trigger_config={"object_type": "Inv", "property": "qty", "operator": "lt", "value": 10},
            action_template={}, enabled=False)
        fired = await check_all_rules([rule], fabric_store=_mock_fabric([{"qty": 3}]))
        assert len(fired) == 0

    @pytest.mark.asyncio
    async def test_data_change_fires(self):
        rule = AutomationRule(pocket_id="p1", name="t", trigger_type=TriggerType.DATA_CHANGE,
            trigger_config={"object_type": "Order", "on": "create"}, action_template={})
        fired = await check_all_rules([rule], event={"object_type": "Order", "on": "create"})
        assert len(fired) == 1
