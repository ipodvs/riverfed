#!/usr/bin/env python3
"""Back-compat shim — the resolver generalized to _agent_bin.py (A6 step 2).

Kept so older references keep working; new code should use
agent_runner (for spawning) or _agent_bin.resolve_agent_bin (for
resolution only).
"""
from __future__ import annotations

from _agent_bin import resolve_claude_bin  # noqa: F401
