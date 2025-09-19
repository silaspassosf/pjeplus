p='d:\\PjePlus\\atos.py'
lines=open(p,encoding='utf-8').read().splitlines()
stack=[]
for i in range(2120,2460):
    if i>len(lines): break
    line=lines[i-1]
    stripped=line.lstrip(' \t')
    indent=len(line)-len(stripped)
    sstr=stripped
    if sstr.startswith('try:'):
        stack.append((i,indent))
    elif sstr.startswith('except') or sstr.startswith('finally'):
        if not stack:
            print(f'UNMATCHED except at {i} indent={indent} line={sstr!r}')
        else:
            last_i,last_indent=stack[-1]
            # if indent matches last_indent, pop; else find matching
            if indent==last_indent:
                stack.pop()
            else:
                # find a try with same indent
                found=False
                for j in range(len(stack)-1,-1,-1):
                    if stack[j][1]==indent:
                        found=True
                        stack.pop(j)
                        break
                if not found:
                    print(f'MISMATCH at {i} indent={indent} last_try_at={last_i} last_indent={last_indent} line={sstr!r}')
print('remaining stack:', stack[-10:])
