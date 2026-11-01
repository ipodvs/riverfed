---
version: alpha
name: Karpathy Wiki
description: >
  Three-layer teach-back knowledge base — immutable raw sources distilled
  into an LLM-curated wiki of sources, topics, entities, and concepts,
  governed by an explicit schema. The original Riverfed model.
folders:
  sources:
    kind: source
    role: one page per ingested transcript or file
    capture: true
    label_field: title
  topics:
    kind: topic
    role: subject areas synthesized across multiple sources
    promote_after: 2
    weight: { min: 2 }
    card: { description: What it is, callout: Why it matters }
  entities:
    kind: entity
    role: canonical pages for recurring tools, products, people, formats
    promote_after: 2
  concepts:
    kind: concept
    role: cross-cutting themes and recurring patterns that span topics
    promote_after: 3
    weight: { min: 3, bonus: 2 }
    card: { description: What it is, callout: Why it matters }
links:
  in-topic: { from: source, field: topics, to: topic }
  mentions: { from: source, field: entities, to: entity }
  evidenced-by: { from: concept, field: sources, to: source }
  spans-topic: { from: concept, field: related_topics, to: topic }
generators: marp, pptx, diagram, guide
search_hint: topics, sources, tools, people, ideas
bases:
  promotion-health: { title: Promotion health }
  capture-log: { title: Capture log }
---

# Karpathy Wiki — knowledge model manifest

The model behind the original Riverfed wiki: Karpathy's three-layer
pattern (raw sources → curated wiki → schema), expressed as a manifest so
the pipeline and the UIs read the layout instead of hardcoding it.

## What the front matter drives

- **`folders`** — the page folders a vault of this model contains. Each
  declares its node `kind` (used by the `/wiki` graph + data UIs), an
  optional `label_field` (frontmatter field used as the node label —
  sources label by `title`), and an optional `weight` rule for graph node
  sizing: `weight = max(min, source_count + bonus)`; folders without a
  `weight` rule render at weight 1.
- **`promote_after`** — the promotion knob (reliability debt #4): how many
  sources of evidence a candidate needs before the agent creates a page.
  Topics promote on the 2nd source, entities on the 2nd, concepts on the
  3rd (concepts are fuzzier; the higher bar keeps them meaningful). The
  ingest + promotion prompts interpolate these numbers — the prompt states
  the *actual* rule, not folklore.
- **`links`** — graph edges, read from page frontmatter: each entry maps
  `from` kind through a frontmatter list `field` to a `to` kind. The edge
  name is the entry key (shows up as the link `kind` in `/wiki/graph`).
- **`card`** — marks a folder browsable in the `/wiki` MAP view and names
  the `## section`s its cards surface (`description` + optional
  `callout`). Folders without a `card` (entities here) appear in the
  graph but not as MAP sections. `card: {}` = browsable with the generic
  lead-paragraph card.
- **`search_hint`** — the `/wiki` search-box placeholder copy (rendered
  as "Search " + hint); falls back to the browsable folder names.
- **`bases`** — the Obsidian Bases (`.base` view files) each vault of this
  model gets, emitted by `wiki/scripts/base_gen.py` during `obsidian_pass`
  and at scaffold time. Each key names a template in `bases/` and the file
  written to the vault root; the value holds per-base knobs (`title`). The
  view YAML lives in the template rather than here because a Base's
  `views:` is a block list, which this front-matter dialect cannot express.
  Bases are a LENS over the vault, never a source of truth — the `/wiki`
  browser route stays the product surface.
- **`generators`** — which Studio generators make sense for vaults of this
  model (gating arrives with the model picker; informational for now).

## Files in this directory

| File | Role |
|---|---|
| `model.md` | This manifest |
| `SCHEMA.md` | Canonical schema template — copied into each new vault at scaffold time |
| `ingest-prompt.md` | Per-transcript ingest prompt template (`wiki/scripts/ingest.py`) |
| `promote-prompt.md` | Backlog-promotion prompt template (`wiki/scripts/promote_backlog.py`) |

Prompt templates are `str.format` templates: `{wiki_rel}`, `{output_rel}`,
`{transcript_name}`, `{wiki_slug}` come from the vault being ingested;
`{topic_promote_after}`, `{entity_promote_after}`, `{concept_promote_after}`
come from this manifest's `promote_after` knobs.

Parsed by [`wiki/scripts/model_registry.py`](../../wiki/scripts/model_registry.py)
(same front-matter dialect as the design presets — scalars, nested
mappings, `{ inline: mappings }`, `>` folded scalars; no block lists).
