"""Rewrite the wiki for Obsidian-native conventions.

What it does (idempotent — safe to re-run):

1. Convert internal markdown links to wikilinks.
     [text](../topics/foo.md)   ->  [[foo|text]]   (or [[foo]] if text == foo)
     [text](./bar.md)           ->  [[bar|text]]   (or [[bar]])
   External http(s):// links are left alone. Anchor-only links (#section) are
   left alone. Image links are left alone.

2. Add a `tags:` frontmatter field on every page, populated from existing
   `topics:` + `entities:` + the page's `kind:` (for entities). Tags are
   merged with any existing `tags:` (deduplicated, no clobber).

3. Add `aliases:` to entity pages where the slug differs from the canonical
   name (best-effort heuristic from the H1 title).

Run from anywhere:
    py -3.13 wiki/scripts/obsidian_pass.py                    # legacy wiki/ vault
    py -3.13 wiki/scripts/obsidian_pass.py --wiki investing   # a wikis/<slug>/ vault
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _wikis import PROJECT_DIR, display_path, resolve_vault  # noqa: E402
from _frontmatter import as_list, split_frontmatter  # noqa: E402

# Top-level vault folders that are NOT wiki pages: per-vault transcript
# staging (sources are immutable!), shared scripts, state, editor config.
_SKIP_TOP_FOLDERS = {"output", "scripts", ".state", ".obsidian"}


def _is_page(p: Path, wiki_dir: Path) -> bool:
    try:
        rel = p.relative_to(wiki_dir)
    except ValueError:
        return False
    return not (rel.parts and rel.parts[0] in _SKIP_TOP_FOLDERS)

LINK_RE = re.compile(r"(?<!\!)\[([^\]]+)\]\(([^)]+)\)")  # ignores ![image]() links


# split_frontmatter (block + inline list parsing) is shared — imported above.


def render_frontmatter(fm: dict, original_raw: str) -> str:
    """Write back the frontmatter. Preserves original key order, appends new
    keys. A key whose value we rewrite is re-serialized inline; when the
    original wrote it as a YAML block list, the trailing `- item` lines are
    consumed so we don't leave a stale block behind the new inline value."""
    lines = original_raw.splitlines()
    seen_keys: set[str] = set()
    out: list[str] = []
    i, n = 0, len(lines)
    while i < n:
        line = lines[i]
        m = re.match(r"^([\w_-]+)\s*:", line)
        if not m:
            out.append(line)
            i += 1
            continue
        key = m.group(1)
        # Span any block-list continuation lines (`- item`) that belong to it.
        j = i + 1
        while j < n and (lines[j].strip().startswith("- ")
                         or lines[j].strip() == "-"):
            j += 1
        if key in fm:
            out.append(_serialize(key, fm[key]))
        else:
            out.extend(lines[i:j])
        seen_keys.add(key)
        i = j
    for key, value in fm.items():
        if key not in seen_keys:
            out.append(_serialize(key, value))
    return "---\n" + "\n".join(out) + "\n---\n"


# Characters that make a plain (unquoted) YAML scalar invalid or ambiguous
# at the start of the value. A title like `"Learn AI" Is Bad Advice` MUST be
# quoted or Obsidian's properties parser rejects the whole frontmatter block.
_YAML_UNSAFE_LEAD = tuple("\"'#&*!|>%@`[]{},")


def _needs_quoting(value: str) -> bool:
    return bool(value) and (
        value != value.strip()
        or value.startswith(_YAML_UNSAFE_LEAD)
        or value.startswith(("- ", "? ", ": "))
        or ":" in value
        or " #" in value
    )


def _quote(value: str) -> str:
    if '"' in value:
        return "'" + value.replace("'", "''") + "'"
    return f'"{value}"'


def _serialize(key: str, value) -> str:
    if isinstance(value, list):
        inner = ", ".join(value)
        return f"{key}: [{inner}]"
    if isinstance(value, str) and _needs_quoting(value):
        return f"{key}: {_quote(value)}"
    return f"{key}: {value}"


def build_slug_index(wiki_dir: Path) -> dict[str, Path]:
    """Map every page's stem to its path. Wikilinks resolve by stem in Obsidian."""
    index: dict[str, Path] = {}
    for p in wiki_dir.rglob("*.md"):
        if _is_page(p, wiki_dir):
            index[p.stem] = p
    return index


def convert_links(body: str, slug_index: dict[str, Path]) -> str:
    """Rewrite internal [.](.md) links as wikilinks."""

    def repl(match: re.Match) -> str:
        text = match.group(1)
        target = match.group(2).strip()
        # leave external URLs alone
        if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", target):
            return match.group(0)
        # leave anchors and email links alone
        if target.startswith("#") or target.startswith("mailto:"):
            return match.group(0)
        # strip optional anchor on the target
        anchor = ""
        if "#" in target:
            target, anchor = target.split("#", 1)
            anchor = "#" + anchor
        # only convert .md links
        if not target.endswith(".md"):
            return match.group(0)
        stem = Path(target).stem
        if stem not in slug_index:
            # unresolved — leave as-is so we don't silently break it
            return match.group(0)
        link_body = stem + anchor
        if text.strip() == stem:
            return f"[[{link_body}]]"
        return f"[[{link_body}|{text}]]"

    return LINK_RE.sub(repl, body)


def humanize(slug: str) -> str:
    return slug.replace("-", " ")


def alias_candidates(slug: str, title: str | None) -> list[str]:
    """Compute aliases to add to entity pages."""
    aliases: list[str] = []
    if title:
        clean = title.strip()
        if clean and clean != slug:
            aliases.append(clean)
    human = humanize(slug)
    if human != slug and human not in aliases:
        aliases.append(human)
    return aliases


