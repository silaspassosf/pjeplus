"""
Módulo principal para processamento de alvarás.
Extraído de listaexec2.py para modularização.
"""

import re
import json
import time
import os
from datetime import datetime
from selenium.webdriver.common.by import By
from .alvara_utils import (
    extrair_dados_alvara_via_clipboard, normalizar_nome, extrair_autor_processo,
    salvar_dados_alvara, extrair_id_timeline, extrair_data_item
)


def processar_alvara(driver, item, link, data, log=True):
    """
    Processa um alvará encontrado na timeline.
    Seleciona, extrai documento e salva dados em alvaras.js
    Ao final, se houver alvarás válidos, chama a função pagamento para análise.
    
    Args:
        driver: WebDriver do Selenium
        item: Elemento da timeline
        link: Link do documento
        data: Data do alvará
        log: Se deve exibir logs
    """
    try:
        # Importações necessárias
        import unicodedata
        
        if log:
            print(f'[ALVARA] Processando alvará: {link.text.strip()}')
        
        # a) Selecionar o documento
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", link)
        driver.execute_script("arguments[0].click();", link)
        
        if log:
            print('[ALVARA] Documento selecionado, aguardando carregamento...')
        time.sleep(2)  # 2s é o bastante para clicar no botão de extração
        
        # NOVO FLUXO: extrair texto via clipboard direto do elemento
        dados_alvara = extrair_dados_alvara_via_clipboard(driver, data_timeline=data, log=log)
        if not dados_alvara:
            if log:
                print('[ALVARA][AVISO] Não foi possível extrair dados do alvará via clipboard')
            return None
        
        # Comparação e salvamento igual ao fluxo anterior
        texto = None  # Não precisamos mais do texto do modal
        if dados_alvara:
            autor_processo = extrair_autor_processo(dados_alvara.get('texto_original', ''), log) if 'texto_original' in dados_alvara else None
            if autor_processo and dados_alvara.get('beneficiario'):
                beneficiario_norm = normalizar_nome(dados_alvara['beneficiario'])
                autor_norm = normalizar_nome(autor_processo)
                if beneficiario_norm == autor_norm:
                    if log:
                        print(f'[ALVARA] ✅ Beneficiário ({dados_alvara["beneficiario"]}) = Autor ({autor_processo}) - Salvando no arquivo')
                    salvar_dados_alvara(dados_alvara, log)
                else:
                    if log:
                        print(f'[ALVARA] ❌ Beneficiário ({dados_alvara["beneficiario"]}) ≠ Autor ({autor_processo}) - NÃO salvando no arquivo')
            else:
                if log:
                    print(f'[ALVARA] ⚠️ Não foi possível comparar beneficiário com autor - Salvando por segurança')
                salvar_dados_alvara(dados_alvara, log)
            
            return dados_alvara
        else:
            if log:
                print('[ALVARA][AVISO] Não foi possível extrair dados do alvará')
            return None
    except Exception as e:
        if log:
            print(f'[ALVARA][ERRO] Falha ao processar alvará: {e}')
        return None
    finally:
        # LIMPEZA FINAL: Garantir que não há modais abertos ao sair da função
        try:
            modais_restantes = driver.find_elements(By.CSS_SELECTOR, 'main#main-content.mat-dialog-content')
            if modais_restantes:
                if log:
                    print(f'[ALVARA] 🧹 Limpeza final: {len(modais_restantes)} modal(s) ainda aberto(s)')
                for _ in range(3):
                    try:
                        from selenium.webdriver.common.keys import Keys
                        driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                        from selenium.webdriver.support.ui import WebDriverWait
                        from selenium.webdriver.support import expected_conditions as EC
                        WebDriverWait(driver, 1).until(
                            EC.invisibility_of_element_located((By.CSS_SELECTOR, 'main#main-content.mat-dialog-content'))
                        )
                    except:
                        pass
                modais_finais = driver.find_elements(By.CSS_SELECTOR, 'main#main-content.mat-dialog-content')
                if modais_finais:
                    if log:
                        print(f'[ALVARA] ⚠️ Ainda restam {len(modais_finais)} modal(s) após limpeza')
                else:
                    if log:
                        print('[ALVARA] ✅ Limpeza concluída, nenhum modal restante')
        except Exception as e_limpeza:
            if log:
                print(f'[ALVARA][ERRO] Erro na limpeza final: {e_limpeza}')


