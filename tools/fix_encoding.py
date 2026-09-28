#!/usr/bin/env python3
"""Try to repair file encodings: attempt common decodings and re-save as UTF-8.
Backups are expected to already exist; this script will not overwrite backups.
Usage: python tools/fix_encoding.py file1 [file2 ...]
"""
import sys, os

COMMON = ['utf-8', 'utf-16', 'utf-16-le', 'utf-16-be', 'cp1252', 'latin-1']

def is_mostly_text(s):
    # heuristic: printable ratio
    if not s:
        return False
    printable = sum(1 for ch in s if ch == '\n' or 32 <= ord(ch) <= 126)
    return (printable / len(s)) > 0.85

def try_fix(path):
    b = open(path, 'rb').read()
    for enc in COMMON:
        try:
            txt = b.decode(enc)
        except Exception:
            continue
        if is_mostly_text(txt):
            # write utf-8
            open(path, 'w', encoding='utf-8').write(txt)
            print(f'CONVERTED: {path} <- {enc} -> utf-8')
            return True
    print(f'UNREPAIRED: {path} (encodings tried: {COMMON})')
    return False

def main():
    if len(sys.argv) < 2:
        print('Usage: fix_encoding.py file1 [file2 ...]')
        return 2
    rc = 0
    for p in sys.argv[1:]:
        if not os.path.exists(p):
            print(f'MISSING: {p}')
            rc |= 1
            continue
        ok = try_fix(p)
        if not ok:
            rc |= 1
    return rc

if __name__ == '__main__':
    raise SystemExit(main())
