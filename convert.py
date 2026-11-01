"""Convert a YouTube URL or local file into a Markdown file with YAML frontmatter.

Usage:
    python convert.py <input> [--out DIR] [--type {auto,url,file}]
                              [--no-frontmatter] [--overwrite]

YouTube URLs go through yt-dlp (more reliable than markitdown's bundled
youtube-transcript-api path, which YouTube currently blocks). Office documents
(docx/pptx/xlsx/odt/rtf/epub + variants) try Firecrawl's anydoc first, with
Microsoft's markitdown as the fallback (--converter picks explicitly).
Everything else goes through markitdown.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unicodedata
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, unquote, urljoin, urlparse

import local_whisper

# Shared with ingest.py so producer and consumer agree on what a usable
# source file is. Lives in wiki/scripts with the other `_`-prefixed helpers.
sys.path.insert(0, str(Path(__file__).resolve().parent / "wiki" / "scripts"))
import _transcript  # noqa: E402

DEFAULT_OUT_DIR = Path(__file__).resolve().parent / "output"

EXT_TO_TYPE = {
    ".pdf": "pdf",
    ".docx": "docx", ".doc": "docx", ".docm": "docx",
    ".pptx": "pptx", ".ppt": "pptx", ".ppsx": "pptx",
    ".xlsx": "xlsx", ".xls": "xlsx", ".xlsm": "xlsx", ".xlsb": "xlsx", ".csv": "csv",
    ".odt": "odt", ".ods": "ods", ".odp": "odp", ".rtf": "rtf",
    ".html": "html", ".htm": "html",
    ".mp3": "audio", ".wav": "audio", ".m4a": "audio", ".flac": "audio", ".ogg": "audio",
    ".png": "image", ".jpg": "image", ".jpeg": "image", ".gif": "image", ".bmp": "image", ".tiff": "image",
    ".epub": "epub",
    ".json": "json", ".xml": "xml", ".zip": "zip",
    ".txt": "text", ".md": "text",
}

# Office formats where Firecrawl's anydoc (Rust parser, firecrawl-anydoc) is
# tried before markitdown. Deliberately independent of EXT_TO_TYPE (which
# drives frontmatter `type:`, not converter choice). PDF is excluded — it has
# its own fallback chain (_convert_pdf_fallback). CSV is excluded: anydoc
# needs an explicit format hint for CSV (no content signature).
ANYDOC_EXTS = {
    ".docx", ".doc", ".docm",
    ".pptx", ".ppt", ".ppsx",
    ".xlsx", ".xls", ".xlsm", ".xlsb",
    ".odt", ".ods", ".odp",
    ".rtf", ".epub",
}

# Default-order switch for --converter auto. Flip to False if
# docs/anydoc-comparison.md concludes markitdown should stay primary; anydoc
# then only runs when markitdown fails or returns empty, or when forced.
_OFFICE_PREFER_ANYDOC = True

YOUTUBE_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be", "music.youtube.com"}

# A browser-ish UA: some publishers return a stub (or 403) to the default
# urllib agent. This only fetches the HTML we then extract locally.
_ARTICLE_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Riverfed/1.0 Safari/537.36"
)


def require_python_310() -> None:
    if sys.version_info < (3, 10):
        sys.stderr.write(
            f"Error: this script needs Python 3.10+, but is running on {sys.version.split()[0]}.\n"
            "Run with the launcher: py -3.13 convert.py <input>\n"
            "Or activate the project venv first: .\\.venv\\Scripts\\Activate.ps1\n"
        )
        sys.exit(1)


def detect_type(value: str, forced: str) -> str:
    if forced != "auto":
        return forced
    parsed = urlparse(value)
    return "url" if parsed.scheme in ("http", "https") else "file"


def is_youtube_url(value: str) -> bool:
    host = (urlparse(value).hostname or "").lower()
    return host in YOUTUBE_HOSTS


def specific_type(value: str, kind: str) -> str:
    if kind == "url":
        return "youtube" if is_youtube_url(value) else "url"
    ext = Path(value).suffix.lower()
    return EXT_TO_TYPE.get(ext, "file")


def canonical_source(value: str, kind: str) -> str:
    """Return a stable identifier for dedupe.

    YouTube URLs collapse to ``youtube:<video-id>`` regardless of which form
    (``youtu.be/X``, ``youtube.com/watch?v=X&t=10s``, ``music.youtube.com``,
    ``/shorts/X``, etc.). Other URLs are normalized to host+path+query (lower
    host, no trailing slash, no fragment). Files resolve to absolute paths.
    """
    if kind == "url":
        parsed = urlparse(value)
        host = (parsed.hostname or "").lower()
        if host in YOUTUBE_HOSTS:
            video_id: str | None = None
            if host == "youtu.be":
                video_id = parsed.path.lstrip("/").split("/")[0] or None
            else:
                qs = parse_qs(parsed.query)
                video_id = (qs.get("v") or [None])[0]
                if not video_id:
                    parts = [p for p in parsed.path.split("/") if p]
                    # /shorts/<id> or /live/<id> or /embed/<id>
                    if len(parts) >= 2 and parts[0] in ("shorts", "live", "embed", "v"):
                        video_id = parts[1]
            if video_id:
                # YouTube IDs are 11 chars of [A-Za-z0-9_-]. Strip any trailing
                # junk introduced by malformed URLs like youtu.be/ID&t=10s.
                m = re.match(r"([A-Za-z0-9_-]{11})", video_id)
                if m:
                    return f"youtube:{m.group(1)}"
            return f"url:{host}{parsed.path}"  # fallback for odd YT URLs
        path = parsed.path.rstrip("/") or "/"
        base = f"{parsed.scheme}://{host}{path}"
        return f"url:{base}?{parsed.query}" if parsed.query else f"url:{base}"
    try:
        return f"file:{Path(value).resolve()}"
    except OSError:
        return f"file:{value}"


_FRONTMATTER_SOURCE_RE = re.compile(r'^source:\s*"?(.+?)"?\s*$')


def find_duplicate(identifier: str, output_dir: Path) -> Path | None:
    """Find an existing .md in output_dir whose frontmatter source matches.

    Returns the path of the duplicate, or None if nothing matches.
    """
    if not output_dir.exists():
        return None
    for p in sorted(output_dir.glob("*.md")):
        head: list[str] = []
        try:
            with p.open("r", encoding="utf-8", errors="replace") as f:
                for i, line in enumerate(f):
                    head.append(line.rstrip("\n"))
                    if i >= 20:
                        break
        except OSError:
            continue
        if not head or head[0].strip() != "---":
            continue
        for line in head[1:]:
            if line.strip() == "---":
                break
            m = _FRONTMATTER_SOURCE_RE.match(line)
            if not m:
                continue
            source_value = m.group(1).strip()
            parsed = urlparse(source_value)
            other_kind = "url" if parsed.scheme in ("http", "https") else "file"
            if canonical_source(source_value, other_kind) == identifier:
                return p
            break
    return None


def slugify(s: str, max_len: int = 80) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = re.sub(r"[^\w\s-]", "", s).strip().lower()
    s = re.sub(r"[-\s]+", "-", s)
    s = s[:max_len].rstrip("-")
    return s or "untitled"


def collide_safe(target: Path) -> Path:
    if not target.exists():
        return target
    stem, suffix, parent = target.stem, target.suffix, target.parent
    for n in range(2, 100):
        candidate = parent / f"{stem}-{n}{suffix}"
        if not candidate.exists():
            return candidate
    return parent / f"{stem}-{int(time.time())}{suffix}"


def yaml_str(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def wrap_with_frontmatter(body: str, *, source: str, type_: str, title: str) -> str:
    converted_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    frontmatter = (
        "---\n"
        f"source: {yaml_str(source)}\n"
        f"type: {yaml_str(type_)}\n"
        f"converted_at: {yaml_str(converted_at)}\n"
        f"title: {yaml_str(title)}\n"
        "---\n\n"
    )
    return frontmatter + body.lstrip()


def warn(msg: str) -> None:
    sys.stderr.write(f"warning: {msg}\n")


def load_project_env() -> None:
    """Load missing values from the project .env for direct CLI use."""
    env_file = Path(__file__).resolve().parent / ".env"
    try:
        lines = env_file.read_text(encoding="utf-8").splitlines()
    except OSError:
        return
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        if key and key not in os.environ:
            os.environ[key] = value


# --------------------------------------------------------------------------- #
# YouTube path (via yt-dlp)
# --------------------------------------------------------------------------- #

def parse_json3(data: dict) -> str:
    """Parse Google's json3 caption format into clean prose."""
    events = data.get("events", []) or []
    chunks: list[str] = []
    for ev in events:
        segs = ev.get("segs") or []
        line = "".join(s.get("utf8", "") for s in segs).strip()
        if line:
            chunks.append(line)
    deduped: list[str] = []
    for line in chunks:
        if not deduped or deduped[-1] != line:
            deduped.append(line)
    text = " ".join(deduped)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def parse_vtt(vtt: str) -> str:
    """Strip timestamps, cue numbers, and inline tags from a WebVTT subtitle."""
    out: list[str] = []
    for raw in vtt.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith(("WEBVTT", "NOTE", "STYLE", "Kind:", "Language:")):
            continue
        if "-->" in line:
            continue
        if line.isdigit():
            continue
        line = re.sub(r"<[^>]+>", "", line)
        out.append(line)
    deduped: list[str] = []
    for line in out:
        if not deduped or deduped[-1] != line:
            deduped.append(line)
    return " ".join(deduped)


