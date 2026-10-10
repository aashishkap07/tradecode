#!/usr/bin/env python3
"""C531: the operator's $600, no reserve -- the book on Delta $200, the cross-venue trade $400.

On real data (the server's ledgers: research/c527_snapshot/, research/c530_snapshot/):
1. The allocation: $200 + $400 = the whole $600, no reserve, Pendle off (Savings paid more at $100).
2. The Delta book rebased $500 -> $200 at start: every figure x0.4, contracts to whole numbers, its month
   anchor x0.4, once, logged, shown.
3. The cross-venue ledger rebased $500 -> $400 (AIN 21 -> 17 contracts).
4. No reserve: the two venues' accounts even each other out at the daily run -- below 65% of their mean,
   or monthly when they differ by > 2%; the sender pays the $1 fee; the sides still sum to the P&L; the log
   says the transfer to make live; the hourly margin watch names the amount and direction.
5. The plan total from $600 (Delta + cross-venue only), the budget line, the top tiles and panels in Chromium.
"""
import os, io, sys, json, time, glob, shutil, types, socket, logging, tempfile, contextlib, importlib.util
from datetime import datetime
REPO = os.path.dirname(os.path.abspath(__file__))
SNAP = os.path.join(REPO, 'research', 'c527_snapshot')
SNAP30 = os.path.join(REPO, 'research', 'c530_snapshot')
BASE = tempfile.mkdtemp(prefix='c531_test_')
os.environ['OMEGA_BASE_PATH'] = BASE
TOKEN = 'c531-test-token-0123456789abcdef'
os.environ['OMEGA_CTRL_TOKEN'] = TOKEN
fails = []


def ok(n, c, d=''):
    print(f"  {'PASS' if c else 'FAIL'}  {n}" + (f"   {d}" if d else ''))
    if not c:
        fails.append(n)


spec = importlib.util.spec_from_file_location('om531', os.path.join(REPO, 'omega_v60_reconstructed.py'))
om = importlib.util.module_from_spec(spec)
with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
    spec.loader.exec_module(om)
LOG = []
class _H(logging.Handler):
    def emit(self, r): LOG.append((r.levelno, r.getMessage()))
lg = logging.getLogger('OmegaV60'); lg.handlers = [_H()]; lg.propagate = False
print("=" * 66); print("C531: $600, NO RESERVE -- DELTA BOOK $200 + CROSS-VENUE $400"); print("=" * 66)
SRC = open(os.path.join(REPO, 'omega_v60_reconstructed.py')).read()
ok("version C531 or later", int(om._OMEGA_VERSION[1:]) >= 531)

print("\n1. THE ALLOCATION")
c0 = om.Config()
# C532 changed the operator's plan (the second venue Pi42, $550 + a $50 reserve; omega_c532_test.py checks it).
# This test checks C531's mechanics at the allocation C531 set, pinned below.
C531 = dict(C521_DELTA_EQUITY=200.0, C524_XVENUE_EQUITY=400.0, C528_BUDGET=600.0, C528_RESERVE=0.0, C530_PENDLE=False,
            C531_XV_REBALANCE=True, C531_XV_TRANSFER_FEE=1.0, C527_PLAN=('delta', 'xvenue', 'pendle'), C532_XV_VENUE='binance')
ok("C531's allocation: Delta book $200 + cross-venue $400 = the whole $600; no reserve; the venues re-balance, $1 a transfer",
   C531['C521_DELTA_EQUITY'] + C531['C524_XVENUE_EQUITY'] == C531['C528_BUDGET'] and C531['C528_RESERVE'] == 0.0)
ok("  untouched: live locked; the cross-venue rule (10 pairs, 10% a leg, in at 20%/yr); warn at 65%",
   c0.C488_LIVE_OK is False and c0.C524_XVENUE_PAIRS == 10 and c0.C524_XVENUE_SIZE == 0.10 and c0.C529_XV_WARN_AT == 0.65)
