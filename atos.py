# atos.py
from Fix import (
    login_pc,
    safe_click,
    esperar_elemento,
    criar_gigs,
    aplicar_filtro_100,
    limpar_temp_selenium,
    buscar_seletor_robusto,
    preencher_campos_prazo,
    # Funções adicionadas para corrigir erros
    esperar_url_conter,
    buscar_documentos_sequenciais,
    indexar_e_processar_lista  # <--- Importação adicionada
)
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def selecionar_opcao_select(driver, seletor, texto_opcao, timeout=10):
    """Seleciona uma opção em um mat-select de forma robusta, simulando o padrão do gigs-plugin.js."""
    select = WebDriverWait(driver, timeout).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, seletor))
    )
    select.send_keys(Keys.ENTER)
    WebDriverWait(driver, timeout).until(
        EC.visibility_of_element_located((By.CSS_SELECTOR, 'mat-option'))
    )
    opcoes = driver.find_elements(By.CSS_SELECTOR, 'mat-option')
    for opcao in opcoes:
        if texto_opcao.lower() in opcao.text.lower():
            opcao.click()
            return True
    raise Exception(f'Opção "{texto_opcao}" não encontrada em {seletor}!')

import os
import logging
import time
from selectors_pje import BTN_TAREFA_PROCESSO
from selenium.webdriver.common.by import By
from driver_config import criar_driver, login_func

logger = logging.getLogger(__name__)

# ====================================================
# BLOCO 1 - ATOS JUDICIAIS PADRÃO (Wrappers)
# ====================================================
def fluxo_cls(driver, conclusao_tipo, forcar_iniciar_execucao=False):
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.common.keys import Keys
    """
    Refatorado fluxo geral para CLS (movimentação de minuta):
    1. Clica no botão 'Abrir tarefa do processo' (seletor robusto mattooltip).
    2. Se estiver em 'Cumprimento de Providências', clica em 'Análise' primeiro.
    3. Clica em 'Conclusão ao Magistrado' (se não estiver já na tela de conclusão).
    4. Clica no botão do tipo de conclusão especificado.
    Retorna True em caso de sucesso, False em caso de falha.
    """
    try:
        # NOTA: A identificação da tarefa atual é feita de forma mais robusta
        # diretamente do botão "Abrir tarefa do processo" durante o clique.
        # A verificação prévia abaixo foi mantida para referência, mas pode ser removida
        # após validação em produção.
        
        """
        # 1. Verifica a tarefa atual usando seletores específicos (MÉTODO ANTIGO - PODE SER REMOVIDO)
        seletores_tarefa = [
            'pje-cabecalho-tarefa .texto-tarefa-processo',  # Novo padrão do cabeçalho
            '.descricao-tarefa button .texto-tarefa-processo',  # Estrutura completa
            'span.texto-tarefa-processo',  # Seletor simples
            'button[mattooltip="Abre a tarefa do processo"]',  # Via tooltip
            'button[aria-label*="tarefa"]'  # Via aria-label
        ]
        
        tarefa_atual = None
        seletor_funcionou = None
        print('[CLS] Testando seletores para identificar tarefa atual...')
        
        for seletor in seletores_tarefa:
            try:
                elemento = WebDriverWait(driver, 2).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, seletor))
                )
                if elemento:
                    if 'button' in seletor:
                        # Se o elemento é um botão, busca o span interno
                        spans = elemento.find_elements(By.CSS_SELECTOR, '.texto-tarefa-processo')
                        if spans:
                            tarefa_atual = spans[0].text.strip().lower()
                    else:
                        tarefa_atual = elemento.text.strip().lower()
                        
                    if tarefa_atual:
                        seletor_funcionou = seletor
                        print(f'[CLS] ✓ Tarefa identificada via seletor: {seletor}')
                        print(f'[CLS] ✓ Tarefa atual: "{tarefa_atual}"')
                        break
            except Exception as e:
                print(f'[CLS] ✗ Seletor falhou: {seletor}')
                continue
        
        if not tarefa_atual:
            print('[CLS] Tentando fallback: busca por elementos com texto de tarefa')
            elementos = driver.find_elements(By.XPATH, 
                "//*[contains(text(),'Cumprimento') or contains(text(),'Análise') or contains(text(),'Minuta')]")
            if elementos:
                tarefa_atual = elementos[0].text.strip().lower()
                seletor_funcionou = "fallback-xpath"
                print(f'[CLS] ✓ Tarefa identificada via fallback: "{tarefa_atual}"')
            
        # Se já está em Análise ou Minuta, pode prosseguir direto para conclusão
        if tarefa_atual and ('análise' in tarefa_atual or 'minuta' in tarefa_atual):
            print('[CLS] Já está em tarefa adequada para conclusão.')
        else:
            print('[CLS] Necessário navegar para tarefa adequada.')        """
        
        # 2. Clica no botão 'Abrir tarefa do processo' e captura informação da tarefa
        from Fix import esperar_elemento, safe_click
        abas_antes = set(driver.window_handles)
        btn_abrir_tarefa = esperar_elemento(driver, BTN_TAREFA_PROCESSO, timeout=15)
        if not btn_abrir_tarefa:
            logger.error('[CLS] Botão "Abrir tarefa do processo" não encontrado!')
            return False
        
        # Captura o texto da tarefa diretamente do botão antes do clique
        tarefa_do_botao = None
        try:
            # Busca span interno do botão que contém o nome da tarefa
            span_tarefa = btn_abrir_tarefa.find_element(By.CSS_SELECTOR, '.texto-tarefa-processo')
            if span_tarefa:
                tarefa_do_botao = span_tarefa.text.strip()
                print(f'[CLS] ✓ Tarefa identificada do botão: "{tarefa_do_botao}"')
        except Exception:
            # Fallback: usa o texto completo do botão
            try:
                tarefa_do_botao = btn_abrir_tarefa.text.strip()
                print(f'[CLS] ✓ Tarefa identificada (texto completo): "{tarefa_do_botao}"')
            except Exception:
                print('[CLS] ⚠ Não foi possível capturar nome da tarefa do botão')
        
        # Executa o clique e registra o resultado
        click_resultado = safe_click(driver, btn_abrir_tarefa)
        if click_resultado and tarefa_do_botao:
            print(f'[CLS] ✓ TAREFA ABERTA: "{tarefa_do_botao}"')
            print(f'[CLS] ✓ Clique bem-sucedido no botão da tarefa')
        elif click_resultado:
            print('[CLS] ✓ Clique bem-sucedido, mas nome da tarefa não capturado')
        else:
            print('[CLS] ✗ Falha no clique do botão da tarefa')
            return False

        # Troca para nova aba, se aberta, e espera carregamento completo
        nova_aba = None
        for _ in range(20):
            abas_depois = set(driver.window_handles)
            novas_abas = abas_depois - abas_antes
            if novas_abas:
                nova_aba = novas_abas.pop()
                break
            time.sleep(0.3)
        if nova_aba:
            driver.switch_to.window(nova_aba)
            print('[CLS] Foco trocado para nova aba da tarefa do processo.')
            # Espera carregamento completo da nova aba (aguarda body presente e pelo menos um botão visível)
            try:
                WebDriverWait(driver, 20).until(lambda d: d.find_element(By.TAG_NAME, 'body'))
                WebDriverWait(driver, 20).until(lambda d: len(d.find_elements(By.TAG_NAME, 'button')) > 0)
                print('[CLS] Nova aba carregada completamente.')
            except Exception as e:
                print(f'[CLS][WARN] Timeout esperando carregamento completo da nova aba: {e}')
        else:
            print('[CLS] Nenhuma nova aba detectada após clique. Prosseguindo na aba atual.')
        # NOVO: Limpa qualquer overlay/modal que possa estar interferindo
        def limpar_overlays():
            try:
                overlays = driver.find_elements(By.CSS_SELECTOR, '.cdk-overlay-backdrop, .mat-dialog-container, .cdk-overlay-container')
                if overlays:
                    from selenium.webdriver.common.keys import Keys
                    driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                    time.sleep(0.3)
                    # Re-fetch elements to avoid stale reference
                    try:
                        fresh_overlays = driver.find_elements(By.CSS_SELECTOR, '.cdk-overlay-backdrop, .mat-dialog-container, .cdk-overlay-container')
                        for overlay in fresh_overlays:
                            try:
                                if overlay.is_displayed():
                                    driver.execute_script('arguments[0].click();', overlay)
                                    time.sleep(0.2)
                            except:
                                pass
                    except:
                        pass
            except Exception as clean_err:
                logger.error(f'[CLS] Erro na limpeza de overlays: {clean_err}')
        limpar_overlays()
        
        # 3. Verifica se já está na URL de conclusão antes de tentar clicar no botão
        current_url = driver.current_url
        if '/conclusao' in current_url:
            print(f'[CLS] Já está na página de conclusão, pulando clique em "Conclusão ao magistrado"')
        else:
            # Verifica a tarefa atual pelo nome já logado
            tarefa_nome = tarefa_do_botao.strip().lower() if tarefa_do_botao else None
            if tarefa_nome:
                if 'conclusão ao magistrado' in tarefa_nome:
                    print('[CLS][INFO] Já está na tarefa "Conclusão ao magistrado". Pulando clique.')
                elif 'cumprimento de providências' in tarefa_nome:
                    print('[CLS][INFO] Detectada tarefa "Cumprimento de Providências". Clicando em "Análise" antes de conclusão.')
                    try:
                        # Primeiro tenta pelo mesmo seletor usado para conclusão ao magistrado
                        btn_analise = WebDriverWait(driver, 10).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, "button[aria-label='Análise']"))
                        )
                        btn_analise.click()
                        print('[CLS][INFO] Clique em "Análise" realizado com sucesso (aria-label exato).')
                    except Exception as e1:
                        # Fallback: busca por texto visível
                        try:
                            btns = driver.find_elements(By.XPATH, "//button[contains(normalize-space(text()), 'Análise') or .//span[contains(normalize-space(text()), 'Análise')]]")
                            btn_analise = next((b for b in btns if b.is_displayed() and b.is_enabled()), None)
                            if btn_analise:
                                btn_analise.click()
                                print('[CLS][INFO] Clique em "Análise" realizado com sucesso (texto visível).')
                            else:
                                raise Exception('Nenhum botão "Análise" disponível.')
                        except Exception as e2:
                            print(f'[CLS][WARN] Não foi possível encontrar/clicar no botão "Análise": {e1} | {e2}')
                            return False
                    time.sleep(1)
                    # Após clicar em Análise, tenta clicar em Conclusão ao magistrado
                    try:
                        btn_conclusao = WebDriverWait(driver, 10).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, "button[aria-label='Conclusão ao magistrado']"))
                        )
                        btn_conclusao.click()
                        print(f'[CLS][DEBUG] Clique no botão Conclusão ao magistrado realizado após Análise.')
                    except Exception as e:
                        print(f'[CLS][ERRO] Falha ao clicar no botão Conclusão ao magistrado após Análise: {e}')
                        return False
                else:
                    # Para qualquer outra tarefa, tenta clicar direto em Conclusão ao magistrado
                    try:
                        btn_conclusao = WebDriverWait(driver, 10).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, "button[aria-label='Conclusão ao magistrado']"))
                        )
                        btn_conclusao.click()
                        print(f'[CLS][DEBUG] Clique no botão Conclusão ao magistrado realizado. Seletor usado: button[aria-label=\'Conclusão ao magistrado\']')
                    except Exception as e:
                        print(f'[CLS][ERRO] Falha ao clicar no botão Conclusão ao magistrado: {e}')
                        return False
            else:
                print('[CLS][WARN] Não foi possível identificar a tarefa atual pelo nome do botão.')
                return False
            time.sleep(1)
            print(f'[CLS][DEBUG] Seletor de clique usado para conclusão: button[aria-label=\'Conclusão ao magistrado\']')
        # 4. Aguarda a URL mudar para /conclusao
        from Fix import esperar_url_conter
        if not esperar_url_conter(driver, '/conclusao', timeout=15):
            print(f'[CLS][ERRO] URL inesperada após clicar em conclusão: {driver.current_url}')
            return False        # 5. Clica no botão do tipo de conclusão priorizando aria-label (contém), com fallback para texto visível (contém)
        print(f'[CLS] Procurando botão de conclusão: {conclusao_tipo}')
        btn_tipo_conclusao = None
        # Primeiro tenta por aria-label que CONTÉM o tipo de conclusão
        btns = driver.find_elements(By.CSS_SELECTOR, f"button[aria-label]")
        for btn in btns:
            aria = btn.get_attribute('aria-label')
            if aria and conclusao_tipo.lower() in aria.lower():
                btn_tipo_conclusao = btn
                break
        if not btn_tipo_conclusao:
            # Fallback: tenta por texto visível (contém)
            xpath_conclusao = f"//button[contains(normalize-space(text()), '{conclusao_tipo}') or .//span[contains(normalize-space(text()), '{conclusao_tipo}')]]"
            btns = driver.find_elements(By.XPATH, xpath_conclusao)
            for btn in btns:
                if btn.is_displayed() and btn.is_enabled():
                    btn_tipo_conclusao = btn
                    break
        if not btn_tipo_conclusao:
            print(f'[CLS][ERRO] Botão de conclusão "{conclusao_tipo}" não encontrado por aria-label nem texto visível.')
            return False
        driver.execute_script('arguments[0].scrollIntoView({block: "center"});', btn_tipo_conclusao)
        time.sleep(0.3)
        driver.execute_script('arguments[0].click();', btn_tipo_conclusao)
        print(f'[CLS] Botão de conclusão "{conclusao_tipo}" clicado via JavaScript.')
        time.sleep(1)

        # 6. Aguarda a URL mudar para /minutar
        if not esperar_url_conter(driver, '/minutar', timeout=20):
            print(f'[CLS][ERRO] URL inesperada após clicar em conclusão tipo: {driver.current_url}')
            return False

        # Foco e interação no campo de filtro de modelos (padrão GIGS)
        try:
            campo_filtro_modelo = WebDriverWait(driver, 10).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, 'input#inputFiltro'))
            )
            driver.execute_script('arguments[0].removeAttribute("disabled"); arguments[0].removeAttribute("readonly");', campo_filtro_modelo)
            driver.execute_script('arguments[0].focus();', campo_filtro_modelo)
            driver.execute_script('arguments[0].value = arguments[1];', campo_filtro_modelo, "")  # Limpa campo
            driver.execute_script('var el=arguments[0]; el.dispatchEvent(new Event("input", {bubbles:true})); el.dispatchEvent(new Event("keyup", {bubbles:true}));', campo_filtro_modelo)
            print('[CLS][MODELO][OK] Foco e eventos JS realizados no campo de filtro de modelos (#inputFiltro).')
            time.sleep(0.3)
        except Exception as e:
            print(f'[CLS][MODELO][ERRO] Falha ao acessar/interagir com o campo de filtro de modelos: {e}')
            return False

        print('[CLS] Fluxo de CLS finalizado com sucesso.')
        return True
    except Exception as e:
        print(f'[CLS][ERRO] Falha no fluxo de CLS: {e}')
        try:
            driver.save_screenshot(f'erro_fluxo_cls_{conclusao_tipo}.png')
        except Exception as screen_err:
            print(f'[CLS][WARN] Falha ao salvar screenshot do erro: {screen_err}')
        return False # Indicate failure


