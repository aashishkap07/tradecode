#!/usr/bin/env python3
"""C540 (build step B1): read-only connections to the operator's REAL Delta Exchange India and Pi42 accounts.

1. A window, not a hand: one network call (an HTTP GET), four read paths per venue, anything else refused.
2. Signed as each venue's official docs say (Delta: method + timestamp(s) + path + query; Pi42: the query string
   with a millisecond timestamp), tested on recorded example responses shaped like the docs'.
3. Keys only from api_keys.json; never in a log line, the page or an error; a loose file is warned about.
4. Refusals in words the operator can act on (permission, IP, clock, wrong key).
5. The page shows the real accounts beside the paper ledger; the logs push redacts every key by its literal text.
"""
import os, io, sys, json, time, glob, gzip, hmac, hashlib, shutil, types, socket, logging, tempfile, subprocess
import contextlib, importlib.util
REPO = os.path.dirname(os.path.abspath(__file__))
SNAP = os.path.join(REPO, 'research', 'c527_snapshot')
BASE = tempfile.mkdtemp(prefix='c540_test_')
os.environ['OMEGA_BASE_PATH'] = BASE
TOKEN = 'c540-test-token-0123456789abcdef'
os.environ['OMEGA_CTRL_TOKEN'] = TOKEN
fails = []


def ok(n, c, d=''):
    print(f"  {'PASS' if c else 'FAIL'}  {n}" + (f"   {d}" if d else ''))
    if not c:
        fails.append(n)


spec = importlib.util.spec_from_file_location('om540', os.path.join(REPO, 'omega_v60_reconstructed.py'))
om = importlib.util.module_from_spec(spec)
with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
    spec.loader.exec_module(om)
LOG = []
class _H(logging.Handler):
    def emit(self, r): LOG.append((r.levelno, r.getMessage()))
lg = logging.getLogger('OmegaV60'); lg.handlers = [_H()]; lg.propagate = False; lg.setLevel(logging.INFO)
print("=" * 66); print("C540 (B1): THE REAL ACCOUNTS, READ-ONLY"); print("=" * 66)
SRC = open(os.path.join(REPO, 'omega_v60_reconstructed.py')).read()
SEC = SRC[SRC.index('# C540 (build step B1)'):SRC.index('# C530: PENDLE FIXED YIELD')]
cfg = om.Config(); cfg.PAPER_MODE = True; cfg.VENUE = 'binance'; om._c467_cfg_ref[0] = cfg
for _k, _v in om._C516_VENUE_DEFAULTS['binance'].items():
    setattr(cfg, _k, _v)
ok("version C540 or later; on by default; live trading still locked (C488_LIVE_OK False)",
   int(om._OMEGA_VERSION[1:]) >= 540 and cfg.C540_READ_ONLY is True and cfg.C488_LIVE_OK is False and cfg.C540_POLL_S == 600)

print("\n1. A WINDOW, NOT A HAND")
ok("one network call in the whole C540 section, and it is an HTTP GET", SEC.count('_C540_HTTP_GET(') == 1
   and '_C540_HTTP_GET = requests.get' in SEC and not any(w in SEC for w in ('requests.post', 'requests.put', 'requests.delete',
                                                                           'requests.request', '.post(', '.put(', '.delete(')))
paths = [p for v in om._C540_READ_PATHS.values() for p in v]
ok("the read list: balances, open positions, fills/trades, transactions -- no order, cancel, margin, leverage or transfer path",
   len(paths) == 8 and not any(w in p.lower() for p in paths for w in ('order', 'cancel', 'change_margin', 'add-margin', 'reduce-margin',
                                                                       'leverage', 'transfer', 'withdraw', 'close', 'preference')),
   str(paths))
ro = om.C540ReadOnly(types.SimpleNamespace(cfg=cfg, c524x=types.SimpleNamespace(pairs={})))
ro.keys = {'delta_india': ('K', 'S'), 'pi42': ('K', 'S')}
bad = []
for v, p in (('delta_india', '/v2/orders'), ('pi42', '/v1/order/place-order'), ('pi42', '/v1/positions/close-all-positions'),
             ('delta_india', '/v2/positions/change_margin')):
    try:
        ro._get(v, p)
        bad.append(p)
    except PermissionError:
        pass
ok("anything off the read list is refused before it leaves the server (order, close-all, margin)", not bad, str(bad))

