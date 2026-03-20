#!/usr/bin/env python3
"""
trim_git_history.py

Mantém apenas os últimos N dias "ativos" (dias com commits) do histórico git local
e opcionalmente empurra o novo histórico para o remoto (force push).

Uso seguro: primeiro rode com `--dry-run` para ver o que será feito.

Exemplo:
  py tools\trim_git_history.py --repo D:\\PjePlus --keep-days-active 3 --apply

Aviso: operação destrutiva localmente (substitui `.git`). Se usar `--push` fará
`git push --force` no ramo especificado — coordene com colaboradores.
"""
import argparse
import subprocess
import shutil
import os
import sys
import tempfile
from datetime import datetime


def run(cmd, check=True, capture=False):
    print(f"> {cmd}")
    return subprocess.run(cmd, shell=True, check=check, capture_output=capture, text=True)


def get_last_n_active_dates(repo, n, branch=None):
    branch_arg = f"{branch}" if branch else "--all"
    cmd = f'git -C "{repo}" log {branch_arg} --pretty=format:%ci --date=iso'
    p = run(cmd, capture=True)
    lines = [l.strip() for l in p.stdout.splitlines() if l.strip()]
    dates = []
    seen = set()
    for l in lines:
        # l like: 2026-03-19 16:25:10 -0300
        day = l.split()[0]
        if day not in seen:
            seen.add(day)
            dates.append(day)
        if len(dates) >= n:
            break
    return dates


def archive_git(repo, dest):
    base = os.path.abspath(repo)
    gitdir = os.path.join(base, '.git')
    if not os.path.exists(gitdir):
        raise RuntimeError('.git not found')
    shutil.make_archive(dest, 'zip', root_dir=gitdir)
    return dest + '.zip'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--repo', default='.', help='caminho do repositório')
    ap.add_argument('--keep-days-active', type=int, default=3, help='quantos dias ativos manter')
    ap.add_argument('--branch', default='main', help='branch alvo (para push)')
    ap.add_argument('--apply', action='store_true', help='realiza as alterações (sem este flag é dry-run)')
    ap.add_argument('--push', action='store_true', help='aplica `git push --force` no remoto após substituir histórico')
    ap.add_argument('--backup-prefix', default='git_backup', help='prefixo para arquivo de backup .zip')
    args = ap.parse_args()

    repo = os.path.abspath(args.repo)
    if not os.path.isdir(repo):
        print('Repo não encontrado:', repo)
        sys.exit(1)

    print('Calculando datas ativas...')
    dates = get_last_n_active_dates(repo, args.keep_days_active, args.branch)
    if not dates:
        print('Nenhum commit encontrado.')
        sys.exit(1)
    cutoff_date = min(dates)
    print('Últimas datas ativas (mais recentes primeiro):', dates)
    print('Data de corte (inclusive):', cutoff_date)

    print('\nDry-run: comando de clone raso que seria executado:')
    abs_repo = os.path.abspath(repo)
    file_url = 'file:///' + abs_repo.replace('\\', '/')
    shallow_clone = repo + '_shallow_tmp'
    print(f'git clone --shallow-since={cutoff_date} --branch {args.branch} --single-branch "{file_url}" "{shallow_clone}"')

    if not args.apply:
        print('\nExecução em modo dry-run. Reexecute com --apply para aplicar as mudanças.')
        return

    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_name = f"{args.backup_prefix}_{ts}"
    print('\nFazendo backup do .git em zip...')
    zip_path = archive_git(repo, backup_name)
    print('Backup criado em:', zip_path)

    print('\nCriando clone raso...')
    if os.path.exists(shallow_clone):
        print('Removendo clone temporário anterior...')
        shutil.rmtree(shallow_clone)
    run(f'git clone --shallow-since={cutoff_date} --branch {args.branch} --single-branch "{file_url}" "{shallow_clone}"')

    # swap .git
    old_git = os.path.join(repo, '.git_old_' + ts)
    print('Movendo .git para', old_git)
    shutil.move(os.path.join(repo, '.git'), old_git)

    print('Substituindo .git pelo clone raso')
    shutil.move(os.path.join(shallow_clone, '.git'), os.path.join(repo, '.git'))
    print('Removendo clone temporário...')
    shutil.rmtree(shallow_clone)

    print('Executando git gc...')
    run(f'git -C "{repo}" gc --aggressive --prune=now')

    if args.push:
        print('Fazendo push forçado para remoto (ATENÇÃO: sobrescreve o histórico remoto)')
        run(f'git -C "{repo}" push --force origin {args.branch}')

    print('\nConcluído. Backup em', zip_path)


if __name__ == '__main__':
    main()
