#!/usr/bin/env python3
"""Live-trade forensics against real Bitget candles  [C486]

    python3 omega_live_forensics.py LOGDIR WORKDIR [--ver C486] [--market]

LOGDIR  : a folder of omega_report_*.log files (e.g. the `logs` branch).
WORKDIR : where the candle cache and outputs go (created if missing).
--ver   : the version whose trades get the per-trade report (default: newest).
--market: also fetch 5-minute candles for every coin traded and measure how the
          bot's picks did against the SAME style of entry across the market in
          the same hour (the "selection edge"), and each day's market regime.

What it does, in order:
 1. Parses every OPEN / HALF / CLOSE line of every report (dates tracked across
    midnight from the status blocks), whole-idea P&L: before C482 a split
    trade's CLOSE held only the remainder, so HALF + CLOSE; from C482 on the
    CLOSE is already the whole idea.
 2. Fetches Bitget 1-minute candles from 3 h before each entry to 4 h after
    each exit (public API, cached), plus BTC for the whole span.
 3. Per trade: best / worst point while open (MFE / MAE) and which came first,
    how far the coin had already run the trade's way (15 m / 1 h / 3 h), where
    the entry sat in its 3-hour range, 15 m ATR, BTC context, and where price
    went 30 m / 1 h / 2 h / 4 h after the exit.
 4. Replays simple alternative exits on the real candles (own stop & target,
    breakeven moves, peak locks, trails, time stops) against what the bot
    actually did, in a four-way split (time halves x coin halves).
 5. Writes WORKDIR/forensics_<ver>.md (one row per trade, a plain verdict each)
    and WORKDIR/analysis.json (every number above).
Nothing here touches the bot; it only reads logs and public market data.
"""
import os, re, sys, json, glob, time, math, bisect, statistics as st, datetime as dt
import urllib.request, urllib.parse

IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
FEE = 0.08                        # % round trip: maker in, taker out
API = 'https://api.bitget.com/api/v2/mix/market/'


# ─── 1. trades ──────────────────────────────────────────────────────────────
EV = re.compile(r'^\s+(>>|<<|->)\s+(\d\d):(\d\d)\s+(OPEN|CLOSE|HALF)\s+(\S+)\s+(LONG|SHORT)\s+@(\S+)\s+(.*)$')


def parse_trades(logdir):
    trades, opens = [], {}
    for path in sorted(glob.glob(os.path.join(logdir, 'omega_report_2026*.log'))):
        fn = os.path.basename(path)
        d, t = fn[13:21], fn[22:28]
        day = dt.date(int(d[:4]), int(d[4:6]), int(d[6:8]))
        last_min = int(t[:2]) * 60 + int(t[2:4])
        lines = open(path, encoding='utf-8', errors='replace').read().split('\n')
        ver = next((re.search(r'OMEGA (C\d+)', x).group(1) for x in lines[:12] if re.search(r'OMEGA (C\d+)', x)), None)
        for i, ln in enumerate(lines):
            m0 = re.match(r'^\s+(\d\d):(\d\d)\s+up\s', ln)
            e = EV.match(ln)
            if not (m0 or e):
                continue
            hh, mm = (int(m0.group(1)), int(m0.group(2))) if m0 else (int(e.group(2)), int(e.group(3)))
            cur = hh * 60 + mm
            if cur < last_min - 600:                       # wrapped past midnight
                day += dt.timedelta(days=1)
            last_min = cur
            if not e:
                continue
            ts = dt.datetime(day.year, day.month, day.day, hh, mm, tzinfo=IST).isoformat()
            kind, sym, side, px, rest = e.group(4), e.group(5), e.group(6), float(e.group(7)), e.group(8)
            nxt = lines[i + 1] if i + 1 < len(lines) else ''
            key = (sym, side)
            if kind == 'OPEN':
                m = re.match(r'x(\d+)\s+\$([\d.]+)', rest)
                tt = re.search(r'target \+([\d.]+)%\s+stop -([\d.]+)%\s+entry score ([\d.]+)', nxt)
                opens[key] = dict(sym=sym, side=side, entry=px, t_open=ts, lev=int(m.group(1)) if m else 1,
                                  margin=float(m.group(2)) if m else None,
                                  target=float(tt.group(1)) if tt else None, stop=float(tt.group(2)) if tt else None,
                                  score=float(tt.group(3)) if tt else None, ver=ver, halves=[])
            elif kind == 'HALF':
                m = re.match(r'([+-][\d.]+)%\s+\$([+-][\d.]+)', rest)
                if key in opens and m:
                    opens[key]['halves'].append(dict(t=ts, px=px, move=float(m.group(1)), pnl=float(m.group(2))))
            else:
                m = re.match(r'([+-][\d.]+)%\s+\$([+-][\d.]+)\s+(WIN|LOSS)', rest)
                r = re.search(r'held (\S+)\s+(.*?)\s{2,}', nxt)
                o = opens.pop(key, None)
                if o is None or not m:
                    continue
                o.update(t_close=ts, exit=px, move=float(m.group(1)), pnl=float(m.group(2)), close_ver=ver,
                         reason=(r.group(2).strip() if r else ''), held=(r.group(1) if r else None))
                v = int((ver or 'C0')[1:])
                o['whole'] = o['pnl'] if (v >= 482 or not o['halves']) else o['pnl'] + sum(h['pnl'] for h in o['halves'])
                trades.append(o)
    return trades


