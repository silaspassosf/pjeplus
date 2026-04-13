# Plano de Implementação: Otimizações PJePlus

## Overview

Este plano traduz o relatório de otimizações (`otimizacoes_sugeridas.md`) em tarefas pequenas, verificáveis e ordenadas. O foco é corrigir falhas de base primeiro, depois melhorar confiabilidade headless e por fim aplicar polimentos de arquitetura.

## Architecture Decisions

- Priorizar correções de infraestrutura de baixo risco antes de mudanças de comportamento em `atos/`.
- Trabalhar em etapas: correções de base, comportamentos de exceção e then performance/organização de JS.
- Manter o sistema funcional entre tarefas; cada tarefa deixa o repositório compilando e com importações válidas.

## Task List

### Phase 1: Foundation

## Task 1: Corrigir loader JS em `Fix/scripts/__init__.py`

**Description:** Corrigir o bug de caminho que quebra `carregar_js()` quando `pasta` é string.

**Acceptance criteria:**
- [ ] `carregar_js(nome, pasta)` funciona quando `pasta` é um `Path` e quando é `str`.
- [ ] `py -m py_compile Fix/scripts/__init__.py` passa.

**Verification:**
- [ ] Execute `py -m py_compile Fix/scripts/__init__.py`.
- [ ] Testar manualmente com `python -c "from Fix.scripts import carregar_js; print(carregar_js('__init__.py', 'Fix/scripts')[:20])"`.

**Dependencies:** None

**Files likely touched:**
- `Fix/scripts/__init__.py`

**Estimated scope:** XS

## Task 2: Corrigir `Fix/drivers/lifecycle.py` logger e imports

**Description:** Mover import de logger para o topo e usar `get_module_logger()` para manter o padrão de logs do projeto.

**Acceptance criteria:**
- [ ] `Fix/drivers/lifecycle.py` importa `get_module_logger` no topo.
- [ ] Não há import solto depois de `yield`.
- [ ] `py -m py_compile Fix/drivers/lifecycle.py` passa.

**Verification:**
- [ ] Execute `py -m py_compile Fix/drivers/lifecycle.py`.

**Dependencies:** Task 1

**Files likely touched:**
- `Fix/drivers/lifecycle.py`

**Estimated scope:** XS

## Task 3: Mover import de `driver_session` para o topo em `x.py`

**Description:** Ajustar `x.py` para carregar `driver_session` juntamente com outros imports, eliminando import lazy dentro de função.

**Acceptance criteria:**
- [ ] `x.py` importa `driver_session` no topo.
- [ ] `x.py` compila sem erro.

**Verification:**
- [ ] Execute `py -m py_compile x.py`.

**Dependencies:** Task 2

**Files likely touched:**
- `x.py`

**Estimated scope:** XS

## Checkpoint: Foundation

- [x] `py -m py_compile Fix/scripts/__init__.py Fix/drivers/lifecycle.py x.py`
- [x] Correções de infraestrutura implementadas
- [x] Revisão rápida antes de avançar para regras de exceção

### Phase 2: Core Behavior

## Task 4: Tornar `ElementoNaoEncontradoError.contexto` opcional

**Description:** Ajustar `Fix/exceptions.py` para aceitar contexto vazio por padrão, facilitando adoção em todo o código.

**Acceptance criteria:**
- [x] `ElementoNaoEncontradoError.__init__` define `contexto: str = ""`.
- [x] `py -m py_compile Fix/exceptions.py` passa.

**Verification:**
- [x] Execute `py -m py_compile Fix/exceptions.py`.

**Dependencies:** None

**Files likely touched:**
- `Fix/exceptions.py`

**Estimated scope:** XS

## Task 5: Substituir `return False` silencioso por exceções em `atos/`

**Description:** Alterar funções em `atos/judicial_bloqueios.py`, `atos/comunicacao_preenchimento.py`, `atos/comunicacao_finalizacao.py`, `atos/core.py` para lançar exceções tipadas em vez de retornar `False` após `except`.

**Status:** concluído — principais caminhos de exceção em `atos/judicial_bloqueios.py` e fluxos auxiliares de preenchimento já foram ajustados e compilam.

**Acceptance criteria:**
- [x] `return False` não é usado em blocos de exceção dessas funções críticas.
- [x] As exceções lançadas são `ElementoNaoEncontradoError` ou `NavegacaoError` conforme o caso.
- [x] O código compila.

**Verification:**
- [x] Execute `py -m py_compile atos/judicial_bloqueios.py atos/comunicacao_preenchimento.py atos/comunicacao_finalizacao.py atos/core.py`.
- [ ] Verificar manualmente um caso de exceção para garantir que a mensagem é descritiva.

**Dependencies:** Task 4

**Files likely touched:**
- `atos/judicial_bloqueios.py`
- `atos/comunicacao_preenchimento.py`
- `atos/comunicacao_finalizacao.py`
- `atos/core.py`

**Estimated scope:** M

## Task 6: Substituir `time.sleep()` por espera reativa em `atos/comunicacao_preenchimento.py`

