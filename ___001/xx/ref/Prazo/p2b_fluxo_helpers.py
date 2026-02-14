"""
P2B Fluxo PZ Helpers - Funções auxiliares do fluxo_pz
Refatoração seguindo abordagem ORIGINAL do p2b.py: lista sequencial de regras
Mantém termos exatos e ordem de precedência do código que FUNCIONA
"""

# ===== CONFIGURAÇÕES DE PERFORMANCE =====
# Número de threads paralelas para verificar processos contra API GIGS
# Valores recomendados:
#   - 5-10: Conexão estável, evita sobrecarga
#   - 15-20: Conexão rápida, processa mais rápido
#   - 3-5: Conexão lenta ou instável
GIGS_API_MAX_WORKERS = 20

import logging
import re
import time
from typing import Optional, Tuple, List, Any
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By

from .p2b_core import (
    normalizar_texto, gerar_regex_geral, parse_gigs_param,
    carregar_progresso_p2b, salvar_progresso_p2b, marcar_processo_executado_p2b,
    processo_ja_executado_p2b, RegraProcessamento, REGEX_PATTERNS, ato_pesqliq_callback
)

# Logger local para evitar conflitos
logger = logging.getLogger(__name__)

# ===== IMPORTS PESADOS REMOVIDOS DO TOPO =====
# Movidos para lazy loading (imports dentro das funções)
# Motivo: Carregamento inicial 5-8x mais rápido
#
# Anteriormente carregados aqui:
# - Fix.core, Fix.extracao
# - atos.judicial, atos.movimentos, atos.wrappers_*
# - pec_excluiargos
#
# Agora cada função importa apenas o que precisa, quando precisa

# Cache de módulos carregados para evitar reimportações
_modules_cache = {}

def _lazy_import():
    """Carrega módulos pesados sob demanda (lazy loading).
    
    Esta função é chamada pelas funções que precisam dos módulos,
    garantindo que só sejam carregados quando realmente necessários.
    """
    global _modules_cache
    
    if not _modules_cache:
        from Fix.core import aguardar_e_clicar
        from Fix.extracao import criar_gigs, extrair_direto, extrair_documento, criar_lembrete_posit
        from atos.judicial import ato_pesquisas, idpj
        from atos.movimentos import mov
        from atos.wrappers_mov import mov_arquivar
        from atos.wrappers_ato import ato_sobrestamento, ato_pesqliq, ato_180, ato_calc2, ato_prev, ato_meios, ato_idpj
        from atos import pec_excluiargos
        
        _modules_cache.update({
            'aguardar_e_clicar': aguardar_e_clicar,
            'criar_gigs': criar_gigs,
            'extrair_direto': extrair_direto,
            'extrair_documento': extrair_documento,
            'criar_lembrete_posit': criar_lembrete_posit,
            'ato_pesquisas': ato_pesquisas,
            'idpj': idpj,
            'mov': mov,
            'mov_arquivar': mov_arquivar,
            'ato_sobrestamento': ato_sobrestamento,
            'ato_pesqliq': ato_pesqliq,
            'ato_180': ato_180,
            'ato_calc2': ato_calc2,
            'ato_prev': ato_prev,
            'ato_meios': ato_meios,
            'ato_idpj': ato_idpj,
            'pec_excluiargos': pec_excluiargos,
        })
    
    return _modules_cache


