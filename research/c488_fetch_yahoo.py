#!/usr/bin/env python3
"""C488 data: 20+ years of daily Yahoo Finance history for the RWA proxies (gold, silver,
copper, platinum, palladium, WTI, Brent, S&P 500 and Nasdaq-100 futures) and more. Run from
the output folder: it writes yahoo/<name>.json."""
import json, os, sys, time, urllib.request, urllib.parse
SYMS = {
 # metals / energy (Bitget: XAU XAG COPPER XPT XPD CL BZ)
 'GC=F': 'gold', 'SI=F': 'silver', 'HG=F': 'copper', 'PL=F': 'platinum', 'PA=F': 'palladium',
 'CL=F': 'wti', 'BZ=F': 'brent', 'NG=F': 'natgas',
 # index futures (Bitget: SP500 NDX100)
 'ES=F': 'sp500', 'NQ=F': 'ndx100', 'YM=F': 'dow', 'RTY=F': 'russell',
 # korea (Bitget: KORU/EWY/SKHY US-listed; SAMSUNG/SKHYNIX KRX)
 'EWY': 'ewy', '005930.KS': 'samsung', '000660.KS': 'skhynix',
 # large US equities Bitget lists as perps
 'AAPL': 'aapl', 'MSFT': 'msft', 'NVDA': 'nvda', 'AMZN': 'amzn', 'META': 'meta', 'GOOGL': 'googl',
 'TSLA': 'tsla', 'COIN': 'coin', 'MSTR': 'mstr', 'AMD': 'amd', 'NFLX': 'nflx', 'PLTR': 'pltr',
 # long crypto history (spot) to extend the perp sample back before 2021
 'BTC-USD': 'btc', 'ETH-USD': 'eth', 'SOL-USD': 'sol', 'XRP-USD': 'xrp', 'DOGE-USD': 'doge', 'ADA-USD': 'ada',
 'BNB-USD': 'bnb', 'LINK-USD': 'link', 'LTC-USD': 'ltc', 'BCH-USD': 'bch', 'TRX-USD': 'trx', 'XLM-USD': 'xlm',
 'DOT-USD': 'dot', 'AVAX-USD': 'avax', 'ATOM-USD': 'atom', 'ETC-USD': 'etc', 'FIL-USD': 'fil', 'UNI7083-USD': 'uni',
 'NEAR-USD': 'near', 'AAVE-USD': 'aave', 'HBAR-USD': 'hbar', 'ICP-USD': 'icp', 'ALGO-USD': 'algo', 'XMR-USD': 'xmr',
 'EOS-USD': 'eos', 'XTZ-USD': 'xtz', 'VET-USD': 'vet', 'MATIC-USD': 'matic', 'THETA-USD': 'theta', 'DASH-USD': 'dash',
}
for y, name in SYMS.items():
    p = f'yahoo/{name}.json'
    if os.path.exists(p): continue
    q = urllib.parse.urlencode(dict(period1=946684800, period2=int(time.time()), interval='1d'))
    u = f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(y)}?{q}"
    for k in range(4):
        try:
            req = urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0'})
            d = json.loads(urllib.request.urlopen(req, timeout=30).read())['chart']['result'][0]
            ts = d['timestamp']; qd = d['indicators']['quote'][0]
            adj = (d['indicators'].get('adjclose') or [{}])[0].get('adjclose')
            rows = []
            for i, t in enumerate(ts):
                c = qd['close'][i]
                if c is None: continue
                rows.append([t * 1000, qd['open'][i], qd['high'][i], qd['low'][i], c, qd['volume'][i], adj[i] if adj else c])
            json.dump(rows, open(p, 'w')); print(name, len(rows), time.strftime('%Y-%m-%d', time.gmtime(rows[0][0] / 1000)), flush=True)
            break
        except Exception as e:
            print('retry', name, e); time.sleep(2 + k)
    time.sleep(0.4)
print('DONE')
