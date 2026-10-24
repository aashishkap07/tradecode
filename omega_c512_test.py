#!/usr/bin/env python3
"""C512: the day that just ended comes from Bitget's live candles, checked
against its last minute before the book trades on it.

Paper check #2 (30 Sep 2026) found that at the 00:05 UTC rebalance Bitget's
history-candles endpoint served the just-finished day as a snapshot from its
first minutes: 0 of 80 closes final (median 3.3% off, ZEC 1479.38 vs 1417.41),
quote volume 99% short. Every rebalance since the book began decided on the
day-before's close for its price inputs -- worth 3.5-9 points a year and ~10
points of worst drawdown on 2020-26 (research/c512_lag_cost.txt).

1. A stale history bar is replaced by the live endpoint's final bar (close,
   volume, open, high, low); older days are untouched.
2. If the day's close still differs from its 23:59 UTC minute, or the live
   endpoint does not answer, the history load RAISES and the rebalance waits
   (C499's rule) -- it never trades on an unfinished day.
3. The carry ledger's history gets the same final bar.
4. The rule tournament drops, once, the day(s) it scored on unfinished candles.
5. On live Bitget data (network): the loaded last day equals the live endpoint
   and its last minute.
"""
import os, io, json, time, types, logging, contextlib, importlib.util, tempfile
import numpy as np
REPO = os.path.dirname(os.path.abspath(__file__))
BASE = tempfile.mkdtemp(prefix='c512_test_')
os.environ['OMEGA_BASE_PATH'] = BASE
fails = []


def ok(n, c, d=''):
    print(f"  {'PASS' if c else 'FAIL'}  {n}" + (f"   {d}" if d else ''))
    if not c:
        fails.append(n)


spec = importlib.util.spec_from_file_location('om512', os.path.join(REPO, 'omega_v60_reconstructed.py'))
om = importlib.util.module_from_spec(spec)
with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
    spec.loader.exec_module(om)
LOG = []
class _H(logging.Handler):
    def emit(self, r): LOG.append((r.levelno, r.getMessage()))
lg = logging.getLogger('OmegaV60'); lg.handlers = [_H()]; lg.propagate = False
print("=" * 66); print("C512: THE JUST-FINISHED DAY, FINAL OR NOT AT ALL"); print("=" * 66)
DAY = 86400000
TODAY = int(time.time() * 1000) // DAY * DAY
YDAY = TODAY - DAY


class Venue:
    """a fake Bitget: history-candles with a STALE last day (the 30 Sep 2026 defect),
    live candles and a 23:59 minute that can be set to agree or not"""
    def __init__(s, live_close=1417.41, minute_close=1417.41, live_fails=False, minute_fails=False, days=40):
        s.live_close, s.minute_close, s.live_fails, s.minute_fails, s.days = live_close, minute_close, live_fails, minute_fails, days
        s.calls = []

    def bar(s, t, c, qv):
        return [str(t), f"{c * 0.99:.2f}", f"{c * 1.02:.2f}", f"{c * 0.97:.2f}", f"{c:.2f}", '1', f"{qv:.2f}"]

    def get(s, path, params, tries=3):
        s.calls.append((path, params.get('granularity')))
        if path == 'history-candles':
            rows = [s.bar(TODAY - k * DAY, 1500.0 + k, 2.5e8) for k in range(s.days, 1, -1)]
            rows.append(s.bar(YDAY, 1479.38, 2.8e6))            # the snapshot from the day's first minutes
            return rows[::-1]
        if path == 'candles':
            if params.get('granularity') == '1m':
                if s.minute_fails:
                    return None
                return [[str(TODAY - 120000), '0', '0', '0', '1418.40', '0', '0'],
                        [str(TODAY - 60000), '0', '0', '0', f"{s.minute_close:.2f}", '0', '0']]
            if s.live_fails:
                return None
            return [s.bar(TODAY, 1421.60, 1.2e7), s.bar(YDAY, s.live_close, 3.6e8),
                    s.bar(YDAY - DAY, 1502.0, 2.5e8)]
        if path == 'history-fund-rate':
            return [dict(fundingTime=str(TODAY - 8 * 3600000 * i), fundingRate='0.0001') for i in range(30)]
        return None


def mk():
    cfg = om.Config(); cfg.PAPER_MODE = True; cfg.C380_MAX_MONTHLY_DD_PCT = 20.0
    pf = om.Portfolio(cfg); pf.equity = pf.available_balance = 250.0
    bot = types.SimpleNamespace(cfg=cfg, portfolio=pf, _c462_state_settled=True, _c408_asset_class=lambda s: 'crypto',
                                _c482_risk_guard=lambda: {'pct': 20.0, 'month_eq0': 250.0})
    e = om.C488Engine(bot); e.reset(); bot.c488 = e; pf._c488 = e
    return bot, e


print("\n1. THE STALE LAST DAY IS REPLACED BY THE FINAL ONE")
bot, e = mk(); v = Venue(); e._get = v.get
c, f = e._history('ZEC/USDT:USDT')
ok("the just-finished day: close 1417.41 (final), not 1479.38 (the first-minutes snapshot)", c[YDAY][0] == 1417.41, str(c[YDAY]))
ok("  and its volume, open, high and low are the final bar's too", c[YDAY][1] == 3.6e8 and c[YDAY][3] == round(1417.41 * 1.02, 2)
   and c[YDAY][4] == round(1417.41 * 0.97, 2))
