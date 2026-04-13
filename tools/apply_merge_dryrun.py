"""Dry-run consolidation: analyze groups and report symbol collisions and top-level side-effects.

Reads tools/propose_merges.json created by propose_fix_merges.py
"""
import os, json, ast, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
PROPOSE = os.path.join(ROOT, 'tools', 'propose_merges.json')
FIX = os.path.join(ROOT, 'Fix')

if not os.path.exists(PROPOSE):
    print('Run tools/propose_fix_merges.py first')
    sys.exit(1)

with open(PROPOSE, 'r', encoding='utf-8') as f:
    proposal = json.load(f)

pilot = proposal.get('pilot', [])

def analyze_file(path):
    full = os.path.join(ROOT, path)
    try:
        src = open(full, 'r', encoding='utf-8').read()
    except Exception as e:
        return {'error': str(e)}
    try:
        node = ast.parse(src)
    except Exception as e:
        return {'parse_error': str(e)}
    exports = []
    top_level_effects = []
    for n in node.body:
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            exports.append(n.name)
        elif isinstance(n, ast.Assign):
            # assignments could be constants or module-level state; collect targets
            for t in n.targets:
                if isinstance(t, ast.Name):
                    exports.append(t.id)
        elif isinstance(n, ast.Expr):
            # docstring if first expr
            if getattr(n, 'value', None) and isinstance(n.value, ast.Str):
                continue
            # otherwise, flag as potential side-effect
            top_level_effects.append(ast.unparse(n) if hasattr(ast, 'unparse') else '<expr>')
        elif isinstance(n, ast.Import) or isinstance(n, ast.ImportFrom):
            continue
        else:
            # other statements (For, If, With, etc.) are potential side-effects
            top_level_effects.append(type(n).__name__)
    # dedupe exports and remove private
    exports = [e for e in dict.fromkeys(exports) if not e.startswith('_')]
    return {'exports': exports, 'top_level_effects': top_level_effects}

report = {'pilot': {}, 'issues': []}
for grp in pilot:
    files = [f['path'] for f in proposal['summary']['groups'].get(grp, {}).get('files', [])]
    report['pilot'][grp] = {'files': files, 'files_analyzed': {}, 'collisions': {}}
    symbol_map = {}
    for p in files:
        info = analyze_file(p)
        report['pilot'][grp]['files_analyzed'][p] = info
        if 'exports' in info:
            for s in info['exports']:
                symbol_map.setdefault(s, []).append(p)
        if info.get('top_level_effects'):
            report['pilot'][grp]['files_analyzed'][p]['has_side_effects'] = True
    # detect collisions
    collisions = {s: ps for s,ps in symbol_map.items() if len(ps) > 1}
    report['pilot'][grp]['collisions'] = collisions

out = os.path.join(ROOT, 'tools', 'dryrun_report.json')
with open(out, 'w', encoding='utf-8') as f:
    json.dump(report, f, ensure_ascii=False, indent=2)

print('Dry-run complete. Report written to tools/dryrun_report.json')
