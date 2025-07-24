"""
Módulo de utilitários para GIGS e funções auxiliares.
Extraído de listaexec.py para reduzir tamanho.
"""

import re
import json
import time
from datetime import datetime
from selenium.webdriver.common.by import By
from Fix import criar_gigs


def navegar_para_pagamentos(driver, log=True):
    """
    Navega para a tela de pagamentos usando o fluxo correto da interface:
    menu hambúrguer > botão Pagamento > aguarda nova aba com URL /cadastro ou /pagamento
    """
    try:
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        if log:
            print('[PAGAMENTO] Navegando para tela de pagamentos via interface...')
        # 1. Clicar no menu hambúrguer
        hamburger_selectors = [
            'button#botao-menu[aria-label="Menu do processo"]',
            'button[id="botao-menu"]',
            'button[aria-label="Menu do processo"]',
            'button[mattooltip="Menu do processo"]',
            'button.botao-menu[mat-icon-button]',
            'button[aria-label="Toggle sidenav"]',
            'button.mat-button.mat-icon-button.sidenav-toggle',
            'button[mattooltip="Menu lateral"]',
            'button[mat-icon-button]',
            '.sidenav-toggle'
        ]
        hamburger_button = None
        for selector in hamburger_selectors:
            try:
                hamburger_button = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                )
                break
            except:
                continue
        if not hamburger_button:
            if log:
                print('[PAGAMENTO][ERRO] Menu hambúrguer não encontrado')
            return False
        hamburger_button.click()
        time.sleep(1)
        if log:
            print('[PAGAMENTO] ✅ Menu hambúrguer clicado')
        # 2. Clicar no botão Pagamento
        try:
            pagamento_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[aria-label="Pagamento"]'))
            )
            abas_iniciais = driver.window_handles
            pagamento_button.click()
            time.sleep(2)
            if log:
                print('[PAGAMENTO] ✅ Botão Pagamento clicado')
        except Exception as e:
            if log:
                print(f'[PAGAMENTO][ERRO] Erro ao clicar no botão Pagamento: {e}')
            return False
        # 3. Trocar para nova aba se aberta
        time.sleep(3)
        abas_atuais = driver.window_handles
        if len(abas_atuais) > len(abas_iniciais):
            nova_aba = abas_atuais[-1]
            driver.switch_to.window(nova_aba)
            if log:
                print('[PAGAMENTO] ✅ Nova aba detectada, mudando para ela...')
        else:
            if log:
                print('[PAGAMENTO] 🔍 Permanecendo na aba atual...')
        # 4. Esperar URL correta
        try:
            WebDriverWait(driver, 15).until(
                lambda d: '/cadastro' in d.current_url or 'pagamento' in d.current_url
            )
            if log:
                print(f'[PAGAMENTO] ✅ Navegação concluída. URL atual: {driver.current_url}')
            return True
        except Exception as e:
            if log:
                print(f'[PAGAMENTO][ERRO] Timeout aguardando navegação para tela de pagamentos: {e}')
                print(f'[PAGAMENTO] URL atual: {driver.current_url}')
                print(f'[PAGAMENTO] Total de abas: {len(driver.window_handles)}')
            # Tentar verificar todas as abas abertas
            try:
                for i, aba in enumerate(driver.window_handles):
                    driver.switch_to.window(aba)
                    if log:
                        print(f'[PAGAMENTO] Aba {i+1}: {driver.current_url}')
                    if '/cadastro' in driver.current_url or 'pagamento' in driver.current_url:
                        if log:
                            print(f'[PAGAMENTO] ✅ Encontrada aba de pagamentos!')
                        return True
            except:
                pass
            return False
    except Exception as e:
        if log:
            print(f'[PAGAMENTO][ERRO] Erro geral na navegação para pagamentos: {e}')
        return False


def analisar_listagem_pagamentos(driver, log=True):
    """
    Analisa a listagem de pagamentos e extrai dados relevantes.
    
    Args:
        driver: WebDriver do Selenium
        log: Se deve exibir logs
        
    Returns:
        list: Lista de pagamentos encontrados
    """
    try:
        pagamentos = []
        
        # Buscar todos os mat-card-content com classe corpo
        cards_pagamento = driver.find_elements(By.CSS_SELECTOR, 'mat-card-content.mat-card-content.corpo')
        
        if log:
            print(f'[PAGAMENTO] Encontrados {len(cards_pagamento)} cards de pagamento')
        
        for index, card in enumerate(cards_pagamento):
            try:
                pagamento_data = extrair_dados_pagamento(card, index, log)
                if pagamento_data:
                    pagamentos.append(pagamento_data)
                    if log:
                        print(f'[PAGAMENTO] Pagamento {index+1}: {pagamento_data["data_pagamento"]} - {pagamento_data["credito_demandante"]}')
                
            except Exception as e:
                if log:
                    print(f'[PAGAMENTO][ERRO] Erro ao processar card {index}: {e}')
                continue
        
        return pagamentos
        
    except Exception as e:
        if log:
            print(f'[PAGAMENTO][ERRO] Erro na análise da listagem: {e}')
        return []


