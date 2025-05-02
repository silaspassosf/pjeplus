browser.runtime.onInstalled.addListener(function(details) {
	if(details.reason == "install"){
		//Ao instalar a extensão
		browser.storage.local.set({
			extensaoAtiva: false,
			videoAtualizacao : false, //Se quiser que o painel de novidades abra automaticamente marque como FALSE
			versaoPje : "",
			desativarAjusteJanelas : true,
			maisPje_velocidade_interacao : 0.5,
			menu_kaizen : {
				principal : {posx : '96%', posy : '92%'},
				detalhes : {posx : '96%', posy : '92%'},
				tarefas : {posx : '96%', posy : '92%'},
				sisbajud : {posx : '93%', posy : '80%'},
				serasajud: {posx: '93%', posy: '80%'}, 
				renajud: {posx: '93%', posy: '80%'}, 
				cnib: {posx: '93%', posy: '80%'}, 
				ccs: {posx: '93%', posy: '80%'},
				prevjud: {posx: '93%', posy: '80%'},
				protestojud: {posx: '93%', posy: '80%'},
				sniper: {posx: '93%', posy: '80%'},
				censec: {posx: '93%', posy: '80%'},
				celesc: {posx: '93%', posy: '80%'},
				casan: {posx: '93%', posy: '80%'},
				sigef: {posx: '93%', posy: '80%'},
				infoseg: {posx: '93%', posy: '80%'},
				saj: {posx: '93%', posy: '80%'},
			},
			impressoraVirtual: [],
			tempAAEspecial: [],
			aaLancarMovimentos:[
				{id:"botao_lancar_movimento_0",nm_botao:"para Contadoria:atualização"},
				{id:"botao_lancar_movimento_1",nm_botao:"para Contadoria:liquidação"},
				{id:"botao_lancar_movimento_2",nm_botao:"para Contadoria:retificação"},
				{id:"botao_lancar_movimento_3",nm_botao:"para Contadoria:DeterminaçãoJudicial"},
				{id:"botao_lancar_movimento_8",nm_botao:"para Contadoria:diligência"},
				{id:"botao_lancar_movimento_10",nm_botao:"para Vara:cumprida diligência"},
				{id:"botao_lancar_movimento_4",nm_botao:"TRT:recurso"},
				{id:"botao_lancar_movimento_5",nm_botao:"Publicação de Pauta"},
				{id:"botao_lancar_movimento_6",nm_botao:"Recebido: para Prosseguir"},
				{id:"botao_lancar_movimento_7",nm_botao:"Leilão:designado"},
				{id:"botao_lancar_movimento_9",nm_botao:"da Contadoria para Vara:prosseguimento"}
			],
			configURLs : {descricao:'',urlSiscondj:'',idSiscondj:'',urlSAOExecucao:''},
			sisbajud: {juiz: '', vara: '', cnpjRaiz: '', teimosinha: '', contasalario: '', naorespostas: '', valor_desbloqueio: '', banco_preferido: '', agencia_preferida: '', preencherValor: '', confirmar: '', executarAAaoFinal: '', salvarEprotocolar: ''},
		}, function() {
			requestTermoDeUso();
		});
	}else if(details.reason == "update"){		
		
		// browser.storage.local.get('concordo', function(result){
			// if (!result.concordo) {
				// requestTermoDeUso();
			// }
		// });
		
		// browser.storage.local.get('extensaoAtiva', function(result){
			// if (!result.extensaoAtiva) {
				// mudarIcone('+PJe: Desligado', 'ico_16_off.png');
			// }
		// });
		
		//Ao atualizar a extensão
		browser.storage.local.set({
			extensaoAtiva: false,
			videoAtualizacao : false, //Se quiser que o painel de novidades abra automaticamente marque como FALSE
			tempBt : [], //limpa a variável das ações automatizadas
			processo_memoria : "",
			versao: 0,
			versaoPje: "",
			tempAR : "",
			tempF2 : "",
			tempF3 : "",
			aaLancarMovimentos:[
				{id:"botao_lancar_movimento_0",nm_botao:"para Contadoria:atualização"},
				{id:"botao_lancar_movimento_1",nm_botao:"para Contadoria:liquidação"},
				{id:"botao_lancar_movimento_2",nm_botao:"para Contadoria:retificação"},
				{id:"botao_lancar_movimento_3",nm_botao:"para Contadoria:DeterminaçãoJudicial"},
				{id:"botao_lancar_movimento_8",nm_botao:"para Contadoria:diligência"},
				{id:"botao_lancar_movimento_10",nm_botao:"para Vara:cumprida diligência"},
				{id:"botao_lancar_movimento_4",nm_botao:"TRT:recurso"},
				{id:"botao_lancar_movimento_5",nm_botao:"Publicação de Pauta"},
				{id:"botao_lancar_movimento_6",nm_botao:"Recebido: para Prosseguir"},
				{id:"botao_lancar_movimento_7",nm_botao:"Leilão:designado"},
				{id:"botao_lancar_movimento_9",nm_botao:"da Contadoria para Vara:prosseguimento"}
			],
			tempAuto : 10,
			anexadoDoctoEmSigilo: -1,
			impressoraVirtual: [],
			tempAAEspecial: [],
			configURLs : {descricao:'',urlSiscondj:'',idSiscondj:'',urlSAOExecucao:''}
		}, function() {
			requestTermoDeUso();
			// browser.runtime.openOptionsPage();
		});		
	}
});

var janelatAtiva;
function notify(message) {
    switch (message.tipo) {
        case 'abrirConfiguracoes':
            browser.runtime.openOptionsPage();
            break
        case 'posicionarJanela':
            browser.windows.getCurrent().then((janela) => posicionarJanela(janela.id, janela.opener, message.left, message.top, message.width, message.height));
			break
		case 'storage_guardar':
			storage_guardar(message.chave, message.valor);
			break
		case 'storage_vinculo':
			storage_vinculo(message.valor);
			break
		case 'storage_limpar':
			storage_limpar(message.valor);
			break
		case 'criarAlerta':
			Alerta(message.valor.trim(), message.icone);
			break
		case 'permissao':
			requestTermoDeUso();
			break
		case 'abrirOpcoes':
			abrirOpcoes(message.script);
			break
		case 'iconeNavegador':
			mudarIcone(message.valor, message.icone);
			break
		case 'obterPartesDoProcesso':
			pjeApiObterPartesDoProcesso(message.trt, message.id, message.processo);
			break
		case 'iniciar':
			executarScript(message.script);			
			break;
		case 'criarJanela':
			criarJanela(message.url, message.posx, message.posy, message.width, message.height);
			break
		case 'insertCSS':
			insertCSS(message.file);
			break
		// case 'atualizarJanela':
		// 	chrome.tabs.query({active: true, lastFocusedWindow: true}, tabs => {
		// 		let url = tabs[0].url;
		// 		console.log('atualizarJanela' + url)
		// 		browser.tabs.reload(tabs[0].id);
		// 	});
		// 	break
        default:
            console.error('Mensagem com tipo invalido: ' + message.tipo)
    }
}