print("\n2. SIGNED AS THE DOCS SAY")
CALLS = []
KD, SD = 'dk_TESTKEY_0123456789abcd', 'ds_TESTSECRET_9876543210zyxw'
KP, SPI = 'pk_TESTKEY_abcdef0123456789', 'ps_TESTSECRET_0011223344556677'


class R:
    def __init__(s, code, body):
        s.status_code, s._b = code, body
    def json(s):
        if isinstance(s._b, Exception):
            raise s._b
        return s._b


T0 = time.time()
ROUTES = {}


def fake_get(url, headers=None, timeout=None):
    CALLS.append((url, dict(headers or {})))
    for k, fn in ROUTES.items():
        if k in url:
            return fn(url)
    return R(404, {'success': False})


om._C540_HTTP_GET = fake_get
ROUTES.update({
    '/v2/wallet/balances': lambda u: R(200, {'meta': {'net_equity': '515.00', 'robo_trading_equity': '0'}, 'success': True, 'result': [
        {'asset_id': 3, 'asset_symbol': 'USD', 'available_balance': '480.10', 'balance': '512.35', 'blocked_margin': '0',
         'position_margin': '30.00', 'order_margin': '0', 'commission': '0', 'id': 1, 'user_id': 7},
        {'asset_id': 5, 'asset_symbol': 'BTC', 'available_balance': '0', 'balance': '0', 'id': 2, 'user_id': 7}]}),
    '/v2/positions/margined': lambda u: R(200, {'success': True, 'result': [
        {'user_id': 7, 'size': -312, 'entry_price': '0.3342', 'margin': '10.4', 'liquidation_price': '0.61', 'product_id': 1,
         'product_symbol': 'KAITOUSD', 'unrealized_pnl': '0.12', 'realized_funding': '0.4', 'mark_price': '0.3338'},
        {'user_id': 7, 'size': 0, 'entry_price': '0', 'product_symbol': 'OLDUSD'}]}),
    '/v2/wallet/transactions': lambda u: R(200, {'success': True, 'result': [
        {'id': 1, 'amount': '0.05', 'balance': '512.3', 'transaction_type': 'funding', 'meta_data': {}, 'asset_symbol': 'USD'},
        {'id': 2, 'amount': '0.04', 'balance': '512.34', 'transaction_type': 'funding', 'meta_data': {}, 'asset_symbol': 'USD'}],
        'meta': {'after': 'CUR2'}} if 'after=' not in u else {'success': True, 'result': [
        {'id': 3, 'amount': '0.03', 'balance': '512.37', 'transaction_type': 'funding', 'meta_data': {}}], 'meta': {'after': None}}),
    '/v2/fills': lambda u: R(200, {'success': True, 'result': [{'id': 9, 'size': 312, 'commission': '0.02', 'product_symbol': 'KAITOUSD'}]}),
    '/v1/wallet/futures-wallet/details': lambda u: R(200, {'inrBalance': '1941.50', 'walletBalance': '1941.50', 'withdrawableBalance': '1468.50',
        'maintenanceMargin': '0.00', 'unrealisedPnlCross': '0.00', 'unrealisedPnlIsolated': '1.25', 'maxWithdrawableBalance': '1468.50',
        'lockedBalance': '473.00', 'marginBalance': '1468.52', 'marginAsset': 'INR'}),
    '/v1/positions/OPEN': lambda u: R(200, [{'id': 5454, 'contractPair': 'KAITOINR', 'contractType': 'PERPETUAL', 'entryPrice': 29.6,
        'leverage': 2, 'liquidationPrice': 55.0, 'marginType': 'ISOLATED', 'margin': 4600, 'positionAmount': 312, 'positionStatus': 'OPEN',
        'positionType': 'LONG', 'quantity': 312, 'baseAsset': 'KAITO', 'marginAsset': 'INR', 'quoteAsset': 'INR'}]),
    '/v1/user-data/transaction-history': lambda u: R(200, [
        {'id': 1, 'time': '2026-10-08T00:00:01.000Z', 'type': 'FUNDING_FEE', 'amount': 2.5, 'asset': 'INR', 'symbol': 'KAITOINR'},
        {'id': 2, 'time': '2026-10-08T00:00:01.000Z', 'type': 'GST_ON_FUNDING_FEE', 'amount': -0.1, 'asset': 'INR', 'symbol': 'KAITOINR'},
        {'id': 3, 'time': '2026-10-07T09:39:28.754Z', 'type': 'COMMISSION', 'amount': -2.1, 'asset': 'INR', 'symbol': 'KAITOINR'}]),
    '/v1/user-data/trade-history': lambda u: R(200, [{'id': 26260, 'time': '2026-10-07T09:39:41.675Z', 'symbol': 'KAITOINR', 'type': 'MARKET',
        'side': 'BUY', 'price': 29.6, 'quantity': 312, 'role': 'TAKER', 'fee': 1.2, 'realizedProfit': 0}]),
})
json.dump({'api_key': 'bitget-old-key-zzzzzzzz', 'delta_india': {'api_key': KD, 'api_secret': SD},
           'pi42': {'api_key': KP, 'api_secret': SPI}}, open(os.path.join(BASE, 'api_keys.json'), 'w'))
