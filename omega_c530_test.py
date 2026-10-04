#!/usr/bin/env python3
"""C530: the operator's new allocation -- $500 book on Delta India, $250 cross-venue, $100 Pendle.

On real data: the server's cross-venue ledger of 4 Oct (research/c530_snapshot/c524_xvenue.json,
AIN +122%), the 3 Oct ledgers and prices (research/c527_snapshot/) and Pendle's market list of
4 Oct 08:46 UTC (research/c530_snapshot/pendle_markets.json).
1. The cross-venue ledger is rebased $500 -> $250 at start: every figure x0.5, Delta legs to whole
   contracts (half up, at least 1), Binance legs re-matched, the two sides still sum to its P&L,
   each side's fraction unchanged, once (a reload does nothing), logged and shown.
2. The Pendle paper ledger, exactly as pre-registered (research/c530_preregistration.md): on the
   real list it picks Ethena sUSDe on Ethereum (5.17%); its costs, its value accruing to 1 at
   expiry, a mark at a new implied APY, maturity and redemption, nothing to buy, a failed read,
   save/load, the VDA tax.
3. The plan: Delta + cross-venue + Pendle = $850, a $100 reserve, inside the $1,000; the tax on the
   trades' net profit and Pendle's gain apart (neither loss offsets the other).
4. The top of the page shows the plan, not the $500 Binance paper book; the risk tile the plan's
   guards; the record tile the plan's; the Pendle panel; no "+-$"; the PENDLE status row; wiring.
"""
import os, io, sys, json, time, glob, shutil, types, socket, logging, tempfile, contextlib, importlib.util
from datetime import datetime, timezone
REPO = os.path.dirname(os.path.abspath(__file__))
SNAP = os.path.join(REPO, 'research', 'c527_snapshot')
SNAP30 = os.path.join(REPO, 'research', 'c530_snapshot')
BASE = tempfile.mkdtemp(prefix='c530_test_')
os.environ['OMEGA_BASE_PATH'] = BASE
TOKEN = 'c530-test-token-0123456789abcdef'
os.environ['OMEGA_CTRL_TOKEN'] = TOKEN
fails = []


def ok(n, c, d=''):
    print(f"  {'PASS' if c else 'FAIL'}  {n}" + (f"   {d}" if d else ''))
    if not c:
        fails.append(n)


spec = importlib.util.spec_from_file_location('om530', os.path.join(REPO, 'omega_v60_reconstructed.py'))
om = importlib.util.module_from_spec(spec)
with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
    spec.loader.exec_module(om)
LOG = []
class _H(logging.Handler):
    def emit(self, r): LOG.append((r.levelno, r.getMessage()))
lg = logging.getLogger('OmegaV60'); lg.handlers = [_H()]; lg.propagate = False
print("=" * 66); print("C530: $500 DELTA BOOK + $250 CROSS-VENUE + $100 PENDLE"); print("=" * 66)
SRC = open(os.path.join(REPO, 'omega_v60_reconstructed.py')).read()
ok("version C530 or later", int(om._OMEGA_VERSION[1:]) >= 530)
c0 = om.Config()
ok("the allocation: cross-venue $250, Pendle $100 (on), the plan = Delta + cross-venue + Pendle, $100 reserve",
   c0.C524_XVENUE_EQUITY == 250.0 and c0.C530_PENDLE is True and c0.C530_PENDLE_EQUITY == 100.0
   and tuple(c0.C527_PLAN) == ('delta', 'xvenue', 'pendle') and c0.C528_RESERVE == 100.0 and c0.C528_BUDGET == 1000.0)
ok("  $500 + $250 + $100 + $100 reserve = $950, inside the $1,000",
   c0.C521_DELTA_EQUITY + c0.C524_XVENUE_EQUITY + c0.C530_PENDLE_EQUITY + c0.C528_RESERVE <= c0.C528_BUDGET)
