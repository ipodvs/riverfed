---
slug: contributing-to-riverfed
source_file: ../output/contributing-to-riverfed.md
title: Contributing to Riverfed
origin: handbook
ingested: 2026-08-15
procedures: [set-up-a-fresh-machine, run-the-local-server, sync-and-ship-a-work-session, smoke-test-changes, ingest-a-source-into-the-wiki, hand-edit-wiki-pages, update-a-deck-or-diagram]
policies: [commit-message-format, branch-strategy, output-folder-immutability, review-ai-changes-before-commit, branding-rules, file-naming]
runbooks: [rebase-conflict-on-sync, claude-code-made-a-mess]
tags: [wiki/sources, set-up-a-fresh-machine, run-the-local-server, sync-and-ship-a-work-session, smoke-test-changes, ingest-a-source-into-the-wiki, hand-edit-wiki-pages, update-a-deck-or-diagram, commit-message-format, branch-strategy, output-folder-immutability, review-ai-changes-before-commit, branding-rules, file-naming, rebase-conflict-on-sync, claude-code-made-a-mess]
---

# Contributing to Riverfed

## TL;DR

The repo's `CONTRIBUTING.md` — the human-workflow handbook for the
two-collaborator, multi-agent Riverfed repo. Covers
fresh-machine setup, the daily `sync.cmd`/`ship.cmd` git rhythm, commit
and branch conventions, per-area smoke tests, wiki ingest + hand-edit
rules, deck/diagram update flow, branding constraints, and how to
recover when an AI agent makes a mess. Almost entirely operational —
this single document seeds the base.

## Extracted

- Procedures:
  - [[set-up-a-fresh-machine]] — authenticate private GitHub access → clone → Windows venv or Mac setup → optional tools → Claude or Codex auth.
  - [[run-the-local-server]] — `start.vbs` / `serve.cmd` to run, `stop.cmd` to stop.
  - [[sync-and-ship-a-work-session]] — `sync.cmd` at session start, CHANGELOG catch-up skim, commit, `ship.cmd` at session end.
  - [[smoke-test-changes]] — full automated suite plus per-area manual smoke tests.
  - [[ingest-a-source-into-the-wiki]] — drop link → readiness/recovery review → Ingest ready with Claude or Codex → auto-review every 5 ingests.
  - [[hand-edit-wiki-pages]] — direct edits allowed on wiki layers; keep frontmatter, re-run `obsidian_pass.py`.
  - [[update-a-deck-or-diagram]] — edit source → rebuild → commit source + outputs together; diagram flow.
- Policies:
  - [[commit-message-format]] — conventional commits, type/scope tables, Co-Authored-By trailer, one logical change per commit.
  - [[branch-strategy]] — one fresh feature branch and PR per coherent block; never continue on a merged branch.
  - [[output-folder-immutability]] — never edit `output/*.md` after ingestion; never commit `output/`.
  - [[review-ai-changes-before-commit]] — always review `git diff` before committing, even when the agent says it's done.
  - [[branding-rules]] — product name, Sith Red rule, nav order, top-left brand spec.
  - [[file-naming]] — kebab-case pages/HTML/icons, snake_case Python.
- Runbooks:
  - [[rebase-conflict-on-sync]] — `sync.cmd`/`ship.cmd` stops on conflict markers → resolve or abort.
  - [[claude-code-made-a-mess]] — agent over-edited or broke something subtle → diff, stash, retry constrained; wiki log as safety net.

## Leftovers

- **"Asking Claude for help"** — the practice of pointing Claude at the
  self-contained docs with an example prompt. A habit, not a procedure
  with steps; below the bar. → Inbox.
- **Exact `marp` rebuild commands** — the deck-update flow says "rebuild
  outputs (`marp` commands above)" but the commands are NOT in this
  document. [[update-a-deck-or-diagram]] names the step without flags;
  the gap is flagged in its Gotchas. → Inbox.
- **Diagram → PNG render method** — described only as
  "`landing/icons/`-style Chrome headless"; too vague to page as steps.
  → Inbox.
- **"Questions?" channel** — "open an issue on the GitHub repo; use
  whatever real-time channel you already use". Too thin to page; used as
  the Escalate path in both runbooks.
