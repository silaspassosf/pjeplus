# Bug Analysis — pec_excluiargos: seleção primeira reclamada + endereço TRT não funciona

**Data:** 2026-07-27
**Módulo:** atos (comunicacao_destinatarios)
**Severidade:** bloqueante

---

## 1. Relato Original

A função de selecionar primeira reclamada + endereço TRT não está funcionando no fluxo `pec_excluiargos`. Em `LEGADO.md` existe uma implementação funcional do mesmo fluxo. O objetivo é corrigir mantendo as regras de negócio atuais, já favorecendo a migração para Playwright (uso de `espera.*` em vez de `time.sleep`/`WebDriverWait` cru).

---

## 2. Pontos de Entrada

| Arquivo | Função | Linha | Papel no fluxo |
|---|---|---|---|
| `atos/comunicacao_destinatarios.py` | `selecionar_destinatarios()` | L392 | Orquestrador de seleção de destinatários; contém o bloco `destinatarios == 'primeiro'` |
| `atos/wrappers_pec.py` | `pec_excluiargos` | L102 | Wrapper que invoca o fluxo com `destinatarios='primeiro'` |
| `atos/comunicacao.py` | `make_comunicacao_wrapper()` | L88 | Factory que cria o wrapper e repassa `destinatarios='primeiro'` para `selecionar_destinatarios` |

---

## 3. Diagnóstico

### 3.1 Causa Raiz

O bloco `destinatarios == 'primeiro'` (L484-636) usa `safe_click_no_scroll()` para clicar no header do painel "Polo Passivo" e na primeira seta de destinatário. Esta função dispara um `dispatchEvent(new MouseEvent('click', {...}))` — um evento sintético — que **não equivale ao `element.click()` nativo**. Em componentes Angular Material (`mat-expansion-panel-header`), o evento sintético pode não acionar corretamente o toggle do painel nem a detecção de mudanças do Angular, deixando o painel fechado. Com o painel fechado, a seta do primeiro destinatário não está acessível no DOM visível, e o fluxo falha.

Agravante: não há `aguardar_renderizacao_nativa` após o clique no header (o `leg/` e o `LEGADO.md` incluem essa espera), e a lógica de endereço do tribunal está inline com try/except aninhados que suprimem silenciosamente erros.

### 3.2 Evidências

- `atos/comunicacao_destinatarios.py:496` — `safe_click_no_scroll(driver, painel_header)` usa `dispatchEvent(MouseEvent)`, não `element.click()` nativo
- `atos/comunicacao_destinatarios.py:511` — `safe_click_no_scroll(driver, primeira_seta)` mesmo padrão
- `Fix/browser_suporte.py:511-517` — `safe_click_no_scroll` definido como `dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true}))`
- `leg/atos/comunicacao_destinatarios.py:548-551` — versão leg usa `click_headless_safe` (estratégia 1 = `element.click()` nativo Selenium)
- `LEGADO.md:2135-2137` — versão funcional usa `driver.execute_script("arguments[0].click();", ...)` que equivale ao `.click()` nativo
- `atos/comunicacao_destinatarios.py:497` — ausência de `aguardar_renderizacao_nativa` após expandir painel (presente no `leg/` L549)
- `atos/comunicacao_destinatarios.py:632` — erro do tribunal suprimido: retorna `sucesso=True` mesmo quando o endereço TRT falha

### 3.3 Impacto

- **`pec_excluiargos`**: completamente quebrado — não seleciona o primeiro destinatário do Polo Passivo, portanto não gera comunicação de exclusão de convênios (SERASA/CNIB)
- **Degradação silenciosa**: o tribunal address é tratado como opcional (exceção suprimida em L632), então mesmo que o clique funcione, o endereço TRT pode nunca ser configurado
- **PW migration**: o uso de `dispatchEvent` não tem equivalente direto no Playwright (que usa `locator.click()` com actionability checks), tornando a migração mais complexa

---

## 4. Correção Sugerida

### 4.1 Estratégia

Substituir `safe_click_no_scroll` por `click_headless_safe` nos dois pontos de clique do bloco `primeiro`, adicionar `aguardar_renderizacao_nativa` após expandir o painel, e extrair a lógica de endereço do tribunal para funções auxiliares `_selecionar_endereco_tribunal` + `_incluir_tribunal_por_cep` (já existentes no `leg/`). Manter `espera.*` para waits — estas já têm caminho de migração PW documentado (`pjeplay.nativo`).

### 4.2 Pontos de Alteração

1. **`atos/comunicacao_destinatarios.py:selecionar_destinatarios()` (bloco `primeiro`, L484-636)** — Substituir todo o bloco inline pela versão simplificada do `leg/`: usar `click_headless_safe` para os dois cliques, adicionar `aguardar_renderizacao_nativa` pós-expansão, delegar endereço tribunal para `_selecionar_endereco_tribunal()`
2. **`atos/comunicacao_destinatarios.py` (novo)** — Adicionar funções `_selecionar_endereco_tribunal()` e `_incluir_tribunal_por_cep()` copiadas/adaptadas do `leg/atos/comunicacao_destinatarios.py:143-178` e `:179-226`, substituindo `time.sleep` por `espera.assentar` onde aplicável
3. **`atos/comunicacao_destinatarios.py` (imports)** — Garantir import de `click_headless_safe` de `Fix.browser_suporte` e `aguardar_renderizacao_nativa` de `Fix.core`

### 4.3 Riscos

- **Regressão em outros modos**: `polo_passivo`, `terceiros` e `informado` também usam `safe_click_no_scroll` ou `_clicar_e_aguardar_spinner` (que internamente usa `safe_click_no_scroll`). Se o `dispatchEvent` for problemático em geral, outros fluxos podem ter o mesmo bug latente. Escopo desta correção: apenas o bloco `primeiro`.
- **Timing no tribunal**: A versão leg usa `time.sleep` em vários pontos; substituir por `espera.assentar` mantém o mesmo comportamento em Selenium (sleep equivalente), mas em PW futuro poderá ser mais rápido. Sem risco de regressão.

---

## 5. Dump de Funcoes

### 1. `atos/comunicacao_destinatarios.py` — `selecionar_destinatarios(driver, destinatarios, terceiro=False, ...)`

**Range:** L392-L647 (256 linhas)
**Callers:** `atos/comunicacao.py:make_comunicacao_wrapper()`
**Callees:** `espera.elemento()`, `safe_click_no_scroll()`, `espera.ate_habilitar()`
**Relevancia:** Ponto de entrada — contem o bloco 'primeiro' com a falha (L484-636)

