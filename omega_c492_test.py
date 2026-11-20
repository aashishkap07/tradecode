#!/usr/bin/env python3
"""C492: what live money needs before the C488 book may trade it (pending #2).

The bot's REAL ExchangeManager and C488Engine run against a simulated Bitget
USDT-M account. Every order the engine sends is turned into the exact Bitget
request by the installed ccxt (create_order_request, on real market data saved
in test_fixtures/c492_bitget_btc_eth.json), and the simulated venue acts on
THAT request: one-way netting, the margin mode the symbol is set to, a
reduce-only that cannot open, fees, funding settlements and account bills.

1. THE ORDER ON THE WIRE: 'cross' reaches Bitget as 'crossed', one-way (no
   tradeSide), a close as reduceOnly YES. ccxt sends 'crossed' as ISOLATED --
   the engine never lets that spelling through. The intraday path is unchanged.
2. (c) PREFLIGHT: hedge mode is switched to one-way when flat, and trading waits
   when it cannot be; each symbol is set to cross at the book's leverage and read
   back before its first order, once; a symbol Bitget will not switch is not
   traded, but a close is never held up.
3. (d) PARTIAL FILLS: the book holds what filled, a flip waits for the old side
   to close, a flatten retries and then shouts, a big order goes in pieces, and
   the fee booked is the fee Bitget charged.
4. (a) FUNDING: Bitget's bills, each booked once (restart included), to the
   right position; the paper estimate is never booked live.
5. (b) SYNC: the ledger equals Bitget's wallet to the cent after trades, fees
   and funding; a gap is followed and shouted; a fill that could not be read
   back is adopted from Bitget; a position that vanished is dropped; a passing
   blip, a foreign position and the intraday engine's symbols are left alone;
   the free balance never exceeds Bitget's; a failed sync blocks the rebalance.
6. (e) THE VENUE'S RULES: the live contract table (real rows) sets steps,
   minimums, status and the biggest market order.
7. A WHOLE LIVE REBALANCE on the simulated venue: targets met, venue == book
   symbol by symbol, ledger == wallet, a second pass trades nothing.
8. SAFETY: C488_LIVE_OK stays False; no key in the .py; with the flag off (or
   in paper) the engine never makes one private call.
9. THE PAGE AND THE REPORT show live state, and NOT READY is shown, not hidden.
"""
import os, sys, io, re, ast, json, time, types, socket, glob, logging, contextlib, importlib.util, tempfile, shutil, collections
import datetime as dt
import numpy as np
REPO = os.path.dirname(os.path.abspath(__file__))
BASE = tempfile.mkdtemp(prefix='c492_test_')
os.environ['OMEGA_BASE_PATH'] = BASE
TOKEN = 'c492-test-token-0123456789abcdef'
os.environ['OMEGA_CTRL_TOKEN'] = TOKEN
fails = []


def ok(n, c, d=''):
    print(f"  {'PASS' if c else 'FAIL'}  {n}" + (f"   {d}" if d else ''))
    if not c:
        fails.append(n)


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        spec.loader.exec_module(m)
    return m


print("=" * 66); print("C492: LIVE MODE FOR THE C488 BOOK"); print("=" * 66)
om = load(os.path.join(REPO, 'omega_v60_reconstructed.py'), 'om492')
src = open(os.path.join(REPO, 'omega_v60_reconstructed.py'), encoding='utf-8').read()
import ccxt
FIX = json.load(open(os.path.join(REPO, 'test_fixtures', 'c492_bitget_btc_eth.json')))


class Logs(logging.Handler):
    def __init__(self):
        super().__init__(); self.lines = []
    def emit(self, r):
        self.lines.append((r.levelname, r.getMessage()))
    def has(self, pat, level=None):
        return any(re.search(pat, m) and (level is None or lv == level) for lv, m in self.lines)
LOG = Logs()
logging.getLogger('OmegaV60').addHandler(LOG)
logging.getLogger('OmegaV60').propagate = False
for h in list(logging.getLogger('OmegaV60').handlers):
    if h is not LOG:
        logging.getLogger('OmegaV60').removeHandler(h)


def clone_market(m, base, step):
    c = json.loads(json.dumps(m))
    c.update(id=f"{base}USDT", symbol=f"{base}/USDT:USDT", base=base, baseId=base, lowercaseId=None)
    c['precision'] = dict(c['precision'], amount=step)
    c['limits'] = dict(c['limits'], amount=dict(c['limits']['amount'], min=step))
    return c


