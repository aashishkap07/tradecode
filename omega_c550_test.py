#!/usr/bin/env python3
"""C550 (B2): the two-exchange order path, DRY -- the 26 tests pre-registered in reports/2026-11-15_b2_preregistration.md
(pushed before the code). Every exchange here is mocked: the dry run uses the bot's own in-memory exchange (_C550Sim),
and the "live" tests route _C550_HTTP to two more _C550Sim instances. No real request is ever made: the real network
functions are replaced by ones that raise.
"""
import os, io, sys, json, time, copy, types, logging, tempfile, contextlib, importlib.util
REPO = os.path.dirname(os.path.abspath(__file__))
BASE = tempfile.mkdtemp(prefix='c550_test_')
os.environ['OMEGA_BASE_PATH'] = BASE
os.environ['OMEGA_CTRL_TOKEN'] = 'c550-test-token-0123456789abcdef'
fails = []


def ok(n, c, d=''):
    print(f"  {'PASS' if c else 'FAIL'}  {n}" + (f"   {d}" if d else ''))
    if not c:
        fails.append(n)


spec = importlib.util.spec_from_file_location('om550', os.path.join(REPO, 'omega_v60_reconstructed.py'))
om = importlib.util.module_from_spec(spec)
with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
    spec.loader.exec_module(om)
LOG = []
class _H(logging.Handler):
    def emit(self, r): LOG.append((r.levelno, r.getMessage()))
lg = logging.getLogger('OmegaV60'); lg.handlers = [_H()]; lg.propagate = False; lg.setLevel(logging.INFO)
print("=" * 66); print("C550 (B2): THE TWO-EXCHANGE ORDER PATH, DRY"); print("=" * 66)
ok("version C550 or later", int(om._OMEGA_VERSION[1:]) >= 550)

# ── no real network, anywhere ────────────────────────────────────────────────
TOUCHED = []
def _no_net(*a, **k):
    TOUCHED.append((a, k))
    raise AssertionError('a real network call was attempted')
om._C550_HTTP = _no_net
om.requests.get = om.requests.post = om.requests.request = om.requests.delete = _no_net

# ── the market the mocks see ─────────────────────────────────────────────────
MK = {'AAA': (2.0, 2.0), 'BBB': (0.5, 0.5), 'CCC': (10.0, 10.0), 'DDD': (1.0, 1.0)}   # coin -> (Delta mark, Binance mark)
RB = [102.0]                                    # CoinDCX's rupee rate (changeable)
RATES_OK = [True]
SHUT = set()
INS = {c: dict(quantity_increment=1.0, min_notional=6.0, taker_fee=0.059, maker_fee=0.0236, exit_only=False,
               status='active') for c in MK}
INS['CCC']['quantity_increment'] = 0.1


class _R:
    def __init__(s, js): s.status_code, s._js = 200, js
    def json(s): return s._js


def public(url, params=None, timeout=None):
    if not RATES_OK[0] and ('settings' in url or 'conversions' in url):
        raise OSError('down')
    if url.endswith('/v2/settings'):
        return _R({'result': {'fiat_to_usd': {'asset_to_fiat_value': 85}}})
    if url.endswith('/futures/data/conversions'):
        return _R([{'symbol': 'USDTINR', 'margin_currency_short_name': 'INR', 'conversion_price': RB[0]}])
    if url == om._C549_DCX_ONE:
        c = params['pair'][2:-5]
        i = dict(INS[c]); i['exit_only'] = i['exit_only'] or c in SHUT
        return _R({'instrument': i})
    raise AssertionError('unexpected public read ' + url)


om._C550_PUBLIC = public
om._c549_dcx_exit_only = lambda c, now=None: c in SHUT
om._c540_keys = lambda: ({'delta_india': ('dkey', 'dsecret'), 'coindcx': ('bkey', 'bsecret')}, False)

cfg = om.Config(); cfg.PAPER_MODE = True; cfg.VENUE = 'binance'; om._c467_cfg_ref[0] = cfg
ok("T1: the lock C550_LIVE_OK exists and is off; C488_LIVE_OK is a different lock and also off; the dry path is on",
   cfg.C550_LIVE_OK is False and cfg.C488_LIVE_OK is False and cfg.C550_ORDERS is True and tuple(cfg.C550_CROSS_CONFIRMED) == ())


def snap_ok(now=None):
    now = now or time.time()
    return {'delta_india': dict(ok=True, at=now, wallets=[], positions=[], equity=0.0),
            'coindcx': dict(ok=True, at=now, wallets=[], positions=[])}


class FakeE:
    def mark(self, s):
        return MK.get(str(s).split('/')[0], (0, 0))[1]


PAIRS = {}
xv = types.SimpleNamespace(pairs=PAIRS, last_run='', closed=[], prods={c: dict(sym=c + 'USD') for c in MK},
                           margins=lambda: {'d': dict(eq=500.0, start=500.0), 'b': dict(eq=500.0, start=500.0)})
bot = types.SimpleNamespace(cfg=cfg, c524x=xv, c488=FakeE(), _c462_state_settled=True,
                            c521d=types.SimpleNamespace(marks={}), c540=types.SimpleNamespace(snap=snap_ok()))


