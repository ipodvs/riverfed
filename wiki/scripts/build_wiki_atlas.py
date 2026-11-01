#!/usr/bin/env python3
"""Build diagrams/wiki-atlas.excalidraw from the current wiki state.

A one-page poster of the knowledge base, in editable Excalidraw JSON so it
can be opened at excalidraw.com and tweaked.

EVERYTHING is read live: the counts, the top concepts and their evidence
weights, every topic, and the most recently ingested sources. It used to be
a hardcoded snapshot from 2026-05-12 with only the four headline counts
live, which meant the cards confidently displayed evidence numbers that had
since more than doubled, and named sources that no longer existed.

Colour encodes the layer of the knowledge model, which is the one case
design.md allows multiple colours in a diagram: concepts accent green,
topics deeper green, entities amber, sources neutral slate.

Usage (from repo root):
    py -3.13 wiki/scripts/build_wiki_atlas.py
"""
from __future__ import annotations
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _wikis import resolve_vault  # noqa: E402

# The wiki vault may live in the vault home since the C1 split.
WIKI = resolve_vault("wiki").root
OUT = ROOT / "diagrams" / "wiki-atlas.excalidraw"

# === Jedi palette (mirrors wiki/training/design.md) ===
BG = "#0a0d12"
CARD_DARK = "#0f1729"
CARD_DARK_2 = "#181b22"
TEXT = "#e6e8ee"
TEXT_DIM = "#c4c7cc"   # grey-5. Was #cae3ff, a pale BLUE that tinted most
                       # of the body copy and kept the old identity alive
                       # long after the accents had been changed.
TEXT_MUTED = "#9aa3b5"
TEXT_FAINT = "#6e7686"
# Riverfed palette. Four colours here is deliberate and sanctioned:
# design.md's diagram register allows multiple colours "when they encode
# stable node kinds", and each one below IS a layer of the knowledge model.
# What is gone is the blue/purple pairing, which encoded nothing.
ACCENT = "#46c98b"        # concepts: the north stars, the accent
ACCENT_DEEP = "#1d9e66"   # topics: the curated subject layer
AMBER = "#ffd93d"         # entities: named things
SLATE = "#8a92a3"         # sources: raw input, deliberately neutral
ORANGE = "#ff6b35"        # reserved for emphasis, not a rotation slot

# === Element builders ===
_seed = [100]
def _s() -> int:
    _seed[0] += 1
    return _seed[0]

def _base(t: str, x: int, y: int, w: int, h: int) -> dict[str, Any]:
    s = _s()
    return {
        "id": f"{t[0]}{s}", "type": t,
        "x": x, "y": y, "width": w, "height": h, "angle": 0,
        "strokeColor": "#000000", "backgroundColor": "transparent",
        "fillStyle": "solid", "strokeWidth": 1, "strokeStyle": "solid",
        "roughness": 1, "opacity": 100,
        "groupIds": [], "frameId": None, "roundness": None,
        "seed": s, "version": 1, "versionNonce": s,
        "isDeleted": False, "boundElements": None,
        "updated": 1, "link": None, "locked": False,
    }

def text(x: int, y: int, w: int, h: int, t: str,
         color: str = TEXT, size: int = 14, font: int = 4,
         align: str = "left") -> dict[str, Any]:
    el = _base("text", x, y, w, h)
    el.update({
        "strokeColor": color, "roughness": 0, "strokeWidth": 1,
        "text": t, "fontSize": size, "fontFamily": font,
        "textAlign": align, "verticalAlign": "top",
        "containerId": None, "originalText": t,
        "lineHeight": 1.25 if size >= 22 else 1.4,
    })
    return el

def rect(x: int, y: int, w: int, h: int,
         stroke: str, fill: str = CARD_DARK,
         sw: int = 2) -> dict[str, Any]:
    el = _base("rectangle", x, y, w, h)
    el.update({
        "strokeColor": stroke, "backgroundColor": fill,
        "strokeWidth": sw,
        "roundness": {"type": 3},
    })
    return el

def ellipse(x: int, y: int, w: int, h: int, fill: str) -> dict[str, Any]:
    """Solid dot. Used for the Riverfed brand mark, which is the dot from
    the wordmark rather than a decorative lozenge."""
    el = _base("ellipse", x, y, w, h)
    el.update({
        "strokeColor": fill, "backgroundColor": fill,
        "fillStyle": "solid", "strokeWidth": 1, "roughness": 0,
    })
    return el


