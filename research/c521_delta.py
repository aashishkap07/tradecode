#!/usr/bin/env python3
"""Round 14 (C521), Part D (descriptive): Delta Exchange India against Binance, for the parallel paper book.

    python3 research/c521_delta.py BNC_DIR DAYS INPUTS_NPZ     (INPUTS_NPZ: the server's c488_inputs.npz, logs branch)

D1 prices:  daily close-to-close returns of the coins both venues list (the bot's 80 candidates
            of 2 Oct 2026 that Delta lists as crypto), Delta vs Binance USDⓈ-M, last DAYS days.
D2 funding: Delta's funding (FUNDING:<SYM> hourly candles, % per interval, exchanged every
            rate_exchange_interval seconds) against Binance's (fundingRate), daily sums.
D3 sizes:   the N2+N3 book's weights over the archive's last 180 days, held on Delta's contracts
            (contract_value x price per contract, at least one) at $500, $1,000, $2,000:
            the share of the planned gross that Delta can hold, against Binance's minimums.
Public endpoints only: api.india.delta.exchange and www.binance.com/fapi (fapi.binance.com
refuses this sandbox).
"""
import os, sys, json, math, time, datetime as dt, concurrent.futures as cf
import numpy as np, requests

HERE = os.path.dirname(os.path.abspath(__file__))
DELTA = 'https://api.india.delta.exchange'
BN = 'https://www.binance.com'
DAYS = int(sys.argv[2]) if len(sys.argv) > 2 else 120
DAY = 86400


def get(url, params, tries=4):
    for k in range(tries):
        try:
            r = requests.get(url, params=params, timeout=30)
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass
        time.sleep(1 + 2 * k)
    return None


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
        out[p['underlying_asset']['symbol']] = dict(sym=p['symbol'], cv=float(p['contract_value']),
                                                    iv=int((p.get('product_specs') or {}).get('rate_exchange_interval') or 28800),
                                                    taker=float(p['taker_commission_rate']))
    return out


