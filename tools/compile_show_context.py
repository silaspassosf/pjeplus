import ast, traceback
p = r'd:\PjePlus\atos.py'
s = open(p, 'r', encoding='utf-8').read()
try:
    ast.parse(s)
    print('Parsed OK')
except SyntaxError as e:
    print('SyntaxError: ', e)
    lineno = e.lineno
    offset = e.offset
    print('line', lineno, 'offset', offset)
    lines = s.splitlines()
    for i in range(max(1, lineno-5), min(len(lines), lineno+5)+1):
        pointer = '->' if i==lineno else '  '
        print(f"{pointer} {i:4}: {lines[i-1]!r}")
    raise
except Exception:
    traceback.print_exc()
