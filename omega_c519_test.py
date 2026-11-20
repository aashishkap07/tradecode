#!/usr/bin/env python3
"""C519: the book's plan holds only what the venue takes, and says so.

The first Binance paper rebalance (1 Oct 2026, 09:17 IST) logged "14 positions
targeted ... 14 trades" and the book held 12. The plan's floor was a flat $6,
and Binance's minimum order is $20 for ETH, LINK, LTC, BCH and ETC ($50 BTC):
two targets in between were refused by _fill's minimum check without a word,
and the loop counted every attempt as a trade.

1. Each coin's floor is max($6, the venue's minimum order); Bitget ($5 on all
   812 contracts) keeps $6.
2. A rebalance on Binance's minimums: targets under a coin's floor are out of
   the plan and named in the PLAN line; every plan target is held; the trade
   count is the fills.
3. A target that is still not held (step, status) is named with its reason,
   and is not counted as a trade.
4. The tournament and the K4 shadow use the same floors.
5. The saved inputs carry the floors and the venue; the replay tool reproduces
   the plan from them.
6. The venue switch: no stop sign when the fresh start is already chosen.
"""
import os, io, re, sys, json, time, types, logging, tempfile, subprocess, contextlib, importlib.util
import numpy as np
REPO = os.path.dirname(os.path.abspath(__file__))
BASE = tempfile.mkdtemp(prefix='c519_test_')
os.environ['OMEGA_BASE_PATH'] = BASE
fails = []


def ok(n, c, d=''):
    print(f"  {'PASS' if c else 'FAIL'}  {n}" + (f"   {d}" if d else ''))
    if not c:
        fails.append(n)


spec = importlib.util.spec_from_file_location('om519', os.path.join(REPO, 'omega_v60_reconstructed.py'))
om = importlib.util.module_from_spec(spec)
with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
    spec.loader.exec_module(om)
LOG = []
class _H(logging.Handler):
    def emit(self, r): LOG.append((r.levelno, r.getMessage()))
lg = logging.getLogger('OmegaV60'); lg.handlers = [_H()]; lg.propagate = False
print("=" * 66); print("C519: THE PLAN HOLDS WHAT THE VENUE TAKES"); print("=" * 66)
SRC = open(os.path.join(REPO, 'omega_v60_reconstructed.py')).read()


def market(n=430, k=60, seed=7):
    g = np.random.default_rng(seed)
    T = (np.arange(n) + 19000) * 86400000
    close = np.full((n, k), np.nan); qv = np.full((n, k), np.nan); fund = np.zeros((n, k))
    for j in range(k):
        a = int(g.integers(0, 150)); b = n
        drift = g.normal(0, 0.004, size=n).cumsum() * 0.02
        ret = drift + g.normal(0, 0.035, size=n)
        px = 10 ** g.uniform(-1, 3) * np.exp(np.cumsum(ret))
        close[a:b, j] = px[a:b]
        qv[a:b, j] = np.exp(g.normal(16 - 0.04 * j, 0.8, size=b - a))
        fund[a:b, j] = g.normal(0.0001, 0.0002, size=b - a) * 3
    return T, close, qv, fund


class PaperEx:
    """ExchangeManager's paper contract: a market order fills at the ask (buy) or bid (sell)"""
    def __init__(s):
        s.e, s.markets, s.orders = None, {}, []
    def place_order(s, sym, side, q, lev, typ, reduce_only=False, **kw):
        m = s.e.marks[sym]; px = m['ask'] if side == 'buy' else m['bid']
        s.orders.append((sym, side, q, px)); return {'id': 'p', 'price': px, 'filled': q, 'status': 'closed'}
    def c487_settle(s, sym, o, side, price, size, wait):
        return float(o['filled']), float(o['price']), 'filled'
    def get_current_price(s, sym):
        return None


T, close, qv, fund = market()
SYMS = [f"C{j:02d}/USDT:USDT" for j in range(close.shape[1])]


