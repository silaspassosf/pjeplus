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

# ===================== CONFIGURAÇÕES DE INTERFACE =====================
INTERFACE = {
    'cores': {
        'primaria': '#1976d2',
        'secundaria': '#fff',
        'sucesso': '#4caf50',
        'erro': '#f44336',
        'aviso': '#ff9800',
        'bloqueio_positivo': '#32cd32',
        'bloqueio_negativo': '#ff6347',
    },
    'estilos': {
        'container': 'position:fixed;top:60px;right:20px;z-index:9999;background:#1976d2;padding:12px;border-radius:12px;box-shadow:0 4px 12px rgba(25,118,210,0.3);',
        'botao': 'padding:10px 20px;font-size:14px;font-weight:bold;cursor:pointer;background:#fff;color:#1976d2;border:none;border-radius:8px;box-shadow:0 2px 4px rgba(0,0,0,0.1);transition:all 0.3s ease;',
        'menu': 'position:fixed;top:10px;right:10px;z-index:99999;background:#2196f3;padding:15px;border-radius:10px;box-shadow:0 4px 20px rgba(0,0,0,0.3);',
    },
    'animacoes': {
        'hover_scale': 'scale(1.05)',
        'hover_shadow': '0 4px 8px rgba(0,0,0,0.2)',
        'normal_scale': 'scale(1)',
        'normal_shadow': '0 2px 4px rgba(0,0,0,0.1)',
    }
}

# ===================== CONFIGURAÇÕES DE SELETORES =====================
SELETORES = {
    'pje': {
        'botao_sisbajud': '#btn_abrir_sisbajud',
        'container_sisbajud': '#sisbajud_btn_container',
    },
    'sisbajud': {
        'login_form': 'form[name="loginForm"]',
        'usuario_input': '#username',
        'senha_input': '#password',
        'login_button': '#kc-login',
        'tabela_teimosinha': '.table-responsive table',
        'linhas_tabela': '.table-responsive table tbody tr',
        'menu_kaizen': '#menu_kaizen_sisbajud',
        'botao_nova_minuta': '#btn_nova_minuta',
        'botao_consultar_minuta': '#btn_consultar_minuta',
        'botao_consultar_teimosinha': '#btn_consultar_teimosinha',
        'botao_processar_bloqueios': '#btn_processar_bloqueios',
    },
    'formularios': {
        'juiz_solicitante': '#juiz_solicitante',
        'vara_juizo': '#vara_juizo',
        'numero_processo': '#numero_processo',
        'tipo_acao': '#tipo_acao',
        'cpf_autor': '#cpf_autor',
        'nome_autor': '#nome_autor',
        'teimosinha_input': '#teimosinha',
        'endereco_opcoes': '#endereco_opcoes',
    }
}

# ===================== CONFIGURAÇÕES DE MENSAGENS =====================
MENSAGENS = {
    'sucesso': {
        'driver_criado': '✅ Driver criado com sucesso!',
        'login_realizado': '✅ Login realizado com sucesso!',
        'cookies_salvos': '✅ Cookies salvos com sucesso!',
        'dados_extraidos': '✅ Dados extraídos com sucesso!',
        'minuta_criada': '✅ Minuta criada com sucesso!',
        'bloqueios_processados': '✅ Bloqueios processados com sucesso!',
    },
    'erro': {
        'driver_falhou': '❌ Falha ao criar driver',
        'login_falhou': '❌ Falha no login',
        'cookies_falhou': '❌ Falha ao carregar cookies',
        'dados_falhou': '❌ Falha ao extrair dados',
        'minuta_falhou': '❌ Falha ao criar minuta',
        'bloqueios_falhou': '❌ Falha ao processar bloqueios',
    },
    'aviso': {
        'cookies_inexistentes': '⚠️ Arquivo de cookies não encontrado',
        'primeiro_acesso': '⚠️ Primeiro acesso detectado',
        'login_manual': '⚠️ Login manual necessário',
        'dados_indisponiveis': '⚠️ Dados do processo indisponíveis',
    },
    'info': {
        'iniciando': '🚀 Iniciando automação...',
        'carregando': '🔄 Carregando...',
        'processando': '⚙️ Processando...',
        'finalizando': '🏁 Finalizando...',
        'aguardando': '⏳ Aguardando...',
    }
}

# ===================== FUNÇÕES DE CONFIGURAÇÃO =====================
def obter_config(chave, valor_padrao=None):
    """
    Obtém um valor de configuração
    
    Args:
        chave (str): Chave da configuração
        valor_padrao: Valor padrão se a chave não existir
        
    Returns:
        Valor da configuração ou valor padrão
    """
    return CONFIG.get(chave, valor_padrao)

def definir_config(chave, valor):
    """
    Define um valor de configuração
    
    Args:
        chave (str): Chave da configuração
        valor: Valor a ser definido
    """
    CONFIG[chave] = valor

def obter_url(chave):
    """
    Obtém uma URL configurada
    
    Args:
        chave (str): Chave da URL
        
    Returns:
        str: URL configurada
    """
    return URLS.get(chave, '')

def obter_timeout(chave):
    """
    Obtém um timeout configurado
    
    Args:
        chave (str): Chave do timeout
        
    Returns:
        int: Timeout em segundos
    """
    return TIMEOUTS.get(chave, 10)

def obter_seletor(categoria, chave):
    """
    Obtém um seletor CSS configurado
    
    Args:
        categoria (str): Categoria do seletor (pje, sisbajud, formularios)
        chave (str): Chave do seletor
        
    Returns:
        str: Seletor CSS
    """
    return SELETORES.get(categoria, {}).get(chave, '')

