---
slug: set-up-a-fresh-machine
kind: procedure
trigger: a new collaborator or a new machine needs a working Riverfed dev environment
last_updated: 2026-08-15
sources: [contributing-to-riverfed]
policies: []
tags: [wiki/procedures]
---

# Set up a fresh machine

## When to run this

A new collaborator joins, or you're moving to a new Windows or Mac machine,
and you need the full Riverfed environment: private-repo access, Python,
optional media tooling, an agent CLI, and one-time git configuration.

## Steps

1. Authenticate before cloning the private repo. Install GitHub CLI, run
   `gh auth login -h github.com`, then `gh auth setup-git`. `PFreitas91` has
   verified write access to the product repo and both private vault repos.
2. Clone and enter the repo:
   `git clone https://github.com/ipodvs/riverfed.git` then
   `cd riverfed`.
3. On Windows, create the Python environment with the pinned interpreter:
   `py -3.13 -m venv .venv` — the project pins 3.13; don't use bare
   `python`.
4. Activate it: `.\.venv\Scripts\Activate.ps1`.
5. Upgrade pip and install deps:
   `python -m pip install --upgrade pip` then
   `pip install -r requirements.txt`.
6. Install the optional-but-recommended system tools, each unlocking a
   feature:
   - `winget install Gyan.FFmpeg` — audio file conversion via markitdown.
   - `winget install UB-Mannheim.TesseractOCR` — on-screen text capture
     (`--frames`).
   - `npm install -g @marp-team/marp-cli` — rendering Marp decks.
7. Install Claude Code, Grok, or Codex, then authenticate with
   `claude auth login`, `grok login`, or `codex login`. If using Claude,
   run `claude` once from the repo and accept project trust; a headless
   job cannot answer that prompt. The **Ingest ready** / **Studio**
   buttons activate when a provider is ready. If the server says a CLI
   is not on PATH, pin `CLAUDE_BIN`, `GROK_BIN`, or `CODEX_BIN` in
   `.env` (Grok installs to `~/.local/bin`, which a service PATH often
   misses).
8. Make `git pull` always rebase (matches what `sync.cmd` does):
   `git config --global pull.rebase true`.
9. On Mac, use the shorter verified path after authentication and clone:
   `./setup.sh` then `./serve.command`. It provisions the venv, dependencies,
   whisper.cpp smoke model, and local transcription check idempotently.

## Gotchas

- GitHub authentication and the pull configuration are one-shot. After them,
  `sync.cmd` and `ship.cmd` run
  silently — no prompts unless something genuinely needs attention.
- Skipping step 5 degrades features (no audio conversion, no `--frames`
  OCR, no deck rendering) but nothing else breaks.

## Done means

Setup completed clean; [[run-the-local-server|the server]] starts and the
browser reaches `http://127.0.0.1:8765`; the Ingest / Studio buttons are
active for the selected agent; `sync.cmd` or `./sync.command` runs without
prompting.