ok("  untouched: live locked, the cross-venue rule (10 pairs, 10% a leg)", c0.C488_LIVE_OK is False
   and c0.C524_XVENUE_PAIRS == 10 and c0.C524_XVENUE_SIZE == 0.10)
cfg = om.Config(); cfg.PAPER_MODE = True; cfg.VENUE = 'binance'; om._c467_cfg_ref[0] = cfg
for _k, _v in om._C516_VENUE_DEFAULTS['binance'].items():
    setattr(cfg, _k, _v)

# ── 1. the rebase, on the server's 4 Oct ledger ──────────────────────────────
print("\n1. THE CROSS-VENUE LEDGER, $500 -> $250 (THE SERVER'S 4 OCT LEDGER)")
x0 = json.load(open(os.path.join(SNAP30, 'c524_xvenue.json')))
shutil.copy(os.path.join(SNAP30, 'c524_xvenue.json'), BASE)
bx = types.SimpleNamespace(cfg=cfg, _c462_state_settled=True, c488=None, c521d=None)
cfgx = om.Config(); cfgx.VENUE = 'binance'; cfgx.C524_XVENUE_EQUITY = 500.0
x500 = om.C524CrossVenue(types.SimpleNamespace(cfg=cfgx, c488=None, c521d=None))
m500 = x500.margins()
LOG.clear()
x = om.C524CrossVenue(bx)
ok("loaded at $500, rebased to $250 at start", x0['start_equity'] == 500.0 and x.start_equity == 250.0
   and len(x.pairs) == len(x0['pairs']) == 10, f"{x.start_equity}")
ok("  equity, fees, funding, price P&L and both sides x0.5",
   all(abs(getattr(x, k) - 0.5 * x0[k]) < 1e-9 for k in ('eq', 'fees', 'funding', 'price_pnl'))
   and all(abs(x.side[v] - 0.5 * x0['side'][v]) < 1e-9 for v in ('d', 'b')), f"eq {x.eq:.4f} side {x.side}")
ok("  the two sides still sum to its P&L", abs(x.side['d'] + x.side['b'] - (x.eq - x.start_equity))
   - abs(0.5 * (x0['side']['d'] + x0['side']['b'] - (x0['eq'] - x0['start_equity']))) < 1e-9)
good = True; rows = []
for c, p0 in x0['pairs'].items():
    p = x.pairs[c]; k0 = abs(p0['d_qty']); k1 = max(1, int(k0 * 0.5 + 0.5)); r = k1 / k0
    good &= (abs(p['d_qty']) == k1 and (p['d_qty'] < 0) == (p0['d_qty'] < 0) and abs(p['b_qty'] - p0['b_qty'] * r) < 1e-9
             and abs(p['pnl'] - 0.5 * p0['pnl']) < 1e-12 and abs(p['funding'] - 0.5 * p0['funding']) < 1e-12
             and p['d_px'] == p0['d_px'] and p['b_px'] == p0['b_px'] and p['fund_from'] == p0['fund_from'])
    rows.append(f"{c} {int(k0)}->{k1}")
ok("  each Delta leg to whole contracts (half up, sign kept), its Binance leg re-matched, P&L to date x0.5",
   good, ', '.join(rows))
ok("  AIN (the +122% coin): 21 contracts -> 11, its Binance leg x11/21",
   x.pairs['AIN']['d_qty'] == -11.0 and abs(x.pairs['AIN']['b_qty'] - x0['pairs']['AIN']['b_qty'] * 11 / 21) < 1e-9)
m = x.margins()
ok("  each side's start is $125 and its fraction is unchanged (within the whole-contract rounding)",
   m['d']['start'] == 125.0 and m['b']['start'] == 125.0
   and abs(m['d']['frac'] - m500['d']['frac']) < 0.002 and abs(m['b']['frac'] - m500['b']['frac']) < 0.002,
   f"Delta {m500['d']['frac']} -> {m['d']['frac']}, Binance {m500['b']['frac']} -> {m['b']['frac']}")
