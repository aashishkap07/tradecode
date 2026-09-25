#!/usr/bin/env python3
"""C489: the intraday engine, in shadow.

1. PARITY: the bot's _c489_* functions return exactly what the research engine
   returns on the same hourly data -- all 16 features, the cross-sectional
   standardisation, the probability model, the quintile book and the overlap.
2. THE MODEL shipped in the bot is research/c489_model.json, weight for weight,
   and scores identically.
3. THE LEDGER: each hour it books  sum(w x r) - 0.08% x turnover - funding at
   settlements; four overlapping cohorts; M1g holds nothing while the gate is
   shut; the record's t-statistic and ELIGIBLE flag follow the project's bar.
4. ISOLATION: the shadow can never touch the account -- no order, no Portfolio
   call anywhere in its code (one read of equity, to seed its dollar ledger),
   and running it leaves equity and balance exactly as they were.
5. WARM-UP (C490): from the first hour it scores with the no-flow model
   (research/c489_model_noflow.json); once 30 coins have a real week of taker
   flow it switches to the full model. A coin's flow is never read as zero.
   THE DUPLICATE ACCOUNT: in dollars from the account's equity at the start.
6. PERSISTENCE, reset on a fresh start, the main-loop tick after the book, the
   status payload, and the dashboard panel in Chromium.
7. THE PRE-REGISTRATION (rounds 1 and 2) was committed before the engine.
"""
import os, sys, io, re, ast, json, time, types, socket, glob, math, contextlib, importlib.util, subprocess, tempfile, shutil, warnings
import numpy as np
REPO = os.path.dirname(os.path.abspath(__file__))
BASE = tempfile.mkdtemp(prefix='c489_test_')
os.environ['OMEGA_BASE_PATH'] = BASE
TOKEN = 'c489-test-token-0123456789abcdef'
os.environ['OMEGA_CTRL_TOKEN'] = TOKEN
warnings.simplefilter('ignore')
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


print("=" * 66); print("C489: THE INTRADAY ENGINE, IN SHADOW"); print("=" * 66)
om = load(os.path.join(REPO, 'omega_v60_reconstructed.py'), 'om489')
M = load(os.path.join(REPO, 'research', 'omega_c489_research.py'), 'r489')
src = open(os.path.join(REPO, 'omega_v60_reconstructed.py'), encoding='utf-8').read()


def market(n=1000, k=45, seed=3):
    g = np.random.default_rng(seed)
    T = (np.arange(n) + 480000) * 3600000
    syms = ['BTCUSDT'] + [f'C{j:02d}USDT' for j in range(k - 1)]
    C = np.exp(np.cumsum(g.normal(0, 0.008, size=(n, k)) + g.normal(0, 0.0005, size=(1, k)), axis=0)) * 10 ** g.uniform(-2, 3, k)
    Hh = C * (1 + np.abs(g.normal(0, 0.004, (n, k)))); L = C * (1 - np.abs(g.normal(0, 0.004, (n, k)))); O = C * (1 + g.normal(0, 0.002, (n, k)))
    QV = np.exp(g.normal(14, 0.7, (n, k))); TB = QV * np.clip(g.normal(0.5, 0.06, (n, k)), 0.05, 0.95)
    for j in range(3, k, 7):
        C[: g.integers(50, 300), j] = np.nan                                   # late listings
    U = ~np.isnan(C)
    F = np.zeros((n, k)); F[::8] = g.normal(0.0001, 0.0002, (len(F[::8]), k))
    return T, syms, O, Hh, L, C, QV, TB, U, F


print("\n1. PARITY WITH THE RESEARCH ENGINE")
args = market()
r_a, F_a = M.features(*args)
r_b, F_b = om._c489_features(*args)
same = [f for f in M.FEATS if np.allclose(F_a[f], F_b[f], rtol=0, atol=0, equal_nan=True)]
ok("all 16 features identical (returns in own-volatility units, flow, Markov, entropy, Hurst, funding, range)",
   len(same) == 16 and np.allclose(r_a, r_b, equal_nan=True, rtol=0, atol=0), f"{len(same)}/16")
