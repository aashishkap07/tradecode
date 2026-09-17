import json, os, time, urllib.request, concurrent.futures as cf
PAIRS = """BTCUSDT ETHUSDT SOLUSDT XRPUSDT ADAUSDT DOGEUSDT LINKUSDT AVAXUSDT
DOTUSDT LTCUSDT ATOMUSDT NEARUSDT APTUSDT ARBUSDT OPUSDT INJUSDT SUIUSDT
FILUSDT UNIUSDT AAVEUSDT ZECUSDT ENAUSDT PEPEUSDT WIFUSDT TIAUSDT SEIUSDT
JUPUSDT PYTHUSDT LDOUSDT RUNEUSDT ORDIUSDT 1000BONKUSDT""".split()
def fetch(sym):
    rows=[]
    for pg in range(1,5):
        u=(f"https://api.bitget.com/api/v2/mix/market/history-fund-rate?symbol={sym}"
           f"&productType=usdt-futures&pageSize=100&pageNo={pg}")
        try:
            with urllib.request.urlopen(u,timeout=25) as r:
                d=json.loads(r.read()).get('data') or []
        except Exception:
            time.sleep(0.4); continue
        if not d: break
        rows += d; time.sleep(0.05)
    if not rows: return sym,0
    rows.sort(key=lambda r:int(r['fundingTime']))
    with open(f"corpusF/{sym}.csv",'w') as f:
        for r in rows: f.write(f"{r['fundingTime']},{r['fundingRate']}\n")
    return sym,len(rows)
with cf.ThreadPoolExecutor(8) as ex:
    tot=0
    for sym,n in ex.map(fetch,PAIRS): tot+=n
    print("funding settlements fetched:",tot)