def ato_judicial(
    driver,
    conclusao_tipo=None,
    modelo_nome=None,
    prazo=None,
    marcar_pec=None,
    movimento=None,
    gigs=None,
    marcar_primeiro_destinatario=None,
    debug=False,
    sigilo=None,
    descricao=None,  # NOVO: parâmetro para descrição
    perito=False,     # NOVO: parâmetro para ativar peritos
    Assinar=False,    # NOVO: parâmetro para ativar assinatura
    coleta_conteudo=None,  # NOVO: parâmetro para coleta de conteúdo parametrizável
    inserir_conteudo=None,  # NOVO: função opcional para inserção no editor (ex: editor_insert.inserir_link_ato_validacao)
    **kwargs
):
    """
    Fluxo generalizado para qualquer ato judicial, seguindo a ordem:
    0. Coleta de conteúdo parametrizável (PRIMEIRO PASSO - na aba /detalhe)
    1. Modelo (fluxo_cls)
    2. Descrição
    3. Sigilo
    4. PEC
    5. Prazo
    6. Movimento
    7. Assinar
    8. Função extra de sigilo (NOTA: não executada aqui, deve ser feita externamente)
    
    NOVO COMPORTAMENTO DE SIGILO:
    - A função visibilidade_sigilosos não é mais executada automaticamente
    - Deve ser executada externamente após fechar a aba e estar na URL /detalhe
    - Use executar_visibilidade_sigilosos_se_necessario(driver, sigilo_ativado)
    
    :return: (sucesso: bool, sigilo_ativado: bool)
    """
    try:
        # 0. PRIMEIRO: Executar coleta de conteúdo parametrizável na aba /detalhe (se especificado)
        if coleta_conteudo:
            print('[ATO][COLETA] Executando coleta de conteúdo parametrizável ANTES do fluxo principal...')
            try:
                # Verifica se está na aba /detalhe
                current_url = driver.current_url
                if '/detalhe' not in current_url:
                    print(f'[ATO][COLETA][WARN] URL atual não contém /detalhe: {current_url}')
                    print('[ATO][COLETA][WARN] Coleta deve ser executada na aba /detalhe')
                    
                # Importa a função do módulo de coleta
                from coleta_atos import executar_coleta_parametrizavel
                
                # Se coleta_conteudo for string, converte para dict simples
                if isinstance(coleta_conteudo, str):
                    config_coleta = {'tipo': coleta_conteudo}
                else:
                    config_coleta = coleta_conteudo
                
                # Extrai parâmetros
                tipo_coleta = config_coleta.get('tipo', '')
                parametros = config_coleta.get('parametros', None)
                
                # Tenta extrair número do processo da URL atual
                try:
                    from anexos import extrair_numero_processo_da_url
                    numero_processo = extrair_numero_processo_da_url(driver)  # Passa o driver, não a URL
                    if not numero_processo:
                        print('[ATO][COLETA][WARN] Número do processo não encontrado na URL')
                        numero_processo = "PROCESSO_DESCONHECIDO"
                except Exception as e:
                    print(f'[ATO][COLETA][ERRO] Erro na extração do número do processo: {e}')
                    numero_processo = "PROCESSO_DESCONHECIDO"
                
                # Executa a coleta
                sucesso_coleta = executar_coleta_parametrizavel(
                    driver, numero_processo, tipo_coleta, parametros, debug
                )
                
                if sucesso_coleta:
                    print(f'[ATO][COLETA] ✓ Coleta de "{tipo_coleta}" executada com sucesso ANTES do fluxo!')
                else:
                    print(f'[ATO][COLETA] ⚠ Falha na coleta de "{tipo_coleta}" (mas continua o fluxo)')
                    
            except Exception as coleta_err:
                print(f'[ATO][COLETA][ERRO] Erro na coleta de conteúdo: {coleta_err}')
                print('[ATO][COLETA] Continuando com o fluxo principal mesmo com erro na coleta...')
                # Não falha o fluxo principal por erro na coleta

        print('[ATO][DEBUG] ==========================================')
        print('[ATO][DEBUG] Iniciando fluxo principal do ato judicial...')
        
        # 1. Modelo (fluxo_cls) - EXECUTADO APENAS UMA VEZ
        sigilo_ativado = False
        print('[ATO][DEBUG] Etapa: Modelo (fluxo_cls)')
        resultado_cls = False
        if conclusao_tipo and modelo_nome:
            try:
                resultado_cls = fluxo_cls(driver, conclusao_tipo, forcar_iniciar_execucao=False)
                if not resultado_cls:
                    print('[ATO][WARN] Fluxo CLS retornou False, tentando continuar...')
                else:
                    print('[ATO][DEBUG] ✅ Fluxo CLS executado com sucesso')
            except Exception as e:
                print(f'[ATO][ERRO] Falha no fluxo CLS: {e}')
                return False, False
        
        # 2. Descrição
        if descricao:
            print(f'[ATO][DEBUG] Etapa: Descrição - {descricao}')
        else:
            print('[ATO][DEBUG] Etapa: Descrição - Nenhuma descrição especificada')
        
        print('[ATO][DEBUG] ==========================================')
        
        # 3. Sigilo (executa apenas se explicitamente True)
        sigilo_ativado = False
        if str(sigilo).lower() in ("sim", "true", "1"):
            print('[ATO][SIGILO] Etapa: Sigilo - Ativando sigilo...')
            # Lógica de sigilo seria executada aqui
            sigilo_ativado = True
        
        print('[ATO][DEBUG] ==========================================')
        
        # 4. PEC
        print('[ATO][DEBUG] Etapa: PEC')
        # LOGS INICIAIS DE DEBUG
        print(f'[ATO][ENTRADA] ================== INÍCIO ato_judicial ==================')
        print(f'[ATO][ENTRADA] conclusao_tipo: {conclusao_tipo!r}')
        print(f'[ATO][ENTRADA] modelo_nome: {modelo_nome!r}')
        print(f'[ATO][ENTRADA] prazo: {prazo!r}')
        print(f'[ATO][ENTRADA] marcar_pec: {marcar_pec!r}')
        print(f'[ATO][ENTRADA] movimento: {movimento!r}')
        print(f'[ATO][ENTRADA] descricao: {descricao!r}')
        print(f'[ATO][ENTRADA] sigilo: {sigilo!r}')
        print(f'[ATO][ENTRADA] debug: {debug!r}')
        print(f'[ATO][ENTRADA] =======================================================')
        
        # 2. Digitação do modelo e prosseguimento (padrão MaisPje/gigs-plugin.js)
        # NOTA: Só executa se fluxo_cls foi bem-sucedido OU se devemos tentar mesmo com falha
        if resultado_cls or conclusao_tipo:  # Tenta mesmo se CLS falhou
            print(f'[ATO][MODELO] Tentando preencher modelo: {modelo_nome}')
            
            try:
                from selenium.webdriver.common.by import By
                # Verifica se já estamos na tela de minuta (campo #inputFiltro existe)
                try:
                    campo_filtro_modelo = driver.find_element(By.CSS_SELECTOR, '#inputFiltro')
                    print('[ATO][MODELO] ✅ Campo #inputFiltro encontrado - já na tela de minuta')
                except:
                    print('[ATO][MODELO] ❌ Campo #inputFiltro não encontrado - não estamos na tela de minuta')
                    if not resultado_cls:
                        print('[ATO][ERRO] Fluxo CLS falhou e não estamos na tela de minuta')
                        return False
                    return False
                
                # Preenche o modelo
                driver.execute_script('arguments[0].focus();', campo_filtro_modelo)
                driver.execute_script('arguments[0].value = arguments[1];', campo_filtro_modelo, modelo_nome)
                # Dispara eventos como no gigs-plugin.js
                for ev in ['input', 'change', 'keyup']:
                    driver.execute_script('var evt = new Event(arguments[1], {bubbles:true}); arguments[0].dispatchEvent(evt);', campo_filtro_modelo, ev)
                # Simula Enter
                from selenium.webdriver.common.keys import Keys
                campo_filtro_modelo.send_keys(Keys.ENTER)
                print(f'[ATO][MODELO][OK] Modelo "{modelo_nome}" preenchido via JS e ENTER pressionado no filtro.')
                
            except Exception as modelo_err:
                print(f'[ATO][MODELO][ERRO] Erro ao preencher modelo: {modelo_err}')
                return False
        else:
            print('[ATO][MODELO] Pulando preenchimento - fluxo CLS falhou e não há conclusao_tipo')
            return False
            
        # 3. Seleciona o modelo filtrado destacado (fundo amarelo)
        try:
            seletor_item_filtrado = '.nodo-filtrado'
            nodo = esperar_elemento(driver, seletor_item_filtrado, timeout=15)
            if not nodo:
                print('[ATO][ERRO] Nodo do modelo não encontrado!')
                return False
            safe_click(driver, nodo)
            print('[ATO] Clique em nodo-filtrado realizado!')
            
            # Aguarda a caixa de visualização do modelo carregar
            seletor_btn_inserir = 'pje-dialogo-visualizar-modelo > div > div.div-preview-botoes > div.div-botao-inserir > button'
            btn_inserir = esperar_elemento(driver, seletor_btn_inserir, timeout=15)
            if not btn_inserir:
                print('[ATO][ERRO] Botão de inserir modelo não encontrado!')
                return False
            time.sleep(0.6)
            
            # Pressiona e solta ESPAÇO para inserir o modelo (padrão MaisPje)
            from selenium.webdriver.common.keys import Keys
            btn_inserir.send_keys(Keys.SPACE)
            print('[ATO] Modelo inserido pressionando ESPAÇO no botão Inserir (padrão MaisPje).')
            
        except Exception as modelo_insert_err:
            print(f'[ATO][MODELO][ERRO] Erro ao inserir modelo: {modelo_insert_err}')
            return False

        # NOVO: Hook de inserção de conteúdo (após inserir modelo, antes do Salvar)
        try:
            if inserir_conteudo:
                print('[ATO][INSERIR] Executando função de inserção de conteúdo no editor...')
                # Resolver função caso venha como string conhecida
                inserir_fn = inserir_conteudo
                if isinstance(inserir_conteudo, str):
                    try:
                        from editor_insert import inserir_link_ato_validacao
                        if inserir_conteudo.lower() in ('link_ato', 'link_ato_validacao'):
                            inserir_fn = inserir_link_ato_validacao
                    except Exception as _e:
                        print(f"[ATO][INSERIR][WARN] Não foi possível resolver função por string: {inserir_conteudo} -> {_e}")
                # Obter número do processo da URL
                try:
                    from anexos import extrair_numero_processo_da_url
                    numero_processo_atual = extrair_numero_processo_da_url(driver)
                except Exception:
                    numero_processo_atual = None
                # Chamar função de forma resiliente
                ok = False
                try:
                    ok = inserir_fn(driver=driver, numero_processo=numero_processo_atual, debug=debug)
                except TypeError:
                    try:
                        ok = inserir_fn(driver, numero_processo_atual)
                    except Exception:
                        ok = inserir_fn(driver)
                print(f"[ATO][INSERIR] Resultado da inserção: {'✓' if ok else '✗'}")
            else:
                if debug:
                    print('[ATO][INSERIR] Nenhuma função de inserção fornecida (pulando)')
        except Exception as e:
            print(f"[ATO][INSERIR][WARN] Erro ao executar inserção: {e}")

        # NOVO: Clica no botão Salvar (mat-raised-button mat-primary) e aguarda 1s para ativar aba de prazos
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        try:
            btn_salvar = WebDriverWait(driver, 15).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'mat-raised-button') and contains(@class, 'mat-primary') and contains(., 'Salvar') and @aria-label='Salvar']"))
            )
            safe_click(driver, btn_salvar)
            print('[ATO] Clique no botão Salvar realizado!')
            time.sleep(1)
        except Exception as e:
            print(f'[ATO][ERRO] Botão Salvar não encontrado ou não clicável: {e}')
            return False

        # LOGS DETALHADOS DE FLUXO
        print(f'[ATO] Iniciando etapas: Descrição → Sigilo → PEC → Prazo → Movimento → Assinar')
        
        # 1. DESCRIÇÃO (MOVIDA PARA CÁ - APÓS SALVAR, ANTES DE SIGILO)
        print('[ATO][DEBUG] ========== ETAPA 1: DESCRIÇÃO ==========')
        print(f'[ATO][DESCRICAO][DEBUG] Parâmetro descricao recebido: {descricao!r}')
        if descricao:
            print(f'[ATO][DESCRICAO][DEBUG] Tentando preencher campo de descrição com: "{descricao}"')
            try:
                # Usa apenas o seletor que está funcionando
                campo_desc = driver.find_element(By.CSS_SELECTOR, 'input[aria-label="Descrição"]')
                print(f'[ATO][DESCRICAO][DEBUG] ✓ Campo de descrição encontrado')
                
                # Limpa campo
                print(f'[ATO][DESCRICAO][DEBUG] Limpando campo de descrição...')
                campo_desc.clear()
                
                # Digita descrição
                print(f'[ATO][DESCRICAO][DEBUG] Digitando descrição: "{descricao}"')
                campo_desc.send_keys(descricao)
                
                # Dispara eventos
                print(f'[ATO][DESCRICAO][DEBUG] Disparando eventos JS...')
                for ev in ['input', 'change', 'keyup']:
                    driver.execute_script('var evt = new Event(arguments[1], {bubbles:true}); arguments[0].dispatchEvent(evt);', campo_desc, ev)
                    print(f'[ATO][DESCRICAO][DEBUG] ✓ Evento "{ev}" disparado')
                
                # Verifica se o valor foi preenchido
                valor_atual = campo_desc.get_attribute('value')
                print(f'[ATO][DESCRICAO][DEBUG] Valor atual no campo: "{valor_atual}"')
                
                if valor_atual == descricao:
                    print(f'[ATO][DESCRICAO][OK] ✓ Descrição preenchida com sucesso!')
                else:
                    print(f'[ATO][DESCRICAO][WARN] ⚠ Valor no campo não confere (esperado: "{descricao}", atual: "{valor_atual}")')
                            
            except Exception as e:
                print(f'[ATO][DESCRICAO][ERRO] ✗ Exceção ao tentar preencher descrição: {e}')
                import traceback
                traceback.print_exc()
        else:
            print('[ATO][DESCRICAO][DEBUG] Nenhuma descrição fornecida, pulando etapa.')
        
        print('[ATO][DEBUG] ==========================================')
        
        # 2. Sigilo (executa apenas se explicitamente True)
        sigilo_ativado = False
        if str(sigilo).lower() in ("sim", "true", "1"):
            try:
                # Busca toggle de sigilo
                toggles = driver.find_elements(By.CSS_SELECTOR, 'mat-slide-toggle')
                
                sigilo_toggle = None
                for toggle in toggles:
                    if 'sigilo' in toggle.text.lower():
                        sigilo_toggle = toggle
                        break
                
                if sigilo_toggle:
                    # Verifica se já está ativado
                    sigilo_input = sigilo_toggle.find_element(By.CSS_SELECTOR, 'input[type="checkbox"], input.mat-slide-toggle-input')
                    checked = sigilo_input.get_attribute('aria-checked') == 'true'
                    
                    if not checked:
                        # Clica no label do toggle
                        label = sigilo_toggle.find_element(By.CSS_SELECTOR, 'label.mat-slide-toggle-label')
                        driver.execute_script('arguments[0].click();', label)
                        time.sleep(0.5)
                        
                        # Verifica se foi ativado
                        sigilo_input_pos = sigilo_toggle.find_element(By.CSS_SELECTOR, 'input[type="checkbox"], input.mat-slide-toggle-input')
                        if sigilo_input_pos.get_attribute('aria-checked') == 'true':
                            sigilo_ativado = True
                            print('[ATO][SIGILO] Sigilo ativado com sucesso.')
                        else:
                            print('[ATO][SIGILO][ERRO] Sigilo não foi ativado.')
                    else:
                        sigilo_ativado = True
                        print('[ATO][SIGILO] Sigilo já estava ativado.')
                else:
                    print('[ATO][SIGILO][ERRO] Toggle de sigilo não encontrado.')
            except Exception as e:
                print(f'[ATO][SIGILO][ERRO] Exceção durante etapa de sigilo: {e}')
        
        print('[ATO][DEBUG] ==========================================')
        
        # 3. PEC
        print('[ATO][DEBUG] Etapa: PEC')
        if marcar_pec is not None:
            try:
                # Busca primeiro o mat-checkbox container usando múltiplos seletores
                pec_checkbox = None
                pec_input = None
                
                # Tenta encontrar o mat-checkbox pelo aria-label
                try:
                    pec_checkbox = driver.find_element(By.CSS_SELECTOR, 'mat-checkbox[aria-label="Enviar para PEC"]')
                    pec_input = pec_checkbox.find_element(By.CSS_SELECTOR, 'input[type="checkbox"]')
                except:
                    # Fallback: busca pela div container e depois o mat-checkbox
                    try:
                        pec_checkbox = driver.find_element(By.CSS_SELECTOR, 'div.checkbox-pec mat-checkbox')
                        pec_input = pec_checkbox.find_element(By.CSS_SELECTOR, 'input[type="checkbox"]')
                    except:
                        # Último fallback: busca diretamente pelo input
                        pec_input = driver.find_element(By.CSS_SELECTOR, 'input[type="checkbox"][aria-label="Enviar para PEC"]')
                        pec_checkbox = pec_input.find_element(By.XPATH, './ancestor::mat-checkbox[1]')
                
                if not pec_checkbox or not pec_input:
                    raise Exception("Não foi possível localizar o checkbox PEC")
                
                # Verifica estado atual do checkbox usando múltiplos métodos
                checked = False
                try:
                    # Método 1: aria-checked
                    aria_checked = pec_input.get_attribute('aria-checked')
                    if aria_checked == 'true':
                        checked = True
                    # Método 2: propriedade checked
                    elif pec_input.get_attribute('checked') == 'true':
                        checked = True
                    # Método 3: is_selected()
                    elif pec_input.is_selected():
                        checked = True
                    # Método 4: verificar classes CSS do mat-checkbox
                    elif 'mat-checkbox-checked' in pec_checkbox.get_attribute('class'):
                        checked = True
                except Exception as state_err:
                    print(f'[ATO][PEC][WARN] Erro ao verificar estado do checkbox: {state_err}')
                    # Em caso de erro, assume desmarcado
                    checked = False
                
                print(f'[ATO][PEC][DEBUG] Estado atual da caixa PEC: {"marcada" if checked else "desmarcada"}. Parâmetro marcar_pec: {marcar_pec}')
                
                # Executa ação baseada no estado e parâmetro
                if marcar_pec and not checked:
                    # Precisa marcar - clica no label ou mat-checkbox
                    driver.execute_script('arguments[0].scrollIntoView({block: "center"});', pec_checkbox)
                    time.sleep(0.2)
                    # Tenta clicar no label primeiro (mais confiável)
                    try:
                        label = pec_checkbox.find_element(By.CSS_SELECTOR, 'label.mat-checkbox-layout')
                        driver.execute_script('arguments[0].click();', label)
                    except:
                        # Fallback: clica no mat-checkbox
                        driver.execute_script('arguments[0].click();', pec_checkbox)
                    print('[ATO][PEC][DEBUG] Caixa PEC estava desmarcada e foi marcada.')
                    time.sleep(0.3)
                elif not marcar_pec and checked:
                    # Precisa desmarcar - clica no label ou mat-checkbox
                    driver.execute_script('arguments[0].scrollIntoView({block: "center"});', pec_checkbox)
                    time.sleep(0.2)
                    # Tenta clicar no label primeiro (mais confiável)
                    try:
                        label = pec_checkbox.find_element(By.CSS_SELECTOR, 'label.mat-checkbox-layout')
                        driver.execute_script('arguments[0].click();', label)
                    except:
                        # Fallback: clica no mat-checkbox
                        driver.execute_script('arguments[0].click();', pec_checkbox)
                    print('[ATO][PEC][DEBUG] Caixa PEC estava marcada e foi desmarcada.')
                    time.sleep(0.3)
                else:
                    print('[ATO][PEC][DEBUG] Nenhuma ação necessária na caixa PEC.')
                    
            except Exception as e:
                print(f'[ATO][ERRO] Não foi possível ajustar PEC: {e}')
                # Log adicional para debug
                try:
                    print(f'[ATO][PEC][DEBUG] URL atual: {driver.current_url}')
                    checkboxes = driver.find_elements(By.CSS_SELECTOR, 'mat-checkbox')
                    print(f'[ATO][PEC][DEBUG] Encontrados {len(checkboxes)} mat-checkbox na página')
                except:
                    pass        # 4. Prazo
        print('[ATO][DEBUG] Etapa: Prazo')
        if prazo is not None:
            try:
                print('[ATO][PRAZO] Preenchendo prazos dos destinatários...')
                preencher_prazos_destinatarios(driver, prazo, apenas_primeiro=marcar_primeiro_destinatario, perito=perito)
                
                # CLIQUE ROBUSTO NO BOTÃO GRAVAR
                print('[ATO][PRAZO] Localizando botão Gravar...')
                
                # Remover elementos obstrutivos antes do clique
                driver.execute_script("""
                    // Remove elementos que podem estar sobrepondo
                    const overlays = document.querySelectorAll('.cdk-overlay-backdrop, .mat-dialog-container, .cdk-overlay-pane');
                    overlays.forEach(overlay => {
                        if (overlay.style) overlay.style.display = 'none';
                    });
                    
                    // Remove possíveis snackbars ou notificações
                    const snackbars = document.querySelectorAll('snack-bar-container, simple-snack-bar');
                    snackbars.forEach(snack => {
                        if (snack.style) snack.style.display = 'none';
                    });
                    
                    // Garante que não há elementos flutuantes
                    document.body.style.overflow = 'visible';
                """)
                
                btn_gravar_prazo = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[.//span[normalize-space(text())='Gravar'] and contains(@class, 'mat-raised-button') and not(contains(@aria-label, 'movimentos'))]"))
                )
                
                # Verificar se o botão está visível e habilitado
                if not btn_gravar_prazo.is_displayed():
                    print('[ATO][PRAZO][ERRO] Botão Gravar não está visível')
                    return False
                    
                if not btn_gravar_prazo.is_enabled():
                    print('[ATO][PRAZO][ERRO] Botão Gravar não está habilitado')
                    return False
                
                # Scroll para garantir que está visível
                driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'center'});", btn_gravar_prazo)
                time.sleep(0.5)
                
                # Tentar clique JavaScript primeiro (mais confiável)
                try:
                    driver.execute_script("arguments[0].click();", btn_gravar_prazo)
                    print('[ATO][PRAZO] ✅ Clique via JavaScript no botão Gravar realizado')
                except Exception as js_error:
                    print(f'[ATO][PRAZO] Falha no clique JavaScript, tentando clique Selenium: {js_error}')
                    # Fallback: clique tradicional do Selenium
                    btn_gravar_prazo.click()
                    print('[ATO][PRAZO] ✅ Clique via Selenium no botão Gravar realizado')
                
                time.sleep(1)
                print('[ATO][PRAZO] Botão Gravar processado com sucesso.')
                
            except Exception as e:
                print(f'[ATO][PRAZO][ERRO] Falha ao preencher prazos ou clicar em Gravar: {e}')
                # Salvar screenshot para debug
                try:
                    driver.save_screenshot('erro_gravar_prazo.png')
                    print('[ATO][PRAZO] Screenshot salvo: erro_gravar_prazo.png')
                except:
                    pass
                return False
        else:
            print('[ATO][PRAZO] Nenhum prazo informado, etapa ignorada.')
               # 5. Movimento
        print('[ATO][DEBUG] Etapa: Movimento')
        if movimento:
            try:
                print(f'[ATO][MOVIMENTO][DEBUG] Parâmetro movimento recebido: {movimento!r}')
                # 1. JavaScript para ativar a aba Movimentos e selecionar o checkbox correto
                js_mov = f'''
                (function() {{
                    // Ativa a aba "Movimentos"
                    var tentativas = 0, abaMov = null;
                    while (tentativas < 3 && !abaMov) {{
                        var abas = Array.from(document.querySelectorAll('.mat-tab-label'));
                        abaMov = abas.find(a => a.textContent && a.textContent.normalize('NFD').replace(/[\\W_]/g, '').toLowerCase().includes('movimentos'));
                        if (abaMov && abaMov.getAttribute('aria-selected') !== 'true') {{
                            abaMov.click();
                            break;
                        }}
                        tentativas++;
                    }}
                    
                    setTimeout(function() {{
                        var textoMov = '{movimento}'.trim().toLowerCase().replace(/\\s+/g, ' ');
                        var checkboxes = Array.from(document.querySelectorAll('mat-checkbox.mat-checkbox.movimento'));
                        var selecionado = false;
                        
                        // Método mais flexível - não depende de mapeamento fixo
                        // Normaliza o texto para busca (remove acentos, etc.)
                        function normalizarTexto(texto) {{
                            return texto.normalize('NFD').replace(/[\\u0300-\\u036f]/g, '').toLowerCase().trim();
                        }}
                        
                        var termoPesquisa = normalizarTexto(textoMov);
                        console.log('[ATO][MOVIMENTO][JS][DEBUG] Termo de pesquisa normalizado:', termoPesquisa);
                          
                        for (var cb of checkboxes) {{
                            try {{
                                var label = cb.querySelector('label.mat-checkbox-layout .mat-checkbox-label');
                                var labelText = label && label.textContent ? label.textContent : '';
                                var labelNorm = labelText.trim().toLowerCase().replace(/\\s+/g, ' ');
                                var labelSemAcento = normalizarTexto(labelText);
                                
                                // DEBUG: log do label de cada movimento
                                console.log('[ATO][MOVIMENTO][JS][DEBUG] labelNorm:', labelNorm);
                                console.log('[ATO][MOVIMENTO][JS][DEBUG] labelSemAcento:', labelSemAcento);
                                
                                // Busca flexível - verifica se o termo pesquisado está contido no texto do checkbox
                                // Tenta diferentes variações de normalização para aumentar chances de match
                                var encontrado = labelNorm.includes(textoMov) || 
                                                labelSemAcento.includes(termoPesquisa) ||
                                                // Busca específica para "frustrada"/"execução frustrada"
                                                (textoMov === 'frustrada' && (labelSemAcento.includes('execucao frustrada') || labelSemAcento.includes('276'))) ||
                                                // Busca por código numérico entre parênteses, se for um número
                                                (textoMov.match(/^\\d+$/) && labelText.includes('(' + textoMov + ')'));
                                
                                if (encontrado) {{
                                    console.log('[ATO][MOVIMENTO][JS][DEBUG] Encontrado movimento correspondente para:', textoMov);
                                    var input = cb.querySelector('input[type="checkbox"]');
                                    // DEBUG: log do input encontrado
                                    console.log('[ATO][MOVIMENTO][JS][DEBUG] input encontrado:', input);
                                    if (input && !input.checked) {{
                                        // Tenta clicar na inner-container (mais confiável)
                                        var inner = cb.querySelector('.mat-checkbox-inner-container');
                                        if(inner) {{
                                            inner.click();
                                            console.log('[ATO][MOVIMENTO][JS][DEBUG] inner-container clicado para:', labelNorm);
                                        }} else {{
                                            input.click();
                                            console.log('[ATO][MOVIMENTO][JS][DEBUG] input clicado para:', labelNorm);
                                        }}
                                    }} else if (input && input.checked) {{
                                        console.log('[ATO][MOVIMENTO][JS][DEBUG] Checkbox já estava marcado:', labelNorm);
                                    }}
                                    window.selecionadoMovimento = true;  // Sinaliza para o Python que o checkbox foi encontrado
                                    window.labelSelecionadoMovimento = labelText;  // Guarda o texto do label selecionado
                                    selecionado = true;
                                    break;
                                }}
                            }} catch (e) {{
                                console.warn('[ATO][MOVIMENTO][JS][CATCH] Erro ao processar checkbox:', e);
                            }}
                        }}
                        
                        if (!selecionado) {{
                            console.warn('[ATO][MOVIMENTO][JS] Movimento "' + textoMov + '" não encontrado na lista de checkboxes.');
                            window.selecionadoMovimento = false;
                            
                            // Diagnóstico detalhado com sugestões de possíveis matches parciais
                            console.warn('[ATO][MOVIMENTO][JS][DIAGNÓSTICO] Listando todos os movimentos disponíveis:');
                            var possivelMatch = [];
                            
                            for (var idx = 0; idx < checkboxes.length; idx++) {{
                                try {{
                                    var cb = checkboxes[idx];
                                    var lbl = cb.querySelector('label.mat-checkbox-layout .mat-checkbox-label');
                                    var labelText = lbl ? lbl.textContent : 'sem label';
                                    console.warn('[ATO][MOVIMENTO][JS][DIAGNÓSTICO] [' + idx + '] ' + labelText);
                                    
                                    // Tenta identificar possíveis matches parciais para sugerir
                                    var normLabel = normalizarTexto(labelText);
                                    var palavrasTermoPesquisa = termoPesquisa.split(/\\s+/);
                                    
                                    // Conta quantas palavras do termo de pesquisa estão na label
                                    var matchCount = 0;
                                    for (var p of palavrasTermoPesquisa) {{
                                        if (p.length > 2 && normLabel.includes(p)) {{ // Ignora palavras muito curtas
                                            matchCount++;
                                        }}
                                    }}
                                    
                                    if (matchCount > 0) {{
                                        possivelMatch.push({{
                                            index: idx,
                                            label: labelText,
                                            matchCount: matchCount,
                                            matchPercentage: (matchCount / palavrasTermoPesquisa.length) * 100
                                        }});
                                    }}
                                }} catch(e) {{
                                    console.warn('[ATO][MOVIMENTO][JS][DIAGNÓSTICO] [' + idx + '] Erro ao ler: ' + e);
                                }}
                            }}
                            
                            // Ordena por quantidade de matches e mostra as melhores sugestões
                            if (possivelMatch.length > 0) {{
                                possivelMatch.sort((a, b) => b.matchPercentage - a.matchPercentage);
                                console.warn('[ATO][MOVIMENTO][JS][SUGESTÕES] Possíveis matches parciais:');
                                for (var i = 0; i < Math.min(3, possivelMatch.length); i++) {{
                                    var match = possivelMatch[i];
                                    console.warn('[ATO][MOVIMENTO][JS][SUGESTÃO ' + (i+1) + '] [' + match.index + '] ' + 
                                        match.label + ' (Match: ' + match.matchPercentage.toFixed(1) + '%)');
                                }}
                            }}
                        }} else {{
                            console.log('[ATO][MOVIMENTO][JS] Movimento "' + textoMov + '" marcado com sucesso.');
                        }}
                    }}, 800);
                }})();
                '''
                print('[ATO][MOVIMENTO][DEBUG] Executando JS para marcar movimento...')
                driver.execute_script(js_mov)
                print('[ATO][MOVIMENTO][DEBUG] JS executado. Aguardando efeito...')
                time.sleep(1.5)  # Aguarda o script JS executar
                
                # 2. Verifica se o movimento foi selecionado 
                movimento_selecionado = driver.execute_script('return window.selecionadoMovimento === true;')
                if not movimento_selecionado:
                    print('[ATO][MOVIMENTO][ERRO] Movimento não foi selecionado pelo JavaScript.')
                    return False
                
                print('[ATO][MOVIMENTO][OK] Movimento selecionado com sucesso:', 
                      driver.execute_script('return window.labelSelecionadoMovimento || "desconhecido";'))
                
                # 3. Clica no botão Gravar (para movimentos)
                print('[ATO][MOVIMENTO][DEBUG] Clicando no botão Gravar movimentos...')
                btn_gravar = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "button[aria-label='Gravar os movimentos a serem lançados']"))
                )
                btn_gravar.click()
                print('[ATO][MOVIMENTO][DEBUG] Botão Gravar movimentos clicado. Aguardando diálogo de confirmação...')
                time.sleep(1.5)
                
                # 4. Clica no botão "Sim" na caixa de diálogo de confirmação
                print('[ATO][MOVIMENTO][DEBUG] Clicando em "Sim" na caixa de diálogo de confirmação...')
                btn_sim = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'mat-button') and contains(@class, 'mat-primary') and .//span[text()='Sim']]"))
                )
                btn_sim.click()
                print('[ATO][MOVIMENTO][DEBUG] Botão "Sim" clicado na caixa de diálogo. Aguardando...')
                time.sleep(1)
                
                # 5. Clica no botão Salvar final
                print('[ATO][MOVIMENTO][DEBUG] Clicando no botão Salvar final...')
                btn_salvar_mov = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "button[aria-label='Salvar'][color='primary']"))
                )
                btn_salvar_mov.click()
                print('[ATO][MOVIMENTO][OK] Botão Salvar final clicado.')
                time.sleep(1)
            except Exception as e:
                print(f'[ATO][MOVIMENTO][ERRO] Falha ao executar etapa de movimento: {e}')
                import traceback
                traceback.print_exc()
                # Extra: dumpar checkboxes e abas para depuração
                try:
                    print('[ATO][MOVIMENTO][DEPURACAO] Listando checkboxes de movimento na página:')
                    checkboxes = driver.find_elements(By.CSS_SELECTOR, 'mat-checkbox.mat-checkbox.movimento')
                    for idx, cb in enumerate(checkboxes):
                        try:
                            label = cb.find_element(By.CSS_SELECTOR, 'label.mat-checkbox-layout .mat-checkbox-label').text
                            print(f'  [MOVIMENTO][{idx}] Label: {label!r}')
                        except Exception as ecb:
                            print(f'  [MOVIMENTO][{idx}] Erro ao obter label: {ecb}')
                    print('[ATO][MOVIMENTO][DEPURACAO] Abas disponíveis:')
                    abas = driver.find_elements(By.CSS_SELECTOR, '.mat-tab-label')
                    for idx, aba in enumerate(abas):
                        print(f'  [ABA][{idx}] Texto: {aba.text!r} | aria-selected: {aba.get_attribute("aria-selected")}')
                except Exception as edebug:
                    print(f'[ATO][MOVIMENTO][DEPURACAO][ERRO] Falha ao depurar checkboxes/abas: {edebug}')
                return False
        # 6. Assinar
        print('[ATO][DEBUG] Etapa: Assinar')
        if Assinar:
            time.sleep(3)  # Espera 3 segundos após salvamento final antes de assinar
            try:
                btn_assinar = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, 'button.mat-fab[aria-label="Enviar para assinatura"]'))
                )
                btn_assinar.click()
                print('[ATO][ASSINAR] Botão "Enviar para assinatura" clicado com sucesso.')
                time.sleep(1)
            except Exception as e:
                print(f'[ATO][ASSINAR][ERRO] Falha ao clicar no botão de assinatura: {e}')
                return False
        else:
            print('[ATO][ASSINAR] Assinatura não solicitada para este ato.')

        # 7. Salvamento final obrigatório (para persistir sigilo e outras mudanças)
        print('[ATO][DEBUG] Etapa: Salvamento final')
        if sigilo_ativado or True:  # Sempre salva no final para garantir persistência
            try:
                print('[ATO][SAVE][DEBUG] Executando salvamento final para persistir todas as mudanças...')
                btn_salvar_final = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[aria-label="Salvar"]'))
                )
                btn_salvar_final.click()
                print('[ATO][SAVE][OK] ✓ Salvamento final executado com sucesso!')
                time.sleep(1.5)  # Aguarda salvamento ser processado
            except Exception as save_err:
                print(f'[ATO][SAVE][WARN] Falha no salvamento final (não crítico): {save_err}')
                # Continua mesmo se não conseguir salvar

        # 8. Fechar aba
        # [REMOVIDO] O fechamento de aba deve ser feito apenas no fluxo de lista (ex: m1.py), nunca aqui.
        
        # Função extra de sigilo (apenas informa se foi ativado)
        print(f'[ATO] Fluxo de ato judicial ({conclusao_tipo}, {modelo_nome}) finalizado com sucesso.')
        if sigilo_ativado:
            print('[ATO][SIGILO] IMPORTANTE: Sigilo foi ativado. Execute visibilidade_sigilosos na URL /detalhe.')
        
        # RETORNA: (sucesso, sigilo_ativado) para permitir execução posterior de visibilidade_sigilosos
        return True, sigilo_ativado
    except Exception as e:
        print(f'[ATO][ERRO] Falha no fluxo do ato judicial ({conclusao_tipo}, {modelo_nome}): {e}')
        try:
            driver.save_screenshot(f'erro_ato_{conclusao_tipo}_{modelo_nome}.png')
        except Exception as screen_err:
            print(f'[ATO][WARN] Falha ao salvar screenshot do erro: {screen_err}')
        # RETORNA: (falha, sigilo_nao_ativado)
        return False, False

