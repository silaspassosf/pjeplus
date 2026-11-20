"""Prazo - Loop Orquestrador"""
import logging
import math
import re
import time
from contextlib import contextmanager
from typing import Dict, Any, List, Optional, Tuple, Union
from concurrent.futures import ThreadPoolExecutor, as_completed


from Fix import espera
from Fix.core import (
    aguardar_renderizacao_nativa,
    aplicar_filtro_100,
    com_retry,
    safe_click_no_scroll,
)
from Fix.variaveis import PjeApiClient, obter_gigs_com_fase, session_from_driver

from core.resultado_execucao import ResultadoExecucao
from Fix.core import _executar_js
logger = logging.getLogger(__name__)


GIGS_API_MAX_WORKERS = 20

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


def log_seletor_vencedor(acao: str, by: Any, seletor: str) -> None:
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


SCRIPT_SELECAO_GIGS_AJ_JT = r'''
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

SCRIPT_SELECAO_LIVRES = r'''
try {
    let linhas = document.querySelectorAll('tr.cdk-drag');
    let selecionados = 0;
    linhas.forEach(function(linha){
        let prazo = linha.querySelector('td[data-label*="prazo" i] time, td:nth-child(9) time');
        let prazoVazio = !prazo || !prazo.textContent.trim();
        let hasComment = linha.querySelector('i.fa-comment') !== null;
        let inputField = linha.querySelector('input[matinput]');
        let campoPreenchido = inputField && inputField.value.trim();
        let temLupa = linha.querySelector('td[data-label*="processo" i] i.fa-search, td:nth-child(3) i.fa-search') !== null;
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

SCRIPT_SELECAO_LIVRES_API = r'''
try {
    let processosComGigsApi = arguments[0] || [];
    let linhas = document.querySelectorAll('tr.cdk-drag');
    let selecionados = 0;
    let padrao = /(\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4})/;
    linhas.forEach(function(linha){
        let prazo = linha.querySelector('td[data-label*="prazo" i] time, td:nth-child(9) time');
        let prazoVazio = !prazo || !prazo.textContent.trim();
        let hasComment = linha.querySelector('i.fa-comment') !== null;
        let inputField = linha.querySelector('input[matinput]');
        let campoPreenchido = inputField && inputField.value.trim();
        let temLupa = linha.querySelector('td[data-label*="processo" i] i.fa-search, td:nth-child(3) i.fa-search') !== null;
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


def _extrair_numero_processo_da_linha(linha_elemento: Any) -> Optional[str]:
    """Extrai número de processo de um elemento <tr> da tabela de atividades."""
    try:
        padrao_processo = re.compile(r'(\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4})')

        try:
            links = espera.elementos(linha_elemento, 'a', teto=0.1)
            for link in links:
                texto = getattr(link, 'text', '').strip()
                match = padrao_processo.search(texto)
                if match:
                    return match.group(1)
        except Exception:
            pass

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


def selecionar_processos_nao_livres(driver: Any, max_processos: int = 20) -> Tuple[int, bool]:
    """Seleciona processos não livres (com prazo preenchido, comentário ou campo preenchido)."""
    try:
        resultado = _executar_js(driver, SCRIPT_SELECAO_NAO_LIVRES, max_processos)

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


def _selecionar_processos_por_gigs_aj_jt(driver: Any, client: 'PjeApiClient') -> int:
    """Seleciona processos com atividade GIGS AJ-JT apenas em fase LIQUIDAÇÃO."""
    try:
        if not pausar_confirmacao('CICLO2/GIGS_AJ_JT', 'Iniciar varredura e seleção de processos com AJ-JT'):
            return 0
        linhas = espera.elementos(driver, 'tr.cdk-drag', teto=1)
        processos_com_gigs = []

        for linha in linhas:
            try:
                numero_processo = _extrair_numero_processo_da_linha(linha)
                if not numero_processo:
                    continue

                dados_gigs_fase = obter_gigs_com_fase(client, numero_processo)
                if not dados_gigs_fase:
                    continue

                if dados_gigs_fase.get('fase') != 'Liquidação':
                    continue

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
            selecionados = _executar_js(
                driver,
                SCRIPT_SELECAO_GIGS_AJ_JT,
                processos_com_gigs
            )
            logger.info(f'[CICLO2][GIGS-AJ-JT] {selecionados} processo(s) com AJ-JT selecionado(s)')
            try:
                aguardar_renderizacao_nativa(driver, 'span.total-registros', timeout=1.5)
            except Exception:
                espera.ate_js(driver, "document.readyState === 'complete'", teto=1.5)
            return selecionados

        logger.info('[CICLO2][GIGS-AJ-JT] Nenhum processo com atividade AJ-JT encontrado')
        return 0

    except Exception as e:
        logger.error('[LOOP_PRAZO][ERRO] Erro em _selecionar_processos_por_gigs_aj_jt: %s: %s', type(e).__name__, e)
        return 0


def _verificar_processo_tem_xs(client: 'PjeApiClient', numero_processo: str) -> bool:
    """Verifica se o processo já tem atividade GIGS xs (sem prazo)."""
    try:
        atividades = client.atividades_gigs(numero_processo)

        if not atividades:
            return False

        for atividade in atividades:
            data_prazo = atividade.get('dataPrazo')
            if not data_prazo or (isinstance(data_prazo, str) and not data_prazo.strip()):
                logger.debug('[LOOP_PRAZO][XS] Processo %s ja tem atividade xs no GIGS', numero_processo)
                return True

        return False
    except Exception as e:
        logger.error('[LOOP_PRAZO][ERRO] Erro ao verificar xs para %s: %s: %s', numero_processo, type(e).__name__, e)
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


def ciclo0(driver: Any) -> bool:
    """Ciclo 0: Painel Global 14 (Análise)"""
    from .loop_lote import _ciclo1_aplicar_filtro_fases
    from .loop_execucao_final import _ciclo2_criar_atividade_xs

    url_painel14 = "https://pje.trt2.jus.br/pjekz/painel/global/14/lista-processos"
    if not pausar_confirmacao('CICLO0/NAVEGAR_PAINEL14', f'Navegar para {url_painel14}'):
        return False
    logger.info(f'[CICLO0] Navegando para Painel Global 14: {url_painel14}')
    driver.get(url_painel14)

    if not espera.ate_url(driver, "painel/global/14", teto=10):
        logger.warning(f'[CICLO0] URL ainda não contém painel/global/14. URL atual: {getattr(driver, "current_url", "")}. Forçando navegação direta...')
        driver.get(url_painel14)
        espera.ate_url(driver, "painel/global/14", teto=10)

    logger.info(f'[CICLO0] URL confirmada: {getattr(driver, "current_url", "")}')

    try:
        if espera.elemento(driver, 'mat-select[formcontrolname="fpglobal_faseProcessual"], mat-select[placeholder*="Fase processual"]', teto=12) is None:
            raise TimeoutError()
        logger.info('[CICLO0] Dropdown "Fase processual" presente - prosseguindo')
    except Exception:
        logger.warning('[CICLO0] Timeout aguardando dropdown "Fase processual" - prosseguindo mesmo assim')

    try:
        mensagem_vazia = espera.elementos(driver, "//span[contains(text(), 'Não há processos neste tema')]", teto=0.5)
        if mensagem_vazia and any(getattr(el, 'is_displayed', lambda: True)() for el in mensagem_vazia):
            logger.info('[CICLO0] Lista já vazia antes do filtro - nada a processar')
            return True
    except Exception:
        pass

    with medir_latencia('CICLO0_APLICAR_FILTRO_FASES'):
        filtro_result = _ciclo1_aplicar_filtro_fases(driver)
    if filtro_result == "no_more_processes":
        logger.info('[CICLO0] Nenhum processo em liquidação/execução.')
        return True
    if not filtro_result:
        logger.error('[CICLO0] Falha ao aplicar filtro de fases.')
        return False

    with medir_latencia('CICLO0_FILTRO_100'):
        logger.info('[CICLO0] Aplicando filtro 100...')
        try:
            ja_100 = espera.elemento(driver, "//span[contains(@class,'mat-select-min-line') and normalize-space(text())='100']", teto=0.5)
            if ja_100:
                logger.info('[CICLO0] Lista já configurada com 100 itens')
            else:
                aplicar_filtro_100(driver)
                logger.info('[CICLO0] Filtro 100 aplicado')
        except Exception as e:
            logger.warning(f'[CICLO0] Aviso ao aplicar filtro 100: {e}')

        try:
            aguardar_renderizacao_nativa(driver, 'span.total-registros', timeout=3)
        except Exception:
            espera.ate_js(driver, "document.readyState === 'complete'", teto=3)

    with medir_latencia('CICLO0_SELECAO_LIVRES_E_XS1'):
        logger.info('[CICLO0] Selecionando processos livres...')

        try:
            total_elem = espera.elemento(driver, 'span.total-registros', teto=2)
            total_text = getattr(total_elem, 'text', '') if total_elem else ''
            m = re.search(r'de\s+(\d+)', total_text)
            total = int(m.group(1)) if m else -1
        except Exception:
            total = -1

        paginas = math.ceil(total / 100) if total > 0 else 1
        total_selecionados = 0

        for pagina in range(paginas):
            try:
                selecionados = _executar_js(driver, SCRIPT_SELECAO_LIVRES)
                if selecionados == -1:
                    logger.error(f"[CICLO0] ERRO no script de seleção de livres na página {pagina+1}")
                    return False
                elif isinstance(selecionados, int) and selecionados > 0:
                    total_selecionados += selecionados
                    logger.info(f"[CICLO0] Página {pagina+1}: {selecionados} livres selecionados")
                    logger.info(f"[CICLO0] Aplicando atividade XS (xs1) para os processos livres selecionados...")
                    if not _ciclo2_criar_atividade_xs(driver):
                        logger.error(f"[CICLO0] Falha ao aplicar XS na página {pagina+1}")
                        return False
                    logger.info(f"[CICLO0] Atividade XS aplicada na página {pagina+1}")
                else:
                    logger.info(f"[CICLO0] Página {pagina+1}: 0 livres selecionados")
            except Exception as e:
                logger.error(f"[CICLO0] Erro ao selecionar livres na página {pagina+1}: {e}")

            if pagina < paginas - 1:
                try:
                    btn_next = espera.elemento(driver, 'mat-paginator button[aria-label="Próxima página"]', teto=2)
                    if btn_next:
                        safe_click_no_scroll(driver, btn_next)
                    try:
                        aguardar_renderizacao_nativa(driver, 'span.total-registros', timeout=1)
                    except Exception:
                        espera.ate_js(driver, "document.readyState === 'complete'", teto=1)
                except Exception:
                    logger.info("[CICLO0] Não foi possível navegar para próxima página (ou última página atingida)")

        logger.info(f"[CICLO0] Total de processos livres selecionados: {total_selecionados}")

        if total_selecionados == 0:
            logger.info("[CICLO0] Nenhum processo livre encontrado")

    logger.info("[CICLO0] Ciclo 0 concluído com sucesso")
    return True


def ciclo1(driver: Any, opcao_destino: str = 'Análise') -> Union[bool, str]:
    """Orquestra ciclo 1: filtro, marcação, suitcase, movimentação para painel 14."""
    # lazy import to avoid circular dependency with loop_lote
    from .loop_lote import (
        _ciclo1_aplicar_filtro_fases,
        _ciclo1_marcar_todas,
        _ciclo1_abrir_suitcase,
        _ciclo1_aguardar_movimentacao_lote,
        _ciclo1_movimentar_destino,
        _ciclo1_retornar_lista,
    )

    try:
        mensagem_vazia = espera.elementos(driver, "//span[contains(text(), 'Não há processos neste tema')]", teto=0.5)
        if mensagem_vazia and any(getattr(el, 'is_displayed', lambda: True)() for el in mensagem_vazia):
            logger.info('[CICLO1] Lista já vazia antes do filtro - nada a processar')
            return "no_more_processes"
    except Exception:
        pass

    with medir_latencia('CICLO1_APLICAR_FILTRO_FASES'):
        filtro_result = _ciclo1_aplicar_filtro_fases(driver)
    if filtro_result == "no_more_processes":
        logger.info('[CICLO1] Nenhum processo em liquidação/execução.')
        return "no_more_processes"
    if not filtro_result:
        return False

    qtd_processos = 0
    try:
        try:
            aguardar_renderizacao_nativa(driver, 'span.total-registros', timeout=1)
        except Exception:
            espera.ate_js(driver, "document.readyState === 'complete'", teto=1)
        processos = espera.elementos(driver, 'tbody tr.tr-class', teto=1)
        qtd_processos = len(processos)
        logger.info(f'[CICLO1] Detectados {qtd_processos} processo(s) na lista')

        if qtd_processos == 1:
            logger.info('[CICLO1] Apenas 1 processo detectado - PJE não disponibiliza batch (suitcase)')
            logger.info('[CICLO1] Prosseguindo para processamento individual (Fase 2)')
            return "single_process"
        elif qtd_processos == 0:
            logger.info('[CICLO1] Nenhum processo encontrado após filtro.')
            return "no_more_processes"

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

    try:
        logger.info('[CICLO1] Pausa breve (2s) para verificação visual da seleção antes do lote')
        aguardar_renderizacao_nativa(driver, timeout=2)
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

    if qtd_processos < 20:
        logger.info(f'[CICLO1] Ciclo 1 concluído - lote único ({qtd_processos} processos), não repetir')
        return "complete_single_batch"
    else:
        logger.info('[CICLO1] Ciclo 1 concluído - pode haver mais processos, verificar novamente')
        return True


def loop_prazo(driver: Any) -> Dict[str, Any]:
    """Função wrapper que executa o fluxo de prazo (Ciclo 0 + Cumprimento de Providências)"""
    try:
        # lazy import to avoid circular dependency with loop_execucao_final
        from .loop_execucao_final import ciclo3

        logger.info("[LOOP_PRAZO] Loop 0: Executando ciclo 0 no painel 14")
        resultado_ciclo0 = ciclo0(driver)
        if not resultado_ciclo0:
            logger.error("[LOOP_PRAZO] Erro crítico no ciclo 0.")
            return ResultadoExecucao(sucesso=False, status='FALHA', erro="Falha em ciclo 0")

        logger.info("[LOOP_PRAZO] Fase Cumprimento de Providências: Executando ciclo 3 (painel 6)")
        resultado_ciclo3 = ciclo3(driver)

        sucesso_geral = resultado_ciclo0 is True and resultado_ciclo3 is True
        return ResultadoExecucao(
            sucesso=sucesso_geral,
            status='OK' if sucesso_geral else 'FALHA',
            detalhes={
                "ciclo0": resultado_ciclo0,
                "ciclo3": resultado_ciclo3,
            }
        )
    except Exception as e:
        logger.error(f'[LOOP_PRAZO] Erro no wrapper: {e}')
        return ResultadoExecucao(sucesso=False, status='FALHA', erro=str(e))
