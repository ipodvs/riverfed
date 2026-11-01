---
title: SOPs-to-Skills schema
purpose: rules and conventions for this operational knowledge base
last_updated: 2026-06-11
tags: [wiki]
---

# SOPs-to-Skills schema

This knowledge base holds a business's **operational knowledge**,
structured for two consumers at once: humans browsing it, and the
**Skills generator** that turns it into an executable Claude Code skill
library. Every page should be written so an agent could act on it.

Three layers, same as every base in this app:

1. **Raw sources** — dropped documents (SOPs, handbooks, checklists,
   meeting notes) converted into `../output/` (or this vault's own
   `output/`). **Immutable**: referenced, never edited.
2. **The base** — the markdown pages in this folder. **LLM-curated**.
3. **The schema** — this file.

## Folder layout

```
<vault>/
├── SCHEMA.md         # this file — conventions
├── index.md          # entry point: Procedures / Policies / Runbooks / Inbox
├── log.md            # append-only record of ingests and consolidation passes
├── sources/          # CAPTURE layer — one page per dropped document
├── procedures/       # step-by-step how-tos (the SOP layer)
├── policies/         # rules, standards, constraints
└── runbooks/         # symptom → diagnosis → recovery recipes
```

**Which folder?** A *procedure* is proactive ("how we do X, start to
finish"). A *runbook* is reactive ("X is broken / went wrong — how we
diagnose and recover"). A *policy* is a rule that constrains both
("we never Y", "Z must always happen before W").

## Page conventions

### sources/<slug>.md — capture note

One file per dropped document, written at ingest:

```markdown
---
slug: kebab-case-of-the-title
source_file: ../output/<original-filename>.md
title: ...
origin: handbook | checklist | meeting-notes | email | transcript
ingested: YYYY-MM-DD
procedures: [procedure slugs this doc documents]
policies: [policy slugs this doc states]
runbooks: [runbook slugs this doc describes]
---

# <Title>

## TL;DR
What this document is and what operational knowledge it carries.

## Extracted
- Procedures: links + one-liners
- Policies: links + one-liners
- Runbooks: links + one-liners

## Leftovers
Anything operational the page extraction did NOT capture (ambiguous,
contradictory, or below the bar) — the consolidation pass reads this.
```

### procedures/<slug>.md

The SOP layer — and the direct feedstock for generated skills. Write
each one so an agent could execute it without asking questions:

```markdown
---
slug: ...
kind: procedure
trigger: one line — the situation/request that starts this procedure
owner: role or person accountable (if the docs say)
last_updated: YYYY-MM-DD
sources: [capture-note slugs]
policies: [policy slugs this procedure must respect]
---

# <Procedure name — verb phrase, e.g. "Onboard a new client">

## When to run this
The trigger conditions, spelled out (requests, events, schedules).

## Steps
1. Numbered, imperative, one action each — with the WHY when a step
   exists to prevent a known failure ("…so that X doesn't happen").
2. Name the exact tools/commands/files involved.

## Gotchas
The hard-won failure modes and their avoidance — this section is gold
for the skill generator.

## Done means
How you know the procedure completed successfully.
```

### policies/<slug>.md

```markdown
---
slug: ...
kind: policy
last_updated: YYYY-MM-DD
sources: [...]
---

# <Policy name — the rule as a sentence>

## The rule
Stated plainly, one paragraph max.

## Why it exists
The incident/risk/value behind it (if the docs say).

## Scope & exceptions
Where it applies; the explicitly allowed exceptions.
```

### runbooks/<slug>.md

```markdown
---
slug: ...
kind: runbook
last_updated: YYYY-MM-DD
sources: [...]
---

# <Runbook name — the failure, e.g. "Server not responding">

## Symptoms
What the person sees/hears when this is the problem.

## Diagnose
Ordered checks, cheapest first. Each check says what its result means.

## Recover
The fix steps, with any "do NOT do X" warnings inline.

## Escalate
When to stop and hand off, and to whom.
```

## Naming rules

- **kebab-case** filenames and slugs; **no dates** in filenames.
- Procedures and runbooks slug as verb/failure phrases:
  `onboard-new-client.md`, `server-not-responding.md`.
- Policies slug as the rule's subject: `refund-approval.md`.

## Cross-linking rules (Obsidian-native)

Internal references are **always wikilinks** (`[[slug]]` /
`[[slug|display]]`); external links standard markdown. A procedure
**must** link the policies it respects; capture notes **should** link
everything they extracted. `scripts/obsidian_pass.py` normalizes
stragglers; idempotent.

## Promotion rules

The bars are 1 for procedures, policies, and runbooks — an SOP is
explicit the moment one document describes it. The bar exists as a
visible knob, not a gate: raise it for noisy doc dumps where you want
the consolidation pass to curate before pages appear. Candidates that
feel too thin to page (a half-described procedure, a rule implied but
never stated) go in the capture note's **Leftovers** and the index's
**Inbox** for the consolidation pass.

## The skill library (what this base compiles to)

`wiki/scripts/studio_skills.py` reads this base and emits a Claude Code
skill library: one `SKILL.md` per procedure/runbook (policies fold in
as rules/gotchas), a library README, and an `agents.md` context file.
Write pages with that consumer in mind: explicit triggers, exact
commands, the why behind steps.

## Operations

| Operation   | Trigger                 | What changes |
|-------------|--------------------------|--------------|
| Ingest      | new file in `output/`    | capture note + extracted P/P/R pages, `index.md`, `log.md` |
| Consolidate | review / threshold       | merge duplicates, promote Inbox leftovers, resolve contradictions |
| Compile     | Studio → Skills          | `.claude/skills/` library emitted from procedures + runbooks |
| Query       | user asks a question     | no writes |
