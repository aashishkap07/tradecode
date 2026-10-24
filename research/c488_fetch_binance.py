#!/usr/bin/env python3
"""C488 data: the Binance USDT-M perpetual archive (data.binance.vision), daily klines and
funding for EVERY symbol, delisted ones included. Usage: python3 research/c488_fetch_binance.py OUTDIR
Writes OUTDIR/k/<SYM>.json and OUTDIR/f/<SYM>.json; skips files that exist, so it can be re-run.
Optional: SEED=<n> shuffles the order so several copies can run side by side."""
import urllib.request, re, os, io, json, zipfile, csv, sys, time
from concurrent.futures import ThreadPoolExecutor
S3 = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision?delimiter=/&prefix="
DL = "https://data.binance.vision/"
OUT = sys.argv[1]
def get(u, tries=4):
    for k in range(tries):
        try:
            return urllib.request.urlopen(u, timeout=40).read()
        except Exception as e:
            if '404' in str(e): return None
            time.sleep(1 + 2 * k)
    return None
def ls_all(prefix, want='Prefix'):
    out, marker = [], ''
    while True:
        raw = None
        for _k in range(6):
            raw = get(S3 + prefix + (f"&marker={marker}" if marker else ''))
            if raw is not None: break
            time.sleep(3 + 3 * _k)
        if raw is None: raise IOError('listing failed ' + prefix)
        x = raw.decode()
        if want == 'Prefix':
            items = re.findall(r'<Prefix>([^<]+)</Prefix>', x)[1:] if not marker else re.findall(r'<Prefix>([^<]+)</Prefix>', x)
            items = [i for i in items if i != prefix]
        else:
            items = re.findall(r'<Key>([^<]+)</Key>', x)
        out += items
        if '<IsTruncated>true' not in x: break
        marker = (re.findall(r'<NextMarker>([^<]+)</NextMarker>', x) or [items[-1]])[0]
    return out
syms = sorted({p.rstrip('/').split('/')[-1] for p in ls_all('data/futures/um/monthly/klines/')})
syms = [s for s in syms if s.endswith('USDT') and '_' not in s]
if os.environ.get("REV"): syms = syms[::-1]
import random
if os.environ.get("SEED"): random.Random(int(os.environ["SEED"])).shuffle(syms)
print('symbols', len(syms), flush=True)
def rows_from_zip(b):
    z = zipfile.ZipFile(io.BytesIO(b)); txt = z.read(z.namelist()[0]).decode()
    return [r for r in csv.reader(io.StringIO(txt)) if r and r[0][:1].isdigit()]
def do_sym(s):
    pk, pf = f"{OUT}/k/{s}.json", f"{OUT}/f/{s}.json"
    if not os.path.exists(pk):
        keys = [k for k in ls_all(f'data/futures/um/monthly/klines/{s}/1d/', 'Key') if k.endswith('.zip')]
        rows = {}
        for k in keys:
            b = get(DL + k)
            if b:
                for r in rows_from_zip(b):
                    rows[int(r[0])] = [int(r[0]), float(r[1]), float(r[2]), float(r[3]), float(r[4]), float(r[5]), float(r[7])]
        json.dump([rows[t] for t in sorted(rows)], open(pk, 'w'))
    if not os.path.exists(pf):
        keys = [k for k in ls_all(f'data/futures/um/monthly/fundingRate/{s}/', 'Key') if k.endswith('.zip')]
        rows = {}
        for k in keys:
            b = get(DL + k)
            if b:
                for r in rows_from_zip(b):
                    rows[int(r[0])] = [int(r[0]), float(r[-1])]
        json.dump([rows[t] for t in sorted(rows)], open(pf, 'w'))
    return s
n = 0
with ThreadPoolExecutor(24) as ex:
    def safe(s):
        try: return do_sym(s)
        except Exception as e: print('SKIP', s, e, flush=True); return s
    for s in ex.map(safe, syms):
        n += 1
        if n % 50 == 0: print(n, s, flush=True)
print('DONE', n)