def sync_marks():
    bot.c521d.marks = {c + 'USD': dict(mark=v[0]) for c, v in MK.items()}


sync_marks()


def pair(side, k, coin):
    return dict(side=side, d_sym=coin + 'USD', cv=1.0, d_qty=float(-side * k), b_qty=side * k * MK[coin][0], d_px=MK[coin][0],
                b_px=MK[coin][1], notional=k * MK[coin][0], opened=0, fund_from=0, pnl=0.0, funding=0.0)


def fresh(name):
    """a new state folder (each part starts clean)"""
    d = os.path.join(BASE, name); os.makedirs(d, exist_ok=True)
    om.BASE_PATH = d
    return d


def say_text():
    return ' | '.join(m for _, m in LOG)


# ═══ A. THE DRY RUN ══════════════════════════════════════════════════════════
print("\nA. THE LOCK AND THE DRY RUN")
fresh('dry')
PAIRS.clear(); PAIRS.update({'AAA': pair(1, 50, 'AAA'), 'BBB': pair(-1, 200, 'BBB'), 'CCC': pair(1, 10, 'CCC')})
xv.last_run = '2026-11-15'
LOG.clear()
p = om.C550OrderPath(bot)
before = copy.deepcopy(PAIRS)
p.tick(now=time.time())
ok("T1: a whole dry day (boot, watch, entries, stops) builds and logs every order and sends NONE to a real exchange",
   not TOUCHED and set(p.legs) == {'AAA', 'BBB', 'CCC'} and not p.live()
   and len([1 for m, pth, b in p.sims['delta'].log if pth == '/v2/orders']) == 3 + 2      # 3 entries + 2 short-Delta stops
   and len([1 for m, pth, b in p.sims['coindcx'].log if pth.endswith('/orders/create')]) == 3,
   f"legs {sorted(p.legs)}; touched {len(TOUCHED)}")
ok("T24: the plan's own ledger is identical before and after (C550 only reads it)", PAIRS == before)
txt = say_text()
ok("T24: the log names each order (CoinDCX's leg, then Delta's) and each short leg's emergency stop",
   'AAA: opened short Delta / long CoinDCX -- CoinDCX buy' in txt and 'then Delta sell 50 contracts' in txt
   and 'emergency stops (account at 25% of its half): AAA Delta short at' in txt and 'BBB CoinDCX short at' in txt, txt[-300:])
ok("T21: the day line states the REAL accounts (read-only) beside the plan's", "real accounts (read-only): Delta India 0" in txt
   and "the plan's accounts: Delta $500.00" in txt)
ok("T2: the day line says why live would be blocked (the lock; cross margin not confirmed on both)",
   'would be blocked live: the lock C550_LIVE_OK is off; cross margin not confirmed on CoinDCX and Delta India' in txt)
open(os.path.join(om.BASE_PATH, 'c550_kill'), 'w').write('x')
LOG.clear()
p._watch_at = 0
p.tick(now=time.time())
ok("T19 (dry): the kill switch cancels everything and closes every leg; nothing new opens while the file is there",
   not p.legs and not p.sims['delta'].pos and not p.sims['coindcx'].pos and p.halt.startswith('the kill switch')
   and p.open_pair('DDD', 1, 10, 1.0, '2026-11-15') is None and not TOUCHED)
os.remove(os.path.join(om.BASE_PATH, 'c550_kill'))
p.tick(now=time.time())
ok("T19: removing the file lifts it", p.halt == '' and 'new pairs allowed again' in say_text())
p._watch_at = 0; p.plan_day = ''; p.tick(now=time.time())
fees1, n1 = p.led['fees'], len(p.legs)
pr = om.C550OrderPath(bot)                                  # a restart: new in-memory exchanges, the record on disk
pr.tick(now=time.time())
entry_fees = sum(x['jx']['fee_d'] + x['jx']['fee_b'] for x in pr.led['pairs'].values())
ok("T15 (dry): after a restart the rehearsal book starts again -- the same pairs; its fees are exactly the entries' own, "
   "not added to the old total", n1 == 3 and set(pr.legs) == set(p.legs) and abs(pr.led['fees'] - entry_fees) < 1e-9
   and pr.led['fees'] < fees1 and not TOUCHED, f"old book {fees1:.4f}; after the restart {pr.led['fees']:.4f} = entries {entry_fees:.4f}")

# ═══ THE "LIVE" TESTS: the lock on, cross confirmed, both exchanges mocked ══
EX, SEQ = {}, []


def router(method, url, headers=None, data=None, timeout=None):
    v = 'delta' if 'delta.exchange' in url else 'coindcx'
    path = '/' + url.split('://', 1)[1].split('/', 1)[1].split('?', 1)[0]
    SEQ.append((v, method, path, json.loads(data) if data else None, dict(headers or {})))
    return EX[v].request(method, url, headers=headers, data=data)


def live_world(name):
    fresh(name)
    EX['delta'] = om._C550Sim('delta', lambda c: MK[c][0])
    EX['coindcx'] = om._C550Sim('coindcx', lambda c: MK[c][1])
    SEQ.clear(); LOG.clear()
    om._C550_HTTP = router
    cfg.C550_LIVE_OK = True
    cfg.C550_CROSS_CONFIRMED = ('delta', 'coindcx')
    bot.c540.snap = snap_ok()
    SHUT.clear(); RB[0] = 102.0; RATES_OK[0] = True
    q = om.C550OrderPath(bot)
    q._booted = True
    return q


