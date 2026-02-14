"""
PEC/petjs.py - TESTE DE PERFORMANCE: Extração via JavaScript
==============================================================

OBJETIVO: Testar se JavaScript direto é mais rápido que Selenium para ler tabela.

HIPÓTESE:
- Selenium: itera elemento por elemento (lento)
- JavaScript: lê tudo de uma vez, retorna JSON (rápido)

TESTE:
1. Driver VT + Login
2. Navega para escaninho
3. Aplica filtro 50 (SEM reordenar coluna)
4. Executa extração via JS puro
5. Compara tempo vs método tradicional
"""

import sys
import time
import os
import json
from datetime import datetime
from pathlib import Path
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Ajuste de path para importações
sys.path.insert(0, str(Path(__file__).parent.parent))

# ============================================================================
# CONFIGURAÇÕES VT - DRIVERS EMBUTIDOS (padrão 2.py)
# ============================================================================

# Caminho do geckodriver
GECKODRIVER_PATH = os.path.join(str(Path(__file__).parent.parent), 'geckodriver.exe')
if not os.path.exists(GECKODRIVER_PATH):
    GECKODRIVER_PATH = os.path.join(str(Path(__file__).parent.parent), 'Fix', 'geckodriver.exe')

# Firefox Developer Edition
FIREFOX_BINARY = r'C:\Program Files\Firefox Developer Edition\firefox.exe'
FIREFOX_BINARY_ALT = r'C:\Users\s164283\AppData\Local\Firefox Developer Edition\firefox.exe'

# Perfis VT
VT_PROFILE_PJE = r'C:\Users\Silas\AppData\Roaming\Mozilla\Firefox\Profiles\13zemix3.default-release-1623328432485'
VT_PROFILE_PJE_ALT = r'C:\Users\s164283\AppData\Roaming\Mozilla\Firefox\Profiles\2bge54ld.Robot'

ESCANINHO_URL = "https://pje.trt2.jus.br/pjekz/escaninho/peticoes-juntadas"


def criar_driver_vt(headless=False):
    """Cria driver Firefox VT (padrão 2.py)"""
    from selenium import webdriver
    from selenium.webdriver.firefox.options import Options
    from selenium.webdriver.firefox.service import Service
    
    if not os.path.exists(GECKODRIVER_PATH):
        print(f"[DRIVER_VT] ❌ Geckodriver não encontrado: {GECKODRIVER_PATH}")
        return None
    
    firefox_binaries = [FIREFOX_BINARY, FIREFOX_BINARY_ALT]
    firefox_bin_usado = None
    
    for bin_path in firefox_binaries:
        if os.path.exists(bin_path):
            firefox_bin_usado = bin_path
            break
    
    if not firefox_bin_usado:
        print(f"[DRIVER_VT] ❌ Nenhum binário Firefox encontrado")
        return None
    
    print(f"[DRIVER_VT] Usando binário: {firefox_bin_usado}")
    
    try:
        options = Options()
        if headless:
            options.add_argument('-headless')
        
        options.binary_location = firefox_bin_usado
        
        if os.path.exists(VT_PROFILE_PJE):
            options.profile = VT_PROFILE_PJE
            print(f"[DRIVER_VT] Perfil: {VT_PROFILE_PJE}")
        elif os.path.exists(VT_PROFILE_PJE_ALT):
            options.profile = VT_PROFILE_PJE_ALT
            print(f"[DRIVER_VT] Perfil alt: {VT_PROFILE_PJE_ALT}")
        else:
            print(f"[DRIVER_VT] ⚠️ Perfil temporário")
        
        options.set_preference("dom.webdriver.enabled", False)
        options.set_preference('useAutomationExtension', False)
        options.set_preference("dom.min_background_timeout_value", 0)
        options.set_preference("dom.timeout.throttling_delay", 0)
        options.set_preference("dom.timeout.budget_throttling_max_delay", 0)
        
        service = Service(executable_path=GECKODRIVER_PATH)
        driver = webdriver.Firefox(options=options, service=service)
        driver.implicitly_wait(10)
        driver.maximize_window()
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        print("[DRIVER_VT] ✅ Driver criado")
        return driver
        
    except Exception as e:
        print(f"[DRIVER_VT] ❌ Erro: {e}")
        return None