function requestTermoDeUso() {	
	mudarIcone('+PJe: Desligado', 'ico_16_off.png');
	browser.tabs.create({
		url: browser.runtime.getURL("aviso.html"),
		active: true
	});
}

function abrirOpcoes(url) {	
	console.log(url)
	browser.tabs.create({
		url: browser.runtime.getURL(url),
		active: true
	});
}

function storage_limpar(param) {
	console.debug('maisPJe: limpando a memoria... ' + param);
	if (param == "pjExtension_depositos") {
		let limparStorage = browser.storage.local.set({'pjExtension_depositos': []});
		Promise.all([limparStorage]).then(values => {
			console.debug('maisPJe: background: pjExtension_depositos... excluido');
		});
	} else if (param == "tempBt") {
		let limparStorage = browser.storage.local.set({'tempBt': []});
		Promise.all([limparStorage]).then(values => {
			console.debug('maisPJe: background: tempBt... excluido');
		});
	} else if (param == "tempAAEspecial") {
		let limparStorage = browser.storage.local.set({'tempAAEspecial': []});
		Promise.all([limparStorage]).then(values => {
			console.debug('maisPJe: background: tempAAEspecial... excluido');
		});
	} else if (param == "tempAR") {
		let limparStorage = browser.storage.local.set({'tempAR': ''});
		Promise.all([limparStorage]).then(values => {
			console.debug('maisPJe: background: tempAR... excluido');
		});
	} else if (param == "AALote") {
		let limparStorage = browser.storage.local.set({'AALote': ''});
		Promise.all([limparStorage]).then(values => {
			console.debug('maisPJe: background: AALote... excluido');
		});
	} else if (param == "tempBt,AALote") {
		let limparStorage1 = browser.storage.local.set({'tempBt': []});
		let limparStorage2 = browser.storage.local.set({'AALote': ''});
		Promise.all([limparStorage1,limparStorage2]).then(values => {
			console.debug('maisPJe: background: tempBt... excluido');
			console.debug('maisPJe: background: AALote... excluido');
		});
	} else if (param == "tempBt,tempAR,AALote,tempAAEspecial,anexadoDoctoEmSigilo") {
		let limparStorage1 = browser.storage.local.set({'tempBt': []});
		let limparStorage2 = browser.storage.local.set({'AALote': ''});
		let limparStorage3 = browser.storage.local.set({'tempAAEspecial': []});
		let limparStorage4 = browser.storage.local.set({'anexadoDoctoEmSigilo': -1});
		let limparStorage5 = browser.storage.local.set({'tempAR': ''});
		Promise.all([limparStorage1,limparStorage2,limparStorage3,limparStorage4,limparStorage5]).then(values => {
			console.debug('maisPJe: background: tempBt... excluido');
			console.debug('maisPJe: background: AALote... excluido');
			console.debug('maisPJe: background: anexadoDoctoEmSigilo... excluido');
			console.debug('maisPJe: background: tempAAEspecial... excluido');
			console.debug('maisPJe: background: tempAR... excluido');
		});	
	} else if (param == "impressoraVirtual") {
		let limparStorage = browser.storage.local.set({'impressoraVirtual': []});
		Promise.all([limparStorage]).then(values => {
			console.debug('maisPJe: background: maispje_assistente_impressao... excluido');
		});
	} else if (param == "processo_memoria") {
		let limparStorage = browser.storage.local.set({'processo_memoria': ''});
		Promise.all([limparStorage]).then(values => {
			console.debug('maisPJe: background: processo_memoria... excluido');
		});
	}
}

async function storage_vinculo(param) {
	// console.info('*****storage_vinculo(' + param + ')')
	param = await conferirVinculoEspecial(param);
	return browser.storage.local.set({'tempBt': ['vinculo', param]});
	
	//FUNÇÃO RESPONSÁVEL POR VERIFICAR A EXISTÊNCIA DE AAEspecial
	async function conferirVinculoEspecial(aaVinculo='Nenhum') {
		return new Promise(async resolve => {
			console.log('maisPJe: conferirVinculoEspecial... ' + param);
			let tempAAEspecial = await getLocalStorage('tempAAEspecial');
			// console.debug('1------- tempAAEspecial: ' + tempAAEspecial);// await sleep(1750 + parseInt(preferencias.maisPje_velocidade_interacao));
			// console.debug('2------- aaVinculo: ' + aaVinculo);
			
			aaVinculo = (tempAAEspecial == '' || tempAAEspecial == 'Nenhum') ? aaVinculo : tempAAEspecial;
			tempAAEspecial = Array.isArray(aaVinculo) ? aaVinculo : aaVinculo.split(','); //transformo a string em array				
			aaVinculo = tempAAEspecial.shift(); //retiro a primeira posição e, ao mesmo tempo, renovo o array
			
			console.log('   |________(Novo vinculo): ' + aaVinculo);
			console.log('   |________(AAESpecial remanescente): ' + tempAAEspecial);
			
			browser.storage.local.set({'tempAAEspecial': tempAAEspecial});
			let novoTempAAEspecial = await getLocalStorage('tempAAEspecial');
			// console.debug('1------- novoTempAAEspecial: ' + novoTempAAEspecial);
			return resolve(aaVinculo);
		});	
	}
}

function storage_guardar(chave,valor) {
	console.log(chave);
	let guardarStorage;
	switch (chave) {
        case 'grau_usuario':
			guardarStorage = browser.storage.local.set({'grau_usuario': valor});
            break;
		case 'tempAR':
			guardarStorage = browser.storage.local.set({'tempAR': valor});
			break;		
	}

	if (!guardarStorage) { 
		console.debug('maisPJe: background: ' + chave + '(' + valor + ')... ERRO 1759!!! mapear chave!!!');
		return;
	}
	
	Promise.all([guardarStorage]).then(values => {
		console.debug('maisPJe: background: ' + chave + '(' + valor + ')... salvo com sucesso');
	});
}

function posicionarJanela(id, pai, left, top, width, height) {
    let updateInfo = {
        left: left,
        top: top,
        width: width,
        height: height
    }
    browser.windows.update(id, updateInfo)
}

function criarJanela(url, posx, posy, largura, altura) {
	browser.windows.create({
		url: url,
		type: "panel",
		left: posx,
		top: posy,
		width: largura,
		height: altura		
	});
}