def creates(v='coindcx'):
    return [s for s in SEQ if s[0] == v and ((v == 'coindcx' and s[2].endswith('/orders/create')) or
                                            (v == 'delta' and s[1] == 'POST' and s[2] == '/v2/orders'))]


print("\nA2. THE GATES (the lock open, mocked exchanges)")
q = live_world('gates')
cfg.C550_CROSS_CONFIRMED = ('delta',)
ok("T2: the lock alone is not enough: without cross margin confirmed on BOTH exchanges it stays dry", not q.live())
cfg.C550_CROSS_CONFIRMED = ('delta', 'coindcx')
ok("T2: with both confirmed, live", q.live())
bot.c540.snap = snap_ok(); bot.c540.snap['coindcx'] = dict(ok=False, at=time.time(), error='the venue answered HTTP 422 ("API key expired. Please generate new keys.")')
LOG.clear()
r = q.open_pair('AAA', 1, 50, 1.0, '2026-11-16')
ok("T20: an expired CoinDCX key: nothing opens, nothing is sent, and it is an alert",
   r is None and not creates() and not creates('delta') and any(l == logging.WARNING and 'API key expired' in m for l, m in LOG))
bot.c540.snap = snap_ok(time.time() - 4000)
ok("T2: keys last read over an hour ago: nothing opens", q.open_pair('AAA', 1, 50, 1.0, '2026-11-16') is None and not creates())
bot.c540.snap = snap_ok()
RATES_OK[0] = False
ok("T5: a rupee rate that cannot be read: nothing opens", q.open_pair('AAA', 1, 50, 1.0, '2026-11-16') is None and not creates()
   and 'a rupee rate could not be read' in say_text())
RATES_OK[0] = True
SHUT.add('AAA')
ok("T2/T8: a close-only CoinDCX market: nothing opens", q.open_pair('AAA', 1, 50, 1.0, '2026-11-16') is None and not creates()
   and 'CoinDCX takes closing orders only on AAA' in say_text())
SHUT.clear()

print("\nB/C. THE ORDERS AND THE TWO LEGS")
q = live_world('orders')
leg = q.open_pair('AAA', 1, 50, 1.0, '2026-11-16')
c_dcx, c_d = creates()[0], creates('delta')[0]
ok("T7: CoinDCX's leg is sent first; Delta's only after CoinDCX's fill is read back",
   SEQ.index(c_dcx) < SEQ.index(c_d) and leg is not None)
ob = c_dcx[3]['order']
want_q = int(50 * 2.0 * 85 / 102 / 2.0)
ok("T4: the CoinDCX order: B-AAA_USDT, INR margin, cross, market, no time_in_force, quantity = Delta's $ x 85/102 / price, "
   "down to its step", ob['pair'] == 'B-AAA_USDT' and ob['margin_currency_short_name'] == 'INR'
   and ob['position_margin_type'] == 'crossed' and ob['order_type'] == 'market_order' and 'time_in_force' not in ob
   and ob['total_quantity'] == want_q and ob['side'] == 'buy', f"{ob}")
ok("T4: CoinDCX's signature is HMAC-SHA256 of the compact JSON body, with its key in X-AUTH-APIKEY",
   c_dcx[4]['X-AUTH-APIKEY'] == 'bkey' and c_dcx[4]['X-AUTH-SIGNATURE'] ==
   om._c540_dcx_sign('bsecret', json.dumps(c_dcx[3], separators=(',', ':'))))
bd = c_d[3]
cid = om._c550_cid('2026-11-16', 'AAA', 'd', 'open')
ok("T3: the Delta order: AAAUSD, whole contracts, sell, market, reduce_only false, a client order id <= 32 from day/coin/leg",
   bd['product_symbol'] == 'AAAUSD' and bd['size'] == 50 and bd['side'] == 'sell' and bd['order_type'] == 'market_order'
   and bd['reduce_only'] is False and bd['client_order_id'] == cid and len(cid) <= 32, f"{bd}")
ok("T3: Delta's signature is method + timestamp + path + query + body, with its key",
   c_d[4]['api-key'] == 'dkey' and c_d[4]['signature'] ==
   om._c540_delta_sign('dsecret', 'POST', c_d[4]['timestamp'], '/v2/orders', '', json.dumps(bd, separators=(',', ':'))))
b_inr = want_q * 2.0 * 102; d_inr = 50 * 1.0 * 2.0 * 85
ok("T5: the two legs are equal in RUPEES within one step (Rs %.0f vs Rs %.0f)" % (b_inr, d_inr),
   abs(b_inr - d_inr) <= 1.0 * 2.0 * 102 + 1.0 * 2.0 * 85)
RB[0] = 110.0
q.open_pair('BBB', -1, 200, 1.0, '2026-11-16')
ob2 = creates()[-1][3]['order']
ok("T5: a changed CoinDCX rate changes the quantity (Rs 110: 200 x 0.5 x 85/110 / 0.5 = 154)",
   ob2['total_quantity'] == int(200 * 0.5 * 85 / 110 / 0.5) and ob2['side'] == 'sell')
