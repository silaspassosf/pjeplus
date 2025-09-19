from pathlib import Path
p=Path(r'd:\PjePlus\atos.py')
s=p.read_text(encoding='utf-8')
start=2148; end=2220
snippet='\n'.join(s.splitlines()[start-1:end])
print('---SNIPPET START---')
print(snippet)
print('---SNIPPET END---')
import ast
try:
    ast.parse(snippet)
    print('SNIPPET PARSES OK')
except SyntaxError as e:
    print('SyntaxError:', e)
    print('lineno', e.lineno, 'offset', e.offset)
    import traceback; traceback.print_exc()
