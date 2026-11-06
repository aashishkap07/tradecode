#!/usr/bin/env python3
"""Round 22b (research/c542b_preregistration.md): run ONCE on the operator's server, which can reach Bybit (this
research sandbox cannot: Bybit blocks its country).

    sudo -u omega /home/omega/omega/venv/bin/python /home/omega/omega/research/c542b_server.py

READ-ONLY. Every request is a GET to one of the addresses in ALLOW below; anything else raises before it is sent.
  1. Bybit (public): the USDT perpetuals, live tickers, and for the coins the test needs their funding history and
     daily closes from 2024-09-21 (Round 22's window plus ten days) to now.
  2. Binance (public): every perpetual's last settled rate, at the same moment as 3 and 4.
  3. Mudrex (only if data/api_keys.json has a "mudrex" section): its futures listing (GET /fapi/v1/futures), which
     carries each asset's funding_fee_perc. Nothing else is called with that key.
  4. CoinSwitch (only if data/api_keys.json has a "coinswitch" section): its futures instrument list and all-pairs
     ticker (signed GETs, Ed25519). Nothing else is called with that key.
Writes two files into the logs worktree (pushed by the hourly logs push, or at once by omega-logpush.sh):
  logs/c542b_bybit.json.gz   the Bybit history (no keys in it)
  logs/c542b_source.json     the one-moment rate comparison (no keys in it)
and prints a short summary. It never prints or writes a key.
"""
import os, json, gzip, time, urllib.parse, concurrent.futures as cf
import requests

HOME = os.environ.get('OMEGA_HOME', '/home/omega/omega')
KEYS = os.path.join(os.environ.get('OMEGA_BASE_PATH', os.path.join(HOME, 'data')), 'api_keys.json')
OUT = os.path.join(HOME, '.logpush', 'logs')
BY = 'https://api.bybit.com'
START_MS = 1727740800000 - 10 * 86400000                      # 2024-09-21 00:00 UTC
ALLOW = {BY + '/v5/market/instruments-info', BY + '/v5/market/tickers', BY + '/v5/market/funding/history',
         BY + '/v5/market/kline', 'https://fapi.binance.com/fapi/v1/premiumIndex',
         'https://www.binance.com/fapi/v1/premiumIndex', 'https://api.india.delta.exchange/v2/products',
         'https://api.coindcx.com/exchange/v1/derivatives/futures/data/active_instruments',
         'https://trade.mudrex.com/fapi/v1/futures', 'https://coinswitch.co/trade/api/v2/futures/instrument_info',
         'https://coinswitch.co/trade/api/v2/futures/all-pairs/ticker'}    # exact addresses; GET only
S = requests.Session()
S.headers['User-Agent'] = 'omega-c542b/1.0'


def get(url, params=None, headers=None, tries=4):
    if url not in ALLOW:
        raise RuntimeError('refused: not on the read-only list: ' + url)
    full = url + ('?' + urllib.parse.urlencode(params, doseq=True) if params else '')
    for k in range(tries):
        try:
            r = S.get(full, headers=headers or {}, timeout=30)
            if r.status_code == 429 or r.status_code >= 500:
                time.sleep(1.5 * (k + 1)); continue
            return r
        except requests.RequestException:
            time.sleep(1.5 * (k + 1))
    raise RuntimeError('no answer from ' + url)


def bybit(path, params):
    r = get(BY + path, params)
    try:
        d = r.json()
    except ValueError:
        raise RuntimeError(f"Bybit {path}: HTTP {r.status_code} {r.headers.get('content-type', '')} (not JSON)")
    if d.get('retCode') != 0:
        raise RuntimeError(f"Bybit {path}: {d.get('retCode')} {d.get('retMsg')}")
    return d['result']


def bybit_perps():
    out, cur = {}, None
    while True:
        p = dict(category='linear', limit=1000)
        if cur:
            p['cursor'] = cur
        res = bybit('/v5/market/instruments-info', p)
        for x in res['list']:
            if x.get('contractType') == 'LinearPerpetual' and x.get('quoteCoin') == 'USDT' and x.get('status') == 'Trading' \
                    and x['symbol'].endswith('USDT'):
                out[x['symbol'][:-4]] = dict(sym=x['symbol'], iv_min=int(x.get('fundingInterval') or 480),
                                             launch=int(x.get('launchTime') or 0))
        cur = res.get('nextPageCursor')
        if not cur:
            return out


