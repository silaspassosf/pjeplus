#!/usr/bin/env python3
"""
Teste simples e direto da inserção no editor
"""

from driver_config import criar_driver
from editor_insert import inserir_html_no_editor_apos_marcador
import time

def teste_inserir_editor():
    print("[TESTE] Iniciando teste da inserção no editor...")
    
    # 1. Criar driver
    driver = criar_driver()
    
    try:
        # 2. Navegar para processo específico (mesmo que foi testado antes)
        url_processo = "https://pje.trt2.jus.br/pjekz/processo/3734856/detalhe"
        print(f"[TESTE] Navegando para: {url_processo}")
        driver.get(url_processo)
        time.sleep(3)
        
        # 3. Ir para anexar documentos
        print("[TESTE] Clicando no menu lateral...")
        driver.find_element("css selector", ".menu-lateral-botao").click()
        time.sleep(1)
        
        print("[TESTE] Clicando em Anexar Documentos...")
        driver.find_element("css selector", "[data-original-title='Anexar Documentos']").click()
        time.sleep(3)
        
        # 4. Selecionar Certidão
        print("[TESTE] Selecionando tipo Certidão...")
        driver.find_element("css selector", "select[name='tipoDocumento'] option[value='Certidão']").click()
        time.sleep(1)
        
        # 5. Preencher descrição
        print("[TESTE] Preenchendo descrição...")
        driver.find_element("css selector", "input[name='descricao']").send_keys("Teste Editor")
        time.sleep(1)
        
        # 6. Selecionar modelo 'xs carta'
        print("[TESTE] Selecionando modelo...")
        modelo_input = driver.find_element("css selector", "input[name='modeloSelecionado']")
        modelo_input.clear()
        modelo_input.send_keys("xs carta")
        time.sleep(1)
        
        # Aplicar filtro
        from selenium.webdriver.common.keys import Keys
        modelo_input.send_keys(Keys.ENTER)
        time.sleep(1)
        
        # Clicar no modelo filtrado
        driver.find_element("css selector", "#tree .nodo-filtrado").click()
        time.sleep(1)
        
        # Inserir modelo
        modelo_input.send_keys(Keys.SPACE)
        time.sleep(2)
        
        # 7. TESTE DA INSERÇÃO
        print("[TESTE] Testando inserção do HTML...")
        
        html_teste = """<p class="corpo" style="font-size: 12pt; line-height: normal; margin-left: 0px !important; text-align: justify !important; text-indent: 4.5cm;">
    <strong>Id Pje:</strong> 62a83b4<br>
    <strong>Rastreamento:</strong> <a href="https://aplicacoes1.trt2.jus.br/eCarta-web/consultarObjeto.xhtml?codigo=YQ829742261BR" target="_blank">YQ829742261BR</a><br>
    <strong>Destinatário:</strong> ANGELA APARECIDA FARIA<br>
    <strong>Data do envio:</strong> 28/08/2025<br>
    <strong>Data da entrega:</strong> 01/09/2025<br>
    <strong>Status:</strong> Objeto entregue ao destinatário
</p>"""
        
        resultado = inserir_html_no_editor_apos_marcador(driver, html_teste, "--", debug=True)
        
        print(f"[TESTE] Resultado da inserção: {resultado}")
        
        if resultado:
            print("[TESTE] ✅ Inserção bem-sucedida!")
        else:
            print("[TESTE] ❌ Falha na inserção!")
        
        # Aguardar para verificação manual
        print("[TESTE] Verificar manualmente se o conteúdo foi inserido...")
        print("[TESTE] Pressione Ctrl+C para finalizar...")
        
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("[TESTE] Finalizando teste...")
    except Exception as e:
        print(f"[TESTE] Erro durante teste: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    teste_inserir_editor()
