async function getLocalStorage(key) {
	return new Promise((resolve, reject) => {
		browser.storage.local.get([key]).then(function (result) {
			if (result[key] === undefined) {
				reject();
			} else {
				resolve(result[key]);
			}
		});
	});
}

function addPaginaFromStorage(pagina, container) {
	return new Promise(async resolver => {
		const documentoTratado = new DOMParser().parseFromString(pagina, 'text/html');
		for (const [pos, node] of Object.entries(documentoTratado.body.children)) {
			container.appendChild(node);
		}
		return resolver(true)
	});
}

/**
 * 	configuracoes que nao dependem de perfil
 * @param {Partial<Preferencias>} preferencias
 * @param {boolean} restaurar
 */
function preencherVariaveisComuns(preferencias, restaurar=false) {
	//configuracoes que nao dependem de perfil
	preferencias.modoLGPD = typeof(preferencias.modoLGPD) == "undefined" ? false : preferencias.modoLGPD;
	preferencias.modoNoite = typeof(preferencias.modoNoite) == "undefined" ? false : preferencias.modoNoite;

	//LGPD
	if (preferencias.modoLGPD) { ativarLGPD() }

	//Modo Noite
	ativarModoNoite(preferencias.modoNoite);

	preferencias.concordo = typeof(preferencias.concordo) == "undefined" ? false : preferencias.concordo;
	preferencias.extensaoAtiva = typeof(preferencias.extensaoAtiva) == "undefined" ? false : preferencias.extensaoAtiva;
	preferencias.desativarAjusteJanelas = typeof(preferencias.desativarAjusteJanelas) == "undefined" ? true : preferencias.desativarAjusteJanelas;
	preferencias.videoAtualizacao = typeof(preferencias.videoAtualizacao) == "undefined" ? true : preferencias.videoAtualizacao;
	preferencias.versao = typeof(preferencias.versao) == "undefined" ? "0" : preferencias.versao;
	preferencias.trt = typeof(preferencias.trt) == "undefined" ? "erro" : preferencias.trt;
	preferencias.num_trt = extrairTRT(preferencias.trt);
	preferencias.nm_usuario = typeof(preferencias.nm_usuario) == "undefined" ? "" : preferencias.nm_usuario;
	preferencias.oj_usuario = typeof(preferencias.oj_usuario) == "undefined" ? "" : preferencias.oj_usuario;
	preferencias.grau_usuario = typeof(preferencias.grau_usuario) == "undefined" ? "" : preferencias.grau_usuario;
	preferencias.tempAR = typeof(preferencias.tempAR) == "undefined" ? "" : preferencias.tempAR;
	preferencias.tempBt = typeof(preferencias.tempBt) == "undefined" ? [] : preferencias.tempBt;
	preferencias.tempAAEspecial = typeof(preferencias.tempAAEspecial) == "undefined" ? [] : preferencias.tempAAEspecial;
	preferencias.tempF2 = typeof(preferencias.tempF2) == "undefined" ? "" : preferencias.tempF2;
	preferencias.tempF3 = typeof(preferencias.tempF3) == "undefined" ? "" : preferencias.tempF3;
	preferencias.tempF4 = typeof(preferencias.tempF4) == "undefined" ? "" : preferencias.tempF4;
    preferencias.ctrlv = typeof(preferencias.ctrlv) == "undefined" ? "" : preferencias.ctrlv;

	preferencias.modulo4PaginaInicial = typeof(preferencias.modulo4PaginaInicial) == "undefined" ? 'nenhum' : preferencias.modulo4PaginaInicial;
	preferencias.atalhosPlugin = typeof(preferencias.atalhosPlugin) == "undefined" ? "SISBAJUD:https://sisbajud.cnj.pje.jus.br/|Caged:https://caged.maisemprego.mte.gov.br/caged|CCS:https://www3.bcb.gov.br/ccs/dologin|Celesc:http://consumidor.celesc.com.br:8895/index.php/acesso|Cnib:https://www.indisponibilidade.org.br/autenticacao/|Honor\u00e1rios:http://www2.trt12.jus.br/ajg/intranet/entrada.asp|Intranet:https://intranet.trt12.jus.br/|Renajud:https://renajud.denatran.serpro.gov.br/renajud/login.jsf|Serasajud:https://sitenet05cert.serasa.com.br/SerasaJudicial/default.aspx|Siel:https://apps.tre-sc.jus.br/siel/index.php" : preferencias.atalhosPlugin;

	//TODO: essas 3 linhas sao de algum modulo especifico?
	preferencias.timeline = typeof(preferencias.timeline) == "undefined" ? ['',[]] : preferencias.timeline;
	preferencias.atalho = typeof(preferencias.atalho) == "undefined" ? {'painelcopiaecola':''}: preferencias.atalho;
	preferencias.atalho.painelcopiaecola = typeof(preferencias.atalho.painelcopiaecola) == "undefined" ? '' : preferencias.atalho.painelcopiaecola;
}

/**
 * @param {Partial<Preferencias>} preferencias
 */
