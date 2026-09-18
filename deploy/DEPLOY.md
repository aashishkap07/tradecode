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
4. Change these and leave everything else alone:
   - **Image:** Canonical Ubuntu 24.04
   - **Shape:** click *Change shape* → **Ampere** → `VM.Standard.A1.Flex`
     → set **1 OCPU** and **6 GB memory**. Check it says
     *Always Free-eligible*. (The bot needs far less, but the headroom
     is free.)

5. **NETWORKING — this is where a new account gets stuck.** A brand-new
   Oracle tenancy has **no network at all**, so the *Virtual cloud network*
   dropdown is empty and the *Subnet* box shows a red **Required**. You are
   being asked to choose from a list of zero things. Do not try to fill
   those dropdowns — switch both radio buttons instead:

   | Section | Change it to | Then |
   |---|---|---|
   | **Primary network** | **Create new virtual cloud network** | name it `omega-vcn`, leave the CIDR at `10.0.0.0/16` |
   | **Subnet** | **Create new public subnet** | name it `omega-subnet`, leave the CIDR at `10.0.0.0/24` |

   The word **public** in "Create new public subnet" is load-bearing. A
   private subnet cannot have a public IP, and without a public IP you can
   never log in.

   - **Private IPv4 address:** leave it on *Automatically assign*.
   - **Public IPv4 address:** ⚠️ **turn the toggle ON.** Until you have
     created the public subnet above, this toggle is greyed out and warns
     *"You must select a public subnet to assign a public IPv4 address."*
     Once the subnet is set, the warning clears and the toggle works.
     **If you leave this off, the server has no address on the internet
     and is unreachable. You would have to delete it and start again.**
   - **IPv6:** leave off.

6. **SSH keys:** choose *Generate a key pair for me*, then **Download
   private key** AND **Download public key**.

   > Do not leave this page until both are saved. Oracle will not show
   > them again, and the private key is the only way into the machine.

7. Click **Create**. After a minute or two you get a **Public IP address**.
   Write it down.

> **If it says "Out of capacity"** — common on the free ARM shape, and not
> your mistake. In order: (a) go **Previous** to the shape step and pick a
> different **Availability Domain** (AD-1 / AD-2 / AD-3); (b) try again in a
> few hours; (c) give up on free and use Hetzner — CX22 is €4/month, takes
> two minutes, and has none of this networking:
> **hetzner.com/cloud** → new project → Ubuntu 24.04 → CX22.

> **Prefer to set the network up separately?** It is fewer controls per
> screen, which helps on a phone. Cancel out, go to
> **Menu → Networking → Virtual Cloud Networks → Start VCN Wizard →
> "Create VCN with Internet Connectivity"**, accept every default, then
> start the instance again and pick that VCN from the dropdown — it will
> no longer be empty.

---

## Step 2 — Log in to it (2 minutes)

On your computer:

```bash
chmod 600 ~/Downloads/ssh-key-*.key
ssh -i ~/Downloads/ssh-key-*.key ubuntu@<YOUR-PUBLIC-IP>
```

**From an Android phone** (no computer needed): install **Termius** from the
Play Store, then *New Host* → **Hostname** = your public IP → **Username** =
`ubuntu` → **Keys** → *import* the private key file you downloaded from
Oracle. Connect.

Note the username is `ubuntu` for an Ubuntu image. It is `opc` if you chose
Oracle Linux instead.

You should see a `ubuntu@...:~$` prompt. You are on the server.

---

## Step 3 — Install everything (5 minutes)

### The easy way: clone it from GitHub (works fine from a phone)

On the server:

```bash
sudo mkdir -p /home/omega
sudo git clone -b claude/trading-system-analysis-tsvzj4 \
     https://github.com/aashishkap07/tradecode.git /home/omega/omega
sudo bash /home/omega/omega/deploy/setup.sh
```

If the repository is private, git asks for a username and password. The
username is your GitHub username. The password is **not** your GitHub
password — it is a **Personal Access Token**:
github.com → *Settings* → *Developer settings* → *Personal access tokens* →
*Tokens (classic)* → *Generate new token* → tick **repo** → copy it.

Updating later is then one command: `cd /home/omega/omega && sudo git pull`.

### The other way: copy the files up from a computer

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
| cannot SSH in at all, "connection timed out" | the instance has no public IP. Check the instance page: if *Public IP* is blank you forgot the toggle in Step 1.5. It cannot be fixed from the instance page — terminate it and create a new one |
| `Permission denied (publickey)` | wrong username (`ubuntu`, not `root`), or the key file needs `chmod 600` |
