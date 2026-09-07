from __future__ import annotations

import subprocess
from pathlib import Path

import pytest


def git(path: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(path), *args], check=True, text=True, capture_output=True
    )
    return result.stdout.strip()


def project(path: Path, remote: str = "https://github.com/acme/widgets.git") -> Path:
    subprocess.run(["git", "init", "-b", "main", str(path)], check=True, capture_output=True)
    git(path, "remote", "add", "origin", remote)
    return path


@pytest.fixture
def hub_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    remote = tmp_path / "origin.git"
    seed = tmp_path / "seed"
    runtime = tmp_path / "runtime"
    subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True)
    subprocess.run(["git", "init", "-b", "main", str(seed)], check=True, capture_output=True)
    git(seed, "config", "user.email", "test@example.com")
    git(seed, "config", "user.name", "Agent Hub Test")
    (seed / "memory").mkdir()
    (seed / "memory" / "README.md").write_text("# Memory\n", encoding="utf-8")
    git(seed, "add", "memory")
    git(seed, "commit", "-m", "init")
    git(seed, "remote", "add", "origin", str(remote))
    git(seed, "push", "-u", "origin", "main")
    subprocess.run(
        ["git", "clone", "-b", "main", str(remote), str(runtime)],
        check=True,
        capture_output=True,
    )
    git(runtime, "config", "user.email", "test@example.com")
    git(runtime, "config", "user.name", "Agent Hub Test")
    (runtime / ".agent-hub-managed").touch()
    monkeypatch.setenv("AGENT_HUB_TESTING", "1")
    monkeypatch.setenv("AGENT_HUB_LOCK_DIR", str(tmp_path / "locks"))
    return runtime


@pytest.fixture
def plan_file(tmp_path: Path) -> Path:
    path = tmp_path / "plan.yaml"
    path.write_text(
        """id: shared-plan
title: Shared plan
goal: Let agents cooperate.
acceptance_criteria:
  - id: tested
    text: The implementation is tested.
tasks:
  - id: first
    title: First task
    project: acme-widgets
    depends_on: []
    write_scope: [src/first/**]
    acceptance: [Tests pass]
    covers: []
  - id: second
    title: Second task
    project: acme-widgets
    depends_on: [first]
    write_scope: [src/second/**]
    acceptance: [Tests pass]
    covers: [tested]
""",
        encoding="utf-8",
    )
    return path


@pytest.fixture
def project_paths(tmp_path: Path) -> tuple[Path, Path, Path]:
    return (
        project(tmp_path / "project-one"),
        project(tmp_path / "project-two"),
        project(tmp_path / "project-three", "https://github.com/example/other.git"),
    )


@pytest.fixture
def policy_hub(hub_repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    from agent_hub.hub import Hub

    monkeypatch.setenv("AGENT_HUB_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.delenv("AGENT_HUB_MODEL", raising=False)
    Hub(hub_repo).ensure_policy()
    return hub_repo
