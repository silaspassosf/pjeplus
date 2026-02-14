import logging
logger = logging.getLogger(__name__)

# loop_prazo.py
# Função para automação em lote do painel global do PJe TRT2
# Segue estritamente o roteiro solicitado pelo usuário
# Importação das configurações do driver
import time
import re

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