import ast
import pathlib
from collections import defaultdict
root = pathlib.Path(r'd:\PjePlus')
file_path = root / 'Fix' / '__init__.py'
text = file_path.read_text(encoding='utf-8')
exports = [name for name in ast.literal_eval(ast.parse(text).body[-1].value) if isinstance(name, str)]
# Actually __all__ might be last statement? simpler parse manually for __all__ assignment.
# But above may be too fragile; use regex fallback.
import re
match = re.search(r"__all__\s*=\s*\[([\s\S]*?)\]", text)
exports = re.findall(r"'([^']+)'", match.group(1)) if match else exports
excluded = {'ref', 'backup_pre_merge', '_archive', '.git', 'node_modules', 'archive'}
usage = defaultdict(list)
for path in root.rglob('*.py'):
    if any(part in excluded for part in path.parts):
        continue
    if path == file_path:
        continue
    try:
        source = path.read_text(encoding='utf-8')
    except Exception:
        continue
    try:
        tree = ast.parse(source)
    except Exception:
        continue
    imported_aliases = set()
    # find import Fix as alias
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == 'Fix':
                    imported_aliases.add(alias.asname or 'Fix')
        elif isinstance(node, ast.ImportFrom) and node.module == 'Fix':
            for alias in node.names:
                if alias.name in exports:
                    usage[alias.name].append(f'{path}:from/{alias.name}')
                elif alias.name == '*':
                    imported_aliases.add('*')
    # find attribute access on Fix or alias imported as Fix
    if imported_aliases:
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id in imported_aliases:
                attr = node.attr
                if attr in exports:
                    usage[attr].append(f'{path}:attr/{node.value.id}.{attr}')
    # for imported * from Fix, not determinable by AST. use text search for known exports.
    if '*' in imported_aliases:
        for name in exports:
            if re.search(rf'\b{name}\b', source):
                usage[name].append(f'{path}:star/{name}')
for name in exports:
    count = len(usage[name])
    print(f'{name}:{count}')
    for hit in usage[name][:5]:
        print('  ' + hit)
