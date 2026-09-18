#!/usr/bin/env bash
# OMEGA V60 — one-shot server setup  [C467-D]
#
# Run this ONCE on a fresh Ubuntu 22.04/24.04 server (Oracle Cloud Always Free,
# Hetzner, DigitalOcean — any of them). It does everything except the two things
# only you can do: choosing a token and logging in to Cloudflare.
#
#   curl -fsSL <this file> -o setup.sh && sudo bash setup.sh
#
# It is safe to run again; every step checks before it acts.

set -euo pipefail

OMEGA_USER="${OMEGA_USER:-omega}"
OMEGA_HOME="/home/${OMEGA_USER}/omega"
REPO="${OMEGA_REPO:-}"        # optional: a git URL to clone

say()  { printf '\n\033[1;36m==> %s\033[0m\n' "$*"; }
warn() { printf '\033[1;33m !! %s\033[0m\n' "$*"; }
die()  { printf '\033[1;31m !! %s\033[0m\n' "$*" >&2; exit 1; }

[ "$(id -u)" -eq 0 ] || die "run this with sudo"

say "1/8  System packages"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq python3 python3-venv python3-pip git curl ca-certificates \
                       logrotate tzdata >/dev/null
echo "    python3 $(python3 -V 2>&1 | cut -d' ' -f2)"

say "2/8  A user that is not root"
if ! id -u "$OMEGA_USER" >/dev/null 2>&1; then
    adduser --disabled-password --gecos "" "$OMEGA_USER" >/dev/null
    echo "    created user '$OMEGA_USER'"
else
    echo "    user '$OMEGA_USER' already exists"
fi
mkdir -p "$OMEGA_HOME"
chown -R "$OMEGA_USER:$OMEGA_USER" "/home/${OMEGA_USER}"

say "3/8  The bot itself"
if [ -n "$REPO" ] && [ ! -d "$OMEGA_HOME/.git" ]; then
    sudo -u "$OMEGA_USER" git clone "$REPO" "$OMEGA_HOME"
    echo "    cloned $REPO"
elif [ -f "$OMEGA_HOME/omega_v60_reconstructed.py" ]; then
    echo "    already present"
else
    warn "omega_v60_reconstructed.py is not in $OMEGA_HOME yet."
    warn "Copy it there, then run this script again:"
    warn "  scp omega_v60_reconstructed.py ${OMEGA_USER}@<server-ip>:${OMEGA_HOME}/"
fi

say "4/8  Python environment"
if [ ! -x "$OMEGA_HOME/venv/bin/python" ]; then
    sudo -u "$OMEGA_USER" python3 -m venv "$OMEGA_HOME/venv"
fi
sudo -u "$OMEGA_USER" "$OMEGA_HOME/venv/bin/pip" install -q --upgrade pip
# C468: PANDAS WAS MISSING HERE, AND IT IS A HARD IMPORT.
# The bot does `import pandas as pd` at module level, so without it the process
# dies at import, systemd restarts it, and it dies again -- and the only symptom
# the operator sees is "connection refused" on port 8138 from a tunnel that is
# working perfectly. Install from requirements.txt so there is ONE list, next to
# the code, instead of a second one buried in a shell script that drifts.
if [ -f "$OMEGA_HOME/requirements.txt" ]; then
    sudo -u "$OMEGA_USER" "$OMEGA_HOME/venv/bin/pip" install -q \
        -r "$OMEGA_HOME/requirements.txt" || \
        warn "some packages failed - check with: $OMEGA_HOME/venv/bin/pip check"
else
    warn "requirements.txt not found - installing the four hard dependencies directly"
    sudo -u "$OMEGA_USER" "$OMEGA_HOME/venv/bin/pip" install -q ccxt pandas numpy requests
fi

# Prove it. A dependency list that has never been imported is a guess.
say "4b/8  Checking the bot can actually import"
if sudo -u "$OMEGA_USER" "$OMEGA_HOME/venv/bin/python" -c \
     "import ccxt, pandas, numpy, requests" 2>/dev/null; then
    echo "    ccxt, pandas, numpy, requests all import cleanly"
else
    die "a hard dependency is still missing - run: $OMEGA_HOME/venv/bin/pip install -r $OMEGA_HOME/requirements.txt"
fi
if sudo -u "$OMEGA_USER" "$OMEGA_HOME/venv/bin/python" -c "import sklearn" 2>/dev/null; then
    echo "    scikit-learn present (ML features enabled)"
else
    warn "scikit-learn missing - the bot will run with ML features DISABLED"
fi

# The state directory, owned by the bot's user and inside ReadWritePaths.
sudo -u "$OMEGA_USER" mkdir -p "$OMEGA_HOME/data/data"
echo "    state directory: $OMEGA_HOME/data"

