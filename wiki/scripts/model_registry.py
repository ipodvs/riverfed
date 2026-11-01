#!/usr/bin/env python3
"""Knowledge-model registry — parse models/<id>/model.md manifests into
structured objects the pipeline + server use instead of hardcoding the
sources/topics/entities/concepts layout.

Mirrors design_tokens.py deliberately (same front-matter dialect, same
shipped/custom union, same path-traversal-guarded id rules): a knowledge
MODEL is to a vault what a design preset is to a deck.

Layout on disk:
    models/<id>/model.md             shipped manifests (committed)
    models/<id>/SCHEMA.md            canonical schema template for new vaults
    models/<id>/ingest-prompt.md     per-transcript ingest prompt template
    models/<id>/promote-prompt.md    backlog-promotion prompt template
    models/custom/<id>/model.md      user-created models (gitignored)

Manifest front matter (parsed by design_tokens._parse_front_matter — no
block lists; use `{ inline: mappings }`):
    name: Karpathy Wiki
    description: >
      ...
    folders:
      sources:
        kind: source
        label_field: title
      concepts:
        kind: concept
        promote_after: 3
        weight: { min: 3, bonus: 2 }
        card: { description: What it is, callout: Why it matters }
    links:
      in-topic: { from: source, field: topics, to: topic }
    generators: marp, pptx, diagram, guide
    search_hint: topics, sources, tools, people, ideas

Usage:
    from model_registry import load_model, list_models, load_model_for_vault
    m = load_model(Path("models/karpathy-wiki"))
    m.folders                      # ordered {folder_name: spec}
    m.kind("concepts")             # "concept"
    m.promote_after("concepts")    # 3
    m.prompt_format_args()         # {"topic_promote_after": 2, ...}
    m.ingest_prompt()              # template text, ready for .format()
"""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from design_tokens import _parse_front_matter  # noqa: E402

PROJECT_DIR = Path(__file__).resolve().parents[2]
MODELS_DIR = PROJECT_DIR / "models"
DEFAULT_MODEL_ID = "karpathy-wiki"

# Same shape as _wikis.SLUG_RE — lowercase alnum + dash/underscore, and the
# id always resolves to a folder directly under models/ (or models/custom/),
# so a malicious id can't traverse out.
MODEL_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")

# A model folder name becomes a filesystem path component under the vault
# root (scaffold_vault does `v.root / folder`), so it must be a single safe
# component — same shape as a slug. This rejects `..`, `.`, absolute paths,
# and slashes/backslashes, closing the vault-boundary escape a manifest key
# like `../escaped` would otherwise open.
FOLDER_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
# Names that are real directories/files in a vault but are NOT page folders —
# a model folder must not collide with the per-vault staging or editor/state
# dirs. Mirrors _wikis._SKIP_TOP_FOLDERS + the scaffolded companion files.
RESERVED_FOLDER_NAMES = {"output", "scripts", ".state", ".obsidian",
                         "index", "schema", "log"}


def valid_folder_name(name: str) -> bool:
    """True if `name` is a safe single path component usable as a vault page
    folder (and not a reserved/non-page directory)."""
    return (bool(name) and bool(FOLDER_NAME_RE.match(name))
            and name.lower() not in RESERVED_FOLDER_NAMES)


def valid_base_name(name: str) -> bool:
    """True if `name` is safe as an Obsidian Base filename — it becomes both
    `models/<id>/bases/<name>.base` and `<vault>/<name>.base`, so it must be a
    single path component. Same shape as a folder name, but the page-folder
    reserved list doesn't apply (a `.base` never collides with a page dir)."""
    return bool(name) and bool(FOLDER_NAME_RE.match(name))


def _to_int(v: Any, default: int = 0) -> int:
    try:
        return int(str(v).strip())
    except (TypeError, ValueError):
        return default


