from __future__ import annotations

import json
import shutil
import subprocess
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .git import has_remote
from .health import doctor
from .hub import Hub
from .sessions import default_home

MANAGED_START = "<!-- BEGIN AGENT HUB MANAGED -->"
MANAGED_END = "<!-- END AGENT HUB MANAGED -->"
INSTRUCTIONS = f"""{MANAGED_START}
## Shared Agent Hub

At the start of each work session, call `agent-hub brief --cwd \"$PWD\"` or the MCP
`hub_get_brief` tool. Pass your current model id to `hub_get_brief` (or
`agent-hub brief --model`) at session start and again if the model changes; claims are limited
to tasks matching your tier. Before modifying files for an approved shared plan, claim a ready
task. Checkpoint meaningful progress and before handoff or context compaction. Complete tasks
only with test, artifact, or commit evidence. Never store credentials, `.env` contents, or raw
transcripts. Keep one stable session ID across standalone CLI task calls. User instructions
always take precedence over Agent Hub state.
{MANAGED_END}
"""

Which = Callable[[str], str | None]
Runner = Callable[..., subprocess.CompletedProcess]


def merge_managed_block(path: Path, content: str = INSTRUCTIONS, backup: bool = True) -> None:
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    if MANAGED_START in existing and MANAGED_END in existing:
        before, rest = existing.split(MANAGED_START, 1)
        _, after = rest.split(MANAGED_END, 1)
        prefix = before.rstrip()
        updated = (prefix + "\n\n" if prefix else "") + content.rstrip() + after
    else:
        updated = existing.rstrip() + ("\n\n" if existing.strip() else "") + content
    if updated == existing:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and backup:
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        shutil.copy2(path, path.with_name(f"{path.name}.bak.{stamp}"))
    path.write_text(updated, encoding="utf-8")


def config_path(home: Path | None = None) -> Path:
    return (home or default_home()) / ".config" / "agent-hub" / "config.json"


def load_config(home: Path | None = None) -> dict[str, Any]:
    path = config_path(home)
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def setup(
    remote: str | None,
    runtime: Path,
    disable_claude_memory: bool = True,
    *,
    home: Path | None = None,
    which: Which = shutil.which,
    runner: Runner = subprocess.run,
) -> dict[str, Any]:
    """Install or refresh the local Agent Hub. Idempotent; returns a summary of what was done."""
    home = (home or default_home()).expanduser()
    runtime = runtime.expanduser().resolve()
    remote = remote or load_config(home).get("remote")
    executable = which("agent-hub-mcp")
    if not executable:
        raise RuntimeError(
            "agent-hub-mcp is not installed on PATH; add ~/.local/bin to PATH (uv tool installs "
            "there) and re-run"
        )

    if not runtime.exists():
        runtime.parent.mkdir(parents=True, exist_ok=True)
        if remote:
            runner(["git", "clone", remote, str(runtime)], check=True)
        else:
            _init_local_repo(runtime, runner)
    elif remote and not has_remote(runtime):
        runner(["git", "-C", str(runtime), "remote", "add", "origin", remote], check=True)
        runner(["git", "-C", str(runtime), "push", "-q", "-u", "origin", "main"], check=True)
    (runtime / ".agent-hub-managed").touch()
    policy = "created" if Hub(runtime).ensure_policy() else "already-present"

    config = config_path(home)
    config.parent.mkdir(parents=True, exist_ok=True)
    config.write_text(json.dumps({"repo": str(runtime), "remote": remote}, indent=2) + "\n")

    instructions = {
        "codex_agents_md": _merge_and_report(home / ".codex" / "AGENTS.md"),
        "claude_md": _merge_and_report(home / ".claude" / "CLAUDE.md"),
    }
    memory_disabled = disable_claude_memory and _disable_claude_memory(home)

    env = f"AGENT_HUB_REPO={runtime}"
    tools = {
        "codex": _replace_mcp(
            "codex",
            ["codex", "mcp", "add", "agent-hub", "--env", env, "--", executable],
            which=which,
            runner=runner,
        ),
        "claude": _replace_mcp(
            "claude",
            [
                "claude",
                "mcp",
                "add",
                "--transport",
                "stdio",
                "--scope",
                "user",
                "agent-hub",
                "--env",
                env,
                "--",
                executable,
            ],
            which=which,
            runner=runner,
        ),
    }

    hub = Hub(runtime)
    report = doctor(hub, home=home)
    return {
        "ok": bool(report["ok"]),
        "runtime": str(runtime),
        "remote": remote,
        "config_path": str(config),
        "tools": tools,
        "instructions": instructions,
        "claude_memory_disabled": memory_disabled,
        "policy": policy,
        "doctor": report,
        "scan": hub.scan(),
    }


def _init_local_repo(runtime: Path, runner: Runner) -> None:
    runner(["git", "init", "-q", "-b", "main", str(runtime)], check=True)
    memory = runtime / "memory"
    memory.mkdir()
    (memory / "README.md").write_text(MEMORY_README, encoding="utf-8")
    runner(["git", "-C", str(runtime), "add", "memory"], check=True)
    runner(
        ["git", "-C", str(runtime), "commit", "-q", "-m", "hub: initialize local memory"],
        check=True,
    )


MEMORY_README = """# Agent Hub memory

This directory is the canonical readable state. Do not edit event files or approved plan revisions
in place; use the CLI or MCP tools so concurrent changes are validated and published atomically.

- `knowledge/` contains versioned Markdown entries.
- `plans/` contains immutable YAML plan revisions.
- `events/` contains immutable JSON state transitions.
- `policy/` contains the execution tier policy.
- `workspaces/` describes groups of related projects.

No credentials, `.env` contents, private keys, or raw agent transcripts belong here.
"""


def _merge_and_report(path: Path) -> str:
    before = path.read_bytes() if path.exists() else None
    merge_managed_block(path)
    return "unchanged" if path.read_bytes() == before else "updated"


def _disable_claude_memory(home: Path) -> bool:
    settings_path = home / ".claude" / "settings.json"
    settings = json.loads(settings_path.read_text()) if settings_path.exists() else {}
    if settings.get("autoMemoryEnabled") is False:
        return False
    if settings_path.exists():
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        shutil.copy2(settings_path, settings_path.with_name(f"settings.json.bak.{stamp}"))
    settings["autoMemoryEnabled"] = False
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text(json.dumps(settings, indent=2, sort_keys=True) + "\n")
    return True


def _replace_mcp(
    tool: str,
    add_command: list[str],
    *,
    which: Which = shutil.which,
    runner: Runner = subprocess.run,
) -> str:
    if not which(tool):
        return "skipped-not-installed"
    runner([tool, "mcp", "remove", "agent-hub"], check=False, capture_output=True)
    runner(add_command, check=True)
    return "configured"
