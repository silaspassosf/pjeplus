// Check da semântica do script de busca ativa do tipo de conclusão
// (atos/judicial_navegacao.escolher_tipo_conclusao — fallback despacho_engine).
// Extrai o script_find.py, reproduz o unescape do Python e valida o DOM falso.
// Roda com: node tests/check_escolher_tipo_js.js
'use strict';
const fs = require('fs');

const src = fs.readFileSync('atos/judicial_navegacao.py', 'utf8');
const m = src.match(/script_find = """([\s\S]*?)"""/);
if (!m) {
  console.error('script_find nao encontrado');
  process.exit(1);
}
// No .py o texto traz `\\u0300`; o Python entrega `\u0300` ao JS.
const js = m[1].replace(/\\\\/g, '\\');
const busca = eval('(' + js + ')');

function btn(text, o = {}) {
  return {
    textContent: text,
    disabled: !!o.disabled,
    offsetWidth: o.visible === false ? 0 : 100,
    offsetHeight: 20,
    _clicked: false,
    getAttribute: k => (k === 'aria-label' ? (o.aria || '') : null),
    scrollIntoView() {},
    click() { this._clicked = true; },
  };
}

function run(buttons, tipo) {
  global.document = { querySelectorAll: () => buttons };
  return busca(tipo);
}

let falhas = 0;
const check = (nome, cond) => {
  console.log((cond ? 'ok  - ' : 'FALHA - ') + nome);
  if (!cond) falhas++;
};

let b = [btn('Despacho')];
check('casa Despacho', run(b, 'Despacho') === true && b[0]._clicked);

b = [btn('Sentenca')];
check('nao casa Sentenca para Despacho', run(b, 'Despacho') === false && !b[0]._clicked);

b = [btn('Remover', { aria: 'Remover Despacho' }), btn('Despacho')];
check('ignora botao de remover', run(b, 'Despacho') === true && !b[0]._clicked && b[1]._clicked);

b = [btn('Despacho', { disabled: true }), btn('Despacho', { visible: false }), btn('Despacho')];
check('pula disabled e invisivel', run(b, 'Despacho') === true && !b[0]._clicked && !b[1]._clicked && b[2]._clicked);

b = [btn('  SUSPENSAO  ')];
check('normaliza caixa e espaco', run(b, 'Suspensao') === true && b[0]._clicked);

b = [btn('SUSPENS\u00c3O')];
check('normaliza acento', run(b, 'Suspensao') === true && b[0]._clicked);

b = [btn('', { aria: 'Homologacao de Calculos' })];
check('casa por aria quando texto vazio', run(b, 'Homologacao de Calculos') === true && b[0]._clicked);

b = [btn('Despacho')];
check('nao casa Despacho para Sentenca', run(b, 'Sentenca') === false);

b = [];
check('sem botoes retorna false', run(b, 'Despacho') === false);

process.exit(falhas ? 1 : 0);
