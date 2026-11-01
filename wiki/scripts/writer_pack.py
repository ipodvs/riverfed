#!/usr/bin/env python3
"""Publish a Riverfed vault as a knowledge pack (v1) for the Writer bridge.

This is a narrow, read-only bridge.  It turns the
vault's existing markdown pages and provenance into a bounded JSON snapshot;
it never changes the vault and never promotes wiki material into canon.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import _frontmatter


ALLOWED_KINDS = {"source", "topic", "concept", "entity", "procedure", "policy", "presentation"}
CRAFT_KINDS = {"procedure", "policy"}
MAX_ITEMS = 500
MAX_BODY_CHARS = 12_000
_HEADING_RE = re.compile(r"^#{1,6}\s+.+$", re.MULTILINE)
_WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|[^\]]+)?\]\]")


def _first_h1(text: str) -> str:
    match = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
    return match.group(1).strip() if match else ""


def _section(text: str, heading: str) -> str:
    match = re.search(
        rf"^##\s+{re.escape(heading)}\s*$(.*?)(?=^##\s|\Z)",
        text,
        re.MULTILINE | re.DOTALL | re.IGNORECASE,
    )
    return match.group(1).strip() if match else ""


def _first_paragraph(text: str) -> str:
    cleaned = _HEADING_RE.sub("", text).strip()
    return next((part.strip() for part in re.split(r"\n\s*\n", cleaned) if part.strip()), "")


def _page_body(text: str) -> str:
    _, _, body = _frontmatter.split_frontmatter(text)
    return body.strip()[:MAX_BODY_CHARS]


def _bounded(value: object, limit: int) -> str:
    return str(value or "").strip()[:limit]


def _page_updated(path: Path, frontmatter: dict) -> str:
    declared = frontmatter.get("last_updated") or frontmatter.get("updated") or frontmatter.get("ingested")
    if declared:
        return _bounded(declared, 80)
    return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(timespec="seconds")


def _safe_id(*parts: str) -> str:
    raw = "-".join(parts)
    slug = re.sub(r"[^a-z0-9_.-]+", "-", raw.lower()).strip("-.") or "item"
    if len(slug) <= 120:
        return slug
    digest = hashlib.sha256(slug.encode("utf-8")).hexdigest()[:16]
    return f"{slug[:103].rstrip('-')}-{digest}"


def _kind(model, folder: str) -> str:
    value = str(model.kind(folder) or "topic").lower()
    return value if value in ALLOWED_KINDS else "topic"


def _lane(kind: str, frontmatter: dict) -> str:
    declared = str(frontmatter.get("writer_lane") or "").lower()
    if declared in {"craft", "research"}:
        return declared
    return "craft" if kind in CRAFT_KINDS else "research"


def _source_ref(source: dict) -> dict:
    ref = {"id": source["id"], "title": source["title"]}
    if source.get("creator"):
        ref["creator"] = source["creator"]
    if source.get("url") and str(source["url"]).startswith(("https://", "http://")):
        ref["url"] = source["url"]
    if source.get("published_at"):
        ref["publishedAt"] = source["published_at"]
    ref["rights"] = _bounded(source.get("rights") or "reference-only", 120)
    return ref


def build_pack(vault, model) -> dict:
    """Return one strict, deterministic ``enge.knowledge-pack`` snapshot."""
    pages: list[dict] = []
    by_slug: dict[str, list[dict]] = {}
    source_pages: dict[str, dict] = {}

    for folder in model.folders:
        root = vault.root / folder
        if not root.exists():
            continue
        kind = _kind(model, folder)
        for path in sorted(root.glob("*.md")):
            text = path.read_text(encoding="utf-8", errors="replace")
            frontmatter = _frontmatter.parse_frontmatter(text)
            slug = _bounded(frontmatter.get("slug") or path.stem, 120)
            page = {
                "path": path,
                "folder": folder,
                "kind": kind,
                "slug": slug,
                "id": _safe_id("academy", vault.slug, kind, slug),
                "title": _bounded(frontmatter.get("title") or _first_h1(text) or path.stem, 300),
                "text": text,
                "frontmatter": frontmatter,
                "updated_at": _page_updated(path, frontmatter),
            }
            pages.append(page)
            by_slug.setdefault(slug, []).append(page)
            if kind == "source":
                source_pages[slug] = {
                    **page,
                    "creator": _bounded(frontmatter.get("channel") or frontmatter.get("creator"), 240),
                    "url": _bounded(frontmatter.get("url"), 2_000),
                    "published_at": _bounded(frontmatter.get("published"), 80),
                    "rights": _bounded(frontmatter.get("rights") or "reference-only", 120),
                }

    if not pages:
        raise ValueError("This Riverfed wiki has no publishable markdown pages")
    if len(pages) > MAX_ITEMS:
        raise ValueError(f"This Riverfed wiki has {len(pages)} pages; the Writer bridge limit is {MAX_ITEMS}")

    reverse_sources: dict[str, list[str]] = {}
    for source in source_pages.values():
        fm = source["frontmatter"]
        for spec in model.links.values():
            if spec.get("from") != "source":
                continue
            for target in _frontmatter.as_list(fm.get(spec.get("field"))):
                reverse_sources.setdefault(target, []).append(source["slug"])

    items = []
    for page in pages:
        fm = page["frontmatter"]
        body = _page_body(page["text"])
        summary = (
            _first_paragraph(_section(page["text"], "TL;DR"))
            or _first_paragraph(_section(page["text"], "What it is"))
            or _first_paragraph(body)
            or page["title"]
        )
        why = (
            _first_paragraph(_section(page["text"], "Why it matters"))
            or _first_paragraph(_section(page["text"], "Callout"))
            or "Use this Riverfed page as working knowledge; verify claims against its recorded sources."
        )
        source_slugs = _frontmatter.as_list(fm.get("sources")) or reverse_sources.get(page["slug"], [])
        if page["kind"] == "source":
            source_slugs = [page["slug"]]
        refs = [_source_ref(source_pages[slug]) for slug in dict.fromkeys(source_slugs) if slug in source_pages][:30]

        relationships = []
        for target_slug in dict.fromkeys(_WIKILINK_RE.findall(body)):
            targets = by_slug.get(target_slug.strip(), [])
            if len(targets) != 1 or targets[0]["id"] == page["id"]:
                continue
            relationships.append({"targetId": targets[0]["id"], "type": "wiki-link"})
            if len(relationships) >= 30:
                break

        tags = [tag for tag in _frontmatter.as_list(fm.get("tags")) if tag][:30]
        item = {
            "id": page["id"],
            "kind": page["kind"],
            "lane": _lane(page["kind"], fm),
            "title": page["title"],
            "summary": _bounded(summary, 1_200),
            "body": body or f"# {page['title']}",
            "whyItMatters": _bounded(why, 1_200),
            "tags": [_bounded(tag, 80) for tag in tags],
            "sourceRefs": refs,
            "updatedAt": page["updated_at"],
        }
        if relationships:
            item["relationships"] = relationships
        item["digest"] = hashlib.sha256(
            json.dumps(item, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        items.append(item)

    items.sort(key=lambda item: (item["lane"], item["kind"], item["title"].lower()))
    index_path = vault.root / "index.md"
    index_text = index_path.read_text(encoding="utf-8", errors="replace") if index_path.exists() else ""
    index_fm = _frontmatter.parse_frontmatter(index_text)
    updated_at = max(item["updatedAt"] for item in items)
    name = _bounded(vault.display_name(), 300)
    pack = {
        "schema": "enge.knowledge-pack",
        "version": 1,
        "id": _safe_id("academy", vault.slug),
        "name": name,
        "description": _bounded(
            index_fm.get("description") or _first_paragraph(_page_body(index_text))
            or f"Private knowledge published from the {name} Riverfed wiki.",
            1_200,
        ),
        "library": {
            "owner": _bounded(index_fm.get("owner") or "Riverfed", 200),
            "visibility": "private",
            "lanes": [lane for lane in ("craft", "research") if any(item["lane"] == lane for item in items)],
        },
        "publishedAt": updated_at,
        "updatedAt": updated_at,
        "rights": _bounded(
            index_fm.get("rights")
            or "Private Riverfed wiki. Source rights remain with their recorded owners.",
            300,
        ),
        "items": items,
    }
    pack["digest"] = hashlib.sha256(
        json.dumps(pack, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return pack
