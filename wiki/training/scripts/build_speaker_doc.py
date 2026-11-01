"""Convert the handbook speaker-notes markdown into a styled Word document.

Reads `wiki/training/ai-builders-handbook-speaker-notes.md` and writes
`wiki/training/out/ai-builders-handbook-speaker-notes.docx` using the
AI Builders brand palette (the default house palette).

The Markdown -> DOCX rendering now lives in the shared, design-aware module
`wiki/scripts/speaker_docx.py` (the Studio's speaker-guide generator uses
the same renderer with a chosen design.md). This script is a thin wrapper
that pins the handbook's title/eyebrow and the default palette.

Run from anywhere:
    py -3.13 wiki/training/scripts/build_speaker_doc.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Force UTF-8 stdout on Windows so arrows / em-dashes don't crash.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "wiki" / "training" / "ai-builders-handbook-speaker-notes.md"
OUT_DIR = ROOT / "wiki" / "training" / "out"
DEST = OUT_DIR / "ai-builders-handbook-speaker-notes.docx"

sys.path.insert(0, str(ROOT / "wiki" / "scripts"))
from speaker_docx import render_markdown_to_docx  # noqa: E402


def main() -> int:
    if not SRC.exists():
        sys.stderr.write(f"Error: source not found: {SRC}\n")
        return 1

    print(f"Reading: {SRC}")
    # design_path=None -> the default house palette (matches the deck theme).
    written = render_markdown_to_docx(
        SRC, DEST,
        design_path=None,
        eyebrow="THE AI BUILDERS HANDBOOK",
        title="AI Builders Handbook — Speaker's Manual",
        subtitle="Companion script for the 30-slide deck",
    )
    print(f"Writing:  {written}")
    print(f"Done. {written.stat().st_size:,} bytes.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
