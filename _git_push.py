import subprocess, sys

commit_msg = "chore: fixes – destinatarios selection, unify prazo utils, update f.py and tests"

commands = [
    ["git", "add", "-A"],
    ["git", "status", "--porcelain"],
    ["git", "commit", "-m", commit_msg],
    ["git", "rev-parse", "--abbrev-ref", "HEAD"],
    ["git", "push", "origin", "main"],
]

try:
    # git add
    print('> git add -A')
    subprocess.check_call(commands[0])

    # show status
    print('> git status --porcelain')
    subprocess.check_call(commands[1])

    # commit (may fail if no changes)
    try:
        print('> git commit -m "MESSAGE"')
        subprocess.check_call(commands[2])
    except subprocess.CalledProcessError as e:
        print('No commit created (maybe no changes):', e)

    # current branch
    branch = subprocess.check_output(commands[3], text=True).strip()
    print('Current branch:', branch)

    # push
    print(f'> git push origin {branch}')
    subprocess.check_call(["git", "push", "origin", branch])

    print('\nPUSH_OK')
    sys.exit(0)
except Exception as e:
    print('ERROR during git operations:', e)
    sys.exit(1)
