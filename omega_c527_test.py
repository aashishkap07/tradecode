#!/usr/bin/env python3
"""C527: every account in one total, as if it were live.

The server's own ledgers (the logs push of 3 Oct 2026 05:47 UTC, research/c527_snapshot/) are
loaded into the real ledger classes and marked at one fixed set of real prices (prices.json, taken
from Binance and Delta at 06:24 UTC). The total is then checked against an independent calculation
written from the ledgers' own arithmetic:
1. each account's row equals its own ledger's equity (the book's includes its exit fee);
2. carry and cross-venue: the daily mark plus the price move since, only from prices under 15 minutes
   old (stale prices: the daily mark alone);
3. the operator's plan (C528) is the book on Delta India + the cross-venue trade ($1,000); 'all' adds
   the Binance book with its Savings, the spot pot and carry;
   BFUSD is shown, not added; the shadow and the tournament are left out and named;
4. the funding settled since carry's and cross-venue's daily run (C527Pending): windows, call counts,
   no double counting once a ledger books it;
5. the Savings rate read from Binance's public listing (tier shared with the spot pot's cash, 6-hour
   refresh, fallbacks);
6. wired into the API, the status block (TOTAL) and the page (Chromium).
"""
import os, io, sys, json, time, glob, shutil, types, socket, logging, tempfile, contextlib, importlib.util
REPO = os.path.dirname(os.path.abspath(__file__))
SNAP = os.path.join(REPO, 'research', 'c527_snapshot')
BASE = tempfile.mkdtemp(prefix='c527_test_')
os.environ['OMEGA_BASE_PATH'] = BASE
TOKEN = 'c527-test-token-0123456789abcdef'
os.environ['OMEGA_CTRL_TOKEN'] = TOKEN
fails = []


def ok(n, c, d=''):
    print(f"  {'PASS' if c else 'FAIL'}  {n}" + (f"   {d}" if d else ''))
    if not c:
        fails.append(n)


for f in glob.glob(os.path.join(SNAP, 'c*.json')):
    shutil.copy(f, BASE)
spec = importlib.util.spec_from_file_location('om527', os.path.join(REPO, 'omega_v60_reconstructed.py'))
om = importlib.util.module_from_spec(spec)
with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
    spec.loader.exec_module(om)
lg = logging.getLogger('OmegaV60'); lg.handlers = [logging.NullHandler()]; lg.propagate = False
print("=" * 66); print("C527: EVERY ACCOUNT IN ONE TOTAL, AS IF LIVE"); print("=" * 66)
SRC = open(os.path.join(REPO, 'omega_v60_reconstructed.py')).read()
ok("version C527 or later", int(om._OMEGA_VERSION[1:]) >= 527)
ok("C528: the book trades 20 coins at every size (top 40 at $1,000 was weaker on the traded rule)", om.Config().C488_TOPN == 20)
cfg = om.Config(); cfg.PAPER_MODE = True; cfg.VENUE = 'binance'; om._c467_cfg_ref[0] = cfg

# C530 changed the operator's allocation ($250 cross-venue, Pendle $100 in the plan, a $100 reserve); this
# test checks its own version's mechanics at the allocation it was written for (omega_c530_test.py checks C530's)
cfg.C524_XVENUE_EQUITY = 500.0; cfg.C527_PLAN = ('delta', 'xvenue'); cfg.C528_RESERVE = 200.0; cfg.C530_PENDLE = False
cfg.C521_DELTA_EQUITY = 500.0; cfg.C528_BUDGET = 1000.0; cfg.C531_XV_REBALANCE = False   # and C531's ($600, no reserve)
for _k, _v in om._C516_VENUE_DEFAULTS['binance'].items():
    setattr(cfg, _k, _v)
L = lambda f: json.load(open(os.path.join(SNAP, f + '.json')))
PX = L('prices')
bk0, sv0, sp0, ca0, de0, xv0, bf0 = (L(f) for f in ('c488_book', 'c501_savings', 'c501_spot', 'c490_carry', 'c521_delta',
                                                     'c524_xvenue', 'c521_bfusd'))
mid = lambda ba: (ba[0] + ba[1]) / 2.0

