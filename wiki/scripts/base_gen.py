#!/usr/bin/env python3
"""Generate Obsidian Bases (`.base` files) into a vault from its knowledge
model's templates.

A Base is a YAML file Obsidian renders as database-style views (table/cards)
over page frontmatter. It is a LENS, never a source of truth: it contains no
knowledge, only view config, and every field it reads is frontmatter the
`/wiki` browser surface reads too. Nothing outside Obsidian parses `.base` —
`lint_links.py` and `obsidian_pass.py` glob `*.md` only — so emitted files are
inert to the rest of the pipeline and to CI.

Why templates instead of hand-written per-vault files: the templates are
`str.format` templates interpolated with the model's own `promote_after`
knobs, so a view can never state a stale threshold. Change
`concepts.promote_after` to 4 in the manifest (or via the Customize modal,
which writes `models/custom/<id>/`) and the next obsidian_pass regenerates the
view to match — the same guarantee the ingest prompts already have.

Why the view YAML lives in `models/<id>/bases/<name>.base` rather than in the
manifest front matter: a Base's `views:` is irreducibly a block list of
mappings, and the manifest dialect (design_tokens._parse_front_matter) parses
scalars, nested mappings and `{ inline: mappings }` only. The manifest
therefore DECLARES bases (`bases: { promotion-health: { title: ... } }`) and
the companion files DEFINE them — the same split already used for SCHEMA.md
and the prompt templates.

Ownership contract (the ledger): generated bases are owned by the model.
Edit one in Obsidian and the pipeline stops touching that file; delete it, or
pass --force-bases, to re-adopt the model's version. Save-As under a new name
to keep both — undeclared names are never touched. This matters because
obsidian_pass runs after EVERY ingest, so an always-regenerate policy would
silently destroy a column tweak hours after it was made.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

# Top-level keys Obsidian recognises in a .base file.
ALLOWED_TOP_KEYS = {"filters", "formulas", "properties", "summaries", "views"}

LEDGER_NAME = "bases.json"

# Status values returned by generate_bases(), in order of interest.
WROTE = "wrote"          # created or updated from the model
UNCHANGED = "unchanged"  # already byte-identical to the model's version
SKIPPED = "skipped"      # user-modified; left alone (--force-bases overrides)
FAILED = "failed"        # template missing or unrenderable


def _norm(text: str) -> str:
    """Newline-normalize so hashes are stable across Windows and macOS."""
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _digest(text: str) -> str:
    return hashlib.sha256(_norm(text).encode("utf-8")).hexdigest()


def base_format_args(model, slug: str = "wiki",
                     title: str = "Wiki") -> dict[str, Any]:
    """Placeholders available to a `.base` template:

    `{topic_promote_after}` / `{entity_promote_after}` / `{concept_promote_after}`
    (one per folder declaring `promote_after`, keyed by node kind),
    `{capture_folder}` (the model's capture layer, e.g. `sources`),
    `{wiki_slug}`, `{wiki_title}`.
    """
    args: dict[str, Any] = dict(model.prompt_format_args())
    args["capture_folder"] = model.capture_folder()
    args["wiki_slug"] = slug
    args["wiki_title"] = title
    return args


def render_base(model, name: str, args: dict[str, Any] | None = None) -> str:
    """Render one declared base to its final YAML text.

    Raises FileNotFoundError if the template is missing, or KeyError/ValueError
    if it contains an unknown placeholder or an unescaped literal brace (write
    templates in block style so only placeholders use braces).
    """
    template = model.base_template(name)
    text = template.format(**(args if args is not None
                              else base_format_args(model)))
    if not text.endswith("\n"):
        text += "\n"
    return _norm(text)


def check_rendered(text: str) -> None:
    """Structural sanity check on rendered Base YAML. Deliberately not a YAML
    parse — CI is stdlib-only by charter (no PyYAML), and semantic correctness
    of the shipped views is established by opening them in Obsidian once."""
    lines = _norm(text).split("\n")
    for i, line in enumerate(lines, 1):
        if line.startswith("\t") or (line.strip() and "\t" in line[:len(line) - len(line.lstrip())]):
            raise ValueError(f"line {i}: tab indentation (YAML forbids tabs)")
    top: list[str] = []
    for line in lines:
        if not line or line.startswith((" ", "#", "-")):
            continue
        if ":" in line:
            top.append(line.split(":", 1)[0].strip())
    unknown = [k for k in top if k not in ALLOWED_TOP_KEYS]
    if unknown:
        raise ValueError(
            f"unknown top-level key(s) {unknown} — expected a subset of "
            f"{sorted(ALLOWED_TOP_KEYS)}")
    if "views" not in top:
        raise ValueError("no `views:` section — the Base would render nothing")


def _load_ledger(vault) -> dict[str, str]:
    p = vault.state_dir / LEDGER_NAME
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return {str(k): str(v) for k, v in data.items()} \
        if isinstance(data, dict) else {}


def _save_ledger(vault, ledger: dict[str, str]) -> None:
    try:
        vault.state_dir.mkdir(parents=True, exist_ok=True)
        (vault.state_dir / LEDGER_NAME).write_text(
            json.dumps(ledger, indent=2, sort_keys=True) + "\n",
            encoding="utf-8", newline="\n")
    except OSError:
        pass  # a missing ledger only costs us the "adopt silently" path


def generate_bases(vault, model, force: bool = False
                   ) -> list[tuple[str, str, str]]:
    """Emit every base the model declares into the vault root.

    Returns [(name, status, detail)] — status is one of WROTE / UNCHANGED /
    SKIPPED / FAILED. Never raises: a broken template degrades to FAILED for
    that base so an ingest is never lost to a view problem.

    Decision per base, given the file on disk, the freshly rendered desired
    content, and the sha256 recorded when we last wrote it:
      - absent                       -> write
      - identical to desired         -> unchanged (adopt into the ledger)
      - differs, ledger says it's ours -> write (a knob changed upstream)
      - differs, ledger disagrees or is absent -> skip; the user owns it
    `.state/` is gitignored, so on a second machine there is no ledger and an
    identical file is adopted silently while a divergent one is skipped loudly.
    """
    results: list[tuple[str, str, str]] = []
    if not model.bases:
        return results
    ledger = _load_ledger(vault)
    args = base_format_args(model, vault.slug, vault.display_name())
    dirty = False

    for name in model.bases:
        path = vault.root / f"{name}.base"
        try:
            desired = render_base(model, name, args)
            check_rendered(desired)
        except Exception as exc:
            results.append((name, FAILED, str(exc)))
            continue

        if not path.exists():
            try:
                path.write_text(desired, encoding="utf-8", newline="\n")
            except OSError as exc:
                results.append((name, FAILED, str(exc)))
                continue
            ledger[name] = _digest(desired)
            dirty = True
            results.append((name, WROTE, "created"))
            continue

        try:
            current = path.read_text(encoding="utf-8")
        except OSError as exc:
            results.append((name, FAILED, str(exc)))
            continue

        if _norm(current) == desired:
            if ledger.get(name) != _digest(desired):
                ledger[name] = _digest(desired)
                dirty = True
            results.append((name, UNCHANGED, ""))
            continue

        ours = ledger.get(name) == _digest(current)
        if ours or force:
            try:
                path.write_text(desired, encoding="utf-8", newline="\n")
            except OSError as exc:
                results.append((name, FAILED, str(exc)))
                continue
            ledger[name] = _digest(desired)
            dirty = True
            results.append((name, WROTE,
                            "forced" if (force and not ours) else "updated"))
        else:
            results.append((name, SKIPPED, "edited outside the pipeline"))

    if dirty:
        _save_ledger(vault, ledger)
    return results