def aplicar_filtro_50(driver: WebDriver) -> bool:
    """Aplica filtro de 50 processos (igual pet2.py)"""
    try:
        print("[FILTRO50] Aplicando filtro...")
        
        span_20 = driver.find_element(By.XPATH, 
            "//span[contains(@class,'mat-select-min-line') and normalize-space(text())='20']")
        
        mat_select = span_20.find_element(By.XPATH, "ancestor::mat-select[@role='combobox']")
        driver.execute_script("arguments[0].scrollIntoView(true);", mat_select)
        time.sleep(0.3)
        driver.execute_script("arguments[0].click();", mat_select)
        time.sleep(0.5)
        
        overlay = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".cdk-overlay-pane"))
        )
        time.sleep(0.3)
        
        opcao_50 = overlay.find_element(By.XPATH, 
            ".//mat-option[.//span[normalize-space(text())='50']]")
        driver.execute_script("arguments[0].click();", opcao_50)
        time.sleep(1)
        
        print('[FILTRO50] ✅ Aplicado')
        return True
        
    except Exception as e:
        print(f'[FILTRO50] ❌ Erro: {e}')
        return False


def extrair_tabela_js(driver: WebDriver) -> dict:
    """
    EXTRAÇÃO VIA JAVASCRIPT PURO - LEITURA ÚNICA E RÁPIDA
    
    Retorna: {
        'tempo_ms': int,
        'total_linhas': int,
        'peticoes': [
            {
                'indice': 0,
                'numero_processo': '...',
                'tipo_peticao': '...',
                'descricao': '...',
                'tarefa': '...',
                'fase': '...',
                'data_juntada': '...'
            },
            ...
        ]
    }
    """
    js_code = """
    // ========================================================================
    // EXTRAÇÃO ULTRA-RÁPIDA VIA JAVASCRIPT PURO
    // ========================================================================
    
    const startTime = performance.now();
    const resultado = {
        tempo_ms: 0,
        total_linhas: 0,
        peticoes: []
    };
    
    try {
        // 1. Encontrar tabela
        const tabela = document.querySelector('table.mat-table, table[mat-table], table');
        if (!tabela) {
            throw new Error('Tabela não encontrada');
        }
        
        // 2. Extrair todas as linhas de dados (tbody > tr)
        const linhas = Array.from(tabela.querySelectorAll('tbody tr.mat-row, tbody tr'));
        console.log(`[JS_EXTRAÇÃO] Total de linhas encontradas: ${linhas.length}`);
        
        // 3. Iterar por todas as linhas e extrair células
        linhas.forEach((linha, idx) => {
            try {
                const tds = Array.from(linha.querySelectorAll('td'));
                
                if (tds.length < 7) {
                    console.warn(`[JS_EXTRAÇÃO] Linha ${idx} tem apenas ${tds.length} colunas, pulando...`);
                    return; // skip
                }
                
                // Extrair textos das células
                const textos = tds.map(td => td.innerText.trim());
                
                // Coluna 1: Número do processo (pode conter "Abrir a tarefa... ATOrd\\n1000123-...")
                let numero_processo = textos[1] || '';
                // Extrair apenas o número do processo (padrão: 7 dígitos-2 dígitos.4 dígitos.1 dígito.2 dígitos.4 dígitos)
                const match_processo = numero_processo.match(/\\d{7}-\\d{2}\\.\\d{4}\\.\\d{1}\\.\\d{2}\\.\\d{4}/);
                if (match_processo) {
                    numero_processo = match_processo[0];
                }
                
                // Coluna 6: "Tarefa - Fase: xxxx"
                const col6 = textos[6] || '';
                let tarefa = '';
                let fase = '';
                
                if (col6.includes('Fase:')) {
                    const partes = col6.split('Fase:');
                    tarefa = partes[0].replace(/^-\\s*/, '').trim();
                    fase = partes[1].trim();
                } else {
                    tarefa = col6.trim();
                }
                
                // Detectar se é PERÍCIA (palavras-chave em tipo, descrição ou tarefa/fase)
                const textoCompleto = `${textos[4]} ${textos[5]} ${tarefa} ${fase}`.toLowerCase();
                const eh_perito = /esclarecimento|laudo|perici|perito/.test(textoCompleto);
                
                // Detectar polo (Reclamante/Reclamada)
                let polo = null;
                if (/reclamante|autor|exequente/i.test(textoCompleto)) {
                    polo = 'ativo';
                } else if (/reclamad[oa]|r[eé]u|executad[oa]/i.test(textoCompleto)) {
                    polo = 'passivo';
                }
                
                // Extrair data de audiência se presente (coluna 3 ou outras)
                let data_audiencia = null;
                const col3 = textos[3] || '';
                if (/audiência|aud[iî]ncia/i.test(col3)) {
                    const matchData = col3.match(/\\d{2}\\/\\d{2}\\/\\d{4}/);
                    if (matchData) {
                        data_audiencia = matchData[0];
                    }
                }
                
                // Montar objeto
                const peticao = {
                    indice: idx,
                    numero_processo: numero_processo,
                    tipo_peticao: textos[4] || '',
                    descricao: textos[5] || '',
                    tarefa: tarefa,
                    fase: fase,
                    data_juntada: textos[7] || '',
                    eh_perito: eh_perito,
                    polo: polo,
                    data_audiencia: data_audiencia
                };
                
                resultado.peticoes.push(peticao);
                
            } catch (e) {
                console.error(`[JS_EXTRAÇÃO] Erro na linha ${idx}:`, e);
            }
        });
        
        resultado.total_linhas = resultado.peticoes.length;
        resultado.tempo_ms = Math.round(performance.now() - startTime);
        
        console.log(`[JS_EXTRAÇÃO] ✅ Extraídas ${resultado.total_linhas} petições em ${resultado.tempo_ms}ms`);
        
    } catch (e) {
        console.error('[JS_EXTRAÇÃO] ❌ Erro crítico:', e);
        resultado.erro = e.toString();
    }
    
    return resultado;
    """
    
    try:
        print("\n[PETJS] ═══════════════════════════════════════")
        print("[PETJS] EXECUTANDO EXTRAÇÃO VIA JAVASCRIPT")
        print("[PETJS] ═══════════════════════════════════════\n")
        
        inicio = time.time()
        resultado = driver.execute_script(js_code)
        fim = time.time()
        
        tempo_python = (fim - inicio) * 1000  # ms
        tempo_js = resultado.get('tempo_ms', 0)
        total = resultado.get('total_linhas', 0)
        
        print(f"\n[PETJS] ═══════════════════════════════════════")
        print(f"[PETJS] RESULTADO DA EXTRAÇÃO:")
        print(f"[PETJS] ═══════════════════════════════════════")
        print(f"[PETJS] Total de petições: {total}")
        print(f"[PETJS] Tempo JS puro: {tempo_js}ms")
        print(f"[PETJS] Tempo Python total: {tempo_python:.1f}ms")
        print(f"[PETJS] ═══════════════════════════════════════\n")
        
        # Mostrar primeiras 3 petições como amostra
        if resultado.get('peticoes'):
            print("[PETJS] AMOSTRA (primeiras 3 petições):")
            print("[PETJS] " + "─" * 60)
            for i, pet in enumerate(resultado['peticoes'][:3], 1):
                print(f"[PETJS] #{i} | {pet['numero_processo']}")
                print(f"[PETJS]    Tipo: {pet['tipo_peticao'][:50]}")
                print(f"[PETJS]    Desc: {pet['descricao'][:50]}")
                print(f"[PETJS]    Tarefa: {pet['tarefa'][:40]}")
                print(f"[PETJS]    Fase: {pet['fase'][:40]}")
                print(f"[PETJS] " + "─" * 60)
        
        return resultado
        
    except Exception as e:
        print(f"[PETJS] ❌ Erro ao executar JS: {e}")
        return {'erro': str(e), 'tempo_ms': 0, 'total_linhas': 0, 'peticoes': []}