function Alerta(mensagem, imagem, id='maisPjeNotificacao', tempo=5000) {
	// 1: indiferente
	// 2: alerta
	// 3: piscando
	// 4: assustado
	// 5: feliz
	// 6: normal
	browser.notifications.clear('maisPjeNotificacao');
	
	if (imagem === undefined) {
		let sorteio = getRandomIntInclusive(1,6);
		imagem = sorteio;
	}
		
	let icone = 'icons/gigs-plugin_' + imagem + '.png'
	chrome.notifications.create(id, {
		type: 'basic',
		iconUrl: icone,
		title: 'maisPJe',
		message: mensagem.trim()
	},function() {
		if (mensagem.includes("Aviso Legal.")) {
			if (chrome.browserAction.onClicked.hasListener(listener)) {
				chrome.notifications.onClicked.removeListener(listener);
			} else {
				chrome.notifications.onClicked.addListener(listener);
			}
		} else {
			setTimeout(function() {
				browser.notifications.clear('maisPjeNotificacao');
			},tempo);			
		}
	});
	
	function getRandomIntInclusive(min, max) {
		min = Math.ceil(min);
		max = Math.floor(max);
		return Math.floor(Math.random() * (max - min + 1)) + min;
	}	
}

async function montarMenu(processo_memoria) {
	browser.menus.removeAll();
	
	//MONTAGEM DO CRIAR PAINEL COPIA E COLA
	browser.menus.create({id: "Painel Copia e Cola", title: "Painel Copia e Cola", contexts: ["all"], icons: {"16" : "icons/memoria_16.png", "32" : "icons/memoria_32.png"}});
	
	//MONTAGEM DO NÚMERO DO PROCESSO
	browser.menus.create({id: "numeroProcesso", title: processo_memoria.numero[0], contexts: ["all"], icons: {"16" : "icons/processo_16.png", "32" : "icons/processo_16.png"}});
	let numeroDoprocessoSoNumeros = processo_memoria.numero[0].replace(/\D/g,"");
	browser.menus.create({id: processo_memoria.numero[0], title: processo_memoria.numero[0], parentId: "numeroProcesso", contexts: ["all"]});
	browser.menus.create({id: numeroDoprocessoSoNumeros, title: numeroDoprocessoSoNumeros, parentId: "numeroProcesso", contexts: ["all"]});
	
	//MONTAGEM DO VALOR DA DÍVIDA
	let valor_formatado_para_uso = Intl.NumberFormat('pt-br', {style: 'decimal', currency: 'BRL'}).format(processo_memoria.divida.valor);
	let valor_formatado_para_exibir_sem_data = Intl.NumberFormat('pt-br', {style: 'currency', currency: 'BRL'}).format(processo_memoria.divida.valor);
	let valor_formatado_para_exibir_com_data = valor_formatado_para_exibir_sem_data + " em " + processo_memoria.divida.data;
	browser.menus.create({id: "Valor da Divida", title: valor_formatado_para_exibir_com_data + " " + processo_memoria.divida.id, contexts: ["all"], icons: {"16" : "icons/seta_16.png", "32" : "icons/seta_32.png"}});
	browser.menus.create({id: valor_formatado_para_exibir_com_data, title: valor_formatado_para_exibir_com_data, parentId: "Valor da Divida", contexts: ["all"]});
	browser.menus.create({id: valor_formatado_para_exibir_sem_data, title: valor_formatado_para_exibir_sem_data, parentId: "Valor da Divida", contexts: ["all"]});
	browser.menus.create({id: valor_formatado_para_uso, title: valor_formatado_para_uso, parentId: "Valor da Divida", contexts: ["all"]});
	browser.menus.create({id: valor_formatado_para_exibir_sem_data + '@extenso', title: valor_formatado_para_exibir_sem_data + ' (valor por extenso)', parentId: "Valor da Divida", contexts: ["all"]});
	browser.menus.create({id: 'somente@extenso'+valor_formatado_para_uso, title: '(somente extenso)', parentId: "Valor da Divida", contexts: ["all"]});
	
	//MONTAGEM DA JUSTIÇA GRATUITA
	// console.log(processo_memoria.justicaGratuita[0]);
	let jg = "Justi\u00e7a gratuita: " + processo_memoria.justicaGratuita[0];
	browser.menus.create({id: jg, title: jg, contexts: ["all"], icons: {"16" : "icons/seta_16.png", "32" : "icons/seta_32.png"}});
	if (processo_memoria.justicaGratuita[1] != '---') {
		browser.menus.create({id: processo_memoria.justicaGratuita[0] + ', decidido em: ' + processo_memoria.justicaGratuita[1], title: processo_memoria.justicaGratuita[0] + ', decidido em: ' + processo_memoria.justicaGratuita[1], parentId: jg, contexts: ["all"]});
	}
	
	
	//MONTAGEM DO TRANSITO
	browser.menus.create({id: "Transito em Julgado: " + processo_memoria.transito, title: "Tr\u00e2nsito em Julgado: " + processo_memoria.transito, contexts: ["all"], icons: {"16" : "icons/seta_16.png", "32" : "icons/seta_32.png"}});
	
	//MONTAGEM DAS CUSTAS	
	browser.menus.create({id: "Custas arbitradas: " + processo_memoria.custas, title: "Custas arbitradas: " + processo_memoria.custas, contexts: ["all"], icons: {"16" : "icons/seta_16.png", "32" : "icons/seta_32.png"}});
	
	browser.menus.create({id: "separador1", type: "separator", contexts: ["all"]});
	
	let i = 0;
	//MONTAGEM DO POLO ATIVO
	let map1 = [].map.call(
		processo_memoria.autor, 
		function(parte) {
			//cria menu PRINCIPAL com o nome + cpf da parte
			let menuidAutor = parte.nome + " (CPF/CNPJ " + (parte.cpfcnpj == "" ? "desconhecido" : parte.cpfcnpj) + ")";
			browser.menus.create({id: menuidAutor, title: parte.nome, contexts: ["all"], icons: {"16" : "icons/user_a_16.png", "32" : "icons/user_a_32.png"}});
			//cria o submenu com o nome + cpf da parte
			browser.menus.create({id: i + "#" + menuidAutor, title: menuidAutor, parentId: menuidAutor, contexts: ["all"]});
			//cria o submenu com o cpf da parte
			if (parte.cpfcnpj != "") {browser.menus.create({id:  i + "#" + parte.cpfcnpj, title: parte.cpfcnpj, parentId: menuidAutor, contexts: ["all"]});}
			//cria o submenu com o cpf da parte só com números
			if (parte.cpfcnpj != "") {
				let cpfCnpjSoNumeros = parte.cpfcnpj.replace(/\D/g,"");
				browser.menus.create({id:  i + "#" + cpfCnpjSoNumeros, title: cpfCnpjSoNumeros, parentId: menuidAutor, contexts: ["all"]});
			}
			//cria o submenu com o nome da parte
			browser.menus.create({id:  i + "#" + parte.nome, title: parte.nome, parentId: menuidAutor, contexts: ["all"]});
			//cria o submenu com a data de nascimento da parte
			if (parte.dataNascimento != "") {
				// browser.menus.create({id:  i + "#" + parte.dataNascimento, title: parte.dataNascimento, parentId: menuidAutor, contexts: ["all"]});
				let dtNasc = parte.dataNascimento.replace( /\-/g,'/');
				let dt = new Date(dtNasc).toLocaleDateString();
				
				let menuidDataNacimento = i + "##" + parte.nome + "_DataNascimento)";
				//cria o menu Data de nascimento
				browser.menus.create({id: menuidDataNacimento, title: 'Data de Nascimento', parentId: menuidAutor, contexts: ["all"], icons: {"16" : "icons/seta_16.png", "32" : "icons/seta_32.png"}});
				//cria o submenu com a data de nascimento da parte
				browser.menus.create({id:  i + "#" + dt, title: dt, parentId: menuidDataNacimento, contexts: ["all"]});
			}
			//cria o submenu com o nome da mãe da parte
			if (parte.nomeGenitora != "") {
				// browser.menus.create({id:  i + "#" + parte.nomeGenitora, title: parte.nomeGenitora, parentId: menuidAutor, contexts: ["all"]});
				
				let menuidNomeGenitora = i + "##" + parte.nome + "_nomeGenitora)";
				//cria o menu Data de nascimento
				browser.menus.create({id: menuidNomeGenitora, title: 'Nome da Genitora', parentId: menuidAutor, contexts: ["all"], icons: {"16" : "icons/seta_16.png", "32" : "icons/seta_32.png"}});
				//cria o submenu com a data de nascimento da parte
				browser.menus.create({id:  i + "#" + parte.nomeGenitora, title: parte.nomeGenitora, parentId: menuidNomeGenitora, contexts: ["all"]});
			}
			//cria o submenu com os advogados do autor
			if (!parte.representantes) { return }
			let map1a = [].map.call(
				parte.representantes, 
				function(representante) {
					//cria submenu PRINCIPAL com o nome + cpf da representante
					let menuidRepresentante = i + "##R#" + representante.nome + " (CPF/CNPJ " + (representante.cpfcnpj == "" ? "desconhecido" : representante.cpfcnpj) + ")";
					browser.menus.create({id: menuidRepresentante, title: representante.nome, parentId: menuidAutor, contexts: ["all"], icons: {"16" : "icons/user_adv_16.png", "32" : "icons/user_adv_32.png"}});
					//cria o submenu com o nome + cpf da representante
					browser.menus.create({id:  i + "#R#" + representante.nome + " (CPF/CNPJ " + (representante.cpfcnpj == "" ? "desconhecido" : representante.cpfcnpj) + ")", title: representante.nome + " (CPF/CNPJ " + (representante.cpfcnpj == "" ? "desconhecido" : representante.cpfcnpj) + ")", parentId: menuidRepresentante, contexts: ["all"]});
					//cria o submenu com o cpf da representante
					if (representante.cpfcnpj != "") {browser.menus.create({id:  i + "#" + representante.cpfcnpj, title: representante.cpfcnpj, parentId: menuidRepresentante, contexts: ["all"]});}
					//cria o submenu com o nome da representante
					browser.menus.create({id:  i + "#R#" + representante.nome, title: representante.nome, parentId: menuidRepresentante, contexts: ["all"]});
					//cria o submenu com o número da OAB da representante
					if (representante.oab != "") {browser.menus.create({id:  i + "#" + representante.oab, title: representante.oab, parentId: menuidRepresentante, contexts: ["all"]});}
					//cria o submenu com o nome + OAB da representante
					browser.menus.create({id:  i + "#R#" + representante.nome + " (OAB/" + (representante.oab == "" ? "desconhecido" : representante.oab) + ")", title: representante.nome + " (OAB/" + (representante.oab == "" ? "desconhecido" : representante.oab) + ")", parentId: menuidRepresentante, contexts: ["all"]});
				}
			);
			i++;
		}
	);
	
	browser.menus.create({id: "separador2", type: "separator", contexts: ["all"]});
	
	i = 0;
	//MONTAGEM DO POLO PASSIVO
	let map2 = [].map.call(
		processo_memoria.reu, 
		function(parte) {
			//cria menu PRINCIPAL com o nome + cpf da parte
			let menuidReu = parte.nome + " (CPF/CNPJ " + (parte.cpfcnpj == "" ? "desconhecido" : parte.cpfcnpj) + ")";
			// console.log(menuidReu)
			browser.menus.create({id: menuidReu, title: parte.nome, contexts: ["all"], icons: {"16" : "icons/user_r_16.png", "32" : "icons/user_r_32.png"}});
			//cria o submenu com o nome + cpf da parte
			browser.menus.create({id: i + "#" + menuidReu, title: menuidReu, parentId: menuidReu, contexts: ["all"]});
			//cria o submenu com o cpf da parte
			if (parte.cpfcnpj != "") {browser.menus.create({id:  i + "#" + parte.cpfcnpj, title: parte.cpfcnpj, parentId: menuidReu, contexts: ["all"]});}
			//cria o submenu com o cpf da parte só com números
			if (parte.cpfcnpj != "") {
				let cpfCnpjSoNumeros = parte.cpfcnpj.replace(/\D/g,"");
				browser.menus.create({id:  i + "#" + cpfCnpjSoNumeros, title: cpfCnpjSoNumeros, parentId: menuidReu, contexts: ["all"]});
			}			
			//cria o submenu com o nome da parte
			browser.menus.create({id:  i + "#" + parte.nome, title: parte.nome, parentId: menuidReu, contexts: ["all"]});
			//cria o submenu com os advogados do reu
			if (!parte.representantes) { return }
			let map2a = [].map.call(
				parte.representantes, 
				function(representante) {
					//cria submenu PRINCIPAL com o nome + cpf da representante
					let menuidRepresentante = i + "##R#" + representante.nome + " (CPF/CNPJ " + (representante.cpfcnpj == "" ? "desconhecido" : representante.cpfcnpj) + ")";
					browser.menus.create({id: menuidRepresentante, title: representante.nome, parentId: menuidReu, contexts: ["all"], icons: {"16" : "icons/user_adv_16.png", "32" : "icons/user_adv_32.png"}});
					//cria o submenu com o nome + cpf da representante
					browser.menus.create({id:  i + "#R#" + representante.nome + " (CPF/CNPJ " + (representante.cpfcnpj == "" ? "desconhecido" : representante.cpfcnpj) + ")", title: representante.nome + " (CPF/CNPJ " + (representante.cpfcnpj == "" ? "desconhecido" : representante.cpfcnpj) + ")", parentId: menuidRepresentante, contexts: ["all"]});
					//cria o submenu com o cpf da representante
					if (representante.cpfcnpj != "") {browser.menus.create({id:  i + "#" + representante.cpfcnpj, title: representante.cpfcnpj, parentId: menuidRepresentante, contexts: ["all"]});}
					//cria o submenu com o nome da representante
					browser.menus.create({id:  i + "#R#" + representante.nome, title: representante.nome, parentId: menuidRepresentante, contexts: ["all"]});
					//cria o submenu com o número da OAB da representante
					if (representante.oab != "") {browser.menus.create({id:  i + "#" + representante.oab, title: representante.oab, parentId: menuidRepresentante, contexts: ["all"]});}
					//cria o submenu com o nome + OAB da representante
					browser.menus.create({id:  i + "#R#" + representante.nome + " (OAB/" + (representante.oab == "" ? "desconhecido" : representante.oab) + ")", title: representante.nome + " (OAB/" + (representante.oab == "" ? "desconhecido" : representante.oab) + ")", parentId: menuidRepresentante, contexts: ["all"]});
				}
			);
			i++;
		}
	);
	
	browser.menus.create({id: "separador3", type: "separator", contexts: ["all"]});
	
	//MONTAGEM DO POLO TERCEIROS
	let map3 = [].map.call(
		processo_memoria.terceiro, 
		function(parte) {
			//cria menu PRINCIPAL com o nome + cpf da parte
			let menuidTerceiro = parte.nome + " (CPF/CNPJ " + (parte.cpfcnpj == "" ? "desconhecido" : parte.cpfcnpj) + ")";
			browser.menus.create({id: "#" + menuidTerceiro, title: parte.nome, contexts: ["all"], icons: {"16" : "icons/user_t_16.png", "32" : "icons/user_t_32.png"}});
			//cria o submenu com o nome + cpf da parte
			browser.menus.create({id: menuidTerceiro, title: menuidTerceiro, parentId: "#" + menuidTerceiro, contexts: ["all"]});
			//cria o submenu com o cpf da parte
			if (parte.cpfcnpj != "") {browser.menus.create({id: parte.cpfcnpj, title: parte.cpfcnpj, parentId: "#" + menuidTerceiro, contexts: ["all"]});}
			//cria o submenu com o nome da parte
			browser.menus.create({id: parte.nome, title: parte.nome, parentId: "#" + menuidTerceiro, contexts: ["all"]});
			//cria o submenu com a expressão "Terceiro Interessado: " + nome da parte
			browser.menus.create({id: "TERCEIRO INTERESSADO: " + parte.nome, title: "TERCEIRO INTERESSADO: " + parte.nome, parentId: "#" + menuidTerceiro, contexts: ["all"]});
			//cria o submenu com os advogados do terceiro
			if (!parte.representantes) { return }
			let map3a = [].map.call(
				parte.representantes, 
				function(representante) {
					//cria submenu PRINCIPAL com o nome + cpf da representante
					let menuidRepresentante = i + "##R#" + representante.nome + " (CPF/CNPJ " + (representante.cpfcnpj == "" ? "desconhecido" : representante.cpfcnpj) + ")";
					browser.menus.create({id: menuidRepresentante, title: representante.nome, parentId: menuidReu, contexts: ["all"], icons: {"16" : "icons/user_adv_16.png", "32" : "icons/user_adv_32.png"}});
					//cria o submenu com o nome + cpf da representante
					browser.menus.create({id:  i + "#R#" + representante.nome + " (CPF/CNPJ " + (representante.cpfcnpj == "" ? "desconhecido" : representante.cpfcnpj) + ")", title: representante.nome + " (CPF/CNPJ " + (representante.cpfcnpj == "" ? "desconhecido" : representante.cpfcnpj) + ")", parentId: menuidRepresentante, contexts: ["all"]});
					//cria o submenu com o cpf da representante
					if (representante.cpfcnpj != "") {browser.menus.create({id:  i + "#" + representante.cpfcnpj, title: representante.cpfcnpj, parentId: menuidRepresentante, contexts: ["all"]});}
					//cria o submenu com o nome da representante
					browser.menus.create({id:  i + "#R#" + representante.nome, title: representante.nome, parentId: menuidRepresentante, contexts: ["all"]});
					//cria o submenu com o número da OAB da representante
					if (representante.oab != "") {browser.menus.create({id:  i + "#" + representante.oab, title: representante.oab, parentId: menuidRepresentante, contexts: ["all"]});}
					//cria o submenu com o nome + OAB da representante
					browser.menus.create({id:  i + "#R#" + representante.nome + " (OAB/" + (representante.oab == "" ? "desconhecido" : representante.oab) + ")", title: representante.nome + " (OAB/" + (representante.oab == "" ? "desconhecido" : representante.oab) + ")", parentId: menuidRepresentante, contexts: ["all"]});
				}
			);
		}
	);

	//MONTAGEM DO LIMPAR MEMORIA
	browser.menus.create({id: "Limpar Memoria", title: "Limpar Mem\u00f3ria", contexts: ["all"], icons: {"16" : "icons/lixeira_16.png", "32" : "icons/lixeira_32.png"}});
	
	let permitirCtrlC = await getLocalStorage('gigsCriarMenuGuardarNumeroProcesso');
	if (permitirCtrlC) { navigator.clipboard.writeText(processo_memoria.numero[0]) } //guarda o processo no ctrl + C 
}

