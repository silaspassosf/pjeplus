# ====================================================
# FUNÇÃO DADOBLOQ - EXTRAÇÃO SISBAJUD /DESDOBRAR
# ====================================================

# Dados globais para armazenar até fechar driver
dados_ordem_global = {}
dados_executados_global = {}

def dadobloq(driver, log=True):
    """
    Extrai dados da página /desdobrar do SISBAJUD
    - Protocolo e data da ordem do card principal
    - Executados com valores bloqueados dos painéis de expansão
    - Apenas valores > 0
    """
    global dados_ordem_global, dados_executados_global

    # Verificar URL
    if '/desdobrar' not in driver.current_url:
        if log:
            print('[DADOBLOQ] ❌ Página deve ser /desdobrar')
        return {'sucesso': False, 'erro': 'Página incorreta'}

    if log:
        print('[DADOBLOQ] 🔍 Extraindo dados SISBAJUD...')

    try:
        from selenium.webdriver.common.by import By
        import time

        time.sleep(1)

        # === 1. EXTRAIR DADOS DO CARD PRINCIPAL ===
        dados_ordem = {}

        # Protocolo
        try:
            protocolo_el = driver.find_element(By.XPATH, "//span[contains(text(), 'Número do Protocolo:')]/following-sibling::span")
            protocolo = protocolo_el.text.strip()
            dados_ordem['protocolo'] = protocolo
            if log:
                print(f'[DADOBLOQ] 📋 Protocolo: {protocolo}')
        except:
            if log:
                print('[DADOBLOQ] ⚠️ Protocolo não encontrado')

        # Data da ordem (24 JUL 2025 15:34 → 24/07/2025)
        try:
            data_el = driver.find_element(By.XPATH, "//span[contains(text(), 'Data/hora do Protocolamento:')]/following-sibling::span")
            data_texto = data_el.text.strip()  # "24 JUL 2025 15:34"

            # Converter formato
            meses = {
                'JAN': '01', 'FEB': '02', 'MAR': '03', 'APR': '04', 'MAY': '05', 'JUN': '06',
                'JUL': '07', 'AUG': '08', 'SEP': '09', 'OCT': '10', 'NOV': '11', 'DEC': '12'
            }

            partes = data_texto.split()
            if len(partes) >= 3:
                dia = partes[0].zfill(2)
                mes = meses.get(partes[1].upper(), '01')
                ano = partes[2]
                data_formatada = f"{dia}/{mes}/{ano}"
                dados_ordem['data_ordem'] = data_formatada
                if log:
                    print(f'[DADOBLOQ] 📅 Data: {data_formatada}')
        except:
            if log:
                print('[DADOBLOQ] ⚠️ Data não encontrada')

        # Atualizar dados globais da ordem
        dados_ordem_global = dados_ordem

        # === 2. EXTRAIR EXECUTADOS DOS PAINÉIS ===
        executados = []

        # Encontrar todos os painéis de expansão
        paineis = driver.find_elements(By.CSS_SELECTOR, 'mat-expansion-panel-header')

        if log:
            print(f'[DADOBLOQ] 📊 Encontrados {len(paineis)} painéis')

        for painel in paineis:
            try:
                # Nome do executado
                nome_el = painel.find_element(By.CSS_SELECTOR, '.col-reu-dados-nome-pessoa')
                nome = nome_el.text.strip()

                # Documento do executado
                doc_el = painel.find_element(By.CSS_SELECTOR, '.col-reu-dados a')
                documento = doc_el.text.strip()

                # Valor bloqueado do description
                desc_el = painel.find_element(By.CSS_SELECTOR, '.mat-expansion-panel-header-description span')
                valor_texto = desc_el.text.strip()

                # Extrair valor numérico (R$ 244,05 → 244.05)
                if 'R$' in valor_texto:
                    valor_str = valor_texto.split('R$')[1].split('(')[0].strip()
                    valor_str = valor_str.replace('.', '').replace(',', '.')
                    try:
                        valor = float(valor_str)
                        # Apenas valores > 0
                        if valor > 0:
                            executado = {
                                'nome': nome,
                                'documento': documento,
                                'valor_bloqueado': valor,
                                'ordem': dados_ordem.get('protocolo', ''),
                                'data_ordem': dados_ordem.get('data_ordem', '')
                            }
                            executados.append(executado)

                            if log:
                                print(f'[DADOBLOQ] ✅ {nome} - {documento}: R$ {valor:.2f}')
                    except:
                        continue

            except Exception as e:
                if log:
                    print(f'[DADOBLOQ] ⚠️ Erro ao processar painel: {str(e)}')
                continue

        # Adicionar aos dados globais
        dados_executados_global.extend(executados)

        if log:
            print(f'[DADOBLOQ] 📈 Extraídos: {len(executados)} executados válidos')
            print(f'[DADOBLOQ] 📈 Total global: {len(dados_executados_global)}')

        return {
            'sucesso': True,
            'ordem': dados_ordem,
            'executados': executados,
            'total_executados': len(executados),
            'total_global': len(dados_executados_global)
        }

    except Exception as e:
        erro = f'Erro na extração: {str(e)}'
        if log:
            print(f'[DADOBLOQ] ❌ {erro}')
        return {'sucesso': False, 'erro': erro}