ok("  the day before (already final in history) is the live endpoint's identical bar", c[YDAY - DAY][0] == 1502.0)
ok("  older days come from history, untouched", c[TODAY - 10 * DAY][0] == 1510.0)
ok("  today's unfinished bar is not used", TODAY not in c)
ok("  and the check asked for the day's last minute", ('candles', '1m') in v.calls and ('candles', '1Dutc') in v.calls)

print("\n2. NOT FINAL, OR NOT ANSWERED: NO TRADE ON IT")
for lab, vv, want in (("the live bar still disagrees with its 23:59 minute", Venue(live_close=1479.38), 'not final'),
                      ("the live daily endpoint does not answer", Venue(live_fails=True), 'recent daily candles did not load'),
                      ("the last-minute candle does not answer", Venue(minute_fails=True), 'last-minute candle did not load')):
    b2, e2 = mk(); e2._get = vv.get
    try:
        e2._history('ZEC/USDT:USDT'); msg = ''
    except RuntimeError as x:
        msg = str(x)
    ok(f"{lab}: the load raises ('{want}')", want in msg, msg)
b3, e3 = mk(); v3 = Venue(live_close=1479.38); e3._get = v3.get
e3.refresh_marks = lambda force=False: True; e3.refresh_rules = lambda force=False: True
e3.candidates = lambda n: ['ZEC/USDT:USDT']; e3._marks_at = time.time() + 1e6
LOG.clear(); e3._tick_at = 0; e3.last_rebal = ''
e3.due = lambda: True; e3.guard = lambda: ''
e3.tick()
ok("  and through the engine's own tick: 'rebalance failed (... not final ...) -- retrying in 10 min', nothing traded",
   any('rebalance failed' in m and 'not final' in m and 'retrying in 10 min' in m for lv, m in LOG) and not e3.book
   and e3.last_rebal == '', str([m for lv, m in LOG][-2:]))
b4, e4 = mk(); v4 = Venue(); v4.get_orig = v4.get
v4.get = lambda path, params, tries=3: ([[str(TODAY - 120000), '0', '0', '0', '1', '0', '0']]
                                        if path == 'candles' and params.get('granularity') == '1m' else v4.get_orig(path, params, tries))
e4._get = v4.get
ok("a coin with no 23:59 minute (halted) is accepted on the live bar", e4._history('ZEC/USDT:USDT')[0][YDAY][0] == 1417.41)

print("\n3. THE CARRY LEDGER GETS THE SAME FINAL BAR")
b5, e5 = mk(); v5 = Venue(); e5._get = v5.get
car = om.C490Carry(b5)
h = car.history(['ZEC/USDT:USDT'], days=30)
ok("C490's history: the last day's close is 1417.41", h is not None and abs(h[2][-1][0] - 1417.41) < 1e-9, str(h[2][-3:] if h else None))

print("\n4. THE TOURNAMENT DROPS, ONCE, WHAT IT SCORED ON UNFINISHED CANDLES")
p = os.path.join(om.BASE_PATH, 'c510_tournament.json')
json.dump(dict(w={'n2n3': {'ZEC/USDT:USDT': 0.03}}, pend={'n2n3': 0.0}, last_day=YDAY, last_obs='x',
               daily=[[YDAY, {'n2n3': -0.00182, 'base': -0.00175}]], eq0=250.0, since='2026-09-29', skipped={}), open(p, 'w'))
LOG.clear()
t = om.C510Tournament(types.SimpleNamespace(cfg=om.Config(), c488=None))
ok("a pre-C512 file: its scored day is dropped, the held books kept, and it says why",
   t.daily == [] and t.w == {'n2n3': {'ZEC/USDT:USDT': 0.03}} and t.c512
   and any("unfinished daily candle and are dropped" in m for lv, m in LOG), str([m for lv, m in LOG]))
t.daily = [[TODAY, {'n2n3': 0.001}]]; t.save()
t2 = om.C510Tournament(types.SimpleNamespace(cfg=om.Config(), c488=None))
ok("  once: a C512 file keeps its rows", t2.daily == [[TODAY, {'n2n3': 0.001}]])

print("\n5. ON LIVE BITGET DATA")
try:
    import requests
    requests.get('https://api.bitget.com/api/v2/public/time', timeout=10)
    b6, e6 = mk()
    for sym in ('BTC/USDT:USDT', 'ZEC/USDT:USDT', 'PUMP/USDT:USDT'):
        cc, ff = e6._history(sym, days=40)
        raw = sym.replace('/USDT:USDT', 'USDT')
        live = requests.get(om.C488Engine.API + 'candles', params=dict(symbol=raw, productType='USDT-FUTURES',
                            granularity='1Dutc', limit=3), timeout=15).json()['data']
        lb = {int(x[0]): float(x[4]) for x in live}
        ok(f"{sym.split('/')[0]}: the loaded just-finished day = Bitget's live bar ({cc[YDAY][0]:g})",
           YDAY in cc and abs(cc[YDAY][0] - lb[YDAY]) < 1e-12 and TODAY not in cc)
except Exception as x:
    ok(f"live Bitget reachable for the data check ({type(x).__name__})", False)
ok("version C512 or later", int(om._OMEGA_VERSION[1:4]) >= 512)
print("\n" + "=" * 66)
print("ALL CHECKS PASSED" if not fails else f"{len(fails)} FAILURE(S): {fails}")
os._exit(1 if fails else 0)
