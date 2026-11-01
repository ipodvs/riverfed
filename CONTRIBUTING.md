# Contributing to Riverfed

Conventions for two-or-more humans working on this repo with Claude Code
as a collaborator. Both of you should skim this once and then refer back
when something feels ambiguous.

> For AI agents: start with [`CLAUDE.md`](CLAUDE.md) — it has the
> technical orientation. This file covers the human workflow.

## Setup on a fresh machine

The product and vault repositories are private. `PFreitas91` has verified
write access to all three; authenticate GitHub once before cloning.

```powershell
winget install GitHub.cli
gh auth login -h github.com
gh auth setup-git
git clone https://github.com/ipodvs/riverfed.git
cd riverfed

# Python environment
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt

# Configuration — the example documents every variable inline
copy .env.example .env
# (all optional: GROQ_API_KEY enables the remote final transcript
#  fallback; WATCHER_INTERVAL_MIN tunes the channel-watcher sweep
#  cadence, default 360 min)

# Optional but recommended:
winget install Gyan.FFmpeg                  # audio file conversion via markitdown
winget install UB-Mannheim.TesseractOCR     # on-screen text capture (--frames)
npm install -g @marp-team/marp-cli          # rendering Marp decks
```

An agent CLI (for wiki ingest + Studio) — one is enough, both lets
you switch freely from the **Agent** selector on `/`:

```powershell
# Claude Code (the default agent):
# https://claude.com/claude-code
claude auth login    # uses your Claude.ai Pro or Max subscription
# Then run `claude` once from this repo and accept the project-trust prompt.

# Grok (alternative — uses a grok.com plan):
# https://grok.com/
grok login

# Codex (alternative — uses a ChatGPT plan):
npm install -g @openai/codex
codex login
```

The server probes them all automatically — the **Ingest ready** /
**Studio** buttons activate when at least one CLI is logged in. Check
what the server sees with:

```powershell
py -3.13 wiki\scripts\agent_runner.py --status
```

### Setup on a Mac

Verified 2026-07-27 on an Apple Silicon Mac from a clean clone. The
idempotent setup creates the Python environment, installs dependencies,
creates `.env` only when it is missing, installs whisper.cpp 1.9.2,
downloads a checksum-pinned smoke model outside the repo, and verifies
local speech-to-text:

```bash
brew install gh
gh auth login -h github.com
gh auth setup-git
git clone https://github.com/ipodvs/riverfed.git
cd riverfed
./setup.sh
./serve.command
```

**Keep the server up (recommended).** Instead of leaving `serve.command`
running in a terminal, install the auto-restart watchdog once:

```bash
./install-watchdog.command      # LaunchAgent, probes /healthz every 5 min
```

It relaunches the local server if it ever dies, so the site can't silently
go down (`~/Library/Logs/riverfed-watchdog.log` if you want to watch it). While
it's installed, `./stop.command` isn't permanent — the server comes back within
5 minutes; run `./uninstall-watchdog.command` first if you want it to stay
stopped.

The default 75 MiB `tiny` model is a setup and smoke-test model. Install
the 547 MiB multilingual production model explicitly when transcript
quality matters:

```bash
./setup.sh --whisper-model large-v3-turbo-q5_0 --skip-python-deps
```

The model name and exact size are shown before download. Models live in
`~/Library/Caches/Riverfed/whisper.cpp`, not Git. Re-running setup
reuses the environment, binary, and checksum-verified model.

An agent CLI is still required for wiki ingest and Studio generation.
Choose either one:

```bash
# Claude Code: https://claude.com/claude-code
claude auth login
# Run `claude` once from this repository and accept project trust. Headless
# jobs cannot answer that first-run prompt.

# Grok: https://grok.com/
grok login

# Codex
npm install -g @openai/codex
codex login
```

Optional authoring tools:

```bash
brew install tesseract             # on-screen text capture with --frames
npm install -g @marp-team/marp-cli # deck rendering
```

Vaults work the same. The vault home is `~/RiverfedVaults` on every OS:

```bash
git clone <your-vault-repo-url> ~/RiverfedVaults/<slug>   # once per shared vault
./sync-vaults.command
```

Anywhere the docs say `py -3.13 wiki\scripts\<x>.py` (Windows
launcher), substitute `./.venv/bin/python wiki/scripts/<x>.py`.

