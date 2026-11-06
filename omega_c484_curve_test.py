#!/usr/bin/env python3
"""C484: the session equity curve is visible from the first minute.

The curve itself is unchanged -- the report's own per-session list, one point
per status block (~8 min), served by /api/status. What changed is only when
the panel shows it: the page hid it until the list held 4 points, so after
every restart, reset or new session the chart was missing for ~25-30 minutes
(the operator: "the equity curve showed properly after sometime"). The report
header already records the starting equity, so there is a point from second 0.

1. the header records the starting equity as the curve's first point
2. /api/status serves exactly that list (as before: <= 80 points, no extras)
3. the page's own drawCurve(), executed in node: 0 points hidden, 1 point a
   flat line, 3 points drawn -- and nothing else about the chart changed
4. NEGATIVE CONTROL: the pre-C484 page from git hides it at 1 and at 3 points
"""
import os, sys, io, json, time, types, contextlib, importlib.util, subprocess, socket, re, tempfile, shutil
import urllib.request, urllib.error
os.environ.setdefault('OMEGA_BASE_PATH', '/tmp/omega_c484_curve')
os.makedirs(os.environ['OMEGA_BASE_PATH'], exist_ok=True)
TOKEN = 'c484-curve-token-0123456789abc'
os.environ['OMEGA_CTRL_TOKEN'] = TOKEN
REPO = os.path.dirname(os.path.abspath(__file__))
MARK = "shown from the session's FIRST point"
fails = []


def ok(n, c, d=''):
    print(f"  {'PASS' if c else 'FAIL'}  {n}" + (f"   {d}" if d else ''))
    if not c:
        fails.append(n)


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    with contextlib.redirect_stdout(io.StringIO()):
        spec.loader.exec_module(m)
    return m


def free_port():
    s = socket.socket(); s.bind(('127.0.0.1', 0)); p = s.getsockname()[1]; s.close(); return p


def serve(om, eq=252.81):
    pm = om.PositionsManager()
    bot = types.SimpleNamespace(cfg=om.Config(),
        portfolio=types.SimpleNamespace(positions=pm, equity=eq, get_live_equity=lambda *a: eq,
                                        get_stats=lambda *a: {'live_equity': eq}),
        mode_mgr=types.SimpleNamespace(mode=types.SimpleNamespace(value='normal'),
                                       session_start_equity=eq, _day_start_equity=eq),
        exchange=types.SimpleNamespace(get_current_price=lambda s: None))
    port = free_port()
    om.RemoteControl(bot, port=port).start(); time.sleep(0.6)
    return port


def get(port, path, raw=False):
    try:
        with urllib.request.urlopen(f'http://127.0.0.1:{port}{path}', timeout=6) as r:
            b = r.read().decode()
            return r.status, (b if raw else json.loads(b))
    except urllib.error.HTTPError as e:
        return e.code, ('' if raw else {})


def run_drawcurve(page, curve):
    """Execute the page's own drawCurve() in node against a stub DOM."""
    m = re.search(r'function drawCurve\(.*?\n}\n', page, re.S)
    if not m:
        return {'err': 'drawCurve not found'}
    js = ("const els={};function q(id){return els[id]||(els[id]={hidden:true,textContent:'',innerHTML:''})}\n"
          "function money(v){return '$'+Number(v).toFixed(2)}\n" + m.group(0) +
          "\ntry{drawCurve(%s)}catch(e){console.log(JSON.stringify({err:String(e)}));process.exit(0)}\n"
          "const s=q('curve').innerHTML;\n"
          "console.log(JSON.stringify({hidden:q('curvewrap').hidden,lab:q('curvelab').textContent,"
          "svg:s.length,nan:/NaN|Infinity/.test(s)}));" % json.dumps(curve))
    r = subprocess.run(['node', '-e', js], capture_output=True, text=True, timeout=20)
    try:
        return json.loads(r.stdout.strip().splitlines()[-1])
    except Exception:
        return {'err': r.stderr[-300:]}


