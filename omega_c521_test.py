#!/usr/bin/env python3
"""C521: two more paper accounts -- BFUSD on Binance, and the same book on Delta Exchange India.

1. Settings and version.
2. BFUSD: the whole wallet accrues the APY every minute; TDS once; against Savings (idle only).
3. Delta: its table (crypto only: tokenised stocks, ETFs, metals out), whole contracts, fills at
   bid/ask, 0.05% taker + 18% GST, coins not listed and targets under one contract named.
4. Delta: reductions realise P&L, flips, the 30% band, funding at each coin's own exchange
   time from FUNDING:<SYM> (C523: the record stamped AT the exchange, as Delta's API really
   answers), catch-up after downtime, a record not yet written waits 15 minutes.
5. The book's rebalance hands Delta its RAW weights; the first run can start from the saved inputs.
6. Persistence and the fresh start.
7. The page (Chromium): both panels, no JavaScript errors.
The Delta API is simulated in its documented formats (the real one answers this sandbox; its
numbers are checked in research/c521_delta.py).
"""
import os, io, sys, json, time, glob, types, socket, logging, tempfile, contextlib, importlib.util
import numpy as np
REPO = os.path.dirname(os.path.abspath(__file__))
BASE = tempfile.mkdtemp(prefix='c521_test_')
os.environ['OMEGA_BASE_PATH'] = BASE
TOKEN = 'c521-test-token-0123456789abcdef'
os.environ['OMEGA_CTRL_TOKEN'] = TOKEN
fails = []


def ok(n, c, d=''):
    print(f"  {'PASS' if c else 'FAIL'}  {n}" + (f"   {d}" if d else ''))
    if not c:
        fails.append(n)


spec = importlib.util.spec_from_file_location('om521', os.path.join(REPO, 'omega_v60_reconstructed.py'))
om = importlib.util.module_from_spec(spec)
with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
    spec.loader.exec_module(om)
LOG = []
class _H(logging.Handler):
    def emit(self, r): LOG.append((r.levelno, r.getMessage()))
lg = logging.getLogger('OmegaV60'); lg.handlers = [_H()]; lg.propagate = False
print("=" * 66); print("C521: BFUSD AND THE SAME BOOK ON DELTA EXCHANGE INDIA (PAPER)"); print("=" * 66)
SRC = open(os.path.join(REPO, 'omega_v60_reconstructed.py')).read()

print("\n1. SETTINGS")
c0 = om.Config()
ok("BFUSD on (7.66% base APY, 9.51% boosted shown, 1% TDS once); Delta on at $500 with 18% GST",
   c0.C521_BFUSD and c0.C521_BFUSD_APY == 0.0766 and c0.C521_BFUSD_BOOST == 0.0951 and c0.C521_BFUSD_TDS == 0.01
   and c0.C521_DELTA and c0.C521_DELTA_EQUITY in (500.0, 200.0) and c0.C521_DELTA_GST == 0.18)   # C531: $200 of the $600
ok("version C521 or later", int(om._OMEGA_VERSION[1:]) >= 521)
ok("the bot builds both, ticks both every pass, resets both on a fresh start",
   'self.c521b = C521Bfusd(self)' in SRC and 'self.c521d = C521Delta(self)' in SRC
   and '(self.c501s, self.c501v, self.c521b, self.c521d' in SRC and 'bot.c521b.reset(); bot.c521d.reset()' in SRC)


def bn_cfg(venue='binance'):
    c = om.Config(); c.PAPER_MODE = True; c.C380_MAX_MONTHLY_DD_PCT = 20.0; c.C488_ENGINE = 'portfolio'; c.VENUE = venue
    c.C521_DELTA_EQUITY = 500.0          # C531 moved the default to $200; this test checks C521 at the size it was written for
    for k, v in om._C516_VENUE_DEFAULTS.get(venue, {}).items():
        setattr(c, k, v)
    return c


print("\n2. BFUSD")
cfg = bn_cfg(); om._c467_cfg_ref[0] = cfg
eqbox = [500.0]
sav = types.SimpleNamespace(active=lambda: True, status=lambda: {'month_est': 1.72})
bot = types.SimpleNamespace(cfg=cfg, _c462_state_settled=True, c488=types.SimpleNamespace(live_equity=lambda: eqbox[0]),
                            c501v=sav)
