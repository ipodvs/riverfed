# Riverfed — orientation for Claude Code

You're entering a project with several interlocking subsystems. Read this
file first; it points you at the deeper docs for each area.

## What this project is

A local app that turns YouTube videos + arbitrary files into a curated,
LLM-curated wiki, and then turns the wiki into teaching materials (Marp
decks, Excalidraw diagrams, speaker manuals, Word docs).

Three surfaces, all served from one local Python HTTP server on
`http://127.0.0.1:8765`:

| Route                             | What it does                                                                                                      |
| --------------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| `/` (`index.html`)                | Drop a YouTube URL or any file → markdown in `output/` + ingest controls, knowledge-base picker, watched channels |
| `/about` (`landing/index.html`)   | Marketing landing page                                                                                            |
| `/studio` (`landing/studio.html`) | Pick a wiki + generate a Marp deck, native PPTX, or Excalidraw diagram from a short prompt                        |
| `/wiki` (`landing/wiki.html`)     | Knowledge map of the wiki + Obsidian-style graph                                                                  |



Full product description: [`README.md`](README.md).

## Where things live

```javascript
.
├── convert.py                  Convert YouTube URL or file → output/<slug>.md
│                               (yt-dlp for YouTube; office docs — docx/pptx/
│                                xlsx/odt/rtf/epub — try Firecrawl's anydoc
│                                first with markitdown as fallback, pick with
│                                --converter; other files via markitdown
│                                with a pdfplumber → pypdfium2 → Tesseract-OCR
│                                fallback when markitdown's pdfminer chokes
│                                on truncated / encrypted / scan-only PDFs;
│                                optional --frames for video frame extraction
│                                + OCR; YouTube recovery order is human
│                                captions, automatic captions, local
│                                whisper.cpp, then optional Groq;
│                                see README "On-screen text")
├── local_whisper.py            Pinned/checksummed whisper.cpp model setup
│                               and local timestamped transcription runner
├── setup.sh                    Idempotent clean-Mac bootstrap; creates the
│                               venv, installs whisper.cpp + smoke model,
│                               and verifies local transcription
├── watcher.py                  Auto-ingest watcher — per-vault YouTube channel
│                               subscriptions (<vault>/.state/subscriptions.json).
│                               Server sweeps every WATCHER_INTERVAL_MIN minutes;
│                               new uploads convert into the vault staging
│                               (queue-for-approval default; per-channel
│                               auto-ingest + deep-capture flags). UI on /.
├── server.py                   The HTTP server. All routes, all subprocess
│                               invocations of helper scripts.
├── index.html                  Converter UI (drop + paste)
├── landing/
│   ├── index.html              Marketing landing (/about)
│   ├── studio.html             Studio (/studio) — Marp + PPTX + Excalidraw generators
│   ├── wiki.html               Knowledge map (/wiki) — list + graph
│   └── icons/                  Riverfed-original icon bank
│       ├── build.py            Source-of-truth Python generator (run to
│       │                       regenerate SVGs + PNGs after edits)
│       ├── README.md           Style spec, catalogue, recolour pattern
│       ├── preview.html        Visual gallery — open in a browser
│       ├── *.svg               22 utility icons + 2 riverfed-mark* brand marks
│       └── png/                256px transparent PNG variants (saber-blue
│                               default + -purple / -green / -yellow
│                               accents) for pptx embedding
├── output/                     Raw converted transcripts (gitignored)
├── output/<slug>-frames/       Extracted video frames (gitignored)
├── models/                     Knowledge-model templates: manifest + canonical
│   │                           schema + agent prompts per model. models/custom/
│   │                           is gitignored (same contract as designs/custom/).
│   │                           CRUD via /api/models; picker in the "+ New" flow.
│   ├── karpathy-wiki/          The original 4-folder model — model.md
│   │                           (manifest: folders, node kinds, capture flag,
│   │                           graph link fields, promote_after knobs,
│   │                           /wiki MAP card specs + search hint,
│   │                           generators), SCHEMA.md (canonical template new
│   │                           vaults are scaffolded from), ingest-prompt.md,
│   │                           promote-prompt.md
│   ├── second-brain/           PARA model — capture notes distilled toward
│   │                           action: projects (promote at 1 committed
│   │                           source) / areas (2) / resources (2) /
│   │                           archives (review-only, never auto-created)
│   └── sops-to-skills/         Ops model (the B2B wedge) — procedures /
│                               policies / runbooks extracted from dropped
│                               docs, written agent-executable; compiles to
│                               an agent skill library (Claude Code skills +
│                               AGENTS.md) via the Studio's
│                               "Compile skills" card (studio_skills.py)
├── wiki/                       Product code only since the C1 vault split —
│   │                           the PAGES of the original wiki vault now live
│   │                           in the vault home (~/RiverfedVaults/wiki/).
│   ├── scripts/                ingest.py, pending.py, obsidian_pass.py,
│   │                           promote_backlog.py, studio_*.py, build_wiki_atlas.py,
│   │                           base_gen.py (Obsidian Bases — renders the
│   │                           model's bases/*.base templates into each
│   │                           vault during obsidian_pass + scaffold, with a
│   │                           .state/bases.json sha256 ledger so hand edits
│   │                           are never clobbered; --force-bases re-adopts),
│   │                           agent_runner.py (A6 provider layer — ALL agent
│   │                           CLI invocations go through its run()/probe();
│   │                           providers: claude-code (default), grok, codex;
│   │                           "auto" takes the first ready in that order;
│   │                           explicit picks hard-fail with a login hint;
│   │                           `--status` prints per-provider status; codex
│   │                           argv is feature-probed from `codex exec
│   │                           --help`; grok is prompt-FILE delivered (it has
│   │                           no stdin route) and pins --sandbox off /
│   │                           --no-leader),
│   │                           _agent_bin.py (per-provider .CMD resolution,
│   │                           CLAUDE_BIN/CODEX_BIN/GROK_BIN overrides),
│   │                           _wikis.py (vault-home resolution + scaffolding +
│   │                           display_path), migrate_vaults.py (the one-shot
│   │                           C1 mover), model_registry.py (manifest parsing —
│   │                           mirrors design_tokens.py), lint_links.py
│   │                           (dangling-wikilink linter, runs in CI),
│   │                           writer_pack.py (bounded, versioned publisher
│   │                           for private ENGE.WRITER library snapshots)
│   └── training/               Marp decks + design system
│       ├── ai-builders-handbook.md   The master Marp deck (35 slides)
│       ├── design.md                 Deck design system (read before authoring decks)
│       ├── themes/ai-builders.css    Custom Marp theme implementing design.md
│       ├── scripts/
│       │   ├── build_speaker_doc.py     Word .docx of speaker notes
│       │   └── build_handbook_pptx.py   Native pptx of the handbook
│       │                                 (36 slides, embeds icons,
│       │                                 atomic-swaps via .tmp.pptx so
│       │                                 rebuild succeeds when PowerPoint
│       │                                 has the file open)
│       └── out/                      Rendered HTML / PDF / PPTX / DOCX
│           └── ai-builders-handbook-native.pptx    Native editable pptx
├── wikis/<slug>/               Repo-shipped DEMO vaults only (riverfed-ops —
│   │                           our own CONTRIBUTING.md as an ops base; what
│   │                           CI exercises). Personal vaults live in the
│   │                           vault home and a home vault wins on slug
│   │                           collision.
│   └── output/                 Per-vault transcript staging (gitignored)
├── ~/RiverfedVaults/<slug>/     THE VAULT HOME (override: RIVERFED_VAULTS_DIR
│                               in .env) — personal knowledge bases, each its
│                               own git repo: model page folders + SCHEMA.md +
│                               index.md + log.md + output/ staging + .state/.
│                               New bases from "+ New" scaffold here. Shared
│                               between the two collaborators via private
│                               riverfed-vault-<slug> GitHub repos for now
│                               (sync-vaults.cmd); access flips off at launch.
├── diagrams/                   Excalidraw diagrams + studio outputs
├── docs/screenshots/           README + landing assets
├── .github/workflows/ci.yml    Minimal CI: py_compile, pending fixture,
│                               design+model manifests parse, link lint,
│                               node --check (runs on push + PR, <2 min)
├── .claude/                    Claude Code project settings (allowed tools etc.)
├── .env.example                Copy to .env. Documents required env vars.
└── start.vbs / stop.cmd /      Windows launchers for server.py
    serve.cmd
```