def executar_visibilidade_sigilosos_se_necessario(driver, sigilo_ativado, debug=False):
    """
    Executa a função visibilidade_sigilosos se sigilo foi ativado.
    NOVO: Atualiza a página com F5 antes de executar as ações de visibilidade.
    Deve ser chamada na aba /detalhe.
    
    :param driver: WebDriver
    :param sigilo_ativado: Boolean indicando se sigilo foi ativado
    :param debug: Boolean para logs detalhados
    :return: True se executou com sucesso ou não era necessário, False se falhou
    """
    if not sigilo_ativado:
        print('[VISIBILIDADE][INFO] Sigilo não foi ativado. Função visibilidade_sigilosos não necessária.')
        return True
    
    try:
        # Verifica se está na URL correta (/detalhe)
        current_url = driver.current_url
        if '/detalhe' not in current_url:
            print(f'[VISIBILIDADE][WARN] URL atual não contém /detalhe: {current_url}')
            print('[VISIBILIDADE][WARN] A função visibilidade_sigilosos deve ser executada na URL /detalhe')
        
        # NOVO: Atualiza a página com F5 como primeira ação
        print('[VISIBILIDADE][INFO] Atualizando página com F5...')
        from selenium.webdriver.common.keys import Keys
        driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.F5)
        
        # Aguarda a página recarregar
        import time
        time.sleep(3)
        print('[VISIBILIDADE][INFO] Página atualizada. Executando visibilidade_sigilosos...')
        
        # Usa a função local do atos.py que já tem tab switching e F5
        resultado = visibilidade_sigilosos(driver, log=debug)
        
        if resultado:
            print('[VISIBILIDADE][OK] ✓ Função visibilidade_sigilosos executada com sucesso.')
            return True
        else:
            print('[VISIBILIDADE][ERRO] ✗ Função visibilidade_sigilosos falhou.')
            return False
            
    except Exception as e:
        print(f'[VISIBILIDADE][ERRO] ✗ Exceção ao executar visibilidade_sigilosos: {e}')
        import traceback
        traceback.print_exc()
        return False

def make_ato_wrapper(conclusao_tipo, modelo_nome, prazo=None, marcar_pec=None, movimento=None, gigs=None, marcar_primeiro_destinatario=None, descricao=None, sigilo=None, perito=False, Assinar=False, coleta_conteudo=None, inserir_conteudo=None):
    def wrapper(driver, debug=False, sigilo_=None, movimento_=None, descricao_=None, perito_=None, Assinar_=None, coleta_conteudo_=None, inserir_conteudo_=None, **kwargs):
        call_args = dict(
            driver=driver,
            conclusao_tipo=conclusao_tipo,
            modelo_nome=modelo_nome,
            prazo=prazo,
            marcar_pec=marcar_pec,
            movimento=movimento_ if movimento_ is not None else movimento,
            gigs=gigs,
            marcar_primeiro_destinatario=marcar_primeiro_destinatario,
            debug=debug,
            sigilo=sigilo_ if sigilo_ is not None else sigilo,
            descricao=descricao_ if descricao_ is not None else descricao,
            perito=perito_ if perito_ is not None else perito,
            Assinar=Assinar_ if Assinar_ is not None else Assinar,
            coleta_conteudo=coleta_conteudo_ if coleta_conteudo_ is not None else coleta_conteudo,
            inserir_conteudo=inserir_conteudo_ if inserir_conteudo_ is not None else inserir_conteudo,
        )
        sucesso, sigilo_ativado = ato_judicial(**call_args)
        
        # Para compatibilidade com código existente, retorna apenas sucesso
        # mas armazena sigilo_ativado como atributo para acesso posterior
        wrapper.ultimo_sigilo_ativado = sigilo_ativado
        return sucesso
    return wrapper

# Wrappers gerados automaticamente
ato_meios = make_ato_wrapper(
    conclusao_tipo='Despacho',
    modelo_nome='xsmeios',
    prazo=5,
    marcar_pec=False,
    movimento=None,
    gigs=None,
    marcar_primeiro_destinatario=True,
    Assinar=True
)

ato_crda = make_ato_wrapper(
    conclusao_tipo='Despacho',
    modelo_nome='a reclda',
    prazo=8,
    marcar_pec=False,
    movimento=None,
    gigs=None,
    marcar_primeiro_destinatario=False
)

ato_crte = make_ato_wrapper(
    conclusao_tipo='Despacho',
    modelo_nome='xreit',
    prazo=8,
    marcar_pec=False,
    movimento=None,
    gigs=None,
    marcar_primeiro_destinatario=False
)

ato_bloq = make_ato_wrapper(
    conclusao_tipo='Despacho',
    modelo_nome='xsparcial',
    prazo=None,
    marcar_pec=True,
    movimento=None,
    gigs="1/SILAS/pec bloq",
    marcar_primeiro_destinatario=False
)

ato_idpj = make_ato_wrapper(
    conclusao_tipo='IDPJ',
    modelo_nome='pjsem',
    prazo=8,
    marcar_pec=True,
    movimento=None,
    gigs=None,
    marcar_primeiro_destinatario=False
)

