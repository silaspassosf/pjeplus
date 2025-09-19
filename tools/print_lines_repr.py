import sys
path = r'd:\PjePlus\atos.py'
start = 2168
end = 2210
with open(path, 'r', encoding='utf-8') as f:
    lines = f.readlines()
for i in range(start-1, end):
    print(f"{i+1:5}: {repr(lines[i])}", end='')
