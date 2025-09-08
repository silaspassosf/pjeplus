from atos import pec_decisao
import sys
import os
from datetime import datetime

with open("log.py", "w", encoding="utf-8") as f:
    f.write(f"# Última execução: {datetime.now()}\n")
    f.write(f"# Script: {os.path.abspath(sys.argv[0])}\n")
    f.write(f"# Argumentos: {' '.join(sys.argv[1:])}\n")

###DIRETRIZES MÁXIMAS INEGOCIÁVEIS
# Priorizar edições apenas no código selecionado ou referenciado  
# Sempre validar se as alterações propostas estão estritamente alinhadas com o prompt do usuário.  
# Evitar modificações em arquivos não explicitamente mencionados.  
# Respeitar convenções de estilo definidas no projeto (ex: indentação com tabs, aspas duplas).  
# Workspace preference: NÃO altere, traduza ou reescreva NENHUMA linha do código, exceto exatamente o trecho solicitado.
# NÃO traduza palavras-chave, nomes de variáveis, comentários, strings, nem nada do código.
# NÃO faça ajustes automáticos, refatorações, nem 'melhorias' não solicitadas.
# Se precisar editar, use sempre o padrão # ...existing code... para indicar partes não alteradas. 
# As edições devem ser ESPECIFICAMENTE sobre erros de log ou pedidos EXPLICITOS do usuario, nada alem disso.
# tenha em mente que descumprir essas diretizes estraga o codigo e causa perda de tempo
# nao é neceasário varrer o codigo todo para cada edição pedida 
# use a busca de termos para ir diretamente à região correta e edirtar apenas o necessário, para ser mais eficiente

from Fix import login_pc, driver_notebook, aplicar_filtro_100, indexar_e_processar_lista, extrair_dados_processo, finalizar_driver
import json
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import re
import logging
import os
from Fix import esperar_elemento, safe_click, criar_gigs, login_pc, aplicar_filtro_100, extrair_documento, extrair_direto, indexar_e_processar_lista, login_notebook, driver_pc
from atos import ato_pesquisas, ato_sobrestamento, ato_180, mov_arquivar, mov_exec, ato_pesqliq, ato_calc2, ato_prev, ato_meios, ato_termoS, ato_termoE, executar_visibilidade_sigilosos_se_necessario, pec_excluiargos
from selenium.common.exceptions import NoSuchElementException, TimeoutException, StaleElementReferenceException
from selenium.webdriver.common.keys import Keys
from driver_config import criar_driver, login_func

# Função de compatibilidade para callbacks que esperam função sem retorno
def ato_pesquisas_callback(driver):
    """Wrapper para manter compatibilidade com callbacks antigos"""
    sucesso, sigilo_ativado = ato_pesquisas(driver)
    if sucesso and sigilo_ativado:
        executar_visibilidade_sigilosos_se_necessario(driver, sigilo_ativado, debug=True)
    return sucesso

def ato_pesqliq_callback(driver):
    """Wrapper para manter compatibilidade com callbacks antigos"""
    sucesso, sigilo_ativado = ato_pesqliq(driver)
    if sucesso and sigilo_ativado:
        executar_visibilidade_sigilosos_se_necessario(driver, sigilo_ativado, debug=True)
    return sucesso

def prescreve(driver):
    """
    Função para tratar prescrição.
    REGRA DE ALTA PRIORIDADE: Trecho "A pronúncia da"
    
    Fluxo:
    0. Executa Bndt (placeholder)
    1. Checagem de timeline (baseada no script JS)
    2. Ações em ORDEM:
       - Alvará → função pagamento
       - Serasa/CNIB em anexo → pec_exclusao
       - Serasa fora de anexos + nenhum Serasa em anexos → criar_gigs
    """
    try:
        print('[PRESCREVE] 🚨 PRESCRIÇÃO DETECTADA - Iniciando fluxo')
        
        # 0. Executa Bndt (placeholder)
        print('[PRESCREVE] 0. Executando Bndt...')
        bndt_resultado = bndt_placeholder(driver)
        if not bndt_resultado:
            print('[PRESCREVE] ⚠️ Falha no Bndt, continuando fluxo')
        
        # 1. Checagem de timeline
        print('[PRESCREVE] 1. Analisando timeline...')
        documentos = analisar_timeline_prescreve_js_puro(driver)
        
        if not documentos:
            print('[PRESCREVE] ❌ Nenhum documento relevante encontrado na timeline')
            return False
        
        # 2. Executar ações em ORDEM SEQUENCIAL
        print('[PRESCREVE] 2. Executando ações sequenciais...')
        
        # Ação 1: Localizar Alvarás e chamar função pagamento
        alvaras = [d for d in documentos if d.get('tipo', '').lower() == 'alvará']
        if alvaras:
            print(f'[PRESCREVE] 📋 {len(alvaras)} Alvará(s) encontrado(s) - executando função pagamento')
            try:
                # Importar e usar a função unificada de processamento de alvarás
                from processar_alvaras import processar_alvaras_completo
                
                resultado_pagamentos = processar_alvaras_completo(
                    driver=driver, 
                    alvaras_encontrados=alvaras, 
                    log=True
                )
                
                if resultado_pagamentos.get('sucesso'):
                    print('[PRESCREVE] ✅ Processamento de alvarás concluído com sucesso')
                    print(f'[PRESCREVE] 📊 Resumo: {len(resultado_pagamentos.get("alvaras_processados", []))} processados, '
                          f'{len(resultado_pagamentos.get("alvaras_registrados", []))} já registrados, '
                          f'{len(resultado_pagamentos.get("alvaras_sem_registro", []))} sem registro')
                else:
                    print('[PRESCREVE] ⚠️ Houve problemas no processamento de alvarás')
                    
            except Exception as e:
                print(f'[PRESCREVE] ❌ Erro no processamento de alvarás: {e}')
        
        # Ação 2: Localizar Serasa/CNIB em anexos e chamar pec_excluiargos
        anexos_serasa_cnib = [d for d in documentos if d.get('isAnexo', False) and d.get('tipo', '').lower() in ['serasa', 'cnib']]
        if anexos_serasa_cnib:
            print(f'[PRESCREVE] 📋 {len(anexos_serasa_cnib)} anexo(s) Serasa/CNIB encontrado(s) - executando pec_excluiargos')
            for anexo in anexos_serasa_cnib:
                try:
                    resultado = pec_excluiargos(driver)
                    if resultado:
                        print(f'[PRESCREVE] ✅ pec_excluiargos executado para anexo: {anexo.get("tipo", "N/A")} ID: {anexo.get("id", "N/A")}')
                    else:
                        print(f'[PRESCREVE] ⚠️ Falha no pec_excluiargos para anexo: {anexo.get("tipo", "N/A")}')
                except Exception as e:
                    print(f'[PRESCREVE] ❌ Erro ao executar pec_excluiargos: {e}')
        
        # Ação 3: Serasa fora de anexos + nenhum Serasa em anexos = criar_gigs
        serasa_timeline = [d for d in documentos if not d.get('isAnexo', False) and 'serasa' in d.get('tipo', '').lower()]
        tem_serasa_anexo = any(d.get('isAnexo', False) and 'serasa' in d.get('tipo', '').lower() for d in documentos)
        
        if serasa_timeline and not tem_serasa_anexo:
            print(f'[PRESCREVE] 📋 {len(serasa_timeline)} Serasa fora de anexos + nenhum Serasa em anexos - criando GIGS')
            try:
                resultado = criar_gigs(driver, "1", "Bianca", "Serasa")
                if resultado:
                    print('[PRESCREVE] ✅ GIGS criado: 1/Bianca/Serasa')
                else:
                    print('[PRESCREVE] ⚠️ Falha ao criar GIGS')
            except Exception as e:
                print(f'[PRESCREVE] ❌ Erro ao criar GIGS: {e}')
        
        print('[PRESCREVE] ✅ Fluxo de prescrição concluído')
        return True
        
    except Exception as e:
        print(f'[PRESCREVE] ❌ Erro geral na função prescreve: {e}')
        return False

def bndt_placeholder(driver):
    """Placeholder para função Bndt"""
    print('[PRESCREVE][BNDT] 📋 Placeholder - implementar lógica Bndt')
    return True

def funcao_pagamento_placeholder(driver, alvara_info):
    """Placeholder para função de pagamento de Alvará"""
    print(f'[PRESCREVE][PAGAMENTO] 📋 Placeholder - implementar pagamento para Alvará: {alvara_info.get("texto", "N/A")}')
    return True

