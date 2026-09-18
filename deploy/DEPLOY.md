# Running OMEGA in the cloud, 24×7

Plain English throughout. No server experience assumed.

---

## What you are building

```
   Your phone, anywhere in the world
              |
              |  https, encrypted, needs your token
              v
     Cloudflare Tunnel        (free, no ports opened on your server)
              |
              v
     A small Linux server that never sleeps
        |-- the bot, under systemd (auto-start, auto-restart)
        |-- the control panel on port 8138 (stop / resume / restart)
        \-- the log files, exactly as they are on your phone today
```

Nothing about how the bot works changes. It writes the same four files
(`omega_report_*.log`, `omega_session_*.log`, `omega_detail_*.log`,
`mode_v60.json`) to a folder, just as it does in Pydroid3.

**Time needed:** about 30 minutes, most of it waiting for downloads.
**Cost:** £0 on Oracle Cloud's Always Free tier.

---

## Step 1 — Get a free server (about 10 minutes)

1. Go to **cloud.oracle.com** and click *Start for free*.
2. Sign up. It asks for a card **to verify identity only** — the Always Free
   resources never charge. Choose a home region near you (Mumbai or
   Hyderabad if you are in India).
3. When you are in: **Menu → Compute → Instances → Create instance**.
4. Change three things and leave the rest alone:
   - **Image:** Canonical Ubuntu 24.04
   - **Shape:** click *Change shape* → **Ampere** → `VM.Standard.A1.Flex`
     → set **1 OCPU** and **6 GB memory**. (This is inside the free
     allowance. The bot needs far less, but the headroom is free.)
   - **SSH keys:** choose *Generate a key pair for me* and **download
     the private key**. You cannot download it again later.
5. Click **Create**. After a minute you get a **Public IP address**. Write
   it down.

> **If it says "Out of capacity"** — this happens on free ARM shapes. Either
> try a different availability domain from the same page, or try again in a
> few hours. If it keeps failing, Hetzner's CX22 is €4/month and takes two
> minutes: **hetzner.com/cloud** → new project → Ubuntu 24.04 → CX22.

---

## Step 2 — Log in to it (2 minutes)

On your computer:

```bash
chmod 600 ~/Downloads/ssh-key-*.key
ssh -i ~/Downloads/ssh-key-*.key ubuntu@<YOUR-PUBLIC-IP>
```

From an Android phone, install **Termius** (free) and add the server with
that key.

You should see a `ubuntu@...:~$` prompt. You are on the server.

---

## Step 3 — Install everything (5 minutes)

Copy the bot and this `deploy` folder up to the server first. From your
computer:

```bash
scp -i ~/Downloads/ssh-key-*.key -r omega_v60_reconstructed.py deploy \
    ubuntu@<YOUR-PUBLIC-IP>:~/
```

Then on the server:

```bash
sudo mkdir -p /home/omega/omega
sudo mv ~/omega_v60_reconstructed.py ~/deploy /home/omega/omega/
sudo bash /home/omega/omega/deploy/setup.sh
```

The script installs Python, creates a user called `omega`, builds a virtual
environment, installs `ccxt`, sets the timezone to IST, **generates your
control-panel token**, and installs the service and log rotation.

It prints your token at the end. Write it down. It is also kept in
`/etc/omega.token`.

---

## Step 4 — Start the bot

```bash
sudo systemctl enable --now omega     # start it, and start it at every boot
sudo systemctl status omega           # is it running?
sudo journalctl -u omega -f           # watch it live (Ctrl-C to stop watching)
```

From this moment it runs 24×7. If it crashes, systemd restarts it in 10
seconds. If the server reboots, it comes back on its own.

---

## Step 5 — Reach it from your phone

### The quick way (no domain, no account, good for testing)

On the server:

```bash
cloudflared tunnel --url http://localhost:8138
```

It prints a random address like `https://wide-mango-1234.trycloudflare.com`.
Open this on your phone:

```
https://wide-mango-1234.trycloudflare.com/?t=YOUR_TOKEN
```

The catch: the address changes every time you restart the tunnel, and it
stops when you close the SSH session.

### The permanent way (needs a domain name, about £8/year)

```bash
cloudflared tunnel login                              # opens a link, log in
cloudflared tunnel create omega
cloudflared tunnel route dns omega omega.yourdomain.com
sudo cloudflared service install
sudo systemctl enable --now cloudflared
```

Now `https://omega.yourdomain.com/?t=YOUR_TOKEN` works forever, from
anywhere, and survives reboots.

