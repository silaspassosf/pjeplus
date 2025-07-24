#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SISB_MODULOS/CONFIG.PY
Configurações e constantes do sistema SISBAJUD/BACEN
Extraído do bacen.py original
"""

# ===================== CONFIGURAÇÕES PRINCIPAIS =====================
CONFIG = {
    'cor_bloqueio_positivo': '#32cd32',
    'cor_bloqueio_negativo': '#ff6347',
    'acao_automatica': 'transferir',
    'banco_preferido': 'Banco do Brasil',
    'agencia_preferida': '5905',
    'teimosinha': '60',
    'nome_default': '',
    'documento_default': '',
    'valor_default': '',
    'juiz_default': 'OTAVIO AUGUSTO MACHADO DE OLIVEIRA',
    'vara_default': '3006',
}

# ===================== VARIÁVEIS GLOBAIS =====================
processo_dados_extraidos = None
login_ahk_executado = False

# ===================== CONFIGURAÇÕES DE DRIVERS =====================
FIREFOX_CONFIG = {
    'profile_path': r'C:\Users\Silas\AppData\Roaming\Mozilla\Firefox\Profiles\arrn673i.Sisb',
    'firefox_binary': r'C:\Program Files\Firefox Developer Edition\firefox.exe',
    'geckodriver_path': r'd:\PjePlus\geckodriver.exe',
    'implicit_wait': 10,
    'page_load_timeout': 30,
}

# ===================== CONFIGURAÇÕES DE COOKIES =====================
COOKIES_CONFIG = {
    'caminho_padrao': 'cookies_sisbajud.json',
    'dominios_validos': [
        'sisbajud.cloud.pje.jus.br',
        'sso.cloud.pje.jus.br',
        'cnj.jus.br'
    ],
    'timeout_carregamento': 3,
}

# ===================== CONFIGURAÇÕES DE URLS =====================
URLS = {
    'sisbajud_base': 'https://sisbajud.cnj.jus.br/',
    'sisbajud_teimosinha': 'https://sisbajud.cnj.jus.br/teimosinha/',
    'sso_pje': 'https://sso.cloud.pje.jus.br',
    'login_pje': 'https://sso.cloud.pje.jus.br/auth/realms/pje/protocol/openid-connect/auth',
}

# ===================== CONFIGURAÇÕES DE TIMEOUTS =====================
TIMEOUTS = {
    'implicit_wait': 10,
    'page_load': 30,
    'script_timeout': 15,
    'aguardar_elemento': 10,
    'aguardar_login': 300,  # 5 minutos
    'entre_acoes': 1,
    'entre_cliques': 0.5,
    'estabilizacao': 3,
}

# ===================== CONFIGURAÇÕES DE ARQUIVOS =====================
ARQUIVOS = {
    'dados_processo': 'dadosatuais.json',
    'cookies_sisbajud': 'cookies_sisbajud.json',
    'log_automacao': 'pje_automacao.log',
    'backup_selenium': '_backup_selenium_pje_trt2',
}

# ===================== FUNÇÕES DE CONFIGURAÇÃO =====================
def obter_config(chave, valor_padrao=None):
    """Obtém um valor de configuração"""
    return CONFIG.get(chave, valor_padrao)

def definir_config(chave, valor):
    """Define um valor de configuração"""
    CONFIG[chave] = valor

def obter_url(chave):
    """Obtém uma URL configurada"""
    return URLS.get(chave, '')

def obter_timeout(chave):
    """Obtém um timeout configurado"""
    return TIMEOUTS.get(chave, 10)

def obter_arquivo(chave):
    """Obtém um caminho de arquivo configurado"""
    return ARQUIVOS.get(chave, '')

def validar_configuracoes():
    """Valida se as configurações estão corretas"""
    import os
    
    erros = []
    
    # Validar caminhos de arquivos
    if not os.path.exists(FIREFOX_CONFIG['geckodriver_path']):
        erros.append(f"GeckoDriver não encontrado: {FIREFOX_CONFIG['geckodriver_path']}")
    
    if not os.path.exists(FIREFOX_CONFIG['firefox_binary']):
        erros.append(f"Firefox não encontrado: {FIREFOX_CONFIG['firefox_binary']}")
    
    # Validar configurações obrigatórias
    obrigatorias = ['juiz_default', 'vara_default']
    for chave in obrigatorias:
        if not CONFIG.get(chave):
            erros.append(f"Configuração obrigatória não definida: {chave}")
    
    if erros:
        print('❌ Erros de configuração encontrados:')
        for erro in erros:
            print(f'  - {erro}')
        return False
    
    return True
