# debug_visual_config.py
"""
Configuração para debug visual integrado ao VS Code
Permite acompanhar execução do Selenium diretamente no editor
"""

import os
import json
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service

class DebugVisualDriver:
    """Driver com integração visual para VS Code"""
    
    def __init__(self, headless=False, debug_mode=True):
        self.debug_mode = debug_mode
        self.driver = None
        self.screenshots_dir = "d:/PjePlus/debug_screenshots"
        self.create_directories()
        
    def create_directories(self):
        """Cria diretórios necessários para debug"""
        os.makedirs(self.screenshots_dir, exist_ok=True)
        os.makedirs("d:/PjePlus/debug_html", exist_ok=True)
        
    def criar_driver_debug(self, headless=False):
        """Cria driver otimizado para debug visual"""
        options = Options()
        
        if not headless:
            # Configurações para janela visível e bem posicionada
            options.add_argument('--width=1200')
            options.add_argument('--height=800')
            # Posiciona janela no lado direito da tela
            options.add_argument('--window-position=800,0')
        else:
            options.add_argument('--headless')
            
        # Configurações de debug
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-gpu')
        options.set_preference('devtools.console.stdout.content', True)
        
        # Usa configuração do driver_config.py existente
        try:
            from driver_config import criar_driver_PC
            options.binary_location = r"C:\Program Files\Firefox Developer Edition\firefox.exe"
            options.set_preference('profile', r"C:\Users\Silas\AppData\Roaming\Mozilla\Dev\Selenium")
        except:
            pass
            
        service = Service(executable_path=r"d:\PjePlus\geckodriver.exe")
        
        self.driver = webdriver.Firefox(service=service, options=options)
        self.driver.implicitly_wait(10)
        
        print(f"[DEBUG_VISUAL] Driver criado - Janela: {'Visível' if not headless else 'Headless'}")
        return self.driver
    
    def capturar_estado_debug(self, nome_passo, incluir_html=True):
        """Captura estado atual para debug"""
        if not self.debug_mode or not self.driver:
            return
            
        timestamp = time.strftime("%H%M%S")
        
        try:
            # Screenshot
            screenshot_path = f"{self.screenshots_dir}/{timestamp}_{nome_passo}.png"
            self.driver.save_screenshot(screenshot_path)
            
            # HTML atual
            if incluir_html:
                html_path = f"d:/PjePlus/debug_html/{timestamp}_{nome_passo}.html"
                with open(html_path, 'w', encoding='utf-8') as f:
                    f.write(self.driver.page_source)
            
            # Info de debug
            debug_info = {
                "timestamp": timestamp,
                "passo": nome_passo,
                "url": self.driver.current_url,
                "title": self.driver.title,
                "screenshot": screenshot_path,
                "html": html_path if incluir_html else None,
                "window_size": self.driver.get_window_size(),
                "cookies": self.driver.get_cookies()
            }
            
            # Salva info em JSON
            info_path = f"d:/PjePlus/debug_html/{timestamp}_{nome_passo}_info.json"
            with open(info_path, 'w', encoding='utf-8') as f:
                json.dump(debug_info, f, indent=2, ensure_ascii=False)
            
            print(f"[DEBUG_VISUAL] Estado capturado: {nome_passo}")
            
        except Exception as e:
            print(f"[DEBUG_VISUAL][ERRO] Falha ao capturar estado: {e}")
    
    def highlight_element(self, element, cor="red", tempo=2):
        """Destaca elemento na tela para debug visual"""
        if not self.debug_mode:
            return
            
        try:
            # Salva estilo original
            original_style = element.get_attribute("style")
            
            # Aplica destaque
            highlight_style = f"border: 3px solid {cor}; background-color: yellow; opacity: 0.8;"
            self.driver.execute_script(f"arguments[0].setAttribute('style', '{highlight_style}');", element)
            
            # Aguarda
            time.sleep(tempo)
            
            # Restaura estilo
            if original_style:
                self.driver.execute_script(f"arguments[0].setAttribute('style', '{original_style}');", element)
            else:
                self.driver.execute_script("arguments[0].removeAttribute('style');", element)
                
        except Exception as e:
            print(f"[DEBUG_VISUAL][ERRO] Falha ao destacar elemento: {e}")
    
    def log_debug_vscode(self, mensagem, nivel="INFO"):
        """Log formatado para VS Code Terminal"""
        timestamp = time.strftime("%H:%M:%S")
        print(f"[{timestamp}][{nivel}][DEBUG_VISUAL] {mensagem}")
    
    def abrir_no_vscode_browser(self, url=None):
        """Abre página atual no browser integrado do VS Code"""
        if not url and self.driver:
            url = self.driver.current_url
            
        if url:
            print(f"[DEBUG_VISUAL] Abrir no VS Code Browser: {url}")
            # O usuário pode usar Ctrl+Shift+P -> "Simple Browser: Show"
            # E colar a URL
            
    def criar_relatorio_debug(self):
        """Cria relatório HTML com todas as capturas"""
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Relatório Debug Visual - PjePlus</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                .step { border: 1px solid #ccc; margin: 10px 0; padding: 10px; }
                .screenshot { max-width: 300px; margin: 10px 0; }
                .info { background: #f5f5f5; padding: 10px; margin: 5px 0; }
            </style>
        </head>
        <body>
            <h1>Relatório Debug Visual - PjePlus</h1>
        """
        
        # Lista arquivos de screenshot
        try:
            screenshots = [f for f in os.listdir(self.screenshots_dir) if f.endswith('.png')]
            screenshots.sort()
            
            for screenshot in screenshots:
                nome_passo = screenshot.replace('.png', '').split('_', 1)[1]
                html_content += f"""
                <div class="step">
                    <h3>{nome_passo}</h3>
                    <img class="screenshot" src="debug_screenshots/{screenshot}" alt="{nome_passo}">
                    <div class="info">Screenshot: {screenshot}</div>
                </div>
                """
                
        except Exception as e:
            print(f"[DEBUG_VISUAL][ERRO] Falha ao criar relatório: {e}")
        
        html_content += "</body></html>"
        
        # Salva relatório
        relatorio_path = "d:/PjePlus/relatorio_debug_visual.html"
        with open(relatorio_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
            
        print(f"[DEBUG_VISUAL] Relatório criado: {relatorio_path}")
        return relatorio_path

# Função helper para integração fácil
def criar_driver_visual_debug(headless=False):
    """Função simplificada para criar driver com debug visual"""
    debug_driver = DebugVisualDriver(debug_mode=True)
    return debug_driver.criar_driver_debug(headless=headless), debug_driver

# Exemplo de uso:
if __name__ == "__main__":
    print("Testando integração visual com VS Code...")
    
    # Cria driver com debug
    driver, debug_helper = criar_driver_visual_debug(headless=False)
    
    try:
        # Exemplo de navegação com debug
        debug_helper.capturar_estado_debug("inicio")
        
        driver.get("https://pje.trt2.jus.br")
        debug_helper.capturar_estado_debug("pagina_inicial")
        
        # Aguarda um pouco para visualização
        time.sleep(3)
        
        # Cria relatório
        debug_helper.criar_relatorio_debug()
        
    finally:
        driver.quit()
        print("Debug visual concluído!")
