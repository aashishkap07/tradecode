#!/usr/bin/env python3
"""C516: phase 1 of the move to Binance -- the paper book, the ledgers and the
shadow on Binance's public data, behind OMEGA_VENUE=binance (Bitget stays the
default).

Binance's futures API refuses this sandbox (HTTP 451), so the futures side is
tested against a simulated Binance whose replies follow Binance's documented
formats. Their column layout is checked against Binance's own archive
(data.binance.vision), and the spot side runs on Binance's real public data
(data-api.binance.vision). The live check on the operator's server is
deploy/omega_binance_check.py.

1. The venue setting, its fees and minimums; Bitget unchanged by default.
2. Real Binance data: the archive's kline columns and the day-close = 23:59-minute
   rule the C512 check relies on; the spot book (the api.binance.com -> data-api
   fallback included).
3. The book's inputs on Binance: marks, contract rules (steps, $50 BTC / $20 ETH
   minimums, status, underlying type), 330 days of candles in one call, every
   funding page, the C512 check, the funding interval.
4. A paper rebalance on Binance prices, rules and fees (0.05%).
5. A book built on one venue is never marked, traded or charged on the other.
6. No live trading on Binance in phase 1.
7. ccxt's Binance USDⓈ-M market table and the order-book bid/ask.
8. The shadow's hourly candles and taker flow; the carry ledger's spot prices and
   perp cost; the spot pot's 1% TDS on each sale.
9. The page (Chromium): the spot pot's fee and TDS.
"""
import os, io, re, json, time, glob, socket, types, zipfile, logging, contextlib, importlib.util, tempfile
import datetime as dt
import numpy as np
REPO = os.path.dirname(os.path.abspath(__file__))
BASE = tempfile.mkdtemp(prefix='c516_test_')
os.environ['OMEGA_BASE_PATH'] = BASE
TOKEN = 'c516-test-token-0123456789abcdef'
os.environ['OMEGA_CTRL_TOKEN'] = TOKEN
fails = []


def ok(n, c, d=''):
    print(f"  {'PASS' if c else 'FAIL'}  {n}" + (f"   {d}" if d else ''))
    if not c:
        fails.append(n)


spec = importlib.util.spec_from_file_location('om516', os.path.join(REPO, 'omega_v60_reconstructed.py'))
om = importlib.util.module_from_spec(spec)
with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
    spec.loader.exec_module(om)
LOG = []
class _H(logging.Handler):
    def emit(self, r): LOG.append((r.levelno, r.getMessage()))
lg = logging.getLogger('OmegaV60'); lg.handlers = [_H()]; lg.propagate = False
print("=" * 66); print("C516: PAPER ON BINANCE (PHASE 1)"); print("=" * 66)
DAY = 86400000
TODAY = int(time.time() * 1000) // DAY * DAY
YDAY = TODAY - DAY
SRC = open(os.path.join(REPO, 'omega_v60_reconstructed.py')).read()


def bn_cfg():
    c = om.Config(); c.PAPER_MODE = True; c.C380_MAX_MONTHLY_DD_PCT = 20.0; c.C488_ENGINE = 'portfolio'
    c.VENUE = 'binance'
    for k, v in om._C516_VENUE_DEFAULTS['binance'].items():
        setattr(c, k, v)
    return c


print("\n1. THE VENUE SETTING")
c0 = om.Config()
ok("Bitget stays the default (Config.VENUE 'bitget', fees 0.06% taker)", c0.VENUE == 'bitget'
   and om._c516_venue(c0) == 'bitget' and abs(c0.TAKER_FEE_PCT - 0.06) < 1e-12)
cb = bn_cfg()
ok("OMEGA_VENUE=binance: taker 0.05%, maker 0.02% (Binance FAQ), spot 0.10%, TDS 1%, spot minimum $5, "
   "Savings 6.8% (USDT Flexible, the operator's app)",
   om._c516_venue(cb) == 'binance' and cb.TAKER_FEE_PCT == 0.05 and cb.MAKER_FEE_PCT == 0.02
   and cb.C501_SPOT_FEE == 0.001 and cb.C501_SPOT_TDS == 0.01 and cb.C502_SPOT_MIN_ORDER == 5.0
   and cb.C501_SAVINGS_APR == 0.068 and om.Config().C501_SAVINGS_APR == 0.0763)
x = om.Config(); x.VENUE = 'kraken'
ok("an unknown venue name falls back to Bitget", om._c516_venue(x) == 'bitget')
ok("main() reads OMEGA_VENUE and applies the venue's defaults before the bot is built",
   SRC.index("os.environ.get('OMEGA_VENUE'") < SRC.index("    bot = TradingBot(cfg)\n    if fresh:"))