```python
# atos/comunicacao_destinatarios.py L392-L647
def selecionar_destinatarios(driver, destinatarios, terceiro=False, debug=False, log=None, cliques_polo_passivo=1, cliques_informado=2, observacao=None, numero_processo=None, dados_processo=None):
    from core.resultado_execucao import ResultadoExecucao
    if log is None:
        def log(_msg):
            return None

    qtd_seta = 2 if str(cliques_polo_passivo).strip().lower() in ('2', '2x') else 1
    qtd_informado = 2 if str(cliques_informado).strip().lower() in ('2', '2x') else 1
    qtd_cliques_fallback = 2 if str(cliques_polo_passivo).strip().lower() in ('2', '2x') else 1

    # Roteamento principal
    if destinatarios is None:
        log('[DESTINATARIOS] Parâmetro None - pulando seleção')
        return ResultadoExecucao(sucesso=False, status='skip', detalhes={'count': 0})

    if isinstance(destinatarios, list):
        log('[DESTINATARIOS] Lista explícita recebida via override')
        return _selecionar_por_lista(driver, destinatarios, 'lista explícita', log, fallback_polo_passivo=True, qtd_seta_override=None, debug=debug, qtd_cliques_fallback=qtd_cliques_fallback)

    if destinatarios == 'extraido':
        log('[DESTINATARIOS] OPÇÃO EXTRAIDO: carregando destinatários em cache')
        try:
            from Fix.extracao_processo import carregar_destinatarios_cache
            cache = carregar_destinatarios_cache() or {}
            lista_destinatarios = cache.get('destinatarios', []) or []
            return _selecionar_por_lista(driver, lista_destinatarios, 'cache', log, fallback_polo_passivo=True, qtd_seta_override=2, debug=debug, qtd_cliques_fallback=qtd_cliques_fallback)
        except Exception as e:
            log(f'[DESTINATARIOS][ERRO] Falha no modo extraido: {e}')
            return ResultadoExecucao(sucesso=False, status='error', erro=str(e), detalhes={'count': 0})

    if destinatarios == 'informado':
        log('[DESTINATARIOS] OPÇÃO INFORMADO: cruzando observação com dados do processo')
        try:
            if not dados_processo:
                try:
                    from Fix.extracao_processo import extrair_dados_processo
                    dados_processo = extrair_dados_processo(driver, caminho_json='dadosatuais.json', debug=debug)
                except Exception:
                    dados_processo = _carregar_dadosatuais_local('dadosatuais.json')

            candidatos = _montar_destinatarios_por_observacao(observacao, dados_processo, debug=debug)
            return _selecionar_por_lista(driver, candidatos, 'observação', log, fallback_polo_passivo=True, qtd_seta_override=qtd_informado, debug=debug, qtd_cliques_fallback=qtd_cliques_fallback)
        except Exception as e:
            log(f'[DESTINATARIOS][ERRO] Falha no modo informado: {e}')
            return ResultadoExecucao(sucesso=False, status='error', erro=str(e), detalhes={'count': 0})

    if destinatarios == 'polo_ativo':
        log('[DESTINATARIOS] OPÇÃO: Clicando no polo ativo')
        try:
            btn = wait_for_clickable(driver, 'button[name="btnIntimarSomentePoloAtivo"]', timeout=10, by=By.CSS_SELECTOR)
            if not btn:
                raise RuntimeError('Botão polo ativo não clicável')
            _clicar_e_aguardar_spinner(driver, btn)
            return ResultadoExecucao(sucesso=True, status='geral', detalhes={'count': 0})
        except Exception as e:
            log(f'[DESTINATARIOS][ERRO] Falha ao clicar polo ativo: {e}')
            return ResultadoExecucao(sucesso=False, status='error', erro=str(e), detalhes={'count': 0})

    if destinatarios in ('polo_passivo', 'polo_passivo_2x'):
        cliques = cliques_polo_passivo if destinatarios == 'polo_passivo' else 2
        log(f'[DESTINATARIOS] Clicando no polo passivo ({cliques}x)')
        try:
            btn_polo_passivo = wait_for_clickable(driver, 'button[name="btnIntimarSomentePoloPassivo"]', timeout=5, by=By.CSS_SELECTOR)
            if not btn_polo_passivo:
                raise RuntimeError('Botão polo passivo não clicável')
            for i in range(cliques):
                _clicar_e_aguardar_spinner(driver, btn_polo_passivo)
                if i < cliques - 1:
                    # Spinner já sumiu (garantido por _clicar_e_aguardar_spinner) — apenas
                    # reobter a referência (Angular pode recriar o nó), sem novo timeout de espera.
                    btn_polo_passivo = driver.find_element(By.CSS_SELECTOR, 'button[name="btnIntimarSomentePoloPassivo"]')
            return ResultadoExecucao(sucesso=True, status='geral', detalhes={'count': 0})
        except Exception as e:
            log(f'[DESTINATARIOS][ERRO] Falha ao clicar polo passivo: {e}')
            return ResultadoExecucao(sucesso=False, status='error', erro=str(e), detalhes={'count': 0})

    if destinatarios == 'terceiros':
        log('[DESTINATARIOS] OPÇÃO TERCEIROS: Clicando em terceiros interessados')
        try:
            if espera.ate_habilitar(driver, 'button[name="btnIntimarSomenteTerceirosInteressados"]', teto=5):
                btn_terceiro = driver.find_element(By.CSS_SELECTOR, 'button[name="btnIntimarSomenteTerceirosInteressados"]')
            else:
                # <i> não tem estado disabled real: ate_aparecer, não ate_habilitar
                espera.ate_aparecer(driver, 'i.fa.fa-user.pec-polo-outros-partes-processo', teto=5)
                btn_terceiro = driver.find_element(By.CSS_SELECTOR, 'i.fa.fa-user.pec-polo-outros-partes-processo')
            _clicar_e_aguardar_spinner(driver, btn_terceiro)
            return ResultadoExecucao(sucesso=True, status='geral', detalhes={'count': 0})
        except Exception as e:
            log(f'[DESTINATARIOS][ERRO] Falha ao selecionar terceiros: {e}')
            return ResultadoExecucao(sucesso=False, status='error', erro=str(e), detalhes={'count': 0})

    if destinatarios == 'primeiro':
        log('[DESTINATARIOS] OPCAO PRIMEIRO: primeiro do Polo Passivo (pec_excluiargos)')
        try:
            # 1. Expandir painel Polo Passivo (legado: WebDriverWait + execute_script)
            painel_header_xpath = (
                '//mat-expansion-panel-header[.//div[contains(@class,"pec-titulo-painel-expansivel-partes-processo")'
                ' and contains(normalize-space(.), "Polo Passivo")]]'
            )
            painel_header = espera.elemento(driver, painel_header_xpath, teto=10, visivel=False)
            if painel_header is None:
                raise Exception('painel Polo Passivo não apareceu')
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", painel_header)
            safe_click_no_scroll(driver, painel_header)
            espera.assentar(driver, 0.5)

            # 2. Clicar na primeira seta do Polo Passivo (legado: WebDriverWait + execute_script)
            seta_xpath = (
                '//mat-expansion-panel[.//*[contains(text(), "Polo Passivo")]]'
                '//button[@aria-label="Clique para acrescentar esta parte '
                'à lista de destinatários de expedientes e comunicações."][1]'
            )
            if not espera.ate_habilitar(driver, seta_xpath, teto=10):
                raise Exception('primeira seta do Polo Passivo não habilitou')
            primeira_seta = driver.find_element(By.XPATH, seta_xpath)
            safe_click_no_scroll(driver, primeira_seta)
            log('[DESTINATARIOS] Primeira seta (primeiro destinatário) clicada')
            espera.assentar(driver, 1)

            # 3. Buscar e adicionar TRIBUNAL se necessário (pec_excluiargos)
            try:
                log('[DESTINATARIOS] 3. Buscando tribunal nos endereços disponíveis...')

                # Verificar se formulário de consulta de endereços apareceu
                try:
                    WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, '.pec-consulta-enderecos'))
                    )
                    log('[DESTINATARIOS] 3a. Formulário de consulta de endereços detectado')
                except Exception:
                    log('[DESTINATARIOS] 3a. Formulário de consulta de endereços não apareceu')
                    raise Exception('Consulta não apareceu')

                # Verificar se há snack-bar de "Nenhum resultado encontrado"
                try:
                    WebDriverWait(driver, 3).until(
                        EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Nenhum resultado encontrado')]"))
                    )
                    log('[DESTINATARIOS] 3b. Snack-bar detectado: "Nenhum resultado encontrado" -> incluir tribunal via CEP')

                    # Digitar CEP 01302906 no campo inputCep
                    log('[DESTINATARIOS] 3c. Digitando CEP 01302906 no campo inputCep')
                    campo_cep = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, 'input#inputCep'))
                    )
                    campo_cep.clear()
                    for char in '01302906':
                        campo_cep.send_keys(char)
                        espera.assentar(driver, 0.1)
                    espera.ate_texto(driver, 'span.mat-option-text', '01302-906', teto=1)

                    log('[DESTINATARIOS] 3d. Clicando na opção do tribunal TRT2 São Paulo')
                    opcao_tribunal = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, "//span[@class='mat-option-text' and contains(text(), '01302-906')]"))
                    )
                    opcao_tribunal.click()
                    log('[DESTINATARIOS] Opção do tribunal selecionada')
                    espera.ate_habilitar(driver, 'button[aria-label="Salva as alterações"]', teto=0.5)

                    log('[DESTINATARIOS] 3e. Clicando no botão Salvar das alterações')
                    btn_salvar_alteracoes = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[aria-label="Salva as alterações"]'))
                    )
                    btn_salvar_alteracoes.click()
                    log('[DESTINATARIOS] Alterações salvas')
                    espera.ate_aparecer(driver, 'i.fa.fa-window-close.btn-fechar', teto=0.5)

                    log('[DESTINATARIOS] 3f. Clicando no botão fechar para fechar endereços')
                    btn_fechar = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, 'i.fa.fa-window-close.btn-fechar'))
                    )
                    btn_fechar.click()
                    log('[DESTINATARIOS] Janela de endereços fechada')
                except Exception:
                    # Se não houver snack-bar, procurar tribunal nas linhas da tabela
                    log('[DESTINATARIOS] 3b. Nenhum snack-bar - buscando tribunal na tabela de endereços')
                    try:
                        WebDriverWait(driver, 5).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, 'table[name="Endereços do destinatário no sistema"]'))
                        )

                        # Procura por linhas que contenham "TRIBUNAL" (case insensitive)
                        linhas_tribunal = driver.find_elements(
                            By.XPATH,
                            "//td[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'tribunal')]"
                        )

                        if linhas_tribunal:
                            log('[DESTINATARIOS] 3c. Encontrado endereço do tribunal, clicando na seta')
                            linha_tribunal = linhas_tribunal[0].find_element(By.XPATH, './ancestor::tr')
                            seta_tribunal = linha_tribunal.find_element(By.CSS_SELECTOR, 'button[aria-label="Selecionar endereço"]')
                            seta_tribunal.click()
                            log('[DESTINATARIOS] Endereço do tribunal selecionado')
                            time.sleep(0.5)

                            log('[DESTINATARIOS] 3d. Clicando no botão fechar para fechar endereços')
                            btn_fechar = WebDriverWait(driver, 10).until(
                                EC.element_to_be_clickable((By.CSS_SELECTOR, 'i.fa.fa-window-close.btn-fechar'))
                            )
                            btn_fechar.click()
                            log('[DESTINATARIOS] Janela de endereços fechada')
                        else:
                            log('[DESTINATARIOS] 3c. Nenhum endereço do tribunal encontrado na tabela - incluindo tribunal via CEP')

                            log('[DESTINATARIOS] 3d. Digitando CEP 01302906 no campo inputCep')
                            campo_cep = WebDriverWait(driver, 10).until(
                                EC.element_to_be_clickable((By.CSS_SELECTOR, 'input#inputCep'))
                            )
                            campo_cep.clear()
                            for char in '01302906':
                                campo_cep.send_keys(char)
                                time.sleep(0.1)
                            time.sleep(1)

                            log('[DESTINATARIOS] 3e. Clicando na opção do tribunal TRT2')
                            opcao_tribunal = WebDriverWait(driver, 10).until(
                                EC.element_to_be_clickable((By.XPATH, "//span[@class='mat-option-text' and contains(text(), '01302-906')]"))
                            )
                            opcao_tribunal.click()
                            log('[DESTINATARIOS] Tribunal selecionado')
                            time.sleep(0.5)

                            log('[DESTINATARIOS] 3f. Clicando em Salvar alterações')
                            btn_salvar_alteracoes = WebDriverWait(driver, 10).until(
                                EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[aria-label="Salva as alterações"]'))
                            )
                            btn_salvar_alteracoes.click()
                            log('[DESTINATARIOS] Alterações salvas')
                            time.sleep(0.5)

                            log('[DESTINATARIOS] 3g. Fechando janela de endereços')
                            btn_fechar = WebDriverWait(driver, 10).until(
                                EC.element_to_be_clickable((By.CSS_SELECTOR, 'i.fa.fa-window-close.btn-fechar'))
                            )
                            btn_fechar.click()
                            log('[DESTINATARIOS] Janela fechada')
                    except Exception as e_tabela:
                        log(f'[DESTINATARIOS] Erro ao processar endereços: {e_tabela}')
            except Exception as tribunal_err:
                log(f'[DESTINATARIOS] Aviso: Não foi possível adicionar tribunal: {tribunal_err}')

            return ResultadoExecucao(sucesso=True, status='ok', detalhes={'count': 1})
        except Exception as e:
            log(f'[DESTINATARIOS][ERRO] Falha ao selecionar primeiro destinatário: {e}')
            return ResultadoExecucao(sucesso=False, status='error', erro=str(e), detalhes={'count': 0})
    # opção padrão: clicar polo passivo 1x
    log('[DESTINATARIOS] OPÇÃO PADRÃO: Clicando no polo passivo (1x)')
    try:
        btn_polo_passivo = wait_for_clickable(driver, 'button[name="btnIntimarSomentePoloPassivo"]', timeout=10, by=By.CSS_SELECTOR)
        if not btn_polo_passivo:
            raise RuntimeError('Botão polo passivo não clicável')
        _clicar_e_aguardar_spinner(driver, btn_polo_passivo)
        return ResultadoExecucao(sucesso=True, status='geral', detalhes={'count': 0})
    except Exception as e:
        log(f'[DESTINATARIOS][ERRO] Falha ao clicar polo passivo padrão: {e}')
        return ResultadoExecucao(sucesso=False, status='error', erro=str(e), detalhes={'count': 0})
```


### 2. `leg/atos/comunicacao_destinatarios.py` — `selecionar_destinatarios(driver, destinatarios, terceiro=False, ...)`

**Range:** L451-L570 (120 linhas)
**Callers:** `atos/comunicacao.py:make_comunicacao_wrapper()`
**Callees:** `click_headless_safe()`, `aguardar_renderizacao_nativa()`, `_selecionar_endereco_tribunal()`
**Relevancia:** Versao funcional de referencia no leg/ — bloco 'primeiro' simplificado (L548-563)

```python
# leg/atos/comunicacao_destinatarios.py L451-L570
def selecionar_destinatarios(driver, destinatarios, terceiro=False, debug=False, log=None, cliques_polo_passivo=1, cliques_informado=2, observacao=None, numero_processo=None, dados_processo=None):
    from core.resultado_execucao import ResultadoExecucao
    if log is None:
        def log(_msg):
            return None

    qtd_seta = 2 if str(cliques_polo_passivo).strip().lower() in ('2', '2x') else 1
    qtd_informado = 2 if str(cliques_informado).strip().lower() in ('2', '2x') else 1
    qtd_cliques_fallback = 2 if str(cliques_polo_passivo).strip().lower() in ('2', '2x') else 1

    # Roteamento principal
    if destinatarios is None:
        log('[DESTINATARIOS] Parâmetro None - pulando seleção')
        return ResultadoExecucao(sucesso=False, status='skip', detalhes={'count': 0})

    if isinstance(destinatarios, list):
        log('[DESTINATARIOS] Lista explícita recebida via override')
        return _selecionar_por_lista(driver, destinatarios, 'lista explícita', log, fallback_polo_passivo=True, qtd_seta_override=None, debug=debug, qtd_cliques_fallback=qtd_cliques_fallback)

    if destinatarios == 'extraido':
        log('[DESTINATARIOS] OPÇÃO EXTRAIDO: carregando destinatários em cache')
        try:
            from Fix.extracao_processo import carregar_destinatarios_cache
            cache = carregar_destinatarios_cache() or {}
            lista_destinatarios = cache.get('destinatarios', []) or []
            return _selecionar_por_lista(driver, lista_destinatarios, 'cache', log, fallback_polo_passivo=True, qtd_seta_override=2, debug=debug, qtd_cliques_fallback=qtd_cliques_fallback)
        except Exception as e:
            log(f'[DESTINATARIOS][ERRO] Falha no modo extraido: {e}')
            return ResultadoExecucao(sucesso=False, status='error', erro=str(e), detalhes={'count': 0})

    if destinatarios == 'informado':
        log('[DESTINATARIOS] OPÇÃO INFORMADO: cruzando observação com dados do processo')
        try:
            if not dados_processo:
                try:
                    from Fix.extracao_processo import extrair_dados_processo
                    dados_processo = extrair_dados_processo(driver, caminho_json='dadosatuais.json', debug=debug)
                except Exception:
                    dados_processo = _carregar_dadosatuais_local('dadosatuais.json')

            candidatos = _montar_destinatarios_por_observacao(observacao, dados_processo, debug=debug)
            return _selecionar_por_lista(driver, candidatos, 'observação', log, fallback_polo_passivo=True, qtd_seta_override=qtd_informado, debug=debug, qtd_cliques_fallback=qtd_cliques_fallback)
        except Exception as e:
            log(f'[DESTINATARIOS][ERRO] Falha no modo informado: {e}')
            return ResultadoExecucao(sucesso=False, status='error', erro=str(e), detalhes={'count': 0})

    if destinatarios == 'polo_ativo':
        log('[DESTINATARIOS] OPÇÃO: Clicando no polo ativo')
        try:
            click_headless_safe(
                driver,
                'i.fa.fa-user.pec-polo-ativo-partes-processo.pec-botao-intimar-polo-partes-processo',
                by=By.CSS_SELECTOR
            )
            return ResultadoExecucao(sucesso=True, status='geral', detalhes={'count': 0})
        except Exception as e:
            log(f'[DESTINATARIOS][ERRO] Falha ao clicar polo ativo: {e}')
            return ResultadoExecucao(sucesso=False, status='error', erro=str(e), detalhes={'count': 0})

    if destinatarios in ('polo_passivo', 'polo_passivo_2x'):
        cliques = cliques_polo_passivo if destinatarios == 'polo_passivo' else 2
        log(f'[DESTINATARIOS] Clicando no polo passivo ({cliques}x)')
        try:
            btn_polo_passivo = wait_for_clickable(driver, 'button[name="btnIntimarSomentePoloPassivo"]', timeout=10, by=By.CSS_SELECTOR)
            if not btn_polo_passivo:
                raise RuntimeError('Botão polo passivo não clicável')
            for i in range(cliques):
                safe_click_no_scroll(driver, btn_polo_passivo, log=False)
                if i < cliques - 1:
                    esperar_elemento(driver, 'button[name="btnIntimarSomentePoloPassivo"]', timeout=3, by=By.CSS_SELECTOR)
            return ResultadoExecucao(sucesso=True, status='geral', detalhes={'count': 0})
        except Exception as e:
            log(f'[DESTINATARIOS][ERRO] Falha ao clicar polo passivo: {e}')
            return ResultadoExecucao(sucesso=False, status='error', erro=str(e), detalhes={'count': 0})

    if destinatarios == 'terceiros':
        log('[DESTINATARIOS] OPÇÃO TERCEIROS: Clicando em terceiros interessados')
        try:
            try:
                btn_terceiro = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[name="btnIntimarSomenteTerceirosInteressados"]'))
                )
            except Exception:
                btn_terceiro = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, 'i.fa.fa-user.pec-polo-outros-partes-processo'))
                )
            driver.execute_script("arguments[0].click();", btn_terceiro)
            return ResultadoExecucao(sucesso=True, status='geral', detalhes={'count': 0})
        except Exception as e:
            log(f'[DESTINATARIOS][ERRO] Falha ao selecionar terceiros: {e}')
            return ResultadoExecucao(sucesso=False, status='error', erro=str(e), detalhes={'count': 0})

    if destinatarios == 'primeiro':
        log('[DESTINATARIOS] OPCAO PRIMEIRO: primeiro do Polo Passivo')
        try:
            click_headless_safe(driver, '//mat-expansion-panel-header[.//div[contains(@class,"pec-titulo-painel-expansivel-partes-processo") and contains(normalize-space(.), "Polo Passivo")]]', by=By.XPATH)
            aguardar_renderizacao_nativa(driver, '.pec-partes-polo li.partes-corpo, ul.sem-padding li.partes-corpo, mat-row', modo='aparecer', timeout=5)
            click_headless_safe(driver, '//mat-expansion-panel[.//*[contains(text(), "Polo Passivo")]]//button[@aria-label="Clique para acrescentar esta parte à lista de destinatários de expedientes e comunicações."][1]', by=By.XPATH)
            log('[DESTINATARIOS] Primeira seta clicada')

            if _selecionar_endereco_tribunal(driver, log, debug=debug):
                log('[DESTINATARIOS] Endereço do tribunal verificado/ajustado')
            else:
                log('[DESTINATARIOS] Endereço do tribunal não foi ajustado ou não estava disponível')

            return ResultadoExecucao(sucesso=True, status='ok', detalhes={'count': 1})
        except Exception as e:
            log(f'[DESTINATARIOS][ERRO] Falha no modo primeiro: {e}')
            return ResultadoExecucao(sucesso=False, status='error', erro=str(e), detalhes={'count': 0})
    # opção padrão: clicar polo passivo 1x
    log('[DESTINATARIOS] OPÇÃO PADRÃO: Clicando no polo passivo (1x)')
    try:
        btn_polo_passivo = wait_for_clickable(driver, 'button[name="btnIntimarSomentePoloPassivo"]', timeout=10, by=By.CSS_SELECTOR)
        if not btn_polo_passivo:
            raise RuntimeError('Botão polo passivo não clicável')
        safe_click_no_scroll(driver, btn_polo_passivo, log=False)
        return ResultadoExecucao(sucesso=True, status='geral', detalhes={'count': 0})
    except Exception as e:
        log(f'[DESTINATARIOS][ERRO] Falha ao clicar polo passivo padrão: {e}')
        return ResultadoExecucao(sucesso=False, status='error', erro=str(e), detalhes={'count': 0})
```


