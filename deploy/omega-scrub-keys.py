#!/usr/bin/env python3
"""C540: redact every value stored in api_keys.json from the logs about to be pushed, by its LITERAL text.

    python3 omega-scrub-keys.py /home/omega/omega/data/api_keys.json /home/omega/omega/.logpush/logs

The push script's regex scrub only catches a key that sits next to a label such as "api_key=". This one does
not care what surrounds a key: any string of 8+ characters stored anywhere in api_keys.json (exchange keys and
secrets, nested sections included) is replaced by <KEY-REDACTED> in every file under the folder, gzip-rotated
logs included. Exit 0 when nothing is left; 1 if a value survived (the push script then refuses to push);
3 if api_keys.json cannot be read (also no push). It prints counts only -- never a value.
"""
import gzip
import json
import os
import sys

MARK = b'<KEY-REDACTED>'


def values(keyfile):
    d = json.load(open(keyfile))
    out = set()

    def walk(x):
        if isinstance(x, dict):
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
        elif isinstance(x, str) and len(x.strip()) >= 8:
            out.add(x.strip().encode('utf-8'))
    walk(d)
    return sorted(out, key=len, reverse=True)          # the longest first: a key inside a longer one is still caught


def scrub_bytes(b, vals):
    for v in vals:
        if v in b:
            b = b.replace(v, MARK)
    return b


def main(keyfile, root):
    try:
        vals = values(keyfile)
    except Exception:
        print('omega-scrub-keys: api_keys.json could not be read')
        return 3
    changed = left = 0
    for dp, _dn, fn in os.walk(root):
        for f in fn:
            p = os.path.join(dp, f)
            try:
                raw = open(p, 'rb').read()
            except Exception:
                continue
            gz = f.endswith('.gz')
            try:
                body = gzip.decompress(raw) if gz else raw
            except Exception:
                body, gz = raw, False
            new = scrub_bytes(body, vals)
            if new != body:
                changed += 1
                with open(p, 'wb') as h:
                    h.write(gzip.compress(new) if gz else new)
            if any(v in new for v in vals):
                left += 1
    print(f'omega-scrub-keys: {len(vals)} value(s) checked, {changed} file(s) redacted, {left} still holding one')
    return 1 if left else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1], sys.argv[2]))
