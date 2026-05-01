import os
import pathlib
import re
root = pathlib.Path(r'd:\PjePlus')
excluded = {'ref', 'backup_pre_merge', '_archive', '.git', 'node_modules', 'archive'}
for dirpath, dirnames, filenames in os.walk(root):
    parts = pathlib.Path(dirpath).parts
    if any(p in excluded for p in parts):
        dirnames[:] = []
        continue
    dirnames[:] = [d for d in dirnames if d not in excluded]
    for fn in filenames:
        if not fn.endswith('.py'):
            continue
        path = pathlib.Path(dirpath) / fn
        try:
            text = path.read_text(encoding='utf-8', errors='ignore')
        except Exception:
            continue
        if re.search(r'from\s+Fix\s+import\s+\*', text):
            print(path)