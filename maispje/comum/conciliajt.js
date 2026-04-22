// {"vl_predicao":"1","dt_predicao":"16/12/2023","ds_predicao":"Algum texto descrevendo a predição"}
const NAO_DEFINIDO = 'N/D';

/**
 * Classe que representa um potencial de conciliação do sistema ConciliaJT.
 *
 * Esta classe armazena as informações relacionadas a um potencial de conciliação, como a cor, a dica associada, o ícone e a opção de abrir link.
 */
class PotencialConciliaJT {
    /**
     * Cria uma instância de PotencialConciliaJT.
     *
     * @param {string} potencial - O nome ou descrição do potencial de conciliação.
     * @param {string} cor - A cor associada ao potencial, usada para representar visualmente o estado.
     * @param {string} dica - A descrição adicional sobre o potencial de conciliação.
     * @param {string} icone - O ícone associado ao potencial, geralmente representando o tipo de conciliação.
     * @param {boolean} [abrir_link=false] - Indica se ao clicar no ícone deve-se abrir um link. Valor padrão é `false`.
     */
    constructor(potencial, cor, dica, icone, abrir_link = false) {
        /**
         * @property {string} potencial - O nome ou descrição do potencial de conciliação.
         */
        this.potencial = potencial;

        /**
         * @property {string} cor - A cor associada ao potencial.
         */
        this.cor = cor;

        /**
         * @property {string} dica - A dica associada ao potencial, fornecendo contexto ou mais informações.
         */
        this.dica = dica;

        /**
         * @property {string} icone - O ícone associado ao potencial de conciliação.
         */
        this.icone = icone;

        /**
         * @property {boolean} abrir_link - Indica se um link deve ser aberto ao clicar no ícone.
         * Se `true`, um link será aberto; se `false`, não será.
         */
        this.abrir_link = abrir_link;
    }
}
const potenciais = new Map();

potenciais.set('N/A', new PotencialConciliaJT(
    'N/A', "color: dimgray;",
    "N/A: Esta classe judicial não possui potencial de acordo computado.",
    "fas fa-thermometer-empty"
));

potenciais.set("0", new PotencialConciliaJT(
    "0", "color: darkred;",
    "0: Processo com potencial de acordo muito baixo.",
    "fas fa-thermometer-empty"
));

potenciais.set("1", new PotencialConciliaJT(
    "1", "color: darkred;",
    "1: Processo com potencial de acordo baixo.",
    "fas fa-thermometer-quarter"
));

potenciais.set("2", new PotencialConciliaJT(
    "2", "color: black;",
    "2: Processo com potencial de acordo incerto.",
    "fas fa-thermometer-half"
));

potenciais.set("3", new PotencialConciliaJT(
    "3", "color: black;",
    "3: Processo com potencial de acordo incerto.",
    "fas fa-thermometer-half"
));

potenciais.set("4", new PotencialConciliaJT(
    "4", "color: darkgreen;",
    "4: Processo com bom potencial de acordo.",
    "fas fa-thermometer-three-quarters"
));

potenciais.set("5", new PotencialConciliaJT(
    "5", "color: darkgreen;",
    "5: Processo com alto potencial de acordo.",
    "fas fa-thermometer-full"
));

potenciais.set("nao_habilitado", new PotencialConciliaJT(
    "nao_habilitado", "color: dimgray;",
    "Conheça o projeto Concilia JT.",
    "fas fa-thermometer-empty", true
));

// Valor padrão para potenciais desconhecidos
const defaultPotencial = new PotencialConciliaJT(
    "default", "color: dimgray;",
    "N/D: Este processo não possui avaliação de potencial de acordo.",
    "fas fa-thermometer-empty"
);


/**
 * APRESENTAR O INDICE CONCILIAJT
 * @param {string} nrProcesso
 * @returns {PotencialConciliaJT} com o potencial daquele processo
 */