ato_termoE = make_ato_wrapper(
    conclusao_tipo='Despacho',
    modelo_nome='xempre',
    prazo=5,
    marcar_pec=False,
    movimento=None,
    gigs=None,
    marcar_primeiro_destinatario=True
)

ato_termoS = make_ato_wrapper(
    conclusao_tipo='Despacho',
    modelo_nome='xsocio',
    prazo=5,
    marcar_pec=False,
    movimento=None,
    gigs=None,
    marcar_primeiro_destinatario=True
)

ato_edital = make_ato_wrapper(
    conclusao_tipo='Despacho',
    modelo_nome='xsedit',
    prazo=5,
    marcar_pec=False,
    movimento=None,
    gigs=None,
    marcar_primeiro_destinatario=True
)

ato_sobrestamento = make_ato_wrapper(
    conclusao_tipo='Suspensão',
    modelo_nome='suspf',
    prazo=0,
    marcar_pec=False,
    movimento='frustrada',
    gigs=None,
    marcar_primeiro_destinatario=False,
    perito=True,
    descricao='Sobrestamento',
    Assinar=True
)

ato_prov = make_ato_wrapper(
    conclusao_tipo='Suspensão',
    modelo_nome='suspprov',
    prazo=0,
    marcar_pec=False,
    movimento=None,
    gigs="1/xs sob chip (sem responsavel)",
    marcar_primeiro_destinatario=False,
    perito=False,
    descricao='Aguarda principal',
    Assinar=False
)

ato_180 = make_ato_wrapper(
    conclusao_tipo='Sobrestamento',
    modelo_nome='x180',
    prazo=0,
    marcar_pec=False,
    movimento=None,
    gigs=None,
    marcar_primeiro_destinatario=False
)

ato_x90 = make_ato_wrapper(
    conclusao_tipo='Sobrestamento',
    modelo_nome='x90',
    prazo=0,
    marcar_pec=False,
    movimento=None,
    gigs="1/xs chip rosto",
    marcar_primeiro_destinatario=False,
    descricao='Aguarda reserva'
)

ato_pesqliq = make_ato_wrapper(
    conclusao_tipo='Homologação de Cálculos',
    modelo_nome='xsbacen',
    prazo=30,
    marcar_pec=False,
    movimento=None,
    gigs=None,
    marcar_primeiro_destinatario=True,
    descricao='pesquisas para execucao',
    sigilo=True
)

# NOVO WRAPPER: ato_calc2
ato_calc2 = make_ato_wrapper(
    conclusao_tipo='Despacho',
    modelo_nome='xscalc2',
    prazo=8,
    marcar_pec=False,
    movimento=None,
    gigs=None,
    marcar_primeiro_destinatario=False
)

# NOVO WRAPPER: ato_meiosub
ato_meiosub = make_ato_wrapper(
    conclusao_tipo='Decisão Geral',
    modelo_nome='meiosub',
    prazo=None,
    marcar_pec=False,
    movimento='50071',
    gigs=None,
    marcar_primeiro_destinatario=False,
    sigilo=False
)

ato_pesquisas = make_ato_wrapper(
    conclusao_tipo='BACEN',
    modelo_nome='xsbacen',
    prazo=30,
    marcar_pec=False,
    movimento='bloqueio',
    gigs=None,
    marcar_primeiro_destinatario=True,
    descricao='Pesquisas para execução',
    sigilo=True
)

# Wrapper para prescrição intercorrente
ato_presc = make_ato_wrapper(
    conclusao_tipo='Extinção',
    modelo_nome='ao-in',
    prazo=8,
    marcar_pec=True,
    movimento='7595',
    gigs=None,
    marcar_primeiro_destinatario=False,
    descricao='Prescrição Intercorrente'
)

# Wrapper para sobrestamento por falência
ato_fal = make_ato_wrapper(
    conclusao_tipo='Sobrestamento',
    modelo_nome='xsfal',
    prazo=0,
    marcar_pec=False,
    movimento='50142',
    gigs=None,
    marcar_primeiro_destinatario=False,
    descricao='Falência'
)

# Wrapper para parcela pendente
ato_parcela = make_ato_wrapper(
    conclusao_tipo='Despacho',
    modelo_nome='xsparcof',
    prazo=12,
    marcar_pec=True,
    movimento=None,
    gigs='1/xs pec oficio',
    marcar_primeiro_destinatario=False,
    descricao='Parcela pendente',
    sigilo=False
)

ato_prev = make_ato_wrapper(
    conclusao_tipo='Despacho',
    modelo_nome='xprev',
    prazo=10,
    marcar_pec=False,
    marcar_primeiro_destinatario=True,
    descricao='tentativa prevjud'
)

# ato_pesquisas permanece manual, pois tem lógica própria
def pesquisas(driver, conclusao_tipo=None, modelo_nome=None, prazo=None, marcar_pec=None, movimento=None, gigs=None, marcar_primeiro_destinatario=None, debug=False, sigilo=True, descricao=None, Assinar=True):
    try:
        # 1. Se existir botão 'Iniciar a execução', clicar antes de seguir
        try:
            btn_iniciar = driver.find_element(By.CSS_SELECTOR, "button[aria-label*='Iniciar a execução'], button[mattooltip*='Iniciar a execução']")
            if btn_iniciar and btn_iniciar.is_displayed() and btn_iniciar.is_enabled():
                safe_click(driver, btn_iniciar)
                print('[PESQUISAS] Clique em "Iniciar a execução" realizado.')
                import time
                time.sleep(1)
        except Exception:
            print('[PESQUISAS] Botão "Iniciar a execução" não encontrado ou não clicável, seguindo fluxo normal.')
        # 2. Segue fluxo padrão do ato judicial
        sucesso, sigilo_ativado = ato_judicial(
            driver,
            conclusao_tipo='BACEN',
            modelo_nome='xsbacen',
            prazo=30,
            marcar_pec=True,
            movimento='bloqueio',
            gigs=gigs,
            marcar_primeiro_destinatario=True,
            debug=debug,
            sigilo=True,
            descricao='Pesquisas'
        )
        
        # Para compatibilidade, armazena sigilo_ativado como atributo
        pesquisas.ultimo_sigilo_ativado = sigilo_ativado
        return sucesso
    except Exception as e:
        print(f'[PESQUISAS][ERRO] Falha no fluxo do ato de pesquisas: {e}')
        try:
            driver.save_screenshot('erro_ato_pesquisas.png')
        except Exception:
            pass
        return False

# ====================================================
# BLOCO 2 - COMUNICAÇÕES PROCESSUAIS (Wrappers + Regra Geral)
# ====================================================

