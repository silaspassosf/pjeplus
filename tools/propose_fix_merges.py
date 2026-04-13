"""Generate proposed consolidation groups for Fix/ modules.

Outputs JSON to stdout and to tools/propose_merges.json
"""
import os, json, ast, re

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
FIX = os.path.join(ROOT, 'Fix')

candidates = []
for dirpath, dirnames, filenames in os.walk(FIX):
    for fn in filenames:
        if not fn.endswith('.py'):
            continue
        path = os.path.join(dirpath, fn)
        rel = os.path.relpath(path, ROOT).replace('\\', '/')
        try:
            with open(path, 'rb') as f:
                lines = sum(1 for _ in f)
        except Exception:
            lines = None
        candidates.append({'path': rel, 'lines': lines})

# helper: pick group
def pick_group(path):
    lower = path.lower()
    name = os.path.basename(path).lower()
    if '/utils' in lower or name.startswith('utils_') or 'utils' in lower:
        return 'utils'
    if 'variaveis' in lower or name.startswith('variaveis'):
        return 'variaveis'
    if 'extracao' in lower or name.startswith('extracao'):
        return 'extracao'
    if 'progress' in lower or 'progresso' in lower or 'monitoramento' in lower:
        return 'progress'
    if 'documents' in lower or 'document' in lower:
        return 'documents'
    if 'selenium_base' in lower or 'driver' in lower:
        return 'selenium'
    if 'session' in lower:
        return 'session'
    if 'navigation' in lower:
        return 'navigation'
    if 'gigs' in lower:
        return 'gigs'
    if 'forms' in lower:
        return 'forms'
    return 'misc'

# Build groups for candidates with <600 lines prioritized
groups = {}
for c in candidates:
    grp = pick_group(c['path'])
    if grp not in groups:
        groups[grp] = []
    groups[grp].append(c)

# also collect small files (<300) and medium (300-600)
summary = {'total_files': len(candidates), 'total_lines': sum(x['lines'] or 0 for x in candidates), 'groups': {}}
for g,v in groups.items():
    small = [x for x in v if x['lines'] is not None and x['lines'] < 300]
    medium = [x for x in v if x['lines'] is not None and 300 <= x['lines'] <= 600]
    large = [x for x in v if x['lines'] is not None and x['lines'] > 600]
    summary['groups'][g] = {
        'count': len(v),
        'small_count': len(small),
        'medium_count': len(medium),
        'large_count': len(large),
        'files': v,
    }

# pick pilot groups
pilot = ['utils','progress','extracao']
proposal = {'summary': summary, 'pilot': pilot}

out_path = os.path.join(ROOT, 'tools', 'propose_merges.json')
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(proposal, f, ensure_ascii=False, indent=2)

print(json.dumps(proposal, ensure_ascii=False, indent=2))