def line(x: int, y: int, dx: int, dy: int,
         color: str, sw: int = 3) -> dict[str, Any]:
    el = _base("line", x, y, abs(dx) if dx else 4, abs(dy) if dy else 4)
    el.update({
        "strokeColor": color, "strokeWidth": sw, "roughness": 0,
        "points": [[0, 0], [dx, dy]],
        "lastCommittedPoint": None,
        "startBinding": None, "endBinding": None,
        "startArrowhead": None, "endArrowhead": None,
    })
    return el

def count(folder: str) -> int:
    p = WIKI / folder
    return len(list(p.glob("*.md"))) if p.exists() else 0

# === Read live counts ===
N_SOURCES = count("sources")
N_TOPICS = count("topics")
N_ENTITIES = count("entities")
N_CONCEPTS = count("concepts")

# === Content, read live from the vault ===
# Everything below used to be a hardcoded snapshot from 2026-05-12, with
# evidence counts frozen at the values of that day ("markdown is the oxygen"
# said 12 sources; it is 26). The footer has always claimed this atlas
# reflects the wiki automatically. Now it does.

def _wrap(text: str, width: int, max_lines: int) -> str:
    """Hard-wrap into the explicit newlines excalidraw text elements need."""
    words, lines, cur = str(text).split(), [], ""
    for w in words:
        if cur and len(cur) + len(w) + 1 > width:
            lines.append(cur)
            cur = w
            if len(lines) == max_lines:
                break
        else:
            cur = f"{cur} {w}".strip()
    if cur and len(lines) < max_lines:
        lines.append(cur)
    if len(lines) == max_lines and len(" ".join(words)) > sum(len(l) for l in lines):
        lines[-1] = lines[-1].rstrip(".,;:") + "..."
    return "\n".join(lines)


# Some vault pages carry mojibake: an em-dash or curly quote was decoded as
# latin-1 somewhere upstream and re-encoded as UTF-8, so the bytes on disk
# really are "â€”". Repair on read so the atlas never renders, or propagates,
# corrupted text. The pages themselves still need fixing at source.
_MOJIBAKE = {
    "â€”": "—", "â€“": "–", "â€œ": "“", "â€\x9d": "”",
    "â€™": "’", "â€˜": "‘", "â€¦": "…", "Â": "",
}


def _clean(s: str) -> str:
    for bad, good in _MOJIBAKE.items():
        s = s.replace(bad, good)
    return s


def _lead(body: str, section: int = 1) -> str:
    """The Nth `## ` section's opening PARAGRAPH, not just its first line.

    Vault pages are hard-wrapped at ~72 characters, so taking one line gave
    a sentence fragment: cards read "The recurring observation that markdown"
    and stopped. Join until the first blank line instead.
    """
    parts = re.split(r"\n## ", body)
    if len(parts) <= section:
        return ""
    out: list[str] = []
    for line in parts[section].splitlines()[1:]:
        s = line.strip()
        if not s:
            if out:
                break
            continue
        if s.startswith(("|", "-", "*", ">", "#")):
            if out:
                break
            continue
        out.append(s)
    text = " ".join(out)
    text = re.sub(r"\[\[([^\]|]+)(\|[^\]]+)?\]\]", r"\1", text)
    text = re.sub(r"[*`]", "", text)
    return _clean(text)


def read_pages(folder: str) -> list[dict[str, Any]]:
    """slug, title, evidence count, and the page's own framing."""
    out: list[dict[str, Any]] = []
    for path in sorted((WIKI / folder).glob("*.md")):
        raw = path.read_text(encoding="utf-8", errors="replace")
        parts = raw.split("---", 2)
        fm, body = (parts[1], parts[2]) if len(parts) > 2 else ("", raw)
        m = re.search(r"^sources:\s*\[(.*?)\]", fm, re.M | re.S)
        n = len([x for x in m.group(1).split(",") if x.strip()]) if m else 0
        title = next((l[2:].strip() for l in body.splitlines()
                      if l.startswith("# ")), path.stem)
        out.append({"slug": path.stem, "title": title, "count": n,
                    "what": _lead(body, 1), "why": _lead(body, 2),
                    "fm": fm})
    out.sort(key=lambda d: (-d["count"], d["slug"]))
    return out


