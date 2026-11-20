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

REPO="${OMEGA_HOME:-/home/omega/omega}"

resp="$(curl -fsS --max-time 10 "http://127.0.0.1:${PORT}/api/health?t=${TOKEN}" 2>/dev/null || echo '')"

# ═══ C479: A SILENT PORT IS NOT A STUCK BOT ══════════════════════
# This used to read "health did not answer" as proof the bot was wedged, and
# restart it. That is wrong, and it was dangerous in the one case that actually
# happens: the control panel fails to bind :8138 because an older copy of the
# bot still holds it. The bot is then perfectly healthy and trading -- it just
# has no panel. The old rule restarted that healthy bot, WITH OPEN POSITIONS,
# every five minutes forever, and each restart re-created the overlap that
# caused the busy port in the first place.
#
# The process dying is systemd's job (Restart=always). This watchdog exists for
# the process that is ALIVE but no longer working. So before restarting, ask a
# liveness question that does not go through the port at all: is the bot still
# WRITING ITS LOG? If it is, it is alive and doing its job, and the panel is a
# separate (self-healing, see C479 in the bot) problem that must not cost a
# restart. Only when the log has ALSO gone quiet is this a real wedge.
if [ -z "$resp" ]; then
    newest="$(ls -t "$REPO"/omega_report_*.log 2>/dev/null | head -1)"

    if [ -z "$newest" ]; then
        # No report log at all: the bot has not got that far yet. Restarting
        # here is the boot-loop mistake the scan-age branch below already
        # guards against -- do not make it from this direction either.
        logger -t omega-watchdog "panel silent and no report log yet — leaving it alone"
        exit 0
    fi

    now="$(date +%s)"
    mtime="$(stat -c %Y "$newest" 2>/dev/null || echo 0)"
    log_age=$(( now - mtime ))

    if [ "$log_age" -lt "$MAX_AGE" ]; then
        logger -t omega-watchdog "control panel not answering, but the bot wrote its log ${log_age}s ago — it is ALIVE, NOT restarting (port :${PORT} is probably still held by an older copy; the bot retries it every 15s)"
        exit 0
    fi

    logger -t omega-watchdog "panel silent AND log stale (${log_age}s > ${MAX_AGE}s) — restarting omega"
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