def extract_first_h1(body: str) -> str | None:
    for line in body.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return None


def merge_tags(existing, new_tags: list[str]) -> list[str]:
    if existing is None:
        existing = []
    if isinstance(existing, str):
        existing = [existing]
    seen: set[str] = set()
    out: list[str] = []
    for t in list(existing) + new_tags:
        if t and t not in seen:
            seen.add(t)
            out.append(t)
    return out


def process_file(path: Path, slug_index: dict[str, Path],
                 wiki_dir: Path, page_folders: set[str],
                 relation_fields: dict[str, list[str]]) -> bool:
    """Process a single markdown file. Returns True if it was modified.

    `relation_fields` maps each page folder to the frontmatter list-fields
    that carry its relationships (derived from the vault's model manifest —
    karpathy source pages contribute `topics`/`entities`, PARA sources
    contribute `projects`/`areas`/`resources`, etc). Relationship values are
    added to the page's tags as raw slugs, matching the pre-model behavior
    for topics/entities."""
    text = path.read_text(encoding="utf-8")
    fm, raw_fm, body = split_frontmatter(text)
    if not raw_fm:
        return False  # no frontmatter -> skip silently (probably README-like)

    new_body = convert_links(body, slug_index)

    # Build tags — relationship-derived tags follow the model manifest, not a
    # fixed topics/entities pair. `as_list` guards a malformed scalar field.
    tag_sources: list[str] = []
    for key in relation_fields.get(path.parent.name, ()):
        tag_sources.extend(as_list(fm.get(key)))
    # mark kind on entity pages
    if path.parent.name == "entities":
        kind = fm.get("kind")
        if isinstance(kind, str) and kind:
            tag_sources.append(f"kind/{kind}")
    # what kind of page is this? Pages directly under one of the model's
    # page folders get a wiki/<folder> class tag (karpathy's sources/topics/
    # entities/concepts, PARA's projects/areas/…); everything else (vault
    # root, training/, …) gets the bare "wiki" tag.
    tag_sources.append(f"wiki/{path.parent.name}"
                       if path.parent.name in page_folders
                       and path.parent.parent == wiki_dir
                       else "wiki")
    fm["tags"] = merge_tags(fm.get("tags"), tag_sources)

    # Build aliases for entity pages
    if path.parent.name == "entities":
        h1 = extract_first_h1(body)
        candidates = alias_candidates(path.stem, h1)
        if candidates:
            fm["aliases"] = merge_tags(fm.get("aliases"), candidates)

    new_text = render_frontmatter(fm, raw_fm) + new_body
    if new_text != text:
        path.write_text(new_text, encoding="utf-8")
        return True
    return False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Normalize wikilinks/tags/aliases across a knowledge base.")
    parser.add_argument("--wiki", default="wiki",
                        help="Knowledge-base slug ('wiki' = the original vault).")
    parser.add_argument("--force-bases", action="store_true",
                        help="Overwrite Obsidian Bases (.base) that were "
                             "edited outside the pipeline, re-adopting the "
                             "model's version.")
    args = parser.parse_args(argv)

    vault = resolve_vault(args.wiki)
    if vault is None or not vault.root.exists():
        print(f"Knowledge base '{args.wiki}' not found.", file=sys.stderr)
        return 1
    wiki_dir = vault.root

    # The model's folders bound the wiki/<folder> page-class tags, and its
    # link specs bind which frontmatter fields become relationship tags per
    # folder. Fall back to the karpathy layout if the manifest can't load —
    # never block a lint pass on a registry problem.
    model = None
    try:
        from model_registry import load_model_for_vault
        model = load_model_for_vault(vault)
        page_folders = set(model.folders)
        # folder -> relation fields = the `field`s of every link spec whose
        # `from` kind matches that folder's kind.
        relation_fields: dict[str, list[str]] = {}
        for folder in model.folders:
            kind = model.kind(folder)
            relation_fields[folder] = [
                spec["field"] for spec in model.links.values()
                if spec.get("from") == kind and spec.get("field")]
    except Exception:
        page_folders = {"sources", "topics", "entities", "concepts"}
        relation_fields = {"sources": ["topics", "entities"]}

    slug_index = build_slug_index(wiki_dir)
    modified = 0
    skipped = 0
    for p in sorted(wiki_dir.rglob("*.md")):
        # skip scripts/ (free-form instructions), output/ (immutable
        # transcripts), .state/, .obsidian/
        if not _is_page(p, wiki_dir):
            continue
        if process_file(p, slug_index, wiki_dir, page_folders, relation_fields):
            print(f"  rewrote {display_path(p)}")
            modified += 1
        else:
            skipped += 1
    print(f"\n{modified} file(s) rewritten, {skipped} unchanged.")

    # Obsidian Bases — regenerated from the model's templates so a view can
    # never state a stale promotion threshold. Best-effort: a view problem
    # must never fail a lint pass (this runs inside every ingest).
    if model is not None and getattr(model, "bases", None):
        try:
            import base_gen
            results = base_gen.generate_bases(vault, model,
                                              force=args.force_bases)
        except Exception as exc:                      # pragma: no cover
            print(f"  bases: skipped ({exc})")
            results = []
        for name, status, detail in results:
            suffix = f" — {detail}" if detail else ""
            if status == base_gen.SKIPPED:
                print(f"  base {name}.base: kept your version{suffix} "
                      "(--force-bases to re-adopt the model's)")
            elif status == base_gen.FAILED:
                print(f"  base {name}.base: FAILED{suffix}")
            else:
                print(f"  base {name}.base: {status}{suffix}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
