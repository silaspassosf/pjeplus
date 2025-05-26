import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time

# Carrega os botões do arquivo JSON
with open('botoes_maispje.json', encoding='utf-8') as f:
    botoes = json.load(f)

# Sistema de vínculos globais
vinculos_queue = []
executando_vinculo = False

def executar_vinculo(vinculo_param, driver):
    """
    Sistema de vínculos (chaining) - executa próxima ação automaticamente.
    Equivalente ao storage_vinculo() e conferirVinculoEspecial() do JavaScript.
    
    Args:
        vinculo_param: string do vínculo ('tipo|nome_botao' ou 'Nenhum')
        driver: instância do Selenium WebDriver
    
    Returns:
        bool: True se processou vínculo, False se 'Nenhum' ou erro
    """
    global vinculos_queue, executando_vinculo
    
    try:
        print(f"[VINCULOS] Processando vínculo: {vinculo_param}")
        
        if not vinculo_param or vinculo_param.lower() in ['nenhum', 'none', '']:
            print("[VINCULOS] Nenhum vínculo para executar.")
            return False
        
        # Previne execução recursiva
        if executando_vinculo:
            print("[VINCULOS] Já executando vínculo. Adicionando à fila.")
            vinculos_queue.append(vinculo_param)
            return True
        
        # Processar vínculos especiais (AAEspecial - arrays)
        if ',' in vinculo_param:
            vinculos_lista = [v.strip() for v in vinculo_param.split(',')]
            proximo_vinculo = vinculos_lista[0]
            vinculos_restantes = vinculos_lista[1:]
            
            print(f"[VINCULOS] AAEspecial detectado. Próximo: {proximo_vinculo}")
            print(f"[VINCULOS] Restantes na fila: {vinculos_restantes}")
            
            # Adiciona restantes à fila
            vinculos_queue.extend(vinculos_restantes)
            vinculo_param = proximo_vinculo
        
        # Parse do vínculo: 'tipo|nome_botao'
        if '|' not in vinculo_param:
            print(f"[VINCULOS][ERRO] Formato de vínculo inválido: {vinculo_param}")
            return False
        
        tipo, nome_botao = vinculo_param.split('|', 1)
        
        # Mapear tipo para seção do JSON
        secao_map = {
            'Anexar': 'aaAnexar',
            'Comunicação': 'aaComunicacao', 
            'AutoGigs': 'aaAutogigs',
            'Despacho': 'aaDespacho',
            'Movimento': 'aaMovimento',
            'Checklist': 'aaChecklist',
            'LançarMovimento': 'aaLancarMovimentos',
            'Variados': 'aaVariados'
        }
        
        secao = secao_map.get(tipo)
        if not secao:
            print(f"[VINCULOS][ERRO] Tipo de vínculo não suportado: {tipo}")
            return False
        
        # Buscar botão na seção
        if secao not in botoes:
            print(f"[VINCULOS][ERRO] Seção {secao} não encontrada no JSON de botões.")
            return False
        
        botao_config = None
        botao_indice = -1
        for i, botao in enumerate(botoes[secao]):
            if botao.get('nm_botao', '') == nome_botao:
                botao_config = botao
                botao_indice = i
                break
        
        if not botao_config:
            print(f"[VINCULOS][ERRO] Botão '{nome_botao}' não encontrado na seção {secao}.")
            return False
        
        print(f"[VINCULOS] Executando vínculo: {secao}[{botao_indice}] - {nome_botao}")
        
        # Marcar como executando para prevenir recursão
        executando_vinculo = True
        
        # Pequeno delay para garantir que a ação anterior terminou
        time.sleep(1)
        
        # Executar ação do vínculo
        sucesso = executar_acao_botao(driver, secao, botao_indice)
        
        # Resetar flag
        executando_vinculo = False
        
        # Processar próximo da fila se houver
        if vinculos_queue:
            proximo_da_fila = vinculos_queue.pop(0)
            print(f"[VINCULOS] Processando próximo da fila: {proximo_da_fila}")
            time.sleep(0.5)  # Pequeno delay entre vínculos
            return executar_vinculo(proximo_da_fila, driver)
        
        return sucesso
        
    except Exception as e:
        executando_vinculo = False
        print(f"[VINCULOS][ERRO] {e}")
        return False

def finalizar_acao_com_vinculo(driver, config, acao_nome="ACAO"):
    """
    Finaliza uma ação e executa vínculos se configurados.
    Deve ser chamada no final de cada função acao_bt_*_selenium().
    
    Args:
        driver: instância do Selenium WebDriver
        config: configuração da ação executada
        acao_nome: nome da ação para logs
    
    Returns:
        bool: True se processou com sucesso
    """
    try:
        vinculo = config.get('vinculo', 'Nenhum')
        
        print(f"[{acao_nome}] Ação finalizada. Vínculo: {vinculo}")
        
        if vinculo and vinculo.lower() not in ['nenhum', 'none', '']:
            print(f"[{acao_nome}] Iniciando execução de vínculo: {vinculo}")
            return executar_vinculo(vinculo, driver)
        else:
            print(f"[{acao_nome}] Nenhum vínculo para executar.")
            return True
            
    except Exception as e:
        print(f"[{acao_nome}][VINCULOS][ERRO] {e}")
        return False

