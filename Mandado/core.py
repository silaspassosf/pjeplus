import logging
logger = logging.getLogger(__name__)

# m1.py
# Fluxo automatizado de mandados PJe TRT2
###DIRETRIZES MÁXIMAS INEGOCIÁVEIS
# Priorizar edições apenas no código selecionado ou referenciado  
# Sempre validar se as alterações propostas estão estritamente alinhadas com o prompt do usuário.  
# Evitar modificações em arquivos não explicitamente mencionados.  
# Respeitar convenções de estilo definidas no projeto (ex: indentação com tabs, aspas duplas).  
# Workspace preference: NÃO altere, traduza ou reescreva NENHUMA linha do código, exceto exatamente o trecho solicitado.
# NÃO traduza palavras-chave, nomes de variáveis, comentários, strings, nem nada do código.
# NÃO faça ajustes automáticos, refatorações, nem ‘melhorias’ não solicitadas.
# Se precisar editar, use sempre o padrão # ...existing code... para indicar partes não alteradas. 
# As edições devem ser ESPECIFICAMENTE sobre erros de log ou pedidos EXPLICITOS do usuario, nada alem disso.
# tenha em mente que descumprir essas diretizes estraga o codigo e causa perda de tempo
# nao é neceasário varrer o codigo todo para cada edição pedida 
# use a busca de termos para ir diretamente à região correta e edirtar apenas o necessário, para ser mais eficiente
# ====================================================
# BLOCO 0 - GERAL
# ====================================================

# 0. Importações Padrão
import os
import sys
import time
from datetime import datetime
from typing import Dict, Any
from Fix.tipos import ResultadoFluxo

# Selenium
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
)

# Módulos Locais Fix
from Fix.core import (
    aguardar_e_clicar,
)
from Fix.extracao import (
    indexar_e_processar_lista,
    indexar_processos,
)
from Fix.utils import (
    navegar_para_tela,
)
from Fix.abas import validar_conexao_driver
from Fix.abas import forcar_fechamento_abas_extras

# Módulo Mandado local
from .entrada_api import processar_mandados_devolvidos_api

with open("log.py", "w", encoding="utf-8") as f:
    f.write(f"# Última execução: {datetime.now()}\n")
    f.write(f"# Script: {os.path.abspath(sys.argv[0])}\n")
    f.write(f"# Argumentos: {' '.join(sys.argv[1:])}\n")

# ====================================================
# CONTROLE DE SESSÃO E PROGRESSO UNIFICADO
# ====================================================

# Sistema de progresso próprio para Mandado usando o sistema unificado
from Fix.monitoramento_progresso_unificado import (
    carregar_progresso_mandado,
    salvar_progresso_mandado,
    extrair_numero_processo_mandado,
    verificar_acesso_negado_mandado,
    processo_ja_executado_mandado,
    marcar_processo_executado_mandado,
)

# Funções de compatibilidade (aliases para manter compatibilidade com código existente)
carregar_progresso = carregar_progresso_mandado
salvar_progresso = salvar_progresso_mandado
extrair_numero_processo = extrair_numero_processo_mandado
verificar_acesso_negado = verificar_acesso_negado_mandado
processo_ja_executado = processo_ja_executado_mandado
marcar_processo_executado = marcar_processo_executado_mandado


def _aguardar_estabilizacao_pos_processo(driver: WebDriver, timeout: float = 6.0) -> bool:
    """Aguarda estado estável após fechar abas antes de abrir próximo processo."""
    inicio = time.time()

    while (time.time() - inicio) < timeout:
        try:
            status = validar_conexao_driver(driver, "MANDADO_POS_PROCESSO")
            if status == "FATAL":
                logger.error('[FLUXO][POS] Contexto fatal detectado durante estabilização')
                return False

            abas = driver.window_handles
            url_atual = (driver.current_url or '').lower()

            # Estado esperado: uma aba na lista/painel global
            if len(abas) == 1 and ('/lista-processos' in url_atual or '/painel/global/' in url_atual):
                # Pequeno buffer para render da lista/chips antes do próximo clique
                try:
                    _ = driver.find_elements(By.CSS_SELECTOR, 'tbody tr.tr-class, tr.cdk-drag')
                except Exception:
                    pass
                time.sleep(0.1)
                return True
        except Exception:
            pass

        time.sleep(0.05)

    # fallback não-bloqueante: pequena pausa extra para reduzir corrida
    time.sleep(0.2)
    logger.warning('[FLUXO][POS] Timeout de estabilização pós-processo; seguindo com buffer de segurança')
    return True


# 2. Funções de Navegação

