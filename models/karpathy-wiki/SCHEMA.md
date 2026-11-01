---
title: Wiki schema
purpose: rules and conventions for this LLM-curated knowledge base
last_updated: 2026-05-11
tags: [wiki]
---

# Wiki schema

This wiki is built using the **three-layer model from Karpathy's
[knowledge-base gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)**:

1. **Raw sources** — the YouTube transcripts and converted files in
   `../output/`. Treated as **immutable**: the wiki references them but never
   edits them.
2. **The wiki** — the markdown files in this folder. **LLM-curated**:
   summaries, cross-links, indexes. Rewritten freely.
3. **The schema** — this file. Defines the conventions below.

An agent (Claude Code or similar) reads sources, writes summaries to
`sources/`, updates `topics/` and `entities/` pages with new cross-references,
appends to `log.md`, and refreshes `index.md` on every ingest.

## Folder layout

```
wiki/
├── SCHEMA.md         # this file — conventions
├── index.md          # entry point: catalog of everything with one-line summaries
├── log.md            # append-only record of ingests, queries, lint passes
├── sources/          # one page per ingested source (1:1 with output/*.md)
├── topics/           # subject pages — synthesize across multiple sources
├── entities/         # canonical pages for recurring tools, products, people
└── concepts/         # cross-cutting themes/patterns that span topics
```

## Page conventions

### sources/<slug>.md

One file per raw source. The file is built once at ingest and edited only when
the source itself changes (rare). Mandatory sections:

```markdown
---
slug: kebab-case-of-the-title
source_file: ../output/<original-filename>.md
url: https://www.youtube.com/watch?v=...
title: ...
channel: ...
duration: HH:MM:SS
published: YYYY-MM-DD
topics: [topic1, topic2]
entities: [entity1, entity2]
ingested: YYYY-MM-DD
---

# <Title>

## TL;DR
2-4 sentences. The single most useful summary of the source.

## Top takeaways
1. ...
2. ...
3. ...

## Key concepts
- bullets, ≤12 words each

## Entities mentioned
Links to entities/*.md when a page exists, plain text otherwise.

## Quotes
> "verbatim line"

## See also
- [Topic page](../topics/...)
- [Related source](./...)
```

### topics/<slug>.md

A topic is a **subject that spans 2+ sources**. Single-source subjects stay
in the source page only — promote to a topic page once a second source covers
it. Structure:

```markdown
---
slug: ...
last_updated: YYYY-MM-DD
sources: [list of source slugs that touch this topic]
---

# <Topic name>

## What it is
2-3 sentences defining the topic in plain language.

## Why it matters
Why anyone studying this would care. 1-2 sentences.

## Core ideas
Synthesized across sources. Cite the source in parentheses, e.g. (karpathys-autoresearch).

## Patterns and recipes
Specific reusable practices found in the sources.

## Open questions
Things the sources disagree on or don't answer.

## Sources
Bullet list with links to sources/*.md.
```

### concepts/<slug>.md

A page for a **cross-cutting theme or recurring pattern** that does not fit
neatly inside any single topic — it shows up across multiple topics. Promote
on the **3rd source** that explicitly names the same idea (lower bar than
topics because concepts are inherently fuzzier and we want them to surface).

Examples we should expect: *"terminal as the interface of work"*,
*"markdown files are the oxygen of LLMs"*, *"CEO = promoter, not builder"*,
*"opportunity cost vs token cost"*, *"agent-friendly websites / agents as
traffic"*, *"memory failures are write failures"*, *"skills as thinking
tools"*.

Difference vs topics: a topic is a **domain** (`ai-marketing`,
`agent-architecture`). A concept is a **stance/idea/pattern** that recurs
across domains. Pages structure mirrors topic pages:

