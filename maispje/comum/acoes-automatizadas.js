function criarFiltro(nome,icone, filtros,color='#333') {
	const li = document.createElement("li");
	let filtro = document.createElement("button");
	filtro.style = `
	  cursor: pointer;
	  color: ${color};
	  position: relative;
	  top: 0.3vh;
	  opacity: .3;
	  border: none;
	  background: none;
	  font-size: inherit;
	`;
	filtro.setAttribute('aria-label',nome);
    // filtro.setAttribute('data-tooltip',nome);

	filtro.setAttribute('aria-pressed',false);
	filtro.onmouseenter  = function () {
		this.style.opacity = '.8';
		document.querySelector('#maisPje_caixa_de_selecao_filtroTexto').innerText = nome;
	}
	filtro.onfocus = filtro.onmouseenter
	filtro.onmouseleave  = function () {
		this.style.opacity = '.3';
		document.querySelector('#maisPje_caixa_de_selecao_filtroTexto').innerText = '';
	}
	filtro.onblur = filtro.onmouseleave;
	filtro.onclick = function (){
		const estavaPressionado = (filtro.getAttribute('aria-pressed') === 'true');
		const botoes = filtros.querySelectorAll('button');
		botoes.forEach(filtro => filtro.setAttribute('aria-pressed',false));
		filtro.setAttribute('aria-pressed', !estavaPressionado);
		for (const [pos, item] of document.querySelectorAll('select optgroup').entries()) {
			if (item.label === nome || estavaPressionado) {
				item.style.display = 'revert';
			} else {
				item.style.display = 'none';
			}
		}
	}
	let i = document.createElement("i");
	i.className = icone;
	filtro.appendChild(i);
	li.appendChild(filtro)
	return li;
}

function criarFiltrosAA(container) {
	const filtro = document.createElement("ul");
	filtro.style = 'min-height: 3vh;font-size: 1.3em; display: flex; justify-content: center; gap: 1vw; list-style: none; padding: 0; margin: 0';
	filtro.setAttribute("role", "list")

	filtro.appendChild(criarFiltro('ANEXAR DOCUMENTOS','icone paperclip t20', filtro));
	filtro.appendChild(criarFiltro('INTIMAÇÃO/EXPEDIENTE','icone envelope t20', filtro));
	filtro.appendChild(criarFiltro('AUTOGIGS','icone tag t20', filtro));
	filtro.appendChild(criarFiltro('DESPACHO','icone gavel t20', filtro));
	filtro.appendChild(criarFiltro('MOVIMENTOS','icone hand-paper t20', filtro));
	filtro.appendChild(criarFiltro('CHECKLIST','icone check-solid t20', filtro));
	filtro.appendChild(criarFiltro('NOMEAR PERITO','icone user-md t20', filtro));
	filtro.appendChild(criarFiltro('CÁLCULOS DO PROCESSO','icone calculator t20', filtro));
	filtro.appendChild(criarFiltro('RETIFICAR AUTUAÇÃO','icone pencil-alt t20', filtro));
	filtro.appendChild(criarFiltro('LANÇAR MOVIMENTOS','icone plus-square t20', filtro));
	filtro.appendChild(criarFiltro('CLICAR EM','icone mouse-pointer-solid t20', filtro));
	filtro.appendChild(criarFiltro('VARIADOS','icone tablets-solid t20', filtro));
	container.appendChild(filtro);

	let nomeEscolhido = document.createElement("div");
	nomeEscolhido.id = 'maisPje_caixa_de_selecao_filtroTexto';
	nomeEscolhido.style = 'min-height: 2vh;font-size: small;color: #333;opacity: .8; margin-top: 8px;';
	container.appendChild(nomeEscolhido);
}

/**
 *
 * Cria campo de texto que permite digitar o nome de alguma AA para encontrar mais facilmente na lista
 */
