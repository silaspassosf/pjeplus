#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste simples para inserção HTML no editor
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
import time

def test_html_insert():
    """Teste de inserção HTML"""
    options = Options()
    driver = webdriver.Firefox(options=options)
    
    try:
        # Criar página teste que replica EXATAMENTE o editor do PJe
        html_teste = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Teste HTML Insert - Réplica PJe Editor</title>
            <style>
                .area-conteudo {
                    border: 1px solid #ccc;
                    min-height: 200px;
                    padding: 10px;
                    font-family: Arial, sans-serif;
                }
                .corpo {
                    font-size: 12pt;
                    line-height: 1.5;
                    margin-left: 0 !important;
                    text-align: justify;
                    text-indent: 4.5cm;
                }
            </style>
        </head>
        <body>
            <h3>Teste de Inserção HTML - Réplica do Editor PJe</h3>
            <div contenteditable="true" 
                 class="area-conteudo ck ck-content ck-editor__editable ck-rounded-corners ck-editor__editable_inline ck-blurred" 
                 aria-label="Conteúdo principal. Alt+F10 para acessar a barra de tarefas" 
                 lang="pt-br" 
                 dir="ltr" 
                 role="textbox" 
                 id="editor">
                <p style="font-size:12pt;line-height:1.5;margin-left:0 !important;text-align:justify;text-indent:4.5cm;" class="corpo">--</p>
            </div>
            <p><strong>Estado inicial:</strong> Marcador "--" dentro de parágrafo com classe "corpo"</p>
        </body>
        </html>
        """
        
        driver.get("data:text/html," + html_teste)
        time.sleep(1)
        
        editable = driver.find_element(By.ID, "editor")
        
        # Script que replica exatamente o cenário do PJe
        script = """
        console.log('=== TESTE INSERÇÃO HTML - RÉPLICA PJE ===');
        
        // 1. Obter editor (passado como argumento)
        let editor = arguments[0];
        let paragrafo = editor.querySelector('p.corpo');
        
        console.log('Estado inicial:');
        console.log('- Editor innerHTML:', editor.innerHTML);
        console.log('- Parágrafo texto:', paragrafo ? paragrafo.textContent : 'PARÁGRAFO NÃO ENCONTRADO');
        console.log('- Marcador presente:', paragrafo ? paragrafo.textContent.includes('--') : false);
        
        if (!paragrafo) {
            return { sucesso: false, erro: 'Parágrafo com classe "corpo" não encontrado!' };
        }
        
        if (!paragrafo.textContent.includes('--')) {
            return { sucesso: false, erro: 'Marcador "--" não encontrado no parágrafo!' };
        }
        
        // 2. HTML para inserir (exatamente como carta.py)
        let htmlParaInserir = `
        <div class="secao-carta">
            <p><strong>Carta de Anuência:</strong></p>
            <p>Processo: <a href="https://pje.trt2.jus.br/processo/123456" target="_blank">1234567-89.2024.5.02.0001</a></p>
            <p>Esta é uma carta de anuência com link clicável.</p>
        </div>`;
        
        console.log('2. HTML para inserir:', htmlParaInserir);
        
        // 3. Método simples: innerHTML.replace() 
        console.log('3. Executando innerHTML.replace()...');
        let htmlOriginal = editor.innerHTML;
        let novoHtml = htmlOriginal.replace('--', htmlParaInserir);
        
        console.log('- HTML original:', htmlOriginal);
        console.log('- HTML após replace:', novoHtml);
        
        // Aplicar o novo HTML
        editor.innerHTML = novoHtml;
        
        // 4. Verificar resultado
        console.log('4. Verificando resultado...');
        let htmlFinal = editor.innerHTML;
        
        console.log('- HTML final:', htmlFinal);
        console.log('- Marcador removido:', !htmlFinal.includes('--'));
        console.log('- HTML inserido presente:', htmlFinal.includes('Carta de Anuência'));
        console.log('- Link presente:', htmlFinal.includes('<a href='));
        
        // 5. Testar estrutura do link
        let link = editor.querySelector('a[href*="processo"]');
        if (link) {
            console.log('- Link encontrado:', link.href);
            console.log('- Link clicável:', true);
        } else {
            console.log('❌ Link não encontrado!');
        }
        
        // 6. Resultado final
        let sucesso = !htmlFinal.includes('--') && 
                     htmlFinal.includes('Carta de Anuência') && 
                     htmlFinal.includes('<a href=');
                     
        console.log('=== RESULTADO FINAL ===');
        console.log('Sucesso:', sucesso ? '✅ SIM' : '❌ NÃO');
        
        return { 
            sucesso: sucesso, 
            texto_final: htmlFinal,
            marcador_removido: !htmlFinal.includes('--'),
            html_inserido: htmlFinal.includes('Carta de Anuência'),
            link_presente: htmlFinal.includes('<a href=')
        };
        """
        
        resultado = driver.execute_script(script, editable)
        
        print("Resultado do teste:", resultado)
        
        # Aguardar para visualizar
        print("Aguardando 5 segundos para visualizar...")
        time.sleep(5)
        
        # Verificar conteúdo final
        conteudo_final = editable.get_attribute('innerHTML')
        print("Conteúdo final:", conteudo_final)
        
    finally:
        driver.quit()

if __name__ == "__main__":
    test_html_insert()