function preencherVariaveisMenuKaizen(preferencias) {
	/** @type {MenuPosition} */
	const kaizenPJe = { posx: '96%', posy: '92%' };
	/** @type {MenuPosition} */
	const posKaizenConvenio = { posx: '93%', posy: '80%' };

	preferencias.menu_kaizen = typeof (preferencias.menu_kaizen) == "undefined" ? { principal: kaizenPJe, detalhes: kaizenPJe, tarefas: kaizenPJe, sisbajud: posKaizenConvenio, serasajud: posKaizenConvenio, renajud: posKaizenConvenio, cnib: posKaizenConvenio, ccs: posKaizenConvenio, prevjud: posKaizenConvenio, protestojud: posKaizenConvenio, sniper: posKaizenConvenio, censec: posKaizenConvenio, celesc: posKaizenConvenio, casan: posKaizenConvenio, sigef: posKaizenConvenio, saj: posKaizenConvenio, infoseg: posKaizenConvenio, ajjt: posKaizenConvenio } : preferencias.menu_kaizen;
	preferencias.menu_kaizen.principal = typeof (preferencias.menu_kaizen.principal) == "undefined" ? kaizenPJe : preferencias.menu_kaizen.principal;
	preferencias.menu_kaizen.detalhes = typeof (preferencias.menu_kaizen.detalhes) == "undefined" ? kaizenPJe : preferencias.menu_kaizen.detalhes;
	preferencias.menu_kaizen.tarefas = typeof (preferencias.menu_kaizen.tarefas) == "undefined" ? kaizenPJe : preferencias.menu_kaizen.tarefas;
	preferencias.menu_kaizen.sisbajud = typeof (preferencias.menu_kaizen.sisbajud) == "undefined" ? posKaizenConvenio : preferencias.menu_kaizen.sisbajud;
	preferencias.menu_kaizen.serasajud = typeof (preferencias.menu_kaizen.serasajud) == "undefined" ? posKaizenConvenio : preferencias.menu_kaizen.serasajud;
	preferencias.menu_kaizen.renajud = typeof (preferencias.menu_kaizen.renajud) == "undefined" ? posKaizenConvenio : preferencias.menu_kaizen.renajud;
	preferencias.menu_kaizen.cnib = typeof (preferencias.menu_kaizen.cnib) == "undefined" ? posKaizenConvenio : preferencias.menu_kaizen.cnib;
	preferencias.menu_kaizen.ccs = typeof (preferencias.menu_kaizen.ccs) == "undefined" ? posKaizenConvenio : preferencias.menu_kaizen.ccs;
	preferencias.menu_kaizen.prevjud = typeof (preferencias.menu_kaizen.prevjud) == "undefined" ? posKaizenConvenio : preferencias.menu_kaizen.prevjud;
	preferencias.menu_kaizen.protestojud = typeof (preferencias.menu_kaizen.protestojud) == "undefined" ? posKaizenConvenio : preferencias.menu_kaizen.protestojud;
	preferencias.menu_kaizen.sniper = typeof (preferencias.menu_kaizen.sniper) == "undefined" ? posKaizenConvenio : preferencias.menu_kaizen.sniper;
	preferencias.menu_kaizen.censec = typeof (preferencias.menu_kaizen.censec) == "undefined" ? posKaizenConvenio : preferencias.menu_kaizen.censec;
	preferencias.menu_kaizen.celesc = typeof (preferencias.menu_kaizen.celesc) == "undefined" ? posKaizenConvenio : preferencias.menu_kaizen.celesc;
	preferencias.menu_kaizen.casan = typeof (preferencias.menu_kaizen.casan) == "undefined" ? posKaizenConvenio : preferencias.menu_kaizen.casan;
	preferencias.menu_kaizen.sigef = typeof (preferencias.menu_kaizen.sigef) == "undefined" ? posKaizenConvenio : preferencias.menu_kaizen.sigef;
	preferencias.menu_kaizen.infoseg = typeof (preferencias.menu_kaizen.infoseg) == "undefined" ? posKaizenConvenio : preferencias.menu_kaizen.infoseg;
	preferencias.menu_kaizen.ajjt = typeof (preferencias.menu_kaizen.ajjt) == "undefined" ? posKaizenConvenio : preferencias.menu_kaizen.ajjt;
	preferencias.menu_kaizen.saj = typeof (preferencias.menu_kaizen.saj) == "undefined" ? posKaizenConvenio : preferencias.menu_kaizen.saj;

	preferencias.acionarKaizenComClique = typeof(preferencias.acionarKaizenComClique) == "undefined" ? false : preferencias.acionarKaizenComClique;
	preferencias.kaizenNaHorizontal = typeof(preferencias.kaizenNaHorizontal) == "undefined" ? false : preferencias.kaizenNaHorizontal;
}

/**
 *
 * @param {Partial<Preferencias>} preferencias
 */
