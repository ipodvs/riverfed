# Riverfed → Multi-Paradigm Knowledge Platform

**Status: design doc for review.** No code yet — this captures the
architecture and a phased roadmap so we can agree on direction before
building. **PFreitas91 — add your thoughts inline / in a follow-up
commit; nothing here is locked.**

## Context

Riverfed started as a YouTube/file → markdown converter, then
grew a Karpathy-style wiki (sources / topics / entities / concepts) and
a Studio that turns the wiki into teaching material (Marp, native PPTX,
Excalidraw, speaker manuals) — all now styled by a customizable
**design picker**.

The realization driving this doc: **the app has become a general
knowledge-gathering engine**, and the Karpathy wiki is only *one* way to
organize knowledge. Different paradigms suit different jobs:

- **Second Brain / PARA** → actionable personal knowledge, email/task capture
- **Business SOPs → agent skills** → turn company ops into agent-executable skills
- **Zettelkasten** → research & writing
- **Karpathy wiki** (have) → distilling consumed content into teachable knowledge

The opportunity is two-sided:
- **Personal**: broaden who the tool serves (knowledge workers, researchers).
- **B2B**: a *"knowledge → agent" transfer tool* — drop a company's
  docs/recordings, get a skill library + context files their agents can run.
  This is the differentiated, sellable wedge.

**Two guiding principles** (from the brainstorm):
1. *"All needs to work together better — think as a whole."* Models
   shouldn't be siloed wikis; they're lenses over a shared knowledge
   substrate that can cross-pollinate.
2. *"We give those as templates and they can do their own ideas."*
   Ship paradigms as **editable templates**; users fork/customize/create
   their own — exactly the pattern the design picker already proves.

## The core idea: knowledge models as templates (mirror the design picker)

We just shipped `designs/` — ship a few palette/typography templates,
let users edit them in a modal or create their own (`designs/custom/`),
and the chosen design flows into every generator. **Do the same for
knowledge structure.**

Two-axis product:

```
   Knowledge MODEL  ×  DESIGN
   (how knowledge is        (how output
    captured + organized)    looks)
        │                        │
        ▼                        ▼
   ingest + folders         generators
        └────────┬───────────────┘
                 ▼
        wiki → decks / skills / diagrams
```

- **Model picker** (new): choose Karpathy / Second Brain / SOPs→Skills /
  Zettelkasten / your own — when you create a knowledge base.
- **Design picker** (have): choose the visual identity for generated output.

## North star: one substrate, many lenses

The "think as a whole" principle. Two architectures to weigh:

- **A — Separate wikis per model** (simpler, ship-first): each knowledge
  base is a folder with its own model + SCHEMA. You pick a model at
  creation. `list_wikis()` already discovers any folder with
  `index.md` + `SCHEMA.md`, so this is the low-friction path.
- **B — Shared substrate, multiple projections** (north star): the raw
  `output/` source pool is shared; each model is a different organizing
  *view* over the same underlying knowledge; cross-model wikilinks let a
  personal Second Brain note reference a business SOP. Richer, but more
  design work (cross-model linking, a meta-index, dedup across models).

**Recommended path: start at A, evolve toward B.** Ship model-as-template
(per-wiki) first; add cross-model interop + a unified index once 2-3
models exist and the interop patterns are real rather than speculative.

## The "knowledge model" abstraction

A model is a small manifest, stored like a design — **shipped templates
in `models/`, user copies in `models/custom/` (gitignored)**:

```
models/
├── karpathy-wiki/
│   ├── model.md           manifest: folders, node types, promotion rules
│   ├── SCHEMA.md          the per-model schema (today's wiki/SCHEMA.md)
│   └── ingest-prompt.md   the ingest instructions for THIS model
├── second-brain/
├── sops-to-skills/
├── zettelkasten/
└── custom/                user-created (gitignored, like designs/custom/)
```

`model.md` front matter (parallels `design.md`):

```yaml
name: Second Brain (PARA)
description: Actionable personal knowledge — Projects, Areas, Resources, Archives.
folders:
  projects:  { node_kind: project,  promote_after: 1 }
  areas:     { node_kind: area,     promote_after: 1 }
  resources: { node_kind: resource, promote_after: 2 }
  archives:  { node_kind: archive }
link_fields: [projects, areas, resources]   # frontmatter keys that form graph edges
generators: [marp, pptx, diagram]            # which Studio outputs make sense
```