**Status:** em progresso — a maioria dos sleeps cegos foi removida e substituída por `aguardar_renderizacao_nativa()`, mas ainda restam backoffs justificados em `preencher_input_js()` e em polling de CKEditor.

**Description:** Remover `time.sleep()` e usar `aguardar_renderizacao_nativa()` ou `wait_for_clickable()` nos pontos identificados.

**Acceptance criteria:**
- [ ] Todos os `time.sleep()` em `atos/comunicacao_preenchimento.py` são removidos ou isolados com comentário justificando a exceção.
- [ ] Async waits do projeto são usados quando necessário.
- [ ] O arquivo compila.

**Verification:**
- [ ] Execute `py -m py_compile atos/comunicacao_preenchimento.py`.
- [ ] Confirmar pelo menos um fluxo manual em ambiente de teste que o campo preenche sem falhas temporais.

**Dependencies:** Task 5

**Files likely touched:**
- `atos/comunicacao_preenchimento.py`

**Estimated scope:** M

## Checkpoint: Core Features

- [ ] `py -m py_compile Fix/exceptions.py atos/judicial_bloqueios.py atos/comunicacao_preenchimento.py atos/comunicacao_finalizacao.py atos/core.py`
- [ ] Fluxos de exceção base e esperas reativas implementados
- [ ] Revisão de comportamento antes de polir JS e arquitetura

### Phase 3: Polish

## Task 7: Extrair scripts JS inline de `SISB/` e `PEC/`

**Description:** Mover JS inline de `driver.execute_script("""...")` para arquivos `SISB/scripts/*.js` e `PEC/scripts/*.js`, usando `Fix.scripts.carregar_js()`.

**Acceptance criteria:**
- [ ] Não há `execute_script("""` em `SISB/` ou `PEC/` para os casos ativos analisados.
- [ ] Cada script é carregado por `carregar_js()` com `Path(...).read_text()` funcionando.
- [ ] O JavaScript continua funcionando sem mudanças de lógica.

**Verification:**
- [ ] Execute `py -m py_compile` nos módulos ajustados.
- [ ] Confirmação manual de um fluxo SISB ou PEC com JS carregado.

**Dependencies:** Tasks 1, 6

**Files likely touched:**
- `SISB/Core/utils_web.py`
- `SISB/processamento_campos_reus.py`
- `SISB/processamento/ordens_acao.py`
- `PEC/anexos/anexos_juntador_metodos.py`
- `PEC/core_progresso.py`
- `Fix/scripts/__init__.py`

**Estimated scope:** L

## Task 8: Converter wrappers de `Fix/core.py` para re-exportações graduais

**Description:** Reduzir wrappers de uma linha no `Fix/core.py` movendo exportações diretas para `Fix/__init__.py` e mantendo compatibilidade.

**Acceptance criteria:**
- [ ] Mínimo uma família de funções (`wait`, `wait_for_visible`, `wait_for_clickable`) é exportada diretamente no `Fix/__init__.py`.
- [ ] `Fix/core.py` continua compatível com importações existentes.
- [ ] O repositório compila.

**Verification:**
- [ ] Execute `py -m py_compile Fix/core.py Fix/__init__.py`.
- [ ] Testar `python -c "from Fix import wait; print(wait)"`.

**Dependencies:** None

**Files likely touched:**
- `Fix/__init__.py`
- `Fix/core.py`

**Estimated scope:** M

## Task 9: Criar workflow de sanity em `.github/workflows/sanity.yml`

**Description:** Adicionar um job CI leve que valida compilação de arquivos críticos e ativa `PJEPLUS_TIME=1`.

**Acceptance criteria:**
- [ ] Existe `.github/workflows/sanity.yml` com compilação de arquivos críticos.
- [ ] O workflow está sintaticamente válido.

**Verification:**
- [ ] Arquivo presente e bem formado.
- [ ] Se possível, executar `act` ou revisão manual do YAML.

**Dependencies:** None

**Files likely touched:**
- `.github/workflows/sanity.yml`

**Estimated scope:** S

## Checkpoint: Complete

- [ ] Todas as tarefas do plano implementadas ou marcadas como “adiar” com justificativa.
- [ ] Compilação de arquivos afetados passa.
- [ ] Revisão de qualidade concluída.
- [ ] Pronto para merge.

## Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| `atos/` exceptions refactor quebrar fluxo | Alto | Fazer alteração em blocos pequenos, compilar cada módulo, testar caso de falha manualmente |
| `time.sleep` substituição deixar fluxo instável | Médio | Usar espera reativa combinada com timeout claro e logs mínimos |
| JS extraction alterar comportamento do script | Médio | Extrair apenas código testado, manter a mesma entrada/saída de `arguments[0]` |
| workflow CI ausente | Baixo | Criar sanity workflow isolado; não depender de toda infraestrutura de testes |

## Open Questions

- Deve a tarefa 5 `atos/` ser limitada inicialmente a um único arquivo para reduzir risco, ou aplicada em lote a todos os arquivos identificados?
- Há testes existentes de integração Selenium para `SISB/` e `PEC/` que possam validar a extração JS sem rodar todo fluxo manualmente?
