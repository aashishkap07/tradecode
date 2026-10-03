#!/usr/bin/env python3
"""C496 W1 data: Bitget hourly candles for every RWA perp (isRwa = YES), as far
back as history-candles serves them.

    python3 research/c496_fetch_rwa1h.py OUTDIR

Writes OUTDIR/<SYMBOL>.json {"<hour_ms>": [close, quote_volume]} and
OUTDIR/contracts.json (the live contract rows, for the record)."""
import os, sys, json, time, threading
import requests
from concurrent.futures import ThreadPoolExecutor

OUT = sys.argv[1]
os.makedirs(OUT, exist_ok=True)
API = 'https://api.bitget.com/api/v2/mix/market/'
_tls = threading.local()


def get(path, params, tries=5):
    if not hasattr(_tls, 's'):
        _tls.s = requests.Session()
    for k in range(tries):
        try:
            d = _tls.s.get(API + path, params=params, timeout=20).json()
            if d.get('data') is not None:
                return d['data']
            if str(d.get('code')) == '429':
                time.sleep(2 + 2 * k)
        except Exception:
            time.sleep(1 + k)
    return None


C = get('contracts', {'productType': 'USDT-FUTURES'})
rwa = [x for x in C if x.get('isRwa') == 'YES']
json.dump(rwa, open(os.path.join(OUT, 'contracts.json'), 'w'))
print(len(rwa), 'RWA perps', flush=True)


def pull(sym):
    p = os.path.join(OUT, sym + '.json')
    if os.path.exists(p):
        return sym, -1
    out, end = {}, int(time.time() * 1000)
    for _ in range(80):
        d = get('history-candles', {'symbol': sym, 'productType': 'USDT-FUTURES', 'granularity': '1H',
                                    'endTime': end, 'limit': 200})
        if not d:
            break
        for x in d:
            out[str(int(x[0]))] = [float(x[4]), float(x[6])]
        first = min(int(x[0]) for x in d)
        if first >= end or len(d) < 2:
            break
        end = first - 1
        time.sleep(0.05)
    json.dump(out, open(p, 'w'))
    return sym, len(out)


n = 0
with ThreadPoolExecutor(10) as ex:
    for s, k in ex.map(pull, [x['symbol'] for x in rwa]):
        n += 1
        if n % 25 == 0:
            print(n, s, k, flush=True)
print('DONE', n)
