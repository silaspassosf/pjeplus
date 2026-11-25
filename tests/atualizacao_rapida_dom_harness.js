/* Harness offline (Node, sem browser/jsdom) para o motor Fix/atualizacao_rapida.js.
 *
 * Simula a sequência de telas JSF do PJe-Calc com um DOM mínimo e uma máquina
 * de estados dirigida por cliques. Valida a lógica do fluxo (data atual, seleção
 * de cálculo, guardas de segurança e sucesso só após "Sucesso!").
 *
 * Rodar:  node tests/atualizacao_rapida_dom_harness.js   (dev-only)
 */
'use strict';
const fs = require('fs');
const path = require('path');

// relógio acelerado: timeouts avançam um clock fake e rodam via setImmediate
let _now = 0;
Date.now = () => _now;
global.setTimeout = (fn, ms) => { _now += (ms || 0); return setImmediate(fn); };
global.clearTimeout = (id) => clearImmediate(id);
global.MutationObserver = class { observe() {} disconnect() {} };
global.Event = class { constructor(type, opts) { this.type = type; this.bubbles = !!(opts && opts.bubbles); } };

// ── DOM mínimo ──
class FakeEl {
    constructor(tag) {
        this.tagName = String(tag).toUpperCase();
        this.attrs = {}; this._text = ''; this.parentElement = null;
        this.childNodes = []; this._listeners = {}; this.onclick = null;
        this.checked = false; this.alt = '';
    }
    get textContent() { return this._text; } set textContent(v) { this._text = String(v); }
    get innerText() { return this._text; } set innerText(v) { this._text = String(v); }
    hasAttribute(n) { return n in this.attrs; }
    getAttribute(n) { return this.attrs[n]; }
    setAttribute(n, v) { this.attrs[n] = String(v); }
    addEventListener(t, fn) { (this._listeners[t] = this._listeners[t] || []).push(fn); }
    dispatchEvent(ev) { (this._listeners[ev.type] || []).forEach((fn) => fn(ev)); return true; }
    click() { if (typeof this.onclick === 'function') this.onclick(); this.dispatchEvent(new Event('click')); }
    matches(sel) { return matchSel(this, sel); }
    // frame.querySelector(sel): só descendentes "pertencentes" a este elemento
    // (_owner marca o dono no registry plano do harness)
    querySelector(sel) { return registry.find((e) => matchSel(e, sel) && e._owner === this) || null; }
}
class HTMLInputElement extends FakeEl { constructor() { super('input'); this._value = ''; } }
class HTMLTextAreaElement extends FakeEl { constructor() { super('textarea'); this._value = ''; } }
Object.defineProperty(HTMLInputElement.prototype, 'value', { get() { return this._value; }, set(v) { this._value = String(v); }, configurable: true });
Object.defineProperty(HTMLTextAreaElement.prototype, 'value', { get() { return this._value; }, set(v) { this._value = String(v); }, configurable: true });
global.HTMLInputElement = HTMLInputElement;
global.HTMLTextAreaElement = HTMLTextAreaElement;

let registry = [];
const add = (el) => { registry.push(el); return el; };
const mkInput = (id, value) => { const e = new HTMLInputElement(); if (id) e.attrs.id = id; if (value != null) { e._value = value; e.attrs.value = value; } return add(e); };
const mkEl = (tag, opts = {}) => { const e = new FakeEl(tag); Object.assign(e.attrs, opts.attrs || {}); if (opts.text != null) e._text = opts.text; if (opts.className) e.attrs.class = opts.className; return add(e); };

