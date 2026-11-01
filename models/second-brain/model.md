---
version: alpha
name: Second Brain (PARA)
description: >
  Tiago Forte's PARA method as a knowledge base — capture notes distilled
  toward ACTION, not teach-back. Sources are captured 1:1, then organized
  into Projects (active, outcome-driven), Areas (ongoing responsibilities),
  and Resources (reference interests), with Archives for what went inactive.
folders:
  sources:
    kind: source
    role: capture layer — one note per ingested transcript or file
    capture: true
    label_field: title
  projects:
    kind: project
    role: active efforts with a concrete outcome and an end in sight
    promote_after: 1
    weight: { min: 3, bonus: 1 }
    card: { description: Outcome, callout: Status & next actions }
  areas:
    kind: area
    role: ongoing responsibilities with a standard to maintain
    promote_after: 2
    weight: { min: 3 }
    card: { description: The standard, callout: Current focus }
  resources:
    kind: resource
    role: reference notes on topics of ongoing interest
    promote_after: 2
    weight: { min: 2 }
    card: { description: What this collects }
  archives:
    kind: archive
    role: parked projects, areas, and resources — inactive but kept
    card: {}
links:
  in-project: { from: source, field: projects, to: project }
  in-area: { from: source, field: areas, to: area }
  in-resource: { from: source, field: resources, to: resource }
  supports: { from: project, field: resources, to: resource }
generators: marp, pptx, diagram, guide
search_hint: projects, areas, resources, archives
bases:
  para-dashboard: { title: PARA dashboard }
  weekly-review: { title: Weekly review }
---

# Second Brain (PARA) — knowledge model manifest

The second shipped knowledge model, and the proof that the registry
abstraction works: same pipeline, same converter, same generators — a
completely different organizing principle.

## How PARA differs from the karpathy-wiki model

| | karpathy-wiki | second-brain |
|---|---|---|
| Organizing question | "What subject is this about?" | "How actionable is this?" |
| Ingest stance | teach-back (summarize to teach) | capture → next action |
| Mid layers | topics / entities / concepts | projects / areas / resources |
| Promotion | evidence count across sources | actionability (projects promote on a single strong source) |
| Park/retire | n/a | archives/ |

## What the front matter drives

- **`capture: true`** on `sources` — the capture layer holds one note per
  ingested transcript; pending-detection keys on it (same mechanic as the
  karpathy model).
- **`promote_after`** — projects promote at 1 (a single source describing
  a concrete actionable effort is enough to open a project page); areas
  and resources need 2 sources of evidence before a page exists. Below
  the bar, candidates live in the capture note + the index's Inbox.
- **`links`** — capture notes link up via frontmatter (`projects:`,
  `areas:`, `resources:` lists); project pages cite supporting resources
  via `resources:`. Archives deliberately have no automatic links.

## Files in this directory

| File | Role |
|---|---|
| `model.md` | This manifest |
| `SCHEMA.md` | Canonical PARA conventions — copied into each new vault at scaffold time |
| `ingest-prompt.md` | Per-transcript capture prompt (`wiki/scripts/ingest.py`) |
| `promote-prompt.md` | Inbox-promotion prompt (`wiki/scripts/promote_backlog.py`) |

Prompt placeholders: `{wiki_rel}`, `{output_rel}`, `{transcript_name}`,
`{wiki_slug}` from the vault; `{project_promote_after}`,
`{area_promote_after}`, `{resource_promote_after}` from this manifest.
