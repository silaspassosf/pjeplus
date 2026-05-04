"""Prazo - Loop Orquestrador

Consolidado de: __init__.py (loop), loop_base.py, loop_helpers.py, loop_api.py, loop_ciclo1.py

Entrypoint publico: loop_prazo()
"""
# ── Imports ──
import logging
import math
import re
import time
from contextlib import contextmanager
from typing import Dict, Any, List, Optional, Tuple, Union
from concurrent.futures import ThreadPoolExecutor, as_completed

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from Fix.core import (
    aguardar_renderizacao_nativa,
    aplicar_filtro_100,
    com_retry,
)
from Fix.variaveis import PjeApiClient, obter_gigs_com_fase, session_from_driver

from core.resultado_execucao import ResultadoExecucao

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════
# ── 1. loop_base.py ──
# ═══════════════════════════════════════════════

# ===== CONFIGURAÇÃO DE PERFORMANCE =====
# Número de workers para verificação paralela da API GIGS
# Ajuste conforme sua conexão: 5-10 (estável), 15-20 (rápida), 3-5 (lenta)
GIGS_API_MAX_WORKERS = 20

# ===== DEPURAÇÃO INTERATIVA (CICLO 1 + CICLO 2) =====
DEBUG_PAUSAS_LOOP = False
_PAUSA_ACUMULADA_S = 0.0


def pausar_confirmacao(acao: str, detalhe: str = '') -> bool:
    """Pausa interativa para confirmação manual de cada ação do loop."""
    global _PAUSA_ACUMULADA_S
    if not DEBUG_PAUSAS_LOOP:
        return True

    msg = f"[PAUSA][{acao}] {detalhe}".strip()
    logger.info(msg)
    inicio_pausa = time.perf_counter()
    try:
        resposta = input(f"{msg} -> Executar? [ENTER=sim / n=abortar]: ").strip().lower()
        duracao_pausa = time.perf_counter() - inicio_pausa
        _PAUSA_ACUMULADA_S += duracao_pausa
        logger.info(f"[PAUSA][TEMPO] {acao}: {duracao_pausa:.3f}s")
        if resposta in ('n', 'nao', 'não', 'no'):
            logger.info(f"[PAUSA][{acao}] Abortado pelo usuário")
            return False
        return True
    except Exception:
        duracao_pausa = time.perf_counter() - inicio_pausa
        _PAUSA_ACUMULADA_S += duracao_pausa
        logger.info(f"[PAUSA][TEMPO] {acao}: {duracao_pausa:.3f}s")
        logger.info(f"[PAUSA][{acao}] Sem entrada interativa - continuando")
        return True


def log_seletor_vencedor(acao: str, by: By, seletor: str) -> None:
    """Registra qual seletor funcionou em ações com múltiplas tentativas."""
    logger.info(f"[SELETOR][{acao}] Vencedor: by={by} seletor={seletor}")


@contextmanager
def medir_latencia(etapa: str):
    """Mede latência de uma etapa e registra início/fim no log."""
    inicio = time.perf_counter()
    pausa_inicio = _PAUSA_ACUMULADA_S
    logger.info(f"[LATENCIA][INICIO] {etapa}")
    try:
        yield
    finally:
        duracao_bruta = time.perf_counter() - inicio
        pausa_dentro = _PAUSA_ACUMULADA_S - pausa_inicio
        duracao_liquida = max(0.0, duracao_bruta - pausa_dentro)
        logger.info(f"[LATENCIA][FIM] {etapa}: liquida={duracao_liquida:.3f}s (bruta={duracao_bruta:.3f}s, pausa={pausa_dentro:.3f}s)")


# ── Scripts JavaScript ──

