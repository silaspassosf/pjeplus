import os, re

root = 'Script'
issues = []

for dirpath, dirs, files in os.walk(root):
    for f in files:
        if f.endswith('.js'):
            p = os.path.join(dirpath, f)
            try:
                s = open(p, 'r', encoding='utf-8').read()
            except Exception:
                continue
            n_try = len(re.findall(r"\btry\s*{", s))
            n_catch = len(re.findall(r"\bcatch\s*\(", s))
            n_finally = len(re.findall(r"\bfinally\b", s))
            if n_try > (n_catch + n_finally):
                issues.append((p, n_try, n_catch, n_finally))

if not issues:
    print('No heuristic issues found')
else:
    for p, t, c, f in issues:
        print(p, 'try=', t, 'catch=', c, 'finally=', f)
