"""Is a converted file actually usable as a source?

The whole pipeline rests on the transcript. Every wiki page, every concept's
evidence count, every deck slide traces back to one. A conversion that
produces only a video's title and description still LOOKS like a valid
markdown file, and until this module existed it flowed straight through
pending detection into ingest, where an agent dutifully wrote a source page
out of the description alone. Two AI Engineer talks reached the wiki that
way in July 2026: their pages described the talks without containing them.

So both ends check. convert.py refuses to report success for a YouTube
conversion with no transcript, and ingest.py refuses to hand one to an agent.

Deliberately NOT a strict schema check. Web articles have no transcript
section and are perfectly valid; the rule only binds video conversions.
"""
from __future__ import annotations

import re

# Long-form videos keep the original conservative floor. Short videos use a
# duration-aware floor so a complete two-minute transcript is not mistaken for
# a partial fetch and sent through every audio fallback.
MIN_TRANSCRIPT_WORDS = 1200
MIN_SHORT_TRANSCRIPT_WORDS = 20
MIN_WORDS_PER_MINUTE = 45

# The heading carries the caption source, e.g. "## Transcript (auto-generated,
# en)", so match the prefix rather than the whole line. An earlier version
# anchored with `$` and therefore rejected every real transcript.
_TRANSCRIPT_HEADING = re.compile(
    r"^##\s+Transcript\b(?P<suffix>[^\n]*)$", re.M | re.I
)
_TYPE_FIELD = re.compile(r'^type:\s*"?([a-z]+)"?', re.M | re.I)
_DURATION_FIELD = re.compile(
    r"^-\s+\*\*Duration:\*\*\s*([0-9]+(?::[0-9]{1,2}){1,2})\s*$",
    re.M | re.I,
)


def is_video(md: str) -> bool:
    """True for conversions of a video, where a transcript is mandatory.
    Web articles and dropped files carry their content in the body instead."""
    m = _TYPE_FIELD.search(md[:1500])
    return bool(m) and m.group(1).lower() in {"youtube", "video"}


def transcript_words(md: str) -> int:
    """Word count of the `## Transcript` section, 0 if there is none."""
    m = _TRANSCRIPT_HEADING.search(md)
    if not m:
        return 0
    rest = md[m.end():]
    nxt = re.search(r"^##\s+", rest, re.M)
    body = rest[: nxt.start()] if nxt else rest
    # Local whisper.cpp output keeps one timestamp per segment for traceability.
    # Do not let those labels inflate the completeness safety floor.
    body = re.sub(
        r"^\[[0-9:.,]+\s+-\s+[0-9:.,]+\]\s*",
        "",
        body,
        flags=re.M,
    )
    return len(body.split())


def duration_seconds(md: str) -> int | None:
    """Return the converted video's duration from its Metadata section."""
    match = _DURATION_FIELD.search(md)
    if not match:
        return None
    try:
        parts = [int(part) for part in match.group(1).split(":")]
    except ValueError:
        return None
    if len(parts) == 2:
        minutes, seconds = parts
        return minutes * 60 + seconds
    if len(parts) == 3:
        hours, minutes, seconds = parts
        return hours * 3600 + minutes * 60 + seconds
    return None


def minimum_words(duration_s: int | float | None = None) -> int:
    """Completeness floor for a video of ``duration_s`` seconds.

    Forty-five words per minute is deliberately conservative for pauses,
    demonstrations, and music. The long-form cap preserves the historical
    1,200-word guard.
    """
    if duration_s is None or duration_s <= 0:
        return MIN_TRANSCRIPT_WORDS
    duration_floor = round(float(duration_s) * MIN_WORDS_PER_MINUTE / 60)
    return min(
        MIN_TRANSCRIPT_WORDS,
        max(MIN_SHORT_TRANSCRIPT_WORDS, duration_floor),
    )


def _transcript_identity(md: str) -> tuple[str, str]:
    match = _TRANSCRIPT_HEADING.search(md)
    if not match:
        return "", ""
    suffix = (match.group("suffix") or "").strip().strip("()")
    low = suffix.lower()
    if "local whisper" in low:
        provenance = "local Whisper"
    elif "whisper via groq" in low:
        provenance = "Groq Whisper"
    elif "auto-generated" in low:
        provenance = "automatic captions"
    elif not suffix:
        provenance = "human captions"
    else:
        provenance = suffix
    language = ""
    language_match = re.search(r",\s*([A-Za-z][A-Za-z0-9-]*)\s*$", suffix)
    if language_match:
        language = language_match.group(1)
    return provenance, language


def diagnose(md: str, name: str = "transcript") -> dict:
    """Return structured source-readiness data for the editor and ingest."""
    video = is_video(md)
    words = transcript_words(md) if video else 0
    duration_s = duration_seconds(md) if video else None
    threshold = minimum_words(duration_s) if video else 0
    provenance, language = _transcript_identity(md) if video else ("", "")

    if not video:
        return {
            "status": "ready",
            "code": "not_required",
            "words": 0,
            "minimum_words": 0,
            "duration_seconds": None,
            "provenance": "",
            "language": "",
            "problem": "",
        }
    if words == 0:
        problem = (
            f"{name}: no '## Transcript' section. This capture contains "
            "metadata and description only. Retry from Add, or Re-run "
            "convert.py, to try human captions, automatic captions, local "
            "Whisper and optional Groq. If the source is private, removed, "
            "age-restricted or blocked, Riverfed cannot recover it "
            "automatically."
        )
        code = "missing_transcript"
        status = "blocked"
    elif words < threshold:
        duration_note = (
            f" for a {duration_s // 60}:{duration_s % 60:02d} video"
            if duration_s is not None else ""
        )
        problem = (
            f"{name}: transcript is {words} words; at least {threshold} are "
            f"expected{duration_note}. This is likely a partial caption or "
            "audio fetch. Retry from Add, or Re-run convert.py, before "
            "ingesting."
        )
        code = "incomplete_transcript"
        status = "blocked"
    else:
        problem = ""
        code = "ready"
        status = "ready"
    return {
        "status": status,
        "code": code,
        "words": words,
        "minimum_words": threshold,
        "duration_seconds": duration_s,
        "provenance": provenance,
        "language": language,
        "problem": problem,
    }


def check(md: str, name: str = "transcript") -> str | None:
    """Return a human-readable problem, or None when the file is usable.

    The message names the likely cause, because the failure people actually
    hit ("no transcript could be fetched") reads as though YouTube were at
    fault when it usually is not.
    """
    problem = diagnose(md, name)["problem"]
    return problem or None
