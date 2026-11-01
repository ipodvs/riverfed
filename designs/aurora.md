---
version: alpha
name: Aurora
description: >
  A bright-dawn palette with soft gradients, magenta and teal accents, generous
  curves. For product launches, marketing decks, conference
  keynotes and anywhere the message needs to feel optimistic and
  fresh.
colors:
  primary: "#FF3E9D"           # magenta: the optimistic driver
  primary-glow: "#FF7AC6"
  secondary: "#22D3EE"          # bright teal: the counter-accent
  success: "#34D399"            # mint: production / live
  highlight: "#FACC15"           # warm gold: call-out highlights
  warning: "#FB923C"             # amber
  error: "#F43F5E"               # rose: destructive only
  background: "#FDF4FF"          # palest lavender: fresh dawn
  background-elevated: "#FFFFFF"
  surface: "#FFFFFF"
  surface-cream: "#FCE7F3"       # pale pink for soft layered surfaces
  foundation: "#1E1B4B"           # midnight violet: dark text + section bg
  on-primary: "#FFFFFF"
  on-surface: "#1E1B4B"
  text-muted: "#64748B"
  text-faint: "#94A3B8"
typography:
  display:
    fontFamily: Sora
    fontSize: 4.5rem
    fontWeight: 700
    lineHeight: 0.95
    letterSpacing: -0.025em
  h1:
    fontFamily: Sora
    fontSize: 2.75rem
    fontWeight: 700
    lineHeight: 1.05
    letterSpacing: -0.02em
  h2:
    fontFamily: Sora
    fontSize: 1.5rem
    fontWeight: 600
    lineHeight: 1.25
  h3:
    fontFamily: Sora
    fontSize: 1.25rem
    fontWeight: 600
  body-md:
    fontFamily: Inter
    fontSize: 1rem
    fontWeight: 400
    lineHeight: 1.55
  eyebrow:
    fontFamily: JetBrains Mono
    fontSize: 0.75rem
    fontWeight: 600
    letterSpacing: 0.12em
  cite:
    fontFamily: JetBrains Mono
    fontSize: 0.6875rem
    fontWeight: 400
rounded:
  sm: 8px
  md: 16px
  lg: 24px
  pill: 9999px
spacing:
  xs: 4px
  sm: 10px
  md: 18px
  lg: 28px
  xl: 48px
components:
  card:
    backgroundColor: "{colors.background-elevated}"
    textColor: "{colors.on-surface}"
    rounded: "{rounded.md}"
    padding: 28px
  card-stripe:
    backgroundColor: "{colors.primary}"
    height: 6px
  pill:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.on-primary}"
    rounded: "{rounded.pill}"
    padding: 8px 18px
  cover-bg:
    backgroundColor: "{colors.foundation}"
    textColor: "{colors.background}"
  section-divider-bg:
    backgroundColor: "{colors.foundation}"
    textColor: "{colors.background}"
---

## Overview

Aurora is the optimistic counterpart to Riverfed and Heritage. Its
bright magenta-and-teal palette, soft pastel backgrounds, and chunky rounded
geometry. It signals "new, fresh, generous" and reads well in product
launch decks, marketing landing pages, and conference keynotes where the
mood needs to be expansive.

## Colors

A **two-accent system** unlike the default or Heritage's single-accent rule.
Magenta and teal share the spotlight, often in alternating cards or in a
gradient that bridges them.

- **Primary (#FF3E9D): magenta:** The headline accent. CTAs, kicker chips,
  the dominant visual mass.
- **Secondary (#22D3EE): bright teal:** The counter-accent. Use it on the
  second card in a row, the alternating step in a flow.
- **Highlight (#FACC15): warm gold:** Reserved for the *one* most important
  number on a slide. Not a rotation colour.
- **Foundation (#1E1B4B): midnight violet:** Dark text on the pale lavender
  background; flip to background on section dividers for high contrast.

## Typography

**Sora** is used for all display + headings. It is a geometric sans with a friendly
warmth at heavy weights. **Inter** for body (workhorse legibility).
**JetBrains Mono** for kickers and citations.

Display tightens letter-spacing aggressively (-0.025em) so the big
headlines read confident and self-contained.

## Layout

Generous rounding: 16-24px on cards, full pill on chips. Stripes on
capped cards are 6px thick (vs 3-4 elsewhere) for the warmth Aurora
needs. Cards have soft shadows (blur 14pt, alpha 18%) that lift them
off the lavender background without going heavy.

## Components

KPI tiles often use **gradient text** for the value (magenta → teal).
Section dividers flip the palette to the midnight foundation with the
chapter number set in magenta-to-teal gradient.

## Do's and Don'ts

- **Do** use magenta and teal as a pair. The system is designed for
  duotone alternation, not single-accent restraint.
- **Do** trust the gradients. Magenta → teal at 135° is the signature.
- **Don't** drop the rounding. Square corners kill the friendly register.
  Stay at 8-24px even on small chips.
- **Don't** add a third bright accent. Yellow is a highlight (one per slide),
  not a rotation colour. Use the warm gold sparingly.