### 3. `leg/atos/comunicacao_destinatarios.py` — `_selecionar_endereco_tribunal(driver, log, debug=False)`

**Range:** L179-L221 (43 linhas)
**Callers:** `leg/atos/comunicacao_destinatarios.py:selecionar_destinatarios()`
**Callees:** `esperar_elemento()`, `_incluir_tribunal_por_cep()`, `safe_click_no_scroll()`
**Relevancia:** Funcao auxiliar que encapsula a logica de endereco do tribunal (a ser portada para o codigo ativo)

```python
# leg/atos/comunicacao_destinatarios.py L179-L221
def _selecionar_endereco_tribunal(driver, log, debug=False):
    try:
        if not esperar_elemento(driver, '.pec-consulta-enderecos', timeout=5, by=By.CSS_SELECTOR):
            if debug:
                log('[DESTINATARIOS] Endereço do tribunal não solicitado após seleção do destinatário')
            return False
    except Exception as e:
        if debug:
            log(f'[DESTINATARIOS][WARN] Falha ao detectar painel de endereços: {e}')
        return False

    try:
        if esperar_elemento(driver, "//*[contains(text(), 'Nenhum resultado encontrado')]", timeout=3, by=By.XPATH):
            log('[DESTINATARIOS] 3b. Nenhum resultado encontrado -> incluir tribunal via CEP')
            return _incluir_tribunal_por_cep(driver, log, debug=debug)
    except Exception:
        pass

    try:
        linhas_tribunal = driver.find_elements(By.XPATH,
            "//td[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'tribunal')]")
        for linha in linhas_tribunal:
            try:
                linha_tr = linha.find_element(By.XPATH, './ancestor::tr')
                seta = linha_tr.find_element(By.CSS_SELECTOR, 'button[aria-label="Selecionar endereço"]')
                if seta:
                    driver.execute_script('arguments[0].scrollIntoView({block: "center"});', seta)
                    safe_click_no_scroll(driver, seta, log=False)
                    log('[DESTINATARIOS] ✓ Endereço do tribunal selecionado')
                    btn_fechar = wait_for_clickable(driver, 'i.fa.fa-window-close.btn-fechar', timeout=10, by=By.CSS_SELECTOR)
                    if btn_fechar:
                        safe_click_no_scroll(driver, btn_fechar, log=False)
                    time.sleep(0.5)
                    return True
            except Exception:
                continue
    except Exception:
        pass

    log('[DESTINATARIOS] 3c. Nenhum endereço do tribunal encontrado na tabela - incluindo tribunal via CEP')
    return _incluir_tribunal_por_cep(driver, log, debug=debug)


```


### 4. `leg/atos/comunicacao_destinatarios.py` — `_incluir_tribunal_por_cep(driver, log, debug=False)`

**Range:** L143-L178 (36 linhas)
**Callers:** `leg/atos/comunicacao_destinatarios.py:_selecionar_endereco_tribunal()`
**Callees:** `wait_for_clickable()`, `safe_click_no_scroll()`
**Relevancia:** Implementa o fluxo CEP 01302906 -> TRT2 Sao Paulo (a ser portada para o codigo ativo)

```python
# leg/atos/comunicacao_destinatarios.py L143-L178
def _incluir_tribunal_por_cep(driver, log, debug=False):
    try:
        campo_cep = wait_for_clickable(driver, 'input#inputCep', timeout=10, by=By.CSS_SELECTOR)
        if not campo_cep:
            raise RuntimeError('Campo CEP não encontrado')
        campo_cep.clear()
        for char in '01302906':
            campo_cep.send_keys(char)
            time.sleep(0.1)
        time.sleep(1)

        opcao_tribunal = wait_for_clickable(
            driver,
            "//span[@class='mat-option-text' and contains(text(), '01302-906')]",
            timeout=10,
            by=By.XPATH
        )
        if not opcao_tribunal:
            raise RuntimeError('Opção tribunal não encontrada')
        safe_click_no_scroll(driver, opcao_tribunal, log=False)

        btn_salvar_alteracoes = wait_for_clickable(driver, 'button[aria-label="Salva as alterações"]', timeout=10, by=By.CSS_SELECTOR)
        if btn_salvar_alteracoes:
            safe_click_no_scroll(driver, btn_salvar_alteracoes, log=False)

        btn_fechar = wait_for_clickable(driver, 'i.fa.fa-window-close.btn-fechar', timeout=10, by=By.CSS_SELECTOR)
        if btn_fechar:
            safe_click_no_scroll(driver, btn_fechar, log=False)
        time.sleep(0.5)
        return True
    except Exception as e:
        if debug:
            log(f'[DESTINATARIOS][WARN] Falha ao incluir tribunal via CEP: {e}')
        return False


```


### 5. `Fix/browser_suporte.py` — `safe_click_no_scroll(driver, element, log=False)`

**Range:** L511-L523 (13 linhas)
**Callers:** `atos/comunicacao_destinatarios.py:selecionar_destinatarios()`
**Callees:** `driver.execute_script()`
**Relevancia:** Mecanismo de clique usado no codigo atual — dispatchEvent(MouseEvent) em vez de .click() nativo

```python
# Fix/browser_suporte.py L511-L523
def safe_click_no_scroll(driver, element, log=False):
    """Click without scroll"""
    try:
        driver.execute_script("arguments[0].dispatchEvent(new MouseEvent('click', {view: window, bubbles: true, cancelable: true}))", element)
        return True
    except Exception:
        return False


# ============================================================
# Public API
# ============================================================

```


### 6. `Fix/browser_suporte.py` — `click_headless_safe(driver: WebDriver, selector: str, by: By = By.CSS_SELECTOR, ...)`

**Range:** L388-L446 (59 linhas)
**Callers:** `leg/atos/comunicacao_destinatarios.py:selecionar_destinatarios()`
**Callees:** `espera.ate_habilitar()`, `element.click()`, `safe_click_no_scroll()`
**Relevancia:** Mecanismo de clique alternativo com 3 estrategias — estrategia 1 usa element.click() nativo (Selenium)

```python
# Fix/browser_suporte.py L388-L446
def click_headless_safe(driver: WebDriver, selector: str, by: By = By.CSS_SELECTOR, timeout: int = 10) -> bool:
    """
    Click ultra-seguro para modo headless com 3 estrategias progressivas.

    Estrategia 1: Wait padrao + click normal
    Estrategia 2: Limpar overlays + scroll + wait + click
    Estrategia 3: JavaScript click direto (ultimo recurso)

    Compensacao especifica do caminho Selenium headless (geckodriver renderiza
    por caminho diferente do headed). Sob o backend Playwright vira no-op
    efetivo: `locator.click()` faz a mesma checagem de actionability em
    headless e headed — ja substituida por `pjeplay/nativo.py`.

    Args:
        driver: WebDriver instance
        selector: Seletor CSS ou XPath
        by: Tipo de seletor (padrao CSS_SELECTOR)
        timeout: Timeout em segundos

    Returns:
        bool: True se click foi bem-sucedido
    """

    # Estrategia 1: Wait padrao element_to_be_clickable
    try:
        if not espera.ate_habilitar(driver, selector, teto=timeout):
            raise TimeoutException(f"element_to_be_clickable: {selector}")
        element = driver.find_element(by, selector)
        element.click()
        return True
    except (ElementClickInterceptedException, TimeoutException):
        pass

    # Estrategia 2: Limpar overlays + scroll + wait + click
    try:
        limpar_overlays_headless(driver)
        element = espera.elemento(driver, selector, teto=timeout // 2, visivel=False)
        if element is None:
            raise TimeoutException(f"presence_of_element_located: {selector}")
        scroll_to_element_safe(driver, element)
        # Aguarda elemento estar clicavel apos scroll (DOM-settle)
        if not espera.ate_habilitar(driver, selector, teto=timeout // 2):
            raise TimeoutException(f"element_to_be_clickable: {selector}")
        driver.find_element(by, selector).click()
        return True
    except (ElementClickInterceptedException, StaleElementReferenceException):
        pass

    # Estrategia 3: JavaScript click (fallback final)
    try:
        element = driver.find_element(by, selector)
        safe_click_no_scroll(driver, element)
        espera.ate_js(driver, "document.readyState === 'complete' || document.readyState === 'interactive'", teto=2.0)  # DOM-settle apos click JS
        return True
    except Exception as e:
        logger.error(f"[HEADLESS] Todas estrategias falharam para '{selector}': {e}")
        return False


```


### 7. `atos/comunicacao.py` — `make_comunicacao_wrapper()`

**Range:** L88-L110 (23 linhas)
**Callers:** `atos/wrappers_pec.py:pec_excluiargos`
**Callees:** `selecionar_destinatarios()`
**Relevancia:** Factory que cria pec_excluiargos com destinatarios='primeiro' — ponto de configuracao do fluxo

```python
# atos/comunicacao.py L88-L110
def make_comunicacao_wrapper(
    tipo_expediente: str, 
    prazo: int, 
    nome_comunicacao: str, 
    sigilo: str, 
    modelo_nome: str, 
    subtipo: Optional[str] = None, 
    descricao: Optional[str] = None,
    tipo_prazo: str = 'dias uteis',
    gigs_extra: Optional[Union[bool, Tuple, List, Any]] = None,
    coleta_conteudo: Optional[Callable] = None,
    inserir_conteudo: Optional[Callable] = None,
    cliques_polo_passivo: int = 1,
    cliques_informado: int = 2,
    destinatarios: str = 'extraido',
    mudar_expediente: Optional[bool] = None,
    checar_sp: Optional[bool] = None,
    endereco_tipo: Optional[str] = None,
    trocar_modelo: bool = False,
    wrapper_name: Optional[str] = None,  # Nome específico para __name__
    terceiro_default: bool = False,
    assinar: bool = False,
    modelo_troca_correios: Optional[str] = None
```


