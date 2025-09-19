p = r'd:\PjePlus\atos.py'
with open(p,'rb') as f:
    data=f.read()
lines=data.splitlines()
for i in range(2148-1,2208):
    b=lines[i]
    # show leading bytes
    lead=b[:20]
    print(f"{i+1:4}: {lead!r} ...")