function encontrarPotencial(nrProcesso) {
	let potencial;
	let descricaoRest;
	if (preferencias.conciliajt.enabled) {
		if (!nrProcesso) {
			potencial = NAO_DEFINIDO;
		} else {
			let folderPrefix = '0';
			if (nrProcesso.length >= 2) {
				folderPrefix = nrProcesso.slice(-2);
			}

			const url = preferencias.conciliajt.url + nrProcesso;

			var request = new XMLHttpRequest();
			request.responseType = 'json';
			request.open('GET', url, false); // `false` makes the request synchronous
			request.send(null);
			if (request.status === 200) {
				/**
				 * @type PotencialRest
				 */
				var jsonResponse = request.response;
				potencial =  jsonResponse.vl_predicao;
				descricaoRest = jsonResponse.ds_predicao;
			} else {
				potencial =  NAO_DEFINIDO;
			}
		}
	} else {
		potencial =  'nao_habilitado';
	}
	const potencialFinal = potenciais.get(potencial) || defaultPotencial;
	if (descricaoRest && descricaoRest.trim() !== '') {
		potencialFinal.dica = descricaoRest;
	}
    return potencialFinal;
}

/**
 * cria um link com o icone da avaliacao do Concilia JT
 * @param {string} processoNumero
 * @returns {Promise<HTMLAnchorElement>} com o link
 */
async function criarLinkPotencialConciliaJT(processoNumero, fontSize = ' ') {
	return new Promise(resolve => {
		const a = document.createElement("a");
		if (!preferencias.conciliajt.enabled && !preferencias.conciliajt.ads_enabled) {
			a.style.display = 'none';
			a.setAttribute('aria-hidden', 'true');
			return a;
		}

		const info = encontrarPotencial(processoNumero);
		a.id = "maispje_item_container_lia";
		a.className = "mat-tooltip-trigger link ng-star-inserted";
		a.setAttribute('aria-label', info.dica);
		a.setAttribute('mattooltip', info.dica);
		a.setAttribute('maisPje-tooltip-menuAbaixo', info.dica);
		a.setAttribute('maisPje-tooltip-abaixo', info.dica);
		if (info.abrir_link && preferencias.conciliajt.ads_enabled) {
			a.onclick = function () {
				window.open(preferencias.conciliajt.ads_url, '_blank', 'dependent=yes');
			};
		} else {
			a.setAttribute('role', 'presentation');
		}
		const i = document.createElement("i");
		i.className = info.icone;
		i.style = fontSize + info.cor;
		i.setAttribute('aria-hidden', 'true');
		a.appendChild(i);
		return resolve(a);
	});
}

/**
 * @param {number} trt
 * @param {boolean} [forcar]
 * @returns {Promise<ConfigURLs>}
 */
