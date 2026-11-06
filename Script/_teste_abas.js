/* ═══════════════════════════════════════════════════════════════════
   TESTE — localizar aba do navegador pelo título (IIFE para console)

   COMO TESTAR
   1. Abra 2+ abas de PJe (ex.: /detalhe de processos diferentes).
   2. Em CADA aba, cole este arquivo inteiro no console (F12) e dê Enter.
   3. Qualquer uma delas:
        PjeAbas.listar()                    // todas as abas vivas
        PjeAbas.buscar('10013')             // por trecho do título
        PjeAbas.buscar('detalhes processo') // multi-termo, sem acento/maiúsculas
        PjeAbas.focar('10013')              // pede para a aba se ativar
        PjeAbas.ajuda()                     // lembrete da API
        PjeAbas.parar()                     // desliga a aba atual

   LIMITE: o navegador não expõe a lista de abas. Isto é um registro
   cooperativo entre abas da MESMA origem (pje.trt2.jus.br):
   cada aba se anuncia no localStorage e escuta pedidos de foco.
   Uma aba SISBAJUD (outro domínio) NÃO entra neste registro —
   para cruzar domínios só com GM_setValue (versão userscript).

   FIREFOX: localizar e marcar a aba (👉 no título) funciona sempre.
   Trazer a aba para a frente por script é bloqueado pelo próprio Firefox
   (dom.disable_window_flip=true, padrão) — o pedido de foco é respondido,
   mas quem troca de aba continua sendo o usuário.
   ═══════════════════════════════════════════════════════════════════ */