def mk(venue='binance', eq=500.0, mins=None, steps=None, status=None):
    """an engine on the given venue's rules: $5 minimum and a step of about $0.05 unless told otherwise"""
    cfg = om.Config(); cfg.PAPER_MODE = True; cfg.C380_MAX_MONTHLY_DD_PCT = 20.0; cfg.C488_ENGINE = 'portfolio'
    cfg.VENUE = venue
    for k, v in om._C516_VENUE_DEFAULTS.get(venue, {}).items():
        setattr(cfg, k, v)
    om._c467_cfg_ref[0] = cfg
    pf = om.Portfolio(cfg); pf.equity = pf.available_balance = eq
    ex = PaperEx()
    bot = types.SimpleNamespace(cfg=cfg, portfolio=pf, exchange=ex, _c462_state_settled=True,
                                _c408_asset_class=lambda s: 'crypto',
                                _c482_risk_guard=lambda: {'pct': 20.0, 'month_eq0': eq})
    e = om.C488Engine(bot); e.reset(); ex.e = e; pf._c488 = e
    bot.c501k = om.C501Allostatic(bot); bot.c501k.reset()
    bot.c510t = om.C510Tournament(bot); bot.c510t.reset()
    for j, s in enumerate(SYMS):
        px = float(close[-1, j])
        e.marks[s] = dict(bid=px * 0.9999, ask=px * 1.0001, last=px, fr=0.0001, vol=float(qv[-1, j]))
        st = (steps or {}).get(s) or float(10 ** np.floor(np.log10(0.5 / px)))
        e.rules[s] = dict(step=st, min_qty=st, min_usdt=float((mins or {}).get(s, 5.0)), max_mkt=1e12,
                          status=(status or {}).get(s, 'normal'), kind='COIN', sub='')
    e._marks_at = e._rules_at = time.time() + 1e6
    e.refresh_marks = lambda force=False: True
    e.refresh_rules = lambda force=False: True
    e.candidates = lambda n: SYMS
    e.matrices = lambda s: (T, SYMS, close, qv, fund)
    e.ohlc_for = lambda T_, k_: None
    return bot, e


def plan_line():
    return next((m for lv, m in LOG if 'C488 PLAN' in m), '')


print("\n1. EACH COIN'S FLOOR")
bot, e = mk()
e.rules['BTC/USDT:USDT'] = dict(step=0.001, min_qty=0.001, min_usdt=50.0, status='normal')
e.rules['ETH/USDT:USDT'] = dict(step=0.001, min_qty=0.001, min_usdt=20.0, status='normal')
ok("Binance: BTC $50, ETH $20 (the venue's minimum, above $6); a $5 coin keeps the $6 floor",
   e.floor('BTC/USDT:USDT') == 50.0 and e.floor('ETH/USDT:USDT') == 20.0 and e.floor('C00/USDT:USDT') == 6.0)
ok("  a coin missing from the table: $6 (the config's $5 minimum is under it)", e.floor('ZZZ/USDT:USDT') == 6.0)
bb, eb = mk('bitget')
ok("Bitget ($5 on all 812 contracts, read 1 Oct 2026): $6 everywhere, as before",
   all(eb.floor(s) == 6.0 for s in SYMS))

print("\n2. A REBALANCE ON BINANCE'S MINIMUMS")
# a first pass on $5 minimums finds the plan's smallest targets above $6
b0, e0 = mk()
e0.rebalance('first')
small = sorted([(abs(d['w']) * 500.0, s) for s, d in e0.plan.items() if abs(d['w']) * 500.0 < 18.0])
ok(f"the $5 plan has small targets to test with ({len(small)} under $18)", len(small) >= 2, str(small[:4]))
picked = [s for _, s in small[:2]]
mins = {s: 20.0 for s in picked}                     # as Binance's ETH, LINK, LTC, BCH, ETC
LOG.clear()
b1, e1 = mk(mins=mins)
e1.rebalance('first')
pl = plan_line()
ok("the coins with a $20 minimum and a smaller target are out of the plan",
   all(s not in e1.plan for s in picked) and len(e1.plan) == len(e0.plan) - 2,
   f"{len(e0.plan)} -> {len(e1.plan)}")
