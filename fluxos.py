import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time

# Carrega os botões do arquivo JSON
with open('botoes_maispje.json', encoding='utf-8') as f:
    botoes = json.load(f)

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
                guia_mov = driver.find_element(By.CSS_SELECTOR, 'pje-editor-lateral div[aria-posinset="2"]')
                if guia_mov.get_attribute('aria-selected') == "false":
                    guia_mov.click()
                    time.sleep(0.5)
                movimentos = str(config['movimento']).split(',')
                for i, mo in enumerate(movimentos):
                    if i == 0:
                        chk = driver.find_element(By.XPATH, f'//pje-movimento//mat-checkbox[contains(.,"{mo}")]')
                        if 'checked' not in chk.get_attribute('class'):
                            chk.find_element(By.TAG_NAME, 'label').click()
                            time.sleep(0.5)
                    else:
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
                btn_gravar = driver.find_element(By.CSS_SELECTOR, 'pje-lancador-de-movimentos button[aria-label*="Gravar"]')
                btn_gravar.click()
                time.sleep(0.5)
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
            print(f"[DESPACHO] Responsável: {config['responsavel']} (implementar fluxo se necessário)")
        print('[DESPACHO] Fluxo de despacho automatizado finalizado.')
        return True
    except Exception as e:
        print(f'[DESPACHO][ERRO] {e}')
        return False