r531 = open(os.path.join(REPO, 'research', 'c531_split_600.txt')).read()
ok("  the choice was the research's: $200/$400 had the best four-case average at the 10.4% slab and stayed positive in the worst",
   '$200  $400  |           +2.28%     +0.12%' in r531)
cfg = om.Config(); cfg.PAPER_MODE = True; cfg.VENUE = 'binance'; om._c467_cfg_ref[0] = cfg
for _k, _v in om._C516_VENUE_DEFAULTS['binance'].items():
    setattr(cfg, _k, _v)
for _k, _v in C531.items():
    setattr(cfg, _k, _v)

print("\n2. THE DELTA BOOK, $500 -> $200 (THE SERVER'S 3 OCT LEDGER)")
d0 = json.load(open(os.path.join(SNAP, 'c521_delta.json')))
shutil.copy(os.path.join(SNAP, 'c521_delta.json'), BASE)
LOG.clear()
bd = types.SimpleNamespace(cfg=cfg, _c462_state_settled=True, c488=None)
dl = om.C521Delta(bd)
f = 0.4
ok("loaded at $500, rebased to $200", d0['start_equity'] == 500.0 and dl.start_equity == 200.0)
ok("  cash, fees, funding, realised x0.4", all(abs(getattr(dl, k) - f * float(d0.get(k) or 0)) < 1e-9
                                               for k in ('cash', 'fees', 'funding', 'realized')), f"cash ${dl.cash:.4f}")
PX = json.load(open(os.path.join(SNAP, 'prices.json')))
dl.marks = {s_: dict(mark=m, bid=b or m, ask=a or m, fr=0.0) for s_, (m, b, a) in PX['delta'].items()}
eq0 = d0['cash'] + sum(p['qty'] * p['cv'] * (PX['delta'][s_][0] - p['avg']) for s_, p in d0['pos'].items())
ok("  every position x0.4 exactly, so its value is x0.4 at any price", all(abs(dl.pos[s_]['qty'] - f * p0['qty']) < 1e-12
   for s_, p0 in d0['pos'].items()) and abs(dl.equity() - f * eq0) < 1e-9 and dl.round_pending,
   f"${dl.equity():.4f} vs 0.4 x ${eq0:.4f}")
tick = [dict(symbol=s_, mark_price=str(m), quotes=dict(best_bid=str(b or m), best_ask=str(a or m)), funding_rate='0')
        for s_, (m, b, a) in PX['delta'].items()] + [dict(symbol=f'PAD{i}USD', mark_price='1', quotes={}, funding_rate='0')
                                                     for i in range(20)]
real_get = om._c521_get
om._c521_get = lambda path, params, tries=3: tick if path == '/v2/tickers' else None
eqb = dl.equity()
dl.refresh_marks(force=True)
om._c521_get = real_get
good, rows = True, []
for s_, p0 in d0['pos'].items():
    k1 = int(abs(p0['qty']) * f + 0.5)
    p = dl.pos.get(s_)
    good &= (p is None and k1 == 0) or (p is not None and abs(p['qty']) == k1 and (p['qty'] < 0) == (p0['qty'] < 0))
    rows.append(f"{s_[:-3]} {int(abs(p0['qty']))}->{k1}")
ok("  at Delta's next prices, whole contracts (nearest; under half a contract closes) and its value does not move",
   good and not dl.round_pending and abs(dl.equity() - eqb) < 1e-9, ', '.join(rows) + f" | ${eqb:.4f} -> ${dl.equity():.4f}")
ok("  logged: what was rounded and the open P&L booked", any("contracts made whole at Delta's prices" in t for _, t in LOG))
if d0.get('month', {}).get('eq0'):
    ok("  its month anchor x0.4 (the guard keeps its percentage)", abs(dl.month['eq0'] - round(f * d0['month']['eq0'], 4)) < 1e-9)
