p = r'd:\PjePlus\atos.py'
text = open(p, 'r', encoding='utf-8').read()
lines = text.splitlines()
low = 1
high = len(lines)
first_bad = None
import ast
# linear scan to find first line where parsing fails
for i in range(200, len(lines), 100):
    try:
        ast.parse('\n'.join(lines[:i]))
    except SyntaxError as e:
        first_bad = i
        break
if first_bad is None:
    # fall back to full parse to see error
    try:
        ast.parse(text)
        print('Full file parses OK')
        raise SystemExit(0)
    except SyntaxError as e:
        first_bad = e.lineno
# binary search between prev chunk and first_bad
low = max(1, first_bad-200)
high = first_bad
while low < high:
    mid = (low+high)//2
    try:
        ast.parse('\n'.join(lines[:mid]))
        low = mid+1
    except SyntaxError:
        high = mid
print('First failing line approx:', low)
# show context
start = max(1, low-10)
end = min(len(lines), low+10)
for n in range(start,end+1):
    print(f"{n:5}: {lines[n-1]!r}")
