# Arquitetura — bianca

## Camadas do Sistema

```
┌─────────────────────────────────────────────────────┐
│                    main.py                          │
│          (menus + orquestrador + TeeOutput)         │
└──────────────┬──────────────────┬───────────────────┘
               │                  │
    ┌──────────▼──────┐  ┌────────▼────────┐
    │  triagem_engine │  │   dom_engine    │
    │   run_triagem() │  │   run_dom()     │
    └──────┬──────────┘  └────────┬────────┘
           │                      │
    ┌──────▼──────────┐  ┌────────▼────────┐
    │ triagem_regras  │  │   atos_utils    │
    │ (coleta+regras) │  │ (def_chip+PEC)  │
    └──────┬──────────┘  └────────┬────────┘
           │                      │
    ┌──────▼──────────────────────▼────────┐
    │              extracao.py             │
    │  (criar_gigs, comentario, lembrete,  │
    │   indexar_processos, abrir_detalhes) │
    └──────────────┬────────────────────────┘
                   │
    ┌──────────────▼────────────────────────┐
    │           selenium_utils.py           │
    │  (aguardar_e_clicar, safe_click,      │
    │   preencher_campo, esperar_elemento,  │
    │   filtrofases, aplicar_filtro_100)    │
    └──────────────┬────────────────────────┘
                   │
    ┌──────────────▼────────────────────────┐
    │            api_client.py              │
    │  (PjeApiClient, session_from_driver,  │
    │   gateway_patch, buscar_paginado)     │
    └──────────────┬────────────────────────┘
                   │
    ┌──────────────▼────────────────────────┐
    │               utils.py               │
    │  (resultado_ok/falha, run_batch,      │
    │   RuleRegistry, ResultadoFluxo)       │
    └──────────────┬────────────────────────┘
                   │
    ┌──────────────▼────────────────────────┐
    │               config.py              │
    │  (GECKODRIVER_PATH, FIREFOX_BINARY,  │
    │   URLs, CEPs, salário mínimo)        │
    └───────────────────────────────────────┘

    ┌───────────────────────────────────────┐
    │               driver.py              │  ← usado por main.py
    │  (criar_driver, login manual)        │
    └───────────────────────────────────────┘
```

---

## Descrição de cada arquivo

| Arquivo | Responsabilidade | Fontes originais |
|---------|-----------------|-----------------|
| `config.py` | Caminhos (geckodriver, Firefox), URLs PJe, constantes (salário, CEPs) | `Triagem/runtime_triagem.py` linhas 34–77 |
| `driver.py` | Cria Firefox Dev Edition, prompts CPF/senha no terminal | `Fix/core.py::criar_driver_pc`, `Fix/utils.py::login_cpf` (reescrita) |
| `utils.py` | Tipos base, resultado_ok/falha, run_batch, RuleRegistry | `Fix/tipos.py`, `utilitarios_processamento.py`, `core/rule_registry.py` |
| `selenium_utils.py` | Operações Selenium (click, wait, fill, tabs, overlays) | `Fix/core.py`, `Fix/browser_suporte.py`, `Fix/abas.py`, `Fix/headless_helpers.py` |
| `api_client.py` | Cliente HTTP para API PJe, cópia de cookies do driver | `api/variaveis_client.py`, `api/variaveis_helpers.py` |
| `extracao.py` | Criação de GIGS/comentários/lembretes, indexação de lista, abertura de processos | `Fix/extracao.py` (subconjunto) |
| `atos_utils.py` | Remoção de chips (def_chip) e criação de PEC (wrappers) | `atos/movimentos_chips.py`, `atos/wrappers_pec.py` |
| `triagem_regras.py` | Coleta de dados do processo (API/PDF/OCR) e regras de alertas | `Triagem/coleta.py`, `Triagem/regras.py` |
| `triagem_engine.py` | Busca lista triagem, enriquece processos, executa triagem_peticao, ações pós-triagem | `Triagem/runtime_triagem.py`, `Triagem/analise_execucao.py` |
| `dom_engine.py` | Fluxo Dom Eletrônico: navega atividades, callbacks bucket1/bucket2, run_dom | `Triagem/dom.py` |
| `main.py` | Menu terminal, cria driver+login, despacha fluxo, captura log | `x.py` (subset) |
| `requirements.txt` | Dependências Python: selenium, requests, pillow, pdf2image, pytesseract | — |
| `instalar.bat` | Setup automático: venv, pip, geckodriver, verificação Firefox | — |
| `drivers/geckodriver.exe` | GeckoDriver binário para controlar Firefox | Copiado de `Fix/geckodriver.exe` |

---

## Fluxo de Execução — run_triagem