## 6. Ambiente

- **Navegador:** Firefox
- **Headless:** sim (produção)
- **Log relevante:** `[DESTINATARIOS] OPCAO PRIMEIRO: primeiro do Polo Passivo (pec_excluiargos)` aparece, mas o fluxo falha silenciosamente no clique do header ou da seta

---

*Artefato gerado pelo Xcode Agent. Autossuficiente — não requer acesso ao código.*
**Relevancia:** Ponto de entrada — contém o bloco 'primeiro' com a falha (L484-636)

```python
# atos/comunicacao_destinatarios.py L392-L647
def selecionar_destinatarios(driver, destinatarios, terceiro=False, debug=False, log=None, cliques_polo_passivo=1, cliques_informado=2, observacao=None, numero_processo=None, dados_processo=None):
    from core.resultado_execucao import ResultadoExecucao
    if log is None:
        def log(_msg):
            return None

    qtd_seta = 2 if str(cliques_polo_passivo).strip().lower() in ('2', '2x') else 1
    qtd_informado = 2 if str(cliques_informado).strip().lower() in ('2', '2x') else 1
    qtd_cliques_fallback = 2 if str(cliques_polo_passivo).strip().lower() in ('2', '2x') else 1

    # Roteamento principal
    if destinatarios is None:
        log('[DESTINATARIOS] Parâmetro None - pulando seleção')
        return ResultadoExecucao(sucesso=False, status='skip', detalhes={'count': 0})

    if isinstance(destinatarios, list):
        log('[DESTINATARIOS] Lista explícita recebida via override')
        return _selecionar_por_lista(driver, destinatarios, 'lista explícita', log, fallback_polo_passivo=True, qtd_seta_override=None, debug=debug, qtd_cliques_fallback=qtd_cliques_fallback)

    if destinatarios == 'extraido':
        log('[DESTINATARIOS] OPÇÃO EXTRAIDO: carregando destinatários em cache')
        try:
            from Fix.extracao_processo import carregar_destinatarios_cache
            cache = carregar_destinatarios_cache() or {}
            lista_destinatarios = cache.get('destinatarios', []) or []
            return _selecionar_por_lista(driver, lista_destinatarios, 'cache', log, fallback_polo_passivo=True, qtd_seta_override=2, debug=debug, qtd_cliques_fallback=qtd_cliques_fallback)
        except Exception as e:
            log(f'[DESTINATARIOS][ERRO] Falha no modo extraido: {e}')
            return ResultadoExecucao(sucesso=False, status='error', erro=str(e), detalhes={'count': 0})

    if destinatarios == 'informado':
        log('[DESTINATARIOS] OPÇÃO INFORMADO: cruzando observação com dados do processo')
        try:
            if not dados_processo:
                try:
                    from Fix.extracao_processo import extrair_dados_processo
                    dados_processo = extrair_dados_processo(driver, caminho_json='dadosatuais.json', debug=debug)
                except Exception:
                    dados_processo = _carregar_dadosatuais_local('dadosatuais.json')

            candidatos = _montar_destinatarios_por_observacao(observacao, dados_processo, debug=debug)
            return _selecionar_por_lista(driver, candidatos, 'observação', log, fallback_polo_passivo=True, qtd_seta_override=qtd_informado, debug=debug, qtd_cliques_fallback=qtd_cliques_fallback)
        except Exception as e:
            log(f'[DESTINATARIOS][ERRO] Falha no modo informado: {e}')
            return ResultadoExecucao(sucesso=False, status='error', erro=str(e), detalhes={'count': 0})

    if destinatarios == 'polo_ativo':
        log('[DESTINATARIOS] OPÇÃO: Clicando no polo ativo')
        try:
            btn = wait_for_clickable(driver, 'button[name="btnIntimarSomentePoloAtivo"]', timeout=10, by=By.CSS_SELECTOR)
            if not btn:
                raise RuntimeError('Botão polo ativo não clicável')
            _clicar_e_aguardar_spinner(driver, btn)
            return ResultadoExecucao(sucesso=True, status='geral', detalhes={'count': 0})
        except Exception as e:
            log(f'[DESTINATARIOS][ERRO] Falha ao clicar polo ativo: {e}')
            return ResultadoExecucao(sucesso=False, status='error', erro=str(e), detalhes={'count': 0})

    if destinatarios in ('polo_passivo', 'polo_passivo_2x'):
        cliques = cliques_polo_passivo if destinatarios == 'polo_passivo' else 2
        log(f'[DESTINATARIOS] Clicando no polo passivo ({cliques}x)')
        try:
            btn_polo_passivo = wait_for_clickable(driver, 'button[name="btnIntimarSomentePoloPassivo"]', timeout=5, by=By.CSS_SELECTOR)
            if not btn_polo_passivo:
                raise RuntimeError('Botão polo passivo não clicável')
            for i in range(cliques):
                _clicar_e_aguardar_spinner(driver, btn_polo_passivo)
                if i < cliques - 1:
                    # Spinner já sumiu (garantido por _clicar_e_aguardar_spinner) — apenas
                    # reobter a referência (Angular pode recriar o nó), sem novo timeout de espera.
                    btn_polo_passivo = driver.find_element(By.CSS_SELECTOR, 'button[name="btnIntimarSomentePoloPassivo"]')
            return ResultadoExecucao(sucesso=True, status='geral', detalhes={'count': 0})
        except Exception as e:
            log(f'[DESTINATARIOS][ERRO] Falha ao clicar polo passivo: {e}')
            return ResultadoExecucao(sucesso=False, status='error', erro=str(e), detalhes={'count': 0})

    if destinatarios == 'terceiros':
        log('[DESTINATARIOS] OPÇÃO TERCEIROS: Clicando em terceiros interessados')
        try:
            if espera.ate_habilitar(driver, 'button[name="btnIntimarSomenteTerceirosInteressados"]', teto=5):
                btn_terceiro = driver.find_element(By.CSS_SELECTOR, 'button[name="btnIntimarSomenteTerceirosInteressados"]')
            else:
                # <i> não tem estado disabled real: ate_aparecer, não ate_habilitar
                espera.ate_aparecer(driver, 'i.fa.fa-user.pec-polo-outros-partes-processo', teto=5)
                btn_terceiro = driver.find_element(By.CSS_SELECTOR, 'i.fa.fa-user.pec-polo-outros-partes-processo')
            _clicar_e_aguardar_spinner(driver, btn_terceiro)
            return ResultadoExecucao(sucesso=True, status='geral', detalhes={'count': 0})
        except Exception as e:
            log(f'[DESTINATARIOS][ERRO] Falha ao selecionar terceiros: {e}')
            return ResultadoExecucao(sucesso=False, status='error', erro=str(e), detalhes={'count': 0})

    if destinatarios == 'primeiro':
        log('[DESTINATARIOS] OPCAO PRIMEIRO: primeiro do Polo Passivo (pec_excluiargos)')
        try:
            # 1. Expandir painel Polo Passivo (legado: WebDriverWait + execute_script)
            painel_header_xpath = (
                '//mat-expansion-panel-header[.//div[contains(@class,"pec-titulo-painel-expansivel-partes-processo")'
                ' and contains(normalize-space(.), "Polo Passivo")]]'
            )
            painel_header = espera.elemento(driver, painel_header_xpath, teto=10, visivel=False)
            if painel_header is None:
                raise Exception('painel Polo Passivo não apareceu')
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", painel_header)
            safe_click_no_scroll(driver, painel_header)
            espera.assentar(driver, 0.5)

            # 2. Clicar na primeira seta do Polo Passivo (legado: WebDriverWait + execute_script)
            seta_xpath = (
                '//mat-expansion-panel[.//*[contains(text(), "Polo Passivo")]]'
                '//button[@aria-label="Clique para acrescentar esta parte '
                'à lista de destinatários de expedientes e comunicações."][1]'
            )
            if not espera.ate_habilitar(driver, seta_xpath, teto=10):
                raise Exception('primeira seta do Polo Passivo não habilitou')
            primeira_seta = driver.find_element(By.XPATH, seta_xpath)
            safe_click_no_scroll(driver, primeira_seta)
            log('[DESTINATARIOS] Primeira seta (primeiro destinatário) clicada')
            espera.assentar(driver, 1)

            # 3. Buscar e adicionar TRIBUNAL se necessário (pec_excluiargos)
            try:
                log('[DESTINATARIOS] 3. Buscando tribunal nos endereços disponíveis...')

                # Verificar se formulário de consulta de endereços apareceu
                try:
                    WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, '.pec-consulta-enderecos'))
                    )
                    log('[DESTINATARIOS] 3a. Formulário de consulta de endereços detectado')
                except Exception:
                    log('[DESTINATARIOS] 3a. Formulário de consulta de endereços não apareceu')
                    raise Exception('Consulta não apareceu')

                # Verificar se há snack-bar de "Nenhum resultado encontrado"
                try:
                    WebDriverWait(driver, 3).until(
                        EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Nenhum resultado encontrado')]"))
                    )
                    log('[DESTINATARIOS] 3b. Snack-bar detectado: "Nenhum resultado encontrado" -> incluir tribunal via CEP')

                    # Digitar CEP 01302906 no campo inputCep
                    log('[DESTINATARIOS] 3c. Digitando CEP 01302906 no campo inputCep')
                    campo_cep = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, 'input#inputCep'))
                    )
                    campo_cep.clear()
                    for char in '01302906':
                        campo_cep.send_keys(char)
                        espera.assentar(driver, 0.1)
                    espera.ate_texto(driver, 'span.mat-option-text', '01302-906', teto=1)

                    log('[DESTINATARIOS] 3d. Clicando na opção do tribunal TRT2 São Paulo')
                    opcao_tribunal = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, "//span[@class='mat-option-text' and contains(text(), '01302-906')]"))
                    )
                    opcao_tribunal.click()
                    log('[DESTINATARIOS] Opção do tribunal selecionada')
                    espera.ate_habilitar(driver, 'button[aria-label="Salva as alterações"]', teto=0.5)

                    log('[DESTINATARIOS] 3e. Clicando no botão Salvar das alterações')
                    btn_salvar_alteracoes = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[aria-label="Salva as alterações"]'))
                    )
                    btn_salvar_alteracoes.click()
                    log('[DESTINATARIOS] Alterações salvas')
                    espera.ate_aparecer(driver, 'i.fa.fa-window-close.btn-fechar', teto=0.5)

                    log('[DESTINATARIOS] 3f. Clicando no botão fechar para fechar endereços')
                    btn_fechar = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, 'i.fa.fa-window-close.btn-fechar'))
                    )
                    btn_fechar.click()
                    log('[DESTINATARIOS] Janela de endereços fechada')
                except Exception:
                    # Se não houver snack-bar, procurar tribunal nas linhas da tabela
                    log('[DESTINATARIOS] 3b. Nenhum snack-bar - buscando tribunal na tabela de endereços')
                    try:
                        WebDriverWait(driver, 5).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, 'table[name="Endereços do destinatário no sistema"]'))
                        )

                        # Procura por linhas que contenham "TRIBUNAL" (case insensitive)
                        linhas_tribunal = driver.find_elements(
                            By.XPATH,
                            "//td[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'tribunal')]"
                        )

                        if linhas_tribunal:
                            log('[DESTINATARIOS] 3c. Encontrado endereço do tribunal, clicando na seta')
                            linha_tribunal = linhas_tribunal[0].find_element(By.XPATH, './ancestor::tr')
                            seta_tribunal = linha_tribunal.find_element(By.CSS_SELECTOR, 'button[aria-label="Selecionar endereço"]')
                            seta_tribunal.click()
                            log('[DESTINATARIOS] Endereço do tribunal selecionado')
                            time.sleep(0.5)

                            log('[DESTINATARIOS] 3d. Clicando no botão fechar para fechar endereços')
                            btn_fechar = WebDriverWait(driver, 10).until(
                                EC.element_to_be_clickable((By.CSS_SELECTOR, 'i.fa.fa-window-close.btn-fechar'))
                            )
                            btn_fechar.click()
                            log('[DESTINATARIOS] Janela de endereços fechada')
                        else:
                            log('[DESTINATARIOS] 3c. Nenhum endereço do tribunal encontrado na tabela - incluindo tribunal via CEP')

                            log('[DESTINATARIOS] 3d. Digitando CEP 01302906 no campo inputCep')
                            campo_cep = WebDriverWait(driver, 10).until(
                                EC.element_to_be_clickable((By.CSS_SELECTOR, 'input#inputCep'))
                            )
                            campo_cep.clear()
                            for char in '01302906':
                                campo_cep.send_keys(char)
                                time.sleep(0.1)
                            time.sleep(1)

                            log('[DESTINATARIOS] 3e. Clicando na opção do tribunal TRT2')
                            opcao_tribunal = WebDriverWait(driver, 10).until(
                                EC.element_to_be_clickable((By.XPATH, "//span[@class='mat-option-text' and contains(text(), '01302-906')]"))
                            )
                            opcao_tribunal.click()
                            log('[DESTINATARIOS] Tribunal selecionado')
                            time.sleep(0.5)

                            log('[DESTINATARIOS] 3f. Clicando em Salvar alterações')
                            btn_salvar_alteracoes = WebDriverWait(driver, 10).until(
                                EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[aria-label="Salva as alterações"]'))
                            )
                            btn_salvar_alteracoes.click()
                            log('[DESTINATARIOS] Alterações salvas')
                            time.sleep(0.5)

                            log('[DESTINATARIOS] 3g. Fechando janela de endereços')
                            btn_fechar = WebDriverWait(driver, 10).until(
                                EC.element_to_be_clickable((By.CSS_SELECTOR, 'i.fa.fa-window-close.btn-fechar'))
                            )
                            btn_fechar.click()
                            log('[DESTINATARIOS] Janela fechada')
                    except Exception as e_tabela:
                        log(f'[DESTINATARIOS] Erro ao processar endereços: {e_tabela}')
            except Exception as tribunal_err:
                log(f'[DESTINATARIOS] Aviso: Não foi possível adicionar tribunal: {tribunal_err}')

            return ResultadoExecucao(sucesso=True, status='ok', detalhes={'count': 1})
        except Exception as e:
            log(f'[DESTINATARIOS][ERRO] Falha ao selecionar primeiro destinatário: {e}')
            return ResultadoExecucao(sucesso=False, status='error', erro=str(e), detalhes={'count': 0})
    # opção padrão: clicar polo passivo 1x
    log('[DESTINATARIOS] OPÇÃO PADRÃO: Clicando no polo passivo (1x)')
    try:
        btn_polo_passivo = wait_for_clickable(driver, 'button[name="btnIntimarSomentePoloPassivo"]', timeout=10, by=By.CSS_SELECTOR)
        if not btn_polo_passivo:
            raise RuntimeError('Botão polo passivo não clicável')
        _clicar_e_aguardar_spinner(driver, btn_polo_passivo)
        return ResultadoExecucao(sucesso=True, status='geral', detalhes={'count': 0})
    except Exception as e:
        log(f'[DESTINATARIOS][ERRO] Falha ao clicar polo passivo padrão: {e}')
        return ResultadoExecucao(sucesso=False, status='error', erro=str(e), detalhes={'count': 0})
```


