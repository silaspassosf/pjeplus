"""Mandado - Apoio a Fluxos (Outros + Utilitarios)

Consolidado de:
    processamento_outros.py — ramo Oficial de Justica / Outros
    utils_sigilo.py — sigilo de certidao e anexos
    utils_lembrete.py — lembrete de bloqueio
    atos_wrapper.py — wrappers de atos usados por regras

Entrypoint publico: fluxo_mandados_outros()
"""

# ════════════════════════════════════════
# Imports (consolidados dos 4 arquivos)
# ════════════════════════════════════════

import os
import time
import unicodedata
from typing import Optional, Any, List, Tuple

from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.by import By

from Fix.abas import validar_conexao_driver
from Fix.extracao import extrair_direto, extrair_documento, criar_lembrete_posit
from Fix.log import logger
from Fix.selenium_base import aguardar_e_clicar

from atos import (
    ato_judicial,
    ato_meios,
    ato_pesquisas,
    ato_crda,
    ato_crte,
    ato_bloq,
    ato_idpj,
    ato_termoE,
    ato_termoS,
    ato_edital,
    pec_idpj,
    mov_arquivar,
    ato_meiosub,
)


# ════════════════════════════════════════
# 1. atos_wrapper.py — re-export de atos/
# ════════════════════════════════════════

__all__ = [
    'ato_judicial',
    'ato_meios',
    'ato_pesquisas',
    'ato_crda',
    'ato_crte',
    'ato_bloq',
    'ato_idpj',
    'ato_termoE',
    'ato_termoS',
    'ato_edital',
    'pec_idpj',
    'mov_arquivar',
    'ato_meiosub',
]


# ════════════════════════════════════════
# 2. utils_lembrete.py — lembrete de bloqueio
# ════════════════════════════════════════

def lembrete_bloq(driver: WebDriver, debug: bool = False) -> bool:
    """Wrapper compatível - delegado para criar_lembrete_posit genérico."""
    return criar_lembrete_posit(
        driver,
        titulo="Bloqueio pendente",
        conteudo="processar após IDPJ",
        debug=debug
    )


# ════════════════════════════════════════
# 3. utils_sigilo.py — sigilo de certidao e anexos
# ════════════════════════════════════════

def retirar_sigilo(elemento: WebElement, driver: Optional[WebDriver] = None, debug: bool = False) -> bool:
    """
     DIRETO E SIMPLES: Verifica tl-nao-sigiloso (AZUL) antes de qualquer ação.

    Lógica clara:
    1. Busca botão de sigilo
    2. Se TEM tl-nao-sigiloso (azul) → retorna True (JÁ SEM SIGILO)
    3. Se TEM tl-sigiloso (vermelho) → clica para remover
    4. Caso contrário → retorna True (sem sigilo)

    Args:
        elemento: WebElement do documento na timeline
        driver: WebDriver Selenium
        debug: Exibir logs detalhados

    Returns:
        True se sigilo foi removido ou já estava removido, False em erro
    """
    if not elemento:
        return False

    if not driver:
        try:
            if hasattr(elemento, '_parent') and hasattr(elemento._parent, 'execute_script'):
                driver = elemento._parent
            else:
                return False
        except Exception:
            return False

    def _link_documento() -> Optional[WebElement]:
        links = elemento.find_elements(By.CSS_SELECTOR, 'a.tl-documento')
        if not links:
            return None
        for link in links:
            role = (link.get_attribute('role') or '').lower()
            target = (link.get_attribute('target') or '').lower()
            if role == 'button' or target != '_blank':
                return link
        return links[-1]

    def _tem_sigilo_link() -> bool:
        link = _link_documento()
        if not link:
            return False
        classes = (link.get_attribute('class') or '').lower()
        if debug:
            logger.info(f"[SIGILO_DEBUG] Classes link documento: {classes}")
        return 'is-sigiloso' in classes

    try:
        if not _tem_sigilo_link():
            if debug:
                logger.info('[SIGILO_DEBUG] Link sem is-sigiloso → JÁ SEM SIGILO')
            return True

        btn_sigilo = None
        seletores = [
            'pje-doc-sigiloso button',
            'pje-doc-sigiloso span button',
            'button i.fa-wpexplorer',
            'i.fa-wpexplorer.tl-sigiloso',
            'i.fa-wpexplorer',
        ]
        for seletor in seletores:
            try:
                candidato = elemento.find_element(By.CSS_SELECTOR, seletor)
                if candidato.is_displayed():
                    btn_sigilo = candidato
                    break
            except Exception:
                continue

        if not btn_sigilo:
            if debug:
                logger.error('[SIGILO_DEBUG] Botão de sigilo não encontrado com link is-sigiloso ativo')
            return False

        try:
            driver.execute_script('arguments[0].click();', btn_sigilo)
        except Exception:
            btn_sigilo.click()

        for _ in range(8):
            time.sleep(0.25)
            try:
                if not _tem_sigilo_link():
                    if debug:
                        logger.info('[SIGILO_DEBUG] is-sigiloso removido após clique')
                    return True
            except Exception:
                pass

        if debug:
            logger.error('[SIGILO_DEBUG] Clique executado, mas classe is-sigiloso permaneceu')
        return False

    except Exception as e:
        if debug:
            logger.error(f"[SIGILO_DEBUG] Erro geral: {e}")
        return False


