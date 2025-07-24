"""
Módulo de utilitários para processamento de alvarás.
Extraído de listaexec2.py para m        # 2. Extrair valor - PADRÕES PARA AMBOS OS FORMATOS
        padroes_valor = [
            # Padrão específico para o formato extraído: "(=) Valor do Alvará..........: R$ 3302,37"
            r'\(=\)\s*Valor do Alvar[áa][.\s]*:?\s*R?\$?\s*(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)',
            # Padrão específico do 1º screenshot (3011): "Valor do Alvará............: R$ 1339,50"
            r'Valor do Alvar[áa][.\s]*:?\s*R?\$?\s*(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)',
            # Padrões para o 2º screenshot (formato comum): "R$ 14.977,84"
            r'R\$\s*(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)',
            # Padrões mais específicos para alvará comum
            r'valor[:\s]*R?\$?\s*(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)',
            r'quantia[:\s]*R?\$?\s*(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)',
            r'import[aâ]ncia[:\s]*R?\$?\s*(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)',
            # Padrão genérico para qualquer valor monetário brasileiro
            r'(\d{1,3}(?:\.\d{3})*,\d{2})'
        ]
"""

import re
import json
import os
import unicodedata
from datetime import datetime
from selenium.webdriver.common.by import By
import pyperclip
from selenium.webdriver.common.keys import Keys


