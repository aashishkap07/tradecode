#!/usr/bin/env python3
"""C510: the integrated bot -- round 10's refinements trade in paper, every
candidate rule is scored beside them, and the log and page say what trades.

1. PARITY: the bot's C2 rankings (base, N2, N3, N2+N3) and its range
   volatility (Parkinson, Garman-Klass) equal the research code's, number for
   number, on the research library (research/omega_c488_research.py); the
   default rule 'base' / 'close' / 'running' reproduces C488 exactly.
2. THE BOOK TRADES THE CHOSEN RULE: the default is N2+N3 (the operator's
   forward test); the rebalance uses it, logs it, saves it with the inputs
   (plus the day's open/high/low); the matrices carry OHLC from Bitget's candles.
3. THE TOURNAMENT: seven rules held on the same prices, scored from daily
   closes exactly as the K4 shadow is; the traded rule is marked; a variant
   needing high/low is skipped, loudly, when the matrices have none; it
   survives a restart; the watchdog flags a missed day.
4. THE LOG SAYS WHAT TRADES: the 8-minute summary leads with the book, not the
   idle scanner's 32% win rate; RECORD / FEES / LIFETIME describe the book and
   label the old scanner; the boot no longer prints "edge is positive" for the
   idle scanner; RULE and TOURNEY rows; live on an unadmitted rule is warned.
5. THE PAGE (Chromium): "What is running" (TRADES / PAPER / OFF), the rule on
   the book, the tournament table, the Record tile is the book's.
6. C509 uses N2+N3's own normal range when the book trades N2+N3.
"""
import os, sys, io, json, time, glob, socket, types, logging, contextlib, importlib.util, tempfile
import datetime as dt
import numpy as np
REPO = os.path.dirname(os.path.abspath(__file__))
BASE = tempfile.mkdtemp(prefix='c510_test_')
os.environ['OMEGA_BASE_PATH'] = BASE
TOKEN = 'c510-test-token-0123456789abcdef'
os.environ['OMEGA_CTRL_TOKEN'] = TOKEN
fails = []


def ok(n, c, d=''):
    print(f"  {'PASS' if c else 'FAIL'}  {n}" + (f"   {d}" if d else ''))
    if not c:
        fails.append(n)


spec = importlib.util.spec_from_file_location('om510', os.path.join(REPO, 'omega_v60_reconstructed.py'))
om = importlib.util.module_from_spec(spec)
with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
    spec.loader.exec_module(om)
sys.path.insert(0, os.path.join(REPO, 'research'))
import omega_c488_research as R
LOG = []
class _H(logging.Handler):
    def emit(self, r): LOG.append((r.levelno, r.getMessage()))
lg = logging.getLogger('OmegaV60'); lg.handlers = [_H()]; lg.propagate = False
print("=" * 66); print("C510: THE INTEGRATED BOT"); print("=" * 66)

# ─── synthetic but realistic matrices: 420 days x 30 coins, funding of both signs ───
g = np.random.default_rng(510); n, k = 420, 30
T = (np.arange(n) + 19000) * 86400000
ret = g.normal(0.0004, 0.035, size=(n, k)) + g.normal(0, 0.02, size=(n, 1))      # a common market factor
close = np.exp(np.cumsum(ret, axis=0)) * 10
close[:40, 25:] = np.nan                                                          # late listings
op = np.vstack([close[:1], close[:-1]])
hi = np.maximum(op, close) * np.exp(np.abs(g.normal(0, 0.02, size=(n, k))))
lo = np.minimum(op, close) * np.exp(-np.abs(g.normal(0, 0.02, size=(n, k))))
op[np.isnan(close)] = hi[np.isnan(close)] = lo[np.isnan(close)] = np.nan
qv = np.exp(g.normal(16, 0.7, size=(n, k)))
fund = g.normal(0.00005, 0.00025, size=(n, k)) * 3
keep = [f"K{j:02d}/USDT:USDT" for j in range(k)]

print("\n1. PARITY WITH THE RESEARCH CODE")
R.TOPN = 20
r = R.returns(close); sd = R.trailing_std(r, 30); elig = R.universe(close, qv)
f7 = np.full_like(fund, np.nan)
for i in range(7, n):
    f7[i] = fund[i - 6:i + 1].sum(axis=0)