# ── the bot, from the server's files ──────────────────────────────────────
pf = om.Portfolio(cfg)
# the portfolio's realised equity: the book's start + closed trades + open positions' funding - fees paid
cash = bk0['born']['eq'] + sum(c['pnl'] for c in bk0['closed']) + sum(p['funding'] - p['fees'] + p['realized']
                                                                    for p in bk0['book'].values())
pf.equity = pf.available_balance = cash
bot = types.SimpleNamespace(cfg=cfg, portfolio=pf, _c462_state_settled=True, _c408_asset_class=lambda s: 'crypto',
                            exchange=types.SimpleNamespace(markets={}, get_current_price=lambda s: None),
                            _c482_risk_guard=lambda: {'pct': 20.0})
e = om.C488Engine(bot); bot.c488 = e; pf._c488 = e
e.load()
pf.get_live_equity = lambda ex: pf.equity + e.unrealized()      # paper: realised equity + open P&L at the book's marks
bot.c501v = om.C501Savings(bot); bot.c501s = om.C501Spot(bot); bot.c490 = om.C490Carry(bot)
bot.c521d = om.C521Delta(bot); bot.c521b = om.C521Bfusd(bot); bot.c524x = om.C524CrossVenue(bot)
ok("the server's ledgers loaded: book 9 positions, carry 8, Delta 9, cross-venue 10 pairs",
   len(e.book) == 9 and len(bot.c490.pos) == 8 and len(bot.c521d.pos) == 9 and len(bot.c524x.pairs) == 10
   and not e.venue_block and bool(e.born))
NOW = time.time()


def set_prices(age=0.0):
    e.marks = {om.C488Engine._ccxt(s): dict(bid=b, ask=a, last=(b + a) / 2, fr=0.0, vol=1e9) for s, (b, a) in PX['perp'].items()}
    e._marks_at = NOW - age
    bot.c501s.bk = {s: (b, a) for s, (b, a) in PX['spot'].items()}
    bot.c501s._book_at = NOW - age
    bot.c521d.marks = {s: dict(mark=m, bid=b or m, ask=a or m, fr=0.0) for s, (m, b, a) in PX['delta'].items()}
    bot.c521d._marks_at = NOW - age


set_prices()
T = om._c527_total(bot, now=NOW)
R = {r['key']: r for r in T['rows']}

# ── the independent calculation ───────────────────────────────────────────
print("\n1. EACH ACCOUNT, FROM ITS OWN LEDGER'S ARITHMETIC")
book = cash
for s, p in bk0['book'].items():
    m = mid(PX['perp'][s.split('/')[0] + 'USDT'])
    book += p['qty'] * (m - p['avg']) - abs(p['qty']) * m * 0.0005           # open P&L less the exit taker fee
ok("the book: start + closed + funding - fees + open P&L at the mid - the exit fee (0.05%)",
   abs(R['book']['eq'] - book) < 0.006 and R['book']['start'] == 500.0, f"{R['book']['eq']} vs {book:.4f}")
ok("Savings: the interest so far (an add-on to the book's cash, start 0)",
   abs(R['savings']['eq'] - sv0['interest']) < 0.006 and R['savings']['start'] == 0.0, str(R['savings']))
spot = sp0['cash'] + sum(p['qty'] * mid(PX['spot'][s]) for s, p in sp0['pos'].items())
ok("the spot pot: cash + coins at the spot mid", abs(R['spot']['eq'] - spot) < 0.006 and R['spot']['start'] == 250.0,
   f"{R['spot']['eq']} vs {spot:.4f}")
delta = de0['cash'] + sum(p['qty'] * p['cv'] * (PX['delta'][s][0] - p['avg']) for s, p in de0['pos'].items())
ok("the Delta book: cash + contracts x contract value x (Delta mark - entry)", abs(R['delta']['eq'] - delta) < 0.006,
   f"{R['delta']['eq']} vs {delta:.4f}")

print("\n2. CARRY AND CROSS-VENUE: THE DAILY MARK + THE PRICE MOVE SINCE")
carry = ca0['eq'] + sum(p['qs'] * (mid(PX['spot'][p['spot']]) - p['s']) - p['qp'] * (mid(PX['perp'][r]) - p['p'])
                        for r, p in ca0['pos'].items())