SCRIPT_SELECAO_GIGS_AJ_JT = '''
function selecionarProcessosPorGIGS(processosComGIGS) {
    console.log("🔍 Iniciando seleção de GIGS. Processos a selecionar:", processosComGIGS);

    let linhas = document.querySelectorAll('tr.cdk-drag');
    console.log("📊 Total de linhas encontradas:", linhas.length);

    let selecionados = 0;
    let padrao = /(\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4})/;

    linhas.forEach(function(linha, idx) {
        // Estratégia 1: Procurar em links <a>
        let numeroProcesso = null;
        let links = linha.querySelectorAll('a');
        for (let link of links) {
            let match = link.textContent.match(padrao);
            if (match) {
                numeroProcesso = match[1];
                break;
            }
        }

        // Estratégia 2: Procurar em toda a linha (fallback)
        if (!numeroProcesso) {
            let match = linha.textContent.match(padrao);
            if (match) {
                numeroProcesso = match[1];
            }
        }

        // Se encontrou processo, log e verifica se está na lista
        if (numeroProcesso) {
            console.log(`  [${idx}] Encontrado: ${numeroProcesso}, está na lista: ${processosComGIGS.includes(numeroProcesso)}`);

            // Se está na lista de GIGS, selecionar
            if (processosComGIGS.includes(numeroProcesso)) {
                let checkbox = linha.querySelector('mat-checkbox input[type="checkbox"]');
                console.log(`    ✓ Checkbox encontrado: ${checkbox !== null}, checked: ${checkbox ? checkbox.checked : 'N/A'}`);

                if (checkbox && !checkbox.checked) {
                    checkbox.click();
                    linha.style.backgroundColor = "#cce5ff";
                    selecionados++;
                    console.log(`    ✅ CLICOU no checkbox`);
                } else {
                    console.log(`    ⚠️ Checkbox não clicado (já estava checked ou não encontrado)`);
                }
            }
        }
    });

    console.log("✅ Seleção concluída. Total selecionados:", selecionados);
    return selecionados;
}
return selecionarProcessosPorGIGS(arguments[0]);
'''

SCRIPT_SELECAO_LIVRES = '''
try {
    let linhas = document.querySelectorAll('tr.cdk-drag');
    let selecionados = 0;
    linhas.forEach(function(linha){
        let prazo = linha.querySelector('td:nth-child(9) time');
        let prazoVazio = !prazo || !prazo.textContent.trim();
        let hasComment = linha.querySelector('i.fa-comment') !== null;
        let inputField = linha.querySelector('input[matinput]');
        let campoPreenchido = inputField && inputField.value.trim();
        let temLupa = linha.querySelector('td:nth-child(3) i.fa-search') !== null;
        if (prazoVazio && !hasComment && !campoPreenchido && !temLupa) {
            let checkbox = linha.querySelector('mat-checkbox input[type="checkbox"]');
            if (checkbox && !checkbox.checked) {
                checkbox.click();
                linha.style.backgroundColor = "#ffccd2";
                selecionados++;
            }
        }
    });
    return selecionados;
} catch(e) { return -1; }
'''

SCRIPT_SELECAO_LIVRES_API = '''
try {
    let processosComGigsApi = arguments[0] || [];
    let linhas = document.querySelectorAll('tr.cdk-drag');
    let selecionados = 0;
    let padrao = /(\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4})/;
    linhas.forEach(function(linha){
        let prazo = linha.querySelector('td:nth-child(9) time');
        let prazoVazio = !prazo || !prazo.textContent.trim();
        let hasComment = linha.querySelector('i.fa-comment') !== null;
        let inputField = linha.querySelector('input[matinput]');
        let campoPreenchido = inputField && inputField.value.trim();
        let temLupa = linha.querySelector('td:nth-child(3) i.fa-search') !== null;
        let numeroProcesso = null;
        let links = linha.querySelectorAll('a');
        for (let link of links) {
            let match = link.textContent.match(padrao);
            if (match) { numeroProcesso = match[1]; break; }
        }
        if (!numeroProcesso) {
            let match = linha.textContent.match(padrao);
            if (match) numeroProcesso = match[1];
        }
        let temGigsApi = numeroProcesso && processosComGigsApi.includes(numeroProcesso);
        if (prazoVazio && !hasComment && !campoPreenchido && !temLupa && !temGigsApi) {
            let checkbox = linha.querySelector('mat-checkbox input[type="checkbox"]');
            if (checkbox && !checkbox.checked) {
                checkbox.click();
                linha.style.backgroundColor = "#ffccd2";
                selecionados++;
            }
        }
    });
    return selecionados;
} catch(e) { return -1; }
'''

