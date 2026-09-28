'use strict';
// lista.pgto.js v0.5.0

// ── Partes/peritos via API (mesma fonte de hcalc-prep / Alv.dados) ──
function _pgXsrf() {
    const c = document.cookie.split(';').map(s => s.trim())
        .find(s => s.toLowerCase().startsWith('xsrf-token='));
    return c ? decodeURIComponent(c.split('=').slice(1).join('=')) : '';
}
async function _pgGet(url) {
    const h = { 'Accept': 'application/json', 'X-Grau-Instancia': '1' };
    const x = _pgXsrf(); if (x) h['X-XSRF-TOKEN'] = x;
    const resp = await fetch(url, { method: 'GET', credentials: 'include', headers: h });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}: ${url}`);
    return JSON.parse(await resp.text());
}
// Nomes que contam como match na descrição do mandado de pagamento:
// autor, advogado do autor e perito. Outros não.
async function _pgNomesConferencia() {
    const m = location.pathname.match(/\/processo\/(\d+)/);
    if (!m) return [];
    const base = location.origin + '/pje-comum-api/api/processos/id/' + m[1];
    const nomes = [];
    try {
        const partes = await _pgGet(base + '/partes');
        for (const p of ((partes && partes.ATIVO) || [])) {
            if (p && p.nome) nomes.push({ nome: p.nome, papel: 'Autor' });
            for (const r of ((p && p.representantes) || [])) {
                if (r && r.nome) nomes.push({ nome: r.nome, papel: 'Advogado do autor' });
            }
        }
    } catch (e) { console.warn('[pgto] partes indisponíveis:', e.message); }
    try {
        const peritos = await _pgGet(base + '/peritos');
        for (const p of (Array.isArray(peritos) ? peritos : [])) {
            const nome = typeof p === 'string' ? p : (p && (p.nome || (p.pessoa && p.pessoa.nome)));
            if (nome) nomes.push({ nome, papel: 'Perito' });
        }
    } catch (e) { console.warn('[pgto] peritos indisponíveis:', e.message); }
    return nomes;
}

const _pgNormNome = s => (s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toUpperCase().replace(/\s+/g, ' ').trim();

// Extrai nome e valor da descrição do mandado de pagamento.
// Ex.: "(Alvará - SISCONDJ-JT - MARIA JUSCILENE BATISTA VELOSO (R$ 20.887,12))"
function _pgParseMandado(doc) {
    const t = (doc.desc || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
    const mVal = t.match(/r\$\s*([\d.]+,\d{2})/i);
    if (!mVal) return null;
    const nome = t.replace(/[()]/g, ' ')
        .replace(/r\$\s*[\d.,]+/gi, ' ')
        .replace(/^.*?\balvara\b/, ' ')
        .replace(/\b(siscondj|jt|certidao|mandado|pagamento|diverso)\b/g, ' ')
        .replace(/[-/]+/g, ' ')
        .replace(/\s+/g, ' ').trim();
    return { nome, valor: mVal[1] };
}

function _pgNomeMatch(nomeDesc, nomes) {
    const a = _pgNormNome(nomeDesc);
    if (!a || a.length < 5) return null;
    for (const n of nomes) {
        const b = _pgNormNome(n && n.nome);
        if (!b || b.length < 5) continue;
        if (a.includes(b) || b.includes(a)) return n;
    }
    return null;
}

// 'dd/mm/yy' -> número comparável (aammdd)
function _pgDataNum(d) {
    const m = (d || '').match(/(\d{2})\/(\d{2})\/(\d{2})/);
    return m ? parseInt(m[3], 10) * 10000 + parseInt(m[2], 10) * 100 + parseInt(m[1], 10) : 0;
}

// ── Beneficiário do PDF do alvará (42(1) / anexo Documento Diverso) ──
// Extração via window.pjeExtrairApi (API + pdf.js + OCR Tesseract, já @require).
// Órgãos sem registro esperado: INSS, UNIÃO, DARF, GPS. Partes com registro
// esperado: autor, perito, advogado do autor (via /partes e /peritos).
// TUDO é logado em console + window.__pgtoBenefLog p/ ajuste fino.
const _pgBenefCache = new Map(); // uid -> resultado da extração
window.__pgtoBenefLog = [];

async function _pgBeneficiario(alv) {
    if (_pgBenefCache.has(alv.id)) return _pgBenefCache.get(alv.id);
    let res;
    try {
        if (typeof window.pjeExtrairApi !== 'function') {
            res = { beneficiario: null, ok: false, erro: 'pjeExtrairApi indisponível' };
        } else {
            const ext = await window.pjeExtrairApi(alv.id);
            if (ext && ext.sucesso && ext.conteudo_bruto) {
                const m = ext.conteudo_bruto.match(/benefici[áa]rio[s]?\s*[:\-]?\s*([^\n]{3,90})/i);
                res = { beneficiario: m ? m[1].replace(/\s{2,}.*$/, '').trim() : null, ok: !!m,
                    erro: m ? null : 'campo Beneficiário não encontrado no PDF' };
            } else {
                res = { beneficiario: null, ok: false, erro: (ext && (ext.erro || ext.aviso)) || 'extração sem conteúdo' };
            }
        }
    } catch (e) {
        res = { beneficiario: null, ok: false, erro: e.message };
    }
    console.log('[pgto][beneficiario]', alv.id, JSON.stringify(res));
    _pgBenefCache.set(alv.id, res);
    return res;
}

const _PG_ORGAOS = /(inss|instituto nacional do seguro social|\buniao\b|darf|\bgps\b|fazenda nacional|receita federal)/i;

function _pgClassificaBeneficiario(benef, nomesConf) {
    if (!benef) return { conta: true, motivo: 'desconhecido' };
    if (_PG_ORGAOS.test(benef)) return { conta: true, motivo: 'órgão (INSS/UNIÃO/DARF/GPS)' };
    const quem = _pgNomeMatch(benef, nomesConf);
    if (quem) return { conta: true, motivo: quem.papel };
    return { conta: false, motivo: 'não listado' };
}

// ── Dialog de controle (não-modal, arrastável) ─────────────────
const _pgEsc = s => String(s == null ? '' : s);

window._pgFecharDialogPgto = function () {
    document.getElementById('listaPgtoDialog')?.remove();
};

function _pgArrastavel(dlg, handle) {
    let arrastando = false, sx = 0, sy = 0, ox = 0, oy = 0;
    const down = (e) => {
        if (e.target.closest('button, a, summary, input')) return;
        arrastando = true; sx = e.clientX; sy = e.clientY;
        const r = dlg.getBoundingClientRect();
        ox = r.left; oy = r.top;
        dlg.style.right = 'auto'; dlg.style.bottom = 'auto';
        e.preventDefault();
    };
    const move = (e) => {
        if (!arrastando) return;
        dlg.style.left = Math.max(4, Math.min(window.innerWidth - 80, ox + e.clientX - sx)) + 'px';
        dlg.style.top = Math.max(4, Math.min(window.innerHeight - 40, oy + e.clientY - sy)) + 'px';
    };
    const up = () => { arrastando = false; };
    handle.addEventListener('pointerdown', down);
    window.addEventListener('pointermove', move);
    window.addEventListener('pointerup', up);
    // Cleanup dos listeners quando a dialog for removida
    const obs = new MutationObserver(() => {
        if (!document.getElementById('listaPgtoDialog')) {
            window.removeEventListener('pointermove', move);
            window.removeEventListener('pointerup', up);
            obs.disconnect();
        }
    });
    obs.observe(document.documentElement, { childList: true, subtree: true });
}

function _pgRenderDialog(saidaPgto, st) {
    document.getElementById('listaPgtoDialog')?.remove();
    const corBorda = st.tudoRegistrado ? '#28a745' : '#9c27b0';
    const dlg = document.createElement('div');
    dlg.id = 'listaPgtoDialog';
    dlg.setAttribute('data-pjetools-panel', 'true');
    dlg.style.cssText = 'position:fixed;bottom:20px;left:20px;z-index:999999999;background:#fff;' +
        'border:2px solid ' + corBorda + ';border-radius:10px;box-shadow:0 10px 40px rgba(0,0,0,.28);' +
        'width:620px;max-width:95vw;max-height:75vh;overflow:auto;font-family:sans-serif;font-size:12px;' +
        'color:#222;pointer-events:auto;';

    // Header arrastável
    const hdr = document.createElement('div');
    hdr.style.cssText = 'position:sticky;top:0;background:#fff;border-bottom:1px solid #eee;' +
        'display:flex;align-items:center;gap:8px;padding:8px 12px;cursor:move;user-select:none;';
    const ttl = document.createElement('span');
    ttl.style.cssText = 'font-weight:bold;font-size:13px;color:' + corBorda + ';flex:1;';
    ttl.textContent = st.titulo;
    const btnX = document.createElement('button');
    btnX.textContent = '✕';
    btnX.style.cssText = 'background:#dc3545;color:#fff;border:none;border-radius:50%;width:22px;height:22px;cursor:pointer;';
    btnX.onclick = (e) => { e.stopPropagation(); window._pgFecharDialogPgto(); };
    hdr.append(ttl, btnX);
    dlg.appendChild(hdr);
    _pgArrastavel(dlg, hdr);

    // Resumo — cotejo da avaliação
    const resumo = document.createElement('div');
    resumo.style.cssText = 'padding:8px 12px;background:' + (st.tudoRegistrado ? '#e8f5e9' : '#fff8e1') + ';';
    resumo.innerHTML =
        '<div style="font-weight:bold;margin-bottom:4px">' +
        (st.tudoRegistrado ? '✅ Provavelmente tudo registrado' : '⚠️ Provavelmente falta registro') +
        '</div><div style="display:flex;flex-wrap:wrap;gap:12px">' +
        '<span>Alvarás (contam): <b>' + st.numAlvaras + '</b></span>' +
        '<span>Movimentos: <b>' + st.numMovs + '</b></span>' +
        '<span>Sem registro esperado: <b>' + st.numFora + '</b></span>' +
        '<span>Pendentes: <b>' + st.pendentes + '</b></span>' +
        '</div>';
    dlg.appendChild(resumo);

    // Tabela de alvarás (clique = destacar na timeline)
    const tbl = document.createElement('table');
    tbl.style.cssText = 'width:100%;border-collapse:collapse;';
    const thead = document.createElement('thead');
    const trh = document.createElement('tr');
    for (const h of ['Data', 'Id', 'Beneficiário', 'Valor esperado', 'Situação']) {
        const th = document.createElement('th');
        th.style.cssText = 'text-align:left;padding:5px 6px;border-bottom:2px solid #ddd;background:#fafafa;';
        th.textContent = h;
        trh.appendChild(th);
    }
    thead.appendChild(trh);
    tbl.appendChild(thead);
    const tbody = document.createElement('tbody');
    for (const d of saidaPgto) {
        const tr = document.createElement('tr');
        tr.style.cssText = 'border-top:1px solid #eee;cursor:pointer;';
        tr.style.backgroundColor = d.registrado ? '#e8f5e9' : (d._semRegistro ? '#f0f0f0' : '#ffebee');
        const celulas = [
            d.data || '—',
            (d.id || '').slice(0, 8),
            '', // beneficiário (montado abaixo, com motivo)
            d._valor ? 'R$ ' + d._valor : '—',
            d._label
        ];
        celulas.forEach((tx, i) => {
            const td = document.createElement('td');
            td.style.cssText = 'padding:5px 6px;vertical-align:top;';
            if (i === 2) {
                const nome = document.createElement('div');
                nome.textContent = d._benef || '(não extraído)';
                nome.style.fontWeight = d._benef ? 'bold' : 'normal';
                const sub = document.createElement('div');
                sub.textContent = (d._semRegistro ? '⚪ ' : '') + (d._motivo || '') + (d._erroExtra ? ' — ' + d._erroExtra : '');
                sub.style.cssText = 'color:#777;font-size:11px;';
                td.append(nome, sub);
            } else {
                td.textContent = _pgEsc(tx);
            }
            tr.appendChild(td);
        });
        tr.title = 'Clique para destacar o documento na timeline';
        tr.onclick = () => {
            const el = resolverElemento(d);
            if (el) {
                el.scrollIntoView({ behavior: 'smooth', block: 'center' });
                el.classList.add('pjetools-destaque');
                setTimeout(() => el?.classList.remove('pjetools-destaque'), 3000);
            }
        };
        tbody.appendChild(tr);
    }
    tbl.appendChild(tbody);
    dlg.appendChild(tbl);

    // Logs de extração (refinamento da regex de beneficiário)
    const det = document.createElement('details');
    det.style.cssText = 'margin:8px 12px 12px;';
    const sum = document.createElement('summary');
    sum.style.cursor = 'pointer';
    sum.textContent = '📜 Logs de extração (' + (window.__pgtoBenefLog || []).length + ')';
    const pre = document.createElement('div');
    pre.style.cssText = 'max-height:220px;overflow:auto;background:#f8f9fa;border:1px solid #e0e0e0;' +
        'border-radius:6px;padding:6px;font-family:monospace;font-size:11px;white-space:pre-wrap;';
    pre.textContent = (window.__pgtoBenefLog || []).map(l =>
        '[' + l.uid + '] ' + (l.data || 's/ data') + ' | benef: ' + (l.beneficiario || '(não encontrado)') +
        ' | conta: ' + (l.conta ? 'sim' : 'não') + ' (' + l.motivo + ')' +
        (l.erro ? ' | erro: ' + l.erro : '')
    ).join('\n') || '(nenhuma extração registrada)';
    det.append(sum, pre);
    dlg.appendChild(det);

    document.body.appendChild(dlg);
}

// ── Pgto ─────────────────────────────────────────────────────────
window.executarPgto = async function () {
    const btnMovimentos = document.getElementById('exibirMovimentos');
    if (btnMovimentos && btnMovimentos.getAttribute('aria-label') === 'Exibir movimentos.') {
        btnMovimentos.click();
        await sleep(1500);
    }

    // Usar docs cacheados se possível, porém sem ignorar movimentos. 
    // Como precisamos ler os movimentos DOM diretamente:
    const docs = await lerTimelineCompleta();
    const filtrados = filtrarDocs(docs);
    const alvaras = filtrados.filter(d => (d.tipo || '').toLowerCase() === 'alvarás' && d.data);

    if (alvaras.length === 0) {
        alert('Nenhum Alvará encontrado na timeline.');
        return;
    }

    // Movimentos "Efetuado pagamento" em toda a timeline (contagem global)
    const itensTimeline = Array.from(document.querySelectorAll('li.tl-item-container, .timeline-item'));
    const movimentos = itensTimeline.filter(el =>
        (el.textContent || '').includes('Efetuado o pagamento de'));

    // Mandados de pagamento registrados na leitura: descrição traz nome + valor.
    // Cada mandado com nome = autor/perito/advogado do autor exige que o próximo
    // alvará válido depois dele esteja registrado (proximidade OU valor igual).
    const nomesConf = await _pgNomesConferencia();

    // Classificação por beneficiário do PDF (42(1) / Documento Diverso).
    // Alvará só exige registro se beneficiário = autor/perito/advogado do autor
    // ou órgão (INSS/UNIÃO/DARF/GPS). Outros: fora da contagem, logados p/ ajuste.
    const classif = new Map(); // alv.id -> { conta, motivo, beneficiario, erro }
    for (const alv of alvaras) {
        const r = await _pgBeneficiario(alv);
        const c = _pgClassificaBeneficiario(r.beneficiario, nomesConf);
        classif.set(alv.id, { ...c, beneficiario: r.beneficiario, erro: r.erro });
        window.__pgtoBenefLog.push({ uid: alv.id, data: alv.data, beneficiario: r.beneficiario,
            conta: c.conta, motivo: c.motivo, erro: r.erro });
    }
    const alvarasContam = alvaras.filter(a => classif.get(a.id).conta);
    const alvarasFora = alvaras.filter(a => !classif.get(a.id).conta);

    const mandados = (docs || []).filter(d => d.tipo === 'MandadoPagamento')
        .sort((a, b) => _pgDataNum(a.data) - _pgDataNum(b.data));
    const alvarasOrd = alvarasContam.slice().sort((a, b) => _pgDataNum(a.data) - _pgDataNum(b.data));
    const valorEsperado = new Map(); // alvará.id -> valor R$ do mandado associado
    for (const mand of mandados) {
        const parsed = _pgParseMandado(mand);
        if (!parsed || !parsed.nome || !parsed.valor) continue;
        if (!_pgNomeMatch(parsed.nome, nomesConf)) continue;
        const dMand = _pgDataNum(mand.data);
        const alvo = alvarasOrd.find(a => !valorEsperado.has(a.id) && _pgDataNum(a.data) >= dMand);
        if (alvo) valorEsperado.set(alvo.id, parsed.valor);
    }

    const saidaPgto = [];
    const elements = Array.from(document.querySelectorAll('li.tl-item-container, .timeline-item'));

    for (const alv of alvaras) {
        let registrado = false;
        const elemAlv = resolverElemento(alv);
        if (elemAlv) {
            const idx = elements.indexOf(elemAlv);
            if (idx !== -1) {
                // Procurar nos itens ACIMA (newer, portanto idx menores)
                // Vamos checar os 15 itens mais recentes acima deste alvara (2 dias de margem costuma ser poucos itens)
                for (let i = idx - 1; i >= Math.max(0, idx - 15); i--) {
                    const txt = elements[i].textContent || '';
                    if (txt.includes('Efetuado o pagamento de')) {
                        registrado = true;
                        break;
                    }
                    // Opcionalmente podemos parar se acharmos outro documento com data muito maior, mas manter o range de 15 é seguro.
                }
            }
        }

        // Fora da lista de beneficiários: sem registro esperado (mas logado)
        const info = classif.get(alv.id);
        if (info && !info.conta) {
            saidaPgto.push({
                ...alv,
                _label: `⚪ ${info.beneficiario || '?'} — sem registro esperado (${info.motivo})`,
                registrado: false,
                _semRegistro: true,
                _benef: info.beneficiario,
                _motivo: info.motivo,
                _erroExtra: info.erro,
                _valor: null
            });
            continue;
        }

        // Match de registro por valor (quando há mandado associado com autor conhecido)
        const valorEsp = valorEsperado.get(alv.id);
        if (!registrado && valorEsp) {
            registrado = movimentos.some(mv => {
                const t = mv.textContent || '';
                return t.includes(valorEsp) || t.replace(/\D/g, '').includes(valorEsp.replace(/\D/g, ''));
            });
        }

        saidaPgto.push({
            ...alv,
            _label: registrado
                ? (valorEsp ? `🟢 Registrado — R$ ${valorEsp}` : '🟢 Alvará Registrado')
                : (valorEsp ? `🔴 Pendente — esperado R$ ${valorEsp}` : '🔴 Alvará Pendente'),
            registrado: registrado,
            _benef: info ? info.beneficiario : null,
            _motivo: info ? info.motivo : null,
            _erroExtra: info ? info.erro : null,
            _valor: valorEsp || null
        });
    }

    // Veredito por contagem: alvarás que exigem registro vs. movimentos de pagamento
    const numAlvaras = alvarasContam.length;
    const numFora = alvarasFora.length;
    const numMovs = movimentos.length;
    const tudoRegistrado = numAlvaras <= numMovs;
    const tituloPgto = tudoRegistrado
        ? `💸 Alvarás: ✅ ${numAlvaras} alvará(s) / ${numMovs} pagamento(s) — provavelmente tudo registrado`
        : `💸 Alvarás: ⚠️ ${numAlvaras} alvará(s) / ${numMovs} pagamento(s) — provavelmente falta registro`;

    // Dialog própria (não-modal, arrastável): cotejo completo + logs
    _pgRenderDialog(saidaPgto, {
        titulo: tituloPgto,
        tudoRegistrado,
        numAlvaras,
        numMovs,
        numFora,
        pendentes: saidaPgto.filter(d => !d.registrado && !d._semRegistro).length
    });

    showToast(tudoRegistrado
        ? `✅ ${numAlvaras} alvará(s) × ${numMovs} pagamento(s) — provavelmente tudo registrado` + (numFora ? ` (${numFora} sem registro esperado)` : '')
        : `⚠️ ${numAlvaras} alvará(s) × ${numMovs} pagamento(s) — provavelmente falta(m) ${numAlvaras - numMovs} registro(s)` + (numFora ? ` (${numFora} sem registro esperado)` : ''),
    tudoRegistrado ? '#28a745' : '#dc3545', 5000);
}