os.chmod(os.path.join(BASE, 'api_keys.json'), 0o600)
xv = types.SimpleNamespace(pairs={'KAITO': {}, 'IO': {}, 'LIT': {}})
bot = types.SimpleNamespace(cfg=cfg, c524x=xv)
ro = om.C540ReadOnly(bot)
LOG.clear()
ro.tick(now=T0)
d0 = [c for c in CALLS if 'india.delta' in c[0]]
u, h = d0[0]
ts = h.get('timestamp', '')
ok("Delta: headers api-key, timestamp in SECONDS, signature = HMAC-SHA256(secret, 'GET' + timestamp + path + query)",
   h.get('api-key') == KD and len(ts) == 10 and abs(int(ts) - T0) < 5
   and h['signature'] == hmac.new(SD.encode(), ('GET' + ts + '/v2/wallet/balances').encode(), hashlib.sha256).hexdigest()
   and u == 'https://api.india.delta.exchange/v2/wallet/balances' and 'User-Agent' in h, u)
u2, h2 = [c for c in d0 if '/v2/positions/margined' in c[0]][0]
q2 = u2.split('/v2/positions/margined')[1]
ok("  a query string is signed with its '?' exactly as sent", q2 == '?contract_types=perpetual_futures'
   and h2['signature'] == hmac.new(SD.encode(), ('GET' + h2['timestamp'] + '/v2/positions/margined' + q2).encode(), hashlib.sha256).hexdigest())
ok("  the docs' own example: GET open orders with ?product_id=1&state=open signs 'GET' + ts + '/v2/orders?product_id=1&state=open'",
   om._c540_delta_sign('s3cr3t', 'GET', '1700000000', '/v2/orders', '?product_id=1&state=open')
   == hmac.new(b's3cr3t', b'GET1700000000/v2/orders?product_id=1&state=open', hashlib.sha256).hexdigest())
p0 = [c for c in CALLS if 'fapi.pi42' in c[0]]
u3, h3 = p0[0]
q3 = u3.split('?', 1)[1]
ok("Pi42: headers api-key + signature = HMAC-SHA256(secret, the query string), timestamp in MILLISECONDS, marginAsset=INR",
   h3.get('api-key') == KP and u3.startswith('https://fapi.pi42.com/v1/wallet/futures-wallet/details?marginAsset=INR&timestamp=')
   and len(q3.split('timestamp=')[1]) == 13 and h3['signature'] == hmac.new(SPI.encode(), q3.encode(), hashlib.sha256).hexdigest(), u3)

print("\n3. WHAT IT READS")
st = ro.status()
dv, pv = st['venues']['delta_india'], st['venues']['pi42']
ok("Delta India: the USD wallet (empty wallets skipped), net equity, the open position (closed ones skipped)",
   dv['ok'] and dv['wallets'] == [dict(asset='USD', balance=512.35, available=480.1, margin=30.0)] and dv['equity'] == 515.0
   and [p['symbol'] for p in dv['positions']] == ['KAITOUSD'] and dv['positions'][0]['size'] == -312.0, json.dumps(dv)[:300])
ok("  the last 24 h of rent across two pages (+0.05 +0.04 +0.03), fills and their fees",
   abs(dv['rent_24h'] - 0.12) < 1e-9 and dv['rent_n'] == 3 and dv['fills_24h'] == 1 and dv['fees_24h'] == 0.02)
