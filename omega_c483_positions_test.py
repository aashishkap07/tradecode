#!/usr/bin/env python3
"""C483: the dashboard must show the positions the bot actually holds.

The panel read getattr(positions, '_positions', {}); PositionsManager keeps
them in .positions, so it ALWAYS said "none -- flat". On 23 Sep it said so while
the bot held three shorts worth $102.

Rule 16: the old panel test used a STUB container whose get_all() returned {},
so it could never have caught this. This one builds REAL Position objects in the
REAL PositionsManager and serves them through the REAL RemoteControl. Section 4
runs the pre-C483 endpoint from git against the same book and requires it to
report nothing.
"""
import os, sys, io, json, time, types, contextlib, importlib.util, subprocess, socket
import urllib.request, urllib.error
from datetime import datetime, timedelta
os.environ.setdefault('OMEGA_BASE_PATH', '/tmp/omega_c483_pos')
os.makedirs(os.environ['OMEGA_BASE_PATH'], exist_ok=True)
TOKEN = 'c483-positions-token-0123456789'
os.environ['OMEGA_CTRL_TOKEN'] = TOKEN
fails = []
def ok(n, c, d=''):
    print(f"  {'PASS' if c else 'FAIL'}  {n}" + (f"   {d}" if d else ''))
    if not c: fails.append(n)

def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    with contextlib.redirect_stdout(io.StringIO()):
        spec.loader.exec_module(m)
    return m

def free_port():
    s = socket.socket(); s.bind(('127.0.0.1', 0)); p = s.getsockname()[1]; s.close(); return p

def book(om):
    pm = om.PositionsManager()
    t0 = datetime.now() - timedelta(minutes=38)
    for sym, side, e, size, m in (('KERNEL/USDT:USDT', 'short', 0.05637, 620.5, 34.98),
                                  ('AVAX/USDT:USDT', 'short', 10.757, 3.2816, 35.30),
                                  ('BTC/USDT:USDT', 'long', 60000.0, 0.0005, 30.0)):
        p = om.Position(symbol=sym, side=side, entry_price=e, size=size, leverage=1,
                        strategy='momentum', initial_margin=m, confidence=0.6,
                        entry_fee=m * 0.0002, confluence_score=0.6, entry_time=t0)
        pm.add(p)
    pm.positions['AVAX/USDT:USDT']._partial_booked_pnl = 0.31
    return pm

MARKS = {'KERNEL/USDT:USDT': 0.05623, 'AVAX/USDT:USDT': 10.724, 'BTC/USDT:USDT': 60300.0}

def serve(om, pm):
    cfg = om.Config()
    bot = types.SimpleNamespace(cfg=cfg,
        portfolio=types.SimpleNamespace(positions=pm, equity=252.81, get_live_equity=lambda *a: 252.95,
                                        get_stats=lambda *a: {'live_equity': 252.95}),
        mode_mgr=types.SimpleNamespace(mode=types.SimpleNamespace(value='normal'),
                                       session_start_equity=252.81, _day_start_equity=254.98),
        exchange=types.SimpleNamespace(get_current_price=lambda s: MARKS.get(s)))
    port = free_port()
    rc = om.RemoteControl(bot, port=port)
    rc.start(); time.sleep(0.6)
    return rc, port

def get(port, path):
    try:
        with urllib.request.urlopen(f'http://127.0.0.1:{port}{path}', timeout=6) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, {}

print("=" * 64); print("C483: THE PANEL SHOWS THE POSITIONS THE BOT HOLDS"); print("=" * 64)
om = load('/home/user/tradecode/omega_v60_reconstructed.py', 'om483')
pm = book(om)
rc, port = serve(om, pm)

print("\n1. THE ENDPOINT")
c, d = get(port, f'/api/positions?t={TOKEN}')
ps = d.get('positions', [])
ok("three held positions come back as three", c == 200 and len(ps) == 3, f"HTTP {c} n={len(ps)} {d.get('error','')}")
byk = {p['symbol']: p for p in ps}
k = byk.get('KERNEL', {})
ok("  margin is the real initial_margin", k.get('margin') == 34.98, f"{k.get('margin')}")
ok("  age is computed, not a TypeError", k.get('age_min') is not None and 37 <= k['age_min'] <= 39, f"{k.get('age_min')} min")
ok("  a short that fell is IN PROFIT", (k.get('move_pct') or 0) > 0 and (k.get('pnl') or 0) > 0,
   f"move {k.get('move_pct')}%  pnl ${k.get('pnl')}")
ok("  the mark price is shown", k.get('mark') == MARKS['KERNEL/USDT:USDT'])
ok("  a split position shows what it already banked", byk.get('AVAX', {}).get('banked') == 0.31)
b = byk.get('BTC', {})
ok("  a long that rose is in profit too", (b.get('move_pct') or 0) > 0, f"{b.get('move_pct')}%")

print("\n2. THE STATUS COUNT")
c, st = get(port, f'/api/status?t={TOKEN}')
ok("status reports 3 open, not 0", c == 200 and st.get('positions') == 3, f"positions={st.get('positions')}")

print("\n3. THE SAME NUMBERS AS THE TEXT REPORT'S TABLE")
p0 = pm.positions['KERNEL/USDT:USDT']; px = MARKS['KERNEL/USDT:USDT']
mv = p0.get_price_move_pct(px); val = p0.size * p0.entry_price
net = (mv / 100.0) * val - p0.entry_fee - (p0.size * px) * (om.Config().TAKER_FEE_PCT / 100.0)
ok("panel P&L == the report table's formula", abs(k.get('pnl', 0) - round(net, 2)) < 1e-9, f"{k.get('pnl')} vs {net:.4f}")

print("\n4. NEGATIVE CONTROL: THE PRE-C483 ENDPOINT, FROM GIT")
def _git(*a):
    return subprocess.run(['git', *a], capture_output=True, text=True, cwd='/home/user/tradecode').stdout
intro = _git('log', '--format=%H', '-S', 'THE PANEL HAS NEVER SHOWN A SINGLE OPEN POSITION', '--',
             'omega_v60_reconstructed.py').split()
ref = (intro[-1] + '^') if intro else 'HEAD'
old_src = _git('show', f'{ref}:omega_v60_reconstructed.py')
if 'THE PANEL HAS NEVER SHOWN A SINGLE OPEN POSITION' in old_src:
    ok("the pre-C483 source can be rebuilt", False, f"{ref} already has the fix")
else:
    tmp = '/tmp/omega_pre483.py'; io.open(tmp, 'w', encoding='utf-8').write(old_src)
    om_old = load(tmp, 'om_pre483')
    rc2, port2 = serve(om_old, book(om_old))
    c, d = get(port2, f'/api/positions?t={TOKEN}')
    ok("pre-C483 reports ZERO positions for the same three-position book",
       c == 200 and d.get('positions') == [], f"{d}")
print("\n" + "=" * 64)
print("ALL CHECKS PASSED" if not fails else f"{len(fails)} FAILURE(S): {fails}")
sys.exit(1 if fails else 0)
