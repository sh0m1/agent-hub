from __future__ import annotations

from pathlib import Path

import pytest

from agent_hub.hub import Hub
from agent_hub.policy import DEFAULT_POLICY_TEXT, PolicyError, parse_policy, policy_path
from agent_hub.state import State, validate_plan


def _claim_event(payload: dict) -> dict:
    return {
        "schema_version": 1,
        "id": "e1",
        "occurred_at": "2026-09-07T00:00:00Z",
        "type": "task_claimed",
        "actor": "codex",
        "session": "one",
        "plan_id": "p",
        "task_id": "t",
        "payload": payload,
    }


def test_claim_replay_records_model_and_tier() -> None:
    state = State()
    state.apply(
        _claim_event(
            {
                "lease_until": "2999-01-01T00:00:00Z",
                "model": "claude-sonnet-5",
                "tier": "standard",
                "tier_override": True,
            }
        )
    )
    task = state.plans["p"].tasks["t"]
    assert (task.model, task.tier, task.tier_override) == ("claude-sonnet-5", "standard", True)


def test_legacy_claim_replays_without_model() -> None:
    state = State()
    state.apply(_claim_event({"lease_until": "2999-01-01T00:00:00Z"}))
    task = state.plans["p"].tasks["t"]
    assert (task.model, task.tier, task.tier_override) == (None, None, False)


def test_heartbeat_preserves_claim_model() -> None:
    state = State()
    state.apply(
        _claim_event({"lease_until": "2999-01-01T00:00:00Z", "model": "m", "tier": "standard"})
    )
    heartbeat = _claim_event({"lease_until": "2999-01-02T00:00:00Z"})
    heartbeat["type"] = "task_heartbeat"
    state.apply(heartbeat)
    assert state.plans["p"].tasks["t"].model == "m"


def _plan(tier: object) -> dict:
    return {
        "id": "p",
        "title": "P",
        "goal": "g",
        "tasks": [{"id": "t", "title": "T", "project": "acme-widgets", "tier": tier}],
    }


def test_validate_plan_checks_tier_against_policy() -> None:
    policy = parse_policy(DEFAULT_POLICY_TEXT)
    validate_plan(_plan("frontier"), policy)
    with pytest.raises(ValueError, match="unknown tier"):
        validate_plan(_plan("cheap"), policy)
    with pytest.raises(ValueError, match="must be a string"):
        validate_plan(_plan(3), policy)


def test_validate_plan_without_policy_accepts_any_tier_string() -> None:
    validate_plan(_plan("anything"))
    with pytest.raises(ValueError, match="must be a string"):
        validate_plan(_plan(["x"]))


def test_ensure_policy_writes_and_publishes_default(hub_repo: Path) -> None:
    hub = Hub(hub_repo)
    assert hub.policy() is None
    event = hub.ensure_policy()
    assert event is not None and event["type"] == "policy_initialized"
    assert policy_path(hub_repo).read_text(encoding="utf-8") == DEFAULT_POLICY_TEXT
    assert hub.ensure_policy() is None
    policy = hub.policy()
    assert policy is not None and policy.default_task_tier == "standard"


def test_scan_rejects_invalid_policy(policy_hub: Path) -> None:
    hub = Hub(policy_hub)
    assert hub.scan()["errors"] == 0
    policy_path(policy_hub).write_text("schema_version: 1\n", encoding="utf-8")
    with pytest.raises(PolicyError):
        hub.scan()


def test_draft_rejects_unknown_tier_when_policy_present(policy_hub: Path, tmp_path: Path) -> None:
    plan = tmp_path / "tiered.yaml"
    plan.write_text(
        """id: tiered
title: Tiered
goal: g
tasks:
  - {id: a, title: A, project: acme-widgets, tier: cheap}
""",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="unknown tier"):
        Hub(policy_hub).draft_plan(plan, "codex", "draft")