def acao_bt_apec_selenium(driver, config):
    """
    Executa o fluxo automatizado de comunicação/expediente (intimação, mandado, edital, etc) na tela de minutas,
    fiel ao gigs-plugin.js (acao_bt_aaComunicacao).
    config: dict com chaves tipo_expediente, tipo_prazo, prazo, subtipo, descricao, sigilo, modelo, salvar, assinar, nm_botao, etc.
    """
    try:
        print(f"[APEC] Iniciando ação automatizada de comunicação/expediente: {config.get('tipo_expediente','')} - {config.get('modelo','')}")
        # NÃO clicar no botão envelope, nem buscar botão na tela: fluxo deve partir diretamente do config recebido
        # 2. Esperar navegação para /comunicacoesprocessuais/minutas
        for _ in range(30):
            if '/comunicacoesprocessuais/minutas' in driver.current_url:
                print('[APEC] Navegação para minutas confirmada.')
                break
            time.sleep(0.5)
        else:
            print('[APEC][ERRO] Timeout aguardando navegação para minutas.')
            return False
        # 3. Preencher tipo de expediente
        tipo = config.get('tipo_expediente') or config.get('tipo') or 'Intimação'
        try:
            campo_tipo = driver.find_element(By.CSS_SELECTOR, 'mat-select[placeholder="Tipo de Expediente"]')
            campo_tipo.click()
            time.sleep(0.5)
            xpath_opcao = f"//mat-option//span[contains(text(), '{tipo}') or contains(text(), '{tipo.lower()}') or contains(text(), '{tipo.upper()}')]"
            opcao_tipo = driver.find_element(By.XPATH, xpath_opcao)
            opcao_tipo.click()
            print(f"[APEC] Tipo de expediente selecionado: {tipo}")
            time.sleep(0.5)
        except Exception as e:
            print(f'[APEC][ERRO] Falha ao selecionar tipo de expediente: {e}')
            return False
        # 4. Tipo de prazo e preenchimento
        tipo_prazo = (config.get('tipo_prazo') or 'dias uteis').lower()
        prazo = config.get('prazo')
        try:
            if tipo_prazo == 'dias uteis' or tipo_prazo == 'dias úteis':
                radio = driver.find_element(By.XPATH, "//mat-radio-button[.//span[contains(translate(.,'Ú','u'),'dias uteis') or contains(translate(.,'Ú','u'),'dias úteis')]]")
                radio.click()
                campo_prazo = driver.find_element(By.CSS_SELECTOR, 'input[aria-label="Prazo em dias úteis"]')
                campo_prazo.clear()
                campo_prazo.send_keys(str(prazo))
                print(f"[APEC] Prazo em dias úteis preenchido: {prazo}")
            elif tipo_prazo == 'sem prazo':
                radio = driver.find_element(By.XPATH, "//mat-radio-button[.//span[contains(translate(.,'SEM PRAZO','sem prazo'),'sem prazo')]]")
                radio.click()
                print('[APEC] Tipo de prazo: sem prazo')
            elif tipo_prazo == 'data certa':
                radio = driver.find_element(By.XPATH, "//mat-radio-button[.//span[contains(translate(.,'DATA CERTA','data certa'),'data certa')]]")
                radio.click()
                campo_prazo = driver.find_element(By.CSS_SELECTOR, 'input[aria-label="Prazo em data certa"]')
                campo_prazo.clear()
                campo_prazo.send_keys(str(prazo))
                print(f"[APEC] Prazo em data certa preenchido: {prazo}")
        except Exception as e:
            print(f'[APEC][ERRO] Falha ao preencher tipo/prazo: {e}')
        # 5. Clicar em "Confeccionar ato agrupado"
        try:
            btn_conf = driver.find_element(By.CSS_SELECTOR, 'button[aria-label="Confeccionar ato agrupado"]')
            btn_conf.click()
            print('[APEC] Botão Confeccionar ato agrupado clicado.')
            time.sleep(1)
        except Exception as e:
            print(f'[APEC][ERRO] Falha ao clicar em Confeccionar ato agrupado: {e}')
            return False
        # 6. Subtipo do expediente
        if config.get('subtipo'):
            try:
                campo_subtipo = driver.find_element(By.CSS_SELECTOR, 'input[data-placeholder="Tipo de Documento"]')
                campo_subtipo.clear()
                campo_subtipo.send_keys(config['subtipo'])
                campo_subtipo.send_keys(Keys.ENTER)
                print(f"[APEC] Subtipo selecionado: {config['subtipo']}")
                time.sleep(0.5)
            except Exception as e:
                print(f'[APEC][ERRO] Falha ao selecionar subtipo: {e}')
        # 7. Descrição
        if config.get('descricao'):
            try:
                input_desc = driver.find_element(By.CSS_SELECTOR, 'input[aria-label="Descrição"]')
                input_desc.clear()
                input_desc.send_keys(config['descricao'])
                print(f"[APEC] Descrição preenchida: {config['descricao']}")
            except Exception:
                print('[APEC] Campo de descrição não encontrado.')
        # 8. Sigilo
        sigilo = (config.get('sigilo') or 'nao').lower()
        if 'sim' in sigilo:
            try:
                chk_sigilo = driver.find_element(By.CSS_SELECTOR, 'input[name="sigiloso"]')
                if not chk_sigilo.is_selected():
                    chk_sigilo.click()
                print('[APEC] Sigilo ativado.')
            except Exception:
                print('[APEC] Campo de sigilo não encontrado.')
        # 9. Escolha do modelo
        if config.get('modelo'):
            try:
                campo_modelo = driver.find_element(By.CSS_SELECTOR, 'input[id="inputFiltro"]')
                campo_modelo.clear()
                campo_modelo.send_keys(config['modelo'])
                campo_modelo.send_keys(Keys.ENTER)
                print(f"[APEC] Modelo selecionado: {config['modelo']}")
                time.sleep(1)
                modelo_item = driver.find_element(By.XPATH, f"//div[@role='treeitem' and contains(.,'{config['modelo']}')]")
                modelo_item.click()
                print('[APEC] Modelo inserido no editor.')
            except Exception as e:
                print(f'[APEC][ERRO] Não foi possível selecionar/inserir modelo: {e}')
        # 10. Salvar e finalizar minuta
        salvar = (config.get('salvar') or 'sim').lower()
        if salvar == 'sim':
            try:
                btn_salvar = driver.find_element(By.CSS_SELECTOR, 'button[aria-label="Salvar"]')
                btn_salvar.click()
                print('[APEC] Minuta salva.')
                time.sleep(1)
                btn_finalizar = driver.find_element(By.CSS_SELECTOR, 'button[aria-label="Finalizar minuta"]')
                btn_finalizar.click()
                print('[APEC] Minuta finalizada.')
                time.sleep(1)
            except Exception as e:
                print(f'[APEC][ERRO] Não foi possível salvar/finalizar minuta: {e}')
                return False
        # 11. Parâmetros especiais: seleção de destinatários, assinatura, etc
        nm_botao = config.get('nm_botao','')
        parametros = []
        import re
        m = re.findall(r'\[(.*?)\]', nm_botao)
        if m:
            parametros = [p.strip() for p in ','.join(m).split(',')]
        if parametros:
            print(f"[APEC] Parâmetros especiais detectados: {parametros}")
            condicao = 0
            if 'ativo' in parametros:
                try:
                    btn_ativo = driver.find_element(By.CSS_SELECTOR, 'pje-pec-partes-processo button[aria-label*="somente polo ativo"]')
                    btn_ativo.click()
                    print('[APEC] Polo ativo selecionado.')
                    condicao = 1
                    time.sleep(1)
                except Exception as e:
                    print(f'[APEC][ERRO] Polo ativo: {e}')
            if 'passivo' in parametros:
                try:
                    btn_passivo = driver.find_element(By.CSS_SELECTOR, 'pje-pec-partes-processo button[aria-label*="somente polo passivo"]')
                    btn_passivo.click()
                    print('[APEC] Polo passivo selecionado.')
                    condicao = 2
                    time.sleep(1)
                except Exception as e:
                    print(f'[APEC][ERRO] Polo passivo: {e}')
            if 'terceiros' in parametros:
                try:
                    btn_terc = driver.find_element(By.CSS_SELECTOR, 'pje-pec-partes-processo button[aria-label*="somente terceiros interessados"]')
                    btn_terc.click()
                    print('[APEC] Terceiros selecionados.')
                    condicao = 3
                    time.sleep(1)
                except Exception as e:
                    print(f'[APEC][ERRO] Terceiros: {e}')
            if 'trt' in parametros:
                try:
                    btn_trt = driver.find_element(By.CSS_SELECTOR, '#maisPje_bt_invisivel_outrosDestinatarios_TRT')
                    btn_trt.click()
                    print('[APEC] TRT selecionado.')
                    condicao = 4
                    time.sleep(1)
                except Exception as e:
                    print(f'[APEC][ERRO] TRT: {e}')
            try:
                for _ in range(20):
                    if driver.find_elements(By.CSS_SELECTOR, 'pje-pec-tabela-destinatarios i[aria-label="Ato confeccionado"]'):
                        print('[APEC] Ato confeccionado detectado.')
                        break
                    time.sleep(0.5)
                time.sleep(1)
            except Exception:
                print('[APEC] Não foi possível detectar ato confeccionado.')
            try:
                btn_salvar_exp = driver.find_element(By.CSS_SELECTOR, 'pje-pec-tabela-destinatarios button[aria-label="Salva os expedientes"]')
                btn_salvar_exp.click()
                print('[APEC] Expedientes salvos.')
                time.sleep(1)
            except Exception as e:
                print(f'[APEC][ERRO] Salvar expedientes: {e}')
            if 'assinar' in parametros and condicao > 0:
                try:
                    btn_assinar = driver.find_element(By.CSS_SELECTOR, 'pje-pec-tabela-destinatarios button[aria-label="Assinar ato(s)"]')
                    btn_assinar.click()
                    print('[APEC] Ato(s) assinado(s).')
                    time.sleep(1)
                except Exception as e:
                    print(f'[APEC][ERRO] Assinar ato(s): {e}')
        print('[APEC] Fluxo de comunicação/expediente automatizado finalizado.')
        return True
    except Exception as e:
        print(f'[APEC][ERRO] {e}')
        return False

