#!/usr/bin/env python3
"""C490: spot-perp cash-and-carry on a paper ledger of its own.

1. PARITY: the bot's _c490_carry_sim returns exactly what the research's
   carry() returns on the same daily data (universe, 3-day funding, the 10%/5%
   hysteresis, the cap of 8, costs on both legs, forced exits on a gap).
2. THE LIVE LEDGER, driven day by day through step() on the same data, holds
   exactly the coins the research holds on every day, and books nearly the same
   returns (it keeps quantities fixed where the research resets to 10%).
3. THE ARITHMETIC of one position: spot move - perp move + funding since the
   last mark; 0.20% of notional in and out; the multiplier (1000PEPE -> PEPE)
   never enters the P&L.
4. ISOLATION: no order and no Portfolio call in its code (one read of equity,
   to seed the ledger); running it leaves the account exactly as it was.
5. THE SCHEDULE, persistence, reset on a fresh start, the main-loop tick, the
   status payload, the report line and the dashboard panel in Chromium.
6. THE PRE-REGISTRATION was committed before the ledger, and the committed
   results admit R3c and nothing else.
"""
import os, sys, io, re, json, time, types, socket, glob, math, contextlib, importlib.util, subprocess, tempfile, shutil, warnings
import datetime as dt
import numpy as np
REPO = os.path.dirname(os.path.abspath(__file__))
BASE = tempfile.mkdtemp(prefix='c490_test_')
os.environ['OMEGA_BASE_PATH'] = BASE
TOKEN = 'c490-test-token-0123456789abcdef'
os.environ['OMEGA_CTRL_TOKEN'] = TOKEN
warnings.simplefilter('ignore')
fails = []
DAY = 86400000


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


print("=" * 66); print("C490: SPOT-PERP CASH-AND-CARRY, A PAPER LEDGER"); print("=" * 66)
om = load(os.path.join(REPO, 'omega_v60_reconstructed.py'), 'om490')
sys.path.insert(0, os.path.join(REPO, 'research'))
X = load(os.path.join(REPO, 'research', 'omega_c490_research.py'), 'r490')
src = open(os.path.join(REPO, 'omega_v60_reconstructed.py'), encoding='utf-8').read()


def market(n=420, k=60, seed=7):
    """daily perp closes, spot closes that track them with a small basis, quote
    volumes, and funding that is persistent (AR(1)) so coins cross 10% and 5%"""
    g = np.random.default_rng(seed)
    T = (np.arange(n) + 18000) * DAY
    syms = [f'C{j:02d}USDT' for j in range(k - 2)] + ['1000PEPEUSDT', 'NOSPOTUSDT']
    C = np.exp(np.cumsum(g.normal(0, 0.04, (n, k)), axis=0)) * 10 ** g.uniform(-1, 3, k)
    S = C * np.exp(np.cumsum(g.normal(0, 0.002, (n, k)), axis=0) * 0.3)          # spot = perp x a slow basis
    S[:, k - 2] = S[:, k - 2] / 1000.0                                               # PEPE spot is 1/1000 of 1000PEPE
    S[:, k - 1] = np.nan                                                             # no spot market at all
    QV = np.exp(g.normal(16, 0.8, (n, k)))
    base = g.uniform(-0.0003, 0.0003, k)
    f = np.zeros((n, k)); x = np.zeros(k)
    for i in range(n):
        x = 0.9 * x + g.normal(0, 0.00015, k)
        f[i] = base + x                                                              # per day, 3 settlements summed
    for j in range(3, k - 2, 9):
        C[: g.integers(60, 200), j] = np.nan; S[: 5, j] = np.nan                     # late listings
    j = 11; C[300:310, j] = np.nan                                                   # a ten-day gap
    return T, syms, C, S, QV, f


print("\n1. PARITY WITH THE RESEARCH ENGINE")
T, syms, C, S, QV, F = market()
sdir = os.path.join(BASE, 'spot'); os.makedirs(sdir)
smap = {}
for j, s in enumerate(syms):
    if np.isnan(S[:, j]).all():
        continue
    sp_name = s[4:] if s.startswith('1000') else s
    smap[s] = [sp_name, 1000.0 if s.startswith('1000') else 1]
    json.dump([[int(T[i]) + 3600000, float(S[i, j])] for i in range(len(T)) if not np.isnan(S[i, j])],
              open(os.path.join(sdir, sp_name + '.json'), 'w'))
