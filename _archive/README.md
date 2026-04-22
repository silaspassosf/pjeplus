# _archive/

Arquivos Python removidos do repositorio via analise de call graph (scan_live_modules.py).

## Como reverter um arquivo

```powershell
# Restaurar um arquivo especifico
git restore <caminho/do/arquivo.py>

# Exemplo:
git restore Fix/extracao_indexacao.py
```

## Como reverter TUDO de uma sessao

Os arquivos estao fisicamente aqui em `_archive/YYYYMMDD_HHMMSS/`.
Para restaurar todos de uma sessao especifica:

```powershell
# Mover tudo de volta
Copy-Item -Recurse _archive\20260415_123456\* . -Force
```

Ou simplesmente reverter o commit de limpeza:

```powershell
git revert HEAD
```

## Estrutura

```
_archive/
  YYYYMMDD_HHMMSS/          <- sessao de arquivamento
    _manifest.json           <- lista completa com paths originais e motivos
    atos/
    Fix/
    ...
```

## Criterio de arquivamento

Arquivo arquivado = nao alcancavel transitivamente a partir de x.py (unico entry point do projeto).
Ferramenta: tools/scan_live_modules.py + tools/archive_dead.py