print("=" * 64); print("C484: THE EQUITY CURVE IS THERE FROM THE FIRST MINUTE"); print("=" * 64)
om = load(os.path.join(REPO, 'omega_v60_reconstructed.py'), 'om484')

print("\n1. THE FIRST POINT EXISTS AT SESSION START")
tmpd = tempfile.mkdtemp(prefix='c484_')
rep = om._C462Report(os.path.join(tmpd, 'report.log'))
with contextlib.redirect_stdout(io.StringIO()):
    rep.header('C4xx', 'PAPER', 252.81, day_barrier=15.0)
ok("the report header records the starting equity", rep.equity_curve == [252.81], f"{rep.equity_curve}")

print("\n2. /api/status SERVES THE REPORT'S OWN CURVE, AS BEFORE")
om._c462_report.equity_curve = [252.81]
port = serve(om)
c, st = get(port, f'/api/status?t={TOKEN}')
ok("one point at start -> the status carries it", c == 200 and st.get('curve') == [252.81], f"{st.get('curve')}")
om._c462_report.equity_curve = [250.0 + 0.01 * k for k in range(500)]
c, st = get(port, f'/api/status?t={TOKEN}')
cv = st.get('curve') or []
ok("a long session is still decimated to 80 points", len(cv) == 80 and cv[0] == 250.0 and cv[-1] == 254.99, f"n={len(cv)}")
ok("nothing else was added to the payload", 'curve_span_h' not in st and 'unreal' not in st)

print("\n3. THE PAGE (its own drawCurve, run in node)")
c, page = get(port, f'/?t={TOKEN}', raw=True)
ok("the page calls drawCurve with the status curve, as before", 'drawCurve(d.curve);' in page)
r0 = run_drawcurve(page, [])
ok("0 points: hidden (nothing to draw yet)", r0.get('hidden') is True, f"{r0}")
r1 = run_drawcurve(page, [252.81])
ok("1 point: SHOWN as a flat line at the starting equity", r1.get('hidden') is False and r1.get('svg', 0) > 50
   and not r1.get('nan') and '1 sample' in r1.get('lab', ''), f"{r1}")
r3 = run_drawcurve(page, [252.81, 252.60, 252.95])
ok("3 points: shown", r3.get('hidden') is False and not r3.get('nan') and '3 samples' in r3.get('lab', ''), f"{r3}")
r9 = run_drawcurve(page, [250 + k * 0.1 for k in range(9)])
ok("many points: drawn exactly as before (low/high/samples label)",
   r9.get('hidden') is False and r9.get('lab', '').startswith('low $250.00') and '9 samples' in r9.get('lab', ''), f"{r9}")

print("\n4. NEGATIVE CONTROL: THE PRE-C484 PAGE, FROM GIT")
def _git(*a):
    return subprocess.run(['git', *a], capture_output=True, text=True, cwd=REPO).stdout
intro = _git('log', '--format=%H', '-S', MARK, '--', 'omega_v60_reconstructed.py').split()
ref = (intro[-1] + '^') if intro else 'HEAD'
old_src = _git('show', f'{ref}:omega_v60_reconstructed.py')
if MARK in old_src or not old_src:
    ok("the pre-C484 source can be rebuilt", False, f"{ref} already has the change")
else:
    tmp = os.path.join(tmpd, 'omega_pre484.py'); io.open(tmp, 'w', encoding='utf-8').write(old_src)
    om_old = load(tmp, 'om_pre484')
    port_o = serve(om_old)
    c, page_o = get(port_o, f'/?t={TOKEN}', raw=True)
    ok("pre-C484 page HIDES the curve at 1 point (the reported delay)", run_drawcurve(page_o, [252.81]).get('hidden') is True)
    ok("pre-C484 page HIDES it at 3 points too (~24 min into a session)",
       run_drawcurve(page_o, [252.81, 252.6, 252.95]).get('hidden') is True)
shutil.rmtree(tmpd, ignore_errors=True)
print("\n" + "=" * 64)
print("ALL CHECKS PASSED" if not fails else f"{len(fails)} FAILURE(S): {fails}")
sys.exit(1 if fails else 0)