(() => {
    'use strict';

    if (window.PjeAbas && window.PjeAbas._v) return;

    const VERSAO = '1.0.0';
    const PREFIXO_ABA = 'pje_abas_v1:';
    const PREFIXO_PEDIDO = 'pje_abas_pedido_v1:';
    const PREFIXO_ACK = 'pje_abas_ack_v1:';
    const BATIDA_MS = 2500;    // heartbeat de cada aba
    // Aba em segundo plano é estrangulada pelo navegador (Chrome: ~1 timer/min),
    // então o TTL precisa ser folgado. Quem fecha a aba normalmente sai pelo
    // pagehide; quem morre sem avisar é confirmado no focar() (ack/timeout).
    const TTL_MS = 180000;    // 3 min sem nenhuma batida = entrada podre
    const PARADA_MS = 15000;  // acima disso, marcada como "pode estar dormindo"

    const meuId = 'aba_' + Math.random().toString(36).slice(2, 8);
    let timer = null;
    let vivo = true;

    const normalizar = (s) => (s || '')
        .normalize('NFD').replace(/[\u0300-\u036f]/g, '')
        .toLowerCase().replace(/\s+/g, ' ').trim();

    const titulo = () => document.title || '';

    // ── registro ────────────────────────────────────────────────────
    function bater() {
        if (!vivo) return;
        try {
            localStorage.setItem(PREFIXO_ABA + meuId, JSON.stringify({
                id: meuId,
                title: titulo(),
                url: location.href,
                ts: Date.now(),
                visivel: document.visibilityState === 'visible',
                foco: document.hasFocus ? document.hasFocus() : false
            }));
        } catch (e) { /* quota/privado */ }
    }

    function sair() {
        vivo = false;
        clearInterval(timer);
        try { localStorage.removeItem(PREFIXO_ABA + meuId); } catch (e) { }
    }

    function listar() {
        const agora = Date.now();
        const abas = [];
        for (let i = 0; i < localStorage.length; i++) {
            const chave = localStorage.key(i);
            if (!chave || chave.indexOf(PREFIXO_ABA) !== 0) continue;
            let dado;
            try { dado = JSON.parse(localStorage.getItem(chave)); } catch (e) { continue; }
            if (!dado || !dado.ts) continue;
            if (agora - dado.ts > TTL_MS) {
                try { localStorage.removeItem(chave); } catch (e) { }   // faxina
                continue;
            }
            dado.eu = dado.id === meuId;
            dado.idadeMs = agora - dado.ts;
            dado.dormindo = dado.idadeMs > PARADA_MS;   // segundo plano estrangulado
            abas.push(dado);
        }
        abas.sort((a, b) => (a.eu ? -1 : b.eu ? 1 : a.title.localeCompare(b.title, 'pt-BR')));
        return abas;
    }

    // Busca por trecho do título (ou da URL). Todos os termos precisam casar.
    function buscar(termo) {
        const termos = normalizar(termo).split(' ').filter(Boolean);
        if (!termos.length) return listar();
        return listar().filter(aba => {
            const alvo = normalizar(aba.title) + ' ' + normalizar(aba.url);
            return termos.every(t => alvo.indexOf(t) > -1);
        });
    }

    // ── foco entre abas ─────────────────────────────────────────────
    function focar(idOuTermo, opcoes) {
        const opts = Object.assign({ marcar: true, timeout: 3000 }, opcoes || {});
        const alvo = idOuTermo && idOuTermo.indexOf('aba_') === 0
            ? listar().find(a => a.id === idOuTermo)
            : buscar(idOuTermo)[0];

        if (!alvo) return Promise.reject(new Error('Aba não encontrada: ' + idOuTermo));
        if (alvo.eu) { window.focus(); return Promise.resolve({ id: alvo.id, eu: true }); }

        const nonce = 'n' + Date.now() + Math.random().toString(36).slice(2, 6);
        try {
            localStorage.setItem(PREFIXO_PEDIDO + alvo.id, JSON.stringify({
                nonce, de: meuId, deTitulo: titulo(), tipo: 'focar', marcar: opts.marcar
            }));
        } catch (e) {
            return Promise.reject(e);
        }

        return new Promise(resolve => {
            const inicio = Date.now();
            const iv = setInterval(() => {
                const ack = localStorage.getItem(PREFIXO_ACK + nonce);
                if (ack) {
                    clearInterval(iv);
                    try {
                        localStorage.removeItem(PREFIXO_ACK + nonce);
                        localStorage.removeItem(PREFIXO_PEDIDO + alvo.id);
                    } catch (e) { }
                    resolve(JSON.parse(ack));
                    return;
                }
                if (Date.now() - inicio > opts.timeout) {
                    clearInterval(iv);
                    // não respondeu: entrada podre — sai da lista
                    try { localStorage.removeItem(PREFIXO_ABA + alvo.id); } catch (e) { }
                    resolve({ ok: false, motivo: 'aba nao respondeu (fechada, descartada ou em hibernacao)' });
                }
            }, 100);
        });
    }

    // ── recebimento de pedidos (nesta aba) ──────────────────────────
    let tituloOriginal = null;
    let timerTitulo = null;

    function marcarTitulo() {
        if (tituloOriginal === null) tituloOriginal = document.title;
        clearTimeout(timerTitulo);
        document.title = '👉 ' + tituloOriginal;
        timerTitulo = setTimeout(() => {
            document.title = tituloOriginal;
            tituloOriginal = null;
        }, 6000);
    }

    function aoReceberPedido(chave) {
        if (!chave || chave.indexOf(PREFIXO_PEDIDO) !== 0) return;
        if (chave !== PREFIXO_PEDIDO + meuId) return;   // não é para mim

        let pedido;
        try { pedido = JSON.parse(localStorage.getItem(chave)); } catch (e) { return; }
        if (!pedido || !pedido.nonce) return;

        let ok = false;
        try { window.focus(); ok = true; } catch (e) { ok = false; }
        if (pedido.marcar) marcarTitulo();
        bater();

        try {
            localStorage.setItem(PREFIXO_ACK + pedido.nonce, JSON.stringify({
                ok, id: meuId, title: titulo(), url: location.href,
                ativo: document.visibilityState === 'visible'
            }));
        } catch (e) { }
    }

    // ── eventos ─────────────────────────────────────────────────────
    window.addEventListener('storage', e => aoReceberPedido(e.key));
    window.addEventListener('focus', bater);
    window.addEventListener('blur', bater);
    document.addEventListener('visibilitychange', bater);
    window.addEventListener('beforeunload', sair);
    window.addEventListener('pagehide', sair);   // fechamento/navegação no Firefox

    timer = setInterval(bater, BATIDA_MS);
    bater();

    // Limpeza de pedidos/acks velhos (só de vez em quando)
    setTimeout(() => {
        const agora = Date.now();
        const lixo = [];
        for (let i = 0; i < localStorage.length; i++) {
            const k = localStorage.key(i);
            if (!k) continue;
            if (k.indexOf(PREFIXO_ACK) === 0 || k.indexOf(PREFIXO_PEDIDO) === 0) lixo.push(k);
        }
        lixo.forEach(k => { try { localStorage.removeItem(k); } catch (e) { } });
    }, 15000);

    // ── API ─────────────────────────────────────────────────────────
    function ajuda() {
        console.log(
            '%cPjeAbas ' + VERSAO + ' — abas da mesma origem',
            'font:bold 13px monospace;color:#1976d2',
            '\n  PjeAbas.listar()                     → abas vivas (id, title, url, ts)',
            '\n  PjeAbas.buscar("10013")              → filtra por trecho do título/URL',
            '\n  PjeAbas.focar("10013")               → pede foco para a aba (Promise)',
            '\n  PjeAbas.focar("10013", {marcar:true}) → foco + título com 👉',
            '\n  PjeAbas.existe("sisbajud")           → true/false',
            '\n  PjeAbas.parar()                      → desliga esta aba',
            '\n  esta aba: ' + meuId + ' — ' + titulo()
        );
        return meuId;
    }

    window.PjeAbas = {
        _v: VERSAO,
        meuId,
        listar,
        buscar,
        focar,
        existe: (termo) => buscar(termo).length > 0,
        ajuda,
        parar: sair,
        limpar: () => {
            const ks = [];
            for (let i = 0; i < localStorage.length; i++) {
                const k = localStorage.key(i);
                if (k && k.indexOf('pje_abas_') === 0) ks.push(k);
            }
            ks.forEach(k => { try { localStorage.removeItem(k); } catch (e) { } });
            bater();
            return ks.length;
        }
    };

    console.log('%c[PjeAbas] ativo nesta aba — ' + meuId + ' — "' + titulo() + '"',
        'color:#1976d2;font-weight:bold');
})();