Recorded clean-clone proof: setup passed twice, the committed 158-test suite
passed (1 optional live-network test skipped), a real YouTube source
converted, a real Codex ingest created one source and five entity pages,
`obsidian_pass.py` completed, and the scratch knowledge base rendered through
`/wiki`. Both agent runners had already been confirmed on this Mac; the
clean-clone ingest used Codex. A separate forced-local run transcribed a
1,157-second public video with the smoke model and no Groq call.

## Run the app

```powershell
start.vbs        # detached, opens browser at http://127.0.0.1:8765
# (or `serve.cmd` for a visible terminal with live logs)
stop.cmd         # shut it down
```

## Daily workflow — staying in sync

Two scripts at the project root, both safe to double-click from Explorer:

| Script | When to run | What it does |
|---|---|---|
| **`sync.cmd`** | At the **start** of every session | Pulls the latest from `origin/main` with rebase. Stops with a clear message if you have uncommitted changes. |
| **`ship.cmd`** | At the **end** of a session, after committing | Pulls latest first (so your push won't be rejected), then pushes your local commits. |
| **`sync-vaults.cmd`** | Whenever you want to share wiki state (after a few ingests, end of session) | For every git vault in `~/RiverfedVaults`: commits local changes, pulls the other person's edits, pushes yours. |

The flow becomes:

```
double-click sync.cmd       (start of session)
... work normally ...
git status                  (what changed?)
git diff                    (review it — especially after an agent session)
git add <the files you meant to change>
git commit -m "feat(...): ..."
double-click ship.cmd       (end of session)
```

Stage files by name rather than `git add .` — after an AI-assisted
session the working tree often contains more than you intended to ship,
and reviewing the diff *before* staging is the cheapest place to catch
that.

Both scripts handle the common failure modes gracefully — uncommitted
work, rebase conflicts, push rejections — and tell you the exact
recovery command to type.

**After `sync.cmd`, skim [`CHANGELOG.md`](CHANGELOG.md).** Newest work
is at the top, and the first section — *How to read this changelog as
PFreitas91* — is a guided catch-up path with a five-minute demo tour.

### One-time machine setup

So `git pull` always rebases (matches what `sync.cmd` does):

```powershell
git config --global pull.rebase true
```

Cache GitHub credentials (so `ship.cmd` doesn't prompt every push):

```powershell
# Easiest: install GitHub CLI and let it manage Git auth
winget install GitHub.cli
gh auth login                                # browser flow, one-time
gh auth setup-git
```

Both of these are one-shot. After that, `sync.cmd` and `ship.cmd` run
silently — no prompts unless something genuinely needs your attention.

### What if there's a conflict?

`sync.cmd` or `ship.cmd` will stop and tell you to resolve. The workflow:

```powershell
# Open the files with <<<<<<< markers, pick the right lines, save.
git add <file1> <file2> ...
git rebase --continue
# Then re-run sync.cmd or ship.cmd.

# Or, if you'd rather start over from the pre-rebase state:
git rebase --abort
```

Conflicts are rare in practice — they only happen when two people edit
the **same file at the same time**. The Riverfed project is big enough
that you'll usually be in different corners (one person in `wiki/`, the
other in `landing/`).

### When in doubt, `git status`

If anything looks off (`sync.cmd` complains, weird files, lost commits),
`git status` is always safe to run and tells you exactly what state your
working tree is in.

## Branch & commit strategy

Use one feature branch and one pull request for every coherent block. This
keeps `main` clone-ready and prevents a merged branch from quietly collecting
new work that the other collaborator cannot see. After a PR merges, switch
back to `main`, run `sync.cmd` / `./sync.command`, and create a fresh branch
for the next block:

```powershell
git switch main
sync.cmd
git switch -c agent/my-thing
# ... commit intentionally ...
git push -u origin agent/my-thing
gh pr create --draft --fill
```

Tiny typo-only documentation fixes may still go directly to `main` when both
collaborators agree. App, pipeline, setup, dependency, generated-artifact, and
roadmap changes go through a PR. Never keep working on a branch after its PR
has merged; that is how changes become "ahead of main" without a review path.

### Commit messages

We follow conventional commits with a focused body. Look at recent
commits (`git log --oneline -20`) for the cadence.

```
type(scope): one-line summary in present tense

A paragraph or two that explains WHY this change matters. Reference
specific functions, files, or behaviour you changed. Future-you (or
your co-conspirator) reads these to understand what was decided and
why — make it useful.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
```

**Types we use:**

| Type | When |
|---|---|
| `feat(<scope>)` | New functionality (new endpoint, new generator, new page) |
| `fix` | Bug fix |
| `docs` | Documentation only (README, CLAUDE.md, design.md) |
| `copy` | Marketing/landing-page copy changes |
| `rebrand` | Brand-identity changes (logo, colour, name) |
| `deck` | Changes to wiki/training/ai-builders-handbook.md or its outputs |
| `wiki` | Wiki content updates (sources/topics/entities/concepts) |
| `chore` | Tooling, dependencies, config |

**Scopes we use:** `wiki`, `studio`, `convert`, `diagrams`, `landing`,
`server`, `models`, `watcher`, `ops`. Skip the scope if the change
spans multiple areas.

**Always include the `Co-Authored-By` line** when Claude Code (or any
AI agent) was involved in the change, naming the model that actually
did the work (sessions in June–July 2026 run Claude Fable 5; older commits
carry Opus 4.7 — that's accurate history, don't rewrite it). It's both
honest and useful for future-you to understand which work was
AI-assisted.

### One logical change per commit

If you find yourself writing "and also" in the body, split into two
commits. Reverting a clean commit is cheap; reverting a tangled one is
expensive.

## Testing

**CI runs on every push** (`.github/workflows/ci.yml`, ~20 s): it
byte-compiles every script, parses all design + knowledge-model
manifests, runs the pending-detection fixture and an ingest dry-run,
lints wikilinks across every vault, and syntax-checks `nav.js`. A red
✗ next to a commit on GitHub means **don't pull until it's green** —
whoever pushed it fixes it.

Beyond CI, smoke tests per area:

| If you changed… | Run |
|---|---|
| `convert.py` | `convert.cmd <some YouTube URL>` — verify .md produced |
| `convert.py` office path | `convert.cmd <some .docx or .pptx>` — job log shows `[convert] converted via anydoc`; `--converter markitdown` still converts |
| `convert.py --frames` path | `convert.cmd <URL> --frames` — check `output/<slug>-frames/` populated + `## Visual content` section in .md |
| `server.py` routes | restart (`stop.cmd` → `start.vbs`), then `curl http://127.0.0.1:8765/healthz` + the route you changed |
| `wiki/scripts/ingest.py` | `py -3.13 wiki\scripts\ingest.py --dry-run` lists pending without errors |
| `models/<id>/` manifests | `py -3.13 wiki\scripts\model_registry.py` — parses every model or exits nonzero |
| Wiki pages / wikilinks | `py -3.13 wiki\scripts\lint_links.py` — dangling wikilinks fail (CI runs this too) |
| Marp deck source | `marp` rebuilds HTML + PDF without errors; preview slide 1 looks right |
| Excalidraw file | drag into excalidraw.com — opens, no console errors |
| Wiki counts changed a lot | `py -3.13 wiki\scripts\build_wiki_atlas.py` rebuilds the atlas without errors |

## Working with the wikis

The wiki is **LLM-curated content** — humans don't write source pages
by hand. There can be *several* knowledge bases ("vaults"), created
from the **Knowledge base** bar on `/`, and since the C1 split they are
**your data, outside this repo**: vaults live at `~/RiverfedVaults/<slug>/`
(override `RIVERFED_VAULTS_DIR` in `.env`), each as its own git repo.
The product repo ships one demo vault (`wikis/riverfed-ops/`) so fresh
clones and CI have something real to exercise — you will *not* see
anyone else's knowledge in your checkout.

**Sharing a vault with a collaborator.** Give the vault its own private
git repo (we name ours `riverfed-vault-<name>`), add the collaborator,
and have them clone it into `~/RiverfedVaults/<slug>`. After that,
**`sync-vaults.cmd`** / **`sync-vaults.command`** (project root,
double-click) commits + pulls + pushes every vault in one go. Vault
repos are separate from this product repo, so sharing one never makes
it public.

Each vault declares a
knowledge model (`karpathy-wiki` teach-back, `second-brain` PARA, or
`sops-to-skills` ops) that defines its folders, prompts, and how `/wiki`
renders it. Everything below applies per-vault — the wiki scripts all
take `--wiki <slug>` (default `wiki`).

The workflow:

1. Drop a YouTube link or file into the converter — or subscribe a
   channel under **Watched channels**, after which new uploads convert
   unattended — → `output/<slug>.md` lands in the vault's staging
2. Review the **Ready / Needs recovery** diagnostics, then click **Ingest
   ready** → the selected Claude Code or Codex CLI creates the capture page
   and updates the model's other folder pages
3. After every 5 ingests, `promote_backlog.py` auto-runs to surface
   patterns (the **Run review now** button triggers it manually)
4. The schema lives at `<vault>/SCHEMA.md` (each vault carries its own
   copy) — read it before hand-editing wiki pages directly (rare)

Hand-editing rules:
- **Never edit `output/*.md` after ingestion** — that's the immutable
  raw layer. Re-convert with `--force` if you need to refresh.
- **Editing a vault's `<folder>/*.md` pages directly is fine** — small fixes,
  typos, restructuring. Just keep frontmatter consistent (slug,
  last_updated, sources, tags) and re-run
  `py -3.13 wiki\scripts\obsidian_pass.py --wiki <slug>` afterward to
  normalise wikilinks.
- **Don't commit `output/`** — it's gitignored. Wiki pages alone are
  enough; if your co-collaborator needs to re-ingest a specific
  source, they can re-convert from the URL in the wiki frontmatter.

## Working with decks + diagrams

Both are markdown/JSON source files committed to the repo. The rendered
outputs (`out/*.{html,pdf,pptx,docx}`, `docs/screenshots/*.png`) are
also committed for easy sharing.

(The `/studio` page generates all of these from a knowledge base + a
short prompt: Marp deck, native PPTX, Excalidraw diagram, speaker
manual, a Claude Code **skill library**, and **Anki flashcards**. The
manual steps below are for hand-editing the committed masters.)

When you edit a deck:
1. Edit `wiki/training/ai-builders-handbook.md` (the source)
2. Rebuild outputs (`marp` commands above)
3. Commit source + outputs together

When you create a new diagram:
1. Either write the `.excalidraw` JSON directly (see existing files for
   shape) or generate via `/studio`
2. Commit to `diagrams/`
3. Optionally render a PNG via `landing/icons/`-style Chrome headless
   for the README

## Branding rules

Read [`wiki/training/design.md`](wiki/training/design.md) — the entire
brand system lives there. Critical rules:

- **Product name**: Riverfed, in user-facing copy and identifiers alike
  (`riverfed-*`, `RIVERFED_*`, `com.riverfed.*`, `~/RiverfedVaults`).
  Don't reintroduce older working names anywhere.
- **Sith Red rule**: red (`#ff4d4d` / `--saber-red` / `--united`) is
  reserved for errors and destructive actions. Never use as a
  decorative card accent. Use orange/yellow for differentiation.
- **Nav order across all pages**: Add · Knowledge · [Create CTA to
  `/studio`]. About is not a separate item.
- **Top-left brand**: "Riverfed" wordmark. It always links to the
  About overview and carries the accessible label `Riverfed: About`.

## When Claude Code makes a mess

Sometimes the agent edits more than you wanted, or breaks something subtle.

- **Always review `git diff` before committing** — even when Claude
  says "I made the change you asked for". Trust but verify.
- **Use `git stash`** liberally — if Claude went off the rails, stash,
  start fresh, retry with a more constrained prompt.
- **The wiki has its own safety net**: every ingest appends to
  `wiki/log.md`. If a promotion went wrong, the log shows what was
  added and you can revert that page.

## Asking Claude for help

When you're not sure how something works, just point Claude at the
files:

> *Read CLAUDE.md and wiki/SCHEMA.md, then explain what `promote_backlog.py`
> actually does and when it should run.*

The docs are intentionally self-contained so Claude can answer
mid-flight without you having to explain context.

## Naming new files

- Pages, slides, decks, diagrams: kebab-case slugs (`my-new-deck.md`,
  `agent-loop.excalidraw`)
- Python scripts: snake_case (`promote_backlog.py`,
  `studio_marp.py`)
- HTML pages: kebab-case (`studio.html`, `wiki.html`)
- Icons: kebab-case verbs/nouns (`folder-spark.svg`, `layers-stack.svg`)

## Questions?

Either of you can open an issue on the GitHub repo. For things that
need real-time discussion, use whatever channel you already use.