def ler_alvaras_arquivo(log=True):
    """
    Lê alvarás existentes do arquivo alvaras.js
    
    Args:
        log: Se deve exibir logs
        
    Returns:
        list: Lista de alvarás do arquivo
    """
    try:
        arquivo_path = os.path.join(os.getcwd(), 'alvaras.js')
        
        if not os.path.exists(arquivo_path):
            if log:
                print('[ALVARA] Arquivo alvaras.js não existe, criando novo')
            return []
        
        with open(arquivo_path, 'r', encoding='utf-8') as f:
            conteudo = f.read()
            
        if conteudo.strip():
            # Tentar extrair dados JSON do arquivo JS
            match = re.search(r'const alvaras = (\[.*?\]);', conteudo, re.DOTALL)
            if match:
                return json.loads(match.group(1))
        
        return []
        
    except Exception as e:
        if log:
            print(f'[ALVARA][ERRO] Erro ao ler arquivo: {e}')
        return []


def atualizar_status_alvara(alvaras, alvara_alvo, novo_status, log=True):
    """
    Atualiza o status de um alvará na lista
    
    Args:
        alvaras: Lista de alvarás
        alvara_alvo: Alvará a ser atualizado
        novo_status: Novo status
        log: Se deve exibir logs
    """
    try:
        for alvara in alvaras:
            # Comparar por data e valor
            if (alvara.get('data_expedicao') == alvara_alvo.get('data_expedicao') and 
                alvara.get('valor') == alvara_alvo.get('valor')):
                alvara['status'] = novo_status
                if log:
                    print(f'[ALVARA] Status atualizado: {alvara_alvo.get("data_expedicao")} - {novo_status}')
                break
                
    except Exception as e:
        if log:
            print(f'[ALVARA][ERRO] Erro ao atualizar status: {e}')


def salvar_alvaras_arquivo(dados_alvaras, log=True):
    """
    Salva a lista completa de alvarás no arquivo alvaras.js
    
    Args:
        dados_alvaras: Lista completa de alvarás
        log: Se deve exibir logs
    """
    try:
        arquivo_path = os.path.join(os.getcwd(), 'alvaras.js')
        
        # Salvar arquivo JS atualizado
        conteudo_js = f"""// Dados de alvarás extraídos automaticamente
// Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}

const alvaras = {json.dumps(dados_alvaras, indent=2, ensure_ascii=False)};

// Função para buscar alvarás por período
function buscarAlvarasPorPeriodo(dataInicio, dataFim) {{
    return alvaras.filter(alvara => {{
        const data = new Date(alvara.data_expedicao.split('/').reverse().join('-'));
        const inicio = new Date(dataInicio);
        const fim = new Date(dataFim);
        return data >= inicio && data <= fim;
    }});
}}

// Função para calcular total de valores
function calcularTotalAlvaras(lista = alvaras) {{
    return lista.reduce((total, alvara) => {{
        const valor = parseFloat(alvara.valor.replace(/[R$\s.]/g, '').replace(',', '.'));
        return total + (isNaN(valor) ? 0 : valor);
    }}, 0);
}}

// Função para buscar alvarás registrados
function buscarAlvarasRegistrados() {{
    return alvaras.filter(alvara => alvara.status === 'ALVARA_REGISTRADO');
}}

console.log(`Total de alvarás registrados: ${{alvaras.length}}`);
"""
        
        with open(arquivo_path, 'w', encoding='utf-8') as f:
            f.write(conteudo_js)
        
        if log:
            print(f'[ALVARA] Arquivo atualizado: {arquivo_path}')
            print(f'[ALVARA] Total de {len(dados_alvaras)} alvarás salvos')
    
    except Exception as e:
        if log:
            print(f'[ALVARA][ERRO] Erro ao salvar arquivo: {e}')
