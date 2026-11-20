#!/bin/bash
PAIRS="BTCUSDT ETHUSDT SOLUSDT XRPUSDT ADAUSDT DOGEUSDT LINKUSDT AVAXUSDT DOTUSDT LTCUSDT BCHUSDT ATOMUSDT NEARUSDT APTUSDT ARBUSDT OPUSDT INJUSDT SUIUSDT TIAUSDT FILUSDT ETCUSDT UNIUSDT AAVEUSDT ORDIUSDT PEPEUSDT WLDUSDT TAOUSDT ZECUSDT XMRUSDT KASUSDT RUNEUSDT GRTUSDT SEIUSDT ENAUSDT DASHUSDT"
fp(){ sym=$1; end=""; : > corpus1h/$sym.csv
 for p in $(seq 1 14); do
  u="https://api.bitget.com/api/v2/mix/market/history-candles?symbol=$sym&granularity=1H&productType=USDT-FUTURES&limit=200"
  [ -n "$end" ] && u="$u&endTime=$end"
  r=$(curl -s -m 25 "$u")
  echo "$r" | python3 -c "
import json,sys
d=json.load(sys.stdin).get('data') or []
for c in d: print(','.join(str(x) for x in c[:6]))" >> corpus1h/$sym.csv 2>/dev/null
  f=$(echo "$r" | python3 -c "
import json,sys
d=json.load(sys.stdin).get('data') or []
print(d[0][0] if d else '')" 2>/dev/null)
  [ -z "$f" ] && break; end=$f
 done; echo "$sym $(wc -l < corpus1h/$sym.csv)"; }
export -f fp
echo "$PAIRS" | tr ' ' '\n' | xargs -P 8 -I{} bash -c 'fp {}'