# Definição da regra geral de comunicação processual
def comunicacao_judicial(
    driver,
    tipo_expediente,
    prazo,
    nome_comunicacao,
    sigilo,
    modelo_nome,
    subtipo=None,
    descricao=None,
    tipo_prazo='dias uteis',
    gigs_extra=None,
    coleta_conteudo=None,  # NOVO: parâmetro para coleta de conteúdo parametrizável
    inserir_conteudo=None,  # NOVO: função opcional para inserção no editor
    cliques_polo_passivo=1,  # NOVO: número de cliques no polo passivo (padrão 1)
    debug=False
):
    """
    Fluxo generalizado para qualquer comunicação processual.
    Ordem de execução:
    0. Coleta de conteúdo parametrizável (PRIMEIRO PASSO - na aba /detalhe)
    1. Abrir tarefa do processo
    2. Comunicações e expedientes
    3. Preenchimento de formulário
    4. Seleção de destinatários
    5. Salvamento
    """
    def log(msg):
        print(f'[COMUNICACAO] {msg}')
        if debug:
            time.sleep(0.5)
            
    try:
        # 0. PRIMEIRO: Executar coleta de conteúdo parametrizável na aba /detalhe (se especificado)
        if coleta_conteudo:
            log('Executando coleta de conteúdo parametrizável ANTES do fluxo principal...')
            try:
                # Verifica se está na aba /detalhe
                current_url = driver.current_url
                if '/detalhe' not in current_url:
                    log(f'[COLETA][WARN] URL atual não contém /detalhe: {current_url}')
                    log('[COLETA][WARN] Coleta deve ser executada na aba /detalhe')
                    
                # Importa a função do módulo de coleta
                from coleta_atos import executar_coleta_parametrizavel
                
                # Se coleta_conteudo for string, converte para dict simples
                if isinstance(coleta_conteudo, str):
                    config_coleta = {'tipo': coleta_conteudo}
                else:
                    config_coleta = coleta_conteudo
                
                # Extrai parâmetros
                tipo_coleta = config_coleta.get('tipo', '')
                parametros = config_coleta.get('parametros', None)
                
                # Tenta extrair número do processo da URL atual
                try:
                    from anexos import extrair_numero_processo_da_url
                    numero_processo = extrair_numero_processo_da_url(driver)  # Passa o driver, não a URL
                    if not numero_processo:
                        log('[COLETA][WARN] Número do processo não encontrado na URL')
                        numero_processo = "PROCESSO_DESCONHECIDO"
                except Exception as e:
                    log(f'[COLETA][ERRO] Erro na extração do número do processo: {e}')
                    numero_processo = "PROCESSO_DESCONHECIDO"
                
                # Executa a coleta
                sucesso_coleta = executar_coleta_parametrizavel(
                    driver, numero_processo, tipo_coleta, parametros, debug
                )
                
                if sucesso_coleta:
                    log(f'✓ Coleta de "{tipo_coleta}" executada com sucesso ANTES do fluxo!')
                else:
                    log(f'⚠ Falha na coleta de "{tipo_coleta}" (mas continua o fluxo)')
                    
            except Exception as coleta_err:
                log(f'[ERRO] Erro na coleta de conteúdo: {coleta_err}')
                log('Continuando com o fluxo principal mesmo com erro na coleta...')
                # Não falha o fluxo principal por erro na coleta

        log('==========================================')
        log('Iniciando fluxo principal de comunicação processual...')

        # 1. FLUXO INICIAL ROBUSTO: abrir tarefa do processo e capturar informação da tarefa
        from Fix import esperar_elemento, safe_click
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selectors_pje import BTN_TAREFA_PROCESSO
        abas_antes = set(driver.window_handles)
        btn_abrir_tarefa = esperar_elemento(driver, BTN_TAREFA_PROCESSO, timeout=15)
        if not btn_abrir_tarefa:
            log('[ERRO CRÍTICO] Botão "Abrir tarefa do processo" não encontrado!')
            raise Exception('Botão tarefa do processo não encontrado')
        
        # Captura o texto da tarefa diretamente do botão antes do clique
        tarefa_do_botao = None
        try:
            # Busca span interno do botão que contém o nome da tarefa
            span_tarefa = btn_abrir_tarefa.find_element(By.CSS_SELECTOR, '.texto-tarefa-processo')
            if span_tarefa:
                tarefa_do_botao = span_tarefa.text.strip()
                log(f'✓ Tarefa identificada do botão: "{tarefa_do_botao}"')
        except Exception:
            # Fallback: usa o texto completo do botão
            try:
                tarefa_do_botao = btn_abrir_tarefa.text.strip()
                log(f'✓ Tarefa identificada (texto completo): "{tarefa_do_botao}"')
            except Exception:
                log('⚠ Não foi possível capturar nome da tarefa do botão')
        
        # Executa o clique e registra o resultado
        click_resultado = safe_click(driver, btn_abrir_tarefa)
        if click_resultado and tarefa_do_botao:
            log(f'✓ TAREFA ABERTA: "{tarefa_do_botao}"')
            log(f'✓ Clique bem-sucedido no botão da tarefa')
        elif click_resultado:
            log('✓ Clique bem-sucedido, mas nome da tarefa não capturado')
        else:
            log('✗ Falha no clique do botão da tarefa')
            raise Exception('Falha no clique do botão da tarefa')
        
        log('Botão "Abrir tarefa do processo" clicado.')
        # Troca para nova aba, se aberta, e espera carregamento completo
        nova_aba = None
        for _ in range(20):
            abas_depois = set(driver.window_handles)
            novas_abas = abas_depois - abas_antes
            if novas_abas:
                nova_aba = novas_abas.pop()
                break
            time.sleep(0.3)
        if nova_aba:
            driver.switch_to.window(nova_aba)
            log('Foco trocado para nova aba da tarefa do processo.')
            # Espera carregamento completo da nova aba (aguarda body presente e pelo menos um botão visível)
            try:
                WebDriverWait(driver, 20).until(lambda d: d.find_element(By.TAG_NAME, 'body'))
                WebDriverWait(driver, 20).until(lambda d: len(d.find_elements(By.TAG_NAME, 'button')) > 0)
                log('Nova aba carregada completamente.')
            except Exception as e:
                log(f'[WARN] Timeout esperando carregamento completo da nova aba: {e}')
        else:
            log('[WARN] Nenhuma nova aba detectada após clique. Prosseguindo na aba atual.')
        # NOVO: Limpa qualquer overlay/modal que possa estar interferindo
        def limpar_overlays():
            try:
                overlays = driver.find_elements(By.CSS_SELECTOR, '.cdk-overlay-backdrop, .mat-dialog-container, .cdk-overlay-container')
                if overlays:
                    from selenium.webdriver.common.keys import Keys
                    driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                    time.sleep(0.3)
                    # Re-fetch elements to avoid stale reference
                    try:
                        fresh_overlays = driver.find_elements(By.CSS_SELECTOR, '.cdk-overlay-backdrop, .mat-dialog-container, .cdk-overlay-container')
                        for overlay in fresh_overlays:
                            try:
                                if overlay.is_displayed():
                                    driver.execute_script('arguments[0].click();', overlay)
                                    time.sleep(0.2)
                            except:
                                pass
                    except:
                        pass
            except Exception as clean_err:
                logger.error(f'[CLS] Erro na limpeza de overlays: {clean_err}')
        limpar_overlays()
        
        # 2. LÓGICA CONDICIONAL: Verificar se já está na página correta ou precisa navegar
        # Se a tarefa identificada contém "expedientes e comunicações", já está na página correta
        if tarefa_do_botao and 'expedientes e comunicações' in tarefa_do_botao.lower():
            log('[DEBUG] ✓ Tarefa "Preparar expedientes e comunicações" identificada - já na página correta!')
            log('[DEBUG] Pulando busca pelo botão de Comunicações e expedientes...')
        else:
            # Fluxo original: buscar e clicar no botão de Comunicações e expedientes
            log('[DEBUG] Buscando botão de Comunicações e expedientes...')
            btn_comunic = None
            # 1. Por aria-label que contenha "Comunica"
            btns = driver.find_elements(By.CSS_SELECTOR, "button[aria-label]")
            for btn in btns:
                aria = btn.get_attribute('aria-label')
                if aria and 'comunica' in aria.lower():
                    if btn.is_displayed() and btn.is_enabled():
                        btn_comunic = btn
                        break
            # 2. Por texto visível (span ou button)
            if not btn_comunic:
                btns = driver.find_elements(By.XPATH, "//button[.//span[contains(translate(., 'ÁÀÂÃÉÈÊÍÏÔÕÖÚÇÑ', 'AAAAEEEIIOOOOUCN'), 'analise')]]")
                for btn in btns:
                    if btn.is_displayed() and btn.is_enabled():
                        btn_comunic = btn
                        break
            if not btn_comunic:
                # Tenta clicar em "Análise" e tenta de novo
                log('[INFO] Botão Comunicações e expedientes não encontrado. Tentando clicar em "Análise" e tentar novamente...')
                try:
                    btn_analise = None
                    # Busca botão Análise por texto
                    btns = driver.find_elements(By.XPATH, "//button[.//span[contains(translate(., 'ANÁLISE', 'análise'), 'análise')]")
                    for btn in btns:
                        if btn.is_displayed() and btn.is_enabled():
                            btn_analise = btn
                            break
                    if not btn_analise:
                        # Busca por aria-label/mattooltip
                        btns = driver.find_elements(By.CSS_SELECTOR, '*[aria-label*="Análise"]')
                        for btn in btns:
                            if btn.is_displayed() and btn.is_enabled():
                                btn_analise = btn
                                break
                        btns = driver.find_elements(By.CSS_SELECTOR, '*[mattooltip*="Análise"]')
                        for btn in btns:
                            if btn.is_displayed() and btn.is_enabled():
                                btn_analise = btn
                                break
                    if btn_analise:
                        safe_click(driver, btn_analise)
                        log('Botão "Análise" clicado para habilitar botões.')
                        time.sleep(1.2)
                    else:
                        log('[WARN] Botão "Análise" não encontrado para workaround.')
                except Exception as e:
                    log(f'[WARN] Erro ao tentar clicar em "Análise": {e}')
                # Tenta novamente buscar o botão de comunicações de forma similar à busca anterior
                # (redefinimos a lógica de busca em vez de chamar uma função inexistente)
                btn_comunic = None
                # 1. Por aria-label que contenha "Comunica"
                btns = driver.find_elements(By.CSS_SELECTOR, "button[aria-label]")
                for btn in btns:
                    aria = btn.get_attribute('aria-label')
                    if aria and 'comunica' in aria.lower():
                        if btn.is_displayed() and btn.is_enabled():
                            btn_comunic = btn
                            break
                # 2. Por texto visível (span ou button)
                if not btn_comunic:
                    btns = driver.find_elements(By.XPATH, "//button[.//span[contains(translate(., 'ÁÀÂÃÉÈÊÍÏÔÕÖÚÇÑ', 'AAAAEEEIIOOOOUCN'), 'comunicacoes')]]")
                    for btn in btns:
                        if btn.is_displayed() and btn.is_enabled():
                            btn_comunic = btn
                            break
            if not btn_comunic:
                log('[ERRO] Botão de Comunicações e expedientes (fa-envelope) não encontrado mesmo após workaround!')
                raise Exception('Botão Comunicações e expedientes não encontrado')
            safe_click(driver, btn_comunic)
            log('Botão de Comunicações e expedientes clicado.')
          ###4.Criar comunicação####
        # Aguarda a tela de minutas carregar
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        try:
            WebDriverWait(driver, 20).until(lambda d: '/minutas' in d.current_url or 'Tipo de Expediente' in d.page_source)
            log('[DEBUG] Tela de minutas carregada.')

            # 1. Selecionar o tipo de expediente
            try:
                selecionar_opcao_select(driver, 'mat-select[placeholder="Tipo de Expediente"]', tipo_expediente)
                log(f'[DEBUG] Tipo de expediente selecionado: {tipo_expediente}')
            except Exception as e:
                log(f'[ERRO] Falha ao selecionar tipo de expediente: {e}')
            # 2. Selecionar o tipo de prazo
            try:
                # Busca todos os mat-radio-button e clica via JS no que corresponde ao tipo_prazo
                radios = driver.find_elements(By.CSS_SELECTOR, 'mat-radio-button')
                found = False
                for radio in radios:
                    label = radio.get_attribute('innerText') or radio.text
                    if label and tipo_prazo.lower() in label.lower():
                        driver.execute_script("arguments[0].click();", radio)
                        found = True
                        log(f'[DEBUG] Tipo de prazo selecionado via JS: {tipo_prazo}')
                        break
                if not found:
                    log(f'[WARN] Nenhum mat-radio-button corresponde ao tipo_prazo: {tipo_prazo}')
            except Exception as e:
                log(f'[WARN] Falha ao selecionar tipo de prazo (JS): {e}')

            # 3. Preencher o prazo
            try:
                prazo = str(prazo) if prazo else ''
                # Tenta encontrar input de prazo por vários seletores
                input_prazo = None
                # 1. Tenta pelo aria-label
                try:
                    input_prazo = driver.find_element(By.CSS_SELECTOR, 'input[aria-label="Prazo em dias úteis"]')
                except Exception:
                    pass
                # 2. Se não achou, tenta por placeholder
                if not input_prazo:
                    try:
                        input_prazo = driver.find_element(By.CSS_SELECTOR, 'input[placeholder*="Prazo"]')
                    except Exception:
                        pass
                # 3. Se ainda não achou, pega o primeiro input[type="text"] visível
                if not input_prazo:
                    inputs = driver.find_elements(By.CSS_SELECTOR, 'input[type="text"]')
                    for inp in inputs:
                        if inp.is_displayed() and inp.is_enabled():
                            input_prazo = inp
                            break
                if input_prazo:
                    input_prazo.clear()
                    input_prazo.send_keys(prazo)
                    log(f'[DEBUG] Prazo preenchido: {prazo}')
                else:
                    log(f'[WARN] Nenhum input de prazo encontrado para preenchimento!')
            except Exception as e:
                log(f'[WARN] Falha ao preencher prazo: {e}')

            # 4. Clicar no botão "Confeccionar ato agrupado"
            try:
                btn_agrupado = driver.find_element(By.CSS_SELECTOR, 'button[aria-label="Confeccionar ato agrupado"]')
                safe_click(driver, btn_agrupado)
                log('[DEBUG] Botão "Confeccionar ato agrupado" clicado.')
                time.sleep(1)
            except Exception as e:
                log(f'[ERRO] Falha ao clicar em "Confeccionar ato agrupado": {e}')
            # 5. (Opcional) Escolher subtipo do expediente
            try:
                # Sempre re-busca o input após qualquer clique ou mudança de DOM
                if subtipo is None:
                    if tipo_expediente.lower() == 'intimação':
                        subtipo = "Atos em Geral"
                    elif tipo_expediente.lower() == 'edital':
                        subtipo = "Edital"
                # Re-busca input de subtipo
                subtipo_input = None
                try:
                    subtipo_input = driver.find_element(By.CSS_SELECTOR, 'input[data-placeholder="Tipo de Documento"]')
                except Exception:
                    # Tenta por placeholder genérico
                    try:
                        subtipo_input = driver.find_element(By.CSS_SELECTOR, 'input[placeholder*="Documento"]')
                    except Exception:
                        pass
                if subtipo_input:
                    subtipo_input.clear()
                    subtipo_input.send_keys(subtipo)
                    WebDriverWait(driver, 5).until(
                        EC.visibility_of_element_located((By.CSS_SELECTOR, 'mat-option'))
                    )
                    # Re-busca opções após digitar
                    opcoes = driver.find_elements(By.CSS_SELECTOR, 'mat-option')
                    found = False
                    for opcao in opcoes:
                        if subtipo.lower() in opcao.text.lower():
                            driver.execute_script("arguments[0].click();", opcao)
                            found = True
                            log(f'[DEBUG] Subtipo selecionado: {subtipo}')
                            break
                    if not found:
                        log(f'[WARN] Subtipo "{subtipo}" não encontrado!')
                else:
                    log(f'[WARN] Input de subtipo não encontrado!')
            except Exception as e:
                log(f'[WARN] Falha ao selecionar subtipo de expediente: {e}')
            # 6. (Opcional) Preencher descrição
            try:
                # Usa o parâmetro descricao ou nome_comunicacao como fallback
                desc_to_use = descricao if descricao else nome_comunicacao
                input_descricao = driver.find_element(By.CSS_SELECTOR, 'input[aria-label="Descrição"]')
                input_descricao.clear()
                input_descricao.send_keys(desc_to_use)
                log(f'[DEBUG] Descrição preenchida: {desc_to_use}')
            except Exception as e:
                log(f'[WARN] Falha ao preencher descrição: {e}')
            
            # 7. (Opcional) Marcar sigilo
            try:
                if sigilo:
                    checkbox_sigilo = driver.find_element(By.CSS_SELECTOR, 'input[name="sigiloso"]')
                    if not checkbox_sigilo.is_selected():
                        checkbox_sigilo.click()
                        log('[DEBUG] Marcado como sigiloso.')
                else:
                    log('[DEBUG] Documento não marcado como sigiloso.')
            except Exception as e:
                log(f'[WARN] Falha ao definir sigilo: {e}')
            # 8. Selecionar o modelo seguindo o padrão gigs-plugin.js como em ato_judicial
            if modelo_nome:
                log(f'Selecionando modelo: {modelo_nome}')
                # 3. Disparar eventos como no gigs-plugin.js
                campo_filtro_modelo = driver.find_element(By.CSS_SELECTOR, '#inputFiltro')
                driver.execute_script('arguments[0].focus();', campo_filtro_modelo)
                driver.execute_script('arguments[0].value = arguments[1];', campo_filtro_modelo, modelo_nome)
                for ev in ['input', 'change', 'keyup']:
                    driver.execute_script('var evt = new Event(arguments[1], {bubbles:true}); arguments[0].dispatchEvent(evt);', campo_filtro_modelo, ev)
                campo_filtro_modelo.send_keys(Keys.ENTER)
                log('[MODELO] Eventos disparados e ENTER pressionado')
                # 5. Selecionar o modelo filtrado destacado (fundo amarelo)
                seletor_item_filtrado = '.nodo-filtrado'
                nodo = esperar_elemento(driver, seletor_item_filtrado, timeout=15)
                if not nodo:
                    log('[MODELO][ERRO] Nodo do modelo não encontrado!')
                    return False
                safe_click(driver, nodo)
                log('[MODELO] Clique em nodo-filtrado realizado!')
                # 6. Aguardar a caixa de visualização do modelo carregar
                seletor_btn_inserir = 'pje-dialogo-visualizar-modelo > div > div.div-preview-botoes > div.div-botao-inserir > button'
                btn_inserir = esperar_elemento(driver, seletor_btn_inserir, timeout=15)
                if not btn_inserir:
                    log('[MODELO][ERRO] Botão de inserir modelo não encontrado!')
                    return False
                time.sleep(0.6)
                # 7. Pressionar ESPAÇO para inserir o modelo (padrão MaisPje)
                btn_inserir.send_keys(Keys.SPACE)
                log('[MODELO] Modelo inserido pressionando ESPAÇO no botão Inserir (padrão MaisPje)')

                # NOVO: Hook de inserção de conteúdo no editor (após inserir modelo, antes de Salvar)
                try:
                    if inserir_conteudo:
                        log('[INSERIR] Executando função de inserção de conteúdo...')
                        inserir_fn = inserir_conteudo
                        if isinstance(inserir_conteudo, str):
                            try:
                                from editor_insert import inserir_link_ato_validacao
                                if inserir_conteudo.lower() in ('link_ato', 'link_ato_validacao'):
                                    inserir_fn = inserir_link_ato_validacao
                            except Exception as _e:
                                log(f"[INSERIR][WARN] Não foi possível resolver função por string: {inserir_conteudo} -> {_e}")
                        # Obter número do processo
                        try:
                            from anexos import extrair_numero_processo_da_url
                            numero_processo_atual = extrair_numero_processo_da_url(driver)
                        except Exception:
                            numero_processo_atual = None
                        ok = False
                        try:
                            ok = inserir_fn(driver=driver, numero_processo=numero_processo_atual, debug=debug)
                        except TypeError:
                            try:
                                ok = inserir_fn(driver, numero_processo_atual)
                            except Exception:
                                ok = inserir_fn(driver)
                        log(f"[INSERIR] Resultado da inserção: {'✓' if ok else '✗'}")
                    else:
                        if debug:
                            log('[INSERIR] Nenhuma função de inserção fornecida (pulando)')
                except Exception as e:
                    log(f"[INSERIR][WARN] Erro ao executar inserção: {e}")
                
            # 9. Salvar e finalizar minuta com tratamento robusto
            try:
                # Primeiro salvar o documento
                log('[DEBUG] Procurando botão "Salvar"...')
                btn_salvar = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[aria-label="Salvar"]'))
                )
                
                # Usar JavaScript para garantir o clique
                log('[DEBUG] Clicando em "Salvar" via JS para maior confiabilidade')
                driver.execute_script("arguments[0].click();", btn_salvar)
                
                # Aguarda feedback visual do salvamento (snackbar ou outro indicador)
                try:
                    WebDriverWait(driver, 5).until(
                        lambda d: len(d.find_elements(By.CSS_SELECTOR, 'simple-snack-bar')) > 0
                    )
                    log('[DEBUG] Mensagem de salvamento detectada')
                    
                    # Fecha mensagens que possam estar interferindo
                    snack_bars = driver.find_elements(By.CSS_SELECTOR, 'simple-snack-bar')
                    for bar in snack_bars:
                        try:
                            fechar_btn = bar.find_element(By.TAG_NAME, 'button')
                            fechar_btn.click()
                            log('[DEBUG] Mensagem fechada')
                        except:
                            pass
                except:
                    # Continua mesmo se não encontrar confirmação visual
                    log('[DEBUG] Nenhuma mensagem de confirmação encontrada, mas prosseguindo')
                
                # Aguarda para estabilizar a UI
                time.sleep(1.5)
                
                # Agora finaliza a minuta
                log('[DEBUG] Procurando botão "Finalizar minuta"...')
                btn_finalizar = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[aria-label="Finalizar minuta"]'))
                )
                
                # Usa clique JavaScript para maior confiabilidade
                log('[DEBUG] Clicando em "Finalizar minuta" via JS')
                driver.execute_script("arguments[0].click();", btn_finalizar)
                
                # Aguarda confirmação extra
                time.sleep(2)
                log('[DEBUG] Minuta finalizada com sucesso.')
            except Exception as e:
                log(f'[ERRO] Falha ao salvar/finalizar minuta: {e}')
            # 10. (Opcional) Clique em "fa-pen" para assinar
            # Exemplo: driver.find_element(By.CSS_SELECTOR, 'button .fa-pen').click()
        except Exception as e:
            log(f'[ERRO] Falha no fluxo de preenchimento de minuta: {e}')
              # 3. De volta à tela de minutas, clicar em .pec-polo-passivo-partes-processo
        try:
            btn_pec_polo = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, '.fa.fa-user.pec-polo-passivo-partes-processo.pec-botao-intimar-polo-partes-processo'))
            )
            
            # Cliques no polo passivo conforme configurado (padrão 1, pec_idpj usa 2)
            for i in range(cliques_polo_passivo):
                btn_pec_polo.click()
                log(f'[DEBUG] Clique {i+1} de {cliques_polo_passivo} em .fa.fa-user.pec-polo-passivo-processo.pec-botao-intimar-polo-partes-processo realizado.')
                
                # Aguarda entre cliques se houver mais de um
                if i < cliques_polo_passivo - 1:
                    time.sleep(2)
                    log('[DEBUG] Aguardando 2 segundos entre os cliques.')
            
            # Maximizar a tela
            driver.maximize_window()
            log('[DEBUG] Tela maximizada.')
            
            # Aplicar zoom de 60%
            driver.execute_script("document.body.style.zoom='0.6'")
            log('[DEBUG] Zoom aplicado para 60%.')
            
        except Exception as e:
            log(f'[ERRO] Não foi possível clicar em .fa.fa-user.pec-polo-passivo-processo.pec-botao-intimar-polo-partes-processo: {e}')
            return False
        
        # 4. Aguardar carregamento (pode ser necessário aguardar algum elemento específico, aqui aguarda 1s)
        time.sleep(3)
          # 5. Clicar em <span class="mat-button-wrapper">Salvar</span>
        try:
            btn_salvar_final = None
            spans = driver.find_elements(By.XPATH, "//span[contains(@class, 'mat-button-wrapper') and normalize-space(text())='Salvar']")
            for span in spans:
                btn = span.find_element(By.XPATH, './ancestor::button[1]')
                if btn.is_displayed() and btn.is_enabled():
                    btn_salvar_final = btn
                    break
            if not btn_salvar_final:
                log('[ERRO] Botão Salvar final não encontrado!')
                return False
            btn_salvar_final.click()
            log('[DEBUG] Clique no botão Salvar final realizado.')
        except Exception as e:
            log(f'[ERRO] Não foi possível clicar no botão Salvar final: {e}')
            return False
        time.sleep(1)

        # Aguarda salvamento ser processado
        time.sleep(2)
        log('[DEBUG] Aguardando processamento do salvamento...')

        # Executa GIGS extra (gigs_minuta) se solicitado, ao final do tratamento da minuta
        if gigs_extra:
            try:
                from Fix import gigs_minuta
                # gigs_extra pode ser tupla ou dict, mas aqui espera (dias_uteis, responsavel, observacao)
                if isinstance(gigs_extra, (tuple, list)) and len(gigs_extra) >= 3:
                    dias_uteis, responsavel, observacao = gigs_extra[:3]
                    log(f'[GIGS_EXTRA] Executando gigs_minuta: {dias_uteis}, {responsavel}, {observacao}')
                    gigs_minuta(driver, dias_uteis, responsavel, observacao)
                else:
                    log(f'[GIGS_EXTRA][WARN] gigs_extra não possui formato esperado: {gigs_extra}')
            except Exception as e:
                log(f'[GIGS_EXTRA][ERRO] Falha ao executar gigs_minuta: {e}')
        
        # Visibilidade sigilosa - MOVIDA para após salvamento completo
        if str(sigilo).lower() in ("sim", "true", "1"):
            try:
                log('[COMUNICACAO] Executando visibilidade_sigilosos após salvamento...')
                # Usa a função local do atos.py que já tem tab switching e F5
                visibilidade_sigilosos(driver, log=debug)
                log('[COMUNICACAO] Visibilidade extra aplicada por sigilo positivo.')
            except Exception as e:
                log(f"[COMUNICACAO][ERRO] Falha ao aplicar visibilidade extra: {e}")
        
        # [REMOVIDO] Chamada do Infojud movida para m1.py para evitar conflitos de contexto
        # A execução do Infojud deve ser feita após todas as operações de PEC estarem completas
        
        log('Comunicação processual finalizada.')
       
        return True
    except Exception as e:
        log(f"[ERRO] Falha no fluxo de comunicação: {e}")
        # Tenta preservar contexto do browser em caso de erro
        try:
            current_handles = driver.window_handles
            if current_handles:
                # Usa primeira aba disponível se contexto ainda válido
                driver.switch_to.window(current_handles[0])
                log('[DEBUG] Contexto preservado usando primeira aba disponível após erro.')
            else:
                log('[ERRO] Contexto do browser completamente perdido.')
        except Exception as recovery_error:
            log(f"[ERRO] Contexto do browser perdido - impossível recuperar: {recovery_error}")
        return False

def make_comunicacao_wrapper(
    tipo_expediente, 
    prazo, 
    nome_comunicacao, 
    sigilo, 
    modelo_nome, 
    subtipo=None, 
    descricao=None,
    tipo_prazo='dias uteis',
    gigs_extra=None,
    coleta_conteudo=None,  # NOVO: parâmetro para coleta
    inserir_conteudo=None,  # NOVO: função opcional de inserção no editor
    cliques_polo_passivo=1  # NOVO: número de cliques no polo passivo
):
    def wrapper(driver, debug=False, coleta_conteudo_=None, inserir_conteudo_=None):
        return comunicacao_judicial(
            driver=driver,
            tipo_expediente=tipo_expediente,
            prazo=prazo,
            nome_comunicacao=nome_comunicacao,
            sigilo=sigilo,
            modelo_nome=modelo_nome,
            subtipo=subtipo,
            descricao=descricao if descricao else nome_comunicacao,
            tipo_prazo=tipo_prazo,
            gigs_extra=gigs_extra,
            coleta_conteudo=coleta_conteudo_ if coleta_conteudo_ is not None else coleta_conteudo,
            inserir_conteudo=inserir_conteudo_ if inserir_conteudo_ is not None else inserir_conteudo,
            cliques_polo_passivo=cliques_polo_passivo,
            debug=debug
        )
    return wrapper

pec_bloqueio = make_comunicacao_wrapper(
    tipo_expediente='Intimação',
    prazo=7,
    nome_comunicacao='ciência bloqueio',
    sigilo=False,
    modelo_nome='xs dec reg',
    subtipo='Intimação',  # Subtipo igual ao tipo_expediente
    gigs_extra=(7, 'xs - carta')
)
pec_decisao = make_comunicacao_wrapper(
    tipo_expediente='Intimação',
    prazo=10,
    nome_comunicacao='intimação de decisão',
    sigilo=False,
    modelo_nome='xs dec reg',
    subtipo='Intimação',  # Subtipo igual ao tipo_expediente
    gigs_extra=(7, 'xs - carta'),
    coleta_conteudo="link_ato",  # NOVO: Coleta automática de link da timeline
    inserir_conteudo='link_ato'  # NOVO: Insere link coletado no marcador '--'
)
pec_idpj = make_comunicacao_wrapper(
    tipo_expediente='Intimação',
    prazo=17,
    nome_comunicacao='defesa IDPJ',
    sigilo=False,
    modelo_nome='xidpj c',
    subtipo="Intimação",  # Adicionando subtipo explícito
    descricao="Intimação para manifestação sobre IDPJ",  # Descrição mais detalhada
    tipo_prazo='dias uteis',
    gigs_extra=(7, 'Guilherme - carta'),
    cliques_polo_passivo=2  # ESPECIAL: pec_idpj precisa de 2 cliques no polo passivo
)
pec_editalidpj = make_comunicacao_wrapper(
    tipo_expediente='Edital',
    prazo=15,
    nome_comunicacao='Defesa IDPJ',
    sigilo=False,
    modelo_nome='IDPJ (edital)',
    subtipo='Edital',  # Subtipo igual ao tipo_expediente
    gigs_extra=None
)
pec_editaldec = make_comunicacao_wrapper(
    tipo_expediente='Edital',
    prazo=8,
    nome_comunicacao='Decisão/Sentença',
    sigilo=False,
    modelo_nome='3dec',
    subtipo='Edital',  # Subtipo igual ao tipo_expediente
    gigs_extra=None,
    coleta_conteudo="link_ato",  # NOVO: Coleta automática de link da timeline
    inserir_conteudo='link_ato'  # NOVO: Insere link coletado no marcador '--'
)
pec_cpgeral = make_comunicacao_wrapper(
    tipo_expediente='Mandado',
    prazo=1,
    nome_comunicacao='Mandado CP',
    sigilo=False,
    modelo_nome='mdd cp geral',
    subtipo='Mandado',  # Subtipo igual ao tipo_expediente
    gigs_extra=None
)
pec_excluiargos = make_comunicacao_wrapper(
    tipo_expediente='Mandado',
    prazo=1,
    nome_comunicacao='Exclusão de convênios',
    sigilo=False,
    modelo_nome='asa/cnib',
    subtipo='Mandado',  # Subtipo igual ao tipo_expediente
    gigs_extra=None
)
pec_mddgeral = make_comunicacao_wrapper(
    tipo_expediente='Mandado',
    prazo=8,
    nome_comunicacao='Mandado',
    sigilo=False,
    modelo_nome='02 - gené',
    subtipo='Mandado',  # Subtipo igual ao tipo_expediente
    gigs_extra=None
)
pec_mddaud = make_comunicacao_wrapper(
    tipo_expediente='Mandado',
    prazo=1,
    nome_comunicacao='Mandado citação',
    sigilo=False,
    modelo_nome='xmdd aud',
    subtipo='Mandado',  # Subtipo igual ao tipo_expediente
    gigs_extra=None
)
pec_editalaud = make_comunicacao_wrapper(
    tipo_expediente='Edital',
    prazo=1,
    nome_comunicacao='Citação',
    sigilo=False,
    modelo_nome='1cit',
    subtipo='Edital',  # Subtipo igual ao tipo_expediente
    gigs_extra=None
)

