#!/bin/bash
PAIRS="BTCUSDT ETHUSDT SOLUSDT XRPUSDT ADAUSDT DOGEUSDT LINKUSDT AVAXUSDT DOTUSDT LTCUSDT ATOMUSDT NEARUSDT APTUSDT ARBUSDT OPUSDT INJUSDT SUIUSDT FILUSDT UNIUSDT AAVEUSDT ZECUSDT KASUSDT GRTUSDT ENAUSDT"
fp(){ sym=$1; end=""; : > corpusL/$sym.csv
 for p in $(seq 1 58); do
  u="https://api.bitget.com/api/v2/mix/market/history-candles?symbol=$sym&granularity=15m&productType=USDT-FUTURES&limit=200"
  [ -n "$end" ] && u="$u&endTime=$end"
  r=$(curl -s -m 20 "$u")
  echo "$r" | python3 -c "
import json,sys
d=json.load(sys.stdin).get('data') or []
for c in d: print(','.join(str(x) for x in c[:6]))" >> corpusL/$sym.csv 2>/dev/null
  f=$(echo "$r" | python3 -c "
import json,sys
d=json.load(sys.stdin).get('data') or []
print(d[0][0] if d else '')" 2>/dev/null)
  [ -z "$f" ] && break; end=$f
 done; echo "$sym $(wc -l < corpusL/$sym.csv)"; }
export -f fp
echo "$PAIRS" | tr ' ' '\n' | xargs -P 10 -I{} bash -c 'fp {}'