RB[0] = 102.0
n0 = len(SEQ)
q.close_pair('AAA', 'spread under 10%/yr', '2026-11-17')
tail = SEQ[n0:]
ex_i = next(i for i, s in enumerate(tail) if s[2].endswith('/positions/exit'))
dl_i = next(i for i, s in enumerate(tail) if s[0] == 'delta' and s[1] == 'POST' and s[2] == '/v2/orders')
ok("T6: the exit: CoinDCX's exit-position call, then Delta's reduce-only close of the exact size; both flat",
   ex_i < dl_i and tail[dl_i][3]['reduce_only'] is True and tail[dl_i][3]['size'] == 50 and tail[dl_i][3]['side'] == 'buy'
   and 'AAA' not in EX['delta'].pos and 'AAA' not in EX['coindcx'].pos and 'AAA' not in q.legs)
ok("T6: no exit order can open a position (a reduce-only order larger than the position is refused by the exchange)",
   EX['delta'].request('POST', 'https://api.india.delta.exchange/v2/orders', data=json.dumps(dict(
       product_symbol='DDDUSD', size=5, side='buy', order_type='market_order', reduce_only=True))).status_code == 400)

q = live_world('refused')
EX['coindcx'].exit_only = {'AAA'}
r = q.open_pair('AAA', 1, 50, 1.0, '2026-11-16')
ok("T8: CoinDCX refuses (HTTP 422, exit-only): Delta's leg is never sent, and it is an alert",
   r is None and not creates('delta') and 'CoinDCX refused the first leg' in say_text() and 'exit-only' in say_text())
q = live_world('delta_fails')
EX['delta'].faults['/v2/orders'] = [('refuse', 400, 'insufficient_margin')]
r = q.open_pair('AAA', 1, 50, 1.0, '2026-11-16')
ok("T9: CoinDCX filled, Delta refused: the CoinDCX leg is unwound at once (exit-position) and alerted",
   r is None and not EX['coindcx'].pos and any(s[2].endswith('/positions/exit') for s in SEQ)
   and 'unwound' in say_text() and 'insufficient_margin' in say_text())
q = live_world('partial')
EX['coindcx'].faults['/exchange/v1/derivatives/futures/orders/create'] = [('partial', 0.5)]
leg = q.open_pair('AAA', 1, 50, 1.0, '2026-11-16')
ok("T10: a half-filled CoinDCX leg: Delta's is sized to the rupees that filled (25 contracts, not 50)",
   leg is not None and creates('delta')[-1][3]['size'] == round(want_q * 0.5 * 2.0 * 102 / (85 * 2.0))
   and abs(EX['delta'].pos['AAA']['qty']) == creates('delta')[-1][3]['size'])
EX['coindcx'].faults['/exchange/v1/derivatives/futures/orders/create'] = [('partial', 0.01)]
r = q.open_pair('DDD', 1, 50, 1.0, '2026-11-16')
ok("T10: a fill under one Delta contract: the CoinDCX leg is unwound", r is None and 'DDD' not in EX['coindcx'].pos
   and 'under one Delta contract' in say_text())
q = live_world('timeouts')
EX['coindcx'].faults['/exchange/v1/derivatives/futures/orders/create'] = [('timeout_after',)]
EX['delta'].faults['/v2/orders'] = [('timeout_after',)]
leg = q.open_pair('AAA', 1, 50, 1.0, '2026-11-16')
ok("T11: both answers lost after the exchanges acted: each is read back (CoinDCX positions, Delta by client order id) and "
   "NOTHING is sent twice", leg is not None and len(creates()) == 1 and len(creates('delta')) == 1
   and any(s[2].startswith('/v2/orders/client_order_id/') for s in SEQ) and abs(EX['delta'].pos['AAA']['qty']) == 50)
EX['coindcx'].faults['/exchange/v1/derivatives/futures/orders/create'] = [('timeout',)]
r = q.open_pair('BBB', 1, 200, 1.0, '2026-11-16')
ok("T11: CoinDCX's answer lost and nothing there: Delta's leg not sent, nothing retried blind",
   r is None and len(creates('delta')) == 1 and 'BBB' not in EX['coindcx'].pos)

print("\nD. THE SAFETY NET")
q = live_world('stops')
q.open_pair('AAA', 1, 50, 1.0, '2026-11-16')        # short Delta (a +1 pair)
q.open_pair('BBB', -1, 200, 1.0, '2026-11-16')      # short CoinDCX
accts = {'d': (480.0, 500.0), 'b': (520.0, 500.0)}
q.place_stops('2026-11-16', accts)
ds = [s for s in creates('delta') if s[3].get('stop_order_type')][-1][3]
sp_a = 2.0 * (1 + (480.0 - 0.25 * 500.0) / (50 * 1.0 * 2.0))
ok("T12: Delta's stop on the short AAA leg: stop_loss_order, reduce-only, on the MARK price, buy, the leg's size, at "
   "mark x (1 + (account - 25% of half) / leg)", ds['stop_order_type'] == 'stop_loss_order' and ds['reduce_only'] is True
   and ds['stop_trigger_method'] == 'mark_price' and ds['side'] == 'buy' and ds['size'] == 50
   and abs(float(ds['stop_price']) - sp_a) < 1e-6, f"{ds['stop_price']} vs {sp_a:.6f}")