ok("carry: its 00:10 UTC mark + spot leg - perp leg since", abs(R['carry']['eq'] - carry) < 0.006
   and abs(R['carry']['start'] - round(ca0['start_equity'], 2)) < 1e-9 and '8 of 8' in R['carry']['how'],
   f"{R['carry']['eq']} vs {carry:.4f} ({R['carry']['how']})")
xven = xv0['eq'] + sum(p['d_qty'] * p['cv'] * (PX['delta'][p['d_sym']][0] - p['d_px'])
                       + p['b_qty'] * (mid(PX['perp'][c + 'USDT']) - p['b_px']) for c, p in xv0['pairs'].items())
ok("cross-venue: its 00:30 UTC mark + Delta leg + Binance leg since", abs(R['xvenue']['eq'] - xven) < 0.006
   and '10 of 10' in R['xvenue']['how'], f"{R['xvenue']['eq']} vs {xven:.4f}")
ok("  with no reading of the funding settled since, both say it joins at the next hour",
   all('funding since the daily run joins at the next hour' in R[k]['how'] for k in ('carry', 'xvenue')))
set_prices(age=3600)
T2 = om._c527_total(bot, now=NOW)
R2 = {r['key']: r for r in T2['rows']}
ok("prices an hour old: carry and cross-venue fall back to their daily mark (no stale re-mark)",
   abs(R2['carry']['eq'] - round(ca0['eq'], 2)) < 0.006 and abs(R2['xvenue']['eq'] - round(xv0['eq'], 2)) < 0.006
   and '0 of 8' in R2['carry']['how'] and '0 of 10' in R2['xvenue']['how'], f"{R2['carry']} {R2['xvenue']}")
set_prices()

print("\n3. THE TWO TOTALS")
plan = delta + xven
alln = plan + book + sv0['interest'] + spot + carry
ok("C528: the plan = the book on Delta India + the cross-venue trade, from $1,000 (the operator's budget)",
   T['plan']['start'] == 1000.0 and abs(T['plan']['eq'] - plan) < 0.02 and T['plan']['n'] == 2
   and T['plan_names'] == ['Same book on Delta India', 'Delta vs Binance funding gap']
   and T['budget'] == {'invest': 1000.0, 'reserve': 200.0}, f"{T['plan']} vs {plan:.4f} {T.get('plan_names')}")
ok("C528: tax on the plan's NET profit only: a loss is not taxed",
   T['tax']['rate'] == 0.312 and (T['tax']['tax'] == 0.0 if T['plan']['pnl'] <= 0 else abs(T['tax']['tax'] - 0.312 * T['plan']['pnl']) < 0.011)
   and abs(T['tax']['after'] - (T['plan']['pnl'] - T['tax']['tax'])) < 0.011, str(T['tax']))
_tb = types.SimpleNamespace(**{k: getattr(bot, k) for k in ('c488', 'c501v', 'c501s', 'c490', 'c521d', 'c521b', 'c524x')})
_tb.cfg = types.SimpleNamespace(**vars(cfg)); _tb.cfg.C528_TAX_RATE = 0.104
_tb.cfg.C527_PLAN = ('book', 'savings', 'xvenue')
_e0 = e.live_equity; e.live_equity = lambda: 600.0                  # a $100 profit on the book
_T6 = om._c527_total(_tb, now=NOW); e.live_equity = _e0
ok("  a profit is taxed at your slab: C528_TAX_RATE 10.4% on the plan's net profit",
   abs(_T6['tax']['tax'] - round(0.104 * _T6['plan']['pnl'], 2)) < 0.011 and _T6['plan']['pnl'] > 0, str(_T6['tax']))
ok("  the Binance book with its Savings, the spot pot and carry are experiments outside it",
   [r['key'] for r in T['rows'] if not r['plan']] == ['book', 'savings', 'spot', 'carry'])
