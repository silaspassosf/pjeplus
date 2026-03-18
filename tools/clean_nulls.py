#!/usr/bin/env python3
"""Safe null-byte cleaner.
Backs up each target file (same dir, .bak_TIMESTAMP) and removes any \x00 bytes.
Usage: python tools/clean_nulls.py path1 [path2 ...]
"""
import sys, shutil, os, time

def clean_file(path):
    if not os.path.exists(path):
        print(f'MISSING: {path}')
        return 1
    ts = int(time.time())
    bak = f"{path}.bak_{ts}"
    shutil.copy2(path, bak)
    with open(path, 'rb') as f:
        data = f.read()
    if b'\x00' not in data:
        print(f'NO_NULLS: {path}')
        return 0
    new = data.replace(b'\x00', b'')
    with open(path, 'wb') as f:
        f.write(new)
    print(f'CLEANED: {path} (backup: {bak})')
    return 0

def main():
    if len(sys.argv) < 2:
        print('Usage: clean_nulls.py file1 [file2 ...]')
        return 2
    rc = 0
    for p in sys.argv[1:]:
        rc |= clean_file(p)
    return rc

if __name__ == '__main__':
    raise SystemExit(main())
