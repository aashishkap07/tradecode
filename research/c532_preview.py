#!/usr/bin/env python3
"""C532 preview: what the server's logs and dashboard will show after the update, made from the server's own
state (the 4 Oct logs push) and LIVE prices (Delta, Pi42, Binance through www.binance.com).

    python3 research/c532_preview.py STATE_DIR OUT_DIR

1. the ledgers load as the bot loads them (rebases logged);
2. the boot's "what is running" lines;
3. the cross-venue trade's next daily run, done now on live data (exits 'not on Pi42', entries on Pi42's coins);
4. the 8-minute status block;
5. the dashboard in Chromium (412 px wide, a phone): a full-page screenshot and each panel's text.
Nothing here touches the server; the state is copied to a temporary folder.
"""
import os, io, sys, json, time, glob, shutil, types, socket, logging, tempfile, contextlib, importlib.util
STATE, OUT = sys.argv[1], sys.argv[2]
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = tempfile.mkdtemp(prefix='c532_preview_')
os.environ['OMEGA_BASE_PATH'] = BASE
os.environ['OMEGA_BN_FAPI'] = 'https://www.binance.com'          # the sandbox reaches Binance's futures data here
TOKEN = 'c532-preview-token-0123456789abcdef'
os.environ['OMEGA_CTRL_TOKEN'] = TOKEN
os.makedirs(OUT, exist_ok=True)
for f in glob.glob(os.path.join(STATE, 'c*.json')) + glob.glob(os.path.join(STATE, 'mode_v60.json')):
    if 'pendle' not in os.path.basename(f):
        shutil.copy(f, BASE)
spec = importlib.util.spec_from_file_location('om532p', os.path.join(REPO, 'omega_v60_reconstructed.py'))
om = importlib.util.module_from_spec(spec)
with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
    spec.loader.exec_module(om)
LINES = []
class _H(logging.Handler):
    def emit(self, r):
        LINES.append(f"{time.strftime('%H:%M:%S', time.localtime(r.created))} | {r.getMessage()}")
lg = logging.getLogger('OmegaV60'); lg.handlers = [_H()]; lg.propagate = False; lg.setLevel(logging.INFO)

cfg = om.Config(); cfg.PAPER_MODE = True; cfg.VENUE = 'binance'; om._c467_cfg_ref[0] = cfg
for _k, _v in om._C516_VENUE_DEFAULTS['binance'].items():
    setattr(cfg, _k, _v)
LINES.append(f"--- 1. LOAD (OMEGA {om._OMEGA_VERSION}, the server's 4 Oct state) ---")
bk0 = json.load(open(os.path.join(BASE, 'c488_book.json')))
pf = om.Portfolio(cfg)
cash = bk0['born']['eq'] + sum(c['pnl'] for c in bk0['closed']) + sum(p['funding'] - p['fees'] + p['realized'] for p in bk0['book'].values())
pf.equity = pf.available_balance = cash
pf.session_start_equity = cash
pf.positions = om.PositionsManager()
bot = types.SimpleNamespace(cfg=cfg, portfolio=pf, _c462_state_settled=True, _c408_asset_class=lambda s: 'crypto',
                            exchange=types.SimpleNamespace(markets={}, get_current_price=lambda s: None),
                            _c482_risk_guard=lambda: {'pct': 20.0, 'month_eq0': 500.0, 'month_budget': 100.0, 'month_used': 0.0,
                                                      'day_cap': 25.0, 'day_used': 0.0, 'halt': ''},
                            _c504_data_health=lambda now=None: {'ok': True, 'bits': [], 'late': [], 'keys': []})
e = om.C488Engine(bot); bot.c488 = e; pf._c488 = e; e.load()
pf.get_live_equity = lambda ex: pf.equity + e.unrealized()
for a, k in (('c501v', 'C501Savings'), ('c501s', 'C501Spot'), ('c490', 'C490Carry'), ('c521d', 'C521Delta'),
             ('c521b', 'C521Bfusd'), ('c524x', 'C524CrossVenue'), ('c530p', 'C530Pendle'), ('c489', 'C489Shadow'),
             ('c501k', 'C501Allostatic'), ('c510t', 'C510Tournament')):
    setattr(bot, a, getattr(om, k)(bot))
bot.c538 = [om.C538TestRule(bot, k) for k in ('f8', 'w3') + (('dx',) if 'dx' in getattr(getattr(om, 'C538TestRule', None), 'RULES', {}) else ())] if hasattr(om, 'C538TestRule') else []   # C538; C541: dx
LINES.append("--- 2. LIVE PRICES ---")
t0 = time.time()
ok_b = e.refresh_marks(force=True)
ok_d = bot.c521d.refresh_products(force=True) and bot.c521d.refresh_marks(force=True)
LINES.append(f"(preview) Binance marks {len(e.marks)} ({'ok' if ok_b else 'FAILED'}), Delta tickers {len(bot.c521d.marks)} "
             f"({'ok' if ok_d else 'FAILED'}), Binance prices taken with Delta's: {len(getattr(bot.c521d, 'bn_snap', {}) or {})} [{time.time() - t0:.0f}s]")
LINES.append("--- 3. BOOT: WHAT IS RUNNING ---")
try:
    om.TradingBot._c503_running(bot)
except Exception as ex:
    LINES.append(f"(preview) the boot summary could not run on the preview bot: {type(ex).__name__}: {ex}")
