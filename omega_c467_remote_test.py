#!/usr/bin/env python3
"""C467-D: run the control panel for real and attack it.

Standing rule 21: a module-level block must be EXECUTED, not merely parsed.
A panel that is about to be exposed to the internet must be shown to REFUSE,
not merely shown to compile.
"""
import ast, io, os, re, sys, tempfile, threading, time, types, urllib.request, urllib.error

SRC = '/home/user/tradecode/omega_v60_reconstructed.py'
src = io.open(SRC, encoding='utf-8').read()
fails = []
def ok(n, c, d=''):
    print(f"  {'PASS' if c else 'FAIL'}  {n}" + (f"   {d}" if d else ''))
    if not c: fails.append(n)

tmp = tempfile.mkdtemp(prefix='omega467_')
REPORT  = os.path.join(tmp, 'omega_report_20260918_005533.log')
SESSION = os.path.join(tmp, 'omega_session_20260918_005533.log')
DETAIL  = os.path.join(tmp, 'omega_detail_20260918_005533.log')
STATE   = os.path.join(tmp, 'mode_v60.json')
for p, n in ((REPORT, 40), (SESSION, 60), (DETAIL, 80)):
    io.open(p, 'w').write('\n'.join(f"{os.path.basename(p)} line {i}" for i in range(n)))
io.open(STATE, 'w').write('{"mode":"normal"}')
io.open(os.path.join(tmp, 'SECRET_not_an_omega_file.txt'), 'w').write('do not serve me')

TOKEN = 'test-token-do-not-use-in-production-0123456789'
os.environ['OMEGA_CTRL_TOKEN'] = TOKEN

# lift RemoteControl out with the globals it closes over
node = next(n for n in ast.parse(src).body
            if isinstance(n, ast.ClassDef) and n.name == 'RemoteControl')
g = {'os': os, 'time': time, 'threading': threading, 'sys': sys, 're': re,
     'json': __import__('json'),
     'datetime': __import__('datetime').datetime,
     'logger': types.SimpleNamespace(info=lambda *a: None, warning=lambda *a: None,
                                     debug=lambda *a: None, report=lambda *a: None),
     '_C462_REPORT_PATH': REPORT, '_C52_LOG_PATH': SESSION,
     '_C460_DETAIL_PATH': DETAIL,
     '_c462_report': types.SimpleNamespace(last_scan={'t': time.time() - 42.0},
                                           n_scans=75, t0=time.time() - 3600)}
exec(compile(ast.Module(body=[node], type_ignores=[]), '<rc>', 'exec'), g)

class Cfg:
    C467_CTRL_AUTH = True; C467_CTRL_TAIL_MAX = 400; PAPER_MODE = True
class Pos:
    def get_all(self): return {}
    def count(self): return 0
bot = types.SimpleNamespace(
    cfg=Cfg(),
    portfolio=types.SimpleNamespace(equity=251.34, positions=Pos(),
                                    get_live_equity=lambda *a: 252.11,
                                    get_stats=lambda *a: {'live_equity': 252.11}),
    mode_mgr=types.SimpleNamespace(mode=types.SimpleNamespace(value='normal'),
                                   _day_start_equity=250.0),
    exchange=None)

PORT = 18138
rc = g['RemoteControl'](bot, port=PORT)
rc.start()
time.sleep(0.7)

def get(path, timeout=6):
    try:
        with urllib.request.urlopen(f'http://127.0.0.1:{PORT}{path}', timeout=timeout) as r:
            return r.status, r.read().decode('utf-8', 'replace')
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode('utf-8', 'replace')
    except Exception as e:
        return 0, f'{type(e).__name__}: {e}'

def post(path, timeout=6):
    req = urllib.request.Request(f'http://127.0.0.1:{PORT}{path}', data=b'', method='POST')
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode('utf-8', 'replace')
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode('utf-8', 'replace')
    except Exception as e:
        return 0, f'{type(e).__name__}: {e}'

print("\n1. THE SERVER IS ACTUALLY LISTENING")
c, b = get(f'/api/health?t={TOKEN}')
ok("it answers", c == 200, f"HTTP {c}")

print("\n2. IT REFUSES WITHOUT THE TOKEN  (this is the whole point)")
for p in ('/', '/api/status', '/api/positions', '/api/health', '/api/logs',
          '/api/files', '/api/download?f=mode_v60.json'):
    c, _ = get(p)
    ok(f"GET {p[:34]:<34} -> 401", c == 401, f"got {c}")
for p in ('/api/pause', '/api/resume', '/api/stop', '/api/scan', '/api/restart'):
    c, _ = post(p)
    ok(f"POST {p:<33} -> 401", c == 401, f"got {c}")

