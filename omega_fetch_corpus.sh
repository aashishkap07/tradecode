#!/bin/bash
PAIRS="BTCUSDT ETHUSDT SOLUSDT XRPUSDT ADAUSDT DOGEUSDT LINKUSDT AVAXUSDT DOTUSDT LTCUSDT
BCHUSDT ATOMUSDT NEARUSDT APTUSDT ARBUSDT OPUSDT INJUSDT SUIUSDT SEIUSDT TIAUSDT
FILUSDT ETCUSDT UNIUSDT AAVEUSDT ENAUSDT ORDIUSDT PEPEUSDT WLDUSDT TAOUSDT ZECUSDT
XMRUSDT DASHUSDT KASUSDT RUNEUSDT GRTUSDT"
OUT=corpus
mkdir -p $OUT
fetch_pair() {
  sym=$1; end=""; : > $OUT/$sym.csv
  for p in $(seq 1 12); do
    url="https://api.bitget.com/api/v2/mix/market/history-candles?symbol=$sym&granularity=15m&productType=USDT-FUTURES&limit=200"
    [ -n "$end" ] && url="$url&endTime=$end"
    r=$(curl -s -m 25 "$url")
    n=$(echo "$r" | grep -o '\["' | wc -l)
    [ "$n" -lt 2 ] && break
    echo "$r" | python3 -c "
import json,sys
d=json.load(sys.stdin).get('data') or []
for c in d: print(','.join(str(x) for x in c[:6]))
" >> $OUT/$sym.csv
    first=$(echo "$r" | python3 -c "
import json,sys
d=json.load(sys.stdin).get('data') or []
print(d[0][0] if d else '')
")
    [ -z "$first" ] && break
    end=$first
  done
  echo "$sym $(wc -l < $OUT/$sym.csv)"
}
export -f fetch_pair; export OUT
echo "$PAIRS" | tr ' ' '\n' | grep -v '^$' | xargs -P 8 -I{} bash -c 'fetch_pair {}'