# ===== FUNÇÃO PRESCREVE =====
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
    # Lazy load modules
    m = _lazy_import()
    criar_gigs = m['criar_gigs']
    pec_excluiargos = m['pec_excluiargos']
    
    try:
        print('[PRESCREVE] 🚨 PRESCRIÇÃO DETECTADA - Iniciando fluxo')
        
        # 0. Executa BNDT (exclusão via Fix.bndt)
        print('[PRESCREVE] 0. Executando BNDT (Exclusão)...')
        try:
            from Fix import bndt
            bndt_resultado = bndt(driver, inclusao=False)
        except Exception as e:
            print(f'[PRESCREVE] ⚠️ Falha no BNDT: {e} - continuando fluxo')
            bndt_resultado = False
        
        # 1. Checagem de timeline
        print('[PRESCREVE] 1. Analisando timeline...')
        documentos = analisar_timeline_prescreve_js_puro(driver)
        
        if not documentos:
            print('[PRESCREVE] ❌ Nenhum documento relevante encontrado na timeline')
            return False
        
        # 2. Executar ações em ORDEM SEQUENCIAL
        print('[PRESCREVE] 2. Executando ações sequenciais...')
        
        # Ação 1: Localizar Serasa/CNIB em anexos e chamar pec_excluiargos (UMA VEZ)
        anexos_serasa_cnib = [d for d in documentos if d.get('isAnexo', False) and d.get('tipo', '').lower() in ['serasa', 'cnib']]
        if anexos_serasa_cnib:
            print(f'[PRESCREVE] 📋 {len(anexos_serasa_cnib)} anexo(s) Serasa/CNIB encontrado(s) - executando pec_excluiargos (UMA VEZ)')
            try:
                resultado = pec_excluiargos(driver)
                if resultado:
                    print(f'[PRESCREVE] ✅ pec_excluiargos executado com sucesso')
                else:
                    print(f'[PRESCREVE] ⚠️ Falha no pec_excluiargos')
            except Exception as e:
                print(f'[PRESCREVE] ❌ Erro ao executar pec_excluiargos: {e}')
        
        # Ação 2: Serasa fora de anexos + nenhum Serasa em anexos = criar_gigs Bianca
        serasa_timeline = [d for d in documentos if not d.get('isAnexo', False) and 'serasa' in d.get('tipo', '').lower()]
        tem_serasa_anexo = any(d.get('isAnexo', False) and 'serasa' in d.get('tipo', '').lower() for d in documentos)

        if serasa_timeline and not tem_serasa_anexo:
            print(f'[PRESCREVE] 📋 {len(serasa_timeline)} Serasa fora de anexos - criando GIGS Bianca')
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
            
            # Log simplificado conforme solicitado
            cnib_serasa_anexos = sum(1 for d in documentos if d.get('isAnexo', False) and d.get('tipo', '').lower() in ['cnib', 'serasa'])
            alvaras = sum(1 for d in documentos if d.get('tipo', '').lower() == 'alvará')
            serasa_nao_anexo = sum(1 for d in documentos if not d.get('isAnexo', False) and d.get('tipo', '').lower() == 'serasa')
            
            print(f'1- CNIB/SERASA (como anexos) - {cnib_serasa_anexos}; Alvaras - {alvaras}; Serasa sem ser anexo - {serasa_nao_anexo}')
            
            return documentos
            
        except json.JSONDecodeError as e:
            print(f'[PRESCREVE][TIMELINE] ❌ Erro ao decodificar JSON: {e}')
            print(f'[PRESCREVE][TIMELINE] Resultado recebido: {resultado_json[:200]}...')
            return []
        
    except Exception as e:
        print(f'[PRESCREVE][TIMELINE] ❌ Erro na análise JavaScript: {e}')
        return []


# ===== HELPERS PRIVADOS: FLUXO_PZ =====

def _encontrar_documento_relevante(driver: WebDriver) -> Tuple[Optional[Any], Optional[Any], int]:
    """
    Helper: Encontra documento relevante (decisão/despacho/sentença) na timeline.
    
    ⚠️ CORRIGIDO: Busca APENAS no tipo real do documento (primeiro <span> dentro do link),
    não na descrição completa que pode conter termos enganosos.
    
    Exemplo correto: <span>Sentença</span><span>(Prescrição...)</span>
    Exemplo incorreto: <span>Edital</span><span>(Decisão/Sentença)</span> <- o tipo é EDITAL, não Decisão

    Returns:
        Tupla (doc_encontrado, doc_link, doc_idx)
    """
    itens = driver.find_elements(By.CSS_SELECTOR, 'li.tl-item-container')
    print(f'[FLUXO_PZ][OTIMIZAÇÃO] Timeline tem {len(itens)} documentos. Iniciando busca do mais antigo para o mais recente.')

    # Busca do mais antigo para o mais recente
    for idx, item in enumerate(itens):
        try:
            link = item.find_element(By.CSS_SELECTOR, 'a.tl-documento:not([target="_blank"])')
            
            # ✅ CORRIGIDO: Extrair apenas o primeiro <span> (tipo real do documento)
            # Não o texto completo que pode incluir descrição enganosa
            primeiro_span = link.find_element(By.CSS_SELECTOR, 'span:not(.sr-only)')
            tipo_real = primeiro_span.text.lower().strip() if primeiro_span else ''
            
            # Verificar se o tipo REAL é um dos procurados
            if tipo_real and re.search(r'^(despacho|decisão|sentença|conclusão)', tipo_real):
                real_idx = idx
                # Mostrar o tipo real encontrado (sem incluir a descrição enganosa)
                print(f'[FLUXO_PZ] ✅ Primeiro documento relevante encontrado na posição {real_idx}: {tipo_real}')
                return item, link, real_idx

        except Exception:
            continue

    return None, None, 0


def _extrair_texto_documento(driver: WebDriver, doc_link: Any) -> Optional[str]:
    """
    Helper: Extrai texto do documento usando múltiplas estratégias.

    Args:
        driver: WebDriver instance
        doc_link: Link do documento

    Returns:
        Texto extraído ou None se falhar
    """
    doc_link.click()
    time.sleep(2)

    # Estratégia 1: extrair_direto (otimizada)
    texto = _extrair_com_extrair_direto(driver)
    if texto:
        return texto

    # Estratégia 2: extrair_documento (fallback)
    texto = _extrair_com_extrair_documento(driver)
    return texto