tp = [s for s in SEQ if s[2].endswith('/positions/create_tpsl')][-1][3]
qb = abs(EX['coindcx'].pos['BBB']['qty'])
# C551 (20 Nov): this expectation first mixed units like the code (the leg's USDT notional against an account in the
# ledger's Rs 85 dollars); the pre-registered meaning -- the account at 25% of its half -- needs the leg in ledger dollars
sp_b = 0.5 * (1 + (520.0 - 0.25 * 500.0) / (qb * 0.5 * 102.0 / 85.0))
ok("T12: CoinDCX's stop on the short BBB leg: the position's own stop loss (stop_market), at the same formula "
   "(C551: the leg's USDT at Rs 102, in ledger dollars of Rs 85)",
   tp['id'] == EX['coindcx'].pos['BBB']['id'] and tp['stop_loss']['order_type'] == 'stop_market'
   and abs(float(tp['stop_loss']['stop_price']) - sp_b) < 1e-6, f"{tp}")
old = q.legs['AAA']['stop']['id']
q.place_stops('2026-11-17', {'d': (300.0, 500.0), 'b': (520.0, 500.0)})
ok("T12: re-placed when the account changes: the old stop is cancelled first, a new one placed (its own client order id)",
   EX['delta'].orders[old]['state'] == 'cancelled' and q.legs['AAA']['stop']['id'] != old
   and [s for s in creates('delta') if s[3].get('stop_order_type')][-1][3]['client_order_id'].endswith('stp2'))
LOG.clear()
MK['AAA'] = (2.0 * 6.3, 2.0 * 6.3)                  # BLESS: +530% in a day
EX['delta'].jump('AAA', MK['AAA'][0])
q.watch('2026-11-17', now_ms=int(time.time() * 1000))
J = q.led['journal']
ok("T13: a +530% jump on the short Delta leg: the stop fires, the watch closes the twin (CoinDCX exit-position), both legs "
   "journalled 'emergency stop', and it is an alert", 'AAA' not in EX['delta'].pos and 'AAA' not in EX['coindcx'].pos
   and 'AAA' not in q.legs and any(x['coin'] == 'AAA' and x['why'] == 'emergency stop' for x in J)
   and any(l == logging.WARNING and 'AAA: the Delta leg is gone (emergency stop)' in m for l, m in LOG))
MK['AAA'] = (2.0, 2.0)
q._cancel_stops('BBB')
MK['BBB'] = (0.5 * 6.3, 0.5 * 6.3)
EX['coindcx'].jump('BBB', MK['BBB'][1], liq_at=0.5 * 1.9)
q.watch('2026-11-17', now_ms=int(time.time() * 1000))
ok("T13: no stop and the exchange liquidates the short CoinDCX leg first: the twin (Delta) is closed, journalled 'liquidated'",
   'BBB' not in EX['delta'].pos and 'BBB' not in q.legs and any(x['coin'] == 'BBB' and x['why'] == 'liquidated' for x in J))
MK['BBB'] = (0.5, 0.5)
q.open_pair('CCC', -1, 10, 1.0, '2026-11-17')
held = EX['delta'].pos['CCC']['qty']
EX['delta']._fill('CCC', -held, 10.0, kind='adl')
q.watch('2026-11-17', now_ms=int(time.time() * 1000))
ok("T14: an auto-deleveraging fill on Delta: the twin is closed the same way, journalled 'auto-deleveraged'",
   'CCC' not in EX['coindcx'].pos and any(x['coin'] == 'CCC' and x['why'] == 'auto-deleveraged' for x in J))

print("\nE. RESTART SAFETY")
q = live_world('restart')
PAIRS.clear(); PAIRS.update({'AAA': pair(1, 50, 'AAA'), 'BBB': pair(-1, 200, 'BBB')})
xv.last_run = '2026-11-18'
q.plan()
n_b, n_d = len(creates()), len(creates('delta'))
q2 = om.C550OrderPath(bot); q2.plan_day = ''
q2.boot_reconcile('2026-11-18'); q2.plan()
ok("T15: a restart and a re-run of the same day: nothing is sent twice (the record + the exchanges' positions)",
   len(creates()) == n_b and len([s for s in creates('delta') if not s[3].get('stop_order_type')]) ==
   len([s for s in creates('delta')[:n_d] if not s[3].get('stop_order_type')]), f"{len(creates())} vs {n_b}")
os.remove(os.path.join(om.BASE_PATH, 'c550_orders.json'))
q3 = om.C550OrderPath(bot); q3.plan_day = ''
q3.boot_reconcile('2026-11-18'); q3.plan()
ok("T15: even with the record lost, the pairs on both exchanges are recognised and not opened again",
   len(creates()) == n_b and set(q3.legs) == {'AAA', 'BBB'})
q = live_world('kill_between')
r = q.venue('coindcx').dcx_market('DDD', 50, 'buy')          # the process "dies" after CoinDCX's leg
LOG.clear()
q4 = om.C550OrderPath(bot)
okb = q4.boot_reconcile('2026-11-19')
ok("T16: killed between an entry's two legs: at boot the lone CoinDCX leg is found and closed FIRST, and it is said",
   okb and 'DDD' not in EX['coindcx'].pos and 'lone leg(s) closed first: DDD' in say_text())
