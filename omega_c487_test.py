#!/usr/bin/env python3
"""C487: a resting order is filled by what the market does AFTER it arrives.

1. PAPER ORDER: a resting entry limit (post-only) and a maker exit (reduce-only
   limit) come back ON THE BOOK -- status 'open', nothing filled -- instead of
   being judged by the 5 minutes BEFORE they were placed. Market and crossing
   orders still fill on arrival, at the bid/ask.
   NEGATIVE CONTROL: the pre-C487 source fills the same resting entry at once.
2. THE FILL TEST (_c487_through): a resting buy at p fills on an ask at or
   below p, a print strictly below p AFTER it arrived, or once prints AT p have
   used up the size queued ahead of it on arrival plus its own (each print
   counted once); with no queue reading, at-price prints never fill it; prints
   from before it arrived never count; sell mirrors it; no data is None.
3. PAPER SETTLE: fills when the market comes to it, waits no longer than asked,
   'unfilled' when it never comes, 'unknown' when nothing could be read.
4. LIVE SETTLE against a simulated exchange: a fill is read back with its real
   average; an order still resting at the deadline is CANCELLED and read once
   more (a fill can race the cancel); a partial fill is reported as partial; an
   order that cannot be read at all is 'unknown' and logged as an ERROR; nothing
   that filled is ever cancelled.
5. THE ORDER PATHS, executed from the shipped source: the entry books nothing
   the market did not fill, scales margin and fee on a partial, and takes the
   real average price; the maker exit and the maker half cross the unfilled
   remainder and blend the price.
6. EVERY limit order the bot places is settled (sweep), and the switch
   C487_HONEST_FILLS=False reproduces the C486 paper order exactly.
"""
import os, sys, io, re, ast, time, types, textwrap, contextlib, importlib.util, subprocess, tempfile, shutil, logging
REPO = os.path.dirname(os.path.abspath(__file__))
os.environ.setdefault('OMEGA_BASE_PATH', '/tmp/omega_c487_test')
os.makedirs(os.environ['OMEGA_BASE_PATH'], exist_ok=True)
MARK = 'C487: A RESTING ORDER IS FILLED BY WHAT HAPPENS AFTER IT ARRIVES'
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


def git(*a):
    return subprocess.run(['git', *a], capture_output=True, text=True, cwd=REPO).stdout


def exman(om, paper=True, honest=True):
    cfg = om.Config(); cfg.PAPER_MODE = paper; cfg.C487_HONEST_FILLS = honest
    ex = om.ExchangeManager(cfg)
    ex.round_to_tick = lambda s, p, side='buy': p
    ex.get_bid_ask = lambda s: (99.0, 101.0, 'book')
    ex.get_current_price = lambda s: 100.0
    return ex


print("=" * 66); print("C487: A RESTING ORDER IS FILLED BY WHAT HAPPENS AFTER IT ARRIVES"); print("=" * 66)
SRC = os.path.join(REPO, 'omega_v60_reconstructed.py')
om = load(SRC, 'om487')
src = open(SRC, encoding='utf-8').read()
intro = git('log', '--format=%H', '-S', MARK, '--', 'omega_v60_reconstructed.py').split()
ref = (intro[-1] + '^') if intro else 'HEAD'
old_src = git('show', f'{ref}:omega_v60_reconstructed.py')
tmpd = tempfile.mkdtemp(prefix='c487_')
om_old = None
if old_src and MARK not in old_src:
    p = os.path.join(tmpd, 'pre487.py'); io.open(p, 'w', encoding='utf-8').write(old_src); om_old = load(p, 'om_pre487')
ok("the pre-C487 source can be rebuilt from git", om_old is not None, ref[:10])

print("\n1. THE PAPER ORDER")
ex = exman(om)
touched = []
ex._limit_touched = lambda *a, **k: touched.append(a) or True
ex._c487_queue = lambda s, sd, p: 4.0
o = ex.place_order('ICP/USDT:USDT', 'buy', 10, 5, 'limit', 99.0)            # post-only entry at the bid
ok("a resting entry comes back ON THE BOOK: status open, nothing filled",
   o['status'] == 'open' and o['filled'] == 0 and o['price'] == 99.0 and o.get('c487_t0'), f"{o['status']} {o['filled']}")
