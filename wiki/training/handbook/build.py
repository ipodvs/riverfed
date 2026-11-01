#!/usr/bin/env python3
"""Build every handbook artifact from ONE spec.

    .venv/bin/python wiki/training/handbook/build.py

Reads `spec.py` and emits, all from the same slide list:

    wiki/training/riverfed-handbook.md  Marp source (beside assets/)
    out/riverfed-handbook.html          Marp render
    out/riverfed-handbook.pdf           Marp render
    out/riverfed-handbook-marp.pptx     Marp render, flattened images
    out/riverfed-handbook.pptx          NATIVE editable PowerPoint
    out/riverfed-handbook.json          spec sidecar (studio_guide reads it)
    out/riverfed-handbook-notes.docx    teaching notes, one per slide

TWO PowerPoints on purpose. The `-marp` one is pixel-identical to the HTML
because every slide is an image, so it presents exactly as designed but
cannot be edited. The plain `.pptx` is real shapes and text boxes, editable
in PowerPoint or Keynote, and therefore approximates the layout rather than
reproducing it. Pick by whether the audience needs to change anything.
Never let the marp render target the plain filename: it did once, and
silently overwrote the editable deck.

Why this exists: the previous handbook was authored TWICE, as 816 lines of
Marp markdown and again as 36 hardcoded slide specs in
`wiki/training/scripts/build_handbook_pptx.py`. They happened to stay in sync
through discipline alone, and every future edit cost double. Here the spec is
the source and both renderers are outputs.

Slide types are restricted to the TEN that both renderers implement:
cover, lead, section, content, cards, six-up, flow, versus, kpi, quote.
`timeline`, `hub` and `donut-kpi` exist in studio_pptx but have no CSS in the
Marp theme, so using them would silently produce two different decks.

Speaker notes live on each slide as `notes`, so a slide and the thing you say
while showing it cannot drift apart. The audience for the notes is someone who
uses AI in a browser and has never run an agent, so they explain rather than
cue.
"""
from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
OUT = ROOT / "wiki" / "training" / "out"
STEM = "riverfed-handbook"
# One design drives BOTH renderers: the Marp theme mirrors these tokens and
# the pptx renderer is patched from this file at build time.
DESIGN = ROOT / "designs" / "riverfed.md"

sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "wiki" / "scripts"))

MARP_ONLY_TYPES = {"timeline", "hub", "donut-kpi"}
SUPPORTED = {"cover", "lead", "section", "content", "cards",
             "six-up", "flow", "versus", "kpi", "quote"}


def esc(s: object) -> str:
    """HTML-escape, but keep the inline markdown the theme expects."""
    return html.escape(str(s), quote=False)


# --------------------------------------------------------------------------
# spec -> Marp markdown
# --------------------------------------------------------------------------

def _eyebrow(spec: dict) -> list[str]:
    return [f'<p class="eyebrow">{esc(spec["eyebrow"])}</p>', ""] \
        if spec.get("eyebrow") else []


def _cite(spec: dict) -> list[str]:
    return ["", f'<p class="cite">{esc(spec["cite"])}</p>'] \
        if spec.get("cite") else []


def _callout(spec: dict) -> list[str]:
    if not spec.get("callout"):
        return []
    return ["", '<div class="callout">', f'<p>{spec["callout"]}</p>', "</div>"]


def _item(it: dict, *, icon: bool = False, num: bool = True) -> str:
    """One card / step / grid cell. Icons are optional; a cell without one
    simply has no icon block rather than a placeholder."""
    parts = ["  <div>"]
    if icon and it.get("icon"):
        parts.append(f'<div class="icon"><img src="assets/icons/{it["icon"]}.svg" /></div>')
    if num and it.get("num"):
        parts.append(f'<span class="num">{esc(it["num"])}</span>')
    parts.append(f'<h3>{esc(it.get("title", ""))}</h3>')
    if it.get("desc"):
        parts.append(f'<p>{it["desc"]}</p>')
    parts.append("</div>")
    return "".join(parts)