# ─── 2. candles ─────────────────────────────────────────────────────────────
def _get(url):
    for k in range(5):
        try:
            with urllib.request.urlopen(url, timeout=20) as r:
                return json.loads(r.read().decode())
        except Exception:
            time.sleep(1 + k)
    return {}


def candles(symbol, start_ms, end_ms, gran='1m'):
    out, end = {}, min(end_ms, int(time.time() * 1000))
    while end > start_ms:
        q = urllib.parse.urlencode(dict(symbol=symbol, productType='USDT-FUTURES', granularity=gran,
                                        endTime=end, limit=200))
        d = _get(API + 'history-candles?' + q)
        rows = [[int(x[0])] + [float(v) for v in x[1:6]] for x in (d.get('data') or [])]
        if not rows:
            break
        for r in rows:
            out[r[0]] = r
        first = min(r[0] for r in rows)
        if first >= end:
            break
        end = first - 1
        time.sleep(0.12)
    return [out[k] for k in sorted(out) if start_ms <= k <= end_ms]


def ms(s):
    return int(dt.datetime.fromisoformat(s).timestamp() * 1000)


def fetch_all(trades, work):
    cache_p = os.path.join(work, 'candles.json')
    cache = json.load(open(cache_p)) if os.path.exists(cache_p) else {}
    for t in trades:
        k = f"{t['sym']}|{t['t_open']}|{t['t_close']}"
        if k not in cache:
            cache[k] = candles(t['sym'] + 'USDT', ms(t['t_open']) - 180 * 60000, ms(t['t_close']) + 240 * 60000)
            print(f"   candles {t['sym']:10} {len(cache[k])}", flush=True)
    if trades:
        s0 = min(ms(t['t_open']) for t in trades) - 200 * 60000
        e0 = max(ms(t['t_close']) for t in trades) + 240 * 60000
        if cache.get('BTC|span', [None])[:1] != [[s0, e0]]:
            cache['BTC|span'] = [[s0, e0]]
            cache['BTC'] = candles('BTCUSDT', s0, e0)
    json.dump(cache, open(cache_p, 'w'))
    return cache


