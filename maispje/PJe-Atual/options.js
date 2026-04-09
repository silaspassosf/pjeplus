var monitores = [];
/** @type {Partial<Preferencias>} */
var preferencias = {};
var aaAnexar_temp = [];
var aaComunicacao_temp = [];
var aaAutogigs_temp = [];
var aaDespacho_temp = [];
var aaMovimento_temp = [];
var aaChecklist_temp = [];
var aaNomearPerito_temp = [];
var aaVariados_temp = [
	{id:"Atualizar Timeline",nm_botao:"Atualizar Timeline",descricao:"Ação Automatizada para ATUALIZAR a timeline de documentos da janela DETALHES DO PROCESSO",temporizador:"0",ativar:true},
	{id:"Atualizar Pagina",nm_botao:"Atualizar Pagina",descricao:"Ação Automatizada para ATUALIZAR a janela DETALHES DO PROCESSO",temporizador:"1",ativar:true},
	{id:"Fechar Pagina",nm_botao:"Fechar Pagina",descricao:"Ação Automatizada para fechar a janela DETALHES DO PROCESSO",temporizador:"3",ativar:true},
	{id:"Apreciar Peticoes",nm_botao:"Apreciar Peticoes",descricao:"Ação Automatizada para apreciar petições na janela DETALHES DO PROCESSO",temporizador:"1",ativar:true},
	{id:"Atalho F2",nm_botao:"Atalho F2",descricao:"Funcionalidade do Menu KAIZEN: Permite ativar/desativar a criação de uma área na tela para acionar a tecla 'F2' ao repousar o mouse em cima pelo tempo ajustado no 'temporizador'.",temporizador:"2",ativar:true},
	{id:"Atalho F3",nm_botao:"Atalho F3",descricao:"Funcionalidade do Menu KAIZEN: Permite ativar/desativar a criação de uma área na tela para acionar a tecla 'F3' ao repousar o mouse em cima pelo tempo ajustado no 'temporizador'.",temporizador:"2",ativar:true},
	{id:"Atalho F4",nm_botao:"Atalho F4",descricao:"Funcionalidade do Menu KAIZEN: Permite ativar/desativar a criação de uma área na tela para acionar a tecla 'F4' ao repousar o mouse em cima pelo tempo ajustado no 'temporizador'.",temporizador:"2",ativar:true},
	{id:"SISBAJUD F2",nm_botao:"SISBAJUD F2",descricao:"Funcionalidade SISBAJUD: ativa automaticamente uma minuta de bloqueio de valores sobre o polo passivo no convênio SISBAJUD. A janela do convênio precisa estar aberta e visível.",temporizador:"2",ativar:true},
	{id:"Assinar Expedientes",nm_botao:"Assinar Expedientes",descricao:"Ação Automatizada que permite assinar os expedientes em lote.",temporizador:"0",ativar:true},
	{id:"Assinar Documentos",nm_botao:"Assinar Documentos",descricao:"Ação Automatizada que permite assinar em lote documentos pendentes no Anexar Documento.",temporizador:"0",ativar:true},
	{id:"Excluir BNDT",nm_botao:"Excluir BNDT",descricao:"Ação Automatizada que permite excluir todas as partes do BNDT.",temporizador:"0",ativar:true},
	{id:"Enviar Email",nm_botao:"Enviar Email",descricao:"Ação Automatizada que permite enviar email personalizado em Lote.",temporizador:"0",ativar:true,objeto:{destinatario:"",titulo:"",corpo:"",assinatura:""}},
	{id:"AUTOGIGS>Renovar Atividade GIGS",nm_botao:"AUTOGIGS>Renovar Atividade GIGS",descricao:"Ação Automatizada que renova uma atividade GIGS, excluindo uma anterior e cadastrando outra igual.",temporizador:"0",ativar:true},
	{id:"AUTOGIGS>Trocar Responsável Atividade GIGS",nm_botao:"AUTOGIGS>Trocar Responsável Atividade GIGS",descricao:"Ação Automatizada que renova o responsável por uma atividade GIGS já existente.",temporizador:"0",ativar:true},
	{id:"DESPACHO>Trocar Magistrado Responsável",nm_botao:"DESPACHO>Trocar Magistrado Responsável",descricao:"Ação Automatizada que substitui o magistrado responsável pela minuta do DESPACHO, cancelando a atual minuta, salvando o conteúdo dela na memória e criando uma nova minuta com aquele conteúdo para o novo juiz configurado no módulo 8.",temporizador:"0",ativar:true},
	{id:"DESPACHO>Rejeitar Prevenção",nm_botao:"DESPACHO>Rejeitar Prevenção",descricao:"Ação Automatizada para rejeitar a prevenção de um processo de forma automática.",temporizador:"0",ativar:true,objeto:{modelo:""}},
	{id:"DESPACHO>Aceitar Prevenção",nm_botao:"DESPACHO>Aceitar Prevenção",descricao:"Ação Automatizada para aceitar a prevenção de um processo de forma automática.",temporizador:"0",ativar:true,objeto:{modelo:""}},
	{id:"MOVIMENTO>Renovar a Data da Tarefa",nm_botao:"MOVIMENTO>Renovar a Data da Tarefa",descricao:"Ação Automatizada que renova a data em que o processo chegou na tarefa atual, movendo o processo para a tarefa Análise e devolvendo-o para a antiga tarefa..",temporizador:"0",ativar:true},
	{id:"RETIFICAR AUTUAÇÃO>Cadastrar Advogado",nm_botao:"RETIFICAR AUTUAÇÃO>Cadastrar Advogado",descricao:"Ação Automatizada para vincular um advogado específico à uma parte no processo.",temporizador:"0",ativar:true,objeto:{advogado:"",parte:""}},
	{id:"KAIZEN>Incluir em Pauta",nm_botao:"KAIZEN>Incluir em Pauta",descricao:"Ação Automatizada para incluir um determinado processo em pauta.",temporizador:"0",ativar:true}
];
var listaModulo2_temp = [];
var listaModulo8_temp = [];
var listaModulo10_temp = [];
var listaModulo11_temp = [];
let aaItemMenuDetalhes = ['Listar Todas','Concluso ao Magistrado','Movimentar Processo','Guardar dados das partes','Abrir o Gigs','Acesso a Terceiros','Anexar documentos','Audiências e Sessões','Download do processo completo','BNDT','Abrir cálculos do processo','Criar Intimação/Expediente','Controle de Segredo','Abre a tela com os dados financeiros','Visualizar intimações/expedientes do processo','Histórico de Sigilo','Lembretes','Lançar movimentos','Obrigação de Pagar','Pagamento','Perícias','Quadro de recursos','Reprocessar chips do processo','Retificar autuação','Retirar Valor Histórico','Verificar Impedimentos e Suspeições','Consultar Domicílio Eletrônico','Copiar Número do Processo'];
var filtros_storage = [];
var mapeadosAADescendentes = false;
var itensModulo1SemAtalhos = getItensModulo1SemAtalhos(salvarOpcoes)
itensModulo1SemAtalhos.push(new ItemCheckboxMenu('gigsAbrirDetalhes', salvarOpcoes))
itensModulo1SemAtalhos.push(new ItemCheckboxMenu('gigsTipoAtencao', salvarOpcoes))

async function iniciar() {
	const opcoesHandler = await browser.storage.local.get(null);
	Promise.all([opcoesHandler]).then(async result => {
		preferencias = result[0];

		if (!preferencias.trt || !preferencias.grau_usuario || !preferencias.versaoPje) {
			browser.runtime.sendMessage({tipo: 'iconeNavegador', valor: '+PJe: Atenção', icone: 'ico_16_alerta.png'});
		} else {
			browser.runtime.sendMessage({tipo: 'iconeNavegador', valor: '+PJe: Atalho Rápido', icone: 'ico_16.png'});
		}

		checarVariaveis();

		if ((preferencias?.trt.includes('trt12') || preferencias?.trt.includes('trt9'))
			&& preferencias?.grau_usuario.includes('segundograu')) {
			let moduloErec = await esperarElemento('.somenteTRT12');
			if (moduloErec) { moduloErec.style.display = 'inherit';}
		}
	});
}

function configurarModoLGPD(modoLGPD) {
	const botao = document.getElementById("modoLGPD");
	const icone = botao.querySelector('i');
	// console.info(botao, icone)
	if (modoLGPD) {
		icone.className = 'icone lgpd-on t20';
		botao.setAttribute('data-tooltip','Modo LGPD Ativado');
		botao.setAttribute('aria-pressed','true');
	} else {
		icone.className = 'icone lgpd-off t20';
		botao.setAttribute('data-tooltip','Modo LGPD Desativado');
		botao.setAttribute('aria-pressed','false');
	}
}

function configurarModoNoite(modoNoite) {
	const botao = document.getElementById("modoNoite");
	const icone = botao.querySelector('i');
	if (modoNoite) {
		icone.style.backgroundImage = 'linear-gradient(to top, #3920d5, #3920d57d, gold, gold)';
		botao.setAttribute('data-tooltip','Modo Noite Ativado');
		botao.setAttribute('aria-pressed','true');
	} else {
		icone.style.backgroundImage = 'unset';
		botao.setAttribute('data-tooltip','Modo Noite Desativado');
		botao.setAttribute('aria-pressed','false');
	}
}

async function mostrarOpcoes(restaurar=false) {
	return new Promise(async resolve => {
		console.log("mostrarOpcoes()");
		limpatela();
		document.getElementById("versao").innerText = "v. " + chrome.runtime.getManifest().version;

		configurarModoLGPD(preferencias.modoLGPD);

		document.getElementById("modoLGPD").addEventListener('click', function() {
			preferencias.modoLGPD = (preferencias.modoLGPD) ? false : true;
			configurarModoLGPD(preferencias.modoLGPD);
			salvarOpcoes();
		});

		configurarModoNoite(preferencias.modoNoite);

		document.getElementById("modoNoite").addEventListener('click', function() {
			preferencias.modoNoite = (preferencias.modoNoite) ? false : true;
			configurarModoNoite(preferencias.modoNoite);
			salvarOpcoes();
		});

		document.querySelector('#desativarAjusteJanelas').checked = preferencias.desativarAjusteJanelas;
		document.querySelector('#desativarAjusteJanelas').addEventListener('click', function () {
			preferencias.desativarAjusteJanelas = document.querySelector('#desativarAjusteJanelas').checked;
			let var1 = browser.storage.local.set({'desativarAjusteJanelas': preferencias.desativarAjusteJanelas});
			Promise.all([var1]).then(values => {
				document.getElementById("overlay").style.display = "flex";
				let Toast = Swal.mixin({
					toast: true,
					position: 'center',
					showConfirmButton: false,
					timer: 1000,
					timerProgressBar: false,
					onOpen: (toast) => {
						setTimeout(function() {
							document.getElementById("overlay").style.display = "none";
						}, 1000)
					}
				})

				Toast.fire({
					icon: 'success',
					title: 'Salvando...'
				})
			});
		});

		let divMonitorDetalhes = document.querySelector('#divMonitorDetalhes');
		let divMonitorTarefas = document.querySelector('#divMonitorTarefas');
		let divMonitorGigs = document.querySelector('#divMonitorGigs');

		document.getElementById("modulo4PaginaInicial").value = preferencias.modulo4PaginaInicial != null ? preferencias.modulo4PaginaInicial : "nenhum";
		document.getElementById("modulo4PaginaInicial").addEventListener('focusout', salvarOpcoes);
		document.getElementById("atalhosPlugin").value = desmontarLinha(preferencias.atalhosPlugin, "|");

		let contador = 0;
		monitores = preferencias.lista_monitores;
		for(let monitor of monitores) {
			criarOpcaoMonitor(divMonitorDetalhes, monitor, contador, preferencias.gigsMonitorDetalhes, 'gigsMonitorDetalhes');
			criarOpcaoMonitor(divMonitorTarefas, monitor, contador, preferencias.gigsMonitorTarefas, 'gigsMonitorTarefas');
			criarOpcaoMonitor(divMonitorGigs, monitor, contador, preferencias.gigsMonitorGigs, 'gigsMonitorGigs');
			contador = contador + 1;
		}

		if (document.querySelector('input[id="gigsMonitorDetalhes' + preferencias.gigsMonitorDetalhes + '"]')) {
			document.querySelector('input[id="gigsMonitorDetalhes' + preferencias.gigsMonitorDetalhes + '"]').checked = true;
		}

		if (document.querySelector('input[id="gigsMonitorTarefas' + preferencias.gigsMonitorTarefas + '"]')) {
			document.querySelector('input[id="gigsMonitorTarefas' + preferencias.gigsMonitorTarefas + '"]').checked = true;
		}
		if (document.querySelector('input[id="gigsMonitorGigs' + preferencias.gigsMonitorGigs + '"]')) {
			document.querySelector('input[id="gigsMonitorGigs' + preferencias.gigsMonitorGigs + '"]').checked = true;
		}

		itensModulo1SemAtalhos.forEach(item => item.configurar(preferencias))

		montarBotoesDetalhes();

		document.getElementById("maisPje_velocidade_interacao").value = preferencias.maisPje_velocidade_interacao;
		document.getElementById("maisPje_velocidade_interacao_label").innerText = preferencias.maisPje_velocidade_interacao;
		document.getElementById("maisPje_velocidade_interacao").addEventListener('input', function () {
			preferencias.maisPje_velocidade_interacao = document.getElementById("maisPje_velocidade_interacao").value;
			document.getElementById("maisPje_velocidade_interacao_label").innerText = preferencias.maisPje_velocidade_interacao;
			salvarOpcoes();
		});

		aaAnexar_temp = preferencias.aaAnexar;
		montarBotoesaaAnexar();
		document.getElementById("aa_anexar_documentos").addEventListener('click', aa_anexar_documentos);

		aaComunicacao_temp = preferencias.aaComunicacao;
		montarBotoesaaComunicacao();
		document.getElementById("aa_comunicacao").addEventListener('click', aa_comunicacao);

		aaAutogigs_temp = preferencias.aaAutogigs;
		montarBotoesaaAutogigs();
		document.getElementById("aa_autogigs").addEventListener('click', aa_autogigs);

		aaDespacho_temp = preferencias.aaDespacho;
		montarBotoesaaDespacho();
		document.getElementById("aa_despacho").addEventListener('click', aa_despacho);

		aaMovimento_temp = preferencias.aaMovimento;
		montarBotoesaaMovimento();
		document.getElementById("aa_movimento").addEventListener('click', aa_movimento);

		aaChecklist_temp = preferencias.aaChecklist;
		montarBotoesaaChecklist();
		document.getElementById("aa_checklist").addEventListener('click', aa_checklist);

		aaNomearPerito_temp = preferencias.aaNomearPerito;
		montarBotoesaaNomearPerito();
		document.getElementById("aa_nomearPerito").addEventListener('click', aa_nomearPerito);

		await ajustarAAVariados(); //pega o que tem na memória e ajusta com os novos casos
		montarBotoesaaVariados();

		document.getElementById("aa_imp_anexar_documentos").addEventListener('click', importarAA);
		document.getElementById("aa_imp_comunicacao").addEventListener('click', importarAA);
		document.getElementById("aa_imp_autogigs").addEventListener('click', importarAA);
		document.getElementById("aa_imp_despacho").addEventListener('click', importarAA);
		document.getElementById("aa_imp_movimento").addEventListener('click', importarAA);
		document.getElementById("aa_imp_checklist").addEventListener('click', importarAA);
		document.getElementById("aa_imp_nomearPerito").addEventListener('click', importarAA);

		document.getElementById("aa_buscar_anexar_documentos").addEventListener('click', buscarAA);
		document.getElementById("aa_buscar_comunicacao").addEventListener('click', buscarAA);
		document.getElementById("aa_buscar_autogigs").addEventListener('click', buscarAA);
		document.getElementById("aa_buscar_despacho").addEventListener('click', buscarAA);
		document.getElementById("aa_buscar_movimento").addEventListener('click', buscarAA);
		document.getElementById("aa_buscar_checklist").addEventListener('click', buscarAA);
		document.getElementById("aa_buscar_nomearPerito").addEventListener('click', buscarAA);

		if (typeof(preferencias.meuFiltro) != "undefined") {
			document.querySelector('#meuFiltro0').checked = preferencias.meuFiltro[0];
			document.querySelector('#meuFiltro0').addEventListener('click', meuFiltroDesmarcar);
			document.querySelector('#meuFiltro1').checked = preferencias.meuFiltro[1];
			document.querySelector('#meuFiltro1').addEventListener('click', meuFiltroDesmarcar);
			document.querySelector('#meuFiltro2').checked = preferencias.meuFiltro[2];
			document.querySelector('#meuFiltro2').addEventListener('click', meuFiltroDesmarcar);
			document.querySelector('#meuFiltro3').checked = preferencias.meuFiltro[3];
			document.querySelector('#meuFiltro3').addEventListener('click', meuFiltroDesmarcar);
			document.querySelector('#meuFiltro4').checked = preferencias.meuFiltro[4];
			document.querySelector('#meuFiltro4').addEventListener('click', meuFiltroDesmarcar);
			document.querySelector('#meuFiltro5').checked = preferencias.meuFiltro[5];
			document.querySelector('#meuFiltro5').addEventListener('click', meuFiltroDesmarcar);
			document.querySelector('#meuFiltro6').checked = preferencias.meuFiltro[6];
			document.querySelector('#meuFiltro6').addEventListener('click', meuFiltroDesmarcar);
			document.querySelector('#meuFiltro7').checked = preferencias.meuFiltro[7];
			document.querySelector('#meuFiltro7').addEventListener('click', meuFiltroDesmarcar);
			document.querySelector('#meuFiltro8').checked = preferencias.meuFiltro[8];
			document.querySelector('#meuFiltro8').addEventListener('click', meuFiltroDesmarcar);
			document.querySelector('#meuFiltro9').checked = preferencias.meuFiltro[9];
			document.querySelector('#meuFiltro9').addEventListener('click', meuFiltroDesmarcar);


			document.querySelector('#meuFiltroJT').checked = preferencias.meuFiltro[10];
			document.querySelector('#meuFiltroJT').onclick = function() {
				document.querySelector('#meuFiltroJS').checked = false;
				document.querySelector('#meuFiltro0').checked = false;
				document.querySelector('#meuFiltro1').checked = false;
				document.querySelector('#meuFiltro2').checked = false;
				document.querySelector('#meuFiltro3').checked = false;
				document.querySelector('#meuFiltro4').checked = false;
				document.querySelector('#meuFiltro5').checked = false;
				document.querySelector('#meuFiltro6').checked = false;
				document.querySelector('#meuFiltro7').checked = false;
				document.querySelector('#meuFiltro8').checked = false;
				document.querySelector('#meuFiltro9').checked = false;
				salvarOpcoes();
			}
			document.querySelector('#meuFiltroJS').checked = preferencias.meuFiltro[11]
			document.querySelector('#meuFiltroJS').onclick = function() {
				document.querySelector('#meuFiltroJT').checked = false;
				document.querySelector('#meuFiltro0').checked = false;
				document.querySelector('#meuFiltro1').checked = false;
				document.querySelector('#meuFiltro2').checked = false;
				document.querySelector('#meuFiltro3').checked = false;
				document.querySelector('#meuFiltro4').checked = false;
				document.querySelector('#meuFiltro5').checked = false;
				document.querySelector('#meuFiltro6').checked = false;
				document.querySelector('#meuFiltro7').checked = false;
				document.querySelector('#meuFiltro8').checked = false;
				document.querySelector('#meuFiltro9').checked = false;
				salvarOpcoes();
			}
		}

		if (typeof(preferencias.filtros_Favoritos) != "undefined") {
			montarFiltrosFavoritos(document.getElementById('filtros_favoristos_relatorio_GIGS'));
		}

		document.getElementById("titulo_email").value = preferencias.emailAutomatizado.titulo;
		document.getElementById("corpo_email").value = preferencias.emailAutomatizado.corpo;
		document.getElementById("assinatura_email").value = preferencias.emailAutomatizado.assinatura;
		document.getElementById("modulo6_destinatario").checked = preferencias.emailAutomatizado.destinatario;

		if (preferencias.emailAutomatizado.destinatario) {
			document.getElementById("modulo6_ignorar").value = preferencias.emailAutomatizado.ignorar;
			document.getElementById("modulo6_ignorar").removeAttribute('disabled');
			document.getElementById("modulo6_ignorar").parentElement.style.opacity = '1';
		} else {
			document.getElementById("modulo6_ignorar").value = '';
			document.getElementById("modulo6_ignorar").setAttribute('disabled',true);
			document.getElementById("modulo6_ignorar").parentElement.style.opacity = '.5';
		}

		document.getElementById("modulo6_destinatario").addEventListener('click', () => {
			preferencias.emailAutomatizado.destinatario = document.getElementById("modulo6_destinatario").checked;
			if (document.getElementById("modulo6_destinatario").checked) {
				document.getElementById("modulo6_ignorar").value = preferencias.emailAutomatizado.ignorar;
				document.getElementById("modulo6_ignorar").removeAttribute('disabled');
				document.getElementById("modulo6_ignorar").parentElement.style.opacity = '1';
			} else {
				document.getElementById("modulo6_ignorar").value = '';
				document.getElementById("modulo6_ignorar").setAttribute('disabled',true);
				document.getElementById("modulo6_ignorar").parentElement.style.opacity = '.5';
			}
			salvarOpcoes();
		});
		document.getElementById("salvarConfig").addEventListener('click', salvarConfig);
		document.getElementById("recuperarConfig").addEventListener('click', recuperarConfig);

		listaModulo2_temp = preferencias.modulo2;
		if (preferencias.tarefaResponsavel != "" || preferencias.prazoResponsavel != "" || preferencias.atividadeResponsavel != "") {
			converter_lista_de_atividades_em_modulo2();
		}
		montar_modulo2();
		document.getElementById("modulo2_criarRegra").addEventListener('click', filtro_Atividades);
		document.getElementById("importar_modulo2").addEventListener('click', importarModulo2);
		document.getElementById("exportar_modulo2").addEventListener('click', exportarModulo2);


		document.querySelector('span[name="par"]').addEventListener('click', salvarOpcoes);
		document.querySelector('span[name="impar"]').addEventListener('click', salvarOpcoes);
		document.querySelector('span[name="todos"]').addEventListener('click', salvarOpcoes);
		document.querySelector('span[name="nenhum"]').addEventListener('click', salvarOpcoes);


		document.querySelector('#modulo8_ignorarZero').checked = preferencias.modulo8_ignorarZero;
		document.querySelector('#modulo8_ignorarZero').addEventListener('click', function () {
			preferencias.modulo8_ignorarZero = document.querySelector('#modulo8_ignorarZero').checked;
			let var1 = browser.storage.local.set({'modulo8_ignorarZero': preferencias.modulo8_ignorarZero});
			Promise.all([var1]).then(values => {
				document.getElementById("overlay").style.display = "flex";
				let Toast = Swal.mixin({
					toast: true,
					position: 'center',
					showConfirmButton: false,
					timer: 1000,
					timerProgressBar: false,
					onOpen: (toast) => {
						setTimeout(function() {
							document.getElementById("overlay").style.display = "none";
						}, 1000)
					}
				})

				Toast.fire({
					icon: 'success',
					title: 'Salvando...'
				})
			});
		});
		listaModulo8_temp = preferencias.modulo8;
		if (listaModulo8_temp.length > 0) {
			await converter_lista_de_magistrados_em_modulo8();
			montar_modulo8();
		}


		document.getElementById("modulo8_criarRegra").addEventListener('click', filtro_Magistrado);
		document.getElementById("convenio_sisbajud").style.backgroundColor = (preferencias.modulo9.sisbajud) ? '#2196F3' : '#b0b0b0';
		document.getElementById("convenio_sisbajud").addEventListener('click', function(event) {modulo9('sisbajud')});
		document.getElementById("convenio_renajud").style.backgroundColor = (preferencias.modulo9.renajud) ? '#2196F3' : '#b0b0b0';
		document.getElementById("convenio_renajud").addEventListener('click', function(event) {modulo9('renajud')});
		document.getElementById("convenio_cnib").style.backgroundColor = (preferencias.modulo9.cnib) ? '#2196F3' : '#b0b0b0';
		document.getElementById("convenio_cnib").addEventListener('click', function(event) {modulo9('cnib')});
		document.getElementById("convenio_serasajud").style.backgroundColor = (preferencias.modulo9.serasajud) ? '#2196F3' : '#b0b0b0';
		document.getElementById("convenio_serasajud").addEventListener('click', function(event) {modulo9('serasajud')});
		document.getElementById("convenio_ccs").style.backgroundColor = (preferencias.modulo9.ccs) ? '#2196F3' : '#b0b0b0';
		document.getElementById("convenio_ccs").addEventListener('click', function(event) {modulo9('ccs')});
		document.getElementById("convenio_crcjud").style.backgroundColor = (preferencias.modulo9.crcjud) ? '#2196F3' : '#b0b0b0';
		document.getElementById("convenio_crcjud").addEventListener('click', function(event) {modulo9('crcjud')});
		document.getElementById("convenio_onr").style.backgroundColor = (preferencias.modulo9.onr) ? '#2196F3' : '#b0b0b0';
		document.getElementById("convenio_onr").addEventListener('click', function(event) {modulo9('onr')});
		document.getElementById("convenio_gprec").style.backgroundColor = (preferencias.modulo9.gprec) ? '#2196F3' : '#b0b0b0';
		document.getElementById("convenio_gprec").addEventListener('click', function(event) {modulo9('gprec')});
		document.getElementById("convenio_ajjt").style.backgroundColor = (preferencias.modulo9.ajjt) ? '#2196F3' : '#b0b0b0';
		document.getElementById("convenio_ajjt").addEventListener('click', function(event) {modulo9('ajjt')});
		document.getElementById("convenio_siscondj").style.backgroundColor = (preferencias.modulo9.siscondj) ? '#2196F3' : '#b0b0b0';
		document.getElementById("convenio_siscondj").addEventListener('click', function(event) {modulo9('siscondj')});
		document.getElementById("convenio_garimpo").style.backgroundColor = (preferencias.modulo9.garimpo) ? '#2196F3' : '#b0b0b0';
		document.getElementById("convenio_garimpo").addEventListener('click', function(event) {modulo9('garimpo')});
		document.getElementById("convenio_sif").style.backgroundColor = (preferencias.modulo9.sif) ? '#2196F3' : '#b0b0b0';
		document.getElementById("convenio_sif").addEventListener('click', function(event) {modulo9('sif')});
		document.getElementById("convenio_pjecalc").style.backgroundColor = (preferencias.modulo9.pjecalc) ? '#2196F3' : '#b0b0b0';
		document.getElementById("convenio_pjecalc").addEventListener('click', function(event) {modulo9('pjecalc')});
		document.getElementById("convenio_prevjud").style.backgroundColor = (preferencias.modulo9.prevjud) ? '#2196F3' : '#b0b0b0';
		document.getElementById("convenio_prevjud").addEventListener('click', function(event) {modulo9('prevjud')});
		document.getElementById("convenio_protestojud").style.backgroundColor = (preferencias.modulo9.protestojud) ? '#2196F3' : '#b0b0b0';
		document.getElementById("convenio_protestojud").addEventListener('click', function(event) {modulo9('protestojud')});
		document.getElementById("convenio_sniper").style.backgroundColor = (preferencias.modulo9.sniper) ? '#2196F3' : '#b0b0b0';
		document.getElementById("convenio_sniper").addEventListener('click', function(event) {modulo9('sniper')});
		document.getElementById("convenio_censec").style.backgroundColor = (preferencias.modulo9.censec) ? '#2196F3' : '#b0b0b0';
		document.getElementById("convenio_censec").addEventListener('click', function(event) {modulo9('censec')});
		document.getElementById("convenio_celesc").style.backgroundColor = (preferencias.modulo9.celesc) ? '#2196F3' : '#b0b0b0';
		document.getElementById("convenio_celesc").addEventListener('click', function(event) {modulo9('celesc')});
		document.getElementById("convenio_casan").style.backgroundColor = (preferencias.modulo9.casan) ? '#2196F3' : '#b0b0b0';
		document.getElementById("convenio_casan").addEventListener('click', function(event) {modulo9('casan')});
		document.getElementById("convenio_sigef").style.backgroundColor = (preferencias.modulo9.sigef) ? '#2196F3' : '#b0b0b0';
		document.getElementById("convenio_sigef").addEventListener('click', function(event) {modulo9('sigef')});
		document.getElementById("convenio_infoseg").style.backgroundColor = (preferencias.modulo9.infoseg) ? '#2196F3' : '#b0b0b0';
		document.getElementById("convenio_infoseg").addEventListener('click', function(event) {modulo9('infoseg')});
		document.getElementById("convenio_ecarta").style.backgroundColor = (preferencias.modulo9.ecarta) ? '#2196F3' : '#b0b0b0';
		document.getElementById("convenio_ecarta").addEventListener('click', function(event) {modulo9('ecarta')});
		document.getElementById("convenio_saj").style.backgroundColor = (preferencias.modulo9.ecarta) ? '#2196F3' : '#b0b0b0';
		document.getElementById("convenio_saj").addEventListener('click', function(event) {modulo9('saj')});


		listaModulo10_temp = preferencias.modulo10;
		await montar_modulo10();

		//modulo10_juntadaMidia
		if (preferencias.modulo10_juntadaMidia[0]) {
			document.querySelector('#modulo10_juntadaMidia').checked = true;
			document.getElementById("modulo10_juntadaMidia").innerText = preferencias.modulo10_juntadaMidia[1] != "" ? 'Ativar Ação Automatizada para anexar depoimentos : ' + preferencias.modulo10_juntadaMidia[1] : "Ativar Ação Automatizada para anexar depoimentos";
		}
		document.querySelector('#modulo10_juntadaMidia').addEventListener('click', ativarJuntadaDeMidia);

		//modulo10_painelCopiaeCola
		document.querySelector('#modulo10_painelCopiaeCola').checked = preferencias.modulo10_painelCopiaeCola;
		document.querySelector('#modulo10_painelCopiaeCola').addEventListener('click', function () {
			preferencias.modulo10_painelCopiaeCola = document.querySelector('#modulo10_painelCopiaeCola').checked;
			let var1 = browser.storage.local.set({'modulo10_painelCopiaeCola': preferencias.modulo10_painelCopiaeCola});
			Promise.all([var1]).then(values => {
				document.getElementById("overlay").style.display = "flex";
				let Toast = Swal.mixin({
					toast: true,
					position: 'center',
					showConfirmButton: false,
					timer: 1000,
					timerProgressBar: false,
					onOpen: (toast) => {
						setTimeout(function() {
							document.getElementById("overlay").style.display = "none";
						}, 1000)
					}
				})

				Toast.fire({
					icon: 'success',
					title: 'Salvando...'
				})
			});
		});

		listaModulo11_temp = preferencias.modulo11;
		montar_modulo11();
		document.getElementById("modulo11_criarRegra").addEventListener('click', criarRegra_modulo11);

		//modulo11_AssinarAutomaticamente
		document.querySelector('#modulo11_AssinarAutomaticamente').checked = preferencias.modulo11_AssinarAutomaticamente;
		document.querySelector('#modulo11_AssinarAutomaticamente').addEventListener('click', function () {
			preferencias.modulo11_AssinarAutomaticamente = document.querySelector('#modulo11_AssinarAutomaticamente').checked;
			let var1 = browser.storage.local.set({'modulo11_AssinarAutomaticamente': preferencias.modulo11_AssinarAutomaticamente});
			Promise.all([var1]).then(values => {
				document.getElementById("overlay").style.display = "flex";
				let Toast = Swal.mixin({
					toast: true,
					position: 'center',
					showConfirmButton: false,
					timer: 1000,
					timerProgressBar: false,
					onOpen: (toast) => {
						setTimeout(function() {
							document.getElementById("overlay").style.display = "none";
						}, 1000)
					}
				})

				Toast.fire({
					icon: 'success',
					title: 'Salvando...'
				})
			});
		});

		function preencherCampoDasPreferencias(id, valor, acaoSalvar = salvarOpcoes) {
			/** @type {HTMLInputElement} */
			const campo = document.querySelector(id);
			if (!campo) return;

			if (campo.type === 'checkbox') {
				campo.checked = !!valor;
				campo.addEventListener('click', acaoSalvar);
			} else {
				campo.value = valor;
				campo.addEventListener('focusout', acaoSalvar);
			}
		}
		preencherCampoDasPreferencias('#pesquisaRapidaDeProcessoEmAba', preferencias.pesquisaRapidaDeProcessoEmAba);
		preencherCampoDasPreferencias('#acionarKaizenComClique', preferencias.acionarKaizenComClique);
		preencherCampoDasPreferencias('#kaizenNaHorizontal', preferencias.kaizenNaHorizontal);

		document.querySelector('#zerarPosicoesKaizen').addEventListener('click', zerarPosicoesKaizen);
		preencherCampoDasPreferencias('#fecharJanelaExpediente', preferencias.extrasFecharJanelaExpediente);
		preencherCampoDasPreferencias('#extrasSugerirDescricaoAoAnexar', preferencias.extrasSugerirDescricaoAoAnexar);
		preencherCampoDasPreferencias('#extrasSugerirTipoAoAnexar', preferencias.extrasSugerirTipoAoAnexar);

		preencherCampoDasPreferencias('#modulo10_salaFavorita', preferencias.modulo10_salaFavorita);

		//e-Rec
		preencherCampoDasPreferencias('#extrasTiposDocumentoProcuracao', preferencias.extrasTiposDocumentoProcuracao);
		preencherCampoDasPreferencias('#extrasTiposDocumentoCustas', preferencias.extrasTiposDocumentoCustas);
		preencherCampoDasPreferencias('#extrasTiposDocumentoDepositoRecursal', preferencias.extrasTiposDocumentoDepositoRecursal);
		preencherCampoDasPreferencias('#extrasTiposDocumentoSentencasAcordao', preferencias.extrasTiposDocumentoSentencasAcordao);

		preencherCampoDasPreferencias('#extrasExibirPreviaDocumentoMouseOver', preferencias.extrasExibirPreviaDocumentoMouseOver);
		preencherCampoDasPreferencias('#extrasExibirPreviaDocumentoFocus', preferencias.extrasExibirPreviaDocumentoFocus);
		preencherCampoDasPreferencias('#extrasERecTipoGigsSemTema', preferencias.extrasERecTipoGigsSemTema);

        preencherCampoDasPreferencias('#extrasFocusSempre', preferencias.extrasFocusSempre);

		preencherCampoDasPreferencias('#elPzoEmLote0', preferencias.extrasPrazoEmLote[0]);
		preencherCampoDasPreferencias('#elPzoEmLote1', preferencias.extrasPrazoEmLote[1]);
		preencherCampoDasPreferencias('#elPzoEmLote2', preferencias.extrasPrazoEmLote[2]);
		preencherCampoDasPreferencias('#elPzoEmLote3', preferencias.extrasPrazoEmLote[3]);
		preencherCampoDasPreferencias('#elPzoEmLote4', preferencias.extrasPrazoEmLote[4]);
		preencherCampoDasPreferencias('#elPzoEmLote5', preferencias.extrasPrazoEmLote[5]);
		preencherCampoDasPreferencias('#atalho_painelcopiaecola', preferencias?.atalho?.painelcopiaecola);


		document.querySelector('#ProcurarExecucaoSAO').checked = (preferencias.extrasProcurarExecucao.includes('SAO')) ? true : false;
		document.querySelector('#ProcurarExecucaoSAO').addEventListener('click', function() {

			if (document.querySelector('#ProcurarExecucaoSAO').checked) {
				preferencias.extrasProcurarExecucao = 'SAO';
				document.querySelector('#ProcurarExecucaoLocal').checked = false;
				salvarOpcoes();
			} else {
				document.querySelector('#ProcurarExecucaoSAO').checked = true;
			}

		});
		document.querySelector('#ProcurarExecucaoLocal').checked = (preferencias.extrasProcurarExecucao.includes('Local')) ? true : false;
		document.querySelector('#ProcurarExecucaoLocal').addEventListener('click', function() {

			if (document.querySelector('#ProcurarExecucaoLocal').checked) {
				preferencias.extrasProcurarExecucao = 'Local';
				document.querySelector('#ProcurarExecucaoSAO').checked = false;
				salvarOpcoes();
			} else {
				document.querySelector('#ProcurarExecucaoLocal').checked = true;
			}

		});


		if (mapeadosAADescendentes || restaurar) {
			await salvarOpcoes();
		}

		const novidades = await carregarNovidades();
		montarNovidades(preferencias.videoAtualizacao, novidades);

		resolve(true);
	});
}

async function salvarOpcoes() {
	return new Promise(async resolve => {
		console.log("salvando...");
		document.getElementById("overlay").style.display = "flex";

		let monitorDetalhes, monitorTarefas, monitorGigs
		let tarefaLeft, tarefaTop, tarefaWidth, tarefaHeight, detalhesLeft, detalhesTop, detalhesWidth, detalhesHeight, gigsLeft, gigsTop, gigsWidth, gigsHeight;
		if (!preferencias.desativarAjusteJanelas) {
			monitorDetalhes = document.querySelector('input[name="gigsMonitorDetalhes"]:checked')?.value;
			monitorTarefas = document.querySelector('input[name="gigsMonitorTarefas"]:checked')?.value;
			monitorGigs = document.querySelector('input[name="gigsMonitorGigs"]:checked')?.value;

			monitorTarefas = (!monitorTarefas) ? '0' : monitorTarefas;
			tarefaLeft = monitores[monitorTarefas].left;
			tarefaTop = monitores[monitorTarefas].top;
			tarefaWidth = monitores[monitorTarefas].width;
			tarefaHeight = monitores[monitorTarefas].height;

			monitorDetalhes = (!monitorDetalhes) ? '0' : monitorDetalhes
			detalhesLeft = monitores[monitorDetalhes].left;
			detalhesTop = monitores[monitorDetalhes].top;
			detalhesWidth = monitores[monitorDetalhes].width;
			detalhesHeight = monitores[monitorDetalhes].height;

			monitorGigs = (!monitorGigs) ? '0' : monitorGigs
			gigsLeft = monitores[monitorGigs].left;
			gigsTop = monitores[monitorGigs].top;
			gigsWidth = monitores[monitorGigs].width;
			gigsHeight = monitores[monitorGigs].height;
		}

		let listaProcessos = [];

		listaProcessos[0] = document.querySelector('#meuFiltro0').checked;
		listaProcessos[1] = document.querySelector('#meuFiltro1').checked;
		listaProcessos[2] = document.querySelector('#meuFiltro2').checked;
		listaProcessos[3] = document.querySelector('#meuFiltro3').checked;
		listaProcessos[4] = document.querySelector('#meuFiltro4').checked;
		listaProcessos[5] = document.querySelector('#meuFiltro5').checked;
		listaProcessos[6] = document.querySelector('#meuFiltro6').checked;
		listaProcessos[7] = document.querySelector('#meuFiltro7').checked;
		listaProcessos[8] = document.querySelector('#meuFiltro8').checked;
		listaProcessos[9] = document.querySelector('#meuFiltro9').checked;
		listaProcessos[10] = document.querySelector('#meuFiltroJT').checked;
		listaProcessos[11] = document.querySelector('#meuFiltroJS').checked;

		let listaAtalhoDetalhes = [];
		listaAtalhoDetalhes[0] = document.getElementById('c0').checked;
		listaAtalhoDetalhes[1] = document.getElementById('c1').checked;
		listaAtalhoDetalhes[2] = document.getElementById('c2').checked;
		listaAtalhoDetalhes[3] = document.getElementById('c3').checked;
		listaAtalhoDetalhes[4] = document.getElementById('c4').checked;
		listaAtalhoDetalhes[5] = document.getElementById('c5').checked;
		listaAtalhoDetalhes[6] = document.getElementById('c6').checked;
		listaAtalhoDetalhes[7] = document.getElementById('c7').checked;
		listaAtalhoDetalhes[8] = document.getElementById('c8').checked;
		listaAtalhoDetalhes[9] = document.getElementById('c9').checked;
		listaAtalhoDetalhes[10] = document.getElementById('c10').checked;
		listaAtalhoDetalhes[11] = document.getElementById('c11').checked;
		listaAtalhoDetalhes[12] = document.getElementById('c12').checked;
		listaAtalhoDetalhes[13] = document.getElementById('c13').checked;
		listaAtalhoDetalhes[14] = document.getElementById('c14').checked;
		listaAtalhoDetalhes[15] = document.getElementById('c15').checked;
		listaAtalhoDetalhes[16] = document.getElementById('c16').checked;
		listaAtalhoDetalhes[17] = document.getElementById('c17').checked;
		listaAtalhoDetalhes[18] = document.getElementById('c18').checked;
		listaAtalhoDetalhes[19] = document.getElementById('c19').checked;
		listaAtalhoDetalhes[20] = document.getElementById('c20').checked;
		listaAtalhoDetalhes[21] = document.getElementById('c21').checked;
		listaAtalhoDetalhes[22] = document.getElementById('c22').checked;
		listaAtalhoDetalhes[23] = document.getElementById('c23').checked;
		listaAtalhoDetalhes[24] = document.getElementById('c24').checked;
		listaAtalhoDetalhes[25] = document.getElementById('c25').checked;
		listaAtalhoDetalhes[26] = document.getElementById('c26').checked; //PDPJ
		listaAtalhoDetalhes[27] = document.getElementById('c27').checked;
		listaAtalhoDetalhes[28] = document.getElementById('c28').checked;
		listaAtalhoDetalhes[29] = document.getElementById('c29').checked; //wiki vt
		listaAtalhoDetalhes[30] = document.getElementById('c30').checked; //Domicilio Eletronico
		listaAtalhoDetalhes[31] = document.getElementById('c31').checked; //EXIBIR TODOS

		aa_eliminarUndefined();

		//modulo 10
		listaModulo10_temp = [];
		for (const [pos, item] of document.querySelectorAll('tr[id="lista_modulo10_item"]').entries()) {
			let h = item.querySelector('input[id="horario"]').value;
			let s = item.querySelector('input[id="sala"]').value;
			let u = item.querySelector('input[id="url"]').value;
			if (h || u || s) {
				listaModulo10_temp.push({horario:h,sala:s,url:u});
			}
		}

		const valoresModulo1 = mergeItensMenu(itensModulo1SemAtalhos);

		preferencias.extrasPrazoEmLote[0] = document.getElementById("elPzoEmLote0").value;
		preferencias.extrasPrazoEmLote[1] = document.getElementById("elPzoEmLote1").value;
		preferencias.extrasPrazoEmLote[2] = document.getElementById("elPzoEmLote2").value;
		preferencias.extrasPrazoEmLote[3] = document.getElementById("elPzoEmLote3").value;
		preferencias.extrasPrazoEmLote[4] = document.getElementById("elPzoEmLote4").value;
		preferencias.extrasPrazoEmLote[5] = document.getElementById("elPzoEmLote5").value;

		preferencias.atalho.painelcopiaecola = document.getElementById("atalho_painelcopiaecola").value;

		await browser.storage.local.set({
			versao: browser.runtime.getManifest().version,
			...valoresModulo1,
			gigsMonitorDetalhes: monitorDetalhes,
			gigsMonitorTarefas: monitorTarefas,
			gigsMonitorGigs: monitorGigs,
			gigsDetalhesLeft: detalhesLeft,
			gigsDetalhesTop: detalhesTop,
			gigsDetalhesWidth: detalhesWidth,
			gigsDetalhesHeight: detalhesHeight,
			gigsTarefaLeft: tarefaLeft,
			gigsTarefaTop: tarefaTop,
			gigsTarefaWidth: tarefaWidth,
			gigsTarefaHeight: tarefaHeight,
			gigsGigsLeft: gigsLeft,
			gigsGigsTop: gigsTop,
			gigsGigsWidth: gigsWidth,
			gigsGigsHeight: gigsHeight,
			atalhosDetalhes : listaAtalhoDetalhes,
			meuFiltro : listaProcessos,
			filtros_Favoritos: filtros_storage,
			modulo5_obterSaldoSIF: document.querySelector('#modulo5_filtros_favoritos_ObterSaldoSIf').checked,
			modulo5_conferirTeimosinhaEmLote: document.querySelector('#modulo5_filtros_favoritos_conferirTeimosinhaEmLote').checked,
			modulo5_juizDaMinuta: document.querySelector('#modulo5_filtros_favoritos_juizDaMinuta').checked,
			modulo5_processosSemAudienciaDesignada: document.querySelector('#modulo5_filtros_favoritos_semAudienciaDesignada').checked,
			modulo5_processosSemGigsCadastrado: document.querySelector('#modulo5_filtros_favoritos_semGIGS').checked,
			modulo5_processosParadosHaMaisDeXXDias: document.querySelector('#modulo5_filtros_favoritos_paradosXXdias').checked,
			modulo5_conferirGarimpoEmLote: document.querySelector('#modulo5_conferirGarimpoEmLote').checked,
			modulo5_obterConcilia: document.querySelector('#modulo5_filtros_favoritos_conciliaJT').checked,
			maisPje_velocidade_interacao: preferencias.maisPje_velocidade_interacao,
			aaAnexar : aaAnexar_temp,
			aaComunicacao : aaComunicacao_temp,
			aaAutogigs : aaAutogigs_temp,
			aaDespacho : aaDespacho_temp,
			aaMovimento : aaMovimento_temp,
			aaChecklist : aaChecklist_temp,
			aaNomearPerito : aaNomearPerito_temp,
			aaLancarMovimentos : preferencias.aaLancarMovimentos,
			aaVariados : aaVariados_temp,
			atalhosPlugin : montarAtalhosPlugin(),
			emailAutomatizado : preferencias.emailAutomatizado,
			videoAtualizacao: true,
			modulo8: listaModulo8_temp,
			modulo9: preferencias.modulo9,
			modulo2: listaModulo2_temp,
			sisbajud: preferencias.sisbajud,
			renajud: preferencias.renajud,
			serasajud: preferencias.serasajud,
			modulo10: listaModulo10_temp,
			modulo11: listaModulo11_temp,
			lista_monitores: monitores,
			modoLGPD: preferencias.modoLGPD,
			modoNoite: preferencias.modoNoite,
			menu_kaizen: preferencias.menu_kaizen,
			pesquisaRapidaDeProcessoEmAba: document.querySelector('#pesquisaRapidaDeProcessoEmAba').checked,
			acionarKaizenComClique: document.querySelector('#acionarKaizenComClique').checked,
			kaizenNaHorizontal: document.querySelector('#kaizenNaHorizontal').checked,
			extrasTiposDocumentoProcuracao: /** @type {HTMLInputElement} */ (document.querySelector('#extrasTiposDocumentoProcuracao'))?.value,
			modulo10_salaFavorita: /** @type {HTMLInputElement} */ (document.querySelector('#modulo10_salaFavorita'))?.value,
			extrasTiposDocumentoCustas: document.querySelector('#extrasTiposDocumentoCustas')?.value,
			extrasTiposDocumentoDepositoRecursal: document.querySelector('#extrasTiposDocumentoDepositoRecursal')?.value,
			extrasTiposDocumentoSentencasAcordao: document.querySelector('#extrasTiposDocumentoSentencasAcordao')?.value,
			extrasExibirPreviaDocumentoMouseOver: document.querySelector('#extrasExibirPreviaDocumentoMouseOver')?.checked,
			extrasExibirPreviaDocumentoFocus: document.querySelector('#extrasExibirPreviaDocumentoFocus').checked,
			extrasFocusSempre: document.querySelector('#extrasFocusSempre').checked,

			extrasERecTipoGigsSemTema: document.querySelector('#extrasERecTipoGigsSemTema')?.value,
			extrasFecharJanelaExpediente: document.querySelector('#fecharJanelaExpediente').checked,
			extrasSugerirTipoAoAnexar: document.querySelector('#extrasSugerirTipoAoAnexar').checked,
			extrasSugerirDescricaoAoAnexar: document.querySelector('#extrasSugerirDescricaoAoAnexar').checked,
			extrasProcurarExecucao: preferencias.extrasProcurarExecucao,
			extrasPrazoEmLote: preferencias.extrasPrazoEmLote,
			modulo4PaginaInicial: document.getElementById("modulo4PaginaInicial").value,
			atalho: preferencias.atalho
		});

		const Toast = Swal.mixin({
			toast: true,
			position: 'center',
			showConfirmButton: false,
			timer: 1000,
			timerProgressBar: false,
			onOpen: (toast) => {
				setTimeout(function() {
					document.getElementById("overlay").style.display = "none";

					let recarregarStorage = browser.storage.local.get(null);
					Promise.all([recarregarStorage]).then(result => {
						preferencias = result[0];
						resolve(true);
					});

				}, 1000)
			}
		})

		Toast.fire({
			icon: 'success',
			title: 'Salvando...'
		})

		// browser.runtime.sendMessage({tipo: 'criarAlerta', valor: '\n Informações salvas com sucesso!', icone: '2'});


	});
}

function meuFiltroDesmarcar() {
	document.querySelector('#meuFiltroJT').checked = false;
	document.querySelector('#meuFiltroJS').checked = false;
	salvarOpcoes();
}

async function zerarPosicoesKaizen() {
	preferencias.menu_kaizen = {principal:{posx:'96%',posy:'92%'},detalhes:{posx:'96%',posy:'92%'},tarefas:{posx:'96%',posy:'92%'},sisbajud:{posx:'93%',posy:'80%'},serasajud:{posx:'93%',posy:'80%'},renajud:{posx:'93%',posy:'80%'},cnib:{posx:'93%',posy:'80%'},ccs:{posx:'93%',posy:'80%'}};
	salvarOpcoes();
}

function ajustarAAVariados() {
	return new Promise(async resolve => {
		let listaDeIds = preferencias.aaVariados.map((item) => item.id);//pega os ids das AA que eu já tenho

		for (const [pos, obj] of aaVariados_temp.entries()) {
			// console.log(obj.id + ' == ' + listaDeIds.indexOf(obj.id) + '   : ' + pos)
			if (listaDeIds.includes(obj.id)) {
				obj.temporizador = preferencias.aaVariados[listaDeIds.indexOf(obj.id)].temporizador;
				obj.ativar = preferencias.aaVariados[listaDeIds.indexOf(obj.id)].ativar;
				if (obj.objeto) {
					obj.objeto = preferencias.aaVariados[listaDeIds.indexOf(obj.id)].objeto;
				}
			} else {
				preferencias.aaVariados.splice(pos,1,obj)
			}
		}
		// console.log(preferencias.aaVariados)
		// console.log(aaVariados_temp)

		preferencias.aaVariados = aaVariados_temp;
		aaVariados_temp = preferencias.aaVariados;
		await browser.storage.local.set({'aaVariados': preferencias.aaVariados});
		resolve(true);
	});
}

//módulo 2
async function converter_lista_de_atividades_em_modulo2() {
	let lista_temp = [];
	//GIGS PREPAROS - versão 2.6.5
	if (preferencias.tarefaResponsavel) {
		preferencias.atividadeResponsavel.concat(preferencias.tarefaResponsavel);
	}

	//GIGS PRAZOS - versão 2.6.5
	if (preferencias.prazoResponsavel) {
		preferencias.atividadeResponsavel.concat(preferencias.prazoResponsavel);;
	}

	//GIGS ATIVIDADES - versão 2.7.0
	if (preferencias.atividadeResponsavel) {
		lista_temp = preferencias.atividadeResponsavel.split('|');
	}
	// console.log(lista_temp);
	[].map.call(lista_temp,function(item) {
		let array1 = item.split(':');
		// console.log(item);
		if (array1.length < 2) {
			// console.log('      |___ignora');
		} else if (array1.length == 2) {
			//verifica se um dos dois itens são vazios
			if (array1[0] == "" || array1[1] == "") {
				// console.log('      |___ignora');
			} else {
				// console.log('      |___' + array1[0] + ' é número? ' + (isNaN(array1[0]) ? "Não" : "Sim"));
				if (isNaN(array1[0])) { //não é número?
					let linha = array1[0] + '|' + array1[1] + '|0|1|2|3|4|5|6|7|8|9';
					listaModulo2_temp.push(linha);
				} else {
					let linha = ' |' + array1[1] + '|' + array1[0];
					listaModulo2_temp.push(linha);
				}
			}
		} else if (array1.length > 2) {
			// console.log('      |___incluido no listaModulo2_temp: ' + '['+array1[0]+','+array1[1]+','+array1[2]+']');
			if (array1[2] == "par") {
				let linha = array1[0] + '|' + array1[1] + '|0|2|4|6|8';
				listaModulo2_temp.push(linha);
			} else if (array1[2] == "impar" || array1[2] == "ímpar") {
				let linha = array1[0] + '|' + array1[1] + '|1|3|5|7|9';
				listaModulo2_temp.push(linha);
			}
		}
	});
	// console.log(listaModulo2_temp);

	//exclui as antigas variáveis
	await browser.storage.local.remove('tarefaResponsavel');
	await browser.storage.local.remove('prazoResponsavel');
	await browser.storage.local.remove('atividadeResponsavel');
}

async function filtro_Atividades() {
	const { value: result } = await Swal.fire({
		title: '    ',
		html:
			'<span>Nome da atividade:</span><br>' +
			'<input type="text" id="modulo2_atividade" class="swal2-input" placeholder="Nome da atividade">' +
			'<span>Nome do usuario responsavel:</span><br>' +
			'<input type="text" id="modulo2_usuario_responsavel" class="swal2-input" placeholder="Nome do usuário responsavel">' +
			'<span>Fase do Processo:</span><br>' +
			'<select id="modulo2_fase_processo" class="swal2-select" placeholder="Fase do Processo">' +
			'<option value="Todas" selected>Todas</option>' +
			'<option value="Conhecimento">Conhecimento</option>' +
			'<option value="Liquidação">Liquidação</option>' +
			'<option value="Execução">Execução</option>' +
			'<option value="Arquivados">Arquivados</option>' +
			'</select><br><br>' +
			'<div id="escolherProcessoFinal"><span>Processo final:</span><br><br>' +
			'<label class="container">' +
			'<input type="checkbox" id="modulo2_Filtro0" checked><span style="position: relative; padding-right: 15px; top: 2px; margin-left: -10px; font-size: 24px;">0</span>' +
			'<span class="checkmark"></span>' +
			'</label>' +
			'<label class="container">' +
			'<input type="checkbox" id="modulo2_Filtro1" checked><span style="position: relative; padding-right: 15px; top: 2px; margin-left: -10px; font-size: 24px;">1</span>' +
			'<span class="checkmark"></span>' +
			'</label>' +
			'<label class="container">' +
			'<input type="checkbox" id="modulo2_Filtro2" checked><span style="position: relative; padding-right: 15px; top: 2px; margin-left: -10px; font-size: 24px;">2</span>' +
			'<span class="checkmark"></span>' +
			'</label>' +
			'<label class="container">' +
			'<input type="checkbox" id="modulo2_Filtro3" checked><span style="position: relative; padding-right: 15px; top: 2px; margin-left: -10px; font-size: 24px;">3</span>' +
			'<span class="checkmark"></span>' +
			'</label>' +
			'<label class="container">' +
			'<input type="checkbox" id="modulo2_Filtro4" checked><span style="position: relative; padding-right: 15px; top: 2px; margin-left: -10px; font-size: 24px;">4</span>' +
			'<span class="checkmark"></span>' +
			'</label><br>' +
			'<label class="container">' +
			'<input type="checkbox" id="modulo2_Filtro5" checked><span style="position: relative; padding-right: 15px; top: 2px; margin-left: -10px; font-size: 24px;">5</span>' +
			'<span class="checkmark"></span>' +
			'</label>' +
			'<label class="container">' +
			'<input type="checkbox" id="modulo2_Filtro6" checked><span style="position: relative; padding-right: 15px; top: 2px; margin-left: -10px; font-size: 24px;">6</span>' +
			'<span class="checkmark"></span>' +
			'</label>' +
			'<label class="container">' +
			'<input type="checkbox" id="modulo2_Filtro7" checked><span style="position: relative; padding-right: 15px; top: 2px; margin-left: -10px; font-size: 24px;">7</span>' +
			'<span class="checkmark"></span>' +
			'</label>' +
			'<label class="container">' +
			'<input type="checkbox" id="modulo2_Filtro8" checked><span style="position: relative; padding-right: 15px; top: 2px; margin-left: -10px; font-size: 24px;">8</span>' +
			'<span class="checkmark"></span>' +
			'</label>' +
			'<label class="container">' +
			'<input type="checkbox" id="modulo2_Filtro9" checked><span style="position: relative; padding-right: 15px; top: 2px; margin-left: -10px; font-size: 24px;">9</span>' +
			'<span class="checkmark"></span>' +
			'</label>' +
			'<br><br><div style="display: grid; grid-template-columns: 1fr 1fr 1fr 1fr; gap: 1em; cursor: pointer;">' +
			'<span id="maisPje_parEimpar" name="par" class="swal2-label spanToogle">Par</span>' +
			'<span id="maisPje_parEimpar" name="impar"class="swal2-label spanToogle">Ímpar</span>' +
			'<span id="maisPje_parEimpar" name="todos" class="swal2-label spanToogle">Todos</span>' +
			'<span id="maisPje_parEimpar" name="nenhum" class="swal2-label spanToogle">Nenhum</span>' +
			'</div><br><br></div>',
		showCancelButton: true,
		focusConfirm: false,
		confirmButtonText: 'Salvar',
		cancelButtonText: 'Cancelar',
		preConfirm: () => {
			let resposta = (document.getElementById('modulo2_atividade').value == "") ? " " : document.getElementById('modulo2_atividade').value;
			resposta += "|" + document.getElementById('modulo2_usuario_responsavel').value;
			resposta += "|" + document.getElementById('modulo2_fase_processo').value;
			if (document.getElementById('modulo2_Filtro0').checked) {
				resposta += "|" + 0;
			}
			if (document.getElementById('modulo2_Filtro1').checked) {
				resposta += "|" + 1;
			}
			if (document.getElementById('modulo2_Filtro2').checked) {
				resposta += "|" + 2;
			}
			if (document.getElementById('modulo2_Filtro3').checked) {
				resposta += "|" + 3;
			}
			if (document.getElementById('modulo2_Filtro4').checked) {
				resposta += "|" + 4;
			}
			if (document.getElementById('modulo2_Filtro5').checked) {
				resposta += "|" + 5;
			}
			if (document.getElementById('modulo2_Filtro6').checked) {
				resposta += "|" + 6;
			}
			if (document.getElementById('modulo2_Filtro7').checked) {
				resposta += "|" + 7;
			}
			if (document.getElementById('modulo2_Filtro8').checked) {
				resposta += "|" + 8;
			}
			if (document.getElementById('modulo2_Filtro9').checked) {
				resposta += "|" + 9;
			}
			return resposta;
		}
	});

	if (result) {
		listaModulo2_temp.push(result);
		preferencias.modulo2 = listaModulo2_temp;
		montar_modulo2();
		salvarOpcoes();
	}
}

async function editar_filtro_Atividades(pos) {
	let item = listaModulo2_temp[pos].split('|');
	const { value: result } = await Swal.fire({
		title: '    ',
		html:
			'<span>Nome da atividade:</span><br>' +
			'<input type="text" id="modulo2_atividade" class="swal2-input" placeholder="Nome da atividade" value="' + item[0] + '">' +
			'<span>Nome do usuario responsavel:</span><br>' +
			'<input type="text" id="modulo2_usuario_responsavel" class="swal2-input" placeholder="Nome do usuario responsavel" value="' + item[1] + '">' +
			'<span>Fase do Processo:</span><br>' +
			'<select id="modulo2_fase_processo" class="swal2-select" placeholder="Fase do Processo">' +
			'<option value="Todas" ' + (item[2].includes('Todas') ? 'selected' : '') + '>Todas</option>' +
			'<option value="Conhecimento" ' + (item[2].includes('Conhecimento') ? 'selected' : '') + '>Conhecimento</option>' +
			'<option value="Liquidação" ' + (item[2].includes('Liquidação') ? 'selected' : '') + '>Liquidação</option>' +
			'<option value="Execução" ' + (item[2].includes('Execução') ? 'selected' : '') + '>Execução</option>' +
			'<option value="Arquivados" ' + (item[2].includes('Arquivados') ? 'selected' : '') + '>Arquivados</option>' +
			'</select><br><br>' +
			'<div id="escolherProcessoFinal"><span>Processo final:</span><br><br>' +
			'<label class="container">' +
			'<input type="checkbox" id="modulo2_Filtro0" ' + (item.includes('0') ? 'checked' : '') + '><span style="position: relative; padding-right: 15px; top: 2px; margin-left: -10px; font-size: 24px;">0</span>' +
			'<span class="checkmark"></span>' +
			'</label>' +
			'<label class="container">' +
			'<input type="checkbox" id="modulo2_Filtro1" ' + (item.includes('1') ? 'checked' : '') + '><span style="position: relative; padding-right: 15px; top: 2px; margin-left: -10px; font-size: 24px;">1</span>' +
			'<span class="checkmark"></span>' +
			'</label>' +
			'<label class="container">' +
			'<input type="checkbox" id="modulo2_Filtro2" ' + (item.includes('2') ? 'checked' : '') + '><span style="position: relative; padding-right: 15px; top: 2px; margin-left: -10px; font-size: 24px;">2</span>' +
			'<span class="checkmark"></span>' +
			'</label>' +
			'<label class="container">' +
			'<input type="checkbox" id="modulo2_Filtro3" ' + (item.includes('3') ? 'checked' : '') + '><span style="position: relative; padding-right: 15px; top: 2px; margin-left: -10px; font-size: 24px;">3</span>' +
			'<span class="checkmark"></span>' +
			'</label>' +
			'<label class="container">' +
			'<input type="checkbox" id="modulo2_Filtro4" ' + (item.includes('4') ? 'checked' : '') + '><span style="position: relative; padding-right: 15px; top: 2px; margin-left: -10px; font-size: 24px;">4</span>' +
			'<span class="checkmark"></span>' +
			'</label><br>' +
			'<label class="container">' +
			'<input type="checkbox" id="modulo2_Filtro5" ' + (item.includes('5') ? 'checked' : '') + '><span style="position: relative; padding-right: 15px; top: 2px; margin-left: -10px; font-size: 24px;">5</span>' +
			'<span class="checkmark"></span>' +
			'</label>' +
			'<label class="container">' +
			'<input type="checkbox" id="modulo2_Filtro6" ' + (item.includes('6') ? 'checked' : '') + '><span style="position: relative; padding-right: 15px; top: 2px; margin-left: -10px; font-size: 24px;">6</span>' +
			'<span class="checkmark"></span>' +
			'</label>' +
			'<label class="container">' +
			'<input type="checkbox" id="modulo2_Filtro7" ' + (item.includes('7') ? 'checked' : '') + '><span style="position: relative; padding-right: 15px; top: 2px; margin-left: -10px; font-size: 24px;">7</span>' +
			'<span class="checkmark"></span>' +
			'</label>' +
			'<label class="container">' +
			'<input type="checkbox" id="modulo2_Filtro8" ' + (item.includes('8') ? 'checked' : '') + '><span style="position: relative; padding-right: 15px; top: 2px; margin-left: -10px; font-size: 24px;">8</span>' +
			'<span class="checkmark"></span>' +
			'</label>' +
			'<label class="container">' +
			'<input type="checkbox" id="modulo2_Filtro9" ' + (item.includes('9') ? 'checked' : '') + '><span style="position: relative; padding-right: 15px; top: 2px; margin-left: -10px; font-size: 24px;">9</span>' +
			'<span class="checkmark"></span>' +
			'</label>' +
			'<br><br><div style="display: grid; grid-template-columns: 1fr 1fr 1fr 1fr; gap: 1em; cursor: pointer;">' +
			'<span id="maisPje_parEimpar" name="par" class="swal2-label spanToogle">Par</span>' +
			'<span id="maisPje_parEimpar" name="impar"class="swal2-label spanToogle">Ímpar</span>' +
			'<span id="maisPje_parEimpar" name="todos" class="swal2-label spanToogle">Todos</span>' +
			'<span id="maisPje_parEimpar" name="nenhum" class="swal2-label spanToogle">Nenhum</span>' +
			'</div><br><br></div>',

		showCancelButton: true,
		focusConfirm: false,
		confirmButtonText: 'Salvar',
		cancelButtonText: 'Cancelar',
		preConfirm: () => {
			let resposta = (document.getElementById('modulo2_atividade').value == "") ? " " : document.getElementById('modulo2_atividade').value;
			resposta += "|" + document.getElementById('modulo2_usuario_responsavel').value;
			resposta += "|" + document.getElementById('modulo2_fase_processo').value;
			if (document.getElementById('modulo2_Filtro0').checked) {
				resposta += "|" + 0;
			}
			if (document.getElementById('modulo2_Filtro1').checked) {
				resposta += "|" + 1;
			}
			if (document.getElementById('modulo2_Filtro2').checked) {
				resposta += "|" + 2;
			}
			if (document.getElementById('modulo2_Filtro3').checked) {
				resposta += "|" + 3;
			}
			if (document.getElementById('modulo2_Filtro4').checked) {
				resposta += "|" + 4;
			}
			if (document.getElementById('modulo2_Filtro5').checked) {
				resposta += "|" + 5;
			}
			if (document.getElementById('modulo2_Filtro6').checked) {
				resposta += "|" + 6;
			}
			if (document.getElementById('modulo2_Filtro7').checked) {
				resposta += "|" + 7;
			}
			if (document.getElementById('modulo2_Filtro8').checked) {
				resposta += "|" + 8;
			}
			if (document.getElementById('modulo2_Filtro9').checked) {
				resposta += "|" + 9;
			}
			return resposta;
		}
	});

	if (result) {
		listaModulo2_temp[pos] = result;
		preferencias.modulo2 = listaModulo2_temp;
		montar_modulo2();
		salvarOpcoes();
	}
}

async function montar_modulo2() {
	listaModulo2_temp = await excluirRepetidos();
	let ancora = document.getElementById('lista_modulo2');
	ancora.textContent = ""; //limpa a tabela
	let tr_cabecalho = document.createElement("tr");
	tr_cabecalho.className = "textoItalico";
	let td_cabecalho_1 = document.createElement("td");
	td_cabecalho_1.innerText = 'TAREFA';
	let td_cabecalho_2 = document.createElement("td");
	td_cabecalho_2.innerText = 'RESPONSÁVEL';
	let td_cabecalho_3 = document.createElement("td");
	td_cabecalho_3.innerText = 'FASE';
	let td_cabecalho_4 = document.createElement("td");
	td_cabecalho_4.innerText = 'PROCESSO FINAL';
	let td_cabecalho_5 = document.createElement("td");



	//*********criar botão excluir
	let div_excluirTodos = document.createElement("div");
	div_excluirTodos.style = "display: grid;grid-template-columns: 1fr 1fr 1fr 1fr;font-style: normal;"
	div_excluirTodos.setAttribute("data-tooltip", "Excluir Todos");
	let bt_excluirTodos = document.createElement("i");
	bt_excluirTodos.className = "icone trash-alt t16";
	bt_excluirTodos.style = "padding: 0 5px 0 5px; background-color: darkcyan;"
	bt_excluirTodos.onmouseenter = function() {
		this.style.setProperty("background-color","orangered");
	}
	bt_excluirTodos.onmouseleave = function (e) {
		this.style.setProperty("background-color","darkcyan");
	};
	bt_excluirTodos.onclick = function () {

		Swal.fire({
			title: 'Tem certeza?',
			text: "",
			showCancelButton: true,
			confirmButtonColor: '#3085d6',
			cancelButtonColor: '#d33',
			confirmButtonText: 'Sim, excluir TODAS as regras do Módulo 2!',
			cancelButtonText: 'Não'
		}).then((result) => {
			if (result.value) {
				listaModulo2_temp = [];
				preferencias.modulo2 = listaModulo2_temp;
				montar_modulo2();
				salvarOpcoes();
			}
		})



	};
	div_excluirTodos.appendChild(document.createElement("span"));
	div_excluirTodos.appendChild(bt_excluirTodos);
	div_excluirTodos.appendChild(document.createElement("span"));
	div_excluirTodos.appendChild(document.createElement("span"));
	td_cabecalho_5.appendChild(div_excluirTodos);

	tr_cabecalho.appendChild(document.createElement("td"));
	tr_cabecalho.appendChild(td_cabecalho_1);
	tr_cabecalho.appendChild(document.createElement("td"));
	tr_cabecalho.appendChild(td_cabecalho_2);
	tr_cabecalho.appendChild(document.createElement("td"));
	tr_cabecalho.appendChild(td_cabecalho_3);
	tr_cabecalho.appendChild(document.createElement("td"));
	tr_cabecalho.appendChild(td_cabecalho_4);
	tr_cabecalho.appendChild(td_cabecalho_5);
	ancora.appendChild(tr_cabecalho);
	let cont = 1;
	let teste = [].map.call(listaModulo2_temp,function(item) {
		let regra = item.split('|');

		let tr = document.createElement("tr");
		tr.style = "height: 2em;";
		tr.className = 'linha-zebrada';

		let td1 = document.createElement("td");
		td1.style = "font-weight: bold";
		td1.innerText = "|___Regra " + cont + ":";
		tr.appendChild(td1);

		let td2 = document.createElement("td");
		td2.innerText = regra[0];
		tr.appendChild(td2);

		let td2a = document.createElement("td");
		tr.appendChild(td2a);

		let td3 = document.createElement("td");
		td3.innerText = regra[1];
		tr.appendChild(td3);

		let td3a = document.createElement("td");
		tr.appendChild(td3a);

		let td4 = document.createElement("td");
		td4.innerText = isNaN(Math.floor(regra[2])) ? regra[2] : 'Todas';
		tr.appendChild(td4);

		let td4a = document.createElement("td");
		tr.appendChild(td4a);

		let td5 = document.createElement("td");
		let var1 = "";

		for (i = 2; i <= regra.length-1; i++) {
			if (!isNaN(Math.floor(regra[i]))) {
				var1 += (i < regra.length-1) ? regra[i] + ", " : regra[i];
			}
		}
		td5.innerText = var1;
		tr.appendChild(td5);

		//*********criar botão editar
		let div_editar = document.createElement("div");
		div_editar.setAttribute("data-tooltip", "Editar");
		let bt_editar = document.createElement("i");
		bt_editar.className = "icone edit t16";
		bt_editar.style = "padding: 0 5px 0 5px;"
		bt_editar.setAttribute("pos",cont-1);
		bt_editar.onmouseenter = function() {
			bt_editar.style.setProperty("background-color","rgb(0, 120, 170)");
		}
		bt_editar.onmouseleave = function () {
			bt_editar.style.setProperty("background-color","black");
		};
		bt_editar.onclick = function () {
			editar_filtro_Atividades(parseInt(this.getAttribute("pos")))
		};
		div_editar.appendChild(bt_editar);

		//*********criar botão excluir
		let div_excluir = document.createElement("div");
		div_excluir.setAttribute("data-tooltip", "Excluir");
		let bt_excluir = document.createElement("i");
		bt_excluir.className = "icone trash-alt t16";
		bt_excluir.style = "padding: 0 5px 0 5px;"
		bt_excluir.setAttribute("pos",cont-1);
		bt_excluir.onmouseenter = function() {
			bt_excluir.style.setProperty("background-color","rgb(0, 120, 170)");
		}
		bt_excluir.onmouseleave = function (e) {
			bt_excluir.style.setProperty("background-color","black");
		};
		bt_excluir.onclick = function () {
			listaModulo2_temp.splice(parseInt(this.getAttribute("pos")), 1);
			preferencias.modulo2 = listaModulo2_temp;
			montar_modulo2();
			salvarOpcoes();
		};
		div_excluir.appendChild(bt_excluir);

		//*********criar botão mover pra cima
		let div_moverPraCima = document.createElement("div");
		if (cont > 1) {
			div_moverPraCima.setAttribute("data-tooltip", "subir posição");
			let bt_moverPraCima = document.createElement("i");
			bt_moverPraCima.innerText = "🡅";
			bt_moverPraCima.style = "padding: 0px 5px; font-style: normal; font-size: 1.3em;color: cadetblue;"
			bt_moverPraCima.setAttribute("pos",cont-1);
			bt_moverPraCima.onmouseenter = function() { this.style.color = 'rgb(0, 120, 170)' };
			bt_moverPraCima.onmouseleave = function (e) { this.style.color = 'cadetblue' };
			bt_moverPraCima.onclick = function () {
				let posAtual = this.getAttribute('pos');
				let posFutura = parseInt(posAtual) - 1;
				console.log('posAtual: ' + posAtual + ' - ' + 'posFutura: ' + posFutura);
				listaModulo2_temp.splice(posFutura, 0, listaModulo2_temp.splice(posAtual, 1)[0]);
				preferencias.modulo2 = listaModulo2_temp;
				montar_modulo2();
				salvarOpcoes();
			};
			div_moverPraCima.appendChild(bt_moverPraCima);
		}

		//*********criar botão mover pra cima
		let div_moverPraBaixo = document.createElement("div");
		if (cont < listaModulo2_temp.length) {
			div_moverPraBaixo.setAttribute("data-tooltip", "descer posição");
			let bt_moverPraBaixo = document.createElement("i");
			bt_moverPraBaixo.innerText = "🡇";
			bt_moverPraBaixo.style = "padding: 0px 5px; font-style: normal; font-size: 1.3em;color: chocolate;"
			bt_moverPraBaixo.setAttribute("pos",cont-1);
			bt_moverPraBaixo.onmouseenter = function() { this.style.color = 'orangered' };
			bt_moverPraBaixo.onmouseleave = function (e) { this.style.color = 'chocolate' };
			bt_moverPraBaixo.onclick = function () {
				let posAtual = this.getAttribute('pos');
				let posFutura = parseInt(posAtual) + 1;
				console.log('posAtual: ' + posAtual + ' - ' + 'posFutura: ' + posFutura);
				listaModulo2_temp.splice(posFutura, 0, listaModulo2_temp.splice(posAtual, 1)[0]);
				preferencias.modulo2 = listaModulo2_temp;
				montar_modulo2();
				salvarOpcoes();
			};
			div_moverPraBaixo.appendChild(bt_moverPraBaixo);
		}

		let td6 = document.createElement("td");
		td6.style = "display: grid;grid-template-columns: 1fr 1fr 1fr 1fr;";
		td6.appendChild(div_editar);
		td6.appendChild(div_excluir);
		td6.appendChild(div_moverPraCima);
		td6.appendChild(div_moverPraBaixo);
		tr.appendChild(td6);

		ancora.appendChild(tr);
		cont++;
	});

	async function excluirRepetidos() {
		return new Promise(resolve => {
			let lista = [];
			for (const [pos, item] of listaModulo2_temp.entries()) {
				if (lista.indexOf(item) == -1) {
					lista.push(item);
				}
			}
			resolve(lista);
		});
	}
}

//módulo 8
async function converter_lista_de_magistrados_em_modulo8() {
	return new Promise(async resolve => {
		let listaTemp = [];
		let corrigir = false;
		let teste = [].map.call(listaModulo8_temp,function(item) {
			let regra = item.split('|');
			if (regra[0] === 'true' || regra[0] === 'false') { //verifica se a regra se enquadra no novo formato
				//arrumar a regra de orgão julgador cargo.. cada tribunal define uma forma diferente. ex: TRT12 é Juiz Titular, já no TRT4 é JUIZ DO TRABALHO TITULAR
				if (!regra[12]) { regra[12] = 'TODOS' }
				if (regra[12].toLowerCase().includes('titular') && regra[12].toLowerCase() != 'titular') {
					console.log('maisPJe.. corrigindo regras MODULO8: orgão Julgador Cargo: ' + regra[12] + ' para titular')
					regra[12] = 'TITULAR';
					corrigir = true;
				} else if (regra[12].toLowerCase().includes('substituto') && regra[12].toLowerCase() != 'substituto') {
					console.log('maisPJe.. corrigindo regras MODULO8: orgão Julgador Cargo: ' + regra[12] + ' para substituto')
					regra[12] = 'SUBSTITUTO';
					corrigir = true;
				}
				// console.log(regra[0] + '|' + regra[1] + '|' + regra[2] + '|' + regra[3] + '|' + regra[4] + '|' + regra[5] + '|' + regra[6] + '|' + regra[7] + '|' + regra[8] + '|' + regra[9] + '|' + regra[10] + '|' + regra[11] + '|' + regra[12])
				listaTemp.push(regra[0] + '|' + regra[1] + '|' + regra[2] + '|' + regra[3] + '|' + regra[4] + '|' + regra[5] + '|' + regra[6] + '|' + regra[7] + '|' + regra[8] + '|' + regra[9] + '|' + regra[10] + '|' + regra[11] + '|' + regra[12]);
			} else {
				let resposta = '';
				if (regra.includes('0')) {
					resposta += 'true';
				} else {
					resposta += 'false';
				}
				resposta += '|';
				if (regra.includes('1')) {
					resposta += 'true';
				} else {
					resposta += 'false';
				}
				resposta += '|';
				if (regra.includes('2')) {
					resposta += 'true';
				} else {
					resposta += 'false';
				}
				resposta += '|';
				if (regra.includes('3')) {
					resposta += 'true';
				} else {
					resposta += 'false';
				}
				resposta += '|';
				if (regra.includes('4')) {
					resposta += 'true';
				} else {
					resposta += 'false';
				}
				resposta += '|';
				if (regra.includes('5')) {
					resposta += 'true';
				} else {
					resposta += 'false';
				}
				resposta += '|';
				if (regra.includes('6')) {
					resposta += 'true';
				} else {
					resposta += 'false';
				}
				resposta += '|';
				if (regra.includes('7')) {
					resposta += 'true';
				} else {
					resposta += 'false';
				}
				resposta += '|';
				if (regra.includes('8')) {
					resposta += 'true';
				} else {
					resposta += 'false';
				}
				resposta += '|';
				if (regra.includes('9')) {
					resposta += 'true';
				} else {
					resposta += 'false';
				}
				resposta += '|';
				resposta += regra[0];
				resposta += '|';
				resposta += 'TODOS';
				listaTemp.push(resposta);
			}

		});

		if (corrigir) {
			listaModulo8_temp = listaTemp;
			preferencias.modulo8 = listaModulo8_temp;
			let guardarStorage = browser.storage.local.set({ 'modulo8': listaTemp });
			Promise.all([guardarStorage]).then(values => {
				let Toast = Swal.mixin({
					toast: true,
					position: 'bottom-end',
					showConfirmButton: false,
					timer: 3000,
					timerProgressBar: true,
					onOpen: (toast) => {
					toast.addEventListener('mouseenter', Swal.stopTimer)
					toast.addEventListener('mouseleave', Swal.resumeTimer)
					}
				})
				Toast.fire({
					icon: 'success',
					title: 'corrigindo regras MODULO8:ORGÃO JULGADOR CARGO...'
				})
				setTimeout(function() {return resolve(true)}, 3000);
			});

		} else {
			listaModulo8_temp = listaTemp;
			preferencias.modulo8 = listaModulo8_temp;
			return resolve(true);
		}
	});

}

async function filtro_Magistrado() {
	const { value: result } = await Swal.fire({
		title: '    ',
		html:
			'<span>Magistrado(a):</span><br>' +
			'<input type="text" id="modulo8_magistrado" class="swal2-input" placeholder="Nome do(a) magistrado(a)">' +
			'<br><br>' +
			'<span>Unidade Judiciária:</span><br>' +
			'<span style="font-size: .8em;color: red;">preencha este campo APENAS se vc atuar em mais de um órgão Julgador (Vara) e quer definir regras diferentes para cada Juiz de cada órgão. Caso contrário, deixe preenchido a palavra TODOS</span><br>' +
			'<input type="text" id="modulo8_oj" class="swal2-input" placeholder="Nome do(a) órgão julgador">' +
			'<br><br>' +
			'<span>Processo Final:</span><br><br>' +
			'<div id="escolherProcessoFinal" class="destacarToogle" style="padding: 10px;border-radius: .1875em;">' +
			'<label class="container"' + (preferencias.modulo8_ignorarZero ? ' style="visibility: hidden;" ' : '') + '>' +
			'<input type="checkbox" id="modulo8_Filtro0" ' + (preferencias.modulo8_ignorarZero ? ' disabled ' : '') + '><span style="position: relative; padding-right: 15px; top: 2px; margin-left: -10px; font-size: 24px;">0</span>' +
			'<span class="checkmark"></span>' +
			'</label>' +
			'<label class="container">' +
			'<input type="checkbox" id="modulo8_Filtro1"><span style="position: relative; padding-right: 15px; top: 2px; margin-left: -10px; font-size: 24px;">1</span>' +
			'<span class="checkmark"></span>' +
			'</label>' +
			'<label class="container">' +
			'<input type="checkbox" id="modulo8_Filtro2"><span style="position: relative; padding-right: 15px; top: 2px; margin-left: -10px; font-size: 24px;">2</span>' +
			'<span class="checkmark"></span>' +
			'</label>' +
			'<label class="container">' +
			'<input type="checkbox" id="modulo8_Filtro3"><span style="position: relative; padding-right: 15px; top: 2px; margin-left: -10px; font-size: 24px;">3</span>' +
			'<span class="checkmark"></span>' +
			'</label>' +
			'<label class="container">' +
			'<input type="checkbox" id="modulo8_Filtro4"><span style="position: relative; padding-right: 15px; top: 2px; margin-left: -10px; font-size: 24px;">4</span>' +
			'<span class="checkmark"></span>' +
			'</label><br>' +
			'<label class="container">' +
			'<input type="checkbox" id="modulo8_Filtro5"><span style="position: relative; padding-right: 15px; top: 2px; margin-left: -10px; font-size: 24px;">5</span>' +
			'<span class="checkmark"></span>' +
			'</label>' +
			'<label class="container">' +
			'<input type="checkbox" id="modulo8_Filtro6"><span style="position: relative; padding-right: 15px; top: 2px; margin-left: -10px; font-size: 24px;">6</span>' +
			'<span class="checkmark"></span>' +
			'</label>' +
			'<label class="container">' +
			'<input type="checkbox" id="modulo8_Filtro7"><span style="position: relative; padding-right: 15px; top: 2px; margin-left: -10px; font-size: 24px;">7</span>' +
			'<span class="checkmark"></span>' +
			'</label>' +
			'<label class="container">' +
			'<input type="checkbox" id="modulo8_Filtro8"><span style="position: relative; padding-right: 15px; top: 2px; margin-left: -10px; font-size: 24px;">8</span>' +
			'<span class="checkmark"></span>' +
			'</label>' +
			'<label class="container">' +
			'<input type="checkbox" id="modulo8_Filtro9"><span style="position: relative; padding-right: 15px; top: 2px; margin-left: -10px; font-size: 24px;">9</span>' +
			'<span class="checkmark"></span>' +
			'</label>' +
			'<br><br><div style="display: grid; grid-template-columns: 1fr 1fr 1fr 1fr; gap: 1em; cursor: pointer;">' +
			'<span id="maisPje_parEimpar" name="par" class="swal2-label spanToogle">Par</span>' +
			'<span id="maisPje_parEimpar" name="impar"class="swal2-label spanToogle">Ímpar</span>' +
			'<span id="maisPje_parEimpar" name="todos" class="swal2-label spanToogle">Todos</span>' +
			'<span id="maisPje_parEimpar" name="nenhum" class="swal2-label spanToogle">Nenhum</span>' +
			'</div></div><br>' +
			'<span>Órgão Julgador Cargo:</span><br><br>' +
			'<div id="escolherOrgaoJulgadorCargo" class="destacarToogle" style="padding: 10px;border-radius: .1875em;">' +
			'<select id="modulo8_orgaoJulgadorCargo" class="swal2-select" style="background-color: white;width: 100%; border: 1px solid #d9d9d9;border-radius: .1875em;box-shadow: inset 0 1px 1px rgba(0,0,0,.06);height: 2.625em;padding: 0 .75em;">' +
				'<option value="TODOS"> TODOS </option>' +
				'<option value="TITULAR"> Juiz Titular </option>' +
				'<option value="SUBSTITUTO"> Juiz Substituto </option>' +
			'</select>' +
			'</div></div>',
		showCancelButton: true,
		focusConfirm: false,
		confirmButtonText: 'Salvar',
		cancelButtonText: 'Cancelar',
		preConfirm: () => {
			let resposta = "";
			resposta += preferencias.modulo8_ignorarZero ? 'false' : document.getElementById('modulo8_Filtro0').checked;
			resposta += "|";
			resposta += document.getElementById('modulo8_Filtro1').checked;
			resposta += "|";
			resposta += document.getElementById('modulo8_Filtro2').checked;
			resposta += "|";
			resposta += document.getElementById('modulo8_Filtro3').checked;
			resposta += "|";
			resposta += document.getElementById('modulo8_Filtro4').checked;
			resposta += "|";
			resposta += document.getElementById('modulo8_Filtro5').checked;
			resposta += "|";
			resposta += document.getElementById('modulo8_Filtro6').checked;
			resposta += "|";
			resposta += document.getElementById('modulo8_Filtro7').checked;
			resposta += "|";
			resposta += document.getElementById('modulo8_Filtro8').checked;
			resposta += "|";
			resposta += document.getElementById('modulo8_Filtro9').checked;
			resposta += "|";
			resposta += document.getElementById('modulo8_magistrado').value;
			resposta += "|";
			resposta += document.getElementById('modulo8_oj').value;
			resposta += "|";
			resposta += document.getElementById('modulo8_orgaoJulgadorCargo').value;
			return resposta;
		}
	});

	if (result) {
		listaModulo8_temp.push(result);
		montar_modulo8();
		salvarOpcoes();
	}
}

async function editar_filtro_Magistrado(pos) {
	let item = listaModulo8_temp[pos].split('|');
	item[12] = (!item[12]) ? 'Nenhum' : item[12];
	const { value: result } = await Swal.fire({
		title: '    ',
		html:
			'<span>Magistrado(a):</span><br>' +
			'<input type="text" id="modulo8_magistrado" class="swal2-input" placeholder="Nome do(a) magistrado(a)" value="' + item[10] + '">' +
			'<br><br>' +
			'<span>Unidade Judiciária:</span><br>' +
			'<span style="font-size: .8em;color: red;">preencha este campo APENAS se vc atuar em mais de um órgão Julgador (Vara) e quer definir regras diferentes para cada Juiz de cada órgão. Caso contrário, deixe preenchido a palavra TODOS</span><br>' +
			'<input type="text" id="modulo8_oj" class="swal2-input" placeholder="Nome do(a) órgão julgador" value="' + item[11] + '">' +
			'<br><br>' +
			'<span>Processo Final:</span><br><br>' +
			'<div id="escolherProcessoFinal" class="destacarToogle" style="padding: 10px;border-radius: .1875em;">' +
			'<label class="container"' + (preferencias.modulo8_ignorarZero ? ' style="visibility: hidden;" ' : '') + '>' +
			'<input type="checkbox" id="modulo8_Filtro0" ' + (item[0] === 'true' ? 'checked' : '') + ' ' + (preferencias.modulo8_ignorarZero ? ' disabled ' : '') + '><span style="position: relative; padding-right: 15px; top: 2px; margin-left: -10px; font-size: 24px;">0</span>' +
			'<span class="checkmark"></span>' +
			'</label>' +
			'<label class="container">' +
			'<input type="checkbox" id="modulo8_Filtro1" ' + (item[1] === 'true' ? 'checked' : '') + '><span style="position: relative; padding-right: 15px; top: 2px; margin-left: -10px; font-size: 24px;">1</span>' +
			'<span class="checkmark"></span>' +
			'</label>' +
			'<label class="container">' +
			'<input type="checkbox" id="modulo8_Filtro2" ' + (item[2] === 'true' ? 'checked' : '') + '><span style="position: relative; padding-right: 15px; top: 2px; margin-left: -10px; font-size: 24px;">2</span>' +
			'<span class="checkmark"></span>' +
			'</label>' +
			'<label class="container">' +
			'<input type="checkbox" id="modulo8_Filtro3" ' + (item[3] === 'true' ? 'checked' : '') + '><span style="position: relative; padding-right: 15px; top: 2px; margin-left: -10px; font-size: 24px;">3</span>' +
			'<span class="checkmark"></span>' +
			'</label>' +
			'<label class="container">' +
			'<input type="checkbox" id="modulo8_Filtro4" ' + (item[4] === 'true' ? 'checked' : '') + '><span style="position: relative; padding-right: 15px; top: 2px; margin-left: -10px; font-size: 24px;">4</span>' +
			'<span class="checkmark"></span>' +
			'</label><br>' +
			'<label class="container">' +
			'<input type="checkbox" id="modulo8_Filtro5" ' + (item[5] === 'true' ? 'checked' : '') + '><span style="position: relative; padding-right: 15px; top: 2px; margin-left: -10px; font-size: 24px;">5</span>' +
			'<span class="checkmark"></span>' +
			'</label>' +
			'<label class="container">' +
			'<input type="checkbox" id="modulo8_Filtro6" ' + (item[6] === 'true' ? 'checked' : '') + '><span style="position: relative; padding-right: 15px; top: 2px; margin-left: -10px; font-size: 24px;">6</span>' +
			'<span class="checkmark"></span>' +
			'</label>' +
			'<label class="container">' +
			'<input type="checkbox" id="modulo8_Filtro7" ' + (item[7] === 'true' ? 'checked' : '') + '><span style="position: relative; padding-right: 15px; top: 2px; margin-left: -10px; font-size: 24px;">7</span>' +
			'<span class="checkmark"></span>' +
			'</label>' +
			'<label class="container">' +
			'<input type="checkbox" id="modulo8_Filtro8" ' + (item[8] === 'true' ? 'checked' : '') + '><span style="position: relative; padding-right: 15px; top: 2px; margin-left: -10px; font-size: 24px;">8</span>' +
			'<span class="checkmark"></span>' +
			'</label>' +
			'<label class="container">' +
			'<input type="checkbox" id="modulo8_Filtro9" ' + (item[9] === 'true' ? 'checked' : '') + '><span style="position: relative; padding-right: 15px; top: 2px; margin-left: -10px; font-size: 24px;">9</span>' +
			'<span class="checkmark"></span>' +
			'</label>' +
			'<br><br><div style="display: grid; grid-template-columns: 1fr 1fr 1fr 1fr; gap: 1em; cursor: pointer;">' +
			'<span id="maisPje_parEimpar" name="par" class="swal2-label spanToogle">Par</span>' +
			'<span id="maisPje_parEimpar" name="impar"class="swal2-label spanToogle">Ímpar</span>' +
			'<span id="maisPje_parEimpar" name="todos" class="swal2-label spanToogle">Todos</span>' +
			'<span id="maisPje_parEimpar" name="nenhum" class="swal2-label spanToogle">Nenhum</span>' +
			'</div></div><br>' +
			'<span>Órgão Julgador Cargo:</span><br><br>' +
			'<div id="escolherOrgaoJulgadorCargo" class="destacarToogle" style="padding: 10px;border-radius: .1875em;">' +
			'<select id="modulo8_orgaoJulgadorCargo" class="swal2-select" style="background-color: white;width: 100%;border: 1px solid #d9d9d9; border-radius: .1875em;box-shadow: inset 0 1px 1px rgba(0,0,0,.06);height: 2.625em;padding: 0 .75em;">' +
				'<option value="TODOS"> TODOS </option>' +
				'<option value="TITULAR"' + (item[12].toLowerCase().includes('titular') ? 'selected' : '')  + '> Juiz Titular </option>' +
				'<option value="SUBSTITUTO"' + (item[12].toLowerCase().includes('substituto') ? 'selected' : '')  + '> Juiz Substituto </option>' +
			'</select>' +
			'</div></div>',
		showCancelButton: true,
		focusConfirm: false,
		confirmButtonText: 'Salvar',
		cancelButtonText: 'Cancelar',
		preConfirm: () => {
			let resposta = "";
			resposta += preferencias.modulo8_ignorarZero ? 'false' : document.getElementById('modulo8_Filtro0').checked;
			resposta += "|";
			resposta += document.getElementById('modulo8_Filtro1').checked;
			resposta += "|";
			resposta += document.getElementById('modulo8_Filtro2').checked;
			resposta += "|";
			resposta += document.getElementById('modulo8_Filtro3').checked;
			resposta += "|";
			resposta += document.getElementById('modulo8_Filtro4').checked;
			resposta += "|";
			resposta += document.getElementById('modulo8_Filtro5').checked;
			resposta += "|";
			resposta += document.getElementById('modulo8_Filtro6').checked;
			resposta += "|";
			resposta += document.getElementById('modulo8_Filtro7').checked;
			resposta += "|";
			resposta += document.getElementById('modulo8_Filtro8').checked;
			resposta += "|";
			resposta += document.getElementById('modulo8_Filtro9').checked;
			resposta += "|";
			resposta += document.getElementById('modulo8_magistrado').value;
			resposta += "|";
			resposta += (document.getElementById('modulo8_oj').value.length < 1 ? "TODOS" : document.getElementById('modulo8_oj').value);
			resposta += "|";
			resposta += document.getElementById('modulo8_orgaoJulgadorCargo').value;
			return resposta;
		}
	});

	if (result) {
		listaModulo8_temp[pos] = result;
		montar_modulo8();
		salvarOpcoes();
	}
}

function montar_modulo8() {
	// console.log('montar_modulo8: ' + listaModulo8_temp)
	let ancora = document.getElementById('lista_modulo8');
	ancora.textContent = "";
	let cont = 1;
	let teste = [].map.call(listaModulo8_temp,function(item) {
		let regra = item.split('|');

		let tr = document.createElement("tr");
		tr.style = "height: 2em;";

		let td1 = document.createElement("td");
		td1.style = "font-weight: bold";
		td1.innerText = "|___Regra " + cont + ":";
		tr.appendChild(td1);

		let td2 = document.createElement("td");
		td2.innerText = regra[10];
		tr.appendChild(td2);

		let td10 = document.createElement("td");
		td10.innerText = regra[12];
		tr.appendChild(td10);

		let td3 = document.createElement("td");
		td3.innerText = regra[11];
		tr.appendChild(td3);

		let td4 = document.createElement("td");
		td4.innerText = "processos final:";
		tr.appendChild(td4);

		let td5 = document.createElement("td");
		let var1 = "";
		for (i = 0; i <= 9; i++) {
			var1 += regra[i] === 'true' ? i : "";
			if (i < 9) {
				var1 += regra[i] === 'true' ? ", " : "";
			}
		}
		td5.innerText = var1;
		tr.appendChild(td5);

		//*********criar botão editar
		let div_editar = document.createElement("div");
		div_editar.setAttribute("data-tooltip", "Editar");
		let bt_editar = document.createElement("i");
		bt_editar.className = "icone edit t16";
		bt_editar.style = "padding: 0 5px 0 5px;"
		bt_editar.setAttribute("pos",cont-1);
		bt_editar.onmouseenter = function() {
			bt_editar.style.setProperty("background-color","rgb(0, 120, 170)");
		}
		bt_editar.onmouseleave = function () {
			bt_editar.style.setProperty("background-color","black");
		};
		bt_editar.onclick = function () {
			editar_filtro_Magistrado(parseInt(this.getAttribute("pos")))
		};
		div_editar.appendChild(bt_editar);

		//*********criar botão excluir
		let div_excluir = document.createElement("div");
		div_excluir.setAttribute("data-tooltip", "Excluir");
		let bt_excluir = document.createElement("i");
		bt_excluir.className = "icone trash-alt t16";
		bt_excluir.style = "padding: 0 5px 0 5px;"
		bt_excluir.setAttribute("pos",cont-1);
		bt_excluir.onmouseenter = function() {
			bt_excluir.style.setProperty("background-color","rgb(0, 120, 170)");
		}
		bt_excluir.onmouseleave = function (e) {
			bt_excluir.style.setProperty("background-color","black");
		};
		bt_excluir.onclick = function () {
			listaModulo8_temp.splice(parseInt(this.getAttribute("pos")), 1);
			montar_modulo8();
			salvarOpcoes();
		};
		div_excluir.appendChild(bt_excluir);

		let td6 = document.createElement("td");
		td6.style = "display: inline-flex;";
		td6.appendChild(div_editar);
		td6.appendChild(div_excluir);
		tr.appendChild(td6);

		ancora.appendChild(tr);
		cont++;
	});
}

//modulo 9
async function modulo9(convenio) {
	switch (convenio) {
		case 'sisbajud':

			//*****ajusta a teimosinha para a configuração de quantos dias quiser 30 e 60 dias
			let teimosinha = (!preferencias.sisbajud.teimosinha) ? 'nao' : preferencias.sisbajud.teimosinha;
			if (teimosinha.includes('60')) {
				teimosinha = '60';
			} else if (teimosinha.includes('55')) {
				teimosinha = '55';
			} else if (teimosinha.includes('50')) {
				teimosinha = '50';
			} else if (teimosinha.includes('45')) {
				teimosinha = '45';
			} else if (teimosinha.includes('40')) {
				teimosinha = '40';
			} else if (teimosinha.includes('35')) {
				teimosinha = '35';
			} else if (teimosinha.includes('30')) {
				teimosinha = '30';
			} else if (teimosinha.includes('25')) {
				teimosinha = '25';
			} else if (teimosinha.includes('20')) {
				teimosinha = '20';
			} else if (teimosinha.includes('15')) {
				teimosinha = '15';
			} else if (teimosinha.includes('10')) {
				teimosinha = '10';
			} else if (teimosinha.includes('5')) {
				teimosinha = '5';
			} else {
				teimosinha = 'nao'
			}
			//*****

			//desabilita o campo agencia se já estiver preenchido no banco preferido
			let agenciaDisabled = preferencias.sisbajud.banco_preferido.includes('[') ? true : false;

			aaSisbajud = (preferencias.sisbajud.executarAAaoFinal ? preferencias.sisbajud.executarAAaoFinal : 'Nenhum');

			let { value: resultsisbajud } = await Swal.fire({
				title: 'SISBAJUD',
				html:
					'A extensão traz diversas facilidades no convênio SISBAJUD. Desde a varinha mágica para preenchimento de campos automaticamente, como aplicação de estilos para facilitar a leitura da resposta do convênio. Você também pode utilizar a varinha mágica na tela de requisição de endereço.<br><br>' +
					'<input type="checkbox" id="swal2-checkbox"' + (preferencias.modulo9.sisbajud ? ' checked ' : '') + '>' +
					'<label for="swal2-checkbox" class="swal2-label"> Ativar</label><div style="display: grid;grid-template-columns: 1fr 1fr;align-items: center;">' +

					'<span style="font-weight: bold;background-color: #d3d3d350; margin-top: 40px; padding: 15px 0 15px 0;border-top: 2px solid #d3d3d3;">CONFIGURAÇÕES GERAIS</span>' +
					'<span style="font-weight: bold;background-color: #d3d3d350; margin-top: 40px; padding: 15px 0 15px 0;text-align: left;border-top: 2px solid #d3d3d3;">: </span>' +

					'<label for="swal-input1" style="font-weight: bold;"> Juiz solicitante da Ordem: </label>' +
					'<input id="swal-input1" class="swal2-input"" value="' + preferencias.sisbajud.juiz + '" style="margin-bottom: 0;">' +
					'<span style="font-weight: bold;" aria-hidden="true"> </span>' +
					'<span style="font-weight: normal;font-size: 0.8em;color: cadetblue;"> Para usar a regra do Módulo 8 digite: MODULO8 </span>' +
					'<label for="swal-input2" style="font-weight: bold;"> Vara/Juízo da ordem (use o código): </label>' +
					'<input id="swal-input2" class="swal2-input"" value="' + preferencias.sisbajud.vara + '">' +



					'<span style="font-weight: bold;background-color: #d3d3d350;padding: 15px 0 15px 0; margin-top: 40px;border-top: 2px solid #d3d3d3;">CONFIGURAÇÕES PARA MINUTAS</span>' +
					'<span style="font-weight: bold;background-color: #d3d3d350;padding: 15px 0 15px 0; margin-top: 40px;text-align: left;border-top: 2px solid #d3d3d3;">: </span>' +

					'<label for="swal-input3" style="font-weight: bold;"> Bloqueio sobre o CNPJ Raiz? </label>' +
					'<select id="swal-input3" class="swal2-select" style="background-color: white;width: 100%;border: 1px solid #d9d9d9;border-radius: .1875em;box-shadow: inset 0 1px 1px rgba(0,0,0,.06);height: 2.625em;padding: 0 .75em;">' +
						'<option value="nao"' + (preferencias.sisbajud.cnpjRaiz.toLowerCase().includes('nao') ? 'selected' : '')  + '> Não </option>' +
						'<option value="sim"' + (preferencias.sisbajud.cnpjRaiz.toLowerCase().includes('sim') ? 'selected' : '')  + '> Sim </option>' +
					'</select>' +

					'<label for="swal-input4" style="font-weight: bold;"> Teimosinha? </label>' +
					'<select id="swal-input4" class="swal2-select" style="background-color: white;width: 100%;border: 1px solid #d9d9d9;border-radius: .1875em;box-shadow: inset 0 1px 1px rgba(0,0,0,.06);height: 2.625em;padding: 0 .75em;">' +
						'<option value="nao"' + (teimosinha.toLowerCase().includes('nao') ? 'selected' : '')  + '> Não </option>' +
						'<option value="5"' + (teimosinha.includes('5') ? 'selected' : '')  + '> 5 dias </option>' +
						'<option value="10"' + (teimosinha.includes('10') ? 'selected' : '')  + '> 10 dias </option>' +
						'<option value="15"' + (teimosinha.includes('15') ? 'selected' : '')  + '> 15 dias </option>' +
						'<option value="20"' + (teimosinha.includes('20') ? 'selected' : '')  + '> 20 dias </option>' +
						'<option value="25"' + (teimosinha.includes('25') ? 'selected' : '')  + '> 25 dias </option>' +
						'<option value="30"' + (teimosinha.includes('30') ? 'selected' : '')  + '> 30 dias </option>' +
						'<option value="35"' + (teimosinha.includes('35') ? 'selected' : '')  + '> 35 dias </option>' +
						'<option value="40"' + (teimosinha.includes('40') ? 'selected' : '')  + '> 40 dias </option>' +
						'<option value="45"' + (teimosinha.includes('45') ? 'selected' : '')  + '> 45 dias </option>' +
						'<option value="50"' + (teimosinha.includes('50') ? 'selected' : '')  + '> 50 dias </option>' +
						'<option value="55"' + (teimosinha.includes('55') ? 'selected' : '')  + '> 55 dias </option>' +
						'<option value="60"' + (teimosinha.includes('60') ? 'selected' : '')  + '> 60 dias </option>' +
					'</select>' +

					'<label for="swal-input5" style="font-weight: bold;"> Penhorar conta-salário? </label>' +
					'<select id="swal-input5" class="swal2-select" style="background-color: white;width: 100%;border: 1px solid #d9d9d9;border-radius: .1875em;box-shadow: inset 0 1px 1px rgba(0,0,0,.06);height: 2.625em;padding: 0 .75em;">' +
						'<option value="nao"' + (preferencias.sisbajud.contasalario.toLowerCase().includes('nao') ? 'selected' : '')  + '> Não </option>' +
						'<option value="sim"' + (preferencias.sisbajud.contasalario.toLowerCase().includes('sim') ? 'selected' : '')  + '> Sim </option>' +
					'</select>' +

					'<label for="swal-input11" style="font-weight: bold;"> Preencher o Valor da Execução? </label>' +
					'<select id="swal-input11" class="swal2-select" style="background-color: white;width: 100%;border: 1px solid #d9d9d9;border-radius: .1875em;box-shadow: inset 0 1px 1px rgba(0,0,0,.06);height: 2.625em;padding: 0 .75em;">' +
						'<option value="nao"' + (preferencias.sisbajud.preencherValor.toLowerCase().includes('nao') ? 'selected' : '')  + '> Não </option>' +
						'<option value="sim"' + (preferencias.sisbajud.preencherValor.toLowerCase().includes('sim') ? 'selected' : '')  + '> Sim </option>' +
					'</select>' +

					'<label for="swal-input13" style="font-weight: bold;"> Clicar em Salvar e Protocolar? </label>' +
					'<select id="swal-input13" class="swal2-select" style="background-color: white;width: 100%;border: 1px solid #d9d9d9;border-radius: .1875em;box-shadow: inset 0 1px 1px rgba(0,0,0,.06);height: 2.625em;padding: 0 .75em;">' +
						'<option value="nao"' + (preferencias.sisbajud.salvarEprotocolar.toLowerCase().includes('nao') ? 'selected' : '')  + '> Não </option>' +
						'<option value="sim"' + (preferencias.sisbajud.salvarEprotocolar.toLowerCase().includes('sim') ? 'selected' : '')  + '> Sim </option>' +
					'</select>' +





					'<label for="swal-input12" style="font-weight: bold;"> Escolher Ação Automatizada para executar após o protocolo da ordem? </label>' +

					'<div style="display: grid;grid-template-columns: 5fr 1fr;align-items: center;"><button id="escolherAAVinculoAASISBAJUD" aria-description="Escolher Ação Automatizada para executar após PROTOCOLO da ordem de INCLUSÃO" style="cursor: pointer; background-color: white;border: 1px solid #d9d9d9;border-radius: .1875em;box-shadow: inset 0 1px 1px rgba(0,0,0,.06);height: 2.625em;padding: 0 .75em;display: flex;align-items: center;font-size: 1em;">' +
					aaSisbajud +
					'</button><button id="apagar-escolherAAVinculoAASISBAJUD" data-tooltip="Remover Ação Automatizada após PROTOCOLO da ordem de INCLUSÃO" aria-label="Remover Ação Automatizada após PROTOCOLO da ordem" style="margin-left: 15px; width: 40px; height: 40px; border: none; background: transparent; cursor: pointer;"><i class="icone trash-alt t20" style="background-color: lightgray; vertical-align: middle;"></i></button></div>' +

					'<span style="font-weight: bold;background-color: #d3d3d350;padding: 15px 0 15px 0; margin-top: 40px;border-top: 2px solid #d3d3d3;">CONFIGURAÇÕES PARA RESPOSTAS</span>' +
					'<span style="font-weight: bold;background-color: #d3d3d350;padding: 15px 0 15px 0; margin-top: 40px;text-align: left;border-top: 2px solid #d3d3d3;">: </span>' +

					'<label for="swal-input6" style="font-weight: bold;"> Não-Respostas? Reiterar ou Cancelar: </label>' +
					'<input id="swal-input6" class="swal2-input"" value="' + preferencias.sisbajud.naorespostas + '">' +
					'<label for="swal-input7" style="font-weight: bold;"> Desbloquear valores abaixo de: </label>' +
					'<input id="swal-input7" class="swal2-input"" value="' + preferencias.sisbajud.valor_desbloqueio + '">' +
					'<label for="swal-input8" style="font-weight: bold;"> Banco preferido (em caso de bloqueio): </label>' +
					'<input id="swal-input8" class="swal2-input"" value="' + preferencias.sisbajud.banco_preferido + '" style="margin-bottom: 0;">' +
					'<span style="font-weight: normal;font-size: 0.8em;color: cadetblue;"> Para abrir múltipla escolha digite o nome do banco (com a agência entre colchetes), separando as opções com vírgula. Por exemplo: </span>' +
					'<span style="font-weight: normal;font-size: 0.8em;color: cadetblue;align-self: flex-start;"> BCO DO BRASIL[1234],CAIXA ECONOMICA FEDERAL[9876] </span>' +
					'<label for="swal-input9" style="font-weight: bold;"> Agência preferida (em caso de bloqueio): </label>' +
					'<input id="swal-input9" class="swal2-input" ' + (agenciaDisabled ? 'disabled style="background-color: #d3d3d350;"' : 'value="' + preferencias.sisbajud.agencia_preferida + '"') + '>' +
					'<label for="swal-input10" style="font-weight: bold;"> Confirmar Banco e Agência? </label>' +
					'<select id="swal-input10" class="swal2-select" style="background-color: white;width: 100%;border: 1px solid #d9d9d9;border-radius: .1875em;box-shadow: inset 0 1px 1px rgba(0,0,0,.06);height: 2.625em;padding: 0 .75em;">' +
						'<option value="nao"' + (preferencias.sisbajud.confirmar.toLowerCase().includes('nao') ? 'selected' : '')  + '> Não </option>' +
						'<option value="sim"' + (preferencias.sisbajud.confirmar.toLowerCase().includes('sim') ? 'selected' : '')  + '> Sim </option>' +
					'</select>',

				focusConfirm: false,
				confirmButtonText: 'Salvar',
				width: 800,
				preConfirm: () => {
					return [
						document.getElementById('swal2-checkbox').checked,
						document.getElementById('swal-input1').value,
						document.getElementById('swal-input2').value,
						document.getElementById('swal-input3').value,
						document.getElementById('swal-input4').value,
						document.getElementById('swal-input5').value,
						document.getElementById('swal-input6').value,
						document.getElementById('swal-input7').value,
						document.getElementById('swal-input8').value,
						document.getElementById('swal-input9').value,
						document.getElementById('swal-input10').value,
						document.getElementById('swal-input11').value,
						document.getElementById('escolherAAVinculoAASISBAJUD').innerText,
						document.getElementById('swal-input13').value
					]
				}
			});

			if (resultsisbajud) {
				preferencias.modulo9.sisbajud = resultsisbajud[0];
				await guardarModulo9();
				document.getElementById("convenio_sisbajud").style.backgroundColor = (preferencias.modulo9.sisbajud) ? '#2196F3' : '#b0b0b0';

				preferencias.sisbajud = {
					juiz: resultsisbajud[1],
					vara: resultsisbajud[2],
					cnpjRaiz: resultsisbajud[3],
					teimosinha: resultsisbajud[4],
					contasalario: resultsisbajud[5],
					naorespostas: resultsisbajud[6],
					valor_desbloqueio: resultsisbajud[7],
					banco_preferido: resultsisbajud[8],
					agencia_preferida: resultsisbajud[9],
					confirmar: resultsisbajud[10],
					preencherValor: resultsisbajud[11],
					executarAAaoFinal: resultsisbajud[12],
					salvarEprotocolar: resultsisbajud[13]
				};
				let var1_sisbajud = browser.storage.local.set({'sisbajud': preferencias.sisbajud});
				Promise.all([var1_sisbajud]).then(values => {
					let Toast = Swal.mixin({
						toast: true,
						position: 'bottom-end',
						showConfirmButton: false,
						timer: 1500,
						timerProgressBar: true,
						onOpen: (toast) => {
						toast.addEventListener('mouseenter', Swal.stopTimer)
						toast.addEventListener('mouseleave', Swal.resumeTimer)
						}
					})
					Toast.fire({
						icon: 'success',
						title: 'Informações salvas com sucesso!'
					})
				});
			}
			break
		case 'renajud':
			let { value: resultrenajud } = await Swal.fire({
				title: 'RENAJUD',
				html:
					'A extensão leva a varinha mágica para dentro do RENAJUD. Com isso na tela de inclusão de restrições, ao acioná-la, basta escolher os executados para pesquisa e pronto, a extensão faz a consulta de todos pra você. Ela também preenche o número do processo nas telas de consulta e cancelamento para facilitar a busca.<br><br>' +
					'<input type="checkbox" id="swal2-checkbox"' + (preferencias.modulo9.renajud ? ' checked ' : '') + '>' +
					'<label for="swal2-checkbox" class="swal2-label"> Ativar</label><div style="display: grid;grid-template-columns: 1fr 1fr;align-items: center;">' +
					'<label for="swal-input1" style="font-weight: bold;"> Tipo de restrição (Transferência, Licenciamento ou Circulação): </label>' +
					'<input id="swal-input1" class="swal2-input"" value="' + preferencias.renajud.tipo_restricao + '">' +
					'<label for="swal-input2" style="font-weight: bold;"> Comarca (Renajud Antigo): </label>' +
					'<input id="swal-input2" class="swal2-input"" value="' + preferencias.renajud.comarca + '">' +
					'<label for="swal-input3" style="font-weight: bold;"> Tribunal (Renajud Novo): </label>' +
					'<input id="swal-input3" class="swal2-input"" value="' + preferencias.renajud.tribunal + '">' +
					'<label for="swal-input4" style="font-weight: bold;"> Órgão: </label>' +
					'<input id="swal-input4" class="swal2-input"" value="' + preferencias.renajud.orgao + '">' +
					'<label for="swal-input5" style="font-weight: bold;"> Juiz (Renajud Antigo): </label>' +
					'<input id="swal-input5" class="swal2-input"" value="' + preferencias.renajud.juiz + '">' +
					'<label for="swal-input6" style="font-weight: bold;"> Juiz (Renajud Novo): </label>' +
					'<input id="swal-input6" class="swal2-input"" value="' + preferencias.renajud.juiz2 + '">',
				focusConfirm: false,
				confirmButtonText: 'Salvar',
				width: 800,
				preConfirm: () => {
					return [
						document.getElementById('swal2-checkbox').checked,
						document.getElementById('swal-input1').value,
						document.getElementById('swal-input2').value,
						document.getElementById('swal-input3').value,
						document.getElementById('swal-input4').value,
						document.getElementById('swal-input5').value,
						document.getElementById('swal-input6').value
					]
				}
			});

			if (resultrenajud) {
				preferencias.modulo9.renajud = resultrenajud[0];
				await guardarModulo9();
				document.getElementById("convenio_renajud").style.backgroundColor = (preferencias.modulo9.renajud) ? '#2196F3' : '#b0b0b0';

				preferencias.renajud = {
					tipo_restricao: resultrenajud[1],
					comarca: resultrenajud[2],
					tribunal: resultrenajud[3],
					orgao: resultrenajud[4],
					juiz: resultrenajud[5],
					juiz2: resultrenajud[6]
				};
				let var1_renajud = browser.storage.local.set({'renajud': preferencias.renajud});
				Promise.all([var1_renajud]).then(values => {
					let Toast = Swal.mixin({
						toast: true,
						position: 'bottom-end',
						showConfirmButton: false,
						timer: 1500,
						timerProgressBar: true,
						onOpen: (toast) => {
						toast.addEventListener('mouseenter', Swal.stopTimer)
						toast.addEventListener('mouseleave', Swal.resumeTimer)
						}
					})
					Toast.fire({
						icon: 'success',
						title: 'Informações salvas com sucesso!'
					})
				});
			}
			break
		case 'cnib':

			let { value: resultcnib } = await Swal.fire({
				title: 'CNIB',
				html:
					'A extensão leva a varinha mágica para dentro do CNIB. Com isso na tela de inclusão de indisponibilidade, ao acioná-la, basta escolher os executados para pesquisa e pronto, a extensão faz a inclusão de todos pra você. Ela também preenche o número do processo nas telas de consulta e cancelamento para facilitar a busca.<br><br>' +
					'<input type="checkbox" id="swal2-checkbox0"' + (preferencias.modulo9.cnib.ativar ? ' checked ' : '') + '>' +
					'<label for="swal2-checkbox" class="swal2-label"> Ativar</label><br><br>' +
					'<div style="background-color: #95959512;padding: 10px;border-radius: 10px;"><label for="swal-input1" style="font-weight: bold;"> Velocidade de Interação no Cnib (em segundos)</label>' +
					'<input id="swal-input3" class="swal2-input" style="background-color: white;" value="' + preferencias.modulo9.cnib.velocidade + '"></div><br aria-hidden="true">' +

					'<div style="background-color: #95959512;padding: 10px;border-radius: 10px;">' +

					'<fieldset style="background-color: #16800024;">' +
					'<legend style="font-weight: bold;"> INCLUIR CNIB:</legend>' +
					'<div style="display: grid;grid-template-rows: 1fr 1fr 1fr;grid-gap: 5px;margin-top: 15px;text-align: initial;padding-left: 35%;">' +
					'<label><input type="checkbox" id="swal2-checkbox1"' + (preferencias.modulo9.cnib.inclusao[0] ? ' checked ' : '') + '>prosseguir automaticamente na tela "Enviar Processo"</label>' +
					'<label><input type="checkbox" id="swal2-checkbox2"' + (preferencias.modulo9.cnib.inclusao[1] ? ' checked ' : '') + '>escolher "Indisponibilidade Genérica"</label>' +
					'<label><input type="checkbox" id="swal2-checkbox3"' + (preferencias.modulo9.cnib.inclusao[2] ? ' checked ' : '') + '>prosseguir automaticamente na tela "Enviar Indisponibilidade"</label>' +
					'<label><input type="checkbox" id="swal2-checkbox4"' + (preferencias.modulo9.cnib.inclusao[3] ? ' checked ' : '') + '>protocolar automaticamente</label>' +
					'<label><input type="checkbox" id="swal2-checkbox5"' + (preferencias.modulo9.cnib.inclusao[4] ? ' checked ' : '') + '>copiar o número do protocolo"</label>' +
					'</div>' +
					'<div style="display: grid;grid-template-columns: auto 2% 30% 7%;align-items: center;margin-top: 15px;text-align: left;">' +
					'<span aria-hidden="true" style="font-weight: bold;"> Escolher Ação Automatizada para executar após PROTOCOLO da ordem de INCLUSÃO</span><span aria-hidden="true">:</span>' +
					'<button id="escolherAAVinculoAACNIB1" aria-description="Escolher Ação Automatizada para executar após PROTOCOLO da ordem de INCLUSÃO" style="cursor: pointer; background-color: white;border: 1px solid #d9d9d9;border-radius: .1875em;box-shadow: inset 0 1px 1px rgba(0,0,0,.06);height: 2.625em;padding: 0 .75em;display: flex;align-items: center;font-size: 1em;">' +
					(preferencias.modulo9.cnib.inclusao[5] ? preferencias.modulo9.cnib.inclusao[5] : 'Nenhum') +
					'</button><button id="apagar-escolherAAVinculoAACNIB1" data-tooltip="Remover Ação Automatizada após PROTOCOLO da ordem de INCLUSÃO" aria-label="Remover Ação Automatizada após PROTOCOLO da ordem" style="margin-left: 15px; width: 40px; height: 40px; border: none; background: transparent; cursor: pointer;"><i class="icone trash-alt t20" style="background-color: lightgray; vertical-align: middle;"></i></button>' +
					'</div><br aria-hidden="true">' +
					'</fieldset>' +

					'<fieldset style="background-color: #80000024;">' +
					'<legend style="font-weight: bold;"> EXCLUIR CNIB:</legend>' +
					'<div style="display: grid;grid-template-rows: 1fr 1fr 1fr;grid-gap: 5px;margin-top: 15px;text-align: initial;padding-left: 35%;">' +
					'<label>' +
					'<input type="radio" id="swal2-radio1" name="swal2-radio0"' + (preferencias.modulo9.cnib.exclusao[0] == 1 ? ' checked ' : '') + '>TOTAL' +
					'<input type="radio" id="swal2-radio2" name="swal2-radio0"' + (preferencias.modulo9.cnib.exclusao[0] == 2 ? ' checked ' : '') + '>PARCIAL' +
					'<input type="radio" id="swal2-radio3" name="swal2-radio0"' + ((preferencias.modulo9.cnib.exclusao[0] != 1 && preferencias.modulo9.cnib.exclusao[0] != 2) ? ' checked ' : '') + '>QUERO ESCOLHER' +
					'</label>' +
					'<label><input type="checkbox" id="swal2-checkbox7"' + (preferencias.modulo9.cnib.exclusao[1] ? ' checked ' : '') + '>prosseguir automaticamente na tela "Enviar Cancelamento"</label>' +
					'<label><input type="checkbox" id="swal2-checkbox8"' + (preferencias.modulo9.cnib.exclusao[2] ? ' checked ' : '') + '>protocolar automaticamente</label>' +
					'<label><input type="checkbox" id="swal2-checkbox9"' + (preferencias.modulo9.cnib.exclusao[3] ? ' checked ' : '') + '>copiar o número do protocolo"</label>' +
					'</div>' +
					'<div style="display: grid;grid-template-columns: auto 2% 30% 7%;align-items: center;margin-top: 15px;text-align: left;">' +
					'<span aria-hidden="true" style="font-weight: bold;">Escolher Ação Automatizada para executar após PROTOCOLO da ordem de EXCLUSÃO</span><span aria-hidden="true">:</span>' +
					'<button id="escolherAAVinculoAACNIB2" aria-description="Escolher Ação Automatizada para executar após PROTOCOLO da ordem de EXCLUSÃO" style="cursor: pointer; background-color: white;border: 1px solid #d9d9d9;border-radius: .1875em;box-shadow: inset 0 1px 1px rgba(0,0,0,.06);height: 2.625em;padding: 0 .75em;display: flex;align-items: center;font-size: 1em;">' +
					(preferencias.modulo9.cnib.exclusao[4] ? preferencias.modulo9.cnib.exclusao[4] : 'Nenhum') +
					'</button><button id="apagar-escolherAAVinculoAACNIB2" data-tooltip="Remover Ação Automatizada após PROTOCOLO da ordem de EXCLUSÃO" aria-label="Remover Ação Automatizada após PROTOCOLO da ordem" style="margin-left: 15px; width: 40px; height: 40px; border: none; background: transparent; cursor: pointer;"><i class="icone trash-alt t20" style="background-color: lightgray; vertical-align: middle;"></i></button>' +
					'</div><br aria-hidden="true">' +
					'</fieldset>' +

					'</div>',
				focusConfirm: false,
				confirmButtonText: 'Salvar',
				width: 800,
				preConfirm: () => {

					let tipoDeExclusao = 0;
					if (document.getElementById('swal2-radio1').checked) { tipoDeExclusao = 1 }
					else if (document.getElementById('swal2-radio2').checked) { tipoDeExclusao = 2 }

					return {
						'ativar':document.getElementById('swal2-checkbox0').checked,
						'velocidade': document.getElementById('swal-input3').value,
						'inclusao': [document.getElementById('swal2-checkbox1').checked,document.getElementById('swal2-checkbox2').checked,document.getElementById('swal2-checkbox3').checked,document.getElementById('swal2-checkbox4').checked,document.getElementById('swal2-checkbox5').checked,document.getElementById('escolherAAVinculoAACNIB1').innerText],
						'exclusao': [tipoDeExclusao,document.getElementById('swal2-checkbox7').checked,document.getElementById('swal2-checkbox8').checked,document.getElementById('swal2-checkbox8').checked,document.getElementById('escolherAAVinculoAACNIB2').innerText],
					}
				}
			});

			if (resultcnib) {
				preferencias.modulo9.cnib = resultcnib;
				await guardarModulo9();
				document.getElementById("convenio_cnib").style.backgroundColor = (preferencias.modulo9.cnib) ? '#2196F3' : '#b0b0b0';
			}
			break
		case 'serasajud':
			let aaSerasajud = (preferencias.serasajud.aa ? preferencias.serasajud.aa : 'Nenhum');
			let { value: resultserasajud } = await Swal.fire({
				title: 'SERASAJUD',
				html:
					'A extensão leva a varinha mágica para dentro do SERASAJUD. Com isso na tela de cadastro de nova ordem, ao acioná-la, basta escolher os executados para pesquisa e pronto, a extensão faz a inclusão de todos pra você. Você também pode utilizar a varinha mágica na tela de requisição de endereço. Ela também preenche o número do processo nas telas de consulta e cancelamento para facilitar a busca.<br><br>' +
					'<input type="checkbox" id="swal2-checkbox"' + (preferencias.modulo9.serasajud ? ' checked ' : '') + '>' +
					'<label for="swal2-checkbox" class="swal2-label"> Ativar</label><div style="display: grid;grid-template-columns: 1fr 1fr;align-items: center;">' +
					'<label for="swal-input1" style="font-weight: bold;"> Foro da ordem: </label>' +
					'<input id="swal-input1" class="swal2-input"" value="' + preferencias.serasajud.foro + '">' +
					'<label for="swal-input2" style="font-weight: bold;"> Vara da ordem: </label>' +
					'<input id="swal-input2" class="swal2-input"" value="' + preferencias.serasajud.vara + '">' +
					'<label for="swal-input3" style="font-weight: bold;"> Prazo de Atendimento - Preencha apenas o número (5)dias (3)dias (2)dias (1)dias: </label>' +
					'<input id="swal-input3" class="swal2-input"" value="' + preferencias.serasajud.prazo_atendimento + '">'+
					'<label for="swal-input4" style="font-weight: bold;"> Escolher Ação Automatizada para executar após o protocolo da ordem: </label>' +
					'<select id="swal-input4" class="swal2-select" style="background-color: white;width: 100%;border: 1px solid #d9d9d9;border-radius: .1875em;box-shadow: inset 0 1px 1px rgba(0,0,0,.06);height: 2.625em;padding: 0 .75em;">' +
					listaAcoesAutomatizadas(aaSerasajud) +
					'</select></div>',
				focusConfirm: false,
				confirmButtonText: 'Salvar',
				width: 800,
				preConfirm: () => {
					return [
						document.getElementById('swal2-checkbox').checked,
						document.getElementById('swal-input1').value,
						document.getElementById('swal-input2').value,
						document.getElementById('swal-input3').value,
						document.getElementById('swal-input4').value,
					]
				}
			});

			if (resultserasajud) {
				preferencias.modulo9.serasajud = resultserasajud[0];
				await guardarModulo9();
				document.getElementById("convenio_serasajud").style.backgroundColor = (preferencias.modulo9.serasajud) ? '#2196F3' : '#b0b0b0';

				preferencias.serasajud = {
					foro: resultserasajud[1],
					vara: resultserasajud[2],
					prazo_atendimento: resultserasajud[3],
					aa:resultserasajud[4]
				};
				let var1_serasajud = browser.storage.local.set({'serasajud': preferencias.serasajud});
				Promise.all([var1_serasajud]).then(values => {
					let Toast = Swal.mixin({
						toast: true,
						position: 'bottom-end',
						showConfirmButton: false,
						timer: 1500,
						timerProgressBar: true,
						onOpen: (toast) => {
						toast.addEventListener('mouseenter', Swal.stopTimer)
						toast.addEventListener('mouseleave', Swal.resumeTimer)
						}
					})
					Toast.fire({
						icon: 'success',
						title: 'Informações salvas com sucesso!'
					})
				});
			}
			break
		case 'ccs':
			let aaCCS = (preferencias.modulo9.ccs[6] ? preferencias.modulo9.ccs[6] : 'Nenhum');
			let { value: resultccs } = await Swal.fire({
				title: 'CCS',
				html:
					'A extensão leva a varinha mágica para dentro do CCS. Com isso na tela de cadastro de nova ordem, ao acioná-la, basta escolher os executados para pesquisa e pronto, a extensão faz a inclusão de todos pra você. Você também pode utilizar a consulta rápida de processo para abrir um processo diretamente no PJe.<br><br>' +
					'<input type="checkbox" id="swal2-checkbox0"' + (preferencias.modulo9.ccs[0] ? ' checked ' : '') + '>' +
					'<label for="swal2-checkbox" class="swal2-label"> Ativar</label><br><br>' +
					'<div style="background-color: #95959512;padding: 10px;border-radius: 10px;">' +
					'<fieldset>' +
					'<legend style="font-weight: bold;"> Prosseguir Automaticamente:</legend>' +
					'<div style="display: grid;grid-template-rows: 1fr 1fr 1fr;grid-gap: 5px;margin-top: 15px;text-align: initial;padding-left: 35%;">' +
					'<label><input type="checkbox" id="swal2-checkbox1"' + (preferencias.modulo9.ccs[1] ? ' checked ' : '') + '>na tela "Requisitar consulta"</label>' +
					'<label><input type="checkbox" id="swal2-checkbox2"' + (preferencias.modulo9.ccs[2] ? ' checked ' : '') + '>na tela "Confirmar consulta"</label>' +
					'<label><input type="checkbox" id="swal2-checkbox3"' + (preferencias.modulo9.ccs[3] ? ' checked ' : '') + '>na tela "Solicitação de detalhamentos"</label>' +
					'<label><input type="checkbox" id="swal2-checkbox4"' + (preferencias.modulo9.ccs[4] ? ' checked ' : '') + '>na tela "Escolher as contas"</label>' +
					'</div></div><br aria-hidden="true"><br aria-hidden="true">'+
					'</fieldset>' +
					'<div style="background-color: #95959512;padding: 10px;border-radius: 10px;"><label for="swal-input1" style="font-weight: bold;"> Velocidade de Interação no CCS (em segundos)</label>' +
					'<input id="swal-input1" class="swal2-input" style="background-color: white;" value="' + preferencias.modulo9.ccs[5] + '"></div>' +
					'<div><label for="swal-input2" style="font-weight: bold;"> Escolher Ação Automatizada para executar após o protocolo da ordem? </label>' +
					'<select id="swal-input2" class="swal2-select" style="background-color: white;width: 100%;border: 1px solid #d9d9d9;border-radius: .1875em;box-shadow: inset 0 1px 1px rgba(0,0,0,.06);height: 2.625em;padding: 0 .75em;">' +
					listaAcoesAutomatizadas(aaCCS) +
					'</select></div>',

				focusConfirm: false,
				confirmButtonText: 'Salvar',
				width: 800,
				preConfirm: () => {
					return [
						document.getElementById('swal2-checkbox0').checked,
						document.getElementById('swal2-checkbox1').checked,
						document.getElementById('swal2-checkbox2').checked,
						document.getElementById('swal2-checkbox3').checked,
						document.getElementById('swal2-checkbox4').checked,
						document.getElementById('swal-input1').value,
						document.getElementById('swal-input2').value
					]
				}
			});

			if (resultccs) {
				preferencias.modulo9.ccs = resultccs;
				await guardarModulo9();
				document.getElementById("convenio_ccs").style.backgroundColor = (preferencias.modulo9.ccs) ? '#2196F3' : '#b0b0b0';
			}
			break
		case 'crcjud':
			let { value: resultcrcjud } = await Swal.fire({
				title: 'CRCJUD',
				html:
					'Na tela "Busca de Registros", a extensão preenche o número do processo, vara, e permite escolher um dos executados do processo. Insere ainda o botão IMPRIMIR, que viabiliza a impressão apenas do conteúdo relevante, e, o botão "Incluir Executado" para inserir pesquisar outro executado do processo.<br>Na tela "Pedido de Certidão", a extensão preenche o número do processo, vara, e permite escolher um dos executados do processo.<br>Na tela "Certidões solicitadas", a extensão preenche apenas o número do processo.<br><br>' +
					'<input type="checkbox" id="swal2-checkbox"' + (preferencias.modulo9.crcjud ? ' checked ' : '') + '>' +
					'<label for="swal2-checkbox" class="swal2-label"> Ativar</label>',
				focusConfirm: false,
				confirmButtonText: 'Salvar',
				width: 800,
				preConfirm: () => {
					return [document.getElementById('swal2-checkbox').checked];
				}
			});

			if (resultcrcjud) {
				preferencias.modulo9.crcjud = resultcrcjud[0];
				await guardarModulo9();
				document.getElementById("convenio_crcjud").style.backgroundColor = (preferencias.modulo9.crcjud) ? '#2196F3' : '#b0b0b0';
			}
			break
		case 'onr':
			preferencias.modulo9.onr = false;
			let { value: resultonr } = await Swal.fire({
				title: 'ONR',
				html:
					'A extensão preenche o número do processo nas telas de consulta e cadastro para facilitar a busca.<br><br>' +
					'<input type="checkbox" id="swal2-checkbox"' + (preferencias.modulo9.onr ? ' checked ' : '') + '>' +
					'<label for="swal2-checkbox" class="swal2-label"> Ativar </label>',
				focusConfirm: false,
				confirmButtonText: 'Salvar',
				width: 800,
				preConfirm: () => {
					alert('[INDISPONÍVEL] Estamos trabalhando na adequação da extensão para a nova página do convênio (penhoraonline.org.br).')
					document.getElementById('swal2-checkbox').checked = false;
					return [document.getElementById('swal2-checkbox').checked];
				}
			});

			if (resultonr) {
				preferencias.modulo9.onr = resultonr[0];
				await guardarModulo9();
				document.getElementById("convenio_onr").style.backgroundColor = (preferencias.modulo9.onr) ? '#2196F3' : '#b0b0b0';
			}
			break
		case 'gprec':
			let { value: resultgprec } = await Swal.fire({
				title: 'GPREC',
				html:
					'A extensão preenche o número do processo nas telas de cadastro para facilitar.<br><br>' +
					'<input type="checkbox" id="swal2-checkbox"' + (preferencias.modulo9.gprec[0] ? ' checked ' : '') + '>' +
					'<label for="swal2-checkbox" class="swal2-label"> Ativar</label><br><br>' +
					'<input type="checkbox" id="swal2-checkbox2"' + (preferencias.modulo9.gprec[2] ? ' checked ' : '') + '>' +
					'<label for="swal2-checkbox2" class="swal2-label"> Registrar valores proporcionais no pagamento</label><br><br>' +
					'<label for="swal-input0" style="font-weight: bold;"> Na tela de cadastro, escolher qual tipo de requisição? </label>' +
					'<select id="swal-input0" class="swal2-select" style="background-color: white;width: 100%;border: 1px solid #d9d9d9;border-radius: .1875em;box-shadow: inset 0 1px 1px rgba(0,0,0,.06);height: 2.625em;padding: 0 .75em;">' +
						'<option value="precatorio"' + (preferencias.modulo9.gprec[3].toLowerCase().includes('precatorio') ? 'selected' : '')  + '> Precatório </option>' +
						'<option value="rpv"' + (preferencias.modulo9.gprec[3].toLowerCase().includes('rpv') ? 'selected' : '')  + '> RPV </option>' +
					'</select>' +
					'<div style="background-color: #95959512;padding: 10px;border-radius: 10px;"><label style="font-weight: bold;" for="swal-input1"> Velocidade de Interação no GPREC (em segundos)</label>' +
					'<input id="swal-input1" class="swal2-input" style="background-color: white;" value="' + preferencias.modulo9.gprec[1] + '"></div>',
				focusConfirm: false,
				confirmButtonText: 'Salvar',
				width: 800,
				preConfirm: () => {
					return [
						document.getElementById('swal2-checkbox').checked,
						document.getElementById('swal-input1').value,
						document.getElementById('swal2-checkbox2').checked,
						document.getElementById('swal-input0').value,
					]
				}
			});

			if (resultgprec) {
				preferencias.modulo9.gprec[0] = resultgprec[0];
				preferencias.modulo9.gprec[1] = resultgprec[1];
				preferencias.modulo9.gprec[2] = resultgprec[2];
				preferencias.modulo9.gprec[3] = resultgprec[3];
				await guardarModulo9();
				document.getElementById("convenio_gprec").style.backgroundColor = (preferencias.modulo9.gprec) ? '#2196F3' : '#b0b0b0';
			}
			break
		case 'ajjt':
			let { value: resultajjt } = await Swal.fire({
				title: 'AJJT',
				html:
					'A extensão busca o processo automaticamente na tela de "Registro de Nomeações de Profissionais", auxiliando ainda no preenchimento dos campos quando do cadastro.<br><br>' +
					'<input type="checkbox" id="swal2-checkbox"' + (preferencias.modulo9.ajjt ? ' checked ' : '') + '>' +
					'<label for="swal2-checkbox" class="swal2-label"> Ativar</label>',
				focusConfirm: false,
				confirmButtonText: 'Salvar',
				width: 800,
				preConfirm: () => {
					return [document.getElementById('swal2-checkbox').checked];
				}
			});

			if (resultajjt) {
				preferencias.modulo9.ajjt = resultajjt[0];
				await guardarModulo9();
				document.getElementById("convenio_ajjt").style.backgroundColor = (preferencias.modulo9.ajjt) ? '#2196F3' : '#b0b0b0';
			}
			break
		case 'siscondj':
			let { value: resultsiscondj } = await Swal.fire({
				title: 'SISCONDJ',
				html:
					'A extensão preenche o número do processo nas telas de consulta para facilitar. Insere o botão de abrir processo no PJe quando da conferência de alvarás expedidos e pendentes de finalização.<br><br>' +
					'<input type="checkbox" id="swal2-checkbox"' + (preferencias.modulo9.siscondj[0] ? ' checked ' : '') + '>' +
					'<label for="swal2-checkbox" class="swal2-label"> Ativar</label><br><br>' +
					'<input type="checkbox" id="swal2-checkbox2"' + (preferencias.modulo9.siscondj[2] ? ' checked ' : '') + '>' +
					'<label for="swal2-checkbox2" class="swal2-label"> Expandir subcontas automaticamente</label><br><br>' +
					'<div style="background-color: #95959512;padding: 10px;border-radius: 10px;"><span style="font-weight: bold;"> Velocidade de Interação no SISCONDJ (em segundos)</span>' +
					'<input id="swal-input1" class="swal2-input" style="background-color: white;" value="' + preferencias.modulo9.siscondj[1] + '"></div>',
				focusConfirm: false,
				confirmButtonText: 'Salvar',
				width: 800,
				preConfirm: () => {
					return [
						document.getElementById('swal2-checkbox').checked,
						document.getElementById('swal-input1').value,
						document.getElementById('swal2-checkbox2').checked,
					]
				}
			});

			if (resultsiscondj) {
				preferencias.modulo9.siscondj[0] = resultsiscondj[0];
				preferencias.modulo9.siscondj[1] = resultsiscondj[1];
				preferencias.modulo9.siscondj[2] = resultsiscondj[2];
				await guardarModulo9();
				document.getElementById("convenio_siscondj").style.backgroundColor = (preferencias.modulo9.siscondj) ? '#2196F3' : '#b0b0b0';
			}
			break
		case 'garimpo':
			let { value: resultgarimpo } = await Swal.fire({
				title: 'GARIMPO',
				html:
					'Ao clicar em "Associar Processo", a extensão automaticamente faz a consulta no PJe por nome do reclamante, eliminando incontáveis cliques. O botão de "Bloquear Processo" agora é acionado com apenas um clique, e ao fazê-lo o número do processo se transforma num link que leva até o processo no PJe.<br><br>' +
					'<input type="checkbox" id="swal2-checkbox"' + (preferencias.modulo9.garimpo[0] ? ' checked ' : '') + '>' +
					'<label for="swal2-checkbox" class="swal2-label"> Ativar</label>' +
					'<div style="background-color: #95959512;padding: 10px;border-radius: 10px;"><span style="font-weight: bold;"> Endereço do Sistema Garimpo </span>' +
					'<input id="swal-input1" class="swal2-input" style="background-color: white;" value="' + preferencias.modulo9.garimpo[1] + '"></div>',
				focusConfirm: false,
				confirmButtonText: 'Salvar',
				width: 800,
				preConfirm: () => {
					return [document.getElementById('swal2-checkbox').checked,document.getElementById('swal-input1').value];
				}
			});

			if (resultgarimpo) {
				preferencias.modulo9.garimpo[0] = resultgarimpo[0];
				preferencias.modulo9.garimpo[1] = resultgarimpo[1];
				await guardarModulo9();
				document.getElementById("convenio_garimpo").style.backgroundColor = (preferencias.modulo9.garimpo) ? '#2196F3' : '#b0b0b0';
			}
			break
		case 'sif':
			preferencias.modulo9.sif[2]
			let { value: resultsif } = await Swal.fire({
				title: 'SIF',
				html:
					'Ao expedir ordem eletrônica, a escolha do magistrado ocorre de acordo com as regras estabelecidas no módulo 8. Além de preencher, com os dados guardados na memória do navegador, os campos de tipo de pessoa, nome e documento de acordo com o beneficiário/representante escolhido. A função apenas funciona no modo de criação de novo alvará.<br>Também foi criado o botão "Exibir Alvarás para Conferência" que fica visível no Escaninho > Situação de Alvará. O objetivo da funcionalidade é oferecer ao usuário conferente uma lista de alvarás pendentes de conferência com link direto para o respectivo documento.<br><br>' +
					'<label for="swal-input2" style="font-weight: bold;"> Data de Atualização do Alvará </label>' +
					'<select id="swal-input2" class="swal2-select" style="background-color: white;width: 100%;border: 1px solid #d9d9d9;border-radius: .1875em;box-shadow: inset 0 1px 1px rgba(0,0,0,.06);height: 2.625em;padding: 0 .75em;">' +
						'<option value="dia"' + (preferencias.modulo9.sif[2].toLowerCase().includes('dia') ? 'selected' : '')  + '> Data do Dia </option>' +
						'<option value="deposito"' + (preferencias.modulo9.sif[2].toLowerCase().includes('deposito') ? 'selected' : '')  + '> Data do Depósito </option>' +
					'</select>' +
					'<input type="checkbox" id="swal2-checkbox"' + (preferencias.modulo9.sif[0] ? ' checked ' : '') + '>' +
					'<label for="swal2-checkbox" class="swal2-label"> Ativar</<label><br><br>' +
					'<div style="background-color: #95959512;padding: 10px;border-radius: 10px;"><label for="swal-input1" style="font-weight: bold;"> Velocidade de Interação no SIF (em segundos)</label>' +
					'<input id="swal-input1" class="swal2-input" style="background-color: white;" value="' + preferencias.modulo9.sif[1] + '"></div>',
				focusConfirm: false,
				confirmButtonText: 'Salvar',
				width: 800,
				preConfirm: () => {
					return [
						document.getElementById('swal2-checkbox').checked,
						document.getElementById('swal-input1').value,
						document.getElementById('swal-input2').value
					]
				}
			});

			if (resultsif) {
				preferencias.modulo9.sif[0] = resultsif[0];
				preferencias.modulo9.sif[1] = resultsif[1];
				preferencias.modulo9.sif[2] = resultsif[2];
				await guardarModulo9();
				document.getElementById("convenio_sif").style.backgroundColor = (preferencias.modulo9.sif) ? '#2196F3' : '#b0b0b0';
			}
			break
		case 'pjecalc':
			let { value: resultpjecalc } = await Swal.fire({
				title: 'pjeCalc',
				html:
					'Ao buscar cálculo ou criar novo cálculo, se existir processo na memória, ele será utilizado no preenchimento automático dos campos.<br><br>' +
					'<input type="checkbox" id="swal2-checkbox"' + (preferencias.modulo9.pjecalc ? ' checked ' : '') + '>' +
					'<label for="swal2-checkbox" class="swal2-label"> Ativar</label>',
				focusConfirm: false,
				confirmButtonText: 'Salvar',
				width: 800,
				preConfirm: () => {
					return [document.getElementById('swal2-checkbox').checked];
				}
			});

			if (resultpjecalc) {
				preferencias.modulo9.pjecalc = resultpjecalc[0];
				await guardarModulo9();
				document.getElementById("convenio_pjecalc").style.backgroundColor = (preferencias.modulo9.pjecalc) ? '#2196F3' : '#b0b0b0';
			}
			break
		case 'prevjud':
			let aaPrevjud = (preferencias.prevjud.aa ? preferencias.prevjud.aa : 'Nenhum');
			let aa2Prevjud = (preferencias.prevjud.aa2 ? preferencias.prevjud.aa2 : 'Nenhum');
			let opt1Prevjud = (preferencias.prevjud.opt1 ? preferencias.prevjud.opt1 : false);
			let { value: resultprevjud } = await Swal.fire({
				title: 'prevjud',
				html:
					'A extensão leva a varinha mágica para dentro do PREVJUD. Com isso na tela de cadastro de nova ordem, ao acioná-la, basta escolher o reclamante. Primeiro será realizado a pesquisa de eventual ordem anterior, e caso não seja encontrado será inserido uma nova ordem.<br><br>' +
					'<div style="background-color: #f0efef;padding: 18px;border-radius: 5px; display: flex; flex-direction: column; gap: 10px;">' +
					'<label for="swal2-checkbox" class="swal2-label">' +
					'<input type="checkbox" id="swal2-checkbox"' + (preferencias.modulo9.prevjud ? ' checked ' : '') + '>' +
					' Ativar</label>' +
					'<label class="swal2-label" for="swal2-checkbox2">' +
					'<input type="checkbox" id="swal2-checkbox2"' + (opt1Prevjud ? ' checked ' : '') + '>' +
					'Baixar automaticamente ao consultar</label>' +
					'</div>' +
					'<div style="display: grid;grid-template-columns: auto 2% 40% 3%;align-items: center;margin-top: 15px;text-align: left;">' +
					'<span aria-hidden="true" style="font-weight: bold;"> Escolher Ação Automatizada para executar após PROTOCOLO da ordem</span><span aria-hidden="true">:</span>' +
					'<button id="escolherAAVinculoAAPrevjud" aria-description="Escolher Ação Automatizada para executar após PROTOCOLO da ordem" style="cursor: pointer; background-color: white;border: 1px solid #d9d9d9;border-radius: .1875em;box-shadow: inset 0 1px 1px rgba(0,0,0,.06);height: 2.625em;padding: 0 .75em;display: flex;align-items: center;font-size: 1em;">' +
					aaPrevjud +
					'</button><button id="apagar-escolherAAVinculoAAPrevjud" data-tooltip="Remover Ação Automatizada após PROTOCOLO da ordem" aria-label="Remover Ação Automatizada após PROTOCOLO da ordem" style="margin-left: 15px; width: 40px; height: 40px; border: none; background: transparent; cursor: pointer;"><i class="icone trash-alt t20" style="background-color: lightgray; vertical-align: middle;"></i></button></div>' +
					'<div style="display: grid;grid-template-columns: auto 2% 40% 3%;align-items: center;margin-top: 15px;text-align: left;">' +
					'<span aria-hidden="true" style="font-weight: bold;"> Escolher Ação Automatizada para executar após CONSULTA da ordem</span><span aria-hidden="true">:</span>' +
					'<button id="escolherAAVinculoAA2Prevjud" aria-description="Escolha Ação Automatizada para executar após CONSULTA da ordem" style="cursor: pointer; background-color: white;border: 1px solid #d9d9d9;border-radius: .1875em;box-shadow: inset 0 1px 1px rgba(0,0,0,.06);height: 2.625em;padding: 0 .75em;display: flex;align-items: center;font-size: 1em;">' +
					aa2Prevjud +
					'</button>'+
					'<button id="apagar-escolherAAVinculoAA2Prevjud"  data-tooltip="Remover Ação Automatizada após CONSULTA da ordem" aria-label="Remover Ação Automatizada após CONSULTA da ordem" style="margin-left: 15px; width: 40px; height: 40px; border: none; background: transparent; cursor: pointer;"><i class="icone trash-alt t20" style="background-color: lightgray; vertical-align: middle;"></i></button></div>',


				focusConfirm: false,
				confirmButtonText: 'Salvar',
				width: 800,
				preConfirm: () => {
					return [
						document.getElementById('swal2-checkbox').checked,
						document.getElementById('escolherAAVinculoAAPrevjud').innerText,
						document.getElementById('swal2-checkbox2').checked,
						document.getElementById('escolherAAVinculoAA2Prevjud').innerText,
					];
				}
			});

			if (resultprevjud) {
				preferencias.modulo9.prevjud = resultprevjud[0];
				await guardarModulo9();
				document.getElementById("convenio_prevjud").style.backgroundColor = (preferencias.modulo9.prevjud) ? '#2196F3' : '#b0b0b0';

				preferencias.prevjud = {
					aa:resultprevjud[1],
					opt1:resultprevjud[2],
					aa2:resultprevjud[3],
				};

				let var1_prevjud = browser.storage.local.set({'prevjud': preferencias.prevjud});
				Promise.all([var1_prevjud]).then(values => {
					let Toast = Swal.mixin({
						toast: true,
						position: 'bottom-end',
						showConfirmButton: false,
						timer: 1500,
						timerProgressBar: true,
						onOpen: (toast) => {
						toast.addEventListener('mouseenter', Swal.stopTimer)
						toast.addEventListener('mouseleave', Swal.resumeTimer)
						}
					})
					Toast.fire({
						icon: 'success',
						title: 'Informações salvas com sucesso!'
					})
				});
			}
			break
		case 'protestojud':
			let { value: resultprotestojud } = await Swal.fire({
				title: 'protestojud',
				html:
					'Ao criar novo título, se existir processo na memória, ele será utilizado no preenchimento automático dos campos.<br><br>' +
					'<input type="checkbox" id="swal2-checkbox"' + (preferencias.modulo9.protestojud ? ' checked ' : '') + '>' +
					'<label for="swal2-checkbox" class="swal2-label"> Ativar</label>',
				focusConfirm: false,
				confirmButtonText: 'Salvar',
				width: 800,
				preConfirm: () => {
					return [document.getElementById('swal2-checkbox').checked];
				}
			});

			if (resultprotestojud) {
				preferencias.modulo9.protestojud = resultprotestojud[0];
				await guardarModulo9();
				document.getElementById("convenio_protestojud").style.backgroundColor = (preferencias.modulo9.protestojud) ? '#2196F3' : '#b0b0b0';
			}
			break
		case 'sniper':
			let { value: resultsniper } = await Swal.fire({
				title: 'SNIPER',
				html:
			'A extensão leva a varinha mágica para dentro do SNIPER permitindo a consulta do Executado escolhido. Deve ser escolhido um executado por vez. A extensão também traz o Assistente de impressão.<br><br>' +
					'<input type="checkbox" id="swal2-checkbox"' + (preferencias.modulo9.protestojud ? ' checked ' : '') + '>' +
					'<label for="swal2-checkbox" class="swal2-label"> Ativar</label>',
				focusConfirm: false,
				confirmButtonText: 'Salvar',
				width: 800,
				preConfirm: () => {
					return [document.getElementById('swal2-checkbox').checked];
				}
			});

			if (resultsniper) {
				preferencias.modulo9.sniper = resultsniper[0];
				await guardarModulo9();
				document.getElementById("convenio_sniper").style.backgroundColor = (preferencias.modulo9.sniper) ? '#2196F3' : '#b0b0b0';
			}
			break
		case 'censec':
			let { value: resultcensec } = await Swal.fire({
				title: 'CENSEC',
				html:
			'A extensão leva a varinha mágica para dentro do CENSEC permitindo a consulta do Executado escolhido. Deve ser escolhido um executado por vez. A extensão também traz o Assistente de impressão.<br><br>' +
					'<input type="checkbox" id="swal2-checkbox"' + (preferencias.modulo9.censec ? ' checked ' : '') + '>' +
					'<label for="swal2-checkbox" class="swal2-label"> Ativar</label>',
				focusConfirm: false,
				confirmButtonText: 'Salvar',
				width: 800,
				preConfirm: () => {
					return [document.getElementById('swal2-checkbox').checked];
				}
			});

			if (resultcensec) {
				preferencias.modulo9.censec = resultcensec[0];
				await guardarModulo9();
				document.getElementById("convenio_censec").style.backgroundColor = (preferencias.modulo9.censec) ? '#2196F3' : '#b0b0b0';
			}
			break
		case 'celesc':
			let { value: resultcelesc } = await Swal.fire({
				title: 'CELESC (Exclusivo TRT12)',
				html:
			'A extensão leva a varinha mágica para dentro do convênio CELESC permitindo a consulta do Executado escolhido. Deve ser escolhido um executado por vez. A extensão também traz o Assistente de impressão. CONVÊNIO EXCLUSIVO do TRT12.<br><br>' +
					'<input type="checkbox" id="swal2-checkbox"' + (preferencias.modulo9.celesc ? ' checked ' : '') + '>' +
					'<label for="swal2-checkbox" class="swal2-label"> Ativar</label>',
				focusConfirm: false,
				confirmButtonText: 'Salvar',
				width: 800,
				preConfirm: () => {
					return [document.getElementById('swal2-checkbox').checked];
				}
			});

			if (resultcelesc) {
				preferencias.modulo9.celesc = resultcelesc[0];
				await guardarModulo9();
				document.getElementById("convenio_celesc").style.backgroundColor = (preferencias.modulo9.celesc) ? '#2196F3' : '#b0b0b0';
			}
			break
		case 'casan':
			let { value: resultcasan } = await Swal.fire({
				title: 'CASAN (Exclusivo TRT12)',
				html:
			'A extensão leva a varinha mágica para dentro do convênio CASAN permitindo a consulta do Executado escolhido. Deve ser escolhido um executado por vez. A extensão também traz o Assistente de impressão. CONVÊNIO EXCLUSIVO do TRT12.<br><br>' +
					'<input type="checkbox" id="swal2-checkbox"' + (preferencias.modulo9.casan ? ' checked ' : '') + '>' +
					'<label for="swal2-checkbox" class="swal2-label"> Ativar</label>',
				focusConfirm: false,
				confirmButtonText: 'Salvar',
				width: 800,
				preConfirm: () => {
					return [document.getElementById('swal2-checkbox').checked];
				}
			});

			if (resultcasan) {
				preferencias.modulo9.casan = resultcasan[0];
				await guardarModulo9();
				document.getElementById("convenio_casan").style.backgroundColor = (preferencias.modulo9.casan) ? '#2196F3' : '#b0b0b0';
			}
			break
		case 'sigef':
			let { value: resultsigef } = await Swal.fire({
				title: 'SIGEF',
				html:
			'A extensão leva a varinha mágica para dentro do convênio SIGEF (INCRA) permitindo a consulta do Executado escolhido. Deve ser escolhido um executado por vez. A extensão também traz o Assistente de impressão.<br><br>' +
					'<input type="checkbox" id="swal2-checkbox"' + (preferencias.modulo9.sigef ? ' checked ' : '') + '>' +
					'<label for="swal2-checkbox" class="swal2-label"> Ativar</label>',
				focusConfirm: false,
				confirmButtonText: 'Salvar',
				width: 800,
				preConfirm: () => {
					return [document.getElementById('swal2-checkbox').checked];
				}
			});

			if (resultsigef) {
				preferencias.modulo9.sigef = resultsigef[0];
				await guardarModulo9();
				document.getElementById("convenio_sigef").style.backgroundColor = (preferencias.modulo9.sigef) ? '#2196F3' : '#b0b0b0';
			}
			break
		case 'infoseg':
			let { value: resultinfoseg } = await Swal.fire({
				title: 'INFOSEG',
				html:
			'A extensão leva a varinha mágica para dentro do convênio INFOSEG permitindo a consulta do Executado escolhido. Deve ser escolhido um executado por vez.<br><br>' +
					'<input type="checkbox" id="swal2-checkbox"' + (preferencias.modulo9.infoseg ? ' checked ' : '') + '>' +
					'<label for="swal2-checkbox" class="swal2-label"> Ativar</label>',
				focusConfirm: false,
				confirmButtonText: 'Salvar',
				width: 800,
				preConfirm: () => {
					return [document.getElementById('swal2-checkbox').checked];
				}
			});

			if (resultinfoseg) {
				preferencias.modulo9.infoseg = resultinfoseg[0];
				await guardarModulo9();
				document.getElementById("convenio_infoseg").style.backgroundColor = (preferencias.modulo9.infoseg) ? '#2196F3' : '#b0b0b0';
			}
			break
		case 'ecarta':
			let { value: resultecarta } = await Swal.fire({
				title: 'ECARTA',
				html:
					'A extensão busca o processo automaticamente na tela de "Relatório de Objetos por Processo".<br><br>' +
					'<input type="checkbox" id="swal2-checkbox"' + (preferencias.modulo9.ecarta[0] ? ' checked ' : '') + '>' +
					'<label for="swal2-checkbox" class="swal2-label"> Ativar</label>' +
					'<div style="background-color: #95959512;padding: 10px;border-radius: 10px;"><label style="font-weight: bold;" for="swal-input1"> Endereço para consulta de AR </label>' +
					'<input id="swal-input1" class="swal2-input" style="background-color: white;" value="' + preferencias.modulo9.ecarta[1] + '"></div>' +
					'<div style="display: grid;text-align: left;"><span style="font-weight: normal;font-size: 0.8em;color: cadetblue;">Exemplos de links:</span><br>' +
					'<div style="display: grid;text-align: left;"><span style="font-weight: normal;font-size: 0.8em;color: cadetblue;"><u>E-Carta impressão:</u> https://pje.trt12.jus.br/eCarta-web/impressaoDetalhesObjeto.xhtml?codigo=  </span><br>' +
					'<span style="font-weight: normal;font-size: 0.8em;color: cadetblue;"><u> E-carta consulta:</u> https://pje.trt12.jus.br/eCarta-web/consultarObjeto.xhtml?codigo=  </span><br>' +
					'<span style="font-weight: normal;font-size: 0.8em;color: cadetblue;"><u>Site dos Correios:</u> https://rastreamento.correios.com.br/app/index.php?Registros=  </span><span>...</span>' +
					'<span style="font-weight: normal;font-size: 0.8em;color: darkorange;"><b>Tenha atenção que os links variam de acordo com o Tribunal e a versão do E-Carta. </b></span></div>' ,
				focusConfirm: false,
				confirmButtonText: 'Salvar',
				width: 800,
				preConfirm: () => {
					return [document.getElementById('swal2-checkbox').checked,document.getElementById('swal-input1').value];
				}
			});

			if (resultecarta) {
				preferencias.modulo9.ecarta[0] = resultecarta[0];
				preferencias.modulo9.ecarta[1] = resultecarta[1];
				await guardarModulo9();
				document.getElementById("convenio_ecarta").style.backgroundColor = (preferencias.modulo9.ecarta) ? '#2196F3' : '#b0b0b0';
			}
			break
		case 'saj':
			let { value: resultsaj } = await Swal.fire({
				title: 'SAJ (AFASTAMENTO DE SIGILO BANCÁRIO)',
				html:
				'A extensão leva a varinha mágica para dentro do SAJ (AFASTAMENTO DE SIGILO BANCÁRIO). Com isso na tela de cadastro de nova ordem, ao acioná-la, basta escolher os executados para pesquisa e pronto, a extensão faz a inclusão de todos pra você.Ela também preenche o número do processo nas telas de consulta e cancelamento para facilitar a busca.<br><br>' +
				'<input type="checkbox" id="swal2-checkbox"' + (preferencias.modulo9.saj ? ' checked ' : '') + '>' +
				'<label for="swal2-checkbox" class="swal2-label"> Ativar</label><div style="display: grid;grid-template-columns: 1fr 1fr;align-items: center;">' +
				'<label for="swal-input1" style="font-weight: bold;"> Vara da ordem: </label>' +
				'<input id="swal-input1" class="swal2-input"" value="' + preferencias.saj.vara + '">' +
				'<label for="swal-input2" style="font-weight: bold;"> Juiz solicitante da Ordem: </label>' +
				'<input id="swal-input2" class="swal2-input"" value="' + preferencias.saj.juiz + '" style="margin-bottom: 0;">' +
				'<span style="font-weight: bold;" aria-hidden="true"> </span>' +
				'<span style="font-weight: normal;font-size: 0.8em;color: cadetblue;"> Para usar a regra do Módulo 8 digite: MODULO8 </span>' +
				'<label for="swal-input3" style="font-weight: bold;"> Prazo da resposta: </label>' +
				'<input id="swal-input3" class="swal2-input"" value="' + preferencias.saj.prazoResposta + '">' +
				'<span style="font-weight: bold;"> Informações Solicitadas </span>' +
				'<span style="font-weight: bold;" aria-hidden="true"> </span>' +
				'<label for="swal2-extratomercantil" class="swal2-label" style="text-align: right; padding: 20px 0 10px 0;"> Extrato Mercantil </label>' +
				'<span style="text-align: left; padding: 20px 0 10px 0;"><input type="checkbox" id="swal2-extratomercantil"' + (preferencias.saj.extratomercantil ? ' checked ' : '') + ' style="cursor: pointer;height: 25px;width: 25px;"></span>' +
				'<label for="swal2-extratomovimentacao" class="swal2-label" style=" padding: 10px 0;text-align: right;"> Extrato de movimentação - Carta-Circular 3454 (Simba)</label>' +
				'<span style="text-align: left; padding: 10px 0;"><input type="checkbox" id="swal2-extratomovimentacao"' + (preferencias.saj.extratomovimentacao ? ' checked ' : '') + ' style="cursor: pointer;height: 25px;width: 25px;"></span>' +
				'<label for="swal2-extratomovfinanceira" class="swal2-label" style=" padding: 10px 0;text-align: right;"> Extrato de aplicações financeiras</label>' +
				'<span style="text-align: left; padding: 10px 0;"><input type="checkbox" id="swal2-extratomovfinanceira"' + (preferencias.saj.extratomovfinanceira ? ' checked ' : '') + ' style="cursor: pointer;height: 25px;width: 25px;"></span>' +
				'<label for="swal2-faturacartaocredito" class="swal2-label" style=" padding: 10px 0;text-align: right;"> Fatura de cartão de crédito</label>' +
				'<span style="text-align: left; padding: 10px 0;"><input type="checkbox" id="swal2-faturacartaocredito"' + (preferencias.saj.faturacartaocredito ? ' checked ' : '') + ' style="cursor: pointer;height: 25px;width: 25px;"></span>' +
				'<label for="swal2-propostaaberturaconta" class="swal2-label" style=" padding: 10px 0;text-align: right;"> Proposta de abertura de conta</label>' +
				'<span style="text-align: left; padding: 10px 0;"><input type="checkbox" id="swal2-propostaaberturaconta"' + (preferencias.saj.propostaaberturaconta ? ' checked ' : '') + ' style="cursor: pointer;height: 25px;width: 25px;"></span>' +
				'<label for="swal2-contratocambio" class="swal2-label" style=" padding: 10px 0;text-align: right;"> Contrato de Câmbio</label>' +
				'<span style="text-align: left; padding: 10px 0;"><input type="checkbox" id="swal2-contratocambio"' + (preferencias.saj.contratocambio ? ' checked ' : '') + ' style="cursor: pointer;height: 25px;width: 25px;"></span>' +
				'<label for="swal2-registrocambio" class="swal2-label" style=" padding: 10px 0;text-align: right;"> Registro de Câmbio</label>' +
				'<span style="text-align: left; padding: 10px 0;"><input type="checkbox" id="swal2-registrocambio"' + (preferencias.saj.registrocambio ? ' checked ' : '') + ' style="cursor: pointer;height: 25px;width: 25px;"></span>' +
				'<label for="swal2-copiacheque" class="swal2-label" style=" padding: 10px 0;text-align: right;"> Cópia de cheque</label>' +
				'<span style="text-align: left; padding: 10px 0;"><input type="checkbox" id="swal2-copiacheque"' + (preferencias.saj.copiacheque ? ' checked ' : '') + ' style="cursor: pointer;height: 25px;width: 25px;"></span>' +
				'<label for="swal2-saldofgts" class="swal2-label" style="padding: 10px 0;text-align: right;"> Saldos do FGTS e do PIS</label>' +
				'<span style="text-align: left; padding: 10px 0;"><input type="checkbox" id="swal2-saldofgts"' + (preferencias.saj.saldofgts ? ' checked ' : '') + ' style="cursor: pointer;height: 25px;width: 25px;"></span>' +
				'<label for="swal2-recebernotificacao" class="swal2-label" style="text-align: right;padding: 10px 0 20px 0;"> Receber as notificações de respostas por e-mail</label>' +
				'<span style="text-align: left; padding: 10px 0 20px 0;"><input type="checkbox" id="swal2-recebernotificacao"' + (preferencias.saj.recebernotificacao ? ' checked ' : '') + ' style="cursor: pointer;height: 25px;width: 25px;"></span>' +
				'<label for="swal-input4" style="font-weight: bold;"> E-mail institucional: </label>' +
				'<input id="swal-input4" class="swal2-input"" value="' + preferencias.saj.email + '">' +
				'<label for="swal-input5" style="font-weight: bold;"> Telefone para contato: </label>' +
				'<input id="swal-input5" class="swal2-input"" value="' + preferencias.saj.telefone + '">' +
				'</div>',
				focusConfirm: false,
				confirmButtonText: 'Salvar',
				width: 800,
				preConfirm: () => {
					return [
						document.getElementById('swal2-checkbox').checked,
						document.getElementById('swal-input1').value,
						document.getElementById('swal-input2').value,
						document.getElementById('swal-input3').value,
						document.getElementById('swal2-extratomercantil').checked,
						document.getElementById('swal2-extratomovimentacao').checked,
						document.getElementById('swal2-extratomovfinanceira').checked,
						document.getElementById('swal2-faturacartaocredito').checked,
						document.getElementById('swal2-propostaaberturaconta').checked,
						document.getElementById('swal2-contratocambio').checked,
						document.getElementById('swal2-registrocambio').checked,
						document.getElementById('swal2-copiacheque').checked,
						document.getElementById('swal2-saldofgts').checked,
						document.getElementById('swal2-recebernotificacao').checked,
						document.getElementById('swal-input4').value,
						document.getElementById('swal-input5').value
					]
				}
			});

			if (resultsaj) {
				preferencias.modulo9.saj = resultsaj[0];
				await guardarModulo9();
				document.getElementById("convenio_saj").style.backgroundColor = (preferencias.modulo9.saj) ? '#2196F3' : '#b0b0b0';

				preferencias.saj = {
					vara: resultsaj[1],
					juiz: resultsaj[2],
					prazoResposta: resultsaj[3],
					extratomercantil: resultsaj[4],
					extratomovimentacao: resultsaj[5],
					extratomovfinanceira: resultsaj[6],
					faturacartaocredito: resultsaj[7],
					propostaaberturaconta: resultsaj[8],
					contratocambio: resultsaj[9],
					registrocambio: resultsaj[10],
					copiacheque: resultsaj[11],
					saldofgts: resultsaj[12],
					recebernotificacao: resultsaj[13],
					email: resultsaj[14],
					telefone: resultsaj[15],
				};
				let var1_saj = browser.storage.local.set({'saj': preferencias.saj});
				Promise.all([var1_saj]).then(values => {
					let Toast = Swal.mixin({
						toast: true,
						position: 'bottom-end',
						showConfirmButton: false,
						timer: 1500,
						timerProgressBar: true,
						onOpen: (toast) => {
						toast.addEventListener('mouseenter', Swal.stopTimer)
						toast.addEventListener('mouseleave', Swal.resumeTimer)
						}
					})
					Toast.fire({
						icon: 'success',
						title: 'Informações salvas com sucesso!'
					})
				});
			}
			break
	}
}

async function guardarModulo9() {
	return new Promise(
		resolver => {
			let var1_modulo9 = browser.storage.local.set({'modulo9': preferencias.modulo9});
			let var1_tempAuto = browser.storage.local.set({'tempAuto': preferencias.tempAuto});
			Promise.all([var1_modulo9,var1_tempAuto]).then(values => {
				let Toast = Swal.mixin({
					toast: true,
					position: 'bottom-end',
					showConfirmButton: false,
					timer: 1500,
					timerProgressBar: true,
					onOpen: (toast) => {
					toast.addEventListener('mouseenter', Swal.stopTimer)
					toast.addEventListener('mouseleave', Swal.resumeTimer)
					}
				})
				Toast.fire({
					icon: 'success',
					title: 'Informações salvas com sucesso!'
				})
				resolver(true);
			});
		}
	);
}

//modulo 10
async function montar_modulo10() {
	let ancora = document.getElementById('lista_modulo10');
	ancora.textContent = "";

	//cabeçalho
	let trh = document.createElement('tr');
	trh.className = "textoItalico";
	trh.style = "font-weight: bold;";
	let td1h = document.createElement('td');
	td1h.style = "width: 10vw; text-align: center;";
	td1h.innerText = "Horário";
	let td2h = document.createElement('td');
	td2h.style = "width: 40vw;";
	td2h.innerText = "Link da audiência";
	let td3h = document.createElement('td');
	td3h.style = "width: 10vw; text-align: center;";
	td3h.innerText = "Sala";
	trh.appendChild(td1h);
	trh.appendChild(td3h);
	trh.appendChild(td2h);
	ancora.appendChild(trh);

	for (const [pos, item] of listaModulo10_temp.entries()) {
		let h = (!item.horario) ? "" : item.horario;
		let e = (!item.url) ? "" : item.url;
		let s = (!item.sala) ? "" : item.sala;
		await inserirlinha(h,s,e);
	}

	await inserirlinha();

	async function inserirlinha(horario="",sala="",url="",foco=false) {
		let tr = document.createElement('tr');
		tr.id = "lista_modulo10_item"
		let td1 = document.createElement('td');
		let input1 = document.createElement('input');
		input1.id = "horario";
		input1.className = "swal2-input";
		input1.type = "text";
		input1.value = horario;
		input1.addEventListener('focusout', function(event) {
			if (document.querySelectorAll('tr[id="lista_modulo10_item"]').length <= listaModulo10_temp.length) { inserirlinha('','','',true) }
			salvarOpcoes();
		});
		td1.appendChild(input1);

		let td2 = document.createElement('td');
		let input2 = document.createElement('input');
		input2.id = "url";
		input2.className = "swal2-input";
		input2.type = "text";
		input2.value = url;
		input2.addEventListener('focusout', function(event) {
			if (document.querySelectorAll('tr[id="lista_modulo10_item"]').length <= listaModulo10_temp.length) { inserirlinha('','','',true) }
			salvarOpcoes();
		});
		td2.appendChild(input2);

		let td3 = document.createElement('td');
		let input3 = document.createElement('input');
		input3.id = "sala";
		input3.className = "swal2-input";
		input3.type = "text";
		input3.value = sala;
		input3.addEventListener('focusout', function(event) {
			if (document.querySelectorAll('tr[id="lista_modulo10_item"]').length <= listaModulo10_temp.length) { inserirlinha('','','',true) }
			salvarOpcoes();
		});
		td3.appendChild(input3);

		tr.appendChild(td1);
		tr.appendChild(td3);
		tr.appendChild(td2);
		ancora.appendChild(tr);

		if (foco) {
			input1.focus();
		}
	}
}

async function ativarJuntadaDeMidia() {
	let inputValue = '';
	if (document.querySelector('#modulo10_juntadaMidia').checked) {

		const { value: result } = await Swal.fire({
			inputLabel: "Digite o nome do modelo de certidão que será utilizada para anexar os vídeos(depoimentos)",
			input: "text",
			inputValue,
			showCancelButton: true,
			inputValidator: (value) => {
				if (!value) {
					return "Você precisa apontar o modelo de certidão de juntada de mídia!!";
				}
			}
		});

		if (result) {
			preferencias.modulo10_juntadaMidia = [true,result];
		} else {
			preferencias.modulo10_juntadaMidia = [false,''];
			document.querySelector('#modulo10_juntadaMidia').checked = false;

		}
	} else {
		preferencias.modulo10_juntadaMidia = [false,''];
	}



	let var1 = browser.storage.local.set({'modulo10_juntadaMidia': preferencias.modulo10_juntadaMidia});
	Promise.all([var1]).then(values => {
		let Toast = Swal.mixin({
			toast: true,
			position: 'bottom-end',
			showConfirmButton: false,
			timer: 1500,
			timerProgressBar: true,
			onOpen: (toast) => {
			toast.addEventListener('mouseenter', Swal.stopTimer)
			toast.addEventListener('mouseleave', Swal.resumeTimer)
			}
		})
		Toast.fire({
			icon: 'success',
			title: 'Informações salvas com sucesso!'
		})
	});
}

//modulo 11
async function montar_modulo11() {
	// console.log('montar_modulo8: ' + listaModulo8_temp)
	let ancora = document.getElementById('lista_modulo11');
	ancora.textContent = "";
	for (const [pos, item] of listaModulo11_temp.entries()) {

		let tr = document.createElement("tr");
		tr.className = 'linha-zebrada';
		tr.style = "display: grid; grid-template-columns: 6% 9% 10% 70% 5%;padding: 5px;";

		let td1 = document.createElement("td");
		td1.style = "font-weight: bold";
		td1.innerText = "|___Regra " + (pos+1) + ":";
		tr.appendChild(td1);

		let td2 = document.createElement("td");
		td2.style = "text-align: center";
		td2.innerText = item.cnpj;
		tr.appendChild(td2);

		let td3 = document.createElement("td");
		td3.innerText = item.observacao;
		tr.appendChild(td3);

		let td4 = document.createElement("td");
		td4.innerText = item.cabecalho;
		tr.appendChild(td4);

		//*********criar botão editar
		let div_editar = document.createElement("div");
		div_editar.setAttribute("data-tooltip", "Editar");
		let bt_editar = document.createElement("i");
		bt_editar.className = "icone edit t16";
		bt_editar.style = "padding: 0 5px 0 5px;"
		bt_editar.setAttribute("pos",pos);
		bt_editar.onmouseenter = function() {
			this.style.setProperty("background-color","rgb(0, 120, 170)");
			this.parentElement.parentElement.parentElement.style.outline = '2px solid #2778c4';
		}
		bt_editar.onmouseleave = function () {
			this.style.setProperty("background-color","black");
			this.parentElement.parentElement.parentElement.style.outline = 'none';
		};
		bt_editar.onclick = function () {
			editar_regra_modulo11(parseInt(this.getAttribute("pos")))
		};
		div_editar.appendChild(bt_editar);

		//*********criar botão excluir
		let div_excluir = document.createElement("div");
		div_excluir.setAttribute("data-tooltip", "Excluir");
		let bt_excluir = document.createElement("i");
		bt_excluir.className = "icone trash-alt t16";
		bt_excluir.style = "padding: 0 5px 0 5px;"
		bt_excluir.setAttribute("pos",pos);
		bt_excluir.onmouseenter = function() {
			this.style.setProperty("background-color","rgb(0, 120, 170)");
			this.parentElement.parentElement.parentElement.style.outline = '2px solid #2778c4';
		}
		bt_excluir.onmouseleave = function (e) {
			this.style.setProperty("background-color","black");
			this.parentElement.parentElement.parentElement.style.outline = 'none';
		};
		bt_excluir.onclick = function () {
			listaModulo11_temp.splice(parseInt(this.getAttribute("pos")), 1);
			montar_modulo11();
			salvarOpcoes();
		};
		div_excluir.appendChild(bt_excluir);

		let td6 = document.createElement("td");
		td6.style = "display: inline-flex;margin-left: auto;";
		td6.appendChild(div_editar);
		td6.appendChild(div_excluir);
		tr.appendChild(td6);

		ancora.appendChild(tr);
	}
}

async function editar_regra_modulo11(pos) {
	let item = listaModulo11_temp[pos];
	Swal.fire({
		title: '    ',
		html:
			'<span>CNPJ:</span><br>' +
			'<input type="text" id="modulo11_cnpjRJ" class="swal2-input" placeholder="00.000.000/0000-00" value="' + item.cnpj + '">' +
			'<br><br>' +
			'<span>Observação:</span><br>' +
			'<input type="text" id="modulo11_observacao" class="swal2-input" value="' + item?.observacao + '">' +
			'<br><br>' +
			'<span>Cabeçalho da Certidão:</span><br>' +
			'<textarea id="modulo11_cabecalhoRJ" class="swal2-textarea" style="height: 40vh;">' + item.cabecalho + '</textarea>',
		focusConfirm: false,
		width: 800,
		confirmButtonText: 'Salvar',
		preConfirm: () => {
			let inputCnpj = document.getElementById('modulo11_cnpjRJ').value;
			let erroFormulario = false;
			//mascara do input do CNPJ
			inputCnpj = inputCnpj.replace(/\D/g, "");
			if (!inputCnpj) {
				return '';
			} else if (inputCnpj.length == 14) { //completo sem pontos e traços
				inputCnpj = inputCnpj.replace(/(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})/, "$1.$2.$3/$4-$5");
				let resposta = {cnpj:inputCnpj,observacao:document.getElementById('modulo11_observacao').value,cabecalho:document.getElementById('modulo11_cabecalhoRJ').value};

				//verificar se o cnpj já existe
				let listaTemp = [...listaModulo11_temp]
				listaTemp.splice(pos,1);
				let existeRegra = listaTemp.find(regra => regra.cnpj == inputCnpj);
				if (existeRegra) {
					return 'erro:Já existe regra para este CNPJ!';
				} else {
					return resposta;
				}

			} else { erroFormulario = true }

			if (erroFormulario) {
				return 'erro:CNPJ inválido!';
			}
		}
	}).then((result) => {

		if (typeof result.value === 'object') {
			listaModulo11_temp[pos] = result.value;
			montar_modulo11();
			salvarOpcoes();
		} else if (result.value == '' || result.isDismissed || result.isDenied) {

		} else if (result.value.includes('erro:')) {
			result.value = result.value.replace('erro:','');
			Swal.fire(result.value, "", "info");
		}
	});
}

async function criarRegra_modulo11() {
	let cabecalhoRJ = 'Certifico que, para fins de habilitação de créditos perante o Administrador Judicial, Sr. XXX, ';
	cabecalhoRJ += 'nomeado nos autos da Ação de Recuperação Judicial nº XXX, que tramita na XXX, passa esta Secretaria';
	cabecalhoRJ += ' a expedir CERTIDÃO DE HABILITAÇÃO DE CRÉDITO, observando os termos do parágrafo único do art. 1º do';
	cabecalhoRJ += ' Provimento CGJT 01/2012 c/c art. 80 da Consolidação dos Provimentos da Corregedoria-Geral da Justiça';
	cabecalhoRJ += ' do Trabalho, publicada no dia 24 de fevereiro de 2016.';

	Swal.fire({
		title: '    ',
		html:
			'<span>CNPJ:</span><br>' +
			'<input type="text" id="modulo11_cnpjRJ" class="swal2-input" placeholder="00.000.000/0000-00" value="">' +
			'<br><br>' +
			'<span>Observação:</span><br>' +
			'<input type="text" id="modulo11_observacao" class="swal2-input" value="">' +
			'<br><br>' +
			'<span>Cabeçalho da Certidão:</span><br>' +
			'<textarea id="modulo11_cabecalhoRJ" class="swal2-textarea" style="height: 40vh;">' + cabecalhoRJ + '</textarea>',
		focusConfirm: false,
		width: 800,
		confirmButtonText: 'Salvar',
		preConfirm: () => {
			let inputCnpj = document.getElementById('modulo11_cnpjRJ').value;
			let erroFormulario = false;
			//mascara do input do CNPJ
			inputCnpj = inputCnpj.replace(/\D/g, "");
			if (!inputCnpj) {
				return '';
			} else if (inputCnpj.length == 14) { //completo sem pontos e traços
				inputCnpj = inputCnpj.replace(/(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})/, "$1.$2.$3/$4-$5");
				let resposta = {cnpj:inputCnpj,observacao:document.getElementById('modulo11_observacao').value,cabecalho:document.getElementById('modulo11_cabecalhoRJ').value};
				//verificar se o cnpj já existe
				let existeRegra = listaModulo11_temp.find(regra => regra.cnpj == inputCnpj);
				if (existeRegra) {
					return 'erro:Já existe regra para este CNPJ!';
				} else {
					return resposta;
				}

			} else { erroFormulario = true }

			if (erroFormulario) {
				return 'erro:CNPJ inválido!';
			}
		}
	}).then((result) => {
		if (typeof result.value === 'object') {
			listaModulo11_temp.push(result.value);
			montar_modulo11();
			salvarOpcoes();
		} else if (result.value == '' || result.isDismissed || result.isDenied) {

		} else if (result.value.includes('erro:')) {
			result.value = result.value.replace('erro:','');
			Swal.fire(result.value, "", "info");
		}
	});
}

async function aa_anexar_documentos() {
	let temp = [];
	Swal.mixin({
		input: 'text',
		confirmButtonText: 'Próximo &rarr;',
		showCancelButton: true,
		progressSteps: ['1', '2', '3', '4', '5', '6', '7']
	}).queue([
	{
		title: 'Nome do Botão',
		text: ''
	},
	{
		title: 'Tipo de Documento',
		html: 'Exemplos:<br>Certidão<br>BacenJud (bloqueio)<br>Renajud (consulta)<br>Documento Diverso'
	},
	{
		title: 'Descrição (Título)',
		text: 'Título que aparece na linha do tempo do processo',
		preConfirm: () => {

			//COMANDO PARA ESCONDER O INPUT DO PRÓXIMO PASSO
			setTimeout(function() {
				document.querySelector('div[class="swal2-content"] input[class="swal2-input"]').style.display = 'none';
			}, 50);

		}
	},
	{
		title: 'Sigilo',
		html:
		'<select id="swal-input4" class="swal2-select" style="background-color: white;width: 50%;">' +
			'<option value="nao" selected> Não </option>' +
			'<option value="sim"> Sim </option>' +
		'</select>' +
		'<select id="swal-input4-1" class="swal2-select" style="background-color: white;width: 50%;">' +
			'<optgroup label="Visibilidade do Documento">' +
			'<option value="Nenhum" selected> Nenhum </option>' +
			'<option value="Polo Ativo"> Apenas Polo Ativo </option>' +
			'<option value="Polo Passivo"> Apenas Polo Passivo </option>' +
			'<option value="Polo Ativo + Polo Passivo"> Polo Ativo + Polo Passivo </option>' +
			'<option value="Perito"> Apenas Perito </option>' +
			'<option value="Todos"> Polo Ativo + Polo Passivo + Perito </option>' +
			'<option value="Perguntar"> Perguntar </option>' +
			'</optgroup>' +
		'</select>',
		preConfirm: () => {
			document.querySelector('input[class*="swal2-input"]').style.display = 'none';
			let sw4 = document.getElementById('swal-input4').value.toLowerCase();
			let sw41 = document.getElementById('swal-input4-1').value.toLowerCase();
			if (sw4.toLowerCase().includes('sim')) {
				if (!sw4.includes('[') && !sw4.includes(']')) {
					switch (sw41) {
						case 'nenhum':
							break;
						case 'polo ativo':
							sw4 += "[Polo Ativo]";
							break;
						case 'polo passivo':
							sw4 += "[Polo Passivo]";
							break;
						case 'polo ativo + polo passivo':
							sw4 += "[Polo Ativo Polo Passivo]";
							break;
						case 'perito':
							sw4 += "[Perito]";
							break;
						case 'todos':
							sw4 += "[Polo Ativo Polo Passivo Perito]";
							break;
						case 'perguntar':
							sw4 += "[Perguntar]";
						break;
					}
				}
			}
			return sw4;
		}
	},
	{
		title: 'Modelo',
		text: 'Caso seja um arquivo em pdf digite apenas PDF'
	},
	{
		title: 'Assinar automaticamente',
		input: 'select',
		inputOptions: {
			'Sim': 'Sim',
			'Não': 'Não',
		}
	}
	]).then((result) => {
		if (result.value) {
			temp = result.value;
			color();
		}
	})

	async function color() {
		const { value: result } = await Swal.fire({
			title: '    ',
			html:
			'<span style="font-weight: bold;"> Cor do Botão </span>' +
			'<input id="swal-input1" class="swal2-input" type="color" value="#3085d6">',
			focusConfirm: true,
			preConfirm: () => {
				return [
					document.getElementById('swal-input1').value
				]
			}
		});

		if (result) {
			criaBotao_aaAnexar(aaAnexar_temp.length, temp[0], temp[1], temp[2], temp[3], temp[4], temp[5], result[0], 'Nenhum', 'sim');
			aaAnexar_temp.push(new AcaoAutomatizada_aaAnexar(temp[0], temp[1], temp[2], temp[3], temp[4], temp[5], result[0], 'Nenhum', 'sim'));
			salvarOpcoes();
		}
	}
}

async function aa_comunicacao() {
	let temp = [];
	Swal.mixin({
		input: 'text',
		confirmButtonText: 'Próximo &rarr;',
		showCancelButton: true,
		progressSteps: ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10']
	}).queue([
	{
		title: 'Nome do Botão',
		text: ''
	},
	{
		title: 'Tipo de Expediente',
		html: 'Exemplos:<br>Intimação<br>Mandado<br>Notificação inicial<br>Ofício<br>Edital'
	},
	{
		title: 'Prazo',
		html: 'Pode ser em número de dias úteis ou uma data.<br>Exemplo: 01/01/2021<br><br><i style="color:cadetblue;">Para dias corridos, acrescente a expressão dc depois do prazo.<br><br>Por exemplo: <b>60dc</b> é igual a 60 dias corridos.</i>'
	},
	{
		title: 'SubTipo de Expediente',
		html: 'Cada tipo de expediente possui um subtipo dentro da janela de edição. Por exemplo:<br>Mandado, na tela de edição do mandado aparecem os subtipos "Mandado", "Mandado Proibitório", Mandado de Arresto de Bem", Mandado de Averbação", "Mandado de Citação", etc...'
	},
	{
		title: 'Descrição (Título)',
		text: 'Título que aparece na linha do tempo do processo'
	},
	{
		title: 'Sigilo',
		input: 'select',
		inputOptions: {
			'Sim': 'Sim',
			'Não': 'Não',
		},
		inputValue: 'Não',
	},
	{
		title: 'Modelo',
		text: ''
	},
	{
		title: 'Salvar automaticamente',
		input: 'select',
		inputOptions: {
			'Sim': 'Sim',
			'Não': 'Não',
		}
	},
	{
		title: 'Mover para a Tarefa "Preparar Comunicação/Expediente"?',
		input: 'select',
		inputOptions: {
			'Sim': 'Sim',
			'Não': 'Não',
		}
	}
	]).then((result) => {
		if (result.value) {
			temp = result.value;
			color();
		}
	});

	async function color() {
		const { value: result } = await Swal.fire({
			title: '    ',
			html:
			'<span style="font-weight: bold;"> Cor do Botão </span>' +
			'<input id="swal-input1" class="swal2-input" type="color" value="#D2691E">',
			focusConfirm: true,
			preConfirm: () => {
				return [
					document.getElementById('swal-input1').value
				]
			}
		});

		if (result) {
			let tipo_prazo = "";
			if (temp[2] != null) {
				if (temp[2].toLowerCase().includes('dc')) {
					tipo_prazo = "Dias Corridos";
					temp[2] = temp[2].replace('dc','');
				} else if (temp[2] == "0") {
					tipo_prazo = "Sem Prazo";
				} else if (temp[2].search("/") > -1) {
					tipo_prazo = "Data Certa";
				} else {
					tipo_prazo = "Dias Úteis";
				}
			}
			criaBotao_aaComunicacao(aaComunicacao_temp.length, temp[0], temp[1], temp[3], tipo_prazo, temp[2], temp[4], temp[5], temp[6], temp[7], result[0], 'Nenhum', temp[8], 'sim');
			aaComunicacao_temp.push(new AcaoAutomatizada_aaComunicacao(temp[0], temp[1], temp[3], tipo_prazo, temp[2], temp[4], temp[5], temp[6], temp[7], result[0], 'Nenhum', temp[8], 'sim'));
			salvarOpcoes();
		}
	}
}

async function aa_autogigs() {
	console.log("aa_autogigs");
	let temp = [];
	let tipo;

	Swal.fire({
		title: 'Tipo de Evento',
		icon: 'question',
		input: 'select',
		inputOptions: {
				'Atividade': 'Atividade',
				'Comentário': 'Comentário',
				'Chip': 'Chip',
				'Lembrete': 'Lembrete',
				'Nenhum': 'Nenhum',
			},
		confirmButtonText: 'Próximo &rarr;',
		showCancelButton: false,
		inputValidator: (value) => {
			return new Promise((resolve) => {
				console.log("Evento: " + value);
				switch (value) {
					case 'Atividade':
						alertAtividade();
						break
					case 'Comentário':
						alertComentario();
						break
					case 'Chip':
						alertChip();
						break
					case 'Lembrete':
						alertLembrete();
						break
					case 'Nenhum':
						alertNenhum();
						break
				}
			})
		}
	});

	async function alertAtividade() {
		Swal.mixin({
			input: 'text',
			confirmButtonText: 'Próximo &rarr;',
			showCancelButton: true,
			cancelButtonText: 'Cancelar',
			progressSteps: ['1', '2', '3', '4', '5', '6', '7', '8']
		}).queue([
		{
			title: 'Nome do Botão',
			text: ''
		},
		{
			title: 'Tipo de Atividade',
			html: 'Exemplos:<br>Acordo<br>Autor<br>Edital<br>Leiloeiro<br>Mandado<br>Ofício<br>Prazo<br>Prescrição Intercorrente'
		},
		{
			title: 'Prazo',
			html: 'Você pode deixar em branco, preencher em número de dias úteis ou uma data específica.<br>Exemplo: 01/01/2021'
		},
		{
			title: 'Responsável pelo GIGS',
			text: ''
		},
		{
			title: 'Responsável pelo Processo',
			text: ''
		},
		{
			title: 'Observação',
			text: 'Se quiser deixar para preencher na hora do lançamento escreva "perguntar"'
		},
		{
			title: 'Salvar automaticamente',
			input: 'select',
			inputOptions: {
				'Sim': 'Sim',
				'Não': 'Não',
			}
		}
		]).then((result2) => {
			if (result2.value) {
				temp = result2.value;
				console.log(temp[2]);
				if (temp[2] != "") {
					tipo = "prazo";
				} else {
					tipo = "preparo";
				}
				color(tipo);
			}
		});
	}

	async function alertComentario() {
		tipo = "comentario";
		Swal.mixin({
			input: 'text',
			confirmButtonText: 'Próximo &rarr;',
			showCancelButton: true,
			cancelButtonText: 'Cancelar',
			progressSteps: ['1', '2', '3', '4', '5', '6']
		}).queue([
		{
			title: 'Nome do Botão',
			text: ''
		},
		{
			title: 'Comentário',
			input: 'textarea',
			html: ''
		},
		{
			title: 'Visibilidade',
			input: 'select',
			inputOptions: {
				'LOCAL': 'LOCAL',
				'RESTRITA': 'RESTRITA',
				'GLOBAL': 'GLOBAL',
			}
		},
		{
			title: 'Responsável pelo Processo',
			text: ''
		},
		{
			title: 'Salvar automaticamente',
			input: 'select',
			inputOptions: {
				'Sim': 'Sim',
				'Não': 'Não',
			}
		}
		]).then((result2) => {
			if (result2.value) {
				temp = result2.value;
				color(tipo);
			}
		});
	}

	async function alertChip() {
		tipo = "chip";
		Swal.mixin({
			input: 'text',
			confirmButtonText: 'Próximo &rarr;',
			showCancelButton: true,
			cancelButtonText: 'Cancelar',
			progressSteps: ['1', '2', '3', '4']
		}).queue([
		{
			title: 'Nome do Botão',
			text: ''
		},
		{
			title: 'Tipo de Chip',
			html: 'Exemplos:<br>Analisar<br>Cálculo - atualização<br>Expedir alvará<br>CTPS - anotar<br>RENAJUD<br>Indisponibilidade de bens<br>Pesquisar Imóveis<br>Incluir em pauta'
		},
		{
			title: 'Salvar automaticamente',
			input: 'select',
			inputOptions: {
				'Sim': 'Sim',
				'Não': 'Não',
			}
		}
		]).then((result2) => {
			if (result2.value) {
				temp = result2.value;
				color(tipo);
			}
		});
	}

	async function alertLembrete() {
		tipo = "lembrete";
		Swal.mixin({
			input: 'text',
			confirmButtonText: 'Próximo &rarr;',
			showCancelButton: true,
			cancelButtonText: 'Cancelar',
			progressSteps: ['1', '2', '3', '4', '5']
		}).queue([
		{
			title: 'Nome do Botão',
			text: ''
		},
		{
			title: 'Descrição (Título)',
			text: ''
		},
		{
			title: 'Visibilidade',
			input: 'select',
			inputOptions: {
				'LOCAL': 'LOCAL',
				'PRIVADO': 'PRIVADO',
				'GLOBAL': 'GLOBAL',
			}
		},
		{
			title: 'Conteúdo do Lembrete',
			input: 'textarea',
		},
		{
			title: 'Salvar automaticamente',
			input: 'select',
			inputOptions: {
				'Sim': 'Sim',
				'Não': 'Não',
			}
		}
		]).then((result2) => {
			if (result2.value) {
				temp = result2.value;
				color(tipo);
			}
		});
	}

	async function alertNenhum() {
		tipo = "nenhum";
		Swal.mixin({
			input: 'text',
			confirmButtonText: 'Próximo &rarr;',
			showCancelButton: true,
			cancelButtonText: 'Cancelar',
			progressSteps: ['1', '2']
		}).queue([
		{
			title: 'Nome do Botão',
			text: ''
		}
		]).then((result) => {
			if (result.value) {
				temp = result.value;
				color(tipo);
			}
		});
	}

	async function color(tipo) {
		let var1 = '#aea705';
		switch (tipo) {
			case 'prazo':
				var1 = '#708090'
				break
			case 'preparo':
				var1 = '#008B8B'
				break
			case 'comentario':
				var1 = '#c71585'
				break
			case 'chip':
				var1 = '#aea705'
				break
			case 'lembrete':
				var1 = '#d9c7a5'
				break
			case 'nenhum':
				var1 = '#CFD0D0'
				break
		}

		const { value: result } = await Swal.fire({
			title: '    ',
			html:
			'<span style="font-weight: bold;"> Cor do Botão </span>' +
			'<input id="swal-input1" class="swal2-input" type="color" value="' + var1 + '">',
			focusConfirm: true,
			preConfirm: () => {
				return [
					document.getElementById('swal-input1').value
				]
			}
		});

		if (result) {
			if (tipo == "prazo" || tipo == "preparo") {
				criaBotao_aaAutogigs(aaAutogigs_temp.length, temp[0], tipo, temp[1], temp[2], temp[3], temp[4], temp[5], temp[6], result[0], 'Nenhum', 'sim');
				aaAutogigs_temp.push(new AcaoAutomatizada_aaAutogigs(temp[0], tipo, temp[1], temp[2], temp[3], temp[4], temp[5], temp[6], result[0], 'Nenhum', 'sim'));
			} else if (tipo == "comentario") {
				console.log('temp[0]: ' + temp[0]); //nome do botão ===  nm_botao
				console.log('temp[1]: ' + temp[1]); //comentario === observacao
				console.log('temp[2]: ' + temp[2]); //visibilidade === prazo
				console.log('temp[3]: ' + temp[3]); //resp processo === responsavel_processo
				console.log('temp[4]: ' + temp[4]); //salvar === salvar
				console.log('temp[5]: ' + result[0]); //cor === cor
				//id, nm_botao, tipo, tipo_atividade, prazo, responsavel, responsavel_processo, observacao, salvar, cor, vinculo, visibilidade
				criaBotao_aaAutogigs(aaAutogigs_temp.length, temp[0], tipo, '', temp[2], '', temp[3], temp[1], temp[4], result[0], 'Nenhum', 'sim');
				//nm_botao, tipo, tipo_atividade, prazo, responsavel, responsavel_processo, observacao, salvar, cor, vinculo, visibilidade='sim'
				aaAutogigs_temp.push(new AcaoAutomatizada_aaAutogigs(temp[0], tipo, '', temp[2], '', temp[3], temp[1], temp[4], result[0], 'Nenhum', 'sim'));
			} else if (tipo == "chip") {
				criaBotao_aaAutogigs(aaAutogigs_temp.length, temp[0], tipo, temp[1], '', '', '', '', temp[2], result[0], 'Nenhum', 'sim');
				aaAutogigs_temp.push(new AcaoAutomatizada_aaAutogigs(temp[0], tipo, temp[1], '', '', '', '', temp[2], result[0], 'Nenhum', 'sim'));
			} else if (tipo == "lembrete") {
				console.log('temp[0]: ' + temp[0]); //nome do botão ===  nm_botao
				console.log('temp[1]: ' + temp[1]); //titulo === tipo_atividade
				console.log('temp[2]: ' + temp[2]); //visibilidade === prazo
				console.log('temp[3]: ' + temp[3]); //conteudo === observacao
				console.log('temp[4]: ' + temp[4]); //salvar === salvar
				console.log('temp[5]: ' + result[0]); //cor === cor
				criaBotao_aaAutogigs(aaAutogigs_temp.length,temp[0],tipo,temp[1],temp[2],'','',temp[3],temp[4],result[0],'Nenhum','sim');
				aaAutogigs_temp.push(new AcaoAutomatizada_aaAutogigs(temp[0],tipo,temp[1],temp[2],'','',temp[3],temp[4],result[0],'Nenhum','sim'));
			} else if (tipo == "nenhum") {
				criaBotao_aaAutogigs(aaAutogigs_temp.length, temp[0], tipo, '', '', '', '', '', '', result[0], 'Nenhum', 'sim');
				aaAutogigs_temp.push(new AcaoAutomatizada_aaAutogigs(temp[0], tipo, '', '', '', '', '', '', result[0], 'Nenhum', 'sim'));
			}
			salvarOpcoes();
			if (tipo == "nenhum") {

			}
		}
	}

}

async function aa_despacho() {
	let temp = [];
	Swal.mixin({
		input: 'text',
		confirmButtonText: 'Próximo &rarr;',
		showCancelButton: true,
		progressSteps: ['1', '2', '3', '4', '5', '6', '7']
	}).queue([
	{
		title: 'Nome do Botão',
		text: ''
	},
	{
		title: 'Tipo',
		text: 'Se deixar em branco, será escolhido o despacho simples. Para definir como decisão ou sentença coloque o texto do botão que você deseja selecionar. Por exemplo: "Admissibilidade de Recursos" ou "Sentença" ou "Sobrestamento / Suspensão", etc.'
	},
	{
		title: 'Descrição (Título)',
		text: 'Título que aparece na linha do tempo do processo'
	},
	{
		title: 'Sigilo',
		input: 'select',
		inputOptions: {
			'Sim': 'Sim',
			'Não': 'Não',
		},
		inputValue: 'Não',
	},
	{
		title: 'Modelo',
		text: ''
	},
	{
		title: 'Juiz',
		text: 'Não é obrigatório. Se deixar em branco, o PJe escolhe para você. Se preencher o nome, ele busca pelo nome. Se quiser o juiz titular do órgão, escreva apenas TITULAR.'
	},
	{
		title: 'Responsável',
		text: 'Atribui a responsabilidade do processo para alguém. Por exemplo: o assessor do juiz.'
	}
	]).then((result) => {
		if (result.value) {
			temp = result.value;
			color();
		}
	});

	async function color() {
		const { value: result } = await Swal.fire({
			title: '    ',
			html:
			'<span style="font-weight: bold;"> Cor do Botão </span>' +
			'<input id="swal-input1" class="swal2-input" type="color" value="#228B22">',
			focusConfirm: true,
			preConfirm: () => {
				return [
					document.getElementById('swal-input1').value
				]
			}
		});

		if (result) {
			//nm_botao, tipo, descricao, modelo, juiz,responsavel, assinar, cor, vinculo, visibilidade
			criaBotao_aaDespacho(aaDespacho_temp.length, temp[0], temp[1], temp[2], temp[3], temp[4], temp[5], temp[6], 'não', result[0], 'Nenhum', 'sim', '');
			aaDespacho_temp.push(new AcaoAutomatizada_aaDespacho(temp[0], temp[1], temp[2], temp[3], temp[4], temp[5], temp[6], 'não', result[0], 'Nenhum', 'sim', ''));
			salvarOpcoes();
		}
	}
}

async function aa_movimento() {
	let temp = [];
	Swal.mixin({
		input: 'text',
		confirmButtonText: 'Próximo &rarr;',
		showCancelButton: true,
		progressSteps: ['1', '2', '3', '4']
	}).queue([
	{
		title: 'Nome do Botão',
		text: ''
	},
	{
		title: 'Nome do Nó de destino',
		text: ''
	},
	{
		title: 'Lançar Chip (nome)',
		text: ''
	},
	{
		title: 'Responsável pelo Processo:',
		text: ''
	}
	]).then((result) => {
		if (result.value) {
			temp = result.value;
			color();
		}
	});

	async function color() {
		const { value: result } = await Swal.fire({
			title: '    ',
			html:
			'<span style="font-weight: bold;"> Cor do Botão </span>' +
			'<input id="swal-input1" class="swal2-input" type="color" value="#B22222">',
			focusConfirm: true,
			preConfirm: () => {
				return [
					document.getElementById('swal-input1').value
				]
			}
		});

		if (result) {
			criaBotao_aaMovimento(aaMovimento_temp.length, temp[0], temp[1], temp[2], temp[3], result[0], 'Nenhum', 'sim');
			aaMovimento_temp.push(new AcaoAutomatizada_aaMovimento(temp[0], temp[1], temp[2], temp[3], result[0], 'Nenhum', 'sim'));
			salvarOpcoes();
		}
	}
}

async function aa_checklist() {
	let temp = [];
	Swal.mixin({
		input: 'text',
		confirmButtonText: 'Próximo &rarr;',
		showCancelButton: true,
		progressSteps: ['1', '2', '3', '4', '5', '6']
	}).queue([
	{
		title: 'Nome do Botão',
		text: ''
	},
	{
		title: 'Tipo do Checklist',
		html: 'Exemplos:<br>BACEN<br>RENAJUD<br>CNIB<br>BNDT'
	},
	{
		title: 'Observação',
		html: 'Perguntar na hora do lançamento? preencha com a expressão "perguntar"',
		input: 'textarea',
	},
	{
		title: 'Status',
		input: 'select',
		inputOptions: {
			'nenhum': 'nenhum',
			'negativo': 'negativo',
			'parcial': 'parcial',
			'positivo': 'positivo',
			'perguntar': 'perguntar',
		},
		inputValue: 'perguntar',
	},
	{
		title: 'Alerta',
		input: 'select',
		inputOptions: {
			'Sim': 'Sim',
			'Não': 'Não',
		},
		inputValue: 'Não',
	},
	{
		title: 'Salvar automaticamente',
		input: 'select',
		inputOptions: {
			'Sim': 'Sim',
			'Não': 'Não',
		}
	}
	]).then((result) => {
		if (result.value) {
			temp = result.value;
			color();
		}
	});

	async function color() {
		const { value: result } = await Swal.fire({
			title: '    ',
			html:
			'<span style="font-weight: bold;"> Cor do Botão </span>' +
			'<input id="swal-input1" class="swal2-input" type="color" value="#B22222">',
			focusConfirm: true,
			preConfirm: () => {
				return [
					document.getElementById('swal-input1').value
				]
			}
		});

		if (result) {
			criaBotao_aaChecklist(aaChecklist_temp.length, temp[0], temp[1], temp[2], temp[3], temp[4], temp[5], result[0], 'Nenhum', 'sim');
			aaChecklist_temp.push(new AcaoAutomatizada_aaChecklist(temp[0], temp[1], temp[2], temp[3], temp[4], temp[5], result[0], 'Nenhum', 'sim'));
			salvarOpcoes();
		}
	}
}

async function aa_nomearPerito() {
	let temp = [];
	Swal.mixin({
		input: 'text',
		confirmButtonText: 'Próximo &rarr;',
		showCancelButton: true,
		progressSteps: ['1', '2', '3', '4', '5', '6', '7']
	}).queue([
	{
		title: 'Nome do Botão',
		text: ''
	},
	{
		title: 'Profissão',
		html: 'Exemplos:<br>CONTADOR<br>ENGENHEIRO<br>MÉDICO CLÍNICO'
	},
	{
		title: 'Nome do Perito',
		html: 'Se deixar o campo em branco, será utilizado o perito sorteado pelo PJe'
	},
	{
		title: 'Prazo',
		html: 'Pode ser em número de dias úteis ou uma data.<br>Exemplo: 01/01/2021<br><br><i style="color:cadetblue;">Para dias corridos, acrescente a expressão dc depois do prazo.<br><br>Por exemplo: <b>60dc</b> é igual a 60 dias corridos.</i>'
	},
	{
		title: 'Designar Automaticamente',
		input: 'select',
		inputOptions: {
			'Sim': 'Sim',
			'Não': 'Não',
		},
		inputValue: 'Não',
	},
	{
		title: 'Modelo da Intimação',
		html: 'Se deixar o campo em branco, será utilizado o modelo próprio do PJe.'
	},
	{
		title: 'Assinar automaticamente',
		input: 'select',
		inputOptions: {
			'Sim': 'Sim',
			'Não': 'Não',
		}
	}
	]).then((result) => {
		if (result.value) {
			temp = result.value;
			color();
		}
	});

	async function color() {
		const { value: result } = await Swal.fire({
			title: '    ',
			html:
			'<span style="font-weight: bold;"> Cor do Botão </span>' +
			'<input id="swal-input1" class="swal2-input" type="color" value="#B22222">',
			focusConfirm: true,
			preConfirm: () => {
				return [
					document.getElementById('swal-input1').value
				]
			}
		});

		if (result) {
            let tipo_prazo = "";
            let prazo = temp[3]
            if (prazo.toLowerCase().includes('dc')) {
                tipo_prazo = "Dias Corridos";
                prazo = prazo.replace('dc','');
            } else if (prazo.search("/") > -1) {
                tipo_prazo = "Data Certa";
            } else {
                tipo_prazo = "Dias Úteis";
            }
            console.log(prazo + ' : ' + tipo_prazo)
			// id, nm_botao, profissao, perito, prazo, tipo_prazo, designar, modelo, assinar, cor, vinculo, visibilidade) {
			criaBotao_aaNomearPerito(aaNomearPerito_temp.length, temp[0], temp[1].toUpperCase(), temp[2].toUpperCase(), prazo, tipo_prazo, temp[4], temp[5], temp[6], result[0], 'Nenhum', 'sim');
			aaNomearPerito_temp.push(new AcaoAutomatizada_aaNomearPerito(temp[0], temp[1].toUpperCase(), temp[2].toUpperCase(), prazo, tipo_prazo, temp[4], temp[5], temp[6], result[0], 'Nenhum', 'sim'));
			salvarOpcoes();
		}
	}
}

async function importarAA() {

	const { value: result } = await Swal.fire({
		title: '    ',
		html:
		'<span style="font-weight: bold;"> IMPORTAR AÇÃO AUTOMATIZADA:</span><br>' +
		'<i style="font-size: 0.8em;font-weight: normal;font-style: normal;text-align: left;color: darkcyan;">Cole uma configuração em cada campo. É possível importar no máximo cinco ações por vez.</i><br>' +
		'<br><textarea id="swal-input-importarAA1" placeholder="código da Ação Automatizada 1" class="swal2-input" style="height: 100px;font-family: inherit;line-height: 1.5em;margin:0;"></textarea>' +
		'<br><textarea id="swal-input-importarAA2" placeholder="código da Ação Automatizada 2" class="swal2-input" style="height: 100px;font-family: inherit;line-height: 1.5em;margin:0;"></textarea>' +
		'<br><textarea id="swal-input-importarAA3" placeholder="código da Ação Automatizada 3" class="swal2-input" style="height: 100px;font-family: inherit;line-height: 1.5em;margin:0;"></textarea>' +
		'<br><textarea id="swal-input-importarAA4" placeholder="código da Ação Automatizada 4" class="swal2-input" style="height: 100px;font-family: inherit;line-height: 1.5em;margin:0;"></textarea>' +
		'<br><textarea id="swal-input-importarAA5" placeholder="código da Ação Automatizada 5" class="swal2-input" style="height: 100px;font-family: inherit;line-height: 1.5em;margin:0;"></textarea>',
		confirmButtonText: 'Importar',
		focusConfirm: false,
		preConfirm: async () => {

			let campos = document.querySelectorAll('textarea[id*="swal-input-importarAA"]');
			let configuracoes = [];
			[].map.call(campos,function(item) { if (item.value) { configuracoes.push(item.value) } });

			return configuracoes;
		}
	});

	let printError = function(error) {
		console.log(error.name + " : " + error.message);
		alert(error.name + " : " + error.message);
	}

	try {
		console.log(result)
		if (result) {

			let colecao = result;
			switch (this.id) {
				case 'aa_imp_anexar_documentos':

					for (var i = 0; i < colecao.length; i++) {
						let temp = JSON.parse(colecao[i]);
						criaBotao_aaAnexar(aaAnexar_temp.length, temp.nm_botao, temp.tipo, temp.descricao, temp.sigilo, temp.modelo, temp.assinar, temp.cor, temp.vinculo, temp.visibilidade);
						aaAnexar_temp.push(new AcaoAutomatizada_aaAnexar(temp.nm_botao, temp.tipo, temp.descricao, temp.sigilo, temp.modelo, temp.assinar, temp.cor, temp.vinculo, temp.visibilidade));
					}
					break;

				case 'aa_imp_comunicacao':

					for (var i = 0; i < colecao.length; i++) {
						let temp = JSON.parse(colecao[i]);
						let tempComandosEspeciais = (!temp.comandosEspeciais) ? '': temp.comandosEspeciais;
						criaBotao_aaComunicacao(aaComunicacao_temp.length, temp.nm_botao, temp.tipo, temp.subtipo, temp.tipo_prazo, temp.prazo, temp.descricao, temp.sigilo, temp.modelo, temp.salvar, temp.cor, temp.vinculo, temp.fluxo, temp.visibilidade, tempComandosEspeciais);
						aaComunicacao_temp.push(new AcaoAutomatizada_aaComunicacao(temp.nm_botao, temp.tipo, temp.subtipo, temp.tipo_prazo, temp.prazo, temp.descricao, temp.sigilo, temp.modelo, temp.salvar, temp.cor, temp.vinculo, temp.fluxo, temp.visibilidade, tempComandosEspeciais));
					}

					break;

				case 'aa_imp_autogigs':

					for (var i = 0; i < colecao.length; i++) {
						let temp = JSON.parse(colecao[i]);
						criaBotao_aaAutogigs(aaAutogigs_temp.length, temp.nm_botao, temp.tipo, temp.tipo_atividade, temp.prazo, temp.responsavel, temp.responsavel_processo, temp.observacao, temp.salvar, temp.cor, temp.vinculo, temp.visibilidade);
						aaAutogigs_temp.push(new AcaoAutomatizada_aaAutogigs( temp.nm_botao, temp.tipo, temp.tipo_atividade, temp.prazo, temp.responsavel, temp.responsavel_processo, temp.observacao, temp.salvar, temp.cor, temp.vinculo, temp.visibilidade));
					}
					break;

				case 'aa_imp_despacho':

					for (var i = 0; i < colecao.length; i++) {

						let temp = JSON.parse(colecao[i]);
						let tempAssinar = (!temp.assinar) ? 'nao' : temp.assinar;
						let tempComandosEspeciais = (!temp.comandosEspeciais) ? '': temp.comandosEspeciais;
						criaBotao_aaDespacho(aaDespacho_temp.length, temp.nm_botao, temp.tipo, temp.descricao, temp.sigilo, temp.modelo, temp.juiz, temp.responsavel, tempAssinar, temp.cor, temp.vinculo, temp.visibilidade, tempComandosEspeciais);
						aaDespacho_temp.push(new AcaoAutomatizada_aaDespacho(temp.nm_botao, temp.tipo, temp.descricao, temp.sigilo, temp.modelo, temp.juiz, temp.responsavel, tempAssinar, temp.cor, temp.vinculo, temp.visibilidade, tempComandosEspeciais));
					}

					break;

				case 'aa_imp_movimento':

					for (var i = 0; i < colecao.length; i++) {
						let temp = JSON.parse(colecao[i]);
						criaBotao_aaMovimento(aaMovimento_temp.length, temp.nm_botao, temp.destino, temp.chip, temp.responsavel, temp.cor, temp.vinculo, temp.visibilidade);
						aaMovimento_temp.push(new AcaoAutomatizada_aaMovimento(temp.nm_botao, temp.destino, temp.chip, temp.responsavel, temp.cor, temp.vinculo, temp.visibilidade));
					}
					break;

				case 'aa_imp_checklist':

					for (var i = 0; i < colecao.length; i++) {
						let temp = JSON.parse(colecao[i]);
						criaBotao_aaChecklist(aaChecklist_temp.length, temp.nm_botao, temp.tipo, temp.observacao, temp.estado, temp.alerta, temp.salvar, temp.cor, temp.vinculo, temp.visibilidade);
						aaChecklist_temp.push(new AcaoAutomatizada_aaChecklist(temp.nm_botao, temp.tipo, temp.observacao, temp.estado, temp.alerta, temp.salvar, temp.cor, temp.vinculo, temp.visibilidade));
					}
					break;

				case 'aa_imp_nomearPerito':
					for (var i = 0; i < colecao.length; i++) {
                        let temp = JSON.parse(colecao[i]);
                        temp.tipo_prazo = (!temp.tipo_prazo) ? 'Dias Úteis' : temp.tipo_prazo; //corrige as AAs criadas no período de teste quando não existia essa variável
						criaBotao_aaNomearPerito(aaNomearPerito_temp.length, temp.nm_botao, temp.profissao, temp.perito, temp.prazo, temp.tipo_prazo, temp.designar, temp.modelo, temp.assinar, temp.cor, temp.vinculo, temp.visibilidade);
						aaNomearPerito_temp.push(new AcaoAutomatizada_aaNomearPerito(temp.nm_botao, temp.profissao, temp.perito, temp.prazo, temp.tipo_prazo, temp.designar, temp.modelo, temp.assinar, temp.cor, temp.vinculo, temp.visibilidade));
					}
					break;
			}
			await salvarOpcoes();

		}
	} catch (e) {
		printError(e);
	}
}

async function importarModulo2() {

	const { value: result } = await Swal.fire({
		title: '    ',
		html:
		'<span style="font-weight: bold;"> Importar Configurações do módulo:</span><br>' +
		'<i style="font-size: 0.8em;font-weight: normal;font-style: normal;text-align: left;color: darkcyan;">Cole a configuração no campo abaixo</i><br>' +
		'<br><textarea id="swal-input-importarModulo" placeholder="código da configuração" class="swal2-input" style="height: 50vh;font-family: inherit;line-height: 1.5em;margin:0;"></textarea>',
		confirmButtonText: 'Importar',
		customClass: 'swal-wide',
		focusConfirm: false,
		preConfirm: async () => {
			return document.getElementById('swal-input-importarModulo').value;
		}
	});

	let printError = function(error) {
		console.log(error.name + " : " + error.message);
		alert(error.name + " : " + error.message);
	}

	try {
		if (result) {
			console.log(result)
			let i = result.replace(/(\[)|(\])/g,''); //tira os colchetes
			i = i.replace(/(\")|(\")/g,''); //tira as aspas
			console.log(i)
			let novasRegras = i.split(',');
			let antigasRegras = listaModulo2_temp;
			listaModulo2_temp = [...antigasRegras, ...novasRegras]; //exclui regras duplicadas

			preferencias.modulo2 = listaModulo2_temp;
			montar_modulo2();
			await salvarOpcoes();
		}
	} catch (e) {
		printError(e);
	}
}

function exportarModulo2() {
	console.log('exportarModulo')
	Swal.fire({
		title: 'Exportar configurações?',
		text: "",
		showCancelButton: true,
		confirmButtonColor: '#3085d6',
		cancelButtonColor: '#d33',
		confirmButtonText: 'Sim, exportar!',
		cancelButtonText: 'Não'
	}).then((result) => {
		if (result.value) {
			copiarDados(listaModulo2_temp);
		}
	})

	function copiarDados(dados) {
		var textarea = document.createElement("textarea");
		textarea.textContent = JSON.stringify(dados);
		document.body.appendChild(textarea);
		textarea.select();
		document.execCommand("copy");
		document.body.removeChild(textarea);

		Swal.fire({
		  position: 'center',
		  icon: 'success',
		  title: 'Conteúdo copiado com sucesso.',
		  showConfirmButton: false,
		  timer: 1500
		})
	}
}

async function buscarAA() {
	let ancora = this.id;

	if (this.style.backgroundColor == 'orangered') {
		this.style.backgroundColor = '#545454';
		filtrar('');
	} else {
		this.style.backgroundColor = 'orangered';
		Swal.fire({
			title: 'Filtrar',
			input: 'text',
			inputPlaceholder: 'Digite o nome ou parte do nome da AA',
			confirmButtonText: 'Filtrar'
		}).then(function (result) {
			filtrar(result.value);
		})
	}

	function filtrar(texto) {
		switch (ancora) {
			case 'aa_buscar_anexar_documentos':
				let listaDeAAAnexar_documentos = document.querySelectorAll('a[id*="botao_anexar_documentos_"]');
				[].map.call(
					listaDeAAAnexar_documentos,
					function(item) {
						if (texto.length == 0) {
							item.style.visibility = 'visible'
						} else if (!item.innerText.toLowerCase().includes(texto.toLowerCase())) {
							item.style.visibility = 'hidden'
						}
					}
				);
				break;

			case 'aa_buscar_comunicacao':
				let listaDeAAComunicacao = document.querySelectorAll('a[id*="botao_comunicacao_"]');
				[].map.call(
					listaDeAAComunicacao,
					function(item) {
						if (texto.length == 0) {
							item.style.visibility = 'visible'
						} else if (!item.innerText.toLowerCase().includes(texto.toLowerCase())) {
							item.style.visibility = 'hidden'
						}
					}
				);
				break;

			case 'aa_buscar_autogigs':

				let listaDeAAAutogigs = document.querySelectorAll('a[id*="botao_autogigs_"]');
				[].map.call(
					listaDeAAAutogigs,
					function(item) {
						if (texto.length == 0) { //lupa desativada
							item.style.opacity = '1'
							item.nextSibling.style.opacity = '1'

						} else if (item.innerText.toLowerCase().includes(texto.toLowerCase())) {
							item.style.opacity = '1'
							item.nextSibling.style.opacity = '1'

						} else {
							item.style.opacity = '0'
							item.nextSibling.style.opacity = '0'
						}
					}
				);
				break;

			case 'aa_buscar_despacho':

				let listaDeAADespacho = document.querySelectorAll('a[id*="botao_despacho_"]');
				[].map.call(
					listaDeAADespacho,
					function(item) {
						if (texto.length == 0) {
							item.style.visibility = 'visible'
						} else if (!item.innerText.toLowerCase().includes(texto.toLowerCase())) {
							item.style.visibility = 'hidden'
						}
					}
				);
				break;

			case 'aa_buscar_movimento':

				let listaDeAAMovimento = document.querySelectorAll('a[id*="botao_movimento_"]');
				[].map.call(
					listaDeAAMovimento,
					function(item) {
						if (texto.length == 0) {
							item.style.visibility = 'visible'
						} else if (!item.innerText.toLowerCase().includes(texto.toLowerCase())) {
							item.style.visibility = 'hidden'
						}
					}
				);
				break;

			case 'aa_buscar_checklist':

				let listaDeAAChecklist = document.querySelectorAll('a[id*="botao_checklist_"]');
				[].map.call(
					listaDeAAChecklist,
					function(item) {
						if (texto.length == 0) {
							item.style.visibility = 'visible'
						} else if (!item.innerText.toLowerCase().includes(texto.toLowerCase())) {
							item.style.visibility = 'hidden'
						}
					}
				);
				break;

		}
	}
}

function montarBotoesDetalhes() {
	if (typeof(preferencias.atalhosDetalhes) != "undefined") {
		document.getElementById('c24').checked = preferencias.atalhosDetalhes[24];
		document.getElementById('c24').addEventListener('click', salvarOpcoes);
		document.getElementById('c0').checked = preferencias.atalhosDetalhes[0];
		document.getElementById('c0').addEventListener('click', salvarOpcoes);
		document.getElementById('c1').checked = preferencias.atalhosDetalhes[1];
		document.getElementById('c1').addEventListener('click', salvarOpcoes);
		document.getElementById('c2').checked = preferencias.atalhosDetalhes[2];
		document.getElementById('c2').addEventListener('click', salvarOpcoes);
		document.getElementById('c3').checked = preferencias.atalhosDetalhes[3];
		document.getElementById('c3').addEventListener('click', salvarOpcoes);
		document.getElementById('c4').checked = preferencias.atalhosDetalhes[4];
		document.getElementById('c4').addEventListener('click', salvarOpcoes);
		document.getElementById('c5').checked = preferencias.atalhosDetalhes[5];
		document.getElementById('c5').addEventListener('click', salvarOpcoes);
		document.getElementById('c6').checked = preferencias.atalhosDetalhes[6];
		document.getElementById('c6').addEventListener('click', salvarOpcoes);
		document.getElementById('c7').checked = preferencias.atalhosDetalhes[7];
		document.getElementById('c7').addEventListener('click', salvarOpcoes);
		document.getElementById('c8').checked = preferencias.atalhosDetalhes[8];
		document.getElementById('c8').addEventListener('click', salvarOpcoes);
		document.getElementById('c9').checked = preferencias.atalhosDetalhes[9];
		document.getElementById('c9').addEventListener('click', salvarOpcoes);
		document.getElementById('c10').checked = preferencias.atalhosDetalhes[10];
		document.getElementById('c10').addEventListener('click', salvarOpcoes);
		document.getElementById('c25').checked = preferencias.atalhosDetalhes[25];
		document.getElementById('c25').addEventListener('click', salvarOpcoes);
		document.getElementById('c11').checked = preferencias.atalhosDetalhes[11];
		document.getElementById('c11').addEventListener('click', salvarOpcoes);
		document.getElementById('c26').checked = preferencias.atalhosDetalhes[26];
		document.getElementById('c26').addEventListener('click', salvarOpcoes);
		document.getElementById('c12').checked = preferencias.atalhosDetalhes[12];
		document.getElementById('c12').addEventListener('click', salvarOpcoes);
		document.getElementById('c27').checked = preferencias.atalhosDetalhes[27];
		document.getElementById('c27').addEventListener('click', salvarOpcoes);
		document.getElementById('c13').checked = preferencias.atalhosDetalhes[13];
		document.getElementById('c13').addEventListener('click', salvarOpcoes);
		document.getElementById('c14').checked = preferencias.atalhosDetalhes[14];
		document.getElementById('c14').addEventListener('click', salvarOpcoes);
		document.getElementById('c15').checked = preferencias.atalhosDetalhes[15];
		document.getElementById('c15').addEventListener('click', salvarOpcoes);
		document.getElementById('c16').checked = preferencias.atalhosDetalhes[16];
		document.getElementById('c16').addEventListener('click', salvarOpcoes);
		document.getElementById('c17').checked = preferencias.atalhosDetalhes[17];
		document.getElementById('c17').addEventListener('click', salvarOpcoes);
		document.getElementById('c18').checked = preferencias.atalhosDetalhes[18];
		document.getElementById('c18').addEventListener('click', salvarOpcoes);
		document.getElementById('c19').checked = preferencias.atalhosDetalhes[19];
		document.getElementById('c19').addEventListener('click', salvarOpcoes);
		document.getElementById('c28').checked = preferencias.atalhosDetalhes[28];
		document.getElementById('c28').addEventListener('click', salvarOpcoes);
		document.getElementById('c20').checked = preferencias.atalhosDetalhes[20];
		document.getElementById('c20').addEventListener('click', salvarOpcoes);
		document.getElementById('c21').checked = preferencias.atalhosDetalhes[21];
		document.getElementById('c21').addEventListener('click', salvarOpcoes);
		document.getElementById('c22').checked = preferencias.atalhosDetalhes[22];
		document.getElementById('c22').addEventListener('click', salvarOpcoes);
		document.getElementById('c23').checked = preferencias.atalhosDetalhes[23];
		document.getElementById('c23').addEventListener('click', salvarOpcoes);
		document.getElementById('c29').checked = preferencias.atalhosDetalhes[29];
		document.getElementById('c29').addEventListener('click', salvarOpcoes);
		document.getElementById('c30').checked = preferencias.atalhosDetalhes[30];
		document.getElementById('c30').addEventListener('click', salvarOpcoes);
		document.getElementById('c31').checked = preferencias.atalhosDetalhes[31];
		document.getElementById('c31').addEventListener('click', salvarOpcoes);
	}
}

async function obterVinculosDescendentes(aaPai,v) {
	return new Promise(async resolve => {
		// console.log(aaPai + ' **** ' + v);

		//ajustando o lançar movimentos que eu mudei o nome das AAs
		let t = v.toString().replace("LançarMovimento|Contadoria:atualização","LançarMovimento|para Contadoria:atualização");
		t = t.replace("LançarMovimento|Contadoria:liquidação","LançarMovimento|para Contadoria:liquidação");
		t = t.replace("LançarMovimento|Contadoria:retificação","LançarMovimento|para Contadoria:retificação");
		t = t.replace("LançarMovimento|Contadoria:DeterminaçãoJudicial","LançarMovimento|para Contadoria:DeterminaçãoJudicial");
		v = t;

		if (v.toString().includes('Nenhum')) { //já foi obtido. Somente uma vez. Regra de transição.
			// alert('Descendente já obtido')
			return resolve(v);
		}
		let vTemp = v;
		let tipo = vTemp.split('|')[0];
		let id = vTemp.split('|')[1]

		let aaTemp;

		if (tipo == 'Anexar') {
			aaTemp = aaAnexar_temp;
		} else if (tipo == 'Comunicação') {
			aaTemp = aaComunicacao_temp;
		} else if (tipo == 'AutoGigs') {
			aaTemp = aaAutogigs_temp;
		} else if (tipo == 'Despacho') {
			aaTemp = aaDespacho_temp;
		} else if (tipo == 'Movimento') {
			aaTemp = aaMovimento_temp;
		} else if (tipo == 'Checklist') {
			aaTemp = aaChecklist_temp;
		} else if (tipo == 'Clicar em') {
			return resolve(v + ',Nenhum');
		} else if (tipo == 'RetificarAutuação') {
			return resolve(v + ',Nenhum');
		} else if (tipo == 'LançarMovimento') {
			return resolve(v + ',Nenhum');
		} else if (tipo == 'Atualizar Pagina') {
			return resolve(v + ',Nenhum');
		} else if (tipo == 'Fechar Pagina') {
			return resolve(v + ',Nenhum');
		} else {
			console.debug('erro na obtenção de descendentes (Classificação do Tipo de AA: não encontrada!)');
			return resolve('Nenhum');
		}

		let aaDescendente;
		if (aaPai == id) { //se chamou ele mesmo interrompe para evitar looping
			console.log('*******(caso1) interrompeu looping na AA ' + id);
			aaDescendente = ",Nenhum";
		} else {
			aaDescendente = await obterAA(aaTemp,id);
		}

		// console.log(id + " vínculo " + aaDescendente);

		if (aaDescendente != ',Nenhum') {
			// console.log("lista de vínculos mapeados: " + v + "   ----> " + v.includes(aaDescendente));
			if (v.split(',').includes(aaDescendente)) { //se chamou uma AA que já foi qualificada como descendente interrompe para evitar looping
				console.log('*******(caso2) interrompeu looping na AA ' + id);
				v += ",Nenhum";
			} else {
				v += "," + await obterVinculosDescendentes(aaPai, aaDescendente);
			}
		}
		return resolve(v)
	});

	async function obterAA(lista,id) {
		return new Promise(async resolve => {
			let aaEncontrada = ',Nenhum';

			for (const [pos, item] of lista.entries()) {
				// console.log(id + " == " + item.nm_botao + "  :  " + (item.nm_botao == id))
				if (item.nm_botao == id) {
					aaEncontrada = item.vinculo;
					mapeadosAADescendentes = true;
					break;
				}
			}

			return resolve(aaEncontrada);
		});
	}
}

async function montarBotoesaaAnexar() {
	if (typeof(aaAnexar_temp) != "undefined") {
		// possibilita mover os botões de lugar arrastando e soltando o elemento
		let el = document.getElementById("botoes_anexar_documentos");
		var origem;

		el.addEventListener("dragstart", function(event) {
			if (event.target.parentElement.id == "botoes_anexar_documentos") {
				origem = event.target;
				event.target.removeAttribute("data-tooltip");
			}
		}, false);

		el.addEventListener("dragover", function(event) {
			event.preventDefault();
		}, false);

		el.addEventListener("dragenter", function(event) {
			if (!origem) {
				return;
			}
			if (event.target.parentElement.id == "botoes_anexar_documentos") {
				if (event.target.id.search("espaco_botao_anexar_documentos_") > -1) {
					event.target.className = origem.className;
					event.target.style = origem.style;
					let largura_ideal = event.target.parentElement.offsetWidth - event.target.getBoundingClientRect().left - 35;
					let largura_elemento = origem.offsetWidth - 35;
					event.target.style.width = (largura_elemento > largura_ideal) ? largura_ideal + "px" : largura_elemento + "px";
					event.target.style.backgroundColor = origem.style.backgroundColor;
					event.target.style.opacity = ".8";
					event.target.style.margin = "0";
					event.target.style.boxShadow = "inset 4px 0px 0px white,inset -4px 0px 0px white";
				}
			}
		}, false);

		el.addEventListener("dragleave", function(event) {
			if (event.target.parentElement.id == "botoes_anexar_documentos") {
				if (event.target.id.search("espaco_botao_anexar_documentos_") > -1) {
					event.target.style.backgroundColor = "white";
					event.target.className = "";
					event.target.style.width = ".8em";
					event.target.style.margin = "";
				}
			}
		}, false);

		document.addEventListener("drop", function(event) {
			if (!origem) {
				return;
			}
			if (event.target.id.search("espaco_botao_anexar_documentos_") < 0) {
				origem = null;
				return;
			}
			if (!event.target.parentElement) {
				origem = null;
				return;
			}
			if (event.target.parentElement.id == "botoes_anexar_documentos") {
				event.preventDefault();

				//retira a marca de posição
				event.target.style.backgroundColor = "white";
				event.target.className = "";
				event.target.style.width = ".8em";
				event.target.style.opacity = "0";

				//pega a posição de destino no Array
				let pos_destino = parseInt(event.target.id.replace('espaco_botao_anexar_documentos_',''));
				let pos_origem = parseInt(origem.id.replace('botao_anexar_documentos_',''));
				let verificador = pos_destino - pos_origem;
				// console.log(pos_origem + " >>> " + pos_destino + " - subtração = " + verificador);
				if (verificador == 0 || verificador == 1) {
					return
				}
				//faz as alterações necessárias no array de objetos
				let temp1 = aaAnexar_temp[pos_origem];
				aaAnexar_temp.splice(pos_origem, 1);

				//insere o botão na nova posição
				if (pos_origem < pos_destino) {
					aaAnexar_temp.splice(pos_destino-1, 0, temp1);
				} else {
					aaAnexar_temp.splice(pos_destino, 0, temp1);
				}

				salvarOpcoes();
				document.getElementById("botoes_anexar_documentos").textContent = '';
				montarBotoesaaAnexar();
			}
			origem = null;
		}, false);

		let ajustandoLista = [];
		for (const [pos, item] of aaAnexar_temp.entries()) {
			let aa = item;

			aa.vinculo = await obterVinculosDescendentes(aa.nm_botao, aa.vinculo); //converto o vínculo antigo, criando a sequencia de vínculos descendentes.
			aa = new AcaoAutomatizada_aaAnexar(aa.nm_botao, aa.tipo, aa.descricao, aa.sigilo, aa.modelo, aa.assinar, aa.cor, aa.vinculo, (!aa.visibilidade?'sim':aa.visibilidade));
			ajustandoLista.push(aa);

			criaBotao_aaAnexar(pos, aa.nm_botao, aa.tipo, aa.descricao, aa.sigilo, aa.modelo, aa.assinar, aa.cor, aa.vinculo, aa.visibilidade);
			if (pos == aaAnexar_temp.length-1) {
				//cria espaçador para o último botão
				let espaco = document.createElement("a");
				espaco.id = "espaco_botao_anexar_documentos_" + (pos+1);
				espaco.style = "width: 0.8em;";
				el.appendChild(espaco);
			}
		}
		aaAnexar_temp = ajustandoLista;
	}
}

async function montarBotoesaaComunicacao() {
	if (typeof(aaComunicacao_temp) != "undefined") {
		// possibilita mover os botões de lugar arrastando e soltando o elemento
		let el = document.getElementById("botoes_comunicacao");
		var origem;

		el.addEventListener("dragstart", function(event) {
			if (event.target.parentElement.id == "botoes_comunicacao") {
				origem = event.target;
				event.target.removeAttribute("data-tooltip");
			}
		}, false);

		el.addEventListener("dragover", function(event) {
			event.preventDefault();
		}, false);

		el.addEventListener("dragenter", function(event) {
			if (!origem) {
				return;
			}
			if (event.target.parentElement.id == "botoes_comunicacao") {
				if (event.target.id.search("espaco_botao_comunicacao_") > -1) {
					event.target.className = origem.className;
					event.target.style = origem.style;
					let largura_ideal = event.target.parentElement.offsetWidth - event.target.getBoundingClientRect().left - 35;
					let largura_elemento = origem.offsetWidth - 35;
					event.target.style.width = (largura_elemento > largura_ideal) ? largura_ideal + "px" : largura_elemento + "px";
					event.target.style.backgroundColor = origem.style.backgroundColor;
					event.target.style.opacity = ".5";
					event.target.style.margin = "0";
					event.target.style.boxShadow = "inset 4px 0px 0px white,inset -4px 0px 0px white";
				}
			}
		}, false);

		el.addEventListener("dragleave", function(event) {
			if (event.target.parentElement.id == "botoes_comunicacao") {
				if (event.target.id.search("espaco_botao_comunicacao_") > -1) {
					event.target.style.backgroundColor = "white";
					event.target.className = "";
					event.target.style.width = ".8em";
					event.target.style.opacity = "";
				}
			}
		}, false);

		document.addEventListener("drop", function(event) {
			if (!origem) {
				return;
			}
			if (event.target.id.search("espaco_botao_comunicacao_") < 0) {
				origem = null;
				return;
			}
			if (!event.target.parentElement) {
				origem = null;
				return;
			}
			if (event.target.parentElement.id == "botoes_comunicacao") {
				event.preventDefault();

				//retira a marca de posição
				event.target.style.backgroundColor = "white";
				event.target.className = "";
				event.target.style.width = ".8em";
				event.target.style.opacity = "0";

				//pega a posição de destino no Array
				let pos_destino = parseInt(event.target.id.replace('espaco_botao_comunicacao_',''));
				let pos_origem = parseInt(origem.id.replace('botao_comunicacao_',''));
				let verificador = pos_destino - pos_origem;
				// console.log(pos_origem + " >>> " + pos_destino + " - subtração = " + verificador);
				if (verificador == 0 || verificador == 1) {
					return
				}
				//faz as alterações necessárias no array de objetos
				let temp1 = aaComunicacao_temp[pos_origem];
				aaComunicacao_temp.splice(pos_origem, 1);

				//insere o botão na nova posição
				if (pos_origem < pos_destino) {
					aaComunicacao_temp.splice(pos_destino-1, 0, temp1);
				} else {
					aaComunicacao_temp.splice(pos_destino, 0, temp1);
				}

				salvarOpcoes();
				document.getElementById("botoes_comunicacao").textContent = '';
				montarBotoesaaComunicacao();
			}
			origem = null;
		}, false);

		let ajustandoLista = [];
		for (const [pos, item] of aaComunicacao_temp.entries()) {
			let aa = item;
			aa.vinculo = await obterVinculosDescendentes(aa.nm_botao, aa.vinculo); //converto o vínculo antigo, criando a sequencia de vínculos descendentes.

			//insere a visibilidade dentro da AA ajusatando todos as ações
			//AcaoAutomatizada_aaComunicacao(nm_botao, tipo, subtipo, tipo_prazo, prazo, descricao, sigilo, modelo, salvar, cor, vinculo, fluxo, visibilidade='sim')
			let tempComandosEspeciais = (!aa.comandosEspeciais) ? '' : aa.comandosEspeciais;
			tempComandosEspeciais = (tempComandosEspeciais == '[]') ? '' : tempComandosEspeciais;

			if (tempComandosEspeciais) {
				let padraoComandoEspecial = /(ativo|passivo|terceiros|assinar|trt|autoridade)/g;
				if (tempComandosEspeciais.match(padraoComandoEspecial).length < 6) {
					tempComandosEspeciais = await ajustarComandosEspeciaisComunicacao(aa.nm_botao, tempComandosEspeciais); //ajusta os comandos antigos par ao novo padrao
				}
			} else {
				//verificar no nome se tem
				let padraoComandoEspecialNoNome = /\[(.*?)\]/g;
				if (padraoComandoEspecialNoNome.test(aa.nm_botao)) {
					tempComandosEspeciais = aa.nm_botao.match(padraoComandoEspecialNoNome).join().toLowerCase();
					tempComandosEspeciais = await ajustarComandosEspeciaisComunicacao(aa.nm_botao, tempComandosEspeciais); //ajusta os comandos antigos par ao novo padrao
				}
			}

			aa = new AcaoAutomatizada_aaComunicacao(aa.nm_botao, aa.tipo, aa.subtipo, aa.tipo_prazo, aa.prazo, aa.descricao, aa.sigilo, aa.modelo, aa.salvar, aa.cor, aa.vinculo, aa.fluxo, (!aa.visibilidade?'sim':aa.visibilidade), tempComandosEspeciais);

			ajustandoLista.push(aa);

			criaBotao_aaComunicacao(pos, aa.nm_botao, aa.tipo, aa.subtipo, aa.tipo_prazo, aa.prazo, aa.descricao, aa.sigilo, aa.modelo, aa.salvar, aa.cor, aa.vinculo, aa.fluxo, aa.visibilidade, tempComandosEspeciais);
			if (pos == aaComunicacao_temp.length-1) {
				//cria espaçador para o último botão
				let espaco = document.createElement("a");
				espaco.id = "espaco_botao_comunicacao_" + (pos+1);
				espaco.style = "width: .8em;";
				el.appendChild(espaco);
			}
		}
		aaComunicacao_temp = ajustandoLista;
	}
}

async function montarBotoesaaAutogigs() {
	if (typeof(aaAutogigs_temp) != "undefined") {
		// possibilita mover os botões de lugar arrastando e soltando o elemento
		let el = document.getElementById("botoes_autogigs");
		var origem;

		el.addEventListener("dragstart", function(event) {
			if (event.target.parentElement.id == "botoes_autogigs") {
				origem = event.target;
				event.target.removeAttribute("data-tooltip");
			}
		}, false);

		el.addEventListener("dragover", function(event) {
			event.preventDefault();
		}, false);

		el.addEventListener("dragenter", function(event) {
			if (!origem) {
				return;
			}
			if (event.target.parentElement.id == "botoes_autogigs") {
				if (event.target.id.search("espaco_botao_autogigs_") > -1) {
					event.target.className = origem.className;
					event.target.style = origem.style;
					let largura_ideal = event.target.parentElement.offsetWidth - event.target.getBoundingClientRect().left - 35;
					let largura_elemento = origem.offsetWidth - 35;
					event.target.style.width = (largura_elemento > largura_ideal) ? largura_ideal + "px" : largura_elemento + "px";
					event.target.style.backgroundColor = origem.style.backgroundColor;
					event.target.style.opacity = ".5";
					event.target.style.margin = "0";
					event.target.style.boxShadow = "inset 4px 0px 0px white,inset -4px 0px 0px white";
				}
			}
		}, false);

		el.addEventListener("dragleave", function(event) {
			if (event.target.parentElement.id == "botoes_autogigs") {
				if (event.target.id.search("espaco_botao_autogigs_") > -1) {
					event.target.style.backgroundColor = "white";
					event.target.className = "";
					event.target.style.width = ".8em";
					event.target.style.opacity = "";
				}
			}
		}, false);

		document.addEventListener("drop", function(event) {
			if (!origem) {
				return;
			}
			if (event.target.id.search("espaco_botao_autogigs_") < 0) {
				origem = null;
				return;
			}
			if (!event.target.parentElement) {
				origem = null;
				return;
			}
			if (event.target.parentElement.id == "botoes_autogigs") {
				event.preventDefault();

				//retira a marca de posição
				event.target.style.backgroundColor = "white";
				event.target.className = "";
				event.target.style.width = ".8em";
				event.target.style.opacity = "0";

				//pega a posição de destino no Array
				let pos_destino = parseInt(event.target.id.replace('espaco_botao_autogigs_',''));
				let pos_origem = parseInt(origem.id.replace('botao_autogigs_',''));
				let verificador = pos_destino - pos_origem;
				if (verificador == 0 || verificador == 1) {
					return
				}
				//faz as alterações necessárias no array de objetos
				let temp1 = aaAutogigs_temp[pos_origem];
				aaAutogigs_temp.splice(pos_origem, 1);

				//insere o botão na nova posição
				if (pos_origem < pos_destino) {
					aaAutogigs_temp.splice(pos_destino-1, 0, temp1);
				} else {
					aaAutogigs_temp.splice(pos_destino, 0, temp1);
				}

				salvarOpcoes();
				document.getElementById("botoes_autogigs").textContent = '';
				montarBotoesaaAutogigs();
			}
			origem = null;
		}, false);

		let ajustandoLista = [];
		for (const [pos, item] of aaAutogigs_temp.entries()) {
			let aa = item;
			aa.vinculo = await obterVinculosDescendentes(aa.nm_botao, aa.vinculo); //converto o vínculo antigo, criando a sequencia de vínculos descendentes.

			//insere a visibilidade dentro da AA ajusatando todos as ações
			//nm_botao, tipo, tipo_atividade, prazo, responsavel, responsavel_processo, observacao, salvar, cor, vinculo, visibilidade=true
			aa = new AcaoAutomatizada_aaAutogigs(aa.nm_botao, aa.tipo, aa.tipo_atividade, aa.prazo, aa.responsavel, aa.responsavel_processo, aa.observacao, aa.salvar, aa.cor, aa.vinculo, (!aa.visibilidade?'sim':aa.visibilidade));
			ajustandoLista.push(aa);

			criaBotao_aaAutogigs(pos, aa.nm_botao, aa.tipo, aa.tipo_atividade, aa.prazo, aa.responsavel, aa.responsavel_processo, aa.observacao, aa.salvar, aa.cor, aa.vinculo, aa.visibilidade);
			if (pos == aaAutogigs_temp.length-1) {
				//cria espaçador para o último botão
				let espaco = document.createElement("a");
				espaco.id = "espaco_botao_autogigs_" + (pos+1);
				espaco.style = "width: .8em;";
				el.appendChild(espaco);
			}
		}
		aaAutogigs_temp = ajustandoLista;
	}
}

async function montarBotoesaaDespacho() {
	if (typeof(aaDespacho_temp) != "undefined") {
		// possibilita mover os botões de lugar arrastando e soltando o elemento
		let el = document.getElementById("botoes_despacho");
		var origem, destino;

		el.addEventListener("dragstart", function(event) {
			if (event.target.parentElement.id == "botoes_despacho") {
				origem = event.target;
				event.target.removeAttribute("data-tooltip");
			}
		}, false);

		el.addEventListener("dragover", function(event) {
			event.preventDefault();
		}, false);

		el.addEventListener("dragenter", function(event) {
			if (!origem) {
				return;
			}
			if (event.target.parentElement.id == "botoes_despacho") {
				if (event.target.id.search("espaco_botao_despacho_") > -1) {
					event.target.className = origem.className;
					event.target.style = origem.style;
					let largura_ideal = event.target.parentElement.offsetWidth - event.target.getBoundingClientRect().left - 35;
					let largura_elemento = origem.offsetWidth - 35;
					event.target.style.width = (largura_elemento > largura_ideal) ? largura_ideal + "px" : largura_elemento + "px";
					event.target.style.backgroundColor = origem.style.backgroundColor;
					event.target.style.opacity = ".5";
					event.target.style.margin = "0";
					event.target.style.boxShadow = "inset 4px 0px 0px white,inset -4px 0px 0px white";
				}
			}
		}, false);

		el.addEventListener("dragleave", function(event) {
			if (event.target.parentElement.id == "botoes_despacho") {
				if (event.target.id.search("espaco_botao_despacho_") > -1) {
					event.target.style.backgroundColor = "white";
					event.target.className = "";
					event.target.style.width = ".8em";
					event.target.style.opacity = "";
				}
			}
		}, false);

		document.addEventListener("drop", function(event) {
			if (!origem) {
				return;
			}
			if (event.target.id.search("espaco_botao_despacho_") < 0) {
				origem = null;
				return;
			}
			if (!event.target.parentElement) {
				origem = null;
				return;
			}
			if (event.target.parentElement.id == "botoes_despacho") {
				event.preventDefault();

				//retira a marca de posição
				event.target.style.backgroundColor = "white";
				event.target.className = "";
				event.target.style.width = ".8em";
				event.target.style.opacity = "0";

				//pega a posição de destino no Array
				let pos_destino = parseInt(event.target.id.replace('espaco_botao_despacho_',''));
				let pos_origem = parseInt(origem.id.replace('botao_despacho_',''));
				let verificador = pos_destino - pos_origem;
				if (verificador == 0 || verificador == 1) {
					return
				}
				//faz as alterações necessárias no array de objetos
				let temp1 = aaDespacho_temp[pos_origem];
				aaDespacho_temp.splice(pos_origem, 1);

				//insere o botão na nova posição
				if (pos_origem < pos_destino) {
					aaDespacho_temp.splice(pos_destino-1, 0, temp1);
				} else {
					aaDespacho_temp.splice(pos_destino, 0, temp1);
				}

				salvarOpcoes();
				document.getElementById("botoes_despacho").textContent = '';
				montarBotoesaaDespacho();
			}
			origem = null;
		}, false);

		let ajustandoLista = [];
		for (const [pos, item] of aaDespacho_temp.entries()) {
			let aa = item;

			aa.vinculo = await obterVinculosDescendentes(aa.nm_botao, aa.vinculo); //converto o vínculo antigo, criando a sequencia de vínculos descendentes.

			//insere a visibilidade dentro da AA ajusatando todos as ações
			//AcaoAutomatizada_aaDespacho(nm_botao, tipo, descricao, sigilo, modelo, juiz, responsavel, assinar, cor, vinculo, visibilidade='sim', comandosEspeciais)

			let tempAssinar = (!aa.assinar) ? 'não' : aa.assinar;
			let tempComandosEspeciais = (!aa.comandosEspeciais) ? '' : aa.comandosEspeciais;
			tempComandosEspeciais = (tempComandosEspeciais == '[]') ? '' : tempComandosEspeciais;

			if (tempComandosEspeciais) {
				let padraoComandoEspecial = /(intimar|prazo|enviarpec|movimento)/g;
				if (tempComandosEspeciais?.match(padraoComandoEspecial)?.length < 4) {
					tempComandosEspeciais = await ajustarComandosEspeciaisDespacho(aa.nm_botao, tempComandosEspeciais); //ajusta os comandos antigos par ao novo padrao
				}
			} else {
				//verificar no nome se tem
				let padraoComandoEspecialNoNome = /\[(.*?)\]/g;
				if (padraoComandoEspecialNoNome.test(aa.nm_botao)) {
					tempComandosEspeciais = aa.nm_botao.match(padraoComandoEspecialNoNome).join().toLowerCase();
					tempComandosEspeciais = await ajustarComandosEspeciaisDespacho(aa.nm_botao, tempComandosEspeciais); //ajusta os comandos antigos par ao novo padrao
				}
			}

			aa = new AcaoAutomatizada_aaDespacho(aa.nm_botao, aa.tipo, aa.descricao, aa.sigilo, aa.modelo, aa.juiz, aa.responsavel, tempAssinar, aa.cor, aa.vinculo, (!aa.visibilidade?'sim':aa.visibilidade), tempComandosEspeciais);
			ajustandoLista.push(aa);

			criaBotao_aaDespacho(pos, aa.nm_botao, aa.tipo, aa.descricao, aa.sigilo, aa.modelo, aa.juiz, aa.responsavel, tempAssinar, aa.cor, aa.vinculo, aa.visibilidade, tempComandosEspeciais);
			if (pos == aaDespacho_temp.length-1) {
				//cria espaçador para o último botão
				let espaco = document.createElement("a");
				espaco.id = "espaco_botao_despacho_" + (pos+1);
				espaco.style = "width: .8em;";
				el.appendChild(espaco);
			}
		}
		aaDespacho_temp = ajustandoLista;
	}
}

async function montarBotoesaaMovimento() {
	if (typeof(aaMovimento_temp) != "undefined") {
		// possibilita mover os botões de lugar arrastando e soltando o elemento
		let el = document.getElementById("botoes_movimento");
		var origem;

		el.addEventListener("dragstart", function(event) {
			if (event.target.parentElement.id == "botoes_movimento") {
				origem = event.target;
				event.target.removeAttribute("data-tooltip");
			}
		}, false);

		el.addEventListener("dragover", function(event) {
			event.preventDefault();
		}, false);

		el.addEventListener("dragenter", function(event) {
			if (!origem) {
				return;
			}
			if (event.target.parentElement.id == "botoes_movimento") {
				if (event.target.id.search("espaco_botao_movimento_") > -1) {
					event.target.className = origem.className;
					event.target.style = origem.style;
					let largura_ideal = event.target.parentElement.offsetWidth - event.target.getBoundingClientRect().left - 35;
					let largura_elemento = origem.offsetWidth - 35;
					event.target.style.width = (largura_elemento > largura_ideal) ? largura_ideal + "px" : largura_elemento + "px";
					event.target.style.backgroundColor = origem.style.backgroundColor;
					event.target.style.opacity = ".5";
					event.target.style.margin = "0";
					event.target.style.boxShadow = "inset 4px 0px 0px white,inset -4px 0px 0px white";
				}
			}
		}, false);

		el.addEventListener("dragleave", function(event) {
			if (event.target.parentElement.id == "botoes_movimento") {
				if (event.target.id.search("espaco_botao_movimento_") > -1) {
					event.target.style.backgroundColor = "white";
					event.target.className = "";
					event.target.style.width = ".8em";
					event.target.style.opacity = "";
				}
			}
		}, false);

		document.addEventListener("drop", function(event) {
			if (!origem) {
				return;
			}
			if (event.target.id.search("espaco_botao_movimento_") < 0) {
				origem = null;
				return;
			}
			if (!event.target.parentElement) {
				origem = null;
				return;
			}
			if (event.target.parentElement.id == "botoes_movimento") {
				event.preventDefault();

				//retira a marca de posição
				event.target.style.backgroundColor = "white";
				event.target.className = "";
				event.target.style.width = ".8em";
				event.target.style.opacity = "0";

				//pega a posição de destino no Array
				let pos_destino = parseInt(event.target.id.replace('espaco_botao_movimento_',''));
				let pos_origem = parseInt(origem.id.replace('botao_movimento_',''));
				let verificador = pos_destino - pos_origem;
				if (verificador == 0 || verificador == 1) {
					return
				}
				//faz as alterações necessárias no array de objetos
				let temp1 = aaMovimento_temp[pos_origem];
				aaMovimento_temp.splice(pos_origem, 1);

				//insere o botão na nova posição
				if (pos_origem < pos_destino) {
					aaMovimento_temp.splice(pos_destino-1, 0, temp1);
				} else {
					aaMovimento_temp.splice(pos_destino, 0, temp1);
				}

				salvarOpcoes();
				document.getElementById("botoes_movimento").textContent = '';
				montarBotoesaaMovimento();
			}
			origem = null;
		}, false);

		let ajustandoLista = [];
		for (const [pos, item] of aaMovimento_temp.entries()) {
			let aa = item;
			aa.vinculo = await obterVinculosDescendentes(aa.nm_botao, aa.vinculo); //converto o vínculo antigo, criando a sequencia de vínculos descendentes.

			//insere a visibilidade dentro da AA ajusatando todos as ações
			//AcaoAutomatizada_aaMovimento(nm_botao, destino, chip, responsavel, cor, vinculo, visibilidade='sim')
			aa = new AcaoAutomatizada_aaMovimento(aa.nm_botao, aa.destino, aa.chip, aa.responsavel, aa.cor, aa.vinculo, (!aa.visibilidade?'sim':aa.visibilidade));
			ajustandoLista.push(aa);

			criaBotao_aaMovimento(pos, aa.nm_botao, aa.destino, aa.chip, aa.responsavel, aa.cor, aa.vinculo, aa.visibilidade);
			if (pos == aaMovimento_temp.length-1) {
				//cria espaçador para o último botão
				let espaco = document.createElement("a");
				espaco.id = "espaco_botao_movimento_" + (pos+1);
				espaco.style = "width: .8em;";
				el.appendChild(espaco);
			}
		}
		aaMovimento_temp = ajustandoLista;
	}
}

async function montarBotoesaaChecklist() {
	if (typeof(aaChecklist_temp) != "undefined") {
		// possibilita mover os botões de lugar arrastando e soltando o elemento
		let el = document.getElementById("botoes_checklist");
		var origem;

		el.addEventListener("dragstart", function(event) {
			if (event.target.parentElement.id == "botoes_checklist") {
				origem = event.target;
				event.target.removeAttribute("data-tooltip");
			}
		}, false);

		el.addEventListener("dragover", function(event) {
			event.preventDefault();
		}, false);

		el.addEventListener("dragenter", function(event) {
			if (!origem) {
				return;
			}
			if (event.target.parentElement.id == "botoes_checklist") {
				if (event.target.id.search("espaco_botao_checklist_") > -1) {
					event.target.className = origem.className;
					event.target.style = origem.style;
					let largura_ideal = event.target.parentElement.offsetWidth - event.target.getBoundingClientRect().left - 35;
					let largura_elemento = origem.offsetWidth - 35;
					event.target.style.width = (largura_elemento > largura_ideal) ? largura_ideal + "px" : largura_elemento + "px";
					event.target.style.backgroundColor = origem.style.backgroundColor;
					event.target.style.opacity = ".5";
					event.target.style.margin = "0";
					event.target.style.boxShadow = "inset 4px 0px 0px white,inset -4px 0px 0px white";
				}
			}
		}, false);

		el.addEventListener("dragleave", function(event) {
			if (event.target.parentElement.id == "botoes_checklist") {
				if (event.target.id.search("espaco_botao_checklist_") > -1) {
					event.target.style.backgroundColor = "white";
					event.target.className = "";
					event.target.style.width = ".8em";
					event.target.style.opacity = "";
				}
			}
		}, false);

		document.addEventListener("drop", function(event) {
			if (!origem) {
				return;
			}
			if (event.target.id.search("espaco_botao_checklist_") < 0) {
				origem = null;
				return;
			}
			if (!event.target.parentElement) {
				origem = null;
				return;
			}
			if (event.target.parentElement.id == "botoes_checklist") {
				event.preventDefault();

				//retira a marca de posição
				event.target.style.backgroundColor = "white";
				event.target.className = "";
				event.target.style.width = ".8em";
				event.target.style.opacity = "0";

				//pega a posição de destino no Array
				let pos_destino = parseInt(event.target.id.replace('espaco_botao_checklist_',''));
				let pos_origem = parseInt(origem.id.replace('botao_checklist_',''));
				let verificador = pos_destino - pos_origem;
				if (verificador == 0 || verificador == 1) {
					return
				}
				//faz as alterações necessárias no array de objetos
				let temp1 = aaChecklist_temp[pos_origem];
				aaChecklist_temp.splice(pos_origem, 1);

				//insere o botão na nova posição
				if (pos_origem < pos_destino) {
					aaChecklist_temp.splice(pos_destino-1, 0, temp1);
				} else {
					aaChecklist_temp.splice(pos_destino, 0, temp1);
				}

				salvarOpcoes();
				document.getElementById("botoes_checklist").textContent = '';
				montarBotoesaaChecklist();
			}
			origem = null;
		}, false);

		let ajustandoLista = [];
		for (const [pos, item] of aaChecklist_temp.entries()) {
			let aa = item;
			aa.vinculo = await obterVinculosDescendentes(aa.nm_botao, aa.vinculo); //converto o vínculo antigo, criando a sequencia de vínculos descendentes.

			//insere a visibilidade dentro da AA ajusatando todos as ações
			//AcaoAutomatizada_aaChecklist(nm_botao, tipo, observacao, estado, alerta, salvar, cor, vinculo, visibilidade='sim')
			aa = new AcaoAutomatizada_aaChecklist(aa.nm_botao, aa.tipo, aa.observacao, aa.estado, aa.alerta, aa.salvar, aa.cor, aa.vinculo, (!aa.visibilidade?'sim':aa.visibilidade));
			ajustandoLista.push(aa);

			criaBotao_aaChecklist(pos, aa.nm_botao, aa.tipo, aa.observacao, aa.estado, aa.alerta, aa.salvar, aa.cor, aa.vinculo, aa.visibilidade);
			if (pos == aaChecklist_temp.length-1) {
				//cria espaçador para o último botão
				let espaco = document.createElement("a");
				espaco.id = "espaco_botao_checklist_" + (pos+1);
				espaco.style = "width: .8em;";
				el.appendChild(espaco);
			}
		}
		aaChecklist_temp = ajustandoLista;
	}
}

async function montarBotoesaaNomearPerito() {
	if (typeof(aaNomearPerito_temp) != "undefined") {
		// possibilita mover os botões de lugar arrastando e soltando o elemento
		let el = document.getElementById("botoes_nomearPerito");
		var origem;

		el.addEventListener("dragstart", function(event) {
			if (event.target.parentElement.id == "botoes_nomearPerito") {
				origem = event.target;
				event.target.removeAttribute("data-tooltip");
			}
		}, false);

		el.addEventListener("dragover", function(event) {
			event.preventDefault();
		}, false);

		el.addEventListener("dragenter", function(event) {
			if (!origem) {
				return;
			}
			if (event.target.parentElement.id == "botoes_nomearPerito") {
				if (event.target.id.search("espaco_botao_nomearPerito_") > -1) {
					event.target.className = origem.className;
					event.target.style = origem.style;
					let largura_ideal = event.target.parentElement.offsetWidth - event.target.getBoundingClientRect().left - 35;
					let largura_elemento = origem.offsetWidth - 35;
					event.target.style.width = (largura_elemento > largura_ideal) ? largura_ideal + "px" : largura_elemento + "px";
					event.target.style.backgroundColor = origem.style.backgroundColor;
					event.target.style.opacity = ".5";
					event.target.style.margin = "0";
					event.target.style.boxShadow = "inset 4px 0px 0px white,inset -4px 0px 0px white";
				}
			}
		}, false);

		el.addEventListener("dragleave", function(event) {
			if (event.target.parentElement.id == "botoes_nomearPerito") {
				if (event.target.id.search("espaco_botao_nomearPerito_") > -1) {
					event.target.style.backgroundColor = "white";
					event.target.className = "";
					event.target.style.width = ".8em";
					event.target.style.opacity = "";
				}
			}
		}, false);

		document.addEventListener("drop", function(event) {
			if (!origem) {
				return;
			}
			if (event.target.id.search("espaco_botao_nomearPerito_") < 0) {
				origem = null;
				return;
			}
			if (!event.target.parentElement) {
				origem = null;
				return;
			}
			if (event.target.parentElement.id == "botoes_nomearPerito") {
				event.preventDefault();

				//retira a marca de posição
				event.target.style.backgroundColor = "white";
				event.target.className = "";
				event.target.style.width = ".8em";
				event.target.style.opacity = "0";

				//pega a posição de destino no Array
				let pos_destino = parseInt(event.target.id.replace('espaco_botao_nomearPerito_',''));
				let pos_origem = parseInt(origem.id.replace('botao_nomearPerito_',''));
				let verificador = pos_destino - pos_origem;
				if (verificador == 0 || verificador == 1) {
					return
				}
				//faz as alterações necessárias no array de objetos
				let temp1 = aaNomearPerito_temp[pos_origem];
				aaNomearPerito_temp.splice(pos_origem, 1);

				//insere o botão na nova posição
				if (pos_origem < pos_destino) {
					aaNomearPerito_temp.splice(pos_destino-1, 0, temp1);
				} else {
					aaNomearPerito_temp.splice(pos_destino, 0, temp1);
				}

				salvarOpcoes();
				document.getElementById("botoes_nomearPerito").textContent = '';
				montarBotoesaaNomearPerito();
			}
			origem = null;
		}, false);

		let ajustandoLista = [];
		for (const [pos, item] of aaNomearPerito_temp.entries()) {
            let aa = item;
            aa.tipo_prazo = (!item.tipo_prazo) ? 'Dias Úteis' : item.tipo_prazo; //corrige as AAs criadas no período de teste quando não existia essa variável
            aa.vinculo = (!item.vinculo) ? 'Nenhum' : item.vinculo;
			aa.vinculo = await obterVinculosDescendentes(aa.nm_botao, aa.vinculo); //converto o vínculo antigo, criando a sequencia de vínculos descendentes.
			aa = new AcaoAutomatizada_aaNomearPerito(aa.nm_botao, aa.profissao, aa.perito, aa.prazo, aa.tipo_prazo, aa.designar, aa.modelo, aa.assinar, aa.cor, aa.vinculo, (!aa.visibilidade?'sim':aa.visibilidade));
			ajustandoLista.push(aa);

			criaBotao_aaNomearPerito(pos, aa.nm_botao, aa.profissao, aa.perito, aa.prazo, aa.tipo_prazo, aa.designar, aa.modelo, aa.assinar, aa.cor, aa.vinculo, aa.visibilidade);
			if (pos == aaNomearPerito_temp.length-1) {
				//cria espaçador para o último botão
				let espaco = document.createElement("a");
				espaco.id = "espaco_botao_nomearPerito" + (pos+1);
				espaco.style = "width: .8em;";
				el.appendChild(espaco);
			}
		}
		aaNomearPerito_temp = ajustandoLista;
	}
}

async function montarBotoesaaVariados() {
	if (typeof(aaVariados_temp) != "undefined") {
		let el = document.getElementById("botoes_variados");

		for (const [pos, item] of aaVariados_temp.entries()) {
			let aa = item;
			criaBotao_aaVariados(pos, aa.nm_botao, aa.descricao, aa.temporizador, aa.ativar, aa.objeto);
			if (pos == aaVariados_temp.length-1) {
				//cria espaçador para o último botão
				let espaco = document.createElement("a");
				espaco.id = "espaco_botao_variados_" + (pos+1);
				espaco.style = "width: .8em;";
				el.appendChild(espaco);
			}
		}
	}
}

function montarAtalhosPlugin() {
	preferencias.atalhosPlugin = document.getElementById("atalhosPlugin").value.replace(/(\r\n|\n|\r)/gm, "|");
	return preferencias.atalhosPlugin;
}

function montarFiltrosFavoritos(ancora) {
	let div0 = document.createElement("div");
	div0.innerText = 'Painel Global: ';
	div0.id = 'Painel_global';
	ancora.appendChild(div0);
	ancora.appendChild(document.createElement("br"));
	let div1 = document.createElement("div");
	div1.innerText = 'Atividades: ';
	div1.id = 'Atividades';
	ancora.appendChild(div1);
	ancora.appendChild(document.createElement("br"));
	let div2 = document.createElement("div");
	div2.innerText = 'Comentários: ';
	div2.id = 'Comentários';
	ancora.appendChild(div2);
	ancora.appendChild(document.createElement("br"));
	let div3 = document.createElement("div");
	div3.innerText = 'Processos do Gabinete: ';
	div3.id = 'Processos do Gabinete';
	ancora.appendChild(div3);

	filtros_storage = preferencias.filtros_Favoritos;
	let tabelaAtividades, tabelaComentarios, tabelaProcessosGabinete = [];
	let pos = 0;
	filtros_storage.map(({tabela,nome,camposFixos,camposDinamicos}) => {
		montarBotao(pos, tabela, nome, camposFixos, camposDinamicos);
		pos++;
	});

	document.querySelector('#modulo5_filtros_favoritos_ObterSaldoSIf').checked = preferencias.modulo5_obterSaldoSIF;
	document.querySelector('#modulo5_filtros_favoritos_ObterSaldoSIf').addEventListener('click', salvarOpcoes);
	document.querySelector('#modulo5_filtros_favoritos_juizDaMinuta').checked = preferencias.modulo5_juizDaMinuta;
	document.querySelector('#modulo5_filtros_favoritos_juizDaMinuta').addEventListener('click', salvarOpcoes);
	document.querySelector('#modulo5_filtros_favoritos_conferirTeimosinhaEmLote').checked = preferencias.modulo5_conferirTeimosinhaEmLote;
	document.querySelector('#modulo5_filtros_favoritos_conferirTeimosinhaEmLote').addEventListener('click', salvarOpcoes);
	document.querySelector('#modulo5_filtros_favoritos_semAudienciaDesignada').checked = preferencias.modulo5_processosSemAudienciaDesignada;
	document.querySelector('#modulo5_filtros_favoritos_semAudienciaDesignada').addEventListener('click', salvarOpcoes);
	document.querySelector('#modulo5_filtros_favoritos_semGIGS').checked = preferencias.modulo5_processosSemGigsCadastrado;
	document.querySelector('#modulo5_filtros_favoritos_semGIGS').addEventListener('click', salvarOpcoes);
	document.querySelector('#modulo5_filtros_favoritos_paradosXXdias').checked = preferencias.modulo5_processosParadosHaMaisDeXXDias;
	document.querySelector('#modulo5_filtros_favoritos_paradosXXdias').addEventListener('click', salvarOpcoes);
	document.querySelector('#modulo5_conferirGarimpoEmLote').checked = preferencias.modulo5_conferirGarimpoEmLote;
	document.querySelector('#modulo5_conferirGarimpoEmLote').addEventListener('click', salvarOpcoes);
	document.querySelector('#modulo5_filtros_favoritos_conciliaJT').checked = preferencias.modulo5_obterConcilia;
	document.querySelector('#modulo5_filtros_favoritos_conciliaJT').addEventListener('click', salvarOpcoes);

	function montarBotao(pos, tabela, nome, camposFixos, camposDinamicos) {
		if (!document.getElementById("maisPje_filtrofavorito_" + tabela + "_" + nome)) {
			//divisor
			let divisor = document.createElement("span");
			divisor.innerText = '|';

			//atalho
			let botao = document.createElement("button");
			botao.id = "maisPje_filtrofavorito_" + nome;
			botao.setAttribute("posicao", pos);
			botao.setAttribute('data-tooltip',descreverCampos(tabela, nome, camposFixos, camposDinamicos));
			botao.onclick = function () {
				Swal.fire({
					title: 'Excluir Filtro \n' + nome + '?',
					text: "",
					showCancelButton: true,
					confirmButtonColor: '#3085d6',
					cancelButtonColor: '#d33',
					confirmButtonText: 'Sim, pode excluir!',
					cancelButtonText: 'Não'
				}).then((result) => {
					if (result.value) {
						filtros_storage.splice(parseInt(this.getAttribute("posicao")), 1);
						salvarOpcoes();
						let el = document.getElementById('filtros_favoristos_relatorio_GIGS');
						el.textContent = '';
						montarFiltrosFavoritos(el);
					}
				})
			};
			let botao_span = document.createElement("span");
			botao_span.innerText = nome;

			botao.appendChild(botao_span);
			switch (tabela) {
				case 'Painel_global':
					document.getElementById('Painel_global').appendChild(divisor);
					document.getElementById('Painel_global').appendChild(botao);
					break;
				case 'Atividades':
					document.getElementById('Atividades').appendChild(divisor);
					document.getElementById('Atividades').appendChild(botao);
					break;
				case 'Comentários':
					document.getElementById('Comentários').appendChild(divisor);
					document.getElementById('Comentários').appendChild(botao);
					break;
				case 'Processos do Gabinete':
					document.getElementById('Processos do Gabinete').appendChild(divisor);
					document.getElementById('Processos do Gabinete').appendChild(botao);
					break;
			}
		}
	}

	function descreverCampos(tabela, nome, camposFixos, camposDinamicos) {
		// console.log(JSON.stringify(camposFixos));
		// console.log(JSON.stringify(camposDinamicos));
		let resposta = "Tabela: " + (tabela != "" ? tabela : "---") + "\n";

		switch (tabela) {
			case 'Painel_global':
				resposta += camposFixos.filtrarSegredoDeJustica ? '- com Segredo de Justiça: Sim\n' : '';
				resposta += camposFixos.filtrarDocumentosNaoApreciados ? '- com Documentos não Apreciados: Sim\n' : '';
				resposta += camposFixos.filtrarPrioridadeProcessual ? '- com Prioridade Processual: Sim\n' : '';
				resposta += camposFixos.filtrarAssociados ? '- com Processos Associados: Sim\n' : '';
				resposta += camposFixos.filtrarAlertaProcessual ? '- com Alerta: Sim\n' : '';
				resposta += camposFixos.filtrarPrazosVencidos ? '- com Prazos Vencidos: Sim\n' : '';
				if (camposDinamicos.fpglobal_classeJudicial.toString() != "") {
					resposta += camposDinamicos.fpglobal_classeJudicial ? '- Classe Judicial: ' + camposDinamicos.fpglobal_classeJudicial.toString() + '\n' : '';
				}
				if (camposDinamicos.fpglobal_chips.toString() != "") {
					resposta += camposDinamicos.fpglobal_chips ? '- Chips: ' + camposDinamicos.fpglobal_chips.toString() + '\n' : '';
				}
				if (camposDinamicos.fpglobal_conclusoPara.toString() != "") {
					resposta += camposDinamicos.fpglobal_conclusoPara ? '- Concluso Para: ' + camposDinamicos.fpglobal_conclusoPara.toString() + '\n' : '';
				}
				if (camposDinamicos.fpglobal_tarefaProcesso.toString() != "") {
					resposta += camposDinamicos.fpglobal_tarefaProcesso ? '- Tarefa do Processo: ' + camposDinamicos.fpglobal_tarefaProcesso.toString() + '\n' : '';
				}
				if (camposDinamicos.fpglobal_subCaixa.toString() != "") {
					resposta += camposDinamicos.fpglobal_subCaixa ? '- Sub-caixa: ' + camposDinamicos.fpglobal_subCaixa.toString() + '\n' : '';
				}
				if (camposDinamicos.fpglobal_usuarioResponsavel.toString() != "") {
					resposta += camposDinamicos.fpglobal_usuarioResponsavel ? '- Usuário Responsável: ' + camposDinamicos.fpglobal_usuarioResponsavel.toString() + '\n' : '';
				}
				if (camposDinamicos.fpglobal_faseProcessual.toString() != "") {
					resposta += camposDinamicos.fpglobal_faseProcessual ? '- Fase Processual: ' + camposDinamicos.fpglobal_faseProcessual.toString() + '\n' : '';
				}

				resposta += camposDinamicos.fpglobal_naTarefaDesde ? '- Na Tarefa desde: ' + camposDinamicos.fpglobal_naTarefaDesde + '\n' : '';
				resposta += camposDinamicos.fpglobal_naTarefaate ? '- Na Tarefa até: ' + camposDinamicos.fpglobal_naTarefaate + '\n' : '';
				break;
			case 'Atividades':
				resposta += camposFixos.filtrarNoPrazo ? '- No Prazo: Sim\n' : '';
				resposta += camposFixos.filtrarVencidas ? '- Vencidas: Sim\n' : '';
				resposta += camposFixos.filtrarConcluidas ? '- Concluídas: Sim\n' : '';
				resposta += camposFixos.filtrarAtividadesSemPrazo ? '- Atividades sem prazo: Sim\n' : '';
				resposta += camposFixos.filtrarAtividadesSemPrazoConcluidas ? '- Atividades sem prazo concluídas: Sim\n' : '';
				resposta += camposFixos.filtrarSemDestinatario ? '- Sem destinatário: Sim\n' : '';
				resposta += camposFixos.filtrarMinhasAtividades ? '- Minhas Atividades: Sim\n' : '';
				if (camposDinamicos.fa_classeJudicial.toString() != "") {
					resposta += camposDinamicos.fa_classeJudicial ? '- Classe Judicial: ' + camposDinamicos.fa_classeJudicial.toString() + '\n' : '';
				}

				if (camposDinamicos?.fa_tarefa) {
					if (camposDinamicos?.fa_tarefa?.toString() != "") {
						resposta += camposDinamicos.fa_tarefa ? '- Tarefa do Processo: ' + camposDinamicos.fa_tarefa.toString() + '\n' : '';
					}
				}
				if (camposDinamicos?.fa_fase) {
					if (camposDinamicos?.fa_fase?.toString() != "") {
						resposta += camposDinamicos.fa_fase ? '- Fase do Processo: ' + camposDinamicos.fa_fase.toString() + '\n' : '';
					}
				}

				resposta += camposDinamicos.fa_data_de ? '- De: ' + camposDinamicos.fa_data_de + '\n' : '';
				resposta += camposDinamicos.fa_data_ate ? '- Até: ' + camposDinamicos.fa_data_ate + '\n' : '';
				if (camposDinamicos.fa_tipo.toString() != "") {
					resposta += camposDinamicos.fa_tipo ? '- Tipo: ' + camposDinamicos.fa_tipo.toString() + '\n' : '';
				}
				resposta += camposDinamicos.fa_descricao ? '- Descrição: ' + camposDinamicos.fa_descricao + '\n' : '';
				if (camposDinamicos.fa_responsaveis.toString() != "") {
					resposta += camposDinamicos.fa_responsaveis ? '- Responsável: ' + camposDinamicos.fa_responsaveis.toString() + '\n' : '';
				}
				break;
			case 'Comentários':
				resposta += camposFixos.meusComentarios ? '- No Prazo: Sim\n' : '';
				resposta += camposFixos.comentariosArquivados ? '- Vencidas: Sim\n' : '';
				if (camposDinamicos.fc_classeJudicial.toString() != "") {
					resposta += camposDinamicos.fc_classeJudicial ? '- Classe Judicial: ' + camposDinamicos.fc_classeJudicial.toString() + '\n' : '';
				}

				if (camposDinamicos?.fc_tarefa) {
					if (camposDinamicos?.fc_tarefa?.toString() != "") {
						resposta += camposDinamicos.fc_tarefa ? '- Tarefa do Processo: ' + camposDinamicos.fc_tarefa.toString() + '\n' : '';
					}
				}
				if (camposDinamicos?.fc_fase) {
					if (camposDinamicos?.fc_fase?.toString() != "") {
						resposta += camposDinamicos.fc_fase ? '- Fase do Processo: ' + camposDinamicos.fc_fase.toString() + '\n' : '';
					}
				}

				resposta += camposDinamicos.fc_descricao ? '- Descrição: ' + camposDinamicos.fc_descricao + '\n' : '';
				resposta += camposDinamicos.fc_data_de ? '- De: ' + camposDinamicos.fc_data_de + '\n' : '';
				resposta += camposDinamicos.fc_data_ate ? '- Até: ' + camposDinamicos.fc_data_ate + '\n' : '';
				if (camposDinamicos.fc_autores.toString() != "") {
					resposta += camposDinamicos.fc_autores ? '- Autores: ' + camposDinamicos.fc_autores.toString() + '\n' : '';
				}
				break;
			case 'Processos do Gabinete':
				resposta += camposFixos.filtrarPorPrazo ? '- No Prazo: Sim\n' : '';
				resposta += camposFixos.filtrarAVencer ? '- A Vencer: Sim\n' : '';
				resposta += camposFixos.filtrarVencidos ? '- Vencidos: Sim\n' : '';
				resposta += camposFixos.filtrarProcessosSemResponsavel ? '- Sem responsável: Sim\n' : '';
				resposta += camposFixos.filtrarED ? '- ED: Sim\n' : '';
				resposta += camposFixos.filtrarSumarissimo ? '- Sumaríssimo: Sim\n' : '';
				resposta += camposDinamicos.fpg_inicio_data_de ? '- Início De: ' + camposDinamicos.fpg_inicio_data_de + '\n' : '';
				resposta += camposDinamicos.fpg_inicio_data_ate ? '- Início Até: ' + camposDinamicos.fpg_inicio_data_ate + '\n' : '';
				resposta += camposDinamicos.fpg_fim_data_de ? '- Fim De: ' + camposDinamicos.fpg_fim_data_de + '\n' : '';
				resposta += camposDinamicos.fpg_fim_data_ate ? '- Fim Até: ' + camposDinamicos.fpg_fim_data_ate + '\n' : '';
				if (camposDinamicos.fpg_classeJudicial.toString() != "") {
					resposta += camposDinamicos.fpg_classeJudicial ? '- Classe Judicial: ' + camposDinamicos.fpg_classeJudicial.toString() + '\n' : '';
				}
				if (camposDinamicos.fpg_relator.toString() != "") {
					resposta += camposDinamicos.fpg_relator ? '- Relator: ' + camposDinamicos.fpg_relator.toString() + '\n' : '';
				}
				if (camposDinamicos.fpg_responsavel.toString() != "") {
					resposta += camposDinamicos.fpg_responsavel ? '- Responsável: ' + camposDinamicos.fpg_responsavel.toString() + '\n' : '';
				}
				break;
		}
		return resposta;
	}
}

function desmontarLinha(linha, caracter) {
	var arr = typeof(linha) == "undefined" ? "" : linha.split(caracter);
	var resultado = "";
	for(var h = 0; h < arr.length; h++ ){
		if (arr[h] != "") {
			if (h == 0) {
				resultado += arr[h];
			} else {
				resultado += "\n" + arr[h];
			}
		}
	}
	return resultado;
}

function criaBotao_aaAnexar(id, nm_botao, tipo, descricao, sigilo, modelo, assinar, cor, vinculo, visibilidade) {

	//ajustar o vinculo para um array
	vinculo = Array.isArray(vinculo) ? vinculo : vinculo.split(',');

	let el = document.getElementById("botoes_anexar_documentos");
	//cria espaçador entre os botões
	let espaco = document.createElement("a");
	espaco.id = "espaco_botao_anexar_documentos_" + id;
	espaco.style = "width: 0.8em; background-color: white;";
	el.appendChild(espaco);

	let a = document.createElement("a");
	a.id = "botao_anexar_documentos_" + id;
	a.className = "swal2-confirm swal2-styled";
	a.draggable = "true";
	a.style = "background-color: " + cor + "; min-width: 60px; text-align: center; margin: .3125em 0em .3125em 0em;";
	a.setAttribute('data-tooltip',"\u00bbTipo: " + (tipo != "" ? tipo : "---") + "\n" + "\u00bbDescrição (Título): " + (descricao != "" ? descricao : "---") + "\n" + "\u00bbSigilo: " + (sigilo != "" ? sigilo : "não") + "\n" + "\u00bbModelo: " + (modelo != "" ? modelo : "---") + "\n" + "\u00bbAssinar? " + (assinar != "" ? assinar : "---") + "\n" + "\u00bbVínculo: " + (vinculo.length > 2 ? vinculo[0] + ' e outros' : vinculo[0]) + "\n" + "\u00bbVisibilidade: " + (visibilidade != "" ? visibilidade : "---"));
	a.innerText = nm_botao;
	a.onclick = function (e) {
		if (e.ctrlKey) { //ativa/desativa a visibilidade
			//nm_botao, tipo, descricao, sigilo, modelo, assinar, cor, vinculo, visibilidade='sim'
			let v = (visibilidade.toLowerCase() == "sim") ? "não" : "sim";
			aaAnexar_temp[id] = new AcaoAutomatizada_aaAnexar(nm_botao, tipo, descricao, sigilo, modelo, assinar, cor, vinculo, v);
			salvarOpcoes();
			document.getElementById("botoes_anexar_documentos").textContent = '';
			montarBotoesaaAnexar();
		} else {
			modalEditor(document.getElementById("botao_anexar_documentos_" + id), "anexar", id);
		}
	};

	//visibilidade
	if (visibilidade === 'sim') {
		a.style.setProperty('outline','2px solid rgba(0, 0, 0, 0.1)');
		a.style.setProperty('outline-offset','-2px');
		a.style.setProperty('background-image','none');
	} else {
		a.style.setProperty('outline','2px dashed rgba(255, 255, 255, 1)');
		a.style.setProperty('outline-offset','-2px');
		a.style.setProperty('background-image','linear-gradient(rgba(255, 255, 255, 0.5), rgba(255, 255, 255, 0.5))');
	}

	el.appendChild(a);

	//perfumaria
	if (vinculo.length > 1) {
		let perfumaria = document.createElement("span");
		perfumaria.style = "width: 7px; height: 10px; background-color: white; clip-path: polygon(25% 0%, 70% 0%, 40% 35%, 95% 35%, 20% 100%, 40% 55%, 0% 55%); position: relative; right: 5px; margin: 0.6em -0.3em;"
		el.appendChild(perfumaria);
	}

}

function criaBotao_aaComunicacao(id, nm_botao, tipo, subtipo, tipo_prazo, prazo, descricao, sigilo, modelo, salvar, cor, vinculo, fluxo, visibilidade, comandosEspeciais) {
	//ajustar o vinculo para aum array
	vinculo = Array.isArray(vinculo) ? vinculo : vinculo.split(',');

	let el = document.getElementById("botoes_comunicacao");

	//cria espaçador entre os botões
	let espaco = document.createElement("a");
	espaco.id = "espaco_botao_comunicacao_" + id;
	espaco.style = "width: .8em; background-color: white;";
	el.appendChild(espaco);

	let a = document.createElement("a");
	a.id = "botao_comunicacao_" + id;
	a.className = "swal2-confirm swal2-styled";
	a.draggable = "true";
	a.style = "background-color: " + cor + "; min-width: 60px; text-align: center; margin: .3125em 0em .3125em 0em;";
	a.setAttribute('data-tooltip',"\u00bbTipo: " + (tipo != "" ? tipo : "---") + "\n" + "\u00bbTipo de Prazo: " + (tipo_prazo != "" ? tipo_prazo : "---") + "\n" + "\u00bbPrazo: " + (prazo != "" ? prazo : "---") + "\n" + "\u00bbSubtipo: " + (subtipo != "" ? subtipo : "---") + "\n" + "\u00bbDescrição (Título): " + (descricao != "" ? descricao : "---") + "\n" + "\u00bbSigilo: " + (sigilo != "" ? sigilo : "não") + "\n" + "\u00bbModelo: " + (modelo != "" ? modelo : "---") + "\n" + "\u00bbSalvar? " + (salvar != "" ? salvar : "---") + "\n" + "\u00bbFluxo: " + fluxo + "\n" + "\u00bbVínculo: " + (vinculo.length > 2 ? vinculo[0] + ' e outros' : vinculo[0]) + "\n" + "\u00bbVisibilidade: " + (visibilidade != "" ? visibilidade : "---") + "\n" + "\u00bbComandos Especiais: " + (comandosEspeciais != "" ? comandosEspeciais : "---")); //comandosEspeciais
	a.innerText = nm_botao;
	a.onclick = function (e) {

		if (e.ctrlKey) { //ativa/desativa a visibilidade
			let v = (visibilidade.toLowerCase() == "sim") ? "não" : "sim";
			aaComunicacao_temp[id] = new AcaoAutomatizada_aaComunicacao(nm_botao, tipo, subtipo, tipo_prazo, prazo, descricao, sigilo, modelo, salvar, cor, vinculo, fluxo, v);
			salvarOpcoes();
			document.getElementById("botoes_comunicacao").textContent = '';
			montarBotoesaaComunicacao();
		} else {
			modalEditor(document.getElementById("botao_comunicacao_" + id), "comunicacao", id);
		}

	};

	//visibilidade
	if (visibilidade === 'sim') {
		a.style.setProperty('outline','2px solid rgba(0, 0, 0, 0.1)');
		a.style.setProperty('outline-offset','-2px');
		a.style.setProperty('background-image','none');
	} else {
		a.style.setProperty('outline','2px dashed rgba(255, 255, 255, 1)');
		a.style.setProperty('outline-offset','-2px');
		a.style.setProperty('background-image','linear-gradient(rgba(255, 255, 255, 0.5), rgba(255, 255, 255, 0.5))');

	}

	el.appendChild(a);

	//perfumaria
	if (vinculo.length > 1) {
		let perfumaria = document.createElement("span");
		perfumaria.style = "width: 7px; height: 10px; background-color: white; clip-path: polygon(25% 0%, 70% 0%, 40% 35%, 95% 35%, 20% 100%, 40% 55%, 0% 55%); position: relative; right: 5px; margin: 0.6em -0.3em;"
		el.appendChild(perfumaria);
	}
}

function criaBotao_aaAutogigs(id, nm_botao, tipo, tipo_atividade, prazo, responsavel, responsavel_processo, observacao, salvar, cor, vinculo, visibilidade) {
	//ajustar o vinculo para aum array
	vinculo = Array.isArray(vinculo) ? vinculo : vinculo.split(',');

	let el = document.getElementById("botoes_autogigs");

	//cria espaçador entre os botões
	let espaco = document.createElement("a");
	espaco.id = "espaco_botao_autogigs_" + id;
	espaco.style = "width: .8em; background-color: white;";
	el.appendChild(espaco);

	let a = document.createElement("a");
	a.id = "botao_autogigs_" + id;
	a.className = "swal2-confirm swal2-styled";
	a.draggable = "true";
	a.style = "background-color: " + cor + "; min-width: 60px; text-align: center; margin: .3125em 0em .3125em 0em;";

	let tt = '';
	switch (tipo) {
		case 'comentario':
			tt = "\u00bbTipo de Evento: Comentário\n\u00bbObservação: " + (observacao != "" ? observacao : "---") + "\n" + "\u00bbVisibilidade do lembrete: " + (prazo != "" ? prazo : "---") + "\n\u00bbResponsável pelo processo: " + (responsavel_processo != "" ? responsavel_processo : "---") + "\n" + "\u00bbSalvar Automaticamente? " + (salvar != "" ? salvar : "---") + "\n" + "\u00bbVínculo: " + (vinculo.length > 2 ? vinculo[0] + ' e outros' : vinculo[0]) + "\n" + "\u00bbVisibilidade: " + (visibilidade != "" ? visibilidade : "---");
			break;
		case 'chip':
			tt = "\u00bbTipo de Evento: Chip\n\u00bbTipo de Chip: " + (tipo_atividade != "" ? tipo_atividade : "---") + "\n" + "\u00bbSalvar Automaticamente? " + (salvar != "" ? salvar : "---") + "\n" + "\u00bbVínculo: " + (vinculo.length > 2 ? vinculo[0] + ' e outros' : vinculo[0]) + "\n" + "\u00bbVisibilidade: " + (visibilidade != "" ? visibilidade : "---");
			break;
		case 'lembrete':
			tt = "\u00bbTipo de Evento: Lembrete\n\u00bbDescrição (Título): " + (tipo_atividade != "" ? tipo_atividade : "---") + "\n" + "\u00bbVisibilidade do lembrete: " + (prazo != "" ? prazo : "---") + "\n" + "\u00bbConteúdo: " + (observacao != "" ? observacao : "---") + "\n" + "\u00bbSalvar Automaticamente? " + (salvar != "" ? salvar : "---") + "\n" + "\u00bbVínculo: " + (vinculo.length > 2 ? vinculo[0] + ' e outros' : vinculo[0]) + "\n" + "\u00bbVisibilidade: " + (visibilidade != "" ? visibilidade : "---");
			break;
		case 'nenhum':
			tt = "\u00bbCadeia de Vínculos:\n\n";
			let espaco = 1;
			let map1 = [].map.call(
				vinculo,
				function(v) {
					if (v != "Nenhum") {
						tt += ("    ".repeat(espaco)) + "⨽ " + v + '\n'
						espaco++;
					} else {
						tt += ("    ".repeat(espaco)) + "⨽ Fim" + '\n'
					}
				}
			);

			tt += "\n" + "\u00bbVisibilidade: " + (visibilidade != "" ? visibilidade : "---");

			break;
		default:
			tt = "\u00bbTipo de Evento: " + (tipo != "" ? tipo : "---") + "\n\u00bbTipo da Atividade: " + (tipo_atividade != "" ? tipo_atividade : "---") + "\n" + "\u00bbPrazo: " + (prazo != "" ? prazo : "---") + "\n" + "\u00bbResponsável pelo GIGS: " + (responsavel != "" ? responsavel : "---") + "\n" + "\u00bbResponsável pelo processo: " + (responsavel_processo != "" ? responsavel_processo : "---") + "\n" + "\u00bbObservação: " + (observacao != "" ? observacao : "---") + "\n" + "\u00bbSalvar? " + (salvar != "" ? salvar : "---") + "\n" + "\u00bbVínculo: " + (vinculo.length > 2 ? vinculo[0] + ' e outros' : vinculo[0]) + "\n" + "\u00bbVisibilidade: " + (visibilidade != "" ? visibilidade : "---");
	}

	a.setAttribute('data-tooltip', tt);
	a.innerText = nm_botao;
	a.onclick = function (e) {

		if (e.ctrlKey) { //ativa/desativa a visibilidade
			let v = (visibilidade.toLowerCase() == "sim") ? "não" : "sim";
			aaAutogigs_temp[id] = new AcaoAutomatizada_aaAutogigs(nm_botao, tipo, tipo_atividade, prazo, responsavel, responsavel_processo, observacao, salvar, cor, vinculo, v);
			salvarOpcoes();
			document.getElementById("botoes_autogigs").textContent = '';
			montarBotoesaaAutogigs();

		} else {
			modalEditor(document.getElementById("botao_autogigs_" + id), "autogigs", id);
		}

	};

	if (tipo.toLowerCase() == "preparo") {
		if (typeof cor === 'undefined') {
			a.style.setProperty('background-color', 'darkcyan');
		}
	}

	if (tipo == 'nenhum') {
		a.style.removeProperty('background-image');
		a.style.removeProperty('background-color');
		a.style.background = 'linear-gradient(135deg, #646464 10px, rgb(140, 140, 140) 11px, #CFD0D0 12px)';
		a.style.color = '#646464'
		a.style.setProperty('outline','2px solid #646464');
	}

	//visibilidade
	if (visibilidade === 'sim') {
		a.style.opacity = '1';
		a.style.setProperty('outline-offset','-2px');
		if (tipo != 'nenhum') {
			a.style.setProperty('outline','2px solid rgba(0, 0, 0, 0.1)');
			a.style.setProperty('background-image','none');
		}

	} else {
		a.style.setProperty('outline-offset','-2px');
		if (tipo == 'nenhum') {
			a.style.opacity = '.5';
		} else {
			a.style.setProperty('outline','2px dashed rgba(255, 255, 255, 1)');
			a.style.setProperty('background-image','linear-gradient(rgba(255, 255, 255, 0.5), rgba(255, 255, 255, 0.5))');
		}
	}

	el.appendChild(a);

	//perfumaria
	if (vinculo.length > 1) {
		let perfumaria = document.createElement("span");
		if (tipo == 'nenhum') {
			perfumaria.style = "font-size: 12px; position: relative; right: 11px; ";
			perfumaria.innerText = '🔘'
		} else {
			perfumaria.style = "width: 7px; height: 10px; background-color: white; clip-path: polygon(25% 0%, 70% 0%, 40% 35%, 95% 35%, 20% 100%, 40% 55%, 0% 55%); position: relative; right: 5px; margin: 0.6em -0.3em;"
		}
		el.appendChild(perfumaria);
	}
}

function criaBotao_aaDespacho(id, nm_botao, tipo, descricao, sigilo, modelo, juiz, responsavel, assinar, cor, vinculo, visibilidade, comandosEspeciais) {
	//ajustar o vinculo para aum array
	vinculo = Array.isArray(vinculo) ? vinculo : vinculo.split(',');

	let el = document.getElementById("botoes_despacho");

	//cria espaçador entre os botões
	let espaco = document.createElement("a");
	espaco.id = "espaco_botao_despacho_" + id;
	espaco.style = "width: .8em; background-color: white;";
	el.appendChild(espaco);

	let a = document.createElement("a");
	a.id = "botao_despacho_" + id;
	a.className = "swal2-confirm swal2-styled";
	a.draggable = "true";
	a.style = "background-color: " + cor + "; min-width: 60px; text-align: center; margin: .3125em 0em .3125em 0em;";
	a.setAttribute('data-tooltip',"\u00bbTipo: " + (tipo != "" ? tipo : "---") + "\n" + "\u00bbDescrição (Título): " + (descricao != "" ? descricao : "---") + "\n" + "\u00bbSigilo: " + (sigilo != "" ? sigilo : "não") + "\n" + "\u00bbModelo: " + (modelo != "" ? modelo : "---") + "\n" + "\u00bbJuiz: " + (juiz != "" ? juiz : "---") + "\n" + "\u00bbResponsável: " + (responsavel != "" ? responsavel : "---")  + "\n" + "\u00bbEnviar para Assinatura: " + (assinar != "" ? assinar : "não") + "\n" + "\u00bbVínculo: " + (vinculo.length > 2 ? vinculo[0] + ' e outros' : vinculo[0]) + "\n" + "\u00bbVisibilidade: " + (visibilidade != "" ? visibilidade : "---") + "\n" + "\u00bbComandos Especiais: " + (comandosEspeciais != "" ? comandosEspeciais : "---")); //comandosEspeciais
	a.innerText = nm_botao;
	a.onclick = function (e) {

		if (e.ctrlKey) { //ativa/desativa a visibilidade
			let v = visibilidade.toLowerCase();
			switch (v) {
				case 'sim':
					v = "não";
					break;
				case 'não':
					v = "conhecimento";
					break;
				case 'conhecimento':
					v = "liquidacao";
					break;
				case 'liquidacao':
					v = "execucao";
					break;
				case 'execucao':
					v = "sim";
					break;
				default:
					v = 'sim';
			}
			aaDespacho_temp[id] = new AcaoAutomatizada_aaDespacho(nm_botao, tipo, descricao, sigilo, modelo, juiz, responsavel, assinar, cor, vinculo, v, comandosEspeciais);
			salvarOpcoes();
			document.getElementById("botoes_despacho").textContent = '';
			montarBotoesaaDespacho();

		} else {
			modalEditor(document.getElementById("botao_despacho_" + id), "despacho", id);
		}

	};

	//aparencia visibilidade
	if (visibilidade === 'não') {
		a.style.setProperty('outline','2px dashed rgba(255, 255, 255, 1)');
		a.style.setProperty('outline-offset','-2px');
		a.style.setProperty('background-image','linear-gradient(rgba(255, 255, 255, 0.5), rgba(255, 255, 255, 0.5))');
	} else {
		a.style.setProperty('outline','2px solid rgba(0, 0, 0, 0.1)');
		a.style.setProperty('outline-offset','-2px');
		a.style.setProperty('background-image','none');
	}

	el.appendChild(a);
	//perfumaria visibilidade conhecimento, liquidação e execução
	if (!visibilidade.includes('sim') && !visibilidade.includes('nao')) {
		let perfumaria = document.createElement("span");
		if (visibilidade.includes('conhecimento')) {
			perfumaria.style = "width: 12px; height: 15px; background-color: white; clip-path: polygon(70% 20%, 30% 20%, 30% 70%, 70% 70%, 70% 60%, 40% 60%, 40% 30%, 70% 30%); position: relative; top: 20px; right: 5px; margin: 0.6em -0.5em;z-index: 1;";
		} else if (visibilidade.includes('liquidacao')) {
			perfumaria.style = "width: 12px; height: 15px; background-color: white; clip-path: polygon(40% 20%, 30% 20%, 30% 70%, 70% 70%, 70% 60%, 40% 60%, 40% 30%, 40% 30%); position: relative; top: 20px;right: 5px; margin: 0.6em -0.5em;z-index: 1;"
		} else if (visibilidade.includes('execucao')) {
			perfumaria.style = "width: 12px; height: 15px; background-color: white; clip-path: polygon(70% 20%, 30% 20%, 30% 70%, 70% 70%, 70% 60%, 40% 60%, 40% 50%, 60% 50%, 60% 40%, 40% 40%, 40% 30%, 70% 30%); position: relative; top: 20px; right: 5px; margin: 0.6em -0.5em;z-index: 1;"
		}
		el.appendChild(perfumaria);
	}
	//perfumaria vínculo
	if (vinculo.length > 1) {
		let perfumaria = document.createElement("span");
		perfumaria.style = "width: 7px; height: 10px; background-color: white; clip-path: polygon(25% 0%, 70% 0%, 40% 35%, 95% 35%, 20% 100%, 40% 55%, 0% 55%); position: relative; right: 5px; margin: 0.6em -0.3em;"
		el.appendChild(perfumaria);
	}

}

function criaBotao_aaMovimento(id, nm_botao, destino, chip, responsavel, cor, vinculo, visibilidade) {
	//ajustar o vinculo para aum array
	vinculo = Array.isArray(vinculo) ? vinculo : vinculo.split(',');

	let el = document.getElementById("botoes_movimento");

	//cria espaçador entre os botões
	let espaco = document.createElement("a");
	espaco.id = "espaco_botao_movimento_" + id;
	espaco.style = "width: .8em; background-color: white;";
	el.appendChild(espaco);

	let a = document.createElement("a");
	a.id = "botao_movimento_" + id;
	a.className = "swal2-confirm swal2-styled";
	a.draggable = "true";
	a.style = "background-color: " + cor + "; min-width: 60px; text-align: center; margin: .3125em 0em .3125em 0em;";
	a.setAttribute('data-tooltip',"\u00bbDestino: " + (destino != "" ? destino : "---") + "\n" + "\u00bbLançar Chip: " + (chip != "" ? chip : "---") + "\n" + "\u00bbResponsável pelo Processo: " + (responsavel != "" ? responsavel : "---") + "\n" + "\u00bbVínculo: " + (vinculo.length > 2 ? vinculo[0] + ' e outros' : vinculo[0]) + "\n" + "\u00bbVisibilidade: " + (visibilidade != "" ? visibilidade : "---"));
	a.innerText = nm_botao;
	a.onclick = function (e) {

		if (e.ctrlKey) { //ativa/desativa a visibilidade
			let v = (visibilidade.toLowerCase() == "sim") ? "não" : "sim";
			aaMovimento_temp[id] = new AcaoAutomatizada_aaMovimento(nm_botao, destino, chip, responsavel, cor, vinculo, v);
			salvarOpcoes();
			document.getElementById("botoes_movimento").textContent = '';
			montarBotoesaaMovimento();

		} else {
			modalEditor(document.getElementById("botao_movimento_" + id), "movimento", id);
		}

	};

	//visibilidade
	if (visibilidade === 'sim') {
		a.style.setProperty('outline','2px solid rgba(0, 0, 0, 0.1)');
		a.style.setProperty('outline-offset','-2px');
		a.style.setProperty('background-image','none');
	} else {
		a.style.setProperty('outline','2px dashed rgba(255, 255, 255, 1)');
		a.style.setProperty('outline-offset','-2px');
		a.style.setProperty('background-image','linear-gradient(rgba(255, 255, 255, 0.5), rgba(255, 255, 255, 0.5))');
	}

	el.appendChild(a);

	//perfumaria
	if (vinculo.length > 1) {
		let perfumaria = document.createElement("span");
		perfumaria.style = "width: 7px; height: 10px; background-color: white; clip-path: polygon(25% 0%, 70% 0%, 40% 35%, 95% 35%, 20% 100%, 40% 55%, 0% 55%); position: relative; right: 5px; margin: 0.6em -0.3em;"
		el.appendChild(perfumaria);
	}
}

function criaBotao_aaChecklist(id, nm_botao, tipo, observacao, estado, alerta, salvar, cor, vinculo, visibilidade) {
	//ajustar o vinculo para um array
	vinculo = Array.isArray(vinculo) ? vinculo : vinculo.split(',');

	let el = document.getElementById("botoes_checklist");

	//(nm_botao, tipo, observacao, estado, alerta, salvar, cor, vinculo)

	//cria espaçador entre os botões
	let espaco = document.createElement("a");
	espaco.id = "espaco_botao_checklist_" + id;
	espaco.style = "width: .8em; background-color: white;";
	el.appendChild(espaco);

	let a = document.createElement("a");
	a.id = "botao_checklist_" + id;
	a.className = "swal2-confirm swal2-styled";
	a.draggable = "true";
	a.style = "background-color: " + cor + "; min-width: 60px; text-align: center; margin: .3125em 0em .3125em 0em;";
	a.setAttribute('data-tooltip',"\u00bbTipo: " + (tipo != "" ? tipo : "---") + "\n" + "\u00bbObservação: " + (observacao != "" ? observacao : "---") + "\n" + "\u00bbStatus: " + (estado != "" ? estado : "---") + "\n" + "\u00bbAlerta: " + (alerta != "" ? alerta : "---") + "\n" + "\u00bbSalvar: " + (salvar != "" ? salvar : "---") + "\n" + "\u00bbVínculo: " + (vinculo.length > 2 ? vinculo[0] + ' e outros' : vinculo[0]) + "\n" + "\u00bbVisibilidade: " + (visibilidade != "" ? visibilidade : "---"));
	a.innerText = nm_botao;
	a.onclick = function (e) {

		if (e.ctrlKey) { //ativa/desativa a visibilidade
			let v = (visibilidade.toLowerCase() == "sim") ? "não" : "sim";
			aaChecklist_temp[id] = new AcaoAutomatizada_aaChecklist(nm_botao, tipo, observacao, estado, alerta, salvar, cor, vinculo, v);
			salvarOpcoes();
			document.getElementById("botoes_checklist").textContent = '';
			montarBotoesaaChecklist();

		} else {
			modalEditor(document.getElementById("botao_checklist_" + id), "checklist", id);
		}

	};

	//visibilidade
	if (visibilidade === 'sim') {
		a.style.setProperty('outline','2px solid rgba(0, 0, 0, 0.1)');
		a.style.setProperty('outline-offset','-2px');
		a.style.setProperty('background-image','none');
	} else {
		a.style.setProperty('outline','2px dashed rgba(255, 255, 255, 1)');
		a.style.setProperty('outline-offset','-2px');
		a.style.setProperty('background-image','linear-gradient(rgba(255, 255, 255, 0.5), rgba(255, 255, 255, 0.5))');
	}

	el.appendChild(a);

	//perfumaria
	if (vinculo.length > 1) {
		let perfumaria = document.createElement("span");
		perfumaria.style = "width: 7px; height: 10px; background-color: white; clip-path: polygon(25% 0%, 70% 0%, 40% 35%, 95% 35%, 20% 100%, 40% 55%, 0% 55%); position: relative; right: 5px; margin: 0.6em -0.3em;"
		el.appendChild(perfumaria);
	}
}

function criaBotao_aaNomearPerito(id, nm_botao, profissao, perito, prazo, tipo_prazo, designar, modelo, assinar, cor, vinculo, visibilidade) {

	//ajustar o vinculo para um array
	vinculo = Array.isArray(vinculo) ? vinculo : vinculo.split(',');

	let el = document.getElementById("botoes_nomearPerito");

	//nome=0,profissao=1,perito=2,prazo=3,tipo_prazo=4,designar=5,modelo=6,sigilo=7,assinar=8

	//cria espaçador entre os botões
	let espaco = document.createElement("a");
	espaco.id = "espaco_botao_nomearPerito_" + id;
	espaco.style = "width: .8em; background-color: white;";
	el.appendChild(espaco);

	let a = document.createElement("a");
	a.id = "botao_nomearPerito_" + id;
	a.className = "swal2-confirm swal2-styled";
	a.draggable = "true";
	a.style = "background-color: " + cor + "; min-width: 60px; text-align: center; margin: .3125em 0em .3125em 0em;";
	let tt = "\u00bbProfissão: " + (profissao != "" ? profissao : "---") + "\n"
	tt += "\u00bbPerito: " + (perito != "" ? perito : "---") + "\n";
	tt += "\u00bbPrazo: " + (prazo != "" ? prazo : "---") + "\n";
    tt += "\u00bbTipo de Prazo: " + (tipo_prazo != "" ? tipo_prazo : "---") + "\n";
	tt += "\u00bbDesignar: " + (designar != "" ? designar : "---") + "\n";
	tt += "\u00bbModelo: " + (modelo != "" ? modelo : "---") + "\n";
	tt += "\u00bbAssinar: " + (assinar != "" ? assinar : "---") + "\n";
	tt += "\u00bbVínculo: " + (vinculo.length > 2 ? vinculo[0] + ' e outros' : vinculo[0]) + "\n";
	tt += "\u00bbVisibilidade: " + (visibilidade != "" ? visibilidade : "---");
	a.setAttribute('data-tooltip', tt);

	a.innerText = nm_botao;
	a.onclick = function (e) {

		if (e.ctrlKey) { //ativa/desativa a visibilidade
			let v = (visibilidade.toLowerCase() == "sim") ? "não" : "sim";
			aaNomearPerito_temp[id] = new AcaoAutomatizada_aaNomearPerito(nm_botao, profissao, perito, prazo, tipo_prazo, designar, modelo, assinar, cor, vinculo, v);
			salvarOpcoes();
			document.getElementById("botoes_nomearPerito").textContent = '';
			montarBotoesaaNomearPerito();

		} else {
			modalEditor(document.getElementById("botao_nomearPerito_" + id), "nomearPerito", id);
		}

	};

	//visibilidade
	if (visibilidade === 'sim') {
		a.style.setProperty('outline','2px solid rgba(0, 0, 0, 0.1)');
		a.style.setProperty('outline-offset','-2px');
		a.style.setProperty('background-image','none');
	} else {
		a.style.setProperty('outline','2px dashed rgba(255, 255, 255, 1)');
		a.style.setProperty('outline-offset','-2px');
		a.style.setProperty('background-image','linear-gradient(rgba(255, 255, 255, 0.5), rgba(255, 255, 255, 0.5))');
	}

	el.appendChild(a);

	//perfumaria
	if (vinculo.length > 1) {
		let perfumaria = document.createElement("span");
		perfumaria.style = "width: 7px; height: 10px; background-color: white; clip-path: polygon(25% 0%, 70% 0%, 40% 35%, 95% 35%, 20% 100%, 40% 55%, 0% 55%); position: relative; right: 5px; margin: 0.6em -0.3em;"
		el.appendChild(perfumaria);
	}
}

function criaBotao_aaVariados(id, nm_botao, descricao, temporizador, ativar=false, objeto) {
	let el = document.getElementById("botoes_variados");

	//cria espaçador entre os botões
	let espaco = document.createElement("a");
	espaco.id = "espaco_botao_variados_" + id;
	espaco.style = "width: .8em; background-color: white;";
	el.appendChild(espaco);

	let a = document.createElement("a");
	a.id = "botao_variados_" + id
	a.className = "swal2-confirm swal2-styled";
	a.draggable = "true";
	a.style = "background-color: orangered; min-width: 60px; text-align: center; margin: .3125em 0em .3125em 0em;";
	a.style.setProperty('background-image','repeating-linear-gradient(45deg, rgba(0,0,0,0.1) 0px, rgba(0,0,0,0.1) 5px, transparent 5px, transparent 10px)');

	//criar tooltip
	let tt = (descricao != "" ? descricao : "---") + "\n\n" + "\u00bbTemporizador: " + (temporizador != "" ? temporizador : "---") + " segundo(s)\n" + "\u00bbAtivada: " + (ativar ? 'Sim' : "Não");
	if (objeto) {
		tt += "\n";
		for (const [key, value] of Object.entries(objeto)) {
			tt += "\n\u00bb" + key + ": " + value;
		}
	}


	a.setAttribute('data-tooltip', tt);
	a.innerText = nm_botao;
	a.onclick = function (e) {
		modalEditorEditar(document.getElementById("botao_variados_" + id), 'variados', id);
	};

	el.appendChild(a);
}

function listaAcoesAutomatizadas(vinculo) {
	vinculo = (typeof(vinculo) == "undefined" || vinculo == "undefined") ? "Nenhum" : vinculo;
	console.log("vinculo: " + vinculo)

	vinculo = Array.isArray(vinculo) ? vinculo : vinculo.split(','); //converte em string
	vinculo = vinculo[0];

	let lista = "<option style='background-color: coral;' value='Nenhum'";
	lista += "Nenhum" == vinculo ? " selected> " : ">";
	lista += " Nenhum </option>";

	lista += '<optgroup label="Anexar Documentos" style="background-color: lightgray;">';
	let teste = [].map.call(aaAnexar_temp,function(item) {
		lista += "<option style='background-color: #d3d3d35e;' value='Anexar|" + item.nm_botao + "'";
		lista += ("Anexar|" + item.nm_botao == vinculo) ? " selected> Anexar|" + item.nm_botao : " > Anexar|" + item.nm_botao;
		lista += " </option>";
	});
	lista += '</optgroup>';

	lista += '<optgroup label="Intimação/Expediente" style="background-color: coral;">';
	teste = [].map.call(aaComunicacao_temp,function(item) {
		lista += "<option style='background-color: #ff7f5021;' value='Comunicação|" + item.nm_botao + "'";
		lista += ("Comunicação|" + item.nm_botao == vinculo) ? " selected> Comunicação|" + item.nm_botao : " > Comunicação|" + item.nm_botao;
		lista += " </option>";
	});
	lista += '</optgroup>';

	lista += '<optgroup label="AutoGIGS" style="background-color: lightgray;">';
	teste = [].map.call(aaAutogigs_temp,function(item) {
		if (item.nm_botao.includes('[concluir]')) {
			lista += "<option style='background-color: #d3d3d35e; color: coral;' value='AutoGigs|" + item.nm_botao + "'";
			lista += ("AutoGigs|" + item.nm_botao == vinculo) ? " selected> AutoGigs|" + item.nm_botao : " > AutoGigs|" + item.nm_botao;
		} else {
			lista += "<option style='background-color: #d3d3d35e;' value='AutoGigs|" + item.nm_botao + "'";
			lista += ("AutoGigs|" + item.nm_botao == vinculo) ? " selected> AutoGigs|" + item.nm_botao : " > AutoGigs|" + item.nm_botao;
		}
		lista += " </option>";
	});
	lista += '</optgroup>';

	lista += '<optgroup label="Despacho" style="background-color: coral;">';
	teste = [].map.call(aaDespacho_temp,function(item) {
		lista += "<option style='background-color: #ff7f5021;' value='Despacho|" + item.nm_botao + "'";
		lista += ("Despacho|" + item.nm_botao == vinculo) ? " selected> Despacho|" + item.nm_botao : " > Despacho|" + item.nm_botao;
		lista += " </option>";
	});
	lista += '</optgroup>';

	lista += '<optgroup label="Movimento" style="background-color: lightgray;">';
	teste = [].map.call(aaMovimento_temp,function(item) {
		lista += "<option style='background-color: #d3d3d35e;' value='Movimento|" + item.nm_botao + "'";
		lista += ("Movimento|" + item.nm_botao == vinculo) ? " selected> Movimento|" + item.nm_botao : " > Movimento|" + item.nm_botao;
		lista += " </option>";
	});
	lista += '</optgroup>';

	lista += '<optgroup label="Checklist" style="background-color: coral;">';
	teste = [].map.call(aaChecklist_temp,function(item) {
		lista += "<option style='background-color: #ff7f5021;' value='Checklist|" + item.nm_botao + "'";
		lista += ("Checklist|" + item.nm_botao == vinculo) ? " selected> Checklist|" + item.nm_botao : " > Checklist|" + item.nm_botao;
		lista += " </option>";
	});
	lista += '</optgroup>';

	lista += '<optgroup label="Itens de Menu" style="background-color: lightgray;">';
	teste = [].map.call(aaItemMenuDetalhes,function(item) {
		lista += "<option style='background-color: #d3d3d35e;' value='Clicar em|" + item + "'";
		lista += ("Clicar em|" + item == vinculo) ? " selected> Clicar em|" + item : " > Clicar em|" + item;
		lista += " </option>";
	});
	lista += '</optgroup>';

	//AA para RETIFICAR AUTUAÇÃO
	lista += '<optgroup label="Retificar Autuação" style="background-color: coral;">';
	let aaItemRetificarAutuacao = [
		['botao_retificar_autuacao_7','addAutor'],
		['botao_retificar_autuacao_8','addRéu'],
		['botao_retificar_autuacao_0','addUnião'],
		['botao_retificar_autuacao_10','addMPT'],
		['botao_retificar_autuacao_3','addLeiloeiro'],
		['botao_retificar_autuacao_4','addPerito'],
		['botao_retificar_autuacao_5','addTestemunha'],
		['botao_retificar_autuacao_6','addTerceiro'],
		['botao_retificar_autuacao_100Digital','Juízo 100% Digital'],
		['botao_retificar_autuacao_tutelaLiminar','Pedido de Tutela'],
		['botao_retificar_autuacao_Falencia','Falência/Rec.Judicial'],
		['botao_retificar_autuacao_assunto','Assunto'],
		['botao_retificar_autuacao_justicaGratuita','Justiça Gratuita'],
		['botao_retificar_autuacao_associarProcesso','Associar Processo']];
	teste = [].map.call(aaItemRetificarAutuacao,function(item) {
		lista += "<option style='background-color: #ff7f5021;' value='RetificarAutuação|" + item[1] + "'";
		lista += ('RetificarAutuação|' + item[1] == vinculo) ? " selected> RetificarAutuação|" + item[1] : "> RetificarAutuação|" + item[1];
		lista += " </option>";
	});
	lista += '</optgroup>';

	//AA para LANÇAR MOVIMENTOS
	lista += '<optgroup label="Lançar Movimento" style="background-color: lightgray;">';
	teste = [].map.call(preferencias.aaLancarMovimentos,function(item) {
		lista += "<option style='background-color: #ff7f5021;' value='LançarMovimento|" + item.nm_botao + "'";
		lista += ("LançarMovimento|" + item.nm_botao == vinculo) ? " selected> LançarMovimento|" + item.nm_botao : " > LançarMovimento|" + item.nm_botao;
		lista += " </option>";
	});
	lista += '</optgroup>';

	//AA para VARIADOS
	lista += '<optgroup label="Variados" style="background-color: coral;">';
	teste = [].map.call(aaVariados_temp,function(item) {
		if (['Atualizar Pagina','Fechar Pagina'].includes(item.nm_botao)) {
			console.log("   |____ " + item.nm_botao + "|" + item.nm_botao)
			lista += "<option style='background-color: #ff7f5021;' value='" + item.nm_botao + "|" + item.nm_botao + "'";
			lista += (item.nm_botao + "|" + item.nm_botao == vinculo) ? " selected> " + item.nm_botao + "|" + item.nm_botao : " > " + item.nm_botao + "|" + item.nm_botao;
			lista += " </option>";
		} else {
			lista += "<option style='background-color: #ff7f5021;' value='Variados|" + item.nm_botao + "'";
			lista += ("Variados|" + item.nm_botao == vinculo) ? " selected> Variados|" + item.nm_botao : " > Variados|" + item.nm_botao;
			lista += " </option>";
		}
	});
	lista += '</optgroup>';

	lista += '</optgroup>';
	return lista;
}

function modalEditor(elemento_pai, tipo, id) {
	let posy = elemento_pai.getBoundingClientRect().top + window.pageYOffset;
	let posx = elemento_pai.getBoundingClientRect().left;
	let largura = elemento_pai.getBoundingClientRect().width;
	let altura = elemento_pai.getBoundingClientRect().height;

	let cssMenu = 'display: grid; grid-template-rows: repeat(4, 1fr); width: 100%; font-size: 1.3em; background-color: white; position: absolute;top: ' + altura + 'px; cursor: pointer; border-radius: 0 0 3px 3px;box-shadow: 0px 4px 6px 0px rgba(62, 62, 62, 0.72);align-items: center;';
	let cssItemMenu = 'padding: 0 5px 0 5px;font-style: normal;height: ' + altura + 'px; display: flex; justify-content: center; align-items: center;';
	let cssItemMenuChamativo = 'padding: 0 5px 0 5px;font-style: normal;height: ' + altura + 'px; display: flex; justify-content: center; align-items: center; border: 1px dashed orangered;background-color: cornsilk;';

	//*******painel base
	let el = document.body;
	let painel = document.createElement("div");
	painel.id = 'painel_' + id;
	painel.setAttribute("posicao",id);
	painel.style = 'position: absolute; background-color: rgba(255, 255, 255, 0.77); width: ' + largura + 'px; height: ' + altura + 'px;  z-index: 10000; display: flex; align-items: center; justify-content: center;  text-align: center; top: ' + posy + 'px;left: ' + posx + 'px;box-shadow: rgba(62, 62, 62, 0.72) 0px 4px 6px 0px;';
	painel.className = 'fade-in';

	//*******janela modal
	let janela_modal = document.createElement("div");
	janela_modal.id = 'janela_modal_' + id;
	janela_modal.style = cssMenu;
	janela_modal.className = 'fade-in';
	janela_modal.onmouseleave = function (e) {
		this.parentElement.remove();
	};

	//*********criar botão editar
	let bt_editar = document.createElement("div");
	bt_editar.id = "botao_editar";
	bt_editar.innerText = "Editar";
	bt_editar.style = cssItemMenu;
	bt_editar.onmouseenter = function() {
		this.style.setProperty("background-color","#e2e2e2");
	}
	bt_editar.onmouseleave = function () {
		this.style.setProperty("background-color","initial");
	};
	bt_editar.onclick = function () {
		modalEditorEditar(elemento_pai, tipo, id);
		painel.remove();
	};

	let bt_clonar = document.createElement("div");
	bt_clonar.id = "botao_clonar";
	bt_clonar.innerText = "Clonar";
	bt_clonar.style = cssItemMenu;
	bt_clonar.onmouseenter = function() {
		this.style.setProperty("background-color","#e2e2e2");
	}
	bt_clonar.onmouseleave = function () {
		this.style.setProperty("background-color","initial");
	};
	bt_clonar.onclick = function () {
		modalEditorClonar(elemento_pai, tipo, id);
		painel.remove();
	};

	//*********criar botão excluir
	let bt_excluir = document.createElement("div");
	bt_excluir.id = "botao_excluir";
	bt_excluir.innerText = "Excluir";
	bt_excluir.style = cssItemMenu;
	bt_excluir.onmouseenter = function() {
		this.style.setProperty("background-color","#e2e2e2");
	}
	bt_excluir.onmouseleave = function (e) {
		this.style.setProperty("background-color","initial");
	};
	bt_excluir.onclick = function () {
		modalEditorExcluir(elemento_pai, tipo, id);
		painel.remove();
	};

	//*********criar botão exportar
	let bt_exportar = document.createElement("div");
	bt_exportar.id = "botao_exportar";
	bt_exportar.innerText = "Exportar";
	bt_exportar.style = cssItemMenu;
	bt_exportar.onmouseenter = function() {
		this.style.setProperty("background-color","#e2e2e2");
	}
	bt_exportar.onmouseleave = function (e) {
		this.style.setProperty("background-color","initial");
	};
	bt_exportar.onclick = function () {
		modalEditorExportar(elemento_pai, tipo, id);
		painel.remove();
	};

	//*********criar botão vínculo
	let bt_vinculo = document.createElement("div");
	bt_vinculo.id = "botao_exportar";
	bt_vinculo.innerText = "Vínculos";
	bt_vinculo.style = cssItemMenuChamativo;
	bt_vinculo.onmouseenter = function() {
		this.style.setProperty("background-color","#e2e2e2");
	}
	bt_vinculo.onmouseleave = function (e) {
		this.style.setProperty("background-color","initial");
	};
	bt_vinculo.onclick = function () {
		modalEditorVinculo(elemento_pai, tipo, id);
		painel.remove();
	};

	janela_modal.appendChild(bt_editar);
	janela_modal.appendChild(bt_clonar);
	janela_modal.appendChild(bt_excluir);
	janela_modal.appendChild(bt_exportar);
	janela_modal.appendChild(bt_vinculo);
	painel.appendChild(janela_modal);
	document.body.appendChild(painel);
}

async function modalEditorEditar(elemento_pai, tipo, id) {
	if (tipo == "anexar") {

		let regraDoSigilo = 0; //nenhum
		if (aaAnexar_temp[id].sigilo.includes('Polo Ativo') && aaAnexar_temp[id].sigilo.includes('Polo Passivo') && aaAnexar_temp[id].sigilo.includes('Perito')) {
			regraDoSigilo = 5; //todos
		} else if (aaAnexar_temp[id].sigilo.includes('Polo Ativo') && aaAnexar_temp[id].sigilo.includes('Polo Passivo')) {
			regraDoSigilo = 3; //ativo e passivo
		} else if (aaAnexar_temp[id].sigilo.includes('Polo Ativo')) {
			regraDoSigilo = 1; //ativo
		} else if (aaAnexar_temp[id].sigilo.includes('Polo Passivo')) {
			regraDoSigilo = 2; //passivo
		} else if (aaAnexar_temp[id].sigilo.includes('Perito')) {
			regraDoSigilo = 4; //perito
		}

		const { value: result } = await Swal.fire({
			title: '    ',
			html:
			'<span style="font-weight: bold;"> Nome do Botão <br><i style="font-size: 0.8em;font-weight: normal;font-style: normal;text-align: left; color: darkcyan;"><br>aceita a expressão <b>[anexos]</b> que irá possibilitar a juntada de vários pdfs na certidão</i></span>' +
			'<input id="swal-input1" class="swal2-input" value="' + aaAnexar_temp[id].nm_botao + '">' +
			'<span style="font-weight: bold;"> Tipo de Documento </span>' +
			'<input id="swal-input2" class="swal2-input" value="' + aaAnexar_temp[id].tipo + '">' +
			'<span style="font-weight: bold;"> Descrição (Título) </span>' +
			'<input id="swal-input3" class="swal2-input" value="' + aaAnexar_temp[id].descricao + '">' +
			'<span style="font-weight: bold;"> Sigilo </span><br>' +
			'<select id="swal-input4" class="swal2-select" style="background-color: white;width: 49%;border: 1px solid #d9d9d9;border-radius: .1875em 0 0 .1875em;box-shadow: inset 0 1px 1px rgba(0,0,0,.06);height: 2.625em;padding: 0 .75em;">' +
				'<option value="nao"' + (aaAnexar_temp[id].sigilo.toLowerCase().includes('nao') ? 'selected' : '')  + '> Não </option>' +
				'<option value="sim"' + (aaAnexar_temp[id].sigilo.toLowerCase().includes('sim') ? 'selected' : '')  + '> Sim </option>' +
			'</select>' +
			'<select id="swal-input4-1" class="swal2-select" style="background-color: white;width: 49%;border: 1px solid #d9d9d9;border-radius: 0 .1875em .1875em 0;box-shadow: inset 0 1px 1px rgba(0,0,0,.06);height: 2.625em;padding: 0 .75em;border-left: 0;">' +
				'<optgroup label="Visibilidade do Documento">' +
				'<option value="Nenhum"' + (regraDoSigilo==0 ? 'selected' : '') + '> Nenhum </option>' +
				'<option value="Polo Ativo"' + (regraDoSigilo==1 ? 'selected' : '') + '> apenas Polo Ativo </option>' +
				'<option value="Polo Passivo"' + (regraDoSigilo==2 ? 'selected' : '') + '> apenas Polo Passivo </option>' +
				'<option value="Polo Ativo + Polo Passivo"' + (regraDoSigilo==3 ? 'selected' : '') + '> Polo Ativo + Polo Passivo </option>' +
				'<option value="Perito"' + (regraDoSigilo==4 ? 'selected' : '') + '> apenas Perito </option>' +
				'<option value="Todos"' + (regraDoSigilo==5 ? 'selected' : '') + '> Polo Ativo + Polo Passivo + Perito </option>' +
				'<option value="Perguntar"' + (regraDoSigilo==6 ? 'selected' : '') + '> Perguntar </option>' +
				'</optgroup>' +
			'</select><br>' +
			'<span style="font-weight: bold;"> Modelo </span>' +
			'<input id="swal-input5" class="swal2-input" value="' + aaAnexar_temp[id].modelo + '">' +
			'<span style="font-weight: bold;"> Assinar </span>' +
			'<br><select id="swal-input6" class="swal2-select" style="background-color: white;width: 100%;border: 1px solid #d9d9d9;border-radius: .1875em;box-shadow: inset 0 1px 1px rgba(0,0,0,.06);height: 2.625em;padding: 0 .75em;">' +
				'<option value="nao"' + (aaAnexar_temp[id].assinar.toLowerCase().includes('nao') ? 'selected' : '')  + '> Não </option>' +
				'<option value="sim"' + (aaAnexar_temp[id].assinar.toLowerCase().toLowerCase().includes('sim') ? 'selected' : '')  + '> Sim </option>' +
			'</select><br>' +
			'<span style="font-weight: bold;"> Cor do Botão </span>' +
			'<input id="swal-input7" class="swal2-input" type="color" value="' + aaAnexar_temp[id].cor + '">' +
			'<br><br><label class="container">' +
			'<input type="checkbox" id="swal-input9" ' + (aaAnexar_temp[id].visibilidade.toLowerCase().includes('sim') ? 'checked' : '') + '><span style="position: relative; padding-right: 15px; top: 2px; margin-left: -10px; font-weight: bold;">Visível na Janela Detalhes?</span>' +
			'<span class="checkmark"></span>' +
			'<input id="swal-input_vinculo" style="display:none;" value="' + aaAnexar_temp[id].vinculo + '">' +
			'</label>',
			confirmButtonText: 'Salvar',
			focusConfirm: false,
			preConfirm: () => {

				let sw4 = document.getElementById('swal-input4').value.toLowerCase();
				let sw41 = document.getElementById('swal-input4-1').value.toLowerCase();

				if (sw4.toLowerCase().includes('sim')) {
					if (!sw4.includes('[') && !sw4.includes(']')) {
						switch (sw41) {
							case 'nenhum':
								break;
							case 'polo ativo':
								sw4 += "[Polo Ativo]";
								break;
							case 'polo passivo':
								sw4 += "[Polo Passivo]";
								break;
							case 'polo ativo + polo passivo':
								sw4 += "[Polo Ativo Polo Passivo]";
								break;
							case 'perito':
								sw4 += "[Perito]";
								break;
							case 'todos':
								sw4 += "[Polo Ativo Polo Passivo Perito]";
								break;
							case 'perguntar':
								sw4 += "[Perguntar]";
								break;
						}
					}
				}

				return [
					document.getElementById('swal-input1').value,
					document.getElementById('swal-input2').value,
					document.getElementById('swal-input3').value,
					sw4,
					document.getElementById('swal-input5').value,
					document.getElementById('swal-input6').value,
					document.getElementById('swal-input7').value,
					document.getElementById('swal-input_vinculo')?.value,
					document.getElementById('swal-input9').checked ? "sim" : "não"
				]
			}
		});

		if (result) {
			aaAnexar_temp[id] = new AcaoAutomatizada_aaAnexar(result[0], result[1], result[2], result[3], result[4], result[5], result[6], result[7], result[8]);
			salvarOpcoes();
			document.getElementById("botoes_anexar_documentos").textContent = '';
			montarBotoesaaAnexar();
		}
	} else if (tipo == "comunicacao") {
		aaComunicacao_temp[id].fluxo = (!aaComunicacao_temp[id].fluxo) ? 'nao' : aaComunicacao_temp[id].fluxo; //correção de bug que não abre a AA quando ela é anterior a existência do fluxo

		const { value: result } = await Swal.fire({
			title: '    ',
			html:
			'<span style="font-weight: bold;"> Nome do Botão </span>' +
			'<input id="swal-inputNomeBotao" class="swal2-input" value="' + aaComunicacao_temp[id].nm_botao + '">' +
			'<div style="padding: 20px;border: 2px solid darkcyan;border-radius: 6px;margin-bottom: 10px;background-color: gainsboro;">'+
			'<span style="font-weight: bold;"> Comandos Especiais <br>' +
			'<i style="font-size: 0.8em;font-weight: normal;font-style: normal;text-align: left; color: darkcyan;">' +
			'<br>Clique no botão abaixo para configurações adicionais após a elaboração do expediente<br>' +
			'</u></p></i></span>' +
			'</i></span>' +
			'<button type="button" id="config_comandosEspeciaisComunicacao" class="swal2-confirm swal2-styled" style="display: inline-block;background-color: darkcyan;padding: 9px 56px;" aria-label="">Configurar</button>' +
			'<div style="display: grid;grid-template-columns: 10fr 1fr;align-items: center;">' +
			'<textarea id="swal-input_comandosEspeciais" class="swal2-textarea" style="background-color: white;font-size: 0.8em;" disabled>' + aaComunicacao_temp[id]?.comandosEspeciais + '</textarea>' +
			'<div id="apagar_config_comandosEspeciaisComunicacao" data-tooltip="Apagar"><i class="icone trash-alt t16" style="padding: 0px 5px; background-color: #545454;pointer-events: none;" pos="0"></i></div></div>' +
			'</div>' +

			'<span style="font-weight: bold;"> Tipo de Expediente </span>' +
			'<input id="swal-input2" class="swal2-input" value="' + aaComunicacao_temp[id].tipo + '">' +
			'<span style="font-weight: bold;"> Tipo de Documento (na elaboração do ato) </span>' +
			'<input id="swal-input3" class="swal2-input" value="' + aaComunicacao_temp[id].subtipo + '">' +
			'<span style="font-weight: bold;"> Tipo de Prazo </span>' +
			'<br><select id="swal-input99" class="swal2-select" style="background-color: white;width: 100%;border: 1px solid #d9d9d9;border-radius: .1875em;box-shadow: inset 0 1px 1px rgba(0,0,0,.06);height: 2.625em;padding: 0 .75em;">' +
				'<option value="Sem Prazo"' + (aaComunicacao_temp[id].tipo_prazo.toLowerCase().includes('sem prazo') ? 'selected' : '')  + '> Sem Prazo </option>' +
				'<option value="Dias Úteis"' + (aaComunicacao_temp[id].tipo_prazo.toLowerCase().includes('dias úteis') ? 'selected' : '')  + '> Dias Úteis </option>' +
				'<option value="Data Certa"' + (aaComunicacao_temp[id].tipo_prazo.toLowerCase().includes('data certa') ? 'selected' : '')  + '> Data Certa </option>' +
				'<option value="Dias Corridos"' + (aaComunicacao_temp[id].tipo_prazo.toLowerCase().includes('dias corridos') ? 'selected' : '')  + '> Dias Corridos </option>' +
			'</select><br>' +
			'<span style="font-weight: bold;"> Prazo </span>' +
			'<input id="swal-input4" class="swal2-input" value="' + aaComunicacao_temp[id].prazo + '">' +
			'<span style="font-weight: bold;"> Descrição (Título) </span>' +
			'<input id="swal-input5" class="swal2-input" value="' + aaComunicacao_temp[id].descricao + '">' +
			'<span style="font-weight: bold;"> Sigilo </span>' +
			'<br><select id="swal-input6" class="swal2-select" style="background-color: white;width: 100%;border: 1px solid #d9d9d9;border-radius: .1875em;box-shadow: inset 0 1px 1px rgba(0,0,0,.06);height: 2.625em;padding: 0 .75em;">' +
				'<option value="nao"' + (aaComunicacao_temp[id].sigilo.toLowerCase().includes('nao') ? 'selected' : '')  + '> Não </option>' +
				'<option value="sim"' + (aaComunicacao_temp[id].sigilo.toLowerCase().includes('sim') ? 'selected' : '')  + '> Sim </option>' +
			'</select><br>' +
			'<span style="font-weight: bold;"> Modelo </span>' +
			'<input id="swal-input7" class="swal2-input" value="' + aaComunicacao_temp[id].modelo + '">' +
			'<span style="font-weight: bold;"> Salvar </span>' +
			'<br><select id="swal-input8" class="swal2-select" style="background-color: white;width: 100%;border: 1px solid #d9d9d9;border-radius: .1875em;box-shadow: inset 0 1px 1px rgba(0,0,0,.06);height: 2.625em;padding: 0 .75em;">' +
				'<option value="nao"' + (aaComunicacao_temp[id].salvar.toLowerCase().includes('nao') ? 'selected' : '')  + '> Não </option>' +
				'<option value="sim"' + (aaComunicacao_temp[id].salvar.toLowerCase().includes('sim') ? 'selected' : '')  + '> Sim </option>' +
			'</select><br>' +
			'<span style="font-weight: bold;"> Mover para a Tarefa "Preparar Comunicação/Expediente" </span>' +
			'<br><select id="swal-input11" class="swal2-select" style="background-color: white;width: 100%;border: 1px solid #d9d9d9;border-radius: .1875em;box-shadow: inset 0 1px 1px rgba(0,0,0,.06);height: 2.625em;padding: 0 .75em;">' +
				'<option value="nao"' + (aaComunicacao_temp[id].fluxo.toLowerCase().includes('nao') ? 'selected' : '')  + '> Não </option>' +
				'<option value="sim"' + (aaComunicacao_temp[id].fluxo.toLowerCase().includes('sim') ? 'selected' : '')  + '> Sim </option>' +
			'</select><br>' +
			'<span style="font-weight: bold;"> Cor do Botão </span>' +
			'<input id="swal-input9" class="swal2-input" type="color" value="' + aaComunicacao_temp[id].cor + '">' +
			'<br><br><label class="container">' +
			'<input type="checkbox" id="swal-input12" ' + (aaComunicacao_temp[id].visibilidade.toLowerCase().includes('sim') ? 'checked' : '') + '><span style="position: relative; padding-right: 15px; top: 2px; margin-left: -10px; font-weight: bold;">Visível na Janela Detalhes?</span>' +
			'<span class="checkmark"></span>' +
			'<input id="swal-input_vinculo" style="display:none;" value="' + aaComunicacao_temp[id].vinculo + '">' +
			'</label>',
			confirmButtonText: 'Salvar',
			focusConfirm: false,
			preConfirm: () => {
				return [
					document.getElementById('swal-inputNomeBotao').value,
					document.getElementById('swal-input2').value,
					document.getElementById('swal-input3').value,
					document.getElementById('swal-input99').value,
					document.getElementById('swal-input4').value,
					document.getElementById('swal-input5').value,
					document.getElementById('swal-input6').value,
					document.getElementById('swal-input7').value,
					document.getElementById('swal-input8').value,
					document.getElementById('swal-input9').value,
					document.getElementById('swal-input_vinculo')?.value,
					document.getElementById('swal-input11').value,
					document.getElementById('swal-input12').checked ? "sim" : "não",
					document.getElementById('swal-input_comandosEspeciais').value, //comandos especiais
				]
			}
		});

		if (result) {

			aaComunicacao_temp[id] = new AcaoAutomatizada_aaComunicacao(result[0], result[1], result[2], result[3], result[4], result[5], result[6], result[7], result[8], result[9], result[10], result[11], result[12], result[13]);
			salvarOpcoes();
			document.getElementById("botoes_comunicacao").textContent = '';
			montarBotoesaaComunicacao();
		}
	} else if (tipo == "autogigs") {
		function texto_html() {
			let var1 = '';
			switch (aaAutogigs_temp[id].tipo) {
				case 'comentario':
					var1 = '<span style="font-weight: bold;"> Nome do Botão <br><i style="font-size: 0.8em;font-weight: normal;font-style: normal;text-align: left; color: darkcyan;"><br>aceita a expressão <b>[concluir]</b> que irá finalizar um COMENTÁRIO observando o texto descrito no campo <u>Comentário</u>. <p style="text-align: center;font-style: italic;">Ex: se usada a expressão [concluir] no nome desta ação, ela irá concluir qualquer comentário que possua em seu texto a expressão <u>' + aaAutogigs_temp[id].observacao + '</u></p></i></span>' +
					'<input id="swal-input1" class="swal2-input" value="' + aaAutogigs_temp[id].nm_botao + '">' +
					'<span style="font-weight: bold;"> Tipo de Ação Automatizada </span>' +
					'<input id="swal-input2" class="swal2-input" value="' + aaAutogigs_temp[id].tipo + '">' +
					'<span style="display: none;"> Tipo de Atividade </span>' +
					'<input id="swal-input3" class="swal2-input" value="' + aaAutogigs_temp[id].tipo_atividade + '" style="display: none;"; disabled>' +
					'<span style="font-weight: bold;"> Visibilidade do Lembrete </span>' +
					'<br><select id="swal-input4" class="swal2-select" style="background-color: white;width: 100%;border: 1px solid #d9d9d9;border-radius: .1875em;box-shadow: inset 0 1px 1px rgba(0,0,0,.06);height: 2.625em;padding: 0 .75em;">' +
						'<option value="LOCAL"' + (aaAutogigs_temp[id].prazo.includes('LOCAL') ? 'selected' : '')  + '> LOCAL </option>' +
						'<option value="RESTRITA"' + (aaAutogigs_temp[id].prazo.includes('RESTRITA') ? 'selected' : '')  + '> RESTRITA </option>' +
						'<option value="GLOBAL"' + (aaAutogigs_temp[id].prazo.includes('GLOBAL') ? 'selected' : '')  + '> GLOBAL </option>' +
					'</select><br>' +
					'<span style="display: none;"> Responsável pelo GIGS </span>' +
					'<input id="swal-input5" class="swal2-input" value="' + aaAutogigs_temp[id].responsavel + '" style="display: none;"; disabled>' +
					'<span style="font-weight: bold;"> Responsável pelo processo </span>' +
					'<input id="swal-input6" class="swal2-input" value="' + aaAutogigs_temp[id].responsavel_processo + '">' +
					'<span style="font-weight: bold;"> Comentário <br><i style="font-size: 0.8em;font-weight: normal;font-style: normal;text-align: left;color: darkcyan;"><br>aceita a expressão <b>[perguntar]</b> que interrompe a ação para o usuário informar o que quer preencher no campo</i></span>' +
					'<textarea id="swal-input7" class="swal2-textarea">' + aaAutogigs_temp[id].observacao + '</textarea>' +
					'<span style="font-weight: bold;"> Salvar </span>' +
					'<br><select id="swal-input8" class="swal2-select" style="background-color: white;width: 100%;border: 1px solid #d9d9d9;border-radius: .1875em;box-shadow: inset 0 1px 1px rgba(0,0,0,.06);height: 2.625em;padding: 0 .75em;">' +
						'<option value="nao"' + (aaAutogigs_temp[id].salvar.toLowerCase().includes('nao') ? 'selected' : '')  + '> Não </option>' +
						'<option value="sim"' + (aaAutogigs_temp[id].salvar.toLowerCase().includes('sim') ? 'selected' : '')  + '> Sim </option>' +
					'</select><br>' +
					'<span style="font-weight: bold;"> Cor do Botão </span>' +
					'<input id="swal-input9" class="swal2-input" type="color" value="' + aaAutogigs_temp[id].cor + '">' +
					'<br><br><label class="container">' +
					'<input type="checkbox" id="swal-input10" ' + (aaAutogigs_temp[id].visibilidade.toLowerCase().includes('sim') ? 'checked' : '') + '><span style="position: relative; padding-right: 15px; top: 2px; margin-left: -10px; font-weight: bold;">Visível na Janela Detalhes?</span>' +
					'<span class="checkmark"></span>' +
					'<input id="swal-input_vinculo" style="display:none;" value="' + aaAutogigs_temp[id].vinculo + '">' +
					'</label>';
					break
				case 'chip':
					var1 = '<span style="font-weight: bold;"> Nome do Botão <br><i style="font-size: 0.8em;font-weight: normal;font-style: normal;text-align: left; color: darkcyan;"><br>aceita a expressão <b>[concluir]</b> que irá finalizar um CHIP, ou uma lista de CHIPS, observando o indicado no campo <u>CHIP</u>. <p style="text-align: center;font-style: italic;">Ex: se usada a expressão [concluir] no nome desta ação, ela irá concluir qualquer CHIP do tipo <u>' + aaAutogigs_temp[id].tipo_atividade + '</u></p></i></span>' +
					'<input id="swal-input1" class="swal2-input" value="' + aaAutogigs_temp[id].nm_botao + '">' +
					'<span style="font-weight: bold;"> Tipo de Ação Automatizada </span>' +
					'<input id="swal-input2" class="swal2-input" value="' + aaAutogigs_temp[id].tipo + '">' +
					'<span style="font-weight: bold;"> CHIP<br><i style="font-size: 0.8em;font-weight: normal;font-style: normal;text-align: left;color: darkcyan;"><br>aceita um ou mais CHIPs desde que separados por vírgula ou a expressão <b>[perguntar]</b> que reliza a pesquisa de chips com base no texto, interrompendo a ação para o usuário selecionar os chips que desejar.</i></i></span>' +
					'<input id="swal-input3" class="swal2-input" value="' + aaAutogigs_temp[id].tipo_atividade + '">' +
					'<span style="display: none;"> Prazo </span>' +
					'<input id="swal-input4" class="swal2-input" value="' + aaAutogigs_temp[id].prazo + '" style="display: none;"; disabled>' +
					'<span style="display: none;"> Responsável pelo GIGS </span>' +
					'<input id="swal-input5" class="swal2-input" value="' + aaAutogigs_temp[id].responsavel + '" style="display: none;"; disabled>' +
					'<span style="display: none;"> Responsável pelo processo </span>' +
					'<input id="swal-input6" class="swal2-input" value="' + aaAutogigs_temp[id].responsavel_processo + '" style="display: none;"; disabled>' +
					'<span style="display: none;"> Observação </span>' +
					'<input id="swal-input7" class="swal2-input" value="' + aaAutogigs_temp[id].observacao + '" style="display: none;"; disabled>' +
					'<span style="font-weight: bold;"> Salvar </span>' +
					'<br><select id="swal-input8" class="swal2-select" style="background-color: white;width: 100%;border: 1px solid #d9d9d9;border-radius: .1875em;box-shadow: inset 0 1px 1px rgba(0,0,0,.06);height: 2.625em;padding: 0 .75em;">' +
						'<option value="nao"' + (aaAutogigs_temp[id].salvar.toLowerCase().includes('nao') ? 'selected' : '')  + '> Não </option>' +
						'<option value="sim"' + (aaAutogigs_temp[id].salvar.toLowerCase().includes('sim') ? 'selected' : '')  + '> Sim </option>' +
					'</select><br>' +
					'<span style="font-weight: bold;"> Cor do Botão </span>' +
					'<input id="swal-input9" class="swal2-input" type="color" value="' + aaAutogigs_temp[id].cor + '">' +
					'<br><br><label class="container">' +
					'<input type="checkbox" id="swal-input10" ' + (aaAutogigs_temp[id].visibilidade.toLowerCase().includes('sim') ? 'checked' : '') + '><span style="position: relative; padding-right: 15px; top: 2px; margin-left: -10px; font-weight: bold;">Visível na Janela Detalhes?</span>' +
					'<span class="checkmark"></span>' +
					'<input id="swal-input_vinculo" style="display:none;" value="' + aaAutogigs_temp[id].vinculo + '">' +
					'</label>';
					break
				case 'lembrete':
					var1 = '<span style="font-weight: bold;"> Nome do Botão <br><i style="font-size: 0.8em;font-weight: normal;font-style: normal;text-align: left; color: darkcyan;"><br>aceita a expressão <b>[concluir]</b> que irá finalizar um LEMBRETE observando a <u>Descrição (Título)</u> e o <u>Conteúdo</u>. <p style="text-align: center;font-style: italic;">Ex: se usada a expressão [concluir] no nome desta ação, ela irá concluir qualquer Lembrete com a descrição (Título) <u>' + aaAutogigs_temp[id].tipo_atividade + '</u> que possua em seu texto a expressão <u>' + aaAutogigs_temp[id].observacao + '</u></p></i></span>' +
					'<input id="swal-input1" class="swal2-input" value="' + aaAutogigs_temp[id].nm_botao + '">' +
					'<span style="font-weight: bold;"> Tipo de Ação Automatizada </span>' +
					'<input id="swal-input2" class="swal2-input" value="' + aaAutogigs_temp[id].tipo + '">' +
					'<span style="font-weight: bold;"> Descrição (Título) </span>' +
					'<input id="swal-input3" class="swal2-input" value="' + aaAutogigs_temp[id].tipo_atividade + '">' +
					'<span style="font-weight: bold;"> Visibilidade do Lembrete </span>' +
					'<br><select id="swal-input4" class="swal2-select" style="background-color: white;width: 100%;border: 1px solid #d9d9d9;border-radius: .1875em;box-shadow: inset 0 1px 1px rgba(0,0,0,.06);height: 2.625em;padding: 0 .75em;">' +
						'<option value="LOCAL"' + (aaAutogigs_temp[id].prazo.includes('LOCAL') ? 'selected' : '')  + '> LOCAL </option>' +
						'<option value="PRIVADO"' + (aaAutogigs_temp[id].prazo.includes('PRIVADO') ? 'selected' : '')  + '> PRIVADO </option>' +
						'<option value="GLOBAL"' + (aaAutogigs_temp[id].prazo.includes('GLOBAL') ? 'selected' : '')  + '> GLOBAL </option>' +
					'</select><br>' +
					'<span style="display: none;"> Responsável pelo GIGS </span>' +
					'<input id="swal-input5" class="swal2-input" value="' + aaAutogigs_temp[id].responsavel + '" style="display: none;"; disabled>' +
					'<span style="display: none;"> Responsável pelo processo </span>' +
					'<input id="swal-input6" class="swal2-input" value="' + aaAutogigs_temp[id].responsavel_processo + '" style="display: none;"; disabled>' +
					'<span style="font-weight: bold;"> Conteúdo do lembrete <br><i style="font-size: 0.8em;font-weight: normal;font-style: normal;text-align: left;color: darkcyan;"><br>aceita a expressão <b>[perguntar]</b> que interrompe a ação para o usuário informar o que quer preencher no campo</i></span>' +
					'<textarea id="swal-input7" class="swal2-textarea">' + aaAutogigs_temp[id].observacao + '</textarea>' +
					'<span style="font-weight: bold;"> Salvar </span>' +
					'<br><select id="swal-input8" class="swal2-select" style="background-color: white;width: 100%;border: 1px solid #d9d9d9;border-radius: .1875em;box-shadow: inset 0 1px 1px rgba(0,0,0,.06);height: 2.625em;padding: 0 .75em;">' +
						'<option value="nao"' + (aaAutogigs_temp[id].salvar.toLowerCase().includes('nao') ? 'selected' : '')  + '> Não </option>' +
						'<option value="sim"' + (aaAutogigs_temp[id].salvar.toLowerCase().includes('sim') ? 'selected' : '')  + '> Sim </option>' +
					'</select><br>' +
					'<span style="font-weight: bold;"> Cor do Botão </span>' +
					'<input id="swal-input9" class="swal2-input" type="color" value="' + aaAutogigs_temp[id].cor + '">' +
					'<br><br><label class="container">' +
					'<input type="checkbox" id="swal-input10" ' + (aaAutogigs_temp[id].visibilidade.toLowerCase().includes('sim') ? 'checked' : '') + '><span style="position: relative; padding-right: 15px; top: 2px; margin-left: -10px; font-weight: bold;">Visível na Janela Detalhes?</span>' +
					'<span class="checkmark"></span>' +
					'<input id="swal-input_vinculo" style="display:none;" value="' + aaAutogigs_temp[id].vinculo + '">' +
					'</label>';
					break
				case 'nenhum':
					var1 = '<span style="font-weight: bold;"> Nome do Botão Agrupador</span>' +
					'<input id="swal-input1" class="swal2-input" value="' + aaAutogigs_temp[id].nm_botao + '">' +
					'<span style="font-weight: bold; display: none;"> Tipo de Ação Automatizada </span>' +
					'<input id="swal-input2" style="display:none;" class="swal2-input" value="' + aaAutogigs_temp[id].tipo + '">' +
					'<input id="swal-input3" style="display:none;" class="swal2-input" value="' + aaAutogigs_temp[id].tipo_atividade + '">' +
					'<input id="swal-input4" style="display:none;" class="swal2-input" value="' + aaAutogigs_temp[id].prazo + '">' +
					'<input id="swal-input5" style="display:none;" class="swal2-input" value="' + aaAutogigs_temp[id].responsavel + '">' +
					'<input id="swal-input6" style="display:none;" class="swal2-input" value="' + aaAutogigs_temp[id].responsavel_processo + '">' +
					'<input id="swal-input7" style="display:none;" class="swal2-input" value="' + aaAutogigs_temp[id].observacao + '">' +
					'<input id="swal-input8" style="display:none;" class="swal2-input" value="' + aaAutogigs_temp[id].salvar + '">' +
					'<span style="font-weight: bold;"> Cor do Botão </span>' +
					'<input id="swal-input9" class="swal2-input" type="color" value="' + aaAutogigs_temp[id].cor + '">' +
					'<br><br><label class="container">' +
					'<input type="checkbox" id="swal-input10" ' + (aaAutogigs_temp[id].visibilidade.toLowerCase().includes('sim') ? 'checked' : '') + '><span style="position: relative; padding-right: 15px; top: 2px; margin-left: -10px; font-weight: bold;">Visível na Janela Detalhes?</span>' +
					'<span class="checkmark"></span>' +
					'<input id="swal-input_vinculo" style="display:none;" value="' + aaAutogigs_temp[id].vinculo + '">' +
					'</label>';
					break
				default:
					var1 = '<span style="font-weight: bold;"> Nome do Botão <br><i style="font-size: 0.8em;font-weight: normal;font-style: normal;text-align: left; color: darkcyan;"><br>aceita a expressão <b>[concluir]</b> que irá finalizar uma ATIVIDADE GIGS observando o <u>Tipo de Atividade</u>, o <u>Responsável pela Atividade</u> e o texto da <u>Observação</u>.<br><br> <span style="background-color: gold;">Agora é possível, numa única Ação Automatizada, configurar o <b>[concluir]</b> com mais de uma <b>ATIVIDADE</b>, <b>RESPONSÁVEL</b> e <b>OBSERVAÇÃO</b>, bastando para isso separar os argumentos com ponto-e-vírgula.. EXPERIMENTE!!</span><br><br><p style="text-align: center;font-style: italic;">Ex: se usada a expressão [concluir] no nome desta ação, ela irá concluir qualquer atividade GIGS do tipo <u>' + aaAutogigs_temp[id].tipo_atividade + '</u> que possua em seu texto a expressão <u>' + aaAutogigs_temp[id].observacao + '</u></p></i></span>' +
					'<input id="swal-input1" class="swal2-input" value="' + aaAutogigs_temp[id].nm_botao + '">' +
					'<span style="font-weight: bold;"> Tipo de Ação Automatizada </span>' +
					'<input id="swal-input2" class="swal2-input" value="' + aaAutogigs_temp[id].tipo + '">' +
					'<span style="font-weight: bold;"> Tipo de Atividade </span>' +
					'<input id="swal-input3" class="swal2-input" value="' + aaAutogigs_temp[id].tipo_atividade + '">' +
					'<span style="font-weight: bold;"> Prazo <br><i style="font-size: 0.8em;font-weight: normal;font-style: normal;text-align: left; color: darkcyan;"><br>aceita a expressão <b>[data_audi]</b> que irá preencher o campo com a data da audiência do processo, ou a expressão <b>[perguntar]</b> que irá abrir uma caixa de diálogo para você preencher com a data desejada.<br><br> <span style="background-color: gold;">quer lançar prazos em dias corridos? Preencha o campo com o número de dias mais a expressão <b>dc</b>. Por exemplo, para lançar 60 dias corridos preencha assim: 60dc</span></i></span>' +
					'<input id="swal-input4" class="swal2-input" value="' + aaAutogigs_temp[id].prazo + '">' +
					'<span style="font-weight: bold;"> Responsável pelo GIGS </span>' +
					'<input id="swal-input5" class="swal2-input" value="' + aaAutogigs_temp[id].responsavel + '">' +
					'<span style="font-weight: bold;"> Responsável pelo processo </span>' +
					'<input id="swal-input6" class="swal2-input" value="' + aaAutogigs_temp[id].responsavel_processo + '">' +
					'<span style="font-weight: bold;"> Observação <br><i style="font-size: 0.8em;font-weight: normal;font-style: normal;text-align: left;color: darkcyan;"><br>aceita a expressão <b>"perguntar"</b> que interrompe a ação para o usuário informar o que quer preencher no campo<br><br>aceita também a expressão <b>"clipboard"</b> que substitui a expressão pelo valor que a extensão copiou pra memória (CTRL+C CTRL+V), mas atenção, só vale para os valores que extensão avisa que copiou pra memória, o seu CTRL+C do windows não tem efeito.</i><br><br><i style="font-size: 0.8em;font-weight: normal;font-style: normal;text-align: left; color: darkcyan;"><br>aceita também as expressões <b>[data_audi]</b> <b>[dados_audi]</b> <b>[link_audi]</b>, que irão ser substituídas no campo observação, respectivamente, pela data da audiência, pelos dados da audiência e pelo link da audiência, se houver.</i><br></span>' +
					'<textarea id="swal-input7" class="swal2-textarea">' + aaAutogigs_temp[id].observacao + '</textarea>' +
					'<span style="font-weight: bold;"> Salvar </span>' +
					'<br><select id="swal-input8" class="swal2-select" style="background-color: white;width: 100%;border: 1px solid #d9d9d9;border-radius: .1875em;box-shadow: inset 0 1px 1px rgba(0,0,0,.06);height: 2.625em;padding: 0 .75em;">' +
						'<option value="nao"' + (aaAutogigs_temp[id].salvar.toLowerCase().includes('nao') ? 'selected' : '')  + '> Não </option>' +
						'<option value="sim"' + (aaAutogigs_temp[id].salvar.toLowerCase().includes('sim') ? 'selected' : '')  + '> Sim </option>' +
					'</select><br>' +
					'<span style="font-weight: bold;"> Cor do Botão </span>' +
					'<input id="swal-input9" class="swal2-input" type="color" value="' + aaAutogigs_temp[id].cor + '">' +
					'<br><br><label class="container">' +
					'<input type="checkbox" id="swal-input10" ' + (aaAutogigs_temp[id].visibilidade.toLowerCase().includes('sim') ? 'checked' : '') + '><span style="position: relative; padding-right: 15px; top: 2px; margin-left: -10px; font-weight: bold;">Visível na Janela Detalhes?</span>' +
					'<span class="checkmark"></span>' +
					'<input id="swal-input_vinculo" style="display:none;" value="' + aaAutogigs_temp[id].vinculo + '">' +
					'</label>';
			}
			return var1;
		}
		const { value: result } = await Swal.fire({
			title: '    ',
			html: texto_html(),
			confirmButtonText: 'Salvar',
			focusConfirm: false,
			preConfirm: () => {
				return [
					document.getElementById('swal-input1').value, //nm
					document.getElementById('swal-input2').value, //tipo
					document.getElementById('swal-input3').value, //tipo_atividade
					document.getElementById('swal-input4').value, //prazo
					document.getElementById('swal-input5').value, //responsavel
					document.getElementById('swal-input6').value, //responsavel_processo
					document.getElementById('swal-input7').value, //observação
					document.getElementById('swal-input8').value, //salvar
					document.getElementById('swal-input9').value, //cor
					document.getElementById('swal-input_vinculo')?.value, //vinculo
					document.getElementById('swal-input10').checked ? "sim" : "não", //visibilidade
				]
			}
		});

		if (result) {
			// aaAutogigs_temp.push(new AcaoAutomatizada_aaAutogigs(temp[0], tipo, '', '', '', '', '', '', result[0], 'Nenhum', 'sim'));
			aaAutogigs_temp[id] = new AcaoAutomatizada_aaAutogigs(result[0], result[1], result[2], result[3], result[4], result[5], result[6], result[7], result[8], result[9], result[10]);
			salvarOpcoes();
			document.getElementById("botoes_autogigs").textContent = '';
			montarBotoesaaAutogigs();
		}
	} else if (tipo == "despacho") {
		const { value: result } = await Swal.fire({
			title: '    ',
			html:
			'<span style="font-weight: bold;"> Nome do Botão </span>' +
			'<input id="swal-inputNomeBotao" class="swal2-input" value="' + aaDespacho_temp[id].nm_botao + '">' +
			'<div style="padding: 20px;border: 2px solid darkcyan;border-radius: 6px;margin-bottom: 10px;background-color: gainsboro;">'+
			'<span style="font-weight: bold;"> Comandos Especiais <br>' +
			'<i style="font-size: 0.8em;font-weight: normal;font-style: normal;text-align: left; color: darkcyan;">' +
			'<br>Clique no botão abaixo para configurações adicionais após a elaboração da minuta<br>' +
			'</u></p></i></span>' +
			'</i></span>' +
			'<button type="button" id="config_comandosEspeciaisDespacho" class="swal2-confirm swal2-styled" style="display: inline-block;background-color: darkcyan;padding: 9px 56px;" aria-label="">Configurar</button>' +
			'<div style="display: grid;grid-template-columns: 10fr 1fr;align-items: center;">' +
			'<textarea id="swal-input_comandosEspeciais" class="swal2-textarea" style="background-color: white;font-size: 0.8em;" disabled>' + aaDespacho_temp[id]?.comandosEspeciais + '</textarea>' +
			'<div id="apagar_config_comandosEspeciaisDespacho" data-tooltip="Apagar"><i class="icone trash-alt t16" style="padding: 0px 5px; background-color: #545454;pointer-events: none;" pos="0"></i></div></div>' +
			'</div>' +

			'<span style="font-weight: bold;"> Tipo </span>' +
			'<input id="swal-input1" class="swal2-input" value="' + aaDespacho_temp[id].tipo + '">' +
			'<span style="font-weight: bold;"> Descrição (Título) </span>' +
			'<input id="swal-input2" class="swal2-input" value="' + aaDespacho_temp[id].descricao + '">' +
			'<span style="font-weight: bold;"> Sigilo </span>' +
			'<br><select id="swal-input3" class="swal2-select" style="background-color: white;width: 100%;border: 1px solid #d9d9d9;border-radius: .1875em;box-shadow: inset 0 1px 1px rgba(0,0,0,.06);height: 2.625em;padding: 0 .75em;">' +
				'<option value="nao"' + (aaDespacho_temp[id].sigilo.toLowerCase().includes('nao') ? 'selected' : '')  + '> Não </option>' +
				'<option value="sim"' + (aaDespacho_temp[id].sigilo.toLowerCase().includes('sim') ? 'selected' : '')  + '> Sim </option>' +
			'</select><br>' +
			'<span style="font-weight: bold;"> Modelo </span>' +
			'<input id="swal-input4" class="swal2-input" value="' + aaDespacho_temp[id].modelo + '">' +
			'<span style="font-weight: bold;"> Juiz </span>' +
			'<input id="swal-input5" class="swal2-input" value="' + aaDespacho_temp[id].juiz + '">' +
			'<span style="font-weight: bold;"> Responsável </span>' +
			'<input id="swal-input6" class="swal2-input" value="' + aaDespacho_temp[id].responsavel + '">' +
			'<span style="font-weight: bold;"> Enviar para assinatura <br><i style="font-size: 0.8em;font-weight: normal;font-style: normal;text-align: left;color: darkcyan;"><br>somente enviará para assinatura os casos que não exigem lançamento de movimento</i></span>' +

			'<br><select id="swal-input7" class="swal2-select" style="background-color: white;width: 100%;border: 1px solid #d9d9d9;border-radius: .1875em;box-shadow: inset 0 1px 1px rgba(0,0,0,.06);height: 2.625em;padding: 0 .75em;">' +
				'<option value="nao"' + (aaDespacho_temp[id].assinar.toLowerCase().includes('nao') ? 'selected' : '')  + '> Não </option>' +
				'<option value="sim"' + (aaDespacho_temp[id].assinar.toLowerCase().includes('sim') ? 'selected' : '')  + '> Sim </option>' +
			'</select><br>' +
			'<span style="font-weight: bold;"> Cor do Botão </span>' +
			'<input id="swal-input8" class="swal2-input" type="color" value="' + aaDespacho_temp[id].cor + '">' +
			'<br><br><label class="container">' +

			'<span style="font-weight: bold;"> Visível na Janela Detalhes? </span>' +
			'<br><select id="swal-input9" class="swal2-select" style="background-color: white;width: 100%;border: 1px solid #d9d9d9;border-radius: .1875em;box-shadow: inset 0 1px 1px rgba(0,0,0,.06);height: 2.625em;padding: 0 .75em;">' +
				'<option value="nao"' + (aaDespacho_temp[id].visibilidade.toLowerCase().includes('nao') ? 'selected' : '')  + '> Não </option>' +
				'<option value="sim"' + (aaDespacho_temp[id].visibilidade.toLowerCase().includes('sim') ? 'selected' : '')  + '> Sim </option>' +
				'<option value="conhecimento"' + (aaDespacho_temp[id].visibilidade.toLowerCase().includes('conhecimento') ? 'selected' : '')  + '> apenas na fase Conhecimento </option>' +
				'<option value="liquidacao"' + (aaDespacho_temp[id].visibilidade.toLowerCase().includes('liquidacao') ? 'selected' : '')  + '> apenas na fase Liquidação </option>' +
				'<option value="execucao"' + (aaDespacho_temp[id].visibilidade.toLowerCase().includes('execucao') ? 'selected' : '')  + '> apenas na fase Execução </option>' +
			'</select><br>' +
			'<input id="swal-input_vinculo" style="display:none;" value="' + aaDespacho_temp[id].vinculo + '">' +
			'</label>',
			confirmButtonText: 'Salvar',
			focusConfirm: false,
			preConfirm: () => {
				return [
					document.getElementById('swal-inputNomeBotao').value, //nm_botao
					document.getElementById('swal-input1').value, //tipo
					document.getElementById('swal-input2').value, //descricao
					document.getElementById('swal-input3').value, //sigilo
					document.getElementById('swal-input4').value, //modelo
					document.getElementById('swal-input5').value, //juiz
					document.getElementById('swal-input6').value, //responsavel
					document.getElementById('swal-input7').value, //assinar
					document.getElementById('swal-input8').value, //cor
					document.getElementById('swal-input9').value, //visibilidade
					document.getElementById('swal-input_vinculo')?.value, //vinculo
					document.getElementById('swal-input_comandosEspeciais').value, //comandos especiais

				]
			}
		});

		if (result) {
			//AcaoAutomatizada_aaDespacho(nm_botao, tipo, descricao, sigilo, modelo, juiz, responsavel, assinar, cor, vinculo, visibilidade='sim', comandosEspeciais)
			console.log(result[11])
			aaDespacho_temp[id] = new AcaoAutomatizada_aaDespacho(result[0], result[1], result[2], result[3], result[4], result[5], result[6], result[7], result[8], result[10], result[9], result[11]);
			salvarOpcoes();
			document.getElementById("botoes_despacho").textContent = '';
			montarBotoesaaDespacho();
		}
	} else if (tipo == "movimento") {
		const { value: result } = await Swal.fire({
			title: '    ',
			html:
			'<span style="font-weight: bold;"> Nome do Botão </span>' +
			'<input id="swal-input1" class="swal2-input" value="' + aaMovimento_temp[id].nm_botao + '">' +
			'<span style="font-weight: bold;"> Nome do Nó de destino <br><i style="font-size: 0.8em;font-weight: normal;font-style: normal;text-align: left;color: darkcyan;"><br>Aceita as expressões:</p><p><b>[?]</b> : onde "?" deverá ser preenchido com o nome de um botão a ser clicado quando o processo chegar no destino</p><p><b>[parar]</b> : que impedirá o fechamento automático da tarefa, deixando essa ação para o usuário, quando o processo chegar ao seu destino</p><p><b>[cancelar conclusão]</b> : comando especial que cancela a conclusão de processos que estejam na tarefa Elaborar Despacho e que não possuam minuta preenchida.</p><p><b>Sobrestamento[#,*,*,*,*,*,*,...]</b> : onde <b>#</b> deverá ser preenchido com o tipo de sobrestamento a ser escolhido e o <b>*</b>, que poderão ser vários, deverão ser preenchidos com a resposta dos campos que irão aparecendo. Por exemplo: a Reunião da execução exige o campo "número de processo", logo o "*" deverá ser preenchido com um número de processo.</p><p style="text-indent:2.8vw;">Também é possível utilizar no lugar do <b>*</b> as expressões abaixo:</p><p><b>[perguntar]</b> : abre uma caixa de pergunta para o usuário digitar o número do processo referência.</p><p><b>[corrigir data]</b> : abre uma caixa de pergunta para o usuário digitar a data final do sobrestamento.</p><p><b>[Atualizar1ano]</b> : Este comando atualizará o prazo do sobrestamento pelo período de 12 meses</p><p><b>[Atualizar2anos]</b> : Este comando atualizará o prazo do sobrestamento pelo período de 24 meses</p><p><b>[AtualizarDataEspecifica ?]</b> : Este comando atualizará o prazo do sobrestamento para a data <b>?</b>,onde <b>?</b> deverá ser preenchido com uma data fixa, no padrão dd/mm/aaaa, ou em meses, no padrão mm </p><p><b>[AtualizarDataPerguntar]</b> : Este comando atualizará o prazo do sobrestamento para a data preenchida no momento do lançamento</p><p><b>[AtualizarDataPeloGIGS]</b> : Este comando atualizará o prazo do sobrestamento para o prazo encontrado nas atividades GIGS. Se houver mais de um prazo, você deverá escolher o prazo desejado em 5 segundos, senão o primeiro prazo encontrado será utilizado.</p><p style="text-align: left;font-style: italic;"><u>Exemplo 1:</u> Sobrestamento[parar]</p><p style="text-align: left;font-style: italic;"><u>Exemplo 2:</u> Sobrestamento[(14971),ADC (362),0000000-00.0000.0.00.0000]</p><p style="text-align: left;font-style: italic;"><u>Exemplo 3:</u>Sobrestamento[Atualizar1ano]</p><p style="text-align: left;font-style: italic;"><u>Exemplo 4:</u> Sobrestamento[AtualizarDataPerguntar]</p><p style="text-align: left;font-style: italic;"><u>Exemplo 5:</u> Sobrestamento[AtualizarDataEspecifica 01/01/2024]</p><p style="text-align: left;font-style: italic;"><u>Exemplo 6:</u> Sobrestamento[(50127),perguntar,corrigir data]</p><p style="text-align: left;font-style: italic;"><u>Exemplo 7:</u> Sobrestamento[AtualizarDataEspecifica 06]</p></i></span>' +
			'<input id="swal-input2" class="swal2-input" value="' + aaMovimento_temp[id].destino + '">' +
			'<span style="font-weight: bold;"> Lançar Chip (nome) </span>' +
			'<input id="swal-input3" class="swal2-input" value="' + aaMovimento_temp[id].chip + '">' +
			'<span style="font-weight: bold;"> Responsável pelo Processo </span>' +
			'<input id="swal-input4" class="swal2-input" value="' + aaMovimento_temp[id].responsavel + '">' +
			'<span style="font-weight: bold;"> Cor do Botão </span>' +
			'<input id="swal-input5" class="swal2-input" type="color" value="' + aaMovimento_temp[id].cor + '">' +
			'<br><br><label class="container">' +
			'<input type="checkbox" id="swal-input7" ' + (aaMovimento_temp[id].visibilidade.toLowerCase().includes('sim') ? 'checked' : '') + '><span style="position: relative; padding-right: 15px; top: 2px; margin-left: -10px; font-weight: bold;">Visível na Janela Detalhes?</span>' +
			'<span class="checkmark"></span>' +
			'<input id="swal-input_vinculo" style="display:none;" value="' + aaMovimento_temp[id].vinculo + '">' +
			'</label>',
			confirmButtonText: 'Salvar',
			focusConfirm: false,
			preConfirm: () => {
				return [
					document.getElementById('swal-input1').value,
					document.getElementById('swal-input2').value,
					document.getElementById('swal-input3').value,
					document.getElementById('swal-input4').value,
					document.getElementById('swal-input5').value,
					document.getElementById('swal-input_vinculo')?.value,
					document.getElementById('swal-input7').checked ? "sim" : "não"
				]
			}
		});

		if (result) {
			aaMovimento_temp[id] = new AcaoAutomatizada_aaMovimento(result[0], result[1], result[2], result[3], result[4], result[5], result[6], result[7]);
			salvarOpcoes();
			document.getElementById("botoes_movimento").textContent = '';
			montarBotoesaaMovimento();
		}
	} else if (tipo == "checklist") {
		const { value: result } = await Swal.fire({
			title: '    ',
			html:
			'<span style="font-weight: bold;"> Nome do Botão <br><i style="font-size: 0.8em;font-weight: normal;font-style: normal;text-align: left; color: darkcyan;"><br>aceita a expressão <b>[concluir]</b> que irá "concluir" o Checklist de acordo com o seu nome, alterando o seu status para NENHUM, retirando o ALERTA e adicionando à descrição a expressão "Desativado em dia-de-hoje".<br>Atenção, que o nome do Checklist fica reduzido depois de lançado, <u>VOCÊ DEVE USAR O NOME REDUZIDO</u>.<br><br><p style="text-align: center;font-style: italic;">Ex: o tipo <b>SERASAJUD/SERASA</b> depois de lançado vira <b>Serasa</b></u></p></i></span>' +
			'<input id="swal-input1" class="swal2-input" value="' + aaChecklist_temp[id].nm_botao + '">' +
			'<span style="font-weight: bold;"> Tipo </span>' +
			'<input id="swal-input2" class="swal2-input" value="' + aaChecklist_temp[id].tipo + '">' +
			'<span style="font-weight: bold;"> Observação <br><i style="font-size: 0.8em;font-weight: normal;font-style: normal;text-align: left; color: darkcyan;">(aceita as expressões "perguntar","corrigir data" e "clipboard")</i></span>' +
			'<textarea id="swal-input3" class="swal2-textarea">' + aaChecklist_temp[id].observacao + '</textarea>' +
			'<span style="font-weight: bold;"> Status </span>' +

			'<br><select id="swal-input4" class="swal2-select" style="background-color: white;width: 100%;border: 1px solid #d9d9d9;border-radius: .1875em;box-shadow: inset 0 1px 1px rgba(0,0,0,.06);height: 2.625em;padding: 0 .75em;">' +
				'<option value="nenhum"' + (aaChecklist_temp[id].estado.includes('nenhum') ? 'selected' : '')  + '> Nenhum </option>' +
				'<option value="negativo"' + (aaChecklist_temp[id].estado.includes('negativo') ? 'selected' : '')  + '> Negativo </option>' +
				'<option value="parcial"' + (aaChecklist_temp[id].estado.includes('parcial') ? 'selected' : '')  + '> Parcial </option>' +
				'<option value="positivo"' + (aaChecklist_temp[id].estado.includes('positivo') ? 'selected' : '')  + '> Positivo </option>' +
				'<option value="perguntar"' + (aaChecklist_temp[id].estado.includes('perguntar') ? 'selected' : '')  + '> Perguntar </option>' +
			'</select><br>' +

			// '<input id="swal-input4" class="swal2-input" value="' + aaChecklist_temp[id].estado + '">' +
			'<span style="font-weight: bold;"> Alerta </span>' +

			'<br><select id="swal-input5" class="swal2-select" style="background-color: white;width: 100%;border: 1px solid #d9d9d9;border-radius: .1875em;box-shadow: inset 0 1px 1px rgba(0,0,0,.06);height: 2.625em;padding: 0 .75em;">' +
				'<option value="nao"' + (aaChecklist_temp[id].alerta.toLowerCase().includes('nao') ? 'selected' : '')  + '> Não </option>' +
				'<option value="sim"' + (aaChecklist_temp[id].alerta.toLowerCase().includes('sim') ? 'selected' : '')  + '> Sim </option>' +
			'</select><br>' +

			// '<input id="swal-input5" class="swal2-input" value="' + aaChecklist_temp[id].alerta + '">' +
			'<span style="font-weight: bold;"> Salvar </span>' +

			'<br><select id="swal-input6" class="swal2-select" style="background-color: white;width: 100%;border: 1px solid #d9d9d9;border-radius: .1875em;box-shadow: inset 0 1px 1px rgba(0,0,0,.06);height: 2.625em;padding: 0 .75em;">' +
				'<option value="nao"' + (aaChecklist_temp[id].salvar.toLowerCase().includes('nao') ? 'selected' : '')  + '> Não </option>' +
				'<option value="sim"' + (aaChecklist_temp[id].salvar.toLowerCase().includes('sim') ? 'selected' : '')  + '> Sim </option>' +
			'</select><br>' +

			// '<input id="swal-input6" class="swal2-input" value="' + aaChecklist_temp[id].salvar + '">' +
			'<span style="font-weight: bold;"> Cor do Botão </span>' +
			'<input id="swal-input7" class="swal2-input" type="color" value="' + aaChecklist_temp[id].cor + '">' +
			'<br><br><label class="container">' +
			'<input type="checkbox" id="swal-input9" ' + (aaChecklist_temp[id].visibilidade.toLowerCase().includes('sim') ? 'checked' : '') + '><span style="position: relative; padding-right: 15px; top: 2px; margin-left: -10px; font-weight: bold;">Visível na Janela Detalhes?</span>' +
			'<span class="checkmark"></span>' +
			'<input id="swal-input_vinculo" style="display:none;" value="' + aaChecklist_temp[id].vinculo + '">' +
			'</label>',
			confirmButtonText: 'Salvar',
			confirmButtonText: 'Salvar',
			focusConfirm: false,
			preConfirm: () => {
				return [
					document.getElementById('swal-input1').value,
					document.getElementById('swal-input2').value,
					document.getElementById('swal-input3').value,
					document.getElementById('swal-input4').value,
					document.getElementById('swal-input5').value,
					document.getElementById('swal-input6').value,
					document.getElementById('swal-input7').value,
					document.getElementById('swal-input_vinculo')?.value,
					document.getElementById('swal-input9').checked ? "sim" : "não"
				]
			}
		});

		if (result) {
			aaChecklist_temp[id] = new AcaoAutomatizada_aaChecklist(result[0], result[1], result[2], result[3], result[4], result[5], result[6], result[7], result[8], result[9]);
			salvarOpcoes();
			document.getElementById("botoes_checklist").textContent = '';
			montarBotoesaaChecklist();
		}
	} else if (tipo == "nomearPerito") {

        // if (!aaNomearPerito_temp[id].tipo_prazo) { aaNomearPerito_temp[id].tipo_prazo = 'dias úteis' }
		const { value: result } = await Swal.fire({
			title: '    ',
			html:
			'<span style="font-weight: bold;"> Nome do Botão </span>' +
			'<input id="swal-input1" class="swal2-input" value="' + aaNomearPerito_temp[id].nm_botao + '">' +
			'<span style="font-weight: bold;"> Tipo </span>' +
			'<input id="swal-input2" class="swal2-input" value="' + aaNomearPerito_temp[id].profissao + '">' +
			'<span style="font-weight: bold;"> Perito </span>' +
			'<input id="swal-input3" class="swal2-input" value="' + aaNomearPerito_temp[id].perito + '">' +
            '<span style="font-weight: bold;"> Prazo </span><br>' +
            '<span style="font-size: .8em;line-height: .8em;">Pode ser em número de dias úteis, uma data fixa ou dias corridos.<br>Para dias corridos, acrescente a expressão dc depois do prazo.<br><i style="color:cadetblue;">Por exemplo: <b>60dc</b> é igual a 60 dias corridos.<br><b>01/01/2027</b> é um prazo em dia fixo.<br><b>30</b> é igual a 30 dias úteis.<br></i></span>' +
			'<input id="swal-input4" class="swal2-input" value="' + aaNomearPerito_temp[id].prazo + '">' +
			'<span style="font-weight: bold;"> Designar </span>' +
			'<br><select id="swal-input5" class="swal2-select" style="background-color: white;width: 100%;border: 1px solid #d9d9d9;border-radius: .1875em;box-shadow: inset 0 1px 1px rgba(0,0,0,.06);height: 2.625em;padding: 0 .75em;">' +
				'<option value="nao"' + (aaNomearPerito_temp[id].designar.toLowerCase().includes('nao') ? 'selected' : '')  + '> Não </option>' +
				'<option value="sim"' + (aaNomearPerito_temp[id].designar.toLowerCase().includes('sim') ? 'selected' : '')  + '> Sim </option>' +
			'</select><br>' +
			'<span style="font-weight: bold;"> Modelo </span>' +
			'<input id="swal-input6" class="swal2-input" value="' + aaNomearPerito_temp[id].modelo + '">' +
			'<span style="font-weight: bold;"> Assinar </span>' +
			'<br><select id="swal-input7" class="swal2-select" style="background-color: white;width: 100%;border: 1px solid #d9d9d9;border-radius: .1875em;box-shadow: inset 0 1px 1px rgba(0,0,0,.06);height: 2.625em;padding: 0 .75em;">' +
				'<option value="nao"' + (aaNomearPerito_temp[id].assinar.toLowerCase().includes('nao') ? 'selected' : '')  + '> Não </option>' +
				'<option value="sim"' + (aaNomearPerito_temp[id].assinar.toLowerCase().includes('sim') ? 'selected' : '')  + '> Sim </option>' +
			'</select><br>' +
			'<span style="font-weight: bold;"> Cor do Botão </span>' +
			'<input id="swal-input8" class="swal2-input" type="color" value="' + aaNomearPerito_temp[id].cor + '">' +
			'<br><br><label class="container">' +
			'<input type="checkbox" id="swal-input9" ' + (aaNomearPerito_temp[id].visibilidade.toLowerCase().includes('sim') ? 'checked' : '') + '><span style="position: relative; padding-right: 15px; top: 2px; margin-left: -10px; font-weight: bold;">Visível na Janela Detalhes?</span>' +
			'</label>',
			confirmButtonText: 'Salvar',
			confirmButtonText: 'Salvar',
			focusConfirm: false,
			preConfirm: () => {
				return [
					document.getElementById('swal-input1').value,
					document.getElementById('swal-input2').value,
					document.getElementById('swal-input3').value,
					document.getElementById('swal-input4').value,
					document.getElementById('swal-input5').value,
					document.getElementById('swal-input6').value,
					document.getElementById('swal-input7').value,
					document.getElementById('swal-input8').value,
					document.getElementById('swal-input9').checked ? "sim" : "não"
				]
			}
		});

		if (result) {

            let tipo_prazo = "";
            let prazo = result[3]
            if (prazo.toLowerCase().includes('dc')) {
                tipo_prazo = "Dias Corridos";
                prazo = prazo.replace('dc','');
            } else if (prazo.search("/") > -1) {
                tipo_prazo = "Data Certa";
            } else {
                tipo_prazo = "Dias Úteis";
            }
            console.log(prazo + ' : ' + tipo_prazo)

			//   new AcaoAutomatizada_aaNomearPerito(nm_botao, profissao, perito, prazo, aa.tipo_prazo, designar, modelo, assinar, cor, vinculo, v);
			aaNomearPerito_temp[id] = new AcaoAutomatizada_aaNomearPerito(result[0], result[1], result[2], prazo, tipo_prazo, result[4], result[5], result[6], result[7], result[8], result[9]);
			salvarOpcoes();
			document.getElementById("botoes_nomearPerito").textContent = '';
			montarBotoesaaNomearPerito();
		}
	} else if (tipo == "variados") {
		function texto_html() {
			let var1 = '';
			// console.log(aaVariados_temp[id].nm_botao)
			switch (aaVariados_temp[id].nm_botao) {
				case 'Atalho F2':
					var1 = '<span style="font-weight: bold;">' + aaVariados_temp[id].nm_botao + '</span><br><br>' +
					'<span style="font-size: .8em;color: darkcyan;">' + aaVariados_temp[id].descricao + '</span><br><br>' +
					'<span style="font-weight: bold;"> Temporizador <br><i style="font-size: 0.8em;font-weight: normal;font-style: normal;text-align: left; color: darkcyan;"><br>tempo (em segundos) para executar a ação</i></span>' +
					'<input id="swal-input1" class="swal2-input" value="' + aaVariados_temp[id].temporizador + '">' +
					'<span style="font-weight: bold;"> Ativar </span>' +
					'<br><select id="swal-input-ativar" class="swal2-select" style="background-color: white;width: 100%;border: 1px solid #d9d9d9;border-radius: .1875em;box-shadow: inset 0 1px 1px rgba(0,0,0,.06);height: 2.625em;padding: 0 .75em;">' +
						'<option value="nao"' + (aaVariados_temp[id].ativar ? '' : 'selected')  + '> Não </option>' +
						'<option value="sim"' + (aaVariados_temp[id].ativar ? 'selected' : '')  + '> Sim </option>' +
					'</select>';
					break
				case 'Atalho F3':
					var1 = '<span style="font-weight: bold;">' + aaVariados_temp[id].nm_botao + '</span><br><br>' +
					'<span style="font-size: .8em;color: darkcyan;">' + aaVariados_temp[id].descricao + '</span><br><br>' +
					'<span style="font-weight: bold;"> Temporizador <br><i style="font-size: 0.8em;font-weight: normal;font-style: normal;text-align: left; color: darkcyan;"><br>tempo (em segundos) para executar a ação</i></span>' +
					'<input id="swal-input1" class="swal2-input" value="' + aaVariados_temp[id].temporizador + '">' +
					'<span style="font-weight: bold;"> Ativar </span>' +
					'<br><select id="swal-input-ativar" class="swal2-select" style="background-color: white;width: 100%;border: 1px solid #d9d9d9;border-radius: .1875em;box-shadow: inset 0 1px 1px rgba(0,0,0,.06);height: 2.625em;padding: 0 .75em;">' +
						'<option value="nao"' + (aaVariados_temp[id].ativar ? '' : 'selected')  + '> Não </option>' +
						'<option value="sim"' + (aaVariados_temp[id].ativar ? 'selected' : '')  + '> Sim </option>' +
					'</select>';
					break
				case 'Atalho F4':
					var1 = '<span style="font-weight: bold;">' + aaVariados_temp[id].nm_botao + '</span><br><br>' +
					'<span style="font-size: .8em;color: darkcyan;">' + aaVariados_temp[id].descricao + '</span><br><br>' +
					'<span style="font-weight: bold;"> Temporizador <br><i style="font-size: 0.8em;font-weight: normal;font-style: normal;text-align: left; color: darkcyan;"><br>tempo (em segundos) para executar a ação</i></span>' +
					'<input id="swal-input1" class="swal2-input" value="' + aaVariados_temp[id].temporizador + '">' +
					'<span style="font-weight: bold;"> Ativar </span>' +
					'<br><select id="swal-input-ativar" class="swal2-select" style="background-color: white;width: 100%;border: 1px solid #d9d9d9;border-radius: .1875em;box-shadow: inset 0 1px 1px rgba(0,0,0,.06);height: 2.625em;padding: 0 .75em;">' +
						'<option value="nao"' + (aaVariados_temp[id].ativar ? '' : 'selected')  + '> Não </option>' +
						'<option value="sim"' + (aaVariados_temp[id].ativar ? 'selected' : '')  + '> Sim </option>' +
					'</select>';
					break
				case 'RETIFICAR AUTUAÇÃO>Cadastrar Advogado':
					var1 = '<span style="font-weight: bold;">' + aaVariados_temp[id].nm_botao + '</span><br><br>' +
					'<span style="font-size: .8em;color: darkcyan;">' + aaVariados_temp[id].descricao + '</span><br><br>' +
					'<span style="font-weight: bold;"> Nome ou CPF do Advogado outorgado <br>' +
					'<i style="font-size: 0.6em;font-weight: normal;font-style: normal;text-align: left; color: darkred;">* se usar o nome tenha certeza que a pesquisa do PJe resultará em apenas um resultado </i></span>' +
					'<input id="swal-input2" class="swal2-input" value="' + aaVariados_temp[id].objeto.advogado + '" style="margin: 2px;">' +
					'<span style="font-weight: bold;"> Nome ou CPF da PARTE outorgante <br>' +
					'<i style="font-size: 0.6em;font-weight: normal;font-style: normal;text-align: left; color: darkred;">* se usar o nome tenha certeza que a pesquisa do PJe resultará em apenas um resultado</i></span>' +
					'<input id="swal-input3" class="swal2-input" value="' + aaVariados_temp[id].objeto.parte + '" style="margin: 2px;">' +
					'<i style="font-size: 0.8em;font-weight: normal;font-style: normal;text-align: left; color: darkcyan;"><br>Temporizador</i></span>' +
					'<input id="swal-input1" class="swal2-input" value="' + aaVariados_temp[id].temporizador + '" style="margin: 2px;">' +
					'<span style="font-weight: bold; display:none;"> Ativar </span>' +
					'<br><select id="swal-input-ativar" class="swal2-select" style=" display:none;background-color: white;width: 100%;border: 1px solid #d9d9d9;border-radius: .1875em;box-shadow: inset 0 1px 1px rgba(0,0,0,.06);height: 2.625em;padding: 0 .75em;">' +
						'<option value="nao"' + (aaVariados_temp[id].ativar ? '' : 'selected')  + '> Não </option>' +
						'<option value="sim"' + (aaVariados_temp[id].ativar ? 'selected' : '')  + '> Sim </option>' +
					'</select>';
					break
				case 'Enviar Email':
					var1 = '<span style="font-weight: bold;">' + aaVariados_temp[id].nm_botao + '</span><br><br>' +
					'<span style="font-size: .8em;color: darkcyan;">' + aaVariados_temp[id].descricao + '</span><br><br>' +
					'<span style="font-weight: bold;"> Configurações do Email <br>' +
					'<i style="font-size: 0.6em;font-weight: normal;font-style: normal;text-align: left; color: darkred;">* é possível utilizar as variáveis do módulo 6</i></span>' +
					'<i style="font-size: 0.8em;font-weight: normal;font-style: normal;text-align: left; color: darkcyan;"><br><br>Destinatário</i></span>' +
					'<input id="swal-input1" class="swal2-input" value="' + aaVariados_temp[id].objeto.destinatario + '" style="margin: 2px;">' +
					'<i style="font-size: 0.8em;font-weight: normal;font-style: normal;text-align: left; color: darkcyan;"><br>Título</i></span>' +
					'<input id="swal-input2" class="swal2-input" value="' + aaVariados_temp[id].objeto.titulo + '" style="margin: 2px;">' +
					'<i style="font-size: 0.8em;font-weight: normal;font-style: normal;text-align: left; color: darkcyan;"><br>corpo</i></span>' +
					'<textarea id="swal-input3" class="swal2-textarea" style="margin: 2px;">' + aaVariados_temp[id].objeto.corpo + '</textarea>' +
					'<i style="font-size: 0.8em;font-weight: normal;font-style: normal;text-align: left; color: darkcyan;"><br>Assinatura</i></span>' +
					'<textarea id="swal-input4" class="swal2-textarea" style="margin: 2px;">' + aaVariados_temp[id].objeto.assinatura + '</textarea>' +
					'<i style="font-size: 0.8em;font-weight: normal;font-style: normal;text-align: left; color: darkcyan;"><br>Temporizador (em segundos)</i> <br>' +
					'<i style="font-size: 0.6em;font-weight: normal;font-style: normal;text-align: left; color: darkred;">* Decorrido este tempo, a extensão irá clicar no botão ENVIAR email.</i></span>' +
					'<input id="swal-input5" class="swal2-input" value="' + aaVariados_temp[id].temporizador + '" style="margin: 2px;">' +
					'<span style="font-weight: bold; display:none;"> Ativar </span>' +
					'<br><select id="swal-input-ativar" class="swal2-select" style=" display:none;background-color: white;width: 100%;border: 1px solid #d9d9d9;border-radius: .1875em;box-shadow: inset 0 1px 1px rgba(0,0,0,.06);height: 2.625em;padding: 0 .75em;">' +
						'<option value="nao"' + (aaVariados_temp[id].ativar ? '' : 'selected')  + '> Não </option>' +
						'<option value="sim"' + (aaVariados_temp[id].ativar ? 'selected' : '')  + '> Sim </option>' +
					'</select>';
					break
				case 'DESPACHO>Rejeitar Prevenção':
					let modeloRP = aaVariados_temp[id]?.objeto?.modelo ? aaVariados_temp[id].objeto.modelo : '';
					var1 = '<span style="font-weight: bold;">' + aaVariados_temp[id].nm_botao + '</span><br><br>' +
					'<span style="font-size: .8em;color: darkcyan;">' + aaVariados_temp[id].descricao + '</span><br><br>' +
					'<span style="font-weight: bold;">Modelo</span>' +
					'<input id="swal-input1" class="swal2-input" value="' + modeloRP + '">' +
					'<span style="font-weight: bold; display:none;"> Ativar </span>' +
					'<br><select id="swal-input-ativar" class="swal2-select" style=" display:none;background-color: white;width: 100%;border: 1px solid #d9d9d9;border-radius: .1875em;box-shadow: inset 0 1px 1px rgba(0,0,0,.06);height: 2.625em;padding: 0 .75em;">' +
						'<option value="nao"' + (aaVariados_temp[id].ativar ? '' : 'selected')  + '> Não </option>' +
						'<option value="sim"' + (aaVariados_temp[id].ativar ? 'selected' : '')  + '> Sim </option>' +
					'</select>';
					break
				case 'DESPACHO>Aceitar Prevenção':
					// let modeloAP = aaVariados_temp[id]?.objeto?.modelo ? aaVariados_temp[id].objeto.modelo : '';
					var1 = '<span style="font-weight: bold;">' + aaVariados_temp[id].nm_botao + '</span><br><br>' +
					'<span style="font-size: .8em;color: darkcyan;">' + aaVariados_temp[id].descricao + '</span><br><br>' +
					// '<span style="font-weight: bold;">Modelo</span>' +
					// '<input id="swal-input1" class="swal2-input" value="' + modeloAP + '">' +
					'<span style="font-weight: bold; display:none;"> Ativar </span>' +
					'<br><select id="swal-input-ativar" class="swal2-select" style=" display:none;background-color: white;width: 100%;border: 1px solid #d9d9d9;border-radius: .1875em;box-shadow: inset 0 1px 1px rgba(0,0,0,.06);height: 2.625em;padding: 0 .75em;">' +
						'<option value="nao"' + (aaVariados_temp[id].ativar ? '' : 'selected')  + '> Não </option>' +
						'<option value="sim"' + (aaVariados_temp[id].ativar ? 'selected' : '')  + '> Sim </option>' +
					'</select>';
					break
				default:
				var1 = '<span style="font-weight: bold;">' + aaVariados_temp[id].nm_botao + '</span><br><br>' +
					'<span style="font-size: .8em;color: darkcyan;">' + aaVariados_temp[id].descricao + '</span><br><br>' +
					'<span style="font-weight: bold;"> Temporizador <br><i style="font-size: 0.8em;font-weight: normal;font-style: normal;text-align: left; color: darkcyan;"><br>tempo (em segundos) para executar a ação</i></span>' +
					'<input id="swal-input1" class="swal2-input" value="' + aaVariados_temp[id].temporizador + '">' +
					'<span style="font-weight: bold; display:none;"> Ativar </span>' +
					'<br><select id="swal-input-ativar" class="swal2-select" style=" display:none;background-color: white;width: 100%;border: 1px solid #d9d9d9;border-radius: .1875em;box-shadow: inset 0 1px 1px rgba(0,0,0,.06);height: 2.625em;padding: 0 .75em;">' +
						'<option value="nao"' + (aaVariados_temp[id].ativar ? '' : 'selected')  + '> Não </option>' +
						'<option value="sim"' + (aaVariados_temp[id].ativar ? 'selected' : '')  + '> Sim </option>' +
					'</select>';
			}
			return var1;
		}

		const { value: result } = await Swal.fire({
			title: '    ',
			html: texto_html(),
			confirmButtonText: 'Salvar',
			focusConfirm: false,
			preConfirm: () => {
				let atv = (document.getElementById('swal-input-ativar').value == 'sim') ? true : false;
				if (aaVariados_temp[id].nm_botao == 'Enviar Email') {
					return [
						document.getElementById('swal-input5').value,
						atv,
						document.getElementById('swal-input1').value,
						document.getElementById('swal-input2').value,
						document.getElementById('swal-input3').value,
						document.getElementById('swal-input4').value
					]
				} else if (aaVariados_temp[id].nm_botao == 'RETIFICAR AUTUAÇÃO>Cadastrar Advogado') {
					return [
						document.getElementById('swal-input1').value, //temporizador
						atv, //ativar
						document.getElementById('swal-input2').value, //adv
						document.getElementById('swal-input3').value //parte
					]

				} else {
					return [
						document.getElementById('swal-input1').value,
						atv
					]
				}

			}
		});

		if (result) {
			if (aaVariados_temp[id].nm_botao == 'Enviar Email') {
				aaVariados_temp[id] = {id: aaVariados_temp[id].id, nm_botao: aaVariados_temp[id].nm_botao , descricao: aaVariados_temp[id].descricao , temporizador: result[0] , ativar: result[1], objeto:{destinatario:result[2],titulo:result[3],corpo:result[4],assinatura:result[5]} };
			} else if (aaVariados_temp[id].nm_botao == 'RETIFICAR AUTUAÇÃO>Cadastrar Advogado') {
				aaVariados_temp[id] = {id: aaVariados_temp[id].id, nm_botao: aaVariados_temp[id].nm_botao , descricao: aaVariados_temp[id].descricao , temporizador: result[0] , ativar: result[1], objeto:{advogado:result[2],parte:result[3]} };
			} else if (aaVariados_temp[id].nm_botao == 'DESPACHO>Rejeitar Prevenção') {
				aaVariados_temp[id] = {id: aaVariados_temp[id].id, nm_botao: aaVariados_temp[id].nm_botao , descricao: aaVariados_temp[id].descricao , temporizador: 0 , ativar: result[1] , objeto:{modelo:result[0]}};
			} else if (aaVariados_temp[id].nm_botao == 'DESPACHO>Aceitar Prevenção') {
				aaVariados_temp[id] = {id: aaVariados_temp[id].id, nm_botao: aaVariados_temp[id].nm_botao , descricao: aaVariados_temp[id].descricao , temporizador: 0 , ativar: result[1] , objeto:{modelo:result[0]}};
			} else {
				aaVariados_temp[id] = {id: aaVariados_temp[id].id, nm_botao: aaVariados_temp[id].nm_botao , descricao: aaVariados_temp[id].descricao , temporizador: result[0] , ativar: result[1]};
			}
			salvarOpcoes();
			document.getElementById("botoes_variados").textContent = '';
			montarBotoesaaVariados();
		}
	}
}

function gerarListaDeVinculos(lista_de_vinculos, tamanho = 10) {
	let html = '';

	for (let i = 0; i < tamanho; i++) {
		const index = i + 1;
		html += '<div style="display: grid;grid-template-columns: 10% 80% 10%;margin: 10px 0;">' +
				'<span style="font-size: 1.5em;margin: 10px 10px 0 0;color: orangered;font-style: italic;opacity: 0.5;">' + index + '</span>' +
				'<button id="escolherAAVinculo' + index + '" aria-description="Escolha vínculo' + index + '" style="cursor: pointer; background-color: white;border: 1px solid #d9d9d9;border-radius: .1875em;box-shadow: inset 0 1px 1px rgba(0,0,0,.06);height: 2.625em;padding: 0 .75em;display: flex;align-items: center;font-size: 1em;">' +
				(lista_de_vinculos[i] ? lista_de_vinculos[i] : 'Nenhum') +
				'</button>' +

				'<button id="apagar-escolherAAVinculo' + index + '"   data-tooltip="Remover vínculo ' + index + '" aria-label="Remover vínculo ' + index + '" style="margin-left: 15px; width: 40px; height: 40px; border: none; background: transparent; cursor: pointer;">' +
				'<i class="icone trash-alt t20" style="background-color: lightgray; vertical-align: middle;"></i></button></div>';
	}

	return html;
}

async function modalEditorVinculo(elemento_pai, tipo, id) {

	let aaComVinculoEspecial;

	if (tipo == "anexar") {
		aaComVinculoEspecial = aaAnexar_temp[id];
	} else if (tipo == "comunicacao") {
		aaComVinculoEspecial = aaComunicacao_temp[id];
	} else if (tipo == "autogigs") {
		aaComVinculoEspecial = aaAutogigs_temp[id];
	} else if (tipo == "despacho") {
		aaComVinculoEspecial = aaDespacho_temp[id];
	} else if (tipo == "movimento") {
		aaComVinculoEspecial = aaMovimento_temp[id];
	} else if (tipo == "checklist") {
		aaComVinculoEspecial = aaChecklist_temp[id];
	} else if (tipo == "nomearPerito") {
		aaComVinculoEspecial = aaNomearPerito_temp[id];
	}

	let lista_de_vinculos = Array.isArray(aaComVinculoEspecial.vinculo) ? aaComVinculoEspecial.vinculo : aaComVinculoEspecial.vinculo.split(','); //transformo a string em array

	const { value: result } = await Swal.fire({
		title: ' EDITAR VÍNCULOS ',
		html:
		// '<style> .swal2-popup { width: 50vw; }	</style>' +
		'<style> .swal2-popup { position: relative;	box-sizing: border-box;	flex-direction: column;	justify-content: center; width: 50%; max-width: 100%; padding: 1.25em; border: none; border-radius: 5px; background: #fff; font-family: inherit;font-size: 1rem; }	</style>' +
		'<p><i style="font-size: 0.8em;font-weight: normal;font-style: normal;text-align: left; color: darkcyan;"><b>ATENÇÃO, a forma de utilizar os vínculos mudou.</b><br>A partir de agora ao final da ação eles serão executados na sequência abaixo, apenas eles, ignorando eventuais vínculos que as outras Ações Automatizadas venham a possuir. Isso facilitará o mapeamento de um tarefa complexa, permitindo tirar o máximo proveito das suas ações automatizadas.<br><br><b><u>Por Exemplo:</u></b> se você quiser juntar um documento, concluir um chip e, em seguida, movimentar o processo para uma tarefa. Basta escolher a Ação Automatiza de juntada no item 1, de conclusão do chip no item 2 e a de movimento no item 3. Eventuais vínculos existentes nas Ações Automatizadas dos itens 1, 2 e 3 serão ignorados, apenas elas serão executadas.</i></p>' +
		gerarListaDeVinculos(lista_de_vinculos, 10),
		confirmButtonText: 'Salvar',
		focusConfirm: false,
		preConfirm: () => {
			return [
				document.getElementById('escolherAAVinculo1').innerText,
				document.getElementById('escolherAAVinculo2').innerText,
				document.getElementById('escolherAAVinculo3').innerText,
				document.getElementById('escolherAAVinculo4').innerText,
				document.getElementById('escolherAAVinculo5').innerText,
				document.getElementById('escolherAAVinculo6').innerText,
				document.getElementById('escolherAAVinculo7').innerText,
				document.getElementById('escolherAAVinculo8').innerText,
				document.getElementById('escolherAAVinculo9').innerText,
				document.getElementById('escolherAAVinculo10').innerText
			]
		}
	});



	if (result) {


		//excluir os Nenhum's
		let temp = [];
		for (const [pos, opcao] of result.entries()) {

			if (opcao != "Nenhum") {
				temp.push(opcao);
			}

		}
		temp.push("Nenhum");


		aaComVinculoEspecial.vinculo = temp;

		if (tipo == "anexar") {
			aaAnexar_temp[id] = aaComVinculoEspecial;
			salvarOpcoes();
			document.getElementById("botoes_anexar_documentos").textContent = '';
			montarBotoesaaAnexar();
		} else if (tipo == "comunicacao") {
			aaComunicacao_temp[id] = aaComVinculoEspecial;
			salvarOpcoes();
			document.getElementById("botoes_comunicacao").textContent = '';
			montarBotoesaaComunicacao();
		} else if (tipo == "autogigs") {
			aaAutogigs_temp[id] = aaComVinculoEspecial;
			salvarOpcoes();
			document.getElementById("botoes_autogigs").textContent = '';
			montarBotoesaaAutogigs();
		} else if (tipo == "despacho") {
			aaDespacho_temp[id] = aaComVinculoEspecial;
			salvarOpcoes();
			document.getElementById("botoes_despacho").textContent = '';
			montarBotoesaaDespacho();
		} else if (tipo == "movimento") {
			aaMovimento_temp[id] = aaComVinculoEspecial;
			salvarOpcoes();
			document.getElementById("botoes_movimento").textContent = '';
			montarBotoesaaMovimento();
		} else if (tipo == "checklist") {
			aaChecklist_temp[id] = aaComVinculoEspecial;
			salvarOpcoes();
			document.getElementById("botoes_checklist").textContent = '';
			montarBotoesaaChecklist();
		} else if (tipo == "nomearPerito") {
			aaNomearPerito_temp[id] = aaComVinculoEspecial;
			salvarOpcoes();
			document.getElementById("botoes_nomearPerito").textContent = '';
			montarBotoesaaNomearPerito();
		}

		// console.log(aaComVinculoEspecial)

	}
}

function modalEditorClonar(elemento_pai, tipo, id) {
	Swal.fire({
		title: 'Clonar o botão \n' + elemento_pai.innerText + '?',
		text: "",
		showCancelButton: true,
		confirmButtonColor: '#3085d6',
		cancelButtonColor: '#d33',
		confirmButtonText: 'Sim, clonar!',
		cancelButtonText: 'Não'
	}).then((result) => {
		if (result.value) {
			if (tipo == "anexar") {
				let aa = new AcaoAutomatizada_aaAnexar();
				aa.nm_botao = aaAnexar_temp[id].nm_botao ? aaAnexar_temp[id].nm_botao : "";
				aa.tipo = aaAnexar_temp[id].tipo ? aaAnexar_temp[id].tipo : "";
				aa.descricao = aaAnexar_temp[id].descricao ? aaAnexar_temp[id].descricao : "";
				aa.sigilo = aaAnexar_temp[id].sigilo ? aaAnexar_temp[id].sigilo : "";
				aa.modelo = aaAnexar_temp[id].modelo ? aaAnexar_temp[id].modelo : "";
				aa.assinar = aaAnexar_temp[id].assinar ? aaAnexar_temp[id].assinar : "";
				aa.cor = aaAnexar_temp[id].cor ? aaAnexar_temp[id].cor : "";
				aa.vinculo = aaAnexar_temp[id].vinculo ? aaAnexar_temp[id].vinculo : "";
				aa.visibilidade = aaAnexar_temp[id].visibilidade ? aaAnexar_temp[id].visibilidade : "sim";
				aaAnexar_temp.push(aa);
				salvarOpcoes();
				document.getElementById("botoes_anexar_documentos").textContent = '';
				montarBotoesaaAnexar();
			} else if (tipo == "comunicacao") {
				let aa = new AcaoAutomatizada_aaComunicacao();
				aa.nm_botao = aaComunicacao_temp[id].nm_botao ? aaComunicacao_temp[id].nm_botao : "";
				aa.tipo = aaComunicacao_temp[id].tipo ? aaComunicacao_temp[id].tipo : "";
				aa.subtipo = aaComunicacao_temp[id].subtipo ? aaComunicacao_temp[id].subtipo : "";
				aa.tipo_prazo = aaComunicacao_temp[id].tipo_prazo ? aaComunicacao_temp[id].tipo_prazo : "";
				aa.prazo = aaComunicacao_temp[id].prazo ? aaComunicacao_temp[id].prazo : "";
				aa.descricao = aaComunicacao_temp[id].descricao ? aaComunicacao_temp[id].descricao : "";
				aa.sigilo = aaComunicacao_temp[id].sigilo ? aaComunicacao_temp[id].sigilo : "";
				aa.modelo = aaComunicacao_temp[id].modelo ? aaComunicacao_temp[id].modelo : "";
				aa.salvar = aaComunicacao_temp[id].salvar ? aaComunicacao_temp[id].salvar : "";
				aa.cor = aaComunicacao_temp[id].cor ? aaComunicacao_temp[id].cor : "";
				aa.vinculo = aaComunicacao_temp[id].vinculo ? aaComunicacao_temp[id].vinculo : "";
				aa.fluxo = aaComunicacao_temp[id].fluxo ? aaComunicacao_temp[id].fluxo : "não";
				aa.visibilidade = aaComunicacao_temp[id].visibilidade ? aaComunicacao_temp[id].visibilidade : "sim";
				aa.comandosEspeciais = aaComunicacao_temp[id].comandosEspeciais ? aaComunicacao_temp[id].comandosEspeciais : "";
				aaComunicacao_temp.push(aa);
				salvarOpcoes();
				document.getElementById("botoes_comunicacao").textContent = '';
				montarBotoesaaComunicacao();
			} else if (tipo == "autogigs") {
				let aa = new AcaoAutomatizada_aaAutogigs();
				aa.nm_botao = aaAutogigs_temp[id].nm_botao ? aaAutogigs_temp[id].nm_botao : "";
				aa.tipo = aaAutogigs_temp[id].tipo ? aaAutogigs_temp[id].tipo : "";
				aa.tipo_atividade = aaAutogigs_temp[id].tipo_atividade ? aaAutogigs_temp[id].tipo_atividade : "";
				aa.prazo = aaAutogigs_temp[id].prazo ? aaAutogigs_temp[id].prazo : "";
				aa.responsavel = aaAutogigs_temp[id].responsavel ? aaAutogigs_temp[id].responsavel : "";
				aa.responsavel_processo = aaAutogigs_temp[id].responsavel_processo ? aaAutogigs_temp[id].responsavel_processo : "";
				aa.observacao = aaAutogigs_temp[id].observacao ? aaAutogigs_temp[id].observacao : "";
				aa.salvar = aaAutogigs_temp[id].salvar ? aaAutogigs_temp[id].salvar : "";
				aa.cor = aaAutogigs_temp[id].cor ? aaAutogigs_temp[id].cor : "";
				aa.vinculo = aaAutogigs_temp[id].vinculo ? aaAutogigs_temp[id].vinculo : "";
				aa.visibilidade = aaAutogigs_temp[id].visibilidade ? aaAutogigs_temp[id].visibilidade : "sim";
				aaAutogigs_temp.push(aa);
				salvarOpcoes();
				document.getElementById("botoes_autogigs").textContent = '';
				montarBotoesaaAutogigs();
			} else if (tipo == "despacho") {
				let aa = new AcaoAutomatizada_aaDespacho();
				aa.nm_botao = aaDespacho_temp[id].nm_botao ? aaDespacho_temp[id].nm_botao : "";
				aa.tipo = aaDespacho_temp[id].tipo ? aaDespacho_temp[id].tipo : "";
				aa.descricao = aaDespacho_temp[id].descricao ? aaDespacho_temp[id].descricao : "";
				aa.sigilo = aaDespacho_temp[id].sigilo ? aaDespacho_temp[id].sigilo : "";
				aa.modelo = aaDespacho_temp[id].modelo ? aaDespacho_temp[id].modelo : "";
				aa.juiz = aaDespacho_temp[id].juiz ? aaDespacho_temp[id].juiz : "";
				aa.responsavel = aaDespacho_temp[id].responsavel ? aaDespacho_temp[id].responsavel : "";
				aa.assinar = aaDespacho_temp[id].assinar ? aaDespacho_temp[id].assinar : "não";
				aa.cor = aaDespacho_temp[id].cor ? aaDespacho_temp[id].cor : "";
				aa.vinculo = aaDespacho_temp[id].vinculo ? aaDespacho_temp[id].vinculo : "";
				aa.visibilidade = aaDespacho_temp[id].visibilidade ? aaDespacho_temp[id].visibilidade : "sim";
				aa.comandosEspeciais = aaDespacho_temp[id].comandosEspeciais ? aaDespacho_temp[id].comandosEspeciais : "[]";
				aaDespacho_temp.push(aa);
				salvarOpcoes();
				document.getElementById("botoes_despacho").textContent = '';
				montarBotoesaaDespacho();
			} else if (tipo == "movimento") {
				let aa = new AcaoAutomatizada_aaMovimento();
				aa.nm_botao = aaMovimento_temp[id].nm_botao ? aaMovimento_temp[id].nm_botao : "";
				aa.destino = aaMovimento_temp[id].destino ? aaMovimento_temp[id].destino : "";
				aa.chip = aaMovimento_temp[id].chip ? aaMovimento_temp[id].chip : "";
				aa.responsavel = aaMovimento_temp[id].responsavel ? aaMovimento_temp[id].responsavel : "";
				aa.cor = aaMovimento_temp[id].cor ? aaMovimento_temp[id].cor : "";
				aa.vinculo = aaMovimento_temp[id].vinculo ? aaMovimento_temp[id].vinculo : "";
				aa.visibilidade = aaMovimento_temp[id].visibilidade ? aaMovimento_temp[id].visibilidade : "sim";
				aaMovimento_temp.push(aa);
				salvarOpcoes();
				document.getElementById("botoes_movimento").textContent = '';
				montarBotoesaaMovimento();
			} else if (tipo == "checklist") {
				let aa = new AcaoAutomatizada_aaChecklist();
				aa.nm_botao = aaChecklist_temp[id].nm_botao ? aaChecklist_temp[id].nm_botao : "";
				aa.tipo = aaChecklist_temp[id].tipo ? aaChecklist_temp[id].tipo : "";
				aa.observacao = aaChecklist_temp[id].observacao ? aaChecklist_temp[id].observacao : "";
				aa.estado = aaChecklist_temp[id].estado ? aaChecklist_temp[id].estado : "";
				aa.alerta = aaChecklist_temp[id].alerta ? aaChecklist_temp[id].alerta : "";
				aa.salvar = aaChecklist_temp[id].salvar ? aaChecklist_temp[id].salvar : "";
				aa.cor = aaChecklist_temp[id].cor ? aaChecklist_temp[id].cor : "";
				aa.vinculo = aaChecklist_temp[id].vinculo ? aaChecklist_temp[id].vinculo : "";
				aa.visibilidade = aaChecklist_temp[id].visibilidade ? aaChecklist_temp[id].visibilidade : "sim";
				aaChecklist_temp.push(aa);
				salvarOpcoes();
				document.getElementById("botoes_checklist").textContent = '';
				montarBotoesaaChecklist();
			} else if (tipo == "nomearPerito") {
				let aa = new AcaoAutomatizada_aaNomearPerito();
				aa.nm_botao = aaNomearPerito_temp[id].nm_botao ? aaNomearPerito_temp[id].nm_botao : "";
				aa.profissao = aaNomearPerito_temp[id].profissao ? aaNomearPerito_temp[id].profissao : "";
				aa.perito = aaNomearPerito_temp[id].perito ? aaNomearPerito_temp[id].perito : "";
				aa.prazo = aaNomearPerito_temp[id].prazo ? aaNomearPerito_temp[id].prazo : "";
				aa.designar = aaNomearPerito_temp[id].designar ? aaNomearPerito_temp[id].designar : "";
				aa.modelo = aaNomearPerito_temp[id].modelo ? aaNomearPerito_temp[id].modelo : "";
				aa.assinar = aaNomearPerito_temp[id].assinar ? aaNomearPerito_temp[id].assinar : "";
				aa.cor = aaNomearPerito_temp[id].cor ? aaNomearPerito_temp[id].cor : "";
				aa.vinculo = aaNomearPerito_temp[id].vinculo ? aaNomearPerito_temp[id].vinculo : "";
				aa.visibilidade = aaNomearPerito_temp[id].visibilidade ? aaNomearPerito_temp[id].visibilidade : "sim";
				aaNomearPerito_temp.push(aa);
				salvarOpcoes();
				document.getElementById("botoes_nomearPerito").textContent = '';
				montarBotoesaaNomearPerito();
			}
		}
	})
}

function modalEditorExcluir(elemento_pai, tipo, id) {
	Swal.fire({
		title: 'Excluir o botão \n' + elemento_pai.innerText + '?',
		text: "",
		showCancelButton: true,
		confirmButtonColor: '#3085d6',
		cancelButtonColor: '#d33',
		confirmButtonText: 'Sim, pode excluir!',
		cancelButtonText: 'Não'
	}).then((result) => {
		if (result.value) {
			if (tipo == "anexar") {
				aaAnexar_temp.splice(id, 1);
				salvarOpcoes();
				document.getElementById("botoes_anexar_documentos").textContent = '';
				montarBotoesaaAnexar();
			} else if (tipo == "comunicacao") {
				aaComunicacao_temp.splice(id, 1);
				salvarOpcoes();
				document.getElementById("botoes_comunicacao").textContent = '';
				montarBotoesaaComunicacao();
			} else if (tipo == "autogigs") {
				aaAutogigs_temp.splice(id, 1);
				salvarOpcoes();
				document.getElementById("botoes_autogigs").textContent = '';
				montarBotoesaaAutogigs();
			} else if (tipo == "despacho") {
				aaDespacho_temp.splice(id, 1);
				salvarOpcoes();
				document.getElementById("botoes_despacho").textContent = '';
				montarBotoesaaDespacho();
			} else if (tipo == "movimento") {
				aaMovimento_temp.splice(id, 1);
				salvarOpcoes();
				document.getElementById("botoes_movimento").textContent = '';
				montarBotoesaaMovimento();
			} else if (tipo == "checklist") {
				aaChecklist_temp.splice(id, 1);
				salvarOpcoes();
				document.getElementById("botoes_checklist").textContent = '';
				montarBotoesaaChecklist();
			} else if (tipo == "nomearPerito") {
				aaNomearPerito_temp.splice(id, 1);
				salvarOpcoes();
				document.getElementById("botoes_nomearPerito").textContent = '';
				montarBotoesaaNomearPerito();
			}
		}
	})
}

function modalEditorExportar(elemento_pai, tipo, id) {
	Swal.fire({
		title: 'Exportar o botão \n' + elemento_pai.innerText + '?',
		text: "",
		showCancelButton: true,
		confirmButtonColor: '#3085d6',
		cancelButtonColor: '#d33',
		confirmButtonText: 'Sim, exportar!',
		cancelButtonText: 'Não'
	}).then((result) => {
		if (result.value) {
			if (tipo == "anexar") {
				 copiarDados(aaAnexar_temp[id]);
			} else if (tipo == "comunicacao") {
				 copiarDados(aaComunicacao_temp[id]);
			} else if (tipo == "autogigs") {
				 copiarDados(aaAutogigs_temp[id]);
			} else if (tipo == "despacho") {
				 copiarDados(aaDespacho_temp[id]);
			} else if (tipo == "movimento") {
				 copiarDados(aaMovimento_temp[id]);
			} else if (tipo == "checklist") {
				 copiarDados(aaChecklist_temp[id]);
			} else if (tipo == "nomearPerito") {
				copiarDados(aaNomearPerito_temp[id]);
			}
		}
	})

	function copiarDados(dados) {
		var textarea = document.createElement("textarea");
		textarea.textContent = JSON.stringify(dados);
		document.body.appendChild(textarea);
		textarea.select();
		document.execCommand("copy");
		document.body.removeChild(textarea);

		Swal.fire({
		  position: 'center',
		  icon: 'success',
		  title: 'Conteúdo copiado com sucesso.',
		  showConfirmButton: false,
		  timer: 1500
		})
	}
}

function aa_eliminarUndefined() {
	//aaAnexar_temp
	let teste1 = [].map.call(aaAnexar_temp,function(item) {
		item.nm_botao = (typeof(item.nm_botao) == "undefined" || item.nm_botao == "undefined") ? "" : item.nm_botao;
		item.tipo = (typeof(item.tipo) == "undefined" || item.tipo == "undefined") ? "" : item.tipo;
		item.descricao = (typeof(item.descricao) == "undefined" || item.descricao == "undefined") ? "" : item.descricao;
		item.sigilo = (typeof(item.sigilo) == "undefined" || item.sigilo == "undefined") ? "não" : item.sigilo;
		item.modelo = (typeof(item.modelo) == "undefined" || item.modelo == "undefined") ? "" : item.modelo;
		item.assinar = (typeof(item.assinar) == "undefined" || item.assinar == "undefined") ? "" : item.assinar;
		item.cor = (typeof(item.cor) == "undefined" || item.cor == "undefined") ? "" : item.cor;
		item.vinculo = (typeof(item.vinculo) == "undefined" || item.vinculo == "undefined") ? "Nenhum" : item.vinculo;
	});

	//aaComunicacao_temp
	let teste2 = [].map.call(aaComunicacao_temp,function(item) {
		item.nm_botao = (typeof(item.nm_botao) == "undefined" || item.nm_botao == "undefined") ? "" : item.nm_botao;
		item.tipo = (typeof(item.tipo) == "undefined" || item.tipo == "undefined") ? "" : item.tipo;
		item.tipo_prazo = (typeof(item.tipo_prazo) == "undefined" || item.tipo_prazo == "undefined") ? "" : item.tipo_prazo;
		item.prazo = (typeof(item.prazo) == "undefined" || item.prazo == "undefined") ? "" : item.prazo;
		item.descricao = (typeof(item.descricao) == "undefined" || item.descricao == "undefined") ? "" : item.descricao;
		item.sigilo = (typeof(item.sigilo) == "undefined" || item.sigilo == "undefined") ? "não" : item.sigilo;
		item.modelo = (typeof(item.modelo) == "undefined" || item.modelo == "undefined") ? "" : item.modelo;
		item.salvar = (typeof(item.salvar) == "undefined" || item.salvar == "undefined") ? "" : item.salvar;
		item.cor = (typeof(item.cor) == "undefined" || item.cor == "undefined") ? "" : item.cor;
		item.vinculo = (typeof(item.vinculo) == "undefined" || item.vinculo == "undefined") ? "Nenhum" : item.vinculo;
	});

	//aaAutogigs_temp
	let teste3 = [].map.call(aaAutogigs_temp,function(item) {
		item.nm_botao = (typeof(item.nm_botao) == "undefined" || item.nm_botao == "undefined") ? "" : item.nm_botao;
		item.tipo = (typeof(item.tipo) == "undefined" || item.tipo == "undefined") ? "" : item.tipo;
		item.tipo_atividade = (typeof(item.tipo_atividade) == "undefined" || item.tipo_atividade == "undefined") ? "" : item.tipo_atividade;
		item.prazo = (typeof(item.prazo) == "undefined" || item.prazo == "undefined") ? "" : item.prazo;
		item.responsavel = (typeof(item.responsavel) == "undefined" || item.responsavel == "undefined") ? "" : item.responsavel;
		item.responsavel_processo = (typeof(item.responsavel_processo) == "undefined" || item.responsavel_processo == "undefined") ? "" : item.responsavel_processo;
		item.observacao = (typeof(item.observacao) == "undefined" || item.observacao == "undefined") ? "" : item.observacao;
		item.salvar = (typeof(item.salvar) == "undefined" || item.salvar == "undefined") ? "" : item.salvar;
		item.cor = (typeof(item.cor) == "undefined" || item.cor == "undefined") ? "" : item.cor;
		item.vinculo = (typeof(item.vinculo) == "undefined" || item.vinculo == "undefined") ? "Nenhum" : item.vinculo;
	});

	//aaDespacho_temp
	let teste4 = [].map.call(aaDespacho_temp,function(item) {
		item.nm_botao = (typeof(item.nm_botao) == "undefined" || item.nm_botao == "undefined") ? "" : item.nm_botao;
		item.tipo = (typeof(item.tipo) == "undefined" || item.tipo == "undefined") ? "" : item.tipo;
		item.descricao = (typeof(item.descricao) == "undefined" || item.descricao == "undefined") ? "" : item.descricao;
		item.sigilo = (typeof(item.sigilo) == "undefined" || item.sigilo == "undefined") ? "não" : item.sigilo;
		item.modelo = (typeof(item.modelo) == "undefined" || item.modelo == "undefined") ? "" : item.modelo;
		item.juiz = (typeof(item.juiz) == "undefined" || item.juiz == "undefined") ? "" : item.juiz;
		item.responsavel = (typeof(item.responsavel) == "undefined" || item.responsavel == "undefined") ? "" : item.responsavel;
		item.cor = (typeof(item.cor) == "undefined" || item.cor == "undefined") ? "" : item.cor;
		item.vinculo = (typeof(item.vinculo) == "undefined" || item.vinculo == "undefined") ? "Nenhum" : item.vinculo;
	});

	//aaMovimento_temp
	let teste5 = [].map.call(aaMovimento_temp,function(item) {
		item.nm_botao = (typeof(item.nm_botao) == "undefined" || item.nm_botao == "undefined") ? "" : item.nm_botao;
		item.destino = (typeof(item.destino) == "undefined" || item.destino == "undefined") ? "" : item.destino;
		item.chip = (typeof(item.chip) == "undefined" || item.chip == "undefined") ? "" : item.chip;
		item.responsavel = (typeof(item.responsavel) == "undefined" || item.responsavel == "undefined") ? "" : item.responsavel;
		item.cor = (typeof(item.cor) == "undefined" || item.cor == "undefined") ? "" : item.cor;
		item.vinculo = (typeof(item.vinculo) == "undefined" || item.vinculo == "undefined") ? "Nenhum" : item.vinculo;
	});

	//aaChecklist_temp
	let teste6 = [].map.call(aaChecklist_temp,function(item) {
		//(nm_botao, tipo, observacao, estado, alerta, salvar, cor, vinculo)
		item.nm_botao = (typeof(item.nm_botao) == "undefined" || item.nm_botao == "undefined") ? "" : item.nm_botao;
		item.tipo = (typeof(item.tipo) == "undefined" || item.tipo == "undefined") ? "" : item.tipo;
		item.observacao = (typeof(item.observacao) == "undefined" || item.observacao == "undefined") ? "" : item.observacao;
		item.estado = (typeof(item.estado) == "undefined" || item.estado == "undefined") ? "" : item.estado;
		item.alerta = (typeof(item.alerta) == "undefined" || item.alerta == "undefined") ? "" : item.alerta;
		item.salvar = (typeof(item.salvar) == "undefined" || item.salvar == "undefined") ? "" : item.salvar;
		item.cor = (typeof(item.cor) == "undefined" || item.cor == "undefined") ? "" : item.cor;
		item.vinculo = (typeof(item.vinculo) == "undefined" || item.vinculo == "undefined") ? "Nenhum" : item.vinculo;
	});
}

function atualizaMonitor(ref) {
	return new Promise(resolver => {
		//altera a imagem do monitor
		if (ref.indexOf("gigsMonitorDetalhes") != -1) {
			let contador = 0;
			for(let monitor of monitores) {

				let nome_img = "../icons/horizontal-screen";
				if (Math.floor(monitor.height) > Math.floor(monitor.width)) {
					nome_img = "../icons/vertical-screen";
				}

				if (ref.indexOf(contador) == -1) {
					document.getElementById('img_gigsMonitorDetalhes' + contador).src = nome_img + ".png";
				} else {
					document.getElementById('img_' + ref).src = nome_img + "_d.png";
				}
				contador = contador + 1;
			}
		} else if (ref.indexOf("gigsMonitorTarefas") != -1) {
			let contador = 0;
			for(let monitor of monitores) {

				let nome_img = "../icons/horizontal-screen";
				if (Math.floor(monitor.height) > Math.floor(monitor.width)) {
					nome_img = "../icons/vertical-screen";
				}

				if (ref.indexOf(contador) == -1) {
					document.getElementById('img_gigsMonitorTarefas' + contador).src = nome_img + ".png";
				} else {
					document.getElementById('img_' + ref).src = nome_img + "_t.png";
				}
				contador = contador + 1;
			}
		} else if (ref.indexOf("gigsMonitorGigs") != -1) {
			let contador = 0;
			for(let monitor of monitores) {

				let nome_img = "../icons/horizontal-screen";
				if (Math.floor(monitor.height) > Math.floor(monitor.width)) {
					nome_img = "../icons/vertical-screen";
				}

				if (ref.indexOf(contador) == -1) {
					document.getElementById('img_gigsMonitorGigs' + contador).src = nome_img + ".png";
				} else {
					document.getElementById('img_' + ref).src = nome_img + "_g.png";
				}
				contador = contador + 1;
			}
		}
		resolver(true);
	});
}

async function criarOpcaoMonitor(divPai, monitor, contador, monitorSelecionado, nomeOpcao) {
	let altura = Math.floor(monitor.height / 8);
	let largura = Math.floor(monitor.width / 8);

	let vertical = false; //200 X 200
	if (altura > largura) {
		vertical = true //200 X 250
		altura = 250;
		largura = 200;
	} else {
		altura = 200;
		largura = 200;
	}

	//----criar radio button
	let radio = document.createElement('input');

	radio.id = nomeOpcao + contador;
	radio.type = 'radio';
	radio.name = nomeOpcao;
	radio.value = contador;
	radio.class = 'radio';
	radio.style = 'width: ' + largura + 'px; height: ' + altura + 'px; cursor: pointer;';
	radio.onclick = async function() {
		await atualizaMonitor(this.id);
		salvarOpcoes();
	}

	//----criar imagem do monitor
	let arquivo = "../icons/horizontal-screen.png";
	if (altura > largura) {
		arquivo = "../icons/vertical-screen.png";
	}

	//----se for o monitor selecionado ele muda a imagem
	if(contador == monitorSelecionado) {
		radio.checked = true;
		if (altura > largura) {
			if (nomeOpcao == "gigsMonitorTarefas") {
				arquivo = "../icons/vertical-screen_t.png";
			} else if (nomeOpcao == "gigsMonitorDetalhes") {
				arquivo = "../icons/vertical-screen_d.png";
			} else if (nomeOpcao == "gigsMonitorGigs") {
				arquivo = "../icons/vertical-screen_g.png";
			}
		} else {
			if (nomeOpcao == "gigsMonitorTarefas") {
				arquivo = "../icons/horizontal-screen_t.png";
			} else if (nomeOpcao == "gigsMonitorDetalhes") {
				arquivo = "../icons/horizontal-screen_d.png";
			} else if (nomeOpcao == "gigsMonitorGigs") {
				arquivo = "../icons/horizontal-screen_g.png";
			}
		}
	}

	var img = new Image(largura, altura);
	img.src = arquivo;
	img.id = "img_" + nomeOpcao + contador;


	//----adicionao o radio button e a imagem no div
	divPai.appendChild(radio);
	divPai.appendChild(img);
}

function tutoriais() {
	Swal.fire({
		title: 'Tutoriais',
		icon: 'question',
		input: 'select',
		inputOptions: {
				0: 'Selecione',
				1: 'Instalação',
				2: 'Apresentação',
				3: 'Módulo 1',
				4: 'Módulo 2',
				5: 'Versão 4.5.9',
				6: 'Versão 4.5.9.1',
				7: 'Versão 4.5.9.3',
				8: 'Versão 4.5.9.5',
				9: 'Versão 4.5.9.6',
				10: 'Versão 4.5.9.7',
				11: 'Versão 4.5.9.8',
				12: 'Versão 4.6.2',
				13: 'Versão 4.6.3',
				14: 'Versão 4.6.3.2 - Baixar documentos (apenas os selecionados)',
				15: 'Versão 4.6.3.2 - Menu Kaizen',
				16: 'Versão 4.6.3.2 - Valor da Execução',
				17: 'Versão 4.6.3.2 - Mudanças nas Ações Automatizadas',
				18: 'Versão 4.6.3.2 - Módulo 9',
				19: 'Versão 4.6.3.2 - AA Recuperação Judicial e Inserir destinatário MTE',
				20: 'Versão 4.6.3.5',
				21: 'Versão 4.6.4.4 - Ação Automatizada múltiplos chips',
				22: 'Versão 4.6.4.4 - Impedimentos e Suspeição na pauta de sessões do segundo grau',
				23: 'Versão 4.6.4.4 - Consultar processos na planilha google docs',
				24: 'Versão 4.6.4.4 - Atribuir responsável do GIGS considerando a fase do processo',
				25: 'Versão 4.6.4.4 - Segundo grau Prazo Relator na Tarefa do Processo',
				26: 'Versão 4.6.4.4 - Ação Automatizada Autogigs - expressão perguntar'
			},
		confirmButtonText: 'Assistir',
		cancelButtonText: 'Voltar',
		showCancelButton: false,
		showConfirmButton: false
	});

	document.querySelector('select[class*="swal2-select"]').addEventListener('change', function(event) {
		switch (event.target.value) {
			case '1':
				apresentarVideo('Instalação', 'https://www.youtube.com/embed/GHZbC45fAuw');
				break
			case '2':
				apresentarVideo('Apresentação', 'https://www.youtube.com/embed/UHebxkguf4A');
				break
			case '3':
				apresentarVideo('Módulo 1', 'https://www.youtube.com/embed/BvqenHqem4s');
				break
			case '4':
				apresentarVideo('Módulo 2', 'https://www.youtube.com/embed/8tLj_3Uy3gU');
				break
			case '5':
				apresentarVideo('Versão 4.5.9', 'https://www.youtube.com/embed/a8VUuVpj5bo'); //
				break
			case '6':
				apresentarVideo('Versão 4.5.9.1', 'https://www.youtube.com/embed/uZFEY4XyWVE');
				break
			case '7':
				apresentarVideo('Versão 4.5.9.3', 'https://www.youtube.com/embed/epgIzD2VdN4');
				break
			case '8':
				apresentarVideo('Versão 4.5.9.5', 'https://www.youtube.com/embed/z9oi4aqUmbg');
				break
			case '9':
				apresentarVideo('Versão 4.5.9.6', 'https://www.youtube.com/embed/7XGdwMQCvps');
				break
			case '10':
				apresentarVideo('Versão 4.5.9.7', 'https://www.youtube.com/embed/gEAY_jJ1YQI');
				break
			case '11':
				apresentarVideo('Versão 4.5.9.8', 'https://www.youtube.com/embed/2OUPBcuQoZg');
				break
			case '12':
				apresentarVideo('Versão 4.6.2', 'https://www.youtube.com/embed/x2IQuKq28c0');
				break
			case '13':
				apresentarVideo('Versão 4.6.3', 'https://www.youtube.com/embed/6tU6UuCdGN4');
				break
			case '14':
				apresentarVideo('Versão 4.6.3.2 - Baixar documentos (apenas os selecionados)', 'https://www.youtube.com/embed/i_PYDJHtPrk');
				break
			case '15':
				apresentarVideo('Versão 4.6.3.2 - Menu Kaizen', 'https://www.youtube.com/embed/xisZQo8F1DI');
				break
			case '16':
				apresentarVideo('Versão 4.6.3.2 - Valor da Execução', 'https://www.youtube.com/embed/IjInZQgF4AI');
				break
			case '17':
				apresentarVideo('Versão 4.6.3.2 - Mudanças nas Ações Automatizadas', 'https://www.youtube.com/embed/1jd6s2-L61E');
				break
			case '18':
				apresentarVideo('Versão 4.6.3.2 - Módulo 9', 'https://www.youtube.com/embed/O9LbeV5g4nc');
				break
			case '19':
				apresentarVideo('Versão 4.6.3.2 - AA Recuperação Judicial e Inserir destinatário MTE', 'https://www.youtube.com/embed/JVPmNc7ESjA');
				break
			case '20':
				apresentarVideo('Versão 4.6.3.5', 'https://www.youtube.com/embed/nIFZu3DWwQw');
				break
			case '21':
				apresentarVideo('Versão 4.6.4.4 - Ação Automatizada múltiplos chips', 'https://www.youtube.com/embed/U0tVL3qSqi4');
				break
			case '22':
				apresentarVideo('Versão 4.6.4.4 - Impedimentos e Suspeição na pauta de sessões do segundo grau', 'https://www.youtube.com/embed/kdrB0ID5kSg');
				break
			case '23':
				apresentarVideo('Versão 4.6.4.4 - Consultar processos na planilha google docs', 'https://www.youtube.com/embed/NYclUVgrPi4');
				break
			case '24':
				apresentarVideo('Versão 4.6.4.4 - Atribuir responsável do GIGS considerando a fase do processo', 'https://www.youtube.com/embed/a2CP4MSojWk');
				break
			case '25':
				apresentarVideo('Versão 4.6.4.4 - Segundo grau Prazo Relator na Tarefa do Processo', 'https://www.youtube.com/embed/h9NJ5-d0pZE');
				break
			case '26':
				apresentarVideo('Versão 4.6.4.4 - Ação Automatizada Autogigs - expressão perguntar', 'https://www.youtube.com/embed/B0vIKUzGjdM');
				break
		}
	});

	function apresentarVideo(titulo, endereco) {
		titulo = titulo.toUpperCase();
		Swal.fire({
			title: '<strong>TUTORIAL ' + titulo + '</strong>',

			html: '<iframe width="560" height="315" src="' + endereco + '?autoplay=1" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>',
			width: 800,
			padding: '3em',
			showCloseButton: true,
			showCancelButton: false,
			showConfirmButton: false,
			focusConfirm: false
		});
	}

}

async function testarMonitores() {
	document.getElementById("overlay").style.display = "flex";

	function sleep(ms) {
		return new Promise(resolve => setTimeout(resolve, ms));
	}

	function registrarMonitor(janela, listaMonitor, posicao) {
		console.log("         _________________________________________________");
		console.log("        |         Monitor Encontrado à " + posicao + "!          ");
		console.log("        |_________________________________________________");
		let params = {};
		params.left = janela.screen.availLeft;
		console.log("        |                    left: " + params.left);
		params.top = janela.screen.availTop;
		console.log("        |                    top: " + params.top);
		params.width = janela.screen.availWidth;
		console.log("        |                    width: " + params.width);
		params.height = janela.screen.availHeight;
		console.log("        |                    height: " + params.height);
		console.log("        |_________________________________________________");
		listaMonitor.push(params);
	}

	let listaMonitor = [];
	//teste de popup habilitado
	let janelaTeste = window.open('','_blank','top=500, left=0, width=100, height=100');
	if (!janelaTeste){
		document.getElementById("overlay").style.opacity = "1";
		let img = document.createElement("img");
		img.src = browser.runtime.getURL("./icons/popup.png");
		document.getElementById("overlay").appendChild(img);
		return;
	} else {
		janelaTeste.close();
	}

	await sleep(20);

	console.log('***MaisPje: Testar monitores para a esquerda');
	let limite_tela = 0; //primeiro monitor o limite da tela à esquerda é zero.
	let limite_tela_anterior = 0;
	let posX_anterior = -100;
	let salto = true;

	while (true) { //movimenta a janela para o limite da tela e tenta um salto...
		let janela = window.open('','_blank','top=500, left=' + limite_tela + ', width=100, height=100'); //abre nova janela dando um salto
		await sleep(20);

		if (salto) {
			console.log("          tamanho_tela: " + janela.screen.availWidth + "   limite_tela: " + limite_tela + "(" + limite_tela_anterior + ")" + "   posX: " + janela.screenX + "(" + posX_anterior + ")");
			//verifica se já chegou no limite de monitoresHandler
			if (posX_anterior == janela.screenX) {
				janela.close();
				break;
			} else {
				//registra o monitor
				registrarMonitor(janela, listaMonitor, "esquerda");

				//tenta dar um salto novo
				posX_anterior = janela.screenX;
				limite_tela_anterior = limite_tela;
				limite_tela = limite_tela - 500; //salto de 500
				janela.close();
				salto = false;
			}
		} else {
			console.log("          (salto) - ajustando ao limite da tela");
			posX_anterior = janela.screenX;
			limite_tela = limite_tela_anterior - janela.screen.availWidth;
			janela.close();
			salto = true;
		}
	}
	console.log("***fim testes para esquerda");

	console.log('***MaisPje: Testar monitores para a direita');
	limite_tela = 500; //primeiro monitor o limite da tela à direita é o tamanho da janela, como eu não tenho janela vou começar em 500 e ajustar o salto para false.
	limite_tela_anterior = 0;
	posX_anterior = 0;
	salto = false;

	while (true) { //movimenta a janela para o limite da tela e tenta um salto...
		let janela = window.open('','_blank','top=500, left=' + limite_tela + ', width=100, height=100'); //abre nova janela dando um salto
		await sleep(20);
		if (salto) {
			console.log("          tamanho_tela: " + janela.screen.availWidth + "   limite_tela: " + limite_tela + "(" + limite_tela_anterior + ")" + "   posX: " + janela.screenX + "(" + posX_anterior + ")");
			//verifica se já chegou no limite de monitoresHandler
			if (posX_anterior == janela.screenX) {
				janela.close();
				break;
			} else {
				//registra o monitor
				console.log("posX_anterior: " + posX_anterior)
				if (posX_anterior > 500) {registrarMonitor(janela, listaMonitor, "direita")} //esse if serve para ignorar o monitor padrão que já foi cadastrado no teste de monitores à esquerda

				//tenta dar um salto novo
				posX_anterior = janela.screenX;
				limite_tela_anterior = limite_tela;
				limite_tela = limite_tela + 500; //salto de 500
				janela.close();
				salto = false;
			}
		} else {
			console.log("          (salto) - ajustando ao limite da tela");
			posX_anterior = janela.screenX;
			limite_tela = limite_tela_anterior + janela.screen.availWidth;
			janela.close();
			salto = true;
		}
	}
	console.log("***fim testes para direita");

	listaMonitor.sort(function(a,b) {
		return a.left - b.left;
	});

	document.getElementById("overlay").style.display = "none";
	console.log("Monitores encontrados: " + listaMonitor.length);
	return Promise.resolve(listaMonitor);
}

function gerarItensPopupNovidades(novidades) {
    const reversedArray = [];

    for (let i = novidades.length - 1; i >= 0; i--) {
      const entry = novidades[i];

      const formattedDate = entry.date

      let changesHtml = '<div><ol>';
	  let correcaoTemp = [];
	  let melhoriaTemp = [];
      entry.changes.forEach((change, index) => {

		if (change.includes('Melhoria:')) {
			change = change.replace('Melhoria:','<span style="opacity: .6;padding: 2px 5px;font-style: normal;background-color: mediumseagreen;color: white;margin-right: 5px;border-radius: 5px;">MELHORIA</span>');
			melhoriaTemp.push(change);
		} else if (change.includes('Correção Técnica:')) {
			change = change.replace('Correção Técnica:','<span style="opacity: .6;padding: 2px 5px;font-style: normal;background-color: goldenrod;color: white;margin-right: 5px;border-radius: 5px;">CORREÇÃO TÉCNICA</span>');
			correcaoTemp.push(change);
		} else {
			change = change.replace('Correção:','<span style="opacity: .6;padding: 2px 5px;font-style: normal;background-color: lightcoral;color: white;margin-right: 5px;border-radius: 5px;">CORREÇÃO</span>');
			correcaoTemp.push(change);
		}




		// changesHtml += `<li>${change}</li>`;
      });

	  correcaoTemp.forEach((change, index) => {
		changesHtml += `<li>${change}</li>`;
	  });
	  changesHtml += '<BR>';
	  melhoriaTemp.forEach((change, index) => {
		changesHtml += `<li>${change}</li>`;
	  });


      changesHtml += '</ol></div>';

      const item = {
        title: `<strong>Versão ${entry.version}</strong>`,
        html: `<div><b>${formattedDate}</b><br><br></div><div style="text-align: left;"><i>${changesHtml}</i></div>`,
        confirmButtonText: 'Versão anterior &rarr;'
      };

      reversedArray.push(item);
    }

    return reversedArray;
  }

async function carregarNovidades() {
	try {
	  const jsonFile = browser.runtime.getURL('./Novidades.json');
	  const response = await fetch(jsonFile);
	  const jsonData = await response.json();
	  return gerarItensPopupNovidades(jsonData);
	} catch (error) {
	  console.error('Erro no arquivo Novidades.JSON:', error);
	}
  }

function montarNovidades(autoplay, novidades) {
	let elemento_base = document.getElementById('config');
	let span = document.createElement("span");
	span.id = "novidades_versao";
	span.className = "titulo";
	span.setAttribute('data-tooltip', 'ver novidades');
	span.innerText = "Novidades ";
	span.onclick = function () {
		Swal.mixin({
			cancelButtonText: 'Fechar',
			showCancelButton: true,
			width: '80%'
		}).queue(novidades).then((result) => {

		})

		let dv = document.createElement("div");
		dv.style = "position: absolute;top: 10px;right: 10px;";
		let ck = document.createElement("input");
		ck.type = "checkbox";
		ck.id = "novidades_MarcarComoLido";
		ck.checked = autoplay;

		ck.onclick = function() {
			///preferencias.videoAtualizacao
			let var1_urls = browser.storage.local.set({'videoAtualizacao': this.checked});
			Promise.all([var1_urls]).then(values => {
				preferencias.videoAtualizacao = false;
				document.querySelector('button[class*="swal2-cancel"]').click();
			});
		}

		dv.appendChild(ck);
		let sp = document.createElement("label");
		sp.innerText = 'Marcar como Lido';
		sp.setAttribute("for", "novidades_MarcarComoLido");
		dv.appendChild(sp);
		document.querySelector('div[class*="swal2-popup"]').appendChild(dv);
	};
	let i = document.createElement("i");
	i.className = "icone novidades-list t16";
	i.style = "background-color: white;";
	span.appendChild(i);
	elemento_base.parentElement.insertBefore(span, elemento_base);

	if (!autoplay) {setTimeout(function() {span.click()}, 500);}
}

async function salvarConfig() {

	let limpar_residuos = browser.storage.local.set({'processo_memoria': '','impressoraVirtual': [],'temp_expediente_especial': '','tempAR': '','tempAuto': '','tempBt': '','tempF2': '','tempF3': '','tempF4': ''});
	Promise.all([limpar_residuos]).then(async values => {

		preferencias =	await browser.storage.local.get(null);
		const { value: result } = await Swal.fire({
			title: '    ',
			html:
			'<span style="font-weight: bold;"> Copie estes dados e salve em um arquivo de texto para recuperá-lo mais tarde. </span><br><br>' +
			'<textarea id="swal-input1" class="swal2-input" style="height: 500px;font-family: inherit;line-height: 1.5em;margin:0;">***' + new Date().toLocaleDateString() + '***' + JSON.stringify(preferencias) + '</textarea>',
			confirmButtonText: 'Copiar',
			focusConfirm: false,
			preConfirm: () => {
				return [
					document.getElementById('swal-input1').value
				]
			}
		});

		if (result) {
			document.getElementById('swal-input1').select();
			document.execCommand("copy");
			Swal.fire({
			  position: 'center',
			  icon: 'success',
			  title: 'Conteúdo copiado com sucesso.',
			  showConfirmButton: false,
			  timer: 1500
			})
		}
	});

}

async function recuperarConfig() {
	const { value: result } = await Swal.fire({
		title: '    ',
		html:
		'<span style="font-weight: bold;"> Cole aqui as configurações para carregá-las.</span><br>' +
		'<textarea id="swal-input1" class="swal2-input" style="height: 500px;font-family: inherit;line-height: 1.5em;margin:0;"></textarea>',
		confirmButtonText: 'Restaurar',
		focusConfirm: false,
		preConfirm: () => {
			let configuracoes = document.getElementById('swal-input1').value;
			configuracoes = configuracoes.substring(configuracoes.search("{"));
			return [configuracoes]
		}
	});

	let printError = function(error) {
		console.log(error.name + " : " + error.message);
		alert(error.name + " : " + error.message);
	}

	try {
		if (result) {
			if (result[0] != "") {
				let padrao = /[\r\n]/gm;
				let resultadoSemQuebrasDeLinha = result[0].replace(padrao,'');
				preferencias = JSON.parse(resultadoSemQuebrasDeLinha);
				await checarVariaveis(true);
			}
		}
	} catch (e) {
		printError(e);
	}
}

function limpatela() {
	document.getElementById("divMonitorDetalhes").textContent = '';
	document.getElementById("divMonitorGigs").textContent = '';
	document.getElementById("divMonitorTarefas").textContent = '';
	document.getElementById("botoes_anexar_documentos").textContent = '';
	document.getElementById("botoes_comunicacao").textContent = '';
	document.getElementById("botoes_autogigs").textContent = '';
	document.getElementById("botoes_despacho").textContent = '';
	document.getElementById("botoes_movimento").textContent = '';
	document.getElementById("botoes_checklist").textContent = '';
	if (document.getElementById("botoes_variados")) {document.getElementById("botoes_variados").textContent = '' }
}

function parEimpar(escolha) {
	let teste = '';
	switch (escolha) {
		case 'par':
			teste = preferencias.modulo8_ignorarZero ? '2,4,6,8' : '0,2,4,6,8';
			break;
		case 'impar':
			teste = '1,3,5,7,9';
			break;
		case 'todos':
			teste = preferencias.modulo8_ignorarZero ? '1,2,3,4,5,6,7,8,9' : '0,1,2,3,4,5,6,7,8,9';
			break;
		case 'nenhum':
			teste = '';
			break;
	}

	let ancora = document.querySelectorAll('div[id="escolherProcessoFinal"] label[class="container"]');
	let map = [].map.call(
		ancora,
		function(elemento) {
			if (teste.includes(elemento.innerText)) {
				elemento.querySelector('input').checked = true;
			} else {
				elemento.querySelector('input').checked = false;
			}
		}
	);
}

function modulo5ParEimpar(escolha) {
	let teste = '';
	switch (escolha) {
		case 'par':
			teste = '0,2,4,6,8';
			break;
		case 'impar':
			teste = '1,3,5,7,9';
			break;
		case 'todos':
			teste = '0,1,2,3,4,5,6,7,8,9';
			break;
		case 'nenhum':
			teste = '';
			break;
	}
	console.log(teste)
	let ancora = document.querySelectorAll('#modulo5 label[class*="modulo5_parEimpar"]');
	let map = [].map.call(
		ancora,
		function(elemento) {
			console.log(elemento.innerText)
			console.log(teste.includes(elemento.innerText.trim()))
			if (teste.includes(elemento.innerText.trim())) {
				elemento.querySelector('input').checked = true;
			} else {
				elemento.querySelector('input').checked = false;
			}
		}
	);
}

async function abrirJanelaConfigURLs(configBase) {
	console.log('abrirJanelaConfigURLs(' + (configBase?'com parametro':'sem parametro') + ')')

	if (configBase) { preferencias.configURLs = configBase }

	console.log(preferencias.configURLs)

	if (!preferencias.configURLs) { return }

	await browser.storage.local.get(['trt','grau_usuario','versaoPje', 'oj_usuario', 'oj_usuarioId'], async function(result){
		preferencias.trt = result.trt;
		preferencias.grau_usuario = result.grau_usuario;
		preferencias.versaoPje = result.versaoPje;
		preferencias.oj_usuario = result.oj_usuario;
		preferencias.oj_usuarioId = result.oj_usuarioId;

		let urlSiscondj = preferencias.configURLs.urlSiscondj;
		let urlSAOExecucao = preferencias.configURLs.urlSAOExecucao;
		urlSAOExecucao = (urlSAOExecucao.includes(preferencias.trt)) ? urlSAOExecucao : 'https://' + preferencias.trt + urlSAOExecucao;
		urlSAOExecucao = (urlSAOExecucao.includes('nenhum')) ? 'nenhum' : urlSAOExecucao;
		urlSAOExecucao = (!preferencias.configURLs.urlSAOExecucao) ? 'nenhum' : urlSAOExecucao;
		let TRTDescricao = (!preferencias.num_trt) ? 'não identificado' : 'Tribunal Regional do Trabalho da ' + preferencias.num_trt + 'a Região';
		preferencias.grau_usuario = (!preferencias.grau_usuario) ? 'não identificado' : preferencias.grau_usuario;
		preferencias.versaoPje = (!preferencias.versaoPje) ? 'não identificado' : preferencias.versaoPje;
		preferencias.oj_usuario = (!preferencias.oj_usuario) ? 'não identificado' : preferencias.oj_usuario;
		preferencias.oj_usuarioId = (!preferencias.oj_usuarioId) ? 'não identificado' : preferencias.oj_usuarioId;

		console.log("   |___ " + preferencias.trt);
		console.log("   |___ " + preferencias.grau_usuario);
		console.log("   |___ " + preferencias.versaoPje);
		console.log("   |___ " + preferencias.configURLs.descricao);
		console.log("   |___ " + preferencias.configURLs.urlSiscondj);
		console.log("   |___ " + preferencias.configURLs.idSiscondj);
		console.log("   |___ " + preferencias.configURLs.urlSAOExecucao);
		console.log("   |___ " + preferencias.configURLs?.linksMenuLateral);
		console.log("   |___ " + preferencias.oj_usuario);
		console.log("   |___ " + preferencias.oj_usuarioId);


		let { value: result2 } = await Swal.fire({
			title: 'CONFIGURAÇÕES BÁSICAS',
			html:
				'<span style="color:lightgray;">As configurações básicas da extensão maisPJe são obtidas automaticamente na tela de login do PJe, sendo desnecessário qualquer registro prévio.<br><br>SEMPRE desconecte do PJe ao instalar/atualizar a extensão.</span><br><br>' +
				`<dl style="display: flex; flex-direction: column; gap: 10px; flex-wrap: wrap; height: 20vh; text-align: left;">` +
				'<div>' +
				'<dt style="font-weight: normal;">URL padrão</dt>' +
				'<dd style="font-weight: normal;color:cadetblue !important;font-style: italic;">' +
				`<a href="https://${preferencias.trt}/${preferencias.grau_usuario}" target="_blank" rel="noopener">` +
					preferencias.trt +
				'</a></dd>' +
				'</div><div>' +
				'<dt>Instância</dt>' +
				'<dd style="font-weight: normal;' + (preferencias.grau_usuario.includes('não identificado') ? 'color:red;' : 'color:cadetblue;') + 'font-style: italic;">' + preferencias.grau_usuario + '</dd>' +
				'</div><div>' +
				'<dt>Versão do PJe</dt>' +
				'<dd style="font-weight: normal;' + (preferencias.versaoPje.includes('não identificado') ? 'color:red;' : 'color:cadetblue;') + 'font-style: italic;">' + preferencias.versaoPje + '</dd>' +
				'</div><div>' +
				'<dt>Unidade do usuário</dt>' +
				'<dd style="font-weight: normal;' + (preferencias.oj_usuario.includes('não identificado') ? 'color:red;' : 'color:cadetblue;') + 'font-style: italic;">' + preferencias.oj_usuario + '</dd>' +
				'</div><div>' +
				'<dt>ID da Unidade</dt>' +
				'<dd style="font-weight: normal;' + (preferencias.oj_usuarioId.includes('não identificado') ? 'color:red;' : 'color:cadetblue;') + 'font-style: italic;">' + preferencias.oj_usuarioId + '</dd>' +
				'</div>' +
				'</dl><br>' +
				'<label for="swal-input3" style="font-weight: bold;"> Descrição: </label>' +
				'<input id="swal-input3" class="swal2-input" value="' + TRTDescricao + '" style="margin: 1vh 0 1vh 0;background-color: #ededed;color: #b3b3b3;" disabled>' +
				'<label for="swal-input1" style="font-weight: bold;"> Siscondj: </label>' +
				'<input id="swal-input1" class="swal2-input" value="' + urlSiscondj + '" style="margin: 1vh 0 1vh 0;">' +
				'<label for="swal-input2" style="font-weight: bold;"> SAO Execução: </label>' +
				'<input id="swal-input2" class="swal2-input" value="' + urlSAOExecucao + '" style="margin: 1vh 0 1vh 0;">' +
				'<span id="maisPje_configuracoes_basicas_restaurar_span" style="float: right;"><button id="maisPje_configuracoes_basicas_restaurar_a" style="all: unset; font-size: .8em;color: cadetblue;font-style: italic;cursor: pointer;">Restaurar</button></span>',

			focusConfirm: false,
			confirmButtonText: 'Salvar',
			width: 800,
			preConfirm: () => {
				return [
					document.getElementById('swal-input1').value,
					document.getElementById('swal-input2').value,
					document.getElementById('swal-input3').value
				]
			}
		});

		if (result2) {

			let var1 = result2[2]
			let var2 = result2[0];
			let var3 = var2.substring(8,var2.search('.trt'));
			let var4 = (result2[1].includes('?maisPje=true')) ? result2[1] : result2[1] + '?maisPje=true' ;
			var4 = (!result2[1] || result2[1].includes('nenhum')) ? '' : var4;

			preferencias.configURLs = {
				descricao: var1,
				urlSiscondj: var2,
				idSiscondj: var3,
				urlSAOExecucao: var4
			};

			let salvando = browser.storage.local.set({'configURLs': preferencias.configURLs});

			Promise.all([salvando]).then(values => {
				let Toast = Swal.mixin({
					toast: true,
					position: 'bottom-end',
					showConfirmButton: false,
					timer: 1500,
					timerProgressBar: true,
					onOpen: (toast) => {
					toast.addEventListener('mouseenter', Swal.stopTimer)
					toast.addEventListener('mouseleave', Swal.resumeTimer)
					}
				})
				Toast.fire({
					icon: 'success',
					title: 'Informações salvas com sucesso!'
				})
			});
		}
	});
}

async function criarCaixaCheckBox(listaDeOpcoes=[],resultadoPadrao=[],titulo='Escolha entre as opções') {
	return new Promise(
		resolver => {
			if (!document.getElementById('maisPje_caixa_de_checkbox')) {

				// DESCRIÇÃO: REGRA DO TOOLTIP
				if (!document.getElementById('maisPje_tooltip_fundo')) {
					tooltip('fundo', true);
				}

				let altura = window.innerHeight || document.documentElement.clientHeight || document.body.clientHeight;

				let elemento1 = document.createElement("div");
				elemento1.id = 'maisPje_caixa_de_checkbox';
				elemento1.style = 'position: fixed; width: 100%; height: ' + altura + 'px; top: 0; inset: 0px; background: #00000080; z-index: 10000; display: flex; align-items: center; justify-content: center; color: rgb(81, 81, 81); font-size: 24px; font-weight: 500; font-family: "NunitoSans Regular", "Arial", sans-serif; text-align: center; flex-direction: column;';
				elemento1.onclick = function (e) {
					if (e.target.id == "maisPje_caixa_de_checkbox") {
						elemento1.remove();
					}
				}; //se clicar fora fecha a janela

				let container = document.createElement("div");
				container.style="height: auto; min-width: 35vw; display: inline-grid; background-color: white;padding: 15px;border-radius: 4px;box-shadow: 0 2px 1px -1px rgba(0,0,0,.2),0 1px 1px 0 rgba(0,0,0,.14),0 1px 3px 0 rgba(0,0,0,.12);";

				let t = document.createElement("span");
				t.style = "color: grey; border-bottom: 1px solid lightgrey;";
				t.innerText = titulo;
				container.appendChild(t);

				let containerCheboxes = document.createElement("div");
				containerCheboxes.style = 'cursor: pointer; margin-top: 10px; padding: 10px; background-color: white; color: rgb(81, 81, 81); min-height: 40px;';

				for (const [pos, opcao] of listaDeOpcoes.entries()) {
					let div = document.createElement("div");
					div.style = "color: rgba(0, 0, 0, 0.87); margin: 1vh 0px 1vh 40%; text-align: left;display: grid;grid-template-columns: 1fr 10fr;align-items: center;min-height: 5vh;font-size: 20px;";
					let opt = document.createElement("input");
					opt.id = 'maisPje_selecao_chk_' + opcao;
					opt.type = 'checkbox';
					opt.checked = resultadoPadrao[pos];
					opt.style = "height: 2.5vh;cursor: pointer;";
					opt.innerText = opcao
					let lbl = document.createElement("label");
					lbl.setAttribute('for',opt.id);
					lbl.style = "cursor: pointer;";
					lbl.innerText = opcao;
					div.appendChild(opt);
					div.appendChild(lbl);
					containerCheboxes.appendChild(div);
				}

				container.appendChild(containerCheboxes);

				let bt_continuar = document.createElement("span");
				bt_continuar.style = "color: white; margin-top: 10px; padding: 10px; border-bottom: 1px solid lightgrey; background-color: #7a9ec8; border-radius: 3px; cursor: pointer;";
				bt_continuar.innerText = "Salvar";
				bt_continuar.onmouseenter = function () {
					bt_continuar.style.backgroundColor  = '#5077a4';
				};
				bt_continuar.onmouseleave = function () {
					bt_continuar.style.backgroundColor  = '#7a9ec8';
				};
				bt_continuar.onclick = function () {
					let listaResultado = document.querySelectorAll('input[id*="maisPje_selecao_chk_"]');
					let temp = []
					for (const [pos, item] of listaResultado.entries()) {
						temp.push(item.checked);
					}
					resolver(temp);
					document.getElementById('maisPje_caixa_de_checkbox').remove();
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

async function ajustarComandosEspeciaisDespacho(nomeBotao, comandosExistentes) {
	return new Promise(resolve => {
		console.log('maisPJe: ajustarComandosEspeciaisDespacho: ' + nomeBotao + '  :  ' + comandosExistentes);
		let opcoes1 = '';
		let opcoes2 = '';
		let opcoes3 = '';
		let opcoes4 = '';
		console.log(nomeBotao)
		if (comandosExistentes) {
			comandosExistentes = comandosExistentes.replace(/(\[)|(\])/g,''); //tira os colchetes
			let ultimoCaractere = comandosExistentes.slice(-1); ////exclui o ultimo ponto e virgula, caso exista
			if (ultimoCaractere == ';') { comandosExistentes = comandosExistentes.slice(0,-1) }
			console.log('   |___' + comandosExistentes)
			let json = comandosExistentes.split(';').map(elements => JSON.parse(`{"${elements?.split(':')?.join('":"')}"}`));
			let objeto = Object.create({});
			let map = [].map.call(
				json,
				function(obj) {
					objeto = { ...objeto, ...obj}
				}
			);
			opcoes1 = (!objeto.intimar) ? 'não' : objeto.intimar;
			opcoes2 = (!objeto.prazo) ? '' : objeto.prazo;
			opcoes3 = (!objeto.enviarpec) ? 'não' : objeto.enviarpec;
			opcoes4 = (!objeto.movimento) ? 'nenhum' : objeto.movimento;
		}

		let resposta = "[";
		resposta += "intimar:" + opcoes1 + ";";
		resposta += "prazo:" + opcoes2 + ";";
		resposta += "enviarpec:" + opcoes3 + ";";
		resposta += "movimento:" + opcoes4 + ";";
		resposta += "]";

		console.log('          |_____ajustado para: ' + resposta);
		return resolve(resposta);
	});
}

async function ajustarComandosEspeciaisComunicacao(nomeBotao, comandosExistentes) {
	return new Promise(resolve => {
		console.log('maisPJe: ajustarComandosEspeciaisComunicacao: ' + nomeBotao + '  :  ' + comandosExistentes);
		let opcoes1 = '';
		let opcoes2 = '';
		let opcoes3 = '';
		let opcoes4 = '';
		let opcoes5 = '';
		let opcoes6 = '';

		if (comandosExistentes) {
			comandosExistentes = comandosExistentes.replace(/(\[)|(\])/g,''); //tira os colchetes
			comandosExistentes = comandosExistentes.replace('trt:','autoridade:'); //tira os colchetes
			let ultimoCaractere = comandosExistentes.slice(-1); ////exclui o ultimo ponto e virgula, caso exista
			if (ultimoCaractere == ';') { comandosExistentes = comandosExistentes.slice(0,-1) }

			let trt = 'trt' + preferencias.num_trt;
			opcoes1 = (comandosExistentes.includes('ativo')) ? 'sim' : 'não'; //ativo
			opcoes2 = (comandosExistentes.includes('passivo')) ? 'sim' : 'não'; //passivo
			opcoes3 = (comandosExistentes.includes('terceiros')) ? 'sim' : 'não'; //terceiros
			opcoes4 = (comandosExistentes.includes('assinar')) ? 'sim' : 'não'; //assinar
			opcoes5 = (comandosExistentes.includes(trt)) ? trt : 'não'; //trt
			opcoes6 = 'não';

			let padraoAutoridade = /autoridade:\D{1,};/;
			if (padraoAutoridade.test(comandosExistentes)) {
				let autoridadeObtida = comandosExistentes.match(padraoAutoridade).join();
				autoridadeObtida = autoridadeObtida.replace('autoridade:','');
				autoridadeObtida = autoridadeObtida.replace(';','');
				opcoes6 = autoridadeObtida;
			}

		}

		let resposta = "[";
		resposta += "ativo:" + opcoes1 + ";";
		resposta += "passivo:" + opcoes2 + ";";
		resposta += "terceiros:" + opcoes3 + ";";
		resposta += "assinar:" + opcoes4 + ";";
		resposta += "trt:" + opcoes5 + ";";
		resposta += "autoridade:" + opcoes6 + ";";
		resposta += "]";

		console.log('          |_____ajustado para: ' + resposta);
		return resolve(resposta);

	});
}

document.addEventListener("DOMContentLoaded", iniciar);

//verificar monitores
document.getElementById("botao").addEventListener('click', async function(event) {
	limpatela();
	preferencias.lista_monitores = await testarMonitores();
	let contador = 0;
	monitores = preferencias.lista_monitores;
	for(let monitor of monitores) {
		criarOpcaoMonitor(divMonitorDetalhes, monitor, contador, preferencias.gigsMonitorDetalhes, 'gigsMonitorDetalhes');
		criarOpcaoMonitor(divMonitorTarefas, monitor, contador, preferencias.gigsMonitorTarefas, 'gigsMonitorTarefas');
		criarOpcaoMonitor(divMonitorGigs, monitor, contador, preferencias.gigsMonitorGigs, 'gigsMonitorGigs');
		contador = contador + 1;
	}
	await salvarOpcoes();
});

document.getElementById("atalhosPlugin").addEventListener('focusout', function(event) {
	salvarOpcoes();
});

document.getElementById("titulo_email").addEventListener('focusout', function(event) {
	preferencias.emailAutomatizado.titulo = document.getElementById("titulo_email").value;
	salvarOpcoes();
});

document.getElementById("corpo_email").addEventListener('focusout', function(event) {
	preferencias.emailAutomatizado.corpo = document.getElementById("corpo_email").value;
	salvarOpcoes();
});

document.getElementById("assinatura_email").addEventListener('focusout', function(event) {
	preferencias.emailAutomatizado.assinatura = document.getElementById("assinatura_email").value;
	salvarOpcoes();
});

document.getElementById("modulo6_ignorar").addEventListener('focusout', function(event) {
	preferencias.emailAutomatizado.ignorar = document.getElementById("modulo6_ignorar").value;
	salvarOpcoes();
});

document.body.addEventListener("click", async function (event) {
	// console.log(event.target.id + ' : ' + event.target.tagName + ' --> ' + event.target.parentElement.id);

	if (event.target.id.includes("escolherAAVinculo") && !event.target.id.includes("apagar")) {
		const possivelAAAtual = event.target.innerText;
		const aa = await criarCaixaDeSelecaoComAAs(preferencias, 'Escolha uma Ação Automatizada para VINCULAR', possivelAAAtual, event.target);
		if (!!aa) { event.target.innerText = aa; }
	}

	if (event.target.id.includes('maisPje_configuracoes_basicas_restaurar_')) {
		let limparStorage = browser.storage.local.remove('configURLs');
		Promise.all([limparStorage]).then(async values => {
			document.querySelector('.swal2-backdrop-show').click();
			await obterUrlsConciliaJT(preferencias.num_trt, true);
		});
	}

	function onButtonClickById(id, callback) {
		const button = event.target.closest(id);
		if (button) {
			console.log(id)
			callback();
		}
	}

	onButtonClickById('a#termoDeUso', () => {
		browser.runtime.sendMessage({tipo: 'permissao'});
		window.close();
	});

	onButtonClickById('button#configURLs', () => abrirJanelaConfigURLs());

	onButtonClickById('#tutoriais', () => tutoriais());

	if (event.target.id.includes("config_comandosEspeciais")) {
		if (event.target.id.includes("apagar_")) {
			event.target.previousSibling.value = '';
			let nmBotao = document.querySelector('input[id="swal-inputNomeBotao"]');
			nmBotao.value = nmBotao.value.replace(/\[(.*?)\]/g,'');
			return;
		}

		let comandosExistentes = event.target.nextSibling.firstElementChild.value;

		if (event.target.id.includes('Despacho')) {
			let opcoes1 = 'não';
			let opcoes2 = '';
			let opcoes3 = 'não';
			let opcoes4 = '';
			let opcoes5 = 'Todos'

			if (comandosExistentes) {
				comandosExistentes = comandosExistentes.replace(/(\[)|(\])/g,''); //tira os colchetes
				let ultimoCaractere = comandosExistentes.slice(-1); ////exclui o ultimo ponto e virgula, caso exista
				if (ultimoCaractere == ';') { comandosExistentes = comandosExistentes.slice(0,-1) }
				let json = comandosExistentes.split(';').map(elements => JSON.parse(`{"${elements?.split(':')?.join('":"')}"}`));
				let objeto = Object.create({});
				let map = [].map.call(
					json,
					function(obj) {
						objeto = { ...objeto, ...obj}
					}
				);
				console.log(objeto)
				opcoes1 = objeto.intimar;
				opcoes2 = objeto.prazo;
				opcoes3 = objeto.enviarpec;
				opcoes4 = objeto.movimento;
				opcoes5 = (!objeto.destinatario) ? 'Todos' : objeto.destinatario;
			}

			opcoes1 = await criarCaixaSelecao(['sim','não'],'Intimar?|Ativa a intimação das partes acerca do Despacho/Decisão/Sentença',opcoes1,'Continuar');
			if (opcoes1 == 'sim') {
				opcoes5 = await criarCaixaSelecao(['Todos','Polo Ativo','Polo Passivo','Polo Ativo + Polo Passivo','Perito'],'Destinatário|Escolha o(s) destinatário(s) da intimação:',opcoes5,'Continuar');
				opcoes2 = await criarCaixaDePergunta('text','Prazo|Digite o prazo da intimação',opcoes2,'digite o número de dias','Continuar');
			} else {
				opcoes2 = '';
			}
			opcoes3 = await criarCaixaSelecao(['sim','não'],'Enviar para o PEC?|Ativa o encaminhamento do processo para a tarefa PEC após a assinatura do juiz',opcoes3,'Continuar');
			opcoes4 = await criarCaixaDePergunta('text', 'Movimentos|Lança automaticamente os códigos de movimento.\nNos casos de múltipla escolha separe os códigos por "-":\nExemplo: (12040)-(12037)-(11382)\nNos casos de escolha única que desencadeia novas opções, separe os códigos da sequência com vírgulas:\nExemplo: (196),(7639)',opcoes4,'Exemplo: (196),(7598)','Salvar');
			opcoes4 = (!opcoes4) ? 'nenhum' : opcoes4;

			let resposta = "[";
			resposta += "intimar:" + opcoes1 + ";";
			resposta += "prazo:" + opcoes2 + ";";
			resposta += "destinatario:" + opcoes5 + ";";
			resposta += "enviarpec:" + opcoes3 + ";";
			resposta += "movimento:" + opcoes4 + ";";
			resposta += "]";

			document.querySelector('#swal-input_comandosEspeciais').value = resposta;
			return;

		} else if (event.target.id.includes('Comunicacao')) {

			let opcoes1 = 'não';
			let opcoes2 = 'não';
			let opcoes3 = 'não';
			let opcoes4 = 'não';
			let opcoes5 = 'não';
			let opcoes6 = '';

			if (comandosExistentes) {
				comandosExistentes = comandosExistentes.replace(/(\[)|(\])/g,''); //tira os colchetes
				let ultimoCaractere = comandosExistentes.slice(-1); ////exclui o ultimo ponto e virgula, caso exista
				if (ultimoCaractere == ';') { comandosExistentes = comandosExistentes.slice(0,-1) }
				let json = comandosExistentes.split(';').map(elements => JSON.parse(`{"${elements?.split(':')?.join('":"')}"}`));
				let objeto = Object.create({});
				let map = [].map.call(
					json,
					function(obj) {
						objeto = { ...objeto, ...obj}
					}
				);

				opcoes1 = objeto.ativo;
				opcoes2 = objeto.passivo;
				opcoes3 = objeto.terceiros;
				opcoes4 = objeto.assinar;
				opcoes5 = objeto.trt;
				opcoes6 = objeto.autoridade;
			}

			// console.log(opcoes1 + ':' + opcoes2 + ':' + opcoes3 + ':' + opcoes4 + ':' + opcoes5 + ':' + opcoes6)

			opcoes1 = await criarCaixaSelecao(['sim','não'],'Intimar Polo Ativo?|Seleciona o polo ativo como destinatário após a elaboração do ato agrupado',opcoes1,'Continuar');
			opcoes2 = await criarCaixaSelecao(['sim','não'],'Intimar Polo Passivo?|Seleciona o polo passivo como destinatário após a elaboração do ato agrupado',opcoes2,'Continuar');
			opcoes3 = await criarCaixaSelecao(['sim','não'],'Intimar Terceiros?|Seleciona o polo terceiros como destinatário após a elaboração do ato agrupado',opcoes3,'Continuar');
			opcoes4 = await criarCaixaSelecao(['sim','não'],'Assinar Automaticamente?|Assina automaticamente o expedinte',opcoes4,'Continuar');
			opcoes5 = await criarCaixaSelecao(['sim','não'],'Intimar TRT?|Seleciona o seu Regional como destinatário após a elaboração do ato agrupado',opcoes5,'Continuar');
			let existeopcoes6 = (opcoes6 != 'não') ? 'sim' : 'não';
			existeopcoes6 = await criarCaixaSelecao(['sim','não'],'Intimar Autoridade?|Seleciona a Autoridade como destinatário após a elaboração do ato agrupado\nDigite o nome da Autoridade que será pesquisada',existeopcoes6,'Continuar');
			if (existeopcoes6 == 'sim') {
				opcoes6 = await criarCaixaDePergunta('text', 'Nome da Autoridade',opcoes6,'Exemplo: Vara do Trabalho de Palhoça','Salvar');
			} else {
				opcoes6 = 'não';
			}

			let resposta = "[";
			resposta += "ativo:" + opcoes1 + ";";
			resposta += "passivo:" + opcoes2 + ";";
			resposta += "terceiros:" + opcoes3 + ";";
			resposta += "assinar:" + opcoes4 + ";";
			resposta += "trt:" + opcoes5 + ";";
			resposta += "autoridade:" + opcoes6 + ";";
			resposta += "]";

			document.querySelector('#swal-input_comandosEspeciais').value = resposta;
			return;
		}

	}

	if (event.target.id.includes("atalhos_emoji")) {

		Swal.fire({
			title: 'EMOJIS - clique para copiar',
			html:
				'<div id="copiarEmojis">' +
				'Pessoas' +
				'<br>' +
				'<i>😀</i> <i>😃</i> <i>😄</i> <i>😁</i> <i>😆</i> <i>😅</i> <i>🤣</i> <i>😂</i> <i>🥹</i> <i>🙂</i> <i>🙃</i> <i>😉</i> <i>😊</i> <i>😇</i> <i>🥰</i> <i>😍</i> <i>🤩</i> <i>😘</i> <i>😗</i> <i>☺️</i> <i>😚</i> <i>😙</i> <i>🥲</i> <i>😋</i> <i>😛</i> <i>😜</i> <i>🤪</i> <i>😝</i> <i>🤑</i> <i>🤗</i> <i>🫢</i> <i>🤭</i> <i>🤫</i> <i>🤔</i> <i>🙂‍↔️</i> <i>🙂‍↕️</i> <i>🫡</i> <i>🤐</i> <i>🤨</i> <i>😐️</i> <i>😑</i> <i>😶</i> <i>😏</i> <i>😒</i> <i>🙄</i> <i>😬</i> <i>🤥</i> <i>😌</i> <i>😔</i> <i>😪</i> <i>😮‍💨</i> <i>🤤</i> <i>😴</i> <i>😷</i> <i>🤒</i> <i>🤕</i> <i>🤢</i> <i>🤮</i> <i>🤧</i> <i>🫠</i> <i>🥵</i> <i>🥶</i> <i>😶‍🌫️</i> <i>🫥</i> <i>🥴</i> <i>😵‍💫</i> <i>😵</i> <i>🤯</i> <i>🤠</i> <i>🥳</i> <i>🥸</i> <i>😎</i> <i>🤓</i> <i>🧐</i> <i>🫤</i> <i>😕</i> <i>😟</i> <i>🙁</i> <i>☹️</i> <i>😮</i> <i>😯</i> <i>😲</i> <i>😳</i> <i>🫣</i> <i>🥺</i> <i>😦</i> <i>😧</i> <i>😨</i> <i>😰</i> <i>😥</i> <i>😢</i> <i>😭</i> <i>😱</i> <i>😖</i> <i>😣</i> <i>😞</i> <i>😓</i> <i>😩</i> <i>😫</i> <i>🥱</i> <i>😤</i> <i>😡</i> <i>😠</i> <i>🤬</i> <i>😈</i> <i>👿</i> <i>💀</i> <i>☠️</i> <i>💩</i> <i>🤡</i> <i>👹</i> <i>👺</i> <i>👻</i> <i>👽️</i> <i>👾</i> <i>🤖</i> <i>😺</i> <i>😸</i> <i>😹</i> <i>😻</i> <i>😼</i> <i>😽</i> <i>🙀</i> <i>😿</i> <i>😾</i> <i>🙈</i> <i>🙉</i> <i>🙊</i> <i>👋</i> <i>🤚</i> <i>🖐️</i> <i>✋</i> <i>🖖</i> <i>👌</i> <i>🤌</i> <i>🤏</i> <i>✌️</i> <i>🤞</i> <i>🫰</i> <i>🤟</i> <i>🤘</i> <i>🤙</i> <i>👈️</i> <i>👉️</i> <i>👆️</i> <i>🖕</i> <i>👇️</i> <i>☝️</i> <i>🫵</i> <i>👍️</i> <i>👎️</i> <i>✊</i> <i>👊</i> <i>🤛</i> <i>🤜</i> <i>👏</i> <i>🙌</i> <i>👐</i> <i>🫶</i> <i>🤲</i> <i>🫳</i> <i>🫴</i> <i>🫱</i> <i>🫲</i> <i>🤝</i> <i>🙏</i> <i>✍️</i> <i>💅</i> <i>🤳</i> <i>💪</i> <i>🦾</i> <i>🦿</i> <i>🦵</i> <i>🦶</i> <i>👂️</i> <i>🦻</i> <i>👃</i> <i>🧠</i> <i>🫀</i> <i>🫁</i> <i>🦷</i> <i>🦴</i> <i>👀</i> <i>👁️</i> <i>👅</i> <i>👄</i> <i>🫦</i> <i>💋</i> <i>👶</i> <i>🧒</i> <i>👦</i> <i>👧</i> <i>🧑</i> <i>👨</i> <i>👩</i> <i>🧔</i> <i>🧔‍</i> <i>🧔‍</i> <i>🧑‍🦰</i> <i>👨‍🦰</i> <i>👩‍🦰</i> <i>🧑‍🦱</i> <i>👨‍🦱</i> <i>👩‍🦱</i> <i>🧑‍🦳</i> <i>👨‍🦳</i> <i>👩‍🦳</i> <i>🧑‍🦲</i> <i>👨‍🦲</i> <i>👩‍🦲</i> <i>👱</i> <i>👱‍</i> <i>👱‍</i> <i>🧓</i> <i>👴</i> <i>👵</i> <i>🙍</i> <i>🙍‍</i> <i>🙍‍</i> <i>🙎</i> <i>🙎‍</i> <i>🙎‍</i> <i>🙅</i> <i>🙅‍</i> <i>🙅‍</i> <i>🙆</i> <i>🙆‍</i> <i>🙆‍</i> <i>💁</i> <i>💁‍</i> <i>💁‍</i> <i>🙋</i> <i>🙋‍</i> <i>🙋‍</i> <i>🧏</i> <i>🧏‍</i> <i>🧏‍</i> <i>🙇</i> <i>🙇‍</i> <i>🙇‍</i> <i>🤦</i> <i>🤦‍</i> <i>🤦‍</i> <i>🤷</i> <i>🤷‍</i> <i>🤷‍</i> <i>🧑‍⚕️</i> <i>👨‍⚕️</i> <i>👩‍⚕️</i> <i>🧑‍🎓</i> <i>👨‍🎓</i> <i>👩‍🎓</i> <i>🧑‍🏫</i> <i>👨‍🏫</i> <i>👩‍🏫</i> <i>🧑‍⚖️</i> <i>👨‍⚖️</i> <i>👩‍⚖️</i> <i>🧑‍🌾</i> <i>👨‍🌾</i> <i>👩‍🌾</i> <i>🧑‍🍳</i> <i>👨‍🍳</i> <i>👩‍🍳</i> <i>🧑‍🔧</i> <i>👨‍🔧</i> <i>👩‍🔧</i> <i>🧑‍🏭</i> <i>👨‍🏭</i> <i>👩‍🏭</i> <i>🧑‍💼</i> <i>👨‍💼</i> <i>👩‍💼</i> <i>🧑‍🔬</i> <i>👨‍🔬</i> <i>👩‍🔬</i> <i>🧑‍💻</i> <i>👨‍💻</i> <i>👩‍💻</i> <i>🧑‍🎤</i> <i>👨‍🎤</i> <i>👩‍🎤</i> <i>🧑‍🎨</i> <i>👨‍🎨</i> <i>👩‍🎨</i> <i>🧑‍✈️</i> <i>👨‍✈️</i> <i>👩‍✈️</i> <i>🧑‍🚀</i> <i>👨‍🚀</i> <i>👩‍🚀</i> <i>🧑‍🚒</i> <i>👨‍🚒</i> <i>👩‍🚒</i> <i>👮</i> <i>👮‍</i> <i>👮‍</i> <i>🕵️</i> <i>💂</i> <i>💂‍</i> <i>💂‍</i> <i>🥷</i> <i>👷</i> <i>👷‍</i> <i>👷‍</i> <i>🫅</i> <i>🤴</i> <i>👸</i> <i>👳</i> <i>👳‍</i> <i>👳‍</i> <i>👲</i> <i>🧕</i> <i>🤵</i> <i>🤵‍</i> <i>🤵‍</i> <i>👰</i> <i>👰‍</i> <i>👰‍</i> <i>🫄</i> <i>🫃</i> <i>🤰</i> <i>🤱</i> <i>👩‍🍼</i> <i>👨‍🍼</i> <i>🧑‍🍼</i> <i>👼</i> <i>🎅</i> <i>🤶</i> <i>🧑‍🎄</i> <i>🦸</i> <i>🦸‍</i> <i>🦸‍</i> <i>🦹</i> <i>🦹‍</i> <i>🦹‍</i> <i>🧙</i> <i>🧙‍</i> <i>🧙‍</i> <i>🧚</i> <i>🧚‍</i> <i>🧚‍</i> <i>🧛</i> <i>🧛‍</i> <i>🧛‍</i> <i>🧜</i> <i>🧜‍</i> <i>🧜‍</i> <i>🧝</i> <i>🧝‍</i> <i>🧝‍</i> <i>🧞</i> <i>🧞‍</i> <i>🧞‍</i> <i>🧟</i> <i>🧟‍</i> <i>🧟‍</i> <i>🧌</i> <i>💆</i> <i>💆‍</i> <i>💆‍</i> <i>💇</i> <i>💇‍</i> <i>💇‍</i> <i>🚶</i> <i>🚶‍</i> <i>🚶‍</i> <i>🧍</i> <i>🧍‍</i> <i>🧍‍</i> <i>🧎</i> <i>🧎‍</i> <i>🧎‍</i> <i>🧑‍🦯</i> <i>👨‍🦯</i> <i>👩‍🦯</i> <i>🧑‍🦼</i> <i>👨‍🦼</i> <i>👩‍🦼</i> <i>🧑‍🦽</i> <i>👨‍🦽</i> <i>👩‍🦽</i> <i>🏃</i> <i>🏃‍</i> <i>🏃‍</i> <i>🚶‍➡️</i> <i>🚶‍‍➡️</i> <i>🚶‍‍➡️</i> <i>🧎‍➡️</i> <i>🧎‍‍➡️</i> <i>🧎‍‍➡️</i> <i>🧑‍🦯‍➡️</i> <i>👨‍🦯‍➡️</i> <i>👩‍🦯‍➡️</i> <i>🧑‍🦼‍➡️</i> <i>👨‍🦼‍➡️</i> <i>👩‍🦼‍➡️</i> <i>🧑‍🦽‍➡️</i> <i>👨‍🦽‍➡️</i> <i>👩‍🦽‍➡️</i> <i>🏃‍➡️</i> <i>🏃‍‍➡️</i> <i>🏃‍‍➡️</i> <i>💃</i> <i>🕺</i> <i>🕴️</i> <i>👯</i> <i>👯‍</i> <i>👯‍</i> <i>🧖</i> <i>🧖‍</i> <i>🧖‍</i> <i>🧗</i> <i>🧗‍</i> <i>🧗‍</i> <i>🤺</i> <i>🏇</i> <i>⛷️</i> <i>🏂️</i> <i>🏌️</i> <i>🏌️‍</i> <i>🏌️‍</i> <i>🏄️</i> <i>🏄‍</i> <i>🏄‍</i> <i>🚣</i> <i>🚣‍</i> <i>🚣‍</i> <i>🏊️</i> <i>🏊‍</i> <i>🏊‍</i> <i>⛹️</i> <i>⛹️‍</i> <i>⛹️‍</i> <i>🏋️</i> <i>🏋️‍</i> <i>🏋️‍</i> <i>🚴</i> <i>🚴‍</i> <i>🚴‍</i> <i>🚵</i> <i>🚵‍</i> <i>🚵‍</i> <i>🤸</i> <i>🤸‍</i> <i>🤸‍</i> <i>🤼</i> <i>🤼‍</i> <i>🤼‍</i> <i>🤽</i> <i>🤽‍</i> <i>🤽‍</i> <i>🤾</i> <i>🤾‍</i> <i>🤾‍</i> <i>🤹</i> <i>🤹‍</i> <i>🤹‍</i> <i>🧘</i> <i>🧘‍</i> <i>🧘‍</i> <i>🛀</i> <i>🛌</i> <i>🧑‍🤝‍🧑</i> <i>👭</i> <i>👫</i> <i>👬</i> <i>💏</i> <i>👩‍❤️‍💋‍👨</i> <i>👨‍❤️‍💋‍👨</i> <i>👩‍❤️‍💋‍👩</i> <i>💑</i> <i>👩‍❤️‍👨</i> <i>👨‍❤️‍👨</i> <i>👩‍❤️‍👩</i> <i>👪️</i> <i>👨‍👩‍👦</i> <i>👨‍👩‍👧</i> <i>👨‍👩‍👧‍👦</i> <i>👨‍👩‍👦‍👦</i> <i>👨‍👩‍👧‍👧</i> <i>👨‍👨‍👦</i> <i>👨‍👨‍👧</i> <i>👨‍👨‍👧‍👦</i> <i>👨‍👨‍👦‍👦</i> <i>👨‍👨‍👧‍👧</i> <i>👩‍👩‍👦</i> <i>👩‍👩‍👧</i> <i>👩‍👩‍👧‍👦</i> <i>👩‍👩‍👦‍👦</i> <i>👩‍👩‍👧‍👧</i> <i>👨‍👦</i> <i>👨‍👦‍👦</i> <i>👨‍👧</i> <i>👨‍👧‍👦</i> <i>👨‍👧‍👧</i> <i>👩‍👦</i> <i>👩‍👦‍👦</i> <i>👩‍👧</i> <i>👩‍👧‍👦</i> <i>👩‍👧‍👧</i> <i>🗣️</i> <i>👤</i> <i>👥</i> <i>🫂</i> <i>👣</i>'+
				'<br><br>'+
				'Animais e Natureza'+
				'<br>'+
				'<i>🐵</i> <i>🐒</i> <i>🦍</i> <i>🦧</i> <i>🐶</i> <i>🐕️</i> <i>🦮</i> <i>🐕‍🦺</i> <i>🐩</i> <i>🐺</i> <i>🦊</i> <i>🦝</i> <i>🐱</i> <i>🐈️</i> <i>🐈‍⬛</i> <i>🦁</i> <i>🐯</i> <i>🐅</i> <i>🐆</i> <i>🐴</i> <i>🐎</i> <i>🦄</i> <i>🦓</i> <i>🦌</i> <i>🦬</i> <i>🐮</i> <i>🐂</i> <i>🐃</i> <i>🐄</i> <i>🐷</i> <i>🐖</i> <i>🐗</i> <i>🐽</i> <i>🐏</i> <i>🐑</i> <i>🐐</i> <i>🐪</i> <i>🐫</i> <i>🦙</i> <i>🦒</i> <i>🐘</i> <i>🦣</i> <i>🦏</i> <i>🦛</i> <i>🐭</i> <i>🐁</i> <i>🐀</i> <i>🐹</i> <i>🐰</i> <i>🐇</i> <i>🐿️</i> <i>🦫</i> <i>🦔</i> <i>🦇</i> <i>🐻</i> <i>🐻‍❄️</i> <i>🐨</i> <i>🐼</i> <i>🦥</i> <i>🦦</i> <i>🦨</i> <i>🦘</i> <i>🦡</i> <i>🐾</i> <i>🦃</i> <i>🐔</i> <i>🐓</i> <i>🐣</i> <i>🐤</i> <i>🐥</i> <i>🐦️</i> <i>🐧</i> <i>🐦‍⬛</i> <i>🕊️</i> <i>🦅</i> <i>🦆</i> <i>🦢</i> <i>🦉</i> <i>🦤</i> <i>🦩</i> <i>🦚</i> <i>🦜</i> <i>🐦‍🔥</i> <i>🪶</i> <i>🪹</i> <i>🪺</i> <i>🥚</i> <i>🐸</i> <i>🐊</i> <i>🐢</i> <i>🦎</i> <i>🐍</i> <i>🐲</i> <i>🐉</i> <i>🦕</i> <i>🦖</i> <i>🐳</i> <i>🐋</i> <i>🐬</i> <i>🦭</i> <i>🐟️</i> <i>🐠</i> <i>🐡</i> <i>🦈</i> <i>🪼</i> <i>🐙</i> <i>🦑</i> <i>🦀</i> <i>🦞</i> <i>🦐</i> <i>🪸</i> <i>🦪</i> <i>🐚</i> <i>🐌</i> <i>🦋</i> <i>🐛</i> <i>🐜</i> <i>🐝</i> <i>🪲</i> <i>🐞</i> <i>🦗</i> <i>🪳</i> <i>🕷️</i> <i>🕸️</i> <i>🦂</i> <i>🦟</i> <i>🪰</i> <i>🪱</i> <i>🦠</i> <i>🍄</i> <i>🍄‍🟫</i> <i>💐</i> <i>💮</i> <i>🏵️</i> <i>🌼</i> <i>🌻</i> <i>🌹</i> <i>🥀</i> <i>🌺</i> <i>🌷</i> <i>🌸</i> <i>🪷</i> <i>🪻</i> <i>🌱</i> <i>🪴</i> <i>🏕️</i> <i>🌲</i> <i>🌳</i> <i>🌰</i> <i>🌴</i> <i>🌵</i> <i>🎋</i> <i>🎍</i> <i>🌾</i> <i>🌿</i> <i>☘️</i> <i>🍀</i> <i>🍁</i> <i>🍂</i> <i>🍃</i> <i>🌍️</i> <i>🌎️</i> <i>🌏️</i> <i>🌑</i> <i>🌒</i> <i>🌓</i> <i>🌔</i> <i>🌕️</i> <i>🌖</i> <i>🌗</i> <i>🌘</i> <i>🌙</i> <i>🌚</i> <i>🌛</i> <i>🌜️</i> <i>☀️</i> <i>🌝</i> <i>🌞</i> <i>🪐</i> <i>💫</i> <i>⭐️</i> <i>🌟</i> <i>✨</i> <i>🌠</i> <i>☄️</i> <i>🌌</i> <i>☁️</i> <i>⛅️</i> <i>⛈️</i> <i>🌤️</i> <i>🌥️</i> <i>🌦️</i> <i>🌧️</i> <i>🌨️</i> <i>🌩️</i> <i>🌪️</i> <i>🌫️</i> <i>🌬️</i> <i>🌀</i> <i>🌈</i> <i>🌂</i> <i>☂️</i> <i>☔️</i> <i>⛱️</i> <i>⚡️</i> <i>❄️</i> <i>☃️</i> <i>⛄️</i> <i>🏔️</i> <i>⛰️</i> <i>🗻</i> <i>🌋</i> <i>🔥</i> <i>💧</i> <i>🌊</i> <i>💥</i> <i>💦</i> <i>💨</i>'+
				'<br><br>'+
				'Comidas'+
				'<br>'+
				'<i>🍇</i> <i>🍈</i> <i>🍉</i> <i>🍊</i> <i>🍋</i> <i>🍋‍🟩</i> <i>🍌</i> <i>🍍</i> <i>🥭</i> <i>🍎</i> <i>🍏</i> <i>🍐</i> <i>🍑</i> <i>🍒</i> <i>🍓</i> <i>🫐</i> <i>🥝</i> <i>🍅</i> <i>🫒</i> <i>🥥</i> <i>🥑</i> <i>🍆</i> <i>🥔</i> <i>🥕</i> <i>🌽</i> <i>🌶️</i> <i>🫑</i> <i>🥒</i> <i>🥬</i> <i>🥦</i> <i>🫛</i> <i>🧄</i> <i>🧅</i> <i>🫚</i> <i>🍄</i> <i>🍄‍🟫</i> <i>🫘</i> <i>🥜</i> <i>🌰</i> <i>🍞</i> <i>🥐</i> <i>🥖</i> <i>🫓</i> <i>🥨</i> <i>🥯</i> <i>🥞</i> <i>🧇</i> <i>🧀</i> <i>🍖</i> <i>🍗</i> <i>🥩</i> <i>🥓</i> <i>🍔</i> <i>🍟</i> <i>🍕</i> <i>🌭</i> <i>🥪</i> <i>🌮</i> <i>🌯</i> <i>🫔</i> <i>🥙</i> <i>🧆</i> <i>🥚</i> <i>🍳</i> <i>🥘</i> <i>🍲</i> <i>🫕</i> <i>🥣</i> <i>🥗</i> <i>🍿</i> <i>🧈</i> <i>🧂</i> <i>🥫</i> <i>🍱</i> <i>🍘</i> <i>🍙</i> <i>🍚</i> <i>🍛</i> <i>🍜</i> <i>🍝</i> <i>🍠</i> <i>🍢</i> <i>🍣</i> <i>🍤</i> <i>🍥</i> <i>🥮</i> <i>🍡</i> <i>🥟</i> <i>🥠</i> <i>🥡</i> <i>🍦</i> <i>🍧</i> <i>🍨</i> <i>🍩</i> <i>🍪</i> <i>🎂</i> <i>🍰</i> <i>🧁</i> <i>🥧</i> <i>🍫</i> <i>🍬</i> <i>🍭</i> <i>🍮</i> <i>🍯</i> <i>🍼</i> <i>🥛</i> <i>🫗</i> <i>☕️</i> <i>🫖</i> <i>🍵</i> <i>🍶</i> <i>🍾</i> <i>🍷</i> <i>🍸️</i> <i>🍹</i> <i>🍺</i> <i>🍻</i> <i>🥂</i> <i>🥃</i> <i>🥤</i> <i>🧋</i> <i>🧃</i> <i>🧉</i> <i>🧊</i> <i>🥢</i> <i>🍽️</i> <i>🍴</i> <i>🥄</i> <i>🔪</i>'+
				'<br><br>'+
				'Esportes'+
				'<br>'+
				'<i>⚽️</i> <i>⚾️</i> <i>🥎</i> <i>🏀</i> <i>🏐</i> <i>🏈</i> <i>🏉</i> <i>🎾</i> <i>🥏</i> <i>🎳</i> <i>🏏</i> <i>🏑</i> <i>🏒</i> <i>🥍</i> <i>🏓</i> <i>🏸</i> <i>🥊</i> <i>🥋</i> <i>🥅</i> <i>⛳️</i> <i>⛸️</i> <i>🎣</i> <i>🤿</i> <i>🎽</i> <i>🎿</i> <i>🛷</i> <i>🥌</i> <i>🎯</i> <i>🪀</i> <i>🪁</i> <i>🎱</i> <i>🎖️</i> <i>🏆️</i> <i>🏅</i> <i>🥇</i> <i>🥈</i> <i>🥉</i>'+
				'<br><br>'+
				'Veículos e Viagens'+
				'<br>'+
				'<i>🏔️</i> <i>⛰️</i> <i>🌋</i> <i>🗻</i> <i>🏕️</i> <i>🏖️</i> <i>🏜️</i> <i>🏝️</i> <i>🏟️</i> <i>🏛️</i> <i>🏗️</i> <i>🧱</i> <i>🪨</i> <i>🪵</i> <i>🛖</i> <i>🏘️</i> <i>🏚️</i> <i>🏠️</i> <i>🏡</i> <i>🏢</i> <i>🏣</i> <i>🏤</i> <i>🏥</i> <i>🏦</i> <i>🏨</i> <i>🏩</i> <i>🏪</i> <i>🏫</i> <i>🏬</i> <i>🏭️</i> <i>🏯</i> <i>🏰</i> <i>💒</i> <i>🗼</i> <i>🗽</i> <i>⛪️</i> <i>🕌</i> <i>🛕</i> <i>🕍</i> <i>⛩️</i> <i>🕋</i> <i>⛲️</i> <i>⛺️</i> <i>🌁</i> <i>🌃</i> <i>🏙️</i> <i>🌄</i> <i>🌅</i> <i>🌆</i> <i>🌇</i> <i>🌉</i> <i>🗾</i> <i>🏞️</i> <i>🎠</i> <i>🎡</i> <i>🎢</i> <i>💈</i> <i>🎪</i> <i>🚂</i> <i>🚃</i> <i>🚄</i> <i>🚅</i> <i>🚆</i> <i>🚇️</i> <i>🚈</i> <i>🚉</i> <i>🚊</i> <i>🚝</i> <i>🚞</i> <i>🚋</i> <i>🚌</i> <i>🚍️</i> <i>🚎</i> <i>🚐</i> <i>🚑️</i> <i>🚒</i> <i>🚓</i> <i>🚔️</i> <i>🚕</i> <i>🚖</i> <i>🚗</i> <i>🚘️</i> <i>🚙</i> <i>🛻</i> <i>🚚</i> <i>🚛</i> <i>🚜</i> <i>🏎️</i> <i>🏍️</i> <i>🛵</i> <i>🦽</i> <i>🦼</i> <i>🛺</i> <i>🚲️</i> <i>🛴</i> <i>🛹</i> <i>🛼</i> <i>🚏</i> <i>🛣️</i> <i>🛤️</i> <i>🛢️</i> <i>⛽️</i> <i>🚨</i> <i>🚥</i> <i>🚦</i> <i>🛑</i> <i>🚧</i> <i>⚓️</i> <i>⛵️</i> <i>🛶</i> <i>🚤</i> <i>🛳️</i> <i>⛴️</i> <i>🛥️</i> <i>🚢</i> <i>✈️</i> <i>🛩️</i> <i>🛫</i> <i>🛬</i> <i>🪂</i> <i>💺</i> <i>🚁</i> <i>🚟</i> <i>🚠</i> <i>🚡</i> <i>🛰️</i> <i>🚀</i> <i>🛸</i> <i>🎆</i> <i>🎇</i> <i>🎑</i> <i>🗿</i>'+
				'<br><br>'+
				'Objetos'+
				'<br>'+
				'<i>🛎️</i> <i>🧳</i> <i>⌛️</i> <i>⏳️</i> <i>⌚️</i> <i>⏰</i> <i>⏱️</i> <i>⏲️</i> <i>🕰️</i> <i>🌡️</i> <i>🗺️</i> <i>🧭</i> <i>🎃</i> <i>🎄</i> <i>🧨</i> <i>🎈</i> <i>🎉</i> <i>🎊</i> <i>🎎</i> <i>🪭</i> <i>🎏</i> <i>🎐</i> <i>🎀</i> <i>🎁</i> <i>🎗️</i> <i>🎟️</i> <i>🎫</i> <i>🔮</i> <i>🪄</i> <i>🧿</i> <i>🎮️</i> <i>🕹️</i> <i>🎰</i> <i>🎲</i> <i>♟️</i> <i>🧩</i> <i>🧸</i> <i>🪅</i> <i>🪆</i> <i>🖼️</i> <i>🎨</i> <i>🧵</i> <i>🪡</i> <i>🧶</i> <i>🪢</i> <i>👓️</i> <i>🕶️</i> <i>🥽</i> <i>🥼</i> <i>🦺</i> <i>👔</i> <i>👕</i> <i>👖</i> <i>🧣</i> <i>🧤</i> <i>🧥</i> <i>🧦</i> <i>👗</i> <i>👘</i> <i>🥻</i> <i>🩱</i> <i>🩲</i> <i>🩳</i> <i>👙</i> <i>👚</i> <i>👛</i> <i>👜</i> <i>👝</i> <i>🛍️</i> <i>🎒</i> <i>🩴</i> <i>👞</i> <i>👟</i> <i>🥾</i> <i>🥿</i> <i>👠</i> <i>👡</i> <i>🩰</i> <i>👢</i> <i>👑</i> <i>👒</i> <i>🎩</i> <i>🎓️</i> <i>🧢</i> <i>🪖</i> <i>⛑️</i> <i>📿</i> <i>💄</i> <i>💍</i> <i>💎</i> <i>📢</i> <i>📣</i> <i>📯</i> <i>🎙️</i> <i>🎚️</i> <i>🎛️</i> <i>🎤</i> <i>🎧️</i> <i>📻️</i> <i>🎷</i> <i>🪗</i> <i>🎸</i> <i>🎹</i> <i>🎺</i> <i>🎻</i> <i>🪕</i> <i>🪈</i> <i>🪇</i> <i>🥁</i> <i>🪘</i> <i>🪩</i> <i>📱</i> <i>📲</i> <i>☎️</i> <i>📞</i> <i>📟️</i> <i>📠</i> <i>🔋</i> <i>🪫</i> <i>🔌</i> <i>💻️</i> <i>🖥️</i> <i>🖨️</i> <i>⌨️</i> <i>🖱️</i> <i>🖲️</i> <i>💽</i> <i>💾</i> <i>💿️</i> <i>📀</i> <i>🧮</i> <i>🎥</i> <i>🎞️</i> <i>📽️</i> <i>🎬️</i> <i>📺️</i> <i>📷️</i> <i>📸</i> <i>📹️</i> <i>📼</i> <i>🔍️</i> <i>🔎</i> <i>🕯️</i> <i>💡</i> <i>🔦</i> <i>🏮</i> <i>🪔</i> <i>📔</i> <i>📕</i> <i>📖</i> <i>📗</i> <i>📘</i> <i>📙</i> <i>📚️</i> <i>📓</i> <i>📒</i> <i>📃</i> <i>📜</i> <i>📄</i> <i>📰</i> <i>🗞️</i> <i>📑</i> <i>🔖</i> <i>🏷️</i> <i>💰️</i> <i>🪙</i> <i>💴</i> <i>💵</i> <i>💶</i> <i>💷</i> <i>💸</i> <i>💳️</i> <i>🪪</i> <i>🧾</i> <i>✉️</i> <i>💌</i> <i>📧</i> <i>🧧</i> <i>📨</i> <i>📩</i> <i>📤️</i> <i>📥️</i> <i>📦️</i> <i>📫️</i> <i>📪️</i> <i>📬️</i> <i>📭️</i> <i>📮</i> <i>🗳️</i> <i>✏️</i> <i>✒️</i> <i>🖋️</i> <i>🖊️</i> <i>🖌️</i> <i>🖍️</i> <i>📝</i> <i>💼</i> <i>📁</i> <i>📂</i> <i>🗂️</i> <i>📅</i> <i>📆</i> <i>🗒️</i> <i>🗓️</i> <i>📇</i> <i>📈</i> <i>📉</i> <i>📊</i> <i>📋️</i> <i>📌</i> <i>📍</i> <i>📎</i> <i>🖇️</i> <i>📏</i> <i>📐</i> <i>✂️</i> <i>🗃️</i> <i>🗄️</i> <i>🗑️</i> <i>🔒️</i> <i>🔓️</i> <i>🔏</i> <i>🔐</i> <i>🔑</i> <i>🗝️</i> <i>🔨</i> <i>🪓</i> <i>⛏️</i> <i>⚒️</i> <i>🛠️</i> <i>🗡️</i> <i>⚔️</i> <i>💣️</i> <i>🔫</i> <i>🪃</i> <i>🏹</i> <i>🛡️</i> <i>🪚</i> <i>🔧</i> <i>🪛</i> <i>🔩</i> <i>⚙️</i> <i>🗜️</i> <i>⚖️</i> <i>🦯</i> <i>🔗</i> <i>⛓️‍💥</i> <i>⛓️</i> <i>🪝</i> <i>🧰</i> <i>🧲</i> <i>🪜</i> <i>🛝</i> <i>🛞</i> <i>🫙</i> <i>⚗️</i> <i>🧪</i> <i>🧫</i> <i>🧬</i> <i>🔬</i> <i>🔭</i> <i>📡</i> <i>🩻</i> <i>💉</i> <i>🩸</i> <i>💊</i> <i>🩹</i> <i>🩺</i> <i>🩼</i> <i>🚪</i> <i>🛗</i> <i>🪞</i> <i>🪟</i> <i>🛏️</i> <i>🛋️</i> <i>🪑</i> <i>🪤</i> <i>🚽</i> <i>🪠</i> <i>🚿</i> <i>🛁</i> <i>🧼</i> <i>🫧</i> <i>🪒</i> <i>🪮</i> <i>🧴</i> <i>🧷</i> <i>🧹</i> <i>🧺</i> <i>🧻</i> <i>🪣</i> <i>🪥</i> <i>🧽</i> <i>🧯</i> <i>🛟</i> <i>🛒</i> <i>🚬</i> <i>⚰️</i> <i>🪦</i> <i>⚱️</i> <i>🏺</i> <i>🪧</i> <i>🕳️</i>'+
				'<br><br>'+
				'Símbolos'+
				'<br>'+
				'<i>💘</i> <i>💝</i> <i>💖</i> <i>💗</i> <i>💓</i> <i>💞</i> <i>💕</i> <i>💟</i> <i>❣️</i> <i>💔</i> <i>❤️</i> <i>🧡</i> <i>💛</i> <i>💚</i> <i>🩵</i> <i>💙</i> <i>💜</i> <i>🩷</i> <i>🤎</i> <i>🖤</i> <i>🩶</i> <i>🤍</i> <i>❤️‍🔥</i> <i>❤️‍🩹</i> <i>💯</i> <i>♨️</i> <i>💢</i> <i>💬</i> <i>👁️‍🗨️</i> <i>🗨️</i> <i>🗯️</i> <i>💭</i> <i>💤</i> <i>🌐</i> <i>♠️</i> <i>♥️</i> <i>♦️</i> <i>♣️</i> <i>🃏</i> <i>🀄️</i> <i>🎴</i> <i>🎭️</i> <i>🔇</i> <i>🔈️</i> <i>🔉</i> <i>🔊</i> <i>🔔</i> <i>🔕</i> <i>🎼</i> <i>🎵</i> <i>🎶</i> <i>💹</i> <i>🏧</i> <i>🚮</i> <i>🚰</i> <i>♿️</i> <i>🚹️</i> <i>🚺️</i> <i>🚻</i> <i>🚼️</i> <i>🧑‍🧑‍🧒</i> <i>🧑‍🧑‍🧒‍🧒</i> <i>🧑‍🧒</i> <i>🧑‍🧒‍🧒</i> <i>🚾</i> <i>🛂</i> <i>🛃</i> <i>🛄</i> <i>🛅</i> <i>🛜</i> <i>⛓️‍💥</i> <i>⚠️</i> <i>🚸</i> <i>⛔️</i> <i>🚫</i> <i>🚳</i> <i>🚭️</i> <i>🚯</i> <i>🚱</i> <i>🚷</i> <i>📵</i> <i>🔞</i> <i>☢️</i> <i>☣️</i> <i>⬆️</i> <i>↗️</i> <i>➡️</i> <i>↘️</i> <i>⬇️</i> <i>↙️</i> <i>⬅️</i> <i>↖️</i> <i>↕️</i> <i>↔️</i> <i>↩️</i> <i>↪️</i> <i>⤴️</i> <i>⤵️</i> <i>🔃</i> <i>🔄</i> <i>🔙</i> <i>🔚</i> <i>🔛</i> <i>🔜</i> <i>🔝</i> <i>🛐</i> <i>⚛️</i> <i>🕉️</i> <i>✡️</i> <i>☸️</i> <i>🪯</i> <i>☯️</i> <i>✝️</i> <i>☦️</i> <i>☪️</i> <i>☮️</i> <i>🕎</i> <i>🔯</i> <i>🪬</i> <i>♈️</i> <i>♉️</i> <i>♊️</i> <i>♋️</i> <i>♌️</i> <i>♍️</i> <i>♎️</i> <i>♏️</i> <i>♐️</i> <i>♑️</i> <i>♒️</i> <i>♓️</i> <i>⛎</i> <i>🔀</i> <i>🔁</i> <i>🔂</i> <i>▶️</i> <i>⏩️</i> <i>⏭️</i> <i>⏯️</i> <i>◀️</i> <i>⏪️</i> <i>⏮️</i> <i>🔼</i> <i>⏫</i> <i>🔽</i> <i>⏬</i> <i>⏸️</i> <i>⏹️</i> <i>⏺️</i> <i>⏏️</i> <i>🎦</i> <i>🔅</i> <i>🔆</i> <i>📶</i> <i>📳</i> <i>📴</i> <i></i> <i></i> <i>⚧</i> <i>✖️</i> <i>➕</i> <i>➖</i> <i>➗</i> <i>🟰</i> <i>♾️</i> <i>‼️</i> <i>⁉️</i> <i>❓️</i> <i>❔</i> <i>❕</i> <i>❗️</i> <i>〰️</i> <i>💱</i> <i>💲</i> <i>⚕️</i> <i>♻️</i> <i>⚜️</i> <i>🔱</i> <i>📛</i> <i>🔰</i> <i>⭕️</i> <i>✅</i> <i>☑️</i> <i>✔️</i> <i>❌</i> <i>❎</i> <i>➰</i> <i>➿</i> <i>〽️</i> <i>✳️</i> <i>✴️</i> <i>❇️</i> <i>©️</i> <i>®️</i> <i>™️</i> <i>#️⃣</i> <i>*️⃣</i> <i>0️⃣</i> <i>1️⃣</i> <i>2️⃣</i> <i>3️⃣</i> <i>4️⃣</i> <i>5️⃣</i> <i>6️⃣</i> <i>7️⃣</i> <i>8️⃣</i> <i>9️⃣</i> <i>🔟</i> <i>🔠</i> <i>🔡</i> <i>🔢</i> <i>🔣</i> <i>🔤</i> <i>🅰️</i> <i>🆎</i> <i>🅱️</i> <i>🆑</i> <i>🆒</i> <i>🆓</i> <i>ℹ️</i> <i>🆔</i> <i>Ⓜ️</i> <i>🆕</i> <i>🆖</i> <i>🅾️</i> <i>🆗</i> <i>🅿️</i> <i>🆘</i> <i>🆙</i> <i>🆚</i> <i>🈁</i> <i>🈂️</i> <i>🈷️</i> <i>🈶</i> <i>🈯️</i> <i>🉐</i> <i>🈹</i> <i>🈚️</i> <i>🈲</i> <i>🉑</i> <i>🈸</i> <i>🈴</i> <i>🈳</i> <i>㊗️</i> <i>㊙️</i> <i>🈺</i> <i>🈵</i> <i>🔴</i> <i>🟠</i> <i>🟡</i> <i>🟢</i> <i>🔵</i> <i>🟣</i> <i>🟤</i> <i>⚫️</i> <i>⚪️</i> <i>🟥</i> <i>🟧</i> <i>🟨</i> <i>🟩</i> <i>🟦</i> <i>🟪</i> <i>🟫</i> <i>⬛️</i> <i>⬜️</i> <i>◼️</i> <i>◻️</i> <i>◾️</i> <i>◽️</i> <i>▪️</i> <i>▫️</i> <i>🔶</i> <i>🔷</i> <i>🔸</i> <i>🔹</i> <i>🔺</i> <i>🔻</i> <i>💠</i> <i>🔘</i> <i>🔳</i> <i>🔲</i> <i>🕛️</i> <i>🕧️</i> <i>🕐️</i> <i>🕜️</i> <i>🕑️</i> <i>🕝️</i> <i>🕒️</i> <i>🕞️</i> <i>🕓️</i> <i>🕟️</i> <i>🕔️</i> <i>🕠️</i> <i>🕕️</i> <i>🕡️</i> <i>🕖️</i> <i>🕢️</i> <i>🕗️</i> <i>🕣️</i> <i>🕘️</i> <i>🕤️</i> <i>🕙️</i> <i>🕥️</i> <i>🕚️</i> <i>🕦️</i> <i>*️</i> <i>#️</i> <i>0️</i> <i>1️</i> <i>2️</i> <i>3️</i> <i>4️</i> <i>5️</i> <i>6️</i> <i>7️</i> <i>8️</i> <i>9️</i>'+
				'<br><br>'+
				'Outros'+
				'<br>'+
				'<i>🏻</i> <i>🏼</i> <i>🏽</i> <i>🏾</i> <i>🏿</i> <i></i> <i></i> <i>⚕</i> <i>🦲</i> <i>🦱</i> <i>🦰</i> <i>🦳</i>'+
				'<br><br>'+
				'Indicadores'+
				'<br>'+
				'<i>🇦</i> <i>🇧</i> <i>🇨</i> <i>🇩</i> <i>🇪</i> <i>🇫</i> <i>🇬</i> <i>🇭</i> <i>🇮</i> <i>🇯</i> <i>🇰</i> <i>🇱</i> <i>🇲</i> <i>🇳</i> <i>🇴</i> <i>🇵</i> <i>🇶</i> <i>🇷</i> <i>🇸</i> <i>🇹</i> <i>🇺</i> <i>🇻</i> <i>🇼</i> <i>🇽</i> <i>🇾</i> <i>🇿</i>'+
				'<br><br>'+
				'Bandeiras'+
				'<br>'+
				'<i>🏁</i> <i>🚩</i> <i>🎌</i> <i>🏴</i> <i>🏳️</i> <i>🏴‍☠️</i> <i>🇦🇨</i> <i>🇦🇩</i> <i>🇦🇪</i> <i>🇦🇫</i> <i>🇦🇬</i> <i>🇦🇮</i> <i>🇦🇱</i> <i>🇦🇲</i> <i>🇦🇴</i> <i>🇦🇶</i> <i>🇦🇷</i> <i>🇦🇸</i> <i>🇦🇹</i> <i>🇦🇺</i> <i>🇦🇼</i> <i>🇦🇽</i> <i>🇦🇿</i> <i>🇧🇦</i> <i>🇧🇧</i> <i>🇧🇩</i> <i>🇧🇪</i> <i>🇧🇫</i> <i>🇧🇬</i> <i>🇧🇭</i> <i>🇧🇮</i> <i>🇧🇯</i> <i>🇧🇱</i> <i>🇧🇲</i> <i>🇧🇳</i> <i>🇧🇴</i> <i>🇧🇶</i> <i>🇧🇷</i> <i>🇧🇸</i> <i>🇧🇹</i> <i>🇧🇻</i> <i>🇧🇼</i> <i>🇧🇾</i> <i>🇧🇿</i> <i>🇨🇦</i> <i>🇨🇨</i> <i>🇨🇩</i> <i>🇨🇫</i> <i>🇨🇬</i> <i>🇨🇭</i> <i>🇨🇮</i> <i>🇨🇰</i> <i>🇨🇱</i> <i>🇨🇲</i> <i>🇨🇳</i> <i>🇨🇴</i> <i>🇨🇵</i> <i>🇨🇷</i> <i>🇨🇺</i> <i>🇨🇻</i> <i>🇨🇼</i> <i>🇨🇽</i> <i>🇨🇾</i> <i>🇨🇿</i> <i>🇩🇪</i> <i>🇩🇬</i> <i>🇩🇯</i> <i>🇩🇰</i> <i>🇩🇲</i> <i>🇩🇴</i> <i>🇩🇿</i> <i>🇪🇦</i> <i>🇪🇨</i> <i>🇪🇪</i> <i>🇪🇬</i> <i>🇪🇭</i> <i>🇪🇷</i> <i>🇪🇸</i> <i>🇪🇹</i> <i>🇪🇺</i> <i>🇫🇮</i> <i>🇫🇯</i> <i>🇫🇰</i> <i>🇫🇲</i> <i>🇫🇴</i> <i>🇫🇷</i> <i>🇬🇦</i> <i>🇬🇧</i> <i>🇬🇩</i> <i>🇬🇪</i> <i>🇬🇫</i> <i>🇬🇬</i> <i>🇬🇭</i> <i>🇬🇮</i> <i>🇬🇱</i> <i>🇬🇲</i> <i>🇬🇳</i> <i>🇬🇵</i> <i>🇬🇶</i> <i>🇬🇷</i> <i>🇬🇸</i> <i>🇬🇹</i> <i>🇬🇺</i> <i>🇬🇼</i> <i>🇬🇾</i> <i>🇭🇰</i> <i>🇭🇲</i> <i>🇭🇳</i> <i>🇭🇷</i> <i>🇭🇹</i> <i>🇭🇺</i> <i>🇮🇨</i> <i>🇮🇩</i> <i>🇮🇪</i> <i>🇮🇱</i> <i>🇮🇲</i> <i>🇮🇳</i> <i>🇮🇴</i> <i>🇮🇶</i> <i>🇮🇷</i> <i>🇮🇸</i> <i>🇮🇹</i> <i>🇯🇪</i> <i>🇯🇲</i> <i>🇯🇴</i> <i>🇯🇵</i> <i>🇰🇪</i> <i>🇰🇬</i> <i>🇰🇭</i> <i>🇰🇮</i> <i>🇰🇲</i> <i>🇰🇳</i> <i>🇰🇵</i> <i>🇰🇷</i> <i>🇰🇼</i> <i>🇰🇾</i> <i>🇰🇿</i> <i>🇱🇦</i> <i>🇱🇧</i> <i>🇱🇨</i> <i>🇱🇮</i> <i>🇱🇰</i> <i>🇱🇷</i> <i>🇱🇸</i> <i>🇱🇹</i> <i>🇱🇺</i> <i>🇱🇻</i> <i>🇱🇾</i> <i>🇲🇦</i> <i>🇲🇨</i> <i>🇲🇩</i> <i>🇲🇪</i> <i>🇲🇫</i> <i>🇲🇬</i> <i>🇲🇭</i> <i>🇲🇰</i> <i>🇲🇱</i> <i>🇲🇲</i> <i>🇲🇳</i> <i>🇲🇴</i> <i>🇲🇵</i> <i>🇲🇶</i> <i>🇲🇷</i> <i>🇲🇸</i> <i>🇲🇹</i> <i>🇲🇺</i> <i>🇲🇻</i> <i>🇲🇼</i> <i>🇲🇽</i> <i>🇲🇾</i> <i>🇲🇿</i> <i>🇳🇦</i> <i>🇳🇨</i> <i>🇳🇪</i> <i>🇳🇫</i> <i>🇳🇬</i> <i>🇳🇮</i> <i>🇳🇱</i> <i>🇳🇴</i> <i>🇳🇵</i> <i>🇳🇷</i> <i>🇳🇺</i> <i>🇳🇿</i> <i>🇴🇲</i> <i>🇵🇦</i> <i>🇵🇪</i> <i>🇵🇫</i> <i>🇵🇬</i> <i>🇵🇭</i> <i>🇵🇰</i> <i>🇵🇱</i> <i>🇵🇲</i> <i>🇵🇳</i> <i>🇵🇷</i> <i>🇵🇸</i> <i>🇵🇹</i> <i>🇵🇼</i> <i>🇵🇾</i> <i>🇶🇦</i> <i>🇷🇪</i> <i>🇷🇴</i> <i>🇷🇸</i> <i>🇷🇺</i> <i>🇷🇼</i> <i>🇸🇦</i> <i>🇸🇧</i> <i>🇸🇨</i> <i>🇸🇩</i> <i>🇸🇪</i> <i>🇸🇬</i> <i>🇸🇭</i> <i>🇸🇮</i> <i>🇸🇯</i> <i>🇸🇰</i> <i>🇸🇱</i> <i>🇸🇲</i> <i>🇸🇳</i> <i>🇸🇴</i> <i>🇸🇷</i> <i>🇸🇸</i> <i>🇸🇹</i> <i>🇸🇻</i> <i>🇸🇽</i> <i>🇸🇾</i> <i>🇸🇿</i> <i>🇹🇦</i> <i>🇹🇨</i> <i>🇹🇩</i> <i>🇹🇫</i> <i>🇹🇬</i> <i>🇹🇭</i> <i>🇹🇯</i> <i>🇹🇰</i> <i>🇹🇱</i> <i>🇹🇲</i> <i>🇹🇳</i> <i>🇹🇴</i> <i>🇹🇷</i> <i>🇹🇹</i> <i>🇹🇻</i> <i>🇹🇼</i> <i>🇹🇿</i> <i>🇺🇦</i> <i>🇺🇬</i> <i>🇺🇳</i> <i>🇺🇸</i> <i>🇺🇾</i> <i>🇺🇿</i> <i>🇻🇦</i> <i>🇻🇨</i> <i>🇻🇪</i> <i>🇻🇬</i> <i>🇻🇮</i> <i>🇻🇳</i> <i>🇻🇺</i> <i>🇼🇫</i> <i>🇼🇸</i> <i>🇽🇰</i> <i>🇾🇪</i> <i>🇾🇹</i> <i>🇿🇦</i> <i>🇿🇲</i> <i>🇿🇼</i>'+
				'<br><br>'+
				'Setas'+
				'<br>'+
                '<i>⬀</i> <i>⬁</i> <i>⬂</i> <i>⬃</i> <i>⬄</i> <i>⬅</i> <i>⬆</i> <i>⬇</i> <i>⬈</i> <i>⬉</i> <i>⬊</i> <i>⬋</i> <i>⬌</i> <i>⬍</i> <i>⬎</i> <i>⬏</i> <i>⬐</i> <i>⬑</i> <i>⬒</i> <i>⬓</i> <i>⬔</i> <i>⬕</i> <i>⬖</i> <i>⬗</i> <i>⬘</i> <i>⬙</i> <i>⬚</i> <i>⬝</i> <i>⬞</i> <i>⬟</i> <i>⬠</i> <i>⬡</i> <i>⬢</i> <i>⬣</i> <i>⬤</i> <i>⬥</i> <i>⬦</i> <i>⬧</i> <i>⬨</i> <i>⬩</i> <i>⬪</i> <i>⬫</i> <i>⬬</i> <i>⬭</i> <i>⬮</i> <i>⬯</i> <i>⬰</i> <i>⬱</i> <i>⬲</i> <i>⬳</i> <i>⬴</i> <i>⬵</i> <i>⬶</i> <i>⬷</i> <i>⬸</i> <i>⬹</i> <i>⬺</i> <i>⬻</i> <i>⬼</i> <i>⬽</i> <i>⬾</i> <i>⬿</i> <i>⭀</i> <i>⭁</i> <i>⭂</i> <i>⭃</i> <i>⭄</i> <i>⭅</i> <i>⭆</i> <i>⭇</i> <i>⭈</i> <i>⭉</i> <i>⭊</i> <i>⭋</i> <i>⭌</i> <i>⭍</i> <i>⭎</i> <i>⭏<</i> <i>⭑</i> <i>⭒</i> <i>⭓</i> <i>⭔</i> <i>⭖</i> <i>⭗</i> <i>⭘</i> <i>⭙</i> <i>⭚</i> <i>⭛</i> <i>⭜</i> <i>⭝</i> <i>⭞</i> <i>⭟</i> <i>⭠</i> <i>⭡</i> <i>⭢</i> <i>⭣</i> <i>⭤</i> <i>⭥</i> <i>⭦</i> <i>⭧</i> <i>⭨</i> <i>⭩</i> <i>⭪</i> <i>⭫</i> <i>⭬</i> <i>⭭</i> <i>⭮</i> <i>⭯</i> <i>⭰</i> <i>⭱</i> <i>⭲</i> <i>⭳</i> <i>⭶</i> <i>⭷</i> <i>⭸</i> <i>⭹</i> <i>⭺</i> <i>⭻</i> <i>⭼</i> <i>⭽</i> <i>⭾</i> <i>⭿</i> <i>⮀</i> <i>⮁</i> <i>⮂</i> <i>⮃</i> <i>⮄</i> <i>⮅</i> <i>⮆</i> <i>⮇</i> <i>⮈</i> <i>⮉</i> <i>⮊</i> <i>⮋</i> <i>⮌</i> <i>⮍</i> <i>⮎</i> <i>⮏</i> <i>⮐</i> <i>⮑</i> <i>⮒</i> <i>⮓</i> <i>⮔</i> <i>⮕</i> <i>⮘</i> <i>⮙</i> <i>⮚</i> <i>⮛</i> <i>⮜</i> <i>⮝</i> <i>⮞</i> <i>⮟</i> <i>⮠</i> <i>⮡</i> <i>⮢</i> <i>⮣</i> <i>⮤</i> <i>⮥</i> <i>⮦</i> <i>⮧</i> <i>⮨</i> <i>⮩</i> <i>⮪</i> <i>⮫</i> <i>⮬</i> <i>⮭</i> <i>⮮</i> <i>⮯</i> <i>⮰</i> <i>⮱</i> <i>⮲</i> <i>⮳</i> <i>⮴</i> <i>⮵</i> <i>⮶</i> <i>⮷</i> <i>⮸</i> <i>⮹</i> <i>⮽</i> <i>⮾</i> <i>⮿</i> <i>⯀</i> <i>⯁</i> <i>⯂</i> <i>⯃</i> <i>⯄</i> <i>⯅</i> <i>⯆</i> <i>⯇</i> <i>⯈</i> <i>⯊</i> <i>⯋</i> <i>⯌</i> <i>⯍</i> <i>⯎</i> <i>⯏</i> <i>⯐</i> <i>⯑</i> <i>🠀</i> <i>🠁</i> <i>🠂</i> <i>🠃</i> <i>🠄</i> <i>🠅</i> <i>🠆</i> <i>🠇</i> <i>🠈</i> <i>🠉</i> <i>🠊</i> <i>🠋</i> <i>🠐</i> <i>🠑</i> <i>🠒</i> <i>🠓</i> <i>🠔</i> <i>🠕</i> <i>🠖</i> <i>🠗</i> <i>🠘</i> <i>🠙</i> <i>🠚</i> <i>🠛</i> <i>🠜</i> <i>🠝</i> <i>🠞</i> <i>🠟</i> <i>🠠</i> <i>🠡</i> <i>🠢</i> <i>🠣</i> <i>🠤</i> <i>🠥</i> <i>🠦</i> <i>🠧</i> <i>🠨</i> <i>🠩</i> <i>🠪</i> <i>🠫</i> <i>🠬</i> <i>🠭</i> <i>🠮</i> <i>🠯</i> <i>🠰</i> <i>🠱</i> <i>🠲</i> <i>🠳</i> <i>🠴</i> <i>🠵</i> <i>🠶</i> <i>🠷</i> <i>🠸</i> <i>🠹</i> <i>🠺</i> <i>🠻</i> <i>🠼</i> <i>🠽</i> <i>🠾</i> <i>🠿</i> <i>🡀</i> <i>🡁</i> <i>🡂</i> <i>🡃</i> <i>🡄</i> <i>🡅</i> <i>🡆</i> <i>🡇</i> <i>🡐</i> <i>🡑</i> <i>🡒</i> <i>🡓</i> <i>🡔</i> <i>🡕</i> <i>🡖</i> <i>🡗</i> <i>🡘</i> <i>🡙</i> <i>🡠</i> <i>🡡</i> <i>🡢</i> <i>🡣</i> <i>🡤</i> <i>🡥</i> <i>🡦</i> <i>🡧</i> <i>🡨</i> <i>🡩</i> <i>🡪</i> <i>🡫</i> <i>🡬</i> <i>🡭</i> <i>🡮</i> <i>🡯</i> <i>🡰</i> <i>🡱</i> <i>🡲</i> <i>🡳</i> <i>🡴</i> <i>🡵</i> <i>🡶</i> <i>🡷</i> <i>🡸</i> <i>🡹</i> <i>🡺</i> <i>🡻</i> <i>🡼</i> <i>🡽</i> <i>🡾</i> <i>🡿</i> <i>🢀</i> <i>🢁</i> <i>🢂</i> <i>🢃</i> <i>🢄</i> <i>🢅</i> <i>🢆</i> <i>🢇</i>'+
                '<br><br>'+
                'Variações de cores'+
				'<br>'+
				'<i>👋🏻</i> <i>🤚🏻</i> <i>🖐🏻</i> <i>✋🏻</i> <i>🖖🏻</i> <i>👌🏻</i> <i>🤌🏻</i> <i>🤏🏻</i> <i>✌🏻</i> <i>🤞🏻</i> <i>🤟🏻</i> <i>🤘🏻</i> <i>🤙🏻</i> <i>👈🏻</i> <i>👉🏻</i> <i>👆🏻</i> <i>🖕🏻</i> <i>👇🏻</i> <i>☝🏻</i> <i>🫵🏻</i> <i>👍🏻</i> <i>👎🏻</i> <i>✊🏻</i> <i>👊🏻</i> <i>🤛🏻</i> <i>🤜🏻</i> <i>👏🏻</i> <i>🙌🏻</i> <i>👐🏻</i> <i>🤲🏻</i> <i>🫱🏻</i> <i>🫲🏻</i> <i>🤝🏻</i> <i>🫳🏻</i> <i>🫴🏻</i> <i>🫸🏻</i> <i>🫷🏻</i> <i>🙏🏻</i> <i>🫰🏻</i> <i>🫶🏻</i> <i>✍🏻</i> <i>💅🏻</i> <i>🤳🏻</i> <i>💪🏻</i> <i>🦵🏻</i> <i>🦶🏻</i> <i>👂🏻</i> <i>🦻🏻</i> <i>👃🏻</i> <i>👶🏻</i> <i>🧒🏻</i> <i>👦🏻</i> <i>👧🏻</i> <i>🧑🏻</i> <i>👱🏻</i> <i>👨🏻</i> <i>🧔🏻</i> <i>🧔🏻‍</i> <i>🧔🏻‍</i> <i>👨🏻‍🦰</i> <i>👨🏻‍🦱</i> <i>👨🏻‍🦳</i> <i>👨🏻‍🦲</i> <i>👩🏻</i> <i>👩🏻‍🦰</i> <i>🧑🏻‍🦰</i> <i>👩🏻‍🦱</i> <i>🧑🏻‍🦱</i> <i>👩🏻‍🦳</i> <i>🧑🏻‍🦳</i> <i>👩🏻‍🦲</i> <i>🧑🏻‍🦲</i> <i>👱🏻‍</i> <i>👱🏻‍</i> <i>🧓🏻</i> <i>👴🏻</i> <i>👵🏻</i> <i>🙍🏻</i> <i>🙍🏻‍</i> <i>🙍🏻‍</i> <i>🙎🏻</i> <i>🙎🏻‍</i> <i>🙎🏻‍</i> <i>🙅🏻</i> <i>🙅🏻‍</i> <i>🙅🏻‍</i> <i>🙆🏻</i> <i>🙆🏻‍</i> <i>🙆🏻‍</i> <i>💁🏻</i> <i>💁🏻‍</i> <i>💁🏻‍</i> <i>🙋🏻</i> <i>🙋🏻‍</i> <i>🙋🏻‍</i> <i>🧏🏻</i> <i>🧏🏻‍</i> <i>🧏🏻‍</i> <i>🙇🏻</i> <i>🙇🏻‍</i> <i>🙇🏻‍</i> <i>🤦🏻</i> <i>🤦🏻‍</i> <i>🤦🏻‍</i> <i>🤷🏻</i> <i>🤷🏻‍</i> <i>🤷🏻‍</i> <i>🧑🏻‍⚕️</i> <i>👨🏻‍⚕️</i> <i>👩🏻‍⚕️</i> <i>🧑🏻‍🎓</i> <i>👨🏻‍🎓</i> <i>👩🏻‍🎓</i> <i>🧑🏻‍🏫</i> <i>👨🏻‍🏫</i> <i>👩🏻‍🏫</i> <i>🧑🏻‍⚖️</i> <i>👨🏻‍⚖️</i> <i>👩🏻‍⚖️</i> <i>🧑🏻‍🌾</i> <i>👨🏻‍🌾</i> <i>👩🏻‍🌾</i> <i>🧑🏻‍🍳</i> <i>👨🏻‍🍳</i> <i>👩🏻‍🍳</i> <i>🧑🏻‍🔧</i> <i>👨🏻‍🔧</i> <i>👩🏻‍🔧</i> <i>🧑🏻‍🏭</i> <i>👨🏻‍🏭</i> <i>👩🏻‍🏭</i> <i>🧑🏻‍💼</i> <i>👨🏻‍💼</i> <i>👩🏻‍💼</i> <i>🧑🏻‍🔬</i> <i>👨🏻‍🔬</i> <i>👩🏻‍🔬</i> <i>🧑🏻‍💻</i> <i>👨🏻‍💻</i> <i>👩🏻‍💻</i> <i>🧑🏻‍🎤</i> <i>👨🏻‍🎤</i> <i>👩🏻‍🎤</i> <i>🧑🏻‍🎨</i> <i>👨🏻‍🎨</i> <i>👩🏻‍🎨</i> <i>🧑🏻‍✈️</i> <i>👨🏻‍✈️</i> <i>👩🏻‍✈️</i> <i>🧑🏻‍🚀</i> <i>👨🏻‍🚀</i> <i>👩🏻‍🚀</i> <i>🧑🏻‍🚒</i> <i>👨🏻‍🚒</i> <i>👩🏻‍🚒</i> <i>👮🏻</i> <i>👮🏻‍</i> <i>👮🏻‍</i> <i>🕵🏻</i> <i>🕵🏻‍</i> <i>🕵🏻‍</i> <i>💂🏻</i> <i>💂🏻‍</i> <i>💂🏻‍</i> <i>🥷🏻</i> <i>👷🏻</i> <i>👷🏻‍</i> <i>👷🏻‍</i> <i>🫅🏻</i> <i>🤴🏻</i> <i>👸🏻</i> <i>👳🏻</i> <i>👳🏻‍</i> <i>👳🏻‍</i> <i>👲🏻</i> <i>🧕🏻</i> <i>🤵🏻</i> <i>🤵🏻‍</i> <i>🤵🏻‍</i> <i>👰🏻</i> <i>👰🏻‍</i> <i>👰🏻‍</i> <i>🫄🏻</i> <i>🫃🏻</i> <i>🤰🏻</i> <i>🧑🏻‍🍼</i> <i>👨🏻‍🍼</i> <i>👩🏻‍🍼</i> <i>🤱🏻</i> <i>👼🏻</i> <i>🎅🏻</i> <i>🤶🏻</i> <i>🧑🏻‍🎄</i> <i>🦸🏻</i> <i>🦸🏻‍</i> <i>🦸🏻‍</i> <i>🦹🏻</i> <i>🦹🏻‍</i> <i>🦹🏻‍</i> <i>🧙🏻</i> <i>🧙🏻‍</i> <i>🧙🏻‍</i> <i>🧚🏻</i> <i>🧚🏻‍</i> <i>🧚🏻‍</i> <i>🧛🏻</i> <i>🧛🏻‍</i> <i>🧛🏻‍</i> <i>🧜🏻</i> <i>🧜🏻‍</i> <i>🧜🏻‍</i> <i>🧝🏻</i> <i>🧝🏻‍</i> <i>🧝🏻‍</i> <i>💆🏻</i> <i>💆🏻‍</i> <i>💆🏻‍</i> <i>💇🏻</i> <i>💇🏻‍</i> <i>💇🏻‍</i> <i>🚶🏻</i> <i>🚶🏻‍</i> <i>🚶🏻‍</i> <i>🧍🏻</i> <i>🧍🏻‍</i> <i>🧍🏻‍</i> <i>🧎🏻</i> <i>🧎🏻‍</i> <i>🧎🏻‍</i> <i>🧑🏻‍🦯</i> <i>👨🏻‍🦯</i> <i>👩🏻‍🦯</i> <i>🧑🏻‍🦼</i> <i>👨🏻‍🦼</i> <i>👩🏻‍🦼</i> <i>🧑🏻‍🦽</i> <i>👨🏻‍🦽</i> <i>👩🏻‍🦽</i> <i>🏃🏻</i> <i>🏃🏻‍</i> <i>🏃🏻‍</i> <i>🚶🏻‍➡️</i> <i>🚶🏻‍‍➡️</i> <i>🚶🏻‍‍➡️</i> <i>🧎🏻‍➡️</i> <i>🧎🏻‍‍➡️</i> <i>🧎🏻‍‍➡️</i> <i>🧑🏻‍🦯‍➡️</i> <i>👨🏻‍🦯‍➡️</i> <i>👩🏻‍🦯‍➡️</i> <i>🧑🏻‍🦼‍➡️</i> <i>👨🏻‍🦼‍➡️</i> <i>👩🏻‍🦼‍➡️</i> <i>🧑🏻‍🦽‍➡️</i> <i>👨🏻‍🦽‍➡️</i> <i>👩🏻‍🦽‍➡️</i> <i>🏃🏻‍➡️</i> <i>🏃🏻‍‍➡️</i> <i>🏃🏻‍‍➡️</i> <i>💃🏻</i> <i>🕺🏻</i> <i>🕴🏻</i> <i>🧖🏻</i> <i>🧖🏻‍</i> <i>🧖🏻‍</i> <i>🧗🏻</i> <i>🧗🏻‍</i> <i>🧗🏻‍</i> <i>🏇🏻</i> <i>🏂🏻</i> <i>🏌🏻</i> <i>🏌🏻‍</i> <i>🏌🏻‍</i> <i>🏄🏻</i> <i>🏄🏻‍</i> <i>🏄🏻‍</i> <i>🚣🏻</i> <i>🚣🏻‍</i> <i>🚣🏻‍</i> <i>🏊🏻</i> <i>🏊🏻‍</i> <i>🏊🏻‍</i> <i>⛹🏻</i> <i>⛹🏻‍</i> <i>⛹🏻‍</i> <i>🏋🏻</i> <i>🏋🏻‍</i> <i>🏋🏻‍</i> <i>🚴🏻</i> <i>🚴🏻‍</i> <i>🚴🏻‍</i> <i>🚵🏻</i> <i>🚵🏻‍</i> <i>🚵🏻‍</i> <i>🤸🏻</i> <i>🤸🏻‍</i> <i>🤸🏻‍</i> <i>🤽🏻</i> <i>🤽🏻‍</i> <i>🤽🏻‍</i> <i>🤾🏻</i> <i>🤾🏻‍</i> <i>🤾🏻‍</i> <i>🤹🏻</i> <i>🤹🏻‍</i> <i>🤹🏻‍</i> <i>🧘🏻</i> <i>🧘🏻‍</i> <i>🧘🏻‍</i> <i>🛀🏻</i> <i>🛌🏻</i> <i>💑🏻</i> <i>💏🏻</i> <i>👫🏻</i> <i>👭🏻</i> <i>👬🏻</i><br>'+
				'<i>👋🏼</i> <i>🤚🏼</i> <i>🖐🏼</i> <i>✋🏼</i> <i>🖖🏼</i> <i>👌🏼</i> <i>🤌🏼</i> <i>🤏🏼</i> <i>✌🏼</i> <i>🤞🏼</i> <i>🤟🏼</i> <i>🤘🏼</i> <i>🤙🏼</i> <i>👈🏼</i> <i>👉🏼</i> <i>👆🏼</i> <i>🖕🏼</i> <i>👇🏼</i> <i>☝🏼</i> <i>🫵🏼</i> <i>👍🏼</i> <i>👎🏼</i> <i>✊🏼</i> <i>👊🏼</i> <i>🤛🏼</i> <i>🤜🏼</i> <i>👏🏼</i> <i>🙌🏼</i> <i>👐🏼</i> <i>🤲🏼</i> <i>🫱🏼</i> <i>🫲🏼</i> <i>🤝🏼</i> <i>🫳🏼</i> <i>🫴🏼</i> <i>🫸🏼</i> <i>🫷🏼</i> <i>🙏🏼</i> <i>🫰🏼</i> <i>🫶🏼</i> <i>✍🏼</i> <i>💅🏼</i> <i>🤳🏼</i> <i>💪🏼</i> <i>🦵🏼</i> <i>🦶🏼</i> <i>👂🏼</i> <i>🦻🏼</i> <i>👃🏼</i> <i>👶🏼</i> <i>🧒🏼</i> <i>👦🏼</i> <i>👧🏼</i> <i>🧑🏼</i> <i>👱🏼</i> <i>👨🏼</i> <i>🧔🏼</i> <i>🧔🏼‍</i> <i>🧔🏼‍</i> <i>👨🏼‍🦰</i> <i>👨🏼‍🦱</i> <i>👨🏼‍🦳</i> <i>👨🏼‍🦲</i> <i>👩🏼</i> <i>👩🏼‍🦰</i> <i>🧑🏼‍🦰</i> <i>👩🏼‍🦱</i> <i>🧑🏼‍🦱</i> <i>👩🏼‍🦳</i> <i>🧑🏼‍🦳</i> <i>👩🏼‍🦲</i> <i>🧑🏼‍🦲</i> <i>👱🏼‍</i> <i>👱🏼‍</i> <i>🧓🏼</i> <i>👴🏼</i> <i>👵🏼</i> <i>🙍🏼</i> <i>🙍🏼‍</i> <i>🙍🏼‍</i> <i>🙎🏼</i> <i>🙎🏼‍</i> <i>🙎🏼‍</i> <i>🙅🏼</i> <i>🙅🏼‍</i> <i>🙅🏼‍</i> <i>🙆🏼</i> <i>🙆🏼‍</i> <i>🙆🏼‍</i> <i>💁🏼</i> <i>💁🏼‍</i> <i>💁🏼‍</i> <i>🙋🏼</i> <i>🙋🏼‍</i> <i>🙋🏼‍</i> <i>🧏🏼</i> <i>🧏🏼‍</i> <i>🧏🏼‍</i> <i>🙇🏼</i> <i>🙇🏼‍</i> <i>🙇🏼‍</i> <i>🤦🏼</i> <i>🤦🏼‍</i> <i>🤦🏼‍</i> <i>🤷🏼</i> <i>🤷🏼‍</i> <i>🤷🏼‍</i> <i>🧑🏼‍⚕️</i> <i>👨🏼‍⚕️</i> <i>👩🏼‍⚕️</i> <i>🧑🏼‍🎓</i> <i>👨🏼‍🎓</i> <i>👩🏼‍🎓</i> <i>🧑🏼‍🏫</i> <i>👨🏼‍🏫</i> <i>👩🏼‍🏫</i> <i>🧑🏼‍⚖️</i> <i>👨🏼‍⚖️</i> <i>👩🏼‍⚖️</i> <i>🧑🏼‍🌾</i> <i>👨🏼‍🌾</i> <i>👩🏼‍🌾</i> <i>🧑🏼‍🍳</i> <i>👨🏼‍🍳</i> <i>👩🏼‍🍳</i> <i>🧑🏼‍🔧</i> <i>👨🏼‍🔧</i> <i>👩🏼‍🔧</i> <i>🧑🏼‍🏭</i> <i>👨🏼‍🏭</i> <i>👩🏼‍🏭</i> <i>🧑🏼‍💼</i> <i>👨🏼‍💼</i> <i>👩🏼‍💼</i> <i>🧑🏼‍🔬</i> <i>👨🏼‍🔬</i> <i>👩🏼‍🔬</i> <i>🧑🏼‍💻</i> <i>👨🏼‍💻</i> <i>👩🏼‍💻</i> <i>🧑🏼‍🎤</i> <i>👨🏼‍🎤</i> <i>👩🏼‍🎤</i> <i>🧑🏼‍🎨</i> <i>👨🏼‍🎨</i> <i>👩🏼‍🎨</i> <i>🧑🏼‍✈️</i> <i>👨🏼‍✈️</i> <i>👩🏼‍✈️</i> <i>🧑🏼‍🚀</i> <i>👨🏼‍🚀</i> <i>👩🏼‍🚀</i> <i>🧑🏼‍🚒</i> <i>👨🏼‍🚒</i> <i>👩🏼‍🚒</i> <i>👮🏼</i> <i>👮🏼‍</i> <i>👮🏼‍</i> <i>🕵🏼</i> <i>🕵🏼‍</i> <i>🕵🏼‍</i> <i>💂🏼</i> <i>💂🏼‍</i> <i>💂🏼‍</i> <i>🥷🏼</i> <i>👷🏼</i> <i>👷🏼‍</i> <i>👷🏼‍</i> <i>🫅🏼</i> <i>🤴🏼</i> <i>👸🏼</i> <i>👳🏼</i> <i>👳🏼‍</i> <i>👳🏼‍</i> <i>👲🏼</i> <i>🧕🏼</i> <i>🤵🏼</i> <i>🤵🏼‍</i> <i>🤵🏼‍</i> <i>👰🏼</i> <i>👰🏼‍</i> <i>👰🏼‍</i> <i>🫄🏼</i> <i>🫃🏼</i> <i>🤰🏼</i> <i>🧑🏼‍🍼</i> <i>👨🏼‍🍼</i> <i>👩🏼‍🍼</i> <i>🤱🏼</i> <i>👼🏼</i> <i>🎅🏼</i> <i>🤶🏼</i> <i>🧑🏼‍🎄</i> <i>🦸🏼</i> <i>🦸🏼‍</i> <i>🦸🏼‍</i> <i>🦹🏼</i> <i>🦹🏼‍</i> <i>🦹🏼‍</i> <i>🧙🏼</i> <i>🧙🏼‍</i> <i>🧙🏼‍</i> <i>🧚🏼</i> <i>🧚🏼‍</i> <i>🧚🏼‍</i> <i>🧛🏼</i> <i>🧛🏼‍</i> <i>🧛🏼‍</i> <i>🧜🏼</i> <i>🧜🏼‍</i> <i>🧜🏼‍</i> <i>🧝🏼</i> <i>🧝🏼‍</i> <i>🧝🏼‍</i> <i>💆🏼</i> <i>💆🏼‍</i> <i>💆🏼‍</i> <i>💇🏼</i> <i>💇🏼‍</i> <i>💇🏼‍</i> <i>🚶🏼</i> <i>🚶🏼‍</i> <i>🚶🏼‍</i> <i>🧍🏼</i> <i>🧍🏼‍</i> <i>🧍🏼‍</i> <i>🧎🏼</i> <i>🧎🏼‍</i> <i>🧎🏼‍</i> <i>🧑🏼‍🦯</i> <i>👨🏼‍🦯</i> <i>👩🏼‍🦯</i> <i>🧑🏼‍🦼</i> <i>👨🏼‍🦼</i> <i>👩🏼‍🦼</i> <i>🧑🏼‍🦽</i> <i>👨🏼‍🦽</i> <i>👩🏼‍🦽</i> <i>🏃🏼</i> <i>🏃🏼‍</i> <i>🏃🏼‍</i> <i>🚶🏼‍➡️</i> <i>🚶🏼‍‍➡️</i> <i>🚶🏼‍‍➡️</i> <i>🧎🏼‍➡️</i> <i>🧎🏼‍‍➡️</i> <i>🧎🏼‍‍➡️</i> <i>🧑🏼‍🦯‍➡️</i> <i>👨🏼‍🦯‍➡️</i> <i>👩🏼‍🦯‍➡️</i> <i>🧑🏼‍🦼‍➡️</i> <i>👨🏼‍🦼‍➡️</i> <i>👩🏼‍🦼‍➡️</i> <i>🧑🏼‍🦽‍➡️</i> <i>👨🏼‍🦽‍➡️</i> <i>👩🏼‍🦽‍➡️</i> <i>🏃🏼‍➡️</i> <i>🏃🏼‍‍➡️</i> <i>🏃🏼‍‍➡️</i> <i>💃🏼</i> <i>🕺🏼</i> <i>🕴🏼</i> <i>🧖🏼</i> <i>🧖🏼‍</i> <i>🧖🏼‍</i> <i>🧗🏼</i> <i>🧗🏼‍</i> <i>🧗🏼‍</i> <i>🏇🏼</i> <i>🏂🏼</i> <i>🏌🏼</i> <i>🏌🏼‍</i> <i>🏌🏼‍</i> <i>🏄🏼</i> <i>🏄🏼‍</i> <i>🏄🏼‍</i> <i>🚣🏼</i> <i>🚣🏼‍</i> <i>🚣🏼‍</i> <i>🏊🏼</i> <i>🏊🏼‍</i> <i>🏊🏼‍</i> <i>⛹🏼</i> <i>⛹🏼‍</i> <i>⛹🏼‍</i> <i>🏋🏼</i> <i>🏋🏼‍</i> <i>🏋🏼‍</i> <i>🚴🏼</i> <i>🚴🏼‍</i> <i>🚴🏼‍</i> <i>🚵🏼</i> <i>🚵🏼‍</i> <i>🚵🏼‍</i> <i>🤸🏼</i> <i>🤸🏼‍</i> <i>🤸🏼‍</i> <i>🤽🏼</i> <i>🤽🏼‍</i> <i>🤽🏼‍</i> <i>🤾🏼</i> <i>🤾🏼‍</i> <i>🤾🏼‍</i> <i>🤹🏼</i> <i>🤹🏼‍</i> <i>🤹🏼‍</i> <i>🧘🏼</i> <i>🧘🏼‍</i> <i>🧘🏼‍</i> <i>🛀🏼</i> <i>🛌🏼</i> <i>💑🏼</i> <i>💏🏼</i> <i>👫🏼</i> <i>👭🏼</i> <i>👬🏼</i><br>'+
				'<i>👋🏽</i> <i>🤚🏽</i> <i>🖐🏽</i> <i>✋🏽</i> <i>🖖🏽</i> <i>👌🏽</i> <i>🤌🏽</i> <i>🤏🏽</i> <i>✌🏽</i> <i>🤞🏽</i> <i>🤟🏽</i> <i>🤘🏽</i> <i>🤙🏽</i> <i>👈🏽</i> <i>👉🏽</i> <i>👆🏽</i> <i>🖕🏽</i> <i>👇🏽</i> <i>☝🏽</i> <i>🫵🏽</i> <i>👍🏽</i> <i>👎🏽</i> <i>✊🏽</i> <i>👊🏽</i> <i>🤛🏽</i> <i>🤜🏽</i> <i>👏🏽</i> <i>🙌🏽</i> <i>👐🏽</i> <i>🤲🏽</i> <i>🫱🏽</i> <i>🫲🏽</i> <i>🤝🏽</i> <i>🫳🏽</i> <i>🫴🏽</i> <i>🫸🏽</i> <i>🫷🏽</i> <i>🙏🏽</i> <i>🫰🏽</i> <i>🫶🏽</i> <i>✍🏽</i> <i>💅🏽</i> <i>🤳🏽</i> <i>💪🏽</i> <i>🦵🏽</i> <i>🦶🏽</i> <i>👂🏽</i> <i>🦻🏽</i> <i>👃🏽</i> <i>👶🏽</i> <i>🧒🏽</i> <i>👦🏽</i> <i>👧🏽</i> <i>🧑🏽</i> <i>👱🏽</i> <i>👨🏽</i> <i>🧔🏽</i> <i>🧔🏽‍</i> <i>🧔🏽‍</i> <i>👨🏽‍🦰</i> <i>👨🏽‍🦱</i> <i>👨🏽‍🦳</i> <i>👨🏽‍🦲</i> <i>👩🏽</i> <i>👩🏽‍🦰</i> <i>🧑🏽‍🦰</i> <i>👩🏽‍🦱</i> <i>🧑🏽‍🦱</i> <i>👩🏽‍🦳</i> <i>🧑🏽‍🦳</i> <i>👩🏽‍🦲</i> <i>🧑🏽‍🦲</i> <i>👱🏽‍</i> <i>👱🏽‍</i> <i>🧓🏽</i> <i>👴🏽</i> <i>👵🏽</i> <i>🙍🏽</i> <i>🙍🏽‍</i> <i>🙍🏽‍</i> <i>🙎🏽</i> <i>🙎🏽‍</i> <i>🙎🏽‍</i> <i>🙅🏽</i> <i>🙅🏽‍</i> <i>🙅🏽‍</i> <i>🙆🏽</i> <i>🙆🏽‍</i> <i>🙆🏽‍</i> <i>💁🏽</i> <i>💁🏽‍</i> <i>💁🏽‍</i> <i>🙋🏽</i> <i>🙋🏽‍</i> <i>🙋🏽‍</i> <i>🧏🏽</i> <i>🧏🏽‍</i> <i>🧏🏽‍</i> <i>🙇🏽</i> <i>🙇🏽‍</i> <i>🙇🏽‍</i> <i>🤦🏽</i> <i>🤦🏽‍</i> <i>🤦🏽‍</i> <i>🤷🏽</i> <i>🤷🏽‍</i> <i>🤷🏽‍</i> <i>🧑🏽‍⚕️</i> <i>👨🏽‍⚕️</i> <i>👩🏽‍⚕️</i> <i>🧑🏽‍🎓</i> <i>👨🏽‍🎓</i> <i>👩🏽‍🎓</i> <i>🧑🏽‍🏫</i> <i>👨🏽‍🏫</i> <i>👩🏽‍🏫</i> <i>🧑🏽‍⚖️</i> <i>👨🏽‍⚖️</i> <i>👩🏽‍⚖️</i> <i>🧑🏽‍🌾</i> <i>👨🏽‍🌾</i> <i>👩🏽‍🌾</i> <i>🧑🏽‍🍳</i> <i>👨🏽‍🍳</i> <i>👩🏽‍🍳</i> <i>🧑🏽‍🔧</i> <i>👨🏽‍🔧</i> <i>👩🏽‍🔧</i> <i>🧑🏽‍🏭</i> <i>👨🏽‍🏭</i> <i>👩🏽‍🏭</i> <i>🧑🏽‍💼</i> <i>👨🏽‍💼</i> <i>👩🏽‍💼</i> <i>🧑🏽‍🔬</i> <i>👨🏽‍🔬</i> <i>👩🏽‍🔬</i> <i>🧑🏽‍💻</i> <i>👨🏽‍💻</i> <i>👩🏽‍💻</i> <i>🧑🏽‍🎤</i> <i>👨🏽‍🎤</i> <i>👩🏽‍🎤</i> <i>🧑🏽‍🎨</i> <i>👨🏽‍🎨</i> <i>👩🏽‍🎨</i> <i>🧑🏽‍✈️</i> <i>👨🏽‍✈️</i> <i>👩🏽‍✈️</i> <i>🧑🏽‍🚀</i> <i>👨🏽‍🚀</i> <i>👩🏽‍🚀</i> <i>🧑🏽‍🚒</i> <i>👨🏽‍🚒</i> <i>👩🏽‍🚒</i> <i>👮🏽</i> <i>👮🏽‍</i> <i>👮🏽‍</i> <i>🕵🏽</i> <i>🕵🏽‍</i> <i>🕵🏽‍</i> <i>💂🏽</i> <i>💂🏽‍</i> <i>💂🏽‍</i> <i>🥷🏽</i> <i>👷🏽</i> <i>👷🏽‍</i> <i>👷🏽‍</i> <i>🫅🏽</i> <i>🤴🏽</i> <i>👸🏽</i> <i>👳🏽</i> <i>👳🏽‍</i> <i>👳🏽‍</i> <i>👲🏽</i> <i>🧕🏽</i> <i>🤵🏽</i> <i>🤵🏽‍</i> <i>🤵🏽‍</i> <i>👰🏽</i> <i>👰🏽‍</i> <i>👰🏽‍</i> <i>🫄🏽</i> <i>🫃🏽</i> <i>🤰🏽</i> <i>🧑🏽‍🍼</i> <i>👨🏽‍🍼</i> <i>👩🏽‍🍼</i> <i>🤱🏽</i> <i>👼🏽</i> <i>🎅🏽</i> <i>🤶🏽</i> <i>🧑🏽‍🎄</i> <i>🦸🏽</i> <i>🦸🏽‍</i> <i>🦸🏽‍</i> <i>🦹🏽</i> <i>🦹🏽‍</i> <i>🦹🏽‍</i> <i>🧙🏽</i> <i>🧙🏽‍</i> <i>🧙🏽‍</i> <i>🧚🏽</i> <i>🧚🏽‍</i> <i>🧚🏽‍</i> <i>🧛🏽</i> <i>🧛🏽‍</i> <i>🧛🏽‍</i> <i>🧜🏽</i> <i>🧜🏽‍</i> <i>🧜🏽‍</i> <i>🧝🏽</i> <i>🧝🏽‍</i> <i>🧝🏽‍</i> <i>💆🏽</i> <i>💆🏽‍</i> <i>💆🏽‍</i> <i>💇🏽</i> <i>💇🏽‍</i> <i>💇🏽‍</i> <i>🚶🏽</i> <i>🚶🏽‍</i> <i>🚶🏽‍</i> <i>🧍🏽</i> <i>🧍🏽‍</i> <i>🧍🏽‍</i> <i>🧎🏽</i> <i>🧎🏽‍</i> <i>🧎🏽‍</i> <i>🧑🏽‍🦯</i> <i>👨🏽‍🦯</i> <i>👩🏽‍🦯</i> <i>🧑🏽‍🦼</i> <i>👨🏽‍🦼</i> <i>👩🏽‍🦼</i> <i>🧑🏽‍🦽</i> <i>👨🏽‍🦽</i> <i>👩🏽‍🦽</i> <i>🏃🏽</i> <i>🏃🏽‍</i> <i>🏃🏽‍</i> <i>🚶🏽‍➡️</i> <i>🚶🏽‍‍➡️</i> <i>🚶🏽‍‍➡️</i> <i>🧎🏽‍➡️</i> <i>🧎🏽‍‍➡️</i> <i>🧎🏽‍‍➡️</i> <i>🧑🏽‍🦯‍➡️</i> <i>👨🏽‍🦯‍➡️</i> <i>👩🏽‍🦯‍➡️</i> <i>🧑🏽‍🦼‍➡️</i> <i>👨🏽‍🦼‍➡️</i> <i>👩🏽‍🦼‍➡️</i> <i>🧑🏽‍🦽‍➡️</i> <i>👨🏽‍🦽‍➡️</i> <i>👩🏽‍🦽‍➡️</i> <i>🏃🏽‍➡️</i> <i>🏃🏽‍‍➡️</i> <i>🏃🏽‍‍➡️</i> <i>💃🏽</i> <i>🕺🏽</i> <i>🕴🏽</i> <i>🧖🏽</i> <i>🧖🏽‍</i> <i>🧖🏽‍</i> <i>🧗🏽</i> <i>🧗🏽‍</i> <i>🧗🏽‍</i> <i>🏇🏽</i> <i>🏂🏽</i> <i>🏌🏽</i> <i>🏌🏽‍</i> <i>🏌🏽‍</i> <i>🏄🏽</i> <i>🏄🏽‍</i> <i>🏄🏽‍</i> <i>🚣🏽</i> <i>🚣🏽‍</i> <i>🚣🏽‍</i> <i>🏊🏽</i> <i>🏊🏽‍</i> <i>🏊🏽‍</i> <i>⛹🏽</i> <i>⛹🏽‍</i> <i>⛹🏽‍</i> <i>🏋🏽</i> <i>🏋🏽‍</i> <i>🏋🏽‍</i> <i>🚴🏽</i> <i>🚴🏽‍</i> <i>🚴🏽‍</i> <i>🚵🏽</i> <i>🚵🏽‍</i> <i>🚵🏽‍</i> <i>🤸🏽</i> <i>🤸🏽‍</i> <i>🤸🏽‍</i> <i>🤽🏽</i> <i>🤽🏽‍</i> <i>🤽🏽‍</i> <i>🤾🏽</i> <i>🤾🏽‍</i> <i>🤾🏽‍</i> <i>🤹🏽</i> <i>🤹🏽‍</i> <i>🤹🏽‍</i> <i>🧘🏽</i> <i>🧘🏽‍</i> <i>🧘🏽‍</i> <i>🛀🏽</i> <i>🛌🏽</i> <i>💑🏽</i> <i>💏🏽</i> <i>👫🏽</i> <i>👭🏽</i> <i>👬🏽</i><br>'+
				'<i>👋🏾</i> <i>🤚🏾</i> <i>🖐🏾</i> <i>✋🏾</i> <i>🖖🏾</i> <i>👌🏾</i> <i>🤌🏾</i> <i>🤏🏾</i> <i>✌🏾</i> <i>🤞🏾</i> <i>🤟🏾</i> <i>🤘🏾</i> <i>🤙🏾</i> <i>👈🏾</i> <i>👉🏾</i> <i>👆🏾</i> <i>🖕🏾</i> <i>👇🏾</i> <i>☝🏾</i> <i>🫵🏾</i> <i>👍🏾</i> <i>👎🏾</i> <i>✊🏾</i> <i>👊🏾</i> <i>🤛🏾</i> <i>🤜🏾</i> <i>👏🏾</i> <i>🙌🏾</i> <i>👐🏾</i> <i>🤲🏾</i> <i>🫱🏾</i> <i>🫲🏾</i> <i>🤝🏾</i> <i>🫳🏾</i> <i>🫴🏾</i> <i>🫸🏾</i> <i>🫷🏾</i> <i>🙏🏾</i> <i>🫰🏾</i> <i>🫶🏾</i> <i>✍🏾</i> <i>💅🏾</i> <i>🤳🏾</i> <i>💪🏾</i> <i>🦵🏾</i> <i>🦶🏾</i> <i>👂🏾</i> <i>🦻🏾</i> <i>👃🏾</i> <i>👶🏾</i> <i>🧒🏾</i> <i>👦🏾</i> <i>👧🏾</i> <i>🧑🏾</i> <i>👱🏾</i> <i>👨🏾</i> <i>🧔🏾</i> <i>🧔🏾‍</i> <i>🧔🏾‍</i> <i>👨🏾‍🦰</i> <i>👨🏾‍🦱</i> <i>👨🏾‍🦳</i> <i>👨🏾‍🦲</i> <i>👩🏾</i> <i>👩🏾‍🦰</i> <i>🧑🏾‍🦰</i> <i>👩🏾‍🦱</i> <i>🧑🏾‍🦱</i> <i>👩🏾‍🦳</i> <i>🧑🏾‍🦳</i> <i>👩🏾‍🦲</i> <i>🧑🏾‍🦲</i> <i>👱🏾‍</i> <i>👱🏾‍</i> <i>🧓🏾</i> <i>👴🏾</i> <i>👵🏾</i> <i>🙍🏾</i> <i>🙍🏾‍</i> <i>🙍🏾‍</i> <i>🙎🏾</i> <i>🙎🏾‍</i> <i>🙎🏾‍</i> <i>🙅🏾</i> <i>🙅🏾‍</i> <i>🙅🏾‍</i> <i>🙆🏾</i> <i>🙆🏾‍</i> <i>🙆🏾‍</i> <i>💁🏾</i> <i>💁🏾‍</i> <i>💁🏾‍</i> <i>🙋🏾</i> <i>🙋🏾‍</i> <i>🙋🏾‍</i> <i>🧏🏾</i> <i>🧏🏾‍</i> <i>🧏🏾‍</i> <i>🙇🏾</i> <i>🙇🏾‍</i> <i>🙇🏾‍</i> <i>🤦🏾</i> <i>🤦🏾‍</i> <i>🤦🏾‍</i> <i>🤷🏾</i> <i>🤷🏾‍</i> <i>🤷🏾‍</i> <i>🧑🏾‍⚕️</i> <i>👨🏾‍⚕️</i> <i>👩🏾‍⚕️</i> <i>🧑🏾‍🎓</i> <i>👨🏾‍🎓</i> <i>👩🏾‍🎓</i> <i>🧑🏾‍🏫</i> <i>👨🏾‍🏫</i> <i>👩🏾‍🏫</i> <i>🧑🏾‍⚖️</i> <i>👨🏾‍⚖️</i> <i>👩🏾‍⚖️</i> <i>🧑🏾‍🌾</i> <i>👨🏾‍🌾</i> <i>👩🏾‍🌾</i> <i>🧑🏾‍🍳</i> <i>👨🏾‍🍳</i> <i>👩🏾‍🍳</i> <i>🧑🏾‍🔧</i> <i>👨🏾‍🔧</i> <i>👩🏾‍🔧</i> <i>🧑🏾‍🏭</i> <i>👨🏾‍🏭</i> <i>👩🏾‍🏭</i> <i>🧑🏾‍💼</i> <i>👨🏾‍💼</i> <i>👩🏾‍💼</i> <i>🧑🏾‍🔬</i> <i>👨🏾‍🔬</i> <i>👩🏾‍🔬</i> <i>🧑🏾‍💻</i> <i>👨🏾‍💻</i> <i>👩🏾‍💻</i> <i>🧑🏾‍🎤</i> <i>👨🏾‍🎤</i> <i>👩🏾‍🎤</i> <i>🧑🏾‍🎨</i> <i>👨🏾‍🎨</i> <i>👩🏾‍🎨</i> <i>🧑🏾‍✈️</i> <i>👨🏾‍✈️</i> <i>👩🏾‍✈️</i> <i>🧑🏾‍🚀</i> <i>👨🏾‍🚀</i> <i>👩🏾‍🚀</i> <i>🧑🏾‍🚒</i> <i>👨🏾‍🚒</i> <i>👩🏾‍🚒</i> <i>👮🏾</i> <i>👮🏾‍</i> <i>👮🏾‍</i> <i>🕵🏾</i> <i>🕵🏾‍</i> <i>🕵🏾‍</i> <i>💂🏾</i> <i>💂🏾‍</i> <i>💂🏾‍</i> <i>🥷🏾</i> <i>👷🏾</i> <i>👷🏾‍</i> <i>👷🏾‍</i> <i>🫅🏾</i> <i>🤴🏾</i> <i>👸🏾</i> <i>👳🏾</i> <i>👳🏾‍</i> <i>👳🏾‍</i> <i>👲🏾</i> <i>🧕🏾</i> <i>🤵🏾</i> <i>🤵🏾‍</i> <i>🤵🏾‍</i> <i>👰🏾</i> <i>👰🏾‍</i> <i>👰🏾‍</i> <i>🫄🏾</i> <i>🫃🏾</i> <i>🤰🏾</i> <i>🧑🏾‍🍼</i> <i>👨🏾‍🍼</i> <i>👩🏾‍🍼</i> <i>🤱🏾</i> <i>👼🏾</i> <i>🎅🏾</i> <i>🤶🏾</i> <i>🧑🏾‍🎄</i> <i>🦸🏾</i> <i>🦸🏾‍</i> <i>🦸🏾‍</i> <i>🦹🏾</i> <i>🦹🏾‍</i> <i>🦹🏾‍</i> <i>🧙🏾</i> <i>🧙🏾‍</i> <i>🧙🏾‍</i> <i>🧚🏾</i> <i>🧚🏾‍</i> <i>🧚🏾‍</i> <i>🧛🏾</i> <i>🧛🏾‍</i> <i>🧛🏾‍</i> <i>🧜🏾</i> <i>🧜🏾‍</i> <i>🧜🏾‍</i> <i>🧝🏾</i> <i>🧝🏾‍</i> <i>🧝🏾‍</i> <i>💆🏾</i> <i>💆🏾‍</i> <i>💆🏾‍</i> <i>💇🏾</i> <i>💇🏾‍</i> <i>💇🏾‍</i> <i>🚶🏾</i> <i>🚶🏾‍</i> <i>🚶🏾‍</i> <i>🧍🏾</i> <i>🧍🏾‍</i> <i>🧍🏾‍</i> <i>🧎🏾</i> <i>🧎🏾‍</i> <i>🧎🏾‍</i> <i>🧑🏾‍🦯</i> <i>👨🏾‍🦯</i> <i>👩🏾‍🦯</i> <i>🧑🏾‍🦼</i> <i>👨🏾‍🦼</i> <i>👩🏾‍🦼</i> <i>🧑🏾‍🦽</i> <i>👨🏾‍🦽</i> <i>👩🏾‍🦽</i> <i>🏃🏾</i> <i>🏃🏾‍</i> <i>🏃🏾‍</i> <i>🚶🏾‍➡️</i> <i>🚶🏾‍‍➡️</i> <i>🚶🏾‍‍➡️</i> <i>🧎🏾‍➡️</i> <i>🧎🏾‍‍➡️</i> <i>🧎🏾‍‍➡️</i> <i>🧑🏾‍🦯‍➡️</i> <i>👨🏾‍🦯‍➡️</i> <i>👩🏾‍🦯‍➡️</i> <i>🧑🏾‍🦼‍➡️</i> <i>👨🏾‍🦼‍➡️</i> <i>👩🏾‍🦼‍➡️</i> <i>🧑🏾‍🦽‍➡️</i> <i>👨🏾‍🦽‍➡️</i> <i>👩🏾‍🦽‍➡️</i> <i>🏃🏾‍➡️</i> <i>🏃🏾‍‍➡️</i> <i>🏃🏾‍‍➡️</i> <i>💃🏾</i> <i>🕺🏾</i> <i>🕴🏾</i> <i>🧖🏾</i> <i>🧖🏾‍</i> <i>🧖🏾‍</i> <i>🧗🏾</i> <i>🧗🏾‍</i> <i>🧗🏾‍</i> <i>🏇🏾</i> <i>🏂🏾</i> <i>🏌🏾</i> <i>🏌🏾‍</i> <i>🏌🏾‍</i> <i>🏄🏾</i> <i>🏄🏾‍</i> <i>🏄🏾‍</i> <i>🚣🏾</i> <i>🚣🏾‍</i> <i>🚣🏾‍</i> <i>🏊🏾</i> <i>🏊🏾‍</i> <i>🏊🏾‍</i> <i>⛹🏾</i> <i>⛹🏾‍</i> <i>⛹🏾‍</i> <i>🏋🏾</i> <i>🏋🏾‍</i> <i>🏋🏾‍</i> <i>🚴🏾</i> <i>🚴🏾‍</i> <i>🚴🏾‍</i> <i>🚵🏾</i> <i>🚵🏾‍</i> <i>🚵🏾‍</i> <i>🤸🏾</i> <i>🤸🏾‍</i> <i>🤸🏾‍</i> <i>🤽🏾</i> <i>🤽🏾‍</i> <i>🤽🏾‍</i> <i>🤾🏾</i> <i>🤾🏾‍</i> <i>🤾🏾‍</i> <i>🤹🏾</i> <i>🤹🏾‍</i> <i>🤹🏾‍</i> <i>🧘🏾</i> <i>🧘🏾‍</i> <i>🧘🏾‍</i> <i>🛀🏾</i> <i>🛌🏾</i> <i>💑🏾</i> <i>💏🏾</i> <i>👫🏾</i> <i>👭🏾</i> <i>👬🏾</i><br>'+
				'<i>👋🏿</i> <i>🤚🏿</i> <i>🖐🏿</i> <i>✋🏿</i> <i>🖖🏿</i> <i>👌🏿</i> <i>🤌🏿</i> <i>🤏🏿</i> <i>✌🏿</i> <i>🤞🏿</i> <i>🤟🏿</i> <i>🤘🏿</i> <i>🤙🏿</i> <i>👈🏿</i> <i>👉🏿</i> <i>👆🏿</i> <i>🖕🏿</i> <i>👇🏿</i> <i>☝🏿</i> <i>🫵🏿</i> <i>👍🏿</i> <i>👎🏿</i> <i>✊🏿</i> <i>👊🏿</i> <i>🤛🏿</i> <i>🤜🏿</i> <i>👏🏿</i> <i>🙌🏿</i> <i>👐🏿</i> <i>🤲🏿</i> <i>🫱🏿</i> <i>🫲🏿</i> <i>🤝🏿</i> <i>🫳🏿</i> <i>🫴🏿</i> <i>🫸🏿</i> <i>🫷🏿</i> <i>🙏🏿</i> <i>🫰🏿</i> <i>🫶🏿</i> <i>✍🏿</i> <i>💅🏿</i> <i>🤳🏿</i> <i>💪🏿</i> <i>🦵🏿</i> <i>🦶🏿</i> <i>👂🏿</i> <i>🦻🏿</i> <i>👃🏿</i> <i>👶🏿</i> <i>🧒🏿</i> <i>👦🏿</i> <i>👧🏿</i> <i>🧑🏿</i> <i>👱🏿</i> <i>👨🏿</i> <i>🧔🏿</i> <i>🧔🏿‍</i> <i>🧔🏿‍</i> <i>👨🏿‍🦰</i> <i>👨🏿‍🦱</i> <i>👨🏿‍🦳</i> <i>👨🏿‍🦲</i> <i>👩🏿</i> <i>👩🏿‍🦰</i> <i>🧑🏿‍🦰</i> <i>👩🏿‍🦱</i> <i>🧑🏿‍🦱</i> <i>👩🏿‍🦳</i> <i>🧑🏿‍🦳</i> <i>👩🏿‍🦲</i> <i>🧑🏿‍🦲</i> <i>👱🏿‍</i> <i>👱🏿‍</i> <i>🧓🏿</i> <i>👴🏿</i> <i>👵🏿</i> <i>🙍🏿</i> <i>🙍🏿‍</i> <i>🙍🏿‍</i> <i>🙎🏿</i> <i>🙎🏿‍</i> <i>🙎🏿‍</i> <i>🙅🏿</i> <i>🙅🏿‍</i> <i>🙅🏿‍</i> <i>🙆🏿</i> <i>🙆🏿‍</i> <i>🙆🏿‍</i> <i>💁🏿</i> <i>💁🏿‍</i> <i>💁🏿‍</i> <i>🙋🏿</i> <i>🙋🏿‍</i> <i>🙋🏿‍</i> <i>🧏🏿</i> <i>🧏🏿‍</i> <i>🧏🏿‍</i> <i>🙇🏿</i> <i>🙇🏿‍</i> <i>🙇🏿‍</i> <i>🤦🏿</i> <i>🤦🏿‍</i> <i>🤦🏿‍</i> <i>🤷🏿</i> <i>🤷🏿‍</i> <i>🤷🏿‍</i> <i>🧑🏿‍⚕️</i> <i>👨🏿‍⚕️</i> <i>👩🏿‍⚕️</i> <i>🧑🏿‍🎓</i> <i>👨🏿‍🎓</i> <i>👩🏿‍🎓</i> <i>🧑🏿‍🏫</i> <i>👨🏿‍🏫</i> <i>👩🏿‍🏫</i> <i>🧑🏿‍⚖️</i> <i>👨🏿‍⚖️</i> <i>👩🏿‍⚖️</i> <i>🧑🏿‍🌾</i> <i>👨🏿‍🌾</i> <i>👩🏿‍🌾</i> <i>🧑🏿‍🍳</i> <i>👨🏿‍🍳</i> <i>👩🏿‍🍳</i> <i>🧑🏿‍🔧</i> <i>👨🏿‍🔧</i> <i>👩🏿‍🔧</i> <i>🧑🏿‍🏭</i> <i>👨🏿‍🏭</i> <i>👩🏿‍🏭</i> <i>🧑🏿‍💼</i> <i>👨🏿‍💼</i> <i>👩🏿‍💼</i> <i>🧑🏿‍🔬</i> <i>👨🏿‍🔬</i> <i>👩🏿‍🔬</i> <i>🧑🏿‍💻</i> <i>👨🏿‍💻</i> <i>👩🏿‍💻</i> <i>🧑🏿‍🎤</i> <i>👨🏿‍🎤</i> <i>👩🏿‍🎤</i> <i>🧑🏿‍🎨</i> <i>👨🏿‍🎨</i> <i>👩🏿‍🎨</i> <i>🧑🏿‍✈️</i> <i>👨🏿‍✈️</i> <i>👩🏿‍✈️</i> <i>🧑🏿‍🚀</i> <i>👨🏿‍🚀</i> <i>👩🏿‍🚀</i> <i>🧑🏿‍🚒</i> <i>👨🏿‍🚒</i> <i>👩🏿‍🚒</i> <i>👮🏿</i> <i>👮🏿‍</i> <i>👮🏿‍</i> <i>🕵🏿</i> <i>🕵🏿‍</i> <i>🕵🏿‍</i> <i>💂🏿</i> <i>💂🏿‍</i> <i>💂🏿‍</i> <i>🥷🏿</i> <i>👷🏿</i> <i>👷🏿‍</i> <i>👷🏿‍</i> <i>🫅🏿</i> <i>🤴🏿</i> <i>👸🏿</i> <i>👳🏿</i> <i>👳🏿‍</i> <i>👳🏿‍</i> <i>👲🏿</i> <i>🧕🏿</i> <i>🤵🏿</i> <i>🤵🏿‍</i> <i>🤵🏿‍</i> <i>👰🏿</i> <i>👰🏿‍</i> <i>👰🏿‍</i> <i>🫄🏿</i> <i>🫃🏿</i> <i>🤰🏿</i> <i>🧑🏿‍🍼</i> <i>👨🏿‍🍼</i> <i>👩🏿‍🍼</i> <i>🤱🏿</i> <i>👼🏿</i> <i>🎅🏿</i> <i>🤶🏿</i> <i>🧑🏿‍🎄</i> <i>🦸🏿</i> <i>🦸🏿‍</i> <i>🦸🏿‍</i> <i>🦹🏿</i> <i>🦹🏿‍</i> <i>🦹🏿‍</i> <i>🧙🏿</i> <i>🧙🏿‍</i> <i>🧙🏿‍</i> <i>🧚🏿</i> <i>🧚🏿‍</i> <i>🧚🏿‍</i> <i>🧛🏿</i> <i>🧛🏿‍</i> <i>🧛🏿‍</i> <i>🧜🏿</i> <i>🧜🏿‍</i> <i>🧜🏿‍</i> <i>🧝🏿</i> <i>🧝🏿‍</i> <i>🧝🏿‍</i> <i>💆🏿</i> <i>💆🏿‍</i> <i>💆🏿‍</i> <i>💇🏿</i> <i>💇🏿‍</i> <i>💇🏿‍</i> <i>🚶🏿</i> <i>🚶🏿‍</i> <i>🚶🏿‍</i> <i>🧍🏿</i> <i>🧍🏿‍</i> <i>🧍🏿‍</i> <i>🧎🏿</i> <i>🧎🏿‍</i> <i>🧎🏿‍</i> <i>🧑🏿‍🦯</i> <i>👨🏿‍🦯</i> <i>👩🏿‍🦯</i> <i>🧑🏿‍🦼</i> <i>👨🏿‍🦼</i> <i>👩🏿‍🦼</i> <i>🧑🏿‍🦽</i> <i>👨🏿‍🦽</i> <i>👩🏿‍🦽</i> <i>🏃🏿</i> <i>🏃🏿‍</i> <i>🏃🏿‍</i> <i>🚶🏿‍➡️</i> <i>🚶🏿‍‍➡️</i> <i>🚶🏿‍‍➡️</i> <i>🧎🏿‍➡️</i> <i>🧎🏿‍‍➡️</i> <i>🧎🏿‍‍➡️</i> <i>🧑🏿‍🦯‍➡️</i> <i>👨🏿‍🦯‍➡️</i> <i>👩🏿‍🦯‍➡️</i> <i>🧑🏿‍🦼‍➡️</i> <i>👨🏿‍🦼‍➡️</i> <i>👩🏿‍🦼‍➡️</i> <i>🧑🏿‍🦽‍➡️</i> <i>👨🏿‍🦽‍➡️</i> <i>👩🏿‍🦽‍➡️</i> <i>🏃🏿‍➡️</i> <i>🏃🏿‍‍➡️</i> <i>🏃🏿‍‍➡️</i> <i>💃🏿</i> <i>🕺🏿</i> <i>🕴🏿</i> <i>🧖🏿</i> <i>🧖🏿‍</i> <i>🧖🏿‍</i> <i>🧗🏿</i> <i>🧗🏿‍</i> <i>🧗🏿‍</i> <i>🏇🏿</i> <i>🏂🏿</i> <i>🏌🏿</i> <i>🏌🏿‍</i> <i>🏌🏿‍</i> <i>🏄🏿</i> <i>🏄🏿‍</i> <i>🏄🏿‍</i> <i>🚣🏿</i> <i>🚣🏿‍</i> <i>🚣🏿‍</i> <i>🏊🏿</i> <i>🏊🏿‍</i> <i>🏊🏿‍</i> <i>⛹🏿</i> <i>⛹🏿‍</i> <i>⛹🏿‍</i> <i>🏋🏿</i> <i>🏋🏿‍</i> <i>🏋🏿‍</i> <i>🚴🏿</i> <i>🚴🏿‍</i> <i>🚴🏿‍</i> <i>🚵🏿</i> <i>🚵🏿‍</i> <i>🚵🏿‍</i> <i>🤸🏿</i> <i>🤸🏿‍</i> <i>🤸🏿‍</i> <i>🤽🏿</i> <i>🤽🏿‍</i> <i>🤽🏿‍</i> <i>🤾🏿</i> <i>🤾🏿‍</i> <i>🤾🏿‍</i> <i>🤹🏿</i> <i>🤹🏿‍</i> <i>🤹🏿‍</i> <i>🧘🏿</i> <i>🧘🏿‍</i> <i>🧘🏿‍</i> <i>🛀🏿</i> <i>🛌🏿</i> <i>💑🏿</i> <i>💏🏿</i> <i>👫🏿</i> <i>👭🏿</i> <i>👬🏿</i>'+
				'<br><br></div>',
			width: '90vw',
			height: '90vh'
		});

	}

	if (event.target.tagName == 'I' && event.target.parentElement.id == "copiarEmojis") {
		navigator.clipboard.writeText(event.target.innerText);
		Swal.fire({
			position: 'center',
			icon: 'success',
			title: ' Ctrl + C: ' + event.target.innerText,
			showConfirmButton: false,
			timer: 1500
		  })
	}
	if (event.target.className.includes("icone question-circle") || event.target.className.includes("duvidas")) {
		let msg = '';

		switch (event.target.id) {
			case 'modulo1_1':
				msg = 'Os monitores que aparecem na tela correspondem àqueles que você tem na sua mesa.<br><br>Escolha um monitor (direita, esquerda, etc.) para ser o monitor padrão da janela DETALHES do processo.<br><br>Depois de escolhido, sempre que a janela DETALHES abrir, ela será direcionada para este monitor.';
				break
			case 'modulo1_2':
				msg = 'Se selecionado, ao abrir a página DETALHES do processo, clica no botão "Apreciar Petições" para você, retirando a petição do escaninho.';
				break
			case 'modulo1_3':
				msg = 'Elimine o clique no menu da janela detalhes para as atividades mais utilizadas.<br><br> Escolha aqueles botões que você mais utiliza diariamente, criando atalhos acessíveis com um clique.<br><br>De clique em clique, sua saúde agradece.';
				break
			case 'modulo1_4':
				msg = 'Se selecionado, ao clicar no ícone MARTELO, ou qualquer ação automatizada dele decorrente, antes de levar o processo até a conclusão ao magistrado, clica no botão "Apreciar Petições" para você, retirando a petição do escaninho.';
				break
			case 'modulo1_5':
				msg = 'Se selecionado, ao abrir a Janela DETALHES, irá guardar os dados do processo na memória da extensão para uso futuro. É o mesmo efeito de clicar no botão (<i class="icone address-card t20" style="vertical-align: bottom; cursor: default;"></i>)<br><br>Para visualizar os dados clique com o botão direito do mouse em qualquer lugar da tela e selecione o submenu "maisPje".';
				break
			case 'modulo1_6':
				msg = 'Se selecionado, ao clicar no ícone MOVIMENTAR PROCESSO, ou qualquer ação automatizada dele decorrente, antes de levar o processo até a tarefa desejada, clica no botão "Apreciar Petições" para você, retirando a petição do escaninho.';
				break
			case 'modulo1_7':
				msg = 'Se selecionado, ao abrir a página DETALHES do processo, irá executar a funcionalidade de "Pesquisa Personalizada" da extensão maisPje. Com ela é possível "filtrar" documentos na timeline do processo.<br><br>Ao definir um padrão de pesquisa (uma palavra), o filtro do Pje será aplicado automaticamente quando do carregamento da página.<br><br>É possível pesquisar mais de uma palavra ao mesmo tempo, bastando separá-las por ponto e vírgula. Contudo, essa pesquisa se limitará apenas à descrição (Título) do documento na timeline não tendo qualquer relação com a ferramenta de pesquisa do próprio PJe. Por exemplo: <br><br><b>Requisição de Pequeno Valor;precatório</b><br><br> esse padrão irá filtrar na timeline do processo os documentos juntados cuja descrição (Título) possua a expressão "Requisição de Pequeno Valor" ou a expressão "precatório".<br><br>Por fim, e não menos importante, também é possível favoritar o(s) tipo(s) de pesquisa utilizados no filtro "oficial" do PJe, "Pesquisar Conteúdo", "Documentos" e/ou "Movimentos", lembrando que essa escolha não terá qualquer influência na pesquisa múltipla (mais de uma palavra separada por ponto e vírgula), apenas na pesquisa simples (uma palavra)';
				break
			case 'modulo1_8':
				msg = 'Se selecionado, ativa o mapeamento de IDs no documento visível no processo. O mapeamento funciona apenas nos documentos em que é possível selecionar o texto.';
				break
			case 'modulo2_1':
				msg = 'Os monitores que aparecem na tela correspondem àqueles que você tem na sua mesa.<br><br>Escolha um monitor (direita, esquerda, etc.) para ser o monitor padrão da janela GIGS do processo.<br><br>Depois de escolhido sempre que a janela GIGS abrir, ela será direcionada para este monitor.<br><br> Caso o monitor escolhido seja o mesmo das janelas Detalhes do processo ou Tarefas do processo, a janela GIGS manterá a proporção de 1/3.';
				break
			case 'modulo2_2':
				msg = 'Aqui é possível atribuir uma atividade (GIGS) para um servidor.<br><br>O resultado esperado é: escolhida a atividade no GIGS, o campo Responsável será preenchido automaticamente.<br><br>Para isso você deve criar as regras, clicando no botão "Criar Regra". Na janela que aparecer preencha o nome da atividade (não é obrigatório), o nome do responsável (é obrigatório) e o(s) número(s) final do processo.<br><br>Por exemplo: Você quer que a atividade ACORDO seja atribuída automaticamente ao servidor JOÃO DA SILVA. Preencha o nome da atividade como "ACORDO", o responsável como "JOÃO DA SILVA" e marque todos os números.<br><br>Caso você queira que apenas os processos pares sejam direcionados ao JOÃO DA SILVA, preencha a atividade como "ACORDO", o responsável como "JOÃO DA SILVA" e marque apenas os números pares (0, 2, 4, 6 e 8).<br><br> Outro exemplo: Você quer que toda e qualquer atividade cadastrada no GIGS seja atribuída para o responsável JOÃO DA SILVA desde que o processo termine com o número 2, 3 ou 5.<br><br>Neste caso, deixe o campo atividade em branco, preencha o responsável como "JOÃO DA SILVA" e marque apenas os números (2, 3 e 5).<br><br>É importante salientar que a extensão dará preferência para as tarefas discriminadas, se não existir ninguém atribuído para aquela tarefa é que serão aplicadas as regras por número final do processo.<br><br> Por exemplo: você tem duas regras cadastradas, uma diz que a atividade ACORDO será atribuída ao responsável JOÃO DA SILVA, a outra diz que toda e qualquer tarefa será atribuída para o responsável JOSÉ DO NASCIMENTO, desde que o processo termine com final par. Neste caso a extensão dará preferência para a primeira regra.';
				break
			case 'modulo3_1':
				msg = 'Os monitores que aparecem na tela correspondem àqueles que você tem na sua mesa.<br><br>Escolha um monitor (direita, esquerda, etc.) para ser o monitor padrão da janela TAREFAS do processo.<br><br>Depois de escolhido sempre que a janela TAREFAS abrir, ela será direcionada para este monitor.';
				break
			case 'modulo4_1':
				msg = 'Se você tem apenas um papel no PJe, esta configuração não é pra você.<br><br>Quando temos mais do que um papel registrado no PJe, no acesso, o sistema escolhe aleatoriamente um deles.<br><br>Aqui, você define qual o papel que o sistema deverá escolher primeiro.<br><br>É possível escolher também selecionando o papel preferido dentro do próprio PJe.';
				break
			case 'modulo5_1':
				msg = 'Se você utiliza a divisão de processos por números (final 0, final 1, etc.), esse filtro irá ajudá-lo a visualizar apenas os seus processos.<br><br>Mas atenção, o filtro funciona somente nos processos que aparecem na tela.<br><br>Se a sua consulta possuir mais de uma página, o filtro não será aplicado nelas.<br><br>Outra forma de utilizar o filtro é pressionando F2.';
				break
			case 'modulo6_1':
				msg = 'Deseja enviar por email um documento do processo? Que tal com um único clique?<br>Configure o seu email como email padrão do navegador, crie um email padrão de resposta, utilizando as variáveis disponíveis e pronto!';
				break
			case 'modulo6_2':
				msg = 'modulo6_2';
				break
			case 'modulo7_1':
				msg = 'Nesse módulo é possível criar ações automatizadas, como por exemplo, uma certidão que você junta com freqüência durante o trabalho.<br><br>Cadastrando-a é possível gerá-la com apenas um clique.<br><br>É possível também criar intimações e lançamentos no GIGS. TUDO de forma automática.<br><br>Não se esqueça de informar corretamente os dados para que o robô possa recuperá-los no PJe.<br><br>DICA: a visibilidade da AA pode ser facilmente alterada ao clicar no botão mantendo a tecla CTRL pressionada.';
				break
			case 'modulo7_2':
				msg = 'Agora é possível ajustar o tempo de execução das interações da ação automatizada.<br><br>Aumente o tempo de interação caso perceba alguma instabilidade no uso da extensão, principalmente quando ela não completa a ação automatizada.<br>Se tiver dúvidas assista o vídeo tutorial.';
				break
			case 'atalhos_1':
				msg = 'Ao pressionar a sequência de teclas durante o uso do PJe, o atalho correspondente será utilizado.<br><br>Lembre-se que, para o atalho funcionar, você deverá estar navegando na respectiva janela (Página PRINCIPAL ou DETALHES).';
				break
			case 'atalhos_2':
				msg = 'Aqui é possível atribuir um atalho ao menu do maisPJe, acessível ao clicar no ícone da extensão na barra de endereços.<br><br>Para isso você deve escrever em cada linha o nome do atalho, dois pontos (:), o endereço do atalho.<br><br>Por exemplo:<br>&nbsp;&nbsp;&nbsp; Intranet:http://intranet.trt12.jus.br/caslogin<br><br>É possível também agrupá-los por cor, bastando para isso colocar a tag [azul], [verde], [vermelho] ou [amarelo] na frente do atalho.<br><br>Por exemplo:<br>&nbsp;&nbsp;&nbsp; [azul]Intranet:http://intranet.trt12.jus.br/caslogin <br>Experimente! <br><br> <i>Dica: você também usar cores hexadecimais dentro do colchetes ;)</i> <br><br> Para personalizar ainda mais, é possível inserir ícones.. clique no link do Emoji (ao lado), copie o ícone desejado e cole ele no início da linha, antes da cor.';
				break
			case 'config_1':
				msg = 'Quer usar as suas configurações em outro computador?<br>Clique em "Guardar", copie o conteúdo e guarde.<br>No computador novo, com a extensão instalada, clique em "Recuperar", cole o conteúdo e pronto! Suas configurações foram restauradas.';
				break
			case 'modulo8':
				msg = 'Permite que a extensão escolha o magistrado automaticamente, quando aparecer no PJe uma caixa de seleção para este fim.<br><br>Você pode criar regra por <i style="font-style:normal;color: chocolate;">NÚMERO FINAL</i> do processo, por <i style="font-style:normal;color: cadetblue;">UNIDADE JUDICIÁRIA</i> ou por <i style="font-style:normal;color: orangered;">ÓRGÃO JULGADOR CARGO</i>.<br><br>A opção de "ignorar 0 na regra por número final" é ideal para divisão de processos entre três juízes, caso o último numeral seja 0, a regra será aplicada de acordo com o penúltimo numeral, e assim por diante.';
				break
			case 'modulo10_duvidas':
			case 'modulo10_duvidas_icone':
				msg = 'Se você utiliza links fixos de audiência agora é possível deixá-los memorizados para usar quando for incluir um processo em pauta.';
				break
			case 'modulo11':
				msg = 'Crie cabeçalhos personalizados para a Certidão Automatizada de Habilitação de Créditos de acordo com o CNPJ da executada.<br><br>Você encontra essa funcionalidade na janela de <b>Registrar Obrigações de Pagar</b> do PJe.';
				break
			default:
				console.log("sem ajuda");
		}
		Swal.fire(
		  'Dúvida?',
		  msg,
		  'question'
		)
	} else if (event.target.className == 'tutorial') {
		Swal.mixin({
			imageWidth: 400,
			imageHeight: 200,
			confirmButtonText: 'Próximo &rarr;',
			showCancelButton: true,
			progressSteps: ['1', '2', '3', '4']
		}).queue([
		{
			html: '<div class="tutorial1" style="width: 400px;height: 200px;"></div>'
		},
		{
			html: '<div class="tutorial2" style="width: 400px;height: 200px;"></div>'
		},
		{
			html: '<div class="tutorial3" style="width: 400px;height: 200px;"></div>'
		},
		{
			html: '<div class="tutorial4" style="width: 400px;height: 200px;"></div>',
			confirmButtonText: 'Pronto!',
			showCancelButton: false
		}
		]).then((result) => {

		})
	} else if (event.target.className.includes("icone video") || event.target.className.includes("video-explicativo")) {
		let video = '';
		switch (event.target.id) {
			case 'modulo1_1':
				video = 'https://www.youtube.com/embed/BvqenHqem4s';
				break
			// case 'modulo2_1_video':
			// 	video = 'https://www.youtube.com/embed/8tLj_3Uy3gU';
			// 	break
			// case 'modulo3_1':
			// 	video = 'https://drive.google.com/file/d/1R2nivNisv2Ro-ycquKKKLBtwX2iWdYbP/preview';
			// 	break
			case 'modulo4_1':
				video = 'https://drive.google.com/file/d/19me--CZ-Utl1WQ_hW-zFq513oXEeCFGQ/preview';
				break
			case 'modulo5_1':
				video = 'https://drive.google.com/file/d/1gYR-NguwPUn2eU9mRpIa9C1u4IubBOWr/preview';
				break
			case 'modulo6_1':
				video = 'https://drive.google.com/file/d/1UK2n4QFBidwTiWbtDAFq2u34AMJw4hyi/preview?t=3m51s';
				break
			case 'modulo6_2':
				video = 'https://drive.google.com/file/d/1QMmbBCWHWkRlrc4SLpyDjuwuOt9BV-rC/preview';
				break
			case 'modulo7_1':
				video = 'https://drive.google.com/file/d/15AzyDkraBy_Mj7GlSPOXSdkWeF3QpbJZ/preview';
				break
			case 'modulo7_2':
				video = 'https://www.youtube.com/embed/1jd6s2-L61E';
				break
			case 'atalhos_1':
				video = 'https://drive.google.com/file/d/1ls27iUBvd7LqwROOW_qmLbMMednSR3eN/preview';
				break
			case 'botoes_1':
			case 'botoes_1_icone':
				video = 'https://drive.google.com/file/d/1LWaryUZc_HAcBNwC63BEkxY9AiLq-79R/preview';
				break
			case 'config_1':
				video = 'https://drive.google.com/file/d/1XhDpAjYn-zy9rRyFzwLGxwHXOH6mN93r/preview?t=1m18s';
				break
			default:
				console.log("sem ajuda");
		}
        if (video) {
            abrirVideo(video);
        }
	}
	//DESCRIÇÃO CRIA AS REGRAS DE SALVAMENTO QUANDO O USUARIO OPTAR PELO POSICIONAMENTO DOS MONITORES
	// if (event.target.id.search('gigsMonitor') > -1) {
		// if (document.querySelector('#desativarAjusteJanelas').checked) {
			// document.querySelector('#desativarAjusteJanelas').checked = false;
			// Swal.fire(
				// 'Posição das Janelas',
				// 'A partir de agora, a extensão controlará o posicionamento das janelas DETALHES, GIGS e TAREFAS para você ;)<br><br>Escolha os monitores de acordo com a sua preferência!<br><br>Se desejar voltar atrás, basta selecionar a opção "Desativar o posicionamento automático das janelas", que fica ao lado do botão "Verificar monitores"',
				// 'info'
			// ).then((result) => {
				// atualizaMonitor(event.target.id);
				// salvarOpcoes();
			// })
		// } else {
			// atualizaMonitor(event.target.id);
			// salvarOpcoes();
		// }
	// }


	//ATALHOS DE Menu
	let id_elemento = event.target.id || event.target.parentElement.id
	if (id_elemento) {

		//eventos do checkbox parEimpar
		if (id_elemento.includes('maisPje_parEimpar')) {
			let msg = event.target;
			// console.log(msg.textContent + " : " + msg.getAttribute('name'));
			parEimpar(msg.getAttribute('name'));
		}

		if (id_elemento.includes('maisPje_modulo5_parEimpar')) {
			let msg = event.target;
			// console.log(msg.textContent + " : " + msg.getAttribute('name'));
			modulo5ParEimpar(msg.getAttribute('name'));
		}



		//eventos dos vinculos: lixeira
		if (id_elemento.includes('apagar-escolherAAVinculo')) {
			let seletor = id_elemento.replace('apagar-','');
			document.getElementById(seletor).innerText = "Nenhum";
		}
	}


});

document.body.addEventListener("mouseover", function (event) {
	let id_elemento = event.target.id || event.target.parentElement.id
	if (id_elemento) {

		event.target.addEventListener("mouseout", function (event) {
			let ancora = document.querySelectorAll('div[id="escolherProcessoFinal"] label[class="container"]');
			let map = [].map.call(
				ancora,
				function(elemento) {
					elemento.style.backgroundColor = "unset";
				}
			);
		});


		if (id_elemento.includes('maisPje_parEimpar')) {
			let escolha = event.target.getAttribute('name');

			let teste = '';
			switch (escolha) {
				case 'par':
					teste = preferencias.modulo8_ignorarZero ? '2,4,6,8' : '0,2,4,6,8';
					break;
				case 'impar':
					teste = '1,3,5,7,9';
					break;
				case 'todos':
					teste = preferencias.modulo8_ignorarZero ? '1,2,3,4,5,6,7,8,9' : '0,1,2,3,4,5,6,7,8,9';
					break;
				case 'nenhum':
					teste = '';
					break;
			}

			let ancora = document.querySelectorAll('div[id="escolherProcessoFinal"] label[class="container"]');
			let map = [].map.call(
				ancora,
				function(elemento) {
					if (teste.includes(elemento.innerText)) {
						elemento.style.backgroundColor = "#ff976e";
					}
				}
			);
		}
	}
});

document.body.addEventListener("selectionchange", function (event) {
	if (event.target.id == 'swal-input-importarAA1') {

		let conteudo = document.querySelector('#swal-input-importarAA1').value;
		let novoConteudo = conteudo.match(/\{.+?\}/g);
		console.log(novoConteudo.length)
		console.log(Array.isArray(novoConteudo))
		let x = 1;
		for (const [pos, item] of novoConteudo.entries()) {
			if (item.length > 0) {
				document.querySelector('#swal-input-importarAA' + x).value = item;
				x++;
			}
		}
	}
});


function AcaoAutomatizada_aaAnexar(nm_botao, tipo, descricao, sigilo, modelo, assinar, cor, vinculo, visibilidade='sim') {
	this.nm_botao = nm_botao;
	this.tipo = tipo;
	this.descricao = descricao;
	this.sigilo = sigilo;
	this.modelo = modelo;
	this.assinar = assinar;
	this.cor = cor;
	this.vinculo = vinculo;
	this.visibilidade = visibilidade;
}

function AcaoAutomatizada_aaComunicacao(nm_botao, tipo, subtipo, tipo_prazo, prazo, descricao, sigilo, modelo, salvar, cor, vinculo, fluxo, visibilidade='sim', comandosEspeciais='') {
	this.nm_botao = nm_botao;
	this.tipo = tipo;
	this.subtipo = subtipo;
	this.tipo_prazo = tipo_prazo;
	this.prazo = prazo;
	this.descricao = descricao;
	this.sigilo = sigilo;
	this.modelo = modelo;
	this.salvar = salvar;
	this.cor = cor;
	this.vinculo = vinculo;
	this.fluxo = fluxo;
	this.visibilidade = visibilidade;
	this.comandosEspeciais = comandosEspeciais;
}

function AcaoAutomatizada_aaAutogigs(nm_botao, tipo, tipo_atividade, prazo, responsavel, responsavel_processo, observacao, salvar, cor, vinculo, visibilidade='sim') {
	this.nm_botao = nm_botao;
	this.tipo = tipo;
	this.tipo_atividade = tipo_atividade;
	this.prazo = prazo;
	this.responsavel = responsavel;
	this.responsavel_processo = responsavel_processo;
	this.observacao = observacao;
	this.salvar = salvar;
	this.cor = cor;
	this.vinculo = vinculo;
	this.visibilidade = visibilidade;
}

function AcaoAutomatizada_aaDespacho(nm_botao, tipo, descricao, sigilo, modelo, juiz, responsavel, assinar, cor, vinculo, visibilidade='sim', comandosEspeciais='') {
	this.nm_botao = nm_botao;
	this.tipo = tipo;
	this.descricao = descricao;
	this.sigilo = sigilo;
	this.modelo = modelo;
	this.juiz = juiz;
	this.responsavel = responsavel;
	this.assinar = assinar;
	this.cor = cor;
	this.vinculo = vinculo;
	this.visibilidade = visibilidade;
	this.comandosEspeciais = comandosEspeciais;
}

function AcaoAutomatizada_aaMovimento(nm_botao, destino, chip, responsavel, cor, vinculo, visibilidade='sim') {
	this.nm_botao = nm_botao;
	this.destino = destino;
	this.chip = chip;
	this.responsavel = responsavel;
	this.cor = cor;
	this.vinculo = vinculo;
	this.visibilidade = visibilidade;
}

function AcaoAutomatizada_aaChecklist(nm_botao, tipo, observacao, estado, alerta, salvar, cor, vinculo, visibilidade='sim') {
	this.nm_botao = nm_botao;
	this.tipo = tipo;
	this.observacao = observacao;
	this.estado = estado;
	this.alerta = alerta;
	this.salvar = salvar;
	this.cor = cor;
	this.vinculo = vinculo;
	this.visibilidade = visibilidade;
}

function AcaoAutomatizada_aaNomearPerito(nm_botao, profissao, perito, prazo, tipo_prazo, designar, modelo, assinar, cor, vinculo, visibilidade='sim') {
	this.nm_botao = nm_botao;
	this.profissao = profissao;
	this.perito = perito;
    this.prazo = prazo;
    this.tipo_prazo = tipo_prazo;
    this.designar = designar;
	this.modelo = modelo;
	this.assinar = assinar;
	this.cor = cor;
	this.vinculo = vinculo;
	this.visibilidade = visibilidade;
}

function EmailAutomatizado(titulo, corpo, assinatura) {
	this.titulo = titulo;
	this.corpo = corpo;
	this.assinatura = assinatura;
}

async function criarCaixaSelecao(listaDeOpcoes=[],titulo='Escolha entre as opções',valorAnterior=[],nomeBotaoContinuar='Nenhum',multiplaEscolha=false,retornarPosicao=false) { //retornarPosicao: a resposta é a posicao do elemento e não seu valor
	return new Promise(
		resolver => {
			if (!document.getElementById('maisPje_caixa_de_selecao')) {

				// DESCRIÇÃO: REGRA DO TOOLTIP
				if (!document.getElementById('maisPje_tooltip_fundo')) {
					tooltip('fundo', true);
				}

				let altura = window.innerHeight || document.documentElement.clientHeight || document.body.clientHeight;

				let elemento1 = document.createElement("div");
				elemento1.id = 'maisPje_caixa_de_selecao';
				elemento1.style = 'position: fixed; width: 100%; height: ' + altura + 'px; top: 0; inset: 0px; background: #00000080; z-index: 10000; display: flex; align-items: center; justify-content: center; color: rgb(81, 81, 81); font-weight: bold; font-family: Open Sans,Arial,Verdana,sans-serif; text-align: center; flex-direction: column;';
				elemento1.onclick = function (e) {
					if (e.target.id == "maisPje_caixa_de_selecao") {
						elemento1.remove();
						resolver(null);
					}
				}; //se clicar fora fecha a janela

				let container = document.createElement("div");
				container.style="height: auto; min-width: 20vw; display: inline-grid; background-color: white;padding: 15px;border-radius: 4px;box-shadow: 0 2px 1px -1px rgba(0,0,0,.2),0 1px 1px 0 rgba(0,0,0,.14),0 1px 3px 0 rgba(0,0,0,.12);";

				let div = document.createElement("div");
				div.style = "color: grey; border-bottom: 1px solid lightgrey; display: grid; grid-template-columns: 93% 6%;margin-bottom: 5px;";
				let t = titulo.split('|');
				let spanTitulo = document.createElement("span");
				spanTitulo.style = "color: grey; font-size:1.4em;";
				spanTitulo.innerText = t[0];
				div.appendChild(spanTitulo);

				let logo = document.createElement("span");
				logo.style = "color: grey; display: flex;justify-self: end; opacity:50%;";
				logo.innerText = "+PJ";
				let logoi = document.createElement("i");
				logoi.style = "color:#e8571e;font-style: normal;";
				logoi.innerText = "e";
				logo.appendChild(logoi)
				div.appendChild(logo);

				container.appendChild(div);

				if (t[1]) { //subtitulo
					let spanSubTitulo = document.createElement("span");
					spanSubTitulo.style = "color: cadetblue;font-style: italic;font-weight: normal;padding: 10px 5px;font-size: 1.1em;";
					spanSubTitulo.innerText = t[1];
					container.appendChild(spanSubTitulo);
				}

				let containerSelect = document.createElement("select");
				containerSelect.style = 'max-height: 90vh;cursor: pointer; margin-top: 10px; padding: 10px; background-color: white; color: rgb(81, 81, 81); font-size:1.3em;overflow-y: auto;text-align: center;';

				if (multiplaEscolha) {
					containerSelect.setAttribute('multiple','true');
					containerSelect.style.minHeight = '80vh';
				}

				let check;
				for (const [pos, opcao] of listaDeOpcoes.entries()) {
					let option = document.createElement("option");
					option.id = 'maisPje_selecao_select_' + (pos+1);
					option.style = 'background-color: whitesmoke;padding: 10px;border-radius: 5px;';
					option.value = opcao;
					option.innerText = opcao;
					option.onmouseenter = function () { this.style.filter = 'brightness(.8)' };
					option.onmouseleave = function () { this.style.filter = 'brightness(1)' };

					option.selected = (valorAnterior.includes(opcao)) ? true : false;

					if (nomeBotaoContinuar.includes('Nenhum')) {
						//ajusta o select para vir aberto
						containerSelect.style.border = 'none';
						containerSelect.setAttribute('size',listaDeOpcoes.length);

						option.onclick = function () {
							clearInterval(check);
							let resposta;
							if (retornarPosicao) {
								resposta = pos;
							} else {
								resposta = this.innerText;
							}
							document.getElementById('maisPje_caixa_de_selecao').remove();
							return resolver(resposta);
						};


					}

					containerSelect.appendChild(option);
				}

				container.appendChild(containerSelect);

				if (!nomeBotaoContinuar.includes('Nenhum')) {
					let bt_continuar = document.createElement("span");
					bt_continuar.style = "color: white; margin-top: 10px; padding: 10px; border-bottom: 1px solid lightgrey; background-color: #7a9ec8; border-radius: 3px; cursor: pointer;font-size: 1.3em;";
					bt_continuar.innerText = nomeBotaoContinuar;
					bt_continuar.onmouseenter = function () {
						bt_continuar.style.backgroundColor  = '#5077a4';
					};
					bt_continuar.onmouseleave = function () {
						bt_continuar.style.backgroundColor  = '#7a9ec8';
					};
					bt_continuar.onclick = function () {
						let valores = containerSelect.value;
						if (multiplaEscolha) {
							let optSelecionadas = containerSelect.selectedOptions;
							valores = Array.from(optSelecionadas).map(({ value }) => value);
						}
						resolver(valores);
						document.getElementById('maisPje_caixa_de_selecao').remove();
					};
					container.appendChild(bt_continuar);
				}

				elemento1.appendChild(container);
				document.body.appendChild(elemento1);
				containerSelect.click(); //serve para exibir as oipções selecionadas

			} else {
				resolver(null);
			}
		}
	);
}

function criarCaixaDePergunta(tipo, titulo, valorAnterior='', placeholder='', nomeDoBotao='OK') {
	return new Promise(resolver => {
		if (!document.getElementById('maisPje_caixa_de_selecao')) {
			// DESCRIÇÃO: REGRA DO TOOLTIP
			if (!document.getElementById('maisPje_tooltip_fundo')) {
			tooltip('fundo', true);
			}

			let altura = window.innerHeight || document.documentElement.clientHeight || document.body.clientHeight;

			let elemento1 = document.createElement("div");
			elemento1.id = 'maisPje_caixa_de_pergunta';
			elemento1.style = 'position: fixed; width: 100%; height: ' + altura + 'px; top: 0; inset: 0px; background: #00000080; z-index: 10000; display: flex; align-items: center; justify-content: center; color: rgb(81, 81, 81); font-weight: bold; font-family: Open Sans,Arial,Verdana,sans-serif; text-align: center; flex-direction: column;';
			elemento1.onclick = function (e) {
				if (e.target.id == "maisPje_caixa_de_pergunta") {
					elemento1.remove();
					resolver(null);
				}
			}; //se clicar fora fecha a janela

			let container = document.createElement("div");
			container.style="height: auto; min-width: 20vw; display: inline-grid; background-color: white;padding: 15px;border-radius: 4px;box-shadow: 0 2px 1px -1px rgba(0,0,0,.2),0 1px 1px 0 rgba(0,0,0,.14),0 1px 3px 0 rgba(0,0,0,.12);";

			let div = document.createElement("div");
			div.style = "color: grey; border-bottom: 1px solid lightgrey; display: grid; grid-template-columns: 93% 6%;margin-bottom: 5px;";
			let t = titulo.split('|');
			let spanTitulo = document.createElement("span");
			spanTitulo.style = "color: grey; font-size:1.4em;";
			spanTitulo.innerText = t[0];
			div.appendChild(spanTitulo);

			let logo = document.createElement("span");
			logo.style = "color: grey; display: flex;justify-self: end; opacity:50%;";
			logo.innerText = "+PJ";
			let logoi = document.createElement("i");
			logoi.style = "color:#e8571e;font-style: normal;";
			logoi.innerText = "e";
			logo.appendChild(logoi)
			div.appendChild(logo);

			container.appendChild(div);

			if (t[1]) { //subtitulo
				let spanSubTitulo = document.createElement("span");
				spanSubTitulo.style = "color: cadetblue;font-style: italic;font-weight: normal;padding: 10px 5px;font-size: 1.1em;";
				spanSubTitulo.innerText = t[1];
				container.appendChild(spanSubTitulo);
			}

			if (t[2]) { //opcoes
				let spanOpt = document.createElement("span");
				spanOpt.style = "text-align: justify;padding-left: 15%;font-weight: bold;color: darkcyan;";
				spanOpt.innerText = t[2];
				container.appendChild(spanOpt);
			}

			let inputTexto;
			if (tipo == 'textarea') {
				inputTexto = document.createElement("textarea")
				inputTexto.id = 'maisPje_cxPergunta_inputTexto';
				inputTexto.style = "font-size: 16px; color: rgba(0,0,0,.87); border-bottom: 1px solid lightgrey; padding: 8px; height: 40px;box-shadow: none;outline: none !important;height: calc(70vh * .1);letter-spacing: normal;";
				if (valorAnterior) { inputTexto.value = valorAnterior }
				if (placeholder) { inputTexto.placeholder = placeholder }
				inputTexto.onkeypress = function (e) {
					if (e.getModifierState("Control") && e.keyCode == 13) {
						btOk.click();
					}
				};

			} else if (tipo == 'data') {
				inputTexto = document.createElement("input");
				inputTexto.id = 'maisPje_cxPergunta_inputTexto';
				inputTexto.type = 'date';
				inputTexto.style = "font-size: 16px; color: rgba(0,0,0,.87); border-bottom: 1px solid lightgrey; padding: 8px; height: 40px;box-shadow: none;outline: none !important;";

				if (valorAnterior) { inputTexto.value = valorAnterior.split('/').reverse().join('-') }
				if (placeholder) { inputTexto.placeholder = placeholder.split('/').reverse().join('-')  }
				inputTexto.onkeypress = function (e) {
					if (e.keyCode == 13) {
						btOk.click();
					}
				};

			} else {
				inputTexto = document.createElement("input");
				inputTexto.id = 'maisPje_cxPergunta_inputTexto';
				inputTexto.type = tipo;
				inputTexto.style = "font-size: 16px; color: rgba(0,0,0,.87); border-bottom: 1px solid lightgrey; padding: 8px; height: 40px;box-shadow: none;outline: none !important;";
				if (valorAnterior) { inputTexto.value = valorAnterior }
				if (placeholder) { inputTexto.placeholder = placeholder }
				inputTexto.onkeypress = function (e) {
					if (e.keyCode == 13) {
						btOk.click();
					}
				};
			}

			container.appendChild(inputTexto);

			let btOk = document.createElement("span");
			btOk.id = 'maisPje_caixa_de_pergunta_btOK';
			btOk.style = "color: white; margin-top: 10px; padding: 10px; border-bottom: 1px solid lightgrey; background-color: #7a9ec8; border-radius: 3px; cursor: pointer;font-size: 1.4em;";
			btOk.innerText = nomeDoBotao;
			btOk.onmouseenter = function () { btOk.style.backgroundColor  = '#5077a4' };
			btOk.onmouseleave = function () { btOk.style.backgroundColor  = '#7a9ec8' };
			btOk.onclick = function () {
				elemento1.remove();
				let resposta;
				if (tipo == 'data') {
					let dataPreenchida = new Date(inputTexto.value);
					let dia  =  (dataPreenchida.getDate()+1 + '').padStart(2,'0') + '/';
					let mes = ((dataPreenchida.getMonth()+1) + '').padStart(2,'0');
					let ano = '/' + dataPreenchida.getFullYear();
					resposta = dia + mes + ano;
				} else {
					resposta = inputTexto.value;
				}
				resolver(resposta);
			};
			container.appendChild(btOk);

			elemento1.appendChild(container);
			document.body.appendChild(elemento1);

			//atribui o foco ao input
			let check1 = setInterval(async function() {
				if (document.activeElement === inputTexto) {
					clearInterval(check1);
					window.focus(); //primeiro a janela
					inputTexto.focus();
				} else {
					inputTexto.focus();
				}
			}, 100);
		} else {
			resolver(null);
		}
	});

}

function sleep(ms) {
	return new Promise(resolve => setTimeout(resolve, ms));
}

document.querySelector('button#modulo2_1_video')?.addEventListener('click', () => abrirVideo('https://www.youtube.com/embed/8tLj_3Uy3gU'));
document.querySelector('button#modulo3_1_video')?.addEventListener('click', () => abrirVideo('https://drive.google.com/file/d/1R2nivNisv2Ro-ycquKKKLBtwX2iWdYbP/preview'));
//filter: sepia(2) saturate(10) hue-rotate(-189deg);
//👤
/** @param {string} video link para o video */
function abrirVideo(video) {
    let html = '<iframe width="640" height="360" src="' + video + '" frameborder="0" allowfullscreen></iframe>';
    if (video.includes('youtube')) {
        html = '<iframe width="560" height="315" src="' + video + '?autoplay=1" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>';
    }
    Swal.fire({
        title: '<strong>Vídeo Tutorial</strong>',
        html: html,
        width: 800,
        padding: '3em',
        showCloseButton: true,
        showCancelButton: false,
        showConfirmButton: false,
        focusConfirm: false
    });
}