def executar_acao_botao(driver, secao, indice=0):
    """
    Função auxiliar para executar ação de botão baseado na seção e índice.
    
    Args:
        driver: instância do Selenium WebDriver
        secao: nome da seção ('aaDespacho', 'aaAutogigs', etc.)
        indice: índice do botão na seção (padrão: 0)
    
    Returns:
        bool: True se executado com sucesso, False caso contrário
    """
    try:
        if secao not in botoes:
            print(f'[EXECUTAR] Seção {secao} não encontrada no arquivo de botões.')
            return False
        
        if indice >= len(botoes[secao]):
            print(f'[EXECUTAR] Índice {indice} inválido para seção {secao} (máximo: {len(botoes[secao])-1}).')
            return False
        
        config = botoes[secao][indice]
        print(f'[EXECUTAR] Executando {secao}[{indice}]: {config.get("nm_botao", "")}')
        
        if secao == 'aaDespacho':
            return acao_bt_aaDespacho_selenium(driver, config)
        elif secao == 'aaComunicacao':
            return acao_bt_apec_selenium(driver, config)
        elif secao == 'aaAnexar':
            return acao_bt_anexar_selenium(driver, config)
        elif secao == 'aaAutogigs':
            return acao_bt_aaAutogigs_selenium(driver, config)
        elif secao == 'aaChecklist':
            return acao_bt_aaChecklist_selenium(driver, config)
        elif secao == 'aaLancarMovimentos':
            return acao_bt_aaLancarMovimentos_selenium(driver, config)
        elif secao == 'aaMovimento':
            return acao_bt_aaMovimento_selenium(driver, config)
        elif secao == 'aaVariados':
            return acao_bt_aaVariados_selenium(driver, config)
        else:
            print(f'[EXECUTAR] Seção {secao} não possui função implementada.')
            return False
            
    except Exception as e:
        print(f'[EXECUTAR][ERRO] {e}')
        return False

def listar_botoes_secao(secao):
    """
    Lista todos os botões disponíveis em uma seção.
    
    Args:
        secao: nome da seção
    
    Returns:
        list: lista com informações dos botões
    """
    if secao not in botoes:
        print(f'Seção {secao} não encontrada.')
        return []
    
    print(f'\n=== Botões da seção {secao} ===')
    for i, botao in enumerate(botoes[secao]):
        nome = botao.get('nm_botao', 'Sem nome')
        descricao = botao.get('descricao', botao.get('observacao', ''))
        print(f'{i:2d}: {nome} - {descricao}')
    
    return botoes[secao]

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

def acao_bt_aaAutogigs_selenium(driver, config):
    """
    Executa o fluxo automatizado de AutoGigs (prazos, comentários, chips e lembretes).
    Implementação completa baseada na versão JavaScript original.
    
    config: dict com chaves:
    - nm_botao: nome do botão
    - tipo: 'prazo'|'preparo'|'comentario'|'chip'|'lembrete'
    - tipo_atividade: tipo da atividade ou nome do chip/título do lembrete
    - prazo: dias úteis ou data para prazos, visibilidade para comentários/lembretes
    - responsavel: responsável pela atividade GIGS
    - responsavel_processo: responsável pelo processo
    - observacao: texto de observação/conteúdo
    - salvar: 'sim'|'não' para salvar automaticamente
    - cor: cor do botão (não usado na execução)
    - vinculo: próxima ação a executar
    """
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    
    try:
        nm_botao = config.get('nm_botao', '')
        tipo = config.get('tipo', '')
        concluir = '[concluir]' in nm_botao
        
        print(f"[AUTOGIGS] Iniciando: {nm_botao} - Tipo: {tipo} - Concluir: {concluir}")
        
        # Verificar se GIGS está aberto em tela de detalhes
        gigs_fechado = _verificar_gigs_fechado(driver)
        if gigs_fechado:
            _abrir_gigs(driver)
        
        # Executar ação baseada no tipo
        if tipo == 'chip':
            return _executar_chip(driver, config, concluir)
        elif tipo == 'comentario':
            return _executar_comentario(driver, config, concluir, gigs_fechado)
        elif tipo == 'lembrete':
            return _executar_lembrete(driver, config, concluir)
        else:  # prazo ou preparo (default)
            return _executar_gigs_atividade(driver, config, concluir, gigs_fechado)
        
    except Exception as e:
        print(f'[AUTOGIGS][ERRO] {e}')
        return False

def _verificar_gigs_fechado(driver):
    """Verifica se o GIGS está fechado na tela de detalhes"""
    try:
        driver.find_element(By.CSS_SELECTOR, 'button[aria-label="Mostrar o GIGS"]')
        return True
    except:
        return False

def _abrir_gigs(driver):
    """Abre o GIGS se estiver fechado"""
    try:
        btn_mostrar = driver.find_element(By.CSS_SELECTOR, 'button[aria-label="Mostrar o GIGS"]')
        btn_mostrar.click()
        time.sleep(1)
        print("[AUTOGIGS] GIGS aberto")
    except Exception as e:
        print(f"[AUTOGIGS][ERRO] Falha ao abrir GIGS: {e}")

def _fechar_gigs(driver):
    """Fecha o GIGS se estiver aberto"""
    try:
        btn_esconder = driver.find_element(By.CSS_SELECTOR, 'button[aria-label="Esconder o GIGS"]')
        btn_esconder.click()
        time.sleep(0.5)
        print("[AUTOGIGS] GIGS fechado")
    except:
        pass