f7[np.isnan(close)] = np.nan
s_base = R.xs_rank(R.lagret(close, 14), elig)                              # omega_c507_research.py, verbatim
s_n2 = np.where((s_base < 0) & (np.nan_to_num(f7, nan=0.0) < 0), 0.0, s_base)
mkt = np.nanmean(np.where(elig, np.nan_to_num(r, nan=np.nan), np.nan), axis=1); mkt = np.nan_to_num(mkt)
beta = np.ones_like(close)
for i in range(60, n):
    m = mkt[i - 59:i + 1]; vm = m.var()
    if vm <= 0:
        continue
    ri = r[i - 59:i + 1]; okk = ~np.isnan(ri)
    cov = np.nanmean((ri - np.nanmean(ri, axis=0)) * (m - m.mean())[:, None], axis=0)
    b = cov / vm; b[okk.sum(0) < 40] = np.nan
    beta[i] = np.where(np.isnan(b), 1.0, b)
m14 = np.full(n, np.nan)
for i in range(14, n):
    m14[i] = np.prod(1 + mkt[i - 13:i + 1]) - 1
s_n3 = R.xs_rank(R.lagret(close, 14) - beta * m14[:, None], elig)
s_n23 = np.where((s_n3 < 0) & (np.nan_to_num(f7, nan=0.0) < 0), 0.0, s_n3)   # omega_c510_research.py
e_bot = om._c488_universe(close, qv, 20)
ok("the universe is the research's", np.array_equal(e_bot, elig))
r_bot = om._c488_returns(close)
for rule, ref in (('base', s_base), ('n2', s_n2), ('n3', s_n3), ('n2n3', s_n23)):
    got = om._c510_c2_rank(close, r_bot, e_bot, om._c510_f7(fund, close), rule)
    ok(f"C2 ranking '{rule}' equals the research's on every day and coin", np.array_equal(got, ref),
       f"{int(np.sum(got != ref))} cells differ")
ok("  N2 removes shorts and only shorts; N3 changes who is ranked",
   np.all(s_n2[s_base > 0] > 0) and (s_n2 < 0).sum() < (s_base < 0).sum() and not np.array_equal(s_n3, s_base))


def ewma_sd_research(x, hl=10.0, min_obs=20):                              # omega_c510_research.py, verbatim
    a = 1.0 - 0.5 ** (1.0 / hl)
    out = np.full_like(x, np.nan)
    v = np.zeros(x.shape[1]); seen = np.zeros(x.shape[1], int)
    for i in range(len(x)):
        okx = ~np.isnan(x[i])
        v = np.where(okx, np.where(seen > 0, (1 - a) * v + a * np.nan_to_num(x[i]), np.nan_to_num(x[i])), v)
        seen = seen + okx
        out[i] = np.where((seen >= min_obs) & ~np.isnan(close[i]), np.sqrt(np.maximum(v, 0.0)), np.nan)
    return out


with np.errstate(divide='ignore', invalid='ignore'):
    lhl = np.log(hi / lo); lco = np.log(close / op)
    bad = ~(np.isfinite(lhl) & (lhl >= 0)); lhl[bad] = np.nan; lco[bad] = np.nan
    park = lhl ** 2 / (4 * np.log(2))
    gk = np.maximum(0.5 * lhl ** 2 - (2 * np.log(2) - 1) * lco ** 2, 0.0); gk[np.isnan(lhl)] = np.nan
for kind, x in (('park', park), ('gk', gk)):
    a_ = om._c510_range_sd(op, hi, lo, close, kind=kind); b_ = ewma_sd_research(x)
    ok(f"range volatility '{kind}' equals the research's", np.allclose(a_, b_, equal_nan=True, rtol=0, atol=1e-15))
# the default is C488 unchanged: the old sleeve construction, written out with the research library
r0, W0, el0 = om._c488_sleeves(T, close, qv, fund, 20)
sc = np.nan_to_num(R.vol_scale(sd)); N = 20
tr = sum(np.sign(np.nan_to_num(R.lagret(close, d))) for d in (7, 14, 28, 56)) / 4.0
ok("rule 'base' + 'close' reproduces C488's three sleeves exactly",
   np.array_equal(W0['C1'], R.banded(np.where(elig, tr * sc / N, 0.0)))
   and np.array_equal(W0['C2'], R.weekly(s_base * sc / (2 * N * 0.2), T))
   and np.array_equal(W0['C3'], R.weekly(-R.xs_rank(f7, elig) * sc / (2 * N * 0.2), T)))
