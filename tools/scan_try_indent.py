from pathlib import Path
p = Path(r'd:\PjePlus\atos.py')
s = p.read_text(encoding='utf-8')
lines = s.splitlines()
stack = []
for i, line in enumerate(lines, start=1):
    stripped = line.lstrip('\t ')
    indent = len(line) - len(stripped)
    tok = stripped
    if tok.startswith('try:'):
        stack.append((i, indent, line))
    elif tok.startswith('except') or tok.startswith('finally'):
        if stack:
            stack.pop()
        else:
            print(f"Unmatched except/finally at {i}: {line!r}")
# After scan
if stack:
    print('Remaining unmatched try blocks:')
    for i, indent, line in stack[-20:]:
        print(f'  try at line {i}, indent {indent}: {line!r}')
else:
    print('No remaining try blocks')
print('\nContext around first remaining try if any:')
if stack:
    i, indent, line = stack[-1]
    start = max(1, i-6)
    end = min(len(lines), i+6)
    for n in range(start, end+1):
        print(f"{n:5}: {lines[n-1]!r}")
