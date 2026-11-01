"""List transcripts in a vault's staging output/ that don't have a matching
wiki source page.

Used by the ingest workflow:
    py -3.13 wiki/scripts/pending.py                    # legacy wiki/ vault
    py -3.13 wiki/scripts/pending.py --wiki investing   # a wikis/<slug>/ vault
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _wikis import PROJECT_DIR, display_path, resolve_vault  # noqa: E402
import _transcript  # noqa: E402
from model_registry import load_model_for_vault  # noqa: E402


def slugify(s: str, max_len: int = 80) -> str:
    """Match the slugify in convert.py so we generate stable slugs."""
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = re.sub(r"[^\w\s-]", "", s).strip().lower()
    s = re.sub(r"[-\s]+", "-", s)
    return s[:max_len].rstrip("-") or "untitled"


def extract_title(md_path: Path) -> str | None:
    """Pull the title from the source frontmatter or first H1."""
    try:
        text = md_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    return extract_title_text(text, md_path.stem)


def extract_title_text(text: str, fallback: str = "untitled") -> str:
    """Pull a title from already-read source markdown."""
    for line in text.splitlines()[:60]:
        m = re.match(r"^title:\s*(.+)$", line)
        if m:
            return m.group(1).strip().strip('"').strip("'")
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return fallback


def frontmatter_value(text: str, key: str) -> str:
    """Read a scalar from the small JSON-compatible conversion frontmatter."""
    match = re.search(rf"^{re.escape(key)}:\s*(.+?)\s*$", text[:4000], re.M)
    if not match:
        return ""
    raw = match.group(1).strip()
    try:
        value = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        value = raw.strip('"').strip("'")
    return str(value) if value is not None else ""


# YouTube video id from a watch?v= / youtu.be URL — the reliable identity of
# a transcript, independent of how it was slugged or re-titled.
_VIDEO_ID_RE = re.compile(r"(?:watch\?v=|youtu\.be/)([A-Za-z0-9_-]{6,})")


def video_id(text: str) -> str | None:
    m = _VIDEO_ID_RE.search(text or "")
    return m.group(1) if m else None


def existing_source_slugs(sources_dir: Path) -> set[str]:
    if not sources_dir.exists():
        return set()
    slugs: set[str] = set()
    for p in sources_dir.glob("*.md"):
        slugs.add(p.stem)
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for line in text.splitlines()[:30]:
            m = re.match(r"^source_file:\s*(.+)$", line)
            if m:
                src = m.group(1).strip().strip('"').strip("'")
                src_path = (p.parent / src).resolve()
                slugs.add(src_path.stem)
    return slugs


def existing_source_video_ids(sources_dir: Path) -> set[str]:
    """Every YouTube video id already covered by a wiki source page —
    collected from `url:` AND `alt_url:` in each page's frontmatter. This is
    what catches re-conversions and SEO re-uploads: the ingest agent merges a
    duplicate video into an existing page via `alt_url`, and slugs pages by
    dropping editorial prefixes, so the output filename rarely matches the
    page slug — but the video id always does."""
    ids: set[str] = set()
    if not sources_dir.exists():
        return ids
    for p in sources_dir.glob("*.md"):
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for line in text.splitlines()[:30]:
            if re.match(r"^(alt_)?url:", line):
                vid = video_id(line)
                if vid:
                    ids.add(vid)
    return ids


def describe_pending(path: Path) -> dict:
    """Return editor-ready source metadata and transcript guard diagnostics."""
    text = path.read_text(encoding="utf-8", errors="replace")
    title = extract_title_text(text, path.stem)
    source = frontmatter_value(text, "source")
    source_type = frontmatter_value(text, "type") or "file"
    converted_at = frontmatter_value(text, "converted_at")
    readiness = _transcript.diagnose(text, path.name)
    frames_dir = path.with_name(path.stem + "-frames")
    return {
        "path": display_path(path),
        "filename": path.name,
        "title": title,
        "slug": slugify(title),
        "source": source,
        "source_type": source_type,
        "converted_at": converted_at,
        "has_frames": (
            "\n## Visual content" in text
            or (frames_dir.is_dir() and any(frames_dir.glob("*.jpg")))
        ),
        "readiness": readiness,
        "_mtime_ns": path.stat().st_mtime_ns,
    }


def _source_key(item: dict) -> str:
    """Stable logical-source key used to collapse conversion revisions."""
    vid = video_id(item.get("source", ""))
    if vid:
        return f"youtube:{vid}"
    source = item.get("source", "").strip().lower()
    return f"source:{source}" if source else f"file:{item['filename']}"


def _prefer_revision(current: dict, candidate: dict) -> dict:
    """Prefer a usable revision, then the newest attempt."""
    current_ready = current["readiness"]["status"] == "ready"
    candidate_ready = candidate["readiness"]["status"] == "ready"
    if current_ready != candidate_ready:
        return candidate if candidate_ready else current
    return candidate if candidate["_mtime_ns"] >= current["_mtime_ns"] else current


def collect_pending(vault, model) -> list[dict]:
    """Collect one editor row per logical source, with best revision selected."""
    if not vault.output.exists():
        return []
    capture_dir = vault.root / model.capture_folder()
    known = existing_source_slugs(capture_dir)
    known_ids = existing_source_video_ids(capture_dir)
    grouped: dict[str, dict] = {}
    for path in sorted(vault.output.glob("*.md")):
        if path.stem in known:
            continue
        try:
            item = describe_pending(path)
        except OSError:
            continue
        vid = video_id(item["source"])
        if vid and vid in known_ids:
            continue
        key = _source_key(item)
        grouped[key] = (
            _prefer_revision(grouped[key], item) if key in grouped else item
        )
    items = sorted(grouped.values(), key=lambda item: item["filename"])
    for item in items:
        item.pop("_mtime_ns", None)
    return items


def pending_payload(vault, model) -> dict:
    items = collect_pending(vault, model)
    ready_count = sum(
        item["readiness"]["status"] == "ready" for item in items
    )
    return {
        "pending": items,
        "count": len(items),
        "ready_count": ready_count,
        "blocked_count": len(items) - ready_count,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="List transcripts pending ingestion into a knowledge base.")
    parser.add_argument("--wiki", default="wiki",
                        help="Knowledge-base slug ('wiki' = the original vault).")
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit structured source-readiness data for the local editor.",
    )
    args = parser.parse_args(argv)

    vault = resolve_vault(args.wiki)
    if vault is None or not vault.exists():
        message = f"Knowledge base '{args.wiki}' not found."
        if args.json:
            print(json.dumps({"error": message}))
        else:
            print(message, file=sys.stderr)
        return 1

    # The model's capture folder holds the 1:1 transcript pages that mark a
    # transcript as ingested (karpathy-wiki: sources/, second-brain: sources/).
    try:
        model = load_model_for_vault(vault)
    except (FileNotFoundError, ValueError) as exc:
        if args.json:
            print(json.dumps({"error": str(exc)}))
        else:
            print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    payload = pending_payload(vault, model)
    pending = payload["pending"]
    if args.json:
        print(json.dumps(payload, ensure_ascii=False))
        return 0

    if not pending:
        print("No pending transcripts. Wiki is up to date.")
        return 0

    print(f"Pending transcripts ({len(pending)}):")
    for item in pending:
        readiness = item["readiness"]
        print(f"  - {item['path']}")
        print(f"      title : {item['title']}")
        print(f"      slug  : {item['slug']}  (suggested)")
        print(f"      status: {readiness['status']}")
        if readiness["problem"]:
            print(f"      issue : {readiness['problem']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