def analisar_timeline_prescreve_js_puro(driver):
    """
    Análise da timeline usando JavaScript PURO - replicando o script fornecido.
    Executa em SEGUNDOS como o userscript original.
    """
    try:
        print('[PRESCREVE][TIMELINE] Executando análise via JavaScript PURO...')
        
        # JavaScript DIRETO baseado no script fornecido
        js_script = """
        function lerTimelineCompleta() {
            const seletores = ['li.tl-item-container', '.tl-data .tl-item-container', '.timeline-item'];
            let itens = [];
            for (const sel of seletores) {
                itens = document.querySelectorAll(sel);
                if (itens.length) break;
            }
            const documentos = [];

            function extrairUid(link) {
                const m = link.textContent.trim().match(/\\s-\\s([A-Za-z0-9]+)$/);
                return m ? m[1] : null;
            }
            
            function extrairData(item) {
                const dEl = item.querySelector('.tl-data[name="dataItemTimeline"]') || item.querySelector('.tl-data');
                const txt = dEl?.textContent.trim() || '';
                const m = txt.match(/(\\d{1,2}\\/\\d{1,2}\\/\\d{4})/);
                return m ? m[1] : '';
            }

            for (let i = 0; i < itens.length; i++) {
                const item = itens[i];
                const link = item.querySelector('a.tl-documento:not([target])');
                if (!link) continue;

                const texto = link.textContent.trim();
                const low = texto.toLowerCase();
                const id = extrairUid(link) || `doc${i}`;
                let tipoEncontrado = null;

                if (low.includes('devolução de ordem')) {
                    tipoEncontrado = 'Certidão devolução pesquisa';
                } else if (low.includes('certidão de oficial') || low.includes('oficial de justiça')) {
                    tipoEncontrado = 'Certidão de oficial de justiça';
                } else if (low.includes('alvará') || low.includes('alvara')) {
                    tipoEncontrado = 'Alvará';
                } else if (low.includes('sobrestamento')) {
                    tipoEncontrado = 'Decisão (Sobrestamento)';
                } else if (low.includes('serasa') || low.includes('apjur') || low.includes('carta ação') || low.includes('carta acao')) {
                    tipoEncontrado = 'SerasaAntigo';
                }
                if (!tipoEncontrado) continue;

                // Registrar documento principal
                documentos.push({
                    tipo: tipoEncontrado,
                    texto: texto,
                    id: id,
                    data: extrairData(item),
                    isAnexo: false
                });

                // Para certidões: buscar anexos Serasa/CNIB
                const isCertAlvo = (
                    tipoEncontrado === 'Certidão devolução pesquisa' ||
                    tipoEncontrado === 'Certidão de oficial de justiça'
                );
                if (isCertAlvo) {
                    const anexosRoot = item.querySelector('pje-timeline-anexos');
                    const toggle = item.querySelector('pje-timeline-anexos div[name="mostrarOuOcultarAnexos"]');
                    let anexoLinks = anexosRoot ? anexosRoot.querySelectorAll('a.tl-documento[id^="anexo_"]') : [];
                    
                    // Expandir anexos se necessário (sem sleep - síncrono)
                    if ((!anexoLinks || anexoLinks.length === 0) && toggle) {
                        try { 
                            toggle.dispatchEvent(new MouseEvent('click', { bubbles: true })); 
                            // Buscar novamente imediatamente
                            anexoLinks = item.querySelectorAll('a.tl-documento[id^="anexo_"]');
                        } catch(e) {}
                    }
                    
                    if (anexoLinks && anexoLinks.length) {
                        Array.from(anexoLinks).forEach(anexo => {
                            const t = (anexo.textContent || '').toLowerCase();
                            const parentData = extrairData(item);
                            if (/serasa|serasajud/.test(t)) {
                                documentos.push({
                                    tipo: 'Serasa',
                                    texto: anexo.textContent.trim(),
                                    id: anexo.id || `serasa_${id}`,
                                    data: parentData,
                                    isAnexo: true,
                                    parentId: id
                                });
                            } else if (/cnib|indisp/.test(t)) {
                                documentos.push({
                                    tipo: 'CNIB',
                                    texto: anexo.textContent.trim(),
                                    id: anexo.id || `cnib_${id}`,
                                    data: parentData,
                                    isAnexo: true,
                                    parentId: id
                                });
                            }
                        });
                    }
                }
            }
            return documentos;
        }

        // Aplicar FILTROS do script original
        function aplicarFiltros(docs) {
            return docs.filter(d => {
                try {
                    const tipo = (d.tipo||'').toString().toLowerCase();
                    const texto = (d.texto||'').toString().toLowerCase();
                    
                    // Filtro de expedição de ordem
                    if (/expedi[cç][aã]o/.test(tipo) && /ordem/.test(tipo)) return false;
                    if (/expedi[cç][aã]o/.test(texto) && /ordem/.test(texto)) return false;
                    
                    // Filtro específico para alvarás (CRÍTICO!)
                    if (tipo === 'alvará' || texto.includes('alvar')) {
                        if (/(expedi[cç][aã]o|expedid[ao]s?|devolvid[ao]s?)/.test(texto)) return false;
                    }
                } catch (e) {}
                return true;
            });
        }

        try {
            const docs = lerTimelineCompleta();
            const docsFiltrados = aplicarFiltros(docs);
            return JSON.stringify(docsFiltrados);
        } catch (e) {
            return JSON.stringify({error: e.message});
        }
        """
        
        # Executar JavaScript e capturar resultado
        import time
        start_time = time.time()
        
        resultado_json = driver.execute_script(js_script)
        
        elapsed = time.time() - start_time
        print(f'[PRESCREVE][TIMELINE] ✅ JavaScript executado em {elapsed:.2f}s')
        
        # Processar resultado
        import json
        try:
            documentos_data = json.loads(resultado_json)
            
            if isinstance(documentos_data, dict) and 'error' in documentos_data:
                print(f'[PRESCREVE][TIMELINE] ❌ Erro no JavaScript: {documentos_data["error"]}')
                return []
            
            # Converter para formato esperado pelo Python
            documentos = []
            for doc in documentos_data:
                documentos.append({
                    'tipo': doc.get('tipo', ''),
                    'texto': doc.get('texto', ''),
                    'id': doc.get('id', ''),
                    'data': doc.get('data', ''),
                    'isAnexo': doc.get('isAnexo', False),
                    'parentId': doc.get('parentId', None)
                })
            
            print(f'[PRESCREVE][TIMELINE] ✅ {len(documentos)} documentos encontrados via JavaScript')
            
            # Log resumido
            tipos_count = {}
            for doc in documentos:
                tipos_count[doc['tipo']] = tipos_count.get(doc['tipo'], 0) + 1
            
            for tipo, count in tipos_count.items():
                print(f'[PRESCREVE][TIMELINE]   - {tipo}: {count}')
            
            return documentos
            
        except json.JSONDecodeError as e:
            print(f'[PRESCREVE][TIMELINE] ❌ Erro ao decodificar JSON: {e}')
            print(f'[PRESCREVE][TIMELINE] Resultado recebido: {resultado_json[:200]}...')
            return []
        
    except Exception as e:
        print(f'[PRESCREVE][TIMELINE] ❌ Erro na análise JavaScript: {e}')
        return []

