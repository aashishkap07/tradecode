#!/usr/bin/env python3
"""C532: is Pi42's funding still Binance's? (The cross-venue ledger reads Pi42's funding and prices from
Binance, Pi42's own price source.) Run it any time -- weekly is enough:

    pip install "python-socketio[client]" websocket-client     # once
    python3 research/c532_pi42_check.py [OUT.json]
    (OMEGA_BN_FAPI=https://www.binance.com where fapi.binance.com is blocked, as in the bot)

It reads every Pi42 rupee perp's current and next funding from Pi42's public websocket (markPriceArr, no
key) and Binance's from its public premiumIndex, and prints how many settle at the same moment and how close
the next rates are. On 4 Oct 2026: 246 compared, 216 at the same moment, 87% within 0.002% a settlement,
median gap 0.0005% (research/c532_pi42/). If that falls well below ~80%, the proxy needs a rethink.
"""
import os, sys, json, time
import requests
import numpy as np
import socketio

got = {}
sio = socketio.Client()


@sio.event
def connect():
    sio.emit('subscribe', {'params': ['markPriceArr']})


@sio.on('markPriceArr')
def arr(d):
    for x in (d if isinstance(d, list) else d.get('data') or []):
        s = (x.get('s') or '').upper()
        if s:
            got[s] = x


sio.connect('https://fawss.pi42.com/', transports=['websocket'], wait_timeout=15)
t0 = time.time()
while time.time() - t0 < 20:
    time.sleep(1)
sio.disconnect()
bn = {x['symbol']: x for x in requests.get(os.environ.get('OMEGA_BN_FAPI', 'https://fapi.binance.com') + '/fapi/v1/premiumIndex', timeout=30).json()}
rows = []
for s, d in got.items():
    if not s.endswith('INR'):
        continue
    b = bn.get(s[:-3] + 'USDT')
    if b:
        rows.append((s[:-3], float(d['r']), float(b['lastFundingRate']), int(d['T']) == int(b['nextFundingTime'])))
a = np.array([[r[1], r[2]] for r in rows])
print(f"{time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())}: {len(rows)} Pi42 rupee perps with a Binance twin; "
      f"{sum(r[3] for r in rows)} settle at the same moment; next rates within 0.002%/settlement: "
      f"{100 * (abs(a[:, 0] - a[:, 1]) < 2e-5).mean():.0f}%; median gap {100 * np.median(abs(a[:, 0] - a[:, 1])):.4f}%")
if len(sys.argv) > 1:
    json.dump(rows, open(sys.argv[1], 'w'))
