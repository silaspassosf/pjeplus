# PENDÊNCIAS E REGISTROS DE COMPORTAMENTO

> Arquivo para registrar falhas mecânicas, armadilhas identificadas e itens que exigem decisão arquitetural/comportamental.
> **Regra do contrato (Seção 3):** Se um teste falhar após edição mecânica, reverta o arquivo (`git checkout -- <arquivo>`), registre aqui com `arquivo:linha` e motivo. Nunca tente "adivinhar" ou alterar lógica sem validação prévia.

---

## 1. Baseline de Execução — Snapshot de Referência (Fase F0)

Data: 22/09/2026 18:12
Comando: `py play/smoke.py --projeto`
Resultado: 91/91 verificações passaram.

```text
=== pjeplay smoke ===
  [OK ] find_element por CSS
  [OK ] find_element por XPATH
  [OK ] find_element por ID
  [OK ] find_elements retorna lista
  [OK ] find_elements vazio nao explode
  [OK ] NoSuchElementException
  [OK ] get_attribute (atributo)
  [OK ] get_attribute (propriedade value)
  [OK ] is_displayed falso em oculto
  [OK ] click dispara handler
  [OK ] clear + send_keys + Keys.TAB
  [OK ] execute_script com argumentos
  [OK ] execute_script recebe elemento
  [OK ] execute_script devolve elemento
  [OK ] execute_async_script
  [OK ] WebDriverWait + EC.presence
  [OK ] WebDriverWait + EC.visibility em elemento tardio
  [OK ] EC.invisibility em oculto
  [OK ] TimeoutException do WebDriverWait
  [OK ] Select por texto visivel
  [OK ] current_url acessivel
  [OK ] page_source contem fixture
  [OK ] window_handles + switch_to + close
  [OK ] get_cookies no formato Selenium
  [OK ] alert auto-aceito nao trava a pagina
  [OK ] alert manual via switch_to
  [OK ] implicitly_wait aceito
  [OK ] nativo: aguardar_renderizacao_nativa (aparecer)
  [OK ] nativo: aguardar_renderizacao_nativa (tardio)
  [OK ] nativo: aguardar_renderizacao_nativa (sumir)
  [OK ] nativo: modo habilitado
  [OK ] nativo: timeout devolve False
  [OK ] nativo: esperar_elemento
  [OK ] nativo: esperar_elemento com texto
  [OK ] nativo: aguardar_e_clicar
  [OK ] nativo: aguardar_e_clicar inexistente -> False
  [OK ] nativo: preencher_campo
  [OK ] nativo: preencher_multiplos_campos
  [OK ] nativo: selecionar_opcao em <select>
  [OK ] nativo: is_headless_mode
  [OK ] pje: aguardar_angular sem testabilities (R4)
  [OK ] pje: esperar_spinner
  [OK ] pje: mat_select com overlay CDK atrasado (R2)
  [OK ] pje: mat_select exato nao pega o prefixo
  [OK ] pje: mat_checkbox marca
  [OK ] pje: mat_checkbox nao faz toggle indevido
  [OK ] pje: mat_data preenche e fecha
  [OK ] pje: linha_tabela filtra
  [OK ] pje: esperar_tabela
  [OK ] pje: ckeditor_versao detecta ck5 (R3)
  [OK ] pje: ckeditor set/get
  [OK ] pje: abrir_em_nova_aba (expect_page, sem race)
  [OK ] pje: fechar_abas_extras
  [OK ] pje: sessao_expirada falso na fixture
  [OK ] guarda: fronteira intacta
  [OK ] espera: assentar retorna cedo com a tela parada
  [OK ] espera: assentar nao antecipa trabalho que ainda vai comecar
  [OK ] espera: assentar nunca excede o teto do sleep original
  [OK ] espera: ate_sumir
  [OK ] espera: ate_desabilitar em botao ativo devolve False
  [OK ] espera: ate_desabilitar detecta botao desabilitado
  [OK ] espera: ate_texto
  [OK ] espera: ate_js
  [OK ] espera: ate_aparecer aceita XPath
  [OK ] espera: ate_sumir aceita XPath
  [OK ] espera: XPath falso devolve False, nao estoura
  [OK ] espera: e_xpath distingue CSS de XPath
  [OK ] api: requisicao usa o contexto do browser
  [OK ] api: obter_json pelo contexto
  [OK ] api: obter_json devolve None em rota inexistente
  [OK ] api: requisicao herda a sessao do browser (sem copiar cookie)
  [OK ] api: esperar_resposta captura o XHR da acao
  [OK ] api: esperar_conclusao confirma a requisicao
  [OK ] api: registrar_trafego coleta as chamadas
  [OK ] api: session_from_driver funciona sem alteracao
  [OK ] medicao: contabiliza sleeps e restaura time.sleep
  [OK ] medicao: envolve e restaura helpers de Fix
  [OK ] medicao: separa tempo_helper de tempo_morto
  [OK ] Fix.core importa sob o backend
  [OK ] helpers de Fix.core foram trocados
  [OK ] import Fix.variaveis
  [OK ] import Fix.extracao
  [OK ] import Fix.utils
  [OK ] import atos.judicial_fluxo
  [OK ] import atos.comunicacao
  [OK ] import PEC.runtime_pec
  [OK ] import Prazo.loop_orquestrador
  [OK ] import Mandado.entrada_api
  [OK ] import SISB.core
  [OK ] import Peticao.runtime_pet
  [OK ] import bianca.triagem_engine

91/91 verificacoes passaram
```

---

## 2. Armadilhas e Bugs Conhecidos (NÃO consertar durante migração)

| Item | Local | Diagnóstico / Descrição | Diretriz |
|---|---|---|---|
| Import quebrado em Fix.core | `Fix/core.py:2551` | Importa `obter_sessao_do_driver` de `Fix.variaveis`, mas a função real é `session_from_driver` ou `cliente_para`. | **Não consertar na F4**. Bug comportamental preexistente. Manter até decisão expressa. |
| Validação de snackbar em `mov_sob` | `atos/movimentos_sobrestamento.py` | Snackbar efêmera do Angular pode sumir antes do polling, gerando falso-negativo. | Mudança de critério é comportamental; não alterar sem alinhamento. |
| Cascata de janelas fechadas | Vários fluxos | Erro "Nenhuma janela aberta" derruba múltiplos processos em cadeia após crash da janela do browser. | Trata-se de ausência de health-check, não regressão de Playwright. |
| Clique em polo ativo | `atos/comunicacao_destinatarios.py` | Botões `mat-icon-button` exigem escada: limpar overlay -> clique real -> fallback sintético. | `dispatchEvent` isolado não dispara o handler nativo. |
| Dependência `pdfplumber` | `.venv` | Módulo ausente no ambiente Python 3.13 de desenvolvimento. | Questão de ambiente/pacote; não mascarar ou contornar na refatoração. |

---

## 3. Registro de Falhas e Reversões durante a Migração

*(Nenhuma ocorrência até o momento — Fase F0 em andamento)*