function mudarIcone(msg, ico) {
	browser.browserAction.setIcon({path:'../icons/' + ico});
	browser.browserAction.setTitle({title: msg});
}

function executarScript(arquivo) {
	browser.tabs.executeScript({file: arquivo});
}

async function devolverMensagem(mensagem) {
	let tabArray = await browser.tabs.query({currentWindow: true, active: true});
	let tabId = tabArray[0].id;
	browser.tabs.sendMessage(tabId,{greeting: mensagem});
}

async function insertCSS(arquivo) {
	let tabArray = await browser.tabs.query({currentWindow: true, active: true});
	let tabId = tabArray[0].id;
	await browser.tabs.insertCSS(tabId, {file: arquivo});
}

var listener = function() {
	requestTermoDeUso();
}

browser.menus.onClicked.addListener((info, tab) => {
	console.log(info.menuItemId)
	if (info.menuItemId == 'Limpar Memoria') {
		let var1 = browser.storage.local.set({'AALote': ''});
		let var2 = browser.storage.local.set({'processo_memoria': ''});
		let var3 = browser.storage.local.set({'temp_expediente_especial': ''});
		let var4 = browser.storage.local.set({'tempAR': ''});
		let var5 = browser.storage.local.set({'tempBt': ''});
		Promise.all([var1,var2,var3,var4,var5]).then(values => {
			Alerta('Limpar mem\u00f3ria...  conclu\u00eddo!!', 2)
			browser.menus.removeAll();
		});		
	} else {
		browser.tabs.sendMessage(tab.id,{greeting: info.menuItemId});
	}	
});

