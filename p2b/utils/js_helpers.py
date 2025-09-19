"""
JavaScript utilities para análise de timeline no PJE
Extraído da função monolítica analisar_timeline_prescreve_js_puro()
"""

class TimelineJSAnalyzer:
    """Analisador de timeline usando JavaScript puro"""

    @staticmethod
    def get_timeline_extraction_script():
        """
        Retorna o script JavaScript para extração de documentos da timeline
        Extraído da função analisar_timeline_prescreve_js_puro()
        """
        return """
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
                    isAnexo: false,
                    linkHref: link.href || '',
                    linkId: link.id || ''
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

    @staticmethod
    def execute_timeline_analysis(driver):
        """
        Executa a análise completa da timeline usando JavaScript

        Args:
            driver: WebDriver instance

        Returns:
            list: Lista de documentos encontrados
        """
        import time
        import json

        try:
            print('[TIMELINE_JS] Executando análise via JavaScript PURO...')

            # Obter script JavaScript
            js_script = TimelineJSAnalyzer.get_timeline_extraction_script()

            # Executar JavaScript
            start_time = time.time()
            resultado_json = driver.execute_script(js_script)
            elapsed = time.time() - start_time

            print(f'[TIMELINE_JS] ✅ JavaScript executado em {elapsed:.2f}s')

            # Processar resultado
            try:
                documentos_data = json.loads(resultado_json)

                if isinstance(documentos_data, dict) and 'error' in documentos_data:
                    print(f'[TIMELINE_JS] ❌ Erro no JavaScript: {documentos_data["error"]}')
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
                        'parentId': doc.get('parentId', None),
                        'linkHref': doc.get('linkHref', ''),
                        'linkId': doc.get('linkId', '')
                    })

                print(f'[TIMELINE_JS] ✅ {len(documentos)} documentos encontrados')

                # Log resumido por tipo
                tipos_count = {}
                for doc in documentos:
                    tipos_count[doc['tipo']] = tipos_count.get(doc['tipo'], 0) + 1

                for tipo, count in tipos_count.items():
                    print(f'[TIMELINE_JS]   - {tipo}: {count}')

                return documentos

            except json.JSONDecodeError as e:
                print(f'[TIMELINE_JS] ❌ Erro ao decodificar JSON: {e}')
                print(f'[TIMELINE_JS] Resultado recebido: {resultado_json[:200]}...')
                return []

        except Exception as e:
            print(f'[TIMELINE_JS] ❌ Erro na análise JavaScript: {e}')
            return []