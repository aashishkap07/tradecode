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

5. **STOP HERE. Do the networking FIRST, on its own, before you touch the
   instance form.** A brand-new Oracle tenancy has no network at all, so the
   *Virtual cloud network* dropdown is empty and *Subnet* shows a red
   **Required**.

   The obvious move — switching those radio buttons to *Create new virtual
   cloud network* / *Create new public subnet* — **does not work**, and this
   is the trap. The instance wizard's inline network builder is a
   reduced-functionality path: it cannot verify that a subnet it has not
   created yet is public, so **"Automatically assign public IPv4 address"
   stays greyed out forever**, still showing *"You must select a public
   subnet to assign a public IPv4 address."* The *Subnet IPv4 prefixes*
   dropdown stays empty for the same reason. Oracle says so itself, in a
   warning on that very page:

   > *"There are additional options available when you use the Networking
   > pages in the console. To have the full range of options, Create a VCN
   > and Create a Subnet and then select an existing VCN and subnet when you
   > create a compute instance."*

   So **cancel out of the instance form** and build the network separately:

   - **☰ menu → Networking → Virtual cloud networks**
   - check the compartment selector on the left says your root compartment
   - **Start VCN Wizard** (in newer consoles, under an **Actions** button)
   - choose **"Create VCN with Internet Connectivity"** → *Start VCN Wizard*

   | Field | Value |
   |---|---|
   | VCN name | `omega-vcn` |
   | Compartment | your root compartment |
   | VCN CIDR block | `10.0.0.0/16` (leave it) |
   | Public subnet CIDR block | `10.0.0.0/24` (leave it) |
   | Private subnet CIDR block | `10.0.1.0/24` (leave it) |

   **Next** → **Create**, and wait for every line to go green. This builds the
   VCN, a **public** subnet, a private subnet, an internet gateway, route
   tables and security rules — everything the inline path could not. It also
   opens port 22, so SSH works with no further firewall work. None of it
   costs anything on the free tier.

   Now go back to **☰ → Compute → Instances → Create instance** and set the
   Networking step to the **opposite** of the inline path:

   | Section | Choose |
   |---|---|
   | **Primary network** | **Select existing virtual cloud network** |
   | Virtual cloud network | `omega-vcn` — now present in the dropdown |
   | **Subnet** | **Select existing subnet** |
   | Subnet | **`Public Subnet-omega-vcn`** |

   ⚠️ The wizard made **two** subnets. Pick the one with **Public** in the
   name. Choosing the private one puts you straight back to a greyed-out
   toggle.

   - **Private IPv4 address:** leave on *Automatically assign*.
   - **Public IPv4 address:** the warning is now gone and the toggle works.
     **Turn it ON.** Without a public IP the server has no address on the
     internet and **you can never log in** — and it cannot be added to an
     instance that was built without one. You would have to terminate it and
     start over.
   - **IPv6:** leave off.

6. **SSH keys:** choose *Generate a key pair for me*, then **Download
   private key** AND **Download public key**.

   > Do not leave this page until both are saved. Oracle will not show
   > them again, and the private key is the only way into the machine.

   > **If you already downloaded a key on an earlier attempt, that key is
   > dead.** Each run of this form generates a fresh pair, and only the pair
   > from the run that actually created the instance works. Delete the old
   > files. Two near-identical `.key` files in your Downloads folder, one of
   > which silently fails, is a miserable thing to debug at the SSH prompt.

7. Click **Create**. After a minute or two you get a **Public IP address**.
   Write it down.

> **If it says "Out of capacity"** — common on the free ARM shape, and not
> your mistake. In order: (a) go **Previous** to the shape step and pick a
> different **Availability Domain** (AD-1 / AD-2 / AD-3); (b) try again in a
> few hours; (c) give up on free and use Hetzner — CX22 is €4/month, takes
> two minutes, and has none of this networking:
> **hetzner.com/cloud** → new project → Ubuntu 24.04 → CX22.


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

**Updating later** takes two commands, not one:

```bash
sudo git config --global --add safe.directory /home/omega/omega   # once, ever
cd /home/omega/omega && sudo git pull
```

That first line is needed because `setup.sh` hands the folder to the `omega`
user while `sudo git pull` runs as `root`. Git refuses to operate on a
repository owned by somebody else and stops with *"detected dubious
ownership"*. Run it once and never think about it again — but without it the
pull fails silently in the middle of a list of pasted commands, and everything
after it runs against the old code.

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

## Step 4a — A trap that will cost you twenty minutes

**Never run the tunnel by typing it at the prompt.** `cloudflared tunnel --url
...` takes over the terminal. Anything you type or paste afterwards goes into
cloudflared, which ignores it — so your commands appear on screen, nothing
happens, and it looks as though the server is broken when in fact nothing was
ever run.

