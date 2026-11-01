---
slug: commit-message-format
kind: policy
last_updated: 2026-06-11
sources: [contributing-to-riverfed]
tags: [wiki/policies]
---

# Commits follow conventional format, one logical change each

## The rule

Every commit is `type(scope): one-line summary in present tense`,
followed by a body explaining WHY the change matters (referencing
specific functions, files, or behaviour), ending with
`Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>`
whenever Claude Code (or any AI agent) was involved. One logical change
per commit — if the body says "and also", split into two commits.

## Why it exists

Future-you (or your co-conspirator) reads commit bodies to understand
what was decided and why. The co-author line is both honest and useful
for knowing which work was AI-assisted. And reverting a clean commit is
cheap; reverting a tangled one is expensive
(contributing-to-riverfed).

## Scope & exceptions

All commits, by humans and agents. Check `git log --oneline -20` for
the house cadence.

**Types:**

| Type | When |
|---|---|
| `feat(<scope>)` | New functionality (new endpoint, generator, page) |
| `fix` | Bug fix |
| `docs` | Documentation only (README, CLAUDE.md, design.md) |
| `copy` | Marketing/landing-page copy changes |
| `rebrand` | Brand-identity changes (logo, colour, name) |
| `deck` | Changes to `wiki/training/ai-builders-handbook.md` or its outputs |
| `wiki` | Wiki content updates (sources/topics/entities/concepts) |
| `chore` | Tooling, dependencies, config |

**Scopes:** `wiki`, `studio`, `convert`, `diagrams`, `landing`,
`server`. The one allowed omission: skip the scope when the change
spans multiple areas.

Respected by: [[sync-and-ship-a-work-session]],
[[update-a-deck-or-diagram]], [[smoke-test-changes]].