def retirar_sigilo_fluxo_argos(driver: WebDriver, documentos_sequenciais: List[WebElement], log: bool = True, debug: bool = False) -> dict:
    """
     FUNÇÃO ÚNICA PARA TODO O FLUXO DE REMOÇÃO DE SIGILO DO ARGOS

    Respeita a ORDEM OBRIGATÓRIA do fluxo ARGOS:
    1º - Certidão de devolução (PRIMEIRO)
    2º - Demais documentos: certidão expedição, intimação, decisão, planilha

    Args:
        driver: WebDriver Selenium
        documentos_sequenciais: Lista de WebElements dos documentos
        log: Exibir logs detalhados
        debug: Ativar modo debug com detalhes das classes CSS

    Returns:
        dict com status de cada etapa e documentos processados
    """
    from core.resultado_execucao import ResultadoExecucao
    if not documentos_sequenciais:
        return ResultadoExecucao(sucesso=False, status='FALHA', erro='nenhum_documento', detalhes={'etapa_erro': 'nenhum_documento'})

    resultado = {
        'sucesso': True,
        'certidao_devolucao': None,
        'demais_documentos': [],
        'total_processados': 0
    }

    if log:
        pass

    # =======================================================
    # ETAPA 1: CERTIDÃO DE DEVOLUÇÃO (PRIMEIRO - DOCUMENTO ÚNICO!)
    # =======================================================
    certidao_encontrada = None
    # No fluxo Argos, buscar a certidão mais recente que está no FINAL da lista
    # A lista vem do topo para baixo da timeline, mas precisamos buscar de baixo para cima
    # para pegar o documento mais recente do bloco (mesmo comportamento do legado)
    for doc in reversed(documentos_sequenciais):
        try:
            texto = doc.text.strip().lower()
            # Marcador único: "certidão de devolução" (documento único, sempre o primeiro)
            if "certidão de devolução" in texto or "certidao de devolucao" in texto:
                certidao_encontrada = doc
                if log:
                    logger.info(f'[SIGILO_ARGOS] Certidão de devolução identificada: {texto[:50]}...')
                break
        except:
            continue

    if not certidao_encontrada:
        if log:
            logger.info("[SIGILO_ARGOS] Certidão de devolução não encontrada - pulando")
        resultado['certidao_devolucao'] = {'status': 'nao_encontrada'}
    else:
        # Verificar se tem sigilo (lógica simplificada do legado)
        links_doc = certidao_encontrada.find_elements(By.CSS_SELECTOR, 'a.tl-documento')
        tem_sigilo = False

        if links_doc:
            link_correto = None
            for link in links_doc:
                target = link.get_attribute('target') or ''
                role = link.get_attribute('role') or ''
                if role == 'button' or target != '_blank':
                    link_correto = link
                    break

            if not link_correto and links_doc:
                link_correto = links_doc[-1]

            if link_correto:
                classes_link = (link_correto.get_attribute('class') or '')
                tem_sigilo = 'is-sigiloso' in classes_link

                if debug:
                    logger.info(f"[SIGILO_ARGOS][DEBUG] Classes do link: {classes_link}")
                    logger.info(f"[SIGILO_ARGOS][DEBUG] tem_sigilo (pré-check): {tem_sigilo}")

        if not tem_sigilo:
            if log:
                logger.info("[SIGILO_ARGOS] Certidão JÁ SEM SIGILO (verificação prévia)")
            resultado['certidao_devolucao'] = {'status': 'ja_sem_sigilo'}
        else:
            if log:
                logger.info("[SIGILO_ARGOS] Removendo sigilo da certidão (detectado via is-sigiloso)...")
            # A função retirar_sigilo fará verificação definitiva via aria-label
            if retirar_sigilo(certidao_encontrada, driver, debug=debug):
                if log:
                    logger.info("[SIGILO_ARGOS] Sigilo removido com sucesso")
                resultado['certidao_devolucao'] = {'status': 'removido'}
                resultado['total_processados'] += 1
            else:
                if log:
                    logger.error("[SIGILO_ARGOS] Falha ao remover sigilo")
                resultado['certidao_devolucao'] = {'status': 'erro'}
                resultado['sucesso'] = False

    # =======================================================
    # ETAPA 2: DEMAIS DOCUMENTOS ESPECÍFICOS (DENTRO DO BLOCO)
    # =======================================================
    tipos_especificos = {
        'certidao_pesquisa': {
            'palavras': ['certidão de pesquisa', 'certidao de pesquisa', 'certidão de devolução de pesquisa', 'certidao de devolucao de pesquisa'],
            'limite': 1,
            'encontrados': []
        },
        'certidao_expedicao': {
            'palavras': ['certidão de expedição', 'certidao de expedicao'],
            'limite': 1,
            'encontrados': []
        },
        'intimacao': {
            'palavras': ['intimação(', 'intimacao(', 'intimação', 'intimacao'],
            'limite': 1,
            'encontrados': []
        },
        'decisao': {
            'palavras': ['decisão', 'decisao'],
            'limite': 1,
            'encontrados': []
        },
        'planilha': {
            'palavras': ['planilha de atualização', 'planilha de atualizacao'],
            'limite': 1,
            'encontrados': []
        }
    }

    # Encontrar onde está a decisão (fim do bloco)
    idx_decisao = None
    for idx in range(len(documentos_sequenciais)):
        texto = documentos_sequenciais[idx].text.strip().lower()
        if "decisão(" in texto or "decisao(" in texto:
            idx_decisao = idx
            if debug:
                logger.info(f"[SIGILO_ARGOS][DEBUG] Decisão no índice {idx} - FIM DO BLOCO")
            break

    if idx_decisao is None:
        if log:
            logger.info("[SIGILO_ARGOS] Decisão não encontrada")
        return resultado

    # Processar índices 1, 2, 3... até ANTES da decisão
    for idx in range(1, idx_decisao):
        doc = documentos_sequenciais[idx]
        texto = doc.text.strip().lower()

        for tipo_nome, tipo_config in tipos_especificos.items():
            if len(tipo_config['encontrados']) >= tipo_config['limite']:
                continue

            for palavra in tipo_config['palavras']:
                if palavra in texto:
                    tipo_config['encontrados'].append({
                        'elemento': doc,
                        'texto': texto[:50],
                        'palavra': palavra
                    })
                    break

    # Adicionar decisão (índice 4 - fim do bloco)
    doc_decisao = documentos_sequenciais[idx_decisao]
    texto_decisao = doc_decisao.text.strip().lower()
    tipos_especificos['decisao']['encontrados'].append({
        'elemento': doc_decisao,
        'texto': texto_decisao[:50],
        'palavra': 'decisão'
    })

    # Remover sigilo dos demais documentos
    for tipo_nome, tipo_config in tipos_especificos.items():
        if not tipo_config['encontrados']:
            continue

        for doc_info in tipo_config['encontrados']:
            elemento = doc_info['elemento']
            texto = doc_info['texto']

            # Verificar se tem sigilo
            links_doc = elemento.find_elements(By.CSS_SELECTOR, 'a.tl-documento')
            tem_sigilo = False

            if links_doc:
                link_correto = None
                for link in links_doc:
                    target = link.get_attribute('target') or ''
                    role = link.get_attribute('role') or ''
                    if role == 'button' or target != '_blank':
                        link_correto = link
                        break

                if not link_correto and links_doc:
                    link_correto = links_doc[-1]

                if link_correto:
                    classes_link = (link_correto.get_attribute('class') or '')
                    tem_sigilo = 'is-sigiloso' in classes_link

                    if debug:
                        logger.info(f"[SIGILO_ARGOS][DEBUG] {tipo_nome.upper()} - Classes link: {classes_link}")
                        logger.info(f"[SIGILO_ARGOS][DEBUG] {tipo_nome.upper()} - tem_sigilo: {tem_sigilo}")

            if not tem_sigilo:
                if log:
                    logger.info(f"[SIGILO_ARGOS] {tipo_nome.upper()}: JÁ SEM SIGILO - {texto}")
                resultado['demais_documentos'].append({
                    'tipo': tipo_nome,
                    'texto': texto,
                    'status': 'ja_sem_sigilo'
                })
            else:
                if log:
                    logger.info(f"[SIGILO_ARGOS] {tipo_nome.upper()}: Removendo sigilo...")
                if retirar_sigilo(elemento, driver, debug=debug):
                    if log:
                        logger.info(f"[SIGILO_ARGOS] {tipo_nome.upper()}: Removido")
                    resultado['demais_documentos'].append({
                        'tipo': tipo_nome,
                        'texto': texto,
                        'status': 'removido'
                    })
                    resultado['total_processados'] += 1
                else:
                    if log:
                        logger.error(f"[SIGILO_ARGOS] {tipo_nome.upper()}: Erro")
                    resultado['demais_documentos'].append({
                        'tipo': tipo_nome,
                        'texto': texto,
                        'status': 'erro'
                    })
                    resultado['sucesso'] = False

    if log:
        logger.info(f"[SIGILO_ARGOS] Concluído: {resultado['total_processados']} documentos processados")

    return resultado