ok("  and the backward-looking 5-minute check is not consulted", not touched)
ok("  and it carries the size queued ahead of it, read from the book on arrival", o.get('c487_queue') == 4.0)
o = ex.place_order('ICP/USDT:USDT', 'sell', 10, 5, 'limit', 101.0, reduce_only=True)   # maker exit at the ask
ok("a maker exit (reduce-only limit) also rests", o['status'] == 'open' and o['filled'] == 0)
o = ex.place_order('ICP/USDT:USDT', 'buy', 10, 5, 'market')
ok("a market buy fills on arrival at the ASK", o['status'] == 'closed' and o['price'] == 101.0 and o['filled'] == 10)
o = ex.place_order('ICP/USDT:USDT', 'sell', 10, 5, 'market', reduce_only=True)
ok("a market close fills on arrival at the BID", o['status'] == 'closed' and o['price'] == 99.0)
o = ex.place_order('ICP/USDT:USDT', 'buy', 10, 5, 'limit', 101.05, post_only=False)   # C297/C395 crossing entry
ok("a deliberate crossing entry fills on arrival", o['status'] == 'closed' and o['filled'] == 10)
o = ex.place_order('ICP/USDT:USDT', 'buy', 10, 5, 'limit', 101.5)                      # post-only that would cross
ok("a post-only entry that would cross is still REJECTED (C363/C364 parity)", o['status'] == 'canceled')
if om_old:
    ex0 = exman(om_old)
    ex0._limit_touched = lambda *a, **k: True
    o0 = ex0.place_order('ICP/USDT:USDT', 'buy', 10, 5, 'limit', 99.0)
    ok("NEGATIVE CONTROL: pre-C487 filled the same resting entry on the spot",
       o0['status'] == 'closed' and o0['filled'] == 10, f"{o0['status']}")

print("\n2. THE FILL TEST")
class R:
    def __init__(self, d): self.d = d
    def json(self): return {'data': self.d}
def through(side, price, book, prints, since=1000, fail_book=False, fail_tape=False, order=None, ex=None):
    ex = ex or exman(om)
    if fail_book:
        ex.get_bid_ask = lambda s: (None, None, 'none')
    else:
        ex.get_bid_ask = lambda s: (book[0], book[1], 'book')
    import requests
    real = requests.get
    def fake(url, params=None, timeout=None):
        if fail_tape: raise IOError('down')
        return R([{'ts': str(x[0]), 'price': str(x[1]), 'size': str(x[2] if len(x) > 2 else 1.0),
                   'tradeId': str(x[3] if len(x) > 3 else x[0])} for x in prints])
    requests.get = fake
    try:
        return ex._c487_through('ICP/USDT:USDT', side, price, since, order)
    finally:
        requests.get = real
ok("buy @100: ask falls to 100 -> filled", through('buy', 100, (99.9, 100.0), []) is True)
ok("buy @100: a print at 99.99 after arrival -> filled", through('buy', 100, (99.9, 100.1), [(2000, 99.99)]) is True)
ok("buy @100: a print exactly AT 100 -> NOT counted (queue unknown)", through('buy', 100, (99.9, 100.1), [(2000, 100.0)]) is False)
ok("buy @100: a print below 100 BEFORE arrival -> not counted", through('buy', 100, (99.9, 100.1), [(900, 99.5)]) is False)
ok("sell @101: bid rises to 101 -> filled", through('sell', 101, (101.0, 101.1), []) is True)
ok("sell @101: a print at 101.01 after arrival -> filled", through('sell', 101, (100.9, 101.1), [(2000, 101.01)]) is True)
ok("sell @101: nothing reaches it -> False", through('sell', 101, (100.9, 101.1), [(2000, 100.95)]) is False)
ok("no book and no tape -> None (unknown), never True",
   through('buy', 100, None, [], fail_book=True, fail_tape=True) is None)
print("   -- the queue: prints AT the price fill it once the size queued ahead of it (plus its own) has traded --")
o = {'c487_queue': 5.0, 'amount': 1.0}
bk = (100.0, 100.1)
ok("queue 5 ahead + own 1: 5.5 traded at 100 -> not yet",
   through('buy', 100, bk, [(2000, 100.0, 3.0, 'a'), (2100, 100.0, 2.5, 'b')], order=o) is False, f"{o.get('c487_at')}")
