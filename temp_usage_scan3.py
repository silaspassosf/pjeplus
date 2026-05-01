import ast
import pathlib

path = pathlib.Path('Fix/core.py')
src = path.read_text(encoding='utf-8')
mod = ast.parse(src)
imported = []
used = set()
for node in ast.walk(mod):
    if isinstance(node, ast.Import):
        for n in node.names:
            imported.append(n.asname or n.name)
    elif isinstance(node, ast.ImportFrom):
        for n in node.names:
            if n.name == '*':
                continue
            imported.append(n.asname or n.name)
    elif isinstance(node, ast.Name):
        used.add(node.id)

print('imported count', len(imported))
print(imported)
print('dead imports')
for name in imported:
    if name not in used:
        print(name)