### 2. `leg/atos/comunicacao_destinatarios.py` — `selecionar_destinatarios(driver, destinatarios, terceiro=False, ...)`

**Range:** L451-L570 (120 linhas)
**Callers:** `atos/comunicacao.py:make_comunicacao_wrapper()`
**Callees:** `click_headless_safe()`, `aguardar_renderizacao_nativa()`, `_selecionar_endereco_tribunal()`
**Relevancia:** Versão funcional de referência no leg/ — bloco 'primeiro' simplificado (L548-563)

```python
# leg/atos/comunicacao_destinatarios.py L451-L570
def selecionar_destinatarios(driver, destinatarios, terceiro=False, debug=False, log=None, cliques_polo_passivo=1, cliques_informado=2, observacao=None, numero_processo=None, dados_processo=None):
    from core.resultado_execucao import ResultadoExecucao
    if log is None:
        def log(_msg):
            return None

    qtd_seta = 2 if str(cliques_polo_passivo).strip().lower() in ('2', '2x') else 1
    qtd_informado = 2 if str(cliques_informado).strip().lower() in ('2', '2x') else 1
    qtd_cliques_fallback = 2 if str(cliques_polo_passivo).strip().lower() in ('2', '2x') else 1

    # Roteamento principal
    if destinatarios is None:
        log('[DESTINATARIOS] Parâmetro None - pulando seleção')
        return ResultadoExecucao(sucesso=False, status='skip', detalhes={'count': 0})

    if isinstance(destinatarios, list):
        log('[DESTINATARIOS] Lista explícita recebida via override')
        return _selecionar_por_lista(driver, destinatarios, 'lista explícita', log, fallback_polo_passivo=True, qtd_seta_override=None, debug=debug, qtd_cliques_fallback=qtd_cliques_fallback)

    if destinatarios == 'extraido':
        log('[DESTINATARIOS] OPÇÃO EXTRAIDO: carregando destinatários em cache')
        try:
            from Fix.extracao_processo import carregar_destinatarios_cache
            cache = carregar_destinatarios_cache() or {}
            lista_destinatarios = cache.get('destinatarios', []) or []
            return _selecionar_por_lista(driver, lista_destinatarios, 'cache', log, fallback_polo_passivo=True, qtd_seta_override=2, debug=debug, qtd_cliques_fallback=qtd_cliques_fallback)
        except Exception as e:
            log(f'[DESTINATARIOS][ERRO] Falha no modo extraido: {e}')
            return ResultadoExecucao(sucesso=False, status='error', erro=str(e), detalhes={'count': 0})

    if destinatarios == 'informado':
        log('[DESTINATARIOS] OPÇÃO INFORMADO: cruzando observação com dados do processo')
        try:
            if not dados_processo:
                try:
                    from Fix.extracao_processo import extrair_dados_processo
                    dados_processo = extrair_dados_processo(driver, caminho_json='dadosatuais.json', debug=debug)
                except Exception:
                    dados_processo = _carregar_dadosatuais_local('dadosatuais.json')

            candidatos = _montar_destinatarios_por_observacao(observacao, dados_processo, debug=debug)
            return _selecionar_por_lista(driver, candidatos, 'observação', log, fallback_polo_passivo=True, qtd_seta_override=qtd_informado, debug=debug, qtd_cliques_fallback=qtd_cliques_fallback)
        except Exception as e:
            log(f'[DESTINATARIOS][ERRO] Falha no modo informado: {e}')
            return ResultadoExecucao(sucesso=False, status='error', erro=str(e), detalhes={'count': 0})

    if destinatarios == 'polo_ativo':
        log('[DESTINATARIOS] OPÇÃO: Clicando no polo ativo')
        try:
            click_headless_safe(
                driver,
                'i.fa.fa-user.pec-polo-ativo-partes-processo.pec-botao-intimar-polo-partes-processo',
                by=By.CSS_SELECTOR
            )
            return ResultadoExecucao(sucesso=True, status='geral', detalhes={'count': 0})
        except Exception as e:
            log(f'[DESTINATARIOS][ERRO] Falha ao clicar polo ativo: {e}')
            return ResultadoExecucao(sucesso=False, status='error', erro=str(e), detalhes={'count': 0})

    if destinatarios in ('polo_passivo', 'polo_passivo_2x'):
        cliques = cliques_polo_passivo if destinatarios == 'polo_passivo' else 2
        log(f'[DESTINATARIOS] Clicando no polo passivo ({cliques}x)')
        try:
            btn_polo_passivo = wait_for_clickable(driver, 'button[name="btnIntimarSomentePoloPassivo"]', timeout=10, by=By.CSS_SELECTOR)
            if not btn_polo_passivo:
                raise RuntimeError('Botão polo passivo não clicável')
            for i in range(cliques):
                safe_click_no_scroll(driver, btn_polo_passivo, log=False)
                if i < cliques - 1:
                    esperar_elemento(driver, 'button[name="btnIntimarSomentePoloPassivo"]', timeout=3, by=By.CSS_SELECTOR)
            return ResultadoExecucao(sucesso=True, status='geral', detalhes={'count': 0})
        except Exception as e:
            log(f'[DESTINATARIOS][ERRO] Falha ao clicar polo passivo: {e}')
            return ResultadoExecucao(sucesso=False, status='error', erro=str(e), detalhes={'count': 0})

    if destinatarios == 'terceiros':
        log('[DESTINATARIOS] OPÇÃO TERCEIROS: Clicando em terceiros interessados')
        try:
            try:
                btn_terceiro = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[name="btnIntimarSomenteTerceirosInteressados"]'))
                )
            except Exception:
                btn_terceiro = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, 'i.fa.fa-user.pec-polo-outros-partes-processo'))
                )
            driver.execute_script("arguments[0].click();", btn_terceiro)
            return ResultadoExecucao(sucesso=True, status='geral', detalhes={'count': 0})
        except Exception as e:
            log(f'[DESTINATARIOS][ERRO] Falha ao selecionar terceiros: {e}')
            return ResultadoExecucao(sucesso=False, status='error', erro=str(e), detalhes={'count': 0})

    if destinatarios == 'primeiro':
        log('[DESTINATARIOS] OPCAO PRIMEIRO: primeiro do Polo Passivo')
        try:
            click_headless_safe(driver, '//mat-expansion-panel-header[.//div[contains(@class,"pec-titulo-painel-expansivel-partes-processo") and contains(normalize-space(.), "Polo Passivo")]]', by=By.XPATH)
            aguardar_renderizacao_nativa(driver, '.pec-partes-polo li.partes-corpo, ul.sem-padding li.partes-corpo, mat-row', modo='aparecer', timeout=5)
            click_headless_safe(driver, '//mat-expansion-panel[.//*[contains(text(), "Polo Passivo")]]//button[@aria-label="Clique para acrescentar esta parte à lista de destinatários de expedientes e comunicações."][1]', by=By.XPATH)
            log('[DESTINATARIOS] Primeira seta clicada')

            if _selecionar_endereco_tribunal(driver, log, debug=debug):
                log('[DESTINATARIOS] Endereço do tribunal verificado/ajustado')
            else:
                log('[DESTINATARIOS] Endereço do tribunal não foi ajustado ou não estava disponível')

            return ResultadoExecucao(sucesso=True, status='ok', detalhes={'count': 1})
        except Exception as e:
            log(f'[DESTINATARIOS][ERRO] Falha no modo primeiro: {e}')
            return ResultadoExecucao(sucesso=False, status='error', erro=str(e), detalhes={'count': 0})
    # opção padrão: clicar polo passivo 1x
    log('[DESTINATARIOS] OPÇÃO PADRÃO: Clicando no polo passivo (1x)')
    try:
        btn_polo_passivo = wait_for_clickable(driver, 'button[name="btnIntimarSomentePoloPassivo"]', timeout=10, by=By.CSS_SELECTOR)
        if not btn_polo_passivo:
            raise RuntimeError('Botão polo passivo não clicável')
        safe_click_no_scroll(driver, btn_polo_passivo, log=False)
        return ResultadoExecucao(sucesso=True, status='geral', detalhes={'count': 0})
    except Exception as e:
        log(f'[DESTINATARIOS][ERRO] Falha ao clicar polo passivo padrão: {e}')
        return ResultadoExecucao(sucesso=False, status='error', erro=str(e), detalhes={'count': 0})
```


### 3. `leg/atos/comunicacao_destinatarios.py` — `_selecionar_endereco_tribunal(driver, log, debug=False)`

**Range:** L179-L221 (43 linhas)
**Callers:** `leg/atos/comunicacao_destinatarios.py:selecionar_destinatarios()`
**Callees:** `esperar_elemento()`, `_incluir_tribunal_por_cep()`, `safe_click_no_scroll()`
**Relevancia:** Função auxiliar que encapsula a lógica de endereço do tribunal (a ser portada para o código ativo)

```python
# leg/atos/comunicacao_destinatarios.py L179-L221
def _selecionar_endereco_tribunal(driver, log, debug=False):
    try:
        if not esperar_elemento(driver, '.pec-consulta-enderecos', timeout=5, by=By.CSS_SELECTOR):
            if debug:
                log('[DESTINATARIOS] Endereço do tribunal não solicitado após seleção do destinatário')
            return False
    except Exception as e:
        if debug:
            log(f'[DESTINATARIOS][WARN] Falha ao detectar painel de endereços: {e}')
        return False

    try:
        if esperar_elemento(driver, "//*[contains(text(), 'Nenhum resultado encontrado')]", timeout=3, by=By.XPATH):
            log('[DESTINATARIOS] 3b. Nenhum resultado encontrado -> incluir tribunal via CEP')
            return _incluir_tribunal_por_cep(driver, log, debug=debug)
    except Exception:
        pass

    try:
        linhas_tribunal = driver.find_elements(By.XPATH,
            "//td[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'tribunal')]")
        for linha in linhas_tribunal:
            try:
                linha_tr = linha.find_element(By.XPATH, './ancestor::tr')
                seta = linha_tr.find_element(By.CSS_SELECTOR, 'button[aria-label="Selecionar endereço"]')
                if seta:
                    driver.execute_script('arguments[0].scrollIntoView({block: "center"});', seta)
                    safe_click_no_scroll(driver, seta, log=False)
                    log('[DESTINATARIOS] ✓ Endereço do tribunal selecionado')
                    btn_fechar = wait_for_clickable(driver, 'i.fa.fa-window-close.btn-fechar', timeout=10, by=By.CSS_SELECTOR)
                    if btn_fechar:
                        safe_click_no_scroll(driver, btn_fechar, log=False)
                    time.sleep(0.5)
                    return True
            except Exception:
                continue
    except Exception:
        pass

    log('[DESTINATARIOS] 3c. Nenhum endereço do tribunal encontrado na tabela - incluindo tribunal via CEP')
    return _incluir_tribunal_por_cep(driver, log, debug=debug)


```