ok("  each leg's entry notional x its own contracts ratio: ~$25 a leg (10% of $250), AIO 13->7 the most off ($26.28)",
   all(abs(p['notional'] - round(x0['pairs'][c]['notional'] * abs(p['d_qty'] / x0['pairs'][c]['d_qty']), 2)) < 1e-9
       and 24.5 < p['notional'] < 26.5 for c, p in x.pairs.items()),
   ', '.join(f"{c} ${p['notional']}" for c, p in x.pairs.items()))
lines = [t for _, t in LOG if 'C530 cross-venue (paper) rebased' in t]
ok("  logged once: from, to, both sides, the contracts", len(lines) == 1 and '$500.00 -> $250.00' in lines[0]
   and 'AIN 21->11' in lines[0] and 'Delta side' in lines[0], lines[0] if lines else str(LOG[-3:]))
d1 = json.load(open(os.path.join(BASE, 'c524_xvenue.json')))
ok("  saved at once, with the record of the change", d1['start_equity'] == 250.0 and len(d1['rebased']) == 1
   and d1['rebased'][0]['to'] == 250.0 and d1['rebased'][0]['frm'] == 500.0)
LOG.clear()
x2 = om.C524CrossVenue(bx)
ok("  a restart does not rebase again", x2.start_equity == 250.0 and abs(x2.eq - x.eq) < 1e-12
   and not any('rebased' in t for _, t in LOG) and len(x2.rebased) == 1)
st = x2.status()
ok("  its status carries the change (the panel says it)", st['rebased'] and st['rebased'][0]['f'] == 0.5
   and st['start_equity'] == 250.0)
ok("  new pairs are sized from its equity ($25 a leg now): the entry rule is unchanged",
   "n = float(getattr(self.cfg, 'C524_XVENUE_SIZE', 0.10)) * self.eq" in SRC)
os.remove(os.path.join(BASE, 'c524_xvenue.json'))

# ── 2. Pendle ────────────────────────────────────────────────────────────────
print("\n2. PENDLE FIXED YIELD, THE PRE-REGISTERED RULE ON PENDLE'S 4 OCT LIST")
PM = json.load(open(os.path.join(SNAP30, 'pendle_markets.json')))


class _R:
    def __init__(self, d, code=200): self.d, self.status_code = d, code
    def json(self): return self.d


calls = []
real_get = om.requests.get
om.requests.get = lambda url, params=None, timeout=None: (calls.append((url, dict(params or {}))), _R(PM))[1]
mk = om._c530_markets()
ok("the list: one call (83 markets, one page), every market read", mk is not None and len(mk) == 83 and len(calls) == 1
   and calls[0][0] == 'https://api-v2.pendle.finance/core/v2/markets/all' and calls[0][1]['isActive'] == 'true')
T0 = datetime(2026, 10, 4, 8, 46, tzinfo=timezone.utc).timestamp()
best = om._c530_pick(mk, T0)
ok("qualifying: exactly Ethena sUSDe and Sky sUSDS on Ethereum, best first",
   [(m['name'], m['protocol'], m['chain']) for m in best] == [('sUSDe', 'Ethena', 1), ('sUSDS', 'Sky Protocol', 1)],
   str([(m['name'], m['protocol'], m['chain'], round(m['apy'], 4)) for m in best]))
nm = {(m['name'], m['chain'], round((m['expiry'] - T0) / 86400)): m for m in mk}
usdai = [m for m in mk if m['name'] == 'USDai' and m['prime']]
ok("  excluded as registered: prime USDai at 11% (11 days, under 21); reUSD 12% (issuer not listed); "
   "sUSDe on chain 143 (not Ethereum/Arbitrum)",
   usdai and usdai[0]['apy'] > 0.10 and usdai[0] not in best
   and all(m not in best for m in mk if m['name'] == 'reUSD') and all(m['chain'] in (1, 42161) for m in best))