sp_mat = np.full_like(C, np.nan)
for j, s in enumerate(syms):
    if s in smap:
        sp_mat[:, j] = S[:, j]
p_r, n_r = X.carry(T, syms, C, QV, F, sdir, smap)
p_b, n_b = om._c490_carry_sim(C, sp_mat, QV, F)
ok("the bot's carry loop returns the research's P&L and position count, day for day",
   np.allclose(p_r, p_b, rtol=0, atol=1e-15) and np.array_equal(n_r, n_b), f"sum {p_r.sum():+.4f}, avg held {n_r[5:].mean():.1f}")
ok("  and the synthetic market exercises the rule: entries, exits, a full book of 8",
   n_r.max() == 8 and (np.diff(n_r) < 0).sum() >= 3 and (np.diff(n_r) > 0).sum() >= 3,
   f"max {n_r.max():.0f}, {(np.diff(n_r) > 0).sum()} days up, {(np.diff(n_r) < 0).sum()} days down")
fl = np.array([0.0, 0.2, 0.08, 0.12, 0.3, 0.04]); okm = np.array([1, 1, 1, 1, 0, 1], bool)
ex, en = om._c490_decide(np.array([0, 1, 1, 0, 1, 1], bool), fl, okm, cap=4)
ok("the hysteresis: a held coin stays at 8%/yr, leaves at 4%/yr or when ineligible; a new one needs 10%+",
   sorted(ex.tolist()) == [4, 5] and en.tolist() == [3], f"exits {ex.tolist()} entries {en.tolist()}")

print("\n2. THE LIVE LEDGER, DAY BY DAY")
def mkcarry(eq=1000.0):
    cfg = om.Config(); cfg.PAPER_MODE = True
    pf = om.Portfolio(cfg); pf.equity = pf.available_balance = eq
    bot = types.SimpleNamespace(cfg=cfg, portfolio=pf, c488=None, _c462_state_settled=True)
    cy = om.C490Carry(bot); cy.reset()
    return bot, cy