### 4. `leg/atos/comunicacao_destinatarios.py` — `_incluir_tribunal_por_cep(driver, log, debug=False)`

**Range:** L143-L178 (36 linhas)
**Callers:** `leg/atos/comunicacao_destinatarios.py:_selecionar_endereco_tribunal()`
**Callees:** `wait_for_clickable()`, `safe_click_no_scroll()`
**Relevancia:** Implementa o fluxo CEP 01302906 → TRT2 São Paulo (a ser portada para o código ativo)

```python
# leg/atos/comunicacao_destinatarios.py L143-L178
def _incluir_tribunal_por_cep(driver, log, debug=False):
    try:
        campo_cep = wait_for_clickable(driver, 'input#inputCep', timeout=10, by=By.CSS_SELECTOR)
        if not campo_cep:
            raise RuntimeError('Campo CEP não encontrado')
        campo_cep.clear()
        for char in '01302906':
            campo_cep.send_keys(char)
            time.sleep(0.1)
        time.sleep(1)

        opcao_tribunal = wait_for_clickable(
            driver,
            "//span[@class='mat-option-text' and contains(text(), '01302-906')]",
            timeout=10,
            by=By.XPATH
        )
        if not opcao_tribunal:
            raise RuntimeError('Opção tribunal não encontrada')
        safe_click_no_scroll(driver, opcao_tribunal, log=False)

        btn_salvar_alteracoes = wait_for_clickable(driver, 'button[aria-label="Salva as alterações"]', timeout=10, by=By.CSS_SELECTOR)
        if btn_salvar_alteracoes:
            safe_click_no_scroll(driver, btn_salvar_alteracoes, log=False)

        btn_fechar = wait_for_clickable(driver, 'i.fa.fa-window-close.btn-fechar', timeout=10, by=By.CSS_SELECTOR)
        if btn_fechar:
            safe_click_no_scroll(driver, btn_fechar, log=False)
        time.sleep(0.5)
        return True
    except Exception as e:
        if debug:
            log(f'[DESTINATARIOS][WARN] Falha ao incluir tribunal via CEP: {e}')
        return False


```


### 5. `Fix/browser_suporte.py` — `safe_click_no_scroll(driver, element, log=False)`

**Range:** L511-L523 (13 linhas)
**Callers:** `atos/comunicacao_destinatarios.py:selecionar_destinatarios()`
**Callees:** `driver.execute_script()`
**Relevancia:** Mecanismo de clique usado no código atual — dispatchEvent(MouseEvent) em vez de .click() nativo

```python
# Fix/browser_suporte.py L511-L523
def safe_click_no_scroll(driver, element, log=False):
    """Click without scroll"""
    try:
        driver.execute_script("arguments[0].dispatchEvent(new MouseEvent('click', {view: window, bubbles: true, cancelable: true}))", element)
        return True
    except Exception:
        return False


# ============================================================
# Public API
# ============================================================

```


### 6. `Fix/browser_suporte.py` — `click_headless_safe(driver: WebDriver, selector: str, by: By = By.CSS_SELECTOR, ...)`

**Range:** L388-L446 (59 linhas)
**Callers:** `leg/atos/comunicacao_destinatarios.py:selecionar_destinatarios()`
**Callees:** `espera.ate_habilitar()`, `element.click()`, `safe_click_no_scroll()`
**Relevancia:** Mecanismo de clique alternativo com 3 estratégias — estratégia 1 usa element.click() nativo (Selenium)

```python
# Fix/browser_suporte.py L388-L446
def click_headless_safe(driver: WebDriver, selector: str, by: By = By.CSS_SELECTOR, timeout: int = 10) -> bool:
    """
    Click ultra-seguro para modo headless com 3 estrategias progressivas.

    Estrategia 1: Wait padrao + click normal
    Estrategia 2: Limpar overlays + scroll + wait + click
    Estrategia 3: JavaScript click direto (ultimo recurso)

    Compensacao especifica do caminho Selenium headless (geckodriver renderiza
    por caminho diferente do headed). Sob o backend Playwright vira no-op
    efetivo: `locator.click()` faz a mesma checagem de actionability em
    headless e headed — ja substituida por `pjeplay/nativo.py`.

    Args:
        driver: WebDriver instance
        selector: Seletor CSS ou XPath
        by: Tipo de seletor (padrao CSS_SELECTOR)
        timeout: Timeout em segundos

    Returns:
        bool: True se click foi bem-sucedido
    """

    # Estrategia 1: Wait padrao element_to_be_clickable
    try:
        if not espera.ate_habilitar(driver, selector, teto=timeout):
            raise TimeoutException(f"element_to_be_clickable: {selector}")
        element = driver.find_element(by, selector)
        element.click()
        return True
    except (ElementClickInterceptedException, TimeoutException):
        pass

    # Estrategia 2: Limpar overlays + scroll + wait + click
    try:
        limpar_overlays_headless(driver)
        element = espera.elemento(driver, selector, teto=timeout // 2, visivel=False)
        if element is None:
            raise TimeoutException(f"presence_of_element_located: {selector}")
        scroll_to_element_safe(driver, element)
        # Aguarda elemento estar clicavel apos scroll (DOM-settle)
        if not espera.ate_habilitar(driver, selector, teto=timeout // 2):
            raise TimeoutException(f"element_to_be_clickable: {selector}")
        driver.find_element(by, selector).click()
        return True
    except (ElementClickInterceptedException, StaleElementReferenceException):
        pass

    # Estrategia 3: JavaScript click (fallback final)
    try:
        element = driver.find_element(by, selector)
        safe_click_no_scroll(driver, element)
        espera.ate_js(driver, "document.readyState === 'complete' || document.readyState === 'interactive'", teto=2.0)  # DOM-settle apos click JS
        return True
    except Exception as e:
        logger.error(f"[HEADLESS] Todas estrategias falharam para '{selector}': {e}")
        return False


```

## 5. Dump de Funcoes

### 1. `atos/comunicacao_destinatarios.py` — `selecionar_destinatarios(driver, destinatarios, terceiro=False, ...)`

**Range:** L392-L647 (256 linhas)
**Callers:** `atos/comunicacao.py:make_comunicacao_wrapper()`
**Callees:** `espera.elemento()`, `safe_click_no_scroll()`, `espera.ate_habilitar()`, `click_headless_safe()`
**Relevancia:** Ponto de entrada — contém o bloco 'primeiro' com a falha (L484-636)

