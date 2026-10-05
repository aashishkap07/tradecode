#!/usr/bin/env python3
"""C533: the operator's $1000, no reserve -- all of it in Delta vs Pi42 ($500 a venue).

1. The allocation (the defaults) and the research it comes from (research/c533_india_1000.txt).
2. The server's cross-venue ledger, begun at $500, rebased to $1000 (x2): every money figure doubled,
   the Delta contracts doubled, the percentages unchanged.
3. The plan total: $1000, the trade only (no reserve row); its tax at the slab.
4. The margin watch with no reserve: a side under 50% -> "move it NOW" from the other venue.
5. The boot lines and the 8-minute block; the page in Chromium (412 px, a phone).
"""
import os, io, sys, json, time, glob, shutil, types, socket, logging, tempfile, contextlib, importlib.util
REPO = os.path.dirname(os.path.abspath(__file__))
SNAP = os.path.join(REPO, 'research', 'c527_snapshot')
BASE = tempfile.mkdtemp(prefix='c533_test_')
os.environ['OMEGA_BASE_PATH'] = BASE
TOKEN = 'c533-test-token-0123456789abcdef'
os.environ['OMEGA_CTRL_TOKEN'] = TOKEN
fails = []


def ok(n, c, d=''):
    print(f"  {'PASS' if c else 'FAIL'}  {n}" + (f"   {d}" if d else ''))
    if not c:
        fails.append(n)


spec = importlib.util.spec_from_file_location('om533', os.path.join(REPO, 'omega_v60_reconstructed.py'))
om = importlib.util.module_from_spec(spec)
with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
    spec.loader.exec_module(om)
LOG = []
class _H(logging.Handler):
    def emit(self, r): LOG.append((r.levelno, r.getMessage()))
lg = logging.getLogger('OmegaV60'); lg.handlers = [_H()]; lg.propagate = False; lg.setLevel(logging.INFO)
print("=" * 66); print("C533: THE $1000, NO RESERVE -- DELTA vs PI42 $500 + $500"); print("=" * 66)
SRC = open(os.path.join(REPO, 'omega_v60_reconstructed.py')).read()
ok("version C533 or later", int(om._OMEGA_VERSION[1:]) >= 533)

print("\n1. THE ALLOCATION")
c0 = om.Config()
ok("Delta vs Pi42 $1000 = the operator's whole $1000; no reserve; the plan is the trade",
   c0.C524_XVENUE_EQUITY == 1000.0 and c0.C528_BUDGET == 1000.0 and c0.C528_RESERVE == 0.0
   and c0.C532_XV_VENUE == 'pi42' and 'xvenue' in c0.C527_PLAN and 'delta' not in c0.C527_PLAN)
ok("  the two accounts even each other out (the other venue tops a side up); $1 a transfer",
   c0.C531_XV_REBALANCE is True and c0.C531_XV_TRANSFER_FEE == 1.0 and c0.C529_XV_WARN_AT == 0.65
   and c0.C529_XV_RESERVE_AT == 0.50)
ok("  untouched: live locked; the rule (10 pairs, 10% a leg); the book on Delta a $500 experiment; tax 31.2%",
   c0.C488_LIVE_OK is False and c0.C524_XVENUE_PAIRS == 10 and c0.C524_XVENUE_SIZE == 0.10
   and c0.C521_DELTA_EQUITY == 500.0 and c0.C530_PENDLE is False and c0.C528_TAX_RATE == 0.312)
r533 = open(os.path.join(REPO, 'research', 'c533_india_1000.txt')).read()
r532 = open(os.path.join(REPO, 'research', 'c532_india_only.txt')).read()
ok("  the choice is the research's: $1000 no reserve, 3.14%/month after tax at 31.2%, a 2%+ year 76%",
   '$0      $0    $1000 |     +4.27%  86%  55% |     +3.72%  82%  44% |     +3.14%  76%  30%' in r533)
ok("  ... above the same $1000 with a $100 or $50 reserve (2.93%, 3.03%) and the $600 without one (3.08%)",
   '$100    $0    $900  |     +4.01%  85%  50% |     +3.49%  80%  39% |     +2.93%' in r533
   and '$50     $0    $950  |     +4.14%  86%  53% |     +3.60%  81%  41% |     +3.03%' in r533
   and '$0      $0    $600  |     +4.19%  86%  54% |     +3.65%  81%  42% |     +3.08%  75%' in r532)
