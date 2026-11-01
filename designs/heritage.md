---
version: alpha
name: Heritage
description: >
  Architectural Minimalism meets Journalistic Gravitas. Deep ink
  headlines, warm limestone backgrounds, a single clay-tone accent.
  For decks that want to read like a premium broadsheet or a
  contemporary gallery catalogue.
colors:
  primary: "#1A1C1E"           # deep ink: headlines, core text
  primary-glow: "#1A1C1E"
  secondary: "#6C7278"         # sophisticated slate: captions, metadata
  success: "#4A6B3E"           # muted moss: subtle confirmations
  highlight: "#B8422E"         # Boston Clay: the SINGLE accent
  warning: "#B8422E"
  error: "#922A1A"             # deeper clay: destructive only
  background: "#F7F5F2"        # warm limestone: softer than pure white
  background-elevated: "#FFFFFF"
  surface: "#F7F5F2"
  surface-cream: "#EFEAE2"     # darker stone for layered surfaces
  foundation: "#1A1C1E"
  on-primary: "#F7F5F2"
  on-surface: "#1A1C1E"
  text-muted: "#6C7278"
  text-faint: "#9A9D9F"
typography:
  display:
    fontFamily: Public Sans
    fontSize: 3.75rem
    fontWeight: 700
    lineHeight: 1.0
    letterSpacing: -0.02em
  h1:
    fontFamily: Public Sans
    fontSize: 3rem
    fontWeight: 700
    lineHeight: 1.1
    letterSpacing: -0.015em
  h2:
    fontFamily: Public Sans
    fontSize: 1.5rem
    fontWeight: 500
    lineHeight: 1.3
  h3:
    fontFamily: Public Sans
    fontSize: 1.125rem
    fontWeight: 600
  body-md:
    fontFamily: Public Sans
    fontSize: 1rem
    fontWeight: 400
    lineHeight: 1.55
  eyebrow:
    fontFamily: Space Grotesk
    fontSize: 0.75rem
    fontWeight: 600
    letterSpacing: 0.18em
  cite:
    fontFamily: Space Grotesk
    fontSize: 0.6875rem
    fontWeight: 400
rounded:
  sm: 2px
  md: 4px
  lg: 6px
  pill: 9999px
spacing:
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 48px
components:
  card:
    backgroundColor: "{colors.background-elevated}"
    textColor: "{colors.on-surface}"
    rounded: "{rounded.sm}"
    padding: 28px
  card-stripe:
    backgroundColor: "{colors.highlight}"
    height: 3px
  pill:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.background}"
    rounded: "{rounded.sm}"
    padding: 4px 12px
  cover-bg:
    backgroundColor: "{colors.background}"
    textColor: "{colors.foundation}"
  section-divider-bg:
    backgroundColor: "{colors.foundation}"
    textColor: "{colors.background}"
---

## Overview

Heritage evokes a premium matte broadsheet with wide margins, restrained
type, a single warm accent. It's the right choice for decks that need
gravitas: investor memos, brand-history retrospectives, editorial
features, museum catalogues.

## Colors

The palette is rooted in **high-contrast neutrals and one accent**.

- **Primary (#1A1C1E):** Deep ink for headlines and core text.
- **Secondary (#6C7278):** Sophisticated slate for borders, captions, metadata.
- **Highlight (#B8422E): "Boston Clay":** The sole driver for interaction.
  CTAs, link underlines, accent rules. Use exactly one.
- **Background (#F7F5F2): Warm limestone:** A foundation softer than pure
  white. The deck breathes against it.

## Typography

**Public Sans** for everything except the small all-caps eyebrows and
captions, which use **Space Grotesk** with wide letter-spacing for a
typographic counter-rhythm. Pair: Public Sans is workhorse-neutral;
Space Grotesk's geometric kicker keeps the layout from going too quiet.

Display sets at -0.02em letter-spacing so the largest sizes read
architectural rather than narrative.

## Layout

Generous outer padding (48px on lg). Cards have a soft hairline border
instead of a shadow. Depth is implied by spacing, not lighting.

## Components

Minimal corner radius (2-6px). Stripes on capped cards are thin (3px) and
sit in the Boston Clay accent. Pills are square-cornered chips, not
capsules. The geometry matches the architectural register.

## Do's and Don'ts

- **Do** treat Boston Clay as scarce. One accent per slide; one CTA per
  view; if everything is highlighted, nothing is.
- **Do** lean on whitespace. Heritage's signature is the breathing room.
- **Don't** introduce additional accents. The palette is intentionally
  thin. The editorial gravitas comes from restraint, not range.
- **Don't** use drop shadows on cards. The shadow on a Heritage card is
  the surrounding negative space, not blurred geometry.
