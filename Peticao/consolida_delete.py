#!/usr/bin/env python3
"""
Script consolidado: gera e insere bookmarklet ao final de delete.js
Execução única: python del.py
Sem dependências externas de outros arquivos .js
"""

import json
from pathlib import Path


def extrair_processos_delete():
    """Extrai processos de delete.js"""
    
    delete_file = Path(__file__).parent / "delete.js"
    
    if not delete_file.exists():
        print("❌ delete.js não encontrado.")
        return {}
    
    delete_processes = {}
    
    try:
        with open(delete_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Estratégia 1: Extrair JSON declarado
        start_marker = 'const delete_processes = {'
        end_marker = '};'
        
        start = content.find(start_marker)
        if start != -1:
            start += len(start_marker)
            end = content.find(end_marker, start)
            if end != -1:
                json_str = content[start:end].strip()
                if json_str:
                    if not json_str.startswith('{'):
                        json_str = '{' + json_str + '}'
                    try:
                        delete_processes = json.loads(json_str)
                    except:
                        pass
        
        # Estratégia 2: Procurar linhas JSON ou números
        if not delete_processes:
            for linha in content.split('\n'):
                linha = linha.strip()
                if linha and not linha.startswith('//') and not linha.startswith('javascript:'):
                    try:
                        dado = json.loads(linha)
                        if isinstance(dado, dict):
                            delete_processes.update(dado)
                    except:
                        if linha.isdigit():
                            delete_processes[linha] = True
    
    except Exception as e:
        print(f"❌ Erro ao ler delete.js: {e}")
    
    return delete_processes


def gerar_bookmarklet_apagar(processos):
    """Gera bookmarklet JavaScript com os processos extraídos.
    O registro agora contém apenas o id_doc por processo.
    """

    # Serializar processos para JSON compacto
    delete_json = json.dumps(processos, ensure_ascii=False, separators=(',', ':'))
    checkbox_selector = json.dumps(
        'input[type="checkbox"], mat-checkbox input, input.mat-checkbox-input',
        ensure_ascii=False,
    )

    # Lógica mínima: número do processo + id_doc extraído do href de a[accesskey="v"]
    bookmarklet = (
        'javascript:(function(){'
        'const dp=' + delete_json + ';'
        'function matchLinha(num,hrefHtml){'
        'var entradas=dp[num];'
        'if(!entradas)return false;'
        'if(!Array.isArray(entradas))entradas=[entradas];'
        'return entradas.some(function(e){'
        'var idDoc=typeof e==="string"||typeof e==="number"?String(e).trim():String((e&&e.id_doc)||"").trim();'
        'return !!idDoc&&hrefHtml.includes("/"+idDoc+"/");'
        '});'
        '}'
        'console.log("[DEL] Iniciando seleção...");'
        'var linhas=document.querySelectorAll("tr.cdk-drag,tr[data-row],tr.ng-star-inserted");'
        'var selecionados=0;'
        'linhas.forEach(function(linha){'
        'try{'
        'var a=linha.querySelector("pje-descricao-processo a,td pje-descricao-processo a");'
        'if(!a||!a.textContent)return;'
        'var num=a.textContent.trim();'
        'if(!dp.hasOwnProperty(num))return;'
            'var aVis=linha.querySelector("a[accesskey=\\"a\\"]");'
        'var hrefHtml=aVis?(aVis.href||aVis.getAttribute("href")||""):"";'
        'if(!matchLinha(num,hrefHtml))return;'
        'var cb=linha.querySelector(' + checkbox_selector + ');'
        'if(cb){cb.click();selecionados++;'
        r'var docId=hrefHtml.match(/\/documento\/(\d+)\//);'
        'console.log("[DEL] OK:",num,"| doc_id:",docId?docId[1]:"?");}'
        '}catch(e){console.error("[DEL] erro linha:",e);}'
        '});'
        'alert("Selecionados: "+selecionados+"\\nClique no lixão para remover.");'
        '})();'
    )
    return bookmarklet


def consolidar_delete_com_bookmarklet():
    """Consolida delete.js e insere bookmarklet ao final"""
    
    # 1. Extrair processos
    processos = extrair_processos_delete()
    
    if not processos:
        print("⚠️  Nenhum processo encontrado em delete.js")
        return False
    
    print(f"📊 Processos extraídos: {len(processos)}")
    
    # 2. Gerar bookmarklet
    bookmarklet = gerar_bookmarklet_apagar(processos)
    
    # 3. Ler delete.js e remover bookmarklet antigo
    delete_file = Path(__file__).parent / "delete.js"
    with open(delete_file, 'r', encoding='utf-8') as f:
        conteudo = f.read()
    
    # Remover linhas que começam com "javascript:"
    linhas_limpas = [
        l for l in conteudo.split('\n')
        if not l.strip().startswith('javascript:')
    ]
    
    # 4. Adicionar novo bookmarklet ao final
    conteudo_novo = '\n'.join(linhas_limpas).rstrip() + '\n' + bookmarklet + '\n'
    
    # 5. Salvar arquivo
    with open(delete_file, 'w', encoding='utf-8') as f:
        f.write(conteudo_novo)
    
    print(f"✅ Bookmarklet inserido ao final de delete.js")
    print(f"📁 Arquivo: {delete_file.absolute()}")
    
    return True


if __name__ == "__main__":
    consolidar_delete_com_bookmarklet()