def extrair_dados_alvara(texto, data_timeline, log=True):
    """
    Extrai dados específicos do alvará: data de expedição, valor e beneficiário
    
    Args:
        texto: Texto do documento extraído
        data_timeline: Data da timeline como fallback
        log: Se deve exibir logs
        
    Returns:
        dict: Dados do alvará ou None se não conseguir extrair
    """
    try:
        dados = {
            'data_expedicao': data_timeline,  # Fallback
            'valor': None,
            'beneficiario': None
        }
        
        if log:
            print(f'[ALVARA][DEBUG] Texto para extração ({len(texto)} chars):')
            print(f'[ALVARA][DEBUG] Primeiros 500 chars: {texto[:500]}...')
        
        # NOVA REGRA: Verificar se contém "3011" no texto
        contem_3011 = '3011' in texto
        
        if contem_3011:
            # Modelo com data de atualização (contém 3011)
            # Buscar "Data de Atualização............: DD/MM/AAAA"
            padroes_data_atualizacao = [
                r'Data de Atualiza[çc]ão[.\s]*:?\s*(\d{1,2}/\d{1,2}/\d{4})',
                r'Data de Atualiza[çc]ão[.\s]*(\d{1,2}/\d{1,2}/\d{4})',
                r'atualiza[çc]ão[:\s]*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{4})',
                r'atualizado em[:\s]*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{4})'
            ]
            
            for padrao in padroes_data_atualizacao:
                match = re.search(padrao, texto, re.IGNORECASE)
                if match:
                    data_encontrada = match.group(1)
                    # Normalizar formato para dd/mm/aaaa
                    data_normalizada = normalizar_data(data_encontrada)
                    if data_normalizada:
                        dados['data_expedicao'] = data_normalizada
                        if log:
                            print(f'[ALVARA] ⚠️ 3011 detectado - Data de atualização encontrada: {data_normalizada}')
                        break
            
            # Se não encontrou data de atualização específica, usar fallback
            if dados['data_expedicao'] == data_timeline:
                if log:
                    print(f'[ALVARA] ⚠️ 3011 detectado - Data de atualização não encontrada, usando fallback: {data_timeline}')
        else:
            # Modelo com data de expedição (não contém 3011)
            # Padrões de busca para data de expedição
            padroes_data_expedicao = [
                r'expedi[çc]ão[:\s]*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{4})',
                r'expedido em[:\s]*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{4})',
                r'data[:\s]*de[:\s]*expedi[çc]ão[:\s]*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{4})',
                r'data[:\s]*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{4})',
                r'em[:\s]*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{4})',
                r'(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{4})'  # Qualquer data no formato
            ]
            
            for padrao in padroes_data_expedicao:
                match = re.search(padrao, texto, re.IGNORECASE)
                if match:
                    data_encontrada = match.group(1)
                    # Normalizar formato para dd/mm/aaaa
                    data_normalizada = normalizar_data(data_encontrada)
                    if data_normalizada:
                        dados['data_expedicao'] = data_normalizada
                        if log:
                            print(f'[ALVARA] Data de expedição encontrada: {data_normalizada}')
                        break
        
        # 2. Extrair valor - PADRÕES PARA AMBOS OS FORMATOS
        padroes_valor = [
            # Padrão específico do 1º screenshot (3011): "Valor do Alvará............: R$ 1339,50"
            r'Valor do Alvar[áa][.\s]*:?\s*R?\$?\s*(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)',
            # Padrões para o 2º screenshot (formato comum): "R$ 14.977,84"
            r'R\$\s*(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)',
            # Padrões mais específicos para alvará comum
            r'valor[:\s]*R?\$?\s*(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)',
            r'quantia[:\s]*R?\$?\s*(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)',
            r'import[aâ]ncia[:\s]*R?\$?\s*(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)',
            # Padrão genérico para qualquer valor monetário brasileiro
            r'(\d{1,3}(?:\.\d{3})*,\d{2})'
        ]
        
        for padrao in padroes_valor:
            matches = re.findall(padrao, texto, re.IGNORECASE)
            if matches:
                # Pegar o maior valor encontrado (assumindo que é o principal)
                valores = [converter_valor_para_float(v) for v in matches]
                valor_maximo = max(valores)
                dados['valor'] = formatar_valor_brasileiro(valor_maximo)
                if log:
                    print(f'[ALVARA] Valor encontrado: {dados["valor"]} (padrão: {padrao})')
                break
        
        # 3. Extrair beneficiário - PADRÕES PARA AMBOS OS FORMATOS
        padroes_beneficiario = [
            # Padrão específico para o formato do alvará extraído: "Beneficiário.................: CONSTRUJA CONSTRUCOES EIRELI"
            r'Benefici[aá]rio[.\s]*:?\s*([A-ZÁÀÂÃÉÊÍÓÔÕÚÇ][A-ZÁÀÂÃÉÊÍÓÔÕÚÇa-záàâãéêíóôõúçç0-9\s\-]+)',
            # Padrão robusto: captura nome após "Beneficiário" (pode haver quebra de linha, pontos, espaços, etc)
            r'Benefici[aá]rio[.\s:]*\n?\s*([A-ZÁÀÂÃÉÊÍÓÔÕÚÇ][A-ZÁÀÂÃÉÊÍÓÔÕÚÇa-záàâãéêíóôõúç\s]+)',
            # Backup: captura nome após "Beneficiário" até o fim da linha
            r'Benefici[aá]rio[.\s:]*([A-ZÁÀÂÃÉÊÍÓÔÕÚÇ][A-ZÁÀÂÃÉÊÍÓÔÕÚÇa-záàâãéêíóôõúç\s]+)',
            # Outros padrões genéricos
            r'favor de[:\s]*([A-ZÁÀÂÃÉÊÍÓÔÕÚÇ][A-ZÁÀÂÃÉÊÍÓÔÕÚÇa-záàâãéêíóôõúç\s]+)',
            r'em favor de[:\s]*([A-ZÁÀÂÃÉÊÍÓÔÕÚÇ][A-ZÁÀÂÃÉÊÍÓÔÕÚÇa-záàâãéêíóôõúç\s]+)',
            r'para[:\s]*([A-ZÁÀÂÃÉÊÍÓÔÕÚÇ][A-ZÁÀÂÃÉÊÍÓÔÕÚÇa-záàâãéêíóôõúç\s]+)',
            r'autorizado[:\s]*([A-ZÁÀÂÃÉÊÍÓÔÕÚÇ][A-ZÁÀÂÃÉÊÍÓÔÕÚÇa-záàâãéêíóôõúç\s]+)'
        ]
        for padrao in padroes_beneficiario:
            match = re.search(padrao, texto, re.IGNORECASE)
            if match:
                beneficiario = match.group(1).strip()
                # Limpar texto (remover quebras de linha, espaços extras)
                beneficiario = re.sub(r'\s+', ' ', beneficiario)
                # Pegar apenas até a primeira vírgula, ponto, ou quebra de campo (dois pontos seguidos de texto)
                beneficiario = re.split(r'[,.]|(?=\s+[A-Z][a-z]+\s*[:])', beneficiario)[0].strip()
                # Nunca aceitar se for igual ao label ou vazio
                if beneficiario.lower() in ['beneficiario', 'beneficiário', '']:
                    continue
                # Nome válido: pelo menos 2 palavras e > 3 letras
                if len(beneficiario.split()) >= 2 and len(beneficiario) > 3:
                    dados['beneficiario'] = beneficiario
                    if log:
                        print(f'[ALVARA] Beneficiário encontrado: "{beneficiario}" (padrão: {padrao})')
                    break
        
        # Verificar se conseguiu extrair pelo menos alguns dados
        if dados['valor'] or dados['beneficiario']:
            return dados
        else:
            if log:
                print('[ALVARA][AVISO] Não foi possível extrair dados específicos do alvará')
            return None
            
    except Exception as e:
        if log:
            print(f'[ALVARA][ERRO] Erro ao extrair dados do alvará: {e}')
        return None