def _extrair_com_extrair_direto(driver: WebDriver) -> Optional[str]:
    """Helper: Extrai texto usando extrair_direto."""
    m = _lazy_import()
    extrair_direto = m['extrair_direto']
    
    try:
        logger.info('[FLUXO_PZ] Tentando extração DIRETA com extrair_direto...')
        resultado_direto = extrair_direto(driver, timeout=10, debug=True, formatar=True)

        if resultado_direto and resultado_direto.get('sucesso'):
            if resultado_direto.get('conteudo'):
                texto = resultado_direto['conteudo'].lower()
                logger.info('[FLUXO_PZ] ✅ Extração DIRETA bem-sucedida')
                return texto
            elif resultado_direto.get('conteudo_bruto'):
                texto = resultado_direto['conteudo_bruto'].lower()
                logger.info('[FLUXO_PZ] ✅ Extração DIRETA bem-sucedida (bruto)')
                return texto

    except Exception as e_direto:
        logger.error(f'[FLUXO_PZ] Erro na extração DIRETA: {e_direto}')

    return None


def _extrair_com_extrair_documento(driver: WebDriver) -> Optional[str]:
    """Helper: Extrai texto usando extrair_documento (fallback)."""
    m = _lazy_import()
    extrair_documento = m['extrair_documento']
    
    try:
        logger.info('[FLUXO_PZ] Usando fallback: extrair_documento original...')
        texto_tuple = extrair_documento(driver, regras_analise=None, timeout=10, log=True)

        if texto_tuple and texto_tuple[0]:
            texto = texto_tuple[0].lower()
            logger.info('[FLUXO_PZ] ✅ Fallback extrair_documento funcionou')
            return texto

    except Exception as e_extrair:
        logger.error(f'[FLUXO_PZ] Erro ao chamar/processar extrair_documento: {e_extrair}')

    return None


