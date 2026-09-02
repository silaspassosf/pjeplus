const fs = require('fs');

const otavioSrc = fs.readFileSync('bookmarklet-otavio-readable.js', 'utf8');
const victorSrc = fs.readFileSync('bookmarklet-victor-readable.js', 'utf8');

function extractVar(src, varName) {
    const regex = new RegExp(`var ${varName}=(.*?);var `);
    const match = src.match(regex);
    if (match) return match[1];
    
    // Some variables might be at the end of the var list
    const fallbackRegex = new RegExp(`var ${varName}=(.*?);`);
    const fallbackMatch = src.match(fallbackRegex);
    return fallbackMatch ? fallbackMatch[1] : null;
}

const otavio_S1 = extractVar(otavioSrc, 'S1');
const victor_S1 = extractVar(victorSrc, 'S1');
const otavio_S3 = extractVar(otavioSrc, 'S3');
const victor_S3 = extractVar(victorSrc, 'S3');
const otavio_S4 = extractVar(otavioSrc, 'S4');
const victor_S4 = extractVar(victorSrc, 'S4');
const otavio_S5 = extractVar(otavioSrc, 'S5');
const victor_S5 = extractVar(victorSrc, 'S5');

const shared_S2 = extractVar(victorSrc, 'S2');
const shared_PR = extractVar(victorSrc, 'PR');
const shared_HH = extractVar(victorSrc, 'HH');