q = live_world('kill_exit')
q.open_pair('AAA', 1, 50, 1.0, '2026-11-19')
q._dcx_exit('AAA')                                           # the process "dies" after the exit's first leg
q5 = om.C550OrderPath(bot)
q5.boot_reconcile('2026-11-19')
ok("T17: killed between an exit's two legs: at boot the remaining Delta leg is closed",
   'AAA' not in EX['delta'].pos and 'AAA' not in q5.legs)

print("\nF. THE WATCH, THE RECONCILIATION, THE KILL SWITCH, MARGIN MODE")
q = live_world('reconcile')
q.open_pair('AAA', 1, 50, 1.0, '2026-11-19')
EX['delta']._fill('CCC', 3, 10.0)                             # a position nobody recorded
LOG.clear(); q.reconcile()
ok("T18: hourly, an unexplained position on an exchange is an alert", 'unexplained difference on CCC' in say_text())
fresh('dryrec'); cfg.C550_LIVE_OK = False
pd = om.C550OrderPath(bot)
bot.c540.snap = snap_ok(); LOG.clear(); pd.reconcile()
ok("T18 (dry): the real accounts hold nothing -- no alert", not any(l == logging.WARNING for l, m in LOG))
bot.c540.snap['coindcx']['positions'] = [dict(symbol='B-X_USDT')]
pd.reconcile()
ok("T18 (dry): a real position while the lock is off is an alert", 'the REAL accounts hold 1 position(s) while the lock is off'
   in say_text())
q = live_world('kill_live')
q.open_pair('AAA', 1, 50, 1.0, '2026-11-19'); q.open_pair('BBB', -1, 200, 1.0, '2026-11-19')
q.place_stops('2026-11-19', {'d': (500.0, 500.0), 'b': (500.0, 500.0)})
q.kill('2026-11-19')
ok("T19: the kill switch: every order cancelled on both exchanges, every leg closed, new pairs refused",
   not EX['delta'].pos and not EX['coindcx'].pos and not q.legs
   and all(o['state'] != 'open' for o in EX['delta'].orders.values() if 'state' in o)
   and q.open_pair('CCC', 1, 10, 1.0, '2026-11-19') is None)
q = live_world('isolated')
EX['coindcx'].cross = False
q.open_pair('AAA', 1, 50, 1.0, '2026-11-19')
ok("T22: CoinDCX fills on isolated margin: no further pairs, and an alert",
   'isolated' in q.halt and q.open_pair('BBB', -1, 200, 1.0, '2026-11-19') is None
   and any(l == logging.WARNING and 'not cross' in m for l, m in LOG))
q = live_world('isolated_d')
EX['delta'].cross = False
q.open_pair('AAA', 1, 50, 1.0, '2026-11-19')
ok("T22: Delta's position shows isolated margin: no further pairs", 'Delta opened AAA on isolated margin' in q.halt)

print("\nG. THE TAX JOURNAL")
q = live_world('journal')
q.open_pair('AAA', 1, 50, 1.0, '2026-11-19')
pp = q.led['pairs']['AAA']
t0 = pp['fund_from']
EX['delta'].funding = [(t0 + 1000, 'AAA', 0.06), (t0 + 2000, 'AAA', -0.01)]
EX['coindcx'].funding = [(t0 + 1500, 'AAA', -2.04)]                          # INR
q._rent(t0 + 10 ** 7)
row = list(pp['jx']['fm'].values())[0]
# C551 (20 Nov): first written as Rs 2.04 / 102 = $0.02, the code's own slip; the ledger's dollar is Rs 85 (the paper
# ledger's and the tax statement's), so CoinDCX's Rs -2.04 is -$0.024
ok("T23: rent from the exchanges' own records, by IST month: Delta +$0.06 / -$0.01 (+18% GST), CoinDCX Rs -2.04 = $-0.024 "
   "(C551: rupees / 85, the ledger's dollar)",
   abs(row[0] - 0.06) < 1e-9 and abs(row[1] + 0.01) < 1e-9 and abs(row[2] + 0.0018) < 1e-9 and abs(row[4] + 2.04 / 85) < 1e-9
   and abs(row[5] + 2.04 / 85 * 0.18) < 1e-9, str(row))
paper_rec = []
stub = types.SimpleNamespace(cfg=cfg, _c544_log=paper_rec.append, venue=lambda: 'coindcx', v2=lambda: 'CoinDCX')
om.C524CrossVenue._c544_close(stub, 'AAA', copy.deepcopy(pp), 'x', 0, 1.0, 0.0, 0.0)
MK['AAA'] = (2.2, 2.2)
q.close_pair('AAA', 'spread changed sign', '2026-11-20')
rec = q.led['journal'][-1]
ok("T23: a live close writes exactly the paper ledger's 'close' record keys", set(rec) == set(paper_rec[0]),
   str(set(rec) ^ set(paper_rec[0])))