@dataclass
class KnowledgeModel:
    """One parsed models/<id>/model.md manifest."""
    id: str = ""
    name: str = ""
    description: str = ""
    # Ordered: manifest order is the canonical folder order (scaffolding,
    # counts, graph iteration all follow it).
    folders: dict[str, dict[str, Any]] = field(default_factory=dict)
    # Edge name → {from: kind, field: frontmatter-list-field, to: kind}
    links: dict[str, dict[str, str]] = field(default_factory=dict)
    # Obsidian Bases this model emits into each vault: name → per-base knobs
    # ({title: ...}). The view YAML itself lives in bases/<name>.base template
    # files — a Base's `views:` is a block list, which the manifest
    # front-matter dialect cannot express.
    bases: dict[str, dict[str, Any]] = field(default_factory=dict)
    generators: list[str] = field(default_factory=list)
    # /wiki search-box hint copy ("Search <hint>"); derived from folder
    # names when empty.
    search_hint: str = ""
    source_path: Path | None = None      # the model.md file
    # Provenance — set by list_models():
    #   "shipped" = models/<id>/ (committed presets)
    #   "custom"  = models/custom/<id>/ (user-created/edited)
    source: str = "shipped"
    overrides_shipped: bool = False

    # --- structure accessors -------------------------------------------------

    @property
    def dir(self) -> Path:
        """The model's directory (holds SCHEMA.md + prompt templates)."""
        assert self.source_path is not None
        return self.source_path.parent

    def kind(self, folder: str) -> str:
        """Node kind for a folder (defaults to the folder name singular-ish)."""
        spec = self.folders.get(folder) or {}
        return str(spec.get("kind") or folder.rstrip("s"))

    def folders_for_kind(self, kind: str) -> list[str]:
        return [f for f in self.folders if self.kind(f) == kind]

    def promote_after(self, folder: str) -> int | None:
        spec = self.folders.get(folder) or {}
        if "promote_after" not in spec:
            return None
        return _to_int(spec.get("promote_after"), 0) or None

    def label_field(self, folder: str) -> str | None:
        spec = self.folders.get(folder) or {}
        v = spec.get("label_field")
        return str(v) if v else None

    def weight_spec(self, folder: str) -> dict[str, int] | None:
        """Graph node sizing rule: weight = max(min, source_count + bonus).
        None = the folder renders at weight 1."""
        spec = self.folders.get(folder) or {}
        w = spec.get("weight")
        if not isinstance(w, dict):
            return None
        return {"min": _to_int(w.get("min"), 1), "bonus": _to_int(w.get("bonus"), 0)}

    def card_spec(self, folder: str) -> dict[str, str] | None:
        """The /wiki MAP card spec for a folder — which `## section`s feed
        the card body (keys: `description`, `callout`; both optional, the
        values are section headings in that folder's pages). An empty
        mapping (`card: {}`) marks a folder browsable with the generic
        lead-paragraph card. None = no card declared."""
        spec = self.folders.get(folder) or {}
        c = spec.get("card")
        if isinstance(c, dict):
            return {str(k): str(v) for k, v in c.items()}
        return None

    def browsable_folders(self) -> list[str]:
        """Folders the /wiki MAP view lists as card sections, in manifest
        order. Folders that declare `card:` win; a manifest with no card
        specs at all falls back to every non-source folder (so a custom
        model gets sensible sections without server edits)."""
        declared = [f for f in self.folders if self.card_spec(f) is not None]
        if declared:
            return declared
        return [f for f in self.folders if self.kind(f) != "source"]

    def prompt_format_args(self) -> dict[str, int]:
        """Per-kind promotion knobs for the prompt templates, e.g.
        {"topic_promote_after": 2, "entity_promote_after": 2,
         "concept_promote_after": 3}."""
        out: dict[str, int] = {}
        for folder in self.folders:
            n = self.promote_after(folder)
            if n is not None:
                out[f"{self.kind(folder)}_promote_after"] = n
        return out

    def capture_folder(self) -> str:
        """The folder whose pages track ingested transcripts 1:1 — pending
        detection keys on it (a transcript is 'done' once a page here
        references its slug or video id). Marked `capture: true` in the
        manifest; falls back to the first folder of kind 'source', then
        the first folder."""
        for folder, spec in self.folders.items():
            if str(spec.get("capture", "")).strip().lower() in {"true", "yes", "1"}:
                return folder
        for folder in self.folders:
            if self.kind(folder) == "source":
                return folder
        return next(iter(self.folders))

    # --- companion files ------------------------------------------------------

    @property
    def schema_path(self) -> Path:
        return self.dir / "SCHEMA.md"

    @property
    def index_path(self) -> Path:
        return self.dir / "index-template.md"

    def index_template(self) -> str | None:
        """The model's starter-index template (index-template.md), or None if
        the model ships none. Placeholders: {title}, {slug}, {model}, {date}."""
        p = self.index_path
        return p.read_text(encoding="utf-8") if p.exists() else None

    def _template(self, filename: str) -> str:
        p = self.dir / filename
        if not p.exists():
            raise FileNotFoundError(
                f"model '{self.id}' has no {filename} (expected {p})")
        return p.read_text(encoding="utf-8")

    def ingest_prompt(self) -> str:
        """The ingest prompt template. Placeholders: {wiki_rel},
        {output_rel}, {transcript_name}, {wiki_slug} + prompt_format_args()."""
        return self._template("ingest-prompt.md")

    def promote_prompt(self) -> str:
        """The backlog-promotion prompt template. Placeholders: {wiki_rel},
        {output_rel}, {wiki_slug} + prompt_format_args()."""
        return self._template("promote-prompt.md")

    @property
    def bases_dir(self) -> Path:
        """Directory holding this model's `.base` view templates."""
        return self.dir / "bases"

    def base_title(self, name: str) -> str:
        """Display/log copy for a declared base (falls back to the name)."""
        spec = self.bases.get(name) or {}
        return str(spec.get("title") or name)

    def base_template(self, name: str) -> str:
        """The raw `.base` template text for a declared base. It is a
        `str.format` template — see base_gen.base_format_args() for the
        placeholders — so thresholds in a view can never go stale against the
        manifest's `promote_after` knobs."""
        p = self.bases_dir / f"{name}.base"
        if not p.exists():
            raise FileNotFoundError(
                f"model '{self.id}' declares base '{name}' but {p} is missing")
        return p.read_text(encoding="utf-8")