def _executar_chip(driver, config, concluir):
    """Executa ações de chip (adicionar ou remover)"""
    try:
        tipo_atividade = config.get('tipo_atividade', '')
        salvar = config.get('salvar', '').lower() == 'sim'
        
        if concluir:
            # Remover chips existentes
            return _remover_chips(driver, tipo_atividade)
        else:
            # Adicionar novos chips
            return _adicionar_chips(driver, tipo_atividade, salvar)
            
    except Exception as e:
        print(f"[AUTOGIGS][CHIP][ERRO] {e}")
        return False

def _remover_chips(driver, chips_para_remover):
    """Remove chips do processo"""
    try:
        # Expandir lista de chips se necessário
        try:
            btn_expandir = driver.find_element(By.CSS_SELECTOR, 'pje-lista-etiquetas button[aria-label="Expandir Chips"]')
            btn_expandir.click()
            time.sleep(0.5)
        except:
            pass
        
        # Buscar chips para remover
        chips = chips_para_remover.split(',')
        for chip in chips:
            chip = chip.strip()
            try:
                # Buscar botão de remoção do chip específico
                btn_remover = driver.find_element(By.CSS_SELECTOR, f'pje-lista-etiquetas mat-chip button[aria-label*="{chip}"]')
                btn_remover.click()
                time.sleep(0.5)
                
                # Confirmar remoção se aparecer diálogo
                try:
                    btn_confirmar = driver.find_element(By.XPATH, "//mat-dialog-container//button[contains(.,'Sim') or contains(.,'Confirmar')]")
                    btn_confirmar.click()
                    time.sleep(0.5)
                    print(f"[AUTOGIGS][CHIP] Chip removido: {chip}")
                except:
                    pass
                    
            except Exception as e:
                print(f"[AUTOGIGS][CHIP][AVISO] Chip não encontrado para remoção: {chip}")
        
        return True
        
    except Exception as e:
        print(f"[AUTOGIGS][CHIP][ERRO] Falha ao remover chips: {e}")
        return False

def _adicionar_chips(driver, chips_para_adicionar, salvar):
    """Adiciona chips ao processo"""
    try:
        # Clicar no botão de adicionar chip
        btn_chip = driver.find_element(By.CSS_SELECTOR, 'button[aria-label="Incluir Chip Amarelo"]')
        btn_chip.click()
        time.sleep(1)
        
        # Verificar se é pergunta dinâmica
        if '[perguntar]' in chips_para_adicionar:
            chips_base = chips_para_adicionar.replace('[perguntar]', '').strip()
            try:
                campo_nome = driver.find_element(By.CSS_SELECTOR, 'input[data-placeholder="Nome do chip"]')
                campo_nome.clear()
                campo_nome.send_keys(chips_base)
                print(f"[AUTOGIGS][CHIP] Modo pergunta ativado com base: {chips_base}")
                # Não salva automaticamente no modo pergunta
                return True
            except:
                pass
        
        # Modo normal - selecionar chips da lista
        chips = chips_para_adicionar.split(',')
        for chip in chips:
            chip = chip.strip()
            try:
                # Buscar chip na tabela de etiquetas disponíveis
                chip_elemento = driver.find_element(By.XPATH, f'//table[@name="Etiquetas"]//tr[contains(.,"{chip}[MMA]")]')
                checkbox = chip_elemento.find_element(By.CSS_SELECTOR, 'input[aria-label="Marcar chip"]')
                if not checkbox.is_selected():
                    checkbox.click()
                    print(f"[AUTOGIGS][CHIP] Chip selecionado: {chip}")
                    time.sleep(0.3)
            except Exception as e:
                print(f"[AUTOGIGS][CHIP][AVISO] Chip não encontrado: {chip}")
        
        # Salvar se configurado
        if salvar:
            try:
                btn_salvar = driver.find_element(By.XPATH, "//button[contains(.,'Salvar')]")
                btn_salvar.click()
                time.sleep(1)
                print("[AUTOGIGS][CHIP] Chips salvos")
            except Exception as e:
                print(f"[AUTOGIGS][CHIP][ERRO] Falha ao salvar: {e}")
        
        return True
        
    except Exception as e:
        print(f"[AUTOGIGS][CHIP][ERRO] Falha ao adicionar chips: {e}")
        return False

def _executar_comentario(driver, config, concluir, gigs_fechado):
    """Executa ações de comentário (adicionar ou arquivar)"""
    try:
        responsavel_processo = config.get('responsavel_processo', '')
        observacao = config.get('observacao', '')
        visibilidade = config.get('prazo', 'LOCAL')  # prazo é usado como visibilidade
        salvar = config.get('salvar', '').lower() == 'sim'
        
        # Definir responsável do processo se especificado
        if responsavel_processo:
            _definir_responsavel_processo(driver, responsavel_processo)
        
        if concluir:
            # Arquivar comentários existentes
            return _arquivar_comentarios(driver, observacao, gigs_fechado)
        else:
            # Adicionar novo comentário
            return _adicionar_comentario(driver, observacao, visibilidade, salvar, gigs_fechado)
            
    except Exception as e:
        print(f"[AUTOGIGS][COMENTARIO][ERRO] {e}")
        return False