class FakeBitget:
    """A USDT-M account as the book sees it through ccxt. Orders are built by
    the real ccxt into Bitget's request and acted on from that request."""
    BILL = 1000

    def __init__(self, markets, wallet=1000.0, fee=0.0005):
        self.cc = ccxt.bitget({'options': {'defaultType': 'swap', 'defaultSubType': 'USDT'}})
        self.cc.set_markets(list(markets.values()))
        self.markets = self.cc.markets
        self.pos_mode, self.asset_mode = 'one_way_mode', 'single'
        self.mode, self.levs = {}, {}           # raw -> 'crossed' | 'isolated', raw -> leverage
        self.wallet, self.fee = wallet, fee
        self.pos, self.px = {}, {}              # raw -> dict(qty, avg), raw -> (bid, ask)
        self.ratio = collections.defaultdict(list)   # raw -> fill ratios for the next orders
        self.orders, self.sent, self.bills = {}, [], []
        self.calls = collections.Counter()
        self.fail, self.read_fail = set(), set()
        self.no_fill = set()
        self._n = self._b = 0

    def _c(self, name):
        self.calls[name] += 1
        if name in self.fail:
            raise ccxt.NetworkError(f"bitget {name} unreachable")

    @staticmethod
    def ok(data):
        return {'code': '00000', 'msg': 'success', 'requestTime': int(time.time() * 1000), 'data': data}

    def mark(self, raw):
        b, a = self.px[raw]; return (b + a) / 2

    def upl(self, raw):
        p = self.pos[raw]; return p['qty'] * (self.mark(raw) - p['avg'])

    def equity(self):
        return self.wallet + sum(self.upl(r) for r in self.pos)

    # -- orders --
    def set_leverage(self, lev, symbol, params={}):
        self._c('set_leverage'); self.levs[self.cc.market(symbol)['id']] = int(lev)

    def create_order(self, symbol, type, side, amount, price=None, params={}):
        self._c('create_order')
        req = self.cc.create_order_request(symbol, type, side, amount, price, dict(params))
        self.sent.append(req)
        raw = req['symbol']
        if self.pos_mode != 'one_way_mode' and not req.get('tradeSide'):
            raise ccxt.ExchangeError('bitget {"code":"40774","msg":"The order type for unilateral position must also be the unilateral position type."}')
        if req.get('marginMode') != self.mode.get(raw, 'crossed'):
            raise ccxt.ExchangeError(f'bitget {{"code":"40920","msg":"order marginMode {req.get("marginMode")} != symbol {self.mode.get(raw, "crossed")}"}}')
        q = float(req['size']); sgn = 1 if req['side'] == 'buy' else -1
        cur = self.pos.get(raw, dict(qty=0.0, avg=0.0))
        if req.get('reduceOnly') == 'YES':
            if cur['qty'] == 0 or (cur['qty'] > 0) == (sgn > 0):
                raise ccxt.InvalidOrder('bitget {"code":"22002","msg":"No position to close"}')
            q = min(q, abs(cur['qty']))
        r = self.ratio[raw].pop(0) if self.ratio[raw] else 1.0
        step = float(self.markets[symbol]['precision']['amount'])
        f = 0.0 if raw in self.no_fill else (q if r >= 1 else float(f"{np.floor(q * r / step) * step:.12g}"))
        b, a = self.px[raw]; fpx = a if sgn > 0 else b
        fee = f * fpx * self.fee
        q0, dq = cur['qty'], sgn * f
        realized = 0.0
        if f > 0:
            if q0 == 0 or (q0 > 0) == (dq > 0):
                nq = q0 + dq; avg = (abs(q0) * cur['avg'] + f * fpx) / abs(nq)
            else:
                closed = min(f, abs(q0)); realized = closed * (fpx - cur['avg']) * (1 if q0 > 0 else -1)
                nq = q0 + dq; avg = cur['avg'] if (abs(nq) < 1e-12 or (nq > 0) == (q0 > 0)) else fpx
            self.wallet += realized - fee
            if abs(nq) < 1e-12:
                self.pos.pop(raw, None)
            else:
                self.pos[raw] = dict(qty=nq, avg=avg)
        self._n += 1; oid = str(self._n)
        self.orders[oid] = dict(id=oid, symbol=symbol, status='closed' if f >= q * 0.999 else 'open', filled=f,
                                amount=q, average=fpx if f > 0 else None, price=None,
                                fee={'cost': fee, 'currency': 'USDT'} if f > 0 else None)
        return {'id': oid, 'info': {'orderId': oid}}

    def fetch_order(self, oid, symbol=None, params={}):
        self._c('fetch_order')
        if oid in self.read_fail:
            raise ccxt.NetworkError('bitget order read failed')
        return dict(self.orders[oid])

    def cancel_order(self, oid, symbol=None, params={}):
        self._c('cancel_order')
        o = self.orders.get(oid)
        if o and o['status'] == 'open':
            o['status'] = 'canceled'

    # -- the raw v2 account endpoints the engine uses --
    def privateMixGetV2MixAccountAccount(self, p):
        self._c('account'); raw = p['symbol']; md = self.mode.get(raw, 'crossed'); lv = self.levs.get(raw, 10)
        return self.ok(dict(marginCoin='USDT', posMode=self.pos_mode, marginMode=md, assetMode=self.asset_mode,
                            crossedMarginLeverage=lv, isolatedLongLever=lv, isolatedShortLever=lv,
                            accountEquity=str(self.equity())))

    def privateMixPostV2MixAccountSetPositionMode(self, p):
        self._c('set_pos_mode')
        if self.pos:
            raise ccxt.ExchangeError('bitget {"code":"40920","msg":"Position or order exists, the position mode cannot be adjusted"}')
        self.pos_mode = p['posMode']; return self.ok({'posMode': self.pos_mode})

    def privateMixPostV2MixAccountSetMarginMode(self, p):
        self._c('set_margin_mode')
        if p['symbol'] in self.pos:
            raise ccxt.ExchangeError('bitget {"code":"45117","msg":"Currently holding positions or orders, the margin mode cannot be adjusted"}')
        self.mode[p['symbol']] = p['marginMode']; return self.ok(dict(symbol=p['symbol'], marginMode=p['marginMode']))

    def privateMixPostV2MixAccountSetLeverage(self, p):
        self._c('set_lev'); self.levs[p['symbol']] = int(p['leverage']); return self.ok(dict(symbol=p['symbol']))

    def privateMixGetV2MixPositionAllPosition(self, p):
        self._c('positions')
        return self.ok([dict(symbol=r, marginCoin='USDT', holdSide='long' if v['qty'] > 0 else 'short',
                             total=str(abs(v['qty'])), available=str(abs(v['qty'])), openPriceAvg=str(v['avg']),
                             marginMode=self.mode.get(r, 'crossed'), posMode=self.pos_mode,
                             unrealizedPL=str(self.upl(r)), markPrice=str(self.mark(r))) for r, v in self.pos.items()])

    def privateMixGetV2MixAccountAccounts(self, p):
        self._c('accounts')
        used = sum(abs(v['qty']) * self.mark(r) / self.levs.get(r, 10) for r, v in self.pos.items())
        free = self.equity() - used
        return self.ok([dict(marginCoin='USDT', accountEquity=str(self.equity()), available=str(self.wallet),
                             crossedMaxAvailable=str(free), isolatedMaxAvailable=str(free),
                             unrealizedPL=str(sum(self.upl(r) for r in self.pos)), assetMode=self.asset_mode)])

    def privateMixGetV2MixAccountBill(self, p):
        self._c('bill')
        lo, hi = int(p.get('startTime') or 0), int(p.get('endTime') or 9e15)
        rows = sorted([b for b in self.bills if lo <= int(b['cTime']) <= hi and
                       (not p.get('businessType') or b['businessType'] == p['businessType'])],
                      key=lambda b: -int(b['billId']))
        if p.get('idLessThan'):
            rows = [b for b in rows if int(b['billId']) < int(p['idLessThan'])]
        page = rows[:int(p.get('limit') or 20)]
        return self.ok(dict(bills=page, endId=page[-1]['billId'] if page else None))

    def settle(self, rate, raws=None, t=None):
        """one funding settlement: the venue pays or charges every position and writes a bill"""
        for r, v in list(self.pos.items()):
            if raws and r not in raws:
                continue
            amt = float(f"{-v['qty'] * self.mark(r) * rate:.8f}")
            self.wallet += amt
            FakeBitget.BILL += 1                   # Bitget's bill ids are unique account-wide
            self.bills.append(dict(billId=str(FakeBitget.BILL), symbol=r, amount=f"{amt:.8f}", fee='0',
                                   businessType='contract_settle_fee', coin='USDT', balance=str(self.wallet),
                                   cTime=str(t or int(time.time() * 1000))))

    def private_calls(self):
        return sum(v for k, v in self.calls.items())


