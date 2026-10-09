#!/usr/bin/env python3
"""C542: Round 22's winner -- the plan's second account moves from Pi42 to CoinDCX (paper); CoinDCX read-only.

The operator, 8 Oct: "my coindcx account is active ...please proceed accordingly ... research again very carefully to
find the best exchange pair". Round 22 (research/c542_preregistration.md, c542_pairs.txt): Delta + CoinDCX is the best
pair under both tax readings; its Part B pick (15 pairs of 12%) runs as a paper copy, not in the plan.
1. The second exchange is a setting (C532_XV_VENUE = 'coindcx'): name, fee, coin list, page and log follow it.
2. The move: each pair's second leg closed on Pi42 and reopened on CoinDCX at the same price, both fees booked on that
   side, once; the Delta legs and the history unchanged; the test copies move the same way; the CoinDCX copy retires.
3. A paper copy at 15 pairs of 12% beside the plan.
4. CoinDCX read-only: signed as its docs say (HMAC-SHA256 of the compact JSON body, ms timestamp), GET for the futures
   wallet and POST for its three other reads, anything else refused; refusals in words; never a key anywhere.
5. The page at phone width, no JavaScript errors.
"""
import os, io, sys, json, time, glob, hmac, hashlib, shutil, types, socket, logging, tempfile, contextlib, importlib.util
REPO = os.path.dirname(os.path.abspath(__file__))
SNAP = os.path.join(REPO, 'research', 'c527_snapshot')
BASE = tempfile.mkdtemp(prefix='c542_test_')
os.environ['OMEGA_BASE_PATH'] = BASE
TOKEN = 'c542-test-token-0123456789abcdef'
os.environ['OMEGA_CTRL_TOKEN'] = TOKEN
fails = []


def ok(n, c, d=''):
    print(f"  {'PASS' if c else 'FAIL'}  {n}" + (f"   {d}" if d else ''))
    if not c:
        fails.append(n)


spec = importlib.util.spec_from_file_location('om542', os.path.join(REPO, 'omega_v60_reconstructed.py'))
om = importlib.util.module_from_spec(spec)
with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
    spec.loader.exec_module(om)
LOG = []
class _H(logging.Handler):
    def emit(self, r): LOG.append((r.levelno, r.getMessage()))
lg = logging.getLogger('OmegaV60'); lg.handlers = [_H()]; lg.propagate = False; lg.setLevel(logging.INFO)
print("=" * 66); print("C542: THE PLAN MOVES TO DELTA + COINDCX (PAPER); COINDCX READ-ONLY"); print("=" * 66)
SRC = open(os.path.join(REPO, 'omega_v60_reconstructed.py')).read()
ok("version C542 or later", int(om._OMEGA_VERSION[1:]) >= 542)
c0 = om.Config()
ok("the plan's second exchange is CoinDCX; its fee 0.05% (+ GST); the 15 x 12% copy on; live trading locked",
   c0.C532_XV_VENUE == 'coindcx' and c0.C541_DCX_FEE == 0.0005 and c0.C542_B15_TEST is True and c0.C488_LIVE_OK is False
   and c0.C524_XVENUE_PAIRS == 10 and c0.C524_XVENUE_SIZE == 0.10 and c0.C524_XVENUE_EQUITY == 1000.0)
cfg = om.Config(); cfg.PAPER_MODE = True; cfg.VENUE = 'binance'; om._c467_cfg_ref[0] = cfg
for _k, _v in om._C516_VENUE_DEFAULTS['binance'].items():
    setattr(cfg, _k, _v)
DAY = 86400000

print("\n1. THE SECOND EXCHANGE IS A SETTING")
om._c532_pi42_coins = lambda: {'HOT', 'FADE', 'BTC'}
om._c541_coindcx_coins = lambda: {'HOT', 'DCXONLY', 'BTC'}
xb = types.SimpleNamespace(cfg=cfg, c488=None, c521d=None)
for f in glob.glob(os.path.join(BASE, 'c5*.json')):
    os.remove(f)
