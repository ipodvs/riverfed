#!/usr/bin/env python3
"""Sync every git-backed vault in the vault home with its remote.

For each ~/RiverfedVaults/<slug>/ that is a git repo:
  1. commit local changes (ingests, watcher runs, hand edits)
  2. pull --rebase (pick up the other collaborator's edits)
  3. push (if a remote is configured)

Vaults without a remote just get the local commit — still versioned,
just not shared. Safe to run any time; conflicts stop that vault with
the exact recovery command and the script moves on to the next one.

Usage:  py -3.13 wiki\\scripts\\sync_vaults.py    (or double-click
        sync-vaults.cmd at the project root)
"""
from __future__ import annotations

import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _wikis import vaults_home  # noqa: E402

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


def _git(vault: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=str(vault),
                          capture_output=True, text=True, timeout=300)


def sync_one(vault: Path) -> str:
    # 1) commit anything local
    _git(vault, "add", "-A")
    staged = _git(vault, "diff", "--cached", "--quiet")
    if staged.returncode != 0:
        msg = f"wiki update {datetime.now():%Y-%m-%d %H:%M} (sync-vaults)"
        c = _git(vault, "commit", "-q", "-m", msg)
        if c.returncode != 0:
            return f"commit failed: {c.stderr.strip()[:140]}"
        committed = "committed local changes; "
    else:
        committed = ""

    # 2) pull + 3) push, only when a remote exists
    remotes = _git(vault, "remote").stdout.split()
    if not remotes:
        return committed + "no remote — local-only vault, done"
    pull = _git(vault, "pull", "--rebase", "--autostash")
    if pull.returncode != 0:
        _git(vault, "rebase", "--abort")
        return (committed + "PULL CONFLICT — resolve by hand: open the "
                f"vault in a terminal ({vault}), run `git pull --rebase`, "
                "fix the <<<<<<< markers, `git rebase --continue`, rerun")
    push = _git(vault, "push")
    if push.returncode != 0:
        return committed + f"push failed: {push.stderr.strip()[:140]}"
    return committed + "in sync with remote"


def main() -> int:
    home = vaults_home()
    if not home.exists():
        print(f"No vault home at {home} — nothing to sync.")
        return 0
    rc = 0
    found = False
    for d in sorted(home.iterdir()):
        if not (d / ".git").exists():
            continue
        found = True
        status = sync_one(d)
        print(f"  {d.name}: {status}")
        if "CONFLICT" in status or "failed" in status:
            rc = 1
    if not found:
        print(f"No git-backed vaults under {home}.")
    return rc


if __name__ == "__main__":
    sys.exit(main())
