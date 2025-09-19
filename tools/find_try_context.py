from pathlib import Path
p=Path(r'd:\PjePlus\atos.py')
s=p.read_text(encoding='utf-8')
lines=s.splitlines()
stack=[]
for i,l in enumerate(lines, start=1):
    stripped=l.lstrip()
    indent=len(l)-len(stripped)
    if stripped.startswith('try:'):
        stack.append((i,indent))
    elif stripped.startswith('except') or stripped.startswith('finally'):
        if stack:
            stack.pop()
        else:
            print('Unmatched except/finally at',i)
# print remaining try with nearby context
if stack:
    print('Remaining try entries (last 10):')
    for ln,ind in stack[-10:]:
        print('try at',ln,'indent',ind)
        for k in range(max(1,ln-3),ln+4):
            print(f'{k:5d}:', lines[k-1])
        print('---')
else:
    print('No remaining try entries')
