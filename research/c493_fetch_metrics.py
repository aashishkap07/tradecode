#!/usr/bin/env python3
"""C493 data for N4a/N4b: Binance USDT-M futures `metrics` (data.binance.vision,
daily files of 5-minute rows), kept to ONE row per UTC day -- the last one, the
state at the daily close. Only the days a coin was in the point-in-time top 40
(and the 35 days before, for the 30-day z-score) are fetched.

    python3 research/c493_fetch_metrics.py BNC_DIR OUTDIR

Writes OUTDIR/<SYM>.json {"<day_ms>": [count_long_short_ratio, sum_toptrader_long_short_ratio]}.
Re-runnable: days already in a file are skipped."""
import os, sys, io, csv, json, time, zipfile, urllib.request, datetime as dt
from concurrent.futures import ThreadPoolExecutor
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import omega_c488_research as R
from omega_c493_research import TRADFI

BNC, OUT = sys.argv[1], sys.argv[2]
os.makedirs(OUT, exist_ok=True)
DL = "https://data.binance.vision/data/futures/um/daily/metrics/{s}/{s}-metrics-{d}.zip"
START = int(dt.datetime(2020, 9, 1, tzinfo=dt.timezone.utc).timestamp() * 1000)

R.EXCLUDE = set(R.EXCLUDE) | TRADFI
T, syms, close, qv, fund = R.load_crypto(BNC)
elig = R.universe(close, qv)
need = {}
for j, s in enumerate(syms):
    rows = np.nonzero(elig[:, j])[0]
    if not len(rows):
        continue
    days = set()
    for i in rows:
        for q in range(max(0, i - 35), i + 1):
            if T[q] >= START:
                days.add(int(T[q]))
    need[s] = sorted(days)
print(f"{len(need)} coins, {sum(len(v) for v in need.values())} coin-days", flush=True)


def get(u, tries=4):
    for k in range(tries):
        try:
            return urllib.request.urlopen(u, timeout=40).read()
        except Exception as e:
            if '404' in str(e):
                return None
            time.sleep(1 + 2 * k)
    return None


def last_row(b):
    z = zipfile.ZipFile(io.BytesIO(b))
    rows = [r for r in csv.reader(io.StringIO(z.read(z.namelist()[0]).decode())) if r and r[0][:1].isdigit()]
    for r in reversed(rows):
        try:
            a = float(r[6]) if r[6] else None
            b_ = float(r[5]) if r[5] else None
            if a or b_:
                return [a, b_]
        except (ValueError, IndexError):
            continue
    return None


def do(s):
    p = os.path.join(OUT, s + '.json')
    have = json.load(open(p)) if os.path.exists(p) else {}
    todo = [t for t in need[s] if str(t) not in have]
    for t in todo:
        d = dt.datetime.utcfromtimestamp(t / 1000).strftime('%Y-%m-%d')
        b = get(DL.format(s=s, d=d))
        v = last_row(b) if b else None
        have[str(t)] = v
    json.dump(have, open(p, 'w'))
    return s, len(todo), sum(1 for v in have.values() if v)


n = 0
with ThreadPoolExecutor(32) as ex:
    for s, k, got in ex.map(do, sorted(need, key=lambda x: -len(need[x]))):
        n += 1
        if n % 20 == 0:
            print(n, s, k, got, flush=True)
print('DONE', n)