pe = om.C530Pendle(types.SimpleNamespace(cfg=cfg, _c462_state_settled=True))
ok("a fresh ledger: nothing yet", pe.start_equity == 0 and pe.hold is None and pe.active())
eqb = pe.run(now=T0)
h = pe.hold; m0 = best[0]
days = (m0['expiry'] - T0) / 86400.0
cost = 1.0 + 99.0 * (0.0005 + m0['fee'] * days / 365.0)
px = (1 + m0['apy']) ** (-days / 365.0)
ok("it buys sUSDe with the $100: gas $1 + 0.05% + the fee rate x years; PT = (1+APY)^(-days/365)",
   h and h['name'] == 'sUSDe' and abs(h['cost'] - cost) < 1e-9 and abs(h['px_entry'] - px) < 1e-12
   and abs(h['qty'] - (100 - cost) / px) < 1e-9 and pe.cash == 0.0 and pe.rolls == 1,
   f"cost ${cost:.4f}, PT {px:.6f}, {h['qty']:.4f} PT for {days:.1f} d at {100 * m0['apy']:.2f}%")
ok("  right after: worth $100 less its costs", abs(eqb - (100 - cost)) < 1e-9, f"${eqb:.4f}")
v30 = pe.equity(T0 + 30 * 86400)
ok("  30 days on at the same APY it has accrued toward 1 (no read needed)",
   abs(v30 - h['qty'] * (1 + m0['apy']) ** (-(days - 30) / 365.0)) < 1e-9 and v30 > eqb, f"${v30:.4f}")
ok("  at its date it is worth exactly the PTs (1 each)", abs(pe.equity(m0['expiry'] + 1) - h['qty']) < 1e-12)
pay = h['qty'] - 100.0
net = (h['qty'] / 100.0) ** (365.0 / days) - 1
ok("  held to its date: +$%.2f on $100 = %.2f%%/yr after costs (registered: $1 gas, conservative; Ethereum gas was "
   "~$0.20 on 4 Oct)" % (pay, 100 * net), abs(pe.status()['hold']['net_apy'] - round(net, 4)) < 1e-9)
sv = om._c527_savings_apr(pe.bot, cfg)
ok("  and the panel compares it with Binance Savings (here %.2f%%): Savings pays more at this size" % (100 * sv),
   pe.status()['savings_apr'] == round(sv, 4) and net < sv)
PM2 = json.loads(json.dumps(PM))
for r in PM2['results']:
    if r['name'] == 'sUSDe' and r['chainId'] == 1:
        r['details']['impliedApy'] = 0.08
om.requests.get = lambda url, params=None, timeout=None: _R(PM2)
pe._mark(om._c530_markets(), T0 + 86400)
ok("a mark at a higher implied APY (8%): the PT is worth less (bond maths), the holding unchanged",
   h['apy_now'] == 0.08 and abs(pe.value(T0 + 86400) - h['qty'] * 1.08 ** (-(days - 1) / 365.0)) < 1e-9
   and pe.value(T0 + 86400) < h['qty'] * (1 + m0['apy']) ** (-(days - 1) / 365.0))
om.requests.get = lambda url, params=None, timeout=None: _R(PM)
pe.save()
pe2 = om.C530Pendle(types.SimpleNamespace(cfg=cfg, _c462_state_settled=True))
ok("save and load: the same holding and equity", pe2.hold == pe.hold and abs(pe2.equity(T0 + 5e5) - pe.equity(T0 + 5e5)) < 1e-12
   and pe2.rolls == 1 and pe2.last_run == pe.last_run)
TX = m0['expiry'] + 3600
eqx = pe.run(now=TX)
cl = pe.closed[-1] if pe.closed else {}
ok("at maturity it redeems at 1 each: the gain is booked; the 4 Oct list then has no market 21+ days out -> the cash waits",
   cl.get('name') == 'sUSDe' and abs(cl['got'] - round(h['qty'], 4)) < 1e-9 and abs(cl['pnl'] - round(h['qty'] - 100, 4)) < 1e-9
   and pe.hold is None and abs(pe.cash - h['qty']) < 1e-9 and any('waits' in t for t in pe.info['did']),
   '; '.join(pe.info.get('did', [])))