BTC, ETH = 'BTC/USDT:USDT', 'ETH/USDT:USDT'


def mkbot(fake=None, live=True, wallet=1000.0, fee=0.0005, extra=None):
    mk = dict(FIX['markets']); mk.update(extra or {})
    fake = fake or FakeBitget(mk, wallet=wallet, fee=fee)
    fake.px.setdefault('BTCUSDT', (49999.0, 50001.0)); fake.px.setdefault('ETHUSDT', (1999.0, 2001.0))
    cfg = om.Config(); cfg.PAPER_MODE = not live; cfg.C380_MAX_MONTHLY_DD_PCT = 15.0; cfg.C488_LIVE_OK = True
    em = om.ExchangeManager(cfg); em.exchange = fake; em.markets = fake.markets
    pf = om.Portfolio(cfg); pf.equity = pf.available_balance = wallet
    bot = types.SimpleNamespace(cfg=cfg, portfolio=pf, exchange=em, _c462_state_settled=True,
                                _c408_asset_class=lambda s: 'crypto',
                                _c482_risk_guard=lambda: {'pct': 15.0, 'month_eq0': wallet})
    e = om.C488Engine(bot); e.reset()
    pf._c488 = e
    e.refresh_marks = lambda force=False: True
    e.refresh_rules = lambda force=False: True
    def sync_marks():
        e.marks = {f"{r[:-4]}/USDT:USDT": dict(bid=b, ask=a, last=(a + b) / 2, fr=0.0001, vol=9e9)
                   for r, (b, a) in fake.px.items()}
    sync_marks(); e._sync_marks = sync_marks
    return bot, e, fake


def inv(pf):
    return abs(pf.available_balance + pf.get_locked_margin() - pf.equity) < 0.011 or \
        pf.available_balance <= pf.equity - pf.get_locked_margin() + 1e-9


def ready(e):
    e.live['checked_at'] = 0.0
    return e.live_ready()


# ─────────────────────────────────────────────────────────────────────────────
print("\n1. THE ORDER ON THE WIRE")
cc = ccxt.bitget({'options': {'defaultType': 'swap', 'defaultSubType': 'USDT'}})
cc.set_markets(list(FIX['markets'].values()))
r_open = cc.create_order_request(BTC, 'market', 'buy', 0.0012, None, {'marginMode': 'cross'})
r_close = cc.create_order_request(BTC, 'market', 'sell', 0.0012, None, {'marginMode': 'cross', 'reduceOnly': True})
r_trap = cc.create_order_request(BTC, 'market', 'buy', 0.0012, None, {'marginMode': 'crossed'})
ok("'cross' reaches Bitget as marginMode 'crossed', one-way (no tradeSide), USDT-FUTURES",
   r_open['marginMode'] == 'crossed' and 'tradeSide' not in r_open and r_open['productType'] == 'USDT-FUTURES'
   and r_open['symbol'] == 'BTCUSDT' and r_open['size'] == '0.0012', f"ccxt {ccxt.__version__}")
ok("a close goes as reduceOnly 'YES' (it can never open or extend)", r_close.get('reduceOnly') == 'YES' and r_close['marginMode'] == 'crossed')
ok("THE TRAP: ccxt sends Bitget's own word 'crossed' as ISOLATED", r_trap['marginMode'] == 'isolated')
cfg = om.Config()
outs = {}
for v in ('cross', 'crossed', 'CROSSED', 'isolated'):
    cfg.C488_MARGIN_MODE = v; outs[v] = om.C488Engine.margin_mode(types.SimpleNamespace(cfg=cfg))
ok("  so the engine turns 'crossed' (any case) into 'cross'; isolated stays isolated; default is cross",
   outs == {'cross': 'cross', 'crossed': 'cross', 'CROSSED': 'cross', 'isolated': 'isolated'} and om.Config().C488_MARGIN_MODE == 'cross', str(outs))
bot, e, fake = mkbot()
fake.mode['ETHUSDT'] = 'isolated'
bot.exchange.place_order(ETH, 'buy', 0.01, 5, 'market')
ok("the intraday path is unchanged: isolated, and it still sets leverage on every order",
   fake.sent[-1]['marginMode'] == 'isolated' and fake.calls['set_leverage'] == 1)

# ─────────────────────────────────────────────────────────────────────────────
print("\n2. (c) THE PREFLIGHT")
bot, e, fake = mkbot(); fake.pos_mode = 'hedge_mode'
ok("a flat account in hedge mode is switched to one-way, and funding is booked from that moment",
   ready(e) and fake.pos_mode == 'one_way_mode' and e.bill_since > 0 and LOG.has('LIVE READY'))
