"""
Módulo de Debug Visual para PJe Plus
Fornece funcionalidades de depuração visual para análise de elementos da página
"""

import time
import os
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def debug_visual_completo(driver, titulo="Debug Visual", debug=True):
    """
    Executa debug visual completo da página atual, gerando relatório HTML
    com informações sobre elementos, estrutura e possíveis problemas.

    Args:
        driver: Instância do WebDriver
        titulo: Título do relatório
        debug: Se True, exibe logs no console

    Returns:
        str: Caminho do arquivo HTML gerado
    """
    if debug:
        print(f"[DEBUG_VISUAL] Iniciando análise visual da página: {titulo}")

    try:
        # Informações básicas da página
        url_atual = driver.current_url
        titulo_pagina = driver.title
        numero_abas = len(driver.window_handles)
        aba_atual = driver.current_window_handle

        if debug:
            print(f"[DEBUG_VISUAL] URL: {url_atual}")
            print(f"[DEBUG_VISUAL] Título: {titulo_pagina}")
            print(f"[DEBUG_VISUAL] Abas: {numero_abas} (atual: {aba_atual})")

        # Análise de elementos principais
        elementos_analisados = {}

        # Botões
        try:
            botoes = driver.find_elements(By.TAG_NAME, 'button')
            elementos_analisados['botoes'] = {
                'total': len(botoes),
                'visiveis': len([b for b in botoes if b.is_displayed()]),
                'exemplos': []
            }

            for i, botao in enumerate(botoes[:10]):  # Analisa primeiros 10
                try:
                    texto = botao.text.strip()
                    aria_label = botao.get_attribute('aria-label') or ''
                    mattooltip = botao.get_attribute('mattooltip') or ''
                    classe = botao.get_attribute('class') or ''
                    disabled = botao.get_attribute('disabled')

                    elementos_analisados['botoes']['exemplos'].append({
                        'indice': i+1,
                        'texto': texto,
                        'aria_label': aria_label,
                        'mattooltip': mattooltip,
                        'classe': classe,
                        'disabled': disabled,
                        'visivel': botao.is_displayed(),
                        'habilitado': botao.is_enabled()
                    })
                except Exception as e:
                    if debug:
                        print(f"[DEBUG_VISUAL] Erro ao analisar botão {i+1}: {e}")

        except Exception as e:
            if debug:
                print(f"[DEBUG_VISUAL] Erro ao analisar botões: {e}")

        # Inputs e campos de formulário
        try:
            inputs = driver.find_elements(By.TAG_NAME, 'input')
            elementos_analisados['inputs'] = {
                'total': len(inputs),
                'tipos': {}
            }

            for inp in inputs:
                tipo = inp.get_attribute('type') or 'text'
                if tipo not in elementos_analisados['inputs']['tipos']:
                    elementos_analisados['inputs']['tipos'][tipo] = 0
                elementos_analisados['inputs']['tipos'][tipo] += 1

        except Exception as e:
            if debug:
                print(f"[DEBUG_VISUAL] Erro ao analisar inputs: {e}")

        # Elementos específicos do PJe
        elementos_pje = {}

        # Botões de tarefa
        try:
            btns_tarefa = driver.find_elements(By.CSS_SELECTOR, 'button[mattooltip*="tarefa"], button[aria-label*="tarefa"]')
            elementos_pje['botoes_tarefa'] = len(btns_tarefa)
        except:
            elementos_pje['botoes_tarefa'] = 0

        # Elementos de sobrestamento
        try:
            elementos_sobrestamento = driver.find_elements(By.XPATH, '//*[contains(text(), "sobrestamento") or contains(text(), "Sobrestamento")]')
            elementos_pje['elementos_sobrestamento'] = len(elementos_sobrestamento)
        except:
            elementos_pje['elementos_sobrestamento'] = 0

        # Timeline
        try:
            itens_timeline = driver.find_elements(By.CSS_SELECTOR, 'li.tl-item-container')
            elementos_pje['itens_timeline'] = len(itens_timeline)
        except:
            elementos_pje['itens_timeline'] = 0

        # Gera relatório HTML
        html_content = f"""
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{titulo} - Debug Visual PJe Plus</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }}
        .header {{
            background-color: #2c3e50;
            color: white;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
        }}
        .section {{
            background-color: white;
            padding: 15px;
            margin-bottom: 15px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .section h3 {{
            color: #2c3e50;
            border-bottom: 2px solid #3498db;
            padding-bottom: 5px;
        }}
        .info-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 10px;
            margin: 10px 0;
        }}
        .info-item {{
            background-color: #ecf0f1;
            padding: 10px;
            border-radius: 4px;
        }}
        .info-label {{
            font-weight: bold;
            color: #2c3e50;
        }}
        .info-value {{
            color: #3498db;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 10px;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 8px;
            text-align: left;
        }}
        th {{
            background-color: #3498db;
            color: white;
        }}
        tr:nth-child(even) {{
            background-color: #f2f2f2;
        }}
        .status-ok {{
            color: #27ae60;
        }}
        .status-warn {{
            color: #f39c12;
        }}
        .status-error {{
            color: #e74c3c;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🔍 {titulo}</h1>
        <p>Relatório de Debug Visual - PJe Plus</p>
        <p><strong>Data:</strong> {time.strftime('%d/%m/%Y %H:%M:%S')}</p>
    </div>

    <div class="section">
        <h3>📄 Informações da Página</h3>
        <div class="info-grid">
            <div class="info-item">
                <div class="info-label">URL:</div>
                <div class="info-value">{url_atual}</div>
            </div>
            <div class="info-item">
                <div class="info-label">Título:</div>
                <div class="info-value">{titulo_pagina}</div>
            </div>
            <div class="info-item">
                <div class="info-label">Total de Abas:</div>
                <div class="info-value">{numero_abas}</div>
            </div>
            <div class="info-item">
                <div class="info-label">Aba Atual:</div>
                <div class="info-value">{aba_atual}</div>
            </div>
        </div>
    </div>

    <div class="section">
        <h3>🔘 Análise de Elementos Gerais</h3>
        <div class="info-grid">
            <div class="info-item">
                <div class="info-label">Botões Totais:</div>
                <div class="info-value">{elementos_analisados.get('botoes', {}).get('total', 0)}</div>
            </div>
            <div class="info-item">
                <div class="info-label">Botões Visíveis:</div>
                <div class="info-value">{elementos_analisados.get('botoes', {}).get('visiveis', 0)}</div>
            </div>
            <div class="info-item">
                <div class="info-label">Inputs Totais:</div>
                <div class="info-value">{elementos_analisados.get('inputs', {}).get('total', 0)}</div>
            </div>
        </div>

        <h4>📋 Detalhes dos Botões (primeiros 10)</h4>
        <table>
            <thead>
                <tr>
                    <th>#</th>
                    <th>Texto</th>
                    <th>ARIA Label</th>
                    <th>MatTooltip</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody>
"""

        # Adiciona linhas da tabela de botões
        for botao in elementos_analisados.get('botoes', {}).get('exemplos', []):
            status = ""
            if botao['visivel'] and botao['habilitado']:
                status = '<span class="status-ok">✓ OK</span>'
            elif botao['visivel'] and not botao['habilitado']:
                status = '<span class="status-warn">⚠ Desabilitado</span>'
            else:
                status = '<span class="status-error">✗ Oculto</span>'

            html_content += f"""
                <tr>
                    <td>{botao['indice']}</td>
                    <td>{botao['texto'][:50]}{'...' if len(botao['texto']) > 50 else ''}</td>
                    <td>{botao['aria_label'][:50]}{'...' if len(botao['aria_label']) > 50 else ''}</td>
                    <td>{botao['mattooltip'][:50]}{'...' if len(botao['mattooltip']) > 50 else ''}</td>
                    <td>{status}</td>
                </tr>
"""

        html_content += """
            </tbody>
        </table>
    </div>

    <div class="section">
        <h3>⚖️ Elementos Específicos do PJe</h3>
        <div class="info-grid">
            <div class="info-item">
                <div class="info-label">Botões de Tarefa:</div>
                <div class="info-value">{elementos_pje.get('botoes_tarefa', 0)}</div>
            </div>
            <div class="info-item">
                <div class="info-label">Elementos Sobrestamento:</div>
                <div class="info-value">{elementos_pje.get('elementos_sobrestamento', 0)}</div>
            </div>
            <div class="info-item">
                <div class="info-label">Itens na Timeline:</div>
                <div class="info-value">{elementos_pje.get('itens_timeline', 0)}</div>
            </div>
        </div>
    </div>

    <div class="section">
        <h3>📊 Tipos de Input Encontrados</h3>
        <table>
            <thead>
                <tr>
                    <th>Tipo</th>
                    <th>Quantidade</th>
                </tr>
            </thead>
            <tbody>
"""

        for tipo, quantidade in elementos_analisados.get('inputs', {}).get('tipos', {}).items():
            html_content += f"""
                <tr>
                    <td>{tipo}</td>
                    <td>{quantidade}</td>
                </tr>
"""

        html_content += """
            </tbody>
        </table>
    </div>

    <div class="section">
        <h3>💡 Recomendações</h3>
        <ul>
            <li>Verifique se os botões de tarefa estão visíveis e acessíveis</li>
            <li>Confirme se há elementos de sobrestamento na página atual</li>
            <li>Analise a timeline para verificar documentos disponíveis</li>
            <li>Teste a abertura de tarefas em novas abas</li>
        </ul>
    </div>
</body>
</html>
"""

        # Salva o arquivo HTML
        timestamp = time.strftime('%Y%m%d_%H%M%S')
        nome_arquivo = f"relatorio_debug_visual_{timestamp}.html"
        caminho_arquivo = os.path.join(os.getcwd(), nome_arquivo)

        with open(caminho_arquivo, 'w', encoding='utf-8') as f:
            f.write(html_content)

        if debug:
            print(f"[DEBUG_VISUAL] ✅ Relatório salvo em: {caminho_arquivo}")

        return caminho_arquivo

    except Exception as e:
        if debug:
            print(f"[DEBUG_VISUAL] ❌ Erro no debug visual: {e}")
        return None