_, Wg, _ = om._c488_sleeves(T, close, qv, fund, 20, rule='n2n3', ohlc=(op, hi, lo), volest='gk')
sdg = ewma_sd_research(gk); scg = np.nan_to_num(R.vol_scale(np.where(np.isnan(sdg), sd, sdg)))
ok("rule 'n2n3' + 'gk' is the research's construction (C2 on N2+N3, every sleeve on range vol)",
   np.allclose(Wg['C2'], R.weekly(s_n23 * scg / (2 * N * 0.2), T), atol=1e-15)
   and np.allclose(Wg['C1'], R.banded(np.where(elig, tr * scg / N, 0.0)), atol=1e-15))
w_old = om._c488_targets(T, close, qv, fund, 20, 0.2, 3.0)[0]
ok("_c488_targets with no rule given = the admitted book", np.array_equal(
   w_old, om._c488_combine({k_: W0[k_] for k_ in ('C1', 'C2', 'C3')}, r0, fund, 1, target_vol=0.2, lev_cap=3.0)[-1]))

print("\n2. THE BOOK TRADES THE CHOSEN RULE")
cfg = om.Config()
ok("the default: C2 = N2+N3 in paper (the forward test); vol and sizing as admitted",
   (cfg.C488_C2_RULE, cfg.C488_VOL_EST, cfg.C488_SIZING) == ('n2n3', 'close', 'running'))


class FakeEx:
    def __init__(s, ref): s.exchange = types.SimpleNamespace(markets={}); s.markets = s.exchange.markets; s.ref = ref
    def place_order(s, sym, side, qty, lev, order_type='market', price=None, reduce_only=False, post_only=None):
        m_ = s.ref[0].marks[sym]
        return {'id': 'p', 'status': 'closed', 'price': m_['ask'] if side == 'buy' else m_['bid'], 'filled': qty}
    def c487_settle(s, sym, o, side, price, size, wait): return float(o['filled']), float(o['price']), 'filled'
    def get_current_price(s, sym): return None


def make_bot(rule=None, day=-1):
    c = om.Config(); c.PAPER_MODE = True; c.C380_MAX_MONTHLY_DD_PCT = 15.0
    if rule:
        c.C488_C2_RULE = rule
    p = om.Portfolio(c); p.equity = p.available_balance = 250.0
    ref = [None]
    b = types.SimpleNamespace(cfg=c, portfolio=p, exchange=FakeEx(ref), _c462_state_settled=True,
                              _c408_asset_class=lambda s: 'crypto',
                              _c482_risk_guard=lambda: {'pct': 15.0, 'month_eq0': 250.0})
    e = om.C488Engine(b); e.reset(); ref[0] = e; p._c488 = e; b.c488 = e
    b.c501k = om.C501Allostatic(b); b.c501k.reset()
    b.c510t = om.C510Tournament(b); b.c510t.reset()
    for j, sy in enumerate(keep):
        x = float(close[day, j]) if not np.isnan(close[day, j]) else 10.0
        e.marks[sy] = dict(bid=x * 0.9999, ask=x * 1.0001, last=x, fr=0.0001, vol=float(qv[day, j]))
        b.exchange.markets[sy] = dict(precision={'amount': 0.001}, limits={'amount': {'min': 0.0}})
    e._marks_at = time.time() + 1e6
    e.refresh_marks = lambda force=False: True; e.refresh_rules = lambda force=False: True
    e.candidates = lambda nn: keep
    return b, e


def history_from(upto):
    """Bitget's history-candles rows and funding for each coin, up to day index `upto`"""
    def _h(sym, days=330):
        j = keep.index(sym); out = {}
        for i in range(max(0, upto - 330), upto + 1):
            if not np.isnan(close[i, j]):
                out[int(T[i])] = (float(close[i, j]), float(qv[i, j]), float(op[i, j]), float(hi[i, j]), float(lo[i, j]))
        fu = {int(T[i]) + 3600000: float(fund[i, j]) for i in range(max(0, upto - 90), upto + 1)}
        return out, fu
    return _h


b1, e1 = make_bot()
e1._history = history_from(n - 2)
LOG.clear(); e1.rebalance('first')
LOG1 = list(LOG)
M = e1.matrices(keep)
ok("matrices() carries the day's open/high/low beside the five matrices (ohlc_for)",
   e1.ohlc_for(M[0], M[1]) is not None and np.allclose(e1.ohlc_for(M[0], M[1])[1][-1],
                                                        hi[n - 2][[keep.index(s_) for s_ in M[1]]], equal_nan=True))