def salvar_resultado_json(resultado: dict, arquivo: str = "petjs_resultado.json"):
    """Salva resultado em JSON para análise"""
    try:
        caminho = Path(__file__).parent / arquivo
        with open(caminho, 'w', encoding='utf-8') as f:
            json.dump(resultado, f, ensure_ascii=False, indent=2)
        print(f"[PETJS] 💾 Resultado salvo em: {caminho}")
    except Exception as e:
        print(f"[PETJS] ⚠️ Erro ao salvar JSON: {e}")


def converter_json_para_peticoes(peticoes_json: list) -> list:
    """
    Converte lista de petições JSON para objetos PeticaoLinha.
    Inclui campos: eh_perito, polo, data_audiencia
    """
    from pet2 import PeticaoLinha
    
    peticoes_objetos = []
    for pet_dict in peticoes_json:
        peticao = PeticaoLinha(
            numero_processo=pet_dict.get('numero_processo', ''),
            tipo_peticao=pet_dict.get('tipo_peticao', ''),
            descricao=pet_dict.get('descricao', ''),
            tarefa=pet_dict.get('tarefa', ''),
            fase=pet_dict.get('fase', ''),
            data_juntada=pet_dict.get('data_juntada', ''),
            elemento_html=None,
            eh_perito=pet_dict.get('eh_perito', False),
            data_audiencia=pet_dict.get('data_audiencia', None),
            polo=pet_dict.get('polo', None),
            indice=pet_dict.get('indice', 0)
        )
        peticoes_objetos.append(peticao)
    
    return peticoes_objetos