```python
# atos/comunicacao_destinatarios.py L392-L647
def selecionar_destinatarios(driver, destinatarios, terceiro=False, debug=False, log=None, cliques_polo_passivo=1, cliques_informado=2, observacao=None, numero_processo=None, dados_processo=None):
    from core.resultado_execucao import ResultadoExecucao
    if log is None:
        def log(_msg):
            return None

    qtd_seta = 2 if str(cliques_polo_passivo).strip().lower() in ('2', '2x') else 1
    qtd_informado = 2 if str(cliques_informado).strip().lower() in ('2', '2x') else 1
    qtd_cliques_fallback = 2 if str(cliques_polo_passivo).strip().lower() in ('2', '2x') else 1

    # Roteamento principal
    if destinatarios is None:
        log('[DESTINATARIOS] Parâmetro None - pulando seleção')
        return ResultadoExecucao(sucesso=False, status='skip', detalhes={'count': 0})

    if isinstance(destinatarios, list):
        log('[DESTINATARIOS] Lista explícita recebida via override')
        return _selecionar_por_lista(driver, destinatarios, 'lista explícita', log, fallback_polo_passivo=True, qtd_seta_override=None, debug=debug, qtd_cliques_fallback=qtd_cliques_fallback)

    if destinatarios == 'extraido':
        log('[DESTINATARIOS] OPÇÃO EXTRAIDO: carregando destinatários em cache')
        try:
            from Fix.extracao_processo import carregar_destinatarios_cache
            cache = carregar_destinatarios_cache() or {}
            lista_destinatarios = cache.get('destinatarios', []) or []
            return _selecionar_por_lista(driver, lista_destinatarios, 'cache', log, fallback_polo_passivo=True, qtd_seta_override=2, debug=debug, qtd_cliques_fallback=qtd_cliques_fallback)
        except Exception as e:
            log(f'[DESTINATARIOS][ERRO] Falha no modo extraido: {e}')
            return ResultadoExecucao(sucesso=False, status='error', erro=str(e), detalhes={'count': 0})

    if destinatarios == 'informado':
        log('[DESTINATARIOS] OPÇÃO INFORMADO: cruzando observação com dados do processo')
        try:
            if not dados_processo:
                try:
                    from Fix.extracao_processo import extrair_dados_processo
                    dados_processo = extrair_dados_processo(driver, caminho_json='dadosatuais.json', debug=debug)
                except Exception:
                    dados_processo = _carregar_dadosatuais_local('dadosatuais.json')

            candidatos = _montar_destinatarios_por_observacao(observacao, dados_processo, debug=debug)
            return _selecionar_por_lista(driver, candidatos, 'observação', log, fallback_polo_passivo=True, qtd_seta_override=qtd_informado, debug=debug, qtd_cliques_fallback=qtd_cliques_fallback)
        except Exception as e:
            log(f'[DESTINATARIOS][ERRO] Falha no modo informado: {e}')
            return ResultadoExecucao(sucesso=False, status='error', erro=str(e), detalhes={'count': 0})

    if destinatarios == 'polo_ativo':
        log('[DESTINATARIOS] OPÇÃO: Clicando no polo ativo')
        try:
            btn = wait_for_clickable(driver, 'button[name="btnIntimarSomentePoloAtivo"]', timeout=10, by=By.CSS_SELECTOR)
            if not btn:
                raise RuntimeError('Botão polo ativo não clicável')
            _clicar_e_aguardar_spinner(driver, btn)
            return ResultadoExecucao(sucesso=True, status='geral', detalhes={'count': 0})
        except Exception as e:
            log(f'[DESTINATARIOS][ERRO] Falha ao clicar polo ativo: {e}')
            return ResultadoExecucao(sucesso=False, status='error', erro=str(e), detalhes={'count': 0})

    if destinatarios in ('polo_passivo', 'polo_passivo_2x'):
        cliques = cliques_polo_passivo if destinatarios == 'polo_passivo' else 2
        log(f'[DESTINATARIOS] Clicando no polo passivo ({cliques}x)')
        try:
            btn_polo_passivo = wait_for_clickable(driver, 'button[name="btnIntimarSomentePoloPassivo"]', timeout=5, by=By.CSS_SELECTOR)
            if not btn_polo_passivo:
                raise RuntimeError('Botão polo passivo não clicável')
            for i in range(cliques):
                _clicar_e_aguardar_spinner(driver, btn_polo_passivo)
                if i < cliques - 1:
                    # Spinner já sumiu (garantido por _clicar_e_aguardar_spinner) — apenas
                    # reobter a referência (Angular pode recriar o nó), sem novo timeout de espera.
                    btn_polo_passivo = driver.find_element(By.CSS_SELECTOR, 'button[name="btnIntimarSomentePoloPassivo"]')
            return ResultadoExecucao(sucesso=True, status='geral', detalhes={'count': 0})
        except Exception as e:
            log(f'[DESTINATARIOS][ERRO] Falha ao clicar polo passivo: {e}')
            return ResultadoExecucao(sucesso=False, status='error', erro=str(e), detalhes={'count': 0})

    if destinatarios == 'terceiros':
        log('[DESTINATARIOS] OPÇÃO TERCEIROS: Clicando em terceiros interessados')
        try:
            if espera.ate_habilitar(driver, 'button[name="btnIntimarSomenteTerceirosInteressados"]', teto=5):
                btn_terceiro = driver.find_element(By.CSS_SELECTOR, 'button[name="btnIntimarSomenteTerceirosInteressados"]')
            else:
                # <i> não tem estado disabled real: ate_aparecer, não ate_habilitar
                espera.ate_aparecer(driver, 'i.fa.fa-user.pec-polo-outros-partes-processo', teto=5)
                btn_terceiro = driver.find_element(By.CSS_SELECTOR, 'i.fa.fa-user.pec-polo-outros-partes-processo')
            _clicar_e_aguardar_spinner(driver, btn_terceiro)
            return ResultadoExecucao(sucesso=True, status='geral', detalhes={'count': 0})
        except Exception as e:
            log(f'[DESTINATARIOS][ERRO] Falha ao selecionar terceiros: {e}')
            return ResultadoExecucao(sucesso=False, status='error', erro=str(e), detalhes={'count': 0})

    if destinatarios == 'primeiro':
        log('[DESTINATARIOS] OPCAO PRIMEIRO: primeiro do Polo Passivo (pec_excluiargos)')
        try:
            # 1. Expandir painel Polo Passivo (legado: WebDriverWait + execute_script)
            painel_header_xpath = (
                '//mat-expansion-panel-header[.//div[contains(@class,"pec-titulo-painel-expansivel-partes-processo")'
                ' and contains(normalize-space(.), "Polo Passivo")]]'
            )
            painel_header = espera.elemento(driver, painel_header_xpath, teto=10, visivel=False)
            if painel_header is None:
                raise Exception('painel Polo Passivo não apareceu')
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", painel_header)
            safe_click_no_scroll(driver, painel_header)
            espera.assentar(driver, 0.5)

            # 2. Clicar na primeira seta do Polo Passivo (legado: WebDriverWait + execute_script)
            seta_xpath = (
                '//mat-expansion-panel[.//*[contains(text(), "Polo Passivo")]]'
                '//button[@aria-label="Clique para acrescentar esta parte '
                'à lista de destinatários de expedientes e comunicações."][1]'
            )
            if not espera.ate_habilitar(driver, seta_xpath, teto=10):
                raise Exception('primeira seta do Polo Passivo não habilitou')
            primeira_seta = driver.find_element(By.XPATH, seta_xpath)
            safe_click_no_scroll(driver, primeira_seta)
            log('[DESTINATARIOS] Primeira seta (primeiro destinatário) clicada')
            espera.assentar(driver, 1)

            # 3. Buscar e adicionar TRIBUNAL se necessário (pec_excluiargos)
            try:
                log('[DESTINATARIOS] 3. Buscando tribunal nos endereços disponíveis...')

                # Verificar se formulário de consulta de endereços apareceu
                try:
                    WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, '.pec-consulta-enderecos'))
                    )
                    log('[DESTINATARIOS] 3a. Formulário de consulta de endereços detectado')
                except Exception:
                    log('[DESTINATARIOS] 3a. Formulário de consulta de endereços não apareceu')
                    raise Exception('Consulta não apareceu')

                # Verificar se há snack-bar de "Nenhum resultado encontrado"
                try:
                    WebDriverWait(driver, 3).until(
                        EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Nenhum resultado encontrado')]"))
                    )
                    log('[DESTINATARIOS] 3b. Snack-bar detectado: "Nenhum resultado encontrado" -> incluir tribunal via CEP')

                    # Digitar CEP 01302906 no campo inputCep
                    log('[DESTINATARIOS] 3c. Digitando CEP 01302906 no campo inputCep')
                    campo_cep = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, 'input#inputCep'))
                    )
                    campo_cep.clear()
                    for char in '01302906':
                        campo_cep.send_keys(char)
                        espera.assentar(driver, 0.1)
                    espera.ate_texto(driver, 'span.mat-option-text', '01302-906', teto=1)

                    log('[DESTINATARIOS] 3d. Clicando na opção do tribunal TRT2 São Paulo')
                    opcao_tribunal = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, "//span[@class='mat-option-text' and contains(text(), '01302-906')]"))
                    )
                    opcao_tribunal.click()
                    log('[DESTINATARIOS] Opção do tribunal selecionada')
                    espera.ate_habilitar(driver, 'button[aria-label="Salva as alterações"]', teto=0.5)

                    log('[DESTINATARIOS] 3e. Clicando no botão Salvar das alterações')
                    btn_salvar_alteracoes = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[aria-label="Salva as alterações"]'))
                    )
                    btn_salvar_alteracoes.click()
                    log('[DESTINATARIOS] Alterações salvas')
                    espera.ate_aparecer(driver, 'i.fa.fa-window-close.btn-fechar', teto=0.5)

                    log('[DESTINATARIOS] 3f. Clicando no botão fechar para fechar endereços')
                    btn_fechar = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, 'i.fa.fa-window-close.btn-fechar'))
                    )
                    btn_fechar.click()
                    log('[DESTINATARIOS] Janela de endereços fechada')
                except Exception:
                    # Se não houver snack-bar, procurar tribunal nas linhas da tabela
                    log('[DESTINATARIOS] 3b. Nenhum snack-bar - buscando tribunal na tabela de endereços')
                    try:
                        WebDriverWait(driver, 5).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, 'table[name="Endereços do destinatário no sistema"]'))
                        )

                        # Procura por linhas que contenham "TRIBUNAL" (case insensitive)
                        linhas_tribunal = driver.find_elements(
                            By.XPATH,
                            "//td[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'tribunal')]"
                        )

                        if linhas_tribunal:
                            log('[DESTINATARIOS] 3c. Encontrado endereço do tribunal, clicando na seta')
                            linha_tribunal = linhas_tribunal[0].find_element(By.XPATH, './ancestor::tr')
                            seta_tribunal = linha_tribunal.find_element(By.CSS_SELECTOR, 'button[aria-label="Selecionar endereço"]')
                            seta_tribunal.click()
                            log('[DESTINATARIOS] Endereço do tribunal selecionado')
                            time.sleep(0.5)

                            log('[DESTINATARIOS] 3d. Clicando no botão fechar para fechar endereços')
                            btn_fechar = WebDriverWait(driver, 10).until(
                                EC.element_to_be_clickable((By.CSS_SELECTOR, 'i.fa.fa-window-close.btn-fechar'))
                            )
                            btn_fechar.click()
                            log('[DESTINATARIOS] Janela de endereços fechada')
                        else:
                            log('[DESTINATARIOS] 3c. Nenhum endereço do tribunal encontrado na tabela - incluindo tribunal via CEP')

                            log('[DESTINATARIOS] 3d. Digitando CEP 01302906 no campo inputCep')
                            campo_cep = WebDriverWait(driver, 10).until(
                                EC.element_to_be_clickable((By.CSS_SELECTOR, 'input#inputCep'))
                            )
                            campo_cep.clear()
                            for char in '01302906':
                                campo_cep.send_keys(char)
                                time.sleep(0.1)
                            time.sleep(1)

                            log('[DESTINATARIOS] 3e. Clicando na opção do tribunal TRT2')
                            opcao_tribunal = WebDriverWait(driver, 10).until(
                                EC.element_to_be_clickable((By.XPATH, "//span[@class='mat-option-text' and contains(text(), '01302-906')]"))
                            )
                            opcao_tribunal.click()
                            log('[DESTINATARIOS] Tribunal selecionado')
                            time.sleep(0.5)

                            log('[DESTINATARIOS] 3f. Clicando em Salvar alterações')
                            btn_salvar_alteracoes = WebDriverWait(driver, 10).until(
                                EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[aria-label="Salva as alterações"]'))
                            )
                            btn_salvar_alteracoes.click()
                            log('[DESTINATARIOS] Alterações salvas')
                            time.sleep(0.5)

                            log('[DESTINATARIOS] 3g. Fechando janela de endereços')
                            btn_fechar = WebDriverWait(driver, 10).until(
                                EC.element_to_be_clickable((By.CSS_SELECTOR, 'i.fa.fa-window-close.btn-fechar'))
                            )
                            btn_fechar.click()
                            log('[DESTINATARIOS] Janela fechada')
                    except Exception as e_tabela:
                        log(f'[DESTINATARIOS] Erro ao processar endereços: {e_tabela}')
            except Exception as tribunal_err:
                log(f'[DESTINATARIOS] Aviso: Não foi possível adicionar tribunal: {tribunal_err}')

            return ResultadoExecucao(sucesso=True, status='ok', detalhes={'count': 1})
        except Exception as e:
            log(f'[DESTINATARIOS][ERRO] Falha ao selecionar primeiro destinatário: {e}')
            return ResultadoExecucao(sucesso=False, status='error', erro=str(e), detalhes={'count': 0})
    # opção padrão: clicar polo passivo 1x
    log('[DESTINATARIOS] OPÇÃO PADRÃO: Clicando no polo passivo (1x)')
    try:
        btn_polo_passivo = wait_for_clickable(driver, 'button[name="btnIntimarSomentePoloPassivo"]', timeout=10, by=By.CSS_SELECTOR)
        if not btn_polo_passivo:
            raise RuntimeError('Botão polo passivo não clicável')
        _clicar_e_aguardar_spinner(driver, btn_polo_passivo)
        return ResultadoExecucao(sucesso=True, status='geral', detalhes={'count': 0})
    except Exception as e:
        log(f'[DESTINATARIOS][ERRO] Falha ao clicar polo passivo padrão: {e}')
        return ResultadoExecucao(sucesso=False, status='error', erro=str(e), detalhes={'count': 0})
```


### 2. `leg/atos/comunicacao_destinatarios.py` — `selecionar_destinatarios(driver, destinatarios, terceiro=False, ...)`

**Range:** L451-L570 (120 linhas)
**Callers:** `atos/comunicacao.py:make_comunicacao_wrapper()`
**Callees:** `click_headless_safe()`, `aguardar_renderizacao_nativa()`, `_selecionar_endereco_tribunal()`
**Relevancia:** Versão funcional de referência no leg/ — bloco 'primeiro' simplificado (L548-563)

```python
# leg/atos/comunicacao_destinatarios.py L451-L570
def selecionar_destinatarios(driver, destinatarios, terceiro=False, debug=False, log=None, cliques_polo_passivo=1, cliques_informado=2, observacao=None, numero_processo=None, dados_processo=None):
    from core.resultado_execucao import ResultadoExecucao
    if log is None:
        def log(_msg):
            return None

    qtd_seta = 2 if str(cliques_polo_passivo).strip().lower() in ('2', '2x') else 1
    qtd_informado = 2 if str(cliques_informado).strip().lower() in ('2', '2x') else 1
    qtd_cliques_fallback = 2 if str(cliques_polo_passivo).strip().lower() in ('2', '2x') else 1

    # Roteamento principal
    if destinatarios is None:
        log('[DESTINATARIOS] Parâmetro None - pulando seleção')
        return ResultadoExecucao(sucesso=False, status='skip', detalhes={'count': 0})

    if isinstance(destinatarios, list):
        log('[DESTINATARIOS] Lista explícita recebida via override')
        return _selecionar_por_lista(driver, destinatarios, 'lista explícita', log, fallback_polo_passivo=True, qtd_seta_override=None, debug=debug, qtd_cliques_fallback=qtd_cliques_fallback)

    if destinatarios == 'extraido':
        log('[DESTINATARIOS] OPÇÃO EXTRAIDO: carregando destinatários em cache')
        try:
            from Fix.extracao_processo import carregar_destinatarios_cache
            cache = carregar_destinatarios_cache() or {}
            lista_destinatarios = cache.get('destinatarios', []) or []
            return _selecionar_por_lista(driver, lista_destinatarios, 'cache', log, fallback_polo_passivo=True, qtd_seta_override=2, debug=debug, qtd_cliques_fallback=qtd_cliques_fallback)
        except Exception as e:
            log(f'[DESTINATARIOS][ERRO] Falha no modo extraido: {e}')
            return ResultadoExecucao(sucesso=False, status='error', erro=str(e), detalhes={'count': 0})

    if destinatarios == 'informado':
        log('[DESTINATARIOS] OPÇÃO INFORMADO: cruzando observação com dados do processo')
        try:
            if not dados_processo:
                try:
                    from Fix.extracao_processo import extrair_dados_processo
                    dados_processo = extrair_dados_processo(driver, caminho_json='dadosatuais.json', debug=debug)
                except Exception:
                    dados_processo = _carregar_dadosatuais_local('dadosatuais.json')

            candidatos = _montar_destinatarios_por_observacao(observacao, dados_processo, debug=debug)
            return _selecionar_por_lista(driver, candidatos, 'observação', log, fallback_polo_passivo=True, qtd_seta_override=qtd_informado, debug=debug, qtd_cliques_fallback=qtd_cliques_fallback)
        except Exception as e:
            log(f'[DESTINATARIOS][ERRO] Falha no modo informado: {e}')
            return ResultadoExecucao(sucesso=False, status='error', erro=str(e), detalhes={'count': 0})

    if destinatarios == 'polo_ativo':
        log('[DESTINATARIOS] OPÇÃO: Clicando no polo ativo')
        try:
            click_headless_safe(
                driver,
                'i.fa.fa-user.pec-polo-ativo-partes-processo.pec-botao-intimar-polo-partes-processo',
                by=By.CSS_SELECTOR
            )
            return ResultadoExecucao(sucesso=True, status='geral', detalhes={'count': 0})
        except Exception as e:
            log(f'[DESTINATARIOS][ERRO] Falha ao clicar polo ativo: {e}')
            return ResultadoExecucao(sucesso=False, status='error', erro=str(e), detalhes={'count': 0})

    if destinatarios in ('polo_passivo', 'polo_passivo_2x'):
        cliques = cliques_polo_passivo if destinatarios == 'polo_passivo' else 2
        log(f'[DESTINATARIOS] Clicando no polo passivo ({cliques}x)')
        try:
            btn_polo_passivo = wait_for_clickable(driver, 'button[name="btnIntimarSomentePoloPassivo"]', timeout=10, by=By.CSS_SELECTOR)
            if not btn_polo_passivo:
                raise RuntimeError('Botão polo passivo não clicável')
            for i in range(cliques):
                safe_click_no_scroll(driver, btn_polo_passivo, log=False)
                if i < cliques - 1:
                    esperar_elemento(driver, 'button[name="btnIntimarSomentePoloPassivo"]', timeout=3, by=By.CSS_SELECTOR)
            return ResultadoExecucao(sucesso=True, status='geral', detalhes={'count': 0})
        except Exception as e:
            log(f'[DESTINATARIOS][ERRO] Falha ao clicar polo passivo: {e}')
            return ResultadoExecucao(sucesso=False, status='error', erro=str(e), detalhes={'count': 0})

    if destinatarios == 'terceiros':
        log('[DESTINATARIOS] OPÇÃO TERCEIROS: Clicando em terceiros interessados')
        try:
            try:
                btn_terceiro = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[name="btnIntimarSomenteTerceirosInteressados"]'))
                )
            except Exception:
                btn_terceiro = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, 'i.fa.fa-user.pec-polo-outros-partes-processo'))
                )
            driver.execute_script("arguments[0].click();", btn_terceiro)
            return ResultadoExecucao(sucesso=True, status='geral', detalhes={'count': 0})
        except Exception as e:
            log(f'[DESTINATARIOS][ERRO] Falha ao selecionar terceiros: {e}')
            return ResultadoExecucao(sucesso=False, status='error', erro=str(e), detalhes={'count': 0})

    if destinatarios == 'primeiro':
        log('[DESTINATARIOS] OPCAO PRIMEIRO: primeiro do Polo Passivo')
        try:
            click_headless_safe(driver, '//mat-expansion-panel-header[.//div[contains(@class,"pec-titulo-painel-expansivel-partes-processo") and contains(normalize-space(.), "Polo Passivo")]]', by=By.XPATH)
            aguardar_renderizacao_nativa(driver, '.pec-partes-polo li.partes-corpo, ul.sem-padding li.partes-corpo, mat-row', modo='aparecer', timeout=5)
            click_headless_safe(driver, '//mat-expansion-panel[.//*[contains(text(), "Polo Passivo")]]//button[@aria-label="Clique para acrescentar esta parte à lista de destinatários de expedientes e comunicações."][1]', by=By.XPATH)
            log('[DESTINATARIOS] Primeira seta clicada')

            if _selecionar_endereco_tribunal(driver, log, debug=debug):
                log('[DESTINATARIOS] Endereço do tribunal verificado/ajustado')
            else:
                log('[DESTINATARIOS] Endereço do tribunal não foi ajustado ou não estava disponível')

            return ResultadoExecucao(sucesso=True, status='ok', detalhes={'count': 1})
        except Exception as e:
            log(f'[DESTINATARIOS][ERRO] Falha no modo primeiro: {e}')
            return ResultadoExecucao(sucesso=False, status='error', erro=str(e), detalhes={'count': 0})
    # opção padrão: clicar polo passivo 1x
    log('[DESTINATARIOS] OPÇÃO PADRÃO: Clicando no polo passivo (1x)')
    try:
        btn_polo_passivo = wait_for_clickable(driver, 'button[name="btnIntimarSomentePoloPassivo"]', timeout=10, by=By.CSS_SELECTOR)
        if not btn_polo_passivo:
            raise RuntimeError('Botão polo passivo não clicável')
        safe_click_no_scroll(driver, btn_polo_passivo, log=False)
        return ResultadoExecucao(sucesso=True, status='geral', detalhes={'count': 0})
    except Exception as e:
        log(f'[DESTINATARIOS][ERRO] Falha ao clicar polo passivo padrão: {e}')
        return ResultadoExecucao(sucesso=False, status='error', erro=str(e), detalhes={'count': 0})
```


