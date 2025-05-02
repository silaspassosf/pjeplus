# sisbajud.py
# Automação SISBAJUD integrada ao PJe (abertas em /detalhe)
# Injeta botões na tela de detalhes do processo no PJe para acionar automações no SISBAJUD
# Autor: Cascade AI

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time

# ===================== CONFIGURAÇÕES =====================
CONFIG = {
    'cor_bloqueio_positivo': '#32cd32',
    'cor_bloqueio_negativo': '#ff6347',
    'acao_automatica': 'transferir',  # opções: 'transferir', 'desbloquear', 'nenhuma'
    'banco_preferido': 'Banco do Brasil',
    'agencia_preferida': '',
    'teimosinha': '30',  # dias
    # ... outros parâmetros
}

# ===================== INJETAR BOTÕES NO PJe =====================
def injetar_botoes_pje(driver):
    """
    Injeta botões na tela de detalhes do processo (/detalhe) do PJe.
    Cada botão, ao ser clicado, pode abrir o SISBAJUD e executar automações.
    """
    driver.execute_script("""
        if (!document.getElementById('btn_minuta_bloqueio')) {
            let container = document.createElement('div');
            container.id = 'sisbajud_btn_container';
            container.style = 'position:fixed;top:60px;right:20px;z-index:9999;background:#fff;padding:8px;border-radius:8px;box-shadow:0 2px 8px #0002;';
            // Botão Minuta Bloqueio
            let btn1 = document.createElement('button');
            btn1.id = 'btn_minuta_bloqueio';
            btn1.innerText = 'Minuta de Bloqueio';
            btn1.style = 'margin:4px;padding:6px 14px;cursor:pointer;';
            btn1.onclick = function() { window.dispatchEvent(new CustomEvent('minuta_bloqueio')); };
            container.appendChild(btn1);
            // Botão Minuta Endereço
            let btn2 = document.createElement('button');
            btn2.id = 'btn_minuta_endereco';
            btn2.innerText = 'Minuta de Endereço';
            btn2.style = 'margin:4px;padding:6px 14px;cursor:pointer;';
            btn2.onclick = function() { window.dispatchEvent(new CustomEvent('minuta_endereco')); };
            container.appendChild(btn2);
            // Botão Processar Bloqueios
            let btn3 = document.createElement('button');
            btn3.id = 'btn_processar_bloqueios';
            btn3.innerText = 'Processar Bloqueios';
            btn3.style = 'margin:4px;padding:6px 14px;cursor:pointer;';
            btn3.onclick = function() { window.dispatchEvent(new CustomEvent('processar_bloqueios')); };
            container.appendChild(btn3);
            document.body.appendChild(container);
        }
    """)

# ===================== PROMPT DE DADOS VIA JS =====================
def prompt_js(driver, mensagem, valor_padrao=''):
    """
    Exibe um prompt JS na página e retorna o valor digitado.
    """
    return driver.execute_script(f"return prompt('{mensagem.replace("'", "\'")}', '{valor_padrao}');")

# ===================== ACIONADORES DE EVENTOS =====================
def bind_eventos(driver):
    """
    Injeta JS para escutar eventos customizados e acionar funções Python.
    Deve ser chamado após injetar os botões.
    """
    # No Selenium puro não é possível escutar eventos JS diretamente.
    # Usamos polling para checar flags JS e disparar as funções Python.
    driver.execute_script("window.sisbajud_event_flag = '';")
    driver.execute_script("""
        window.addEventListener('minuta_bloqueio', function() { window.sisbajud_event_flag = 'minuta_bloqueio'; });
        window.addEventListener('minuta_endereco', function() { window.sisbajud_event_flag = 'minuta_endereco'; });
        window.addEventListener('processar_bloqueios', function() { window.sisbajud_event_flag = 'processar_bloqueios'; });
    """)

def checar_evento(driver):
    """
    Checa se algum evento foi disparado via botão JS.
    """
    flag = driver.execute_script("return window.sisbajud_event_flag;")
    if flag:
        driver.execute_script("window.sisbajud_event_flag = '';")
    return flag

# ===================== FLUXOS DE AUTOMAÇÃO SISBAJUD =====================
def abrir_sisbajud_em_nova_aba(driver):
    """
    Abre o SISBAJUD em nova aba e retorna o handle.
    """
    driver.execute_script("window.open('https://sisbajud.cnj.jus.br/', '_blank');")
    driver.switch_to.window(driver.window_handles[-1])
    time.sleep(2)
    return driver.current_window_handle

def minuta_bloqueio(driver):
    """
    Fluxo de geração de minuta de bloqueio no SISBAJUD.
    Pode pedir dados ao usuário via prompt_js.
    """
    handle = abrir_sisbajud_em_nova_aba(driver)
    # Exemplo: pedir valor do bloqueio
    valor = prompt_js(driver, 'Informe o valor do bloqueio:', '1000,00')
    # Aqui implementar o preenchimento dos campos e execução da minuta
    # ...
    print(f'[SISBAJUD] Minuta de bloqueio iniciada com valor: {valor}')
    # Feche a aba do SISBAJUD se desejar
    # driver.close()
    # driver.switch_to.window(driver.window_handles[0])

def minuta_endereco(driver):
    """
    Fluxo de geração de minuta de endereço no SISBAJUD.
    """
    handle = abrir_sisbajud_em_nova_aba(driver)
    endereco = prompt_js(driver, 'Informe o endereço para pesquisa:', '')
    # Implementar automação do preenchimento
    print(f'[SISBAJUD] Minuta de endereço iniciada para: {endereco}')
    # driver.close()
    # driver.switch_to.window(driver.window_handles[0])

def processar_bloqueios(driver):
    """
    Processa a tabela de bloqueios no SISBAJUD, muda cor das linhas e preenche campos automaticamente.
    """
    handle = abrir_sisbajud_em_nova_aba(driver)
    # Exemplo: mudar cor das linhas com bloqueio positivo
    driver.execute_script(f"""
        let linhas = document.querySelectorAll('tr');
        linhas.forEach(function(linha) {
            if (linha.innerText.toLowerCase().includes('bloqueio positivo')) {{
                linha.style.backgroundColor = '{CONFIG['cor_bloqueio_positivo']}';
            }}
            if (linha.innerText.toLowerCase().includes('bloqueio negativo')) {{
                linha.style.backgroundColor = '{CONFIG['cor_bloqueio_negativo']}';
            }}
        });
    """)
    # Preencher campos de transferência/desbloqueio conforme config
    # ...
    print('[SISBAJUD] Processamento de bloqueios executado.')
    # driver.close()
    # driver.switch_to.window(driver.window_handles[0])

# ===================== LOOP PRINCIPAL =====================
def main():
    driver = webdriver.Firefox()
    driver.get('https://pje.trt2.jus.br/primeirograu/Processo/DetalheProcesso')
    time.sleep(3)
    injetar_botoes_pje(driver)
    bind_eventos(driver)
    print('[SISBAJUD] Botões injetados na tela de detalhes do processo.')
    while True:
        evento = checar_evento(driver)
        if evento == 'minuta_bloqueio':
            minuta_bloqueio(driver)
        elif evento == 'minuta_endereco':
            minuta_endereco(driver)
        elif evento == 'processar_bloqueios':
            processar_bloqueios(driver)
        time.sleep(1)

if __name__ == '__main__':
    main()