ln = [t for _, t in LOG if 'C531 Delta book (paper) rebased' in t]
ok("  logged once, saved, a restart does nothing more", len(ln) == 1 and '$500.00 -> $200.00' in ln[0]
   and json.load(open(os.path.join(BASE, 'c521_delta.json')))['start_equity'] == 200.0
   and om.C521Delta(bd).start_equity == 200.0 and len([t for _, t in LOG if 'Delta book (paper) rebased' in t]) == 1, ln[0] if ln else '')
ok("  its status says so (the panel shows it)", dl.status()['rebased'][0]['to'] == 200.0)
os.remove(os.path.join(BASE, 'c521_delta.json'))

print("\n3. THE CROSS-VENUE LEDGER, $500 -> $400 (THE SERVER'S 4 OCT LEDGER)")
x0 = json.load(open(os.path.join(SNAP30, 'c524_xvenue.json')))
shutil.copy(os.path.join(SNAP30, 'c524_xvenue.json'), BASE)
bx = types.SimpleNamespace(cfg=cfg, _c462_state_settled=True, c488=None, c521d=None)
x = om.C524CrossVenue(bx)
ok("rebased x0.8: $400, AIN 21 -> 17 contracts, the sides x0.8", x.start_equity == 400.0 and x.pairs['AIN']['d_qty'] == -17.0
   and abs(x.side['d'] - 0.8 * x0['side']['d']) < 1e-9 and abs(x.eq - 0.8 * x0['eq']) < 1e-9, f"eq ${x.eq:.2f}")

print("\n4. NO RESERVE: THE TWO ACCOUNTS EVEN EACH OTHER OUT")
inv = lambda: abs((x.side['d'] + x.side['b']) - (x.eq - x.start_equity)) < 1e-9
ed, eb = 200 + x.side['d'], 200 + x.side['b']
ok("the 4 Oct sides at $400: Delta 78%, Binance 122% of $200 (AIN +122%)", abs(ed / 200 - 0.781) < 0.002 and abs(eb / 200 - 1.219) < 0.002,
   f"Delta ${ed:.2f}, Binance ${eb:.2f}")
LOG.clear(); eqa = x.eq
t1 = x.even_out(datetime(2026, 10, 5, 0, 30))
amt = (eb - ed) / 2
ok("the month's first run: they differ by more than 2% -> Binance sends half the difference, paying the $1 fee",
   t1 and t1['frm'] == 'Binance' and t1['to'] == 'Delta' and abs(t1['amt'] - round(amt, 2)) < 1e-9 and t1['why'] == 'the monthly re-balance'
   and abs((200 + x.side['d']) - (ed + amt)) < 1e-9 and abs((200 + x.side['b']) - (eb - amt - 1.0)) < 1e-9 and abs(x.eq - (eqa - 1.0)) < 1e-9,
   f"{t1}")
ok("  the two sides still sum to the ledger's P&L; the fee is counted", inv() and x.transfer_fees == 1.0)
ok("  the log says the transfer to make live", any('C531 cross-venue (paper): the monthly re-balance -> Binance sends $' in t
                                                   and 'LIVE: make this transfer' in t for _, t in LOG))
ok("  the next day, balanced: nothing moves", x.even_out(datetime(2026, 10, 6, 0, 30)) is None and len(x.transfers) == 1)
x.side['d'] -= 110.0; x.eq -= 110.0                                # a coin squeezes the Delta shorts: -$110 in a day
ed, eb = 200 + x.side['d'], 200 + x.side['b']
t2 = x.even_out(datetime(2026, 10, 7, 0, 30))
ok("a side below 65% of their mean mid-month: evened out at the daily run",
   t2 and t2['frm'] == 'Binance' and 'Delta side at' in t2['why'] and abs(t2['amt'] - round((eb - ed) / 2, 2)) < 1e-9 and inv(),
   f"{t2}")