ok("  the steadier near-tie ($200 book + $800 trade: 3.03%, 77%) is written down beside the setting",
   '$0      $200  $800  |     +4.13%  88%  53% |     +3.60%  84%  41% |     +3.03%  77%' in r533
   and "$200 book +" in SRC)

print("\n2. THE SERVER'S CROSS-VENUE LEDGER, $500 -> $1000")
cfg = om.Config(); cfg.PAPER_MODE = True; cfg.VENUE = 'binance'; om._c467_cfg_ref[0] = cfg
for _k, _v in om._C516_VENUE_DEFAULTS['binance'].items():
    setattr(cfg, _k, _v)
x0 = json.load(open(os.path.join(SNAP, 'c524_xvenue.json')))
for f in glob.glob(os.path.join(SNAP, 'c*.json')):
    shutil.copy(f, BASE)
om._c532_pi42_coins = lambda: None
L = lambda f: json.load(open(os.path.join(SNAP, f + '.json')))
PX = L('prices'); bk0 = L('c488_book')
pf = om.Portfolio(cfg)
cash = bk0['born']['eq'] + sum(c['pnl'] for c in bk0['closed']) + sum(p['funding'] - p['fees'] + p['realized'] for p in bk0['book'].values())
pf.equity = pf.available_balance = cash
bot = types.SimpleNamespace(cfg=cfg, portfolio=pf, _c462_state_settled=True, _c408_asset_class=lambda s: 'crypto',
                            exchange=types.SimpleNamespace(markets={}, get_current_price=lambda s: None),
                            _c482_risk_guard=lambda: {'pct': 20.0, 'month_eq0': 500.0, 'month_budget': 100.0, 'month_used': 0.0,
                                                      'day_cap': 25.0, 'day_used': 0.0, 'halt': ''},
                            _c504_data_health=lambda now=None: {'ok': True, 'bits': [], 'late': [], 'keys': []})
e = om.C488Engine(bot); bot.c488 = e; pf._c488 = e; e.load()
pf.get_live_equity = lambda ex: pf.equity + e.unrealized()
pf.session_start_equity = 500.0; pf.positions = om.PositionsManager()
LOG.clear()
for a, k in (('c501v', 'C501Savings'), ('c501s', 'C501Spot'), ('c490', 'C490Carry'), ('c521d', 'C521Delta'), ('c521b', 'C521Bfusd'),
             ('c524x', 'C524CrossVenue'), ('c530p', 'C530Pendle'), ('c489', 'C489Shadow'), ('c501k', 'C501Allostatic'),
             ('c510t', 'C510Tournament')):
    setattr(bot, a, getattr(om, k)(bot))
xv = bot.c524x; de = bot.c521d
ok("loaded at $500 (the server's ledger), rebased to $1000; the Delta book stays $500",
   x0['start_equity'] == 500.0 and xv.start_equity == 1000.0 and de.start_equity == 500.0)
ok("  every money figure x2: equity, fees, funding, price P&L",
   abs(xv.eq - 2 * x0['eq']) < 1e-6 and abs(xv.fees - 2 * x0['fees']) < 1e-6
   and abs(xv.funding - 2 * x0['funding']) < 1e-6 and abs(xv.price_pnl - 2 * x0['price_pnl']) < 1e-6)
ok("  the return in % is unchanged (a bigger copy of the same trade)",
   abs((xv.eq / xv.start_equity) - (x0['eq'] / x0['start_equity'])) < 1e-9)
dq = {c: (abs(p['d_qty']), abs(xv.pairs[c]['d_qty'])) for c, p in x0['pairs'].items()}
ok("  each Delta leg's whole contracts doubled, its other leg re-matched", all(b == 2 * a for a, b in dq.values() if a >= 1)
   and all(abs(abs(xv.pairs[c]['b_qty']) - 2 * abs(p['b_qty'])) < 1e-9 * max(1, abs(p['b_qty'])) for c, p in x0['pairs'].items()),
   str(dq))
rb = [m for _, m in LOG if 'rebased $500.00 -> $1000.00' in m]
ok("  the rebase is logged (C530 line), with each side's money", len(rb) == 1 and 'Delta side $' in rb[0], rb[0][:200] if rb else '')
ok("  and recorded in the ledger (frm 500 -> to 1000, x2)", xv.rebased[-1]['frm'] == 500.0 and xv.rebased[-1]['to'] == 1000.0
   and xv.rebased[-1]['f'] == 2.0)
xv2 = om.C524CrossVenue(bot)
ok("  a second start does not rebase again", xv2.start_equity == 1000.0 and len(xv2.rebased) == len(xv.rebased))