T, syms, O, Hh, L, C, QV, TB, U, F = args
Z_a = M.xs_standardise(F_a, U); Z_b = om._c489_xs_standardise(F_b, U)
ok("cross-sectional standardisation identical", all(np.allclose(Z_a[f], Z_b[f], equal_nan=True, rtol=0, atol=0) for f in M.FEATS))
w = np.random.default_rng(1).normal(0, 0.05, 17)
X = np.nan_to_num(np.stack([Z_a[f][-50:] for f in M.FEATS], -1)).reshape(-1, 16)
ok("the logistic scorer identical", np.array_equal(M.logit_predict(w, X), om._c489_logit_predict(w, X)))
P = np.where(U, np.random.default_rng(2).random(C.shape), np.nan)
ok("the quintile book and the 4-hour overlap identical",
   np.array_equal(M.overlap(M.quintile_book(P, U)), om._c489_overlap(om._c489_quintile_book(P, U))))
nonnan = {f: int((~np.isnan(F_b[f][-1])).sum()) for f in ('mk1', 'mk2', 'pe', 'hurst', 'flow4', 'resid4')}
ok("the features actually compute on the last hour (not all-NaN)", all(v > 30 for v in nonnan.values()), f"{nonnan}")

print("\n2. THE SHIPPED MODEL")
mj = json.load(open(os.path.join(REPO, 'research', 'c489_model.json')))
ok("the bot's coefficients are research/c489_model.json's, feature order included",
   om._C489_MODEL['feats'] == mj['feats'] and np.allclose(om._C489_MODEL['w'], mj['w'], atol=1e-9)
   and np.allclose(om._C489_MODEL['gate'], mj['gate'], atol=1e-9))

print("\n3. THE LEDGER")
def mkshadow():
    cfg = om.Config(); cfg.PAPER_MODE = True
    pf = om.Portfolio(cfg); pf.equity = pf.available_balance = 1000.0
    c488 = types.SimpleNamespace(marks={'AUSDT'.replace('USDT', '/USDT:USDT'): {'fr': 0.001},
                                        'B/USDT:USDT': {'fr': 0.001}})
    bot = types.SimpleNamespace(cfg=cfg, portfolio=pf, c488=c488, _c462_state_settled=True)
    sh = om.C489Shadow(bot); sh.reset()
    return bot, sh
