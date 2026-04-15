# Reorganização da pasta `Fix/` — Fase 1

## Resumo

Esta migração reorganizou a pasta `Fix/` para reduzir complexidade e facilitar manutenção, seguindo a **Opção 1 — Minimal (híbrido domínio+tipo)** do plano em `docs/ideas/reorganizar-fix.md`.

### Princípios aplicados

1. **Implementação move-se para pacotes** — código real vai para `Fix/<pacote>/<modulo>.py`
2. **Arquivos originais viram stubs** — emitem `DeprecationWarning` e re-exportam do novo local
3. **Compatibilidade total** — todos os imports legados continuam funcionando
4. **Zero break** — nenhum consumidor externo precisa ser alterado

## Mudanças realizadas

### 1. Pacote `Fix/progress/` — Progresso unificado

| Antes (root) | Depois (pacote) |
|---|---|
| `Fix/monitoramento_progresso_unificado.py` (566 lines) | `Fix/progress/monitoramento.py` |
| `Fix/progress_models.py` (84 lines) | `Fix/progress/models.py` |
| `Fix/progress.py` (shim) | → re-exporta de `Fix.progress` |
| `Fix/progresso_unificado.py` (shim 7 lines) | → re-exporta de `Fix.progress.monitoramento` |

**Stubs criados:**
- `Fix/monitoramento_progresso_unificado.py` → stub → `Fix.progress.monitoramento`
- `Fix/progress_models.py` → stub → `Fix.progress.models`
- `Fix/progress.py` → stub → `Fix.progress`
- `Fix/progresso_unificado.py` → stub → `Fix.progress.monitoramento`

**Novo uso recomendado:**
```python
from Fix.progress import ProgressoUnificado, carregar_progresso_unificado, StatusModulo, Checkpoint
# ou
from Fix.progress.monitoramento import carregar_progresso_unificado
from Fix.progress.models import StatusModulo, NivelLog
```

### 2. Pacote `Fix/extraction/` — Indexação e processamento

| Antes (root) | Depois (pacote) |
|---|---|
| `Fix/extracao_indexacao.py` (609 lines) | `Fix/extraction/indexacao.py` |

**Stubs criados:**
- `Fix/extracao_indexacao.py` → stub → `Fix.extraction.indexacao`
- `Fix/extracao_indexacao_fluxo.py` → stub → `Fix.extraction.indexacao`

**Novo uso recomendado:**
```python
from Fix.extraction import indexar_processos, filtrofases, indexar_e_processar_lista
# ou
from Fix.extraction.indexacao import indexar_processos
```

### 3. Stubs pré-existentes mantidos

Estes já eram stubs e foram atualizados para apontar para os novos pacotes:

| Arquivo | Aponta para |
|---|---|
| `Fix/extracao_documento.py` | `Fix.extracao_conteudo` |
| `Fix/extracao_processo.py` | `Fix.extracao_conteudo` |
| `Fix/extracao_analise.py` | `Fix.extracao` |

### 4. Legacy fix

- `Fix/legacy/extracao_indexacao_fluxo.py` — imports relativos atualizados para absolutos (`Fix.extraction.*`, `Fix.progress.*`)
- `Fix/legacy/extracao_processo.py` — import de `.utils` → `Fix.utils`

## Estrutura resultante

```
Fix/
├── progress/                    # NOVO — sistema de progresso
│   ├── __init__.py              # API pública consolidada
│   ├── monitoramento.py         # implementação principal (566 lines)
│   └── models.py                # StatusModulo, NivelLog, Checkpoint, etc.
├── extraction/                  # NOVO — indexação e processamento
│   ├── __init__.py              # API pública consolidada
│   └── indexacao.py             # filtrofases, indexar_processos, etc. (609 lines)
├── selenium_base/               # existente (9 files)
├── documents/                   # existente (3 files)
├── drivers/                     # existente (2 files)
├── navigation/                  # existente (3 files)
├── session/                     # existente (2 files)
├── forms/                       # existente (2 files)
├── gigs/                        # existente (2 files)
├── legacy/                      # existente (5 files)
├── scripts/                     # existente (1 file)
│
├── monitoramento_progresso_unificado.py  # STUB → progress.monitoramento
├── progress.py                           # STUB → progress
├── progress_models.py                    # STUB → progress.models
├── progresso_unificado.py                # STUB → progress.monitoramento
├── extracao_indexacao.py                 # STUB → extraction.indexacao
├── extracao_indexacao_fluxo.py           # STUB → extraction.indexacao
├── extracao_documento.py                 # STUB → extracao_conteudo
├── extracao_processo.py                  # STUB → extracao_conteudo
├── extracao_analise.py                   # STUB → extracao
├── variaveis.py                          # re-export (resolvers, helpers, client, painel)
│
└── [demais módulos root-level]
```

## Validação

### Script de verificação
```bash
# Sintaxe
py -m py_compile Fix/**/*.py

# Imports (88 módulos verificados)
py tools/check_imports.py
```

**Resultado:** 88 OK, 0 FAIL, 1 SKIP (`Fix.native_host` — depende de ambiente específico)

## DeprecationWarnings

Os stubs emitem `DeprecationWarning` quando importados. Para suprimi-los em produção:
```python
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
```

## Rollback

Todos os arquivos originais foram convertidos em stubs que re-exportam dos novos locais. Para reverter:
1. Os stubs garantem compatibilidade total
2. Os arquivos `Fix/legacy/` contêm versões antigas de backup
3. Nenhum dado foi perdido

## Próximas fases (não executadas ainda)

### Fase 2 — Split de arquivos grandes (>600 lines)
- `Fix/selenium_base/element_interaction.py` (625 lines) → dividir por responsabilidade
- `Fix/documents/search.py` (605 lines) → dividir por responsabilidade

### Fase 3 — Consolidação de módulos pequenos
- 45 arquivos < 300 linhas são candidatos a consolidação por domínio
- Meta: reduzir de ~84 para ~12-18 arquivos/pacotes

### Fase 4 — Limpeza final
- Remover `Fix/legacy/` após período de confiança
- Remover stubs deprecated