def parse_srv3(xml: str) -> str:
    """Parse YouTube's srv3 timed-text XML into clean prose."""
    root = ET.fromstring(xml)
    chunks: list[str] = []
    for paragraph in root.iter("p"):
        line = html.unescape("".join(paragraph.itertext()))
        line = re.sub(r"\s+", " ", line).strip()
        if line:
            chunks.append(line)
    deduped: list[str] = []
    for line in chunks:
        if not deduped or deduped[-1] != line:
            deduped.append(line)
    return " ".join(deduped)


CAPTION_FETCH_ATTEMPTS = 2
YTDLP_EXTRACTOR_RETRIES = 3


def fetch_subtitle_text(formats: list[dict]) -> str:
    """Fetch one caption track, trying every supported format and URL.

    Each URL gets one retry for transient network failures or empty responses.
    An exhausted format falls through to the next supported representation.
    """
    by_ext: dict[str, list[dict]] = {}
    for fmt in formats:
        ext = (fmt.get("ext") or "").lower()
        if ext in USABLE_SUB_EXTS:
            by_ext.setdefault(ext, []).append(fmt)

    # Try every format we understand, and treat an empty parse as a failure
    # rather than a result. Previously a json3 track that downloaded fine but
    # parsed to nothing was returned as-is, so the vtt fallback below never
    # ran and the video ended up with no transcript.
    for ext in ("json3", "srv3", "vtt"):
        for fmt in by_ext.get(ext, []):
            url = fmt.get("url")
            if not url:
                continue
            for attempt in range(1, CAPTION_FETCH_ATTEMPTS + 1):
                try:
                    with urllib.request.urlopen(url, timeout=20) as response:
                        raw = response.read().decode("utf-8", errors="replace")
                    if ext == "json3":
                        text = parse_json3(json.loads(raw))
                    elif ext == "srv3":
                        text = parse_srv3(raw)
                    else:
                        text = parse_vtt(raw)
                    if text.strip():
                        return text
                    warn(
                        f"{ext} subtitle parsed empty"
                        + ("; retrying" if attempt < CAPTION_FETCH_ATTEMPTS
                           else "; trying next caption source")
                    )
                except Exception as exc:
                    warn(
                        f"failed to fetch or parse {ext} subtitle "
                        f"(attempt {attempt}/{CAPTION_FETCH_ATTEMPTS}): {exc}"
                    )
                if attempt < CAPTION_FETCH_ATTEMPTS:
                    time.sleep(0.2)

    return ""


# yt-dlp reports some non-caption tracks in the `subtitles` dict. `live_chat`
# is the big one: it is the chat replay of a stream or premiere, offered only
# as ext "json", which no caption parser here understands.
NON_CAPTION_TRACKS = {"live_chat"}
# The extensions fetch_subtitle_text can actually parse.
USABLE_SUB_EXTS = {"json3", "srv3", "vtt"}


def _usable(formats: list[dict] | None) -> bool:
    """True if a track offers at least one format we can parse."""
    return bool(formats) and any(
        (f.get("ext") or "").lower() in USABLE_SUB_EXTS for f in formats)


def subtitle_candidates(
    subs: dict, auto_subs: dict
) -> list[tuple[str, str, list[dict]]]:
    """Return usable caption tracks in recovery order.

    Manual captions are attempted first, then automatic captions. Within each
    source, preferred English tracks precede any other language. Every
    candidate is known to contain a representation fetch_subtitle_text can
    parse.
    """
    preferred = ("en", "en-US", "en-GB", "en-orig")
    candidates: list[tuple[str, str, list[dict]]] = []
    for source_label, table in (("manual", subs), ("auto", auto_subs)):
        table = table or {}
        seen: set[str] = set()
        for lang in preferred:
            if _usable(table.get(lang)):
                candidates.append((lang, source_label, table[lang]))
                seen.add(lang)
        for lang, formats in table.items():
            if lang in seen or lang in NON_CAPTION_TRACKS:
                continue
            if _usable(formats):
                candidates.append((lang, source_label, formats))
    return candidates


def pick_subtitle(subs: dict, auto_subs: dict) -> tuple[str, str, list[dict]]:
    """Choose the first usable caption track.

    Kept as the small selection primitive and for callers that only need the
    preferred track. convert_youtube uses fetch_best_subtitle so a selected
    track that later fails never prevents the remaining candidates from being
    attempted.
    """
    candidates = subtitle_candidates(subs, auto_subs)
    return candidates[0] if candidates else ("", "", [])


def fetch_best_subtitle(
    subs: dict, auto_subs: dict
) -> tuple[str, str, str, int]:
    """Try every usable manual and automatic caption track.

    Returns (text, language, source_label, candidate_count). A non-zero count
    with empty text means YouTube advertised usable tracks but every supported
    fetch and parse path failed.
    """
    candidates = subtitle_candidates(subs, auto_subs)
    for lang, source_label, formats in candidates:
        text = fetch_subtitle_text(formats)
        if text.strip():
            return text, lang, source_label, len(candidates)
        warn(
            f"{source_label} caption track {lang!r} failed; "
            "trying the next advertised caption track"
        )
    return "", "", "", len(candidates)


def format_youtube_date(yyyymmdd: str | None) -> str:
    if not yyyymmdd or len(yyyymmdd) != 8:
        return ""
    return f"{yyyymmdd[:4]}-{yyyymmdd[4:6]}-{yyyymmdd[6:]}"


# --------------------------------------------------------------------------- #
# Frame extraction + on-screen text (Tier 2)
# --------------------------------------------------------------------------- #

