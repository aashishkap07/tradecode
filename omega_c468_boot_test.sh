#!/usr/bin/env bash
# C468: DOES THE BOT BOOT WITH NO STDIN AND OPEN ITS PORT?
#
# This is the test that did not exist, and its absence cost a whole evening.
# C467-D shipped a systemd unit for a program that calls input() five times
# before it opens port 8138, and imports into a directory the unit had made
# read-only. Both are invisible to every other check in the battery: the file
# parses, the AST is fine, the sweep is clean, the control panel passes its own
# tests when started by hand. Only actually running it headless finds them.
#
# Usage:   OMEGA_PY=/path/to/venv/bin/python bash omega_c468_boot_test.sh
# Passes when port 8138 answers /api/health within 60 seconds of a start with
# stdin closed.
cd /home/user/tradecode
export OMEGA_BASE_PATH=/tmp/claude-0/omegatest
export OMEGA_NONINTERACTIVE=1
export OMEGA_MODE=test
export OMEGA_CAPITAL=250
export OMEGA_MAX_DD=15
export OMEGA_CTRL_TOKEN=boot-test-token-1234567890
export OMEGA_LOG_WIDTH=100
# stdin closed, exactly as systemd gives it
timeout 90 "${OMEGA_PY:-python3}" omega_v60_reconstructed.py < /dev/null > /tmp/claude-0/omegatest/boot.log 2>&1 &
BOTPID=$!
for i in $(seq 1 60); do
    if curl -fsS --max-time 3 "http://127.0.0.1:8138/api/health?t=boot-test-token-1234567890" >/tmp/claude-0/omegatest/health.json 2>/dev/null; then
        echo "PORT 8138 OPEN after ${i}s"
        cat /tmp/claude-0/omegatest/health.json; echo
        kill $BOTPID 2>/dev/null; wait $BOTPID 2>/dev/null
        exit 0
    fi
    kill -0 $BOTPID 2>/dev/null || { echo "BOT DIED after ${i}s"; break; }
    sleep 1
done
kill $BOTPID 2>/dev/null; wait $BOTPID 2>/dev/null
echo "PORT NEVER OPENED"
exit 1