SCRIPT_SELECAO_NAO_LIVRES = '''
function selecionarProcessos(maxProcessos) {
    const linhas = document.querySelectorAll('tr.cdk-drag');
    let selecionados = 0;
    let totalNaoLivres = 0;

    // Primeiro conta total de não livres
    linhas.forEach(linha => {
        const prazo = linha.querySelector('td:nth-child(9) time');
        const prazoPreenchido = prazo && prazo.textContent.trim();
        const hasComment = linha.querySelector('i.fa-comment') !== null;
        const inputField = linha.querySelector('input[matinput]');
        const campoPreenchido = inputField && inputField.value.trim();

        if (prazoPreenchido || hasComment || campoPreenchido) {
            totalNaoLivres++;
        }
    });

    // Depois seleciona até maxProcessos
    for (const linha of linhas) {
        if (selecionados >= maxProcessos) break;

        const prazo = linha.querySelector('td:nth-child(9) time');
        const prazoPreenchido = prazo && prazo.textContent.trim();
        const hasComment = linha.querySelector('i.fa-comment') !== null;
        const inputField = linha.querySelector('input[matinput]');
        const campoPreenchido = inputField && inputField.value.trim();

        if (prazoPreenchido || hasComment || campoPreenchido) {
            const checkbox = linha.querySelector('mat-checkbox input[type="checkbox"]');
            if (checkbox && !checkbox.checked) {
                checkbox.click();
                linha.style.backgroundColor = "#d2ffcc";
                selecionados++;
            }
        }
    }
    return {selecionados, totalNaoLivres};
}
return selecionarProcessos(arguments[0]);
'''


# ═══════════════════════════════════════════════
# ── 2. loop_helpers.py ──
# ═══════════════════════════════════════════════

def _extrair_numero_processo_da_linha(linha_elemento: WebElement) -> Optional[str]:
    """Extrai número de processo de um elemento <tr> da tabela de atividades.

    Procura por <a> (links) que contenham o padrão de número de processo:
    NNNNNNN-DD.AAAA.J.TT.OOOO (formato processual brasileiro).

    Args:
        linha_elemento: elemento <tr> da tabela

    Returns:
        String com número do processo (formatado com pontos e hífen) ou None
    """
    try:
        # Buscar padrão processual usando regex
        padrao_processo = re.compile(r'(\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4})')

        # Estratégia 1: Procurar em links <a> (localização padrão no PJe)
        try:
            links = linha_elemento.find_elements(By.CSS_SELECTOR, 'a')
            for link in links:
                texto = link.text.strip()
                match = padrao_processo.search(texto)
                if match:
                    return match.group(1)
        except Exception:
            pass

        # Estratégia 2: Procurar em toda a linha (fallback)
        try:
            texto_linha = linha_elemento.text.strip()
            match = padrao_processo.search(texto_linha)
            if match:
                return match.group(1)
        except Exception:
            pass

        return None
    except Exception as e:
        logger.error(f'[LOOP_PRAZO][DEBUG] Erro ao extrair número do processo: {e}')
        return None


