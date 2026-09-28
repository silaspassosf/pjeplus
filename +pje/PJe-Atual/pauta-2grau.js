//FUNÇÃO QUE INSERE A FUNCIONALIDADE DE VERIFICAR IMPEDIMENTO E SUSPEIÇÃO NA PAUTA DO SEGUNDO GRAU
async function obterImpedimentosSuspeicoesPautaSegundoGrau() {
	console.log('obterImpedimentosSuspeicoesPautaSegundoGrau');
	let filtroIeSPauta2grau;
	await guardarFiltroStorage('');
	monitor_janela_pauta();
	iniciar();

	async function iniciar() {
		incluirBotaoVerificarIeS();
        incluirAtalhoVisualizarVoto();
        incluirCaixaDeSelecao();
		filtroIeSPauta2grau = await recuperarFiltroStorage();
		if (filtroIeSPauta2grau) {
			await montarFiltro(filtroIeSPauta2grau);
			await mapearProcessos(filtroIeSPauta2grau);
		}
	}

	async function incluirBotaoVerificarIeS() {
		// console.log('incluirBotaoVerificarIeS')
		if (!document.getElementById('maisPje_bt_verificar_impedimento_e_suspeicao')) {
			let ancora = document.getElementById('abaPautaJulgamentoListPanel') || document.querySelector('div[id*="votacaoAntecipadaListPanel"]');
			if (!ancora) { return }
			let botao = document.createElement("button");
			botao.id = "maisPje_bt_verificar_impedimento_e_suspeicao";
			botao.textContent = "Verificar Impedimento e Suspeição";
			botao.style = "cursor: pointer; position: relative; top: 20%; width: 99%; padding: 5px; margin: 5px; height: 35px; z-index: 1;";
			botao.onclick = async function () {
				limparIconesIeS();
				await guardarFiltroStorage('');
				if (document.getElementById('maisPje_filtroIeS')) { document.getElementById('maisPje_filtroIeS').remove() }
				consultaRapidaMagistrado(prompt('Digite o nome dos Magistrados:\n(Para mais de um magistrado separe por vírgula)',''));
			};
			ancora.insertBefore(botao, ancora.firstElementChild);
		}

	}

    async function incluirAtalhoVisualizarVoto() {

        //abaPautaJulgamentoList:0:ordem
        // await sleep(2000);
        let tabela = document.querySelector('table[id*="abaPautaJulgamentoList"]') || document.querySelector('table[id*="votacaoAntecipadaList"]');
        if (!tabela) { return }
        let listaNum = tabela.innerText.match(padraoProcesso).join().split(",");
        //bt imprimir tudo
        let ancora = await esperarElemento('th div','Voto');
        let btImprimirTodos = await botaoImprimir('imprimirTudo');
        btImprimirTodos.title = 'Imprimir Selecionados'
        btImprimirTodos.onclick = async function (event) {
            let colecao = tabela.querySelectorAll('tbody td input[checked="checked"]');
            console.log(colecao.length)
            for (const [pos, item] of colecao.entries()) {
                let linha = item.closest('tr');
                linha.style.backgroundColor = 'orange';
                linha.querySelector('a[id*="maisPJe_imprimirVoto_"]').click();
                await sleep(3000); //tempo para a janela nova abrir, carregar a decisão e montar o clone
                linha.style.backgroundColor = 'revert';
            }
            alert('maisPje: impressão em Lote finalizada..')
        };


        ancora.parentElement.appendChild(btImprimirTodos);


        for (const [pos, processo] of listaNum.entries()) {
            if (document.getElementById('maisPJe_imprimirVoto_' + pos)) { continue }
            let ancora = querySelectorByText('td[id*="abaPautaJulgamentoList:"]',processo);
            if (!ancora) { ancora = querySelectorByText('td[id*="votacaoAntecipadaList:"]',processo) }
            if (!ancora) { return }
            ancora = ancora.parentElement.querySelector('a[id*=":votoRelator"],a[id*=":linkVoto"]');
            let btImprimir = await botaoImprimir(pos);
            btImprimir.onclick = async function (event) {
                let idProcesso = await obterIdProcessoViaApi(processo);
                const tipoAcordao = await apis.idTipoDocumentoAcordao.executar(preferencias.trt);
                const acordaos = await apis.documentosProcesso.executar(preferencias.trt, {idProcesso, tipoDocumento: tipoAcordao.valorVariavel, ordemAscendente: 'false'});
                const documento = acordaos.resultado[0];
                let idDocumento = documento?.id;

                if (documento?.tipo == 'Acórdão') {
                    const htmlCodificado = await apis.documentoProcessoPorIdHtml.executar(preferencias.trt, {idProcesso, idDocumento});
                    let htmlDecodificado = '<html><head><meta name="viewport" content="width=device-width, initial-scale=1" charset="utf-8"><title>Acórdão ' + processo + '</title>';
                    htmlDecodificado += '</head><body onload="window.print(); window.close();">'
                    htmlDecodificado += htmlCodificado.modeloDocumento;
                    htmlDecodificado+= '</body></html>';
                    const novaJanela = URL.createObjectURL(new Blob([htmlDecodificado], { type: "text/html" }));
                    window.open(novaJanela, 'Acórdão ref. ' + processo + '.html');
                } else {
                    alert('Não foi encontrado minuta de Voto pendente de assinatura. Favor consultar os documentos do processo.')
                }
                return;

            };
            ancora.parentElement.appendChild(btImprimir)
        }

        async function botaoImprimir(id) {
            return new Promise(async resolve => {
                const atalho = document.createElement('a');
                atalho.id = 'maisPJe_imprimirVoto_' + id;
                atalho.style = 'cursor: pointer; background-color: revert; font-size: 14px; margin: 0px 5px; padding: 5px; border-radius: 15px;';
                atalho.title = 'Imprimir Voto';
                atalho.innerText = '🖨️';
                atalho.onmouseenter = function () { this.style.backgroundColor = '#0000001c' }
                atalho.onmouseleave = function() { this.style.backgroundColor = 'revert' }
                resolve(atalho);
            });
        }
    }

    async function incluirCaixaDeSelecao() {
        //a aba Análise Prévia não tem caixa de selecao.. precisa criar

        let tabela = document.querySelector('table[id*="votacaoAntecipadaList"]');
        if (!tabela) { return }

        //bt selecionar tudo
        let ancora = await esperarElemento('table[id*="votacaoAntecipadaList"] th');
        let cxSelecionarTodos = await criarCxSelecao('imprimirTudo');
        cxSelecionarTodos.title = 'Selecionar Todos'
        cxSelecionarTodos.onclick = async function (event) {
            let colecao = document.querySelectorAll('input[id*="maisPJe_selecionarVoto_"]');
            if (event.target.checked) {
                Array.from(colecao).forEach(function (cx) {
                    cx.checked = true;
                    cx.setAttribute('checked', 'checked');
                });
            } else {
                Array.from(colecao).forEach(function (cx) {
                    cx.checked = false;
                    cx.setAttribute('checked', 'none');
                });
            }

        };
        ancora.appendChild(cxSelecionarTodos);

        let linhas = document.querySelectorAll('table[id*="votacaoAntecipadaList"] tbody tr[class*="rich-table-row"]');
        console.log(linhas.length)
        for (const [pos, linha] of linhas.entries()) {
            if (document.getElementById('maisPJe_selecionarVoto_' + pos)) { continue }
            let cxSelecao = await criarCxSelecao(pos);
            linha.querySelector('td').insertBefore(cxSelecao, linha.querySelector('td').firstChild)
        }

        async function criarCxSelecao(id) {
            return new Promise(async resolve => {
                const atalho = document.createElement('input');
                atalho.id = 'maisPJe_selecionarVoto_' + id;
                atalho.type = 'checkbox';
                atalho.style = 'margin-left:-4px';
                atalho.onchange = function (e) {
                    console.log(e.target.checked)
                    let novaSituacao = e.target.checked ? 'checked' : 'none';
                    e.target.setAttribute('checked', novaSituacao);
                }
                resolve(atalho);
            });
        }
    }

    // FUNÇÃO QUE RETORNA A minuta de Voto não assinada
    async function obterUltimoDocumentoDoProcesso(idProcesso,ordenacao="false") {
        return new Promise(async resolve => {
            let urlBase = preferencias.trt;
            let grau_usuario = getGrauAsNumber(preferencias.grau_usuario);
            if (preferencias.trt.includes('dev015')) { urlBase = preferencias.trt.replace('dev015','pje') }
            let documentos = await apis.timelineProcesso.executar(preferencias.trt, { idProcesso, buscarMovimentos: "false", ordemAscendente: ordenacao });
            let ultimo = documentos[documentos.length-1];
            console.log(ultimo)
            return resolve(ultimo)
        });
    }


	async function consultaRapidaMagistrado(nome) {
		if(!nome){
			return;
		}
		if(!preferencias.trt){
			return;
		}

		let resposta = await obterMagistradosTribunalViaApi(nome);
		filtroIeSPauta2grau = await criarCaixaDeSelecao(resposta);

		if (filtroIeSPauta2grau.length > 0) {
			montarFiltro(filtroIeSPauta2grau);
			mapearProcessos(filtroIeSPauta2grau);
		}

		function criarCaixaDeSelecao(dados) {
			return new Promise(
				resolver => {
					if (!document.getElementById('maisPje_caixa_de_selecao_magistrados')) {

						let altura = window.innerHeight || document.documentElement.clientHeight || document.body.clientHeight;

						let elemento1 = document.createElement("div");
						elemento1.id = 'maisPje_caixa_de_selecao_magistrados';
						elemento1.style = 'position: fixed; width: 100%; height: ' + altura + 'px; top: 0; inset: 0px; background: #00000080; z-index: 10000; display: flex; align-items: center; justify-content: center; color: rgb(81, 81, 81); font-weight: bold; font-family: Open Sans,Arial,Verdana,sans-serif; text-align: center; flex-direction: column;';

						let container = document.createElement("div");
						container.style="height: auto; min-width: 35vw; display: inline-grid; background-color: white;padding: 15px;border-radius: 4px;box-shadow: 0 2px 1px -1px rgba(0,0,0,.2),0 1px 1px 0 rgba(0,0,0,.14),0 1px 3px 0 rgba(0,0,0,.12);";

						let titulo = document.createElement("span");
						titulo.style = "color: grey; border-bottom: 1px solid lightgrey;";
						titulo.innerText = "Lista de Magistrados";
						container.appendChild(titulo);

						let lista_de_magistrados_temp = [];
						let map = [].map.call(
							dados,
							function(dado) {
								let span = document.createElement("span");
								span.id = dado.idMagistrado
								span.style = "cursor: pointer; margin-top: 10px; padding: 10px;";
								span.innerText = dado.nomeMagistrado;
								span.onmouseenter = function () {
									span.style.backgroundColor  = 'lightgrey';
									span.style.color  = 'red';
									span.innerText = "Excluir";
								};
								span.onmouseleave = function () {
									span.style.backgroundColor  = 'white';
									span.style.color  = 'rgb(81, 81, 81)';
									span.innerText = dado.nomeMagistrado;
								};
								span.onclick = function () {
									this.remove();
									lista_de_magistrados_temp.splice(lista_de_magistrados_temp.findIndex(e => e.idMagistrado === dado.idMagistrado), 1);
								};
								container.appendChild(span);
								lista_de_magistrados_temp.push({ idMagistrado:dado.idMagistrado,nomeMagistrado:dado.nomeMagistrado });
							}
							//
						);

						const bt_continuar = criarBotaoComCoresPadrao("Verificar", 'maisPJe_bt_verificar');
						bt_continuar.onclick = function () {
							resolver(lista_de_magistrados_temp);
							document.getElementById('maisPje_caixa_de_selecao_magistrados').remove();
						};
						container.appendChild(bt_continuar);
						elemento1.appendChild(container);
						document.body.appendChild(elemento1);

					} else {
						resolver(null);
					}
				}
			);
		}
	}

	function montarFiltro(listaDeMagistradosParaVerificarIeS) {
        let ancora = document.getElementById('abaPautaJulgamentoListPanel') || document.querySelector('div[id*="votacaoAntecipadaListPanel"]');
        let containerNomes = document.createElement('div');
        containerNomes.style = 'display: grid;white-space: nowrap;grid-template-columns: repeat(4,auto);';
		listaDeMagistradosParaVerificarIeS.forEach( item => {
			if (!ancora) { return }
			let container = document.createElement("div");
			container.id = 'maisPje_filtroIeS';

			let div = document.createElement("span");
			div.id = 'maisPje_div_' + item.idMagistrado;
			div.style = 'background-color: #0078aa; color: #fff;padding: 7px 12px; font-size: 15px; border-radius: 16px; line-height: 40px; margin: 10px;';

			let span = document.createElement("span");
			span.innerText = item.nomeMagistrado;

			let fechar = document.createElement("span");
			fechar.style = 'background-color:#01638a; margin-left: 5px; padding: 0 4px; border-radius: 16px; cursor:pointer;';
			fechar.innerText = 'X';
			fechar.onclick = function() {
				document.getElementById('maisPje_div_' + item.idMagistrado).remove();
				listaDeMagistradosParaVerificarIeS.splice(listaDeMagistradosParaVerificarIeS.findIndex(e => e.idMagistrado === item.idMagistrado), 1);
				mapearProcessos(listaDeMagistradosParaVerificarIeS);
			}

			div.appendChild(span);
			div.appendChild(fechar);
			container.appendChild(div);
			containerNomes.appendChild(container);
		});
        ancora.insertBefore(containerNomes, ancora.children[1]);

        //montar relatório de impedimento e suspeiçã
        if (!document.getElementById('maisPje_div_relatorioIES')) {
            let containerRelatorio = document.createElement('div');

            let containerRelatorioBotoes = document.createElement('div');
            let btImprimir = document.createElement('a');
            btImprimir.id = 'maisPJe_imprimirRelatorioIES';
            btImprimir.style = 'cursor: pointer; background-image: linear-gradient(white, rgb(236, 244, 254)); font-size: 14px; margin: 16px; padding: 5px 59px; border: 2px solid white; outline: rgb(190, 214, 248) solid 1px; filter: brightness(1);';
            btImprimir.title = 'Imprimir regras IeS encontradas';
            btImprimir.innerText = 'Imprimir';
            btImprimir.onmouseenter = function () { this.style.filter = 'brightness(.8)' }
            btImprimir.onmouseleave = function() { this.style.filter = 'brightness(1)' }
            btImprimir.onclick = function() {
                imprimirElemento(document.getElementById('maisPje_div_relatorioIES'))
            }
            containerRelatorioBotoes.appendChild(btImprimir);

            let btVerificarTodos = document.createElement('a');
            btVerificarTodos.id = 'maisPJe_verificarIESemLote';
            btVerificarTodos.style = 'cursor: pointer; background-image: linear-gradient(white, rgb(236, 244, 254)); font-size: 14px; margin: 16px; padding: 5px 59px; border: 2px solid white; outline: rgb(190, 214, 248) solid 1px; filter: brightness(1);';
            btVerificarTodos.title = 'Verificar Todos';
            btVerificarTodos.innerText = 'Verificar Todos';
            btVerificarTodos.onmouseenter = function () { this.style.filter = 'brightness(.8)' }
            btVerificarTodos.onmouseleave = function() { this.style.filter = 'brightness(1)' }
            btVerificarTodos.onclick = async function() {
                while(true) {
                    await sleep(1000);
                    let ancora = await esperarElemento('tbody[class*="maisPje-verificacao-IeS-finalizado"]');
                    console.log(ancora);
                    let tabela = document.getElementById('abaPautaJulgamentoListPanel_body') || document.getElementById('votacaoAntecipadaListPanel_body');
                    let paginador = tabela.lastElementChild;
                    paginador.style.backgroundColor = 'lightsalmon';
                    let paginas = paginador.querySelectorAll('tbody td')[2].innerText;
                    let proximo = paginador.querySelector('tbody td input');
                    proximo.style.color = 'red';
                    console.log(parseInt(paginas) + ' == ' + proximo.value)
                    if (parseInt(paginas) == proximo.value) {
                        break
                    } else {
                        proximo.value = parseInt(proximo.value)+1;
                        triggerEvent(proximo,'change');
                    }
                    await sleep(1000);
                }
                document.querySelector('#maisPJe_imprimirRelatorioIES').click();
            }
            containerRelatorioBotoes.appendChild(btVerificarTodos);

            containerRelatorio.appendChild(containerRelatorioBotoes);

            let div_relatorio = document.createElement("div");
            div_relatorio.id = 'maisPje_div_relatorioIES';
            div_relatorio.style = 'border-top: 1px dashed #bed6f8;margin-top: 10px;padding: 10px;background-color: white;color: black;';
            div_relatorio.innerText = '\n\n\n\nRegras de Impedimento e/ou Suspeição encontradas:\n';
            containerRelatorio.appendChild(div_relatorio);

            document.body.appendChild(containerRelatorio);
        }

	}

	async function obterMagistradosTribunalViaApi(nome) {
		// console.log('obterMagistradosTribunalViaApi');
		let resposta = await fetch('https://' + preferencias.trt + '/pje-comum-api/api/pessoas/fisicas?pagina=1&tamanhoPagina=10000&especializacao=8&situacao=1');
		let dados = await resposta.json();
		let listaMagistradosInformados = nome.split(',');
		let listaMagistradosPesquisados = [];
		for (const [pos, magistrado] of dados.resultado.entries()) {

			listaMagistradosInformados.forEach( item => {

				if (magistrado.nome.includes(item.toUpperCase().trim())) {
					listaMagistradosPesquisados.push({idMagistrado:magistrado.id,nomeMagistrado:magistrado.nome})
				}

			});
		}
		return listaMagistradosPesquisados;
	}

	async function mapearProcessos(listaDeMagistradosParaVerificarIeS) {
		limparIconesIeS();

		if(!listaDeMagistradosParaVerificarIeS){ return }

		// console.log(listaDeMagistradosParaVerificarIeS.length);
		if(listaDeMagistradosParaVerificarIeS.length < 1){ return }

		let tabela = document.querySelector('table[id*="abaPautaJulgamentoList"]') || document.querySelector('table[id*="votacaoAntecipadaList"]');
		if (!tabela) { return }
		let listaNum = tabela.innerText.match(padraoProcesso).join().split(",");
		for (const [pos, processo] of listaNum.entries()) {
			let idProcesso = await obterIdProcessoViaApiPublica(processo,'maisPJe_obterImpedimentosSuspeicoesPautaSegundoGrau');
			let listaDeIeSPorMagistrados = [];
			for (const [pos, magistrado] of listaDeMagistradosParaVerificarIeS.entries()) {
				let ies = await fetchObterRegrasImpedimentoESuspeicao(idProcesso[0].id,magistrado.idMagistrado)
				//retorna true ou false
				listaDeIeSPorMagistrados.push({idMagistrado:magistrado.idMagistrado,nomeMagistrado:magistrado.nomeMagistrado,regrasIeS:ies});
			}

            let motivosIesPorMagistrado = [];
			let mensagem = '---MaisPJe: IMPEDIMENTO E/OU SUSPEIÇÃO---\n\n';
			listaDeIeSPorMagistrados.forEach( item => {
				// console.log('RegraIeS ( ' + item.nomeMagistrado + '): ' + item.regrasIeS)

				if (item.regrasIeS) {
					mensagem += item.nomeMagistrado + ': Encontrado Impedimento/suspeição\n';
                    motivosIesPorMagistrado.push({"nome":item.nomeMagistrado,"regras":item.regrasIeS})
                    addRegraNoRelatorio(processo,item.nomeMagistrado,item.regrasIeS);
				} else {
					mensagem += item.nomeMagistrado + ': OK\n';
				}
			})

			let ancora = querySelectorByText('td[id*="abaPautaJulgamentoList:',processo);
			if (!ancora) { ancora = querySelectorByText('td[id*="votacaoAntecipadaList:',processo) }
			if (!ancora) { return }
			let botao = document.createElement('button');
			botao.id = "maisPje_icone_IeS_" + processo;
			botao.style = 'float: right;border: none;background-color: transparent;width: auto;height: auto;';
			botao.title = mensagem;
            botao.onclick = async () => {
                let t = '';
                if (motivosIesPorMagistrado.length > 0) {
                    motivosIesPorMagistrado.forEach(item => {
                        item.regras.forEach(opcoes => {
                            t += '\nDesembargador(a): ' + item.nome + '\n\n';
                            opcoes.motivos.forEach(motivo => {
                                t += '   ' + motivo.tipo.adjetivo + ' pelo motivo de ' + motivo.texto + '\n';
                            });
                        })
                    });
                    await criarCaixaDeAlerta('Processo: ' + processo,t);
                } else {
                    t += '\nNão foram encontradas regras de Impedimento e/ou Suspeição para os desembargadores:\n';
                    listaDeIeSPorMagistrados.forEach(item => { t += '\n' + item.nomeMagistrado });
                    await criarCaixaDeAlerta('',t);
                }
            }
			let i = document.createElement('i');
			i.className = 'maisPje-icone thumbs-down';
			let estilo  = 'width:15px;height:15px;';
			i.style =  estilo + ((mensagem.includes('Encontrado')) ? 'background-color:red;' : 'background-color: green;transform: scaleX(-1) rotate(180deg);');
			botao.appendChild(i);
			ancora.appendChild(botao);

            //cria marcador para registrar que verificou todos
            if (pos == listaNum.length-1) {
                let tabela = ancora.closest('tbody');
                tabela.classList.add('maisPje-verificacao-IeS-finalizado');
            }
		}

        function addRegraNoRelatorio(processo,nome,regras) {
            let texto_relatorio = '';
            regras.forEach(opcoes => {
                texto_relatorio += '\nProcesso: ' + processo + '\nDesembargador(a): ' + nome + '\n';
                opcoes.motivos.forEach(motivo => {
                    texto_relatorio += 'Motivo: ' + motivo.tipo.adjetivo + ' pelo motivo de ' + motivo.texto + '\n';
                });
            })
            document.getElementById('maisPje_div_relatorioIES').innerText += texto_relatorio;
        }
	}

	async function fetchObterRegrasImpedimentoESuspeicao(idProcesso, idMagistrado) {
		let resposta = await fetch('https://' + preferencias.trt + '/pje-comum-api/api/regrasimpedimentomagistrado/regrasimpedimento?idMagistrado=' + idMagistrado + '&idProcesso=' + idProcesso);
		let dados = await resposta.json();
		if (dados.length > 0) {
			console.log(JSON.stringify(dados))
			return dados;
		} else {
			return null;
		}
	}

	function monitor_janela_pauta() {
		console.log("Extensão maisPJE (" + agora() + "): monitor_janela_pauta");
		let targetDocumento = document.body;
		let observerDocumento = new MutationObserver(function(mutationsDocumento) {
			mutationsDocumento.forEach(function(mutation) {
				if (!mutation.addedNodes[0] || !mutation.removedNodes[0]) { return }

                if (mutation.removedNodes[0]) {
                    if (!mutation.removedNodes[0].tagName) { return }
                    console.log(mutation.removedNodes[0].tagName + " : " + mutation.removedNodes[0].id + " : " + mutation.removedNodes[0].innerText);

                    //troca de abas
                    if (mutation.removedNodes[0].tagName.includes("DL") && mutation.removedNodes[0].id == "composicaoSessaoMessages") {
                        if (guardarFiltroStorage(filtroIeSPauta2grau)) {
                            iniciar();
                        }
                    }

                    //seleção de itens pela caixa de seleção : aba Pauta de julgamento
                    if (mutation.removedNodes[0].tagName.includes("DIV") && mutation.removedNodes[0].id == "divAbaPautaJulgamentoList") {
                        if (guardarFiltroStorage(filtroIeSPauta2grau)) {
                            iniciar();
                        }
                    }

                    //troca na paginação : aba Pauta de julgamento
                    if (mutation.removedNodes[0].tagName.includes("DIV") && mutation.removedNodes[0].id == "abaPautaJulgamentoListPanel") {
                        if (guardarFiltroStorage(filtroIeSPauta2grau)) {
                            iniciar();
                        }
                    }

                    //troca na paginação : aba Análise Prévia
                    if (mutation.removedNodes[0].tagName.includes("DIV") && mutation.removedNodes[0].id.includes("votacaoAntecipadaListPanel")) {
                        if (guardarFiltroStorage(filtroIeSPauta2grau)) {
                            iniciar();
                        }
                    }
                }

                //DIV : modalStatusContainer
			});
		});
		let configDocumento = { childList: true, subtree:true }
		observerDocumento.observe(targetDocumento, configDocumento); //inicia o MutationObserver
	}

	async function guardarFiltroStorage(filtro) {
		return new Promise(resolve => {
			browser.storage.local.set({'filtroIeSPauta2grau': filtro});
			return resolve(true);
		});
	}

	async function recuperarFiltroStorage(filtro) {
		return new Promise(resolve => {
			browser.storage.local.get('filtroIeSPauta2grau', function(result){
				return resolve(result.filtroIeSPauta2grau);
			});
		});
	}

	function limparIconesIeS() {
		document.querySelectorAll('div[id^="maisPje_icone_IeS_"]').forEach( item => {
			item.remove();
		});
	}
}