_cb = types.SimpleNamespace(**vars(cfg)); _cb.C527_PLAN = ('book', 'savings', 'xvenue')
_tb2 = types.SimpleNamespace(**{k: getattr(bot, k) for k in ('c488', 'c501v', 'c501s', 'c490', 'c521d', 'c521b', 'c524x')}, cfg=_cb)
_T7 = om._c527_total(_tb2, now=NOW)
ok("  if the CA rules Binance's futures business income too: C527_PLAN = book + Savings + cross-venue",
   _T7['plan']['n'] == 3 and abs(_T7['plan']['eq'] - (book + sv0['interest'] + xven)) < 0.02)
ok("every account = the plan + the Binance book and Savings + the spot pot + carry, from the sum of their starts",
   abs(T['all']['start'] - (1750 + round(ca0['start_equity'], 2))) < 0.011 and abs(T['all']['eq'] - alln) < 0.04
   and T['all']['n'] == 6, f"{T['all']} vs {alln:.4f}")
ok("  P&L = now - start, and the percentage of the start",
   abs(T['all']['pnl'] - (T['all']['eq'] - T['all']['start'])) < 0.011
   and abs(T['all']['pct'] - 100 * (T['all']['eq'] / T['all']['start'] - 1)) < 0.01)
ok("BFUSD is shown (interest and its TDS), not added: the same wallet as Savings",
   'bfusd' not in R and abs(T['bfusd']['interest'] - bf0['interest']) < 1e-3 and T['bfusd']['tds'] == round(bf0['tds'], 2))
ok("the spot pot's TDS is reported (creditable tax, already inside its figure)", abs(T['tds'] - sp0['tds']) < 1e-3)
bot.c489, bot.c510t = object(), object()
T3 = om._c527_total(bot, now=NOW)
ok("the intraday shadow and the tournament are left out, and named", T3['left_out'] == ['intraday shadow', 'rule tournament']
   and len(T3['rows']) == 6)
ok("paper flag follows PAPER_MODE", T['paper'] is True)
print(f"     at the snapshot's prices: planned ${T['plan']['eq']:.2f} ({T['plan']['pnl']:+.2f}), "
      f"every account ${T['all']['eq']:.2f} of ${T['all']['start']:.2f} ({T['all']['pnl']:+.2f})")

print("\n4. FUNDING SETTLED SINCE THE DAILY RUNS, NOT YET BOOKED (C527Pending)")
H = 3600000
xv, ca = bot.c524x, bot.c490
f0 = min(p['fund_from'] for p in xv.pairs.values())                  # 3 Oct 00:00 UTC
NOWP = f0 / 1000 + 6 * 3600 + 600                                    # 06:10 UTC: settlements at 00, 04 (and 06 hourly-ish) in
calls = {'bn': [], 'delta': []}
RATE_B, RATE_D = 0.0001, 0.02                                        # Binance 0.01%; Delta 0.02% (Delta quotes percent)


