from __future__ import annotations

from pathlib import Path
from typing import Any

from .git import is_managed_clone, remote_url, run_git
from .hub import Hub
from .policy import PolicyError
from .sessions import default_home


def doctor(hub: Hub, home: Path | None = None) -> dict[str, Any]:
    """Read-only health report for a runtime clone and the user's tool configuration."""
    home = home or default_home()
    checks: dict[str, Any] = {"root": str(hub.root), "managed_clone": is_managed_clone(hub.root)}
    status = run_git(hub.root, "status", "--porcelain", "--untracked-files=no").stdout
    checks["git"] = status.strip() == ""
    try:
        checks["policy"] = "ok" if hub.policy() else "absent"
    except PolicyError as exc:
        checks["policy"] = f"invalid: {exc}"
    try:
        checks["scan"] = hub.scan()["errors"] == 0
    except ValueError:
        checks["scan"] = False
    checks["queued_checkpoints"] = len(list(hub._outbox_root().glob("*.json")))
    checks["codex_instructions"] = (home / ".codex" / "AGENTS.md").exists()
    checks["claude_instructions"] = (home / ".claude" / "CLAUDE.md").exists()
    checks["remote"] = remote_url(hub.root)
    informational = {"root", "queued_checkpoints", "policy", "remote"}
    checks["ok"] = all(
        value for key, value in checks.items() if key not in informational
    ) and not str(checks["policy"]).startswith("invalid")
    return checks
