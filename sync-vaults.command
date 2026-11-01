#!/bin/zsh
# ============================================================
# sync-vaults.command  --  macOS twin of sync-vaults.cmd.
#
# The vaults live OUTSIDE this repo (~/RiverfedVaults), each as
# its own git repo. This commits whatever ingests/edits happened
# locally, pulls the other collaborator's edits, and pushes yours.
#
# Safe to double-click from Finder.
# ============================================================
cd "$(dirname "$0")" || exit 1
export PATH="/opt/homebrew/bin:$HOME/.local/bin:$PATH"

echo ""
echo "=== Syncing knowledge-base vaults ==="
echo ""

.venv/bin/python wiki/scripts/sync_vaults.py
