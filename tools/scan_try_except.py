from pathlib import Path
p=Path(r'd:\PjePlus\atos.py')
s=p.read_text(encoding='utf-8')
lines=s.splitlines()
stack=[]
for i,l in enumerate(lines, start=1):
    stripped=l.strip()
    if stripped.startswith('try:'):
        stack.append((i,'try'))
    if stripped.startswith('except') or stripped.startswith('finally'):
        if stack:
            stack.pop()
        else:
            print('Unmatched except/finally at',i)
print('\nRemaining try blocks on stack (latest 50):')
for it in stack[-50:]:
    print(it)
print('\nTotal try count:',sum(1 for l in lines if l.strip().startswith('try:')))
print('Total except/finally count:',sum(1 for l in lines if l.strip().startswith('except') or l.strip().startswith('finally')))