def normalizar_data(data_str):
    """Normaliza data para formato dd/mm/aaaa"""
    try:
        # Remove espaços e substitui - por /
        data_clean = data_str.strip().replace('-', '/')
        
        # Verifica se já está no formato correto
        if re.match(r'\d{1,2}/\d{1,2}/\d{4}', data_clean):
            partes = data_clean.split('/')
            dia = partes[0].zfill(2)
            mes = partes[1].zfill(2)
            ano = partes[2]
            return f"{dia}/{mes}/{ano}"
        
        return None
    except:
        return None


def extrair_autor_processo(texto, log=True):
    """Extrai o nome do autor do processo do texto do alvará"""
    try:
        # Padrões específicos para ambos os formatos de alvará
        padroes_autor = [
            # Padrão específico do 1º screenshot (3011): "Autor (reclamante) ......: LUIS JOSE CARDOSO"
            r'Autor \(reclamante\)[.\s]*:?\s*([A-ZÁÀÂÃÉÊÍÓÔÕÚÇ][A-ZÁÀÂÃÉÊÍÓÔÕÚÇa-záàâãéêíóôõúç\s]+)',
            # Padrões para o 2º screenshot (formato comum): "Requerente...........: NOME"
            r'Requerente[.\s]*:?\s*([A-ZÁÀÂÃÉÊÍÓÔÕÚÇ][A-ZÁÀÂÃÉÊÍÓÔÕÚÇa-záàâãéêíóôõúç\s]+)',
            # Padrões genéricos de backup
            r'autor[:\s]*([A-ZÁÀÂÃÉÊÍÓÔÕÚÇ][A-ZÁÀÂÃÉÊÍÓÔÕÚÇa-záàâãéêíóôõúç\s]+)',
            r'requerente[:\s]*([A-ZÁÀÂÃÉÊÍÓÔÕÚÇ][A-ZÁÀÂÃÉÊÍÓÔÕÚÇa-záàâãéêíóôõúç\s]+)',
            r'exequente[:\s]*([A-ZÁÀÂÃÉÊÍÓÔÕÚÇ][A-ZÁÀÂÃÉÊÍÓÔÕÚÇa-záàâãéêíóôõúç\s]+)',
            r'processo[:\s]*\d+-\d+\.\d+\.\d+\.\d+[:\s]*([A-ZÁÀÂÃÉÊÍÓÔÕÚÇ][A-ZÁÀÂÃÉÊÍÓÔÕÚÇa-záàâãéêíóôõúç\s]+)',
            r'nos autos[:\s]*.*?[:\s]*([A-ZÁÀÂÃÉÊÍÓÔÕÚÇ][A-ZÁÀÂÃÉÊÍÓÔÕÚÇa-záàâãéêíóôõúç\s]+)'
        ]
        
        for padrao in padroes_autor:
            match = re.search(padrao, texto, re.IGNORECASE)
            if match:
                autor = match.group(1).strip()
                # Limpar texto (remover quebras de linha, espaços extras)
                autor = re.sub(r'\s+', ' ', autor)
                # Pegar apenas até a primeira vírgula, "X" ou "versus" (se houver)
                autor = re.split(r'[,]|(?:\s+[xX]\s+)|(?:\s+versus\s+)|(?:\s+vs?\s+)', autor)[0].strip()
                if len(autor) > 3:  # Nome válido
                    if log:
                        print(f'[ALVARA] Autor do processo encontrado: "{autor}" (padrão: {padrao})')
                    return autor
        
        if log:
            print('[ALVARA] ⚠️ Autor do processo não encontrado no texto')
        return None
        
    except Exception as e:
        if log:
            print(f'[ALVARA][ERRO] Erro ao extrair autor do processo: {e}')
        return None