print("\n3. THE PLAN TOTAL")
NOW = time.time()
e.marks = {om.C488Engine._ccxt(s): dict(bid=b, ask=a, last=(b + a) / 2, fr=0.0, vol=1e9) for s, (b, a) in PX['perp'].items()}
e._marks_at = NOW
bot.c501s.bk = {s: (b, a) for s, (b, a) in PX['spot'].items()}; bot.c501s._book_at = NOW
de.marks = {s: dict(mark=m_, bid=b or m_, ask=a or m_, fr=0.0) for s, (m_, b, a) in PX['delta'].items()}
de._marks_at = NOW
T = om._c527_total(bot, now=NOW)
R = {r['key']: r for r in T['rows']}
ok("the plan = Delta vs Pi42 $1000, nothing else (no reserve row); the books are experiments",
   T['plan']['start'] == 1000.0 and [r['key'] for r in T['rows'] if r['plan']] == ['xvenue']
   and 'reserve' not in R and 'Pi42' in R['xvenue']['label'] and not R['delta']['plan'] and not R['book']['plan'], str(T['plan']))
ok("  the budget: $1000 invested, $0 reserve", T['budget']['invest'] == 1000.0 and T['budget']['reserve'] == 0.0)
ok("  its tax: the trade's net profit at 31.2% (one speculative business)",
   T['tax']['business'] == round(R['xvenue']['pnl'], 2) and T['tax']['vda'] == 0 and T['tax']['rate'] == 0.312)

print("\n4. THE MARGIN WATCH WITH NO RESERVE")
m = xv.margins()
ok("each side starts with half: $500 on Delta, $500 on Pi42", m['d']['start'] == 500.0 and m['b']['start'] == 500.0, str(m))
LOG.clear(); xv._warned = {}
_sd = dict(xv.side)
xv.side = {'d': _sd['d'] - 0.55 * 500.0, 'b': _sd['b'] + 0.55 * 500.0}          # a rally: the Delta (short) side loses
xv.margin_watch()
w = [x for lv, x in LOG if lv >= logging.WARNING and 'C529 cross-venue' in x]
ok("a side under 50%: 'no reserve: LIVE, move $X from Pi42 to Delta NOW'", len(w) == 1
   and 'no reserve: LIVE, move $' in w[0] and 'from Pi42 to Delta NOW' in w[0] and 'reserve held' not in w[0], w[0][:220] if w else '')
LOG.clear(); xv._warned = {}
xv.side = {'d': _sd['d'] - 0.42 * 500.0, 'b': _sd['b'] + 0.42 * 500.0}
xv.margin_watch()
w = [x for lv, x in LOG if lv >= logging.WARNING and 'C529 cross-venue' in x]
ok("  a side under 65%: the daily run moves it from Pi42 (no reserve)", len(w) == 1
   and 'no reserve: the daily run (00:30 UTC) moves $' in w[0] and 'from Pi42' in w[0], w[0][:220] if w else '')
xv.side = _sd; xv._warned = {}

print("\n5. THE BOOT LINES, THE 8-MINUTE BLOCK, THE PAGE")
LOG.clear()
om.TradingBot._c503_running(bot)
bl = [x for _, x in LOG]
pl = [x for x in bl if 'YOUR PLAN' in x]
ok("boot: YOUR PLAN = Delta vs Pi42 $1000 = $1000 of your $1000, no reserve", len(pl) == 1 and '$1000 of your $1000' in pl[0]
   and 'Delta vs Pi42' in pl[0] and 'eserve' not in pl[0], pl[0] if pl else str(bl[:3]))
pp = [x for x in bl if x.strip().startswith('PAPER')]
ok("  the book on Delta is listed as an experiment, the trade at $1000", len(pp) == 1
   and 'the same book on Delta Exchange India, $500 (C521), an experiment' in pp[0] and 'both legs, $1000' in pp[0], pp[0][:300] if pp else '')
fbot = types.SimpleNamespace(cfg=cfg, portfolio=pf, c488=e, c501s=bot.c501s, c501v=bot.c501v, c501k=bot.c501k,
                             c489=bot.c489, c490=bot.c490, c510t=bot.c510t, c521b=bot.c521b, c521d=de, c524x=xv,
                             c530p=bot.c530p,
                             mode_mgr=types.SimpleNamespace(mode=types.SimpleNamespace(value='normal')), exchange=bot.exchange,
                             _c467_day_barrier=lambda: {'pnl': 0.0, 'limit': 9.0, 'used': 0.0, 'frac': 0.0},
                             _c482_risk_guard=bot._c482_risk_guard, _c504_data_health=bot._c504_data_health)
