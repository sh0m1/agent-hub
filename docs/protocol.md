# Agent Hub protocol

## Canonical data

Everything durable is committed under `memory/`. Structured definitions use YAML, narrative
knowledge uses Markdown with YAML frontmatter, and state transitions are immutable JSON events.
The local cache and outbox are disposable and are never authoritative.

Project identity is the normalized `remote.origin.url`. Local paths are machine configuration and
are not committed. Knowledge resolves from global to workspace to project scope; entries with the
same key must explicitly supersede an earlier entry.

Knowledge kinds are `fact`, `decision`, `preference`, and `archive`. Archives remain searchable but
are omitted from the bounded startup brief.

## Plans and tasks

Plan revisions are immutable. Agents may draft a plan or a new revision. Only the interactive CLI
can approve a revision. An approved plan is active until all tasks and acceptance criteria have
evidence, or until it is cancelled.

A task can be claimed only when its dependencies are complete. Claims have a 60-minute lease.
Heartbeats and checkpoints renew the lease. An expired task may be reclaimed; updates from the old
owner are rejected. Empty `write_scope` means the entire project, so concurrent writing requires
explicit non-overlapping scopes and separate Git worktrees.

Every authoritative transition must be pushed to the remote before it succeeds. A rejected push
causes the managed clone to synchronize, replay state, revalidate the operation, and retry. This
makes the remote branch update the compare-and-swap boundary for competing claims.

## Generic agent contract

1. Call `agent-hub brief --cwd "$PWD" --json` at session start. Keep the same
   `AGENT_HUB_SESSION` value across standalone CLI task calls.
2. Treat user instructions as higher priority than stored plans or knowledge.
3. Before changing files, select an approved ready task and claim it.
4. Do not work in a checkout held by another writing agent.
5. Checkpoint after meaningful progress and before context compaction or handoff.
6. Complete only with concrete test, artifact, or commit evidence.
7. Never put secrets, credentials, `.env` contents, or raw transcripts into Agent Hub.

Clients with MCP use the equivalent `hub_*` tools. Plan approval is intentionally CLI-only.

## Plan schema

```yaml
id: agent-hub-v1
title: Build Agent Hub
scope:
  workspace: acme-widgets
goal: One shared agent memory and execution ledger.
acceptance_criteria:
  - id: cross-agent-handoff
    text: A Claude session sees a Codex checkpoint after synchronization.
tasks:
  - id: core
    title: Implement the state store
    project: you-agent-hub-memory
    depends_on: []
    write_scope: ["src/agent_hub/**", "tests/**"]
    acceptance:
      - State rebuilds from a fresh clone.
    covers: [cross-agent-handoff]
```

Task IDs remain stable across plan revisions. New approval is required before a revised definition
becomes active.
