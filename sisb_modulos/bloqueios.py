# sisb_modulos/bloqueios.py
# Processamento de bloqueios SISBAJUD

import time
import re
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def processar_bloqueios(driver, config, linhas_filtradas=None):
    """
    Processa bloqueios na tabela de teimosinha:
    1. Se linhas_filtradas for fornecido, clica em TODAS as linhas filtradas com "JUN 2025"
    2. Para cada linha, clica no elemento da linha
    3. Confirma navegação para /detalhes
    4. Aplica cores nas linhas baseado no status de bloqueio (verde=positivo, vermelho=negativo)
    5. Retorna à página anterior e continua com a próxima linha
    
    Esta função trabalha com o driver atual, não cria novo driver.
    
    Args:
        driver: O WebDriver Selenium
        config: Configurações do sistema
        linhas_filtradas: Lista opcional contendo as linhas filtradas com "JUN 2025"
    """
    print('[BACEN] Iniciando processamento de bloqueios...')
    
    try:
        # Verificar se temos linhas filtradas para processar
        if linhas_filtradas and isinstance(linhas_filtradas, list) and len(linhas_filtradas) > 0:
            print(f'[BACEN] Recebidas {len(linhas_filtradas)} linhas filtradas para processamento')
            
            # URL base fixa para construir URLs de detalhes
            url_base_sisbajud = 'https://sisbajud.cnj.jus.br/teimosinha/'
            print(f'[BACEN] URL base definida: {url_base_sisbajud}')
            
            # Processar TODAS as linhas filtradas, sem filtro adicional por réu
            linhas_processadas = 0
            linhas_com_erro = 0
            
            for idx, linha in enumerate(linhas_filtradas, 1):
                id_serie = linha.get('id_serie', 'N/A')
                
                if id_serie and id_serie != 'N/A' and str(id_serie).isdigit():
                    print(f'[BACEN] Processando linha {idx}/{len(linhas_filtradas)} - ID: {id_serie}')
                    
                    # Construir URL direta para detalhes da linha específica
                    url_detalhes = f'{url_base_sisbajud}{id_serie}/detalhes'
                    print(f'[BACEN] Navegando diretamente para: {url_detalhes}')
                    
                    try:
                        # Navegar diretamente para a página de detalhes
                        driver.get(url_detalhes)
                        time.sleep(2)
                        
                        # Verificar se conseguimos navegar para detalhes
                        current_url = driver.current_url
                        if '/detalhes' in current_url and id_serie in current_url:
                            print(f'[BACEN] ✅ Navegação direta bem-sucedida para linha {idx} (ID: {id_serie})!')
                            
                            # Aplicar cores nas linhas da página de detalhes
                            _aplicar_cores_status_bloqueio(driver, config)
                            linhas_processadas += 1
                            
                            # Aguardar um pouco antes de processar a próxima linha
                            time.sleep(1)
                            
                        else:
                            print(f'[BACEN] ❌ Falha ao navegar para detalhes da linha {idx} (ID: {id_serie})')
                            print(f'[BACEN] URL atual: {current_url}')
                            linhas_com_erro += 1
                            
                    except Exception as e:
                        print(f'[BACEN] ❌ Erro ao navegar para detalhes da linha {idx} (ID: {id_serie}): {e}')
                        linhas_com_erro += 1
                        
                else:
                    print(f'[BACEN] ❌ ID inválido para linha {idx}: {id_serie}')
                    linhas_com_erro += 1
            
            # Relatório final do processamento
            print(f'[BACEN] ✅ Processamento concluído: {linhas_processadas} linhas processadas, {linhas_com_erro} erros')
            if linhas_processadas > 0:
                return True
        
        # Se não tem linhas filtradas ou o clique nas linhas não funcionou, seguir com o fluxo original
        # Passo 1: Procurar e clicar no botão de ações (três pontos)
        print('[BACEN] Passo 1: Procurando botão de ações (três pontos)...')
        
        # Estratégia múltipla para encontrar o botão
        botao_acoes_encontrado = False
        
        # Método 1: Por classe específica do mat-icon
        try:
            botao_acoes = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[mat-icon-button] mat-icon.fa-ellipsis-h'))
            )
            # Clicar no botão pai (button)
            botao_pai = botao_acoes.find_element(By.XPATH, './..')
            botao_pai.click()
            print('[BACEN] ✅ Botão de ações clicado (método 1 - classe fa-ellipsis-h)')
            botao_acoes_encontrado = True
            
        except Exception:
            # Método 2: Por seletor CSS mais genérico
            try:
                botao_acoes = WebDriverWait(driver, 3).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, 'button.mat-menu-trigger.mat-icon-button'))
                )
                botao_acoes.click()
                print('[BACEN] ✅ Botão de ações clicado (método 2 - classes mat-menu-trigger)')
                botao_acoes_encontrado = True
                
            except Exception:
                # Método 3: Buscar por atributo aria-haspopup
                try:
                    botao_acoes = WebDriverWait(driver, 3).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[aria-haspopup="true"]'))
                    )
                    botao_acoes.click()
                    print('[BACEN] ✅ Botão de ações clicado (método 3 - aria-haspopup)')
                    botao_acoes_encontrado = True
                    
                except Exception as e:
                    print(f'[BACEN][ERRO] Não foi possível encontrar o botão de ações: {e}')
                    return False
        
        if not botao_acoes_encontrado:
            print('[BACEN][ERRO] Botão de ações não encontrado')
            return False
        
        # Aguardar menu aparecer
        time.sleep(1)
        
        # Passo 2: Procurar e clicar no ícone de lupa/detalhes
        print('[BACEN] Passo 2: Procurando ícone de detalhes (lupa)...')
        
        detalhes_clicado = False
        
        # Método 1: Por classe específica fa-search-plus
        try:
            icone_detalhes = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'mat-icon.fa-search-plus'))
            )
            icone_detalhes.click()
            print('[BACEN] ✅ Ícone de detalhes clicado (método 1 - fa-search-plus)')
            detalhes_clicado = True
            
        except Exception:
            # Método 2: Buscar por qualquer ícone de pesquisa/lupa
            try:
                seletores_alternativos = [
                    'mat-icon[class*="search"]',
                    'mat-icon[class*="zoom"]', 
                    'mat-icon[class*="detail"]',
                    'mat-icon.fa-search',
                    'button[title*="detail" i]',
                    'button[title*="detalhes" i]'
                ]
                
                for seletor in seletores_alternativos:
                    try:
                        elemento = WebDriverWait(driver, 2).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, seletor))
                        )
                        elemento.click()
                        print(f'[BACEN] ✅ Ícone de detalhes clicado (método alternativo - {seletor})')
                        detalhes_clicado = True
                        break
                    except Exception:
                        continue
                        
            except Exception as e:
                print(f'[BACEN][ERRO] Não foi possível encontrar o ícone de detalhes: {e}')
                return False
        
        if not detalhes_clicado:
            print('[BACEN][ERRO] Ícone de detalhes não encontrado')
            return False
        
        # Passo 3: Confirmar navegação para /detalhes
        print('[BACEN] Passo 3: Confirmando navegação para /detalhes...')
        
        # Aguardar navegação
        time.sleep(2)
        
        # Verificar se chegamos na URL de detalhes
        navegacao_confirmada = False
        for tentativa in range(10):
            current_url = driver.current_url
            print(f'[BACEN] Tentativa {tentativa + 1}/10 - URL atual: {current_url}')
            
            if '/detalhes' in current_url:
                print('[BACEN] ✅ Navegação para /detalhes confirmada!')
                print(f'[BACEN] URL de detalhes: {current_url}')
                navegacao_confirmada = True
                break
                
            time.sleep(1)
        
        # Se não chegou na URL /detalhes, verificar elementos de detalhes
        if not navegacao_confirmada:
            print(f'[BACEN][AVISO] URL /detalhes não detectada após 10 tentativas.')
            print(f'[BACEN] URL final: {driver.current_url}')
            print('[BACEN] Verificando se elementos de detalhes estão presentes...')
            
            # Verificar se elementos típicos de página de detalhes estão presentes
            elementos_detalhes = driver.execute_script("""
                const indicadores = [
                    'sisbajud-detalhes',
                    'detalhe-ordem',
                    'informacoes-ordem',
                    '[class*="detail"]',
                    '[class*="detalhes"]'
                ];
                
                for (let seletor of indicadores) {
                    if (document.querySelector(seletor)) {
                        console.log('[BACEN] Elemento de detalhes encontrado:', seletor);
                        return true;
                    }
                }
                return false;
            """)
            
            if elementos_detalhes:
                print('[BACEN] ✅ Elementos de detalhes detectados na página!')
                navegacao_confirmada = True
            else:
                print('[BACEN][ERRO] Elementos de detalhes não detectados')
                return False
        
        # Passo 4: Aplicar cores nas linhas após confirmar navegação para detalhes
        if navegacao_confirmada:
            print('[BACEN] Passo 4: Aplicando cores nas linhas da tabela após navegação confirmada...')
            _aplicar_cores_status_bloqueio(driver, config)
            print('[BACEN] ✅ Processamento de bloqueios concluído com sucesso!')
            return True
        else:
            print('[BACEN][ERRO] Navegação para detalhes não confirmada')
            return False
            
    except Exception as e:
        print(f'[BACEN][ERRO] Exceção durante processamento de bloqueios: {e}')
        return False