ok("  a difference smaller than the fee is not worth a transfer", x.even_out(datetime(2026, 11, 1, 0, 30)) is None)
cfg.C531_XV_REBALANCE = False
x.side['d'] -= 90.0; x.eq -= 90.0
ok("  off (C531_XV_REBALANCE = False): nothing moves", x.even_out(datetime(2026, 11, 2, 0, 30)) is None)
cfg.C531_XV_REBALANCE = True
ok("  wired into the daily run before exits and entries, its fee in the day's P&L",
   "tr = self.even_out(datetime.utcfromtimestamp(now_ms / 1000))" in SRC and "day_pnl -= tr['fee']" in SRC)
st = x.status()
ok("  the status lists the transfers and their fees", st['n_transfers'] == 2 and st['transfer_fees'] == 2.0 and st['rebalance'] is True)
LOG.clear(); x._warned = {}
m = x.margins()
x.margin_watch()
w = [t for lv, t in LOG if lv >= logging.WARNING]
give = (m['b']['eq'] - m['d']['eq']) / 2
ok("the hourly watch with no reserve names the amount and the direction: below 50%, 'move it NOW'",
   any(f"move ${give:.2f} from Binance to Delta NOW" in t for t in w), (w[0] if w else 'no warning') + f" | Delta {m['d']['frac']}")
x.side['d'] += 60.0; x.eq += 60.0; x._warned = {}; LOG.clear()
m = x.margins(); x.margin_watch()
w = [t for lv, t in LOG if lv >= logging.WARNING]
give = (m['b']['eq'] - m['d']['eq']) / 2
ok("  between 50% and 65%: the daily run moves it; live, make that transfer",
   any(f"the daily run (00:30 UTC) moves ${give:.2f} from Binance" in t for t in w), (w[0] if w else 'no warning') + f" | Delta {m['d']['frac']}")
x.save()
x2 = om.C524CrossVenue(bx)
ok("  saved and loaded: the transfers, their fees, the month", len(x2.transfers) == 2 and x2.transfer_fees == 2.0 and x2.reb_month == '2026-11')
os.remove(os.path.join(BASE, 'c524_xvenue.json'))

print("\n5. THE PLAN FROM $600, THE PAGE")
for f_ in glob.glob(os.path.join(SNAP, 'c*.json')):
    shutil.copy(f_, BASE)
L = lambda f_: json.load(open(os.path.join(SNAP, f_ + '.json')))
bk0 = L('c488_book')
pf = om.Portfolio(cfg)
cash = bk0['born']['eq'] + sum(c['pnl'] for c in bk0['closed']) + sum(p['funding'] - p['fees'] + p['realized'] for p in bk0['book'].values())
pf.equity = pf.available_balance = cash
bot = types.SimpleNamespace(cfg=cfg, portfolio=pf, _c462_state_settled=True, _c408_asset_class=lambda s: 'crypto',
                            exchange=types.SimpleNamespace(markets={}, get_current_price=lambda s: None),
                            _c482_risk_guard=lambda: {'pct': 20.0})
e = om.C488Engine(bot); bot.c488 = e; pf._c488 = e; e.load()
pf.get_live_equity = lambda ex: pf.equity + e.unrealized()
bot.c501v = om.C501Savings(bot); bot.c501s = om.C501Spot(bot); bot.c490 = om.C490Carry(bot)
bot.c521d = om.C521Delta(bot); bot.c521b = om.C521Bfusd(bot); bot.c524x = om.C524CrossVenue(bot); bot.c530p = om.C530Pendle(bot)
NOW = time.time()
e.marks = {om.C488Engine._ccxt(s): dict(bid=b, ask=a, last=(b + a) / 2, fr=0.0, vol=1e9) for s, (b, a) in PX['perp'].items()}
e._marks_at = NOW
bot.c501s.bk = {s: (b, a) for s, (b, a) in PX['spot'].items()}; bot.c501s._book_at = NOW
de = bot.c521d
de.marks = {s: dict(mark=m_, bid=b or m_, ask=a or m_, fr=0.0) for s, (m_, b, a) in PX['delta'].items()}
de._marks_at = NOW
T = om._c527_total(bot, now=NOW)
R = {r['key']: r for r in T['rows']}
ok("the plan = Delta book + cross-venue, from $600 (Pendle off: not in it)", T['plan']['start'] == 600.0 and T['plan']['n'] == 2
   and [r['key'] for r in T['rows'] if r['plan']] == ['delta', 'xvenue'] and 'pendle' not in R
   and R['delta']['start'] == 200.0 and R['xvenue']['start'] == 400.0, str(T['plan']))
