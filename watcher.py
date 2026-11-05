"""Auto-ingest watcher — subscribed channels feed the wiki while you sleep.

Roadmap "go further #1": watch chosen YouTube channels/playlists per
knowledge base; new uploads get converted into the vault's staging
(queue-for-approval default) and, for subscriptions marked auto_ingest,
ingested unattended. Turns "tool I operate" into "knowledge that
compounds on its own".

Subscriptions live in `<vault>/.state/subscriptions.json` (state, not
repo content — gitignored with the rest of .state/). On subscribe, the
channel's latest uploads become the seen-baseline, so only videos
published AFTER subscribing are picked up — no accidental back-fill of a
10-year channel.

Module contract: importing this file needs stdlib only (server.py
imports it for subscription reads/writes). yt-dlp is imported inside the
functions that talk to YouTube — those run under the venv python
(server shells out for them, exactly like convert jobs).

CLI (run with the venv python):
    python watcher.py --wiki wiki --list --json
    python watcher.py --wiki wiki --subscribe <channel-or-playlist-url> [--auto] [--frames] --json
    python watcher.py --wiki wiki --unsubscribe <sub-id> --json
    python watcher.py --wiki wiki --check --json     # discovery only (no convert)
    python watcher.py --wiki wiki --run  [--json]    # discover + convert new videos
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

PROJECT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_DIR / "wiki" / "scripts"))
from _wikis import Vault, resolve_vault  # noqa: E402

CONVERT = PROJECT_DIR / "convert.py"
UPLOADS_PER_CHECK = 10        # newest N uploads examined per sweep
SEEN_CAP = 400                # per-subscription seen-id memory
HISTORY_CAP = 100             # vault-level capture-history memory
CONVERT_TIMEOUT_SEC = 900     # per-video convert cap
# The server kills a sweep job at 45 min. Stop STARTING conversions once a
# new one could run past this budget, so the sweep always finishes on its own
# and writes last_sweep; leftovers wait for the next sweep.
SWEEP_BUDGET_SEC = 40 * 60
# A video whose convert fails or times out this many sweeps in a row is
# marked seen and skipped. Without this, one hanging video ate the budget of
# every sweep and the newer uploads behind it never got converted.
MAX_CONVERT_ATTEMPTS = 3
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform == "win32" else 0

# Deep-visual-capture flag set — same expansion server.py uses for the UI's
# "Deep visual capture" checkbox (see CLAUDE.md "Converting a video").
FRAMES_ARGS = ["--frames", "--frame-width", "1024",
               "--dense-until", "1200", "--dense-interval", "45",
               "--max-frames", "60"]


# --------------------------------------------------------------------------- #
# Subscription store (stdlib-only — server.py calls these in-process)
# --------------------------------------------------------------------------- #

def _subs_file(vault: Vault) -> Path:
    return vault.state_dir / "subscriptions.json"


def load_subs(vault: Vault) -> dict:
    f = _subs_file(vault)
    if f.exists():
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            if isinstance(data, dict) and isinstance(data.get("subscriptions"), list):
                data.setdefault("history", [])
                return data
        except Exception:
            pass
    return {"subscriptions": [], "last_sweep": None, "history": []}


def save_subs(vault: Vault, data: dict) -> None:
    f = _subs_file(vault)
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def get_sub(data: dict, sub_id: str) -> dict | None:
    return next((s for s in data["subscriptions"] if s.get("id") == sub_id), None)


def unsubscribe(vault: Vault, sub_id: str) -> bool:
    data = load_subs(vault)
    before = len(data["subscriptions"])
    data["subscriptions"] = [s for s in data["subscriptions"]
                             if s.get("id") != sub_id]
    if len(data["subscriptions"]) == before:
        return False
    save_subs(vault, data)
    return True


def update_sub(vault: Vault, sub_id: str, *, auto_ingest: bool | None = None,
               frames: bool | None = None) -> dict | None:
    data = load_subs(vault)
    sub = get_sub(data, sub_id)
    if sub is None:
        return None
    if auto_ingest is not None:
        sub["auto_ingest"] = bool(auto_ingest)
    if frames is not None:
        sub["frames"] = bool(frames)
    save_subs(vault, data)
    return sub


# --------------------------------------------------------------------------- #
# YouTube discovery (yt-dlp — venv python only)
# --------------------------------------------------------------------------- #

def _normalize_channel_url(url: str) -> str:
    """Channel pages need /videos for a flat uploads listing; playlists and
    explicit tab URLs pass through untouched."""
    u = url.strip().rstrip("/")
    if "list=" in u or "/playlist" in u:
        return u
    if re.search(r"/(videos|streams|shorts)$", u):
        return u
    if re.search(r"(youtube\.com/(@[\w.-]+|channel/[\w-]+|c/[\w.-]+|user/[\w.-]+))$", u):
        return u + "/videos"
    return u


def channel_uploads(url: str, limit: int = UPLOADS_PER_CHECK) -> tuple[str, list[dict]]:
    """Newest `limit` uploads of a channel/playlist via a flat (no-download)
    listing. Returns (feed_title, [{id, title, url}, ...]) newest-first."""
    import yt_dlp

    opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": "in_playlist",
        "playlist_items": f"1:{limit}",
        "skip_download": True,
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(_normalize_channel_url(url), download=False)
    if info is None:
        raise RuntimeError("yt-dlp returned no info for this URL")
    title = info.get("title") or info.get("channel") or url
    out: list[dict] = []
    for e in info.get("entries") or []:
        vid = e.get("id")
        if not vid:
            continue
        out.append({
            "id": vid,
            "title": e.get("title") or vid,
            "url": e.get("url") if str(e.get("url", "")).startswith("http")
                   else f"https://www.youtube.com/watch?v={vid}",
        })
    return str(title), out


def subscribe(vault: Vault, url: str, auto_ingest: bool = False,
              frames: bool = False) -> tuple[dict | None, str]:
    """Add a subscription. The latest uploads become the seen-baseline so
    only future videos are picked up. Returns (sub, "") or (None, error)."""
    try:
        title, uploads = channel_uploads(url)
    except Exception as exc:
        return None, f"Could not read that channel/playlist: {exc}"
    if not uploads:
        return None, "That URL lists no videos (private/empty channel?)."

    data = load_subs(vault)
    sub_id = re.sub(r"[^a-z0-9@._-]+", "-",
                    _normalize_channel_url(url).split("youtube.com/")[-1].lower()
                    ).strip("-")[:80] or f"sub-{len(data['subscriptions']) + 1}"
    if get_sub(data, sub_id):
        return None, "Already subscribed to that channel in this base."

    sub = {
        "id": sub_id,
        "url": url.strip(),
        "title": title,
        "auto_ingest": bool(auto_ingest),
        "frames": bool(frames),
        "added": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "seen_ids": [u["id"] for u in uploads],   # baseline — no back-fill
        "last_check": None,
        "last_new": 0,
        "converted_total": 0,
        "last_converted": None,
    }
    data["subscriptions"].append(sub)
    save_subs(vault, data)
    return sub, ""


def _covered_video_ids(vault: Vault) -> set[str]:
    """Video ids already in the base (capture-folder pages, url + alt_url)
    or already staged in the vault's output — same identity rule as
    pending.py."""
    from ingest import existing_source_video_ids, _video_id
    from model_registry import load_model_for_vault

    try:
        capture_dir = vault.root / load_model_for_vault(vault).capture_folder()
    except Exception:
        capture_dir = vault.sources
    ids = set(existing_source_video_ids(capture_dir))
    if vault.output.exists():
        for p in vault.output.glob("*.md"):
            try:
                head = "\n".join(p.read_text(encoding="utf-8", errors="replace")
                                 .splitlines()[:30])
            except OSError:
                continue
            vid = _video_id(head)
            if vid:
                ids.add(vid)
    return ids


def discover(vault: Vault) -> list[dict]:
    """Per subscription: which of the newest uploads are NEW (not seen, not
    already covered by the base)? Pure discovery — converts nothing."""
    data = load_subs(vault)
    covered = _covered_video_ids(vault)
    findings: list[dict] = []
    for sub in data["subscriptions"]:
        try:
            _, uploads = channel_uploads(sub["url"])
        except Exception as exc:
            findings.append({"sub": sub["id"], "error": str(exc), "new": []})
            continue
        seen = set(sub.get("seen_ids") or [])
        new = [u for u in uploads if u["id"] not in seen and u["id"] not in covered]
        sub["last_check"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        sub["last_new"] = len(new)
        findings.append({"sub": sub["id"], "title": sub.get("title", ""),
                         "auto_ingest": bool(sub.get("auto_ingest")),
                         "frames": bool(sub.get("frames")), "new": new})
    save_subs(vault, data)
    return findings


def _record_converted(vault: Vault, sub_id: str, video: dict,
                      auto_ingest: bool) -> None:
    """Mark the video seen AND leave a durable audit trail: bump the
    subscription's converted_total and prepend a vault-level history
    entry. Unattended sweeps must stay accountable after the job log
    scrolls away — this is what the UI's capture counter reads."""
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    data = load_subs(vault)
    sub = get_sub(data, sub_id)
    if sub is not None:
        seen = sub.get("seen_ids") or []
        if video["id"] not in seen:
            seen.insert(0, video["id"])
        sub["seen_ids"] = seen[:SEEN_CAP]
        sub["converted_total"] = int(sub.get("converted_total") or 0) + 1
        sub["last_converted"] = now
    history = data.get("history") or []
    history.insert(0, {
        "id": video["id"],
        "title": video["title"],
        "sub": sub_id,
        "channel": (sub or {}).get("title") or sub_id,
        "at": now,
        "auto_ingest": bool(auto_ingest),
    })
    data["history"] = history[:HISTORY_CAP]
    save_subs(vault, data)