function preencherVariaveisModulo1(preferencias) {
	preferencias.gigsMonitorDetalhes = typeof(preferencias.gigsMonitorDetalhes) == "undefined" ? 0 : preferencias.gigsMonitorDetalhes;
	preferencias.gigsMonitorTarefas = typeof(preferencias.gigsMonitorTarefas) == "undefined" ? 0 : preferencias.gigsMonitorTarefas;
	preferencias.gigsMonitorGigs = typeof(preferencias.gigsMonitorGigs) == "undefined" ? 0 : preferencias.gigsMonitorGigs;
	preferencias.gigsAbrirGigs = typeof(preferencias.gigsAbrirGigs) == "undefined" ? 0 : preferencias.gigsAbrirGigs;
	preferencias.gigsAbrirDetalhes = typeof(preferencias.gigsAbrirDetalhes) == "undefined" ? 0 : preferencias.gigsAbrirDetalhes;
	preferencias.gigsAbrirTarefas = typeof(preferencias.gigsAbrirTarefas) == "undefined" ? 0 : preferencias.gigsAbrirTarefas;
	preferencias.gigsApreciarPeticoes = typeof(preferencias.gigsApreciarPeticoes) == "undefined" ? 0 : preferencias.gigsApreciarPeticoes;
	preferencias.gigsApreciarPeticoes2 = typeof(preferencias.gigsApreciarPeticoes2) == "undefined" ? 0 : preferencias.gigsApreciarPeticoes2;
	preferencias.gigsApreciarPeticoes3 = typeof(preferencias.gigsApreciarPeticoes3) == "undefined" ? 0 : preferencias.gigsApreciarPeticoes3;
	preferencias.gigsOcultarChips = typeof(preferencias.gigsOcultarChips) == "undefined" ? 0 : preferencias.gigsOcultarChips;
	preferencias.gigsOcultarLembretes = typeof(preferencias.gigsOcultarLembretes) == "undefined" ? 0 : preferencias.gigsOcultarLembretes;
	preferencias.gigsTirarSomLembretes = typeof(preferencias.gigsTirarSomLembretes) == "undefined" ? false : preferencias.gigsTirarSomLembretes;
	preferencias.gigsCriarMenu = typeof(preferencias.gigsCriarMenu) == "undefined" ? 0 : preferencias.gigsCriarMenu;
	preferencias.gigsCriarMenuGuardarNumeroProcesso = typeof(preferencias.gigsCriarMenuGuardarNumeroProcesso) == "undefined" ? 0 : preferencias.gigsCriarMenuGuardarNumeroProcesso;
	preferencias.gigsCriarMenuAbrirPainelCopiaECola = typeof(preferencias.gigsCriarMenuAbrirPainelCopiaECola) == "undefined" ? false : preferencias.gigsCriarMenuAbrirPainelCopiaECola;
	preferencias.sanearAJG = typeof(preferencias.sanearAJG) == "undefined" ? false : preferencias.sanearAJG;
	preferencias.mapeamentoDeIDs = typeof(preferencias.mapeamentoDeIDs) == "undefined" ? false : preferencias.mapeamentoDeIDs;
	preferencias.ocultarPublicacoesDJEN = typeof(preferencias.ocultarPublicacoesDJEN) == "undefined" ? '' : preferencias.ocultarPublicacoesDJEN;
	preferencias.ocultarDocumentosExcluidos = typeof(preferencias.ocultarDocumentosExcluidos) == "undefined" ? '' : preferencias.ocultarDocumentosExcluidos;
	preferencias.exibirFaseProcessualNaTimeline = typeof(preferencias.exibirFaseProcessualNaTimeline) == "undefined" ? '' : preferencias.exibirFaseProcessualNaTimeline;
	preferencias.gigsTipoAtencao = typeof(preferencias.gigsTipoAtencao) == "undefined" ? 1 : preferencias.gigsTipoAtencao;

	preferencias.gigsDetalhesLeft = typeof(preferencias.gigsDetalhesLeft) == "undefined" ? window.screen.availLeft : preferencias.gigsDetalhesLeft;
	preferencias.gigsDetalhesTop = typeof(preferencias.gigsDetalhesTop) == "undefined" ? window.screen.availTop : preferencias.gigsDetalhesTop;
	preferencias.gigsDetalhesWidth = typeof(preferencias.gigsDetalhesWidth) == "undefined" ? window.screen.availWidth : preferencias.gigsDetalhesWidth;
	preferencias.gigsDetalhesHeight = typeof(preferencias.gigsDetalhesHeight) == "undefined" ? window.screen.availHeight : preferencias.gigsDetalhesHeight;
	preferencias.gigsTarefaLeft = typeof(preferencias.gigsTarefaLeft) == "undefined" ? window.screen.availLeft : preferencias.gigsTarefaLeft;
	preferencias.gigsTarefaTop = typeof(preferencias.gigsTarefaTop) == "undefined" ? window.screen.availTop : preferencias.gigsTarefaTop;
	preferencias.gigsTarefaWidth = typeof(preferencias.gigsTarefaWidth) == "undefined" ? window.screen.availWidth : preferencias.gigsTarefaWidth;
	preferencias.gigsTarefaHeight = typeof(preferencias.gigsTarefaHeight) == "undefined" ? window.screen.availHeight : preferencias.gigsTarefaHeight;
	preferencias.gigsGigsLeft = typeof(preferencias.gigsGigsLeft) == "undefined" ? window.screen.availLeft : preferencias.gigsGigsLeft;
	preferencias.gigsGigsTop = typeof(preferencias.gigsGigsTop) == "undefined" ? window.screen.availTop : preferencias.gigsGigsTop;
	preferencias.gigsGigsWidth = typeof(preferencias.gigsGigsWidth) == "undefined" ? window.screen.availWidth : preferencias.gigsGigsWidth;
	preferencias.gigsGigsHeight = typeof(preferencias.gigsGigsHeight) == "undefined" ? window.screen.availHeight : preferencias.gigsGigsHeight;
	preferencias.atalhosDetalhes = typeof(preferencias.atalhosDetalhes) == "undefined" ? [true,true,true,false,true,false,true,false,false,true,false,false,true,false,true,false,false,false,true,false,false,true,false,false,true] : preferencias.atalhosDetalhes;
	preferencias.processo_memoria = typeof(preferencias.processo_memoria) == "undefined" ? "" : preferencias.processo_memoria;

}