b = om.C521Bfusd(bot); b.reset()
ok("on Binance it runs; on Bitget it is off (BFUSD is Binance's)",
   b.active() and not om.C521Bfusd(types.SimpleNamespace(cfg=bn_cfg('bitget'), c488=None)).active())
t0 = time.time() - 3 * 86400.0
b.tick(now=t0)
ok("first minute: no interest yet, 1% TDS withheld once on the $500 converted ($5.00)",
   b.interest == 0.0 and abs(b.tds - 5.0) < 1e-9 and b.eq0 == 500.0)
b._tick_at = 0; b.tick(now=t0 + 86400)
ok("a day later: $500 x 7.66% / 365 = $0.1049 (the WHOLE wallet earns, not just idle cash)",
   abs(b.interest - 500 * 0.0766 / 365) < 1e-9, f"{b.interest:.6f}")
eqbox[0] = 510.0; b._tick_at = 0; b.tick(now=t0 + 2 * 86400)
ok("  the next day accrues on the equity held through it ($500), then follows the new equity ($510)",
   abs(b.interest - 2 * 500 * 0.0766 / 365) < 1e-9 and b.eq == 510.0)
st = b.status()
ok("status: about $3.26/month on $510 vs Savings $1.72 -> +$1.54/month; the $5.10... TDS paid back in ~99 days",
   st['month_est'] == round(510 * 0.0766 / 12, 2) and st['savings_month'] == 1.72 and st['gain_month'] == round(510 * 0.0766 / 12 - 1.72, 2)
   and st['tds'] == 5.0 and st['payback_days'] == round(30.4 * 5.0 / (510 * 0.0766 / 12 - 1.72), 0), str(st))
b.save(); b2 = om.C521Bfusd(bot)
ok("persists across a restart", abs(b2.interest - b.interest) < 1e-12 and b2.tds == 5.0 and b2.since == b.since)

print("\n3. DELTA: THE TABLE, WHOLE CONTRACTS, FEES WITH GST")
NOW = int(time.time())


