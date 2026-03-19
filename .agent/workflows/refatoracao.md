---
description: Workflow para refatoração segura de módulos
---

# Workflow: Refatoração Segura

## Passo 1: Preparação
```bash
# Criar backup
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
Copy-Item -Path "." -Destination "../BACKUP_$timestamp" -Recurse -Exclude ".git"

# Criar branch
git checkout -b refactor/nome-do-modulo
```

## Passo 2: Análise
- Ler código em `ref/` (versão funcional)
- Identificar duplicações
- Mapear dependências

## Passo 3: Execução
- Aplicar mudanças incrementalmente
- Commit a cada funcionalidade completa
- Testar após cada commit

## Passo 4: Validação
```bash
# Testes
pytest tests/ -v

# Lint
pylint . --rcfile=.pylintrc

# Contar linhas (verificar redução)
Get-ChildItem -Recurse -Include *.py | Measure-Object -Line
```

## Passo 5: Merge
```bash
git checkout main
git merge refactor/nome-do-modulo
git push origin main
```
