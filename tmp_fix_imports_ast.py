import ast, os, pathlib
root = pathlib.Path(r'd:\PjePlus')
excluded_dirs = {'ref', 'backup_pre_merge', '_archive', '.git', 'node_modules', 'archive'}
exports = None
with open(root / 'Fix' / '__init__.py', encoding='utf-8') as f:
    text = f.read()
import re
match = re.search(r"__all__\s*=\s*\[([\s\S]*?)\]", text)
exports = re.findall(r"'([^']+)'", match.group(1)) if match else []
usage = set()
for dirpath, dirnames, filenames in os.walk(root):
    parts = pathlib.Path(dirpath).parts
    if any(part in excluded_dirs for part in parts):
        dirnames[:] = []
        continue
    dirnames[:] = [d for d in dirnames if d not in excluded_dirs]
    for filename in filenames:
        if not filename.endswith('.py'):
            continue
        path = pathlib.Path(dirpath) / filename
        if path == root / 'Fix' / '__init__.py':
            continue
        try:
            source = path.read_text(encoding='utf-8')
        except Exception:
            continue
        try:
            tree = ast.parse(source)
        except Exception:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module == 'Fix':
                for alias in node.names:
                    if alias.name in exports:
                        usage.add((alias.name, path, 'from'))
            elif isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
                if node.value.id == 'Fix' and node.attr in exports:
                    usage.add((node.attr, path, 'attr'))
for name, path, kind in sorted(usage):
    print(f'{name}:{kind}:{path}')
print('done')