browser.runtime.onMessage.addListener(notify);

// browser.tabs.onCreated.addListener(IdentificadorDeJanelaOuAba);

// browser.tabs.onActivated.addListener(IdentificadorDeJanelaOuAba);

// async function IdentificadorDeJanelaOuAba(tab) {
// 	await sleep(2000); //espera carregar alguns dados da janela para obter a url senão ela vem vazia
// 	console.info('JANELA ATIVA: ' + janelatAtiva?.url);
// 	let urlInfo = await browser.tabs.get(tab.id);
// 	console.info('           |____tabid: ' + tab.id);
// 	console.info('           |____windowid: ' + tab.windowId);
// 	console.info('           |____url2: ' + urlInfo.url);
	
// 	if (urlInfo.url.includes(".jus.br/pjekz/") && urlInfo.url.includes("/detalhe")) {
// 		janelatAtiva = {windowId: tab.windowId, id: tab.id, url: urlInfo.url}
// 	}	
// }


async function pjeApiObterPartesDoProcesso(trt, id, processo){
	console.log('trt: ' + trt + ' id: ' + id + ' processo: ' + processo)
	let url = 'https://' + trt + '/pje-comum-api/api/processos/id/' + id + '/partes';
	let resposta = await fetch(url);
	let dados = await resposta.json();
	
	let poloAtivo = [];
	let map1 = [].map.call(
		dados.ATIVO, 
		function(parte) {
			let listaAdvAutor = [];
			if (parte.representantes) {
				let map1a = [].map.call(
					parte.representantes, 
					function(representante) {
						listaAdvAutor.push(new Pessoa(representante.nome.trim(), representante.documento ? representante.documento : "", representante.numeroOab, 'ativo', []));
					}
				);
			}
			
			let dataNascimento = '';
			let nomeGenitora = '';
			if (parte.pessoaFisica) {
				dataNascimento = (!parte.pessoaFisica.dataNascimento) ? 'nao informado' : parte.pessoaFisica.dataNascimento.trim();
				nomeGenitora = (!parte.pessoaFisica.nomeGenitora) ? 'nao informado' : parte.pessoaFisica.nomeGenitora.trim();
			}
			poloAtivo.push(new Pessoa(parte.nome.trim(), parte.documento ? parte.documento : "", "", 'ativo', listaAdvAutor, dataNascimento, nomeGenitora));
		}
	);
	
	let poloPassivo = [];
	let map2 = [].map.call(
		dados.PASSIVO, 
		function(parte) {
			let listaAdvReu = [];
			if (parte.representantes) {
				let map2a = [].map.call(
					parte.representantes, 
					function(representante) {
						listaAdvReu.push(new Pessoa(representante.nome.trim(), representante.documento ? representante.documento : "", representante.numeroOab, 'passivo', []));
					}
				);
			}
			poloPassivo.push(new Pessoa(parte.nome.trim(), parte.documento ? parte.documento : "", "", 'passivo', listaAdvReu));
		}
	);
	
	let poloTerceiro = [];
	if (dados.TERCEIROS) {
		let map3 = [].map.call(
			dados.TERCEIROS, 
			function(parte) {
				poloTerceiro.push(new Pessoa(parte.nome.trim(), parte.documento ? parte.documento : "", "", 'terceiro'));
			}
		);
	}
	const tempoParaCadaApi = await getVelocidadeInteracao() * 1000 + 1000;
	// console.info('tempoParaCadaApi', tempoParaCadaApi)
	// const tempoParaCadaApi = 1000 + 1000;
	const processoApi = await obterProcessoViaApi(trt, id, tempoParaCadaApi);
	const dtAutuacao = await obterDtAutuacaoDoProcessoViaApi(processoApi);
	const divida = await pjeApiObterValorExecucao(trt, id, tempoParaCadaApi);
	// const movimentos = await pjeApiObterMovimentos(trt, id);
	const justicaGratuita = await obterJusticaGratuita(trt, id, processoApi);
	// console.info('justicaGratuita', justicaGratuita)
	const transitoEvalorCustas = await obterDataTransitoEmJulgadoDosMovimentos(trt, id);
	const transito = transitoEvalorCustas[0];
	// let valorCustas = (isNaN(parseFloat(transitoEvalorCustas[1]))) ? '---' : parseFloat(transitoEvalorCustas[1]);
	const valorCustas = 'R$ ' + transitoEvalorCustas[1];
	const processoMemoria = new Processo(processo, id, poloAtivo, poloPassivo, poloTerceiro, divida, justicaGratuita, transito, valorCustas, dtAutuacao);
	const var1 = browser.storage.local.set({'processo_memoria': processoMemoria});
	Promise.all([var1]).then(values => { montarMenu(processoMemoria) });
}

