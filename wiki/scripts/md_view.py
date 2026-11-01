#!/usr/bin/env python3
"""Render a vault/output markdown page as a styled, on-brand HTML document.

The server used to serve wiki + output pages as raw ``text/markdown``, so a
browser showed the YAML frontmatter block and every ``#`` / ``**`` / ``[[..]]``
mark as plain text — unreadable. This module turns one markdown page into a
self-contained HTML document in the Porcelain theme (light UI, Jedi Green
#157347 accent, no gradients — matches the /wiki and converter surfaces).

Deliberately dependency-free (no markdown/mistune in the venv, and the tool
must work offline): a small block+inline renderer covering exactly what our
ingest agent emits per wiki/SCHEMA.md — headings, bold/italic, inline and
fenced code, ordered/unordered nested lists, blockquotes, rules, tables,
links, images, and Obsidian ``[[wikilink]]`` / ``[[target|alias]]`` refs.
Frontmatter is lifted into a compact metadata header instead of dumped raw.

Entry point: ``render_page(md_text, *, title, resolve_wikilink=None)`` ->
full HTML string. ``resolve_wikilink(slug)`` returns an href or None; an
unresolved wikilink renders as a styled non-link so nothing 404s.
"""
from __future__ import annotations

import html
import re
from typing import Callable, Optional

try:  # package-relative when imported as a module
    from _frontmatter import split_frontmatter, as_list
except ImportError:  # pragma: no cover - direct script runs
    from wiki.scripts._frontmatter import split_frontmatter, as_list  # type: ignore

WikiResolver = Callable[[str], Optional[str]]

