---
name: Riverfed Ops
slug: riverfed-ops
model: sops-to-skills
purpose: catalog of every page in the Riverfed Ops knowledge base
last_updated: 2026-08-15
tags: [wiki]
---

# Riverfed Ops — index

This is the **entry point** for the Riverfed Ops knowledge base. Every page is
listed here with a one-line summary so an agent can pick what to read deeply.

For the conventions that govern this vault, see [[SCHEMA|SCHEMA.md]].

## Capture log (1 page per ingested document)

- [[contributing-to-riverfed]] — the repo's CONTRIBUTING.md: the human
  workflow handbook (setup, git rhythm, commits, testing, wiki/deck rules,
  recovery). Seeded the whole base.

## Procedures

- [[set-up-a-fresh-machine]] — authenticate private GitHub access → clone →
  Windows venv or Mac `./setup.sh` → optional tools → Claude or Codex auth.
- [[run-the-local-server]] — `start.vbs` (detached) or `serve.cmd` (live
  logs); `stop.cmd` to stop.
- [[sync-and-ship-a-work-session]] — `sync.cmd` at session start, CHANGELOG
  catch-up skim, commit, `ship.cmd` at session end.
- [[smoke-test-changes]] — full automated suite plus the per-area manual
  smoke-test table.
- [[ingest-a-source-into-the-wiki]] — drop link → readiness/recovery review →
  **Ingest ready** with Claude or Codex → auto-review every 5 ingests.
- [[hand-edit-wiki-pages]] — direct wiki edits: read SCHEMA first, keep
  frontmatter, re-run `obsidian_pass.py`.
- [[update-a-deck-or-diagram]] — edit source → rebuild → commit source +
  outputs together; diagram create flow.

## Policies

- [[commit-message-format]] — conventional commits with WHY-body,
  Co-Authored-By trailer, one logical change per commit.
- [[branch-strategy]] — one fresh feature branch and PR per coherent block;
  never continue on a merged branch.
- [[output-folder-immutability]] — never edit `output/*.md` after ingestion;
  never commit `output/`.
- [[review-ai-changes-before-commit]] — always review `git diff`, even when
  the agent says it's done.
- [[branding-rules]] — Riverfed name, Sith Red rule, nav order,
  top-left brand spec.
- [[file-naming]] — kebab-case content files, snake_case Python.

## Runbooks

- [[rebase-conflict-on-sync]] — `sync.cmd`/`ship.cmd` stopped on `<<<<<<<`
  markers: resolve + `git rebase --continue`, or `--abort`.
- [[claude-code-made-a-mess]] — agent over-edited or broke something subtle:
  diff, stash, retry constrained; `wiki/log.md` for bad promotions.

## Inbox

Below-the-bar candidates awaiting another capture or the consolidation pass:

- "Asking Claude for help" practice — point Claude at the self-contained docs
  with a focused prompt; a habit, not steps (contributing-to-riverfed).
- Exact `marp` rebuild commands for the master deck — referenced but not
  present in (contributing-to-riverfed); [[update-a-deck-or-diagram]]
  step 2 needs them.
- Diagram → PNG render method — described only as "`landing/icons/`-style
  Chrome headless" (contributing-to-riverfed).