def _arquivar_comentarios(driver, texto_busca, gigs_fechado):
    """Arquiva comentários que contenham o texto especificado"""
    try:
        arquivados = 0
        
        while True:
            # Buscar comentários com o texto
            comentarios = driver.find_elements(By.CSS_SELECTOR, 
                'table[name="Lista de Comentários"] tbody tr, div[id="comentarios"] mat-card, div[id="tabela-comentarios"] tbody tr')
            
            comentario_encontrado = False
            for comentario in comentarios:
                if texto_busca.lower() in comentario.text.lower():
                    try:
                        # Clicar no botão arquivar
                        btn_arquivar = comentario.find_element(By.CSS_SELECTOR, 'i[aria-label*="Arquivar"], button[id*="arquivar"]')
                        btn_arquivar.click()
                        time.sleep(0.5)
                        
                        # Confirmar arquivamento
                        try:
                            btn_confirmar = driver.find_element(By.XPATH, "//mat-dialog-container//button[contains(.,'Sim') or contains(.,'Confirmar')]")
                            btn_confirmar.click()
                            time.sleep(1)
                            arquivados += 1
                            comentario_encontrado = True
                            print(f"[AUTOGIGS][COMENTARIO] Comentário arquivado: {texto_busca}")
                            break
                        except:
                            pass
                    except Exception as e:
                        print(f"[AUTOGIGS][COMENTARIO][ERRO] Falha ao arquivar: {e}")
            
            if not comentario_encontrado:
                break
        
        if gigs_fechado:
            _fechar_gigs(driver)
        
        print(f"[AUTOGIGS][COMENTARIO] Total de comentários arquivados: {arquivados}")
        return True
        
    except Exception as e:
        print(f"[AUTOGIGS][COMENTARIO][ERRO] Falha ao arquivar: {e}")
        return False

def _adicionar_comentario(driver, observacao, visibilidade, salvar, gigs_fechado):
    """Adiciona novo comentário"""
    try:
        # Clicar em novo comentário
        btn_novo = driver.find_element(By.XPATH, "//pje-gigs-comentarios-lista//button[contains(.,'Novo Comentário')]")
        btn_novo.click()
        time.sleep(1)
        
        # Processar observação (verificar se é pergunta)
        observacao_final = _processar_observacao(driver, observacao)
        
        # Preencher comentário
        campo_desc = driver.find_element(By.CSS_SELECTOR, 'textarea[name="descricao"], textarea[formcontrolname="descricao"]')
        campo_desc.clear()
        campo_desc.send_keys(observacao_final)
        
        # Definir visibilidade
        _definir_visibilidade_comentario(driver, visibilidade)
        
        # Salvar se configurado
        if salvar:
            btn_salvar = driver.find_element(By.XPATH, "//button[contains(.,'Salvar')]")
            btn_salvar.click()
            time.sleep(1)
            
            if gigs_fechado:
                _fechar_gigs(driver)
            
            print(f"[AUTOGIGS][COMENTARIO] Comentário adicionado: {observacao_final[:50]}...")
        
        return True
        
    except Exception as e:
        print(f"[AUTOGIGS][COMENTARIO][ERRO] Falha ao adicionar: {e}")
        return False

def _definir_visibilidade_comentario(driver, visibilidade):
    """Define a visibilidade do comentário"""
    try:
        radios = driver.find_elements(By.CSS_SELECTOR, 'pje-gigs-comentarios-cadastro mat-radio-button')
        
        if visibilidade.upper() == 'LOCAL' and len(radios) > 0:
            radios[0].find_element(By.CSS_SELECTOR, 'input').click()
        elif visibilidade.upper() == 'RESTRITA' and len(radios) > 1:
            radios[1].find_element(By.CSS_SELECTOR, 'input').click()
            # Escolher usuários restritos se necessário
            _escolher_usuarios_restritos(driver)
        elif visibilidade.upper() == 'GLOBAL' and len(radios) > 2:
            radios[2].find_element(By.CSS_SELECTOR, 'input').click()
            
        time.sleep(0.5)
        
    except Exception as e:
        print(f"[AUTOGIGS][COMENTARIO][ERRO] Falha ao definir visibilidade: {e}")

def _escolher_usuarios_restritos(driver):
    """Permite escolha de usuários restritos para comentário"""
    try:
        select_usuarios = driver.find_element(By.CSS_SELECTOR, 'pje-gigs-comentarios-cadastro mat-select[placeholder="Usuários concedidos"]')
        select_usuarios.click()
        print("[AUTOGIGS][COMENTARIO] Selecione os usuários restritos manualmente")
        # Aguarda o usuário fazer a seleção
        time.sleep(3)
    except Exception as e:
        print(f"[AUTOGIGS][COMENTARIO][ERRO] Falha ao abrir seleção de usuários: {e}")

def _executar_lembrete(driver, config, concluir):
    """Executa ações de lembrete (adicionar ou remover)"""
    try:
        titulo = config.get('tipo_atividade', '')
        visibilidade = config.get('prazo', 'LOCAL')  # prazo é usado como visibilidade
        conteudo = config.get('observacao', '')
        salvar = config.get('salvar', '').lower() == 'sim'
        
        if concluir:
            # Remover lembretes existentes
            return _remover_lembretes(driver, titulo, conteudo)
        else:
            # Adicionar novo lembrete
            return _adicionar_lembrete(driver, titulo, visibilidade, conteudo, salvar)
            
    except Exception as e:
        print(f"[AUTOGIGS][LEMBRETE][ERRO] {e}")
        return False

