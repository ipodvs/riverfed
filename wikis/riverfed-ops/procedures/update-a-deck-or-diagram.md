---
slug: update-a-deck-or-diagram
kind: procedure
trigger: deck content needs changing, or a new diagram is needed
last_updated: 2026-06-11
sources: [contributing-to-riverfed]
policies: [branding-rules, file-naming, commit-message-format]
tags: [wiki/procedures, branding-rules, file-naming, commit-message-format]
---

# Update a deck or diagram

## When to run this

You're changing the master deck or adding/editing an Excalidraw
diagram. Both are source files committed to the repo, and their
rendered outputs (`out/*.{html,pdf,pptx,docx}`,
`docs/screenshots/*.png`) are **also committed** for easy sharing —
so source and outputs must move together.

## Steps

For a deck change:

1. Edit `wiki/training/ai-builders-handbook.md` (the source).
2. Rebuild the outputs with the `marp` CLI — done when it rebuilds
   HTML + PDF without errors and preview slide 1 looks right.
3. Commit source + outputs **together** (commit type `deck` per
   [[commit-message-format]]) — so the repo never carries stale
   renders.

For a new diagram:

1. Either write the `.excalidraw` JSON directly (see existing files in
   `diagrams/` for shape) or generate via `/studio`.
2. Commit it to `diagrams/`.
3. Optionally render a PNG for the README.

## Gotchas

- The exact `marp` command flags are NOT in the source handbook
  (contributing-to-riverfed refers to "commands above" that
  aren't in the document) — flagged in the index Inbox until a capture
  states them.
- The PNG render method is only described as "`landing/icons/`-style
  Chrome headless" — also in the Inbox; treat as optional.
- All visuals must respect [[branding-rules]] — especially the Sith
  Red rule (red = errors only, never decorative).
- Verify the Excalidraw file by dragging it into excalidraw.com — it
  should open with no console errors ([[smoke-test-changes]]).

## Done means

Source edited, outputs rebuilt without errors, and one commit contains
both — no stale renders left behind.