ok("T23: ... with the exits' REAL fill prices (2.2 on both, from the fills) and fees from the fills",
   rec['d_px1'] == 2.2 and rec['b_px1'] == 2.2 and rec['fee_d_out'] > 0 and rec['fee_b_out'] > 0 and rec['why'] == 'spread changed sign')
MK['AAA'] = (2.0, 2.0)
q.save()
tsp = importlib.util.spec_from_file_location('ts550', os.path.join(REPO, 'omega_tax_statement.py'))
ts = importlib.util.module_from_spec(tsp)
with contextlib.redirect_stdout(io.StringIO()):
    tsp.loader.exec_module(ts)
try:
    d = ts.load(os.path.join(om.BASE_PATH, 'c550_live.json'))
    o = ts.build(d, '2026-27', True, 85.0)
    okj = 'AAA' in json.dumps(o, default=str)
except Exception as ex:
    okj = False; print('    ', type(ex).__name__, ex)
ok("T23: omega_tax_statement.py --live (its build) reads the order path's ledger without error, the close in it", okj)

print("\nG2. C551: ONE UNIT FOR THE LEDGER (added 20 Nov 2026 after the operator's 10:14 IST server lines; regression "
      "checks for a bug found then, not pre-registered)")
q = live_world('units')
q.led['start_equity'] = 1000.0
q.open_pair('BBB', -1, 200, 1.0, '2026-11-16')                               # long Delta / short CoinDCX
lb_, pb_ = q.legs['BBB'], q.led['pairs']['BBB']
qb = abs(EX['coindcx'].pos['BBB']['qty'])
ob_ = [o for o in EX['coindcx'].orders.values() if o['pair'] == 'B-BBB_USDT'][-1]
ok("C551: the ledger's CoinDCX quantity is Delta-equivalent (real x 102/85); the real one stays in the leg (for the exchange)",
   abs(abs(pb_['b_qty']) - qb * 102 / 85) < 1e-9 and abs(lb_['b']['qty']) == qb and abs(pb_['b_real']) == qb
   and pb_['b_conv'] == 102.0 and pb_['d_rate'] == 85.0, f"real {qb:g}, ledger {pb_['b_qty']:.4f}")
ok("C551: CoinDCX's entry fee (USDT, as CoinDCX reports it) is booked at Rs 102 in ledger dollars of Rs 85",
   abs(pb_['jx']['fee_b'] * 85 - float(ob_['fee_amount']) * 102) < 1e-9, f"{ob_['fee_amount']} USDT")
q.place_stops('2026-11-16', {'d': (500.0, 500.0), 'b': (480.0, 500.0)})
spb = float([s for s in SEQ if s[2].endswith('/positions/create_tpsl')][-1][3]['stop_loss']['stop_price'])
left = (480.0 * 85 - qb * (spb - 0.5) * 102) / (500.0 * 85)
ok("C551: at CoinDCX's emergency stop, that account in RUPEES is at 25% of its half (not ~10%)", abs(left - 0.25) < 1e-6,
   f"stop {spb:.6g}: {100 * left:.2f}% of the half")
q.open_pair('AAA', 1, 50, 1.0, '2026-11-16')                                 # short Delta
q.place_stops('2026-11-16', {'d': (450.0, 500.0), 'b': (480.0, 500.0)})
spa = float([s for s in creates('delta') if s[3].get('stop_order_type')][-1][3]['stop_price'])
ok("C551: at Delta's emergency stop, that account is at 25% of its half (unchanged)",
   abs((450.0 - 50 * 1.0 * (spa - 2.0)) / 500.0 - 0.25) < 1e-6, f"stop {spa:.6g}")
t0 = pb_['fund_from']
EX['coindcx'].funding = [(t0 + 1500, 'BBB', -5.10)]                          # Rs -5.10 of rent paid on CoinDCX
EX['delta'].funding = []
q._rent(t0 + 10 ** 7)
fee_in_usdt = float(ob_['fee_amount'])
MK['BBB'] = (0.55, 0.55); sync_marks()                                      # both prices +10%
q.close_pair('BBB', 'spread under 10%/yr', '2026-11-20')
recb = q.led['journal'][-1]
fee_out_usdt = float([x for x in EX['coindcx'].fills if x['coin'] == 'BBB'][-1]['px']) * qb * 0.0005 * 1.18
ok("C551: the close in RUPEES: Delta's price result x 85 and CoinDCX's real one (USDT x 102); the pair nets to under one "
   "CoinDCX step", abs(recb['px_d'] * 85 - 200 * 1.0 * 0.05 * 85) < 1e-6 and abs(recb['px_b'] * 85 + qb * 0.05 * 102) < 1e-6
   and abs(recb['px_d'] + recb['px_b']) * 85 <= 1.0 * 0.55 * 102, f"Delta Rs {recb['px_d'] * 85:.2f}, CoinDCX Rs {recb['px_b'] * 85:.2f}")
ok("C551: CoinDCX's fees in RUPEES = its fills' USDT fees x 102 (entry + exit)",
   abs(recb['fee_b'] * 85 - (fee_in_usdt + fee_out_usdt) * 102) < 1e-6, f"Rs {recb['fee_b'] * 85:.4f}")
