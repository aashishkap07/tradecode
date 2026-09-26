#!/usr/bin/env python3
"""C482-C: the report block shows what the bot HOLDS before anything else.

Renders the real _C462Report.status() with two open positions, then flat, and
checks the order of rows. Also checks the new DAY / MONTH rows read the guard.
"""
import os, sys, types, importlib.util, io, contextlib
os.environ.setdefault('OMEGA_BASE_PATH', '/tmp/omega_c482_layout')
os.makedirs(os.environ['OMEGA_BASE_PATH'], exist_ok=True)
spec = importlib.util.spec_from_file_location('om', '/home/user/tradecode/omega_v60_reconstructed.py')
om = importlib.util.module_from_spec(spec)
with contextlib.redirect_stdout(io.StringIO()):
    spec.loader.exec_module(om)
fails = []
def ok(n, c, d=''):
    print(f"  {'PASS' if c else 'FAIL'}  {n}" + (f"   {d}" if d else ''))
    if not c: fails.append(n)

class P:
    def __init__(s, side, e, size): s.side = side; s.entry_price = e; s.size = size; s.entry_fee = 0.01; s.leverage = 1
    def get_price_move_pct(s, px): return (px / s.entry_price - 1) * 100 * (1 if s.side == 'long' else -1)
    def get_age_seconds(s): return 1260
    def _c443_uei(s, cfg): return (0.45, None)
G = {'pct': 15.0, 'month_eq0': 250.0, 'month_budget': 37.5, 'month_used': 0.0, 'month_left': 37.5,
     'day0': 250.0, 'day_cap': 9.38, 'day_used': 0.15, 'day_left': 9.23, 'day_pnl': -0.15,
     'min_room': 0.26, 'halt': ''}
def render(pos, width, guard=G, capped=''):
    R = om._C462Report(os.path.join(os.environ['OMEGA_BASE_PATH'], 'r.log'))
    if hasattr(R, 'set_width'): R.set_width(width)
    out = []; R._emit = lambda line='', *a, **k: out.append(str(line))
    pf = types.SimpleNamespace(positions=types.SimpleNamespace(get_all=lambda: pos, count=lambda: len(pos)),
        equity=250.03, get_live_equity=lambda *a: 250.21,
        get_stats=lambda *a: {'live_equity': 250.21, 'locked': 46.72 if pos else 0.0,
                              'available': 203.13, 'unrealized': 0.18 if pos else 0.0, 'win_rate': 0},
        lifetime_trades=0, session_start_equity=250.0)
    bot = types.SimpleNamespace(portfolio=pf, cfg=om.Config(),
        exchange=types.SimpleNamespace(get_current_price=lambda s: {'MON/USDT:USDT': 0.02336,
                                                                   'WIF/USDT:USDT': 0.19720}[s]),
        _c467_day_barrier=lambda: {'limit': guard['day_cap'] or 1e-6, 'used': guard['day_used'],
                                   'frac': guard['day_used'] / (guard['day_cap'] or 1e-6),
                                   'pnl': guard['day_pnl'], 'day0': 250.0, 'capped': capped, 'guard': guard},
        mode_mgr=types.SimpleNamespace(mode=types.SimpleNamespace(value='normal')))
    R.status(bot)
    return [l for l in out if l.strip()]
def idx(lines, pfx):
    for i, l in enumerate(lines):
        if l.lstrip().startswith(pfx): return i
    return None

print("=" * 62); print("C482-C: OPEN POSITIONS FIRST"); print("=" * 62)
two = {'MON/USDT:USDT': P('short', 0.02345, 1000), 'WIF/USDT:USDT': P('short', 0.1971, 120)}
print("\n1. WIDE SCREEN, TWO POSITIONS")
L = render(two, 96)
i_eq, i_open, i_mon, i_sess, i_scan = (idx(L, 'EQUITY'), idx(L, 'OPEN'), idx(L, 'MON '),
                                       idx(L, 'SESSION'), idx(L, 'FEES'))
ok("OPEN is the row right after EQUITY", i_open == i_eq + 1, f"EQUITY@{i_eq} OPEN@{i_open}")
ok("the position rows come before SESSION", i_mon is not None and i_mon < i_sess, f"MON@{i_mon} SESSION@{i_sess}")
ok("  and before FEES / SCAN / MARKET", i_mon < i_scan)
print("\n2. PHONE WIDTH (the two-line stanza layout)")
L = render(two, 46)
i_open, i_sess = idx(L, 'OPEN'), idx(L, 'SESSION')
mon = next((i for i, l in enumerate(L) if 'MON' in l and 'SHORT' in l), None)
ok("positions still come before SESSION at 46 columns", mon is not None and i_open < mon < i_sess,
   f"OPEN@{i_open} MON@{mon} SESSION@{i_sess}")
print("\n3. FLAT")
L = render({}, 96)
ok("'OPEN flat' is right after EQUITY", idx(L, 'OPEN') == idx(L, 'EQUITY') + 1)
ok("  and no empty table is drawn", idx(L, 'PAIR') is None)
print("\n4. THE DAY AND MONTH ROWS READ THE C482 GUARD")
L = render(two, 96)
day = L[idx(L, 'DAY')]; mon = L[idx(L, 'MONTH')] if idx(L, 'MONTH') is not None else ''
ok("DAY shows the fixed limit, not vol/trust", 'limit $9.38' in day and 'vol x' not in day, day.strip())
ok("MONTH shows the dial and the month used", 'dial 15%' in mon and 'of $37.50' in mon, mon.strip())
Gh = dict(G, halt='day', day_used=9.4)
L = render(two, 96, Gh, capped='day')
ok("a halted day says NOT TRADING on the DAY row", 'NOT TRADING' in L[idx(L, 'DAY')], L[idx(L, 'DAY')].strip())
print("\n" + "=" * 62)
print("ALL CHECKS PASSED" if not fails else f"{len(fails)} FAILURE(S): {fails}")
sys.exit(1 if fails else 0)
