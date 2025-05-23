from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time

def add_botao_despacho_selenium(driver):
    """
    Adiciona um botão flutuante na página para ativar o despacho automatizado.
    """
    driver.execute_script('''
        if (!document.getElementById('btn-despacho-auto')) {
            var btn = document.createElement('button');
            btn.id = 'btn-despacho-auto';
            btn.innerText = 'Despacho Automático';
            btn.style.position = 'fixed';
            btn.style.top = '10px';
            btn.style.right = '10px';
            btn.style.zIndex = 9999;
            btn.style.background = '#1976d2';
            btn.style.color = '#fff';
            btn.style.padding = '10px 16px';
            btn.style.border = 'none';
            btn.style.borderRadius = '6px';
            btn.style.fontSize = '16px';
            btn.onclick = function() { alert("Execute o comando Python para despacho automático!"); };
            document.body.appendChild(btn);
        }
    ''')

def acao_bt_aaDespacho_selenium(driver, config):
    """
    Executa o fluxo de despacho automatizado, fiel ao gigs-plugin.js.
    config: dict com chaves nm_botao, tipo, descricao, sigilo, modelo, juiz, responsavel, cor, vinculo, assinar
    """
    try:
        print(f"[DESPACHO] Iniciando ação automatizada: {config.get('nm_botao','')} (vínculo: {config.get('vinculo','')})")
        # 1. Movimentar para tarefa correta (Análise → Conclusão ao Magistrado)
        try:
            btn_analise = driver.find_element(By.XPATH, "//button[contains(translate(.,'ANÁLISE','análise'),'análise')]")
            btn_analise.click()
            print('[DESPACHO] Movimentado para Análise.')
            time.sleep(1)
        except Exception:
            print('[DESPACHO] Botão Análise não encontrado ou já na tarefa correta.')
        try:
            btn_conclusao = driver.find_element(By.XPATH, "//button[contains(translate(.,'CONCLUSÃO','conclusão'),'conclusão ao magistrado')]")
            btn_conclusao.click()
            print('[DESPACHO] Movimentado para Conclusão ao Magistrado.')
            time.sleep(1)
        except Exception:
            print('[DESPACHO] Botão Conclusão ao Magistrado não encontrado ou já na tarefa correta.')
        # 2. Selecionar magistrado (se necessário)
        if config.get('juiz'):
            try:
                select_juiz = driver.find_element(By.CSS_SELECTOR, 'mat-select[placeholder="Magistrado"]')
                select_juiz.click()
                time.sleep(0.5)
                opcoes = driver.find_elements(By.CSS_SELECTOR, 'mat-option')
                for op in opcoes:
                    if config['juiz'].lower() in op.text.lower():
                        op.click()
                        print(f"[DESPACHO] Magistrado selecionado: {config['juiz']}")
                        break
                time.sleep(1)
            except Exception:
                print('[DESPACHO] Não foi possível selecionar magistrado.')
        # 3. Selecionar tipo de conclusão (Despacho)
        try:
            btn_tipo = driver.find_element(By.XPATH, "//button[contains(.,'Despacho')]")
            btn_tipo.click()
            print('[DESPACHO] Tipo de conclusão selecionado: Despacho.')
            time.sleep(1)
        except Exception:
            print('[DESPACHO] Botão de tipo Despacho não encontrado ou já selecionado.')
        # 4. Preencher descrição
        if config.get('descricao'):
            try:
                input_desc = driver.find_element(By.CSS_SELECTOR, 'input[aria-label="Descrição"]')
                input_desc.clear()
                input_desc.send_keys(config['descricao'])
                print(f"[DESPACHO] Descrição preenchida: {config['descricao']}")
            except Exception:
                print('[DESPACHO] Campo de descrição não encontrado.')
        # 5. Sigilo
        if config.get('sigilo','').lower() == 'sim':
            try:
                chk_sigilo = driver.find_element(By.CSS_SELECTOR, 'input[name="sigiloso"]')
                if not chk_sigilo.is_selected():
                    chk_sigilo.click()
                print('[DESPACHO] Sigilo ativado.')
            except Exception:
                print('[DESPACHO] Campo de sigilo não encontrado.')
        # 6. Escolher modelo
        if config.get('modelo'):
            try:
                campo_modelo = driver.find_element(By.CSS_SELECTOR, 'input[id="inputFiltro"]')
                campo_modelo.clear()
                campo_modelo.send_keys(config['modelo'])
                campo_modelo.send_keys(Keys.ENTER)
                print(f"[DESPACHO] Modelo selecionado: {config['modelo']}")
                time.sleep(1)
                # Seleciona o modelo na árvore
                modelo_item = driver.find_element(By.XPATH, f"//div[@role='treeitem' and contains(.,'{config['modelo']}')]")
                modelo_item.click()
                print('[DESPACHO] Modelo inserido no editor.')
            except Exception:
                print('[DESPACHO] Não foi possível selecionar/inserir modelo.')
        # 7. Salvar documento
        try:
            btn_salvar = driver.find_element(By.CSS_SELECTOR, 'button[aria-label="Salvar"]')
            btn_salvar.click()
            print('[DESPACHO] Documento salvo.')
            time.sleep(1)
        except Exception:
            print('[DESPACHO] Botão Salvar não encontrado.')

        # === AÇÕES EXTRAS (INTIMAÇÃO, PEC, PRAZOS, MOVIMENTOS, ETC) ===
        # 8. Intimação/PEC
        if config.get('marcar_pec'):
            try:
                # Exemplo: botão ou checkbox de PEC
                btn_pec = driver.find_element(By.CSS_SELECTOR, 'button[aria-label*="PEC"], input[type="checkbox"][aria-label*="PEC"]')
                if btn_pec.tag_name == 'input' and not btn_pec.is_selected():
                    btn_pec.click()
                elif btn_pec.tag_name == 'button':
                    btn_pec.click()
                print('[DESPACHO] PEC marcada.')
                time.sleep(0.5)
            except Exception:
                print('[DESPACHO] Não foi possível marcar PEC.')
        # 9. Prazo
        if config.get('prazo') is not None:
            try:
                # Busca linhas de destinatários na minuta
                linhas = driver.find_elements(By.CSS_SELECTOR, 'table.t-class tr.ng-star-inserted')
                if not linhas:
                    print('[DESPACHO][PRAZO][ERRO] Nenhuma linha de destinatário encontrada!')
                else:
                    for tr in linhas:
                        try:
                            input_prazo = tr.find_element(By.CSS_SELECTOR, 'mat-form-field.prazo input[type="text"].mat-input-element')
                            input_prazo.clear()
                            input_prazo.send_keys(str(config['prazo']))
                            print(f'[DESPACHO][PRAZO][OK] Preenchido prazo {config["prazo"]} para destinatário.')
                        except Exception as e:
                            print(f'[DESPACHO][PRAZO][WARN] Erro ao preencher prazo: {e}')
            except Exception as e:
                print(f'[DESPACHO][PRAZO][ERRO] {e}')
        # 10. Movimento
        if config.get('movimento'):
            try:
                # Ativa a guia Movimentos se desativada
                guia_mov = driver.find_element(By.CSS_SELECTOR, 'pje-editor-lateral div[aria-posinset="2"]')
                if guia_mov.get_attribute('aria-selected') == "false":
                    guia_mov.click()
                    time.sleep(0.5)
                movimentos = str(config['movimento']).split(',')
                for i, mo in enumerate(movimentos):
                    if i == 0:
                        # Checkbox de movimento
                        chk = driver.find_element(By.XPATH, f'//pje-movimento//mat-checkbox[contains(.,"{mo}")]')
                        if 'checked' not in chk.get_attribute('class'):
                            chk.find_element(By.TAG_NAME, 'label').click()
                            time.sleep(0.5)
                    else:
                        # Complementos do tipo
                        time.sleep(0.5)
                        complementos = driver.find_elements(By.CSS_SELECTOR, 'pje-complemento')
                        if len(complementos) > i-1:
                            combo = complementos[i-1].find_element(By.TAG_NAME, 'mat-select')
                            combo.click()
                            time.sleep(0.3)
                            opcoes = driver.find_elements(By.CSS_SELECTOR, 'mat-option')
                            for op in opcoes:
                                if mo.lower() in op.text.lower():
                                    op.click()
                                    break
                            time.sleep(0.5)
                # Gravar movimento
                btn_gravar = driver.find_element(By.CSS_SELECTOR, 'pje-lancador-de-movimentos button[aria-label*="Gravar"]')
                btn_gravar.click()
                time.sleep(0.5)
                # Confirmação
                btn_sim = driver.find_element(By.XPATH, '//mat-dialog-container//button[.//span[contains(text(),"Sim")]]')
                btn_sim.click()
                print('[DESPACHO] Movimento(s) lançado(s).')
            except Exception as e:
                print(f'[DESPACHO][MOVIMENTO][ERRO] {e}')
        # 9. Enviar para assinatura
        if config.get('assinar','não').lower() == 'sim':
            try:
                btn_assinar = driver.find_element(By.CSS_SELECTOR, 'button[aria-label="Enviar para assinatura"]')
                btn_assinar.click()
                print('[DESPACHO] Documento enviado para assinatura.')
                time.sleep(1)
            except Exception:
                print('[DESPACHO] Botão Enviar para assinatura não encontrado.')
        # 10. Inserir responsável (se necessário)
        if config.get('responsavel'):
            # ...adicione aqui o fluxo de inserir responsável, se aplicável...
            print(f"[DESPACHO] Responsável: {config['responsavel']} (implementar fluxo se necessário)")
        print('[DESPACHO] Fluxo de despacho automatizado finalizado.')
        return True
    except Exception as e:
        print(f'[DESPACHO][ERRO] {e}')
        return False