def valid_model_id(model_id: str) -> bool:
    return bool(model_id) and bool(MODEL_ID_RE.match(model_id)) \
        and model_id != "custom"


def load_model(path: Path) -> KnowledgeModel:
    """Load a model from its directory (or its model.md path directly)."""
    manifest = path / "model.md" if path.is_dir() else path
    text = manifest.read_text(encoding="utf-8")
    fm = _parse_front_matter(text)

    folders_raw = fm.get("folders")
    if not isinstance(folders_raw, dict) or not folders_raw:
        raise ValueError(f"{manifest}: manifest declares no `folders:`")
    folders: dict[str, dict[str, Any]] = {}
    for fname, spec in folders_raw.items():
        fname = str(fname)
        if not valid_folder_name(fname):
            raise ValueError(
                f"{manifest}: invalid folder name {fname!r} — a folder must be "
                "a single lowercase path component (letters, digits, - or _) "
                "and not a reserved name (output, scripts, .state, index, "
                "schema, log)")
        folders[fname] = dict(spec) if isinstance(spec, dict) else {}

    links: dict[str, dict[str, str]] = {}
    for lname, spec in (fm.get("links") or {}).items():
        if not isinstance(spec, dict):
            continue
        if not all(spec.get(k) for k in ("from", "field", "to")):
            raise ValueError(
                f"{manifest}: link '{lname}' needs from/field/to "
                f"(got {spec!r})")
        links[str(lname)] = {k: str(v) for k, v in spec.items()}

    # `bases:` is optional — a model with none simply omits the key. But a
    # DECLARED-and-empty `bases:` is always a mistake: the front-matter dialect
    # silently drops block-list lines, so the habitual `- promotion-health`
    # form parses to {} and would emit nothing at all. Fail loudly instead.
    bases_raw = fm.get("bases")
    if bases_raw is not None and (not isinstance(bases_raw, dict)
                                  or not bases_raw):
        raise ValueError(
            f"{manifest}: `bases:` must be a mapping of name → knobs and "
            "non-empty (this front-matter dialect has no block lists — write "
            "`name: { title: ... }` one per line, or omit `bases:` entirely)")
    bases: dict[str, dict[str, Any]] = {}
    for bname, spec in (bases_raw or {}).items():
        bname = str(bname)
        if not valid_base_name(bname):
            raise ValueError(
                f"{manifest}: invalid base name {bname!r} — a base name must "
                "be a single lowercase path component (letters, digits, "
                "- or _)")
        bases[bname] = dict(spec) if isinstance(spec, dict) else {}

    generators = [g.strip() for g in str(fm.get("generators") or "").split(",")
                  if g.strip()]

    return KnowledgeModel(
        id=manifest.parent.name,
        name=str(fm.get("name", manifest.parent.name)),
        description=str(fm.get("description", "")),
        folders=folders,
        links=links,
        bases=bases,
        generators=generators,
        search_hint=str(fm.get("search_hint", "")),
        source_path=manifest,
    )


def _model_dirs(parent: Path) -> list[Path]:
    if not parent.exists():
        return []
    return sorted(d for d in parent.iterdir()
                  if d.is_dir() and d.name != "custom"
                  and (d / "model.md").exists())


