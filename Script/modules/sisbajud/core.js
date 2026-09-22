'use strict';

// ── Storage helpers (GM primeiro, localStorage fallback) ────────────
const _sisbSet = (typeof GM_setValue !== 'undefined')
    ? (k, v) => GM_setValue(k, JSON.stringify(v))
    : (k, v) => { try { localStorage.setItem('pjetools_' + k, JSON.stringify(v)); } catch(e) {} };

const _sisbGet = (typeof GM_getValue !== 'undefined')
    ? (k, d = null) => {
        try { const v = GM_getValue(k, d); return v != null ? (typeof v === 'string' ? JSON.parse(v) : v) : d; }
        catch(e) { return d; }
      }
    : (k, d = null) => {
        try { const v = localStorage.getItem('pjetools_' + k); return v ? JSON.parse(v) : d; }
        catch(e) { return d; }
      };

// ═══════════════════════════════════════════════════════════════════
// SISBAJUD Core - Extração e Acumulação de Dados
// Baseado em SISB/relatorios/generator.py
// ═══════════════════════════════════════════════════════════════════

/**
 * Estrutura do acumulador:
 * {
 *   executados: {
 *     'NOME|DOCUMENTO': {
 *       nome: 'Nome Executado',
 *       documento: 'CPF/CNPJ',
 *       protocolos: [
 *         {numero: '123', valor: 100.50, valor_formatado: 'R$ 100,50', erro_bloqueio: null}
 *       ],
 *       total: 100.50
 *     }
 *   },
 *   total_geral: 100.50,
 *   ordens_com_erro_bloqueio: []
 * }
 */