x = om.C524CrossVenue(xb)
cb_d, cb_p = 0.0005 * 1.18 + 0.0002, 0.0010 * 1.18 + 0.0002
ok("CoinDCX: its name, a rupee venue with its own coin list, cost a side 0.05% x 1.18 + 0.02% = 0.079%, GST on rent paid",
   x.venue() == 'coindcx' and x.v2() == 'CoinDCX' and x.on_pi42() and abs(x.cost_b() - cb_d) < 1e-15 and x.fgst(-1.0) == -1.18)
ok("  its coin list is CoinDCX's (Pi42's is not read)", x.pi42_refresh(force=True) and x.pi42 == {'HOT', 'DCXONLY', 'BTC'})
cfg.C532_XV_VENUE = 'pi42'
ok("C532_XV_VENUE = 'pi42' still gives Pi42 exactly (name, 0.138%, its list)",
   x.v2() == 'Pi42' and abs(x.cost_b() - cb_p) < 1e-15 and x.pi42_refresh(force=True) and x.pi42 == {'HOT', 'FADE', 'BTC'})
cfg.C532_XV_VENUE = 'binance'
ok("  and 'binance' the original C524 trade", x.v2() == 'Binance' and not x.on_pi42() and x.cost_b() == om._C524_COST_B)
cfg.C532_XV_VENUE = 'coindcx'
st = x.status()
ok("the page gets the fee and where the rent comes from", st['v2'] == 'CoinDCX' and st['v2_fee'] == 0.0005
   and "Binance's own (8 Oct: identical on 191 of 191 coins)" in st['v2_note'])

print("\n2. THE MOVE FROM PI42 (ONCE, BOTH FEES BOOKED)")
snap = json.load(open(os.path.join(SNAP, 'c524_xvenue.json')))
ok("the snapshot is a Pi42-era ledger (no 'venue' saved)", 'venue' not in snap and len(snap.get('pairs') or {}) >= 5)
cfg.C524_XVENUE_EQUITY = float(snap['start_equity'])
for f in glob.glob(os.path.join(BASE, 'c5*.json')):
    os.remove(f)
json.dump(snap, open(os.path.join(BASE, 'c524_xvenue.json'), 'w'))
n_tot = sum(abs(float(p['d_qty'])) * float(p['cv']) * float(p['d_px']) for p in snap['pairs'].values())
cost = n_tot * (cb_p + cb_d)
cfg.C532_XV_VENUE = 'pi42'
x0 = om.C524CrossVenue(xb)                                   # the same file read as Pi42's: no move (the baseline)
cfg.C532_XV_VENUE = 'coindcx'
ok("  read with the plan on Pi42, nothing moves (C544 saves its new journal at once, still as a Pi42 ledger)",
   abs(x0.eq - float(snap['eq'])) < 1e-12
   and json.load(open(os.path.join(BASE, 'c524_xvenue.json'))).get('venue', 'pi42') == 'pi42')
LOG.clear()
x = om.C524CrossVenue(xb)
ok(f"each pair's Pi42 leg closed and reopened on CoinDCX: {len(snap['pairs'])} pairs, ${n_tot:.2f} of bets x (0.138% + 0.079%) "
   f"= ${cost:.2f}, on the second account's side",
   abs((x0.eq - x.eq) - cost) < 1e-9 and abs((x.fees - x0.fees) - cost) < 1e-9
   and abs((x0.side['b'] - x.side['b']) - cost) < 1e-9 and abs(x.side['d'] - x0.side['d']) < 1e-12,
   f"{x0.eq - x.eq:.6f} vs {cost:.6f}")
ok("  every pair keeps its Delta leg, quantities and history; its own P&L carries its share of the fee",
   set(x.pairs) == set(snap['pairs']) and all(x.pairs[c]['d_qty'] == snap['pairs'][c]['d_qty'] and x.pairs[c]['b_qty'] == snap['pairs'][c]['b_qty']
                                             for c in snap['pairs'])
   and abs(sum(float(snap['pairs'][c]['pnl']) - x.pairs[c]['pnl'] for c in snap['pairs']) - cost) < 1e-9
   and x.daily == {int(k): v for k, v in snap['daily'].items()} and x.start_equity == float(snap['start_equity']))
