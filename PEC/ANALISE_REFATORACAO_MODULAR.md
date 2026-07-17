# ANALISE E PROPOSTA DE REFATORACAO MODULAR - PEC

## Objetivo
Atualizar a proposta de refatoracao para a estrutura atual do PEC, mantendo apenas a subpasta anexos/ e deixando o restante na raiz. Limites de tamanho: alvo 300 linhas por arquivo, sem necessidade de dividir se ficar ate 500 linhas.

## Estrutura atual (raiz + anexos)
- Arquivos principais na raiz: processamento.py, processamento_base.py, processamento_fluxo.py, processamento_indexacao.py, processamento_buckets.py, processamento_listas.py, regras.py, matcher.py, helpers.py, executor.py
- Analises na raiz: sobrestamento.py (def_sob), prescricao.py (def_presc), ajuste_gigs.py (def_ajustegigs), sisbajud_driver.py
- Outros: core.py, carta.py
- Subpasta permitida: anexos/ (mantida)

## Limites e criterio de divisao
- Alvo: 300 linhas por arquivo
- Aceitavel: ate 500 linhas (nao precisa dividir)
- Dividir apenas se passar de 500 linhas ou se houver responsabilidades muito distintas

## Proposta revisada (sem subpastas extras)
### Orquestradores (mantem compatibilidade)
- processamento.py: permanece como orquestrador publico
- regras.py: permanece como shim de compatibilidade (reexports)

### Execucao e fluxo
- processamento_base.py: executar_acao, processar_processo_pec_individual, _lazy_import_pec
- processamento_fluxo.py: executar_fluxo_robusto, executar_fluxo_novo, _configurar_driver, _navegar_atividades, _aplicar_filtros, _organizar_e_executar_buckets
- processamento_indexacao.py: _indexar_todos_processos, _filtrar_por_observacao, _filtrar_por_progresso, _filtrar_por_acoes_validas, _agrupar_em_buckets, _executar_dry_run, indexar_e_criar_buckets_unico
- processamento_buckets.py: _processar_buckets, _processar_bucket_generico, _processar_bucket_demais, _processar_bucket_sisbajud, _imprimir_relatorio_final
- processamento_listas.py: criar_lista_sisbajud, executar_lista_sisbajud_por_abas, criar_lista_resto

### Regras e acoes
- matcher.py: _build_action_rules, get_cached_rules, get_action_rules, determinar_acoes_por_observacao, determinar_acao_por_observacao
- helpers.py: remover_acentos, normalizar_texto, gerar_regex_geral
- executor.py: chamar_funcao_com_assinatura_correta, executar_acao, executar_acao_pec

### Analises
- sobrestamento.py: def_sob
- prescricao.py: def_presc
- ajuste_gigs.py: def_ajustegigs
- sisbajud_driver.py: get_or_create_driver_sisbajud, fechar_driver_sisbajud_global

### Outros
- core.py: utilitarios core PEC
- carta.py: fluxo de carta
- anexos/: manter subpasta para juntadas e extracao

## Ajustes recomendados (sem mudar estrutura)
1. Verificar tamanhos atuais e dividir apenas se exceder 500 linhas.
2. Manter nomes atuais dos arquivos para evitar quebra de imports.
3. Atualizar apenas reexports em regras.py quando houver movimento interno.

## Observacoes
- Esta proposta respeita a estrutura atual e evita granularizacao excessiva.
- Se algum arquivo ultrapassar 500 linhas e nao der para dividir sem perder contexto, registrar excecao.
