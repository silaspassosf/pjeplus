#!/bin/sh
# Install git hook for Unix-like systems
set -e
cp .githooks/pre-commit .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
echo "Installed pre-commit hook to .git/hooks/pre-commit"
