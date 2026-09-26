#!/usr/bin/env python3
"""C489 data: Binance USDT-M archive 1-hour klines with taker-buy volume.
Usage: python3 research/c489_fetch_h1.py SYMBOLS.json OUTDIR  (SEED=<n> to run several side by side)"""
import urllib.request, urllib.parse, re, os, io, json, zipfile, csv, sys, time, random
from concurrent.futures import ThreadPoolExecutor
S3 = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision?delimiter=/&prefix="
DL = "https://data.binance.vision/"
OUT = sys.argv[2]; syms = json.load(open(sys.argv[1]))
if os.environ.get('SEED'): random.Random(int(os.environ['SEED'])).shuffle(syms)
os.makedirs(OUT, exist_ok=True)
def get(u, tries=5):
    for k in range(tries):
        try: return urllib.request.urlopen(u, timeout=60).read()
        except Exception as e:
            if '404' in str(e): return None
            time.sleep(2 + 3 * k)
    return None
def keys(prefix):
    out, marker = [], ''
    while True:
        raw = get(S3 + prefix + (f"&marker={urllib.parse.quote(marker)}" if marker else ''))
        if raw is None: raise IOError('list ' + prefix)
        x = raw.decode(); ks = re.findall(r'<Key>([^<]+)</Key>', x); out += ks
        if '<IsTruncated>true' not in x: break
        marker = ks[-1]
    return [k for k in out if k.endswith('.zip')]
def one(s):
    p = f"{OUT}/{s}.json"
    if os.path.exists(p): return s
    try:
        rows = {}
        for k in keys(f'data/futures/um/monthly/klines/{s}/1h/'):
            if int(k[-11:-7]) < 2021: continue
            b = get(DL + k)
            if not b: continue
            z = zipfile.ZipFile(io.BytesIO(b)); t = z.read(z.namelist()[0]).decode()
            for r in csv.reader(io.StringIO(t)):
                if r and r[0][:1].isdigit():
                    # t, o, h, l, c, quote_vol, taker_buy_quote_vol
                    rows[int(r[0])] = [int(r[0]), float(r[1]), float(r[2]), float(r[3]), float(r[4]), float(r[7]), float(r[10])]
        json.dump([rows[t] for t in sorted(rows)], open(p + '.tmp', 'w')); os.replace(p + '.tmp', p)
    except Exception as e:
        print('SKIP', s, e, flush=True)
    return s
n = 0
with ThreadPoolExecutor(16) as ex:
    for s in ex.map(one, syms):
        n += 1
        if n % 25 == 0: print(n, s, flush=True)
print('DONE', n)
