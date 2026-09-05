# Agent Hub

Agent Hub is a Git-native shared memory and execution ledger for local coding agents. It gives
Codex, Claude Code, Cursor, Gemini CLI, and shell-capable agents one readable source of truth for
knowledge, approved plans, task claims, checkpoints, and completion evidence.

It does not call a model API and does not depend on a particular subscription. Git is the durable
store; a small CLI provides safe state transitions, and a stdio MCP server exposes the same
operations to clients that support MCP.

## Install

```sh
uv tool install .
agent-hub setup --remote https://github.com/you/agent-hub-memory.git
agent-hub doctor
agent-hub scan
```

`setup` creates a dedicated runtime clone at `~/.local/share/agent-hub/repo`, adds bounded managed
blocks to the Codex and Claude user instruction files, and configures the local MCP server. Existing
configuration is preserved and backed up before it is changed.

## Everyday workflow

```sh
agent-hub brief --cwd "$PWD"
agent-hub plan list
agent-hub task ready
agent-hub task claim PLAN TASK --actor codex
agent-hub task checkpoint PLAN TASK --summary "Implemented parser" --evidence "pytest: 12 passed"
agent-hub task complete PLAN TASK --evidence "commit: abc123" --evidence "pytest: 12 passed"
```

For supported tools, prefer `agent-hub run codex` or `agent-hub run claude`. The wrapper identifies
the session, synchronizes before launch, and renews leases while the process is alive.

Plans are drafted from YAML and become executable only after interactive approval:

```sh
agent-hub plan draft plan.yaml
agent-hub plan approve my-plan
```

See [docs/protocol.md](docs/protocol.md) for schemas, state transitions, concurrency semantics, and
the generic agent integration contract.