def render_cover(s: dict) -> list[str]:
    out = ["<!-- _class: cover -->", "<!-- _paginate: false -->", "",
           '<div class="cover-shapes"></div>',
           '<div class="cover-wordmark">Riverfed<span class="dot">.</span></div>', ""]
    out += _eyebrow(s)
    out += [f'# {s["title"]}', ""]
    if s.get("subtitle"):
        out += [f'## {s["subtitle"]}', ""]
    if s.get("tags"):
        out += ['<div class="tag-row">']
        out += [f"  <span>{esc(t)}</span>" for t in s["tags"]]
        out += ["</div>"]
    return out


def render_lead(s: dict) -> list[str]:
    out = ["<!-- _class: lead -->", ""] + _eyebrow(s)
    out += [f'# {s.get("headline", s.get("title", ""))}', ""]
    if s.get("subtitle"):
        out += [f'## {s["subtitle"]}']
    return out + _cite(s)


def render_section(s: dict) -> list[str]:
    out = ["<!-- _class: section -->", ""]
    if s.get("number"):
        out += [f'<span class="section-num">{esc(s["number"])}</span>', ""]
    out += [f'# {s["title"]}', ""]
    if s.get("subtitle"):
        out += [f'## {s["subtitle"]}']
    return out


def render_content(s: dict) -> list[str]:
    out = _eyebrow(s) + [f'# {s["title"]}', ""]
    if s.get("body"):
        out += [s["body"], ""]
    if s.get("bullets"):
        out += ["<ul>"] + [f"  <li>{b}</li>" for b in s["bullets"]] + ["</ul>"]
    return out + _callout(s) + _cite(s)


def _grid(s: dict, cls: str, key: str, *, icon: bool, num: bool = True) -> list[str]:
    items = s.get(key) or []
    width = {2: " two", 3: "", 4: " four"}.get(len(items), "") if cls == "cards" else ""
    out = _eyebrow(s) + [f'# {s["title"]}', "", f'<div class="{cls}{width}">']
    out += [_item(it, icon=icon, num=num) for it in items]
    out += ["</div>"]
    return out + _callout(s) + _cite(s)


def render_cards(s: dict) -> list[str]:
    return _grid(s, "cards", "cards", icon=bool(s.get("icons")))


def _iconic(items: list[dict], base: str) -> str:
    """`.six-up.iconic > *` is a `40px 1fr` grid whose first column is
    reserved for the icon. Without an icon the FIRST CHILD lands in that 40px
    column instead, so the label and description wrap one character at a time.
    Only opt into the modifier when the items actually carry icons."""
    return f"{base} iconic" if any(i.get("icon") for i in items) else base


def render_sixup(s: dict) -> list[str]:
    items = s.get("items") or []
    return _grid(s, _iconic(items, "six-up"), "items",
                 icon=any(i.get("icon") for i in items))


def render_flow(s: dict) -> list[str]:
    steps = s.get("steps") or []
    return _grid(s, "steps", "steps", icon=any(i.get("icon") for i in steps))


def render_versus(s: dict) -> list[str]:
    old, new = s.get("old") or {}, s.get("new") or {}
    def panel(p: dict, kind: str) -> list[str]:
        block = [f'<div class="panel {kind}">', f'<h3>{esc(p.get("title",""))}</h3>']
        if p.get("desc"):
            block.append(f'<p>{p["desc"]}</p>')
        if p.get("bullets"):
            block += ["<ul>"] + [f"  <li>{b}</li>" for b in p["bullets"]] + ["</ul>"]
        block.append("</div>")
        return block
    out = _eyebrow(s) + [f'# {s["title"]}', "", '<div class="versus">']
    out += panel(old, "old") + ['<div class="arrow">&rarr;</div>'] + panel(new, "new")
    out += ["</div>"]
    return out + _callout(s) + _cite(s)


def render_kpi(s: dict) -> list[str]:
    out = _eyebrow(s) + [f'# {s["title"]}', "", '<div class="kpi">']
    for k in s.get("kpis") or []:
        out.append(f'<div><strong>{esc(k["value"])}</strong>'
                   f'<p>{k.get("label","")}</p></div>')
    out += ["</div>"]
    return out + _callout(s) + _cite(s)


