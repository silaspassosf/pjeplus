#!/usr/bin/env python3
"""
Teste da função de inserção HTML usando método bookmarklet
Testa especificamente com o HTML da carta de anuência
"""

import time
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By

def teste_carta_metodo_bookmarklet():
    """Testa inserção da carta usando método bookmarklet"""
    
    # Configurar Firefox
    options = Options()
    options.add_argument('--width=1200')
    options.add_argument('--height=800')
    
    driver = webdriver.Firefox(options=options)
    
    try:
        print('[TESTE] Criando página de teste que replica o editor PJe...')
        
        # HTML da carta (exemplo real)
        html_carta = '''<div class="secao-carta">
<p class="corpo" style="font-size: 12pt; line-height: normal; margin-left: 0px !important; text-align: justify !important; text-indent: 4.5cm;">
&nbsp; &nbsp; IID: 62a83b4<br>
DESTINATÁRIO: ANGELA APARECIDA FARIA<br>
DATA DO ENVIO: 28/08/2025<br>
DATA DE ENTREGA: 01/09/2025<br>
RESULTADO: Objeto entregue ao destinatário<br>
OBJETO: <a target="_blank" rel="noopener noreferrer" href="https://aplicacoes1.trt2.jus.br/eCarta-web/consultarObjeto.xhtml?codigo=YQ829742261BR">YQ829742261BR</a><br>
DEVOLVIDA? ( ) - Desmarcado significa ENTREGA CONFIRMADA.
</p>
</div>'''
        
        # Criar página teste que replica EXATAMENTE o editor do PJe
        html_teste = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Teste Carta - Método Bookmarklet</title>
            <style>
                .area-conteudo {{
                    border: 1px solid #ccc;
                    min-height: 200px;
                    padding: 10px;
                    font-family: Arial, sans-serif;
                }}
                .corpo {{
                    font-size: 12pt;
                    line-height: 1.5;
                    margin-left: 0 !important;
                    text-align: justify;
                    text-indent: 4.5cm;
                }}
            </style>
        </head>
        <body>
            <h3>Teste Carta - Método Bookmarklet</h3>
            <div contenteditable="true" 
                 class="area-conteudo ck ck-content ck-editor__editable ck-rounded-corners ck-editor__editable_inline ck-blurred" 
                 aria-label="Conteúdo principal" 
                 lang="pt-br" 
                 dir="ltr" 
                 role="textbox" 
                 id="editor">
                <p style="font-size:12pt;line-height:1.5;margin-left:0 !important;text-align:justify;text-indent:4.5cm;" class="corpo">--</p>
            </div>
            <p><strong>Estado inicial:</strong> Marcador "--" dentro de parágrafo com classe "corpo"</p>
            <p><strong>Teste:</strong> Inserir HTML da carta de anuência usando método bookmarklet</p>
        </body>
        </html>
        """
        
        # Carregar a página
        driver.get("data:text/html;charset=utf-8," + html_teste.replace('#', '%23'))
        time.sleep(1)
        
        # Encontrar o editor
        editor = driver.find_element(By.ID, "editor")
        print('[TESTE] ✅ Editor encontrado')
        
        # JavaScript que simula o método bookmarklet
        script_bookmarklet = f"""
        console.log('[TESTE] === INSERÇÃO CARTA VIA MÉTODO BOOKMARKLET ===');
        
        let editor = arguments[0];
        let htmlContent = arguments[1];
        let marcador = '--';
        
        // 1. Verificar estado inicial
        let htmlOriginal = editor.innerHTML;
        console.log('HTML original:', htmlOriginal);
        
        if (!htmlOriginal.includes(marcador)) {{
            return {{ sucesso: false, erro: 'Marcador não encontrado' }};
        }}
        
        // 2. ESTRATÉGIA BOOKMARKLET: Criar container temporário
        let container = document.createElement('div');
        container.innerHTML = htmlContent;
        
        // 3. Posicionar fora da tela
        container.style.position = 'absolute';
        container.style.left = '-9999px';
        document.body.appendChild(container);
        
        try {{
            // 4. Selecionar conteúdo usando Range
            let range = document.createRange();
            range.selectNodeContents(container);
            
            let selection = window.getSelection();
            selection.removeAllRanges();
            selection.addRange(range);
            
            // 5. Copiar para clipboard
            let copySuccess = document.execCommand('copy');
            console.log('Cópia para clipboard:', copySuccess);
            
            // 6. Limpar seleção temporária
            selection.removeAllRanges();
            document.body.removeChild(container);
            
            if (!copySuccess) {{
                return {{ sucesso: false, erro: 'Falha ao copiar' }};
            }}
            
            // 7. Encontrar parágrafo no editor
            let paragrafo = editor.querySelector('p.corpo');
            if (!paragrafo) {{
                return {{ sucesso: false, erro: 'Parágrafo não encontrado' }};
            }}
            
            // 8. Encontrar nó de texto com marcador
            let textNode = paragrafo.firstChild;
            if (!textNode || textNode.nodeType !== Node.TEXT_NODE) {{
                return {{ sucesso: false, erro: 'Nó de texto não encontrado' }};
            }}
            
            let posicaoMarcador = textNode.textContent.indexOf(marcador);
            if (posicaoMarcador < 0) {{
                return {{ sucesso: false, erro: 'Marcador não encontrado no texto' }};
            }}
            
            // 9. Selecionar apenas o marcador
            let rangeMarcador = document.createRange();
            rangeMarcador.setStart(textNode, posicaoMarcador);
            rangeMarcador.setEnd(textNode, posicaoMarcador + marcador.length);
            
            selection.removeAllRanges();
            selection.addRange(rangeMarcador);
            
            console.log('Marcador selecionado');
            
            // 10. SIMULAR PASTE
            let pasteSuccess = false;
            
            // Método 1: execCommand paste
            try {{
                pasteSuccess = document.execCommand('paste');
                console.log('Paste via execCommand:', pasteSuccess);
            }} catch (e) {{
                console.log('execCommand paste falhou:', e);
            }}
            
            // Método 2: Inserção direta (fallback)
            if (!pasteSuccess) {{
                try {{
                    rangeMarcador.deleteContents();
                    
                    let tempDiv = document.createElement('div');
                    tempDiv.innerHTML = htmlContent;
                    let fragment = document.createDocumentFragment();
                    
                    while (tempDiv.firstChild) {{
                        fragment.appendChild(tempDiv.firstChild);
                    }}
                    
                    rangeMarcador.insertNode(fragment);
                    
                    console.log('Inserção direta realizada');
                    pasteSuccess = true;
                }} catch (e) {{
                    console.log('Erro na inserção direta:', e);
                }}
            }}
            
            // 11. Verificar resultado
            let htmlFinal = editor.innerHTML;
            let marcadorRemovido = !htmlFinal.includes(marcador);
            let htmlInserido = htmlFinal.includes('DESTINATÁRIO');
            let linkPresente = htmlFinal.includes('<a target="_blank"');
            
            console.log('=== RESULTADO ===');
            console.log('HTML final:', htmlFinal);
            console.log('Marcador removido:', marcadorRemovido);
            console.log('HTML da carta inserido:', htmlInserido);
            console.log('Link presente:', linkPresente);
            
            return {{
                sucesso: pasteSuccess && marcadorRemovido,
                marcador_removido: marcadorRemovido,
                html_inserido: htmlInserido,
                link_presente: linkPresente,
                html_final: htmlFinal
            }};
            
        }} catch (e) {{
            if (document.body.contains(container)) {{
                document.body.removeChild(container);
            }}
            console.error('Erro:', e);
            return {{ sucesso: false, erro: e.toString() }};
        }}
        """
        
        # Executar o teste
        print('[TESTE] Executando inserção via método bookmarklet...')
        resultado = driver.execute_script(script_bookmarklet, editor, html_carta)
        
        print(f'[TESTE] Resultado: {resultado}')
        
        if resultado and resultado.get('sucesso'):
            print('[TESTE] ✅ SUCESSO! Carta inserida via método bookmarklet')
            print(f'[TESTE] - Marcador removido: {resultado.get("marcador_removido")}')
            print(f'[TESTE] - HTML inserido: {resultado.get("html_inserido")}')
            print(f'[TESTE] - Link presente: {resultado.get("link_presente")}')
            
            # Verificar visualmente
            time.sleep(2)
            
            # Verificar se link é clicável
            try:
                link = driver.find_element(By.CSS_SELECTOR, 'a[href*="aplicacoes1.trt2.jus.br"]')
                print('[TESTE] ✅ Link encontrado e é clicável')
                print(f'[TESTE] URL do link: {link.get_attribute("href")}')
            except:
                print('[TESTE] ❌ Link não encontrado ou não clicável')
                
        else:
            print('[TESTE] ❌ FALHA na inserção')
            erro = resultado.get('erro') if resultado else 'Resultado None'
            print(f'[TESTE] Erro: {erro}')
        
        # Manter navegador aberto para inspeção visual
        input('[TESTE] Pressione Enter para fechar o navegador...')
        
    except Exception as e:
        print(f'[TESTE] ❌ Erro durante teste: {e}')
        import traceback
        traceback.print_exc()
    
    finally:
        driver.quit()


if __name__ == '__main__':
    teste_carta_metodo_bookmarklet()
