#!/usr/bin/env python3
"""C486: the votes the live record was earned with, and numbers a restart cannot reset.

1. tier_model and score_accel are back to EXACTLY their pre-C485 live values:
   the restored explicit code is run beside the pre-C485 source from git on
   real candle windows and must agree on every value (and actually vote).
   Negative control: the C485 source casts 0 for both.
2. /api/status: the session P&L reads the portfolio's session baseline (it
   read a field the mode manager does not have, so it was always +$0.00),
   and it now carries the all-time record. Negative control: the C485 status
   says +$0.00 for a session that is down $1.40.
3. The page, rendered in Chromium, shows "this run", "today" and "all-time".
4. The RISK line prints the guard's fixed month budget, not dial x today's
   equity. Negative control: the C485 line prints $38.41 beside a $37.92 guard.
"""
import os, sys, io, re, ast, json, time, types, socket, datetime, contextlib, importlib.util, subprocess, tempfile, shutil, glob
import urllib.request, urllib.error
import numpy as np
REPO = os.path.dirname(os.path.abspath(__file__))
os.environ.setdefault('OMEGA_BASE_PATH', '/tmp/omega_c486_test')
os.makedirs(os.environ['OMEGA_BASE_PATH'], exist_ok=True)
TOKEN = 'c486-test-token-0123456789abcdef'
os.environ['OMEGA_CTRL_TOKEN'] = TOKEN
MARK = 'C486: RESTORED, written out'
fails = []


def ok(n, c, d=''):
    print(f"  {'PASS' if c else 'FAIL'}  {n}" + (f"   {d}" if d else ''))
    if not c:
        fails.append(n)


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        spec.loader.exec_module(m)
    return m


def git(*a):
    return subprocess.run(['git', *a], capture_output=True, text=True, cwd=REPO).stdout


def source_before(marker, fallback='HEAD'):
    intro = git('log', '--format=%H', '-S', marker, '--', 'omega_v60_reconstructed.py').split()
    ref = (intro[-1] + '^') if intro else fallback
    return ref, git('show', f'{ref}:omega_v60_reconstructed.py')


def bars(sym, a, b):
    rows = [list(map(float, ln.split(',')[:6])) for ln in open(os.path.join(REPO, 'corpusO', f'{sym}USDT.csv'))
            if ln.count(',') >= 5]
    return np.asarray(sorted(rows))[a:b]


def votes(om, sym, R, start, steps=(0, 7, 19, 26, 33, 47, 61, 70)):
    ta = om.TechnicalAnalysis(om.Config())
    ta._bot_ref = types.SimpleNamespace(_market_bias_resultant=R, _ohlcv_cache={})
    out = []
    for k in steps:
        w = bars(sym.split('/')[0], start + k, start + k + 120)
        res = {'symbol': sym, 'direction': 0, 'components': {}}
        ta._compute_skill_components(w[:, 4], w[:, 5], w[:, 2], w[:, 3], res, sym)
        out.append((res['components'].get('tier_model'), res['components'].get('score_accel')))
    return out


def free_port():
    s = socket.socket(); s.bind(('127.0.0.1', 0)); p = s.getsockname()[1]; s.close(); return p


def serve(om):
    pm = om.PositionsManager()
    pf = types.SimpleNamespace(positions=pm, equity=250.14, session_start_equity=251.54,
                               lifetime_trades=126, lifetime_wins=40, lifetime_losses=86, lifetime_pnl=1.54,
                               session_trades=3, session_wins=0,
                               get_live_equity=lambda *a: 250.14, get_stats=lambda *a: {'live_equity': 250.14})
    bot = types.SimpleNamespace(cfg=om.Config(), portfolio=pf,
                                mode_mgr=types.SimpleNamespace(mode=types.SimpleNamespace(value='normal')),
                                exchange=types.SimpleNamespace(get_current_price=lambda s: None),
                                _c467_day_barrier=lambda: {'pnl': -2.49, 'limit': 9.44, 'used': 2.49, 'frac': 0.26})
    port = free_port()
    om.RemoteControl(bot, port=port).start(); time.sleep(0.6)
    return port


def status(port):
    with urllib.request.urlopen(f'http://127.0.0.1:{port}/api/status?t={TOKEN}', timeout=6) as r:
        return json.loads(r.read().decode())


def render(port):
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        return None
    exe = (glob.glob('/opt/pw-browsers/chromium-*/chrome-linux/chrome') or [None])[0]
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=exe) if exe else p.chromium.launch()
        pg = b.new_page(viewport={'width': 412, 'height': 900}); errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.goto(f'http://127.0.0.1:{port}/?t={TOKEN}'); pg.wait_for_timeout(3500)
        out = dict(eqs=pg.inner_text('#eqs'), recs=pg.inner_text('#recs'), errs=errs)
        b.close()
    return out


print("=" * 66); print("C486: THE LIVE-RECORD VOTES, AND NUMBERS A RESTART CANNOT RESET"); print("=" * 66)
om = load(os.path.join(REPO, 'omega_v60_reconstructed.py'), 'om486')
tmpd = tempfile.mkdtemp(prefix='c486_')
ref485, src_pre485 = source_before('C485: NEUTRALISED')
ref486, src_pre486 = source_before(MARK)
om_pre485 = om_pre486 = None
if src_pre485 and 'C485: NEUTRALISED' not in src_pre485:
    p = os.path.join(tmpd, 'pre485.py'); io.open(p, 'w', encoding='utf-8').write(src_pre485); om_pre485 = load(p, 'om_pre485')