def render_quote(s: dict) -> list[str]:
    out = _eyebrow(s) + [f'> {s["quote"]}', ""]
    if s.get("attribution"):
        out += [f'<p class="attribution">{esc(s["attribution"])}</p>']
    return out + _cite(s)


RENDERERS = {
    "cover": render_cover, "lead": render_lead, "section": render_section,
    "content": render_content, "cards": render_cards, "six-up": render_sixup,
    "flow": render_flow, "versus": render_versus, "kpi": render_kpi,
    "quote": render_quote,
}


def emit_marp(deck: dict, slides: list[dict]) -> str:
    head = ["---", "marp: true", f'theme: {deck.get("theme", "riverfed")}',
            "paginate: true", f'title: {deck["title"]}',
            f'description: {deck["description"]}', "tags: [wiki]", "---", ""]
    blocks = []
    for i, s in enumerate(slides, 1):
        kind = s.get("type", "content")
        if kind not in RENDERERS:
            raise ValueError(
                f"slide {i} ({s.get('title','?')!r}): type {kind!r} has no Marp "
                f"renderer. {'It is PPTX-only; ' if kind in MARP_ONLY_TYPES else ''}"
                f"supported: {sorted(SUPPORTED)}")
        blocks.append("\n".join(RENDERERS[kind](s)).rstrip())
    # "Riverfed" is a plain word in slide text; only the cover carries the
    # wordmark (design.md "Brand mark").
    body = "\n\n---\n\n".join(blocks)
    return "\n".join(head) + body + "\n"


# --------------------------------------------------------------------------
# spec -> teaching notes markdown
# --------------------------------------------------------------------------

def _marp_bin() -> list[str] | None:
    """Resolve the marp CLI, mirroring studio_marp.py: a real binary first,
    then `npx`. Returns None when neither is available, so a missing marp
    degrades to "markdown only" instead of failing the build."""
    import shutil
    exe = shutil.which("marp")
    if exe:
        return [exe]
    if shutil.which("npx"):
        return ["npx", "-y", "@marp-team/marp-cli@latest"]
    return None


def render_marp(md_path: Path) -> None:
    """Render the Marp source to HTML, PDF and PPTX.

    The PPTX here is the MARP one: every slide is a flattened image, so it is
    pixel-identical to the HTML but not editable. It is written as
    `<stem>-marp.pptx` and never as `<stem>.pptx`, which belongs to the native
    editable deck from studio_pptx. Those two collided once already and the
    marp render silently overwrote the editable file.
    """
    import subprocess
    marp = _marp_bin()
    if not marp:
        print("note: marp CLI not found, wrote markdown only "
              "(brew install marp-cli, or npm i -g @marp-team/marp-cli)")
        return
    theme = ROOT / "wiki" / "training" / "themes" / "riverfed.css"
    targets = [
        (OUT / f"{STEM}.html", "html"),
        (OUT / f"{STEM}.pdf", "pdf"),
        (OUT / f"{STEM}-marp.pptx", "pptx (flattened, not editable)"),
    ]
    for dest, label in targets:
        cmd = [*marp, "--html", "--allow-local-files",
               "--theme", str(theme), str(md_path), "-o", str(dest)]
        r = subprocess.run(cmd, cwd=md_path.parent,
                           capture_output=True, text=True)
        if r.returncode == 0 and dest.exists():
            print(f"wrote out/{dest.name}  ({dest.stat().st_size:,} bytes) "
                  f"[marp {label}]")
        else:
            print(f"warning: marp failed for {dest.name}: "
                  f"{(r.stderr or '').strip()[:200]}", file=sys.stderr)