function criarFiltroTextoAAs(selectAcaoAutomatizada) {
	const search = document.createElement("search");
	search.setAttribute("aria-label", "Ações automatizadas")
	const filtroTexto = document.createElement("input");
	filtroTexto.setAttribute('aria-label','Filtro das Ações automatizadas')
	filtroTexto.setAttribute('placeholder','Filtro das Ações automatizadas')
	filtroTexto.id = 'maisPje_filtroTexto';
	filtroTexto.style.cssText = `
		padding: 8px 12px;
		margin: 6px 0;
		border: 1px solid #ccc;
		border-radius: 6px;
		font-size: 14px;
		font-family: inherit;
		background-color: #fff;
		color: #333;
		box-shadow: 0 1px 3px rgba(0,0,0,0.1);
		transition: border-color 0.2s ease, box-shadow 0.2s ease;
		width: -moz-available;
	`;

    filtroTexto.addEventListener('input', function () {
		filtrarOptionsPorTexto(filtroTexto.value, selectAcaoAutomatizada);
	});

	const btnLimpar = document.createElement("button");
    btnLimpar.type = "button";
    btnLimpar.id = "limparFiltroAA";
    btnLimpar.setAttribute("aria-label", "Limpar filtro de ações automatizadas");
    btnLimpar.setAttribute("title", "Limpar filtro de ações automatizadas");
    btnLimpar.innerHTML = '×';
    btnLimpar.style.cssText = `
        background: none;
        border: none;
        font-size: 30px;
        font-weight: bold;
        color: #666;
        cursor: pointer;
        width: 44px;
        height: 35px;
        opacity: 0.7;
        transition: opacity 0.2s ease;
    `;
    btnLimpar.addEventListener('mouseenter', () => btnLimpar.style.opacity = '1');
    btnLimpar.addEventListener('mouseleave', () => btnLimpar.style.opacity = '0.7');
	btnLimpar.addEventListener('click', () => {
        filtroTexto.value = '';
        filtroTexto.focus();
        filtroTexto.dispatchEvent(new Event('input'));
    });
	const container = document.createElement("div");
	container.style.cssText = `
		position: relative;
		display: inline-flex;
		width: 100%;
	`;
	container.appendChild(filtroTexto);
	container.appendChild(btnLimpar);
	search.appendChild(container);
	return search;
}

function criarOption(prefixo, texto, acao, aaAtual = '', classe = 'optionAA', estilo = '') {
	const option = document.createElement("option");
    if (typeof texto === 'string') {
        option.value = texto;
        option.innerText = texto;
    } else if (Array.isArray(texto)) {
        option.value = texto[0];
        option.innerText = texto[1] || texto[0];
    } else if (typeof texto === 'object' && texto !== null) {
        option.value = texto.valor || texto.value || '';
        option.innerText = texto.texto || texto.text || texto.value || '';
    }
	option.value = prefixo + option.value;
	option.innerText = prefixo + option.innerText;
    // option.classList.add(classe);
    option.className = classe;
	option.style = estilo;
    if (!!acao) {
        option.onclick = acao;
    }
    if (!!aaAtual && (option.value === aaAtual || option.innerText === aaAtual)){
        option.selected = true;
    }
	return option;
}

/**
 *
 * @param {string} nomeGrupo
 * @param {string} prefixo
 * @param {Object} opcoes
 * @param {function} acao
 * @param {*} aaAtual
 * @returns {HTMLOptGroupElement}
 */
function criarOptGroup(nomeGrupo, prefixo, opcoes, acao, aaAtual) {
	const optGroup = document.createElement("optgroup");
	optGroup.label = nomeGrupo;
	opcoes?.forEach(item => {
        let comVinculo = (item.vinculo && item.vinculo != 'Nenhum') ? 'optionAA vinculo' : 'optionAA';
        if (item.nm_botao?.includes('[concluir]')) { comVinculo = comVinculo + ' concluir' }
		let optionAAA = criarOption(prefixo, item.nm_botao || item, acao, aaAtual, comVinculo);
        if (item.vinculo && item.vinculo != 'Nenhum') { optionAAA.setAttribute('aavinculo',item.vinculo) }
		optGroup.appendChild(optionAAA);
	});
	return optGroup;
}

/**
 *
 * @param {Preferencias} preferencias
 * @param {function} acao
 * @param {*} aaAtual
 * @returns {HTMLDivElement} container com o select das ações automatizadas
 */
