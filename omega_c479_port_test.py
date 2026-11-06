#!/usr/bin/env python3
"""C479: the control panel must survive a busy port.

WHAT THIS PROTECTS. The panel is the operator's only remote stop button on a
box they cannot see. It binds :8138. On a real server the bind fails in ONE
ordinary situation: systemd restarts the bot while the old process still holds
the port. Before C479 that printed one warning line and the bot then traded on
FOREVER with no dashboard and no stop button, and never tried again.

Standing rule 5: a protection that fails quietly is not a protection.
Standing rule 16: a verification tool that cannot fail its own test is not a
tool -- so section 4 runs the SAME scenario against the pre-C479 behaviour and
requires it to stay dead. If section 4 ever passes, this file is lying.
"""
import ast, io, os, re, socket, sys, threading, time, types, urllib.request, urllib.error
from http.server import HTTPServer, BaseHTTPRequestHandler

SRC = '/home/user/tradecode/omega_v60_reconstructed.py'
raw = io.open(SRC, encoding='utf-8').read()

fails = []
def ok(n, c, d=''):
    print(f"  {'PASS' if c else 'FAIL'}  {n}" + (f"   {d}" if d else ''))
    if not c: fails.append(n)

TOKEN = 'test-token-do-not-use-in-production-0123456789'
os.environ['OMEGA_CTRL_TOKEN'] = TOKEN


def free_port():
    s = socket.socket()
    s.bind(('127.0.0.1', 0))
    p = s.getsockname()[1]
    s.close()
    return p


class Squatter:
    """A REAL listener, not a TIME_WAIT socket. HTTPServer already sets
    SO_REUSEADDR, so only a live listener actually refuses the bind -- and a
    live listener is exactly what an overlapping restart leaves behind."""
    def __init__(self, port):
        class H(BaseHTTPRequestHandler):
            def log_message(self, *a): pass
            def do_GET(self):
                self.send_response(200); self.end_headers(); self.wfile.write(b'squatter')
        self.srv = HTTPServer(('0.0.0.0', port), H)
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
    def release(self):
        self.srv.shutdown(); self.srv.server_close()


def load_remote_control(src_text, log_sink):
    """Lift RemoteControl out of the given source with the globals it closes over."""
    node = next(n for n in ast.parse(src_text).body
                if isinstance(n, ast.ClassDef) and n.name == 'RemoteControl')
    def rec(level):
        return lambda *a: log_sink.append((level, ' '.join(str(x) for x in a)))
    g = {'os': os, 'time': time, 'threading': threading, 'sys': sys, 're': re,
         'json': __import__('json'),
         'datetime': __import__('datetime').datetime,
         'logger': types.SimpleNamespace(info=rec('info'), warning=rec('warning'),
                                         error=rec('error'), debug=rec('debug'),
                                         report=rec('report')),
         '_C462_REPORT_PATH': '/dev/null', '_C52_LOG_PATH': '/dev/null',
         '_C460_DETAIL_PATH': '/dev/null',
         '_OMEGA_VERSION': 'C479', 'BASE_PATH': '/tmp',
         '_c462_report': types.SimpleNamespace(last_scan={'t': time.time() - 42.0},
                                               n_scans=75, t0=time.time() - 3600)}
    exec(compile(ast.Module(body=[node], type_ignores=[]), '<rc>', 'exec'), g)
    return g['RemoteControl']


class Cfg:
    C467_CTRL_AUTH = True; C467_CTRL_TAIL_MAX = 400; PAPER_MODE = True
    C479_CTRL_RETRY_S = 1          # 15s in production; 1s so this test is quick
class Pos:
    def get_all(self): return {}
    def count(self): return 0
def make_bot():
    return types.SimpleNamespace(
        cfg=Cfg(),
        portfolio=types.SimpleNamespace(equity=251.34, positions=Pos(),
                                        get_live_equity=lambda *a: 252.11,
                                        get_stats=lambda *a: {'live_equity': 252.11}),
        mode_mgr=types.SimpleNamespace(mode=types.SimpleNamespace(value='normal'),
                                       _day_start_equity=250.0),
        exchange=None)


def answers(port, path='/api/health'):
    try:
        with urllib.request.urlopen(
                f'http://127.0.0.1:{port}{path}?t={TOKEN}', timeout=4) as r:
            return r.status, r.read().decode('utf-8', 'replace')
    except Exception:
        return 0, ''


def wait_until(fn, limit=25.0, step=0.25):
    t0 = time.time()
    while time.time() - t0 < limit:
        if fn():
            return time.time() - t0
        time.sleep(step)
    return None


print("=" * 62)
print("C479: A BUSY PORT MUST NOT COST THE OPERATOR THE STOP BUTTON")
print("=" * 62)

RC = load_remote_control(raw, [])

# ── 1 ────────────────────────────────────────────────────────────────────
print("\n1. THE SCENARIO IS REAL: A LIVE LISTENER REFUSES THE BIND")
PORT = free_port()
squat = Squatter(PORT)
try:
    HTTPServer(('0.0.0.0', PORT), BaseHTTPRequestHandler)
    ok("a second bind on a held port raises EADDRINUSE", False, "it SUCCEEDED")
