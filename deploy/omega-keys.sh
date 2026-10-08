#!/usr/bin/env bash
# C540 (B1): put an exchange's API key into data/api_keys.json WITHOUT it ever appearing on screen, in the
# shell history, in a process list or in chat.
#
#   sudo -u omega bash /home/omega/omega/deploy/omega-keys.sh delta_india
#   sudo -u omega bash /home/omega/omega/deploy/omega-keys.sh pi42
#   sudo -u omega bash /home/omega/omega/deploy/omega-keys.sh coindcx     (C542)
#
# It asks for the key and the secret with hidden typing (paste them; nothing is shown), merges them into
# api_keys.json under that section (other sections are kept), writes the file readable by its owner only
# (chmod 600) and prints only how many characters it saved. Run it as the omega user so the bot can read it.
set -uo pipefail
VENUE="${1:-}"
case "$VENUE" in
    delta_india|pi42|coindcx) ;;
    *) echo "usage: sudo -u omega bash $0 delta_india|coindcx|pi42"; exit 2 ;;
esac
FILE="${OMEGA_BASE_PATH:-/home/omega/omega/data}/api_keys.json"
umask 077
read -r -s -p "$VENUE API key (paste, then Enter; nothing is shown): " K; echo
read -r -s -p "$VENUE API secret (paste, then Enter; nothing is shown): " S; echo
if [ -z "$K" ] || [ -z "$S" ]; then echo "nothing saved: the key or the secret was empty"; exit 1; fi
OMEGA_K="$K" OMEGA_S="$S" OMEGA_V="$VENUE" OMEGA_F="$FILE" python3 - <<'PY'
import json, os
f, v = os.environ['OMEGA_F'], os.environ['OMEGA_V']
d = {}
if os.path.exists(f):
    try:
        d = json.load(open(f))
    except Exception:
        raise SystemExit(f"{f} exists but is not valid JSON -- nothing changed; fix or move it first")
d[v] = {'api_key': os.environ['OMEGA_K'].strip(), 'api_secret': os.environ['OMEGA_S'].strip()}
tmp = f + '.tmp'
fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
with os.fdopen(fd, 'w') as h:
    json.dump(d, h, indent=1)
os.chmod(tmp, 0o600)
os.replace(tmp, f)
print(f"saved {v}: key {len(d[v]['api_key'])} characters, secret {len(d[v]['api_secret'])} characters -> {f} (chmod 600)")
PY
unset K S