print("\n3. A WRONG TOKEN IS STILL A REFUSAL")
for bad in ('', 'x', TOKEN[:-1], TOKEN + 'x', TOKEN.upper()):
    c, _ = get(f'/api/status?t={bad}')
    ok(f"token {bad[:18]!r:<22} -> 401", c == 401, f"got {c}")

print("\n4. WITH THE TOKEN, EVERYTHING WORKS")
c, b = get(f'/api/health?t={TOKEN}')
ok("health reports the scan age", c == 200 and '"last_scan_age_s"' in b, b[:90])
ok("  and it is the REAL age, not a placeholder", '42' in b, b[:90])
c, b = get(f'/api/status?t={TOKEN}')
ok("status returns JSON", c == 200 and b.strip().startswith('{'), f"HTTP {c}")
c, b = get(f'/api/logs?file=report&n=5&t={TOKEN}')
ok("report log tails exactly 5 lines", c == 200 and len(b.splitlines()) == 5,
   f"{len(b.splitlines())} lines")
ok("  and they are the LAST 5", 'line 39' in b and 'line 35' in b
   and 'line 34' not in b, b.replace('\n', ' | ')[:80])
for which, marker in (('session', 'omega_session'), ('detail', 'omega_detail')):
    c, b = get(f'/api/logs?file={which}&n=3&t={TOKEN}')
    ok(f"{which} log tails (the path was WIRED, not guessed)",
       c == 200 and marker in b, b[:60])
c, b = get(f'/api/logs?file=report&n=99999&t={TOKEN}')
ok("a huge n is clamped to C467_CTRL_TAIL_MAX", len(b.splitlines()) <= 400,
   f"{len(b.splitlines())} lines")
c, b = get(f'/api/files?t={TOKEN}')
ok("files lists the logs and the state file", c == 200 and 'mode_v60.json' in b
   and 'omega_report' in b)
ok("  and does NOT list unrelated files", 'SECRET_not_an_omega_file' not in b)

c, b = get(f'/?t={TOKEN}')
ok("the dashboard page itself loads", c == 200 and '<button' in b, f"HTTP {c}")
ok("  and its JavaScript carries the token on every call",
   b.count("+T()") >= 3 and 'function T()' in b,
   f"{b.count('+T()')} tokenised fetches")

print("\n5. DOWNLOAD, AND THE PATH-TRAVERSAL GUARD")
c, b = get(f'/api/download?f=omega_report_20260918_005533.log&t={TOKEN}')
ok("a real log downloads", c == 200 and 'line 0' in b, f"HTTP {c}")
for evil in ('../../../../etc/passwd', '..%2f..%2fetc%2fpasswd', '/etc/passwd',
             'SECRET_not_an_omega_file.txt', '....//etc/passwd',
             'omega_report_20260918_005533.log/../../../etc/passwd'):
    c, b = get(f'/api/download?f={evil}&t={TOKEN}')
    ok(f"refuses {evil[:36]:<36}", c == 404 and 'root:' not in b, f"HTTP {c}")

print("\n6. THE BUTTONS QUEUE REAL COMMANDS")
for path, key in (('/api/pause', 'pause'), ('/api/resume', 'resume'),
                  ('/api/scan', 'force_scan')):
    rc._commands.clear()
    c, b = post(f'{path}?t={TOKEN}')
    ok(f"{path:<14} queues {key}", c == 200 and rc._commands.get(key) is True,
       f"HTTP {c} {dict(rc._commands)}")
rc._commands.clear()
c, b = post(f'/api/restart?t={TOKEN}')
ok("/api/restart asks for BOTH restart and stop", c == 200
   and rc._commands.get('restart') and rc._commands.get('stop'), f"{dict(rc._commands)}")
ok("  and check_commands consumes it as a stop", rc.check_commands() == 'stop')
ok("  ...then pops the restart flag with a log line",
   rc.check_commands() is None and 'restart' not in rc._commands)

c, b = post(f'/api/not-a-real-command?t={TOKEN}')
ok("an unknown POST route is a 404, not a 200 with an error in it", c == 404,
   f"HTTP {c} {b[:50]}")

print("\n7. WITH NO TOKEN THE PANEL MUST NOT REACH THE NETWORK")
os.environ.pop('OMEGA_CTRL_TOKEN', None)
rc2 = g['RemoteControl'](bot, port=PORT + 1)
rc2.start(); time.sleep(0.5)
addr = rc2._server.server_address[0] if rc2._server else None
ok("it binds to 127.0.0.1, never 0.0.0.0", addr == '127.0.0.1', f"bound to {addr}")
ok("  and the earlier tokened server DID bind 0.0.0.0",
   rc._server.server_address[0] == '0.0.0.0', f"{rc._server.server_address[0]}")

print("\n" + "=" * 62)
print("ALL CHECKS PASSED" if not fails else f"{len(fails)} FAILURE(S): {fails}")
sys.exit(1 if fails else 0)
