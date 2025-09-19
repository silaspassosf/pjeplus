# processar_alvaras.py
"""
Módulo para processamento completo de alvarás
Função única que organiza todo o fluxo necessário para def prescreve
"""

def extrair_dados_alvara_detalhados(driver, alvara_info, log=True):
    """
    Extrai dados detalhados de um alvará aberto no navegador usando Fix.py
    
    Args:
        driver: WebDriver do Selenium
        alvara_info: Informações básicas do alvará da timeline
        log: Se deve exibir logs
        
    Returns:
        dict: Dados extraídos do alvará ou None se falhou
    """
    try:
        import re
        from datetime import datetime
        from Fix import extrair_pdf, formatar_moeda_brasileira
        
        if log:
            print('[EXTRAÇÃO-ALVARÁ] Extraindo dados detalhados usando extrair_pdf do Fix.py...')
        
        # Aguardar um pouco para garantir que a página carregou
        import time
        time.sleep(3)
        
        # Usar a função extrair_pdf do Fix.py em vez de extrair_direto
        texto_completo = extrair_pdf(driver, timeout=15, log=log)
        
        if not texto_completo:
            if log:
                print('[EXTRAÇÃO-ALVARÁ] ⚠️ Falha na extração usando extrair_pdf do Fix.py')
            return None
        
        if log:
            print(f'[EXTRAÇÃO-ALVARÁ] ✅ Texto extraído com sucesso: {len(texto_completo)} caracteres')
        
        # Dados básicos do alvará
        dados = {
            'texto_timeline': alvara_info.get('texto', ''),
            'data_timeline': alvara_info.get('data', ''),
            'texto_completo': texto_completo,
            'texto_bruto': texto_completo,  # Para extrair_pdf, texto bruto = texto completo
            'info_documento': {'metodo': 'extrair_pdf'},
            'url_documento': driver.current_url,
            'metodo_extracao': 'extrair_pdf do Fix.py'
        }
        
        # Usar padrões aprimorados para extrair dados específicos do alvará
        
        # === EXTRAIR VALOR MONETÁRIO ===
        valores_encontrados = []
        patterns_valor = [
            r'Valor\.*\s*R\$\s*([0-9]{1,3}(?:\.[0-9]{3})*(?:,[0-9]{2})?)',  # Valor......... R$ 47.586,17
            r'R\$\s*([0-9]{1,3}(?:\.[0-9]{3})*(?:,[0-9]{2})?)',  # R$ 1.234,56
            r'valor\s*de\s*R\$\s*([0-9.,]+)',  # valor de R$ 1234,56
            r'quantia\s*de\s*R\$\s*([0-9.,]+)',  # quantia de R$ 1234,56
            r'importância\s*de\s*R\$\s*([0-9.,]+)',  # importância de R$ 1234,56
            r'([0-9]{1,3}(?:\.[0-9]{3})*(?:,[0-9]{2})?)\s*reais',  # 1.234,56 reais
            r'no\s*valor\s*de\s*R\$\s*([0-9.,]+)',  # no valor de R$ 1234,56
            r'libere\s*R\$\s*([0-9.,]+)',  # libere R$ 1234,56
            r'autorizo.*?R\$\s*([0-9.,]+)',  # autorizo ... R$ 1234,56
            r'Total\s*de\s*Pagamentos.*?([0-9]{1,3}(?:\.[0-9]{3})*(?:,[0-9]{2})?)',  # Total de Pagamentos Informados no Mandado: 001
        ]
        
        for pattern in patterns_valor:
            matches = re.findall(pattern, texto_completo, re.IGNORECASE | re.DOTALL)
            valores_encontrados.extend(matches)
        
        # Processar valores usando função do Fix.py e pagamento.py
        if valores_encontrados:
            valores_processados = []
            for valor_str in valores_encontrados:
                try:
                    # Usar função do Fix.py para processar moeda
                    valor_formatado = formatar_moeda_brasileira(valor_str)
                    if valor_formatado and valor_formatado != "R$ 0,00":
                        # Converter para float usando função do pagamento.py
                        try:
                            from pagamento import converter_valor_pagamento_para_float
                            valor_numerico = converter_valor_pagamento_para_float(f"R$ {valor_str}")
                        except:
                            # Fallback manual
                            valor_numerico = float(valor_str.replace('.', '').replace(',', '.'))
                        
                        valores_processados.append((valor_numerico, valor_str, valor_formatado))
                except:
                    continue
            
            if valores_processados:
                # Usar o maior valor encontrado
                maior_valor = max(valores_processados, key=lambda x: x[0])
                dados['valor'] = maior_valor[1]  # Valor original
                dados['valor_formatado'] = maior_valor[2]  # Valor formatado
                dados['valor_numerico'] = maior_valor[0]  # Valor numérico
        
        # === EXTRAIR BENEFICIÁRIO/FAVORECIDO ===
        beneficiario_patterns = [
            # Padrão específico da imagem: "Beneficiário...... NOME" (para antes do CPF)
            r'Beneficiário\.+\s*([A-ZÁÀÂÃÉÊÇÍÓÔÕÚ][A-ZÁÀÂÃÉÊÇÍÓÔÕÚ\s]+?)(?:\s+CPF|\s*\n)',
            r'Beneficiario\.+\s*([A-ZÁÀÂÃÉÊÇÍÓÔÕÚ][A-ZÁÀÂÃÉÊÇÍÓÔÕÚ\s]+?)(?:\s+CPF|\s*\n)',
            # Outros padrões
            r'em\s+favor\s+de\s+([^,\n.;]+?)(?:\s*[-,\n.]|$)',
            r'beneficiário[:\s]+([^,\n.;]+?)(?:\s*[-,\n.]|$)',
            r'favorecido[:\s]+([^,\n.;]+?)(?:\s*[-,\n.]|$)',
            r'libere\s+para\s+([^,\n.;]+?)(?:\s*[-,\n.]|$)',
            r'autorizo.*?para\s+([^,\n.;]+?)(?:\s*[-,\n.]|$)',
            r'pague\s+a\s+([^,\n.;]+?)(?:\s*[-,\n.]|$)',
            r'(?:Sr\.|Sra\.|Nome:)\s*([^,\n.;]+?)(?:\s*[-,\n.]|$)',
        ]
        
        for pattern in beneficiario_patterns:
            match = re.search(pattern, texto_completo, re.IGNORECASE | re.DOTALL)
            if match:
                beneficiario = match.group(1).strip()
                # Limpar e validar beneficiário
                beneficiario = re.sub(r'\s+', ' ', beneficiario)
                if (len(beneficiario) > 3 and 
                    not any(palavra in beneficiario.lower() for palavra in 
                           ['processo', 'autos', 'juiz', 'vara', 'tribunal', 'cpf', 'cnpj', 'rg'])):
                    dados['beneficiario'] = beneficiario
                    break
        
        # === EXTRAIR CPF/CNPJ ===
        documento_patterns = [
            r'CPF[:\s]*([0-9]{3}\.?[0-9]{3}\.?[0-9]{3}-?[0-9]{2})',
            r'CNPJ[:\s]*([0-9]{2}\.?[0-9]{3}\.?[0-9]{3}/?[0-9]{4}-?[0-9]{2})',
            r'(?:portador\s+do\s+)?CPF\s*(?:n[º°]?)?\s*([0-9]{3}\.?[0-9]{3}\.?[0-9]{3}-?[0-9]{2})',
            r'([0-9]{3}\.?[0-9]{3}\.?[0-9]{3}-?[0-9]{2})',  # CPF sem prefixo
            r'([0-9]{2}\.?[0-9]{3}\.?[0-9]{3}/?[0-9]{4}-?[0-9]{2})',  # CNPJ sem prefixo
        ]
        
        for pattern in documento_patterns:
            match = re.search(pattern, texto_completo, re.IGNORECASE)
            if match:
                documento = match.group(1)
                documento_limpo = re.sub(r'[^\d]', '', documento)
                if len(documento_limpo) == 11:
                    dados['cpf'] = documento
                    break
                elif len(documento_limpo) == 14:
                    dados['cnpj'] = documento
                    break
        
        # === EXTRAIR DATA DO ALVARÁ ===
        data_patterns = [
            r'Data\s+da\s+Expedição:\s*(\d{1,2})[/-](\d{1,2})[/-](\d{4})',  # Data da Expedição: 12/04/2022
            r'Data\s+da\s+Expedição:\s*(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})',  # Data da Expedição: 12 de abril de 2022
            r'(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})',  # 12 de janeiro de 2024
            r'(\d{1,2})[/-](\d{1,2})[/-](\d{4})',  # 12/01/2024
            r'em\s+(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})',
            r'data:\s*(\d{1,2})[/-](\d{1,2})[/-](\d{4})',
        ]
        
        meses = {
            'janeiro': '01', 'fevereiro': '02', 'março': '03', 'abril': '04',
            'maio': '05', 'junho': '06', 'julho': '07', 'agosto': '08',
            'setembro': '09', 'outubro': '10', 'novembro': '11', 'dezembro': '12'
        }
        
        for pattern in data_patterns:
            match = re.search(pattern, texto_completo, re.IGNORECASE)
            if match:
                if '\\w+' in pattern:  # Formato com mês por extenso
                    dia = match.group(1).zfill(2)
                    mes_nome = match.group(2).lower()
                    ano = match.group(3)
                    mes = meses.get(mes_nome, '01')
                    dados['data_alvara'] = f"{dia}/{mes}/{ano}"
                else:  # Formato numérico
                    dia = match.group(1).zfill(2)
                    mes = match.group(2).zfill(2)
                    ano = match.group(3)
                    dados['data_alvara'] = f"{dia}/{mes}/{ano}"
                break
        
        # === EXTRAIR INFORMAÇÕES BANCÁRIAS ===
        banco_patterns = [
            r'banco[:\s]+([^,\n.;]+?)(?:\s*[-,\n.]|agência)',
            r'agência[:\s]*([0-9-]+)',
            r'conta[:\s]*([0-9-]+)',
            r'pix[:\s]*([^,\n.;]+?)(?:\s*[-,\n.]|$)',
        ]
        
        for pattern in banco_patterns:
            match = re.search(pattern, texto_completo, re.IGNORECASE)
            if match:
                valor = match.group(1).strip()
                if 'banco' in pattern:
                    dados['banco'] = valor
                elif 'agência' in pattern or 'agencia' in pattern:
                    dados['agencia'] = valor
                elif 'conta' in pattern:
                    dados['conta'] = valor
                elif 'pix' in pattern:
                    dados['pix'] = valor
        
        if log:
            print(f'[EXTRAÇÃO-ALVARÁ] ✅ Dados extraídos usando {dados.get("metodo_extracao", "Fix.py")}:')
            print(f'[EXTRAÇÃO-ALVARÁ]   - Valor: {dados.get("valor_formatado", dados.get("valor", "N/A"))}')
            print(f'[EXTRAÇÃO-ALVARÁ]   - Beneficiário: {dados.get("beneficiario", "N/A")}')
            print(f'[EXTRAÇÃO-ALVARÁ]   - CPF/CNPJ: {dados.get("cpf", dados.get("cnpj", "N/A"))}')
            print(f'[EXTRAÇÃO-ALVARÁ]   - Data: {dados.get("data_alvara", "N/A")}')
            print(f'[EXTRAÇÃO-ALVARÁ]   - Banco: {dados.get("banco", "N/A")}')
        
        return dados
        
    except Exception as e:
        if log:
            print(f'[EXTRAÇÃO-ALVARÁ] ❌ Erro na extração usando Fix.py: {e}')
        return None

