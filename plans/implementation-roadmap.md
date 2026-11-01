# Implementation roadmap — from "one wiki" to the knowledge platform

**Companion to** [`multi-paradigm-knowledge.md`](multi-paradigm-knowledge.md)
(the strategy doc — read that first for the *why*). This doc is the *how and
in what order*: what we build next, grounded in three weeks of real usage,
demos, and the failures we actually hit. Written 2026-06-09.

The shape of it: **two tracks run in parallel.** Track A is the product bet
(knowledge models as templates → the B2B "knowledge → agent" wedge). Track B
is reliability — every demo and test session this month hit the same three
operational failures, and they'll bite the brother, friends, and any future
customer harder than a missing feature will.

---

## Strategy decision — packaging & go-to-market (decided 2026-06-12)

Brainstormed and settled before committing the next blocks:

- **Stay private for now** (the two of us); keep dogfooding daily.
- **Destination: hybrid.** Open-source the local-first app as the
  distribution engine. Keep SOPs-to-Skills consultancy as an
  opportunity-triggered revenue motion, not a scheduled product
  milestone. One codebase can support both when demand appears.
- **Hosted SaaS: deferred until evidence** (non-technical users asking
  for it, or pilot clients wanting managed hosting). The BYO-Claude
  design is a local-first strength and a multi-tenant blocker —
  re-platforming before demand means months of rebuild aimed at
  NotebookLM's home turf.
- **Positioning** (why we win where we play): NotebookLM's studio
  outputs are sealed artifacts inside their app; ours are *files you
  own* — an Obsidian-compatible wiki in git, editable .pptx, .apkg,
  .excalidraw, executable SKILL.md libraries. Chat-native vs
  **agent-native**: our bases live where the user's own Claude Code can
  act on them. For SMBs, local-first kills the "upload our SOPs to your
  cloud?" objection.
- **Name**: **Riverfed** (decided 2026-11-01 for the open-source
  launch). Still open: an EUIPO/TMview check in classes 9, 41 and 42.

What this changes below: a new **Track C — launch readiness** carries
the work between "private tool" and "hybrid launch"; A4 interop drops
off the critical path.

---

## Where we actually are (verified 2026-06-09)

**Shipped since the strategy doc** — the plumbing the plan assumed we'd need:

| Capability                                                               | State                                            |
| ------------------------------------------------------------------------ | ------------------------------------------------ |
| Design picker → Marp + native PPTX + Word speaker notes + diagrams       | ✅ fully token-driven, 3 shipped presets + custom |
| Frame capture (dense window, vision-relevant flagging, UI toggle)        | ✅ proven on whiteboard + screen-recording videos |
| Ingest robustness (single-flight lock, video-id pending, alt\_url merge) | ✅                                                |
| PDF fallback chain (pdfplumber → pypdfium2 → OCR)                        | ✅                                                |
| Project skills (`.claude/skills/` — 6 SOPs-for-AI)                       | ✅ dogfooding the exact pattern Phase 3 sells     |
| Shared top nav (single source of truth)                                  | ✅                                                |
| Two-collaborator hygiene (.gitattributes, gitignore, CHANGELOG catch-up) | ✅                                                |

**Not started** — the multi-paradigm plan itself:

- No `models/` directory; ingest.py + pending.py hardcode `wiki/`
- `/ingest` takes no wiki param; graph + list\_wikis hardcode the 4 folders
- No scaffolder, no model picker, no second paradigm, no `studio_skills.py`

**Known operational debt** (all hit repeatedly this month):

1. **Long operations are blocking fetches.** Convert/ingest/studio hold one
   HTTP request open for minutes; the browser drops it and the UI shows a
   stale "Ingesting…" banner forever. Every "it's stuck" alarm this month
   (≥4 incidents) was this or its cousin.
2. **marp/chromium renders occasionally zombie.** We found one stuck for
   125 minutes; it silently blocked later renders.
3. **The server dies on sleep/sign-out** and stays down until someone
   notices (3 incidents, including right before a demo prep).
4. **Promotion threshold mismatch.** The prompt says "promote at ≥2
   sources" but the agent applies \~3+-and-novel; the user experiences
   "nothing ever promotes." Needs a *decision*, and the manifest work in
   Phase 0 is exactly where the knob belongs.
5. No CI — a syntax error in any script ships silently until someone runs it.

---

## Track A — implement the plan (the product bet)

### A0. Foundation refactor (Phase 0 of the strategy doc) — ✅ shipped 2026-06-11