ok("  budget: your $600, no reserve; the tax on the trades' net profit only", T['budget'] == {'invest': 600.0, 'reserve': 0.0}
   and T['tax']['vda'] == 0 and T['tax']['tax'] == round(max(0.0, T['plan']['pnl']) * 0.312, 2), str(T['tax']))


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
ix = [i for i, r in enumerate(out) if r.strip().startswith('PLAN')]
ok("the log's PLAN row is from $600; no PENDLE row", ix and '$600.00' in out[ix[0]] and not any(r.strip().startswith('PENDLE') for r in out),
   out[ix[0]] if ix else '')
port = free_port(); om.RemoteControl(fbot, port=port).start(); time.sleep(0.6)
try:
    from playwright.sync_api import sync_playwright
    exe = (glob.glob('/opt/pw-browsers/chromium-*/chrome-linux/chrome') or [None])[0]
    with sync_playwright() as pw:
        br = pw.chromium.launch(executable_path=exe) if exe else pw.chromium.launch()
        pg = br.new_page(viewport={'width': 412, 'height': 900}); errs = []
        pg.on('pageerror', lambda e_: errs.append(str(e_)))
        pg.goto(f'http://127.0.0.1:{port}/?t={TOKEN}'); pg.wait_for_timeout(3000); pg.evaluate("document.querySelectorAll('details').forEach(function(x){x.open=true})")   # C535: folded panels opened
        G = {k: pg.inner_text('#' + k) for k in ('eqk', 'eq', 'eqs', 'days', 'pendle', 'xvenue', 'delta', 'alltotal', 'running', 'plantotal')}
        G['alltotal'] = G['plantotal'] + '\n' + G['alltotal']   # C539: the plan's total, tax and budget lines moved to "Your plan in detail" (#plantotal)
        br.close()
    ok("the top tile: your plan, of $600, the Delta book and cross-venue; no Pendle", G['eqk'].lower() == 'your plan · paper'
       and 'of $600.00' in G['eqs'] and 'Delta book $' in G['eqs'] and 'Delta vs Binance $' in G['eqs'] and 'Pendle' not in G['eqs'], G['eqs'])
    ok("the risk tile: no reserve, evened out from the other venue", 'no reserve: evened out from the other venue below 65%' in G['days'], G['days'])
    ok("the cross-venue panel: the no-reserve rule; the Delta panel: its rebase", 'below 65% of their mean' in G['xvenue'] and 'no reserve: below 50% the log says move it NOW' in G['xvenue']
       and 'rebased $500.00 → $200.00' in G['delta'], G['xvenue'][-300:])
    ok("the Pendle panel says why it is off", 'off (C530_PENDLE = False since C531' in G['pendle'], G['pendle'][:200])
    ok("the totals: from $600, no reserve; Pendle not running", 'of $600.00' in G['alltotal']
       and 'your equity $600.00 = $600.00 trading, no reserve' in G['alltotal']
       and 'Pendle' not in G['running'], G['alltotal'][-300:])
    ok("no JavaScript errors", not errs, str(errs))
    for k in ('eqk', 'eq', 'eqs', 'days'):
        print(f"     [{k}] " + G[k].replace('\n', ' | '))
except ImportError:
    ok("Chromium/playwright available for the page check", False)
print("\n" + "=" * 66)
print("ALL CHECKS PASSED" if not fails else f"{len(fails)} FAILURE(S): {fails}")
os._exit(1 if fails else 0)
