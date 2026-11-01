---
slug: claude-code-made-a-mess
kind: runbook
last_updated: 2026-06-11
sources: [contributing-to-riverfed]
tags: [wiki/runbooks]
---

# Claude Code made a mess

## Symptoms

The agent edited more than you wanted, or something subtle broke after
an agent session. Often caught at the
[[review-ai-changes-before-commit]] gate — the diff shows changes you
didn't ask for.

## Diagnose

1. `git diff` — cheapest check; shows exactly what the agent changed
   versus what you asked for. Unexpected files in the diff = the mess
   is uncommitted and easy to unwind.
2. For wiki damage: read `wiki/log.md` — every ingest appends there, so
   it shows exactly which pages a bad promotion added or changed.

## Recover

1. If the working tree is the mess: `git stash` it — liberally — then
   start fresh and retry with a **more constrained prompt**. Do NOT
   keep iterating on top of a tangled tree.
2. If a wiki promotion went wrong: identify the page from `wiki/log.md`
   and revert that page.

## Escalate

If the damage is already committed/pushed and stash can't help,
coordinate with the other collaborator before rewriting any shared
history — GitHub issue or your usual real-time channel
(contributing-to-riverfed).
