---
tags: [wiki/training, wiki]
---

# Training decks built from the wiki

Markdown decks for [Marp](https://marp.app/), styled by our custom theme
in `themes/ai-builders.css`. Every claim cites a source slug — open the
matching page in [[../sources/]] to drill into the original transcript.

The visual identity and slide-system rules are documented in
[[design]] — read that first before writing a new deck.

## Folder layout

```
training/
├── README.md                ← this file
├── design.md                ← the design system (read first)
├── .marprc.yml              ← Marp config (theme, output dir)
├── themes/
│   └── ai-builders.css      ← custom theme (palette, components, slide types)
├── assets/                  ← brand-neutral AI / tech illustrations
│   ├── ai-atom.png
│   ├── brain-spark.png
│   ├── brand-building.png
│   ├── cloud-star.png
│   ├── connected-nodes.png
│   └── partnership.png
├── ai-builders-handbook.md  ← the master training deck (~30 slides)
└── out/                     ← rendered HTML / PDF / PPTX (gitignored)
```

## Available decks

| File | Slides | Audience |
|---|---:|---|
| [[ai-builders-handbook]] | ~30 | Builders, founders, solo operators |

## Companion documents

| File | Purpose |
|---|---|
| [[ai-builders-handbook-speaker-notes]] | Markdown source — slide-by-slide presenter script |
| `ai-builders-handbook-speaker-notes.docx` | Pre-rendered Word document with the same content, styled in our brand colours |

The `.docx` is regenerated from the markdown by:

```powershell
py -3.13 wiki\training\scripts\build_speaker_doc.py
```

Edit the markdown source whenever you want to revise the script; re-run
the builder to refresh the Word doc.

## Rendering

Install Marp CLI once:

```powershell
npm install -g @marp-team/marp-cli
```

Render from the `training/` folder so the `.marprc.yml` is picked up:

```powershell
cd C:\Users\ipodvs\Youtuber\wiki\training
marp ai-builders-handbook.md --html -o out\ai-builders-handbook.html
marp ai-builders-handbook.md --pdf  -o out\ai-builders-handbook.pdf
marp ai-builders-handbook.md --pptx -o out\ai-builders-handbook.pptx
marp ai-builders-handbook.md --preview   # live preview
```

Or use **Marp for VS Code** — open the .md, click *Open Preview to the
Side*, instant slide view.

## Building a new deck

1. Read [[design]] — the design system.
2. Copy `ai-builders-handbook.md` as a starting point.
3. Trim sections you don't need; reuse the slide types
   (`cover`, `section`, `lead`, `dark`) for visual rhythm.
4. Use components from `themes/ai-builders.css` (`.kpi`, `.cards`,
   `.versus`, `.two-column`, `.steps`, `.six-up`, `.callout`) before
   inventing new HTML.
5. Keep slide count tight — handbook ~30, sub-deck 8–15.
6. Cite the source slug at bottom-left for any non-obvious claim.

## Forking the visual identity

The theme uses CSS custom properties on `:root`. Copy
`themes/ai-builders.css` → `themes/your-brand.css`, override the
palette + typography variables, and change `.marprc.yml` to point at
the new theme. Structural rules (slide types, components, scale) stay
portable.

## Acknowledgements

Layout patterns (cover with photo wall, two-panel comparisons, outcome
strips, card grids, section dividers with giant section numbers) are
inspired by the Computacenter brandbook decks in
`Codex Personal Assistance/Marp Computacenter/`. Palette, identity, and
training content are entirely our own.
