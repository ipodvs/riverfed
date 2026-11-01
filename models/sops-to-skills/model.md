---
version: alpha
name: SOPs to Skills
description: >
  A small business's operational knowledge — dropped docs distilled into
  Procedures (step-by-step how-tos), Policies (rules and standards), and
  Runbooks (diagnose-and-recover recipes) — structured so the Skills
  generator can emit a Claude Code skill library from it. Knowledge in,
  agents out.
folders:
  sources:
    kind: source
    role: capture layer — one page per dropped document or transcript
    capture: true
    label_field: title
  procedures:
    kind: procedure
    role: step-by-step how-tos with triggers, tools, and gotchas
    promote_after: 1
    weight: { min: 3 }
    card: { description: When to run this, callout: Done means }
  policies:
    kind: policy
    role: rules, standards, and constraints that govern the work
    promote_after: 1
    weight: { min: 2 }
    card: { description: The rule, callout: Why it exists }
  runbooks:
    kind: runbook
    role: symptom-driven diagnose-and-recover recipes
    promote_after: 1
    weight: { min: 3 }
    card: { description: Symptoms }
links:
  documents: { from: source, field: procedures, to: procedure }
  governs: { from: source, field: policies, to: policy }
  recovers: { from: source, field: runbooks, to: runbook }
  enforces: { from: procedure, field: policies, to: policy }
generators: marp, pptx, diagram, guide, skills
search_hint: procedures, policies, runbooks
bases:
  ops-catalog: { title: Ops catalogue }
  sop-freshness: { title: SOP freshness }
---

# SOPs to Skills — knowledge model manifest

The B2B wedge model: drop a business's operational docs in, get a
structured operations base out — and from it, a **Claude Code skill
library** (`studio_skills.py`) any agent session can execute.

## Why promotion bars are 1 here

Unlike concepts (evidence accumulates across sources), an SOP is
explicit the moment one document describes it: a single doc describing
"how we onboard a client" IS the procedure. The bars exist so the knob
is visible and tunable per business, not to gate extraction.

## The pipeline this model feeds

```
drop docs → ingest (capture + extract P/P/R pages)
          → studio_skills.py reads the base
          → .claude/skills/<name>/SKILL.md per procedure/runbook
            + skills README + agents.md context file
          → a fresh Claude Code session executes the work
```

Policies don't become standalone skills — they surface as rules and
gotchas INSIDE the skills generated from the procedures that cite them
(the `enforces` link).

## Files in this directory

| File | Role |
|---|---|
| `model.md` | This manifest |
| `SCHEMA.md` | Canonical conventions — copied into each new vault at scaffold time |
| `ingest-prompt.md` | Per-document extraction prompt (`wiki/scripts/ingest.py`) |
| `promote-prompt.md` | Consolidation pass (`wiki/scripts/promote_backlog.py`) |

Prompt placeholders: `{wiki_rel}`, `{output_rel}`, `{transcript_name}`,
`{wiki_slug}` from the vault; `{procedure_promote_after}`,
`{policy_promote_after}`, `{runbook_promote_after}` from this manifest.