mv = [m for _, m in LOG if 'C542' in m and 'moves from Pi42 to CoinDCX' in m]
ok("  the log says so in words, once", len(mv) == 1 and f"${cost:.2f}" in mv[0] and 'the Delta legs and the history are unchanged' in mv[0],
   mv[0][:240] if mv else '')
d = json.load(open(os.path.join(BASE, 'c524_xvenue.json')))
ok("  saved at once with the new exchange and the move recorded", d.get('venue') == 'coindcx' and d['venue_moves'][-1]['frm'] == 'Pi42'
   and d['venue_moves'][-1]['to'] == 'CoinDCX' and abs(d['venue_moves'][-1]['cost'] - round(cost, 4)) < 1e-9
   and abs(d['eq'] - x.eq) < 1e-9)
LOG.clear()
x2 = om.C524CrossVenue(xb)
ok("a restart does not move it again", abs(x2.eq - x.eq) < 1e-12 and not any('moves from' in m for _, m in LOG))
ok("the page shows the move for two weeks ('Second account moved: Pi42 -> CoinDCX')",
   x2.status()['venue_moves'][-1]['to'] == 'CoinDCX' and "Second account moved: '+vm.frm+' \\u2192 '+vm.to" in SRC)

print("\n3. THE TEST COPIES")
xb.c524x = x2
json.dump(dict(snap, key='f8', base=float(snap['eq']), base_main=float(snap['eq']), since='2026-10-06', last_slot=0,
               snaps={'2026-10-07': dict(me=1.0, main=1.0, n=10, same=10)}, slots=[]),
          open(os.path.join(BASE, 'c538_f8.json'), 'w'))
json.dump(dict(snap, key='dx', base=float(snap['eq']), base_main=float(snap['eq']), since='2026-10-08', last_slot=0, snaps={}, slots=[]),
          open(os.path.join(BASE, 'c538_dx.json'), 'w'))
LOG.clear()
F8 = om.C538TestRule(xb, 'f8'); DX = om.C538TestRule(xb, 'dx'); B15 = om.C538TestRule(xb, 'b15')
xb.c538 = [F8, DX, B15]
ok("the 8-hour copy moves the same way (same fee), keeping its scoreboard and its base",
   abs((float(snap['eq']) - F8.eq) - cost) < 1e-9 and F8.snaps == {'2026-10-07': dict(me=1.0, main=1.0, n=10, same=10)}
   and F8.base == float(snap['eq']) and json.load(open(os.path.join(BASE, 'c538_f8.json')))['venue'] == 'coindcx')
ok("the CoinDCX copy (C541) was already on CoinDCX: no move, and it retires now your plan is there",
   abs(DX.eq - float(snap['eq'])) < 1e-12 and not DX.active() and DX.venue() == 'coindcx')
cfg.C532_XV_VENUE = 'pi42'
ok("  (it would run again if the plan went back to Pi42)", DX.active())
cfg.C532_XV_VENUE = 'coindcx'
ok("the new copy: 15 pairs of 12% on your plan's exchange, on by default, off with C542_B15_TEST",
   B15.active() and B15.n_pairs() == 15 and B15.bet() == 0.12 and B15.v2() == 'CoinDCX' and x2.n_pairs() == 10 and x2.bet() == 0.10)
cfg.C542_B15_TEST = False
off = B15.active()
cfg.C542_B15_TEST = True
s15 = B15.test_status()
ok("  history's expectation travels with it: +$29.40 a month before tax, ahead in 19 of 24 months", not off
   and s15['month'] == 29.40 and s15['ahead'] == 79 and s15['short'] == '15 x 12%')
ok("the bot runs four copies; the logs push carries the new file",
   "for k in ('f8', 'w3', 'dx', 'b15')]" in SRC and 'c538_b15.json' in open(os.path.join(REPO, 'deploy', 'omega-logpush.sh')).read())