def _definir_regras_processamento() -> List[Tuple]:
    """
    Helper: Define lista de regras SEQUENCIAIS baseada no p2b.py ORIGINAL.
    Mantém EXATAMENTE os mesmos termos e ordem de precedência.

    Returns:
        Lista de tuplas (keywords, tipo_acao, params, acao_secundaria)
    """
    # Lazy load modules necessários para as regras
    m = _lazy_import()
    mov_arquivar = m['mov_arquivar']
    ato_180 = m['ato_180']
    ato_calc2 = m['ato_calc2']
    ato_prev = m['ato_prev']
    ato_meios = m['ato_meios']
    ato_sobrestamento = m['ato_sobrestamento']
    
    return [
        # REGRA DE PRESCRIÇÃO - MÁXIMA PRIORIDADE
        ([re.compile(r'A pronúncia da', re.IGNORECASE)],
         None, None, None),  # prescreve será chamado separadamente

        # REGRA DE BLOQUEIO - DEVE VIR ANTES PARA TER PRIORIDADE
        ([gerar_regex_geral(k) for k in ['sob pena de bloqueio']],
         'checar_cabecalho_impugnacoes', None, None),

        # REGRAS DE SOBRESTAMENTO
        ([gerar_regex_geral(k) for k in [
            '05 dias para a apresentação',
            'suspensão da execução, com fluência',
            '05 dias para oferta',
            'concede-se 05 dias para oferta',
            'cinco dias para apresentação',
            'cinco dias para oferta',
            'cinco dias para apresentacao',
            'concedo o prazo de oito dias',
            'meios  efetivos  para  o prosseguimento da execução',
            'visibilidade aos advogados',
            'início da fluência',
            'oito dias para apresentação',
            'oito dias para apresentacao',
            'Reitere-se a intimação para que o(a) reclamante apresente cálculos',
            'remessa ao sobrestamento, com fluência',
            'sob pena de sobrestamento e fluência do prazo prescricional',
        ]],
         'gigs', '1//xs sob 24', ato_sobrestamento),

        # REGRAS DE HOMOLOGAÇÃO
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
         'gigs', '-1//SILVIA - Homologação', None),

        # REGRA DE EMBARGOS
        ([gerar_regex_geral('exequente, ora embargado')],
         'gigs', '1/fernanda/julgamento embargos', None),

        # REGRA DE PEC
        ([gerar_regex_geral(k) for k in ['hasta', 'saldo devedor']],
         'gigs', '1//xs saldo', None),

        # REGRA DE DESCUMPRIMENTO
        ([gerar_regex_geral('Ante a notícia de descumprimento')],
         'checar_cabecalho', None, None),

        # REGRA DE IMPUGNAÇÕES
        ([gerar_regex_geral(k) for k in ['impugnações apresentadas', 'impugnacoes apresentadas', 'homologo estes', 'fixando o crédito do autor em', 'referente ao principal', 'sob pena de sequestro', 'comprovar a quitação', 'comprovar o pagamento', 'a reclamada para pagamento da parcela pendente', 'intime-se a reclamada para pagamento das', 'homologo os calculos', 'sob pena de execução']],
         'checar_cabecalho_impugnacoes', None, None),

        # REGRA DE ARQUIVAMENTO
        ([gerar_regex_geral(k) for k in ['arquivem-se os autos', 'remetam-se os autos ao aquivo', 'A pronúncia da prescrição intercorrente se trata', 'Se revê o novo sobrestamento', 'cumprido o acordo homologado', 'julgo extinta a presente execução, nos termos do art. 924']],
         'movimentar', mov_arquivar, None),

        # REGRA DE CONCLUSOS PARA LIBERAÇÃO
        ([gerar_regex_geral('conclusos para liberação')],
         'gigs', 'B-1//Bruna Liberação', None),

        # REGRA DE PARCELAMENTO
        ([gerar_regex_geral('sobre o preenchimento dos pressupostos legais para concessão do parcelamento')],
         'gigs', '1/Bruna/Liberação', None),

        # REGRA DE RECOLHIMENTO
        ([gerar_regex_geral(k) for k in ['comprovar recolhimento', 'comprovar recolhimentos']],
         'gigs', '1/Silvia/Argos', ato_pesqliq_callback),

        # REGRA DE BAIXA/AGUARDE-SE (Conjunto específico que chama checar_prox)
        ([gerar_regex_geral(k) for k in ['determinar cancelamento/baixa', 'deixo de receber o Agravo', 'quanto à petição', 'art. 112 do CPC', 'comunique-se por Edital', 'Aguarde-se', 'mantenho o despacho', 'mantenho a decisão', 'edital de intimação de decisão', 'sob pena de preclusão']],
         'checar_prox', None, None),

        # REGRA DE PENHORA
        ([gerar_regex_geral('Defiro a penhora no rosto dos autos')],
         'gigs', '1//xs sob 6', ato_180),

        # REGRA DE CÁLCULOS
        ([gerar_regex_geral('RECLAMANTE para apresentar cálculos de liquidação')],
         None, None, ato_calc2),

        # REGRA DE TENTATIVAS
        ([gerar_regex_geral('deverá realizar tentativas')],
         None, None, ato_prev),

        # REGRA DE INSTAURAÇÃO
        ([gerar_regex_geral('defiro a instauração')],
         'checar_anexos_instauracao', None, None),

        # REGRA DE TENDO EM VISTA
        ([gerar_regex_geral(k) for k in ['tendo em vista que', 'pagamento da parcela pendente', 'sob pena de sequestro']],
         'checar_anexos_tendo_em_vista', None, None),

        # REGRA DE NÃO AMPARADA
        ([gerar_regex_geral('não está amparada')],
         None, None, ato_meios),

        # REGRA DE INSTAURADO EM FACE
        ([gerar_regex_geral('instaurado em face')],
         None, None, 'idpj'),
    ]


