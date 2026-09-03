// Script/alvara/siscon_consulta.js — consulta automática de dados bancários TRT2
// (porta do sis.js v1.3.0, sem a UI standalone).
//
// Regras de integração definidas pelo usuário:
//   - NÃO precisa de dados de entrada: a chamada acontece sozinha quando a
//     verba aparece (detectada na decisão OU adicionada manualmente) e quando
//     o usuário muda o destinatário/advogado do card.
//   - Caminho de busca:
//       * Advogado como destinatário → primeiro /index; se não achar, /pf
//         (INFORMANDO quando localizado apenas no segundo).
//       * A própria parte (reclamante/reclamada com CPF) → apenas /pf.
//       * Escritório → NPJ (/consulta-pj), um único domínio de busca.
//   - Ao lado dos dados existe o "link dos dados": leva à página FINAL de
//     onde os dados são extraídos (detailUrl). Quando a chamada succeeds mas
//     não retorna dados, o link aponta para a BUSCA pré-preenchida.
//   - O botão "Puxar do SISCON" permanece como fallback manual (reconsulta).

(function () {
    'use strict';

    const Alv = (window.Alv = window.Alv || {});

    const BASE = 'https://aplicacoes1.trt2.jus.br/adv-dados-bancarios-consulta';

    // ─────────────────────────────────────────────────────────────────
    // Documento
    // ─────────────────────────────────────────────────────────────────
    const onlyDigits = v => (v || '').replace(/\D+/g, '');
    const formatCpf = d => d.replace(/^(\d{3})(\d{3})(\d{3})(\d{2})$/, '$1.$2.$3-$4');
    const formatCnpj = d => d.replace(/^(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})$/, '$1.$2.$3/$4-$5');

    function normalizeDoc(v) {
        const d = onlyDigits(v);
        if (d.length === 11) return { kind: 'cpf', raw: d, display: formatCpf(d) };
        if (d.length === 14) return { kind: 'cnpj', raw: d, display: formatCnpj(d) };
        return { kind: 'invalid', raw: d, display: d };
    }

    // ─────────────────────────────────────────────────────────────────
    // Transporte (GM_xmlhttpRequest com fallback fetch)
    // ─────────────────────────────────────────────────────────────────
    function _request(details) {
        if (typeof GM_xmlhttpRequest === 'function') {
            return new Promise((resolve, reject) => {
                GM_xmlhttpRequest({
                    timeout: 30000,
                    ...details,
                    onload: resolve,
                    onerror: reject,
                    ontimeout: reject
                });
            });
        }

        // Fallback: pode falhar por CORS fora do mesmo domínio — o botão
        // "Puxar do SISCON" do card é o caminho manual nesses casos.
        return fetch(details.url, {
            method: details.method || 'GET',
            body: details.data,
            credentials: 'include'
        }).then(async r => ({ status: r.status, responseText: await r.text() }));
    }

    async function fetchViewState(url) {
        const r = await _request({ method: 'GET', url });
        const html = r.responseText || '';
        const m = html.match(/name="javax\.faces\.ViewState"\s+id="javax\.faces\.ViewState"\s+value="([^"]+)"/);
        if (!m) throw new Error('ViewState não encontrado.');
        return m[1];
    }

    function isEmptyCpf(html) {
        return /Nenhuma pessoa física encontrada\./i.test(html) || /Nenhum advogado encontrado\./i.test(html);
    }

    function isEmptyCnpj(html) {
        return /Nenhuma pessoa jurídica encontrada\./i.test(html);
    }

    // ─────────────────────────────────────────────────────────────────
    // Buscas (porta literal do sis.js)
    // ─────────────────────────────────────────────────────────────────
    async function searchCpfAsAdvogado(docDigits) {
        const url = `${BASE}/index`;
        const vs = await fetchViewState(url);

        const body = new URLSearchParams({
            formSearch: 'formSearch',
            'formSearch:tipoBusca_input': 'CPF',
            'formSearch:cpfOuOab': docDigits,
            'formSearch:j_idt39': 'formSearch:j_idt39',
            'javax.faces.partial.ajax': 'true',
            'javax.faces.source': 'formSearch:j_idt39',
            'javax.faces.partial.execute': 'formSearch:j_idt39 formSearch:tipoBusca formSearch:cpfOuOab',
            'javax.faces.partial.render': 'formSearch:resultado messages',
            'javax.faces.behavior.event': 'action',
            'javax.faces.partial.event': 'click',
            'javax.faces.ViewState': vs
        });

        const r = await _request({
            method: 'POST',
            url,
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'Faces-Request': 'partial/ajax',
                'X-Requested-With': 'XMLHttpRequest'
            },
            data: body.toString()
        });

        const txt = r.responseText || '';
        if (isEmptyCpf(txt)) return { status: 'empty' };

        const m = txt.match(/\/adv-dados-bancarios-consulta\/advogado\?id=(\d+)/);
        if (!m) throw new Error('Resposta de advogado recebida, mas nenhum ID foi encontrado.');
        return { status: 'found', detailUrl: `${BASE}/advogado?id=${m[1]}`, kind: 'cpf-adv' };
    }

    async function searchCpfAsPessoaFisica(docDigits) {
        const url = `${BASE}/consulta-pf`;
        const vs = await fetchViewState(url);

        const body = new URLSearchParams({
            formSearch: 'formSearch',
            'formSearch:cpf': docDigits,
            'formSearch:j_idt38': 'formSearch:j_idt38',
            'javax.faces.partial.ajax': 'true',
            'javax.faces.source': 'formSearch:j_idt38',
            'javax.faces.partial.execute': 'formSearch:j_idt38 formSearch:cpf',
            'javax.faces.partial.render': 'formSearch:resultado messages',
            'javax.faces.behavior.event': 'action',
            'javax.faces.partial.event': 'click',
            'javax.faces.ViewState': vs
        });

        const r = await _request({
            method: 'POST',
            url,
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'Faces-Request': 'partial/ajax',
                'X-Requested-With': 'XMLHttpRequest'
            },
            data: body.toString()
        });

        const txt = r.responseText || '';
        if (isEmptyCpf(txt)) return { status: 'empty' };

        const m = txt.match(/\/adv-dados-bancarios-consulta\/pessoa-fisica\?id=(\d+)/);
        if (!m) throw new Error('Resposta de pessoa física recebida, mas nenhum ID foi encontrado.');
        return { status: 'found', detailUrl: `${BASE}/pessoa-fisica?id=${m[1]}`, kind: 'cpf-pf' };
    }

    async function searchCnpj(docDigits) {
        const url = `${BASE}/consulta-pj`;
        const vs = await fetchViewState(url);

        const body = new URLSearchParams({
            formSearch: 'formSearch',
            'formSearch:cnpj': docDigits,
            'formSearch:j_idt37': 'formSearch:j_idt37',
            'javax.faces.partial.ajax': 'true',
            'javax.faces.source': 'formSearch:j_idt37',
            'javax.faces.partial.execute': 'formSearch:j_idt37 formSearch:cnpj',
            'javax.faces.partial.render': 'formSearch:resultado messages',
            'javax.faces.behavior.event': 'action',
            'javax.faces.partial.event': 'click',
            'javax.faces.ViewState': vs
        });

        const r = await _request({
            method: 'POST',
            url,
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'Faces-Request': 'partial/ajax',
                'X-Requested-With': 'XMLHttpRequest'
            },
            data: body.toString()
        });

        const txt = r.responseText || '';
        if (isEmptyCnpj(txt)) return { status: 'empty' };

        const m = txt.match(/\/adv-dados-bancarios-consulta\/pessoa-juridica\?id=(\d+)/);
        if (!m) throw new Error('Resposta de CNPJ recebida, mas nenhum ID foi encontrado.');
        return { status: 'found', detailUrl: `${BASE}/pessoa-juridica?id=${m[1]}`, kind: 'cnpj' };
    }

    // ─────────────────────────────────────────────────────────────────
    // Página final — de onde os dados são de fato extraídos
    // ─────────────────────────────────────────────────────────────────
    async function fetchDetail(detailUrl, kind) {
        const r = await _request({ method: 'GET', url: detailUrl });
        const html = r.responseText || '';
        const doc = new DOMParser().parseFromString(html, 'text/html');

        const getByLabel = (text) => {
            const labels = [...doc.querySelectorAll('label')];
            const label = labels.find(el => (el.textContent || '').trim() === text);
            if (!label) return '';
            const span = label.parentElement ? label.parentElement.querySelector('span.readonly') : null;
            return (span ? span.textContent : '').trim();
        };

        if (kind === 'cnpj') {
            return {
                nome: getByLabel('Razão Social'),
                documento: getByLabel('CNPJ:'),
                banco: getByLabel('Banco:'),
                tipo: getByLabel('Tipo:'),
                agencia: getByLabel('Agência:'),
                conta: getByLabel('Conta:')
            };
        }

        return {
            nome: getByLabel('Nome:'),
            documento: getByLabel('CPF:'),
            banco: getByLabel('Banco:'),
            tipo: getByLabel('Tipo:'),
            agencia: getByLabel('Agência:'),
            conta: getByLabel('Conta:')
        };
    }

    function buildSearchLink(kind, docDigits) {
        const q = encodeURIComponent(docDigits);
        if (kind === 'cpf-adv') return `${BASE}/index?doc=${q}&origem=advogado`;
        if (kind === 'cpf-pf') return `${BASE}/consulta-pf?doc=${q}&origem=pessoa-fisica`;
        return `${BASE}/consulta-pj?doc=${q}`;
    }

    // ─────────────────────────────────────────────────────────────────
    // Modo de busca por card (regras do usuário)
    // ─────────────────────────────────────────────────────────────────
    function _modoDoCard(card) {
        const destino = (card.querySelector('[data-field="destinoTipo"]')?.value || '');
        const docInput = card.querySelector('[data-field="destinatarioDocumento"]');
        const norm = normalizeDoc(docInput ? docInput.value : '');

        // Escritório → NPJ (/consulta-pj), um único domínio.
        if (/escrit[oó]rio/i.test(destino)) {
            return { modo: 'cnpj', norm, parte: false };
        }

        // Advogado/procurador como destinatário → /index primeiro, depois /pf.
        if (/advogado|procurador/i.test(destino)) {
            return { modo: 'advogado', norm, parte: false };
        }

        // A própria parte (reclamante/reclamada com documento) → apenas /pf
        // (CPF) ou /consulta-pj (CNPJ). Nunca busca no /index.
        return { modo: 'parte', norm, parte: true };
    }

    async function _consultarPorModo(modo, norm) {
        if (norm.kind === 'cnpj') {
            const r = await searchCnpj(norm.raw);
            if (r.status === 'empty') {
                return { status: 'empty', origem: 'CNPJ (/consulta-pj)', searchLink: buildSearchLink('cnpj', norm.raw) };
            }
            return { status: 'found', origem: 'CNPJ (/consulta-pj)', detailUrl: r.detailUrl, kind: r.kind };
        }

        // Todo CPF segue a mesma ordem de endpoints, independentemente de ser
        // parte, advogado ou procurador no card.
        if (norm.kind === 'cpf') {
            const adv = await searchCpfAsAdvogado(norm.raw);

            if (adv.status === 'found') {
                return { status: 'found', origem: 'Advogado (/index)', detailUrl: adv.detailUrl, kind: adv.kind };
            }

            // Não achou no /index → cai para /pf e INFORMA.
            const pf = await searchCpfAsPessoaFisica(norm.raw);
            if (pf.status === 'empty') {
                return {
                    status: 'empty',
                    origem: 'Advogado (/index) e Pessoa Física (/pf)',
                    searchLink: buildSearchLink('cpf-pf', norm.raw)
                };
            }
            return {
                status: 'found',
                origem: 'Pessoa Física (/pf)',
                atencao: 'Não localizado como advogado (/index); encontrado apenas como pessoa física (/pf).',
                detailUrl: pf.detailUrl,
                kind: pf.kind
            };
        }

        // modo 'parte' com CPF → somente /pf (nunca /index).
        const pf = await searchCpfAsPessoaFisica(norm.raw);
        if (pf.status === 'empty') {
            return { status: 'empty', origem: 'Pessoa Física (/pf)', searchLink: buildSearchLink('cpf-pf', norm.raw) };
        }
        return { status: 'found', origem: 'Pessoa Física (/pf)', detailUrl: pf.detailUrl, kind: pf.kind };
    }

    // ─────────────────────────────────────────────────────────────────
    // Consulta por card (memo + UI + autopreenchimento)
    // ─────────────────────────────────────────────────────────────────
    const _memo = new Map();

    function _chave(card) {
        const doc = onlyDigits(card.querySelector('[data-field="destinatarioDocumento"]')?.value || '');
        const modo = _modoDoCard(card).modo;
        return `${card.dataset.itemId}|${modo}|${doc}`;
    }

    function _garantirLinha(card) {
        let row = card.querySelector('[data-consulta]');
        if (row) return row;

        row = document.createElement('div');
        row.className = 'pje-alvara-consulta';
        row.setAttribute('data-consulta', 'true');
        row.innerHTML = `
            <span data-consulta-status class="muted">Dados bancários: aguardando consulta…</span>
            <a data-consulta-link href="#" target="_blank" rel="noopener" style="display:none">link dos dados</a>
        `;

        const dados = card.querySelector('.pje-alvara-dados');
        if (dados) {
            dados.appendChild(row);
        } else {
            card.appendChild(row);
        }

        return row;
    }

    function _status(card, texto, cls) {
        const row = _garantirLinha(card);
        const el = row.querySelector('[data-consulta-status]');
        if (el) {
            el.className = cls || 'muted';
            el.textContent = texto;
        }
    }

    function _link(card, url, texto) {
        const row = _garantirLinha(card);
        const a = row.querySelector('[data-consulta-link]');
        if (!a) return;
        if (url) {
            a.href = url;
            a.textContent = texto || 'link dos dados';
            a.style.display = 'inline';
        } else {
            a.style.display = 'none';
        }
    }

    function _preencherCampos(card, data) {
        const set = (sel, val) => {
            const input = card.querySelector(sel);
            if (input && val && !input.value.trim()) input.value = val;
        };

        // Nome/documento só se estiverem vazios (mantêm editáveis).
        set('[data-field="destinatarioNome"]', data.nome);
        set('[data-field="destinatarioDocumento"]', data.documento);

        // Banco/agência/conta/tipo: autopreenchidos e SEGUEM editáveis.
        set('[data-field="banco"]', data.banco);
        set('[data-field="agencia"]', data.agencia);
        set('[data-field="conta"]', data.conta);
        set('[data-field="tipoConta"]', data.tipo);
    }

    async function consultarCard(card, opts) {
        opts = opts || {};
        const forcar = opts.forcar === true;
        const { modo, norm } = _modoDoCard(card);
        const chave = _chave(card);

        if (!forcar && _memo.has(chave)) {
            const memo = _memo.get(chave);
            _aplicarResultado(card, memo);
            return memo;
        }

        if (norm.kind === 'invalid') {
            const resultado = {
                status: 'error',
                message: modo === 'cnpj'
                    ? 'CNPJ do escritório não disponível — preencha manualmente ou use a busca.'
                    : 'Documento do destinatário ausente ou inválido para a consulta.'
            };
            _aplicarResultado(card, resultado);
            return resultado;
        }

        _status(card, 'Consultando dados bancários…', 'muted');

        try {
            const resultado = await _consultarPorModo(modo, norm);

            // Encontrou registro → busca a página de detalhe e extrai
            // nome/documento/banco/agência/conta/tipo para o autopreenchimento.
            if (resultado.status === 'found') {
                resultado.data = await fetchDetail(
                    resultado.detailUrl,
                    resultado.kind
                );
            }

            _memo.set(chave, resultado);
            _aplicarResultado(card, resultado);
            return resultado;
        } catch (error) {
            const resultado = {
                status: 'error',
                message: (error && error.message) || String(error)
            };
            _aplicarResultado(card, resultado);
            return resultado;
        }
    }

    function _salvarDadosNoEstado(card, data) {
        const estado = Alv.estado.carregarEstado();

        if (!estado || !Array.isArray(estado.itens)) return;

        const item = estado.itens.find(i => i.id === card.dataset.itemId);

        if (!item) return;

        // Merge: só preenche o que estiver vazio — campos seguem editáveis.
        item.dados = item.dados || {};
        if (data.banco && !item.dados.banco) item.dados.banco = data.banco;
        if (data.agencia && !item.dados.agencia) item.dados.agencia = data.agencia;
        if (data.conta && !item.dados.conta) item.dados.conta = data.conta;
        if (data.tipo && !item.dados.tipoConta) item.dados.tipoConta = data.tipo;
        if (!item.destinatarioNome && data.nome) item.destinatarioNome = data.nome;
        if (!item.destinatarioDocumento && data.documento) {
            item.destinatarioDocumento = data.documento;
        }

        Alv.estado.salvarEstado(estado);
    }

    function _aplicarResultado(card, resultado) {
        if (resultado.status === 'found') {
            _preencherCampos(card, resultado.data || {});
            _salvarDadosNoEstado(card, resultado.data || {});
            _status(
                card,
                'Dados carregados — origem: ' + resultado.origem +
                (resultado.atencao ? ' — ATENÇÃO: ' + resultado.atencao : ''),
                'ok'
            );
            _link(card, resultado.detailUrl, 'link dos dados');
            return;
        }

        if (resultado.status === 'empty') {
            _status(
                card,
                'Nenhum dado cadastrado no SISCON (' + resultado.origem + ').',
                'warn'
            );
            _link(card, resultado.searchLink, 'abrir busca com o documento preenchido');
            return;
        }

        _status(
            card,
            'Falha na consulta automática — use "Puxar do SISCON" ou o link: ' +
            (resultado.message || 'erro desconhecido'),
            'erro'
        );
        _link(card, buildSearchLink('cpf-adv', ''), 'abrir busca');
    }

    // ─────────────────────────────────────────────────────────────────
    // API pública
    // ─────────────────────────────────────────────────────────────────

    // Chamada quando o overlay abre (verbas detectadas) e quando uma verba
    // é adicionada manualmente. Consulta apenas os cards aplicáveis.
    function inicializar(estado) {
        const overlay = document.getElementById('pje-alvara-overlay');
        if (!overlay) return;

        overlay.querySelectorAll('[data-alvara-card]').forEach(card => {
            const destino = (card.querySelector('[data-field="destinoTipo"]')?.value || '');
            const aplicavel =
                /advogado|procurador|escrit[oó]rio|reclamante|reclamada/i.test(destino);

            if (aplicavel) {
                consultarCard(card, { forcar: false });
            }
        });
    }

    // Reconsulta um card (troca de destinatário/advogado ou fallback manual).
    function consultarNoCard(card, forcar) {
        return consultarCard(card, { forcar: forcar === true });
    }

    // Consulta unitária para consumidores externos, como o painel de AUD.
    // Reutiliza a mesma busca do overlay de alvará e devolve o detalhe bancário.
    async function consultarDocumento(documento) {
        const norm = normalizeDoc(documento);
        if (norm.kind === 'invalid') {
            throw new Error('Informe um CPF com 11 números ou CNPJ com 14 números.');
        }

        // CPF: primeiro procura como advogado em /index; se não encontrar,
        // cai para pessoa física em /consulta-pf. CNPJ segue /consulta-pj.
        const resultado = await _consultarPorModo(norm.kind === 'cpf' ? 'advogado' : 'parte', norm);
        if (resultado.status === 'empty') {
            return resultado;
        }

        resultado.data = await fetchDetail(resultado.detailUrl, resultado.kind);
        return resultado;
    }

    Alv.siscon = {
        BASE,
        consultarCard,
        consultarNoCard,
        inicializar,
        buildSearchLink,
        normalizeDoc,
        consultarDocumento
    };
})();
