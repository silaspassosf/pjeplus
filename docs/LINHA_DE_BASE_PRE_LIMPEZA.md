# Linha de base pré-limpeza — referência de restauração

**Commit de referência:** `d1204f1`
**Data:** 2026-10-22 16:01:57 -0300
**Mensagem:** `feat(hcalc): deteccao automatica de planilha .pjc no pje via API e estado inicial no overlay`

## Por que este commit

`d1204f1` é o **último commit antes de a limpeza começar**. O primeiro commit da
limpeza é `3e9b535` (F0+F1, 2026-10-23 01:40). Tudo entre eles e `HEAD` é
trabalho de limpeza (`z-ai/glm-5.3-flash` até a F6, `deepseek-v4.1-flash` depois).

**Regra:** em qualquer regressão de comportamento, a referência é `d1204f1` —
não o commit imediatamente anterior. É o estado que rodava em produção.

## Como comparar

```bash
# ver o arquivo como era antes da limpeza
git show d1204f1:Fix/core.py

# diferença completa de um arquivo
git diff d1204f1 HEAD -- Mandado/entrada_api.py

# rodar a versão antiga isolada (worktree separado, sem tocar no working tree)
git worktree add scratch/wt_base d1204f1
```

Para executar a versão antiga é preciso instalar o shim Playwright **antes** de
importar qualquer `Fix/*` (o core antigo referencia `webdriver` no topo):

```python
import sys; sys.path.insert(0, "Play")
from pjeplay.compat import instalar
instalar()
```

O worktree precisa de `Fix/geckodriver.exe` existente para desviar do `NameError`
em `Fix/core.py` (o código antigo assume o binário presente).

## O que foi verificado contra esta base

| Item | Método | Resultado |
|---|---|---|
| `fechar_intimacao` | diff AST contra `d1204f1` | **0 alterações** |
| `processar_sisbajud` | execução com 10 certidões reais | **idêntico 10/10** |
| `aguardar_transicao_minutar` | diff AST | **0 alterações** |
| `espera.elemento`/`elementos` | execução, 6 cenários, driver instrumentado | **idêntico 6/6** |
| Funções públicas de espera (107) | resolução por re-export real | **106 existem** (só `credencial` saiu, órfã) |
| `Fix/espera.py` | diff de conteúdo | só **+72** (telemetria); nada removido |
| `Fix/core.py` — contrato | 59 nomes públicos | 55 existem; 4 órfãos, **zero quebrados** |
| `Fix/utils.py` | 54 defs | **0 removidas** |

**Conclusão:** as funções de espera e de fluxo não foram apagadas nem alteradas.
O que mudou foi **tempo de execução** — o fluxo ficou mais rápido e passou a
vencer a renderização do Angular (ver `docs/PROJETO_LIMPEZA_PJEPLUS.md`, seção
"Corrida de renderização").

## Evidência de log

Execução de mandado em **19/10** (`logs_execucao/x_PC_Visible_20261019_000138.log`),
antes de qualquer limpeza:

```
[INTIMACAO] [3] Aguardando modal abrir...     00:02:54
[INTIMACAO] [4] Buscando linhas com prazo 30  00:02:55   <- ~1s de folga
[INTIMACAO] [4] Total de linhas encontradas: 10
[INTIMACAO] [4]  Linha 1 selecionada (prazo 30, nao fechado)
```

Mesmo trecho em **23/10** (`x_PC_Visible_20261023_151647.log`):

```
[INTIMACAO] [3] Aguardando modal abrir...     15:17:20
[INTIMACAO] [4] Buscando linhas com prazo 30  15:17:20   <- 0s de folga
[INTIMACAO] [4] Total de linhas encontradas: 4
[INTIMACAO] [4]  Nenhuma linha prazo 30 nao fechada encontrada
```

CLS — a transição para minutar **nunca falhou**. Tempo até detectar, por execução:

```
20/10 16:26   4.724s
21/10 16:07   4.114s
22/10 14:13   4.468s
22/10 21:28   4.028s
23/10 00:23   3.789s
23/10 15:16   5.155s   <- depois da limpeza, e funcionou
```

O `[CLS][TIMING][TRANSICAO_MINUTAR] 5.155s` do log de 23/10 prova que o fluxo
seguiu normalmente (o 1º CLS do dia terminou com `status: sucesso` em 11,060s).
O 2º CLS foi **interrompido pelo usuário** às 15:18:36
(`interrompido pelo usuario — finalizando de forma cooperativa`), enquanto
ainda estava no passo 5 — não houve falha.

## Quando usar esta base

- Suspeita de regressão de comportamento em qualquer fluxo → comparar com `d1204f1`.
- Regressão confirmada → restaurar **o trecho exato** desta base, não reescrever.
- Regressão **não** confirmada (comportamento idêntico) → o defeito é latente ou
  de ambiente; investigar timing/renderização, não a lógica.