def selecionar_processos_nao_livres(driver: WebDriver, max_processos: int = 20) -> Tuple[int, bool]:
    """Seleciona processos não livres (com prazo preenchido, comentário ou campo preenchido).
    Retorna (quantidade_selecionada, ha_mais) onde ha_mais indica se há mais processos além do limite.
    """
    try:
        # Executar script JavaScript para seleção
        resultado = driver.execute_script(SCRIPT_SELECAO_NAO_LIVRES, max_processos)

        if resultado == -1:
            logger.error('[LOOP_PRAZO][ERRO] Falha no script de selecao de nao livres')
            return 0, False

        selecionados = resultado['selecionados']
        total_nao_livres = resultado['totalNaoLivres']

        ha_mais = total_nao_livres > max_processos

        logger.info('[LOOP_PRAZO][NAO_LIVRES] Selecionados %s processos nao livres (total: %s)', selecionados, total_nao_livres)

        if ha_mais:
            logger.info('[LOOP_PRAZO][NAO_LIVRES] Ha mais processos nao livres alem do limite (%s)', max_processos)

        return selecionados, ha_mais

    except Exception as e:
        logger.error('[LOOP_PRAZO][ERRO] Erro em selecionar_processos_nao_livres: %s: %s', type(e).__name__, e)
        return 0, False


# ═══════════════════════════════════════════════
# ── 3. loop_api.py ──
# ═══════════════════════════════════════════════

def _selecionar_processos_por_gigs_aj_jt(driver: WebDriver, client: 'PjeApiClient') -> int:
    """Seleciona processos com atividade GIGS AJ-JT apenas em fase LIQUIDAÇÃO."""
    try:
        if not pausar_confirmacao('CICLO2/GIGS_AJ_JT', 'Iniciar varredura e seleção de processos com AJ-JT'):
            return 0
        linhas = driver.find_elements(By.CSS_SELECTOR, 'tr.cdk-drag')
        processos_com_gigs = []

        for linha in linhas:
            try:
                numero_processo = _extrair_numero_processo_da_linha(linha)
                if not numero_processo:
                    continue

                dados_gigs_fase = obter_gigs_com_fase(client, numero_processo)
                if not dados_gigs_fase:
                    continue

                # Apenas Liquidação
                if dados_gigs_fase.get('fase') != 'Liquidação':
                    continue

                # Procurar por AJ-JT
                atividades_gigs = dados_gigs_fase.get('atividades_gigs', [])
                for atividade in atividades_gigs:
                    if 'AJ-JT' in atividade.get('observacao', ''):
                        processos_com_gigs.append(numero_processo)
                        break

            except Exception:
                continue

        if processos_com_gigs:
            if not pausar_confirmacao('CICLO2/GIGS_AJ_JT_SCRIPT', f'Selecionar {len(processos_com_gigs)} processo(s) via script JS'):
                return 0
            selecionados = driver.execute_script(
                SCRIPT_SELECAO_GIGS_AJ_JT,
                processos_com_gigs
            )
            logger.info(f'[CICLO2][GIGS-AJ-JT] {selecionados} processo(s) com AJ-JT selecionado(s)')
            try:
                aguardar_renderizacao_nativa(driver, 'span.total-registros', timeout=1.5)
            except Exception:
                try:
                    WebDriverWait(driver, 1.5).until(lambda d: d.execute_script('return document.readyState') == 'complete')
                except Exception:
                    pass
            return selecionados

        logger.info('[CICLO2][GIGS-AJ-JT] Nenhum processo com atividade AJ-JT encontrado')
        return 0

    except Exception as e:
        logger.error('[LOOP_PRAZO][ERRO] Erro em _selecionar_processos_por_gigs_aj_jt: %s: %s', type(e).__name__, e)
        return 0


def _verificar_processo_tem_xs(client: 'PjeApiClient', numero_processo: str) -> bool:
    """Verifica se o processo já tem atividade GIGS xs (sem prazo).

    Args:
        client: Cliente PJe API
        numero_processo: Número do processo formatado (NNNNNNN-DD.AAAA.J.TT.OOOO)

    Returns:
        True se processo já tem atividade xs (sem prazo), False caso contrário
    """
    try:
        # Buscar atividades GIGS do processo
        atividades = client.atividades_gigs(numero_processo)

        if not atividades:
            return False

        # Verificar se existe alguma atividade sem prazo (dataPrazo vazio/null)
        for atividade in atividades:
            data_prazo = atividade.get('dataPrazo')
            # Se dataPrazo é None, vazio ou string vazia, é atividade xs
            if not data_prazo or (isinstance(data_prazo, str) and not data_prazo.strip()):
                logger.debug('[LOOP_PRAZO][XS] Processo %s ja tem atividade xs no GIGS', numero_processo)
                return True

        return False
    except Exception as e:
        logger.error('[LOOP_PRAZO][ERRO] Erro ao verificar xs para %s: %s: %s', numero_processo, type(e).__name__, e)
        # Em caso de erro, retornar False para não bloquear o processo
        return False


