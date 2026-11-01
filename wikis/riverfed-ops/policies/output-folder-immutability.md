---
slug: output-folder-immutability
kind: policy
last_updated: 2026-06-11
sources: [contributing-to-riverfed]
tags: [wiki/policies]
---

# output/ is immutable and never committed

## The rule

Never edit `output/*.md` after ingestion — that's the immutable raw
layer. If a conversion needs refreshing, re-convert with `--force`
instead of editing. And never commit `output/` — it's gitignored.

## Why it exists

The raw layer must stay a faithful record of what was converted, so
the curated wiki pages can always be traced back to it. Committing it
is unnecessary: wiki pages alone are enough, and if your
co-collaborator needs to re-ingest a specific source they can
re-convert from the URL in the wiki page's frontmatter
(contributing-to-riverfed).

## Scope & exceptions

Applies to the converter's raw output staging. No exceptions stated —
the only sanctioned "change" is a full re-conversion via `--force`.

Respected by: [[ingest-a-source-into-the-wiki]],
[[hand-edit-wiki-pages]].