ok("  and the PLAN line names them with their floor ('under $6 or Binance's minimum ... < $20')",
   "or Binance's minimum" in pl and all(f"{s.split('/')[0]} " in pl.split('| under')[1] for s in picked)
   and pl.count('< $20') == 2, pl[pl.find('| under'):][:160])
held = [s for s in e1.plan if e1._qty(s) != 0.0]
ok("every plan target is held", len(held) == len(e1.plan), f"{len(held)} of {len(e1.plan)}")
reb = next((m for lv, m in LOG if 'C488 REBALANCE' in m), '')
nf = len(b1.exchange.orders)
ok(f"the trade count is the fills: '{len(e1.plan)} positions targeted ... {nf} trades'",
   e1.info['n_trades'] == nf and f"{len(e1.plan)} positions targeted" in reb and f", {nf} trades $" in reb
   and e1.info['not_held'] == 0, reb[:120])
ok("  and no 'targets not held' line when there are none", not any('not held' in m for lv, m in LOG))
ok("  every opening order meets its coin's minimum", all(q * px >= e1._min_usdt(s) for s, sd, q, px in b1.exchange.orders))

print("\n3. A TARGET STILL NOT HELD IS NAMED, WITH ITS REASON, AND IS NOT A TRADE")
names = sorted(e0.plan, key=lambda s: abs(e0.plan[s]['w']))
s_st, s_step = names[2], names[3]
px_step = e0.mark(s_step)
big_step = float(10 ** np.ceil(np.log10(3.0 * abs(e0.plan[s_step]['w']) * 500.0 / px_step)))   # one step > 2x the target
LOG.clear()
b2, e2 = mk(status={s_st: 'maintain'}, steps={s_step: big_step})
e2.rebalance('first')
miss = next((m for lv, m in LOG if 'not held' in m), '')
ok("a contract under maintenance: named, 'the contract is 'maintain''",
   f"{s_st.split('/')[0]} " in miss and "the contract is 'maintain'" in miss, miss[:200])
ok("a target that rounds to no step at all: named, 'its smallest order is ...'",
   f"{s_step.split('/')[0]} " in miss and 'its smallest order is' in miss)
ok(f"  '2 of {len(e2.plan)} targets not held', and the count of trades leaves both out",
   f"2 of {len(e2.plan)} targets not held" in miss and e2.info['n_trades'] == len(b2.exchange.orders)
   and e2.info['not_held'] == 2 and s_st not in e2.book and s_step not in e2.book)
ok("_fill's minimum check cannot hide a target any more: the rebalance checks the book after the loop",
   SRC.count("targets not held: ") == 1 and "n += 1 if x > 0 else 0" in SRC)

print("\n4. THE TOURNAMENT AND THE K4 SHADOW HOLD WHAT THE BOOK COULD")
t1 = b1.c510t
ok("the rebalance hands its floors to the tournament: no rule holds a coin under its floor",
   all(s not in w for w in t1.w.values() for s in picked) and len(t1.w) >= 5, str(sorted(t1.w)))
fl_all = {s: 1e9 for s in SYMS}
t1.observe(T, SYMS, close, qv, fund, None, 20, e1.target_vol(), 3.0, 500.0, floors=fl_all)
ok("  a floor above every target empties every rule's book", all(not w for w in t1.w.values()))
bk, ek = mk(mins=mins); bk.c510t = None            # K4 runs only when the tournament does not (C511)
ek.rebalance('first'); k1 = bk.c501k
ok("the K4 shadow (on when the tournament is off) uses the same floors",
   k1.active() and all(s not in k1.wb and s not in k1.wk for s in picked) and set(k1.wb) == set(ek.plan),
   f"{len(k1.wb)} vs {len(ek.plan)}")
ok("  without floors both keep the $6 floor (their callers before C519, and the tests)",
   'floors=None' in SRC and "fl.get(s, mn)" in SRC)