def _obter_processos_com_gigs_api(client: 'PjeApiClient', numeros_processos: List[str], max_workers: int = 20) -> List[str]:
    """Retorna lista de números de processos que têm QUALQUER atividade GIGS (com ou sem prazo)."""
    com_gigs: List[str] = []

    def verificar_um(numero: str) -> Tuple[str, bool]:
        try:
            atividades = client.atividades_gigs(numero)
            return (numero, bool(atividades))
        except Exception:
            return (numero, False)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(verificar_um, num): num for num in numeros_processos}
        for future in as_completed(futures):
            try:
                numero, tem = future.result()
                if tem:
                    com_gigs.append(numero)
            except Exception:
                pass

    logger.info(f'[LOOP_PRAZO][GIGS_API] {len(com_gigs)}/{len(numeros_processos)} processos com gigs (API)')
    return com_gigs


# ═══════════════════════════════════════════════
# ── 4. loop_ciclo1.py ──
# ═══════════════════════════════════════════════

def ciclo1(driver: WebDriver, opcao_destino: str = 'Análise') -> Union[bool, str]:
    """
    Orquestra ciclo 1: filtro, marcação, suitcase, movimentação para painel 14.

    Returns:
        True: sucesso (pode ter mais processos, repetir loop)
        "complete_single_batch": sucesso, todos processos movidos em lote único (<20), não repetir
        False: erro crítico
        "no_more_processes": sem processos em liquidação/execução
        "marcar_todas_not_found_but_continue": marcar-todas não encontrado
        "go_to_ciclo2": batch indisponível no ciclo1, seguir para ciclo2
        "single_process": apenas 1 processo, batch não disponível
    """
    # lazy import to avoid circular dependency with loop_lote
    from .loop_lote import (
        _ciclo1_aplicar_filtro_fases,
        _ciclo1_marcar_todas,
        _ciclo1_abrir_suitcase,
        _ciclo1_aguardar_movimentacao_lote,
        _ciclo1_movimentar_destino,
        _ciclo1_retornar_lista,
    )

    # ===== VERIFICAÇÃO PRÉVIA: Lista já vazia antes do filtro =====
    try:
        mensagem_vazia = driver.find_elements(By.XPATH, "//span[contains(text(), 'Não há processos neste tema')]")
        if mensagem_vazia and any(el.is_displayed() for el in mensagem_vazia):
            logger.info('[CICLO1] Lista já vazia antes do filtro - nada a processar')
            return "no_more_processes"
    except Exception:
        pass  # Se erro ao verificar, segue normalmente

    with medir_latencia('CICLO1_APLICAR_FILTRO_FASES'):
        filtro_result = _ciclo1_aplicar_filtro_fases(driver)
    if filtro_result == "no_more_processes":
        logger.info('[CICLO1] Nenhum processo em liquidação/execução.')
        return "no_more_processes"
    if not filtro_result:
        return False

    # ===== VERIFICAR QUANTIDADE DE PROCESSOS =====
    # Se houver apenas 1 processo, o PJE não mostra o botão batch (suitcase)
    qtd_processos = 0
    try:
        try:
            aguardar_renderizacao_nativa(driver, 'span.total-registros', timeout=1)
        except Exception:
            try:
                WebDriverWait(driver, 1).until(lambda d: d.execute_script('return document.readyState') == 'complete')
            except Exception:
                pass
        processos = driver.find_elements(By.CSS_SELECTOR, 'tbody tr.tr-class')
        qtd_processos = len(processos)
        logger.info(f'[CICLO1] Detectados {qtd_processos} processo(s) na lista')

        if qtd_processos == 1:
            logger.info('[CICLO1] Apenas 1 processo detectado - PJE não disponibiliza batch (suitcase)')
            logger.info('[CICLO1] Prosseguindo para processamento individual (Fase 2)')
            return "single_process"
        elif qtd_processos == 0:
            logger.info('[CICLO1] Nenhum processo encontrado após filtro.')
            return "no_more_processes"

        # Otimização: se menos de 20, sabemos que processaremos tudo em um único lote
        if qtd_processos < 20:
            logger.info(f'[CICLO1] Lote único detectado ({qtd_processos} < 20) - não repetir após conclusão')
    except Exception as e:
        logger.info(f'[CICLO1] Erro ao contar processos: {e}')
        logger.info('[CICLO1] Continuando com o fluxo normal...')

    with medir_latencia('CICLO1_MARCAR_TODAS'):
        marcar_result = _ciclo1_marcar_todas(driver)
    if marcar_result == "marcar_todas_not_found_but_continue":
        logger.info('[CICLO1] Marcar-todas indisponível; prosseguindo para Fase 2.')
        return "marcar_todas_not_found_but_continue"
    elif marcar_result == "error":
        logger.info(f'[CICLO1] Falha em marcar-todas: {marcar_result}')
        return False
    elif marcar_result != "success":
        logger.info(f'[CICLO1] Retorno inesperado em marcar-todas: {marcar_result}')
        return False

    # Pequena pausa para garantir que a lista e UI estabilizaram
    try:
        logger.info('[CICLO1] Pausa breve (2s) para verificação visual da seleção antes do lote')
        aguardar_renderizacao_nativa(driver, timeout=2)
        # Também oferece a pausa interativa se DEBUG_PAUSAS_LOOP estiver habilitado
        pausar_confirmacao('CICLO1/VERIFICAR_SELECAO', 'Verificar seleção antes de abrir suitcase')
    except Exception:
        pass

    with medir_latencia('CICLO1_ABRIR_SUITCASE'):
        abriu_suitcase = _ciclo1_abrir_suitcase(driver)
    if not abriu_suitcase:
        logger.info('[CICLO1] Suitcase indisponível no ciclo1; redirecionando para ciclo2.')
        return "go_to_ciclo2"

    with medir_latencia('CICLO1_AGUARDAR_MOVIMENTACAO_LOTE'):
        aguardou_mov_lote = _ciclo1_aguardar_movimentacao_lote(driver)
    if not aguardou_mov_lote:
        logger.info('[CICLO1] Erro ao aguardar movimentação em lote.')
        return False

    with medir_latencia(f'CICLO1_MOVIMENTAR_DESTINO_{opcao_destino}'):
        moveu_destino = _ciclo1_movimentar_destino(driver, opcao_destino)
    if not moveu_destino:
        logger.info('[CICLO1] Erro ao movimentar destino.')
        return False

    with medir_latencia('CICLO1_RETORNAR_LISTA'):
        _ciclo1_retornar_lista(driver)

    # Retornar status baseado na quantidade inicial de processos
    if qtd_processos < 20:
        logger.info(f'[CICLO1] Ciclo 1 concluído - lote único ({qtd_processos} processos), não repetir')
        return "complete_single_batch"
    else:
        logger.info('[CICLO1] Ciclo 1 concluído - pode haver mais processos, verificar novamente')
        return True


