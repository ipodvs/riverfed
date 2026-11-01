"""Automated wiki ingest on your own agent CLI's subscription auth.

Reads pending transcripts from ../../output and hands each one to a
headless agent CLI — Claude Code, Grok or Codex, picked by --provider
(see agent_runner) — which uses whatever auth that CLI is logged into,
typically a claude.ai / grok.com / ChatGPT subscription. No API key
required for any of them.

Usage:
    py -3.13 wiki/scripts/ingest.py                    # ingest every pending transcript
    py -3.13 wiki/scripts/ingest.py --dry-run          # show what would be ingested
    py -3.13 wiki/scripts/ingest.py --limit 1          # ingest only the first
    py -3.13 wiki/scripts/ingest.py --wiki investing   # target a wikis/<slug>/ vault
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import unicodedata
from pathlib import Path

# Claude's streamed output contains arrows, em-dashes, and other Unicode.
# Windows' default console codec (cp1252) can't encode most of them. Force
# UTF-8 with a replacement fallback so a stray glyph never crashes a long
# ingest mid-run.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

_SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_SCRIPTS_DIR))
from _wikis import PROJECT_DIR, Vault, display_path, resolve_vault  # noqa: E402
import _transcript  # noqa: E402  (shared with convert.py)
import pending as pending_scanner  # noqa: E402  (canonical revision selection)
from model_registry import KnowledgeModel, load_model_for_vault  # noqa: E402

OBSIDIAN_PASS = _SCRIPTS_DIR / "obsidian_pass.py"

INGEST_TIMEOUT_S = int(os.environ.get("INGEST_TIMEOUT_S", "1800"))

# After this many ingests, auto-run promote_backlog.py to surface new
# concept/entity pages from accumulated "watch for…" log entries. Set to
# 0 to disable. Default 5. The counter is per-vault (<vault>/.state/).
AUTO_REVIEW_THRESHOLD = int(os.environ.get("AUTO_REVIEW_THRESHOLD", "5"))
PROMOTE_SCRIPT = _SCRIPTS_DIR / "promote_backlog.py"

# Hide child-process console windows when this script is invoked from a
# windowless parent (pythonw.exe via the web server). Without this flag every
# subprocess opens a new flashing cmd window.
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform == "win32" else 0


# All agent invocations go through the provider layer (A6 step 1):
# argv construction, stdin prompt delivery, env scrub, NO_WINDOW and
# timeout handling live in agent_runner.run()/probe().
# (_SCRIPTS_DIR is already on sys.path from the _wikis import above.)
import agent_runner  # noqa: E402


# The ingest prompt template lives with the vault's knowledge model
# (models/<id>/ingest-prompt.md) — see model_registry.load_model_for_vault.
# Placeholders: {wiki_rel}, {output_rel}, {transcript_name}, {wiki_slug}
# + the model's promote_after knobs ({concept_promote_after} etc.).



# --------------------------------------------------------------------------- #
# Discovery
# --------------------------------------------------------------------------- #

def slugify(s: str, max_len: int = 80) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = re.sub(r"[^\w\s-]", "", s).strip().lower()
    s = re.sub(r"[-\s]+", "-", s)
    return s[:max_len].rstrip("-") or "untitled"


def extract_transcript_title(md: str) -> str | None:
    for line in md.splitlines()[:60]:
        m = re.match(r'^title:\s*"?(.+?)"?\s*$', line)
        if m:
            return m.group(1).strip()
    for line in md.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return None


# YouTube video id — the reliable identity of a transcript, independent of
# how it was slugged or re-titled. Catches re-conversions and SEO re-uploads
# that the agent merges into an existing page via `alt_url`.
_VIDEO_ID_RE = re.compile(r"(?:watch\?v=|youtu\.be/)([A-Za-z0-9_-]{6,})")


def _video_id(text: str) -> str | None:
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
    """Every YouTube video id already covered by a source page, from `url:`
    AND `alt_url:` in frontmatter. The ingest agent merges duplicate
    re-uploads into an existing page via `alt_url` and slugs pages by dropping
    editorial prefixes, so the video id is the only stable match."""
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
                vid = _video_id(line)
                if vid:
                    ids.add(vid)
    return ids


def pending_transcripts(vault: Vault, model: KnowledgeModel) -> list[Path]:
    """Return the same logical-source revisions shown in the editor.

    Recovery attempts are immutable, so output/ may hold both a failed
    capture and a usable retry for one video. The canonical pending scanner
    chooses one usable revision per logical source and prevents duplicate
    agent runs.
    """
    items = pending_scanner.collect_pending(vault, model)
    return [vault.output / item["filename"] for item in items]


# --------------------------------------------------------------------------- #
# Claude Code invocation
# --------------------------------------------------------------------------- #

_VISION_FRAME_RE = re.compile(
    r"^###\s+🔍\s+[^\n]*?`([^`]+)`\s*$", re.MULTILINE
)


def vision_frame_paths(transcript_path: Path) -> list[Path]:
    """Return safe, existing frames tagged vision-relevant in a transcript."""
    frames_dir = transcript_path.with_name(transcript_path.stem + "-frames")
    if not frames_dir.is_dir():
        return []
    try:
        text = transcript_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []

    frames_root = frames_dir.resolve()
    selected: list[Path] = []
    seen: set[Path] = set()
    for relative in _VISION_FRAME_RE.findall(text):
        candidate = (transcript_path.parent / relative).resolve()
        try:
            candidate.relative_to(frames_root)
        except ValueError:
            continue
        if (candidate.is_file()
                and candidate.suffix.lower() in {".jpg", ".jpeg", ".png"}
                and candidate not in seen):
            seen.add(candidate)
            selected.append(candidate)
    return selected

def ingest_one(transcript_path: Path, vault: Vault, model: KnowledgeModel,
               provider: str = agent_runner.DEFAULT_PROVIDER) -> dict:
    """Run one transcript through the agent (headless). Streams stdout."""
    if not agent_runner.resolve_agent_bin(provider):
        return {
            "transcript": transcript_path.name,
            "returncode": -1,
            "elapsed_seconds": 0.0,
            "output": "",
            "error": f"{provider} CLI not found on PATH",
        }
    prompt = model.ingest_prompt().format(
        transcript_name=transcript_path.name,
        wiki_rel=display_path(vault.root),
        output_rel=display_path(vault.output),
        wiki_slug=vault.slug,
        **model.prompt_format_args(),
    )

    # Tier 2: if this transcript has a `-frames/` sibling directory (from
    # `convert.py --frames`), grant the agent filesystem access. Claude
    # views JPEGs through Read and grok through its own read_file — both
    # lazily, 2-3 frames deep, which is the point (a 60-frame deep capture
    # must not be front-loaded into context). ONLY Codex needs the
    # vision-relevant JPEGs attached upfront with `codex exec --image`
    # (handled by agent_runner.run), because reading an image file gets
    # it bytes rather than pixels. The gate below is therefore about that
    # one capability gap, NOT about "every provider that isn't Claude".
    frames_dir = transcript_path.with_name(transcript_path.stem + "-frames")
    has_frames = frames_dir.is_dir() and any(frames_dir.glob("*.jpg"))
    image_paths = (vision_frame_paths(transcript_path)
                   if provider == "codex" else [])

    add_dirs: list[Path] = [vault.root, vault.output]
    if has_frames:
        add_dirs.append(frames_dir)
        print(f"  (frames available: {frames_dir.name})")
    if image_paths:
        names = ", ".join(p.name for p in image_paths)
        prompt += (
            "\n\nCodex vision note: the following 🔍 frames are attached to "
            f"this prompt as images: {names}. Inspect their pixels directly."
        )
        print(f"  (attaching {len(image_paths)} vision frame(s) to Codex)")

    def _echo(line: str) -> None:
        print(f"    {line}")
        sys.stdout.flush()

    print(f"  $ {agent_runner.CMD_LABELS[provider]} ... "
          f"(transcript: {transcript_path.name})")
    res = agent_runner.run(
        prompt,
        cwd=PROJECT_DIR,
        timeout=INGEST_TIMEOUT_S,
        add_dirs=add_dirs,
        image_paths=image_paths,
        allowed_tools="Read,Write,Edit,Glob,Grep,Bash,TodoWrite",
        on_line=_echo,
        provider=provider,
    )

    result = {
        "transcript": transcript_path.name,
        "returncode": res.returncode,
        "elapsed_seconds": res.elapsed_seconds,
        "output": res.output,
    }
    if res.error:
        result["error"] = res.error
    return result


def _review_state_file(vault: Vault) -> Path:
    return vault.state_dir / "review.json"


def load_review_state(vault: Vault) -> dict:
    """Read review counter state, returning defaults if missing/corrupt."""
    state_file = _review_state_file(vault)
    if state_file.exists():
        try:
            return json.loads(state_file.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"ingests_since_review": 0, "last_review_at": None}


def save_review_state(vault: Vault, state: dict) -> None:
    state_file = _review_state_file(vault)
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(json.dumps(state, indent=2) + "\n",
                          encoding="utf-8")


def maybe_run_review(vault: Vault, ingests_just_done: int,
                     provider: str = agent_runner.DEFAULT_PROVIDER) -> None:
    """Bump the review counter and auto-run promote_backlog.py if we've
    crossed the threshold. Resets the counter on a successful review."""
    if ingests_just_done <= 0:
        return
    state = load_review_state(vault)
    state["ingests_since_review"] = state.get("ingests_since_review", 0) + ingests_just_done

    if AUTO_REVIEW_THRESHOLD <= 0:
        save_review_state(vault, state)
        print(f"[review] auto-review disabled (AUTO_REVIEW_THRESHOLD=0). "
              f"Counter at {state['ingests_since_review']} — run "
              f"`py -3.13 wiki/scripts/promote_backlog.py --wiki {vault.slug}` "
              f"to review manually.")
        return

    if state["ingests_since_review"] < AUTO_REVIEW_THRESHOLD:
        save_review_state(vault, state)
        remaining = AUTO_REVIEW_THRESHOLD - state["ingests_since_review"]
        print(f"[review] {state['ingests_since_review']}/{AUTO_REVIEW_THRESHOLD} "
              f"ingests since last review. {remaining} more until auto-review.")
        return

    if not PROMOTE_SCRIPT.exists():
        print(f"[review] threshold reached but {PROMOTE_SCRIPT.name} not found — skipping.")
        save_review_state(vault, state)
        return

    print(f"\n[review] {state['ingests_since_review']} ingests since last review "
          f"(threshold {AUTO_REVIEW_THRESHOLD}). Running promote_backlog.py…")
    try:
        rc = subprocess.call(
            [sys.executable, str(PROMOTE_SCRIPT), "--wiki", vault.slug,
             "--provider", provider],
            cwd=str(PROJECT_DIR),
            creationflags=NO_WINDOW,
        )
    except Exception as exc:
        print(f"[review] failed to run promote_backlog.py: {exc}")
        save_review_state(vault, state)
        return

    if rc == 0:
        from datetime import datetime, timezone
        state["ingests_since_review"] = 0
        state["last_review_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        print("[review] review complete; counter reset.")
    else:
        print(f"[review] promote_backlog.py exited {rc} — counter not reset.")
    save_review_state(vault, state)


def run_obsidian_pass(vault: Vault) -> None:
    """Belt-and-braces — Claude should have run this, but enforce it here too."""
    if not OBSIDIAN_PASS.exists():
        return
    print("\nFinalizing with obsidian_pass.py…")
    proc = subprocess.run(
        [sys.executable, str(OBSIDIAN_PASS), "--wiki", vault.slug],
        stdin=subprocess.DEVNULL,
        capture_output=True, text=True,
        encoding="utf-8", errors="replace",
        cwd=str(PROJECT_DIR), timeout=120,
        creationflags=NO_WINDOW,
    )
    print(proc.stdout, end="")
    if proc.returncode != 0:
        sys.stderr.write(proc.stderr)


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Auto-ingest pending transcripts using Claude Code.")
    parser.add_argument("--dry-run", action="store_true", help="List pending transcripts and exit.")
    parser.add_argument("--limit", type=int, default=0, help="Cap how many transcripts to ingest this run (0 = all).")
    parser.add_argument("--wiki", default="wiki",
                        help="Knowledge-base slug ('wiki' = the original vault; "
                             "others live at wikis/<slug>/).")
    parser.add_argument("--reingest", nargs="+", metavar="SLUG", default=[],
                        help="Re-ingest these transcripts even though the wiki "
                             "already covers them. For when a transcript was "
                             "re-converted and the earlier version was wrong "
                             "or incomplete. The agent's re-conversion rule "
                             "applies: it UPDATES the existing page rather "
                             "than creating a duplicate.")
    parser.add_argument("--provider", default="auto",
                        choices=["auto", *agent_runner.PROVIDERS],
                        help=agent_runner.provider_arg_help(
                            "run the ingest on"))
    args = parser.parse_args(argv)

    vault = resolve_vault(args.wiki)
    if vault is None or not vault.exists():
        sys.stderr.write(f"Knowledge base '{args.wiki}' not found.\n")
        return 1
    if vault.slug != "wiki":
        print(f"Knowledge base: {vault.display_name()} ({display_path(vault.root)})")

    try:
        model = load_model_for_vault(vault)
    except (FileNotFoundError, ValueError) as exc:
        sys.stderr.write(f"ERROR: {exc}\n")
        return 1

    pending = pending_transcripts(vault, model)

    # Explicit re-ingest targets bypass pending detection, which by design
    # hides anything the wiki already covers. Without this the only way to
    # re-process a corrected transcript was to delete its wiki page first,
    # which briefly dangles every link pointing at it.
    if args.reingest:
        wanted = {s.removesuffix(".md") for s in args.reingest}
        forced, missing = [], set(wanted)
        for path in sorted(vault.output.glob("*.md")):
            if path.stem in wanted:
                forced.append(path)
                missing.discard(path.stem)
        if missing:
            sys.stderr.write(
                "ERROR: no transcript in "
                f"{display_path(vault.output)} for: {', '.join(sorted(missing))}\n")
            return 1
        already = {p.name for p in pending}
        pending = forced + [p for p in pending if p.name not in
                            {f.name for f in forced}]
        print(f"Re-ingesting {len(forced)} transcript(s) by request"
              + (f", plus {len(pending) - len(forced)} pending" if len(pending) > len(forced) else "")
              + ".")
        del already

    if not pending:
        print("No pending transcripts. Wiki is up to date.")
        return 0

    print(f"Pending: {len(pending)}")
    for p in pending:
        title = extract_transcript_title(p.read_text(encoding="utf-8", errors="replace")) or p.stem
        print(f"  - {p.name}  ({title})")
    if args.dry_run:
        return 0

    provider, pstatus = agent_runner.resolve_provider(args.provider)
    if provider is None:
        sys.stderr.write(f"\nERROR: {agent_runner.unavailable_message(pstatus)}\n")
        return 2
    print(f"\n{pstatus['display_name']} {pstatus['version']} — "
          f"logged in ({pstatus['account']})\n")

    targets = pending[: args.limit] if args.limit > 0 else pending

    # Refuse to hand an agent a video conversion with no usable transcript.
    # Such a file is valid markdown with a real title and description, so it
    # passes pending detection, and the agent will faithfully write a wiki
    # page out of the description alone. Two talks entered the wiki that way
    # before this check existed: pages that described a talk without
    # containing it. Better to skip loudly and re-convert.
    usable, rejected = [], []
    for path in targets:
        problem = _transcript.check(
            path.read_text(encoding="utf-8", errors="replace"), path.name)
        (rejected if problem else usable).append((path, problem))
    if rejected:
        print(f"\nSkipping {len(rejected)} unusable transcript(s):")
        for path, problem in rejected:
            print(f"  ! {problem}")
    targets = [p for p, _ in usable]
    if not targets:
        sys.stderr.write("\nNothing usable to ingest.\n")
        return 1

    results: list[dict] = []
    for idx, transcript_path in enumerate(targets, start=1):
        print(f"\n[{idx}/{len(targets)}] Ingesting {transcript_path.name}")
        result = ingest_one(transcript_path, vault, model, provider)
        results.append(result)
        status = "OK" if result["returncode"] == 0 else f"exit {result['returncode']}"
        print(f"  -> {status} in {result['elapsed_seconds']:.1f}s")
        if result["returncode"] != 0:
            sys.stderr.write(f"  (Last output: {result.get('output', '')[-500:]})\n")
            return 3

    run_obsidian_pass(vault)
    succeeded = sum(1 for r in results if r["returncode"] == 0)
    maybe_run_review(vault, succeeded, provider)

    print("\nDone.")
    for r in results:
        print(f"  {r['transcript']}: exit {r['returncode']} in {r['elapsed_seconds']:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