```markdown
---
slug: ...
kind: concept           # always "concept" for concepts/*.md
last_updated: YYYY-MM-DD
sources: [...]          # every source that named this concept
related_topics: [...]   # topic slugs the concept touches
---

# <Concept name>

## What it is
2-3 sentences. The plain-language statement of the idea.

## Why it matters
The leverage. Why an agent should know this.

## Evidence across sources
Per-source bullets — exactly how each source frames the same idea.
Cite source slugs in parentheses.

## How to apply it
Recipes or practices that follow from the concept.

## Open questions
Where the sources disagree, or what's unresolved.

## Sources
- [[source-slug]]
```

### entities/<slug>.md

A canonical page for a recurring **tool, product, person, or format** that
appears in ≥2 sources, or that warrants its own page on its own merit
(e.g. Claude Code).

```markdown
---
slug: ...
kind: tool | product | person | concept | format
last_updated: YYYY-MM-DD
sources: [...]
---

# <Entity name>

## What it is
1-2 sentences.

## Mentions
Per-source notes, ≤3 bullets per source.

## Related entities
Cross-links.
```

## Naming rules

- **kebab-case** for all filenames and slugs.
- **No dates** in filenames — frontmatter holds dates.
- **Singular nouns** for entities (`claude-code.md`, not `claude-codes.md`).
- **Topic slugs** are descriptive, not category labels: `agent-architecture.md`
  not `category-2.md`.

## Cross-linking rules (Obsidian-native)

This vault uses **Obsidian wikilinks**. Use `[[slug]]` (or `[[slug|display]]`
when the display differs from the slug). Slugs are unique across the wiki, so
you do **not** need to qualify with a folder.

Examples:
- `[[ai-agents]]` — link to the topic page (Obsidian resolves by stem)
- `[[claude-code|Claude Code]]` — link with custom display text
- `[[karpathys-autoresearch#TL;DR]]` — link to a heading inside another page

Rules:
- Internal links: **always wikilinks**, never relative markdown links.
- External links (`https://…`): standard markdown `[text](url)`.
- Link the **first occurrence** of each entity per page only.
- A topic page **must** link every source it lists; a source page **should**
  link every topic and entity it mentions.

The script `scripts/obsidian_pass.py` converts any straggler markdown links
to wikilinks, populates `tags:`, and adds `aliases:` to entity pages. It is
idempotent — safe to re-run.

## Frontmatter conventions

Every page has YAML frontmatter. Standard fields (see per-page templates
below for required fields):

- **slug** — kebab-case identifier, must match the filename stem
- **tags** — Obsidian-style tags. Auto-populated by `obsidian_pass.py` from
  `topics:` + `entities:` + (for entities) `kind/<kind>` + the page-class
  tag (`wiki/sources`, `wiki/topics`, `wiki/entities`)
- **aliases** — (entities only) alternative names this page is known by,
  e.g. `[Claude Code, claude code]`. Lets `[[Claude Code]]` resolve.
- **last_updated** — ISO date

The legacy `topics:` and `entities:` arrays remain for human readability and
machine queries; `tags:` is the field Obsidian indexes for the tag pane and
graph view.

## Linting (run periodically)

Ask the agent to:

1. **Orphans** — sources/topics/entities with no inbound links.
2. **Dead links** — broken relative paths.
3. **Stale claims** — facts that may have changed since ingest date.
4. **Missing cross-refs** — entities mentioned but not linked.
5. **Schema drift** — pages missing required frontmatter fields.

## Operations

| Operation | Trigger                          | What changes                                  |
|-----------|----------------------------------|-----------------------------------------------|
| Ingest    | new file in `../output/`         | new `sources/` page, updated `topics/` and `entities/`, `index.md`, `log.md` append |
| Query     | user asks a question             | no writes; agent reads relevant pages and answers |
| Lint      | manual, weekly                   | possibly rewrites pages to fix issues; logs findings |

## Controlled vocabulary

Topics should be drawn from this list (extend with care):

`ai-agents`, `ai-coding-tools`, `ai-marketing`, `agent-architecture`,
`autoresearch`, `business-operations`, `claude-code`, `codex`, `design-md`,
`knowledge-management`, `prompt-engineering`, `taste-and-creativity`,
`music`, `meme-culture`.
