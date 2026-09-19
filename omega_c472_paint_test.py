#!/usr/bin/env python3
"""C472: one painter, tested on the lines that actually went wrong.

The operator's screenshot showed "taker flow -0.11" with 'taker' in red on a
MARKET row. C466 had already fixed exactly that for the console; C469 wrote a
second copy of the rules in JavaScript and brought it straight back.
"""
import ast, io, re, sys, types

SRC = '/home/user/tradecode/omega_v60_reconstructed.py'
src = io.open(SRC, encoding='utf-8').read()
fails = []
def ok(n, c, d=''):
    print(f"  {'PASS' if c else 'FAIL'}  {n}" + (f"   {d}" if d else ''))
    if not c: fails.append(n)

# lift the token table and the two painters and RUN them
ns = {'re': re}
for blk in ('_C466_PALETTES', '_C466_RESET', '_C466_STRIP', '_C466_TOKENS', '_C472_CLASS'):
    m = re.search(r'^' + blk + r'\s*=.*?(?=\n[A-Za-z_]\w*\s*=|\ndef |\nclass )', src, re.M | re.S)
    assert m, blk
    exec(compile(m.group(0), blk, 'exec'), ns)
for fn in ('_c472_escape', '_c472_paint_html', '_c466_paint'):
    m = re.search(rf'^def {fn}\(.*?(?=\n(?:def |class |_C4))', src, re.M | re.S)
    assert m, fn
    exec(compile(m.group(0), fn, 'exec'), ns)
paint = ns['_c472_paint_html']
console = ns['_c466_paint']
PAL = ns['_C466_PALETTES']['classic']

print("\n1. THE BUG FROM THE OPERATOR'S SCREENSHOT")
line = "  MARKET    TRENDING  bias +0.38  breadth +0.35  taker flow -0.11"
h = paint(line)
ok("'taker flow' is NOT painted as a loss",
   '<span class="l-b">taker' not in h and '>taker<' not in h, h[h.find('taker')-30:][:80])
ok("  and the C469 JavaScript rule WOULD have painted it (rule 16 control)",
   re.search(r'\b(LOSS|TAKER|taker)\b', line) is not None,
   "the old /\\b(LOSS|TAKER|taker)\\b/ matches 'taker' here")

print("\n2. THE COST SENSE IS STILL PAINTED")
for txt, want in (("C376 taker exit ARB", True),
                  ("mk9/tk3", True),
                  ("LOSS: CRV/USDT", True),
                  ("TAKER", True)):
    h = paint(f"  {txt}")
    ok(f"{txt!r:<26} painted as a cost", ('l-b' in h) == want, h[:90])

print("\n3. THE GOOD SENSE")
for txt in ("WIN: JUP/USDT", "C376 MAKER exit filled", "maker", "mk10"):
    ok(f"{txt!r:<26} painted as good", 'l-g' in paint(f"  {txt}"))

print("\n4. SIGN DECIDES ON NUMBERS, AND A SYMMETRIC BARRIER IS NEUTRAL")
ok("$+0.64 is a gain", 'l-g' in paint("  net $+0.64"))
ok("$-0.04 is a loss", 'l-b' in paint("  net $-0.04"))
ok("+1.36R is a gain", 'l-g' in paint("  +1.36R"))
ok("-0.75R is a loss", 'l-b' in paint("  -0.75R"))
h = paint("  start $250.00  day +/-0.68%")
ok("a +/- barrier is NOT painted red", 'l-b' not in h, h)

print("\n5. THE SERVER PAINTER AND THE CONSOLE PAINTER AGREE")
CORPUS = [
 "  MARKET    TRENDING  bias +0.38  breadth +0.35  taker flow -0.11",
 "  << 09:58  CLOSE  JUP LONG   WIN",
 "          @0.2545  +4.00% > $+0.64  held 39m  maker",
 "  DAY       real $+0.92  loss room $1.97 (0.79%)  0% used",
 "  FEES      $0.11  mk9/tk3  0.042% of eq",
 "  RECORD    5 closed  2W 3L  win 40%  payoff 1.97  avg $+0.04/tr",
 "13:49 | ERROR: something FAILED",
 "  ------------------------------------------",
 "  >> 09:19  OPEN   JUP LONG",
 "  INFO      1 tilted  flow/fund/news/oi on 119",
]
# Compare by ROLE, and un-escape first. The console also paints row LABELS
# (cyan) and rules (dim); those are not status colours and the browser
# deliberately handles labels with CSS instead. Comparing "everything the
# console coloured" against "everything the server coloured" measures that
# difference, not agreement about meaning. And comparing '&lt;&lt;' against
# '<<' measures HTML escaping. Neither is the question.
ROLE = {PAL['gain']: 'good', PAL['loss']: 'bad', PAL['warn']: 'warn'}
CLS = {'l-g': 'good', 'l-b': 'bad', 'l-w': 'warn'}
def unesc(t):
    return t.replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')
disagree = []
for line in CORPUS:
    srv = {(CLS[c], unesc(t)) for c, t in
           re.findall(r'<span class="(l-[gbw])">(.*?)</span>', paint(line))}
    con = {(ROLE[c], t) for c, t in
           re.findall(r'(\x1b\[[0-9;]*m)(.*?)\x1b\[0m', console(line, PAL))
           if c in ROLE}
    if srv != con:
        disagree.append((line[:44], sorted(srv - con), sorted(con - srv)))
ok(f"all {len(CORPUS)} corpus lines agree on every STATUS token", not disagree,
   f"{len(disagree)} disagreement(s)")
for d in disagree[:3]:
    print("      ", d)

print("\n6. LOG CONTENT CANNOT INJECT HTML")
evil = '  <script>alert(1)</script> "><img src=x onerror=alert(1)> & WIN'
h = paint(evil)
ok("tags are escaped", '<script>' not in h and '<img' not in h, h[:70])
ok("ampersand is escaped", '&amp;' in h)
ok("  but real tokens still paint", 'l-g' in h)

print("\n7. THE GREEN-EMOJI SEPARATOR IS GONE")
ok("C301's 18 green squares are replaced by an ASCII rule",
   '"\\U0001f7e9" * 18' not in src and '"-" * 36' in src)
# The changelog entry for C301 still NAMES the emoji, and should -- it is the
# historical record of what C301 did. What must be gone is any LIVE line that
# multiplies it into a bar.
_live = [l for l in src.split(chr(10))
         if '\\U0001f7e9' in l and 'logger.' in l]
ok("  no LIVE line builds an emoji bar any more", not _live, f"{_live[:1]}")

print("\n" + "=" * 62)
print("ALL CHECKS PASSED" if not fails else f"{len(fails)} FAILURE(S): {fails}")
sys.exit(1 if fails else 0)