ok("Pi42: the INR wallet (balance, margin, free), the open position, rent and its GST apart, fills and fees",
   pv['ok'] and pv['inr'] == 1941.5 and pv['margin_inr'] == 1468.52 and pv['free_inr'] == 1468.5 and pv['upnl_inr'] == 1.25
   and pv['positions'][0]['coin'] == 'KAITO' and pv['positions'][0]['side'] == 'LONG' and pv['rent_24h_inr'] == 2.5
   and pv['gst_24h_inr'] == -0.1 and pv['by_type'].get('COMMISSION') == -2.1 and pv['fills_24h'] == 1 and pv['fees_24h_inr'] == 1.2,
   json.dumps(pv)[:300])
ok("beside the paper ledger: how many real positions are coins the paper holds (KAITO: 1 on each venue)",
   dv['in_paper'] == 1 and pv['in_paper'] == 1 and st['paper_pairs'] == 3 and st['live_locked'] is True)
li = [m for _, m in LOG if 'C540 real account' in m]
ok("the log: one line per venue in words, the paper ledger beside it, 'nothing is traded live'",
   len(li) == 2 and 'Delta India: USD 512.35, 1 position(s)' in li[0] and 'the paper ledger holds 3 pairs' in li[0]
   and 'Pi42: INR 1941.50' in li[1] and 'nothing is traded live' in li[1], li[0][:200] if li else '')
n0 = len(CALLS)
ro.tick(now=T0 + 60)
ok("read every 10 minutes, not every loop", len(CALLS) == n0)
ro.tick(now=T0 + 601)
ok("  and logged once an hour per venue (no repeat at the 10-minute read)", len(CALLS) > n0 and len([m for _, m in LOG if 'C540 real account' in m]) == 2)

print("\n4. KEYS: ONLY FROM api_keys.json, NEVER SHOWN")
blob = json.dumps(ro.status()) + ' '.join(m for _, m in LOG)
ok("the key and the secret never appear in the status (the page) or any log line", not any(k in blob for k in (KD, SD, KP, SPI)))
ok("they are read from BASE_PATH/api_keys.json (sections delta_india and pi42); the old top-level keys are left alone",
   "os.path.join(BASE_PATH, 'api_keys.json')" in SEC and set(om._c540_keys()[0]) == {'delta_india', 'pi42'})
ok("no key or secret is written in the Python file", not any(w in SEC for w in ("api_key = '", 'api_key = "', "api_secret = '", 'api_secret = "')))
os.chmod(os.path.join(BASE, 'api_keys.json'), 0o644)
LOG.clear(); ro._tick_at = 0; ro._said.pop('loose', None)
ro.tick(now=T0 + 7200)
ok("api_keys.json readable by other users: a warning to chmod 600 it (the key itself never printed)",
   any('readable by other users' in m and 'chmod 600' in m for _, m in LOG) and ro.status()['loose'] is True)
os.chmod(os.path.join(BASE, 'api_keys.json'), 0o600)

print("\n5. REFUSALS IN WORDS")
cases = [
    ('delta_india', R(401, {'success': False, 'error': {'code': 'UnauthorizedApiAccess'}}), "'Trading' permission"),
    ('delta_india', R(401, {'success': False, 'error': {'code': 'ip_not_whitelisted_for_api_key'}}), "IP address is not on this key's allowed list"),
    ('delta_india', R(401, {'success': False, 'error': {'code': 'SignatureExpired'}}), "clock is off"),
    ('delta_india', R(401, {'success': False, 'error': {'code': 'invalid_api_key'}}), 'does not know this key'),
    ('pi42', R(401, {'code': 401, 'message': 'Invalid api-key'}), 'Pi42 refused the key'),
    ('pi42', R(429, {'message': 'limit'}), 'too many requests'),
    ('pi42', R(403, ValueError('<html>403 Forbidden</html>')), "firewall answered instead of its API"),   # seen from a blocked network, 8 Oct
]
okc = []
for v, resp, want in cases:
    path = '/v2/wallet/balances' if v == 'delta_india' else '/v1/wallet/futures-wallet/details'
    saved = dict(ROUTES); ROUTES.clear(); ROUTES[path] = (lambda r: (lambda u: r))(resp)
    ro.snap.clear(); ro._tick_at = 0; ro._said.clear(); LOG.clear()
    ro.tick(now=T0 + 10000)
    s_ = ro.status()['venues'][v]
    okc.append(s_.get('ok') is False and want in s_.get('error', '') and any(want in m for _, m in LOG))
    ROUTES.clear(); ROUTES.update(saved)
