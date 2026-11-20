#!/usr/bin/env python3
"""C491: Binance USDT-M 1-minute klines for the round-4 universe (research/c491_preregistration.md).

    python3 research/c491_fetch_1m.py NEED_JSON OUT_DIR

NEED_JSON: {symbol: [YYYY-MM, ...]}. Writes OUT_DIR/SYMBOL.npz with t (ms, int64)
and o, h, l, c (float64), one row per minute, sorted. A month the archive does
not have is recorded in OUT_DIR/missing.json."""
import os, sys, io, csv, json, time, zipfile, urllib.request
import numpy as np
from concurrent.futures import ThreadPoolExecutor
DL = "https://data.binance.vision/data/futures/um/monthly/klines/{s}/1m/{s}-1m-{m}.zip"


def get(u, tries=5):
    for k in range(tries):
        try:
            return urllib.request.urlopen(u, timeout=90).read()
        except Exception as e:
            if '404' in str(e):
                return None
            time.sleep(2 + 2 * k)
    return None


def month(sym, m):
    b = get(DL.format(s=sym, m=m))
    if not b:
        return sym, m, None
    z = zipfile.ZipFile(io.BytesIO(b))
    txt = z.read(z.namelist()[0]).decode()
    rows = [r for r in csv.reader(io.StringIO(txt)) if r and r[0][:1].isdigit()]
    a = np.array([[float(x) for x in r[:5]] for r in rows])
    return sym, m, a


def main(need_path, out):
    need = json.load(open(need_path))
    os.makedirs(out, exist_ok=True)
    jobs = [(s, m) for s, ms in need.items() if not os.path.exists(os.path.join(out, s + '.npz')) for m in ms]
    got, missing = {}, []
    with ThreadPoolExecutor(12) as ex:
        for i, (s, m, a) in enumerate(ex.map(lambda j: month(*j), jobs)):
            if a is None:
                missing.append([s, m])
            else:
                got.setdefault(s, []).append(a)
            if (i + 1) % 50 == 0:
                print(f"{i + 1}/{len(jobs)}", flush=True)
            if s in got and sum(1 for j in jobs if j[0] == s) == len(got[s]) + sum(1 for x in missing if x[0] == s):
                pass
    for s, parts in got.items():
        a = np.vstack(parts)
        t = a[:, 0].astype(np.int64)
        t = np.where(t > 10 ** 14, t // 1000, t)                 # guard: microsecond stamps
        o = np.argsort(t)
        t, a = t[o], a[o]
        keep = np.concatenate([[True], np.diff(t) > 0])
        np.savez(os.path.join(out, s + '.npz'), t=t[keep], o=a[keep, 1], h=a[keep, 2], l=a[keep, 3], c=a[keep, 4])
    json.dump(missing, open(os.path.join(out, 'missing.json'), 'w'))
    print('DONE', len(got), 'coins;', len(missing), 'coin-months missing', flush=True)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
