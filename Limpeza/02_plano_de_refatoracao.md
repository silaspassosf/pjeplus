# Plano Estrutural de Refatoração em 10 Lotes (Fase B)
## Diretrizes, Arquitetura-Alvo e Matriz de Riscos

---

## 1. Fontes de Verdade e Princípios Norteadores

A refatoração seguiu estritamente a seguinte hierarquia de fontes de verdade:

1. **Código atualmente executado na branch de trabalho (`refactor/pw-nativo`).**
2. **`idx.md`**, consultado obrigatoriamente antes de qualquer modificação para respeito às convenções arquiteturais.
3. **Módulos canônicos de runtime:**
   - Playwright nativo: `Fix/espera.py`, `Fix/browser_suporte.py`, `play/pjeplay/nativo.py`.
   - APIs REST: `Fix/variaveis.py` (`PjeApiClient`).
   - Logging: `Fix/diagnostico_runtime.py`.
4. **Referência histórica:** A tag `pre-refac` e a branch `main` serviram exclusivamente para consulta de lógica original validada (`git show main:ARQUIVO`), sendo terminantemente proibida a reintrodução de Selenium.

---

## 2. Arquitetura Atual vs Arquitetura-Alvo

### 2.1. Arquitetura Anterior (Monolítica e Dispersa)

```
┌────────────────────────────────────────────────────────┐
│ Módulos de Negócio (Mandado, P2B, PEC)                 │
│                                                        │
│  - Decisão de negócio misturada com cliques no DOM     │
│  - Listas locais redundantes de CSS/XPath              │
│  - Loops imperativos com fallbacks locais de até 18s   │
│  - Prints não estruturados e logging concorrente       │
│  - Imports dinâmicos manuais (importlib de api)        │
└───────────┬────────────────────────────────┬───────────┘
            │                                │
            ▼                                ▼
   ┌─────────────────┐             ┌─────────────────────┐
   │ Fix/core.py     │             │ api/variaveis_client│
   │ (Helpers soltos)│             │ (REST Gateway)      │
   └─────────────────┘             └─────────────────────┘
```

### 2.2. Arquitetura-Alvo (Modular e em Camadas)

```
┌────────────────────────────────────────────────────────┐
│ Regras de Negócio Puras (Pure Domain Rules)            │
│  - Classificação de textos / regex (sem DOM, sem API)  │
│  - Decisão determinística de qual ato executar         │
└───────────────────────────┬────────────────────────────┘
                            │
┌───────────────────────────▼────────────────────────────┐
│ Orquestradores de Fluxo (Mandado, P2B, PEC)            │
│  - Coordenam a sequência: API -> Regra -> Ação -> Check│
│  - Sem listas locais de seletores                      │
│  - Observabilidade estruturada e sanitizada            │
└──────────────┬──────────────────────────┬──────────────┘
               │                          │
┌──────────────▼──────────┐    ┌──────────▼──────────────┐
│ Registro Central de     │    │ API REST Gateway        │
│ Seletores Semânticos    │    │ (PjeApiClient)          │
│ (Ação -> Vencedor       │    │                         │
│  -> Fallback Único)     │    │ - Autenticação JWT      │
│                         │    │ - Download de binários  │
│ - Parada imediata       │    │ - Paginação unificada   │
│ - Telemetria HIT/MISS   │    └─────────────────────────┘
└──────────────┬──────────┘
               │
┌──────────────▼─────────────────────────────────────────┐
│ Fix/espera.py & Fix/browser_suporte.py (Playwright PW) │
│ - safe_click_no_scroll, click_headless_safe            │
│ - aguardar_renderizacao_nativa                         │
└────────────────────────────────────────────────────────┘
```

---

## 3. Contrato da Ação Semântica e Algoritmo do Vencedor

### 3.1. Identificação Semântica
Cada ponto de interação na interface do PJe é desacoplado de seletores CSS/XPath locais e identificado por uma chave semântica única:

`acao_semantica`: ex. `mandado_menu_flutuante`, `comunicacao_input_prazo`, `pec_carta_btn_anexar`.

### 3.2. Algoritmo de Execução Rápida
```
1. Consultar cache em memória do Vencedor para (acao, contexto).
2. Se vencedor existe:
     Tentar executar ação apenas com o vencedor (timeout curto, ex: 2.5s).
     Se sucesso:
       Incrementar contador de sucessos do vencedor.
       Retornar imediatamente (encerrando a cadeia).
     Se falhou:
       Invalidar vencedor no cache de execução.
       Registrar falha do vencedor anterior.
3. Se não há vencedor ou vencedor falhou:
     Iterar pela lista controlada centralizada de seletores da ação.
     No primeiro sucesso:
       Armazenar seletor como novo vencedor para a sessão.
       Retornar imediatamente.
4. Se todos os seletores da cadeia falharem:
     Lançar ElementoNaoEncontradoError com payload estruturado (ação, contexto, seletores testados).
```

---

## 4. O Plano de 10 Lotes de Refatoração

