#!/usr/bin/env python3
"""Resolve agent CLI binaries, per provider (A6 step 2).

Generalizes the original _claude_bin.py: npm registers `claude.CMD` and
`codex.CMD` on Windows, and Python's `subprocess.run(["claude", ...])`
does NOT walk PATHEXT to find them — it requires the exact filename.
`shutil.which()` does walk PATHEXT, so it returns the absolute path
including the extension.

Per-provider env overrides let users pin a specific binary (e.g. a beta
channel): CLAUDE_BIN for claude-code, CODEX_BIN for codex, GROK_BIN for
grok (whose installer drops it in ~/.local/bin, not always on a service
process's PATH).

Callers should not import this directly for spawning — go through
agent_runner.run()/probe(), which owns argv construction, prompt
delivery, env scrub and timeouts.
"""
from __future__ import annotations

import os
import shutil
from pathlib import Path

# provider id -> (binary name on PATH, env override var)
PROVIDER_BINS: dict[str, tuple[str, str]] = {
    "claude-code": ("claude", "CLAUDE_BIN"),
    "codex": ("codex", "CODEX_BIN"),
    "grok": ("grok", "GROK_BIN"),
}


def resolve_agent_bin(provider: str) -> str | None:
    """Absolute path of the provider's CLI, or None if not installed.

    Honours the provider's env override first; otherwise walks PATH
    (including PATHEXT on Windows) for the well-known binary name.
    """
    try:
        bin_name, override_var = PROVIDER_BINS[provider]
    except KeyError:
        raise ValueError(f"unknown agent provider: {provider!r} "
                         f"(available: {', '.join(sorted(PROVIDER_BINS))})")
    override = os.environ.get(override_var)
    if override and (Path(override).exists() or shutil.which(override)):
        return shutil.which(override) or override
    return shutil.which(bin_name)


def resolve_claude_bin() -> str | None:
    """Back-compat alias for the original _claude_bin API."""
    return resolve_agent_bin("claude-code")
