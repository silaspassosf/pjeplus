# ===================== SISTEMA DE VÍNCULOS (CHAINING) =====================
# Implementação do sistema de vínculos de ações automatizadas em Python
# Baseado nas funções JavaScript storage_vinculo(), conferirVinculoEspecial() e monitorFim()

import threading
import queue
import copy

# Armazenamento global dos vínculos (equivalente ao browser storage)
vinculo_storage = {
    'tempBt': [],  # Equivalente ao tempBt do JS
    'tempAAEspecial': [],  # Equivalente ao tempAAEspecial do JS
    'AALote': ''  # Equivalente ao AALote do JS
}

# Fila para execução sequencial de vínculos
fila_execucao = queue.Queue()

def storage_vinculo(param):
    """
    Equivalente à função storage_vinculo() do JavaScript.
    Processa e armazena vínculos para execução sequencial.
    
    Args:
        param: string com formato "tipo1|botao1,tipo2|botao2,Nenhum" ou "Nenhum"
    """
    print(f'[VINCULO] storage_vinculo({param})')
    
    # Chama conferirVinculoEspecial para processar vínculos em cadeia
    param_processado = conferir_vinculo_especial(param)
    
    # Armazena o vínculo processado
    vinculo_storage['tempBt'] = ['vinculo', param_processado]
    
    return param_processado

def conferir_vinculo_especial(aa_vinculo='Nenhum'):
    """
    Equivalente à função conferirVinculoEspecial() do JavaScript.
    Verifica e processa vínculos especiais em cadeia.
    
    Args:
        aa_vinculo: string com vínculos no formato "tipo1|botao1,tipo2|botao2,Nenhum"
    
    Returns:
        str: próximo vínculo a ser executado
    """
    print(f'[VINCULO] conferirVinculoEspecial({aa_vinculo})')
    
    temp_aa_especial = vinculo_storage.get('tempAAEspecial', [])
    
    # Se tempAAEspecial está vazio ou é 'Nenhum', usa o vínculo atual
    if not temp_aa_especial or temp_aa_especial == 'Nenhum':
        aa_vinculo_final = aa_vinculo
    else:
        aa_vinculo_final = temp_aa_especial
    
    # Se tem vínculos múltiplos, processa como array
    if isinstance(aa_vinculo_final, str) and ',' in aa_vinculo_final:
        temp_aa_especial = aa_vinculo_final.split(',')
    elif isinstance(aa_vinculo_final, list):
        temp_aa_especial = aa_vinculo_final.copy()
    else:
        temp_aa_especial = [aa_vinculo_final] if aa_vinculo_final != 'Nenhum' else []
    
    # Remove o primeiro item da lista (próximo a executar)
    if temp_aa_especial:
        proximo_vinculo = temp_aa_especial.pop(0)
        
        print(f'[VINCULO] Próximo vínculo: {proximo_vinculo}')
        print(f'[VINCULO] AAEspecial remanescente: {temp_aa_especial}')
        
        # Atualiza o storage com os vínculos remanescentes
        vinculo_storage['tempAAEspecial'] = temp_aa_especial
        
        return proximo_vinculo
    
    return 'Nenhum'

def monitor_fim(param=''):
    """
    Equivalente à função monitorFim() do JavaScript.
    Monitora o fim da execução e processa próximos vínculos na cadeia.
    
    Args:
        param: vínculo atual ou string vazia
    """
    if not param:
        param = vinculo_storage.get('tempAAEspecial', 'Nenhum')
        if isinstance(param, list):
            param = ','.join(param) if param else 'Nenhum'
    
    print(f'[VINCULO] monitorFim({param})')
    
    if param and param != 'Nenhum':
        # Se tem vínculo, adiciona à fila de execução
        storage_vinculo(param)
        fila_execucao.put(param)
    else:
        # Se não tem vínculo, verifica se é execução em lote
        aa_lote = vinculo_storage.get('AALote', '')
        if aa_lote:
            print('[VINCULO] Finalizando execução em lote')
            vinculo_storage['AALote'] = ''