function criarSelectAcoesAutomatizadas(preferencias, acao, aaAtual) {
	function onTeclaSelect(event) {
		if (event.key === 'Enter') {
			acao();
		}
	  }
	const container = document.createElement("div");
	const selectAcaoAutomatizada = document.createElement("select");
    selectAcaoAutomatizada.id = "selectAcaoAutomatizada";
	selectAcaoAutomatizada.onkeyup=onTeclaSelect;
	selectAcaoAutomatizada.style = 'cursor: pointer; padding: 10px; border: 0; background-color: white; color: rgb(81, 81, 81); min-height: 60vh; min-width: 55vw; font-size:1.125em;';
	selectAcaoAutomatizada.size = 10;
	const searchFiltroTexto = criarFiltroTextoAAs(selectAcaoAutomatizada);
	container.appendChild(searchFiltroTexto);

	const clicarContinuar = acao;
	//Nenhuma
	const optionNenhumAA = criarOption('', 'Nenhum', clicarContinuar, aaAtual, 'optionNenhumAA');
	selectAcaoAutomatizada.appendChild(optionNenhumAA);

	//monta as acoes automatizadas de Anexar Documentos
	const optionGR1 = criarOptGroup('ANEXAR DOCUMENTOS', 'Anexar|', preferencias.aaAnexar, clicarContinuar, aaAtual);
	selectAcaoAutomatizada.appendChild(optionGR1);

	//monta as acoes automatizadas de Comunicação
	const optionGR2 = criarOptGroup('INTIMAÇÃO/EXPEDIENTE', 'Comunicação|', preferencias.aaComunicacao, clicarContinuar, aaAtual);
	selectAcaoAutomatizada.appendChild(optionGR2);

	//monta as acoes automatizadas de Autogigs
	const optionGR3 = criarOptGroup('AUTOGIGS', 'AutoGigs|', preferencias.aaAutogigs, clicarContinuar);
	selectAcaoAutomatizada.appendChild(optionGR3);

	//monta as acoes automatizadas de Despacho
	const optionGR4 = criarOptGroup('DESPACHO', 'Despacho|', preferencias.aaDespacho, clicarContinuar, aaAtual);

	const optionAADAceitarPrevencao = criarOption('Despacho|', 'bt_prevencaoAceitar', clicarContinuar, aaAtual);
	const optionAADRejeitarPrevencao = criarOption('Despacho|', 'bt_prevencaoRejeitar', clicarContinuar, aaAtual);
	optionGR4.prepend(optionAADRejeitarPrevencao);
	optionGR4.prepend(optionAADAceitarPrevencao);

	selectAcaoAutomatizada.appendChild(optionGR4);

	//monta as acoes automatizadas de Movimento
	const optionGR5 = criarOptGroup('MOVIMENTOS', 'Movimento|', preferencias.aaMovimento, clicarContinuar, aaAtual);
	selectAcaoAutomatizada.appendChild(optionGR5);

	//monta as acoes automatizadas de Checklist
	const optionGR6 = criarOptGroup('CHECKLIST', 'Checklist|', preferencias.aaChecklist, clicarContinuar, aaAtual);
	selectAcaoAutomatizada.appendChild(optionGR6);

	//monta as acoes automatizadas de Nomear Perito
	const optionGR7 = criarOptGroup('NOMEAR PERITO', 'Nomear Perito|', preferencias.aaNomearPerito, clicarContinuar, aaAtual);
	selectAcaoAutomatizada.appendChild(optionGR7);

	//monta as acoes automatizadas de Cálculos
	let aaItemCalculosDoProcesso = [['botao_abrirPjeCalc', 'Abrir PJeCalc'], ['botao_atualizacaoRapida', 'Atualização Rápida'], ['atualizacaorapidaRPVPrec', 'Atualização Rápida GPREC']];
	const optionGR8 = criarOptGroup('CÁLCULOS DO PROCESSO', 'CalculosDoProcesso|', aaItemCalculosDoProcesso, clicarContinuar, aaAtual);
	selectAcaoAutomatizada.appendChild(optionGR8);

	//monta as acoes automatizadas de Retificar Autuação
	let aaItemRetificarAutuacao = [['botao_retificar_autuacao_7', 'addAutor'], ['botao_retificar_autuacao_8', 'addRéu'], ['botao_retificar_autuacao_0', 'addUnião'], ['botao_retificar_autuacao_10', 'addMPT'], ['botao_retificar_autuacao_3', 'addLeiloeiro'], ['botao_retificar_autuacao_4', 'addPerito'], ['botao_retificar_autuacao_5', 'addTestemunha'], ['botao_retificar_autuacao_6', 'addTerceiro'], ['botao_retificar_autuacao_100Digital', 'Juízo 100% Digital'], ['botao_retificar_autuacao_tutelaLiminar', 'Pedido de Tutela'], ['botao_retificar_autuacao_Falencia', 'Falência/Rec.Judicial'], ['botao_retificar_autuacao_assunto', 'Assunto'], ['botao_retificar_autuacao_justicaGratuita', 'Justiça Gratuita'], ['botao_retificar_autuacao_associarProcesso', 'Associar Processo']];
	const optionGR9 = criarOptGroup('RETIFICAR AUTUAÇÃO', 'RetificarAutuação|', aaItemRetificarAutuacao, clicarContinuar, aaAtual);
	selectAcaoAutomatizada.appendChild(optionGR9);

	//monta as acoes automatizadas de Lançar Movimentos
	const optionGR10 = criarOptGroup('LANÇAR MOVIMENTOS', 'LançarMovimento|', preferencias.aaLancarMovimentos, clicarContinuar, aaAtual);
	selectAcaoAutomatizada.appendChild(optionGR10);

	let aaItemMenuDetalhes = ['Listar Todas','Concluso ao Magistrado', 'Movimentar Processo', 'Guardar dados das partes', 'Abrir o Gigs', 'Acesso a Terceiros', 'Anexar documentos', 'Audiências e Sessões', 'Download do processo completo', 'BNDT', 'Abrir cálculos do processo', 'Criar Intimação/Expediente', 'Controle de Segredo', 'Abre a tela com os dados financeiros', 'Visualizar intimações/expedientes do processo', 'Histórico de Sigilo', 'Lembretes', 'Lançar movimentos', 'Obrigação de Pagar', 'Pagamento', 'Perícias', 'Quadro de recursos', 'Reprocessar chips do processo', 'Retificar autuação', 'Retirar Valor Histórico', 'Verificar Impedimentos e Suspeições', 'Consultar Domicílio Eletrônico','Copiar Número do Processo'];
	const optionGR11 = criarOptGroup('CLICAR EM', 'Clicar em|', aaItemMenuDetalhes, clicarContinuar, aaAtual);
	selectAcaoAutomatizada.appendChild(optionGR11);

	//monta as acoes automatizadas de VARIADOS
	let optionGR12 = document.createElement("optgroup");
	optionGR12.label = 'VARIADOS';
	for (const [pos, item] of preferencias.aaVariados.entries()) {
		const prefixo = ['Atualizar Pagina', 'Fechar Pagina'].includes(item.nm_botao) ?
			item.nm_botao + '|' : 'Variados|';
		const optionVAR = criarOption(prefixo, item.nm_botao, clicarContinuar, aaAtual);
		optionGR12.appendChild(optionVAR);
	}
	selectAcaoAutomatizada.appendChild(optionGR12);

    selectAcaoAutomatizada.addEventListener('mouseover', function (event) {
        if (event.target.tagName === 'OPTION') {
            console.log(event.target.textContent);
            if (document.getElementById('maisPjeContainerMapaVinculos')) { document.getElementById('maisPjeContainerMapaVinculos').remove() }
            if (event.target.hasAttribute('aavinculo')) { criarMapaDosVinculos(event.target.textContent,event.target.getAttribute('aavinculo')) }
        }
	});

	container.appendChild(selectAcaoAutomatizada);
	return container;
}

