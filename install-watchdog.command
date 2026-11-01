#!/bin/zsh
# ============================================================
# install-watchdog.command  --  macOS twin of install-watchdog.cmd.
#
# Registers a per-user LaunchAgent (com.riverfed.watchdog) that runs
# watchdog.command every 5 minutes: it probes http://127.0.0.1:8765/healthz
# and kickstarts the server LaunchAgent if it has died.
#
# Double-click from Finder or run from a terminal. Idempotent - safe to
# re-run; it overwrites the plist and reloads the job.
# ============================================================
cd "$(dirname "$0")" || exit 1

LABEL="com.riverfed.watchdog"
PLIST="$HOME/Library/LaunchAgents/${LABEL}.plist"
SCRIPT="$(pwd)/watchdog.command"
LOG="$HOME/Library/Logs/riverfed-watchdog.log"

if [ ! -f "$SCRIPT" ]; then
    echo "watchdog.command not found next to this installer." >&2
    exit 1
fi
chmod +x "$SCRIPT"

echo "Writing $PLIST"
cat > "$PLIST" <<PLISTEOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>${LABEL}</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/zsh</string>
        <string>${SCRIPT}</string>
    </array>
    <key>StartInterval</key>
    <integer>300</integer>
    <key>RunAtLoad</key>
    <true/>
    <key>StandardOutPath</key>
    <string>${LOG}</string>
    <key>StandardErrorPath</key>
    <string>${LOG}</string>
</dict>
</plist>
PLISTEOF

# Reload cleanly: bootout the old job (ignore errors if not loaded), then bootstrap.
launchctl bootout "gui/$(id -u)/${LABEL}" 2>/dev/null
launchctl bootstrap "gui/$(id -u)" "$PLIST"

if launchctl print "gui/$(id -u)/${LABEL}" >/dev/null 2>&1; then
    echo
    echo "Watchdog installed and running."
    echo "It probes http://127.0.0.1:8765/healthz every 5 minutes and kickstarts"
    echo "the server if it has died. Logs: $LOG"
else
    echo "ERROR: watchdog job did not load. Check $LOG" >&2
    exit 1
fi