## Architecture at a glance

```javascript
        YouTube URL / file
                ↓
            convert.py
        (captions + local whisper.cpp fallback,
         anydoc/markitdown, optional --frames + OCR)
                ↓
            output/<slug>.md
            output/<slug>-frames/   (if --frames)
                ↓
        wiki/scripts/ingest.py     (Claude Code, Grok, or Codex)
                ↓
            <vault>/<model-defined folders>/*.md
                ↓
        Studio generators selected by the model
        ↓
   decks · PPTX · diagrams · guides · Anki · agent skills
```

## Common commands

### Staying in sync with origin/main

This repo has two collaborators (often more, counting AI agents).
**Always** pull before starting work; **always** push when done.
Two scripts at the project root handle both safely:

```powershell
sync.cmd         # double-click — pulls latest with rebase
ship.cmd         # double-click — pulls + pushes pending commits
sync-vaults.cmd  # double-click — commit+pull+push every git vault in
                 # ~/RiverfedVaults (the knowledge bases are shared via
                 # private riverfed-vault-<slug> repos for now)
```

If you skip `sync.cmd` and `git push` later rejects, that's why — the
other collaborator pushed first. `ship.cmd` handles that automatically
by rebasing before pushing. Full conflict-resolution recipe in
[`CONTRIBUTING.md`](CONTRIBUTING.md) → "Daily workflow".

### Running the server

```powershell
# Detached, no console window (recommended)
start.vbs

# With a visible terminal (debugging)
serve.cmd

# Stop the detached server
stop.cmd
```

On the **Mac**, the double-clickable twins are `start.command` /
`serve.command` / `stop.command`, but the server usually runs as the launchd
agent `com.riverfed.server` (starts at login). Restart it after Python changes
with `launchctl kickstart -k "gui/$(id -u)/com.riverfed.server"`, then confirm
`curl -s 127.0.0.1:8765/healthz`. A `com.riverfed.watchdog` LaunchAgent
(installed via `install-watchdog.command`) probes `/healthz` every 5 min and
relaunches the server if it died — so a crash no longer leaves the site down.
While the watchdog is on, `stop.command` isn't permanent (the server returns
within 5 min); `uninstall-watchdog.command` to stop that.

The server auto-reloads HTML on every request (no restart needed for
HTML/JS edits). For Python changes (server.py, helper scripts) restart
via `stop.cmd && start.vbs` (Windows) or `launchctl kickstart` (Mac,
above). **Note:** `server.py` imports some modules in-process (`_wikis`,
`model_registry`, `_frontmatter`, `md_view`, `agent_runner`), so a restart is
required to pick up edits to those — CLI helper scripts (ingest.py etc.) are
spawned fresh and go live immediately.