# ═══════════════════════════════════════════════
# ── 5. __init__.py (loop parts) ──
# ═══════════════════════════════════════════════

def loop_prazo(driver: WebDriver) -> Dict[str, Any]:
    """Função wrapper que executa o fluxo completo de prazo (ciclo1 + ciclo2)"""
    try:
        # lazy import to avoid circular dependency with loop_execucao_final
        from .loop_execucao_final import ciclo2, ciclo3

        # 1. Navegar para Painel Global 14 (Análise)
        url_lista = "https://pje.trt2.jus.br/pjekz/painel/global/14/lista-processos"
        if not pausar_confirmacao('LOOP/NAVEGAR_PAINEL14', f'Navegar para {url_lista}'):
            return ResultadoExecucao(sucesso=False, status='FALHA', erro="Abortado pelo usuário em navegar painel 14")
        logger.info(f'[LOOP_PRAZO] Navegando para Painel Global 14: {url_lista}')
        driver.get(url_lista)
        # Espera dinâmica: aguardar elemento chave do painel de atividades
        try:
            WebDriverWait(driver, 12).until(
                EC.presence_of_element_located((By.XPATH, "//span[contains(text(), 'Fase processual')]") )
            )
            logger.info('[LOOP_PRAZO] Elemento "Fase processual" presente - prosseguindo')
        except Exception:
            logger.info('[LOOP_PRAZO] Timeout aguardando elemento "Fase processual" - prosseguindo mesmo assim')

        # FASE 1: Loop para ciclo1 (Análise)
        logger.info("[LOOP_PRAZO] Fase 1: Processando processos no painel 14")
        while True:
            resultado_ciclo1 = ciclo1(driver)

            if resultado_ciclo1 == "no_more_processes":
                logger.info("[LOOP_PRAZO] Não há mais processos para processar no ciclo1.")
                break
            elif resultado_ciclo1 == "single_process":
                logger.info("[LOOP_PRAZO] Apenas 1 processo detectado - pulando batch")
                break
            elif resultado_ciclo1 == "complete_single_batch":
                logger.info("[LOOP_PRAZO] Lote único processado (<20 processos) - não repetir ciclo1")
                break
            elif resultado_ciclo1 is False:
                logger.error("[LOOP_PRAZO] Erro crítico no ciclo1.")
                return ResultadoExecucao(sucesso=False, status='FALHA', erro="Falha em ciclo1")
            elif resultado_ciclo1 in ["go_to_ciclo2", "marcar_todas_not_found_but_continue"]:
                break

            logger.info("[LOOP_PRAZO] Ciclo 1 concluído. Verificando se há mais...")
            aguardar_renderizacao_nativa(driver, timeout=4)

        # 2. Navegar para Painel Global 8 (Cumprimento de providências)
        url_painel8 = "https://pje.trt2.jus.br/pjekz/painel/global/8/lista-processos"
        if not pausar_confirmacao('LOOP/NAVEGAR_PAINEL8', f'Navegar para {url_painel8}'):
            return ResultadoExecucao(sucesso=False, status='FALHA', erro="Abortado pelo usuário em navegar painel 8")
        logger.info(f'[LOOP_PRAZO] Navegando para Painel Global 8: {url_painel8}')
        driver.get(url_painel8)
        try:
            WebDriverWait(driver, 5).until(EC.url_contains("painel/global/8"))
        except Exception:
            pass

        # FASE 2: Ciclo 2
        logger.info("[LOOP_PRAZO] Fase 2: Executando ciclo 2")
        resultado_ciclo2 = ciclo2(driver)

        # FASE 3: Ciclo 3 (painel cumprimento providências - livres sem GIGS)
        logger.info("[LOOP_PRAZO] Fase 3: Executando ciclo 3")
        resultado_ciclo3 = ciclo3(driver)

        return ResultadoExecucao(
            sucesso=resultado_ciclo2 is True and resultado_ciclo3 is True,
            status='OK',
            detalhes={
                "ciclo1": "concluido",
                "ciclo2": resultado_ciclo2,
                "ciclo3": resultado_ciclo3
            }
        )
    except Exception as e:
        logger.error(f'[LOOP_PRAZO] Erro no wrapper: {e}')
        return ResultadoExecucao(sucesso=False, status='FALHA', erro=str(e))