def obter_mensagem(categoria, chave):
    """
    Obtém uma mensagem configurada
    
    Args:
        categoria (str): Categoria da mensagem (sucesso, erro, aviso, info)
        chave (str): Chave da mensagem
        
    Returns:
        str: Mensagem configurada
    """
    return MENSAGENS.get(categoria, {}).get(chave, '')

def obter_cor(chave):
    """
    Obtém uma cor configurada
    
    Args:
        chave (str): Chave da cor
        
    Returns:
        str: Código da cor
    """
    return INTERFACE.get('cores', {}).get(chave, '#000000')

def obter_estilo(chave):
    """
    Obtém um estilo CSS configurado
    
    Args:
        chave (str): Chave do estilo
        
    Returns:
        str: Estilo CSS
    """
    return INTERFACE.get('estilos', {}).get(chave, '')

def editar_configuracoes():
    """
    Interface para editar configurações interativamente
    """
    print('🔧 Editor de Configurações')
    print('=' * 30)
    
    configuracoes_editaveis = [
        'juiz_default',
        'vara_default',
        'banco_preferido',
        'agencia_preferida',
        'teimosinha',
        'nome_default',
        'documento_default',
        'valor_default',
    ]
    
    for i, chave in enumerate(configuracoes_editaveis, 1):
        valor_atual = CONFIG.get(chave, '')
        print(f'{i}. {chave}: {valor_atual}')
    
    print('0. Sair')
    print()
    
    try:
        opcao = int(input('Escolha uma opção para editar: '))
        
        if opcao == 0:
            return
        
        if 1 <= opcao <= len(configuracoes_editaveis):
            chave = configuracoes_editaveis[opcao - 1]
            valor_atual = CONFIG.get(chave, '')
            
            print(f'Valor atual de {chave}: {valor_atual}')
            novo_valor = input(f'Digite o novo valor para {chave}: ').strip()
            
            if novo_valor:
                CONFIG[chave] = novo_valor
                print(f'✅ {chave} alterado para: {novo_valor}')
            else:
                print('❌ Valor não alterado.')
        else:
            print('❌ Opção inválida.')
            
    except ValueError:
        print('❌ Entrada inválida.')
    except KeyboardInterrupt:
        print('\n⏹️ Edição cancelada.')

def validar_configuracoes():
    """
    Valida se as configurações estão corretas
    
    Returns:
        bool: True se as configurações estão válidas
    """
    erros = []
    
    # Validar caminhos de arquivos
    import os
    
    if not os.path.exists(FIREFOX_CONFIG['geckodriver_path']):
        erros.append(f"GeckoDriver não encontrado: {FIREFOX_CONFIG['geckodriver_path']}")
    
    if not os.path.exists(FIREFOX_CONFIG['firefox_binary']):
        erros.append(f"Firefox não encontrado: {FIREFOX_CONFIG['firefox_binary']}")
    
    # Validar configurações obrigatórias
    obrigatorias = ['juiz_default', 'vara_default']
    for chave in obrigatorias:
        if not CONFIG.get(chave):
            erros.append(f"Configuração obrigatória não definida: {chave}")
    
    # Validar timeouts
    for chave, valor in TIMEOUTS.items():
        if not isinstance(valor, int) or valor <= 0:
            erros.append(f"Timeout inválido para {chave}: {valor}")
    
    if erros:
        print('❌ Erros de configuração encontrados:')
        for erro in erros:
            print(f'  - {erro}')
        return False
    
    print('✅ Configurações válidas!')
    return True

def exportar_configuracoes():
    """
    Exporta as configurações para um arquivo JSON
    """
    import json
    import os
    
    try:
        config_exportada = {
            'CONFIG': CONFIG,
            'FIREFOX_CONFIG': FIREFOX_CONFIG,
            'COOKIES_CONFIG': COOKIES_CONFIG,
            'URLS': URLS,
            'TIMEOUTS': TIMEOUTS,
            'ARQUIVOS': ARQUIVOS,
        }
        
        caminho_export = os.path.join(os.path.dirname(__file__), '..', 'config_sisb.json')
        
        with open(caminho_export, 'w', encoding='utf-8') as f:
            json.dump(config_exportada, f, ensure_ascii=False, indent=2)
        
        print(f'✅ Configurações exportadas para: {caminho_export}')
        
    except Exception as e:
        print(f'❌ Erro ao exportar configurações: {e}')

def importar_configuracoes():
    """
    Importa configurações de um arquivo JSON
    """
    import json
    import os
    
    try:
        caminho_import = os.path.join(os.path.dirname(__file__), '..', 'config_sisb.json')
        
        if not os.path.exists(caminho_import):
            print(f'❌ Arquivo de configuração não encontrado: {caminho_import}')
            return
        
        with open(caminho_import, 'r', encoding='utf-8') as f:
            config_importada = json.load(f)
        
        # Atualizar configurações globais
        globals().update(config_importada)
        
        print(f'✅ Configurações importadas de: {caminho_import}')
        
    except Exception as e:
        print(f'❌ Erro ao importar configurações: {e}')

# ===================== INICIALIZAÇÃO =====================
if __name__ == "__main__":
    print("📋 Configurações SISB")
    print("=" * 30)
    
    # Validar configurações na inicialização
    if validar_configuracoes():
        print("✅ Módulo de configuração pronto!")
    else:
        print("❌ Corrija os erros de configuração antes de continuar.")