You can tell at a glance: **if your pasted commands have no `$` prompt in front
of them and produce no output, they did not run.**

Press **Ctrl+C** to get the prompt back, then use the service instead
(Step 5) so the terminal stays free.

The same applies to any long-running command. When in doubt, paste **one line
at a time** and wait for each to finish — five commands pasted together scroll
their errors past too fast to read, and the first failure makes the rest
meaningless.

---

## Step 4b — If the panel does not answer

The single most likely failure, and it looks alarming but usually is not:

```
dial tcp 127.0.0.1:8138: connect: connection refused
```
…and the browser shows **Bad gateway 502**, with Cloudflare ticked green and
your host marked with a red X.

**Read that literally.** Cloudflare reached your server perfectly. There is
simply nothing listening on port 8138 — so the tunnel is fine and the *bot* is
the problem. Check it:

```bash
sudo systemctl status omega          # active? or failed?
sudo journalctl -u omega -n 60       # the real error is in here
```

| What the journal says | What it means |
|---|---|
| `ModuleNotFoundError: No module named 'pandas'` | a dependency is missing — `sudo /home/omega/omega/venv/bin/pip install -r /home/omega/omega/requirements.txt` |
| `EOFError` around `input()` | the bot is asking a startup question and nothing can answer. `OMEGA_NONINTERACTIVE=1` is missing from the unit |
| `OMEGA CANNOT WRITE ITS STATE DIRECTORY` | `OMEGA_BASE_PATH` is outside `ReadWritePaths` — the message names the fix |
| `active (running)` and nothing obviously wrong | give it 30 seconds; it fetches the market list before opening the port. Then `curl -fsS "http://127.0.0.1:8138/api/health?t=$(sudo cat /etc/omega.token)"` |

The quickest single check that the bot itself is healthy, from the server:

```bash
curl -fsS "http://127.0.0.1:8138/api/health?t=$(sudo cat /etc/omega.token)"
```

If that answers, the bot is fine and the problem is the tunnel. If it does not,
the tunnel is fine and the problem is the bot.

---

## Step 5 — Reach it from your phone

### The quick way (no domain, no account, good for testing)

**Run it as a service, not by typing it at the prompt.** A tunnel started by
hand dies the moment you close the SSH session — the bot keeps running and the
way in vanishes, which looks exactly like a broken bot.

```bash
sudo systemctl enable --now cloudflared-quick
sudo journalctl -u cloudflared-quick | grep -o 'https://.*trycloudflare.com' | tail -1
```

That last command prints your address. Open on your phone:

```
https://<that-address>/?t=YOUR_TOKEN
```

Two catches, both the price of having no Cloudflare account: the address
**changes every time the tunnel restarts**, and Cloudflare states quick tunnels
carry no uptime guarantee. Fine for getting going; not where you want to stay.

### The permanent way (needs a domain name, about £8/year)

```bash
cloudflared tunnel login                              # opens a link, log in
cloudflared tunnel create omega
cloudflared tunnel route dns omega omega.yourdomain.com
sudo cloudflared service install
sudo systemctl enable --now cloudflared
sudo systemctl disable --now cloudflared-quick    # stop the random-address one
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
| 502 Bad gateway / "connection refused" on 8138 | the tunnel is fine, the bot is down. See Step 4b |
| panel worked, then stopped after you closed SSH | you started the tunnel by hand. `sudo systemctl enable --now cloudflared-quick` |
| pasted commands do nothing, no output, no prompt | the terminal is busy running something (usually cloudflared). Ctrl+C, then check you see a `$` before typing anything else |
| `git pull` says "detected dubious ownership" | `sudo git config --global --add safe.directory /home/omega/omega` |
| the tunnel address stopped working | a quick tunnel gets a new address on every restart. `sudo journalctl -u cloudflared-quick \| grep -o 'https://.*trycloudflare.com' \| tail -1` |
| equity reset to its starting value after a restart | the bot resumed before it had ever saved state. Only happens before the first closed trade, and knowledge files survive it |
| lost the token | `sudo cat /etc/omega.token` |
| cannot SSH in at all, "connection timed out" | the instance has no public IP. Check the instance page: if *Public IP* is blank you missed the toggle in Step 1.5. Terminate it and create a new one — it cannot be added afterwards |
| "Automatically assign public IPv4 address" is greyed out | you are on the instance wizard's inline network builder, which can never enable it. Build the VCN separately first — Step 1.5 |
| the subnet dropdown offers two subnets | pick the one with **Public** in the name |
| `Permission denied (publickey)` | wrong username (`ubuntu`, not `root`), or the key file needs `chmod 600` |
