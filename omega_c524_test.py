#!/usr/bin/env python3
"""C524: round 15's fixes and the cross-venue funding ledger.

1. The book fetches 160 candidates (8x its width) and the carry ledger 160 (4x its 40): on 2021-26
   the research's picks fell outside the old 80 on 4.2% (top 20) and 41% (top 40) of days.
2. One history fetch per coin per UTC day, shared by the book and the carry ledger.
3. The intraday shadow: each coin's SETTLED funding of the hour held (not the live rate at
   00/08/16 UTC only), its funding history refreshed every hour in one Binance call, and the venue's
   cost (Binance 0.05% + 0.02%) in the ledger and the gate.
4. C524CrossVenue: the pre-registered rule (7-day spread, in at 20%/yr, out under 10% or a sign
   change, 10 pairs, 10% a leg, whole Delta contracts, the Binance leg matched), costs on both legs,
   each leg's settled funding, marks; Binance only.
5. The page (Chromium).
"""
import os, io, sys, json, time, glob, types, socket, logging, tempfile, contextlib, importlib.util
import numpy as np
REPO = os.path.dirname(os.path.abspath(__file__))
BASE = tempfile.mkdtemp(prefix='c524_test_')
os.environ['OMEGA_BASE_PATH'] = BASE
TOKEN = 'c524-test-token-0123456789abcdef'
os.environ['OMEGA_CTRL_TOKEN'] = TOKEN
fails = []


def ok(n, c, d=''):
    print(f"  {'PASS' if c else 'FAIL'}  {n}" + (f"   {d}" if d else ''))
    if not c:
        fails.append(n)


spec = importlib.util.spec_from_file_location('om524', os.path.join(REPO, 'omega_v60_reconstructed.py'))
om = importlib.util.module_from_spec(spec)
with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
    spec.loader.exec_module(om)
LOG = []
class _H(logging.Handler):
    def emit(self, r): LOG.append((r.levelno, r.getMessage()))
lg = logging.getLogger('OmegaV60'); lg.handlers = [_H()]; lg.propagate = False
print("=" * 66); print("C524: CANDIDATE WIDTH, ONE FETCH A DAY, THE SHADOW'S FUNDING, CROSS-VENUE"); print("=" * 66)
SRC = open(os.path.join(REPO, 'omega_v60_reconstructed.py')).read()
ok("version C524 or later", int(om._OMEGA_VERSION[1:]) >= 524)
cfg = om.Config(); cfg.PAPER_MODE = True; cfg.VENUE = 'binance'; om._c467_cfg_ref[0] = cfg

# C530 changed the operator's allocation ($250 cross-venue, Pendle $100 in the plan, a $100 reserve); this
# test checks its own version's mechanics at the allocation it was written for (omega_c530_test.py checks C530's)
cfg.C524_XVENUE_EQUITY = 500.0; cfg.C527_PLAN = ('delta', 'xvenue'); cfg.C528_RESERVE = 200.0; cfg.C530_PENDLE = False
cfg.C521_DELTA_EQUITY = 500.0; cfg.C528_BUDGET = 1000.0; cfg.C531_XV_REBALANCE = False   # and C531's ($600, no reserve)
for _k, _v in om._C516_VENUE_DEFAULTS['binance'].items():      # the venue's own fees, as main() sets them
    setattr(cfg, _k, _v)
DAY = 86400000
today = int(time.time() * 1000) // DAY * DAY

print("\n1. THE CANDIDATE LISTS")
pf = om.Portfolio(cfg); pf.equity = 500.0
bot = types.SimpleNamespace(cfg=cfg, portfolio=pf, _c462_state_settled=True, _c408_asset_class=lambda s: 'crypto',
                            exchange=types.SimpleNamespace(markets={}), _c482_risk_guard=lambda: {'pct': 20.0})
e = om.C488Engine(bot); bot.c488 = e
e.marks = {f'C{j:03d}/USDT:USDT': dict(bid=1.0, ask=1.0, last=1.0, fr=0.0001, vol=1e9 - j) for j in range(300)}
ok("the book's candidate list is 8x its width: 160 at top 20 (was 80)", cfg.C488_CANDIDATE_MULT == 8 and len(e.candidates(20)) == 160)
ok("the carry ledger's is 4x its 40: 160 (was 2x, 80)", "e.candidates(P['topn'], mult=4)" in SRC
   and "e.candidates(P['topn'], mult=2)" not in SRC)

