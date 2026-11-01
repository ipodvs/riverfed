#!/usr/bin/env python3
"""One-shot C1 migration — move personal vaults out of the product repo
into the vault home (default ~/RiverfedVaults, see RIVERFED_VAULTS_DIR).

What moves:
  - The legacy `wiki` vault: its knowledge-model page folders + index.md,
    log.md, SCHEMA.md, .obsidian/, .state/, Excalidraw/ go to
    <home>/wiki/. `wiki/scripts/` and `wiki/training/` are PRODUCT code
    and stay in the repo.
  - The legacy staging `<project>/output/` contents → <home>/wiki/output/.
  - Every `wikis/<slug>/` vault except the keep-list (repo demo vaults,
    default: riverfed-ops) → <home>/<slug>/, whole directory.

Each migrated vault gets a .gitignore (output/, .state/) and — when git
is available — its own repo with an initial commit: your knowledge,
versioned in YOUR repo, not the product's.

Dry-run by default; pass --apply to act. Stop the server first
(stop.cmd) so the watcher can't sweep mid-move.

Usage:
    py -3.13 wiki\\scripts\\migrate_vaults.py            # show the plan
    py -3.13 wiki\\scripts\\migrate_vaults.py --apply    # do it
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _wikis import (LEGACY_WIKI_DIR, PROJECT_DIR, ROOT_OUTPUT,  # noqa: E402
                    WIKIS_PARENT, vaults_home)

if sys.platform == "win32":  # match the other scripts' console behavior
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

# Vault data inside the legacy wiki/ dir (everything else there is product
# code: scripts/, training/).
LEGACY_VAULT_ITEMS = ["sources", "topics", "entities", "concepts",
                      "index.md", "log.md", "SCHEMA.md",
                      ".obsidian", ".state", "Excalidraw"]
KEEP_IN_REPO = {"riverfed-ops"}        # repo demo vaults — publishable

VAULT_GITIGNORE = """\
# Raw transcript staging + runtime state — the pages are the knowledge.
output/
.state/
"""


def _git_init(vault_dir: Path) -> str:
    git = shutil.which("git")
    if not git:
        return "git not found — skipped repo init"
    if (vault_dir / ".git").exists():
        return "already a git repo"
    try:
        for cmd in (
            [git, "init", "-q"],
            [git, "add", "-A"],
            [git, "commit", "-q", "-m",
             "Initial commit — migrated out of the product repo (C1 vault split)"],
        ):
            r = subprocess.run(cmd, cwd=str(vault_dir), capture_output=True,
                               text=True, timeout=120)
            if r.returncode != 0:
                return f"git step failed: {' '.join(cmd[1:3])}: {r.stderr.strip()[:120]}"
        return "git repo initialized + initial commit"
    except Exception as exc:  # noqa: BLE001
        return f"git init skipped: {exc}"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--apply", action="store_true",
                    help="Actually move (default is a dry-run plan)")
    args = ap.parse_args()
    apply = args.apply
    home = vaults_home()

    moves: list[tuple[Path, Path]] = []   # (src, dst)

    # 1) legacy wiki vault items
    wiki_dst = home / "wiki"
    if (LEGACY_WIKI_DIR / "index.md").exists():
        for item in LEGACY_VAULT_ITEMS:
            src = LEGACY_WIKI_DIR / item
            if src.exists():
                moves.append((src, wiki_dst / item))
        # 2) legacy staging → <home>/wiki/output/ (.gitkeep stays — it keeps
        # the gitignored staging dir present in the product repo)
        if ROOT_OUTPUT.exists():
            for entry in sorted(ROOT_OUTPUT.iterdir()):
                if entry.name == ".gitkeep":
                    continue
                moves.append((entry, wiki_dst / "output" / entry.name))
    else:
        print("note: legacy wiki/ has no index.md — already migrated?")

    # 3) personal wikis/<slug> vaults (whole directories)
    vault_dirs: list[tuple[Path, Path]] = []
    if WIKIS_PARENT.exists():
        for d in sorted(WIKIS_PARENT.iterdir()):
            if d.is_dir() and d.name not in KEEP_IN_REPO \
                    and (d / "index.md").exists():
                vault_dirs.append((d, home / d.name))

    if not moves and not vault_dirs:
        print("Nothing to migrate.")
        return 0

    print(f"Vault home: {home}")
    print(f"{'APPLYING' if apply else 'DRY RUN (pass --apply to act)'}\n")
    for src, dst in moves:
        print(f"  move {src.relative_to(PROJECT_DIR)}  ->  {dst}")
    for src, dst in vault_dirs:
        print(f"  move {src.relative_to(PROJECT_DIR)}/  ->  {dst}/  (whole vault)")

    if not apply:
        return 0

    # refuse to clobber
    targets = [d for _, d in moves] + [d for _, d in vault_dirs]
    for t in targets:
        if t.exists():
            print(f"\nERROR: target already exists: {t} — aborting, nothing moved.")
            return 1

    moved_vault_roots: list[Path] = []
    if moves:
        (wiki_dst / "output").mkdir(parents=True, exist_ok=True)
        for src, dst in moves:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dst))
        moved_vault_roots.append(wiki_dst)
    for src, dst in vault_dirs:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))
        moved_vault_roots.append(dst)

    print("\nPer-vault git:")
    for root in moved_vault_roots:
        gi = root / ".gitignore"
        if not gi.exists():
            gi.write_text(VAULT_GITIGNORE, encoding="utf-8")
        print(f"  {root.name}: {_git_init(root)}")

    print(f"""
Done. {len(moved_vault_roots)} vault(s) now live under {home}

Next steps:
  1. Commit the deletions in the product repo (git add -A; the moved
     pages stay in private history — the future public repo is cut
     fresh at C4).
  2. Restart the server: stop.cmd then start.vbs.
  3. Verify: py -3.13 wiki\\scripts\\pending.py  (should resolve the
     vault-home wiki) and open /wiki in the browser.""")
    return 0


if __name__ == "__main__":
    sys.exit(main())