| Lote | Escopo | Arquivos Principais | Objetivo e Critérios de Aceitação |
|---|---|---|---|
| **Lote 1** | Testes de Caracterização | `tests/test_caracterizacao_regras.py` | Criar suite de testes unitários offline para travar o comportamento funcional das regras puras (PEC, Mandado, P2B).<br>**Critério:** Cobertura de 100% dos ramos de classificação jurídica sem dependência de browser. |
| **Lote 2** | Centralização de Observabilidade e Logs | `Fix/diagnostico_runtime.py`, `PEC/regras_execucao.py`, `PEC/anexos/*`, `Mandado/*` | Implementar `sanitizar_dados_sensiveis` (máscara de CPF/CNPJ) e `log_erro_estruturado`. Remover `logging.basicConfig(force=True)` e converter 65 `print(...)` em logs de debug.<br>**Critério:** Zero prints em stdout e logs de erro canônicos de 10 campos. |
| **Lote 3** | Centralização de Seletores e Vencedores | `Fix/seletores_catalogo.py` | Implementar módulo de catálogo com registro de ações semânticas, parada imediata ao primeiro sucesso, invalidação dinâmica e fallback contextual.<br>**Critério:** Testes unitários com DOM mock validando HIT/MISS e troca de vencedor. |
| **Lote 4** | Eliminação de Fallbacks Duplicados | `atos/comunicacao_preenchimento.py`, `Mandado/entrada_api.py` | Migrar loops locais de CSS/XPath para chamadas semânticas do catálogo central. Remover seletores obsoletos.<br>**Critério:** Redução drástica de linhas nos módulos chamadores e comportamento idêntico no browser. |
| **Lote 5** | Consolidação de Modelos e Helpers | `atos/judicial_modelos.py`, `atos/judicial_fluxo.py`, `atos/comunicacao_finalizacao.py` | Consolidar a inserção de modelos no CKEditor em função unificada com medição de baseline e guarda anti-corrida.<br>**Critério:** Eliminar duplicação entre fluxo de atos e fluxo de comunicações. |
| **Lote 6** | Separação de Camadas (Regra vs DOM) | `Mandado/regras.py` | Isolar a função pura `decidir_ato_despacho_argos` da execução física no navegador.<br>**Critério:** Regra testável via unit test sem WebDriver/Playwright ativo. |
| **Lote 7** | Simplificação de Funções Complexas | `Mandado/regras.py` | Refatorar `_executar_ato_seguro` para orquestrar as estratégias de despacho com tratamento de erro padronizado e retorno antecipado.<br>**Critério:** Aninhamento máximo de 3 níveis e eliminação de blocos repetidos de try/except. |
| **Lote 8** | Remoção de Código Morto Comprovado | `Mandado/*`, `Prazo/*`, `atos/*` | Excluir os 16 stubs e funções mortas comprovadas na auditoria estática (Seção 2.1 da Fase A).<br>**Critério:** Zero referências em todo o projeto e aprovação na compilação estática (`py_compile`). |
| **Lote 9** | Atualização de `idx.md` | `idx.md` | Documentar os novos componentes (`Fix/seletores_catalogo.py`, `log_erro_estruturado`, `inserir_modelo_no_editor`) e remover termos de funções excluídas.<br>**Critério:** Sincronização estrita da documentação do repositório. |
| **Lote 10** | Validação Completa Final | Workspace inteiro | Executar `pytest`, `tools/check_pw.py` (ratchet) e `play/smoke.py --projeto`.<br>**Critério:** Aprovação total em todos os linters e suítes de validação. |

---

## 5. Matriz de Riscos e Procedimentos de Rollback

| Risco Mapeado | Severidade | Ação Preventiva de Mitigação | Procedimento Cirúrgico de Rollback |
|---|---|---|---|
| Invalidação incorreta de seletor vencedor travar tela alterada | Média | O catálogo executa imediatamente toda a lista de fallbacks se o vencedor falhar. | Reversão atômica do commit do Lote 3/4 via `git revert 289dc4f 03fd11e`. |
| Remoção acidental de função com dispatch dinâmico | Baixa | Toda exclusão foi auditada estaticamente; funções com dependências cruzadas (ex: `_encontrar_documento_relevante`) foram preservadas. | Restauração pontual do arquivo afetado: `git checkout HEAD~1 -- CAMINHO/ARQUIVO.py`. |
| Conflito na digitação de minutas no CKEditor | Alta | Implementação de guarda de baseline: mede tamanho antes e depois da inserção, aguardando estabilidade do DOM. | Reversão do commit do Lote 5: `git revert 21d6747`. |
| Supressão de logs essenciais para suporte | Média | Logs de erro mantêm formato canônico com 10 atributos de diagnóstico completo. | Ajuste imediato do nível do logger em `Fix/diagnostico_runtime.py`. |

---

## 6. Lista Explícita do que NÃO Pode Ser Alterado

Para garantir total conformidade institucional e jurídica, os seguintes domínios foram declarados intocáveis:

1. **Termos e Regras Jurídicas:**
   - Dicionários de termos (`_TERMOS_ARGOS`, `_TERMOS_OUTROS`).
   - Critérios de liquidação, cálculo de crédito mock (`0.01`), prazo de intimação (30 dias).
   - Roteamento de destinatários, verificação de advogados e polos da ação.
2. **Módulos Classificados como SHIM:**
   - `Fix/abas.py`, `Fix/headless_helpers.py`, `Fix/element_wait.py`, `Fix/smart_finder.py`, `Fix/documents.py`, `Fix/navigation.py`, `Fix/gigs.py`, `Fix/selectors_pje.py`, `Fix/log.py`, `PEC/orquestrador.py`, `Prazo/p2b_core.py`, `atos/judicial.py`, `atos/movimentos.py`.
3. **Módulos e Pastas Legadas:**
   - `leg/`, `_archive/`, `Mandado/core.py`, `Mandado/processamento.py`, `Prazo/p2b_fluxo_prescricao.py`, `PEC/prescricao.py`.
4. **Backend Playwright Nativo:**
   - `play/pjeplay/*` (camada interna do motor de automação).
5. **Fluxos Não-Alvo:**
   - Triagem (`bianca/triagem_engine.py`), Petição (`Peticao/runtime_pet.py`), Domicílio Eletrônico (`bianca/dom_engine.py`), SISBAJUD autônomo (`SISB/core.py`).

---
*Fim do Plano Estrutural de Refatoração.*