class FakeDelta:
    """Delta Exchange India's /v2/products, /v2/tickers and /v2/history/candles, as documented"""
    def __init__(s):
        s.px = {'BTC': 84000.0, 'ETH': 2700.0, 'SOL': 119.0, '1000PEPE': 0.0044, 'HYPE': 89.0, 'XAUT': 3800.0, 'TSLAX': 420.0}
        s.cv = {'BTC': 0.001, 'ETH': 0.01, 'SOL': 1.0, '1000PEPE': 1000.0, 'HYPE': 0.1, 'XAUT': 0.001, 'TSLAX': 0.01}
        for k in range(22):
            s.px[f"C{k:02d}"] = 1.0 + k; s.cv[f"C{k:02d}"] = 1.0
        s.fr = 0.02                       # the ticker's live (next-exchange) rate, percent: only a fallback
        s.calls = []
        s.unwritten = set()               # exchange times whose record Delta has not written yet

    @staticmethod
    def rate_at(t):
        """the rate SETTLED at exchange time t, percent: a different value at each exchange"""
        return 0.01 + (t // 3600 % 7) * 0.001

    def __call__(s, path, params, tries=3):
        s.calls.append((path, dict(params)))
        if path == '/v2/products':
            out = []
            for c in s.px:
                top = 'tradfi' if c in ('XAUT', 'TSLAX') else None
                tags = ['metal'] if c == 'XAUT' else (['xStock'] if c == 'TSLAX' else ['layer_1'])
                sp = dict(rate_exchange_interval=14400 if c == 'HYPE' else 28800, tags=tags)
                if top:
                    sp['top_tag'] = top
                out.append(dict(symbol=c + 'USD', contract_value=str(s.cv[c]), taker_commission_rate='0.0005',
                                product_specs=sp, settling_asset={'symbol': 'USD'}, underlying_asset={'symbol': c}))
            return out
        if path == '/v2/tickers':
            return [dict(symbol=c + 'USD', mark_price=str(p), funding_rate=str(s.fr),
                         quotes={'best_bid': str(p * 0.9999), 'best_ask': str(p * 1.0001)}) for c, p in s.px.items()]
        if path == '/v2/history/candles':
            # C523: as Delta answers FUNDING:<SYM> -- a step series written AT each exchange time (even
            # when unchanged), hourly candles forward-filled, and NOTHING before the first exchange
            # record inside the window (so the hour before an exchange comes back empty)
            iv = 14400 if params['symbol'].split(':')[-1] == 'HYPEUSD' else 28800
            st, en = int(params['start']), int(params['end'])
            first = -(-st // iv) * iv
            out = []
            for t in range(first, en + 1, 3600):
                step = t // iv * iv
                if step in s.unwritten:
                    break
                r = s.rate_at(step)
                out.append(dict(time=t, open=r, high=r, low=r, close=r, volume=None))
            return out
        return None


fd = FakeDelta(); om._c521_get = fd
eng = types.SimpleNamespace(live_equity=lambda: 500.0, born={'eq': 500.0}, last_rebal='', target_vol=lambda: 0.2667)
dbot = types.SimpleNamespace(cfg=cfg, _c462_state_settled=True, c488=eng)
d = om.C521Delta(dbot); d.reset()
ok("Delta's table: crypto only -- the gold token (top_tag tradfi, 'metal') and the Tesla xStock are left out",
   d.refresh_products(force=True) and 'BTC' in d.prods and 'XAUT' not in d.prods and 'TSLAX' not in d.prods
   and d.prods['HYPE']['iv'] == 14400 and d.prods['BTC']['cv'] == 0.001)
keep = ['BTC/USDT:USDT', 'ETH/USDT:USDT', 'SOL/USDT:USDT', '1000PEPE/USDT:USDT', 'HYPE/USDT:USDT', 'FET/USDT:USDT']
#            BTC +$90 (1 ct = $84 -> 1), ETH -$40 (1 ct = $27 -> -1), SOL +$30 (< half a $119 contract -> 0),
#            PEPE -$22 (1 ct = $4.40 -> -5), HYPE +$27 (1 ct = $8.90 -> 3), FET +$12 (not listed)
w = np.array([90, -40, 30, -22, 27, 12]) / 500.0
LOG.clear()
d.rebalance(keep, w, 'first')
q = {s: p['qty'] for s, p in d.pos.items()}
ok("contracts = round(target / (contract value x mark)): BTC 1, ETH -1, PEPE -5, HYPE 3; SOL (under half a contract) none",
   q == {'BTCUSD': 1.0, 'ETHUSD': -1.0, '1000PEPEUSD': -5.0, 'HYPEUSD': 3.0}, str(q))
inf = d.info
ok("  the coin Delta does not list (FET) and the one under a contract (SOL) are NAMED, not forced",
   any('FET' in x for x in inf['missing']) and any('SOL' in x for x in inf['zero']), str(inf.get('missing')) + str(inf.get('zero')))
btc = d.pos['BTCUSD']
fee_btc = 0.001 * 84000 * 1.0001 * 0.0005 * 1.18
ok("buys fill at the ask, sells at the bid; fee = notional x 0.05% x 1.18 (GST)",
   abs(btc['avg'] - 84000 * 1.0001) < 1e-6 and abs(btc['fees'] - fee_btc) < 1e-12
   and abs(d.pos['ETHUSD']['avg'] - 2700 * 0.9999) < 1e-9, f"BTC fee {btc['fees']:.5f}")
tot_fee = sum(p['fees'] for p in d.pos.values())
ok("equity = $500 - fees + open P&L at the marks", abs(d.equity() - (500 - tot_fee + d.unrealized())) < 1e-9
   and abs(d.cash - (500 - tot_fee)) < 1e-9, f"equity {d.equity():.4f}")
ok("one log line says what was held of what was planned", any('C521 Delta Exchange India (paper, same plan)' in m and 'not on Delta: FET' in m
                                                              for lv, m in LOG), next((m for lv, m in LOG if 'same plan' in m), '')[:200])

print("\n4. DELTA: REDUCTIONS, FLIPS, THE BAND, FUNDING")
fd.px['BTC'] = 86000.0; fd.px['ETH'] = 2600.0; d.refresh_marks(force=True)
cash0 = d.cash
#            BTC +$90 -> 0 (close), ETH -$40 -> +$60 (flip to +2), PEPE -$22 -> -$23 (inside the band: no trade), HYPE same
w2 = np.array([0, 60, 30, -23, 27, 12]) / 500.0
n0 = d.trades
d.rebalance(keep, w2, 'daily')
gain_btc = 0.001 * (86000 * 0.9999 - 84000 * 1.0001)
ok("closing BTC realises its P&L at the bid (+$1.83) and records the whole idea",
   'BTCUSD' not in d.pos and any(c['sym'] == 'BTCUSD' and abs(c['pnl'] - round(gain_btc, 4)) < 1e-4 for c in d.closed),
   str(d.closed[-2:]))
ok("ETH flips: the short closes (P&L on 1 contract) and 2 longs open at the ask", d.pos['ETHUSD']['qty'] == 2.0
   and abs(d.pos['ETHUSD']['avg'] - 2600 * 1.0001) < 1e-9 - 0 + 1e-6, str(d.pos['ETHUSD']))
ok("PEPE inside the 30% band and the $6 minimum: no trade", d.pos['1000PEPEUSD']['qty'] == -5.0)
# funding: the first tick only schedules; a due exchange books -qty x cv x mark x rate
for p in d.pos.values():
    p.pop('fund_next', None)
d.accrue_funding(now=NOW)
ok("each position gets its next exchange time on its own interval (HYPE 4 h, the rest 8 h)",
   d.pos['HYPEUSD']['fund_next'] % 14400 == 0 and d.pos['ETHUSD']['fund_next'] % 28800 == 0)
f0 = {s: p['funding'] for s, p in d.pos.items()}
for p in d.pos.values():
    p['fund_next'] = NOW // 28800 * 28800                          # one exchange due now
fd.calls.clear()
d.accrue_funding(now=NOW)
pay = {s: d.pos[s]['funding'] - f0[s] for s in d.pos}
m = {s: d.marks[s]['mark'] for s in d.pos}
due0 = NOW // 28800 * 28800
nex = {s: len(range(due0, NOW + 1, d.prods[s[:-3]]['iv'])) for s in d.pos}     # exchanges owed on each coin's clock
owed = {s: sum(fd.rate_at(t) / 100 for t in range(due0, NOW + 1, d.prods[s[:-3]]['iv'])) for s in d.pos}
ok("a long pays a positive rate, a short receives it: -qty x cv x mark x the rate SETTLED at each exchange (HYPE every 4 h)",
   all(abs(pay[s] - (-d.pos[s]['qty'] * d.pos[s]['cv'] * m[s] * owed[s])) < 1e-12 for s in d.pos)
   and pay['ETHUSD'] < 0 < pay['1000PEPEUSD'], str({k: round(v, 6) for k, v in pay.items()}))
ok("  C523: the rate is FUNDING:<SYM>'s record stamped AT the exchange (start = the exchange time), not the ticker's",
   all(q_['start'] % 14400 == 0 and q_['end'] - q_['start'] == 3599 for p, q_ in fd.calls
       if p == '/v2/history/candles' and q_['symbol'].startswith('FUNDING:'))
   and any(p == '/v2/history/candles' for p, q_ in fd.calls) and fd.rate_at(due0) != fd.fr)
ok("  (the C521 window, the hour BEFORE the exchange, gets nothing from Delta: why every exchange fell back to the ticker)",
   fd('/v2/history/candles', {'symbol': 'FUNDING:ETHUSD', 'start': due0 - 3600, 'end': due0 - 1, 'resolution': '1h'}) == [])
for p in d.pos.values():
    p['fund_next'] = NOW // 28800 * 28800 - 2 * 28800              # down for 16 hours: three exchanges owed
f1 = d.pos['ETHUSD']['funding']
d.accrue_funding(now=NOW)
ok("after downtime every missed exchange is booked (3 for ETH, each at its own settled rate), then the next is scheduled",
   abs((d.pos['ETHUSD']['funding'] - f1)
       - sum(-2 * 0.01 * m['ETHUSD'] * fd.rate_at(due0 - k * 28800) / 100 for k in range(3))) < 1e-12
   and d.pos['ETHUSD']['fund_next'] > NOW)
# C523: a record Delta has not written yet: wait (nothing booked, the exchange stays owed) ...
d.pos['ETHUSD']['fund_next'] = due0; fd.unwritten = {due0}
f2 = d.pos['ETHUSD']['funding']
d.accrue_funding(now=due0 + 60)
ok("C523: a record not yet written is waited for (nothing booked, the exchange still owed)",
   d.pos['ETHUSD']['funding'] == f2 and d.pos['ETHUSD']['fund_next'] == due0)
LOG.clear()
d.accrue_funding(now=due0 + 901)
ok("  after 15 minutes the ticker's rate is used, and said",
   abs((d.pos['ETHUSD']['funding'] - f2) - (-2 * 0.01 * m['ETHUSD'] * fd.fr / 100)) < 1e-12
   and d.pos['ETHUSD']['fund_next'] == due0 + 28800 and any('no record after 15 min' in str(x) for x in LOG), str(LOG[-2:]))
fd.unwritten = set()

print("\n5. THE BOOK HANDS DELTA ITS RAW PLAN; THE FIRST RUN CAN START FROM THE SAVED INPUTS")
ok("C488Engine.rebalance calls c521d.rebalance(keep, w, ...) with the raw weights, after the tournament",
   "_d521.rebalance(keep, w, 'first' if not _d521.start_equity else why)" in SRC
   and SRC.index("_d521.rebalance(keep, w,") > SRC.index("_t510.observe(T, keep, close"))
# a real C488 rebalance on synthetic coins that Delta lists
g = np.random.default_rng(7)
n, k = 430, 60
T = (np.arange(n) + 19000) * 86400000
close = np.full((n, k), np.nan); qv = np.full((n, k), np.nan); fund = np.zeros((n, k))
for j in range(k):
    a = int(g.integers(0, 150)); ret = g.normal(0, 0.004, size=n).cumsum() * 0.02 + g.normal(0, 0.035, size=n)
    px = 10 ** g.uniform(-1, 2) * np.exp(np.cumsum(ret))
    close[a:, j] = px[a:]; qv[a:, j] = np.exp(g.normal(16 - 0.04 * j, 0.8, size=n - a)); fund[a:, j] = g.normal(0.0001, 0.0002, size=n - a) * 3
SY = [f"C{j:02d}/USDT:USDT" for j in range(k)]
for j in range(22):
    fd.px[f"C{j:02d}"] = float(close[-1, j]); fd.cv[f"C{j:02d}"] = 10 ** np.floor(np.log10(5.0 / close[-1, j]))
for c_ in ('C00', 'C03', 'C07', 'C12'):                              # coins the book plans that Delta does not list
    fd.px.pop(c_); fd.cv.pop(c_)


class PaperEx:
    def __init__(s): s.e, s.orders = None, []
    def place_order(s, sym, side, q, lev, typ, reduce_only=False, **kw):
        m_ = s.e.marks[sym]; px = m_['ask'] if side == 'buy' else m_['bid']
        s.orders.append((sym, side, q, px)); return {'id': 'p', 'price': px, 'filled': q, 'status': 'closed'}
    def c487_settle(s, sym, o, side, price, size, wait): return float(o['filled']), float(o['price']), 'filled'
    def get_current_price(s, sym): return None


pf = om.Portfolio(cfg); pf.equity = pf.available_balance = 500.0
ex = PaperEx()
B = types.SimpleNamespace(cfg=cfg, portfolio=pf, exchange=ex, _c462_state_settled=True, _c408_asset_class=lambda s: 'crypto',
                          _c482_risk_guard=lambda: {'pct': 20.0, 'month_eq0': 500.0})
E = om.C488Engine(B); E.reset(); ex.e = E; pf._c488 = E; B.c488 = E
B.c510t = om.C510Tournament(B); B.c510t.reset(); B.c501k = om.C501Allostatic(B)
B.c521d = om.C521Delta(B); B.c521d.reset()
for j, s in enumerate(SY):
    p_ = float(close[-1, j]); st_ = float(10 ** np.floor(np.log10(0.5 / p_)))
    E.marks[s] = dict(bid=p_ * 0.9999, ask=p_ * 1.0001, last=p_, fr=0.0001, vol=float(qv[-1, j]))
    E.rules[s] = dict(step=st_, min_qty=st_, min_usdt=5.0, max_mkt=1e12, status='normal', kind='COIN', sub='')
E._marks_at = E._rules_at = time.time() + 1e6
E.refresh_marks = lambda force=False: True; E.refresh_rules = lambda force=False: True
E.candidates = lambda n_: SY; E.matrices = lambda s_: (T, SY, close, qv, fund); E.ohlc_for = lambda a_, b_: None
LOG.clear()
E.rebalance('first')
dl = B.c521d
ok(f"after the book's first rebalance Delta holds the plan's listed coins ({len(dl.pos)} positions, {dl.trades} fills)",
   dl.start_equity == 500.0 and len(dl.pos) > 0 and dl.trades == len(dl.pos)
   and all(s[:-3] in fd.px for s in dl.pos), str(sorted(dl.pos)))
plan_listed = {s.split('/')[0] for s in E.plan if s.split('/')[0] in fd.px}
ok("  every coin it holds is in the book's raw plan; coins Delta lacks (C22..C59) are named",
   {s[:-3] for s in dl.pos} <= {s.split('/')[0] for s in E.plan} | {s.split('/')[0] for s in SY}
   and len(dl.info['missing']) > 0 and all(x.split()[0] in ('C00', 'C03', 'C07', 'C12') or x.split()[0] not in fd.px
                                            for x in dl.info['missing'])
   and not any(s[:-3] in ('C00', 'C03', 'C07', 'C12') for s in dl.pos), str(dl.info['missing'][:4]))
# bootstrap from the saved inputs, for a server that updates mid-day
dl2 = om.C521Delta(B); dl2.reset(); B.c521d = dl2
ok("bootstrap: the saved c488_inputs.npz of today's rebalance rebuilds the same plan for Delta",
   dl2.bootstrap() and set(dl2.pos) == set(dl.pos) and all(dl2.pos[s]['qty'] == dl.pos[s]['qty'] for s in dl.pos),
   f"{sorted(dl2.pos)} vs {sorted(dl.pos)}")
E.last_rebal = '2000-01-01'
dl3 = om.C521Delta(B); dl3.reset()
ok("  but never from a stale day's inputs", not dl3.bootstrap() and not dl3.pos)

print("\n6. PERSISTENCE AND THE FRESH START")
dl.save(); dl4 = om.C521Delta(B)
ok("the Delta book persists (positions, cash, fees, funding, closed)",
   {s: p['qty'] for s, p in dl4.pos.items()} == {s: p['qty'] for s, p in dl.pos.items()}
   and abs(dl4.cash - dl.cash) < 1e-12 and dl4.trades == dl.trades and dl4.start_equity == 500.0)
dl4.reset(); dl5 = om.C521Delta(B)
ok("a fresh start empties it", not dl5.pos and dl5.start_equity == 0.0 and dl5.cash == 0.0)

print("\n8. ROUND 14 IN THE BOT")
c8 = om.Config()
ok("range vol (GK) is the traded volatility estimator: admitted in round 14 at equal risk",
   c8.C488_VOL_EST == 'gk' and c8.C488_C2_RULE == 'n2n3' and c8.C488_SIZING == 'running')
names = [v[0] for v in om._C510_VARIANTS]
ok("the tournament scores two more risk rules forward: the drawdown loop and ex-ante risk (on N2+N3 + GK)",
   names[-2:] == ['n2n3_gk_dd', 'n2n3_gk_xa'] and len(names) == 9
   and next(v for v in om._C510_VARIANTS if v[0] == 'n2n3_gk')[5].endswith('ADMITTED'))
tt = om.C510Tournament(types.SimpleNamespace(cfg=cfg, c488=None)); tt.reset(save=False)
tt.daily = [[1, {'n2n3_gk_dd': 0.10}], [2, {'n2n3_gk_dd': -0.15 / 1.0}]]
ok("the drawdown loop's scale: 1 - DD/30%: a 15% fall from the peak halves the book",
   abs(tt._dd_scale('n2n3_gk_dd') - 0.5) < 1e-12, f"{tt._dd_scale('n2n3_gk_dd')}")
tt.daily = [[1, {'n2n3_gk_dd': -0.40}]]
ok("  floored at 0.25 (a 40% fall); no history: 1.0", abs(tt._dd_scale('n2n3_gk_dd') - 0.25) < 1e-12
   and tt._dd_scale('other') == 1.0)
sys.path.insert(0, os.path.join(REPO, 'research'))
with contextlib.redirect_stdout(io.StringIO()):
    import omega_c521_research as RQ
r8 = om._c488_returns(close)
_, W8, _ = om._c488_sleeves(T, close, qv, fund, 20, rule='n2n3')
parts8 = {k_: W8[k_] for k_ in ('C1', 'C2', 'C3')}
mine = om._c521_combine_exante(parts8, r8, fund, 1, target_vol=RQ.TV, lev_cap=RQ.LEV)
theirs = RQ.combine_exante(dict(r=r8, fund=fund), parts8)
ok("the bot's ex-ante risk = the research's combine_exante, to the last bit",
   np.array_equal(np.nan_to_num(mine), np.nan_to_num(theirs)), f"max diff {np.nanmax(np.abs(mine - theirs)):.1e}")

print("\n9. THE 8-MINUTE STATUS BLOCK")
cfg9 = bn_cfg(); om._c467_cfg_ref[0] = cfg9
pf9 = om.Portfolio(cfg9); pf9.equity = pf9.available_balance = 500.0; pf9.session_start_equity = 500.0
b9 = types.SimpleNamespace(cfg=cfg9, portfolio=pf9, _c462_state_settled=True, _c408_asset_class=lambda s: 'crypto',
                           exchange=types.SimpleNamespace(markets={}, get_current_price=lambda s: None),
                           _c482_risk_guard=lambda: {'pct': 20.0, 'month_eq0': 500.0, 'month_budget': 100.0,
                                                     'month_used': 0.0, 'day_cap': 25.0, 'day_used': 0.0, 'halt': ''})
e9 = om.C488Engine(b9); e9.reset(); b9.c488 = e9; pf9._c488 = e9
b9._c504_data_health = lambda now=None: {'ok': True, 'bits': [], 'late': [], 'keys': []}
b9.c489 = om.C489Shadow(b9); b9.c490 = om.C490Carry(b9); b9.c501s = om.C501Spot(b9); b9.c501v = om.C501Savings(b9)
b9.c501k = om.C501Allostatic(b9); b9.c510t = om.C510Tournament(b9)
b9.c521b = b; b9.c521d = dl
rows9 = []
rep9 = om._C462Report(os.path.join(BASE, 'r9.log')); rep9._emit = lambda line: rows9.append(str(line)); rep9.status(b9)
def row9(key):
    """a packed row and its continuation lines (blank label column)"""
    i_ = next((j for j, r_ in enumerate(rows9) if r_.strip().startswith(key)), None)
    if i_ is None:
        return ''
    out = [rows9[i_]]
    for r_ in rows9[i_ + 1:]:
        if r_[:12].strip() or not r_.strip():
            break
        out.append(r_)
    return ' '.join(out)


r_bf, r_dl = row9('BFUSD'), row9('DELTA')
ok("BFUSD: 'wallet $510.00 at 7.66% | +$0.21 so far | ~$3.26/month | vs Savings $1.72 | paper'",
   'wallet $510.00 at 7.66%' in r_bf and '/month' in r_bf and 'vs Savings' in r_bf, r_bf)
ok("DELTA: '$499.xx (-0.xx%) | 12 held | fees | funding | paper, same plan'",
   'held' in r_dl and 'fees' in r_dl and 'funding' in r_dl and 'paper, same plan' in r_dl, r_dl)

print("\n7. THE PAGE (Chromium)")


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
bP.c501k = om.C501Allostatic(bP); bP.c510t = om.C510Tournament(bP)
bP.c521b = b; b.bot = bP
bP.c521d = dl
bP._c504_data_health = lambda now=None: {'ok': True, 'bits': [], 'late': [], 'keys': []}
fbot = types.SimpleNamespace(cfg=cfg, portfolio=pfP, c488=eP, c501s=bP.c501s, c501v=bP.c501v, c501k=bP.c501k,
                             c489=bP.c489, c490=bP.c490, c510t=bP.c510t, c521b=b, c521d=dl,
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
        pg.on('pageerror', lambda x: errs.append(str(x)))
        pg.goto(f'http://127.0.0.1:{port}/?t={TOKEN}'); pg.wait_for_timeout(3000)
        bft, dlt, run = pg.inner_text('#bfusd'), pg.inner_text('#delta'), pg.inner_text('#running')
        br.close()
    ok("the BFUSD panel: base APY 7.66%, the wallet, earned, a month vs Savings, TDS and its payback",
       'base APY 7.66%' in bft and 'boosted up to 9.51%' in bft and 'vs Savings' in bft and 'TDS' in bft and '/month' in bft, bft[:300])
    ok("the Delta panel: equity, held, gross of planned, fees, funding, the positions, what is not on Delta",
       'Delta' in dlt and 'held' in dlt and 'planned' in dlt and 'funding' in dlt and 'contracts' in dlt
       and 'not on Delta' in dlt and '18% GST' in dlt, dlt[:300])
    ok("'What is running' lists both under PAPER", 'BFUSD wallet' in run and 'Delta Exchange India book $500' in run, run[:300])
    ok("no JavaScript errors", not errs, str(errs))
except ImportError:
    ok("Chromium/playwright available for the page check", False)
print("\n" + "=" * 66)
print("ALL CHECKS PASSED" if not fails else f"{len(fails)} FAILURE(S): {fails}")
os._exit(1 if fails else 0)