### Converting a video

```powershell
# Web UI is easier; CLI is for batch / scripts
convert.cmd "https://www.youtube.com/watch?v=..."

# With frame extraction + OCR (Tier 2 — captures slides/code/dashboards)
convert.cmd "https://www.youtube.com/watch?v=..." --frames
convert.cmd "..." --frames --frame-width 1024   # for code-heavy videos

# Dense sampling for whiteboard/Excalidraw content
# (chapter-start frames catch the blank canvas; dense window catches the
# populated diagram a minute or two later)
convert.cmd "..." --frames --dense-until 1200 --dense-interval 45 --max-frames 60
```

**When to use which flags:**

| Content shape                                   | Recommended flags                                                                       |
| ----------------------------------------------- | --------------------------------------------------------------------------------------- |
| Talking-head interview / podcast                | (no `--frames`)                                                                         |
| Slide deck / conference talk                    | `--frames --frame-width 1024`                                                           |
| Code screencast / terminal demo                 | `--frames --frame-width 1024`                                                           |
| Whiteboard / Excalidraw heavy (early sections)  | `--frames --frame-width 1024 --dense-until 1200 --dense-interval 45 --max-frames 60`    |
| Screen-recording (UI tour / file-tree / editor) | same as whiteboard — small UI text OCRs to gibberish too, so dense + 🔍-flag everything |

