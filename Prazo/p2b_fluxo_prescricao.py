import logging
import time

from selenium.webdriver.remote.webdriver import WebDriver

from .p2b_fluxo_lazy import _lazy_import

logger = logging.getLogger(__name__)


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
        pass
        
        # 0. Executa BNDT (exclusão via Fix.bndt)
        pass
        try:
            from Fix import bndt
            bndt_resultado = bndt(driver, inclusao=False)
        except Exception as e:
            pass
            bndt_resultado = False
        
        # 1. Checagem de timeline
        pass
        documentos = analisar_timeline_prescreve_js_puro(driver)
        
        if not documentos:
            pass
            return False
        
        # 2. Executar ações em ORDEM SEQUENCIAL
        pass
        
        # Ação 1: Localizar Serasa/CNIB em anexos e chamar pec_excluiargos (UMA VEZ)
        anexos_serasa_cnib = [d for d in documentos if d.get('isAnexo', False) and d.get('tipo', '').lower() in ['serasa', 'cnib']]
        if anexos_serasa_cnib:
            pass
            try:
                resultado = pec_excluiargos(driver)
                if resultado:
                    pass
                else:
                    pass
            except Exception as e:
                logger.error(f'[PRESCREVE]  Erro ao executar pec_excluiargos: {e}')
        
        # Ação 2: Serasa fora de anexos + nenhum Serasa em anexos = criar_gigs Bianca
        serasa_timeline = [d for d in documentos if not d.get('isAnexo', False) and 'serasa' in d.get('tipo', '').lower()]
        tem_serasa_anexo = any(d.get('isAnexo', False) and 'serasa' in d.get('tipo', '').lower() for d in documentos)

        if serasa_timeline and not tem_serasa_anexo:
            pass
            try:
                resultado = criar_gigs(driver, "1", "Bianca", "Serasa")
                if resultado:
                    pass
                else:
                    pass
            except Exception as e:
                logger.error(f'[PRESCREVE]  Erro ao criar GIGS: {e}')
        
        pass
        return True
        
    except Exception as e:
        logger.error(f'[PRESCREVE]  Erro geral na função prescreve: {e}')
        return False


def analisar_timeline_prescreve_js_puro(driver: WebDriver):
    """
    Análise da timeline usando JavaScript PURO - replicando o script fornecido.
    Executa em SEGUNDOS como o userscript original.
    """
    try:
        pass
        
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
                const m = link.textContent.trim().match(/\s-\s([A-Za-z0-9]+)$/);
                return m ? m[1] : null;
            }
            
            function extrairData(item) {
                const dEl = item.querySelector('.tl-data[name="dataItemTimeline"]') || item.querySelector('.tl-data');
                const txt = dEl?.textContent.trim() || '';
                const m = txt.match(/(\d{1,2}\/\d{1,2}\/\d{4})/);
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
        start_time = time.time()
        
        resultado_json = driver.execute_script(js_script)
        
        elapsed = time.time() - start_time
        pass
        
        # Processar resultado
        import json
        try:
            documentos_data = json.loads(resultado_json)
            
            if isinstance(documentos_data, dict) and 'error' in documentos_data:
                logger.error(f'[PRESCREVE][TIMELINE]  Erro no JavaScript: {documentos_data["error"]}')
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
            
            pass
            
            # Log simplificado conforme solicitado
            cnib_serasa_anexos = sum(1 for d in documentos if d.get('isAnexo', False) and d.get('tipo', '').lower() in ['cnib', 'serasa'])
            alvaras = sum(1 for d in documentos if d.get('tipo', '').lower() == 'alvará')
            serasa_nao_anexo = sum(1 for d in documentos if not d.get('isAnexo', False) and d.get('tipo', '').lower() == 'serasa')
            
            pass
            
            return documentos
            
        except json.JSONDecodeError as e:
            logger.error(f'[PRESCREVE][TIMELINE]  Erro ao decodificar JSON: {e}')
            pass
            return []
        
    except Exception as e:
        logger.error(f'[PRESCREVE][TIMELINE]  Erro na análise JavaScript: {e}')
        return []