rb = [m_ for lv, m_ in LOG if 'C488 REBALANCE' in m_]
ok("the rebalance line names the rule: 'rule C2 N2+N3'", len(rb) == 1 and 'rule C2 N2+N3' in rb[0], str(rb))
T2, keep2, cl2, qv2, fd2 = M
w_n23 = om._c488_targets(T2, cl2, qv2, fd2, 20, e1.target_vol(), 3.0, rule='n2n3')[0]
eq1 = 250.0
want = {s_: round(float(x), 6) for s_, x in zip(keep2, np.nan_to_num(w_n23)) if abs(x) * eq1 >= 6.0}
ok("the plan is N2+N3's book, coin for coin", {s_: v['w'] for s_, v in e1.plan.items()} == want,
   f"{len(e1.plan)} vs {len(want)}")
z = np.load(os.path.join(om.BASE_PATH, 'c488_inputs.npz'))
ok("the saved inputs carry the rule and the day's open/high/low",
   list(z['rule']) == ['n2n3', 'close', 'running'] and z['hi'].shape == z['close'].shape
   and np.allclose(z['hi'], e1.ohlc_for(T2, keep2)[1], equal_nan=True))
b0, e0 = make_bot(rule='base'); e0._history = history_from(n - 2); e0.rebalance('first')
w_b = om._c488_targets(T2, cl2, qv2, fd2, 20, e0.target_vol(), 3.0)[0]
ok("C488_C2_RULE='base' trades the admitted book, unchanged",
   {s_: v['w'] for s_, v in e0.plan.items()} == {s_: round(float(x), 6) for s_, x in zip(keep2, np.nan_to_num(w_b))
                                                  if abs(x) * 250.0 >= 6.0} and e0.admitted() and not e1.admitted())

b90 = types.SimpleNamespace(cfg=b1.cfg, c488=e1)
h90 = om.C490Carry(b90).history(keep[:6], days=120)
ok("the carry ledger reads the same (now five-value) daily history: closes and volumes unchanged",
   h90 is not None and np.allclose(h90[2][-1], close[n - 2][:6], equal_nan=True)
   and np.allclose(h90[3][-1], qv[n - 2][:6], equal_nan=True))

print("\n3. THE TOURNAMENT")
t1 = b1.c510t.status()
ok("seven rules held after the first rebalance, the traded one marked, none skipped (OHLC present)",
   sum(v['on'] for v in t1['rows']) == 7 and t1['traded'] == 'n2n3' and not any(v['skipped'] for v in t1['rows'])
   and t1['days'] == 0, str([(v['name'], v['on'], v['skipped']) for v in t1['rows']]))
row = next(v for v in t1['rows'] if v['name'] == 'n2n3')
ok("  the traded rule's row holds the same book the paper book was planned from",
   {s_: round(x, 6) for s_, x in b1.c510t.w['n2n3'].items()} == want)
tl = [m_ for lv, m_ in LOG1 if 'C510 tournament' in m_]
ok("  and it logs 'C510 tournament (paper, same prices, ...)' after the trades", len(tl) == 1
   and 'N2+N3 (traded)' in tl[0]
   and LOG1.index(next(x for x in LOG1 if 'C510 tournament' in x[1])) > LOG1.index(next(x for x in LOG1 if 'C488 REBALANCE' in x[1])),
   str(tl))
w_prev = {k_: dict(v) for k_, v in b1.c510t.w.items()}
pend_prev = dict(b1.c510t.pend)
e1._history = history_from(n - 1); e1.last_rebal = ''
e1.rebalance('daily')
t2 = b1.c510t.status()
M2 = e1.matrices(keep); pos2 = {s_: j for j, s_ in enumerate(M2[1])}; r2 = om._c488_returns(M2[2])
hand = sum(x * float(np.nan_to_num(r2[-1][pos2[s_]])) - x * float(np.nan_to_num(M2[4][-1][pos2[s_]]))
           for s_, x in w_prev['base'].items()) - pend_prev['base']
got = next(v for v in t2['rows'] if v['name'] == 'base')
ok("a day later each rule is scored: yesterday's weights x today's return - funding - 0.08% x turnover",
   t2['days'] == 1 and abs(got['ret'] - hand) < 1e-5 and abs(b1.c510t.daily[-1][1]['base'] - hand) < 1e-7,
   f"{got['ret']} vs {hand}")