### 3. `leg/atos/comunicacao_destinatarios.py` — `_selecionar_endereco_tribunal(driver, log, debug=False)`

**Range:** L179-L221 (43 linhas)
**Callers:** `leg/atos/comunicacao_destinatarios.py:selecionar_destinatarios()`
**Callees:** `esperar_elemento()`, `_incluir_tribunal_por_cep()`, `safe_click_no_scroll()`
**Relevancia:** Função auxiliar que encapsula a lógica de endereço do tribunal (a ser portada para o código ativo)

```python
# leg/atos/comunicacao_destinatarios.py L179-L221
def _selecionar_endereco_tribunal(driver, log, debug=False):
    try:
        if not esperar_elemento(driver, '.pec-consulta-enderecos', timeout=5, by=By.CSS_SELECTOR):
            if debug:
                log('[DESTINATARIOS] Endereço do tribunal não solicitado após seleção do destinatário')
            return False
    except Exception as e:
        if debug:
            log(f'[DESTINATARIOS][WARN] Falha ao detectar painel de endereços: {e}')
        return False

    try:
        if esperar_elemento(driver, "//*[contains(text(), 'Nenhum resultado encontrado')]", timeout=3, by=By.XPATH):
            log('[DESTINATARIOS] 3b. Nenhum resultado encontrado -> incluir tribunal via CEP')
            return _incluir_tribunal_por_cep(driver, log, debug=debug)
    except Exception:
        pass

    try:
        linhas_tribunal = driver.find_elements(By.XPATH,
            "//td[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'tribunal')]")
        for linha in linhas_tribunal:
            try:
                linha_tr = linha.find_element(By.XPATH, './ancestor::tr')
                seta = linha_tr.find_element(By.CSS_SELECTOR, 'button[aria-label="Selecionar endereço"]')
                if seta:
                    driver.execute_script('arguments[0].scrollIntoView({block: "center"});', seta)
                    safe_click_no_scroll(driver, seta, log=False)
                    log('[DESTINATARIOS] ✓ Endereço do tribunal selecionado')
                    btn_fechar = wait_for_clickable(driver, 'i.fa.fa-window-close.btn-fechar', timeout=10, by=By.CSS_SELECTOR)
                    if btn_fechar:
                        safe_click_no_scroll(driver, btn_fechar, log=False)
                    time.sleep(0.5)
                    return True
            except Exception:
                continue
    except Exception:
        pass

    log('[DESTINATARIOS] 3c. Nenhum endereço do tribunal encontrado na tabela - incluindo tribunal via CEP')
    return _incluir_tribunal_por_cep(driver, log, debug=debug)


```


### 4. `leg/atos/comunicacao_destinatarios.py` — `_incluir_tribunal_por_cep(driver, log, debug=False)`

**Range:** L143-L178 (36 linhas)
**Callers:** `leg/atos/comunicacao_destinatarios.py:_selecionar_endereco_tribunal()`
**Callees:** `wait_for_clickable()`, `safe_click_no_scroll()`
**Relevancia:** Implementa o fluxo CEP 01302906 → TRT2 São Paulo (a ser portada para o código ativo)

```python
# leg/atos/comunicacao_destinatarios.py L143-L178
def _incluir_tribunal_por_cep(driver, log, debug=False):
    try:
        campo_cep = wait_for_clickable(driver, 'input#inputCep', timeout=10, by=By.CSS_SELECTOR)
        if not campo_cep:
            raise RuntimeError('Campo CEP não encontrado')
        campo_cep.clear()
        for char in '01302906':
            campo_cep.send_keys(char)
            time.sleep(0.1)
        time.sleep(1)

        opcao_tribunal = wait_for_clickable(
            driver,
            "//span[@class='mat-option-text' and contains(text(), '01302-906')]",
            timeout=10,
            by=By.XPATH
        )
        if not opcao_tribunal:
            raise RuntimeError('Opção tribunal não encontrada')
        safe_click_no_scroll(driver, opcao_tribunal, log=False)

        btn_salvar_alteracoes = wait_for_clickable(driver, 'button[aria-label="Salva as alterações"]', timeout=10, by=By.CSS_SELECTOR)
        if btn_salvar_alteracoes:
            safe_click_no_scroll(driver, btn_salvar_alteracoes, log=False)

        btn_fechar = wait_for_clickable(driver, 'i.fa.fa-window-close.btn-fechar', timeout=10, by=By.CSS_SELECTOR)
        if btn_fechar:
            safe_click_no_scroll(driver, btn_fechar, log=False)
        time.sleep(0.5)
        return True
    except Exception as e:
        if debug:
            log(f'[DESTINATARIOS][WARN] Falha ao incluir tribunal via CEP: {e}')
        return False


```


### 5. `Fix/browser_suporte.py` — `safe_click_no_scroll(driver, element, log=False)`

**Range:** L511-L523 (13 linhas)
**Callers:** `atos/comunicacao_destinatarios.py:selecionar_destinatarios()`
**Callees:** `driver.execute_script()`
**Relevancia:** Mecanismo de clique usado no código atual — dispatchEvent(MouseEvent) em vez de .click() nativo

```python
# Fix/browser_suporte.py L511-L523
def safe_click_no_scroll(driver, element, log=False):
    """Click without scroll"""
    try:
        driver.execute_script("arguments[0].dispatchEvent(new MouseEvent('click', {view: window, bubbles: true, cancelable: true}))", element)
        return True
    except Exception:
        return False


# ============================================================
# Public API
# ============================================================

```


### 6. `Fix/browser_suporte.py` — `click_headless_safe(driver: WebDriver, selector: str, by: By = By.CSS_SELECTOR, ...)`

**Range:** L388-L446 (59 linhas)
**Callers:** `leg/atos/comunicacao_destinatarios.py:selecionar_destinatarios()`
**Callees:** `espera.ate_habilitar()`, `element.click()`, `safe_click_no_scroll()`
**Relevancia:** Mecanismo de clique alternativo com 3 estratégias — estratégia 1 usa element.click() nativo (Selenium)

```python
# Fix/browser_suporte.py L388-L446
def click_headless_safe(driver: WebDriver, selector: str, by: By = By.CSS_SELECTOR, timeout: int = 10) -> bool:
    """
    Click ultra-seguro para modo headless com 3 estrategias progressivas.

    Estrategia 1: Wait padrao + click normal
    Estrategia 2: Limpar overlays + scroll + wait + click
    Estrategia 3: JavaScript click direto (ultimo recurso)

    Compensacao especifica do caminho Selenium headless (geckodriver renderiza
    por caminho diferente do headed). Sob o backend Playwright vira no-op
    efetivo: `locator.click()` faz a mesma checagem de actionability em
    headless e headed — ja substituida por `pjeplay/nativo.py`.

    Args:
        driver: WebDriver instance
        selector: Seletor CSS ou XPath
        by: Tipo de seletor (padrao CSS_SELECTOR)
        timeout: Timeout em segundos

    Returns:
        bool: True se click foi bem-sucedido
    """

    # Estrategia 1: Wait padrao element_to_be_clickable
    try:
        if not espera.ate_habilitar(driver, selector, teto=timeout):
            raise TimeoutException(f"element_to_be_clickable: {selector}")
        element = driver.find_element(by, selector)
        element.click()
        return True
    except (ElementClickInterceptedException, TimeoutException):
        pass

    # Estrategia 2: Limpar overlays + scroll + wait + click
    try:
        limpar_overlays_headless(driver)
        element = espera.elemento(driver, selector, teto=timeout // 2, visivel=False)
        if element is None:
            raise TimeoutException(f"presence_of_element_located: {selector}")
        scroll_to_element_safe(driver, element)
        # Aguarda elemento estar clicavel apos scroll (DOM-settle)
        if not espera.ate_habilitar(driver, selector, teto=timeout // 2):
            raise TimeoutException(f"element_to_be_clickable: {selector}")
        driver.find_element(by, selector).click()
        return True
    except (ElementClickInterceptedException, StaleElementReferenceException):
        pass

    # Estrategia 3: JavaScript click (fallback final)
    try:
        element = driver.find_element(by, selector)
        safe_click_no_scroll(driver, element)
        espera.ate_js(driver, "document.readyState === 'complete' || document.readyState === 'interactive'", teto=2.0)  # DOM-settle apos click JS
        return True
    except Exception as e:
        logger.error(f"[HEADLESS] Todas estrategias falharam para '{selector}': {e}")
        return False


```


### 7. `atos/comunicacao.py` — `make_comunicacao_wrapper()`

**Range:** L88-L110 (23 linhas)
**Callers:** `atos/wrappers_pec.py:pec_excluiargos`
**Callees:** `selecionar_destinatarios()`
**Relevancia:** Factory que cria pec_excluiargos com destinatarios='primeiro' — ponto de configuração do fluxo

```python
# atos/comunicacao.py L88-L110
def make_comunicacao_wrapper(
    tipo_expediente: str, 
    prazo: int, 
    nome_comunicacao: str, 
    sigilo: str, 
    modelo_nome: str, 
    subtipo: Optional[str] = None, 
    descricao: Optional[str] = None,
    tipo_prazo: str = 'dias uteis',
    gigs_extra: Optional[Union[bool, Tuple, List, Any]] = None,
    coleta_conteudo: Optional[Callable] = None,
    inserir_conteudo: Optional[Callable] = None,
    cliques_polo_passivo: int = 1,
    cliques_informado: int = 2,
    destinatarios: str = 'extraido',
    mudar_expediente: Optional[bool] = None,
    checar_sp: Optional[bool] = None,
    endereco_tipo: Optional[str] = None,
    trocar_modelo: bool = False,
    wrapper_name: Optional[str] = None,  # Nome específico para __name__
    terceiro_default: bool = False,
    assinar: bool = False,
    modelo_troca_correios: Optional[str] = None
```