if src_pre486 and MARK not in src_pre486:
    p = os.path.join(tmpd, 'pre486.py'); io.open(p, 'w', encoding='utf-8').write(src_pre486); om_pre486 = load(p, 'om_pre486')
ok("the pre-C485 and pre-C486 sources can be rebuilt from git", om_pre485 is not None and om_pre486 is not None,
   f"{ref485[:10]} / {ref486[:10]}")

print("\n1. THE TWO VOTES ARE EXACTLY WHAT THE LIVE RECORD WAS EARNED WITH")
cases = [(s, R, st) for s in ('BTC', 'ETH', 'SOL', 'AVAX', 'DOGE') for R in (0.6, 0.0, -0.6) for st in (1500, 4200)]
same = 0; seen_t = set(); seen_a = set(); total = 0
for sym, R, st in cases:
    now = votes(om, sym + '/USDT:USDT', R, st) if True else None
    old = votes(om_pre485, sym + '/USDT:USDT', R, st) if om_pre485 else now
    total += len(now)
    same += sum(1 for a, b in zip(now, old) if a == b)
    seen_t |= {v[0] for v in now}; seen_a |= {v[1] for v in now}
ok(f"restored code == pre-C485 code on every value ({total} evaluations, 5 coins, 3 tapes)", same == total, f"{same}/{total}")
ok("tier_model actually votes (short in a rising tape, long in a falling one, +0.05 elsewhere)",
   {-0.25, 0.20, 0.05} <= seen_t, f"{sorted(seen_t)}")
ok("score_accel actually votes (all four contrarian values appear)", {0.25, 0.10, -0.20, -0.10} <= seen_a, f"{sorted(seen_a)}")
if om_pre486:
    z = votes(om_pre486, 'BTC/USDT:USDT', 0.6, 1500)
    ok("NEGATIVE CONTROL: the C485 source casts 0 for both", all(t == 0.0 and a in (0, 0.0) for t, a in z), f"{z[-1]}")

print("\n2. /api/status")
port = serve(om)
st = status(port)
ok("session P&L = equity - the portfolio's session baseline (250.14 - 251.54)", st.get('pnl') == -1.40, f"{st.get('pnl')}")
ok("today's realised P&L travels (survives a restart: anchored at midnight)", (st.get('day') or {}).get('realised') == -2.49)
ok("the all-time record travels", st.get('life') == {'n': 126, 'w': 40, 'l': 86, 'pnl': 1.54}, f"{st.get('life')}")
if om_pre486:
    st_old = status(serve(om_pre486))
    ok("NEGATIVE CONTROL: the C485 status says +$0.00 for a session that is down $1.40",
       st_old.get('pnl') == 0.0 and 'life' not in st_old, f"pnl={st_old.get('pnl')}")

print("\n3. THE PAGE (Chromium)")
r = render(port)
if r is None:
    ok("Chromium/playwright available for the page check", False)
else:
    ok("equity tile: this run -$1.40 · today -$2.49", 'this run -$1.40' in r['eqs'] and 'today -$2.49' in r['eqs'], r['eqs'])
    ok("record tile: all-time 40W 86L · +$1.54", 'all-time 40W 86L' in r['recs'] and '+$1.54' in r['recs'], r['recs'].replace('\n', ' | '))
    ok("no JavaScript errors", not r['errs'], f"{r['errs']}")

print("\n4. THE RISK LINE PRINTS THE GUARD'S MONTH BUDGET")
def lift(text, names, extra):
    tree = ast.parse(text); got = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name in names and node.name not in got:
            got[node.name] = node
    LOG = []
    class L:
        def info(self, m): LOG.append(str(m))
        warning = debug = info
    g = {'time': time, 'logger': L(), 'datetime': datetime, 'os': os, 'math': __import__('math')}
    body = list(got.values()) + extra
    mod = ast.Module(body=[ast.ClassDef(name='B', bases=[], keywords=[], body=body, decorator_list=[])], type_ignores=[])
    ast.fix_missing_locations(mod); exec(compile(mod, '<b>', 'exec'), g)
    return g['B'], LOG
stub = ast.parse("def _c463_realised_payoff(self):\n    return (1.31, 40)\n").body
def banner(text):
    B, LOG = lift(text, ['_c369_apply_budget', '_c369_derive_budget', '_c482_risk_guard'], stub)
    b = B(); b.cfg = om.Config(); b.cfg.C380_MAX_MONTHLY_DD_PCT = 15.0
    b.portfolio = types.SimpleNamespace(equity=256.10, _c482_month={'key': datetime.date.today().strftime('%Y-%m'), 'eq0': 252.81},
                                        save_state=lambda: None)
    b.mode_mgr = types.SimpleNamespace(_day_start_equity=256.10)
    b._c462_state_settled = True; b._c406_budget_key = None
    b._c369_apply_budget(256.10)
    return next((m for m in LOG if 'RISK @' in m), '')
line = banner(io.open(os.path.join(REPO, 'omega_v60_reconstructed.py'), encoding='utf-8').read())
ok("RISK line: 15% of the month-start $252.81 = $37.92/month", '= $37.92/month' in line, line[:90])
if src_pre486:
    old = banner(src_pre486)
    _want = f"= ${256.10 * 15 / 100.0:.2f}/month"          # dial x TODAY's equity, not the month anchor
    ok("NEGATIVE CONTROL: the C485 line printed 15% of today's $256.10, not the guard's $37.92",
       _want in old and '$37.92' not in old, old[:90])

shutil.rmtree(tmpd, ignore_errors=True)
print("\n" + "=" * 66)
print("ALL CHECKS PASSED" if not fails else f"{len(fails)} FAILURE(S): {fails}")
sys.exit(1 if fails else 0)