def _plain(value):
    """Strip presentation markup for renderers that take plain text.

    The spec is authored for Marp, so it carries `<strong>`, `<code>` and
    `<br>`. The Marp emitter passes those through to the browser, but
    python-pptx writes whatever string it is given verbatim, so a callout
    reading "<strong>Read the numbers</strong>" appears with the tags
    visible on the slide. Nothing is lost by stripping: the pptx callout is
    already rendered bold, and `<code>` has no run-level equivalent here.
    """
    if isinstance(value, str):
        text = re.sub(r"<br\s*/?>", " ", value)
        # `<strong>` survives: studio_pptx's run splitter turns it into an
        # accent-coloured run, matching the Marp callout's lead-in. Everything
        # else (notably <code>, which has no run-level equivalent) is dropped.
        text = re.sub(r"</?(?!strong\b)[a-zA-Z][^>]*>", "", text)
        return " ".join(html.unescape(text).split())
    if isinstance(value, list):
        return [_plain(v) for v in value]
    if isinstance(value, dict):
        # `notes` never reaches a slide; leave it exactly as written.
        return {k: (v if k == "notes" else _plain(v)) for k, v in value.items()}
    return value


def emit_notes(deck: dict, slides: list[dict]) -> str:
    out = [f'# {deck["title"]} — teaching notes', "",
           deck.get("notes_intro", ""), ""]
    n = 0
    for s in slides:
        n += 1
        title = s.get("title") or s.get("headline") or s.get("quote", "")[:60]
        # Slide titles carry presentation markup (<br> for line breaks, <code>
        # in step text). A notes heading is prose, so strip it.
        title = re.sub(r"<[^>]+>", " ", str(title))
        title = html.unescape(" ".join(title.split()))
        out += [f"## Slide {n} · {title}", ""]
        if s.get("notes"):
            out += [s["notes"].strip(), ""]
        else:
            out += ["_(no note)_", ""]
    return "\n".join(out)


def main() -> int:
    import spec as S  # noqa: E402  (the deck source)

    slides = S.SLIDES
    OUT.mkdir(parents=True, exist_ok=True)

    # The Marp source lives beside wiki/training/assets/, because slides
    # reference icons as `assets/icons/<name>.svg` and marp resolves those
    # relative to the markdown file. Rendered outputs go to out/.
    md = emit_marp(S.DECK, slides)
    md_path = ROOT / "wiki" / "training" / f"{STEM}.md"
    md_path.write_text(md, encoding="utf-8", newline="\n")
    print(f"wrote wiki/training/{STEM}.md  ({len(slides)} slides)")

    (OUT / f"{STEM}.json").write_text(
        json.dumps({"slides": slides}, indent=2, ensure_ascii=False),
        encoding="utf-8", newline="\n")
    print(f"wrote out/{STEM}.json")

    notes_md = emit_notes(S.DECK, slides)
    notes_path = OUT / f"{STEM}-notes.md"
    notes_path.write_text(notes_md, encoding="utf-8", newline="\n")

    # The pptx renderer keeps its palette and fonts as MODULE-LEVEL constants
    # that still default to the pre-rebrand blue and purple. _apply_design
    # rewrites them from a design.md. Without this call the PowerPoint renders
    # in a different identity from the Marp deck built one function earlier,
    # which is exactly the divergence a single source is supposed to prevent.
    from studio_pptx import build_pptx, _apply_design  # noqa: E402
    _apply_design(str(DESIGN))
    tmp = OUT / f"{STEM}.tmp.pptx"
    build_pptx({"slides": [_plain(s) for s in slides]}, tmp)
    dest = OUT / f"{STEM}.pptx"
    try:
        tmp.replace(dest)
    except PermissionError:
        print(f"warning: {dest.name} is locked (close PowerPoint); "
              f"new build left at {tmp.name}", file=sys.stderr)
        dest = tmp
    print(f"wrote out/{dest.name}  ({dest.stat().st_size:,} bytes)")

    from speaker_docx import render_markdown_to_docx  # noqa: E402
    docx = OUT / f"{STEM}-notes.docx"
    # NB: this renderer takes the notes markdown PATH, not its text.
    render_markdown_to_docx(
        notes_path, docx,
        design_path=DESIGN)
    print(f"wrote out/{docx.name}  ({docx.stat().st_size:,} bytes)")

    render_marp(md_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