print("\n2. ONE HISTORY FETCH PER COIN PER DAY")
calls = []
def fake_bn_history(sym, days=330):
    calls.append((sym, days))
    out = {today - k * DAY: (1.0 + k, 1e6, 1.0, 1.1, 0.9) for k in range(1, days + 1)}
    return out, {today - k * 8 * 3600000: 0.0001 for k in range(1, 600)}
e._bn_history = fake_bn_history
o1, f1 = e._history('C001/USDT:USDT', 330)
o2, f2 = e._history('C001/USDT:USDT', 120)
ok("the carry ledger's read (120 days) after the book's (330) comes from the day's cache: one fetch",
   len(calls) == 1 and len(o1) == 330 and len(o2) == 120 and min(o2) == today - 120 * DAY and f2 == f1, str(calls))
o2[today - DAY] = 'changed'
ok("  and it hands out copies (a caller's edit does not reach the cache)", e._history('C001/USDT:USDT', 120)[0][today - DAY] != 'changed')
e._hist_cache['C001/USDT:USDT'] = (today - DAY,) + e._hist_cache['C001/USDT:USDT'][1:]
e._history('C001/USDT:USDT', 120)
ok("  a new UTC day fetches again", len(calls) == 2)
e._history('C002/USDT:USDT', 120); e._history('C002/USDT:USDT', 330)
ok("  a longer window than the cached one fetches again", len(calls) == 4, str(calls[-2:]))

print("\n3. THE INTRADAY SHADOW: SETTLED FUNDING, FRESH EVERY HOUR, THE VENUE'S COST")
ok("cost per unit of turnover: Binance 0.05% + 0.02% = 0.07%; Bitget 0.08% (the research's)",
   abs(om._c489_cost(cfg) - 0.0007) < 1e-12 and abs(om._c489_cost(types.SimpleNamespace(VENUE='bitget')) - 0.0008) < 1e-12)
ok("  the gate's 'beats the round trip' is twice it", "> 2 * _c489_cost(self.cfg)" in SRC and "> 2 * 0.0008" not in SRC)
sbot = types.SimpleNamespace(cfg=cfg, portfolio=pf, c488=types.SimpleNamespace(marks={}), _c462_state_settled=True)
sh = om.C489Shadow(sbot); sh.reset()
now_h = int(time.time() * 1000) // 3600000 * 3600000
bulk = []
def fake_bn_get(base, path, params, tries=3):
    bulk.append((path, dict(params)))
    if path == '/fapi/v1/fundingRate' and 'symbol' not in params:
        h = params['startTime'] + 60000
        return [dict(symbol='AUSDT', fundingTime=h, fundingRate='0.0003'), dict(symbol='ZZZUSDT', fundingTime=h, fundingRate='0.9')]
    return None
om._c516_bn_get = fake_bn_get
sh._fund_h = now_h - 3 * 3600000
sh._fund_fresh(['AUSDT', 'BUSDT'], now_h)
ok("every hour since the last: one bulk call each (all coins' settlements), the universe's coins kept",
   len(bulk) == 3 and all('symbol' not in q for _, q in bulk) and set(sh.fund) == {'AUSDT'}
   and len(sh.fund['AUSDT']) == 3 and sh._fund_h == now_h, f"{len(bulk)} calls, {sorted(sh.fund)}")
bulk.clear(); sh._fund_h = 0
sh._fund_fresh(['AUSDT'], now_h)
ok("  after a restart at most 48 hours back (the restart's own pull covers 31 days)", len(bulk) == 49)
def fail_get(base, path, params, tries=3):
    return None
om._c516_bn_get = fail_get; sh._fund_h = now_h - 2 * 3600000
sh._fund_fresh(['AUSDT'], now_h)
ok("  a failed call stops there and the next hour resumes from it", sh._fund_h == now_h - 2 * 3600000)
ok("the ledger charges events in [hour - 1 h, hour) from that history, not the live 'fr' at 00/08/16 UTC only",
   "settle = (datetime.utcfromtimestamp(now_h / 1000).hour % 8) == 0" not in SRC
   and "if h0 <= t // 3600000 * 3600000 < now_h" in SRC)

print("\n4. THE CROSS-VENUE LEDGER (paper)")
DSEC = today // 1000


