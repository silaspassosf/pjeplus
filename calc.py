import re
import requests
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
import time
from Fix import obter_driver_padronizado
import logging

# Configuração básica de logging se não houver
if not logging.getLogger().hasHandlers():
    logging.basicConfig(
        filename='pje_automation.log',
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

def obter_id_processo_da_url(driver):
    """
    Extrai o id do processo da URL da aba de detalhes.
    Exemplo de URL: https://pje.trt2.jus.br/pjekz/processo/2485752/detalhe
    """
    match = re.search(r'/processo/(\d+)/detalhe', driver.current_url)
    if match:
        return int(match.group(1))
    return None

def obter_valor_calculo_api(driver, id_processo):
    """
    Faz requisição autenticada à API de cálculos do PJe e retorna o valor e data do cálculo mais recente.
    """
    url = (
        f"https://pje.trt2.jus.br/pje-comum-api/api/calculos/processo"
        f"?pagina=1&tamanhoPagina=10&ordenacaoCrescente=true&idProcesso={id_processo}"
        f"&mostrarCalculosHomologados=true&incluirCalculosHomologados=true"
    )
    session = requests.Session()
    for cookie in driver.get_cookies():
        session.cookies.set(cookie['name'], cookie['value'])
    resp = session.get(url)
    resp.raise_for_status()
    data = resp.json()
    if not data.get('resultado'):
        return None
    calculos = data['resultado']
    calculo_mais_recente = max(calculos, key=lambda c: c['dataLiquidacao'])
    return {
        'total': calculo_mais_recente['total'],
        'dataLiquidacao': calculo_mais_recente['dataLiquidacao']
    }

def mostrar_inscricao_calculo_pje(driver, mensagem):
    """
    Insere um bloco fixo, grande, vermelho, no topo da tela de detalhes, igual à inscrição da extensão MaisPje.
    """
    script = f'''
    (function() {{
        let antigo = document.getElementById('pjeplus-calc-info');
        if (antigo) antigo.remove();
        let div = document.createElement('div');
        div.id = 'pjeplus-calc-info';
        div.style = `
            position: fixed;
            top: 70px;
            left: 50%;
            transform: translateX(-50%);
            min-width: 420px;
            max-width: 90vw;
            background: #b71c1c;
            color: #fff;
            font-size: 1.5em;
            font-weight: bold;
            padding: 22px 32px;
            border-radius: 10px;
            box-shadow: 0 4px 24px rgba(0,0,0,0.25);
            z-index: 999999;
            text-align: center;
        `;
        div.innerHTML = `<span style='font-size:1.2em;'>CÁLCULO PJeCalc</span><br>${mensagem}`;
        document.body.appendChild(div);
    }})();
    '''
    driver.execute_script(script)

def mostrar_calculo_ao_lado_novo_executado(driver, valor, data):
    valor_str = f"R$ {valor:,.2f}".replace(",", "v").replace(".", ",").replace("v", ".")
    data_fmt = data.split("T")[0] if "T" in data else data
    partes = data_fmt.split("-")
    if len(partes) == 3:
        data_br = f"{partes[2]}/{partes[1]}/{partes[0]}"
    else:
        data_br = data_fmt
    script = (
        "(function() {"
        "    let alvo = Array.from(document.querySelectorAll('button, span, a, div, mat-card, mat-card-title, mat-card-content, *'))"
        "        .find(e => e.textContent && e.textContent.trim().toLowerCase().includes('novo executado'));"
        "    let html = 'Cálculo: {valor_str}<br>Data: {data_br}';"
        "    let id = 'pjeplus-calc-inline';"
        "    let antigo = document.getElementById(id);"
        "    if (antigo) antigo.remove();"
        "    if (alvo) {"
        "        let span = document.createElement('span');"
        "        span.id = id;"
        "        span.style = 'color: #b71c1c; font-weight: bold; font-size: 1.1em; margin-left: 18px; vertical-align: middle; display: inline-block;';"
        "        span.innerHTML = html;"
        "        alvo.parentNode.insertBefore(span, alvo.nextSibling);"
        "    } else {"
        "        let div = document.createElement('div');"
        "        div.id = id;"
        "        div.style = 'position: fixed; top: 80px; left: 50%; transform: translateX(-50%); background: #fff0f0; color: #b71c1c; font-weight: bold; font-size: 1.2em; padding: 8px 24px; border-radius: 8px; z-index: 99999; box-shadow: 0 2px 8px #0002;';"
        "        div.innerHTML = html;"
        "        document.body.appendChild(div);"
        "    }"
        "})();"
    ).format(valor_str=valor_str, data_br=data_br)
    driver.execute_script(script)

def mostrar_sem_calculo_ao_lado_novo_executado(driver):
    script = '''
    (function() {
        let alvo = Array.from(document.querySelectorAll('button, span, a, div, mat-card, mat-card-title, mat-card-content, *'))
            .find(e => e.textContent && e.textContent.trim().toLowerCase().includes('novo executado'));
        let id = 'pjeplus-calc-inline';
        let antigo = document.getElementById(id);
        if (antigo) antigo.remove();
        if (alvo) {
            let span = document.createElement('span');
            span.id = id;
            span.style = `color: #b71c1c; font-weight: bold; font-size: 1.1em; margin-left: 18px; vertical-align: middle; display: inline-block;`;
            span.innerHTML = 'Sem Cálculos';
            alvo.parentNode.insertBefore(span, alvo.nextSibling);
        } else {
            // Fallback: exibe no topo da tela de detalhes
            let div = document.createElement('div');
            div.id = id;
            div.style = `position: fixed; top: 80px; left: 50%; transform: translateX(-50%); background: #fff0f0; color: #b71c1c; font-weight: bold; font-size: 1.2em; padding: 8px 24px; border-radius: 8px; z-index: 99999; box-shadow: 0 2px 8px #0002;`;
            div.innerHTML = 'Sem Cálculos';
            document.body.appendChild(div);
        }
    })();
    '''
    driver.execute_script(script)

def exibir_valor_calculo_na_tela(driver):
    """
    Busca o valor do cálculo via API e exibe como inscrição fixa na tela de detalhes.
    Também faz log do valor extraído para depuração.
    """
    import logging
    logger = logging.getLogger(__name__)
    id_processo = obter_id_processo_da_url(driver)
    if not id_processo:
        logger.error('[CALC] ID do processo não encontrado na URL.')
        mostrar_inscricao_calculo_pje(driver, 'ID do processo não encontrado na URL.')
        return
    try:
        resultado = obter_valor_calculo_api(driver, id_processo)
        if resultado:
            valor = resultado['total']
            data = resultado['dataLiquidacao']
            logger.info(f'[CALC] Valor extraído via API: R$ {valor} | Data: {data}')
            mostrar_calculo_ao_lado_novo_executado(driver, valor, data)
        else:
            logger.warning('[CALC] Nenhum cálculo encontrado via API.')
            mostrar_sem_calculo_ao_lado_novo_executado(driver)
    except Exception as e:
        logger.error(f'[CALC] Erro ao buscar cálculo via API: {e}')
        mostrar_inscricao_calculo_pje(driver, f'Erro ao buscar cálculo: {e}')

# Exemplo de uso:
# exibir_valor_calculo_na_tela(driver)
