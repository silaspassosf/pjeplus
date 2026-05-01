"""
erase_analysis.py - Deep analysis of x.py dependency tree.
Traces all imports from x.py, maps function definitions vs usage.
Output goes directly to erase_output.txt to avoid console encoding issues.
"""
import ast
import os
import sys
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(r'd:\PjePlus')
OUTPUT_FILE = ROOT / 'tools' / 'erase_output.txt'

EXCLUDED_DIRS = {
    'bianca', 'peticao', 'triagem',
    '__pycache__', '.git', '.git_old_20260319_171141',
    'aider-env', '_archive', '-++backups',
    '.aider.tags.cache.v4', '.claude', '.qwen', '.vscode',
    '.github', '.githooks', 'outros projetos', 'ORIGINAIS',
    'backup_pre_merge', 'ref', 'tools', 'scripts', 'AHK',
    'cache', 'cookies_sessoes', 'logs_execucao', 'docs',
}

ANALYSIS_DIRS = {'Fix', 'Prazo', 'PEC', 'Mandado', 'atos', 'core', 'SISB', 'busca', 'carta', 'api', 'AVJT', 'Agente', 'Aud1', 'maispje'}


def collect_py_files():
    files = []
    for root, dirs, fnames in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d.lower() not in {x.lower() for x in EXCLUDED_DIRS}]
        for f in fnames:
            if f.endswith('.py'):
                fpath = os.path.join(root, f)
                files.append(fpath)
    return files


