"""C462 missed-opportunity audit: replay the bot's OWN shipped geometry over the
real forward tape for every pair it analysed, and ask whether the refusals were
right. Geometry is not invented here -- R = 2 x ATR(14) (C372), target 2.00R
(C416_HARD_FLOOR_R), stop 0.75R (C377_HARD_STOP_R), maker both ways (C461)."""
import json, time, urllib.request, urllib.error, concurrent.futures as cf, statistics, sys

SCANS = json.load(open('/tmp/claude-0/scans.json'))
IST_OFFSET = 19800           # the bot's clock, confirmed against Bitget server time
DAY_UTC = "2026-09-16"
BASE = "https://api.bitget.com/api/v2/mix/market/candles"

def fetch(sym, limit=200):
    url = f"{BASE}?symbol={sym}USDT&productType=usdt-futures&granularity=15m&limit={limit}"
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=20) as r:
                d = json.loads(r.read())
            if d.get('code') != '00000' or not d.get('data'):
                return None
            return [[int(c[0])] + [float(x) for x in c[1:6]] for c in d['data']]
        except Exception:
            time.sleep(0.4 * (attempt + 1))
    return None

def atr_pct(bars, i, n=14):
    if i < n: return None
    tr = []
    for k in range(i - n + 1, i + 1):
        h, l, pc = bars[k][2], bars[k][3], bars[k-1][4]
        tr.append(max(h - l, abs(h - pc), abs(l - pc)))
    c = bars[i][4]
    return (sum(tr) / len(tr)) / c * 100.0 if c else None

TARGET_R, STOP_R, FEE_RT = 2.00, 0.75, 0.04    # C416 / C377 / C461 maker both

def simulate(bars, i0, side, R):
    """Entry at bars[i0] close. Adverse extreme first inside every bar."""
    e = bars[i0][4]
    sg = 1.0 if side == 'long' else -1.0
    tp = e * (1 + sg * TARGET_R * R / 100.0)
    sl = e * (1 - sg * STOP_R * R / 100.0)
    peak = 0.0
    for b in bars[i0 + 1:]:
        h, l = b[2], b[3]
        adverse = l if side == 'long' else h
        fav = h if side == 'long' else l
        peak = max(peak, sg * (fav / e - 1) * 100.0)
        if (side == 'long' and adverse <= sl) or (side == 'short' and adverse >= sl):
            return 'STOP', -STOP_R, peak, -(STOP_R * R) - FEE_RT
        if (side == 'long' and fav >= tp) or (side == 'short' and fav <= tp):
            return 'TARGET', TARGET_R, peak, (TARGET_R * R) - FEE_RT
    last = bars[-1][4]
    mv = sg * (last / e - 1) * 100.0
    return 'OPEN', mv / R, peak, mv - FEE_RT

def run(scan_key, label):
    pairs = SCANS[scan_key]
    hh, mm, ss = map(int, scan_key.split(':'))
    import datetime as dt
    t_ist = dt.datetime.fromisoformat(f"{DAY_UTC}T{scan_key}")
    t_utc = t_ist - dt.timedelta(seconds=IST_OFFSET)
    scan_ms = int(t_utc.replace(tzinfo=dt.timezone.utc).timestamp() * 1000)
    syms = sorted(pairs)
    data = {}
    with cf.ThreadPoolExecutor(8) as ex:
        for s, b in zip(syms, ex.map(fetch, syms)):
            if b: data[s] = b
    rows = []
    for s in syms:
        bars = data.get(s)
        if not bars: continue
        i0 = None
        for i, b in enumerate(bars):
            if b[0] <= scan_ms: i0 = i
            else: break
        if i0 is None or i0 < 20 or i0 >= len(bars) - 2: continue
        R = atr_pct(bars, i0)
        if not R: continue
        R *= 2.0
        info = pairs[s]
        side = info.get('dir') or 'long'
        res, r, peak, net = simulate(bars, i0, side, R)
        fwd_h = (bars[-1][0] - bars[i0][0]) / 3.6e6
        rows.append(dict(sym=s, side=side, reason=(info.get('reason') or 'hard gate / no score'),
                         score=info.get('score'), R=R, res=res, r=r, peak=peak, net=net, fwd=fwd_h))
    return rows

rows = run(sys.argv[1] if len(sys.argv) > 1 else '12:40:11', 'scan 1')
json.dump(rows, open('/tmp/claude-0/missed_rows.json', 'w'))
print(f"pairs replayed: {len(rows)}   forward window "
      f"{statistics.median(r['fwd'] for r in rows):.1f}h")