def navegacao(driver: WebDriver) -> bool:
    """Navegação para a lista de documentos internos do PJe TRT2"""
    try:
        url_lista = os.getenv('URL_PJE_ESCANINHO', 'https://pje.trt2.jus.br/pjekz/escaninho/documentos-internos')
        logger.info(f'[NAV] Iniciando navegação para: {url_lista}')

        if not navegar_para_tela(driver, url=url_lista, delay=2):
            raise Exception('Falha na navegação para a tela de documentos internos')

        # Maximizar janela e aplicar zoom reduzido para melhorar visibilidade
        try:
            try:
                driver.maximize_window()
            except Exception:
                # Alguns perfis/headless podem não suportar maximize
                pass
            try:
                driver.execute_script("document.body.style.zoom='70%';")
            except Exception:
                # Falha ao aplicar zoom via JS não é crítico
                pass
            logger.info('[NAV] Janela maximizada e zoom aplicado (70%)')
        except Exception:
            pass

        # CONTAR PROCESSOS ANTES DO CLIQUE NO FILTRO
        try:
            processos_antes_selector = 'tr.cdk-drag'
            processos_antes = driver.find_elements(By.CSS_SELECTOR, processos_antes_selector)
            quantidade_antes = len(processos_antes)
        except Exception as count_error:
            logger.info(f'[NAV][CONTAGEM][ERRO] Erro ao contar processos antes: {count_error}')
            quantidade_antes = 0

        logger.info('[NAV] Verificando/ativando filtro de mandados devolvidos...')


        # IDENTIFICAR O ÍCONE ESPECÍFICO DE MANDADOS DEVOLVIDOS
        try:
            # Procurar pelo ícone com aria-label contendo "Mandados devolvidos"
            icones_mandados = driver.find_elements(By.CSS_SELECTOR, 'i[aria-label*="Mandados devolvidos"]')

            if not icones_mandados:
                logger.info('[NAV][ERRO] Ícone de mandados devolvidos não encontrado')
                return False

            icone_mandados = icones_mandados[0]  # Deve haver apenas um

            aria_label = icone_mandados.get_attribute('aria-label')
            aria_pressed = icone_mandados.get_attribute('aria-pressed')
            logger.info(f'[NAV][FILTRO] Ícone encontrado: aria-label="{aria_label}", aria-pressed="{aria_pressed}"')


            # VERIFICAR SE O FILTRO JÁ ESTÁ ATIVO
            if aria_pressed == 'true':
                logger.info('[NAV][FILTRO]  Filtro de mandados devolvidos já está ativo')
                # Mesmo que já esteja ativo, vamos verificar se a lista está correta
            else:
                logger.info('[NAV][FILTRO]  Filtro não está ativo, clicando para ativar...')
                # Usar o seletor específico baseado no aria-label
                icone_selector = f'i[aria-label="{aria_label}"]'
                resultado = aguardar_e_clicar(driver, icone_selector, timeout=10, log=True)

                if not resultado:
                    logger.info('[NAV][FILTRO]  Falha ao clicar no ícone de mandados devolvidos')
                    return False

                logger.info('[NAV][FILTRO]  Ícone de mandados devolvidos clicado com sucesso')


        except Exception as icone_error:
            logger.info(f'[NAV][FILTRO][ERRO] Erro ao identificar ícone: {icone_error}')
            return False

        # VERIFICAR PRESENÇA DO CHIP DE FILTRO "MANDADOS DEVOLVIDOS"
        try:
            logger.info('[NAV][FILTRO] Verificando presença do filtro "Mandados devolvidos"...')
            # Seletor mais simples e confiável para o chip de filtro
            filtro_selector = 'mat-chip'

            # Aguardar até 10 segundos pela presença de QUALQUER chip de filtro
            filtro_chips = WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, filtro_selector))
            )

            # Verificar se algum chip contém "Mandados devolvidos"
            filtro_encontrado = False
            for chip in filtro_chips:
                try:
                    chip_text = chip.text.strip()
                    if "mandados devolvidos" in chip_text.lower():
                        filtro_encontrado = True
                        logger.info(f'[NAV][FILTRO]  Filtro encontrado: "{chip_text}"')
                        break
                except Exception:
                    continue  # item individual, continua

            if filtro_encontrado:
                logger.info('[NAV][FILTRO]  Filtro "Mandados devolvidos" confirmado com chip presente')
                return True
            else:
                logger.info('[NAV][FILTRO]  Chip "Mandados devolvidos" não encontrado - tentando clicar novamente...')
                # Tentar clicar novamente no ícone
                resultado_retry = aguardar_e_clicar(driver, icone_selector, timeout=10, log=True)
                if resultado_retry:
                    logger.info('[NAV][FILTRO]  Retry do clique realizado')
                    time.sleep(0.002)  # Aguardar carregamento após retry
                    return True
                else:
                    logger.info('[NAV][FILTRO]  Falha no retry do clique')
                    return False

        except TimeoutException:
            logger.info('[NAV][FILTRO]  Timeout aguardando filtro - tentando clicar novamente...')
            # Tentar clicar novamente no ícone
            resultado_retry = aguardar_e_clicar(driver, icone_selector, timeout=10, log=True)
            if resultado_retry:
                logger.info('[NAV][FILTRO]  Retry do clique realizado após timeout')
                time.sleep(0.002)
                return True
            else:
                logger.info('[NAV][FILTRO]  Falha no retry após timeout')
                return False
        except Exception as filtro_error:
            logger.info(f'[NAV][FILTRO][ERRO] Erro na verificação: {filtro_error}')
            return False

    except Exception as e:
        logger.info(f'[NAV][ERRO] Falha na navegação: {e}')
        return False



def iniciar_fluxo_robusto(driver: WebDriver) -> ResultadoFluxo:
    """Executa o fluxo de Mandado via engine-based da entrada API."""
    logger.info('[FLUXO] Iniciando Mandado via entrada API (engine-based)')

    progresso_before = carregar_progresso()
    count_before = len(progresso_before.get('processos_executados', []))

    from core.resultado_execucao import ResultadoExecucao

    try:
        success = bool(processar_mandados_devolvidos_api(driver))
    except Exception as e:
        logger.info(f'[FLUXO][ERRO] processar_mandados_devolvidos_api falhou: {e}')
        success = False

    progresso_after = carregar_progresso()
    count_after = len(progresso_after.get('processos_executados', []))
    processed = max(0, count_after - count_before)

    return ResultadoExecucao(sucesso=success, processos=processed)

# 3. Funções de Processamento

