#!/usr/bin/env python3
"""C473: the fresh-or-resume choice, given back without a keyboard.

Also guards the defect this version nearly shipped: the dashboard page was
briefly returned from an undefined name with dead code after the return.
ast.parse is perfectly happy with that. Only serving it finds it.
"""
import ast, io, os, re, sys, time, types, threading, urllib.request, urllib.error

SRC = '/home/user/tradecode/omega_v60_reconstructed.py'
src = io.open(SRC, encoding='utf-8').read()
fails = []
def ok(n, c, d=''):
    print(f"  {'PASS' if c else 'FAIL'}  {n}" + (f"   {d}" if d else ''))
    if not c: fails.append(n)

print("\n1. THE VERSION STRING MOVES")
m = re.search(r"^_OMEGA_VERSION = '(C\d+)'", src, re.M)
ok("a version is defined", bool(m), m.group(1) if m else 'MISSING')
ok("  and it is no longer C469 (it sat there through C470/471/472)",
   bool(m) and m.group(1) != 'C469', m.group(1) if m else '')

print("\n2. THE FLAG IS CONSUMED, NOT JUST READ")
blk = src[src.index("_flag473 = os.path.join"):src.index("fresh = (choice != '2')")]
ok("the flag file is removed on use", "os.remove(_flag473)" in blk)
ok("  and a flag that cannot be cleared is REFUSED, not obeyed",
   "_forced473 = False" in blk.split("except Exception as _e473")[1],
   "obeying an unclearable flag would wipe the account on every restart")
ok("the dashboard writes the same file the shell would",
   "'FRESH_START'" in src and src.count("FRESH_START") >= 3)

print("\n3. SERVE THE PAGE AND DRIVE THE BUTTON")
os.environ['OMEGA_CTRL_TOKEN'] = 'tok473'
BASE = '/tmp/claude-0/c473base'
os.makedirs(BASE, exist_ok=True)
for f in ('FRESH_START',):
    try: os.remove(os.path.join(BASE, f))
    except OSError: pass
node = next(n for n in ast.parse(src).body
            if isinstance(n, ast.ClassDef) and n.name == 'RemoteControl')
g = {'os': os, 'time': time, 'threading': threading, 'sys': sys, 're': re,
     'json': __import__('json'), 'datetime': __import__('datetime').datetime,
     'logger': types.SimpleNamespace(info=lambda *a: None, warning=lambda *a: None,
                                     debug=lambda *a: None),
     '_C462_REPORT_PATH': '/tmp/claude-0/r3.log', '_C52_LOG_PATH': '/tmp/claude-0/r3.log',
     '_C460_DETAIL_PATH': '/tmp/claude-0/r3.log',
     '_OMEGA_VERSION': m.group(1), 'BASE_PATH': BASE,
     '_c462_report': types.SimpleNamespace(last_scan={'t': time.time() - 9}, n_scans=5,
         n_analyses=99, t0=time.time() - 60,
         stats=lambda: {'n': 0, 'w': 0, 'l': 0, 'wr': 0, 'payoff': 0,
                        'expectancy': 0, 'breakeven_wr': 0},
         n_maker=0, n_taker=0, fees_maker=0, fees_taker=0, equity_curve=[])}
for blkname in ('_C466_PALETTES', '_C466_RESET', '_C466_STRIP', '_C466_TOKENS', '_C472_CLASS'):
    mm = re.search(r'^' + blkname + r'\s*=.*?(?=\n[A-Za-z_]\w*\s*=|\ndef |\nclass )', src, re.M | re.S)
    exec(compile(mm.group(0), blkname, 'exec'), g)
for fn in ('_c472_escape', '_c472_paint_html'):
    mm = re.search(rf'^def {fn}\(.*?(?=\n(?:def |class |_C4))', src, re.M | re.S)
    exec(compile(mm.group(0), fn, 'exec'), g)
