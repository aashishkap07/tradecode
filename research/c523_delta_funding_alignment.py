#!/usr/bin/env python3
"""C523: which Delta Exchange India FUNDING:<SYM> value is the rate settled at an exchange time T?

    python3 research/c523_delta_funding_alignment.py [DAYS]

FUNDING:<SYM> hourly candles are a step series that changes at each exchange (00/08/16 UTC for
8-hour coins). Two readings:
  AT     the value written at T is the rate settled at T;
  BEFORE the value in force during the hour before T (written at the previous exchange) is.
Binance publishes the rate it settled at T (fapi/v1/fundingRate); both venues' rates come from
the same perp premium over the same 8 hours, so the right reading correlates better with it.
Also shown: Delta's API answers a window that holds no exchange time (e.g. 07:00-07:59 UTC)
with nothing, which is what the C521 bot asked for. Public endpoints only.
"""
import sys, json, time, urllib.request
import numpy as np

DAYS = int(sys.argv[1]) if len(sys.argv) > 1 else 30


def get(url):
    r = urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'}), timeout=30)
    return json.loads(r.read())


def main():
    now = int(time.time()); st = now - DAYS * 86400
    print(f"Delta FUNDING:<SYM> vs Binance's settled rate, per exchange, last {DAYS} days")
    print(f"  {'coin':6} {'n':>4} {'AT T':>6} {'BEFORE T':>9}")
    at, bef = [], []
    for c in ('BTC', 'ETH', 'XRP', 'DOGE', 'BNB', 'SUI', 'ADA', 'LINK', 'AVAX', 'LTC', 'DOT', 'NEAR'):
        try:
            fk = get(f'https://api.india.delta.exchange/v2/history/candles?resolution=1h&symbol=FUNDING:{c}USD'
                     f'&start={st}&end={now}')['result']
            bf = get(f'https://www.binance.com/fapi/v1/fundingRate?symbol={c}USDT&startTime={st * 1000}&limit=1000')
        except Exception as e:
            print(f"  {c:6} {type(e).__name__}"); continue
        dv = {int(x['time']): float(x['close']) for x in fk}
        b = {int(x['fundingTime']) // 1000 // 3600 * 3600: float(x['fundingRate']) * 100 for x in bf}
        T = [t for t in sorted(b) if t in dv and (t - 3600) in dv]
        if len(T) < 20 or np.std([dv[t] for t in T]) == 0:
            print(f"  {c:6} {len(T):4d}  (Delta's rate constant: no test)"); continue
        bn = [b[t] for t in T]
        c1 = float(np.corrcoef([dv[t] for t in T], bn)[0, 1]); c2 = float(np.corrcoef([dv[t - 3600] for t in T], bn)[0, 1])
        at.append(c1); bef.append(c2)
        print(f"  {c:6} {len(T):4d} {c1:+6.2f} {c2:+9.2f}")
        time.sleep(0.3)
    print(f"  median: AT T {np.median(at):+.2f}, BEFORE T {np.median(bef):+.2f}; AT wins on {sum(a > b for a, b in zip(at, bef))}"
          f" of {len(at)} coins")
    due = now // 28800 * 28800
    w0 = get(f'https://api.india.delta.exchange/v2/history/candles?resolution=1h&symbol=FUNDING:BTCUSD'
             f'&start={due - 3600}&end={due - 1}')['result']
    w1 = get(f'https://api.india.delta.exchange/v2/history/candles?resolution=1h&symbol=FUNDING:BTCUSD'
             f'&start={due}&end={due + 3599}')['result']
    print(f"Delta's answer for BTC, the hour BEFORE the last exchange: {len(w0)} candles; the hour starting AT it: {len(w1)}")


if __name__ == '__main__':
    main()
