#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SISB_MODULOS/INTERFACE_PJE.PY
Interface e injeções JavaScript no PJe
Extraído do bacen.py original
"""

def injetar_botao_sisbajud_pje(driver):
    """
    Injeta apenas um botão no PJe para abrir o SISBAJUD
    
    Args:
        driver: WebDriver Selenium do PJe
    """
    try:
        script_botao = """
        if (!document.getElementById('btn_abrir_sisbajud')) {
            let container = document.createElement('div');
            container.id = 'sisbajud_btn_container';
            container.style = 'position:fixed;top:60px;right:20px;z-index:9999;background:#1976d2;padding:12px;border-radius:12px;box-shadow:0 4px 12px rgba(25,118,210,0.3);';
            
            let btn = document.createElement('button');
            btn.id = 'btn_abrir_sisbajud';
            btn.innerHTML = '🏦 Abrir SISBAJUD';
            btn.style = 'padding:10px 20px;font-size:14px;font-weight:bold;cursor:pointer;background:#fff;color:#1976d2;border:none;border-radius:8px;box-shadow:0 2px 4px rgba(0,0,0,0.1);transition:all 0.3s ease;';
            btn.onmouseenter = function() { this.style.transform = 'scale(1.05)'; this.style.boxShadow = '0 4px 8px rgba(0,0,0,0.2)'; };
            btn.onmouseleave = function() { this.style.transform = 'scale(1)'; this.style.boxShadow = '0 2px 4px rgba(0,0,0,0.1)'; };
            btn.onclick = function() { window.dispatchEvent(new CustomEvent('abrir_sisbajud')); };
            
            container.appendChild(btn);
            document.body.appendChild(container);
        }
        """
        
        driver.execute_script(script_botao)
        print('[INTERFACE_PJE] ✅ Botão SISBAJUD injetado no PJe')
        
    except Exception as e:
        print(f'[INTERFACE_PJE] ❌ Erro ao injetar botão: {e}')

def prompt_js(driver, mensagem, valor_padrao=''):
    """
    Exibe um prompt JavaScript no navegador
    
    Args:
        driver: WebDriver Selenium
        mensagem: Mensagem do prompt
        valor_padrao: Valor padrão
        
    Returns:
        str: Valor inserido pelo usuário
    """
    try:
        # Escapar aspas na mensagem
        mensagem_escapada = mensagem.replace("'", "\\'")
        valor_padrao_escapado = str(valor_padrao).replace("'", "\\'")
        
        resultado = driver.execute_script(
            f"return prompt('{mensagem_escapada}', '{valor_padrao_escapado}');"
        )
        
        return resultado
        
    except Exception as e:
        print(f'[INTERFACE_PJE] ❌ Erro no prompt JS: {e}')
        return None

def bind_eventos(driver):
    """
    Configura apenas o evento de abrir SISBAJUD
    
    Args:
        driver: WebDriver Selenium do PJe
    """
    try:
        # Inicializar flag de evento
        driver.execute_script("window.sisbajud_event_flag = '';")
        
        # Configurar listener para evento de abrir SISBAJUD
        script_eventos = """
        window.addEventListener('abrir_sisbajud', function() { 
            window.sisbajud_event_flag = 'abrir_sisbajud'; 
        });
        """
        
        driver.execute_script(script_eventos)
        print('[INTERFACE_PJE] ✅ Eventos configurados no PJe')
        
    except Exception as e:
        print(f'[INTERFACE_PJE] ❌ Erro ao configurar eventos: {e}')

def checar_evento(driver):
    """
    Verifica se algum evento foi disparado
    
    Args:
        driver: WebDriver Selenium do PJe
        
    Returns:
        str: Nome do evento ou string vazia
    """
    try:
        flag = driver.execute_script("return window.sisbajud_event_flag;")
        
        if flag:
            # Limpar flag após leitura
            driver.execute_script("window.sisbajud_event_flag = '';")
            
        return flag or ''
        
    except Exception as e:
        print(f'[INTERFACE_PJE] ❌ Erro ao checar evento: {e}')
        return ''

def verificar_botao_existe(driver):
    """
    Verifica se o botão SISBAJUD já existe na página
    
    Args:
        driver: WebDriver Selenium do PJe
        
    Returns:
        bool: True se o botão existe
    """
    try:
        existe = driver.execute_script("""
            return document.getElementById('btn_abrir_sisbajud') !== null;
        """)
        
        return bool(existe)
        
    except Exception as e:
        print(f'[INTERFACE_PJE] ❌ Erro ao verificar botão: {e}')
        return False

def remover_botao_sisbajud(driver):
    """
    Remove o botão SISBAJUD da página
    
    Args:
        driver: WebDriver Selenium do PJe
    """
    try:
        script_remover = """
        let container = document.getElementById('sisbajud_btn_container');
        if (container) {
            container.remove();
            return true;
        }
        return false;
        """
        
        removido = driver.execute_script(script_remover)
        
        if removido:
            print('[INTERFACE_PJE] ✅ Botão SISBAJUD removido')
        else:
            print('[INTERFACE_PJE] ⚠️ Botão SISBAJUD não encontrado para remoção')
            
    except Exception as e:
        print(f'[INTERFACE_PJE] ❌ Erro ao remover botão: {e}')

def injetar_css_personalizado(driver, css_code):
    """
    Injeta CSS personalizado na página
    
    Args:
        driver: WebDriver Selenium
        css_code: Código CSS para injetar
    """
    try:
        script_css = f"""
        let style = document.createElement('style');
        style.textContent = `{css_code}`;
        document.head.appendChild(style);
        """
        
        driver.execute_script(script_css)
        print('[INTERFACE_PJE] ✅ CSS personalizado injetado')
        
    except Exception as e:
        print(f'[INTERFACE_PJE] ❌ Erro ao injetar CSS: {e}')

def obter_informacoes_pagina(driver):
    """
    Obtém informações básicas da página atual
    
    Args:
        driver: WebDriver Selenium
        
    Returns:
        dict: Informações da página
    """
    try:
        info = driver.execute_script("""
            return {
                url: window.location.href,
                titulo: document.title,
                dominio: window.location.hostname,
                ready_state: document.readyState,
                timestamp: new Date().toISOString()
            };
        """)
        
        return info
        
    except Exception as e:
        print(f'[INTERFACE_PJE] ❌ Erro ao obter informações: {e}')
        return {}

def aguardar_elemento_js(driver, seletor, timeout=10):
    """
    Aguarda um elemento aparecer usando JavaScript
    
    Args:
        driver: WebDriver Selenium
        seletor: Seletor CSS do elemento
        timeout: Timeout em segundos
        
    Returns:
        bool: True se elemento foi encontrado
    """
    try:
        script_aguardar = f"""
        let elemento = null;
        let tentativas = 0;
        let maxTentativas = {timeout * 10}; // 10 tentativas por segundo
        
        function verificarElemento() {{
            elemento = document.querySelector('{seletor}');
            if (elemento) {{
                return true;
            }}
            
            tentativas++;
            if (tentativas < maxTentativas) {{
                setTimeout(verificarElemento, 100);
                return false;
            }}
            
            return false;
        }}
        
        return verificarElemento();
        """
        
        encontrado = driver.execute_script(script_aguardar)
        return bool(encontrado)
        
    except Exception as e:
        print(f'[INTERFACE_PJE] ❌ Erro ao aguardar elemento: {e}')
        return False

def scroll_para_elemento(driver, seletor):
    """
    Faz scroll para um elemento específico
    
    Args:
        driver: WebDriver Selenium
        seletor: Seletor CSS do elemento
        
    Returns:
        bool: True se conseguiu fazer scroll
    """
    try:
        script_scroll = f"""
        let elemento = document.querySelector('{seletor}');
        if (elemento) {{
            elemento.scrollIntoView({{
                behavior: 'smooth',
                block: 'center',
                inline: 'nearest'
            }});
            return true;
        }}
        return false;
        """
        
        sucesso = driver.execute_script(script_scroll)
        return bool(sucesso)
        
    except Exception as e:
        print(f'[INTERFACE_PJE] ❌ Erro ao fazer scroll: {e}')
        return False

def destacar_elemento(driver, seletor, cor='#ff0000'):
    """
    Destaca um elemento na página
    
    Args:
        driver: WebDriver Selenium
        seletor: Seletor CSS do elemento
        cor: Cor do destaque
        
    Returns:
        bool: True se conseguiu destacar
    """
    try:
        script_destacar = f"""
        let elemento = document.querySelector('{seletor}');
        if (elemento) {{
            elemento.style.border = '3px solid {cor}';
            elemento.style.backgroundColor = '{cor}33';
            return true;
        }}
        return false;
        """
        
        sucesso = driver.execute_script(script_destacar)
        return bool(sucesso)
        
    except Exception as e:
        print(f'[INTERFACE_PJE] ❌ Erro ao destacar elemento: {e}')
        return False