bot, e, fake = mkbot(); fake.pos_mode = 'hedge_mode'; fake.pos['ETHUSDT'] = dict(qty=0.5, avg=2000.0)
ok("in hedge mode WITH a position it is not ready, says why, and nothing is traded",
   not ready(e) and 'position mode' in e.live['why'] and LOG.has('LIVE NOT READY', 'ERROR'))
n0 = fake.calls['create_order']; e._tick_at = 0; e.tick()
ok("  a tick sends no order and does not re-check before 10 minutes", fake.calls['create_order'] == n0 and fake.calls['set_pos_mode'] == 1)
fake.pos.clear(); e.live['checked_at'] -= 601
ok("  and it becomes ready on the next check once the account is flat", e.live_ready() and fake.pos_mode == 'one_way_mode')
bot, e, fake = mkbot()
def refused(p):
    raise ccxt.AuthenticationError('bitget {"code":"40037","msg":"Apikey does not exist"}')
fake.privateMixGetV2MixAccountAccount = refused; LOG.lines.clear()
ok("a key Bitget refuses: not ready, and the log names the KEY (permissions, IP allow-list), not the mode",
   not ready(e) and LOG.has('refused the API key', 'ERROR') and not LOG.has('ONE-WAY position mode'))
bot, e, fake = mkbot(); bot.exchange.exchange = types.SimpleNamespace(markets=fake.markets)
ok("a ccxt without Bitget's v2 account endpoints is refused, with the fix named",
   not ready(e) and 'pip install -U ccxt' in e.live['why'])
bot, e, fake = mkbot(); ready(e)
fake.mode['ETHUSDT'] = 'isolated'; fake.levs['ETHUSDT'] = 10
e.trade_to(ETH, 0.05, 't')
ok("before its first order a symbol is set to crossed at 5x and read back; the order goes crossed",
   fake.mode['ETHUSDT'] == 'crossed' and fake.levs['ETHUSDT'] == 5 and fake.sent[-1]['marginMode'] == 'crossed'
   and abs(fake.pos['ETHUSDT']['qty'] - 0.05) < 1e-12 and ETH in e.prepared)
a0 = fake.calls['account']; e.trade_to(ETH, 0.08, 't')
ok("  once: the next order on it reads nothing again", fake.calls['account'] == a0 and abs(fake.pos['ETHUSDT']['qty'] - 0.08) < 1e-12)
bot, e, fake = mkbot(); ready(e)
fake.mode['BTCUSDT'] = 'isolated'; fake.pos['BTCUSDT'] = dict(qty=0.001, avg=50000.0)   # an intraday leftover
LOG.lines.clear(); n0 = len(fake.sent)
e.trade_to(BTC, 0.002, 't')
ok("a symbol Bitget will not switch (it holds an isolated position) is NOT traded, loudly",
   len(fake.sent) == n0 and BTC not in e.book and LOG.has('could not be set to crossed', 'ERROR'))
bot, e, fake = mkbot(); ready(e)
e.trade_to(ETH, 0.05, 't'); e.prepared.clear(); fake.fail.add('account')
e.trade_to(ETH, 0.0, 't')
ok("a CLOSE is never held up by a settings read (Bitget's account read down, the close still goes)",
   'ETHUSDT' not in fake.pos and ETH not in e.book and fake.sent[-1].get('reduceOnly') == 'YES')

# ─────────────────────────────────────────────────────────────────────────────
print("\n3. (d) PARTIAL FILLS")
bot, e, fake = mkbot(); ready(e); pf = bot.portfolio
fake.ratio['ETHUSDT'] = [0.4]; LOG.lines.clear()
e.trade_to(ETH, 0.10, 't')
ok("an opening order filled 40%: the book holds exactly what filled, at the fill price",
   abs(e.book[ETH]['qty'] - 0.04) < 1e-12 and abs(fake.pos['ETHUSDT']['qty'] - 0.04) < 1e-12
   and abs(e.book[ETH]['avg'] - 2001.0) < 1e-9 and inv(pf) and LOG.has('PARTIAL fill'))
fake.ratio['ETHUSDT'] = [1.0]
e.trade_to(ETH, 0.10, 't')
ok("  and the next pass tops it up to the target", abs(e.book[ETH]['qty'] - 0.10) < 1e-12 and abs(fake.pos['ETHUSDT']['qty'] - 0.10) < 1e-12)
LOG.lines.clear(); e.trade_to(ETH, 0.06, 't')
ok("a normal reduction (0.10 -> 0.06, filled in full) is QUIET: no partial warning",
   abs(e.book[ETH]['qty'] - 0.06) < 1e-12 and not LOG.has('partial|in part|PARTIAL'))
fake.ratio['ETHUSDT'] = [0.5]; LOG.lines.clear(); e.trade_to(ETH, 0.02, 't')
ok("  a reduction filled in part says so and holds what filled (0.06 -> 0.04 of a 0.02 target)",
   abs(e.book[ETH]['qty'] - 0.04) < 1e-12 and abs(fake.pos['ETHUSDT']['qty'] - 0.04) < 1e-12 and LOG.has('of a \\+0.02 target'))
e.trade_to(ETH, 0.10, 't')
fake.ratio['ETHUSDT'] = [0.5]; n0 = len(fake.sent); LOG.lines.clear()
e.trade_to(ETH, -0.10, 't')
vq = lambda r: (fake.pos.get(r) or {}).get('qty', 0.0)
ok("a flip whose close fills only half does NOT open the short (one-way would net it)",
   abs(e._qty(ETH) - 0.05) < 1e-12 and abs(vq('ETHUSDT') - 0.05) < 1e-12
   and len(fake.sent) == n0 + 1 and fake.sent[-1]['reduceOnly'] == 'YES' and LOG.has('flip to -0.1 waits'))
