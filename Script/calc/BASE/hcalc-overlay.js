(function () {
    'use strict';
    const HCALC_DEBUG = false;
    const dbg = (...args) => { if (HCALC_DEBUG) console.log('[hcalc]', ...args); };
    const warn = (...args) => console.warn('[hcalc]', ...args);
    const err = (...args) => console.error('[hcalc]', ...args);
    // Proxies para dependencias de hcalc-core.js e hcalc-pdf.js
    const normalizarNomeParaComparacao = n => window.normalizarNomeParaComparacao(n);
    const carregarPDFJSSeNecessario = () => window.carregarPDFJSSeNecessario();
    const processarPlanilhaPDF = (...a) => window.processarPlanilhaPDF(...a);
    const executarPrep = (...a) => window.executarPrep(...a);
    const destacarElementoNaTimeline = (...a) => window.destacarElementoNaTimeline(...a);
    const encontrarItemTimeline = (href) => window.encontrarItemTimeline && window.encontrarItemTimeline(href);
    const expandirAnexos = (item) => window.expandirAnexos && window.expandirAnexos(item);
    // ==========================================
    function initializeBotao() {
        if (window.__hcalcBotaoInitialized) {
            dbg('initializeBotao ignorado: botão já inicializado.');
            return;
        }
        dbg('initializeBotao iniciado (FASE A - leve).');
        window.__hcalcBotaoInitialized = true;

        // CSS mínimo — apenas o botão (~200 bytes)
        if (!document.getElementById('hcalc-btn-style')) {
            const s = document.createElement('style');
            s.id = 'hcalc-btn-style';
            s.innerText = `
        #btn-abrir-homologacao {
            position: fixed; bottom: 20px; right: 20px; z-index: 99999;
            background: #00509e; color: white; border: none; border-radius: 6px;
            padding: 10px 18px; font-size: 13px; font-weight: bold; cursor: pointer;
            box-shadow: 0 3px 5px rgba(0,0,0,0.3);
        }
        #btn-abrir-homologacao:hover { background: #003d7a; }`;
            document.head.appendChild(s);
        }

        // Injeta APENAS botão + input file (sem overlay)
        document.body.insertAdjacentHTML(
            'beforeend',
            `
            <button id="btn-abrir-homologacao" type="button">
                \uD83D\uDCC4 Carregar Planilha
            </button>
            <input
                id="input-planilha-pdf"
                type="file"
                accept="application/pdf"
                style="display:none"
            />
            `
        );

        const btn = document.getElementById('btn-abrir-homologacao');

        // Handler do botão — inicializa overlay lazy na primeira vez
        btn.onclick = async () => {
            if (!window.__hcalcOverlayInitialized) {
                dbg('Primeiro clique: carregando overlay completo (lazy init)...');
                initializeOverlay();
                // initializeOverlay substitui btn.onclick com o handler completo
            }

            // FASE 1: ainda não há planilha carregada
            if (!window.hcalcState.planilhaCarregada) {
                dbg('FASE 1: abrindo file picker.');
                document.getElementById('input-planilha-pdf').click();
                return;
            }

            // FASE 3: overlay já inicializado e planilha carregada
            btn.click();
        };
        dbg('Botão flutuante injetado (lazy init ativo).');
    }


    function initializeOverlay() {
        if (window.__hcalcOverlayInitialized) {
            dbg('initializeOverlay ignorado: overlay ja inicializado.');
            return;
        }
        dbg('initializeOverlay iniciado.');
        window.__hcalcOverlayInitialized = true;

        // ==========================================
        // 1. ESTILOS DO OVERLAY E BOTÃO (v1.9 - UI Compacta)
        // ==========================================
        const styles = `
        #homologacao-overlay {
            display: none; position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
            background: transparent; z-index: 100000; justify-content: flex-end; align-items: flex-start;
            font-family: Arial, sans-serif; pointer-events: none;
        }

        #homologacao-modal {
            background: #fff; width: 630px; max-width: 630px; height: 100vh; max-height: 100vh; overflow-y: auto;
            border-radius: 0; box-shadow: -4px 0 20px rgba(0,0,0,0.25); padding: 10px; margin: 0;
            display: flex; flex-direction: column; gap: 5px; color: #333; pointer-events: all;
        }

        .modal-header { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #ddd; padding-bottom: 6px; margin-bottom: 3px; }
        .modal-header h2 { margin: 0; color: #00509e; font-size: 15px; }
        .btn-close { background: #cc0000; color: white; border: none; padding: 3px 10px; cursor: pointer; border-radius: 3px; font-weight: bold; font-size: 11px; }

        fieldset { border: 1px solid #ddd; border-radius: 4px; padding: 6px; margin-bottom: 4px; background: #fff; }
        legend { background: #00509e; color: white; padding: 2px 6px; border-radius: 3px; font-size: 12px; font-weight: bold; }

        .row { display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 4px; align-items: center; }
        .col { display: flex; flex-direction: column; flex: 1; min-width: 140px; }

        label { font-size: 11px; font-weight: bold; margin-bottom: 3px; color: #555; }
        input[type="text"], input[type="date"] { padding: 6px; border: 1px solid #aaa; border-radius: 3px; font-size: 13px; }
        textarea { padding: 6px; border: 1px solid #aaa; border-radius: 3px; font-size: 12px; resize: vertical; font-family: Arial, sans-serif; }
        select { padding: 6px; border: 1px solid #aaa; border-radius: 3px; font-size: 13px; }

        .hidden { display: none !important; }
        /* Destaque para o campo atual da coleta */
        .highlight { border: 2px solid #ff9800 !important; background: #fffde7 !important; box-shadow: 0 0 6px rgba(255,152,0,0.4); }

        /* Badges para partes detectadas (v1.9) */
        .partes-badges { display: flex; flex-wrap: wrap; gap: 5px; margin: 6px 0; }
        .badge {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: 600;
            white-space: nowrap;
        }
        .badge-blue { background: #e0f2fe; color: #0369a1; border: 1px solid #bae6fd; }
        .badge-gray { background: #f3f4f6; color: #6b7280; border: 1px solid #e5e7eb; }
        .badge-green { background: #d1fae5; color: #047857; border: 1px solid #a7f3d0; }

        .btn-action { background: #28a745; color: white; border: none; padding: 8px 12px; border-radius: 3px; cursor: pointer; font-weight: bold; font-size: 13px; }
        .btn-action:hover { background: #218838; }
        .btn-gravar { background: #00509e; width: 100%; padding: 12px; font-size: 16px; margin-top: 10px; }

        /* Compactar espaçamento interno para caber na tela */
        #homologacao-modal fieldset { padding: 8px 10px; margin-bottom: 6px; }
        #homologacao-modal .row { margin-bottom: 6px; gap: 8px; }
        #homologacao-modal input[type=text],
        #homologacao-modal input[type=date],
        #homologacao-modal select,
        #homologacao-modal textarea { padding: 5px 7px; font-size: 12px; }
        #homologacao-modal label { font-size: 11px; margin-bottom: 2px; }
        #homologacao-modal legend { font-size: 12px; padding: 3px 8px; }
        #homologacao-modal .btn-gravar { padding: 10px; font-size: 15px; margin-top: 10px; }

        /* Estilos do Card de Resumo da Planilha (FASE 1) */
        #resumo-extracao-card {
            width: 260px;
            background: #f8f9fa;
            border: 2px solid #10b981;
            border-radius: 8px;
            padding: 0;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            pointer-events: all;
            align-self: flex-start;
            margin-right: 8px;
            overflow: hidden;
            flex-shrink: 0;
        }
        #resumo-extracao-card h4 {
            margin: 0;
            padding: 10px 12px;
            border-bottom: 1px solid #10b981;
            cursor: pointer;
            user-select: none;
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 13px;
            color: #16a34a;
            background: #f0fdf4;
        }
        #resumo-extracao-card h4:hover { background: #dcfce7; }
        #resumo-body {
            padding: 10px 12px;
            display: none;
        }
        #resumo-conteudo { display: flex; flex-direction: column; gap: 6px; }
        .resumo-item {
            padding: 4px 6px;
            background: white;
            border-radius: 4px;
            border: 1px solid #e5e7eb;
            font-size: 12px;
        }
        .resumo-item strong { color: #16a34a; }
        #btn-reload-planilha {
            margin-top: 8px;
            width: 100%;
            padding: 5px 10px;
            font-size: 11px;
            border-radius: 4px;
            border: 1px solid #10b981;
            background: #fff;
            color: #10b981;
            cursor: pointer;
        }
        #btn-reload-planilha:hover { background: #10b981; color: white; }

        /* Recursos com anexos — integrado de rec.js v1.0 */
        .rec-recurso-card {
            padding: 8px 10px; margin-bottom: 6px;
            border: 1px solid #e5e7eb; border-radius: 5px;
            background: white; cursor: pointer; transition: all 0.2s;
        }
        .rec-recurso-card:hover { background: #f0f9ff; border-color: #3b82f6; }
        .rec-tipo-badge {
            display: inline-block; padding: 1px 7px; border-radius: 3px;
            font-size: 10px; font-weight: 700; color: white;
            background: #3b82f6; margin-right: 6px;
        }
        .rec-anexos-lista { margin-top: 6px; padding-top: 5px; border-top: 1px solid #e5e7eb; display: none; }
        .rec-recurso-card.expandido .rec-anexos-lista { display: block; }
        .rec-anexo-item {
            display: flex; align-items: center; gap: 6px;
            padding: 3px 4px; border-radius: 3px; cursor: pointer;
            font-size: 11px; transition: background 0.15s;
        }
        .rec-anexo-item:hover { background: #f3f4f6; }
        .rec-anexo-badge {
            padding: 1px 5px; border-radius: 2px;
            font-size: 10px; font-weight: 600; color: white; white-space: nowrap;
        }
        .rec-anexo-id {
            font-size: 10px; background: #f3f4f6;
            padding: 1px 4px; border-radius: 2px;
            font-family: monospace; color: #374151; user-select: all;
        }
        .rec-seta-toggle { font-size: 10px; color: #9ca3af; margin-left: auto; }
    `;
        if (!document.getElementById('hcalc-overlay-style')) {
            const styleSheet = document.createElement('style');
            styleSheet.id = 'hcalc-overlay-style';
            styleSheet.innerText = styles;
            document.head.appendChild(styleSheet);
        }

        // ==========================================
        // 2. HTML DO OVERLAY (ESTRUTURA)
        // ==========================================
        const htmlModal = `
    <div id="homologacao-overlay">
        <!-- Card de Resumo da Planilha Extraída (à esquerda) -->
        <div id="resumo-extracao-card" style="display:none">
            <h4 id="resumo-toggle">
                <span>📋 Planilha Carregada</span>
                <span id="resumo-seta">▶</span>
            </h4>
            <div id="resumo-body">
                <div id="resumo-conteudo"></div>
                <button id="btn-reload-planilha">🔄 Recarregar PDF</button>
            </div>
        </div>
       
        <div id="homologacao-modal">
            <div class="modal-header">
                <h2>Assistente de Homologação</h2>
                <button class="btn-close" id="btn-fechar">X Fechar</button>
            </div>



            <!-- SEÇÃO 1 e 2: BASE E PARTE -->
            <fieldset>
                <legend>Cálculo Base e Autoria</legend>
                <div class="row">
                    <div class="col">
                        <label>Origem do Cálculo</label>
                        <select id="calc-origem">
                            <option value="pjecalc" selected>PJeCalc</option>
                            <option value="outros">Outros</option>
                        </select>
                    </div>
                    <div class="col" id="col-pjc">
                        <label><input type="checkbox" id="calc-pjc" checked> Acompanha arquivo .PJC?</label>
                    </div>
                    <div class="col">
                        <label>Autor do Cálculo</label>
                        <select id="calc-autor">
                            <option value="autor" selected>Reclamante (Autor)</option>
                            <option value="reclamada">Reclamada</option>
                            <option value="perito">Perito</option>
                        </select>
                    </div>
                    <div class="col hidden" id="col-esclarecimentos">
                        <label><input type="checkbox" id="calc-esclarecimentos" checked> Esclarecimentos do Perito?</label>
                        <input type="text" id="calc-peca-perito" placeholder="Id da Peça">
                    </div>
                </div>
            </fieldset>

            <!-- SEÇÃO 3: ATUALIZAÇÃO -->
            <fieldset>
                <legend>Atualização</legend>
                <div class="row">
                    <div class="col">
                        <label>Índice de Atualização</label>
                        <select id="calc-indice">
                            <option value="adc58" selected>SELIC / IPCA-E (ADC 58)</option>
                            <option value="tr">TR / IPCA-E (Casos Antigos)</option>
                        </select>
                    </div>
                </div>
            </fieldset>

            <!-- SEÇÃO 5: DADOS COPIADOS DA PLANILHA (ÚNICO FIELDSET) -->
            <fieldset>
                <legend>Dados Copiados da Planilha</legend>

                <div style="padding: 8px; border: 1px dashed #d9d9d9; border-radius: 4px; margin-bottom: 6px; background: #fff;">
                    <label style="display:block; margin-bottom: 5px; color:#00509e; font-size: 12px;">1) Identificação, Datas, Principal e FGTS</label>
                    <div class="row">
                        <div class="col" style="flex: 0 0 140px;">
                            <label>Id da Planilha</label>
                            <input type="text" id="val-id" class="coleta-input" placeholder="Id #XXXX">
                        </div>
                        <div class="col" style="flex: 0 0 140px;">
                            <label>Data da Atualização</label>
                            <input type="text" id="val-data" class="coleta-input" placeholder="DD/MM/AAAA">
                        </div>
                        <div class="col" style="flex: 1;">
                            <label>Crédito Principal (ou Total)</label>
                            <input type="text" id="val-credito" class="coleta-input" placeholder="R$ Crédito Principal">
                        </div>
                    </div>
                    <div class="row" style="align-items: center; gap: 10px; margin-bottom: 5px;">
                        <div class="col" style="flex: 0 0 auto;">
                            <label><input type="checkbox" id="calc-fgts" checked> FGTS apurado separado?</label>
                        </div>
                        <div class="col" id="fgts-radios" style="flex: 0 0 auto; display: flex; gap: 12px;">
                            <label style="margin: 0;"><input type="radio" name="fgts-tipo" value="devido" checked> Devido</label>
                            <label style="margin: 0;"><input type="radio" name="fgts-tipo" value="depositado"> Depositado</label>
                        </div>
                    </div>
                    <div class="row" id="row-fgts-valor">
                        <div class="col" id="col-fgts-val" style="flex: 0 0 auto;">
                            <label style="font-size: 11px; margin-bottom: 2px;">Valor FGTS Separado</label>
                            <input type="text" id="val-fgts" class="coleta-input" placeholder="R$ FGTS" style="width: 140px;">
                        </div>
                    </div>
                    <div class="row hidden" id="col-juros-val">
                        <div class="col">
                            <label>Juros</label>
                            <input type="text" id="val-juros" placeholder="R$ Juros">
                        </div>
                        <div class="col">
                            <label>Data de Ingresso</label>
                            <input type="date" id="data-ingresso">
                        </div>
                    </div>
                </div>

                <div style="padding: 8px; border: 1px dashed #d9d9d9; border-radius: 4px; margin-bottom: 6px; background: #fff;">
                    <label style="display:block; margin-bottom: 5px; color:#00509e; font-size: 12px;">2) INSS (Autor e Reclamada) e IR</label>
                    <div class="row" style="margin-bottom: 0;">
                        <div class="col">
                            <label>INSS - Desconto (Reclamante)</label>
                            <input type="text" id="val-inss-rec" class="coleta-input" placeholder="R$ INSS Reclamante (Desconto)">
                        </div>
                        <div class="col">
                            <label>INSS - Total da Empresa (Reclamada)</label>
                            <input type="text" id="val-inss-total" class="coleta-input" placeholder="R$ INSS Total / Reclamada">
                        </div>
                    </div>
                    <div class="row" style="margin-top: 5px;">
                        <div class="col">
                            <label><input type="checkbox" id="ignorar-inss"> Não há INSS</label>
                            <small style="color: #666; display: block;">*INSS Reclamada = Subtração automática se PJeCalc marcado.</small>
                        </div>
                        <div class="col">
                            <label>Imposto de Renda</label>
                            <select id="irpf-tipo" style="margin-bottom: 5px; width: 100%;">
                                <option value="isento" selected>Não há</option>
                                <option value="informar">Informar Valores</option>
                            </select>
                            <div id="irpf-campos" class="hidden" style="display:flex; gap: 5px;">
                                <input type="text" id="val-irpf-base" placeholder="Base (R$)" style="flex:1;">
                                <input type="text" id="val-irpf-meses" placeholder="Meses" style="flex:1;">
                            </div>
                        </div>
                    </div>
                </div>

                <div style="padding: 8px; border: 1px dashed #d9d9d9; border-radius: 4px; margin-bottom: 6px; background: #fff;">
                    <label style="display:block; margin-bottom: 5px; color:#00509e; font-size: 12px;">3) Honorários Advocatícios</label>
                    <div class="row" style="margin-bottom: 0; align-items: flex-start;">

                        <!-- Coluna AUTOR -->
                        <div class="col" style="flex: 1; min-width: 160px;">
                            <label>Honorários Adv Autor</label>
                            <input type="text" id="val-hon-autor" class="coleta-input highlight" placeholder="R$ Honorários Autor">
                            <label style="font-size: 11px; margin-top: 4px; display: block;">
                                <input type="checkbox" id="ignorar-hon-autor"> Não há honorários autor
                            </label>
                        </div>

                        <!-- Coluna RÉU -->
                        <div class="col" style="flex: 1; min-width: 160px;">
                            <label>
                                <input type="checkbox" id="chk-hon-reu" checked style="margin-right: 5px;">Não há Honorários Adv Réu
                            </label>
                            <div id="hon-reu-campos" class="hidden" style="margin-top: 6px;">
                                <label style="font-size: 11px; display: block; margin-bottom: 6px;">
                                    <input type="checkbox" id="chk-hon-reu-suspensiva" checked> Condição Suspensiva
                                </label>
                                <div style="display: flex; gap: 8px; flex-direction: column; margin-bottom: 6px;">
                                    <label style="font-size: 11px;">
                                        <input type="radio" name="rad-hon-reu-tipo" value="percentual" checked> Percentual
                                    </label>
                                    <label style="font-size: 11px;">
                                        <input type="radio" name="rad-hon-reu-tipo" value="valor"> Valor Informado
                                    </label>
                                </div>
                                <div id="hon-reu-perc-campo" style="margin-bottom: 4px;">
                                    <input type="text" id="val-hon-reu-perc" class="coleta-input" value="5%" placeholder="%" style="width: 80px;">
                                </div>
                                <div id="hon-reu-valor-campo" class="hidden" style="margin-bottom: 4px;">
                                    <input type="text" id="val-hon-reu" class="coleta-input" placeholder="R$ Honorários Réu" style="width: 140px;">
                                </div>
                            </div>
                        </div>

                    </div>
                </div>

                <div style="padding: 8px; border: 1px dashed #d9d9d9; border-radius: 4px; background: #fff;">
                    <label style="display:block; margin-bottom: 5px; color:#00509e; font-size: 12px;">4) Custas</label>
                    <div class="row" style="margin-bottom: 5px;">
                        <div class="col" style="flex: 0 0 140px;">
                            <label>Valor</label>
                            <input type="text" id="val-custas" class="coleta-input" placeholder="R$ Custas">
                        </div>
                        <div class="col" style="flex: 0 0 140px;">
                            <label>Status</label>
                            <select id="custas-status">
                                <option value="devidas" selected>Devidas</option>
                                <option value="pagas">Já Pagas</option>
                            </select>
                        </div>
                        <div class="col" style="flex: 0 0 140px;">
                            <label>Origem</label>
                            <select id="custas-origem">
                                <option value="sentenca" selected>Sentença</option>
                                <option value="acordao">Acórdão</option>
                            </select>
                        </div>
                    </div>
                    <div class="row" style="margin-bottom: 0;">
                        <div class="col" id="custas-data-col" style="flex: 1;">
                            <label>Data Custas <small style="color: #666;">(vazio = mesma planilha)</small></label>
                            <input type="text" id="custas-data-origem" class="coleta-input" placeholder="DD/MM/AAAA">
                        </div>
                        <div class="col hidden" id="custas-acordao-col" style="flex: 1;">
                            <label>Acórdão</label>
                            <select id="custas-acordao-select">
                                <option value="">Selecione o acórdão</option>
                            </select>
                        </div>
                    </div>
                </div>
            </fieldset>

            <!-- SEÇÃO 6: RESPONSABILIDADE -->
            <fieldset>
                <legend>Responsabilidade</legend>
                <div class="row">
                    <select id="resp-tipo">
                        <option value="unica">Reclamada Única</option>
                        <option value="solidarias">Devedoras Solidárias</option>
                        <option value="subsidiarias" selected>Devedoras Subsidiárias</option>
                    </select>
                </div>
                <div id="resp-sub-opcoes" class="row">
                    <label><input type="checkbox" id="resp-integral" checked> Responde pelo período total</label>
                    <label style="margin-left: 15px;"><input type="checkbox" id="resp-diversos"> Períodos Diversos (Gera estrutura para preencher)</label>
                </div>
            </fieldset>

            <!-- SEÇÃO 6.1: PERÍODOS DIVERSOS (Dinâmico) -->
            <fieldset id="resp-diversos-fieldset" class="hidden">
                <legend>Períodos Diversos - Cálculos Separados por Reclamada</legend>
                <div class="row" style="margin-bottom: 15px;">
                    <div class="col">
                        <label style="font-weight: bold;">Devedora Principal</label>
                        <select id="resp-devedora-principal" style="width: 100%; padding: 8px;">
                            <option value="">Selecione a devedora principal...</option>
                        </select>
                        <small style="color: #666; display: block; margin-top: 5px;">*Padrão: primeira reclamada</small>
                    </div>
                </div>
                <div class="row" style="margin-bottom: 15px; font-size: 13px; color: #555;">
                    <label>Preencha período, planilha e tipo (Principal/Subsidiária) para cada reclamada com responsabilidade diversa:</label>
                </div>
                <div id="resp-diversos-container"></div>
                <button type="button" class="btn-action" id="btn-adicionar-periodo" style="margin-top: 10px;">+ Adicionar Período Diverso</button>
            </fieldset>

            <!-- Links de Sentença e Acórdão -->
            <fieldset style="border: none; padding: 8px 0; margin: 8px 0;">
                <div id="link-sentenca-acordao-container"></div>
            </fieldset>

            <!-- SEÇÃO 7B: HONORÁRIOS PERICIAIS (auto-esconde se não detectar perito) -->
            <fieldset id="fieldset-pericia-conh" class="hidden">
                <legend>Honorários Periciais <span id="link-sentenca-container"></span></legend>
                <div class="row">
                    <div class="col">
                        <label><input type="checkbox" id="chk-perito-conh"> Honorários Periciais (Conhecimento)</label>
                        <div id="perito-conh-campos" class="hidden" style="margin-top: 5px; display: flex; gap: 10px;">
                            <input type="text" id="val-perito-nome" placeholder="Nome do Perito">
                            <select id="perito-tipo-pag">
                                <option value="reclamada" selected>Pago pela Reclamada (Valor)</option>
                                <option value="trt">Pago pelo TRT (Autor Sucumbente)</option>
                            </select>
                            <input type="text" id="val-perito-valor" placeholder="R$ Valor ou ID TRT">
                            <input type="text" id="val-perito-data" placeholder="Data da Sentença">
                        </div>
                    </div>
                </div>
                <div class="row hidden" id="row-perito-contabil">
                    <div class="col">
                        <label>Honorários Periciais (Contábil - Rogério)</label>
                        <div id="perito-contabil-campos" style="margin-top: 5px; display: flex; gap: 10px;">
                            <input type="text" id="val-perito-contabil-valor" placeholder="Valor dos honorários contábeis">
                        </div>
                    </div>
                </div>
            </fieldset>

            <!-- Custas já foram movidas para o card 4 acima -->

            <!-- SEÇÃO 8: DEPÓSITOS -->
            <fieldset id="fieldset-deposito">
                <legend>Depósitos</legend>
                <div class="row">
                    <label id="label-chk-deposito"><input type="checkbox" id="chk-deposito"> Há Depósito Recursal?</label>
                    <label style="margin-left: 20px;"><input type="checkbox" id="chk-pag-antecipado"> Pagamento Antecipado</label>
                </div>

                <!-- CONTAINER DE DEPÓSITOS RECURSAIS (dinâmico) -->
                <div id="deposito-campos" class="hidden">
                    <div id="depositos-container"></div>
                    <button type="button" id="btn-add-deposito" class="btn-action" style="margin-top: 8px; padding: 4px 12px; font-size: 11px;">+ Adicionar Depósito Recursal</button>
                </div>

                <!-- CONTAINER DE PAGAMENTOS ANTECIPADOS (dinâmico) -->
                <div id="pag-antecipado-campos" class="hidden">
                    <div id="pagamentos-container"></div>
                    <button type="button" id="btn-add-pagamento" class="btn-action" style="margin-top: 8px; padding: 4px 12px; font-size: 11px;">+ Adicionar Pagamento</button>
                </div>
            </fieldset>

            <!-- SEÇÃO 9: INTIMAÇÕES -->
            <fieldset id="fieldset-intimacoes">
                <legend>Intimações</legend>
                <div id="lista-intimacoes-container">
                    <small style="color:#666; font-style:italic;">Aguardando leitura das partes...</small>
                </div>
                <div id="links-editais-container" class="hidden" style="margin-top: 10px; border-top: 1px dashed #ccc; padding-top: 10px;">
                    <label style="font-weight:bold; font-size:12px; color:#5b21b6;">Editais Detectados na Timeline:</label>
                    <div id="links-editais-lista"></div>
                </div>
            </fieldset>

            <button class="btn-action btn-gravar" id="btn-gravar">GRAVAR DECISÃO (Copiar p/ PJe)</button>
        </div>
    </div>
    `;
        // Check robusto: Remover overlay antigo se existir (previne duplicação)
        const existingOverlay = document.getElementById('homologacao-overlay');
        if (existingOverlay) {
            dbg('Overlay já existe, removendo versão antiga antes de recriar');
            existingOverlay.remove();
        }

        // Inserir HTML limpo
        document.body.insertAdjacentHTML('beforeend', htmlModal);
        dbg('Overlay HTML inserido no DOM.');

        // Toggle colapso/expansão do card de resumo
        const resumoToggle = document.getElementById('resumo-toggle');
        const resumoBody = document.getElementById('resumo-body');
        const resumoSeta = document.getElementById('resumo-seta');
        if (resumoToggle && resumoBody) {
            resumoToggle.addEventListener('click', () => {
                const aberto = resumoBody.style.display !== 'none';
                resumoBody.style.display = aberto ? 'none' : 'block';
                if (resumoSeta) resumoSeta.textContent = aberto ? '▶' : '▼';
            });
        }

        if (!document.getElementById('homologacao-overlay')) {
            err('Falha apos insercao: homologacao-overlay nao encontrado.');
            return;
        }

        // ==========================================
        // Bind no input file (FASE 4 do MD)
        // ==========================================
        const fileInput = document.getElementById('input-planilha-pdf');
        if (fileInput && !fileInput._hcalcBound) {
            fileInput._hcalcBound = true;
            fileInput.addEventListener('change', async (e) => {
                const file = e.target.files[0];
                if (!file) return;

                try {
                    await carregarPDFJSSeNecessario();
                    const dados = await processarPlanilhaPDF(file);
                    // Atualiza estado
                    window.hcalcState.planilhaExtracaoData = dados;
                    window.hcalcState.planilhaCarregada = !!dados && !!dados.sucesso;

                    // Atualizar card/resumo
                    if (window.hcalcAtualizarResumoPlanilha) {
                        window.hcalcAtualizarResumoPlanilha(dados);
                    }
                } catch (e2) {
                    err('Erro ao processar planilha PDF:', e2);
                    window.hcalcState.planilhaCarregada = false;
                }
            });
        }

        // ==========================================
        // 3. LÓGICA DE INTERFACE E EVENTOS (TOGGLES)
        // ==========================================
        const $ = (id) => document.getElementById(id);
        dbg('Binding de eventos iniciado.');

        // ==========================================
        // FASE 1: Sistema de Fases do Botão
        // ==========================================
        $('btn-abrir-homologacao').onclick = async () => {
            const btn = $('btn-abrir-homologacao');
            const inputFile = $('input-planilha-pdf');

            // FASE 1: Carregar Planilha (estado inicial)
            if (!window.hcalcState.planilhaCarregada) {
                dbg('FASE 1: Clique em Carregar Planilha');
                inputFile.click(); // Abre file picker
                return;
            }

            // FASE 3: Gerar Homologação (após planilha carregada)
            dbg('FASE 3: Clique em Gerar Homologação');
            try {
                // Executar prep.js: varredura + extração da sentença + AJ-JT
                const peritosConh = window.hcalcPeritosConhecimentoDetectados || [];
                const partesData = window.hcalcPartesData || {};
                const prep = await executarPrep(partesData, peritosConh);

                // CORREÇÃO 1: Salvar globalmente para preencherDepositosAutomaticos
                window.hcalcLastPrepResult = prep;

                // Retrocompat: manter window.hcalcTimelineData para construirSecaoIntimacoes
                window.hcalcTimelineData = {
                    sentenca: prep.sentenca.data ? { data: prep.sentenca.data, href: prep.sentenca.href } : null,
                    acordaos: prep.acordaos,
                    editais: prep.editais
                };

                // Strikethrough no label de depósito recursal se não há acórdão
                const labelDeposito = $('label-chk-deposito');
                if (labelDeposito) {
                    labelDeposito.style.textDecoration = prep.acordaos.length === 0 ? 'line-through' : 'none';
                }

                // Link sentença (info inline no card de custas)
                const linkSentencaContainer = $('link-sentenca-container');
                if (linkSentencaContainer) {
                    linkSentencaContainer.innerHTML = '';
                    if (prep.sentenca.data) {
                        const info = [];
                        if (prep.sentenca.custas) info.push(`Custas: R$${prep.sentenca.custas}`);
                        if (prep.sentenca.responsabilidade) info.push(`Resp: ${prep.sentenca.responsabilidade}`);

                        // Honorários periciais: prioriza AJ-JT, só mostra sentença se não tiver AJ-JT
                        if (prep.pericia.peritosComAjJt.length > 0) {
                            info.push(`Hon.Periciais: ${prep.pericia.peritosComAjJt.length} AJ-JT detectado(s)`);
                        } else if (prep.sentenca.honorariosPericiais.length > 0) {
                            info.push(`Hon.Periciais: ${prep.sentenca.honorariosPericiais.map(h => 'R$' + h.valor + (h.trt ? ' (TRT)' : '')).join(', ')}`);
                        }

                        linkSentencaContainer.innerHTML = `<span style="font-size:12px; color:#16a34a;">✔ Sentença: ${prep.sentenca.data}${info.length ? ' | ' + info.join(' | ') : ''}</span>`;
                    }
                }

                // Links clicáveis de Sentença e Acórdão (fieldset separado)
                const linkSentencaAcordaoContainer = $('link-sentenca-acordao-container');
                if (linkSentencaAcordaoContainer) {
                    linkSentencaAcordaoContainer.innerHTML = '';

                    // Link da Sentença (foca na timeline)
                    if (prep.sentenca.href) {
                        const sentencaLink = document.createElement('a');
                        sentencaLink.href = '#';
                        sentencaLink.innerHTML = `<i class="fas fa-crosshairs"></i> Sentença${prep.sentenca.data ? ' - ' + prep.sentenca.data : ''}`;
                        sentencaLink.style.cssText = 'display:block; color:#16a34a; font-size:12px; margin-bottom:5px; text-decoration:none; font-weight:600; cursor:pointer;';
                        sentencaLink.addEventListener('click', (e) => {
                            e.preventDefault();
                            destacarElementoNaTimeline(prep.sentenca.href);
                        });
                        linkSentencaAcordaoContainer.appendChild(sentencaLink);
                    }

                    // Links de Acórdãos
                    if (prep.acordaos.length > 0) {
                        prep.acordaos.forEach((acordao, i) => {
                            if (acordao.href) {
                                const lbl = prep.acordaos.length > 1 ? `Acórdão ${i + 1}` : `Acórdão`;
                                const a = document.createElement('a');
                                a.href = '#';
                                a.innerHTML = `<i class="fas fa-crosshairs"></i> ${lbl}${acordao.data ? ' - ' + acordao.data : ''}`;
                                a.style.cssText = "display:block; color:#00509e; font-size:12px; margin-top:5px; text-decoration:none; cursor:pointer;";
                                a.addEventListener('click', (e) => {
                                    e.preventDefault();
                                    destacarElementoNaTimeline(acordao.href);
                                });
                                linkSentencaAcordaoContainer.appendChild(a);
                            }
                        });

                        // RECURSOS COM ANEXOS (integrado de rec.js v1.0)
                        if (prep.depositos.length > 0) {
                            const recDiv = document.createElement('div');
                            recDiv.style.cssText = 'margin-top:8px; padding:6px; background:#fffde7; border:1px solid #fbbf24; border-radius:4px;';
                            recDiv.innerHTML = `<strong style="font-size:11px;color:#92400e">📎 Recursos das Reclamadas (${prep.depositos.length})</strong>`;

                            prep.depositos.forEach((dep, depIdx) => {
                                const card = document.createElement('div');
                                card.className = 'rec-recurso-card';
                                card.dataset.href = dep.href || '';

                                const corBadge = { 'Depósito': '#10b981', 'Garantia': '#f59e0b', 'Custas': '#ef4444', 'Anexo': '#6b7280' };

                                let anexosHtml = '';
                                if (dep.anexos && dep.anexos.length > 0) {
                                    anexosHtml = `<div class="rec-anexos-lista">` +
                                        dep.anexos.map((ax, axIdx) =>
                                            `<div class="rec-anexo-item" data-dep-idx="${depIdx}" data-ax-idx="${axIdx}">
                                            <span class="rec-anexo-badge" style="background:${corBadge[ax.tipo] || '#6b7280'}">${ax.tipo}</span>
                                            <code class="rec-anexo-id">${ax.id || 'sem id'}</code>
                                            <span style="font-size:10px;color:#6b7280;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:120px" title="${ax.texto}">${ax.texto.substring(0, 40)}</span>
                                        </div>`
                                        ).join('') +
                                        `</div>`;
                                }

                                card.innerHTML = `
                                <div style="display:flex;align-items:center;gap:6px;margin-bottom:3px">
                                    <span class="rec-tipo-badge">${dep.tipo || 'RO'}</span>
                                    <span style="font-size:11px;color:#92400e;font-weight:600;flex:1">${dep.depositante || 'Parte não identificada'}</span>
                                    <span style="font-size:10px;color:#6b7280">${dep.data || 'sem data'}</span>
                                    ${dep.anexos && dep.anexos.length > 0 ? `<span class="rec-seta-toggle">▶ ${dep.anexos.length} anexo${dep.anexos.length > 1 ? 's' : ''}</span>` : ''}
                                </div>
                                ${anexosHtml}`;

                                card.addEventListener('click', e => {
                                    const axItem = e.target.closest('.rec-anexo-item');
                                    if (axItem) {
                                        e.stopPropagation();
                                        const axIdx = parseInt(axItem.dataset.axIdx, 10);
                                        const ax = dep.anexos[axIdx];
                                        if (!ax) return;

                                        // 1. Destacar o recurso na timeline
                                        if (dep.href) try { destacarElementoNaTimeline(dep.href); } catch (e2) { console.error('[hcalc]', e2); }

                                        // 2. Re-encontrar e clicar no anexo (evita referência stale do Angular)
                                        setTimeout(async () => {
                                            try {
                                                const item = encontrarItemTimeline(dep.href);
                                                if (item) {
                                                    await expandirAnexos(item);
                                                    const links = item.querySelectorAll('a.tl-documento[id^="anexo_"]');
                                                    let alvo = null;
                                                    if (ax.id) {
                                                        alvo = Array.from(links).find(l => l.textContent.includes(ax.id));
                                                    }
                                                    alvo = alvo || links[axIdx] || links[0];
                                                    if (alvo) alvo.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
                                                } else if (ax.elemento && ax.elemento.isConnected) {
                                                    ax.elemento.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
                                                }
                                            } catch (e3) { console.error('[hcalc] Erro ao clicar no anexo:', e3); }
                                        }, 600);
                                        return;
                                    }

                                    card.classList.toggle('expandido');
                                    const seta = card.querySelector('.rec-seta-toggle');
                                    if (seta) seta.textContent = card.classList.contains('expandido')
                                        ? `\u25bc ${dep.anexos.length} anexo${dep.anexos.length > 1 ? 's' : ''}`
                                        : `\u25b6 ${dep.anexos.length} anexo${dep.anexos.length > 1 ? 's' : ''}`;
                                    if (dep.href) try { destacarElementoNaTimeline(dep.href); } catch (e2) { console.error('[hcalc]', e2); }
                                });

                                recDiv.appendChild(card);
                            });

                            linkSentencaAcordaoContainer.appendChild(recDiv);
                        }
                    } else {
                        // Aviso quando não há acórdão
                        const avisoDiv = document.createElement('div');
                        avisoDiv.style.cssText = 'margin-top:8px; padding:8px; background:#fef2f2; border:1px solid #ef4444; border-radius:4px;';
                        avisoDiv.innerHTML = `<span style="font-size:12px; color:#dc2626; font-weight:600;">⚠ Não há Acórdão</span>`;
                        linkSentencaAcordaoContainer.appendChild(avisoDiv);
                    }
                }

                // Preencher custas automaticamente - PRIORIZA PLANILHA
                if (window.hcalcState.planilhaExtracaoData?.custas && $('val-custas')) {
                    $('val-custas').value = window.hcalcState.planilhaExtracaoData.custas;
                    // FIX: sem acórdão → custas são da sentença → data = sentença
                    const semAcordao = prep.acordaos.length === 0;
                    if (semAcordao && prep.sentenca.data && $('custas-data-origem')) {
                        $('custas-data-origem').value = prep.sentenca.data;
                    } else if (window.hcalcState.planilhaExtracaoData.dataAtualizacao && $('custas-data-origem')) {
                        $('custas-data-origem').value = window.hcalcState.planilhaExtracaoData.dataAtualizacao;
                    }
                } else if (prep.sentenca.custas && $('val-custas')) {
                    $('val-custas').value = prep.sentenca.custas;
                    // Data das custas = data da sentença (apenas se não há planilha)
                    if (prep.sentenca.data && $('custas-data-origem')) {
                        $('custas-data-origem').value = prep.sentenca.data;
                    }
                }

                // Se tem recurso da reclamada → custas já pagas
                if (prep.recursosPassivo && prep.recursosPassivo.length > 0) {
                    const custasStatusEl = $('custas-status');
                    if (custasStatusEl) {
                        custasStatusEl.value = 'pagas';
                        console.log('[hcalc] Recurso da reclamada detectado! Custas marcadas como pagas.');
                    }
                }

                // Depósito recursal: visível se tem acórdãos
                const fieldsetDeposito = $('fieldset-deposito');
                if (prep.acordaos.length === 0) {
                    if (fieldsetDeposito) fieldsetDeposito.classList.add('hidden');
                } else {
                    if (fieldsetDeposito) fieldsetDeposito.classList.remove('hidden');
                }

                // Povoar select de acórdãos se existirem
                const custasAcordaoSelect = $('custas-acordao-select');
                if (custasAcordaoSelect && prep.acordaos.length > 0) {
                    custasAcordaoSelect.innerHTML = '<option value="">Selecione o acórdão</option>';
                    prep.acordaos.forEach((acordao, i) => {
                        const opt = document.createElement('option');
                        opt.value = i;
                        opt.textContent = `Acórdão ${i + 1}${acordao.data ? ' - ' + acordao.data : ''}`;
                        opt.dataset.data = acordao.data || '';
                        opt.dataset.id = acordao.id || '';
                        custasAcordaoSelect.appendChild(opt);
                    });
                }

                // Editais
                const editaisContainer = $('links-editais-container');
                const editaisLista = $('links-editais-lista');
                if (editaisContainer && editaisLista) {
                    editaisLista.innerHTML = '';
                    if (prep.editais.length > 0) {
                        editaisContainer.classList.remove('hidden');
                        prep.editais.forEach((edital, i) => {
                            if (edital.href) {
                                const btn = document.createElement('a');
                                btn.href = edital.href;
                                btn.target = "_blank";
                                btn.innerHTML = `<i class="fas fa-external-link-alt"></i> Edital ${i + 1}`;
                                btn.style.cssText = "display:inline-block; margin-right:10px; color:#00509e; font-size:12px; text-decoration:none;";
                                editaisLista.appendChild(btn);
                            }
                        });
                    } else {
                        editaisContainer.classList.add('hidden');
                    }
                }

                // ==========================================
                // REGRAS AUTO-PREENCHIMENTO (prep sobrepõe defaults)
                // ==========================================

                // REGRA 1: Depósito recursal — disparar evento onChange para unificar fluxo
                // CORREÇÃO 2: Usar dispatchEvent em vez de manipulação direta do DOM
                if (prep.depositos.length > 0) {
                    console.log('[INICIALIZAÇÃO] Detectados', prep.depositos.length, 'recursos com depósito/garantia');

                    const chkDep = $('chk-deposito');
                    if (chkDep) {
                        chkDep.checked = true;
                        // Disparar onChange sintético — aciona visibilidade E preencherDepositosAutomaticos
                        // de forma unificada, eliminando dessincronização
                        chkDep.dispatchEvent(new Event('change', { bubbles: true }));
                        console.log('[INICIALIZAÇÃO] Evento change disparado');
                    }
                }

                // REGRA 2: Perito conhecimento + TRT / AJ-JT match
                const peritoTipoEl = $('perito-tipo-pag');
                const peritoValorEl = $('val-perito-valor');
                const peritoDataEl = $('val-perito-data');
                if (prep.pericia.peritosComAjJt.length > 0) {
                    // Perito casou com AJ-JT — pago pelo TRT
                    const match = prep.pericia.peritosComAjJt[0];
                    if (peritoTipoEl) peritoTipoEl.value = 'trt';
                    if (peritoValorEl) peritoValorEl.value = match.idAjJt || '';
                } else if (prep.sentenca.honorariosPericiais.length > 0) {
                    // Honorários periciais na sentença
                    const hon = prep.sentenca.honorariosPericiais[0];
                    if (hon.trt && peritoTipoEl) {
                        peritoTipoEl.value = 'trt';
                    }
                    // Sempre preencher valor se detectado
                    if (peritoValorEl && !peritoValorEl.value) {
                        peritoValorEl.value = 'R$' + hon.valor;
                    }
                }
                // Data da sentença no campo de data do perito
                if (prep.sentenca.data && peritoDataEl && !peritoDataEl.value) {
                    peritoDataEl.value = prep.sentenca.data;
                }

                // REGRA 3 e 4: Responsabilidade (subsidiária / solidária)
                const respTipoEl = $('resp-tipo');
                const respSubOpcoes = $('resp-sub-opcoes');
                const passivo = window.hcalcPartesData?.passivo || [];
                if (prep.sentenca.responsabilidade && respTipoEl) {
                    if (prep.sentenca.responsabilidade === 'subsidiaria') {
                        respTipoEl.value = 'subsidiarias';
                        if (respSubOpcoes) respSubOpcoes.classList.remove('hidden');
                    } else if (prep.sentenca.responsabilidade === 'solidaria') {
                        respTipoEl.value = 'solidarias';
                        if (respSubOpcoes) respSubOpcoes.classList.add('hidden');
                    }
                } else if (passivo.length <= 1 && respTipoEl) {
                    respTipoEl.value = 'unica';
                    if (respSubOpcoes) respSubOpcoes.classList.add('hidden');
                }

                // REGRA 5: Custas
                // Sempre padrão = sentença (usuário pode mudar para acórdão se necessário)
                const custasStatusEl = $('custas-status');
                const custasOrigemEl = $('custas-origem');
                if (prep.sentenca.custas) {
                    // ATENÇÃO: Não sobrepõe se planilha já preencheu custas
                    if ($('val-custas') && !window.hcalcState.planilhaExtracaoData?.custas) {
                        $('val-custas').value = prep.sentenca.custas;
                    }
                    // Sempre usa sentença como padrão
                    if (custasStatusEl) custasStatusEl.value = 'devidas';
                    if (custasOrigemEl) custasOrigemEl.value = 'sentenca';
                    // ATENÇÃO: Não sobrepõe data se planilha já preencheu
                    if ($('custas-data-origem') && prep.sentenca.data && !window.hcalcState.planilhaExtracaoData?.custas) {
                        $('custas-data-origem').value = prep.sentenca.data;
                    }
                }

                // REGRA 6: hsusp → Honorários Adv. Réu com condição suspensiva
                const chkHonReu = $('chk-hon-reu');
                const honReuCampos = $('hon-reu-campos');
                if (prep.sentenca.hsusp) {
                    // Lógica invertida: desmarcar "Não há" para mostrar campos
                    if (chkHonReu) chkHonReu.checked = false;
                    if (honReuCampos) honReuCampos.classList.remove('hidden');

                    const radSusp = document.querySelector('input[name="rad-hon-reu"][value="suspensiva"]');
                    if (radSusp) radSusp.checked = true;
                } else {
                    // Estado padrão: checkbox marcado, campos ocultos
                    if (chkHonReu) chkHonReu.checked = true;
                    if (honReuCampos) honReuCampos.classList.add('hidden');
                }

                // ==========================================
                // PREENCHER COM DADOS DA PLANILHA (PRIORIDADE)
                // ==========================================
                if (window.hcalcState.planilhaExtracaoData) {
                    const dados = window.hcalcState.planilhaExtracaoData;

                    if (dados.idPlanilha && $('val-id')) $('val-id').value = dados.idPlanilha;
                    if (dados.verbas && $('val-credito')) $('val-credito').value = dados.verbas;

                    // FGTS: preencher valor + ajustar checkbox + marcar status depositado conforme extração
                    if ($('val-fgts') && $('calc-fgts')) {
                        const temFgts = dados.fgts && dados.fgts !== '0,00' && dados.fgts !== '0';

                        if (temFgts) {
                            $('val-fgts').value = dados.fgts;
                            $('calc-fgts').checked = true;

                            // Marcar radio button correto (depositado ou devido)
                            if (dados.fgtsDepositado) {
                                const radDepositado = document.querySelector('input[name="fgts-tipo"][value="depositado"]');
                                if (radDepositado) radDepositado.checked = true;
                            } else {
                                const radDevido = document.querySelector('input[name="fgts-tipo"][value="devido"]');
                                if (radDevido) radDevido.checked = true;
                            }
                        } else {
                            // Sem FGTS detectado → desmarcar checkbox (que vem marcado por padrão)
                            $('calc-fgts').checked = false;
                        }
                        $('calc-fgts').dispatchEvent(new Event('change', { bubbles: true }));
                    }

                    // INSS: preencher valores + ajustar checkbox se não há nenhum
                    if (dados.inssTotal && $('val-inss-total')) $('val-inss-total').value = dados.inssTotal;
                    if (dados.inssAutor && $('val-inss-rec')) $('val-inss-rec').value = dados.inssAutor;

                    // Verificar se não há INSS nenhum
                    const semInssTotal = !dados.inssTotal || dados.inssTotal === '0,00' || dados.inssTotal === '0';
                    const semInssAutor = !dados.inssAutor || dados.inssAutor === '0,00' || dados.inssAutor === '0';

                    if (semInssTotal && semInssAutor && $('ignorar-inss')) {
                        $('ignorar-inss').checked = true;
                        $('ignorar-inss').dispatchEvent(new Event('change', { bubbles: true }));
                    }

                    // Custas: valor e data da planilha (prevalece sobre sentença)
                    if (dados.custas && $('val-custas')) {
                        $('val-custas').value = dados.custas;
                        // Data das custas = data de liquidação da planilha
                        if (dados.dataAtualizacao && $('custas-data-origem')) {
                            $('custas-data-origem').value = dados.dataAtualizacao;
                        }
                    }

                    if (dados.dataAtualizacao && $('val-data')) $('val-data').value = dados.dataAtualizacao;
                    if (dados.honAutor && $('val-hon-autor')) $('val-hon-autor').value = dados.honAutor;

                    // Aplicar IRPF se tributável
                    if (dados.irpfIsento === false) {
                        const irpfTipoEl = document.getElementById('irpf-tipo');
                        if (irpfTipoEl && irpfTipoEl.options.length > 1) {
                            irpfTipoEl.value = irpfTipoEl.options[1].value; // primeiro != 'isento'
                            irpfTipoEl.dispatchEvent(new Event('change', { bubbles: true }));
                        }
                    }

                    // Auto-selecionar origem como PJeCalc
                    if ($('calc-origem')) $('calc-origem').value = 'pjecalc';
                }

                // Mostrar card colapsado se planilha foi carregada (Fase 3)
                const resumoCard = $('resumo-extracao-card');
                if (resumoCard && window.hcalcState.planilhaExtracaoData) {
                    resumoCard.style.display = 'block';
                    // Preencher conteúdo do card
                    const dados = window.hcalcState.planilhaExtracaoData;
                    const resumoConteudo = $('resumo-conteudo');
                    if (resumoConteudo) {
                        resumoConteudo.innerHTML = `
                            <div class="resumo-item"><strong>ID:</strong> ${dados.idPlanilha || 'N/A'}</div>
                            <div class="resumo-item"><strong>Crédito:</strong> R$ ${dados.verbas || '0,00'}</div>
                            ${dados.fgts ? `<div class="resumo-item"><strong>FGTS:</strong> R$ ${dados.fgts}</div>` : ''}
                            <div class="resumo-item"><strong>INSS Total:</strong> R$ ${dados.inssTotal || '0,00'}</div>
                            <div class="resumo-item"><strong>INSS Rec:</strong> R$ ${dados.inssAutor || '0,00'}</div>
                            ${dados.custas ? `<div class="resumo-item"><strong>Custas:</strong> R$ ${dados.custas}</div>` : ''}
                            <div class="resumo-item"><strong>Data:</strong> ${dados.dataAtualizacao || 'N/A'}</div>
                            ${dados.periodoCalculo ? `<div class="resumo-item"><strong>Período:</strong> ${dados.periodoCalculo}</div>` : ''}
                            ${dados.irpfIsento === false ? `<div class="resumo-item" style="color:#b45309"><strong>IRPF:</strong> Tributável</div>` : ''}
                        `;
                    }
                }

                $('homologacao-overlay').style.display = 'flex';
                dbg('Overlay exibido para o usuario.');

                // Fallback: tentar clipboard se não tem ID da planilha
                if (!window.hcalcState.planilhaExtracaoData?.idPlanilha) {
                    try {
                        const txt = await navigator.clipboard.readText();
                        if (txt && txt.trim().length > 0) {
                            $('val-id').value = txt.trim();
                        }
                    } catch (e) { console.warn('Clipboard ignorado ou bloqueado', e); }
                }

                updateHighlight();
            } catch (e) {
                err('Erro no handler do botao Gerar Homologacao:', e);
                alert('Erro ao abrir assistente. Verifique o console (F12).');
                return;
            }
        };

        // ==========================================
        // FASE 2: Handler do Input File (Carregar Planilha)
        // ==========================================
        $('input-planilha-pdf').onchange = async (e) => {
            const file = e.target.files[0];
            if (!file) return;

            const btn = $('btn-abrir-homologacao');
            btn.textContent = '⏳ Processando...';
            btn.disabled = true;

            try {
                // Configurar PDF.js (primeira vez)
                const loaded = await carregarPDFJSSeNecessario();
                if (!loaded) {
                    throw new Error('PDF.js não disponível');
                }

                // Processar planilha
                const dados = await processarPlanilhaPDF(file);

                if (dados.sucesso) {
                    // Salvar no state
                    window.hcalcState.planilhaExtracaoData = dados;
                    window.hcalcState.planilhaCarregada = true;

                    // Atualizar dropdowns de linhas extras com a planilha principal recém-carregada
                    atualizarDropdownsPlanilhas();

                    // Atualizar botão
                    btn.textContent = '✓ Dados Extraídos';
                    btn.style.background = '#10b981';
                    btn.disabled = false;

                    dbg('Planilha extraída:', dados);

                    // Feedback visual momentâneo
                    setTimeout(() => {
                        btn.textContent = 'Gerar Homologação';
                        btn.style.background = '#00509e';
                    }, 2000);
                } else {
                    throw new Error(dados.erro || 'Erro desconhecido');
                }
            } catch (error) {
                console.error('[HCalc] Erro ao processar PDF:', error.message);
                alert('Erro ao processar PDF: ' + error.message);
                btn.textContent = '📄 Carregar Planilha';
                btn.disabled = false;
            }
        };

        // Handler do botão Reload (recarregar planilha)
        $('btn-reload-planilha').onclick = () => {
            const inputFile = $('input-planilha-pdf');
            inputFile.click();
        };

        $('btn-fechar').onclick = (e) => {
            e.preventDefault();  // Previne scroll indesejado
            const modal = $('homologacao-modal');
            const overlay = $('homologacao-overlay');
            modal.style.opacity = '1';
            modal.style.pointerEvents = 'all';
            modal.dataset.ghost = 'false';
            overlay.style.display = 'none';
            overlay.style.pointerEvents = 'none';
            // LIMPAR REFERÊNCIAS DOM: v1.8 usa método centralizado
            window.hcalcState.resetPrep();
            console.log('[hcalc] Estado resetado via hcalcState.resetPrep()');
        };
        $('homologacao-overlay').onclick = (e) => {
            if (e.target.id === 'homologacao-overlay') {
                // Não fecha — torna transparente e "fantasma"
                const modal = $('homologacao-modal');
                const overlay = $('homologacao-overlay');
                const isGhost = modal.dataset.ghost === 'true';
                if (isGhost) {
                    // Segundo clique fora: volta ao normal
                    modal.style.opacity = '1';
                    modal.style.pointerEvents = 'all';
                    overlay.style.pointerEvents = 'none';
                    modal.dataset.ghost = 'false';
                } else {
                    // Primeiro clique fora: vira fantasma
                    modal.style.opacity = '0.25';
                    modal.style.transition = 'opacity 0.3s';
                    modal.style.pointerEvents = 'none';
                    // Mantém overlay transparente para detectar clique de retorno
                    overlay.style.pointerEvents = 'all';
                    modal.dataset.ghost = 'true';
                }
            }
        };

        $('calc-origem').onchange = (e) => { $('col-pjc').classList.toggle('hidden', e.target.value !== 'pjecalc'); };
        $('calc-autor').onchange = (e) => { $('col-esclarecimentos').classList.toggle('hidden', e.target.value !== 'perito'); };
        $('calc-esclarecimentos').onchange = (e) => { $('calc-peca-perito').classList.toggle('hidden', !e.target.checked); };

        $('calc-fgts').onchange = (e) => {
            const isChecked = e.target.checked;
            $('fgts-radios').classList.toggle('hidden', !isChecked);
            $('row-fgts-valor').classList.toggle('hidden', !isChecked);
            updateHighlight();
        };
        $('calc-indice').onchange = (e) => { $('col-juros-val').classList.toggle('hidden', e.target.value !== 'tr'); };
        $('ignorar-hon-autor').onchange = (e) => { $('val-hon-autor').classList.toggle('hidden', e.target.checked); updateHighlight(); };
        $('ignorar-inss').onchange = (e) => {
            $('val-inss-rec').classList.toggle('hidden', e.target.checked);
            $('val-inss-total').classList.toggle('hidden', e.target.checked);
            updateHighlight();
        };
        $('irpf-tipo').onchange = (e) => { $('irpf-campos').classList.toggle('hidden', e.target.value === 'isento'); };

        $('resp-tipo').onchange = (e) => {
            $('resp-sub-opcoes').classList.toggle('hidden', e.target.value !== 'subsidiarias');

            // Atualizar visibilidade de checkboxes "Depositado pela Principal" em todos os depósitos
            window.hcalcState.depositosRecursais.forEach(d => {
                if (!d.removed) {
                    atualizarVisibilidadeDepositoPrincipal(d.idx);
                }
            });
        };

        // Lógica para Períodos Diversos
        $('resp-diversos').onchange = (e) => {
            const fieldset = $('resp-diversos-fieldset');
            const container = $('resp-diversos-container');
            const selectPrincipal = $('resp-devedora-principal');
            const reclamadas = window.hcalcPartesData?.passivo?.map(r => r.nome) || [];

            if (e.target.checked) {
                fieldset.classList.remove('hidden');

                // Preencher dropdown de Devedora Principal
                selectPrincipal.innerHTML = '';
                reclamadas.forEach((rec, idx) => {
                    const opt = document.createElement('option');
                    opt.value = rec;
                    opt.textContent = rec;
                    if (idx === 0) opt.selected = true; // Primeira como padrão
                    selectPrincipal.appendChild(opt);
                });

                // Verifique se já existe um formulário, senão crie um
                if (container.children.length === 0) {
                    adicionarLinhaPeridoDiverso();
                }
            } else {
                fieldset.classList.add('hidden');
                container.innerHTML = '';
            }
        };

        // Atualizar listas quando principal mudar
        $('resp-devedora-principal').onchange = (e) => {
            // Atualizar todos os dropdowns de reclamadas (centralizado)
            atualizarDropdownsReclamadas();
        };

        $('btn-adicionar-periodo').onclick = (e) => {
            e.preventDefault();
            adicionarLinhaPeridoDiverso();
        };

        // ─── PLANILHAS EXTRAS: REGISTRO E SINCRONIZAÇÃO ───────────────────────────
        function registrarPlanilhaDisponivel(id, label, dados) {
            if (!window.hcalcState.planilhasDisponiveis) window.hcalcState.planilhasDisponiveis = [];
            // Substitui entrada com mesmo id (re-upload da mesma linha)
            window.hcalcState.planilhasDisponiveis =
                window.hcalcState.planilhasDisponiveis.filter(p => p.id !== id);
            window.hcalcState.planilhasDisponiveis.push({ id, label, dados });
            atualizarDropdownsPlanilhas();
        }

        function atualizarDropdownsPlanilhas() {
            const extras = window.hcalcState.planilhasDisponiveis || [];
            document.querySelectorAll('.periodo-planilha-select').forEach(sel => {
                const currentVal = sel.value;
                // Remove todas as opções extras (mantém apenas 'principal')
                Array.from(sel.options).filter(o => o.value !== 'principal').forEach(o => o.remove());
                // Re-adiciona as disponíveis
                extras.forEach(p => {
                    const opt = document.createElement('option');
                    opt.value = p.id;
                    opt.textContent = `📊 ${p.label}`;
                    sel.appendChild(opt);
                });
                // Restaura seleção anterior se ainda válida
                if (Array.from(sel.options).some(o => o.value === currentVal)) sel.value = currentVal;
            });
        }

        function atualizarDropdownsReclamadas() {
            const todasReclamadas = window.hcalcPartesData?.passivo?.map(r => r.nome) || [];
            const principalIntegral = $('resp-devedora-principal')?.value || '';

            // Coletar todas as reclamadas já selecionadas em linhas existentes
            const jaUsadas = new Set([principalIntegral]);
            document.querySelectorAll('.periodo-reclamada').forEach(select => {
                if (select.value) jaUsadas.add(select.value);
            });

            // Atualizar cada dropdown
            document.querySelectorAll('.periodo-reclamada').forEach(select => {
                const valorAtual = select.value;

                // Reconstruir opções excluindo as já usadas (exceto a própria seleção)
                select.innerHTML = '<option value="">Selecione a reclamada...</option>';
                todasReclamadas.forEach(rec => {
                    if (!jaUsadas.has(rec) || rec === valorAtual) {
                        const opt = document.createElement('option');
                        opt.value = rec;
                        opt.textContent = rec;
                        if (rec === valorAtual) opt.selected = true;
                        select.appendChild(opt);
                    }
                });
            });
        }

        function adicionarLinhaPeridoDiverso() {
            const container = $('resp-diversos-container');
            const reclamadas = window.hcalcPartesData?.passivo?.map(r => r.nome) || [];
            const principalIntegral = $('resp-devedora-principal')?.value || '';
            const idx = container.children.length;
            const rowId = `periodo-diverso-${idx}`;
            const numeroDevedora = idx + 2; // #1 é a principal, então começa do #2

            const div = document.createElement('div');
            div.id = rowId;
            div.className = 'row';
            div.style.marginBottom = '15px';
            div.style.padding = '12px';
            div.style.backgroundColor = '#f5f5f5';
            div.style.borderRadius = '4px';

            // Filtrar: remover a principal integral E as já selecionadas em outras linhas
            const jaUsadas = new Set([principalIntegral]);
            document.querySelectorAll('.periodo-reclamada').forEach(select => {
                if (select.value) jaUsadas.add(select.value);
            });

            let selectOptions = '<option value="">Selecione a reclamada...</option>';
            reclamadas.forEach(rec => {
                if (!jaUsadas.has(rec)) {
                    selectOptions += `<option value="${rec}">${rec}</option>`;
                }
            });

            div.innerHTML = `
                <div style="margin-bottom: 10px;">
                    <label style="font-weight: bold;">Devedora #${numeroDevedora}</label>
                    <select class="periodo-reclamada" data-idx="${idx}" style="width: 100%; padding: 8px;">
                        ${selectOptions}
                    </select>
                </div>
                <div style="margin-bottom: 10px;">
                    <label style="font-weight: bold;">Tipo de Responsabilidade</label>
                    <div style="display: flex; gap: 15px;">
                        <label><input type="radio" name="periodo-tipo-${idx}" class="periodo-tipo" data-idx="${idx}" value="subsidiaria" checked> Subsidiária</label>
                        <label><input type="radio" name="periodo-tipo-${idx}" class="periodo-tipo" data-idx="${idx}" value="principal"> Principal (Período Parcial)</label>
                    </div>
                </div>
                <div style="display: flex; gap: 10px; margin-bottom: 10px;">
                    <div style="flex: 1;">
                        <label>Período (vazio = integral)</label>
                        <input type="text" class="periodo-periodo" data-idx="${idx}" placeholder="Deixe vazio para período integral" style="width: 100%; padding: 8px;">
                    </div>
                    <div style="flex: 1;">
                        <label>ID Cálculo Separado</label>
                        <input type="text" class="periodo-id" data-idx="${idx}" placeholder="ID #XXXX" style="width: 100%; padding: 8px;">
                    </div>
                </div>
                <div style="margin-bottom: 10px;">
                    <label style="font-weight: bold; font-size: 12px;">Planilha desta Devedora</label>
                    <div style="display: flex; gap: 8px; align-items: center; margin-top: 4px;">
                        <select class="periodo-planilha-select" data-idx="${idx}"
                                style="flex: 1; padding: 6px; font-size: 12px; border: 1px solid #ccc; border-radius: 4px;">
                            <option value="principal">📋 Mesma planilha principal</option>
                        </select>
                        <button type="button" class="btn-carregar-planilha-extra btn-action"
                                data-idx="${idx}"
                                style="font-size: 11px; padding: 6px 10px; white-space: nowrap; background: #7c3aed;">
                            📄 Carregar Nova
                        </button>
                        <input type="file" class="input-planilha-extra-pdf" data-idx="${idx}"
                               accept=".pdf" style="display: none;">
                    </div>
                </div>
                <div style="display: flex; gap: 10px; align-items: center; margin-bottom: 10px;">
                    <label><input type="checkbox" class="periodo-total" data-idx="${idx}"> Período Total</label>
                    <button type="button" class="btn-remover-periodo btn-action" data-idx="${idx}" data-row-id="${rowId}" style="padding: 8px; margin-left: auto; background: #d32f2f;">Remover</button>
                </div>
            `;
            container.appendChild(div);

            // ─── BOTÃO REMOVER: atualizar dropdowns após remoção ──────────────────────
            const btnRemover = div.querySelector(`.btn-remover-periodo[data-idx="${idx}"]`);
            btnRemover.onclick = () => {
                document.getElementById(rowId).remove();
                atualizarDropdownsReclamadas(); // Liberar reclamada de volta
            };

            // ─── AUTO-PREENCHER CAMPOS com planilha principal (padrão) ────────────────
            const periodoInput = div.querySelector(`.periodo-periodo[data-idx="${idx}"]`);
            const idInput = div.querySelector(`.periodo-id[data-idx="${idx}"]`);

            if (window.hcalcState.planilhaExtracaoData) {
                const pd = window.hcalcState.planilhaExtracaoData;
                if (periodoInput && pd.periodoCalculo) periodoInput.value = pd.periodoCalculo;
                if (idInput && pd.idPlanilha) idInput.value = pd.idPlanilha;
            }

            // ─── SELECT RECLAMADA: atualizar dropdowns quando selecionada ─────────────
            const selectReclamada = div.querySelector(`.periodo-reclamada[data-idx="${idx}"]`);
            selectReclamada.onchange = () => {
                // Atualizar todos os dropdowns para refletir nova seleção
                atualizarDropdownsReclamadas();
            };

            // ─── SELECT: trocar planilha ──────────────────────────────────────────────
            const selectPlanilha = div.querySelector(`.periodo-planilha-select[data-idx="${idx}"]`);

            // Injetar planilhas já disponíveis neste dropdown
            atualizarDropdownsPlanilhas();

            selectPlanilha.onchange = (e) => {
                const val = e.target.value;
                const pd = val === 'principal'
                    ? window.hcalcState.planilhaExtracaoData
                    : (window.hcalcState.planilhasDisponiveis || []).find(p => p.id === val)?.dados;
                if (!pd) return;
                if (pd.idPlanilha && idInput) idInput.value = pd.idPlanilha;
                if (pd.periodoCalculo && periodoInput) periodoInput.value = pd.periodoCalculo;
            };

            // ─── BOTÃO CARREGAR NOVA PLANILHA ─────────────────────────────────────────
            const btnCarregar = div.querySelector(`.btn-carregar-planilha-extra[data-idx="${idx}"]`);
            const inputExtra = div.querySelector(`.input-planilha-extra-pdf[data-idx="${idx}"]`);

            btnCarregar.onclick = () => inputExtra.click();

            inputExtra.onchange = async (e) => {
                const file = e.target.files[0];
                if (!file) return;
                inputExtra.value = '';  // reset — permite re-upload do mesmo arquivo

                const originalText = btnCarregar.textContent;
                btnCarregar.textContent = '⏳...';
                btnCarregar.disabled = true;

                try {
                    const loaded = await carregarPDFJSSeNecessario();
                    if (!loaded) throw new Error('PDF.js não disponível');

                    const dados = await processarPlanilhaPDF(file);
                    if (!dados.sucesso) throw new Error(dados.erro || 'Erro desconhecido');

                    // Preencher campos da linha com dados extraídos
                    if (dados.idPlanilha && idInput) idInput.value = dados.idPlanilha;
                    if (dados.periodoCalculo && periodoInput) periodoInput.value = dados.periodoCalculo;

                    // Registrar como planilha disponível para as demais linhas
                    const extraId = `extra_${idx}`;
                    const extraLabel = `${dados.idPlanilha || 'Extra'} (Dev.${idx + 2})`;
                    registrarPlanilhaDisponivel(extraId, extraLabel, dados);

                    // Selecionar esta planilha no dropdown desta linha
                    selectPlanilha.value = extraId;

                    // Feedback visual
                    btnCarregar.textContent = '✓ Analisada';
                    btnCarregar.style.background = '#10b981';
                    btnCarregar.disabled = false;

                } catch (err) {
                    alert('Erro ao processar planilha: ' + err.message);
                    btnCarregar.textContent = originalText;
                    btnCarregar.disabled = false;
                }
            };
        }

        $('chk-hon-reu').onchange = (e) => {
            // Lógica invertida: marcado = "Não há" = esconde campos
            $('hon-reu-campos').classList.toggle('hidden', e.target.checked);
        };

        // Controlar exibição de campo percentual vs valor
        document.querySelectorAll('input[name="rad-hon-reu-tipo"]').forEach(radio => {
            radio.addEventListener('change', (e) => {
                const isPercentual = e.target.value === 'percentual';
                $('hon-reu-perc-campo').classList.toggle('hidden', !isPercentual);
                $('hon-reu-valor-campo').classList.toggle('hidden', isPercentual);
            });
        });

        $('chk-perito-conh').onchange = (e) => { $('perito-conh-campos').classList.toggle('hidden', !e.target.checked); };

        // CORREÇÃO 4: Event listener simplificado - guard interno em preencherDepositosAutomaticos
        $('chk-deposito').onchange = (e) => {
            // Toggle visibilidade
            $('deposito-campos').classList.toggle('hidden', !e.target.checked);

            // Preencher automaticamente se marcado (safe: tem guard para jaTemCampos)
            if (e.target.checked) {
                preencherDepositosAutomaticos();
            }
        };

        $('chk-pag-antecipado').onchange = (e) => {
            $('pag-antecipado-campos').classList.toggle('hidden', !e.target.checked);
            if (e.target.checked && window.hcalcState.pagamentosAntecipados.length === 0) {
                adicionarPagamentoAntecipado(); // Adiciona primeiro pagamento automaticamente
            }
        };

        // Event listeners para radios de tipo de liberação
        document.querySelectorAll('input[name="lib-tipo"]').forEach(radio => {
            radio.addEventListener('change', (e) => {
                const valor = e.target.value;
                $('lib-remanescente-campos').classList.toggle('hidden', valor !== 'remanescente');
                $('lib-devolucao-campos').classList.toggle('hidden', valor !== 'devolucao');
            });
        });

        document.getElementsByName('rad-intimacao').forEach((rad) => {
            rad.onchange = (e) => { $('intimacao-mandado-campos').classList.toggle('hidden', e.target.value === 'diario'); };
        });

        // ==========================================
        // ==========================================
        // FUNÇÕES DE GERENCIAMENTO DE MÚLTIPLOS DEPÓSITOS
        // ==========================================

        // Preenche depósitos automaticamente com recursos detectados (Depósito/Garantia)
        function preencherDepositosAutomaticos() {
            const prep = window.hcalcLastPrepResult;
            if (!prep || !prep.depositos || prep.depositos.length === 0) {
                console.log('[AUTO-DEPOSITOS] Sem dados de prep');
                return;
            }

            const container = $('depositos-container');
            if (!container) {
                console.error('[AUTO-DEPOSITOS] Container não encontrado!');
                return;
            }

            // Se já tem campos, não limpar (permite adicionar manualmente)
            const jaTemCampos = container.children.length > 0;
            if (jaTemCampos) {
                console.log('[AUTO-DEPOSITOS] Container já possui campos, pulando');
                return;
            }

            // Limpar depósitos existentes apenas se estiver vazio
            container.innerHTML = '';
            window.hcalcState.nextDepositoIdx = 0;
            window.hcalcState.depositosRecursais = [];

            console.log('[AUTO-DEPOSITOS] Iniciando preenchimento com', prep.depositos.length, 'recursos');

            // Preencher com TODOS os depósitos/garantias dos recursos detectados
            for (const deposito of prep.depositos) {
                // Filtrar anexos de tipo Depósito, Garantia ou Custas
                const anexosRelevantes = (deposito.anexos || []).filter(ax =>
                    ax.tipo === 'Depósito' || ax.tipo === 'Garantia' || ax.tipo === 'Custas'
                );

                // CONSOLIDAR: apenas 1 ocorrência de cada tipo por recurso
                // (múltiplos anexos do mesmo tipo = guia + comprovante = mesmo depósito)
                const tiposUnicos = {};
                anexosRelevantes.forEach(ax => {
                    if (!tiposUnicos[ax.tipo]) {
                        tiposUnicos[ax.tipo] = ax; // Pega o primeiro de cada tipo
                    }
                });
                const anexosConsolidados = Object.values(tiposUnicos);

                // CORREÇÃO 3: Fallback para recursos sem anexos expandidos
                if (anexosConsolidados.length > 0) {
                    for (const anexo of anexosConsolidados) {
                        adicionarDepositoRecursal();
                        const idx = window.hcalcState.nextDepositoIdx - 1;

                        const tipoSelect = $(`dep-tipo-${idx}`);
                        const depositanteSelect = $(`dep-depositante-${idx}`);
                        const idInput = $(`dep-id-${idx}`);

                        if (tipoSelect) {
                            tipoSelect.value = anexo.tipo === 'Depósito' ? 'bb' : 'garantia';
                            tipoSelect.dispatchEvent(new Event('change', { bubbles: true }));
                        }

                        if (depositanteSelect) {
                            depositanteSelect.value = deposito.depositante;
                        }

                        if (idInput) {
                            idInput.value = anexo.id || '';
                        }
                    }
                    console.log('[AUTO-DEPOSITOS]', anexosConsolidados.length, 'depósito(s) consolidado(s) de', deposito.depositante);
                } else {
                    // FALLBACK: Recurso detectado mas sem anexos expandidos
                    console.warn('[AUTO-DEPOSITOS] Recurso sem anexos para', deposito.depositante, '— criando linha sem ID');
                    adicionarDepositoRecursal();
                    const idx = window.hcalcState.nextDepositoIdx - 1;
                    const depositanteSelect = $(`dep-depositante-${idx}`);
                    if (depositanteSelect) {
                        depositanteSelect.value = deposito.depositante || '';
                    }
                }
            }
        }

        function adicionarDepositoRecursal() {
            const idx = window.hcalcState.nextDepositoIdx++;
            const container = $('depositos-container');

            // Buscar TODAS as reclamadas do processo (não só as com recursos)
            const reclamadas = window.hcalcPartesData?.passivo?.map(r => r.nome) || [];

            const depositoDiv = document.createElement('div');
            depositoDiv.id = `deposito-item-${idx}`;
            depositoDiv.className = 'deposito-item';
            depositoDiv.style.cssText = 'border: 1px solid #ddd; padding: 8px; margin-bottom: 8px; border-radius: 4px; background: #f9f9f9;';

            // Construir opções do select de depositante com TODAS as reclamadas do processo
            let optionsHtml = '<option value="">-- Selecione Reclamada --</option>';
            for (const nome of reclamadas) {
                optionsHtml += `<option value="${nome}">${nome}</option>`;
            }

            depositoDiv.innerHTML = `
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <strong style="font-size: 11px; color: #666;">Depósito Recursal #${idx + 1}</strong>
                    <button type="button" id="btn-remover-dep-${idx}" style="padding: 2px 8px; font-size: 10px; color: #dc2626; background: #fee; border: 1px solid #fca; border-radius: 3px; cursor: pointer;">✕ Remover</button>
                </div>
                <div class="row">
                    <select id="dep-tipo-${idx}" data-dep-idx="${idx}">
                        <option value="bb" selected>Banco do Brasil</option>
                        <option value="sif">CEF (SIF)</option>
                        <option value="garantia">Seguro Garantia</option>
                    </select>
                    <select id="dep-depositante-${idx}" data-dep-idx="${idx}">
                        ${optionsHtml}
                    </select>
                    <input type="text" id="dep-id-${idx}" placeholder="ID da Guia" data-dep-idx="${idx}">
                </div>
                <div class="row" id="dep-principal-row-${idx}">
                    <label><input type="checkbox" id="dep-principal-${idx}" checked data-dep-idx="${idx}"> Depositado pela Devedora Principal?</label>
                </div>
                <div class="row hidden" id="dep-solidaria-info-${idx}" style="font-size: 11px; color: #059669; font-style: italic;">
                    ✓ Devedoras solidárias: qualquer depósito pode ser liberado
                </div>
                <div class="row" id="dep-liberacao-row-${idx}">
                    <label><input type="radio" name="rad-dep-lib-${idx}" value="reclamante" checked data-dep-idx="${idx}"> Liberação simples (Reclamante)</label>
                    <label style="margin-left: 10px;"><input type="radio" name="rad-dep-lib-${idx}" value="detalhada" data-dep-idx="${idx}"> Liberação detalhada (Crédito, INSS, Hon.)</label>
                </div>
            `;

            container.appendChild(depositoDiv);

            // Event listeners para este depósito específico
            const tipoEl = $(`dep-tipo-${idx}`);
            const principalEl = $(`dep-principal-${idx}`);
            const liberacaoRow = $(`dep-liberacao-row-${idx}`);

            tipoEl.onchange = (e) => {
                liberacaoRow.classList.toggle('hidden', e.target.value === 'garantia');
            };

            principalEl.onchange = (e) => {
                liberacaoRow.classList.toggle('hidden', !e.target.checked);
            };

            // Atualizar visibilidade inicial baseado em tipo de responsabilidade
            atualizarVisibilidadeDepositoPrincipal(idx);

            // Event listener para botão remover (evita problema sandbox TamperMonkey)
            const btnRemoverDep = depositoDiv.querySelector(`#btn-remover-dep-${idx}`);
            if (btnRemoverDep) {
                btnRemoverDep.addEventListener('click', () => {
                    depositoDiv.remove();
                    const dep = window.hcalcState.depositosRecursais.find(d => d.idx === idx);
                    if (dep) dep.removed = true;
                });
            }

            // Armazenar referência no estado
            window.hcalcState.depositosRecursais.push({ idx, removed: false });
        }

        function atualizarVisibilidadeDepositoPrincipal(idx) {
            const tipoResp = $('resp-tipo')?.value || 'unica';
            const isSolidaria = tipoResp === 'solidarias';

            const principalRow = $(`dep-principal-row-${idx}`);
            const solidariaInfo = $(`dep-solidaria-info-${idx}`);
            const principalChk = $(`dep-principal-${idx}`);

            if (principalRow && solidariaInfo) {
                if (isSolidaria) {
                    // Ocultar checkbox, mostrar info, forçar checked
                    principalRow.classList.add('hidden');
                    solidariaInfo.classList.remove('hidden');
                    if (principalChk) principalChk.checked = true;
                } else {
                    // Mostrar checkbox, ocultar info
                    principalRow.classList.remove('hidden');
                    solidariaInfo.classList.add('hidden');
                }
            }
        }

        function adicionarPagamentoAntecipado() {
            const idx = window.hcalcState.nextPagamentoIdx++;
            const container = $('pagamentos-container');

            const pagamentoDiv = document.createElement('div');
            pagamentoDiv.id = `pagamento-item-${idx}`;
            pagamentoDiv.className = 'pagamento-item';
            pagamentoDiv.style.cssText = 'border: 1px solid #ddd; padding: 8px; margin-bottom: 8px; border-radius: 4px; background: #f9f9f9;';

            pagamentoDiv.innerHTML = `
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <strong style="font-size: 11px; color: #666;">Pagamento Antecipado #${idx + 1}</strong>
                    <button type="button" id="btn-remover-pag-${idx}" style="padding: 2px 8px; font-size: 10px; color: #dc2626; background: #fee; border: 1px solid #fca; border-radius: 3px; cursor: pointer;">✕ Remover</button>
                </div>
                <div class="row">
                    <input type="text" id="pag-id-${idx}" placeholder="ID do Depósito" data-pag-idx="${idx}">
                </div>
                <div class="row">
                    <label><input type="radio" name="lib-tipo-${idx}" value="nenhum" checked data-pag-idx="${idx}"> Padrão (extinção)</label>
                    <label style="margin-left: 15px;"><input type="radio" name="lib-tipo-${idx}" value="remanescente" data-pag-idx="${idx}"> Com Remanescente</label>
                    <label style="margin-left: 15px;"><input type="radio" name="lib-tipo-${idx}" value="devolucao" data-pag-idx="${idx}"> Com Devolução</label>
                </div>
                <div id="lib-remanescente-campos-${idx}" class="hidden">
                    <div class="row">
                        <input type="text" id="lib-rem-valor-${idx}" placeholder="Valor Remanescente (ex: 1.234,56)" data-pag-idx="${idx}">
                        <input type="text" id="lib-rem-titulo-${idx}" placeholder="Título (ex: custas processuais)" data-pag-idx="${idx}">
                    </div>
                </div>
                <div id="lib-devolucao-campos-${idx}" class="hidden">
                    <div class="row">
                        <input type="text" id="lib-dev-valor-${idx}" placeholder="Valor Devolução (ex: 1.234,56)" data-pag-idx="${idx}">
                    </div>
                </div>
            `;

            container.appendChild(pagamentoDiv);

            // Event listeners para os radios deste pagamento
            document.querySelectorAll(`input[name="lib-tipo-${idx}"]`).forEach(radio => {
                radio.addEventListener('change', (e) => {
                    const valor = e.target.value;
                    $(`lib-remanescente-campos-${idx}`).classList.toggle('hidden', valor !== 'remanescente');
                    $(`lib-devolucao-campos-${idx}`).classList.toggle('hidden', valor !== 'devolucao');
                });
            });

            // Event listener para botão remover (evita problema sandbox TamperMonkey)
            const btnRemoverPag = pagamentoDiv.querySelector(`#btn-remover-pag-${idx}`);
            if (btnRemoverPag) {
                btnRemoverPag.addEventListener('click', () => {
                    pagamentoDiv.remove();
                    const pag = window.hcalcState.pagamentosAntecipados.find(p => p.idx === idx);
                    if (pag) pag.removed = true;
                });
            }

            // Armazenar referência no estado
            window.hcalcState.pagamentosAntecipados.push({ idx, removed: false });
        }

        // Bind dos botões de adicionar
        $('btn-add-deposito').onclick = adicionarDepositoRecursal;
        $('btn-add-pagamento').onclick = adicionarPagamentoAntecipado;

        // Máscara de data DD/MM/YYYY para campos de data
        const aplicarMascaraData = (input) => {
            input.addEventListener('input', (e) => {
                let valor = e.target.value.replace(/\D/g, ''); // Remove não-dígitos
                if (valor.length >= 2) {
                    valor = valor.slice(0, 2) + '/' + valor.slice(2);
                }
                if (valor.length >= 5) {
                    valor = valor.slice(0, 5) + '/' + valor.slice(5);
                }
                e.target.value = valor.slice(0, 10); // Limita a DD/MM/YYYY
            });
        };

        // Aplicar máscara aos campos de data
        ['val-data', 'custas-data-origem', 'val-perito-data'].forEach(id => {
            const campo = $(id);
            if (campo) aplicarMascaraData(campo);
        });

        // Toggle origem custas: Sentença vs Acórdão
        $('custas-origem').onchange = (e) => {
            const isAcordao = e.target.value === 'acordao';
            $('custas-data-col').classList.toggle('hidden', isAcordao);
            $('custas-acordao-col').classList.toggle('hidden', !isAcordao);
        };

        const ordemCopiaLabels = {
            'val-id': '1) Id da Planilha',
            'val-data': '1) Data da Atualização',
            'val-credito': '1) Crédito Principal',
            'val-fgts': '1) FGTS Separado',
            'val-inss-rec': '2) INSS - Desconto Reclamante',
            'val-inss-total': '2) INSS - Total Empresa',
            'val-hon-autor': '3) Honorários do Autor',
            'val-custas': '4) Custas'
        };

        window.hcalcPeritosDetectados = [];
        window.hcalcPeritosConhecimentoDetectados = [];

        function isNomeRogerio(nome) {
            return /rogerio|rogério/i.test(nome || '');
        }

        function aplicarRegrasPeritosDetectados(peritosDetectados) {
            const nomes = Array.isArray(peritosDetectados) ? peritosDetectados.filter(Boolean) : [];
            const temRogerio = nomes.some((nome) => isNomeRogerio(nome));
            const peritosConhecimento = nomes.filter((nome) => !isNomeRogerio(nome));

            window.hcalcPeritosDetectados = nomes;
            window.hcalcPeritosConhecimentoDetectados = peritosConhecimento;

            console.log('[hcalc] aplicarRegrasPeritosDetectados: nomes=', nomes, 'temRogerio=', temRogerio, 'peritosConhecimento=', peritosConhecimento);

            const origemEl = $('calc-origem');
            const pjcEl = $('calc-pjc');
            const autorEl = $('calc-autor');
            const colEsclarecimentosEl = $('col-esclarecimentos');
            const rowPeritoContabilEl = $('row-perito-contabil');
            const chkPeritoConhEl = $('chk-perito-conh');
            const peritoConhCamposEl = $('perito-conh-campos');
            const valPeritoNomeEl = $('val-perito-nome');
            const valPeritoContabilValorEl = $('val-perito-contabil-valor');
            const fieldsetPericiaConh = $('fieldset-pericia-conh');

            console.log('[hcalc] Elementos encontrados: rowPeritoContabilEl=', rowPeritoContabilEl, 'fieldsetPericiaConh=', fieldsetPericiaConh);

            // SE ROGÉRIO (perito contábil)
            if (temRogerio) {
                console.log('[hcalc] Rogério detectado! Mostrando row-perito-contabil...');
                origemEl.value = 'pjecalc';
                origemEl.disabled = true;
                pjcEl.checked = true;
                pjcEl.disabled = true;
                autorEl.value = 'perito';
                autorEl.disabled = true;
                colEsclarecimentosEl.classList.remove('hidden');
                
                // Mostrar fieldset pai (contém honorários contábeis E conhecimento)
                if (fieldsetPericiaConh) {
                    fieldsetPericiaConh.classList.remove('hidden');
                }
                
                // Mostrar linha de honorários contábeis
                if (rowPeritoContabilEl) {
                    rowPeritoContabilEl.classList.remove('hidden');
                    console.log('[hcalc] ✓ Classe hidden removida de row-perito-contabil');
                } else {
                    console.error('[hcalc] ✗ Elemento row-perito-contabil NÃO ENCONTRADO!');
                }
                
                // Esconder seção de conhecimento se APENAS Rogério
                if (peritosConhecimento.length === 0) {
                    // Não esconder o fieldset, apenas o checkbox de conhecimento
                    if (chkPeritoConhEl) {
                        chkPeritoConhEl.parentElement.parentElement.classList.add('hidden');
                    }
                }
            } else {
                origemEl.disabled = false;
                pjcEl.disabled = false;
                autorEl.disabled = false;
                rowPeritoContabilEl.classList.add('hidden');
                if (valPeritoContabilValorEl) {
                    valPeritoContabilValorEl.value = '';
                }
                colEsclarecimentosEl.classList.add('hidden');
            }

            // SE TEM QUALQUER PERITO DE CONHECIMENTO (que não seja Rogério)
            if (peritosConhecimento.length > 0) {
                console.log('[hcalc] Perítos de conhecimento detectados:', peritosConhecimento);
                if (fieldsetPericiaConh) fieldsetPericiaConh.classList.remove('hidden');
                chkPeritoConhEl.checked = true;
                peritoConhCamposEl.classList.remove('hidden');
                valPeritoNomeEl.value = peritosConhecimento.join(' | ');
                console.log('[hcalc] ✓ Seção de conhecimento mostrada com peritos:', peritosConhecimento);
            } else if (!temRogerio) {
                // Esconder card de perícia se não há nenhum perito
                if (fieldsetPericiaConh) fieldsetPericiaConh.classList.add('hidden');
            }
        }

        function atualizarStatusProximoCampo(nextInputId = null) {
            // Função simplificada - status removido da interface
            // Mantida para compatibilidade com código existente
        }

        // Timeline functions moved to prep.js
        // readTimelineBasic / extractDataFromTimelineItem / getTimelineItems
        // now handled by window.executarPrep()

        function construirSecaoIntimacoes() {
            const container = $('lista-intimacoes-container');
            if (!container) return;

            const passivo = window.hcalcPartesData?.passivo || [];
            const advMap = window.hcalcStatusAdvogados || {};
            const partesIntimadasEdital = window.hcalcPrepResult?.partesIntimadasEdital || [];

            container.innerHTML = '';

            if (passivo.length === 0) {
                container.innerHTML = `
                    <div style="margin-bottom: 5px;">
                        <input type="text" id="int-nome-parte-manual" placeholder="Nome da Reclamada" style="width: 100%; padding: 6px; box-sizing: border-box; margin-bottom: 5px;">
                        <select id="sel-intimacao-manual" style="width: 100%; padding: 4px;">
                            <option value="diario">Diário (Advogado - Art. 523)</option>
                            <option value="mandado">Mandado (Art. 880 - 48h)</option>
                            <option value="edital">Edital (Art. 880 - 48h)</option>
                        </select>
                    </div>`;
                return;
            }

            passivo.forEach((parte, idx) => {
                const temAdvogado = advMap[parte.nome] === true;
                let modoDefault = 'mandado';

                if (temAdvogado) modoDefault = 'diario';
                else if (partesIntimadasEdital.includes(parte.nome)) modoDefault = 'edital';

                const divRow = document.createElement('div');
                divRow.className = 'intimacao-row';
                divRow.style.cssText = "display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px; padding: 6px; background: #f9f9f9; border: 1px solid #ddd; border-radius: 4px;";

                // Checkbox para marcar como principal (primeira é marcada por padrão)
                const isPrimeiraPorPadrao = idx === 0;

                divRow.innerHTML = `
                    <div style="flex: 1; font-size: 13px; font-weight: bold; color: #333; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; padding-right: 10px;" title="${parte.nome}">
                        ${parte.nome}
                    </div>
                    <div style="flex-shrink: 0; display: flex; align-items: center; gap: 8px;">
                        <label style="font-size: 11px; margin: 0; display: flex; align-items: center; gap: 3px; color: #666;">
                            <input type="checkbox" class="chk-parte-principal" data-nome="${parte.nome}" ${isPrimeiraPorPadrao ? 'checked' : ''}>
                            Principal
                        </label>
                        <select class="sel-modo-intimacao" data-nome="${parte.nome}" style="padding: 4px; font-size: 12px; border: 1px solid #ccc; border-radius: 4px;">
                            <option value="diario" ${modoDefault === 'diario' ? 'selected' : ''}>Diário (Advogado - Art 523)</option>
                            <option value="mandado" ${modoDefault === 'mandado' ? 'selected' : ''}>Mandado (Art 880 - 48h)</option>
                            <option value="edital" ${modoDefault === 'edital' ? 'selected' : ''}>Edital (Art 880 - 48h)</option>
                            <option value="ignorar">Não Intimar</option>
                        </select>
                    </div>
                `;
                container.appendChild(divRow);
            });
        }

        async function refreshDetectedPartes() {
            const partes = await derivePartesData();

            // Armazenar globalmente para uso em geração de textos
            window.hcalcPartesData = partes;

            const reclamadas = (partes?.passivo || []).map(p => p.nome).filter(Boolean);
            const peritos = ordenarComRogerioPrimeiro(extractPeritos(partes));
            const advogadosMap = extractAdvogadosPorReclamada(partes);
            const statusAdvMap = extractStatusAdvogadoPorReclamada(partes);
            const advogadosAutor = extractAdvogadosDoAutor(partes);

            window.hcalcStatusAdvogados = statusAdvMap;
            window.hcalcAdvogadosAutor = advogadosAutor; // Cache global para validação de honorários
            window.hcalcPeritosDetectados = peritos; // Cache global para validação de honorários

            // Log para debug
            console.log('hcalc: advogados por reclamada', advogadosMap);
            console.log('hcalc: status advogado por reclamada', statusAdvMap);
            console.log(`[hcalc] Detecção atualizada: ${reclamadas.length} reclamada(s), ${peritos.length} perito(s)`);

            aplicarRegrasPeritosDetectados(peritos);

            // Log de debug
            console.log(`[hcalc] Detecção atualizada: ${reclamadas.length} reclamada(s), ${peritos.length} perito(s)`);

            // LÓGICA DE RESPONSABILIDADE DINÂMICA
            const respFieldset = document.querySelector('fieldset #resp-tipo')?.closest('fieldset');
            if (reclamadas.length <= 1 && respFieldset) {
                respFieldset.classList.add('hidden');
            } else if (reclamadas.length > 1 && respFieldset) {
                respFieldset.classList.remove('hidden');
            }

            // AUTO-PREENCHER DEPOSITANTE COM RECLAMADA EXTRAIDA
            const depDepositante = $('dep-depositante');
            if (depDepositante && reclamadas.length > 0) {
                if (reclamadas.length === 1) {
                    // Só 1 reclamada: preencher e travar
                    depDepositante.value = reclamadas[0];
                    depDepositante.disabled = true;
                } else {
                    // 2+ reclamadas: transformar em dropdown
                    const selectEl = document.createElement('select');
                    selectEl.id = 'dep-depositante';
                    selectEl.style.cssText = depDepositante.style.cssText || 'padding: 8px; border: 1px solid #aaa; border-radius: 4px; font-size: 14px;';
                    reclamadas.forEach((rec, idx) => {
                        const opt = document.createElement('option');
                        opt.value = rec;
                        opt.textContent = rec;
                        if (idx === 0) opt.selected = true;
                        selectEl.appendChild(opt);
                    });
                    depDepositante.replaceWith(selectEl);
                }
            }

            // CONSTRUIR SEÇÃO DE INTIMAÇÕES
            construirSecaoIntimacoes();
        }

        function getProcessIdFromUrl() {
            const match = window.location.href.match(/\/processo\/(\d+)/);
            return match ? match[1] : null;
        }

        function shapePartesPayload(dados) {
            const buildRecord = (parte, tipo, idx, total) => {
                let nome = parte.nome.trim();
                return {
                    nome,
                    cpfcnpj: parte.documento || 'desconhecido',
                    tipo,
                    telefone: formatTelefones(parte.pessoaFisica),
                    representantes: (parte.representantes || []).map(rep => ({
                        nome: rep.nome.trim(),
                        cpfcnpj: rep.documento || 'desconhecido',
                        oab: rep.numeroOab || '',
                        tipo: rep.tipo
                    }))
                };
            };

            const formatTelefones = (pessoaFisica) => {
                if (!pessoaFisica) { return 'desconhecido'; }
                const numbers = [];
                if (pessoaFisica.dddCelular && pessoaFisica.numeroCelular) {
                    numbers.push(`(${pessoaFisica.dddCelular}) ${pessoaFisica.numeroCelular}`);
                }
                if (pessoaFisica.dddResidencial && pessoaFisica.numeroResidencial) {
                    numbers.push(`(${pessoaFisica.dddResidencial}) ${pessoaFisica.numeroResidencial}`);
                }
                if (pessoaFisica.dddComercial && pessoaFisica.numeroComercial) {
                    numbers.push(`(${pessoaFisica.dddComercial}) ${pessoaFisica.numeroComercial}`);
                }
                return numbers.join(' | ') || 'desconhecido';
            };

            const ativo = (dados?.ATIVO || []).map((parte, idx) => buildRecord(parte, 'AUTOR', idx, dados.ATIVO.length));
            const passivo = (dados?.PASSIVO || []).map((parte, idx) => buildRecord(parte, 'RÉU', idx, dados.PASSIVO.length));
            const outros = (dados?.TERCEIROS || []).map((parte, idx) => buildRecord(parte, parte.tipo || 'TERCEIRO', idx, dados.TERCEIROS.length));

            return { ativo, passivo, outros };
        }

        async function fetchPartesViaApi() {
            const trtHost = window.location.host;
            const baseUrl = `https://${trtHost}`;
            const idProcesso = getProcessIdFromUrl();
            if (!idProcesso) {
                console.warn('hcalc: idProcesso não detectado na URL.');
                return null;
            }
            const url = `${baseUrl}/pje-comum-api/api/processos/id/${idProcesso}/partes`;
            try {
                const response = await fetch(url, { credentials: 'include' });
                if (!response.ok) {
                    throw new Error(`API retornou ${response.status}`);
                }
                const json = await response.json();
                const partes = shapePartesPayload(json);
                // Armazenar no cache
                const PROCESS_CACHE = window.calcPartesCache || {};
                PROCESS_CACHE[idProcesso] = partes;
                window.calcPartesCache = PROCESS_CACHE;

                // LIMITAR CACHE: Manter apenas últimas 5 entradas para prevenir crescimento ilimitado
                const keys = Object.keys(window.calcPartesCache);
                if (keys.length > 5) {
                    delete window.calcPartesCache[keys[0]];
                    console.log('hcalc: cache limitado a 5 entradas, removida mais antiga');
                }

                console.log('hcalc: partes extraídas via API', partes);
                return partes;
            } catch (error) {
                console.error('hcalc: falha ao buscar partes via API', error);
                return null;
            }
        }

        async function derivePartesData() {
            // Inicializar cache se não existir
            if (!window.calcPartesCache) {
                window.calcPartesCache = {};
            }
            const cache = window.calcPartesCache;
            const processId = getProcessIdFromUrl();

            // 1. Tentar cache primeiro
            if (processId && cache[processId]) {
                console.log('hcalc: usando dados do cache', cache[processId]);
                return cache[processId];
            }

            // 2. Tentar buscar via API
            if (processId) {
                const apiData = await fetchPartesViaApi();
                if (apiData) {
                    return apiData;
                }
            }

            // 3. Fallback: buscar qualquer cache disponível
            const fallbackKey = processId ? Object.keys(cache).find((key) => key.includes(processId)) : null;
            if (fallbackKey) {
                console.log('hcalc: usando cache alternativo', cache[fallbackKey]);
                return cache[fallbackKey];
            }

            const cachedValues = Object.values(cache);
            if (cachedValues.length > 0) {
                console.log('hcalc: usando primeiro cache disponível', cachedValues[0]);
                return cachedValues[0];
            }

            // 4. Último recurso: parsear DOM
            console.warn('hcalc: usando parseamento do DOM (pode ser impreciso)');
            return parsePartesFromDom();
        }

        function parsePartesFromDom() {
            const rows = document.querySelectorAll('div[class*="bloco-participante"] tbody tr');
            const data = { ativo: [], passivo: [], outros: [] };
            rows.forEach((row) => {
                const text = row.innerText || '';
                const value = text.split('\n').map((l) => l.trim()).find(Boolean) || text.trim();
                if (!value) { return; }
                if (/reclamante|exequente|autor/i.test(text)) {
                    data.ativo.push({ nome: value });
                } else if (/reclamado|réu|executado/i.test(text)) {
                    data.passivo.push({ nome: value });
                } else {
                    // Detectar tipo por padrão no texto
                    let tipo = 'OUTRO';
                    if (/perito/i.test(text) || /perito/i.test(value)) {
                        tipo = 'PERITO';
                    }
                    data.outros.push({ nome: value, tipo });
                }
            });
            console.log('[hcalc] parsePartesFromDom: detectou', data);
            return data;
        }

        function extractPeritos(partes) {
            const outros = partes?.outros || [];
            console.log('[hcalc] extractPeritos: outros=', outros);
            // Filtrar por tipo 'PERITO' ou qualquer variação no nome/tipo
            const peritosEncontrados = outros.filter((part) => {
                const tipo = (part.tipo || '').toUpperCase();
                const nome = (part.nome || '').toUpperCase();
                return tipo.includes('PERITO') || nome.includes('PERITO');
            }).map((part) => part.nome);
            console.log('[hcalc] extractPeritos: peritos encontrados=', peritosEncontrados);
            return peritosEncontrados;
        }

        function ordenarComRogerioPrimeiro(nomes) {
            if (!Array.isArray(nomes) || nomes.length === 0) { return []; }
            const rogerio = [];
            const demais = [];
            nomes.forEach((nome) => {
                if (/rogerio/i.test(nome || '')) {
                    rogerio.push(nome);
                } else {
                    demais.push(nome);
                }
            });
            return [...rogerio, ...demais];
        }

        // ==========================================
        // FUNÇÕES DE EXTRAÇÃO DE REPRESENTANTES
        // ==========================================
        window.hcalcPartesData = null; // Cache global de partes para uso em geração de textos

        function extractAdvogadosPorReclamada(partes) {
            const map = {};
            if (!partes?.passivo) { return map; }
            partes.passivo.forEach((reclamada) => {
                const reps = reclamada.representantes || [];
                const advogados = reps.filter(rep => {
                    const tipo = (rep.tipo || '').toUpperCase();
                    return tipo.includes('ADVOGADO') || tipo.includes('OAB');
                }).map(rep => ({
                    nome: rep.nome,
                    oab: rep.oab || ''
                }));
                map[reclamada.nome] = advogados;
            });
            return map;
        }

        function extractAdvogadosDoAutor(partes) {
            const advogados = [];
            if (!partes?.ativo) { return advogados; }
            partes.ativo.forEach((reclamante) => {
                const reps = reclamante.representantes || [];
                const advs = reps.filter(rep => {
                    const tipo = (rep.tipo || '').toUpperCase();
                    return tipo.includes('ADVOGADO') || tipo.includes('OAB');
                }).map(rep => ({
                    nome: rep.nome,
                    oab: rep.oab || '',
                    nomeNormalizado: normalizarNomeParaComparacao(rep.nome)
                }));
                advogados.push(...advs);
            });
            console.log('hcalc: advogados do autor extraídos:', advogados);
            return advogados;
        }

        function verificarSeNomeEAdvogadoAutor(nomeParaVerificar, advogadosAutor) {
            if (!nomeParaVerificar || !advogadosAutor || advogadosAutor.length === 0) {
                return false;
            }
            const nomeNorm = normalizarNomeParaComparacao(nomeParaVerificar);
            return advogadosAutor.some(adv => {
                const match = adv.nomeNormalizado === nomeNorm ||
                    nomeNorm.includes(adv.nomeNormalizado) ||
                    adv.nomeNormalizado.includes(nomeNorm);
                if (match) {
                    console.log(`hcalc: match encontrado - "${nomeParaVerificar}" = advogado autor "${adv.nome}"`);
                }
                return match;
            });
        }

        function extractStatusAdvogadoPorReclamada(partes) {
            const map = {};
            if (!partes?.passivo) { return map; }

            partes.passivo.forEach((reclamada) => {
                const reps = Array.isArray(reclamada.representantes) ? reclamada.representantes : [];
                const temRepresentante = reps.length > 0;

                const temIndicadorAdv = reps.some((rep) => {
                    const tipo = (rep?.tipo || '').toUpperCase();
                    const oab = (rep?.oab || rep?.numeroOab || '').toString().trim();
                    return tipo.includes('ADVOGADO') || tipo.includes('OAB') || oab !== '';
                });

                map[reclamada.nome] = temRepresentante || temIndicadorAdv;
            });

            return map;
        }

        function temAdvogado(nomeReclamada, advogadosMap) {
            if (!advogadosMap || !nomeReclamada) { return false; }
            const reps = advogadosMap[nomeReclamada] || [];
            return reps.length > 0;
        }

        function obterReclamadasSemAdvogado(partes, advogadosMap) {
            if (!partes?.passivo) { return []; }
            return partes.passivo.filter(rec => !temAdvogado(rec.nome, advogadosMap)).map(rec => rec.nome);
        }

        function obterReclamadasComAdvogado(partes, advogadosMap) {
            if (!partes?.passivo) { return []; }
            return partes.passivo.filter(rec => temAdvogado(rec.nome, advogadosMap)).map(rec => rec.nome);
        }

        // OTIMIZAÇÃO: adiar refresh até browser estar ocioso (não compete com carregamento)
        if (typeof requestIdleCallback === 'function') {
            requestIdleCallback(() => refreshDetectedPartes(), { timeout: 3000 });
        } else {
            setTimeout(refreshDetectedPartes, 1500); // fallback para browsers sem rIC
        }

        // ==========================================
        // 4. LÓGICA DE NAVEGAÇÃO "COLETA INTELIGENTE"
        // ==========================================
        const orderSequence = [
            'val-id', 'val-data', 'val-credito', 'val-fgts',
            'val-inss-rec', 'val-inss-total', 'val-hon-autor', 'val-custas'
        ];

        function updateHighlight(currentId = null) {
            orderSequence.forEach((id) => $(id).classList.remove('highlight'));
            const visibleInputs = orderSequence.filter((id) => !$(id).classList.contains('hidden'));
            if (visibleInputs.length === 0) return;
            let nextIndex = 0;
            if (currentId) {
                const currentIndex = visibleInputs.indexOf(currentId);
                if (currentIndex !== -1 && currentIndex < visibleInputs.length - 1) {
                    nextIndex = currentIndex + 1;
                } else if (currentIndex === visibleInputs.length - 1) {
                    return;
                }
            }
            const nextInputId = visibleInputs[nextIndex];
            $(nextInputId).classList.add('highlight');
            $(nextInputId).focus();
            atualizarStatusProximoCampo(nextInputId);
        }

        orderSequence.forEach((id) => {
            const el = $(id);
            el.addEventListener('paste', () => {
                setTimeout(() => {
                    el.value = el.value.trim();
                    updateHighlight(id);
                }, 10);
            });
            el.addEventListener('focus', () => {
                orderSequence.forEach((i) => $(i).classList.remove('highlight'));
                el.classList.add('highlight');
            });
        });

        // ==========================================
        // 5. FUNÇÕES AUXILIARES DE CÁLCULO E TEXTO
        function parseMoney(str) {
            if (!str) return 0;
            str = str.replace(/[R$\s]/g, '').replace(/\./g, '').replace(',', '.');
            const num = parseFloat(str);
            return isNaN(num) ? 0 : num;
        }

        function formatMoney(num) {
            return num.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' }).replace(/\s/g, '');
        }

        function normalizeMoneyInput(val) {
            if (!val || val === '[VALOR]') return val;
            const parsed = parseMoney(val);
            if (parsed === 0 && !/^\s*0/.test(val)) return val;
            return formatMoney(parsed);
        }

        function bold(text) { return `<strong>${text}</strong>`; }
        function u(text) { return `<u>${text}</u>`; }

        // ==========================================
        // 6. GERADOR DE DECISÃO HTML (O CORE)
        // ==========================================
        $('btn-gravar').onclick = () => {
            dbg('Clique em Gravar Decisao detectado.');
            let text = `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Vistos.</p>`;
            let houveDepositoDireto = false;
            let houveLibecaoDetalhada = false;
            const passivoTotal = (window.hcalcPartesData?.passivo || []).length;

            const autoria = $('calc-autor').options[$('calc-autor').selectedIndex].text;
            const idPlanilha = $('val-id').value || '[ID DA PLANILHA]';
            const valData = $('val-data').value || '[DATA]';
            const valCredito = $('val-credito').value || '[VALOR]';
            const valFgts = $('val-fgts').value || '[VALOR FGTS]';
            const isPerito = $('calc-autor').value === 'perito';
            const peritoEsclareceu = $('calc-esclarecimentos').checked;
            const pecaPerito = $('calc-peca-perito').value || '[ID PEÇA]';
            const indice = $('calc-indice').value;
            const isFgtsSep = $('calc-fgts').checked;
            const ignorarInss = $('ignorar-inss').checked;

            const xxx = () => u(bold('XXX'));

            const appendBaseAteAntesPericiais = ({
                idCalculo,
                usarPlaceholder = false,
                reclamadaLabel = ''
            }) => {
                let introTxt = '';
                const vCredito = usarPlaceholder ? 'R$XXX' : `R$${valCredito}`;
                const vFgts = usarPlaceholder ? 'R$XXX' : `R$${valFgts}`;
                const vData = usarPlaceholder ? 'XXX' : valData;

                if (isPerito && peritoEsclareceu) {
                    introTxt += `As impugnações apresentadas já foram objeto de esclarecimentos pelo Sr. Perito sob o #${bold(pecaPerito)}, nada havendo a ser reparado no laudo. Portanto, HOMOLOGO os cálculos do expert (#${bold(idCalculo)}), `;
                } else {
                    introTxt += `Tendo em vista a concordância das partes, HOMOLOGO os cálculos apresentados pelo(a) ${u(autoria)} (#${bold(idCalculo)}), `;
                }

                // Verificar se FGTS foi depositado (para evitar contradição)
                const fgtsTipo = isFgtsSep ? (document.querySelector('input[name="fgts-tipo"]:checked')?.value || 'devido') : 'devido';
                const fgtsJaDepositado = fgtsTipo === 'depositado';

                if (isFgtsSep && !fgtsJaDepositado) {
                    // FGTS devido (a ser recolhido em conta vinculada) - texto especial Lei 14.905/2024
                    introTxt += `fixando o crédito do autor em ${bold(vCredito)} relativo ao principal, e ${bold(vFgts)} relativo ao ${bold('FGTS')} a ser recolhido em conta vinculada, para ${bold(vData)}. `;
                    introTxt += `Atualização na forma da Lei 14.905/2024 e da decisão proferida pela SDI-1 do C. TST, ou seja, a correção monetária será feita pelo IPCA-E até a distribuição da ação; taxa Selic do ajuizamento até 29/08/2024, e, a partir de 30/08/2024, atualização pelo IPCA, com juros de mora correspondentes à diferença entre a SELIC e o IPCA, conforme o artigo 406 do Código Civil.`;
                } else if (isFgtsSep && fgtsJaDepositado) {
                    // FGTS depositado (não menciona "a ser recolhido")
                    introTxt += `fixando o crédito do autor em ${bold(vCredito)}, atualizado para ${bold(vData)}. `;
                    
                    // Aplica índice de atualização normal
                    if (indice === 'adc58') {
                        const textoAtualizacao = `Atualização: pelo IPCA-E na fase pré-judicial e, a partir do ajuizamento da ação, pela taxa SELIC (art. 406 do Código Civil), conforme decisão do E. Supremo Tribunal Federal nas ADCs 58 e 59 e ADI 5867, de 18/12/2020.`;
                        introTxt += textoAtualizacao;
                    } else {
                        const dtIngresso = usarPlaceholder ? 'XXX' : ($('data-ingresso').value || '[DATA INGRESSO]');
                        const textoAtualizacao = `Atualização: pela TR/IPCA-E, conforme sentença transitado em julgado. Juros legais a partir de ${bold(dtIngresso)}.`;
                        introTxt += textoAtualizacao;
                    }
                } else {
                    // Sem FGTS separado
                    introTxt += `fixando o crédito em ${bold(vCredito)}, referente ao valor principal, atualizado para ${bold(vData)}. `;
                    
                    // Aplica índice de atualização normal
                    if (indice === 'adc58') {
                        const textoAtualizacao = `Atualização: pelo IPCA-E na fase pré-judicial e, a partir do ajuizamento da ação, pela taxa SELIC (art. 406 do Código Civil), conforme decisão do E. Supremo Tribunal Federal nas ADCs 58 e 59 e ADI 5867, de 18/12/2020.`;
                        introTxt += textoAtualizacao;
                    } else {
                        const dtIngresso = usarPlaceholder ? 'XXX' : ($('data-ingresso').value || '[DATA INGRESSO]');
                        const textoAtualizacao = `Atualização: pela TR/IPCA-E, conforme sentença transitado em julgado. Juros legais a partir de ${bold(dtIngresso)}.`;
                        introTxt += textoAtualizacao;
                    }
                }

                if (reclamadaLabel) {
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;"><strong>${reclamadaLabel}</strong></p>`;
                }
                text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">${introTxt}</p>`;

                // 2º parágrafo: FGTS devido - liberação após recolhimento
                if (isFgtsSep && !fgtsJaDepositado) {
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Após o recolhimento do FGTS pela reclamada, deverá a Secretaria providenciar a liberação ao autor, por meio de expedição de alvará, ante o término do contrato de forma imotivada.</p>`;
                }

                // 3º parágrafo: FGTS depositado (com valor)
                if (isFgtsSep && fgtsJaDepositado) {
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">O FGTS, no valor de ${bold(vFgts)}, já foi depositado e, portanto, já está deduzido do crédito.</p>`;
                }

                if (!usarPlaceholder && $('calc-origem').value === 'pjecalc' && !$('calc-pjc').checked) {
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Considerando a ausência do arquivo de origem, <u>deverá a parte apresentar novamente a planilha ora homologada, acompanhada obrigatoriamente do respectivo arquivo ${bold('.PJC')} no prazo de 05 dias</u>.</p>`;
                }

                if (usarPlaceholder) {
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Desde já, ficam autorizados os descontos previdenciários (cota do reclamante) ora fixados em ${xxx()}, para ${xxx()}, devendo, para as retenções, serem observados os termos da Súmula 368, C. TST e da Instrução Normativa RFB nº 1.500, de 29/10/2014.</p>`;
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Os valores relativos às contribuições previdenciárias devidas em decorrência de decisões proferidas pela Justiça do Trabalho a partir de 1º de outubro de 2023, inclusive acordos homologados, devem ser recolhidos pelo(a) reclamado(a) por meio da DCTF-Web, depois de serem informados os dados da reclamatória trabalhista no e-Social. Atente-se que os registros no e-Social serão feitos por meio dos eventos: "S-2500 - Processos Trabalhistas" e "S-2501 - Informações de Tributos Decorrentes de Processo Trabalhista".</p>`;
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Nos casos em que os recolhimentos forem efetuados diretamente pela Justiça do Trabalho, o reclamado deverá enviar através do e-Social somente o evento "S-2500 – Processos Trabalhistas".</p>`;
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">A reclamada, ainda, deverá pagar o valor de sua cota-parte no INSS, a saber, ${xxx()}, para ${xxx()}.</p>`;
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Para as deduções fiscais de Imposto de Renda, fixadas em ${xxx()} para ${xxx()}, observem-se a Súmula 368 do TST e IN RFB 1500/2014.</p>`;
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Honorários advocatícios sucumbenciais pela reclamada, no importe de ${xxx()}, para ${xxx()}.</p>`;
                    if ($('chk-hon-reu').checked) {
                        text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Não foram arbitrados honorários ao advogado do réu.</p>`;
                    } else {
                        const rdHonReu = document.querySelector('input[name="rad-hon-reu"]:checked').value;
                        if (rdHonReu === 'suspensiva') {
                            text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Honorários advocatícios pela reclamante sob condição suspensiva, diante da gratuidade deferida.</p>`;
                        } else {
                            text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Honorários advocatícios sucumbenciais em favor da reclamada na ordem de ${xxx()}.</p>`;
                        }
                    }
                    return;
                }

                if (ignorarInss) {
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Pela natureza do crédito, não há contribuições previdenciárias devidas.</p>`;
                } else {
                    const valInssRecStr = $('val-inss-rec').value || '0';
                    const valInssTotalStr = $('val-inss-total').value || '0';
                    const valInssRec = parseMoney(valInssRecStr);
                    const valInssTotal = parseMoney(valInssTotalStr);
                    let valInssReclamadaStr = valInssTotalStr;
                    if ($('calc-origem').value === 'pjecalc') {
                        const recResult = valInssTotal - valInssRec;
                        valInssReclamadaStr = formatMoney(recResult);
                    }
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">A reclamada deverá pagar o valor de sua cota-parte no INSS, a saber, ${bold(valInssReclamadaStr)}, para ${bold(valData)}.</p>`;
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Desde já, ficam autorizados os descontos previdenciários (cota do reclamante) ora fixados em ${bold('R$' + valInssRecStr)}, para ${bold(valData)}, devendo, para as retenções, serem observados os termos da Súmula 368, C. TST e da Instrução Normativa RFB nº 1.500, de 29/10/2014.</p>`;
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Os valores relativos às contribuições previdenciárias devidas em decorrência de decisões proferidas pela Justiça do Trabalho a partir de 1º de outubro de 2023, inclusive acordos homologados, devem ser recolhidos pelo(a) reclamado(a) por meio da DCTF-Web, depois de serem informados os dados da reclamatória trabalhista no e-Social. Atente-se que os registros no e-Social serão feitos por meio dos eventos: "S-2500 - Processos Trabalhistas" e "S-2501 - Informações de Tributos Decorrentes de Processo Trabalhista".</p>`;
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Nos casos em que os recolhimentos forem efetuados diretamente pela Justiça do Trabalho, o reclamado deverá enviar através do e-Social somente o evento "S-2500 – Processos Trabalhistas".</p>`;
                }

                if ($('irpf-tipo').value === 'isento') {
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Não há deduções fiscais cabíveis.</p>`;
                } else {
                    const vBase = $('val-irpf-base').value || '[VALOR]';
                    if ($('calc-origem').value === 'pjecalc') {
                        const vMes = $('val-irpf-meses').value || '[X]';
                        text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Ficam autorizados os descontos fiscais, calculados sobre as verbas tributáveis (${bold('R$' + vBase)}), pelo período de ${bold(vMes + ' meses')}.</p>`;
                    } else {
                        text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Para as deduções fiscais de Imposto de Renda, fixadas em ${bold('R$' + vBase)} para ${bold(valData)}, observem-se a Súmula 368 do TST e IN RFB 1500/2014.</p>`;
                    }
                }

                if (!$('ignorar-hon-autor').checked) {
                    const vHonA = normalizeMoneyInput($('val-hon-autor').value || '[VALOR]');
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Honorários advocatícios sucumbenciais pela reclamada, no importe de ${bold(vHonA)}, para ${bold(valData)}.</p>`;
                }

                if ($('chk-hon-reu').checked) {
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Não foram arbitrados honorários ao advogado do réu.</p>`;
                } else {
                    const tipoHonReu = document.querySelector('input[name="rad-hon-reu-tipo"]:checked').value;
                    const temSuspensiva = $('chk-hon-reu-suspensiva').checked;

                    if (tipoHonReu === 'percentual') {
                        const p = $('val-hon-reu-perc').value;
                        if (temSuspensiva) {
                            text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Honorários advocatícios pela reclamante sob condição suspensiva, na ordem de ${bold(p)}, diante da gratuidade deferida.</p>`;
                        } else {
                            text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Honorários advocatícios sucumbenciais em favor da reclamada na ordem de ${bold(p)}, a serem descontados do crédito do autor.</p>`;
                        }
                    } else {
                        const vHonR = normalizeMoneyInput($('val-hon-reu').value || '[VALOR]');
                        if (temSuspensiva) {
                            text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Honorários advocatícios pela reclamante sob condição suspensiva, no importe de ${bold(vHonR)}, para ${bold(valData)}, diante da gratuidade deferida.</p>`;
                        } else {
                            text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Honorários advocatícios sucumbenciais em favor da reclamada, no importe de ${bold(vHonR)}, para ${bold(valData)}, a serem descontados do crédito do autor.</p>`;
                        }
                    }
                }
            };

            // Função unificada para liberação detalhada (depósito recursal ou pagamento antecipado)
            const gerarLiberacaoDetalhada = (contexto) => {
                const { prefixo = '', depositoInfo = '' } = contexto;

                // Linha inicial com referência à planilha
                text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Passo à liberação de valores conforme planilha #${bold(idPlanilha)}:</p>`;

                let numLiberacao = 1;

                // 1) Crédito do reclamante
                if (depositoInfo) {
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">${numLiberacao}) Libere-se ao reclamante ${depositoInfo}, no valor de ${bold('R$' + valCredito)}, expedindo-se alvará eletrônico.</p>`;
                } else {
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">${numLiberacao}) Libere-se ao reclamante seu crédito, no valor de ${bold('R$' + valCredito)}, expedindo-se alvará eletrônico.</p>`;
                }
                numLiberacao++;

                // 2) INSS (se não ignorado)
                if (!ignorarInss) {
                    const valInssRec = normalizeMoneyInput($('val-inss-rec').value || '0,00');
                    const valInssTotal = normalizeMoneyInput($('val-inss-total').value || '0,00');

                    // Calcular INSS patronal
                    const isPjeCalc = $('calc-pjc').checked;
                    let inssEmpregado = valInssRec; // parte empregado - sempre valor do reclamante
                    let inssPatronal = valInssTotal; // parte patronal/reclamada

                    // Se é PJC: patronal = total - empregado
                    if (isPjeCalc && valInssTotal && valInssRec) {
                        const totalNum = parseMoney(valInssTotal);
                        const recNum = parseMoney(valInssRec);
                        const patronalNum = totalNum - recNum;
                        inssPatronal = formatMoney(patronalNum);
                    }
                    // Se não é PJC: usa direto o valInssTotal

                    const totalInss = valInssTotal;
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">${numLiberacao}) Proceda a Secretaria à transferência de valores ao órgão competente, via Siscondj, sendo: ${bold('R$ ' + inssEmpregado)} referente às contribuições previdenciárias parte empregado e ${bold('R$ ' + inssPatronal)} no que concernem às contribuições patronais (total de ${bold('R$ ' + totalInss)}).</p>`;
                    numLiberacao++;
                }

                // 3) Honorários periciais (se houver)
                const peritoContabilDetectado = (window.hcalcPeritosDetectados || []).find((nome) => isNomeRogerio(nome));
                const valorPeritoContabil = $('val-perito-contabil-valor')?.value || '';

                // Perito contábil (Rogério) - se houver
                if (peritoContabilDetectado && valorPeritoContabil) {
                    const vContabil = normalizeMoneyInput(valorPeritoContabil);
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">${numLiberacao}) Libere-se ao perito ${bold(peritoContabilDetectado)} seus honorários, no valor de ${bold('R$' + vContabil)}.</p>`;
                    numLiberacao++;
                }

                // Peritos de conhecimento - se houver
                const peritosConhecimentoDetectados = window.hcalcPeritosConhecimentoDetectados || [];
                const nomesInputConhecimento = ($('val-perito-nome').value || '')
                    .split(/\||,|;|\n/g)
                    .map((n) => n.trim())
                    .filter(Boolean);
                const nomesConhecimento = peritosConhecimentoDetectados.length
                    ? peritosConhecimentoDetectados
                    : nomesInputConhecimento;

                const valorPeritoConh = $('val-perito-valor')?.value || '';
                const tipoPagPericia = $('perito-tipo-pag')?.value || 'reclamada';

                if ($('chk-perito-conh').checked && nomesConhecimento.length > 0 && valorPeritoConh) {
                    nomesConhecimento.forEach((nomePerito) => {
                        if (tipoPagPericia !== 'trt') {
                            const vP = normalizeMoneyInput(valorPeritoConh);
                            text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">${numLiberacao}) Libere-se ao perito ${bold(nomePerito)} seus honorários, no valor de ${bold('R$' + vP)}.</p>`;
                            numLiberacao++;
                        }
                    });
                }

                // 4) Honorários do advogado do autor (se não ignorado)
                if (!$('ignorar-hon-autor').checked) {
                    const vHonA = normalizeMoneyInput($('val-hon-autor').value || '[VALOR]');
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">${numLiberacao}) Libere-se ao patrono da parte autora seus honorários, no valor de ${bold('R$' + vHonA)}.</p>`;
                    numLiberacao++;
                }

                // Retornar o número da próxima liberação (para devolução)
                return numLiberacao;
            };

            const appendDisposicoesFinais = () => {
                text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;"><strong>Disposições finais:</strong></p>`;

                // CONTÁBIL PRIMEIRO (Rogério)
                const peritoContabilDetectado = (window.hcalcPeritosDetectados || []).find((nome) => isNomeRogerio(nome));
                const valorPeritoContabil = $('val-perito-contabil-valor')?.value || '';
                if (peritoContabilDetectado && valorPeritoContabil) {
                    const vContabil = normalizeMoneyInput(valorPeritoContabil);
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Honorários contábeis em favor de ${bold(peritoContabilDetectado)}, ora arbitrados em ${bold(vContabil)}.</p>`;
                }

                // CONHECIMENTO DEPOIS
                const peritosConhecimentoDetectados = window.hcalcPeritosConhecimentoDetectados || [];
                const nomesInputConhecimento = ($('val-perito-nome').value || '')
                    .split(/\||,|;|\n/g)
                    .map((n) => n.trim())
                    .filter(Boolean);
                const nomesConhecimento = peritosConhecimentoDetectados.length
                    ? peritosConhecimentoDetectados
                    : nomesInputConhecimento;

                if ($('chk-perito-conh').checked && nomesConhecimento.length > 0) {
                    const vP = $('val-perito-valor').value || '[VALOR/ID]';
                    const dtP = $('val-perito-data').value || $('val-data').value || '[DATA]';
                    const tipoPagPericia = $('perito-tipo-pag').value;

                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Honorários periciais da fase de conhecimento assim estabelecidos:</p>`;

                    nomesConhecimento.forEach((nomePerito) => {
                        if (tipoPagPericia === 'trt') {
                            text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">- Em favor de ${bold(nomePerito)}, pagos pelo TRT, considerando a sucumbência do autor no objeto da perícia (#${bold(vP)}).</p>`;
                        } else {
                            text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">- Em favor de ${bold(nomePerito)}, pagamento de ${bold('R$' + vP)} pela reclamada, para ${bold(dtP)}.</p>`;
                        }
                    });
                }

                if ($('custas-status').value === 'pagas') {
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Custas pagas em razão de recurso.</p>`;
                } else {
                    const valC = $('val-custas').value || '[VALOR]';
                    const origemCustas = $('custas-origem').value;

                    if (valC && valC !== '0,00' && valC !== '0') {
                        if (origemCustas === 'acordao') {
                            // Custas por acórdão (inclui ID do acórdão no texto)
                            const acordaoIdx = $('custas-acordao-select').value;
                            const acordaoSel = $('custas-acordao-select').selectedOptions[0];
                            const dataAcordao = acordaoSel?.dataset?.data || '[DATA ACÓRDÃO]';
                            const idAcordao = acordaoSel?.dataset?.id || '';
                            const idTexto = idAcordao ? ` #${bold(idAcordao)}` : '';
                            text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Custas definidas em acórdão${idTexto}, pela reclamada, no valor de ${bold('R$' + valC)} para ${bold(dataAcordao)}.</p>`;
                        } else {
                            // Custas por sentença (padrão)
                            const dataCustas = $('custas-data-origem').value || valData;
                            text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Custas de ${bold('R$' + valC)} pela reclamada, para ${bold(dataCustas)}.</p>`;
                        }
                    }
                }

                // ==========================================
                // DEPÓSITOS RECURSAIS (múltiplos)
                // ==========================================
                if ($('chk-deposito').checked) {
                    const passivoDetectado = (window.hcalcPartesData?.passivo || []).map((p) => p?.nome).filter(Boolean);
                    const primeiraReclamada = passivoDetectado[0] || '';
                    const tipoRespAtual = $('resp-tipo')?.value || 'unica';

                    // Coletar todos os depósitos válidos (não removidos)
                    const depositosValidos = window.hcalcState.depositosRecursais
                        .filter(d => !d.removed)
                        .map(d => {
                            const idx = d.idx;
                            const tDep = $(`dep-tipo-${idx}`)?.value || 'bb';
                            const dNome = $(`dep-depositante-${idx}`)?.value || '[RECLAMADA]';
                            const dId = $(`dep-id-${idx}`)?.value || '[ID]';
                            let isPrin = $(`dep-principal-${idx}`)?.checked ?? true;
                            const liberacao = document.querySelector(`input[name="rad-dep-lib-${idx}"]:checked`)?.value || 'reclamante';

                            const isDepositoJudicial = tDep !== 'garantia';
                            let criterioLiberacaoDeposito = 'manual';
                            let depositanteResolvida = dNome;

                            // Auto-resolver depositante baseado em partes detectadas
                            if (passivoDetectado.length === 1) {
                                depositanteResolvida = passivoDetectado[0];
                                isPrin = true;
                                criterioLiberacaoDeposito = 'reclamada-unica';
                            } else if (tipoRespAtual === 'subsidiarias' && primeiraReclamada && isPrin) {
                                depositanteResolvida = primeiraReclamada;
                                criterioLiberacaoDeposito = 'subsidiaria-principal';
                            } else if (tipoRespAtual === 'solidarias') {
                                // Solidárias: qualquer depósito pode ser liberado
                                depositanteResolvida = depositanteResolvida || primeiraReclamada || '[RECLAMADA]';
                                isPrin = true; // Forçar como principal (todas são principais em solidária)
                                criterioLiberacaoDeposito = 'solidaria';
                            }

                            const deveLiberarDeposito = isDepositoJudicial && (
                                criterioLiberacaoDeposito === 'reclamada-unica' ||
                                criterioLiberacaoDeposito === 'subsidiaria-principal' ||
                                criterioLiberacaoDeposito === 'solidaria' ||
                                (criterioLiberacaoDeposito === 'manual' && isPrin)
                            );

                            const naturezaDevedora = criterioLiberacaoDeposito === 'solidaria'
                                ? 'solidária'
                                : (isPrin ? 'principal' : 'subsidiária');

                            const bancoTxt = tDep === 'bb' ? 'Banco do Brasil' : (tDep === 'sif' ? 'Caixa Econômica Federal (SIF)' : 'seguro garantia regular');

                            return {
                                idx, tDep, depositanteResolvida, dId, isPrin, liberacao,
                                isDepositoJudicial, naturezaDevedora, bancoTxt, deveLiberarDeposito
                            };
                        });

                    if (depositosValidos.length === 0) {
                        text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Há depósito recursal. (Configure os dados)</p>`;
                    } else {
                        // Agrupar depósitos por depositante + tipo
                        const grupos = {};
                        depositosValidos.forEach(dep => {
                            const chave = `${dep.depositanteResolvida}|${dep.naturezaDevedora}|${dep.bancoTxt}`;
                            if (!grupos[chave]) {
                                grupos[chave] = {
                                    depositante: dep.depositanteResolvida,
                                    natureza: dep.naturezaDevedora,
                                    banco: dep.bancoTxt,
                                    depositos: [],
                                    todosGarantia: true,
                                    todosLiberacaoDireta: true
                                };
                            }
                            grupos[chave].depositos.push(dep);
                            if (dep.isDepositoJudicial) grupos[chave].todosGarantia = false;
                            if (dep.liberacao !== 'reclamante') grupos[chave].todosLiberacaoDireta = false;
                        });

                        const formatarLista = (itens) => {
                            if (!itens || itens.length === 0) { return ''; }
                            if (itens.length === 1) { return itens[0]; }
                            if (itens.length === 2) { return `${itens[0]} e ${itens[1]}`; }
                            return `${itens.slice(0, -1).join(', ')} e ${itens[itens.length - 1]}`;
                        };

                        // Gerar texto para cada grupo
                        Object.values(grupos).forEach(grupo => {
                            const ids = grupo.depositos.map(d => `${bold(d.dId)}`);
                            const idsTexto = ids.length > 1 ? `Ids ${formatarLista(ids)}` : `Id ${ids[0]}`;

                            text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Há depósito${grupo.depositos.length > 1 ? 's' : ''} recursal${grupo.depositos.length > 1 ? 's' : ''} da devedora ${grupo.natureza} (${grupo.depositante} ${idsTexto}) via ${grupo.banco}.</p>`;

                            if (grupo.todosGarantia) {
                                text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Tratando-se de seguro garantia, não há liberação imediata de valores nesta oportunidade.</p>`;
                            } else {
                                // Processar liberações
                                const depsLiberaveis = grupo.depositos.filter(d => d.deveLiberarDeposito && d.isDepositoJudicial);

                                if (depsLiberaveis.length > 0) {
                                    const depsDiretos = depsLiberaveis.filter(d => d.liberacao === 'reclamante');
                                    const depsDetalhados = depsLiberaveis.filter(d => d.liberacao === 'detalhada');

                                    if (depsDiretos.length > 0) {
                                        houveDepositoDireto = true;
                                        const txtPlural = depsDiretos.length > 1 ? 'os depósitos recursais' : 'o depósito recursal';
                                        text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Libere-se ${txtPlural} em favor do reclamante. Após, apure-se o remanescente devido.</p>`;
                                    }

                                    if (depsDetalhados.length > 0) {
                                        const idsDetalhados = depsDetalhados.map(d => `${grupo.depositante} #${bold(d.dId)}`);
                                        const listaDeps = formatarLista(idsDetalhados);

                                        houveLibecaoDetalhada = true;
                                        gerarLiberacaoDetalhada({
                                            depositoInfo: `o${depsDetalhados.length > 1 ? 's' : ''} depósito${depsDetalhados.length > 1 ? 's' : ''} recursal${depsDetalhados.length > 1 ? 'is' : ''} (${listaDeps} via ${grupo.banco})`
                                        });
                                    }
                                } else {
                                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Por ora, não há liberação automática do${grupo.depositos.length > 1 ? 's' : ''} depósito${grupo.depositos.length > 1 ? 's' : ''} recursal${grupo.depositos.length > 1 ? 'is' : ''} informado${grupo.depositos.length > 1 ? 's' : ''}.</p>`;
                                }
                            }
                        });
                    }
                }

                // ==========================================
                // PAGAMENTOS ANTECIPADOS (múltiplos)
                // ==========================================
                const isPagamentoAntecipado = $('chk-pag-antecipado').checked;
                if (isPagamentoAntecipado) {
                    const pagamentosValidos = window.hcalcState.pagamentosAntecipados
                        .filter(p => !p.removed)
                        .map(p => {
                            const idx = p.idx;
                            return {
                                idx,
                                id: $(`pag-id-${idx}`)?.value || '[ID]',
                                tipoLib: document.querySelector(`input[name="lib-tipo-${idx}"]:checked`)?.value || 'nenhum',
                                remValor: $(`lib-rem-valor-${idx}`)?.value || '',
                                remTitulo: $(`lib-rem-titulo-${idx}`)?.value || '',
                                devValor: $(`lib-dev-valor-${idx}`)?.value || ''
                            };
                        });

                    if (pagamentosValidos.length === 0) {
                        text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Realizado depósito pela reclamada. (Configure os dados)</p>`;
                    } else {
                        pagamentosValidos.forEach(pag => {
                            text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Realizado depósito pela reclamada, #${bold(pag.id)}.</p>`;

                            houveLibecaoDetalhada = true;
                            let proximoNum = gerarLiberacaoDetalhada({});

                            if (pag.tipoLib === 'devolucao') {
                                text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">${proximoNum}) Devolva-se à reclamada o valor pago a maior, no montante de ${bold('R$ ' + (pag.devValor || '[VALOR]'))}, expedindo-se o competente alvará.</p>`;
                                text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Concede-se 05 dias para manifestação das partes.</p>`;
                                text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Após, tornem conclusos para extinção da execução.</p>`;
                            } else if (pag.tipoLib === 'remanescente') {
                                text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Sem prejuízo, fica a reclamada intimada a pagar o valor remanescente de ${bold('R$ ' + (pag.remValor || '[VALOR]'))} devidos a título de ${bold(pag.remTitulo || '[TÍTULO]')}, em 15 dias, sob pena de execução.</p>`;
                                text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Cientes as partes.</p>`;
                            } else {
                                text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Concede-se 05 dias para manifestações. Silentes, cumpra-se e, após, tornem conclusos para extinção da execução.</p>`;
                            }
                        });
                    }
                }

                // INTIMAÇÕES (apenas se NÃO houver pagamento antecipado)
                if (!isPagamentoAntecipado) {
                    const formatarListaPartes = (nomes) => {
                        if (!nomes || nomes.length === 0) { return ''; }
                        if (nomes.length === 1) { return nomes[0]; }
                        if (nomes.length === 2) { return `${nomes[0]} e ${nomes[1]}`; }
                        return `${nomes.slice(0, -1).join(', ')} e ${nomes[nomes.length - 1]}`;
                    };

                    const elsOpcoes = document.querySelectorAll('.sel-modo-intimacao');
                    const grpDiario = [];
                    const grpMandado = [];
                    const grpEdital = [];

                    // Verificar se é responsabilidade subsidiária
                    const isSubsidiaria = $('resp-tipo')?.value === 'subsidiarias';

                    // Obter lista de principais (marcadas como principal)
                    const principaisSet = new Set();
                    if (isSubsidiaria) {
                        document.querySelectorAll('.chk-parte-principal:checked').forEach(chk => {
                            principaisSet.add(chk.getAttribute('data-nome'));
                        });
                    }

                    if (elsOpcoes.length > 0) {
                        elsOpcoes.forEach((sel) => {
                            const nome = sel.getAttribute('data-nome');
                            const v = sel.value;

                            // FILTRO: Se subsidiária, intima apenas principais
                            if (isSubsidiaria && !principaisSet.has(nome)) {
                                return; // Pula subsidiárias
                            }

                            if (v === 'diario') grpDiario.push(nome);
                            else if (v === 'mandado') grpMandado.push(nome);
                            else if (v === 'edital') grpEdital.push(nome);
                        });
                    } else {
                        const valManual = $('sel-intimacao-manual')?.value || 'diario';
                        const nomeManual = $('int-nome-parte-manual')?.value || '[RECLAMADA]';
                        if (valManual === 'diario') grpDiario.push(nomeManual);
                        else if (valManual === 'mandado') grpMandado.push(nomeManual);
                        else if (valManual === 'edital') grpEdital.push(nomeManual);
                    }

                    if (grpDiario.length > 0) {
                        const alvoComAdv = formatarListaPartes(grpDiario);
                        const verboComAdv = grpDiario.length > 1 ? 'Intimem-se as reclamadas' : 'Intime-se a reclamada';
                        const patronoTxt = grpDiario.length > 1 ? 'seus patronos' : 'seu patrono';
                        const tipoValores = houveDepositoDireto ? 'valores remanescentes' : 'valores acima indicados';

                        if (houveDepositoDireto) {
                            text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Após referida atualização, ${verboComAdv} ${bold(alvoComAdv)}, na pessoa de ${patronoTxt}, para que pague(m) os ${tipoValores} em 15 dias, na forma do art. 523, caput, do CPC, sob pena de penhora.</p>`;
                        } else {
                            text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">${verboComAdv} ${bold(alvoComAdv)}, na pessoa de ${patronoTxt}, para que pague(m) os ${tipoValores} em 15 dias, na forma do art. 523, caput, do CPC, sob pena de penhora.</p>`;
                        }
                    }

                    if (grpMandado.length > 0) {
                        const alvoMand = formatarListaPartes(grpMandado);
                        const verboMand = grpMandado.length > 1 ? 'Intimem-se as reclamadas' : 'Intime-se a reclamada';
                        text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">${verboMand} ${bold(alvoMand)} para pagamento dos valores acima em 48 (quarenta e oito) horas, sob pena de penhora, expedindo-se o competente ${bold("mandado")}.</p>`;
                    }

                    if (grpEdital.length > 0) {
                        const alvoEdit = formatarListaPartes(grpEdital);
                        const verboEdit = grpEdital.length > 1 ? 'Citem-se as reclamadas' : 'Cite-se a reclamada';
                        text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">${verboEdit} ${bold(alvoEdit)}, por ${bold("edital")}, para pagamento dos valores acima em 48 (quarenta e oito) horas, sob pena de penhora.</p>`;
                    }
                }
            };

            // ==========================================
            // GERAÇÃO DE TEXTO - RESPONSABILIDADES
            // ==========================================
            function gerarTextoResponsabilidades() {
                const formatarLista = (nomes) => {
                    if (nomes.length === 0) return '';
                    if (nomes.length === 1) return bold(nomes[0]);
                    if (nomes.length === 2) return `${bold(nomes[0])} e ${bold(nomes[1])}`;
                    const ultimos = nomes.slice(-2);
                    const anteriores = nomes.slice(0, -2);
                    return `${anteriores.map(n => bold(n)).join(', ')}, ${bold(ultimos[0])} e ${bold(ultimos[1])}`;
                };

                const linhasPeriodos = Array.from(document.querySelectorAll('#resp-diversos-container [id^="periodo-diverso-"]'));
                if (linhasPeriodos.length === 0) return null;

                const principalSelecionada = $('resp-devedora-principal')?.value || '1';
                const periodoCompleto = window.hcalcState.planilhaExtracaoData?.periodoCalculo || '';
                const principaisParciais = [];
                const subsidiariasComPeriodo = [];

                linhasPeriodos.forEach((linha) => {
                    const idx = linha.id.replace('periodo-diverso-', '');
                    const nomeRec = document.querySelector(`.periodo-reclamada[data-idx="${idx}"]`)?.value || '';
                    const periodoTexto = document.querySelector(`.periodo-periodo[data-idx="${idx}"]`)?.value || '';
                    const idPlanilha = document.querySelector(`.periodo-id[data-idx="${idx}"]`)?.value || '';
                    const tipoRadio = document.querySelector(`input[name="periodo-tipo-${idx}"]:checked`)?.value || 'principal';

                    // NOVO: detectar se usa mesma planilha da principal
                    const planilhaSel = document.querySelector(`.periodo-planilha-select[data-idx="${idx}"]`)?.value || 'principal';
                    const usarMesmaPlanilha = planilhaSel === 'principal';

                    // Período vazio ou igual ao período completo = integral
                    const isPeriodoIntegral = !periodoTexto || periodoTexto === periodoCompleto;

                    if (nomeRec && !isPeriodoIntegral) {
                        if (tipoRadio === 'principal') {
                            principaisParciais.push({ nome: nomeRec, periodo: periodoTexto, idPlanilha: idPlanilha || '', usarMesmaPlanilha });
                        } else {
                            subsidiariasComPeriodo.push({ nome: nomeRec, periodo: periodoTexto, idPlanilha: idPlanilha || '', usarMesmaPlanilha });
                        }
                    }
                });

                // Identificar subsidiárias integrais (reclamadas que NÃO são principais e NÃO estão em períodos)
                const principaisNomes = new Set([principalSelecionada, ...principaisParciais.map(p => p.nome)]);
                const subsidiariasComPeriodoNomes = new Set(subsidiariasComPeriodo.map(s => s.nome));
                const todasReclamadas = Array.from(document.querySelectorAll('.chk-parte-principal'))
                    .map(chk => chk.getAttribute('data-nome'))
                    .filter(n => n);

                const subsidiariasIntegrais = todasReclamadas.filter(nome =>
                    !principaisNomes.has(nome) && !subsidiariasComPeriodoNomes.has(nome)
                );

                let textoIntro = '<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Sobre a responsabilidade pelo crédito, tem-se o seguinte:</p>';
                textoIntro += '<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;"><strong>1 - Devedoras Principais:</strong></p>';
                textoIntro += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">- ${bold(principalSelecionada)} é devedora principal pelo período integral do contrato.</p>`;

                principaisParciais.forEach(prin => {
                    textoIntro += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">- ${bold(prin.nome)} também é principal, mas pelo período parcial de ${prin.periodo}.</p>`;
                });

                const todasSubsidiarias = [...subsidiariasIntegrais, ...subsidiariasComPeriodo];
                if (todasSubsidiarias.length > 0) {
                    textoIntro += '<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;"><strong>2 - Devedoras Subsidiárias:</strong></p>';

                    // Subsidiárias integrais (agrupadas)
                    if (subsidiariasIntegrais.length > 0) {
                        const listaFormatada = formatarLista(subsidiariasIntegrais);
                        const verbo = subsidiariasIntegrais.length === 1 ? 'é responsável subsidiária' : 'são responsáveis subsidiárias';
                        textoIntro += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">- ${listaFormatada} ${verbo} pelo período integral do contrato.</p>`;
                    }

                    // Subsidiárias com período específico (individuais)
                    subsidiariasComPeriodo.forEach(sub => {
                        textoIntro += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">- ${bold(sub.nome)} é responsável subsidiária pelo período de ${sub.periodo}.</p>`;
                    });
                }

                textoIntro += '<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Após isso, passo às homologações específicas:</p>';

                return {
                    textoIntro,
                    principalIntegral: principalSelecionada,
                    principaisParciais,
                    subsidiarias: todasSubsidiarias,
                    subsidiariasIntegrais,
                    subsidiariasComPeriodo,
                    todasPrincipais: [
                        { nome: principalSelecionada, periodo: 'integral', idPlanilha: '' },
                        ...principaisParciais
                    ]
                };
            }

            const linhasPeriodos = Array.from(document.querySelectorAll('#resp-diversos-container [id^="periodo-diverso-"]'));
            const usarDuplicacao = $('resp-diversos').checked && linhasPeriodos.length > 0;

            if (usarDuplicacao && passivoTotal > 1) {
                const dadosResp = gerarTextoResponsabilidades();

                if (dadosResp) {
                    const { textoIntro, todasPrincipais, subsidiariasIntegrais, subsidiariasComPeriodo } = dadosResp;
                    const principalIntegral = todasPrincipais[0];

                    text += textoIntro;

                    text += '<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;"><strong>1 - Devedoras Principais:</strong></p>';

                    todasPrincipais.forEach((prin, i) => {
                        const letra = String.fromCharCode(97 + i);
                        const labelPrin = prin.periodo === 'integral'
                            ? `${bold(prin.nome)} (Período Integral)`
                            : `${bold(prin.nome)} (${prin.periodo})`;

                        text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;"><strong>${letra}) Reclamada ${labelPrin}:</strong></p>`;

                        const idParaUsar = prin.periodo === 'integral'
                            ? idPlanilha
                            : (prin.usarMesmaPlanilha || !prin.idPlanilha ? idPlanilha : prin.idPlanilha);

                        // placeholder=false se usa mesma planilha (valores já estão no form principal)
                        // placeholder=true  se tem período parcial mas sem planilha própria nem principal
                        const usarPlaceholder = prin.periodo !== 'integral' && !prin.usarMesmaPlanilha && !prin.idPlanilha;

                        appendBaseAteAntesPericiais({
                            idCalculo: idParaUsar,
                            usarPlaceholder: usarPlaceholder,
                            reclamadaLabel: ''
                        });
                    });

                    const totalSubsidiarias = subsidiariasIntegrais.length + subsidiariasComPeriodo.length;
                    if (totalSubsidiarias > 0) {
                        text += '<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;"><strong>2 - Devedoras Subsidiárias:</strong></p>';
                        text += '<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">(Respondem apenas em caso de insuficiência patrimonial das principais)</p>';

                        let letraIdx = 0;

                        // Subsidiárias integrais (agrupadas)
                        subsidiariasIntegrais.forEach((nomeSub) => {
                            const letra = String.fromCharCode(97 + letraIdx);
                            text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">${letra}) Reclamada ${bold(nomeSub)}:</p>`;
                            text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;"><em>Subsidiária pelo período integral do contrato, com os mesmos valores definidos para a devedora principal <strong>${principalIntegral.nome}</strong>, conforme planilha <strong>${idPlanilha}</strong>.</em></p>`;
                            letraIdx++;
                        });

                        // Subsidiárias com período específico
                        subsidiariasComPeriodo.forEach((sub) => {
                            const letra = String.fromCharCode(97 + letraIdx);
                            text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;"><strong>${letra}) Reclamada ${bold(sub.nome)}</strong></p>`;

                            if (sub.usarMesmaPlanilha) {
                                // ── CASO 1: mesma planilha da principal → texto simplificado ──
                                const nomePrincipal = principalIntegral;
                                const idPrincipalUsar = idPlanilha; // val-id.value — planilha principal
                                text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">
                                    <em>Subsidiária pelo período de <strong>${sub.periodo}</strong>.
                                    Os valores são os mesmos definidos para a devedora principal
                                    <strong>${nomePrincipal}</strong>, conforme planilha <strong>${idPrincipalUsar}</strong>,
                                    não sendo necessária homologação em separado.</em></p>`;
                            } else {
                                // ── CASO 2: planilha própria carregada ou sem planilha ──
                                const idSubPlanilha = sub.idPlanilha || idPlanilha;
                                const comPlaceholder = !sub.idPlanilha; // sem planilha própria = placeholder
                                text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">
                                    <em>Subsidiária pelo período de <strong>${sub.periodo}</strong>.</em></p>`;
                                appendBaseAteAntesPericiais({
                                    idCalculo: idSubPlanilha,
                                    usarPlaceholder: comPlaceholder,
                                    reclamadaLabel: sub.nome
                                });
                            }
                            letraIdx++;
                        });
                    }
                }

                appendDisposicoesFinais();
            } else {
                let introTxt = '';
                if (isPerito && peritoEsclareceu) {
                    introTxt += `As impugnações apresentadas já foram objeto de esclarecimentos pelo Sr. Perito sob o #${bold(pecaPerito)}, nada havendo a ser reparado no laudo. Portanto, HOMOLOGO os cálculos do expert (#${bold(idPlanilha)}), `;
                } else {
                    introTxt += `Tendo em vista a concordância das partes, HOMOLOGO os cálculos apresentados pelo(a) ${u(autoria)} (#${bold(idPlanilha)}), `;
                }

                // Verificar se FGTS foi depositado (para evitar contradição)
                const fgtsTipo = isFgtsSep ? (document.querySelector('input[name="fgts-tipo"]:checked')?.value || 'devido') : 'devido';
                const fgtsJaDepositado = fgtsTipo === 'depositado';

                if (isFgtsSep && !fgtsJaDepositado) {
                    // FGTS devido (a ser recolhido)
                    introTxt += `fixando o crédito do autor em ${bold('R$' + valCredito)} relativo ao principal, e ${bold('R$' + valFgts)} relativo ao ${bold('FGTS')} a ser recolhido em conta vinculada, atualizados para ${bold(valData)}. `;
                } else if (isFgtsSep && fgtsJaDepositado) {
                    // FGTS depositado (não menciona "a ser recolhido")
                    introTxt += `fixando o crédito do autor em ${bold('R$' + valCredito)}, atualizado para ${bold(valData)}. `;
                } else {
                    introTxt += `fixando o crédito em ${bold('R$' + valCredito)}, referente ao valor principal, atualizado para ${bold(valData)}. `;
                }
                if (indice === 'adc58') {
                    if (isFgtsSep) {
                        introTxt += `A atualização foi feita na forma da Lei 14.905/2024 e da decisão da SDI-1 do C. TST (IPCA-E até a distribuição; taxa Selic até 29/08/2024, e IPCA + juros de mora a partir de 30/08/2024).`;
                    } else {
                        introTxt += `A correção monetária foi realizada pelo IPCA-E na fase pré-judicial e, a partir do ajuizamento, pela taxa SELIC (ADC 58).`;
                    }
                } else {
                    const valJuros = $('val-juros').value || '[JUROS]';
                    const dtIngresso = $('data-ingresso').value || '[DATA INGRESSO]';
                    introTxt += `Atualizáveis pela TR/IPCA-E, conforme sentença. Juros legais de ${bold('R$' + valJuros)} a partir de ${bold(dtIngresso)}.`;
                }
                text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">${introTxt}</p>`;

                // 2º parágrafo: FGTS depositado (com valor)
                if (isFgtsSep && fgtsJaDepositado) {
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;"><u>O FGTS devido, ${bold('R$' + valFgts)}, já foi depositado, portanto deduzido.</u></p>`;
                }

                if (passivoTotal > 1) {
                    if ($('resp-tipo').value === 'solidarias') {
                        text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Declaro que as reclamadas respondem de forma solidária pela presente execução.</p>`;
                    } else if ($('resp-tipo').value === 'subsidiarias') {
                        if ($('resp-integral').checked) {
                            // Obter lista de principais e subsidiárias
                            const principais = [];
                            const subsidiarias = [];

                            document.querySelectorAll('.chk-parte-principal').forEach(chk => {
                                const nome = chk.getAttribute('data-nome');
                                if (chk.checked) {
                                    principais.push(nome);
                                } else {
                                    subsidiarias.push(nome);
                                }
                            });

                            // Texto específico nomeando principais e subsidiárias
                            if (principais.length > 0 && subsidiarias.length > 0) {
                                const formatarLista = (nomes) => {
                                    if (nomes.length === 1) return bold(nomes[0]);
                                    if (nomes.length === 2) return `${bold(nomes[0])} e ${bold(nomes[1])}`;
                                    return nomes.slice(0, -1).map(n => bold(n)).join(', ') + ' e ' + bold(nomes[nomes.length - 1]);
                                };

                                const txtPrincipais = formatarLista(principais);
                                const txtSubsidiarias = formatarLista(subsidiarias);
                                const verboPrin = principais.length > 1 ? 'são devedoras principais' : 'é devedora principal';
                                const verboSub = subsidiarias.length > 1 ? 'são subsidiárias' : 'é subsidiária';

                                text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">${txtPrincipais} ${verboPrin}, ${txtSubsidiarias} ${verboSub} pelo período integral do contrato, portanto, os valores neste momento são devidos apenas pelas principais.</p>`;
                            } else {
                                // Fallback se não houver checkboxes marcados
                                text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">A primeira reclamada é devedora principal, as demais são subsidiárias pelo período integral do contrato, portanto, os valores neste momento são devidos apenas pela primeira.</p>`;
                            }
                        }
                    }
                }
                if ($('calc-origem').value === 'pjecalc' && !$('calc-pjc').checked) {
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Considerando a ausência do arquivo de origem, <u>deverá a parte apresentar novamente a planilha ora homologada, acompanhada obrigatoriamente do respectivo arquivo ${bold('.PJC')} no prazo de 05 dias</u>.</p>`;
                }
                if (ignorarInss) {
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Pela natureza do crédito, não há contribuições previdenciárias devidas.</p>`;
                } else {
                    const valInssRecStr = $('val-inss-rec').value || '0';
                    const valInssTotalStr = $('val-inss-total').value || '0';
                    const valInssRec = parseMoney(valInssRecStr);
                    const valInssTotal = parseMoney(valInssTotalStr);
                    let valInssReclamadaStr = valInssTotalStr;
                    if ($('calc-origem').value === 'pjecalc') {
                        const recResult = valInssTotal - valInssRec;
                        valInssReclamadaStr = formatMoney(recResult);
                    }
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">A reclamada deverá pagar o valor de sua cota-parte no INSS, a saber, ${bold(valInssReclamadaStr)}, para ${bold(valData)}.</p>`;
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Desde já, ficam autorizados os descontos previdenciários (cota do reclamante) ora fixados em ${bold('R$' + valInssRecStr)}, para ${bold(valData)}, devendo, para as retenções, serem observados os termos da Súmula 368, C. TST e da Instrução Normativa RFB nº 1.500, de 29/10/2014.</p>`;
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Os valores relativos às contribuições previdenciárias devidas em decorrência de decisões proferidas pela Justiça do Trabalho a partir de 1º de outubro de 2023, inclusive acordos homologados, devem ser recolhidos pelo(a) reclamado(a) por meio da DCTF-Web, depois de serem informados os dados da reclamatória trabalhista no e-Social. Atente-se que os registros no e-Social serão feitos por meio dos eventos: "S-2500 - Processos Trabalhistas" e "S-2501 - Informações de Tributos Decorrentes de Processo Trabalhista".</p>`;
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Nos casos em que os recolhimentos forem efetuados diretamente pela Justiça do Trabalho, o reclamado deverá enviar através do e-Social somente o evento "S-2500 – Processos Trabalhistas".</p>`;
                }
                if ($('irpf-tipo').value === 'isento') {
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Não há deduções fiscais cabíveis.</p>`;
                } else {
                    const vBase = $('val-irpf-base').value || '[VALOR]';
                    if ($('calc-origem').value === 'pjecalc') {
                        const vMes = $('val-irpf-meses').value || '[X]';
                        text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Ficam autorizados os descontos fiscais, calculados sobre as verbas tributáveis (${bold('R$' + vBase)}), pelo período de ${bold(vMes + ' meses')}.</p>`;
                    } else {
                        text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Para as deduções fiscais de Imposto de Renda, fixadas em ${bold('R$' + vBase)} para ${bold(valData)}, observem-se a Súmula 368 do TST e IN RFB 1500/2014.</p>`;
                    }
                }
                if (!$('ignorar-hon-autor').checked) {
                    const vHonA = normalizeMoneyInput($('val-hon-autor').value || '[VALOR]');
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Honorários advocatícios sucumbenciais pela reclamada, no importe de ${bold(vHonA)}, para ${bold(valData)}.</p>`;
                }
                if ($('chk-hon-reu').checked) {
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Não foram arbitrados honorários ao advogado do réu.</p>`;
                } else {
                    const tipoHonReu = document.querySelector('input[name="rad-hon-reu-tipo"]:checked').value;
                    const temSuspensiva = $('chk-hon-reu-suspensiva').checked;

                    if (tipoHonReu === 'percentual') {
                        const p = $('val-hon-reu-perc').value;
                        if (temSuspensiva) {
                            text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Honorários advocatícios pela reclamante sob condição suspensiva, na ordem de ${bold(p)}, diante da gratuidade deferida.</p>`;
                        } else {
                            text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Honorários advocatícios sucumbenciais em favor da reclamada na ordem de ${bold(p)}, a serem descontados do crédito do autor.</p>`;
                        }
                    } else {
                        const vHonR = normalizeMoneyInput($('val-hon-reu').value || '[VALOR]');
                        if (temSuspensiva) {
                            text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Honorários advocatícios pela reclamante sob condição suspensiva, no importe de ${bold(vHonR)}, para ${bold(valData)}, diante da gratuidade deferida.</p>`;
                        } else {
                            text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Honorários advocatícios sucumbenciais em favor da reclamada, no importe de ${bold(vHonR)}, para ${bold(valData)}, a serem descontados do crédito do autor.</p>`;
                        }
                    }
                }
                appendDisposicoesFinais();
            }

            // Linha final - OMITIR se houver liberação detalhada (depósito recursal ou pagamento antecipado)
            if (!houveLibecaoDetalhada) {
                text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">${u('Ficam as partes cientes de que qualquer questionamento acerca desta decisão, salvo erro material, será apreciado após a garantia do juízo.')}</p>`;
            }
            const blob = new Blob([text], { type: 'text/html' });
            const clipboardItem = new window.ClipboardItem({ 'text/html': blob });
            navigator.clipboard.write([clipboardItem]).then(() => {
                alert('Decisão copiada com sucesso! Vá ao editor do PJe e cole (Ctrl+V).');
                $('homologacao-overlay').style.display = 'none';
                dbg('Decisao copiada para area de transferencia com sucesso.');
            }).catch((err) => {
                alert('Erro ao copiar. O navegador pode ter bloqueado.');
                console.error(err);
                err('Falha ao copiar decisao para clipboard:', err);
            });
        };

        dbg('initializeOverlay finalizado com sucesso.');
    }

    // Expor API pública para o userscript loader
    window.hcalcInitBotao = initializeBotao;
})();