def processar_alvaras_completo(driver, alvaras_encontrados=None, log=True):
    """
    Função única que processa completamente alvarás encontrados na timeline.
    
    Fluxo completo:
    1. Se alvaras_encontrados não fornecido, busca alvarás na timeline
    2. Extrai conteúdo e dados detalhados de todos os alvarás
    3. Abre aba de pagamentos para comparação
    4. Registra alvarás não registrados
    
    Args:
        driver: WebDriver do Selenium
        alvaras_encontrados: Lista opcional de alvarás já localizados da função prescreve
                           Formato: [{'elemento': element, 'link': link, 'data': data, 'texto': texto}, ...]
        log: Se deve exibir logs
        
    Returns:
        dict: {
            'alvaras_processados': [...],
            'alvaras_registrados': [...],
            'alvaras_sem_registro': [...],
            'sucesso': bool
        }
    """
    try:
        from datetime import datetime
        import time
        import re
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.common.keys import Keys
        
        if log:
            print('[PROCESSAR-ALVARAS] 🚀 Iniciando processamento completo de alvarás...')
        
        resultado = {
            'alvaras_processados': [],
            'alvaras_registrados': [],
            'alvaras_sem_registro': [],
            'sucesso': False
        }
        
        # ===== ETAPA 1: USAR ALVARÁS FORNECIDOS PELA FUNÇÃO PRESCREVE =====
        if not alvaras_encontrados:
            if log:
                print('[PROCESSAR-ALVARAS] ⚠️ Nenhum alvará fornecido pela função prescreve')
            return resultado
        
        if log:
            print(f'[PROCESSAR-ALVARAS] 📋 {len(alvaras_encontrados)} alvará(s) fornecidos para processar')
        
        # ===== ETAPA 2: CLICAR EM CADA ALVARÁ PARA ABRIR E EXTRAIR DADOS =====
        if log:
            print('[PROCESSAR-ALVARAS] 2. Clicando nos alvarás para extrair dados detalhados...')
        
        alvaras_processados = []
        
        for idx, alvara_info in enumerate(alvaras_encontrados):
            try:
                if log:
                    print(f'[PROCESSAR-ALVARAS] 2.{idx+1}. Processando alvará: {alvara_info.get("texto", "N/A")}')
                
                # Localizar e clicar no alvará usando o ID
                alvara_id = alvara_info.get('id', '')
                if not alvara_id:
                    if log:
                        print(f'[PROCESSAR-ALVARAS] ⚠️ ID do alvará não encontrado, pulando...')
                    continue
                
                # Script para localizar e clicar no alvará na timeline
                script_clicar_alvara = f"""
                // Localizar alvará por ID na timeline
                const seletores = ['li.tl-item-container', '.tl-data .tl-item-container', '.timeline-item'];
                let itens = [];
                for (const sel of seletores) {{
                    itens = document.querySelectorAll(sel);
                    if (itens.length) break;
                }}
                
                function extrairUid(link) {{
                    const m = link.textContent.trim().match(/\\s-\\s([A-Za-z0-9]+)$/);
                    return m ? m[1] : null;
                }}
                
                // Procurar o item com o ID específico
                for (let item of itens) {{
                    const link = item.querySelector('a.tl-documento:not([target])');
                    if (!link) continue;
                    
                    const itemId = extrairUid(link) || '';
                    if (itemId === '{alvara_id}') {{
                        // Fazer scroll para o elemento
                        item.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
                        
                        // Destacar o elemento temporariamente
                        item.style.outline = '3px solid #007bff';
                        item.style.background = '#e7f3ff';
                        
                        // Clicar no link do alvará
                        link.dispatchEvent(new MouseEvent('click', {{ bubbles: true }}));
                        
                        // Remover destaque após 2 segundos
                        setTimeout(() => {{
                            item.style.outline = '';
                            item.style.background = '';
                        }}, 2000);
                        
                        return true;
                    }}
                }}
                return false;
                """
                
                # Executar script para clicar no alvará
                sucesso_clique = driver.execute_script(script_clicar_alvara)
                
                if not sucesso_clique:
                    if log:
                        print(f'[PROCESSAR-ALVARAS] ❌ Não foi possível localizar/clicar no alvará ID: {alvara_id}')
                    continue
                
                if log:
                    print(f'[PROCESSAR-ALVARAS] ✅ Alvará clicado, aguardando abertura...')
                
                # Aguardar abertura do documento
                time.sleep(2)
                
                # Aguardar página carregar completamente
                try:
                    WebDriverWait(driver, 10).until(
                        lambda d: d.execute_script("return document.readyState") == "complete"
                    )
                except:
                    pass
                
                # Extrair dados detalhados do alvará aberto
                dados_alvara = extrair_dados_alvara_detalhados(driver, alvara_info, log=log)
                
                if dados_alvara:
                    dados_alvara['id'] = alvara_id
                    dados_alvara['timestamp'] = datetime.now().isoformat()
                    dados_alvara['status'] = 'EXTRAIDO_COM_SUCESSO'
                    dados_alvara['origem'] = 'prescreve'
                    alvaras_processados.append(dados_alvara)
                    
                    if log:
                        print(f'[PROCESSAR-ALVARAS] ✅ Dados extraídos: Valor: {dados_alvara.get("valor", "N/A")}, '
                              f'Beneficiário: {dados_alvara.get("beneficiario", "N/A")}')
                else:
                    if log:
                        print(f'[PROCESSAR-ALVARAS] ⚠️ Não foi possível extrair dados detalhados do alvará')
                
                # Voltar para a timeline (fechar documento se necessário)
                if 'detalhe' not in driver.current_url:
                    driver.back()
                    time.sleep(1)
                    
            except Exception as e:
                if log:
                    print(f'[PROCESSAR-ALVARAS] ❌ Erro ao processar alvará {idx+1}: {e}')
                continue
        
        resultado['alvaras_processados'] = alvaras_processados
        
        if not alvaras_processados:
            if log:
                print('[PROCESSAR-ALVARAS] ⚠️ Nenhum alvará foi processado com sucesso')
            return resultado
        
        # ===== ETAPA 3: NAVEGAR PARA PAGAMENTOS =====
        if log:
            print('[PROCESSAR-ALVARAS] 3. Navegando para aba de pagamentos...')
        
        pagamentos_sucesso = False
        try:
            # ===== SUB-ETAPA 3.1: ABRIR MENU HAMBÚRGUER =====
            if log:
                print('[PROCESSAR-ALVARAS] 3.1. Abrindo menu hambúrguer...')
            
            hamburger_selectors = [
                'button#botao-menu[aria-label="Menu do processo"]',
                'button[aria-label="Menu do processo"]',
                'button.mat-icon-button i.fa-bars',
                '.fa-bars'
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
            
            if hamburger_button:
                hamburger_button.click()
                time.sleep(1)
                if log:
                    print('[PROCESSAR-ALVARAS] ✅ Menu hambúrguer clicado')
                
                # ===== SUB-ETAPA 3.2: CLICAR NO BOTÃO PAGAMENTO =====
                if log:
                    print('[PROCESSAR-ALVARAS] 3.2. Clicando no botão Pagamento...')
                
                pagamento_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[aria-label="Pagamento"]'))
                )
                
                # Armazenar abas atuais
                abas_iniciais = driver.window_handles
                
                pagamento_button.click()
                time.sleep(3)
                
                # Verificar se nova aba foi aberta
                abas_atuais = driver.window_handles
                if len(abas_atuais) > len(abas_iniciais):
                    nova_aba = abas_atuais[-1]
                    driver.switch_to.window(nova_aba)
                    if log:
                        print('[PROCESSAR-ALVARAS] ✅ Nova aba de pagamentos aberta')
                
                # Aguardar URL de pagamentos
                WebDriverWait(driver, 15).until(
                    lambda d: '/cadastro' in d.current_url or 'pagamento' in d.current_url
                )
                
                pagamentos_sucesso = True
                if log:
                    print('[PROCESSAR-ALVARAS] ✅ Navegação para pagamentos bem-sucedida')
                    
            else:
                if log:
                    print('[PROCESSAR-ALVARAS] ❌ Menu hambúrguer não encontrado')
                
        except Exception as e:
            if log:
                print(f'[PROCESSAR-ALVARAS] ❌ Erro na navegação para pagamentos: {e}')
        
        # ===== ETAPA 4: ANALISAR PAGAMENTOS (SIMPLIFICADO) =====
        if pagamentos_sucesso:
            if log:
                print('[PROCESSAR-ALVARAS] 4. Analisando listagem de pagamentos...')
            
            try:
                # Aguardar página carregar
                time.sleep(3)
                
                # Verificar se há cards de pagamento usando a estrutura HTML real do PJe
                cards_pagamento = []
                
                # Script JavaScript para detectar pagamentos com precisão
                script_verificar_pagamentos = """
                // Verificar se existe mensagem de "sem pagamentos"
                const cardVazio = document.querySelector('mat-card.card-tabela-vazia');
                if (cardVazio && cardVazio.textContent.includes('Não há pagamento para ser exibido')) {
                    return { tipo: 'sem_pagamentos', quantidade: 0, detalhes: 'Mensagem: Não há pagamento para ser exibido' };
                }
                
                // Verificar se existem pagamentos dentro de pje-pagamento-listagem
                const pjeListagem = document.querySelector('pje-pagamento-listagem');
                if (pjeListagem) {
                    // Contar apenas cards que NÃO são card-tabela-vazia
                    const cardsTabela = pjeListagem.querySelectorAll('mat-card.card-tabela:not(.card-tabela-vazia)');
                    
                    // Extrair informações resumidas de cada card
                    const detalhesCards = [];
                    cardsTabela.forEach((card, index) => {
                        const credor = card.querySelector('.credor .dd-cabecalho')?.textContent?.trim() || 'N/A';
                        const total = card.querySelector('.dl-valor .dd-cabecalho')?.textContent?.trim() || 'N/A';
                        const dataPagamento = card.querySelector('.dl-rubrica .dd-rubrica')?.textContent?.trim() || 'N/A';
                        
                        detalhesCards.push({
                            indice: index + 1,
                            credor: credor,
                            total: total,
                            data: dataPagamento
                        });
                    });
                    
                    return { 
                        tipo: 'com_pagamentos', 
                        quantidade: cardsTabela.length,
                        detalhes: detalhesCards
                    };
                }
                
                // Fallback: verificar por cards genéricos mas filtrar corretamente
                const todosCards = document.querySelectorAll('mat-card');
                let cardsPagamentoCount = 0;
                const detalhesCards = [];
                
                for (const card of todosCards) {
                    const texto = card.textContent.toLowerCase();
                    
                    // Excluir explicitamente cards que não são pagamentos
                    if (texto.includes('não há pagamento') || 
                        texto.includes('menu') || 
                        texto.includes('navegação') ||
                        card.classList.contains('card-tabela-vazia') ||
                        card.classList.contains('navigation-card') ||
                        card.classList.contains('info-card')) {
                        continue;
                    }
                    
                    // Verificar se contém dados típicos de pagamento (credor + valor + data)
                    const temCredor = texto.includes('credor') || texto.includes('beneficiário');
                    const temValor = texto.includes('r$') || texto.includes('total:');
                    const temData = texto.includes('data do pagamento');
                    
                    if (temCredor && temValor && temData) {
                        cardsPagamentoCount++;
                        detalhesCards.push({
                            indice: cardsPagamentoCount,
                            tipo: 'detectado_por_conteudo'
                        });
                    }
                }
                
                return { 
                    tipo: 'detectado_js', 
                    quantidade: cardsPagamentoCount,
                    detalhes: detalhesCards
                };
                """
                
                try:
                    resultado_deteccao = driver.execute_script(script_verificar_pagamentos)
                    
                    if resultado_deteccao['tipo'] == 'sem_pagamentos':
                        cards_pagamento = []
                        if log:
                            print('[PROCESSAR-ALVARAS] ✅ Detectado: "Não há pagamento para ser exibido"')
                            print(f'[PROCESSAR-ALVARAS]    Detalhes: {resultado_deteccao["detalhes"]}')
                            
                    elif resultado_deteccao['tipo'] == 'com_pagamentos':
                        num_pagamentos = resultado_deteccao['quantidade']
                        cards_pagamento = [f"pagamento_{i}" for i in range(num_pagamentos)]
                        
                        if log:
                            print(f'[PROCESSAR-ALVARAS] ✅ Detectado: {num_pagamentos} pagamento(s) em pje-pagamento-listagem')
                            for detalhe in resultado_deteccao['detalhes']:
                                print(f'[PROCESSAR-ALVARAS]    Card {detalhe["indice"]}: {detalhe["credor"]} - {detalhe["total"]} - {detalhe["data"]}')
                                
                    else:
                        # Fallback com JavaScript melhorado
                        num_pagamentos = resultado_deteccao['quantidade']
                        cards_pagamento = [f"pagamento_{i}" for i in range(num_pagamentos)] if num_pagamentos > 0 else []
                        
                        if log:
                            print(f'[PROCESSAR-ALVARAS] 🔍 JavaScript (fallback) detectou: {num_pagamentos} pagamento(s)')
                            if resultado_deteccao['detalhes']:
                                for detalhe in resultado_deteccao['detalhes']:
                                    print(f'[PROCESSAR-ALVARAS]    Card {detalhe["indice"]}: {detalhe["tipo"]}')
                            
                except Exception as e:
                    if log:
                        print(f'[PROCESSAR-ALVARAS] ⚠️ Erro na detecção JavaScript: {e}')
                    
                    # Fallback simples: usar seletores diretos
                    try:
                        # Primeiro verificar mensagem de sem pagamentos
                        cards_vazios = driver.find_elements(By.CSS_SELECTOR, 'mat-card.card-tabela-vazia')
                        if cards_vazios and any('Não há pagamento' in card.text for card in cards_vazios):
                            cards_pagamento = []
                            if log:
                                print('[PROCESSAR-ALVARAS] ✅ Fallback: Encontrada mensagem "sem pagamentos"')
                        else:
                            # Contar cards dentro de pje-pagamento-listagem
                            cards_listagem = driver.find_elements(By.CSS_SELECTOR, 'pje-pagamento-listagem mat-card.card-tabela:not(.card-tabela-vazia)')
                            cards_pagamento = cards_listagem
                            if log:
                                print(f'[PROCESSAR-ALVARAS] ✅ Fallback: {len(cards_pagamento)} card(s) de pagamento encontrados')
                    except Exception as fallback_error:
                        cards_pagamento = []
                        if log:
                            print(f'[PROCESSAR-ALVARAS] ❌ Fallback falhou: {fallback_error}')
                            print('[PROCESSAR-ALVARAS] ⚠️ Assumindo sem pagamentos')
                
                if cards_pagamento:
                    if log:
                        print(f'[PROCESSAR-ALVARAS] 📋 {len(cards_pagamento)} card(s) de pagamento encontrado(s)')
                    
                    # Usar as funções do pagamento.py para análise detalhada
                    try:
                        from pagamento import analisar_listagem_pagamentos, comparar_alvaras_com_pagamentos
                        
                        # Analisar pagamentos usando a função especializada
                        pagamentos_detalhados = analisar_listagem_pagamentos(driver, log=log)
                        
                        if pagamentos_detalhados:
                            if log:
                                print(f'[PROCESSAR-ALVARAS] 🔍 Dados extraídos de {len(pagamentos_detalhados)} pagamento(s):')
                                for i, pag in enumerate(pagamentos_detalhados):
                                    print(f'[PROCESSAR-ALVARAS]    {i+1}. {pag.get("data_pagamento", "N/A")} - {pag.get("credito_demandante", "N/A")}')
                            
                            # Comparar alvarás processados com pagamentos encontrados
                            comparar_alvaras_com_pagamentos(alvaras_processados, pagamentos_detalhados, log=log)
                            
                            # Classificar alvarás baseado na comparação
                            resultado['alvaras_registrados'] = [alv for alv in alvaras_processados if alv.get('status') == 'ALVARA REGISTRADO']
                            resultado['alvaras_sem_registro'] = [alv for alv in alvaras_processados if alv.get('status') == 'SEM REGISTRO']
                            
                        else:
                            if log:
                                print('[PROCESSAR-ALVARAS] ⚠️ Nenhum dado de pagamento extraído')
                            resultado['alvaras_sem_registro'] = alvaras_processados.copy()
                    
                    except ImportError as e:
                        if log:
                            print(f'[PROCESSAR-ALVARAS] ⚠️ Não foi possível importar funções de pagamento.py: {e}')
                            print('[PROCESSAR-ALVARAS] Usando lógica simplificada...')
                        
                        # Fallback: lógica simplificada
                        resultado['alvaras_registrados'] = alvaras_processados[:len(cards_pagamento)//2]
                        resultado['alvaras_sem_registro'] = alvaras_processados[len(cards_pagamento)//2:]
                    
                    except Exception as e:
                        if log:
                            print(f'[PROCESSAR-ALVARAS] ❌ Erro na análise detalhada de pagamentos: {e}')
                        resultado['alvaras_sem_registro'] = alvaras_processados.copy()
                else:
                    if log:
                        print('[PROCESSAR-ALVARAS] ⚠️ Nenhum pagamento encontrado')
                    resultado['alvaras_sem_registro'] = alvaras_processados.copy()
                    
            except Exception as e:
                if log:
                    print(f'[PROCESSAR-ALVARAS] ❌ Erro ao analisar pagamentos: {e}')
                resultado['alvaras_sem_registro'] = alvaras_processados.copy()
        else:
            resultado['alvaras_sem_registro'] = alvaras_processados.copy()
        
        # ===== ETAPA 5: REGISTRAR ALVARÁS NÃO REGISTRADOS =====
        if resultado['alvaras_sem_registro']:
            if log:
                print(f'[PROCESSAR-ALVARAS] 5. Marcando {len(resultado["alvaras_sem_registro"])} alvará(s) para registro...')
            
            for alvara in resultado['alvaras_sem_registro']:
                alvara['status'] = 'AGUARDANDO_REGISTRO'
                if log:
                    print(f'[PROCESSAR-ALVARAS] 📝 Marcado para registro: {alvara.get("texto_timeline", "N/A")}')
        
        # ===== FINALIZAÇÃO =====
        resultado['sucesso'] = True
        
        if log:
            print('[PROCESSAR-ALVARAS] 📊 RESUMO FINAL:')
            print(f'[PROCESSAR-ALVARAS]   - Alvarás processados: {len(resultado["alvaras_processados"])}')
            print(f'[PROCESSAR-ALVARAS]   - Alvarás já registrados: {len(resultado["alvaras_registrados"])}')
            print(f'[PROCESSAR-ALVARAS]   - Alvarás sem registro: {len(resultado["alvaras_sem_registro"])}')
            print('[PROCESSAR-ALVARAS] ✅ Processamento completo finalizado!')
        
        return resultado
        
    except Exception as e:
        if log:
            print(f'[PROCESSAR-ALVARAS] ❌ Erro geral no processamento: {e}')
        
        resultado['sucesso'] = False
        return resultado