A new `wiki/scripts/model_registry.py` (sibling of `design_tokens.py`)
loads these — `load_model(path)`, `list_models(root)`, `save_model(...)`
— so the same picker/edit/reset/create UX from the design system applies.

## Paradigm catalog (templates to ship)

| Model | Folders | Best for | Buyer | Output emphasis |
|---|---|---|---|---|
| **Karpathy wiki** (have) | sources · topics · entities · concepts | distilling consumed content into teachable knowledge | learners, creators | decks, manuals (human) |
| **Second Brain / PARA** | projects · areas · resources · archives | actionable personal knowledge; email/task capture | knowledge workers | summaries, action lists (human) |
| **SOPs → Agent Skills** | procedures · policies · runbooks → `.claude/skills/*.md` | company ops → agent-executable skills | **businesses (B2B)** | **skills + context files (agent)** |
| **Zettelkasten** | flat atomic notes + dense bidirectional links | research, writing, idea development | researchers, writers | essays, outlines (human) |
| **Decision log / ADR** | decisions + context + consequences | engineering/operating memory | eng & ops teams | decision records (human/agent) |

The SOPs→Skills model is the only one whose primary output is
**agent-facing** — it needs a new generator (`studio_skills.py`) that
emits `.claude/skills/<name>.md` SOPs + an `agents.md` context file,
rather than a deck. That's the B2B differentiator.

## Coupling reality (grounding for the build — verified by exploration)

| Layer | Coupled to Karpathy? | Work to generalize |
|---|---|---|
| Studio generators (marp/pptx/diagram/guide) | ❌ No — take `--wiki <slug>`, tell Claude "read the wiki at `{wiki}/`" | none — model-agnostic already |
| `list_wikis()` discovery | ⚠️ Mostly no | folder-count display hardcodes the 4 names — read from model manifest |
| Ingest prompt (`ingest.py`) | ✅ Yes — ~100 lines hardcode the 4 folders; does NOT read SCHEMA dynamically | load the model's `ingest-prompt.md` instead of the hardcoded template |
| Ingest target | ✅ Yes — hardcoded to `wiki/`; `/ingest` has no wiki param | parameterize `ingest.py` + `pending.py` + `/ingest` by wiki slug |
| Graph view (`build_wiki_graph`) | ✅ Yes — 4 hardcoded folder loops + node-kind logic | read node types + link fields from model manifest |
| Scaffolding | None — wikis hand-created | add "create knowledge base from model" scaffolder |

**Bottom line: generation is already pluggable; ingest + graph + scaffolding are the real work.**

## Phased roadmap (sequence later — both tracks captured)

- **Phase 0 — Foundation.** `models/` registry + `model_registry.py`
  loader. Parameterize `ingest.py`, `pending.py`, and the `/ingest`
  route by wiki slug. Make `list_wikis()` + `build_wiki_graph()` read
  folder/node definitions from the model manifest. Convert today's
  `wiki/SCHEMA.md` + ingest prompt into the `karpathy-wiki` model (no
  behavior change — pure refactor to prove the abstraction).
- **Phase 1 — Scaffolder + model picker UI.** "Create a knowledge base"
  flow: pick a model template → scaffold folders + SCHEMA + index.md.
  Model picker + editor (clone the design-picker modal: edit/reset/create).
- **Phase 2 — Second Brain (personal track).** Ship the PARA template +
  ingest prompt. Closest cousin to the wiki; validates the abstraction
  on a real second model.
- **Phase 3 — SOPs → Skills (B2B wedge).** Ship the model + a new
  `studio_skills.py` generator that emits `.claude/skills/*.md` +
  `agents.md`. This is the sellable "knowledge → agent" story.
- **Phase 4 — Interop ("think as a whole").** Cross-model wikilinks, a
  unified meta-index across knowledge bases, shared `output/` substrate
  so one source can feed multiple models.
- **Phase 5 — Long tail.** Zettelkasten, ADR templates; polish the
  custom-model editor; per-model generator gating.

## B2B track notes (for later)