def fake_bn(base, path, params, tries=3):
    calls['bn'].append(params['startTime'] + 60000)
    h = params['startTime'] + 60000
    out = []
    for r in list(ca.pos) + [c + 'USDT' for c in xv.pairs]:
        if (h // H) % 4 == 0:
            out.append({'symbol': r, 'fundingTime': h + 7, 'fundingRate': str(RATE_B)})
    return out


def fake_delta(path, params, tries=3):
    calls['delta'].append(params['symbol'])
    return [{'time': t, 'close': RATE_D} for t in range(params['start'], params['end'] + 1, 3600)]   # a record every hour


om._c516_bn_get, om._c521_get = fake_bn, fake_delta
om._C527_EARN.update(at=1e12)                                        # the Savings-rate read is section 5's; none here
xv.prods = {c: dict(sym=p['d_sym'], cv=p['cv'], iv=4 * 3600, taker=0.0005) for c, p in xv.pairs.items()}
P = om.C527Pending(bot); bot.c527p = P
P.tick(now=NOWP)
exp_c = sum(RATE_B * (1 if p['marked'] < t <= NOWP * 1000 else 0) * p['qp'] * mid(PX['perp'][r])
            for r, p in ca0['pos'].items() for t in range(f0 + 7, int(NOWP * 1000), 4 * H))
exp_x = 0.0
for c, p in xv0['pairs'].items():
    n_d = sum(1 for t in range(p['fund_from'] // 1000, int(NOWP) + 1, 3600) if (t // 3600) % 4 == 0)   # 00:00, 04:00
    exp_x += -p['d_qty'] * p['cv'] * PX['delta'][p['d_sym']][0] * RATE_D / 100.0 * n_d
    n_b = sum(1 for t in range(p['fund_from'] + 7, int(NOWP * 1000), 4 * H))
    exp_x += -p['b_qty'] * mid(PX['perp'][c + 'USDT']) * RATE_B * n_b
ok("carry: each position's settlements AFTER its 00:10 mark (04:00 only, not 00:00) x quantity x perp mark",
   abs(P.carry - exp_c) < 1e-9 and P.n_carry == 8, f"{P.carry:.6f} vs {exp_c:.6f}")
ok("cross-venue: from the cut-off (00:00 included, as the ledger books it); Delta's 4-hour coins read only at 00/04 "
   "(the hourly records between are ignored); both legs at their marks", abs(P.xvenue - exp_x) < 1e-9 and P.n_xvenue == 10,
   f"{P.xvenue:.6f} vs {exp_x:.6f}")
ok("one Binance call per hour since 00:00 UTC (every coin at once: 7), one Delta call per pair",
   len(calls['bn']) == len(set(calls['bn'])) == 7 and len(calls['delta']) == 10, f"{len(calls['bn'])} {len(calls['delta'])}")
P.tick(now=NOWP + 120)
ok("  not again within the hour", len(calls['delta']) == 10)
calls['bn'].clear(); calls['delta'].clear()
P.tick(now=NOWP - 600 + 3600 + 200)                                   # 07:03:20 UTC: the next hour, 3 minutes in
ok("  the next hour: one new Binance call (the rest cached) and the pairs again", len(calls['bn']) == 1 and len(calls['delta']) == 10,
   str(calls['bn']))
set_prices()
T4 = om._c527_total(bot, now=NOW)
R4 = {r['key']: r for r in T4['rows']}
ok("the total adds it to carry and cross-venue, and says so",
   abs(R4['xvenue']['eq'] - round(R['xvenue']['eq'] + P.xvenue, 2)) <= 0.011 and 'not yet booked' in R4['xvenue']['how']
   and abs(R4['carry']['eq'] - round(R['carry']['eq'] + P.carry, 2)) <= 0.011, f"{R4['xvenue']} {P.xvenue:.4f}")
k0 = sorted(xv.pairs)[0]; ff = xv.pairs[k0]['fund_from']
xv.pairs[k0]['fund_from'] = ff + 86400000                             # the daily run booked it and moved the cut-off
ok("after the ledger books it (its cut-off moves), the old reading is dropped, not counted twice",
   P.for_total()[1] is None and P.for_total()[0] is not None and P.due(NOWP + 7200 - 3000))
T5 = om._c527_total(bot, now=NOW)
ok("  and the total says the funding joins at the next hour", "joins at the next hour" in {r['key']: r for r in T5['rows']}['xvenue']['how'])
xv.pairs[k0]['fund_from'] = ff
om._c521_get = lambda path, params, tries=3: None
P2 = om.C527Pending(bot); P2.tick(now=NOWP)
ok("a venue that does not answer: nothing shown, retried in 10 minutes", P2.at == 0 and P2._fail_at == NOWP
   and not P2.due(NOWP + 300) and P2.due(NOWP + 700) and P2.for_total() == (None, None))
ok("wired: created, ticked with the paper ledgers", all(t in SRC for t in ("self.c527p = C527Pending(self)", "self.c524x, self.c530p,\n"
                                                                             "                                  self.c527p):")))   # C530: Pendle joined
del bot.c527p

print("\n5. THE SAVINGS RATE READS ITSELF (Binance's public Simple Earn listing)")
# the listing's shape as Binance served it on 3 Oct 2026 (trimmed to the fields read)
LISTING = {'code': '000000', 'success': True, 'data': {'list': [{'asset': 'USDT', 'productDetailList': [
    {'productType': 'LENDING_FLEXIBLE', 'status': 'ENABLE', 'apy': '0.06690948', 'marketApr': '0.02690948',
     'apyTierOption': [{'beginAmount': '0.00000000', 'endAmount': '1000.00000000', 'ratio': '0.04000000'}]}]}]}}
gets = []


class _R:
    def __init__(self, code, j): self.status_code, self._j = code, j
    def json(self): return self._j


real_get = om.requests.get
answer = [_R(200, LISTING)]
om.requests.get = lambda url, params=None, timeout=None: (gets.append(url), answer[0])[1]
om._C527_EARN.update(at=0.0, fail_at=0.0, market=None, bonus=0.0, cap=0.0)
ok("before any read: the configured rate (6.69% on Binance)", abs(bot.c501v.apr() - 0.0669) < 1e-12)
T0 = 1791000000.0
om._c527_earn_refresh(T0)
E = om._C527_EARN
ok("the listing read: market 2.690948% + 4% bonus on the first 1,000 USDT", abs(E['market'] - 0.02690948) < 1e-12
   and E['bonus'] == 0.04 and E['cap'] == 1000.0 and len(gets) == 1)
held = bot.c501v.idle + bot.c501s.cash
ok(f"idle ${bot.c501v.idle:.2f} + spot cash ${bot.c501s.cash:.2f} = ${held:.2f} < 1,000: the full 6.690948%",
   abs(bot.c501v.apr() - 0.06690948) < 1e-12 and abs(om._c527_savings_apr(bot, cfg) - 0.06690948) < 1e-12)
idle0 = bot.c501v.idle; bot.c501v.idle = 1500.0
ok("above 1,000 together, the bonus covers only the first 1,000 (the account shares one tier)",
   abs(bot.c501v.apr() - (0.02690948 + 0.04 * 1000.0 / (1500.0 + bot.c501s.cash))) < 1e-12)
bot.c501v.idle = idle0
om._c527_earn_refresh(T0 + 5 * 3600)
om._c527_earn_refresh(T0 + 6 * 3600 + 1)
ok("read at most every 6 hours", len(gets) == 2)
answer[0] = _R(500, {})
om._c527_earn_refresh(T0 + 12 * 3600 + 2)
om._c527_earn_refresh(T0 + 12 * 3600 + 600)
ok("a failed read keeps the last good rate, warns once, and waits 30 minutes", len(gets) == 3 and E['fail_at'] == T0 + 12 * 3600 + 2
   and abs(bot.c501v.apr() - 0.06690948) < 1e-12)
cfg.C527_SAVINGS_LIVE = False
ok("C527_SAVINGS_LIVE off: the configured rate", abs(bot.c501v.apr() - 0.0669) < 1e-12)
cfg.C527_SAVINGS_LIVE = True
cb = om.Config(); cb.VENUE = 'bitget'
ok("off Binance (Bitget): the configured rate", abs(om._c527_savings_apr(bot, cb) - float(cb.C501_SAVINGS_APR)) < 1e-12)
c0, t0_ = bot.c501s.cash, NOW
bot.c501s._last_ts, bot.c501s._tick_at = t0_, 0.0
bot.c501s.due = lambda now=None: False
bot.c501s.book = lambda force=False: bot.c501s.bk
bot.c501s.tick(now=t0_ + 3600)
ok("the spot pot's cash earns the same rate (one hour)", abs(bot.c501s.cash - c0 * (1 + 0.06690948 * 3600 / (365 * 86400))) < 1e-9,
   f"{bot.c501s.cash - c0:.6f}")
ok("the Savings status says the rate is Binance's own", bot.c501v.status()['apr_live'] is True
   and abs(bot.c501v.status()['apr'] - 0.0669) < 1e-4)
om.requests.get = real_get

print("\n6. WIRED")
ok("in the API, the status block and the page", all(t in SRC for t in ("_out469['c527'] = _c527_total(bot_ref)",
                                                                      "self._pack('PLAN'", 'id="alltotal"', "var tt7=d.c527;")))


def free_port():
    s_ = socket.socket(); s_.bind(('127.0.0.1', 0)); p_ = s_.getsockname()[1]; s_.close(); return p_


pf.session_start_equity = 500.0
pf.positions = om.PositionsManager()
bot._c482_risk_guard = lambda: {'pct': 20.0, 'month_eq0': 500.0, 'month_budget': 100.0, 'month_used': 0.0,
                                'day_cap': 25.0, 'day_used': 0.0, 'halt': ''}
bot._c504_data_health = lambda now=None: {'ok': True, 'bits': [], 'late': [], 'keys': []}
bot.c489 = om.C489Shadow(bot); bot.c501k = om.C501Allostatic(bot); bot.c510t = om.C510Tournament(bot)
fbot = types.SimpleNamespace(cfg=cfg, portfolio=pf, c488=e, c501s=bot.c501s, c501v=bot.c501v, c501k=bot.c501k,
                             c489=bot.c489, c490=bot.c490, c510t=bot.c510t, c521b=bot.c521b, c521d=bot.c521d, c524x=bot.c524x,
                             mode_mgr=types.SimpleNamespace(mode=types.SimpleNamespace(value='normal')), exchange=bot.exchange,
                             _c467_day_barrier=lambda: {'pnl': 0.0, 'limit': 9.0, 'used': 0.0, 'frac': 0.0},
                             _c482_risk_guard=bot._c482_risk_guard, _c504_data_health=bot._c504_data_health)
e.refresh_marks = lambda force=False: True                         # keep the snapshot's prices
bot.c521d.refresh_marks = lambda force=False: True
bot.c501s.book = lambda force=False: bot.c501s.bk
NOW = time.time(); set_prices()
rep = om._C462Report(os.path.join(BASE, 'r.log')); rows = []
rep._emit = lambda line: rows.append(str(line))
rep.status(fbot)
ix = [i for i, r in enumerate(rows) if r.strip().startswith('PLAN')]
tot = ' '.join(r.strip() for r in rows[ix[0]:ix[0] + 3]) if len(ix) == 1 else ''   # a row wraps to the phone's width
ok("the log's status block has a PLAN row: the plan, from its start, and after tax on net profit (C529: no 'all accounts' sum)",
   f"${T['plan']['eq']:,.2f} of ${T['plan']['start']:,.2f}" in tot and 'after tax on net profit' in tot and 'paper' in tot
   and 'all 6 accounts' not in tot, tot or '\n'.join(rows[-12:]))
print('     ' + '\n     '.join(r.rstrip() for r in rows[ix[0]:ix[0] + 3]) if ix else '')
port = free_port(); om.RemoteControl(fbot, port=port).start(); time.sleep(0.6)
try:
    from playwright.sync_api import sync_playwright
    exe = (glob.glob('/opt/pw-browsers/chromium-*/chrome-linux/chrome') or [None])[0]
    with sync_playwright() as pw:
        br = pw.chromium.launch(executable_path=exe) if exe else pw.chromium.launch()
        pg = br.new_page(viewport={'width': 412, 'height': 900}); errs = []
        pg.on('pageerror', lambda e_: errs.append(str(e_)))
        pg.goto(f'http://127.0.0.1:{port}/?t={TOKEN}'); pg.wait_for_timeout(3000)
        txt = pg.inner_text('#alltotal')
        svt = pg.inner_text('#savings')
        br.close()
    ok("the panel: both totals, every account's row, BFUSD and TDS notes, what is left out",
       'your plan (Same book on Delta India + Delta vs Binance funding gap)' in txt and 'every paper account' not in txt
       and 'experiments — paper only, not part of your money, never added up' in txt and 'Main book' in txt
       and 'Delta vs Binance' in txt and 'experiment' in txt and 'budget: $1000.00 in the plan + $200.00 reserve' in txt and 'your equity $1000.00' in txt
       and 'after tax on its net profit' in txt and 'a loss is not taxed' in txt
       and 'BFUSD' in txt and 'TDS' in txt and 'left out' in txt and 'paper' in txt, txt[:700])
    ok("the Savings panel says its rate is Binance's own, read every 6 h", 'rate now, read every 6 h' in svt, svt[:300])
    ok("no JavaScript errors", not errs, str(errs))
    print('     ' + txt.replace('\n', '\n     ')[:1400])
except ImportError:
    ok("Chromium/playwright available for the page check", False)
print("\n" + "=" * 66)
print("ALL CHECKS PASSED" if not fails else f"{len(fails)} FAILURE(S): {fails}")
os._exit(1 if fails else 0)
