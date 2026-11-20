#!/usr/bin/env python3
"""C548: six paper experiments switched off at the operator's request (paper; nothing traded changes).

The operator, 23 Oct 2026: "please switch off the 6 paper plans you mentioned above" (reports/2026-10-23_recheck.md
section 6). None has a route to the operator's money (each runs on Binance; the plan is India-only):
the intraday shadow (C489), carry (C490), the spot pot (C501), Savings (C501), BFUSD (C521) and the K4 shadow (C501).
1. TradingBot switches them off before it builds the ledgers (`_c548_retire`); C548_RETIRE False brings them back.
2. Their code and saved ledgers stay (old tests still exercise them with Config() defaults).
3. Kept: the plan, its test copies, the book on Delta India, the Binance book and the rule tournament.
4. The page and the totals no longer count the six.
"""
import os, io, sys, json, time, types, logging, tempfile, contextlib, importlib.util
REPO = os.path.dirname(os.path.abspath(__file__))
BASE = tempfile.mkdtemp(prefix='c548_test_')
os.environ['OMEGA_BASE_PATH'] = BASE
os.environ['OMEGA_CTRL_TOKEN'] = 'c548-test-token-0123456789abcdef'
fails = []


def ok(n, c, d=''):
    print(f"  {'PASS' if c else 'FAIL'}  {n}" + (f"   {d}" if d else ''))
    if not c:
        fails.append(n)


spec = importlib.util.spec_from_file_location('om548', os.path.join(REPO, 'omega_v60_reconstructed.py'))
om = importlib.util.module_from_spec(spec)
with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
    spec.loader.exec_module(om)
lg = logging.getLogger('OmegaV60'); lg.handlers = [logging.NullHandler()]; lg.propagate = False
print("=" * 66); print("C548: SIX PAPER EXPERIMENTS SWITCHED OFF"); print("=" * 66)
ok("version C548 or later", int(om._OMEGA_VERSION[1:]) >= 548)
SIX = ('C489_SHADOW', 'C490_CARRY', 'C501_SPOT', 'C501_SAVINGS', 'C521_BFUSD', 'C501_K4')

print("\n1. THE SWITCH")
c0 = om.Config()
ok("Config keeps the six's own defaults (on) and says to retire them", all(getattr(c0, k) is True for k in SIX)
   and c0.C548_RETIRE is True)
off = om._c548_retire(c0)
ok("_c548_retire turns exactly the six off and names them", sorted(off) == sorted(SIX) and all(getattr(c0, k) is False for k in SIX), str(off))
c1 = om.Config(); c1.C548_RETIRE = False
ok("C548_RETIRE = False keeps all six (one setting brings them back)", om._c548_retire(c1) == [] and all(getattr(c1, k) for k in SIX))
SRC = open(os.path.join(REPO, 'omega_v60_reconstructed.py')).read()
i0 = SRC.index("class TradingBot:")
ok("TradingBot retires them before it builds any ledger",
   SRC.index("self._c548_off = _c548_retire(cfg)", i0) < SRC.index("self.c489 = C489Shadow(self)", i0))

print("\n2. WHAT RUNS AND WHAT DOES NOT")
cfg = om.Config(); cfg.PAPER_MODE = True; cfg.VENUE = 'binance'; om._c467_cfg_ref[0] = cfg
for _k, _v in om._C516_VENUE_DEFAULTS['binance'].items():
    setattr(cfg, _k, _v)
# a saved carry ledger, to show the switch keeps history
json.dump(dict(eq=498.10, start_equity=499.83, last_run='2026-10-23', fees=2.66, funding=0.86, trades=29, pos={},
               daily={}, closed=[], info={}), open(os.path.join(BASE, 'c490_carry.json'), 'w'))
om._c548_retire(cfg)
bot = types.SimpleNamespace(cfg=cfg, portfolio=om.Portfolio(cfg), _c462_state_settled=True,
                            _c408_asset_class=lambda s: 'crypto', exchange=types.SimpleNamespace(markets={}),
                            _c482_risk_guard=lambda: {'pct': 20.0})
e = om.C488Engine(bot); bot.c488 = e
made = {}
for a, k in (('c489', 'C489Shadow'), ('c490', 'C490Carry'), ('c501s', 'C501Spot'), ('c501v', 'C501Savings'),
             ('c501k', 'C501Allostatic'), ('c521b', 'C521Bfusd'), ('c521d', 'C521Delta'), ('c510t', 'C510Tournament'),
             ('c524x', 'C524CrossVenue')):
    setattr(bot, a, getattr(om, k)(bot)); made[a] = getattr(bot, a)
bot.c538 = [om.C538TestRule(bot, k) for k in om.C538TestRule.RULES]
gone = ('c489', 'c490', 'c501s', 'c501v', 'c501k', 'c521b')
ok("the six are not active", not any(made[a].active() for a in gone), str({a: made[a].active() for a in gone}))
ok("kept: the plan, the book on Delta India and the rule tournament", made['c524x'].active() and made['c521d'].active()
   and made['c510t'].active())
ok("kept: the plan's three test copies (dx stays retired since C542)",
   {t.key for t in bot.c538 if t.active()} == {'f8', 'w3', 'b15'})
ok("the switch keeps history: the carry ledger still holds its saved $498.10",
   abs(float(made['c490'].eq) - 498.10) < 1e-9 and made['c490'].last_run == '2026-10-23')
before = (made['c490'].eq, made['c490'].last_run)
try:
    made['c490'].tick()
except Exception:
    pass
ok("an off ledger does nothing on its tick", (made['c490'].eq, made['c490'].last_run) == before)

print("\n3. THE TOTALS AND THE PAGE")
T = om._c527_total(bot)
keys = {r['key'] for r in T['rows']}
ok("the totals carry none of the six", not keys & {'savings', 'spot', 'carry'}, str(sorted(keys)))
ok("no spot-pot TDS line, and the 'left out' note names only what runs", T['tds'] == 0.0
   and 'intraday shadow' not in T['left_out'] and 'rule tournament' in T['left_out'], str(T['left_out']))
ok("no BFUSD line", 'bfusd' not in T)
ok("the page says 15 x 12% stays a copy after Round 23",
   "Round 23 (23 Oct) tested six kinds of protection and none paid for itself" in SRC)
ok("the six's code is still there (old tests run it with Config() defaults)",
   all(f"class {k}" in SRC for k in ('C489Shadow', 'C490Carry', 'C501Spot', 'C501Savings', 'C501Allostatic', 'C521Bfusd')))
ok("C488_LIVE_OK stays False; no keys in the code", 'self.C488_LIVE_OK = False' in SRC)
print()
print("=" * 66)
print("C548 TEST: " + ("ALL PASS" if not fails else f"{len(fails)} FAIL"))
for f in fails:
    print("   -", f)
sys.exit(1 if fails else 0)
