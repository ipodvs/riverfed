"""Shared bootstrap for the stdlib-only test suite.

CI runs `python -m unittest discover -s tests` (no pip installs). Every test
module imports this first to put wiki/scripts on the path and to hand out a
throwaway vault home so scaffold tests never touch the real ~/RiverfedVaults.

Safe to run in a working checkout: the suite writes only to temp dirs (vault
homes here, and a temp models root in the custom-model test) and removes them
via addCleanup. It never reads, writes, or deletes the user's gitignored
models/custom/ or designs/custom/.
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = PROJECT_DIR / "wiki" / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


def fresh_vault_home() -> Path:
    """Point RIVERFED_VAULTS_DIR at a new temp dir and return it. `_wikis`
    reads the env var live on every call, so no module reload is needed."""
    home = Path(tempfile.mkdtemp(prefix="riverfed-test-vaults-"))
    os.environ["RIVERFED_VAULTS_DIR"] = str(home)
    return home