window.SisbCore = {
    // ── Acumulador global ────────────────────────────────────────────
    acumulador: {
        executados: {},
        total_geral: 0.0,
        ordens_com_erro_bloqueio: []
    },

    timerId: null,
    // TIMEOUT retained for compatibility but auto-reset is disabled to persist until user finalization
    TIMEOUT: 0,

    // ── Reset ────────────────────────────────────────────────────────
    reset() {
        this.acumulador = {
            executados: {},
            total_geral: 0.0,
            ordens_com_erro_bloqueio: []
        };
        if (this.timerId) {
            clearTimeout(this.timerId);
            this.timerId = null;
        }
        // persist cleared state
        try { _sisbSet('sisbajud_acumulador', this.acumulador); } catch (e) { console.warn('[SISB Core] persist reset failed', e); }
        console.log('[SISB Core] Acumulador resetado');
    },

    // ── Utilitários compartilhados de DOM e UI ───────────────────────
    sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    },

    async wait(selectorOrFn, timeoutMs = 10000) {
        const start = Date.now();
        while (Date.now() - start < timeoutMs) {
            let el = null;
            try {
                if (typeof selectorOrFn === 'function') el = selectorOrFn();
                else el = document.querySelector(selectorOrFn);
            } catch(e) { el = null; }
            if (el) return el;
            await this.sleep(200);
        }
        return null;
    },

    async click(selectorOrEl, timeoutMs = 5000) {
        const el = (typeof selectorOrEl === 'string' || typeof selectorOrEl === 'function')
            ? await this.wait(selectorOrEl, timeoutMs)
            : selectorOrEl;
        if (!el) { console.warn('[SISB] Elemento não encontrado:', selectorOrEl); return false; }
        try { el.scrollIntoView({ block: 'center', behavior: 'instant' }); } catch(e) {}
        await this.sleep(300);
        let targetToClick = el;
        if (el.tagName && el.tagName.toLowerCase() === 'mat-radio-button') {
            targetToClick = el.querySelector('label') || el.querySelector('input') || el;
        }
        if (typeof targetToClick.click === 'function') {
            targetToClick.click();
        } else if (typeof targetToClick.dispatchEvent === 'function') {
            targetToClick.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, view: window }));
        }
        return true;
    },

    preencherInput(el, valor) {
        if (!el || valor === undefined || valor === null) return;
        el.focus();
        if (typeof el.select === 'function') {
            try { el.select(); } catch(e) {}
        }
        const valStr = String(valor);
        let ok = false;
        try {
            ok = document.execCommand('insertText', false, valStr);
        } catch(e) {}
        if (!ok || el.value !== valStr) {
            try {
                const nativeSetter = Object.getOwnPropertyDescriptor(
                    window.HTMLInputElement.prototype, 'value'
                ).set;
                nativeSetter.call(el, valStr);
            } catch(e) {
                el.value = valStr;
            }
            el.dispatchEvent(new Event('input', { bubbles: true }));
        }
        el.dispatchEvent(new Event('change', { bubbles: true }));
        el.blur();
    },

    mostrarToast(mensagem, tipo = 'ok') {
        const prev = document.getElementById('pjetools-sisb-toast');
        if (prev) prev.remove();
        const toast = document.createElement('div');
        toast.id = 'pjetools-sisb-toast';
        const cores = { ok: '#28a745', erro: '#dc3545', aviso: '#ffc107' };
        const icones = { ok: '✅', erro: '❌', aviso: '⚠️' };
        toast.style.cssText = 'position:fixed;bottom:160px;right:20px;z-index:9999999;background:' + (cores[tipo] || '#333') + ';color:#fff;padding:10px 16px;border-radius:6px;font-size:13px;font-family:sans-serif;max-width:360px;box-shadow:0 4px 14px rgba(0,0,0,0.3);transition:opacity 0.3s;opacity:1;';
        toast.textContent = (icones[tipo] || '') + ' ' + mensagem;
        document.body.appendChild(toast);
        setTimeout(() => {
            toast.style.opacity = '0';
            setTimeout(() => { if (toast.parentNode) toast.remove(); }, 300);
        }, tipo === 'erro' ? 5000 : 3000);
    },

    criarBotao(id, texto, cor, onclick) {
        const btn = document.createElement('button');
        btn.id = id;
        btn.textContent = texto;
        btn.style.cssText = 'background:' + cor + ';color:#fff;border:none;border-radius:4px;padding:10px 16px;font-weight:bold;font-size:13px;cursor:pointer;box-shadow:0 3px 8px rgba(0,0,0,0.25);transition:transform 0.2s,box-shadow 0.2s;min-width:200px;text-align:left;';
        btn.onmouseover = () => { btn.style.transform = 'translateY(-2px)'; btn.style.boxShadow = '0 5px 12px rgba(0,0,0,0.35)'; };
        btn.onmouseout = () => { btn.style.transform = 'translateY(0)'; btn.style.boxShadow = '0 3px 8px rgba(0,0,0,0.25)'; };
        btn.onclick = onclick;
        return btn;
    },

    copyToClipboardHtml(content) {
        const container = document.createElement('div');
        container.innerHTML = content;
        container.style.position = 'fixed';
        container.style.pointerEvents = 'none';
        container.style.opacity = '0';
        document.body.appendChild(container);
        window.getSelection().removeAllRanges();
        const range = document.createRange();
        range.selectNode(container);
        window.getSelection().addRange(range);
        let sucesso = false;
        try {
            sucesso = document.execCommand('copy');
        } catch (err) {
            console.error('[SISB] Erro ao copiar HTML:', err);
        }
        document.body.removeChild(container);
        window.getSelection().removeAllRanges();
        return sucesso;
    },

    async resolverSenhaSisb() {
        // 2026-09-22: logins (PJe/SISBAJUD) sao manuais; servidores locais de senha
        // (server.py, senha_api.py) foram removidos por seguranca. A senha, quando
        // necessaria, fica so no GM_getValue local do Tampermonkey.
        try {
            if (typeof GM_getValue !== 'undefined') {
                let v = GM_getValue('BP_PASS') || GM_getValue('sisbajud_senha');
                if (v) return String(v);
            }
        } catch(e) {}
        return window.__sisbSenha || window.BP_PASS || '';
    },

    salvarEstado: _sisbSet,
    lerEstado: _sisbGet,


    // ── Agrupar dados (merge) ────────────────────────────────────────
    agruparDados(dados_novos) {
        if (!dados_novos || !dados_novos.executados) return;

        for (const [chave, dados_exec] of Object.entries(dados_novos.executados)) {
            // Se executado já existe, merge protocolos
            if (this.acumulador.executados[chave]) {
                const exec_acum = this.acumulador.executados[chave];

                // Adicionar todos os protocolos (extend)
                const protocolos_novos = Array.isArray(dados_exec.protocolos)
                    ? dados_exec.protocolos
                    : [dados_exec.protocolos].filter(Boolean);

                exec_acum.protocolos.push(...protocolos_novos);
                exec_acum.total += dados_exec.total || 0;
            } else {
                // Novo executado - adicionar integralmente
                this.acumulador.executados[chave] = {
                    nome: dados_exec.nome || 'Executado',
                    documento: dados_exec.documento || '',
                    protocolos: Array.isArray(dados_exec.protocolos)
                        ? [...dados_exec.protocolos]
                        : [dados_exec.protocolos].filter(Boolean),
                    total: parseFloat(dados_exec.total) || 0.0
                };
            }

            // Somar ao total geral
            this.acumulador.total_geral += dados_exec.total || 0;
        }

        // Adicionar ordens com erro (se houver)
        if (dados_novos.ordens_com_erro_bloqueio) {
            this.acumulador.ordens_com_erro_bloqueio.push(
                ...dados_novos.ordens_com_erro_bloqueio
            );
        }

        // Resetar timer
        // Persistir acumulador para sobreviver a navegações/paginas
        try { _sisbSet('sisbajud_acumulador', this.acumulador); } catch (e) { console.warn('[SISB Core] persist failed', e); }

        console.log('[SISB Core] Dados agrupados:', {
            executados: Object.keys(this.acumulador.executados).length,
            total_geral: this.acumulador.total_geral
        });
    },

    // ── Extrair dados da página SISBAJUD ─────────────────────────────
    async extrairDadosBloqueios(protocoloFornecido) {
        console.log('[SISB Core] Iniciando extração de bloqueios...');

        // Aguardar container (modal CDK, overlay teimosinha, ou página PDPJ)
        var cont = null;
        for (var tentativa = 0; tentativa < 25; tentativa++) {
            cont = document.querySelector('SISBAJUD-INCLUSAO-DESDOBRAMENTO')
                || document.querySelector('.cdk-overlay-container .mat-dialog-container')
                || document.querySelector('.container-fluid');
            if (cont) {
                // Se for overlay de teimosinha, não precisa validar "protocolo" no texto
                if (cont.tagName === 'SISBAJUD-INCLUSAO-DESDOBRAMENTO') break;
                var txt = cont.innerText || cont.textContent || '';
                if (txt.toLowerCase().indexOf('protocolo') > -1) break;
                if (txt.toLowerCase().indexOf('bloqueio') > -1 || txt.toLowerCase().indexOf('saldo') > -1) break;
            }
            await new Promise(function(r) { setTimeout(r, 600); });
        }

        if (!cont) {
            console.warn('[SISB Core] Container de dados não encontrado');
            return null;
        }

        await new Promise(function(r) { setTimeout(r, 500); });

        // Extrair protocolo (do parâmetro ou do DOM)
        var protocolo = protocoloFornecido || 'N/A';
        if (!protocoloFornecido) {
            var protoLabels = Array.from(document.querySelectorAll('.sisbajud-label')).filter(function(el) {
                return el.textContent && el.textContent.trim().toLowerCase().indexOf('protocolo') > -1;
            });
            if (protoLabels.length > 0 && protoLabels[0].nextElementSibling) {
                protocolo = protoLabels[0].nextElementSibling.textContent.trim();
            } else {
                var txtSemTags = cont.innerHTML.replace(/<[^>]+>/g, ' ');
                var matchProto = txtSemTags.match(/Número do protocolo:\s*(\d+)/i);
                if (matchProto) protocolo = matchProto[1];
            }
        }

        console.log('[SISB Core] Protocolo:', protocolo);

        // Estrutura de retorno
        const dados_bloqueios = {
            executados: {},
            total_geral: 0.0,
            ordens_com_erro_bloqueio: []
        };

        // Buscar todos os headers de executados globalmente no documento 
        const headers = document.querySelectorAll('mat-expansion-panel-header.sisbajud-mat-expansion-panel-header');

        if (!headers || headers.length === 0) {
            console.warn('[SISB Core] Nenhum header de executado encontrado');
            return dados_bloqueios;
        }

        console.log(`[SISB Core] Encontrados ${headers.length} executados`);

        // Processar cada executado
        for (let idx = 0; idx < headers.length; idx++) {
            const header = headers[idx];

            try {
                // Extrair nome
                let nome = 'Executado não identificado';
                const nomeEl = header.querySelector('.col-reu-dados-nome-pessoa');
                if (nomeEl) {
                    nome = nomeEl.textContent.trim();
                }

                // Extrair documento (CPF/CNPJ)
                let documento = '';
                const docEl = header.querySelector('.col-reu-dados a');
                if (docEl) {
                    documento = docEl.textContent.trim();
                }

                // Extrair valor bloqueado
                let valor_float = 0.0;
                let valor_texto = '';
                const valorEl = header.querySelector('.div-description-reu span');
                if (valorEl) {
                    valor_texto = valorEl.textContent.trim();

                    // Regex para extrair valor: "R$ 187,94"
                    const valorMatch = valor_texto.match(/R\$\s*([0-9.,]+)/);
                    if (valorMatch) {
                        const valorStr = valorMatch[1];
                        // Converter formato BR (1.234,56) para float
                        valor_float = parseFloat(
                            valorStr.replace(/\./g, '').replace(',', '.')
                        );
                    }
                }

                // Pular se valor for 0
                if (valor_float <= 0) {
                    console.log(`[SISB Core] Executado ${idx + 1} sem bloqueio (valor=0)`);
                    continue;
                }

                // Formatar valor
                const valor_formatado = this.formatarValor(valor_float);

                // Criar chave única
                const chave = `${nome}|${documento}`;

                // Inicializar executado se não existir
                if (!dados_bloqueios.executados[chave]) {
                    dados_bloqueios.executados[chave] = {
                        nome: nome,
                        documento: documento,
                        protocolos: [],
                        total: 0.0
                    };
                }

                // Adicionar protocolo
                dados_bloqueios.executados[chave].protocolos.push({
                    numero: protocolo,
                    valor: valor_float,
                    valor_formatado: valor_formatado,
                    erro_bloqueio: null
                });

                // Somar aos totais
                dados_bloqueios.executados[chave].total += valor_float;
                dados_bloqueios.total_geral += valor_float;

                console.log(`[SISB Core] Executado ${idx + 1}: ${nome} - ${valor_formatado}`);

            } catch (err) {
                console.error(`[SISB Core] Erro ao processar executado ${idx + 1}:`, err);
                continue;
            }
        }

        console.log('[SISB Core] Extração concluída:', {
            executados: Object.keys(dados_bloqueios.executados).length,
            total: dados_bloqueios.total_geral
        });

        return dados_bloqueios;
    },

    // ── Formatação de valores ────────────────────────────────────────
    formatarValor(valor) {
        if (!Number.isFinite(valor)) return 'R$ 0,00';

        return valor.toLocaleString('pt-BR', {
            style: 'currency',
            currency: 'BRL',
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        });
    },

    // ── Detectar erros de bloqueio ───────────────────────────────────
    detectarErroBloqueio(modal, protocolo) {
        // TODO: Implementar detecção de erros específicos
        // Exemplos: "Bloqueio indisponível", "Erro no processamento", etc.
        const texto = modal.textContent || '';

        if (texto.includes('indisponível') || texto.includes('erro')) {
            return {
                protocolo: protocolo,
                valor_esperado: 0.0,
                mensagem: 'Bloqueio indisponível'
            };
        }

        return null;
    }
};