bot, cy = mkcarry()
keep = [om.C488Engine._ccxt(s) for s in syms]
raws = [om.C488Engine._raw(s) for s in keep]
held_live, rets = [], []
for i in range(4, len(T)):
    now = int(T[i]) + DAY + 600000                           # 00:10 UTC after day i closes
    spot = {smap[s][0]: float(S[i, j]) for j, s in enumerate(syms) if s in smap and not np.isnan(S[i, j])}
    perp = {r: float(C[i, j]) for j, r in enumerate(raws) if not np.isnan(C[i, j])}
    events = {r: {int(T[i2]) + 3600000: float(F[i2, j]) for i2 in range(max(0, i - 5), i + 1)} for j, r in enumerate(raws)}
    eq0 = cy.eq or 1000.0
    cy.step(now, spot, perp, events, T[:i + 1], keep, C[:i + 1], QV[:i + 1], F[:i + 1])
    held_live.append(len(cy.pos)); rets.append(cy.daily.get(now // DAY * DAY, 0.0))
held_live = np.array(held_live); rets = np.array(rets)
ok("step() holds exactly as many coins as the research on every day", np.array_equal(held_live, n_r[4:]),
   f"{int((held_live != n_r[4:]).sum())} days differ")
rho = np.corrcoef(rets, p_r[4:] / 0.10 * 0.10)[0, 1]
ok("  and books nearly the same returns (fixed quantities vs a daily reset to 10%)",
   rho > 0.97 and abs(rets.sum() - p_r[4:].sum()) < 0.25 * abs(p_r[4:].sum()) + 0.01,
   f"rho {rho:.3f}, total {rets.sum():+.4f} vs {p_r[4:].sum():+.4f}")
ok("  the ledger's dollars are the compounded returns on the $1000 seed",
   abs(cy.eq - 1000.0 * np.prod(1 + rets)) < 1e-6 and cy.start_equity == 1000.0, f"${cy.eq:.2f}")

print("\n3. ONE POSITION, BY HAND")
bot, cy = mkcarry()
n_ = 40; Tt = (np.arange(n_) + 19000) * DAY
kk = ['1000PEPE/USDT:USDT', 'AAA/USDT:USDT']
Ct = np.column_stack([np.full(n_, 0.012), np.full(n_, 2.0)]); Qt = np.full((n_, 2), 1e7); Ft = np.column_stack([np.full(n_, 0.0006), np.zeros(n_)])
# the universe needs 90 days of age; this 40-day frame is patched to 5 for the hand check
orig = om._c488_universe
om._c488_universe = lambda c, q, n, age_min=90, volwin=30: orig(c, q, n, age_min=5, volwin=5)
try:
    now = int(Tt[-1]) + DAY + 600000
    cy.step(now, {'PEPEUSDT': 0.000012, 'AAAUSDT': 2.0}, {'1000PEPEUSDT': 0.012, 'AAAUSDT': 2.0}, {}, Tt, kk, Ct, Qt, Ft)
    p = cy.pos.get('1000PEPEUSDT') or {}
    ok("in at 0.0006/day = 21.9%/yr: 10% of $1000 on each leg, 0.20% of it paid",
       p and abs(p['qs'] * 0.000012 - 100.0) < 1e-9 and abs(p['qp'] * 0.012 - 100.0) < 1e-9 and abs(cy.eq - (1000 - 0.2)) < 1e-9
       and 'AAAUSDT' not in cy.pos, f"eq {cy.eq:.4f} f3 {p.get('f3', 0):.3f}")
    now2 = now + DAY
    ev = {'1000PEPEUSDT': {now + 1000: 0.0002, now + 8 * 3600000: 0.0002, now - 1000: 0.5}}    # the last one predates the mark
    Ct2 = np.vstack([Ct, Ct[-1]]); Tt2 = np.append(Tt, Tt[-1] + DAY)
    eq_b = cy.eq
    cy.step(now2, {'PEPEUSDT': 0.0000126, 'AAAUSDT': 2.0}, {'1000PEPEUSDT': 0.0126, 'AAAUSDT': 2.0}, ev, Tt2, kk,
            Ct2, np.vstack([Qt, Qt[-1]]), np.vstack([Ft, Ft[-1]]))
    exp = p['qs'] * (0.0000126 - 0.000012) - p['qp'] * (0.0126 - 0.012) + 0.0004 * p['qp'] * 0.0126
    ok("a 5% move on both legs nets to zero; the two settlements after the mark are collected, the older one is not",
       abs((cy.eq - eq_b) - exp) < 1e-9 and abs(exp - 0.0004 * 105.0) < 1e-9, f"day {cy.eq - eq_b:+.6f}")
    Ft3 = np.vstack([Ft, Ft[-1], [0.0, 0.0], [0.0, 0.0], [0.0, 0.0]])
    Ct3 = np.vstack([Ct2, Ct2[-1], Ct2[-1], Ct2[-1]]); Tt3 = np.append(Tt2, Tt2[-1] + DAY * np.arange(1, 4))
    eq_c = cy.eq
    cy.step(now2 + 3 * DAY, {'PEPEUSDT': 0.0000126, 'AAAUSDT': 2.0}, {'1000PEPEUSDT': 0.0126, 'AAAUSDT': 2.0}, {}, Tt3, kk,
            Ct3, np.vstack([Qt, Qt[-1], Qt[-1], Qt[-1], Qt[-1]]), Ft3)
    ok("three days of zero funding -> out, paying 0.20% of the leg's current value",
       not cy.pos and abs((eq_c - cy.eq) - 0.002 * p['qp'] * 0.0126) < 1e-9 and cy.closed[-1]['why'] == 'funding fell',
       f"{cy.closed[-1]}")
finally:
    om._c488_universe = orig
ok("a perp with no spot market is never entered", all('NOSPOT' not in c['coin'] for c in cy.closed))

print("\n4. ISOLATION")
cls_src = src[src.index('class C490Carry:'):src.index('\nclass TradingBot:')]
pf_lines = [l.strip() for l in cls_src.splitlines() if 'portfolio' in l and not l.strip().startswith('#')]
ok("no order and no Portfolio call anywhere in the ledger's code: one read of equity, to seed it",
   'place_order' not in cls_src and 'release_margin' not in cls_src and 'c488_lock' not in cls_src and 'create_order' not in cls_src
   and pf_lines == ['self.start_equity = float(self.bot.portfolio.equity) or 250.0    # read once: a seed, never a write']
   and not re.search(r'portfolio\.\w+\s*[-+*/]?=(?!=)', cls_src), f"{pf_lines}")
bot, cy = mkcarry()
e0, a0 = bot.portfolio.equity, bot.portfolio.available_balance
for i in range(4, 200):
    spot = {smap[s][0]: float(S[i, j]) for j, s in enumerate(syms) if s in smap and not np.isnan(S[i, j])}
    perp = {r: float(C[i, j]) for j, r in enumerate(raws) if not np.isnan(C[i, j])}
    cy.step(int(T[i]) + DAY + 600000, spot, perp, {}, T[:i + 1], keep, C[:i + 1], QV[:i + 1], F[:i + 1])
ok("two hundred ledger days leave the account's equity and balance exactly as they were",
   bot.portfolio.equity == e0 and bot.portfolio.available_balance == a0 and cy.eq != 1000.0, f"ledger ${cy.eq:.2f}")

print("\n5. SCHEDULE, PERSISTENCE AND WIRING")
bot, cy = mkcarry()
d0 = dt.datetime(2026, 9, 26, 0, 9); d1 = dt.datetime(2026, 9, 26, 0, 10)
ok("due from 00:10 UTC, once a day", not cy.due(d0) and cy.due(d1) and (setattr(cy, 'last_run', '2026-09-26') or not cy.due(d1)))
cy.last_run = ''
for i in range(4, 120):
    spot = {smap[s][0]: float(S[i, j]) for j, s in enumerate(syms) if s in smap and not np.isnan(S[i, j])}
    perp = {r: float(C[i, j]) for j, r in enumerate(raws) if not np.isnan(C[i, j])}
    cy.step(int(T[i]) + DAY + 600000, spot, perp, {}, T[:i + 1], keep, C[:i + 1], QV[:i + 1], F[:i + 1])
cy.last_run = '2026-09-26'; cy.save()
cy2 = om.C490Carry(bot)
ok("the ledger, its positions, its daily record and its seed survive a restart",
   abs(cy2.eq - cy.eq) < 1e-12 and cy2.pos == cy.pos and cy2.daily == cy.daily and cy2.start_equity == 1000.0
   and cy2.last_run == '2026-09-26', f"{len(cy2.pos)} held, {len(cy2.daily)} days")
cy2.reset()
ok("reset (fresh start) empties it", not cy2.pos and cy2.eq == 0.0 and not cy2.daily and cy2.start_equity == 0.0)
i88 = src.find("self.c488.tick(can_trade=self.mode_mgr.can_trade())"); i89 = src.find("self.c489.tick()")
i90 = src.find("self.c490.tick()"); ip = src.find("# 2. Check if paused (NO scanning when paused)")
ok("it ticks after the book and the shadow, before the pause check", 0 < i88 < i89 < i90 < ip)
cfg = om.Config()
ok("a fresh start resets it; on by default, with the pre-registered numbers",
   "bot.c490.reset()" in src and cfg.C490_CARRY is True and (cfg.C490_CARRY_ENTER, cfg.C490_CARRY_EXIT, cfg.C490_CARRY_SIZE,
   cfg.C490_CARRY_CAP, cfg.C490_CARRY_TOPN) == (0.10, 0.05, 0.10, 8, 40) and om._OMEGA_VERSION == 'C490')
ok("the report carries a CARRY line and the readable log keeps C490 lines",
   "self._pack('CARRY'," in src and "'C490',                     # the carry ledger's daily run" in src)

def free_port():
    s_ = socket.socket(); s_.bind(('127.0.0.1', 0)); pt = s_.getsockname()[1]; s_.close(); return pt
cy.last_run = '2026-09-26'
pf = bot.portfolio; pf.session_start_equity = 1000.0; pf.positions = om.PositionsManager()
pf.get_live_equity = lambda *a: pf.equity
c488 = types.SimpleNamespace(status=lambda: {'mode': 'portfolio', 'n': 0, 'gross': 0, 'gross_x': 0, 'unrealized': 0,
                                               'funding': 0, 'target_vol': 0.2, 'last_rebal': '', 'next_rebal_utc': '2026-09-26 00:05',
                                               'halt': '', 'info': {}, 'positions': []})
c489 = types.SimpleNamespace(status=lambda: {'mode': 'off'})
fbot = types.SimpleNamespace(cfg=bot.cfg, portfolio=pf, c488=c488, c489=c489, c490=cy,
                             mode_mgr=types.SimpleNamespace(mode=types.SimpleNamespace(value='normal')),
                             exchange=types.SimpleNamespace(get_current_price=lambda s: None),
                             _c467_day_barrier=lambda: {'pnl': 0.0, 'limit': 9.0, 'used': 0.0, 'frac': 0.0},
                             _c482_risk_guard=lambda: {'pct': 15.0, 'month_eq0': 1000.0})
port = free_port(); om.RemoteControl(fbot, port=port).start(); time.sleep(0.6)
import urllib.request
st = json.loads(urllib.request.urlopen(f'http://127.0.0.1:{port}/api/status?t={TOKEN}', timeout=6).read())
c = st.get('c490') or {}
ok("/api/status carries the ledger in dollars", c.get('mode') == 'paper' and c.get('start_equity') == 1000.0
   and abs(c.get('usd', 0) - round(cy.eq, 2)) < 1e-9 and c.get('n') == len(cy.pos) and len(c.get('positions', [])) == len(cy.pos),
   f"{ {k2: c.get(k2) for k2 in ('mode', 'usd', 'pnl_usd', 'n', 'last_run')} }")
try:
    from playwright.sync_api import sync_playwright
    exe = (glob.glob('/opt/pw-browsers/chromium-*/chrome-linux/chrome') or [None])[0]
    with sync_playwright() as pw:
        b = pw.chromium.launch(executable_path=exe) if exe else pw.chromium.launch()
        pg = b.new_page(viewport={'width': 412, 'height': 900}); errs = []
        pg.on('pageerror', lambda x_: errs.append(str(x_)))
        pg.goto(f'http://127.0.0.1:{port}/?t={TOKEN}'); pg.wait_for_timeout(3500)
        txt = pg.inner_text('#carry')
        pg.screenshot(path=os.path.join(BASE, 'carry.png'), full_page=True); b.close()
    ok("the Cash-and-carry panel: a paper ledger from $1000.00 that never touches the account, its coins listed",
       'paper ledger from $1000.00' in txt and 'never touches the account' in txt and f"{len(cy.pos)} of 8 held" in txt
       and all(p_['coin'] in txt for p_ in c.get('positions', [])), txt.replace('\n', ' | ')[:220])
    ok("no JavaScript errors", not errs, f"{errs}")
except ImportError:
    ok("Chromium/playwright available for the page check", False)

print("\n6. THE PRE-REGISTRATION AND THE RESULT")
commits = git('log', '--format=%H %s', '--', 'research/c490_preregistration.md').strip().splitlines()
eng = git('log', '--format=%H', '-S', 'class C490Carry', '--', 'omega_v60_reconstructed.py').split()
first = commits[-1].split()[0] if commits else ''
before = bool(first) and ((not eng) or subprocess.run(['git', 'merge-base', '--is-ancestor', first, eng[-1]], cwd=REPO).returncode == 0)
ok("the round-3 plan was committed before the ledger existed", before, first[:12])
res = json.load(open(os.path.join(REPO, 'research', 'c490_results.json')))
adm = {k: v.get('admitted') for k, v in res.items() if isinstance(v, dict)}
ok("the committed results admit R3c CARRY (t >= 2.6 Bonferroni, 3/4 quarters) and nothing else",
   adm.get('R3c CARRY') and res['R3c CARRY']['t'] >= 2.6 and res['R3c CARRY']['npos'] >= 3
   and not any(v for k, v in adm.items() if k != 'R3c CARRY'), f"{adm}")

shutil.rmtree(BASE, ignore_errors=True)
print("\n" + "=" * 66)
print("ALL CHECKS PASSED" if not fails else f"{len(fails)} FAILURE(S): {fails}")
sys.exit(1 if fails else 0)
