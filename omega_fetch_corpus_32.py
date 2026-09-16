import json, os, sys, time, urllib.request, concurrent.futures as cf
PAIRS = """BTCUSDT ETHUSDT SOLUSDT XRPUSDT ADAUSDT DOGEUSDT LINKUSDT AVAXUSDT
DOTUSDT LTCUSDT ATOMUSDT NEARUSDT APTUSDT ARBUSDT OPUSDT INJUSDT SUIUSDT
FILUSDT UNIUSDT AAVEUSDT ZECUSDT ENAUSDT PEPEUSDT WIFUSDT TIAUSDT SEIUSDT
JUPUSDT PYTHUSDT LDOUSDT RUNEUSDT ORDIUSDT 1000BONKUSDT""".split()
OUT = 'corpusL'
def fetch(sym, pages=52):
    rows, end = [], None
    for _ in range(pages):
        u = (f"https://api.bitget.com/api/v2/mix/market/history-candles?symbol={sym}"
             f"&granularity=15m&productType=USDT-FUTURES&limit=200")
        if end: u += f"&endTime={end}"
        try:
            with urllib.request.urlopen(u, timeout=25) as r:
                d = json.loads(r.read()).get('data') or []
        except Exception:
            time.sleep(0.5); continue
        if not d: break
        rows = d + rows
        end = d[0][0]
        time.sleep(0.05)
    if len(rows) < 1000: return sym, 0
    with open(f"{OUT}/{sym}.csv", 'w') as f:
        for c in rows:
            f.write(','.join(str(x) for x in c[:6]) + '\n')
    return sym, len(rows)
with cf.ThreadPoolExecutor(8) as ex:
    tot = 0
    for sym, n in ex.map(fetch, PAIRS):
        tot += n
        print(f"{sym:<14}{n}", flush=True)
    print("TOTAL BARS", tot)