def normalizar_nome(nome):
    """Normaliza nome para comparação (remove acentos, espaços extras, converte para minúsculo)"""
    try:
        if not nome:
            return ""
        
        # Converter para string se não for
        nome_str = str(nome)
        
        # Remover acentos
        nome_sem_acento = unicodedata.normalize('NFD', nome_str)
        nome_sem_acento = ''.join(c for c in nome_sem_acento if unicodedata.category(c) != 'Mn')
        
        # Converter para minúsculo e remover espaços extras
        nome_normalizado = re.sub(r'\s+', ' ', nome_sem_acento.lower().strip())
        
        return nome_normalizado
        
    except Exception as e:
        # Em caso de erro, retornar o nome original em minúsculo
        return str(nome).lower().strip() if nome else ""


def converter_valor_para_float(valor_str):
    """Converte string de valor brasileiro para float"""
    try:
        # Remove pontos (separadores de milhares) e substitui vírgula por ponto
        valor_clean = valor_str.replace('.', '').replace(',', '.')
        return float(valor_clean)
    except:
        return 0.0


def formatar_valor_brasileiro(valor_float):
    """Formata float para string no formato brasileiro"""
    try:
        return f"R$ {valor_float:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    except:
        return "R$ 0,00"


def salvar_dados_alvara(dados, log=True):
    """Salva dados do alvará em alvaras.js"""
    try:
        arquivo_path = os.path.join(os.getcwd(), 'alvaras.js')
        
        # Criar entrada de log
        entrada = {
            'timestamp': datetime.now().isoformat(),
            'data_expedicao': dados['data_expedicao'],
            'valor': dados['valor'],
            'beneficiario': dados['beneficiario']
        }
        
        # Ler arquivo existente ou criar novo
        dados_existentes = []
        if os.path.exists(arquivo_path):
            try:
                with open(arquivo_path, 'r', encoding='utf-8') as f:
                    conteudo = f.read()
                    if conteudo.strip():
                        # Tentar extrair dados JSON do arquivo JS
                        match = re.search(r'const alvaras = (\[.*?\]);', conteudo, re.DOTALL)
                        if match:
                            dados_existentes = json.loads(match.group(1))
            except:
                pass
        
        # Adicionar nova entrada
        dados_existentes.append(entrada)
        
        # Salvar arquivo JS
        conteudo_js = f"""// Dados de alvarás extraídos automaticamente
// Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}

const alvaras = {json.dumps(dados_existentes, indent=2, ensure_ascii=False)};

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

console.log(`Total de alvarás registrados: ${{alvaras.length}}`);
"""
        
        with open(arquivo_path, 'w', encoding='utf-8') as f:
            f.write(conteudo_js)
        
        if log:
            print(f'[ALVARA] Dados salvos em: {arquivo_path}')
            print(f'[ALVARA] Data: {dados["data_expedicao"]}, Valor: {dados["valor"]}, Beneficiario: {dados["beneficiario"]}')
    
    except Exception as e:
        if log:
            print(f'[ALVARA][ERRO] Erro ao salvar dados: {e}')


def extrair_id_timeline(item, log=True):
    """
    Extrai o ID único do item da timeline (como em lista.js)
    
    Args:
        item: Elemento da timeline
        log: Se deve exibir logs
        
    Returns:
        str: ID do item ou ID gerado baseado no texto
    """
    try:
        # Tentar extrair ID do atributo data-id ou similar
        try:
            item_id = item.get_attribute('data-id')
            if item_id:
                return item_id
        except:
            pass
        
        # Tentar extrair de atributos comuns
        for attr in ['id', 'data-item-id', 'data-timeline-id']:
            try:
                item_id = item.get_attribute(attr)
                if item_id:
                    return item_id
            except:
                continue
        
        # Fallback: gerar ID baseado no texto do link principal
        try:
            links = item.find_elements(By.CSS_SELECTOR, 'a.tl-documento:not([target="_blank"])')
            if links:
                texto_link = links[0].text.strip()
                # Criar hash simples do texto para ID único
                import hashlib
                id_gerado = hashlib.md5(texto_link.encode()).hexdigest()[:8]
                return f"tl-{id_gerado}"
        except:
            pass
        
        # Último fallback: ID baseado na posição
        return f"item-{hash(str(item)) % 10000}"
        
    except Exception as e:
        if log:
            print(f'[TIMELINE-ID][ERRO] Erro ao extrair ID: {e}')
        return f"erro-{hash(str(item)) % 10000}"


