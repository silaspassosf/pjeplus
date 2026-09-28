"""
erase_imports_analysis.py - Analyze imports that are never used.
Focuses on from X import Y where Y is never called/referenced.
"""
import ast
import os
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(r'd:\PjePlus')
OUTPUT_FILE = ROOT / 'tools' / 'erase_imports_output.txt'

EXCLUDED_DIRS = {
    'bianca', 'peticao', 'triagem',
    '__pycache__', '.git', '.git_old_20260319_171141',
    'aider-env', '_archive', '-++backups',
    '.aider.tags.cache.v4', '.claude', '.qwen', '.vscode',
    '.github', '.githooks', 'outros projetos', 'ORIGINAIS',
    'backup_pre_merge', 'ref', 'tools', 'scripts', 'AHK',
    'cache', 'cookies_sessoes', 'logs_execucao', 'docs',
}

ANALYSIS_DIRS = {'Fix', 'Prazo', 'PEC', 'Mandado', 'atos', 'core', 'SISB', 'busca', 'carta', 'api'}


def collect_py_files():
    files = []
    for root, dirs, fnames in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d.lower() not in {x.lower() for x in EXCLUDED_DIRS}]
        for f in fnames:
            if f.endswith('.py'):
                files.append(os.path.join(root, f))
    return files


def get_rel_path(filepath):
    try:
        return str(Path(filepath).relative_to(ROOT))
    except ValueError:
        return filepath


def analyze_file_imports(filepath):
    """Analyze a single file for unused imports."""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            source = f.read()
        tree = ast.parse(source, filename=filepath)
    except SyntaxError:
        return None

    # Collect all from X import Y statements
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = node.module or ''
            for alias in node.names:
                name = alias.asname or alias.name
                imports.append({
                    'module': module,
                    'original_name': alias.name,
                    'local_name': name,
                    'line': node.lineno,
                })

    if not imports:
        return None

    # Collect all names used in the file (excluding the import statements themselves)
    used_names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            continue
        if isinstance(node, ast.Import):
            continue
        if isinstance(node, ast.Name):
            used_names.add(node.id)
        elif isinstance(node, ast.Attribute):
            used_names.add(node.attr)
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                used_names.add(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                used_names.add(node.func.attr)

    # Check which imports are unused
    unused = []
    used = []
    for imp in imports:
        local = imp['local_name']
        # For re-export wrappers (like Fix/utils.py), imports used as re-exports are "used"
        # We detect this by checking if the file has __all__ or if it's an __init__.py
        if local in used_names or imp['original_name'] == '*':
            used.append(imp)
        else:
            unused.append(imp)

    return {
        'total_imports': len(imports),
        'used': used,
        'unused': unused,
    }


def main():
    out = open(OUTPUT_FILE, 'w', encoding='utf-8')
    def p(msg=""):
        out.write(msg + "\n")

    p("=" * 80)
    p("UNUSED IMPORTS ANALYSIS")
    p("=" * 80)

    all_files = collect_py_files()
    
    # Filter to scope
    scope_files = []
    for f in all_files:
        rel = get_rel_path(f)
        parts = rel.replace('\\', '/').split('/')
        if parts[0] in ANALYSIS_DIRS or rel == 'x.py' or rel in ('dom.py', 'p2.py', 'f.py', 'monitor.py', 'utilitarios_processamento.py'):
            scope_files.append(f)

    p(f"Files in scope: {len(scope_files)}")

    total_unused_imports = 0
    results = {}

    for f in sorted(scope_files):
        rel = get_rel_path(f)
        result = analyze_file_imports(f)
        if result and result['unused']:
            # Skip wrapper/re-export files (they import to re-export)
            # Check if file name suggests it's a wrapper
            basename = os.path.basename(f)
            if basename in ('__init__.py',):
                # __init__.py files often import to re-export - be cautious
                # Only flag if the unused import is from an external module
                pass

            if basename == 'utils.py' and 'Fix' in rel:
                # Fix/utils.py is explicitly a re-export wrapper - skip
                continue

            results[rel] = result
            total_unused_imports += len(result['unused'])

    # Print results
    for rel in sorted(results.keys()):
        r = results[rel]
        if not r['unused']:
            continue
        p(f"\n{'-' * 70}")
        p(f"FILE: {rel}")
        p(f"   Total imports: {r['total_imports']} | Used: {len(r['used'])} | UNUSED: {len(r['unused'])}")
        for u in r['unused']:
            p(f"   [UNUSED IMPORT] from {u['module']} import {u['original_name']} (line {u['line']})")

    p(f"\n{'=' * 80}")
    p(f"TOTAL UNUSED IMPORTS: {total_unused_imports}")
    p(f"{'=' * 80}")

    # Ranking
    p(f"\n{'=' * 80}")
    p("TOP FILES BY UNUSED IMPORT COUNT")
    p(f"{'=' * 80}")
    ranked = sorted(results.items(), key=lambda x: len(x[1]['unused']), reverse=True)
    for rel, r in ranked[:30]:
        p(f"  {len(r['unused']):3d} unused imports  -  {rel}")

    out.close()
    print("DONE - output in tools/erase_imports_output.txt")


if __name__ == '__main__':
    main()