def funding(sym):
    out, end = {}, int(time.time() * 1000)
    while end > START_MS:
        lst = bybit('/v5/market/funding/history', dict(category='linear', symbol=sym, endTime=end, limit=200))['list']
        if not lst:
            break
        for x in lst:
            out[int(x['fundingRateTimestamp'])] = float(x['fundingRate'])
        oldest = min(int(x['fundingRateTimestamp']) for x in lst)
        if oldest >= end or len(lst) < 200:
            break
        end = oldest - 1
    return sorted((t, v) for t, v in out.items() if t >= START_MS)


def daily(sym):
    lst = bybit('/v5/market/kline', dict(category='linear', symbol=sym, interval='D', start=START_MS,
                                         end=int(time.time() * 1000), limit=1000))['list']
    return sorted((int(x[0]) // 1000, float(x[4]), float(x[6])) for x in lst)


def keys():
    try:
        return json.load(open(KEYS))
    except Exception:
        return {}


def mudrex(sec):
    out, off = {}, 0
    h = {'X-Authentication': sec}
    while off < 2000:
        r = get('https://trade.mudrex.com/fapi/v1/futures', dict(offset=off, limit=100), h)
        if r.status_code != 200:
            return dict(error=f'HTTP {r.status_code} {r.headers.get("content-type", "")} {r.text[:120]}')
        d = r.json().get('data') or []
        for x in d:
            s = str(x.get('symbol') or '')
            if s.endswith('USDT'):
                out[s[:-4]] = dict(fr=x.get('funding_fee_perc'), nxt=x.get('funding_interval'),
                                   prev=x.get('previous_funding_interval'), price=x.get('price'),
                                   min_notional=x.get('min_notional_value'), max_lev=x.get('max_leverage'),
                                   cap=x.get('max_funding_rate'))
        if len(d) < 100:
            break
        off += 100
    return dict(assets=out)


def coinswitch(api_key, secret):
    try:
        from cryptography.hazmat.primitives.asymmetric import ed25519
    except Exception as e:
        return dict(error='the cryptography package is missing: ' + str(e)[:80])
    sk = secret.strip()
    if len(sk) == 128:                                         # seed + public key: the first half is the seed
        sk = sk[:64]
    try:
        priv = ed25519.Ed25519PrivateKey.from_private_bytes(bytes.fromhex(sk))
    except Exception:
        return dict(error='the CoinSwitch secret is not a 64-character hex Ed25519 key')

    def signed(path, params):
        dp = urllib.parse.unquote_plus(path + ('?' + urllib.parse.urlencode(params) if params else ''))
        ep = str(int(time.time() * 1000))
        sig = priv.sign(('GET' + dp + ep).encode()).hex()
        r = get('https://coinswitch.co' + path, params, {'Content-Type': 'application/json', 'X-AUTH-APIKEY': api_key.strip(),
                                                      'X-AUTH-SIGNATURE': sig, 'X-AUTH-EPOCH': ep})
        try:
            return r.status_code, r.json()
        except Exception:
            return r.status_code, {'text': r.text[:200]}
    out = {}
    st, inst = signed('/trade/api/v2/futures/instrument_info', None)
    out['instrument_info_status'] = st
    codes = {'EXCHANGE_2'}

    def walk(x):
        if isinstance(x, dict):
            for k, v in x.items():
                if isinstance(k, str) and k.startswith('EXCHANGE_'):
                    codes.add(k)
                if k == 'exchange' and isinstance(v, str) and v.startswith('EXCHANGE_'):
                    codes.add(v)
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
    walk(inst)
    out['exchanges'] = sorted(codes)
    out['instruments'] = {}
    for code in sorted(codes):
        st, d = signed('/trade/api/v2/futures/instrument_info', {'exchange': code})
        rows = (d or {}).get('data') or {}
        out['instruments'][code] = {s[:-4]: dict(taker=v.get('taker_fee_rate'), maker=v.get('maker_fee_rate'),
                                                 status=v.get('status'), min_qty=v.get('min_base_quantity'))
                                    for s, v in rows.items() if isinstance(v, dict) and s.endswith('USDT')} if st == 200 \
            else f'HTTP {st} {str(d)[:120]}'
    out['tickers'] = {}
    for code in sorted(codes):
        st, d = signed('/trade/api/v2/futures/all-pairs/ticker', {'exchange': code})
        rows = (d or {}).get('data') or {}
        out['tickers'][code] = {s[:-4]: dict(fr=v.get('funding_rate'), nxt=v.get('next_funding_timestamp'),
                                             mark=v.get('mark_price'), last=v.get('last_price'))
                                for s, v in rows.items() if isinstance(v, dict) and s.endswith('USDT')} if st == 200 \
            else f'HTTP {st} {str(d)[:120]}'
    return out


def share(a, b, tol=2e-5):
    common = [c for c in a if c in b and a[c] is not None and b[c] is not None]
    if not common:
        return 0, 0.0
    hit = sum(1 for c in common if abs(float(a[c]) - float(b[c])) <= tol)
    return len(common), hit / len(common)


def main():
    t0 = time.time()
    print('Round 22b server check (read-only)')
    try:
        by = bybit_perps()
        tick = {x['symbol'][:-4]: x for x in bybit('/v5/market/tickers', dict(category='linear'))['list'] if x['symbol'].endswith('USDT')}
        print(f'  Bybit: {len(by)} USDT perpetuals, tickers {len(tick)}')
    except Exception as e:
        by, tick = {}, {}
        print(f'  !! Bybit did not answer the server: {e} -- the venues are compared with Binance only, and no history is fetched')
    bn = []
    for u in ('https://fapi.binance.com/fapi/v1/premiumIndex', 'https://www.binance.com/fapi/v1/premiumIndex'):
        try:
            bn = get(u).json()
        except Exception:
            bn = []
        if isinstance(bn, list) and bn:
            break
    bn = bn if isinstance(bn, list) else []
    bn_last = {x['symbol'][:-4]: float(x['lastFundingRate']) for x in bn if x['symbol'].endswith('USDT')}
    dl = get('https://api.india.delta.exchange/v2/products', dict(contract_types='perpetual_futures', states='live')).json()['result']
    delta = {p['underlying_asset']['symbol'] for p in dl if (p.get('settling_asset') or {}).get('symbol') == 'USD'}
    try:
        dcx = get('https://api.coindcx.com/exchange/v1/derivatives/futures/data/active_instruments',
                  {'margin_currency_short_name[]': 'INR'}).json()
        dcx = {p.split('-', 1)[1].rsplit('_', 1)[0] for p in dcx if isinstance(p, str) and p.startswith('B-') and p.endswith('_USDT')}
    except Exception:
        dcx = set()
    k = keys()
    src = dict(at=int(time.time()), bybit_pred={c: float(x['fundingRate']) for c, x in tick.items() if x.get('fundingRate') not in (None, '')},
               bybit_next={c: int(x.get('nextFundingTime') or 0) for c, x in tick.items()},
               bybit_turnover={c: float(x.get('turnover24h') or 0) for c, x in tick.items()}, binance_last=bn_last,
               delta=sorted(delta), coindcx_inr=sorted(dcx))
    if 'mudrex' in k:
        try:
            src['mudrex'] = mudrex(k['mudrex'].get('api_secret') or k['mudrex'].get('api_key') or '')
        except Exception as e:
            src['mudrex'] = dict(error=str(e)[:200])
    else:
        src['mudrex'] = dict(error='no mudrex key saved')
    if 'coinswitch' in k:
        try:
            src['coinswitch'] = coinswitch(k['coinswitch'].get('api_key', ''), k['coinswitch'].get('api_secret', ''))
        except Exception as e:
            src['coinswitch'] = dict(error=str(e)[:200])
    else:
        src['coinswitch'] = dict(error='no coinswitch key saved')

    # the last settled Bybit rate, for the comparison (one request per coin of the venues read)
    venue_coins = set()
    if 'assets' in src['mudrex']:
        venue_coins |= set(src['mudrex']['assets'])
    for code, rows in (src['coinswitch'].get('tickers') or {}).items():
        if isinstance(rows, dict):
            venue_coins |= set(rows)
    venue_coins &= set(by)

    def last_settled(c):
        try:
            lst = bybit('/v5/market/funding/history', dict(category='linear', symbol=by[c]['sym'], limit=1))['list']
            return c, float(lst[0]['fundingRate']) if lst else None
        except Exception:
            return c, None
    with cf.ThreadPoolExecutor(6) as ex:
        src['bybit_last'] = dict(ex.map(last_settled, sorted(venue_coins)))

    summary = []
    if 'assets' in src['mudrex']:
        m = {c: v['fr'] for c, v in src['mudrex']['assets'].items()}
        for unit, f in (('as a fraction', 1.0), ('as a percent', 0.01)):
            mm = {c: (float(v) * f if v not in (None, '') else None) for c, v in m.items()}
            for ref, name in ((src['bybit_pred'], 'Bybit predicted'), (src['bybit_last'], 'Bybit last settled'),
                              (bn_last, 'Binance last settled')):
                n, s_ = share(mm, ref)
                summary.append(f'Mudrex ({unit}) vs {name}: {s_:.0%} of {n} coins within 0.002%')
        summary.append(f"Mudrex: {len(m)} coins; on Delta {len(set(m) & delta)}; on CoinDCX (INR) {len(set(m) & dcx)}")
    else:
        summary.append('Mudrex: ' + src['mudrex'].get('error', '?'))
    for code, rows in (src['coinswitch'].get('tickers') or {}).items():
        if not isinstance(rows, dict):
            summary.append(f'CoinSwitch {code}: {rows}'); continue
        cs = {c: (float(v['fr']) if v.get('fr') not in (None, '') else None) for c, v in rows.items()}
        for ref, name in ((src['bybit_pred'], 'Bybit predicted'), (src['bybit_last'], 'Bybit last settled'),
                          (bn_last, 'Binance last settled')):
            n, s_ = share(cs, ref)
            summary.append(f'CoinSwitch {code} vs {name}: {s_:.0%} of {n} coins within 0.002%')
        summary.append(f'CoinSwitch {code}: {len(cs)} coins; on Delta {len(set(cs) & delta)}; on CoinDCX (INR) {len(set(cs) & dcx)}')
    if 'error' in src['coinswitch']:
        summary.append('CoinSwitch: ' + src['coinswitch']['error'])
    src['summary'] = summary
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, 'c542b_source.json'), 'w') as h:
        json.dump(src, h)
    print('  one-moment rates saved: ' + os.path.join(OUT, 'c542b_source.json'))
    for s_ in summary:
        print('   ', s_)

    # the history: coins on Delta, plus coins on CoinDCX or Mudrex/CoinSwitch with Bybit turnover >= $0.5M a day
    census = os.path.join(HOME, 'research', 'c542b_census', 'mudrex_list_20261009.json')
    mlist = set(json.load(open(census))) if os.path.exists(census) else set()
    need = {c for c in by if c in delta}
    need |= {c for c in by if (c in dcx or c in mlist or c in venue_coins) and src['bybit_turnover'].get(c, 0) >= 5e5}
    if not need:
        print('  no Bybit history fetched'); return
    print(f'  fetching Bybit history for {len(need)} coins (funding since 2024-09-21 + daily closes)...', flush=True)
    hist = dict(fetched=int(time.time()), start_ms=START_MS, instruments={c: by[c] for c in need}, funding={}, daily={}, errors={})

    def one(c):
        try:
            return c, funding(by[c]['sym']), daily(by[c]['sym']), None
        except Exception as e:
            return c, None, None, str(e)[:120]
    done = 0
    with cf.ThreadPoolExecutor(6) as ex:
        for c, f, d, err in ex.map(one, sorted(need)):
            done += 1
            if err:
                hist['errors'][c] = err
            else:
                hist['funding'][c] = f; hist['daily'][c] = d
            if done % 50 == 0:
                print(f'    {done}/{len(need)}', flush=True)
    path = os.path.join(OUT, 'c542b_bybit.json.gz')
    with gzip.open(path, 'wt') as h:
        json.dump(hist, h)
    nrec = sum(len(v) for v in hist['funding'].values())
    print(f'  Bybit history saved: {path} ({len(hist["funding"])} coins, {nrec} settlements, {len(hist["errors"])} errors, '
          f'{os.path.getsize(path) / 1e6:.1f} MB) in {time.time() - t0:.0f} s')
    print('Done. The logs push (every hour at :17) sends both files; to send them now: '
          'sudo -u omega /usr/local/bin/omega-logpush.sh')


if __name__ == '__main__':
    main()
