#!/usr/bin/env python3
"""Does YOUR terminal do colour? Run this in Pydroid3 and look at the answer.

    python3 omega_color_test.py

I could not settle this from documentation -- Pydroid 3 ships a terminal
emulator, and terminal emulators support ANSI colour, but its non-interactive
output window may not. So the bot decides at boot with C466_COLOR='auto'
(paint when stdout is a real terminal), and this tells you whether that
decision was right on YOUR device.

Nothing here touches the bot. The log FILES are never coloured whatever you
choose -- colour goes to the console alone.
"""
import sys

R = '\033[0m'
P = {'dim': '\033[2m', 'lbl': '\033[36m', 'gain': '\033[32m',
     'loss': '\033[31m', 'warn': '\033[33m', 'head': '\033[1;37m'}
CVD = {'dim': '\033[2m', 'lbl': '\033[36m', 'gain': '\033[94m',
       'loss': '\033[95m', 'warn': '\033[33m', 'head': '\033[1;37m'}


def sample(pal, name):
    print(f"  {pal['head']}--- {name} ---{R}")
    print(f"  {pal['lbl']}EQUITY{R}    $250.82  unreal {pal['gain']}$+0.38{R}")
    print(f"  {pal['lbl']}SESSION{R}   {pal['gain']}$+0.82{R} {pal['gain']}+0.33%{R}")
    print(f"  {pal['lbl']}DAY{R}       +/-0.68%  48% used")
    print(f"            [{pal['gain']}------------|######------{R}]")
    print(f"  {pal['lbl']}FEES{R}      $0.01  {pal['gain']}mk3{R}/{pal['loss']}tk0{R}")
    print(f"  {pal['dim']}  <<{R} 22:36  CLOSE  UNI LONG   {pal['gain']}WIN{R}")
    print(f"       {pal['gain']}+4.00%{R} > {pal['gain']}$+0.48{R}  {pal['gain']}+1.03R{R}  {pal['gain']}maker{R}")
    print(f"  {pal['dim']}  <<{R} 23:10  CLOSE  ZEC LONG   {pal['loss']}LOSS{R}")
    print(f"       {pal['loss']}-1.45%{R} > {pal['loss']}$-0.44{R}  {pal['loss']}-0.75R{R}  {pal['loss']}TAKER{R}")
    print(f"  {pal['dim']}----------------------------------------{R}")
    print()


print()
print("  OMEGA colour check")
print("  ==================")
print()
try:
    tty = sys.stdout.isatty()
except Exception:
    tty = False
print(f"  stdout.isatty() = {tty}   ->  'auto' would turn colour "
      f"{'ON' if tty else 'OFF'} here")
print()
sample(P, 'classic  (green gain / red loss)')
sample(CVD, 'cvd  (blue gain / magenta loss, for red-green colour blindness)')
print("  WHAT TO DO:")
print("   - The lines above are COLOURED       -> your terminal is fine.")
print("     If 'auto' said OFF, set C466_COLOR = 'on' in Config to force it.")
print("   - You see [32m and [0m as TEXT       -> no colour support.")
print("     Set C466_COLOR = 'off' in Config. Everything still works;")
print("     the dashboard just stays monochrome, and the log files were")
print("     never coloured anyway.")
print("   - Green and red are hard to tell apart -> set")
print("     C466_PALETTE = 'cvd'  (the second sample above).")
print()
