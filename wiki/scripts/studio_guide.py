#!/usr/bin/env python3
"""Studio: generate a speaking guide for a deck or a diagram.

Companion to studio_marp.py and studio_diagram.py — runs AFTER one of
those produces a deck/diagram, and writes a presenting guide next to it.

Output naming:
  wiki/training/studio/<name>.md         → wiki/training/studio/<name>-speaker-notes.md
  diagrams/studio/<name>.excalidraw      → diagrams/studio/<name>-presenting-notes.md

Usage (from repo root):
    py -3.13 wiki/scripts/studio_guide.py \\
        --wiki wiki \\
        --target wiki/training/studio/my-deck.md \\
        --audience "Operators who already use AI agents"
"""
from __future__ import annotations
import argparse
import sys
from pathlib import Path

# The provider layer, imported at module level because the
# --provider help text is built from it during argparse setup.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import agent_runner  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent.parent
DESIGN_MD_REL = "wiki/training/design.md"
EXAMPLE_NOTES_REL = "wiki/training/ai-builders-handbook-speaker-notes.md"


def detect_kind(target: Path) -> str:
    if target.suffix == ".md":
        return "deck"
    if target.suffix == ".excalidraw":
        return "diagram"
    if target.suffix == ".pptx":
        return "deck-pptx"
    raise SystemExit(f"Error: unsupported target type: {target.suffix}")


def out_path_for(target: Path, kind: str) -> Path:
    stem = target.stem
    if kind == "diagram":
        suffix = "-presenting-notes"
    else:
        suffix = "-speaker-notes"
    return target.parent / f"{stem}{suffix}.md"


def build_prompt_deck(target_rel: str, audience: str, out_rel: str) -> str:
    return f"""You are the Riverfed studio agent. Generate a speaker
manual for the Marp deck at `{target_rel}`.

Requirements:
- Read the deck. For each slide, write one section:
  - Slide N · <slide title>
  - The hook (one line — how to land the slide in the room)
  - The main beat (2-4 sentences — the substance the audience must
    leave with)
  - Anticipated Q&A (1-2 likely audience questions + concise answers,
    or "None" if the slide is self-contained)
- Voice: direct, concrete, no hedging. Cite the wiki source slug at
  the end of any non-obvious claim (e.g. "see sources/building-ai-agents").
- Look at `{EXAMPLE_NOTES_REL}` for tone and structure.
- Audience: {audience}.
- Read `{DESIGN_MD_REL}` for the brand voice rules in section 6.

Write the final speaker manual to `{out_rel}`. Do not output anything
else to stdout. When done, print a single line:
  WROTE {out_rel}
"""


def build_prompt_pptx(target_rel: str, sidecar_rel: str | None,
                       audience: str, out_rel: str) -> str:
    """Native PowerPoint speaker manual. Same shape as the Marp version,
    but reads the slide structure from the .pptx.json sidecar that
    studio_pptx.py left next to the .pptx (the .pptx itself is a binary
    zip — much easier to read the JSON we already have)."""
    sidecar_note = (
        f"- The structured slide data lives in `{sidecar_rel}` (sibling of\n"
        f"  the .pptx). Read that JSON to see each slide's type, title,\n"
        f"  bullets, kpis, quote, etc. — it's the source of truth.\n"
    ) if sidecar_rel else (
        "- The .pptx itself is a binary zip; if no JSON sidecar exists,\n"
        "  use python-pptx to read slide contents (less reliable).\n"
    )
    return f"""You are the Riverfed studio agent. Generate a speaker
manual for the native PowerPoint deck at `{target_rel}`.

Requirements:
{sidecar_note}- For each slide in the deck (in order), write one section:
  - Slide N · <slide title from the JSON>
  - The hook (one line — how to land the slide in the room)
  - The main beat (2-4 sentences — the substance the audience must
    leave with; reference the actual content of bullets/kpis/quotes)
  - Anticipated Q&A (1-2 likely audience questions + concise answers,
    or "None" if the slide is self-contained)
- Voice: direct, concrete, no hedging. Cite the wiki source slug at
  the end of any non-obvious claim (the JSON's `cite` field is the
  hint).
- Look at `{EXAMPLE_NOTES_REL}` for tone and structure.
- Audience: {audience}.
- Read `{DESIGN_MD_REL}` section 6 for the brand voice rules.

Write the final speaker manual to `{out_rel}`. Do not output anything
else to stdout. When done, print a single line:
  WROTE {out_rel}
"""


