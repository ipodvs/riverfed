#!/bin/zsh
# ============================================================
# ship.command  --  macOS twin of ship.cmd.
#
# Push your local commits to GitHub at the END of a session:
#   1. Stops if you have uncommitted work (commit it first).
#   2. Pulls latest with rebase (so your push won't be rejected).
#   3. Pushes your local commits to origin/main.
#
# Safe to double-click from Finder.
# ============================================================
cd "$(dirname "$0")" || exit 1

echo ""
echo "=== Shipping local commits to origin/main ==="
echo ""

# 1. Bail if there are uncommitted changes.
if ! git diff --quiet || ! git diff --cached --quiet; then
    echo "*** You have uncommitted local changes:"
    git status --short
    echo ""
    echo "Commit them first, then re-run ship.command."
    echo "  git add ."
    echo "  git commit -m \"your message\""
    echo "Or temporarily set them aside with:"
    echo "  git stash"
    exit 1
fi

# 2. Show what we're about to ship
if ! git fetch origin; then
    echo "*** git fetch failed. Check your network or GitHub auth."
    exit 1
fi

echo ""
echo "--- Local commits ahead of origin ---"
git log --oneline --pretty="  %h: %s" origin/main..HEAD
echo ""

AHEAD=$(git rev-list --count origin/main..HEAD)
if [ "$AHEAD" = "0" ]; then
    echo "Nothing to push - local is already at origin/main."
    git log -1 --pretty="  HEAD is %h - %an: %s"
    exit 0
fi

# 3. Sync first (rebase any incoming commits underneath ours)
echo "--- Syncing with origin first (rebase) ---"
if ! git pull --rebase origin main; then
    echo ""
    echo "*** Rebase hit a conflict."
    echo "    Open the conflicting files, resolve the markers (<<<<<<<),"
    echo "    then run:"
    echo "        git add <resolved-files>"
    echo "        git rebase --continue"
    echo "        ./ship.command"
    echo ""
    echo "    Or abort with:  git rebase --abort"
    exit 1
fi

# 4. Push
echo ""
echo "--- Pushing ---"
if ! git push origin main; then
    echo ""
    echo "*** Push failed. See output above."
    exit 1
fi

echo ""
echo "=== Shipped ==="
git log --pretty="  %h: %s" -3
