"""Módulo PEC - Processamento de Execução e Cumprimento (PJe)."""

import time
import re
import os
from typing import Optional, Dict, List, Tuple, Any
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# ====================================================
# CONTROLE DE PROGRESSO UNIFICADO
# ====================================================
from Fix.monitoramento_progresso_unificado import (
    carregar_progresso_unificado,
    salvar_progresso_unificado,
    processo_ja_executado_unificado,
    marcar_processo_executado_unificado,
    extrair_numero_processo_unificado,
    verificar_acesso_negado_unificado,
)

from Fix.core import aguardar_e_clicar, esperar_elemento, preencher_campo
from Fix.extracao import extrair_dados_processo

# Funções específicas para PEC (compatibilidade)
def carregar_progresso_pec() -> Dict[str, Any]:
    """Carrega o estado de progresso usando sistema unificado"""
    return carregar_progresso_unificado('pec')


def salvar_progresso_pec(progresso: Dict[str, Any]) -> bool:
    """Salva o estado de progresso usando sistema unificado"""
    salvar_progresso_unificado('pec', progresso)
    return True


def extrair_numero_processo_pec(driver: Any) -> Optional[str]:
    """
    Extrai o número do processo da URL ou elemento da página (adaptado para PEC).
    Funciona tanto na visualização de processo individual quanto na lista.
    """
    try:
        # Método 1: Extrair da URL quando estamos dentro de um processo
        url = driver.current_url
        if "processo/" in url:
            match = re.search(r"processo/(\d+)", url)
            if match:
                numero_limpo = match.group(1)
                print(f"[PROGRESSO_PEC] ✅ Número extraído da URL: {numero_limpo}")
                return numero_limpo
        
        # Método 2: Buscar por seletores específicos na página
        try:
            candidatos = driver.find_elements(By.CSS_SELECTOR, 'h1, h2, h3, .processo-numero, [data-testid*="numero"], .cabecalho, .numero-processo')
            for elemento in candidatos:
                texto = elemento.text.strip()
                match = re.search(r'(\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4})', texto)
                if match:
                    numero_limpo = re.sub(r'[^\d]', '', match.group(1))
                    print(f"[PROGRESSO_PEC] ✅ Número extraído do elemento: {numero_limpo}")
                    return numero_limpo
        except Exception as inner_e:
            print(f"[PROGRESSO_PEC] ⚠️ Erro ao buscar por seletores: {inner_e}")
        
        # Método 3: JavaScript para extrair da página atual (mais robusto)
        try:
            numero_js = driver.execute_script("""
                // Busca por padrão de processo em todo o texto da página
                var textoCompleto = document.body.innerText || document.body.textContent || '';
                var matches = textoCompleto.match(/\\d{7}-\\d{2}\\.\\d{4}\\.\\d\\.\\d{2}\\.\\d{4}/g);
                if (matches && matches.length > 0) {
                    // Retorna o primeiro número encontrado (sem formatação)
                    return matches[0].replace(/[^\\d]/g, '');
                }
                
                // Fallback: buscar em título da página ou elementos específicos
                var titulo = document.title;
                var matchTitulo = titulo.match(/\\d{7}-\\d{2}\\.\\d{4}\\.\\d\\.\\d{2}\\.\\d{4}/);
                if (matchTitulo) {
                    return matchTitulo[0].replace(/[^\\d]/g, '');
                }
                
                return null;
            """)
            
            if numero_js:
                print(f"[PROGRESSO_PEC] ✅ Número extraído via JavaScript: {numero_js}")
                return numero_js
                
        except Exception as js_e:
            print(f"[PROGRESSO_PEC] ⚠️ Erro no JavaScript de extração: {js_e}")
        
        print("[PROGRESSO_PEC] ⚠️ Nenhum número de processo encontrado")
        return None
        
    except Exception as e:
        print(f"[PROGRESSO_PEC][ERRO] Falha ao extrair número do processo: {e}")
        return None


def verificar_acesso_negado_pec(driver: Any) -> bool:
    """Verifica se estamos na página de acesso negado no sistema PEC"""
    try:
        url_atual = driver.current_url
        return "acesso-negado" in url_atual.lower() or "login.jsp" in url_atual.lower()
    except Exception as e:
        msg = str(e)
        print(f"[PROGRESSO_PEC][ERRO] Falha ao verificar acesso negado: {msg}")
        if "browsing context has been discarded" in msg.lower() or "session deleted because of page crash" in msg.lower():
            # Driver está inválido, sinalizar restart para o fluxo
            return True
        return False


