---
version: alpha
name: Riverfed
description: >
  Deep-space dark + Riverfed green accent. The house identity for generated
  artifacts: one green accent over neutrals, with Inter for display and body
  and JetBrains Mono for project labels. Used in the AI Builders Handbook and
  every internal training deck.
colors:
  primary: "#46c98b"          # Riverfed deck green · the one accent (design.md: decks
                              # use this rather than the #1d9e66 brand dot, which is
                              # tuned for light surfaces)
  secondary: "#6c7278"        # slate · a stable NODE KIND in diagrams and the
                              # comparison colour on versus slides. Deliberately
                              # neutral: design.md forbids blue+purple as a generic
                              # "AI" signal, and a second bright accent reads as
                              # decorative rotation.
  success: "#1d9e66"          # Riverfed brand green, deeper: distinct from the
                              # accent while keeping success semantically green
  highlight: "#ffd93d"         # voltage · Sentinel yellow + Star Wars logo gold
  warning: "#ff6b35"           # fibre · Tatooine sunset
  error: "#ff4d4d"             # united · Sith red (errors ONLY: see Don'ts)
  background: "#0a0d12"        # bg-dark · deep space
  background-elevated: "#181b22"
  surface: "#fafaff"           # bg-cream · default light canvas
  surface-cream: "#f5f0e6"     # Jedi-robe warm cream
  foundation: "#0f1729"        # primary text + section divider bg
  on-primary: "#ffffff"
  on-surface: "#0f1729"
  text-muted: "#9aa3b5"
  text-faint: "#6e7686"
typography:
  display:
    fontFamily: Inter
    fontSize: 4.25rem
    fontWeight: 700
    lineHeight: 0.96
    letterSpacing: -0.01em
  h1:
    fontFamily: Inter
    fontSize: 2.5rem
    fontWeight: 700
    lineHeight: 1.05
    letterSpacing: -0.01em
  h2:
    fontFamily: Inter
    fontSize: 1.5rem
    fontWeight: 500
    lineHeight: 1.2
  h3:
    fontFamily: Inter
    fontSize: 1.125rem
    fontWeight: 700
    lineHeight: 1.2
  body-md:
    fontFamily: Inter
    fontSize: 1rem
    fontWeight: 400
    lineHeight: 1.5
  eyebrow:
    fontFamily: JetBrains Mono
    fontSize: 0.6875rem
    fontWeight: 700
    letterSpacing: 0.14em
  cite:
    fontFamily: JetBrains Mono
    fontSize: 0.625rem
    fontWeight: 400
rounded:
  sm: 4px
  md: 8px
  lg: 10px
  pill: 9999px
spacing:
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 40px
components:
  card:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.on-surface}"
    rounded: "{rounded.sm}"
    padding: 24px
  card-stripe:
    backgroundColor: "{colors.primary}"
    height: 4px
  pill:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.on-primary}"
    rounded: "{rounded.pill}"
    padding: 6px 14px
  cover-bg:
    backgroundColor: "{colors.background}"
    textColor: "{colors.on-primary}"
  section-divider-bg:
    backgroundColor: "{colors.foundation}"
    textColor: "{colors.on-primary}"
---

## Overview

Riverfed is a training brand for AI operators. The visual language is
deep-space dark with one green accent per slide. It evokes a terminal at night with one editor window open. The mood is
focused, deliberate, and slightly cinematic.

## Colors

Colours are named for **what they do in a layout** (`primary`, `secondary`,
`surface`). The rule is one accent over neutrals; a second colour has to earn
its place by carrying a stable meaning.

- **Primary (#46c98b): Riverfed deck green:** The one accent for kickers,
  buttons, callouts, the lead cell in any rotation. This is the dark-surface
  twin of the `#1d9e66` brand dot, which is tuned for light backgrounds.
- **Secondary (#6c7278): slate:** Deliberately neutral. It carries a stable
  node kind in diagrams and the "before / other" side of a comparison, never
  decoration on the next card. A second *bright* accent here is how a deck
  starts looking generated, and blue+purple in particular is banned outright
  by design.md's anti-slop contract.
- **Success (#1d9e66): brand green, deeper:** Production, live, passing.
  Distinct from the accent while keeping success semantically green.
- **Highlight (#ffd93d): amber:** Highlights only, never a primary surface.
- **Error (#ff4d4d): Sith red:** Errors and destructive actions *only* (see
  Don'ts).

## Typography

Inter is the Riverfed display, heading, and body family. JetBrains Mono is
reserved for eyebrow kickers, citations, code, paths, and compact technical
metadata. Do not introduce a third family into a Riverfed artifact. Office exports keep these canonical names; install both
families for exact rendering, with Aptos and Consolas serving only as local
substitution fallbacks when the brand fonts are unavailable.

The wordmark is fixed: `Riverfed` in Inter 900 with tight tracking, followed
by the green signature dot. Studio design selection never overrides it.

Hero text loosens to 0.96 line-height and tightens letter-spacing by -0.01em.
Body stays at 1.5 line-height for comfortable reading.

## Layout

16:9 widescreen for decks (13.333 × 7.5 inches in native pptx). Hierarchy
comes from type, spacing, solid fills, and hairline rules. Cards do not float
by default. Prefer a 1px border and no shadow. Use a shadow only when depth is
real (for example, a transient overlay). Accent stripes are solid, not
decorative gradients.

## Components

| Slide-type vocabulary | Use for |
|---|---|
| cover, lead, section | Identity / openers |
| content, quote | Workhorse text |
| kpi, donut-kpi | Hero numbers |
| versus, hub | Comparisons + part-of-whole |
| cards, six-up | Collections |
| flow, timeline | Sequential / chronological |

Every content-style slide gets a small ambient diamond ◆ top-right in the
accent green: the deck's one documented ambient signature. Do not introduce
additional dots, sparkles, halos, orbit shapes, or floating decoration.

## Anti-AI-slop rules

- One accent per slide. A second colour needs a named semantic role.
- Never pair blue and purple merely to make a slide read as "AI."
- No ambient glow, blue-purple gradient, scattered-dot field, or neon shadow.
- Do not turn every idea into a rounded card. Try a ruled list, shared outer
  boundary, table, timeline, or whitespace first.
- Do not add an icon only to fill a corner. Icons must improve recognition or
  explain an action/system.
- `pill` geometry is for compact tags and segmented controls only. Buttons,
  search fields, and content panels use 6–10px corners.
- Motion must communicate state or causality; no decorative reveal animation.
- Multi-colour diagrams are allowed when colours encode node kinds or paths
  and the meaning is consistent or explained by a legend.
- Never use em dashes (`U+2014`, including the equivalent HTML entity).
  Rewrite the thought with a sentence break, comma, colon, or parentheses.

## Do's and Don'ts

- **Do** stick to one accent per slide. A card row is not automatically a
  contrasting case; use multiple colours only for stable semantic categories.
- **Do** use the typographic Riverfed wordmark on the cover and nowhere
  else. Never use a pictorial logo in a layout.
- **Don't** use Sith red (`#ff4d4d`) for decorative "card 5 of 5" cycling.
  Red is the error/destructive colour. Use a neutral rule or numbering if you
  only need differentiation.
- **Don't** invent new HTML components inside a Marp deck. The reusable
  classes (`.cards`, `.kpi`, `.versus`, `.callout`, `.six-up`, `.steps`,
  `.outcomes`) cover every layout in the system.