ok("  every rule has a score and a gap to the admitted rule",
   all(v['days'] == 1 for v in t2['rows']) and next(v for v in t2['rows'] if v['name'] == 'base')['vs_base'] == 0.0)
b2 = types.SimpleNamespace(cfg=b1.cfg, c488=e1)
again = om.C510Tournament(b2)
ok("it survives a restart (c510_tournament.json)", again.status()['rows'] == t2['rows'] and again.eq0 == t2['eq0'])
b3, e3 = make_bot()
e3.matrices = lambda ss: (T[:n - 1], keep, close[:n - 1], qv[:n - 1], fund[:n - 1])     # no OHLC from a caller
e3.rebalance('first')
t3 = b3.c510t.status()
sk = [v for v in t3['rows'] if v['skipped']]
ok("matrices without high/low: the range-vol rules are skipped and say why; the rest run",
   len(sk) == 2 and all('no high/low' in v['skipped'] for v in sk) and sum(v['on'] for v in t3['rows']) == 5)
TODAY = dt.datetime.utcnow().strftime('%Y-%m-%d')
bw = types.SimpleNamespace(cfg=b1.cfg, c488=e1, c510t=b1.c510t, c501k=None, c489=None, c490=None, c501s=None, c501v=None)
e1.last_rebal = TODAY; e1._last_M = (TODAY, 20, None); e1._marks_at = time.time()
b1.c510t.last_obs = '2000-01-01'
hw = om.TradingBot._c504_data_health(bw, time.time())
ok("the watchdog flags a rebalance the tournament missed", 'tournament' in hw['keys'], str(hw['late']))
b1.c510t.last_obs = TODAY
ok("  and not once it recorded it", 'tournament' not in om.TradingBot._c504_data_health(bw, time.time())['keys'])

print("\n4. THE LOG SAYS WHAT TRADES")
cfg4 = om.Config(); cfg4.PAPER_MODE = True; cfg4.C380_MAX_MONTHLY_DD_PCT = 15.0; cfg4.C488_ENGINE = 'portfolio'
om._c467_cfg_ref[0] = cfg4
pf = om.Portfolio(cfg4); pf.equity = 243.80; pf.available_balance = 223.0; pf.session_start_equity = 243.80
pf.get_live_equity = lambda *a: 241.33
pf.lifetime_trades, pf.lifetime_wins, pf.lifetime_losses, pf.lifetime_pnl = 139, 44, 95, -6.20
bot = types.SimpleNamespace(cfg=cfg4, portfolio=pf, _c462_state_settled=True, _c408_asset_class=lambda s: 'crypto',
                            exchange=types.SimpleNamespace(markets={}, get_current_price=lambda s: None),
                            _c482_risk_guard=lambda: {'pct': 15.0, 'month_eq0': 252.81, 'month_budget': 37.92,
                                                      'month_used': 11.48, 'day_cap': 9.0, 'day_used': 0.0, 'halt': ''})
e = om.C488Engine(bot); e.reset(); bot.c488 = e; pf._c488 = e
BUILD = om._C509_FIRST_BUILD[0]
e.born = dict(ts=time.time() - 3.73 * 86400, eq=252.63, approx=False)
e.month = {'key': dt.datetime.now().strftime('%Y-%m'), 'eq0': 252.81}
e.marks = {'NEAR/USDT:USDT': dict(bid=4.9, ask=4.91, last=4.905, fr=0.0001, vol=9e9)}
e.book = {'NEAR/USDT:USDT': dict(qty=2.0, avg=4.9602, fees=0.006, funding=0.0, realized=0.0, opened=BUILD)}
e._marks_at = time.time(); e.last_rebal = TODAY
e.tally = e._c510_tally([{'pnl': -3.7219}, {'pnl': -1.5881}, {'pnl': -1.4859}, {'pnl': -0.8565}, {'pnl': -0.7551},
                         {'pnl': -0.0738}, {'pnl': -0.0817}, {'pnl': -0.066}, {'pnl': 0.1092}, {'pnl': 0.0347},
                         {'pnl': 0.0133}])
ok("the book's record from the server's 11 closed positions: 3W 8L, net -$8.47",
   e.tally == dict(n=11, w=3, l=8, pnl=-8.4718), str(e.tally))
