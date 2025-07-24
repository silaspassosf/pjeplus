#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SISB_MODULOS/DADOS_PROCESSO.PY
Gestão de dados do processo para integração entre janelas
Extraído do bacen.py original
"""

import json
import os
from .config import ARQUIVOS, processo_dados_extraidos

def salvar_dados_processo_temp(dados_processo=None):
    """
    Salva dados do processo no arquivo do projeto (dadosatuais.json) para integração entre janelas
    
    Args:
        dados_processo: Dados do processo (usa global se None)
    """
    from .config import processo_dados_extraidos
    
    dados = dados_processo or processo_dados_extraidos
    
    if dados:
        try:
            # Usa caminho do projeto ao invés de pasta temporária
            project_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            dados_path = os.path.join(project_path, ARQUIVOS['dados_processo'])
            
            # Sempre sobrescreve o arquivo para não acumular dados de múltiplos processos
            with open(dados_path, 'w', encoding='utf-8') as f:
                json.dump(dados, f, ensure_ascii=False, indent=2)
            
            print(f'[DADOS_PROCESSO] ✅ Dados do processo salvos em: {dados_path}')
            return True
            
        except Exception as e:
            print(f'[DADOS_PROCESSO] ❌ Falha ao salvar dados do processo: {e}')
            return False
    else:
        print('[DADOS_PROCESSO] ⚠️ Nenhum dado de processo para salvar')
        return False

def carregar_dados_processo_temp():
    """
    Carrega dados do processo salvos pelo Driver 1
    
    Returns:
        dict: Dados do processo ou None se não encontrou
    """
    from .config import processo_dados_extraidos
    
    try:
        project_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        dados_path = os.path.join(project_path, ARQUIVOS['dados_processo'])
        
        if os.path.exists(dados_path):
            with open(dados_path, 'r', encoding='utf-8') as f:
                dados = json.load(f)
            
            # Atualizar variável global
            processo_dados_extraidos = dados
            
            print('[DADOS_PROCESSO] ✅ Dados do processo carregados:', dados)
            return dados
        else:
            print('[DADOS_PROCESSO] ⚠️ Nenhum dado de processo encontrado')
            return None
            
    except Exception as e:
        print(f'[DADOS_PROCESSO] ❌ Falha ao carregar dados: {e}')
        return None

def integrar_storage_processo(driver):
    """
    Integra dados do processo com o storage local, similar ao JavaScript original
    
    Args:
        driver: WebDriver Selenium
    """
    def safe_extract(data, key, default=""):
        """Extrai dados de forma segura, convertendo listas para string se necessário"""
        value = data.get(key, default)
        if isinstance(value, list):
            if value:  # Se a lista não está vazia
                return str(value[0]) if value[0] else default
            return default
        return str(value) if value else default

    def safe_escape(text):
        """Escapa texto para JavaScript de forma segura"""
        if not text:
            return ""
        return str(text).replace("'", "\\'").replace('"', '\\"').replace('\n', '\\n').replace('\r', '\\r')

    try:
        dados = carregar_dados_processo_temp()
        
        if dados:
            # Extrair número do processo
            numero = safe_escape(safe_extract(dados, "numero"))
            
            # Extrair dados do autor
            autor_list = dados.get("autor", [])
            if autor_list and len(autor_list) > 0:
                autor_data = autor_list[0]
                nome_ativo = safe_escape(autor_data.get("nome", ""))
                doc_ativo = safe_escape(autor_data.get("cpfcnpj", ""))
            else:
                nome_ativo = ""
                doc_ativo = ""
            
            # Extrair dados do réu
            reu_list = dados.get("reu", [])
            if reu_list and len(reu_list) > 0:
                reu_data = reu_list[0]
                nome_passivo = safe_escape(reu_data.get("nome", ""))
                doc_passivo = safe_escape(reu_data.get("cpfcnpj", ""))
            else:
                nome_passivo = ""
                doc_passivo = ""
            
            print(f'[DADOS_PROCESSO] Integrando dados: numero={numero}, autor={nome_ativo}, reu={nome_passivo}')
            
            # Injetar dados no JavaScript
            script_integracao = f"""
                // Simular storage.local.set do JavaScript original
                if (!window.processo_memoria) {{
                    window.processo_memoria = {{}};
                }}
                
                window.processo_memoria = {{
                    numero: '{numero}',
                    autor: [{{"nome": "{nome_ativo}", "cpfcnpj": "{doc_ativo}"}}],
                    reu: [{{"nome": "{nome_passivo}", "cpfcnpj": "{doc_passivo}"}}]
                }};
                
                console.log("Dados do processo integrados ao storage:", window.processo_memoria);
            """
            
            driver.execute_script(script_integracao)
            print('[DADOS_PROCESSO] ✅ Dados do processo integrados ao storage local')
            
        else:
            print('[DADOS_PROCESSO] ⚠️ Nenhum dado disponível para integração')
            
    except Exception as e:
        print(f'[DADOS_PROCESSO] ❌ Falha ao integrar dados do processo: {e}')
        import traceback
        traceback.print_exc()

def validar_dados_processo(dados):
    """
    Valida se os dados do processo estão no formato correto
    
    Args:
        dados: Dados do processo para validar
        
    Returns:
        bool: True se dados são válidos
    """
    try:
        if not isinstance(dados, dict):
            return False
        
        # Verificar campos obrigatórios
        campos_obrigatorios = ['numero']
        for campo in campos_obrigatorios:
            if campo not in dados:
                return False
        
        # Verificar se autor e reu são listas (se existirem)
        if 'autor' in dados and not isinstance(dados['autor'], list):
            return False
        
        if 'reu' in dados and not isinstance(dados['reu'], list):
            return False
        
        return True
        
    except Exception as e:
        print(f'[DADOS_PROCESSO] ❌ Erro na validação: {e}')
        return False

def obter_dados_processo():
    """
    Obtém dados do processo (da variável global ou arquivo)
    
    Returns:
        dict: Dados do processo ou None
    """
    from .config import processo_dados_extraidos
    
    # Primeiro tentar da variável global
    if processo_dados_extraidos:
        return processo_dados_extraidos
    
    # Se não tem na global, tentar carregar do arquivo
    return carregar_dados_processo_temp()

def limpar_dados_processo():
    """
    Limpa dados do processo (variável global e arquivo)
    """
    from .config import processo_dados_extraidos
    
    try:
        # Limpar variável global
        processo_dados_extraidos = None
        
        # Remover arquivo se existir
        project_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        dados_path = os.path.join(project_path, ARQUIVOS['dados_processo'])
        
        if os.path.exists(dados_path):
            os.remove(dados_path)
            print(f'[DADOS_PROCESSO] ✅ Arquivo de dados removido: {dados_path}')
        
        print('[DADOS_PROCESSO] ✅ Dados do processo limpos')
        return True
        
    except Exception as e:
        print(f'[DADOS_PROCESSO] ❌ Erro ao limpar dados: {e}')
        return False

def backup_dados_processo():
    """
    Cria backup dos dados do processo
    
    Returns:
        str: Caminho do backup ou None se erro
    """
    try:
        project_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        dados_path = os.path.join(project_path, ARQUIVOS['dados_processo'])
        
        if not os.path.exists(dados_path):
            print('[DADOS_PROCESSO] ⚠️ Nenhum arquivo de dados para backup')
            return None
        
        # Criar nome do backup com timestamp
        from datetime import datetime
        import shutil
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = f"{dados_path}.backup_{timestamp}"
        
        shutil.copy2(dados_path, backup_path)
        print(f'[DADOS_PROCESSO] ✅ Backup criado: {backup_path}')
        
        return backup_path
        
    except Exception as e:
        print(f'[DADOS_PROCESSO] ❌ Erro ao criar backup: {e}')
        return None

def extrair_numero_processo(dados=None):
    """
    Extrai o número do processo dos dados
    
    Args:
        dados: Dados do processo (usa carregados se None)
        
    Returns:
        str: Número do processo ou string vazia
    """
    if dados is None:
        dados = obter_dados_processo()
    
    if dados and isinstance(dados, dict):
        return dados.get('numero', '')
    
    return ''

def extrair_dados_autor(dados=None):
    """
    Extrai dados do autor dos dados do processo
    
    Args:
        dados: Dados do processo (usa carregados se None)
        
    Returns:
        dict: Dados do autor ou dict vazio
    """
    if dados is None:
        dados = obter_dados_processo()
    
    if dados and isinstance(dados, dict):
        autor_list = dados.get('autor', [])
        if autor_list and len(autor_list) > 0:
            return autor_list[0]
    
    return {}

def extrair_dados_reu(dados=None):
    """
    Extrai dados do réu dos dados do processo
    
    Args:
        dados: Dados do processo (usa carregados se None)
        
    Returns:
        dict: Dados do réu ou dict vazio
    """
    if dados is None:
        dados = obter_dados_processo()
    
    if dados and isinstance(dados, dict):
        reu_list = dados.get('reu', [])
        if reu_list and len(reu_list) > 0:
            return reu_list[0]
    
    return {}

def obter_info_dados_processo():
    """
    Obtém informações sobre os dados do processo
    
    Returns:
        dict: Informações dos dados
    """
    try:
        project_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        dados_path = os.path.join(project_path, ARQUIVOS['dados_processo'])
        
        existe_arquivo = os.path.exists(dados_path)
        dados = obter_dados_processo()
        
        info = {
            'arquivo_existe': existe_arquivo,
            'dados_carregados': dados is not None,
            'caminho_arquivo': dados_path,
            'valido': validar_dados_processo(dados) if dados else False
        }
        
        if dados:
            info['numero_processo'] = extrair_numero_processo(dados)
            info['tem_autor'] = bool(extrair_dados_autor(dados))
            info['tem_reu'] = bool(extrair_dados_reu(dados))
        
        return info
        
    except Exception as e:
        print(f'[DADOS_PROCESSO] ❌ Erro ao obter informações: {e}')
        return {'erro': str(e)}
