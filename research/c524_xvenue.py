#!/usr/bin/env python3
"""Round 15 (C524) Part B: a cross-venue funding spread, Delta Exchange India vs Binance USDⓈ-M.

    python3 research/c524_xvenue.py CACHE_DIR

Rules and bar fixed in research/c524_preregistration.md (committed first):
  s       trailing 7-day mean of (Delta funding - Binance funding), annualised, as paid by a long
  enter   |s| >= 20%/yr: short the perp on the venue where longs pay more, long it on the other
  exit    |s| < 10%/yr or s changes sign; at most 10 pairs, each 10% of capital per leg
  P&L     funding net + (long leg's daily return - short leg's) - costs on entry and exit of both legs
          (Binance 0.05% + 0.02% half-spread; Delta 0.05% x 1.18 GST + 0.02% half-spread)
  window  2024-10-01 .. 2026-09-30; decided on day t, earning day t+1
  bar     net HAC t >= 2, >= 3 of 4 half-years positive, the last 6 months positive
Delta's funding: FUNDING:<SYM> records at each exchange time (C523: the value set AT T is the rate
settled at T). Public endpoints only (api.india.delta.exchange, www.binance.com/fapi).
"""
import os, sys, json, math, time, datetime as dt, concurrent.futures as cf
import numpy as np, requests

DELTA = 'https://api.india.delta.exchange'
BN = 'https://www.binance.com'
DAY = 86400
START = int(dt.datetime(2024, 10, 1, tzinfo=dt.timezone.utc).timestamp())
END = int(dt.datetime(2026, 10, 1, tzinfo=dt.timezone.utc).timestamp())       # exclusive
ENTER, EXIT_, MAXP, SIZE, WIN = 0.20, 0.10, 10, 0.10, 7
COST_B = 0.0005 + 0.0002
COST_D = 0.0005 * 1.18 + 0.0002


def get(url, params, tries=5):
    for k in range(tries):
        try:
            r = requests.get(url, params=params, timeout=40)
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass
        time.sleep(1 + 2 * k)
    return None


def cached(cache, name, fn):
    p = os.path.join(cache, name + '.json')
    if os.path.exists(p):
        return json.load(open(p))
    x = fn()
    if x is not None:
        json.dump(x, open(p, 'w'))
    return x


def delta_products():
    d = get(DELTA + '/v2/products', dict(contract_types='perpetual_futures', states='live'))['result']
    out = {}
    for p in d:
        tags = (p.get('product_specs') or {}).get('tags') or []
        top = (p.get('product_specs') or {}).get('top_tag') or ''
        if top == 'tradfi' or any(t in ('xStock', 'metal') for t in tags):
            continue
        if (p.get('settling_asset') or {}).get('symbol') != 'USD':
            continue
        out[p['underlying_asset']['symbol']] = dict(sym=p['symbol'], iv=int((p.get('product_specs') or {}).get('rate_exchange_interval') or 28800))
    return out


def binance_perps():
    d = get(BN + '/fapi/v1/exchangeInfo', {})
    return {s['symbol'] for s in d['symbols'] if s.get('contractType') == 'PERPETUAL' and s.get('quoteAsset') == 'USDT'}


def delta_funding(sym):
    out = {}
    t = START - 10 * DAY
    while t < END:
        e = min(END, t + 120 * DAY)
        r = (get(DELTA + '/v2/history/candles', dict(resolution='1h', symbol='FUNDING:' + sym, start=t, end=e)) or {}).get('result') or []
        out.update({int(x['time']): float(x['close']) for x in r})
        t = e
        time.sleep(0.15)
    return sorted(out.items())


def delta_daily(sym):
    r = (get(DELTA + '/v2/history/candles', dict(resolution='1d', symbol=sym, start=START - 10 * DAY, end=END)) or {}).get('result') or []
    return sorted((int(x['time']), float(x['close'])) for x in r)


def delta_daily_mark(sym):
    r = (get(DELTA + '/v2/history/candles', dict(resolution='1d', symbol='MARK:' + sym, start=START - 10 * DAY, end=END)) or {}).get('result') or []
    return sorted((int(x['time']), float(x['close'])) for x in r)


def bn_funding(sym):
    out, t = [], (START - 10 * DAY) * 1000
    while t < END * 1000:
        r = get(BN + '/fapi/v1/fundingRate', dict(symbol=sym, startTime=t, endTime=END * 1000, limit=1000)) or []
        if not r:
            break
        out += [(int(x['fundingTime']), float(x['fundingRate'])) for x in r]
        if len(r) < 1000:
            break
        t = int(r[-1]['fundingTime']) + 1
    return out


