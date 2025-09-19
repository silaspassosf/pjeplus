import ast
from pathlib import Path
p=Path(r'd:\PjePlus\atos.py')
s=p.read_text(encoding='utf-8')
try:
    ast.parse(s)
    print('AST OK')
except SyntaxError as e:
    print('SyntaxError:', e.msg)
    print('Line', e.lineno, 'Offset', e.offset)
    # print a few lines of context
    lines=s.splitlines()
    for i in range(max(1,e.lineno-5), e.lineno+5):
        print(f'{i:4d}: {lines[i-1]}')
    raise