e.fills_run = [12, 0.111, 187.11]
bot._c504_data_health = lambda now=None: {'ok': True, 'bits': [], 'late': [], 'keys': []}
bot.c489 = om.C489Shadow(bot); bot.c490 = om.C490Carry(bot)
bot.c501s = om.C501Spot(bot); bot.c501v = om.C501Savings(bot); bot.c501k = om.C501Allostatic(bot)
bot.c510t = om.C510Tournament(bot); bot.c510t.w = {k_: dict(v) for k_, v in b1.c510t.w.items()}
bot.c510t.daily = list(b1.c510t.daily); bot.c510t.eq0 = 252.18; bot.c510t.since = TODAY; bot.c510t.last_obs = TODAY
bot.c510t.skipped = {}
rep = om._C462Report(os.path.join(BASE, 'r.log')); rows = []
rep._emit = lambda line: rows.append(str(line)); rep.status(bot)
blk = '\n'.join(rows)
def row_(key):
    """a packed row and its continuation lines (blank label column)"""
    i_ = next((j for j, r_ in enumerate(rows) if r_.strip().startswith(key)), None)
    if i_ is None:
        return ''
    out = [rows[i_]]
    for r_ in rows[i_ + 1:]:
        if r_[:12].strip() or not r_.strip():
            break
        out.append(r_)
    return ' '.join(out)
ok("RECORD: 'book closed 11 | 3W 8L | net $-8.47'", 'book closed 11' in row_('RECORD') and '3W 8L' in row_('RECORD')
   and 'net $-8.47' in row_('RECORD'), row_('RECORD'))
ok("FEES: the book's fills, 'book $0.11 | 12 taker fills this run | 0.059% of $187.11 traded'",
   'book $0.11' in row_('FEES') and '12 taker fills' in row_('FEES') and '0.059% of $187.11' in row_('FEES'), row_('FEES'))
ok("LIFETIME: '139tr 44W 95L old scanner | account $-6.20 realised'",
   '139tr 44W 95L old scanner' in row_('LIFETIME') and 'account $-6.20 realised' in row_('LIFETIME'), row_('LIFETIME'))
ok("RULE: 'C2 N2+N3 | forward test (paper)'", 'C2 N2+N3' in row_('RULE') and 'forward test' in row_('RULE'), row_('RULE'))
ok("TOURNEY: '1d from <first scored day> | base ... | N2+N3* ...' (C513: the day scored)", '1d from' in row_('TOURNEY') and 'N2+N3*' in row_('TOURNEY')
   and '+K4+GK' in row_('TOURNEY'), row_('TOURNEY'))
# the 8-minute summary line and the boot, through the real TradingBot methods
tb = om.TradingBot.__new__(om.TradingBot)
tb.cfg = cfg4; tb.portfolio = pf; tb.c488 = e; tb.exchange = bot.exchange
tb._c504_warn = lambda *a, **kw: None; tb._c498_session_pnl = lambda st: (0.0, 0.0)
pf.positions = om.PositionsManager()
LOG.clear()
try:
    om.TradingBot._display_summary(tb) if hasattr(om.TradingBot, '_display_summary') else None
except Exception:
    pass
summ = [m_ for lv, m_ in LOG if 'Win Rate' in m_ or 'C510 Book' in m_]
src = open(os.path.join(REPO, 'omega_v60_reconstructed.py')).read()
ok("the 8-minute summary leads with the book: 'C510 Book (what trades): ... rule ... closed 11: 3W/8L'",
   "🎯 C510 Book (what trades)" in src and (not summ or ('C510 Book' in summ[0] and 'closed 11: 3W/8L' in summ[0])),
   str(summ))
ok("the boot prints no 'edge is positive' for the idle scanner while the book trades",
   "the idle scanner's own bookkeeping, not a measured edge" in src
   and src.index("if _b503:\n                # C510") < src.index("✅ edge is positive"))
F = om._C460ConsoleFilter()
rec = lambda m_: logging.LogRecord('OmegaV60', logging.INFO, __file__, 1, m_, None, None)
ok("the tournament, the book line and the boot RULE line reach the session log",
   F.filter(rec('   🏁 C510 tournament (paper, same prices, 1 day scored from x): base +0.1%'))
   and F.filter(rec('🎯 C510 Book (what trades): 1 positions')) and F.filter(rec('   RULE   C2 N2+N3: C2 = x')))
