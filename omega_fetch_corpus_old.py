"""A SEPARATE BATCH at a DIFFERENT TIME. Standing Rule 9, honoured this time.

corpusL/ holds the most recent ~108 days. This walks PAST that window and
collects the ~108 days before it, so the replication is on data the first
measurement never touched. C459 shipped on a within-window 4/4 and did not
replicate; this is the step that was skipped.
"""
import json, os, time, urllib.request, concurrent.futures as cf
PAIRS = """BTCUSDT ETHUSDT SOLUSDT XRPUSDT ADAUSDT DOGEUSDT LINKUSDT AVAXUSDT
DOTUSDT LTCUSDT ATOMUSDT NEARUSDT APTUSDT ARBUSDT OPUSDT INJUSDT SUIUSDT
FILUSDT UNIUSDT AAVEUSDT ZECUSDT ENAUSDT PEPEUSDT WIFUSDT TIAUSDT SEIUSDT
JUPUSDT PYTHUSDT LDOUSDT RUNEUSDT ORDIUSDT 1000BONKUSDT""".split()
SKIP, TAKE = 52, 52
def fetch(sym):
    end=None; rows=[]
    for page in range(SKIP+TAKE):
        u=(f"https://api.bitget.com/api/v2/mix/market/history-candles?symbol={sym}"
           f"&granularity=15m&productType=USDT-FUTURES&limit=200")
        if end: u+=f"&endTime={end}"
        try:
            with urllib.request.urlopen(u,timeout=25) as r:
                d=json.loads(r.read()).get('data') or []
        except Exception:
            time.sleep(0.5); continue
        if not d: break
        if page>=SKIP: rows = d + rows
        end=d[0][0]; time.sleep(0.05)
    if len(rows)<1000: return sym,0
    with open(f"corpusO/{sym}.csv",'w') as f:
        for c in rows: f.write(','.join(str(x) for x in c[:6])+'\n')
    return sym,len(rows)
with cf.ThreadPoolExecutor(8) as ex:
    tot=0
    for sym,n in ex.map(fetch,PAIRS):
        tot+=n
    print("TOTAL BARS",tot)