# ====================================================
# FUNÇÃO PARA GERAR TEXTO DE SAÍDA FORMATADO
# Baseado na formatação do testo.js
# ====================================================

def gerar_texto_saida():
    """
    Gera texto de saída formatado baseado nos dados extraídos
    Usa formatação similar ao testo.js
    """
    if not dados_executados_global:
        return "Nenhum dado de bloqueio extraído."

    # Funções de formatação (baseado no testo.js)
    def formatar_valor_br(valor_num):
        """Formata valor para padrão brasileiro"""
        return f"{valor_num:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    def get_data_atual_br():
        """Retorna data atual em formato brasileiro"""
        from datetime import datetime
        hoje = datetime.now()
        return hoje.strftime("%d/%m/%Y")

    # Agrupar por executado
    executados_agrupados = {}
    total_geral = 0.0

    for item in dados_executados_global:
        nome = item['nome']
        if nome not in executados_agrupados:
            executados_agrupados[nome] = {
                'documento': item['documento'],
                'bloqueios': []
            }

        executados_agrupados[nome]['bloqueios'].append({
            'ordem': item['ordem'],
            'data': item['data_ordem'],
            'valor': item['valor_bloqueado']
        })

        total_geral += item['valor_bloqueado']

    # Estilos baseados no testo.js
    p_style = 'class="corpo" style="font-size:12pt;line-height:1.5;margin-left:0 !important;text-align:justify !important;text-indent:4.5cm;"'
    p_style_center = 'class="corpo" style="font-size:12pt;line-height:1.5;margin-left:0 !important;text-align:center;text-indent:4.5cm;"'

    # Gerar HTML formatado (como testo.js)
    resultado = f'<p {p_style_center}><strong>Discriminação dos bloqueios realizados</strong></p>'
    resultado += f'<p {p_style}><strong>Data da extração</strong> - {get_data_atual_br()}.</p>'
    resultado += f'<p {p_style}><strong>Total geral bloqueado</strong> - R$ <u>{formatar_valor_br(total_geral)}</u></p>'
    resultado += f'<p {p_style}><u>______________________________</u></p>'
    resultado += f'<p {p_style}><strong>Discriminação por executado:</strong></p>'

    for nome, dados in executados_agrupados.items():
        total_executado = 0.0
        resultado += f'<p {p_style}><strong>{nome}</strong> - {dados["documento"]}</p>'

        for bloqueio in dados['bloqueios']:
            resultado += f'<p {p_style}>Ordem {bloqueio["ordem"]} - {bloqueio["data"]} - R$ {formatar_valor_br(bloqueio["valor"])}</p>'
            total_executado += bloqueio['valor']

        resultado += f'<p {p_style}>Total {nome} = R$ {formatar_valor_br(total_executado)}</p>'
        resultado += f'<p {p_style}>______</p>'

    resultado += f'<p {p_style}><u>______________________________</u></p>'
    resultado += f'<p {p_style_center}><strong>Ação Posterior</strong></p>'
    resultado += f'<p {p_style}>Considerando os valores bloqueados, houve transferência do montante à conta judicial, que será efetivada em até 48h úteis.</p>'
    resultado += f'<p {p_style}>Nos casos de bloqueio integral, todo e qualquer valor remanescente foi desbloqueado na mesma ação.</p>'
    resultado += f'<p {p_style}>Ordens sem resposta foram canceladas.</p>'

    return resultado