function matchSel(el, sel) {
    sel = sel.trim();
    const desc = sel.match(/^li(?:\[id="([^"]+)"\])?\s+a$/);
    if (desc) {
        if (el.tagName !== 'A') return false;
        const p = el.parentElement;
        if (!p || p.tagName !== 'LI') return false;
        return desc[1] ? p.attrs.id === desc[1] : true;
    }
    const m = sel.match(/^([a-z0-9]+)?(?:\.([\w-]+))?(?:\[([^\]=]+)(?:="([^"]*)")?\])?$/i);
    if (!m) return false;
    const [, tag, cls, attr, val] = m;
    if (tag && el.tagName !== tag.toUpperCase()) return false;
    if (cls && !(el.attrs.class || '').split(/\s+/).includes(cls)) return false;
    if (attr) {
        if (attr.endsWith('*')) { const key = attr.slice(0, -1); if (!(key in el.attrs) || !String(el.attrs[key]).includes(val)) return false; }
        else if (el.attrs[attr] !== val) return false;
    }
    return true;
}
global.document = {
    documentElement: new FakeEl('html'),
    querySelector(sel) { return registry.find((e) => matchSel(e, sel)) || null; },
    querySelectorAll(sel) { return registry.filter((e) => matchSel(e, sel)); },
    title: '',
};
let _closed = false;
global.window = { close() { _closed = true; } };
// sessionStorage fake (o motor registra a fase nele; sobrevive à navegação)
global.sessionStorage = {
    _s: {},
    getItem(k) { return k in this._s ? this._s[k] : null; },
    setItem(k, v) { this._s[k] = String(v); },
    removeItem(k) { delete this._s[k]; },
    clear() { this._s = {}; },
};
global.window.sessionStorage = global.sessionStorage;

// ── máquina de estados ──
const CNJ = '1001190-87.2024.5.02.0000';
let ENVIO_COM_SUCESSO = true;
let CNJ_ABERTO = CNJ;
let _tituloEl = null;
function titulo(t) { if (!_tituloEl) _tituloEl = mkEl('div', { attrs: { id: 'barraTitulo' } }); _tituloEl._text = t; }
function reset() { registry = []; _tituloEl = null; _closed = false; ENVIO_COM_SUCESSO = true; CNJ_ABERTO = CNJ; }

function montarEnvio() {
    titulo('Enviar para o PJe');
    const cons = mkInput(null, 'Consolidar Dados');
    cons.onclick = () => {
        mkEl('span', { className: 'rich-messages-label', text: 'Os dados estão prontos para serem enviados para o PJe' });
        const env = mkInput(null, 'Enviar para o PJe');
        env.onclick = () => {
            const ok = mkInput('popup_ok');
            ok.onclick = () => { if (ENVIO_COM_SUCESSO) mkEl('h2', { text: 'Sucesso!' }); };
        };
    };
}
function montarLiquidacao() {
    const li = mkEl('li');
    const a = mkEl('a', { text: 'Liquidar Atualização' }); a.parentElement = li;
    a.onclick = () => {
        // estrutura do +PJe: barraTitulo.parentElement.parentElement = frame
        // que contém data/liquidar (o motor lê DENTRO dele, não em document)
        const root = new FakeEl('div');      // frameAtualizacao
        const mid = new FakeEl('div');       // barraTitulo.parentElement
        const barra = document.querySelector('div[id="barraTitulo"]');
        barra.parentElement = mid; mid.parentElement = root;
        titulo('Atualização > Liquidar Atualização');
        mkEl('textarea', { attrs: { id: 'formulario:comentarios' } })._owner = root;
        mkInput('formulario:dataDeLiquidacaoInputDate')._owner = root;
        const liq = mkInput('formulario:liquidar'); liq._owner = root;
        liq.onclick = () => {
            mkEl('div', { attrs: { id: 'divMensagem' }, text: 'Operação realizada com sucesso.' });
            const li2 = mkEl('li', { attrs: { id: 'li_operacoes_validar_atualizacao' } });
            const a2 = mkEl('a', { text: 'Enviar para o PJe' }); a2.parentElement = li2;
            a2.onclick = montarEnvio;
        };
    };
}
function linhaCalculo(numero) {
    const tr = new FakeEl('tr');
    const cells = [0, 1, 2, 3, 4, 5].map(() => { const td = new FakeEl('td'); td.parentElement = tr; return td; });
    cells[2]._text = numero; tr.childNodes = cells;
    const a = mkEl('a', { attrs: { title: 'Abrir' }, className: 'linkSelecionar' });
    a.parentElement = cells[1];
    a.onclick = () => {
        titulo('Cálculo > Dados do Cálculo');
        mkEl('span', { attrs: { id: 'formulario:panelDadosCalculo' }, text: 'Processo ' + CNJ_ABERTO });
        montarLiquidacao();
    };
    return a;
}
function montarBusca(modo, numeros) {
    ['numeroProcessoBusca', 'digitoProcessoBusca', 'anoProcessoBusca', 'justicaBusca', 'regiaoBusca', 'varaProcessoBusca', 'numeroCalculoBusca']
        .forEach((n) => mkInput('formulario:' + n));
    mkInput('formulario:setor');
    const buscar = mkInput('formulario:buscar');
    buscar.onclick = () => {
        // re-busca: se há número de cálculo informado, filtra a listagem (como o PJeCalc)
        const numCampo = registry.find((e) => e.attrs.id === 'formulario:numeroCalculoBusca');
        const filtro = numCampo && numCampo._value ? String(numCampo._value).trim() : null;
        // remove resultados anteriores
        registry = registry.filter((e) => !(e.tagName === 'A' && e.attrs.title === 'Abrir')
            && !(e.tagName === 'SPAN' && (e.attrs.class || '').includes('box-msg-livre')));
        if (modo === 'semCalculo') { mkEl('span', { className: 'box-msg-livre', text: 'Não existem resultados para a pesquisa solicitada.' }); return; }
        const alvo = filtro ? numeros.filter((n) => n === filtro) : numeros;
        if (!alvo.length) { mkEl('span', { className: 'box-msg-livre', text: 'Não existem resultados para a pesquisa solicitada.' }); return; }
        alvo.forEach((n) => linhaCalculo(n));
    };
}

const src = fs.readFileSync(path.join(__dirname, '..', 'Fix', 'atualizacao_rapida.js'), 'utf8');
const motor = eval('(' + src + ')');

async function cenario(nome, setup, cfg, esperado) {
    reset(); setup();
    const res = await motor(cfg);
    const ok = esperado(res);
    console.log((ok ? 'PASS' : 'FAIL') + '  ' + nome + '  -> ' + JSON.stringify(res));
    if (!ok) process.exitCode = 1;
}

(async () => {
    const data = '17/11/2026';
    await cenario('happy_single (data atual, sem confirmação, fecha aba)',
        () => montarBusca('lista', ['123']),
        { numeroProcesso: CNJ, data, idCalculo: null },
        (r) => r.ok === true && r.numeroCalculo === '123' && r.data === data && _closed === true);

    await cenario('happy_com_id (filtra número exato da listagem)',
        () => { montarBusca('lista', ['123', '456']); mkInput('formulario:numeroCalculoBusca'); },
        { numeroProcesso: CNJ, data, idCalculo: '456' },
        (r) => r.ok === true && r.numeroCalculo === '456');

    await cenario('sem_calculo',
        () => montarBusca('semCalculo', []),
        { numeroProcesso: CNJ, data, idCalculo: null },
        (r) => r.ok === false && /sem cálculo/i.test(r.erro) && r.posEnvio === false);

    await cenario('ambiguidade_sem_id (não escolhe arbitrariamente)',
        () => montarBusca('lista', ['123', '456']),
        { numeroProcesso: CNJ, data, idCalculo: null },
        (r) => r.ok === false && /Múltiplos cálculos/.test(r.erro) && r.posEnvio === false);

    await cenario('mais_recente_com_varios (teimosinha: escolhe o maior número)',
        () => montarBusca('lista', ['123', '456', '789']),
        { numeroProcesso: CNJ, data, idCalculo: null, selecionarMaisRecente: true },
        (r) => r.ok === true && r.numeroCalculo === '789');

    await cenario('processo_errado (cancela antes de liquidar)',
        () => { montarBusca('lista', ['123']); CNJ_ABERTO = '9999999-99.9999.9.99.9999'; },
        { numeroProcesso: CNJ, data, idCalculo: null },
        (r) => r.ok === false && /outro processo/.test(r.erro) && r.posEnvio === false);

    await cenario('somente_busca (não liquida nem envia — modo de inspeção)',
        () => { montarBusca('lista', ['123']); ENVIO_COM_SUCESSO = true; },
        { numeroProcesso: CNJ, data, idCalculo: null, somenteBusca: true },
        (r) => r.ok === true && r.somenteBusca === true && r.numeroCalculo === '123' && _closed === false);

    await cenario('pos_envio_sem_sucesso (não reenviar)',
        () => { montarBusca('lista', ['123']); ENVIO_COM_SUCESSO = false; },
        { numeroProcesso: CNJ, data, idCalculo: null },
        (r) => r.ok === false && r.posEnvio === true);

    console.log(process.exitCode ? '\nHARNESS: FALHOU' : '\nHARNESS: TODOS OS CENÁRIOS OK');
})();