def retirar_sigilo_certidao_devolucao_primeiro(driver: WebDriver, documentos_sequenciais: List[WebElement], log: bool = True) -> bool:
    """COMPATIBILIDADE: Chama retirar_sigilo_fluxo_argos e retorna apenas status da certidão."""
    resultado = retirar_sigilo_fluxo_argos(driver, documentos_sequenciais, log)
    cert_status = resultado.get('certidao_devolucao', {}).get('status', 'erro')
    return cert_status in ['removido', 'ja_sem_sigilo', 'nao_encontrada']


def retirar_sigilo_demais_documentos_especificos(driver, documentos_sequenciais, log=True):
    """COMPATIBILIDADE: Chama retirar_sigilo_fluxo_argos e retorna lista de demais documentos."""
    resultado = retirar_sigilo_fluxo_argos(driver, documentos_sequenciais, log)
    return resultado.get('demais_documentos', [])


def retirar_sigilo_documentos_especificos(driver, documentos_sequenciais, log=True):
    """
     FUNÇÃO EFICIENTE - Remove sigilo APENAS dos documentos específicos fornecidos:
    Os documentos_sequenciais já vêm filtrados da buscar_documentos_sequenciais()
    MÁXIMO 5 documentos: 1 certidão devolução, 1 certidão expedição, 1 intimação, 1 decisão, 1 planilha

    NADA MAIS que isso - SEM VARRER TIMELINE INTEIRA!
    """
    if not documentos_sequenciais:
        return []

    #  EFICIÊNCIA: Os documentos já vêm filtrados, apenas remover sigilo diretamente
    documentos_processados = []
    total_processados = 0

    #  PROCESSAMENTO DIRETO: Remove sigilo apenas dos documentos fornecidos
    for i, elemento in enumerate(documentos_sequenciais):
        try:
            texto = elemento.text.strip()[:50] if elemento.text else f"DOCUMENTO_{i+1}"

            resultado_sigilo = retirar_sigilo(elemento, driver)

            if resultado_sigilo:
                documentos_processados.append({
                    'indice': i+1,
                    'texto': texto,
                    'status': 'sucesso'
                })
                total_processados += 1
            else:
                documentos_processados.append({
                    'indice': i+1,
                    'texto': texto,
                    'status': 'falha'
                })

        except Exception as e:
            if log:
                logger.error(f"[SIGILO_ESPECÍFICO]  Erro ao processar documento {i+1}: {e}")
            documentos_processados.append({
                'indice': i+1,
                'texto': texto if 'texto' in locals() else f"DOCUMENTO_{i+1}",
                'status': 'erro',
                'erro': str(e)
            })

    #  RELATÓRIO FINAL
    if log:
        for doc in documentos_processados:
            status_icon = "" if doc['status'] == 'sucesso' else "" if doc['status'] == 'erro' else ""

    return documentos_processados


