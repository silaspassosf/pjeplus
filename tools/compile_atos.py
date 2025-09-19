from pathlib import Path
p=Path(r'd:\PjePlus\atos.py')
s=p.read_text(encoding='utf-8')
try:
    compile(s, str(p), 'exec')
    print('OK')
except SyntaxError as se:
    print('SyntaxError:', se.msg)
    print('File:', se.filename)
    print('Line:', se.lineno)
    print('Offset:', se.offset)
    # print the problematic line
    lines=s.splitlines()
    if se.lineno and 1<=se.lineno<=len(lines):
        print('Source:', lines[se.lineno-1])
    raise
