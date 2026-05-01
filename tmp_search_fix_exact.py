import pathlib
import re
import sys

root = pathlib.Path(r'd:\PjePlus')
pattern = re.compile(r'^\s*from\s+Fix\s+import\s+login_pje\b')
excluded = {'ref', 'backup_pre_merge', '_archive', '.git', 'node_modules'}
for path in root.rglob('*.py'):
    if any(part in excluded for part in path.parts):
        continue
    try:
        text = path.read_text(encoding='utf-8', errors='ignore')
    except Exception:
        continue
    for i, line in enumerate(text.splitlines(), 1):
        if pattern.match(line):
            print(f'{path}:{i}:{line}')
print('done')