def extrair_data_item(item):
    """Extrai data do item da timeline usando Selenium"""
    try:
        # Buscar elemento .tl-data
        data_element = None
        try:
            data_element = item.find_element(By.CSS_SELECTOR, '.tl-data[name="dataItemTimeline"]')
        except:
            try:
                data_element = item.find_element(By.CSS_SELECTOR, '.tl-data')
            except:
                pass
        
        # Se não encontrou, buscar em elementos anteriores usando JavaScript
        if not data_element:
            try:
                # Precisaria do driver aqui, mas não temos acesso
                # Deixar para implementar no contexto adequado
                pass
            except Exception as e:
                pass
        
        if data_element:
            data_texto = data_element.text.strip()
            # Converter formato "01 mar. 2019" para "01/03/2019"
            data_convertida = converter_data_texto_para_numerico(data_texto)
            if data_convertida:
                return data_convertida
        
        # Fallback: buscar data no texto do item
        texto_completo = item.text
        match_data = re.search(r'(\d{1,2}/\d{1,2}/\d{4})', texto_completo)
        if match_data:
            return match_data.group(1)
        
        return 'Data não encontrada'
    except:
        return 'Erro na data'


def converter_data_texto_para_numerico(data_texto):
    """Converte texto de data para formato numérico"""
    try:
        meses = {
            'jan': '01', 'fev': '02', 'mar': '03', 'abr': '04',
            'mai': '05', 'jun': '06', 'jul': '07', 'ago': '08',
            'set': '09', 'out': '10', 'nov': '11', 'dez': '12'
        }
        
        match = re.search(r'(\d{1,2})\s+(\w{3})\.?\s+(\d{4})', data_texto)
        if match:
            dia = match.group(1).zfill(2)
            mes_texto = match.group(2).lower()
            ano = match.group(3)
            
            mes_numero = meses.get(mes_texto)
            if mes_numero:
                return f"{dia}/{mes_numero}/{ano}"
        
        return None
    except:
        return None


