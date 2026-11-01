# `--frames` vs transcript-only: a real-world comparison

**Test date:** 2026-05-19
**Test subject:** *Building AI Agents that actually work (Full Course)* — Greg Isenberg / Remy Gaskell, 58:55, talking-head interview, YouTube id `eA9Zf2-qYYM`.

## TL;DR

Frame extraction + OCR cost a few minutes and ~1.2 MB on disk; for a **talking-head video** it added almost zero usable information, and the ingest agent correctly skipped it as a duplicate. **The system worked exactly as designed** — produced rich raw data, then the curating LLM judged the data unworthy and refused to pollute the wiki.

For this video specifically: **0 quality improvement**. The pipeline's value shows up on **slide- or code-heavy content** that we haven't yet stress-tested.

## What was tested

| Step | Without `--frames` (v1, 2026-05-11) | With `--frames` (v3, today) |
|---|---|---|
| 1. `convert.py` | ~30 sec — YouTube transcript only | ~4 min — transcript + 137 MB video download + ffmpeg frame extraction + Tesseract OCR |
| 2. `ingest.py` (Claude Code headless) | Produced `wiki/sources/building-ai-agents.md` | **Skipped — judged duplicate** by URL match + reasoned the new visual data was useless |
| 3. Wiki state after | 28 sources, dedicated page for this video | 28 sources — wiki unchanged, only `log.md` got a "Duplicate skipped" entry |

## Quantitative comparison

### Raw markdown output (`output/<slug>.md`)