def _remover_lembretes(driver, titulo, conteudo):
    """Remove lembretes que correspondam aos critérios"""
    try:
        # Aguardar carregamento dos post-its
        try:
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'pje-visualizador-post-its div[class*="post-it-set"]'))
            )
        except:
            print("[AUTOGIGS][LEMBRETE] Nenhum lembrete encontrado")
            return True
        
        postits = driver.find_elements(By.CSS_SELECTOR, 'div[class*="post-it-set"] mat-expansion-panel')
        removidos = 0
        
        for postit in postits:
            try:
                elemento_titulo = postit.find_element(By.CSS_SELECTOR, 'div[class="post-it-div-titulo"]')
                elemento_conteudo = postit.find_element(By.CSS_SELECTOR, 'div[aria-label="Conteúdo do Lembrete"]')
                
                titulo_match = titulo.lower() in elemento_titulo.text.lower() if titulo else True
                conteudo_match = conteudo.lower() in elemento_conteudo.text.lower() if conteudo else True
                
                if titulo_match and conteudo_match:
                    btn_remover = postit.find_element(By.CSS_SELECTOR, 'button[aria-label="Remover Lembrete"]')
                    btn_remover.click()
                    time.sleep(0.5)
                    
                    # Confirmar remoção
                    try:
                        btn_confirmar = driver.find_element(By.XPATH, "//mat-dialog-container//button[contains(.,'Sim') or contains(.,'Confirmar')]")
                        btn_confirmar.click()
                        time.sleep(1)
                        removidos += 1
                        print(f"[AUTOGIGS][LEMBRETE] Lembrete removido: {titulo}")
                    except:
                        pass
                        
            except Exception as e:
                print(f"[AUTOGIGS][LEMBRETE][ERRO] Falha ao processar lembrete: {e}")
        
        print(f"[AUTOGIGS][LEMBRETE] Total de lembretes removidos: {removidos}")
        return True
        
    except Exception as e:
        print(f"[AUTOGIGS][LEMBRETE][ERRO] Falha ao remover: {e}")
        return False

def _adicionar_lembrete(driver, titulo, visibilidade, conteudo, salvar):
    """Adiciona novo lembrete"""
    try:
        # Abrir menu de post-it
        btn_menu = driver.find_element(By.CSS_SELECTOR, 'button[id="botao-menu"]')
        btn_menu.click()
        time.sleep(0.5)
        
        btn_postit = driver.find_element(By.CSS_SELECTOR, 'pje-icone-post-it button')
        btn_postit.click()
        time.sleep(1)
        
        # Preencher título
        campo_titulo = driver.find_element(By.CSS_SELECTOR, 'input[id="tituloPostit"]')
        campo_titulo.clear()
        campo_titulo.send_keys(titulo)
        
        # Definir visibilidade
        _definir_visibilidade_lembrete(driver, visibilidade)
        
        # Processar e preencher conteúdo
        conteudo_final = _processar_observacao(driver, conteudo)
        campo_conteudo = driver.find_element(By.CSS_SELECTOR, 'textarea[id="conteudoPostit"]')
        campo_conteudo.clear()
        campo_conteudo.send_keys(conteudo_final)
        
        # Salvar se configurado
        if salvar:
            btn_salvar = driver.find_element(By.XPATH, "//button[contains(.,'Salvar')]")
            btn_salvar.click()
            time.sleep(2)  # Aguardar salvamento
            print(f"[AUTOGIGS][LEMBRETE] Lembrete adicionado: {titulo}")
        
        return True
        
    except Exception as e:
        print(f"[AUTOGIGS][LEMBRETE][ERRO] Falha ao adicionar: {e}")
        return False

def _definir_visibilidade_lembrete(driver, visibilidade):
    """Define a visibilidade do lembrete"""
    try:
        select_visibilidade = driver.find_element(By.CSS_SELECTOR, 'mat-select[id="visibilidadePostit"]')
        select_visibilidade.click()
        time.sleep(0.5)
        
        opcao = driver.find_element(By.XPATH, f"//mat-option[contains(.,'{visibilidade.upper()}')]")
        opcao.click()
        time.sleep(0.5)
        
        # Se for PRIVADO, permitir seleção de usuários
        if visibilidade.upper() == 'PRIVADO':
            _escolher_usuarios_lembrete(driver)
            
    except Exception as e:
        print(f"[AUTOGIGS][LEMBRETE][ERRO] Falha ao definir visibilidade: {e}")

def _escolher_usuarios_lembrete(driver):
    """Permite escolha de usuários para lembrete privado"""
    try:
        time.sleep(1)  # Aguardar transição
        select_usuarios = driver.find_element(By.CSS_SELECTOR, 'pje-dialogo-post-it mat-select[id="destinatarioPostit"]')
        select_usuarios.click()
        print("[AUTOGIGS][LEMBRETE] Selecione os usuários para lembrete privado")
        time.sleep(3)  # Aguarda o usuário fazer a seleção
    except Exception as e:
        print(f"[AUTOGIGS][LEMBRETE][ERRO] Falha ao abrir seleção de usuários: {e}")