# ════════════════════════════════════════
# 4. processamento_outros.py — ramo Oficial de Justica / Outros
# ════════════════════════════════════════

# Controla se o fluxo de "outros" pode automaticamente invocar atos
# Defina a variável de ambiente PJE_ALLOW_MANDADO_ATOS=1 para permitir
ALLOW_MANDADO_ATOS = os.environ.get('PJE_ALLOW_MANDADO_ATOS', '0').lower() in ('1', 'true', 'yes', 'y')


def ultimo_mdd(driver: WebDriver, log: bool = True) -> Tuple[Optional[str], Optional[Any]]:
    """
    Busca o último mandado na timeline (item com texto começando por 'Mandado' e ícone de gavel) e retorna (nome_autor, elemento_mandado).
    Versão robusta com verificações de conectividade.
    """
    try:
        # Verificação inicial de conexão
        if not validar_conexao_driver(driver, contexto="MDD_INICIO"):
            if log:
                logger.error('[MDD][ERRO_FATAL] Driver em estado inválido ao buscar mandado')
            return None, None

        # Usando aguardar_e_clicar ao invés de find_elements direto para maior robustez
        timeline = aguardar_e_clicar(driver, 'ul.timeline-container', timeout=5)
        if not timeline:
            if log:
                logger.error('[MDD][ERRO] Timeline não encontrada, tentando método direto')
            itens = driver.find_elements(By.CSS_SELECTOR, 'li.tl-item-container')
        else:
            itens = timeline.find_elements(By.CSS_SELECTOR, 'li.tl-item-container')

        if not itens:
            if log:
                logger.warning('[MDD][ALERTA] Nenhum item encontrado na timeline')
            return None, None

        for idx, item in enumerate(itens):
            try:
                # Verificação periódica de conexão durante loop
                if idx % 10 == 0 and idx > 0:  # Verificar a cada 10 itens para não impactar performance
                    if not validar_conexao_driver(driver, contexto=f"MDD_LOOP_{idx}"):
                        if log:
                            logger.error(f'[MDD][ERRO_FATAL] Driver em estado inválido durante loop (item {idx})')
                        return None, None

                # Usa wait com timeout curto para não prejudicar performance
                link = aguardar_e_clicar(driver, item.find_element(By.CSS_SELECTOR, 'a.tl-documento:not([target="_blank"])'), timeout=1)
                if not link:
                    continue

                doc_text = link.text.strip().lower()
                if doc_text.startswith('mandado'):
                    # Procura ícone de gavel (fa-gavel)

                    icones = item.find_elements(By.CSS_SELECTOR, 'i.fa-gavel')
                    if not icones:
                        continue  # Não é mandado assinado por oficial
                    # Procura nome do autor próximo ao link ou assinatura
                    nome_autor = None
                    # Tenta encontrar assinatura padrão
                    try:
                        assinatura = item.find_element(By.CSS_SELECTOR, '.assinatura, .autor, .assinante, .nome-assinatura')
                        nome_autor = assinatura.text.strip()
                    except Exception:
                        # Fallback: procura texto logo após o link
                        try:
                            spans = item.find_elements(By.CSS_SELECTOR, 'span')
                            for s in spans:
                                s_text = s.text.strip()
                                if s_text and s_text.lower() != doc_text:
                                    nome_autor = s_text
                                    break
                        except Exception:
                            pass
                    return nome_autor, item
            except Exception as e:
                if log:
                    logger.error(f'[MDD][DEBUG] Erro ao processar item {idx}: {e}')
                continue

        # Verificação final de conexão
        if not validar_conexao_driver(driver, contexto="MDD_FIM"):
            if log:
                logger.error('[MDD][ERRO_FATAL] Driver em estado inválido ao finalizar busca de mandado')
            return None, None

        return None, None
    except Exception as e:
        if log:
            logger.error(f'[MDD][ERRO] Falha ao buscar último mandado: {e}')
        return None, None


