#!/usr/bin/env bash
# OMEGA V60 — health watchdog  [C467-D]
#
# WHY THIS EXISTS. systemd restarts the bot when the PROCESS dies. It cannot
# see the worse failure: a process that is still alive but has stopped
# scanning — a wedged network call, a thread that died quietly. A bot that
# looks up and is doing nothing for eight hours while you sleep is worse than
# one that crashed, because nothing tells you.
#
# This asks the bot's own /api/health endpoint how long ago its last scan was.
# If that is older than MAX_AGE, it restarts the service.
#
# Install as a cron job, every 5 minutes:
#   sudo cp omega-watchdog.sh /usr/local/bin/ && sudo chmod +x /usr/local/bin/omega-watchdog.sh
#   echo '*/5 * * * * root /usr/local/bin/omega-watchdog.sh' | sudo tee /etc/cron.d/omega-watchdog

set -uo pipefail

PORT="${OMEGA_PORT:-8138}"
TOKEN="$(cat /etc/omega.token 2>/dev/null || echo '')"
# Scans run every ~8 minutes (SCAN_INTERVAL 480s). Three missed scans is a
# genuine problem; one is a slow exchange. 1800s = 30 minutes.
MAX_AGE="${OMEGA_MAX_SCAN_AGE:-1800}"

resp="$(curl -fsS --max-time 10 "http://127.0.0.1:${PORT}/api/health?t=${TOKEN}" 2>/dev/null || echo '')"

if [ -z "$resp" ]; then
    logger -t omega-watchdog "health endpoint did not answer — restarting omega"
    systemctl restart omega
    exit 0
fi

age="$(printf '%s' "$resp" | grep -o '"last_scan_age_s":[ ]*[0-9.]*' | grep -o '[0-9.]*$' || echo '')"

# No scan recorded yet is NORMAL for the first few minutes after a start.
# Restarting on it would put the bot in a boot loop, which is the classic
# watchdog mistake: a health check that cannot tell "starting" from "stuck".
if [ -z "$age" ]; then
    logger -t omega-watchdog "no scan recorded yet — leaving it alone"
    exit 0
fi

if awk -v a="$age" -v m="$MAX_AGE" 'BEGIN{exit !(a>m)}'; then
    logger -t omega-watchdog "last scan was ${age}s ago (limit ${MAX_AGE}s) — restarting omega"
    systemctl restart omega
else
    exit 0
fi
