import tokenize, io
path = r'd:\PjePlus\atos.py'
s = open(path,'rb').read()
buf = io.BytesIO(s)
stack = []
for toknum, tokval, start, end, line in tokenize.tokenize(buf.readline):
    if toknum == tokenize.NAME and tokval == 'try':
        stack.append(('try', start))
    elif toknum == tokenize.NAME and tokval == 'except':
        if stack:
            # pop last try
            stack.pop()
        else:
            print('unmatched except at', start)
    elif toknum == tokenize.NAME and tokval == 'finally':
        if stack:
            stack.pop()
        else:
            print('unmatched finally at', start)
# print remaining
if stack:
    print('Remaining try tokens:')
    for t, pos in stack[-20:]:
        print(t, pos)
else:
    print('No remaining try tokens')