def acao_bt_anexar_selenium(driver, config):
    """
    Executa o fluxo automatizado de anexar documentos, fiel ao gigs-plugin.js (acao_bt_aaAnexar).
    config: dict com chaves tipo, descricao, sigilo, modelo, assinar, extras, etc.
    """
    try:
        print(f"[ANEXAR] Iniciando ação automatizada de anexar: {config.get('tipo','')} - {config.get('modelo','')}")
        # 1. Clicar no botão de anexar documentos (fa-paperclip)
        try:
            btn_anexar = driver.find_element(By.ID, 'pjextension_bt_detalhes_4')
            btn_anexar.click()
            print('[ANEXAR] Botão de anexar documentos clicado.')
            time.sleep(1)
        except Exception:
            print('[ANEXAR] Botão de anexar documentos não encontrado ou já clicado.')
        # 2. PDF?
        if config.get('modelo','').lower() == 'pdf':
            try:
                switch_pdf = driver.find_element(By.CSS_SELECTOR, 'input[role="switch"]')
                switch_pdf.click()
                print('[ANEXAR] Switch PDF ativado.')
                time.sleep(0.5)
            except Exception:
                print('[ANEXAR] Switch PDF não encontrado.')
        # 3. Preencher tipo
        tipo = config.get('tipo') or 'Certidão'
        try:
            campo_tipo = driver.find_element(By.CSS_SELECTOR, 'input[aria-label="Tipo de Documento"]')
            campo_tipo.clear()
            campo_tipo.send_keys(tipo)
            campo_tipo.send_keys(Keys.ENTER)
            print(f"[ANEXAR] Tipo de documento selecionado: {tipo}")
            time.sleep(0.5)
        except Exception as e:
            print(f'[ANEXAR][ERRO] Falha ao selecionar tipo: {e}')
        # 4. Preencher descrição
        if config.get('descricao'):
            try:
                campo_desc = driver.find_element(By.CSS_SELECTOR, 'input[aria-label="Descrição"]')
                campo_desc.clear()
                campo_desc.send_keys(config['descricao'])
                print(f"[ANEXAR] Descrição preenchida: {config['descricao']}")
            except Exception:
                print('[ANEXAR] Campo de descrição não encontrado.')
        # 5. Sigilo
        sigilo = (config.get('sigilo') or 'nao').lower()
        if 'sim' in sigilo:
            try:
                chk_sigilo = driver.find_element(By.CSS_SELECTOR, 'input[name="sigiloso"]')
                if not chk_sigilo.is_selected():
                    chk_sigilo.click()
                print('[ANEXAR] Sigilo ativado.')
                time.sleep(0.5)
            except Exception:
                print('[ANEXAR] Campo de sigilo não encontrado.')
        # 6. Escolha do modelo
        if config.get('modelo') and config.get('modelo','').lower() != 'pdf':
            try:
                campo_modelo = driver.find_element(By.CSS_SELECTOR, 'input[id="inputFiltro"]')
                campo_modelo.clear()
                campo_modelo.send_keys(config['modelo'])
                campo_modelo.send_keys(Keys.ENTER)
                print(f"[ANEXAR] Modelo selecionado: {config['modelo']}")
                time.sleep(1)
                modelo_item = driver.find_element(By.XPATH, f"//div[@role='treeitem' and contains(.,'{config['modelo']}')]")
                modelo_item.click()
                print('[ANEXAR] Modelo inserido no editor.')
            except Exception as e:
                print(f'[ANEXAR][ERRO] Não foi possível selecionar/inserir modelo: {e}')
        # 7. Upload de PDF (se modelo for PDF)
        if config.get('modelo','').lower() == 'pdf':
            try:
                btn_upload = driver.find_element(By.CSS_SELECTOR, 'label.upload-button')
                btn_upload.click()
                print('[ANEXAR] Botão de upload de PDF clicado. Aguarde seleção manual do arquivo.')
                for _ in range(120):
                    if driver.find_elements(By.CSS_SELECTOR, 'span.nome-arquivo-pdf'):
                        print('[ANEXAR] PDF carregado.')
                        break
                    time.sleep(0.5)
                if not config.get('descricao'):
                    try:
                        el_pdf = driver.find_element(By.CSS_SELECTOR, 'span.nome-arquivo-pdf')
                        nome_pdf = el_pdf.text.replace('.pdf','')
                        campo_desc = driver.find_element(By.CSS_SELECTOR, 'input[aria-label="Descrição"]')
                        campo_desc.clear()
                        campo_desc.send_keys(nome_pdf)
                        print(f"[ANEXAR] Descrição preenchida com nome do PDF: {nome_pdf}")
                    except Exception:
                        print('[ANEXAR] Não foi possível preencher descrição com nome do PDF.')
            except Exception as e:
                print(f'[ANEXAR][ERRO] Upload de PDF: {e}')
        # 8. Juntada de depoimentos/anexos
        extras = config.get('extras','')
        if '[anexos]' in extras.lower() or extras == 'ID997_Anexar Depoimento':
            try:
                btn_salvar = driver.find_element(By.CSS_SELECTOR, 'button[aria-label="Salvar"]')
                btn_salvar.click()
                print('[ANEXAR] Documento salvo para anexos.')
                time.sleep(1)
                guia_anexos = driver.find_element(By.CSS_SELECTOR, 'div[aria-posinset="2"]')
                guia_anexos.click()
                print('[ANEXAR] Guia Anexos aberta.')
                time.sleep(0.5)
                btn_upload = driver.find_element(By.CSS_SELECTOR, 'label.upload-button')
                btn_upload.click()
                print('[ANEXAR] Botão de upload de anexo clicado.')
                time.sleep(2)
                if extras == 'ID997_Anexar Depoimento':
                    guia_anexos.click()
                    print('[ANEXAR] Fluxo de depoimento finalizado.')
                    return True
            except Exception as e:
                print(f'[ANEXAR][ERRO] Juntada de anexos: {e}')
        # 9. Assinar ou salvar
        assinar = (config.get('assinar') or 'nao').lower()
        if assinar == 'sim':
            try:
                btn_assinar = driver.find_element(By.CSS_SELECTOR, 'button[aria-label="Assinar documento e juntar ao processo"]')
                btn_assinar.click()
                print('[ANEXAR] Documento assinado e juntado ao processo.')
                time.sleep(2)
            except Exception as e:
                print(f'[ANEXAR][ERRO] Assinar documento: {e}')
        else:
            try:
                btn_salvar = driver.find_element(By.CSS_SELECTOR, 'button[aria-label="Salvar"]')
                btn_salvar.click()
                print('[ANEXAR] Documento salvo.')
                time.sleep(1)
            except Exception as e:
                print(f'[ANEXAR][ERRO] Salvar documento: {e}')
        print('[ANEXAR] Fluxo de anexar documento automatizado finalizado.')
        return True
    except Exception as e:
        print(f'[ANEXAR][ERRO] {e}')
        return False

# Exemplo de uso:
if __name__ == "__main__":
    # driver = webdriver.Firefox()  # ou webdriver.Chrome(), já autenticado
    driver = None  # Substitua pelo seu driver Selenium
    # Escolha um botão de cada grupo para testar
    despacho = botoes['aaDespacho'][0]
    comunicacao = botoes['aaComunicacao'][0]
    anexar = botoes['aaAnexar'][0]
    acao_bt_aaDespacho_selenium(driver, despacho)
    acao_bt_apec_selenium(driver, comunicacao)
    acao_bt_anexar_selenium(driver, anexar)
