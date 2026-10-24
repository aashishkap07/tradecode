#!/usr/bin/env python3
"""C541: CoinDCX vs Binance, coin by coin (8 Oct 2026): last rent rate, rent interval, fees, minimum order.

    python3 research/c541_coindcx_check.py DIR      # DIR holds coins.json (Delta, CoinDCX and Pi42 coin lists)
"""
import json, sys, time, requests, concurrent.futures as cf
S = sys.argv[1]
coins = json.load(open(S + '/coins.json'))
D = set(coins['delta']); dcx = set(coins['dcx'])
both = sorted(D & dcx)
rt = requests.get('https://public.coindcx.com/market_data/v3/current_prices/futures/rt', timeout=20).json()['prices']
fi = {x['symbol']: int(x['fundingIntervalHours']) for x in requests.get('https://www.binance.com/fapi/v1/fundingInfo', timeout=20).json()}

def one(c):
    m = c + 'USDT'
    inst = requests.get('https://api.coindcx.com/exchange/v1/derivatives/futures/data/instrument',
                        params={'pair': f'B-{c}_USDT', 'margin_currency_short_name': 'INR'}, timeout=20).json().get('instrument', {})
    bf = requests.get('https://www.binance.com/fapi/v1/fundingRate', params={'symbol': m, 'limit': 3}, timeout=20).json()
    return c, inst, bf
out = {}
with cf.ThreadPoolExecutor(4) as ex:
    for c, inst, bf in ex.map(one, both):
        r = rt.get(f'B-{c}_USDT', {})
        last = bf[-1] if isinstance(bf, list) and bf else None
        out[c] = dict(dcx_fr=r.get('fr'), bn_last=float(last['fundingRate']) if last else None, bn_time=last['fundingTime'] if last else None,
                      dcx_freq=inst.get('funding_frequency'), bn_freq=fi.get(c + 'USDT', 8), min_notional=inst.get('min_notional'),
                      taker=inst.get('taker_fee'), maker=inst.get('maker_fee'), max_lev=inst.get('max_leverage_long'), status=inst.get('status'))
json.dump(out, open(S + '/dcx_check.json', 'w'), indent=0)
same = [c for c, v in out.items() if v['dcx_fr'] is not None and v['bn_last'] is not None and abs(v['dcx_fr'] - v['bn_last']) < 1e-9]
diff = [(c, v['dcx_fr'], v['bn_last']) for c, v in out.items() if c not in same]
print(f'Delta&CoinDCX coins {len(both)}: CoinDCX last rate == Binance last settled rate: {len(same)}; differ/missing: {len(diff)}')
print(' ', diff[:15])
fq = [(c, v['dcx_freq'], v['bn_freq']) for c, v in out.items() if v['dcx_freq'] != v['bn_freq']]
print(f'funding interval equal to Binance: {len(out) - len(fq)}; different: {len(fq)}', fq[:15])
from collections import Counter
print('taker fees', Counter(v['taker'] for v in out.values()), 'maker', Counter(v['maker'] for v in out.values()))
mn = sorted(((v['min_notional'] or 0), c) for c, v in out.items())
print('min_notional (USDT) range', mn[:3], mn[-8:], ' >100:', [c for x, c in mn if x > 100])
print('status', Counter(v['status'] for v in out.values()))
