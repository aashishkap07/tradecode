#!/usr/bin/env bash
# OMEGA V60 — push the logs to GitHub so they can be analysed  [C472]
#
# WHY THIS EXISTS. The logs live on your server. Nobody analysing them can
# reach your server. Without this you have to remember to download files and
# attach them, which means analysis happens when you remember, not when
# something interesting happens.
#
# This commits the REPORT and SESSION logs to a `logs` branch every hour. The
# detail log is NOT pushed by default: it is ~3 MB an hour and mostly working.
# Set PUSH_DETAIL=1 if a specific investigation needs it.
#
# Install:
#   sudo cp omega-logpush.sh /usr/local/bin/ && sudo chmod +x /usr/local/bin/omega-logpush.sh
#   echo '17 * * * * omega /usr/local/bin/omega-logpush.sh' | sudo tee /etc/cron.d/omega-logpush
#
# (minute 17, so it does not collide with every other cron job on the hour.)

set -uo pipefail

REPO="${OMEGA_HOME:-/home/omega/omega}"
BRANCH="${OMEGA_LOG_BRANCH:-logs}"
PUSH_DETAIL="${PUSH_DETAIL:-0}"

cd "$REPO" || exit 1

# A worktree keeps the logs branch entirely separate from the code branch, so
# this can never commit, stash or disturb the checkout the bot is running from.
WT="${REPO}/.logpush"
if [ ! -d "$WT/.git" ] && [ ! -f "$WT/.git" ]; then
    git worktree add -B "$BRANCH" "$WT" 2>/dev/null || {
        git fetch origin "$BRANCH" 2>/dev/null
        git worktree add "$WT" "$BRANCH" 2>/dev/null || exit 1
    }
fi

mkdir -p "$WT/logs"
copied=0
for f in "$REPO"/omega_report_*.log "$REPO"/omega_session_*.log; do
    [ -e "$f" ] || continue
    cp -f "$f" "$WT/logs/" && copied=$((copied+1))
done
if [ "$PUSH_DETAIL" = "1" ]; then
    for f in "$REPO"/omega_detail_*.log; do
        [ -e "$f" ] || continue
        cp -f "$f" "$WT/logs/" && copied=$((copied+1))
    done
fi
# The state files are small and say what the bot believes about itself.
for f in "$REPO"/data/mode_v60.json "$REPO"/data/state_v60.json; do
    [ -e "$f" ] && cp -f "$f" "$WT/logs/"
done

[ "$copied" -gt 0 ] || exit 0

# ── SCRUB. Nothing here should carry a secret, but "should" is not a control.
# A token or an API key that reaches a git history is there permanently, so
# this runs on every push rather than trusting that the bot never logs one.
if [ -f /etc/omega.token ]; then
    TOK="$(cat /etc/omega.token)"
    [ -n "$TOK" ] && grep -rlF "$TOK" "$WT/logs" 2>/dev/null | while read -r h; do
        sed -i "s|${TOK}|<TOKEN-REDACTED>|g" "$h"
    done
fi
# The value class MUST include _ and -. Exchange keys look like
# "bg_9f8a7b6c5d4e..." and a class of [A-Za-z0-9/+] stops at the underscore,
# matching two characters, failing the {16,} length test and redacting
# NOTHING -- which is the worst possible outcome for a scrubber, because it
# reports success. Caught by feeding it a real-shaped Bitget key.
SECRET_RE='(api[_-]?key|api[_-]?secret|passphrase|secret|password)'
grep -rlEi "${SECRET_RE}[\"':= ]+[A-Za-z0-9/+_-]{16,}" \
     "$WT/logs" 2>/dev/null | while read -r h; do
    sed -i -E "s/(${SECRET_RE})([\"':= ]+)[A-Za-z0-9\/+_-]{16,}/\1\3<REDACTED>/gI" "$h"
done

cd "$WT" || exit 1
git add -A logs
git diff --cached --quiet && exit 0          # nothing changed, say nothing
git -c user.name='omega-bot' -c user.email='omega@localhost' \
    commit -q -m "logs: $(date -u '+%Y-%m-%d %H:%M UTC') ($copied file(s))"
for i in 1 2 3 4; do
    git push -q origin "HEAD:$BRANCH" && exit 0
    sleep $((2 ** i))
done
logger -t omega-logpush "push failed after 4 attempts"
exit 1