**In the web UI** (`/`), the dense flag-set is one click: the
**"Deep visual capture"** checkbox (a sub-option under "Also capture
on-screen text") sends `dense: true`, which `server.py` expands to
`--frames --frame-width 1024 --dense-until 1200 --dense-interval 45 --max-frames 60`.
Its label flags the trade-off: more ingest tokens (the agent reads
every frame as an image), worth it when visuals carry info the
narration skips. Empirical proof of the payoff for screen-recordings:
[`docs/frames-ingest-comparison.md`](docs/frames-ingest-comparison.md)
→ "Follow-up 2".

The `--dense-until` window auto-flags every sampled frame as
vision-relevant (🔍) so the ingest agent will `Read` them as images
even when OCR returned `(no on-screen text)` (which is normal for
hand-drawn diagrams).

Full empirical comparison + diagram extraction case study:
[`docs/frames-ingest-comparison.md`](docs/frames-ingest-comparison.md).

### Converting a file

`convert.cmd report.docx` (or drop it on `/`). Office documents
(docx/pptx/xlsx/odt/rtf/epub + variants) go through Firecrawl's anydoc
first — grouped slide reading order, real headings — with markitdown as
the automatic fallback; `--converter anydoc|markitdown` forces an engine
(explicit picks hard-fail rather than silently falling back). PDFs keep
the pdfplumber → pypdfium2 → OCR chain. Empirical A/B:
[`docs/anydoc-comparison.md`](docs/anydoc-comparison.md).

### Ingesting into the wiki

Either:

- Web UI: open `/`, review **Ready / Needs recovery** under Knowledge,
  then click **Ingest ready**
- CLI: `py -3.13 wiki\scripts\ingest.py` (add `--dry-run` to preview)

The auto-review counter (default every 5 ingests, per-vault) auto-runs
`promote_backlog.py` to promote concept/entity candidates. Manual
trigger: **Run review now** button in the same UI, or
`py -3.13 wiki\scripts\promote_backlog.py`.

### Multiple knowledge bases (vaults)

The converter page (`/`) has a **Knowledge base** bar at the top: a
dropdown of every vault plus a **+ New** control that scaffolds a fresh
one (e.g. an "Investing" base fully separate from the AI wiki).
Everything on that page — convert target, pending list, ingest, review,
output-folder listing — is scoped to the selected vault, and the
selection persists per-browser (localStorage).

On disk (since the C1 vault split, 2026-06-12): personal vaults live in
the **vault home** — `~/RiverfedVaults/<slug>/` by default, overridable
via `RIVERFED_VAULTS_DIR` (env var or `.env`; CLI scripts read both, so
they resolve identically to the server). Each has its own `output/`
staging, so every base's "pending" queue is isolated, and each is its
own git repo (knowledge versioned in the USER's repo, not the
product's). The product repo ships demo vaults under `wikis/<slug>/`
(riverfed-ops); a vault-home vault wins on slug collision. Resolution
order: home → repo demo → home-as-scaffold-target. A vault = its
knowledge model's page folders + `SCHEMA.md` (copied from the model's
canonical template at creation) + a starter `index.md` whose `name:`
frontmatter is the display name and whose `model:` frontmatter declares
the knowledge model (undeclared → `karpathy-wiki`).
Resolution/scaffolding logic lives in
[`wiki/scripts/_wikis.py`](wiki/scripts/_wikis.py); paths embedded in
prompts/UI go through its `display_path()` (repo-relative inside the
project, absolute outside). The one-shot migration that moved existing
vaults out is [`wiki/scripts/migrate_vaults.py`](wiki/scripts/migrate_vaults.py).

**Knowledge models** (`models/<id>/`) define what a vault IS: its
folders + node kinds, which folder is the **capture layer** (`capture:
true` — pending-detection keys on it), the `/wiki` graph link fields,
per-folder `promote_after` thresholds, the `/wiki` MAP **card specs**
(`card: { description: <## section>, callout: <## section> }` marks a
folder browsable and names the sections its cards surface; `search_hint`
is the search-box copy), and the agent prompt templates
the pipeline uses. Parsed by
[`wiki/scripts/model_registry.py`](wiki/scripts/model_registry.py)
(mirrors `design_tokens.py`: shipped `models/<id>/` + gitignored
`models/custom/<id>/`, custom wins on id collision). `ingest.py` and
`promote_backlog.py` load the vault's model and format its prompts with
the manifest's threshold knobs; `server.py` builds `/wiki/data`,
`/wiki/graph`, and `/wikis` counts from the manifest. To change what the
ingest agent does, edit `models/<id>/ingest-prompt.md` — not ingest.py.

Three models ship: `karpathy-wiki` (teach-back wiki), `second-brain`
(PARA, capture toward action), and `sops-to-skills` (procedures, policies,
and runbooks compiled into agent skills). The "+ New" control on `/` picks the
model at create time; its **Customize…** modal edits promotion knobs +
both prompts and saves to `models/custom/<id>/` (same id = override,
new id = new model; reset = delete the override). API:
`GET /api/models[/<id>]`, `PUT /api/models/<id>` (prompt placeholders
validated at save), `DELETE /api/models/<id>`.

**Agent choice (A6 — bring your own agent):** every agent-running
script (ingest, promote, all studio generators) also takes
`--provider auto|claude-code|grok|codex` (default `auto`: the first
ready of Claude Code, Grok, Codex). An explicit choice hard-fails with
the login hint when that CLI isn't ready — never a silent fallback.
Grok is the first fallback: it reads frames through `read_file`, and
Codex still receives the same JPEGs through `codex exec --image`. In the UI the
**Agent** selector on `/` (next to the Knowledge base picker) makes the
same choice for ingest/review AND the Studio generators (shared via
localStorage). Quick status check:
`py -3.13 wiki\scripts\agent_runner.py --status`.
`CLAUDE_MODEL` (env var or `.env`) pins which Claude model every
pipeline run uses. House policy: `CLAUDE_MODEL=opus` — the alias
tracks the newest Opus-tier model (one tier below frontier) and needs
a current CLI (stale alias tables resolve low — `claude update`). A
full id (`claude-opus-4-8`) hard-pins. Unset = inherit the user's
interactive Claude Code default. `CODEX_MODEL` is the codex twin (a
pin the installed CLI can't honor fails loudly); unset, codex uses
`~/.codex/config.toml`. `GROK_MODEL` is the grok twin but carries NO
tier-ceiling meaning — grok-4.6 and grok-4.5 are versions of one model,
not tiers of a family — so it ships unset (grok's own default).

All five wiki scripts take `--wiki <slug>` (default `wiki`):

```powershell
py -3.13 wiki\scripts\pending.py          --wiki investing
py -3.13 wiki\scripts\ingest.py           --wiki investing
py -3.13 wiki\scripts\promote_backlog.py  --wiki investing
py -3.13 wiki\scripts\obsidian_pass.py    --wiki investing
py -3.13 wiki\scripts\lint_links.py       --wiki investing   # omit --wiki for all vaults
```

Server API: `GET /wikis` lists vaults (slug, name, model, counts);
`POST /wikis {"name": "Investing", "model": "karpathy-wiki"}` creates
one (`model` optional); `/convert`, `/pending`, `/ingest`, `/review`,
`/files` all accept `?wiki=<slug>`. The Studio + `/wiki` graph pages
already work per-vault through the same `GET /wikis` discovery (the
Studio passes the vault's *path* — `wikis/<slug>` — to the generator
scripts).

ENGE.WRITER uses a separate loopback-only publishing boundary:
`GET /api/writer/libraries` discovers local vaults and
`GET /api/writer/knowledge-pack?wiki=<slug>` emits the selected vault as a
bounded `enge.knowledge-pack` v1 snapshot. The publisher lives in
`wiki/scripts/writer_pack.py`; it caps packs at 500 pages and bodies at 12,000
characters, keeps source/relationship provenance, and defaults procedures and
policies to the craft lane. Only the production Writer origin and loopback
development origins receive CORS access. Restart the Python server after
changing the publisher or routes.

### Building the master deck

```powershell
cd wiki\training
marp --html --allow-local-files --theme themes/ai-builders.css ai-builders-handbook.md -o out/ai-builders-handbook.html
marp --html --allow-local-files --theme themes/ai-builders.css ai-builders-handbook.md -o out/ai-builders-handbook.pdf
marp --html --allow-local-files --theme themes/ai-builders.css ai-builders-handbook.md -o out/ai-builders-handbook.pptx
```

For per-slide PNG previews (used in the README gallery):

```powershell
marp --html --allow-local-files --theme themes/ai-builders.css --images png --image-scale 1.5 -o out/preview/ ai-builders-handbook.md
# (Marp writes "preview.001" etc. — rename to "preview/slide.001.png" pattern after)
```

Rebuild the speaker-notes Word doc:

```powershell
.venv\Scripts\python.exe wiki\training\scripts\build_speaker_doc.py
```

The Markdown→DOCX rendering lives in the shared, **design-aware** module
[`wiki/scripts/speaker_docx.py`](wiki/scripts/speaker_docx.py)
(`render_markdown_to_docx(md, out, design_path=None)`). `build_speaker_doc.py`
is a thin wrapper that pins the handbook title/eyebrow + default house palette; `studio_guide.py` calls the same renderer with the chosen
`--design`, so the Studio's speaker notes come out as a Word `.docx` styled
in the deck's palette + fonts (foundation→headings/body, vibrant
accent→H3/eyebrow/rule/borders, text-muted→subtitles, body-md→body font with
a Calibri fallback since Word can't @import web fonts). Saves via a
`.tmp.docx` atomic swap so a doc open in Word degrades gracefully.

### Regenerating the wiki atlas

```powershell
py -3.13 wiki\scripts\build_wiki_atlas.py
```

Reads live counts from `wiki/{sources,topics,entities,concepts}/`, emits
`diagrams/wiki-atlas.excalidraw` (open it in Excalidraw or Obsidian to
preview or export a PNG).

### Studio generators

From `/studio` in the browser, OR from CLI:

```powershell
py -3.13 wiki\scripts\studio_marp.py    --wiki wiki --prompt "..." --slides 14
py -3.13 wiki\scripts\studio_pptx.py    --wiki wiki --prompt "..." --slides 14
py -3.13 wiki\scripts\studio_diagram.py --wiki wiki --prompt "..."
py -3.13 wiki\scripts\studio_guide.py   --wiki wiki --target wiki/training/studio/my-deck.md
py -3.13 wiki\scripts\studio_skills.py  --wiki wikis/riverfed-ops --prompt "everything"
py -3.13 wiki\scripts\studio_anki.py    --wiki wiki --prompt "..." --cards 30
```

`studio_anki.py` authors atomic, source-cited flashcards from the base
(agent emits `<slug>.cards.json`, genanki renders `<slug>.apkg` — both in
`wiki/training/studio/anki/`). Deck/note ids are stable hashes, so
re-generating the same deck updates it in Anki instead of duplicating.

`studio_skills.py` compiles a knowledge base (best: a sops-to-skills
model base) into an agent skill library — one `SKILL.md` per
procedure/runbook in the house skill format, policies folded into
Gotchas, + library README + `agents.md`. Output defaults to
`wiki/training/studio/skills/<base>/` (gitignored); point `--out` at a
repo to install directly. It takes no `--design` (skills are plain
markdown).

All four scripts accept an optional `--design <path>` flag.
`studio_pptx.py` applies the tokens directly (mutates its palette/font
constants). `studio_marp.py` applies them by deriving a Marp theme that
overrides the `ai-builders.css` `:root` palette + fonts, then renders
through it — so the design picker now reskins both the native PPTX and
the Marp HTML/PDF/PPTX. `studio_diagram.py` + `studio_guide.py` still
accept the flag for API consistency but don't yet apply it.

The Marp reskin (`_build_design_theme` + `_prepare_design_deck` in
`studio_marp.py`) is genuinely token-driven, not just a palette swap:

- **Palette + full --grey-1..6 ramp.** The `--saber-*` aliases follow
  automatically (they're `var(--accent)` etc.), so only base tokens are
  overridden. The grey ramp maps only from neutral text tokens
  (`text-muted` / `text-faint`), never `secondary` — Aurora's `secondary`
  is bright teal and would otherwise tint subtitles.
- **Accent by vibrancy, not blindly primary.** A saturation/lightness
  check picks `primary` when vibrant (saber blue, Aurora magenta), else
  `highlight` (Heritage's `primary` is near-black ink; its accent is the
  clay `highlight`).
- **foundation powers the dark hero/section bg, not background** — a
  light palette's `background` is light and would make white cover text
  unreadable. Cover/section slides follow `components.cover-bg` /
  `section-divider-bg`; card radius follows `rounded` / `components.card`.
- **Fonts actually load.** The base theme only *names* families, so
  non-system fonts silently fall back to the OS sans (making every design
  look identically-fonted). The derived theme `@import`s each family from
  Google Fonts (Public Sans/Space Grotesk for Heritage; Sora/Inter/
  JetBrains Mono for Aurora). Falls back gracefully offline.
- **Brand SVGs are recoloured; the cover logo is dropped.** The bundled
  icons carry a hardcoded saber-blue stroke and are `<img>`-embedded (CSS
  can't reach them), so we inline each icon and swap the blue for the
  accent. The brand cover logo is removed on custom-design decks (a
  flattened gradient logo reads badly). Inlining is required because marp
  keeps `<img src>` as external paths in the HTML.

`studio_marp.py` ALSO auto-renders the .md to **HTML / PDF / PPTX**
next to the source via the marp CLI (resolved via `shutil.which("marp")`
with `npx @marp-team/marp-cli@latest` fallback). Best-effort: missing
marp emits the .md only with an install nudge. Each render success
prints `RENDERED:<fmt>:<path>` on stdout so server.py can surface them
in the JSON response — Studio UI shows all four file paths in the
status box.

### Native PPTX of the handbook

Sibling of the Marp build — same content, rendered through python-pptx
so every slide is editable in PowerPoint (real text boxes, real shapes,
embedded icon PNGs, no flattened HTML):

```powershell
.venv\Scripts\python.exe wiki\training\scripts\build_handbook_pptx.py
```

Writes to `wiki/training/out/ai-builders-handbook-native.pptx`. If
PowerPoint has it open (file lock), the build writes a sibling
`.tmp.pptx` and prints a friendly warning; close PowerPoint and re-run
to land the atomic swap.

### Regenerating the icon bank

```powershell
.venv\Scripts\python.exe landing\icons\build.py
```

Re-emits the 22 utility SVGs + 4 PNG colour variants each (saber-blue
default / -purple / -green / -yellow) into `landing/icons/png/`.
Required after any edit to the `ICONS` dict in `build.py`. The pptx
renderer embeds the colour-matched PNG variant for each accent.

## Subsystem-specific docs

Don't reinvent these — read first:

| If you're working on…                                                     | Read                                                                                                                                                 |
| ------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| Wiki page schema, slug conventions, frontmatter                           | [`wiki/SCHEMA.md`](wiki/SCHEMA.md)                                                                                                                   |
| Marp deck design (palette, components, slide types, voice)                | [`wiki/training/design.md`](wiki/training/design.md)                                                                                                 |
| Excalidraw diagrams (palette, conventions, pattern recipes)               | [`wiki/training/design.md`](wiki/training/design.md) → "Excalidraw conventions" section                                                              |
| Brand identity (logo, fonts, gradient CTA, Jedi palette)                  | [`wiki/training/design.md`](wiki/training/design.md)                                                                                                 |
| Native PPTX renderer (13 slide types, brand mark, capped cards)           | [`wiki/scripts/studio_pptx.py`](wiki/scripts/studio_pptx.py) docstring at top of file                                                                |
| Icon bank (style spec, regenerate, recolour, transparency)        | [`landing/icons/README.md`](landing/icons/README.md)                                                                                                 |
| Frame extraction strategy (when, dense-window, OCR gotchas)               | [`docs/frames-ingest-comparison.md`](docs/frames-ingest-comparison.md)                                                                               |
| Studio design presets (DESIGN.md format, palette/font overrides)          | [`designs/README.md`](designs/README.md)                                                                                                             |
| Knowledge-model manifests (folders, link fields, promote\_after, prompts) | [`models/karpathy-wiki/model.md`](models/karpathy-wiki/model.md) body + [`wiki/scripts/model_registry.py`](wiki/scripts/model_registry.py) docstring |
| Adding a new generator (next: Notion, Anki, podcast scripts)              | Pattern of `wiki/scripts/studio_marp.py` + the `/studio` UI card                                                                                     |

## Conventions

### Python

- **Python 3.10+ required** (we pin to `py -3.13` in wrappers to avoid the
  system default 3.7 on Windows)
- Use the project venv for any pip install: `.venv\Scripts\python.exe -m pip ...`
- Type hints on new function signatures; `from __future__ import annotations`
  for `X | Y` syntax
- No emojis in source files unless explicitly requested
- For Windows-spawned subprocesses, **always** pass
  `creationflags=NO_WINDOW` (defined in server.py + ingest.py) so detached
  pythonw\.exe doesn't open flashing console windows
- Stdin-pipe long prompts to the provider CLI, not as argv — Windows'
  `claude.CMD` shim truncates argv past \~8 KB and Codex reads `-` from stdin

### Wiki content

- Slug conventions, frontmatter fields, link styles: see `wiki/SCHEMA.md`
- **Memory shorthand**: drop editorial prefixes when slugging (e.g.
  "Screensharing: Foo" → `foo.md`, not `screensharing-foo.md`)
- Source pages cite the original transcript; topics aggregate
  sources; entities are named things; concepts are recurring ideas

### Decks

- Design system rules live in `wiki/training/design.md` — every Marp
  deck must follow them
- Use the existing component classes (`.cards`, `.kpi`, `.versus`,
  `.callout`, `.six-up`, `.steps`, `.outcomes`); don't invent new HTML
- One accent colour per slide unless deliberately contrasting
- **The Sith Red rule**: red (`--united` / `--saber-red`) is for errors
  only. Never on decorative cards. Use orange/yellow for differentiation.

### Native PPTX (`studio_pptx.py`)

Sibling renderer to Marp, same Jedi palette, same component vocabulary,
output is a real editable .pptx (no flattened HTML). 13 slide types
available — each one maps to a slide spec dict:

| Type        | Use for                                  | Key fields                                  |
| ----------- | ---------------------------------------- | ------------------------------------------- |
| `cover`     | Title slide                              | `title`, `subtitle`, `tags`                 |
| `lead`      | Single big-idea slide                    | `headline`, `eyebrow`, `cite`               |
| `section`   | Module divider with ghost numeral        | `number`, `module`, `title`, `subtitle`     |
| `content`   | Bulleted slide + callout                 | `title`, `bullets`, `callout`, `cite`       |
| `kpi`       | 1-3 hero-number tiles (raw counts, $, ×) | `kpis: [{value, label}, …]`, `callout`      |
| `donut-kpi` | 1-3 percentage ring charts               | `kpis: [{value: "30%", label}, …]`          |
| `quote`     | Verbatim quote with accent bar           | `quote`, `attribution`, `cite`              |
| `versus`    | Old-vs-new comparison panels             | `old: {…}`, `new: {…}`                      |
| `cards`     | 2-4 unordered parallel siblings          | `cards: [{num, title, desc, icon}, …]`      |
| `six-up`    | 3×2 grid for tight catalogues            | `items: [{num, title, desc, icon}, …]`      |
| `flow`      | 3-5 sequential steps with arrows         | `steps: [{num, title, desc, icon}, …]`      |
| `timeline`  | 3-6 chronological milestones             | `milestones: [{label, title, desc}, …]`     |
| `hub`       | Central concept + 3-6 radial spokes      | `hub: "AIOS"`, `spokes: [{title, desc}, …]` |

Choosing between `cards` and `flow`: cards = parallel/unordered;
flow = sequential. `hub` = parts-of-a-named-thing.

All content-style slides (everything except cover/lead/section) get
a small ambient diamond top-right via `_add_brand_mark(slide)` —
the deck's brand signature per design.md.

`_add_capped_card(...)` is the unified card primitive — single rounded
rect with a 4-stop hard-edge gradient stripe (accent at top/left, white
body). Used by kpi/cards/flow/six-up so the stripe and body share the
rounded corners cleanly. Pass `stripe_side="top"|"bottom"|"left"|"right"`.

PROMPT\_TEMPLATE at the top of `studio_pptx.py` is what the studio
agent uses to generate JSON specs — keep it in sync when adding new
slide types.

### Diagrams

- Excalidraw conventions in `wiki/training/design.md`
- Same Jedi palette as decks (`--saber-blue`, `--saber-purple`, etc.)
- Roughness 1, fontFamily 4 (Excalifont) for text, 3 (Cascadia) for eyebrows
- Background `#0a0d12` (deep space)

### Branding

- Product name: **Riverfed**, in user-facing copy and identifiers alike
  (`riverfed-*`, `RIVERFED_*` env vars, `com.riverfed.*` LaunchAgents,
  `~/RiverfedVaults`). Don't reintroduce older working names anywhere.
- Top nav order across all pages: **Add · Knowledge · \[Create]**.
  Create is the CTA to `/studio`. The Riverfed wordmark is the
  shared About link on every view. Routes and filenames are unchanged.
- Logo: NONE — the brand is the typographic wordmark only:
  `Riverfed` in Inter 900 (tight tracking) + a signature dot in brand
  green #1d9e66 (deck green #46c98b on dark covers). No pictorial mark
  on any page or slide; the square riverfed-mark files exist ONLY as the
  browser favicon. Full spec: design.md "Brand mark"

### Commits

- Format: `type(scope): one-line summary` followed by an explanatory body.
  Examples we use: `feat(wiki)`, `feat(studio)`, `feat(convert)`,
  `feat(diagrams)`, `fix`, `docs`, `copy`, `rebrand`.
- Always include a `Co-Authored-By` trailer naming the agent and model that
  did the work (for example `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`).
- One logical change per commit. If you find yourself writing "and also" in
  the body, split.

### Docs — keep the second collaborator current

**Paulo (`PFreitas91`) was present for none of the decisions and syncs
intermittently.** After shipping a coherent block, refresh the docs that
keep him able to contribute — invoke the **`catch-up-docs`** skill, which
carries the full procedure. Short version: `CHANGELOG.md` (new section
*and* the "How to read this changelog as PFreitas91" guide above it) →
tick `plans/implementation-roadmap.md` → `CLAUDE.md`/`AGENTS.md` if
structure or "not done yet" changed → `CONTRIBUTING.md` only if the human
workflow changed.

This is load-bearing, not courtesy: the ingest agent treats the roadmap as
ground truth, so an unticked shipped block gets restated as "the next
action" in generated pages. Treat any sentence containing **"never", "not
yet", "only", "first", or "currently"** as a dated claim and verify it
against the tree — that pattern is what caught CLAUDE.md still saying "no
unit tests" and CONTRIBUTING still telling Paulo the app had "never been
run on a Mac".

## Known gotchas

- **Ingest/review run on a job lane, not a lock** — jobs go through
  `JOBS`/`JOB_LANES` (server.py); ingest and review share the `wiki` lane, so a
  second click *queues* behind the first instead of deadlocking (the old
  `_INGEST_LOCK` single-flight is gone). **Stuck ingests self-heal now:**
  `agent_runner.run()` enforces a wall-clock timeout that kills the whole
  process group (agent CLI + tool subprocesses) — see
  [`wiki/scripts/agent_runner.py`](wiki/scripts/agent_runner.py) `_kill_tree()`
  — so a hung agent no longer pins the lane forever (fixed 2026-08-05; before
  that, streaming mode only timed out *after* stdout EOF and a hung child ran
  41 min). If you still need to kill one by hand on the Mac:
  `ps -Ao pid,etime,command | grep ingest.py`, then `kill -9 <pid>` the
  `ingest.py` / `promote_backlog.py` PID (never the launchd server or a running
  agent CLI session; on Windows it's `tasklist` + `taskkill /PID <pid> /F /T`). A
  killed mid-run ingest can leave the wiki mid-edit (e.g. a source page deleted
  before recreate) — recover with `git restore wiki/sources/<page>.md`.
- **Windows path handling** — paths must use `Path` (not f-strings of
  `\` joins). All scripts already do this.
- **Provider nesting env vars** — Claude Code refuses nested launches when
  `CLAUDECODE` / `CLAUDE_CODE_ENTRYPOINT` leak; Codex carries its own sandbox
  markers; Grok scrubs `GROK_SANDBOX` and `GROK_AGENT` so a parent session
  cannot confine vault writes. `agent_runner.scrub_env()` removes the
  correct set per provider.
- **Multi-line prompts** — `claude.CMD` truncates argv past \~8 KB, and
  `grok -p -` treats the `-` as a literal prompt. `agent_runner` owns
  delivery (`PROMPT_DELIVERY`): stdin for Claude and Codex, a temp file
  for Grok. Callers pass `prompt=`.
- **Windows .CMD resolution in subprocess** — `subprocess.run(["claude", ...])`
  does NOT walk PATHEXT on Windows; it requires the exact filename. npm
  registers `claude.CMD` and `codex.CMD` (no `.exe`), so bare-string
  invocations fail with `FileNotFoundError`. All agent invocations go through
  [`wiki/scripts/agent_runner.py`](wiki/scripts/agent_runner.py) (A6),
  which resolves via [`wiki/scripts/_agent_bin.py`](wiki/scripts/_agent_bin.py)
  and honours the `CLAUDE_BIN` / `CODEX_BIN` / `GROK_BIN` env overrides for
  pinning a specific binary (grok's installer uses `~/.local/bin`, which a
  launchd/systemd service PATH usually misses — pin it there).
  Never spawn an agent CLI directly from a new script —
  call `agent_runner.run()` / `.probe()` instead (it also owns per-provider
  argv construction, prompt delivery (stdin, or a temp file for grok), the
  nested-session env scrub, `NO_WINDOW`, and the codex `exec --help`
  feature-probe).
- **ffmpeg + Tesseract for --frames** — Tesseract is a system install
  (`winget install UB-Mannheim.TesseractOCR`). ffmpeg is bundled via the
  `imageio-ffmpeg` pip package, no system install. If a fresh machine
  doesn't have Tesseract, `--frames` still works but skips the OCR pass
  (with a warning) — graceful degradation.
- **Local YouTube transcription**: `setup.sh` installs whisper.cpp
  1.9.2 and the 75 MiB smoke model on macOS. The 547 MiB
  `large-v3-turbo-q5_0` model is an explicit production-quality choice.
  Models live in the user cache, never in Git. Caption recovery order is
  human, automatic, local, optional Groq, then rejection. Keep this
  order and the shared transcript guard intact.
- **Marp --allow-local-files** prints a scary warning but is required
  for the deck to embed local SVGs.
- **PPTX file locks** — if PowerPoint has the deck open, `marp -o foo.pptx`
  fails with `EBUSY`. Close PowerPoint, retry. The native pptx builder
  (`build_handbook_pptx.py`) handles this gracefully by writing to a
  sibling `.tmp.pptx` and atomically swapping into the canonical path
  — re-run after closing PowerPoint to land the swap.
- **svglib/reportlab transparency** — `renderPM` always renders to an
  opaque white canvas; `configPIL={'transparent': ...}` only works in
  palette mode, not RGB. Both `landing/icons/build.py` and
  `wiki/scripts/studio_pptx.py` post-process the PNG via PIL: convert
  to RGBA and scale alpha by `min(R,G,B) > 200` so pure white → alpha 0
  and anti-aliased fringes fade cleanly.
- **Hand-drawn diagrams + OCR** — Tesseract returns gibberish or
  empty text for Excalidraw / whiteboard frames because the strokes
  aren't typeset characters. By default this drops them below the
  `vision_relevant` threshold (≥50 OCR chars) and the ingest agent
  skips them. Two protections in place:
  1. `convert.py --dense-until` auto-flags every dense-sampled frame
     as `vision_relevant=True` regardless of OCR — the user-supplied
     window IS the "expect visual content here" signal.
  2. Claude opens tagged frames through Read; Codex receives the same JPEGs
     through `codex exec --image` because `--add-dir` alone does not send
     pixels to the model. The prompt requires visual inspection before a
     duplicate skip. Frame downloads retry transient failures three times.
- **start.vbs vs serve.cmd** — start.vbs uses `pythonw.exe` (no console).
  serve.cmd uses `python.exe` (visible console for debugging). Stop with
  `stop.cmd` either way.

## What's intentionally not done yet

- **Notion/podcast generators** — the Studio accepts new generators;
  the pattern is `studio_anki.py` (JSON spec → deterministic renderer)
  or `studio_skills.py` (agent writes files directly). Add a
  `studio_<kind>.py` + a card in `landing/studio.html` + the route in
  `server.py`'s `_handle_studio`.
- **Source review and ingest recovery is partly shipped.** The Knowledge
  queue now surfaces provenance, duration, language, word count, guard
  diagnostics, and targeted recovery; server preflight blocks bad captures
  and one usable immutable revision is selected per source. Still open:
  reviewed transcript revisions, approval, and the source-to-wiki diff. See
  [`plans/implementation-roadmap.md`](plans/implementation-roadmap.md).
- **External SOPs-to-Skills pilot** is opportunity-triggered, not a
  scheduled product milestone. The model and compiler stay shipped;
  create the consultancy delivery kit only when a real company
  opportunity exists.
- **Skill eval harness** remains useful as the QA gate for that future
  external pilot, but it does not outrank editor and ingest quality.
- **API-key agent runners** — explicitly cut from A6 v1 (recorded in
  the roadmap so it doesn't creep back): every core task edits files,
  so text-only API runners would serve only the JSON-spec generators —
  a confusing capability matrix. If headless pilot deployments ever
  need API mode, use the Claude Agent SDK / Codex SDK as real agent
  loops — a v2 decision.
- **Watcher auto-chain under real cadence** — the sweep→auto-ingest
  chain is code-complete and the queue-for-approval path is verified
  end-to-end; the first *scheduled* unattended ingest (vs the manual
  "Check now" sweep) will happen naturally once a watched channel
  uploads — worth confirming in `server.log` when it does.
- **CI depth** — `.github/workflows/ci.yml` covers compile/parse/lint
  smoke (B3) plus `unittest discover -s tests`. No deck-rendering check
  and no Windows runner yet.

## When in doubt

Read [`README.md`](README.md) for the product narrative, [`CONTRIBUTING.md`](CONTRIBUTING.md)
for working-with-each-other conventions, and the subsystem-specific docs
linked in the table above for the technical details.