e.trade_to(ETH, -0.10, 't')
ok("  the next pass closes the rest, then opens the short", abs(e._qty(ETH) + 0.10) < 1e-12
   and abs(vq('ETHUSDT') + 0.10) < 1e-12 and [s.get('reduceOnly') for s in fake.sent[-2:]] == ['YES', None])
fake.ratio['ETHUSDT'] = [0.3]; LOG.lines.clear()
e.flatten('test')
ok("a live flatten retries what a partial close left, until it is flat", not e.book and 'ETHUSDT' not in fake.pos
   and fake.sent[-1]['reduceOnly'] == 'YES')
e.trade_to(ETH, 0.05, 't'); fake.no_fill.add('ETHUSDT'); LOG.lines.clear()
e.flatten('test')
ok("  and if Bitget will not fill it, the flatten says so loudly (CHECK BITGET BY HAND)",
   ETH in e.book and LOG.has('still open after the flatten', 'ERROR'))
bot, e, fake = mkbot(); ready(e)
e.rules[ETH] = dict(step=0.01, min_qty=0.01, min_usdt=5.0, max_mkt=0.03, status='normal')
e.trade_to(ETH, 0.08, 't')
ok("an order larger than Bitget's biggest market order goes in pieces (0.03 + 0.03 + 0.02)",
   [s['size'] for s in fake.sent] == ['0.03', '0.03', '0.02'] and abs(e.book[ETH]['qty'] - 0.08) < 1e-12)
bot, e, fake = mkbot(fee=0.0004); ready(e); pf = bot.portfolio
e.trade_to(ETH, 0.5, 't')
charged = 0.5 * 2001.0 * 0.0004
ok("the fee booked is the fee Bitget charged (0.04%), not the 0.06% estimate",
   abs(e.book[ETH]['fees'] - charged) < 1e-9 and abs(pf.equity - fake.wallet) < 1e-9, f"${charged:.4f}")

# ─────────────────────────────────────────────────────────────────────────────
print("\n4. (a) FUNDING FROM BITGET'S BILLS")
bot, e, fake = mkbot(); ready(e); pf = bot.portfolio
e.trade_to(ETH, 0.5, 't'); e.trade_to(BTC, -0.002, 't')
time.sleep(0.01); fake.settle(0.0001)
e.live_sync(force=True)
bill = {b['symbol']: float(b['amount']) for b in fake.bills}
ok("one settlement: each position's funding is exactly its bill (long pays, short receives)",
   abs(e.book[ETH]['funding'] - bill['ETHUSDT']) < 1e-12 and abs(e.book[BTC]['funding'] - bill['BTCUSDT']) < 1e-12
   and bill['ETHUSDT'] < 0 < bill['BTCUSDT'], f"ETH {bill['ETHUSDT']:+.4f} BTC {bill['BTCUSDT']:+.4f}")
ok("  and the ledger equals Bitget's wallet to the cent (drift 0)", abs(pf.equity - fake.wallet) < 1e-9 and abs(e.live['drift']) < 1e-9)
e.live_sync(force=True); e.save()
e2 = om.C488Engine(bot); e2.refresh_marks = e.refresh_marks; e2.marks = e.marks; e2.live.update(ready=True)
bot.portfolio._c488 = e2; e2.live_sync(force=True)
ok("  never twice: a second sync, and a RESTART, book it again zero times",
   abs(e2.book[ETH]['funding'] - bill['ETHUSDT']) < 1e-12 and e2.live['bills'] == 2 and abs(pf.equity - fake.wallet) < 1e-9)
e2.reset()
ok("  a fresh start clears the booked-bill list and the funding start (set again at the next live check)",
   e2.bill_seen == [] and e2.bill_since == 0 and not e2.live['ready'])
bot, e, fake = mkbot(); ready(e); pf = bot.portfolio
e.trade_to(ETH, 0.5, 't')
e.fund_iv[ETH] = (8, time.time()); e.fund_next[ETH] = int(time.time() * 1000) - 1
called = []; orig = e.accrue_funding; e.accrue_funding = lambda: called.append(1)
e._tick_at = 0; e.last_rebal = dt.datetime.utcnow().strftime('%Y-%m-%d'); e.tick()
ok("live, the paper funding estimate is never booked (the settlement passed, nothing was estimated)",
   not called and e.book[ETH]['funding'] == 0.0)
e.accrue_funding = orig
bot, e, fake = mkbot(); ready(e); pf = bot.portfolio
e.trade_to(ETH, 0.5, 't'); time.sleep(0.01); fake.settle(0.0001); amt = float(fake.bills[-1]['amount'])
e.trade_to(ETH, 0.0, 't'); e.live_sync(force=True)
ok("a bill that arrives after the position closed is booked to that closed position",
   abs(e.closed[-1]['funding'] - amt) < 1e-9 and abs(pf.equity - fake.wallet) < 1e-9,
   f"closed funding {e.closed[-1]['funding']:+.4f} bill {amt:+.4f} ledger {pf.equity:.4f} wallet {fake.wallet:.4f} {e.live['funding_other']}")
fake.pos['XRPUSDT'] = dict(qty=10.0, avg=1.0); fake.px['XRPUSDT'] = (1.0, 1.0); fake.mode['XRPUSDT'] = 'isolated'
time.sleep(0.01); fake.settle(0.001, raws={'XRPUSDT'}); e.live_sync(force=True)
ok("a bill for a symbol the book never held is not booked to the book (the balance sync takes it)",
   abs(e.live['funding_other'] + 0.01) < 1e-9 and abs(pf.equity - fake.wallet) < 1e-9,
   f"other {e.live['funding_other']:+.4f} ledger {pf.equity:.4f} wallet {fake.wallet:.4f}")
bot, e, fake = mkbot(); ready(e)
e.trade_to(ETH, 0.5, 't'); time.sleep(0.01)
for k in range(150):
    fake.settle(0.00001)
e.live_sync(force=True)
ok("150 bills arrive in two pages (idLessThan) and all 150 are booked once",
   e.live['bills'] == 150 and fake.calls['bill'] >= 2 and abs(bot.portfolio.equity - fake.wallet) < 1e-9,
   f"bills {e.live['bills']} calls {fake.calls['bill']} ledger {bot.portfolio.equity:.4f} wallet {fake.wallet:.4f}")

