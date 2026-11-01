#!/usr/bin/env python3
"""Vault resolution + scaffolding — the foundation for multiple knowledge bases.

A "vault" (knowledge base) is a folder holding the knowledge model's page
folders + SCHEMA.md + index.md, discoverable on disk. Since the C1 vault
split (2026-06-12) knowledge is DATA and lives outside the product repo:

  - **The vault home** — `~/RiverfedVaults/<slug>/` by default, overridable
    via the `RIVERFED_VAULTS_DIR` env var (also read from `<project>/.env`
    so CLI runs resolve identically to the server). Every vault here has
    its own staging at `<slug>/output/`. New vaults scaffold here, and
    each can be its own git repo — your knowledge, versioned in *your*
    repo, not the product's.
  - **Repo demo vaults** — `<project>/wikis/<slug>/` ships publishable
    demo bases with the product (riverfed-ops). A vault-home copy with the
    same slug wins, mirroring the models/designs custom-wins contract.
  - **Legacy fallback** — pre-migration layouts (pages at `<project>/wiki/`
    with staging at `<project>/output/`) keep resolving until
    `migrate_vaults.py` has moved them; CI checkouts (no vault home) see
    only the repo demo vaults.

Slug rules mirror the design-picker id guard: lowercase alnum + dash/underscore.
"""
from __future__ import annotations

import os
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[2]
LEGACY_WIKI_DIR = PROJECT_DIR / "wiki"
WIKIS_PARENT = PROJECT_DIR / "wikis"          # repo-shipped demo vaults
ROOT_OUTPUT = PROJECT_DIR / "output"          # legacy vault's staging

SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
RESERVED = {"output", "wiki", "wikis", "scripts", "training", "designs",
            "landing", "models", "docs", "diagrams", "plans"}


