import pathlib
import re
import sys
root = pathlib.Path(r'd:\PjePlus')
file_path = root / 'Fix' / '__init__.py'
text = file_path.read_text(encoding='utf-8')
export_section = re.search(r"__all__\s*=\s*\[([\s\S]*?)\]", text)
if not export_section:
    raise SystemExit('No __all__ found')
exports = re.findall(r"'([^']+)'", export_section.group(1))
excluded_dirs = {'ref', 'backup_pre_merge', '_archive', '.git', 'node_modules', 'archive'}
usage = {name: [] for name in exports}
for path in root.rglob('*.py'):
    if any(part in excluded_dirs for part in path.parts):
        continue
    if path == file_path:
        continue
    try:
        content = path.read_text(encoding='utf-8', errors='ignore')
    except Exception:
        continue
    for name in exports:
        if re.search(rf'\bfrom\s+Fix\s+import\s+.*\b{name}\b', content) or re.search(rf'\bFix\.{name}\b', content):
            for i, line in enumerate(content.splitlines(), 1):
                if re.search(rf'\bfrom\s+Fix\s+import\s+.*\b{name}\b', line) or re.search(rf'\bFix\.{name}\b', line):
                    usage[name].append(f'{path}:{i}:{line.strip()}')
                    break
for name, hits in usage.items():
    if hits:
        print(f'USED {name}')
        for hit in hits[:5]:
            print('  ' + hit)
    else:
        print(f'UNUSED {name}')
print('done')