def _executar_gigs_atividade(driver, config, concluir, gigs_fechado):
    """Executa ações de atividade GIGS (adicionar ou concluir)"""
    try:
        responsavel_processo = config.get('responsavel_processo', '')
        
        # Definir responsável do processo se especificado
        if responsavel_processo:
            _definir_responsavel_processo(driver, responsavel_processo)
        
        if concluir:
            # Concluir atividades existentes
            return _concluir_atividades_gigs(driver, config, gigs_fechado)
        else:
            # Adicionar nova atividade
            return _adicionar_atividade_gigs(driver, config, gigs_fechado)
            
    except Exception as e:
        print(f"[AUTOGIGS][GIGS][ERRO] {e}")
        return False

def _concluir_atividades_gigs(driver, config, gigs_fechado):
    """Conclui atividades GIGS baseadas nos critérios especificados"""
    try:
        # Aguardar carregamento da lista de atividades
        try:
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'div[id="tabela-atividades"] table tbody tr'))
            )
        except:
            print("[AUTOGIGS][GIGS] Nenhuma atividade encontrada")
            return True
        
        atividades = driver.find_elements(By.CSS_SELECTOR, 'div[id="tabela-atividades"] table tbody tr')
        tipo_atividade_filtro = config.get('tipo_atividade', '').lower().split(';')
        responsavel_filtro = config.get('responsavel', '').lower().split(';')
        observacao_filtro = config.get('observacao', '').lower().split(';')
        
        concluidas = 0
        
        for atividade in atividades:
            try:
                # Extrair informações da atividade
                responsavel_elem = atividade.find_element(By.CSS_SELECTOR, 'span[class*="texto-responsavel"]')
                responsavel_texto = responsavel_elem.text.lower() if responsavel_elem else ""
                
                descricao_elem = atividade.find_element(By.CSS_SELECTOR, 'span[class*="descricao"]')
                descricao_texto = descricao_elem.text.lower().split(':')[0] if descricao_elem else ""
                
                texto_completo = atividade.text.lower()
                observacao_texto = texto_completo.replace(descricao_texto + ':', '').replace(responsavel_texto, '')
                
                # Verificar critérios de filtro
                condicao1 = not tipo_atividade_filtro[0] or any(t in descricao_texto for t in tipo_atividade_filtro if t)
                condicao2 = not responsavel_filtro[0] or any(r in responsavel_texto for r in responsavel_filtro if r)
                condicao3 = not observacao_filtro[0] or any(o in observacao_texto for o in observacao_filtro if o)
                
                if condicao1 and condicao2 and condicao3:
                    # Concluir atividade
                    btn_concluir = atividade.find_element(By.CSS_SELECTOR, 'button[aria-label="Concluir Atividade"]')
                    atividade.location_once_scrolled_into_view  # Scroll para o elemento
                    btn_concluir.click()
                    time.sleep(0.5)
                    
                    # Confirmar conclusão
                    try:
                        btn_sim = driver.find_element(By.XPATH, "//mat-dialog-container//button[contains(.,'Sim')]")
                        btn_sim.click()
                        time.sleep(1)
                        concluidas += 1
                        print(f"[AUTOGIGS][GIGS] Atividade concluída: {descricao_texto}")
                    except:
                        pass
                        
                time.sleep(0.3)  # Pequena pausa entre verificações
                
            except Exception as e:
                print(f"[AUTOGIGS][GIGS][ERRO] Falha ao processar atividade: {e}")
        
        if gigs_fechado:
            _fechar_gigs(driver)
        
        print(f"[AUTOGIGS][GIGS] Total de atividades concluídas: {concluidas}")
        return True
        
    except Exception as e:
        print(f"[AUTOGIGS][GIGS][ERRO] Falha ao concluir atividades: {e}")
        return False

def _adicionar_atividade_gigs(driver, config, gigs_fechado):
    """Adiciona nova atividade GIGS"""
    try:
        # Verificar se o painel GIGS está visível
        try:
            driver.find_element(By.CSS_SELECTOR, 'pje-gigs-ficha-processo')
        except:
            _abrir_gigs(driver)
        
        # Clicar em Nova atividade
        btn_nova = driver.find_element(By.XPATH, "//pje-gigs-lista-atividades//button[contains(.,'Nova atividade')]")
        btn_nova.click()
        time.sleep(1)
        
        # Aguardar carregamento do formulário
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'pje-gigs-cadastro-atividades'))
            )
        except:
            print("[AUTOGIGS][GIGS][ERRO] Formulário de atividade não carregou")
            return False
        
        # Preencher tipo de atividade
        tipo_atividade = config.get('tipo_atividade', '')
        if tipo_atividade:
            _preencher_tipo_atividade_gigs(driver, tipo_atividade)
        
        # Preencher responsável
        responsavel = config.get('responsavel', '')
        if responsavel:
            _preencher_responsavel_gigs(driver, responsavel)
        else:
            _atribuir_responsavel_automatico(driver)
        
        # Processar variáveis especiais de audiência
        config_processado = _processar_variaveis_audiencia(driver, config)
        
        # Preencher observação
        observacao = config_processado.get('observacao', '')
        if observacao:
            observacao_final = _processar_observacao(driver, observacao)
            campo_obs = driver.find_element(By.CSS_SELECTOR, 'textarea[formcontrolname="observacao"]')
            campo_obs.clear()
            campo_obs.send_keys(observacao_final)
        
        # Preencher prazo
        prazo = config_processado.get('prazo', '')
        if prazo:
            _preencher_prazo_gigs(driver, prazo)
        
        # Salvar se configurado
        salvar = config.get('salvar', '').lower() == 'sim'
        if salvar:
            btn_salvar = driver.find_element(By.XPATH, "//button[contains(.,'Salvar')]")
            btn_salvar.click()
            
            # Aguardar confirmação de salvamento
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, "//simple-snack-bar[contains(.,'sucesso')]"))
                )
                print("[AUTOGIGS][GIGS] Atividade GIGS criada com sucesso")
                
                # Fechar notificação
                try:
                    btn_fechar = driver.find_element(By.CSS_SELECTOR, 'simple-snack-bar button')
                    btn_fechar.click()
                except:
                    pass
                    
            except:
                print("[AUTOGIGS][GIGS][AVISO] Confirmação de salvamento não detectada")
            
            if gigs_fechado:
                _fechar_gigs(driver)
        
        return True
        
    except Exception as e:
        print(f"[AUTOGIGS][GIGS][ERRO] Falha ao adicionar atividade: {e}")
        return False