_concepts = read_pages("concepts")
_topics = read_pages("topics")

# Top concepts by weight of evidence, not by a list someone froze in May.
NORTH_STARS = [{
    "num": f"{i + 1:02d}",
    "count": c["count"],
    "title": c["title"],
    "desc": _wrap(c["what"], 46, 4),
    "ev": _wrap(c["why"], 42, 3),
    "attr": "",
} for i, c in enumerate(_concepts[:6])]

TOPICS = [(t["slug"], _wrap(t["what"], 38, 2)) for t in _topics]


def _recent_sources(limit: int = 8) -> list[tuple[str, str, str]]:
    """The most recently ingested transcripts: channel, title, and the
    page's own TL;DR. An earlier version put the raw slug in the third slot,
    where it overprinted the title, because a slug is not a description."""
    rows = []
    for path in (WIKI / "sources").glob("*.md"):
        raw = _clean(path.read_text(encoding="utf-8", errors="replace"))
        parts = raw.split("---", 2)
        fm, body = (parts[1], parts[2]) if len(parts) > 2 else ("", raw)

        def field(name: str) -> str:
            m = re.search(rf"^{name}:\s*(.+)$", fm, re.M)
            return m.group(1).strip().strip('"') if m else ""

        rows.append((field("ingested"), field("channel") or "SOURCE",
                     field("title") or path.stem, _lead(body, 1)))
    rows.sort(reverse=True)
    return [(ch.upper()[:20], _wrap(title, 32, 2), _wrap(summary, 42, 2))
            for _, ch, title, summary in rows[:limit]]


SOURCES = _recent_sources()


def _channel_line(top: int = 6) -> str:
    """Who the corpus is actually drawn from, by volume. Was a frozen list of
    six names, one of which ("Howie Liu") has no page in the wiki."""
    counts: dict[str, int] = {}
    for path in (WIKI / "sources").glob("*.md"):
        raw = path.read_text(encoding="utf-8", errors="replace")
        fm = raw.split("---", 2)[1] if raw.startswith("---") else ""
        m = re.search(r"^channel:\s*(.+)$", fm, re.M)
        if m:
            ch = _clean(m.group(1).strip().strip('"'))
            counts[ch] = counts.get(ch, 0) + 1
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    names = " · ".join(c for c, _ in ranked[:top])
    rest = len(ranked) - top
    return f"drawn from {names}" + (f" · + {rest} more" if rest > 0 else "")


CHANNEL_LINE = _channel_line()

# === Build elements ===
els: list[dict[str, Any]] = []

# --- Header ---
els.append(text(60, 50, 1280, 56, "Riverfed · Wiki Atlas", TEXT, 44))
els.append(text(60, 112, 1480, 32,
                f"A knowledge base distilled from {N_SOURCES} sources of operators showing how AI agents actually ship work —",
                TEXT_DIM, 20))
els.append(text(60, 138, 1480, 32, "coding, marketing, business, and design.", TEXT_DIM, 20))
# Brand mark: the Riverfed dot, not a lozenge.
els.append(ellipse(1548, 74, 16, 16, ACCENT))

# Stats row
for i, (n, lbl, color) in enumerate([
    (N_SOURCES,  "SOURCES",  SLATE),
    (N_TOPICS,   "TOPICS",   ACCENT_DEEP),
    (N_ENTITIES, "ENTITIES", AMBER),
    (N_CONCEPTS, "CONCEPTS", ACCENT),
]):
    x = 60 + i * 116
    els.append(text(x, 184, 100, 50, str(n), color, 44, font=4))
    els.append(text(x, 240, 100, 18, lbl, TEXT_MUTED, 12, font=3))

els.append(text(500, 198, 1080, 20,
                CHANNEL_LINE,
                TEXT_FAINT, 13, font=3))

# --- Section: Six North Stars ---
els.append(text(60, 290, 1280, 24, f"THE TOP {len(NORTH_STARS)} OF {N_CONCEPTS} CONCEPTS", ACCENT, 18, font=3))
els.append(text(60, 318, 1280, 24,
                "Cross-cutting ideas that surface when multiple operators independently arrive at the same frame",
                TEXT_MUTED, 16))