ok("Delta: no permission / IP not allowed / clock / unknown key; Pi42: refused / too many requests / a firewall page -- each said plainly",
   all(okc), str(okc))


def boom(u):
    raise ConnectionError('host unreachable https://fapi.pi42.com?signature=abc')


ROUTES['/v1/wallet/futures-wallet/details'] = boom
ro.snap.clear(); ro._tick_at = 0; ro._said.clear(); LOG.clear()
ro.tick(now=T0 + 20000)
e_ = ro.status()['venues']['pi42'].get('error', '')
ok("a network failure: 'not reached (ConnectionError)', never the URL, the signature or the exception text",
   e_.startswith('not reached (ConnectionError)') and 'signature' not in e_ and 'http' not in e_, e_)
os.remove(os.path.join(BASE, 'api_keys.json'))
n1 = len(CALLS); ro._tick_at = 0
ro.tick(now=T0 + 30000)
ok("no keys: nothing is called, and the page says 'not connected'", len(CALLS) == n1
   and ro.status()['venues']['pi42'] == {'connected': False} and ro.status()['venues']['delta_india'] == {'connected': False})

print("\n6. THE LOGS PUSH REDACTS EVERY KEY BY ITS LITERAL TEXT")
W = tempfile.mkdtemp(prefix='c540_scrub_')
kf = os.path.join(W, 'api_keys.json'); lg_ = os.path.join(W, 'logs'); os.makedirs(lg_)
json.dump({'delta_india': {'api_key': KD, 'api_secret': SD}, 'pi42': {'api_key': KP, 'api_secret': SPI}}, open(kf, 'w'))
open(os.path.join(lg_, 'a.log'), 'w').write(f"x {SD} y\nheaders {{'x': '{KP}'}}\n")
open(os.path.join(lg_, 'b.log.1.gz'), 'wb').write(gzip.compress(f"old line with {SPI} inside\n".encode()))
open(os.path.join(lg_, 'c.json'), 'w').write('{"clean": true}')
r_ = subprocess.run([sys.executable, os.path.join(REPO, 'deploy', 'omega-scrub-keys.py'), kf, lg_], capture_output=True, text=True)
a_ = open(os.path.join(lg_, 'a.log')).read(); b_ = gzip.decompress(open(os.path.join(lg_, 'b.log.1.gz'), 'rb').read()).decode()
ok("every value in api_keys.json is redacted wherever it sits -- no label needed, gzip-rotated logs included",
   r_.returncode == 0 and SD not in a_ and KP not in a_ and a_.count('<KEY-REDACTED>') == 2 and SPI not in b_
   and '<KEY-REDACTED>' in b_ and open(os.path.join(lg_, 'c.json')).read() == '{"clean": true}', r_.stdout.strip())
ok("  it prints counts only, never a value", not any(k in r_.stdout + r_.stderr for k in (KD, SD, KP, SPI)))
open(kf, 'w').write('{not json')
r2 = subprocess.run([sys.executable, os.path.join(REPO, 'deploy', 'omega-scrub-keys.py'), kf, lg_], capture_output=True, text=True)
ok("  an unreadable api_keys.json stops the push (exit 3)", r2.returncode == 3)
LP = open(os.path.join(REPO, 'deploy', 'omega-logpush.sh')).read()
ok("  the push script runs it after the label scrub and refuses to push on any failure, or if it is missing",
   'omega-scrub-keys.py" "$KEYS_JSON" "$WT/logs"' in LP and 'could not be scrubbed — refusing to push' in LP
   and 'is missing — refusing to push' in LP and LP.index('omega-scrub-keys.py') < LP.index('git add -A -f logs')
   and 'api_keys.json' not in LP[LP.index('for f in "$REPO"/data/mode_v60.json'):LP.index('[ "$copied" -gt 0 ] || exit 0')])
r3 = subprocess.run(['bash', '-n', os.path.join(REPO, 'deploy', 'omega-logpush.sh')], capture_output=True)
ok("  the push script still parses", r3.returncode == 0)

