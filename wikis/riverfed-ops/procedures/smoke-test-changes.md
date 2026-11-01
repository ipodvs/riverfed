---
slug: smoke-test-changes
kind: procedure
trigger: you changed code/content in an area and want to verify it before committing
last_updated: 2026-08-15
sources: [contributing-to-riverfed]
policies: []
tags: [wiki/procedures]
---

# Smoke-test changes

## When to run this

After changing any area of the repo, before opening or merging a PR. Automated
tests are the baseline; the relevant manual smoke test proves the behavior a
unit test cannot cover (contributing-to-riverfed).

## Steps

1. Run the full test suite: `python -m unittest discover -s tests`.
2. Identify which area your change touched and run the matching smoke test:

   | If you changed… | Run |
   |---|---|
   | `convert.py` | `convert.cmd <some YouTube URL>` — verify .md produced |
   | `convert.py --frames` path | `convert.cmd <URL> --frames` — check `output/<slug>-frames/` populated + `## Visual content` section in the .md |
   | `server.py` routes | `curl http://127.0.0.1:8765/<route>` returns 200 |
   | `wiki/scripts/ingest.py` | `py -3.13 wiki\scripts\ingest.py --dry-run` lists pending without errors |
   | Marp deck source | `marp` rebuilds HTML + PDF without errors; preview slide 1 looks right |
   | Excalidraw file | drag into excalidraw.com — opens, no console errors |
   | Wiki pages | `py -3.13 wiki\scripts\build_wiki_atlas.py` rebuilds atlas without errors |

3. For browser JavaScript changes, extract and parse every inline script with
   Node before the manual route check.
4. Fix and re-run until the checks pass, then commit per
   [[commit-message-format]].

## Gotchas

- The `curl` route check needs the server up first —
  [[run-the-local-server]].
- `--dry-run` on ingest is the safe check: it lists pending without
  writing anything to the wiki.

## Done means

The full automated suite and the smoke test for every area you touched pass
cleanly.