ok("  and says so on its panel", pe.status()['hold'] is None and pe.status()['cash'] == round(h['qty'], 2))
om.requests.get = lambda url, params=None, timeout=None: _R({}, 503)
pe.last_run = ''; pe._tick_at = 0.0; LOG.clear()
pe.tick(now=TX + 86400)
ok("a failed read: no change, a warning, retried in 5 minutes", pe._fail_at == TX + 86400 and pe.last_run == ''
   and any('C530 Pendle read failed' in t for _, t in LOG))
om.requests.get = real_get
stp = pe.status()
ok("its tax is a VDA's: 31.2% of the gain", stp['tax_rate'] == 0.312 and abs(stp['tax'] - round(max(0, stp['pnl']) * 0.312, 2)) < 0.006)
ok("its daily record is kept like the other ledgers'", len(pe.daily) >= 1 and 'record' in stp)
for f in ('c530_pendle.json',):
    try:
        os.remove(os.path.join(BASE, f))
    except OSError:
        pass

# ── 3. the plan, from the 3 Oct ledgers ──────────────────────────────────────
print("\n3. THE PLAN: DELTA $500 + CROSS-VENUE $250 + PENDLE $100")
for f in glob.glob(os.path.join(SNAP, 'c*.json')):
    shutil.copy(f, BASE)
L = lambda f: json.load(open(os.path.join(SNAP, f + '.json')))
PX = L('prices'); bk0 = L('c488_book'); xv0 = L('c524_xvenue')
pf = om.Portfolio(cfg)
cash = bk0['born']['eq'] + sum(c['pnl'] for c in bk0['closed']) + sum(p['funding'] - p['fees'] + p['realized'] for p in bk0['book'].values())
pf.equity = pf.available_balance = cash
bot = types.SimpleNamespace(cfg=cfg, portfolio=pf, _c462_state_settled=True, _c408_asset_class=lambda s: 'crypto',
                            exchange=types.SimpleNamespace(markets={}, get_current_price=lambda s: None),
                            _c482_risk_guard=lambda: {'pct': 20.0})
e = om.C488Engine(bot); bot.c488 = e; pf._c488 = e; e.load()
pf.get_live_equity = lambda ex: pf.equity + e.unrealized()
bot.c501v = om.C501Savings(bot); bot.c501s = om.C501Spot(bot); bot.c490 = om.C490Carry(bot)
bot.c521d = om.C521Delta(bot); bot.c521b = om.C521Bfusd(bot); bot.c524x = om.C524CrossVenue(bot)
NOW = time.time()
e.marks = {om.C488Engine._ccxt(s): dict(bid=b, ask=a, last=(b + a) / 2, fr=0.0, vol=1e9) for s, (b, a) in PX['perp'].items()}
e._marks_at = NOW
bot.c501s.bk = {s: (b, a) for s, (b, a) in PX['spot'].items()}; bot.c501s._book_at = NOW
de = bot.c521d
de.marks = {s: dict(mark=m, bid=b or m, ask=a or m, fr=0.0) for s, (m, b, a) in PX['delta'].items()}
de._marks_at = NOW
bot.c530p = om.C530Pendle(bot)
om.requests.get = lambda url, params=None, timeout=None: _R(PM)
bot.c530p.run(now=NOW)
om.requests.get = real_get
ok("the 3 Oct cross-venue ledger is rebased too ($500 -> $250)", bot.c524x.start_equity == 250.0 and xv0['start_equity'] == 500.0)
T = om._c527_total(bot, now=NOW)
R = {r['key']: r for r in T['rows']}
ok("the plan = Delta book + cross-venue + Pendle, from $850", T['plan']['start'] == 850.0 and T['plan']['n'] == 3
   and [r['key'] for r in T['rows'] if r['plan']] == ['delta', 'xvenue', 'pendle'], str(T['plan']))
