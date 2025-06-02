import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait # Added
from selenium.webdriver.support import expected_conditions as EC # Added
import time
import threading # Added for vinculos
import queue # Added for vinculos
import copy # Added for vinculos

# Armazenamento global dos vínculos (equivalente ao browser storage)
vinculo_storage = {
    'tempBt': [],  # Equivalente ao tempBt do JS
    'tempAAEspecial': [],  # Equivalente ao tempAAEspecial do JS
    'AALote': ''  # Equivalente ao AALote do JS
}

# Fila para execução sequencial de vínculos
fila_execucao = queue.Queue()

# Variáveis globais para controle de threads de vínculos
_processador_vinculos_thread = None
_parar_processador_vinculos_event = threading.Event()

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
        aa_pai: nome da ação automatizada pai (nm_botao do config da ação atual)
        vinculo_atual: string com vínculos no formato "tipo1|botao1,tipo2|botao2,Nenhum"
    
    Returns:
        str: vínculos processados e concatenados por vírgula, ou 'Nenhum'
    """
    print(f'[VINCULO] obterVinculosDescendentes({aa_pai}, {vinculo_atual})')
    
    if 'Nenhum' in str(vinculo_atual) or not vinculo_atual:
        return 'Nenhum'
    
    vinculos_processados_lista = []
    # Usar um set para rastrear os botões já processados nesta chamada específica para evitar loops diretos na lista de vínculos
    botoes_nesta_cadeia = {aa_pai} 

    vinculos_para_processar = []
    if isinstance(vinculo_atual, str):
        vinculos_para_processar = [v.strip() for v in vinculo_atual.split(',') if v.strip() and v.strip().lower() != 'nenhum']
    elif isinstance(vinculo_atual, list): # Caso já venha como lista
        vinculos_para_processar = [v.strip() for v in vinculo_atual if isinstance(v, str) and v.strip() and v.strip().lower() != 'nenhum']

    if not vinculos_para_processar:
        return 'Nenhum'

    for vinculo_item_str in vinculos_para_processar:
        if not vinculo_item_str or vinculo_item_str.lower() == 'nenhum':
            continue

        # Extrair o nome do botão do vinculo_item_str (ex: "tipo|botaoNome" -> "botaoNome")
        nome_botao_vinculo = vinculo_item_str.split('|')[-1].strip()

        # Verifica se é um loop (ação chama ela mesma ou botão já na cadeia)
        if nome_botao_vinculo == aa_pai:
            print(f'[VINCULO] Interrompeu loop direto na AA {nome_botao_vinculo} (era o aa_pai).')
            continue # Pula este vínculo, mas processa os próximos da lista
        
        if nome_botao_vinculo in botoes_nesta_cadeia:
            print(f'[VINCULO] Interrompeu loop circular na AA {nome_botao_vinculo} (já estava na cadeia de processamento atual).')
            continue # Pula este vínculo

        vinculos_processados_lista.append(vinculo_item_str)
        botoes_nesta_cadeia.add(nome_botao_vinculo) # Adiciona o botão atual à lista de processados desta chamada

    if not vinculos_processados_lista:
        return 'Nenhum'
    
    return ','.join(vinculos_processados_lista)


def executar_acao_por_tipo(driver, config):
    """
    Executa ação automatizada baseada no tipo ou seção especificada no config.
    Mapeamento baseado na análise do gigs-plugin.js onde cada seção tem suas funções específicas.
    
    Args:
        driver: instância do Selenium WebDriver
        config: configuração da ação (deve conter 'nm_botao', e idealmente 'secao' ou 'tipo' para mapeamento)
    
    Returns:
        bool: True se executou com sucesso, False caso contrário
    """
    tipo_config = config.get('tipo', '').lower() # Tipo original do botão JSON
    secao_config = config.get('secao', '') # Seção vinda do processar_fila_vinculos ou original
    nm_botao_config = config.get('nm_botao', '')

    # Prioriza a seção se já estiver definida (ex: vindo da fila de vínculos)
    secao_para_executar = secao_config

    if not secao_para_executar:
        # Mapeamento baseado na análise do JavaScript - cada seção tem mapeamento específico
        # Primeiro, busca diretamente pelo nome do botão no JSON para obter configuração completa
        for s, botoes_da_secao in botoes.items():
            for btn_json_cfg in botoes_da_secao:
                if btn_json_cfg.get('nm_botao') == nm_botao_config:
                    secao_para_executar = s
                    # Preserva o vínculo original se houver, mas atualiza outras configurações
                    vinculo_original = config.get('vinculo')
                    config.update(copy.deepcopy(btn_json_cfg))
                    if vinculo_original is not None: 
                        config['vinculo'] = vinculo_original
                    config['secao'] = s
                    break
            if secao_para_executar: 
                break
        
        # Se não encontrou pelo nome, tenta mapear pelo tipo - fallback baseado no JS
        if not secao_para_executar:
            if tipo_config in ['despacho', 'homologação de c', 'sobrest', 'sobrestamento /', 'sobrestamento', 'extinção da', 'entinção', 'bacen /', 'idpj']:
                secao_para_executar = 'aaDespacho'
            elif tipo_config in ['intimação', 'mandado', 'notificação inicial', 'edital']:
                secao_para_executar = 'aaComunicacao'
            elif tipo_config in ['prazo', 'comentario', 'lembrete']:
                secao_para_executar = 'aaAutogigs'
            elif tipo_config == 'checklist':
                secao_para_executar = 'aaChecklist'
            elif tipo_config in ['lancar movimentos', 'lançarmovimentos']:
                secao_para_executar = 'aaLancarMovimentos'
            elif tipo_config == 'movimento':
                secao_para_executar = 'aaMovimento'
            elif tipo_config == 'variados':
                secao_para_executar = 'aaVariados'
    
    if not secao_para_executar:
        print(f'[AUTOGIGS][ERRO] Seção não reconhecida ou não mapeada para botão: {nm_botao_config} (tipo: {tipo_config})')
        return False

    print(f"[AUTOGIGS] Executando ação: Botão='{nm_botao_config}', Tipo Original='{tipo_config}', Seção Target='{secao_para_executar}'")

    # Mapeamento de seções para funções baseado na estrutura do JavaScript
    # Cada seção corresponde a uma função específica como no gigs-plugin.js
    try:
        if secao_para_executar == 'aaDespacho': 
            return acao_bt_aaDespacho_selenium(driver, config)
        elif secao_para_executar == 'aaComunicacao': 
            return acao_bt_apec_selenium(driver, config)
        elif secao_para_executar == 'aaAnexar': 
            return acao_bt_anexar_selenium(driver, config)
        elif secao_para_executar == 'aaAutogigs': 
            return acao_bt_aaAutogigs_selenium(driver, config)
        elif secao_para_executar == 'aaChecklist': 
            return acao_bt_aaChecklist_selenium(driver, config)
        elif secao_para_executar == 'aaLancarMovimentos': 
            return acao_bt_aaLancarMovimentos_selenium(driver, config)
        elif secao_para_executar == 'aaMovimento': 
            return acao_bt_aaMovimento_selenium(driver, config)
        elif secao_para_executar == 'aaVariados': 
            return acao_bt_aaVariados_selenium(driver, config)
        else:
            print(f'[AUTOGIGS][ERRO] Seção \'{secao_para_executar}\' não possui função de execução implementada.')
            return False
    except Exception as e:
        print(f'[AUTOGIGS][ERRO] Exceção ao executar função da seção {secao_para_executar}: {e}')
        import traceback
        traceback.print_exc()
        return False


def executar_autogigs(driver, config, callback_fim=None):
    """
    Função principal para executar ações automatizadas com suporte a vínculos.
    Adaptada de vinculos.js e integrada com fluxos.py.
    
    Args:
        driver: instância do Selenium WebDriver.
        config: dict de configuração da ação, vindo do JSON `botoes` ou construído para um vínculo.
                Deve conter 'nm_botao'. Pode conter 'vinculo' para a próxima ação.
        callback_fim: função callback opcional.
    """
    nm_botao_atual = config.get('nm_botao', 'Desconhecido')
    vinculo_da_acao_atual = config.get('vinculo', 'Nenhum') # Vínculo definido NO BOTÃO ATUAL para a PRÓXIMA ação.

    print(f"[AUTOGIGS] Iniciando execução de: '{nm_botao_atual}'. Vínculo definido nesta ação: '{vinculo_da_acao_atual}'")

    try:
        sucesso = executar_acao_por_tipo(driver, config) # Passa o config completo
        
        if sucesso:
            print(f"[AUTOGIGS] Ação '{nm_botao_atual}' executada com sucesso.")
            if callback_fim:
                callback_fim(driver, config)
            
            # Se a ação atual tem um vínculo definido, processa-o.
            if vinculo_da_acao_atual and vinculo_da_acao_atual.lower() != 'nenhum':
                print(f"[AUTOGIGS] Ação '{nm_botao_atual}' possui vínculo: '{vinculo_da_acao_atual}'. Processando...")
                # `nm_botao_atual` é o aa_pai para os vínculos definidos em `vinculo_da_acao_atual`
                vinculos_para_proxima_etapa = obter_vinculos_descendentes(nm_botao_atual, vinculo_da_acao_atual)
                
                if vinculos_para_proxima_etapa and vinculos_para_proxima_etapa.lower() != 'nenhum':
                    print(f"[AUTOGIGS] Vínculos descendentes processados para '{nm_botao_atual}': '{vinculos_para_proxima_etapa}'. Enviando para monitor_fim.")
                    monitor_fim(vinculos_para_proxima_etapa) # monitor_fim colocará na fila
                else:
                    print(f"[AUTOGIGS] Nenhum vínculo válido restante após obter_vinculos_descendentes para '{nm_botao_atual}'. Chamando monitor_fim com 'Nenhum'.")
                    monitor_fim('Nenhum') # Finaliza cadeia/lote se não houver mais vínculos válidos
            else:
                print(f"[AUTOGIGS] Ação '{nm_botao_atual}' não possui vínculos ou o vínculo é 'Nenhum'. Chamando monitor_fim com 'Nenhum'.")
                monitor_fim('Nenhum') # Se não há vínculos definidos nesta ação, finaliza cadeia/lote
        else:
            print(f"[AUTOGIGS][ERRO] Falha na execução de '{nm_botao_atual}'. Cadeia de vínculos interrompida.")
            monitor_fim('Nenhum') # Interrompe a cadeia e finaliza lote se aplicável
            
    except Exception as e:
        print(f"[AUTOGIGS][ERRO GRAVE] Exceção durante execução de '{nm_botao_atual}': {e}")
        import traceback
        traceback.print_exc()
        monitor_fim('Nenhum') # Interrompe e finaliza em caso de exceção grave


def processar_fila_vinculos(driver):
    """
    Processa a fila de execução de vínculos em uma thread separada.
    Baseado na lógica do logStorageChange do gigs-plugin.js
    """
    print('[VINCULO][FILA] Thread processar_fila_vinculos iniciada.')
    while not _parar_processador_vinculos_event.is_set():
        try:
            # Pega o próximo item da fila. `get` bloqueia até um item estar disponível ou timeout.
            # O item na fila é uma string de vínculos, ex: "tipo1|botaoA,tipo2|botaoB"
            # ou um único "tipo|botao" ou apenas "botaoNome"
            vinculos_da_fila_str = fila_execucao.get(timeout=1) 

            if not vinculos_da_fila_str or vinculos_da_fila_str.lower() == 'nenhum':
                if vinculos_da_fila_str and vinculos_da_fila_str.lower() == 'nenhum':
                     print("[VINCULO][FILA] 'Nenhum' recebido explicitamente na fila. Fim de uma cadeia.")
                # Se AALote estava ativo, monitor_fim já o teria limpado.
                fila_execucao.task_done()
                continue # Volta para o início do loop para pegar o próximo item ou verificar _parar_processador_vinculos_event

            print(f"[VINCULO][FILA] Processando da fila: '{vinculos_da_fila_str}'")

            # Baseado na análise do JS: processamento sequencial, um vínculo por vez
            # A string pode conter múltiplos vínculos separados por vírgula, mas processa apenas o primeiro
            # O restante fica armazenado em tempAAEspecial para processamento posterior
            vinculo_para_processar = storage_vinculo(vinculos_da_fila_str)
            
            if not vinculo_para_processar or vinculo_para_processar.lower() == 'nenhum':
                print(f"[VINCULO][FILA] storage_vinculo retornou 'Nenhum' para: '{vinculos_da_fila_str}'. Finalizando cadeia.")
                fila_execucao.task_done()
                continue

            # Extrair tipo e nome do botão do vínculo atual
            # Formato esperado: "tipo|nome_botao" ou apenas "nome_botao"
            if '|' in vinculo_para_processar:
                tipo_vinculo, nome_botao_vinculo = vinculo_para_processar.split('|', 1)
                tipo_vinculo = tipo_vinculo.strip()
                nome_botao_vinculo = nome_botao_vinculo.strip()
            else:
                tipo_vinculo = ''
                nome_botao_vinculo = vinculo_para_processar.strip()

            print(f"[VINCULO][FILA] Extraído - Tipo: '{tipo_vinculo}', Botão: '{nome_botao_vinculo}'")

            # Buscar configuração do botão no JSON - similar ao JavaScript que busca por nome
            config_vinculo = None
            secao_vinculo = None
            
            # Busca em todas as seções para encontrar o botão
            for secao, botoes_da_secao in botoes.items():
                for btn_cfg in botoes_da_secao:
                    if btn_cfg.get('nm_botao') == nome_botao_vinculo:
                        config_vinculo = copy.deepcopy(btn_cfg)
                        secao_vinculo = secao
                        break
                if config_vinculo:
                    break

            # Se não encontrou configuração específica, cria uma baseada no tipo
            if not config_vinculo:
                print(f"[VINCULO][FILA] Configuração não encontrada para botão '{nome_botao_vinculo}'. Criando configuração baseada no tipo '{tipo_vinculo}'.")
                config_vinculo = {
                    'nm_botao': nome_botao_vinculo,
                    'tipo': tipo_vinculo,
                    'vinculo': 'Nenhum'  # Vínculos próprios do botão serão tratados separadamente
                }
                
                # Mapeamento de tipo para seção baseado na análise do JS
                if tipo_vinculo.lower() in ['despacho', 'homologação de c', 'sobrest', 'extinção da', 'bacen /', 'idpj']:
                    secao_vinculo = 'aaDespacho'
                elif tipo_vinculo.lower() in ['intimação', 'mandado', 'notificação inicial', 'edital']:
                    secao_vinculo = 'aaComunicacao'
                elif tipo_vinculo.lower() in ['prazo', 'comentario', 'lembrete']:
                    secao_vinculo = 'aaAutogigs'
                elif tipo_vinculo.lower() == 'anexar':
                    secao_vinculo = 'aaAnexar'
                elif tipo_vinculo.lower() == 'autogigs':
                    secao_vinculo = 'aaAutogigs'
                else:
                    print(f"[VINCULO][FILA][ERRO] Tipo '{tipo_vinculo}' não mapeado para nenhuma seção conhecida.")
                    fila_execucao.task_done()
                    continue

            if secao_vinculo:
                config_vinculo['secao'] = secao_vinculo

            print(f"[VINCULO][FILA] Executando vínculo: Seção='{secao_vinculo}', Botão='{nome_botao_vinculo}', Tipo='{tipo_vinculo}'")

            # Executa a ação do vínculo - similar ao acao_vinculo do JS
            try:
                # Adiciona delay para simular velocidade de interação do JS (let velocidade = preferencias.maisPje_velocidade_interacao + 500;)
                time.sleep(0.5)  # 500ms base + tempo de interação
                
                sucesso = executar_acao_por_tipo(driver, config_vinculo)
                
                if sucesso:
                    print(f"[VINCULO][FILA] Vínculo '{nome_botao_vinculo}' executado com sucesso.")
                    
                    # Verifica se há mais vínculos pendentes em tempAAEspecial
                    # Baseado na lógica do JS que verifica preferencias.tempAAEspecial
                    vinculos_pendentes = conferir_vinculo_especial()
                    
                    if vinculos_pendentes and vinculos_pendentes.lower() != 'nenhum':
                        print(f"[VINCULO][FILA] Vínculos pendentes encontrados: '{vinculos_pendentes}'. Continuando cadeia.")
                        # Coloca os vínculos pendentes na fila para processamento
                        fila_execucao.put(vinculos_pendentes)
                    else:
                        print(f"[VINCULO][FILA] Não há mais vínculos pendentes. Verificando AALote.")
                        # Verifica se há itens no lote AALote - similar ao JS
                        if vinculo_storage.get('AALote'):
                            print(f"[VINCULO][FILA] AALote contém itens. Continuando processamento em lote.")
                            # AALote será processado pelo monitor_fim quando necessário
                        else:
                            print(f"[VINCULO][FILA] AALote vazio. Finalizando processamento.")
                else:
                    print(f"[VINCULO][FILA][ERRO] Falha na execução do vínculo '{nome_botao_vinculo}'. Interrompendo cadeia.")
                    # Limpa vínculos pendentes em caso de erro
                    vinculo_storage['tempAAEspecial'] = []
                    
            except Exception as e:
                print(f"[VINCULO][FILA][ERRO] Exceção durante execução do vínculo '{nome_botao_vinculo}': {e}")
                import traceback
                traceback.print_exc()
                # Limpa vínculos pendentes em caso de exceção
                vinculo_storage['tempAAEspecial'] = []

            fila_execucao.task_done()
            
        except queue.Empty:
            # Timeout na fila - continua o loop para verificar _parar_processador_vinculos_event
            continue
        except Exception as e:
            print(f"[VINCULO][FILA][ERRO GRAVE] Exceção não tratada: {e}")
            import traceback
            traceback.print_exc()
            # Continua executando mesmo com erro grave
            fila_execucao.task_done()

    print('[VINCULO][FILA] Thread processar_fila_vinculos finalizada.')
    # Portanto, vinculos_da_fila_str DEVE ser UM ÚNICO comando "tipo|botao" ou "botao".

    proximo_item_para_executar = vinculos_da_fila_str # Deveria ser um único item aqui.

    partes = proximo_item_para_executar.split('|', 1)
    tipo_vinculo_item = None
    nm_botao_vinculo_item = ''

    if len(partes) == 2:
        tipo_vinculo_item = partes[0].lower().strip()
        nm_botao_vinculo_item = partes[1].strip()
    else:
        nm_botao_vinculo_item = partes[0].strip()
    
    print(f"[VINCULO][FILA] Próximo item para executar: Tipo='{tipo_vinculo_item}', Botão='{nm_botao_vinculo_item}'")

    config_para_proxima_acao = None
    secao_identificada = None

    # Busca a configuração completa do botão no JSON `botoes`
    for secao_json, lista_botoes_json in botoes.items():
        for botao_cfg_original_json in lista_botoes_json:
            if botao_cfg_original_json.get('nm_botao') == nm_botao_vinculo_item:
                # Verificação opcional de tipo para desambiguação
                # Se tipo_vinculo_item existe E (tipo no JSON é diferente E seção não corresponde ao tipo_vinculo_item)
                # pode ser um problema. Mas priorizamos o nome do botão.
                if tipo_vinculo_item and \
                   botao_cfg_original_json.get('tipo','').lower() != tipo_vinculo_item and \
                   not secao_json.lower().replace('aa','').startswith(tipo_vinculo_item):
                    print(f"[VINCULO][FILA][AVISO] Tipo do vínculo ('{tipo_vinculo_item}') diverge do tipo no JSON ('{botao_cfg_original_json.get('tipo')}') para o botão '{nm_botao_vinculo_item}'. Usando config do JSON.")
                
                config_para_proxima_acao = copy.deepcopy(botao_cfg_original_json)
                secao_identificada = secao_json
                break
        if config_para_proxima_acao: break
    
    if config_para_proxima_acao:
        # Garante que a seção está no config para executar_acao_por_tipo
        config_para_proxima_acao['secao'] = secao_identificada 
        # Se o tipo veio do vinculo (ex: "despacho|Meu Botao"), pode ser útil tê-lo.
        if tipo_vinculo_item: config_para_proxima_acao['tipo_vinculo_origem'] = tipo_vinculo_item
        
        print(f"[VINCULO][FILA] Config para executar_autogigs (item da fila): {config_para_proxima_acao}")
        # Chama executar_autogigs para a ação vinculada.
        # O `vinculo` dentro de `config_para_proxima_acao` (se existir) será o próximo da cadeia.
        executar_autogigs(driver, config_para_proxima_acao)
    else:
        print(f"[VINCULO][FILA][ERRO] Botão '{nm_botao_vinculo_item}' (tipo do vinculo: {tipo_vinculo_item}) não encontrado no JSON de botões. Cadeia interrompida.")
        monitor_fim('Nenhum') # Sinaliza que esta tentativa de vínculo falhou e interrompe.
    
    fila_execucao.task_done()
    
except queue.Empty:
    # Timeout é esperado, permite que o loop verifique _parar_processador_vinculos_event
    if _parar_processador_vinculos_event.is_set():
        print("[VINCULO][FILA] Evento de parada recebido, finalizando thread processar_fila_vinculos.")
        break # Sai do loop while
    continue # Volta para o início do while
except Exception as e:
    print(f'[VINCULO][FILA][ERRO GRAVE] Falha no processamento da fila: {e}')
    import traceback
    traceback.print_exc()
    if not fila_execucao.empty(): # Evitar erro se a fila estiver vazia e get falhou
         try:
            fila_execucao.task_done() # Tenta marcar como feito para não bloquear join() indefinidamente
         except ValueError: # Se task_done() for chamado mais vezes que put()
            pass 
    monitor_fim('Nenhum') # Tenta limpar o estado em caso de erro grave na thread.

_processador_vinculos_thread = None
_parar_processador_vinculos_event = threading.Event()

def iniciar_processador_vinculos(driver):
    """
    Inicia a thread para processamento de vínculos em background.
    Garante que apenas uma thread esteja ativa.
    """
    global _processador_vinculos_thread
    if _processador_vinculos_thread is None or not _processador_vinculos_thread.is_alive():
        _parar_processador_vinculos_event.clear() # Reseta o evento de parada
        _processador_vinculos_thread = threading.Thread(
            target=processar_fila_vinculos, 
            args=(driver,), 
            daemon=True # Permite que o programa principal saia mesmo se a thread estiver rodando.
        )
        _processador_vinculos_thread.start()
        print('[VINCULO] Processador de vínculos iniciado/reiniciado.')
    else:
        print('[VINCULO] Processador de vínculos já está ativo.')

def parar_processador_vinculos():
    """Sinaliza a thread do processador de vínculos para parar e aguarda sua finalização."""
    global _processador_vinculos_thread
    if _processador_vinculos_thread and _processador_vinculos_thread.is_alive():
        print("[VINCULO] Solicitando parada do processador de vínculos...")
        _parar_processador_vinculos_event.set() # Sinaliza para a thread parar
        _processador_vinculos_thread.join(timeout=5) # Espera a thread terminar
        if _processador_vinculos_thread.is_alive():
            print("[VINCULO][AVISO] Timeout ao esperar a thread do processador de vínculos terminar.")
        else:
            print("[VINCULO] Processador de vínculos parado.")
    else:
        print("[VINCULO] Processador de vínculos não estava ativo ou já foi parado.")
    _processador_vinculos_thread = None # Limpa a referência da thread

def limpar_storage_vinculos():
    """
    Limpa o storage de vínculos e a fila de execução.
    """
    global vinculo_storage
    print('[VINCULO] Limpando storage de vínculos e fila de execução...')
    vinculo_storage = {
        'tempBt': [],
        'tempAAEspecial': [],
        'AALote': ''
    }
    
    # Limpa a fila de execução
    # É importante fazer isso de forma segura, especialmente se a thread ainda estiver consumindo.
    # Idealmente, pare a thread antes de limpar a fila se houver risco de condição de corrida.
    with fila_execucao.mutex: # Bloqueia a fila para limpá-la
        fila_execucao.queue.clear()
        # Reseta contadores internos de tasks se necessário (depende da versão/implementação de queue)
        # Para Python 3.7+, task_done() decrementa um contador interno.
        # Limpar a queue diretamente não reseta esse contador, o que pode fazer join() bloquear.
        # Uma forma de "resetar" é garantir que todas as tasks sejam marcadas como done.
        # No entanto, como estamos limpando a fila, não haverá mais itens para processar.
        # Se a thread foi parada corretamente, isso deve ser seguro.
        # Para garantir que join() não bloqueie se houve puts sem gets correspondentes:
        try:
            while True: 
                fila_execucao.get_nowait() 
                fila_execucao.task_done()
        except queue.Empty:
            pass # Fila está vazia

    print('[VINCULO] Storage de vínculos e fila de execução foram limpos.')


# Carrega os botões do arquivo JSON
with open('botoes_maispje.json', encoding='utf-8') as f:
    botoes = json.load(f)

def executar_acao_botao(driver, secao, indice=0):
    """
    Função auxiliar para executar ação de botão baseado na seção e índice.
    
    Args:
        driver: instância do Selenium WebDriver
        secao: nome da seção ('aaDespacho', 'aaAutogigs', etc.)
        indice: índice do botão na seção (padrão: 0)
    
    Returns:
        bool: True se executado com sucesso, False caso contrário
    """
    try:
        if secao not in botoes:
            print(f'[EXECUTAR] Seção {secao} não encontrada no arquivo de botões.')
            return False
        
        if indice >= len(botoes[secao]):
            print(f'[EXECUTAR] Índice {indice} inválido para seção {secao} (máximo: {len(botoes[secao])-1}).')
            return False
        
        config = botoes[secao][indice]
        print(f'[EXECUTAR] Executando {secao}[{indice}]: {config.get("nm_botao", "")}')
        
        if secao == 'aaDespacho':
            return acao_bt_aaDespacho_selenium(driver, config)
        elif secao == 'aaComunicacao':
            return acao_bt_apec_selenium(driver, config)
        elif secao == 'aaAnexar':
            return acao_bt_anexar_selenium(driver, config)
        elif secao == 'aaAutogigs':
            return acao_bt_aaAutogigs_selenium(driver, config)
        elif secao == 'aaChecklist':
            return acao_bt_aaChecklist_selenium(driver, config)
        elif secao == 'aaLancarMovimentos':
            return acao_bt_aaLancarMovimentos_selenium(driver, config)
        elif secao == 'aaMovimento':
            return acao_bt_aaMovimento_selenium(driver, config)
        elif secao == 'aaVariados':
            return acao_bt_aaVariados_selenium(driver, config)
        else:
            print(f'[EXECUTAR] Seção {secao} não possui função implementada.')
            return False
            
    except Exception as e:
        print(f'[EXECUTAR][ERRO] {e}')
        return False

def listar_botoes_secao(secao):
    """
    Lista todos os botões disponíveis em uma seção.
    
    Args:
        secao: nome da seção
    
    Returns:
        list: lista com informações dos botões
    """
    if secao not in botoes:
        print(f'Seção {secao} não encontrada.')
        return []
    
    print(f'\n=== Botões da seção {secao} ===')
    for i, botao in enumerate(botoes[secao]):
        nome = botao.get('nm_botao', 'Sem nome')
        descricao = botao.get('descricao', botao.get('observacao', ''))
        print(f'{i:2d}: {nome} - {descricao}')
    
    return botoes[secao]

def acao_bt_aaDespacho_selenium(driver, config):
    """
    Executa o fluxo de despacho automatizado, fiel ao gigs-plugin.js.
    config: dict com chaves nm_botao, tipo, descricao, sigilo, modelo, juiz, responsavel, cor, vinculo, assinar
    """
    try:
        print(f"[DESPACHO] Iniciando ação automatizada: {config.get('nm_botao','')} (vínculo: {config.get('vinculo','')})")
        # 1. Movimentar para tarefa correta (Análise → Conclusão ao Magistrado)
        try:
            btn_analise = driver.find_element(By.XPATH, "//button[contains(translate(.,'ANÁLISE','análise'),'análise')]")
            btn_analise.click()
            print('[DESPACHO] Movimentado para Análise.')
            time.sleep(1)
        except Exception:
            print('[DESPACHO] Botão Análise não encontrado ou já na tarefa correta.')
        try:
            btn_conclusao = driver.find_element(By.XPATH, "//button[contains(translate(.,'CONCLUSÃO','conclusão'),'conclusão ao magistrado')]")
            btn_conclusao.click()
            print('[DESPACHO] Movimentado para Conclusão ao Magistrado.')
            time.sleep(1)
        except Exception:
            print('[DESPACHO] Botão Conclusão ao Magistrado não encontrado ou já na tarefa correta.')
        # 2. Selecionar magistrado (se necessário)
        if config.get('juiz'):
            try:
                select_juiz = driver.find_element(By.CSS_SELECTOR, 'mat-select[placeholder="Magistrado"]')
                select_juiz.click()
                time.sleep(0.5)
                opcoes = driver.find_elements(By.CSS_SELECTOR, 'mat-option')
                for op in opcoes:
                    if config['juiz'].lower() in op.text.lower():
                        op.click()
                        print(f"[DESPACHO] Magistrado selecionado: {config['juiz']}")
                        break
                time.sleep(1)
            except Exception:
                print('[DESPACHO] Não foi possível selecionar magistrado.')
        # 3. Selecionar tipo de conclusão (Despacho)
        try:
            btn_tipo = driver.find_element(By.XPATH, "//button[contains(.,'Despacho')]")
            btn_tipo.click()
            print('[DESPACHO] Tipo de conclusão selecionado: Despacho.')
            time.sleep(1)
        except Exception:
            print('[DESPACHO] Botão de tipo Despacho não encontrado ou já selecionado.')
        # 4. Preencher descrição
        if config.get('descricao'):
            try:
                input_desc = driver.find_element(By.CSS_SELECTOR, 'input[aria-label="Descrição"]')
                input_desc.clear()
                input_desc.send_keys(config['descricao'])
                print(f"[DESPACHO] Descrição preenchida: {config['descricao']}")
            except Exception:
                print('[DESPACHO] Campo de descrição não encontrado.')
        # 5. Sigilo
        if config.get('sigilo','').lower() == 'sim':
            try:
                chk_sigilo = driver.find_element(By.CSS_SELECTOR, 'input[name="sigiloso"]')
                if not chk_sigilo.is_selected():
                    chk_sigilo.click()
                print('[DESPACHO] Sigilo ativado.')
            except Exception:
                print('[DESPACHO] Campo de sigilo não encontrado.')
        # 6. Escolher modelo
        if config.get('modelo'):
            try:
                campo_modelo = driver.find_element(By.CSS_SELECTOR, 'input[id="inputFiltro"]')
                campo_modelo.clear()
                campo_modelo.send_keys(config['modelo'])
                campo_modelo.send_keys(Keys.ENTER)
                print(f"[DESPACHO] Modelo selecionado: {config['modelo']}")
                time.sleep(1)
                modelo_item = driver.find_element(By.XPATH, f"//div[@role='treeitem' and contains(.,'{config['modelo']}')]")
                modelo_item.click()
                print('[DESPACHO] Modelo inserido no editor.')
            except Exception:
                print('[DESPACHO] Não foi possível selecionar/inserir modelo.')
        # 7. Salvar documento
        try:
            btn_salvar = driver.find_element(By.CSS_SELECTOR, 'button[aria-label="Salvar"]')
            btn_salvar.click()
            print('[DESPACHO] Documento salvo.')
            time.sleep(1)
        except Exception:
            print('[DESPACHO] Botão Salvar não encontrado.')
        # === AÇÕES EXTRAS (INTIMAÇÃO, PEC, PRAZOS, MOVIMENTOS, ETC) ===
        # 8. Intimação/PEC
        if config.get('marcar_pec'):
            try:
                btn_pec = driver.find_element(By.CSS_SELECTOR, 'button[aria-label*="PEC"], input[type="checkbox"][aria-label*="PEC"]')
                if btn_pec.tag_name == 'input' and not btn_pec.is_selected():
                    btn_pec.click()
                elif btn_pec.tag_name == 'button':
                    btn_pec.click()
                print('[DESPACHO] PEC marcada.')
                time.sleep(0.5)
            except Exception:
                print('[DESPACHO] Não foi possível marcar PEC.')
        # 9. Prazo
        if config.get('prazo') is not None:
            try:
                linhas = driver.find_elements(By.CSS_SELECTOR, 'table.t-class tr.ng-star-inserted')
                if not linhas:
                    print('[DESPACHO][PRAZO][ERRO] Nenhuma linha de destinatário encontrada!')
                else:
                    for tr in linhas:
                        try:
                            input_prazo = tr.find_element(By.CSS_SELECTOR, 'mat-form-field.prazo input[type="text"].mat-input-element')
                            input_prazo.clear()
                            input_prazo.send_keys(str(config['prazo']))
                            print(f'[DESPACHO][PRAZO][OK] Preenchido prazo {config["prazo"]} para destinatário.')
                        except Exception as e:
                            print(f'[DESPACHO][PRAZO][WARN] Erro ao preencher prazo: {e}')
            except Exception as e:
                print(f'[DESPACHO][PRAZO][ERRO] {e}')
        # 10. Movimento
        if config.get('movimento'):
            try:
                guia_mov = driver.find_element(By.CSS_SELECTOR, 'pje-editor-lateral div[aria-posinset="2"]')
                if guia_mov.get_attribute('aria-selected') == "false":
                    guia_mov.click()
                    time.sleep(0.5)
                movimentos = str(config['movimento']).split(',')
                for i, mo in enumerate(movimentos):
                    if i == 0:
                        chk = driver.find_element(By.XPATH, f'//pje-movimento//mat-checkbox[contains(.,"{mo}")]')
                        if 'checked' not in chk.get_attribute('class'):
                            chk.find_element(By.TAG_NAME, 'label').click()
                            time.sleep(0.5)
                    else:
                        time.sleep(0.5)
                        complementos = driver.find_elements(By.CSS_SELECTOR, 'pje-complemento')
                        if len(complementos) > i-1:
                            combo = complementos[i-1].find_element(By.TAG_NAME, 'mat-select')
                            combo.click()
                            time.sleep(0.3)
                            opcoes = driver.find_elements(By.CSS_SELECTOR, 'mat-option')
                            for op in opcoes:
                                if mo.lower() in op.text.lower():
                                    op.click()
                                    break
                            time.sleep(0.5)
                btn_gravar = driver.find_element(By.CSS_SELECTOR, 'pje-lancador-de-movimentos button[aria-label*="Gravar"]')
                btn_gravar.click()
                time.sleep(0.5)
                btn_sim = driver.find_element(By.XPATH, '//mat-dialog-container//button[.//span[contains(text(),"Sim")]]')
                btn_sim.click()
                print('[DESPACHO] Movimento(s) lançado(s).')
            except Exception as e:
                print(f'[DESPACHO][MOVIMENTO][ERRO] {e}')
        # 9. Enviar para assinatura
        if config.get('assinar','não').lower() == 'sim':
            try:
                btn_assinar = driver.find_element(By.CSS_SELECTOR, 'button[aria-label="Enviar para assinatura"]')
                btn_assinar.click()
                print('[DESPACHO] Documento enviado para assinatura.')
                time.sleep(1)
            except Exception:
                print('[DESPACHO] Botão Enviar para assinatura não encontrado.')
        # 10. Inserir responsável (se necessário)
        if config.get('responsavel'):
            print(f"[DESPACHO] Responsável: {config['responsavel']} (implementar fluxo se necessário)")
        print('[DESPACHO] Fluxo de despacho automatizado finalizado.')
        return True
    except Exception as e:
        print(f'[DESPACHO][ERRO] {e}')
        return False

def acao_bt_apec_selenium(driver, config):
    """
    Executa o fluxo automatizado de comunicação/expediente (intimação, mandado, edital, etc) na tela de minutas,
    fiel ao gigs-plugin.js (acao_bt_aaComunicacao).
    config: dict com chaves tipo_expediente, tipo_prazo, prazo, subtipo, descricao, sigilo, modelo, salvar, assinar, nm_botao, etc.
    """
    try:
        print(f"[APEC] Iniciando ação automatizada de comunicação/expediente: {config.get('tipo_expediente','')} - {config.get('modelo','')}")
        # NÃO clicar no botão envelope, nem buscar botão na tela: fluxo deve partir diretamente do config recebido
        # 2. Esperar navegação para /comunicacoesprocessuais/minutas
        for _ in range(30):
            if '/comunicacoesprocessuais/minutas' in driver.current_url:
                print('[APEC] Navegação para minutas confirmada.')
                break
            time.sleep(0.5)
        else:
            print('[APEC][ERRO] Timeout aguardando navegação para minutas.')
            return False
        # 3. Preencher tipo de expediente
        tipo = config.get('tipo_expediente') or config.get('tipo') or 'Intimação'
        try:
            campo_tipo = driver.find_element(By.CSS_SELECTOR, 'mat-select[placeholder="Tipo de Expediente"]')
            campo_tipo.click()
            time.sleep(0.5)
            xpath_opcao = f"//mat-option//span[contains(text(), '{tipo}') or contains(text(), '{tipo.lower()}') or contains(text(), '{tipo.upper()}')]"
            opcao_tipo = driver.find_element(By.XPATH, xpath_opcao)
            opcao_tipo.click()
            print(f"[APEC] Tipo de expediente selecionado: {tipo}")
            time.sleep(0.5)
        except Exception as e:
            print(f'[APEC][ERRO] Falha ao selecionar tipo de expediente: {e}')
            return False
        # 4. Tipo de prazo e preenchimento
        tipo_prazo = (config.get('tipo_prazo') or 'dias uteis').lower()
        prazo = config.get('prazo')
        try:
            if tipo_prazo == 'dias uteis' or tipo_prazo == 'dias úteis':
                radio = driver.find_element(By.XPATH, "//mat-radio-button[.//span[contains(translate(.,'Ú','u'),'dias uteis') or contains(translate(.,'Ú','u'),'dias úteis')]]")
                radio.click()
                campo_prazo = driver.find_element(By.CSS_SELECTOR, 'input[aria-label="Prazo em dias úteis"]')
                campo_prazo.clear()
                campo_prazo.send_keys(str(prazo))
                print(f"[APEC] Prazo em dias úteis preenchido: {prazo}")
            elif tipo_prazo == 'sem prazo':
                radio = driver.find_element(By.XPATH, "//mat-radio-button[.//span[contains(translate(.,'SEM PRAZO','sem prazo'),'sem prazo')]]")
                radio.click()
                print('[APEC] Tipo de prazo: sem prazo')
            elif tipo_prazo == 'data certa':
                radio = driver.find_element(By.XPATH, "//mat-radio-button[.//span[contains(translate(.,'DATA CERTA','data certa'),'data certa')]]")
                radio.click()
                campo_prazo = driver.find_element(By.CSS_SELECTOR, 'input[aria-label="Prazo em data certa"]')
                campo_prazo.clear()
                campo_prazo.send_keys(str(prazo))
                print(f"[APEC] Prazo em data certa preenchido: {prazo}")
        except Exception as e:
            print(f'[APEC][ERRO] Falha ao preencher tipo/prazo: {e}')
        # 5. Clicar em "Confeccionar ato agrupado"
        try:
            btn_conf = driver.find_element(By.CSS_SELECTOR, 'button[aria-label="Confeccionar ato agrupado"]')
            btn_conf.click()
            print('[APEC] Botão Confeccionar ato agrupado clicado.')
            time.sleep(1)
        except Exception as e:
            print(f'[APEC][ERRO] Falha ao clicar em Confeccionar ato agrupado: {e}')
            return False
        # 6. Subtipo do expediente
        if config.get('subtipo'):
            try:
                campo_subtipo = driver.find_element(By.CSS_SELECTOR, 'input[data-placeholder="Tipo de Documento"]')
                campo_subtipo.clear()
                campo_subtipo.send_keys(config['subtipo'])
                campo_subtipo.send_keys(Keys.ENTER)
                print(f"[APEC] Subtipo selecionado: {config['subtipo']}")
                time.sleep(0.5)
            except Exception as e:
                print(f'[APEC][ERRO] Falha ao selecionar subtipo: {e}')
        # 7. Descrição
        if config.get('descricao'):
            try:
                input_desc = driver.find_element(By.CSS_SELECTOR, 'input[aria-label="Descrição"]')
                input_desc.clear()
                input_desc.send_keys(config['descricao'])
                print(f"[APEC] Descrição preenchida: {config['descricao']}")
            except Exception:
                print('[APEC] Campo de descrição não encontrado.')
        # 8. Sigilo
        sigilo = (config.get('sigilo') or 'nao').lower()
        if 'sim' in sigilo:
            try:
                chk_sigilo = driver.find_element(By.CSS_SELECTOR, 'input[name="sigiloso"]')
                if not chk_sigilo.is_selected():
                    chk_sigilo.click()
                print('[APEC] Sigilo ativado.')
            except Exception:
                print('[APEC] Campo de sigilo não encontrado.')
        # 9. Escolha do modelo
        if config.get('modelo'):
            try:
                campo_modelo = driver.find_element(By.CSS_SELECTOR, 'input[id="inputFiltro"]')
                campo_modelo.clear()
                campo_modelo.send_keys(config['modelo'])
                campo_modelo.send_keys(Keys.ENTER)
                print(f"[APEC] Modelo selecionado: {config['modelo']}")
                time.sleep(1)
                modelo_item = driver.find_element(By.XPATH, f"//div[@role='treeitem' and contains(.,'{config['modelo']}')]")
                modelo_item.click()
                print('[APEC] Modelo inserido no editor.')
            except Exception as e:
                print(f'[APEC][ERRO] Não foi possível selecionar/inserir modelo: {e}')
        # 10. Salvar e finalizar minuta
        salvar = (config.get('salvar') or 'sim').lower()
        if salvar == 'sim':
            try:
                btn_salvar = driver.find_element(By.CSS_SELECTOR, 'button[aria-label="Salvar"]')
                btn_salvar.click()
                print('[APEC] Minuta salva.')
                time.sleep(1)
                btn_finalizar = driver.find_element(By.CSS_SELECTOR, 'button[aria-label="Finalizar minuta"]')
                btn_finalizar.click()
                print('[APEC] Minuta finalizada.')
                time.sleep(1)
            except Exception as e:
                print(f'[APEC][ERRO] Não foi possível salvar/finalizar minuta: {e}')
                return False
        # 11. Parâmetros especiais: seleção de destinatários, assinatura, etc
        nm_botao = config.get('nm_botao','')
        parametros = []
        import re
        m = re.findall(r'\[(.*?)\]', nm_botao)
        if m:
            parametros = [p.strip() for p in ','.join(m).split(',')]
        if parametros:
            print(f"[APEC] Parâmetros especiais detectados: {parametros}")
            condicao = 0
            if 'ativo' in parametros:
                try:
                    btn_ativo = driver.find_element(By.CSS_SELECTOR, 'pje-pec-partes-processo button[aria-label*="somente polo ativo"]')
                    btn_ativo.click()
                    print('[APEC] Polo ativo selecionado.')
                    condicao = 1
                    time.sleep(1)
                except Exception as e:
                    print(f'[APEC][ERRO] Polo ativo: {e}')
            if 'passivo' in parametros:
                try:
                    btn_passivo = driver.find_element(By.CSS_SELECTOR, 'pje-pec-partes-processo button[aria-label*="somente polo passivo"]')
                    btn_passivo.click()
                    print('[APEC] Polo passivo selecionado.')
                    condicao = 2
                    time.sleep(1)
                except Exception as e:
                    print(f'[APEC][ERRO] Polo passivo: {e}')
            if 'terceiros' in parametros:
                try:
                    btn_terc = driver.find_element(By.CSS_SELECTOR, 'pje-pec-partes-processo button[aria-label*="somente terceiros interessados"]')
                    btn_terc.click()
                    print('[APEC] Terceiros selecionados.')
                    condicao = 3
                    time.sleep(1)
                except Exception as e:
                    print(f'[APEC][ERRO] Terceiros: {e}')
            if 'trt' in parametros:
                try:
                    btn_trt = driver.find_element(By.CSS_SELECTOR, '#maisPje_bt_invisivel_outrosDestinatarios_TRT')
                    btn_trt.click()
                    print('[APEC] TRT selecionado.')
                    condicao = 4
                    time.sleep(1)
                except Exception as e:
                    print(f'[APEC][ERRO] TRT: {e}')
            try:
                for _ in range(20):
                    if driver.find_elements(By.CSS_SELECTOR, 'pje-pec-tabela-destinatarios i[aria-label="Ato confeccionado"]'):
                        print('[APEC] Ato confeccionado detectado.')
                        break
                    time.sleep(0.5)
                time.sleep(1)
            except Exception:
                print('[APEC] Não foi possível detectar ato confeccionado.')
            try:
                btn_salvar_exp = driver.find_element(By.CSS_SELECTOR, 'pje-pec-tabela-destinatarios button[aria-label="Salva os expedientes"]')
                btn_salvar_exp.click()
                print('[APEC] Expedientes salvos.')
                time.sleep(1)
            except Exception as e:
                print(f'[APEC][ERRO] Salvar expedientes: {e}')
            if 'assinar' in parametros and condicao > 0:
                try:
                    btn_assinar = driver.find_element(By.CSS_SELECTOR, 'pje-pec-tabela-destinatarios button[aria-label="Assinar ato(s)"]')
                    btn_assinar.click()
                    print('[APEC] Ato(s) assinado(s).')
                    time.sleep(1)
                except Exception as e:
                    print(f'[APEC][ERRO] Assinar ato(s): {e}')
        print('[APEC] Fluxo de comunicação/expediente automatizado finalizado.')
        return True
    except Exception as e:
        print(f'[APEC][ERRO] {e}')
        return False

def acao_bt_anexar_selenium(driver, config):
    """
    Executa o fluxo automatizado de anexar documentos, fiel ao gigs-plugin.js (acao_bt_aaAnexar).
    config: dict com chaves tipo, descricao, sigilo, modelo, assinar, extras, etc.
    """
    try:
        print(f"[ANEXAR] Iniciando ação automatizada de anexar: {config.get('tipo','')} - {config.get('modelo','')}")
        # 1. Clicar no botão de anexar documentos (fa-paperclip)
        try:
            btn_anexar = driver.find_element(By.ID, 'pjextension_bt_detalhes_4')
            btn_anexar.click()
            print('[ANEXAR] Botão de anexar documentos clicado.')
            time.sleep(1)
        except Exception:
            print('[ANEXAR] Botão de anexar documentos não encontrado ou já clicado.')
        # 2. PDF?
        if config.get('modelo','').lower() == 'pdf':
            try:
                switch_pdf = driver.find_element(By.CSS_SELECTOR, 'input[role="switch"]')
                switch_pdf.click()
                print('[ANEXAR] Switch PDF ativado.')
                time.sleep(0.5)
            except Exception:
                print('[ANEXAR] Switch PDF não encontrado.')
        # 3. Preencher tipo
        tipo = config.get('tipo') or 'Certidão'
        try:
            campo_tipo = driver.find_element(By.CSS_SELECTOR, 'input[aria-label="Tipo de Documento"]')
            campo_tipo.clear()
            campo_tipo.send_keys(tipo)
            campo_tipo.send_keys(Keys.ENTER)
            print(f"[ANEXAR] Tipo de documento selecionado: {tipo}")
            time.sleep(0.5)
        except Exception as e:
            print(f'[ANEXAR][ERRO] Falha ao selecionar tipo: {e}')
        # 4. Preencher descrição
        if config.get('descricao'):
            try:
                campo_desc = driver.find_element(By.CSS_SELECTOR, 'input[aria-label="Descrição"]')
                campo_desc.clear()
                campo_desc.send_keys(config['descricao'])
                print(f"[ANEXAR] Descrição preenchida: {config['descricao']}")
            except Exception:
                print('[ANEXAR] Campo de descrição não encontrado.')
        # 5. Sigilo
        sigilo = (config.get('sigilo') or 'nao').lower()
        if 'sim' in sigilo:
            try:
                chk_sigilo = driver.find_element(By.CSS_SELECTOR, 'input[name="sigiloso"]')
                if not chk_sigilo.is_selected():
                    chk_sigilo.click()
                print('[ANEXAR] Sigilo ativado.')
                time.sleep(0.5)
            except Exception:
                print('[ANEXAR] Campo de sigilo não encontrado.')
        # 6. Escolha do modelo
        if config.get('modelo') and config.get('modelo','').lower() != 'pdf':
            try:
                campo_modelo = driver.find_element(By.CSS_SELECTOR, 'input[id="inputFiltro"]')
                campo_modelo.clear()
                campo_modelo.send_keys(config['modelo'])
                campo_modelo.send_keys(Keys.ENTER)
                print(f"[ANEXAR] Modelo selecionado: {config['modelo']}")
                time.sleep(1)
                modelo_item = driver.find_element(By.XPATH, f"//div[@role='treeitem' and contains(.,'{config['modelo']}')]")
                modelo_item.click()
                print('[ANEXAR] Modelo inserido no editor.')
            except Exception as e:
                print(f'[ANEXAR][ERRO] Não foi possível selecionar/inserir modelo: {e}')
        # 7. Upload de PDF (se modelo for PDF)
        if config.get('modelo','').lower() == 'pdf':
            try:
                btn_upload = driver.find_element(By.CSS_SELECTOR, 'label.upload-button')
                btn_upload.click()
                print('[ANEXAR] Botão de upload de PDF clicado. Aguarde seleção manual do arquivo.')
                for _ in range(120):
                    if driver.find_elements(By.CSS_SELECTOR, 'span.nome-arquivo-pdf'):
                        print('[ANEXAR] PDF carregado.')
                        break
                    time.sleep(0.5)
                if not config.get('descricao'):
                    try:
                        el_pdf = driver.find_element(By.CSS_SELECTOR, 'span.nome-arquivo-pdf')
                        nome_pdf = el_pdf.text.replace('.pdf','')
                        campo_desc = driver.find_element(By.CSS_SELECTOR, 'input[aria-label="Descrição"]')
                        campo_desc.clear()
                        campo_desc.send_keys(nome_pdf)
                        print(f"[ANEXAR] Descrição preenchida com nome do PDF: {nome_pdf}")
                    except Exception:
                        print('[ANEXAR] Não foi possível preencher descrição com nome do PDF.')
            except Exception as e:
                print(f'[ANEXAR][ERRO] Upload de PDF: {e}')
        # 8. Juntada de depoimentos/anexos
        extras = config.get('extras','')
        if '[anexos]' in extras.lower() or extras == 'ID997_Anexar Depoimento':
            try:
                btn_salvar = driver.find_element(By.CSS_SELECTOR, 'button[aria-label="Salvar"]')
                btn_salvar.click()
                print('[ANEXAR] Documento salvo para anexos.')
                time.sleep(1)
                guia_anexos = driver.find_element(By.CSS_SELECTOR, 'div[aria-posinset="2"]')
                guia_anexos.click()
                print('[ANEXAR] Guia Anexos aberta.')
                time.sleep(0.5)
                btn_upload = driver.find_element(By.CSS_SELECTOR, 'label.upload-button')
                btn_upload.click()
                print('[ANEXAR] Botão de upload de anexo clicado.')
                time.sleep(2)
                if extras == 'ID997_Anexar Depoimento':
                    guia_anexos.click()
                    print('[ANEXAR] Fluxo de depoimento finalizado.')
                    return True
            except Exception as e:
                print(f'[ANEXAR][ERRO] Juntada de anexos: {e}')
        # 9. Assinar ou salvar
        assinar = (config.get('assinar') or 'nao').lower()
        if assinar == 'sim':
            try:
                btn_assinar = driver.find_element(By.CSS_SELECTOR, 'button[aria-label="Assinar documento e juntar ao processo"]')
                btn_assinar.click()
                print('[ANEXAR] Documento assinado e juntado ao processo.')
                time.sleep(2)
            except Exception as e:
                print(f'[ANEXAR][ERRO] Assinar documento: {e}')
        else:
            try:
                btn_salvar = driver.find_element(By.CSS_SELECTOR, 'button[aria-label="Salvar"]')
                btn_salvar.click()
                print('[ANEXAR] Documento salvo.')
                time.sleep(1)
            except Exception as e:
                print(f'[ANEXAR][ERRO] Salvar documento: {e}')
        print('[ANEXAR] Fluxo de anexar documento automatizado finalizado.')
        return True
    except Exception as e:
        print(f'[ANEXAR][ERRO] {e}')
        return False

def acao_bt_aaAutogigs_selenium(driver, config):
    """
    Executa o fluxo automatizado de AutoGigs (prazos, comentários, chips e lembretes).
    Implementação completa baseada na versão JavaScript original.
    
    config: dict com chaves:
    - nm_botao: nome do botão
    - tipo: 'prazo'|'preparo'|'comentario'|'chip'|'lembrete'
    - tipo_atividade: tipo da atividade ou nome do chip/título do lembrete
    - prazo: dias úteis ou data para prazos, visibilidade para comentários/lembretes
    - responsavel: responsável pela atividade GIGS
    - responsavel_processo: responsável pelo processo
    - observacao: texto de observação/conteúdo
    - salvar: 'sim'|'não' para salvar automaticamente
    - cor: cor do botão (não usado na execução)
    - vinculo: próxima ação a executar
    """
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    
    try:
        nm_botao = config.get('nm_botao', '')
        tipo = config.get('tipo', '')
        concluir = '[concluir]' in nm_botao
        
        print(f"[AUTOGIGS] Iniciando: {nm_botao} - Tipo: {tipo} - Concluir: {concluir}")
        
        # Verificar se GIGS está aberto em tela de detalhes
        gigs_fechado = _verificar_gigs_fechado(driver)
        if gigs_fechado:
            _abrir_gigs(driver)
        
        # Executar ação baseada no tipo
        if tipo == 'chip':
            return _executar_chip(driver, config, concluir)
        elif tipo == 'comentario':
            return _executar_comentario(driver, config, concluir, gigs_fechado)
        elif tipo == 'lembrete':
            return _executar_lembrete(driver, config, concluir)
        else:  # prazo ou preparo (default)
            return _executar_gigs_atividade(driver, config, concluir, gigs_fechado)
        
    except Exception as e:
        print(f'[AUTOGIGS][ERRO] {e}')
        return False

def _verificar_gigs_fechado(driver):
    """Verifica se o GIGS está fechado na tela de detalhes"""
    try:
        driver.find_element(By.CSS_SELECTOR, 'button[aria-label="Mostrar o GIGS"]')
        return True
    except:
        return False

def _abrir_gigs(driver):
    """Abre o GIGS se estiver fechado"""
    try:
        btn_mostrar = driver.find_element(By.CSS_SELECTOR, 'button[aria-label="Mostrar o GIGS"]')
        btn_mostrar.click()
        time.sleep(1)
        print("[AUTOGIGS] GIGS aberto")
    except Exception as e:
        print(f"[AUTOGIGS][ERRO] Falha ao abrir GIGS: {e}")

def _fechar_gigs(driver):
    """Fecha o GIGS se estiver aberto"""
    try:
        btn_esconder = driver.find_element(By.CSS_SELECTOR, 'button[aria-label="Esconder o GIGS"]')
        btn_esconder.click()
        time.sleep(0.5)
        print("[AUTOGIGS] GIGS fechado")
    except:
        pass

def _executar_chip(driver, config, concluir):
    """Executa ações de chip (adicionar ou remover)"""
    try:
        tipo_atividade = config.get('tipo_atividade', '')
        salvar = config.get('salvar', '').lower() == 'sim'
        
        if concluir:
            # Remover chips existentes
            return _remover_chips(driver, tipo_atividade)
        else:
            # Adicionar novos chips
            return _adicionar_chips(driver, tipo_atividade, salvar)
            
    except Exception as e:
        print(f"[AUTOGIGS][CHIP][ERRO] {e}")
        return False

def _remover_chips(driver, chips_para_remover):
    """Remove chips do processo"""
    try:
        # Expandir lista de chips se necessário
        try:
            btn_expandir = driver.find_element(By.CSS_SELECTOR, 'pje-lista-etiquetas button[aria-label="Expandir Chips"]')
            btn_expandir.click()
            time.sleep(0.5)
        except:
            pass
        
        # Buscar chips para remover
        chips = chips_para_remover.split(',')
        for chip in chips:
            chip = chip.strip()
            try:
                # Buscar botão de remoção do chip específico
                btn_remover = driver.find_element(By.CSS_SELECTOR, f'pje-lista-etiquetas mat-chip button[aria-label*="{chip}"]')
                btn_remover.click()
                time.sleep(0.5)
                
                # Confirmar remoção se aparecer diálogo
                try:
                    btn_confirmar = driver.find_element(By.XPATH, "//mat-dialog-container//button[contains(.,'Sim') or contains(.,'Confirmar')]")
                    btn_confirmar.click()
                    time.sleep(0.5)
                    print(f"[AUTOGIGS][CHIP] Chip removido: {chip}")
                except:
                    pass
            except Exception as e:
                print(f"[AUTOGIGS][CHIP][AVISO] Chip não encontrado para remoção: {chip}")
        
        return True
        
    except Exception as e:
        print(f"[AUTOGIGS][CHIP][ERRO] Falha ao remover chips: {e}")
        return False

def _adicionar_chips(driver, chips_para_adicionar, salvar):
    """Adiciona chips ao processo"""
    try:
        # Clicar no botão de adicionar chip
        btn_chip = driver.find_element(By.CSS_SELECTOR, 'button[aria-label="Incluir Chip Amarelo"]')
        btn_chip.click()
        time.sleep(1)
        
        # Verificar se é pergunta dinâmica
        if '[perguntar]' in chips_para_adicionar:
            chips_base = chips_para_adicionar.replace('[perguntar]', '').strip()
            try:
                campo_nome = driver.find_element(By.CSS_SELECTOR, 'input[data-placeholder="Nome do chip"]')
                campo_nome.clear()
                campo_nome.send_keys(chips_base)
                print(f"[AUTOGIGS][CHIP] Modo pergunta ativado com base: {chips_base}")
                # Não salva automaticamente no modo pergunta
                return True
            except:
                pass
        
        # Modo normal - selecionar chips da lista
        chips = chips_para_adicionar.split(',')
        for chip in chips:
            chip = chip.strip()
            try:
                # Buscar chip na tabela de etiquetas disponíveis
                chip_elemento = driver.find_element(By.XPATH, f'//table[@name="Etiquetas"]//tr[contains(.,"{chip}[MMA]")]')
                checkbox = chip_elemento.find_element(By.CSS_SELECTOR, 'input[aria-label="Marcar chip"]')
                if not checkbox.is_selected():
                    checkbox.click()
                    print(f"[AUTOGIGS][CHIP] Chip selecionado: {chip}")
                    time.sleep(0.3)
            except Exception as e:
                print(f"[AUTOGIGS][CHIP][AVISO] Chip não encontrado: {chip}")
        
        # Salvar se configurado
        if salvar:
            try:
                btn_salvar = driver.find_element(By.XPATH, "//button[contains(.,'Salvar')]")
                btn_salvar.click()
                time.sleep(1)
                print("[AUTOGIGS][CHIP] Chips salvos")
            except Exception as e:
                print(f"[AUTOGIGS][CHIP][ERRO] Falha ao salvar: {e}")
        
        return True
        
    except Exception as e:
        print(f"[AUTOGIGS][CHIP][ERRO] Falha ao adicionar chips: {e}")
        return False

def _executar_comentario(driver, config, concluir, gigs_fechado):
    """Executa ações de comentário (adicionar ou arquivar)"""
    try:
        responsavel_processo = config.get('responsavel_processo', '')
        observacao = config.get('observacao', '')
        visibilidade = config.get('prazo', 'LOCAL')  # prazo é usado como visibilidade
        salvar = config.get('salvar', '').lower() == 'sim'
        
        # Definir responsável do processo se especificado
        if responsavel_processo:
            _definir_responsavel_processo(driver, responsavel_processo)
        
        if concluir:
            # Arquivar comentários existentes
            return _arquivar_comentarios(driver, observacao, gigs_fechado)
        else:
            # Adicionar novo comentário
            return _adicionar_comentario(driver, observacao, visibilidade, salvar, gigs_fechado)
            
    except Exception as e:
        print(f"[AUTOGIGS][COMENTARIO][ERRO] {e}")
        return False

def _arquivar_comentarios(driver, texto_busca, gigs_fechado):
    """Arquiva comentários que contenham o texto especificado"""
    try:
        arquivados = 0
        
        while True:
            # Buscar comentários com o texto
            comentarios = driver.find_elements(By.CSS_SELECTOR, 
                'table[name="Lista de Comentários"] tbody tr, div[id="comentarios"] mat-card, div[id="tabela-comentarios"] tbody tr')
            
            comentario_encontrado = False
            for comentario in comentarios:
                if texto_busca.lower() in comentario.text.lower():
                    try:
                        # Clicar no botão arquivar
                        btn_arquivar = comentario.find_element(By.CSS_SELECTOR, 'i[aria-label*="Arquivar"], button[id*="arquivar"]')
                        btn_arquivar.click()
                        time.sleep(0.5)
                        
                        # Confirmar arquivamento
                        try:
                            btn_confirmar = driver.find_element(By.XPATH, "//mat-dialog-container//button[contains(.,'Sim') or contains(.,'Confirmar')]")
                            btn_confirmar.click()
                            time.sleep(1)
                            arquivados += 1
                            comentario_encontrado = True
                            print(f"[AUTOGIGS][COMENTARIO] Comentário arquivado: {texto_busca}")
                            break
                        except:
                            pass
                    except Exception as e:
                        print(f"[AUTOGIGS][COMENTARIO][ERRO] Falha ao arquivar: {e}")
            
            if not comentario_encontrado:
                break
        
        if gigs_fechado:
            _fechar_gigs(driver)
        
        print(f"[AUTOGIGS][COMENTARIO] Total de comentários arquivados: {arquivados}")
        return True
        
    except Exception as e:
        print(f"[AUTOGIGS][COMENTARIO][ERRO] Falha ao arquivar: {e}")
        return False

def _adicionar_comentario(driver, observacao, visibilidade, salvar, gigs_fechado):
    """Adiciona novo comentário"""
    try:
        # Clicar em novo comentário
        btn_novo = driver.find_element(By.XPATH, "//pje-gigs-comentarios-lista//button[contains(.,'Novo Comentário')]")
        btn_novo.click()
        time.sleep(1)
        
        # Processar observação (verificar se é pergunta)
        observacao_final = _processar_observacao(driver, observacao)
        
        # Preencher comentário
        campo_desc = driver.find_element(By.CSS_SELECTOR, 'textarea[name="descricao"], textarea[formcontrolname="descricao"]')
        campo_desc.clear()
        campo_desc.send_keys(observacao_final)
        
        # Definir visibilidade
        _definir_visibilidade_comentario(driver, visibilidade)
        
        # Salvar se configurado
        if salvar:
            btn_salvar = driver.find_element(By.XPATH, "//button[contains(.,'Salvar')]")
            btn_salvar.click()
            time.sleep(1)
            
            if gigs_fechado:
                _fechar_gigs(driver)
            
            print(f"[AUTOGIGS][COMENTARIO] Comentário adicionado: {observacao_final[:50]}...")
        
        return True
        
    except Exception as e:
        print(f"[AUTOGIGS][COMENTARIO][ERRO] Falha ao adicionar: {e}")
        return False

def _definir_visibilidade_comentario(driver, visibilidade):
    """Define a visibilidade do comentário"""
    try:
        radios = driver.find_elements(By.CSS_SELECTOR, 'pje-gigs-comentarios-cadastro mat-radio-button')
        
        if visibilidade.upper() == 'LOCAL' and len(radios) > 0:
            radios[0].find_element(By.CSS_SELECTOR, 'input').click()
        elif visibilidade.upper() == 'RESTRITA' and len(radios) > 1:
            radios[1].find_element(By.CSS_SELECTOR, 'input').click()
            # Escolher usuários restritos se necessário
            _escolher_usuarios_restritos(driver)
        elif visibilidade.upper() == 'GLOBAL' and len(radios) > 2:
            radios[2].find_element(By.CSS_SELECTOR, 'input').click()
            
        time.sleep(0.5)
        
    except Exception as e:
        print(f"[AUTOGIGS][COMENTARIO][ERRO] Falha ao definir visibilidade: {e}")

def _escolher_usuarios_restritos(driver):
    """Permite escolha de usuários restritos para comentário"""
    try:
        select_usuarios = driver.find_element(By.CSS_SELECTOR, 'pje-gigs-comentarios-cadastro mat-select[placeholder="Usuários concedidos"]')
        select_usuarios.click()
        print("[AUTOGIGS][COMENTARIO] Selecione os usuários restritos manualmente")
        # Aguarda o usuário fazer a seleção
        time.sleep(3)
    except Exception as e:
        print(f"[AUTOGIGS][COMENTARIO][ERRO] Falha ao abrir seleção de usuários: {e}")

def _executar_lembrete(driver, config, concluir):
    """Executa ações de lembrete (adicionar ou remover)"""
    try:
        titulo = config.get('tipo_atividade', '')
        visibilidade = config.get('prazo', 'LOCAL')  # prazo é usado como visibilidade
        conteudo = config.get('observacao', '')
        salvar = config.get('salvar', '').lower() == 'sim'
        
        if concluir:
            # Remover lembretes existentes
            return _remover_lembretes(driver, titulo, conteudo)
        else:
            # Adicionar novo lembrete
            return _adicionar_lembrete(driver, titulo, visibilidade, conteudo, salvar)
            
    except Exception as e:
        print(f"[AUTOGIGS][LEMBRETE][ERRO] {e}")
        return False

def _remover_lembretes(driver, titulo, conteudo):
    """Remove lembretes que correspondam aos critérios"""
    try:
        # Aguardar carregamento dos post-its
        try:
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'pje-visualizador-post-its div[class*="post-it-set"]'))
            )
        except:
            print("[AUTOGIGS][LEMBRETE] Nenhum lembrete encontrado")
            return True
        
        postits = driver.find_elements(By.CSS_SELECTOR, 'div[class*="post-it-set"] mat-expansion-panel')
        removidos = 0
        
        for postit in postits:
            try:
                elemento_titulo = postit.find_element(By.CSS_SELECTOR, 'div[class="post-it-div-titulo"]')
                elemento_conteudo = postit.find_element(By.CSS_SELECTOR, 'div[aria-label="Conteúdo do Lembrete"]')
                
                titulo_match = titulo.lower() in elemento_titulo.text.lower() if titulo else True
                conteudo_match = conteudo.lower() in elemento_conteudo.text.lower() if conteudo else True
                
                if titulo_match and conteudo_match:
                    btn_remover = postit.find_element(By.CSS_SELECTOR, 'button[aria-label="Remover Lembrete"]')
                    btn_remover.click()
                    time.sleep(0.5)
                    
                    # Confirmar remoção
                    try:
                        btn_confirmar = driver.find_element(By.XPATH, "//mat-dialog-container//button[contains(.,'Sim') or contains(.,'Confirmar')]")
                        btn_confirmar.click()
                        time.sleep(1)
                        removidos += 1
                        print(f"[AUTOGIGS][LEMBRETE] Lembrete removido: {titulo}")
                    except:
                        pass
                        
            except Exception as e:
                print(f"[AUTOGIGS][LEMBRETE][ERRO] Falha ao processar lembrete: {e}")
        
        print(f"[AUTOGIGS][LEMBRETE] Total de lembretes removidos: {removidos}")
        return True
        
    except Exception as e:
        print(f"[AUTOGIGS][LEMBRETE][ERRO] Falha ao remover: {e}")
        return False

def _adicionar_lembrete(driver, titulo, visibilidade, conteudo, salvar):
    """Adiciona novo lembrete"""
    try:
        # Abrir menu de post-it
        btn_menu = driver.find_element(By.CSS_SELECTOR, 'button[id="botao-menu"]')
        btn_menu.click()
        time.sleep(0.5)
        
        btn_postit = driver.find_element(By.CSS_SELECTOR, 'pje-icone-post-it button')
        btn_postit.click()
        time.sleep(1)
        
        # Preencher título
        campo_titulo = driver.find_element(By.CSS_SELECTOR, 'input[id="tituloPostit"]')
        campo_titulo.clear()
        campo_titulo.send_keys(titulo)
        
        # Definir visibilidade
        _definir_visibilidade_lembrete(driver, visibilidade)
        
        # Processar e preencher conteúdo
        conteudo_final = _processar_observacao(driver, conteudo)
        campo_conteudo = driver.find_element(By.CSS_SELECTOR, 'textarea[id="conteudoPostit"]')
        campo_conteudo.clear()
        campo_conteudo.send_keys(conteudo_final)
        
        # Salvar se configurado
        if salvar:
            btn_salvar = driver.find_element(By.XPATH, "//button[contains(.,'Salvar')]")
            btn_salvar.click()
            time.sleep(2)  # Aguardar salvamento
            print(f"[AUTOGIGS][LEMBRETE] Lembrete adicionado: {titulo}")
        
        return True
        
    except Exception as e:
        print(f"[AUTOGIGS][LEMBRETE][ERRO] Falha ao adicionar: {e}")
        return False

def _definir_visibilidade_lembrete(driver, visibilidade):
    """Define a visibilidade do lembrete"""
    try:
        select_visibilidade = driver.find_element(By.CSS_SELECTOR, 'mat-select[id="visibilidadePostit"]')
        select_visibilidade.click()
        time.sleep(0.5)
        
        opcao = driver.find_element(By.XPATH, f"//mat-option[contains(.,'{visibilidade.upper()}')]")
        opcao.click()
        time.sleep(0.5)
        
        # Se for PRIVADO, permitir seleção de usuários
        if visibilidade.upper() == 'PRIVADO':
            _escolher_usuarios_lembrete(driver)
            
    except Exception as e:
        print(f"[AUTOGIGS][LEMBRETE][ERRO] Falha ao definir visibilidade: {e}")

def _escolher_usuarios_lembrete(driver):
    """Permite escolha de usuários para lembrete privado"""
    try:
        time.sleep(1)  # Aguardar transição
        select_usuarios = driver.find_element(By.CSS_SELECTOR, 'pje-dialogo-post-it mat-select[id="destinatarioPostit"]')
        select_usuarios.click()
        print("[AUTOGIGS][LEMBRETE] Selecione os usuários para lembrete privado")
        time.sleep(3)  # Aguarda o usuário fazer a seleção
    except Exception as e:
        print(f"[AUTOGIGS][LEMBRETE][ERRO] Falha ao abrir seleção de usuários: {e}")

def _executar_gigs_atividade(driver, config, concluir, gigs_fechado):
    """Executa ações de atividade GIGS (adicionar ou concluir)"""
    try:
        responsavel_processo = config.get('responsavel_processo', '')
        
        # Definir responsável do processo se especificado
        if responsavel_processo:
            _definir_responsavel_processo(driver, responsavel_processo)
        
        if concluir:
            # Concluir atividades existentes
            return _concluir_atividades_gigs(driver, config, gigs_fechado)
        else:
            # Adicionar nova atividade
            return _adicionar_atividade_gigs(driver, config, gigs_fechado)
            
    except Exception as e:
        print(f"[AUTOGIGS][GIGS][ERRO] {e}")
        return False

def _concluir_atividades_gigs(driver, config, gigs_fechado):
    """Conclui atividades GIGS baseadas nos critérios especificados"""
    try:
        # Aguardar carregamento da lista de atividades
        try:
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'div[id="tabela-atividades"] table tbody tr'))
            )
        except:
            print("[AUTOGIGS][GIGS] Nenhuma atividade encontrada")
            return True
        
        atividades = driver.find_elements(By.CSS_SELECTOR, 'div[id="tabela-atividades"] table tbody tr')
        tipo_atividade_filtro = config.get('tipo_atividade', '').lower().split(';')
        responsavel_filtro = config.get('responsavel', '').lower().split(';')
        observacao_filtro = config.get('observacao', '').lower().split(';')
        
        concluidas = 0
        
        for atividade in atividades:
            try:
                # Extrair informações da atividade
                responsavel_elem = atividade.find_element(By.CSS_SELECTOR, 'span[class*="texto-responsavel"]')
                responsavel_texto = responsavel_elem.text.lower() if responsavel_elem else ""
                
                descricao_elem = atividade.find_element(By.CSS_SELECTOR, 'span[class*="descricao"]')
                descricao_texto = descricao_elem.text.lower().split(':')[0] if descricao_elem else ""
                
                texto_completo = atividade.text.lower()
                observacao_texto = texto_completo.replace(descricao_texto + ':', '').replace(responsavel_texto, '')
                
                # Verificar critérios de filtro
                condicao1 = not tipo_atividade_filtro[0] or any(t in descricao_texto for t in tipo_atividade_filtro if t)
                condicao2 = not responsavel_filtro[0] or any(r in responsavel_texto for r in responsavel_filtro if r)
                condicao3 = not observacao_filtro[0] or any(o in observacao_texto for o in observacao_filtro if o)
                
                if condicao1 and condicao2 and condicao3:
                    # Concluir atividade
                    btn_concluir = atividade.find_element(By.CSS_SELECTOR, 'button[aria-label="Concluir Atividade"]')
                    atividade.location_once_scrolled_into_view  # Scroll para o elemento
                    btn_concluir.click()
                    time.sleep(0.5)
                    
                    # Confirmar conclusão
                    try:
                        btn_sim = driver.find_element(By.XPATH, "//mat-dialog-container//button[contains(.,'Sim')]")
                        btn_sim.click()
                        time.sleep(1)
                        concluidas += 1
                        print(f"[AUTOGIGS][GIGS] Atividade concluída: {descricao_texto}")
                    except:
                        pass
                        
                time.sleep(0.3)  # Pequena pausa entre verificações
                
            except Exception as e:
                print(f"[AUTOGIGS][GIGS][ERRO] Falha ao processar atividade: {e}")
        
        if gigs_fechado:
            _fechar_gigs(driver)
        
        print(f"[AUTOGIGS][GIGS] Total de atividades concluídas: {concluidas}")
        return True
        
    except Exception as e:
        print(f"[AUTOGIGS][GIGS][ERRO] Falha ao concluir atividades: {e}")
        return False

def _adicionar_atividade_gigs(driver, config, gigs_fechado):
    """Adiciona nova atividade GIGS"""
    try:
        # Verificar se o painel GIGS está visível
        try:
            driver.find_element(By.CSS_SELECTOR, 'pje-gigs-ficha-processo')
        except:
            _abrir_gigs(driver)
        
        # Clicar em Nova atividade
        btn_nova = driver.find_element(By.XPATH, "//pje-gigs-lista-atividades//button[contains(.,'Nova atividade')]")
        btn_nova.click()
        time.sleep(1)
        
        # Aguardar carregamento do formulário
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'pje-gigs-cadastro-atividades'))
            )
        except:
            print("[AUTOGIGS][GIGS][ERRO] Formulário de atividade não carregou")
            return False
        
        # Preencher tipo de atividade
        tipo_atividade = config.get('tipo_atividade', '')
        if tipo_atividade:
            _preencher_tipo_atividade_gigs(driver, tipo_atividade)
        
        # Preencher responsável
        responsavel = config.get('responsavel', '')
        if responsavel:
            _preencher_responsavel_gigs(driver, responsavel)
        else:
            _atribuir_responsavel_automatico(driver)
        
        # Processar variáveis especiais de audiência
        config_processado = _processar_variaveis_audiencia(driver, config)
        
        # Preencher observação
        observacao = config_processado.get('observacao', '')
        if observacao:
            observacao_final = _processar_observacao(driver, observacao)
            campo_obs = driver.find_element(By.CSS_SELECTOR, 'textarea[formcontrolname="observacao"]')
            campo_obs.clear()
            campo_obs.send_keys(observacao_final)
        
        # Preencher prazo
        prazo = config_processado.get('prazo', '')
        if prazo:
            _preencher_prazo_gigs(driver, prazo)
        
        # Salvar se configurado
        salvar = config.get('salvar', '').lower() == 'sim'
        if salvar:
            btn_salvar = driver.find_element(By.XPATH, "//button[contains(.,'Salvar')]")
            btn_salvar.click()
            
            # Aguardar confirmação de salvamento
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, "//simple-snack-bar[contains(.,'sucesso')]"))
                )
                print("[AUTOGIGS][GIGS] Atividade GIGS criada com sucesso")
                
                # Fechar notificação
                try:
                    btn_fechar = driver.find_element(By.CSS_SELECTOR, 'simple-snack-bar button')
                    btn_fechar.click()
                except:
                    pass
            except:
                print("[AUTOGIGS][GIGS][AVISO] Confirmação de salvamento não detectada")
            
            if gigs_fechado:
                _fechar_gigs(driver)
        
        return True
        
    except Exception as e:
        print(f"[AUTOGIGS][GIGS][ERRO] Falha ao adicionar atividade: {e}")
        return False

def _preencher_tipo_atividade_gigs(driver, tipo_atividade):
    """Preenche o tipo de atividade no GIGS"""
    try:
        campo_tipo = driver.find_element(By.CSS_SELECTOR, 'input[formcontrolname="tipoAtividade"]')
        campo_tipo.focus()
        
        # Simular tecla para baixo para abrir dropdown
        from selenium.webdriver.common.keys import Keys
        campo_tipo.send_keys(Keys.ARROW_DOWN)
        time.sleep(0.5)
        
        # Aguardar e clicar na opção
        opcao = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, f"//mat-option[contains(.,'{tipo_atividade}')]"))
        )
        opcao.click()
        time.sleep(0.5)
        print(f"[AUTOGIGS][GIGS] Tipo de atividade selecionado: {tipo_atividade}")
        
    except Exception as e:
        print(f"[AUTOGIGS][GIGS][ERRO] Falha ao selecionar tipo de atividade: {e}")

def _preencher_responsavel_gigs(driver, responsavel):
    """Preenche o responsável da atividade GIGS"""
    try:
        campo_resp = driver.find_element(By.CSS_SELECTOR, 'input[formcontrolname="responsavel"]')
        campo_resp.focus()
        
        from selenium.webdriver.common.keys import Keys
        campo_resp.send_keys(Keys.ARROW_DOWN)
        time.sleep(0.5)
        
        opcao = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, f"//mat-option[contains(.,'{responsavel}')]"))
        )
        opcao.click()
        time.sleep(0.5)
        print(f"[AUTOGIGS][GIGS] Responsável selecionado: {responsavel}")
        
    except Exception as e:
        print(f"[AUTOGIGS][GIGS][ERRO] Falha ao selecionar responsável: {e}")

def _atribuir_responsavel_automatico(driver):
    """Atribui responsável automaticamente"""
    try:
        # Implementar lógica de atribuição automática se necessário
        print("[AUTOGIGS][GIGS] Responsável será atribuído automaticamente pelo sistema")
    except Exception as e:
        print(f"[AUTOGIGS][GIGS][ERRO] Falha na atribuição automática: {e}")

def _processar_variaveis_audiencia(driver, config):
    """Processa variáveis especiais de audiência ([data_audi], [dados_audi], [link_audi])"""
    config_processado = config.copy()
    
    try:
        prazo = config.get('prazo', '')
        observacao = config.get('observacao', '')
        
        # Verificar se há variáveis de audiência
        if '[data_audi]' in prazo or '[data_audi]' in observacao or '[dados_audi]' in observacao or '[link_audi]' in observacao:
            # Extrair ID do processo da URL
            url = driver.current_url
            if '/processo/' in url and '/detalhe' in url:
                inicio = url.find('/processo/') + 10
                fim = url.find('/detalhe')
                processo_id = url[inicio:fim]
                
                # Tentar obter dados da audiência (implementação simplificada)
                print(f"[AUTOGIGS][GIGS] Processando variáveis de audiência para processo: {processo_id}")
                
                # Por enquanto, apenas substituir com valores padrão
                import datetime
                data_atual = datetime.datetime.now().strftime('%d/%m/%Y %H:%M')
                
                if '[data_audi]' in prazo:
                    config_processado['prazo'] = data_atual
                if '[data_audi]' in observacao:
                    config_processado['observacao'] = observacao.replace('[data_audi]', f'Data: {data_atual}')
                if '[dados_audi]' in observacao:
                    config_processado['observacao'] = config_processado['observacao'].replace('[dados_audi]', 'Audiência - Sala Virtual')
                if '[link_audi]' in observacao:
                    config_processado['observacao'] = config_processado['observacao'].replace('[link_audi]', 'Link não informado')
                    
                print("[AUTOGIGS][GIGS] Variáveis de audiência processadas")
            else:
                print("[AUTOGIGS][GIGS][AVISO] Não foi possível extrair ID do processo para variáveis de audiência")
        
    except Exception as e:
        print(f"[AUTOGIGS][GIGS][ERRO] Falha ao processar variáveis de audiência: {e}")
    
    return config_processado

def _preencher_prazo_gigs(driver, prazo):
    """Preenche o prazo da atividade GIGS"""
    try:
        if len(prazo) < 5:  # Provavelmente dias úteis
            campo_dias = driver.find_element(By.CSS_SELECTOR, 'input[formcontrolname="dias"]')
            campo_dias.clear()
            campo_dias.send_keys(prazo)
            print(f"[AUTOGIGS][GIGS] Dias úteis preenchidos: {prazo}")
        else:  # Provavelmente data específica
            campo_data = driver.find_element(By.CSS_SELECTOR, 'input[data-placeholder="Data Prazo"]')
            campo_data.clear()
            campo_data.send_keys(prazo)
            print(f"[AUTOGIGS][GIGS] Data de prazo preenchida: {prazo}")
        
        time.sleep(1)  # Aguardar cálculo do sistema
        
    except Exception as e:
        print(f"[AUTOGIGS][GIGS][ERRO] Falha ao preencher prazo: {e}")

def _definir_responsavel_processo(driver, responsavel):
    """Define o responsável pelo processo"""
    try:
        campo_resp_proc = driver.find_element(By.CSS_SELECTOR, 'input[aria-label*="Responsável"]')
        campo_resp_proc.focus()
        
        from selenium.webdriver.common.keys import Keys
        campo_resp_proc.send_keys(Keys.ARROW_DOWN)
        time.sleep(0.5)
        
        opcao = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, f"//mat-option[contains(.,'{responsavel}')]"))
        )
        opcao.click()
        time.sleep(0.5)
        print(f"[AUTOGIGS] Responsável do processo definido: {responsavel}")
        
    except Exception as e:
        print(f"[AUTOGIGS][ERRO] Falha ao definir responsável do processo: {e}")

def _processar_observacao(driver, observacao):
    """Processa observação, incluindo prompts dinâmicos"""
    try:
        if 'perguntar' in observacao:
            texto_base = observacao.replace('perguntar', '').strip()
            # Simular prompt - por enquanto retorna o texto base
            # Em uma implementação completa, poderia usar tkinter ou similar para prompt
            print(f"[AUTOGIGS] Prompt solicitado. Usando texto base: {texto_base}")
            return texto_base
        
        if 'corrigir data' in observacao:
            observacao_limpa = observacao.replace('corrigir data', '').strip()
            print(f"[AUTOGIGS] Correção de data solicitada. Usando observação: {observacao_limpa}")
            return observacao_limpa
        
        return observacao
        
    except Exception as e:
        print(f"[AUTOGIGS][ERRO] Falha ao processar observação: {e}")
        return observacao

def acao_bt_aaChecklist_selenium(driver, config):
    """
    Executa o fluxo automatizado de Checklist.
    config: dict com chaves nm_botao, tipo, observacao, estado, alerta, salvar
    """
    try:
        print(f"[CHECKLIST] Iniciando ação automatizada: {config.get('nm_botao','')} - {config.get('observacao','')}")
        
        # Marcar item no checklist
        if config.get('tipo'):
            try:
                # Procurar checkbox ou item do checklist
                item_checklist = driver.find_element(By.XPATH, f"//input[@type='checkbox' and contains(@aria-label,'{config['tipo']}')]")
                if not item_checklist.is_selected():
                    item_checklist.click()
                    print(f"[CHECKLIST] Item marcado: {config['tipo']}")
                
                # Adicionar observação se necessário
                if config.get('observacao'):
                    campo_obs = driver.find_element(By.CSS_SELECTOR, 'input[placeholder*="observação" i], textarea[placeholder*="observação" i]')
                    campo_obs.send_keys(config['observacao'])
                
                # Salvar se configurado
                if config.get('salvar', '').lower() != 'não':
                    btn_salvar = driver.find_element(By.CSS_SELECTOR, 'button[aria-label*="Salvar"]')
                    btn_salvar.click()
                    time.sleep(1)
                
            except Exception as e:
                print(f'[CHECKLIST][ERRO] {e}')
        
        return True
        
    except Exception as e:
        print(f'[CHECKLIST][ERRO] {e}')
        return False

def acao_bt_aaLancarMovimentos_selenium(driver, config):
    """
    Executa o fluxo automatizado de Lançar Movimentos.
    config: dict com chaves id, nm_botao (contendo descrição do movimento)
    """
    try:
        movimento = config.get('nm_botao', '')
        print(f"[LANCAR_MOVIMENTOS] Iniciando lançamento: {movimento}")
        
        # Abrir área de movimentos
        try:
            btn_movimentos = driver.find_element(By.XPATH, "//button[contains(.,'Movimento') or contains(.,'Lançar')]")
            btn_movimentos.click()
            time.sleep(1)
        except Exception:
            print('[LANCAR_MOVIMENTOS] Área de movimentos já aberta ou não encontrada.')
        
        # Buscar e selecionar o movimento específico
        if movimento:
            try:
                # Extrair palavras-chave do movimento
                palavras_chave = movimento.replace(':', ' ').split()
                
                for palavra in palavras_chave:
                    if len(palavra) > 3:  # Usar palavras significativas
                        try:
                            movimento_item = driver.find_element(By.XPATH, f"//div[contains(translate(.,'{palavra.upper()}','{palavra.lower()}'),'{palavra.lower()}')]")
                            movimento_item.click()
                            print(f"[LANCAR_MOVIMENTOS] Movimento selecionado: {movimento}")
                            time.sleep(0.5)
                            break
                        except:
                            continue
                
                # Confirmar lançamento
                btn_gravar = driver.find_element(By.CSS_SELECTOR, 'button[aria-label*="Gravar"], button[aria-label*="Lançar"]')
                btn_gravar.click()
                time.sleep(1)
                
                # Confirmar diálogo se aparecer
                try:
                    btn_sim = driver.find_element(By.XPATH, '//button[contains(.,"Sim") or contains(.,"Confirmar")]')
                    btn_sim.click()
                    time.sleep(0.5)
                except:
                    pass
                
            except Exception as e:
                print(f'[LANCAR_MOVIMENTOS][MOVIMENTO][ERRO] {e}')
        
        return True
        
    except Exception as e:
        print(f'[LANCAR_MOVIMENTOS][ERRO] {e}')
        return False

def acao_bt_aaMovimento_selenium(driver, config):
    """
    Executa o fluxo automatizado de Movimento (mudança de estado do processo).
    config: dict com chaves nm_botao, destino, chip, responsavel
    """
    try:
        destino = config.get('destino', '')
        print(f"[MOVIMENTO] Iniciando movimentação: {config.get('nm_botao','')} → {destino}")
        
        if destino:
            try:
                # Procurar botão de movimentação
                btn_movimento = driver.find_element(By.XPATH, f"//button[contains(.,'{destino}') or contains(@aria-label,'{destino}')]")
                btn_movimento.click()
                time.sleep(1)
                
                # Preencher responsável se necessário
                if config.get('responsavel'):
                    try:
                        select_resp = driver.find_element(By.CSS_SELECTOR, 'mat-select[placeholder*="responsável" i]')
                        select_resp.click()
                        time.sleep(0.5)
                        opcao_resp = driver.find_element(By.XPATH, f"//mat-option[contains(.,'{config['responsavel']}')]")
                        opcao_resp.click()
                    except:
                        print('[MOVIMENTO] Não foi possível selecionar responsável.')
                
                # Confirmar movimento
                btn_confirmar = driver.find_element(By.CSS_SELECTOR, 'button[aria-label*="Confirmar"], button[aria-label*="Movimentar"]')
                btn_confirmar.click()
                time.sleep(1)
                
                print(f"[MOVIMENTO] Processo movimentado para: {destino}")
                
            except Exception as e:
                print(f'[MOVIMENTO][DESTINO][ERRO] {e}')
        
        return True
        
    except Exception as e:
        print(f'[MOVIMENTO][ERRO] {e}')
        return False

def acao_bt_aaVariados_selenium(driver, config):
    """
    Executa o fluxo automatizado de Variados (funcionalidades diversas de automação).
    config: dict com chaves id, nm_botao, descricao, temporizador, ativar
    """
    try:
        acao = config.get('nm_botao', '')
        print(f"[VARIADOS] Iniciando ação automatizada: {acao}")
        
        if acao == 'Atualizar Pagina':
            driver.refresh()
            time.sleep(int(config.get('temporizador', 1)))
            print('[VARIADOS] Página atualizada.')
            
        elif acao == 'Fechar Pagina':
            driver.close()
            print('[VARIADOS] Página fechada.')
            
        elif acao == 'Apreciar Peticoes':
            try:
                btn_apreciar = driver.find_element(By.XPATH, "//button[contains(.,'Apreciar') or contains(.,'Petição')]")
                btn_apreciar.click()
                time.sleep(int(config.get('temporizador', 1)))
                print('[VARIADOS] Petições apreciadas.')
            except Exception as e:
                print(f'[VARIADOS][APRECIAR][ERRO] {e}')
                
        elif 'Atalho F' in acao:
            # Simular teclas de atalho
            from selenium.webdriver.common.keys import Keys
            tecla = acao.split()[-1]  # F2, F3, etc.
            driver.find_element(By.TAG_NAME, 'body').send_keys(getattr(Keys, tecla))
            time.sleep(int(config.get('temporizador', 2)))
            print(f'[VARIADOS] Atalho {tecla} executado.')
            
        elif acao == 'Assinar Expedientes':
            try:
                btn_assinar = driver.find_element(By.XPATH, "//button[contains(.,'Assinar') and contains(.,'Expediente')]")
                btn_assinar.click()
                time.sleep(2)
                print('[VARIADOS] Expedientes assinados em lote.')
            except Exception as e:
                print(f'[VARIADOS][ASSINAR_EXP][ERRO] {e}')
                
        elif acao == 'Assinar Documentos':
            try:
                btn_assinar_doc = driver.find_element(By.XPATH, "//button[contains(.,'Assinar') and contains(.,'Documento')]")
                btn_assinar_doc.click()
                time.sleep(2)
                print('[VARIADOS] Documentos assinados em lote.')
            except Exception as e:
                print(f'[VARIADOS][ASSINAR_DOC][ERRO] {e}')
                
        elif acao == 'Enviar Email':
            # Implementar funcionalidade de email se necessário
            print('[VARIADOS] Funcionalidade de email a ser implementada.')
            
        else:
            print(f'[VARIADOS] Ação não reconhecida: {acao}')
        
        return True
        
    except Exception as e:
        print(f'[VARIADOS][ERRO] {e}')
        return False

def acionar_botao_exec1():
    # Lógica para acionar o botão Exec1 do grupo aaAutogigs
    # Exemplo: chamar função de fluxo, automação, etc.
    print("Botão Exec1 (aaAutogigs) acionado.")