# Tesseract isn't always on PATH even when installed — winget (Windows) and
# Homebrew (macOS) both use well-known locations; fall back to those.
_TESSERACT_FALLBACKS = (
    Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe"),  # winget
    Path("/opt/homebrew/bin/tesseract"),                    # Homebrew, Apple Silicon
    Path("/usr/local/bin/tesseract"),                       # Homebrew, Intel
)


def _resolve_tesseract() -> bool:
    """Configure pytesseract to find the Tesseract binary. Returns True if
    OCR is available."""
    try:
        import pytesseract
    except ImportError:
        return False
    cmd = pytesseract.pytesseract.tesseract_cmd
    if shutil.which(cmd):
        return True
    for candidate in _TESSERACT_FALLBACKS:
        if candidate.exists():
            pytesseract.pytesseract.tesseract_cmd = str(candidate)
            return True
    return False


def _resolve_ffmpeg() -> str | None:
    """Find an ffmpeg binary — system PATH first, then the one bundled by
    the imageio-ffmpeg pip package."""
    via_path = shutil.which("ffmpeg")
    if via_path:
        return via_path
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


def _hms(seconds: float | int) -> str:
    s = int(round(float(seconds)))
    h, rem = divmod(s, 3600)
    m, ss = divmod(rem, 60)
    return f"{h:d}:{m:02d}:{ss:02d}" if h else f"{m:02d}:{ss:02d}"


def _pick_frame_timestamps(
    duration: float,
    chapters: list[dict] | None,
    *,
    max_frames: int = 30,
    dense_until: float = 0,
    dense_interval: float = 30,
) -> list[tuple[float, str]]:
    """Choose ≤max_frames timestamps to extract frames at.

    Returns a list of (timestamp_seconds, source) tuples where `source`
    is one of "dense" | "chapter" | "uniform". The source is used
    downstream to auto-flag dense-sampled frames as vision_relevant
    (whole point of dense sampling: trust the timestamp, not the OCR).

    Strategy:
    - If `dense_until > 0`: sample every `dense_interval` seconds from 0
      up to `dense_until` (good for videos where the first stretch has
      diagrams that get progressively populated — chapter-start frames
      alone catch the blank canvas).
    - Then: chapter-start timestamps (filtered to AFTER dense_until)
      added on top, with a final midpoint between the last chapter and
      the end for the wrap-up.
    - Falls back to uniform sampling when chapters are missing.
    - Final list is sorted + deduped + capped at `max_frames`.
    """
    if duration <= 0:
        return []

    selected: list[tuple[float, str]] = []

    # Dense head sampling for the early window
    if dense_until > 0:
        t = 0.0
        while t <= min(dense_until, duration):
            selected.append((t, "dense"))
            t += max(5.0, dense_interval)

    if chapters:
        starts = [float(c.get("start_time") or 0) for c in chapters
                  if c.get("start_time") is not None]
        # Drop chapters that fall inside the dense window — they're
        # already covered by the dense pass.
        starts = [s for s in starts if s > dense_until]
        # Add a midpoint between the last chapter and the end
        if starts and starts[-1] < duration - 30:
            starts.append((starts[-1] + duration) / 2)
        selected.extend((s, "chapter") for s in starts)
    elif not selected:
        # No chapters AND no dense pass — uniform sampling
        if duration < 60:        n = 8
        elif duration < 300:     n = 12
        elif duration < 900:     n = 18
        elif duration < 2700:    n = 24
        else:                    n = 30
        selected = [(duration * (i + 0.5) / n, "uniform") for i in range(n)]

    # Ensure 0.0 is in there if we have any frames at all
    if selected and not any(abs(t) < 0.5 for t, _ in selected):
        selected = [(0.0, "dense" if dense_until > 0 else "chapter")] + selected

    # Sort + dedupe (within 1s — keep first occurrence so dense wins)
    seen: set[float] = set()
    deduped: list[tuple[float, str]] = []
    for t, src in sorted(selected, key=lambda x: x[0]):
        key = round(t, 1)
        if key not in seen:
            seen.add(key)
            deduped.append((key, src))
    selected = deduped

    # Cap at max_frames, decimating evenly if over
    if len(selected) > max_frames:
        step = len(selected) / max_frames
        selected = [selected[int(i * step)] for i in range(max_frames)]
    return selected


FRAME_DOWNLOAD_ATTEMPTS = 3


def _download_video_for_frames(url: str, tmp_dir: Path) -> Path | None:
    """Download a fresh video URL, retrying transient YouTube 403s."""
    try:
        import yt_dlp
    except ImportError as exc:
        warn(f"frame download unavailable ({exc})")
        return None

    last_error: Exception | None = None
    for attempt in range(1, FRAME_DOWNLOAD_ATTEMPTS + 1):
        ydl_opts = {
            "format": "best[height<=720]/best",
            "quiet": True,
            "no_warnings": True,
            "outtmpl": str(tmp_dir / f"video-{attempt}.%(ext)s"),
            "noplaylist": True,
            "extractor_retries": 3,
            "retries": 10,
            "fragment_retries": 10,
        }
        try:
            # Recreate YoutubeDL and re-extract metadata on every attempt so
            # a retry receives a fresh signed media URL instead of replaying
            # the same expired/blocked URL that returned HTTP 403.
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                video_path = Path(ydl.prepare_filename(info))
            if video_path.is_file():
                return video_path
            last_error = RuntimeError("download produced no file")
        except Exception as exc:
            last_error = exc
        if attempt < FRAME_DOWNLOAD_ATTEMPTS:
            warn(
                f"frame download attempt {attempt}/{FRAME_DOWNLOAD_ATTEMPTS} "
                f"failed ({last_error}); retrying with a fresh media URL"
            )

    warn(
        f"frame download failed after {FRAME_DOWNLOAD_ATTEMPTS} attempts: "
        f"{last_error}"
    )
    return None


