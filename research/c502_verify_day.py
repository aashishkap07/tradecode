#!/usr/bin/env python3
# C502: independent check of a spot-pot day (first used on 28 Sep 07:39 UTC):
# fresh Bitget history -> S1 built with the bot's _c501_s1_targets AND line by
# line with the RESEARCH library -> the two must agree -> $ targets at $250,
# marked against the $6 (C501) and $2 (C502) floors.
#     python3 research/c502_verify_day.py
import io, os, sys, types, logging, tempfile, contextlib, importlib.util, datetime as dt, time, math, json, urllib.request
import numpy as np
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'research'))
os.environ['OMEGA_BASE_PATH'] = tempfile.mkdtemp()
spec = importlib.util.spec_from_file_location('om', os.path.join(REPO, 'omega_v60_reconstructed.py')); om = importlib.util.module_from_spec(spec)
with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
    spec.loader.exec_module(om)
logging.getLogger('OmegaV60').handlers = [logging.NullHandler()]
import omega_c488_research as R
import ccxt
x = ccxt.bitget({'options': {'defaultType': 'swap'}}); x.session.trust_env = True
mk = x.load_markets()
cfg = om.Config(); cfg.PAPER_MODE = True; cfg.C380_MAX_MONTHLY_DD_PCT = 15.0
pf = om.Portfolio(cfg); pf.equity = 250.39
ex = types.SimpleNamespace(markets=mk, exchange=types.SimpleNamespace(markets=mk))
bot = types.SimpleNamespace(cfg=cfg, portfolio=pf, exchange=ex, _c462_state_settled=True, _c482_risk_guard=lambda: {'pct': 15.0})
for k in ('_C411_INDEX','_C411_METAL','_C411_ENERGY','_C411_US_LISTED','_C411_KOREA'):
    setattr(bot, k, getattr(om.TradingBot, k))
bot._c408_asset_class = lambda s: om.TradingBot._c408_asset_class(bot, s)
e = om.C488Engine(bot); bot.c488 = e; pf._c488 = e
assert e.refresh_marks(force=True)
T, keep, close, qv, fund = e.matrices(e.candidates(20))
print(f"history: {len(keep)} coins, last complete day {dt.datetime.utcfromtimestamp(T[-1]/1000).date()}")
# the bot's function
wb, _ = om._c501_s1_targets(T, close, qv, 20, target_vol=0.20, cost=0.0010)
# the research library, built line by line as research/omega_c501_research.py does
R.TOPN = 20
r = R.returns(close); sd = R.trailing_std(r, 30); elig = R.universe(close, qv); sc = np.nan_to_num(R.vol_scale(sd))
s = sum(np.sign(np.nan_to_num(R.lagret(close, d))) for d in (7, 14, 28, 56)) / 4.0
W1 = R.banded(np.where(elig, np.maximum(s, 0.0) * sc / 20, 0.0))
u = R.pnl(W1, r, np.zeros_like(fund), 1, cost=0.0010)[0]
n = len(T); L = np.zeros(n)
for i in range(60, n):
    v = u[i-60:i].std() * math.sqrt(365); L[i] = 0.20 / v if v > 0 else 0.0
W = W1 * L[:, None]; g = np.abs(W).sum(1); W = W * np.where(g > 1.0, 1.0 / np.maximum(g, 1e-12), 1.0)[:, None]
wr = W[-1]
print(f"max |bot - research| weight difference: {np.nanmax(np.abs(np.nan_to_num(wb) - np.nan_to_num(wr))):.2e}")
print(f"pot scale L = {L[-1]:.3f} (60-day vol of the unit book {100*0.20/L[-1]:.1f}%/yr); gross {100*np.abs(wr).sum():.1f}%")
elig_now = [keep[j].split('/')[0] for j in range(len(keep)) if elig[-1, j]]
print(f"top 20 today: {' '.join(elig_now)}")
up = [(keep[j].split('/')[0], s[-1, j]) for j in range(len(keep)) if elig[-1, j] and s[-1, j] > 0]
print(f"trend score > 0: {', '.join(f'{c} {v:+.2f}' for c, v in up)}")
for j in np.argsort(-wr):
    if wr[j] * 250 >= 1:
        print(f"   {keep[j].split('/')[0]:6} weight {100*wr[j]:.2f}%  -> ${wr[j]*250:.2f}"
              f"{'  (under $2: not opened)' if wr[j]*250 < 2 else '  (under $6: C501 dropped it)' if wr[j]*250 < 6 else ''}  "
              f"trend {s[-1,j]:+.2f}  30d sd {100*sd[-1,j]:.2f}%/day")