def obter_vinculos_descendentes(aa_pai, vinculo_atual):
    """
    Equivalente à função obterVinculosDescendentes() do JavaScript.
    Processa vínculos descendentes para evitar loops infinitos.
    
    Args:
        aa_pai: nome da ação automatizada pai
        vinculo_atual: vínculo atual no formato "tipo|botao"
    
    Returns:
        str: vínculos processados
    """
    print(f'[VINCULO] obterVinculosDescendentes({aa_pai}, {vinculo_atual})')
    
    if 'Nenhum' in str(vinculo_atual):
        return vinculo_atual
    
    # Lista para rastrear vínculos já processados (evitar loops)
    vinculos_processados = []
    
    def processar_vinculo_recursivo(vinculo):
        if not vinculo or vinculo == 'Nenhum':
            return 'Nenhum'
        
        # Verifica se é um loop (ação chama ela mesma)
        if vinculo == aa_pai:
            print(f'[VINCULO] Interrompeu loop na AA {vinculo}')
            return 'Nenhum'
        
        # Verifica se já foi processado (evitar loops)
        if vinculo in vinculos_processados:
            print(f'[VINCULO] Interrompeu loop circular na AA {vinculo}')
            return 'Nenhum'
        
        vinculos_processados.append(vinculo)
        return vinculo
    
    # Processa o vínculo atual
    resultado = processar_vinculo_recursivo(vinculo_atual)
    
    return resultado

def executar_autogigs(driver, config, callback_fim=None):
    """
    Função principal para executar ações automatizadas com suporte a vínculos.
    
    Args:
        driver: instância do Selenium WebDriver
        config: configuração da ação automatizada
        callback_fim: função callback para chamar ao final (opcional)
    """
    try:
        nm_botao = config.get('nm_botao', '')
        vinculo = config.get('vinculo', 'Nenhum')
        
        print(f'[AUTOGIGS] Executando: {nm_botao} (vínculo: {vinculo})')
        
        # Executa a ação automatizada conforme o tipo
        sucesso = executar_acao_por_tipo(driver, config)
        
        if sucesso:
            print(f'[AUTOGIGS] Ação {nm_botao} executada com sucesso')
            
            # Chama callback se fornecido
            if callback_fim:
                callback_fim(driver, config)
            
            # Processa vínculos descendentes
            if vinculo and vinculo != 'Nenhum':
                vinculos_processados = obter_vinculos_descendentes(nm_botao, vinculo)
                monitor_fim(vinculos_processados)
        else:
            print(f'[AUTOGIGS][ERRO] Falha na execução de {nm_botao}')
            
    except Exception as e:
        print(f'[AUTOGIGS][ERRO] Exceção durante execução: {e}')

def executar_acao_por_tipo(driver, config):
    """
    Executa ação automatizada baseada no tipo.
    
    Args:
        driver: instância do Selenium WebDriver
        config: configuração da ação
    
    Returns:
        bool: True se executou com sucesso, False caso contrário
    """
    tipo = config.get('tipo', '')
    
    if tipo == 'chip':
        return executar_chip(driver, config)
    elif tipo == 'comentario':
        return executar_comentario(driver, config)
    elif tipo == 'lembrete':
        return executar_lembrete(driver, config)
    elif tipo == 'prazo':
        return executar_prazo(driver, config)
    elif tipo == 'preparo':
        return executar_preparo(driver, config)
    else:
        print(f'[AUTOGIGS][ERRO] Tipo não reconhecido: {tipo}')
        return False

def executar_chip(driver, config):
    """Executa ação de chip"""
    try:
        tipo_atividade = config.get('tipo_atividade', '')
        print(f'[AUTOGIGS][CHIP] Adicionando chip: {tipo_atividade}')
        
        # Implementar lógica de chip aqui
        # ...
        
        return True
    except Exception as e:
        print(f'[AUTOGIGS][CHIP][ERRO] {e}')
        return False

def executar_comentario(driver, config):
    """Executa ação de comentário"""
    try:
        observacao = config.get('observacao', '')
        prazo_visibilidade = config.get('prazo', '')
        print(f'[AUTOGIGS][COMENTARIO] Adicionando comentário: {observacao}')
        
        # Implementar lógica de comentário aqui
        # ...
        
        return True
    except Exception as e:
        print(f'[AUTOGIGS][COMENTARIO][ERRO] {e}')
        return False