def extract_frames_and_ocr(
    *, url: str, slug: str, duration: float, chapters: list[dict] | None,
    out_dir: Path, max_width: int = 512,
    max_frames: int = 30, dense_until: float = 0, dense_interval: float = 30,
) -> list[dict]:
    """Download the video, extract frames at chosen timestamps, OCR each one.

    Returns a list of dicts: {timestamp_s, timestamp_label, frame_path,
    ocr_text, ocr_chars, vision_relevant}. Empty list if extraction fails.
    """
    ffmpeg = _resolve_ffmpeg()
    if not ffmpeg:
        warn("frame extraction skipped — ffmpeg not available (pip install imageio-ffmpeg).")
        return []

    timestamps_with_source = _pick_frame_timestamps(
        duration, chapters,
        max_frames=max_frames, dense_until=dense_until,
        dense_interval=dense_interval,
    )
    if not timestamps_with_source:
        warn("no frame timestamps could be chosen (duration unknown).")
        return []
    timestamps = [t for t, _ in timestamps_with_source]
    sources = {round(t, 1): src for t, src in timestamps_with_source}

    frames_dir = out_dir / f"{slug}-frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    # Download to a temp file first — frame extraction needs a local source
    import tempfile
    tmp_dir = Path(tempfile.mkdtemp(prefix="convert-frames-"))
    video_path: Path | None = None
    try:
        video_path = _download_video_for_frames(url, tmp_dir)
        if video_path is None:
            return []

        # Extract each frame via a single ffmpeg call per timestamp.
        # Using `-ss <t> -i video -frames:v 1` is fast (seeks before decoding).
        results: list[dict] = []
        for idx, t in enumerate(timestamps, start=1):
            label = _hms(t)
            frame_name = f"frame_{idx:03d}_t{label.replace(':', '-')}.jpg"
            frame_path = frames_dir / frame_name
            cmd = [
                ffmpeg, "-y", "-ss", str(t), "-i", str(video_path),
                "-frames:v", "1",
                "-vf", f"scale={max_width}:-2",
                "-q:v", "3",       # JPEG quality (1-31, lower = better)
                str(frame_path),
            ]
            try:
                subprocess.run(
                    cmd, check=True,
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform == "win32" else 0,
                )
            except subprocess.CalledProcessError:
                continue
            if not frame_path.exists():
                continue
            results.append({
                "timestamp_s": t,
                "timestamp_label": label,
                "frame_path": frame_path,
                "source": sources.get(round(t, 1), "chapter"),
                "ocr_text": "",
                "ocr_chars": 0,
                "vision_relevant": False,
            })

        # OCR pass — local, free
        ocr_available = _resolve_tesseract()
        if ocr_available:
            import pytesseract
            from PIL import Image
            for r in results:
                try:
                    img = Image.open(r["frame_path"])
                    text = pytesseract.image_to_string(img, lang="eng").strip()
                except Exception:
                    text = ""
                # Collapse whitespace, drop near-empty / OCR-noise lines
                lines = [ln.strip() for ln in text.splitlines() if len(ln.strip()) >= 3]
                clean = "\n".join(lines)
                r["ocr_text"] = clean
                r["ocr_chars"] = len(clean)
                # Vision-relevant heuristic: ≥50 chars of OCR text = likely a
                # slide / code / dashboard / terminal. We also auto-flag dense-
                # sampled frames: user explicitly asked for that window, and
                # hand-drawn diagrams (Excalidraw, whiteboards) often OCR to
                # gibberish but are exactly what we want vision to read.
                r["vision_relevant"] = (
                    r["ocr_chars"] >= 50 or r["source"] == "dense"
                )
        else:
            warn("Tesseract OCR not available — frames extracted but on-screen text not captured. "
                 "Install via `winget install UB-Mannheim.TesseractOCR`.")
            # Still flag dense frames so vision-on-demand picks them up
            # even without OCR — the user-supplied dense window is the
            # "expect visual content here" signal.
            for r in results:
                r["vision_relevant"] = r["source"] == "dense"

        return results
    finally:
        # Always clean downloads and partials; extracted frames stay.
        shutil.rmtree(tmp_dir, ignore_errors=True)