/**
 *
 * @param {Preferencias} preferencias
 * @param {string} label
 * @param {*} aaAtual
 * @param {HTMLElement} [elementoDevolverFoco]
 * @returns
 */
async function criarCaixaDeSelecaoComAAs(preferencias, label, aaAtual = '', elementoDevolverFoco = undefined) {
	return new Promise(
		resolver => {
			const resolveDevolveFoco = (valor) => {
				elementoDevolverFoco?.focus();
				resolver(valor);
			};
			if (!document.getElementById('maisPje_caixa_de_selecao')) {

				// DESCRIÇÃO: REGRA DO TOOLTIP
				if (!document.getElementById('maisPje_tooltip_fundo')) {
					tooltip('fundo', true);
				}

				let elemento1 = criarPopup('maisPje_caixa_de_selecao', resolveDevolveFoco);
				let container = document.createElement("div");
				container.style="height: auto; min-width: 50vw; display: inline-grid; background-color: white;padding: 15px;border-radius: 4px;box-shadow: 0 2px 1px -1px rgba(0,0,0,.2),0 1px 1px 0 rgba(0,0,0,.14),0 1px 3px 0 rgba(0,0,0,.12);";

				const bt_continuar = criarBotaoComCoresPadrao('Salvar');
				bt_continuar.onclick = function () {
					resolveDevolveFoco(selectAcaoAutomatizada.value);
                    if (document.getElementById('maisPjeContainerMapaVinculos')) { document.getElementById('maisPjeContainerMapaVinculos').remove() }
					document.getElementById('maisPje_caixa_de_selecao').remove();
				};

				let titulo = document.createElement("h2");
				titulo.style = "color: #333; opacity: .8; border-bottom: 1px solid lightgrey;";
				titulo.innerText = label;
				container.appendChild(titulo);

				criarFiltrosAA(container);

				const containerSelectAcaoAutomatizada = criarSelectAcoesAutomatizadas(preferencias, () => bt_continuar.click(), aaAtual);
				const selectAcaoAutomatizada = containerSelectAcaoAutomatizada.querySelector('select');
				/** @type HTMLElement */
				const filtroTexto = containerSelectAcaoAutomatizada.querySelector('#maisPje_filtroTexto');
				container.appendChild(containerSelectAcaoAutomatizada);
				container.appendChild(bt_continuar);
				elemento1.appendChild(container);
				document.body.appendChild(elemento1);
                // elemento1.showModal();
				filtroTexto.focus();

			} else {
				resolveDevolveFoco(null);
			}
		}
	);

}