ok("  the same prints seen again on the next look are NOT counted twice",
   through('buy', 100, bk, [(2000, 100.0, 3.0, 'a'), (2100, 100.0, 2.5, 'b')], order=o) is False and o['c487_at'] == 5.5)
ok("  0.6 more traded at 100 -> 6.1 >= 6 -> filled",
   through('buy', 100, bk, [(2000, 100.0, 3.0, 'a'), (2100, 100.0, 2.5, 'b'), (2200, 100.0, 0.6, 'c')], order=o) is True)
o = {'c487_queue': 0.0, 'amount': 1.0}
ok("inside the spread (nobody ahead): 1.0 traded at our price -> filled",
   through('sell', 100.05, (100.0, 100.1), [(2000, 100.05, 1.0, 'z')], order=o) is True)
o = {'c487_queue': None, 'amount': 1.0}
ok("unknown depth ahead (queue None): prints AT the price never fill it",
   through('buy', 100, bk, [(2000, 100.0, 999.0, 'q')], order=o) is False)
o = {'c487_queue': 0.0, 'amount': 1.0}
ok("prints at the price from BEFORE the order arrived do not count",
   through('buy', 100, bk, [(900, 100.0, 50.0, 'old')], order=o) is False)
def queue(side, price, t):
    ex = exman(om); ex.exchange = types.SimpleNamespace(fetch_ticker=lambda s: t)
    return ex._c487_queue('ICP/USDT:USDT', side, price)
T = {'bid': 100.0, 'ask': 100.2, 'bidVolume': 7.0, 'askVolume': 3.0}
ok("queue read at placement: at the bid -> the bid size; at the ask -> the ask size",
   queue('buy', 100.0, T) == 7.0 and queue('sell', 100.2, T) == 3.0)
ok("  inside the spread -> 0 (first in line); behind the touch -> None (unseen depth)",
   queue('buy', 100.1, T) == 0.0 and queue('buy', 99.9, T) is None and queue('sell', 100.3, T) is None)
ok("  a failed book read -> None (strict: only prints THROUGH the price fill it)",
   queue('buy', 100.0, {'bid': None, 'ask': None}) is None)

print("\n3. PAPER SETTLE")
def psettle(seq, wait):
    ex = exman(om); it = iter(seq); calls = []
    def thr(*a):
        calls.append(time.time())
        try: return next(it)
        except StopIteration: return seq[-1]
    ex._c487_through = thr
    ex_sleep = time.sleep
    t0 = time.time()
    o = {'id': 'x', 'status': 'open', 'price': 99.0, 'filled': 0.0, 'c487_t0': t0}
    r = ex.c487_settle('ICP/USDT:USDT', o, 'buy', 99.0, 10.0, wait)
    return r, time.time() - t0, len(calls)
r, dt_, n = psettle([False, False, True], 10.0)
ok("the market comes to it on the 3rd look -> filled at the limit", r == (10.0, 99.0, 'filled'), f"{r} after {dt_:.1f}s")
r, dt_, n = psettle([False], 2.0)
ok("the market never comes -> unfilled, after waiting ~the full 2s", r[2] == 'unfilled' and r[0] == 0 and 1.8 <= dt_ < 3.5, f"{r} {dt_:.1f}s")
r, dt_, n = psettle([None], 1.0)
ok("nothing could be read -> 'unknown' (callers treat it as NOT filled)", r[2] == 'unknown' and r[0] == 0)
ex = exman(om)
r = ex.c487_settle('ICP/USDT:USDT', {'id': 'm', 'status': 'closed', 'price': 101.0, 'filled': 10}, 'buy', 0.0, 10, 30)
ok("a market order passes straight back at its fill", r == (10.0, 101.0, 'filled'))
r = ex.c487_settle('ICP/USDT:USDT', {'id': 'c', 'status': 'canceled'}, 'buy', 99.0, 10, 30)
ok("a rejected order is unfilled at once", r == (0.0, 0.0, 'unfilled'))

print("\n4. LIVE SETTLE (simulated exchange)")
class Venue:
    def __init__(self, states, fail=False, fill_on_cancel=None):
        self.states = list(states); self.i = 0; self.cancelled = 0; self.fail = fail; self.foc = fill_on_cancel
    def fetch_order(self, oid, sym):
        if self.fail: raise IOError('venue down')
        if self.cancelled and self.foc is not None:
            return self.foc
        s = self.states[min(self.i, len(self.states) - 1)]; self.i += 1; return s
    def cancel_order(self, oid, sym):
        self.cancelled += 1
