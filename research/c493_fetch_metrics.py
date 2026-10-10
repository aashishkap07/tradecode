#!/usr/bin/env python3
"""C493 data for N4a/N4b: Binance USDT-M futures `metrics` (data.binance.vision,
daily files of 5-minute rows), kept to ONE row per UTC day -- the last one, the
state at the daily close. Only the days a coin was in the point-in-time top 40
(and the 35 days before, for the 30-day z-score) are fetched.

    python3 research/c493_fetch_metrics.py BNC_DIR OUTDIR

Writes OUTDIR/<SYM>.json {"<day_ms>": [count_long_short_ratio, sum_toptrader_long_short_ratio]}.
Re-runnable: days already in a file are skipped. One flat job list over 64 threads,
with a kept-alive session per thread, saved every 10,000 files."""
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


import threading, requests
_tls = threading.local()


def get(u, tries=4):
    """one kept-alive session per thread (a fresh TLS handshake per file cost 0.5 s)"""
    if not hasattr(_tls, 's'):
        _tls.s = requests.Session()
    for k in range(tries):
        try:
            r = _tls.s.get(u, timeout=40)
            if r.status_code == 404:
                return None
            r.raise_for_status()
            return r.content
        except Exception:
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


have = {}
for s in need:
    p = os.path.join(OUT, s + '.json')
    have[s] = json.load(open(p)) if os.path.exists(p) else {}
jobs = [(s, t) for s in need for t in need[s] if str(t) not in have[s]]
print(f"{len(jobs)} files to fetch", flush=True)
lock = threading.Lock()


def one(job):
    s, t = job
    d = dt.datetime.utcfromtimestamp(t / 1000).strftime('%Y-%m-%d')
    b = get(DL.format(s=s, d=d))
    try:
        v = last_row(b) if b else None
    except Exception:
        v = None
    with lock:
        have[s][str(t)] = v
    return s


def flush():
    with lock:
        snap = {s: dict(v) for s, v in have.items()}
    for s, v in snap.items():
        json.dump(v, open(os.path.join(OUT, s + '.json'), 'w'))


n = 0
with ThreadPoolExecutor(64) as ex:
    for _ in ex.map(one, jobs):
        n += 1
        if n % 10000 == 0:
            flush(); print(n, flush=True)
flush()
print('DONE', n)