function criarMapaDosVinculos(aa_pai,v='Nenhum',descricao='') {
	return new Promise(resolver => {

		if (v == 'Nenhum') { return resolver(true) }

		let container = document.getElementById('maisPjeContainerMapaVinculos');
		if (container) { container.remove() }
		container = document.createElement("div");
		container.id = "maisPjeContainerMapaVinculos";

		let fundo = document.createElement("div");
		// fundo.style = 'position: fixed; width: 100%; height: 100%; inset: 0px; background: #008b8ba3 none repeat scroll 0% 0%; z-index: 10000; display: flex; align-items: center; color: rgb(81, 81, 81); font-size: 80px; font-weight: bold; text-align: center;  text-shadow: rgb(0, 0, 0) 1px 1px;flex-direction: column;top: 62vh;';
		fundo.style = "position: fixed; width: 100%; height: 100%; inset: 0px; background: #000000c4; z-index: 10000; display: flex; align-items: center; color: rgb(81, 81, 81); font-size: 80px; font-weight: bold; text-align: center; text-shadow: rgb(0, 0, 0) 1px 1px; flex-direction: column; top: " + (descricao ? "62%" : "92%") + ";"; //62

        let barra_descricao = document.createElement("div");
		barra_descricao.style = "overflow-y: auto; opacity: 0.98; text-align: center; color: white; font-size: 14px; height: auto;padding: 28px;text-shadow: none;";
		barra_descricao.innerText = descricao + '\n\n\nMapeamento dos Vínculos:';

		let barra_mapaVinculos = document.createElement("div");
		barra_mapaVinculos.style = "overflow-y: auto; opacity: 0.98; text-align: center; color: white;font-size: 14px; margin-top: 15px;";

		let lista = Array.isArray(v) ? v : v.split(',');
		lista = [aa_pai].concat(lista);//adiciona a própria AA como a primeira da lista

		for (const [pos, vinc] of lista.entries()) {

			if (vinc != 'Nenhum') {
				let bt = document.createElement("button");
				bt.name = vinc;
				bt.className = "mat-raised-button mat-primary ng-star-inserted";
				bt.style = "margin: 3px; z-index: 5; height: 4vh; border: 2px dashed #957e7e;outline: 2px dashed white; line-height: 30px;";
				bt.style.backgroundColor = (pos == 0) ? 'cadetblue' : 'burlywood';

				let numero = document.createElement("span");
				numero.style = "font-size: 20px; color: white; font-weight: bold; text-shadow: #bfbfbf 1px 1px, gray -1px -1px;margin-right: 10px;vertical-align: top;";
				numero.innerText = pos+1;
				bt.appendChild(numero);

				let span = document.createElement("span");
				span.className = "mat-button-wrapper";
				span.style = "vertical-align: super;"
				span.innerText = vinc;
				bt.appendChild(span);
				barra_mapaVinculos.appendChild(bt);

				if (lista[pos+1] != 'Nenhum') {
					let separador = document.createElement('i');
					// separador.className = 'botao-menu-texto fa fa-arrow-right';
                    separador.className = 'botao-menu-texto';
                    separador.innerText = '🡆';
					separador.style = 'color: white; height: 4vh;  display: inline-block; padding: 0px 10px; font-style: normal; font-size: 30px;';
					barra_mapaVinculos.appendChild(separador);
				}
			}
		}

        if (descricao) { fundo.appendChild(barra_descricao) }
		fundo.appendChild(barra_mapaVinculos);
		container.appendChild(fundo);
		document.body.appendChild(container);
		resolver(true);
	});
}