e.refresh_marks = lambda force=False: True
de.refresh_marks = lambda force=False: True
bot.c501s.book = lambda force=False: bot.c501s.bk
de.guard()
rep = om._C462Report(os.path.join(BASE, 'r.log')); rows = []
rep._emit = lambda line: rows.append(str(line))
rep.status(fbot)
keys = [r.strip().split(' ')[0] for r in rows if r.strip()]
ix = [i for i, r in enumerate(rows) if r.strip().startswith('PLAN')]
blk = ' '.join(r.strip() for r in rows[ix[0]:ix[0] + 3]) if ix else ''
ok("the 8-minute block opens with PLAN: of $1,000.00, Delta vs Pi42, no reserve", 'PLAN' in keys
   and keys.index('PLAN') < keys.index('BELOW') < keys.index('EQUITY')
   and 'of $1,000.00' in blk and 'Delta vs Pi42' in blk and 'eserve' not in blk, blk[:300])


def free_port():
    s_ = socket.socket(); s_.bind(('127.0.0.1', 0)); p_ = s_.getsockname()[1]; s_.close(); return p_


port = free_port(); om.RemoteControl(fbot, port=port).start(); time.sleep(0.6)
try:
    from playwright.sync_api import sync_playwright
    exe = (glob.glob('/opt/pw-browsers/chromium-*/chrome-linux/chrome') or [None])[0]
    with sync_playwright() as pw:
        br = pw.chromium.launch(executable_path=exe) if exe else pw.chromium.launch()
        pg = br.new_page(viewport={'width': 412, 'height': 900}); errs = []
        pg.on('pageerror', lambda e_: errs.append(str(e_)))
        pg.goto(f'http://127.0.0.1:{port}/?t={TOKEN}'); pg.wait_for_timeout(3000); pg.evaluate("document.querySelectorAll('details').forEach(function(x){x.open=true})")   # C535: folded panels opened
        G = {k: pg.inner_text('#' + k) for k in ('eqk', 'eqs', 'dayk', 'day', 'days', 'recs', 'running', 'alltotal', 'xvenue')}
        W = pg.evaluate('document.documentElement.scrollWidth')
        br.close()
    ok("the top tile: your plan of $1000 = Delta vs Pi42; no reserve; the books listed as experiments",
       G['eqk'].lower() == 'your plan · paper' and 'of $1000.00' in G['eqs'] and 'Delta vs Pi42 $' in G['eqs']
       and 'reserve' not in G['eqs'].lower().split('experiments')[0] and 'experiments, not in your plan: Binance book' in G['eqs'], G['eqs'])
    ok("the risk tile: your two accounts, the weaker side's %, evened out from the other venue, no reserve",
       G['dayk'].lower() == 'risk · your two accounts' and 'weaker side' in G['day'] and 'Pi42 side' in G['days']
       and '(no reserve: evened out from the other venue below 65%)' in G['days'], G['day'] + ' | ' + G['days'])
    ok("the record tile: Delta vs Pi42; no reserve, no Delta book", 'Delta vs Pi42' in G['recs']
       and 'reserve' not in G['recs'] and 'Delta book' not in G['recs'], G['recs'])
    ok("what is running: YOUR PLAN first; the Binance book an EXPERIMENT", G['running'].startswith('YOUR PLAN')
       and 'EXPERIMENT the paper account (Binance, not your plan)' in G['running'], G['running'][:200])
    ok("the totals: $1000 = $1000 trading, no reserve; the C533 report named; the slab note",
       'your equity $1000.00 = $1000.00 trading, no reserve: a cross-venue side below 65% is topped up from the other venue' in G['alltotal']
       and 'reports/2026-10-04_c533_1000.md' in G['alltotal'] and '₹12 lakh' in G['alltotal'], G['alltotal'][-400:])
    ok("the cross-venue panel: $500 a side; no reserve, below 50% the log says move it NOW",
       'no reserve: below 50% the log says move it NOW' in G['xvenue'] and 'reserve (half on each venue)' not in G['xvenue']
       and 'settled in rupees' in G['xvenue'], G['xvenue'][-400:])
    ok("fits a phone (412 px, no sideways scroll)", W <= 412, str(W))
    ok("no JavaScript errors", not errs, str(errs))
except ImportError:
    ok("Chromium/playwright available for the page check", False)
print("\n" + "=" * 66)
print("ALL CHECKS PASSED" if not fails else f"{len(fails)} FAILURE(S): {fails}")
os._exit(1 if fails else 0)