// Carregar acumulador persistido (se existir)
try {
    const saved = _sisbGet('sisbajud_acumulador');
    if (saved && saved.executados) {
        window.SisbCore.acumulador = saved;
        console.log('[SISB Core] Acumulador carregado do storage -', Object.keys(saved.executados).length, 'executados');
    }
} catch (e) { console.warn('[SISB Core] load acumulador failed', e); }

// Registrar cleanup se disponível
if (window.PJeState && window.PJeState.registry) {
    window.PJeState.registry.add(() => {
        if (window.SisbCore.timerId) {
            clearTimeout(window.SisbCore.timerId);
        }
        // Não resetar automaticamente para preservar dados acumulados até finalização pelo usuário
    });
}

// =====================================================================
// AUTOMAÇÃO SISBAJUD (PJeTools Nativo)
// =====================================================================
window.PjeSisbajudAuto = {
    async iniciarMinuta() {
        console.log('[SisbajudAuto] Extraindo dados para Minuta...');
        let btnGuardar = document.querySelector('#maisPJe_bt_detalhes_guardarDados');
        if (btnGuardar) btnGuardar.click();

        let dados = await this.extrairDadosEssenciaisDet();
        _sisbSet('sisbajud_dados_basicos', dados);
        _sisbSet('sisbajud_acao', 'aguardando_escolha');

        console.log('[SisbajudAuto] Dados da minuta salvos:', dados);
        const msg = dados.numero ? `Dados do processo ${dados.numero} salvos!` : 'Dados do processo extraídos para Minuta!';
        if (typeof showToast === 'function') {
            showToast(msg, '#28a745', 3500);
        } else {
            alert(msg);
        }
    },

    async iniciarTeimosinha() {
        console.log('[SisbajudAuto] Extraindo dados para Teimosinha...');
        let btnGuardar = document.querySelector('#maisPJe_bt_detalhes_guardarDados');
        if (btnGuardar) btnGuardar.click();

        let dados = await this.extrairDadosEssenciaisDet();
        _sisbSet('sisbajud_dados_basicos', dados);
        _sisbSet('sisbajud_acao', 'teimosinha');

        console.log('[SisbajudAuto] Dados para Teimosinha salvos:', dados);
        if (typeof showToast === 'function') {
            showToast('Dados salvos para Teimosinha!', '#28a745', 3500);
        }
    },

    async iniciarEndereco() {
        console.log('[SisbajudAuto] Extraindo dados para Endereço...');
        let btnGuardar = document.querySelector('#maisPJe_bt_detalhes_guardarDados');
        if (btnGuardar) btnGuardar.click();

        let dados = await this.extrairDadosEssenciaisDet();
        _sisbSet('sisbajud_dados_basicos', dados);
        _sisbSet('sisbajud_acao', 'endereco');

        console.log('[SisbajudAuto] Dados para Endereço salvos:', dados);
        if (typeof showToast === 'function') {
            showToast('Dados salvos para Endereço!', '#17a2b8', 3500);
        }
    },

    _abrirAbaSisbajud() {
        let baseUrl = window.location.href.includes('cnj.jus.br') ? 'https://sisbajud.cnj.jus.br' : 'https://sisbajud.pdpj.jus.br';
        let url = baseUrl + '/minuta/cadastrar';
        setTimeout(() => {
            if (typeof GM_openInTab !== 'undefined') {
                GM_openInTab(url, { active: true });
            } else {
                window.open(url, '_blank');
            }
        }, 800);
    },

    async extrairDadosEssenciaisDet() {
        let dados = {
            numero: '',
            processo: '',
            partesPassivas: [],
            partesAtivas: [],
            valorExecucao: 0,
            juiz: 'Otavio Augusto',
            vara: '30006',
            diasTeimosinha: 30
        };

        const reCnj = /\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}/;

        // 1. Título da página
        let mTitle = (document.title || '').match(reCnj);
        if (mTitle) dados.numero = mTitle[0];

        // 2. Elementos DOM no PJe
        if (!dados.numero) {
            let seletores = [
                '.texto-numero-processo',
                '.title-case-number',
                'span.processo-numero',
                'a.numero-processo',
                'pje-cabecalho-processo',
                '[id*="numeroProcesso"]',
                'span[title*="Processo"]'
            ];
            for (let sel of seletores) {
                let el = document.querySelector(sel);
                if (el) {
                    let m = (el.textContent || '').match(reCnj);
                    if (m) {
                        dados.numero = m[0];
                        break;
                    }
                }
            }
        }

        // 3. Regex no texto visível do body
        if (!dados.numero && document.body) {
            let mBody = (document.body.innerText || '').match(reCnj);
            if (mBody) dados.numero = mBody[0];
        }

        // Pegar ID do processo da URL
        const matchId = window.location.href.match(/\/processo\/([0-9]+)\/detalhe/);
        const idProcesso = matchId ? matchId[1] : null;

        if (idProcesso) {
            try {
                // 4. API de processo se ainda não achou número
                if (!dados.numero) {
                    let urlProc = location.origin + '/pje-comum-api/api/processos/id/' + idProcesso;
                    let respProc = await fetch(urlProc, { method: 'GET', headers: { 'Content-Type': 'application/json' } });
                    if (respProc.ok) {
                        let jsonProc = await respProc.json();
                        dados.numero = jsonProc.numeroProcesso || jsonProc.numero || '';
                    }
                }

                // Buscar Partes
                let urlPartes = location.origin + '/pje-comum-api/api/processos/id/' + idProcesso + '/partes';
                let respPartes = await fetch(urlPartes, { method: 'GET', headers: { 'Content-Type': 'application/json' } });
                if (respPartes.ok) {
                    let json = await respPartes.json();
                    let shape = (lista) => (lista || []).map(p => ({ nome: (p.nome || '').trim(), cpfcnpj: (p.documento || '').replace(/[^0-9]/g, '') }));
                    dados.partesAtivas = shape(json.ATIVO);
                    dados.partesPassivas = shape(json.PASSIVO);
                }

                // Buscar Valor da Execução via GIGS
                let urlGigs = location.origin + '/pje-gigs-api/api/execucao/processo/' + idProcesso;
                let respGigs = await fetch(urlGigs, { method: 'GET', headers: { 'Content-Type': 'application/json' } });
                if (respGigs.ok) {
                    let json = await respGigs.json();
                    dados.valorExecucao = json.valor ?? json.valorExecucao ?? json.total ?? 0;
                }
                
                // Fallback de valor via Calculos API
                if (!dados.valorExecucao || dados.valorExecucao <= 0) {
                    const qs = new URLSearchParams({ idProcesso: idProcesso, pagina: '1', tamanhoPagina: '10', ordenacaoCrescente: 'true', mostrarCalculosHomologados: 'true', incluirCalculosHomologados: 'true' });
                    let urlCalc = location.origin + '/pje-comum-api/api/calculos/processo?' + qs.toString();
                    let respCalc = await fetch(urlCalc, { method: 'GET', headers: { 'Content-Type': 'application/json' } });
                    if (respCalc.ok) {
                        let json = await respCalc.json();
                        let resultado = json.resultado || [];
                        if (resultado.length > 0) {
                            let ultimo = resultado.reduce((prev, curr) => (new Date(prev.dataHoraImportacao) > new Date(curr.dataHoraImportacao) ? prev : curr));
                            dados.valorExecucao = ultimo.total ?? ultimo.valor ?? ultimo.valorExecucao ?? 0;
                        }
                    }
                }
            } catch (e) {
                console.error('[SisbAuto] Erro ao buscar dados da API:', e);
            }
        }

        // Fallback visual se API falhou para o passivo
        if (dados.partesPassivas.length === 0) {
            dados.partesPassivas = this.extrairPolosPassivosDet();
        }

        dados.processo = dados.numero;
        return dados;
    },

    extrairPolosPassivosDet() {
        if (window.PjeLibParser && typeof window.PjeLibParser.extrairPolos === 'function') {
            try {
                let p = window.PjeLibParser.extrairPolos();
                let passivo = p.passivo || p.reu || p.executado;
                if (passivo && passivo.length > 0) {
                    return passivo.map(x => ({
                        nome: x.nome, 
                        cpfcnpj: (x.cpfcnpj || x.documento || '').replace(/[^0-9]/g, '')
                    })).filter(x => x.cpfcnpj);
                }
            } catch(e) {}
        }
        
        let partes = [];
        let pText = document.body.innerText; 
        // Fallback básico, pois o PJeLibParser é esperado estar presente
        return partes;
    },

    mostrarDialogoExecutados(partes, onContinuar) {
        let overlay = document.createElement('div');
        overlay.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.5);z-index:9999999;display:flex;align-items:center;justify-content:center;';
        
        let container = document.createElement('div');
        container.style.cssText = 'text-align: inherit; font-weight: inherit; height: auto; min-width: 35vw; max-height: 80vh; display: inline-grid; background-color: white; padding: 15px; border-radius: 4px; box-shadow: rgba(0, 0, 0, 0.2) 0px 2px 1px -1px, rgba(0, 0, 0, 0.14) 0px 1px 1px 0px, rgba(0, 0, 0, 0.12) 0px 1px 3px 0px; overflow-y: auto;';
        
        let title = document.createElement('span');
        title.style.cssText = 'color: grey; border-bottom: 1px solid lightgrey; margin-bottom:10px; font-weight:bold; padding-bottom:5px;';
        title.textContent = 'Lista de Executados - clique para EXCLUIR';
        container.appendChild(title);

        let partesAtivas = [...partes];

        function renderizarLista() {
            let spans = container.querySelectorAll('.sisb-parte-item');
            spans.forEach(s => s.remove());
            partesAtivas.forEach((p, idx) => {
                let pSpan = document.createElement('span');
                pSpan.className = 'sisb-parte-item';
                pSpan.style.cssText = 'cursor: pointer; margin-top: 10px; padding: 10px; font-weight: bold; font-size: 16px; background-color: white; color: rgb(81, 81, 81); border-radius:3px; transition: background 0.2s;';
                pSpan.textContent = `${p.nome} (${p.cpfcnpj})`;
                pSpan.onmouseover = () => pSpan.style.backgroundColor = '#ffebee';
                pSpan.onmouseout = () => pSpan.style.backgroundColor = 'white';
                pSpan.onclick = () => { partesAtivas.splice(idx, 1); renderizarLista(); };
                container.insertBefore(pSpan, btnContinuar);
            });
        }

        let btnContinuar = document.createElement('button');
        btnContinuar.className = 'botaoContinuar';
        btnContinuar.textContent = 'Continuar';
        btnContinuar.style.cssText = 'margin-top:20px; padding:10px; background:#1976d2; color:white; border:none; border-radius:4px; font-size:16px; cursor:pointer; font-weight:bold;';
        btnContinuar.onclick = () => { overlay.remove(); onContinuar(partesAtivas); };

        let btnCancelar = document.createElement('button');
        btnCancelar.textContent = 'Cancelar';
        btnCancelar.style.cssText = 'margin-top:10px; padding:10px; background:#f5f5f5; color:#333; border:1px solid #ccc; border-radius:4px; font-size:14px; cursor:pointer;';
        btnCancelar.onclick = () => overlay.remove();

        container.appendChild(btnContinuar);
        container.appendChild(btnCancelar);
        overlay.appendChild(container);
        document.body.appendChild(overlay);

        renderizarLista();
    }
};