async function obterUrlsConciliaJT(trt, forcar = false) {
    return new Promise(resolve => {
        if (!trt) {
            console.info('nao tem TRT definido, não consulta configUrls...')
            return resolve(undefined);
        }
		//CONTROLA A CONSULTA DO ACESSO AO PROJETO CONCILIA PARA APENAS 1 VEZ POR DIA
		browser.storage.local.get(['verificadorDiario','configURLs']).then(async function(result) {
			let hoje = new Date().getDate();
			let verificador = false;
			let configBase = result.configURLs; //configurações existentes do storage

			if (!result.verificadorDiario || typeof(configBase) == "undefined") {
				verificador = true;
			} else {
				let diaVerificador = result.verificadorDiario;
				if (diaVerificador != hoje) {
					verificador = true;
				}
			}

			if (forcar || verificador) {

				let url = 'https://www.trt12.jus.br/repo/maispje/Downloads/versoes/configURLs.json';

				configBase = await fetch(url).then(function (response) {  //configurações existentes do site
					console.log('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
					console.log('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
					console.log('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
					console.log(`FETCH: ${url}`)
					console.log('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
					console.log('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
					console.log('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
					return response.json();
				})
				.then(data=> data[trt] || null)
				.catch(function (err) {
					console.error('configUrl error', err, data, trt)
					alert(`maisPJE: erro ao acessar  ${url}`);
					return null;
				});

				// console.log(JSON.stringify(configBase))
				//guarda as novas configurações no storage
				await salvarConfigUrls(configBase,hoje);
			}

			return resolve(configBase);

		});

    });
}

/**
 * @param {ConfigURLs} configuracaoBase
 * @param {number} dia
 * @returns {Promise<boolean>}
 */
async function salvarConfigUrls(configuracaoBase, dia) {
	return new Promise(resolve => {
        if (!configuracaoBase || !dia) { //nao salva se um dos valores não estiver definido
            return resolve(false);
        }
		let guardarStorage1 = browser.storage.local.set({ 'configURLs': configuracaoBase });
		let guardarStorage2 = browser.storage.local.set({ 'verificadorDiario': dia });
		Promise.all([guardarStorage1,guardarStorage2]).then(values => {
			return resolve(true)
		});
	});
}

/**
 * @param {Number} num_trt
 * @param {GrauUsuario} grauPJe
 * @returns {Promise<ConciliaJTConfig>} configuração do ConciliaJT para o TRT e grau informados.
 */
async function buscaConfigConciliaJT(num_trt, grauPJe) {
	let dados = await obterUrlsConciliaJT(num_trt);
	// if (!num_trt || !grauPJe) { dados = null } // nao funcionava com o TST, pois 0 eh false no js
	const configPadrao  = {'ads_url':'','ads_enabled':false,'enabled':false,'url':''}; //TODO: pra que me importam as URLs se nao tem nada habilitado?

	/**
	 * @type ConciliaJTConfig
	 */
    const configConcilia =  dados?.conciliajt?.[grauPJe] ?? configPadrao;
	const url = configConcilia?.url || '';
	if (url && !url.endsWith('/')) {
		configConcilia.url += '/';
	}
    return configConcilia;
}

async function conciLIAnaPauta(linha) {
	return new Promise(async resolve => {
		console.log('conciLIAnaPauta')
		if (!preferencias.conciliajt.enabled && !preferencias.conciliajt.ads_enabled) { return }

		let el = document.querySelectorAll('td[id="pjextension_coluna_lia"]') || document.querySelectorAll('maisPJe-conciliaJT');
		if (el) {
			let limpar = [].map.call(
				el,
				function(elemento) {
					elemento.remove();
				}
			);
		}

		console.log('2')
		let tabela = document.querySelector('pje-data-table[nametabela="Horários do dia"]') || document.querySelector('pje-inteligente-semanal table[role="grid"]');

		if (!tabela) { return resolve(false) }

		console.log('3')

		if (tabela.tagName == "PJE-DATA-TABLE") { //PAUTA TRADICIONAL


			if (!linha) { return resolve(false) }
			let tbody = tabela.getElementsByTagName('tbody')[0];
			let tr = tbody.getElementsByTagName('tr');
			if (!tr) {
				return resolve(false)
			}
			if (preferencias.conciliajt.enabled || preferencias.conciliajt.ads_enabled) { //FIXME: Preciso desse if se já tem outro no inicio do metodo? Se chegou aqui, eh pq essa condicao eh sempre true!

				//INSERE O ICONE DO CONCILIAJT NO CABEÇALHO DA TABELA (APENAS NA PAUTA TRADICIONAL)
				if (!document.getElementById('pjextension_coluna_lia_cabecalho') && document.querySelector('table[name="Horários do dia"]')) {
					let tabela = document.querySelector('table[name="Horários do dia"]').firstElementChild.firstElementChild;
					let th = document.createElement("th");
					th.className = "th-class centralizado ng-star-inserted";
					th.setAttribute('scope','col');
					let a0 = document.createElement("a");
					a0.id = "pjextension_coluna_lia_cabecalho";
					a0.setAttribute('title', 'Avaliação Concilia JT');
					let i0 = document.createElement("i");
					i0.className = "fas fa-handshake";
					i0.style = "font-size: 1.7rem;";
					a0.appendChild(i0);
					th.appendChild(a0);
					tabela.appendChild(th);
				}

				let numeroProcesso = await extrairNumeroProcesso(linha.innerText);
				if (!numeroProcesso) { return resolve(false) }

				let td = document.createElement("td");
				td.id = "pjextension_coluna_lia";
				td.className = "centralizado td-class ng-star-inserted";
				const a = await criarLinkPotencialConciliaJT(numeroProcesso, "font-size: 2rem; ");
				td.appendChild(a);
				linha.appendChild(td);
			}

			return resolve(true);

		} else { //PAUTA INTELIGENTE

			// if (!preferencias.conciliajt.enabled && !preferencias.conciliajt.ads_enabled) { return }

			//DESCRIÇÃO: REGRA DO TOOLTIP
			if (!document.getElementById('maisPje-tooltip-menuAbaixo')) {
				tooltip('menuAbaixo');
			}

			let carregamento = await esperarElemento('div[class*="container-loading"] mat-progress-spinner')
			await esperarDesaparecer(carregamento)

			let linhasTabela = await esperarColecao('table tbody td mat-card div[class*="opcoes-card"]');

			if (!linhasTabela) { return resolve(false) }

			for (const [pos, linha] of linhasTabela.entries()) {
				// console.log('pos: ' + pos + '   -   ' + linha.parentElement.innerText)
				if (linha.parentElement.innerText.match(padraoProcesso)) {
						let processoNumero = linha.parentElement.innerText.match(padraoProcesso).join();
						let el_concilia = document.createElement("maisPJe-conciliaJT");
						el_concilia.id = 'maisPJe_container_lia'
						el_concilia.style = 'margin-left: 10px;font-size: 1.6em;';

						const a = await criarLinkPotencialConciliaJT(processoNumero, "font-size: 1.75rem; ");
						el_concilia.appendChild(a);
						linha.appendChild(el_concilia);
					}

			}

			return resolve(true);

		}

	});
}

async function conciLIAnaTriagemInicial() {
	if (!preferencias.conciliajt.enabled && !preferencias.conciliajt.ads_enabled) { return }
	let el = document.querySelectorAll('td[id="maisPje_coluna_lia"]');
	if (el) {
		let limpar = [].map.call(
			el,
			function(elemento) {
				elemento.remove();
			}
		);
	}
	// let tabela = await esperarElemento('pje-data-table[nametabela="Tabela de Processos"]');
	let tabela = await esperarElemento('pje-data-table[nametabela="Tabela de Atividades"],pje-data-table[nametabela="Tabela de Processos"]');

	if (!tabela) {
		return
	}

	await esperarElemento('span[class="total-registros"]');

	//DESCRIÇÃO: REGRA DO TOOLTIP
	if (!document.getElementById('maisPje_tooltip_abaixo')) { tooltip('abaixo') }

	// const linhasTabela = await esperarColecao('table tbody tr');
	const linhasTabela = await esperarColecao('table[name="Tabela de Atividades"] tbody tr, table[name="Tabela de Processos"] tbody tr');

	if (!linhasTabela) {
		return
	}
	for (const [key, linha] of linhasTabela.entries()) {
		const ancora = linha.querySelector('div[class*="container-icones-processuais"]');
		if (!ancora.querySelector('#maisPje_coluna_lia')) {
			let div = document.createElement("div");
			div.id = "maisPje_coluna_lia";
			div.style = "margin-left: 10px;";
			ancora.appendChild(div);
			const processoNumero = linha.innerText.match(padraoProcesso).join();
			criarLinkPotencialConciliaJT(processoNumero, " font-size: 1.75rem; ").then((a) => div.replaceChildren(a));
		}
	}
}
