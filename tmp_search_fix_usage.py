import pathlib
import re
import sys
root = pathlib.Path(r'd:\PjePlus')
excluded = {'ref', 'backup_pre_merge', '_archive', '.git', 'node_modules', 'archive'}
patterns = {
    'login_pje': re.compile(r'\b(?:login_pje|Fix\.login_pje|from\s+Fix\s+import\s+login_pje)\b'),
    'configurar_recovery_driver': re.compile(r'\b(?:configurar_recovery_driver|Fix\.configurar_recovery_driver|from\s+Fix\s+import\s+configurar_recovery_driver)\b'),
}
for path in root.rglob('*.py'):
    if any(part in excluded for part in path.parts):
        continue
    try:
        text = path.read_text(encoding='utf-8', errors='ignore')
    except Exception:
        continue
    lines = text.splitlines()
    for i, line in enumerate(lines, 1):
        if line.strip().startswith('#'):
            continue
        for name, pattern in patterns.items():
            if pattern.search(line):
                print(f'{path}:{i}:{name}:{line.strip()}')
print('done')