def _env_file_value(key: str) -> str:
    """Minimal .env reader (KEY=value lines) so CLI invocations resolve the
    vault home exactly like the server (which loads .env at startup)."""
    try:
        for line in (PROJECT_DIR / ".env").read_text(
                encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if line.startswith(key + "="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    except OSError:
        pass
    return ""


def vaults_home() -> Path:
    """Where personal vaults live — outside the product repo. Real env var
    wins, then .env, then the default."""
    val = os.environ.get("RIVERFED_VAULTS_DIR", "").strip() \
        or _env_file_value("RIVERFED_VAULTS_DIR")
    return (Path(val).expanduser() if val
            else Path.home() / "RiverfedVaults").resolve()


def display_path(p: Path) -> str:
    """Path for prompts, logs, and API payloads: repo-relative posix when
    inside the project (keeps repo-vault behavior identical to before the
    split), absolute posix for vault-home paths."""
    rp = Path(p).resolve()
    try:
        return rp.relative_to(PROJECT_DIR).as_posix()
    except ValueError:
        return rp.as_posix()


def resolve_vault_dir(arg: str) -> Path:
    """Resolve a studio-style --wiki argument to a directory: repo-relative
    ('wiki', 'wikis/riverfed-ops') or absolute (a vault-home path)."""
    p = Path(arg)
    return (p if p.is_absolute() else PROJECT_DIR / p).resolve()


@dataclass
class Vault:
    slug: str
    root: Path
    output: Path

    @property
    def sources(self) -> Path:
        return self.root / "sources"

    @property
    def topics(self) -> Path:
        return self.root / "topics"

    @property
    def entities(self) -> Path:
        return self.root / "entities"

    @property
    def concepts(self) -> Path:
        return self.root / "concepts"

    @property
    def index(self) -> Path:
        return self.root / "index.md"

    @property
    def schema(self) -> Path:
        return self.root / "SCHEMA.md"

    @property
    def log(self) -> Path:
        return self.root / "log.md"

    @property
    def state_dir(self) -> Path:
        return self.root / ".state"

    def exists(self) -> bool:
        return self.index.exists() and self.schema.exists()

    def display_name(self) -> str:
        """Human title — from index.md frontmatter `name:`, else the slug
        prettified. (Deliberately NOT `title:` — the legacy index titles
        itself "Wiki index", which reads badly in a picker.)"""
        try:
            for line in self.index.read_text(encoding="utf-8",
                                             errors="replace").splitlines()[:20]:
                m = re.match(r"^name:\s*(.+)$", line)
                if m:
                    return m.group(1).strip().strip('"').strip("'")
        except OSError:
            pass
        return self.slug.replace("-", " ").replace("_", " ").title()

    def model_id(self) -> str:
        """The knowledge model this vault follows — index.md frontmatter
        `model:`, defaulting to the original karpathy-wiki layout for
        vaults scaffolded before models existed."""
        try:
            for line in self.index.read_text(encoding="utf-8",
                                             errors="replace").splitlines()[:20]:
                m = re.match(r"^model:\s*(.+)$", line)
                if m:
                    return m.group(1).strip().strip('"').strip("'")
        except OSError:
            pass
        return "karpathy-wiki"


def valid_slug(slug: str) -> bool:
    return bool(slug) and bool(SLUG_RE.match(slug)) and slug not in RESERVED


def resolve_vault(slug: str | None) -> Vault | None:
    """Map a slug to its on-disk Vault. None for an invalid/unknown slug.

    Resolution order:
      "wiki" → <home>/wiki/ if migrated there, else the legacy
               <project>/wiki/ + <project>/output/ pair.
      other  → <home>/<slug>/ if it exists, else the repo demo
               wikis/<slug>/ if it exists, else <home>/<slug>/ as the
               scaffold target for a new vault.
    """
    slug = (slug or "wiki").strip() or "wiki"
    home = vaults_home()
    if slug == "wiki":
        hv = Vault("wiki", home / "wiki", home / "wiki" / "output")
        if hv.exists():
            return hv
        return Vault("wiki", LEGACY_WIKI_DIR, ROOT_OUTPUT)
    if not valid_slug(slug):
        return None

    home_root = (home / slug).resolve()
    try:
        home_root.relative_to(home)                # path-traversal guard
    except ValueError:
        return None
    home_v = Vault(slug, home_root, home_root / "output")
    if home_v.exists():
        return home_v

    repo_root = (WIKIS_PARENT / slug).resolve()
    try:
        repo_root.relative_to(WIKIS_PARENT.resolve())
    except ValueError:
        return None
    repo_v = Vault(slug, repo_root, repo_root / "output")
    if repo_v.exists():
        return repo_v

    return home_v   # not on disk yet → new vaults scaffold into the home


def discover_vaults() -> list[Vault]:
    """Every vault on disk: the `wiki` vault (home or legacy) + each
    vault-home and repo-demo folder that has index.md + SCHEMA.md
    (home wins on slug collision, via resolve_vault)."""
    out: list[Vault] = []
    legacy = resolve_vault("wiki")
    if legacy and legacy.exists():
        out.append(legacy)
    slugs: set[str] = set()
    for parent in (vaults_home(), WIKIS_PARENT):
        if parent.exists():
            for d in sorted(parent.iterdir()):
                if d.is_dir() and d.name != "wiki":
                    slugs.add(d.name)
    for s in sorted(slugs):
        v = resolve_vault(s)
        if v and v.exists():
            out.append(v)
    return out


# Ultimate fallback index, generated from the manifest when a model ships no
# index-template.md (e.g. a custom model created via the API, which writes
# model.md/SCHEMA.md/prompts but no index template). Section headings come
# from the model's own folders, so a PARA/SOP vault no longer starts life with
# a Karpathy-shaped index.
_INDEX_FRONT = """\
---
name: {title}
slug: {slug}
model: {model}
purpose: catalog of every page in the {title} knowledge base
last_updated: {date}
tags: [wiki]
---

# {title} — index

This is the **entry point** for the {title} knowledge base. Every page is
listed here with a one-line summary so an agent can pick what to read deeply.

For the conventions that govern this vault, see [[SCHEMA|SCHEMA.md]].

"""


def _folder_heading(folder: str) -> str:
    return folder.replace("_", " ").replace("-", " ").strip().title()


def _generate_index(km, title: str, slug: str, date: str) -> str:
    """Build a starter index from the model manifest — the capture folder gets
    the 'nothing yet' note, every other folder becomes an empty section, in
    manifest order."""
    capture = km.capture_folder()
    body_parts: list[str] = []
    for folder in km.folders:
        heading = _folder_heading(folder)
        if folder == capture:
            body_parts.append(
                f"## {heading} (1 page per ingested source)\n\n"
                "_(none yet — convert a video or drop a file, then ingest "
                "into this vault)_")
        else:
            body_parts.append(f"## {heading}")
    front = _INDEX_FRONT.format(title=title, slug=slug, date=date, model=km.id)
    return front + "\n\n".join(body_parts) + "\n"


def _render_index(km, title: str, slug: str, date: str) -> str:
    """A new vault's index.md. Prefer the model's own index-template.md (nicer,
    model-appropriate wording — PARA/SOP call the capture layer 'Inbox'); fall
    back to a manifest-generated index for models that ship no template."""
    tmpl = km.index_template()
    if tmpl:
        try:
            return tmpl.format(title=title, slug=slug, date=date, model=km.id)
        except (KeyError, IndexError, ValueError):
            # A stray/typo'd brace in a template must not break scaffolding —
            # degrade to the manifest-generated index.
            pass
    return _generate_index(km, title, slug, date)


def scaffold_vault(slug: str, title: str, date: str,
                   schema_template: Path | None = None,
                   model: str = "karpathy-wiki") -> tuple[Vault | None, str]:
    """Create a new vault on disk following a knowledge model. Returns
    (vault, "") on success or (None, error_message). `date` is passed in
    (callers stamp it — the scripts avoid importing datetime here to stay
    easily testable)."""
    if not valid_slug(slug):
        return None, (f"Invalid name '{slug}'. Use lowercase letters, numbers, "
                      "dashes — and not a reserved word.")
    v = resolve_vault(slug)
    if v is None:
        return None, f"Could not resolve a path for '{slug}'."
    if v.exists():
        return None, f"A knowledge base '{slug}' already exists."

    # Folders + schema template come from the model manifest. Lazy import —
    # model_registry pulls in design_tokens, which most _wikis callers
    # (pending.py, server vault resolution) never need.
    from model_registry import load_model, resolve_model_dir
    model_dir = resolve_model_dir(model)
    if model_dir is None:
        return None, f"Unknown knowledge model '{model}'."
    try:
        km = load_model(model_dir)
    except Exception as exc:
        return None, f"Could not load model '{model}': {exc}"

    root_resolved = v.root.resolve()
    try:
        for folder in km.folders:
            target = (v.root / folder).resolve()
            # Defense in depth: load_model already rejects unsafe folder names,
            # but never create a page folder that resolves outside the vault.
            try:
                target.relative_to(root_resolved)
            except ValueError:
                return None, (f"model '{model}' folder '{folder}' resolves "
                              "outside the vault root — refusing to scaffold")
            target.mkdir(parents=True, exist_ok=True)
        v.output.mkdir(parents=True, exist_ok=True)   # per-vault staging
        # SCHEMA.md — the model's canonical template, so the ingest agent
        # follows the model's node/slug rules. `schema_template` overrides
        # (legacy callers), then a minimal fallback.
        tmpl = schema_template or km.schema_path
        if not tmpl.exists():
            tmpl = LEGACY_WIKI_DIR / "SCHEMA.md"
        if tmpl.exists():
            shutil.copyfile(tmpl, v.schema)
        else:
            v.schema.write_text("# SCHEMA\n\n" + "\n".join(
                f"- {f}/" for f in km.folders) + "\n", encoding="utf-8")
        v.index.write_text(
            _render_index(km, title or slug, slug, date),
            encoding="utf-8")
    except OSError as exc:
        return None, f"Failed to create vault: {exc}"

    # Obsidian Bases from the model's templates, so a fresh vault opened in
    # Obsidian has its views on day one. Best-effort — a view problem must
    # never fail vault creation (the views render empty until first ingest
    # anyway, since no page carries a wiki/<folder> tag yet).
    if getattr(km, "bases", None):
        try:
            import base_gen
            base_gen.generate_bases(v, km)
        except Exception:
            pass
    return v, ""