async function listaProcessoParaAcoesEmLote(listaPronta) {
	return new Promise(
		resolver => {
			console.log("      |___maisPJe: acoesacoesEmLoteContainer");

            /** @type {HTMLDialogElement} */
			let elemento1 = document.querySelector('dialog#maisPje_aaLote_lista_processos');
			if (elemento1) { elemento1.showModal(); return }

			elemento1 = criarDialogPopup('maisPje_aaLote_lista_processos');
			let container = document.createElement("section");
			container.style="text-align: center; font-weight: bold; height: auto; min-width: 35vw; display: inline-grid; background-color: white;padding: 15px;border-radius: 4px;box-shadow: 0 2px 1px -1px rgba(0,0,0,.2),0 1px 1px 0 rgba(0,0,0,.14),0 1px 3px 0 rgba(0,0,0,.12);";

			let titulo = document.createElement("h2");
			titulo.style = "color: grey; border-bottom: 1px solid lightgrey; margin: 0;";
			titulo.innerText = "Processos para Ação Automatizada em lote";
			container.appendChild(titulo);

			let lista_processos = document.createElement('textarea');
			lista_processos.id = 'maisPje_aaLote_lista_processos_textarea';
			lista_processos.placeholder = '\n\nDigite ou cole a sua lista de processos aqui.\n\nOs números devem estar no padrão CNJ.\n\nNão importa se eles estão sozinhos ou misturados com outras palavras de texto.\n\nAo clicar em "CONTINUAR" a extensão irá encontrar os números dos processos no texto e criará uma lista.\n\nApenas os processos que fazem parte dessa nova lista é que serão utilizados para a ação automatizada em lote.\n\nBom proveito!'
			lista_processos.ariaDescription = lista_processos.placeholder;
			// lista_processos.value = (listaPronta) ? listaPronta : '';
			lista_processos.value = (listaPronta) ? listaPronta : '';
			lista_processos.style = 'width: 100%; height: 75vh;';
			lista_processos.addEventListener("selectionchange", function (event) { ajustarNumeroDeProcessos() });
			container.appendChild(lista_processos);

			const bt_continuar = criarBotaoComCoresPadrao();
            bt_continuar.style = 'font-size: 18pt; padding: 5px';
			bt_continuar.onclick = async function () {
				let lista = lista_processos.value.match(padraoProcesso).join();
				resolver(lista.split(','));
				document.getElementById('maisPje_aaLote_lista_processos').remove();
			};
			container.appendChild(bt_continuar);
			elemento1.appendChild(container);
			document.body.appendChild(elemento1);
            if (elemento1.showModal && !elemento1.open) {
                elemento1.showModal();
            }
			// lista_processos.focus();
			if (listaPronta) { bt_continuar.click() }
		}
	);

	async function ajustarNumeroDeProcessos() {
		let conteudo = document.querySelector('#maisPje_aaLote_lista_processos_textarea').value;
		let padrao = /\d{20}/gm;
		if (padrao.test(conteudo)) {
			let listaTemp = conteudo.match(/\d{20}/gm).join();
			let novaLista = [];
			[].map.call(
				listaTemp.toString().split(','),
				function(item) {
					let numeroNovo = item.replace(/(\d{7})(\d{2})(\d{4})(\d{1})(\d{2})(\d{4})/g,"$1-$2.$3.$4.$5.$6");
					novaLista.push(numeroNovo)
				}
			);
			// let novoConteudo = conteudo.replace(/(\d{7})(\d{2})(\d{4})(\d{1})(\d{2})(\d{4})/gm,"$1-$2.$3.$4.$5.$6");
			document.querySelector('#maisPje_aaLote_lista_processos_textarea').value = novaLista.toString();
			await sleep(500);
		}
	}
}
