(function() {
    // Espera por window.AUD_DATA (Aud.data.js) — segurança para instalação
    // standalone; no pjetools a ordem dos @require já garante os dados.
    function aguardarDados(cb) {
        if (window.AUD_DATA) return cb();
        setTimeout(function () { aguardarDados(cb); }, 50);
    }

    aguardarDados(function () {

        function isRouteAud() {
        return window.location.href.indexOf('/aud') !== -1;
    }

    function isRouteDetalhe() {
        var href = window.location.href;
        return href.indexOf('/detalhe') !== -1 || /\/processo\/\d+\/detalhe/.test(href);
    }

    function init(force) {
        if (!force && !isRouteAud()) return;
        if (!document.body) {
            setTimeout(function() { init(force); }, 300);
            return;
        }
        var topDoc = document;
        try {
            if (window.top && window.top.document) topDoc = window.top.document;
        } catch(e) {}
        var existing = document.getElementById('pjetools-aud-container') || (topDoc && topDoc.getElementById('pjetools-aud-container'));
        if (existing) {
            window.__pjeAudFechadoManualmente = false;
            return;
        }
        window.__pjeAudFechadoManualmente = false;

                var perfis = window.AUD_DATA.perfis;
        var S2 = window.AUD_DATA.S2;
        var PR = window.AUD_DATA.PR;
        var HH = window.AUD_DATA.HH;

var diaDaSemana = new Date().getDay(); // 0 = Dom, 1 = Seg, 2 = Ter, 3 = Qua, 4 = Qui, 5 = Sex, 6 = Sáb
        var perfilAtual = "";
        if (diaDaSemana === 1 || diaDaSemana === 2) {
            perfilAtual = "victor";
        } else if (diaDaSemana === 3 || diaDaSemana === 4) {
            perfilAtual = "otavio";
        }

        function renderizarPainel(perfilId, estaRetraido) {
            var ex = document.getElementById('pjetools-aud-container');
            if (ex) ex.remove();

            if (typeof estaRetraido === 'undefined') {
                estaRetraido = false;
            }

            if (!perfilId) {
                criarSeletor();
                return;
            }

            var perfil = perfis[perfilId];
            var T = perfil.title;
            var S1 = perfil.S1;
            var S2_list = perfil.S2 || S2;
            var S3 = perfil.S3;
            var S4 = perfil.S4;
            var S5 = perfil.S5;

            function calcularTopMinimo() {
                var toolbar = document.querySelector('mat-toolbar.barra-ata, mat-toolbar, .barra-ata');
                if (toolbar) {
                    var rectT = toolbar.getBoundingClientRect();
                    return Math.max(65, Math.ceil(rectT.bottom + 8));
                }
                var btnEnviar = document.getElementById('enviarInformacoesParaPje');
                if (btnEnviar) {
                    var rectB = btnEnviar.getBoundingClientRect();
                    return Math.max(65, Math.ceil(rectB.bottom + 8));
                }
                var cabecalho = document.querySelector('app-ata-cabecalho, .header, .toolbar');
                if (cabecalho) {
                    var rectC = cabecalho.getBoundingClientRect();
                    return Math.max(65, Math.ceil(rectC.bottom + 8));
                }
                return 75;
            }

            var topMinimo = calcularTopMinimo();

            var P = document.createElement('div');
            P.id = 'pjetools-aud-container';
            P.style.cssText = 'position:fixed;top:' + topMinimo + 'px;right:10px;background:#fff;border:1px solid #c8d0ea;border-radius:10px;padding:8px 12px;z-index:2147483647;box-shadow:0 6px 24px rgba(30,50,130,.2);font-family:Arial,sans-serif;font-size:14px;box-sizing:border-box;user-select:none;';

            // Compensa o zoom do navegador (Ctrl +/-) para o painel manter o
            // tamanho fixo em tela, independente do zoom aplicado na página.
            function aplicarZoomComp() {
                try {
                    if (!window.__pjeAudBaseDPR) window.__pjeAudBaseDPR = window.devicePixelRatio || 1;
                    var zc = window.__pjeAudBaseDPR / (window.devicePixelRatio || 1);
                    if (!isFinite(zc) || zc <= 0 || Math.abs(zc - 1) < 0.02) zc = 1;
                    P.style.zoom = (zc === 1) ? '' : String(zc);
                    P.dataset.zoomComp = String(zc);
                } catch (e) {
                    P.style.zoom = '';
                    P.dataset.zoomComp = '1';
                }
            }

            // Posiciona o painel no espaço vazio à direita do editor.
            // O fator de escala é MEDIDO (rect/offsetWidth), não deduzido do
            // devicePixelRatio — imune a baseDPR defasado. Sempre ancora em
            // editor.right + margem; o clamp é só para o painel não vazar da
            // tela. Não há fallback para a borda direita: se não couber todo,
            // fica o mais à direita possível sem sair da viewport.
            function fatorVisual() {
                try {
                    var r = P.getBoundingClientRect();
                    var f = r.width / (P.offsetWidth || r.width || 1);
                    return (isFinite(f) && f > 0) ? f : 1;
                } catch (e) { return 1; }
            }

            function posicionarAoLadoDoEditor() {
                var fator = fatorVisual();
                var larguraVisual = P.getBoundingClientRect().width || (P.offsetWidth * fator);
                var margem = 8;
                var margemDir = 4;
                var maxLeft = window.innerWidth - larguraVisual - margemDir;
                var alvo = null;
                var edRight = null;
                var ed = acharEditor();
                if (ed) {
                    try {
                        edRight = Math.ceil(ed.getBoundingClientRect().right);
                        alvo = edRight + margem;
                    } catch (e) { }
                }
                if (alvo === null) alvo = maxLeft;

                // Painel expandido: se o espaço vazio entre o editor e a borda
                // da tela for menor que o painel (zoom alto), REDUZ a largura
                // para caber — nunca invadindo o editor. Piso de 260px visuais;
                // abaixo disso, mantém o tamanho e apenas clampa. Restaura os
                // 380px quando o espaço voltar (zoom out).
                if (edRight !== null && !estaRetraido) {
                    var disponivel = window.innerWidth - edRight - margem - margemDir;
                    var nominalVisual = 380 * fator;
                    var PISO = 260;
                    if (disponivel >= PISO) {
                        var alvoVisual;
                        if (disponivel < larguraVisual) {
                            alvoVisual = disponivel;
                        } else if (larguraVisual < nominalVisual - 2 && disponivel >= nominalVisual) {
                            alvoVisual = nominalVisual;
                        } else {
                            alvoVisual = null;
                        }
                        if (alvoVisual !== null) {
                            P.style.width = Math.floor(alvoVisual / fator) + 'px';
                            larguraVisual = alvoVisual;
                        }
                    }
                    maxLeft = window.innerWidth - larguraVisual - margemDir;
                }

                alvo = Math.max(10, Math.min(maxLeft, alvo));
                P.style.left = (alvo / fator) + 'px';
                P.style.right = 'auto';
            }

            function E(t, c, x) {
                var e = document.createElement(t);
                if (c) e.style.cssText = c;
                if (x != null) e.textContent = x;
                return e;
            }

            var bodyDiv = E('div', 'display:block;user-select:text;overflow-y:auto;overflow-x:hidden;height:360px;box-sizing:border-box;padding-right:4px;');

            // Altura fixa do corpo: o painel não estica com a página nem com o
            // conteúdo — tudo que exceder fica disponível pela barra de rolagem.
            // O header (hdr) fica sempre visível no topo, pois só o bodyDiv rola.
            var ALTURA_CORPO = 360;

            // ST agora cria um grupo colapsável de botões: o título funciona
            // como toggle. `aberto` define o estado inicial (apenas o primeiro
            // grupo é criado expandido; os demais nascem retraídos).
            function ST(t, aberto) {
                var expandido = !!aberto;
                var d = E('div', 'margin-top:6px;border-top:1px solid #eef;');
                var titulo = E('div', 'display:flex;align-items:center;gap:5px;cursor:pointer;padding:6px 0 5px 0;user-select:none;');
                var chevron = E('span', 'font-size:11px;color:#8899cc;width:12px;display:inline-block;text-align:center;flex:0 0 12px;', expandido ? '▾' : '▸');
                var rotulo = E('span', 'font-weight:bold;font-size:13px;color:#8899cc;text-transform:uppercase;letter-spacing:.7px;', t);
                var conteudo = E('div', expandido ? 'padding:0 0 5px 0;' : 'display:none;padding:0 0 5px 0;');
                titulo.appendChild(chevron);
                titulo.appendChild(rotulo);
                d.appendChild(titulo);
                d.appendChild(conteudo);
                function toggleGrupo(e) {
                    if (e) { e.preventDefault(); e.stopPropagation(); }
                    expandido = !expandido;
                    conteudo.style.display = expandido ? 'block' : 'none';
                    chevron.textContent = expandido ? '▾' : '▸';
                }
                titulo.onclick = toggleGrupo;
                bodyDiv.appendChild(d);
                d._conteudo = conteudo;
                return conteudo;
            }

            // Localiza o editor CKEditor 5 (ou contenteditable) sem alertar.
            // Usado tanto pelo getEditor() quanto pelo posicionamento do painel.
            function acharEditor() {
                function findInDoc(d) {
                    if (!d) return null;
                    try {
                        return [...d.querySelectorAll('.ck-editor__editable[contenteditable="true"],.ck-editor__editable_inline[contenteditable="true"],[contenteditable="true"]')].find(function (x) { return x && x.ckeditorInstance; });
                    } catch(e) { return null; }
                }
                var ed = findInDoc(document);
                if (!ed && typeof unsafeWindow !== 'undefined' && unsafeWindow && unsafeWindow.document) {
                    ed = findInDoc(unsafeWindow.document);
                }
                if (!ed) {
                    var iframes = document.querySelectorAll('iframe');
                    for (var i = 0; i < iframes.length; i++) {
                        try {
                            var idoc = iframes[i].contentDocument || (iframes[i].contentWindow && iframes[i].contentWindow.document);
                            ed = findInDoc(idoc);
                            if (ed) break;
                        } catch(e) {}
                    }
                }
                return ed;
            }

            function getEditor() {
                var ed = acharEditor();
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

            // Hora de encerramento: hora atual + 12 minutos, formato HH:MM
            function horaEncerramento() {
                var d = new Date(Date.now() + 12 * 60000);
                var hh = String(d.getHours()).padStart(2, '0');
                var mm = String(d.getMinutes()).padStart(2, '0');
                return hh + ':' + mm;
            }

            // Os templates contêm o marcador %HEC% em "Audiência encerrada às %HEC%."
            // (marcado direto na ocorrência); aqui é expandido no momento do clique.
            function completarEncerramento(html) {
                var texto = String(html || '');
                var hora = horaEncerramento();
                return texto.split('%HEC%').join(hora)
                    .replace(/Audiência encerrada às\s*\./gi, 'Audiência encerrada às ' + hora + '.')
                    .replace(/Audiência encerrada às\s*(?=<|$)/gi, 'Audiência encerrada às ' + hora + '.');
            }

            function ins(h) {
                var ed = getEditor();
                if (!ed) return;
                h = completarEncerramento(h);
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
                var btn = E('button', 'flex:1 1 auto;min-width:70px;padding:7px 4px;background:#e8f0fe;border:1px solid #b0c4f8;border-radius:6px;cursor:pointer;font-size:14px;text-align:center;line-height:1.3;');
                btn.textContent = b.t;
                btn.onclick = function () { ins(b.h); };
                btn.onmouseover = function () { this.style.background = '#c5d8ff'; };
                btn.onmouseout = function () { this.style.background = '#e8f0fe'; };
                return btn;
            }

            function BC(b, bg) {
                var btn = E('button', 'display:block;width:100%;padding:7px 8px;margin:3px 0;background:' + (bg || '#f5f8ff') + ';border:1px solid #c8d4f0;border-radius:6px;cursor:pointer;font-size:16px;text-align:left;');
                btn.textContent = b.t;
                btn.onclick = function () { ins(b.h); };
                btn.onmouseover = function () { this.style.background = '#d8e4ff'; };
                btn.onmouseout = function () { this.style.background = (bg || '#f5f8ff'); };
                return btn;
            }

            function BP(b) {
                var btn = E('button', 'padding:6px 4px;background:#f5f8ff;border:1px solid #c8d4f0;border-radius:5px;cursor:pointer;font-size:14px;text-align:center;width:100%;');
                btn.textContent = b.t;
                btn.onclick = function () { ins(b.h); };
                btn.onmouseover = function () { this.style.background = '#d8e4ff'; };
                btn.onmouseout = function () { this.style.background = '#f5f8ff'; };
                return btn;
            }

            var hdr = E('div', 'display:flex;justify-content:space-between;align-items:center;gap:6px;cursor:grab;margin:-8px -12px 8px -12px;padding:8px 12px;background:#f4f6fc;border-top-left-radius:9px;border-top-right-radius:9px;border-bottom:1px solid #e8edff;');

            var titleBox = E('div', 'display:flex;align-items:center;gap:6px;cursor:pointer;flex:1;min-width:0;');
            var titleLabel = E('span', 'font-weight:bold;font-size:14px;color:#1e293b;white-space:nowrap;', '📌 Painel AUD');
            titleBox.appendChild(titleLabel);
            var selPerfil = E('select', 'font-size:14px;color:#223;font-weight:bold;border:1px solid #ccc;border-radius:4px;padding:2px 4px;background:#fff;cursor:pointer;');
            var opO = E('option', null, 'Otavio'); opO.value = 'otavio';
            var opV = E('option', null, 'Victor'); opV.value = 'victor';
            selPerfil.appendChild(opO);
            selPerfil.appendChild(opV);
            selPerfil.value = perfilId;
            selPerfil.onchange = function(e) {
                e.stopPropagation();
                renderizarPainel(this.value, false);
            };
            titleBox.appendChild(selPerfil);


            var rightControls = E('div', 'display:flex;align-items:center;gap:4px;');
            var toggleBtn = E('button', 'border:none;background:none;cursor:pointer;font-size:16px;color:#475569;padding:2px 4px;font-weight:bold;', estaRetraido ? '➕' : '➖');
            var fc = E('button', 'border:none;background:none;cursor:pointer;font-size:20px;color:#94a3b8;padding:0 2px;', '✕');
            fc.onclick = function (e) { e.stopPropagation(); window.__pjeAudFechadoManualmente = true; P.remove(); };

            rightControls.appendChild(toggleBtn);
            rightControls.appendChild(fc);

            hdr.appendChild(titleBox);
            hdr.appendChild(rightControls);
            P.appendChild(hdr);
            P.appendChild(bodyDiv);

            function aplicarRetracao(retraido) {
                estaRetraido = retraido;
                var minTop = calcularTopMinimo();

                if (!P.dataset.dragged) {
                    P.style.top = minTop + 'px';
                    posicionarAoLadoDoEditor();
                } else {
                    P.style.top = Math.max(minTop, P.getBoundingClientRect().top || minTop) + 'px';
                }

                if (estaRetraido) {
                    bodyDiv.style.display = 'none';
                    P.style.width = 'auto';
                    P.style.maxWidth = 'none';
                    P.style.maxHeight = 'none';
                    P.style.overflowY = 'visible';
                    P.style.padding = '4px 10px';
                    P.style.background = '#1e293b';
                    P.style.color = '#ffffff';
                    P.style.borderRadius = '20px';
                    P.style.boxShadow = '0 4px 14px rgba(0,0,0,0.3)';
                    P.title = 'Dois cliques em qualquer lugar para expandir';

                    hdr.style.marginBottom = '0';
                    hdr.style.borderBottom = 'none';
                    hdr.style.background = 'transparent';

                    titleLabel.style.color = '#f8fafc';
                    titleLabel.textContent = '📌 Painel AUD';
                    toggleBtn.textContent = '➕';
                    toggleBtn.style.color = '#cbd5e1';
                    toggleBtn.title = 'Expandir Painel de Consultas (ou clique duplo)';
                } else {
                    // Painel expandido: tamanho fixo — largura 380px e corpo com
                    // altura fixa (ALTURA_CORPO). O conteúdo que exceder fica
                    // disponível pela barra de rolagem interna do bodyDiv;
                    // o header (hdr) permanece sempre visível no topo.
                    bodyDiv.style.display = 'block';
                    bodyDiv.style.height = ALTURA_CORPO + 'px';
                    P.style.width = '380px';
                    P.style.maxWidth = 'min(380px, calc(100vw - 20px))';
                    P.style.padding = '8px 12px';
                    P.style.background = '#ffffff';
                    P.style.color = '#0f172a';
                    P.style.borderRadius = '10px';
                    P.style.boxShadow = '0 6px 24px rgba(30,50,130,.2)';
                    P.title = 'Dois cliques em qualquer lugar para retrair';

                    hdr.style.marginBottom = '8px';
                    hdr.style.borderBottom = '1px solid #e8edff';
                    hdr.style.background = '#f4f6fc';

                    titleLabel.style.color = '#1e293b';
                    titleLabel.textContent = '📌 Painel AUD';
                    toggleBtn.textContent = '➖';
                    toggleBtn.style.color = '#475569';
                    toggleBtn.title = 'Retrair Painel de Consultas (ou clique duplo)';

                    // Sem altura dinâmica: o painel não se adapta à página —
                    // a rolagem interna do corpo resolve o excedente.
                    P.style.overflowY = 'visible';
                    P.style.maxHeight = 'none';
                }
            }

            function alternarRetracao(e) {
                if (e && e.target && (e.target.tagName === 'SELECT' || e.target.tagName === 'OPTION')) return;
                aplicarRetracao(!estaRetraido);
            }

            titleBox.onclick = alternarRetracao;
            toggleBtn.onclick = alternarRetracao;

            // Evento dblclick padrão
            P.addEventListener('dblclick', function (e) {
                if (e.target && (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT' || e.target.tagName === 'OPTION' || e.target.tagName === 'TEXTAREA')) {
                    return;
                }
                e.stopPropagation();
                aplicarRetracao(!estaRetraido);
            });

            // Detector de duplo clique por intervalo (resiliente a sombras/Angular)
            var lastClickTime = 0;
            P.addEventListener('click', function (e) {
                if (e.target && (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT' || e.target.tagName === 'OPTION' || e.target.tagName === 'TEXTAREA' || e.target.tagName === 'A')) {
                    return;
                }
                var now = Date.now();
                if (now - lastClickTime < 350) {
                    e.stopPropagation();
                    aplicarRetracao(!estaRetraido);
                    lastClickTime = 0;
                } else {
                    lastClickTime = now;
                }
            });

            (function tornarArrastavel(el, handle) {
                let ox = 0, oy = 0, drag = false;
                handle.addEventListener('mousedown', function (e) {
                    if (e.target.tagName === 'BUTTON' || e.target.tagName === 'SELECT' || e.target.tagName === 'OPTION' || e.target.tagName === 'INPUT') return;
                    drag = true;
                    var rect = el.getBoundingClientRect();
                    ox = e.clientX - rect.left;
                    oy = e.clientY - rect.top;
                    e.preventDefault();
                });
                document.addEventListener('mousemove', function (e) {
                    if (!drag) return;
                    el.dataset.dragged = 'true';
                    var minTop = calcularTopMinimo();
                    var fator = fatorVisual();
                    var larguraVisual = el.getBoundingClientRect().width;
                    var targetTop = Math.max(minTop, e.clientY - oy);
                    var targetLeft = Math.max(10, Math.min(window.innerWidth - larguraVisual - 4, e.clientX - ox));
                    el.style.left = (targetLeft / fator) + 'px';
                    el.style.top = targetTop + 'px';
                    el.style.right = 'auto';
                    el.style.bottom = 'auto';
                    el.style.transform = 'none';
                });
                document.addEventListener('mouseup', function () {
                    drag = false;
                });
            })(P, hdr);

            function ajustarAoZoomEScroll() {
                if (!P || !document.body.contains(P)) return;
                aplicarZoomComp();
                if (!P.dataset.dragged) {
                    P.style.top = calcularTopMinimo() + 'px';
                    posicionarAoLadoDoEditor();
                } else {
                    var minTop = calcularTopMinimo();
                    var rect = P.getBoundingClientRect();
                    if (rect.top < minTop) {
                        P.style.top = minTop + 'px';
                    }
                }
            }

            window.addEventListener('resize', ajustarAoZoomEScroll);
            window.addEventListener('scroll', ajustarAoZoomEScroll, { passive: true });

            try {
                var domObs = new MutationObserver(ajustarAoZoomEScroll);
                domObs.observe(document.body, { childList: true, subtree: true });
            } catch (e) { }

            aplicarZoomComp();
            aplicarRetracao(estaRetraido);
            // Posiciona após aplicar zoom/retração (largura final conhecida).
            posicionarAoLadoDoEditor();

            // Grupo Base (S1): primeiro grupo do painel — único que começa expandido.
            var dBase = ST('Base', true);
            var r1 = E('div', 'display:flex;flex-wrap:wrap;gap:4px;');
            S1.forEach(function (b) { r1.appendChild(BF(b)); });
            dBase.appendChild(r1);

            // Grupo Consultas (Infojud / CEP / SisconDJ) — colapsado por padrão.
            var dConsultas = ST('Consultas', false);
            var consultas = E('div', 'display:flex;flex-direction:column;gap:5px;');

            function linhaConsulta(rotulo, placeholder, cor) {
                var linha = E('div', 'display:flex;align-items:center;gap:4px;');
                var label = E('label', 'flex:0 0 76px;margin:0;font-size:14px;font-weight:bold;', rotulo);
                var input = E('input', 'flex:1;min-width:0;box-sizing:border-box;padding:5px;font-size:16px;border:1px solid #ccc;border-radius:3px;');
                input.type = 'text';
                input.placeholder = placeholder;
                input.inputMode = 'numeric';
                var buscar = E('button', 'flex:0 0 62px;padding:5px 3px;background:' + cor + ';color:#fff;border:none;border-radius:4px;cursor:pointer;font-size:14px;font-weight:bold;', 'Buscar');
                var status = E('span', 'display:none;flex:0 0 38px;color:#188038;font-size:13px;font-weight:bold;white-space:nowrap;overflow:hidden;', 'Dados copiados');
                
                input.addEventListener('keydown', function(e) {
                    if (e.key === 'Enter') {
                        e.preventDefault();
                        buscar.click();
                    }
                });

                linha.appendChild(label);
                linha.appendChild(input);
                linha.appendChild(buscar);
                linha.appendChild(status);
                consultas.appendChild(linha);
                return { input: input, buscar: buscar, status: status, cor: cor };
            }

            // O próprio botão vira confirmação (DADOS OK / FALHA) e volta a Buscar depois.
            function feedbackBuscar(linha, ok) {
                linha.buscar.textContent = ok ? 'DADOS OK' : 'FALHA';
                linha.buscar.style.background = ok ? '#188038' : '#c5221f';
                setTimeout(function () {
                    linha.buscar.textContent = 'Buscar';
                    linha.buscar.style.background = linha.cor;
                }, 3000);
            }

            async function copiarTexto(texto) {
                if (typeof GM_setClipboard === 'function') {
                    GM_setClipboard(String(texto));
                    return;
                }
                if (navigator.clipboard && navigator.clipboard.writeText) {
                    try {
                        await navigator.clipboard.writeText(String(texto));
                        return;
                    } catch(e) {}
                }
                var area = document.createElement('textarea');
                area.value = String(texto);
                area.style.cssText = 'position:fixed;left:-9999px;top:0;';
                document.body.appendChild(area);
                area.select();
                if (!document.execCommand('copy')) throw new Error('Não foi possível copiar os dados.');
                area.remove();
            }

            var fInfo = linhaConsulta('Infojud', 'CPF ou CNPJ', '#43a047');
            fInfo.buscar.onclick = async function () {
                var c = fInfo.input.value.replace(/\D/g, '');
                fInfo.input.value = c;
                if (c.length !== 11 && c.length !== 14) {
                    feedbackBuscar(fInfo, false);
                    return;
                }
                fInfo.buscar.disabled = true;
                fInfo.buscar.textContent = 'Buscando...';
                try {
                    var consultarInfojud = window.consultarInfojudComRetorno;
                    if (typeof consultarInfojud !== 'function' && typeof unsafeWindow !== 'undefined') {
                        consultarInfojud = unsafeWindow.consultarInfojudComRetorno;
                    }
                    if (typeof consultarInfojud === 'function') {
                        var resultado = await consultarInfojud(c);
                        await copiarTexto(resultado.texto);
                        feedbackBuscar(fInfo, true);
                    } else {
                        var urlDecjuiz = (c.length === 11 ? 'https://cav.receita.fazenda.gov.br/Servicos/ATSDR/Decjuiz/detalheNICPF.asp?NI=' : 'https://cav.receita.fazenda.gov.br/Servicos/ATSDR/Decjuiz/detalheNICNPJ.asp?NI=') + encodeURIComponent(c);
                        window.open(urlDecjuiz, '_blank');
                        feedbackBuscar(fInfo, true);
                    }
                } catch (e) {
                    feedbackBuscar(fInfo, false);
                } finally {
                    fInfo.buscar.disabled = false;
                    fInfo.buscar.textContent = 'Buscar';
                }
            };

            var fCep = linhaConsulta('CEP', 'Digite o CEP', '#1e88e5');
            async function buscarEnderecoPorCEP(cep) {
                var cepNumerico = String(cep).replace(/\D/g, '');
                if (cepNumerico.length !== 8) {
                    throw new Error('Digite um CEP válido com 8 números.');
                }
                var fontes = [
                    {
                        nome: 'ViaCEP',
                        url: 'https://viacep.com.br/ws/' + cepNumerico + '/json/',
                        parse: function (d) { return d.erro ? null : {
                            logradouro: d.logradouro, bairro: d.bairro, complemento: d.complemento,
                            cidade: d.localidade, uf: d.uf, cep: d.cep
                        }; }
                    },
                    {
                        nome: 'BrasilAPI',
                        url: 'https://brasilapi.com.br/api/cep/v2/' + cepNumerico,
                        parse: function (d) { return d.errors ? null : {
                            logradouro: d.street, bairro: d.neighborhood, complemento: '',
                            cidade: d.city, uf: d.state, cep: d.cep
                        }; }
                    },
                    {
                        nome: 'BrasilCEP',
                        url: 'https://brasilcep.dev/v1/' + cepNumerico + '.json',
                        parse: function (d) { return d.erro ? null : {
                            logradouro: d.logradouro, bairro: d.bairro, complemento: d.complemento,
                            cidade: d.localidade, uf: d.uf, cep: d.cep
                        }; }
                    }
                ];
                var resultados = [];
                for (var i = 0; i < fontes.length; i++) {
                    var fonte = fontes[i];
                    try {
                        var resposta = await fetch(fonte.url, { headers: { Accept: 'application/json' } });
                        if (!resposta.ok) continue;
                        var parsed = fonte.parse(await resposta.json());
                        if (parsed && parsed.logradouro) resultados.push(parsed);
                    } catch (e) {
                        console.warn('[CEP] Falha em ' + fonte.nome + ':', e.message);
                    }
                }
                if (!resultados.length) throw new Error('Não foi possível localizar o CEP em nenhuma API.');
                var combinado = resultados.reduce(function (acc, atual) {
                    return {
                        logradouro: acc.logradouro || atual.logradouro || '',
                        bairro: acc.bairro || atual.bairro || '',
                        complemento: acc.complemento || atual.complemento || '',
                        cidade: acc.cidade || atual.cidade || '',
                        uf: acc.uf || atual.uf || '',
                        cep: acc.cep || atual.cep || cepNumerico
                    };
                }, {});
                var cepLimpo = String(combinado.cep).replace(/\D/g, '') || cepNumerico;
                var cepFormatado = cepLimpo.length === 8 ? cepLimpo.substring(0, 5) + '-' + cepLimpo.substring(5) : cepLimpo;
                var texto = [combinado.logradouro + ', número __', combinado.bairro, combinado.complemento,
                    'CEP - ' + cepFormatado, combinado.cidade + '/' + combinado.uf]
                    .filter(Boolean).join(' - ');
                return texto;
            }
            fCep.buscar.onclick = async function () {
                var c = fCep.input.value.replace(/\D/g, '');
                fCep.input.value = c;
                if (c.length !== 8) { alert('Digite um CEP válido com 8 números.'); return; }
                fCep.buscar.disabled = true;
                fCep.buscar.textContent = 'Buscando...';
                try {
                    var endereco = await buscarEnderecoPorCEP(c);
                    await copiarTexto(endereco);
                    feedbackBuscar(fCep, true);
                } catch (e) {
                    feedbackBuscar(fCep, false);
                } finally {
                    fCep.buscar.disabled = false;
                    fCep.buscar.textContent = 'Buscar';
                }
            };

            var fSiscon = linhaConsulta('SisconDJ', 'Dados da consulta', '#8e44ad');
            dConsultas.appendChild(consultas);
            var sisconCard = E('div', 'display:none;margin-top:6px;padding:7px;background:#faf5ff;border:1px solid #c084fc;border-radius:5px;font-size:14px;');
            dConsultas.appendChild(sisconCard);
            function safeTxt(t) {
                return String(t || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
            }

            function formatarDoc(d) {
                var digits = String(d || '').replace(/\D/g, '');
                if (digits.length === 11) return digits.replace(/^(\d{3})(\d{3})(\d{3})(\d{2})$/, '$1.$2.$3-$4');
                if (digits.length === 14) return digits.replace(/^(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})$/, '$1.$2.$3/$4-$5');
                return d || '';
            }

            function exibirDadosSiscon(resultado, docBusca) {
                var dados = (resultado.data && resultado.data.primeiro) || resultado.data || {};
                console.log('[AUD][SISCON] resultado recebido:', resultado);
                console.log('[AUD][SISCON] primeiro bloco usado:', dados);

                var nome = (resultado.data && resultado.data.nome) || dados.nome || dados.razaoSocial || '';
                var docBruto = (resultado.data && resultado.data.documento) || dados.documento || dados.cnpj || docBusca || '';
                var docFormatado = formatarDoc(docBruto);

                var textoDados = (dados.conta || '') +
                    ', agência ' + (dados.agencia || '') +
                    ', do Banco ' + (dados.banco || '') +
                    (dados.contaJuridica ? ' (Conta PJ em nome de ' + (dados.razaoSocial || '') +
                        (dados.cnpj ? ' - ' + dados.cnpj : '') + ')' : '');

                var textoCopiado = 'Nome: ' + nome + ' CPF/CNPJ: ' + docFormatado + '\n' +
                    'Dados: ' + textoDados + '\n' +
                    'Chave Pix: ';

                sisconCard.innerHTML = '<strong>Nome:</strong> ' + safeTxt(nome) + ' &nbsp;<strong>CPF/CNPJ:</strong> ' + safeTxt(docFormatado) + '<br>' +
                    '<strong>Dados:</strong> ' + safeTxt(textoDados) + '<br>' +
                    '<strong>Chave Pix:</strong> ' +
                    (resultado.detailUrl ? ' <a href="' + resultado.detailUrl + '" target="_blank" rel="noopener">confirmar</a>' : '');
                sisconCard.style.display = 'block';

                return textoCopiado;
            }
            fSiscon.buscar.onclick = async function () {
                var c = fSiscon.input.value.replace(/\D/g, '');
                fSiscon.input.value = c;
                if (c.length !== 11 && c.length !== 14) { alert('Digite um CPF ou CNPJ válido.'); return; }
                fSiscon.buscar.disabled = true;
                fSiscon.buscar.textContent = 'Buscando...';
                try {
                    var api = (window.Alv && (window.Alv.siscondj || window.Alv.siscon)) || (typeof unsafeWindow !== 'undefined' && unsafeWindow && unsafeWindow.Alv && (unsafeWindow.Alv.siscondj || unsafeWindow.Alv.siscon));
                    if (api && typeof api.consultarDocumento === 'function') {
                        var resultado = await api.consultarDocumento(c);
                        if (resultado.status === 'empty') {
                            feedbackBuscar(fSiscon, false);
                            sisconCard.innerHTML = 'Nenhum dado bancário encontrado. ' + (resultado.searchLink ? '<a href="' + resultado.searchLink + '" target="_blank" rel="noopener">abrir busca</a>' : '');
                            sisconCard.style.display = 'block';
                            return;
                        }
                        var textoParaCopiar = exibirDadosSiscon(resultado, c);
                        await copiarTexto(textoParaCopiar);
                        feedbackBuscar(fSiscon, true);
                    } else {
                        var urlBusca = 'https://aplicacoes1.trt2.jus.br/adv-dados-bancarios-consulta/' + (c.length === 11 ? 'consulta-pf?cpf=' : 'consulta-pj?cnpj=') + c;
                        window.open(urlBusca, '_blank');
                        feedbackBuscar(fSiscon, true);
                    }
                } catch (e) {
                    feedbackBuscar(fSiscon, false);
                    sisconCard.style.display = 'none';
                } finally {
                    fSiscon.buscar.disabled = false;
                    fSiscon.buscar.textContent = 'Buscar';
                }
            };


            if (S2_list.length > 0) {
                var d2 = ST('Perícias', false);
                var g2 = E('div', 'display:grid;grid-template-columns:1fr 1fr;gap:4px;');
                S2_list.forEach(function (b) { g2.appendChild(BP(b)); });
                d2.appendChild(g2);
            }

            if (S3.length > 0) {
                var d3 = ST('Adiamento - Testemunhas', false);
                S3.forEach(function (b) { d3.appendChild(BC(b)); });
            }

            var d4 = ST('Acordo', false);
            S4.forEach(function (b) { d4.appendChild(BC(b)); });

            var honBtn = E('button', 'display:block;width:100%;padding:7px 8px;margin:3px 0;background:#fff8e1;border:1px solid #f0c060;border-radius:6px;cursor:pointer;font-size:16px;text-align:left;', 'Honorários periciais - acordo pós perícia');
            var honEx = E('div', 'display:none;margin-top:4px;padding:6px;background:#fffdf0;border:1px solid #f0d080;border-radius:5px;');
            var selP = E('select', 'width:100%;margin-bottom:4px;padding:4px;font-size:16px;border:1px solid #ccc;border-radius:3px;');
            var op0 = E('option', null, 'Selecione o perito aqui');
            op0.value = '';
            selP.appendChild(op0);
            Object.keys(PR).forEach(function (n) {
                var o = E('option', null, n);
                o.value = n;
                selP.appendChild(o);
            });
            honEx.appendChild(selP);

            var bColar = E('button', 'display:block;width:100%;padding:5px;background:#4caf50;color:#fff;border:none;border-radius:4px;cursor:pointer;font-size:16px;', 'Colar dados');
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
                var d5 = ST('Outros', false);
                S5.forEach(function (b) { d5.appendChild(BC(b, '#fdf5ff')); });
            }

            document.body.appendChild(P);

            if (window.PJeState && window.PJeState.registry) {
                window.PJeState.registry.add(function () {
                    var el = document.getElementById('pjetools-aud-container');
                    if (el) el.remove();
                });
            }
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
            btnO.style.cssText = 'padding:10px 20px;font-size:18px;cursor:pointer;background:#2196f3;color:#fff;border:none;border-radius:4px;';
            btnO.onclick = function() {
                overlay.remove();
                renderizarPainel('otavio');
            };
            
            var btnV = document.createElement('button');
            btnV.textContent = 'Victor';
            btnV.style.cssText = 'padding:10px 20px;font-size:18px;cursor:pointer;background:#4caf50;color:#fff;border:none;border-radius:4px;';
            btnV.onclick = function() {
                overlay.remove();
                renderizarPainel('victor');
            };
            
            btns.appendChild(btnO);
            btns.appendChild(btnV);
            modal.appendChild(btns);
            overlay.appendChild(modal);
            document.body.appendChild(overlay);
        renderizarPainel(perfilAtual, false);
    }

    if (isRouteAud()) {
        init(true);
    }

    var _targetWin = typeof unsafeWindow !== 'undefined' ? unsafeWindow : window;
    _targetWin.PJeAud = _targetWin.PJeAud || {};
    _targetWin.PJeAud.init = init;
    window.PJeAud = window.PJeAud || _targetWin.PJeAud;
    window.PJeAud.init = init;

    // Re-injeção automática do painel no ambiente /aud (remoção fora dele).
    if (typeof window.__pjeAudInterval === 'undefined') {
        window.__pjeAudInterval = setInterval(function() {
            if (isRouteAud()) {
                if (!document.getElementById('pjetools-aud-container') && document.body && !window.__pjeAudFechadoManualmente) {
                    init();
                }
            } else {
                var el = document.getElementById('pjetools-aud-container');
                if (el) el.remove();
            }
        }, 1000);
    }

    }); // fim aguardarDados

})();