print("\n2. REAL BINANCE DATA")
try:
    import requests
    arc = 'https://data.binance.vision/data/futures/um/daily/klines/{s}/{i}/{s}-{i}-{d}.zip'
    day = (dt.datetime.utcnow() - dt.timedelta(days=3)).strftime('%Y-%m-%d')
    got = {}
    for sym in ('BTCUSDT', '1000PEPEUSDT'):
        rows = {}
        for iv in ('1d', '1m'):
            z = zipfile.ZipFile(io.BytesIO(requests.get(arc.format(s=sym, i=iv, d=day), timeout=30).content))
            rows[iv] = z.read(z.namelist()[0]).decode().strip().split('\n')
        got[sym] = rows
    hdr = got['BTCUSDT']['1d'][0].split(',')
    ok("Binance's own archive: column 7 is quote volume, 9 taker-buy base volume, 5 volume (what the code reads)",
       hdr[4] == 'close' and hdr[5] == 'volume' and hdr[7] == 'quote_volume' and hdr[9] == 'taker_buy_volume', str(hdr))
    for sym in got:
        d1 = got[sym]['1d'][1].split(','); m1 = got[sym]['1m'][-1].split(',')
        ok(f"  {sym} {day}: the day's close = its 23:59 minute's close ({d1[4]} = {m1[4]}), the C512 rule on Binance",
           d1[4] == m1[4] and int(m1[0]) == int(d1[0]) + DAY - 60000)
except Exception as e:
    ok(f"Binance archive reachable ({type(e).__name__}: {e})", False)
bk = om._c516_bn_spot_book(tries=2)
ok(f"Binance spot bid/ask, live ({len(bk)} pairs; api.binance.com refuses this sandbox, data-api.binance.vision answers)",
   len(bk) > 300 and 'BTCUSDT' in bk and 0 < bk['BTCUSDT'][0] < bk['BTCUSDT'][1], str(bk.get('BTCUSDT')))
r_ = om._c516_bn_get('https://fapi.binance.com', '/fapi/v1/time', {}, 1)
ok("  a refused host (fapi gives this sandbox 451) reads as None, not an exception", r_ is None or 'serverTime' in r_, str(r_))