def processar_peticoes_js_integrado(driver: WebDriver) -> dict:
    """
    PROCESSAMENTO INTEGRADO COM EXTRAÇÃO JS
    
    Fluxo:
    1. Extrai tabela via JS (RÁPIDO - 3ms)
    2. Converte JSON para objetos PeticaoLinha
    3. Define regras (importa de pet2.py)
    4. Executa motor simplificado (testa hipóteses e executa ações)
    5. Retorna relatório
    """
    from pet2 import definir_regras, executar_regras_simplificado
    
    print("\n" + "="*70)
    print("PROCESSAMENTO INTEGRADO: Extração JS + Motor de Regras")
    print("="*70 + "\n")
    
    # 1. Extração JS (ULTRA-RÁPIDA)
    print("[INTEGRADO] ETAPA 1: Extração via JavaScript...")
    resultado_js = extrair_tabela_js(driver)
    
    if not resultado_js.get('peticoes'):
        print("[INTEGRADO] ❌ Nenhuma petição extraída")
        return {}
    
    print(f"[INTEGRADO] ✅ {len(resultado_js['peticoes'])} petições extraídas em {resultado_js['tempo_ms']}ms\n")
    
    # 2. Converter para objetos PeticaoLinha
    print("[INTEGRADO] ETAPA 2: Convertendo para objetos PeticaoLinha...")
    peticoes = converter_json_para_peticoes(resultado_js['peticoes'])
    print(f"[INTEGRADO] ✅ {len(peticoes)} objetos criados\n")
    
    # 3. Definir regras
    print("[INTEGRADO] ETAPA 3: Definindo regras de processamento...")
    regras_dict = definir_regras()
    total_hipoteses = sum(len(hipoteses) for hipoteses in regras_dict.values())
    print(f"[INTEGRADO] ✅ {len(regras_dict)} blocos, {total_hipoteses} hipóteses definidas\n")
    
    # 4. Executar motor (TESTE - apenas verifica matches, não executa ações reais)
    print("[INTEGRADO] ETAPA 4: Executando motor de regras (MODO TESTE)...")
    print("[INTEGRADO] " + "="*60 + "\n")
    
    resultado = executar_motor_teste(driver, peticoes, regras_dict)
    
    print("\n[INTEGRADO] " + "="*60)
    print("[INTEGRADO] ✅ Processamento concluído\n")
    
    return resultado