def fluxo_mandados_outros(driver: WebDriver, log: bool = True) -> None:
    """
    Processa o fluxo de mandados não-Argos (Oficial de Justiça).
    1. Verifica se é certidão de oficial através do cabeçalho
    2. Extrai e analisa o texto da certidão
    3. Verifica padrões de mandado positivo/negativo
    4. Cria GIGS ou executa atos conforme resultado
    """
    try:
        # Usa aguardar_e_clicar mais robusto ao invés de find_element direto
        cabecalho = aguardar_e_clicar(driver, ".cabecalho-conteudo .mat-card-title", timeout=5, retornar_elemento=True)
        if not cabecalho:
            if log:
                logger.warning('[MANDADOS][OUTROS][ALERTA] Cabeçalho não encontrado. Tentando fallback.')
            cabecalho = driver.find_element(By.CSS_SELECTOR, ".cabecalho-conteudo .mat-card-title")

        titulo_documento = cabecalho.text.lower()
        if log:
            logger.info(f"[MANDADOS][OUTROS] Cabeçalho detectado: {cabecalho.text}")

        eh_certidao_oficial = any(p in titulo_documento for p in [
            "certidão de oficial",
            "certidão de oficial de justiça"
        ])

        if not eh_certidao_oficial:
            return

    except Exception as e:
        if log:
            logger.error(f"[MANDADOS][OUTROS][ERRO] Erro ao verificar cabeçalho: {e}. Criando GIGS fallback.")
        # REMOVIDO: GIGS 0/PZ MDD considerado inútil

        # Fechamento simples sem verificações excessivas (igual ao ARGOS)
        return

    def analise_padrao(texto):
        # Diagnostic: confirmar entrada em analise_padrao
        logger.info('[MANDADOS][OUTROS] ENTER analise_padrao()')
        # Normalizar texto removendo acentos para facilitar matching
        try:
            texto_norm = ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')
        except Exception as e:
            logger.info(f'[MANDADOS][OUTROS] analise_padrao: falha na normalizacao: {e}')
            texto_norm = texto
        texto_lower = texto_norm.lower()
        if log:
            logger.info(f"[MANDADOS][OUTROS] Texto (normalizado) para análise (len={len(texto_lower)}):\n{texto_lower[:800]}\n---Fim do documento---")

        padrao_positivo = any(p in texto_lower for p in [
            "citei",
            "intimei",
            "recebeu o mandado",
            "de tudo ficou ciente"
            "procedi à intimação",
            "procedi à citação",
            "procedi à entrega do mandado",
            "procedi à penhora",
            "penhorei"

        ])
        padrao_negativo = any(p in texto_lower for p in [
            "não localizado",
            "resultado negativo",
            "diligencias negativas",
            "diligência negativa",
            "não encontrado",
            "deixei de citar",
            "deixei de efetuar",
            "deixei de comparacer",
            "deixei de intimar",
            "deixei de penhorar",
            "não logrei êxito",
            "desconhecido no local",
            "não foi possível efetuar"
            "parou de responder",
            "não foi possível localizar",
        ])

        padrao_cancelamento_total = any(p in texto_lower for p in [
            "ordem de cancelamento total",
        ])
        if padrao_cancelamento_total:
            return None

        if padrao_positivo:
            pass
        elif padrao_negativo:
            if log:
                logger.info("Padrão de mandado NEGATIVO encontrado no texto.")  # NOVA REGRA: localizar mandado anterior na timeline, extrair conteúdo e, se contiver 'penhora', chamar ato_meios
                logger.info('[MANDADOS][OUTROS] padrao_negativo detectado — invocando ultimo_mdd()')
                autor_ant, elemento_ant = ultimo_mdd(driver, log=log)
                if elemento_ant:
                    try:
                        link_ant = elemento_ant.find_element(By.CSS_SELECTOR, 'a.tl-documento:not([target="_blank"])')
                        # Comportamento idêntico ao p2b: abrir link, aguardar estabilização e chamar extrair_direto
                        try:
                            aguardar_e_clicar(driver, link_ant)
                        except Exception:
                            try:
                                driver.execute_script("arguments[0].click();", link_ant)
                            except Exception:
                                pass
                        # Usar WebDriverWait ao invés de time.sleep
                        from Fix.core import wait_for_page_load
                        wait_for_page_load(driver, timeout=5)
                        try:
                            texto_mandado_ant_result = extrair_direto(driver, timeout=10, debug=True, formatar=True)
                        except Exception:
                            texto_mandado_ant_result = extrair_documento(driver, regras_analise=None, timeout=10, log=log)
                        texto_mandado_ant = texto_mandado_ant_result.get('conteudo', '') if texto_mandado_ant_result and texto_mandado_ant_result.get('sucesso') else None
                        if texto_mandado_ant and 'penhora' in texto_mandado_ant.lower():
                            if not ALLOW_MANDADO_ATOS:
                                logger.info('[MANDADOS][OUTROS] atos automáticos desabilitados (PJE_ALLOW_MANDADO_ATOS=0) — pulando ato_meios()')
                            else:
                                logger.info('[MANDADOS][OUTROS] Invocando ato_meios() (do mandado anterior)')
                                try:
                                    ato_meios(driver)
                                    logger.info('[MANDADOS][OUTROS] ato_meios() retornou')
                                except Exception as e:
                                    logger.error(f'[MANDADOS][OUTROS] erro em ato_meios(): {e}')
                    except Exception as e:
                        if log:
                            logger.error(f"Falha ao processar mandado anterior: {e}")
            # Verifica se contém "penhora de bens" no texto
            if "penhora de bens" in texto_lower:
                if not ALLOW_MANDADO_ATOS:
                    logger.info('[MANDADOS][OUTROS] atos automáticos desabilitados — pulando ato_meios() (penhora de bens)')
                else:
                    logger.info('[MANDADOS][OUTROS] Invocando ato_meios() (penhora de bens)')
                    try:
                        ato_meios(driver)
                        logger.info('[MANDADOS][OUTROS] ato_meios() retornou')
                    except Exception as e:
                        logger.error(f'[MANDADOS][OUTROS] erro em ato_meios(): {e}')
            elif "deixei de penhorar" in texto_lower:
                if not ALLOW_MANDADO_ATOS:
                    logger.info('[MANDADOS][OUTROS] atos automáticos desabilitados — pulando ato_meios() (deixei de penhorar)')
                else:
                    logger.info('[MANDADOS][OUTROS] Invocando ato_meios() (deixei de penhorar)')
                    try:
                        ato_meios(driver)
                        logger.info('[MANDADOS][OUTROS] ato_meios() retornou')
                    except Exception as e:
                        logger.error(f'[MANDADOS][OUTROS] erro em ato_meios(): {e}')
            else:
                # Busca último mandado na timeline
                autor, elemento = ultimo_mdd(driver, log=log)
                if autor:
                    if 'silas passos' in autor.lower():
                        if not ALLOW_MANDADO_ATOS:
                            logger.info('[MANDADOS][OUTROS] atos automáticos desabilitados — pulando ato_edital()')
                        else:
                            logger.info('[MANDADOS][OUTROS] Invocando ato_edital()')
                            try:
                                ato_edital(driver)
                                logger.info('[MANDADOS][OUTROS] ato_edital() retornou')
                            except Exception as e:
                                logger.error(f'[MANDADOS][OUTROS] erro em ato_edital(): {e}')
                    else:
                        pass
                else:
                    pass
        else:
            pass
    try:
        # ALWAYS emit a short diagnostic log before attempting extraction
        logger.info('[MANDADOS][OUTROS] Invocando extrair_direto() (debug ON para diagnóstico)')
        texto_result = extrair_direto(driver, timeout=10, debug=True, formatar=True)
        logger.info(f'[MANDADOS][OUTROS] extrair_direto returned (diagnostic): {bool(texto_result and texto_result.get("sucesso"))}')
    except Exception as e:
        logger.error(f'[MANDADOS][OUTROS] extrair_direto falhou: {e}')
        texto_result = None

    if not texto_result or not texto_result.get('sucesso'):
        if log:
            logger.info('[MANDADOS][OUTROS] extrair_direto não retornou conteúdo; usando extrair_documento() fallback')
        texto_tuple = extrair_documento(driver, regras_analise=None, timeout=10, log=log)
        texto = texto_tuple[0] if texto_tuple and texto_tuple[0] else None
    else:
        texto = texto_result.get('conteudo', '')
    # Diagnostic: confirmar atribuição de texto
    logger.info(f'[MANDADOS][OUTROS] Texto atribuído len={len(texto) if texto else 0}')
    if not texto:
        if log:
            logger.error("[MANDADOS][OUTROS][ERRO] Não foi possível extrair o texto da certidão.")
        return
    if log:
        logger.info(f"[MANDADOS][OUTROS] Texto extraído (primeiros 200 chars): {texto[:200].replace(chr(10),' ')}")
    logger.info('[MANDADOS][OUTROS] Chamando analise_padrao()')
    # Analisar o texto extraído e executar ações padrão (positivo/negativo/cancelamento)
    try:
        analise_padrao(texto)
        logger.info('[MANDADOS][OUTROS] analise_padrao returned')
    except Exception as e:
        if log:
            logger.error(f"[MANDADOS][OUTROS][ERRO] Falha na análise padrão: {e}")
    return