Pure refactor, zero behavior change, proves the abstraction.
*(Shipped as specced — ingest prompt verified byte-identical, graph/data
JSON deep-equal. One deviation: wiki/SCHEMA.md stays a full live copy
with a pointer comment, not a stub — the ingest agent reads it per-vault.
Debt #4 resolved with the defaults below: concepts 3, entities 2.)*

- **NEW models/karpathy-wiki/**: `model.md` (manifest: folders, node
  kinds, link fields, **promote\_after per folder**, generator gating),
  `SCHEMA.md` (moved from `wiki/SCHEMA.md`, pointer left behind),
  `ingest-prompt.md` (extracted from the f-string in `ingest.py`).
- **NEW wiki/scripts/model\_registry.py** — mirror `design_tokens.py`
  exactly: `load_model()`, `list_models(root)` (shipped + `models/custom/`
  gitignored), `save_model()`. Same path-traversal-guarded id regex.
- **Parameterize the pipeline by wiki slug**: `ingest.py --wiki <slug>`,
  `pending.py --wiki <slug>`, `/ingest` POST body `{wiki}`. The wiki's
  folder declares its model (frontmatter in `index.md`: `model: karpathy-wiki`).
- **De-hardcode** `list_wikis()` + `build_wiki_data()` + `build_wiki_graph()`
  — read folders/node-kinds/link-fields from the manifest.
- **Resolve debt #4 here**: `promote_after` lives in the manifest;
  `promote_backlog.py` reads it and the prompt states the *actual* rule.
  (Default: keep concepts at 3, entities at 2 — matches observed agent
  judgment — but now it's a visible, per-model knob, not folklore.)

**Verify**: re-run an ingest on a fixture transcript → byte-identical wiki
output vs today. `/wiki` graph renders unchanged. `pending.py` unchanged.

### A1. Scaffolder + model picker (Phase 1) — ✅ shipped 2026-06-11

Clone the design-picker pattern end-to-end (it's the proven template):

- "Create knowledge base" card on `/` → pick a model template → scaffolds
  `<name>/` with folders + SCHEMA + index.md (+ model frontmatter).
- Model picker/editor modal in the UI (edit/reset/create → `models/custom/`).
- CRUD endpoints `/api/models[/<id>]` (copy the designs CRUD shape).

**Verify**: scaffold an empty base from the UI; it appears in `list_wikis()`;
ingest into it works with its model's prompt.
*(Shipped — Playwright-verified UI flow; the editor edits knobs + both
prompts with placeholder validation at save.)*

### A2. Second Brain / PARA template (Phase 2 — personal track) — ✅ shipped 2026-06-11

- `models/second-brain/` — projects/areas/resources/archives, its own
  ingest-prompt (capture → actionable note, not teach-back).
- Dogfood on real personal content (email exports, meeting notes via the
  existing file converter).

**Verify**: one source ingested into PARA lands as a project/resource note;
generators can build a deck from it.
*(Shipped — real ingest of a weekly-review note produced a capture note +
a projects/ page with outcome + next actions, and correctly Inbox'd the
below-bar area/resource candidates. Required a new manifest concept:
capture: true marks the folder pending-detection keys on. Generators
are vault-path-driven and folder-agnostic by inspection; first real PARA
deck still to be produced by daily use.)*

### A3. SOPs → Agent Skills generator (Phase 3 — **the B2B wedge**) — ✅ shipped 2026-06-11

*(Shipped — models/sops-to-skills + studio\_skills.py + Studio card. The
pilot ran on our own CONTRIBUTING.md: 7 procedures / 6 policies / 2
runbooks extracted, 9 skills compiled via the live /studio/skills route,
and a fresh claude -p session in a scratch repo executed
sync-and-ship-a-work-session end-to-end — house commit format + trailer
verified on the bare remote. The eval harness ("go further" #2) is
deferred: libraries are execution-verified, not yet grader-verified.)*

- **NEW wiki/scripts/studio\_skills.py** + Studio card: reads a knowledge
  base, emits `.claude/skills/<name>/SKILL.md` (+ `references/`) and an
  `agents.md` context file. We already wrote 6 production skills by hand —
  the generator encodes that exact format + the operator best-practices
  already in the wiki (`building-skills-for-claude`).
- `models/sops-to-skills/` template (procedures/policies/runbooks).
- **Pilot it**: take one real small business's docs (even ours — the
  product repo itself), run the full drop-docs → skill-library flow, and
  have a fresh Claude Code session execute one generated skill end-to-end.
  That executed-skill demo IS the sales pitch.

### A4. Interop (Phase 4) — ◐ first on-demand bridge shipped 2026-08-24

Shared `output/` substrate, cross-model wikilinks, meta-index. Don't design
this before A2 ships; the strategy doc's open questions get answered by
real usage.

The first evidence-led interop edge now exists: the local Riverfed server can
publish any selected vault as a strict `enge.knowledge-pack` v1 for the private
ENGE.WRITER workspace. Discovery and publishing stay loopback-only, snapshots
are bounded and deterministic, and Writer must explicitly import or refresh
them. This does **not** ship the broader shared-output substrate, cross-model
wikilinks, or meta-index; those remain on demand.

### A5. Model-adaptive /wiki page — ✅ shipped 2026-06-11

Surfaced by the first non-karpathy vaults: the `/wiki` MAP view's list
sections, sidebar, search modes, and per-kind card layouts are hardcoded
to topics/concepts/entities — a PARA or sops-to-skills base renders empty
sections. (The graph view, tiles, counts, and lede are already
model-driven; a hotfix auto-switches kind-less vaults to the graph.)

Design the MAP view to follow the manifest:

- **Sections per kind**, driven by the model's folders: list + search any
  kind, with the mode toggle (today's TOPICS|CONCEPTS) generated from the
  model instead of hardcoded.
- **Per-kind card fields** declared in the manifest (which frontmatter/
  sections to surface — e.g. procedures show trigger + step count;
  projects show status + outcome; topics keep description/why-it-matters).
  Today these field extractions live per-kind in `build_wiki_data()`;
  move the *what-to-show* part into the manifest so a custom model's
  pages get sensible cards without server edits.
- **Sidebar + search** index every kind, not just topics/concepts.
- Keep the karpathy view pixel-identical — it's the reference rendering.

**Verify**: `/wiki` on a sops-to-skills vault lists procedures/policies/
runbooks as browsable card sections with search; karpathy vault unchanged.

**Shipped 2026-06-11** (Block 6): `card` + `search_hint` manifest fields
(registry: `card_spec()` / `browsable_folders()`); `/wiki/data` returns
model-ordered `sections`, `/wiki/graph` returns `kinds` + per-node
`folder`; MAP sidebar/toggles/search/cards and the graph legend/colors
all generate from them. Verified: karpathy /wiki rendered text
byte-identical before/after (Playwright diff; one deliberate addition —
concept cards now show their last-updated pill like topics); ops vault
browsable as procedures(7)/policies(6)/runbooks(2) with search and
vault-aware OPEN MD links; Customize PUT round-trips the new fields.

---

### A6. Multi-provider agent runner — "bring your own agent" — ✅ shipped 2026-07-04 (both steps)

Origin: a Codex-authored plan reviewed together 2026-06-12; the verdicts
below record what we adopted, corrected, and cut, so the reasoning
survives until implementation.

**Goal**: every agent task (ingest, promotion, all Studio generators,
the watcher's auto-chain) runs on the user's choice of subscription
CLI — Claude Code (today's behavior) or Codex — through one provider
layer. This is the OSS launch headline ("works with the agent you
already pay for") and derisks the SMB pitch for ChatGPT-shop clients.

**Design (adopted from the Codex plan):**

- `wiki/scripts/agent_runner.py` — the provider interface:
  `status()` → `{provider, ok, logged_in, account, version}`;
  `run(prompt, cwd, writable_dirs, image_paths, timeout)` → streamed
  logs + returncode. Providers: `claude-code` (default), `codex`.
- **Two-step ship, A0-style**: (1) move all 9 call sites (server +
  ingest/promote + 6 studio scripts) onto the runner with Claude
  behavior byte-identical; (2) add the Codex runner. The swap is only
  feasible because scripts verify by FILESYSTEM, not transcript — keep
  that invariant.
- Claude runner: exactly today's behavior (stdin prompts, --add-dir,
  env scrub, CLAUDE_BIN override).
- Codex runner: `codex exec --sandbox workspace-write --cd <project>`,
  prompt via stdin; auth via `codex login status`. **Feature-probe the
  flag set** (`codex exec --help`) and degrade gracefully — the Codex
  CLI moves fast; do not hardcode flags from the plan (`--ephemeral` /
  `codex doctor` were unverified).
- Server/UI: `claude_ok`/`claude_auth` → `agent_ok`/`agent_auth`;
  provider selector Auto → Claude → Codex. **Explicit selection
  hard-fails with the login hint — never silent fallback.** Cache
  `status()` with a short TTL (/pending polls every 10 s; two providers
  would otherwise mean 4 subprocess probes per poll).
- Skills compiler emits both `.claude/skills/` and the Codex-readable
  skills tree + uppercase `AGENTS.md` (verify the exact Codex skills
  path at implementation time).

**Corrections to the original plan (decided in review):**

- **Frames stay lazy.** Keep the read-2-3-🔍-frames-from-disk protocol
  for both providers (Codex can view workspace images); upfront
  `--image` only as a small-count fallback — a 60-frame deep capture
  must not be front-loaded into context.
- **Windows resolution**: generalize `_claude_bin.py` → `_agent_bin.py`
  (npm installs `codex.cmd`; bare-name subprocess fails — the
  documented PATHEXT gotcha). Per-provider env-scrub lists (Claude:
  CLAUDECODE etc.; Codex: its own nested-session vars).
- **Codex refuses non-git dirs** by default
  (`--skip-git-repo-check`) — invisible today, real once C1 moves
  vaults out of the repo. Design `writable_dirs` together with C1.
- **Prompt audit**: model templates must stay provider-neutral — no
  Claude-specific tool vocabulary in `models/<id>/*.md`.

**Cut from v1** (recorded so it doesn't creep back): raw API-key
runners (`openai_api` / `anthropic_api`). Text-only runners serve only
the JSON-spec generators while every core task edits files — a
confusing capability matrix in exchange for two more runners to
maintain, and it contradicts the feature's premise (use the
subscription you already pay for). If API mode is ever needed (headless
pilot deployments), use the Claude Agent SDK / Codex SDK as real agent
loops — a v2 decision.

**Verify**: the same fixture video ingested into two scratch vaults,
one per provider — outputs won't be byte-identical (different models)
but both must be schema-valid: pages in the model's folders,
frontmatter intact, `lint_links.py` clean, pending empty afterward.
Skills compile lands both trees. Watcher auto-chain gates on
`agent_runner.status()`. Step 1 alone must pass the A0 bar:
byte-identical Claude behavior.

**Sequencing**: after C1 (shares the writable-dirs design), before C2
(the Mac pass then exercises both runners).

**Step 1 shipped 2026-07-04**: `wiki/scripts/agent_runner.py` owns
binary resolution (via \_claude\_bin), argv construction, stdin prompt
delivery, per-provider env scrub, NO\_WINDOW, both run modes (streamed
for ingest/promote, captured for the studio scripts) and the
version/auth probes; all 9 call sites moved onto it. Verified at the A0
bar with a subprocess-capture harness over all 12 invocations —
identical argv, cwd, timeouts, creationflags, encodings and prompt
sha256s — plus a byte-identical ingest `--dry-run`, a byte-identical
`/pending` JSON against the restarted server, and a real end-to-end
ingest into a scratch vault-home vault (109 s, pages + lint clean) run
from *inside* a Claude Code session (proves the nested-session scrub
live). Two intended deviations, both invisible in normal operation:
marp/pptx/diagram/guide env scrub unified from `CLAUDECODE=""` to the
canonical pop of CLAUDECODE/CLAUDE\_CODE\_ENTRYPOINT/CLAUDE\_PROJECT\_DIR
(ingest's documented pattern), and the frames `--add-dir` now precedes
`--allowedTools` (flag *set* identical). `status()` already returns the
canonical `{provider, ok, logged_in, account, version}` shape —
`py -3.13 wiki/scripts/agent_runner.py --status` prints it — so step
2's server/UI/watcher adoption is a rename, not a redesign. Step 2
prerequisite: the Codex CLI installed on a dev machine to feature-probe
`codex exec --help`.

**Step 2 shipped 2026-07-04** (same day — the Codex CLI landed on the
dev machine): probed codex-cli 0.142.5 and the real flag set is richer
than the June plan assumed — `--add-dir` exists (maps 1:1 to our vault
dirs), `--ephemeral` is real (pipeline runs don't pile up in the
session list), sandboxing works on native Windows (`workspace-write`
verified writing through `--add-dir` in a git-less dir). The codex argv
is built ONLY from flags advertised by `codex exec --help` (probed once
per process, cached) so CLI drift degrades gracefully; a missing
`--sandbox` refuses to run rather than running unsandboxed.
`_claude_bin.py` generalized to `_agent_bin.py` (CLAUDE\_BIN /
CODEX\_BIN overrides; the old module stays as a shim). Server: /pending
now returns `agent_ok` + `agent_auth` {auto, providers}; one
`_check_agent_auth` gate for ingest/review/studio; the watcher
auto-chain gates on `resolve_provider("auto")`; status probes cached
20 s (two providers × 10 s polls). UI: **Agent** selector
(Auto → Claude Code → Codex) in the vault bar, shared with the Studio
via localStorage; explicit picks render that provider's login hint when
not ready. Skills compiler emits the `.claude/skills/` tree + uppercase
`AGENTS.md` (the convention Codex discovers). Prompt audit: all six
model prompt templates neutralized (headless wording instead of
Claude's `-p`, "view frames as images" instead of the `Read` tool name).

**Exit test met**: the same fixture transcript ingested end-to-end via
BOTH providers into scratch vault-home vaults — Claude 109 s / Codex
194 s, both schema-valid (pages in model folders, frontmatter intact,
`lint_links.py` clean, pending empty after). Codex's agent also
correctly held single-source topics below the promotion bar. Skills
compile verified landing both trees; hard-fail / fallback / TTL
semantics unit-checked; the selector Playwright-verified live.

---

### A7. Third provider — Grok CLI (A6, cont.) — ✅ shipped 2026-08-15 (both steps)

Origin: the user already pays for Grok and reports it fast and cheap.
A6 built the provider layer for exactly this, so the real question this
block answers is whether that layer holds for a provider nobody had in
mind when it was designed. It does — with one structural exception,
recorded below.

**Goal**: `grok` joins `claude-code` and `codex` as a first-class
provider for every agent task (ingest, promotion, the six Studio
generators, the watcher auto-chain), selectable from the Agent selector
and from `--provider` on every script.

**Probed, not assumed** (grok 1.0.3, Mac, 2026-08-15 — A6's "never
hardcode flags from the plan" correction, applied a second time). Grok
is a Claude-Code-shaped CLI, not a Codex-shaped one:

| Capability | claude-code | codex | grok |
| ---------- | ----------- | ----- | ---- |
| reads `CLAUDE.md`, `.claude/skills`, `.claude/agents` | native | needs the `.agents/` mirror | native (documented compat) |
| sees frame JPEGs | yes (Read) | yes (`codex exec --image`) | **yes**, via its own `read_file` |
| prompt on stdin | yes | yes (`-`) | **no** |
| `--add-dir` | yes | yes | not needed (no sandbox by default) |
| flag stability | stable | drifts (hence the help-probe) | stable, Claude-compatible |

Two of those invert what A6 would lead you to expect, so state them
plainly. **Grok can see frames** — verified against a real deep-capture
frame from the cloudflare source, which it described correctly through
`read_file`. So Grok inherits Claude's lazy read-2-3-🔍-frames protocol
unchanged and does NOT need the `--image` handoff Codex needs; A6's
"frames stay lazy" correction holds for it as written. And **Grok
cannot take a prompt on stdin** — `grok -p -` treats the `-` as a
literal prompt. It takes `--prompt-file <path>`, which also implies
headless single-turn.

**Design:**

- **The one structural change**: `agent_runner.run()` currently writes
  the prompt to the child's stdin for every provider. It grows a
  per-provider delivery mode — `stdin` (claude, codex; unchanged) vs
  `file` (grok: a `NamedTemporaryFile`, its path passed as
  `--prompt-file`, unlinked in a `finally` that also covers the timeout
  path). File mode skips the prompt-writer thread and the Windows
  write/read deadlock it exists to dodge. Both run modes, the kill-tree
  and the wall-clock deadline timer are otherwise untouched.
- Grok argv (every flag verified accepted on 1.0.3):
  `grok --prompt-file <tmp> --permission-mode bypassPermissions
  --sandbox off --no-leader --cwd <project> [--model <GROK_MODEL>]`
- `--permission-mode bypassPermissions` is the
  `--dangerously-skip-permissions` twin.
- `--sandbox off` is defensive, not cosmetic. Grok's sandbox is off by
  default — which is exactly why writes to vault dirs outside the cwd
  just work and no `--add-dir` equivalent is needed — but `--sandbox`
  also reads `GROK_SANDBOX` from the environment, and its `workspace`
  profile confines writes to cwd + `/tmp`. Pinning `off` in argv makes
  the vault-write guarantee independent of the user's shell.
- `--no-leader` is the subtle one. Grok can run against a shared leader
  process (`~/.grok/leader.sock`, `[cli] use_leader`). Under leader
  mode the real agent lives outside our process tree, so `_kill_tree()`
  would reap a client and leave the worker running — silently voiding
  the timeout contract that the 2026-08-05 41-minute-hang fix exists to
  enforce. Off by default today; pin it anyway.
- `add_dirs` is a documented no-op for grok, mirroring how
  `allowed_tools` is a no-op for codex.
- Status probe: there is no `grok login status`. Use `grok --version`
  (~0.05 s) then `grok models` (~0.7 s), which prints `You are logged
  in with grok.com.` plus the model list — parse that line for
  `logged_in` and `account`, same shape as `_status_codex`. Both fit
  the 20 s TTL cache budget; the transient-failure guard applies
  unchanged.
- Env scrub: `GROK_SANDBOX` and `GROK_AGENT` (the latter can swap the
  agent profile out from under the pipeline). Grok publishes no
  documented nested-session marker like `CLAUDECODE` — probe from
  inside a grok session at implementation time and add it if one turns
  up.
- **No feature-probe layer.** Codex has `_codex_exec_flags()` because
  its CLI drifts; grok's surface is stable and Claude-compatible, and
  every flag above is verified. A second help-scraping cache would be
  cargo-culted symmetry. If a guard is wanted, one startup assertion
  beats a probe.

**Decisions resolved 2026-08-15 (both by the user):**

1. **Auto order stays `("claude-code", "grok", "codex")`** — today's
   default is unchanged and Grok becomes the FIRST fallback. That is a
   real upgrade to the 2026-07-05 failure path: when Claude hit its
   usage limit mid-ingest, Codex finished the queue but could not see
   frames. Grok can, so an auto-failover now preserves deep visual
   capture instead of silently degrading to OCR-only.
2. **`GROK_MODEL` ships unset**, wired as a knob and commented out in
   `.env.example`, twinning `CODEX_MODEL`. The one-tier-below-frontier
   ceiling from the model policy does NOT map here: `grok-4.6` and
   `grok-4.5` are versions, not tiers, so there is no ladder to hold.
   Say that in the `.env.example` comment rather than implying a
   ceiling that nothing enforces.

**Cut from v1** (recorded so it doesn't creep back):

- An `XAI_API_KEY` raw-API runner — the same reasoning that cut
  `openai_api` / `anthropic_api` in A6, and grok's own docs treat the
  key as a custom-endpoint concern, not the subscription path.
- Mapping `allowed_tools` onto grok's `--allow`. The compat alias
  `--allowedTools` exists, but grok's tool IDs differ
  (`run_terminal_cmd`, `search_replace`, `read_file`), so under
  `bypassPermissions` a partial mapping buys nothing and misleads the
  next reader.
- A third skills tree. Grok reads `.claude/skills/` and `CLAUDE.md`
  natively, so the `.claude` ↔ `.agents` mirror that
  `test_docs_freshness.py` enforces gains no third copy.

**Known risk, time-boxed**: grok's plain output emits very few newlines
— narration runs straight into the answer — and `on_line` is
newline-driven, so the job log may arrive as one chunk. (Codex needed
`_codex_line_filter` for the opposite reason.) If it reads badly, the
fix is `--output-format streaming-json` (NDJSON of session updates)
plus a small parser: spike it inside step 1, do not build it upfront.
That NDJSON shape is UNVERIFIED — the planning session could not
capture it.

**Touch points** (most call sites need nothing — they already derive
from `agent_runner.PROVIDERS`):

- `_agent_bin.PROVIDER_BINS` (`grok` / `GROK_BIN`), and in
  `agent_runner`: `PROVIDERS`, `DISPLAY_NAMES`, `LOGIN_HINTS`
  (`grok login`), `CMD_LABELS`, `_SCRUB_VARS`, `_ARGV_BUILDERS`,
  `_STATUS_FNS`.
- `ingest.py` — `image_paths` stays gated on `provider == "codex"`
  (correct for grok, but comment it, so nobody later assumes grok is
  text-only).
- The six `studio_*.py` `--provider` help strings hardcode "auto
  (default), claude-code, or codex" — derive them from
  `agent_runner.PROVIDERS` once instead of adding a third literal in
  six places.
- `index.html`: the no-agent-ready hint (hardcodes the two login
  commands), the visual-capture warning ("Codex will not receive video
  frames" — now wrong for two of three providers), and the selector
  tooltip. The selector itself is data-driven and needs nothing.
- `.env.example` (`GROK_MODEL` block + `GROK_BIN`), `CLAUDE.md`,
  `AGENTS.md`, `README.md`, `CONTRIBUTING.md`, the `riverfed-ops`
  procedures (ingest-a-source, set-up-a-fresh-machine, contributing),
  CHANGELOG + the Paulo catch-up guide.
- Tests: extend `test_agent_runner_images.py` (grok gets no `--image`
  and no `--add-dir`), `test_agent_runner_timeout.py` (kill-tree in
  file-delivery mode, and the temp prompt file is unlinked on the
  timeout path), `test_agent_status_transient.py`; add one for
  `--prompt-file` delivery and for `--sandbox off` / `--no-leader`
  being present in argv.

**Two-step ship, A6-style**: (1) the stdin → `--prompt-file` split
alone, with claude and codex byte-identical at the A0 bar — it is the
only edit touching the shared path all three providers use; (2)
register grok and adopt it across UI, docs and tests.

**Verify**: A6's exit test, re-run for the third provider — the same
fixture transcript ingested end-to-end via grok into a scratch
vault-home vault, schema-valid (pages in the model's folders,
frontmatter intact, `lint_links.py` clean, pending empty afterward).
Because grok has vision the fixture MUST be a frames-bearing source and
the pages must carry frame citations — that is the claim Codex cannot
make, and the reason this provider earns a block. Plus: an explicit
pick that is logged out hard-fails with grok's login hint, and
auto-failover from a logged-out claude lands on grok, not codex.

**Sequencing**: independent of C3 and C4 — one focused session,
schedulable whenever. Prerequisite: commit the in-flight
`agent/local-whisper-bootstrap` work first; this block touches many
files and the checkout is shared with parallel sessions.

**Shipped 2026-08-15** (both steps, same session as the plan).

**Step 1 — per-provider prompt delivery.** `PROMPT_DELIVERY` decides how
the prompt reaches each CLI: "stdin" (claude-code, codex — unchanged) or
"file" (grok). File mode writes a temp file BEFORE argv is built (the
builder puts the path in the command line), hands the child `DEVNULL`
for stdin so a CLI that reads stdin at startup sees EOF rather than
blocking on a pipe nobody will write, and unlinks the file in a `finally`
that also covers the timeout path. The two run modes moved into
`_run_captured` / `_run_streamed` so that cleanup wraps both; the
streaming prompt-writer thread is skipped entirely under file delivery.
A0 bar met: claude-code and codex argv verified byte-identical against
the previous commit across four cases (with and without `add_dirs` /
`allowed_tools`), both still on stdin, and both smoke-tested live
through `run()` (claude 11.4 s rc=0, codex 60.9 s rc=0).

**Step 2 — grok registered.** Argv is
`grok --prompt-file F --permission-mode bypassPermissions --sandbox off
--no-leader --cwd <project> [--model $GROK_MODEL]`. No feature-probe
layer (grok's surface is stable and Claude-compatible, unlike codex's).
`add_dirs` and `allowed_tools` are documented no-ops. Status probe is
`grok --version` + `grok models` (there is no `grok login status`),
parsing "You are logged in with grok.com." — ~0.75 s for the pair, well
inside the 20 s TTL cache. Env scrub takes `GROK_SANDBOX` and
`GROK_AGENT`. `provider_arg_help()` now builds the `--provider` help
from `PROVIDERS`, replacing the two-provider string that had been
hardcoded in six studio scripts; the UI's no-agent hint likewise builds
from the `/pending` payload, so provider number four needs no UI edit.

**Exit test met**: the 13-frame source
`the-1-trending-github-repo-just-solved-claudes-search-problem` ingested
end-to-end via grok into a scratch vault-home vault — 271 s, exit 0, 6
pages in the model's folders, frontmatter intact, `lint_links.py` clean,
pending empty afterward, and the finalize pass rewriting 3 files without
complaint. Crucially the pages carry **frame citations**
(`frame t=00:45`, `04:30`, `05:15`) for structure the audio never
states: the seven-step pipeline diagram, the README report card, the
install matrix. That is the claim codex cannot make, and it is why grok
sits ahead of codex in the auto order. Grok also left no junk in the
repo root (codex friction #2 does not reproduce). The full 165-test
suite is green.

**Two things worth carrying forward:**

- A blanket "Claude Code" → "Codex" find-replace had previously
  corrupted AGENTS.md's provider paragraphs into nonsense
  (`--provider auto|Codex|codex`, "prefers Codex, falls back to Codex",
  "`Codex update`", "`Codex-opus-4-8`"). Fixed while rewriting those
  paragraphs. Provider ids are ids in BOTH mirrors — never sed them.
- **Pre-existing, provider-independent bug found during the exit test**:
  a source title containing ` #` is truncated at the hash. The
  transcript frontmatter from `convert.py` quotes it correctly
  (`title: "The #1 Trending..."`), but the ingesting agent copies it
  into the wiki page UNQUOTED, and `_frontmatter._strip_trailing_comment`
  then correctly reads ` #...` as a YAML comment — leaving
  `title: The`. The Claude-ingested copy in the live wiki has exactly
  the same damage, so this is not a grok regression and not new. Fix
  belongs in the ingest prompts (quote values needing it) plus a
  defensive quote in `obsidian_pass._serialize`; the already-damaged
  pages need re-titling by hand since the original text is gone.

---

## Track B — reliability (protects every demo, test, and customer)

### B1. Async job queue (kills the #1 failure class)

Replace blocking fetches with jobs: `POST /jobs {kind, params}` → id;
worker thread runs convert/ingest/studio subprocesses; `GET /jobs/<id>`
returns state + log tail; UI polls. The single-flight lock becomes a queue
(second ingest *queues* instead of being rejected). Stale-banner problem
becomes structurally impossible, and the UI can finally show real progress
("reading transcript 2/3…" from the stderr stream we already emit).

### B2. Render + server watchdogs — ◐ partly shipped 2026-08-05

**Shipped 2026-08-05 (Mac):** the server health-watchdog and the process-tree hard-timeout both landed. A `com.riverfed.watchdog` LaunchAgent probes `/healthz` every 5 min and `launchctl kickstart`s the server if it died (the launchd equivalent of the `start.vbs` Scheduled-Task line below), and `agent_runner.run()` now enforces a real wall-clock timeout that kills the whole process group on every agent run (ingest/review/studio), so a hung run can't pin the lane. **Still open:** the marp-specific ~3-min timeout + one-retry wrapper (the chromium-zombie guard).

**Update 2026-08-15:** the auto-ingest watcher is self-healing too — sweeps are interval-guarded and driven by both an in-process poll and the launchd watchdog's `/watcher/tick`, with sweep freshness on `/healthz`, so a stalled sweep thread can't silently stop ingest. The frames follow-up is now fixed: frame downloads retry three full yt-dlp extractions with fresh media URLs, a transcript saved without requested frames is surfaced as a warning with a retry action, and Codex receives tagged JPEGs through `codex exec --image` rather than filesystem access alone.

- Wrap every marp invocation with a hard timeout (\~3 min) + process-tree
  kill + one retry — the 125-minute chromium zombie can't recur.
- `start.vbs` → register a Scheduled Task (`onstart` + hourly health-probe
  `curl /healthz || restart`) so sleep/sign-out can't leave the site down.

### B3. Minimal CI (GitHub Actions) — ✅ shipped 2026-06-11

One workflow, <2 min: `py_compile` every script · `pending.py` against a
fixture · `design_tokens.py` + (new) `model_registry.py` parse all shipped
presets · wiki link-integrity scan (promote this session's inline checker to
`wiki/scripts/lint_links.py`) · `node --check landing/nav.js`. Protects the
two-collaborator flow — red X instead of a broken evening for whoever pulls.
*(Shipped as .github/workflows/ci.yml; pending.py runs against both
committed vaults and ingest.py --dry-run exercises model loading.)*

### B4. Whisper fallback (`GROQ_API_KEY`) — ✅ shipped 2026-06-11

The documented gap; cheap now, unblocks caption-less videos (several
near-misses already).
*(Shipped in convert.py: smallest audio stream → Groq
whisper-large-v3-turbo, auto-segmented past 24 MB; without the key
behavior is unchanged and the warning now points at the knob. Gate +
no-key path verified; first real transcription pending a GROQ\_API\_KEY
on this machine.)*

---

## Track C — launch readiness (added 2026-06-12)

The gap between "our private tool" and the hybrid launch. C1 is next
regardless of launch timing — it fixes a today-problem: two
collaborators share one product repo, so `sync.cmd` currently pulls
Joao's personal vaults onto Paulo's machine.

### C1. Vault/data split — ✅ shipped 2026-06-12

Today `wiki/` + `wikis/<slug>/` are tracked in the product repo: our
knowledge (including transcript-derived source pages we could never
publish) is welded to the code's git history. Split them:

- Vaults move to a **vault home outside the repo** (e.g.
  `~/RiverfedVaults/<slug>/`, overridable via env var). `_wikis.py` is
  the single resolution point, so the change is contained.
- Per-vault git (optional): a vault can be its own private repo —
  versioned knowledge stays versioned, in *your* repo, not the
  product's.
- One-shot migration script moves existing vaults out; the product repo
  keeps ONE demo vault (riverfed-ops — our own CONTRIBUTING.md,
  publishable).
- The public-history problem then solves itself at C4: we cut a fresh
  public repo from a clean tree, no history scrub needed.

**Verify**: a fresh clone contains no personal vaults; existing vaults
keep working from the vault home (convert → ingest → studio → /wiki);
CI green with only the demo vault.

**Shipped 2026-06-12**: vault home at `~/RiverfedVaults/` (override
`RIVERFED_VAULTS_DIR`, read from env then .env); resolution order home →
repo demo → home-as-scaffold-target; `display_path()` keeps repo vaults
rendering as before while home vaults go absolute; studio scripts take
absolute `--wiki` + `--add-dir` the vault; `/vault/page` serves pages
locally (OPEN MD + graph links — GitHub blob URLs couldn't reach
external vaults). `migrate_vaults.py` moved the wiki (110 pages +
staging + Obsidian config) and investing vaults out, each now its own
git repo. Verified live: scaffold→convert→REAL ingest→anki into a
vault-home test vault (agent read/write outside the repo), UI smoke on
all three vaults, traversal guards, CI green on the clean checkout —
the exit test exactly.

### C2. Runs-anywhere pass and local transcription: ✅ shipped 2026-07-27

The practical clean-Mac path is now real:

- `setup.sh` creates or reuses `.venv`, installs Python dependencies,
  creates `.env` only when missing, installs whisper.cpp 1.9.2 on macOS,
  downloads a checksum-pinned model into
  `~/Library/Caches/Riverfed/whisper.cpp`, and runs a local smoke
  transcription. A second run reuses the environment, binary, and
  verified model.
- The setup screen shows the model and exact download size before any
  fetch. `tiny` is the 75 MiB smoke default. The multilingual
  `large-v3-turbo-q5_0` production option is 547 MiB and must be chosen
  explicitly, so a large model never arrives by surprise.
- `convert.py` now recovers YouTube transcripts in this fixed order:
  every human caption track, every automatic track, every supported
  caption representation with one retry, local whisper.cpp, optional
  Groq when `GROQ_API_KEY` is present, then a clear rejection.
- Local transcripts keep segment timestamps, detected language,
  whisper.cpp version, model provenance, and the local-only privacy
  note. Transcript text is filtered out of job logs.
- The shared transcript guard runs before ingest. Timestamp labels
  cannot inflate the 1,200-word threshold.
- The server port can be isolated with `RIVERFED_PORT`, which lets a
  clean-clone validation run beside the normal local app.

**Recorded proof on the designated Apple Silicon Mac:**

- A clean clone ran `./setup.sh --whisper-model tiny`; the combined handoff
  branch passes the full 158-test suite plus a real YouTube conversion, a real
  Codex ingest, the Obsidian normalization pass, and the live `/wiki` route
  against a scratch vault. The ingest created one source and five entity pages
  without changing the immutable converted transcript.
- A 1,157-second public video was forced through local whisper.cpp with
  captions suppressed. The 75 MiB smoke model produced 486 timestamped
  segments in about 20.5 seconds of model compute, a real-time factor of
  about 0.018, and a 3,856-word spoken transcript that passed the guard.
  No Groq call was made.
- Regression coverage exercises human and automatic caption ordering,
  every supported URL and format, retry behavior, partial captions,
  local-before-remote fallback, total failure, checksum and atomic model
  setup, language and timestamp provenance, and the live forced-local
  path.

**Deliberately not claimed:** the 547 MiB production model was not
downloaded during this milestone, so its word-error rate, peak memory,
and quality threshold remain unmeasured. Airplane-mode replay and a
genuinely captionless public fixture also remain useful quality
hardening. They belong in the editor and ingest-quality milestone below,
not in a second bootstrap project.

### C3. Source review and ingest recovery loop: ◐ first slice shipped 2026-08-15

Editor workflow plus ingestion quality remains the current product milestone,
but its reliability foundation is no longer a stranded local candidate.

**Shipped first slice:** one canonical source-readiness scan now drives the
Knowledge queue, server preflight, and ingest selection. It reports source
type, transcript provenance, language, duration, word count, guard result, and
an actionable failure code. Failed captures cannot start ingest. Retry runs
the deterministic caption/audio recovery chain, keeps the original capture,
and chooses one usable revision per logical source. The transcript floor is
duration-aware, so complete short videos are not rejected by a long-form rule.
Deep visual recovery retries transient downloads and supplies tagged frames to
both Claude and Codex.

**Still open:**

- Add transcript review as a separate revision or correction layer.
  Preserve the immutable capture, show a diff, and record which revision
  was ingested.
- Make re-ingest explicit and safe: preview affected pages, preserve
  source links, and show the resulting knowledge-base diff.
- Turn the known transcript failures into a small regression corpus,
  including the production whisper model quality check, offline replay,
  captionless input, partial captions, rate limiting, bot detection, and
  missing-caption diagnostics.

**Exit test:** from the browser, a user can inspect a weak or failed
source, understand the exact reason, choose a recovery path, approve the
guarded transcript, ingest it, and see the source-to-wiki diff without
losing the original capture.

### Deferred: external SOPs-to-Skills pilot

The shipped SOPs-to-Skills model and compiler stay available. An
external company pilot is no longer a scheduled product milestone. It
starts only when a real consultancy or company opportunity exists. At
that point the pilot kit should add the offer definition, one external
dry run, the skill-eval delivery gate, and a concise demo. Until that
trigger, editor workflow and ingestion reliability take priority.

### C4. OSS launch cut — when we decide to go

Cut a **new public repo from a clean tree** (sidesteps private history
entirely): license choice, README-for-strangers, demo GIF/video — the
landing page already exists. **Shipped 2026-11-01:** public repo
`ipodvs/riverfed` cut from a clean tree under MIT, with every
identifier on the Riverfed name (`~/RiverfedVaults`,
`RIVERFED_*` env vars, `com.riverfed.*` LaunchAgents, the Whisper
cache dir). Still open: the TMview check, the domains, README-for-
strangers polish and the demo GIF/video. Launch content rides the
build-in-public material we already have.

**Verify**: a stranger with Claude Code installed reaches their first
converted video in under 10 minutes from the public README alone.

---

## Go further — beyond the original plan

Ranked by leverage-per-effort:

1. **Auto-ingest watcher (cron)** — ✅ shipped 2026-06-11. Watch chosen YouTube channels/playlists;
   new video → convert (+frames heuristic) → queue ingest → wiki grows while
   you sleep. Turns "tool I operate" into "knowledge that compounds on its
   own" — the product's own tagline — and it's the best live demo we could
   own. Builds directly on B1's job queue.
   \*(watcher.py + server sweep thread (WATCHER\_INTERVAL\_MIN, default 6 h)
   - "Watched channels" UI on /. Queue-for-approval default, per-channel
     auto-ingest + deep-capture flags, baseline-on-subscribe so no
     back-catalogue floods in. Verified live: a subscribed channel's video
     was discovered, converted unattended, and appeared as pending.)\*
2. **Skill eval hardening.** Run the skill-creator's eval/description-
   optimization loop on our 6 skills (we deferred it). Doubles as the QA
   harness for A3's *generated* skills — same grader, same evals.json.
3. **Anki + Notion generators.** The Studio's stated next generators; Anki
   especially is a natural "teach forever" fit and trivially demoable.
   *(Anki half ✅ shipped 2026-06-11 — studio\_anki.py: agent-authored
   atomic source-cited cards → genanki .apkg with stable ids, so
   re-generating updates the deck in Anki. First run: 28 concept cards
   through the live /studio/anki route. Notion still open.)*
4. **Staleness surfacing.** A "needs revisit" report (pages whose sources
   are old / contradicted by newer ingests). First step toward the wiki
   maintaining *itself*.
5. **Dead-CSS sweep + Lighthouse pass** on the 4 pages (the old inline
   `nav.top` styles are dead code now).

---

## Suggested sequence (each block ≈ one focused session)

| # | Block               | Contents                         | Exit test                                                                                    |
| - | ------------------- | -------------------------------- | -------------------------------------------------------------------------------------------- |
| 1 | **Stability first** | B1 + B2 (+ B5-trivial: dead CSS) | Kill the server mid-ingest → job resumes/reports; no stale banners; marp can't zombie        |
| 2 | **Foundation**      | A0 + B3                          | Fixture ingest byte-identical; CI green on a PR                                              |
| 3 | **Second paradigm** | A1 + A2                          | Create PARA base from UI → ingest → deck                                                     |
| 4 | **The wedge**       | A3 (+ eval harness #2)           | Fresh Claude session executes a *generated* skill                                            |
| 5 | **Compounding**     | Watcher #1 + B4 + Anki #3        | A subscribed channel's new video appears in the wiki unattended                              |
| 6 | **Adaptive UI**     | A5 model-adaptive /wiki          | Ops vault browsable as card sections (procedures/policies/runbooks); karpathy view unchanged |
| 7 | **Vault split** | C1 | A fresh clone has no personal vaults; vaults live + work outside the repo |
| 8 | **Bring your own agent** | A6 multi-provider runner — ✅ 2026-07-04 | ✅ Fixture ingested via Claude AND Codex into scratch vaults; both schema-valid + lint clean |
| 9 | **Runs anywhere** | C2 local speech-to-text and bootstrap: ✅ 2026-07-27 | ✅ Clean Mac clone, idempotent setup, forced local transcript, real convert and Codex ingest, live wiki |
| 10 | **Review and recover** | C3 source editor and ingest quality — ◐ readiness/retry slice shipped 2026-08-15 | Inspect failure, choose recovery, approve transcript, ingest, and review the wiki diff |
| 11 | **Launch cut** | C4 (when ready) | Stranger → first converted video in <10 min; name resolved (Riverfed ✅ 2026-11-01) |
| 12 | **Third agent** | A7 Grok CLI provider — ✅ 2026-08-15 | ✅ 13-frame fixture ingested via Grok into a scratch vault (271 s) — schema-valid, lint clean, frame citations present |

Blocks 1-9 ✅ shipped (1-6 on 2026-06-11; Block 7 = C1 on
2026-06-12; Block 8 = A6 on 2026-07-04; Block 9 = C2 on
2026-07-27; Block 12 = A7 on 2026-08-15, merged onto current main
2026-09-27). In progress: **Block 10 = source review and ingest recovery**;
readiness diagnostics, guarded retry, revision selection, and visual recovery
are shipped, while reviewed transcript revisions and source-to-wiki diff
approval remain.
The external SOPs-to-Skills pilot is opportunity-triggered and has no
place in the scheduled sequence. **A4 interop dropped off the
critical path** since 2026-06-12; its first Riverfed → Writer snapshot bridge
shipped on demand on 2026-08-24. Schedule broader interop only when another
real cross-model need appears.

Block 1 before Block 2 deliberately: the refactor (A0) involves lots of
ingest test-runs, and doing those on top of the async queue + watchdogs
makes every later block faster and calmer.

## Decisions needed from us two (before their block starts)

1. **Promotion knob defaults** (Block 2): concepts ≥3 / entities ≥2 as
   default — agree or loosen?
2. **Manifest format** (Block 2): markdown + YAML front-matter, same as
   design.md — any objection?
3. **Watcher scope** (Block 5): which channels first, and ingest auto or
   queue-for-approval?
   *(Resolved 2026-06-11 with the safe default: queue-for-approval, with a
   per-channel auto-ingest toggle in the UI — so the channel list and the
   auto decision are yours to make per-base, not hardcoded. Subscribe from
   the "Watched channels" section on /.)*
4. **Packaging & GTM** (decided 2026-06-12): stay private for now;
   destination hybrid (OSS distribution + SMB pilot revenue); hosted
   SaaS deferred until evidence; name kept until traction (re-opens at
   C4 / first paid pilot). Full reasoning in "Strategy decision" at the
   top of this doc.