const audTemplate = `(function() {
    window.PJeAud = {
        init: function() {
            if (window.location.href.indexOf('/aud/') === -1) return;
            if (document.getElementById('pjetools-aud-container')) return;

            var perfis = {
                otavio: {
                    title: "Otavio",
                    S1: ${otavio_S1},
                    S3: ${otavio_S3},
                    S4: ${otavio_S4},
                    S5: ${otavio_S5}
                },
                victor: {
                    title: "Victor",
                    S1: ${victor_S1},
                    S3: ${victor_S3},
                    S4: ${victor_S4},
                    S5: ${victor_S5}
                }
            };

            var S2 = ${shared_S2};
            var PR = ${shared_PR};
            var HH = ${shared_HH};

            var diaDaSemana = new Date().getDay(); // 0 = Dom, 1 = Seg, 2 = Ter, 3 = Qua, 4 = Qui, 5 = Sex, 6 = Sáb
            var perfilAtual = "";
            if (diaDaSemana === 1 || diaDaSemana === 2) {
                perfilAtual = "victor";
            } else if (diaDaSemana === 3 || diaDaSemana === 4) {
                perfilAtual = "otavio";
            }

            function renderizarPainel(perfilId) {
                var ex = document.getElementById('pjetools-aud-container');
                if (ex) ex.remove();

                if (!perfilId) {
                    criarSeletor();
                    return;
                }

                var perfil = perfis[perfilId];
                var T = perfil.title;
                var S1 = perfil.S1;
                var S3 = perfil.S3;
                var S4 = perfil.S4;
                var S5 = perfil.S5;

                var P = document.createElement('div');
                P.id = 'pjetools-aud-container';
                P.style.cssText = 'position:fixed;top:50%;transform:translateY(-50%);right:8px;width:295px;max-height:90vh;overflow-y:auto;background:#fff;border:1px solid #c8d0ea;border-radius:10px;padding:12px;z-index:2147483647;box-shadow:0 6px 24px rgba(30,50,130,.2);font-family:Arial,sans-serif;font-size:13px;';

                function E(t, c, x) {
                    var e = document.createElement(t);
                    if (c) e.style.cssText = c;
                    if (x != null) e.textContent = x;
                    return e;
                }

                function ST(t) {
                    var d = E('div', 'margin-top:10px;border-top:1px solid #eef;padding-top:6px;');
                    d.appendChild(E('div', 'font-weight:bold;font-size:10px;color:#8899cc;text-transform:uppercase;letter-spacing:.7px;margin-bottom:5px;', t));
                    P.appendChild(d);
                    return d;
                }

                function getEditor() {
                    var ed = [...document.querySelectorAll('.ck-editor__editable[contenteditable="true"],.ck-editor__editable_inline[contenteditable="true"],[contenteditable="true"]')].find(function (x) { return x.ckeditorInstance; });
                    if (!ed) {
                        alert('Editor CKEditor 5 não encontrado na tela. Abra a ata primeiro.');
                        return null;
                    }
                    return ed;
                }

                function getSelectionRange(ck) {
                    try {
                        var s = ck.model.document.selection;
                        var r = [...s.getRanges()];
                        return r.length > 0 ? r[0] : null;
                    } catch (e) {
                        return null;
                    }
                }

                function ins(h) {
                    var ed = getEditor();
                    if (!ed) return;
                    var ck = ed.ckeditorInstance;
                    var SR = getSelectionRange(ck);
                    if (!SR) {
                        alert('Posicione o cursor no editor antes de usar o botão.');
                        return;
                    }
                    try {
                        var v = ck.data.processor.toView(h);
                        var m = ck.data.toModel(v);
                        ck.model.change(function () { ck.model.insertContent(m, SR); });
                        ed.focus();
                    } catch (e) {
                        alert('Erro: ' + e.message);
                    }
                }

                function BF(b) {
                    var btn = E('button', 'flex:1 1 auto;min-width:70px;padding:7px 4px;background:#e8f0fe;border:1px solid #b0c4f8;border-radius:6px;cursor:pointer;font-size:11px;text-align:center;line-height:1.3;');
                    btn.textContent = b.t;
                    btn.onclick = function () { ins(b.h); };
                    btn.onmouseover = function () { this.style.background = '#c5d8ff'; };
                    btn.onmouseout = function () { this.style.background = '#e8f0fe'; };
                    return btn;
                }

                function BC(b, bg) {
                    var btn = E('button', 'display:block;width:100%;padding:7px 8px;margin:3px 0;background:' + (bg || '#f5f8ff') + ';border:1px solid #c8d4f0;border-radius:6px;cursor:pointer;font-size:12px;text-align:left;');
                    btn.textContent = b.t;
                    btn.onclick = function () { ins(b.h); };
                    btn.onmouseover = function () { this.style.background = '#d8e4ff'; };
                    btn.onmouseout = function () { this.style.background = (bg || '#f5f8ff'); };
                    return btn;
                }

                function BP(b) {
                    var btn = E('button', 'padding:6px 4px;background:#f5f8ff;border:1px solid #c8d4f0;border-radius:5px;cursor:pointer;font-size:11px;text-align:center;width:100%;');
                    btn.textContent = b.t;
                    btn.onclick = function () { ins(b.h); };
                    btn.onmouseover = function () { this.style.background = '#d8e4ff'; };
                    btn.onmouseout = function () { this.style.background = '#f5f8ff'; };
                    return btn;
                }

                var hdr = E('div', 'display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;padding-bottom:8px;border-bottom:2px solid #e8edff;');
                
                var selPerfil = E('select', 'font-size:14px;color:#223;font-weight:bold;border:1px solid #ccc;border-radius:4px;padding:2px;');
                var opO = E('option', null, 'Otavio'); opO.value = 'otavio';
                var opV = E('option', null, 'Victor'); opV.value = 'victor';
                selPerfil.appendChild(opO);
                selPerfil.appendChild(opV);
                selPerfil.value = perfilId;
                selPerfil.onchange = function() {
                    renderizarPainel(this.value);
                };
                hdr.appendChild(selPerfil);

                var fc = E('button', 'border:none;background:none;cursor:pointer;font-size:18px;color:#aab;padding:0 2px;', '✕');
                fc.onclick = function () { P.remove(); };
                hdr.appendChild(fc);
                P.appendChild(hdr);

                var r1 = E('div', 'display:flex;flex-wrap:wrap;gap:4px;');
                S1.forEach(function (b) { r1.appendChild(BF(b)); });
                P.appendChild(r1);

                var ricep = E('div', 'display:flex;gap:4px;margin-top:6px;');
                var bInfo = E('button', 'flex:1;padding:5px 3px;background:#e8f5e9;border:1px solid #80c080;border-radius:5px;cursor:pointer;font-size:11px;text-align:center;', 'INFOJUD CPF');
                var bCep2 = E('button', 'flex:1;padding:5px 3px;background:#e3f2fd;border:1px solid #90caf9;border-radius:5px;cursor:pointer;font-size:11px;text-align:center;', 'CEP endereço');
                ricep.appendChild(bInfo);
                ricep.appendChild(bCep2);
                P.appendChild(ricep);

                var xp = E('div', 'display:none;margin-top:4px;padding:6px;background:#f8f8ff;border:1px solid #dde;border-radius:5px;');
                P.appendChild(xp);

                var fInfo = E('div', '');
                var cpfIn = E('input', null);
                cpfIn.type = 'text';
                cpfIn.placeholder = 'Digite o CPF';
                cpfIn.style.cssText = 'width:100%;box-sizing:border-box;margin-bottom:4px;padding:4px;font-size:12px;border:1px solid #ccc;border-radius:3px;';
                fInfo.appendChild(cpfIn);
                var bPcpf = E('button', 'display:block;width:100%;padding:5px;background:#2196f3;color:#fff;border:none;border-radius:4px;cursor:pointer;font-size:12px;', 'Pesquisar e colar');
                bPcpf.onclick = function () {
                    var c = cpfIn.value.replace(/\\D/g, '');
                    if (c.length !== 11) { alert('Digite um CPF válido com 11 números.'); return; }
                    alert('Consulta INFOJUD será implementada na próxima etapa.');
                };
                fInfo.appendChild(bPcpf);

                var fCep = E('div', '');
                var cepIn = E('input', null);
                cepIn.type = 'text';
                cepIn.placeholder = 'Digite o CEP';
                cepIn.style.cssText = 'width:100%;box-sizing:border-box;margin-bottom:4px;padding:4px;font-size:12px;border:1px solid #ccc;border-radius:3px;';
                fCep.appendChild(cepIn);
                var bPcep = E('button', 'display:block;width:100%;padding:5px;background:#2196f3;color:#fff;border:none;border-radius:4px;cursor:pointer;font-size:12px;', 'Pesquisar e colar');
                bPcep.onclick = function () {
                    var c = cepIn.value.replace(/\\D/g, '');
                    if (c.length !== 8) { alert('Digite um CEP válido com 8 números.'); return; }
                    alert('Consulta de CEP será implementada na próxima etapa.');
                };
                fCep.appendChild(bPcep);

                bInfo.onclick = function () {
                    var open = xp.style.display !== 'none' && xp.dataset.active === 'info';
                    xp.style.display = open ? 'none' : 'block';
                    xp.dataset.active = 'info';
                    while (xp.firstChild) xp.removeChild(xp.firstChild);
                    if (!open) xp.appendChild(fInfo);
                };

                bCep2.onclick = function () {
                    var open = xp.style.display !== 'none' && xp.dataset.active === 'cep';
                    xp.style.display = open ? 'none' : 'block';
                    xp.dataset.active = 'cep';
                    while (xp.firstChild) xp.removeChild(xp.firstChild);
                    if (!open) xp.appendChild(fCep);
                };

                if (S2.length > 0) {
                    var d2 = ST('Perícias');
                    var g2 = E('div', 'display:grid;grid-template-columns:1fr 1fr;gap:4px;');
                    S2.forEach(function (b) { g2.appendChild(BP(b)); });
                    d2.appendChild(g2);
                }

                if (S3.length > 0) {
                    var d3 = ST('Adiamento - Testemunhas');
                    S3.forEach(function (b) { d3.appendChild(BC(b)); });
                }

                var d4 = ST('Acordo');
                S4.forEach(function (b) { d4.appendChild(BC(b)); });

                var honBtn = E('button', 'display:block;width:100%;padding:7px 8px;margin:3px 0;background:#fff8e1;border:1px solid #f0c060;border-radius:6px;cursor:pointer;font-size:12px;text-align:left;', 'Honorários periciais - acordo pós perícia');
                var honEx = E('div', 'display:none;margin-top:4px;padding:6px;background:#fffdf0;border:1px solid #f0d080;border-radius:5px;');
                var selP = E('select', 'width:100%;margin-bottom:4px;padding:4px;font-size:12px;border:1px solid #ccc;border-radius:3px;');
                var op0 = E('option', null, 'Selecione o perito aqui');
                op0.value = '';
                selP.appendChild(op0);
                Object.keys(PR).forEach(function (n) {
                    var o = E('option', null, n);
                    o.value = n;
                    selP.appendChild(o);
                });
                honEx.appendChild(selP);

                var bColar = E('button', 'display:block;width:100%;padding:5px;background:#4caf50;color:#fff;border:none;border-radius:4px;cursor:pointer;font-size:12px;', 'Colar dados');
                bColar.onclick = function () {
                    var n = selP.value;
                    if (!n) { selP.style.borderColor = 'red'; return; }
                    selP.style.borderColor = '#ccc';
                    var pp = PR[n];
                    var hf = HH.replace('perito *', n).replace('Banco *', pp.banco || '(banco não informado)').replace('agência *', pp.agencia || '(agência não informada)').replace('conta corrente *', pp.conta || '(conta não informada)');
                    ins(hf);
                };
                honEx.appendChild(bColar);

                honBtn.onclick = function () {
                    honEx.style.display = honEx.style.display === 'none' ? 'block' : 'none';
                };

                d4.appendChild(honBtn);
                d4.appendChild(honEx);

                if (S5.length > 0) {
                    var d5 = ST('Extras');
                    S5.forEach(function (b) { d5.appendChild(BC(b, '#fdf5ff')); });
                }

                document.body.appendChild(P);
            }

            function criarSeletor() {
                var overlay = document.createElement('div');
                overlay.id = 'pjetools-aud-container'; // same ID so it doesn't duplicate
                overlay.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.5);display:flex;justify-content:center;align-items:center;z-index:9999999;';
                
                var modal = document.createElement('div');
                modal.style.cssText = 'background:#fff;padding:20px;border-radius:8px;box-shadow:0 4px 12px rgba(0,0,0,0.3);text-align:center;font-family:Arial,sans-serif;';
                
                var titulo = document.createElement('h3');
                titulo.textContent = 'Qual o juiz da pauta de hoje?';
                titulo.style.marginTop = '0';
                modal.appendChild(titulo);
                
                var btns = document.createElement('div');
                btns.style.cssText = 'display:flex;gap:10px;justify-content:center;margin-top:20px;';
                
                var btnO = document.createElement('button');
                btnO.textContent = 'Otavio';
                btnO.style.cssText = 'padding:10px 20px;font-size:14px;cursor:pointer;background:#2196f3;color:#fff;border:none;border-radius:4px;';
                btnO.onclick = function() {
                    overlay.remove();
                    renderizarPainel('otavio');
                };
                
                var btnV = document.createElement('button');
                btnV.textContent = 'Victor';
                btnV.style.cssText = 'padding:10px 20px;font-size:14px;cursor:pointer;background:#4caf50;color:#fff;border:none;border-radius:4px;';
                btnV.onclick = function() {
                    overlay.remove();
                    renderizarPainel('victor');
                };
                
                btns.appendChild(btnO);
                btns.appendChild(btnV);
                modal.appendChild(btns);
                overlay.appendChild(modal);
                document.body.appendChild(overlay);
            }

            renderizarPainel(perfilAtual);
        }
    };
})();
`;

fs.writeFileSync('Script/modules/Aud/Aud.js', audTemplate);
console.log('Aud.js generated successfully!');