def _record_failure(vault: Vault, sub_id: str, video: dict) -> int:
    """Count a failed/timed-out convert. Returns the attempt count; at
    MAX_CONVERT_ATTEMPTS the video is marked seen so later sweeps skip it."""
    data = load_subs(vault)
    sub = get_sub(data, sub_id)
    if sub is None:
        return 0
    failures = dict(sub.get("failures") or {})
    n = int(failures.get(video["id"], 0)) + 1
    if n >= MAX_CONVERT_ATTEMPTS:
        failures.pop(video["id"], None)
        seen = sub.get("seen_ids") or []
        if video["id"] not in seen:
            seen.insert(0, video["id"])
        sub["seen_ids"] = seen[:SEEN_CAP]
    else:
        failures[video["id"]] = n
    sub["failures"] = failures
    save_subs(vault, data)
    return n


def _clear_failure(vault: Vault, sub_id: str, video_id: str) -> None:
    data = load_subs(vault)
    sub = get_sub(data, sub_id)
    if sub is not None and video_id in (sub.get("failures") or {}):
        sub["failures"].pop(video_id, None)
        save_subs(vault, data)


def _attempt_note(n: int) -> str:
    if n >= MAX_CONVERT_ATTEMPTS:
        return f" — skipped after {n} attempts"
    return f" (attempt {n} of {MAX_CONVERT_ATTEMPTS})"