MK['BBB'] = (0.5, 0.5); sync_marks()
q.save()
try:
    d = ts.load(os.path.join(om.BASE_PATH, 'c550_live.json'))
    o = ts.build(d, '2026-27', True, 85.0)
    itb = next(it for it in o['closed'] if it['rec'].get('coin') == 'BBB')
    lgb = itb['legs']['b']
    okr = abs(lgb['rent_out'] * 85 + 5.10) < 1e-6 and abs(lgb['rent_gst'] * 85 + 5.10 * 0.18) < 1e-6 \
        and abs(lgb['price'] * 85 + qb * 0.05 * 102) < 1e-6
    det = f"rent Rs {lgb['rent_out'] * 85:.2f}, GST Rs {lgb['rent_gst'] * 85:.3f}, price Rs {lgb['price'] * 85:.2f}"
except Exception as ex:
    okr, det = False, f"{type(ex).__name__}: {ex}"
ok("C551: the tax statement (--live build) shows CoinDCX's rent, its GST and its price result in the exchange's own rupees",
   okr, det)
q = live_world('exit_px')
q.open_pair('AAA', 1, 50, 1.0, '2026-11-19')                                 # long CoinDCX: its exit is a sell
_orig = EX['coindcx']._dcx
def _newest_first(method, path, body, params, part):
    r = _orig(method, path, body, params, part)
    return om._C550Resp(200, list(reversed(r.json()))) if path.endswith('/trades') else r
EX['coindcx']._dcx = _newest_first
MK['AAA'] = (2.2, 2.2); sync_marks()
q.close_pair('AAA', 'spread under 10%/yr', '2026-11-20')
rx = q.led['journal'][-1]
qa = abs(rx['b_qty']) * 85 / 102
ok("C551: the exit's price and fee come from the exit's OWN fills (the closing side), even when CoinDCX lists the newest "
   "first -- never the entry's fill", rx['b_px1'] == 2.2 and abs(rx['fee_b_out'] * 85 - round(qa * 2.2 * 0.0005 * 1.18, 8) * 102) < 1e-6,
   f"exit at {rx['b_px1']}")
MK['AAA'] = (2.0, 2.0); sync_marks()
q.led['start_equity'] = 1000.0
bot.c540.snap = snap_ok()
bot.c540.snap['delta_india'].update(equity=500.0, wallets=[dict(asset='USD', balance=500.0)])
bot.c540.snap['coindcx']['wallets'] = [dict(asset='INR', balance=42500.0)]
ra1 = q._real_accts()
bot.c540.snap['coindcx']['wallets'] = [dict(asset='USDT', balance=42500.0 / 102)]
bot.c540.snap['delta_india'].update(equity=42500.0, wallets=[dict(asset='INR', balance=42500.0)])
ra2 = q._real_accts()
ok("C551: the REAL balances in ledger dollars: CoinDCX Rs 42,500 or 416.67 USDT = $500; Delta $500 or Rs 42,500 = $500",
   abs(ra1['b'][0] - 500) < 1e-9 and abs(ra1['d'][0] - 500) < 1e-9 and abs(ra2['b'][0] - 500) < 1e-6
   and abs(ra2['d'][0] - 500) < 1e-9 and ra1['b'][1] == 500.0, f"{ra1} / {ra2}")
bot.c540.snap = snap_ok()

print("\nH. IN THE BOT; THE READ-ONLY CLIENT UNTOUCHED")
SRC = open(os.path.join(REPO, 'omega_v60_reconstructed.py')).read()
i0 = SRC.index('class TradingBot:')
ok("T24: the bot builds C550 after C540 and ticks it after C540's tick, inside its own try",
   SRC.index('self.c550 = C550OrderPath(self)', i0) > SRC.index('self.c540 = C540ReadOnly(self)', i0)
   and SRC.index('self.c550.tick()', i0) > SRC.index('self.c540.tick()', i0))
ok("T26: C540's read list is unchanged (Delta: 5 reads; CoinDCX: its 4)",
   om._C540_READ_PATHS['coindcx'] == ('/exchange/v1/derivatives/futures/wallets', '/exchange/v1/derivatives/futures/positions',
                                       '/exchange/v1/derivatives/futures/positions/transactions', '/exchange/v1/users/balances')
   and all('orders' not in x or x.endswith('history') or 'fills' in x for x in om._C540_READ_PATHS['delta_india']),
   str(om._C540_READ_PATHS))
try:
    om.C550Venue('coindcx', lambda *a, **k: None).call('POST', '/exchange/v1/users/balances'); refused = False
except PermissionError:
    refused = True
try:
    om.C550Venue('delta', lambda *a, **k: None).call('POST', '/v2/wallet/withdrawals'); refused2 = False
except PermissionError:
    refused2 = True
ok("T26: C550's order classes refuse any path not on their own list (no wallet, no withdrawals)", refused and refused2)
ok("T26: C550 is its own section and class, apart from C540ReadOnly", 'class C550Venue' in SRC and 'class C550OrderPath' in SRC
   and SRC.index('class C550Venue') > SRC.index('class C540ReadOnly'))
ok("T1: across every test above, not one real network call", not TOUCHED, str(TOUCHED[:1]))

print("\n" + "=" * 66)
print(f"C550: {'ALL PASS' if not fails else str(len(fails)) + ' FAIL'}")
sys.exit(1 if fails else 0)
