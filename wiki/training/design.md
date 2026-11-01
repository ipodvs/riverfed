---
tags: [wiki/training, design-system, wiki]
last_updated: 2026-07-21
---

# AI Builders: Deck Design System

The single source of truth for every Marp deck under `wiki/training/`,
plus the cross-surface taste rules shared by the product UI and marketing
site. Hand this file to any agent (or designer) and they should produce
work that feels authored rather than assembled from generic AI patterns.

The system borrows useful structural patterns from the reference workspace,
but no pattern is mandatory. A card grid, icon, pill, gradient, or ornament
must solve a communication problem; it is never added simply to make a
surface look "designed."

---

## 1. Tokens

### Palette

```
--bg-cream        #fafaff   default canvas (icy cream)
--cream           #f5f0e6   Jedi-robe warm cream (alternate light surface)
--bg-dark         #0e1117   cover slide background: deep space
--bg-elevated     #181b22   inline panels on dark slides
--foundation      #0f1729   primary text + section divider bg: Coruscant night
--foundation-2    #1a2540   elevated dark surface

--accent          #46c98b   Riverfed deck green: the one dark-surface accent
--accent-hover    #1d9e66   deeper brand green (hover / pressed)
--neural          #6c7278   slate: neutral second colour, never a bright accent
--circuit         #1d9e66   deeper green (success / production)
--legacy-blue     #4f8cff   the Deep Space design's accent; also the handbook
--fibre           #ff6b35   orange (warning / energy)
--voltage         #ffd93d   yellow (highlight): Star Wars logo gold
--united          #ff4d4d   red (ALERT only: see Sith rule below)
```