def bn_daily(sym):
    r = get(BN + '/fapi/v1/klines', dict(symbol=sym, interval='1d', startTime=(START - 10 * DAY) * 1000, limit=1000)) or []
    return [(int(x[0]) // 1000, float(x[4])) for x in r]


def delta_daily_funding(recs, iv_now, shift00=False):
    """sum per UTC day of Delta's rate at each exchange time, fraction. The exchange interval is the
    product's current one unless the record shows otherwise: per 30-day block, a 4-hour product whose
    values never change at 04/12/20 UTC but do at 00/08/16 was on 8 hours then."""
    v = dict(recs)
    hrs = iv_now // 3600
    days = {}
    ts = sorted(v)
    blocks = {}
    for t in ts:
        blocks.setdefault((t - START) // (30 * DAY), []).append(t)
    for b, tt in blocks.items():
        h_iv = hrs
        if hrs == 4:
            ch4 = sum(1 for t in tt if (t // 3600) % 8 == 4 and (t - 3600) in v and v[t] != v[t - 3600])
            ch8 = sum(1 for t in tt if (t // 3600) % 8 == 0 and (t - 3600) in v and v[t] != v[t - 3600])
            if ch4 == 0 and ch8 > 0:
                h_iv = 8
        for t in tt:
            if (t // 3600) % h_iv == 0:
                d = (t - (1 if shift00 else 0)) // DAY * DAY
                days[d] = days.get(d, 0.0) + v[t] / 100.0
    return days


def hac_t(x, lags=10):
    x = np.asarray(x, float); n = len(x)
    if n < 30 or x.std() == 0:
        return float('nan')
    m = x.mean(); e = x - m
    s = (e @ e) / n
    for l in range(1, lags + 1):
        s += 2 * (1 - l / (lags + 1)) * (e[l:] @ e[:-l]) / n
    return float(m / math.sqrt(s / n))


def load(cache):
    os.makedirs(cache, exist_ok=True)
    prods = delta_products()
    bset = binance_perps()
    both = sorted(c for c in prods if c + 'USDT' in bset)
    print(f"Delta crypto perps {len(prods)}; listed on Binance USDⓈ-M too: {len(both)}", flush=True)

    def one(c):
        p = prods[c]
        df = cached(cache, 'dfund_' + c, lambda: delta_funding(p['sym']))
        dp = cached(cache, 'dpx_' + c, lambda: delta_daily(p['sym']))
        dm = cached(cache, 'dmark_' + c, lambda: delta_daily_mark(p['sym'])) if os.environ.get('C524_MARK') else None
        bf = cached(cache, 'bfund_' + c, lambda: bn_funding(c + 'USDT'))
        bp = cached(cache, 'bpx_' + c, lambda: bn_daily(c + 'USDT'))
        return c, df, dp, dm, bf, bp
    with cf.ThreadPoolExecutor(4) as ex:
        return prods, list(ex.map(one, both))


def matrices(prods, res, shift00=False, mark=False):
    D = np.arange(START, END, DAY)
    k = len(res)
    fD = np.full((len(D), k), np.nan); fB = fD.copy(); pD = fD.copy(); pB = fD.copy()
    idx = {int(t): i for i, t in enumerate(D)}
    names = []
    for j, (c, df, dp, dm, bf, bp) in enumerate(res):
        names.append(c)
        px = dm if (mark and dm) else dp
        if not df or not bf or not px or not bp:
            continue
        for d, x in delta_daily_funding(df, prods[c]['iv'], shift00).items():
            if d in idx: fD[idx[d], j] = x
        bd = {}
        for t, r in bf:
            tt = t // 1000 - (1 if shift00 else 0)
            d = tt // DAY * DAY
            bd[d] = bd.get(d, 0.0) + r
        for d, x in bd.items():
            if d in idx: fB[idx[d], j] = x
        for t, x in px:
            if t // DAY * DAY in idx: pD[idx[t // DAY * DAY], j] = x
        for t, x in bp:
            if t in idx: pB[idx[t], j] = x
    return D, names, fD, fB, pD, pB


def simulate(D, names, fD, fB, pD, pB, cost_mult=1.0, allow=None, verbose=True, tag='X1'):
    k = len(names)
    rD = np.full_like(pD, np.nan); rB = rD.copy()
    rD[1:] = pD[1:] / pD[:-1] - 1; rB[1:] = pB[1:] / pB[:-1] - 1
    ok = ~np.isnan(fD) & ~np.isnan(fB) & ~np.isnan(rD) & ~np.isnan(rB)
    if allow is not None:
        ok &= np.array([n in allow for n in names])[None, :]
    sp = fD - fB                                                     # per day, as paid by a long
    s7 = np.full_like(sp, np.nan)
    with np.errstate(invalid='ignore'):
        for i in range(WIN - 1, len(D)):
            blk = sp[i - WIN + 1:i + 1]
            n = (~np.isnan(blk)).sum(0)
            s7[i] = np.where(n >= WIN, np.nanmean(blk, 0) * 365, np.nan)
    if allow is not None:
        s7[:, ~np.array([n in allow for n in names])] = np.nan
    cB, cD = COST_B * cost_mult, COST_D * cost_mult
    held = {}
    pnl = np.zeros(len(D)); fund_p = np.zeros(len(D)); px_p = np.zeros(len(D)); cost_p = np.zeros(len(D))
    npairs = np.zeros(len(D)); picks = []
    for i in range(len(D) - 1):
        sig = s7[i]
        for j in list(held):
            side = held[j]
            if np.isnan(sig[j]) or abs(sig[j]) < EXIT_ or np.sign(sig[j]) != side:
                cost_p[i + 1] += SIZE * (cB + cD)
                del held[j]
        cand = [j for j in range(k) if j not in held and not np.isnan(sig[j]) and abs(sig[j]) >= ENTER and ok[i + 1, j]]
        cand.sort(key=lambda j: -abs(sig[j]))
        for j in cand[:max(0, MAXP - len(held))]:
            held[j] = int(np.sign(sig[j]))
            cost_p[i + 1] += SIZE * (cB + cD)
            picks.append((int(D[i]), names[j], float(sig[j])))
        for j, side in held.items():
            if not ok[i + 1, j]:
                continue
            fund_p[i + 1] += SIZE * side * sp[i + 1, j]
            px_p[i + 1] += SIZE * side * (rB[i + 1, j] - rD[i + 1, j])
        npairs[i + 1] = len(held)
        pnl[i + 1] = fund_p[i + 1] + px_p[i + 1] - cost_p[i + 1]
    live = np.arange(len(D)) >= WIN
    x = pnl[live]; Dl = D[live]
    t = hac_t(x)
    ann = x.mean() * 365
    months = {}
    for d_, v in zip(Dl, x):
        m = dt.datetime.utcfromtimestamp(d_).strftime('%Y-%m')
        months[m] = months.get(m, 0.0) + v
    mv = np.array(list(months.values()))
    halves = [('2024-10..2025-03', '2024-10', '2025-03'), ('2025-04..2025-09', '2025-04', '2025-09'),
              ('2025-10..2026-03', '2025-10', '2026-03'), ('2026-04..2026-09 (last 6 months)', '2026-04', '2026-09')]
    hp = [sum(val for m, val in months.items() if a <= m <= b) for _, a, b in halves]
    passed = (t >= 2) and (sum(1 for v in hp if v > 0) >= 3) and hp[-1] > 0
    by = {}
    for _, c, s_ in picks:
        by[c] = by.get(c, 0) + 1
    wk = []
    for i in range(WIN, len(D) - WIN, WIN):
        a_, b_ = s7[i], s7[i + WIN]
        m = ~np.isnan(a_) & ~np.isnan(b_)
        if m.sum() > 10:
            wk.append(np.corrcoef(a_[m], b_[m])[0, 1])
    if verbose:
        print(f"\n{tag} cross-venue funding spread, {dt.datetime.utcfromtimestamp(Dl[0]):%Y-%m-%d} .. {dt.datetime.utcfromtimestamp(Dl[-1]):%Y-%m-%d}, "
              f"{k} coins on both venues, on capital (2x gross per venue at 10 pairs)")
        print(f"  net {100 * ann:+.2f}%/yr  HAC t {t:+.2f}  vol {100 * x.std() * math.sqrt(365):.2f}%/yr  "
              f"| funding {100 * fund_p[live].mean() * 365:+.2f}%/yr  price {100 * px_p[live].mean() * 365:+.2f}%/yr  "
              f"costs {100 * cost_p[live].mean() * 365:.2f}%/yr  | pairs held: median {np.median(npairs[live]):.0f}, max {int(npairs.max())}")
        print(f"  months: {len(mv)}, positive {int((mv > 0).sum())}, median {100 * np.median(mv):+.2f}%, worst {100 * mv.min():+.2f}%, best {100 * mv.max():+.2f}%")
        for (name, _, _), v in zip(halves, hp):
            print(f"  {name:34} {100 * v:+.2f}%")
        print(f"  BAR (t >= 2, >= 3/4 half-years, last 6 months > 0): {'PASSED' if passed else 'NOT PASSED'}")
        print("  entries by coin: " + ", ".join(f"{c} {n}" for c, n in sorted(by.items(), key=lambda a: -a[1])[:15]))
        if wk:
            print(f"  persistence: the 7-day spread's correlation with the next 7 days', across coins: median {np.median(wk):+.2f} ({len(wk)} weeks)")
    return dict(net_ann=ann, t=t, months=months, halves=hp, passed=bool(passed), coins=names, entries=by,
                fund_ann=float(fund_p[live].mean() * 365), price_ann=float(px_p[live].mean() * 365),
                cost_ann=float(cost_p[live].mean() * 365), persistence=float(np.median(wk)) if wk else None,
                worst_month=float(mv.min()), pos_months=int((mv > 0).sum()), n_months=len(mv))


def main(cache):
    prods, res = load(cache)
    D, names, fD, fB, pD, pB = matrices(prods, res)
    out = simulate(D, names, fD, fB, pD, pB)
    json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'c524_xvenue.json'), 'w'), indent=1, default=float)


if __name__ == '__main__':
    main(sys.argv[1])