# ── a simulated Binance USDⓈ-M, in Binance's documented reply formats ─────────
class FakeBinance:
    def __init__(s, n_days=400, fund_rows=None, minute_close=None, fail=(), bad_day=None):
        s.n_days, s.fund_rows, s.minute_close, s.fail, s.bad_day = n_days, fund_rows, minute_close, set(fail), bad_day
        s.calls = []
        # the busiest first: four non-crypto perps as Binance lists them on 30 Sep 2026 (no isRwa flag;
        # ABC stands for a listing newer than the research's name list, caught by its TradFi tag)
        s.coins = {'SOXLUSDT': 38.2, 'CLUSDT': 72.4, 'SKHYNIXUSDT': 180.0, 'ABCUSDT': 12.0, 'STKUSDT': 55.0,
                   'BTCUSDT': 83461.0, 'ETHUSDT': 4100.0, '1000PEPEUSDT': 0.004211, 'ZECUSDT': 1482.85,
                   'HYPEUSDT': 41.2, 'SUIUSDT': 3.3}
        for k in range(60):                   # Binance lists ~500; the bot refuses a table under 50
            s.coins[f"C{k:02d}USDT"] = 1.0 + k

    def px(s, sym, t):
        base = s.coins[sym]
        k = (TODAY - t // DAY * DAY) // DAY          # every candle of one UTC day shares that day's close
        return base * (1 + 0.004 * np.sin(k / 3.0 + len(sym)) + 0.0006 * k * (1 if hash(sym) % 2 else -1))

    def kline(s, sym, t, iv_ms):
        c = s.px(sym, t)
        v = 1000.0 + (t // iv_ms) % 97
        sh = 0.5 + 0.1 * np.sin(t / 3.6e6 / 7.0 + len(sym))     # the taker-buy share moves, as it does
        return [t, f"{c * 0.99:.8g}", f"{c * 1.02:.8g}", f"{c * 0.97:.8g}", f"{c:.8g}", f"{v:.3f}", t + iv_ms - 1,
                f"{v * c:.4f}", 1234, f"{v * sh:.3f}", f"{v * sh * c:.4f}", "0"]

    def __call__(s, base, path, params, tries=3):
        s.calls.append((path, dict(params)))
        if path in s.fail:
            return None
        coins = list(s.coins)
        if path == '/fapi/v1/ticker/bookTicker':
            return [dict(symbol=c, bidPrice=f"{s.coins[c] * 0.9999:.8g}", bidQty="10", askPrice=f"{s.coins[c] * 1.0001:.8g}",
                         askQty="10", time=1) for c in coins] + [dict(symbol='BTCUSDT_261225', bidPrice='84000', askPrice='84010')]
        if path == '/fapi/v1/ticker/24hr':
            return [dict(symbol=c, lastPrice=f"{s.coins[c]:.8g}", quoteVolume=f"{1e9 / (1 + i):.2f}") for i, c in enumerate(coins)]
        if path == '/fapi/v1/premiumIndex':
            return [dict(symbol=c, markPrice=f"{s.coins[c]:.8g}", lastFundingRate='0.00010000',
                         nextFundingTime=TODAY + DAY) for c in coins]
        if path == '/fapi/v1/exchangeInfo':
            def one(c, notional='5', step='1', typ='COIN', status='TRADING', ctype='PERPETUAL', base=None,
                    delivery=4133404800000, sub=()):
                return dict(symbol=c, pair=c.split('_')[0], contractType=ctype, status=status,
                            baseAsset=base or c[:-4], quoteAsset='USDT', deliveryDate=delivery,
                            marginAsset='USDT', underlyingType=typ, underlyingSubType=list(sub),
                            filters=[dict(filterType='PRICE_FILTER', tickSize='0.0001', minPrice='0.0001', maxPrice='1000000'),
                                     dict(filterType='LOT_SIZE', stepSize=step, minQty=step, maxQty='1000000'),
                                     dict(filterType='MARKET_LOT_SIZE', stepSize=step, minQty=step, maxQty='120000'),
                                     dict(filterType='MIN_NOTIONAL', notional=notional)])
            sy = [one('SOXLUSDT', '5', '0.01'), one('CLUSDT', '5', '0.01'), one('SKHYNIXUSDT', '5', '0.01'),
                  one('ABCUSDT', '5', '0.1', sub=('TradFi',)), one('STKUSDT', ctype='TRADIFI_PERPETUAL'),
                  one('BTCUSDT', '50', '0.001'), one('ETHUSDT', '20', '0.001'), one('1000PEPEUSDT', '5', '1'),
                  one('ZECUSDT', '5', '0.001'), one('HYPEUSDT', '5', '0.01'), one('SUIUSDT', '5', '0.1')]
            sy += [one(f"C{k:02d}USDT", '5', '0.1') for k in range(60)]
            sy += [one('BTCDOMUSDT', typ='INDEX'), one('XYZUSDT', status='SETTLING'),
                   one('BTCUSDT_261225', ctype='CURRENT_QUARTER', base='BTC', delivery=1798185600000),
                  one('NEWUSDT', typ='PREMARKET')]
            return dict(timezone='UTC', symbols=sy)
        if path == '/fapi/v1/klines':
            sym, iv = params['symbol'], params['interval']
            ms = {'1d': DAY, '1h': 3600000, '1m': 60000}[iv]
            st = int(params['startTime'])
            now = int(time.time() * 1000)
            out = []
            t = max(st // ms * ms, (TODAY - s.n_days * DAY) // ms * ms)
            while t <= now and len(out) < int(params.get('limit', 500)):
                out.append(s.kline(sym, t, ms))
                t += ms
            if iv == '1m' and s.minute_close is not None:
                for r in out:
                    r[4] = f"{s.minute_close:.8g}"
            if iv == '1d' and s.bad_day is not None:
                for r in out:
                    if r[0] == YDAY:
                        r[4] = f"{s.bad_day:.8g}"
            return out
        if path == '/fapi/v1/fundingRate':
            st = int(params['startTime'])
            iv = 4 if params['symbol'] == 'HYPEUSDT' else 8
            rows, t = [], st // 3600000 * 3600000
            while t < int(time.time() * 1000) and len(rows) < int(params['limit']):
                if t % (iv * 3600000) == 0:
                    rows.append(dict(symbol=params['symbol'], fundingTime=t + 3,
                                     fundingRate=f"{0.0001 * (1 + 0.5 * np.sin(t / 2.88e7)):.8f}", markPrice='1'))
                t += 3600000
            return rows[:s.fund_rows] if s.fund_rows is not None else rows
        if path == '/fapi/v1/fundingInfo':
            return [dict(symbol='HYPEUSDT', adjustedFundingRateCap='0.02', adjustedFundingRateFloor='-0.02',
                         fundingIntervalHours=4, disclaimer=False)]
        return None


def mk(fake):
    cfg = bn_cfg(); om._c467_cfg_ref[0] = cfg
    pf = om.Portfolio(cfg); pf.equity = pf.available_balance = 500.0
    bot = types.SimpleNamespace(cfg=cfg, portfolio=pf, _c462_state_settled=True, _c408_asset_class=lambda s: 'crypto',
                                exchange=types.SimpleNamespace(markets={}, get_current_price=lambda s: None),
                                _c482_risk_guard=lambda: {'pct': 20.0, 'month_eq0': 500.0})
    om._c516_bn_get = fake
    e = om.C488Engine(bot); e.reset(); bot.c488 = e; pf._c488 = e
    bot.c501k = om.C501Allostatic(bot); bot.c501k.reset()
    bot.c510t = om.C510Tournament(bot); bot.c510t.reset()
    return bot, e


REAL_GET = om._c516_bn_get
print("\n3. THE BOOK'S INPUTS ON BINANCE")
fk = FakeBinance(); bot, e = mk(fk)
ok("the engine knows its venue", e.venue == 'binance')
ok("marks: every USDT perpetual (bid, ask, last, funding, 24 h quote volume); dated futures left out",
   e.refresh_marks(force=True) and 'BTC/USDT:USDT' in e.marks and '1000PEPE/USDT:USDT' in e.marks
   and not any('_' in k for k in e.marks) and e.marks['BTC/USDT:USDT']['fr'] == 0.0001
   and e.marks['BTC/USDT:USDT']['bid'] < e.marks['BTC/USDT:USDT']['ask'] and e.marks['BTC/USDT:USDT']['vol'] > 0)
old = dict(e.marks['BTC/USDT:USDT'])
fk.fail = {'/fapi/v1/premiumIndex'}; e.refresh_marks(force=True); fk.fail = set()
ok("  premiumIndex failing keeps the last funding rate (never a silent 0)", e.marks['BTC/USDT:USDT']['fr'] == old['fr'])
ok("rules: BTC step 0.001 / $50 minimum, ETH $20, PEPE per 1000 coins, TRADING = 'normal'",
   e.refresh_rules(force=True) and e._step('BTC/USDT:USDT') == (0.001, 0.001) and e._min_usdt('BTC/USDT:USDT') == 50.0
   and e._min_usdt('ETH/USDT:USDT') == 20.0 and e._step('1000PEPE/USDT:USDT')[0] == 1.0
   and e.rules['BTC/USDT:USDT']['status'] == 'normal' and e.rules['BTC/USDT:USDT']['max_mkt'] == 120000.0)
ok("  a SETTLING contract takes no new position; the quarterly future is not a perpetual",
   not e._tradable('XYZ/USDT:USDT', False) and e._tradable('XYZ/USDT:USDT', True) is False
   and 'BTC_261225/USDT:USDT' not in e.rules and 'BTCUSDT_261225' not in str(list(e.rules)))
ok("  INDEX (BTCDOM) and PREMARKET underlyings are not crypto coins for the book",
   not e._is_crypto('BTCDOM/USDT:USDT') and not e._is_crypto('NEW/USDT:USDT') and e._is_crypto('ZEC/USDT:USDT'))
ok("  stock, ETF and commodity perps (SOXL, CL, SKHYNIX: the research's list) are not crypto, though Binance calls them COIN",
   not any(e._is_crypto(f"{b}/USDT:USDT") for b in ('SOXL', 'CL', 'SKHYNIX')) and e.rules['SOXL/USDT:USDT']['kind'] == 'COIN')
ok("  a quoted contract that is not a USDT-margined PERPETUAL (STK, another contract type) is never a candidate",
   'STK/USDT:USDT' in e.marks and 'STK/USDT:USDT' not in e.rules and not e._is_crypto('STK/USDT:USDT'))
ok("  and a newer listing tagged TradFi by Binance (underlyingSubType) is left out too",
   not e._is_crypto('ABC/USDT:USDT') and e.rules['ABC/USDT:USDT']['sub'] == 'TradFi')
import sys
sys.path.insert(0, os.path.join(REPO, 'research'))
from omega_c493_research import TRADFI as RESEARCH_TRADFI
ok("  the bot's list is the research's list, name for name (62)",
   om._C516_TRADFI == {x[:-4] for x in RESEARCH_TRADFI} and len(om._C516_TRADFI) == 62)
fk.calls.clear()
c, f = e._history('ZEC/USDT:USDT')
kl = [p for p, q in fk.calls if p == '/fapi/v1/klines']
ok("330 days of daily candles in ONE call (limit 332), today's unfinished day left out",
   len(kl) == 2 and max(c) == YDAY and TODAY not in c and len(c) == 330, f"{len(kl)} kline calls, {len(c)} days")
row = fk.kline('ZECUSDT', YDAY, DAY)
ok("  each day is (close, QUOTE volume, open, high, low), from columns 4, 7, 1, 2, 3",
   c[YDAY] == (float(row[4]), float(row[7]), float(row[1]), float(row[2]), float(row[3])), str(c[YDAY]))
ok("  funding: 200 days of settlements (8-hourly: ~600 records), at their own rates",
   590 <= len(f) <= 610 and all(0.00005 <= v <= 0.00015 for v in f.values()) and len(set(f.values())) > 10, str(len(f)))
fk2 = FakeBinance(); bot2, e2 = mk(fk2)
fk2.calls.clear(); c2, f2 = e2._history('HYPE/USDT:USDT', days=330)
fr = [q for p, q in fk2.calls if p == '/fapi/v1/fundingRate']
ok("  a 4-hourly coin pages forward: 1000 records, then the rest (1,200 in all, 2 calls)",
   len(fr) == 2 and 1190 <= len(f2) <= 1210 and fr[1]['startTime'] > fr[0]['startTime'], f"{len(fr)} calls, {len(f2)} records")
for lab, fkx, want in (("the daily candles do not load", FakeBinance(fail={'/fapi/v1/klines'}), 'daily candles did not load'),
                       ("funding does not load", FakeBinance(fail={'/fapi/v1/fundingRate'}), 'funding did not load'),
                       ("the just-finished day's close differs from its 23:59 minute (C512)",
                        FakeBinance(bad_day=1500.0), 'daily close not final')):
    b3, e3 = mk(fkx)
    try:
        e3._history('ZEC/USDT:USDT'); msg = ''
    except RuntimeError as x:
        msg = str(x)
    ok(f"C499/C512 on Binance -- {lab}: the load raises and the rebalance waits 10 min", want in msg, msg)
ok("funding interval: 4 h where fundingInfo lists it (HYPE), Binance's default 8 h elsewhere",
   e._bn_fund_interval('HYPE/USDT:USDT') == 4 and e._bn_fund_interval('ZEC/USDT:USDT') == 8)

print("\n4. A PAPER REBALANCE ON BINANCE PRICES, RULES AND FEES")


class PaperEx:
    """ExchangeManager's paper contract: a market order fills at the ask (buy) or bid (sell)"""
    def __init__(s, e):
        s.e, s.markets, s.orders = e, {k: {} for k in e.rules}, []
    def place_order(s, sym, side, q, lev, typ, reduce_only=False, **kw):
        m = s.e.marks[sym]; px = m['ask'] if side == 'buy' else m['bid']
        s.orders.append((sym, side, q, px)); return {'id': 'p', 'price': px, 'filled': q, 'status': 'closed'}
    def c487_settle(s, sym, o, side, price, size, wait):
        return float(o['filled']), float(o['price']), 'filled'
    def get_current_price(s, sym):
        return None


fk5 = FakeBinance(); b5, e5 = mk(fk5)
e5.refresh_rules(force=True); e5.refresh_marks(force=True)
b5.exchange = PaperEx(e5)
cand5 = e5.candidates(20)
ok("the busiest perps on Binance are the four non-crypto ones, and none is a candidate",
   [k.split('/')[0] for k in sorted(e5.marks, key=lambda k: -e5.marks[k]['vol'])[:5]] == ['SOXL', 'CL', 'SKHYNIX', 'ABC', 'STK']
   and not any(c.split('/')[0] in ('SOXL', 'CL', 'SKHYNIX', 'ABC', 'STK') for c in cand5), str([c.split('/')[0] for c in cand5[:6]]))
LOG.clear()
e5.rebalance('first')
ords = b5.exchange.orders
ok("  and none is in the plan or the book", not any(s_.split('/')[0] in ('SOXL', 'CL', 'SKHYNIX', 'ABC')
                                                   for s_ in list(e5.plan) + list(e5.book)))
ok(f"the first rebalance trades on Binance prices ({len(ords)} fills), all at the book's side of the spread",
   len(ords) > 0 and all(px == (e5.marks[s_]['ask'] if sd == 'buy' else e5.marks[s_]['bid']) for s_, sd, q, px in ords))
ok("  every quantity is a whole Binance step, and every opening order meets its minimum ($50 BTC, $20 ETH)",
   all(abs(q / e5._step(s_)[0] - round(q / e5._step(s_)[0])) < 1e-6 and q * px >= e5._min_usdt(s_) for s_, sd, q, px in ords),
   str([(s_.split('/')[0], q, round(q * px, 2)) for s_, sd, q, px in ords][:6]))
fees = sum(p['fees'] for p in e5.book.values()); notional = sum(q * px for s_, sd, q, px in ords)
ok(f"  fees at Binance's 0.05% taker: ${fees:.4f} on ${notional:.2f}", abs(fees - 0.0005 * notional) < 1e-9)
ok("  the saved book says it is a Binance book", json.load(open(e5.path)).get('venue') == 'binance')
e5.fund_next = {s_: int(time.time() * 1000) - 1000 for s_ in e5.book}
f0 = {s_: p['funding'] for s_, p in e5.book.items()}
e5.accrue_funding()
paid = {s_: e5.book[s_]['funding'] - f0[s_] for s_ in e5.book}
ok("paper funding on Binance's own schedule: each position settled once, at its mark and the premiumIndex rate",
   all(abs(paid[s_] - (-e5.book[s_]['qty'] * e5.mark(s_) * 0.0001)) < 1e-12 for s_ in e5.book), str(list(paid.values())[:3]))

print("\n5. ONE VENUE'S BOOK IS NEVER MARKED OR TRADED ON THE OTHER'S PRICES")
p = os.path.join(om.BASE_PATH, 'c488_book.json')
json.dump(dict(book={'PEPE/USDT:USDT': dict(qty=-1655000.0, avg=4.26e-06, fees=0.004, funding=0.0, realized=0.0,
                                             opened=time.time())}, last_rebal='2026-09-30'), open(p, 'w'))
LOG.clear(); fk6 = FakeBinance(); om._c516_bn_get = fk6
cfg6 = bn_cfg(); pf6 = om.Portfolio(cfg6); pf6.equity = 249.93
b6 = types.SimpleNamespace(cfg=cfg6, portfolio=pf6, _c462_state_settled=True, _c408_asset_class=lambda s: 'crypto',
                           exchange=PaperEx.__new__(PaperEx), _c482_risk_guard=lambda: {'pct': 20.0, 'month_eq0': 250.0})
e6 = om.C488Engine(b6); b6.c488 = e6
ok("an old Bitget book (no 'venue' saved) loaded on Binance is blocked, and says how to switch",
   e6.venue_block and 'Bitget positions' in e6.venue_block and 'FRESH_START' in e6.venue_block
   and any('C516' in m and 'start fresh' in m for lv, m in LOG), e6.venue_block)
e6.due = lambda: True; fk6.calls.clear(); e6._tick_at = 0; e6.tick()
ok("  its tick trades nothing, reads nothing, books no funding; its open P&L counts as 0, not Binance-priced",
   not fk6.calls and e6.unrealized() == 0.0 and e6.book['PEPE/USDT:USDT']['funding'] == 0.0)
e6.save()
ok("  and a save keeps the book labelled as Bitget's", json.load(open(p)).get('venue') == 'bitget')
e6.reset()
ok("a fresh start clears it: flat, labelled Binance", not e6.venue_block and not e6.book
   and json.load(open(p)).get('venue') == 'binance')
d6 = json.load(open(p)); d6['book'] = {'1000PEPE/USDT:USDT': dict(qty=-1655.0, avg=0.00421, fees=0.004, funding=0.0,
                                                                  realized=0.0, opened=time.time())}
json.dump(d6, open(p, 'w'))
cfgb = om.Config(); cfgb.PAPER_MODE = True
eb = om.C488Engine(types.SimpleNamespace(cfg=cfgb, portfolio=pf6, _c462_state_settled=True))
ok("  and a Binance book loaded by a Bitget run is blocked the same way", 'Binance positions' in eb.venue_block
   and 'reads Bitget' in eb.venue_block, eb.venue_block)

print("\n6. NO LIVE TRADING ON BINANCE IN PHASE 1")
cfgL = bn_cfg(); cfgL.PAPER_MODE = False; cfgL.C488_LIVE_OK = True
eL = om.C488Engine(types.SimpleNamespace(cfg=cfgL, portfolio=pf6, _c462_state_settled=True, exchange=None))
LOG.clear()
ok("live on Binance (even with C488_LIVE_OK = True): not ready, and it says the order path is not built",
   eL.live_ready() is False and 'phase 2' in eL.live.get('why', '') and any('phase 2' in m for lv, m in LOG))

cfgX = bn_cfg(); cfgX.PAPER_MODE = False
LOG.clear()
ok("  and live mode on Binance does not even connect: 'LIVE mode on Binance is not built (phase 2)'",
   om.ExchangeManager(cfgX).connect() is False and any('not built (phase 2)' in m for lv, m in LOG))

print("\n7. CCXT'S BINANCE USDⓈ-M TABLE AND THE ORDER-BOOK BID/ASK")
import ccxt
EXI = FakeBinance()(None, '/fapi/v1/exchangeInfo', {})
for x in EXI['symbols']:
    x.setdefault('onboardDate', 1569398400000); x.setdefault('deliveryDate', 4133404800000)
    x.setdefault('pricePrecision', 4); x.setdefault('quantityPrecision', 3); x.setdefault('orderTypes', ['LIMIT', 'MARKET'])
    x.setdefault('timeInForce', ['GTC']); x.setdefault('liquidationFee', '0.0125'); x.setdefault('marketTakeBound', '0.05')
orig_bn = ccxt.binanceusdm


class PatchedUSDM(orig_bn):
    def fapiPublicGetExchangeInfo(self, params={}):
        return EXI
    def fetch_currencies(self, params={}):
        return {}
    def fetch_ticker(self, symbol, params={}):
        return {'symbol': symbol, 'last': 83461.0, 'bid': None, 'ask': None}
    def fetch_order_book(self, symbol, limit=None, params={}):
        return {'bids': [[83460.9, 1.0]], 'asks': [[83461.1, 2.0]]}


ccxt.binanceusdm = PatchedUSDM
try:
    cfg7 = bn_cfg(); em = om.ExchangeManager(cfg7)
    LOG.clear()
    ok_c = em.connect()
    mk7 = em.markets.get('BTC/USDT:USDT') or {}
    ok(f"connect() on Binance: ccxt binanceusdm, {len(em.markets)} USDT perpetuals, the quarterly left out",
       ok_c and type(em.exchange).__name__ == 'PatchedUSDM' and 'BTC/USDT:USDT' in em.markets
       and '1000PEPE/USDT:USDT' in em.markets and not any('-' in k.split(':')[-1] or '_' in k for k in em.markets)
       and any(k.startswith('BTC/USDT:USDT-') for k in em.exchange.markets), str(sorted(em.markets)[:5]))
    ok("  ccxt reads the same step and minimum the book uses (0.001 BTC, $50)",
       float(mk7['precision']['amount']) == 0.001 and float(mk7['limits']['cost']['min']) == 50.0,
       f"{mk7.get('precision')} {mk7.get('limits', {}).get('cost')}")
    ok("  the log says Binance: 'Binance Fees: Maker 0.02% | Taker 0.05%'",
       any('Binance Fees: Maker 0.02% | Taker 0.05%' in m for lv, m in LOG), str([m for lv, m in LOG][:4]))
    b_, a_, src_ = em.get_bid_ask('BTC/USDT:USDT')
    ok("  a ticker without bid/ask (Binance futures') takes them from the order book, not a modelled spread",
       (b_, a_, src_) == (83460.9, 83461.1, 'book'), str((b_, a_, src_)))
finally:
    ccxt.binanceusdm = orig_bn

print("\n8. THE SHADOW, THE CARRY LEDGER AND THE SPOT POT")
fk8 = FakeBinance(); b8, e8 = mk(fk8)
sh = om.C489Shadow(b8)
raw_, got, flow, fund = sh._pull('ZECUSDT', 200)
now_h = int(time.time() * 1000) // 3600000 * 3600000
k0 = max(got); r0 = fk8.kline('ZECUSDT', k0, 3600000)
ok("the shadow's hours from Binance 1-hour candles (open, high, low, close, quote volume); the running hour left out",
   now_h not in got and k0 == now_h - 3600000 and got[k0] == [float(r0[1]), float(r0[2]), float(r0[3]), float(r0[4]),
                                                               float(r0[7])] and len(got) >= 199)
ok("  taker flow = taker-buy volume / volume for EVERY hour (Bitget served 30 h): the full model's input from day one",
   len(flow) == len(got) and abs(flow[k0] - float(r0[9]) / float(r0[5])) < 1e-12 and 0.3 < flow[k0] < 0.7 and len(fund) > 0)
car = om.C490Carry(b8)
om._c516_bn_spot_book = lambda tries=3: {'ZECUSDT': (1480.0, 1482.0), 'PEPEUSDT': (4.2e-06, 4.22e-06)}
sp_ = car.spot_prices()
ok("the carry ledger's spot prices are Binance spot mids; 1000PEPE's spot pair is PEPEUSDT",
   sp_ == {'ZECUSDT': 1481.0, 'PEPEUSDT': 4.21e-06} and om.C490Carry.spot_of('1000PEPEUSDT', sp_) == 'PEPEUSDT')
ok("  its perp leg costs Binance's 0.05% + 0.02% half-spread (0.07%); Bitget's stays 0.08%",
   abs(om._c516_perp_cost(b8.cfg) - 0.0007) < 1e-12 and om._c516_perp_cost(om.Config()) == 0.0008)
spot = om.C501Spot(b8); spot.reset()
spot.bk, spot._book_at = {'ZECUSDT': (1480.0, 1482.0)}, time.time()
spot.cash, spot.start_equity, spot.eq_last = 150.0, 250.0, 250.0
spot.pos = {'ZECUSDT': dict(qty=0.0675, avg=1400.0, opened=time.time() - 86400, realised=0.0)}
spot.book = lambda force=False: spot.bk
T5 = np.array([TODAY - k * DAY for k in range(200, 0, -1)], dtype=np.int64)
e8._last_M = (dt.datetime.utcnow().strftime('%Y-%m-%d'), 20,
              (T5, ['ZEC/USDT:USDT'], np.full((200, 1), 1480.0), np.full((200, 1), 1e9), np.zeros((200, 1))))
orig_t = om._c501_s1_targets
om._c501_s1_targets = lambda *a, **k: (np.zeros(1), None)
try:
    cash0 = spot.cash; spot.run()
finally:
    om._c501_s1_targets = orig_t
val = 0.0675 * 1480.0
ok(f"the spot pot's sale pays 0.10% fee AND 1% TDS: ${val:.2f} sold -> cash +${val * (1 - 0.001) - val * 0.01:.2f}",
   abs(spot.cash - cash0 - (val * 0.999 - val * 0.01)) < 1e-9 and abs(spot.tds - val * 0.01) < 1e-9 and not spot.pos,
   f"{spot.cash - cash0:.4f} tds {spot.tds:.4f}")
st_ = spot.status()
ok("  the status names the venue, the fee and the TDS withheld",
   st_['venue'] == 'Binance' and st_['fee_pct'] == 0.1 and st_['tds_pct'] == 1.0 and st_['tds'] > 0)
spot.save(); sp2 = om.C501Spot(b8)
ok("  TDS survives a restart", abs(sp2.tds - spot.tds) < 1e-9)
b9 = types.SimpleNamespace(cfg=om.Config(), c488=None)
ok("  and on Bitget there is no TDS line (0%)", om.C501Spot(b9).status().get('tds_pct') == 0.0)

print("\n9. THE PAGE (Chromium)")


def free_port():
    s_ = socket.socket(); s_.bind(('127.0.0.1', 0)); p_ = s_.getsockname()[1]; s_.close(); return p_


om._c516_bn_get = REAL_GET
cfgP = bn_cfg(); om._c467_cfg_ref[0] = cfgP
pfP = om.Portfolio(cfgP); pfP.equity = pfP.available_balance = 500.0; pfP.session_start_equity = 500.0
pfP.positions = om.PositionsManager()
bP = types.SimpleNamespace(cfg=cfgP, portfolio=pfP, _c462_state_settled=True, _c408_asset_class=lambda s: 'crypto',
                           exchange=types.SimpleNamespace(markets={}, get_current_price=lambda s: None),
                           _c482_risk_guard=lambda: {'pct': 20.0, 'month_eq0': 500.0, 'month_budget': 100.0,
                                                     'month_used': 0.0, 'day_cap': 25.0, 'day_used': 0.0, 'halt': ''})
eP = om.C488Engine(bP); eP.reset(); bP.c488 = eP; pfP._c488 = eP
bP.c489 = om.C489Shadow(bP); bP.c490 = om.C490Carry(bP)
bP.c501s = sp2; sp2.bot = bP; bP.c501v = om.C501Savings(bP); bP.c501k = om.C501Allostatic(bP); bP.c510t = om.C510Tournament(bP)
bP._c504_data_health = lambda now=None: {'ok': True, 'bits': [], 'late': [], 'keys': []}
fbot = types.SimpleNamespace(cfg=cfgP, portfolio=pfP, c488=eP, c501s=sp2, c501v=bP.c501v, c501k=bP.c501k,
                             c489=bP.c489, c490=bP.c490, c510t=bP.c510t,
                             mode_mgr=types.SimpleNamespace(mode=types.SimpleNamespace(value='normal')),
                             exchange=bP.exchange,
                             _c467_day_barrier=lambda: {'pnl': 0.0, 'limit': 9.0, 'used': 0.0, 'frac': 0.0},
                             _c482_risk_guard=bP._c482_risk_guard, _c504_data_health=bP._c504_data_health)
sp2.bk = {'ZECUSDT': (1480.0, 1482.0)}; sp2._book_at = time.time() + 1e6
port = free_port(); om.RemoteControl(fbot, port=port).start(); time.sleep(0.6)
try:
    from playwright.sync_api import sync_playwright
    exe = (glob.glob('/opt/pw-browsers/chromium-*/chrome-linux/chrome') or [None])[0]
    with sync_playwright() as pw:
        br = pw.chromium.launch(executable_path=exe) if exe else pw.chromium.launch()
        pg = br.new_page(viewport={'width': 412, 'height': 900}); errs = []
        pg.on('pageerror', lambda x: errs.append(str(x)))
        pg.goto(f'http://127.0.0.1:{port}/?t={TOKEN}'); pg.wait_for_timeout(3000)
        spt = pg.inner_text('#spotpot')
        br.close()
    ok("the spot pot says 'fees 0.10% · 1% TDS on each sale (India)' and 'TDS withheld $1.00 (creditable against your tax)'",
       'fees 0.10%' in spt and '1% TDS on each sale (India)' in spt and 'TDS withheld $1.00' in spt
       and 'BGB' not in spt, spt[:300])
    ok("no JavaScript errors", not errs, str(errs))
except ImportError:
    ok("Chromium/playwright available for the page check", False)
ok("version C516 or later", int(om._OMEGA_VERSION[1:4]) >= 516)
print("\n" + "=" * 66)
print("ALL CHECKS PASSED" if not fails else f"{len(fails)} FAILURE(S): {fails}")
os._exit(1 if fails else 0)