def list_models(root: Path | None = None) -> list[KnowledgeModel]:
    """The merged catalogue of shipped + custom models. A custom model with
    the same id as a shipped one wins and gets `overrides_shipped` set —
    exactly the design_tokens.list_designs contract."""
    models_dir = (root or PROJECT_DIR) / "models"
    out: dict[str, KnowledgeModel] = {}

    for d in _model_dirs(models_dir):
        try:
            m = load_model(d)
            m.source = "shipped"
            out[d.name] = m
        except Exception as exc:
            print(f"warning: failed to load model {d.name}: {exc}")

    for d in _model_dirs(models_dir / "custom"):
        try:
            m = load_model(d)
            m.source = "custom"
            m.overrides_shipped = d.name in out
            out[d.name] = m
        except Exception as exc:
            print(f"warning: failed to load custom model {d.name}: {exc}")

    shipped_order = [d.name for d in _model_dirs(models_dir)]
    custom_only = [k for k in sorted(out) if k not in shipped_order]
    return [out[k] for k in shipped_order if k in out] + \
           [out[k] for k in custom_only]


def resolve_model_dir(model_id: str, root: Path | None = None) -> Path | None:
    """Map an id to its on-disk model directory (custom wins over shipped).
    None for an invalid/unknown id."""
    if not valid_model_id(model_id):
        return None
    models_dir = (root or PROJECT_DIR) / "models"
    for candidate in (models_dir / "custom" / model_id, models_dir / model_id):
        if (candidate / "model.md").exists():
            return candidate
    return None


def load_model_for_vault(vault) -> KnowledgeModel:
    """The model a vault declares (index.md frontmatter `model:`), falling
    back to the default karpathy-wiki model when undeclared. An unknown
    declared model raises — better a loud error than ingesting with the
    wrong schema."""
    model_id = getattr(vault, "model_id", lambda: DEFAULT_MODEL_ID)() \
        or DEFAULT_MODEL_ID
    d = resolve_model_dir(model_id)
    if d is None:
        raise FileNotFoundError(
            f"vault '{getattr(vault, 'slug', '?')}' declares model "
            f"'{model_id}' but models/{model_id}/model.md does not exist")
    m = load_model(d)
    m.source = "custom" if d.parent.name == "custom" else "shipped"
    return m


def save_model(path: Path, m: KnowledgeModel, body: str | None = None) -> None:
    """Write a model manifest to disk (models/custom/<id>/model.md for user
    models). Companion files (SCHEMA.md, prompts) are copied by callers."""
    from design_tokens import _emit_mapping  # local import — serializer only

    fm: dict[str, Any] = {"version": "alpha", "name": m.name or m.id}
    if m.description:
        fm["description"] = m.description
    fm["folders"] = {k: dict(v) for k, v in m.folders.items()}
    if m.links:
        fm["links"] = {k: dict(v) for k, v in m.links.items()}
    if m.bases:
        fm["bases"] = {k: dict(v) for k, v in m.bases.items()}
    if m.generators:
        fm["generators"] = ", ".join(m.generators)
    if m.search_hint:
        fm["search_hint"] = m.search_hint

    lines: list[str] = ["---"]
    _emit_mapping(lines, fm, 0)
    lines.append("---")
    if body is None:
        body = f"\n# {m.name or m.id}\n\n{m.description or ''}\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n" + body, encoding="utf-8")


if __name__ == "__main__":
    # Smoke test — CI runs this; nonzero exit if any shipped model fails to
    # parse or the default model is missing.
    models = list_models()
    if not any(m.id == DEFAULT_MODEL_ID for m in models):
        print(f"ERROR: default model '{DEFAULT_MODEL_ID}' not found/parseable")
        sys.exit(1)
    for m in models:
        print(f"=== {m.name} ({m.id}, {m.source}) ===")
        print(f"  folders: {', '.join(f'{f}[{m.kind(f)}]' for f in m.folders)}")
        print(f"  browsable: {', '.join(m.browsable_folders())}"
              f" (cards: { {f: m.card_spec(f) for f in m.folders if m.card_spec(f) is not None} })")
        print(f"  links: {', '.join(m.links)}")
        print(f"  promotion knobs: {m.prompt_format_args()}")
        print(f"  generators: {', '.join(m.generators) or '(none)'}")
        print(f"  bases: {', '.join(m.bases) or '(none)'}")
        for required in ("SCHEMA.md", "ingest-prompt.md", "promote-prompt.md"):
            if not (m.dir / required).exists():
                print(f"ERROR: {m.id} is missing {required}")
                sys.exit(1)
        # Every declared base must have a template that renders cleanly and
        # looks structurally like a Base. CI is stdlib-only (no PyYAML), so
        # this is a rendering + structure check, not a YAML parse — semantic
        # correctness is established by opening the shipped views in Obsidian.
        import base_gen
        for bname in m.bases:
            try:
                text = base_gen.render_base(m, bname)
                base_gen.check_rendered(text)
            except Exception as exc:
                print(f"ERROR: {m.id} base '{bname}': {exc}")
                sys.exit(1)
            print(f"    {bname}.base OK ({len(text.splitlines())} lines)")
    print(f"{len(models)} model(s) OK")