# Configuração do logging (CORRIGIDA)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    handlers=[
        logging.FileHandler('pje_automacao.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('AutomacaoPJe')

# ===== FUNÇÕES DE PROGRESSO PARA P2B =====
def carregar_progresso_p2b():
    """Carrega o estado de progresso do arquivo JSON específico para P2B"""
    try:
        if os.path.exists("progresso_p2b.json"):
            with open("progresso_p2b.json", "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        print(f"[PROGRESSO_P2B][AVISO] Erro ao carregar progresso: {e}")
    return {"processos_executados": [], "session_active": True, "last_update": None}

def salvar_progresso_p2b(progresso):
    """Salva o estado de progresso no arquivo JSON específico para P2B"""
    try:
        progresso["last_update"] = datetime.now().isoformat()
        with open("progresso_p2b.json", "w", encoding="utf-8") as f:
            json.dump(progresso, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[PROGRESSO_P2B][ERRO] Falha ao salvar progresso: {e}")

def extrair_numero_processo_p2b(driver):
    """Extrai o número do processo da URL ou elemento da página (adaptado para P2B)"""
    try:
        url = driver.current_url
        
        # Primeiro tenta extrair o ID da URL
        if "processo/" in url:
            match = re.search(r"processo/(\d+)", url)
            if match:
                id_processo = match.group(1)
                return id_processo
        
        # Depois tenta extrair o número formatado dos elementos
        try:
            candidatos = driver.find_elements(By.CSS_SELECTOR, 'h1, h2, h3, .processo-numero, [data-testid*="numero"], .cabecalho')
            for elemento in candidatos:
                texto = elemento.text.strip()
                if texto:
                    match = re.search(r'(\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4})', texto)
                    if match:
                        numero_formatado = re.sub(r'[^\d]', '', match.group(1))
                        return numero_formatado
        except Exception:
            pass
        
        return None
    except Exception as e:
        print(f"[PROGRESSO_P2B][ERRO] Falha ao extrair número do processo: {e}")
        return None

def verificar_acesso_negado_p2b(driver):
    """Verifica se estamos na página de acesso negado no sistema P2B"""
    try:
        url_atual = driver.current_url
        return "acesso-negado" in url_atual.lower() or "login.jsp" in url_atual.lower()
    except Exception as e:
        print(f"[PROGRESSO_P2B][ERRO] Falha ao verificar acesso negado: {e}")
        return False

def processo_ja_executado_p2b(numero_processo, progresso):
    """Verifica se o processo já foi executado no fluxo P2B"""
    if not numero_processo:
        return False
    return numero_processo in progresso.get("processos_executados", [])

def marcar_processo_executado_p2b(numero_processo, progresso):
    """Marca processo como executado no fluxo P2B"""
    if numero_processo and numero_processo not in progresso.get("processos_executados", []):
        progresso.setdefault("processos_executados", []).append(numero_processo)
        salvar_progresso_p2b(progresso)
        print(f"[PROGRESSO_P2B] Processo {numero_processo} marcado como executado")

def processo_ja_executado(numero_processo, progresso):
    """Verifica se o processo já foi executado"""
    if not numero_processo:
        return False
    return numero_processo in progresso.get("processos_executados", [])

def marcar_processo_executado(numero_processo, progresso):
    """Marca processo como executado (mantido inativo como em m1.py)"""
    # Função desativada para não registrar processos como executados nesta execução
    pass

def recuperar_sessao(driver):
    """Tenta recuperar sessão após acesso negado (comportamento similar ao m1.py)"""
    try:
        print("[RECOVERY_P2B][SESSÃO] Detectado acesso negado, tentando recuperar sessão...")
        # Navega para página de login padrão (usa variável de ambiente se existir)
        login_url = os.getenv('URL_PJE_LOGIN', 'https://pje.trt2.jus.br/pjekz/login')
        driver.get(login_url)
        time.sleep(3)

        # Chama função de login existente
        if login_func(driver):
            print("[RECOVERY_P2B][SESSÃO] ✅ Login realizado com sucesso")
            # Navega de volta para a lista padrão
            url_lista = os.getenv('URL_PJE_ESCANINHO', 'https://pje.trt2.jus.br/pjekz/escaninho/documentos-internos')
            driver.get(url_lista)
            time.sleep(3)
            try:
                icone_selector = 'i.fa-reply-all.icone-clicavel'
                resultado = safe_click(driver, icone_selector, timeout=10, log=True)
                if resultado:
                    print("[RECOVERY_P2B][SESSÃO] ✅ Filtro de mandados devolvidos reaplicado")
                    time.sleep(2)
                    return True
                else:
                    print("[RECOVERY_P2B][SESSÃO] ❌ Falha ao reaplicar filtro")
            except Exception as filter_error:
                print(f"[RECOVERY_P2B][SESSÃO][ERRO] Falha no filtro: {filter_error}")
        else:
            print("[RECOVERY_P2B][SESSÃO] ❌ Falha no login")
        return False
    except Exception as e:
        print(f"[RECOVERY_P2B][SESSÃO][ERRO] Falha na recuperação: {e}")
        return False

def resetar_progresso():
    """Reseta o arquivo de progresso - útil para reiniciar do zero"""
    try:
        if os.path.exists("progresso_p2b.json"):
            os.remove("progresso_p2b.json")
            print("[PROGRESSO_P2B][RESET] ✅ Arquivo de progresso removido")
        else:
            print("[PROGRESSO_P2B][RESET] ❌ Arquivo de progresso não existe")
    except Exception as e:
        print(f"[PROGRESSO_P2B][RESET][ERRO] Falha ao resetar: {e}")

def listar_processos_executados():
    """Lista processos já executados"""
    progresso = carregar_progresso_p2b()
    executados = progresso.get("processos_executados", [])
    if executados:
        print(f"[PROGRESSO_P2B][LIST] {len(executados)} processos já executados:")
        for i, proc in enumerate(executados, 1):
            print(f"  {i:3d}. {proc}")
    else:
        print("[PROGRESSO_P2B][LIST] Nenhum processo executado ainda")
    return executados

def reset_progresso_p2b():
    """Limpa o progresso de execução do P2B"""
    try:
        if os.path.exists("progresso_p2b.json"):
            os.remove("progresso_p2b.json")
            print("[PROGRESSO_P2B][RESET] Progresso limpo com sucesso")
        else:
            print("[PROGRESSO_P2B][RESET] Arquivo de progresso não existe")
    except Exception as e:
        print(f"[PROGRESSO_P2B][RESET][ERRO] Falha ao limpar progresso: {e}")

def reaplicar_filtros_p2b(driver):
    """Reaplica os filtros específicos do P2B após recovery do driver"""
    try:
        print("[RECOVERY_P2B][FILTROS] Reaplicando filtros específicos do P2B...")
        
        # 1. Navegar para atividades
        url_atividades = 'https://pje.trt2.jus.br/pjekz/gigs/relatorios/atividades'
        driver.get(url_atividades)
        time.sleep(3)
        
        # 2. Aplicar filtro de 100 itens por página
        from Fix import aplicar_filtro_100
        if not aplicar_filtro_100(driver):
            print("[RECOVERY_P2B][FILTROS] ❌ Falha ao aplicar filtro de 100 itens")
            return False
        time.sleep(2)
        
        # 3. Remover chip "Vencidas"
        try:
            chip_remove_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[ngclass="chips-icone-fechar"][mattooltip="Remover filtro"]'))
            )
            safe_click(driver, chip_remove_button)
        except Exception as e:
            print(f"[RECOVERY_P2B][FILTROS] Chip 'Vencidas' não encontrado ou já removido: {e}")
        
        # 4. Clicar no ícone fa-pen
        btn_fa_pen = esperar_elemento(driver, 'i.fa-pen', timeout=15)
        if not btn_fa_pen:
            print("[RECOVERY_P2B][FILTROS] ❌ Botão fa-pen não encontrado")
            return False
        safe_click(driver, btn_fa_pen)
        
        # 5. Aplicar filtro "xs"
        campo_descricao = esperar_elemento(driver, 'input[aria-label*="Descrição"]', timeout=15)
        if not campo_descricao:
            print("[RECOVERY_P2B][FILTROS] ❌ Campo descrição não encontrado")
            return False
        campo_descricao.clear()
        campo_descricao.send_keys('xs')
        campo_descricao.send_keys(Keys.ENTER)
        time.sleep(3)
        
        print("[RECOVERY_P2B][FILTROS] ✅ Filtros P2B reaplicados com sucesso")
        return True
        
    except Exception as e:
        print(f"[RECOVERY_P2B][FILTROS][ERRO] Falha ao reaplicar filtros: {e}")
        return False


def parse_gigs_param(param):
    """
    Recebe uma string no formato 'dias/responsavel/observacao' e retorna (dias, responsavel, observacao).
    Se não houver responsável, deve ser 'dias/-/observacao'.
    """
    if isinstance(param, str) and param.count('/') >= 2:
        partes = param.split('/', 2)
        try:
            dias = int(partes[0]) if partes[0].isdigit() else 0
        except Exception:
            dias = 0
        responsavel = partes[1].strip()
        observacao = partes[2].strip()
        return dias, responsavel, observacao
    # fallback: dias=0, responsavel='', observacao=param
    return 0, '', param

def checar_anexos_tendo_em_vista():
    """
    Verifica se existem documentos sigilosos em pesquisa patrimonial
    e chama a função apropriada baseada no resultado.
    """
    global driver
    sigiloso = checar_anexos(driver)
    
    if sigiloso == 'nao':
        # Não há documentos sigilosos, chama ato_meios
        ato_meios()
    elif sigiloso == 'sim':
        # Há documentos sigilosos, chama ato_termoE
        ato_termoE()
    else:
        # Caso de erro ou não encontrado
        print(f"checar_anexos retornou valor inesperado: {sigiloso}")
        print("Não foi possível determinar se há documentos sigilosos")

def checar_anexos_instauracao():
    """
    Verifica se existem documentos sigilosos em pesquisa patrimonial
    e chama a função apropriada baseada no resultado.
    """
    global driver
    sigiloso = checar_anexos(driver)
    
    if sigiloso == 'nao':
        # Não há documentos sigilosos, chama ato_meios
        ato_meios()
    elif sigiloso == 'sim':
        # Há documentos sigilosos, chama ato_termoS
        ato_termoS()
    else:
        # Caso de erro ou não encontrado
        print(f"checar_anexos retornou valor inesperado: {sigiloso}")
        print("Não foi possível determinar se há documentos sigilosos")

def checar_anexos(driver, log=True):
    """
    Função que seleciona 'pesquisa patrimonial' na timeline, abre seus anexos,
    verifica se há documentos sigilosos e retorna 'sim' ou 'nao'.
    
    Args:
        driver: WebDriver do Selenium
        log: Boolean para ativar logs detalhados
        
    Returns:
        str: 'sim' se houver anexos sigilosos, 'nao' caso contrário
    """
    if log:
        print('[CHECAR_ANEXOS] Iniciando verificação de anexos sigilosos...')
    
    try:
        # 1. Seleciona "pesquisa patrimonial" na timeline
        if log:
            print('[CHECAR_ANEXOS] 1. Buscando documento "pesquisa patrimonial" na timeline...')
        
        # Busca itens da timeline
        itens_timeline = driver.find_elements(By.CSS_SELECTOR, 'li.tl-item-container')
        documento_encontrado = None
        
        for item in itens_timeline:
            try:
                # Busca link do documento
                link = item.find_element(By.CSS_SELECTOR, 'a.tl-documento:not([target="_blank"])')
                texto_documento = link.text.lower()
                
                # Verifica se é pesquisa patrimonial (apenas este termo)
                if 'pesquisa patrimonial' in texto_documento:
                    documento_encontrado = item
                    if log:
                        print(f'[CHECAR_ANEXOS] ✓ Documento encontrado: {link.text}')
                    break  # Para na primeira ocorrência
            except Exception:
                continue
        
        if not documento_encontrado:
            if log:
                print('[CHECAR_ANEXOS] ❌ Documento "pesquisa patrimonial" não encontrado na timeline')
            return 'nao'
        
        # 2. Abre os anexos do documento
        if log:
            print('[CHECAR_ANEXOS] 2. Abrindo anexos do documento...')
        
        btn_anexos = documento_encontrado.find_elements(By.CSS_SELECTOR, "pje-timeline-anexos > div > div")
        if not btn_anexos:
            if log:
                print('[CHECAR_ANEXOS] ❌ Botão de anexos não encontrado')
            return 'nao'
        
        safe_click(driver, btn_anexos[0])
        time.sleep(2)
        
        # 3. Verifica se há documentos sigilosos nos anexos
        if log:
            print('[CHECAR_ANEXOS] 3. Verificando anexos sigilosos...')
        
        anexos = driver.find_elements(By.CSS_SELECTOR, ".tl-item-anexo")
        
        if not anexos:
            if log:
                print('[CHECAR_ANEXOS] ❌ Nenhum anexo encontrado')
            return 'nao'
        
        if log:
            print(f'[CHECAR_ANEXOS] ✓ Encontrados {len(anexos)} anexos')
        
        # Tipos de anexos que devem ser considerados sigilosos
        tipos_sigilosos = ["infojud", "doi", "irpf", "ir2022", "ir2023", "ir2024", "dimob", "ecac", "efinanceira", "e-financeira"]
        
        tem_sigiloso = False
        
        for anexo in anexos:
            try:
                texto_anexo = anexo.text.strip().lower()
                if log:
                    print(f'[CHECAR_ANEXOS] Verificando anexo: {texto_anexo}')
                
                # Verifica se é um tipo de anexo sigiloso
                for tipo in tipos_sigilosos:
                    if tipo in texto_anexo:
                        if log:
                            print(f'[CHECAR_ANEXOS] ✓ Anexo sigiloso encontrado: {tipo} em "{texto_anexo}"')
                        
                        # Verifica se já tem sigilo aplicado (ícone vermelho)
                        btn_sigilo = anexo.find_elements(By.CSS_SELECTOR, "i.fa-wpexplorer")
                        if btn_sigilo:
                            if "tl-nao-sigiloso" in btn_sigilo[0].get_attribute("class"):
                                # Ícone azul - não tem sigilo
                                if log:
                                    print(f'[CHECAR_ANEXOS] Anexo sem sigilo aplicado: {texto_anexo}')
                            else:
                                # Ícone vermelho - já tem sigilo
                                tem_sigiloso = True
                                if log:
                                    print(f'[CHECAR_ANEXOS] ✓ Anexo com sigilo já aplicado: {texto_anexo}')
                        else:
                            # Considera sigiloso por tipo, mesmo sem ícone
                            tem_sigiloso = True
                            if log:
                                print(f'[CHECAR_ANEXOS] ✓ Anexo considerado sigiloso por tipo: {texto_anexo}')
                        
                        break  # Para no primeiro tipo encontrado
                        
            except Exception as e:
                if log:
                    print(f'[CHECAR_ANEXOS] Erro ao verificar anexo: {e}')
                continue
        
        # 4. Retorna resultado
        resultado = 'sim' if tem_sigiloso else 'nao'
        if log:
            print(f'[CHECAR_ANEXOS] ✓ Resultado final: {resultado}')
            if tem_sigiloso:
                print('[CHECAR_ANEXOS] Documentos sigilosos encontrados nos anexos')
            else:
                print('[CHECAR_ANEXOS] Nenhum documento sigiloso encontrado nos anexos')
        
        return resultado
        
    except Exception as e:
        if log:
            print(f'[CHECAR_ANEXOS] ❌ Erro durante verificação: {e}')
        return 'nao'

def checar_prox(driver, itens, doc_idx, regras, texto_normalizado):
    """
    Checa se há próximo documento relevante na timeline e retorna (doc_encontrado, doc_link, doc_idx) se houver.
    Executa apenas uma vez por chamada.
    """
    doc_encontrado = None
    doc_link = None
    next_idx = doc_idx + 1
    if next_idx < len(itens):
        for idx, item in enumerate(itens[next_idx:], next_idx):
            try:
                link = item.find_element(By.CSS_SELECTOR, 'a.tl-documento:not([target="_blank"])')
                doc_text = link.text.lower()
                if not re.search(r'despacho|decisão|sentença|conclusão', doc_text):
                    continue
                mag_icons = item.find_elements(By.CSS_SELECTOR, 'div.tl-icon[aria-label*="Magistrado"]')
                mag_ok = any('otavio' in mag.get_attribute('aria-label').lower() or 'mariana' in mag.get_attribute('aria-label').lower() for mag in mag_icons)
                if mag_ok:
                    doc_encontrado = item
                    doc_link = link
                    doc_idx = idx
                    break
            except Exception:
                continue
    return doc_encontrado, doc_link, doc_idx

def fluxo_pz(driver):
    """
    Processa prazos detalhados em processos abertos.
    Usa extrair_documento para obter texto, analisa regras,
    cria GIGS parametrizadas, executa atos sequenciais e fecha aba.
    """
    acao_secundaria = None
    texto = None # Initialize texto as None    
    # 1. Seleciona documento relevante (decisão, despacho ou sentença)
    itens = driver.find_elements(By.CSS_SELECTOR, 'li.tl-item-container')
    doc_encontrado = None
    doc_link = None
    doc_idx = 0
    minuta_salva = False  # FLAG CORREÇÃO: evita repetir loop após salvar minuta
    
    while True:
        for idx, item in enumerate(itens[doc_idx:], doc_idx):
            try:
                link = item.find_element(By.CSS_SELECTOR, 'a.tl-documento:not([target="_blank"])')
                doc_text = link.text.lower()
                if not re.search(r'despacho|decisão|sentença|conclusão', doc_text):
                    continue
                mag_icons = item.find_elements(By.CSS_SELECTOR, 'div.tl-icon[aria-label*="Magistrado"]')
                mag_ok = any('otavio' in mag.get_attribute('aria-label').lower() or 'mariana' in mag.get_attribute('aria-label').lower() for mag in mag_icons)
                if mag_ok:
                    doc_encontrado = item
                    doc_link = link
                    doc_idx = idx
                    break
            except Exception:
                continue
        
        if not doc_encontrado or not doc_link:
            logger.error('[FLUXO_PZ] Nenhum documento relevante encontrado.')
            return

        doc_link.click()
        time.sleep(2) # Wait for panel/URL to load
        
        # 2. Extrair texto usando a função DIRETA de Fix.py (primeira opção)
        import datetime
        texto = None
        
        # Tentar primeiro com extrair_direto (nova função otimizada)
        try:
            logger.info('[FLUXO_PZ] Tentando extração DIRETA com extrair_direto...')
            resultado_direto = extrair_direto(driver, timeout=10, debug=False, formatar=False)
            
            if resultado_direto and resultado_direto.get('sucesso') and resultado_direto.get('conteudo_bruto'):
                texto = resultado_direto['conteudo_bruto'].lower()
                logger.info(f'[FLUXO_PZ] ✅ Extração DIRETA bem-sucedida via {resultado_direto.get("metodo", "método desconhecido")}')
            else:
                logger.warning('[FLUXO_PZ] extrair_direto não conseguiu extrair texto válido')
                
        except Exception as e_direto:
            logger.error(f'[FLUXO_PZ] Erro na extração DIRETA: {e_direto}')
        
        # Fallback: usar extrair_documento original se a extração direta falhou
        if not texto:
            logger.info('[FLUXO_PZ] Usando fallback: extrair_documento original...')
            texto_tuple = None
            try:
                texto_tuple = extrair_documento(driver, regras_analise=None, timeout=10, log=True)
                if texto_tuple and texto_tuple[0]:
                    texto = texto_tuple[0].lower()
                    logger.info('[FLUXO_PZ] ✅ Fallback extrair_documento funcionou')
                else:
                    logger.error('[FLUXO_PZ] extrair_documento retornou None ou texto vazio.')
            except Exception as e_extrair:
                logger.error(f'[FLUXO_PZ] Erro ao chamar/processar extrair_documento: {e_extrair}')
        
        if not texto:
            logger.error('[FLUXO_PZ] ❌ Não foi possível extrair o texto do documento com nenhum método.')
            return
        
        # Log do texto extraído (início apenas)
        log_texto = texto[:200] + '...' if len(texto) > 200 else texto
        print(f'[FLUXO_PZ] Texto extraído: {log_texto}')

        # 4. Define as regras com parâmetros e ações sequenciais
        def remover_acentos(txt):
            import unicodedata
            return ''.join(c for c in unicodedata.normalize('NFD', txt) if unicodedata.category(c) != 'Mn')

        def normalizar_texto(txt):
            return remover_acentos(txt.lower())

        texto_normalizado = normalizar_texto(texto)

        def gerar_regex_geral(termo):
            # Remove acentos e deixa minúsculo para o termo
            termo_norm = normalizar_texto(termo)
            # Divide termo em palavras
            palavras = termo_norm.split()
            # Monta regex permitindo pontuação, vírgula, etc. entre as palavras
            partes = [re.escape(p) for p in palavras]
            # Entre cada palavra, aceita qualquer quantidade de espaços, pontuação, vírgula, etc.
            regex = r''
            for i, parte in enumerate(partes):
                regex += parte
                if i < len(partes) - 1:
                    regex += r'[\s\.,;:!\-–—]*'
            # Permite o trecho em qualquer lugar do texto (texto antes/depois)
            return re.compile(rf"{regex}", re.IGNORECASE)

        regras = [
            # REGRA DE PRESCRIÇÃO - MÁXIMA PRIORIDADE
            ([gerar_regex_geral(k) for k in ['A pronúncia da']],
             None, None, prescreve),
            
            # REGRA DE BLOQUEIO - DEVE VIR ANTES PARA TER PRIORIDADE
            ([gerar_regex_geral(k) for k in ['sob pena de bloqueio']],
             'checar_cabecalho_impugnacoes', None, None),
            ([gerar_regex_geral(k) for k in [
                '05 dias para a apresentação',
                'suspensão da execução, com fluência',
                '05 dias para oferta',
                'concede-se 05 dias para oferta',
                'cinco dias para apresentação',
                'cinco dias para oferta',
                'cinco dias para apresentacao',
                'concedo cinco dias',
                'concedo o prazo de oito dias',
                'oito dias para apresentacao',
                'visibilidade aos advogados',
                'início da fluência',                
                'oito dias para apresentação',
                'oito dias para apresentacao',
                'Reitere-se a intimação para que o(a) reclamante apresente cálculos',
                'remessa ao sobrestamento, com fluência',
                'sob pena de sobrestamento e fluência do prazo prescricional',
            ]],
             'gigs', '1/Silas/Sob 24', ato_sobrestamento),
            ([gerar_regex_geral(k) for k in [
                'é revel, não',
                'concorda com homologação',
                'concorda com homologacao',
                'tomarem ciência dos esclarecimentos apresentados',
                'no prazo de oito dias, impugnar',                
                'concordância quanto à imediata homologação da conta',
                'conclusos para homologação de cálculos',
                'ciência do laudo técnico apresentado',
                'homologação imediata',
                'aceita a imediata homologação',
                'aceita a imediata homologacao',
                'informar se aceita a imediata homologação',
                'apresentar impugnação, querendo',
            ]],
             'gigs', '1/Silvia/Homologação', None),
            ([gerar_regex_geral('exequente, ora embargado')],
             'gigs', '1/fernanda/julgamento embargos', None),
            ([gerar_regex_geral(k) for k in ['hasta', 'saldo devedor']],
             'gigs', '1/SILAS/pec', None),
            ([gerar_regex_geral('Ante a notícia de descumprimento')],
             'checar_cabecalho', None, None),
            ([gerar_regex_geral(k) for k in ['impugnações apresentadas', 'impugnacoes apresentadas', 'homologo estes', 'fixando o crédito do autor em', 'referente ao principal', 'sob pena de sequestro', 'comprovar a quitação', 'comprovar o pagamento', 'a reclamada para pagamento da parcela pendente', 'intime-se a reclamada para pagamento das']],
             'checar_cabecalho_impugnacoes', None, None),          
            ([gerar_regex_geral(k) for k in ['arquivem-se os autos', ' remetam-se os autos ao aquivo', 'A pronúncia da prescrição intercorrente se trata', 'Se revê o novo sobrestamento', 'cumprido o acordo homologado', 'julgo extinta a presente execução, nos termos do art. 924']],
             'movimentar', mov_arquivar, None),
            ([gerar_regex_geral(k) for k in ['bloqueio realizado, ora convertido']], 'gigs', '1/SILAS/pec bloqueio', None),
            ([gerar_regex_geral(k) for k in ['sobre o preenchimento dos pressupostos legais para concessão do parcelamento']],
             'gigs', '1/Bruna/Liberação', None),
            ([gerar_regex_geral(k) for k in ['comprovar o recolhimento', 'comprovar os recolhimentos']],
             'gigs', '1/Silvia/Argos', ato_pesqliq_callback),
            ([gerar_regex_geral(k) for k in ['determinar cancelamento/baixa', 'deixo de receber o Agravo', 'quanto à petição', 'art. 112 do CPC', 'comunique-se por Edital', 'Aguarde-se o cumprimento do mandado expedido']],
             'checar_prox', None, None),
            ([gerar_regex_geral(k) for k in ['Defiro a penhora no rosto dos autos']],
             'gigs', '1/SILAS/sob6', ato_180),
            ([gerar_regex_geral(k) for k in ['RECLAMANTE para apresentar cálculos de liquidação']],
             None, None, ato_calc2),
            ([gerar_regex_geral('deverá realizar tentativas')],
             None, None, ato_prev),
            ([gerar_regex_geral('defiro a instauração')],
             'checar_anexos_instauracao', None, None),
            ([gerar_regex_geral(k) for k in ['tendo em vista que', 'pagamento da parcela pendente', 'sob pena de sequestro']],
             
             'checar_anexos_tendo_em_vista', None, None),
            ([gerar_regex_geral('não está amparada')],
             None, None, ato_meios),
        ]
        

# ...existing code...
        if 'bloqueio de valores realizado, ora' in texto or 'para os fins do art. 884' in texto:
            try:
                # 0. Extrair dados do processo
                from Fix import extrair_dados_processo
                dados_processo = extrair_dados_processo(driver)
                
                # Verificação simplificada de advogados
                parte_sem_advogado = False
                partes_passivas = []
                if dados_processo and 'partes' in dados_processo:
                    partes_data = dados_processo['partes']
                    if isinstance(partes_data, dict):
                        partes_passivas = partes_data.get('passivas', [])
                    elif isinstance(partes_data, list):
                        partes_passivas = partes_data
                    else:
                        partes_passivas = []
                    partes_sem_advogado = [p for p in partes_passivas if not p.get('representantes')]
                    parte_sem_advogado = len(partes_sem_advogado) > 0
                
                # NOVA LÓGICA: Verificar itens ACIMA do despacho
                itens_acima_despacho = itens[:doc_idx]  # Itens mais recentes que o despacho
                count_intimacoes = 0
                outros_itens = False
                
                for item in itens_acima_despacho:
                    texto_item = item.text.lower()
                    if 'intimação' in texto_item or 'intimacao' in texto_item:
                        count_intimacoes += 1
                    else:
                        outros_itens = True
                
                # a) Se há apenas uma intimação acima e nada mais
                if count_intimacoes == 1 and not outros_itens:
                    print('[FLUXO_PZ] Regra: Bloqueio realizado - Bruna/Liberação (apenas uma intimação acima)')
                    dias, responsavel, observacao = parse_gigs_param('1/Bruna/Liberação')
                    criar_gigs(driver, dias, responsavel, observacao)
                    minuta_salva = True
                    return
                # b) Se há mais itens, seguir checagem estabelecida
                else:
                    # Verificar item mais recente da timeline
                    primeiro_item = itens[0] if itens else None
                    
                    if primeiro_item:
                        primeiro_item_text = primeiro_item.text.lower()
                        
                        # Hipótese 1: GIGS Bruna - Liberação
                        if any(termo in primeiro_item_text for termo in ['edital', 'certidão de oficial de justiça']):
                            print('[FLUXO_PZ] Regra: Bloqueio realizado - Bruna/Liberação')
                            dias, responsavel, observacao = parse_gigs_param('1/Bruna/Liberação')
                            criar_gigs(driver, dias, responsavel, observacao)
                            minuta_salva = True
                        elif 'intimação' in primeiro_item_text or 'intimacao' in primeiro_item_text:
                            # Verificar se é intimação de correio via carta()
                            from carta import carta
                            carta_result = carta(driver, limite_intimacoes=4)
                            if carta_result:  # Se carta() encontrou intimação de correio
                                print('[FLUXO_PZ] Regra: Bloqueio realizado - Bruna/Liberação (correio)')
                                dias, responsavel, observacao = parse_gigs_param('1/Bruna/Liberação')
                                criar_gigs(driver, dias, responsavel, observacao)
                                minuta_salva = True
                            else:
                                # Verificar se há despacho anterior na timeline para condição "xs pec bloqueio"
                                despacho_encontrado = False
                                if len(itens) > 1:  # Verificar se há mais itens na timeline
                                    for i, item_timeline in enumerate(itens[1:], 1):  # Começar do segundo item
                                        item_text = item_timeline.text.lower()
                                        if 'despacho' in item_text:
                                            despacho_encontrado = True
                                            break
                                # Hipótese 2: parte sem advogado + despacho → GIGS "xs pec bloqueio"
                                if parte_sem_advogado and despacho_encontrado:
                                    print('[FLUXO_PZ] Regra: Bloqueio realizado - SILAS/pec bloqueio')
                                    dias, responsavel, observacao = parse_gigs_param('1/SILAS/pec bloqueio')
                                    criar_gigs(driver, dias, responsavel, observacao)
                                    minuta_salva = True
                                else:
                                    print('[FLUXO_PZ] Regra: Bloqueio realizado - Bruna/Liberação (padrão)')
                                    dias, responsavel, observacao = parse_gigs_param('1/Bruna/Liberação')
                                    criar_gigs(driver, dias, responsavel, observacao)
                                    minuta_salva = True
                        else:
                            # Hipótese 2: verificar despacho + parte sem advogado
                            if parte_sem_advogado and 'despacho' in primeiro_item_text:
                                print('[FLUXO_PZ] Regra: Bloqueio realizado - xs/pec bloqueio')
                                dias, responsavel, observacao = parse_gigs_param('1/xs/pec bloqueio')
                                criar_gigs(driver, dias, responsavel, observacao)
                                minuta_salva = True
                            else:
                                print('[FLUXO_PZ] Regra: Bloqueio realizado - Bruna/Liberação (caso padrão)')
                                dias, responsavel, observacao = parse_gigs_param('1/Bruna/Liberação')
                                criar_gigs(driver, dias, responsavel, observacao)
                                minuta_salva = True
                        
                        return
            except Exception as bloqueio_error:
                logger.error(f'[FLUXO_PZ] Erro na regra especial de bloqueio: {bloqueio_error}')
                if minuta_salva:
                    logger.info('[FLUXO_PZ] Minuta já salva. Não repetindo loop após erro.')
                    break
                raise
# ...existing code...
        # 5. VERIFICAÇÃO DE PREVALÊNCIA: prescreve tem prioridade absoluta
        regex_prescreve = gerar_regex_geral('A pronúncia da')
        if regex_prescreve.search(texto_normalizado):
            print('[FLUXO_PZ] ✅ PREVALÊNCIA: Prescrição detectada - executando com prioridade máxima')
            try:
                prescreve(driver)
                print('[FLUXO_PZ] ✅ Prescrição executada - ENCERRANDO fluxo (prevalência)')
                return  # SAIR imediatamente
            except Exception as prescreve_error:
                print(f'[FLUXO_PZ] ❌ Erro na execução de prescreve: {prescreve_error}')
                # Continua com regras normais se prescreve falhar
        
        # 6. Iterate through rules and keywords to find the first match
        acao_definida = None
        parametros_acao = None
        termo_encontrado = None
        acao_secundaria = None  # Reset before checking rules
        for keywords, tipo_acao, params, acao_sec in regras:
            for regex in keywords:
                match = regex.search(texto_normalizado)
                if match:
                    # Log da regra encontrada
                    print(f'[FLUXO_PZ] Regra aplicada: {tipo_acao} - {params if params else acao_sec.__name__ if acao_sec else "Nenhuma"}')
                    acao_definida = tipo_acao
                    parametros_acao = params
                    acao_secundaria = acao_sec
                    termo_encontrado = regex.pattern
                    # NOVA REGRA: se acao_definida == 'checar_prox', chamar checar_prox imediatamente
                    if acao_definida == 'checar_prox':
                        prox_doc_encontrado, prox_doc_link, prox_doc_idx = checar_prox(driver, itens, doc_idx, regras, texto_normalizado)
                        if prox_doc_encontrado and prox_doc_link:
                            print(f'[FLUXO_PZ] Regra de cancelamento/baixa: buscando próximo documento relevante')
                            doc_encontrado = prox_doc_encontrado
                            doc_link = prox_doc_link
                            doc_idx = prox_doc_idx
                            break
                    break
            if acao_definida:
                break        
        
        # 6. Perform action(s) based on the matched rule (or default)
        import datetime
        gigs_aplicado = False
        if acao_definida == 'gigs':
            # parametros_acao já está no formato 'dias/responsavel/observacao'
            try:
                dias, responsavel, observacao = parse_gigs_param(parametros_acao)
                criar_gigs(driver, dias, responsavel, observacao)
                gigs_aplicado = True
                minuta_salva = True  # FLAG: minuta foi salva
                print(f'[FLUXO_PZ] GIGS criado: {observacao}')
                if acao_secundaria:
                    print(f'[FLUXO_PZ] Executando ação secundária: {acao_secundaria.__name__}')
                    try:
                        acao_secundaria(driver)
                    except TypeError:
                        acao_secundaria(driver)
                    time.sleep(1)
            except Exception as gigs_error:
                logger.error(f'[FLUXO_PZ] Falha ao criar GIGS ou na ação secundária: {gigs_error}')
                if minuta_salva:
                    logger.info('[FLUXO_PZ] Minuta já salva. Não repetindo loop após erro.')
                    break
        elif acao_definida == 'movimentar':
             func_movimento = parametros_acao
             print(f'[FLUXO_PZ] Executando movimentação: {func_movimento.__name__}')
             try:
                 resultado_movimento = func_movimento(driver)
                 if resultado_movimento:
                     print(f'[FLUXO_PZ] Movimentação {func_movimento.__name__} executada com SUCESSO.')
                     minuta_salva = True  # FLAG: minuta foi salva
                 else:
                     logger.error(f'[FLUXO_PZ] Movimentação {func_movimento.__name__} FALHOU (retornou False).')
                     return  # Sai da função sem log de sucesso
                 time.sleep(1) # Pause after movement
             except Exception as mov_error:
                 logger.error(f'[FLUXO_PZ] Falha ao executar movimentação {func_movimento.__name__}: {mov_error}')
                 if minuta_salva:
                     logger.info('[FLUXO_PZ] Minuta já salva. Não repetindo loop após erro.')
                     break
                 return  # Sai da função sem log de sucesso
        elif acao_definida == 'checar_cabecalho':
            # Nova regra: verificar cor do cabeçalho para "Ante a notícia de descumprimento"
            try:
                cabecalho = driver.find_element(By.CSS_SELECTOR, 'mat-card.resumo-processo')
                cor_fundo = cabecalho.value_of_css_property('background-color')
                print(f'[FLUXO_PZ] Cor do cabeçalho detectada: {cor_fundo}')
                
                # Verifica se é cinza: rgb(144, 164, 174)
                if 'rgb(144, 164, 174)' in cor_fundo:
                    print('[FLUXO_PZ] Cabeçalho cinza detectado - executando pesquisas')
                    sucesso, sigilo_ativado = ato_pesquisas(driver)
                    if sucesso:
                        minuta_salva = True  # FLAG: minuta foi salva
                        # Aplicar visibilidade se necessário (após fechar minuta e voltar para detalhes)
                        if sigilo_ativado:
                            executar_visibilidade_sigilosos_se_necessario(driver, sigilo_ativado, debug=True)
                    else:
                        print('[FLUXO_PZ] ⚠️ Falha ao executar ato_pesquisas')
                else:
                    print('[FLUXO_PZ] Cabeçalho não é cinza - criando GIGS padrão')
                    dias, responsavel, observacao = parse_gigs_param('1/SILVIA/Argos')
                    criar_gigs(driver, dias, responsavel, observacao)
                    # Executar ato_pesqliq como ação secundária
                    sucesso, sigilo_ativado = ato_pesqliq(driver)
                    if sucesso:
                        minuta_salva = True  # FLAG: minuta foi salva
                        # Aplicar visibilidade se necessário (após fechar minuta e voltar para detalhes)
                        if sigilo_ativado:
                            executar_visibilidade_sigilosos_se_necessario(driver, sigilo_ativado, debug=True)
                    else:
                        print('[FLUXO_PZ] ⚠️ Falha ao executar ato_pesqliq')
                
                time.sleep(1)
            except Exception as cabecalho_error:
                logger.error(f'[FLUXO_PZ] Erro ao verificar cor do cabeçalho: {cabecalho_error}')
                if minuta_salva:
                    logger.info('[FLUXO_PZ] Minuta já salva. Não repetindo loop após erro.')
                    break
                # Fallback: criar GIGS padrão
                print('[FLUXO_PZ] Fallback - criando GIGS padrão')
                dias, responsavel, observacao = parse_gigs_param('1/SILVIA/Argos')
                criar_gigs(driver, dias, responsavel, observacao)
                minuta_salva = True  # FLAG: minuta foi salva
        elif acao_definida == 'checar_cabecalho_impugnacoes':
            # Nova regra: verificar cor do cabeçalho para "impugnações apresentadas"
            try:
                cabecalho = driver.find_element(By.CSS_SELECTOR, 'mat-card.resumo-processo')
                cor_fundo = cabecalho.value_of_css_property('background-color')
                print(f'[FLUXO_PZ] Cor do cabeçalho detectada para impugnações: {cor_fundo}')
                
                # Verifica se é cinza: rgb(144, 164, 174)
                if 'rgb(144, 164, 174)' in cor_fundo:
                    print('[FLUXO_PZ] Cabeçalho cinza detectado - executando criar_gigs + pesquisas')
                    
                    # 1. Criar gigs antes das pesquisas
                    print('[FLUXO_PZ] Etapa 1: Criando gigs (1/Silvia/Argos)')
                    criar_gigs(driver, "1", "Silvia", "Argos")
                    
                    # 2. Executar pesquisas
                    print('[FLUXO_PZ] Etapa 2: Executando pesquisas')
                    sucesso, sigilo_ativado = ato_pesquisas(driver)
                    if sucesso:
                        minuta_salva = True  # FLAG: minuta foi salva
                        # Aplicar visibilidade se necessário (após fechar minuta e voltar para detalhes)
                        if sigilo_ativado:
                            executar_visibilidade_sigilosos_se_necessario(driver, sigilo_ativado, debug=True)
                    else:
                        print('[FLUXO_PZ] ⚠️ Falha ao executar ato_pesquisas')
                else:
                    print('[FLUXO_PZ] Cabeçalho não é cinza - executando criar_gigs + mov_exec + pesquisas')
                    
                    # 1. Criar gigs antes de tudo
                    print('[FLUXO_PZ] Etapa 1: Criando gigs (1/Silvia/Argos)')
                    criar_gigs(driver, "1", "Silvia", "Argos")
                    
                    # 2. Executar movimento
                    print('[FLUXO_PZ] Etapa 2: Executando mov_exec')
                    mov_exec(driver)
                    
                    # 3. Fechar aba atual para voltar ao processo
                    print('[FLUXO_PZ] Etapa 3: Fechando aba atual para voltar ao processo')
                    try:
                        driver.close()  # Fecha aba atual
                        if len(driver.window_handles) > 0:
                            driver.switch_to.window(driver.window_handles[-1])  # Volta para última aba
                            print('[FLUXO_PZ] ✅ Voltou para aba do processo')
                        else:
                            print('[FLUXO_PZ] ⚠️ Nenhuma aba disponível após fechamento')
                    except Exception as close_error:
                        print(f'[FLUXO_PZ] ⚠️ Erro ao fechar aba: {close_error}')
                    
                    # 4. Executar pesquisas na aba do processo
                    print('[FLUXO_PZ] Etapa 4: Executando pesquisas')
                    sucesso, sigilo_ativado = ato_pesquisas(driver)
                    if sucesso:
                        minuta_salva = True  # FLAG: minuta foi salva
                        # Aplicar visibilidade se necessário (após fechar minuta e voltar para detalhes)
                        if sigilo_ativado:
                            executar_visibilidade_sigilosos_se_necessario(driver, sigilo_ativado, debug=True)
                    else:
                        print('[FLUXO_PZ] ⚠️ Falha ao executar ato_pesquisas')
                
                time.sleep(1)
            except Exception as cabecalho_error:
                logger.error(f'[FLUXO_PZ] Erro ao verificar cor do cabeçalho para impugnações: {cabecalho_error}')
                if minuta_salva:
                    logger.info('[FLUXO_PZ] Minuta já salva. Não repetindo loop após erro.')
                    break
                # Fallback: executar criar_gigs + mov_exec + pesquisas
                print('[FLUXO_PZ] Fallback - executando criar_gigs + mov_exec + pesquisas')
                
                # 1. Criar gigs antes de tudo
                print('[FLUXO_PZ] Fallback Etapa 1: Criando gigs (1/Silvia/Argos)')
                criar_gigs(driver, "1", "Silvia", "Argos")
                
                # 2. Executar movimento
                print('[FLUXO_PZ] Fallback Etapa 2: Executando mov_exec')
                mov_exec(driver)
                
                # 3. Fechar aba atual para voltar ao processo
                print('[FLUXO_PZ] Fallback Etapa 3: Fechando aba atual para voltar ao processo')
                try:
                    driver.close()  # Fecha aba atual
                    if len(driver.window_handles) > 0:
                        driver.switch_to.window(driver.window_handles[-1])  # Volta para última aba
                        print('[FLUXO_PZ] ✅ Voltou para aba do processo (fallback)')
                    else:
                        print('[FLUXO_PZ] ⚠️ Nenhuma aba disponível após fechamento (fallback)')
                except Exception as close_error:
                    print(f'[FLUXO_PZ] ⚠️ Erro ao fechar aba (fallback): {close_error}')
                
                # 4. Executar pesquisas na aba do processo
                print('[FLUXO_PZ] Fallback Etapa 4: Executando pesquisas')
                sucesso, sigilo_ativado = ato_pesquisas(driver)
                if sucesso:
                    minuta_salva = True  # FLAG: minuta foi salva
                    # Aplicar visibilidade se necessário (após fechar minuta e voltar para detalhes)
                    if sigilo_ativado:
                        executar_visibilidade_sigilosos_se_necessario(driver, sigilo_ativado, debug=True)
                else:
                    print('[FLUXO_PZ] ⚠️ Falha ao executar ato_pesquisas (fallback)')
        
        # Se não há ação primária mas existe ação secundária, trate a secundária como primária
        if acao_definida is None and acao_secundaria:
            print(f'[FLUXO_PZ] Executando ação: {acao_secundaria.__name__}')
            try:
                acao_secundaria(driver)
                minuta_salva = True  # FLAG: minuta foi salva
                
                # NOVA LÓGICA: se acao_secundaria for prescreve, PARAR EXECUÇÃO (predominância)
                if acao_secundaria.__name__ == 'prescreve':
                    print('[FLUXO_PZ] ✅ Prescrição executada - PARANDO execução (predominância)')
                    return  # SAIR da função imediatamente
                
                time.sleep(1)
            except Exception as sec_error:
                logger.error(f'[FLUXO_PZ] Falha ao executar ação {acao_secundaria.__name__}: {sec_error}')
                if minuta_salva:
                    logger.info('[FLUXO_PZ] Minuta já salva. Não repetindo loop após erro.')
                    break
        
        # NOVA LÓGICA: buscar o próximo documento relevante APENAS se a ação primária for 'checar_prox'
        if acao_definida == 'checar_prox':
            prox_doc_encontrado, prox_doc_link, prox_doc_idx = checar_prox(driver, itens, doc_idx, regras, texto_normalizado)
            if prox_doc_encontrado and prox_doc_link:
                print(f'[FLUXO_PZ] Trecho localizado. Buscando próximo documento relevante')
                doc_encontrado = prox_doc_encontrado
                doc_link = prox_doc_link
                doc_idx = prox_doc_idx
                continue  # repete o while para o próximo documento
                
        # NOVA LÓGICA: se prescreve foi executado, PARAR tudo (predominância total)
        if acao_secundaria and acao_secundaria.__name__ == 'prescreve':
            print('[FLUXO_PZ] ✅ Prescrição executada - ENCERRANDO fluxo (predominância total)')
            break  # sair do while True
            
        break  # se não encontrou ou acabou a timeline, encerra
    # Fim do while True    
    
    # Fechar a aba após o processamento do fluxo_pz (sem usar try/finally)
    all_windows = driver.window_handles
    main_window = all_windows[0]
    current_window = driver.current_window_handle

    if current_window != main_window and len(all_windows) > 1:
        driver.close()
        # Troca para uma aba válida após fechar
        try:
            if main_window in driver.window_handles:
                driver.switch_to.window(main_window)
            elif driver.window_handles:
                driver.switch_to.window(driver.window_handles[0])
            else:
                print("[LIMPEZA][ERRO] Nenhuma aba restante para alternar.")
        except Exception as e:
            print(f"[LIMPEZA][ERRO] Falha ao alternar para aba válida após fechar: {e}")
        # Testa se a aba está realmente acessível
        from selenium.common.exceptions import NoSuchWindowException
        try:
            _ = driver.current_url
        except NoSuchWindowException:
            print("[LIMPEZA][ERRO] Tentou acessar uma aba já fechada.")
    
    print('[FLUXO_PZ] Processo concluído, retornando à lista')

def fluxo_prazo(driver):
    """
    Executa o fluxo de prazo: Itera processos, chama fluxo_pz para cada um.
    Otimizado para verificar progresso na lista antes de abrir processos.
    """
    from Fix import indexar_processos # Import da função de indexação

    print('[FLUXO_PRAZO] Iniciando processamento da lista de processos')
    
    # Carrega o progresso uma vez
    progresso = carregar_progresso_p2b()
    
    # Indexa todos os processos da lista primeiro
    try:
        processos = indexar_processos(driver)
        if not processos:
            print('[FLUXO_PRAZO][ALERTA] Nenhum processo encontrado na lista')
            return
        print(f'[FLUXO_PRAZO] {len(processos)} processos encontrados na lista')
    except Exception as e:
        print(f'[FLUXO_PRAZO][ERRO] Falha ao indexar processos: {e}')
        return
    
    # Filtra processos já executados ANTES de abrir qualquer um
    processos_para_executar = []
    processos_pulados = 0
    
    for proc_id, linha in processos:
        if proc_id == '[sem número]':
            processos_para_executar.append((proc_id, linha))
            continue
            
        # Usa o número formatado diretamente para comparação (sem conversão)
        if processo_ja_executado_p2b(proc_id, progresso):
            print(f"[PROGRESSO_P2B] Processo {proc_id} já foi executado, pulando...")
            processos_pulados += 1
        else:
            processos_para_executar.append((proc_id, linha))
            print(f"[PROGRESSO_P2B] Processo {proc_id} será processado")
    
    print(f'[FLUXO_PRAZO] {processos_pulados} processos pulados (já executados)')
    print(f'[FLUXO_PRAZO] {len(processos_para_executar)} processos serão processados')
    
    if not processos_para_executar:
        print('[FLUXO_PRAZO] Todos os processos já foram executados!')
        return

    # Processa apenas os processos filtrados usando uma abordagem customizada
    def processar_lista_filtrada():
        """Processa apenas os processos que não foram executados ainda"""
        aba_lista_original = driver.current_window_handle
        processos_processados = 0
        processos_com_erro = 0
        
        for idx, (proc_id, linha) in enumerate(processos_para_executar):
            print(f'[PROCESSAR] Iniciando processo {idx+1}/{len(processos_para_executar)}: {proc_id}', flush=True)
            
            try:
                # Tenta usar a linha existente primeiro
                linha_atual = linha
                
                # Se a linha ficou stale, reindexar
                try:
                    linha_atual.is_displayed()
                except:
                    from Fix import reindexar_linha
                    linha_atual = reindexar_linha(driver, proc_id)
                    if not linha_atual:
                        print(f'[PROCESSAR][ERRO] Não foi possível reindexar linha para {proc_id}')
                        processos_com_erro += 1
                        continue
                
                # Abre detalhes do processo
                from Fix import abrir_detalhes_processo
                if not abrir_detalhes_processo(driver, linha_atual):
                    print(f'[PROCESSAR][ERRO] Botão de detalhes não encontrado para {proc_id}')
                    processos_com_erro += 1
                    continue
                
                # Aguarda nova aba carregar
                time.sleep(2)
                from Fix import trocar_para_nova_aba
                nova_aba = trocar_para_nova_aba(driver, aba_lista_original)
                if not nova_aba:
                    print(f'[PROCESSAR][ERRO] Nova aba não carregou para {proc_id}')
                    processos_com_erro += 1
                    continue
                
                print(f'[PROCESSAR] Nova aba carregada: {driver.title[:50]}... | URL: {driver.current_url[:50]}...')
                
                # Executa callback com o número do processo conhecido
                try:
                    def callback_com_numero(driver_proc):
                        """Callback que conhece o número do processo"""
                        try:
                            print(f"[PROGRESSO_P2B] Processando: {proc_id}")
                            
                            fluxo_pz(driver_proc) # Call the main function for the process tab
                            
                            # Marca processo como executado usando o número da lista
                            if proc_id != '[sem número]':
                                progresso_atual = carregar_progresso_p2b()
                                marcar_processo_executado_p2b(proc_id, progresso_atual)
                                print(f"[PROGRESSO_P2B] Processo {proc_id} concluído com sucesso")
                            else:
                                print("[PROGRESSO_P2B] Processo sem número identificado foi executado")
                                
                        except Exception as callback_error:
                            logger.error(f'[FLUXO_PRAZO] ERRO no fluxo_pz: {callback_error}')
                            # Mesmo com erro, marca como executado para evitar loop infinito
                            if proc_id != '[sem número]':
                                progresso_atual = carregar_progresso_p2b()
                                marcar_processo_executado_p2b(proc_id, progresso_atual)
                                print(f"[PROGRESSO_P2B] Processo {proc_id} marcado como executado (com erro)")
                            raise
                    
                    callback_com_numero(driver)
                    processos_processados += 1
                    print(f'[PROCESSAR] Callback executado com sucesso para {proc_id}')
                except Exception as e:
                    print(f'[PROCESSAR][ERRO] Callback falhou para {proc_id}: {e}')
                    processos_com_erro += 1
                
                # Volta para aba da lista
                try:
                    if aba_lista_original in driver.window_handles:
                        driver.switch_to.window(aba_lista_original)
                        # Fecha outras abas
                        for handle in driver.window_handles:
                            if handle != aba_lista_original:
                                try:
                                    driver.switch_to.window(handle)
                                    driver.close()
                                except:
                                    pass
                        driver.switch_to.window(aba_lista_original)
                    else:
                        print(f'[PROCESSAR][ERRO] Aba da lista não está mais disponível')
                except Exception as e:
                    print(f'[PROCESSAR][ERRO] Falha ao voltar para lista: {e}')
                
            except Exception as e:
                print(f'[PROCESSAR][ERRO] Falha geral no processo {proc_id}: {e}')
                processos_com_erro += 1
                continue
        
        print(f'[FLUXO_PRAZO] Processamento concluído: {processos_processados} sucesso, {processos_com_erro} erros')
    
    # Executa o processamento customizado
    processar_lista_filtrada()

    print('[FLUXO_PRAZO] Processamento da lista concluído')

def navegar_para_atividades(driver):
    """
    Navega para a tela de atividades do GIGS clicando no ícone .fa-tags.
    """
    try:
        # Navegação por clique no ícone .fa-tags
        print("[NAVEGAR] Procurando ícone .fa-tags...")
        tag_icon = esperar_elemento(driver, ".fa-tags", timeout=20)
        if not tag_icon:
            print("[ERRO] Ícone .fa-tags não encontrado!")
            return
        safe_click(driver, tag_icon)
        print("[NAVEGAR] Ícone .fa-tags clicado.")

        # Aguarda o carregamento da tela de atividades
        esperar_elemento(driver, ".classe-unica-da-tela-atividades", timeout=20)
        print("[OK] Na tela de atividades do GIGS. Continue o fluxo normalmente...")
    except Exception as e:
        print(f"[ERRO] Falha ao navegar para a tela de atividades: {e}")

# Updated to use driver_notebook and login_notebook from Fix.py.
from Fix import login_notebook, driver_notebook

def esperar_url(driver, url_esperada, timeout=30):
    """
    Espera até a URL do driver ser igual à url_esperada ou até o timeout.
    Retorna True se a URL for atingida, False caso contrário.
    """
    import time
    start = time.time()
    while time.time() - start < timeout:
        if driver.current_url == url_esperada:
            return True
        time.sleep(0.5)
    return False

def esperar_url_conter(driver, trecho_url, timeout=60):
    import time
    start = time.time()
    while time.time() - start < timeout:
        if trecho_url in driver.current_url:
            return True
        time.sleep(0.5)
    return False

# Updated the executar_fluxo function to use the new driver and login function.
def executar_fluxo(driver):
    """
    Executa o fluxo completo de navegação, filtro e processamento, usando o driver já autenticado.
    """
    try:
        # Maximizar a janela do navegador
        driver.maximize_window()
        driver.execute_script("document.body.style.zoom='70%'")
        url_atividades = 'https://pje.trt2.jus.br/pjekz/gigs/relatorios/atividades'
        driver.get(url_atividades)
        if not esperar_url(driver, url_atividades, timeout=30):
            logger.error(f'[NAVEGAR] Timeout aguardando URL {url_atividades}. URL atual: {driver.current_url}')
            raise Exception(f'Timeout aguardando URL {url_atividades}')
        from Fix import aplicar_filtro_100
        try:
            # 3. Aplicar filtro de 100 itens por página
            if not aplicar_filtro_100(driver):
                raise Exception('Falha ao aplicar filtro de 100 itens por página')
            time.sleep(2)
            # Passo 1: Remover chip "Vencidas"
            chip_removal_success = False
            for tentativa in range(3):
                try:
                    time.sleep(0.5)
                    chip_remove_button = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[ngclass="chips-icone-fechar"][mattooltip="Remover filtro"]'))
                    )
                    try:
                        chip_remove_button.is_displayed()
                    except StaleElementReferenceException:
                        continue
                    safe_click(driver, chip_remove_button)
                    chip_removal_success = True
                    break
                except StaleElementReferenceException as e:
                    time.sleep(1)
                except Exception as e:
                    if tentativa < 2:
                        time.sleep(1)
                    else:
                        logger.error('[FILTRO] Falha ao remover chip após 3 tentativas.')
                        raise
            if not chip_removal_success:
                raise Exception("Falha na remoção do chip 'Vencidas'")
            # Passo 2: Clicar no ícone fa-pen
            btn_fa_pen = esperar_elemento(driver, 'i.fa-pen', timeout=15)
            safe_click(driver, btn_fa_pen)
            # Passo 3: Aplicar filtro "xs"
            campo_descricao = esperar_elemento(driver, 'input[aria-label*="Descrição"]', timeout=15)
            campo_descricao.clear()
            campo_descricao.send_keys('xs')
            campo_descricao.send_keys(Keys.ENTER)
            logger.info('[FILTRO] Filtro xs aplicado com sucesso.')
            time.sleep(3)
        except Exception as e:
            logger.error(f'[FILTRO] Erro na sequência de filtros: {e}')
            # Não raise aqui: tentaremos processar a lista mesmo assim
            
        # 5. Executar fluxo de prazo
        logger.info('[FLUXO_PRAZO] Iniciando processamento da lista de processos')
        try:
            fluxo_prazo(driver)
            logger.info('[FLUXO_PRAZO] Processamento da lista concluído')
        except Exception as e:
            logger.error(f'[FLUXO_PRAZO] Erro ao processar lista: {e}')
    except Exception as e:
        logger.error(f'[EXECUCAO] {e}')
        raise  # Re-raise para que a função chamadora possa lidar com o erro

def main():
    driver = criar_driver(headless=False)
    if not driver:
        print('[ERRO] Falha ao iniciar o driver.')
        return
    # Tenta login automático e em caso de falha tenta login manual antes de encerrar
    if not login_func(driver):
        print('[P2B] Falha no login automático. Tentando fallback para login manual...')
        try:
            from driver_config import login_manual
            if login_manual(driver):
                print('[P2B] ✅ Login manual realizado com sucesso. Continuando execução.')
            else:
                print('[P2B] ❌ Login manual não realizado. Mantendo driver aberto para inspeção.')
                return
        except Exception as e:
            print(f"[P2B][ERRO] Falha ao tentar login manual: {e}")
            print('[P2B] Mantendo driver aberto para inspeção.')
            return
    print('[P2] Login realizado com sucesso.')
    executar_fluxo(driver)

def processar_p2(driver_existente=None):
    """
    Função principal que executa o fluxo do p2.py.
    Aceita um driver existente ou cria um novo se nenhum for fornecido.
    
    Args:
        driver_existente: Driver do Selenium já configurado e logado (opcional)
    """
    driver = driver_existente
    should_quit = False
    
    try:
        if not driver:
            driver = criar_driver()
            login_func(driver)
            should_quit = True  # Só fecha o driver se foi criado aqui
        executar_fluxo(driver)
        return True
    except Exception as e:
        logger.error(f'[PROCESSAR_P2] Erro: {e}')
        return False
    finally:
        if should_quit and driver:
            finalizar_driver(driver)

if __name__ == "__main__":
    processar_p2()  # Quando executado diretamente, cria seu próprio driver

class AutomacaoP2:
    def __init__(self):
        self.driver = None
        self.etapa_atual = None

    def iniciar(self):
        try:
            from Fix import driver_pc
            self.driver = driver_pc(headless=False)
            if not self.driver:
                logging.error('[AutomacaoP2] Falha ao iniciar o driver.')
                return False
            return True
        except Exception as e:
            logging.error(f'[AutomacaoP2] Erro ao iniciar driver: {e}')
            return False

    def login(self):
        self.etapa_atual = 'login'
        try:
            from Fix import login_pc
            if not login_pc(self.driver):
                logging.error('[AutomacaoP2] Falha no login.')
                return False
            logging.info('[AutomacaoP2] Login realizado com sucesso.')
            return True
        except Exception as e:
            logging.error(f'[AutomacaoP2] Erro no login: {e}')
            return False

    def executar_fluxo(self):
        self.etapa_atual = 'fluxo_principal'
        try:
            if not self.driver:
                if not self.iniciar():
                    return False
            if not self.login():
                return False
            executar_fluxo(self.driver)
            return True
        except Exception as e:
            logging.error(f'[AutomacaoP2] Erro ao executar fluxo: {e}')
            return False

    def reiniciar_etapa(self):
        logging.info(f'[AutomacaoP2] Reiniciando etapa: {self.etapa_atual}')
        # Implementar lógica de reinício se necessário

    def finalizar(self):
        if self.driver:
            try:
                finalizar_driver(self.driver)
                logging.info('[AutomacaoP2] Driver finalizado.')
            except Exception as e:
                logging.error(f'[AutomacaoP2] Erro ao finalizar driver: {e}')
