#!/usr/bin/env python3
"""C488 data: BTCUSDT 1-hour perpetual klines from the Binance archive (the C4 evening test). Run from
the output folder: it writes bnc/BTCUSDT_1h.json."""
import urllib.request, re, io, zipfile, csv, json
from concurrent.futures import ThreadPoolExecutor
S3 = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision?delimiter=/&prefix=data/futures/um/monthly/klines/BTCUSDT/1h/"
x = urllib.request.urlopen(S3, timeout=40).read().decode()
keys = [k for k in re.findall(r'<Key>([^<]+)</Key>', x) if k.endswith('.zip')]
def one(k):
    b = urllib.request.urlopen("https://data.binance.vision/" + k, timeout=60).read()
    z = zipfile.ZipFile(io.BytesIO(b)); t = z.read(z.namelist()[0]).decode()
    return [[int(r[0]), float(r[1]), float(r[2]), float(r[3]), float(r[4]), float(r[7])] for r in csv.reader(io.StringIO(t)) if r and r[0][:1].isdigit()]
rows = {}
with ThreadPoolExecutor(8) as ex:
    for rs in ex.map(one, keys):
        for r in rs: rows[r[0]] = r
json.dump([rows[t] for t in sorted(rows)], open('bnc/BTCUSDT_1h.json', 'w')); print('BTC 1h', len(rows), len(keys), 'months')