def render_visual_content_section(frames: list[dict], slug: str) -> str:
    """Format the Visual content section that gets appended to the .md."""
    if not frames:
        return ""
    with_text = [f for f in frames if f["ocr_chars"] > 0]
    vision_count = sum(1 for f in frames if f["vision_relevant"])
    talking_head = with_text and (len(with_text) < max(2, len(frames) // 10))

    out: list[str] = ["## Visual content", ""]
    out.append(
        f"_{len(frames)} frames extracted, "
        f"{len(with_text)} have on-screen text "
        f"({vision_count} flagged vision-relevant)._"
    )
    if talking_head:
        out.append("")
        out.append("_Mostly talking-head footage — on-screen text is sparse, audio transcript above is the primary content._")
    out.append("")
    for f in frames:
        rel = Path(f["frame_path"]).relative_to(Path(f["frame_path"]).parent.parent).as_posix()
        marker = "🔍" if f["vision_relevant"] else "·"
        out.append(f"### {marker} t={f['timestamp_label']}  `{rel}`")
        out.append("")
        if f["ocr_text"]:
            for line in f["ocr_text"].splitlines():
                out.append(f"> {line}")
        else:
            out.append("> _(no on-screen text)_")
        out.append("")
    return "\n".join(out)


def _download_audio_for_transcription(url: str, target_dir: Path) -> Path | None:
    """Download the smallest practical YouTube audio stream with progress."""
    try:
        import yt_dlp
    except ImportError as exc:
        warn(f"audio transcription unavailable ({exc})")
        return None

    last_percent = -10

    def progress(data: dict) -> None:
        nonlocal last_percent
        if data.get("status") != "downloading":
            return
        downloaded = int(data.get("downloaded_bytes") or 0)
        total = int(
            data.get("total_bytes") or data.get("total_bytes_estimate") or 0
        )
        if not total:
            return
        percent = int(downloaded * 100 / total)
        if percent >= last_percent + 10:
            print(
                f"  audio download: {min(percent, 100)}% "
                f"({downloaded / (1024 * 1024):.1f} MiB)",
                file=sys.stderr,
            )
            last_percent = percent

    print("  audio transcription: downloading source audio", file=sys.stderr)
    ydl_opts = {
        "format": "worstaudio[ext=m4a]/worstaudio/bestaudio",
        "outtmpl": str(target_dir / "audio.%(ext)s"),
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "noplaylist": True,
        "extractor_retries": YTDLP_EXTRACTOR_RETRIES,
        "retries": 10,
        "progress_hooks": [progress],
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except Exception as exc:
        warn(f"audio download failed: {exc}")
        return None
    audio_files = [
        path for path in target_dir.iterdir()
        if path.is_file() and path.stem == "audio"
    ]
    if not audio_files:
        warn("audio download produced no file")
        return None
    audio = audio_files[0]
    print(
        f"  audio download complete: {audio.stat().st_size / (1024 * 1024):.1f} MiB",
        file=sys.stderr,
    )
    return audio


def whisper_transcribe_locally(
    url: str,
) -> local_whisper.LocalTranscript | None:
    """Transcribe with the configured local whisper.cpp binary and model."""
    try:
        model_name = local_whisper.selected_model_name()
        ready, reason = local_whisper.readiness(model_name)
    except (OSError, RuntimeError, ValueError) as exc:
        warn(f"local Whisper configuration failed: {exc}")
        return None
    if not ready:
        warn(f"local Whisper unavailable: {reason}")
        return None

    tmpdir = Path(tempfile.mkdtemp(prefix="riverfed-local-whisper-"))
    try:
        audio = _download_audio_for_transcription(url, tmpdir)
        if audio is None:
            return None
        ffmpeg = _resolve_ffmpeg()
        if not ffmpeg:
            warn(
                "local Whisper cannot prepare audio because ffmpeg is missing; "
                "re-run ./setup.sh"
            )
            return None
        wav_path = tmpdir / "audio-16khz-mono.wav"
        print(
            "  local Whisper: converting audio to 16 kHz mono WAV",
            file=sys.stderr,
        )
        proc = subprocess.run(
            [
                ffmpeg,
                "-y",
                "-hide_banner",
                "-loglevel", "error",
                "-i", str(audio),
                "-ar", "16000",
                "-ac", "1",
                "-c:a", "pcm_s16le",
                str(wav_path),
            ],
            capture_output=True,
            text=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
            if sys.platform == "win32" else 0,
        )
        if proc.returncode != 0 or not wav_path.is_file():
            detail = (proc.stderr or "").strip()[:300]
            warn(f"local Whisper audio conversion failed: {detail}")
            return None
        result = local_whisper.transcribe_wav(
            wav_path,
            model_name=model_name,
            output_dir=tmpdir / "result",
        )
        if result is None:
            warn("local Whisper completed but returned no speech")
        return result
    except (OSError, RuntimeError, ValueError) as exc:
        warn(f"local Whisper failed: {exc}")
        return None
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def whisper_transcribe_via_groq(url: str) -> str:
    """Remote fallback (Track B4), used only after local Whisper.

    Groq is gated on GROQ_API_KEY. Without the key this returns an empty
    string and the caller preserves the best local or caption transcript.

    Groq caps uploads at ~25 MB, so long videos are segmented with the
    bundled imageio-ffmpeg binary (stream-copy, no re-encode) and the
    pieces are transcribed in order."""
    api_key = (os.environ.get("GROQ_API_KEY") or "").strip()
    if not api_key:
        return ""

    try:
        import requests
    except ImportError as exc:
        warn(f"Groq Whisper unavailable ({exc})")
        return ""

    tmpdir = Path(tempfile.mkdtemp(prefix="riverfed-groq-whisper-"))
    try:
        print(
            "  local Whisper did not produce a complete transcript; "
            "trying optional Groq fallback",
            file=sys.stderr,
        )
        audio = _download_audio_for_transcription(url, tmpdir)
        if audio is None:
            return ""

        # Segment if over Groq's upload cap (24 MB to leave headroom).
        pieces: list[Path] = [audio]
        if audio.stat().st_size > 24 * 1024 * 1024:
            try:
                import imageio_ffmpeg
                ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
            except ImportError:
                warn(
                    "Groq Whisper audio exceeds 24 MB and imageio-ffmpeg "
                    "is missing"
                )
                return ""
            seg_pattern = tmpdir / f"seg%03d{audio.suffix}"
            proc = subprocess.run(
                [ffmpeg, "-hide_banner", "-loglevel", "error",
                 "-i", str(audio), "-f", "segment", "-segment_time", "1200",
                 "-c", "copy", str(seg_pattern)],
                capture_output=True, text=True,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
                if sys.platform == "win32" else 0,
            )
            segs = sorted(tmpdir.glob(f"seg*{audio.suffix}"))
            if proc.returncode != 0 or not segs:
                warn(f"Groq Whisper ffmpeg segmenting failed "
                     f"({proc.stderr.strip()[:200]})")
                return ""
            pieces = segs

        texts: list[str] = []
        for i, piece in enumerate(pieces, start=1):
            if len(pieces) > 1:
                print(
                    f"  Groq Whisper: transcribing segment {i}/{len(pieces)}",
                    file=sys.stderr,
                )
            with piece.open("rb") as fh:
                resp = requests.post(
                    "https://api.groq.com/openai/v1/audio/transcriptions",
                    headers={"Authorization": f"Bearer {api_key}"},
                    files={"file": (piece.name, fh)},
                    data={"model": "whisper-large-v3-turbo",
                          "response_format": "text"},
                    timeout=600,
                )
            if resp.status_code != 200:
                warn(f"Groq Whisper returned {resp.status_code} "
                     f"({resp.text[:200]})")
                return ""
            texts.append(resp.text.strip())
        return "\n".join(t for t in texts if t).strip()
    except Exception as exc:
        warn(f"Groq Whisper failed: {exc}")
        return ""
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def convert_youtube(url: str) -> tuple[str, str, dict]:
    """Run yt-dlp on a YouTube URL. Returns (markdown_body, title, info_dict).
    The info_dict carries the chapters + duration we need for frame extraction."""
    try:
        import yt_dlp
    except ImportError:
        sys.stderr.write(
            "Error: yt-dlp is not installed. From this folder run:\n"
            "  .\\.venv\\Scripts\\python.exe -m pip install -r requirements.txt\n"
        )
        sys.exit(2)

    ydl_opts = {
        "skip_download": True,
        "quiet": True,
        "no_warnings": True,
        "extractor_retries": YTDLP_EXTRACTOR_RETRIES,
        "writesubtitles": True,
        "writeautomaticsub": True,
        "subtitleslangs": ["en.*", "en"],
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as exc:
        sys.stderr.write(f"Error: yt-dlp failed to fetch {url}\n  {exc}\n")
        sys.exit(2)

    if info is None:
        sys.stderr.write("Error: yt-dlp returned no info for this URL.\n")
        sys.exit(2)

    title = info.get("title") or "Untitled"
    description = (info.get("description") or "").strip()
    uploader = info.get("uploader") or info.get("channel") or ""
    duration_s = info.get("duration") or 0
    duration_str = info.get("duration_string") or (
        f"{duration_s // 60}:{duration_s % 60:02d}" if duration_s else ""
    )
    upload_date = format_youtube_date(info.get("upload_date"))
    video_id = info.get("id") or ""
    webpage_url = info.get("webpage_url") or url
    view_count = info.get("view_count")
    like_count = info.get("like_count")

    subs = info.get("subtitles") or {}
    auto_subs = info.get("automatic_captions") or {}
    transcript, lang, src_label, caption_candidates = fetch_best_subtitle(
        subs, auto_subs
    )
    transcript_note = ""

    # A very short caption result is commonly a partial fetch. Give the audio
    # fallback a chance before the shared transcript guard rejects it. If the
    # video itself is short, Whisper may also stay under the floor; the guard
    # remains intentionally conservative and reports the measured word count.
    caption_words = len(transcript.split())
    transcript_floor = _transcript.minimum_words(duration_s)
    needs_audio_fallback = (
        not transcript or caption_words < transcript_floor
    )
    if needs_audio_fallback:
        if transcript:
            warn(
                f"caption transcript is only {caption_words} words; "
                "trying the audio transcription fallback"
            )
        elif caption_candidates:
            warn(
                f"{caption_candidates} usable caption track(s) were advertised "
                "but every fetch/parse path failed; trying audio transcription"
            )
        else:
            warn(
                "YouTube advertised no usable caption track; "
                "trying audio transcription"
            )

        local_result = whisper_transcribe_locally(webpage_url)
        best_words = caption_words
        if local_result is not None:
            local_words = local_whisper.content_word_count(local_result.text)
            if local_words > best_words:
                transcript = local_result.text
                lang = local_result.language
                src_label = "whisper-local"
                best_words = local_words
                transcript_note = (
                    f"_Transcribed locally with {local_result.engine} "
                    f"{local_result.engine_version}, model "
                    f"`{local_result.model}`, language "
                    f"`{local_result.language or 'auto'}`, "
                    f"{local_result.segment_count} timestamped segments. "
                    "Audio stayed on this machine._"
                )

        if best_words < transcript_floor:
            audio_transcript = whisper_transcribe_via_groq(webpage_url)
        else:
            audio_transcript = ""
        if len(audio_transcript.split()) > best_words:
            transcript = audio_transcript
            lang = ""
            src_label = "whisper-groq"
            transcript_note = (
                "_Transcribed remotely with Groq "
                "`whisper-large-v3-turbo` after local recovery did not "
                "produce a complete transcript._"
            )
        elif (
            best_words < transcript_floor
            and not (os.environ.get("GROQ_API_KEY") or "").strip()
        ):
            warn(
                "optional remote Groq fallback was not attempted because "
                "GROQ_API_KEY is not configured"
            )
        elif (
            best_words < transcript_floor
            and not audio_transcript
        ):
            warn("optional remote Groq fallback was attempted but failed")

    parts: list[str] = [f"# {title}", ""]
    meta: list[str] = []
    if uploader:
        meta.append(f"- **Channel:** {uploader}")
    if duration_str:
        meta.append(f"- **Duration:** {duration_str}")
    if upload_date:
        meta.append(f"- **Published:** {upload_date}")
    if video_id:
        meta.append(f"- **Video ID:** `{video_id}`")
    if view_count:
        meta.append(f"- **Views:** {view_count:,}")
    if like_count:
        meta.append(f"- **Likes:** {like_count:,}")
    meta.append(f"- **URL:** <{webpage_url}>")
    if meta:
        parts.append("## Metadata")
        parts.append("")
        parts.extend(meta)
        parts.append("")

    if description:
        parts.append("## Description")
        parts.append("")
        parts.append(description)
        parts.append("")

    if transcript:
        if src_label == "manual":
            label = "Transcript"
        elif src_label == "whisper-local":
            language_label = f", {lang}" if lang else ""
            label = f"Transcript (local Whisper{language_label})"
        elif src_label == "whisper-groq":
            label = "Transcript (Whisper via Groq)"
        else:
            label = f"Transcript (auto-generated, {lang})"
        parts.append(f"## {label}")
        parts.append("")
        if transcript_note:
            parts.append(transcript_note)
            parts.append("")
        parts.append(transcript)
        parts.append("")

    return "\n".join(parts), title, info


# --------------------------------------------------------------------------- #
# File / non-YouTube URL path (via markitdown)
# --------------------------------------------------------------------------- #

def extract_title_from_md(md: str, source: str, kind: str) -> str:
    lines = md.splitlines()
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
    if kind == "url":
        return urlparse(source).path.strip("/") or urlparse(source).netloc or "untitled"
    return Path(source).stem or "untitled"


def _convert_pdf_fallback(pdf_path: Path) -> tuple[str, str] | None:
    """Try alternative parsers when markitdown fails (or returns empty) on a
    PDF. Returns (markdown_text, method_name) on first success, or None if
    every strategy fails.

    The chain — fastest/cheapest first, OCR last:

      1. pdfplumber — wraps pdfminer but recovers from many malformed xref
         tables that throw PSEOF in pure pdfminer.
      2. pypdfium2 — Google's pdfium binding. Very robust to truncated /
         non-standard PDFs; handles most encrypted PDFs with empty password.
      3. pypdfium2 (rasterize) + pytesseract (OCR) — for scanned / image-only
         PDFs that have no text layer at all. Slow (~1-3s/page) but the only
         option for true scans. Skipped if Tesseract isn't installed."""
    # Silence pdfminer's chatty "Could not get FontBBox" / similar logging
    # so the user's conversion-status box isn't noisy on a successful parse.
    import logging
    logging.getLogger("pdfminer").setLevel(logging.ERROR)

    # 1) pdfplumber
    try:
        import pdfplumber
        with pdfplumber.open(str(pdf_path)) as pdf:
            chunks: list[str] = []
            for page in pdf.pages:
                t = (page.extract_text() or "").strip()
                if t:
                    chunks.append(t)
        if chunks:
            return "\n\n".join(chunks), "pdfplumber"
    except Exception as exc:
        sys.stderr.write(f"[convert] pdfplumber fallback failed: {exc}\n")

    # 2) pypdfium2 text extraction
    try:
        import pypdfium2 as pdfium  # type: ignore
        doc = pdfium.PdfDocument(str(pdf_path))
        try:
            chunks = []
            for page in doc:
                try:
                    tp = page.get_textpage()
                    t = (tp.get_text_range() or "").strip()
                    tp.close()
                finally:
                    page.close()
                if t:
                    chunks.append(t)
        finally:
            doc.close()
        if chunks:
            return "\n\n".join(chunks), "pypdfium2"
    except Exception as exc:
        sys.stderr.write(f"[convert] pypdfium2 fallback failed: {exc}\n")

    # 3) pypdfium2 rasterise + Tesseract OCR (scanned PDFs)
    try:
        import pypdfium2 as pdfium  # type: ignore
        import pytesseract  # type: ignore
        # Probe for the binary; pytesseract raises if not installed.
        pytesseract.get_tesseract_version()
        doc = pdfium.PdfDocument(str(pdf_path))
        try:
            chunks = []
            for page in doc:
                try:
                    pil = page.render(scale=2).to_pil()
                    t = (pytesseract.image_to_string(pil) or "").strip()
                finally:
                    page.close()
                if t:
                    chunks.append(t)
        finally:
            doc.close()
        if chunks:
            return "\n\n".join(chunks), "pypdfium2 + Tesseract OCR"
    except Exception as exc:
        sys.stderr.write(f"[convert] OCR fallback unavailable: {exc}\n")

    return None


def _anydoc_available() -> bool:
    import importlib.util
    return importlib.util.find_spec("anydoc") is not None


def _convert_office_anydoc(path: Path) -> tuple[str, str] | None:
    """Convert an office document via Firecrawl's anydoc (firecrawl-anydoc,
    a Rust document parser). Returns (markdown_text, "anydoc"), or None when
    the package is missing (silent — it's optional), the parse fails, or the
    output is empty — the caller falls through to markitdown either way."""
    try:
        import anydoc  # firecrawl-anydoc — optional dependency
    except ImportError:
        return None
    try:
        text = anydoc.to_markdown(str(path))
    except Exception as exc:
        sys.stderr.write(f"[convert] anydoc failed: {exc}\n")
        return None
    if not (text or "").strip():
        # e.g. Marp-exported decks: slides are flattened images, no text
        # shapes — nothing to extract. Leave a trace so "why didn't anydoc
        # handle my file" is answerable from the job log.
        sys.stderr.write("[convert] anydoc found no text in this document\n")
        return None
    return text, "anydoc"


def fetch_url_html(url: str) -> str | None:
    """Fetch a web page's raw HTML. Returns None (with a warning) on any
    network/decoding failure so the caller can fall back to markitdown."""
    req = urllib.request.Request(url, headers={"User-Agent": _ARTICLE_USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read()
            charset = r.headers.get_content_charset() or "utf-8"
    except Exception as exc:
        sys.stderr.write(f"[convert] could not fetch {url}: {exc}\n")
        return None
    try:
        return raw.decode(charset, "replace")
    except (LookupError, UnicodeDecodeError):
        return raw.decode("utf-8", "replace")


def _absolutize_links(html_fragment: str, base_url: str) -> str:
    """Rewrite relative href/src in an HTML fragment to absolute URLs so the
    ingested page's links still resolve once it lives in the wiki."""
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        return html_fragment
    soup = BeautifulSoup(html_fragment, "lxml")
    for el in soup.find_all("a"):
        v = el.get("href")
        if v and not v.startswith(
            ("http://", "https://", "data:", "mailto:", "tel:", "#")
        ):
            el["href"] = urljoin(base_url, v)
    # Images an extractor keeps inline get the same cleanup the appended
    # figures get: absolutize AND unwrap proxy URLs, so no raw `/_next/image`
    # resizer links survive in the body.
    for el in soup.find_all("img"):
        v = el.get("src")
        if v and not v.startswith("data:"):
            el["src"] = _unproxy_image_url(v, base_url)
    return str(soup)


def _unproxy_image_url(src: str, base_url: str) -> str:
    """Resolve an <img> src to a real absolute URL. Unwraps Next.js image
    proxy links (`/_next/image?url=<encoded>&w=...`) to the underlying file so
    the ingested figure points at the real asset, not a resizer endpoint."""
    absolute = urljoin(base_url, src)
    parsed = urlparse(absolute)
    if parsed.path.endswith("/_next/image"):
        inner = parse_qs(parsed.query).get("url", [None])[0]
        if inner:
            return urljoin(base_url, unquote(inner))
    return absolute


def _collect_content_images(html: str, base_url: str) -> list[tuple[str, str]]:
    """Pull the article's content images as ``(url, alt)`` from the raw page
    HTML — readability drops these, but for many pieces the figures (and their
    alt text) are the point. Site chrome (header/nav/footer/aside) and SVG
    logos are excluded, proxy URLs are unwrapped, and duplicates removed."""
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        return []
    soup = BeautifulSoup(html, "lxml")
    for chrome in soup.find_all(["header", "nav", "footer", "aside"]):
        chrome.decompose()
    out: list[tuple[str, str]] = []
    seen: set[str] = set()
    for im in soup.find_all("img"):
        src = im.get("src") or im.get("data-src") or ""
        if not src:
            srcset = im.get("srcset") or ""
            if srcset:  # take the last (usually highest-res) candidate
                src = srcset.split(",")[-1].strip().split(" ")[0]
        if not src:
            continue
        img_url = _unproxy_image_url(src, base_url)
        low = img_url.lower()
        if (low.endswith(".svg") or img_url.startswith("data:")
                or not img_url.startswith(("http://", "https://"))):
            continue
        if img_url in seen:
            continue
        seen.add(img_url)
        out.append((img_url, (im.get("alt") or "").strip()))
    return out


def extract_article_markdown(html: str, url: str) -> tuple[str, str] | None:
    """Isolate the main article from a page's HTML and return
    ``(markdown_body, title)``, or None if extraction is unavailable or the
    result is too thin to trust (caller then falls back to full-page
    markitdown).

    Two-stage on purpose: readability-lxml strips the boilerplate (nav,
    sidebars, footers, cookie bars) and hands back just the article's HTML;
    markitdown then renders THAT to Markdown, which preserves the heading
    structure and inline formatting that a whole-page conversion buries in
    chrome. Relative links are absolutized in between."""
    try:
        from readability import Document
    except ImportError:
        return None
    try:
        doc = Document(html)
        title = (doc.short_title() or "").strip()
        content_html = doc.summary(html_partial=True)
    except Exception as exc:
        sys.stderr.write(f"[convert] readability extraction failed: {exc}\n")
        return None
    if not content_html or not content_html.strip():
        return None
    content_html = _absolutize_links(content_html, url)

    tmp = tempfile.NamedTemporaryFile(
        "w", suffix=".html", delete=False, encoding="utf-8"
    )
    try:
        tmp.write(content_html)
        tmp.close()
        from markitdown import MarkItDown
        body = (MarkItDown(enable_plugins=False).convert(tmp.name).text_content or "").strip()
    except Exception as exc:
        sys.stderr.write(f"[convert] markitdown failed on extracted article: {exc}\n")
        return None
    finally:
        try:
            Path(tmp.name).unlink()
        except OSError:
            pass

    # Readability occasionally over-strips a JS-rendered page down to a stub.
    # Below a floor, decline so the caller falls back to full-page markitdown.
    if len(body) < 200:
        return None

    # Readability strips images; re-attach the article's figures (which it
    # dropped) as a Figures section, keeping their alt text. Appended rather
    # than positioned inline: reliable, and the alt captions carry the meaning.
    images = [im for im in _collect_content_images(html, url) if im[0] not in body]
    if images:
        figs = ["## Figures", ""]
        for i, (img_url, alt) in enumerate(images, 1):
            figs.append(f"![{alt or f'Figure {i}'}]({img_url})")
            figs.append("")
        body = body.rstrip() + "\n\n" + "\n".join(figs).rstrip() + "\n"

    return body, title


def convert_url_article(url: str) -> tuple[str, str] | None:
    """Fetch + extract a readable article for a non-YouTube URL. Returns
    ``(markdown_body, title)`` or None to signal 'fall back to markitdown'."""
    html = fetch_url_html(url)
    if html is None:
        return None
    return extract_article_markdown(html, url)


def convert_with_markitdown(input_value: str, converter: str = "auto") -> str:
    import warnings
    warnings.filterwarnings(
        "ignore",
        message="Couldn't find ffmpeg or avconv.*",
        category=RuntimeWarning,
        module="pydub.utils",
    )

    office_path: Path | None = None
    try:
        candidate = Path(input_value)
        if candidate.is_file() and candidate.suffix.lower() in ANYDOC_EXTS:
            office_path = candidate
    except (OSError, ValueError):
        office_path = None

    # Explicit --converter anydoc hard-fails rather than silently falling
    # back — same policy as an explicit --provider pick in agent_runner.py.
    if converter == "anydoc":
        if office_path is None:
            sys.stderr.write(
                "Error: --converter anydoc only handles office documents "
                "(docx/pptx/xlsx/odt/rtf/epub and variants), not this input.\n")
            sys.exit(2)
        if not _anydoc_available():
            sys.stderr.write(
                "Error: --converter anydoc, but firecrawl-anydoc is not installed.\n"
                "  .venv/bin/python -m pip install firecrawl-anydoc\n")
            sys.exit(2)
        fb = _convert_office_anydoc(office_path)
        if fb is None:
            sys.stderr.write(
                "Error: anydoc could not convert this document (see above). "
                "Re-run with --converter auto to allow the markitdown fallback.\n")
            sys.exit(2)
        text, method = fb
        sys.stderr.write(f"[convert] converted via {method}\n")
        return text

    # Sits before the markitdown import so an anydoc success never requires
    # markitdown to be installed.
    anydoc_tried = False
    if converter == "auto" and office_path is not None and _OFFICE_PREFER_ANYDOC:
        anydoc_tried = True
        fb = _convert_office_anydoc(office_path)
        if fb is not None:
            text, method = fb
            sys.stderr.write(f"[convert] converted via {method}\n")
            return text

    try:
        from markitdown import MarkItDown
    except ImportError:
        sys.stderr.write(
            "Error: markitdown is not installed. From this folder run:\n"
            "  py -3.13 -m venv .venv\n"
            "  .\\.venv\\Scripts\\Activate.ps1\n"
            "  pip install -r requirements.txt\n"
        )
        sys.exit(2)

    md = MarkItDown(enable_plugins=False)
    pdf_path: Path | None = None
    try:
        candidate = Path(input_value)
        if candidate.is_file() and candidate.suffix.lower() == ".pdf":
            pdf_path = candidate
    except (OSError, ValueError):
        pdf_path = None

    try:
        result = md.convert(input_value)
        text = result.text_content or ""
    except Exception as exc:
        message = str(exc)
        lower = message.lower()
        if "ffmpeg" in lower or "couldntdecodeerror" in lower or "audioop" in lower:
            sys.stderr.write(
                "Error: audio conversion failed. ffmpeg is likely missing.\n"
                "  Install it with:  winget install Gyan.FFmpeg\n"
                f"  (underlying error: {message})\n"
            )
            sys.exit(2)
        # PDF-specific fallback chain — recovers from PSEOF / Unexpected EOF
        # and similar pdfminer failures on malformed or scan-only PDFs.
        if pdf_path is not None:
            sys.stderr.write(
                f"[convert] markitdown failed on PDF ({message}); "
                "trying pdfplumber -> pypdfium2 -> OCR...\n")
            fb = _convert_pdf_fallback(pdf_path)
            if fb is not None:
                text, method = fb
                sys.stderr.write(
                    f"[convert] recovered via {method}\n")
                title = pdf_path.stem.replace("_", " ").replace("-", " ").strip() or "Untitled PDF"
                return f"# {title}\n\n{text}\n"
            sys.stderr.write(
                "Error: this PDF can't be parsed by markitdown or any of "
                "the fallback parsers (pdfplumber, pypdfium2, OCR).\n"
                "  - If it's encrypted, decrypt it first (or open + Save As).\n"
                "  - If it's a scan, install Tesseract: "
                "winget install UB-Mannheim.TesseractOCR\n"
                "  - If it's truncated, re-download the original.\n"
                f"  - Original error: {message}\n")
            sys.exit(2)
        if office_path is not None and converter == "auto" and not anydoc_tried:
            sys.stderr.write(
                f"[convert] markitdown failed on office doc ({message}); "
                "trying anydoc...\n")
            fb = _convert_office_anydoc(office_path)
            if fb is not None:
                text, method = fb
                sys.stderr.write(f"[convert] recovered via {method}\n")
                return text
        sys.stderr.write(f"Error: markitdown failed to convert input.\n  {message}\n")
        sys.exit(2)

    # markitdown returned something — but for PDFs, empty/whitespace-only
    # content is usually an image-only scan that pdfminer couldn't read. Try
    # the fallback so OCR can pick it up.
    if pdf_path is not None and not text.strip():
        sys.stderr.write(
            "[convert] markitdown returned empty text for the PDF "
            "(likely a scan); trying fallback parsers + OCR...\n")
        fb = _convert_pdf_fallback(pdf_path)
        if fb is not None:
            text, method = fb
            sys.stderr.write(f"[convert] recovered via {method}\n")
            title = pdf_path.stem.replace("_", " ").replace("-", " ").strip() or "Untitled PDF"
            return f"# {title}\n\n{text}\n"

    # Same recovery for office docs markitdown "converted" to nothing —
    # only when auto mode hasn't already tried (and failed) anydoc.
    if (office_path is not None and converter == "auto" and not anydoc_tried
            and not text.strip()):
        sys.stderr.write(
            "[convert] markitdown returned empty text for the office doc; "
            "trying anydoc...\n")
        fb = _convert_office_anydoc(office_path)
        if fb is not None:
            text, method = fb
            sys.stderr.write(f"[convert] recovered via {method}\n")
            return text

    return text


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #

def main(argv: list[str] | None = None) -> int:
    require_python_310()
    load_project_env()

    parser = argparse.ArgumentParser(
        description="Convert a YouTube URL or file to Markdown for Claude Code ingestion."
    )
    parser.add_argument("input", help="URL (http/https) or path to a file")
    parser.add_argument("--out", default=str(DEFAULT_OUT_DIR), help="Output directory")
    parser.add_argument(
        "--type", choices=("auto", "url", "file"), default="auto",
        help="Force input interpretation (default: auto)",
    )
    parser.add_argument(
        "--converter", choices=("auto", "anydoc", "markitdown"), default="auto",
        help="Office-document converter (docx/pptx/xlsx/odt/rtf/epub and "
             "variants): auto tries anydoc first, falling back to markitdown "
             "on failure or empty output; an explicit pick hard-fails rather "
             "than silently falling back. YouTube and PDF are unaffected.",
    )
    parser.add_argument("--no-frontmatter", action="store_true", help="Skip YAML frontmatter")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing output file")
    parser.add_argument(
        "--force", action="store_true",
        help="Re-convert even if an output already exists for the same source (default: skip)",
    )
    parser.add_argument(
        "--frames", action="store_true",
        help="(YouTube only) Extract frames + run OCR for on-screen text. "
             "Appends a 'Visual content' section to the .md and saves frames to "
             "output/<slug>-frames/.",
    )
    parser.add_argument(
        "--frame-width", type=int, default=512,
        help="Frame width in pixels (default 512; bump to 1024 for code/text-heavy videos).",
    )
    parser.add_argument(
        "--max-frames", type=int, default=30,
        help="Cap on extracted frames (default 30). Bump for long videos with "
             "dense visual content.",
    )
    parser.add_argument(
        "--dense-until", type=float, default=0,
        help="Sample one frame every --dense-interval seconds from 0 up to this "
             "timestamp (default 0 = off). Use for videos where the first stretch "
             "has whiteboard/Excalidraw diagrams that get populated mid-chapter — "
             "chapter-start frames alone catch the blank canvas. "
             "Accepts seconds (1200) or mm:ss (20:00).",
    )
    parser.add_argument(
        "--dense-interval", type=float, default=30,
        help="Seconds between dense-sampled frames (default 30). "
             "Only used with --dense-until.",
    )
    args = parser.parse_args(argv)

    # Allow mm:ss for --dense-until
    if isinstance(args.dense_until, str) and ":" in args.dense_until:
        m, s = args.dense_until.split(":")
        args.dense_until = int(m) * 60 + int(s)
    args.dense_until = float(args.dense_until)

    kind = detect_type(args.input, args.type)
    type_label = specific_type(args.input, kind)

    if kind == "file" and not Path(args.input).exists():
        sys.stderr.write(f"Error: file not found: {args.input}\n")
        return 2
    if kind == "url" and type_label == "youtube" and "&list=" in args.input:
        warn("playlist URLs aren't fully supported; only the first video will be converted.")

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    if not args.force:
        identifier = canonical_source(args.input, kind)
        existing = find_duplicate(identifier, out_dir)
        if existing:
            sys.stderr.write(
                f"already-converted: {existing.name} — use --force to re-convert.\n"
            )
            print(str(existing.resolve()))
            return 0

    yt_info: dict | None = None
    if type_label == "youtube":
        body, title, yt_info = convert_youtube(args.input)
    else:
        body = ""
        title = ""
        # Non-YouTube web URLs: try readable-article extraction first (strips
        # site chrome, keeps headings). Files, and any page it can't extract
        # (JS-only, paywalled, fetch error), fall through to markitdown.
        if type_label == "url":
            article = convert_url_article(args.input)
            if article is not None:
                body, title = article
        if not body.strip():
            body = convert_with_markitdown(args.input, converter=args.converter)
            title = extract_title_from_md(body, args.input, kind)
        if not body.strip():
            sys.stderr.write("Error: conversion produced an empty document.\n")
            return 3
        if not title:
            title = extract_title_from_md(body, args.input, kind)

    if not body.strip():
        sys.stderr.write("Error: conversion produced an empty document.\n")
        return 3

    slug = slugify(title)
    target = out_dir / f"{slug}.md"
    if not args.overwrite:
        target = collide_safe(target)
        slug = target.stem  # if we collided, frames dir should match the resolved stem

    # Frame extraction (Tier 2) — opt-in, YouTube only for now
    if args.frames and type_label == "youtube" and yt_info is not None:
        duration = float(yt_info.get("duration") or 0)
        chapters = yt_info.get("chapters") or []
        frames = extract_frames_and_ocr(
            url=args.input, slug=slug, duration=duration, chapters=chapters,
            out_dir=out_dir, max_width=args.frame_width,
            max_frames=args.max_frames,
            dense_until=args.dense_until,
            dense_interval=args.dense_interval,
        )
        visual_section = render_visual_content_section(frames, slug)
        if visual_section:
            body = body.rstrip() + "\n\n" + visual_section
        else:
            warn(
                "visual-capture-failed: no frames were extracted; transcript "
                "was saved without visual content"
            )
    elif args.frames and type_label != "youtube":
        warn("--frames is only supported for YouTube URLs (skipping).")

    payload = body if args.no_frontmatter else wrap_with_frontmatter(
        body, source=args.input, type_=type_label, title=title,
    )

    target.write_text(payload, encoding="utf-8")
    print(str(target.resolve()))

    # A video conversion with no captions produces a file that LOOKS fine:
    # valid markdown, real frontmatter, a title and a description. It used to
    # exit 0, so the watcher, the server and any script treated it as a good
    # source, and the ingest agent went on to write a wiki page out of the
    # description alone. Write the file (it is still worth inspecting) but
    # report failure, so callers can act on it.
    problem = _transcript.check(payload, target.name)
    if problem:
        warn(problem)
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