print("\n7. PUTTING A KEY IN WITHOUT SHOWING IT")
KB = tempfile.mkdtemp(prefix='c540_keys_')
json.dump({'delta_india': {'api_key': 'keep-this-key-123', 'api_secret': 'keep-this-secret-456'}}, open(os.path.join(KB, 'api_keys.json'), 'w'))
r4 = subprocess.run(['bash', os.path.join(REPO, 'deploy', 'omega-keys.sh'), 'pi42'], input='PIKEY_abcdefgh1234\nPISECRET_zyxw98765\n',
                    capture_output=True, text=True, env=dict(os.environ, OMEGA_BASE_PATH=KB))
kj = json.load(open(os.path.join(KB, 'api_keys.json')))
mode = os.stat(os.path.join(KB, 'api_keys.json')).st_mode & 0o777
ok("deploy/omega-keys.sh pi42: hidden prompts, merged under 'pi42', the other section kept, chmod 600",
   r4.returncode == 0 and kj['pi42'] == {'api_key': 'PIKEY_abcdefgh1234', 'api_secret': 'PISECRET_zyxw98765'}
   and kj['delta_india']['api_key'] == 'keep-this-key-123' and mode == 0o600, r4.stdout.strip()[-160:] + r4.stderr[-200:])
ok("  it shows only how many characters it saved, never the key or the secret",
   'PIKEY_abcdefgh1234' not in r4.stdout + r4.stderr and 'PISECRET_zyxw98765' not in r4.stdout + r4.stderr and '18 characters' in r4.stdout)
r5 = subprocess.run(['bash', os.path.join(REPO, 'deploy', 'omega-keys.sh'), 'binance'], input='', capture_output=True, text=True,
                    env=dict(os.environ, OMEGA_BASE_PATH=KB))
ok("  only delta_india or pi42", r5.returncode == 2 and 'usage' in r5.stdout)

print("\n8. THE PAGE")
for f in glob.glob(os.path.join(BASE, 'c5*.json')):
    os.remove(f)
for f in glob.glob(os.path.join(SNAP, 'c*.json')):
    shutil.copy(f, BASE)
cfg.C524_XVENUE_EQUITY = 1000.0
om._c532_pi42_coins = lambda: None
L = lambda f: json.load(open(os.path.join(SNAP, f + '.json')))
PX = L('prices'); bk0 = L('c488_book')
pf = om.Portfolio(cfg)
cash = bk0['born']['eq'] + sum(c['pnl'] for c in bk0['closed']) + sum(p['funding'] - p['fees'] + p['realized'] for p in bk0['book'].values())
pf.equity = pf.available_balance = cash
bt = types.SimpleNamespace(cfg=cfg, portfolio=pf, _c462_state_settled=True, _c408_asset_class=lambda s: 'crypto',
                           exchange=types.SimpleNamespace(markets={}, get_current_price=lambda s: None),
                           _c482_risk_guard=lambda: {'pct': 20.0, 'month_eq0': 500.0, 'month_budget': 100.0, 'month_used': 0.0,
                                                     'day_cap': 25.0, 'day_used': 0.0, 'halt': ''},
                           _c504_data_health=lambda now=None: {'ok': True, 'bits': [], 'late': [], 'keys': []})
e = om.C488Engine(bt); bt.c488 = e; pf._c488 = e; e.load()
pf.get_live_equity = lambda ex: pf.equity + e.unrealized()
pf.session_start_equity = 500.0; pf.positions = om.PositionsManager()
for a, k in (('c501v', 'C501Savings'), ('c501s', 'C501Spot'), ('c490', 'C490Carry'), ('c521d', 'C521Delta'), ('c521b', 'C521Bfusd'),
             ('c524x', 'C524CrossVenue'), ('c530p', 'C530Pendle'), ('c489', 'C489Shadow'), ('c501k', 'C501Allostatic'),
             ('c510t', 'C510Tournament')):
    setattr(bt, a, getattr(om, k)(bt))