exec(compile(ast.Module(body=[node], type_ignores=[]), '<rc>', 'exec'), g)
io.open('/tmp/claude-0/r3.log', 'w').write("  line\n")
class Cfg: C467_CTRL_AUTH = True; C467_CTRL_TAIL_MAX = 400; PAPER_MODE = True
class Pos:
    def get_all(self): return {}
    def count(self): return 0
bot = types.SimpleNamespace(cfg=Cfg(),
    portfolio=types.SimpleNamespace(equity=250, positions=Pos(), session_trades=0,
        session_wins=0, get_live_equity=lambda *a: 250,
        get_stats=lambda *a: {'live_equity': 250}),
    mode_mgr=types.SimpleNamespace(mode=types.SimpleNamespace(value='normal'),
        _day_start_equity=250, session_start_equity=250),
    exchange=None, _last_scan_time=time.time() - 9, _market_bias_resultant=0.1,
    _bot_start_time=time.time() - 60,
    _c467_day_barrier=lambda: {'pnl': 0, 'limit': 1.7, 'used': 0, 'frac': 0,
                               'vol': 1, 'trust': 1, 'capped': '', 'day0': 250})
rc = g['RemoteControl'](bot, port=18473); rc.start(); time.sleep(0.7)

def get(p):
    try:
        with urllib.request.urlopen(f'http://127.0.0.1:18473{p}', timeout=6) as r:
            return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()
    except Exception as e:
        return 0, f'{type(e).__name__}: {e}'
def post(p):
    req = urllib.request.Request(f'http://127.0.0.1:18473{p}', data=b'', method='POST')
    try:
        with urllib.request.urlopen(req, timeout=6) as r:
            return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()
    except Exception as e:
        return 0, f'{type(e).__name__}: {e}'

code, page = get('/?t=tok473')
ok("the dashboard page SERVES", code == 200 and '<button' in page,
   f"HTTP {code} {page[:70]}")
ok("  (this is what catches an undefined name after a return)", code == 200)
ok("the page is stamped with the serving version",
   f"var PAGEVER='{m.group(1)}'" in page,
   re.search(r"var PAGEVER='[^']*'", page).group(0) if 'PAGEVER' in page else 'MISSING')
ok("  and the placeholder is gone", '__PAGEVER__' not in page)
ok("the Start fresh button is present and marked dangerous",
   "cmd('fresh')" in page and 'danger' in page.split("cmd('fresh')")[0][-120:])

print("\n4. THE BUTTON ARMS THE FLAG")
flag = os.path.join(BASE, 'FRESH_START')
ok("no flag before", not os.path.exists(flag))
rc._commands.clear()
code, body = post('/api/fresh?t=tok473')
ok("POST /api/fresh succeeds", code == 200 and '"ok": true' in body.lower().replace('"ok":true','"ok": true'), f"{code} {body}")
ok("  the flag file now exists", os.path.exists(flag))
ok("  and a restart was requested",
   rc._commands.get('restart') and rc._commands.get('stop'), f"{dict(rc._commands)}")
code, _ = post('/api/fresh')
ok("  it still needs the token", code == 401, f"got {code}")

print("\n5. THE FLAG IS CONSUMED EXACTLY ONCE")
consume = src[src.index("_flag473 = os.path.join"):src.index("    if _forced473:")]
consume = re.sub(r'^    ', '', consume, flags=re.M)
ns = {'os': os, 'BASE_PATH': BASE, 'print': lambda *a, **k: None}
exec(compile(consume, 'c473', 'exec'), ns)
ok("first boot sees the flag", ns['_forced473'] is True)
ok("  and deletes it", not os.path.exists(flag))
ns2 = {'os': os, 'BASE_PATH': BASE, 'print': lambda *a, **k: None}
exec(compile(consume, 'c473', 'exec'), ns2)
ok("second boot does NOT start fresh again", ns2['_forced473'] is False,
   "a persistent flag would wipe the account on every reboot")

print("\n" + "=" * 62)
print("ALL CHECKS PASSED" if not fails else f"{len(fails)} FAILURE(S): {fails}")
sys.exit(1 if fails else 0)