# ====================================================
# BLOCO 3 - MOVIMENTOS (importado de mov.py)
# ====================================================

def mov(driver, seletor_alvo, texto_confirmacao=None, debug=False, timeout=15):
    """
    Fluxo geral para movimentos:
    1. Clica no botão "Abrir tarefa do processo" (BTN_TAREFA_PROCESSO)
    2. Troca para nova aba, se aberta
    3. Procura o botão alvo (seletor_alvo)
       - Se não encontrar, clica em "Análise" e tenta novamente
    4. Clica no botão alvo
    5. (Opcional) Confirma ação se texto_confirmacao for fornecido
    """
    from selenium.webdriver.common.by import By
    try:
        print(f'[MOV][DEBUG] Iniciando fluxo de movimento para seletor: {seletor_alvo}')
        btn_abrir_tarefa = esperar_elemento(driver, BTN_TAREFA_PROCESSO, timeout=timeout)
        if not btn_abrir_tarefa:
            print('[MOV][ERRO] Botão "Abrir tarefa do processo" não encontrado!')

            return False
        
        # Captura o texto da tarefa diretamente do botão antes do clique
        tarefa_do_botao = None
        try:
            # Busca span interno do botão que contém o nome da tarefa
            span_tarefa = btn_abrir_tarefa.find_element(By.CSS_SELECTOR, '.texto-tarefa-processo')
            if span_tarefa:
                tarefa_do_botao = span_tarefa.text.strip()
                print(f'[MOV] ✓ Tarefa identificada do botão: "{tarefa_do_botao}"')
        except Exception:
            # Fallback: usa o texto completo do botão
            try:
                tarefa_do_botao = btn_abrir_tarefa.text.strip()
                print(f'[MOV] ✓ Tarefa identificada (texto completo): "{tarefa_do_botao}"')
            except Exception:
                print('[MOV] ⚠ Não foi possível capturar nome da tarefa do botão')
        
        abas_antes = set(driver.window_handles)
        # Executa o clique e registra o resultado
        click_resultado = safe_click(driver, btn_abrir_tarefa)
        if click_resultado and tarefa_do_botao:
            print(f'[MOV] ✓ TAREFA ABERTA: "{tarefa_do_botao}"')
            print(f'[MOV] ✓ Clique bem-sucedido no botão da tarefa')
        elif click_resultado:
            print('[MOV] ✓ Clique bem-sucedido, mas nome da tarefa não capturado')
        else:
            print('[MOV] ✗ Falha no clique do botão da tarefa')
            return False
        
        print('[MOV] Botão "Abrir tarefa do processo" clicado.')
        # Troca para nova aba, se aberta
        nova_aba = None
        for _ in range(20):
            abas_depois = set(driver.window_handles)
            novas_abas = abas_depois - abas_antes
            if novas_abas:
                nova_aba = novas_abas.pop()
                break
            time.sleep(0.3)
        if nova_aba:
            driver.switch_to.window(nova_aba)
            print('[MOV] Foco trocado para nova aba da tarefa do processo.')
        else:
            print('[MOV][WARN] Nenhuma nova aba detectada após clique. Prosseguindo na aba atual.')
        # Procura botão alvo
        try:
            btn_alvo = WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, seletor_alvo))
            )
            safe_click(driver, btn_alvo)
            print(f'[MOV] Botão alvo ({seletor_alvo}) clicado.')
        except Exception:
            # Tenta clicar em "Análise" e tenta novamente
            print('[MOV][INFO] Botão alvo não encontrado. Tentando clicar em "Análise" e tentar novamente...')
            btn_analise = None
            # Busca por texto
            btns_analise = driver.find_elements(By.XPATH, "//button[contains(translate(normalize-space(text()), 'ANÁLISE', 'análise'), 'análise')]")
            for btn in btns_analise:
                if btn.is_displayed() and btn.is_enabled():
                    btn_analise = btn
                    break
            if not btn_analise:
                btns_analise = driver.find_elements(By.CSS_SELECTOR, "button[aria-label*='Análise']")
                for btn in btns_analise:
                    if btn.is_displayed() and btn.is_enabled():
                        btn_analise = btn
                        break
            if btn_analise:
                btn_analise.click()
                print('[MOV][DEBUG] Clique no botão "Análise" realizado.')
                time.sleep(1)
                btn_alvo = WebDriverWait(driver, timeout).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, seletor_alvo))
                )
                safe_click(driver, btn_alvo)
                print(f'[MOV] Botão alvo ({seletor_alvo}) clicado após "Análise".')
            else:
                print('[MOV][ERRO] Botão "Análise" não encontrado no fluxo alternativo.')
                return False        # Confirmação/log final
        if texto_confirmacao:
            try:
                btn_confirma = WebDriverWait(driver, timeout).until(
                    EC.element_to_be_clickable((By.XPATH, f"//button[contains(., '{texto_confirmacao}') or .//span[contains(., '{texto_confirmacao}')]"))
                )
                btn_confirma.click()
                print(f'[MOV] Botão de confirmação "{texto_confirmacao}" clicado.')
            except Exception as e:
                print(f'[MOV][ERRO] Não foi possível clicar no botão de confirmação "{texto_confirmacao}": {e}')
                return False
        print('[MOV] Fluxo de movimento finalizado com sucesso.')
        return True
    except Exception as e:
        print(f'[MOV][ERRO] Falha no fluxo de movimento: {e}')
        return False

# Wrappers para movimentos específicos

def mov_arquivar(driver, debug=False):
    """Movimento: Arquivar o processo"""
    return mov(driver, "button[aria-label='Arquivar o processo']", debug=debug)

def mov_exec(driver, debug=False):
    """Movimento: Iniciar execução"""
    return mov(driver, "button[aria-label='Iniciar execução']", debug=debug)

def mov_sob(driver, numero_processo, observacao, debug=False, timeout=15):
    """
    Movimento de sobrestamento com prazo específico.
    
    Fluxo:
    1. Abre tarefa do processo (igual ao mov padrão)
    2. Executa def_chip para remover chips de prazo vencido
    3. Clica no ícone de calendário
    4. Preenche prazo em meses (extrai número da observação)
    5. Confirma com "Prosseguir"
    
    Args:
        driver: WebDriver do Selenium
        numero_processo: Número do processo
        observacao: Observação que contém o número do prazo (ex: "sob 6")
        debug: Se True, exibe logs detalhados
        timeout: Timeout para aguardar elementos
    
    Returns:
        bool: True se executado com sucesso
    """
    import re
    import time
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selectors_pje import BTN_TAREFA_PROCESSO
    
    def log_msg(msg):
        if debug:
            print(f"[MOV_SOB] {msg}")
    
    log_msg(f"Iniciando movimento de sobrestamento para processo {numero_processo}")
    log_msg(f"Observação: {observacao}")
    
    try:
        # Extrai o número da observação (ex: "sob 6" -> "6")
        numero_match = re.search(r'\bsob\s+(\d+)', observacao.lower())
        if not numero_match:
            log_msg(f"❌ Número não encontrado na observação: {observacao}")
            return False
        
        prazo_meses = numero_match.group(1)
        log_msg(f"✅ Prazo extraído: {prazo_meses} meses")
        
        # ===== ETAPA 1: ABRIR TAREFA DO PROCESSO (igual ao mov padrão) =====
        log_msg("1. Abrindo tarefa do processo...")
        
        btn_abrir_tarefa = esperar_elemento(driver, BTN_TAREFA_PROCESSO, timeout=timeout)
        if not btn_abrir_tarefa:
            log_msg("❌ Botão 'Abrir tarefa do processo' não encontrado!")
            return False
        
        # Captura o texto da tarefa antes do clique
        tarefa_do_botao = None
        try:
            span_tarefa = btn_abrir_tarefa.find_element(By.CSS_SELECTOR, '.texto-tarefa-processo')
            if span_tarefa:
                tarefa_do_botao = span_tarefa.text.strip()
                log_msg(f"✅ Tarefa identificada: '{tarefa_do_botao}'")
        except Exception:
            try:
                tarefa_do_botao = btn_abrir_tarefa.text.strip()
                log_msg(f"✅ Tarefa identificada (texto completo): '{tarefa_do_botao}'")
            except Exception:
                log_msg("⚠️ Não foi possível capturar nome da tarefa")
        
        # Clica na tarefa e troca para nova aba
        abas_antes = set(driver.window_handles)
        click_resultado = safe_click(driver, btn_abrir_tarefa)
        
        if not click_resultado:
            log_msg("❌ Falha no clique do botão da tarefa")
            return False
        
        log_msg("✅ Botão 'Abrir tarefa do processo' clicado")
        
        # Aguarda nova aba e troca para ela
        nova_aba = None
        for _ in range(20):
            abas_depois = set(driver.window_handles)
            novas_abas = abas_depois - abas_antes
            if novas_abas:
                nova_aba = novas_abas.pop()
                break
            time.sleep(0.3)
        
        if nova_aba:
            driver.switch_to.window(nova_aba)
            log_msg("✅ Foco trocado para nova aba da tarefa")
        else:
            log_msg("⚠️ Nenhuma nova aba detectada, prosseguindo na aba atual")
        
        # ===== ETAPA 2: EXECUTAR DEF_CHIP =====
        log_msg("2. Executando def_chip para remover chips de prazo vencido...")
        
        try:
            resultado_chip = def_chip(driver, numero_processo, observacao, debug=debug)
            if resultado_chip:
                log_msg("✅ def_chip executado com sucesso")
            else:
                log_msg("⚠️ def_chip não encontrou chips para remover (normal)")
        except Exception as e:
            log_msg(f"⚠️ Erro em def_chip: {e}")
            # Continua o fluxo mesmo se def_chip falhar
        
        # ===== ETAPA 3: CLICAR NO BOTÃO DE CALENDÁRIO =====
        log_msg("3. Clicando no botão de calendário para definir prazo...")
        
        try:
            # Usar o seletor correto do botão calendário completo
            btn_calendario = WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 
                    'button[mattooltip="Definir prazo para este motivo de sobrestamento"]'))
            )
            
            log_msg("✅ Botão de calendário encontrado")
            
            # Tentar diferentes formas de clique para garantir sucesso
            try:
                # Primeiro: clique direto
                btn_calendario.click()
                log_msg("✅ Clique direto no botão executado")
            except Exception:
                try:
                    # Segundo: usar JavaScript
                    driver.execute_script("arguments[0].click();", btn_calendario)
                    log_msg("✅ Clique via JavaScript executado")
                except Exception:
                    # Terceiro: clicar no ícone interno
                    icone_interno = btn_calendario.find_element(By.CSS_SELECTOR, "i.fas.fa-calendar-alt")
                    icone_interno.click()
                    log_msg("✅ Clique no ícone interno executado")
            
            # Aguardar o modal aparecer
            log_msg("Aguardando modal 'Prazo do sobrestamento' aparecer...")
            
            modal_prazo = WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "pje-dialog-prazo-sobrestamento"))
            )
            
            log_msg("✅ Modal 'Prazo do sobrestamento' encontrado!")
            
            # Aguardar o campo de meses estar disponível
            WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "input[formcontrolname='mesesPrazoControl']"))
            )
            
            log_msg("✅ Campo de meses disponível no modal")
            time.sleep(1)  # Aguarda estabilizar
            
        except Exception as e:
            log_msg(f"❌ Erro ao clicar no botão de calendário ou aguardar modal: {e}")
            log_msg("ℹ️  Tentando seletores alternativos...")
            
            # Fallback: tentar seletor genérico de ícone calendário
            try:
                icone_calendario = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "i.fas.fa-calendar-alt"))
                )
                driver.execute_script("arguments[0].click();", icone_calendario)
                log_msg("✅ Fallback: clique via JavaScript no ícone calendário")
                
                # Tentar aguardar modal novamente
                modal_prazo = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "pje-dialog-prazo-sobrestamento"))
                )
                log_msg("✅ Modal encontrado via fallback")
                
            except Exception as e2:
                log_msg(f"❌ Fallback também falhou: {e2}")
                return False
        
        # ===== ETAPA 4: PREENCHER PRAZO EM MESES =====
        log_msg(f"4. Preenchendo prazo de {prazo_meses} meses no modal...")
        
        try:
            # Usar seletor específico do campo de meses no modal
            campo_prazo = WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "input[formcontrolname='mesesPrazoControl']"))
            )
            
            log_msg("✅ Campo 'Prazo em meses' encontrado")
            
            # Limpar e preencher o campo
            campo_prazo.clear()
            campo_prazo.send_keys(prazo_meses)
            
            log_msg(f"✅ Prazo {prazo_meses} meses preenchido no campo")
            
            # Verificar se o valor foi preenchido corretamente
            valor_atual = campo_prazo.get_attribute('value')
            if valor_atual == prazo_meses:
                log_msg(f"✅ Valor {prazo_meses} confirmado no campo")
            else:
                log_msg(f"⚠️  Valor no campo: '{valor_atual}' (esperado: '{prazo_meses}')")
            
            time.sleep(0.5)
            
        except Exception as e:
            log_msg(f"❌ Erro ao preencher prazo no modal: {e}")
            log_msg("ℹ️  Tentando seletor alternativo...")
            
            # Fallback para seletor por data-placeholder
            try:
                campo_prazo_alt = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "input[data-placeholder='Prazo em meses']"))
                )
                campo_prazo_alt.clear()
                campo_prazo_alt.send_keys(prazo_meses)
                log_msg(f"✅ Fallback: Prazo {prazo_meses} meses preenchido")
            except Exception as e2:
                log_msg(f"❌ Fallback também falhou: {e2}")
                return False
        
        # ===== ETAPA 5: CONFIRMAR COM "PROSSEGUIR" =====
        log_msg("5. Confirmando com botão 'Prosseguir' do modal...")
        
        try:
            # Procurar botão "Prosseguir" especificamente no modal de prazo
            btn_prosseguir = WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable((By.XPATH, 
                    "//pje-dialog-prazo-sobrestamento//button[.//span[contains(text(), 'Prosseguir')]]"))
            )
            
            log_msg("✅ Botão 'Prosseguir' encontrado no modal")
            
            # Tentar diferentes formas de clique
            try:
                btn_prosseguir.click()
                log_msg("✅ Clique direto no botão 'Prosseguir'")
            except Exception:
                driver.execute_script("arguments[0].click();", btn_prosseguir)
                log_msg("✅ Clique via JavaScript no botão 'Prosseguir'")
            
            log_msg("Aguardando processamento do sobrestamento...")
            time.sleep(3)  # Aguarda processamento
            
            # Verificar se o modal foi fechado (indicando sucesso)
            try:
                WebDriverWait(driver, 5).until(
                    EC.invisibility_of_element_located((By.CSS_SELECTOR, "pje-dialog-prazo-sobrestamento"))
                )
                log_msg("✅ Modal fechado - processamento concluído")
            except:
                log_msg("⚠️  Modal ainda visível - pode estar processando ou houve erro")
            
        except Exception as e:
            log_msg(f"❌ Erro ao clicar em 'Prosseguir': {e}")
            log_msg("ℹ️  Tentando seletor alternativo...")
            
            # Fallback: botão genérico
            try:
                btn_prosseguir_alt = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[.//span[contains(text(), 'Prosseguir')]]"))
                )
                driver.execute_script("arguments[0].click();", btn_prosseguir_alt)
                log_msg("✅ Fallback: Clique no botão 'Prosseguir' genérico")
                time.sleep(2)
            except Exception as e2:
                log_msg(f"❌ Fallback também falhou: {e2}")
                return False
        
        log_msg("✅ Movimento de sobrestamento finalizado com sucesso!")
        return True
        
    except Exception as e:
        log_msg(f"❌ Erro geral no movimento de sobrestamento: {e}")
        return False