def run_sweep(vault: Vault, json_mode: bool = False,
              budget_sec: float = SWEEP_BUDGET_SEC) -> dict:
    """Discover + convert every new upload into the vault's staging.
    Successful conversions are marked seen immediately (a crash mid-sweep
    never reconverts finished ones). Returns a summary; prints progress
    lines + a machine-readable tail for the server job log."""
    started = time.monotonic()
    findings = discover(vault)
    failures = {s["id"]: dict(s.get("failures") or {})
                for s in load_subs(vault)["subscriptions"]}
    converted: list[dict] = []
    errors: list[str] = []
    deferred: list[str] = []
    auto_pending = False

    for f in findings:
        if f.get("error"):
            errors.append(f"{f['sub']}: {f['error']}")
            continue
        # Previously failing videos go last, so they can't starve new ones.
        prior = failures.get(f["sub"], {})
        for video in sorted(f["new"], key=lambda v: prior.get(v["id"], 0)):
            if time.monotonic() - started + CONVERT_TIMEOUT_SEC > budget_sec:
                deferred.append(video["id"])
                continue
            cmd = [sys.executable, "-u", str(CONVERT), video["url"],
                   "--out", str(vault.output)]
            if f.get("frames"):
                cmd += FRAMES_ARGS
            print(f"[watcher] converting: {video['title']} ({video['id']})")
            try:
                proc = subprocess.run(cmd, capture_output=True, text=True,
                                      encoding="utf-8", errors="replace",
                                      timeout=CONVERT_TIMEOUT_SEC,
                                      cwd=str(PROJECT_DIR),
                                      creationflags=NO_WINDOW)
            except subprocess.TimeoutExpired:
                n = _record_failure(vault, f["sub"], video)
                errors.append(f"{video['id']}: convert timed out"
                              + _attempt_note(n))
                continue
            if proc.returncode != 0:
                n = _record_failure(vault, f["sub"], video)
                tail = (proc.stderr or proc.stdout or "").strip()[-300:]
                errors.append(f"{video['id']}: convert exit {proc.returncode} ({tail})"
                              + _attempt_note(n))
                continue
            _clear_failure(vault, f["sub"], video["id"])
            _record_converted(vault, f["sub"], video,
                              bool(f.get("auto_ingest")))
            converted.append({"id": video["id"], "title": video["title"],
                              "sub": f["sub"]})
            if f.get("auto_ingest"):
                auto_pending = True
            print(f"CONVERTED:{video['id']}:{video['title']}")

    data = load_subs(vault)
    data["last_sweep"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    save_subs(vault, data)

    summary = {
        "wiki": vault.slug,
        "checked": len(findings),
        "converted": converted,
        "errors": errors,
        "deferred": deferred,
        "auto_ingest_requested": auto_pending,
    }
    if auto_pending:
        # The server's sweep job watches for this line and queues the
        # standard ingest job (wiki lane) behind the sweep.
        print("AUTO_INGEST_REQUESTED")
    print(f"[watcher] sweep done: {len(converted)} new video(s) converted, "
          f"{len(errors)} error(s)")
    if deferred:
        print(f"[watcher] {len(deferred)} video(s) left for the next sweep "
              f"(time budget reached)")
    if json_mode:
        print(json.dumps(summary))
    return summary


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Auto-ingest watcher.")
    ap.add_argument("--wiki", default="wiki")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--subscribe", metavar="URL")
    ap.add_argument("--auto", action="store_true",
                    help="with --subscribe: ingest new videos unattended")
    ap.add_argument("--frames", action="store_true",
                    help="with --subscribe: deep visual capture on new videos")
    ap.add_argument("--unsubscribe", metavar="SUB_ID")
    ap.add_argument("--check", action="store_true",
                    help="discovery only — list new videos, convert nothing")
    ap.add_argument("--run", action="store_true",
                    help="discover + convert new videos into the vault staging")
    ap.add_argument("--json", action="store_true", dest="json_mode")
    args = ap.parse_args(argv)

    vault = resolve_vault(args.wiki)
    if vault is None or not vault.exists():
        print(f"Knowledge base '{args.wiki}' not found.", file=sys.stderr)
        return 1

    if args.subscribe:
        sub, err = subscribe(vault, args.subscribe, auto_ingest=args.auto,
                             frames=args.frames)
        if sub is None:
            print(json.dumps({"success": False, "error": err}) if args.json_mode
                  else f"Error: {err}", file=sys.stderr if not args.json_mode else sys.stdout)
            return 1
        print(json.dumps({"success": True, "subscription": sub}) if args.json_mode
              else f"Subscribed: {sub['title']} ({sub['id']}) — baseline "
                   f"{len(sub['seen_ids'])} uploads, watching for new ones.")
        return 0

    if args.unsubscribe:
        ok = unsubscribe(vault, args.unsubscribe)
        print(json.dumps({"success": ok}) if args.json_mode
              else ("Unsubscribed." if ok else "No such subscription."))
        return 0 if ok else 1

    if args.check:
        findings = discover(vault)
        if args.json_mode:
            print(json.dumps({"success": True, "findings": findings}))
        else:
            for f in findings:
                if f.get("error"):
                    print(f"  {f['sub']}: ERROR {f['error']}")
                    continue
                print(f"  {f['sub']}: {len(f['new'])} new")
                for v in f["new"]:
                    print(f"    - {v['title']} ({v['id']})")
        return 0

    if args.run:
        summary = run_sweep(vault, json_mode=args.json_mode)
        return 0 if not summary["errors"] else 0   # partial failures don't fail the sweep

    # default: --list
    data = load_subs(vault)
    print(json.dumps({"success": True, **data}) if args.json_mode
          else json.dumps(data, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
