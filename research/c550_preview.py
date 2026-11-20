#!/usr/bin/env python3
"""C550 preview: the dry order path's first day on the server's own ledger and LIVE public data (Delta's tickers and
settings, Binance's marks, CoinDCX's rupee rate, instrument data and close-only flags). Orders go ONLY to the bot's
in-memory exchange; the real order function is replaced by one that raises. The read-only keys are taken as fine (on
the server C540 reads them every 10 minutes).

    python3 research/c550_preview.py LEDGER_DIR OUT_DIR
"""
import os, io, sys, json, time, types, logging, tempfile, contextlib, importlib.util
import requests
LEDGER, OUT = sys.argv[1], sys.argv[2]
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.environ['OMEGA_BASE_PATH'] = tempfile.mkdtemp(prefix='c550_preview_')
spec = importlib.util.spec_from_file_location('om550p', os.path.join(REPO, 'omega_v60_reconstructed.py'))
om = importlib.util.module_from_spec(spec)
with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
    spec.loader.exec_module(om)
LINES = []
class _H(logging.Handler):
    def emit(self, r): LINES.append(r.getMessage())
lg = logging.getLogger('OmegaV60'); lg.handlers = [_H()]; lg.propagate = False; lg.setLevel(logging.INFO)
def _never(*a, **k):
    raise AssertionError('an order reached the real network')
om._C550_HTTP = _never
L = json.load(open(os.path.join(LEDGER, 'c524_xvenue.json')))
prods = {p['underlying_asset']['symbol']: dict(sym=p['symbol']) for p in requests.get(
    'https://api.india.delta.exchange/v2/products', params=dict(contract_types='perpetual_futures', states='live'), timeout=30).json()['result']}
tk = {t['symbol']: dict(mark=float(t.get('mark_price') or 0)) for t in requests.get(
    'https://api.india.delta.exchange/v2/tickers', params=dict(contract_types='perpetual_futures'), timeout=30).json()['result']}
bn = {x['symbol']: float(x['markPrice']) for x in requests.get('https://www.binance.com/fapi/v1/premiumIndex', timeout=30).json()}
half = L['start_equity'] / 2.0
xv = types.SimpleNamespace(pairs=L['pairs'], last_run=L['last_run'], closed=L['closed'], prods=prods,
                           margins=lambda: {v: dict(eq=half + L['side'][v], start=half) for v in ('d', 'b')})
cfg = om.Config(); cfg.PAPER_MODE = True
now = time.time()
snap = {'delta_india': dict(ok=True, at=now, wallets=[], positions=[], equity=0.0),
        'coindcx': dict(ok=True, at=now, wallets=[dict(asset='INR', balance=0.07)], positions=[])}
bot = types.SimpleNamespace(cfg=cfg, c524x=xv, _c462_state_settled=True, c521d=types.SimpleNamespace(marks=tk),
                            c488=types.SimpleNamespace(mark=lambda s: bn.get(str(s).split('/')[0] + 'USDT', 0.0)),
                            c540=types.SimpleNamespace(snap=snap))
p = om.C550OrderPath(bot)
p.tick(now=now)
os.makedirs(OUT, exist_ok=True)
open(os.path.join(OUT, 'c550_preview.txt'), 'w').write('\n'.join(LINES) + '\n')
d_orders = [b for m, pth, b in p.sims['delta'].log if pth == '/v2/orders']
b_orders = [b for m, pth, b in p.sims['coindcx'].log if pth.endswith('/orders/create')]
print('\n'.join(LINES))
print(f"\n{len(p.legs)} pairs held in the dry book (plan: {len(L['pairs'])}); Delta orders {len(d_orders)} "
      f"(stops {sum(1 for b in d_orders if b.get('stop_order_type'))}); CoinDCX entries {len(b_orders)}, "
      f"stop-losses {sum(1 for m, pth, b in p.sims['coindcx'].log if pth.endswith('create_tpsl'))}")
for c, leg in sorted(p.legs.items()):
    pp = L['pairs'][c]
    print(f"  {c:8} side {leg['side']:+d}  Delta {leg['d']['k']:+d} contracts (plan {int(pp['d_qty']):+d})  CoinDCX {leg['b']['qty']:+g}"
          f"  stop {leg['stop'].get('v')} {leg['stop'].get('px', 0):.6g}")
