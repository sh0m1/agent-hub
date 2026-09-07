# Agent Hub

Agent Hub is a Git-native shared memory and execution ledger for local coding agents. It gives
Codex, Claude Code, Cursor, Gemini CLI, and shell-capable agents one readable source of truth for
knowledge, approved plans, task claims, checkpoints, and completion evidence.

It does not call a model API and does not depend on a particular subscription. Git is the durable
store; a small CLI provides safe state transitions, and a stdio MCP server exposes the same
operations to clients that support MCP.

## Install

One command on a machine that already runs Claude Code and/or Codex CLI:

```sh
curl -fsSL https://raw.githubusercontent.com/sh0m1/agent-hub/main/install.sh \
  | sh -s -- --remote https://github.com/you/agent-hub-memory.git
```

It installs `uv` if missing, installs `agent-hub` pinned to a released tag, and runs
`agent-hub setup`, which ends with a summary of what was configured. Flags: `--ref <tag>` to pick
a version, `--keep-claude-memory` to leave Claude Code's automatic memory on, `--dry-run` to print
the commands without touching anything.

Manual equivalent:

```sh
uv tool install git+https://github.com/sh0m1/agent-hub@v0.3.0
agent-hub setup --remote https://github.com/you/agent-hub-memory.git
```

`setup` creates a dedicated runtime clone at `~/.local/share/agent-hub/repo`, adds bounded managed
blocks to the Codex and Claude user instruction files, and registers the MCP server with whichever
of `codex` and `claude` are on `PATH` (others are reported as skipped, not errors). Existing
configuration is preserved and backed up before it is changed. `agent-hub doctor` and
`agent-hub scan` remain available for later health checks; `--json` gives machine-readable output.

Upgrade by re-running the one-liner, or:

```sh
uv tool install --force git+https://github.com/sh0m1/agent-hub@v0.3.0
agent-hub setup   # the remote is remembered
```

The remote URL is stored verbatim in `~/.config/agent-hub/config.json` and echoed by `--dry-run`;
prefer SSH or a credential helper over embedding a token in the URL.

Add repository-level instructions for tools that do not load the user configuration:

```sh
agent-hub adapter install /path/to/project --tools agents,claude,gemini,cursor,copilot
```

Only a marked managed block is added or replaced; existing project instructions are preserved.

## Everyday workflow

```sh
export AGENT_HUB_ACTOR=codex
export AGENT_HUB_SESSION="$(agent-hub session --actor codex --value)"
agent-hub brief --cwd "$PWD" --model gpt-5.6-terra
agent-hub plan list
agent-hub task ready --tier standard
agent-hub task claim PLAN TASK --cwd "$PWD"
agent-hub task checkpoint PLAN TASK --summary "Implemented parser" --evidence "pytest: 12 passed"
agent-hub task complete PLAN TASK --evidence "commit: abc123" --evidence "pytest: 12 passed"
```

Tasks carry a `tier` (default `standard`); `memory/policy/tiers.yaml` maps model ids to tiers.
Frontier models plan and review, cheaper models execute, and the hub rejects claims that cross
tiers. See [docs/protocol.md](docs/protocol.md#execution-tiers).

For supported tools, prefer the managed wrapper. Its options precede the tool name:

```sh
agent-hub run --plan PLAN --task TASK --cwd /path/to/worktree --model gpt-5.6-terra codex
```

The wrapper identifies the session, claims the task, synchronizes before launch, and renews the
lease while the process is alive.

Plans are drafted from YAML and become executable only after interactive approval:

```sh
agent-hub plan draft plan.yaml
agent-hub plan approve my-plan
```

See [docs/protocol.md](docs/protocol.md) for schemas, state transitions, concurrency semantics, and
the generic agent integration contract.
