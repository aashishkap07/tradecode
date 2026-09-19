#!/usr/bin/env python3
"""C479-B: an alert must reach the screen because of its LEVEL, not its wording.

The console filter's own rule 2 is "anything wrong reaches the screen". It
implemented that by matching fifteen substrings against the message text, so
every warning or error whose wording missed all fifteen was dropped from the
console AND the session log. An AST scan of the bot found 60 of 98 such calls
invisible -- including the emergency liquidation handler.

Rule 16: section 5 runs the same cases against the PRE-C479-B filter and
requires them to be dropped. If section 5 passes, this test is not testing.
"""
import ast, io, logging, os, re, sys, types

SRC = '/home/user/tradecode/omega_v60_reconstructed.py'
raw = io.open(SRC, encoding='utf-8').read()

fails = []
def ok(n, c, d=''):
    print(f"  {'PASS' if c else 'FAIL'}  {n}" + (f"   {d}" if d else ''))
    if not c: fails.append(n)


def load_filter(src_text):
    """Lift the filter class plus the two helpers it closes over."""
    tree = ast.parse(src_text)
    want = {'_c465_flagged', '_c463_is_report', '_C460ConsoleFilter', '_C460Verbose'}
    body = [n for n in tree.body
            if (isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n.name in want)]
    got = {n.name for n in body}
    missing = want - got
    if missing:
        raise SystemExit(f"cannot lift {missing} -- the test needs fixing, not the code")
    g = {'logging': logging, 're': re, 'os': os, '__import__': __import__}
    exec(compile(ast.Module(body=body, type_ignores=[]), '<f>', 'exec'), g)
    g['cfg_console_verbose'] = g['_C460Verbose']()
    # rebind the class's globals so it sees cfg_console_verbose / the helpers
    g['_C460ConsoleFilter'].filter.__globals__.update(g)
    return g['_C460ConsoleFilter']()


def rec(msg, level=logging.INFO):
    r = logging.LogRecord('OmegaV60', level, __file__, 1, msg, (), None)
    return r


print("=" * 62)
print("C479-B: THE LEVEL IS THE SIGNAL, NOT THE WORDING")
print("=" * 62)

F = load_filter(raw)

# The real messages the AST scan found invisible. Text taken from the bot.
REAL_ALERTS = [
    ("\U0001f6a8 EMERGENCY TRIGGERED: Unrealized -8.4% (threshold -8.0%)", logging.WARNING),
    ("\U0001f6a8 Loss worsening (-8.4% → -9.1%). Closing all.",        logging.WARNING),
    ("Save state error: disk full",                                        logging.ERROR),
    ("Load state error: corrupt json",                                     logging.ERROR),
    ("Order error BTCUSDT: insufficient margin",                           logging.ERROR),
    ("Close position error ETHUSDT: timeout",                              logging.ERROR),
    ("Exchange connect error: name resolution",                            logging.ERROR),
    ("Save positions error: read-only filesystem",                         logging.ERROR),
    ("Scan error: list index out of range",                                logging.ERROR),
    ("⚠️ Double-close prevented: BTCUSDT already closed",        logging.WARNING),
    ("⏳ Observing for 60s before deciding...",                        logging.WARNING),
    ("\U0001f6a8 CONTROL PANEL DID NOT OPEN — port 8138 is already in use.",
                                                                           logging.ERROR),
    ("   The bot itself is FINE and is trading normally. What is missing is",
                                                                           logging.ERROR),
]

print("\n1. EVERY REAL ALERT NOW REACHES THE SCREEN")
bad = [m for m, lv in REAL_ALERTS if not F.filter(rec(m, lv))]
ok("all 13 of the messages the AST scan found invisible now pass",
   not bad, f"still dropped: {bad[:2]}" if bad else "")

print("\n2. THE LEVEL ALONE IS ENOUGH -- WORDING IS IRRELEVANT")
nonsense = "zzz qqq this wording matches nothing in any list zzz"
ok("a WARNING with no alert word passes",  F.filter(rec(nonsense, logging.WARNING)))
ok("an ERROR with no alert word passes",   F.filter(rec(nonsense, logging.ERROR)))
ok("a CRITICAL with no alert word passes", F.filter(rec(nonsense, logging.CRITICAL)))
ok("the same text at INFO is still dropped (the filter still filters)",
   not F.filter(rec(nonsense, logging.INFO)))
ok("  and at DEBUG",  not F.filter(rec(nonsense, logging.DEBUG)))

print("\n3. LOWER CASE 'error:' WAS THE WHOLE BUG -- C462'S DEFECT, SECOND LIST")
ok("'ERROR' in caps passed even before (that is why this hid so long)",
   F.filter(rec("ERROR something", logging.INFO)))
ok("'error:' in lower case was NOT matched by the text rules",
   not F.filter(rec("Save state error: disk full", logging.INFO)))
ok("  ...and now passes on its level instead",
   F.filter(rec("Save state error: disk full", logging.ERROR)))