def _processar_regras_gerais(driver: WebDriver, texto_normalizado: str, doc_idx: int = 0):
    """
    Helper: Processa regras gerais usando abordagem SEQUENCIAL do p2b.py ORIGINAL.
    Mantém ordem de precedência: prescrição > arquivamento > bloqueio > regras gerais

    Args:
        driver: WebDriver instance
        texto_normalizado: Texto normalizado para análise
        doc_idx: Índice atual do documento na timeline (para checar_prox)

    Returns:
        Tupla (doc_encontrado, doc_link, doc_idx) se checar_prox encontrou próximo documento,
        None caso contrário
    """
    # Lazy load modules
    m = _lazy_import()
    mov_arquivar = m['mov_arquivar']
    criar_gigs = m['criar_gigs']
    
    regras = _definir_regras_processamento()

    # 5. VERIFICAÇÃO DE PREVALÊNCIA: Homologo o acordo tem prioridade máxima - não aplicar nada
    regex_homologo_acordo = gerar_regex_geral('Homologo o acordo')
    if regex_homologo_acordo.search(texto_normalizado):
        print('[FLUXO_PZ] ✅ PREVALÊNCIA MÁXIMA: "Homologo o acordo" detectado - NÃO APLICAR NENHUMA AÇÃO')
        return  # SAIR imediatamente sem fazer nada

    # 5. VERIFICAÇÃO DE PREVALÊNCIA: prescreve tem prioridade absoluta
    regex_prescreve = gerar_regex_geral('A pronúncia da')
    if regex_prescreve.search(texto_normalizado):
        print('[FLUXO_PZ] ✅ PREVALÊNCIA: Prescrição detectada - executando com prioridade máxima')
        try:
            prescreve(driver)  # Será implementado quando necessário
            print('[FLUXO_PZ] ✅ Prescrição executada - ENCERRANDO fluxo (prevalência)')
            return  # SAIR imediatamente
        except Exception as prescreve_error:
            print(f'[FLUXO_PZ] ❌ Erro na execução de prescreve: {prescreve_error}')
            # Continua com regras normais se prescreve falhar

    # 5.1. VERIFICAÇÃO DE PREVALÊNCIA: arquivamento tem prioridade máxima sobre outras regras
    regex_arquivamento = gerar_regex_geral('julgo extinta a presente execução, nos termos do art. 924')
    if regex_arquivamento.search(texto_normalizado):
        print('[FLUXO_PZ] ✅ PREVALÊNCIA: Arquivamento detectado - executando com prioridade máxima')
        try:
            resultado_arquivamento = mov_arquivar(driver)
            if resultado_arquivamento:
                print('[FLUXO_PZ] ✅ Arquivamento executado com SUCESSO - ENCERRANDO fluxo (prevalência)')
                return  # SAIR imediatamente
            else:
                print('[FLUXO_PZ] ❌ Arquivamento FALHOU - continuando com regras normais')
        except Exception as arquivamento_error:
            print(f'[FLUXO_PZ] ❌ Erro na execução de arquivamento: {arquivamento_error}')
            # Continua com regras normais se arquivamento falhar

    # 6. Iterate through rules and keywords to find the first match
    acao_definida = None
    parametros_acao = None
    termo_encontrado = None
    acao_secundaria = None  # Reset before checking rules

    print(f'[FLUXO_PZ][DEBUG] Iniciando verificação de {len(regras)} regras...')

    for idx, (keywords, tipo_acao, params, acao_sec) in enumerate(regras):
        for regex in keywords:
            match = regex.search(texto_normalizado)
            if match:
                # Log da regra encontrada
                print(f'[FLUXO_PZ][DEBUG] ✅ Match encontrado na regra #{idx}')
                print(f'[FLUXO_PZ][DEBUG] Regex pattern: {regex.pattern}')
                print(f'[FLUXO_PZ][DEBUG] Match text: {match.group(0)}')
                print(f'[FLUXO_PZ] Regra aplicada: {tipo_acao} - {params if params else acao_sec.__name__ if acao_sec else "Nenhuma"}')
                acao_definida = tipo_acao
                parametros_acao = params
                acao_secundaria = acao_sec
                termo_encontrado = regex.pattern
                # NOVA REGRA: se acao_definida == 'checar_prox', chamar checar_prox imediatamente
                if acao_definida == 'checar_prox':
                    from Prazo.p2b_core import checar_prox
                    # Obter itens da timeline para checar_prox
                    itens = driver.find_elements(By.CSS_SELECTOR, 'li.tl-item-container')
                    print(f'[FLUXO_PZ][DEBUG] Chamando checar_prox com doc_idx={doc_idx}, len(itens)={len(itens)}')
                    prox_doc_encontrado, prox_doc_link, prox_doc_idx = checar_prox(driver, itens, doc_idx, regras, texto_normalizado)
                    if prox_doc_encontrado and prox_doc_link:
                        print(f'[FLUXO_PZ] Regra de cancelamento/baixa: buscando próximo documento relevante')
                        # Retornar os valores encontrados para que o fluxo continue com o próximo documento
                        return prox_doc_encontrado, prox_doc_link, prox_doc_idx
                    else:
                        print(f'[FLUXO_PZ] Nenhum próximo documento relevante encontrado')
                break
        if acao_definida:
            break

    # Log se nenhuma regra foi encontrada
    if not acao_definida:
        print('[FLUXO_PZ][DEBUG] ❌ Nenhuma regra encontrada para o texto extraído')
        print(f'[FLUXO_PZ][DEBUG] Tamanho total do texto: {len(texto_normalizado)} caracteres')
        print(f'[FLUXO_PZ][DEBUG] Primeiras 1000 chars: {texto_normalizado[:1000]}')
        # Buscar especificamente por "comprovar" para debug
        if 'comprovar' in texto_normalizado:
            idx = texto_normalizado.find('comprovar')
            print(f'[FLUXO_PZ][DEBUG] ✅ "comprovar" encontrado na posição {idx}')
            print(f'[FLUXO_PZ][DEBUG] Contexto: {texto_normalizado[max(0,idx-50):idx+100]}')
        else:
            print('[FLUXO_PZ][DEBUG] ❌ "comprovar" NÃO encontrado no texto')

    # 6. Perform action(s) based on the matched rule (or default)
    import datetime
    gigs_aplicado = False
    if acao_definida == 'gigs':
        # parametros_acao já está no formato 'dias/responsavel/observacao'
        try:
            print(f'[FLUXO_PZ][DEBUG] Regra GIGS encontrada: {parametros_acao}')
            print(f'[FLUXO_PZ][DEBUG] Ação secundária: {acao_secundaria.__name__ if acao_secundaria else "Nenhuma"}')

            dias, responsavel, observacao = parse_gigs_param(parametros_acao)
            criar_gigs(driver, dias, responsavel, observacao)
            gigs_aplicado = True
            print(f'[FLUXO_PZ] GIGS criado: {observacao}')

            if acao_secundaria:
                # Tratamento especial para função 'idpj'
                if acao_secundaria == 'idpj':
                    print('[FLUXO_PZ] Executando ação secundária: IDPJ (instaurado em face)')
                    try:
                        from atos import idpj
                        resultado_idpj = idpj(driver, debug=True)
                        print(f'[FLUXO_PZ][DEBUG] Resultado do IDPJ: {resultado_idpj}')
                    except Exception as idpj_error:
                        logger.error(f'[FLUXO_PZ] Falha ao executar IDPJ: {idpj_error}')
                else:
                    print(f'[FLUXO_PZ] Executando ação secundária: {acao_secundaria.__name__}')
                    try:
                        resultado_callback = acao_secundaria(driver)
                        print(f'[FLUXO_PZ][DEBUG] Resultado do callback: {resultado_callback}')
                    except TypeError:
                        acao_secundaria(driver)
                time.sleep(1)
        except Exception as gigs_error:
            logger.error(f'[FLUXO_PZ] Falha ao criar GIGS ou na ação secundária: {gigs_error}')

    elif acao_definida == 'movimentar':
         func_movimento = parametros_acao
         print(f'[FLUXO_PZ] Executando movimentação: {func_movimento.__name__}')
         try:
             resultado_movimento = func_movimento(driver)
             if resultado_movimento:
                 print(f'[FLUXO_PZ] Movimentação {func_movimento.__name__} executada com SUCESSO.')
             else:
                 logger.error(f'[FLUXO_PZ] Movimentação {func_movimento.__name__} FALHOU (retornou False).')
         except Exception as mov_error:
             logger.error(f'[FLUXO_PZ] Falha ao executar movimentação {func_movimento.__name__}: {mov_error}')

    elif acao_definida == 'checar_cabecalho_impugnacoes':
        _processar_cabecalho_impugnacoes(driver)

    # Se não há ação primária mas existe ação secundária, trate a secundária como primária
    if acao_definida is None and acao_secundaria:
        # Tratamento especial para função 'idpj'
        if acao_secundaria == 'idpj':
            print('[FLUXO_PZ] Executando função IDPJ (instaurado em face)')
            try:
                from atos import idpj
                resultado_idpj = idpj(driver, debug=True)
                if resultado_idpj:
                    print('[FLUXO_PZ] ✅ Função IDPJ executada com sucesso')
                else:
                    print('[FLUXO_PZ] ❌ Função IDPJ falhou')
            except Exception as idpj_error:
                logger.error(f'[FLUXO_PZ] Falha ao executar função IDPJ: {idpj_error}')
        else:
            print(f'[FLUXO_PZ] Executando ação: {acao_secundaria.__name__}')
            try:
                acao_secundaria(driver)
                time.sleep(1)
            except Exception as sec_error:
                logger.error(f'[FLUXO_PZ] Falha ao executar ação {acao_secundaria.__name__}: {sec_error}')