/**
 *
 * @param {Partial<Preferencias>} preferencias
 */
async function preencherConfiguracaoConciliaJT(preferencias) {
	preferencias.configURLs = typeof(preferencias.configURLs) == "undefined" ? await obterUrlsConciliaJT(preferencias.num_trt) : preferencias.configURLs;
}

/** @param {Partial<Preferencias>} preferencias */
async function preencherVariaveisModulo2(preferencias) {
	preferencias.modulo2 = typeof (preferencias.modulo2) == "undefined" ? [] : preferencias.modulo2;
	preferencias.modulo2 = await inserirFaseModulo2();
	async function inserirFaseModulo2() {
		return new Promise(resolve2 => {
			let lista = [];
			for (const [pos, item] of preferencias.modulo2.entries()) {
				if (item.includes('Conhecimento') || item.includes('Liquidação') || item.includes('Execução') || item.includes('Arquivados') || item.includes('Todas')) {
					lista.push(item);
				} else {
					let itemTemp = item.split('|');
					itemTemp.splice(2, 0, "Todas");
					let novoItem = itemTemp.toString().replace(/,/g,'|');
					lista.push(novoItem);
				}
			}
			resolve2(lista);
		});
	}
}

/**
 * @param {Partial<Preferencias>} preferencias
 */
function preencherVariaveisModulo5(preferencias) {
	preferencias.modulo5_obterSaldoSIF = typeof (preferencias.modulo5_obterSaldoSIF) == "undefined" ? true : preferencias.modulo5_obterSaldoSIF;
	preferencias.modulo5_conferirTeimosinhaEmLote = typeof (preferencias.modulo5_conferirTeimosinhaEmLote) == "undefined" ? true : preferencias.modulo5_conferirTeimosinhaEmLote;
	preferencias.modulo5_juizDaMinuta = typeof (preferencias.modulo5_juizDaMinuta) == "undefined" ? true : preferencias.modulo5_juizDaMinuta;
	preferencias.modulo5_processosSemAudienciaDesignada = typeof (preferencias.modulo5_processosSemAudienciaDesignada) == "undefined" ? true : preferencias.modulo5_processosSemAudienciaDesignada;
	preferencias.modulo5_processosSemGigsCadastrado = typeof (preferencias.modulo5_processosSemGigsCadastrado) == "undefined" ? true : preferencias.modulo5_processosSemGigsCadastrado;
	preferencias.modulo5_processosParadosHaMaisDeXXDias = typeof (preferencias.modulo5_processosParadosHaMaisDeXXDias) == "undefined" ? true : preferencias.modulo5_processosParadosHaMaisDeXXDias;
	preferencias.modulo5_conferirGarimpoEmLote = typeof (preferencias.modulo5_conferirGarimpoEmLote) == "undefined" ? true : preferencias.modulo5_conferirGarimpoEmLote;
	preferencias.modulo5_obterConcilia = typeof (preferencias.modulo5_obterConcilia) == "undefined" ? true : preferencias.modulo5_obterConcilia;
}

/**
 * @param {Partial<Preferencias>} preferencias
 */
function preencherVariaveisModulo6(preferencias) {
	preferencias.emailAutomatizado = typeof (preferencias.emailAutomatizado) == "undefined" ? new EmailAutomatizado("Processo n. #{processo} (#{tipoDocumento} Id. #{idDocumento})", "Encaminho o(a) #{tipoDocumento} (Id. #{idDocumento}), expedido no processo #{processo}, para ciência ou cumprimento.\n\nO documento poderá ser acessado via internet mediante o seguinte link: #{autenticacao}\n\nAtenciosamente,", "#{servidor}\nDiretor de Secretaria\n#{OJServidor}", false, '') : preferencias.emailAutomatizado;
	preferencias.emailAutomatizado.destinatario = typeof (preferencias.emailAutomatizado.destinatario) == "undefined" ? false : preferencias.emailAutomatizado.destinatario;
	preferencias.emailAutomatizado.ignorar = typeof (preferencias.emailAutomatizado.ignorar) == "undefined" ? false : preferencias.emailAutomatizado.ignorar;
}

/**
 * @param {Partial<Preferencias>} preferencias
 */