say "5/8  Timezone (so log timestamps match your clock)"
TZWANT="${OMEGA_TZ:-Asia/Kolkata}"
timedatectl set-timezone "$TZWANT" 2>/dev/null || warn "could not set timezone"
echo "    $TZWANT — $(date)"

say "6/8  The control-panel token"
TOKEN_FILE="/etc/omega.token"
if [ ! -f "$TOKEN_FILE" ]; then
    head -c 32 /dev/urandom | base64 | tr -d '/+=' | head -c 40 > "$TOKEN_FILE"
    chmod 600 "$TOKEN_FILE"
fi
TOKEN="$(cat "$TOKEN_FILE")"
echo "    token stored in $TOKEN_FILE (root only)"

say "7/8  The service"
SRC_UNIT="$(dirname "$0")/omega.service"
[ -f "$SRC_UNIT" ] || SRC_UNIT="$OMEGA_HOME/deploy/omega.service"
if [ -f "$SRC_UNIT" ]; then
    sed -e "s|CHANGE_ME_TO_A_LONG_RANDOM_STRING|${TOKEN}|" \
        -e "s|/home/omega/omega|${OMEGA_HOME}|g" \
        -e "s|^User=omega|User=${OMEGA_USER}|" \
        -e "s|^Group=omega|Group=${OMEGA_USER}|" \
        "$SRC_UNIT" > /etc/systemd/system/omega.service
    chmod 600 /etc/systemd/system/omega.service
    systemctl daemon-reload
    echo "    installed /etc/systemd/system/omega.service"
else
    warn "omega.service not found next to this script — skipping"
fi

SRC_TUN="$(dirname "$0")/cloudflared-quick.service"
[ -f "$SRC_TUN" ] || SRC_TUN="$OMEGA_HOME/deploy/cloudflared-quick.service"
if [ -f "$SRC_TUN" ]; then
    sed -e "s|^User=omega|User=${OMEGA_USER}|" \
        -e "s|^Group=omega|Group=${OMEGA_USER}|" \
        "$SRC_TUN" > /etc/systemd/system/cloudflared-quick.service
    systemctl daemon-reload
    echo "    installed /etc/systemd/system/cloudflared-quick.service"
fi

SRC_ROT="$(dirname "$0")/omega-logrotate.conf"
[ -f "$SRC_ROT" ] || SRC_ROT="$OMEGA_HOME/deploy/omega-logrotate.conf"
if [ -f "$SRC_ROT" ]; then
    sed -e "s|/home/omega/omega|${OMEGA_HOME}|g" \
        -e "s|su omega omega|su ${OMEGA_USER} ${OMEGA_USER}|" \
        "$SRC_ROT" > /etc/logrotate.d/omega
    echo "    installed /etc/logrotate.d/omega"
fi

say "8/8  Cloudflare Tunnel"
if ! command -v cloudflared >/dev/null 2>&1; then
    ARCH="$(dpkg --print-architecture)"
    curl -fsSL -o /tmp/cloudflared.deb \
      "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-${ARCH}.deb"
    dpkg -i /tmp/cloudflared.deb >/dev/null 2>&1 || apt-get -f install -y -qq
    rm -f /tmp/cloudflared.deb
fi
echo "    cloudflared $(cloudflared --version 2>&1 | head -1 || echo 'installed')"

cat <<EOF

────────────────────────────────────────────────────────────────
 DONE. Two things are left, and only you can do them.
────────────────────────────────────────────────────────────────

 1. START THE BOT
        sudo systemctl enable --now omega
        sudo systemctl status omega
        sudo journalctl -u omega -f          # watch it live

 2. OPEN IT TO THE INTERNET (free, no ports opened)

    No domain name? Start here. Runs as a service, so it survives
    you closing the SSH session:
        sudo systemctl enable --now cloudflared-quick
        sudo journalctl -u cloudflared-quick | \
             grep -o 'https://.*trycloudflare.com' | tail -1

    That prints your address. It CHANGES every time the tunnel
    restarts, which is the price of having no account.

    Have a domain? Then the address is permanent:
        cloudflared tunnel login             # opens a link; log in
        cloudflared tunnel create omega
        cloudflared tunnel route dns omega omega.<your-domain>
        sudo cloudflared service install
        sudo systemctl enable --now cloudflared
        sudo systemctl disable --now cloudflared-quick

 YOUR CONTROL-PANEL ADDRESS will be:
        https://<your tunnel address>/?t=${TOKEN}

 YOUR TOKEN (write it down — it is also in /etc/omega.token):
        ${TOKEN}

 Anyone with that address can pause, resume and stop your bot.
 Treat it exactly like a password.
────────────────────────────────────────────────────────────────
EOF