def _processar_cabecalho_impugnacoes(driver: WebDriver) -> None:
    """
    Helper: Processa checagem de cabeçalho para impugnações.
    """
    # Lazy load modules
    m = _lazy_import()
    ato_pesquisas = m['ato_pesquisas']
    ato_pesqliq = m['ato_pesqliq']
    criar_gigs = m['criar_gigs']
    
    # Implementação baseada no p2b.py original
    try:
        cabecalho = driver.find_element(By.CSS_SELECTOR, 'mat-card.resumo-processo')
        cor_fundo = cabecalho.value_of_css_property('background-color')
        print(f'[FLUXO_PZ] Cor do cabeçalho detectada para impugnações: {cor_fundo}')

        # Verifica se é verde: rgb(76, 175, 80) - fase de liquidação
        if 'rgb(76, 175, 80)' in cor_fundo:
            print('[FLUXO_PZ] Cabeçalho verde detectado - fase de liquidação')
            try:
                # Procurar "Iniciar Execução"
                iniciar_exec = driver.find_element(By.XPATH, "//button[contains(text(),'Iniciar Execução')]")
                iniciar_exec.click()
                time.sleep(1)
                print('[FLUXO_PZ] Iniciar Execução clicado - executando ato_pesquisa (modelo xsbacen)')
                sucesso, sigilo_ativado = ato_pesquisas(driver)
                if sucesso:
                    # Aplicar visibilidade se necessário
                    if sigilo_ativado:
                        _executar_visibilidade_sigilosos(driver, sigilo_ativado, debug=True)
            except Exception as e:
                print(f'[FLUXO_PZ] Iniciar Execução não encontrado - usando conclusão homologação de cálculos: {e}')
                # Buscar conclusão homologação de cálculos
                try:
                    itens = driver.find_elements(By.CSS_SELECTOR, 'li.tl-item-container')
                    for item in itens:
                        link = item.find_element(By.CSS_SELECTOR, 'a.tl-documento')
                        if 'homologação de cálculos' in link.text.lower() or 'homologacao de calculos' in link.text.lower():
                            link.click()
                            time.sleep(2)
                            print('[FLUXO_PZ] Conclusão homologação clicada - executando ato_pesquisa')
                            sucesso, sigilo_ativado = ato_pesquisas(driver)
                            if sucesso:
                                # Aplicar visibilidade se necessário
                                if sigilo_ativado:
                                    _executar_visibilidade_sigilosos(driver, sigilo_ativado, debug=True)
                            break
                except Exception as e2:
                    print(f'[FLUXO_PZ] Erro ao buscar conclusão homologação: {e2}')

        # Verifica se é cinza: rgb(144, 164, 174)
        elif 'rgb(144, 164, 174)' in cor_fundo:
            print('[FLUXO_PZ] Cabeçalho cinza detectado - executando criar_gigs + pesquisas')

            # 1. Criar gigs antes das pesquisas
            print('[FLUXO_PZ] Etapa 1: Criando gigs (1/Silvia/Argos)')
            criar_gigs(driver, "1", "Silvia", "Argos")
            time.sleep(3)  # Aguardar modal fechar completamente e snackbar desaparecer
            # Criar GIGS adicional "1//xs sigilo"
            print('[FLUXO_PZ] Etapa 1b: Criando segundo gigs (1//xs sigilo)')
            criar_gigs(driver, "1", "", "xs sigilo")

            # 2. Executar pesquisas
            print('[FLUXO_PZ] Etapa 2: Executando pesquisas')
            sucesso, sigilo_ativado = ato_pesquisas(driver)
            if sucesso:
                # Aplicar visibilidade se necessário
                if sigilo_ativado:
                    _executar_visibilidade_sigilosos(driver, sigilo_ativado, debug=True)
            else:
                print('[FLUXO_PZ] ⚠️ Falha ao executar ato_pesquisas')
        else:
            print('[FLUXO_PZ] Cabeçalho não é cinza - executando criar_gigs + mov_exec + pesquisas')

                # 1. Criar gigs antes de tudo
            print('[FLUXO_PZ] Etapa 1: Criando gigs (1/Silvia/Argos)')
            criar_gigs(driver, "1", "Silvia", "Argos")
            time.sleep(3)  # Aguardar modal fechar completamente e snackbar desaparecer
            # Criar GIGS adicional "1/xs sigilo" (observacao='xs sigilo', responsavel='')
            print('[FLUXO_PZ] Etapa 1b: Criando segundo gigs (1//xs sigilo)')
            criar_gigs(driver, "1", "", "xs sigilo")

            # 2. Executar movimento
            print('[FLUXO_PZ] Etapa 2: Executando mov_exec')
            try:
                from atos.wrappers_mov import mov_exec
                mov_ok = mov_exec(driver)
            except Exception as _mov_e:
                print(f'[FLUXO_PZ] ❌ Erro em mov_exec: {_mov_e}')
                mov_ok = False

            # Se não conseguiu executar mov_exec, executar fallback PESQLIQ
            if not mov_ok:
                print('[FLUXO_PZ] ⚠️ mov_exec falhou - executando ato_pesqliq como fallback')
                try:
                    resultado_pesq = ato_pesqliq(driver)
                    if isinstance(resultado_pesq, tuple):
                        sucesso, sigilo_ativado = resultado_pesq
                    else:
                        sucesso = resultado_pesq
                        sigilo_ativado = True  # ato_pesqliq ativa sigilo internamente
                    if sucesso:
                        if sigilo_ativado:
                            _executar_visibilidade_sigilosos(driver, sigilo_ativado, debug=True)
                    else:
                        print('[FLUXO_PZ] ⚠️ Falha ao executar ato_pesqliq no fallback')
                except Exception as _e_pesq:
                    print(f'[FLUXO_PZ] ❌ Erro no fallback ato_pesqliq: {_e_pesq}')
            else:
                # 3. Fechar aba atual para voltar ao processo
                print('[FLUXO_PZ] Etapa 3: Fechando aba atual para voltar ao processo')
                try:
                    driver.close()
                    if len(driver.window_handles) > 0:
                        driver.switch_to.window(driver.window_handles[-1])
                        print('[FLUXO_PZ] ✅ Voltou para aba do processo')
                    else:
                        print('[FLUXO_PZ] ⚠️ Nenhuma aba disponível após fechamento')
                except Exception as close_error:
                    print(f'[FLUXO_PZ] ⚠️ Erro ao fechar aba: {close_error}')

                # 4. Executar pesquisas na aba do processo
                print('[FLUXO_PZ] Etapa 4: Executando pesquisas')
                sucesso, sigilo_ativado = ato_pesquisas(driver)
                if sucesso:
                    # Aplicar visibilidade se necessário
                    if sigilo_ativado:
                        _executar_visibilidade_sigilosos(driver, sigilo_ativado, debug=True)
                else:
                    print('[FLUXO_PZ] ⚠️ Falha ao executar ato_pesquisas')

        time.sleep(1)
    except Exception as cabecalho_error:
        logger.error(f'[FLUXO_PZ] Erro ao verificar cor do cabeçalho para impugnações: {cabecalho_error}')