def verificar_e_recuperar_acesso_negado(driver, criar_driver_func, login_func):
    """
    Verifica se o driver está em estado de acesso negado e tenta recuperar.
    
    Args:
        driver: Driver atual
        criar_driver_func: Função para criar novo driver
        login_func: Função para fazer login
        
    Returns:
        tuple: (driver_valido, foi_recuperado)
            - driver_valido: Driver válido (novo ou o mesmo)
            - foi_recuperado: True se houve recuperação, False caso contrário
    """
    try:
        if not verificar_acesso_negado_pec(driver):
            return driver, False
        
        print("[RECOVERY] ⚠️ Acesso negado detectado! URL: /acesso-negado")
        print("[RECOVERY]  Fechando driver atual...")
        
        try:
            driver.quit()
        except Exception as e:
            print(f"[RECOVERY] ⚠️ Erro ao fechar driver: {e}")
        
        print("[RECOVERY]  Criando novo driver...")
        novo_driver = criar_driver_func(headless=False)
        if not novo_driver:
            print('[RECOVERY] ❌ Falha ao criar novo driver')
            raise Exception("Falha ao criar driver durante recuperação")
        
        print("[RECOVERY]  Executando login...")
        if not login_func(novo_driver):
            print('[RECOVERY] ❌ Falha ao fazer login')
            novo_driver.quit()
            raise Exception("Falha no login durante recuperação")
        
        print('[RECOVERY] ✅ Driver reiniciado e login efetuado com sucesso')
        return novo_driver, True
        
    except Exception as e:
        print(f"[RECOVERY] ❌ Erro crítico na recuperação: {e}")
        raise


def processo_ja_executado_pec(numero_processo: str, progresso: Optional[Dict[str, Any]] = None) -> bool:
    """Verifica se o processo já foi executado no fluxo PEC usando sistema unificado"""
    if not numero_processo:
        return False
    
    if progresso is None:
        progresso = carregar_progresso_pec()
    
    return processo_ja_executado_unificado(numero_processo, progresso)