crit = []
class H(logging.Handler):
    def emit(self, rec):
        if rec.levelno >= logging.ERROR: crit.append(rec.getMessage())
logging.getLogger('OmegaV60').addHandler(H())
def lsettle(v, size=10.0, wait=1.2):
    ex = exman(om, paper=False); ex.exchange = v
    return ex.c487_settle('ICP/USDT:USDT', {'id': 'L1', 'status': None}, 'buy', 99.0, size, wait)
v = Venue([{'status': 'closed', 'filled': 10.0, 'average': 98.97}])
ok("filled -> read back with the REAL average price, nothing cancelled", lsettle(v) == (10.0, 98.97, 'filled') and v.cancelled == 0)
v = Venue([{'status': 'open', 'filled': 0.0}])
r = lsettle(v)
ok("still resting at the deadline -> CANCELLED and reported unfilled", r[2] == 'unfilled' and v.cancelled == 1, f"{r} cancels={v.cancelled}")
v = Venue([{'status': 'open', 'filled': 4.0, 'average': 99.0}])
r = lsettle(v)
ok("40% filled at the deadline -> rest cancelled, reported PARTIAL 4.0 @ 99.0", r == (4.0, 99.0, 'partial') and v.cancelled == 1, f"{r}")
v = Venue([{'status': 'open', 'filled': 0.0}], fill_on_cancel={'status': 'closed', 'filled': 10.0, 'average': 99.0})
r = lsettle(v)
ok("a fill that races the cancel is caught by the read-back -> filled", r == (10.0, 99.0, 'filled'), f"{r}")
v = Venue([], fail=True)
n0 = len(crit)
r = lsettle(v, wait=0.5)
ok("an order that cannot be read at all -> 'unknown', never booked", r == (0.0, 0.0, 'unknown'))
ok("  and it says so at ERROR for a human to check the venue",
   len(crit) > n0 and 'CHECK THE EXCHANGE BY HAND' in crit[-1], f"{crit[-1:]}")

print("\n5. THE ORDER PATHS, EXECUTED FROM THE SHIPPED SOURCE")
def block(start, end_marker, from_src=src):
    i = from_src.index(start); j = from_src.index(end_marker, i) + len(end_marker)
    ls = i - (from_src.rfind('\n', 0, i) + 1)
    return textwrap.dedent(' ' * ls + from_src[i:j])
class PF:
    def __init__(self): self.released = []
    def release_margin(self, m, pnl, fees, count_trade=True): self.released.append(round(m, 6))
class EX:
    def __init__(self, settle, market_px=98.5):
        self.settle = settle; self.orders = []; self.mpx = market_px
    def c487_settle(self, sym, order, side, price, size, wait):
        self.orders.append(('settle', size, wait))
        return self.settle(order, size) if callable(self.settle) else self.settle
    def place_order(self, sym, side, size, lev, order_type='market', price=None, reduce_only=False, post_only=None):
        self.orders.append(('place', order_type, size)); return {'id': 'm', 'status': 'closed', 'price': self.mpx, 'filled': size}
entry = block("            if getattr(self.cfg, 'C487_HONEST_FILLS', True) and order.get('status') != 'canceled':",
              "f\"after {time.time() - _t487:.0f}s\")")
def run_entry(settle, cross=False):
    cfg = om.Config()
    self_ = types.SimpleNamespace(cfg=cfg, exchange=EX(settle), portfolio=PF())
    ns = dict(vars(om)); ns.update(self=self_, order={'id': 'E', 'status': 'open', 'price': 99.0, 'filled': 0.0},
                                   symbol='ICP/USDT:USDT', side='buy', size=5.0, price=99.0, margin=99.0, leverage=5,
                                   fee=99.0 * 5 * (0.0006 if cross else 0.0002), _cross402=cross)
    exec(compile(entry, '<entry>', 'exec'), ns)
    return ns, self_
ns, s_ = run_entry((0.0, 0.0, 'unfilled'))
ok("entry NOT filled -> the order is marked canceled, so the C286 path releases it and books nothing",
   ns['order']['status'] == 'canceled' and ns['order']['filled'] == 0)
