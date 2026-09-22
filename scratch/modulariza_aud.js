// Modularização de Aud.js → Aud.data.js + Aud.core.js (Aud.js NÃO é alterado)
const fs = require('fs');
const path = 'd:/PjePlus/Script/modules/Aud/';
const raw = fs.readFileSync(path + 'Aud.js', 'utf8');

// ── Âncoras ──
const A_PERFIS = 'var perfis = {';
const A_DIA = 'var diaDaSemana = new Date().getDay();';
const idxPerfis = raw.indexOf(A_PERFIS);
const idxDia = raw.indexOf(A_DIA);
if (idxPerfis < 0 || idxDia < 0 || idxPerfis >= idxDia) throw new Error('Âncoras não encontradas na ordem esperada');
if (raw.indexOf(A_PERFIS) !== raw.lastIndexOf(A_PERFIS)) throw new Error('Âncora var perfis não é única');
if (raw.indexOf(A_DIA) !== raw.lastIndexOf(A_DIA)) throw new Error('Âncora var diaDaSemana não é única');

const dataBlock = raw.slice(idxPerfis, idxDia); // perfis + S2 + PR + HH, até antes de diaDaSemana

// ── Transformações de FORMATAÇÃO (zero mudança semântica) ──
let d = dataBlock;

// R2: seções de perfil
if ((d.match(/otavio: \{/g) || []).length !== 1) throw new Error('âncora otavio não única');
if ((d.match(/victor: \{/g) || []).length !== 1) throw new Error('âncora victor não única');
d = d.replace(/otavio: \{/, '// @SECAO: PERFIL OTAVIO\notavio: {');
d = d.replace(/victor: \{/, '// @SECAO: PERFIL VICTOR\nvictor: {');

// R3: subseções S1..S5 dentro de perfil
const nSub = (d.match(/\bS[1-5]: \[/g) || []).length;
d = d.replace(/(\bS[1-5]: \[)/g, '// @SUBSECAO: $1\n$1'.replace('$1\n', '').replace('// @SUBSECAO: ', '// @SUBSECAO: '));
// (refaz de forma correta abaixo, a linha acima é apenas contagem segura)
d = dataBlock;
d = d.replace(/otavio: \{/, '// @SECAO: PERFIL OTAVIO\notavio: {');
d = d.replace(/victor: \{/, '// @SECAO: PERFIL VICTOR\nvictor: {');
d = d.replace(/(^|\n)(\s*)(S[1-5]: \[)/g, function (m, nl, ind, decl) {
  const nome = decl.split(':')[0].trim();
  return nl + ind + '// @SUBSECAO: ' + nome + '\n' + ind + decl;
});

// R6: HH
d = d.replace(/(\n\s*)var HH = /, '$1// @SECAO: TEXTO PADRAO HONORARIOS (HH)\n$1var HH = ');

// R1: itens {"t": "..."}
const nItens = (d.match(/\{"t": "/g) || []).length;
d = d.replace(/\{"t": "((?:[^"\\]|\\.)*)"/g, function (m, title) {
  return '// @ITEM: ' + title + '\n' + m;
});

// R5: entradas de PR (uma linha: var PR = {...};
const iPr = d.indexOf('var PR = ');
if (iPr < 0) throw new Error('PR não encontrado');
const iPrEnd = d.indexOf('\n', iPr);
let prLine = d.slice(iPr, iPrEnd);
const prRest = d.slice(iPrEnd);
const nPeritos = (prLine.match(/"[^"]+": \{/g) || []).length;
prLine = prLine.replace(/("[^"]+": \{)/g, '// @PERITO\n$1');
d = d.slice(0, iPr) + prLine + prRest;

// R4: continuação de linha após </p> (um parágrafo por linha)
const nPar = (d.match(/<\/p><p/g) || []).length;
d = d.replace(/<\/p><p/g, '</p>\\\n<p');

// ── Validação: reconstrução byte-idêntica ao bloco original ──
let recon = d
  .replace(/\/\/ @(?:ITEM|SECAO|SUBSECAO|PERITO)[^\n]*\n/g, '')
  .replace(/\\\n/g, '');
if (recon !== dataBlock) {
  // diagnóstico mínimo
  for (let i = 0; i < Math.max(recon.length, dataBlock.length); i++) {
    if (recon[i] !== dataBlock[i]) {
      throw new Error('Validação falhou na posição ' + i + ':\nORIG: ' + JSON.stringify(dataBlock.slice(i - 40, i + 40)) + '\nRECON: ' + JSON.stringify(recon.slice(i - 40, i + 40)));
    }
  }
  throw new Error('Validação falhou (tamanhos: ' + recon.length + ' vs ' + dataBlock.length + ')');
}

// ── Monta Aud.data.js ──
const dataFile =
  '// ==UserScript==\n' +
  '// @name         Aud - Dados (perfis, peritos, textos padrão)\n' +
  '// @namespace    pjetools\n' +
  '// @version      1.0\n' +
  '// @grant        none\n' +
  '// ==/UserScript==\n' +
  '(function () {\n' +
  "    'use strict';\n\n" +
  d +
  '\n    window.AUD_DATA = { perfis: perfis, S2: S2, PR: PR, HH: HH };\n' +
  '})();\n';
fs.writeFileSync(path + 'Aud.data.js', dataFile, 'utf8');

// ── Monta Aud.core.js ──
// indentação da linha de var perfis no original
const lineStart = raw.lastIndexOf('\n', idxPerfis) + 1;
const indent = raw.slice(lineStart, idxPerfis);
const replacementVars =
  indent + 'var perfis = window.AUD_DATA.perfis;\n' +
  indent + 'var S2 = window.AUD_DATA.S2;\n' +
  indent + 'var PR = window.AUD_DATA.PR;\n' +
  indent + 'var HH = window.AUD_DATA.HH;\n\n';
const core = raw.slice(0, idxPerfis) + replacementVars + raw.slice(idxDia);

// aguardarDados + wrapper nas chamadas automáticas de init
const aguardar =
  '    // Espera por window.AUD_DATA (Aud.data.js) — segurança para instalação\n' +
  '    // standalone; no pjetools a ordem dos @require já garante os dados.\n' +
  '    function aguardarDados(cb) {\n' +
  '        if (window.AUD_DATA) return cb();\n' +
  '        setTimeout(function () { aguardarDados(cb); }, 50);\n' +
  '    }\n\n';
const coreMark = '(function() {\n';
if (core.indexOf(coreMark) !== 0) throw new Error('Início do IIFE inesperado em Aud.core.js');
let coreOut = core.slice(0, coreMark.length) + aguardar + core.slice(coreMark.length);

const OLD_INT = "!window.__pjeAudFechadoManualmente) {\n                    init();";
if (coreOut.indexOf(OLD_INT) === -1) throw new Error('Âncora do intervalo não encontrada');
coreOut = coreOut.replace(OLD_INT, "!window.__pjeAudFechadoManualmente) {\n                    aguardarDados(function () { init(); });");
if (coreOut.split('aguardarDados(function () { init(); });').length - 1 !== 1) throw new Error('Wrapper do intervalo aplicado mais de uma vez');

fs.writeFileSync(path + 'Aud.core.js', coreOut, 'utf8');

console.log('OK');
console.log('data: itens=' + nItens + ' subsecoes=' + nSub + ' peritos=' + nPeritos + ' paragrafos=' + nPar);
console.log('data bytes=' + dataFile.length + ' core bytes=' + coreOut.length);