print("\n5. THE SAVED INPUTS CARRY THE FLOORS; THE REPLAY REPRODUCES THE PLAN")
LOG.clear(); b3, e3 = mk(mins=mins); e3.rebalance('first')
z = np.load(os.path.join(om.BASE_PATH, 'c488_inputs.npz'))
fz = {s: float(v) for s, v in zip([str(k) for k in z['keep']], z['floor'])}
other = next(s for s in SYMS if s not in picked)
ok("c488_inputs.npz has each coin's floor and the venue", 'floor' in z.files and str(z['venue'][0]) == 'binance'
   and all(fz[s] == 20.0 for s in picked) and fz[other] == 6.0, f"{len(fz)} floors")
inp = os.path.join(BASE, 'inputs_c519.npz')
import shutil; shutil.copy(os.path.join(om.BASE_PATH, 'c488_inputs.npz'), inp)
outj = os.path.join(BASE, 'replay.json')
env = dict(os.environ, OMEGA_BASE_PATH=tempfile.mkdtemp(prefix='c519_rp_'), OMEGA_BN_FAPI='http://127.0.0.1:9')
t0 = time.time()
rp = subprocess.run([sys.executable, os.path.join(REPO, 'research', 'c498_plan_replay.py'), '--dial', '20',
                     '--inputs', inp, '--out', outj], capture_output=True, text=True, timeout=600, env=env)
rows = json.load(open(outj))['rows'] if os.path.exists(outj) else []
rplan = {r['coin']: r['target'] for r in rows if r['in_plan']}
splan = {s.split('/')[0]: round(d['w'] * 500.0, 2) for s, d in e3.plan.items()}
ok(f"the replay's plan = the server's plan, coin for coin and to the cent ({len(rplan)} targets, {time.time() - t0:.0f} s)",
   rp.returncode == 0 and rplan == splan, (rp.stderr or rp.stdout)[-300:] if rplan != splan else '')
ok("  and it shows the two coins as 'no ($20)'",
   all(any(r['coin'] == s.split('/')[0] and not r['in_plan'] and r['floor'] == 20.0 for r in rows) for s in picked)
   and rp.stdout.count('no ($20)') == 2)

print("\n6. THE VENUE SWITCH")
p = os.path.join(om.BASE_PATH, 'c488_book.json')
bk = dict(book={'PEPE/USDT:USDT': dict(qty=-1655000.0, avg=4.26e-06, fees=0.004, funding=0.0, realized=0.0,
                                       opened=time.time())}, last_rebal='2026-09-30')
for fresh in (True, False):
    json.dump(bk, open(p, 'w'))
    cfg = om.Config(); cfg.PAPER_MODE = True; cfg.VENUE = 'binance'; cfg.C519_FRESH = fresh
    pf = om.Portfolio(cfg); pf.equity = 500.0
    b = types.SimpleNamespace(cfg=cfg, portfolio=pf, _c462_state_settled=True, _c408_asset_class=lambda s: 'crypto',
                              exchange=PaperEx(), _c482_risk_guard=lambda: {'pct': 20.0, 'month_eq0': 500.0})
    LOG.clear(); ev = om.C488Engine(b)
    stop = [m for lv, m in LOG if '\U0001f6d1 C516' in m]
    calm = [m for lv, m in LOG if 'starts fresh on Binance, so it begins flat' in m]
    if fresh:
        ok("a switch WITH a fresh start: one calm line, no stop sign", not stop and len(calm) == 1, (calm or stop or [''])[0])
        ev.reset()
        ok("  and the fresh start clears the block", not ev.venue_block)
    else:
        ok("a switch WITHOUT a fresh start: the stop sign, as before (blocked)", len(stop) == 1 and not calm
           and ev.venue_block)
ok("main() sets C519_FRESH before the bot is built", SRC.index("cfg.C519_FRESH = bool(fresh)") < SRC.index("    bot = TradingBot(cfg)\n"))
ok("version C519 or later", om._OMEGA_VERSION >= 'C519')

print("\n" + "=" * 66)
print(f"{len(fails)} FAILURE(S): {fails}" if fails else "ALL CHECKS PASSED")
sys.exit(1 if fails else 0)
