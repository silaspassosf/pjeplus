#!/usr/bin/env python3
import os, re, sys
from pathlib import Path
root = Path(__file__).resolve().parents[1]
init = root / 'Fix' / '__init__.py'
text = init.read_text(encoding='utf-8')
m = re.search(r"__all__\s*=\s*\[([\s\S]*?)\]", text)
if not m:
    print('NO __all__ FOUND')
    sys.exit(1)
arr_txt = m.group(1)
names = re.findall(r"'([^']+)'", arr_txt)

# files to search
exclude = {str(init)}
counts = {}
for name in names:
    counts[name]=0

for path in root.rglob('*.py'):
    pstr = str(path)
    if pstr in exclude:
        continue
    try:
        s = path.read_text(encoding='utf-8')
    except Exception:
        continue
    for name in names:
        if name in s:
            counts[name]+= s.count(name)

print('NAME\tCOUNT')
for k,v in sorted(counts.items(), key=lambda x: x[1]):
    print(f'{k}\t{v}')