# ====================================================
# FUNÇÃO PARA COPIAR TEXTO PARA CLIPBOARD
# Baseado no testo.js
# ====================================================

def copiar_para_clipboard(texto_html):
    """
    Copia texto HTML para clipboard (simulando testo.js)
    """
    try:
        import pyperclip
        # Converter HTML para texto simples para clipboard
        texto_simples = texto_html.replace('<p class="corpo" style="font-size:12pt;line-height:1.5;margin-left:0 !important;text-align:justify !important;text-indent:4.5cm;">', '')
        texto_simples = texto_simples.replace('<p class="corpo" style="font-size:12pt;line-height:1.5;margin-left:0 !important;text-align:center;text-indent:4.5cm;">', '')
        texto_simples = texto_simples.replace('<strong>', '').replace('</strong>', '')
        texto_simples = texto_simples.replace('<u>', '').replace('</u>', '')
        texto_simples = texto_simples.replace('</p>', '\n')
        texto_simples = texto_simples.replace('<br>', '\n')
        texto_simples = texto_simples.replace('&nbsp;', ' ')
        texto_simples = texto_simples.strip()

        pyperclip.copy(texto_simples)
        print('✅ Texto copiado para clipboard!')
        return True
    except ImportError:
        print('⚠️ Instale pyperclip: pip install pyperclip')
        print('📄 Texto gerado:')
        print(texto_html)
        return False
    except Exception as e:
        print(f'❌ Erro ao copiar: {str(e)}')
        print('📄 Texto gerado:')
        print(texto_html)
        return False

# ====================================================
# FUNÇÃO PARA LIMPAR DADOS GLOBAIS
# ====================================================

def limpar_dados():
    """
    Limpa dados globais (chamar ao fechar driver SISBAJUD)
    """
    global dados_ordem_global, dados_executados_global
    dados_ordem_global = {}
    dados_executados_global = []
    print('[DADOBLOQ] 🧹 Dados limpos')

# ====================================================
# EXEMPLO DE USO DA FUNÇÃO DADOBLOQ
# ====================================================

def exemplo_uso():
    """
    Exemplo de como usar a função dadobloq
    """
    print("=== EXEMPLO DE USO DA FUNÇÃO DADOBLOQ ===")
    print()
    print("# 1. Importar e configurar driver SISBAJUD")
    print("from selenium import webdriver")
    print("driver = webdriver.Firefox()  # ou Chrome()")
    print("# Navegar para página /desdobrar do SISBAJUD")
    print()
    print("# 2. Chamar função dadobloq")
    print("resultado = dadobloq(driver)")
    print()
    print("# 3. Verificar resultado")
    print("if resultado['sucesso']:")
    print("    print(f\"Extraídos {resultado['total_executados']} executados\")")
    print()
    print("# 4. Gerar texto formatado")
    print("texto_html = gerar_texto_saida()")
    print("copiar_para_clipboard(texto_html)")
    print()
    print("# 5. Limpar dados ao fechar driver")
    print("limpar_dados()")
    print("driver.quit()")
    print()
    print("=== FIM DO EXEMPLO ===")

if __name__ == "__main__":
    exemplo_uso()