# ─── 3. per-trade measurement ───────────────────────────────────────────────
def measure(t, rows, btc):
    sg = 1 if t['side'] == 'LONG' else -1
    t0, t1, e, x = ms(t['t_open']), ms(t['t_close']), t['entry'], t['exit']
    fav = lambda px: sg * (px / e - 1) * 100
    r = dict(t)
    inside = [c for c in rows if t0 <= c[0] <= t1]
    before = [c for c in rows if c[0] < t0]
    after = [c for c in rows if c[0] > t1]
    if inside:
        hi = [fav(c[2] if sg > 0 else c[3]) for c in inside]
        lo = [fav(c[3] if sg > 0 else c[2]) for c in inside]
        i_best, i_worst = max(range(len(hi)), key=hi.__getitem__), min(range(len(lo)), key=lo.__getitem__)
        r.update(mfe=hi[i_best], mae=lo[i_worst], green_first=i_best < i_worst)
    if before:
        c0 = before[-1][4]
        for m in (15, 60, 180):
            ref = [c for c in before if c[0] >= t0 - m * 60000]
            r[f'pre{m}'] = sg * (c0 / ref[0][4] - 1) * 100 if ref else None
        h3, l3 = max(c[2] for c in before), min(c[3] for c in before)
        r['range_pos'] = ((e - l3) / (h3 - l3) if sg > 0 else (h3 - e) / (h3 - l3)) if h3 > l3 else 0.5
        b15 = {}
        for c in before:
            b = b15.setdefault(c[0] // 900000, [c[1], c[2], c[3], c[4]])
            b[1] = max(b[1], c[2]); b[2] = min(b[2], c[3]); b[3] = c[4]
        bars = [b15[k] for k in sorted(b15)]
        tr = [max(bars[j][1] - bars[j][2], abs(bars[j][1] - bars[j - 1][3]), abs(bars[j][2] - bars[j - 1][3]))
              for j in range(1, len(bars))]
        r['atr15'] = st.mean(tr) / e * 100 if tr else None
    b0, b1 = btc.get(t0 // 60000 * 60000), btc.get(t1 // 60000 * 60000)
    bp = btc.get(t0 // 60000 * 60000 - 3600000)
    r['btc_pre60'] = sg * (b0[4] / bp[4] - 1) * 100 if b0 and bp else None
    r['btc_during'] = sg * (b1[4] / b0[4] - 1) * 100 if b0 and b1 else None
    for m in (30, 60, 120, 240):
        seg = [c for c in after if c[0] <= t1 + m * 60000]
        if seg and seg[-1][0] - t1 >= (m - 2) * 60000:
            r[f'post{m}'] = sg * (seg[-1][4] / x - 1) * 100
            r[f'post{m}_vs_entry'] = sg * (seg[-1][4] / e - 1) * 100
            r[f'post{m}_best'] = max(sg * ((c[2] if sg > 0 else c[3]) / x - 1) * 100 for c in seg)
    notl = (t.get('margin') or 0) * (t.get('lev') or 1)
    r['ret_notional'] = 100 * t['whole'] / notl if notl else None
    r['path'] = [(fav(c[3] if sg > 0 else c[2]), fav(c[2] if sg > 0 else c[3]), fav(c[4]))
                 for c in rows if c[0] >= t0][:240]
    return r


# ─── 4. exit replays ────────────────────────────────────────────────────────
def replay(P, stop, target, be_at=None, lock_at=None, lock=0.0, trail_at=None, keep=0.5, time_min=None, need=0.3):
    sl, mfe = -stop, 0.0
    for m, (lo, hi, cl) in enumerate(P):
        if lo <= sl:
            return sl - FEE
        if hi >= target:
            return target - FEE
        mfe = max(mfe, hi)
        if be_at is not None and mfe >= be_at: sl = max(sl, FEE)
        if lock_at is not None and mfe >= lock_at: sl = max(sl, FEE + lock * mfe)
        if trail_at is not None and mfe >= trail_at: sl = max(sl, keep * mfe)
        if time_min is not None and m == time_min and mfe < need:
            return cl - FEE
    return (P[-1][2] if P else 0.0) - FEE


POLICIES = {
    'own stop & target only': {},
    'breakeven once +0.5%': dict(be_at=0.5),
    'breakeven once +1.0%': dict(be_at=1.0),
    'lock 30% of peak once +1%': dict(lock_at=1.0, lock=0.3),
    'trail 50% of peak once +1%': dict(trail_at=1.0, keep=0.5),
    'trail 60% of peak once +1.5%': dict(trail_at=1.5, keep=0.6),
    'exit at 30 min if never +0.3%': dict(time_min=30, need=0.3),
}


def exit_table(A):
    rows = [r for r in A if r.get('stop') and r.get('target') and len(r.get('path') or []) >= 30
            and r.get('ret_notional') is not None]
    if len(rows) < 8:
        return ['(too few trades with a recorded stop/target to replay)']
    coins = sorted({r['sym'] for r in rows}); half = {s: 'A' if i % 2 == 0 else 'B' for i, s in enumerate(coins)}
    cut = sorted(r['t_open'] for r in rows)[len(rows) // 2]
    grp = lambda r: ('early' if r['t_open'] < cut else 'late') + half[r['sym']]
    out = ['| exit rule (full size, 0.08% fees) | mean % per trade | beats actual in (of 4) |', '|---|---|---|']
    act = {id(r): r['ret_notional'] for r in rows}
    out.append(f"| **what the bot actually did** | **{st.mean(act.values()):+.3f}** | — |")
    for name, kw in POLICIES.items():
        v = {id(r): replay(r['path'], r['stop'], r['target'], **kw) for r in rows}
        beats = 0
        for g in sorted({grp(r) for r in rows}):
            d = [v[id(r)] - act[id(r)] for r in rows if grp(r) == g]
            beats += st.mean(d) > 0
        out.append(f"| {name} | {st.mean(v.values()):+.3f} | {beats}/4 |")
    return out


# ─── 5. market baseline (optional) ──────────────────────────────────────────
def market(A, work):
    coins = sorted({r['sym'] for r in A} | {'BTC', 'ETH', 'SOL', 'XRP', 'DOGE'})
    s0 = min(ms(r['t_open']) for r in A) - 4 * 3600000
    cache_p = os.path.join(work, 'universe5m.json')
    U = json.load(open(cache_p)) if os.path.exists(cache_p) else {}
    for c in coins:
        if c not in U:
            U[c] = candles(c + 'USDT', s0, int(time.time() * 1000), gran='5m')
    json.dump(U, open(cache_p, 'w'))
    setups = {1: [], -1: []}
    for rows in U.values():
        last = {1: -99, -1: -99}
        for i in range(36, len(rows) - 12, 3):
            c, c36 = rows[i][4], rows[i - 36][4]
            hi = max(x[2] for x in rows[i - 36:i + 1]); lo = min(x[3] for x in rows[i - 36:i + 1])
            pos = (c - lo) / (hi - lo) if hi > lo else 0.5; r3 = (c / c36 - 1) * 100
            for sg, okk in ((1, r3 >= 2 and pos >= 0.75), (-1, r3 <= -2 and pos <= 0.25)):
                if okk and i - last[sg] >= 12:
                    last[sg] = i
                    setups[sg].append((rows[i][0], sg * (rows[i + 12][4] / c - 1) * 100))
    for sg in setups:
        setups[sg].sort()
    keys = {sg: [s[0] for s in setups[sg]] for sg in setups}
    by_day = {}
    for sg in setups:
        for t, v in setups[sg]:
            by_day.setdefault((dt.datetime.fromtimestamp(t / 1000, IST).strftime('%d %b'), sg), []).append(v)
    for r in A:
        sg = 1 if r['side'] == 'LONG' else -1
        P = r.get('path') or []
        if len(P) < 61:
            continue
        t0 = ms(r['t_open'])
        a, b = bisect.bisect_left(keys[sg], t0 - 3600000), bisect.bisect_right(keys[sg], t0 + 3600000)
        base = [v for _, v in setups[sg][a:b]]
        if len(base) >= 5:
            r['fwd60'] = P[60][2]
            r['market60'] = st.mean(base)
            r['edge60'] = r['fwd60'] - r['market60']
    return by_day


# ─── report ─────────────────────────────────────────────────────────────────
def verdict(r):
    mfe, p60, p240 = r.get('mfe'), r.get('post60'), r.get('post240')
    if r['whole'] > 0:
        v = ('won; kept going %+.1f%% within 1 h — some profit left' % p60 if p60 is not None and p60 > 1 else
             'won; price reversed %+.1f%% after the exit — good exit' % p60 if p60 is not None and p60 < -0.5 else
             'won; exit close to fair')
        return v
    v = ('wrong from the start (never above %+.1f%%) — only not entering avoids it' % mfe if mfe is not None and mfe < 0.5
         else 'was up %+.1f%% first, then gave it back' % mfe if mfe is not None else 'no candles')
    if p240 is not None:
        v += ('; price went %+.1f%% further against after the exit — the exit saved money' % p240 if p240 < -1 else
              '; price recovered %+.1f%% after the exit — shaken out' % p240 if p240 > 1 else '; little changed after')
    return v


def write_report(A, ver, work, by_day=None):
    R = [r for r in A if r.get('close_ver') == ver]
    f = lambda v, p=1: '—' if v is None else f"{v:+.{p}f}"
    hm = lambda s: dt.datetime.fromisoformat(s).astimezone(IST).strftime('%d %b %H:%M')
    L = [f"# Trade forensics — {ver} ({len(R)} trades)\n",
         "All % are price moves in the trade's direction (+ = good for the trade). "
         "Best/worst = while open (Bitget 1-minute candles). Ran-up = the coin's move the trade's way in the 3 h "
         "before entry. Range = where the entry sat in the last 3 h (100% = at the extreme the trade chases). "
         "After exit = from the exit price.\n",
         "| # | opened → closed (IST) | coin | side | size | result | exit reason | best / worst | ran up 3h | range | after exit 1h / 4h | verdict |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for n, r in enumerate(R, 1):
        L.append(f"| {n} | {hm(r['t_open'])} → {hm(r['t_close'])[7:]} | {r['sym']} | {r['side'].lower()} | "
                 f"${(r.get('margin') or 0):.0f}×{r.get('lev') or 1} | **${r['whole']:+.2f}** | {(r.get('reason') or '').split(':')[0][:24]} | "
                 f"{f(r.get('mfe'))} / {f(r.get('mae'))} | {f(r.get('pre180'))}% | {100 * (r.get('range_pos') or 0):.0f}% | "
                 f"{f(r.get('post60'))} / {f(r.get('post240'))} | {verdict(r)} |")
    W = [r for r in R if r['whole'] > 0]; Lo = [r for r in R if r['whole'] <= 0]
    ng = [r for r in Lo if r.get('mfe') is not None and r['mfe'] < 0.5]
    L.append(f"\n**{ver}: {len(W)} wins / {len(Lo)} losses, net ${sum(r['whole'] for r in R):+.2f}.** "
             f"Losers never meaningfully up (best < +0.5%): {len(ng)} (${sum(r['whole'] for r in ng):+.2f}); "
             f"up first then gave it back: {len(Lo) - len(ng)} (${sum(r['whole'] for r in Lo if r not in ng):+.2f}).\n")
    L.append("## Would a different exit have done better? (every trade with a recorded stop, all versions)\n")
    L += exit_table(A)
    if by_day:
        L.append("\n## Market regime: the bot's entry style across ALL traded coins, next-hour result\n")
        L.append("| day | long chases: n / avg next hour | short chases: n / avg next hour |")
        L.append("|---|---|---|")
        for d in sorted({k[0] for k in by_day}, key=lambda s: dt.datetime.strptime(s + ' 2026', '%d %b %Y')):
            lg, sh = by_day.get((d, 1), []), by_day.get((d, -1), [])
            L.append(f"| {d} | {len(lg)} / {st.mean(lg) - FEE if lg else 0:+.3f}% | {len(sh)} / {st.mean(sh) - FEE if sh else 0:+.3f}% |")
        ed = [r['edge60'] for r in A if r.get('edge60') is not None]
        vr = [r['edge60'] for r in R if r.get('edge60') is not None]
        if ed:
            L.append(f"\nSelection edge (bot pick's next hour minus same-style market entries, same hour): "
                     f"all versions {st.mean(ed):+.3f}% (n={len(ed)}); {ver} {st.mean(vr) if vr else 0:+.3f}% (n={len(vr)}).\n")
    p = os.path.join(work, f'forensics_{ver}.md')
    open(p, 'w', encoding='utf-8').write('\n'.join(L) + '\n')
    return p


def main(argv):
    if len(argv) < 3:
        print(__doc__); return 2
    logdir, work = argv[1], argv[2]
    os.makedirs(work, exist_ok=True)
    trades = parse_trades(logdir)
    vers = [t['close_ver'] for t in trades if t.get('close_ver')]
    ver = argv[argv.index('--ver') + 1] if '--ver' in argv else (sorted(set(vers), key=lambda v: int(v[1:]))[-1] if vers else None)
    print(f"{len(trades)} closed trades parsed; report for {ver}")
    cache = fetch_all(trades, work)
    btc = {c[0]: c for c in cache.get('BTC', [])}
    A = [measure(t, cache.get(f"{t['sym']}|{t['t_open']}|{t['t_close']}", []), btc) for t in trades]
    by_day = market(A, work) if '--market' in argv else None
    out = write_report(A, ver, work, by_day)
    json.dump([{k: v for k, v in r.items() if k != 'path'} for r in A], open(os.path.join(work, 'analysis.json'), 'w'), indent=1, ensure_ascii=False)
    print(f"report: {out}")
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
