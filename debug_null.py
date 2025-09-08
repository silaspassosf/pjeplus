#!/usr/bin/env python3
# -*- coding: utf-8 -*-

def debug_null_bytes():
    dados_html_teste = '''<p class="corpo" style="font-size: 12pt; line-height: normal; margin-left: 0px !important; text-align: justify !important; text-indent: 4.5cm;">&nbsp; &nbsp; IID: 62a83b4<br>DESTINATÁRIO: ANGELA APARECIDA FARIA<br>DATA DO ENVIO: 28/08/2025<br>DATA DE ENTREGA: 01/09/2025<br>RESULTADO: Objeto entregue ao destinatário<br>OBJETO: <a target="_blank" rel="noopener noreferrer" href="https://aplicacoes1.trt2.jus.br/eCarta-web/consultarObjeto.xhtml?codigo=YQ829742261BR">YQ829742261BR</a><br>DEVOLVIDA? ( ) - Desmarcado significa ENTREGA CONFIRMADA.</p>'''
    
    print("Verificando null bytes...")
    print(f"Tamanho: {len(dados_html_teste)}")
    print(f"Contém null bytes: {'\x00' in dados_html_teste}")
    
    # Verificar cada caractere
    for i, char in enumerate(dados_html_teste):
        if ord(char) == 0:
            print(f"Null byte encontrado na posição {i}")
        if ord(char) < 32 and ord(char) not in [9, 10, 13]:  # Tab, LF, CR são ok
            print(f"Caractere de controle encontrado na posição {i}: {ord(char)}")
    
    # Tentar limpar
    cleaned = dados_html_teste.replace('\x00', '')
    print(f"Após limpeza: {len(cleaned)} caracteres")
    
    # Testar JSON
    import json
    try:
        json_str = json.dumps(cleaned)
        print("JSON encoding: OK")
        print(f"JSON: {json_str[:100]}...")
    except Exception as e:
        print(f"Erro no JSON: {e}")

if __name__ == "__main__":
    debug_null_bytes()