def extrair_dados_pagamento(card, index, log=True):
    """
    Extrai dados específicos de um card de pagamento.
    
    Args:
        card: Elemento do card de pagamento
        index: Índice do card
        log: Se deve exibir logs
        
    Returns:
        dict: Dados do pagamento ou None
    """
    try:
        dados_pagamento = {
            'index': index,
            'data_pagamento': None,
            'credito_demandante': None,
            'valor_total': None
        }
        
        # Buscar todos os dl dentro do card
        dls = card.find_elements(By.CSS_SELECTOR, 'dl.dl-rubrica')
        
        for dl in dls:
            try:
                dt = dl.find_element(By.CSS_SELECTOR, 'dt.dt-rubrica')
                dd = dl.find_element(By.CSS_SELECTOR, 'dd.dd-rubrica')
                
                campo = dt.text.strip()
                valor = dd.text.strip()
                
                if campo == 'Data do Pagamento':
                    dados_pagamento['data_pagamento'] = valor
                elif campo == 'Crédito do demandante':
                    dados_pagamento['credito_demandante'] = valor
                    # Extrair valor numérico
                    dados_pagamento['valor_total'] = converter_valor_pagamento_para_float(valor)
            
            except Exception as e:
                continue
        
        # Verificar se conseguiu extrair dados essenciais
        if dados_pagamento['data_pagamento'] and dados_pagamento['credito_demandante']:
            return dados_pagamento
        else:
            if log:
                print(f'[PAGAMENTO][AVISO] Dados insuficientes no card {index}')
            return None
            
    except Exception as e:
        if log:
            print(f'[PAGAMENTO][ERRO] Erro ao extrair dados do card {index}: {e}')
        return None


def converter_valor_pagamento_para_float(valor_str):
    """Converte valor de pagamento para float"""
    try:
        # Remove R$, &nbsp;, espaços e converte
        valor_clean = valor_str.replace('R$', '').replace('&nbsp;', '').replace(' ', '')
        valor_clean = valor_clean.replace('.', '').replace(',', '.')
        return float(valor_clean)
    except:
        return 0.0


def verificar_correspondencia_data_valor(alvara_data, alvara_valor, pagamento_data, pagamento_valor, log=True):
    """
    Verifica se há correspondência entre alvará e pagamento.
    Critérios: data igual ou diferença máxima de 5 dias, valor igual ou diferença máxima de R$ 300.
    
    Args:
        alvara_data: Data do alvará (formato dd/mm/aaaa)
        alvara_valor: Valor do alvará (float)
        pagamento_data: Data do pagamento (formato dd/mm/aaaa)
        pagamento_valor: Valor do pagamento (float)
        log: Se deve exibir logs
        
    Returns:
        bool: True se houver correspondência
    """
    try:
        # Converter datas
        try:
            alvara_date = datetime.strptime(alvara_data, '%d/%m/%Y')
            pagamento_date = datetime.strptime(pagamento_data, '%d/%m/%Y')
            
            # Calcular diferença em dias
            diferenca_dias = abs((alvara_date - pagamento_date).days)
            
        except:
            # Se não conseguir converter, considerar como não correspondente
            if log:
                print(f'[PAGAMENTO][AVISO] Erro ao converter datas: {alvara_data} / {pagamento_data}')
            return False
        
        # Calcular diferença de valores
        diferenca_valor = abs(alvara_valor - pagamento_valor)
        
        # Verificar critérios
        data_ok = diferenca_dias <= 5
        valor_ok = diferenca_valor <= 300.0
        
        if log and (data_ok or valor_ok):
            print(f'[PAGAMENTO] Comparação: Data {diferenca_dias} dias, Valor R$ {diferenca_valor:.2f}')
        
        return data_ok and valor_ok
        
    except Exception as e:
        if log:
            print(f'[PAGAMENTO][ERRO] Erro na verificação de correspondência: {e}')
        return False


