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
curl -fsSL https://raw.githubusercontent.com/sh0m1/agent-hub/main/install.sh | sh
```

It installs `uv` if missing, installs `agent-hub` pinned to a released tag, and runs
`agent-hub setup`, which ends with a summary of what was configured. The memory lives in a local
Git repository at `~/.local/share/agent-hub/repo`; nothing leaves the machine.

To share the memory across machines, give the same command a Git remote — on the first machine
it pushes the existing local memory there, on the others it clones it:

```sh
curl -fsSL https://raw.githubusercontent.com/sh0m1/agent-hub/main/install.sh \
  | sh -s -- --remote git@github.com:you/agent-hub-memory.git
```

To go back to a machine-local memory, `agent-hub setup --local` detaches and forgets the remote
(your local history is kept). Other flags: `--ref <tag>` to pick a version, `--keep-claude-memory`
to leave Claude Code's automatic memory on, `--dry-run` to print the commands without touching
anything. Manual equivalent: `uv tool install git+https://github.com/sh0m1/agent-hub@v0.5.0` then
`agent-hub setup [--remote <url> | --local]`.

`setup` adds bounded managed blocks to the Codex and Claude user instruction files and registers
the MCP server with whichever of `codex` and `claude` are on `PATH` (others are reported as
skipped, not errors). Existing configuration is preserved and backed up before it is changed.
Re-run the one-liner (or plain `agent-hub setup`) to upgrade; the remote is remembered.
`agent-hub doctor` and `agent-hub scan` remain available for later health checks; `--json` gives
machine-readable output.

The remote URL is stored verbatim in `~/.config/agent-hub/config.json` and echoed by `--dry-run`;
prefer SSH or a credential helper over embedding a token in the URL.

Add repository-level instructions for tools that do not load the user configuration:

```sh
agent-hub adapter install /path/to/project --tools agents,claude,gemini,cursor,copilot
```

Only a marked managed block is added or replaced; existing project instructions are preserved.

## Everyday workflow

With Claude Code or Codex there is nothing to type. The managed instruction block tells the agent
to call `hub_get_brief` at session start, claim a task before writing, checkpoint progress, and
complete with evidence — all through the MCP server that `setup` registered. You approve plans
and edit the tier policy; the agents do the rest.

From a shell — for humans, or for agents without MCP — the same contract is four commands. The
session id defaults to one stable for the terminal, so nothing needs exporting:

```sh
agent-hub brief --cwd "$PWD" --model gpt-5.6-terra
agent-hub task claim PLAN TASK --cwd "$PWD"
agent-hub task checkpoint PLAN TASK --summary "Implemented parser" --evidence "pytest: 12 passed"
agent-hub task complete PLAN TASK --evidence "commit: abc123" --evidence "pytest: 12 passed"
```

`agent-hub plan list` and `agent-hub task ready [--tier NAME]` show what is available. Set
`AGENT_HUB_ACTOR` to name the agent and `AGENT_HUB_SESSION` to pin a session id explicitly.

Tasks carry a `tier` (default `standard`); `memory/policy/tiers.yaml` maps model ids to tiers.
Frontier models plan and review, cheaper models execute, and the hub rejects claims that cross
tiers. See [docs/protocol.md](docs/protocol.md#execution-tiers).

To launch a tool with a task already claimed and the lease renewed while it runs, use the managed
wrapper. Its options precede the tool name:

```sh
agent-hub run --plan PLAN --task TASK --cwd /path/to/worktree --model gpt-5.6-terra codex
```

Plans are drafted from YAML and become executable only after interactive approval:

```sh
agent-hub plan draft plan.yaml
agent-hub plan approve my-plan
```

See [docs/protocol.md](docs/protocol.md) for schemas, state transitions, concurrency semantics, and
the generic agent integration contract.