def _aplicar_cores_status_bloqueio(driver, config):
    """
    Aplica cores nas linhas da tabela baseado na comparação do valor da coluna 'Valor a bloquear' com o valor do card superior.
    Verde se igual ao valor do card, vermelho se diferente.
    """
    print('[BACEN] Aplicando cores nas linhas da tabela (comparação com valor do card superior)...')
    try:
        cor_igual = config['cor_bloqueio_positivo']
        cor_diferente = config['cor_bloqueio_negativo']
        print(f'[BACEN] Cores configuradas: Igual={cor_igual}, Diferente={cor_diferente}')

        js_aplicar_cores = rf'''
            console.log('[BACEN] Iniciando aplicação de cores nas linhas...');
            // 1. Extrair valor de referência do card superior
            let valorCard = null;
            let labels = document.querySelectorAll('span.sisbajud-label');
            labels.forEach(label => {{
                if (label.textContent.trim() === 'Valor a bloquear') {{
                    let valorSpan = label.nextElementSibling;
                    if (valorSpan && valorSpan.classList.contains('sisbajud-label-valor')) {{
                        let texto = valorSpan.textContent.trim();
                        let limpo = texto.replace(/R\$/g, '').replace(/\$/g, '').replace(/\s/g, '').replace(/\./g, '').replace(',', '.');
                        let num = parseFloat(limpo);
                        if (!isNaN(num)) valorCard = num;
                    }}
                }}
            }});
            if (valorCard === null) {{
                console.warn('[BACEN] Valor do card superior não encontrado!');
                return null;
            }}
            console.log('[BACEN] Valor de referência do card superior:', valorCard);

            // 2. Buscar todas as linhas da tabela que tenham a coluna 'Valor a bloquear'
            let linhas = Array.from(document.querySelectorAll('tr'));
            let linhasProcessadas = 0;
            let linhasIguais = 0;
            let linhasDiferentes = 0;
            linhas.forEach((linha, idx) => {{
                let celula = linha.querySelector('td.cdk-column-valorBloquear');
                if (!celula) return;
                let textoCelula = (celula.innerText || celula.textContent || '').trim();
                let limpo = textoCelula.replace(/R\$/g, '').replace(/\$/g, '').replace(/\s/g, '').replace(/\./g, '').replace(',', '.');
                let valorCelula = parseFloat(limpo);
                if (isNaN(valorCelula)) return;
                let cor = null;
                if (Math.abs(valorCelula - valorCard) < 0.01) {{
                    cor = '{cor_igual}';
                    linhasIguais++;
                }} else {{
                    cor = '{cor_diferente}';
                    linhasDiferentes++;
                }}
                // Aplicar cor na linha e células
                linha.style.backgroundColor = cor + ' !important';
                linha.style.color = 'white !important';
                linha.style.fontWeight = 'bold !important';
                Array.from(linha.children).forEach(cel => {{
                    cel.style.backgroundColor = cor + ' !important';
                    cel.style.color = 'white !important';
                    cel.style.fontWeight = 'bold !important';
                }});
                linhasProcessadas++;
            }});
            console.log('[BACEN] Linhas processadas:', linhasProcessadas, 'Iguais:', linhasIguais, 'Diferentes:', linhasDiferentes);
            return {{
                linhasProcessadas: linhasProcessadas,
                iguais: linhasIguais,
                diferentes: linhasDiferentes
            }};
        '''

        resultado = driver.execute_script(js_aplicar_cores)
        if resultado:
            print(f'[BACEN] ✅ Cores aplicadas com sucesso!')
            print(f"[BACEN] Linhas processadas: {resultado.get('linhasProcessadas', 0)}")
            print(f"[BACEN] Linhas iguais ao valor do card (verde): {resultado.get('iguais', 0)}")
            print(f"[BACEN] Linhas diferentes do valor do card (vermelho): {resultado.get('diferentes', 0)}")
        else:
            print('[BACEN] ⚠️ Nenhum resultado retornado do JavaScript')
    except Exception as e:
        print(f'[BACEN][ERRO] Falha ao aplicar cores nas linhas: {e}')
        import traceback
        traceback.print_exc()