def parse_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            source = f.read()
        tree = ast.parse(source, filename=filepath)
    except SyntaxError:
        return None

    defs = []
    imports = []
    calls = []
    names_used = set()

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            defs.append({
                'name': node.name,
                'line': node.lineno,
                'end_line': getattr(node, 'end_lineno', node.lineno),
            })
        elif isinstance(node, ast.ClassDef):
            defs.append({
                'name': node.name,
                'line': node.lineno,
                'end_line': getattr(node, 'end_lineno', node.lineno),
                'type': 'class',
            })
        elif isinstance(node, ast.Import):
            for alias in node.names:
                imports.append({
                    'module': alias.name,
                    'name': alias.asname or alias.name,
                    'line': node.lineno,
                    'type': 'import',
                })
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ''
            for alias in node.names:
                imports.append({
                    'module': module,
                    'name': alias.name,
                    'asname': alias.asname,
                    'line': node.lineno,
                    'type': 'from',
                })
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                calls.append(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                calls.append(node.func.attr)
        elif isinstance(node, ast.Name):
            names_used.add(node.id)
        elif isinstance(node, ast.Attribute):
            names_used.add(node.attr)

    return {
        'defs': defs,
        'imports': imports,
        'calls': calls,
        'names_used': names_used,
    }


def get_rel_path(filepath):
    try:
        return str(Path(filepath).relative_to(ROOT))
    except ValueError:
        return filepath


def main():
    out = open(OUTPUT_FILE, 'w', encoding='utf-8')
    def p(msg=""):
        out.write(msg + "\n")
        out.flush()

    p("=" * 80)
    p("ERASE ANALYSIS - Mapping x.py dependency tree")
    p("=" * 80)

    all_files = collect_py_files()
    p(f"\nTotal .py files in scope: {len(all_files)}")

    file_data = {}
    for f in all_files:
        rel = get_rel_path(f)
        parsed = parse_file(f)
        if parsed:
            file_data[rel] = parsed

    p(f"Successfully parsed: {len(file_data)} files")

    scope_modules = []
    for rel in sorted(file_data.keys()):
        parts = rel.replace('\\', '/').split('/')
        if parts[0] in ANALYSIS_DIRS or rel == 'x.py' or rel in ('dom.py', 'p2.py', 'f.py', 'monitor.py', 'utilitarios_processamento.py', 'apiaud.py'):
            scope_modules.append(rel)

    p(f"\nModules in analysis scope: {len(scope_modules)}")

    # Build global usage map
    global_usage = defaultdict(set)
    for rel, data in file_data.items():
        for name in data['names_used']:
            global_usage[name].add(rel)
        for call in data['calls']:
            global_usage[call].add(rel)

    # Also track which functions are imported explicitly
    import_targets = defaultdict(set)  # {func_name: set of files that import it}
    for rel, data in file_data.items():
        for imp in data['imports']:
            if imp['type'] == 'from':
                import_targets[imp['name']].add(rel)

    p("\n" + "=" * 80)
    p("PER-FILE ANALYSIS: Functions defined vs used")
    p("=" * 80)

    results = {}

    for rel in sorted(scope_modules):
        data = file_data[rel]
        if not data['defs']:
            continue

        file_defs = data['defs']
        used = []
        unused = []

        for d in file_defs:
            name = d['name']
            if name.startswith('__') and name.endswith('__'):
                continue

            # Check usage outside this file
            users = global_usage.get(name, set())
            external_users = users - {rel}

            # Check imports
            importers = import_targets.get(name, set()) - {rel}

            all_external = external_users | importers

            # Internal use
            internal_use = name in data['names_used'] or name in data['calls']

            if all_external:
                used.append({
                    'name': name,
                    'line': d['line'],
                    'used_by': sorted(all_external)[:5],
                    'total_users': len(all_external),
                })
            elif internal_use:
                used.append({
                    'name': name,
                    'line': d['line'],
                    'used_by': ['(internal only)'],
                    'total_users': 0,
                })
            else:
                unused.append({
                    'name': name,
                    'line': d['line'],
                })

        if unused:
            results[rel] = {
                'total_defs': len(file_defs),
                'used_count': len(used),
                'unused_count': len(unused),
                'unused': unused,
                'used': used,
            }

    # Print results
    total_unused = 0
    for rel in sorted(results.keys()):
        r = results[rel]
        if r['unused_count'] == 0:
            continue
        total_unused += r['unused_count']
        p(f"\n{'-' * 70}")
        p(f"FILE: {rel}")
        p(f"   Total defs: {r['total_defs']} | Used: {r['used_count']} | UNUSED: {r['unused_count']}")
        p(f"   UNUSED functions:")
        for u in r['unused']:
            p(f"      - {u['name']} (line {u['line']})")

    p(f"\n{'=' * 80}")
    p(f"TOTAL UNUSED FUNCTIONS: {total_unused}")
    p(f"{'=' * 80}")

    # Save JSON
    output_json = ROOT / 'tools' / 'erase_analysis_results.json'
    serializable = {}
    for rel, r in results.items():
        sr = dict(r)
        sr['used'] = [dict(u) for u in r['used']]
        sr['unused'] = [dict(u) for u in r['unused']]
        for u in sr['used']:
            if isinstance(u.get('used_by'), set):
                u['used_by'] = sorted(u['used_by'])
        serializable[rel] = sr
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(serializable, f, indent=2, ensure_ascii=False)

    # Import chain from x.py
    p(f"\n{'=' * 80}")
    p("IMPORT CHAIN FROM x.py")
    p(f"{'=' * 80}")

    x_data = file_data.get('x.py')
    if x_data:
        p("\nDirect imports from x.py:")
        for imp in x_data['imports']:
            if imp['type'] == 'from':
                asname = f" as {imp['asname']}" if imp.get('asname') else ""
                p(f"  from {imp['module']} import {imp['name']}{asname} (line {imp['line']})")
            else:
                p(f"  import {imp['module']} (line {imp['line']})")

    # Summary of files with most unused
    p(f"\n{'=' * 80}")
    p("TOP FILES BY UNUSED FUNCTION COUNT")
    p(f"{'=' * 80}")
    ranked = sorted(results.items(), key=lambda x: x[1]['unused_count'], reverse=True)
    for rel, r in ranked[:30]:
        p(f"  {r['unused_count']:3d} unused / {r['total_defs']:3d} total  -  {rel}")

    out.close()
    print("DONE - output in tools/erase_output.txt")


if __name__ == '__main__':
    main()
