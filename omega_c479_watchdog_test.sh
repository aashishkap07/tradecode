#!/usr/bin/env bash
# C479: the watchdog must not restart a HEALTHY bot.
#
# The old rule was "health endpoint did not answer -> systemctl restart omega".
# That is wrong whenever the bot is alive but the control panel failed to bind
# its port, which is exactly what an overlapping restart causes. The result was
# a healthy bot, holding open positions, restarted every five minutes forever.
#
# Rule 16: section 6 runs the SAME case against the PREVIOUS watchdog, taken
# from git, and requires it to restart. If section 6 ever passes, this test is
# no longer testing anything.
set -uo pipefail
cd "$(dirname "$0")"

PASS=0; FAIL=0
ok()  { if [ "$2" = "$3" ]; then echo "  PASS  $1"; PASS=$((PASS+1));
        else echo "  FAIL  $1   expected '$3', got '$2'"; FAIL=$((FAIL+1)); fi; }

WORK="$(mktemp -d)"; trap 'rm -rf "$WORK"' EXIT
BIN="$WORK/bin"; REPO="$WORK/repo"; mkdir -p "$BIN" "$REPO"

cat > "$BIN/systemctl" <<'S'
#!/usr/bin/env bash
echo "$@" >> "$MARKER"
S
cat > "$BIN/logger" <<'S'
#!/usr/bin/env bash
shift 2 2>/dev/null
echo "$@" >> "$WLOG"
S
cat > "$BIN/curl" <<'S'
#!/usr/bin/env bash
[ -n "${CURL_BODY:-}" ] || exit 7
printf '%s' "$CURL_BODY"
S
chmod +x "$BIN"/*

# $1=script  $2=curl body ('' = silent)  $3=report log age in seconds ('' = no log)
run_case() {
    local script="$1" body="$2" age="$3"
    rm -f "$REPO"/omega_report_*.log
    if [ -n "$age" ]; then
        local f="$REPO/omega_report_20260919_000000.log"
        echo "a line" > "$f"
        touch -d "@$(( $(date +%s) - age ))" "$f"
    fi
    export MARKER="$WORK/marker" WLOG="$WORK/wlog"
    rm -f "$MARKER" "$WLOG"; : > "$MARKER"; : > "$WLOG"
    CURL_BODY="$body" OMEGA_HOME="$REPO" PATH="$BIN:$PATH" \
        bash "$script" >/dev/null 2>&1
    if [ -s "$MARKER" ]; then echo "RESTARTED"; else echo "left-alone"; fi
}

W=deploy/omega-watchdog.sh
echo "=============================================================="
echo "C479: A SILENT PORT IS NOT A STUCK BOT"
echo "=============================================================="

echo
echo "1. THE PANEL ANSWERS (unchanged behaviour)"
ok "fresh scan -> leave it alone" \
   "$(run_case $W '{"ok":true,"last_scan_age_s":42.0}' 60)" "left-alone"
ok "stale scan -> restart" \
   "$(run_case $W '{"ok":true,"last_scan_age_s":9999.0}' 60)" "RESTARTED"
ok "no scan recorded yet -> leave it alone (no boot loop)" \
   "$(run_case $W '{"ok":true}' 60)" "left-alone"

echo
echo "2. THE PANEL IS SILENT -- THE CASE C479 IS ABOUT"
ok "silent panel + FRESH log -> the bot is alive, DO NOT restart" \
   "$(run_case $W '' 60)" "left-alone"
ok "silent panel + log written 29 min ago -> still inside the limit" \
   "$(run_case $W '' 1740)" "left-alone"

echo
echo "3. A REAL WEDGE IS STILL CAUGHT"
ok "silent panel + log stale 31 min -> restart" \
   "$(run_case $W '' 1860)" "RESTARTED"
ok "silent panel + log stale 6 hours -> restart" \
   "$(run_case $W '' 21600)" "RESTARTED"

echo
echo "4. NOTHING WRITTEN YET"
ok "silent panel + no report log at all -> leave it alone" \
   "$(run_case $W '' '')" "left-alone"

echo
echo "5. THE OPERATOR IS TOLD WHICH OF THE TWO IT WAS"
run_case $W '' 60 >/dev/null
if grep -qi "ALIVE, NOT restarting" "$WORK/wlog"; then
    echo "  PASS  it says the bot is alive and names the port as the suspect"; PASS=$((PASS+1))
else
    echo "  FAIL  the syslog line does not explain the situation:"; cat "$WORK/wlog"; FAIL=$((FAIL+1))
fi

echo
echo "6. NEGATIVE CONTROL: THE PREVIOUS WATCHDOG MUST FAIL THIS"
OLD="$WORK/old-watchdog.sh"
if git show HEAD:deploy/omega-watchdog.sh > "$OLD" 2>/dev/null && [ -s "$OLD" ]; then
    if grep -q 'C479' "$OLD"; then
        echo "  FAIL  HEAD already contains C479 -- this test can no longer fail"; FAIL=$((FAIL+1))
    else
        ok "pre-C479 restarts the healthy bot (the bug)" \
           "$(run_case $OLD '' 60)" "RESTARTED"
        ok "  ...and it agreed with the new one on a real wedge" \
           "$(run_case $OLD '' 21600)" "RESTARTED"
    fi
else
    echo "  FAIL  could not read the previous watchdog from git"; FAIL=$((FAIL+1))
fi

echo
echo "=============================================================="
if [ "$FAIL" -eq 0 ]; then echo "ALL $PASS CHECKS PASSED"; exit 0
else echo "$FAIL FAILURE(S) out of $((PASS+FAIL))"; exit 1; fi