def _processar_checar_cabecalho(driver: WebDriver) -> None:
    """
    Helper: Processa checagem de cabeçalho para "Ante a notícia de descumprimento".
    """
    # Lazy load modules
    m = _lazy_import()
    ato_pesquisas = m['ato_pesquisas']
    ato_pesqliq = m['ato_pesqliq']
    criar_gigs = m['criar_gigs']
    
    try:
        cabecalho = driver.find_element(By.CSS_SELECTOR, 'mat-card.resumo-processo')
        cor_fundo = cabecalho.value_of_css_property('background-color')
        print(f'[FLUXO_PZ] Cor do cabeçalho detectada: {cor_fundo}')

        # Verifica se é cinza: rgb(144, 164, 174)
        if 'rgb(144, 164, 174)' in cor_fundo:
            print('[FLUXO_PZ] Cabeçalho cinza detectado - executando pesquisas')
            sucesso, sigilo_ativado = ato_pesquisas(driver)
            if sucesso:
                # Aplicar visibilidade se necessário
                if sigilo_ativado:
                    _executar_visibilidade_sigilosos(driver, sigilo_ativado, debug=True)
        else:
            print('[FLUXO_PZ] Cabeçalho não é cinza - criando GIGS padrão')
            dias, responsavel, observacao = parse_gigs_param('1/SILVIA/Argos')
            criar_gigs(driver, dias, responsavel, observacao)
            time.sleep(3)  # Aguardar modal fechar completamente e snackbar desaparecer
            # Criar GIGS adicional "1/xs sigilo" (observacao='xs sigilo', responsavel='')
            print('[FLUXO_PZ] Criando segundo gigs (1//xs sigilo)')
            criar_gigs(driver, "1", "", "xs sigilo")
            # Executar ato_pesqliq como ação secundária
            sucesso, sigilo_ativado = ato_pesqliq(driver)
            if sucesso:
                # Aplicar visibilidade se necessário
                if sigilo_ativado:
                    _executar_visibilidade_sigilosos(driver, sigilo_ativado, debug=True)
    except Exception as cabecalho_error:
        logger.error(f'[FLUXO_PZ] Erro ao verificar cor do cabeçalho: {cabecalho_error}')