def tratar_timeline(driver, itens_alvo, log=True):
    """
    Versão HÍBRIDA: Injeta JavaScript para ler a timeline rapidamente e retorna os dados para o Python processar.
    """
    try:
        if log:
            print('[LISTA-EXEC] 🚀 Injetando script JS para leitura INSTANTÂNEA da timeline...')

        # Script JavaScript para extrair dados da timeline
        script_js = """
        const itens_alvo = arguments[0];
        const resultados = [];
        const itens_timeline = document.querySelectorAll('li.tl-item-container');

        itens_timeline.forEach((item, index) => {
            try {
                const link = item.querySelector('a.tl-documento:not([target="_blank"])');
                if (!link) return;

                const textoCompleto = link.innerText.trim();
                const textoLower = textoCompleto.toLowerCase();
                
                // Extrair data
                let data = '';
                const dataEl = item.querySelector('.data-producao-documento');
                if (dataEl) {
                    data = dataEl.innerText.trim();
                }

                // Extrair ID
                let id = null;
                if (textoCompleto.includes(' - ')) {
                    id = textoCompleto.split(' - ').pop().trim();
                }

                for (const alvo of itens_alvo) {
                    for (const termo of alvo.termos) {
                        if (textoLower.includes(termo)) {
                            // Encontrou uma correspondência
                            resultados.push({
                                'nome': alvo.nome,
                                'tipo': alvo.tipo,
                                'texto_original': textoCompleto,
                                'data': data,
                                'id_timeline': id,
                                'index': index,
                                'tem_anexos': item.querySelector('pje-timeline-anexos') !== null
                            });
                            // Pula para o próximo item da timeline para não duplicar
                            return; 
                        }
                    }
                }
            } catch (e) {
                // Ignora erros em itens individuais
            }
        });

        return JSON.stringify(resultados);
        """

        # Executar o script e obter o resultado como uma string JSON
        json_resultados = driver.execute_script(script_js, itens_alvo)

        if not json_resultados:
            if log:
                print('[LISTA-EXEC] ❌ Script JS não retornou dados.')
            return []

        # Converter a string JSON de volta para uma lista de dicionários Python
        documentos_encontrados = json.loads(json_resultados)

        if log:
            print(f'[LISTA-EXEC] ✅ Leitura via JS concluída INSTANTANEAMENTE. {len(documentos_encontrados)} itens relevantes encontrados.')

        return documentos_encontrados

    except Exception as e:
        if log:
            print(f'[LISTA-EXEC][ERRO-JS] Falha ao executar script de injeção: {e}')
        return []


def gerar_gigs_final(driver, dados_gigs_final, log=True):
    """
    Gera o GIGS final consolidado com todas as medidas relevantes.
    
    Args:
        driver: WebDriver do Selenium
        dados_gigs_final: Estrutura com todos os dados coletados
        log: Se deve exibir logs
    """
    try:
        if log:
            print('[GIGS-FINAL] Gerando GIGS consolidado...')
        
        # Construir texto do GIGS
        texto_gigs = []
        
        # SEÇÃO 1: Alvarás sem registro
        if dados_gigs_final['alvaras_sem_registro']:
            texto_gigs.append("ALVARÁS:")
            for alvara in dados_gigs_final['alvaras_sem_registro']:
                linha_alvara = f"{alvara['id']}, {alvara['data']}, {alvara['valor']}"
                texto_gigs.append(linha_alvara)
            texto_gigs.append("")  # Linha em branco
        
        # SEÇÃO 2: Pesquisas (CNIB e SERASA agrupados)
        pesquisas = []
        pesquisas.extend(dados_gigs_final['cnib_anexos'])
        pesquisas.extend(dados_gigs_final['serasa_anexos'])
        
        if pesquisas:
            texto_gigs.append("PESQUISAS:")
            for pesquisa in pesquisas:
                texto_gigs.append(f"ID {pesquisa}")
            texto_gigs.append("")  # Linha em branco
        
        # SEÇÃO 3: Sobrestamentos
        if dados_gigs_final['sobrestamentos']:
            for sobrestamento in dados_gigs_final['sobrestamentos']:
                linha_sobrestamento = f"Sobrestamento ID {sobrestamento['id']} de {sobrestamento['data']}"
                texto_gigs.append(linha_sobrestamento)
            texto_gigs.append("")  # Linha em branco
        
        # Juntar tudo em um texto único
        observacao_final = "\n".join(texto_gigs).strip();
        
        if not observacao_final:
            if log:
                print('[GIGS-FINAL] Nenhuma medida relevante encontrada para o GIGS.')
            return None
        
        if log:
            print(f'[GIGS-FINAL] Texto do GIGS:\n{observacao_final}')
        
        # Criar GIGS com dias_uteis=0 e responsavel vazio
        resultado = criar_gigs(
            driver=driver,
            dias_uteis=0,
            responsavel="",
            observacao=observacao_final,
            timeout=10,
            log=log
        )
        
        if log:
            if resultado:
                print('[GIGS-FINAL] ✅ GIGS final criado com sucesso!')
            else:
                print('[GIGS-FINAL] ❌ Falha ao criar GIGS final.')
        
        return resultado
        
    except Exception as e:
        if log:
            print(f'[GIGS-FINAL][ERRO] Erro ao gerar GIGS final: {e}')
        return None