LINES.append("--- 4. THE CROSS-VENUE TRADE'S NEXT DAILY RUN, DONE NOW ON LIVE DATA ---")
xv = bot.c524x
before = sorted(xv.pairs)
try:
    if os.environ.get('OMEGA_PREVIEW_NORUN'):                  # C535: show the server's state as it is
        raise StopIteration('skipped (OMEGA_PREVIEW_NORUN)')
    with xv._lock:
        pnl = xv.run()
    inf = xv.info
    LINES.append(f"(preview) run: day {pnl:+.2f} -> ${xv.eq:.2f}; held before {before}; after {sorted(xv.pairs)}")
    LINES.append(f"(preview) entered: {inf.get('entered')}")
    LINES.append(f"(preview) exited: {inf.get('exited')}")
    LINES.append(f"(preview) {inf.get('wide')} of {inf.get('scored')} coins at 20%/yr+, {inf.get('wide_on')} of them on Pi42 "
                 f"({inf.get('pi42')} Pi42 coins); skipped (one contract > a leg): {inf.get('under_one_contract')}")
    if xv.transfers:
        LINES.append(f"(preview) transfer: {xv.transfers[-1]}")
except Exception as ex:
    LINES.append(f"(preview) the run failed: {type(ex).__name__}: {ex}")
for t538 in bot.c538:                                         # C538: copy the daily ledger, then any decision due now
    try:
        t538.tick()
        st538 = t538.test_status()
        LINES.append(f"(preview) C538 {t538.NAME}: copied {t538.since}, last decision slot "
                     f"{om.datetime.utcfromtimestamp(t538.last_slot / 1000):%Y-%m-%d %H:%M} UTC, {st538['n']} pairs, "
                     f"{st538['same']} the same as the daily rule's, ${t538.eq:.2f} (daily ${xv.eq:.2f})")
    except Exception as ex:
        LINES.append(f"(preview) C538 {getattr(t538, 'NAME', '?')} failed: {type(ex).__name__}: {ex}")
m = xv.margins()
LINES.append(f"(preview) sides now: Delta ${m['d']['eq']} ({m['d']['frac']}), {xv.v2()} ${m['b']['eq']} ({m['b']['frac']})")
xv.margin_watch()
LINES.append("--- 5. THE 8-MINUTE STATUS BLOCK ---")
fbot = types.SimpleNamespace(cfg=cfg, portfolio=pf, c488=e, c501s=bot.c501s, c501v=bot.c501v, c501k=bot.c501k,
                             c489=bot.c489, c490=bot.c490, c510t=bot.c510t, c521b=bot.c521b, c521d=bot.c521d, c524x=xv,
                             c530p=bot.c530p, c538=bot.c538,
                             mode_mgr=types.SimpleNamespace(mode=types.SimpleNamespace(value='normal')), exchange=bot.exchange,
                             _c467_day_barrier=lambda: {'pnl': 0.0, 'limit': 9.0, 'used': 0.0, 'frac': 0.0},
                             _c482_risk_guard=bot._c482_risk_guard, _c504_data_health=bot._c504_data_health)
e.refresh_marks = lambda force=False: True
bot.c521d.refresh_marks = lambda force=False: True
bot.c521d.guard()
rep = om._C462Report(os.path.join(BASE, 'r.log')); rows = []
rep._emit = lambda line: rows.append(str(line))
rep.status(fbot)
LINES.extend(r.rstrip() for r in rows)
T = om._c527_total(fbot)
LINES.append("--- 6. THE PLAN TOTAL ---")
LINES.append(json.dumps(dict(plan=T['plan'], tax=T['tax'], budget=T['budget'],
                             rows=[(r['key'], r['label'], r['start'], r['eq'], r['plan']) for r in T['rows']]), indent=1))


def free_port():
    s_ = socket.socket(); s_.bind(('127.0.0.1', 0)); p_ = s_.getsockname()[1]; s_.close(); return p_


port = free_port(); om.RemoteControl(fbot, port=port).start(); time.sleep(0.8)
from playwright.sync_api import sync_playwright
exe = (glob.glob('/opt/pw-browsers/chromium-*/chrome-linux/chrome') or [None])[0]
panels = {}
with sync_playwright() as pw:
    br = pw.chromium.launch(executable_path=exe) if exe else pw.chromium.launch()
    pg = br.new_page(viewport={'width': 412, 'height': 900}, device_scale_factor=2); errs = []
    pg.on('pageerror', lambda e_: errs.append(str(e_)))
    pg.goto(f'http://127.0.0.1:{port}/?t={TOKEN}'); pg.wait_for_timeout(3500)
    pg.screenshot(path=os.path.join(OUT, 'dashboard_top.png'))
    pg.screenshot(path=os.path.join(OUT, 'dashboard_full.jpg'), full_page=True, type='jpeg', quality=72)
    for k in ('sub', 's-money', 's-acc', 's-pairs', 's-next', 's-test', 'plandetk', 'moresum', 'alltotalk', 'eqk', 'eq', 'eqs', 'day', 'days', 'reck', 'rec', 'recs',
              'running', 'alltotal', 'xvenue', 'delta', 'pendle'):
        try:
            panels[k] = pg.inner_text('#' + k)
        except Exception as ex:
            panels[k] = f'({type(ex).__name__})'
    br.close()
open(os.path.join(OUT, 'panels.txt'), 'w').write('\n\n'.join(f'[{k}]\n{v}' for k, v in panels.items())
                                                  + f"\n\n[JavaScript errors] {errs}\n")
open(os.path.join(OUT, 'log_preview.txt'), 'w').write('\n'.join(LINES) + '\n')
print('\n'.join(LINES))
print('\nJS errors:', errs)
os._exit(0)
