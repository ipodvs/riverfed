---
slug: hand-edit-wiki-pages
kind: procedure
trigger: a wiki page needs a small manual fix — typo, restructure, frontmatter tweak (rare)
last_updated: 2026-06-11
sources: [contributing-to-riverfed]
policies: [output-folder-immutability, file-naming]
tags: [wiki/procedures, output-folder-immutability, file-naming]
---

# Hand-edit wiki pages

## When to run this

A `wiki/<layer>/*.md` page needs a small fix — typos, restructuring.
Direct edits are fine, but rare by design: the wiki is LLM-curated
(contributing-to-riverfed).

## Steps

1. Read `wiki/SCHEMA.md` before editing — it defines the page
   conventions you must preserve.
2. Edit the `wiki/<layer>/*.md` page directly.
3. Keep the frontmatter consistent: `slug`, `last_updated`, `sources`,
   `tags`.
4. Re-run `py -3.13 wiki\scripts\obsidian_pass.py` afterward to
   normalise wikilinks — it's idempotent.

## Gotchas

- Edit only the wiki layers, never `output/*.md` — that's the immutable
  raw layer ([[output-folder-immutability]]). Re-convert with `--force`
  if the raw conversion itself needs refreshing.
- New page filenames follow [[file-naming]] (kebab-case slugs).

## Done means

The edit is in place, frontmatter intact, and `obsidian_pass.py` ran
clean.
