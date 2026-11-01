"""Local web UI for the youtuber → markdown converter.

Run:  py -3.13 server.py    (or .\\.venv\\Scripts\\python.exe server.py)
Then open http://127.0.0.1:8765 in a browser.

Routes:
  GET  /                  → index.html
  POST /convert           → JSON {url} OR multipart {file}; runs convert.py
  GET  /files             → JSON list of files in output/
  GET  /files/<filename>  → serve a markdown file from output/
"""

from __future__ import annotations

import ctypes
import json
import mimetypes
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import webbrowser
from datetime import datetime, timezone
from email.parser import BytesParser
from email.policy import default as default_policy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote, unquote


def disable_windows_quick_edit() -> None:
    """Disable Quick Edit / Insert mode on the console.

    On Windows, clicking inside the console window puts it into Mark mode,
    which pauses the process until the user presses Enter. That makes the
    server appear hung. Turning these flags off prevents the freeze.
    """
    if sys.platform != "win32":
        return
    try:
        kernel32 = ctypes.windll.kernel32
        STD_INPUT_HANDLE = -10
        ENABLE_QUICK_EDIT_MODE = 0x0040
        ENABLE_INSERT_MODE = 0x0020
        ENABLE_EXTENDED_FLAGS = 0x0080
        INVALID_HANDLE = ctypes.c_void_p(-1).value

        handle = kernel32.GetStdHandle(STD_INPUT_HANDLE)
        if handle == INVALID_HANDLE or handle == 0:
            return
        mode = ctypes.c_uint(0)
        if not kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            return
        new_mode = (mode.value | ENABLE_EXTENDED_FLAGS) & ~ENABLE_QUICK_EDIT_MODE & ~ENABLE_INSERT_MODE
        kernel32.SetConsoleMode(handle, new_mode)
    except Exception:
        pass  # Best effort — never let this kill the server.

PROJECT_DIR = Path(__file__).resolve().parent
INDEX = PROJECT_DIR / "index.html"
LANDING_DIR = PROJECT_DIR / "landing"
LANDING_INDEX = LANDING_DIR / "index.html"
LANDING_STUDIO = LANDING_DIR / "studio.html"
CONVERT = PROJECT_DIR / "convert.py"
OUTPUT_DIR = PROJECT_DIR / "output"
WIKI_DIR = PROJECT_DIR / "wiki"
INGEST_SCRIPT = WIKI_DIR / "scripts" / "ingest.py"
PENDING_SCRIPT = WIKI_DIR / "scripts" / "pending.py"
STUDIO_MARP_SCRIPT = WIKI_DIR / "scripts" / "studio_marp.py"
STUDIO_DIAGRAM_SCRIPT = WIKI_DIR / "scripts" / "studio_diagram.py"
STUDIO_GUIDE_SCRIPT = WIKI_DIR / "scripts" / "studio_guide.py"
STUDIO_PPTX_SCRIPT = WIKI_DIR / "scripts" / "studio_pptx.py"
STUDIO_SKILLS_SCRIPT = WIKI_DIR / "scripts" / "studio_skills.py"
STUDIO_ANKI_SCRIPT = WIKI_DIR / "scripts" / "studio_anki.py"
PROMOTE_SCRIPT = WIKI_DIR / "scripts" / "promote_backlog.py"
REVIEW_STATE_FILE = WIKI_DIR / ".state" / "review.json"
AUTO_REVIEW_THRESHOLD = int(os.environ.get("AUTO_REVIEW_THRESHOLD", "5"))
# Windows venvs put the interpreter under Scripts/, POSIX under bin/
VENV_PYTHON = PROJECT_DIR / ".venv" / "Scripts" / "python.exe" \
    if sys.platform == "win32" else PROJECT_DIR / ".venv" / "bin" / "python"
LOG_FILE = PROJECT_DIR / "server.log"
ENV_FILE = PROJECT_DIR / ".env"

HOST = "127.0.0.1"
PORT = int(os.environ.get("RIVERFED_PORT", "8765"))
CONVERT_TIMEOUT = 600  # seconds
INGEST_TIMEOUT = 1800  # seconds PER TRANSCRIPT — the ingest job cap scales
                       # with the pending count (see submit_ingest_job)
STUDIO_TIMEOUT = 900   # seconds — Claude Code single-shot generation

# When this server runs as pythonw.exe (no console), every subprocess.run /
# Popen Windows spawns gets its own new console window unless we explicitly
# suppress it. CREATE_NO_WINDOW is Windows-only; the constant only exists on
# the win32 build of Python, so guard the lookup.
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform == "win32" else 0

# ---- async job queue --------------------------------------------------------
# Long operations (convert / ingest / review / studio) run as background jobs:
# POST returns {job_id} immediately and the UI polls GET /jobs/<id> for state +
# a live log tail. Lanes serialize what must not run concurrently — the "wiki"
# lane (ingest + review) replaces the old single-flight lock: a second click
# QUEUES behind the first instead of being rejected. run_streaming() gives
# every job line-streamed progress and a hard timeout that kills the whole
# process TREE (a plain subprocess timeout only kills the .CMD shim on
# Windows, orphaning node/chromium — the 125-minute marp zombie).
sys.path.insert(0, str(WIKI_DIR / "scripts"))
from _proc import run_streaming  # noqa: E402
import _wikis  # noqa: E402  (vault resolution + scaffolding — multi-knowledge-base)
import _frontmatter  # noqa: E402  (shared page-frontmatter parser — block + inline lists)
import model_registry as _models  # noqa: E402  (knowledge-model manifests)
import md_view  # noqa: E402  (raw markdown -> on-brand HTML page renderer)
import pending as _pending  # noqa: E402  (video-id matching for duplicate alerts)
import watcher as _watcher  # noqa: E402  (channel subscriptions — stdlib at import;
#                                          yt-dlp work runs via the venv python)
import writer_pack as _writer_pack  # noqa: E402  (read-only Writer snapshot bridge)

import jobs as _jobs  # noqa: E402  (sibling module: jobs.py)
import agent_runner as _agent  # noqa: E402  (agent provider layer — A6 step 1)

JOBS = _jobs.JobManager()
JOB_LANES = {"convert": "convert", "ingest": "wiki", "review": "wiki",
             "studio": "studio"}


# Provider status probes are cached this long (agent_runner.status ttl).
# /pending polls every 10 s and each provider costs two subprocess
# probes (version + auth) — six per poll at three providers, uncached.
AGENT_STATUS_TTL = 20.0


def agent_auth_summary() -> tuple[str | None, dict]:
    """(auto_resolved_provider_or_None, payload for the UI).

    The payload is {"auto": <provider id or null>,
    "providers": {id: agent_runner.status(id), ...}} — the UI selector and
    banners render from it.
    """
    provider, _ = _agent.resolve_provider("auto", ttl=AGENT_STATUS_TTL)
    statuses = {p: _agent.status(p, ttl=AGENT_STATUS_TTL)
                for p in _agent.PROVIDERS}
    return provider, {"auto": provider, "providers": statuses}


def load_env_file() -> None:
    """Read .env if present and merge missing keys into os.environ.

    Lines look like KEY=value or KEY="value". Existing environment values
    win — the .env file is a fallback, not an override. Subprocesses spawned
    later (convert.py, ingest.py) inherit the merged env.
    """
    if not ENV_FILE.exists():
        return
    try:
        text = ENV_FILE.read_text(encoding="utf-8")
    except OSError as exc:
        sys.stderr.write(f"warning: could not read .env ({exc})\n")
        return
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export "):].lstrip()
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
            value = value[1:-1]
        if key and key not in os.environ:
            os.environ[key] = value


class _Tee:
    """Write to multiple streams (e.g., stderr + a log file) at once."""
    def __init__(self, *streams):
        self.streams = streams
    def write(self, data):
        for s in self.streams:
            try:
                s.write(data)
                s.flush()
            except Exception:
                pass
    def flush(self):
        for s in self.streams:
            try:
                s.flush()
            except Exception:
                pass


def install_file_logging() -> None:
    """Mirror stdout/stderr to server.log so crashes are recoverable."""
    try:
        log_fp = open(LOG_FILE, "a", encoding="utf-8", buffering=1)
        log_fp.write(f"\n--- server start {datetime.now().isoformat(timespec='seconds')} ---\n")
        sys.stdout = _Tee(sys.stdout, log_fp)
        sys.stderr = _Tee(sys.stderr, log_fp)
    except Exception as exc:
        sys.stderr.write(f"warning: could not open {LOG_FILE} for logging: {exc}\n")


def python_executable() -> str:
    """Prefer the project venv if present, else fall back to the running interpreter."""
    if VENV_PYTHON.exists():
        return str(VENV_PYTHON)
    return sys.executable


def parse_multipart_file(content_type: str, body: bytes) -> tuple[str, bytes] | None:
    """Extract a single uploaded file (field name 'file') from a multipart body."""
    header = f"Content-Type: {content_type}\r\n\r\n".encode()
    msg = BytesParser(policy=default_policy).parsebytes(header + body)
    for part in msg.iter_parts():
        cd = part.get("Content-Disposition", "")
        if "form-data" not in cd:
            continue
        name = part.get_param("name", header="Content-Disposition")
        filename = part.get_filename()
        if name == "file" and filename:
            payload = part.get_payload(decode=True) or b""
            return filename, payload
    return None