**Extra lock (recommended):** in the Cloudflare dashboard, go to
*Zero Trust → Access → Applications* and put the hostname behind a Google
login. Then even someone who steals the token cannot get in.

---

## What you can do from the panel

| Address | What it does |
|---|---|
| `/?t=TOKEN` | the dashboard — equity, positions, buttons |
| `/api/logs?file=report&n=200&t=TOKEN` | last 200 lines of the **report** log |
| `/api/logs?file=session&n=300&t=TOKEN` | the session log |
| `/api/logs?file=detail&n=400&t=TOKEN` | the full forensic log |
| `/api/files?t=TOKEN` | list every log and state file, with sizes |
| `/api/download?f=omega_report_...log&t=TOKEN` | download one file to your phone |
| `/api/health?t=TOKEN` | how long since the last scan |
| `/api/status?t=TOKEN` | equity, mode, open positions as JSON |

Buttons (POST): `/api/pause`, `/api/resume`, `/api/stop`, `/api/scan`,
`/api/restart`.

Everything you have on the phone today is here, plus reading the logs and
downloading files over the internet.

---

## Everyday commands

| I want to… | Type this |
|---|---|
| see if it is running | `sudo systemctl status omega` |
| watch it live | `sudo journalctl -u omega -f` |
| stop it | `sudo systemctl stop omega` |
| start it | `sudo systemctl start omega` |
| restart it | `sudo systemctl restart omega` |
| stop it restarting at boot | `sudo systemctl disable omega` |
| update the bot | `scp` the new file up, then `sudo systemctl restart omega` |
| see the report log | `tail -f /home/omega/omega/omega_report_*.log` |
| check disk space | `df -h` |

---

## Optional: the watchdog

systemd restarts the bot when the **process** dies. It cannot see a bot that
is still alive but has stopped scanning — a wedged network call, a dead
thread. That failure is worse, because nothing tells you.

```bash
sudo cp /home/omega/omega/deploy/omega-watchdog.sh /usr/local/bin/
sudo chmod +x /usr/local/bin/omega-watchdog.sh
echo '*/5 * * * * root /usr/local/bin/omega-watchdog.sh' | sudo tee /etc/cron.d/omega-watchdog
```

Every five minutes it asks the bot when it last scanned. If that is more
than 30 minutes ago it restarts the service and writes a line to the system
log. It deliberately does **not** restart when no scan has happened yet,
because that is normal just after a start and would cause a boot loop.

---

## Security — read this before you go live

While you are on paper money, nothing is at risk. Before you put real keys
on this machine:

1. **Never put the token or API keys in the Python file.** That file goes to
   git. They belong in `/etc/systemd/system/omega.service`, which the setup
   script already sets to mode 600 (root only).
2. **The bot refuses to be unsafe by default.** With no `OMEGA_CTRL_TOKEN`
   set, the control panel binds to `127.0.0.1` only and cannot be reached
   from the network at all. It only opens to `0.0.0.0` once a token exists.
3. **Bitget key permissions:** enable trading, **disable withdrawals**, and
   set the IP allow-list to your server's public IP.
4. **Never open port 8138 in the firewall.** The Cloudflare tunnel makes an
   outbound connection; nothing needs to be open inbound. If you opened a
   port you would be exposing the panel to the whole internet.
5. **Keep the server updated:** `sudo apt update && sudo apt upgrade -y`,
   once a month.

---

## One real benefit beyond uptime

The container where this code is developed is **geo-blocked from Binance and
Bybit**. That is why the taker-flow and open-interest channels (C464) ship
*unmeasured* — they could not be backtested.

**A server in Europe or India is not geo-blocked.** Once the bot runs there,
those two channels become measurable for the first time, and they are two of
the three remaining levers that could produce genuine edge. To me this is a
bigger reason to move than the 24×7 uptime is.

---

## If something goes wrong

| Symptom | What to do |
|---|---|
| `systemctl status omega` says *failed* | `sudo journalctl -u omega -n 50` shows the last 50 lines — the error is there |
| panel says "token required" | you left `?t=YOUR_TOKEN` off the address |
| panel does not load at all | `sudo systemctl status cloudflared`; the tunnel is down |
| "no space left on device" | `df -h`, then `sudo logrotate -f /etc/logrotate.d/omega` |
| bot runs but never trades | normal — see the report log; most scans find nothing |
| lost the token | `sudo cat /etc/omega.token` |
