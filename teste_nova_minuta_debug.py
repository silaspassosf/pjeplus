
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste específico para depurar o problema do botão "Nova" no SISBAJUD
"""

import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def criar_driver():
    """Cria e configura o driver do Chrome"""
    chrome_options = Options()
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    driver = webdriver.Chrome(options=chrome_options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    return driver

def debug_pagina_minuta(driver):
    """Debug detalhado da página de minuta"""
    print("\n" + "="*60)
    print("DEBUG PÁGINA DE MINUTA")
    print("="*60)
    
    # 1. Informações básicas da página
    print(f"URL atual: {driver.current_url}")
    print(f"Título da página: {driver.title}")
    
    # 2. Buscar todos os botões na página
    botoes = driver.execute_script("""
        let botoes = Array.from(document.querySelectorAll('button'));
        return botoes.map(btn => ({
            tag: btn.tagName,
            id: btn.id || 'sem-id',
            class: btn.className || 'sem-class',
            text: btn.textContent.trim(),
            disabled: btn.disabled,
            aria_label: btn.getAttribute('aria-label') || 'sem-aria-label',
            mat_fab: btn.hasAttribute('mat-fab'),
            innerHTML: btn.innerHTML.substring(0, 100) + (btn.innerHTML.length > 100 ? '...' : '')
        }));
    """)
    
    print(f"\nTotal de botões encontrados: {len(botoes)}")
    print("\nBotões com texto 'Nova' ou similar:")
    
    for i, botao in enumerate(botoes):
        if 'nova' in botao['text'].lower() or 'add' in botao['text'].lower() or 'criar' in botao['text'].lower():
            print(f"\n  Botão {i+1}:")
            print(f"    Texto: '{botao['text']}'")
            print(f"    ID: {botao['id']}")
            print(f"    Classe: {botao['class']}")
            print(f"    Desabilitado: {botao['disabled']}")
            print(f"    Mat-fab: {botao['mat_fab']}")
            print(f"    Aria-label: {botao['aria_label']}")
            print(f"    HTML: {botao['innerHTML']}")
    
    # 3. Testar função querySelectorByText do JavaScript original
    print("\n" + "-"*50)
    print("TESTE DA FUNÇÃO querySelectorByText")
    print("-"*50)
    
    resultado_busca = driver.execute_script("""
        // Função removeAcento (reprodução fiel do mini-selenium.js)
        function removeAcento(text) {
            let stringComAcentos = "ÄÅÁÂÀÃäáâàãÉÊËÈéêëèÍÎÏÌíîïìÖÓÔÒÕöóôòõÜÚÛüúûùÇç";
            let stringSemAcentos = "AAAAAAaaaaaEEEEeeeeIIIIiiiiOOOOOoooooUUUuuuuCc";
            
            for (let i = 0; i < stringComAcentos.length; i++) {
                while(true) {
                    if (text.search(stringComAcentos[i].toString()) > -1) {
                        text = text.replace(stringComAcentos[i].toString(), stringSemAcentos[i].toString());
                    } else {
                        break;
                    }
                }
            }
            return text;
        }
        
        // Função querySelectorByText (reprodução fiel do mini-selenium.js)
        function querySelectorByText(tagname, texto) {
            return Array.from(document.querySelectorAll(tagname)).find(el => 
                removeAcento(el.textContent.trim().toLowerCase()).includes(removeAcento(texto.toLowerCase()))
            );
        }
        
        // Buscar botão Nova
        let botaoNova = querySelectorByText('button', 'Nova');
        
        if (botaoNova) {
            return {
                encontrado: true,
                texto: botaoNova.textContent.trim(),
                id: botaoNova.id || 'sem-id',
                class: botaoNova.className || 'sem-class',
                disabled: botaoNova.disabled,
                hasAttribute_disabled: botaoNova.hasAttribute('disabled'),
                aria_label: botaoNova.getAttribute('aria-label') || 'sem-aria-label',
                mat_fab: botaoNova.hasAttribute('mat-fab'),
                innerHTML: botaoNova.innerHTML
            };
        } else {
            return { encontrado: false };
        }
    """)
    
    if resultado_busca['encontrado']:
        print("✅ Botão Nova encontrado pela função querySelectorByText!")
        print(f"  Texto: '{resultado_busca['texto']}'")
        print(f"  ID: {resultado_busca['id']}")
        print(f"  Classe: {resultado_busca['class']}")
        print(f"  Desabilitado: {resultado_busca['disabled']}")
        print(f"  Has disabled attribute: {resultado_busca['hasAttribute_disabled']}")
        print(f"  Mat-fab: {resultado_busca['mat_fab']}")
        print(f"  Aria-label: {resultado_busca['aria_label']}")
        print(f"  HTML: {resultado_busca['innerHTML']}")
    else:
        print("❌ Botão Nova NÃO encontrado pela função querySelectorByText")
    
    # 4. Verificar estrutura da página
    print("\n" + "-"*50)
    print("ESTRUTURA DA PÁGINA")
    print("-"*50)
    
    estrutura = driver.execute_script("""
        return {
            has_sisbajud_components: !!document.querySelector('[class*="sisbajud"]'),
            has_mat_components: !!document.querySelector('[class*="mat-"]'),
            has_fab_buttons: document.querySelectorAll('button[mat-fab], .mat-fab').length,
            has_minuta_text: document.body.textContent.includes('minuta'),
            url_contains_minuta: window.location.href.includes('minuta'),
            page_ready_state: document.readyState
        };
    """)
    
    print(f"Componentes SISBAJUD: {estrutura['has_sisbajud_components']}")
    print(f"Componentes Angular Material: {estrutura['has_mat_components']}")
    print(f"Botões FAB: {estrutura['has_fab_buttons']}")
    print(f"Texto 'minuta' na página: {estrutura['has_minuta_text']}")
    print(f"URL contém 'minuta': {estrutura['url_contains_minuta']}")
    print(f"Estado da página: {estrutura['page_ready_state']}")

def testar_click_nova(driver):
    """Testa o clique no botão Nova"""
    print("\n" + "="*60)
    print("TESTE DO CLIQUE NO BOTÃO NOVA")
    print("="*60)
    
    url_antes = driver.current_url
    print(f"URL antes do clique: {url_antes}")
    
    # Executar o clique
    resultado = driver.execute_script("""
        // Função removeAcento (reprodução fiel do mini-selenium.js)
        function removeAcento(text) {
            let stringComAcentos = "ÄÅÁÂÀÃäáâàãÉÊËÈéêëèÍÎÏÌíîïìÖÓÔÒÕöóôòõÜÚÛüúûùÇç";
            let stringSemAcentos = "AAAAAAaaaaaEEEEeeeeIIIIiiiiOOOOOoooooUUUuuuuCc";
            
            for (let i = 0; i < stringComAcentos.length; i++) {
                while(true) {
                    if (text.search(stringComAcentos[i].toString()) > -1) {
                        text = text.replace(stringComAcentos[i].toString(), stringSemAcentos[i].toString());
                    } else {
                        break;
                    }
                }
            }
            return text;
        }
        
        // Função querySelectorByText (reprodução fiel do mini-selenium.js)
        function querySelectorByText(tagname, texto) {
            return Array.from(document.querySelectorAll(tagname)).find(el => 
                removeAcento(el.textContent.trim().toLowerCase()).includes(removeAcento(texto.toLowerCase()))
            );
        }
        
        // Buscar e clicar no botão Nova
        let botaoNova = querySelectorByText('button', 'Nova');
        
        if (botaoNova) {
            console.log('Botão Nova encontrado, tentando clicar...');
            
            // Verificar se não está desabilitado
            if (!botaoNova.hasAttribute('disabled') && !botaoNova.disabled) {
                console.log('Botão habilitado, clicando...');
                
                // Focar no botão antes de clicar
                botaoNova.focus();
                
                // Scroll para o botão se necessário
                botaoNova.scrollIntoView({ behavior: 'smooth', block: 'center' });
                
                // Clicar no botão
                botaoNova.click();
                
                console.log('Clique executado!');
                return { sucesso: true, mensagem: 'Clique executado com sucesso' };
            } else {
                console.log('Botão desabilitado');
                return { sucesso: false, mensagem: 'Botão está desabilitado' };
            }
        } else {
            console.log('Botão Nova não encontrado');
            return { sucesso: false, mensagem: 'Botão Nova não encontrado' };
        }
    """)
    
    print(f"Resultado do clique: {resultado}")
    
    # Aguardar possível mudança de URL
    print("Aguardando possível mudança de URL...")
    for i in range(10):
        time.sleep(1)
        url_atual = driver.current_url
        if url_atual != url_antes:
            print(f"✅ URL mudou para: {url_atual}")
            break
        print(f"  Tentativa {i+1}/10 - URL ainda é: {url_atual}")
    else:
        print("❌ URL não mudou após 10 segundos")
    
    # Verificar se elementos de cadastro apareceram
    print("\nVerificando elementos de cadastro...")
    elementos_cadastro = driver.execute_script("""
        let elementos = [
            'input[placeholder*="Juiz"]',
            'input[placeholder*="Solicitante"]',
            'sisbajud-cadastro-minuta',
            'mat-form-field'
        ];
        
        let encontrados = [];
        for (let seletor of elementos) {
            if (document.querySelector(seletor)) {
                encontrados.push(seletor);
            }
        }
        
        return encontrados;
    """)
    
    if elementos_cadastro:
        print(f"✅ Elementos de cadastro encontrados: {elementos_cadastro}")
    else:
        print("❌ Nenhum elemento de cadastro encontrado")

def main():
    """Função principal de teste"""
    print("INICIANDO TESTE DE DEBUG DO BOTÃO NOVA")
    print("="*60)
    
    driver = None
    try:
        # Criar driver
        driver = criar_driver()
        
        # Navegar para SISBAJUD (assumindo que você já tenha login)
        print("Para este teste, navegue manualmente para a página de minuta do SISBAJUD")
        print("e pressione Enter quando estiver pronto...")
        input()
        
        # Debug da página
        debug_pagina_minuta(driver)
        
        # Testar clique
        testar_click_nova(driver)
        
        print("\nTeste concluído! Pressione Enter para encerrar...")
        input()
        
    except Exception as e:
        print(f"Erro durante o teste: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if driver:
            driver.quit()

if __name__ == "__main__":
    main()
