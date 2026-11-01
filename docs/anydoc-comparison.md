# anydoc vs markitdown: office document conversion

**Test date:** 2026-08-06
**Converters:** firecrawl-anydoc 0.1.6 (`--converter anydoc`) vs markitdown (`--converter markitdown`), both via `convert.py`
**Verdict feeds:** `_OFFICE_PREFER_ANYDOC` in `convert.py` (the one-line default switch)

## TL;DR

Keep `_OFFICE_PREFER_ANYDOC = True`. On a real 36-slide native PowerPoint,
anydoc preserves within-slide reading order and emphasis while markitdown
scrambles multi-column slides into disassociated text and injects HTML-comment
junk. On a real Word document the two are at parity, with anydoc slightly
ahead (Title style becomes a real `#` heading, which also fixes the output
slug). Where anydoc has nothing to offer (flattened Marp exports), it returns
empty and `auto` mode falls back to markitdown exactly as designed.

## What was tested

Three real in-repo documents, both arms each:

```
.venv/bin/python convert.py <file> --converter anydoc     --out /tmp/ab/anydoc     --no-frontmatter --force
.venv/bin/python convert.py <file> --converter markitdown --out /tmp/ab/markitdown --no-frontmatter --force
```

1. `wiki/training/out/ai-builders-handbook-native.pptx` — 36-slide native deck
   (python-pptx generated: real text boxes, cards, KPI tiles, icons)
2. `wiki/training/out/riverfed-handbook-notes.docx` — speaker-notes Word doc
   (python-docx generated: Title style + 40+ headings + prose)
3. `wiki/training/out/riverfed-handbook-marp.pptx` — Marp-exported deck
   (flattened: each slide is one background image, no text shapes)

Plus regression guards: a PDF (`ai-builders-handbook.pdf`) and a corrupt
`.docx`. The PDF run never touches anydoc (its fallback chain is unchanged);
the corrupt file logs `[convert] anydoc failed: malformed document …` and
still converts via markitdown.

## Quantitative comparison

| Sample | Metric | anydoc | markitdown | Δ |
| --- | --- | --- | --- | --- |
| native pptx | bytes | 15,038 | 15,809 | −5% (comment junk removed) |
| native pptx | emphasis runs (`**…**`) | 216 | 0 | anydoc keeps title/eyebrow emphasis |
| native pptx | HTML comments | 0 | 36 (`<!-- Slide number -->`) | markitdown-only junk |
| native pptx | broken image refs | 0 (alt text inline) | 53 (`![…](Picture5.jpg)` — files don't exist) | markitdown-only junk |
| notes docx | bytes | 19,831 | 19,828 | parity |
| notes docx | headings | 42 | 41 | anydoc: Title style → `#` |
| marp pptx | output | (empty → falls back) | 40× `### Notes:` with zero content | both useless; anydoc honest |

## Qualitative analysis

**Native pptx — the decisive case.** markitdown walks shapes in XML order, so
a three-column module slide comes out as `MODULE 1 / MODULE 2 / MODULE 3 /
Foundations / Architecture / Build & Operate / <desc> / <desc> / <desc>` —
the module names are disassociated from their own descriptions, which is
poison for LLM ingestion (the agent has to guess which description belongs to
which module). anydoc groups each column: `MODULE 1 / Foundations / Six
mental models that change how you operate.` It also renders slide titles and
eyebrows in bold and inlines image alt text where the image sits.
Neither converter emits per-slide `#` headings for this deck (the native
renderer's title boxes aren't PowerPoint title placeholders) — not a
differentiator.

**Speaker-notes docx.** Byte-for-byte near-identical prose. Two real
differences, both anydoc wins: the Word Title style becomes a `#` heading
(markitdown demotes it to plain text), which also makes
`extract_title_from_md` pick the right title for the slug; and the trailing
newline is present.

**Marp-exported pptx.** No text exists in the file — every slide is a
flattened image. anydoc returns empty (logged as `[convert] anydoc found no
text in this document`) and `auto` falls back; markitdown "extracts" forty
empty `### Notes:` headings, which would pollute a wiki page with junk
structure. Marp decks should be ingested from their `.md` source anyway.

## Recommendation

`_OFFICE_PREFER_ANYDOC = True` stands (anydoc first under `--converter auto`,
markitdown as the recovery arm). Revisit only if a systematic anydoc
truncation mode shows up in real ingests — the switch is one line in
`convert.py`.

## Artifacts

Converted outputs were produced in the session scratchpad (`/tmp/ab/{anydoc,markitdown}`);
regenerate with the two commands above — conversion is deterministic.
