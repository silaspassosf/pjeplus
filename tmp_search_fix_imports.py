import pathlib
import re
import sys

root = pathlib.Path(r'd:\PjePlus')
regex = re.compile(r'^(?:from\s+Fix\s+import|import\s+Fix(?:\b|$))')
excluded = {'ref', 'backup_pre_merge', '.git', 'node_modules'}
count = 0
for path in root.rglob('*.py'):
    if any(part in excluded for part in path.parts):
        continue
    try:
        text = path.read_text(encoding='utf-8', errors='ignore')
    except Exception:
        continue
    for i, line in enumerate(text.splitlines(), 1):
        if regex.search(line.strip()):
            print(f'{path}:{i}:{line}')
            count += 1
            if count >= 300:
                sys.exit(0)
print('TOTAL', count)