def mov_fimsob(driver, debug=False, timeout=15):
    """
    Movimento para encerrar sobrestamento.
    
    Fluxo:
    1. Abre tarefa do processo 
    2. Muda para aba /aguardandofinal
    3. Clica no botão "Encerrar sobrestamento"
    4. Confirma com "Sim"
    5. Fecha aba
    
    Args:
        driver: WebDriver do Selenium
        debug: Se True, exibe logs detalhados
        timeout: Timeout para aguardar elementos
    
    Returns:
        bool: True se executado com sucesso
    """
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selectors_pje import BTN_TAREFA_PROCESSO
    
    def log_msg(msg):
        if debug:
            print(f"[MOV_FIMSOB] {msg}")
    
    log_msg("Iniciando movimento para encerrar sobrestamento")
    
    try:
        # ===== ETAPA 1: ABRIR TAREFA DO PROCESSO =====
        log_msg("1. Abrindo tarefa do processo...")
        
        btn_abrir_tarefa = esperar_elemento(driver, BTN_TAREFA_PROCESSO, timeout=timeout)
        if not btn_abrir_tarefa:
            log_msg("❌ Botão 'Abrir tarefa do processo' não encontrado!")
            return False
        
        # Captura o texto da tarefa antes do clique
        try:
            span_tarefa = btn_abrir_tarefa.find_element(By.CSS_SELECTOR, '.texto-tarefa-processo')
            tarefa_do_botao = span_tarefa.text.strip() if span_tarefa else btn_abrir_tarefa.text.strip()
            log_msg(f"✅ Tarefa identificada: '{tarefa_do_botao}'")
        except Exception:
            log_msg("⚠️ Não foi possível capturar nome da tarefa")
        
        # Clica na tarefa e aguarda nova aba
        abas_antes = set(driver.window_handles)
        click_resultado = safe_click(driver, btn_abrir_tarefa)
        
        if not click_resultado:
            log_msg("❌ Falha no clique do botão da tarefa")
            return False
        
        log_msg("✅ Botão 'Abrir tarefa do processo' clicado")
        
        # ===== ETAPA 2: MUDAR PARA ABA /AGUARDANDOFINAL =====
        log_msg("2. Mudando para aba /aguardandofinal...")
        
        # Aguarda nova aba e troca para ela
        nova_aba = None
        for _ in range(20):
            abas_depois = set(driver.window_handles)
            novas_abas = abas_depois - abas_antes
            if novas_abas:
                nova_aba = novas_abas.pop()
                break
            time.sleep(0.3)
        
        if nova_aba:
            driver.switch_to.window(nova_aba)
            log_msg("✅ Foco trocado para nova aba da tarefa")
            
            # Verifica se está na URL correta
            url_atual = driver.current_url
            if '/aguardandofinal' in url_atual:
                log_msg("✅ Confirmado: aba /aguardandofinal")
            else:
                log_msg(f"⚠️ URL atual: {url_atual} (esperado: /aguardandofinal)")
        else:
            log_msg("❌ Nenhuma nova aba detectada")
            return False
        
        # ===== ETAPA 3: CLICAR EM "ENCERRAR SOBRESTAMENTO" =====
        log_msg("3. Clicando no botão 'Encerrar sobrestamento'...")
        
        try:
            btn_encerrar = WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 
                    'button[mattooltip="Encerrar sobrestamento"][aria-label="Encerrar todos os motivos de sobrestamento"]'))
            )
            btn_encerrar.click()
            log_msg("✅ Botão 'Encerrar sobrestamento' clicado")
            time.sleep(1)  # Aguarda modal de confirmação
        except Exception as e:
            log_msg(f"❌ Erro ao clicar no botão 'Encerrar sobrestamento': {e}")
            
            # Fallback: tentar por texto do botão
            try:
                log_msg("Tentando fallback por texto do botão...")
                btn_encerrar = WebDriverWait(driver, timeout).until(
                    EC.element_to_be_clickable((By.XPATH, 
                        '//button[contains(.//div[@class="texto-botao-skinny"], "Encerrar sobrestamento")]'))
                )
                btn_encerrar.click()
                log_msg("✅ Botão 'Encerrar sobrestamento' clicado (fallback)")
                time.sleep(1)
            except Exception as e2:
                log_msg(f"❌ Erro no fallback: {e2}")
                return False
        
        # ===== ETAPA 4: CONFIRMAR COM "SIM" =====
        log_msg("4. Confirmando com 'Sim'...")
        
        try:
            btn_sim = WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 
                    'button[mat-button][color="primary"] span.mat-button-wrapper'))
            )
            
            # Verifica se é realmente o botão "Sim"
            if 'Sim' in btn_sim.text:
                btn_sim.click()
                log_msg("✅ Botão 'Sim' clicado")
                time.sleep(2)  # Aguarda processamento
            else:
                # Fallback por XPath
                btn_sim = WebDriverWait(driver, timeout).until(
                    EC.element_to_be_clickable((By.XPATH, 
                        '//button[.//span[contains(text(), "Sim")]]'))
                )
                btn_sim.click()
                log_msg("✅ Botão 'Sim' clicado (fallback)")
                time.sleep(2)
                
        except Exception as e:
            log_msg(f"❌ Erro ao confirmar com 'Sim': {e}")
            return False
        
        # ===== ETAPA 5: FECHAR ABA =====
        log_msg("5. Fechando aba...")
        
        try:
            driver.close()  # Fecha aba atual
            
            # Volta para a aba principal (primeira disponível)
            abas_restantes = driver.window_handles
            if abas_restantes:
                driver.switch_to.window(abas_restantes[0])
                log_msg("✅ Aba fechada e foco retornado para aba principal")
            else:
                log_msg("⚠️ Nenhuma aba restante encontrada")
                
        except Exception as e:
            log_msg(f"❌ Erro ao fechar aba: {e}")
            # Não falha a função por erro no fechamento
        
        log_msg("✅ Movimento para encerrar sobrestamento finalizado com sucesso!")
        return True
        
    except Exception as e:
        log_msg(f"❌ Erro geral no movimento para encerrar sobrestamento: {e}")
        return False

# ====================================================
# BLOCO 4 - FLUXOS DE EXECUÇÃO E AUXILIARES
# ====================================================

def visibilidade_sigilosos(driver, polo='ativo', log=False):
    """
    Aplica visibilidade a documentos sigilosos anexados automaticamente.
    NOVO: Automaticamente troca para aba /detalhe e atualiza a página com driver.refresh().
    Sequência: Tab switch → refresh → Múltipla seleção → Primeira checkbox → Visibilidade → Salvar
    
    :param driver: A instância do WebDriver.
    :param polo: 'ativo', 'passivo', 'ambos'. Define qual polo será selecionado.
    :param log: Ativa logs detalhados.
    :return: True se executou com sucesso, False caso contrário.
    """
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    import time
    
    if log:
        print(f"[VISIBILIDADE] Iniciando atribuição de visibilidade para polo: '{polo}'")

    try:
        # NOVO: Troca para aba /detalhe se houver múltiplas abas
        if len(driver.window_handles) > 1:
            if log:
                print("[VISIBILIDADE] Múltiplas abas detectadas. Trocando para primeira aba (/detalhe)...")
            driver.switch_to.window(driver.window_handles[0])
            
            current_url = driver.current_url
            if log:
                print(f"[VISIBILIDADE] URL após trocar para primeira aba: {current_url}")
                
            if '/detalhe' in current_url:
                if log:
                    print("[VISIBILIDADE] ✓ Agora está na aba /detalhe correta")
            else:
                if log:
                    print(f"[VISIBILIDADE] ⚠ URL não contém /detalhe: {current_url}")
        else:
            current_url = driver.current_url
            if log:
                print(f"[VISIBILIDADE] Apenas uma aba. URL atual: {current_url}")
        
        # NOVO: Atualiza a página com F5 - APENAS driver.refresh()
        if log:
            print("[VISIBILIDADE] Atualizando página com driver.refresh()...")
        
        try:
            driver.refresh()
            time.sleep(3)  # Aguarda a página recarregar
            if log:
                print("[VISIBILIDADE][F5] ✓ Página atualizada com driver.refresh()")
        except Exception as refresh_err:
            if log:
                print(f"[VISIBILIDADE][F5][ERRO] Falha no refresh: {refresh_err}")
            return False
        
        # Aguarda a página estar completamente carregada
        try:
            WebDriverWait(driver, 10).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            if log:
                print("[VISIBILIDADE][F5] ✓ Página completamente carregada")
        except:
            if log:
                print("[VISIBILIDADE][F5] ⚠ Timeout aguardando carregamento completo")
        
        if log:
            print("[VISIBILIDADE] Iniciando sequência de visibilidade...")

        # 1. Ativa múltipla seleção PRIMEIRO
        if log:
            print("[VISIBILIDADE] 1. Ativando múltipla seleção...")
        try:
            btn_multi = driver.find_element(By.CSS_SELECTOR, 'button[aria-label="Exibir múltipla seleção."]')
            btn_multi.click()
            time.sleep(0.5)
            if log:
                print("[VISIBILIDADE] ✓ Múltipla seleção ativada")
        except Exception as e:
            if log:
                print(f'[VISIBILIDADE][ERRO] Falha ao ativar múltipla seleção: {e}')
            return False
            
        # 2. Clica na primeira checkbox encontrada na timeline
        if log:
            print("[VISIBILIDADE] 2. Procurando primeira checkbox na timeline...")
        try:
            primeira_checkbox = driver.find_element(By.CSS_SELECTOR, 'ul.pje-timeline mat-card mat-checkbox label')
            primeira_checkbox.click()
            time.sleep(0.5)
            if log:
                print("[VISIBILIDADE] ✓ Primeira checkbox marcada")
        except Exception as e:
            if log:
                print(f'[VISIBILIDADE][ERRO] Falha ao marcar primeira checkbox: {e}')
            return False
            
        # 3. Clica no botão de visibilidade
        if log:
            print("[VISIBILIDADE] 3. Clicando no botão de visibilidade...")
        try:
            btn_visibilidade = driver.find_element(By.CSS_SELECTOR, 'div.div-todas-atividades-em-lote button[mattooltip="Visibilidade para Sigilo"]')
            btn_visibilidade.click()
            time.sleep(1)
            if log:
                print("[VISIBILIDADE] ✓ Modal de visibilidade aberto")
        except Exception as e:
            if log:
                print(f'[VISIBILIDADE][ERRO] Falha ao clicar no botão de visibilidade: {e}')
            return False
            
        # 4. No modal, seleciona o polo desejado
        if log:
            print(f"[VISIBILIDADE] 4. Selecionando polo: {polo}")
        try:
            if polo == 'ativo':
                icones = driver.find_elements(By.CSS_SELECTOR, 'pje-data-table[nametabela="Tabela de Controle de Sigilo"] i.icone-polo-ativo')
                for icone in icones:
                    linha = icone.find_element(By.XPATH, './../../..')
                    label = linha.find_element(By.CSS_SELECTOR, 'label')
                    label.click()
            elif polo == 'passivo':
                icones = driver.find_elements(By.CSS_SELECTOR, 'pje-data-table[nametabela="Tabela de Controle de Sigilo"] i.icone-polo-passivo')
                for icone in icones:
                    linha = icone.find_element(By.XPATH, './../../..')
                    label = linha.find_element(By.CSS_SELECTOR, 'label')
                    label.click()
            elif polo == 'ambos':
                # Marca todos
                btn_todos = driver.find_element(By.CSS_SELECTOR, 'th button')
                btn_todos.click()
            if log:
                print(f"[VISIBILIDADE] ✓ Polo '{polo}' selecionado")
        except Exception as e:
            if log:
                print(f'[VISIBILIDADE][ERRO] Falha ao selecionar polo: {e}')
            return False
            
        # 5. Confirma no botão Salvar
        if log:
            print("[VISIBILIDADE] 5. Salvando configuração de visibilidade...")
        try:
            btn_salvar = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, '//button[.//span[contains(text(),"Salvar")]]'))
            )
            btn_salvar.click()
            time.sleep(1)
            if log:
                print("[VISIBILIDADE] ✓ Configuração salva")
        except Exception as e:
            if log:
                print(f'[VISIBILIDADE][ERRO] Falha ao salvar configuração: {e}')
            return False
            
        # 6. Oculta múltipla seleção
        if log:
            print("[VISIBILIDADE] 6. Ocultando múltipla seleção...")
        try:
            btn_ocultar = driver.find_element(By.CSS_SELECTOR, 'button[aria-label="Ocultar múltipla seleção."]')
            btn_ocultar.click()
            if log:
                print("[VISIBILIDADE] ✓ Múltipla seleção ocultada")
        except:
            if log:
                print("[VISIBILIDADE] ⚠ Não foi possível ocultar múltipla seleção")
            pass
            
        if log:
            print('[VISIBILIDADE] ✓ Visibilidade aplicada com sucesso!')
        return True
        
    except Exception as e:
        if log:
            print(f'[VISIBILIDADE][ERRO] Falha ao aplicar visibilidade: {e}')
        return False


# Definição do fluxo principal
def fluxo_principal(driver):
    # Navegação por clique no ícone .fa-tags
    print("[NAVEGAR] Procurando ícone .fa-tags...")
    tag_icon = esperar_elemento(driver, ".fa-tags", timeout=20)
    if not tag_icon:
        print("[ERRO] Ícone .fa-tags não encontrado!")
        return
    safe_click(driver, tag_icon)
    print("[NAVEGAR] Ícone .fa-tags clicado.")
    # Aguarda o carregamento da tela de atividades (ajuste o seletor se necessário)
    esperar_elemento(driver, ".classe-unica-da-tela-atividades", timeout=20)
    print("[OK] Na tela de atividades do GIGS. Continue o fluxo normalmente...")

def callback_ato(driver):
    # Fluxo completo de ato judicial/minuta
    preencher_campos_prazo(driver, valor=0)
    criar_gigs(driver, dias_uteis=5, observacao='Ato Judicial', tela='minuta')
    buscar_documentos_sequenciais(driver)
    print('[ATOS] Fluxo de ato judicial executado.')

def iniciar_fluxo_pec(driver):
    try:
        print("[INICIAR] Iniciando fluxo PEC...")
        # Clicar no botão "Processo Eletrônico Colaborativo (PEC)"
        safe_click(driver, '#cke_16', timeout=10)
        #safe_click(driver, 'span.cke_button_label.cke_button__pec_label', timeout=10)
        
        # Verificar e clicar no botão "Incluir PEC" se ele não estiver visível
        # incluir_pec_button = buscar_seletor_robusto(driver, 'Incluir PEC')
        # if incluir_pec_button and incluir_pec_button.is_displayed():
        #     safe_click(driver, incluir_pec_button)
        
        # safe_click(driver, 'a[title="Incluir PEC"]', timeout=10)
        safe_click(driver, 'a[title="Incluir processo eletrônico colaborativo"]', timeout=10)

        # Preencher os campos do PEC
        # ... (código para preencher os campos do PEC)
        
        # Clicar no botão "OK" para confirmar a inclusão do PEC
        safe_click(driver, '#btnOk', timeout=10)
        
        # Lógica para lidar com a lista de processos (se aplicável)
        # ...
        
        print("[INFO] Preparando lista de processos...")
        # tratar_pec = callback_ato(driver)
        
        def tratar_pec(driver):
            # Implemente a lógica específica para tratar cada PEC aqui
            # Por exemplo, preencher campos, anexar documentos, etc.
            print("[INFO] Tratando PEC...")
            
            # Exemplo: Preencher o campo de observação
            # driver.find_element(By.CSS_SELECTOR, "textarea[id*='observacoes']").send_keys("PEC processado automaticamente")
            # time.sleep(1)
            # safe_click(driver, '#cke_61', timeout=10)
            # time.sleep(1)
            return True

        if not indexar_e_processar_lista(driver, tratar_pec, seletor_btn='button[aria-label="Abrir processo"]'):
            print('[ERRO] Falha ao processar lista de PECs')

    except Exception as e:
        logger.error(f'Erro no fluxo principal: {str(e)}')
        driver.save_screenshot('screenshot_erro_fluxo.png')
        raise
    
def fluxo_sincrono_processo(driver):
    """
    Fluxo robusto para processamento de cada processo na lista, fiel ao gigs-plugin.js:
    - Verifica tarefa atual
    - Clica no suitcase
    - Seleciona destino
    - Logs detalhados
    - Interrompe em caso de erro crítico
    """
    try:
        print('[SINCRONO] Iniciando fluxo do processo atual...')
        # 1. Verifica se está na tela de tarefas/processos
        tarefa = None
        try:
            tarefa_elem = driver.find_element(By.CSS_SELECTOR, '.texto-tarefa-processo')
            tarefa = tarefa_elem.text.strip().lower()
            print(f'[SINCRONO] Tarefa identificada: {tarefa}')
        except Exception as e:
            print(f'[SINCRONO][ERRO] Não foi possível identificar a tarefa atual: {e}')
            raise

        # 2. Clica no suitcase (ícone de movimentação)
        try:
            suitcase_btn = driver.find_element(By.CSS_SELECTOR, 'button[aria-label*="Movimentar"], button[mattooltip*="Movimentar"], .fa-suitcase')
            safe_click(driver, suitcase_btn)
            print('[SINCRONO] Clique no suitcase realizado.')
        except Exception as e:
            print(f'[SINCRONO][ERRO] Falha ao clicar no suitcase: {e}')
            raise

        # 3. Seleciona destino (exemplo: "Conclusão ao magistrado")
        try:
            destino_btn = driver.find_element(By.CSS_SELECTOR, 'button[aria-label*="Conclusão ao magistrado"]')
            safe_click(driver, destino_btn)
            print('[SINCRONO] Clique em "Conclusão ao magistrado" realizado.')
        except Exception as e:
            print(f'[SINCRONO][ERRO] Falha ao clicar no destino "Conclusão ao magistrado": {e}')
            raise

        # 4. Confirmação/log final
        print('[SINCRONO] Processo movimentado com sucesso.')
        return True
    except Exception as e:
        print(f'[SINCRONO][FATAL] Erro crítico no fluxo do processo: {e}')
        driver.save_screenshot('erro_fluxo_sincrono.png')
        return False

def main():
    limpar_temp_selenium()
    PROFILE_PATH = r"C:\Users\Silas\AppData\Roaming\Mozilla\Dev\Selenium"
    FIREFOX_BINARY = r"C:\Program Files\Firefox Developer Edition\firefox.exe"
    from selenium.webdriver.firefox.service import Service
    from selenium import webdriver
    from selenium.webdriver.firefox.options import Options
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.common.by import By
    import time
    options = Options()
    options.binary_location = FIREFOX_BINARY
    options.set_preference('profile', PROFILE_PATH)
    service = Service()
    driver = webdriver.Firefox(service=service, options=options)
    try:
        usuario = os.environ.get('PJE_USUARIO') or input('Usuário PJe: ')
        senha = os.environ.get('PJE_SENHA') or input('Senha PJe: ')
        if not login_func(driver, usuario, senha):
            raise Exception('Falha no login')
        print('Clicando no ícone de tags...')
        icone_tags = esperar_elemento(driver, '.fa-tags', timeout=15)
        if icone_tags:
            safe_click(driver, icone_tags)
            esperar_elemento(driver, 'input[aria-label*="Descrição"]', timeout=20)
            time.sleep(1)
        else:
            raise Exception('Ícone de tags não encontrado')
        from Fix import aplicar_filtro_100
        print('[DEBUG] Chamando aplicar_filtro_100(driver)...')
        aplicar_filtro_100(driver)
        # Aplica filtro xs no campo correto
        campo_desc = driver.find_element(By.CSS_SELECTOR, 'input[aria-label*="Descrição"]')
        campo_desc.clear()
        campo_desc.send_keys('xs') # Modificado de 'xs pec' para 'xs'
        campo_desc.send_keys(Keys.ENTER)
        print('[DEBUG] Filtro xs aplicado.') # Log atualizado
        time.sleep(2)  # Aguarda atualização da lista
        # Indexa e processa a lista de processos (indexação ocorre apenas uma vez)
        from Fix import indexar_e_processar_lista
        print('[DEBUG] Iniciando processamento da lista...')
        indexar_e_processar_lista(driver, fluxo_sincrono_processo, seletor_btn='button[aria-label="Abrir processo"]', log=True)
        print('[MAIN] Fim do processamento da lista de processos.', flush=True)
    except Exception as e:
        logger.error(f'Erro no fluxo principal: {str(e)}')
        driver.save_screenshot('screenshot_erro_fluxo.png')
        raise

ato_pesquisas_wrapper = lambda driver, debug=False: pesquisas(
    driver,
    conclusao_tipo='BACEN',
    modelo_nome='xsbacen',
    descricao='Pesquisas',
    marcar_pec=True,
    sigilo=True,
    prazo=30,
    marcar_primeiro_destinatario=True,
    debug=debug
)