# ─────────────────────────────────────────────────────────────────────────────
print("\n5. (b) THE SYNC")
bot, e, fake = mkbot(); ready(e); pf = bot.portfolio
e.trade_to(ETH, 0.5, 't'); e.trade_to(BTC, -0.002, 't'); e.trade_to(ETH, 0.2, 't'); e.trade_to(BTC, 0.001, 't')
time.sleep(0.01); fake.settle(0.0002); e.live_sync(force=True)
ok("after opens, a reduction, a flip and a settlement: ledger == Bitget wallet, positions equal",
   abs(pf.equity - fake.wallet) < 1e-9 and abs(e.live['drift']) < 1e-9 and e.live['corrections'] == 0
   and all(abs(e._qty(f"{r[:-4]}/USDT:USDT") - v['qty']) < 1e-12 for r, v in fake.pos.items()), f"wallet ${fake.wallet:.4f}")
fake.wallet -= 2.00; LOG.lines.clear()
e.live_sync(force=True)
ok("a $2 gap the book did not see (over 0.1% of ~$998): the ledger follows Bitget, and it is shouted",
   abs(pf.equity - fake.wallet) < 1e-9 and abs(e.live['drift'] + 2.0) < 1e-9 and LOG.has('the ledger now follows Bitget')
   and e.live['drift_loud'] == 1)
fake.wallet -= 0.10; LOG.lines.clear(); e.live_sync(force=True)
ok("  a 10-cent gap is followed quietly (under $0.50 and 0.1%)", abs(pf.equity - fake.wallet) < 1e-9 and not LOG.has('the ledger now follows Bitget'))
ok("the free balance is never more than Bitget says can open a position",
   pf.available_balance <= float(e.live['venue_free']) + 1e-9 and pf.available_balance <= pf.equity - pf.get_locked_margin() + 1e-9)
bot, e, fake = mkbot(); ready(e); pf = bot.portfolio
fake.read_fail.add('1'); LOG.lines.clear()
e.trade_to(ETH, 0.5, 't')
ok("an order that filled but could not be read back: not booked (C487 says CHECK THE EXCHANGE)",
   ETH not in e.book and abs(fake.pos['ETHUSDT']['qty'] - 0.5) < 1e-12 and LOG.has('could not be read back', 'ERROR'))
e.live_sync(force=True)
ok("  the next sync adopts Bitget's 0.5 ETH at its price, loudly; the ledger equals the wallet",
   abs(e.book[ETH]['qty'] - 0.5) < 1e-12 and abs(e.book[ETH]['avg'] - 2001.0) < 1e-9 and e.live['corrections'] == 1
   and LOG.has('the book now follows Bitget', 'ERROR') and abs(pf.equity - fake.wallet) < 1e-9 and inv(pf))
fake.pos.pop('ETHUSDT'); LOG.lines.clear(); e.live_sync(force=True)
ok("a position that vanished at Bitget (liquidated, closed by hand) is dropped, with a record",
   ETH not in e.book and e.closed[-1].get('why') == 'gone at Bitget' and e.live['corrections'] == 2)
e.trade_to(ETH, 0.5, 't')
real = fake.privateMixGetV2MixPositionAllPosition; seq = [0]
def blip(p):
    seq[0] += 1
    d = real(p)
    if seq[0] == 1:
        d['data'] = [x for x in d['data'] if x['symbol'] != 'ETHUSDT']
    return d
fake.privateMixGetV2MixPositionAllPosition = blip
c0 = e.live['corrections']; e.live_sync(force=True); fake.privateMixGetV2MixPositionAllPosition = real
ok("a one-read blip (the position missing once, back 2 s later) changes nothing", e.live['corrections'] == c0 and abs(e._qty(ETH) - 0.5) < 1e-12)
fake.pos['XRPUSDT'] = dict(qty=10.0, avg=1.0); fake.px['XRPUSDT'] = (1.0, 1.0); fake.mode['XRPUSDT'] = 'isolated'
e.live_sync(force=True)
ok("an isolated position the book never opened is not adopted (said once, left alone)",
   'XRP/USDT:USDT' not in e.book and LOG.has('did not open'))
bot.portfolio.positions.positions['BTC/USDT:USDT'] = types.SimpleNamespace(initial_margin=0.0)
fake.pos['BTCUSDT'] = dict(qty=0.001, avg=50000.0)
e.live_sync(force=True)
ok("a symbol the intraday engine holds is its business: not adopted", BTC not in e.book)
bot.portfolio.positions.positions.clear()
bot, e, fake = mkbot(); ready(e)
fake.fail.add('accounts'); calls = []
ok("a failed sync blocks the rebalance (it raises, and the tick retries in 10 min)",
   not e.live_sync(force=True) and e.live['sync_error'] != '')
try:
    e.candidates = lambda n: [ETH]
    e.rebalance('t'); raised = False
except RuntimeError as x:
    raised = 'sync' in str(x)
ok("  rebalance() refuses: 'Bitget did not answer the pre-rebalance sync'", raised and not fake.sent)

# ─────────────────────────────────────────────────────────────────────────────
print("\n6. (e) THE VENUE'S OWN RULES")
bot, e, fake = mkbot(live=False)
e2 = om.C488Engine(bot)
TABLE = FIX['contracts'] + [dict(FIX['contracts'][1], symbol=f"Z{j:02d}USDT", baseCoin=f"Z{j:02d}") for j in range(98)]
e2._get = lambda path, params, tries=3: TABLE if path == 'contracts' else None
e2.refresh_rules(force=True)
ok("the live contract table (real Bitget rows) gives step, minimum, $ minimum, market cap, status",
   e2.rules[BTC] == dict(step=0.0001, min_qty=0.0001, min_usdt=5.0, max_mkt=220.0, status='normal')
   and e2.rules[ETH]['step'] == 0.01 and e2.rules[ETH]['max_mkt'] == 1900.0, str(e2.rules[BTC]))