print("\n4. NO REGRESSION: THE FILTER STILL SUPPRESSES PER-PAIR WORKING")
NOISE = [
    "\U0001f6d1 USELESS: LONG at RSI 93 ... brake 30%",
    "⚡ BTCUSDT: mom=-0.13 vol=-0.01 tec=-0.03",
    "\U0001f4ca ETHUSDT: DRI -0.059 retention 0.81",
    "⚙ SOLUSDT: flow baseline set",
]
kept = [m for m in NOISE if F.filter(rec(m, logging.INFO))]
ok("per-pair INFO working is still dropped", not kept, f"leaked: {kept}" if kept else "")
ok("  but a per-pair line at ERROR is NOT dropped (a crash in a pair path is a crash)",
   F.filter(rec("⚡ BTCUSDT: mom=-0.13 vol=-0.01", logging.ERROR)))
ok("the dashboard still passes at INFO",
   F.filter(rec("│ EQUITY    $250.00  30 markets", logging.INFO)))
ok("a named decision still passes at INFO",
   F.filter(rec("C435-2 cleared 3 kept 1", logging.INFO)))

# replay a real detail log: the suppression rate must not collapse
import glob
det = sorted(glob.glob('/home/user/tradecode/omega_detail_*.log'))
if det:
    lines = io.open(det[-1], encoding='utf-8', errors='replace').read().splitlines()
    body = [l.split('|', 1)[1].strip() for l in lines if '|' in l]
    if body:
        passed = sum(1 for l in body if F.filter(rec(l, logging.INFO)))
        pct = 100.0 * passed / len(body)
        ok(f"replaying {len(body)} real INFO lines, the screen still takes a minority",
           pct < 50.0, f"{pct:.0f}% would print ({os.path.basename(det[-1])})")
    else:
        ok("a real detail log could be replayed", False, "no parseable lines")
else:
    ok("a real detail log could be replayed", False, "no detail log on disk")

print("\n4b. C479-C: AN ALARM THAT CANNOT BE CLEARED IS A FALSE ALARM LEFT STANDING")
PANEL_INFO = [
    "\U0001f310 Remote control on http://0.0.0.0:8138 \u2014 TOKEN REQUIRED",
    "   \U0001f4f1 Same WiFi: http://192.168.1.9:8138/?t=<your token>",
    "   \U0001f30d Internet: put a Cloudflare Tunnel in front of this port.",
    "       See deploy/DEPLOY.md \u2014 one command, no open ports, free.",
    "\U0001f310 Remote control on http://127.0.0.1:8138 \u2014 LOCALHOST ONLY",
    "   \U0001f512 No OMEGA_CTRL_TOKEN is set, so it is NOT reachable from the",
    "      network. Set one to expose it: export OMEGA_CTRL_TOKEN='...'",
    "\u2705 CONTROL PANEL IS BACK \u2014 the port freed up after 1 try.",
]
miss = [m for m in PANEL_INFO if not F.filter(rec(m, logging.INFO))]
ok("every control-panel line reaches the readable log at INFO",
   not miss, f"still hidden: {miss[:2]}" if miss else "")
ok("  specifically: the RECOVERY notice, so the ERROR can be cleared",
   F.filter(rec("\u2705 CONTROL PANEL IS BACK \u2014 the port freed up after 1 try.",
                logging.INFO)))
ok("  and the panel's own URL, which the operator needs to reach the dashboard",
   F.filter(rec("\U0001f310 Remote control on http://0.0.0.0:8138 \u2014 TOKEN REQUIRED",
                logging.INFO)))
ok("  ...without letting per-pair working back in",
   not F.filter(rec("\u26a1 BTCUSDT: mom=-0.13 vol=-0.01", logging.INFO)))

print("\n5. NEGATIVE CONTROL: THE OLD FILTER MUST DROP THESE")
MARKER = "            if record.levelno >= logging.WARNING:\n                return True\n"
if raw.count(MARKER) != 1:
    ok("the pre-C479-B filter can still be reconstructed", False,
       f"marker found {raw.count(MARKER)}x -- THIS TEST CAN NO LONGER FAIL")
else:
    OLDF = load_filter(raw.replace(MARKER, ""))
    dropped = [m for m, lv in REAL_ALERTS if not OLDF.filter(rec(m, lv))]
    ok("the old filter hid most of these alerts", len(dropped) >= 10,
       f"{len(dropped)} of {len(REAL_ALERTS)} were invisible")
    ok("  including the EMERGENCY liquidation handler",
       not OLDF.filter(rec(REAL_ALERTS[0][0], REAL_ALERTS[0][1])))
    ok("  and 'Save state error:'",
       not OLDF.filter(rec("Save state error: disk full", logging.ERROR)))
    ok("  while the new one shows every one of them",
       all(F.filter(rec(m, lv)) for m, lv in REAL_ALERTS))

print("\n" + "=" * 62)
print("ALL CHECKS PASSED" if not fails else f"{len(fails)} FAILURE(S): {fails}")
sys.exit(1 if fails else 0)
