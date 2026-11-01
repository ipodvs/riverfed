#!/usr/bin/env python3
"""Wiki link-integrity linter — fail on dangling [[wikilinks]].

Scans every knowledge base (or one, via --wiki) for Obsidian wikilinks
whose target doesn't resolve to a page in that vault. Targets resolve the
way Obsidian resolves them: by file stem anywhere in the vault (model
folders + vault root), case-insensitively, with entity `aliases:`
honoured. `[[slug#Heading]]` checks the slug only; `[[slug|display]]`
checks the slug only; fenced code blocks and inline code spans are
ignored (SCHEMA.md is full of example links).

Internal markdown links to .md files ([text](../topics/foo.md)) are a
style violation per SCHEMA.md — reported as warnings (obsidian_pass.py
converts them), but they don't fail the run.

Usage:
    py -3.13 wiki/scripts/lint_links.py                # all vaults
    py -3.13 wiki/scripts/lint_links.py --wiki wiki    # one vault
Exit codes: 0 = clean, 1 = dangling links found, 2 = vault not found.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _wikis import PROJECT_DIR, Vault, discover_vaults, display_path, resolve_vault  # noqa: E402
from model_registry import load_model_for_vault  # noqa: E402

WIKILINK_RE = re.compile(r"!?\[\[([^\][|#\n]+)(?:#[^\][|\n]*)?(?:\|[^\][\n]*)?\]\]")
MD_INTERNAL_LINK_RE = re.compile(r"\[[^\]\n]*\]\((?!https?://|mailto:)([^)\s]+\.md)[^)]*\)")
FENCE_RE = re.compile(r"^(```|~~~)")
INLINE_CODE_RE = re.compile(r"`[^`\n]*`")
ALIAS_LINE_RE = re.compile(r"^aliases:\s*\[(.*)\]\s*$")


def _vault_pages(vault: Vault) -> list[Path]:
    """Every markdown page in the vault: model folders + root-level files
    (index.md, log.md, SCHEMA.md)."""
    try:
        folders = list(load_model_for_vault(vault).folders)
    except Exception:
        folders = [d.name for d in vault.root.iterdir()
                   if d.is_dir() and not d.name.startswith(".")]
    pages = sorted(vault.root.glob("*.md"))
    for folder in folders:
        d = vault.root / folder
        if d.exists():
            pages.extend(sorted(d.glob("*.md")))
    return pages


def _valid_targets(vault: Vault, pages: list[Path]) -> set[str]:
    """Everything a [[wikilink]] may point at: page stems + filenames +
    frontmatter aliases, casefolded."""
    targets: set[str] = set()
    for p in pages:
        targets.add(p.stem.casefold())
        targets.add(p.name.casefold())
        try:
            head = p.read_text(encoding="utf-8", errors="replace").splitlines()[:30]
        except OSError:
            continue
        for line in head:
            m = ALIAS_LINE_RE.match(line.strip())
            if m:
                for alias in m.group(1).split(","):
                    alias = alias.strip().strip('"').strip("'")
                    if alias:
                        targets.add(alias.casefold())
    return targets


def _scannable_text(text: str) -> str:
    """Drop fenced code blocks + inline code spans (example links live there)."""
    out: list[str] = []
    in_fence = False
    for line in text.splitlines():
        if FENCE_RE.match(line.strip()):
            in_fence = not in_fence
            continue
        if not in_fence:
            out.append(INLINE_CODE_RE.sub("", line))
    return "\n".join(out)


def lint_vault(vault: Vault) -> tuple[int, int]:
    """Returns (dangling_count, style_warning_count) for one vault."""
    pages = _vault_pages(vault)
    targets = _valid_targets(vault, pages)
    rel_root = display_path(vault.root)

    dangling = 0
    warnings = 0
    for p in pages:
        try:
            text = _scannable_text(p.read_text(encoding="utf-8", errors="replace"))
        except OSError:
            continue
        rel = p.relative_to(vault.root).as_posix()
        for m in WIKILINK_RE.finditer(text):
            target = m.group(1).strip()
            if not target:
                continue
            key = target.casefold()
            if key.endswith(".md"):
                key = key[:-3]
            if key not in targets:
                dangling += 1
                print(f"  DANGLING  {rel}: [[{target}]]")
        for m in MD_INTERNAL_LINK_RE.finditer(text):
            warnings += 1
            print(f"  style     {rel}: markdown link to {m.group(1)} "
                  f"(use a wikilink; obsidian_pass.py converts these)")

    status = "OK" if dangling == 0 else f"{dangling} dangling"
    print(f"[{rel_root}] {len(pages)} pages, {status}"
          + (f", {warnings} style warning(s)" if warnings else ""))
    return dangling, warnings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Lint wiki link integrity.")
    parser.add_argument("--wiki", default=None,
                        help="Knowledge-base slug (default: every vault).")
    args = parser.parse_args(argv)

    if args.wiki:
        vault = resolve_vault(args.wiki)
        if vault is None or not vault.exists():
            print(f"Knowledge base '{args.wiki}' not found.", file=sys.stderr)
            return 2
        vaults = [vault]
    else:
        vaults = discover_vaults()

    total_dangling = 0
    for vault in vaults:
        d, _ = lint_vault(vault)
        total_dangling += d
    return 1 if total_dangling else 0


if __name__ == "__main__":
    sys.exit(main())
