from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time
import json
from Fix import esperar_elemento, safe_click, colar_conteudo
from selectors_pje import BTN_TAREFA_PROCESSO

with open('botoes_maispje.json', encoding='utf-8') as f:
    botoes = json.load(f)

def add_botao_apec_selenium(driver):
    """
    Adiciona um botão flutuante na página para ativar a comunicação/expediente automatizada.
    """
    driver.execute_script('''
        if (!document.getElementById('btn-apec-auto')) {
            var btn = document.createElement('button');
            btn.id = 'btn-apec-auto';
            btn.innerText = 'Intimação/Expediente Automático';
            btn.style.position = 'fixed';
            btn.style.top = '50px';
            btn.style.right = '10px';
            btn.style.zIndex = 9999;
            btn.style.background = '#388e3c';
            btn.style.color = '#fff';
            btn.style.padding = '10px 16px';
            btn.style.border = 'none';
            btn.style.borderRadius = '6px';
            btn.style.fontSize = '16px';
            btn.onclick = function() { alert("Execute o comando Python para comunicação/expediente automático!"); };
            document.body.appendChild(btn);
        }
    ''')

def acao_bt_apec_selenium(driver, config):
    """
    Executa o fluxo automatizado de comunicação/expediente (intimação, mandado, edital, etc) na tela de minutas,
    fiel ao gigs-plugin.js (acao_bt_aaComunicacao).
    config: dict com chaves tipo_expediente, tipo_prazo, prazo, subtipo, descricao, sigilo, modelo, salvar, assinar, nm_botao, etc.
    """
    try:
        print(f"[APEC] Iniciando ação automatizada de comunicação/expediente: {config.get('tipo_expediente','')} - {config.get('modelo','')}")
        print(f"[APEC] URL atual antes de qualquer ação: {driver.current_url}")
        # Se já está na tela de minutas, não faz nada
        if '/comunicacoesprocessuais/minutas' in driver.current_url:
            print('[APEC] Já está na tela de minutas, pulando cliques iniciais.')
            # Não retorna! Continua para o preenchimento dos campos normalmente
        else:
            # 0. Copiar chave do link de validação antes de abrir a tarefa
            chave_link = None
            try:
                # Busca o botão correto pelo aria-label (ajustado para buscar o botão de copiar link de validação do documento)
                btns_copiar = driver.find_elements(By.CSS_SELECTOR, 'span[aria-label*="link de validação"] i.far.fa-copy, span[aria-label*="validação"] i.far.fa-copy')
                btn_copiar = None
                for b in btns_copiar:
                    if b.is_displayed():
                        btn_copiar = b
                        break
                if btn_copiar:
                    btn_copiar.click()
                    print('[APEC] Ícone de copiar link de validação clicado.')
                    # Tenta obter o valor do clipboard via JS (pode não funcionar em todos os browsers)
                    try:
                        chave_link = driver.execute_script('return navigator.clipboard && navigator.clipboard.readText ? navigator.clipboard.readText() : null;')
                        print(f'[APEC][DEBUG] Valor lido do clipboard: {chave_link}')
                        if not chave_link or isinstance(chave_link, type(driver.execute_script)):
                            print('[APEC][WARN] Não foi possível ler clipboard via JS. Usuário pode precisar colar manualmente.')
                            chave_link = None
                    except Exception as e:
                        print(f'[APEC][WARN] Falha ao ler clipboard via JS: {e}')
                        chave_link = None
                else:
                    print('[APEC][WARN] Botão de copiar link de validação não encontrado. (aria-label deve conter "link de validação" ou "validação")')
            except Exception as e:
                print(f'[APEC][WARN] Erro ao buscar botão de copiar link de validação: {e}')
                chave_link = None
            # 1. Abrir tarefa do processo (robusto, igual ato_judicial)
            try:
                abas_antes = set(driver.window_handles)
                btn_tarefa = esperar_elemento(driver, BTN_TAREFA_PROCESSO, timeout=15)
                if not btn_tarefa:
                    print('[APEC][ERRO] Botão "Abrir tarefa do processo" não encontrado!')
                else:
                    tarefa_texto = btn_tarefa.text.strip().lower()
                    safe_click(driver, btn_tarefa)
                    print('[APEC] Botão "Abrir tarefa do processo" clicado.')
                    # Troca para nova aba se aberta
                    for _ in range(20):
                        abas_depois = set(driver.window_handles)
                        novas_abas = abas_depois - abas_antes
                        if novas_abas:
                            nova_aba = novas_abas.pop()
                            driver.switch_to.window(nova_aba)
                            print('[APEC] Foco trocado para nova aba da tarefa do processo.')
                            # Se for "Preparar expedientes e comunicações", a nova aba já será minutas
                            if 'preparar expedientes' in tarefa_texto or 'preparar expedientes e comunicações' in tarefa_texto:
                                if '/comunicacoesprocessuais/minutas' in driver.current_url:
                                    print('[APEC] Nova aba já está em minutas após "Preparar expedientes", iniciando preenchimento dos campos.')
                                    # Espera apenas o campo de tipo de expediente, não o overlay
                                    for _ in range(20):
                                        try:
                                            campo_tipo = driver.find_element(By.CSS_SELECTOR, 'mat-select[placeholder="Tipo de Expediente"]')
                                            if campo_tipo.is_displayed():
                                                print('[APEC] Campo "Tipo de Expediente" detectado, tela pronta para preenchimento.')
                                                break
                                        except Exception:
                                            pass
                                        time.sleep(0.3)
                                    else:
                                        print('[APEC][ERRO] Timeout aguardando campo "Tipo de Expediente" na tela de minutas.')
                                        return False
                                    break
                                # Pequena espera extra caso a navegação ainda esteja ocorrendo
                                for _ in range(10):
                                    if '/comunicacoesprocessuais/minutas' in driver.current_url:
                                        print('[APEC] Navegação para minutas confirmada após "Preparar expedientes".')
                                        # Espera campo de tipo de expediente
                                        for _ in range(20):
                                            try:
                                                campo_tipo = driver.find_element(By.CSS_SELECTOR, 'mat-select[placeholder="Tipo de Expediente"]')
                                                if campo_tipo.is_displayed():
                                                    print('[APEC] Campo "Tipo de Expediente" detectado, tela pronta para preenchimento.')
                                                    break
                                            except Exception:
                                                pass
                                            time.sleep(0.3)
                                        else:
                                            print('[APEC][ERRO] Timeout aguardando campo "Tipo de Expediente" na tela de minutas.')
                                            return False
                                        break
                                    time.sleep(0.5)
                                else:
                                    print('[APEC][ERRO] Timeout aguardando navegação para minutas após "Preparar expedientes".')
                                    return False
                                break
                            # Caso contrário, segue fluxo normal (aguarda /transicao e clica em Comunicações)
                            break
                        time.sleep(0.3)
            except Exception as e:
                print(f'[APEC][ERRO] Falha ao clicar em tarefa do processo: {e}')
            # Checa novamente se já está em minutas antes de aguardar /transicao
            if '/comunicacoesprocessuais/minutas' in driver.current_url:
                print('[APEC] Já está em minutas após troca de aba, iniciando preenchimento dos campos.')
            else:
                # 2. Espera URL /transicao
                for _ in range(30):
                    if '/transicao' in driver.current_url:
                        print(f'[APEC] URL de transição confirmada: {driver.current_url}')
                        break
                    time.sleep(0.5)
                else:
                    print('[APEC][ERRO] Timeout aguardando URL de transição.')
                    return False
                # 3. Clicar em Comunicações e expedientes, com fallback para Análise
                try:
                    try:
                        btn_comunic = driver.find_element(By.XPATH, "//button[contains(@aria-label, 'Comunicações e expedientes')]")
                        btn_comunic.click()
                        print('[APEC] Botão Comunicações e expedientes clicado.')
                    except Exception:
                        print('[APEC][WARN] Botão Comunicações e expedientes não encontrado, tentando fallback Análise...')
                        btn_analise = driver.find_element(By.XPATH, "//button[contains(@aria-label, 'Análise') or .//div[contains(text(),'Análise')]]")
                        btn_analise.click()
                        print('[APEC] Botão Análise clicado para habilitar botões.')
                        time.sleep(1)
                        btn_comunic = driver.find_element(By.XPATH, "//button[contains(@aria-label, 'Comunicações e expedientes')]")
                        btn_comunic.click()
                        print('[APEC] Botão Comunicações e expedientes clicado após fallback.')
                    time.sleep(1)
                    # Espera navegação para minutas
                    for _ in range(30):
                        url_atual = driver.current_url
                        print(f"[APEC] Aguardando navegação... URL atual: {url_atual}")
                        if '/comunicacoesprocessuais/minutas' in url_atual:
                            print('[APEC] Navegação para minutas confirmada.')
                            break
                        time.sleep(0.5)
                    else:
                        print('[APEC][ERRO] Timeout aguardando navegação para minutas.')
                        return False
                except Exception as e:
                    print(f'[APEC][ERRO] Botão Comunicações e expedientes não encontrado: {e}')
                    return False
        # Passa chave_link para config para uso posterior
        if chave_link:
            config['chave_link'] = chave_link
        # 3. Preencher tipo de expediente
        tipo = config.get('tipo_expediente') or config.get('tipo') or 'Intimação'
        for tentativa in range(5):
            try:
                campo_tipo = driver.find_element(By.CSS_SELECTOR, 'mat-select[placeholder="Tipo de Expediente"]')
                campo_tipo.click()
                time.sleep(0.5)
                xpath_opcao = f"//mat-option//span[contains(text(), '{tipo}') or contains(text(), '{tipo.lower()}') or contains(text(), '{tipo.upper()}')]"
                opcao_tipo = driver.find_element(By.XPATH, xpath_opcao)
                opcao_tipo.click()
                print(f"[APEC] Tipo de expediente selecionado: {tipo}")
                time.sleep(0.5)
                break
            except Exception as e:
                msg = str(e)
                if 'cdk-overlay-backdrop' in msg or 'obscures it' in msg or 'not clickable' in msg:
                    print(f"[APEC][WARN] Overlay ou elemento não clicável, retry {tentativa+1}/5...")
                    time.sleep(1.2)
                    continue
                else:
                    print(f'[APEC][ERRO] Falha ao selecionar tipo de expediente: {e}')
                    return False
        else:
            print(f'[APEC][ERRO] Não foi possível clicar/selecionar tipo de expediente após múltiplas tentativas.')
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
                print('[APEC] Modelo selecionado na lista.')
                # Clicar no botão Inserir, como no gigs-plugin.js (aaComunicacao)
                try:
                    btns_inserir = driver.find_elements(By.XPATH, "//button[contains(.,'Inserir') or contains(@aria-label,'Inserir')]")
                    btn_inserir = None
                    for b in btns_inserir:
                        if b.is_displayed() and b.is_enabled():
                            btn_inserir = b
                            break
                    if btn_inserir:
                        btn_inserir.click()
                        print('[APEC] Botão Inserir clicado para efetivar o modelo no editor (padrão gigs-plugin.js).')
                        time.sleep(1)
                    else:
                        print('[APEC] Botão Inserir não encontrado ou não habilitado.')
                except Exception as e:
                    print(f'[APEC] Erro ao tentar clicar em Inserir: {e}')
                print('[APEC] Modelo inserido no editor.')
                # Substituição de variáveis no editor usando função modular
                if config.get('chave_link'):
                    colar_conteudo(driver, 'link', config['chave_link'])
                # Se não for para salvar, apenas retorna aqui para permitir conferência manual
                salvar = (config.get('salvar') or 'sim').lower()
                if salvar == 'não' or salvar == 'nao' or salvar == 'false' or salvar == 'n':
                    print('[APEC] Salvamento automático desativado, aguardando conferência manual do usuário.')
                    print('[APEC] Fluxo de comunicação/expediente automatizado finalizado (sem salvar).')
                    return True
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
            # Espera ato confeccionado
            try:
                for _ in range(20):
                    if driver.find_elements(By.CSS_SELECTOR, 'pje-pec-tabela-destinatarios i[aria-label="Ato confeccionado"]'):
                        print('[APEC] Ato confeccionado detectado.')
                        break
                    time.sleep(0.5)
                time.sleep(1)
            except Exception:
                print('[APEC] Não foi possível detectar ato confeccionado.')
            # Salvar expedientes
            try:
                btn_salvar_exp = driver.find_element(By.CSS_SELECTOR, 'pje-pec-tabela-destinatarios button[aria-label="Salva os expedientes"]')
                btn_salvar_exp.click()
                print('[APEC] Expedientes salvos.')
                time.sleep(1)
            except Exception as e:
                print(f'[APEC][ERRO] Salvar expedientes: {e}')
            # Assinar ato(s)
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