ok("  its equity is the three rows' sum", abs(T['plan']['eq'] - (R['delta']['eq'] + R['xvenue']['eq'] + R['pendle']['eq'])) < 0.011)
ok("  Pendle's row: its equity now (the PT accruing), 'paper'", abs(R['pendle']['eq'] - round(bot.c530p.equity(NOW), 2)) < 0.006
   and 'PT at' in R['pendle']['how'], str(R['pendle']))
ok("  the Binance book, Savings, the spot pot and carry are experiments, outside the plan",
   all(not R[k]['plan'] for k in ('book', 'savings', 'spot', 'carry')))
ok("  budget: $100 reserve; plan + reserve inside the $1,000", T['budget'] == {'invest': 1000.0, 'reserve': 100.0}
   and T['plan']['start'] + T['budget']['reserve'] <= T['budget']['invest'])
tx = T['tax']
ok("the tax: the trades' net profit at your slab, Pendle's gain at 31.2%, each never below 0",
   abs(tx['business'] - round(R['delta']['pnl'] + R['xvenue']['pnl'], 2)) < 0.011 and abs(tx['vda'] - R['pendle']['pnl']) < 0.006
   and tx['tax_business'] == round(max(0.0, tx['business']) * 0.312, 2) and tx['tax_vda'] == round(max(0.0, tx['vda']) * 0.312, 2)
   and abs(tx['tax'] - (tx['tax_business'] + tx['tax_vda'])) < 0.006 and abs(tx['eq_after'] - (T['plan']['eq'] - tx['tax'])) < 0.006,
   str(tx))
rows_bak = list(T['rows'])
fake = [dict(r) for r in rows_bak]
cfg.C528_TAX_RATE = 0.104
de.cash += 60.0                                                    # the trades $60 up ...
bot.c530p.cash -= 5.0                                              # ... Pendle $5 down
T3 = om._c527_total(bot, now=NOW)
t3 = T3['tax']
ok("  the trades up, Pendle down: the trades are taxed at your slab in full, Pendle's loss offsets nothing",
   t3['business'] > 0 and t3['vda'] < 0 and t3['tax_vda'] == 0.0 and t3['tax'] == t3['tax_business']
   and t3['tax_business'] == round(t3['business'] * 0.104, 2), str(t3))
de.cash -= 60.0; bot.c530p.cash += 5.0; cfg.C528_TAX_RATE = 0.312

print("\n3b. BOTH LEGS OF A CROSS-VENUE PAIR PRICED AT THE SAME MOMENT")
xvp = bot.c524x
cx = sorted(xvp.pairs)[0]; rawx = cx + 'USDT'; kx = om.C488Engine._ccxt(rawx)
tick = [dict(symbol=s_, mark_price=str(m_), quotes=dict(best_bid=str(b_ or m_), best_ask=str(a_ or m_)), funding_rate='0')
        for s_, (m_, b_, a_) in PX['delta'].items()]
tick += [dict(symbol=f'PAD{i}USD', mark_price='1', quotes={}, funding_rate='0') for i in range(20)]   # a full answer (>= 20)
om._c521_get_real = om._c521_get
om._c521_get = lambda path, params, tries=3: tick if path == '/v2/tickers' else None
e_refresh = e.refresh_marks
e.refresh_marks = lambda force=False: True
ok_ = de.refresh_marks(force=True)
om._c521_get = om._c521_get_real
snap_px = de.bn_at_marks(rawx)
ok("Delta's ticker read also takes Binance's prices at that moment", ok_ and abs(snap_px - e.mark(kx)) < 1e-12
   and abs(de.bn_snap_at - e._marks_at) < 1e-6, f"{cx} {snap_px}")
