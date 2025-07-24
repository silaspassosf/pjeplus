#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SISB_MODULOS/COOKIES.PY
Gestão de cookies para SISBAJUD/BACEN
Baseado na implementação do driver_config.py
"""

import json
import os
import time
import glob
from datetime import datetime, timedelta
from .config import COOKIES_CONFIG, URLS

def salvar_cookies_sisbajud(driver, caminho_arquivo=None, info_extra=None):
    """
    Salva todos os cookies da sessão SISBAJUD em um arquivo JSON.
    O nome do arquivo inclui data/hora e info_extra se fornecido.
    Baseado na implementação do driver_config.py
    """
    try:
        cookies = driver.get_cookies()
        if not cookies:
            print('[COOKIES] Nenhum cookie encontrado para salvar.')
            return False
        
        # Filtrar apenas cookies dos domínios relevantes do SISBAJUD
        dominios_validos = ['sisbajud.cloud.pje.jus.br', 'sso.cloud.pje.jus.br', 'cnj.jus.br']
        cookies_filtrados = [
            c for c in cookies 
            if any(dominio in c.get('domain', '') for dominio in dominios_validos)
        ]
        
        if not cookies_filtrados:
            print('[COOKIES] Nenhum cookie SISBAJUD encontrado para salvar.')
            return False
        
        if not caminho_arquivo:
            pasta = os.path.join(os.getcwd(), 'cookies_sisbajud')
            os.makedirs(pasta, exist_ok=True)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            info = f'_{info_extra}' if info_extra else ''
            caminho_arquivo = os.path.join(pasta, f'cookies_sisbajud{info}_{timestamp}.json')
        
        # Adiciona metadados para validação
        dados_cookies = {
            'timestamp': datetime.now().isoformat(),
            'url_base': driver.current_url,
            'tipo': 'sisbajud',
            'cookies': cookies_filtrados
        }
        
        with open(caminho_arquivo, 'w', encoding='utf-8') as f:
            json.dump(dados_cookies, f, ensure_ascii=False, indent=2)
        
        print(f'[COOKIES] ✅ {len(cookies_filtrados)} cookies SISBAJUD salvos em: {caminho_arquivo}')
        return True
        
    except Exception as e:
        print(f'[COOKIES] ❌ Erro ao salvar cookies: {e}')
        return False

def carregar_cookies_sisbajud(driver, max_idade_horas=24):
    """
    Carrega cookies de sessão SISBAJUD mais recentes e válidos automaticamente.
    Retorna True se cookies foram carregados com sucesso, False caso contrário.
    Baseado na implementação do driver_config.py
    """
    try:
        pasta = os.path.join(os.getcwd(), 'cookies_sisbajud')
        if not os.path.exists(pasta):
            print('[COOKIES] Pasta de cookies SISBAJUD não encontrada.')
            return False
        
        # Busca todos os arquivos de cookies
        arquivos_cookies = glob.glob(os.path.join(pasta, 'cookies_sisbajud*.json'))
        if not arquivos_cookies:
            print('[COOKIES] Nenhum arquivo de cookies SISBAJUD encontrado.')
            return False
        
        # Encontra o arquivo mais recente
        arquivo_mais_recente = max(arquivos_cookies, key=os.path.getmtime)
        
        with open(arquivo_mais_recente, 'r', encoding='utf-8') as f:
            dados = json.load(f)
        
        # Verifica se é formato antigo ou novo
        if 'timestamp' in dados:
            timestamp_str = dados['timestamp']
            cookies = dados['cookies']
        else:
            # Formato antigo - usa timestamp do arquivo
            timestamp_str = datetime.fromtimestamp(os.path.getmtime(arquivo_mais_recente)).isoformat()
            cookies = dados
        
        # Verifica idade dos cookies
        timestamp_cookies = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00').replace('+00:00', ''))
        idade = datetime.now() - timestamp_cookies
        
        if idade > timedelta(hours=max_idade_horas):
            print(f'[COOKIES] Cookies muito antigos ({idade.total_seconds()/3600:.1f}h). Pulando.')
            return False
        
        # Navega para o domínio SISBAJUD antes de carregar cookies
        print('[COOKIES] 🔄 Navegando para domínio SISBAJUD...')
        driver.get('https://sso.cloud.pje.jus.br')
        time.sleep(2)
        
        # Carrega cookies
        cookies_carregados = 0
        for cookie in cookies:
            try:
                # Remove campos que podem causar problemas
                cookie_limpo = {
                    'name': cookie['name'],
                    'value': cookie['value'],
                    'domain': cookie['domain'],
                    'path': cookie.get('path', '/'),
                    'secure': cookie.get('secure', False),
                    'httpOnly': cookie.get('httpOnly', False)
                }
                
                driver.add_cookie(cookie_limpo)
                cookies_carregados += 1
                
            except Exception as e:
                print(f'[COOKIES] Erro ao carregar cookie {cookie.get("name", "unknown")}: {e}')
        
        print(f'[COOKIES] {cookies_carregados} cookies carregados de {os.path.basename(arquivo_mais_recente)}')
        
        # Testa se os cookies funcionam navegando para uma página protegida
        driver.get('https://sisbajud.cloud.pje.jus.br')
        time.sleep(3)
        
        # Verifica se recebeu a URL de acesso negado
        if 'acesso-negado' in driver.current_url.lower() or 'erro' in driver.current_url.lower():
            print('[COOKIES] URL de acesso negado detectada. Cookies inválidos.')
            # Apaga todos os cookies do navegador
            try:
                driver.delete_all_cookies()
                print('[COOKIES] Cookies apagados do navegador.')
            except Exception as e:
                print(f'[COOKIES] Erro ao apagar cookies: {e}')
            
            return False
        
        # Verifica se está logado (não é redirecionado para login)
        if 'login' in driver.current_url.lower() or 'sso' in driver.current_url.lower():
            print('[COOKIES] Cookies inválidos - ainda redirecionando para login.')
            return False
        else:
            print('[COOKIES] ✅ Cookies válidos! Login automático SISBAJUD realizado.')
            return True
            
    except Exception as e:
        print(f'[COOKIES] ❌ Falha ao carregar cookies: {e}')
        return False

def verificar_e_aplicar_cookies_sisbajud(driver):
    """
    Função integrada que verifica e aplica cookies SISBAJUD automaticamente.
    Retorna True se login via cookies foi bem-sucedido.
    """
    print('[COOKIES] Tentando login automático SISBAJUD via cookies salvos...')
    sucesso = carregar_cookies_sisbajud(driver)
    
    if sucesso:
        print('[COOKIES] ✅ Login SISBAJUD realizado via cookies! Pularemos a tela de login.')
    else:
        print('[COOKIES] ❌ Cookies inválidos ou inexistentes. Login manual necessário.')
    
    return sucesso

def validar_cookies(caminho='cookies_sisbajud.json'):
    """
    Valida se o arquivo de cookies é válido
    
    Args:
        caminho: Caminho do arquivo de cookies
        
    Returns:
        bool: True se válido
    """
    if not os.path.exists(caminho):
        return False
    
    try:
        with open(caminho, 'r', encoding='utf-8') as f:
            cookies = json.load(f)
        
        # Verificar se é uma lista
        if not isinstance(cookies, list):
            return False
        
        # Verificar se os cookies têm campos obrigatórios
        dominios_validos = COOKIES_CONFIG['dominios_validos']
        for cookie in cookies:
            if not isinstance(cookie, dict):
                return False
            
            # Campos obrigatórios
            if not all(campo in cookie for campo in ['name', 'value', 'domain']):
                return False
            
            # Verificar se o domínio é válido
            if not any(dominio in cookie['domain'] for dominio in dominios_validos):
                return False
        
        return True
        
    except Exception as e:
        print(f'[COOKIES] ❌ Erro ao validar cookies: {e}')
        return False

def limpar_cookies(caminho='cookies_sisbajud.json'):
    """
    Remove arquivo de cookies
    
    Args:
        caminho: Caminho do arquivo de cookies
    """
    try:
        if os.path.exists(caminho):
            os.remove(caminho)
            print(f'[COOKIES] ✅ Arquivo de cookies removido: {caminho}')
        else:
            print(f'[COOKIES] ⚠️ Arquivo de cookies não existe: {caminho}')
            
    except Exception as e:
        print(f'[COOKIES] ❌ Erro ao remover cookies: {e}')

def obter_info_cookies(caminho='cookies_sisbajud.json'):
    """
    Obtém informações sobre os cookies salvos
    
    Args:
        caminho: Caminho do arquivo de cookies
        
    Returns:
        dict: Informações dos cookies
    """
    if not os.path.exists(caminho):
        return {'existe': False, 'total': 0, 'dominios': []}
    
    try:
        with open(caminho, 'r', encoding='utf-8') as f:
            cookies = json.load(f)
        
        dominios = list(set(cookie.get('domain', '') for cookie in cookies))
        
        return {
            'existe': True,
            'total': len(cookies),
            'dominios': dominios,
            'valido': validar_cookies(caminho)
        }
        
    except Exception as e:
        print(f'[COOKIES] ❌ Erro ao obter info dos cookies: {e}')
        return {'existe': False, 'total': 0, 'dominios': [], 'erro': str(e)}

def backup_cookies(caminho='cookies_sisbajud.json'):
    """
    Cria backup dos cookies
    
    Args:
        caminho: Caminho do arquivo de cookies
        
    Returns:
        str: Caminho do backup ou None se erro
    """
    if not os.path.exists(caminho):
        print(f'[COOKIES] ⚠️ Arquivo de cookies não existe para backup: {caminho}')
        return None
    
    try:
        import shutil
        from datetime import datetime
        
        # Criar nome do backup com timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = f"{caminho}.backup_{timestamp}"
        
        shutil.copy2(caminho, backup_path)
        print(f'[COOKIES] ✅ Backup criado: {backup_path}')
        
        return backup_path
        
    except Exception as e:
        print(f'[COOKIES] ❌ Erro ao criar backup: {e}')
        return None
