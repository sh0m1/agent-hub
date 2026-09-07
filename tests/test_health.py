from __future__ import annotations

from pathlib import Path

from agent_hub.health import doctor
from agent_hub.hub import Hub
from agent_hub.sessions import default_home


def test_default_home_honours_environment(fake_home: Path) -> None:
    assert default_home() == fake_home


def test_doctor_reads_instruction_files_from_the_given_home(
    hub_repo: Path, fake_home: Path
) -> None:
    report = doctor(Hub(hub_repo), home=fake_home)
    assert report["codex_instructions"] is False
    assert report["claude_instructions"] is False
    assert report["policy"] == "absent"
    assert report["remote"] == str(hub_repo.parent / "origin.git")
    (fake_home / ".codex").mkdir()
    (fake_home / ".codex" / "AGENTS.md").write_text("x\n", encoding="utf-8")
    (fake_home / ".claude").mkdir()
    (fake_home / ".claude" / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    report = doctor(Hub(hub_repo))
    assert report["codex_instructions"] is True
    assert report["claude_instructions"] is True
    assert report["ok"] is True


def test_doctor_reports_local_hubs(local_hub: Path, fake_home: Path) -> None:
    report = doctor(Hub(local_hub), home=fake_home)
    assert report["remote"] is None
    assert report["git"] is True