def build_prompt_diagram(target_rel: str, audience: str, out_rel: str) -> str:
    return f"""You are the Riverfed studio agent. Generate a 1-page
presenting guide for the Excalidraw diagram at `{target_rel}`.

Requirements:
- Read the diagram JSON to understand its structure (elements, labels,
  what each part shows).
- Write a presenting guide with this structure:
  - **Context** — what concept does this diagram capture, why does it
    matter (2-3 sentences)
  - **The walkthrough** — how to talk through the diagram in order:
    which element to point to first, then next, etc. Numbered 1-5,
    each step one sentence
  - **Three takeaways** — the points the audience should leave with
  - **Anticipated Q&A** — 1-2 likely audience questions + concise answers
- Voice: direct, concrete, no hedging. Cite a wiki source slug if a
  claim is non-obvious.
- Audience: {audience}.

Write the final guide to `{out_rel}`. Do not output anything else to
stdout. When done, print a single line:
  WROTE {out_rel}
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--wiki", required=True)
    ap.add_argument("--target", required=True,
                    help="Path (relative or absolute) to the deck .md "
                         "or diagram .excalidraw")
    ap.add_argument("--audience", default="Operators who already use AI agents")
    ap.add_argument("--design", default=None,
                    help="Optional design.md path. The speaker notes are also "
                         "rendered to a styled Word .docx using this design's "
                         "palette + fonts (falls back to the default house "
                         "palette if omitted).")
    ap.add_argument("--provider", default="auto",
                    help=agent_runner.provider_arg_help(
                        "run this generation on"))
    args = ap.parse_args()

    target = Path(args.target)
    if not target.is_absolute():
        target = (ROOT / target).resolve()
    if not target.exists():
        print(f"Error: target not found: {target}", file=sys.stderr)
        return 1
    try:
        target_rel = target.relative_to(ROOT).as_posix()
    except ValueError:
        print(f"Error: target must be inside the repo: {target}", file=sys.stderr)
        return 1

    kind = detect_kind(target)
    out = out_path_for(target, kind)
    out.parent.mkdir(parents=True, exist_ok=True)
    out_rel = out.relative_to(ROOT).as_posix()

    if kind == "deck":
        prompt = build_prompt_deck(target_rel, args.audience, out_rel)
    elif kind == "deck-pptx":
        sidecar = target.with_suffix(".pptx.json")
        sidecar_rel = sidecar.relative_to(ROOT).as_posix() if sidecar.exists() else None
        prompt = build_prompt_pptx(target_rel, sidecar_rel, args.audience, out_rel)
    else:
        prompt = build_prompt_diagram(target_rel, args.audience, out_rel)

    # Agent invocation goes through the provider layer (A6 step 1).
    provider, pstatus = agent_runner.resolve_provider(args.provider)
    if provider is None:
        print(f"Error: {agent_runner.unavailable_message(pstatus)}",
              file=sys.stderr)
        return 2

    print(f"[studio_guide] generating guide for {kind}: {out_rel}",
          file=sys.stderr)
    try:
        res = agent_runner.run(prompt, cwd=ROOT, timeout=600,
                               add_dirs=[ROOT], provider=provider)
    except FileNotFoundError:
        print(f"Error: the {provider} CLI could not be executed.",
              file=sys.stderr)
        return 2
    if res.timed_out:
        print("Error: guide generation timed out after 10 minutes.",
              file=sys.stderr)
        return 3

    if res.returncode != 0:
        sys.stderr.write(res.stderr or "")
        return res.returncode

    if not out.exists():
        print(f"Error: agent did not write {out_rel}", file=sys.stderr)
        sys.stderr.write(res.output or "")
        return 4

    # Render the speaker notes to a styled Word .docx using the chosen design.
    # Best-effort: if python-docx or the renderer fails, we still return the
    # .md (the docx is an extra deliverable, not a hard requirement).
    docx_rel: str | None = None
    try:
        from speaker_docx import render_markdown_to_docx
        docx_out = out.with_suffix(".docx")
        written = render_markdown_to_docx(out, docx_out, design_path=args.design)
        docx_rel = written.relative_to(ROOT).as_posix()
        print(f"[studio_guide] wrote Word doc: {docx_rel}", file=sys.stderr)
    except Exception as exc:
        print(f"[studio_guide] Word .docx render skipped: {exc}", file=sys.stderr)

    # Stdout contract: zero or more `RENDERED:<fmt>:<rel>` lines, then the
    # primary deliverable as the LAST line. When the docx rendered, it's the
    # headline output; otherwise the .md is.
    print(f"RENDERED:md:{out_rel}")
    if docx_rel:
        print(f"RENDERED:docx:{docx_rel}")
        print(docx_rel)
    else:
        print(out_rel)
    return 0


if __name__ == "__main__":
    sys.exit(main())
