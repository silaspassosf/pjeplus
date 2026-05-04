---
description: "Use when analyzing xcode planning docs, expanding xcode/12-Compilacao, or generating granular simplification plans for Fix and SISB. Covers entrypoint anchoring, frozen heavy files, public-contract preservation, and concrete fatias with gate/dependencies."
applyTo: "xcode/**"
---

# Xcode: Granulares de Fix e SISB

Use esta instrucao quando a tarefa for analisar, planejar ou granularizar `Fix/` e `SISB/` dentro de `xcode/`.

## Regra geral

- Nao tratar `Fix` e `SISB` como modulos de negocio equivalentes a `Mandado`, `Prazo`, `PEC`, `Triagem` ou `Peticao`.
- Ancorar a analise no grafo real de execucao saindo de `x.py`, nao em contagem bruta de arquivos.
- Antes de propor merge, separar:
  - superficie publica a preservar
  - arquivos pesados congelados
  - facades e shims de compatibilidade
  - arquivos pequenos que hoje so dispersam o caminho real
- Cada plano granular deve trazer fatias concretas com este formato:
  - `Escopo`
  - `Resultado esperado`
  - `Gate`
  - `Depends on`
- Cada plano deve declarar explicitamente o que fica fora do escopo e por qual motivo.

## Regras para Fix

- Tratar `Fix` como infraestrutura compartilhada de todos os fluxos A-G.
- Comecar pelo caminho real ja estabilizado no plano:
  - `Fix/core.py` como runtime e facade de interacao
  - `Fix/log.py` e `Fix/progress.py` como contratos compartilhados
  - `Fix/scripts/__init__.py` como shim de compatibilidade critica
- Nao propor uma unica consolidacao cega por pastas; organizar por familias funcionais:
  - runtime/driver
  - selenium/wait/select/click
  - extracao
  - log/progresso/contratos
  - facades publicas
- Arquivos pesados acima de 600 linhas entram congelados na primeira rodada, salvo prova forte em contrario.
- O granular de `Fix` deve explicitar quais simbolos publicos precisam continuar importaveis por `x.py`, `f.py` e modulos de negocio.
- Se houver merge interno, exigir shim curto de compatibilidade antes de qualquer pruning agressivo.

## Regras para SISB

- Ancorar a analise no caminho real: `PEC/regras_pec.py` -> `SISB.core.processar_ordem_sisbajud`.
- Nao usar `SISB/s_orquestrador.py` como centro arquitetural se ele estiver funcionando apenas como casca residual ou compatibilidade.
- Separar o modulo em camadas antes de propor consolidacao:
  - runtime/entrada real
  - processamento/acoes
  - extracao e relatorios
  - series e suporte especializado
- `SISB/core.py` e `SISB/helpers.py` devem ser avaliados primeiro como unidades congeladas do caminho real; so quebrar isso com evidencia concreta.
- O granular de `SISB` deve deixar claro quais facades em `SISB/__init__.py` e `SISB/processamento/__init__.py` permanecem obrigatorias.
- Sempre registrar quando um arquivo foi podado antes e nao deve voltar ao centro estrutural sem prova de uso real.

## Evidencias obrigatorias a consultar

- `xcode/00-mapa-execucao-real-xpy.md`
- `xcode/03-plano-fases-incrementais.md`
- `xcode/04-matriz-nucleo-dependencias.md`
- `xcode/06-consolidacao-funcoes-e-pruning.md`
- `xcode/README.md`

## Sinais de boa analise

- A primeira fatia nao exige editar muitos consumidores em paralelo.
- O plano preserva imports publicos antes de mover implementacao.
- Os arquivos pequenos deixam de definir a arquitetura do modulo.
- O plano identifica explicitamente arquivos congelados, facades, shims e contratos.

## Sinais de analise fraca

- Comecar por contagem de pastas sem citar `x.py`.
- Tratar `s_orquestrador.py` como entrypoint principal do SISB sem provar alcance.
- Tentar fundir `Fix` inteiro sem separar runtime, contratos e facades.
- Propor arquivos finais abaixo de 400 linhas ou quebrar arquivos ja estabilizados acima de 600 sem justificativa.