#!/bin/zsh
# ============================================================
# sync.command  --  macOS twin of sync.cmd.
#
# Pull the latest from GitHub before you start work. If the
# other collaborator has pushed anything, you'll have it. If
# you have uncommitted local changes, the script tells you to
# commit or stash first.
#
# Safe to double-click from Finder.
# ============================================================
cd "$(dirname "$0")" || exit 1

echo ""
echo "=== Pulling latest from origin/main ==="
echo ""

# 1. Bail if there are uncommitted changes - rebase would refuse.
if ! git diff --quiet || ! git diff --cached --quiet; then
    echo "*** You have uncommitted local changes:"
    git status --short
    echo ""
    echo "Commit them first, then re-run sync.command."
    echo "  git add ."
    echo "  git commit -m \"your message\""
    echo "Or temporarily set them aside with:"
    echo "  git stash"
    exit 1
fi

# 2. Fetch + rebase
if ! git fetch origin; then
    echo "*** git fetch failed. Check your network or GitHub auth."
    exit 1
fi

# 3. Show what's about to come in
echo ""
echo "--- Incoming commits from origin ---"
git log --oneline --pretty="  %h %an: %s" HEAD..origin/main
echo ""

if ! git pull --rebase origin main; then
    echo ""
    echo "*** Rebase hit a conflict."
    echo "    Open the conflicting files, resolve the markers (<<<<<<<),"
    echo "    then run:"
    echo "        git add <resolved-files>"
    echo "        git rebase --continue"
    echo ""
    echo "    Or abort with:  git rebase --abort"
    exit 1
fi

echo ""
echo "=== Up to date ==="
git log -1 --pretty="  HEAD is %h - %an: %s"
