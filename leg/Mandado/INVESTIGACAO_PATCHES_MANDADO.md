# Investigação e Patches — Fluxo `Mandado` (Argos / Outros)

## Objetivo
Diagnosticar e reduzir a latência observada entre o momento em que o fluxo
`Argos`/`Outros` é reconhecido (após abrir o detalhe do processo) e o início
real das ações automatizadas (cliques, extrações, aplicação de regras).

## Escopo
Arquivos/trechos chave analisados:
- `x.py` → orquestra execução (invoca `Mandado/processamento_api.py`).
- `Mandado/processamento_api.py::processar_mandado_detalhe` → abre detalhe,
  espera timeline e chama `_selecionar_doc_via_timeline`.
- `Mandado/_selecionar_doc_via_timeline` (mesmo arquivo) → `safe_click_no_scroll` +
  `aguardar_renderizacao_nativa` → identifica `argos` / `outros`.
- `Mandado/processamento_argos.py::processar_argos` → sequência de etapas,
  registra alguns timings (ETAPA4) mas ainda depende de sleeps/esperas.
- `Fix/documents/search.py::buscar_documento_argos` → realiza clicks, sleeps
  e extracao (`time.sleep(1)` + `extrair_direto`) — já tem logs de timing.
- `Fix/extracao_indexacao.py` → troca de abas, `time.sleep(1)`, reindexação.
- `Fix/utils_observer.py::aguardar_renderizacao_nativa` → função de polling usada
  em vários pontos; preferível a sleeps quando seletor confiável.

## Achados rápidos
- Vários `time.sleep(...)` usados como guard-rails (p.ex. 1s, 1.5s), aumentando
  latência acumulada por processo e por documento testado.
- `buscar_documento_argos` faz `safe_click_no_scroll` seguido de `time.sleep(1)`
  antes de extrair; substituível por espera dirigida (observer) para reduzir tempo.
- `indexar_e_processar_lista` faz sleeps antes/depois de trocar abas e abrir
  detalhe; trocas carregam verificações redundantes que podem ser tornadas
  event-driven com `aguardar_renderizacao_nativa`.
- Já existem logs de timing em `processar_argos` (ETAPA4), mas faltam logs no
  ponto de entrada (`processar_mandado_detalhe`) e antes/depois de clicks na
  timeline — precisamos dessas medições para priorizar otimizações.

## Patches propostos (resumo)
1. Instrumentação mínima (fase 1):
   - Arquivo: `Mandado/processamento_api.py`
   - Inserir logs com timestamps e durações em pontos-chave:
     - Antes de `driver.get(detalhe_url)`
     - Após `wait_for_page_load` / `esperar_elemento('li.tl-item-container')`
     - Antes e depois de `_selecionar_doc_via_timeline`
     - Antes de chamar `processar_argos` / `fluxo_mandados_outros`
   - Objetivo: medir latência por etapa sem alterar comportamento.

2. Substituir sleeps por esperas dirigidas (fase 2):
   - Arquivos: `Fix/documents/search.py`, `Fix/extracao_indexacao.py`
   - Trocar `time.sleep(1)` (e maiores) por `aguardar_renderizacao_nativa(...)`
     ou `wait_for_page_load(driver, timeout=...)` quando um seletor confiável
     existir. Preferir timeout curtos (2–4s) e retry leve em vez de sleeps
     fixos.

3. Refinamento da extração (fase 2b):
   - Arquivo: `Fix/documents/search.py::buscar_documento_argos`
   - Remover sleep pós-click e usar `aguardar_renderizacao_nativa` +
     `extrair_direto(driver, debug=True)` imediatamente; adicionar log de
     tempo entre click→extrair.

4. Reduzir overhead de troca de abas (fase 3):
   - Arquivo: `Fix/extracao_indexacao.py::trocar_para_nova_aba` e `_indexar_processar_item`
   - Diminuir sleeps e confiar nas verificações de `verificar_carregamento_detalhe`
     e `aguardar_renderizacao_nativa` para decidir reload/refresh.

5. Testes e rollback
   - Cada alteração deve ser pequena, com commit separado e possibilidade de
     rollback rápido.
   - Adicionar um teste de sanidade manual: executar `py x.py` → Mandado isolado
     e analisar logs `TIMING` no `logs_execucao/x_*.log`.

## Plano de implementação (tarefas)

### Task 1: Instrumentação mínima (XS)
- Descrição: Adicionar logs de tempo em `processar_mandado_detalhe` e
  pontos de clique na timeline.
- Acceptance criteria:
  - Logs contendo chaves `[MANDADOS_TIMING]` com timestamps/durações aparecem
    em `logs_execucao/x_*.log` após execução de Mandado isolado.
  - Nenhuma alteração no fluxo funcional.
- Arquivos: `Mandado/processamento_api.py`
- Escopo: 1-2 arquivos

### Task 2: Remover sleep pós-click em busca Argos (S)
- Descrição: Substituir `time.sleep(1)` por `aguardar_renderizacao_nativa` no
  trecho após `safe_click_no_scroll` em `buscar_documento_argos`.
- Acceptance criteria:
  - Redução média observada no log `[ARGOS][TIMING][CLIQUE]` por documento
    (comparar baseline antes/ depois).
  - Não introduzir falhas de sincronização (testar em ~10 processos).
- Arquivos: `Fix/documents/search.py`
- Escopo: 1-2 arquivos

### Task 3: Otimizar troca de abas e reindexação (M)
- Descrição: Reduzir sleeps e usar `aguardar_renderizacao_nativa`/`verificar_carregamento_detalhe`.
- Acceptance criteria:
  - Tempo entre abrir detalhe e estar pronto para callback reduzido.
  - Fluxo não quebra em cenários normais.
- Arquivos: `Fix/extracao_indexacao.py`
- Escopo: 3-5 arquivos

### Checkpoint 1: Após Tasks 1–2
- Verificar logs (`TIMING`) e validar redução estatística de latência.
- Garantir que `py x.py` (Mandado isolado) conclui sem regressões.

### Task 4: Ajustes finos em `processar_argos` (M)
- Descrição: Completar instrumentação interna (já há ETAPA4), ajustar timeouts
  locais e reduzir checks redundantes.
- Acceptance criteria: menor latência total por processo e regras aplicadas sem erro.

### Checkpoint 2: Teste em lote
- Executar `py x.py` com Mandado isolado para ~50 processos (ou subset realista).
- Validar tempos médios e percentil 95.

## Comandos de verificação (rápidos)
Fazer Mandado isolado e coletar logs:

```bash
py x.py   # escolher VT/PC e opção B (Mandado isolado)
# após execução, inspecionar logs:
findstr /I "MANDADOS_TIMING ARGOS TIMING" logs_execucao\x_*  # Windows
```

## Riscos e mitigação
- Risco: Substituir sleeps por waits sem seletor confiável pode causar
  timeouts ou flappers.  Mitigação: aplicar mudanças em etapas, manter
  fallback para sleep breve se observer falhar.
- Risco: alterações de sincronização podem expor condições de corrida.  Mitigação:
  testes em ambiente controlado e commits atômicos com rollback.

## Próximos passos sugeridos
1. Aprovar instrumentação (Task 1).  Eu aplico o patch e executo `py x.py` para
   coletar baseline de tempos.
2. Aplicar Task 2 (p.ex. em `Fix/documents/search.py`) e re-executar para medir
   ganho.  Se estável, aplicar Task 3 e 4.

---
Documento gerado automaticamente para guiar investigação e patches no fluxo
`Mandado`. Se aprovar, implemento Task 1 agora e rodo `py x.py` para coletar
logs de timing.