Greys: `--grey-1` (#1a1d24) → `--grey-6` (#eff1f4), six steps.

**Rule of accent use:** one accent per composition. Default to `--accent`
on decks and Riverfed green on product/marketing surfaces. Additional colours
are permitted only when they encode a stable category, state, or comparison
that the audience needs to distinguish. Never rotate colours merely to make
neighbouring cards look different.

### Jedi palette

The brand is "Riverfed". Jedi training is distilled into a knowledge
system. Our palette maps cleanly to canonical Star Wars Jedi colors, so we
give every token a Jedi alias. Use whichever name reads clearer in context.

| Functional | Jedi alias | Hex | Lore |
|---|---|---:|---|
| `--accent` | `--saber-green` | `#46c98b` | **The dark-surface accent** (2026-07-25). Riverfed artifacts lead with green: the dark twin of the `#1d9e66` brand dot. |
| `--circuit` | (none) | `#1d9e66` | Brand green, deeper. Success / live states; distinct from the accent. |
| `--neural` | (slate) | `#6c7278` | **Neutral second colour.** A stable node kind in diagrams, or the "other" side of a comparison. Never a second bright accent. |
| (alt accent) | `--saber-blue` | `#4f8cff` | **The Deep Space design's accent**, and what the AI Builders Handbook plus existing Excalidraw diagrams already use. Not the accent for Riverfed-branded artifacts. |
| (legacy) | `--saber-blue-glow` | `#4dbeff` | **Legacy deck token.** Focus/energy only; never ambient decoration. No renderer reads it. |
| (retired) | `--saber-purple` | `#7a59e2` | **Retired as an accent.** Pairing it with blue is the "AI" signal the anti-slop contract bans; it survives only in already-rendered legacy artifacts. |
| `--voltage` | `--saber-yellow` | `#ffd93d` | **Jedi Sentinel** + the Star Wars logo gold. Highlights only. |
| `--fibre` | `--saber-orange` | `#ff6b35` | **Tatooine sunset** / rare orange saber. Energy / warmth. |
| `--united` | `--saber-red` | `#ff4d4d` | **SITH**: error / destructive only (see rule below). |
| (none) | `--cream` | `#f5f0e6` | **Jedi robes**: warm cream for soft light surfaces. |

**The Sith Red rule.** Red is the Sith color. We *do not* use red as a regular
content accent. It appears only when the system needs to signal: error,
destructive action, broken state, or alert. The `--united` modifier on
Marp cards exists for this and only this. Never use it for "card 5 of 5" if all
you need is differentiation (use spacing, a neutral rule, or numbering).

**The no-glow rule.** Do not use ambient halos, neon drop-shadows, or
blue-purple gradients. They are an overused shorthand for "AI" and make the
work feel unowned. `--saber-blue-glow` is a legacy deck token: reserve it for
a real focus/energy state where luminosity carries meaning. Product and
marketing surfaces do not use it. Filled CTAs use one solid, accessible
colour.

**Why the alias layer?** Functional names (`--accent`, `--neural`) are
mnemonic for *what the color does in a layout*. Jedi names (`--saber-blue`,
`--saber-purple`) are mnemonic for *what the brand stands for*. Both are
useful, so we ship both, pointing at the same hex. Refactoring the
functional names would cascade through 30 Marp slides and break too much,
so we keep them and add aliases instead.

### Surface registers

Do not pour the whole deck palette onto every surface. Each register has a
different job:

| Register | Colour policy | Structural policy |
|---|---|---|
| Product UI + marketing | Porcelain neutrals + Riverfed green (`#157347`, hover `#115d3a`). Red only for errors. | Hairlines, type, spacing, and clear control grouping. Almost no decorative colour. |
| Decks | One deck accent + neutrals per slide. A second colour only for a meaningful comparison. | Components may be more expressive because slides are presentation surfaces. |
| Diagrams + graphs | Multiple colours only when they encode stable node kinds, states, or paths. Include a legend when meaning is not obvious. | Information density justifies visual encoding; decoration does not. |
| Design picker | Swatches show the real selectable designs. Their colour is data, not page decoration. | Keep the surrounding Studio UI neutral so the designs remain distinguishable. |

### Anti-AI-slop contract

This is a hard constraint for every new UI, deck, diagram, and generated
artifact. The failure mode is familiar: blue-purple gradients, floating
rounded cards, pill-shaped everything, decorative sparkle icons, centered
copy stacked section after section, and motion that explains nothing.

**Colour**

- Product and marketing surfaces use one green accent plus neutrals.
- Blue and purple never appear together as a generic signal for "AI."
- A rainbow sequence is not visual variety. Extra colours require a named,
  stable meaning that survives across the whole composition.
- Gradients and glows are off by default. Use a solid fill, hairline, or type
  weight first.

**Containers**

- Do not wrap every idea in its own card. First try whitespace, a shared
  boundary, a ruled list, columns, or a table.
- When several siblings belong together, prefer one outer boundary with
  internal dividers over several floating cards.
- Product corner radii: 6–8px for controls, 8–10px for real containers.
  `999px` is reserved for true capsules: status tags and compact segmented
  controls whose shape communicates grouping.
- Buttons, search fields, nav CTAs, content panels, and ordinary form fields
  are not pills.
- Shadows are not a default hierarchy tool. Use a 1px border; at most a
  near-flat `0 1px 2px` shadow. Strong shadows belong to transient overlays
  such as modals.

**Icons and decoration**

- An icon must improve recognition or explain an action. Do not add an icon
  tile to every feature merely to fill the upper-left corner.
- Prefer bare monochrome icons. Avoid tinted rounded-square backplates,
  sparkles, orbit dots, random blobs, and ungoverned ambient ornaments. The
  deck's single documented top-right diamond is the only exception; it does
  not appear on product or marketing surfaces.
- The Riverfed wordmark is enough branding. Do not add a pictorial logo or repeat
  the mark as decoration.

**Composition**

- Do not repeat the formula `centered eyebrow → centered heading → centered
  paragraph → three cards` down a page.
- Marketing sections default left-aligned. Centering is reserved for a single
  deliberate hero or closing beat, not every section.
- Sequential content gets equal columns or a real timeline. Do not stagger
  card heights for visual interest.
- Long catalogues become ruled indexes or tables, not walls of cards.
- Technical labels render as plain mono metadata. Do not turn every file type,
  path, or format into a chip.

**Motion**

- Motion must explain state, causality, or navigation.
- No ambient scroll reveals, floating loops, shimmer, parallax, or pulsing
  decoration. Content is present immediately.
- Keep feedback transitions short (roughly 120–180ms) and respect
  `prefers-reduced-motion`.

**Copy**

- Never use em dashes (`U+2014`, including the equivalent HTML entity).
  Rewrite the thought with two sentences, a comma, a colon, or parentheses.
- Specific evidence beats synthetic confidence. Name the file, count, output,
  or action rather than using generic claims such as "unlock," "supercharge,"
  or "AI-powered."
- Avoid decorative arrows in every CTA. Use them only when direction or
  navigation is the point.

**Live product evidence and extensibility**

- Product figures are observations, not marketing constants. The About page
  reads `/wikis`, selects the main base by the stable `wiki` slug, and renders
  the folder counts supplied by that base's current knowledge model.
- Never copy a wiki count into HTML, a footer, or descriptive prose. Show a
  clear loading or unavailable state if the live endpoint cannot be read.
  Stale evidence is worse than no evidence.
- The public model catalogue reads `/api/models`. Names, descriptions,
  folders, and generators come from the registry so a newly added model is
  visible without another landing-page edit.
- Explain the shared engine before naming individual methods. Karpathy Wiki,
  Second Brain (PARA), and SOPs to Skills are examples of model-specific
  organisation and output, not the architecture itself.
- Do not assume every base has `topics`, `entities`, or `concepts`. Folder
  labels and counts must follow the selected model manifest.
- A direct `file:` preview cannot read the local API safely. Give it an
  explicit link to the localhost About route. Do not add broad CORS access to
  private vault data to make a static preview appear live.

### 2026-07-21 product audit decisions

These are canonical replacement patterns, not one-off fixes:

| Rejected pattern | Approved replacement |
|---|---|
| Blue SVG inside a pale rounded tile | Bare charcoal icon; omit the icon when the heading already identifies the feature |
| Purple/green/rainbow stripes across peer rows | One green emphasis, then graphite and neutral rules unless colours encode data |
| Three separately floating pipeline cards | One bordered three-column group, equal tracks, internal dividers, wrapped technical metadata |
| Fifteen feature cards with icon tiles and tag chips | Three-column ruled catalogue; no icon tiles; plain mono metadata |
| Twelve square file-type cards | Compact ruled inventory with extension + label |
| Three rounded tier cards with shadows | One flat progression row with dividers |
| Eyebrow pill + cloud of format pills | Plain mono eyebrow + dot-separated metadata line |
| Pill CTAs and pill search fields | 7–8px rectangular controls; capsules only for real tags/toggles |
| Large rounded closing CTA panel | Flat section separated by a rule |
| Scroll-in reveal animation | Static, immediately available content |

**Functional exceptions:** Wiki node colours encode model folders; graph
colours encode node kinds; Studio design swatches represent actual selectable
palettes; compact status labels and segmented controls may remain capsules.
Those uses carry information and are not decorative palette rotation.

### Typography strategy

Riverfed uses a fixed two-family system. Typography is part of the brand,
not a per-page styling choice.

| Role | Canonical family | Weight | Use |
|---|---|---:|---|
| Wordmark | Inter | 900 | `Riverfed` + the green signature dot |
| Display + UI | Inter | 700–900 | Marketing headlines, product headings, navigation, controls |
| Body | Inter | 400–600 | Paragraphs, descriptions, form copy, generated Riverfed artifacts |
| Project voice | JetBrains Mono | 400–700 | Eyebrows, citations, code, paths, compact metadata |

**Stacks**

- Sans: `Inter, -apple-system, BlinkMacSystemFont, Segoe UI, system-ui, sans-serif`
- Mono: `JetBrains Mono, SF Mono, Menlo, Consolas, monospace`
- Inter and JetBrains Mono must request all weights actually used. In
  particular, every page that renders the wordmark must load Inter 900.
- No third active family is allowed in the product interface.

**Font inventory and disposition**

| Family | Where it was found | Decision |
|---|---|---|
| Inter | Product pages, navigation, Marp base theme, speaker docs | Canonical Riverfed sans family |
| JetBrains Mono | Metadata, code, Marp citations (and the pre-2026-11 wordmark suffix) | Canonical Riverfed project voice |
| Aptos Display / Aptos | Previous house preset and native PowerPoint defaults | Removed from the brand definition; Office may substitute Aptos locally when Inter is unavailable |
| Consolas | Previous house metadata default | Fallback for JetBrains Mono only |
| Sora | Aurora preset | Allowed only inside Aurora-generated artifacts and its Studio preview |
| Public Sans / Space Grotesk | Heritage preset | Allowed only inside Heritage-generated artifacts and its Studio preview |
| Excalifont / Cascadia | Excalidraw diagrams | Medium-specific exception because they are built into Excalidraw |
| Segoe UI / Arial / Calibri | Platform fallbacks | Fallbacks only, never an authored Riverfed choice |

**Surface policy**

- Marketing, Converter, Wiki, Studio chrome, and shared navigation always use
  Inter plus JetBrains Mono. The selected Studio design never restyles the
  Studio interface.
- The Riverfed artifact preset uses the same Inter plus JetBrains Mono
  pair across Marp, native PowerPoint, Word, and Anki.
- Alternate Studio presets may change artifact typography because the design
  itself is the output identity. Their fonts stay inside the preview and the
  generated file.
- The Riverfed wordmark sits outside the selected artifact design.
  `Riverfed` stays Inter 900 with the green dot even when an Aurora or
  Heritage artifact is generated.
- Office files keep the canonical font names. Install Inter and JetBrains Mono
  for exact rendering; local Office substitutions are fallbacks, not brand
  alternatives.

**Deck scale**

  | Element | Size | Weight |
  |---|---:|---:|
  | Cover H1 | 88 px | 700 |
  | Section H1 | 80 px | 700 |
  | Content H1 | 56 px | 700 |
  | H2 (subtitle) | 30 px | 500 |
  | H3 (card head) | 24 px | 700 |
  | Body | 24 px | 400 |
  | Eyebrow | 16 px | 700 (uppercase) |
  | Caption / cite | 13–15 px | 400 |

- **Letter spacing**: -0.01em on headings; +0.14em (uppercase) on eyebrows
  and section numbers
- **Line height**: 0.96 on hero headings, 1.18 on body

### Layout

- Slide canvas: 1280 × 720 (16:9)
- Padding: 56 px horizontal, 44 px vertical
- Decorative top-right diamond `◆` in accent on content slides (the deck's
  one documented ambient signature; the wordmark is cover-only)
- Pagination bottom-right, grey
- Citation bottom-left, mono, grey

### Brand mark: wordmark only

The Riverfed brand is **typography, not a picture**:

- **`Riverfed`** in **Inter 900**, tight tracking (-0.03 to -0.045em by
  size), sentence case, followed by
- **the signature dot** in brand green `#1d9e66` (the nav and Marp
  covers; dark PPTX covers use the deck green token).

In running text the name is a plain
word, `Riverfed`, with no dot and no special styling; only the nav, the
deck cover and the PPTX cover kicker carry the wordmark.

No pictorial logo appears on any page or slide (user call, 2026-07-21:
the enlarged square mark reads as an app-icon blob).

The square dot-mark (`landing/icons/riverfed-mark*.svg` + PNGs) survives in
exactly ONE place: the browser-tab favicon, where the geometry works at
16-32px. Never render it larger than that.

**Where the brand appears:**

| Surface | Treatment |
|---|---|
| All navs (converter + landing) | text wordmark, green dot, no image |
| Marp cover slide | `.cover-wordmark`: 26px ivory wordmark, top-right |
| Native PPTX cover | fixed wordmark kicker: Inter `Riverfed` + green dot |
| Landing page hero | none: plain mono eyebrow + headline lead |
| README | plain `<h1>Riverfed</h1>` |
| Favicon | the square dot-mark (only pictorial use) |

**Do not** put the wordmark on every content slide. The ambient `◆`
does that job. It appears once per deck (cover) to set identity, then
stays out of the way.

The wordmark is not controlled by the Studio design picker. A selected output
design may change the surrounding artifact typography, never the wordmark.

### Excalidraw conventions

Excalidraw is our **whiteboard** for system diagrams, flows, and
architecture sketches. Files live in `diagrams/` at the repo root, as
plain `.excalidraw` JSON (diff-able, agent-editable, version-controlled).
We export to PNG and embed in Marp slides where appropriate.

**Aesthetic register:** Excalidraw is intentionally hand-drawn. This is
the *right* register for system maps and "here's how the loop works"
moments. Sketchy reads as "this is a thinking tool, not a finished
deliverable." For polished, audience-ready content, use Marp.

**Element defaults** (encode these in every file):

**The canonical exemplar is [`diagrams/wiki-atlas.excalidraw`](../../diagrams/wiki-atlas.excalidraw).**
Match its conventions exactly when generating new diagrams. The values
below are derived from it.

| Property | Value | Why |
|---|---|---|
| `roughness` | `0` (clean): reserve `1` only for the occasional hand-drawn accent | The atlas reads crisp and map-like, not sketchy; roughness-1 everywhere looks messy |
| `strokeWidth` | `1` (default) / `2` (emphasis), `3` very sparingly | Thin, elegant lines: the atlas is 92×`1`, 25×`2`, 6×`3` |
| Connectors | thin **`line`** elements (not `arrow`) at `#4dbeff`/`#cae3ff` | The atlas connects nodes with clean lines, not sketchy arrowheads |
| `fontFamily` | `4` (Excalifont) for headings/body, `3` (Cascadia) for eyebrow tags + code | Excalifont matches our Inter weight; Cascadia for code |
| `fillStyle` | `solid` | `hachure` is too noisy at slide-embed sizes |
| `roundness.type` | `3` (adaptive) on rectangles | Matches the soft corners of our Marp cards |
| `viewBackgroundColor` | `#0a0d12` (space) for dark; `#fafaff` (cream) for light | Mirrors our two canvases |
| Label colours | `#e6e8ee` body, `#cae3ff` soft labels; node strokes rotate the saber palette (blue/green/yellow/purple) for category coding | Multi-colour nodes + light text is the atlas signature |

**Palette mapping**: same Jedi tokens, hex-exact:

| Use | Hex | Token equivalent |
|---|---:|---|
| Primary stroke (Agent / "new way" / live) | `#4f8cff` | `--accent` / `--saber-blue` |
| Bright accent / arrow / energy line | `#4dbeff` | `--saber-blue-glow` |
| Secondary stroke (Mace / orbit) | `#7a59e2` | `--neural` / `--saber-purple` |
| Success / growth / "Yoda way" | `#46c98b` | `--circuit` / `--saber-green` |
| Highlight / sentinel | `#ffd93d` | `--voltage` / `--saber-yellow` |
| Muted stroke (de-emphasized / "old way") | `#4a5160` | `--grey-3` |
| Muted fill (dark canvas) | `#1a1d24` | `--grey-1` |
| Body text on dark | `#e6e8ee` | `--text` |
| Dim body on dark | `#9aa3b5` | `--text-muted` |
| Background: dark | `#0a0d12` | `--bg` |
| Background: light | `#fafaff` | `--bg-cream` |

**Sith Red rule still applies.** `#ff4d4d` only for error/destructive
elements: never for a regular "card 5 of 5" decorative accent.

**Pattern recipes:**

| Use case | Recipe |
|---|---|
| Old vs new comparison | Two rectangles, the "new" one with `#4f8cff` stroke at strokeWidth 3 and `#0f1729` fill; the "old" with `#4a5160` stroke at strokeWidth 2 and `#1a1d24` fill. Arrow between in `#4f8cff`. |
| Architecture flow (3-layer wiki, agent loop) | Boxes in `#181b22` fill, `#4f8cff` stroke, connected by `#4dbeff` arrows. Eyebrow labels in Cascadia. |
| Decision tree / conditional | Diamonds in `#0f1729` fill with `#7a59e2` stroke. Yes-branch → `#46c98b` arrow, no-branch → `#4a5160` arrow. |
| Annotation / pull quote | Short line at `#4f8cff` strokeWidth 4 + text in `#e6e8ee` |

**Example file:** [`diagrams/chat-vs-agent.excalidraw`](../../diagrams/chat-vs-agent.excalidraw),
the canonical "chat vs agent" comparison rebuilt in our palette.
Drag into [excalidraw.com](https://excalidraw.com) to open.

**Don't:** import a pictorial brand mark into a sketch. If ownership must be
shown, add the typographic Riverfed wordmark once, small and unobtrusive.

---

## 2. Slide types

Every slide picks ONE class from this list. Always use a class. Never use a
"plain default" slide.

| Class | Use for | Background | Type colour |
|---|---|---|---|
| `cover` | Title slide only | dark | white on dark |
| `lead` | Single statement, big idea, centered | cream | foundation |
| `section` | Module divider with section number | foundation (dark) | white |
| (none) | Default content slide | cream | foundation |
| `dark` | Content slide on dark for visual rhythm | bg-dark | white / grey-5 |

Use `<!-- _class: cover -->`, `<!-- _class: section -->`, etc.

For dividers, also add a section number as `<div class="section-num">02</div>`.

---

## 3. Reusable components

All defined in `themes/ai-builders.css`. Use these instead of inventing
new layouts.

### `.eyebrow`
Small uppercase tag above an H1. Sets context in 3–6 words.
```html
<p class="eyebrow">Module 1 · Foundations</p>
<h1>The mental models</h1>
```

### `.kpi`: three big numbers
For statistic-heavy slides. Each cell: big number + one-line label.
```html
<div class="kpi">
  <div><strong>132</strong><p>Tiny portfolio companies</p></div>
  <div><strong>$40K</strong><p>monthly Claude bill</p></div>
  <div><strong>2 wks</strong><p>to ship the platform</p></div>
</div>
```

### `.cards`: three or four cards
For genuinely parallel "the X pieces" slides. Cards use the composition's
single accent or a neutral rule by default. The modifiers `.is-neural`,
`.is-circuit`, `.is-fibre`, and `.is-voltage` are reserved for stable semantic
categories that are explained or already known; never rotate them for visual
variety. `.is-united` is error/destructive only.
```html
<div class="cards four">
  <div><span class="num">01</span><h3>…</h3><p>…</p></div>
  <div><span class="num">02</span><h3>…</h3><p>…</p></div>
  <div><span class="num">03</span><h3>…</h3><p>…</p></div>
  <div><span class="num">04</span><h3>…</h3><p>…</p></div>
</div>
```

### `.versus`: old vs new
Two panels with an arrow between. The "old" panel is muted grey, the
"new" panel has the accent border.
```html
<div class="versus">
  <div class="panel old"><h3>Then</h3>…</div>
  <div class="arrow">›</div>
  <div class="panel new"><h3>Now</h3>…</div>
</div>
```

### `.two-column`
50/50 split for parallel content. Use `.narrow` for 0.9 / 1.1.

### `.outcomes`: four-up strip at bottom
For "and the result is…" closers.
```html
<div class="outcomes">
  <div>Less waste</div><div>Faster cycle</div><div>Clearer ownership</div><div>Better reuse</div>
</div>
```

### `.callout`: dark pull-quote box
Big idea in a dark band against the cream slide.
```html
<div class="callout">
  <p><strong>Key shift:</strong> the deck source becomes clean text we can review, automate and reuse.</p>
</div>
```

### `.steps`: four sequential phases
For "the workflow" slides. Each step: number + heading + caption.
```html
<div class="steps">
  <div><span class="num">01</span><h3>Capture</h3><p>…</p></div>
  …
</div>
```

### `.six-up`: six-item grid (3×2)
For "the six concepts" / "six principles" slides. Smaller cards than
`.cards`, accent stripe on the left.

### `.icon-row`
Horizontal row of 3–5 icons only when the symbols improve recognition or
explain a system. "Texture" alone is not sufficient reason to add them.

### `blockquote`
For verbatim source quotes. The accent left-border makes them feel
authored, not decorative.

### `.cite`
Source slug citation at bottom-left. One per slide where a claim is
non-obvious. Monospaced.

---

## 4. Assets

Located in `wiki/training/assets/`. Brand-neutral AI/tech illustrations
borrowed from the Computacenter brandbook (generic enough to use across
projects, no Computacenter brand identity).

| File | Used for |
|---|---|
| `ai-atom.png` | Anything about agents, models, compute |
| `brain-spark.png` | Thinking, reasoning, decision |
| `brand-building.png` | Business, architecture, structure |
| `cloud-star.png` | Cloud, scale, distribution |
| `connected-nodes.png` | Networks, MCP, vault |
| `partnership.png` | Teams, collaboration, agent fleet |

**Usage:** prefer simple monochrome SVG / Lucide icons when an icon earns its
place. Use these PNGs only when the image communicates something the type and
layout cannot. There is no pictorial Riverfed logo asset for layouts; the square
mark is favicon-only.

---

## 5. Slide-budget rules

The handbook deck (`ai-builders-handbook.md`) targets **~30 slides**
total. Sub-decks target **8–15**.

For every slide, ask:
- **What's the single most important thing this slide says?** If you
  can't answer in one sentence, split the slide.
- **What's the hierarchy?** A visual can be a comparison, KPI, quote,
  diagram, deliberate type scale, or a single ruled structure. Do not add a
  card grid or icon merely to satisfy a visual quota. Pure bullet lists are a
  smell, but unnecessary decoration is also a smell.
- **Could a viewer in the back row read this?** If body text is more
  than 4 short bullets or 60 words, cut.

> **Rule of thumb:** if you find yourself writing a 5th bullet, you're
> writing the next slide. Split.

---

## 6. Voice

- **Direct, not academic.** Write "Agents handle the loop. You pick the
  metric." Avoid "Agents are autonomous systems that…"
- **Cite the source slug** for any non-obvious claim, in small mono at
  the bottom-left. Lets the viewer trace it back to the original
  transcript in `wiki/sources/`.
- **One concrete example per slide** beats three abstract claims.
- **No hedging.** "Maybe", "could", "possibly" weaken the deck. Either
  state it or remove it.

---

## 7. The build/render workflow

```powershell
cd wiki\training
marp ai-builders-handbook.md --html -o out\ai-builders-handbook.html
marp ai-builders-handbook.md --pdf  -o out\ai-builders-handbook.pdf
marp ai-builders-handbook.md --pptx -o out\ai-builders-handbook.pptx
```

Output goes to `wiki/training/out/` (gitignored if you version this).

The `.marprc.yml` next to the deck file sets the theme and allows
local-file inclusion (needed for images and the theme CSS).

### Native PPTX: the sibling renderer

Marp's `--pptx` exports a "flipbook" pptx where each slide is a
flattened image, so it is not editable. For a real editable pptx, we have a
parallel implementation in [`wiki/scripts/studio_pptx.py`](../scripts/studio_pptx.py):

```powershell
.venv\Scripts\python.exe wiki\training\scripts\build_handbook_pptx.py
```

It writes to `wiki/training/out/ai-builders-handbook-native.pptx` with
real text boxes, real shapes, embedded icon PNGs, and the documented deck
diamond on content slides.

The native renderer mirrors most components in section 3 above. Mapping:

| Marp class            | Native pptx slide type   | Notes                              |
|-----------------------|--------------------------|------------------------------------|
| `cover`               | `cover`                  | wordmark only; no pictorial logo |
| `lead`                | `lead`                   | Vertical accent bar + hero text    |
| `section`             | `section`                | Giant ghost numeral on right       |
| (default content)     | `content`                | Bullets + optional callout band    |
| `.kpi`                | `kpi`                    | 1-3 hero-number tiles              |
| (new)                 | `donut-kpi`              | 1-3 percentage ring charts         |
| `blockquote`          | `quote`                  | Giant decorative " + accent bar    |
| `.versus`             | `versus`                 | Two panels + center arrow          |
| `.cards`              | `cards`                  | 2-4 parallel siblings              |
| `.six-up`             | `six-up`                 | 3×2 grid catalogue                 |
| `.steps`              | `flow`                   | 3-5 sequential steps with arrows   |
| (new)                 | `timeline`               | 3-6 chronological milestones       |
| (new)                 | `hub`                    | Central concept + radial spokes    |

`flow`, `timeline`, `donut-kpi`, and `hub` are native-only (no Marp
equivalent yet). When you add a new Marp component, mirror it in
`studio_pptx.py` so the two renderers stay aligned.

---

## 8. How to extend

When you want a new deck:

1. **Copy `ai-builders-handbook.md`** as a starting point.
2. **Keep the cover + section + lead + dark slide types.** They are
   the visual rhythm of the system.
3. **Reuse the components** above before inventing new HTML. If you
   genuinely need a new pattern, add it to `themes/ai-builders.css` so
   it's reusable, then add a section here.
4. **Stay under the budget**: handbook ~30, sub-deck 8–15.
5. **Cite sources** at bottom-left where you make a claim.

If you ever want to fork the visual identity (different audience, different
palette), copy `themes/ai-builders.css` to a new file and override the
`:root` variables. The structural rules (slide types, components, type
scale) are deliberately portable.

---

## 9. What good looks like

A "good" slide in this system:

1. Has **one** big idea, expressed in the H1
2. Visualizes it with **one** component (card grid, comparison, KPI,
   quote, icon row, callout)
3. Cites its source if the claim is non-obvious
4. Has white space. The page does **not** feel full
5. Could stand alone on social media without explanation

A "bad" slide:

1. Has 6+ bullets
2. Looks like a Wikipedia paragraph that escaped onto a slide
3. Uses three colours for no reason
4. Has no visual at all, just title + bullets
5. Repeats what the previous slide said
6. Rotates blue, purple, green, and orange across peer cards without meaning
7. Adds glows, gradients, pills, icons, or shadows just to look "AI"

When in doubt: **fewer words, larger type, more breathing room**.