ok("  and it waited LIMIT_ORDER_TIMEOUT_SECONDS for the market", s_.exchange.orders[-1] == ('settle', 5.0, 30.0), f"{s_.exchange.orders}")
ns, s_ = run_entry((5.0, 98.9, 'filled'))
ok("entry filled at 98.9 -> the position takes the REAL price, full size, maker fee on the real notional",
   ns['order']['status'] == 'closed' and ns['price'] == 98.9 and ns['size'] == 5.0
   and abs(ns['fee'] - 5.0 * 98.9 * 0.0002) < 1e-9 and ns['margin'] == 99.0, f"fee {ns['fee']:.5f}")
ns, s_ = run_entry((2.0, 99.0, 'partial'))
ok("entry 40% filled -> 60% of the margin released, margin/size/fee scaled to what filled",
   abs(ns['margin'] - 39.6) < 1e-9 and ns['size'] == 2.0 and s_.portfolio.released == [59.4]
   and abs(ns['fee'] - 2.0 * 99.0 * 0.0002) < 1e-9, f"margin {ns['margin']} released {s_.portfolio.released}")
ns, s_ = run_entry((5.0, 101.04, 'filled'), cross=True)
ok("a crossing entry waits only 3s (it fills on arrival or not at all) and keeps the TAKER rate",
   s_.exchange.orders[-1][2] == 3.0 and abs(ns['fee'] - 5.0 * 101.04 * 0.0006) < 1e-9, f"{s_.exchange.orders} fee {ns['fee']:.5f}")
ex_blk = block("                        _mf487 = 1.0\n", "_close_order = dict(_close_order, filled=0)")
def run_exit(settle):
    cfg = om.Config()
    self_ = types.SimpleNamespace(cfg=cfg, exchange=EX(settle, market_px=100.4))
    pos = types.SimpleNamespace(size=10.0, leverage=5)
    ns = dict(vars(om)); ns.update(self=self_, _close_order={'id': 'X', 'status': 'open', 'filled': 0.0}, pos=pos,
                                   symbol='ICP/USDT:USDT', close_side='sell', _lim376=101.0, exit_price=100.5)
    exec(compile(ex_blk, '<exit>', 'exec'), ns)
    return ns, self_
def settle_exit(order, size):
    return (4.0, 101.0, 'partial') if order.get('id') == 'X' else (size, 100.4, 'filled')
ns, s_ = run_exit((10.0, 101.0, 'filled'))
ok("maker exit filled -> closed at the limit, 100% maker", ns['_close_order']['status'] == 'closed'
   and ns['_close_order']['price'] == 101.0 and ns['_mf487'] == 1.0)
ok("  after resting C487_EXIT_REST_S", s_.exchange.orders[0] == ('settle', 10.0, 5.0), f"{s_.exchange.orders}")
ns, s_ = run_exit((0.0, 0.0, 'unfilled'))
ok("maker exit not filled -> handed to the market fallback (filled=0)", ns['_close_order']['filled'] == 0)
ns, s_ = run_exit(settle_exit)
ok("maker exit 40% filled (live) -> the 60% crosses, price blended, 40% maker",
   ('place', 'market', 6.0) in s_.exchange.orders and abs(ns['_close_order']['price'] - (4 * 101.0 + 6 * 100.4) / 10) < 1e-9
   and abs(ns['_mf487'] - 0.4) < 1e-9, f"{ns['_close_order']['price']:.3f} {s_.exchange.orders}")
half = block("                        _mf487h = 1.0\n", "_ord = dict(_ord, filled=0)")
def run_half(settle):
    cfg = om.Config()
    self_ = types.SimpleNamespace(cfg=cfg, exchange=EX(settle, market_px=100.4))
    pos = types.SimpleNamespace(size=10.0, leverage=5)
    ns = dict(vars(om)); ns.update(self=self_, _ord={'id': 'X', 'status': 'open', 'filled': 0.0}, pos=pos, _half=5.0,
                                   symbol='ICP/USDT:USDT', close_side='sell', _lim462=101.0, price=100.5)
    exec(compile(half, '<half>', 'exec'), ns)
    return ns, self_
