#!/usr/bin/env bash
# C480: the log archive must never lose bytes.
#
# logrotate runs copytruncate DAILY on omega_session_* and omega_detail_*: it
# copies the file aside and truncates the original to ZERO. The push script
# then mirrored those zero bytes over the good copy on GitHub. Thirteen 19-Sep
# session logs -- 323 KB, the only decision record for that day -- were
# destroyed exactly this way, and the branch is force-pushed so its history
# could not help either.
#
# Rule 16: section 5 runs the same case against the PREVIOUS script's `cp -f`
# and requires the data to be destroyed. If section 5 passes, this is not a test.
set -uo pipefail
cd "$(dirname "$0")"
SCRIPT=deploy/omega-logpush.sh

P=0; F=0
ok(){ if [ "$2" = "$3" ]; then echo "  PASS  $1"; P=$((P+1));
      else echo "  FAIL  $1   expected '$3', got '$2'"; F=$((F+1)); fi; }

W="$(mktemp -d)"; trap 'rm -rf "$W"' EXIT
warn(){ :; }; logger(){ :; }
copied=0

# Lift keep() out of the SHIPPED script -- testing a copy would test nothing.
KEEPSRC="$(sed -n '/^keep() {/,/^}$/p' "$SCRIPT")"
if [ -z "$KEEPSRC" ]; then echo "  FAIL  could not extract keep() from $SCRIPT"; exit 1; fi
eval "$KEEPSRC"

echo "=============================================================="
echo "C480: A ROTATED (TRUNCATED) LOG MUST NOT ERASE THE ARCHIVE"
echo "=============================================================="

WT="$W/wt"; SRC="$W/src"; mkdir -p "$WT/logs" "$SRC"

echo
echo "1. THE REAL CASE: 90 KB ON THE BRANCH, 0 BYTES ON DISK"
head -c 90149 /dev/zero | tr '\0' 'x' > "$WT/logs/omega_session_20260919_003314.log"
: > "$SRC/omega_session_20260919_003314.log"          # logrotate truncated it
keep "$SRC/omega_session_20260919_003314.log"
ok "the 90 KB archive survives" \
   "$(stat -c %s "$WT/logs/omega_session_20260919_003314.part01.log" 2>/dev/null || echo MISSING)" "90149"
ok "  and the restarted (empty) file is kept alongside it" \
   "$(stat -c %s "$WT/logs/omega_session_20260919_003314.log" 2>/dev/null || echo MISSING)" "0"

echo
echo "2. ORDINARY GROWTH STILL OVERWRITES"
printf 'aaaa' > "$WT/logs/grow.log"
printf 'aaaabbbb' > "$SRC/grow.log"
keep "$SRC/grow.log"
ok "a larger file replaces the archived one" "$(stat -c %s "$WT/logs/grow.log")" "8"
ok "  and no part file is made for normal growth" \
   "$(ls "$WT/logs"/grow.part*.log 2>/dev/null | wc -l)" "0"

echo
echo "3. A FILE THE ARCHIVE HAS NEVER SEEN"
printf 'hello' > "$SRC/brand_new.log"
keep "$SRC/brand_new.log"
ok "is simply copied" "$(stat -c %s "$WT/logs/brand_new.log")" "5"

echo
echo "4. ROTATED TWICE ON DIFFERENT DAYS -> TWO PARTS, NOTHING LOST"
printf '111111' > "$WT/logs/twice.log"; printf '1' > "$SRC/twice.log"; keep "$SRC/twice.log"
printf '222222222' > "$WT/logs/twice.log"; printf '2' > "$SRC/twice.log"; keep "$SRC/twice.log"
ok "part01 holds the first day" "$(stat -c %s "$WT/logs/twice.part01.log")" "6"
ok "part02 holds the second"    "$(stat -c %s "$WT/logs/twice.part02.log")" "9"
tot=$(( $(stat -c %s "$WT/logs/twice.part01.log") + $(stat -c %s "$WT/logs/twice.part02.log") + $(stat -c %s "$WT/logs/twice.log") ))
ok "  every byte is still on disk (6+9+1)" "$tot" "16"

echo
echo "5. NEGATIVE CONTROL: THE PREVIOUS SCRIPT MUST DESTROY IT"
OLDWT="$W/old"; mkdir -p "$OLDWT/logs"
head -c 90149 /dev/zero | tr '\0' 'x' > "$OLDWT/logs/omega_session_20260919_003314.log"
if git show HEAD:deploy/omega-logpush.sh 2>/dev/null | grep -q 'cp -f "\$f" "\$WT/logs/"'; then
    cp -f "$SRC/omega_session_20260919_003314.log" "$OLDWT/logs/"     # what it did
    ok "pre-C480 'cp -f' zeroes the 90 KB archive" \
       "$(stat -c %s "$OLDWT/logs/omega_session_20260919_003314.log")" "0"
    ok "  ...and leaves no copy behind" \
       "$(ls "$OLDWT/logs"/*part* 2>/dev/null | wc -l)" "0"
else
    echo "  FAIL  HEAD no longer contains the old cp -f -- this test can no longer fail"; F=$((F+1))
fi

echo
echo "=============================================================="
if [ "$F" -eq 0 ]; then echo "ALL $P CHECKS PASSED"; exit 0
else echo "$F FAILURE(S) of $((P+F))"; exit 1; fi