# 3x2 grid: card 490w × 280h, x positions 60/576/1092, y 346/646
NS_X = [60, 576, 1092]
NS_Y = [346, 646]
NS_W_LAST = 448  # last col is narrower because canvas is 1600
for i, ns in enumerate(NORTH_STARS):
    col = i % 3
    row = i // 3
    x = NS_X[col]
    y = NS_Y[row]
    w = 490 if col < 2 else NS_W_LAST
    # card
    els.append(rect(x, y, w, 280, ACCENT, CARD_DARK, sw=2))
    # eyebrow
    els.append(text(x + 20, y + 18, w - 40, 20,
                    f"{ns['num']} · {ns['count']} sources", ACCENT, 13, font=3))
    # headline
    els.append(text(x + 20, y + 54, w - 40, 32, ns["title"], TEXT, 22, font=4))
    # description (multiline)
    els.append(text(x + 20, y + 100, w - 40, 100, ns["desc"], TEXT_DIM, 14, font=4))
    # vertical accent line + evidence
    els.append(line(x + 20, y + 190, 0, 64, ACCENT, sw=3))
    els.append(text(x + 40, y + 200, w - 60, 80, ns["ev"], TEXT, 14, font=4))
    if ns["attr"]:
        els.append(text(x + 40, y + 250, w - 60, 20, ns["attr"], TEXT_FAINT, 12, font=4))

# --- Section: 11 Topics ---
els.append(text(60, 990, 1280, 24, f"THE {N_TOPICS} TOPICS", ACCENT_DEEP, 18, font=3))
els.append(text(60, 1018, 1280, 24,
                "Subject areas — each spans 2+ sources, with shared frame and vocabulary",
                TEXT_MUTED, 16))

# 4-col grid: card 350w × 100h, x: 60/436/812/1188, y: 1046/1166/1286
T_X = [60, 436, 812, 1188]
for i, (slug, desc) in enumerate(TOPICS):
    col = i % 4
    row = i // 4
    x = T_X[col]
    y = 1046 + row * 120
    els.append(rect(x, y, 350, 100, ACCENT_DEEP, CARD_DARK_2, sw=2))
    els.append(text(x + 18, y + 16, 314, 20, slug, ACCENT_DEEP, 13, font=3))
    els.append(text(x + 18, y + 44, 314, 60, desc, TEXT_DIM, 13, font=4))

# --- Section: Featured Sources ---
els.append(text(60, 1430, 1280, 24, "MOST RECENT SOURCES", SLATE, 18, font=3))
els.append(text(60, 1458, 1280, 24,
                f"The {len(SOURCES)} most recently ingested of {N_SOURCES} transcripts",
                TEXT_MUTED, 16))

# 4-col grid: card 350w × 120h, x: 60/436/812/1188, y: 1486/1626
S_X = [60, 436, 812, 1188]
for i, (kind, slug, pitch) in enumerate(SOURCES):
    col = i % 4
    row = i // 4
    x = S_X[col]
    y = 1486 + row * 140
    # Card is 120 tall: channel, then a title that may wrap to two lines
    # (~40px at 15px/1.4), then the summary. The title used to sit at +38
    # with the summary at +68, so any two-line title overprinted it.
    els.append(rect(x, y, 350, 120, SLATE, CARD_DARK, sw=2))
    els.append(text(x + 18, y + 12, 314, 16, kind, SLATE, 10, font=3))
    els.append(text(x + 18, y + 32, 314, 44, slug, TEXT, 14, font=4))
    els.append(text(x + 18, y + 80, 314, 34, pitch, TEXT_DIM, 11, font=4))

# --- Footer ---
els.append(text(60, 1752, 1480, 20,
                "Add a new transcript  →  run wiki/scripts/ingest.py  →  this atlas reflects the new state automatically",
                TEXT_FAINT, 13, font=3))

# === Final excalidraw doc ===
doc = {
    "type": "excalidraw",
    "version": 2,
    "source": "riverfed · build_wiki_atlas.py",
    "elements": els,
    "appState": {
        "viewBackgroundColor": BG,
        "gridSize": None,
        "gridStep": 5,
    },
    "files": {},
}

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(doc, indent=2), encoding="utf-8")
print(f"wrote {OUT}")
print(f"  sources={N_SOURCES} · topics={N_TOPICS} · entities={N_ENTITIES} · concepts={N_CONCEPTS}")
print(f"  elements={len(els)}")
