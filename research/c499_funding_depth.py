#!/usr/bin/env python3
"""C499 evidence -- python3 research/c499_funding_depth.py BINANCE_ARCHIVE/f

How far is the bot's C488 book from the research spec, and which fix closes it?
Reference R: Bitget funding where Bitget has it (~90 days) + Binance archive funding
for older days. Compared with A: the bot today (last 200 records, zero before);
B: all Bitget serves (~90 days), zero before; C: all Bitget serves, unknown = NaN."""
import io, os, sys, json, types, logging, tempfile, contextlib, importlib.util, datetime as dt
import numpy as np
from concurrent.futures import ThreadPoolExecutor
os.environ['OMEGA_BASE_PATH'] = tempfile.mkdtemp()
spec = importlib.util.spec_from_file_location('om', os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'omega_v60_reconstructed.py')); om = importlib.util.module_from_spec(spec)
with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
    spec.loader.exec_module(om)
logging.getLogger('OmegaV60').handlers = [logging.NullHandler()]
BNC = sys.argv[1] if len(sys.argv) > 1 else 'bnc/f'   # the Binance archive's f/<SYM>.json (research/c488_fetch_binance.py)
cfg = om.Config(); cfg.PAPER_MODE = True; cfg.C380_MAX_MONTHLY_DD_PCT = 15.0
bot = types.SimpleNamespace(cfg=cfg, portfolio=om.Portfolio(cfg), exchange=types.SimpleNamespace(markets={}, exchange=types.SimpleNamespace(markets={})),
                            _c462_state_settled=True, _c408_asset_class=lambda s: 'crypto', _c482_risk_guard=lambda: {'pct': 15.0})
e = om.C488Engine(bot)
names_26sep = "2Z AAVE ADA ARB ARK AVAX BCH BGB BR BTC BTW DOGE DOT ENA ETH FIL HYPE INJ LINK LTC MUBARAK NEAR ONDO PEPE PHA PUMP Q QNT RARE SEI SOL SUI TAO TRUMP UNI WLD XLM XPL XRP ZEC".split()
names = names_26sep
if '--live' in sys.argv:                      # tonight's candidate list instead of the 26 Sep one
    assert e.refresh_marks(force=True)
    import ccxt
    _x = ccxt.bitget({'options': {'defaultType': 'swap'}}); _x.session.trust_env = True
    _mk = _x.load_markets()
    bot.exchange = types.SimpleNamespace(markets=_mk, exchange=types.SimpleNamespace(markets=_mk))
    for _k in ('_C411_INDEX', '_C411_METAL', '_C411_ENERGY', '_C411_US_LISTED', '_C411_KOREA'):
        setattr(bot, _k, getattr(om.TradingBot, _k))
    bot._c408_asset_class = lambda s_: om.TradingBot._c408_asset_class(bot, s_)
    names = [s_.split('/')[0] for s_ in e.candidates(20)]
syms = [f"{n}/USDT:USDT" for n in names]
orig = e._history
def full(sym):
    c, _ = orig(sym)
    raw = e._raw(sym); f = {}
    for pn in range(1, 40):
        d = e._get('history-fund-rate', {'symbol': raw, 'productType': 'USDT-FUTURES', 'pageSize': 100, 'pageNo': pn})
        if not d: break
        for r in d: f[int(r['fundingTime'])] = float(r['fundingRate'])
        if len(d) < 100: break
    b = {}
    p = os.path.join(BNC, e._raw(sym) + '.json')
    if os.path.exists(p):
        b = {int(t): float(r) for t, r in json.load(open(p))}
    return sym, (c, f, b)
with ThreadPoolExecutor(8) as p:
    H = dict(p.map(full, syms))
DAY = 86400000
def book(day_end_ms, now_ms, mode):
    """day_end_ms: completed days before this; now_ms: the fetch moment"""
    nanmask = {}
    def h(sym, days=330):
        c, f, b = H[sym]
        c = {t: v for t, v in c.items() if t < day_end_ms}
        fb = sorted((t, r) for t, r in f.items() if t <= now_ms)
        if mode == 'A': fb = fb[-200:]
        out = dict(fb)
        first = fb[0][0] if fb else now_ms
        if mode == 'R':
            out.update({t: r for t, r in b.items() if t < first})
            first = min([first] + [t for t in b if t < first])
        nanmask[sym] = first
        return c, out
    e._history = h
    T, keep, close, qv, fund = e.matrices(syms)
    if mode in ('A', 'B'):
        fund = np.nan_to_num(fund)          # the pre-C499 matrices(): unknown funding = 0
    if mode == 'C':                         # what C499's matrices() does itself
        for j, s in enumerate(keep):
            fund[T < (nanmask[s] // DAY * DAY), j] = np.nan
    w, sl, _ = om._c488_targets(T, close, qv, fund, 20, e.target_vol(), 3.0)
    return {s.split('/')[0]: float(w[j]) for j, s in enumerate(keep)}
for lab, dend in (('26 Sep rebalance', dt.datetime(2026, 9, 26, tzinfo=dt.timezone.utc)), ('27 Sep rebalance', dt.datetime(2026, 9, 27, tzinfo=dt.timezone.utc))):
    d0 = int(dend.timestamp() * 1000); now = d0 + 5 * 60000
    B = {m: book(d0, now, m) for m in ('R', 'A', 'B', 'C')}
    eq = 250.0
    print(f"\n{lab} (targets in $ at $250 equity; R = Bitget 90d + Binance older funding)")
    keys = sorted(B['R'], key=lambda k: -abs(B['R'][k]))
    print(f"{'coin':7}" + ''.join(f"{m:>9}" for m in ('R', 'A', 'B', 'C')))
    for k in keys:
        if max(abs(B[m][k]) for m in B) * eq >= 4:
            print(f"{k:7}" + ''.join(f"{B[m][k]*eq:+9.2f}" for m in ('R', 'A', 'B', 'C')))
    for m in ('A', 'B', 'C'):
        dif = sum(abs(B[m][k] - B['R'][k]) for k in keys) * eq
        g = lambda x: sum(abs(v) for v in x.values()) * eq
        print(f"  {m}: total |target - R| ${dif:6.2f} | gross ${g(B[m]):6.2f} vs R ${g(B['R']):6.2f}")