except OSError as e:
    ok("a second bind on a held port raises EADDRINUSE",
       getattr(e, 'errno', None) in (98, 48, 10048), f"errno {getattr(e,'errno',None)}")
ok("  and SO_REUSEADDR is already on, so this is not a TIME_WAIT story",
   HTTPServer.allow_reuse_address in (1, True), f"{HTTPServer.allow_reuse_address}")

# ── 2 ────────────────────────────────────────────────────────────────────
print("\n2. THE BOT SURVIVES IT, AND SAYS SO IN WORDS THE OPERATOR CAN USE")
log = []
rc = load_remote_control(raw, log)(make_bot(), port=PORT)
rc.start()
time.sleep(0.5)
ok("start() does not raise", True)
ok("the panel is NOT serving (the port really is held)", rc._server is None,
   f"_server={rc._server!r}")
errs = [m for lvl, m in log if lvl == 'error']
ok("it logs at ERROR, not one warning lost in the scroll", len(errs) >= 1,
   f"{len(errs)} error line(s)")
blob = ' '.join(errs).lower()
ok("  it says the BOT IS FINE (so nobody restarts a healthy bot)",
   'trading normally' in blob or 'is fine' in blob)
ok("  it says what was lost (the dashboard / stop button)",
   'stop' in blob and ('dashboard' in blob or 'panel' in blob))
ok("  it says it will come back by itself", 'by itself' in blob or 'retried' in blob)
ok("  it names the command that finds the culprit", 'ss -ltnp' in blob)

# ── 3 ────────────────────────────────────────────────────────────────────
print("\n3. WHEN THE PORT FREES UP, THE PANEL COMES BACK ON ITS OWN")
squat.release()
took = wait_until(lambda: rc._server is not None)
ok("the panel rebinds with NO restart and NO human", took is not None,
   f"after {took:.1f}s" if took else "never came back within 25s")

code, body = (0, '')
if took is not None:
    got = wait_until(lambda: answers(PORT)[0] == 200, limit=10)
    code, body = answers(PORT)
ok("  and it actually SERVES -- bound is not the same as working",
   code == 200 and '"last_scan_age_s"' in body, f"HTTP {code} {body[:60]}")
try:
    with urllib.request.urlopen(f'http://127.0.0.1:{PORT}/api/health', timeout=4) as r:
        untokened = r.status
except urllib.error.HTTPError as e:
    untokened = e.code
except Exception:
    untokened = 0
ok("  a tokenless request is still refused after recovery", untokened == 401,
   f"HTTP {untokened}")
infos = ' '.join(m for lvl, m in log if lvl == 'info').lower()
ok("  and the operator is TOLD it came back", 'control panel is back' in infos)

# ── 4 ── the negative control ────────────────────────────────────────────
print("\n4. NEGATIVE CONTROL: THE OLD BEHAVIOUR MUST FAIL THIS SAME TEST")
MARKER = "                threading.Thread(target=_retry479, daemon=True).start()"
if raw.count(MARKER) != 1:
    ok("the pre-C479 code can still be reconstructed", False,
       f"marker found {raw.count(MARKER)}x -- THIS TEST CAN NO LONGER FAIL, fix it")
else:
    old_src = raw.replace(MARKER, "                pass")
    PORT2 = free_port()
    squat2 = Squatter(PORT2)
    log2 = []
    rc_old = load_remote_control(old_src, log2)(make_bot(), port=PORT2)
    rc_old.start()
    time.sleep(0.5)
    ok("pre-C479 also fails to bind", rc_old._server is None)
    squat2.release()
    back = wait_until(lambda: rc_old._server is not None, limit=6)
    ok("pre-C479 NEVER recovers -- which is the bug C479 fixes",
       back is None, f"it recovered after {back}s" if back else "still dead after 6s")

# ── 5 ────────────────────────────────────────────────────────────────────
print("\n5. THE RETRY LOOP STOPS, AND CAN BE STOPPED")
PORT3 = free_port()
squat3 = Squatter(PORT3)
log3 = []
rc3 = load_remote_control(raw, log3)(make_bot(), port=PORT3)
rc3.start(); time.sleep(0.5)
live_before = threading.active_count()
rc3._stop479[0] = True
squat3.release()
still_dead = wait_until(lambda: rc3._server is not None, limit=4)
ok("_stop479 ends the retry loop (it does not run for the life of the process)",
   still_dead is None, "rebound anyway" if still_dead else "stayed stopped, as asked")
n_back = sum(1 for lvl, m in log if 'IS BACK' in m)
ok("the successful retry logs exactly once, then the loop exits",
   n_back == 1, f"{n_back} 'is back' line(s)")

print("\n" + "=" * 62)
print("ALL CHECKS PASSED" if not fails else f"{len(fails)} FAILURE(S): {fails}")
sys.exit(1 if fails else 0)