def executar_motor_teste(driver: WebDriver, peticoes: list, regras_dict: dict) -> dict:
    """
    Motor de execução em MODO TESTE (apenas identifica matches, não executa ações).
    Log agrupado por BLOCOS + grupo SEM MATCH (formato limpo, uma linha por petição)
    """
    from pet2 import verifica_peticao_contra_hipotese, verifica_peticao_pericias, verifica_peticao_diretos
    
    contadores = {bloco: 0 for bloco in regras_dict.keys()}
    ordem_blocos = ["pericias", "recurso", "diretos", "gigs", "analise", "apagar"]
    
    # Estrutura para agrupar resultados por bloco
    resultados_por_bloco = {bloco: [] for bloco in ordem_blocos}
    sem_match = []
    
    print(f"═══════════════════════════════════════════════════════════════════")
    print(f"PROCESSAMENTO DE {len(peticoes)} PETICOES (MODO TESTE)")
    print(f"═══════════════════════════════════════════════════════════════════\n")
    print("[Analisando...]\n")
    
    # Análise: classificar cada petição
    for idx, peticao in enumerate(peticoes, 1):
        executado = False
        
        for bloco in ordem_blocos:
            if bloco not in regras_dict:
                continue
            
            hipoteses = regras_dict[bloco]
            
            for nome_hipotese, patterns, acao in hipoteses:
                # Verificar match
                if bloco == "pericias":
                    match = verifica_peticao_pericias(peticao, patterns)
                elif bloco == "diretos":
                    match = verifica_peticao_diretos(peticao, patterns)
                else:
                    match = verifica_peticao_contra_hipotese(peticao, patterns)
                
                if match:
                    acao_nome = _obter_nome_acao(acao)
                    acao_detalhada = _formatar_acao_detalhada(acao, nome_hipotese)
                    resultados_por_bloco[bloco].append({
                        'idx': idx,
                        'processo': peticao.numero_processo,
                        'tipo': peticao.tipo_peticao,
                        'descricao': peticao.descricao,
                        'fase': peticao.fase,
                        'tarefa': peticao.tarefa,
                        'hipotese': nome_hipotese,
                        'acao': acao_nome,
                        'acao_detalhada': acao_detalhada
                    })
                    contadores[bloco] += 1
                    executado = True
                    break
            
            if executado:
                break
        
        if not executado:
            sem_match.append({
                'idx': idx,
                'processo': peticao.numero_processo,
                'tipo': peticao.tipo_peticao,
                'descricao': peticao.descricao
            })
    
    # Exibir resultados AGRUPADOS POR BLOCO
    print("═══════════════════════════════════════════════════════════════════")
    print("RESULTADOS AGRUPADOS POR BLOCO")
    print("═══════════════════════════════════════════════════════════════════\n")
    
    # SEM MATCH primeiro
    if sem_match:
        print(f"── SEM MATCH ({len(sem_match)} peticoes)\n")
        for item in sem_match:
            print(f"  {item['processo']} - {item['tipo']} ({item['descricao']})")
        print()
    
    # Blocos com matches
    for bloco in ordem_blocos:
        if resultados_por_bloco[bloco]:
            items = resultados_por_bloco[bloco]
            print(f"── BLOCO: {bloco.upper()} ({len(items)} peticoes)\n")
            for item in items:
                # Extrair campos relevantes para contexto
                contexto_partes = []
                if item.get('fase'):
                    contexto_partes.append(item['fase'])
                if item.get('tarefa') and item['tarefa'] != item['fase']:
                    contexto_partes.append(item['tarefa'])
                
                contexto = ", ".join(contexto_partes) if contexto_partes else ""
                contexto_str = f" ({contexto})" if contexto else ""
                
                print(f"  {item['processo']} - {item['hipotese']}{contexto_str} -> {item['acao_detalhada']}")
            print()
    
    # Resumo final
    print("═══════════════════════════════════════════════════════════════════")
    print("RESUMO FINAL:")
    print("═══════════════════════════════════════════════════════════════════")
    
    if sem_match:
        print(f"  SEM MATCH  : {len(sem_match):3d} peticoes")
    
    for bloco in ordem_blocos:
        if contadores[bloco] > 0:
            print(f"  {bloco.upper():10s} : {contadores[bloco]:3d} peticoes")
    
    print("═══════════════════════════════════════════════════════════════════\n")
    
    return contadores