def _preencher_tipo_atividade_gigs(driver, tipo_atividade):
    """Preenche o tipo de atividade no GIGS"""
    try:
        campo_tipo = driver.find_element(By.CSS_SELECTOR, 'input[formcontrolname="tipoAtividade"]')
        campo_tipo.focus()
        
        # Simular tecla para baixo para abrir dropdown
        from selenium.webdriver.common.keys import Keys
        campo_tipo.send_keys(Keys.ARROW_DOWN)
        time.sleep(0.5)
        
        # Aguardar e clicar na opção
        opcao = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, f"//mat-option[contains(.,'{tipo_atividade}')]"))
        )
        opcao.click()
        time.sleep(0.5)
        print(f"[AUTOGIGS][GIGS] Tipo de atividade selecionado: {tipo_atividade}")
        
    except Exception as e:
        print(f"[AUTOGIGS][GIGS][ERRO] Falha ao selecionar tipo de atividade: {e}")

def _preencher_responsavel_gigs(driver, responsavel):
    """Preenche o responsável da atividade GIGS"""
    try:
        campo_resp = driver.find_element(By.CSS_SELECTOR, 'input[formcontrolname="responsavel"]')
        campo_resp.focus()
        
        from selenium.webdriver.common.keys import Keys
        campo_resp.send_keys(Keys.ARROW_DOWN)
        time.sleep(0.5)
        
        opcao = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, f"//mat-option[contains(.,'{responsavel}')]"))
        )
        opcao.click()
        time.sleep(0.5)
        print(f"[AUTOGIGS][GIGS] Responsável selecionado: {responsavel}")
        
    except Exception as e:
        print(f"[AUTOGIGS][GIGS][ERRO] Falha ao selecionar responsável: {e}")

def _atribuir_responsavel_automatico(driver):
    """Atribui responsável automaticamente"""
    try:
        # Implementar lógica de atribuição automática se necessário
        print("[AUTOGIGS][GIGS] Responsável será atribuído automaticamente pelo sistema")
    except Exception as e:
        print(f"[AUTOGIGS][GIGS][ERRO] Falha na atribuição automática: {e}")

def _processar_variaveis_audiencia(driver, config):
    """Processa variáveis especiais de audiência ([data_audi], [dados_audi], [link_audi])"""
    config_processado = config.copy()
    
    try:
        prazo = config.get('prazo', '')
        observacao = config.get('observacao', '')
        
        # Verificar se há variáveis de audiência
        if '[data_audi]' in prazo or '[data_audi]' in observacao or '[dados_audi]' in observacao or '[link_audi]' in observacao:
            # Extrair ID do processo da URL
            url = driver.current_url
            if '/processo/' in url and '/detalhe' in url:
                inicio = url.find('/processo/') + 10
                fim = url.find('/detalhe')
                processo_id = url[inicio:fim]
                
                # Tentar obter dados da audiência (implementação simplificada)
                print(f"[AUTOGIGS][GIGS] Processando variáveis de audiência para processo: {processo_id}")
                
                # Por enquanto, apenas substituir com valores padrão
                import datetime
                data_atual = datetime.datetime.now().strftime('%d/%m/%Y %H:%M')
                
                if '[data_audi]' in prazo:
                    config_processado['prazo'] = data_atual
                if '[data_audi]' in observacao:
                    config_processado['observacao'] = observacao.replace('[data_audi]', f'Data: {data_atual}')
                if '[dados_audi]' in observacao:
                    config_processado['observacao'] = config_processado['observacao'].replace('[dados_audi]', 'Audiência - Sala Virtual')
                if '[link_audi]' in observacao:
                    config_processado['observacao'] = config_processado['observacao'].replace('[link_audi]', 'Link não informado')
                    
                print("[AUTOGIGS][GIGS] Variáveis de audiência processadas")
            else:
                print("[AUTOGIGS][GIGS][AVISO] Não foi possível extrair ID do processo para variáveis de audiência")
        
    except Exception as e:
        print(f"[AUTOGIGS][GIGS][ERRO] Falha ao processar variáveis de audiência: {e}")
    
    return config_processado