function preencherVariaveisModulo7(preferencias) {
	preferencias.aaAnexar = typeof (preferencias.aaAnexar) == "undefined" ? [] : preferencias.aaAnexar;
	preferencias.aaComunicacao = typeof (preferencias.aaComunicacao) == "undefined" ? [] : preferencias.aaComunicacao;
	preferencias.aaAutogigs = typeof (preferencias.aaAutogigs) == "undefined" ? [] : preferencias.aaAutogigs;
	preferencias.aaDespacho = typeof (preferencias.aaDespacho) == "undefined" ? [] : preferencias.aaDespacho;
	preferencias.aaMovimento = typeof (preferencias.aaMovimento) == "undefined" ? [] : preferencias.aaMovimento;
	preferencias.aaChecklist = typeof (preferencias.aaChecklist) == "undefined" ? [] : preferencias.aaChecklist;
	preferencias.aaNomearPerito = typeof (preferencias.aaNomearPerito) == "undefined" ? [] : preferencias.aaNomearPerito;
	preferencias.aaLancarMovimentos = typeof (preferencias.aaLancarMovimentos) == "undefined" ? [] : preferencias.aaLancarMovimentos;
	preferencias.aaVariados = typeof (preferencias.aaVariados) == "undefined" ? aaVariados_temp : preferencias.aaVariados;
	//TODO: achei que tinha a ver com o modulo 7
	preferencias.monitorGIGS = typeof(preferencias.monitorGIGS) == "undefined" ? [] : preferencias.monitorGIGS;
}

/** @param {Partial<Preferencias>} preferencias */
function preencherVariaveisModulo8(preferencias) {
	preferencias.modulo8 = typeof (preferencias.modulo8) == "undefined" ? [] : preferencias.modulo8;
	preferencias.modulo8_ignorarZero = typeof (preferencias.modulo8_ignorarZero) == "undefined" ? false : preferencias.modulo8_ignorarZero;
}

/**
 * @param {Partial<Preferencias>} preferencias
 */
function preencherVariaveisConvenios(preferencias) {
	preferencias.sisbajud = typeof(preferencias.sisbajud) == "undefined" ? {juiz: '', vara: '', cnpjRaiz: '', teimosinha: '', contasalario: '', naorespostas: '', valor_desbloqueio: '', banco_preferido: '', agencia_preferida: '', preencherValor: '', confirmar: '', executarAAaoFinal: '', salvarEprotocolar: ''} : preferencias.sisbajud;
	preferencias.sisbajud.juiz = typeof(preferencias.sisbajud.juiz) == "undefined" ? "" : preferencias.sisbajud.juiz;
	preferencias.sisbajud.vara = typeof(preferencias.sisbajud.vara) == "undefined" ? "" : preferencias.sisbajud.vara;
	preferencias.sisbajud.cnpjRaiz = typeof(preferencias.sisbajud.cnpjRaiz) == "undefined" ? "não" : preferencias.sisbajud.cnpjRaiz;
	preferencias.sisbajud.teimosinha = typeof(preferencias.sisbajud.teimosinha) == "undefined" ? "não" : preferencias.sisbajud.teimosinha;
	preferencias.sisbajud.contasalario = typeof(preferencias.sisbajud.contasalario) == "undefined" ? "não" : preferencias.sisbajud.contasalario;
	preferencias.sisbajud.naorespostas = typeof(preferencias.sisbajud.naorespostas) == "undefined" ? "Cancelar" : preferencias.sisbajud.naorespostas;
	preferencias.sisbajud.valor_desbloqueio = typeof(preferencias.sisbajud.valor_desbloqueio) == "undefined" ? "não" : preferencias.sisbajud.valor_desbloqueio;
	preferencias.sisbajud.banco_preferido = typeof(preferencias.sisbajud.banco_preferido) == "undefined" ? "não" : preferencias.sisbajud.banco_preferido;
	preferencias.sisbajud.agencia_preferida = typeof(preferencias.sisbajud.agencia_preferida) == "undefined" ? "não" : preferencias.sisbajud.agencia_preferida;
	preferencias.sisbajud.preencherValor = typeof(preferencias.sisbajud.preencherValor) == "undefined" ? "não" : preferencias.sisbajud.preencherValor;
	preferencias.sisbajud.confirmar = typeof(preferencias.sisbajud.confirmar) == "undefined" ? "não" : preferencias.sisbajud.confirmar;
	preferencias.sisbajud.executarAAaoFinal = typeof(preferencias.sisbajud.executarAAaoFinal) == "undefined" ? "Nenhum" : preferencias.sisbajud.executarAAaoFinal;
	preferencias.sisbajud.salvarEprotocolar = typeof(preferencias.sisbajud.salvarEprotocolar) == "undefined" ? "não" : preferencias.sisbajud.salvarEprotocolar;
	preferencias.sisbajud = {juiz: preferencias.sisbajud.juiz, vara: preferencias.sisbajud.vara, cnpjRaiz: preferencias.sisbajud.cnpjRaiz, teimosinha: preferencias.sisbajud.teimosinha, contasalario: preferencias.sisbajud.contasalario, naorespostas: preferencias.sisbajud.naorespostas, valor_desbloqueio: preferencias.sisbajud.valor_desbloqueio, banco_preferido: preferencias.sisbajud.banco_preferido, agencia_preferida: preferencias.sisbajud.agencia_preferida, preencherValor: preferencias.sisbajud.preencherValor, confirmar: preferencias.sisbajud.confirmar, executarAAaoFinal: preferencias.sisbajud.executarAAaoFinal, salvarEprotocolar: preferencias.sisbajud.salvarEprotocolar};
	preferencias.sisbajud.naorespostas = preferencias.sisbajud.naorespostas == "" ? "Cancelar" : preferencias.sisbajud.naorespostas;

	//ajustando pq agora perdeu o juiz responsavel
	preferencias.serasajud = typeof(preferencias.serasajud) == "undefined" ? {foro: "", vara: "", prazo_atendimento: "", aa: "Nenhum"} : preferencias.serasajud;
	preferencias.serasajud.aa = preferencias.serasajud.aa ? preferencias.serasajud.aa : "Nenhum";
	preferencias.serasajud = {"foro": preferencias.serasajud.foro, "vara": preferencias.serasajud.vara, "prazo_atendimento": preferencias.serasajud.prazo_atendimento, "aa": preferencias.serasajud.aa}
	preferencias.prevjud = typeof(preferencias.prevjud) == "undefined" ? {aa: "Nenhum",opt1:false,aa2: "Nenhum"} : preferencias.prevjud;
	preferencias.prevjud.aa = preferencias.prevjud.aa ? preferencias.prevjud.aa : "Nenhum";
	preferencias.prevjud.aa2 = preferencias.prevjud.aa2 ? preferencias.prevjud.aa2 : "Nenhum";
	preferencias.prevjud.opt1 = preferencias.prevjud.opt1 ? preferencias.prevjud.opt1 : false;

	preferencias.renajud = typeof(preferencias.renajud) == "undefined" ? {tipo_restricao: "", comarca: "", tribunal: "", orgao: "", juiz: "", juiz2: ""} : preferencias.renajud;

	preferencias.saj = typeof(preferencias.saj) == "undefined" ? { vara: "", juiz: "", prazoResposta: "", extratomercantil: "", extratomovimentacao: "", extratomovfinanceira: "", faturacartaocredito: "", propostaaberturaconta: "", contratocambio: "", registrocambio: "", copiacheque: "", saldofgts: "", recebernotificacao: "", email: "", telefone: "" } : preferencias.saj;

}

/**
 * @param { Partial<Preferencias>} preferencias
 */
function preencherVariaveisModulo9(preferencias) {
	let cnibNovaConfiguracao = { 'ativar': false, 'velocidade': 0, 'inclusao': [true, true, true, true, true, 'Nenhum'], 'exclusao': [true, true, true, true, 'Nenhum'] };
	preferencias.modulo9 = typeof (preferencias.modulo9) == "undefined" ? { sisbajud: true, renajud: true, cnib: cnibNovaConfiguracao, serasajud: true, ccs: [true, false, false, false, false, 5], crcjud: true, onr: false, gprec: true, ajjt: true, siscondj: [true, 10], garimpo: [true, ""], sif: [true, 10], pjecalc: true, prevjud: true, protestojud: true, sniper: true, censec: true, celesc: true, casan: true, sigef: true, infoseg: true, ecarta: true, saj: true } : preferencias.modulo9;
	preferencias.modulo9.cnib = typeof (preferencias.modulo9.cnib) == "undefined" ? cnibNovaConfiguracao : preferencias.modulo9.cnib;
	preferencias.modulo9.cnib = Array.isArray(preferencias.modulo9.cnib) ? cnibNovaConfiguracao : preferencias.modulo9.cnib;

	preferencias.modulo9.ccs = Array.isArray(preferencias.modulo9.ccs) ? preferencias.modulo9.ccs : [preferencias.modulo9.ccs,false,false,false,false,5,'Nenhum'];
	preferencias.modulo9.ccs[6] = (preferencias.modulo9.ccs[6] ? preferencias.modulo9.ccs[6] : 'Nenhum');
	preferencias.modulo9.sif = (preferencias.modulo9.sif[1]) ? preferencias.modulo9.sif : [true,10];
	preferencias.modulo9.sif = (preferencias.modulo9.sif[2]) ? preferencias.modulo9.sif : [preferencias.modulo9.sif[0],preferencias.modulo9.sif[1],'dia'];
	preferencias.modulo9.siscondj = (preferencias.modulo9.siscondj) ? preferencias.modulo9.siscondj : [true,10,true];
	preferencias.modulo9.siscondj[2] = typeof(preferencias.modulo9.siscondj[2]) == "undefined" ? true : preferencias.modulo9.siscondj[2];
	preferencias.modulo9.gprec = preferencias.modulo9.gprec[1] ? preferencias.modulo9.gprec : [true,5,false];
	preferencias.modulo9.gprec = !preferencias.modulo9.gprec[2] ? [preferencias.modulo9.gprec[0],preferencias.modulo9.gprec[1],false] : [preferencias.modulo9.gprec[0],preferencias.modulo9.gprec[1],preferencias.modulo9.gprec[2]];
	preferencias.modulo9.gprec = !preferencias.modulo9.gprec[3] ? [preferencias.modulo9.gprec[0],preferencias.modulo9.gprec[1],preferencias.modulo9.gprec[2],'rpv'] : [preferencias.modulo9.gprec[0],preferencias.modulo9.gprec[1],preferencias.modulo9.gprec[2],preferencias.modulo9.gprec[3]];
	if (!Array.isArray(preferencias.modulo9.garimpo)) { preferencias.modulo9.garimpo = [preferencias.modulo9.garimpo,''] }
	//TODO
	if (!Array.isArray(preferencias.modulo9.ecarta)) { preferencias.modulo9.ecarta = [preferencias.modulo9.ecarta,''] }

}

/**
 * @param {Partial<Preferencias>} preferencias
 */
function preencherVariaveisModulo10(preferencias) {
	preferencias.modulo10 = typeof (preferencias.modulo10) == "undefined" ? [] : preferencias.modulo10;
	preferencias.modulo10_juntadaMidia = typeof (preferencias.modulo10_juntadaMidia) == "undefined" ? [false, ''] : preferencias.modulo10_juntadaMidia;
	preferencias.modulo10_painelCopiaeCola = typeof (preferencias.modulo10_painelCopiaeCola) == "undefined" ? false : preferencias.modulo10_painelCopiaeCola;
	preferencias.modulo10_salaFavorita = preferencias.modulo10_salaFavorita ?? '' ;

}

/**
 * @param {Partial<Preferencias>} preferencias
 */
function preencherVariaveisModulo11(preferencias) {
	preferencias.modulo11 = typeof (preferencias.modulo11) == "undefined" ? [] : preferencias.modulo11;
	preferencias.modulo11_AssinarAutomaticamente = typeof (preferencias.modulo11_AssinarAutomaticamente) == "undefined" ? false : preferencias.modulo11_AssinarAutomaticamente;
}


/** @param {Partial<Preferencias>} preferencias */
function preencherVariaveisModuloExtras(preferencias) {
	preferencias.zoom_editor = typeof(preferencias.zoom_editor) == "undefined" ? 1 : preferencias.zoom_editor;
	preferencias.extrasFecharJanelaExpediente = typeof(preferencias.extrasFecharJanelaExpediente) == "undefined" ? true : preferencias.extrasFecharJanelaExpediente;
	preferencias.extrasSugerirTipoAoAnexar = typeof(preferencias.extrasSugerirTipoAoAnexar) == "undefined" ? true : preferencias.extrasSugerirTipoAoAnexar;
	preferencias.extrasSugerirDescricaoAoAnexar = typeof(preferencias.extrasSugerirDescricaoAoAnexar) == "undefined" ? true : preferencias.extrasSugerirDescricaoAoAnexar;
	preferencias.extrasProcurarExecucao = typeof(preferencias.extrasProcurarExecucao) == "undefined" ? 'SAO' : preferencias.extrasProcurarExecucao;
	preferencias.extrasTiposDocumentoProcuracao = preferencias.extrasTiposDocumentoProcuracao ?? 'Procuração, Substabelecimento' ;
	preferencias.extrasTiposDocumentoSentencasAcordao =  preferencias.extrasTiposDocumentoSentencasAcordao ?? 'Sentença, Acórdão';
	preferencias.extrasTiposDocumentoCustas =  preferencias.extrasTiposDocumentoCustas ?? 'Custas, emolumentos, Preparo';
	preferencias.extrasTiposDocumentoDepositoRecursal =  preferencias.extrasTiposDocumentoDepositoRecursal ?? 'Recursal, Preparo';
	preferencias.extrasExibirPreviaDocumentoMouseOver = preferencias.extrasExibirPreviaDocumentoMouseOver ?? false;
	preferencias.extrasExibirPreviaDocumentoFocus = preferencias.extrasExibirPreviaDocumentoFocus ?? false;
	preferencias.extrasFocusSempre = preferencias.extrasFocusSempre ?? false;
	preferencias.extrasERecTipoGigsSemTema = preferencias.extrasERecTipoGigsSemTema ?? 'Não tem tese (TST e STF)';
	preferencias.extrasPrazoEmLote = typeof(preferencias.extrasPrazoEmLote) == "undefined" ? ['0','2','5','8','10','15'] : preferencias.extrasPrazoEmLote;

    if (preferencias.extrasFocusSempre) {
          browser.runtime.sendMessage({
            tipo: "insertCSS",
            file: "maisPJe_focus.css",
        });
    }
}

/**
 * @param {boolean} restaurar
 * @returns {Promise<any>}
 */
async function checarVariaveis(restaurar=false) {
	return new Promise(async resolve => {
		preencherVariaveisComuns(preferencias);
		await preencherConfiguracaoConciliaJT(preferencias);
		preferencias.tarefaResponsavel = typeof(preferencias.tarefaResponsavel) == "undefined" ? "" : preferencias.tarefaResponsavel;
		preferencias.prazoResponsavel = typeof(preferencias.prazoResponsavel) == "undefined" ? "" : preferencias.prazoResponsavel;
		preferencias.atividadeResponsavel = typeof(preferencias.atividadeResponsavel) == "undefined" ? "" : preferencias.atividadeResponsavel;
		preencherVariaveisModulo1(preferencias);
		preferencias.lista_monitores = typeof(preferencias.lista_monitores) == "undefined" ? [{"left":0,"top":0,"width":0,"height":0}] : preferencias.lista_monitores;
		preferencias.lista_monitores = preferencias.lista_monitores.length < 1 ? [{"left":0,"top":0,"width":0,"height":0}] : preferencias.lista_monitores;

		preferencias.gigsPesquisaDeDocumentos = typeof(preferencias.gigsPesquisaDeDocumentos) == "undefined" ? 0 : preferencias.gigsPesquisaDeDocumentos;
		preferencias.guiaPersonalizadaDetalhes = typeof(preferencias.guiaPersonalizadaDetalhes) == "undefined" ? '' : preferencias.guiaPersonalizadaDetalhes;
		//TODO: essa variavel esta em segundos aqui e em milissegundos no gigs-plugin.js. Qual o correto?
		preferencias.maisPje_velocidade_interacao = typeof(preferencias.maisPje_velocidade_interacao) == "undefined" ? 1 : preferencias.maisPje_velocidade_interacao;
		preencherVariaveisModulo7(preferencias);
		preferencias.meuFiltro = typeof(preferencias.meuFiltro) == "undefined" ? [] : preferencias.meuFiltro;
		preferencias.filtros_Favoritos = typeof(preferencias.filtros_Favoritos) == "undefined" ? [] : preferencias.filtros_Favoritos;
		preencherVariaveisModulo5(preferencias);
		preencherVariaveisModulo6(preferencias);
		preferencias.versaoPje =  typeof(preferencias.versaoPje) == "undefined" ? "" : preferencias.versaoPje;
		//tempAuto esta comentada no gigs-plugin, alem de ter um objeto e nao um numero
		preferencias.tempAuto = typeof(preferencias.tempAuto) == "undefined" ? 10 : preferencias.tempAuto;
		preferencias.monitorGIGS = typeof(preferencias.monitorGIGS) == "undefined" ? [] : preferencias.monitorGIGS;
		preferencias.pjExtension_depositos = typeof(preferencias.pjExtension_depositos) == "undefined" ? [] : preferencias.pjExtension_depositos;
		await preencherVariaveisModulo2(preferencias);
		preencherVariaveisConvenios(preferencias);
		//TODO: essa linha so existe nesse arquivo. Isso ta certo? nao parece que esse typeof vai ser verdadeiro nunca.
		preferencias.sisbajud.teimosinha = typeof(preferencias.sisbajud.teimosinha) == "sim" ? "60" : preferencias.sisbajud.teimosinha;

		preencherVariaveisModulo8(preferencias);
		preencherVariaveisModulo10(preferencias);
		preencherVariaveisModulo11(preferencias);
		preencherVariaveisMenuKaizen(preferencias);

		preencherVariaveisModulo9(preferencias);

		preferencias.pesquisaRapidaDeProcessoEmAba = typeof(preferencias.pesquisaRapidaDeProcessoEmAba) == "undefined" ? false : preferencias.pesquisaRapidaDeProcessoEmAba;
		preencherVariaveisModuloExtras(preferencias);

		//verificar velocidade de interação //TODO: isso deveria ir para o modulo 7? ou so faz sentido na tela de opcoes?
		if (parseInt(String(preferencias.maisPje_velocidade_interacao)) > 2.5) {
			alert('Identificado erro na velocidade de interação!!!\n\nEla foi reajustada para 1 segundo!')
			preferencias.maisPje_velocidade_interacao = 1;
		}

		if (!preferencias.desativarAjusteJanelas) {
			console.log("...analisando monitores");
			console.log("      |___________" + preferencias.lista_monitores.length);
			if (preferencias.lista_monitores.length == 0) { //somente verifica monitores automaticamente se a opção de ajuste estiver desmarcada e a lista de monitores estiver zerada
				preferencias.lista_monitores = await testarMonitores();
			}
		}

		// salvando o modulo9.ecarta para aqueles usuarios que não tem a extensão
		if (typeof(preferencias.modulo9.ecarta) == "undefined") {
			preferencias.modulo9.ecarta = [];
			preferencias.modulo9.ecarta[0] = true;
			preferencias.modulo9.ecarta[1] = '';
			await guardarModulo9();
		}
		if (typeof(preferencias.modulo9.saj) == "undefined") {
			preferencias.modulo9.saj = true;
			await guardarModulo9();
		}

		// if (restaurar == 1) {

		// } else if () {

		// }
		let guardarStorage = browser.storage.local.set({ 'lista_monitores': preferencias.lista_monitores });
		Promise.all([guardarStorage]).then(values => {
			// console.log("ENTROU")
			if (preferencias.concordo) {
				mostrarOpcoes(restaurar);
				resolve(true);
			} else {
				browser.runtime.sendMessage({tipo: 'permissao'});
				window.close();
			}

		});

		try {
			let linksPessoaisMenuLateral = browser.storage.local.set({ 'linksMenuLateral': preferencias.linksMenuLateral });
			Promise.all([linksPessoaisMenuLateral]).then(values => { console.info(values); })

		} catch (err) {
			console.error('erro ao tentar salvar links personalizados', err);
		}
	});
}