async function pjeApiObterValorExecucao(trt, id, timeout){
	return new Promise(async resolve => {
		let valorExecucaoGigs = await pjeApiObterValorExecucaoGigs(trt, id, timeout);
		// console.log(valorExecucaoGigs.valor + " : " + valorExecucaoGigs.data)
		
		if (isNaN(valorExecucaoGigs.valor) || valorExecucaoGigs.valor < 1) {
			const valorExecucaoPjeCalc = await pjeApiObterValorExecucaoPJeCalc(trt, id, timeout);
			// console.log(valorExecucaoPjeCalc.valor + " : " + valorExecucaoPjeCalc.data)
			resolve(valorExecucaoPjeCalc);
		} else {
			resolve(valorExecucaoGigs);
		}		
	});
}

async function pjeApiObterValorExecucaoPJeCalc(trt, id, timeout){
	return new Promise(async resolve => {
		const semValor = { id: '(PJeCalc)', valor: 0, data: '--/--/----' };

		const timeoutId = criarTimeoutParaApi(resolve, timeout, semValor, 'PJe Calc - dívida');
	  try {
		const url = 'https://' + trt + '/pje-comum-api/api/calculos/processo?pagina=1&tamanhoPagina=10&ordenacaoCrescente=true&idProcesso=' + id + '&mostrarCalculosHomologados=true&incluirCalculosHomologados=true';
		// console.log(url);
		const dados = await fetch(url).then((resposta) => resposta.json());
		clearTimeout(timeoutId);
		if (!dados  || !dados.resultado || !dados.resultado[0]) {return resolve(semValor);}
		
		let ultimoCalculo;
		let dataUltimoCalculo = new Date(1900, 1, 1);
		for (const [pos, calculo] of dados.resultado.entries()) {
			if (pos == 0) { ultimoCalculo = calculo; }
			let dt = new Date(calculo.dataLiquidacao);
			if (dt > dataUltimoCalculo) {
				dataUltimoCalculo = dt;
				ultimoCalculo = calculo;
			}
		}		
		let dia  =  (dataUltimoCalculo.getDate() + '').padStart(2,'0') + '/';
		let mes = ((dataUltimoCalculo.getMonth()+1) + '').padStart(2,'0');
		let ano = '/' + dataUltimoCalculo.getFullYear();
		resolve({id: '(PJeCalc)',valor: ultimoCalculo.total, data: (dia + mes + ano)});
	  } catch (err) {
		alert("maisPje: Algo deu errado ao recuperar o valor da dívida no PJeCalc.");
		console.error(err);
		resolve(semValor);
	  }
	});
}