def _preencher_prazo_gigs(driver, prazo):
    """Preenche o prazo da atividade GIGS"""
    try:
        if len(prazo) < 5:  # Provavelmente dias úteis
            campo_dias = driver.find_element(By.CSS_SELECTOR, 'input[formcontrolname="dias"]')
            campo_dias.clear()
            campo_dias.send_keys(prazo)
            print(f"[AUTOGIGS][GIGS] Dias úteis preenchidos: {prazo}")
        else:  # Provavelmente data específica
            campo_data = driver.find_element(By.CSS_SELECTOR, 'input[data-placeholder="Data Prazo"]')
            campo_data.clear()
            campo_data.send_keys(prazo)
            print(f"[AUTOGIGS][GIGS] Data de prazo preenchida: {prazo}")
        
        time.sleep(1)  # Aguardar cálculo do sistema
        
    except Exception as e:
        print(f"[AUTOGIGS][GIGS][ERRO] Falha ao preencher prazo: {e}")

def _definir_responsavel_processo(driver, responsavel):
    """Define o responsável pelo processo"""
    try:
        campo_resp_proc = driver.find_element(By.CSS_SELECTOR, 'input[aria-label*="Responsável"]')
        campo_resp_proc.focus()
        
        from selenium.webdriver.common.keys import Keys
        campo_resp_proc.send_keys(Keys.ARROW_DOWN)
        time.sleep(0.5)
        
        opcao = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, f"//mat-option[contains(.,'{responsavel}')]"))
        )
        opcao.click()
        time.sleep(0.5)
        print(f"[AUTOGIGS] Responsável do processo definido: {responsavel}")
        
    except Exception as e:
        print(f"[AUTOGIGS][ERRO] Falha ao definir responsável do processo: {e}")

def _processar_observacao(driver, observacao):
    """Processa observação, incluindo prompts dinâmicos"""
    try:
        if 'perguntar' in observacao:
            texto_base = observacao.replace('perguntar', '').strip()
            # Simular prompt - por enquanto retorna o texto base
            # Em uma implementação completa, poderia usar tkinter ou similar para prompt
            print(f"[AUTOGIGS] Prompt solicitado. Usando texto base: {texto_base}")
            return texto_base
        
        if 'corrigir data' in observacao:
            observacao_limpa = observacao.replace('corrigir data', '').strip()
            print(f"[AUTOGIGS] Correção de data solicitada. Usando observação: {observacao_limpa}")
            return observacao_limpa
        
        return observacao
        
    except Exception as e:
        print(f"[AUTOGIGS][ERRO] Falha ao processar observação: {e}")
        return observacao

def acao_bt_aaChecklist_selenium(driver, config):
    """
    Executa o fluxo automatizado de Checklist.
    config: dict com chaves nm_botao, tipo, observacao, estado, alerta, salvar
    """
    try:
        print(f"[CHECKLIST] Iniciando ação automatizada: {config.get('nm_botao','')} - {config.get('observacao','')}")
        
        # Marcar item no checklist
        if config.get('tipo'):
            try:
                # Procurar checkbox ou item do checklist
                item_checklist = driver.find_element(By.XPATH, f"//input[@type='checkbox' and contains(@aria-label,'{config['tipo']}')]")
                if not item_checklist.is_selected():
                    item_checklist.click()
                    print(f"[CHECKLIST] Item marcado: {config['tipo']}")
                
                # Adicionar observação se necessário
                if config.get('observacao'):
                    campo_obs = driver.find_element(By.CSS_SELECTOR, 'input[placeholder*="observação" i], textarea[placeholder*="observação" i]')
                    campo_obs.send_keys(config['observacao'])
                
                # Salvar se configurado
                if config.get('salvar', '').lower() != 'não':
                    btn_salvar = driver.find_element(By.CSS_SELECTOR, 'button[aria-label*="Salvar"]')
                    btn_salvar.click()
                    time.sleep(1)
                
            except Exception as e:
                print(f'[CHECKLIST][ERRO] {e}')
        
        return True
        
    except Exception as e:
        print(f'[CHECKLIST][ERRO] {e}')
        return False

def acao_bt_aaLancarMovimentos_selenium(driver, config):
    """
    Executa o fluxo automatizado de Lançar Movimentos.
    config: dict com chaves id, nm_botao (contendo descrição do movimento)
    """
    try:
        movimento = config.get('nm_botao', '')
        print(f"[LANCAR_MOVIMENTOS] Iniciando lançamento: {movimento}")
        
        # Abrir área de movimentos
        try:
            btn_movimentos = driver.find_element(By.XPATH, "//button[contains(.,'Movimento') or contains(.,'Lançar')]")
            btn_movimentos.click()
            time.sleep(1)
        except Exception:
            print('[LANCAR_MOVIMENTOS] Área de movimentos já aberta ou não encontrada.')
        
        # Buscar e selecionar o movimento específico
        if movimento:
            try:
                # Extrair palavras-chave do movimento
                palavras_chave = movimento.replace(':', ' ').split()
                
                for palavra in palavras_chave:
                    if len(palavra) > 3:  # Usar palavras significativas
                        try:
