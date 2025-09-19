from pathlib import Path
p=Path(r'd:\PjePlus\atos.py')
lines=p.read_text(encoding='utf-8').splitlines()
for i in range(2080,2241):
    print(f'{i}: {repr(lines[i-1])}')
