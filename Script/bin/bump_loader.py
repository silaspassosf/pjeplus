#!/usr/bin/env python3
"""
Bump loader script (Python)
Usage: python Script/bin/bump_loader.py [--file Script/hcalc.user.js] [--dry-run]

Behavior:
- increments @version patch (X.Y.Z -> X.Y.(Z+1))
- increments numeric `v=` query params in `.js?v=` by 1
- updates `t=` timestamps to current yyyyMMddHHmm
"""
import re
import argparse
from datetime import datetime
from pathlib import Path


def bump_version(content: str):
    def repl(m):
        prefix = m.group(1)
        major = int(m.group(2))
        minor = int(m.group(3))
        patch = int(m.group(4)) + 1
        return f"{prefix}{major}.{minor}.{patch}"
    new, n = re.subn(r'(@version\s+)(\d+)\.(\d+)\.(\d+)', repl, content)
    return new, n


def bump_v_params(content: str):
    def repl(m):
        prefix = m.group(1)
        v = int(m.group(2)) + 1
        return f"{prefix}{v}"
    new, n = re.subn(r'(\.js\?v=)(\d+)', repl, content)
    return new, n


def bump_t_timestamp(content: str, now: str):
    def repl(m):
        return m.group(1) + now
    new, n = re.subn(r'(\bt=)(\d{10,})', repl, content)
    return new, n


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--file', '-f', default=None, help='userscript file to bump (default: repo-root/Script/hcalc.user.js)')
    p.add_argument('--dry-run', action='store_true', default=True, help='do not write changes, only show diff summary')
    p.add_argument('--apply', action='store_true', help='write changes to file (overrides --dry-run)')
    args = p.parse_args()

    if args.file:
        path = Path(args.file)
    else:
        # Compute repository root relative to this script (Script/bin -> repo root)
        repo_root = Path(__file__).resolve().parent.parent.parent
        path = repo_root / 'Script' / 'hcalc.user.js'

    if not path.exists():
        print(f'File not found: {path}')
        return 2

    content = path.read_text(encoding='utf-8')

    new_content = content
    changed = False

    new_content, c1 = bump_version(new_content)
    new_content, c2 = bump_v_params(new_content)
    now = datetime.now().strftime('%Y%m%d%H%M')
    new_content, c3 = bump_t_timestamp(new_content, now)

    total_changes = c1 + c2 + c3

    print('Summary:')
    print(f' - @version bumps: {c1}')
    print(f' - ".js?v=" param increments: {c2}')
    print(f' - t= timestamp replacements: {c3} (new: {now})')

    if total_changes == 0:
        print('No changes detected.')
        return 0

    if args.apply:
        backup = path.with_suffix(path.suffix + '.bak')
        # If a previous backup exists, remove it to allow overwrite
        if backup.exists():
            backup.unlink()
        path.rename(backup)
        path.write_text(new_content, encoding='utf-8')
        print(f'Updated {path}. Backup saved to {backup}')
    else:
        print('\nDry run mode (no file written). To apply changes run with --apply')

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