def _buscar_linhas_jun_2025(driver):
    """
    Busca na tabela de resultados as linhas que contêm "JUN DE 2025"
    e retorna as linhas encontradas para processamento pela função processar_bloqueios.
    """
    try:
        print('[KAIZEN] Buscando linhas com "JUN DE 2025" na tabela...')
        
        # Buscar todas as tabelas na página
        tabelas = driver.find_elements(By.TAG_NAME, 'table')
        
        if not tabelas or len(tabelas) == 0:
            print('[KAIZEN][AVISO] Nenhuma tabela encontrada na página')
            return []
        
        linhas_encontradas = []
        
        for indice_tabela in range(len(tabelas)):
            tabela = tabelas[indice_tabela]
            # Buscar linhas da tabela
            linhas = tabela.find_elements(By.TAG_NAME, 'tr')
            
            for indice_linha in range(len(linhas)):
                try:
                    linha = linhas[indice_linha]
                    texto_linha = linha.text.upper() if linha.text else ""
                    
                    # Verificar se a linha contém o texto buscado
                    if "JUN DE 2025" in texto_linha:
                        print('✅ Linha com "JUN DE 2025" encontrada!')
                        # Buscar células da linha para encontrar o ID da série
                        celulas = linha.find_elements(By.TAG_NAME, 'td')
                        id_serie = 'ID não encontrado'
                        
                        # PRIORIDADE 1: Tentar pegar o ID da primeira célula
                        if celulas and len(celulas) > 0:
                            try:
                                primeira_celula = celulas[0]
                                texto_celula = primeira_celula.text
                                
                                # Remove espaços e caracteres especiais, busca números
                                numeros_encontrados = re.sub(r'\D', '', texto_celula)
                                
                                # Verificar se encontramos um número válido
                                if numeros_encontrados and len(numeros_encontrados) >= 8:
                                    id_serie = numeros_encontrados
                                    print(f'ID da série (8+ dígitos) encontrado: {id_serie}')
                                elif numeros_encontrados and len(numeros_encontrados) >= 4:
                                    # Se não tem 8+ dígitos, aceitar números com 4+ dígitos como fallback
                                    id_serie = numeros_encontrados
                                    print(f'ID da série (4+ dígitos) encontrado: {id_serie}')
                                
                            except Exception as e:
                                print(f'[KAIZEN][ERRO] Falha ao processar primeira célula: {e}')
                        
                        # PRIORIDADE 2: Se não encontrou na primeira célula, buscar em todas
                        if id_serie == 'ID não encontrado':
                            for indice_celula in range(len(celulas)):
                                try:
                                    celula = celulas[indice_celula]
                                    texto_celula = celula.text or celula.get_attribute('innerText') or ''
                                    
                                    # Procurar por padrões de ID (números com 8+ dígitos primeiro, depois 4+)
                                    matches_8_plus = re.findall(r'\b\d{8,}\b', texto_celula)
                                    if matches_8_plus:
                                        id_serie = matches_8_plus[0]
                                        print(f'ID da série (8+ dígitos) encontrado na célula {indice_celula}: {id_serie}')
                                        break
                                    
                                    matches_4_plus = re.findall(r'\b\d{4,}\b', texto_celula)
                                    if matches_4_plus:
                                        id_serie = matches_4_plus[0]
                                        print(f'ID da série (4+ dígitos) encontrado na célula {indice_celula}: {id_serie}')
                                        break
                                    
                                    # Verificar atributos HTML que possam conter ID
                                    for attr in ['id', 'data-id', 'data-serie', 'data-row-id']:
                                        attr_value = celula.get_attribute(attr)
                                        if attr_value and len(attr_value) >= 4:
                                            id_serie = attr_value
                                            print(f'ID da série encontrado no atributo {attr}: {id_serie}')
                                            break
                                    
                                    if id_serie != 'ID não encontrado':
                                        break
                                    
                                except Exception as e:
                                    continue
                        
                        resultado = {
                            'tabela': indice_tabela,
                            'linha': indice_linha,
                            'id_serie': id_serie,
                            'texto_completo': texto_linha.strip(),
                            'elemento': linha
                        }
                        
                        linhas_encontradas.append(resultado)
                        
                except Exception as e:
                    continue
        
        # Exibir resultados encontrados
        if linhas_encontradas and len(linhas_encontradas) > 0:
            total = len(linhas_encontradas)
            print(f'✅ Encontradas {total} linha(s) com "JUN DE 2025":')
            
            for i in range(total):
                linha = linhas_encontradas[i]
                id_serie = linha.get('id_serie', 'N/A')
                texto = linha.get('texto_completo', '')
                
                print(f'Linha {i + 1}:')
                print(f'  - ID da Série: {id_serie}')
                print(f'  - Texto: {texto[:150]}...')
                print('  ---')
            
            # Retornar as linhas encontradas para processamento posterior
            return linhas_encontradas
                
        else:
            print('❗ Nenhuma linha com "JUN DE 2025" encontrada na tabela')
            return []
        
    except Exception as e:
        print(f'❌ Falha ao buscar linhas: {e}')
        import traceback
        traceback.print_exc()
        return []