def main():
    now = int(time.time()) // DAY * DAY
    st = now - DAYS * DAY
    prods = delta_products()
    z = np.load(sys.argv[3])
    cands = [str(k).split('/')[0] for k in z['keep']]
    both = [c for c in cands if c in prods]
    print(f"Delta Exchange India: {len(prods)} crypto perps (tokenised stocks, ETFs and metals left out); "
          f"of the bot's {len(cands)} candidates (2 Oct) Delta lists {len(both)}: {' '.join(both)}")
    print(f"missing on Delta: {' '.join(c for c in cands if c not in prods)}")

    def one(c):
        p = prods[c]
        dk = get(DELTA + '/v2/history/candles', dict(resolution='1d', symbol=p['sym'], start=st, end=now))
        fk = get(DELTA + '/v2/history/candles', dict(resolution='1h', symbol='FUNDING:' + p['sym'], start=st, end=now))
        bk = get(BN + '/fapi/v1/klines', dict(symbol=c + 'USDT', interval='1d', startTime=st * 1000, limit=DAYS + 2))
        bf = get(BN + '/fapi/v1/fundingRate', dict(symbol=c + 'USDT', startTime=st * 1000, limit=1000))
        return c, dk, fk, bk, bf
    with cf.ThreadPoolExecutor(6) as ex:
        res = list(ex.map(one, both))
    rows = []
    for c, dk, fk, bk, bf in res:
        if not dk or not bk or not dk.get('result'):
            continue
        dc = {int(x['time']): float(x['close']) for x in dk['result']}
        bc = {int(x[0]) // 1000: float(x[4]) for x in bk}
        days = sorted(set(dc) & set(bc))
        if len(days) < 30:
            continue
        a = np.array([dc[d] for d in days]); b = np.array([bc[d] for d in days])
        ra, rb = a[1:] / a[:-1] - 1, b[1:] / b[:-1] - 1
        corr = float(np.corrcoef(ra, rb)[0, 1]); te = float((ra - rb).std() * math.sqrt(365))
        # funding: Delta's rate at each exchange (the hourly value in force just before it), % -> fraction
        iv = prods[c]['iv'] // 3600
        dfund = {}
        for x in (fk or {}).get('result') or []:
            t = int(x['time'])
            if (t // 3600 + 1) % iv == 0:                                # the hour ending at an exchange time
                d = (t + 3600) // DAY * DAY
                dfund[d] = dfund.get(d, 0.0) + float(x['close']) / 100.0
        bfund = {}
        for x in bf or []:
            d = int(x['fundingTime']) // 1000 // DAY * DAY
            bfund[d] = bfund.get(d, 0.0) + float(x['fundingRate'])
        fd = sorted(set(dfund) & set(bfund) & set(days))
        fdiff = float(np.mean([dfund[d] - bfund[d] for d in fd]) * 365) if len(fd) > 20 else float('nan')
        fcorr = float(np.corrcoef([dfund[d] for d in fd], [bfund[d] for d in fd])[0, 1]) if len(fd) > 20 else float('nan')
        rows.append(dict(coin=c, days=len(days), corr=corr, te=te, mean_diff=float((ra - rb).mean() * 365),
                         fund_days=len(fd), delta_fund_ann=float(np.mean([dfund[d] for d in fd]) * 365) if fd else float('nan'),
                         bn_fund_ann=float(np.mean([bfund[d] for d in fd]) * 365) if fd else float('nan'),
                         fund_diff_ann=fdiff, fund_corr=fcorr))
    print(f"\nD1/D2 over the last {DAYS} days (annualised; funding as paid by a long):")
    print(f"  {'coin':9} {'days':>4} {'ret corr':>8} {'tracking':>8} {'Delta fund':>10} {'Binance':>8} {'diff':>7} {'fund corr':>9}")
    for r in sorted(rows, key=lambda r: r['coin']):
        print(f"  {r['coin']:9} {r['days']:4d} {r['corr']:8.4f} {100 * r['te']:7.2f}% {100 * r['delta_fund_ann']:9.1f}% "
              f"{100 * r['bn_fund_ann']:7.1f}% {100 * r['fund_diff_ann']:+6.1f}% {r['fund_corr']:9.2f}")
    if rows:
        print(f"  median: return correlation {np.median([r['corr'] for r in rows]):.4f}, tracking error "
              f"{100 * np.median([r['te'] for r in rows]):.2f}%/yr, funding Delta - Binance "
              f"{100 * np.nanmedian([r['fund_diff_ann'] for r in rows]):+.1f}%/yr, funding correlation "
              f"{np.nanmedian([r['fund_corr'] for r in rows]):.2f}")
    # D3: what Delta's contracts can hold of the book's recent plans
    out3 = {}
    bdir = sys.argv[1]
    sys.path.insert(0, HERE)
    import omega_c521_research as Q
    D = Q.prep(bdir)
    x, Wc, _ = Q.book(D, Q.sleeves(D))
    last = range(len(D['T']) - 180, len(D['T']))
    print(f"\nD3 the share of the N2+N3 book's planned gross that each venue's contracts hold (last 180 days of the archive):")
    for eq in (500.0, 1000.0, 2000.0):
        held_d, held_b, plan = 0.0, 0.0, 0.0
        for i in last:
            for j, s in enumerate(D['syms']):
                w = Wc[i, j]
                if w == 0.0 or np.isnan(D['c'][i, j]):
                    continue
                tgt = abs(w) * eq; plan += tgt
                c = s[:-4]
                px = D['c'][i, j]
                if c in prods:
                    cn = prods[c]['cv'] * px
                    held_d += round(tgt / cn) * cn if cn > 0 else 0.0
                fl = max(6.0, Q.BIG.get(s, 5.0))
                held_b += tgt if tgt >= fl else 0.0
        out3[eq] = dict(delta=held_d / plan, binance=held_b / plan)
        print(f"  ${eq:,.0f}: Delta holds {100 * held_d / plan:.0f}% of the planned gross (rounded to whole contracts), "
              f"Binance {100 * held_b / plan:.0f}% (its minimums)")
    json.dump(dict(rows=rows, d3={str(k): v for k, v in out3.items()}, delta_count=len(prods), listed=both),
              open(os.path.join(HERE, 'c521_delta.json'), 'w'), indent=1)


if __name__ == '__main__':
    main()