def copiar_texto_alvara_via_clipboard(driver, log=True):
    """
    Tenta acessar todos os frames/objects, seleciona e copia TODO o texto do PDF.js via Selenium.
    Retorna o texto copiado ou None.
    """
    import time
    import pyperclip
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    
    try:
        # Limpar clipboard antes de começar
        pyperclip.copy("")
        time.sleep(0.1)
        
        original_window = driver.current_window_handle
        
        # Primeiro tentar encontrar object.conteudo-pdf especificamente (como no JS que funcionou)
        try:
            # Tentar executar JS diretamente no documento principal para encontrar o PDF
            texto_extraido = driver.execute_script("""
                try {
                    const pdfObject = document.querySelector('object.conteudo-pdf');
                    if (pdfObject) {
                        const pdfDoc = pdfObject.contentDocument || pdfObject.contentWindow.document;
                        if (pdfDoc) {
                            const pages = pdfDoc.querySelectorAll('.page');
                            if (pages.length > 0) {
                                // Selecionar todo o conteúdo de todas as páginas
                                let allText = '';
                                for (let i = 0; i < pages.length; i++) {
                                    const range = pdfDoc.createRange();
                                    range.selectNodeContents(pages[i]);
                                    const selection = pdfDoc.getSelection();
                                    selection.removeAllRanges();
                                    selection.addRange(range);
                                    allText += selection.toString() + '\\n';
                                    selection.removeAllRanges();
                                }
                                return allText.trim();
                            }
                        }
                    }
                    return null;
                } catch(e) {
                    return null;
                }
            """)
            
            if texto_extraido and len(texto_extraido.strip()) > 10:
                # Verificar se não é log do sistema
                if not ('[ALVARA]' in texto_extraido or '[DEBUG]' in texto_extraido or 'copiar_texto_alvara_via_clipboard' in texto_extraido):
                    if log:
                        print(f"[ALVARA][CLIPBOARD][JS-DIRECT] Texto extraído diretamente: {texto_extraido[:200]}...")
                    return texto_extraido
        except Exception as e:
            if log:
                print(f"[ALVARA][DEBUG] Falha na extração direta JS: {e}")
        
        # Fallback: método original com frames
        frames = driver.find_elements(By.TAG_NAME, 'iframe')
        objects = driver.find_elements(By.TAG_NAME, 'object')
        candidates = frames + objects
        for frame in candidates:
            try:
                driver.switch_to.frame(frame)
                # Tentar extrair via JS dentro do frame
                try:
                    texto_frame = driver.execute_script("""
                        try {
                            const pages = document.querySelectorAll('.page');
                            if (pages.length > 0) {
                                let allText = '';
                                for (let i = 0; i < pages.length; i++) {
                                    const range = document.createRange();
                                    range.selectNodeContents(pages[i]);
                                    const selection = window.getSelection();
                                    selection.removeAllRanges();
                                    selection.addRange(range);
                                    allText += selection.toString() + '\\n';
                                    selection.removeAllRanges();
                                }
                                return allText.trim();
                            }
                            return null;
                        } catch(e) {
                            return null;
                        }
                    """)
                    driver.switch_to.default_content()
                    
                    if texto_frame and len(texto_frame.strip()) > 10:
                        if not ('[ALVARA]' in texto_frame or '[DEBUG]' in texto_frame or 'copiar_texto_alvara_via_clipboard' in texto_frame):
                            if log:
                                print(f"[ALVARA][CLIPBOARD][JS-FRAME] Texto extraído do frame: {texto_frame[:200]}...")
                            return texto_frame
                except Exception as e:
                    if log:
                        print(f"[ALVARA][DEBUG] Falha na extração JS do frame: {e}")
                
                # Método anterior como último recurso
                try:
                    driver.switch_to.frame(frame)
                    driver.execute_script(
                        """
                        try {
                            var sel = window.getSelection();
                            sel.removeAllRanges();
                            sel.selectAllChildren(document.body);
                        } catch(e) {}
                        """
                    )
                    time.sleep(0.2)
                    # Tentar múltiplas formas de simular Ctrl+C
                    try:
                        body = driver.find_element(By.TAG_NAME, 'body')
                        body.send_keys(Keys.CONTROL, 'c')
                    except:
                        # Alternativa: usar Actions
                        from selenium.webdriver.common.action_chains import ActionChains
                        ActionChains(driver).key_down(Keys.CONTROL).send_keys('c').key_up(Keys.CONTROL).perform()
                    
                    time.sleep(0.3)
                    texto = pyperclip.paste()
                    driver.switch_to.default_content()
                    
                    if texto and len(texto.strip()) > 10:
                        if not ('[ALVARA]' in texto or '[DEBUG]' in texto or 'copiar_texto_alvara_via_clipboard' in texto):
                            if log:
                                print(f"[ALVARA][CLIPBOARD][CTRL-C] Texto copiado via Ctrl+C: {texto[:200]}...")
                            return texto
                except Exception as e:
                    if log:
                        print(f"[ALVARA][DEBUG] Falha no método Ctrl+C: {e}")
                
                driver.switch_to.default_content()
            except Exception as e:
                try:
                    driver.switch_to.default_content()
                except:
                    pass
                continue
        
        if log:
            print('[ALVARA][ERRO] Não encontrou frame/object para copiar o texto do alvará.')
        return None
    except Exception as e:
        if log:
            print(f"[ALVARA][ERRO] Falha ao copiar texto do alvará via clipboard/frame: {e}")
        return None


def extrair_dados_alvara_via_clipboard(driver, data_timeline=None, log=True):
    """
    Localiza o elemento do alvará, copia o texto via Ctrl+A/Ctrl+C e extrai os dados do alvará.
    Args:
        driver: Instância do Selenium WebDriver
        data_timeline: Data da timeline como fallback (opcional)
        log: Se deve exibir logs
    Returns:
        dict: Dados extraídos do alvará ou None
    """
    try:
        texto = copiar_texto_alvara_via_clipboard(driver, log=log)
        if log:
            print(f"[ALVARA][DEBUG] Texto realmente copiado do clipboard: {repr(texto)}")
        if not texto:
            if log:
                print('[ALVARA][ERRO] Não foi possível copiar o texto do alvará via clipboard.')
            return None
        return extrair_dados_alvara(texto, data_timeline, log=log)
    except Exception as e:
        if log:
            print(f'[ALVARA][ERRO] Falha ao extrair dados do alvará via clipboard: {e}')
        return None