def executar_lembrete(driver, config):
    """Executa ação de lembrete"""
    try:
        tipo_atividade = config.get('tipo_atividade', '')
        observacao = config.get('observacao', '')
        print(f'[AUTOGIGS][LEMBRETE] Criando lembrete: {tipo_atividade} - {observacao}')
        
        # Implementar lógica de lembrete aqui
        # ...
        
        return True
    except Exception as e:
        print(f'[AUTOGIGS][LEMBRETE][ERRO] {e}')
        return False

def executar_prazo(driver, config):
    """Executa ação de prazo"""
    try:
        prazo = config.get('prazo', '')
        observacao = config.get('observacao', '')
        print(f'[AUTOGIGS][PRAZO] Criando prazo: {prazo} dias - {observacao}')
        
        # Implementar lógica de prazo aqui usando criar_gigs
        # ...
        
        return True
    except Exception as e:
        print(f'[AUTOGIGS][PRAZO][ERRO] {e}')
        return False

def executar_preparo(driver, config):
    """Executa ação de preparo"""
    try:
        observacao = config.get('observacao', '')
        print(f'[AUTOGIGS][PREPARO] Criando atividade de preparo: {observacao}')
        
        # Implementar lógica de preparo aqui
        # ...
        
        return True
    except Exception as e:
        print(f'[AUTOGIGS][PREPARO][ERRO] {e}')
        return False

def processar_fila_vinculos(driver):
    """
    Processa fila de vínculos em thread separada.
    Equivalente ao comportamento assíncrono do JavaScript.
    
    Args:
        driver: instância do Selenium WebDriver
    """
    while True:
        try:
            # Aguarda próximo vínculo na fila (timeout de 1 segundo)
            proximo_vinculo = fila_execucao.get(timeout=1)
            
            if proximo_vinculo and proximo_vinculo != 'Nenhum':
                # Parseia o vínculo no formato "tipo|botao"
                if '|' in proximo_vinculo:
                    tipo, botao = proximo_vinculo.split('|', 1)
                    
                    # Cria configuração para execução
                    config_vinculo = {
                        'nm_botao': botao,
                        'tipo': tipo.lower(),
                        'vinculo': 'Nenhum'  # Para evitar loops infinitos
                    }
                    
                    # Executa a ação vinculada
                    executar_autogigs(driver, config_vinculo)
            
            fila_execucao.task_done()
            
        except queue.Empty:
            # Timeout na fila, continua aguardando
            continue
        except Exception as e:
            print(f'[VINCULO][ERRO] Falha no processamento da fila: {e}')

def iniciar_processador_vinculos(driver):
    """
    Inicia thread para processamento de vínculos em background.
    
    Args:
        driver: instância do Selenium WebDriver
    """
    thread_vinculos = threading.Thread(
        target=processar_fila_vinculos, 
        args=(driver,), 
        daemon=True
    )
    thread_vinculos.start()
    print('[VINCULO] Processador de vínculos iniciado')

def limpar_storage_vinculos():
    """
    Limpa o storage de vínculos.
    Equivalente à função storage_limpar() do JavaScript.
    """
    global vinculo_storage
    vinculo_storage = {
        'tempBt': [],
        'tempAAEspecial': [],
        'AALote': ''
    }
    
    # Limpa também a fila
    while not fila_execucao.empty():
        try:
            fila_execucao.get_nowait()
        except queue.Empty:
            break
    
    print('[VINCULO] Storage de vínculos limpo')

# ===================== EXEMPLO DE USO DO SISTEMA DE VÍNCULOS =====================

def exemplo_uso_vinculos(driver):
    """
    Exemplo de como usar o sistema de vínculos.
    """
    # Inicia o processador de vínculos
    iniciar_processador_vinculos(driver)
    
    # Configuração de ação com vínculos
    config_acao1 = {
        'nm_botao': 'Criar Prazo',
        'tipo': 'prazo',
        'prazo': '5',
        'observacao': 'Prazo inicial',
        'vinculo': 'comentario|Adicionar Comentário,chip|Status Processado,Nenhum'
    }
    
    # Executa primeira ação (que disparará as outras em cadeia)
    executar_autogigs(driver, config_acao1)
    
    print('[EXEMPLO] Sistema de vínculos iniciado - ações serão executadas em sequência')

# ===================== FIM DO SISTEMA DE VÍNCULOS =====================