def debug_editor_completo(driver, log=True):
    """
    Debug completo do editor para localizar seletores e estrutura do conteúdo.
    Identifica especificamente o texto "link" marcado com fundo amarelo.
    """
    if log:
        print("[DEBUG_EDITOR] Iniciando análise completa do editor...")
    
    try:
        # 1. Verifica se o editor principal existe
        editor_wrapper = driver.find_elements(By.CSS_SELECTOR, 'div.editor-wrapper')
        if log:
            print(f"[DEBUG_EDITOR] Editor wrappers encontrados: {len(editor_wrapper)}")
        
        # 2. Localiza área de conteúdo editável
        area_conteudo = driver.find_elements(By.CSS_SELECTOR, '.area-conteudo.ck.ck-content.ck-editor__editable')
        if log:
            print(f"[DEBUG_EDITOR] Áreas de conteúdo editável: {len(area_conteudo)}")
            
        if area_conteudo:
            conteudo_html = area_conteudo[0].get_attribute('innerHTML')
            if log:
                print(f"[DEBUG_EDITOR] HTML interno da área editável:")
                print(f"[DEBUG_EDITOR] {conteudo_html[:500]}...")
        
        # 3. Busca especificamente por texto marcado (fundo amarelo)
        elementos_marcados = driver.find_elements(By.CSS_SELECTOR, 'mark.marker-yellow')
        if log:
            print(f"[DEBUG_EDITOR] Elementos com marca amarela encontrados: {len(elementos_marcados)}")
            
        for i, elemento in enumerate(elementos_marcados):
            texto = elemento.text
            if log:
                print(f"[DEBUG_EDITOR] Marca {i+1}: '{texto}'")
                print(f"[DEBUG_EDITOR] HTML: {elemento.get_attribute('outerHTML')}")
                print(f"[DEBUG_EDITOR] Visível: {elemento.is_displayed()}")
        
        # 4. Busca por "link" em diferentes contextos
        seletores_link = [
            'mark.marker-yellow',
            'mark[class*="yellow"]',
            '*[contains(text(), "link")]',
            'p:contains("link")',
            '.corpo:contains("link")'
        ]
        
        for seletor in seletores_link:
            try:
                if 'contains' in seletor:
                    # XPath para texto
                    elementos = driver.find_elements(By.XPATH, f"//*[contains(text(), 'link')]")
                else:
                    # CSS Selector
                    elementos = driver.find_elements(By.CSS_SELECTOR, seletor)
                
                if log:
                    print(f"[DEBUG_EDITOR] Seletor '{seletor}': {len(elementos)} elementos")
                    
                for elem in elementos:
                    if 'link' in elem.text.lower():
                        if log:
                            print(f"[DEBUG_EDITOR] ✓ Encontrado 'link' em: {elem.text}")
                            print(f"[DEBUG_EDITOR] ✓ Seletor usado: {seletor}")
                            print(f"[DEBUG_EDITOR] ✓ HTML: {elem.get_attribute('outerHTML')}")
            except Exception as e:
                if log:
                    print(f"[DEBUG_EDITOR] ⚠ Erro no seletor '{seletor}': {e}")
        
        # 5. Análise DOM específica para o padrão identificado
        if log:
            print(f"[DEBUG_EDITOR] Analisando estrutura DOM específica...")
            
        # Baseado no HTML fornecido: <mark class="marker-yellow">"link"</mark>
        try:
            mark_elements = driver.find_elements(By.CSS_SELECTOR, 'mark.marker-yellow')
            for mark in mark_elements:
                texto_completo = mark.text
                if log:
                    print(f"[DEBUG_EDITOR] Mark encontrado: '{texto_completo}'")
                    print(f"[DEBUG_EDITOR] Parent element: {mark.find_element(By.XPATH, '..').tag_name}")
                    print(f"[DEBUG_EDITOR] Parent class: {mark.find_element(By.XPATH, '..').get_attribute('class')}")
                    
                # Verifica se contém "link"
                if '"link"' in texto_completo or 'link' in texto_completo.lower():
                    if log:
                        print(f"[DEBUG_EDITOR] ✓ ELEMENTO ALVO IDENTIFICADO!")
                        print(f"[DEBUG_EDITOR] ✓ Texto: '{texto_completo}'")
                        print(f"[DEBUG_EDITOR] ✓ Seletor CSS: mark.marker-yellow")
                        print(f"[DEBUG_EDITOR] ✓ XPath: //mark[@class='marker-yellow']")
                    return mark  # Retorna o elemento encontrado
        except Exception as e:
            if log:
                print(f"[DEBUG_EDITOR] ⚠ Erro na análise DOM específica: {e}")
        
        # 6. Teste de JavaScript para acessar conteúdo
        if log:
            print(f"[DEBUG_EDITOR] Testando acesso via JavaScript...")
            
        try:
            # Executa JavaScript para encontrar elementos
            js_result = driver.execute_script("""
                // Busca por todos os elementos mark com classe marker-yellow
                var marks = document.querySelectorAll('mark.marker-yellow');
                var results = [];
                
                for (var i = 0; i < marks.length; i++) {
                    var mark = marks[i];
                    results.push({
                        text: mark.textContent,
                        innerHTML: mark.innerHTML,
                        outerHTML: mark.outerHTML,
                        className: mark.className,
                        visible: mark.offsetParent !== null
                    });
                }
                
                return results;
            """)
            
            if log:
                print(f"[DEBUG_EDITOR] Resultado JavaScript: {js_result}")
                
            for result in js_result:
                if 'link' in result['text'].lower():
                    if log:
                        print(f"[DEBUG_EDITOR] ✓ JS encontrou elemento alvo: {result}")
                        
        except Exception as e:
            if log:
                print(f"[DEBUG_EDITOR] ⚠ Erro no JavaScript: {e}")
        
        if log:
            print(f"[DEBUG_EDITOR] Análise completa finalizada.")
            
        return None
        
    except Exception as e:
        if log:
            print(f"[DEBUG_EDITOR] ✗ Erro geral na análise: {e}")
        return None

def substituir_link_por_clipboard_debug(driver, debug=True):
    """
    Função específica para substituir "link" por conteúdo do clipboard
    com debug detalhado baseado na análise do HTML fornecido.
    """
    if debug:
        print("[SUBST_LINK] Iniciando substituição de 'link' por clipboard...")
    
    try:
        # 1. Primeiro executa debug completo
        if debug:
            print("[SUBST_LINK] Executando debug completo do editor...")
        elemento_alvo = debug_editor_completo(driver, log=debug)
        
        # 2. Busca específica pelo elemento mark.marker-yellow
        if debug:
            print("[SUBST_LINK] Buscando elemento mark.marker-yellow...")
            
        mark_elements = driver.find_elements(By.CSS_SELECTOR, 'mark.marker-yellow')
        
        if not mark_elements:
            if debug:
                print("[SUBST_LINK] ✗ Nenhum elemento mark.marker-yellow encontrado")
            return False
            
        # 3. Identifica o elemento que contém "link"
        elemento_link = None
        for mark in mark_elements:
            texto = mark.text
            if debug:
                print(f"[SUBST_LINK] Analisando mark: '{texto}'")
                
            if '"link"' in texto or 'link' in texto.lower():
                elemento_link = mark
                if debug:
                    print(f"[SUBST_LINK] ✓ Elemento alvo encontrado: '{texto}'")
                break
        
        if not elemento_link:
            if debug:
                print("[SUBST_LINK] ✗ Elemento contendo 'link' não encontrado")
            return False
        
        # 4. Executa substituição via JavaScript com clipboard
        if debug:
            print("[SUBST_LINK] Executando substituição via JavaScript...")
            
        resultado = driver.execute_script("""
            return new Promise((resolve) => {
                // Função para substituir texto preservando formatação
                function substituirTextoPreservandoFormatacao(elemento, textoAntigo, textoNovo) {
                    // Percorre todos os nós filhos
                    function percorrerNos(node) {
                        if (node.nodeType === Node.TEXT_NODE) {
                            if (node.textContent.includes(textoAntigo)) {
                                node.textContent = node.textContent.replace(textoAntigo, textoNovo);
                                return true;
                            }
                        } else {
                            for (let child of node.childNodes) {
                                if (percorrerNos(child)) return true;
                            }
                        }
                        return false;
                    }
                    
                    return percorrerNos(elemento);
                }
                
                // Tenta acessar clipboard
                if (navigator.clipboard && navigator.clipboard.readText) {
                    navigator.clipboard.readText()
                        .then(clipboardText => {
                            console.log('[SUBST_LINK] Clipboard lido:', clipboardText);
                            
                            // Encontra elemento mark.marker-yellow
                            const marks = document.querySelectorAll('mark.marker-yellow');
                            let substituido = false;
                            
                            for (const mark of marks) {
                                if (mark.textContent.includes('link')) {
                                    console.log('[SUBST_LINK] Substituindo em:', mark.textContent);
                                    
                                    // Preserva as aspas se existirem
                                    let textoCompleto = mark.textContent;
                                    let novoTexto;
                                    
                                    if (textoCompleto.includes('"link"')) {
                                        novoTexto = textoCompleto.replace('"link"', '"' + clipboardText + '"');
                                    } else {
                                        novoTexto = textoCompleto.replace('link', clipboardText);
                                    }
                                    
                                    // Substitui preservando formatação
                                    if (substituirTextoPreservandoFormatacao(mark, textoCompleto, novoTexto)) {
                                        console.log('[SUBST_LINK] ✓ Substituição realizada:', novoTexto);
                                        
                                        // Dispara eventos de mudança
                                        const evento = new Event('input', { bubbles: true });
                                        mark.dispatchEvent(evento);
                                        
                                        // Evento no editor principal
                                        const editor = document.querySelector('.ck-editor__editable');
                                        if (editor) {
                                            editor.dispatchEvent(new Event('input', { bubbles: true }));
                                        }
                                        
                                        substituido = true;
                                        break;
                                    }
                                }
                            }
                            
                            resolve({
                                sucesso: substituido,
                                clipboardText: clipboardText,
                                message: substituido ? 'Substituição realizada' : 'Elemento não encontrado'
                            });
                        })
                        .catch(error => {
                            console.error('[SUBST_LINK] Erro ao ler clipboard:', error);
                            resolve({
                                sucesso: false,
                                error: error.message,
                                message: 'Erro ao acessar clipboard'
                            });
                        });
                } else {
                    resolve({
                        sucesso: false,
                        message: 'Clipboard API não disponível'
                    });
                }
            });
        """)
        
        if debug:
            print(f"[SUBST_LINK] Resultado da execução: {resultado}")
            
        if resultado and resultado.get('sucesso'):
            if debug:
                print(f"[SUBST_LINK] ✓ Substituição bem-sucedida!")
                print(f"[SUBST_LINK] ✓ Texto do clipboard: '{resultado.get('clipboardText')}'")
            return True
        else:
            if debug:
                print(f"[SUBST_LINK] ✗ Falha na substituição: {resultado.get('message')}")
            return False
            
    except Exception as e:
        if debug:
            print(f"[SUBST_LINK] ✗ Erro na substituição: {e}")
        return False

def preencher_prazos_destinatarios(driver, prazo, apenas_primeiro=False, perito=False, perito_nomes=None):
    from selenium.webdriver.common.by import By
    # Lista fixa de nomes de peritos
    nomes_peritos_padrao = [
        'ROGERIO APARECIDO ROSA',
        # Adicione outros nomes fixos aqui se necessário
    ]
    if perito_nomes is None:
        perito_nomes = nomes_peritos_padrao
    linhas = driver.find_elements(By.CSS_SELECTOR, 'table.t-class tr.ng-star-inserted')
    if not linhas:
        print('[ATO][PRAZO][ERRO] Nenhuma linha de destinatário encontrada!')
        return False
    ativos = []
    for tr in linhas:
        try:
            checkbox = tr.find_element(By.CSS_SELECTOR, 'input[type="checkbox"][aria-label="Intimar parte"]')
            nome_elem = tr.find_element(By.CSS_SELECTOR, '.destinario')
            nome = nome_elem.text.strip().upper()
            # Se já está marcado
            if checkbox.get_attribute('aria-checked') == 'true':
                ativos.append((tr, checkbox, nome))
            # Se está desmarcado e é perito e perito=True e nome na lista
            elif perito and nome in [n.upper() for n in perito_nomes]:
                driver.execute_script("arguments[0].click();", checkbox)
                print(f'[ATO][PRAZO][PERITO] Checkbox do perito {nome} ativado.')
                ativos.append((tr, checkbox, nome))
        except Exception as e:
            print(f'[ATO][PRAZO][WARN] Erro ao localizar checkbox/nome: {e}')
    if not ativos:
        print('[ATO][PRAZO][ERRO] Nenhum destinatário ativo!')
        return False
    if apenas_primeiro:
        # Desmarca todos exceto o primeiro
        for i, (tr, checkbox, nome) in enumerate(ativos):
            if i == 0:
                continue
            try:
                driver.execute_script("arguments[0].click();", checkbox)
                print(f'[ATO][PRAZO][INFO] Checkbox do destinatário {i+1} desmarcado.')
            except Exception as e:
                print(f'[ATO][PRAZO][WARN] Erro ao desmarcar checkbox: {e}')
        ativos = [ativos[0]]
    # Preenche prazos
    for tr, checkbox, nome in ativos:
        try:
            input_prazo = tr.find_element(By.CSS_SELECTOR, 'mat-form-field.prazo input[type="text"].mat-input-element')
            input_prazo.clear()
            input_prazo.send_keys(str(prazo))
            input_prazo.clear()
            input_prazo.send_keys(str(prazo))
            print(f'[ATO][PRAZO][OK] Preenchido prazo {prazo} para destinatário {nome}.')
        except Exception as e:
            print(f'[ATO][PRAZO][WARN] Erro ao preencher prazo: {e}')
    return True

def selecionar_subtipo(driver, subtipo, timeout=10):
    """Seleciona um subtipo de documento de forma robusta, simulando o padrão do gigs-plugin.js."""
    input_subtipo = WebDriverWait(driver, timeout).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, 'input[data-placeholder="Tipo de Documento"]'))
    )
    input_subtipo.clear()
    input_subtipo.send_keys(subtipo)
    
    # Espera pelo dropdown de opções e seleciona a opção exata
    opcoes = WebDriverWait(driver, timeout).until(
        EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'mat-option'))
    )
    for opcao in opcoes:
        if opcao.text.strip().lower() == subtipo.lower():
            opcao.click()
            return True
    raise Exception(f'Subtipo "{subtipo}" não encontrado!')

# ====================================================
# EXEMPLO DE USO - SIGILO CORRIGIDO
# ====================================================
"""
EXEMPLO DE USO COM O NOVO SISTEMA DE SIGILO:

# No fluxo principal (ex: m1.py):
from atos import ato_pesqliq, executar_visibilidade_sigilosos_se_necessario

# Executa o ato
sucesso = ato_pesqliq(driver, debug=True)

if sucesso:
    # NOVO: Troca para a primeira aba (deve ser /detalhe) sem fechar a atual
    if len(driver.window_handles) > 1:
        driver.switch_to.window(driver.window_handles[0])
    
    # Executa visibilidade se sigilo foi ativado (inclui F5 automático)
    sigilo_ativado = getattr(ato_pesqliq, 'ultimo_sigilo_ativado', False)
    executar_visibilidade_sigilosos_se_necessario(driver, sigilo_ativado, debug=True)

# OU, usando o ato_judicial diretamente:
sucesso, sigilo_ativado = ato_judicial(
    driver, 
    conclusao_tipo='Homologação de Cálculos',
    modelo_nome='xsbacen',
    sigilo=True,
    descricao='pesquisas para execucao'
)

if sucesso:
    # NOVO: Troca para primeira aba sem fechar (deve ser /detalhe)
    if len(driver.window_handles) > 1:
        driver.switch_to.window(driver.window_handles[0])
    
    # Executa visibilidade (inclui F5 automático)
    executar_visibilidade_sigilosos_se_necessario(driver, sigilo_ativado, debug=True)
"""

# ====================================================
# BLOCO 5 - FUNÇÕES DE CHIPS
# ====================================================

def def_chip(driver, numero_processo, observacao, debug=False, timeout=10):
    """
    Remove chips de 'Prazo vencido' e 'Prazo vencido pós sentença' do processo.
    
    Args:
        driver: WebDriver do Selenium
        numero_processo: Número do processo (para logs)
        observacao: Observação que disparou a ação (para logs)
        debug: Se True, exibe logs detalhados
        timeout: Timeout para aguardar elementos
    
    Returns:
        bool: True se pelo menos um chip foi removido, False caso contrário
    """
    import time
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    
    def log_msg(msg):
        if debug:
            print(f"[DEF_CHIP] {msg}")
    
    log_msg(f"Iniciando remoção de chips para processo {numero_processo}")
    log_msg(f"Observação que disparou: {observacao}")
    
    chips_removidos = 0
    
    try:
        # Lista de textos de chips para remover
        chips_para_remover = [
            "Prazo vencido",
            "Prazo vencido pós sentença",
            "SISBAJUD",
        ]
        
        for chip_texto in chips_para_remover:
            try:
                log_msg(f"Procurando chip: {chip_texto}")
                
                # Procura o chip específico usando o texto
                chip_xpath = f"//mat-chip[.//span[contains(text(), '{chip_texto}')]]"
                
                # Aguarda o chip aparecer (com timeout menor para não travar)
                try:
                    chip_element = WebDriverWait(driver, 3).until(
                        EC.presence_of_element_located((By.XPATH, chip_xpath))
                    )
                    log_msg(f"✅ Chip '{chip_texto}' encontrado")
                except:
                    log_msg(f"⏭️ Chip '{chip_texto}' não encontrado, pulando...")
                    continue
                
                # Procura o botão de remover dentro do chip
                botao_remover = chip_element.find_element(
                    By.CSS_SELECTOR, 
                    "button[mattooltip*='Remover Chip'], button.etq-botao-excluir"
                )
                
                log_msg(f"Clicando no botão de remover do chip '{chip_texto}'")
                botao_remover.click()
                
                # Aguarda o modal de confirmação aparecer
                time.sleep(1)
                
                # Procura o botão "Sim" para confirmar
                try:
                    botao_sim = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((
                            By.XPATH, 
                            "//button[.//span[contains(text(), 'Sim')]]"
                        ))
                    )
                    
                    log_msg(f"Confirmando remoção do chip '{chip_texto}'")
                    botao_sim.click()
                    
                    # Aguarda a remoção ser processada
                    time.sleep(2)
                    
                    chips_removidos += 1
                    log_msg(f"✅ Chip '{chip_texto}' removido com sucesso")
                    
                except Exception as e:
                    log_msg(f"❌ Erro ao confirmar remoção do chip '{chip_texto}': {e}")
                    continue
                    
            except Exception as e:
                log_msg(f"❌ Erro ao processar chip '{chip_texto}': {e}")
                continue
        
        # Resultado final
        if chips_removidos > 0:
            log_msg(f"✅ Total de chips removidos: {chips_removidos}")
            return True
        else:
            log_msg("⚠️ Nenhum chip foi removido")
            return False
            
    except Exception as e:
        log_msg(f"❌ Erro geral na remoção de chips: {e}")
        return False