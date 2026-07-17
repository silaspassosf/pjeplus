import logging
logger = logging.getLogger(__name__)

# loop_prazo.py
# Função para automação em lote do painel global do PJe TRT2
# Segue estritamente o roteiro solicitado pelo usuário
# Importação das configurações do driver
import time
import re
from contextlib import contextmanager

from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from Fix.core import (
    aplicar_filtro_100,
    aguardar_e_clicar,
    selecionar_opcao,
    filtrofases,
)
from Fix.utils import (
    configurar_recovery_driver,
    handle_exception_with_recovery,
)
from Fix.core import criar_driver_PC
from Fix.utils import login_cpf

# Type hints e imports adicionais
from typing import Optional, Dict, List, Union, Tuple, TYPE_CHECKING
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from concurrent.futures import ThreadPoolExecutor, as_completed

# Import de Fix.variaveis no topo (revertido para evitar problemas de timing)
# Mas mantendo lazy loading onde já está implementado
from Fix.variaveis import session_from_driver, PjeApiClient, obter_gigs_com_fase

# Import das funções refatoradas do módulo Prazo
from Prazo.p2b_prazo import fluxo_prazo

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


def clicar_com_multiplos_seletores(
    driver: WebDriver,
    acao: str,
    seletores: List[Tuple[By, str]],
    timeout: int = 10,
    usar_js: bool = True
) -> bool:
    """Tenta múltiplos seletores e loga qual funcionou."""
    ultimo_erro = None
    for by, seletor in seletores:
        try:
            elemento = WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable((by, seletor))
            )
            # scrollIntoView removido: não é mais necessário para filtro 100
            if usar_js:
                driver.execute_script("arguments[0].click();", elemento)
            else:
                elemento.click()
            log_seletor_vencedor(acao, by, seletor)
            return True
        except Exception as e:
            ultimo_erro = e
            logger.info(f"[SELETOR][{acao}] Falhou by={by} seletor={seletor}: {str(e)[:120]}")

    logger.error(f"[SELETOR][{acao}] Nenhum seletor funcionou. Último erro: {ultimo_erro}")
    return False


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

# NOTA: Imports de Fix.variaveis movidos para funções individuais (lazy loading)
# para evitar lentidão no carregamento inicial do módulo

# Constantes JavaScript para seleção de processos
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

# Variante que também exclui processos com gigs detectados via API (sem prazo)
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