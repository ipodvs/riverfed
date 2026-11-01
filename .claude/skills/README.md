# Riverfed — Claude Code skills

These are **SOPs for AI**: the workflows we repeat in this project, captured as
skills so any Claude Code session (yours, your brother's, mine) executes them
the same way — with the hard-won gotchas baked in. They follow the operator
best-practices in the wiki ([`building-skills-for-claude`](../../wiki/sources/building-skills-for-claude.md),
[`how-i-actually-use-claude-skills`](../../wiki/sources/how-i-actually-use-claude-skills.md)):
a `SKILL.md` per skill with `name` + `description` frontmatter (the trigger),
and **progressive disclosure** — the body holds the workflow, and it points to
the project's existing docs (`CLAUDE.md`, `design.md`, `CONTRIBUTING.md`, …)
for depth instead of duplicating them (so they don't drift).

| Skill | Triggers on |
|---|---|
| **convert-and-ingest** | "add this video", "ingest", "convert this link", "why isn't it pending" — convert + ingest, frame-flag decision, single-flight rule, video-id pending |
| **studio-deck** | "make a deck/slides/training/PowerPoint" — Marp or native PPTX + design + Word speaker notes; file-lock recovery |
| **studio-diagram** | "make a diagram/excalidraw/map", "this looks sketchy" — atlas-style Excalidraw (roughness 0, line connectors) |
| **server-recovery** | "site is down", "ingest stuck", "spinning forever" — restart, diagnose hung vs finished, surgical kill |
| **git-sync-ship** | "sync", "commit this", "ship it", push rejected — sync.cmd/ship.cmd, commit convention, LF rule |
| **remove-wiki-video** | "this video was a mistake", "remove all references to X" — purge source + transcript + cross-refs cleanly |
| **catch-up-docs** | "update the docs", "catch up the changelog", after shipping a block — the four collaborator-facing docs, in order, plus the staleness checks |

## How skills load (progressive disclosure)

1. **Frontmatter** (name + description) — always in context; this is what makes
   Claude *decide* to use the skill.
2. **SKILL.md body** — pulled in when the skill triggers.
3. **Referenced docs** — read on demand only when needed.

## Editing / adding skills

Use the **skill-creator** skill (`/skill-creator` or "use skill creator"). Keep
descriptions specific about *when* to trigger (Claude tends to under-trigger),
explain the *why* behind each step, and point to existing docs rather than
copying them. Iterate: a first-pass skill is rarely perfect — use it, notice
what's off, refine.
