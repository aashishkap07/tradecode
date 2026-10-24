#!/usr/bin/env python3
"""Round 16 (C525) D1, descriptive: Delta Exchange India's option implied volatility vs Deribit's.

    python3 research/c525_delta_options.py

Near-the-money options (strike within 5% of spot) at the same expiry, strike and type on both,
BTC and ETH, now. Delta: /v2/tickers quotes.mark_iv, bid_iv, ask_iv; Deribit:
public/get_book_summary_by_currency mark_iv. If Indian retail overpaid for options as it does for
perpetual longs (round 15), Delta's IV would sit above Deribit's.
"""
import json, urllib.request, re, datetime as dt
import numpy as np

MON = {m: i + 1 for i, m in enumerate('JAN FEB MAR APR MAY JUN JUL AUG SEP OCT NOV DEC'.split())}


def get(url):
    r = urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'}), timeout=40)
    return json.loads(r.read())


def main():
    print(f"Delta India vs Deribit option implied volatility, {dt.datetime.utcnow():%Y-%m-%d %H:%M} UTC")
    for cur in ('BTC', 'ETH'):
        dl = get(f'https://api.india.delta.exchange/v2/tickers?contract_types=call_options,put_options&underlying_asset_symbols={cur}')['result']
        db = get(f'https://www.deribit.com/api/v2/public/get_book_summary_by_currency?currency={cur}&kind=option')['result']
        deri = {}
        for x in db:
            m = re.match(rf'{cur}-(\d+)([A-Z]+)(\d+)-(\d+)-([CP])', x['instrument_name'])
            if m and x.get('mark_iv') is not None:
                day, mon, yy, k, cp = m.groups()
                deri[(dt.date(2000 + int(yy), MON[mon], int(day)), int(k), cp)] = x['mark_iv'] / 100
        rows = []
        for x in dl:
            m = re.match(r'([CP])-\w+-(\d+)-(\d{2})(\d{2})(\d{2})', x['symbol'])
            if not m:
                continue
            cp, k, d, mo, y = m.groups()
            key = (dt.date(2000 + int(y), int(mo), int(d)), int(k), cp)
            spot = float(x.get('spot_price') or 0)
            q = x.get('quotes') or {}
            if key in deri and spot and abs(int(k) / spot - 1) < 0.05 and q.get('mark_iv'):
                rows.append((key[0], float(q['mark_iv']), float(q.get('bid_iv') or 0), deri[key]))
        if not rows:
            print(f"  {cur}: no matched options"); continue
        diff = np.array([r[1] - r[3] for r in rows]); bd = np.array([r[2] - r[3] for r in rows if r[2] > 0.01])
        print(f"  {cur}: {len(rows)} matched near-the-money options, {len(set(r[0] for r in rows))} expiries; Delta mark IV - Deribit: "
              f"median {100 * np.median(diff):+.1f} vol points; Delta BID IV - Deribit mark: median {100 * np.median(bd):+.1f} points")


if __name__ == '__main__':
    main()