Ta = {r['key']: r for r in om._c527_total(bot, now=NOW)['rows']}['xvenue']['eq']
b0 = e.marks[kx]; e.marks[kx] = dict(b0, bid=b0['bid'] * 1.05, ask=b0['ask'] * 1.05, last=b0['last'] * 1.05)
Tb = {r['key']: r for r in om._c527_total(bot, now=NOW)['rows']}['xvenue']['eq']
ok("  Binance moves 5% after Delta's read: the plan's cross-venue row does not jump (both legs at Delta's read time)",
   abs(Ta - Tb) < 0.006, f"{Ta} vs {Tb}")
de.bn_snap_at = de._marks_at - 600
Tc = {r['key']: r for r in om._c527_total(bot, now=NOW)['rows']}['xvenue']['eq']
ok("  with no snapshot of that moment it falls back to Binance's latest (the old way), so nothing goes blank",
   abs(Tc - Ta) > 0.01, f"{Ta} -> {Tc}")
e.marks[kx] = b0; de.bn_snap_at = de._marks_at; e.refresh_marks = e_refresh

# ── 4. the page, the status block, the wiring ────────────────────────────────
print("\n4. THE TOP OF THE PAGE IS THE PLAN")


def free_port():
    s_ = socket.socket(); s_.bind(('127.0.0.1', 0)); p_ = s_.getsockname()[1]; s_.close(); return p_


pf.session_start_equity = 500.0
pf.positions = om.PositionsManager()
bot._c482_risk_guard = lambda: {'pct': 20.0, 'month_eq0': 500.0, 'month_budget': 100.0, 'month_used': 0.0,
                                'day_cap': 25.0, 'day_used': 0.0, 'halt': ''}
bot._c504_data_health = lambda now=None: {'ok': True, 'bits': [], 'late': [], 'keys': []}
bot.c489 = om.C489Shadow(bot); bot.c501k = om.C501Allostatic(bot); bot.c510t = om.C510Tournament(bot)
de.guard()
fbot = types.SimpleNamespace(cfg=cfg, portfolio=pf, c488=e, c501s=bot.c501s, c501v=bot.c501v, c501k=bot.c501k,
                             c489=bot.c489, c490=bot.c490, c510t=bot.c510t, c521b=bot.c521b, c521d=de, c524x=bot.c524x,
                             c530p=bot.c530p,
                             mode_mgr=types.SimpleNamespace(mode=types.SimpleNamespace(value='normal')), exchange=bot.exchange,
                             _c467_day_barrier=lambda: {'pnl': 0.0, 'limit': 9.0, 'used': 0.0, 'frac': 0.0},
                             _c482_risk_guard=bot._c482_risk_guard, _c504_data_health=bot._c504_data_health)
e.refresh_marks = lambda force=False: True
de.refresh_marks = lambda force=False: True
bot.c501s.book = lambda force=False: bot.c501s.bk
rep = om._C462Report(os.path.join(BASE, 'r.log')); out = []
rep._emit = lambda line: out.append(str(line))
rep.status(fbot)
ix = [i for i, r in enumerate(out) if r.strip().startswith('PENDLE')]
prow = ' '.join(r.strip() for r in out[ix[0]:ix[0] + 2]) if ix else ''
ok("the log's status block has a PENDLE row: equity, the PT and its date, Savings beside it",
   len(ix) == 1 and 'sUSDe' in prow and 'Savings' in prow and 'paper, fixed yield' in prow, prow)