def _executar_visibilidade_sigilosos(driver: WebDriver, sigilo_ativado: bool, debug: bool = False) -> None:
    """
    Helper: Executa visibilidade para sigilosos se necessário.
    """
    # Implementação será movida para helper específico
    pass


def _fechar_aba_processo(driver: WebDriver) -> None:
    """
    Helper: Fecha aba do processo e volta para lista.
    """
    all_windows = driver.window_handles
    main_window = all_windows[0]
    current_window = driver.current_window_handle

    if current_window != main_window and len(all_windows) > 1:
        driver.close()
        try:
            if main_window in driver.window_handles:
                driver.switch_to.window(main_window)
            elif driver.window_handles:
                driver.switch_to.window(driver.window_handles[0])
        except Exception as e:
            print(f"[LIMPEZA][ERRO] Falha ao alternar para aba válida: {e}")
            try:
                driver.current_url  # Testa se aba está acessível
            except Exception:
                print("[LIMPEZA][ERRO] Tentou acessar aba já fechada.")

    print('[FLUXO_PZ] Processo concluído, retornando à lista')
# ===== VALIDAÇÃO =====

if __name__ == "__main__":
    print("P2B Fluxo PZ Helpers - Teste básico")

    # Teste importações
    try:
        from Prazo.p2b_core import normalizar_texto, gerar_regex_geral
        print("✅ Importações do p2b_core funcionam")

        # Teste funções básicas
        teste = "TESTE ÁCÊNTÖS"
        resultado = normalizar_texto(teste)
        print(f"✅ Normalização funciona: '{teste}' -> '{resultado}'")

    except ImportError as e:
        print(f"❌ Erro de importação: {e}")

    print("✅ P2B Fluxo PZ Helpers validado")