def executar_debug_visual(driver, debug=True):
    """
    Função principal para executar debug visual completo.
    Esta é a função que deve ser chamada pelo exemplo_debug_visual.py
    """
    titulo = f"Debug Visual - {time.strftime('%d/%m/%Y %H:%M:%S')}"
    caminho_relatorio = debug_visual_completo(driver, titulo, debug)

    if caminho_relatorio:
        print(f"🎯 Debug visual concluído! Relatório: {caminho_relatorio}")

        # Tenta abrir o relatório no navegador padrão
        try:
            import webbrowser
            webbrowser.open(f"file://{caminho_relatorio}")
            print("📂 Relatório aberto no navegador")
        except:
            print("⚠️ Não foi possível abrir automaticamente no navegador")

        return True
    else:
        print("❌ Falha ao gerar relatório de debug visual")
        return False

# Função de exemplo para teste
if __name__ == "__main__":
    print("🔍 Inicializando Debug Visual do PJe Plus...")

    try:
        # Importa e inicializa driver
        from driver_config import criar_driver

        print("🌐 Criando driver...")
        driver = criar_driver()

        if driver:
            print("✅ Driver criado com sucesso")
            print("📊 Executando análise visual...")

            # Executa debug visual
            sucesso = executar_debug_visual(driver, debug=True)

            if sucesso:
                print("🎉 Debug visual concluído com sucesso!")
            else:
                print("❌ Falha na execução do debug visual")

            # Fecha o driver
            print("🔚 Fechando driver...")
            driver.quit()

        else:
            print("❌ Falha ao criar driver")

    except ImportError as e:
        print(f"❌ Erro de importação: {e}")
        print("Verifique se o módulo driver_config está disponível")
    except Exception as e:
        print(f"❌ Erro geral: {e}")
        import traceback
        traceback.print_exc()