def _formatar_acao_detalhada(acao, nome_hipotese: str) -> str:
    """
    Formata ação de forma detalhada para o log, identificando wrapper específico.
    
    Exemplos:
    - Wrapper específico: "ato_instc"
    - GIGS: "gigs(-1, Silvia homologacao)"
    - Tupla: "(gigs(...), ato_datalocal)"
    """
    if acao is None:
        return "None"
    
    # Tupla de ações
    if isinstance(acao, tuple):
        partes = []
        for sub_acao in acao:
            partes.append(_formatar_acao_detalhada(sub_acao, nome_hipotese))
        return f"({', '.join(partes)})"
    
    # Callable/Lambda - tentar identificar wrapper específico
    if callable(acao):
        # 1. Verificar se tem __name__ direto
        if hasattr(acao, '__name__'):
            nome = acao.__name__
            
            # Se começa com 'ato_', é um wrapper específico
            if nome.startswith('ato_'):
                return nome
            
            # Se é 'wrapper' genérico, tentar extrair o nome real da hipótese
            if nome == 'wrapper':
                # Mapear hipóteses para wrappers específicos (baseado em pet2.py)
                mapa_hipoteses = {
                    'Agravo de Instrumento - Conhecimento': 'ato_instc',
                    'Agravo de Instrumento - Liquidação/Execução': 'ato_inste',
                    'Solicitação de Habilitação - CEJU': 'ato_ceju',
                    'Apresentação de Cálculos': 'ato_respcalc',
                    'Assistente': 'ato_assistente',
                    'Concordância (Liquidação)': 'ato_concor',
                    'CAGED (Previdenciário)': 'ato_prevjud',
                    'Esclarecimentos ao Laudo - Conhecimento': 'ato_esc',
                    'Esclarecimentos ao Laudo - Liquidação': 'ato_escliq',
                    'Apresentação de Laudo Pericial': 'ato_laudo',
                    'Indicação de Data de Realização': 'ato_datalocal',
                }
                
                # Buscar wrapper específico pelo nome da hipótese
                if nome_hipotese in mapa_hipoteses:
                    return mapa_hipoteses[nome_hipotese]
                
                # Se não encontrou, retornar wrapper genérico
                return "wrapper"
            
            # Se é _gigs, tentar extrair parâmetros
            if nome == '_gigs' or 'gigs' in nome.lower():
                if hasattr(acao, '__closure__') and acao.__closure__:
                    try:
                        dias = None
                        obs = None
                        for cell in acao.__closure__:
                            val = cell.cell_contents
                            if isinstance(val, str):
                                if val.replace('-', '').isdigit():
                                    dias = val
                                else:
                                    obs = val
                        
                        if dias and obs:
                            return f"gigs({dias}, {obs})"
                        elif obs:
                            return f"gigs({obs})"
                    except:
                        pass
                
                return "gigs"
            
            # Outros callables
            return nome
        
        # 2. Lambda sem nome - verificar código
        if hasattr(acao, '__code__'):
            varnames = acao.__code__.co_names
            for varname in varnames:
                if varname.startswith('ato_'):
                    return varname
        
        return "lambda"
    
    return str(type(acao).__name__)


def _obter_nome_acao(acao) -> str:
    """Obtém nome legível da ação para log"""
    if acao is None:
        return "None"
    elif callable(acao):
        # Lambda ou função
        if hasattr(acao, '__name__'):
            return acao.__name__
        else:
            return "lambda/callable"
    elif isinstance(acao, tuple):
        # Tupla de ações
        nomes = [_obter_nome_acao(a) for a in acao]
        return f"({', '.join(nomes)})"
    else:
        return str(type(acao).__name__)


def main():
    """
    Fluxo de teste INTEGRADO:
    1. Driver VT
    2. Login
    3. Navega escaninho
    4. Filtro 50 (SEM reordenar)
    5. Extração JS + Motor de Regras INTEGRADO
    """
    from Fix.utils import login_cpf
    
    print("\n" + "="*70)
    print("TESTE INTEGRADO: Extração JS + Motor de Regras")
    print("="*70 + "\n")
    
    driver = None
    try:
        # 1. Driver
        print("[MAIN] 1/5 - Criando driver VT...")
        driver = criar_driver_vt(headless=False)
        if not driver:
            print("[MAIN] ❌ Falha ao criar driver")
            return
        print("[MAIN] ✅ Driver criado\n")
        
        # 2. Login
        print("[MAIN] 2/5 - Realizando login...")
        if not login_cpf(driver):
            print("[MAIN] ❌ Falha no login")
            return
        print("[MAIN] ✅ Login OK\n")
        
        # 3. Navegar
        print(f"[MAIN] 3/5 - Navegando para escaninho...")
        driver.get(ESCANINHO_URL)
        time.sleep(2)
        print("[MAIN] ✅ Navegação OK\n")
        
        # 4. Filtro 50
        print("[MAIN] 4/5 - Aplicando filtro 50...")
        if not aplicar_filtro_50(driver):
            print("[MAIN] ⚠️ Filtro pode ter falhado, continuando...")
        time.sleep(2)
        print("[MAIN] ✅ Filtro OK\n")
        
        # 5. PROCESSAMENTO INTEGRADO
        print("[MAIN] 5/5 - PROCESSAMENTO INTEGRADO...")
        print("[MAIN] " + "="*60 + "\n")
        
        resultado = processar_peticoes_js_integrado(driver)
        
        # Aguardar para inspeção manual
        input("\n⏸️  Pressione ENTER para fechar o navegador...")
        
    except KeyboardInterrupt:
        print("\n[MAIN] ⚠️ Interrompido pelo usuário")
    except Exception as e:
        print(f"[MAIN] ❌ Erro fatal: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if driver:
            print("\n[MAIN] Fechando driver...")
            try:
                driver.quit()
                print("[MAIN] ✅ Driver fechado")
            except:
                pass


if __name__ == "__main__":
    main()
