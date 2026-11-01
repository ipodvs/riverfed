---
slug: ingest-a-source-into-the-wiki
kind: procedure
trigger: a YouTube link or file should become curated wiki content
last_updated: 2026-08-15
sources: [contributing-to-riverfed]
policies: [output-folder-immutability]
tags: [wiki/procedures, output-folder-immutability]
---

# Ingest a source into the wiki

## When to run this

You have a YouTube link (or file) whose content belongs in the wiki.
The wiki is **LLM-curated** — humans don't write source pages by hand;
this pipeline does (contributing-to-riverfed).

## Steps

1. Drop the YouTube link into the converter (the `/` page) —
   `output/<slug>.md` lands.
2. Open **Knowledge** and inspect the source-readiness row. A usable capture
   is marked **Ready** with provenance, language, duration, and word count; a
   blocked capture is marked **Needs recovery** with the exact failure.
3. If recovery is needed, run the targeted retry from that row. The original
   capture stays immutable and the successful retry becomes the selected
   revision for this ingest.
4. Click **Ingest ready**. The agent picked in the **Agent** selector
   (Claude Code, Grok, or Codex) creates `wiki/sources/<slug>.md` and
   updates topic/entity/concept pages. Leave it on **Auto** unless you
   have a reason: auto takes the first ready CLI, so a usage limit on
   one doesn't stall the queue.
5. Let the review cadence work: after every 5 ingests,
   `promote_backlog.py` auto-runs to surface patterns. Trigger it
   manually anytime with the **Run review now** button.
6. If you ever need to hand-touch the resulting pages, read
   `wiki/SCHEMA.md` first, then follow [[hand-edit-wiki-pages]].

## Gotchas

- Never edit `output/*.md` after ingestion and never commit `output/`
  ([[output-folder-immutability]]). To refresh a stale conversion,
  use the Knowledge recovery action or re-convert with `--overwrite`.
- Deep visual capture is provider-aware: Claude opens tagged JPEGs with Read;
  Grok opens them through `read_file`; Codex receives the same files through
  `codex exec --image`.
- Every ingest appends to `wiki/log.md` — that log is the safety net if
  a promotion goes wrong ([[claude-code-made-a-mess]]).

## Done means

The source passed readiness, `wiki/sources/<slug>.md` exists, related layer
pages are updated, and the ingest is recorded in `wiki/log.md`.