def marcar_processo_executado_pec(numero_processo: str, progresso: Optional[Dict[str, Any]] = None, status: str = "SUCESSO", detalhes: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Marca processo como executado no fluxo PEC usando sistema unificado"""
    if not numero_processo:
        return progresso
    
    if progresso is None:
        progresso = carregar_progresso_pec()
    
    sucesso = True if (status or "").upper() == "SUCESSO" else False
    marcar_processo_executado_unificado('pec', numero_processo, progresso, sucesso=sucesso)
    
    return progresso


def reiniciar_driver_e_logar_pje(driver, log=True):
    """
    Reinicia o driver do PJe usando as fábricas em `driver_config` e executa o login
    Retorna o novo driver se bem-sucedido, ou None em caso de falha.
    """
    try:
        if log:
            print('[RECOVERY][RESTART] Reiniciando driver e efetuando novo login...')
        try:
            # Tentar fechar o driver anterior de forma segura
            try:
                driver.quit()
            except Exception:
                pass

            # Importar factories e função de login do Fix
            from Fix.core import criar_driver_PC
            from Fix.utils import login_cpf

            # Criar novo driver
            novo_driver = criar_driver_PC(headless=False)
            if not novo_driver:
                if log:
                    print('[RECOVERY][RESTART] Falha ao criar novo driver')
                return None

            # Executar login (pode ser automático ou manual conforme configuração)
            ok = False
            try:
                ok = login_cpf(novo_driver)
            except Exception as e:
                if log:
                    print(f'[RECOVERY][RESTART] Erro ao executar login_func: {e}')
                ok = False

            if not ok:
                if log:
                    print('[RECOVERY][RESTART] Login falhou no novo driver')
                try:
                    novo_driver.quit()
                except Exception:
                    pass
                return None

            # Navegar para a lista de atividades para retomar o processamento
            try:
                url_atividades = 'https://pje.trt2.jus.br/pjekz/gigs/relatorios/atividades'
                novo_driver.get(url_atividades)
                time.sleep(4)
                # Tentar reaplicar filtro de 100 itens se disponível
                try:
                    from Fix import aplicar_filtro_100
                    aplicar_filtro_100(novo_driver)
                    time.sleep(1)
                except Exception:
                    pass
            except Exception:
                pass

            if log:
                print('[RECOVERY][RESTART] Novo driver pronto e logado')
            return novo_driver

        except Exception as e:
            if log:
                print(f'[RECOVERY][RESTART] Falha durante reinício do driver: {e}')
            return None
    except Exception as e:
        print(f'[RECOVERY][RESTART][ERRO] Exceção inesperada: {e}')
        return None

# ===== SISTEMA DE CACHE GLOBAL PARA REGRAS DE AÇÃO =====
# Cache singleton para evitar rebuilding das regras a cada execução
#
# NOTA IMPORTANTE SOBRE ASSINATURAS DE FUNÇÃO:
# - Todas as funções nas regras devem ter assinatura: func(driver, debug=False) -> bool
# - Algumas funções legado (mov_sob, def_chip, def_sob) precisam de parâmetros extras
# - Solução: Essas funções precisam ser capturadas antes da execução ou estar em estado
#   pré-configurado (ex: closure que já capturou numero_processo e observacao)
# - Na prática atual, essas funções são chamadas já com acesso direto ao estado do processo.
#
# IMPORTANTE: PADRONIZAR TODAS AS AÇÕES PARA ASSINATURA SIMPLES!


def navegar_para_atividades(driver):
    """
    Navega para a tela de atividades do GIGS através da URL direta.
    """
    try:
        url_atividades = 'https://pje.trt2.jus.br/pjekz/gigs/relatorios/atividades'
        print(f"[NAVEGAR] Navegando para atividades: {url_atividades}")
        driver.get(url_atividades)
        
        # Aguarda a página carregar
        import time
        time.sleep(3)
        
        # Verifica se chegou na página correta
        if 'atividades' in driver.current_url:
            print("[NAVEGAR] ✅ Navegação para atividades bem-sucedida")
            return True
        else:
            print(f"[NAVEGAR] ❌ Erro: URL atual é {driver.current_url}")
            return False
            
    except Exception as e:
        print(f"[NAVEGAR] Erro ao navegar para atividades: {e}")
        return False


def aplicar_filtro_xs(driver):
    """
    Aplica filtro 'xs' na tela de atividades do GIGS.
    """
    try:
        from selenium.webdriver.common.by import By
        from selenium.webdriver.common.keys import Keys
        from Fix import esperar_elemento, safe_click
        
        # Clicar no ícone fa-pen para abrir filtros
        btn_fa_pen = esperar_elemento(driver, 'i.fa-pen', timeout=15)
        if not btn_fa_pen:
            print("[FILTRO_XS] ❌ Botão fa-pen não encontrado")
            return False
        
        safe_click(driver, btn_fa_pen)
        time.sleep(2)
        
        # Aplicar filtro "xs" no campo descrição
        campo_descricao = esperar_elemento(driver, 'input[aria-label*="Descrição"]', timeout=15)
        if not campo_descricao:
            print("[FILTRO_XS] ❌ Campo descrição não encontrado")
            return False
        
        # Aplicar preencher_campo para 'xs'
        resultado_preenchimento = preencher_campo(driver, campo_descricao, 'xs')
        if not resultado_preenchimento:
            print("[FILTRO_XS] ❌ Falha ao preencher campo descrição")
            return False
        
        campo_descricao.send_keys(Keys.ENTER)
        
        print('[FILTRO_XS] ✅ Filtro xs aplicado com sucesso')
        time.sleep(3)
        return True
        
    except Exception as e:
        print(f"[FILTRO_XS] ❌ Erro ao aplicar filtro: {e}")
        return False

# Função principal para manter compatibilidade

def indexar_processo_atual_gigs(driver):
    """
    Extrai número do processo e observação da página atual de atividades GIGS.
    Assume que já está na página de detalhes do processo.
    
    Returns:
        tuple: (numero_processo, observacao) ou None se falhar
    """
    from selenium.webdriver.common.by import By
    import re
    
    try:
        # Método 1: Tentar extrair da URL atual
        url_atual = driver.current_url
        if "processo" in url_atual:
            # Extrai número da URL se disponível
            match_url = re.search(r'processo/(\d+)', url_atual)
            if match_url:
                numero_processo = match_url.group(1)
                print(f"[INDEXAR_GIGS] Número extraído da URL: {numero_processo}")
        
        # Método 2: Buscar na página por elementos que contenham o número
        try:
            # Procura por elementos que podem conter o número do processo
            candidatos = driver.find_elements(By.CSS_SELECTOR, 
                'h1, h2, h3, .processo-numero, [data-testid*="numero"], .cabecalho')
            
            numero_processo = None
            for elemento in candidatos:
                texto = elemento.text.strip()
                # Busca padrão de número de processo: 1234567-12.2024.5.02.1234
                match = re.search(r'(\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4})', texto)
                if match:
                    numero_processo = match.group(1)
                    print(f"[INDEXAR_GIGS] Número encontrado na página: {numero_processo}")
                    break
            
            if not numero_processo:
                print("[INDEXAR_GIGS] ⚠️ Número do processo não encontrado na página")
                # Fallback: usar um identificador genérico baseado na URL
                numero_processo = f"PROC_{hash(url_atual) % 1000000}"
        
        except Exception as e:
            print(f"[INDEXAR_GIGS] ⚠️ Erro ao buscar número na página: {e}")
            numero_processo = "UNKNOWN"
        
        # Método 3: Buscar observação na estrutura HTML específica do GIGS
        observacao = ""
        try:
            print("[INDEXAR_GIGS] Procurando observação na estrutura HTML específica...")
            
            # Procura pelo elemento <span class="descricao"> que contém "Prazo: observacao"
            elementos_descricao = driver.find_elements(By.CSS_SELECTOR, 'span.descricao')
            
            for elemento in elementos_descricao:
                try:
                    texto_completo = elemento.text.strip()
                    print(f"[INDEXAR_GIGS] Texto encontrado: {texto_completo}")
                    
                    # Verifica se tem o padrão "Prazo: observacao"
                    if texto_completo.startswith('Prazo:'):
                        # Extrai a observação após "Prazo: "
                        observacao = texto_completo[6:].strip().lower()  # Remove "Prazo: " e converte para minúscula
                        observacao = observacao.rstrip('.')  # Remove ponto final se houver
                        print(f"[INDEXAR_GIGS] ✅ Observação extraída: {observacao}")
                        break
                except Exception as e:
                    print(f"[INDEXAR_GIGS] Erro ao processar elemento descricao: {e}")
                    continue
            
            if not observacao:
                print("[INDEXAR_GIGS] ⚠️ Observação não encontrada na estrutura específica")
                # Fallback: buscar qualquer texto que contenha padrões conhecidos no HTML
                texto_pagina = driver.page_source.lower()
                
                padroes_conhecidos = ['xs carta', 'xs pec cp', 'xs pec edital', 'xs bloq', 'sob chip', 'sobrestamento vencido']
                for padrao in padroes_conhecidos:
                    if padrao in texto_pagina:
                        observacao = padrao
                        print(f"[INDEXAR_GIGS] Observação encontrada no fallback: {observacao}")
                        break
                
                if not observacao:
                    observacao = "observacao nao encontrada"
                    print("[INDEXAR_GIGS] ⚠️ Usando observação padrão")
        
        except Exception as e:
            print(f"[INDEXAR_GIGS] ⚠️ Erro ao buscar observação: {e}")
            observacao = "erro ao extrair observacao"
        
        return (numero_processo, observacao)
        
    except Exception as e:
        print(f"[INDEXAR_GIGS] ❌ Erro geral ao indexar processo atual: {e}")
        return None


def analisar_documentos_pos_carta(driver, numero_processo, observacao, debug=False):
    """
    Analisa documentos após execução de carta para observação "xs pz carta".
    Busca até 4 documentos (sentença, decisão ou despacho) e aplica regras específicas.
    """
    from selenium.webdriver.common.by import By
    from Fix import extrair_documento, criar_gigs
    import time
    
    def log_msg(msg):
        if debug:
            print(f"[XS_PZ_CARTA] {msg}")
    
    log_msg(f"Iniciando análise de documentos para processo {numero_processo}")
    
    try:
        # Buscar itens da timeline
        itens = driver.find_elements(By.CSS_SELECTOR, 'li.tl-item-container')
        if not itens:
            log_msg("❌ Nenhum item encontrado na timeline")
            return False
        
        log_msg(f"Encontrados {len(itens)} itens na timeline")
        
        # Contador de documentos processados
        documentos_processados = 0
        max_documentos = 4
        
        # Procurar documentos relevantes (sentença, decisão ou despacho)
        for item in itens:
            if documentos_processados >= max_documentos:
                log_msg(f"Limite de {max_documentos} documentos atingido")
                break
                
            try:
                # Verificar se é um documento relevante
                link = item.find_element(By.CSS_SELECTOR, 'a.tl-documento:not([target="_blank"])')
                if not link:
                    continue
                
                doc_text = link.text.lower()
                log_msg(f"Verificando documento: {doc_text}")
                
                # Verificar se é sentença, decisão ou despacho
                if not any(termo in doc_text for termo in ['sentença', 'decisão', 'despacho']):
                    continue
                
                log_msg(f"Documento relevante encontrado: {doc_text}")
                
                # Clicar no documento para abrir
                try:
                    # Rolar até o elemento para garantir visibilidade
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", link)
                    time.sleep(0.5)
                    
                    # Clicar no documento
                    link.click()
                    time.sleep(2)
                    
                    log_msg("Documento aberto com sucesso")
                    
                    # Extrair conteúdo do documento
                    resultado_extracao = extrair_documento(driver, timeout=10, log=debug)
                    if not resultado_extracao or not resultado_extracao[0]:
                        log_msg("❌ Falha ao extrair conteúdo do documento")
                        continue
                    
                    texto_documento = resultado_extracao[0].lower()
                    log_msg(f"Conteúdo extraído: {texto_documento[:100]}...")
                    
                    # Aplicar regras conforme conteúdo
                    regra_aplicada = False
                    
                    # Regra a: "defiro a instauração" -> ato_idpj
                    if "defiro a instauração" in texto_documento:
                        log_msg("Regra aplicada: 'defiro a instauração' -> ato_idpj")
                        from atos import ato_idpj
                        resultado_idpj = ato_idpj(driver, debug=debug)
                        
                        if resultado_idpj:
                            log_msg("✅ ato_idpj executado com sucesso")
                            regra_aplicada = True
                        else:
                            log_msg("❌ Falha ao executar ato_idpj")
                    
                    # Regra b: "bloqueio realizado" ou "844" -> criar GIGS 1/Bruna/Liberação
                    elif "bloqueio realizado" in texto_documento or "844" in texto_documento:
                        log_msg("Regra aplicada: 'bloqueio realizado' ou '844' -> criar GIGS")
                        resultado_gigs = criar_gigs(
                            driver=driver,
                            dias_uteis=1,
                            responsavel="Bruna",
                            observacao="Liberação",
                            timeout=10,
                            log=debug
                        )
                        
                        if resultado_gigs:
                            log_msg("✅ GIGS criado com sucesso")
                            regra_aplicada = True
                        else:
                            log_msg("❌ Falha ao criar GIGS")
                    
                    # Regra c: "instaurado em face" -> ato_meios
                    elif "instaurado em face" in texto_documento:
                        log_msg("Regra aplicada: 'instaurado em face' -> ato_meios")
                        from atos import ato_meios
                        resultado_meios = ato_meios(driver, debug=debug)
                        
                        if resultado_meios:
                            log_msg("✅ ato_meios executado com sucesso")
                            regra_aplicada = True
                        else:
                            log_msg("❌ Falha ao executar ato_meios")
                    
                    if regra_aplicada:
                        documentos_processados += 1
                        log_msg(f"Documento processado com sucesso ({documentos_processados}/{max_documentos})")
                    else:
                        log_msg("⚠️ Nenhuma regra aplicável para este documento")
                    
                except Exception as e:
                    log_msg(f"❌ Erro ao processar documento: {e}")
                    continue
                    
            except Exception as e:
                log_msg(f"❌ Erro ao analisar item da timeline: {e}")
                continue
        
        log_msg(f"Análise concluída. {documentos_processados} documentos processados.")
        return documentos_processados > 0
        
    except Exception as e:
        log_msg(f"❌ Erro geral na análise de documentos: {e}")
        return False


def main(driver=None, tipo_driver='PC', tipo_login='CPF', headless=False):
    """
    Função principal - executa o novo fluxo
    
    Args:
        driver: Driver existente (opcional)
        tipo_driver: Tipo de driver ('PC', 'VT', etc.) - usado se driver=None
        tipo_login: Tipo de login ('CPF', 'PC') - usado se driver=None  
        headless: Executar em modo headless - usado se driver=None
    
    Se driver não for fornecido, cria automaticamente usando credencial()
    """
    if driver is None:
        print(f"[PEC] Criando driver automaticamente: {tipo_driver} + {tipo_login}")
        
        # ===== SETUP UNIFICADO COM CREDENCIAL =====
        from Fix.core import credencial
        driver = credencial(
            tipo_driver=tipo_driver,
            tipo_login=tipo_login, 
            headless=headless
        )
        
        if not driver:
            print('[PEC][ERRO] Falha ao criar driver com credencial()')
            return False
            
        print('[PEC] ✅ Driver criado e login realizado via credencial()')
        
        # ===== CONFIGURAR RECOVERY GLOBAL =====
        def recovery_credencial():
            return credencial(tipo_driver=tipo_driver, tipo_login=tipo_login, headless=headless)
        
        try:
            # Configurar recovery se disponível
            if 'configurar_recovery_driver' in globals():
                configurar_recovery_driver(recovery_credencial, lambda d: True)
                print("[PEC] ✅ Sistema de recuperação automática configurado")
        except:
            print("[PEC] ⚠️ Recovery não configurado")
    else:
        print("[PEC] Usando driver fornecido externamente")
    
    # Import local para evitar circular import
    from PEC.processamento import executar_fluxo_novo
    return executar_fluxo_novo(driver)