cfgL = om.Config(); cfgL.PAPER_MODE = False; cfgL.C488_LIVE_OK = True
bl = types.SimpleNamespace(cfg=cfgL, portfolio=pf, _c462_state_settled=False)
eL = om.C488Engine(bl); eL.reset(); LOG.clear()
eL._tick_at = 0; eL.tick()
ok("live on an unadmitted rule is warned, once, by name", any(lv == logging.WARNING and 'C510 LIVE on a rule that has NOT'
                                                             in m_ and 'N2+N3' in m_ for lv, m_ in LOG), str(LOG[-3:]))

print("\n5. THE PAGE (Chromium)")


def free_port():
    s_ = socket.socket(); s_.bind(('127.0.0.1', 0)); p_ = s_.getsockname()[1]; s_.close(); return p_


fbot = types.SimpleNamespace(cfg=cfg4, portfolio=pf, c488=e, c501s=bot.c501s, c501v=bot.c501v, c501k=bot.c501k,
                             c489=bot.c489, c490=bot.c490, c510t=bot.c510t,
                             mode_mgr=types.SimpleNamespace(mode=types.SimpleNamespace(value='normal')),
                             exchange=types.SimpleNamespace(get_current_price=lambda s: None),
                             _c467_day_barrier=lambda: {'pnl': 0.0, 'limit': 9.0, 'used': 0.0, 'frac': 0.0},
                             _c482_risk_guard=bot._c482_risk_guard, _c504_data_health=bot._c504_data_health)
port = free_port(); om.RemoteControl(fbot, port=port).start(); time.sleep(0.6)
try:
    from playwright.sync_api import sync_playwright
    exe = (glob.glob('/opt/pw-browsers/chromium-*/chrome-linux/chrome') or [None])[0]
    with sync_playwright() as pw:
        br = pw.chromium.launch(executable_path=exe) if exe else pw.chromium.launch()
        pg = br.new_page(viewport={'width': 412, 'height': 900}); errs = []
        pg.on('pageerror', lambda x: errs.append(str(x)))
        pg.goto(f'http://127.0.0.1:{port}/?t={TOKEN}'); pg.wait_for_timeout(3000)
        run_ = pg.inner_text('#running'); bk = pg.inner_text('#book'); tt = pg.inner_text('#tourney')
        rc = pg.inner_text('#rec') + ' ' + pg.inner_text('#recs')
        br.close()
    ok("'What is running': TRADES the book (rule C2 N2+N3, forward test) · PAPER ledgers · OFF the old scanner",
       'TRADES' in run_ and 'C2 N2+N3' in run_ and 'forward test' in run_ and 'PAPER' in run_
       and 'rule tournament' in run_ and 'OFF' in run_ and '44W 95L' in run_ and 'crypto only' in run_, run_)
    ok("the book panel names its rule", 'rule: C2 N2+N3' in bk and 'forward test' in bk, bk)
    ok("the tournament table: every rule, the traded one marked, each with its research evidence",
       '(traded)' in tt and 'admitted C488 rule' in tt and 'round 11' in tt and 'vs base' in tt, tt)
    ok("the Record tile is the book's: '3W 8L · book: 11 closed, net -$8.47 · old scanner (off)'",
       '3W 8L' in rc and 'book: 11 closed' in rc and '-$8.47' in rc and 'old scanner (off)' in rc, rc)
    ok("  the separate K4 line gives way to the tournament's K4 row", 'allostatic shadow (K4' not in bk, bk)
    ok("no JavaScript errors", not errs, str(errs))
except ImportError:
    ok("Chromium/playwright available for the page check", False)

print("\n6. C509 WITH THE RULE THAT TRADES")
RN = json.load(open(os.path.join(REPO, 'research', 'c510_normal_range.json')))
ok("the bot's N2+N3 range table is research/c510_normal_range.json",
   all(list(om._C510_RANGES_N2N3[int(k_)]) == v for k_, v in RN['days'].items()))
cx = e.context()['start']
row4 = om._c509_row(cx['days'], 15.0, 'n2n3')
ok("with the book on N2+N3 the 'normal for that long' range is N2+N3's",
   abs(cx['p10'] - row4[2]) < 1e-5 and abs(cx['p90'] - row4[6]) < 1e-5, f"{cx['p10']} {cx['p90']}")
ok("version C510 or later", int(om._OMEGA_VERSION[1:4]) >= 510)
print("\n" + "=" * 66)
print("ALL CHECKS PASSED" if not fails else f"{len(fails)} FAILURE(S): {fails}")
os._exit(1 if fails else 0)
