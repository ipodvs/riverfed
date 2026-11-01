---
name: convert-and-ingest
description: >
  Add a YouTube video or a file to the Riverfed wiki — convert it to a
  transcript, then ingest it into wiki/sources + topics/entities/concepts. Use
  this whenever the user wants to "add a video", "ingest this", "convert this
  YouTube link", "put this in the wiki", drops a URL/PDF/file to process, or
  asks why something isn't showing as pending or won't ingest. Covers the
  frame-capture decision (when to use --frames / Deep visual capture), the
  single-flight ingest rule, and how "pending" is actually detected.
---

# Convert & ingest into the wiki

The pipeline is two steps, deliberately separate:

```
YouTube URL / file → convert.py → output/<slug>.md → ingest.py → wiki/*
```

`convert.py` only makes the transcript. `ingest.py` (Codex headless)
reads it and writes the wiki pages. Converting does **not** auto-ingest.

## Step 0 — Pick (or create) the knowledge base

The **Knowledge base** bar at the top of `/` scopes everything on the page
— convert target, pending list, ingest, review, output listing. **+ New**
scaffolds a fresh base (e.g. "Investing") at `wikis/<slug>/` with its own
isolated `output/` staging. On the CLI, every wiki script takes
`--wiki <slug>` (default `wiki` = the original base):

```powershell
py -3.13 wiki\scripts\ingest.py  --wiki investing
py -3.13 wiki\scripts\pending.py --wiki investing
```

A conversion staged in one base will never show as pending in another.

## Step 1 — Convert (pick the right frame flags)

Frames matter because the OCR-based "is there visual content" heuristic is
wrong for hand-drawn and small-UI-text content — so the *user's* intent (the
flags) is the signal, not OCR. Choose by what the video actually shows:

| Content shape | Flags | Why |
|---|---|---|
| Talking-head / podcast | *(none)* | Audio transcript is the whole story |
| Slide deck / conference talk | `--frames --frame-width 1024` | Slides OCR well |
| Code screencast / terminal | `--frames --frame-width 1024` | Capture code/commands |
| **Whiteboard / Excalidraw** | `--frames --frame-width 1024 --dense-until 1200 --dense-interval 45 --max-frames 60` | Diagrams build up mid-chapter; dense window catches the populated canvas |
| **Screen-recording (UI tour / file-tree / editor)** | same as whiteboard | Small UI text OCRs to gibberish too — dense + 🔍-flag everything |

```powershell
convert.cmd "https://www.youtube.com/watch?v=..."                 # talking-head
convert.cmd "..." --frames --frame-width 1024                     # slides/code
convert.cmd "..." --frames --frame-width 1024 --dense-until 1200 --dense-interval 45 --max-frames 60   # whiteboard/screen-rec
```

In the **web UI** (`/`), the dense flag-set is the **"Deep visual capture"**
checkbox (a sub-option of "Also capture on-screen text"). It costs more
ingest tokens (the agent reads every frame as an image) but captures
diagrams/UI the narration skips — worth it for whiteboard/screen-recordings.

**Re-converting an existing video?** Add `--force` — convert.py skips a URL
that already produced an output file otherwise.

## Converting a file (not a video)

Drop it on **Add**, or `convert.cmd report.docx`. Office documents
(docx/pptx/xlsx/odt/rtf/epub + variants) convert through **anydoc** first —
grouped slide reading order, real headings — with markitdown as the automatic
fallback; the job log says which ran (`[convert] converted via anydoc`).
Force an engine with `--converter anydoc|markitdown` (an explicit pick
hard-fails instead of silently falling back). PDFs keep their own
pdfplumber -> pypdfium2 -> OCR chain. Evidence:
[`docs/anydoc-comparison.md`](../../../docs/anydoc-comparison.md).

## Step 2 — Ingest

- **Web UI**: open `/`, click **Ingest pending** under the Wiki section.
- **CLI**: `py -3.13 wiki\scripts\ingest.py` (add `--dry-run` to preview).

Ingest and review share one serialized job lane — a second click **queues**
behind the first instead of running concurrently (concurrent runs used to
deadlock). Each transcript takes 3–8 minutes; the status box polls the job
and shows a live log tail, so a quiet minute at the start is normal (Codex
is reading the schema + corpus before it prints anything).

## Step 3 — Verify

```powershell
py -3.13 wiki\scripts\pending.py        # should drop the video off the list
```

"Pending" is matched by **video id** (the `url:` and `alt_url:` in each
source page), not filename. So:
- A re-conversion (`<slug>-2.md`) of an already-ingested video is **not**
  pending — it's a duplicate the agent already handled.
- A re-upload with a new SEO title gets **merged into the existing page via
  `alt_url:`** — also not pending.
- If a video genuinely isn't in the wiki, it *will* show as pending.

So "Wiki is up to date" with a video you just added usually means it was
already ingested (often merged), **not** that it was skipped. Confirm by
checking `wiki/sources/` for a page whose `url:`/`alt_url:` matches the
video id (`watch?v=XXXX`).

## When it looks stuck

If "Ingesting…" spins forever or the site won't load, use the
**server-recovery** skill — don't kill processes blindly.

## References (read on demand)

- [`AGENTS.md`](../../../AGENTS.md) — full command reference + gotchas
- [`docs/frames-ingest-comparison.md`](../../../docs/frames-ingest-comparison.md)
  — empirical proof of when dense frames pay off (whiteboard + screen-recording cases)
- [`wiki/SCHEMA.md`](../../../wiki/SCHEMA.md) — page schema + slug conventions