```
main.py::main()
  └─ criar_driver_e_fazer_login()         # driver.py — Firefox + CPF/senha no terminal
       └─ executar_triagem(driver)
            └─ run_triagem(driver)         # triagem_engine.py
                 ├─ drv.get(URL_LISTA_TRIAGEM)
                 ├─ esperar_elemento(...)  # selenium_utils
                 ├─ buscar_lista_triagem(drv)
                 │    └─ _criar_cliente(drv)     # api_client.py
                 │    └─ _buscar_paginado_patch(...)
                 ├─ [filtra triagem_inicial]
                 ├─ [enriquece cada item → bucket A/B/C/D]
                 └─ run_batch(lista, ...)  # utils.py
                      ├─ open_item(proc)   → drv.get(url_processo)
                      ├─ execute_item(proc)
                      │    ├─ triagem_peticao(drv)    # triagem_engine.py
                      │    │    └─ coletar_dados_processo(...)  # triagem_regras.py
                      │    ├─ criar_comentario(drv, texto)      # extracao.py
                      │    ├─ _aplicar_acao_pos_triagem(...)
                      │    │    ├─ determinar_acao_pos_triagem(txt)  # triagem_regras.py
                      │    │    └─ acao_bucket_X(drv, numero, info)  # triagem_engine.py
                      │    └─ fechar_abas_extras(drv)           # selenium_utils.py
                      └─ persist_result(proc, result)  # sem-op (sem progresso)
```

---

## Fluxo de Execução — run_dom

```
main.py::main()
  └─ criar_driver_e_fazer_login()
       └─ executar_dom(driver)
            └─ run_dom(driver)             # dom_engine.py
                 ├─ drv.get(LIST_URL)
                 ├─ filtrofases(drv, ['conhecimento'])   # selenium_utils.py
                 ├─ navigate_to_activities_and_filter(drv)
                 │    ├─ drv.get(url_atividades)
                 │    ├─ [remove chip Vencidas]
                 │    ├─ [preenche filtro dom.e]
                 │    └─ aplicar_filtro_100(drv)
                 └─ execute_list_with_bucket2_callback(drv)
                      ├─ indexar_processos(drv)          # extracao.py
                      └─ processar_item_dom(drv, item)
                           ├─ abrir_detalhes_processo(drv, linha)  # extracao.py
                           └─ callback_bucket2(drv, tipo)
                                ├─ def_chip(drv, chips_ciencia_resposta)  # atos_utils.py
                                ├─ criar_gigs(drv, 'dom.e')               # extracao.py
                                ├─ has_dom_eletronico_reminder(drv)
                                ├─ checar_empresas(drv)
                                ├─ criar_lembrete_posit(drv, "DomicEletr", ...)  # extracao.py
                                └─ pec_wrapper(drv)     # atos_utils.py
```

---

## Política de Login Manual

`driver.py::fazer_login_manual(driver)` — lógica:

```python
# Opção A: preencher campos automaticamente após prompts
cpf = input("CPF (somente números): ").strip()
senha = input("Senha PJe: ").strip()
# preenche campo CPF, campo senha, clica entrar

# Opção B: aguardar login manual (mais robusto se tela mudar)
driver.get("https://pje.trt2.jus.br/pjekz/")
input("Faça o login no navegador e pressione ENTER aqui para continuar...")
```

A **Opção A** (preencher campos) é preferida por não exigir interação com o navegador. Mas se a tela de login do PJe mudar seletores, a **Opção B** é o fallback seguro.

A função deve implementar A com fallback para B se a página não carregar campos em 10s.

---

## Decisões Explícitas de Design

### Por que não importar Fix.* diretamente?

`bianca/` deve ser 100% standalone — pode ser copiada para outra máquina sem o restante do projeto. Importar `Fix.*` criaria dependência implícita da estrutura de pastas do projeto principal.

### Por que copiar e não symlink?

Symlinks não funcionam de forma confiável em Windows sem permissões elevadas e quebram em cópias de pasta.

### Por que sem ProgressoUnificado?

O requisito explícito é "não é necessário migrar controle de progresso". Em `bianca/`, cada execução começa do zero. Isso simplifica o código e elimina 3 dependências.

### Por que `utils.py` inclui RuleRegistry?

`core/rule_registry.py` é um utilitário genérico que `triagem_regras.py` precisa. Incluí-lo em `utils.py` evita criar um arquivo de 1 função, mantendo o mínimo de arquivos.

### Por que `instalar.bat` e não `setup.py`?

O público-alvo usa Windows e chama `py` no terminal. Um `.bat` é mais imediato e não exige entender Python packaging.
