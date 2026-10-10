#!/usr/bin/env python3
"""C507: the book's rule simulated day by day on Bitget's own data, July -> 28 Sep
2026, with the bot's own functions -- to compare with the live paper book over
the same days (it began 25 Sep 2026 12:16:57 UTC).

    python3 research/c507_sim_recent.py [--save M.npz]

Result on 29 Sep 2026: Jul +0.71%, Aug +9.63%, 1-24 Sep +3.71%, 25-28 Sep
-2.92%; the worst coins over 25-28 Sep were PUMP, WLD and LINK (C2 shorts).
Candles are fetched live, so a later run sees the same history plus newer days.
"""
import io, os, sys, types, logging, tempfile, contextlib, importlib.util, datetime as dt
import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.environ['OMEGA_BASE_PATH'] = tempfile.mkdtemp()
spec = importlib.util.spec_from_file_location('om', os.path.join(REPO, 'omega_v60_reconstructed.py'))
om = importlib.util.module_from_spec(spec)
with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
    spec.loader.exec_module(om)
logging.getLogger('OmegaV60').handlers = [logging.NullHandler()]
import ccxt

x = ccxt.bitget({'options': {'defaultType': 'swap'}}); x.session.trust_env = True
mk = x.load_markets()
cfg = om.Config(); cfg.PAPER_MODE = True; cfg.C380_MAX_MONTHLY_DD_PCT = 15.0
pf = om.Portfolio(cfg); pf.equity = 250.0
ex = types.SimpleNamespace(markets=mk, exchange=types.SimpleNamespace(markets=mk))
bot = types.SimpleNamespace(cfg=cfg, portfolio=pf, exchange=ex, _c462_state_settled=True,
                            _c482_risk_guard=lambda: {'pct': 15.0})
for k in ('_C411_INDEX', '_C411_METAL', '_C411_ENERGY', '_C411_US_LISTED', '_C411_KOREA'):
    setattr(bot, k, getattr(om.TradingBot, k))
bot._c408_asset_class = lambda s: om.TradingBot._c408_asset_class(bot, s)
e = om.C488Engine(bot); bot.c488 = e
e.refresh_marks(force=True)
# the bot's own candidate list, from its 29 Sep log line "C488 CANDIDATES (80 with history)"
logged = ("1000BONK AAVE ADA AERO AKE ALGO APT ARB ASTER ATOM AVAX BCH BGB BNB BTC BTW CRV DOGE DOT ENA ETC ETH "
          "FARTCOIN FET FIL GRAM GRASS GRT HBAR HYPE ICP INJ IOTA JASMY JUP KAS LDO LINK LSK LTC MARSCOIN MON "
          "MUBARAK NEAR NIL NMR ONDO ONE OP PENGU PEPE PHA POL PONS PUMP PYTH Q QNT RAY RENDER SEI SHIB SOL SOON "
          "SUI TAO TIA TRUMP UNI US USELESS VIRTUAL WLD XLM XPL XRP ZEC ZRO 牛来 龙虾").split()
full = {s.split('/')[0]: s for s in mk if s.endswith('/USDT:USDT')}
T, keep, close, qv, fund = e.matrices([full[c] for c in logged if c in full])
if '--save' in sys.argv:
    np.savez_compressed(sys.argv[sys.argv.index('--save') + 1], T=T, keep=np.array(keep), close=close, qv=qv, fund=fund)
r, Wsl, elig = om._c488_sleeves(T, close, qv, fund, 20)
parts = {k: Wsl[k] for k in ('C1', 'C2', 'C3')}
W = om._c488_combine(parts, r, fund, 1, target_vol=0.20, lev_cap=3.0)
W = np.where(np.abs(W) * 250.0 >= 6.0, W, 0.0)                  # the $6 floor at $250
x, info = om._c488_pnl(W, r, fund, 1)
dates = [dt.datetime.utcfromtimestamp(t / 1000).date() for t in T]


def seg(a, b):
    ii = [i for i, d in enumerate(dates) if a <= d <= b]
    return float(np.prod(1 + x[ii]) - 1), ii


for lab, a, b in (('Jul 2026', dt.date(2026, 7, 1), dt.date(2026, 7, 31)),
                  ('Aug 2026', dt.date(2026, 8, 1), dt.date(2026, 8, 31)),
                  ('1-24 Sep', dt.date(2026, 9, 1), dt.date(2026, 9, 24)),
                  ('25-28 Sep (live days)', dt.date(2026, 9, 25), dt.date(2026, 9, 28))):
    v, ii = seg(a, b)
    print(f"  simulated book {lab:22}: {100 * v:+.2f}%  ({len(ii)} days)")
print("  daily, 22-28 Sep:", ' '.join(f"{d:%d}:{100 * v:+.2f}%" for d, v in zip(dates, x) if d >= dt.date(2026, 9, 22)))
# which coins drove 25-28 Sep (price P&L of yesterday's weights, % of equity)
Wl = np.zeros_like(W); Wl[1:] = W[:-1]
contrib = Wl * np.nan_to_num(r)
ii = [i for i, d in enumerate(dates) if dt.date(2026, 9, 25) <= d <= dt.date(2026, 9, 28)]
cc = contrib[ii].sum(0)
print("  worst coins 25-28 Sep (price P&L, % of equity):",
      [(keep[j].split('/')[0], round(100 * cc[j], 2)) for j in np.argsort(cc)[:6]])
print("  best coins:", [(keep[j].split('/')[0], round(100 * cc[j], 2)) for j in np.argsort(-cc)[:4]])