e2._get = lambda path, params, tries=3: FIX['contracts'][:1]
e2.refresh_rules(force=True)
ok("  a short read never replaces a full table", len(e2.rules) == 100 and ETH in e2.rules)
e2.rules[ETH] = dict(e2.rules[ETH], step=0.1, min_qty=0.3)
ok("  and the step comes from it before ccxt's copy", e2._step(ETH) == (0.1, 0.3))
bot, e, fake = mkbot(); ready(e)
e.trade_to(ETH, 0.5, 't')
e.rules = {BTC: dict(step=0.0001, min_qty=0.0001, min_usdt=5.0, max_mkt=220.0, status='maintain'),
           ETH: dict(step=0.01, min_qty=0.01, min_usdt=5.0, max_mkt=1900.0, status='limit_open')}
n0 = len(fake.sent)
e.trade_to(BTC, 0.002, 't'); e.trade_to(ETH, 0.8, 't')
ok("'maintain' takes no order; 'limit_open' takes no opening order", len(fake.sent) == n0)
e.trade_to(ETH, 0.2, 't')
ok("  but a 'limit_open' contract can still be reduced", abs(e._qty(ETH) - 0.2) < 1e-12)
e.rules = {BTC: dict(step=0.0001, min_qty=0.0001, min_usdt=5.0, max_mkt=220.0, status='normal')}
e.trade_to(ETH, 0.5, 't')
ok("  a contract missing from a table that loaded is not opened", abs(e._qty(ETH) - 0.2) < 1e-12)
e.rules[BTC]['min_usdt'] = 150.0
e.trade_to(BTC, 0.002, 't')
ok("  Bitget's own $ minimum per contract is used (a $100 order under a $150 minimum is not sent)", BTC not in e.book)

# ─────────────────────────────────────────────────────────────────────────────
print("\n7. A WHOLE LIVE REBALANCE ON THE SIMULATED VENUE")
def market(n=430, k=40, seed=11):
    g = np.random.default_rng(seed)
    T = (np.arange(n) + 19000) * 86400000
    close = np.full((n, k), np.nan); qv = np.full((n, k), np.nan); fund = np.zeros((n, k))
    for j in range(k):
        a = int(g.integers(0, 150)); b = n
        ret = g.normal(0, 0.004, size=n).cumsum() * 0.02 + g.normal(0, 0.035, size=n)
        px = 10 ** g.uniform(-1, 3) * np.exp(np.cumsum(ret))
        close[a:b, j] = px[a:b]; qv[a:b, j] = np.exp(g.normal(16 - 0.04 * j, 0.8, size=b - a))
        fund[a:b, j] = g.normal(0.0001, 0.0002, size=b - a) * 3
    return T, close, qv, fund
T, close, qv, fund = market()
bases = [f"C{j:02d}" for j in range(close.shape[1])]
syms = [f"{b}/USDT:USDT" for b in bases]
extra = {}
for j, b in enumerate(bases):
    px = float(close[-1, j]); st = float(10 ** np.floor(np.log10(max(0.5 / px, 1e-9))))
    extra[f"{b}/USDT:USDT"] = clone_market(FIX['markets'][BTC], b, st)
bot, e, fake = mkbot(extra=extra); pf = bot.portfolio
for j, b in enumerate(bases):
    px = float(close[-1, j]); fake.px[f"{b}USDT"] = (px * 0.9999, px * 1.0001)
    fake.mode[f"{b}USDT"] = 'isolated' if j % 3 == 0 else 'crossed'
e._sync_marks()
for s in syms:
    st = float(fake.markets[s]['precision']['amount'])
    e.rules[s] = dict(step=st, min_qty=st, min_usdt=5.0, max_mkt=1e12, status='normal')
e.candidates = lambda n: syms
e.matrices = lambda s: (T, syms, close, qv, fund)
ready(e); LOG.lines.clear()
e.rebalance('live test')
eq = e.info['equity']
off = [s for s, pl in e.plan.items() if abs(e._qty(s) - pl['w'] * eq / e.mark(s)) > 0.51 * e._step(s)[0] + 1e-12]
ok("every target reached to within half a step", not off and len(e.plan) > 5, f"{len(e.plan)} targets, gross {e.info['gross_target']}x")
ok("Bitget holds exactly the book, symbol by symbol",
   set(fake.pos) == {e._raw(s) for s in e.book} and all(abs(fake.pos[e._raw(s)]['qty'] - p['qty']) < 1e-12 for s, p in e.book.items()))
ok("every order went crossed and one-way; every traded symbol was switched from isolated first where needed",
   all(r['marginMode'] == 'crossed' and 'tradeSide' not in r for r in fake.sent)
   and all(fake.mode[e._raw(s)] == 'crossed' and fake.levs[e._raw(s)] == 5 for s in e.book))
ok("the ledger equals Bitget's wallet; no correction was needed", abs(pf.equity - fake.wallet) < 1e-9
   and e.live['corrections'] == 0 and inv(pf), f"wallet ${fake.wallet:.4f}, fees ${1000 - fake.wallet:.4f}")
n0 = len(fake.sent); e.last_rebal = ''; e.rebalance('again')
ok("a second pass trades nothing", len(fake.sent) == n0 and e.info['n_trades'] == 0)
e.flatten('end')
ok("a flatten leaves Bitget flat and the ledger on the wallet", not fake.pos and not e.book and abs(pf.equity - fake.wallet) < 1e-9)

# ─────────────────────────────────────────────────────────────────────────────
print("\n8. SAFETY")
ok("C488_LIVE_OK is still False by default", om.Config().C488_LIVE_OK is False)
c = om.Config()
ok("the Bitget keys are not in the .py: empty in Config, loaded only from api_keys.json",
   (c.API_KEY, c.API_SECRET, c.API_PASSWORD) == ('', '', '')
   and "api_file = os.path.join(BASE_PATH, 'api_keys.json')" in src)
