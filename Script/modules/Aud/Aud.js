(function() {
    function isRouteDetalhe() {
        var href = window.location.href;
        return href.indexOf('/detalhe') !== -1 || /\/processo\/\d+\/detalhe/.test(href);
    }

    function init() {
        if (!isRouteDetalhe()) return;
        if (!document.body) {
            setTimeout(init, 300);
            return;
        }
        var topDoc = document;
        try {
            if (window.top && window.top.document) topDoc = window.top.document;
        } catch(e) {}
        if (document.getElementById('pjetools-aud-container') || (topDoc && topDoc.getElementById('pjetools-aud-container'))) return;
        window.__pjeAudFechadoManualmente = false;

        function renderizarPainel(estaRetraido) {
            var ex = document.getElementById('pjetools-aud-container');
            if (ex) ex.remove();

            if (typeof estaRetraido === 'undefined') {
                estaRetraido = false;
            }

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

            function atualizarMaxHeight() {
                var currentTop = P.getBoundingClientRect().top;
                var safeTop = Math.max(topMinimo, currentTop);
                P.style.maxHeight = 'calc(100vh - ' + (safeTop + 15) + 'px)';
            }

            function E(t, c, x) {
                var e = document.createElement(t);
                if (c) e.style.cssText = c;
                if (x != null) e.textContent = x;
                return e;
            }

            var bodyDiv = E('div', 'display:block;user-select:text;');

            function ST(t) {
                var d = E('div', 'margin-top:6px;border-top:1px solid #eef;padding-top:6px;');
                d.appendChild(E('div', 'font-weight:bold;font-size:13px;color:#8899cc;text-transform:uppercase;letter-spacing:.7px;margin-bottom:5px;', t));
                bodyDiv.appendChild(d);
                return d;
            }

            var hdr = E('div', 'display:flex;justify-content:space-between;align-items:center;gap:6px;cursor:grab;margin:-8px -12px 8px -12px;padding:8px 12px;background:#f4f6fc;border-top-left-radius:9px;border-top-right-radius:9px;border-bottom:1px solid #e8edff;');

            var titleBox = E('div', 'display:flex;align-items:center;gap:6px;cursor:pointer;flex:1;min-width:0;');
            var titleLabel = E('span', 'font-weight:bold;font-size:14px;color:#1e293b;white-space:nowrap;', '🔍 Consultas');
            titleBox.appendChild(titleLabel);

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
                    P.style.left = 'auto';
                    P.style.right = '10px';
                    P.style.top = minTop + 'px';
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
                    titleLabel.textContent = '🔍 Consultas';
                    toggleBtn.textContent = '➕';
                    toggleBtn.style.color = '#cbd5e1';
                    toggleBtn.title = 'Expandir Painel de Consultas (ou clique duplo)';
                } else {
                    bodyDiv.style.display = 'block';
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
                    titleLabel.textContent = '🔍 Consultas';
                    toggleBtn.textContent = '➖';
                    toggleBtn.style.color = '#475569';
                    toggleBtn.title = 'Retrair Painel de Consultas (ou clique duplo)';

                    P.style.overflowY = 'auto';
                    atualizarMaxHeight();
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
                    var targetTop = Math.max(minTop, e.clientY - oy);
                    var targetLeft = Math.max(10, Math.min(window.innerWidth - el.offsetWidth - 10, e.clientX - ox));
                    el.style.left = targetLeft + 'px';
                    el.style.top = targetTop + 'px';
                    el.style.right = 'auto';
                    el.style.bottom = 'auto';
                    el.style.transform = 'none';
                    atualizarMaxHeight();
                });
                document.addEventListener('mouseup', function () {
                    drag = false;
                });
            })(P, hdr);

            function ajustarAoZoomEScroll() {
                if (!P || !document.body.contains(P)) return;
                var minTop = calcularTopMinimo();
                if (!P.dataset.dragged) {
                    P.style.top = minTop + 'px';
                    P.style.right = '10px';
                    P.style.left = 'auto';
                } else {
                    var rect = P.getBoundingClientRect();
                    if (rect.top < minTop) {
                        P.style.top = minTop + 'px';
                    }
                }
                atualizarMaxHeight();
            }

            window.addEventListener('resize', ajustarAoZoomEScroll);
            window.addEventListener('scroll', ajustarAoZoomEScroll, { passive: true });

            try {
                var domObs = new MutationObserver(ajustarAoZoomEScroll);
                domObs.observe(document.body, { childList: true, subtree: true });
            } catch (e) { }

            aplicarRetracao(estaRetraido);

            var dConsultas = ST('Consultas');
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
                    if (typeof consultarInfojud !== 'function') throw new Error('Módulo Infojud não disponível.');
                    var resultado = await consultarInfojud(c);
                    await copiarTexto(resultado.texto);
                    feedbackBuscar(fInfo, true);
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

                var textoCopiado = 'Nome: ' + nome + '  CPF/CNPJ: ' + docFormatado + '\n' +
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
                    var api = (window.Alv && window.Alv.siscondj) || (typeof unsafeWindow !== 'undefined' && unsafeWindow && unsafeWindow.Alv && unsafeWindow.Alv.siscondj);
                    if (!api || typeof api.consultarDocumento !== 'function') throw new Error('Módulo SISCONDJ não disponível.');
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
                } catch (e) {
                    feedbackBuscar(fSiscon, false);
                    sisconCard.style.display = 'none';
                } finally {
                    fSiscon.buscar.disabled = false;
                    fSiscon.buscar.textContent = 'Buscar';
                }
            };

            document.body.appendChild(P);

            if (window.PJeState && window.PJeState.registry) {
                window.PJeState.registry.add(function () {
                    var el = document.getElementById('pjetools-aud-container');
                    if (el) el.remove();
                });
            }
        }

        renderizarPainel(false);
    }

    var _targetWin = typeof unsafeWindow !== 'undefined' ? unsafeWindow : window;
    _targetWin.PJeAud = _targetWin.PJeAud || {};
    _targetWin.PJeAud.init = init;
    window.PJeAud = window.PJeAud || _targetWin.PJeAud;
    window.PJeAud.init = init;

    if (typeof window.__pjeAudInterval === 'undefined') {
        window.__pjeAudInterval = setInterval(function() {
            if (isRouteDetalhe()) {
                if (!document.getElementById('pjetools-aud-container') && document.body && !window.__pjeAudFechadoManualmente) {
                    init();
                }
            } else {
                var el = document.getElementById('pjetools-aud-container');
                if (el) el.remove();
            }
        }, 1000);
    }
})();