| Metric | v1 (transcript only) | v3 (with `--frames`) | Δ |
|---|---:|---:|---:|
| Lines | 95 | 216 | **+121 (+127%)** |
| Bytes | 61,854 | 65,790 | **+3,936 (+6.4%)** |
| Sections | 4 (metadata, description, transcript, _that's it_) | 5 (same + new `## Visual content`) | +1 |
| Frame JPEGs on disk | 0 | 28 (1.2 MB total) | +28 |

The `+121 lines` is mostly markdown bookkeeping — one `### · t=mm:ss path/to/frame.jpg` header + one blockquote per frame. **The information density of the addition is very low.**

### Frame metadata (28 frames extracted)

The convert script uses chapter-aware timestamp picking. This video has 28 chapters, so each chapter got one frame; the cap is ≤30 per video.

| Vision flag | Count | What it means |
|---|---:|---|
| 🔍 vision-flagged | 3 | OCR returned ≥40 chars — Tesseract thinks something text-rich is on screen, worth re-reading as an image |
| · normal | 25 | OCR returned <40 chars or nothing meaningful |

| OCR result | Count | What landed in the .md |
|---|---:|---|
| `(no on-screen text)` | 22 | OCR returned trivially short / empty text |
| Some text captured | 6 | But all 6 are **garbled** — see qualitative section |

## Qualitative analysis — was the OCR usable?

**Short answer: no.** Every single one of the 6 frames where Tesseract returned text produced unusable output. Sample:

| Timestamp | What's actually on screen (inferred from context) | What OCR captured |
|---|---|---|
| 15:52 (`·`) | Browser/IDE UI chrome | `EP PP PP ee:` + `O©=8@Ceec*+anv7~+O8 680° °O =m.` |
| 34:49 (🔍) | App with tagline | `Let's knock something off your list` + icon garbage |
| 40:04 (`·`) | (mostly visual) | `tae ton 9 ened cme` |
| 43:08 (`·`) | UI icons | `©: 86Ce8¢+nev~O8 68G¢ °-O =` |
| 53:34 (🔍) | OpenClaw migration screen | `fae pean oe we cae` + 2 more illegible lines |
| 56:28 (🔍) | Final demo screen | `uid 2 minienaist portfolio se for Geog teenberg, Local hast on port 3111 for preview ence done.` ← clearly meant **"build a minimalist portfolio site for Greg Isenberg, localhost on port 3111 for preview once done."** |

**Pattern.** YouTube's overlay UI (likes, share, subscribe, video-progress icons, channel avatar) confuses Tesseract — it tries to read these icons as text and produces glyph-soup. Even at `--frame-width 1024` the screen text is too anti-aliased for clean OCR. Frame 27 is the **best result** and it's still a paraphrase, not a transcription.

## Quality improvement to the wiki

**Zero.** The existing `wiki/sources/building-ai-agents.md` (ingested 2026-05-11) is byte-identical after this test. The page already comprehensively covers:

- agents.md, memory.md as role + learned-rules markdown files
- MCPs (Gmail, Calendar, Stripe, Notion) as tool layer
- Skills as markdown SOPs
- Context engineering > prompt engineering
- "Same engine, different car" for Claude Code / Codex / OpenClaw / Antigravity / Manus / Cowork
- 3-5 new skills per week compounds to full-workflow automation

The 28 frames did not add any new factual claim, terminology, or framework that wasn't already captured from the transcript.

## What the ingest agent actually did — the smart part

This is where the new ingest system earned its keep. The pipeline:

1. `ingest.py` mounted the `-frames/` directory so Claude Code had **read access to all 28 JPEGs as images** (not just the OCR text)
2. Claude Code ran for 113.8 seconds, then wrote in `wiki/log.md`:

> Duplicate of `[[building-ai-agents]]` (same video ID `eA9Zf2-qYYM`, same title, same transcript). The `-3` file is a re-download with `--frames` enabled. 28 frames extracted but only 3 flagged vision-relevant; OCR output is garbled talking-head frames with no meaningful visual data (no slides, no code, no dashboards). The existing source page is comprehensive.
>
> **Action:** No new pages created. No existing pages updated.

Three judgments the agent made:

1. **URL-aware dedup** despite the file-stem dedup in `existing_source_slugs()` missing it. The agent compared the YouTube video ID and recognised the match.
2. **Vision-on-demand pass actually inspected the frames as images**, not just trusted the OCR text. That's how it confidently said "talking-head — no slides, no code, no dashboards."
3. **Do-no-harm.** Even with rich new raw data, the agent refused to pollute the wiki because the data didn't move any of the curated source page's claims.

This is the right architecture: **produce more raw signal than you need, let the curating LLM decide what to keep.**

## When `--frames` would actually pay off

The system has been **stress-tested only on a worst case** (talking-head interview). The cases where the test predicts real value:

| Content shape | Expected `--frames` payoff |
|---|---|
| Slide deck talks (eg. conference recordings) | **High** — slide text is a stable, OCR-friendly target. Each slide is a discrete claim the transcript may understate ("as you can see here" → slide has the actual numbers/names) |
| Code screencasts | **High** — actual code on screen rarely matches what the speaker reads aloud. Vision-on-demand pass can quote the code verbatim. Tesseract may still struggle; vision via Claude is the real win |
| Dashboard / tool demos | **Medium** — UI labels + KPI values that the speaker doesn't always say |
| Whiteboard / drawn diagrams | **Medium-high** — vision pass can read hand-drawn structure; OCR alone won't |
| Walking-and-talking podcast | **Zero** (this test) |
| Animated explainer with text overlays | **High** if the overlays carry the message |

## Cost summary

| Step | Cost |
|---|---|
| Video download | ~3 min wall, 137 MB transient (deleted after frame extraction) |
| Frame extraction (28 × ffmpeg seek-and-decode) | ~10 sec |
| OCR (28 × Tesseract) | ~30 sec |
| **Per-conversion total** | **~4 min wall, +1.2 MB committed on disk** |
| Ingest (Claude Code, with frames as images) | 113.8 sec — same order as a non-`--frames` ingest |

OCR text is essentially free; the cost is the video download. For videos that *are* slide- or code-heavy, this is cheap insurance for substantially richer source pages.

## Recommendation

1. **Default `--frames` to OFF** for talking-head content (interviews, podcasts, walking-and-talking).
2. **Default `--frames` to ON** for: conference talks (slides), screencasts (code/dashboards), animated explainers (text overlays).
3. **Trust the ingest agent's "skipped: duplicate"** verdicts — it's correctly conservative, and it's already logging its reasoning in `wiki/log.md`.
4. **Next stress test:** rerun this experiment on a slide-heavy video (e.g. `karpathys-autoresearch`, `googles-design-md`, or a fresh conference recording) to confirm the system *does* extract real value when the content shape is right.

## Artifacts

- Raw v1 markdown: `output/building-ai-agents-that-actually-work-full-course.md` (95 lines)
- Raw v3 markdown: `output/building-ai-agents-that-actually-work-full-course-3.md` (216 lines)
- Frames: `output/building-ai-agents-that-actually-work-full-course-3-frames/` (28 × ~40 KB JPEGs)
- Ingest log entry: `wiki/log.md` → "2026-05-19 — Duplicate skipped" section
- Existing wiki page (unchanged): `wiki/sources/building-ai-agents.md`

---

# Follow-up: dense sampling for hand-drawn diagrams (2026-05-19)

**User insight:** The first 20 minutes of the video has Excalidraw
whiteboard diagrams. Chapter-aligned frames hit the *start* of each
chapter where the canvas is blank — diagrams get populated mid-chapter.

## The fix: new flags + auto-flag

Added three flags to `convert.py`:

```
--dense-until SECS       Sample every --dense-interval seconds from 0
                         up to this timestamp. Default 0 (off).
--dense-interval SECS    Seconds between dense-sampled frames. Default 30.
--max-frames N           Cap on extracted frames. Default 30.
```

And one structural change to `extract_frames_and_ocr`:

- Each frame now carries a `source` field: `"dense" | "chapter" | "uniform"`.
- Frames where `source == "dense"` are **auto-flagged
  `vision_relevant=True`** regardless of OCR character count.
- Rationale: hand-drawn Excalidraw / whiteboard text reliably OCRs
  to gibberish (<50 chars), so the existing threshold drops them.
  But the user-supplied dense window is an explicit signal that
  visual content is expected there — trust the timestamp, not the OCR.

## The re-run

```powershell
convert.py "https://www.youtube.com/watch?v=eA9Zf2-qYYM" \
  --force --frames --frame-width 1024 \
  --dense-until 1200 --dense-interval 45 --max-frames 60
```

Output:

| Metric | v3 (no dense) | v2 (dense) | Δ |
|---|---:|---:|---:|
| Total frames | 28 | 42 | +14 |
| First-20min frames | 13 | 27 | **+14** (×2) |
| Vision-flagged (🔍) before patch | 3 | 3 | 0 |
| Vision-flagged after patch | 3 | **30** | +27 |
| Convert wall time | ~4 min | ~4 min | ≈ |
| Frame JPEGs on disk | 1.2 MB | 1.8 MB | +0.6 MB |

The OCR threshold caught only 3 vision-relevant frames in either run.
After the patch (now in `convert.py`), the 27 dense first-20min
frames all carry the 🔍 marker that tells the ingest agent to inspect
them as images.

## What was actually in those frames

Spot-check via `Read` (image) on six dense frames in the first 20 min:

| Frame | Time | What's on the Excalidraw board | Tesseract OCR returned |
|---|---|---|---|
| 007 | 04:30 | **The Agent Loop**: You → 1.OBSERVE → 2.THINK → 3.ACT → loop back (cycle) → "task complete" exit | `(no on-screen text)` |
| 009 | 06:00 | **4-component agent hub**: LLM / Loop / Tools / Context as co-equal pillars | `(no on-screen text)` |
| 013 | 09:00 | Antigravity IDE screencast (Gemini 3.1 Pro coding agent) | `(no on-screen text)` |
| 021 | 15:00 | **Folder hierarchy**: Workspace → AI with Remy / Client / Business → Exec Assistant / Head of Marketing / CFO per dept | `(no on-screen text)` |
| 023 | 16:30 | Claude chat session (Opus 4.6) discussing sub-agent diagrams | `(no on-screen text)` |
| 027 | 19:30 | **"No onboarding = bad employee"** before/after: empty `agents.md` → generic output | `“This thing do« anything about me”` (partial) |

**Three of these frames carry genuine new structural information** that the
existing wiki page does not capture:

1. **Frame 009** — the 4-component hub (LLM / Loop / Tools / Context as
   parallel components of every agent). The wiki mentions these scattered
   across bullets but never presents them as a unified architecture.
2. **Frame 021** — the department-based folder pattern (workspace per
   department, role-agents nested inside). The wiki says "onboard agents
   like employees" but doesn't describe the folder structure.
3. **Frame 027** — the "no onboarding = bad output" before-state. The wiki
   captures the conclusion ("rich `agents.md` → great output") but not
   the failure-mode visualization.

## What the default ingest still got wrong

Even with 30 frames flagged 🔍, the default ingest pipeline **still
skipped** the file. From `wiki/log.md`:

> 42 extracted frames yielded no usable OCR data (garbled talking-head
> captures). The existing source page comprehensively covers all
> content from this video.

That conclusion is **wrong** — the agent didn't actually `Read` the
JPEGs. It looked at the OCR text in the .md (gibberish), the
"duplicate URL" signal, and bailed early without inspecting any
frames as images.

## The targeted prompt that worked

To get the agent to actually look:

```
Read at least these 6 specific frames AS IMAGES (use the Read tool on
the .jpg paths directly): frame_007_t04-30.jpg, frame_009_t06-00.jpg,
frame_013_t09-00.jpg, frame_021_t15-00.jpg, frame_023_t16-30.jpg,
frame_027_t19-30.jpg.

For each: describe the diagram (the speakers-on-camera are the small
top-left corner; the Excalidraw is the large bright board taking ~80%
of the frame). Then check whether each diagram's structural content
is captured in wiki/sources/building-ai-agents.md.
```

Run took 150 sec, agent confirmed 3 of 6 diagrams add real new value.

## Lessons

1. **Dense sampling works** — it caught the populated diagram canvases
   that chapter-start frames missed.
2. **OCR is the wrong signal for hand-drawn content.** Tesseract +
   Excalidraw = gibberish. The OCR threshold (≥50 chars → 🔍) is fine
   for slides + code + dashboards but wrong for whiteboards.
3. **Auto-flagging dense frames is the right fix.** If the user
   explicitly asked for the dense window, they're telling the system
   "trust me, look here." `convert.py` now does this automatically.
4. **The ingest agent's "duplicate" short-circuit is too aggressive.**
   When the only thing that's different is the visual content, the
   agent should inspect at least one or two flagged frames before
   declaring "no new info." Currently it doesn't, and a targeted
   manual prompt is needed to get the diagrams extracted. This is
   the next thing to fix in `ingest.py`.
5. **Cost is still cheap.** Dense window added ~0.6 MB on disk and
   roughly the same wall-clock time as the non-dense run; the heavy
   cost is the YouTube video download (137 MB), not the frame
   extraction or OCR.

## Recommendation update

- **Default `--frames` to OFF** for talking-head content. (unchanged)
- **Use `--frames --dense-until 600-1800 --dense-interval 30-60`**
  for any video with whiteboard / Excalidraw / drawn diagrams that
  build up over time. The dense window covers the part where
  diagrams typically get populated.
- **Default `--frames` to ON** for slide decks, code screencasts,
  dashboards — and now also for whiteboard-heavy videos with a dense
  window.
- **Followup work needed:** patch `ingest.py` prompt so the agent
  always inspects ≥3 🔍 frames as images before declaring a re-conversion
  a "duplicate skip." Until that lands, manually run a targeted
  prompt when you suspect there's visual content the agent would
  benefit from extracting.

---

# Follow-up 2: dense sampling for screen-recordings, not just whiteboards (2026-06-02)

**Video:** "How I actually use Claude skills" (AI with Remy,
`sP3TyuB0Qo0`, 18:48). A screen-recording — Excalidraw teaching
diagrams *plus* Claude Desktop / VS Code / Finder screen captures. Not a
whiteboard talk, not a slide deck.

## Why it matters

The first pass was a **default ingest** (transcript only — the original
`--frames` run flagged the video talking-head and extracted 14 frames,
**0 vision-relevant**, so the agent never opened them). The resulting
wiki page was solid on the verbal content but had **zero** visual
specifics. This is the failure mode the dense window fixes — and it
proves the fix generalizes past hand-drawn diagrams.

Tesseract returns garbage on **two** kinds of content: hand-drawn
strokes (Excalidraw) *and* small typeset UI text in screen recordings
(file-tree sidebars, code panes, menu labels). Both score below the
50-char OCR threshold → flagged not-vision-relevant → skipped. So the
OCR-based heuristic is wrong for *any* screen-recording, not just
whiteboards.

## The re-run

```
convert.cmd "https://www.youtube.com/watch?v=sP3TyuB0Qo0" \
  --frames --frame-width 1024 --dense-until 1200 --dense-interval 45 --max-frames 60 --force
```

- Default run: 14 frames, 1 with OCR text, **0 flagged 🔍**.
- Dense run: **26 frames, all 26 flagged 🔍.** (`--force` was needed —
  the URL was already converted; without it convert.py skips.)

## What the frames carried that the transcript didn't

| Frame | New information (absent from narration) |
|---|---|
| t=00:45 | Three-pillars Excalidraw (Context/Tools/Skills) with colour coding + concrete per-pillar examples |
| t=02:15 | WITHOUT-vs-WITH skills flowchart — exact box text on both paths + bottom annotation |
| t=07:30 | **Global vs Project-Level skill scoping** — an entire second diagram never spoken aloud |
| t=08:15 | The full `.claude/skills/` library — **40+ folders**; transcript names <5 |
| t=06:00 | `ad-creative-analysis/SKILL.md` internals: bash calling `gemini-2.0-flash` via the Gemini Files API from inside the skill |
| t=10:30 | Orchestrator live run with a `PAUSE — wait for user to approve` human-in-the-loop gate |
| t=15:00 | `skill-creator` body with its `eval_runner/generate_evals.py` eval loop |

## Result

A `## Visual architecture` section (7 bullets, each frame-cited) plus
**3 promoted nodes** — concept `workflow-first-skills`, entities
`remy-gaskell` and `soul-md` — and cross-links into 18 existing pages.
Committed as `9e49616`.

## Lesson

Dense sampling is the right tool for **any screen-heavy video**, not
just whiteboards. The "is it talking-head?" heuristic should be the
*user's* call, not OCR's — which is why this is now a one-click option.

## Now wired into the UI (2026-06-02)

The `/` converter has a **"Deep visual capture"** checkbox (sub-option of
"Also capture on-screen text"). Checking it sends `dense: true`; the
server expands that to
`--frames --frame-width 1024 --dense-until 1200 --dense-interval 45 --max-frames 60`.
The label is explicit that it **spends more ingest tokens** (the agent
reads every frame as an image) but is worth it when the visuals carry
information the narration skips. No CLI needed for the common case.