- SOPs→Skills output is agent-facing: `.claude/skills/*.md`, `agents.md`,
  runbooks. The pitch: *"drop your Notion/Drive/recordings → get a skill
  library your agents run."*
- Future considerations (not Phase 3): multi-tenancy, redaction/privacy
  pass on ingested company docs, packaging skills for deployment to a
  client's agent fleet. There's prior art for redaction rules in the
  repo's `Codex Personal Assistance/REDACTION_RULES.md`.

## Personal track notes (for later)

- Second Brain + Zettelkasten broaden the personal market.
- Second Brain pairs naturally with the existing converter (drop an
  email export / meeting note → PARA capture).

## Open design questions (resolve at implementation time)

1. **Manifest format** — markdown + YAML front matter (like `design.md`),
   or pure YAML? Leaning markdown-front-matter for consistency with the
   design system + human-readable rationale below the tokens.
2. **Substrate sharing** — do all models share one `output/` pool, or
   does each knowledge base fork its own? (Decides Phase 4 difficulty.)
3. **Cross-model linking** — wikilink syntax across knowledge bases, and
   how the graph view renders multi-model edges.
4. **Promotion rules** — keep them per-model-configurable in the manifest
   (`promote_after: N`) vs hardcoded thresholds.
5. **Generator gating** — should a model declare which Studio generators
   apply (e.g. SOPs→Skills hides "Marp deck", shows "Skill library")?

## Critical files (when implementation begins)

- `wiki/scripts/ingest.py` — parameterize target wiki + load per-model ingest prompt
- `wiki/scripts/pending.py` — parameterize the sources dir by wiki slug
- `server.py` — `/ingest` wiki param; `list_wikis()` + `build_wiki_data()`
  + `build_wiki_graph()` read model manifest; new scaffolder + model-registry endpoints
- `wiki/SCHEMA.md` — migrate into `models/karpathy-wiki/SCHEMA.md`
- **NEW** `models/` directory + `wiki/scripts/model_registry.py` (mirror `design_tokens.py`)
- **NEW** `wiki/scripts/studio_skills.py` — the SOPs→skills generator (Phase 3)
- `landing/index.html` + `landing/studio.html` — model picker UI (clone the design-picker modal)
- `CLAUDE.md`, `README.md`, `CHANGELOG.md`, a new `models/README.md` — docs

## Reuse (don't reinvent)

- **Design-picker pattern** (`designs/` + `design_tokens.py` + the
  studio.html modal + the `/api/designs` CRUD endpoints) is the exact
  template for the model picker. Clone its structure: ship templates,
  `*/custom/` for user copies (gitignored), edit/reset/create modal,
  CRUD endpoints with a path-traversal-guarded id regex.
- **`_claude_bin.resolve_claude_bin()`** — any new script that shells to
  `claude` must use this (Windows `.CMD` resolution).
- **Atomic-swap + `--tmp` pattern** from `build_handbook_pptx.py` for any
  file a user might have open.

## Verification (per phase, when built)

- **Phase 0**: run the existing handbook ingest after the refactor →
  identical wiki output (pure refactor, no behavior change). `ingest.py
  --dry-run` still works; `/wiki` graph renders unchanged.
- **Phase 1**: scaffold a new empty knowledge base from a template via
  the UI → folders + SCHEMA + index.md appear; it shows in `list_wikis()`.
- **Phase 2**: ingest a sample into a Second Brain base → PARA folders
  populate; generators read it and produce a deck.
- **Phase 3**: ingest a sample SOP doc → `studio_skills.py` emits a
  `.claude/skills/<name>.md` that a fresh Claude Code session can load
  and execute end-to-end.
- **Phase 4**: a source ingested once surfaces in two models; a
  cross-model wikilink resolves in the graph view.

## Recommended starting point (for discussion)

Phase 0 → Phase 2 (personal, Second Brain) to prove the abstraction on a
real second model, then **Phase 3 (SOPs → Skills) as the headline B2B
feature** once the plumbing is solid. Phase 4 interop is the long-game
differentiator but shouldn't block shipping the first two models.

**Open for the brother's input**: which paradigm matters most to start,
whether to chase the B2B wedge sooner, and the substrate-sharing call
(open question #2) — it's the biggest architectural fork.
