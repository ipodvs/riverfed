---
name: studio-deck
description: >
  Generate a slide deck from the Riverfed wiki — either a Marp deck
  (markdown → HTML/PDF/PPTX) or a native editable PowerPoint — styled by a
  chosen design, with optional Word speaker notes. Use whenever the user wants
  a "deck", "slides", "presentation", "training", "PowerPoint", or "pptx" built
  from the wiki, asks to "make a training on X", or wants speaker notes for a
  deck. Covers picking the generator + design, the file-lock recovery, and the
  design-reskin behaviour.
---

# Generate a Studio deck

Two generators, same wiki content, different output:

| Generator | Output | Use when |
|---|---|---|
| **Marp** (`studio_marp.py`) | markdown → HTML + PDF + PPTX (flattened image flipbook) | Diff-able source-of-truth deck; rich component library (versus/six-up/cards) |
| **Native PPTX** (`studio_pptx.py`) | a real editable `.pptx` (13 slide types) | Hand-off someone will edit in PowerPoint — real text boxes/shapes |

Both **reskin to the chosen design** (palette, fonts, icons, cover/section).

## Run it

From `/studio` in the browser (pick wiki + design + generator), **or** CLI:

```powershell
py -3.13 wiki\scripts\studio_marp.py --wiki wiki --prompt "..." --slides 14 --design designs\heritage.md
py -3.13 wiki\scripts\studio_pptx.py --wiki wiki --prompt "..." --slides 14 --design designs\aurora.md
```

- `--design` is optional; omit for the default house palette. Shipped
  designs: `designs/riverfed.md`, `heritage.md`, `aurora.md` (+ any
  `designs/custom/*.md`).
- Marp auto-renders HTML/PDF/PPTX next to the `.md` (needs the `marp` CLI;
  falls back to `npx @marp-team/marp-cli`). Each run prints the output paths.
- No server restart needed for generator changes — each `/studio` request
  spawns a fresh subprocess.

## Speaker notes (Word .docx, design-styled)

Tick **"Also generate a speaking guide"** (or pass the deck to
`studio_guide.py --design <path>`). It writes a slide-by-slide presenter
script as **both** `<name>-speaker-notes.md` and a Word `.docx` themed by the
same design (Heritage → Public Sans + ink + clay, Aurora → magenta/violet,
etc.). Word can't embed web fonts, so a non-installed family falls back to
Calibri — colours/layout still correct.

## Gotchas

- **PPTX file lock** — if PowerPoint has the target `.pptx` open, the build
  writes a sibling `.tmp.pptx` and warns instead of failing. **Close
  PowerPoint and regenerate** to land it at the canonical name. (Same for the
  speaker-notes `.docx` → `.tmp.docx`.)
- **Icons** — the native-PPTX agent must pick from the real icon bank (the
  prompt injects the 22 valid names); unknown names render blank. If you see
  "icon not found" warnings, the agent invented a name.
- **One accent per slide**; red (`--saber-red`) is errors only — never
  decorative (the "Sith Red rule").

## References (read on demand)

- [`designs/README.md`](../../../designs/README.md) — the design system,
  token→output mapping, how the reskin works, editor walkthrough
- [`wiki/training/design.md`](../../../wiki/training/design.md) — deck design
  system (palette, components, slide types, voice)
- [`wiki/scripts/studio_pptx.py`](../../../wiki/scripts/studio_pptx.py) —
  13 slide-type specs (docstring at top)
