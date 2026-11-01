#!/usr/bin/env python3
"""Shared wiki-page frontmatter parser.

Every consumer of page frontmatter (server graph/data builders, the Obsidian
normalization pass, linters) used to carry its own tiny YAML-ish parser, and
they drifted: some understood inline lists (`sources: [a, b]`) but silently
dropped valid YAML *block* sequences:

    sources:
      - alpha
      - beta

A block-list rewrite of a relationship field would then make graph edges,
source counts, and tags disappear with no error. This module is the one parser
they all share, so "what frontmatter forms parse" is answered in exactly one
place.

Supported forms:
  key: value                     scalar (quotes stripped)
  key: [a, b, c]                 inline list
  key:                           block list ->
    - a                            ["a", "b"]
    - b
  key: []                        empty list
  # comment                      ignored (also trailing ` # ...` on a scalar)

This is the PAGE dialect. Model *manifests* (models/<id>/model.md) use a
different, richer dialect with nested inline mappings — that stays in
design_tokens._parse_front_matter. Don't cross the two.
"""
from __future__ import annotations

import re

# Frontmatter is the leading `---`-fenced block. Anchored to the start so a
# `---` horizontal rule later in the body is never mistaken for it.
_FM_RE = re.compile(r"\A---[ \t]*\r?\n(.*?)\r?\n---[ \t]*\r?\n?", re.DOTALL)
_KEY_RE = re.compile(r"^([\w_-]+)\s*:(.*)$")


def _strip_quotes(v: str) -> str:
    v = v.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        return v[1:-1]
    return v


def _strip_trailing_comment(v: str) -> str:
    """Drop a trailing ` # ...` YAML comment when it is outside quotes and
    brackets. Leaves `url: https://x#y` and `title: "a # b"` intact."""
    in_quote = ""
    depth = 0
    for i, ch in enumerate(v):
        if in_quote:
            if ch == in_quote:
                in_quote = ""
        elif ch in "\"'":
            in_quote = ch
        elif ch in "[{":
            depth += 1
        elif ch in "]}":
            depth = max(0, depth - 1)
        elif ch == "#" and depth == 0 and i > 0 and v[i - 1] in " \t":
            return v[:i].rstrip()
    return v


def _split_inline_list(inner: str) -> list[str]:
    return [_strip_quotes(part) for part in inner.split(",") if part.strip()]


def _parse_block(raw: str) -> dict:
    lines = raw.splitlines()
    out: dict = {}
    i, n = 0, len(lines)
    while i < n:
        line = lines[i]
        i += 1
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        m = _KEY_RE.match(line)
        if not m:
            continue
        key = m.group(1).strip()
        val = _strip_trailing_comment(m.group(2).strip()).strip()
        if not key:
            continue
        if val == "":
            # Empty value: a block list follows if the next non-comment lines
            # are `- item`; otherwise it is just an empty scalar (skipped, as
            # every prior parser did).
            items: list[str] = []
            while i < n:
                nxt = lines[i].strip()
                if nxt.startswith("#"):
                    i += 1
                    continue
                if nxt == "-":
                    items.append("")
                    i += 1
                elif nxt.startswith("- "):
                    items.append(_strip_quotes(
                        _strip_trailing_comment(nxt[2:]).strip()))
                    i += 1
                else:
                    break
            if items:
                out[key] = items
        elif val.startswith("[") and val.endswith("]"):
            out[key] = _split_inline_list(val[1:-1])
        else:
            out[key] = _strip_quotes(val)
    return out


def split_frontmatter(text: str) -> tuple[dict, str, str]:
    """Return (frontmatter_dict, raw_frontmatter_str, body_str).
    ({}, "", text) when there is no leading frontmatter block."""
    m = _FM_RE.match(text)
    if not m:
        return {}, "", text
    raw = m.group(1)
    return _parse_block(raw), raw, text[m.end():]


def parse_frontmatter(text: str) -> dict:
    """Parse just the frontmatter dict (block + inline lists, scalars)."""
    return split_frontmatter(text)[0]


def as_list(value) -> list[str]:
    """Coerce a parsed frontmatter value to list[str] for relationship-field
    consumers. A list stays a list; a bare non-empty scalar becomes a
    single-element list; None/empty -> []. This is the guard that stops a
    malformed scalar relationship field from being iterated character by
    character."""
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v) for v in value]
    s = str(value).strip()
    return [s] if s else []