async function pjeApiObterValorExecucaoGigs(trt, id, timeout){
	return new Promise(async resolve => {
		const semValor = {id: '(GIGS)',valor: 0, data: '--/--/----'};
		const timeoutId = criarTimeoutParaApi(resolve, timeout, semValor, 'GIGS - dívida');

	  try {
		let url = 'https://' + trt + '/pje-gigs-api/api/execucao/processo/' + id;
		const dados = await fetch(url).then((resposta) => resposta.json());
		clearTimeout(timeoutId);
		if (!dados) {return resolve(semValor);}
		
		let ultimoCalculo = dados.valor;
		let dataUltimoCalculo = new Date(dados.data);		
		let dia  =  (dataUltimoCalculo.getDate() + '').padStart(2,'0') + '/';
		let mes = ((dataUltimoCalculo.getMonth()+1) + '').padStart(2,'0');
		let ano = '/' + dataUltimoCalculo.getFullYear()
		
		
		resolve({id: '(GIGS)',valor: ultimoCalculo, data: (dia + mes + ano)});
	  } catch (err) {
		alert("maisPje: Algo deu errado ao recuperar o valor da dívida no GIGS.");
		console.error(err);
		resolve(semValor);
	  }	
	});
}

async function getVelocidadeInteracao() {
	const velocidadeInteracao = await getLocalStorage('maisPje_velocidade_interacao');
	// console.info('velocidadeInteracao', velocidadeInteracao);
	return velocidadeInteracao || 0.5 // padrao
}

async function obterJusticaGratuita(trt, id, processo) {
	const sanearAJG = await getLocalStorage('sanearAJG');
	// alert(sanearAJG)

	if (!sanearAJG) {
		return new Promise(async resolve => resolve(['Sanear AJG DESATIVADA', '---']));
	}

	const movimentos = await pjeApiObterMovimentosAJG(trt, id);

	let justicaGratuita = await pjeApiObterJusticaGratuita(processo);

	//agora varre os movimentos para verificar se bate com o dado estruturado.
	for (const [pos, movimento] of movimentos.entries()) {
		//a função de remover acento não funcionou.. então tive que fazer assim
		// ###### Unicode character table ######

		// #	let	tipo 	minus	maius
		// #	a 	crase 	\u00E0 	\u00C0
		// #	a 	agudo 	\u00E1 	\u00C1
		// #	a 	chapeu 	\u00E2 	\u00C2
		// #	a 	ttil 	\u00E3 	\u00C3
		// #	c 	cedilha 	\u00E7 	\u00C7
		// #	e 	agudo 	\u00E9 	\u00C9
		// #	e 	chapeu 	\u00EA 	\u00CA
		// #	i 	agudo 	\u00ED 	\u00CD
		// #	o 	agudo 	\u00F3 	\u00D3
		// #	o 	chapeu 	\u00F4 	\u00D4
		// #	o 	ttil 	\u00F5 	\u00D5
		// #	u 	agudo 	\u00FA 	\u00DA

		let g = true;
		const titulo = movimento.titulo ?? movimento.textoFinalExterno;
		// console.error('titulo', titulo)
		if (sanearAJG && g && titulo.includes('oncedida a assist\u00EAncia judici\u00E1ria gratuita')) {

			let dataDeferimento = new Date(movimento.data ?? movimento.atualizadoEm);
			let dia  =  (dataDeferimento.getDate() + '').padStart(2,'0') + '/';
			let mes = ((dataDeferimento.getMonth()+1) + '').padStart(2,'0');
			let ano = '/' + dataDeferimento.getFullYear()
			justicaGratuita[1] = dia + mes + ano;


			if (titulo.includes('Exclu\u00EDdo de ')) { //excluído o movimento significa que houve uma retificação no movimento de justiça gratuita

				if (titulo.includes('N\u00E3o')) { //excluído o movimento de não-concessão
					console.log('excluído mov não-concessão')
					justicaGratuita[0] = 'Sim';
					justicaGratuita[1] += " (corrigido)";
				} else { //excluído o movimento de concessão
					console.log('excluído mov concessão')
					justicaGratuita[0] = 'Não';
					justicaGratuita[1] += " (corrigido)";
				}

			} else if (titulo.includes('Não')) {

				if (justicaGratuita[0] == 'Sim') {
					let alerta = '\nEncontrei uma inconsistência no lançamento da Justiça Gratuita.\n\n Na timeline do processo, no dia ' + justicaGratuita[1] + ', existe um movimento de não concessão da justiça gratuita enquanto que nos assentamentos est\u00E1 registrado "Processo com justiça gratuita deferida".\n\nSUGEST\u00C3O: confirme na decisão se o registro est\u00E1 correto e retifique a autuação do processo, indo na guia [Caracter\u00EDsticas], e desmarque a opção Justiça Gratuita, se for o caso. (cd-mnjg)\n\n Ou, para registrar a concessão da justiça gratuita, elabore um despacho simples e, na guia movimentos, assinale o movimento de concessão.(cd-mnjg)\n\n'; //(cd-mnjg): código montar menu justiça gratuita
					devolverMensagem(alerta);
					justicaGratuita[0] = '???';
				}

			} else {
				justicaGratuita[0] = 'Sim';
			}

			g = false;

		}

		if (!g) { break } //achou AJG sai do loop
	}

	async function pjeApiObterJusticaGratuita(processo){
		// console.info('sanearAJG', sanearAJG)
		if (sanearAJG) {
			return new Promise(async resolve => {
				if (!processo) {
					return resolve('erro')
				}
				if (processo.justicaGratuita) {
					return resolve(['Sim', '---']);
				} else {
					return resolve(['Não', '---']);
				}
			});
		} else {
			return new Promise(async resolve => resolve(['Sanear AJG DESATIVADA', '---']));
		}
	}
	return justicaGratuita;
}