# the 15 x 12% copy really holds up to 15 pairs at 12% -- a run on fake data
D0 = (int(time.time() * 1000) // DAY - 3) * DAY
COINS = [f'C{j:02d}' for j in range(20)]


class FakeDelta:
    def __call__(s, path, params, tries=3):
        if path == '/v2/products':
            return [dict(symbol=k + 'USD', contract_value='1', taker_commission_rate='0.0005',
                         product_specs=dict(rate_exchange_interval=28800, tags=['layer_1']), settling_asset={'symbol': 'USD'},
                         underlying_asset={'symbol': k}) for k in COINS]
        if path == '/v2/tickers':
            return [dict(symbol=k + 'USD', mark_price='1.0') for k in COINS]
        if path == '/v2/history/candles':
            st, en = int(params['start']), int(params['end'])
            return [dict(time=t, close=0.10) for t in range(-(-st // 28800) * 28800, en + 1, 3600)]
        return None


om._c521_get = FakeDelta()
om._c516_bn_get = lambda base, path, params, tries=3: (
    [dict(fundingTime=t, fundingRate='0.0') for t in range(-(-params['startTime'] // 28800000) * 28800000,
                                                            params['startTime'] + 9 * DAY, 28800000)]
    if path == '/fapi/v1/fundingRate' else None)
om._c541_coindcx_coins = lambda: set(COINS)
xe = types.SimpleNamespace(marks={k + '/USDT:USDT': {} for k in COINS}, refresh_marks=lambda force=False: True, mark=lambda s_: 1.0)
xb3 = types.SimpleNamespace(cfg=cfg, c488=xe, portfolio=None, _c462_state_settled=True)
for f in glob.glob(os.path.join(BASE, 'c5*.json')):
    os.remove(f)
cfg.C524_XVENUE_EQUITY = 1000.0
cfg.C546_XV_SAME_SHARE = 1.0          # C546: these 20 coins all face one way; this check is about size, not direction
xm = om.C524CrossVenue(xb3); xm.reset(); xb3.c524x = xm
xm.run(now_ms=D0 + 30 * 60000)
b3 = om.C538TestRule(xb3, 'b15'); b3.reset(); xb3.c538 = [b3]
b3.start_equity = b3.eq = 1000.0
with b3._lock:
    b3.run(D0 + 30 * 60000)
n_ = [abs(p['d_qty']) for p in b3.pairs.values()]
ok("a run on 20 equally wide coins: your plan opens 10 pairs of $100, the copy 15 pairs of $120",
   len(xm.pairs) == 10 and all(abs(p['d_qty']) == 100 for p in xm.pairs.values()) and len(b3.pairs) == 15 and set(n_) == {120.0},
   f"{len(xm.pairs)} / {len(b3.pairs)} {sorted(set(n_))}")
ok("  every entry names CoinDCX", all('CoinDCX' in e for e in xm.info['entered'] + b3.info['entered']) and xm.info['venue'] == 'CoinDCX')
cfg.C546_XV_SAME_SHARE = 0.6          # C546's cap back on

print("\n4. COINDCX, READ-ONLY")
SEC = SRC[SRC.index('# C540 (build step B1)'):SRC.index('# C530: PENDLE FIXED YIELD')]
P = om._C540_READ_PATHS['coindcx']
ok("CoinDCX's read list: futures wallet, positions, rent transactions, rupee balance -- nothing that orders, exits, "
   "changes margin or leverage, transfers or withdraws",
   len(P) == 4 and not any(w in p for p in P for w in ('order', 'cancel', 'exit', 'margin', 'leverage', 'transfer', 'withdraw', 'create')))
CALLS = []


class R_:
    def __init__(s, code, body):
        s.status_code, s._b = code, body
    def json(s):
        if s._b is None:
            raise ValueError('html')
        return s._b


now = time.time()
ROUTES = {
    '/exchange/v1/derivatives/futures/wallets': [dict(id='w1', currency_short_name='INR', balance='41250.5', locked_balance='0'),
                                                 dict(id='w2', currency_short_name='USDT', balance='0', locked_balance='0')],
    '/exchange/v1/derivatives/futures/positions': [dict(id='p1', pair='B-KAITO_USDT', active_pos=-120.0, avg_price=1.2,
                                                        liquidation_price=1.9, locked_margin=5000.0, margin_currency_short_name='INR'),
                                                   dict(id='p2', pair='B-LIT_USDT', active_pos=0.0)],
    '/exchange/v1/derivatives/futures/positions/transactions': [
        dict(pair='B-KAITO_USDT', stage='funding', amount=12.5, margin_currency_short_name='INR', created_at=int((now - 3600) * 1000)),
        dict(pair='B-KAITO_USDT', stage='funding', amount=-2.0, margin_currency_short_name='INR', created_at=int((now - 7200) * 1000)),
        dict(pair='B-KAITO_USDT', stage='funding', amount=99.0, margin_currency_short_name='INR', created_at=int((now - 3 * 86400) * 1000))],
    '/exchange/v1/users/balances': [dict(currency='INR', balance=1500.25, locked_balance=0), dict(currency='BTC', balance=0)],
}


def fake(method):
    def f(url, data=None, headers=None, timeout=None, **kw):
        CALLS.append((method, url, data, dict(headers or {})))
        path = url.split('api.coindcx.com')[1]
        return R_(200, ROUTES[path])
    return f


om._C540_HTTP_GET, om._C540_HTTP_POST = fake('GET'), fake('POST')
KX, SX = 'dcx-test-key-AAAA1111', 'dcx-test-secret-BBBB2222CCCC'
json.dump({'coindcx': {'api_key': KX, 'api_secret': SX}}, open(os.path.join(BASE, 'api_keys.json'), 'w'))
os.chmod(os.path.join(BASE, 'api_keys.json'), 0o600)
bt = types.SimpleNamespace(cfg=cfg, c524x=xm)
ro = om.C540ReadOnly(bt)
LOG.clear()
ro.tick(now=now)
st = ro.status()['venues'].get('coindcx') or {}
ok("its four reads, in words: rupee futures wallet 41,250.50, one open position (KAITO), rent last 24 h +10.50 (two "
   "payments, the older one left out), rupee wallet 1,500.25",
   st.get('ok') and st['wallets'][0] == dict(asset='INR', balance=41250.5, locked=0.0) and len(st['positions']) == 1
   and st['positions'][0]['coin'] == 'KAITO' and st['rent_24h'] == {'INR': 10.5} and st['rent_n'] == 2 and st['spot_inr'] == 1500.25,
   json.dumps({k: st.get(k) for k in ('wallets', 'rent_24h', 'spot_inr')}))
meth = {u.split('api.coindcx.com')[1]: m for m, u, _, _ in CALLS}
ok("  the futures wallet by GET, the other three by POST, as CoinDCX's docs say -- and nothing else was called",
   meth == {'/exchange/v1/derivatives/futures/wallets': 'GET', '/exchange/v1/derivatives/futures/positions': 'POST',
            '/exchange/v1/derivatives/futures/positions/transactions': 'POST', '/exchange/v1/users/balances': 'POST'}, str(meth))
okk = True
for m, u, body, h in CALLS:
    d_ = json.loads(body)
    okk &= (body == json.dumps(d_, separators=(',', ':')) and isinstance(d_['timestamp'], int) and abs(d_['timestamp'] / 1000 - time.time()) < 60
            and h['X-AUTH-APIKEY'] == KX and h['X-AUTH-SIGNATURE'] == hmac.new(SX.encode(), body.encode(), hashlib.sha256).hexdigest()
            and h['Content-Type'] == 'application/json')
ok("  each signed as the docs say: hex HMAC-SHA256 of the exact compact JSON body sent, a millisecond timestamp inside",
   okk and json.loads(CALLS[1][2])['margin_currency_short_name'] == ['INR', 'USDT'] and json.loads(CALLS[2][2])['stage'] == 'funding')
bad = []
ro.keys = {'coindcx': (KX, SX)}
for p in ('/exchange/v1/derivatives/futures/orders/create', '/exchange/v1/derivatives/futures/positions/exit',
          '/exchange/v1/derivatives/futures/positions/add_margin', '/exchange/v1/derivatives/futures/positions/update_leverage',
          '/exchange/v1/wallets/transfer', '/exchange/v1/orders/create'):
    try:
        ro._get('coindcx', p)
        bad.append(p)
    except PermissionError:
        pass
ok("anything off the read list is refused before it leaves the server (create order, exit, margin, leverage, transfer)", not bad, str(bad))
ln = [m for _, m in LOG if 'C540 real account' in m and 'CoinDCX' in m]
ok("the log: one line in words, no key", len(ln) == 1 and 'CoinDCX: futures INR 41250.50' in ln[0] and 'rupee wallet INR 1500.25' in ln[0]
   and 'nothing is traded live' in ln[0] and KX not in ln[0] and SX not in ln[0], ln[0][:220] if ln else '')
ok("  and the status and the page data never carry the key", KX not in json.dumps(ro.status()) and SX not in json.dumps(ro.status()))
ok("refusals in words: a wrong key, a key bound to another IP, CoinDCX's firewall",
   'CoinDCX refused the key' in om._c540_why('coindcx', 401, {'code': 401, 'message': 'Invalid credentials', 'status': 'error'})
   and 'bound to another IP' in om._c540_why('coindcx', 401, {'message': 'IP not whitelisted / bind IP'})
   and "CoinDCX's firewall answered" in om._c540_why('coindcx', 403, None))
ok("the key helper takes coindcx (and, Round 22b, mudrex and coinswitch for the server check)",
   'delta_india|pi42|coindcx|mudrex|coinswitch)' in open(os.path.join(REPO, 'deploy', 'omega-keys.sh')).read())
# the real CoinDCX, a fake key: its answer is a refusal in words (proves the request reached its key check)
om._C540_HTTP_GET, om._C540_HTTP_POST = om.requests.get, om.requests.post
ro2 = om.C540ReadOnly(bt); ro2.keys = {'coindcx': ('fakefakefakefakefake', 'fakefakefakefakefakefake')}
try:
    ro2._get('coindcx', '/exchange/v1/derivatives/futures/positions', {'page': '1', 'size': '10', 'margin_currency_short_name': ['INR']})
    real = 'answered 200 to a fake key?'
except om.C540Refused as ex:
    real = str(ex)
except Exception as ex:
    real = f'network: {type(ex).__name__}'
ok("the REAL CoinDCX, a fake key: 'CoinDCX refused the key' (the request reached its key check in the right shape)",
   real.startswith('CoinDCX refused the key') or real.startswith('network'), real)

print("\n5. THE PAGE")
for f in glob.glob(os.path.join(BASE, 'c5*.json')):
    os.remove(f)
for f in glob.glob(os.path.join(SNAP, 'c*.json')):
    shutil.copy(f, BASE)
cfg.C524_XVENUE_EQUITY = 1000.0; cfg.C531_XV_REBALANCE = True
om._c541_coindcx_coins = lambda: {f'C{j:03d}' for j in range(505)}
L = lambda f: json.load(open(os.path.join(SNAP, f + '.json')))
PX = L('prices'); bk0 = L('c488_book')
pf = om.Portfolio(cfg)
cash = bk0['born']['eq'] + sum(c['pnl'] for c in bk0['closed']) + sum(p['funding'] - p['fees'] + p['realized'] for p in bk0['book'].values())
pf.equity = pf.available_balance = cash
bot = types.SimpleNamespace(cfg=cfg, portfolio=pf, _c462_state_settled=True, _c408_asset_class=lambda s: 'crypto',
                            exchange=types.SimpleNamespace(markets={}, get_current_price=lambda s: None),
                            _c482_risk_guard=lambda: {'pct': 20.0, 'month_eq0': 500.0, 'month_budget': 100.0, 'month_used': 0.0,
                                                      'day_cap': 25.0, 'day_used': 0.0, 'halt': ''},
                            _c504_data_health=lambda now=None: {'ok': True, 'bits': [], 'late': [], 'keys': []})
e = om.C488Engine(bot); bot.c488 = e; pf._c488 = e; e.load()
pf.get_live_equity = lambda ex: pf.equity + e.unrealized()
pf.session_start_equity = 500.0; pf.positions = om.PositionsManager()
for a, k in (('c501v', 'C501Savings'), ('c501s', 'C501Spot'), ('c490', 'C490Carry'), ('c521d', 'C521Delta'), ('c521b', 'C521Bfusd'),
             ('c524x', 'C524CrossVenue'), ('c530p', 'C530Pendle'), ('c489', 'C489Shadow'), ('c501k', 'C501Allostatic'),
             ('c510t', 'C510Tournament')):
    setattr(bot, a, getattr(om, k)(bot))
bot.c538 = [om.C538TestRule(bot, k) for k in ('f8', 'w3', 'dx', 'b15')]
xv, de = bot.c524x, bot.c521d
xv.pi42_refresh(force=True)
NOWs = time.time()
e.marks = {om.C488Engine._ccxt(s): dict(bid=b, ask=a, last=(b + a) / 2, fr=0.0, vol=1e9) for s, (b, a) in PX['perp'].items()}
e._marks_at = NOWs
bot.c501s.bk = {s: (b, a) for s, (b, a) in PX['spot'].items()}; bot.c501s._book_at = NOWs
de.marks = {s: dict(mark=m_, bid=b or m_, ask=a or m_, fr=0.0) for s, (m_, b, a) in PX['delta'].items()}
de._marks_at = NOWs
e.refresh_marks = lambda force=False: True
de.refresh_marks = lambda force=False: True
bot.c501s.book = lambda force=False: bot.c501s.bk
om._C540_HTTP_GET, om._C540_HTTP_POST = fake('GET'), fake('POST')
json.dump({'coindcx': {'api_key': KX, 'api_secret': SX}}, open(os.path.join(BASE, 'api_keys.json'), 'w'))
os.chmod(os.path.join(BASE, 'api_keys.json'), 0o600)
bot.c540 = om.C540ReadOnly(bot); bot.c540.tick(now=time.time())
fbot = types.SimpleNamespace(cfg=cfg, portfolio=pf, c488=e, c501s=bot.c501s, c501v=bot.c501v, c501k=bot.c501k,
                             c489=bot.c489, c490=bot.c490, c510t=bot.c510t, c521b=bot.c521b, c521d=de, c524x=xv,
                             c530p=bot.c530p, c538=bot.c538, c540=bot.c540,
                             mode_mgr=types.SimpleNamespace(mode=types.SimpleNamespace(value='normal')), exchange=bot.exchange,
                             _c467_day_barrier=lambda: {'pnl': 0.0, 'limit': 9.0, 'used': 0.0, 'frac': 0.0},
                             _c482_risk_guard=bot._c482_risk_guard, _c504_data_health=bot._c504_data_health)


def free_port():
    s_ = socket.socket(); s_.bind(('127.0.0.1', 0)); p_ = s_.getsockname()[1]; s_.close(); return p_


def page():
    port = free_port(); om.RemoteControl(fbot, port=port).start(); time.sleep(0.6)
    from playwright.sync_api import sync_playwright
    exe = (glob.glob('/opt/pw-browsers/chromium-*/chrome-linux/chrome') or [None])[0]
    with sync_playwright() as pw:
        br = pw.chromium.launch(executable_path=exe) if exe else pw.chromium.launch()
        pg = br.new_page(viewport={'width': 412, 'height': 900}); errs = []
        pg.on('pageerror', lambda e_: errs.append(str(e_)))
        pg.goto(f'http://127.0.0.1:{port}/?t={TOKEN}'); pg.wait_for_timeout(3000)
        tc = lambda i: pg.evaluate(f"(document.getElementById('{i}')||{{}}).textContent||''")
        G = dict(money=tc('s-money'), acc=tc('s-acc'), nxt=tc('s-next'), test=tc('s-test'), xven=tc('xvenue'), real=tc('realacc'),
                 det=tc('plandetk'), W=pg.evaluate('document.documentElement.scrollWidth'), html=pg.content())
        br.close()
    return G, errs


try:
    for t in bot.c538:
        t.copy_main()
    G, er = page()
    ok("your money: 'all of it in the rent-gap trade (Delta vs CoinDCX)'", 'Delta vs CoinDCX' in G['money'], G['money'][:200])
    ok("your two accounts: Delta India and CoinDCX, with the real CoinDCX account read-only beside them",
       'CoinDCX' in G['acc'] and 'Your real accounts (read-only)' in G['acc'] and 'CoinDCX INR 41250.50' in G['acc'], G['acc'][-260:])
    ok("what happens next: 'Second account moved: Pi42 -> CoinDCX', the pairs and the fee, Delta and history unchanged",
       'Second account moved: Pi42 → CoinDCX' in G['nxt'] and 'closed and reopened on CoinDCX at the same prices' in G['nxt']
       and 'Your Delta bets and the plan’s history are unchanged' in G['nxt'], G['nxt'][:400])
    ok("your plan in detail: CoinDCX's fee 0.05% + GST, where its rent comes from, its coins",
       'Delta vs CoinDCX' in G['xven'] and 'its fee 0.05% + GST' in G['xven'] and "Binance's own (8 Oct: identical on 191 of 191 coins)" in G['xven']
       and "CoinDCX's 505 coins only" in G['xven'], G['xven'][:400])
    ok("the copies: 15 pairs of 12% with its plain warning; the retired CoinDCX copy is gone",
       '15 pairs of 12%' in G['test'] and 'BLESS rose 530% on 15 Oct 2025' in G['test'] and 'It is not your plan' in G['test']
       and 'CoinDCX instead of Pi42' not in G['test'] and 'three copies of your plan' in G['test'], G['test'][:300])
    ok("the real accounts' detail: CoinDCX's wallets, rupee wallet, position, rent; Pi42 (not connected) not mentioned",
       'CoinDCX' in G['real'] and 'rupee wallet ₹1,500.25' in G['real'] and 'B-KAITO_USDT' in G['real'] and 'INR 10.5000' in G['real']
       and 'Pi42' not in G['real'], G['real'][:400])
    ok("no 'Pi42' left in your plan's own sections, except the move note and the copies' history lines",
       'Pi42' not in G['money'] and 'Pi42' not in G['acc'] and 'Pi42' not in G['xven'])
    ok("the page never carries a key", KX not in G['html'] and SX not in G['html'])
    # C543: copies that started on different days -- each row says its start; the header says so
    f8, w3, dx_, b15 = bot.c538
    for t, sn in ((f8, '2026-10-06'), (w3, '2026-10-06'), (b15, '2026-10-08')):
        t.since = sn
        t.snaps = {'2026-10-09': dict(me=(1.10 if t is b15 else 4.20), main=(1.00 if t is b15 else 4.05), n=10, same=10)}
    G3, er3 = page(); er += er3
    T3 = G3['test']
    ok("C543: a copy that started later says so on its row, and the header says each is compared over its own days",
       '15 pairs of 12% (since 8 Oct)' in T3 and 'Checks every 8 hours (since' not in T3 and 'Since 6 Oct (the newest since 8 Oct)' in T3
       and 'each is compared with your rule over the same days it has run' in T3 and 'ahead $0.10' in T3, T3[:420])
    ok("412 px wide (a phone): nothing overflows", max(G['W'], G3['W']) <= 412, str((G['W'], G3['W'])))
    ok("no JavaScript errors", not er, '; '.join(er)[:300])
except Exception as ex:
    import traceback; traceback.print_exc()
    ok("page check ran", False, f"{type(ex).__name__}: {ex}")

print("\n" + "=" * 66)
print(f"C542 TEST: {'ALL PASS' if not fails else f'{len(fails)} FAIL'}")
shutil.rmtree(BASE, ignore_errors=True)
sys.exit(1 if fails else 0)