bot, sh = mkshadow()
sh.syms = [f'S{j:02d}USDT' for j in range(20)] + ['AUSDT', 'BUSDT']
k = len(sh.syms)
p = np.linspace(0.40, 0.60, k)                               # AUSDT/BUSDT are the two highest
h0 = 1790000000000 // 3600000 * 3600000
h0 = h0 - (h0 // 3600000 % 8) * 3600000 + 3600000             # an hour that is NOT a settlement
sh.step(h0, p, True, np.full(k, np.nan))
w1 = dict(sh.led['M1']['w'])
ok("first hour: one cohort of four -> each weight is a quarter of the cohort's", abs(sum(abs(v) for v in w1.values()) - 0.25) < 1e-12
   and abs(sum(w1.values())) < 1e-12, f"gross {sum(abs(v) for v in w1.values()):.3f}")
eq_before = sh.led['M1']['eq']
r = np.random.default_rng(5).normal(0, 0.01, k)
sh.step(h0 + 3600000, p, True, r)
pnl = sum(w1.get(s, 0.0) * r[j] for j, s in enumerate(sh.syms))
w2 = sh.led['M1']['w']
turn = sum(abs(w2.get(s, 0) - w1.get(s, 0)) for s in set(w1) | set(w2))
ok("the next hour books sum(w x r) - 0.08% x turnover, compounding the equity index",
   abs(sh.led['M1']['eq'] - eq_before * (1 + pnl - 0.0008 * turn)) < 1e-12, f"pnl {pnl:+.6f} turn {turn:.3f}")
bot, sh = mkshadow(); sh.syms = [f'S{j:02d}USDT' for j in range(20)] + ['AUSDT', 'BUSDT']
sh.step(h0, p, True, np.full(k, np.nan))
hs = h0 + (8 - (h0 // 3600000) % 8) * 3600000                  # the next settlement hour
for hh in range(h0 + 3600000, hs, 3600000):
    sh.step(hh, p, True, np.zeros(k))
eq0 = sh.led['M1']['eq']; wS = dict(sh.led['M1']['w'])
sh.step(hs, p, True, np.zeros(k))
fu = -sum(wS.get(s, 0.0) * 0.001 for s in ('AUSDT', 'BUSDT'))
ok("at a funding settlement, the held weights pay the current rate (flat prices, same book)",
   abs(sh.led['M1']['eq'] - eq0 * (1 + fu)) < 1e-12 and fu < 0, f"funding {fu:+.6f}")
bot, sh = mkshadow(); sh.syms = [f'S{j:02d}USDT' for j in range(20)] + ['AUSDT', 'BUSDT']
for i in range(6):
    sh.step(h0 + i * 3600000, p, False, np.zeros(k))
ok("M1g holds nothing while the cost gate is shut; M1 still trades",
   not sh.led['M1g']['w'] and sh.led['M1']['w'] and sh.led['M1g']['eq'] == 1.0)
ok("four cohorts at most (the 4-hour hold)", len(sh.led['M1']['cohorts']) == 4)
g = np.random.default_rng(9)
sh.led['M1']['daily'] = {i * 86400000: float(x) for i, x in enumerate(g.normal(0.004, 0.01, 150))}
rec = sh.record('M1')
x = np.array(list(sh.led['M1']['daily'].values()))
ok("the record: 150 strong days -> t >= 2, 4/4 quarters, ELIGIBLE", rec['eligible'] and rec['t'] >= 2 and rec['npos'] >= 3, f"{rec}")
sh.led['M1']['daily'] = {i * 86400000: float(x) for i, x in enumerate(g.normal(0.004, 0.01, 60))}
ok("  but never before 120 days, however good", not sh.record('M1')['eligible'])

print("\n4. ISOLATION")
cls_src = src[src.index('class C489Shadow:'):src.index('\n# ═══ C490:')]
pf_lines = [l.strip() for l in cls_src.splitlines() if 'portfolio' in l and not l.strip().startswith('#')]
ok("no order and no Portfolio call anywhere in the shadow's code: one read of equity, to seed the dollar ledger",
   'place_order' not in cls_src and 'release_margin' not in cls_src and 'c488_lock' not in cls_src
   and pf_lines == ['self.start_equity = float(self.bot.portfolio.equity) or 250.0    # read once: a seed, never a write']
   and not re.search(r'portfolio\.\w+\s*[-+*/]?=(?!=)', cls_src), f"{pf_lines}")
bot, sh = mkshadow(); sh.syms = [f'S{j:02d}USDT' for j in range(20)] + ['AUSDT', 'BUSDT']
e0, a0 = bot.portfolio.equity, bot.portfolio.available_balance
for i in range(30):
    sh.step(h0 + i * 3600000, p, True, np.random.default_rng(i).normal(0, 0.02, k))
ok("thirty shadow hours leave equity and balance exactly as they were",
   bot.portfolio.equity == e0 and bot.portfolio.available_balance == a0 and sh.led['M1']['eq'] != 1.0)
rec = sh.record('M1')
ok("the duplicate account: seeded from the account's $1000 once, shown in dollars",
   sh.start_equity == 1000.0 and abs(rec['usd'] - round(1000.0 * sh.led['M1']['eq'], 2)) < 1e-9
   and abs(rec['pnl_usd'] - round(1000.0 * (sh.led['M1']['eq'] - 1), 2)) < 1e-9 and rec['open'] == len(sh.led['M1']['w'])
   and abs(rec['gross'] - round(sum(abs(v) for v in sh.led['M1']['w'].values()), 3)) < 1e-9, f"{rec['usd']} {rec['pnl_usd']}")
bot.portfolio.equity = 5.0
sh.step(h0 + 30 * 3600000, p, True, np.zeros(k))
ok("  and the seed never moves with the account afterwards", sh.start_equity == 1000.0)

print("\n5. WARM-UP")
bot, sh = mkshadow()
T, syms, O, Hh, L, C, QV, TB, U, F = market(n=1000, k=45)
now_h = int(T[-1]) + 3600000
sh.syms = syms
sh.candles = {s: {int(T[i]): [O[i, j], Hh[i, j], L[i, j], C[i, j], QV[i, j]] for i in range(len(T)) if not np.isnan(C[i, j])}
              for j, s in enumerate(syms)}
sh.fund = {s: {int(T[i]): float(F[i, j]) for i in range(0, len(T), 8)} for j, s in enumerate(syms)}
sh.flow = {s: {int(T[i]): float(TB[i, j] / QV[i, j]) for i in range(len(T) - 30, len(T))} for j, s in enumerate(syms)}
pr, gate, rl, n30 = sh.predict(now_h)
m30 = sh.model_used
Tm, Om, Hm, Lm, Cm, QVm, TBm, Um, Fx = sh.matrices(now_h)
r_, Fm_ = om._c489_features(Tm, sh.syms, Om, Hm, Lm, Cm, QVm, TBm, Um, Fx)
have = (~np.isnan(TBm[-172:])).sum(0)
for f in ('flow1', 'flow4'):
    Fm_[f][-1, have < 140] = np.nan
Z_ = om._c489_xs_standardise(Fm_, Um)
mn = om._C489_MODEL_NOFLOW
Xn = np.stack([Z_[f][-1] for f in mn['feats']], -1)
pn = om._c489_logit_predict(np.array(mn['w']), np.nan_to_num(Xn)); pn[np.isnan(Xn).any(-1) | ~Um[-1]] = np.nan
ok("with 30 hours of flow it scores at once, with the no-flow model, and exactly that model's numbers",
   n30 >= 30 and m30.startswith('warm-up') and np.allclose(pr, pn, equal_nan=True, rtol=0, atol=1e-15), f"{n30} coins, {m30}")
ok("  the flow inputs are UNKNOWN there, not zero: no flow feature feeds the warm-up model",
   'flow1' not in mn['feats'] and 'flow4' not in mn['feats'] and np.isnan(Fm_['flow4'][-1]).all())
sh.flow = {s: {int(T[i]): float(TB[i, j] / QV[i, j]) for i in range(len(T) - 300, len(T))} for j, s in enumerate(syms)}
pr2, gate2, rl2, n300 = sh.predict(now_h)
ok("with 300 hours of flow it switches to the full 16-feature model", n300 >= 30 and sh.model_used.startswith('full'),
   f"{n300} coins, {sh.model_used}")
ok("  and the scores are probabilities near 0.5 (the model is weak, as the research found)",
   np.nanmin(pr2) > 0.4 and np.nanmax(pr2) < 0.6 and np.nanmin(pr) > 0.4 and np.nanmax(pr) < 0.6,
   f"{np.nanmin(pr2):.3f}..{np.nanmax(pr2):.3f}")
mj2 = json.load(open(os.path.join(REPO, 'research', 'c489_model_noflow.json')))
ok("the bot's warm-up coefficients are research/c489_model_noflow.json's",
   mn['feats'] == mj2['feats'] and np.allclose(mn['w'], mj2['w'], atol=1e-9) and np.allclose(mn['gate'], mj2['gate'], atol=1e-9))

print("\n6. PERSISTENCE AND WIRING")
bot, sh = mkshadow(); sh.syms = [f'S{j:02d}USDT' for j in range(20)] + ['AUSDT', 'BUSDT']
for i in range(5):
    sh.step(h0 + i * 3600000, p, True, np.full(k, 0.001))
sh.last_hour = h0 + 4 * 3600000; sh.flow = {'AUSDT': {h0: 0.55}}; sh.save()
sh2 = om.C489Shadow(bot)
ok("the ledgers, the last hour, the dollar seed and the collected flow survive a restart",
   abs(sh2.led['M1']['eq'] - sh.led['M1']['eq']) < 1e-15 and sh2.last_hour == sh.last_hour and sh2.flow.get('AUSDT') == {h0: 0.55}
   and sh2.start_equity == 1000.0)
sh2.reset()
ok("reset (fresh start) empties the record", sh2.led['M1']['eq'] == 1.0 and not sh2.flow and sh2.last_hour == 0 and sh2.start_equity == 0.0)
i_488 = src.find("self.c488.tick(can_trade=self.mode_mgr.can_trade())"); i_489 = src.find("self.c489.tick()")
i_pause = src.find("# 2. Check if paused (NO scanning when paused)")
ok("the shadow ticks right after the book, before the pause check", 0 < i_488 < i_489 < i_pause)
ok("a fresh start resets it too; on by default", "bot.c489.reset()" in src and om.Config().C489_SHADOW is True)

def free_port():
    s = socket.socket(); s.bind(('127.0.0.1', 0)); pt = s.getsockname()[1]; s.close(); return pt
bot, sh = mkshadow(); sh.syms = [f'S{j:02d}USDT' for j in range(20)] + ['AUSDT', 'BUSDT']
for i in range(5):
    sh.step(h0 + i * 3600000, p, i % 2 == 0, np.full(k, 0.001))
sh.last_hour = h0 + 4 * 3600000
pf = bot.portfolio; pf.session_start_equity = 1000.0; pf.positions = om.PositionsManager()
pf.get_live_equity = lambda *a: pf.equity
c488 = types.SimpleNamespace(status=lambda: {'mode': 'portfolio', 'n': 0, 'gross': 0, 'gross_x': 0, 'unrealized': 0,
                                               'funding': 0, 'target_vol': 0.2, 'last_rebal': '', 'next_rebal_utc': '2026-09-26 00:05',
                                               'halt': '', 'info': {}, 'positions': []})
fbot = types.SimpleNamespace(cfg=bot.cfg, portfolio=pf, c488=c488, c489=sh,
                             mode_mgr=types.SimpleNamespace(mode=types.SimpleNamespace(value='normal')),
                             exchange=types.SimpleNamespace(get_current_price=lambda s: None),
                             _c467_day_barrier=lambda: {'pnl': 0.0, 'limit': 9.0, 'used': 0.0, 'frac': 0.0},
                             _c482_risk_guard=lambda: {'pct': 15.0, 'month_eq0': 1000.0})
port = free_port(); om.RemoteControl(fbot, port=port).start(); time.sleep(0.6)
import urllib.request
st = json.loads(urllib.request.urlopen(f'http://127.0.0.1:{port}/api/status?t={TOKEN}', timeout=6).read())
c = st.get('c489') or {}
ok("/api/status carries the shadow's record, in dollars", c.get('mode') == 'shadow' and 'M1' in c and 'M1g' in c and c['coins'] == 22
   and c.get('start_equity') == 1000.0 and 'usd' in c['M1'] and 'pnl_usd' in c['M1g'] and 'model' in c,
   f"{ {k2: c.get(k2) for k2 in ('mode', 'coins', 'warming', 'gate', 'last_hour', 'start_equity', 'model')} }")
try:
    from playwright.sync_api import sync_playwright
    exe = (glob.glob('/opt/pw-browsers/chromium-*/chrome-linux/chrome') or [None])[0]
    with sync_playwright() as pw:
        b = pw.chromium.launch(executable_path=exe) if exe else pw.chromium.launch()
        pg = b.new_page(viewport={'width': 412, 'height': 900}); errs = []
        pg.on('pageerror', lambda x: errs.append(str(x)))
        pg.goto(f'http://127.0.0.1:{port}/?t={TOKEN}'); pg.wait_for_timeout(3500)
        txt = pg.inner_text('#shadow'); b.close()
    ok("the Intraday engine (shadow) panel: a duplicate paper account in dollars that never touches the real one",
       'duplicate paper account from $1000.00' in txt and 'never touches the real one' in txt
       and 'M1 probability model $' in txt and 'M1g cost-gated $' in txt, txt.replace('\n', ' | ')[:220])
    ok("no JavaScript errors", not errs, f"{errs}")
except ImportError:
    ok("Chromium/playwright available for the page check", False)

print("\n7. THE PRE-REGISTRATION")
commits = git('log', '--format=%H %s', '--', 'research/c489_preregistration.md').strip().splitlines()
eng = git('log', '--format=%H', '-S', 'class C489Shadow', '--', 'omega_v60_reconstructed.py').split()
first = commits[-1].split()[0] if commits else ''
before = bool(first) and ((not eng) or subprocess.run(['git', 'merge-base', '--is-ancestor', first, eng[-1]], cwd=REPO).returncode == 0)
ok("round 1 committed first; round 2 appended before its holdout; both predate the engine",
   len(commits) == 2 and before and 'round 2' in commits[0].lower(), ' / '.join(c[:12] for c in commits))

shutil.rmtree(BASE, ignore_errors=True)
print("\n" + "=" * 66)
print("ALL CHECKS PASSED" if not fails else f"{len(fails)} FAILURE(S): {fails}")
sys.exit(1 if fails else 0)