async function pjeApiObterMovimentosAJG(trt, id) {
    const NAO_CONCEDIDA_A_ASSISTENCIA_JUDICIARIA_GRATUITA = 334;
    const CONCEDIDA_A_GRATUIDADE_DA_JUSTICA_A_NOME_DA_PARTE = 787;
    const CONCEDIDA_A_ASSISTENCIA_JUDICIARIA_GRATUITA = 11024;
	const EXCLUIDO = 50033;

	const codigosMovimentos = [NAO_CONCEDIDA_A_ASSISTENCIA_JUDICIARIA_GRATUITA, 
		CONCEDIDA_A_ASSISTENCIA_JUDICIARIA_GRATUITA, 
		CONCEDIDA_A_GRATUIDADE_DA_JUSTICA_A_NOME_DA_PARTE, EXCLUIDO];
	return pjeApiObterMovimentosPelosCodigos(trt, id, codigosMovimentos);
}

async function pjeApiObterMovimentosPelosCodigos(trt, id, codigosMovimentos) {
	const semValor = 'erro';
	
	// const timeoutId = criarTimeoutParaApi(resolve, timeout, semValor, 'movimentos');
	try {
		let parametrosApi = '';
		for (const codigo of codigosMovimentos) {
			 parametrosApi += `&codEventos=${codigo}`;
		}
		// console.error(parametrosApi);
		const url = `https://${trt}/pje-comum-api/api/processos/id/${id}/movimentos/?ordemAscendente=false` + parametrosApi;
		const resposta = await fetch(url);
		// clearTimeout(timeoutId);
		// console.info(resposta)
		if (!resposta.ok) {
			alert("maisPje: Algo deu errado ao recuperar os movimentos.");
			return semValor;
		}
		const movimentos = await resposta.json();
		// console.info(movimentos)
		return movimentos;
	} catch (err) {
		alert("maisPje: Algo deu errado ao recuperar os movimentos.");
		return semValor;
	}
}

async function pjeApiObterMovimentos(trt, id, timeout) {
	const url = `https://${trt}/pje-comum-api/api/processos/id/${id}/timeline?somenteDocumentosAssinados=false&buscarMovimentos=true&buscarDocumentos=false`;
	const semValor = 'erro';
	// const timeoutId = criarTimeoutParaApi(resolve, timeout, semValor, 'movimentos');
	try {
		const resposta = await fetch(url);
		// clearTimeout(timeoutId);
		if (!resposta.ok) {
			alert("maisPje: Algo deu errado ao recuperar os movimentos.");
			return semValor;
		}
		const movimentos = await resposta.json();
		return movimentos;
	} catch (err) {
		alert("maisPje: Algo deu errado ao recuperar os movimentos.");
		return semValor;
	}
}

function criarTimeoutParaApi(resolve, timeout, semValor, api = '') {
	return setTimeout(() => {
		alert("maisPje: a API " + api + " demorou demais.");
		resolve(semValor);
	}, timeout);
}

async function obterProcessoViaApi(trt, idProcesso, timeout) {
	return new Promise(async resolve => {
		const semValor = undefined;
		const timeoutId = criarTimeoutParaApi(resolve, timeout, semValor, 'processo');
		try {
			const url = 'https://' + trt + '/pje-comum-api/api/processos/id/' + idProcesso;
			const resposta = await fetch(url);		
			clearTimeout(timeoutId);
			const processo = await resposta.json();
			return resolve(processo);
		} catch (err) {
			alert("maisPje: Algo deu errado ao recuperar os dados do processo.");
			// console.error(err);
			resolve(semValor);
		}	
	});
}

async function obterDtAutuacaoDoProcessoViaApi(processo) {
	return new Promise(async resolve => {
		if (!processo?.autuadoEm) {return resolve('--/--/----')}
		let dtAutuacao = new Date(processo.autuadoEm);
		let dia  =  (dtAutuacao.getDate() + '').padStart(2,'0') + '/';
		let mes = ((dtAutuacao.getMonth()+1) + '').padStart(2,'0');
		let ano = '/' + dtAutuacao.getFullYear()
		return resolve(dia + mes + ano);
	});
}

function sleep(ms) {
	return new Promise(resolve => setTimeout(resolve, ms));
}

//FUNÇÃO QUE RETORNA O TRANSITO EM JULGADO DE UM PROCESSO
async function obterDataTransitoEmJulgadoDosMovimentos(trt, id) {
	return new Promise(async resolve => {
		let dataTransito = '---';
		let custasProcessuais = '---';
		let achouDataTransitoJulgado = false; //pegar sempre a primeira aparição
		let achouCustasProcessuais = false; //pegar sempre a primeira aparição

		const TRANSITADO_EM_JULGADO = 848;
		ARBITRADAS_AS_CUSTAS_PROCESSUAIS_NO_VALOR = 50073;
		const movimentos = await pjeApiObterMovimentosPelosCodigos(trt, id, [TRANSITADO_EM_JULGADO, ARBITRADAS_AS_CUSTAS_PROCESSUAIS_NO_VALOR]);

		for (const [pos, movimento] of movimentos.entries()) {
			const titulo = movimento.titulo ?? movimento.textoFinalExterno;
			// console.error('titulo', titulo)
			if (!achouDataTransitoJulgado && titulo.includes('Transitado em julgado em')) {
				if (new RegExp('\\d{2}\\/\\d{2}\\/\\d{4}').test(titulo)) {
					dataTransito = titulo.match(new RegExp('\\d{2}\\/\\d{2}\\/\\d{4}')).join();
					achouDataTransitoJulgado = true;
				}
			}
			
			if (!achouCustasProcessuais && titulo.toLowerCase().includes('arbitradas') && titulo.toLowerCase().includes('custas processuais')) {
				custasProcessuais = titulo.replace(new RegExp('[^0-9\,]', 'g'), ""); //tira o R$ e o resto, deixando apenas o valor
				achouCustasProcessuais = true;
			}

			if (achouDataTransitoJulgado && achouCustasProcessuais) { break } //achou os dois sai do loop
		}
		// console.log('dataTransito : ' + dataTransito);
		// console.log('custasProcessuais : ' + custasProcessuais);
		return resolve([dataTransito,custasProcessuais])
	});
}

function Processo(numero, id, autor, reu, terceiro, divida, justicaGratuita, transito, custas, dtAutuacao) {
  this.numero = numero;
  this.id = id;
  this.autor = autor;
  this.reu = reu;
  this.terceiro = terceiro;
  this.divida = divida;
  this.justicaGratuita = justicaGratuita;
  this.transito = transito;
  this.custas = custas;
  this.dtAutuacao = dtAutuacao;
}

function Pessoa(nome, cpfcnpj, oab, polo, representantes, dataNascimento, nomeGenitora) {
  this.nome = nome;
  this.cpfcnpj = cpfcnpj;
  this.oab = oab;
  this.polo = polo;
  this.representantes = representantes;
  this.dataNascimento = dataNascimento;
  this.nomeGenitora = nomeGenitora;
}