_ESCAPE = {"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}


def _esc(s: str) -> str:
    return "".join(_ESCAPE.get(c, c) for c in s)


# ── mojibake repair ───────────────────────────────────────────────────────
# Many vault pages have UTF-8 punctuation that was decoded as Windows-1252
# and re-saved as UTF-8 (double-encoding), so an em dash "—" sits on disk as
# the bytes for "â€”", an arrow "→" as "â†'", a curly quote as "â€™", etc.
# Reading the file as UTF-8 (correctly) still yields the garbage because the
# garbage IS the stored content. Reverse it: map each mis-decoded char back to
# its original byte and re-decode the run as UTF-8. Runs that don't reverse to
# valid UTF-8 are left untouched, so legitimate lone accents are never harmed.
_CHAR2BYTE: dict[str, int] = {}
for _b in range(0x80, 0x100):
    for _codec in ("cp1252", "latin-1"):
        try:
            _CHAR2BYTE.setdefault(bytes([_b]).decode(_codec), _b)
            break
        except UnicodeDecodeError:
            continue
# maximal runs of >=2 "high" chars (min UTF-8 multibyte char = 2 such chars)
_MOJI_RUN_RE = re.compile("[" + re.escape("".join(_CHAR2BYTE)) + "]{2,}")


def _demojibake(text: str) -> str:
    text = text.lstrip("﻿")  # stray UTF-8 BOM at file start
    if not _MOJI_RUN_RE.search(text):
        return text

    def _fix(m: re.Match) -> str:
        run = m.group(0)
        try:
            return bytes(_CHAR2BYTE[c] for c in run).decode("utf-8")
        except (KeyError, UnicodeDecodeError):
            return run

    return _MOJI_RUN_RE.sub(_fix, text)


# ── inline spans ──────────────────────────────────────────────────────────
_CODE_RE = re.compile(r"`([^`]+)`")
_IMG_RE = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
_WIKILINK_RE = re.compile(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]")
_BARE_URL_RE = re.compile(r"https?://[^\s<>\x00]+")
_BOLD_RE = re.compile(r"\*\*([^*]+)\*\*|__([^_]+)__")
_ITALIC_RE = re.compile(r"(?<![*\w])\*([^*\n]+)\*(?!\*)|(?<![_\w])_([^_\n]+)_(?![_\w])")


def _render_inline(text: str, resolve: WikiResolver | None) -> str:
    """Inline markdown -> HTML. Code spans are extracted first so their
    contents are never re-parsed as emphasis/links."""
    placeholders: list[str] = []

    def _stash(html_frag: str) -> str:
        placeholders.append(html_frag)
        return f"\x00{len(placeholders) - 1}\x00"

    # 1. code spans (highest precedence, opaque body)
    text = _CODE_RE.sub(lambda m: _stash(f"<code>{_esc(m.group(1))}</code>"), text)

    # 2. images before links (share bracket syntax)
    def _img(m: re.Match) -> str:
        return _stash(f'<img src="{_esc(m.group(2))}" alt="{_esc(m.group(1))}" loading="lazy">')

    text = _IMG_RE.sub(_img, text)

    # 3. wikilinks -> resolved <a> or styled span
    def _wiki(m: re.Match) -> str:
        target = m.group(1).strip()
        label = (m.group(2) or target).strip()
        href = resolve(target) if resolve else None
        if href:
            return _stash(f'<a class="wl" href="{_esc(href)}">{_esc(label)}</a>')
        return _stash(f'<span class="wl wl-dead" title="no page yet">{_esc(label)}</span>')

    text = _WIKILINK_RE.sub(_wiki, text)

    # 4. normal links
    def _link(m: re.Match) -> str:
        href = m.group(2)
        rel = ' rel="noopener noreferrer" target="_blank"' if re.match(r"[a-z]+://", href) else ""
        return _stash(f'<a href="{_esc(href)}"{rel}>{_esc(m.group(1))}</a>')

    text = _LINK_RE.sub(_link, text)

    # 4b. autolink bare URLs (e.g. a plain YouTube link in the text). Markdown
    #     links + code are already stashed, so this only hits unlinked URLs.
    def _autolink(m: re.Match) -> str:
        url = m.group(0)
        trail = ""
        # trim trailing sentence punctuation, but keep balanced parens
        while url and url[-1] in ").,;:!?\"'":
            if url[-1] == ")" and url.count("(") > url.count(")"):
                break
            trail = url[-1] + trail
            url = url[:-1]
        linked = _stash(f'<a href="{_esc(url)}" rel="noopener noreferrer" target="_blank">{_esc(url)}</a>')
        return linked + trail

    text = _BARE_URL_RE.sub(_autolink, text)

    # 5. everything else is now plain -> escape, then re-apply emphasis
    #    (placeholders are \x00N\x00 sentinels, untouched by escaping)
    text = _esc(text)
    text = _BOLD_RE.sub(lambda m: f"<strong>{m.group(1) or m.group(2)}</strong>", text)
    text = _ITALIC_RE.sub(lambda m: f"<em>{m.group(1) or m.group(2)}</em>", text)

    # 6. restore placeholders
    def _restore(m: re.Match) -> str:
        return placeholders[int(m.group(1))]

    return re.sub(r"\x00(\d+)\x00", _restore, text)


# ── block parser ──────────────────────────────────────────────────────────
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
_HR_RE = re.compile(r"^\s*([-*_])(?:\s*\1){2,}\s*$")
_ULI_RE = re.compile(r"^(\s*)[-*+]\s+(.*)$")
_OLI_RE = re.compile(r"^(\s*)(\d+)[.)]\s+(.*)$")
_TABLE_SEP_RE = re.compile(r"^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)+\|?\s*$")


def _split_row(line: str) -> list[str]:
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|"):
        line = line[:-1]
    return [c.strip() for c in line.split("|")]


def _render_blocks(body: str, resolve: WikiResolver | None) -> str:
    lines = body.split("\n")
    out: list[str] = []
    i, n = 0, len(lines)

    def inline(s: str) -> str:
        return _render_inline(s, resolve)

    while i < n:
        line = lines[i]

        # blank
        if not line.strip():
            i += 1
            continue

        # fenced code
        fence = re.match(r"^\s*(```+|~~~+)(.*)$", line)
        if fence:
            marker = fence.group(1)[0] * 3
            lang = fence.group(2).strip()
            buf: list[str] = []
            i += 1
            while i < n and not lines[i].lstrip().startswith(marker):
                buf.append(lines[i])
                i += 1
            i += 1  # closing fence
            cls = f' class="lang-{_esc(lang)}"' if lang else ""
            out.append(f"<pre><code{cls}>{_esc(chr(10).join(buf))}</code></pre>")
            continue

        # heading
        h = _HEADING_RE.match(line)
        if h:
            level = len(h.group(1))
            out.append(f"<h{level}>{inline(h.group(2).strip())}</h{level}>")
            i += 1
            continue

        # horizontal rule
        if _HR_RE.match(line):
            out.append("<hr>")
            i += 1
            continue

        # blockquote (consecutive > lines; blank-> break)
        if line.lstrip().startswith(">"):
            buf = []
            while i < n and lines[i].lstrip().startswith(">"):
                buf.append(re.sub(r"^\s*>\s?", "", lines[i]))
                i += 1
            inner = _render_blocks("\n".join(buf), resolve)
            out.append(f"<blockquote>{inner}</blockquote>")
            continue

        # table: header row + separator row
        if "|" in line and i + 1 < n and _TABLE_SEP_RE.match(lines[i + 1]):
            headers = _split_row(line)
            i += 2
            rows: list[list[str]] = []
            while i < n and "|" in lines[i] and lines[i].strip():
                rows.append(_split_row(lines[i]))
                i += 1
            thead = "".join(f"<th>{inline(c)}</th>" for c in headers)
            body_html = ""
            for r in rows:
                cells = "".join(f"<td>{inline(c)}</td>" for c in r)
                body_html += f"<tr>{cells}</tr>"
            out.append(f"<table><thead><tr>{thead}</tr></thead><tbody>{body_html}</tbody></table>")
            continue

        # lists (ordered/unordered, nested by indent)
        if _ULI_RE.match(line) or _OLI_RE.match(line):
            block, i = _collect_list_lines(lines, i, n)
            out.append(_render_list(block, resolve))
            continue

        # paragraph: gather until a blank or a block-starting line
        buf = [line]
        i += 1
        while i < n and lines[i].strip() and not _starts_block(lines[i]):
            buf.append(lines[i])
            i += 1
        out.append(f"<p>{inline(' '.join(s.strip() for s in buf))}</p>")

    return "\n".join(out)


def _starts_block(line: str) -> bool:
    return bool(
        _HEADING_RE.match(line)
        or _HR_RE.match(line)
        or _ULI_RE.match(line)
        or _OLI_RE.match(line)
        or line.lstrip().startswith(">")
        or re.match(r"^\s*(```+|~~~+)", line)
    )


def _collect_list_lines(lines: list[str], i: int, n: int) -> tuple[list[str], int]:
    """Grab the contiguous list block (list items + their indented
    continuation lines), stopping at a blank line followed by a non-indented
    line, or any non-list top-level construct."""
    block: list[str] = []
    while i < n:
        line = lines[i]
        if not line.strip():
            # a blank line continues the list only if the next line is still
            # indented / another item
            nxt = lines[i + 1] if i + 1 < n else ""
            if nxt.strip() and (nxt.startswith(" ") or _ULI_RE.match(nxt) or _OLI_RE.match(nxt)):
                block.append("")
                i += 1
                continue
            break
        if _ULI_RE.match(line) or _OLI_RE.match(line) or line.startswith(" "):
            block.append(line)
            i += 1
            continue
        break
    return block, i


def _render_list(block: list[str], resolve: WikiResolver | None) -> str:
    """Render one (possibly nested) list block. Indentation in steps of ~2
    spaces defines nesting; the first item's marker sets ol vs ul per level."""
    def indent_of(s: str) -> int:
        return len(s) - len(s.lstrip(" "))

    items: list[tuple[int, bool, str]] = []  # (indent, ordered, text)
    for line in block:
        if not line.strip():
            continue
        m = _OLI_RE.match(line)
        if m:
            items.append((indent_of(line), True, m.group(3)))
            continue
        m = _ULI_RE.match(line)
        if m:
            items.append((indent_of(line), False, m.group(2)))
            continue
        # continuation line -> append to previous item's text
        if items:
            ind, ordered, text = items[-1]
            items[-1] = (ind, ordered, text + " " + line.strip())

    def build(idx: int, base_indent: int) -> tuple[str, int]:
        """Emit one or more sibling lists at ``base_indent``. Consecutive
        items of the SAME marker type share a list; when the type flips
        (ul<->ol) a new sibling list opens, so '- a' then '1. b' render as
        <ul>..</ul><ol>..</ol> rather than one merged list."""
        html_parts: list[str] = []
        while idx < len(items):
            ind, ordered, _text = items[idx]
            if ind < base_indent:
                break
            tag = "ol" if ordered else "ul"
            html_parts.append(f"<{tag}>")
            while idx < len(items):
                ind2, ordered2, text2 = items[idx]
                if ind2 < base_indent:
                    break
                if ind2 > base_indent:
                    # deeper: attach to the last <li> we opened
                    nested, idx = build(idx, ind2)
                    if html_parts and html_parts[-1].endswith("</li>"):
                        html_parts[-1] = html_parts[-1][: -len("</li>")] + nested + "</li>"
                    else:
                        html_parts.append(nested)
                    continue
                if ordered2 != ordered:
                    break  # sibling list of the other type — reopen in outer loop
                html_parts.append(f"<li>{_render_inline(text2, resolve)}</li>")
                idx += 1
            html_parts.append(f"</{tag}>")
        return "".join(html_parts), idx

    base = items[0][0] if items else 0
    html_str, _ = build(0, base)
    return html_str


# ── frontmatter header ────────────────────────────────────────────────────
def _meta_header(fm: dict, title: str) -> str:
    if not fm:
        return f'<header class="page-head"><h1 class="doc-title">{_esc(title)}</h1></header>'
    chips: list[str] = []
    channel = fm.get("channel")
    if isinstance(channel, str) and channel.strip():
        chips.append(f'<span class="chip">{_esc(channel.strip())}</span>')
    duration = fm.get("duration")
    if duration:
        chips.append(f'<span class="chip">{_esc(str(duration))}</span>')
    updated = fm.get("last_updated") or fm.get("date") or fm.get("published")
    if updated:
        label = "updated" if ("last_updated" in fm or "date" in fm) else "published"
        chips.append(f'<span class="chip">{label} {_esc(str(updated))}</span>')
    for key in ("sources", "source", "sub_topics", "related"):
        vals = as_list(fm.get(key)) if key in fm else []
        if vals:
            noun = key.replace("_", " ")
            chips.append(f'<span class="chip">{len(vals)} {_esc(noun)}</span>')
            break
    tags = as_list(fm.get("tags")) if "tags" in fm else []
    tag_html = "".join(f'<span class="tag">{_esc(t)}</span>' for t in tags)
    chip_html = "".join(chips)
    parts = [f'<header class="page-head"><h1 class="doc-title">{_esc(title)}</h1>']
    if chip_html or tag_html:
        parts.append(f'<div class="meta">{chip_html}{tag_html}</div>')
    url = fm.get("url")
    if isinstance(url, str) and re.match(r"https?://", url.strip()):
        u = url.strip()
        parts.append(f'<a class="src-link" href="{_esc(u)}" rel="noopener noreferrer" '
                     f'target="_blank">Watch source &#8599;</a>')
    parts.append("</header>")
    return "".join(parts)


_STYLE = """
:root{
  --bg:#f7f8fa; --bg-card:#ffffff; --bg-elevated:#eef1f5;
  --border:#e2e5eb; --border-soft:#eaedf2;
  --text:#15171c; --muted:#5c6470; --dim:#7d8490;
  --accent:#157347; --accent-hover:#115d3a;
  --mono:ui-monospace,SFMono-Regular,"SF Mono",Menlo,Consolas,monospace;
  --sans:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--text);font-family:var(--sans);
  line-height:1.65;font-size:16px;-webkit-font-smoothing:antialiased}
.wrap{max-width:760px;margin:0 auto;padding:48px 24px 96px}
.page-head{margin:0 0 28px;padding-bottom:20px;border-bottom:1px solid var(--border)}
.doc-title{font-size:30px;line-height:1.2;font-weight:700;letter-spacing:-.01em;margin:0}
.meta{display:flex;flex-wrap:wrap;gap:8px;margin-top:14px}
.chip{font:600 12px/1 var(--mono);color:var(--muted);background:var(--bg-elevated);
  border:1px solid var(--border-soft);border-radius:999px;padding:6px 10px}
.tag{font:600 12px/1 var(--mono);color:var(--accent);background:rgba(21,115,71,.08);
  border:1px solid rgba(21,115,71,.18);border-radius:999px;padding:6px 10px}
.src-link{display:inline-block;margin-top:14px;font-weight:600;font-size:14px;
  color:#fff;background:var(--accent);border:0;border-radius:8px;padding:8px 14px}
.src-link:hover{background:var(--accent-hover);color:#fff}
h1,h2,h3,h4,h5,h6{line-height:1.3;font-weight:700;letter-spacing:-.01em;
  margin:1.9em 0 .6em}
h2{font-size:22px;padding-bottom:.3em;border-bottom:1px solid var(--border-soft)}
h3{font-size:18px}
h4,h5,h6{font-size:15px;color:var(--muted);text-transform:uppercase;letter-spacing:.04em}
p{margin:0 0 1.05em}
a{color:var(--accent);text-decoration:none;border-bottom:1px solid rgba(21,115,71,.3)}
a:hover{color:var(--accent-hover);border-bottom-color:var(--accent-hover)}
.wl{background:rgba(21,115,71,.07);border-bottom:1px solid rgba(21,115,71,.25);
  border-radius:3px;padding:.5px 3px}
.wl-dead{color:var(--dim);background:var(--bg-elevated);border-bottom:1px dashed var(--border);
  padding:.5px 3px;border-radius:3px}
strong{font-weight:650;color:#0d0f13}
em{font-style:italic}
code{font-family:var(--mono);font-size:.88em;background:var(--bg-elevated);
  border:1px solid var(--border-soft);border-radius:5px;padding:.12em .4em}
pre{background:#0f1720;color:#e6edf3;border-radius:12px;padding:18px 20px;
  overflow-x:auto;margin:0 0 1.3em;border:1px solid #1b2530}
pre code{background:none;border:0;padding:0;font-size:13.5px;color:inherit;line-height:1.6}
ul,ol{margin:0 0 1.1em;padding-left:1.4em}
li{margin:.3em 0}
li>ul,li>ol{margin:.35em 0 .1em}
blockquote{margin:0 0 1.3em;padding:2px 18px;border-left:3px solid var(--accent);
  background:rgba(21,115,71,.05);border-radius:0 8px 8px 0;color:var(--text)}
blockquote p:last-child{margin-bottom:.6em}
blockquote p:first-child{margin-top:.6em}
hr{border:0;border-top:1px solid var(--border);margin:2.2em 0}
img{max-width:100%;height:auto;border-radius:10px;border:1px solid var(--border);margin:.4em 0}
table{width:100%;border-collapse:collapse;margin:0 0 1.4em;font-size:14.5px;
  display:block;overflow-x:auto}
th,td{border:1px solid var(--border);padding:8px 12px;text-align:left;vertical-align:top}
th{background:var(--bg-elevated);font-weight:650}
tr:nth-child(even) td{background:#fafbfc}
.doc-foot{margin-top:56px;padding-top:18px;border-top:1px solid var(--border);
  font:500 12px/1.5 var(--mono);color:var(--dim);display:flex;gap:14px;flex-wrap:wrap}
.doc-foot a{border:0}
@media (max-width:520px){.wrap{padding:32px 18px 72px}.doc-title{font-size:25px}}
"""


def render_page(md_text: str, *, title: str,
                resolve_wikilink: WikiResolver | None = None,
                back_href: str | None = None,
                raw_href: str | None = None) -> str:
    """Full standalone HTML document for one markdown page."""
    md_text = _demojibake(md_text)
    fm, _raw, body = split_frontmatter(md_text)
    header = _meta_header(fm, title)
    content = _render_blocks(body, resolve_wikilink)
    foot_links = []
    if back_href:
        foot_links.append(f'<a href="{_esc(back_href)}">&larr; Knowledge map</a>')
    if raw_href:
        foot_links.append(f'<a href="{_esc(raw_href)}">View raw markdown</a>')
    foot = f'<div class="doc-foot">{"".join(foot_links)}</div>' if foot_links else ""
    return (
        "<!doctype html>\n<html lang=\"en\"><head>"
        "<meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
        f"<title>{_esc(title)}</title>"
        f"<style>{_STYLE}</style></head><body>"
        f'<main class="wrap">{header}{content}{foot}</main>'
        "</body></html>"
    )