ns, s_ = run_half(lambda o, sz: (2.0, 101.0, 'partial') if o.get('id') == 'X' else (sz, 100.4, 'filled'))
ok("maker half 40% filled (live) -> the rest crosses, price blended",
   ('place', 'market', 3.0) in s_.exchange.orders and abs(ns['_ord']['price'] - (2 * 101.0 + 3 * 100.4) / 5) < 1e-9
   and abs(ns['_mf487h'] - 0.4) < 1e-9)
ns, s_ = run_half((0.0, 0.0, 'unfilled'))
ok("maker half not filled -> market fallback", ns['_ord']['filled'] == 0)
ok("the exit fee blends maker/taker on a live partial (both close paths)",
   "_exit_rate462 = (self.cfg.MAKER_FEE_PCT * _c487_mfrac" in src and "_rate487h = (self.cfg.MAKER_FEE_PCT * _mf487h" in src)

print("\n6. SWEEP AND SWITCH")
tree = ast.parse(src)
def fn_src(name):
    n = next(x for x in ast.walk(tree) if isinstance(x, ast.FunctionDef) and x.name == name)
    return ast.get_source_segment(src, n)
bad = []
for name in ('_open_position', '_close_position_inner', '_c336_partial_close'):
    body = fn_src(name)
    for m in re.finditer(r"= self\.exchange\.place_order\(", body):
        tail = body[m.start():m.start() + 1500]
        if 'c487_settle(' not in tail:
            bad.append((name, body[:m.start()].count('\n')))
ok("every order the bot places is followed by a c487_settle (entries, pyramid, maker exits, closes)",
   not bad, f"unsettled: {bad}")
if old_src and om_old:
    otree = ast.parse(old_src); obad = 0
    for name in ('_open_position', '_close_position_inner', '_c336_partial_close'):
        n = next(x for x in ast.walk(otree) if isinstance(x, ast.FunctionDef) and x.name == name)
        body_o = ast.get_source_segment(old_src, n)
        obad += sum('c487_settle(' not in body_o[m.start():m.start() + 1500]
                    for m in re.finditer(r"= self\.exchange\.place_order\(", body_o))
    ok("POSITIVE CONTROL: the same sweep flags every order in the pre-C487 source", obad >= 6, f"{obad} unsettled")
body = fn_src('_open_position')
i_settle = body.find("self.exchange.c487_settle(symbol, order, side, price, size, _w487)")
i_c286 = body.find("if order.get('status') == 'canceled' or order.get('filled', 1) == 0:")
ok("the entry is settled BEFORE the C286 unfilled check reads it", 0 < i_settle < i_c286, f"{i_settle} < {i_c286}")
ok("the entry wait is the existing LIMIT_ORDER_TIMEOUT_SECONDS (30s), read by live code for the first time",
   om.Config().LIMIT_ORDER_TIMEOUT_SECONDS == 30 and 'self.cfg.LIMIT_ORDER_TIMEOUT_SECONDS' in body)
if om_old:
    same = 0; cases = [('buy', 10, 'limit', 99.0, False, None), ('sell', 10, 'limit', 101.0, True, None),
                       ('buy', 10, 'market', None, False, None), ('sell', 10, 'market', None, True, None),
                       ('buy', 10, 'limit', 101.05, False, False), ('buy', 10, 'limit', 101.5, False, None)]
    for touch in (True, False):
        for side, sz, ot, px, ro, po in cases:
            a = exman(om, honest=False); b = exman(om_old)
            a._limit_touched = b._limit_touched = (lambda t: (lambda *x, **k: t))(touch)
            ra = a.place_order('ICP/USDT:USDT', side, sz, 5, ot, px, reduce_only=ro, post_only=po)
            rb = b.place_order('ICP/USDT:USDT', side, sz, 5, ot, px, reduce_only=ro, post_only=po)
            strip = lambda r: {k: v for k, v in r.items() if k != 'id'}
            same += strip(ra) == strip(rb)
    ok("SWITCH: C487_HONEST_FILLS=False gives exactly the C486 paper order (12 cases, touched and not)",
       same == 12, f"{same}/12")

shutil.rmtree(tmpd, ignore_errors=True)
print("\n" + "=" * 66)
print("ALL CHECKS PASSED" if not fails else f"{len(fails)} FAILURE(S): {fails}")
sys.exit(1 if fails else 0)
