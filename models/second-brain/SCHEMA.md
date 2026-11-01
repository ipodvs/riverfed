---
title: Second Brain schema (PARA)
purpose: rules and conventions for this PARA-method knowledge base
last_updated: 2026-06-11
tags: [wiki]
---

# Second Brain schema (PARA)

This knowledge base follows **Tiago Forte's PARA method**: organize by
**actionability**, not by subject. The question for every piece of
information is not "what is this about?" but "**what is this for, and how
soon will I act on it?**"

Three layers, same as every base in this app:

1. **Raw sources** — the transcripts and converted files in `../output/`
   (or this vault's own `output/`). **Immutable**: referenced, never edited.
2. **The base** — the markdown pages in this folder. **LLM-curated**:
   capture notes, project/area/resource pages, indexes. Rewritten freely.
3. **The schema** — this file.

## Folder layout

```
<vault>/
├── SCHEMA.md         # this file — conventions
├── index.md          # entry point: Projects / Areas / Resources / Archives / Inbox
├── log.md            # append-only record of captures, promotions, archive moves
├── sources/          # CAPTURE layer — one note per ingested source (1:1 with output/*.md)
├── projects/         # active efforts with a concrete OUTCOME and an end in sight
├── areas/            # ongoing responsibilities with a STANDARD to maintain
├── resources/        # reference notes on topics of ongoing interest
└── archives/         # parked projects/areas/resources — inactive but kept
```

**The actionability ladder** (most → least): a *project* has an outcome
and a deadline-ish end; an *area* never ends, it has a standard you
maintain; a *resource* is interest/reference material; an *archive* is
anything that went inactive. Information moves DOWN the ladder over time
(project ships → archive) and UP when life changes (resource → project
when you commit to act).

## Page conventions

### sources/<slug>.md — capture note

One file per raw source, written at ingest. Capture for **action**, not
summary-for-its-own-sake. Mandatory sections:

```markdown
---
slug: kebab-case-of-the-title
source_file: ../output/<original-filename>.md
url: https://...            # when the source has one
title: ...
channel: ...                # or author/origin
ingested: YYYY-MM-DD
projects: [project-slugs this source advances]
areas: [area-slugs this source informs]
resources: [resource-slugs this source feeds]
---

# <Title>

## TL;DR
2-3 sentences. What this source is and why it entered the system.

## Actionable takeaways
Numbered. Each one states a thing you could DO, not a fact you could know.

## Tasks & ideas extracted
- [ ] checkbox bullets for concrete next actions the source suggests
- Idea bullets for things worth considering later

## Worth keeping
The reference-grade facts/quotes/numbers — the part a future you would
search for.

## Filed under
Links to the project/area/resource pages this capture feeds.
```

### projects/<slug>.md

A **project** = an active effort with a concrete outcome and an end in
sight. Promote on the **first source** that clearly describes an
actionable effort you (or the vault owner) are committed to — a single
strong source is enough; below that bar it stays an Inbox candidate.

```markdown
---
slug: ...
kind: project
status: active            # active | waiting | done (done → move to archives/)
outcome: one line — what "done" looks like
last_updated: YYYY-MM-DD
sources: [capture-note slugs that feed this project]
resources: [resource slugs this project draws on]
---

# <Project name>

## Outcome
What will exist when this is done. 1-2 sentences.

## Status & next actions
- [ ] the immediate next physical/visible action
- [ ] then-what

## Notes from sources
Per-source bullets — what each capture contributed. Cite slugs in
parentheses.

## Log
- YYYY-MM-DD — what moved
```

### areas/<slug>.md

An **area** = an ongoing responsibility with a standard to maintain
(health, finances, team, brand…). No end date. Promote once **2 sources**
inform the same responsibility.

```markdown
---
slug: ...
kind: area
standard: one line — the bar this area is held to
last_updated: YYYY-MM-DD
sources: [...]
---

# <Area name>

## The standard
What "maintained" looks like.

## Current focus
What's getting attention this season, and why.

## Principles & practices
Synthesized across sources, cited in parentheses.

## Watch items
Early signals that the standard is slipping.
```

### resources/<slug>.md

A **resource** = a topic of ongoing interest or a reference collection.
Promote once **2 sources** feed the same interest. The PARA sibling of a
karpathy "topic", but organized for retrieval-when-acting rather than
teaching.

```markdown
---
slug: ...
kind: resource
last_updated: YYYY-MM-DD
sources: [...]
---

# <Resource name>

## What this collects
1-2 sentences.

## Key notes
The distilled reference material, grouped however serves retrieval.
Cite source slugs in parentheses.

## Pointers
External links, tools, people worth returning to.
```

### archives/<slug>.md

A parked page. Created by **moving** a project/area/resource here when it
goes inactive — keep the original frontmatter, add:

```markdown
archived: YYYY-MM-DD
archived_from: projects     # or areas / resources
archive_reason: one line
```

Never create archive pages directly at ingest. The ingest agent does not
archive; humans (or a periodic review) do.

## Naming rules

- **kebab-case** for all filenames and slugs. **No dates** in filenames.
- Project slugs name the OUTCOME, not the activity: `launch-riverfed-beta`,
  not `marketing-stuff`.
- Area slugs are nouns of responsibility: `personal-finance`, `team-health`.
- Resource slugs are subjects: `ai-coding-tools`, `index-investing`.

## Cross-linking rules (Obsidian-native)

Identical to every base in this app: internal references are **always
wikilinks** — `[[slug]]` or `[[slug|display]]`; external links are
standard markdown `[text](url)`. Slugs are unique across the vault, so no
folder qualification. Link the first occurrence per page. A project page
**must** link every capture note in its `sources:`; a capture note
**should** link every P/A/R page it feeds.

The script `scripts/obsidian_pass.py` converts straggler markdown links
to wikilinks and populates `tags:`. Idempotent — safe to re-run.

## Frontmatter conventions

- **slug** — kebab-case identifier, must match the filename stem
- **kind** — project | area | resource | archive (capture notes omit it)
- **status** — projects only: active | waiting | done
- **tags** — auto-populated by `obsidian_pass.py` (page-class tag
  `wiki/<folder>` + the frontmatter list fields)
- **last_updated** — ISO date

## Promotion rules (the Inbox)

Candidates that don't meet a bar yet live in two places: the capture
note itself, and an **Inbox** section in `index.md` (one bullet per
candidate, naming the capture notes that back it). The ingest agent adds
Inbox bullets; the promotion pass (or the next qualifying ingest) turns
them into pages and clears the bullets.

- **Project** — promote on the **1st** source describing a concrete,
  committed, outcome-shaped effort.
- **Area** — promote on the **2nd** source informing the same
  responsibility.
- **Resource** — promote on the **2nd** source feeding the same interest.
- **Archive** — never auto-promoted; pages are *moved* here by review.

## Operations

| Operation | Trigger                  | What changes |
|-----------|--------------------------|--------------|
| Capture   | new file in `output/`    | new `sources/` note, updated P/A/R pages it feeds, `index.md`, `log.md` append |
| Promote   | review or threshold met  | Inbox candidate → new project/area/resource page |
| Archive   | review                   | page moves to `archives/` with `archived:` frontmatter |
| Query     | user asks a question     | no writes; agent reads relevant pages and answers |