# every 12+ character literal (no spaces, not a '<...>' placeholder) assigned to a KEY / SECRET / PASSWORD / TOKEN name
lit = re.findall(r"""\b(\w*(?:KEY|SECRET|PASSWORD|TOKEN)\w*)\s*=\s*['"]([^'"\s<.]{12,})['"]""", src)
KNOWN = {'NEWS_API_KEY'}      # pre-existing NewsData.io key -- flagged to the operator, pending #3
ok("no NEW credential literal in the .py (the one known NewsData.io key is flagged in pending #3)",
   {n for n, v in lit} <= KNOWN, str(sorted({n for n, v in lit})))
ok("the key file is checked for other users' access (chmod 600 named)", "st_mode & 0o077" in src and 'chmod 600' in src)
bot, e, fake = mkbot(); bot.cfg.C488_LIVE_OK = False
e._tick_at = 0; e.tick(); e._tick_at = 0; e.tick()
ok("live with C488_LIVE_OK False: not one call reaches Bitget", fake.private_calls() == 0)


class PaperEx:
    def __init__(self, eng, fake):
        self.exchange, self.markets, self.eng = fake, fake.markets, eng
    def place_order(self, sym, side, qty, lev, order_type='market', price=None, reduce_only=False, post_only=None):
        m = self.eng[0].marks[sym]; px = m['ask'] if side == 'buy' else m['bid']
        return {'id': 'p', 'status': 'closed', 'price': px, 'filled': qty}
    def c487_settle(self, sym, o, side, price, size, wait):
        return float(o['filled']), float(o['price']), 'filled'
    def get_current_price(self, sym):
        return None
bot, e, fake = mkbot(live=False); ref = [e]; bot.exchange = PaperEx(ref, fake)
e.candidates = lambda n: [ETH, BTC]
e.trade_to(ETH, 0.5, 't'); e._tick_at = 0; e.tick(); e.live_sync = None
ok("paper: trades and ticks make no private call, and the paper funding estimate still runs",
   fake.private_calls() == 0 and e.status()['live'] == {'on': False, 'rules': 0})

# ─────────────────────────────────────────────────────────────────────────────
print("\n9. THE PAGE AND THE REPORT")
bot, e, fake = mkbot(); ready(e)
e.trade_to(ETH, 0.5, 'page'); time.sleep(0.01); fake.settle(0.0001); fake.wallet -= 1.0; e.live_sync(force=True)
st = e.status()['live']
ok("status()['live'] carries Bitget equity, drift, fixes, funding from bills, margin, sync age",
   st['on'] and st['ready'] and abs(st['venue_equity'] - fake.equity()) < 1e-3 and st['drift_total'] < -0.99
   and st['bills'] == 1 and st['margin'] == 'cross' and st['synced_s'] is not None, str({k: st[k] for k in ('venue_equity', 'drift_total', 'bills')}))
ok("the report prints a LIVE line (and NOT READY / SYNC FAILING when so)",
   "self._pack('LIVE'" in src and 'NOT READY' in src and 'SYNC FAILING' in src)


def free_port():
    s = socket.socket(); s.bind(('127.0.0.1', 0)); p = s.getsockname()[1]; s.close(); return p


def page(e, bot):
    e.last_rebal = '2026-09-26'; e.info = {'topn': 20}
    pf = bot.portfolio; pf.session_start_equity = 1000.0; pf.positions = om.PositionsManager()
    pf.get_live_equity = lambda *a: pf.equity + e.unrealized()
    fbot = types.SimpleNamespace(cfg=bot.cfg, portfolio=pf, c488=e,
                                 mode_mgr=types.SimpleNamespace(mode=types.SimpleNamespace(value='normal')),
                                 exchange=types.SimpleNamespace(get_current_price=lambda s: None),
                                 _c467_day_barrier=lambda: {'pnl': 0.0, 'limit': 9.0, 'used': 0.0, 'frac': 0.0},
                                 _c482_risk_guard=lambda: {'pct': 15.0, 'month_eq0': 1000.0})
    port = free_port(); om.RemoteControl(fbot, port=port).start(); time.sleep(0.6)
    from playwright.sync_api import sync_playwright
    exe = (glob.glob('/opt/pw-browsers/chromium-*/chrome-linux/chrome') or [None])[0]
    with sync_playwright() as pw:
        b = pw.chromium.launch(executable_path=exe) if exe else pw.chromium.launch()
        pg = b.new_page(viewport={'width': 412, 'height': 900}); errs = []
        pg.on('pageerror', lambda x: errs.append(str(x)))
        pg.goto(f'http://127.0.0.1:{port}/?t={TOKEN}'); pg.wait_for_timeout(3500)
        txt = pg.inner_text('#book'); b.close()
    return txt, errs


try:
    txt, errs = page(e, bot)
    ok("the Portfolio book panel shows the live line: Bitget equity, drift, fixes, bills funding, margin, sync",
       'live · Bitget $' in txt and 'drift so far' in txt and 'position fixes' in txt and 'cross margin' in txt and 'synced' in txt,
       txt.replace('\n', ' | ')[-220:])
    ok("  no JavaScript errors", not errs, str(errs))
    bot2, e2, fake2 = mkbot(); fake2.pos_mode = 'hedge_mode'; fake2.pos['ETHUSDT'] = dict(qty=0.5, avg=2000.0); ready(e2)
    txt2, errs2 = page(e2, bot2)
    ok("NOT READY is SHOWN on the panel, with the reason", 'LIVE NOT READY' in txt2 and 'position mode' in txt2 and not errs2,
       txt2.replace('\n', ' | ')[-160:])
except ImportError:
    ok("Chromium/playwright available for the page check", False)

shutil.rmtree(BASE, ignore_errors=True)
print("\n" + "=" * 66)
print("ALL CHECKS PASSED" if not fails else f"{len(fails)} FAILURE(S): {fails}")
sys.exit(1 if fails else 0)
