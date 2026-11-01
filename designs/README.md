# Designs

A catalogue of visual-identity presets the Studio can apply to any
generated deck or diagram. Each preset is a `design.md` file following
the [google-labs-code/design.md](https://github.com/google-labs-code/design.md)
spec: YAML front matter (tokens) + Markdown body (rationale).

## The format

```md
---
name: Heritage
description: >
  Architectural Minimalism meets Journalistic Gravitas.
colors:
  primary: "#1A1C1E"
  secondary: "#6C7278"
  highlight: "#B8422E"
  background: "#F7F5F2"
typography:
  h1:
    fontFamily: Public Sans
    fontSize: 3rem
    fontWeight: 700
  body-md:
    fontFamily: Public Sans
    fontSize: 1rem
  eyebrow:
    fontFamily: Space Grotesk
    fontSize: 0.75rem
rounded: { sm: 4px, md: 8px }
spacing: { sm: 8px, md: 16px }
components:
  card:
    backgroundColor: "{colors.background}"
    rounded: "{rounded.sm}"
---

## Overview
…

## Colors
…

## Typography
…
```

The tokens are the normative values. The prose tells human readers (and
LLMs reading the file) *why* the values exist and how to apply them.

## The catalogue

| ID | Name | Vibe |
|---|---|---|
| `riverfed` | Riverfed | The house identity: deep-space dark with one Riverfed green accent over neutrals, Inter + JetBrains Mono. The default for branded artifacts. |
| `deep-space` | Deep Space | The same dark canvas with an electric-blue accent: a cool, technical alternative to the house green, and the palette the AI Builders Handbook was authored in. |
| `heritage` | Heritage | Architectural minimalism meets journalistic gravitas. Warm limestone, deep ink, single Boston-clay accent. |
| `aurora` | Aurora | Bright-dawn palette with a magenta and teal duotone, generous curves, and Sora display type. For launches and keynotes. |

## How the Studio uses these

1. The `/studio` page shows a picker with one card per design (palette
   swatches + name + 1-line description + font hint).
2. Selection is saved to `localStorage` and sent as `design_id` in the
   POST body to `/studio/{marp,pptx,diagram}`.
3. `server.py` resolves `design_id` → `designs/<id>.md` (with a
   path-traversal guard: only `[a-z0-9][a-z0-9_-]*` allowed), and
   forwards `--design <path>` to the generator subprocess.
4. The generator calls into the design:
   - `studio_pptx.py` → `_apply_design(path)` mutates its module-level
     palette + font constants so every slide-type renderer picks them up.
   - `studio_marp.py` → derives a Marp theme (see "Marp reskin" below).
   - `studio_guide.py` → renders the speaker notes to a Word `.docx` via
     [`wiki/scripts/speaker_docx.py`](../wiki/scripts/speaker_docx.py), themed
     by the design (see "Speaker-notes Word doc" below).
   All load the design via
   [`wiki/scripts/design_tokens.py`](../wiki/scripts/design_tokens.py).

## Token → constant mapping (used by `studio_pptx.py`)

| design.md key   | studio_pptx.py constant |
|---|---|
| `colors.primary`              | `COL_ACCENT_BLUE`   |
| `colors.secondary`            | `COL_NEURAL`        |
| `colors.success`              | `COL_GREEN`         |
| `colors.highlight`            | `COL_YELLOW`        |
| `colors.background`           | `COL_BG_DARK`       |
| `colors.background-elevated`  | `COL_PANEL_DARK`    |
| `colors.surface`              | `COL_BG_CREAM`      |
| `colors.surface-cream`        | `COL_BG_CREAM_LO`   |
| `colors.foundation`           | `COL_TEXT_DARK`     |
| `colors.text-muted`           | `COL_TEXT_MUTED`    |
| `colors.text-faint`           | `COL_TEXT_FAINT`    |
| `typography.h1.fontFamily`    | `FONT_DISPLAY`      |
| `typography.body-md.fontFamily` | `FONT_BODY`       |
| `typography.eyebrow.fontFamily` | `FONT_MONO`       |

The generator's defaults are the Riverfed values, so if a design
omits a token the renderer falls back to the saber-blue, Inter, and
JetBrains Mono baseline.

## Marp reskin (studio_marp.py)

`studio_marp.py` applies the design by deriving a Marp theme: it reads
`wiki/training/themes/ai-builders.css` verbatim (keeping the
`@theme ai-builders` name so the deck's front matter still resolves) and
appends an override block. The base theme isn't fully variable-driven. It
hardcodes white card backgrounds, navy shadows, a saber-blue cover glow,
10px card radii, and white-on-dark cover/section text. The override
does two things, both winning by cascade order (no edit to the shared
theme, so the master handbook stays byte-identical):

1. **Palette + grey ramp**: re-points the base custom properties
   (`--accent`, `--neural`, `--circuit`, `--bg-cream`, `--foundation`, the
   full `--grey-1..6` ramp, etc.). Most of the deck reads through these,
   and the `--saber-*` aliases follow automatically (`var(--accent)`).
2. **Hardcoded selectors**: re-declares the handful of rules that bake in
   values: card radius (from `rounded` / `components.card.rounded`), card
   surfaces + shadows, the cover-logo glow, dark-slide code tint, and the
   `cover` / `section` hero slides (from `components.cover-bg` /
   `section-divider-bg`).

Fonts map `body-md → section`, `h1 → headings`, `eyebrow → eyebrows/nums/cite`.

Two deliberate, design-agnostic rules make light/editorial palettes (e.g.
Heritage) render correctly rather than just "apply colours":

- **Accent is the *vibrant* token, not always `primary`.** A saturation +
  lightness check picks `primary` when it's vibrant (saber blue),
  else `highlight` (Heritage's `primary` is near-black ink; its accent is
  the clay `highlight`). Without this the deck's eyebrows / KPI numbers /
  card stripes / links render as dull ink.
- **The dark hero/section background comes from `foundation`** (reliably
  dark across designs), not `background`. In a light palette `background`
  is light, which would make white cover text unreadable. The cover /
  section slides themselves follow the design's `components.cover-bg` and
  `section-divider-bg` (so Heritage gets a light limestone cover + dark ink
  section dividers, exactly as its tokens specify).

### Brand assets + fonts

Two things the CSS palette can't reach on its own are handled at render time
by `_prepare_deck` and the font `@import`:

- **Fonts actually load.** The base theme only *names* font families, so
  non-system fonts (Public Sans, Inter…) silently fall back to the OS
  default sans. This makes differently-fonted designs look identical. The
  derived theme now `@import`s each of the design's families from Google
  Fonts (one line each, before `:root`), so chromium fetches and renders the
  real typeface. Offline, it falls back gracefully.
- **Embedded icons.** Bundled icons are `<img>`-embedded SVGs with a hardcoded
  saber-blue stroke, so CSS cannot recolour them. On a custom-design deck we
  inline each icon SVG and swap the brand blue for the design's accent, such
  as clay for Heritage. The typographic Riverfed cover wordmark is never
  removed or recoloured; its Inter and JetBrains Mono lockup sits outside the
  selected artifact design. Inlining is required because Marp keeps
  `<img src>` as external path references in the HTML.

## Speaker-notes Word doc (studio_guide.py → speaker_docx.py)

When "Also generate a speaking guide" is on, the agent writes the notes as
Markdown, then [`wiki/scripts/speaker_docx.py`](../wiki/scripts/speaker_docx.py)
renders a styled Word `.docx` themed by the chosen design:

| design.md token | Word doc usage |
|---|---|
| `foundation` (dark) | Title / Heading 1 / Heading 2 / body text / bold runs |
| accent (vibrant `primary`, else `highlight`) | Heading 3, cover eyebrow, accent rule, callout/quote left border |
| `text-muted` (never `secondary`) | subtitle + meta greys |
| `surface-cream` | inline-code + code-block shading |
| `body-md.fontFamily` | body font, with a **Calibri fallback** |

Word can't `@import` web fonts like the Marp HTML can, so a non-installed
family (Public Sans, Sora) falls back to Calibri. Set the family in Word's
font menu, or install it, for an exact match. The same atomic `.tmp.docx`
swap as the PPTX path keeps an open-in-Word file from hard-failing.

`build_speaker_doc.py` (the handbook builder) is a thin wrapper over the
same renderer with `design_path=None` (default house palette).

## Not yet wired

- **studio_diagram.py**: accepts `--design <path>` for API compatibility
  but doesn't apply the tokens. Open issue: pipe colour tokens into the
  generated Excalidraw JSON's `strokeColor` / `backgroundColor` fields.

## Customising via the Studio UI

The Studio page (`/studio`) loads designs dynamically and exposes
three actions per tile:

- **Click the tile** to select it as the active design.
- **✎ Edit** (hover-revealed top-right) opens a modal with form fields
  for the editable tokens: name, description, 8 colour pickers
  (primary / secondary / success / highlight / background / surface /
  foundation / text-muted), 3 font family fields (Display / Body /
  Mono). The fonts come with a `<datalist>` of widely-installed
  families (Aptos, Inter, Public Sans, Sora, Calibri, Arial, etc.) but
  you can type any name. Live swatches preview the palette as you type.
- **↺ Reset** / **🗑 Delete** (only on customs): removes the custom
  override and falls back to the shipped default; on pure customs
  (no shipped twin) this deletes the design entirely.

A **+ Create new design** tile at the end of the grid opens the same
modal pre-seeded from the currently-selected design. Pick a new ID
(lowercase letters / numbers / dashes; that becomes the filename) and
save.

### How the override works

- **Shipped** designs live at `designs/<id>.md` (committed to git).
- **Custom** designs live at `designs/custom/<id>.md` (gitignored).
- When a custom design has the same `<id>` as a shipped one, the
  custom wins, and the tile shows an `EDITED` badge. Resetting just
  removes the custom file; the shipped one is untouched (read-only
  from the UI's perspective).
- New designs created from scratch go straight to
  `designs/custom/<new-id>.md` and show a `CUSTOM` badge.

### Persistence

Custom designs persist as real files on disk, so they survive browser
restarts and are usable directly from the CLI:

```powershell
py -3.13 wiki\scripts\studio_pptx.py --wiki wiki `
  --prompt "..." `
  --design designs\custom\my-design.md
```

If you want to share a custom design with the team, copy it from
`designs/custom/` into `designs/` (drops the `custom/` prefix) and
commit it.

## Adding a new design by hand

If you'd rather skip the UI editor:

1. Copy one of the existing files (`riverfed.md` is the most
   complete template) and rename it `<your-id>.md`. The ID becomes the
   filename and the `design_id` the UI passes back to the server.
2. Edit the YAML front matter: at minimum set `name`, `description`,
   and the `colors.primary` / `colors.secondary` / `colors.background`
   / `colors.surface` / `colors.foundation` tokens.
3. Edit the prose so a human (or LLM) reading the file can apply the
   design without seeing it rendered. Cover Overview / Colors /
   Typography / Layout / Components / Do's & Don'ts.
4. Drop the file at `designs/<your-id>.md` (to ship it) or
   `designs/custom/<your-id>.md` (to keep it local). No HTML edits
   needed. The picker is dynamic.
5. Smoke-test:
   ```powershell
   py -3.13 wiki\scripts\design_tokens.py
   # should print your new design alongside the existing three
   ```
6. End-to-end test via the Studio UI: select your design, generate a
   pptx, open it in PowerPoint to confirm the palette + fonts landed.

## The server API

`GET /api/designs`: list all designs (shipped + custom).
`GET /api/designs/<id>`: full tokens for the editor.
`PUT /api/designs/<id>`: body JSON: `{name, description, colors,
typography, rounded, spacing}`. Writes to `designs/custom/<id>.md`.
Path-traversal guard: id must match `^[a-z0-9][a-z0-9_-]*$`.
`DELETE /api/designs/<id>`: removes the custom file (no-op if absent).
If a shipped twin exists, the response includes
`"reset_to_default": true`.

## Validation

The official `@google/design.md` CLI lints token references, checks
WCAG contrast ratios, and detects token-level regressions between
versions. We don't run it in CI yet. To run it ad hoc:

```bash
npx @google/design.md lint designs/heritage.md
```

(On Windows in PowerShell, quote the package name: `npx "@google/design.md" lint …`.)