ix = [i for i, r in enumerate(out) if r.strip().startswith('PLAN')]
ok("  and the PLAN row is from $850", ix and '$850.00' in out[ix[0]], out[ix[0]] if ix else '')
port = free_port(); om.RemoteControl(fbot, port=port).start(); time.sleep(0.6)
try:
    from playwright.sync_api import sync_playwright
    exe = (glob.glob('/opt/pw-browsers/chromium-*/chrome-linux/chrome') or [None])[0]
    with sync_playwright() as pw:
        br = pw.chromium.launch(executable_path=exe) if exe else pw.chromium.launch()
        pg = br.new_page(viewport={'width': 412, 'height': 900}); errs = []
        pg.on('pageerror', lambda e_: errs.append(str(e_)))
        pg.goto(f'http://127.0.0.1:{port}/?t={TOKEN}'); pg.wait_for_timeout(3000)
        G = {k: pg.inner_text('#' + k) for k in ('eqk', 'eq', 'eqs', 'day', 'days', 'reck', 'rec', 'recs', 'pendle',
                                                 'xvenue', 'running', 'alltotal')}
        br.close()
    T = om._c527_total(bot)
    ok("the top tile: 'Your plan · paper' and the plan's equity (was the $500 Binance book)",
       G['eqk'].lower() == 'your plan · paper' and G['eq'] == f"${T['plan']['eq']:.2f}", f"{G['eqk']} {G['eq']}")
    ok("  under it: of $850, after tax, each part, and the Binance book named as an experiment",
       'of $850.00' in G['eqs'] and 'after tax' in G['eqs'] and 'Delta book $' in G['eqs'] and 'cross-venue $' in G['eqs']
       and 'Pendle $' in G['eqs'] and 'Binance book (experiment, not in your plan)' in G['eqs'], G['eqs'])
    ok("the risk tile: the Delta book's own month guard and the cross-venue sides (the plan's exits)",
       'Delta book: month' in G['days'] and 'cross-venue: Delta side' in G['days'] and 'Binance side' in G['days']
       and 'Pendle: fixed to' in G['days'] and G['day'].startswith('20%'), G['days'])
    ok("the record tile: the plan so far, each part's, the target", G['reck'].lower() == 'plan so far' and '%' in G['rec']
       and 'Delta book' in G['recs'] and 'cross-venue' in G['recs'] and 'Pendle' in G['recs'] and '2–4% a month' in G['recs'],
       G['recs'])
    ok("the Pendle panel: the PT, its date, its yield after costs against Savings, what qualifies",
       'sUSDe' in G['pendle'] and 'Ethereum' in G['pendle'] and 'Binance Savings pays' in G['pendle']
       and 'qualifying today (2 of 83)' in G['pendle'] and 'VDA' in G['pendle'], G['pendle'][:500])
    ok("the cross-venue panel: $250, the rebase said, no '+-$'", '$250.00' in G['xvenue'] and 'rebased $500.00 → $250.00' in G['xvenue']
       and '+-$' not in G['xvenue'], G['xvenue'][:300])
    ok("what is running and the totals: Pendle listed, the plan from $850, the tax split, $100 reserve",
       'Pendle fixed yield $100' in G['running'] and '= $850.00' in G['running'] and 'of $850.00' in G['alltotal']
       and "of Pendle's gain" in G['alltotal'] and '$850.00 in the plan + $100.00 reserve' in G['alltotal'], G['alltotal'][-500:])
    ok("no JavaScript errors", not errs, str(errs))
    for k in ('eqk', 'eq', 'eqs', 'day', 'days', 'reck', 'rec', 'recs'):
        print(f"     [{k}] " + G[k].replace('\n', ' | '))
    print('     ' + G['pendle'].replace('\n', '\n     ')[:900])
except ImportError:
    ok("Chromium/playwright available for the page check", False)
ok("wired: created, ticked, reset on a fresh start, in the API and the boot line",
   all(t in SRC for t in ("self.c530p = C530Pendle(self)", "self.c524x, self.c530p,", "bot.c530p.reset()",
                          "_out469['c530'] = bot_ref.c530p.status()", "Pendle fixed yield on a stablecoin, $")))
lp = open(os.path.join(REPO, 'deploy', 'omega-logpush.sh')).read()
ok("the log push sends c530_pendle.json", '"$REPO"/data/c530_pendle.json' in lp)
ok("the bot holds no wallet key and never sends a transaction (paper: one public GET)",
   'eth_sendRawTransaction' not in SRC and 'private_key' not in SRC.split('class C530Pendle')[1].split('def _c527_total')[0])
print("\n" + "=" * 66)
print("ALL CHECKS PASSED" if not fails else f"{len(fails)} FAILURE(S): {fails}")
os._exit(1 if fails else 0)
