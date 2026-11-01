#!/bin/zsh
# ============================================================
# uninstall-watchdog.command  --  macOS twin of uninstall-watchdog.cmd.
#
# Removes the com.riverfed.watchdog LaunchAgent. Does not touch the
# server itself.
# ============================================================
LABEL="com.riverfed.watchdog"
PLIST="$HOME/Library/LaunchAgents/${LABEL}.plist"

echo "Removing LaunchAgent: $LABEL"
launchctl bootout "gui/$(id -u)/${LABEL}" 2>/dev/null && echo "Job unloaded." || echo "Job was not loaded."
rm -f "$PLIST" && echo "Removed $PLIST"