def list_output_files(out_dir: Path | None = None) -> list[dict]:
    OUTPUT_DIR = out_dir if out_dir is not None else PROJECT_DIR / "output"  # noqa: N806
    if not OUTPUT_DIR.exists():
        return []
    out = []
    for p in sorted(OUTPUT_DIR.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
        if not p.is_file() or p.name.startswith("."):
            continue
        st = p.stat()
        out.append({
            "name": p.name,
            "size": st.st_size,
            "modified": datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M"),
        })
    return out


def _parse_frontmatter(text: str) -> dict:
    """Parse a wiki page's frontmatter. Delegates to the shared page-frontmatter
    parser so block-list sequences (`sources:\\n  - a\\n  - b`) parse the same
    everywhere — server, obsidian_pass, linters."""
    return _frontmatter.parse_frontmatter(text)


def _strip_section(text: str, heading: str) -> str:
    """Return the first paragraph under `## heading`, or empty string."""
    import re
    m = re.search(rf"^##\s+{re.escape(heading)}\s*$(.*?)(?=^##\s|\Z)",
                  text, re.MULTILINE | re.DOTALL)
    if not m:
        return ""
    body = m.group(1).strip()
    # First paragraph (everything before a blank line)
    para = body.split("\n\n", 1)[0].strip()
    # Strip trailing parenthesised citation tag like "(some-slug)"
    return re.sub(r"\s*\([a-z0-9-]+(?:\s*\|\s*[a-z0-9-]+)*\)\s*$", "", para)


def _first_h1(text: str) -> str:
    import re
    m = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
    return m.group(1).strip() if m else ""


def _lead_paragraph(text: str) -> str:
    """First prose paragraph after the H1, before any `##` section — the
    generic card body for folders whose card spec names no sections."""
    import re
    body = re.sub(r"^---\s*\n.*?\n---\s*\n", "", text, flags=re.DOTALL)
    m = re.search(r"^#\s+.+\n+(.*?)(?=^#{1,6}\s|\Z)",
                  body, re.MULTILINE | re.DOTALL)
    if not m:
        return ""
    return m.group(1).strip().split("\n\n", 1)[0].strip()


def _slugs_in_dir(dir_path) -> list[str]:
    return [p.stem for p in sorted(dir_path.glob("*.md"))] if dir_path.exists() else []


def _read_md(path) -> tuple[dict, str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    return _parse_frontmatter(text), text


def _resolve_wiki_dir(slug: str | None = None) -> Path | None:
    """Map a wiki slug (from /wikis) to its directory, or return the
    default wiki/ if no slug is given. Returns None if not found."""
    vault = _wikis.resolve_vault(slug)
    if vault is None or not vault.exists():
        return None
    return vault.root


def _resolve_vault_checked(slug: str | None):
    """Resolve a slug to an existing Vault, or None."""
    vault = _wikis.resolve_vault(slug)
    if vault is None or not vault.exists():
        return None
    return vault


def _model_for(vault) -> "_models.KnowledgeModel":
    """The vault's knowledge model. Falls back to the default karpathy-wiki
    manifest on any error — a broken/missing manifest must degrade the UI,
    never take the server down."""
    try:
        return _models.load_model_for_vault(vault)
    except Exception as exc:
        sys.stderr.write(f"warning: model for vault '{vault.slug}' failed "
                         f"({exc}); using default\n")
        return _models.load_model(_models.MODELS_DIR / _models.DEFAULT_MODEL_ID)


def build_wiki_data(wiki_slug: str | None = None) -> dict:
    """Parse a wiki tree into a JSON-friendly structure for the /wiki
    browsing UI. Folder names + node kinds come from the vault's knowledge
    model manifest; the per-kind field extraction below is what the UI
    expects. Cheap enough to compute per-request (few dozen small
    markdown files)."""
    vault = _resolve_vault_checked(wiki_slug)
    if vault is None:
        return {"available": False}
    WIKI = vault.root  # noqa: N806
    model = _model_for(vault)

    def _folder_pages(kind: str):
        """(path, frontmatter, text) for every page of the given kind,
        across all folders the model maps to that kind."""
        for folder in model.folders_for_kind(kind):
            for p in sorted((WIKI / folder).glob("*.md")):
                fm, text = _read_md(p)
                yield p, fm, text

    # Source pages first — the substrate every browsable section cites.
    sources_by_slug = {}
    source_fms: list[tuple[str, dict]] = []
    for p, fm, text in _folder_pages("source"):
        slug = fm.get("slug") or p.stem
        source_fms.append((slug, fm))
        sources_by_slug[slug] = {
            "slug": slug,
            "title": fm.get("title") or _first_h1(text) or slug,
            "channel": fm.get("channel") or "",
            "url": fm.get("url") or "",
            "tldr": _strip_section(text, "TL;DR"),
        }

    # Reverse source links per kind: a member page with no `sources:` list
    # of its own (karpathy entities, e.g.) still gets provenance via the
    # source pages' link fields (manifest specs with `from: source`).
    rev_fields_by_kind: dict[str, list[str]] = {}
    for spec in model.links.values():
        if spec.get("from") == "source":
            rev_fields_by_kind.setdefault(spec["to"], []).append(spec["field"])
    rev_sources: dict[str, dict[str, list[str]]] = {}
    for src_slug, fm in source_fms:
        for kind, fields in rev_fields_by_kind.items():
            for fld in fields:
                for target in _frontmatter.as_list(fm.get(fld)):
                    rev_sources.setdefault(kind, {}) \
                        .setdefault(target, []).append(src_slug)

    # Browsable card sections, in manifest order. The folder's card spec
    # names the `## section`s each card surfaces (description + optional
    # callout); a folder with an empty card spec falls back to the page's
    # lead paragraph. Folders without a card spec (karpathy entities) stay
    # graph-only.
    sections = []
    for folder in model.browsable_folders():
        kind = model.kind(folder)
        card = model.card_spec(folder) or {}
        desc_heading = card.get("description") or ""
        callout_heading = card.get("callout") or ""
        label_field = model.label_field(folder)
        items = []
        for p in sorted((WIKI / folder).glob("*.md")):
            fm, text = _read_md(p)
            slug = fm.get("slug") or p.stem
            name = ((fm.get(label_field) if label_field else None)
                    or _first_h1(text) or p.stem)
            srcs = _frontmatter.as_list(fm.get("sources"))
            if not srcs:
                srcs = rev_sources.get(kind, {}).get(slug, [])
            items.append({
                "slug": slug,
                "name": name,
                "description": (_strip_section(text, desc_heading)
                                if desc_heading else _lead_paragraph(text)),
                "callout": (_strip_section(text, callout_heading)
                            if callout_heading else ""),
                "sources": srcs,
                "source_count": len(srcs),
                "last_updated": fm.get("last_updated") or "",
            })
        items.sort(key=lambda it: -it["source_count"])
        sections.append({"folder": folder, "kind": kind, "items": items})

    # Presentations: anything in wiki/training/out/ named <handbook-base>.<ext>
    presentations = []
    training_out = WIKI / "training" / "out"
    training_root = WIKI / "training"
    grouped: dict[str, list[dict]] = {}
    for dir_ in (training_root, training_out):
        if not dir_.exists():
            continue
        for p in sorted(dir_.glob("*.*")):
            if p.suffix.lower() not in {".md", ".html", ".pdf", ".pptx", ".docx"}:
                continue
            if p.name.startswith("~$") or p.name.startswith("_"):
                continue
            # Group by display name (strip -speaker-notes / common pattern)
            stem = p.stem
            if stem.endswith("-speaker-notes"):
                display = stem[:-len("-speaker-notes")].replace("-", " ").title() + " Speaker Notes"
            else:
                display = stem.replace("-", " ").title()
            grouped.setdefault(display, []).append({
                "format": p.suffix.lstrip(".").upper(),
                "path": p.relative_to(PROJECT_DIR).as_posix(),
            })
    for name, files in sorted(grouped.items()):
        # Deduplicate by format (prefer wiki/training/out/ versions)
        by_fmt: dict[str, dict] = {}
        for f in files:
            existing = by_fmt.get(f["format"])
            if existing is None or "/out/" in f["path"]:
                by_fmt[f["format"]] = f
        order = ["HTML", "PDF", "PPTX", "DOCX", "MD"]
        sorted_files = sorted(by_fmt.values(),
                              key=lambda f: order.index(f["format"]) if f["format"] in order else 99)
        presentations.append({"name": name, "files": sorted_files})

    counts = {}
    for folder in model.folders:
        d = WIKI / folder
        counts[folder] = len(list(d.glob("*.md"))) if d.exists() else 0

    return {
        "available": True,
        "model": model.id,
        "counts": counts,
        "search_hint": model.search_hint
        or ", ".join(model.browsable_folders()),
        "sections": sections,
        "sources_by_slug": sources_by_slug,
        "presentations": presentations,
    }


def build_wiki_graph(wiki_slug: str | None = None) -> dict:
    """Build a node/link graph for the Obsidian-style force-directed view.

    Everything structural comes from the vault's knowledge model manifest:
    nodes = every page in every model folder (kind, label field, and the
    weight rule per folder); links = the manifest's `links` specs, read
    from page frontmatter (karpathy-wiki: source→topic `topics:`,
    source→entity `entities:`, concept→source `sources:`, concept→topic
    `related_topics:`)."""
    vault = _resolve_vault_checked(wiki_slug)
    if vault is None:
        return {"available": False}
    wiki_dir = vault.root
    model = _model_for(vault)

    nodes: list[dict] = []
    seen_ids: set[str] = set()
    links: list[dict] = []

    def add_node(kind: str, slug: str, label: str,
                 weight: int = 1, folder: str = "") -> str:
        node_id = f"{kind}:{slug}"
        if node_id in seen_ids:
            return node_id
        seen_ids.add(node_id)
        nodes.append({
            "id": node_id,
            "kind": kind,        # folder kind from the model manifest
            "slug": slug,
            "label": label,
            "val": weight,       # size proxy
            "folder": folder,    # so the UI can link to the page file
        })
        return node_id

    def add_link(a: str, b: str, kind: str) -> None:
        if a in seen_ids and b in seen_ids and a != b:
            links.append({"source": a, "target": b, "kind": kind})

    # First pass — create all nodes so links never reference unknown IDs
    for folder in model.folders:
        kind = model.kind(folder)
        label_field = model.label_field(folder)
        wspec = model.weight_spec(folder)
        for p in (wiki_dir / folder).glob("*.md"):
            fm, text = _read_md(p)
            slug = fm.get("slug") or p.stem
            label = ((fm.get(label_field) if label_field else None)
                     or _first_h1(text) or p.stem)
            weight = 1
            if wspec:
                weight = max(wspec["min"],
                             len(_frontmatter.as_list(fm.get("sources")))
                             + wspec["bonus"])
            add_node(kind, slug, label, weight=weight, folder=folder)

    # Second pass — links from frontmatter relationships, per the manifest's
    # link specs, grouped by origin kind (each origin page emits its links in
    # spec order).
    specs_by_from: dict[str, list[tuple[str, dict]]] = {}
    for edge_kind, spec in model.links.items():
        specs_by_from.setdefault(spec["from"], []).append((edge_kind, spec))

    for from_kind, specs in specs_by_from.items():
        for folder in model.folders_for_kind(from_kind):
            for p in (wiki_dir / folder).glob("*.md"):
                fm, _ = _read_md(p)
                page_id = f"{from_kind}:{fm.get('slug') or p.stem}"
                for edge_kind, spec in specs:
                    for target in _frontmatter.as_list(fm.get(spec["field"])):
                        add_link(page_id, f"{spec['to']}:{target}", edge_kind)

    # Ordered kind catalogue (manifest folder order) — the UI assigns
    # legend entries + node colors from this, not from a hardcoded list.
    kinds_meta: list[dict] = []
    for folder in model.folders:
        k = model.kind(folder)
        if all(km["kind"] != k for km in kinds_meta):
            kinds_meta.append({"kind": k, "folder": folder})

    return {
        "available": True,
        "model": model.id,
        "kinds": kinds_meta,
        "nodes": nodes,
        "links": links,
        "counts": {
            "nodes": len(nodes),
            "links": len(links),
        },
    }


def _page_title(target: Path) -> str:
    """Human title for a markdown page: frontmatter name/title, else the
    first '# ' heading, else a prettified filename stem."""
    try:
        text = target.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return target.stem.replace("-", " ").title()
    fm, _raw, body = _frontmatter.split_frontmatter(text)
    for key in ("name", "title"):
        val = fm.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    for line in body.splitlines():
        m = re.match(r"^#\s+(.+)$", line.strip())
        if m:
            return m.group(1).strip()
    return target.stem.replace("-", " ").title()


def _review_state_file(vault) -> Path:
    return vault.state_dir / "review.json"


def read_review_state(wiki_slug: str | None = None) -> dict:
    """Return the current review counter for the UI ("X / threshold").
    Per-vault — each knowledge base has its own <vault>/.state/review.json."""
    state = {"ingests_since_review": 0, "last_review_at": None}
    vault = _resolve_vault_checked(wiki_slug)
    if vault is not None:
        state_file = _review_state_file(vault)
        if state_file.exists():
            try:
                state.update(json.loads(state_file.read_text(encoding="utf-8")))
            except Exception:
                pass
    state["threshold"] = AUTO_REVIEW_THRESHOLD
    state["auto_enabled"] = AUTO_REVIEW_THRESHOLD > 0
    return state


def list_wikis() -> list[dict]:
    """Every knowledge base on disk: the original `wiki/` plus each
    user-created vault under `wikis/<slug>/` (a folder counts once it has
    index.md + SCHEMA.md — see wiki/scripts/_wikis.py). Page counts follow
    each vault's knowledge-model folders."""
    out: list[dict] = []
    for v in _wikis.discover_vaults():
        model = _model_for(v)
        counts = {}
        for folder in model.folders:
            d = v.root / folder
            counts[folder] = len(list(d.glob("*.md"))) if d.exists() else 0
        out.append({
            "slug": v.slug,
            "name": v.display_name(),
            # Repo-relative for repo vaults, absolute for vault-home ones —
            # studio scripts resolve either via _wikis.resolve_vault_dir.
            "path": _wikis.display_path(v.root),
            "model": model.id,
            "counts": counts,
        })
    return out


def _pending_payload(vault) -> dict:
    """Structured source-readiness snapshot from the canonical scanner."""
    proc = subprocess.run(
        [
            python_executable(),
            str(PENDING_SCRIPT),
            "--wiki",
            vault.slug,
            "--json",
        ],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
        cwd=str(PROJECT_DIR),
        creationflags=NO_WINDOW,
    )
    try:
        payload = json.loads((proc.stdout or "").strip() or "{}")
    except json.JSONDecodeError as exc:
        raise RuntimeError("pending source scan returned invalid JSON") from exc
    if proc.returncode != 0 or payload.get("error"):
        message = (
            payload.get("error")
            or (proc.stderr or "").strip()
            or f"pending source scan exited {proc.returncode}"
        )
        raise RuntimeError(message)
    if not isinstance(payload.get("pending"), list):
        raise RuntimeError("pending source scan omitted its source list")
    return payload


def duplicate_details(existing_path: str, vault, frames_wanted: bool) -> dict:
    """Context for the UI's duplicate alert when convert.py skips an
    already-converted source: has the video already been ingested into the
    vault (and as which page), does the existing transcript carry frames,
    and was a frames/dense request silently dropped by the skip. Best-effort
    — any read failure just leaves the flags at their defaults."""
    details = {
        "already_ingested": False,
        "source_page": "",
        "existing_has_frames": False,
        "frames_requested_ignored": False,
    }
    try:
        text = Path(existing_path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return details
    details["existing_has_frames"] = "\n## Visual content" in text
    details["frames_requested_ignored"] = (
        frames_wanted and not details["existing_has_frames"])
    if vault is None:
        return details
    try:
        capture_dir = vault.root / _models.load_model_for_vault(vault).capture_folder()
    except Exception:
        capture_dir = vault.sources
    if not capture_dir.exists():
        return details
    # Match by video id first (survives re-slugging + alt_url merges),
    # then fall back to the slug/source_file match pending.py uses.
    vid = _pending.video_id("\n".join(text.splitlines()[:30]))
    if vid:
        for p in sorted(capture_dir.glob("*.md")):
            try:
                head = p.read_text(encoding="utf-8",
                                   errors="replace").splitlines()[:30]
            except OSError:
                continue
            if any(re.match(r"^(alt_)?url:", ln) and _pending.video_id(ln) == vid
                   for ln in head):
                details["already_ingested"] = True
                details["source_page"] = p.stem
                return details
    stem = Path(existing_path).stem
    if stem in _pending.existing_source_slugs(capture_dir):
        details["already_ingested"] = True
        details["source_page"] = stem
    return details


def submit_ingest_job(vault, provider: str = "auto") -> dict:
    """Queue an ingest run for a vault on the 'wiki' lane. Module-level so
    both the POST /ingest handler and the watcher's auto-ingest chain can
    submit it (the chain runs inside a job thread, where no Handler
    instance exists). `provider` is the RESOLVED agent id from the
    pre-submit gate (or "auto" to let the script resolve)."""
    if not INGEST_SCRIPT.exists():
        return {"success": False, "error": "ingest.py not found"}
    try:
        readiness = _pending_payload(vault)
    except Exception as exc:
        return {"success": False, "error": f"Could not inspect sources: {exc}"}
    ready_count = int(readiness.get("ready_count", 0))
    blocked_count = int(readiness.get("blocked_count", 0))
    if ready_count <= 0:
        if blocked_count:
            noun = "source" if blocked_count == 1 else "sources"
            return {
                "success": False,
                "error": (
                    f"{blocked_count} {noun} need transcript recovery before "
                    "ingest. Review the source readiness details under "
                    "Knowledge and retry recovery there."
                ),
                "code": "sources_need_recovery",
            }
        return {
            "success": False,
            "error": "No ready sources to ingest.",
            "code": "no_ready_sources",
        }
    cmd = [python_executable(), "-u", str(INGEST_SCRIPT), "--wiki", vault.slug,
           "--provider", provider]
    # INGEST_TIMEOUT is a per-transcript budget (ingest.py enforces the same
    # bound per agent run). The whole-job cap must scale with the backlog,
    # or a well-behaved multi-video ingest gets killed mid-queue — a single
    # 30-min cap killed a real 1-video Codex run on 2026-07-05 during its
    # final self-review. +10 min slack covers finalize + agent startup.
    timeout_s = INGEST_TIMEOUT * ready_count + 600

    def run(job):
        rc, out, err, timed_out = run_streaming(
            cmd, cwd=str(PROJECT_DIR), timeout=timeout_s,
            on_line=job.emit, creationflags=NO_WINDOW)
        if timed_out:
            return {"success": False,
                    "error": f"Ingest timed out after {timeout_s}s"}
        stdout = "\n".join(out).strip()
        stderr = "\n".join(err).strip()
        if rc == 0:
            return {"success": True, "stdout": stdout, "stderr": stderr}
        return {"success": False,
                "error": stderr or stdout or f"Exit code {rc}",
                "stdout": stdout}

    label = ("Ingest pending transcripts" if vault.slug == "wiki"
             else f"Ingest pending transcripts ({vault.display_name()})")
    job_id = JOBS.submit("ingest", JOB_LANES["ingest"], run, label=label)
    return {"success": True, "job_id": job_id, "state": "queued"}


def submit_watcher_sweep(vault) -> dict:
    """Queue a watcher sweep for a vault on the 'convert' lane: discovery +
    conversion of new uploads runs under the venv python (watcher.py --run);
    if any converted subscription is marked auto-ingest, the standard ingest
    job is chained onto the 'wiki' lane afterwards."""
    cmd = [python_executable(), "-u", str(PROJECT_DIR / "watcher.py"),
           "--wiki", vault.slug, "--run"]

    def run(job):
        rc, out, err, timed_out = run_streaming(
            cmd, cwd=str(PROJECT_DIR), timeout=2700,
            on_line=job.emit, creationflags=NO_WINDOW)
        if timed_out:
            return {"success": False, "error": "Watcher sweep timed out after 45 min"}
        converted = []
        for line in out:
            line = line.strip()
            if line.startswith("CONVERTED:"):
                _, vid, title = line.split(":", 2)
                converted.append({"id": vid, "title": title})
        if rc != 0:
            tail = "\n".join(err).strip() or "\n".join(out).strip()
            return {"success": False, "error": tail[-500:] or f"Exit {rc}",
                    "converted": converted}
        result = {"success": True, "wiki": vault.slug, "converted": converted}
        if any(l.strip() == "AUTO_INGEST_REQUESTED" for l in out):
            job.emit("[watcher] auto-ingest subscription converted — queueing ingest…")
            provider, pstatus = _agent.resolve_provider("auto",
                                                        ttl=AGENT_STATUS_TTL)
            if provider is not None:
                result["ingest"] = submit_ingest_job(vault, provider)
            else:
                result["ingest"] = {
                    "success": False,
                    "error": (_agent.unavailable_message(pstatus)
                              + " — videos staged as pending instead"),
                }
        return result

    job_id = JOBS.submit("convert", JOB_LANES["convert"], run,
                         label=f"Watcher sweep ({vault.display_name()})")
    return {"success": True, "job_id": job_id, "state": "queued"}


def _watcher_interval_min() -> int:
    """Sweep cadence in minutes (env, read live). 0 disables the cadence."""
    try:
        return int(os.environ.get("WATCHER_INTERVAL_MIN", "360") or "0")
    except ValueError:
        return 360


# In-flight debounce: don't resubmit a sweep for a vault within this window of
# the last attempt, so a sweep that's still running (and hasn't updated
# last_sweep yet) isn't duplicated by the next tick. Matches the sweep job cap.
_SWEEP_INFLIGHT_GRACE = 45 * 60
_last_sweep_attempt: dict[str, float] = {}


def _iso_age_sec(iso_str, now_ts: float) -> float:
    """Age in seconds of an ISO-8601 timestamp; +inf if missing/unparseable."""
    if not iso_str:
        return float("inf")
    try:
        dt = datetime.fromisoformat(iso_str)
    except (ValueError, TypeError):
        return float("inf")
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return now_ts - dt.timestamp()


def sweep_due_vaults(force: bool = False) -> list[str]:
    """Submit a watcher sweep for every subscribed vault whose last sweep is
    older than the interval. Interval-guarded and in-flight-debounced, so it's
    SAFE to call frequently — this is what makes the automation self-healing:
    both the in-process cadence thread AND the external /healthz watchdog drive
    it, so a stalled thread can't leave auto-ingest dark (the 2026-08-05
    incident). Returns the slugs actually swept."""
    interval_min = _watcher_interval_min()
    if interval_min <= 0 and not force:
        return []
    interval_sec = max(interval_min, 1) * 60
    now = time.time()
    swept: list[str] = []
    for v in _wikis.discover_vaults():
        try:
            data = _watcher.load_subs(v)
        except Exception:
            continue
        if not data.get("subscriptions"):
            continue
        attempt = _last_sweep_attempt.get(v.slug, 0.0)
        if not force and (now - attempt) < _SWEEP_INFLIGHT_GRACE:
            continue  # a sweep we launched is still likely in flight
        last = data.get("last_sweep")
        if not force and _iso_age_sec(last, now) < interval_sec:
            continue  # swept recently enough
        # Don't pile onto an active convert-lane job (a running sweep or a
        # user's convert) — the next tick will retry.
        if JOBS.lane_active(JOB_LANES["convert"]) is not None:
            continue
        _last_sweep_attempt[v.slug] = now
        submit_watcher_sweep(v)
        swept.append(v.slug)
        sys.stdout.write(
            f"[watcher] sweep submitted for {v.slug} "
            f"(last_sweep={last or 'never'}) at "
            f"{datetime.now(timezone.utc).isoformat(timespec='seconds')}\n")
        sys.stdout.flush()
    return swept


def watcher_health() -> dict:
    """Freshness summary for /healthz: the oldest last_sweep age across
    subscribed vaults, and whether it's stale (no sweep in >2 intervals)."""
    interval_min = _watcher_interval_min()
    if interval_min <= 0:
        return {"enabled": False}
    now = time.time()
    oldest = 0.0
    subscribed = 0
    for v in _wikis.discover_vaults():
        try:
            data = _watcher.load_subs(v)
        except Exception:
            continue
        if not data.get("subscriptions"):
            continue
        subscribed += 1
        oldest = max(oldest, _iso_age_sec(data.get("last_sweep"), now))
    if not subscribed:
        return {"enabled": True, "subscribed_vaults": 0}
    age = None if oldest == float("inf") else int(oldest)
    return {
        "enabled": True,
        "subscribed_vaults": subscribed,
        "interval_min": interval_min,
        "oldest_sweep_age_sec": age,
        "stale": oldest > interval_min * 60 * 2,
    }


def start_watcher_thread() -> None:
    """In-process sweep cadence. Polls sweep_due_vaults() frequently (not a
    single 6h sleep) so one missed wakeup can't dark the watcher for hours;
    the interval guard inside sweep_due_vaults() keeps actual sweeps at
    WATCHER_INTERVAL_MIN. The launchd watchdog also POSTs /watcher/tick every
    5 min, so even if THIS thread dies the sweeps keep happening. Reads the env
    inside main() (after load_env_file), not at import."""
    interval_min = _watcher_interval_min()
    if interval_min <= 0:
        print("Watcher: background sweeps disabled (WATCHER_INTERVAL_MIN=0)")
        return
    poll_sec = min(interval_min, 30) * 60  # wake at least every 30 min

    def loop():
        time.sleep(90)   # let the server settle after boot
        while True:
            try:
                sweep_due_vaults()
            except Exception as exc:
                sys.stderr.write(f"[watcher] sweep scheduling failed: {exc}\n")
            time.sleep(poll_sec)

    threading.Thread(target=loop, daemon=True, name="watcher-sweep").start()
    print(f"Watcher: sweeping subscribed channels every {interval_min} min "
          f"(polling every {poll_sec // 60} min, watchdog-backed)")


class Handler(BaseHTTPRequestHandler):
    server_version = "youtuber/1.0"

    # ---------- helpers ----------

    def _send_bytes(self, status: int, content_type: str, body: bytes, extra_headers: dict | None = None):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for k, v in (extra_headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, payload: dict, status: int = 200):
        self._send_bytes(status, "application/json; charset=utf-8",
                         json.dumps(payload).encode("utf-8"))

    def _writer_origin_headers(self) -> dict | None:
        """CORS for the one browser-local Writer bridge, never the full API.

        Loopback origins are always allowed; a hosted Writer origin must be
        listed in RIVERFED_WRITER_ORIGINS (comma-separated, env or .env)."""
        origin = self.headers.get("Origin", "")
        hosted = {o.strip().rstrip("/") for o in
                  os.environ.get("RIVERFED_WRITER_ORIGINS", "").split(",")
                  if o.strip()}
        allowed = origin in hosted \
            or re.fullmatch(r"http://(?:127\.0\.0\.1|localhost):\d+", origin)
        if origin and not allowed:
            return None
        headers = {"Vary": "Origin"}
        if origin:
            headers.update({
                "Access-Control-Allow-Origin": origin,
                "Access-Control-Allow-Methods": "GET, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type",
                "Access-Control-Allow-Private-Network": "true",
                "Access-Control-Max-Age": "600",
            })
        return headers

    def _send_writer_json(self, payload: dict, status: int = 200):
        headers = self._writer_origin_headers()
        if headers is None:
            self._send_json({"success": False, "error": "Origin not allowed"}, 403)
            return
        self._send_bytes(status, "application/json; charset=utf-8",
                         json.dumps(payload).encode("utf-8"), headers)

    def _send_file(self, path: Path, content_type: str | None = None):
        if not path.exists() or not path.is_file():
            self._send_json({"success": False, "error": "Not found"}, 404)
            return
        ct = content_type or mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        body = path.read_bytes()
        self._send_bytes(200, ct, body)

    def log_message(self, format, *args):
        sys.stderr.write(f"[{self.log_date_time_string()}] {self.address_string()} - {format % args}\n")

    def do_OPTIONS(self):
        path = self.path.split("?", 1)[0]
        if path not in ("/api/writer/libraries", "/api/writer/knowledge-pack"):
            self._send_json({"success": False, "error": "Not found"}, 404)
            return
        headers = self._writer_origin_headers()
        if headers is None:
            self._send_json({"success": False, "error": "Origin not allowed"}, 403)
            return
        self._send_bytes(204, "text/plain; charset=utf-8", b"", headers)

    # ---------- conversion (async job) ----------

    def _submit_convert(self, input_value: str, frames: bool = False,
                        dense: bool = False, force: bool = False, cleanup=None,
                        original_filename: str | None = None,
                        label: str = "", vault=None) -> dict:
        """Queue a convert job; returns {success, job_id} immediately."""
        cmd = [python_executable(), "-u", str(CONVERT), input_value]
        if force:
            # Re-convert even though an output for the same source exists —
            # the UI's "Re-convert anyway" action on a duplicate alert.
            cmd.append("--force")
        if vault is not None:
            # Every vault stages transcripts in its own output/ so each
            # knowledge base has an isolated "pending" queue. (The "wiki"
            # slug used to be exempt and stage in the repo-root output/ --
            # correct before the C1 vault split, a stranded-transcript bug
            # after it: pending scans vault.output, so a root-staged file
            # never showed as pending. The watcher path always passed --out.)
            cmd += ["--out", str(vault.output)]
        if dense:
            # Deep visual capture: dense sampling + hi-res + every frame
            # flagged vision-relevant. Proven on whiteboard/Excalidraw and
            # screen-recording videos (see docs/frames-ingest-comparison.md).
            # Implies --frames. Costs more ingest tokens (agent reads every
            # frame as an image) but captures diagrams/UI/code the OCR misses.
            cmd += [
                "--frames",
                "--frame-width", "1024",
                "--dense-until", "1200",
                "--dense-interval", "45",
                "--max-frames", "60",
            ]
        elif frames:
            cmd.append("--frames")

        def run(job):
            try:
                rc, out, err, timed_out = run_streaming(
                    cmd, cwd=str(PROJECT_DIR), timeout=CONVERT_TIMEOUT,
                    on_line=job.emit, creationflags=NO_WINDOW)
            finally:
                # Uploaded temp files must outlive the REQUEST but not the
                # job — clean up here, not in the handler.
                if cleanup is not None:
                    try:
                        cleanup()
                    except OSError:
                        pass
            if timed_out:
                return {"success": False,
                        "error": f"Conversion timed out after {CONVERT_TIMEOUT}s"}
            stderr = "\n".join(err).strip()
            if rc == 0:
                stdout_lines = [l for l in out if l.strip()]
                visual_failure = next(
                    (line.split("visual-capture-failed:", 1)[1].strip()
                     for line in err
                     if "visual-capture-failed:" in line),
                    "",
                )
                result = {
                    "success": True,
                    "output_path": stdout_lines[-1] if stdout_lines else "",
                    "already_converted": any(
                        l.startswith("already-converted:") for l in err),
                    "stderr": stderr,
                }
                if visual_failure:
                    result["visual_capture_failed"] = True
                    result["visual_capture_error"] = visual_failure
                if original_filename:
                    result["original_filename"] = original_filename
                if result["already_converted"] and result["output_path"]:
                    result.update(duplicate_details(
                        result["output_path"], vault, frames or dense))
                return result
            err_msg = stderr or "\n".join(out).strip() or f"Exit code {rc}"
            return {"success": False, "error": err_msg, "stderr": stderr}

        job_id = JOBS.submit("convert", JOB_LANES["convert"], run,
                             label=label or input_value[:80])
        return {"success": True, "job_id": job_id, "state": "queued"}

    # ---------- routes ----------

    def do_GET(self):
        try:
            self._dispatch_get()
        except Exception as exc:
            sys.stderr.write(f"GET {self.path} crashed: {exc!r}\n")
            try:
                self._send_json({"success": False, "error": f"Server error: {exc}"}, 500)
            except Exception:
                pass

    def _query(self, key: str) -> str | None:
        """Read a single query-string parameter from self.path."""
        if "?" not in self.path:
            return None
        qs = self.path.split("?", 1)[1]
        from urllib.parse import parse_qs
        vals = parse_qs(qs).get(key)
        return vals[0] if vals else None

    def _dispatch_get(self):
        path = self.path.split("?", 1)[0]

        if path == "/healthz":
            # Liveness must never depend on the filesystem: watcher_health()
            # touches the vault dirs, and if that raises (e.g. a macOS TCC
            # denial on ~/Documents after a Homebrew python upgrade), /healthz
            # must still answer ok:true — it's the watchdog's up/down signal.
            try:
                watcher = watcher_health()
            except Exception as exc:
                watcher = {"error": f"{type(exc).__name__}: {exc}"}
            self._send_json({"ok": True,
                             "ts": datetime.now().isoformat(timespec="seconds"),
                             "watcher": watcher})
            return

        # Async job inspection — the UI polls these instead of holding a
        # long fetch open while convert/ingest/studio runs.
        if path == "/jobs":
            try:
                limit = int(self._query("limit") or 20)
            except ValueError:
                limit = 20
            self._send_json({"success": True, "jobs": JOBS.list(limit=limit)})
            return
        if path.startswith("/jobs/"):
            snap = JOBS.snapshot(path[len("/jobs/"):].strip("/"))
            if snap is None:
                self._send_json({"success": False, "error": "Unknown job id"}, 404)
            else:
                self._send_json({"success": True, "job": snap})
            return

        if path in ("/", "/index.html"):
            self._send_file(INDEX, "text/html; charset=utf-8")
            return

        # Landing page (marketing) — served from the same origin so nav between
        # the two feels like one product.
        if path in ("/about", "/about/", "/landing", "/landing/"):
            self._send_file(LANDING_INDEX, "text/html; charset=utf-8")
            return

        if path in ("/studio", "/studio/"):
            if LANDING_STUDIO.exists():
                self._send_file(LANDING_STUDIO, "text/html; charset=utf-8")
            else:
                self._send_json({"success": False, "error": "studio.html missing"}, 404)
            return

        if path in ("/wiki", "/wiki/"):
            wiki_html = LANDING_DIR / "wiki.html"
            if wiki_html.exists():
                self._send_file(wiki_html, "text/html; charset=utf-8")
            else:
                self._send_json({"success": False, "error": "wiki.html missing"}, 404)
            return

        if path == "/wiki/data":
            slug = self._query("wiki") or "wiki"
            self._send_json(build_wiki_data(slug))
            return

        if path == "/wiki/graph":
            slug = self._query("wiki") or "wiki"
            self._send_json(build_wiki_graph(slug))
            return

        if path == "/wikis":
            self._send_json({"wikis": list_wikis()})
            return

        if path == "/api/writer/libraries":
            libraries = [{
                "slug": wiki["slug"],
                "name": wiki["name"],
                "model": wiki["model"],
                "pageCount": sum(wiki["counts"].values()),
            } for wiki in list_wikis()]
            self._send_writer_json({"success": True, "libraries": libraries})
            return

        if path == "/api/writer/knowledge-pack":
            vault = _resolve_vault_checked(self._query("wiki"))
            if vault is None:
                self._send_writer_json({"success": False, "error": "Unknown Riverfed wiki"}, 404)
                return
            try:
                pack = _writer_pack.build_pack(vault, _model_for(vault))
            except ValueError as exc:
                self._send_writer_json({"success": False, "error": str(exc)}, 422)
                return
            self._send_writer_json(pack)
            return

        if path == "/watcher":
            vault = _resolve_vault_checked(self._query("wiki"))
            if vault is None:
                self._send_json({"success": False, "error": "unknown wiki"}, 404)
                return
            self._send_json({"success": True, "wiki": vault.slug,
                             **_watcher.load_subs(vault)})
            return

        if path == "/api/designs":
            self._handle_design_list()
            return
        if path.startswith("/api/designs/"):
            slug = path[len("/api/designs/"):].rstrip("/")
            self._handle_design_get(slug)
            return

        if path == "/api/models":
            self._handle_model_list()
            return
        if path.startswith("/api/models/"):
            mid = path[len("/api/models/"):].rstrip("/")
            self._handle_model_get(mid)
            return

        # Shared top-nav component — single source of truth, served to every
        # page (/, /about, /studio, /wiki) so the nav never drifts.
        if path == "/nav.js":
            self._send_file(LANDING_DIR / "nav.js",
                            "application/javascript; charset=utf-8")
            return

        # Browsers request /favicon.ico implicitly on every page; without
        # this, the first page-load of a session logs a console 404.
        if path == "/favicon.ico":
            self._send_file(
                LANDING_DIR / "icons" / "png" / "riverfed-mark.png",
                "image/png")
            return

        # Landing-page assets (icons, fonts referenced from /icons/…)
        if path.startswith("/icons/"):
            name = unquote(path[len("/icons/"):])
            target = (LANDING_DIR / "icons" / name).resolve()
            try:
                target.relative_to((LANDING_DIR / "icons").resolve())
            except ValueError:
                self._send_json({"success": False, "error": "Forbidden"}, 403)
                return
            self._send_file(target)
            return

        # Read-only vault page view — the /wiki UI's "OPEN MD" links. Vaults
        # can live outside the repo (vault home) since the C1 split, so
        # GitHub blob URLs no longer reach them; this serves the markdown
        # locally for every vault, repo or home.
        if path == "/vault/page":
            vault = _resolve_vault_checked(self._query("wiki"))
            if vault is None:
                self._send_json({"success": False, "error": "Unknown wiki"}, 404)
                return
            name = unquote(self._query("file") or "")
            target = (vault.root / name).resolve()
            try:
                target.relative_to(vault.root.resolve())
            except ValueError:
                self._send_json({"success": False, "error": "Forbidden"}, 403)
                return
            if target.suffix.lower() != ".md" or not target.is_file():
                self._send_json({"success": False, "error": "Not found"}, 404)
                return
            self._render_md_page(target, title=_page_title(target), vault=vault)
            return

        if path == "/files":
            vault = _resolve_vault_checked(self._query("wiki"))
            out_dir = vault.output if vault else OUTPUT_DIR
            self._send_json({"files": list_output_files(out_dir)})
            return

        if path.startswith("/files/"):
            vault = _resolve_vault_checked(self._query("wiki"))
            out_dir = (vault.output if vault else OUTPUT_DIR).resolve()
            name = unquote(path[len("/files/"):])
            target = (out_dir / name).resolve()
            try:
                target.relative_to(out_dir)
            except ValueError:
                self._send_json({"success": False, "error": "Forbidden"}, 403)
                return
            if name.endswith(".md"):
                # Output transcripts live outside any vault's page folders, so
                # no wikilink resolver — [[refs]] (rare here) render as chips.
                self._render_md_page(target, title=_page_title(target), vault=None)
            else:
                self._send_file(target)
            return

        if path == "/pending":
            self._send_json(self._list_pending(self._query("wiki")))
            return

        self._send_json({"success": False, "error": "Not found"}, 404)

    @staticmethod
    def _wikilink_resolver(vault):
        """Build a slug -> '/vault/page?...' resolver for one vault so
        [[wikilinks]] become real in-tool links. Indexes every *.md one
        level under the vault root (the model's page folders); unresolved
        slugs return None and render as styled non-links."""
        index: dict[str, str] = {}
        try:
            for folder in sorted(p for p in vault.root.iterdir() if p.is_dir()):
                if folder.name.startswith(".") or folder.name == "output":
                    continue
                for page in folder.glob("*.md"):
                    index.setdefault(page.stem, f"{folder.name}/{page.name}")
        except OSError:
            pass

        def resolve(slug: str) -> str | None:
            rel = index.get(slug) or index.get(slug.strip().lower().replace(" ", "-"))
            if not rel:
                return None
            return ("/vault/page?wiki=" + quote(vault.slug)
                    + "&file=" + quote(rel))

        return resolve

    def _render_md_page(self, target: Path, title: str, vault=None) -> None:
        """Serve one markdown file as an on-brand HTML page (or raw text when
        ?raw=1). Shared by /vault/page and /files/<name>.md."""
        if self._query("raw"):
            self._send_file(target, "text/markdown; charset=utf-8")
            return
        try:
            md_text = target.read_text(encoding="utf-8", errors="replace")
        except OSError:
            self._send_json({"success": False, "error": "Not found"}, 404)
            return
        resolver = self._wikilink_resolver(vault) if vault is not None else None
        raw_href = self.path + ("&raw=1" if "?" in self.path else "?raw=1")
        back = "/wiki" if vault is not None else None
        html_doc = md_view.render_page(
            md_text, title=title, resolve_wikilink=resolver,
            back_href=back, raw_href=raw_href,
        )
        self._send_bytes(200, "text/html; charset=utf-8", html_doc.encode("utf-8"))

    def _list_pending(self, wiki_slug: str | None = None) -> dict:
        if not PENDING_SCRIPT.exists():
            return {
                "pending": [],
                "count": 0,
                "ready_count": 0,
                "blocked_count": 0,
                "wiki_available": False,
            }
        vault = _resolve_vault_checked(wiki_slug)
        if vault is None:
            return {
                "pending": [],
                "count": 0,
                "ready_count": 0,
                "blocked_count": 0,
                "wiki_available": False,
                "error": f"Knowledge base '{wiki_slug}' not found",
            }
        try:
            source_payload = _pending_payload(vault)
        except Exception as exc:
            source_payload = {
                "pending": [],
                "count": 0,
                "ready_count": 0,
                "blocked_count": 0,
                "error": str(exc),
            }
        agent_auto, agent_auth = agent_auth_summary()
        return {
            **source_payload,
            "wiki": vault.slug,
            "wiki_available": True,
            "agent_ok": agent_auto is not None,
            "agent_auth": agent_auth,
            "wiki_busy": JOBS.lane_active(JOB_LANES["ingest"]),
            "review": read_review_state(vault.slug),
        }

    def _check_agent_auth(self, requested: str | None) -> tuple[str | None, dict | None]:
        """Shared pre-submit gate for jobs that shell out to an agent CLI.
        Returns (resolved_provider, None) when ready, or (None,
        error_response). Runs in the request (fast) so the user gets an
        immediate, friendly failure instead of a queued job that dies.
        An EXPLICIT provider that is not ready hard-fails with its login
        hint — never a silent fallback to the other provider."""
        provider, pstatus = _agent.resolve_provider(requested,
                                                    ttl=AGENT_STATUS_TTL)
        if provider is None:
            return None, {"success": False,
                          "error": _agent.unavailable_message(pstatus)}
        return provider, None

    def _submit_ingest(self, wiki_slug: str | None = None,
                       provider_req: str | None = None) -> dict:
        """Queue an ingest job on the 'wiki' lane (serialized with review —
        a second click queues behind the first instead of being rejected)."""
        vault = _resolve_vault_checked(wiki_slug)
        if vault is None:
            return {"success": False,
                    "error": f"Knowledge base '{wiki_slug}' not found"}
        provider, auth_err = self._check_agent_auth(provider_req)
        if auth_err:
            return auth_err
        return submit_ingest_job(vault, provider)

    def _submit_review(self, wiki_slug: str | None = None,
                       provider_req: str | None = None) -> dict:
        """Queue a promote_backlog.py run on the 'wiki' lane. Resets the
        auto-review counter on success (inside the job, when it actually
        finishes)."""
        if not PROMOTE_SCRIPT.exists():
            return {"success": False, "error": "promote_backlog.py not found"}
        vault = _resolve_vault_checked(wiki_slug)
        if vault is None:
            return {"success": False,
                    "error": f"Knowledge base '{wiki_slug}' not found"}
        provider, auth_err = self._check_agent_auth(provider_req)
        if auth_err:
            return auth_err

        cmd = [python_executable(), "-u", str(PROMOTE_SCRIPT),
               "--wiki", vault.slug, "--provider", provider]

        def run(job):
            rc, out, err, timed_out = run_streaming(
                cmd, cwd=str(PROJECT_DIR), timeout=INGEST_TIMEOUT,
                on_line=job.emit, creationflags=NO_WINDOW)
            if timed_out:
                return {"success": False,
                        "error": f"Review timed out after {INGEST_TIMEOUT}s"}
            stdout = "\n".join(out).strip()
            stderr = "\n".join(err).strip()
            if rc != 0:
                return {"success": False,
                        "error": stderr or stdout or f"Exit {rc}"}
            # Reset this vault's counter on success
            state_file = _review_state_file(vault)
            state_file.parent.mkdir(parents=True, exist_ok=True)
            from datetime import timezone
            state_file.write_text(json.dumps({
                "ingests_since_review": 0,
                "last_review_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            }, indent=2) + "\n", encoding="utf-8")
            return {"success": True,
                    "stdout_tail": stdout.splitlines()[-5:]}

        label = ("Promote backlog (review)" if vault.slug == "wiki"
                 else f"Promote backlog ({vault.display_name()})")
        job_id = JOBS.submit("review", JOB_LANES["review"], run, label=label)
        return {"success": True, "job_id": job_id, "state": "queued"}

    def _handle_studio(self, route: str) -> None:
        """POST /studio/marp or /studio/diagram.

        Body (JSON): { wiki: <slug>, prompt: <str>, slides?: <int>,
                       audience?: <str> }
        Invokes the matching wiki/scripts/studio_*.py script via Claude
        Code headless and returns the generated file path.
        """
        ctype = self.headers.get("Content-Type", "")
        length = int(self.headers.get("Content-Length", "0") or 0)
        if length <= 0 or not ctype.startswith("application/json"):
            self._send_json({"success": False, "error": "Expected JSON body"}, 400)
            return
        try:
            payload = json.loads(self.rfile.read(length))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            self._send_json({"success": False, "error": f"Bad JSON: {exc}"}, 400)
            return

        wiki_slug = (payload.get("wiki") or "").strip()
        user_prompt = (payload.get("prompt") or "").strip()
        if not wiki_slug or not user_prompt:
            self._send_json({"success": False, "error": "wiki + prompt required"}, 400)
            return

        # Validate wiki choice against actual discoverable wikis
        wikis = {w["slug"]: w for w in list_wikis()}
        if wiki_slug not in wikis:
            self._send_json({"success": False, "error": f"Unknown wiki: {wiki_slug}"}, 400)
            return
        # Studio scripts take --wiki as a PATH: repo-relative for repo
        # vaults ("wikis/riverfed-ops"), absolute for vault-home ones.
        wiki_path = wikis[wiki_slug]["path"]

        # Resolve design_id to a designs/<id>.md path, with path-traversal
        # guard (only accept alphanumeric + dash/underscore identifiers).
        design_id_raw = (payload.get("design_id") or "riverfed").strip()
        design_path: Path | None = None
        if re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", design_id_raw or ""):
            candidate = PROJECT_DIR / "designs" / f"{design_id_raw}.md"
            if candidate.exists() and candidate.is_file():
                design_path = candidate
        if design_path is None:
            # Silent fallback to default — the renderer's hardcoded
            # palette already matches riverfed.
            fallback = PROJECT_DIR / "designs" / "riverfed.md"
            if fallback.exists():
                design_path = fallback

        # Auth check (same pattern as /ingest). The provider comes from the
        # JSON body ("auto" or any agent_runner.PROVIDERS id); explicit
        # choices hard-fail here when that CLI isn't ready.
        provider_req = (payload.get("provider") or "auto").strip() or "auto"
        provider, auth_err = self._check_agent_auth(provider_req)
        if auth_err:
            self._send_json(auth_err)
            return

        # Build the subprocess command. All three generators accept
        # --design <path> — studio_pptx.py uses the tokens to override
        # its palette/fonts; the others accept the flag but log a
        # warning ("design X not yet wired").
        design_args = ["--design", str(design_path)] if design_path else []
        provider_args = ["--provider", provider]
        if route == "/studio/marp":
            script = STUDIO_MARP_SCRIPT
            cmd = [python_executable(), "-u", str(script),
                   "--wiki", wiki_path,
                   "--prompt", user_prompt,
                   *design_args, *provider_args]
            slides = payload.get("slides")
            if isinstance(slides, int) and 4 <= slides <= 60:
                cmd += ["--slides", str(slides)]
            audience = (payload.get("audience") or "").strip()
            if audience:
                cmd += ["--audience", audience]
            kind = "marp"
        elif route == "/studio/pptx":
            script = STUDIO_PPTX_SCRIPT
            cmd = [python_executable(), "-u", str(script),
                   "--wiki", wiki_path,
                   "--prompt", user_prompt,
                   *design_args, *provider_args]
            slides = payload.get("slides")
            if isinstance(slides, int) and 4 <= slides <= 60:
                cmd += ["--slides", str(slides)]
            audience = (payload.get("audience") or "").strip()
            if audience:
                cmd += ["--audience", audience]
            kind = "pptx"
        elif route == "/studio/skills":
            # Skills are plain markdown — no design flag. The script prints
            # one SKILL:<rel> line per generated skill (streams into the job
            # log) and the library root as the canonical final path.
            script = STUDIO_SKILLS_SCRIPT
            cmd = [python_executable(), "-u", str(script),
                   "--wiki", wiki_path,
                   "--prompt", user_prompt,
                   *provider_args]
            kind = "skills"
        elif route == "/studio/anki":
            # Flashcards are Anki-native styled — no design flag either.
            script = STUDIO_ANKI_SCRIPT
            cmd = [python_executable(), "-u", str(script),
                   "--wiki", wiki_path,
                   "--prompt", user_prompt,
                   *provider_args]
            cards = payload.get("cards")
            if isinstance(cards, int) and 5 <= cards <= 200:
                cmd += ["--cards", str(cards)]
            kind = "anki"
        else:
            script = STUDIO_DIAGRAM_SCRIPT
            cmd = [python_executable(), "-u", str(script),
                   "--wiki", wiki_path,
                   "--prompt", user_prompt,
                   *design_args, *provider_args]
            kind = "diagram"

        if not script.exists():
            self._send_json({"success": False, "error": f"{script.name} not found"}, 500)
            return

        with_guide = bool(payload.get("with_guide")) and STUDIO_GUIDE_SCRIPT.exists()
        audience = (payload.get("audience") or "").strip()

        def _parse_paths(stdout_lines: list[str]) -> tuple[str, dict[str, str]]:
            """Studio scripts print one path per line; the canonical path is
            the final line. Zero or more `RENDERED:<fmt>:<rel-path>` lines
            name the auto-rendered outputs (HTML/PDF/PPTX, guide md/docx)."""
            lines = [l.strip() for l in stdout_lines if l.strip()]
            out_path = lines[-1] if lines else ""
            renders: dict[str, str] = {}
            for line in lines:
                if line.startswith("RENDERED:"):
                    try:
                        _, fmt, path = line.split(":", 2)
                        renders[fmt.strip()] = path.strip()
                    except ValueError:
                        pass
            return out_path, renders

        def run(job):
            rc, out, err, timed_out = run_streaming(
                cmd, cwd=str(PROJECT_DIR), timeout=STUDIO_TIMEOUT,
                on_line=job.emit, creationflags=NO_WINDOW)
            if timed_out:
                return {"success": False,
                        "error": f"Generation timed out after {STUDIO_TIMEOUT}s"}
            out_path, renders = _parse_paths(out)
            if rc != 0 or not out_path:
                err_msg = ("\n".join(err).strip() or "\n".join(out).strip()
                           or f"Exit code {rc}")
                return {"success": False, "error": err_msg}

            result = {
                "success": True,
                "kind": kind,
                "path": out_path,
                "wiki": wiki_slug,
                "stderr_tail": [l for l in err if l.strip()][-3:],
            }
            if renders:
                result["renders"] = renders
            if kind == "skills":
                result["skills"] = [l.split("SKILL:", 1)[1].strip()
                                    for l in out if l.strip().startswith("SKILL:")]

            # Chained: "Also generate a speaking guide" runs inside the SAME
            # job (second phase), so the UI sees one job with live progress
            # through both phases.
            if with_guide:
                job.emit("[studio] deck done — generating speaking guide…")
                guide_cmd = [python_executable(), "-u", str(STUDIO_GUIDE_SCRIPT),
                             "--wiki", wiki_path,
                             "--target", out_path,
                             *design_args, *provider_args]
                if audience:
                    guide_cmd += ["--audience", audience]
                grc, gout, gerr, gtimed = run_streaming(
                    guide_cmd, cwd=str(PROJECT_DIR), timeout=STUDIO_TIMEOUT,
                    on_line=job.emit, creationflags=NO_WINDOW)
                if gtimed:
                    result["guide_error"] = (
                        f"Guide generation timed out after {STUDIO_TIMEOUT}s")
                else:
                    guide_path, guide_renders = _parse_paths(gout)
                    if grc == 0 and guide_path:
                        result["guide_path"] = guide_path
                        if guide_renders:
                            result["guide_renders"] = guide_renders
                    else:
                        result["guide_error"] = ("\n".join(gerr).strip()
                                                 or "\n".join(gout).strip())
            return result

        label = f"{kind}: {user_prompt[:60]}"
        job_id = JOBS.submit("studio", JOB_LANES["studio"], run, label=label)
        self._send_json({"success": True, "job_id": job_id, "state": "queued",
                         "kind": kind})

    # ====================================================================
    # Design picker — CRUD over designs/*.md (shipped) + designs/custom/*.md
    # ====================================================================

    _DESIGN_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")

    def _design_tokens_module(self):
        """Lazy-import the design_tokens helper from wiki/scripts/."""
        scripts_dir = WIKI_DIR / "scripts"
        if str(scripts_dir) not in sys.path:
            sys.path.insert(0, str(scripts_dir))
        import importlib
        if "design_tokens" in sys.modules:
            return importlib.reload(sys.modules["design_tokens"])
        import design_tokens as dt
        return dt

    def _serialize_design_summary(self, d) -> dict:
        """Compact metadata for the tile grid — colours + font hints."""
        swatch = lambda k, fb: ("#" + d.color(k, fb)) if k in d.colors else None
        return {
            "id": d.source_path.stem if d.source_path else "",
            "name": d.name,
            "description": d.description,
            "source": d.source,
            "overrides_shipped": d.overrides_shipped,
            "swatches": [
                # Fallbacks are house-palette greens/neutrals, never blue+purple:
                # these two render adjacent in the picker, and design.md's
                # anti-AI-slop contract forbids that pairing as a generic
                # "AI" signal — including for designs that omit the tokens.
                swatch("primary", "46c98b"),
                swatch("secondary", "6c7278"),
                swatch("success", "46c98b") or swatch("highlight", "ffd93d"),
                swatch("background", "0a0d12"),
                swatch("surface", "fafaff"),
            ],
            "fonts": {
                "display": d.font_family("h1", "Inter"),
                "body":    d.font_family("body-md", "Inter"),
                "mono":    d.font_family("eyebrow", "JetBrains Mono"),
            },
        }

    def _handle_design_list(self) -> None:
        try:
            dt = self._design_tokens_module()
            designs = dt.list_designs(PROJECT_DIR)
        except Exception as exc:
            self._send_json({"success": False, "error": f"list failed: {exc}"}, 500)
            return
        self._send_json({
            "success": True,
            "designs": [self._serialize_design_summary(d) for d in designs],
        })

    def _handle_design_get(self, slug: str) -> None:
        if not self._DESIGN_ID_RE.match(slug or ""):
            self._send_json({"success": False, "error": "bad id"}, 400)
            return
        try:
            dt = self._design_tokens_module()
            designs = {(d.source_path.stem if d.source_path else ""): d
                       for d in dt.list_designs(PROJECT_DIR)}
        except Exception as exc:
            self._send_json({"success": False, "error": f"list failed: {exc}"}, 500)
            return
        d = designs.get(slug)
        if d is None:
            self._send_json({"success": False, "error": "not found"}, 404)
            return
        shipped_path = PROJECT_DIR / "designs" / f"{slug}.md"
        self._send_json({
            "success": True,
            "design": {
                "id": slug,
                "name": d.name,
                "description": d.description,
                "colors": d.colors,
                "typography": d.typography,
                "rounded": d.rounded,
                "spacing": d.spacing,
                "components": d.components,
                "source": d.source,
                "overrides_shipped": d.overrides_shipped,
                "has_shipped_default": shipped_path.exists(),
            },
        })

    def _handle_design_put(self, slug: str) -> None:
        if not self._DESIGN_ID_RE.match(slug or ""):
            self._send_json({"success": False, "error": "bad id"}, 400)
            return
        length = int(self.headers.get("Content-Length", "0") or 0)
        ctype = self.headers.get("Content-Type", "")
        if length <= 0 or not ctype.startswith("application/json"):
            self._send_json({"success": False, "error": "expected JSON body"}, 400)
            return
        try:
            payload = json.loads(self.rfile.read(length))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            self._send_json({"success": False, "error": f"bad JSON: {exc}"}, 400)
            return

        name = (payload.get("name") or "").strip()
        if not name:
            self._send_json({"success": False, "error": "name required"}, 400)
            return
        # Basic colour validation: each value must be a hex string
        colors = payload.get("colors") or {}
        if not isinstance(colors, dict):
            self._send_json({"success": False, "error": "colors must be an object"}, 400)
            return
        hex_re = re.compile(r"^#?[0-9A-Fa-f]{3,8}$")
        clean_colors: dict[str, str] = {}
        for k, v in colors.items():
            if not isinstance(v, str) or not hex_re.match(v.strip()):
                continue  # silently drop invalid; the renderer falls back
            val = v.strip()
            if not val.startswith("#"):
                val = "#" + val
            clean_colors[k] = val

        # Typography: only fontFamily for h1 / body-md / eyebrow is editable
        # via the UI; preserve any other roles the user may have copied in.
        typography = payload.get("typography") or {}
        if not isinstance(typography, dict):
            typography = {}
        clean_typo = {}
        for role, spec in typography.items():
            if isinstance(spec, dict):
                clean_typo[role] = {k: v for k, v in spec.items()
                                    if isinstance(v, (str, int, float)) and v != ""}

        rounded = payload.get("rounded") or {}
        spacing = payload.get("spacing") or {}

        try:
            dt = self._design_tokens_module()
            tokens = dt.DesignTokens(
                name=name,
                description=str(payload.get("description") or "").strip(),
                colors=clean_colors,
                typography=clean_typo,
                rounded={k: str(v) for k, v in (rounded or {}).items() if v},
                spacing={k: str(v) for k, v in (spacing or {}).items() if v},
            )
            out = PROJECT_DIR / "designs" / "custom" / f"{slug}.md"
            dt.save_design(out, tokens)
        except Exception as exc:
            self._send_json({"success": False, "error": f"save failed: {exc}"}, 500)
            return

        self._send_json({"success": True, "id": slug,
                         "path": out.relative_to(PROJECT_DIR).as_posix()})

    def _handle_design_delete(self, slug: str) -> None:
        if not self._DESIGN_ID_RE.match(slug or ""):
            self._send_json({"success": False, "error": "bad id"}, 400)
            return
        custom_path = PROJECT_DIR / "designs" / "custom" / f"{slug}.md"
        if not custom_path.exists():
            # Reset on a shipped design with no custom override = no-op
            self._send_json({"success": True, "message": "nothing to delete"})
            return
        try:
            custom_path.unlink()
        except Exception as exc:
            self._send_json({"success": False, "error": f"delete failed: {exc}"}, 500)
            return
        # If the shipped version exists, deleting the custom = reset to default
        shipped_path = PROJECT_DIR / "designs" / f"{slug}.md"
        self._send_json({
            "success": True,
            "reset_to_default": shipped_path.exists(),
        })

    # ---------- knowledge-model CRUD (/api/models) ----------
    # Same contract as the designs CRUD: GET list/one, PUT writes a custom
    # override under models/custom/<id>/, DELETE removes the custom (reset
    # to shipped when one exists). A model is a directory (manifest +
    # SCHEMA.md + two prompt templates), not a single file.

    def _serialize_model_summary(self, m) -> dict:
        return {
            "id": m.id,
            "name": m.name,
            "description": m.description,
            "source": m.source,
            "overrides_shipped": m.overrides_shipped,
            "has_shipped_default": (_models.MODELS_DIR / m.id / "model.md").exists(),
            "capture_folder": m.capture_folder(),
            "folders": [{
                "name": f,
                "kind": m.kind(f),
                "promote_after": m.promote_after(f),
                "role": str((m.folders.get(f) or {}).get("role") or ""),
            } for f in m.folders],
            "links": list(m.links),
            "generators": m.generators,
        }

    def _handle_model_list(self) -> None:
        try:
            models = _models.list_models()
        except Exception as exc:
            self._send_json({"success": False, "error": f"list failed: {exc}"}, 500)
            return
        self._send_json({
            "success": True,
            "models": [self._serialize_model_summary(m) for m in models],
        })

    def _handle_model_get(self, mid: str) -> None:
        if not _models.valid_model_id(mid):
            self._send_json({"success": False, "error": "bad id"}, 400)
            return
        d = _models.resolve_model_dir(mid)
        if d is None:
            self._send_json({"success": False, "error": "not found"}, 404)
            return
        try:
            m = _models.load_model(d)
            m.source = "custom" if d.parent.name == "custom" else "shipped"
            m.overrides_shipped = (m.source == "custom"
                                   and (_models.MODELS_DIR / mid / "model.md").exists())
            payload = self._serialize_model_summary(m)
            payload["folders_spec"] = m.folders
            payload["links_spec"] = m.links
            payload["ingest_prompt"] = m.ingest_prompt()
            payload["promote_prompt"] = m.promote_prompt()
            payload["schema"] = m.schema_path.read_text(encoding="utf-8") \
                if m.schema_path.exists() else ""
        except Exception as exc:
            self._send_json({"success": False, "error": f"load failed: {exc}"}, 500)
            return
        self._send_json({"success": True, "model": payload})

    @staticmethod
    def _validate_prompt_template(tmpl: str, km, with_transcript: bool) -> str | None:
        """A custom prompt with a typo'd {placeholder} (or a stray literal
        brace) must fail at SAVE time, not mid-ingest. Returns an error
        string or None."""
        args = {"wiki_rel": "wiki", "output_rel": "output", "wiki_slug": "wiki",
                **km.prompt_format_args()}
        if with_transcript:
            args["transcript_name"] = "example.md"
        try:
            tmpl.format(**args)
        except KeyError as exc:
            return f"unknown placeholder {{{exc.args[0]}}}"
        except (IndexError, ValueError) as exc:
            return f"bad template syntax: {exc} (escape literal braces as {{{{ }}}})"
        return None

    def _handle_model_put(self, mid: str) -> None:
        if not _models.valid_model_id(mid):
            self._send_json({"success": False, "error": "bad id"}, 400)
            return
        length = int(self.headers.get("Content-Length", "0") or 0)
        ctype = self.headers.get("Content-Type", "")
        if length <= 0 or not ctype.startswith("application/json"):
            self._send_json({"success": False, "error": "expected JSON body"}, 400)
            return
        try:
            payload = json.loads(self.rfile.read(length))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            self._send_json({"success": False, "error": f"bad JSON: {exc}"}, 400)
            return

        name = (payload.get("name") or "").strip()
        if not name:
            self._send_json({"success": False, "error": "name required"}, 400)
            return

        # Anything the payload omits is inherited from a base model: the
        # explicit `base`, else the existing model with this id, else the
        # default — so "duplicate karpathy-wiki and tweak one knob" is a
        # one-field PUT.
        base_id = (payload.get("base") or "").strip() or mid
        base_dir = _models.resolve_model_dir(base_id) \
            or _models.resolve_model_dir(_models.DEFAULT_MODEL_ID)
        try:
            base = _models.load_model(base_dir)
        except Exception as exc:
            self._send_json({"success": False,
                             "error": f"base model failed to load: {exc}"}, 500)
            return

        folders = payload.get("folders") if isinstance(payload.get("folders"), dict) \
            else base.folders
        if not folders:
            self._send_json({"success": False, "error": "folders must be a non-empty object"}, 400)
            return
        folders = {str(k): (dict(v) if isinstance(v, dict) else {})
                   for k, v in folders.items()}
        for fname in folders:
            if not _models.valid_folder_name(fname):
                self._send_json({"success": False,
                                 "error": f"invalid folder name '{fname}' — "
                                 "must be a single lowercase path component "
                                 "(letters, digits, - or _), not a reserved "
                                 "name"}, 400)
                return

        links = payload.get("links") if isinstance(payload.get("links"), dict) \
            else base.links
        clean_links: dict[str, dict] = {}
        for lname, spec in (links or {}).items():
            if not isinstance(spec, dict) or \
                    not all(isinstance(spec.get(k), str) and spec.get(k)
                            for k in ("from", "field", "to")):
                self._send_json({"success": False,
                                 "error": f"link '{lname}' needs from/field/to strings"}, 400)
                return
            clean_links[str(lname)] = {k: str(v) for k, v in spec.items()}

        generators = payload.get("generators")
        if isinstance(generators, str):
            generators = [g.strip() for g in generators.split(",") if g.strip()]
        if not isinstance(generators, list):
            generators = base.generators

        km = _models.KnowledgeModel(
            id=mid, name=name,
            description=str(payload.get("description") or base.description or "").strip(),
            folders=folders, links=clean_links,
            bases=dict(base.bases),
            generators=[str(g) for g in generators],
            search_hint=str(payload.get("search_hint") or base.search_hint or ""),
            source_path=_models.MODELS_DIR / "custom" / mid / "model.md",
        )

        ingest_prompt = payload.get("ingest_prompt") or base.ingest_prompt()
        promote_prompt = payload.get("promote_prompt") or base.promote_prompt()
        for label, tmpl, with_t in (("ingest_prompt", ingest_prompt, True),
                                    ("promote_prompt", promote_prompt, False)):
            err = self._validate_prompt_template(str(tmpl), km, with_t)
            if err:
                self._send_json({"success": False, "error": f"{label}: {err}"}, 400)
                return
        schema = payload.get("schema")
        if not isinstance(schema, str) or not schema.strip():
            schema = base.schema_path.read_text(encoding="utf-8") \
                if base.schema_path.exists() else "# SCHEMA\n"

        try:
            target = _models.MODELS_DIR / "custom" / mid
            _models.save_model(target / "model.md", km)
            (target / "ingest-prompt.md").write_text(str(ingest_prompt), encoding="utf-8")
            (target / "promote-prompt.md").write_text(str(promote_prompt), encoding="utf-8")
            (target / "SCHEMA.md").write_text(schema, encoding="utf-8")
            # Obsidian Bases travel with the model: copy the base model's
            # templates so a customized model keeps its views (and so its
            # thresholds re-interpolate from the CUSTOM manifest — a model
            # customized to promote_after: 4 gets views that say 4). Copied,
            # not referenced, so editing them never mutates the shipped model.
            if base.bases and base.bases_dir.exists():
                shutil.copytree(base.bases_dir, target / "bases",
                                dirs_exist_ok=True)
            _models.load_model(target)   # round-trip check before reporting OK
        except Exception as exc:
            self._send_json({"success": False, "error": f"save failed: {exc}"}, 500)
            return

        self._send_json({"success": True, "id": mid,
                         "path": target.relative_to(PROJECT_DIR).as_posix()})

    def _handle_model_delete(self, mid: str) -> None:
        if not _models.valid_model_id(mid):
            self._send_json({"success": False, "error": "bad id"}, 400)
            return
        custom_dir = (_models.MODELS_DIR / "custom" / mid).resolve()
        try:
            custom_dir.relative_to((_models.MODELS_DIR / "custom").resolve())
        except ValueError:
            self._send_json({"success": False, "error": "bad id"}, 400)
            return
        if not (custom_dir / "model.md").exists():
            self._send_json({"success": True, "message": "nothing to delete"})
            return
        try:
            shutil.rmtree(custom_dir)
        except Exception as exc:
            self._send_json({"success": False, "error": f"delete failed: {exc}"}, 500)
            return
        self._send_json({
            "success": True,
            "reset_to_default": (_models.MODELS_DIR / mid / "model.md").exists(),
        })

    def do_PUT(self):
        try:
            path = self.path.split("?", 1)[0]
            if path.startswith("/api/designs/"):
                slug = path[len("/api/designs/"):].rstrip("/")
                self._handle_design_put(slug)
                return
            if path.startswith("/api/models/"):
                mid = path[len("/api/models/"):].rstrip("/")
                self._handle_model_put(mid)
                return
            self._send_json({"success": False, "error": "Not found"}, 404)
        except Exception as exc:
            sys.stderr.write(f"PUT {self.path} crashed: {exc!r}\n")
            try:
                self._send_json({"success": False, "error": f"Server error: {exc}"}, 500)
            except Exception:
                pass

    def do_DELETE(self):
        try:
            path = self.path.split("?", 1)[0]
            if path.startswith("/api/designs/"):
                slug = path[len("/api/designs/"):].rstrip("/")
                self._handle_design_delete(slug)
                return
            if path.startswith("/api/models/"):
                mid = path[len("/api/models/"):].rstrip("/")
                self._handle_model_delete(mid)
                return
            self._send_json({"success": False, "error": "Not found"}, 404)
        except Exception as exc:
            sys.stderr.write(f"DELETE {self.path} crashed: {exc!r}\n")
            try:
                self._send_json({"success": False, "error": f"Server error: {exc}"}, 500)
            except Exception:
                pass

    def do_POST(self):
        try:
            self._dispatch_post()
        except Exception as exc:
            sys.stderr.write(f"POST {self.path} crashed: {exc!r}\n")
            try:
                self._send_json({"success": False, "error": f"Server error: {exc}"}, 500)
            except Exception:
                pass

    def _dispatch_post(self):
        path = self.path.split("?", 1)[0]
        if path == "/ingest":
            self._send_json(self._submit_ingest(self._query("wiki"),
                                                self._query("provider")))
            return
        if path == "/review":
            self._send_json(self._submit_review(self._query("wiki"),
                                                self._query("provider")))
            return
        if path == "/wikis":
            self._handle_wiki_create()
            return
        if path.startswith("/watcher/"):
            self._handle_watcher_post(path)
            return
        if path in ("/studio/marp", "/studio/diagram", "/studio/pptx",
                    "/studio/skills", "/studio/anki"):
            self._handle_studio(path)
            return
        if path != "/convert":
            self._send_json({"success": False, "error": "Not found"}, 404)
            return

        # The target knowledge base for /convert comes from the query string
        # (works uniformly for JSON and multipart bodies).
        vault = _resolve_vault_checked(self._query("wiki"))
        if vault is None:
            self._send_json({"success": False,
                             "error": f"Knowledge base '{self._query('wiki')}' not found"}, 404)
            return

        ctype = self.headers.get("Content-Type", "")
        length = int(self.headers.get("Content-Length", "0") or 0)

        if length <= 0:
            self._send_json({"success": False, "error": "Empty request body"}, 400)
            return

        body = self.rfile.read(length)

        if ctype.startswith("application/json"):
            try:
                payload = json.loads(body)
            except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                self._send_json({"success": False, "error": f"Bad JSON: {exc}"}, 400)
                return
            url = (payload.get("url") or "").strip()
            if not url:
                self._send_json({"success": False, "error": "Empty URL"}, 400)
                return
            frames = bool(payload.get("frames"))
            dense = bool(payload.get("dense"))
            force = bool(payload.get("force"))
            self._send_json(self._submit_convert(url, frames=frames, dense=dense,
                                                 force=force, vault=vault))
            return

        if ctype.startswith("multipart/form-data"):
            parsed = parse_multipart_file(ctype, body)
            if not parsed:
                self._send_json({"success": False, "error": "No file in request"}, 400)
                return
            filename, content = parsed
            safe_name = Path(filename).name or "upload.bin"
            tmp_dir = Path(tempfile.mkdtemp(prefix="youtuber-upload-"))
            tmp_path = tmp_dir / safe_name
            tmp_path.write_bytes(content)

            def _cleanup(tmp_path=tmp_path, tmp_dir=tmp_dir):
                # Runs inside the JOB after convert.py finishes — the temp
                # upload must outlive this request, not the job.
                try:
                    tmp_path.unlink()
                    tmp_dir.rmdir()
                except OSError:
                    pass

            self._send_json(self._submit_convert(
                str(tmp_path), cleanup=_cleanup,
                original_filename=filename, label=filename, vault=vault))
            return

        self._send_json({"success": False, "error": f"Unsupported Content-Type: {ctype}"}, 415)

    def _handle_watcher_post(self, path: str) -> None:
        """POST /watcher/subscribe | /watcher/unsubscribe | /watcher/update |
        /watcher/check — channel subscriptions per knowledge base.
        Subscribe shells out to the venv python (channel resolution needs
        yt-dlp); the rest are in-process JSON state operations."""
        length = int(self.headers.get("Content-Length", "0") or 0)
        try:
            payload = json.loads(self.rfile.read(length)) if length > 0 else {}
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            self._send_json({"success": False, "error": f"Bad JSON: {exc}"}, 400)
            return

        # Vault-agnostic heartbeat: submit sweeps for any vault whose last
        # sweep is overdue (interval-guarded, so safe to hit every few minutes).
        # The launchd watchdog POSTs this so a stalled in-process cadence thread
        # can't silently dark auto-ingest.
        if path == "/watcher/tick":
            swept = sweep_due_vaults(force=bool(payload.get("force")))
            self._send_json({"success": True, "swept": swept})
            return

        vault = _resolve_vault_checked(payload.get("wiki"))
        if vault is None:
            self._send_json({"success": False, "error": "unknown wiki"}, 404)
            return

        if path == "/watcher/subscribe":
            url = (payload.get("url") or "").strip()
            if not url.startswith(("http://", "https://")):
                self._send_json({"success": False, "error": "url required"}, 400)
                return
            cmd = [python_executable(), str(PROJECT_DIR / "watcher.py"),
                   "--wiki", vault.slug, "--subscribe", url, "--json"]
            if payload.get("auto_ingest"):
                cmd.append("--auto")
            if payload.get("frames"):
                cmd.append("--frames")
            try:
                proc = subprocess.run(cmd, capture_output=True, text=True,
                                      encoding="utf-8", errors="replace",
                                      timeout=120, cwd=str(PROJECT_DIR),
                                      creationflags=NO_WINDOW)
            except subprocess.TimeoutExpired:
                self._send_json({"success": False,
                                 "error": "Channel lookup timed out"}, 504)
                return
            try:
                result = json.loads((proc.stdout or "").strip().splitlines()[-1])
            except (IndexError, json.JSONDecodeError):
                self._send_json({"success": False,
                                 "error": (proc.stderr or proc.stdout or
                                           f"exit {proc.returncode}").strip()[-300:]},
                                500)
                return
            self._send_json(result, 200 if result.get("success") else 400)
            return

        if path == "/watcher/unsubscribe":
            ok = _watcher.unsubscribe(vault, (payload.get("id") or "").strip())
            self._send_json({"success": ok} if ok else
                            {"success": False, "error": "no such subscription"},
                            200 if ok else 404)
            return

        if path == "/watcher/update":
            sub = _watcher.update_sub(
                vault, (payload.get("id") or "").strip(),
                auto_ingest=payload.get("auto_ingest"),
                frames=payload.get("frames"))
            if sub is None:
                self._send_json({"success": False, "error": "no such subscription"}, 404)
                return
            self._send_json({"success": True, "subscription": sub})
            return

        if path == "/watcher/check":
            if not _watcher.load_subs(vault)["subscriptions"]:
                self._send_json({"success": False,
                                 "error": "No subscriptions in this base yet"}, 400)
                return
            self._send_json(submit_watcher_sweep(vault))
            return

        self._send_json({"success": False, "error": "Not found"}, 404)

    def _handle_wiki_create(self) -> None:
        """POST /wikis {name, model?} — scaffold a new knowledge base at
        wikis/<slug>/ (the model's folders + its SCHEMA.md template +
        starter index.md declaring the model + its own output/ staging)."""
        length = int(self.headers.get("Content-Length", "0") or 0)
        if length <= 0:
            self._send_json({"success": False, "error": "Empty request body"}, 400)
            return
        try:
            payload = json.loads(self.rfile.read(length))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            self._send_json({"success": False, "error": f"Bad JSON: {exc}"}, 400)
            return

        title = (payload.get("name") or payload.get("title") or "").strip()
        slug = (payload.get("slug") or "").strip().lower()
        if not slug and title:
            # Derive a slug from the human name: "Investing & Markets" → "investing-markets"
            slug = re.sub(r"[-\s]+", "-",
                          re.sub(r"[^\w\s-]", "", title).strip().lower())[:64].strip("-")
        if not title:
            title = slug.replace("-", " ").replace("_", " ").title()
        model_id = (payload.get("model") or "").strip() or _models.DEFAULT_MODEL_ID

        vault, err = _wikis.scaffold_vault(
            slug, title, datetime.now().strftime("%Y-%m-%d"), model=model_id)
        if vault is None:
            self._send_json({"success": False, "error": err}, 400)
            return
        model = _model_for(vault)
        print(f"Created knowledge base '{vault.slug}' "
              f"(model {model.id}) at "
              f"{_wikis.display_path(vault.root)}")
        self._send_json({
            "success": True,
            "wiki": {
                "slug": vault.slug,
                "name": vault.display_name(),
                "path": _wikis.display_path(vault.root),
                "model": model.id,
                "counts": {folder: 0 for folder in model.folders},
            },
        })


def open_browser_when_ready(url: str) -> None:
    def _open():
        webbrowser.open(url)
    threading.Timer(0.6, _open).start()


def main() -> int:
    disable_windows_quick_edit()
    load_env_file()
    install_file_logging()
    if not INDEX.exists():
        sys.stderr.write(f"Error: {INDEX} not found.\n")
        return 1
    if not CONVERT.exists():
        sys.stderr.write(f"Error: {CONVERT} not found.\n")
        return 1
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    try:
        httpd = ThreadingHTTPServer((HOST, PORT), Handler)
    except OSError as exc:
        sys.stderr.write(f"Error: could not bind to {HOST}:{PORT} ({exc}).\n"
                         "Is another instance already running?\n")
        return 2

    url = f"http://{HOST}:{PORT}/"
    print(f"Serving at {url}")
    print(f"Output dir: {OUTPUT_DIR}")
    print("Press Ctrl+C to stop.")
    start_watcher_thread()
    open_browser_when_ready(url)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down…")
        httpd.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())