bt.c538 = [om.C538TestRule(bt, k) for k in ('f8', 'w3')]
bt.c540 = om.C540ReadOnly(bt)
NOWs = time.time()
e.marks = {om.C488Engine._ccxt(s): dict(bid=b, ask=a, last=(b + a) / 2, fr=0.0, vol=1e9) for s, (b, a) in PX['perp'].items()}
e._marks_at = NOWs
bt.c501s.bk = {s: (b, a) for s, (b, a) in PX['spot'].items()}; bt.c501s._book_at = NOWs
bt.c521d.marks = {s: dict(mark=m_, bid=b or m_, ask=a or m_, fr=0.0) for s, (m_, b, a) in PX['delta'].items()}
bt.c521d._marks_at = NOWs
e.refresh_marks = lambda force=False: True
bt.c521d.refresh_marks = lambda force=False: True
bt.c501s.book = lambda force=False: bt.c501s.bk
fbot = types.SimpleNamespace(cfg=cfg, portfolio=pf, c488=e, c501s=bt.c501s, c501v=bt.c501v, c501k=bt.c501k,
                             c489=bt.c489, c490=bt.c490, c510t=bt.c510t, c521b=bt.c521b, c521d=bt.c521d, c524x=bt.c524x,
                             c530p=bt.c530p, c538=bt.c538, c540=bt.c540,
                             mode_mgr=types.SimpleNamespace(mode=types.SimpleNamespace(value='normal')), exchange=bt.exchange,
                             _c467_day_barrier=lambda: {'pnl': 0.0, 'limit': 9.0, 'used': 0.0, 'frac': 0.0},
                             _c482_risk_guard=bt._c482_risk_guard, _c504_data_health=bt._c504_data_health)


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
        pg.evaluate("document.querySelectorAll('details').forEach(function(x){x.open=true})"); pg.wait_for_timeout(200)
        G = dict(acc=pg.inner_text('#s-acc'), real=pg.inner_text('#realacc'), W=pg.evaluate('document.documentElement.scrollWidth'),
                 html=pg.content())
        br.close()
    return G, errs


try:
    G0, er0 = page()
    ok("no keys yet: one plain line under your two accounts, and where the guide is",
       'Your real exchange accounts: not connected yet' in G0['acc'] and 'reports/2026-10-08_b1_read_only.md' in G0['real'], G0['acc'][-200:])
    json.dump({'delta_india': {'api_key': KD, 'api_secret': SD}, 'pi42': {'api_key': KP, 'api_secret': SPI}},
              open(os.path.join(BASE, 'api_keys.json'), 'w'))
    os.chmod(os.path.join(BASE, 'api_keys.json'), 0o600)
    ROUTES['/v1/wallet/futures-wallet/details'] = lambda u: R(200, {'walletBalance': '1941.50', 'marginBalance': '1468.52',
                                                                    'withdrawableBalance': '1468.50', 'marginAsset': 'INR'})
    bt.c540._tick_at = 0
    bt.c540.tick()
    G1, er1 = page()
    ok("connected: 'Your real accounts (read-only): Delta India USD 512.35 · 1 position · Pi42 ₹1,941.50 · 1 position'",
       'Your real accounts (read-only): Delta India USD 512.35' in G1['acc'] and '₹1,941.50' in G1['acc']
       and 'Nothing is traded with real money yet' in G1['acc'], G1['acc'][-260:])
    ok("  'Your plan in detail' shows each account, its positions and whether the paper holds them, rent and its GST, fills",
       'Delta India: balance USD 512.35 (net equity 515.00)' in G1['real'] and 'KAITOUSD' in G1['real'] and 'of them in the paper ledger' in G1['real']
       and 'GST ₹-0.10' in G1['real'] and 'GET requests only: the bot cannot place, change or cancel anything' in G1['real'], G1['real'][:400])
    ok("  the page never carries a key or a secret", not any(k in G1['html'] for k in (KD, SD, KP, SPI)))
    ROUTES['/v2/wallet/balances'] = lambda u: R(401, {'success': False, 'error': {'code': 'UnauthorizedApiAccess'}})
    bt.c540._tick_at = 0
    bt.c540.tick()
    G2, er2 = page()
    ok("a refusal shows in words where you look (here: Delta wants the Trading permission to read wallets)",
       "Delta India: not read" in G2['acc'] and "'Trading' permission" in G2['real'], G2['acc'][-200:])
    ok("412 px, no JavaScript errors", max(G0['W'], G1['W'], G2['W']) <= 412 and not (er0 + er1 + er2), str(er0 + er1 + er2)[:200])
except Exception as ex:
    import traceback; traceback.print_exc()
    ok("page check ran", False, f"{type(ex).__name__}: {ex}")

print("\n" + "=" * 66)
print(f"C540 TEST: {'ALL PASS' if not fails else f'{len(fails)} FAIL'}")
shutil.rmtree(BASE, ignore_errors=True); shutil.rmtree(W, ignore_errors=True); shutil.rmtree(KB, ignore_errors=True)
sys.exit(1 if fails else 0)
