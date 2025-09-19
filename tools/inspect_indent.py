p = r'd:\PjePlus\atos.py'
start=2128
end=2230
with open(p,'r',encoding='utf-8') as f:
    lines=f.readlines()
for i in range(start-1,end):
    line=lines[i]
    stripped=line.lstrip('\t ')
    indent=len(line)-len(stripped)
    if 'try:' in stripped or stripped.strip().startswith('except') or stripped.strip().startswith('finally') or stripped.strip().startswith('#'):
        print(f"{i+1:4} indent={indent} |{line.rstrip()}|")
    else:
        # print only comments and try/except
        pass