class FakeDelta:
    """Delta's products, tickers and FUNDING records; each coin's rate per exchange (percent)"""
    def __init__(s):
        # coin: (Delta % per 4 h, Binance % per 8 h, contract value, price)
        s.c = {'HOT': (0.10, 0.01, 1.0, 2.0),          # Delta dearer for longs by ~+197%/yr  -> short Delta
               'COLD': (-0.05, 0.01, 1.0, 3.0),        # Delta cheaper: ~ -120%/yr           -> long Delta
               'MILD': (0.0080, 0.01, 1.0, 1.0),       # ~+6%/yr: below 20%, not entered
               'BIG': (0.10, 0.0, 1.0, 400.0),         # one contract $400 > a $50 leg
               'GAP': (0.10, 0.01, 1.0, 1.0)}          # Binance misses a day: no 7-day spread
        for j in range(20):                             # Delta lists far more; these are not on Binance
            s.c[f'ONLYD{j:02d}'] = (0.01, 0.0, 1.0, 1.0)
        s.px = {k: v[3] for k, v in s.c.items()}
    def __call__(s, path, params, tries=3):
        if path == '/v2/products':
            return [dict(symbol=k + 'USD', contract_value=str(v[2]), taker_commission_rate='0.0005',
                         product_specs=dict(rate_exchange_interval=14400, tags=['layer_1']), settling_asset={'symbol': 'USD'},
                         underlying_asset={'symbol': k}) for k, v in s.c.items()]
        if path == '/v2/tickers':
            return [dict(symbol=k + 'USD', mark_price=str(s.px[k])) for k in s.c]
        if path == '/v2/history/candles':
            k = params['symbol'].split(':')[1][:-3]
            st, en = int(params['start']), int(params['end'])
            first = -(-st // 14400) * 14400
            return [dict(time=t, close=s.c[k][0]) for t in range(first, en + 1, 3600)]       # forward-filled hourly
        return None


fdl = FakeDelta()
om._c521_get = fdl
def fake_bn(base, path, params, tries=3):
    if path == '/fapi/v1/fundingRate' and 'symbol' in params:
        k = params['symbol'][:-4]
        lo = params['startTime']
        out = []
        for t in range(-(-lo // (8 * 3600000)) * 8 * 3600000, lo + 9 * DAY, 8 * 3600000):
            if k == 'GAP' and today - 3 * DAY <= t < today - 2 * DAY:
                continue
            out.append(dict(fundingTime=t, fundingRate=str(fdl.c[k][1] / 100)))
        return out
    return None
om._c516_bn_get = fake_bn
ok("the Delta record rule: one value per exchange hour (forward-filled hours ignored), per UTC day",
   om._c524_delta_daily([dict(time=t, close=0.1) for t in range(DSEC - DAY // 1000, DSEC, 3600)], 14400, 0, DSEC)
   == {DSEC - DAY // 1000: 0.006})
xb = types.SimpleNamespace(cfg=cfg, portfolio=pf, _c462_state_settled=True, _c408_asset_class=lambda s: 'crypto',
                           exchange=types.SimpleNamespace(markets={}), _c482_risk_guard=lambda: {'pct': 20.0})
xe = om.C488Engine(xb); xb.c488 = xe
xe.marks = {k + '/USDT:USDT': dict(bid=v[3], ask=v[3], last=v[3], fr=0.0, vol=1e8) for k, v in fdl.c.items()
            if not k.startswith('ONLYD')}
xe.refresh_marks = lambda force=False: True
x = om.C524CrossVenue(xb); x.reset()
ok("Binance only: off on the Bitget venue", x.active() and not om.C524CrossVenue(types.SimpleNamespace(
    cfg=types.SimpleNamespace(VENUE='bitget'), portfolio=pf)).active())
x.run(now_ms=today + 30 * 60000)
P = x.pairs
sH = (0.10 * 6 - 0.01 * 3) / 100 * 365
ok("enters at a 7-day spread >= 20%%/yr: HOT short Delta / long Binance (+%.0f%%/yr), COLD long Delta / short Binance" % (100 * sH),
   set(P) == {'HOT', 'COLD'} and P['HOT']['side'] == 1 and P['COLD']['side'] == -1
   and abs(P['HOT']['s_entry'] - sH) < 1e-9, str({k: (v['side'], round(v['s_entry'], 3)) for k, v in P.items()}))
ok("  MILD (+6%/yr) is under the bar; GAP lacks a day on Binance; BIG's one contract ($400) is more than a $50 leg",
   'MILD' not in P and 'GAP' not in P and 'BIG' not in P and any(s_.startswith('BIG') for s_ in x.info['under_one_contract']),
   str(x.info))
h = P['HOT']
ok("  10% of $500 a leg in whole Delta contracts (25 x $2 = $50), the Binance leg matched; short Delta = negative contracts",
   h['d_qty'] == -25.0 and abs(h['b_qty'] - 25.0) < 1e-9 and P['COLD']['d_qty'] == 17.0 and P['COLD']['b_qty'] < 0)
cost0 = (50.0 + 51.0) * (om._C524_COST_B + om._C524_COST_D)
ok("  costs on both legs: Binance 0.07% + Delta 0.079% of each pair's notional", abs(x.fees - cost0) < 1e-9
   and abs(x.eq - (500.0 - cost0)) < 1e-9, f"fees {x.fees:.6f}")
# the next day: prices move together, funding settles
fdl.px['HOT'] = 2.2; xe.marks['HOT/USDT:USDT'].update(bid=2.2, ask=2.2, last=2.2)
eq_before = x.eq
x.last_run = ''
x.run(now_ms=today + DAY + 30 * 60000)
hD = sum(1 for t in range(today // 1000 + 3600, (today + DAY) // 1000, 3600) if (t // 3600) % 4 == 0)
hB = sum(1 for t in range(today + 8 * 3600000, today + DAY, 8 * 3600000))
fu_hot = 25 * 2.2 * 0.10 / 100 * hD - 25.0 * 2.2 * 0.01 / 100 * hB
fu_cold = -17 * 3.0 * (-0.05 / 100) * (hD + 1) * 0 + 0                     # computed below from the ledger's own rule
ok("each leg's SETTLED funding since it opened: HOT's short Delta collects 0.10%% at each of %d exchanges, its long Binance "
   "pays 0.01%% at %d; prices that move together cancel" % (hD, hB),
   abs(x.pairs['HOT']['funding'] - fu_hot) < 1e-9 and abs(x.pairs['HOT']['pnl'] - (-50.0 * (om._C524_COST_B + om._C524_COST_D)
                                                                                   + fu_hot)) < 1e-9,
   f"{x.pairs['HOT']['funding']:.6f} vs {fu_hot:.6f}")
ok("  the 00:00 exchange of the opening day is not collected (opened 00:30)", hD == 5)
f_day1 = x.pairs['HOT']['funding']
x.last_run = ''
x.run(now_ms=today + 2 * DAY + 30 * 60000)
fu_day2 = 25 * 2.2 * 0.10 / 100 * 6 - 25.0 * 2.2 * 0.01 / 100 * 3
ok("C525: the next full day collects all 6 of Delta's exchanges and all 3 of Binance's, 00:00 UTC included "
   "(C524 lost the 00:00 settlement every day after the first)",
   abs((x.pairs['HOT']['funding'] - f_day1) - fu_day2) < 1e-9, f"{x.pairs['HOT']['funding'] - f_day1:.6f} vs {fu_day2:.6f}")
ok("  Binance's funding history is asked for 1000 records (an hourly coin has 192 in 8 days)",
   "'startTime': lo * 1000, 'limit': 1000}" in SRC)
# the spread collapses on HOT: out, with costs
fdl.c['HOT'] = (0.002, 0.01, 1.0, 2.2)
x.last_run = ''
x.run(now_ms=today + 8 * DAY + 30 * 60000)
ok("out when the 7-day spread is under 10%/yr (and the costs of both legs are paid again)", 'HOT' not in x.pairs
   and any(c['coin'] == 'HOT' and 'under 10%' in c['why'] for c in x.closed), str(x.closed[-2:]))
fdl.c['COLD'] = (0.10, 0.01, 1.0, 3.0)
x.last_run = ''
x.run(now_ms=today + 16 * DAY + 30 * 60000)
ok("out when the spread changes sign (COLD: Delta became the dearer side) -- and, as the rule reads, back in the same day on "
   "the other side", any(c['coin'] == 'COLD' and 'sign' in c['why'] for c in x.closed) and x.pairs.get('COLD', {}).get('side') == 1,
   str(x.closed[-2:]))
st = x.status()
ok("status: equity, pairs, funding, price P&L, fees, the record", all(k in st for k in ('eq', 'pairs', 'funding', 'price_pnl',
                                                                                     'fees', 'record', 'next_run_utc')))
ok("C529: after entries, exits, funding and marks, the two venues' sides sum to the ledger's P&L exactly",
   abs(x.side['d'] + x.side['b'] - (x.eq - x.start_equity)) < 1e-9 and x.side['d'] != 0 and x.side['b'] != 0,
   f"{x.side} vs {x.eq - x.start_equity:+.6f}")
x.save(); x2 = om.C524CrossVenue(xb)
ok("saved and loaded", x2.eq == x.eq and set(x2.pairs) == set(x.pairs) and x2.trades == x.trades and x2.side == x.side)
ok("wired: created, ticked with the paper ledgers, reset on a fresh start, in the API, the status block, the boot line, "
   "the hourly log push", all(t in SRC for t in ("self.c524x = C524CrossVenue(self)", "self.c521d, self.c524x",
                                                 "bot.c524x.reset()", "_out469['c524']", "self._pack('XVENUE'",
                                                 "Delta vs Binance funding spread, both legs"))
   and 'c524_xvenue.json' in open(os.path.join(REPO, 'deploy', 'omega-logpush.sh')).read())

ok("C525: the tournament panel names a rule with no book yet ('not scored yet ... join at the next rebalance') instead of "
   "dropping it (2 Oct: 'rule tournament (9 rules)' above, 7 rows shown)",
   "notyet.push(v.label);return;" in SRC and "not scored yet (they join at the next rebalance" in SRC)
ok("C525: the cross-venue panel says it is marked, funded and traded once a day (a new pair shows only its costs until then)",
   "marked, funded and traded once a day at" in SRC)

ok("C526: a rule not yet scored reads 'new' in the status block and the tournament's log line, not '+0.00%'",
   "else 'new')   # C526" in SRC and "else 'new, scored from tomorrow')" in SRC)

print("\n5. THE PAGE (Chromium)")


def free_port():
    s_ = socket.socket(); s_.bind(('127.0.0.1', 0)); p_ = s_.getsockname()[1]; s_.close(); return p_


pfP = om.Portfolio(cfg); pfP.equity = pfP.available_balance = 500.0; pfP.session_start_equity = 500.0
pfP.positions = om.PositionsManager()
bP = types.SimpleNamespace(cfg=cfg, portfolio=pfP, _c462_state_settled=True, _c408_asset_class=lambda s: 'crypto',
                           exchange=types.SimpleNamespace(markets={}, get_current_price=lambda s: None),
                           _c482_risk_guard=lambda: {'pct': 20.0, 'month_eq0': 500.0, 'month_budget': 100.0,
                                                     'month_used': 0.0, 'day_cap': 25.0, 'day_used': 0.0, 'halt': ''})
eP = om.C488Engine(bP); eP.reset(); bP.c488 = eP; pfP._c488 = eP
bP.c489 = om.C489Shadow(bP); bP.c490 = om.C490Carry(bP); bP.c501s = om.C501Spot(bP); bP.c501v = om.C501Savings(bP)
bP.c501k = om.C501Allostatic(bP); bP.c510t = om.C510Tournament(bP); bP.c521b = om.C521Bfusd(bP); bP.c521d = om.C521Delta(bP)
bP._c504_data_health = lambda now=None: {'ok': True, 'bits': [], 'late': [], 'keys': []}
x.bot = xb
fbot = types.SimpleNamespace(cfg=cfg, portfolio=pfP, c488=eP, c501s=bP.c501s, c501v=bP.c501v, c501k=bP.c501k,
                             c489=bP.c489, c490=bP.c490, c510t=bP.c510t, c521b=bP.c521b, c521d=bP.c521d, c524x=x,
                             mode_mgr=types.SimpleNamespace(mode=types.SimpleNamespace(value='normal')), exchange=bP.exchange,
                             _c467_day_barrier=lambda: {'pnl': 0.0, 'limit': 9.0, 'used': 0.0, 'frac': 0.0},
                             _c482_risk_guard=bP._c482_risk_guard, _c504_data_health=bP._c504_data_health)
port = free_port(); om.RemoteControl(fbot, port=port).start(); time.sleep(0.6)
try:
    from playwright.sync_api import sync_playwright
    exe = (glob.glob('/opt/pw-browsers/chromium-*/chrome-linux/chrome') or [None])[0]
    with sync_playwright() as pw:
        br = pw.chromium.launch(executable_path=exe) if exe else pw.chromium.launch()
        pg = br.new_page(viewport={'width': 412, 'height': 900}); errs = []
        pg.on('pageerror', lambda e_: errs.append(str(e_)))
        pg.goto(f'http://127.0.0.1:{port}/?t={TOKEN}'); pg.wait_for_timeout(3000)
        xvt = pg.inner_text('#xvenue')
        br.close()
    ok("the cross-venue panel: equity, pairs, funding, prices, fees, each pair's direction and spread",
       'long on the venue where longs pay less' in xvt and 'pairs' in xvt and 'funding' in xvt and 'fees' in xvt
       and ('Delta' in xvt), xvt[:500])
    ok("no JavaScript errors", not errs, str(errs))
except ImportError:
    ok("Chromium/playwright available for the page check", False)
print("\n" + "=" * 66)
print("ALL CHECKS PASSED" if not fails else f"{len(fails)} FAILURE(S): {fails}")
os._exit(1 if fails else 0)
