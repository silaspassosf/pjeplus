// Data: 13/09/2023
// trt1 : 2.10.1 - ANGICO
// trt2 : 2.10.1 - ANGICO
// trt3 : 2.10.1 - ANGICO
// trt4 : 2.9.3 - SIBIPIRUNA
// trt5 : 2.10.1 - ANGICO
// trt6 : 2.9.6 - SIBIPIRUNA
// trt7 : 2.9.6 - SIBIPIRUNA
// trt8 : 2.10.1 - ANGICO
// trt9 : 2.9.6 - SIBIPIRUNA
// trt10 : 2.9.6 - SIBIPIRUNA
// trt11 : 2.9.6 - SIBIPIRUNA
// trt12 : 2.10.1 - ANGICO
// trt13 : 2.10.1 - ANGICO
// trt14 : 2.9.6 - SIBIPIRUNA
// trt15 : 2.9.5 - SIBIPIRUNA
// trt16 : 2.10.1 - ANGICO
// trt17 : 2.9.6 - SIBIPIRUNA
// trt18 : 2.9.6 - SIBIPIRUNA
// trt19 : 2.9.6 - SIBIPIRUNA
// trt20 : 2.10.1 - ANGICO
// trt21 : 2.9.6 - SIBIPIRUNA
// trt22 : 2.10.1 - ANGICO
// trt23 : 2.10.1 - ANGICO
// trt24 : 2.10.1 - ANGICO
var preferencias = [];
var erro = false;
var seletorDetalhesNumeroProcesso210 = '*[aria-label*="Abre o resumo do processo"],*[mattooltip="Abre o resumo do processo."]';
var seletorDetalhesNumeroProcesso = seletorDetalhesNumeroProcesso210 + ',' + '*[aria-label*="Detalhes do Processo"],*[mattooltip="Detalhes do Processo"],button[name="numero-processo"], button[name="numero-processo"], pje-descricao-processo button, pje-descricao-processo a';

browser.storage.local.get(null, async function(configuracoes){
	preferencias = configuracoes;	
	if (preferencias.concordo) {
		if (preferencias.extensaoAtiva) {
			await checarVariaveis();
			await sleep(preferencias.maisPje_velocidade_interacao * 0.2);
			executar();
		}
	} else {
		browser.runtime.sendMessage({tipo: 'criarAlerta', valor: '+PJe: Para a extensão funcionar você precisa tomar ciência do Aviso Legal.\nClique aqui para visualizá-lo.', icone: '6'});
		browser.runtime.sendMessage({tipo: 'iconeNavegador', valor: '+PJe: Desligado', icone: 'ico_16_off.png'});
	}
});

//FUNÇÃO RESPONSÁVEL POR FILTRAR AS PÁGINAS QUE RECEBERÃO TRATAMENTO
//SEMPRE QUE A PÁGINA É CARREGADA (ONLOAD) A FUNÇÃO VERIFICA O ENDEREÇO DA PÁGINA E EXECUTA AS FUNÇÕES DE ACORDO COM AS PREFERÊNCIAS GRAVADAS
async function executar() {
	if (!preferencias.extensaoAtiva) { return } 
	console.debug(document.referrer + " >>>> " + document.location.href);
	// console.log(document.referrer.length);

	//teste atualizar bugado
	//não resolve pois a mensagem está aparecendo na tela do sisbajud enquanto 	que o correto seria na tela do detalhes
	// if (document.referrer.length == 0 && preferencias.tempBt[1] == 'Atualizar Pagina|Atualizar Pagina') {
	// 	await criarCaixaDeAlerta('ALERTA','Erro ao carregar os dados da extensão. A página será atualizada automaticamente.',5);
	// 	window.reload();
	// 	return;
	// }
	
	console.debug('*******************************');
	console.debug('*************maisPje: INICIANDO A PAGINA');
	console.debug('*******************************');
	console.debug('*************preferencias.AALote:' + preferencias.AALote);
	console.debug('*************preferencias.tempBt:' + preferencias.tempBt);
	console.debug('*************preferencias.tempAAEspecial:' + preferencias.tempAAEspecial);
	console.debug('*************preferencias.tempAR:' + preferencias.tempAR);
	// console.debug('*************preferencias.trt:' + preferencias.trt);
	
	
	
	if (document.location.href.includes("/administracao")) {
		if (document.referrer.includes("login.seam")) {
			mudarPerfil();
			await sleep(2000);
			addBotaoTelaPrincipal();
			kaizen('PRINCIPAL');
		}
		
	} else if (document.location.href.includes(".jus.br/pjekz/")) {
		
		if (document.querySelector('pje-cabecalho-perfil')) { monitor_Janela_Principal() }
		
		//Por quê <<<!document.location.href.includes("mailto")>>> ? serve para inibir a entrada de parametros enviados com o protocolo mailto contendo links do pje (que possuem a expressão ".jus.br/pjekz/")
		if (document.referrer.length == 0 && !document.location.href.includes("/pauta-audiencias") && !document.location.href.includes("/conteudo") && !document.location.href.includes("mailto") && !document.location.href.includes("/detalhe")) {
			if (!document.location.href.includes("maisPje_ignorar_trocaPerfil")) {
				mudarPerfil();
			}
			addBotaoTelaPrincipal();
			kaizen('PRINCIPAL');
		}

		if (document.location.href.includes("/tarefa") || document.location.href.includes("/movimentar")) {
			if (preferencias.tempBt.length > 0) {
				posicionarJanelaTarefas(preferencias.desativarAjusteJanelas);
				if (preferencias.tempBt[0] == "acao_bt_aaDespacho") {	
					fundo(true);
					monitor_janela_tarefa();
					acao_bt_aaDespacho(preferencias.tempBt[1]);
					browser.runtime.sendMessage({tipo: 'storage_limpar', valor: 'tempBt'});
				}
				
				if (preferencias.tempBt[0] == "acao_bt_aaMovimento") {	
					fundo(true);
					acao_bt_aaMovimento(preferencias.tempBt[1]);
					browser.runtime.sendMessage({tipo: 'storage_limpar', valor: 'tempBt'});
				}
				
			} else {
				posicionarJanelaTarefas(preferencias.desativarAjusteJanelas);
				addBotaoTarefas();
				kaizen('TAREFAS');				
				if (preferencias.grau_usuario == 'segundograu') { incluirPrazoRelator() } //pjeKz
				monitor_janela_tarefa();
				
				if (preferencias.gigsAbrirDetalhes) {
					//DESCRIÇÃO: Esse If a seguir, é responsável pela abertura automática da janela DETALHES a partir da janela TAREFAS de acordo com as preferências do usuário,		
					//exceto se o usuário navegar pelo fluxo (o último acontece por causa da mistura entre os sistemas KZ e o legado).
					if (document.referrer.search("/detalhe") == -1 && document.referrer.search("movimentar") == -1 && document.referrer.search("/tarefa") == -1) {	
						console.log("Extensão maisPJE (" + agora() + "): abrirDetalhesProcesso() - a partir de TAREFAS");
						abrirDetalhesProcesso();			
					}
				}
				
				if (document.location.href.includes("/minutar") || document.location.href.includes("/assinar")) {
					await addZoom_Editor(); //INCLUI O BOTÃO DE ZOOM NO EDITOR DE TEXTOS
				} else  if (document.location.href.includes("/comunicacoesprocessuais/")) {
					inserirParte_BB_CEF();
				} else  if (document.location.href.includes("/sobrestamento/aguardandofinal")) {
					// analisarMotivosSobrestamento();
				}
				
				if (document.location.href.includes("/475")) { //475 é o ID da Tarefa Conclusão ao Magistrado
					//este if serve apenas para os casos do processo já estar na tarefa de conclusão a magistrado. 
					//a transição entre tarefas a função acionada é a do document.body.addEventListener('focusout'
					filtroMagistrado();
				}
			}
			
		//ENDEREÇO DA PÁGINA: DETALHES
		} else if (document.location.href.includes("/detalhe") && !document.location.href.includes("/calculo")) {
			posicionarJanelaDetalhes(preferencias.desativarAjusteJanelas);			
			addBotaoDetalhes();
			kaizen('DETALHES');
			
			if (preferencias.AALote.length == 0) { monitor_documento_JanelaDetalhes() }			
			
			//DESCRIÇÃO: Abre a janela GIGS.
			if (preferencias.gigsAbrirGigs && preferencias.AALote.length == 0) { // não executar quando vem de lote
				await sleep(100);
				console.log("Extensão maisPJE (" + agora() + "): abrirGigs()");
				let idProcesso = document.location.href.substring(document.location.href.search("/processo/")+10, document.location.href.search("/detalhe"));
				abrirGigs(idProcesso);
			}
			
			if (preferencias.gigsOcultarChips && preferencias.AALote.length == 0) { // não executar quando vem de lote
				console.log("Extensão maisPJE (" + agora() + "): gigsEsconderChips() - a partir de DETALHES");
				ocultarChips();
			}
			
			if (preferencias.gigsOcultarLembretes && preferencias.AALote.length == 0) { // não executar quando vem de lote
				console.log("Extensão maisPJE (" + agora() + "): gigsRecolherLembretes() - a partir de DETALHES");
				ocultarLembretes();
			}
			
			if (preferencias.gigsCriarMenu && preferencias.AALote.length == 0 && preferencias.tempBt.length == 0) { // não executar quando vem de vinculo ou de lote
				console.log("Extensão maisPJE (" + agora() + "): gigsCriarMenu() - a partir de DETALHES");
				gigsCriarMenu();
			}
			
			//DESCRIÇÃO: Aprecia petições automaticamente de acordo com as preferências do usuário.		
			if (preferencias.gigsApreciarPeticoes && preferencias.AALote.length == 0 && preferencias.tempBt.length == 0) { // não executar quando vem de vinculo ou de lote
				console.log("Extensão maisPJE (" + agora() + "): apreciarPeticoes() - a partir de DETALHES");
				apreciarPeticoes();
			}
			
			//DESCRIÇÃO: Abre a janela TAREFAS, exceto se sua origem não for a janela TAREFAS.
			if (preferencias.gigsAbrirTarefas && !document.referrer.includes("/tarefa")) {
				//DESCRIÇÃO: Essa condicional serve para a JANELA TAREFA abrir mais rápido quando se deseja abrir a TAREFA sem o GIGS
				console.log("Extensão maisPJE (" + agora() + "): abrirTarefasProcesso() - a partir de DETALHES");
				abrirTarefasProcesso();
			}
			
			//DESCRIÇÃO: identifica se o GIGs está aberto na janela e insere os botões
			addBotaoGigs();
			
			//DESCRIÇÃO: insere o botão de busca personalizada na timeline
			addBotaoBotaoBuscaPersonalizada()
			
			//DESCRIÇÃO: identifica se a tela de alertas abriu
			addBotaoFecharAlertasEmLote();

			if (preferencias.AALote.length > 0) {
				console.log("Extensão maisPJE (" + agora() + "): Ações Automatizadas em Lote");
				fundo(true);
				acao_vinculo(preferencias.AALote);
			}
			
		//ENDEREÇO DA PÁGINA: GIGS
		} else if (document.location.href.includes("pjekz/gigs/abrir-gigs")) {
			addBotaoGigs();
			iniciarMonitorGigs();
			
		//ENDEREÇO DA PÁGINA: ANEXAR DOCUMENTOS EM DETALHES
		} else if (document.location.href.includes("/anexar")) {	
			if (preferencias.tempBt.length > 0) {
				if (preferencias.tempBt[0] == "acao_bt_aaAnexar") {	
					fundo(true);				
					acao_bt_aaAnexar(preferencias.tempBt[1]);
					browser.runtime.sendMessage({tipo: 'storage_limpar', valor: 'tempBt'});
				}
			}
			posicionarJanelaTarefas(preferencias.desativarAjusteJanelas);
			// ajustarColuna("70%");
			monitor_janela_anexar();//cria monitor para identificar a assinatura e a atualização automatica d janela detalhes
			await addZoom_Editor(); //INCLUI O BOTÃO DE ZOOM NO EDITOR DE TEXTOS
			
		//ENDEREÇO DA PÁGINA: COMUNICAÇÕES E EXPEDIENTES
		} else if (document.location.href.includes("/comunicacoesprocessuais/")) {
			inserirParte_BB_CEF(); //parei aqui o refatoramento do código
			
			if (preferencias.tempBt.length > 0) {
				if (preferencias.tempBt[0] == "acao_bt_aaComunicacao") {	
					fundo(true);				
					acao_bt_aaComunicacao(preferencias.tempBt[1]);
					browser.runtime.sendMessage({tipo: 'storage_limpar', valor: 'tempBt'});
				}
			}
		
		//ENDEREÇO DA PÁGINA: RETIFICAR AUTUAÇÃO
		} else if (document.location.href.includes("/retificar")) {
			
			monitor_janela_retificar_autuacao();
			
			if (preferencias.tempBt.length > 0) {
				if (preferencias.tempBt[0] == "acao_bt_retificarAutuacao") {	
					acao_bt_retificarAutuacao(preferencias.tempBt[1]);
					browser.runtime.sendMessage({tipo: 'storage_limpar', valor: 'tempBt'});
				}
			}
		
		} else if (document.location.href.includes("/pessoa-fisica?perito")) {
			await clicarBotao('mat-select[name="especializacao"]');
			await clicarBotao('mat-option[role="option"]','Perito');
		} else if (document.location.href.includes("/pessoa-fisica?advogado")) {
			await clicarBotao('mat-select[name="especializacao"]');
			await clicarBotao('mat-option[role="option"]','Advogado');
			
		//DETALHES DO PROCESSO: OBRIGAÇÕES DE PAGAR
		} else if (document.location.href.includes("/obrigacao-pagar/")) {
			let ancora = await esperarElemento('a[mattooltip="Incluir obrigação de pagar"]');
			if (ancora) {
				ancora.addEventListener('click', async function(event) {
					await registrarObrigacaoDePagar();
				});
				ancora.click();
			}
		} else if (document.location.href.includes("/pagamento/")) {
			let ancora = await esperarElemento('a[mattooltip="Incluir pagamento"]');
			if (ancora) {
				ancora.addEventListener('click', async function(event) {
					await registrarObrigacaoDePagar();
				});
				ancora.click();
			}
		
		} else if (document.location.href.includes("/comunicacoesprocessuais/minutas")) {
			inserirParte_BB_CEF();
		} else {
			console.log('1000')
		}
	
	
	
	
	//TAREFAS pje antigo
	} else if (document.location.href.includes("/Processo/movimentar.seam")) { 
		if (document.location.href.includes("/segundograu/")) {
			incluirPrazoRelator(); //pjeKz
			
			//Ação Automatizada em vínculo no segundo grau com a  tela do PJe1.0			
			if (preferencias.tempAR) {
				let guardarStorage = browser.storage.local.set({'tempAR': ''});
				Promise.all([guardarStorage]).then(values => {
					browser.runtime.sendMessage({tipo: 'storage_vinculo', valor: preferencias.tempAR});					
					window.close();					
				});
			}
		}
		
		if (document.location.href.includes("/primeirograu/")) { // movimentar em lote processos do pje antigo
			if (preferencias.tempBt[0] == "acao_bt_aaMovimento") {	
				fundo(true);
				acao_bt_aaMovimento(preferencias.tempBt[1]);
				browser.runtime.sendMessage({tipo: 'storage_limpar', valor: 'tempBt'});
			}
		}
	
	//ENDEREÇO DA PÁGINA: DETALHES NO PJE ANTIGO 
	} else if (document.location.href.includes(preferencias.grau_usuario + "/Processo/ConsultaProcesso/Detalhe/") && document.location.href.includes("baixar=true")) {
		acao1();
		
		function acao1() {
			let check = setInterval(function() {
				if (document.querySelector('a[title="Download de documentos em PDF"]')) {
					clearInterval(check);
					document.querySelector('a[title="Download de documentos em PDF"]').click();
					acao2();
				}
			}, 100);
		}
		
		function acao2() {
			let check = setInterval(function() {
				if (document.querySelector('input[value="Gerar PDF"]')) {
					clearInterval(check);
					document.querySelector('input[value="Gerar PDF"]').click();
				}
			}, 100);
		}
	
	//PAUTA DE SEGUNDO GRAU
	} else if (document.location.href.includes(preferencias.grau_usuario) && document.location.href.includes("/PautaJulgamento/pautaPopUp.seam")) {
		obterImpedimentosSuspeicoesPautaSegundoGrau();
		obterSegredoDeJustica();
		
	} else if (document.location.href.includes(preferencias.grau_usuario) && document.location.href.includes("/SecretarioSessao/include/popupPainelSecretarioSessao.seam")) {
		obterSegredoDeJustica();
		
	//ENDEREÇO DA PÁGINA: CONSULTA PJE ANTIGO passando por parametro o nome da parte
	} else if (document.location.href.includes('/Processo/ConsultaProcesso/listView.seam') && document.location.href.includes('nomeautor') && document.location.href.includes("garimpo")) {
		let nomeautor = document.location.href.substring(document.location.href.search('nomeautor=')+10, document.location.href.length);
		nomeautor = nomeautor.replace('&garimpo', '');
		let check = setInterval(function() {
			if (document.querySelector('input[id*=":nomeParte"]')) {				
				clearInterval(check);
				let el = document.querySelector('input[id*=":nomeParte"]');
				el.focus();
				el.value = nomeautor.replace(/%20/g, ' ');
				triggerEvent(el, 'input');
				acao1();
			}
		}, 100);
		
		function acao1() {
			document.querySelector('input[value*="Pesquisar"]').click();
			acao2();
		}
		
		function acao2() {
			let check2 = setInterval(function() {
				if (!document.getElementById('consultaProcessoViewList:tb')) { return }
				if (!document.getElementById('consultaProcessoViewList:tb').querySelector('tr')) { return }
				if (!document.getElementById('consultaProcessoViewList:tb').querySelector('tr').innerText) { return }
				let el = document.getElementById('consultaProcessoViewList:tb').querySelector('tr').innerText;
				if (el) {
					clearInterval(check2);
					let processoNumero = el.match(new RegExp('\\d{7}-\\d{2}\\.\\d{4}\\.\\d{1,2}\\.\\d{1,2}\\.\\d{4}','g')).join();
					// let textarea = document.createElement("textarea");
					// textarea.textContent = processoNumero;
					// document.body.appendChild(textarea);
					// textarea.select();
					// document.execCommand("copy");
					// document.body.removeChild(textarea);
					navigator.clipboard.writeText(processoNumero);
					browser.runtime.sendMessage({tipo: 'criarAlerta', valor: processoNumero + ' copiado!! Use o (CTRL + V)!!', icone: '6'});					
				}
			}, 100);
		}
	
	//ENDEREÇO DA PÁGINA: PJECALC
	} else if (document.location.href.includes("/pjecalc/")) {
		if (!preferencias.modulo9.pjecalc) { return }

		//cria o event listener do esc
		document.body.addEventListener('keydown', async function(event) {
			if (event.code === "Escape") {
				//Cancela o fundo que bloqueia a página
				fundo(false);
				console.log('maisPJe: ESC pressionado...')
				//limpa a memória da ação automatizada em lote
				browser.runtime.sendMessage({tipo: 'storage_limpar', valor: 'tempBt,tempAR,AALote,tempAAEspecial,anexadoDoctoEmSigilo'}); //preferencias.anexadoDoctoEmSigilo
				preferencias.tempBT = [];
				preferencias.tempAR = '';
				preferencias.tempAAEspecial = [];
				preferencias.AALote = '';
				preferencias.anexadoDoctoEmSigilo = -1;
			}
		});
		
		console.log("Extensão maisPJE (" + agora() + "): correios");
		
		let estaOffLine = await esperarElemento('h1','503 Service Unavailable',1000);
		let erroServidor = document.querySelector('div[class="conteudoErro"]');
		if (estaOffLine || erroServidor) { 
			
			let guardarStorage = browser.storage.local.set({'tempAR': ''});
			Promise.all([guardarStorage]).then(values => { 
				fundo(false);
				return;
			});			
			
		}
		
		monitor_janela_PJeCalc();
		
		// if (preferencias.tempAR == 'atualizacaorapida') { await clicarBotao('a[title="Buscar Cálculo"]') }
		if (document.location.href.includes("?maisPje=atualizacaorapida")) {
			browser.runtime.sendMessage({tipo: 'storage_guardar', chave: 'tempAR', valor: 'atualizacaorapida'});
			await clicarBotao('a[title="Buscar Cálculo"]');
		} else {
			await clicarBotao('a[title="Buscar Cálculo"]');
		}
		
	//ENDEREÇO DA PÁGINA: PROTESTOJUD
	} else if (document.location.href.includes("cenprotsc") && document.location.href.includes("titulo/cadastro")) {
		if (!preferencias.modulo9.protestojud) { return }
		if (!document.getElementById('maisPje_menuConvenios')) {
			menuConvenios("PROTESTOJUD");
		}
		
	
	//ENDEREÇO DA PÁGINA: PREVJUD
	} else if (document.location.href.includes("previdenciario.pdpj.jus.br")) {
		if (!preferencias.modulo9.prevjud) { return }
		if (!document.getElementById('maisPje_menuConvenios')) {
			menuConvenios("PREVJUD");
		}
		
	//ENDEREÇO DA PÁGINA: CORREIOS
	} else if (document.location.href.includes("correios.com.br")) {
		console.log("Extensão maisPJE (" + agora() + "): correios");
		correios();
		
	//ENDEREÇO DA PÁGINA: E-CARTA
	} else if (document.location.href.includes("/eCarta-web/")) {
		console.log("Extensão maisPJE (" + agora() + "): e-carta");
		let var1 = browser.storage.local.get('processo_memoria', function(result){
			if (!result.processo_memoria.numero) {return}
			if (document.getElementById('main:processoCNJ')) {
				let el1 = document.getElementById('main:processoCNJ');
				el1.focus();
				el1.value = result.processo_memoria.numero;
				triggerEvent(el1, 'input');
				el1.blur();
				
				let el2 = document.getElementById('main:gerarRelatorio');
				el2.focus();
				el2.click();
			}
		});
		
		if (true) {
			document.addEventListener("DOMContentLoaded", function(event) { 
				document.body.dispatchEvent(simularTecla('keydown',40)); //SETA PRA BAIXO
			});
		}
		
	//ENDEREÇO DA PÁGINA: RELATÓRIOS SAO	
	} else if (document.location.href.includes("/sao/execucao/") || document.location.href.includes("/sao/acesso-negado") || document.location.href.includes("/sao/login")) {
		if (document.location.href.includes("maisPje")) {			
			
		} else {
			if (document.location.href.includes("/sao/acesso-negado") || document.location.href.includes("/sao/login")) {
				fundo(true);
				await clicarBotao('a[href="/sao/"]');				
				fundo(false);
			}
		}
	
	//ENDEREÇO DA PÁGINA: PLANILHAS GOOGLE
	} else if (document.location.href.includes("docs.google.com/spreadsheets")) {
		addBotaoPlanilhasGoogle();
	
	//ENDEREÇO DA PÁGINA: SISBAJUD
	} else if (document.location.href.includes("sisbajud.cnj.jus.br") || document.location.href.includes("sisbajud.cloud.pje.jus.br")) {
		if (!preferencias.modulo9.sisbajud) { return }
		if (!document.getElementById('maisPje_menuConvenios')) {
			console.log("SISBAJUD");
			menuConvenios("SISBAJUD");
		}
	
	//ENDEREÇO DA PÁGINA: CCS
	} else if (document.location.href.includes("bcb.gov.br/ccs")) {
		if (!preferencias.modulo9.ccs[0]) { return }
		
		if (!document.getElementById('maisPje_menuConvenios')) {
			
			let segundos = !preferencias.modulo9.ccs[5] ? 5 : preferencias.modulo9.ccs[5];
			
			if (document.location.href.includes('maisPje=preencherCampos')) {
				await menuConvenios("CCS","preencherCampos");
			} else {
				await menuConvenios("CCS");
				
				//CONFIRMAÇÃO DE CONSULTA
				if (document.location.href.includes('validarParametrosRequisicaoCpfCnpj.do?method=validarParametrosRequisicao')) {
					await clicarBotao('input[name="assinaturaTermoResponsabilidade"]');					
					let bt_continuar = await esperarElemento('input[value="Requisitar Consulta"]');
					bt_continuar.focus();
					if (preferencias.modulo9.ccs[2]) { await timer(bt_continuar, segundos, 'orangered') }
				}				
				
				//Resultado de requisitar consulta
				if (document.location.href.includes('confirmarConsultaCpfCnpj.do?method=requisitar')) {					
					let bt_continuar = await esperarElemento('input[value="Solicitar Detalhamentos dos CPF/CNPJ Consultados"]');
					bt_continuar.focus();
					if (preferencias.modulo9.ccs[3]) { await timer(bt_continuar, segundos, 'orangered') }
				}
				
				//Solicitação de detalhamentos dos CPF/CNPJ consultados
				if (document.location.href.includes('solicitarDetalhamentoVisualizacao.do?method=solicitarDetalhamento')) {					
					let bt_continuar = await esperarElemento('input[value="Solicitar Detalhamentos"]');
					bt_continuar.focus();
					if (preferencias.modulo9.ccs[4]) { await timer(bt_continuar, segundos, 'orangered') }					
				}
				
				if (document.location.href.includes('solicitarDetalhamentoCpfCnpj.do?method=solicitarDetalhamento')) {
					//copiar numero da ordem
					let el = await esperarElemento('form[name="solicitarDetalhamentoCpfCnpjForm"]');
					el = el.querySelectorAll('td')[2];
					if (!el || el.length == 0) { return }					
					let padrao = /\d{15,}/gm;				
					if (padrao.test(el.innerText)) {
						el.classList.add('maisPje_destaque_elemento_on');
						el.classList.remove('maisPje_destaque_elemento_off');
						let textocopiado = el.innerText.match(padrao).join();
						// let ta = document.createElement("textarea");
						// ta.textContent = textocopiado;
						// document.body.appendChild(ta);
						// ta.select();
						// document.execCommand("copy");
						// document.body.removeChild(ta);
						navigator.clipboard.writeText(textocopiado);
						browser.runtime.sendMessage({tipo: 'criarAlerta', valor: 'Número da ordem CCS (' + textocopiado + ') copiada para a memória (CTRL + C)!!\n Use apenas CTRL + V para guardar essa informação..', icone: '5'});								
						setTimeout(async function() { 
							el.classList.add('maisPje_destaque_elemento_off');
							el.classList.remove('maisPje_destaque_elemento_on');
						}, 1000);				
					}
				}
			}
		}
	//ENDEREÇO DA PÁGINA: CNIB
	} else if (document.location.href.includes("indisponibilidade.org.br")) {
		if (!preferencias.modulo9.cnib) { return }
		console.log("CNIB");
		if (!document.getElementById('maisPje_menuConvenios')) {
			menuConvenios("CNIB");
		}
		
		if (document.location.href.includes("indisponibilidade.org.br") && (document.location.href.includes("ordem/cancelamento/") || document.location.href.includes("/ordem/consulta/"))) {
			let var1 = browser.storage.local.get('processo_memoria', function(result){
				if (!result.processo_memoria.numero) {return}
				if (document.getElementById('ordem-processo-numero')) {
					let el = document.getElementById('ordem-processo-numero');
					el.focus();
					el.value = result.processo_memoria.numero;
					triggerEvent(el, 'input');
					el.blur();
				}
				
				if (document.location.href.includes("ordem/cancelamento/")) {
					browser.storage.local.get('tempAR', function(result){
						preferencias.tempAR = result.tempAR;						
						if (preferencias.tempAR == 'excluir CNIB') {
							document.querySelector('form[id="form-consulta"] button').click();
							browser.storage.local.set({'tempAR': ''});
						}
					});
				}
			});
		}
	
	//ENDEREÇO DA PÁGINA: RENAJUD	
	} else if (document.location.href.includes("renajud.denatran.serpro.gov.br/renajud")) {
		if (!preferencias.modulo9.renajud) { return }
		console.log('RENAJUD');
		if (!document.getElementById('maisPje_menuConvenios')) {
			menuConvenios("RENAJUD");
		}
		
		let var1 = browser.storage.local.get('processo_memoria', function(result){
			if (!result.processo_memoria.numero) {return}
			if (document.getElementById('form-pesq:campo-processo') || document.getElementById('campo-processo')) {
				let el = document.getElementById('form-pesq:campo-processo') || document.getElementById('campo-processo');
				el.focus();
				el.value = result.processo_memoria.numero;
				triggerEvent(el, 'input');
				el.blur();
			}
		});		
	
	//ENDEREÇO PAGINA: RENAJUD NOVO
	} else if (document.location.href.includes("renajud.pdpj.jus.br") && !document.location.href.includes("blob")) {
		if (!preferencias.modulo9.renajud) { return }
		console.log('RENAJUD NOVO');
		if (!document.getElementById('maisPje_menuConvenios')) {
			menuConvenios("RENAJUDNOVO");
			await assistenteDeImpressao();
		}
	
	//ENDEREÇO DA PÁGINA: SERASAJUD ANTIGO
	} else if (document.location.href.includes("serasa.com.br/SerasaJudicial/CadastrarOficios")) {
		if (!preferencias.modulo9.serasajud) { return }
		console.log('SERASAJUD - Antigo');
		let var1 = browser.storage.local.get('processo_memoria', async function(result){
			if (!result.processo_memoria.numero) {return}
			
			let el = await esperarElemento('input[id="ctl00_Conteudo_txtNumeroProcesso"]');
			if (!el) { return }				
			el.focus();
			el.value = result.processo_memoria.numero;
			triggerEvent(el, 'input');
			el.blur();
			
			let janelaDePreenchimento = await esperarElemento('div[id="ctl00_Conteudo_modalBenef_foregroundElement"]');
			
			if (janelaDePreenchimento.style.display.includes('none')) { return }

			console.log("      |___INSERÇÃO DOS RÉUS: SERASAJUD ANTIGO");
			let lista_de_executados = await criarCaixaDeSelecaoComReclamados(false);
			fundo(true);
			if (!lista_de_executados) { return }			
			//SÓ PERMITE CADASTRAR UM POR VEZ
			console.log("      |___" + lista_de_executados[0].nome + " ( " + lista_de_executados[0].cpfcnpj + ")");
			await preencherInput('input[id="ctl00_Conteudo_txtNomeBenef"]', lista_de_executados[0].nome);
			
			let elSelect = await esperarElemento('select[id="ctl00_Conteudo_ddlTipoPessoaBenef"]');
			if (lista_de_executados[0].cpfcnpj.length > 14) { //CNPJ
				elSelect.value = 1;
			} else { //CPF
				elSelect.value = 0;
			}
			triggerEvent(el, 'change');			
			await preencherInput('input[id="ctl00_Conteudo_txtCPFBeneficiario"]', lista_de_executados[0].cpfcnpj);
			await clicarBotao('input[id="ctl00_Conteudo_btnOk"]');
			await preencherInput('input[id="ctl00_Conteudo_txtCPFBeneficiario"]', lista_de_executados[0].cpfcnpj);
			await clicarBotao('input[id="ctl00_Conteudo_btnOk"]');
			fundo(false)
		});
		
	//ENDEREÇO DA PÁGINA: SERASAJUD NOVO
	} else if (document.location.href.includes("serasa-judicial.serasaexperian")) {
		if (!preferencias.modulo9.serasajud) { return }
		menuConvenios("SERASAJUD");
	
	//ENDEREÇO DA PÁGINA: CRCJUD
	} else if (document.location.href.includes("sistema.registrocivil.org.br/crcjud")) {
		if (!preferencias.modulo9.crcjud) { return }
		console.log('ARPEN - CRCJUD');
		monitor_janela_crcjud();
		await assistenteDeImpressao();
		
	//ENDEREÇO DA PÁGINA: ONR - PENHORA ONLINE
	} else if (document.location.href.includes("penhoraonline.org.br")) {
		if (!preferencias.modulo9.onr) { return }
		console.log('ONR - PENHORA ONLINE');
		monitor_janela_onr();
	
	//ENDEREÇO DA PÁGINA: SNIPER
	} else if (document.location.href.includes("sniper.pdpj.jus.br") && !document.location.href.includes("blob:")) {
		// console.log('entrou');
		let ancora = await esperarElemento('mat-sidenav-container', null, 1000); //serve para ignorar as páginas de representação das relações
		if (!ancora) { 
			document.body.setAttribute("maisPje-impressao","true");
			await assistenteDeImpressao();
			
		} else {
			
			if (!document.getElementById('maisPje_menuConvenios')) {
				console.log("SNIPER");
				menuConvenios("SNIPER");
			}
			
			await assistenteDeImpressao();			
		}
		
	//ENDEREÇO DA PÁGINA: CASAN
	} else if (document.location.href.includes("casan-ws")) {
		if (!document.getElementById('maisPje_menuConvenios')) {
			console.log("CASAN");
			menuConvenios("CASAN");
		}
		await assistenteDeImpressao();
		
	//ENDEREÇO DA PÁGINA: CELESC
	} else if (document.location.href.includes("celesc.com.br/consulta")) {
		if (!document.getElementById('maisPje_menuConvenios')) {
			console.log("CELESC");
			menuConvenios("CELESC");
		}
		await assistenteDeImpressao();
		
	//ENDEREÇO DA PÁGINA: CENSEC
	} else if (document.location.href.includes("censec.org.br/private")) {
		if (!document.getElementById('maisPje_menuConvenios')) {
			console.log("CENSEC");
			menuConvenios("CENSEC");
		}
		await assistenteDeImpressao();
	
	//ENDEREÇO DA PÁGINA: SIGEF
	} else if (document.location.href.includes("sigef.incra.gov.br/consultar/parcelas/")) {
		if (!document.getElementById('maisPje_menuConvenios')) {
			console.log("SIGEF");
			menuConvenios("SIGEF");
		}
		await assistenteDeImpressao();
	
	//ENDEREÇO DA PÁGINA: INFOSEG
	} else if (document.location.href.includes("infoseg.sinesp.gov.br/infoseg2")) {
		if (!document.getElementById('maisPje_menuConvenios')) {
			console.log("INFOSEG");
			menuConvenios("INFOSEG");
		}
		await assistenteDeImpressao();
		
	//ENDEREÇO DA PÁGINA: GPREC
	} else if (document.location.href.includes(".jus.br/gprec/")) {
		if (!preferencias.modulo9.gprec) { return }
		console.log('GPREC');
		await incluirBotoesGPREC();
				
		let var1 = browser.storage.local.get('processo_memoria', async function(result){	
			if (!result.processo_memoria.numero) {return}
			//Nova RP
			if (document.location.href.includes("gprec/view/private/solicitacao/solicitacao_cadastro")) {
				let check = setInterval(function() {
					if (document.getElementById('tabGeral:inNrProc')) {
						clearInterval(check);
						let el = document.getElementById('tabGeral:inNrProc');
						el.value = result.processo_memoria.numero;
						triggerEvent(el, 'input');
					}
				}, 200);
			}
			
			//consultar pagamento RPV e consultar listade RPVS expedidos
			if (document.location.href.includes("gprec/view/private/rpv/rpv") && document.location.href.includes("_lista.xhtml")) {
				await preencherInput('input[id="inNrProc"]', result.processo_memoria.numero);
				await clicarBotao('button[id="btnRpvPagListBuscar"], button[id="btnRpPesquisar"]');
				await sleep(1000);
				inserirBotaoBusca();
			}
		});
		
		//atribui ao botão limpar a possibilidade
		async function inserirBotaoBusca() {
			let ancora = await esperarElemento('button','Limpar',2000);
			if (!ancora) { return }
			if (document.getElementById('maisPJe_GPREC_botao_Busca')) { return }
			ancora = ancora.parentElement;			
			let bt = document.createElement('button');
			bt.id = 'maisPJe_GPREC_botao_Busca'
			bt.className = "ui-button ui-widget ui-state-default ui-corner-all ui-button-text-icon-left";
			bt.style = "margin-left: 8%;";
			let span1 = document.createElement('span');
			span1.className = "ui-button-icon-left ui-icon ui-c ui-icon-refresh";			
			let span2 = document.createElement('span');
			span2.className = "ui-button-text ui-c";
			span2.innerText = "maisPje: Buscar da memória";
			bt.appendChild(span1);
			bt.appendChild(span2);			
			bt.onclick = function () { window.location.reload() }
			ancora.appendChild(bt);
			
			let check = setInterval(function() {
				if (!document.getElementById('maisPJe_GPREC_botao_Busca')) { 
					clearInterval(check);
					inserirBotaoBusca();
				}
			}, 10000);
		}
	
	//ENDEREÇO DA PÁGINA: SIGEO AJJT
	} else if (document.location.href.includes("aj.sigeo.jt.jus.br")) {
		if (!preferencias.modulo9.ajjt) { return }
		if (!document.getElementById('maisPje_menuConvenios')) {
			menuConvenios("AJJT");
			ajjt();
		}
		
	//ENDEREÇO DA PÁGINA: SIF
	} else if (document.location.href.includes(".jus.br/sif")) {
		if (document.location.href.includes("/sif/consultar-extrato/")) {
			
			let el = await esperarElemento('a[placeholder*="voltar para a tela anterior"]');
			
			if (document.location.href.includes("maisPJe_SIF_bt_extrato")) {
				let inicio = document.location.href.match(new RegExp(/\d{2}[.]\d{2}[.]\d{4}/g)).join();
				inicio = inicio.replace(new RegExp(/[.]/g),'/');
				let dNow = new Date();
				let fim = ("0" + dNow.getDate()).slice(-2) + '/' + ("0" + (dNow.getMonth()+1)).slice(-2) + '/' + dNow.getFullYear();
				acao1(inicio, fim);
			} else if (!document.getElementById('maisPJe_SIF_bt_extrato_90')) {
				let ancora = el.parentElement;
				//INSERE O BOTAO DE AUTOMATIZAR
				let bt_extrato_90_dias = document.createElement("button");
				bt_extrato_90_dias.id = "maisPJe_SIF_bt_extrato_90";
				bt_extrato_90_dias.className = "mat-focus-indicator naoImprimir mat-raised-button mat-button-base mat-primary";
				bt_extrato_90_dias.style = "margin-top: 20px;";
				bt_extrato_90_dias.onclick = function () {
					let dNow = new Date();
					let dNow90a = new Date();
					dNow90a.setDate(dNow.getDate() - 90);
					acao1(("0" + dNow90a.getDate()).slice(-2) + '/' + ("0" + dNow90a.getMonth()).slice(-2) + '/' + dNow90a.getFullYear(), ("0" + dNow.getDate()).slice(-2) + '/' + ("0" + (dNow.getMonth()+1)).slice(-2) + '/' + dNow.getFullYear())
				};
				let span = document.createElement("span");
				span.textContent = 'MaisPje: Extrato de 90 dias';
				bt_extrato_90_dias.appendChild(span);
				ancora.appendChild(bt_extrato_90_dias);
			}
			
			async function acao1(dt_inicio, dt_fim) {
				fundo(true);
				let el = await esperarElemento('input[formcontrolname="dataInicio"]');
				el.value = dt_inicio;
				triggerEvent(el, 'input');
				acao2(dt_fim);
			}
			
			async function acao2(dt_fim) {
				let el = await esperarElemento('input[formcontrolname="dataFim"]');
				el.value = dt_fim;
				triggerEvent(el, 'input');
				acao3();
			}
			
			async function acao3() {
				//copia o número da conta judicial para a memoria (ctrl + c) 
				let texto = document.querySelector('mat-grid-list').innerText;
				let padrao = /\d{4}\.\d{3}\.\d{8}\-\d{1}/g; //3521/042/01501234-0
				if (padrao.test(texto)) {
					navigator.clipboard.writeText(texto.match(padrao).join());
				}				

				let el = await clicarBotao('button[placeholder*="consultar extrato"]');
				fundo(false);
				await esperarTransicaoSIF();
				acao4();
			}
			
			async function acao4() {				
				await esperarConferenciaAlvaraSif('Imprimir Extrato');
				window.close();
			}
		
		} else if (document.location.href.includes("/boleto/novo")) {
			let var1 = browser.storage.local.get('processo_memoria', async function(result){
				fundo(true);
				
				let el = await esperarElemento('input[aria-label="Digite o número do processo"]');
				el.value = result.processo_memoria.numero;
				triggerEvent(el, 'input');
				
				fundo(false);
			
			});
			
		} else {
			if (!preferencias.modulo9.sif) { return }
			monitor_janela_sif();
			
			if (document.location.href.includes("?conferir")) {
				fundo(true);
				await esperarTransicaoSIF();
				await escolherOpcaoTeste('mat-select[aria-label="Items per page:"], pje-paginador mat-select[aria-labelledby="mat-select-value-7"]','30');
				await esperarTransicaoSIF(5000);
				
				let listaDeAlvaras = await esperarColecao('button[mattooltip="Conferir"]:not([disabled="true"])');
				let listaDeConferidor = await esperarColecao('td[class*="mat-column-nomeConferidor"]');
				
				for (const [pos, alvara] of listaDeAlvaras.entries()) {
					// console.log(alvara.className.includes('mat-button-disabled'))
					// console.log(listaDeConferidor[pos].innerText.length)
					if (!alvara.className.includes('mat-button-disabled') || listaDeConferidor[pos].innerText.length < 3) {
						await clicarBotao(alvara);
						fundo(false);
						await esperarConferenciaAlvaraSif('Conferir e Salvar');
						fundo(true);
					}					
				}
				await esperarTransicaoSIF();
				await sleep(1000);
				window.close();
			}
		}
	
	//PÁGINA DE CONFERÊNCIA DE ALVARÁ SIF
	} else if (document.title.includes('maisPJe - ALVARÁS AGUARDANDO_CONFERENCIA')) {
		
		let tabela = await esperarColecao('tbody tr[title="Processo em outro Órgão Julgador"]', 1);
		let map = [].map.call(
			tabela, 
			function(linha) {
				let atalho = linha.querySelector('td a[id*="numeroProcesso:"]')
				let padrao = /\d{7}\-\d{2}\.\d{4}\.\d{1}\.\d{2}\.\d{4}/g;				
				if (padrao.test(atalho.id)) {
					let numeroFormatado = atalho.id.match(padrao).join();
					atalho.onclick = function() {
						this.style.textDecoration = 'line-through';
						consultaRapidaPJE(numeroFormatado)
					}						
				}
			}
		);
	
	//ENDEREÇO DA PÁGINA: SISCONDJ
	} else if (document.location.href.includes(preferencias.configURLs.idSiscondj)) {
		if (!preferencias.modulo9.siscondj) { return }
		console.log('SISCONDJ');
		
		let var1 = browser.storage.local.get('processo_memoria', function(result){			
			
			// CONSULTA DE CONTAS
			if (document.location.href.includes("/pages/movimentacao/conta/new")) {
				let check = setInterval(function() {
					if (document.getElementById('numeroProcesso')) {
						clearInterval(check);
						let el = document.getElementById('numeroProcesso');
						el.value = result.processo_memoria.numero;
						triggerEvent(el, 'input');
						el.addEventListener('click', function(event) { el.value = "" });				
						clicarBotao('input[id="bt_buscar"]');						
					}
				}, 200);
			}
			
			if (document.location.href.includes("/pages/movimentacao/conta/buscar")) {
				monitor_janela_siscondj();		
			}
		});
		
		// inclui atalho para o pje
		if (document.location.href.includes("/pages/mandado/pagamento/exibir")) {
			console.log('3')
			let check = setInterval(function() {
				let el = document.getElementById('table_processo');
				if (el) {
					clearInterval(check);
					consultaPJe(el.querySelectorAll('td'));
					document.getElementById('maisPJe_atalhoConsultaPJe').title = 'Consultar Processo no PJe (Atalho: F2)'
				}
			}, 200);
		}
	}
	
}

//CHECAR E FAZER VALIDAÇÃO DE VARIÁVEIS
async function checarVariaveis() {
	if (!preferencias) {
		return;
	}
	
	if (!preferencias.oj_usuario) {
		let ehServidor = await verificarSeServidor();
		ehServidor ? console.log('Usuário identificado como Servidor/Magistrado') : console.log('Usuário identificado como Advogado/Perito');
		if (!ehServidor) {
			preferencias.extensaoAtiva = false;
			browser.storage.local.set({'extensaoAtiva':false});
			browser.runtime.sendMessage({tipo: 'iconeNavegador', valor: '+PJe: Desligado', icone: 'ico_16_off.png'});
			return;
		}
	}
	
	preferencias.versao = typeof(preferencias.versao) == "undefined" ? "0" : preferencias.versao;
	preferencias.trt = typeof(preferencias.trt) == "undefined" ? "erro" : preferencias.trt;
	preferencias.nm_usuario = typeof(preferencias.nm_usuario) == "undefined" ? "" : preferencias.nm_usuario;
	preferencias.oj_usuario = typeof(preferencias.oj_usuario) == "undefined" ? "" : preferencias.oj_usuario;
	preferencias.grau_usuario = typeof(preferencias.grau_usuario) == "undefined" ? "" : preferencias.grau_usuario;
	preferencias.desativarAjusteJanelas = typeof(preferencias.desativarAjusteJanelas) == "undefined" ? true : preferencias.desativarAjusteJanelas;
	preferencias.videoAtualizacao = typeof(preferencias.videoAtualizacao) == "undefined" ? true : preferencias.videoAtualizacao;
	preferencias.perfilUsuario = typeof(preferencias.perfilUsuario) == "undefined" ? "" : preferencias.perfilUsuario;
	preferencias.atalhosPlugin = typeof(preferencias.atalhosPlugin) == "undefined" ? "SISBAJUD:https://sisbajud.cnj.jus.br/|Caged:https://caged.maisemprego.mte.gov.br/caged|CCS:https://www3.bcb.gov.br/ccs/dologin|Celesc:http://consumidor.celesc.com.br:8895/index.php/acesso|Cnib:https://www.indisponibilidade.org.br/autenticacao/|Honor\u00e1rios:http://www2.trt12.jus.br/ajg/intranet/entrada.asp|Intranet:https://intranet.trt12.jus.br/|Renajud:https://renajud.denatran.serpro.gov.br/renajud/login.jsf|Serasajud:https://sitenet05cert.serasa.com.br/SerasaJudicial/default.aspx|Siel:https://apps.tre-sc.jus.br/siel/index.php" : preferencias.atalhosPlugin;
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
	preferencias.gigsOcultarCabecalho = typeof(preferencias.gigsOcultarCabecalho) == "undefined" ? 0 : preferencias.gigsOcultarCabecalho;
	preferencias.gigsCriarMenu = typeof(preferencias.gigsCriarMenu) == "undefined" ? 0 : preferencias.gigsCriarMenu;
	preferencias.gigsPesquisaDeDocumentos = typeof(preferencias.gigsPesquisaDeDocumentos) == "undefined" ? 0 : preferencias.gigsPesquisaDeDocumentos;
	preferencias.maisPje_velocidade_interacao = typeof(preferencias.maisPje_velocidade_interacao) == "undefined" ? 1 : preferencias.maisPje_velocidade_interacao * 1000; //NA HORA DE USAR EU CONVERTO EM SEGUNDOS
	preferencias.aaAnexar = typeof(preferencias.aaAnexar) == "undefined" ? [] : preferencias.aaAnexar;
	preferencias.aaComunicacao = typeof(preferencias.aaComunicacao) == "undefined" ? [] : preferencias.aaComunicacao;
	preferencias.aaAutogigs = typeof(preferencias.aaAutogigs) == "undefined" ? [] : preferencias.aaAutogigs;
	preferencias.aaDespacho = typeof(preferencias.aaDespacho) == "undefined" ? [] : preferencias.aaDespacho;
	preferencias.aaMovimento = typeof(preferencias.aaMovimento) == "undefined" ? [] : preferencias.aaMovimento;
	preferencias.aaChecklist = typeof(preferencias.aaChecklist) == "undefined" ? [] : preferencias.aaChecklist;
	preferencias.aaVariados = typeof(preferencias.aaVariados) == "undefined" ? [{id:"Atualizar Pagina",nm_botao:"Atualizar Pagina",descricao:"AA para ATUALIZAR a janela DETALHES DO PROCESSO",temporizador:"1",ativar:true},{id:"Fechar Pagina",nm_botao:"Fechar Pagina",descricao:"AA para fechar a janela DETALHES DO PROCESSO",temporizador:"3",ativar:true},{id:"Apreciar Peticoes",nm_botao:"Apreciar Peticoes",descricao:"AA para apreciar petições na janela DETALHES DO PROCESSO",temporizador:"1",ativar:true},{id:"Atalho F2",nm_botao:"Atalho F2",descricao:"Funcionalidade do Menu KAIZEN: Permite ativar/desativar a criação de uma área na tela para acionar a tecla 'F2' ao repousar o mouse em cima pelo tempo ajustado no 'temporizador'.",temporizador:"2",ativar:true}] : preferencias.aaVariados;
	preferencias.meuFiltro = typeof(preferencias.meuFiltro) == "undefined" ? [] : preferencias.meuFiltro;
	preferencias.emailAutomatizado = typeof(preferencias.emailAutomatizado) == "undefined" ? new EmailAutomatizado("Processo n. #{processo} (#{tipoDocumento} Id. #{idDocumento})", "Encaminho o(a) #{tipoDocumento} (Id. #{idDocumento}), expedido no processo #{processo}, para ciência ou cumprimento.\n\nO documento poderá ser acessado via internet mediante o seguinte link: #{autenticacao}\n\nAtenciosamente,", "#{servidor}\nDiretor de Secretaria\n#{OJServidor}") : preferencias.emailAutomatizado;
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
	preferencias.atalhosDetalhes = typeof(preferencias.atalhosDetalhes) == "undefined" ? [true,true,true,false,true,false,true,false,false,true,false,false,true,false,true,false,false,false,true,false,false,true,false,false] : preferencias.atalhosDetalhes;
	preferencias.processo_memoria = typeof(preferencias.processo_memoria) == "undefined" ? "" : preferencias.processo_memoria;
	preferencias.tempAR = typeof(preferencias.tempAR) == "undefined" ? "" : preferencias.tempAR;
	preferencias.tempBt = typeof(preferencias.tempBt) == "undefined" ? [] : preferencias.tempBt;
	preferencias.tempAAEspecial = typeof(preferencias.tempAAEspecial) == "undefined" ? [] : preferencias.tempAAEspecial;
	preferencias.tempF2 = typeof(preferencias.tempF2) == "undefined" ? "" : preferencias.tempF2;
	preferencias.tempF3 = typeof(preferencias.tempF3) == "undefined" ? "" : preferencias.tempF3;
	preferencias.tempAuto = typeof(preferencias.tempAuto) == "undefined" ? 10 : preferencias.tempAuto;
	preferencias.monitorGIGS = typeof(preferencias.monitorGIGS) == "undefined" ? [] : preferencias.monitorGIGS;
	
	preferencias.sisbajud = typeof(preferencias.sisbajud) == "undefined" ? {juiz: '', vara: '', cnpjRaiz: '', teimosinha: '', contasalario: '', naorespostas: '', valor_desbloqueio: '', banco_preferido: '', agencia_preferida: '', preencherValor: '', confirmar: '', executarAAaoFinal: '', salvarEprotocolar: ''} : preferencias.sisbajud;
	preferencias.sisbajud.juiz = typeof(preferencias.sisbajud.juiz) == "undefined" ? "" : preferencias.sisbajud.juiz;
	preferencias.sisbajud.vara = typeof(preferencias.sisbajud.vara) == "undefined" ? "" : preferencias.sisbajud.vara;
	preferencias.sisbajud.cnpjRaiz = typeof(preferencias.sisbajud.cnpjRaiz) == "undefined" ? "não" : preferencias.sisbajud.cnpjRaiz;
	preferencias.sisbajud.teimosinha = typeof(preferencias.sisbajud.teimosinha) == "undefined" ? "não" : preferencias.sisbajud.teimosinha;
	preferencias.sisbajud.contasalario = typeof(preferencias.sisbajud.contasalario) == "undefined" ? "não" : preferencias.sisbajud.contasalario;
	preferencias.sisbajud.naorespostas = typeof(preferencias.sisbajud.naorespostas) == "undefined" ? "não" : preferencias.sisbajud.naorespostas;
	preferencias.sisbajud.valor_desbloqueio = typeof(preferencias.sisbajud.valor_desbloqueio) == "undefined" ? "não" : preferencias.sisbajud.valor_desbloqueio;
	preferencias.sisbajud.banco_preferido = typeof(preferencias.sisbajud.banco_preferido) == "undefined" ? "não" : preferencias.sisbajud.banco_preferido;
	preferencias.sisbajud.agencia_preferida = typeof(preferencias.sisbajud.agencia_preferida) == "undefined" ? "não" : preferencias.sisbajud.agencia_preferida;
	preferencias.sisbajud.preencherValor = typeof(preferencias.sisbajud.preencherValor) == "undefined" ? "não" : preferencias.sisbajud.preencherValor;
	preferencias.sisbajud.confirmar = typeof(preferencias.sisbajud.confirmar) == "undefined" ? "não" : preferencias.sisbajud.confirmar;
	preferencias.sisbajud.executarAAaoFinal = typeof(preferencias.sisbajud.executarAAaoFinal) == "undefined" ? "Nenhum" : preferencias.sisbajud.executarAAaoFinal;
	preferencias.sisbajud.salvarEprotocolar = typeof(preferencias.sisbajud.salvarEprotocolar) == "undefined" ? "não" : preferencias.sisbajud.salvarEprotocolar;		
	preferencias.sisbajud = {juiz: preferencias.sisbajud.juiz, vara: preferencias.sisbajud.vara, cnpjRaiz: preferencias.sisbajud.cnpjRaiz, teimosinha: preferencias.sisbajud.teimosinha, contasalario: preferencias.sisbajud.contasalario, naorespostas: preferencias.sisbajud.naorespostas, valor_desbloqueio: preferencias.sisbajud.valor_desbloqueio, banco_preferido: preferencias.sisbajud.banco_preferido, agencia_preferida: preferencias.sisbajud.agencia_preferida, preencherValor: preferencias.sisbajud.preencherValor, confirmar: preferencias.sisbajud.confirmar, executarAAaoFinal: preferencias.sisbajud.executarAAaoFinal, salvarEprotocolar: preferencias.sisbajud.salvarEprotocolar};
	
	preferencias.serasajud_juiz = typeof(preferencias.serasajud_juiz) == "undefined" ? "" : preferencias.serasajud_juiz;
	preferencias.serasajud_foro = typeof(preferencias.serasajud_foro) == "undefined" ? "" : preferencias.serasajud_foro;
	preferencias.serasajud_vara = typeof(preferencias.serasajud_vara) == "undefined" ? "" : preferencias.serasajud_vara;
	preferencias.serasajud_prazo_atendimento = typeof(preferencias.serasajud_prazo_atendimento) == "undefined" ? "" : preferencias.serasajud_prazo_atendimento;
	preferencias.serasajud = typeof(preferencias.serasajud) == "undefined" ? {juiz: preferencias.serasajud_juiz, foro: preferencias.serasajud_foro, vara: preferencias.serasajud_vara, prazo_atendimento: preferencias.serasajud_prazo_atendimento} : preferencias.serasajud;
	preferencias.renajud = typeof(preferencias.renajud) == "undefined" ? {tipo_restricao: "", comarca: "", tribunal: "", orgao: "", juiz: "", juiz2: ""} : preferencias.renajud;
	preferencias.zoom_editor = typeof(preferencias.zoom_editor) == "undefined" ? 1 : preferencias.zoom_editor;
	preferencias.modulo8 = typeof(preferencias.modulo8) == "undefined" ? [] : preferencias.modulo8;
	preferencias.modulo9 = typeof(preferencias.modulo9) == "undefined" ? {sisbajud:true,renajud:true,cnib:true,serasajud:true,ccs:[true,false,false,false,false,5],crcjud:true,onr:false,gprec:true,ajjt:true,siscondj:true,garimpo:true,sif:true,pjecalc:true,prevjud:true,protestojud:true,ecarta:true} : preferencias.modulo9;
	preferencias.modulo9.ccs = Array.isArray(preferencias.modulo9.ccs) ? preferencias.modulo9.ccs : [preferencias.modulo9.ccs,false,false,false,false,5];
	preferencias.modulo10 = typeof(preferencias.modulo10) == "undefined" ? [] : preferencias.modulo10;
	preferencias.modulo10_juntadaMidia = typeof(preferencias.modulo10_juntadaMidia) == "undefined" ? [false,''] : preferencias.modulo10_juntadaMidia;
	preferencias.modulo2 = typeof(preferencias.modulo2) == "undefined" ? [] : preferencias.modulo2;
	preferencias.modoLGPD = typeof(preferencias.modoLGPD) == "undefined" ? false : preferencias.modoLGPD;
	preferencias.menu_kaizen = typeof(preferencias.menu_kaizen) == "undefined" ? {principal:{posx:'96%',posy:'92%'},detalhes:{posx:'96%',posy:'92%'},tarefas:{posx:'96%',posy:'92%'},sisbajud:{posx:'93%',posy:'80%'},serasajud:{posx:'93%',posy:'80%'},renajud:{posx:'93%',posy:'80%'},cnib:{posx:'93%',posy:'80%'},ccs:{posx:'93%',posy:'80%'},prevjud:{posx:'93%',posy:'80%'},protestojud:{posx:'93%',posy:'80%'},sniper:{posx:'93%',posy:'80%'},censec:{posx:'93%',posy:'80%'},celesc:{posx:'93%',posy:'80%'},casan:{posx:'93%',posy:'80%'},sigef:{posx:'93%',posy:'80%'},infoseg:{posx:'93%',posy:'80%'},ajjt:{posx:'93%',posy:'80%'}} : preferencias.menu_kaizen;
	preferencias.AALote = typeof(preferencias.AALote) == "undefined" ? '' : preferencias.AALote;
	preferencias.erros = typeof(preferencias.erros) == "undefined" ? '' : preferencias.erros;
	preferencias.acionarKaizenComClique = typeof(preferencias.acionarKaizenComClique) == "undefined" ? false : preferencias.acionarKaizenComClique;	
	preferencias.kaizenNaHorizontal = typeof(preferencias.kaizenNaHorizontal) == "undefined" ? false : preferencias.kaizenNaHorizontal;
	preferencias.extrasEditorOcultarAutotexto = typeof(preferencias.extrasEditorOcultarAutotexto) == "undefined" ? false : preferencias.extrasEditorOcultarAutotexto;
	preferencias.extrasEditorInverterOrdem = typeof(preferencias.extrasEditorInverterOrdem) == "undefined" ? false : preferencias.extrasEditorInverterOrdem;
	preferencias.modulo4PaginaInicial = typeof(preferencias.modulo4PaginaInicial) == "undefined" ? 'nenhum' : preferencias.modulo4PaginaInicial;
	preferencias.configURLs = typeof(preferencias.configURLs) == "undefined" ? {descricao:'',urlSiscondj:'',idSiscondj:'',urlSAOExecucao:''} : preferencias.configURLs;
	preferencias.configURLs.descricao = typeof(preferencias.configURLs.descricao) == "undefined" ? 'ERRO' : preferencias.configURLs.descricao;
	preferencias.configURLs.urlSiscondj = typeof(preferencias.configURLs.urlSiscondj) == "undefined" ? 'ERRO' : preferencias.configURLs.urlSiscondj;
	preferencias.configURLs.idSiscondj = typeof(preferencias.configURLs.idSiscondj) == "undefined" ? 'ERRO' : preferencias.configURLs.idSiscondj;
	preferencias.configURLs.urlSAOExecucao = typeof(preferencias.configURLs.urlSAOExecucao) == "undefined" ? 'ERRO' : preferencias.configURLs.urlSAOExecucao;
	preferencias.anexadoDoctoEmSigilo = typeof(preferencias.anexadoDoctoEmSigilo) == "undefined" ? -1 : preferencias.anexadoDoctoEmSigilo;
	preferencias.timeline = typeof(preferencias.timeline) == "undefined" ? ['',[]] : preferencias.timeline;
	preferencias.extrasFecharJanelaExpediente = typeof(preferencias.extrasFecharJanelaExpediente) == "undefined" ? true : preferencias.extrasFecharJanelaExpediente;
	preferencias.extrasSugerirTipoAoAnexar = typeof(preferencias.extrasSugerirTipoAoAnexar) == "undefined" ? true : preferencias.extrasSugerirTipoAoAnexar;
	preferencias.extrasSugerirDescricaoAoAnexar = typeof(preferencias.extrasSugerirDescricaoAoAnexar) == "undefined" ? true : preferencias.extrasSugerirDescricaoAoAnexar;
	
	//LGPD
	if (preferencias.modoLGPD) { ativarLGPD() }
	
	//CONCILIAJT
	let padraoInicial = /trt\d{1,2}/; //eliminar urls que possuem numero. por exemplo: https://pjehom2.trt12.jus.br
	let padrao = /\d{1,2}/;
	if (padraoInicial.test(preferencias.trt)) {
		preferencias.num_trt = preferencias.trt.match(padraoInicial).join();
		if (padrao.test(preferencias.num_trt)) {
			preferencias.num_trt = preferencias.num_trt.match(padrao).join();
		} else {
			preferencias.num_trt = '';
		}
	}
	
	preferencias.conciliajt = await buscaConfigConciliaJT(preferencias.num_trt);

	//base de desenvolvimento do CSJT - regularizar variáveis
	if (document.location.href.includes('desenvolvimento.pje.csjt.jus.br')) { preferencias.num_trt = 99 }
}

//FUNÇÃO PARA CONSULTAR OS ARS NO SITE DOS CORREIOS
async function correios() {
	await preencherInput('input[id="objeto"]','');
	let objetoPesquisado = document.location.href.match(new RegExp("[A-Z]{2}[0-9]{9}[A-Z]{2}","g")).join();
	await preencherInput('input[id="objeto"]',objetoPesquisado);	
	document.getElementById('captcha').focus();
	document.addEventListener('keydown', function(event) {
		if (event.key === "Enter") {
			setTimeout(function(){acao(objetoPesquisado)}, 500);
		}
	});
	
	document.getElementById('b-pesquisar').addEventListener('click', function(event) {
		setTimeout(function(){acao(objetoPesquisado)}, 500);
	});
	
	async function acao(objetoPesquisado) {
		let objetoEncontrado = document.getElementById('titulo-pagina').innerText.replace(/\s+/g, '');
		if (!new RegExp("[A-Z]{2}[0-9]{9}[A-Z]{2}","g").test(objetoEncontrado)) {
			return;
		}
		let ancora = document.getElementById('titulo-pagina').parentElement;
		
		//VERIFICA SE O NÚMERO DO REGISTRO EXIBIDO NA TELA CORRESPONDE AO NÚMERO DO REGISTRO DO LOCATION.HREF
		if (objetoPesquisado != objetoEncontrado) {
			criarCaixaDeAlerta("ERRO",'O REGISTRO da tela (' + objetoEncontrado + ') não corresponde com o REGISTRO informado no GIGS (' + objetoPesquisado + '). Favor refazer a pesquisa.');
			return;
		}
		
		//INSERE O NOME DO DESTINATARIO, SE HOUVER
		if (preferencias.tempAR) {
			ancora.style = "margin-bottom: 10px;";
			let e3 = document.createElement("span");
			e3.id = "maisPje_parte";
			e3. innerText = "Destinatário: " + preferencias.tempAR;
			e3.style = "font-size: 1rem; font-weight: bold; color: black; line-height: 2;";
			ancora.appendChild(e3);
			browser.storage.local.set({'tempAR': ''});
		}
		
		//ABRE MOVIMENTAÇÕES EXTRAS
		clicarBotao(document.getElementById('a-ver-mais'), null, 1000);
		
		//INSERE O BOTAO DE IMPRIMIR
		let bt_imprimir = document.createElement("button");
		bt_imprimir.id = "maisPJe_bt_imprimir";
		bt_imprimir.style = "background-color: #007bff;height: 2.5rem;margin:auto;color:#ffc20e;width: auto;border-radius: 0.25rem;position: absolute; right: 0px; top: 0px;";
		bt_imprimir.onmouseenter = function () {bt_imprimir.style.backgroundColor  = '#006add'};
		bt_imprimir.onmouseleave = function () {bt_imprimir.style.backgroundColor  = '#007bff'};
		bt_imprimir.onclick = function () {
			bt_imprimir.style.setProperty('display', 'none', 'important');
			setTimeout(function(){
				window.print();
				bt_imprimir.style.setProperty('display', 'flex', 'important');
			}, 250);
		};
		let span = document.createElement("span");
		span.textContent = 'Imprimir';
		bt_imprimir.appendChild(span);
		ancora.parentElement.insertAdjacentElement('afterbegin', bt_imprimir);
		
		await esperarElemento('div[class*="jumbotron"]',null,1000);
		//ocultar elementos
		document.querySelector('div[class*="jumbotron"]').style.setProperty('display', 'none', 'important');
		document.getElementById('acessibilidade').style.setProperty('display', 'none', 'important');
		document.getElementById('menu').style.setProperty('display', 'none', 'important');
		document.querySelector('nav[aria-label="breadcrumb"]').style.setProperty('display', 'none', 'important');
		document.querySelector('div[class="bannersro"]').style.setProperty('display', 'none', 'important');
		document.getElementById('rodape').style.setProperty('display', 'none', 'important');
	}
}

//FUNÇÃO SIGEO - AJJT
async function ajjt() {
	console.log('SIGEO - AJ JT');
	
	//corrige o bug da tela branca
	let corpo = await esperarElemento('body')
	corpo.style.height = 'auto';
	
	let var1 = browser.storage.local.get('processo_memoria', async function(result){			
		if (!result.processo_memoria.numero) {return}
		
		//nomearProfissionais - lista Geral
		if (document.location.href.includes("nomearprofissionais_index.jsf")) {
			
			if (preferencias.tempAR == 'prosseguirMinutaAJJT') {
				let limparStorage = browser.storage.local.set({'tempAR': ''});
				Promise.all([limparStorage]).then(async values => {			
					let tabela = await esperarColecao('table[summary="Resultado da pesquisa."] tbody tr', 1, 5000);
					console.log(tabela.length);
					if (tabela.length == 1) {
						await clicarBotao(tabela[0]);
						await clicarBotao('input[id="formAJIntranet:criarSolicitacao"]');
					}
					return;
				});
			} else {
				let check = setInterval(function() {
					if (document.getElementById('formAJIntranet:atributo')) {
						clearInterval(check);
						acaoA1(result.processo_memoria.numero);
					}
				}, 200);
			}
			
		}
		
		//nomearProfissionais - dados do processo judicial
		if (document.location.href.includes("nomearprofissionais_1_dadosnomeacao.jsf")) {
			let check = setInterval(function() {
				if (document.getElementById('formAJIntranet:id_NumeroProcessoJudicial')) {
					clearInterval(check);
					acaoB1(result.processo_memoria.numero);
				}
			}, 200);
		}
		
		//nomearProfissionais - dados do processo judicial fim
		if (document.location.href.includes("nomearprofissionais_2_2_dadosprocessoWS.jsf")) {
			let check = setInterval(function() {
				if (document.getElementById('formAJIntranet:id_NumeroProcessoJudicial')) {
					clearInterval(check);
					acaoC1(result.processo_memoria.numero);
				}
			}, 200);
		}
		
		//nomearProfissionais - consultar perito por nome
		if (document.location.href.includes("nomearprofissionais_3_dadosprofissional_guia.jsf")) {
			let check = setInterval(function() {
				if (document.getElementById('formAJIntranet:id_NomeProfissionalGuiaIndividual')) {
					clearInterval(check);
					acaoD1(result.processo_memoria.terceiro);
				}
			}, 200);
		}
		
		//nomearProfissionais - escolher perito consultado
		if (document.location.href.includes("nomearprofissionais_popup_1_pesquisarprofissionais.jsf")) {
			let check = setInterval(function() {
				if (document.querySelector('input[name="formAJIntranet:profissional"]')) {
					clearInterval(check);
					acaoE1();
				}
			}, 200);
		}
		
		//mantersolicitacaopagamento - lista de Pagamentos
		if (document.location.href.includes("mantersolicitacaopagamento_principal.jsf")) {
			let check = setInterval(async function() {
				if (document.getElementById('formAJIntranet:combo_pesquisa')) {
					clearInterval(check);
					if (!document.getElementById('formAJIntranet:combo_pesquisa').hasAttribute('disabled')) {
						acaoF1(result.processo_memoria.numero);
					} else {
						let tabela = await esperarColecao('table[summary="Resultado da pesquisa."] tbody tr', 1, 5000);
						let map = [].map.call(
							tabela, 
							function(linha) {
								let colunaStatus = linha.querySelector('td[headers="005"]');					
								switch (colunaStatus.innerText) {
									case 'Criada':
										colunaStatus.style = "font-size: x-large;background-color: darkgray;color: white;border-width: 5px 5px 0 5px;border-color: white;border-style: solid;text-align: center;";
										break
									case 'Validada':
										colunaStatus.style = "font-size: x-large;background-color: darkkhaki;color: white;border-width: 5px 5px 0 5px;border-color: white;border-style: solid;text-align: center;";
										break
									case 'Aguardando Ratificacao':
										colunaStatus.style = "font-size: x-large;background-color: darkkhaki;color: white;border-width: 5px 5px 0 5px;border-color: white;border-style: solid;text-align: center;";
										break
									case 'Aguardando Pagamento':
										colunaStatus.style = "font-size: x-large;background-color: darkcyan;color: white;border-width: 5px 5px 0 5px;border-color: white;border-style: solid;text-align: center;";
										break
									case 'Paga':
										colunaStatus.style = "font-size: x-large;background-color: darkseagreen;color: white;border-width: 5px 5px 0 5px;border-color: white;border-style: solid;text-align: center;";
										break
									case 'Cancelada':
										colunaStatus.style = "font-size: x-large;background-color: darkred;color: white;border-width: 5px 5px 0 5px;border-color: white;border-style: solid;text-align: center;";
										break
								}
							}
						);
						if (tabela[0].querySelector('td[headers="005"]').innerText == 'Paga') {
							await clicarBotao(tabela[0]);
							await clicarBotao('input[id="formAJIntranet:visualizar"]');
						} else {
							await clicarBotao(tabela[0]);
							await sleep(2000)
							await clicarBotao('input[id="formAJIntranet:imprimir"]');
						}
						
					}
				}
			}, 200);
		}
		
		//manter_solicitacao_pagamento_incluir.jsf - inclusão de pagamento
		if (document.location.href.includes("manter_solicitacao_pagamento_incluir.jsf")) {
			let check = setInterval(async function() {
				if (document.getElementById('formAJIntranet:decisaoFundamentada')) {
					clearInterval(check);
					let ancora = document.getElementById('formAJIntranet:decisaoFundamentada');
					ancora.addEventListener('input', async function(event) {
						console.log('input')
						let texto = event.target.value;
						if (texto.length == 0) { return }
						console.log(texto);
						let padrao = /[1-9]\d{0,2}(?:\.\d{3})*,\d{2}/m;
						if (padrao.test(texto)) {
							let valorDosHonorarios = texto.match(padrao).join();
							console.log(valorDosHonorarios);
							let campo1 = document.getElementById('formAJIntranet:valorInfSo');
							if (campo1.value=="0,00") {
								campo1.style.backgroundColor = 'orange';
								campo1.value = valorDosHonorarios;
								triggerEvent(campo1, 'input');
								setTimeout(function(){ campo1.style.backgroundColor = 'revert' }, 1000);
							}
							
							let campo2 = document.getElementById('formAJIntranet:quantidadeBeneficiados');
							campo2.style.backgroundColor = 'orange';
							campo2.value = '1';
							triggerEvent(campo2, 'input');
							setTimeout(function(){ campo2.style.backgroundColor = 'revert' }, 1000);
							
							let campo3 = document.getElementById('formAJIntranet:motivos0');
							campo3.parentElement.style.backgroundColor = 'orange';
							console.log(campo3.checked);
							if (!campo3.checked) {
								campo3.click();
								setTimeout(function(){ campo3.parentElement.style.backgroundColor = 'revert' }, 1000);
							} else {
								setTimeout(function(){ campo3.parentElement.style.backgroundColor = 'revert' }, 1000);
							}
							
							let campo4 = document.getElementById('formAJIntranet:motivos1');
							campo4.parentElement.style.backgroundColor = 'orange';
							console.log(campo4.checked);
							if (!campo4.checked) {
								campo4.click();
								setTimeout(function(){ campo4.parentElement.style.backgroundColor = 'revert' }, 1000);
							} else {
								setTimeout(function(){ campo4.parentElement.style.backgroundColor = 'revert' }, 1000);
							}
							
							let campo5 = document.getElementById('formAJIntranet:dataPrestacao');
							if (campo5.value==" ") {
								campo5.style.backgroundColor = 'orange';
								campo5.value = result.processo_memoria.transito;
								triggerEvent(campo5, 'input');
								setTimeout(function(){ campo5.style.backgroundColor = 'revert' }, 1000);
							}
						}
					});
				}
			}, 200);
		}
		
	});
	
	function acaoA1(numero) {
		let el = document.getElementById('formAJIntranet:atributo');
		el.value = "2";
		triggerEvent(el, 'change');
		acaoA2(numero);
	}
	
	function acaoA2(numero) {			
		let el = document.getElementById('formAJIntranet:palavra');
		el.value = numero;
		triggerEvent(el, 'input');
		acaoA3();
	}
	
	function acaoA3() {
		if (document.getElementById('formAJIntranet:botaoPesquisarPorPalavraChave')) {
			let el = document.getElementById('formAJIntranet:botaoPesquisarPorPalavraChave');
			
			let var1 = browser.storage.local.set({'tempAR': 'prosseguirMinutaAJJT'});
			Promise.all([var1]).then( values => {			
				el.click();
				return;
			});
		}
	}
	
	function acaoB1(numero) {
		let el = document.getElementById('formAJIntranet:id_NumeroProcessoJudicial');
		el.value = numero;
		triggerEvent(el, 'input');
		acaoB2(numero);
	}
	
	function acaoB2() {
		let el = document.getElementById('formAJIntranet:pesquisarProcesso');
		el.click();
	}
	
	function acaoC1(numero) {
		let el = document.getElementById('formAJIntranet:id_NumeroProcessoJudicialCNJ');
		el.value = numero;
		triggerEvent(el, 'input');
	}
	
	function acaoD1(terceiros) {
		let nome_perito;
		if (terceiros.length <= 0) {
			return
		} else if (terceiros.length == 1) {
			nome_perito = terceiros[0].nome;
		} else {
			let msg = "Escolha o perito da ordem (Digite o número correspondente): \n\n";
			let i = 0;
			let map3 = [].map.call(
				terceiros, 
				function(parte) {
					msg = msg + (i) + " - " + parte.nome + "\n";
					i++;
				}
			);
			nome_perito = terceiros[parseInt(prompt(msg,''))].nome;
		}
		
		let el = document.getElementById('formAJIntranet:id_NomeProfissionalGuiaIndividual');
		el.value = nome_perito;
		triggerEvent(el, 'input');
		acaoD2();
	}
	
	function acaoD2() {
		let el = document.getElementById('formAJIntranet:pesquisar');
		el.click();
	}
	
	function acaoE1() {
		let el = document.querySelector('input[name="formAJIntranet:profissional"]');
		el.click();
		acaoE2();
	}
	
	function acaoE2() {			
		let el = document.getElementById('formAJIntranet:pesquisar');
		el.click();
	}
	
	function acaoF1(numero) {
		let el = document.getElementById('formAJIntranet:combo_pesquisa');
		el.value = "1";
		triggerEvent(el, 'change');
		acaoF2(numero);
	}
	
	async function acaoF2(numero) {			
		let el = document.getElementById('formAJIntranet:palavra');
		el.value = numero;
		triggerEvent(el, 'input');
		
		if (document.location.href.includes('prosseguirPesquisa')) {
			await clicarBotao('input[id="formAJIntranet:localizar"]');			
		}
	}
	
}

//Funções GPREC incluirBotoesGPREC
async function incluirBotoesGPREC() {
	function criarBotaoGPREC(textoLink, destinoLink) {
		const menu = document.createElement('li');
		menu.className = "ui-widget ui-menuitem ui-corner-all ui-menu-parent";
		const a1 = document.createElement('a');
		a1.className = "ui-menuitem-link ui-submenu-link ui-corner-all";
		a1.style.fontWeight = 'bold';
		a1.innerText = textoLink
		a1.onmouseenter = () => {a1.style.backgroundColor  = '#e4f1fb'; a1.style.color = 'orangered'; };
		a1.onmouseleave = () => {a1.style.backgroundColor  = 'revert'; a1.style.color = 'revert'; };
		a1.onclick = () => window.location.href = destinoLink;
		menu.appendChild(a1);
		return menu;
	};
	return new Promise(
		async resolver => {
			console.log('incluirBotoesGPREC')
			const barra = await esperarElemento('ul[class*="ui-menu-list"]');
			if (barra.hasAttribute('maisPje')) { return resolver(false) }
			barra.setAttribute('maisPje','true');		
			const menu1 = criarBotaoGPREC("maisPJe: RPV > RegistrarPagamento", '/gprec/view/private/rpv/rpv_pagamento_lista.xhtml');
			barra.insertBefore(menu1, barra.lastElementChild);
			const menu2 = criarBotaoGPREC("maisPJe: RPV > lista", '/gprec/view/private/rpv/rpv_lista.xhtml');
			barra.insertBefore(menu2, barra.lastElementChild);
			resolver(true);
		}
	);
}

//FUNÇÃO RESPONSÁVEL PELO POSICIONAMENTO DA JANELA DETALHES DE ACORDO COM AS PREFERÊNCIAS DO USUÁRIO
//ELA É ACIONADA DE DENTRO DA FUNÇÃO EXECUTAR()
function posicionarJanelaDetalhes(desativado) {
	if (!desativado) {
		// console.log("Extensão maisPJE (" + agora() + "): posicionarJanelaDetalhes()");
		let largura = preferencias.gigsDetalhesWidth;
		let altura = preferencias.gigsDetalhesHeight;
		let posx = preferencias.gigsDetalhesLeft;
		let posy = preferencias.gigsDetalhesTop;
		
		if (preferencias.gigsMonitorDetalhes == preferencias.gigsMonitorGigs && preferencias.gigsMonitorDetalhes == preferencias.gigsMonitorTarefas) {
			// console.log("Extensão maisPJE (" + agora() + "):    |_ MONITOR: DETALHES junto com de GIGS e TAREFAS");
			if (preferencias.gigsAbrirTarefas && preferencias.gigsAbrirGigs || preferencias.gigsAbrirDetalhes && preferencias.gigsAbrirGigs) {
				// console.log("Extensão maisPJE (" + agora() + "):       |_ Check abrirTarefas e AbrirGigs ou abrirDetalhes e AbrirGigs");
				if (largura > altura) {
					posx = posx + Math.floor(largura * 0.50);
					largura = Math.floor(largura * 0.50);
					altura = Math.floor(altura * 0.66)	;	
					//afinação
					largura = largura + 12;
					altura = altura - 59;
					posx = posx - 5;
					posy = posy;
				} else {
					posy = posy + Math.floor(altura * 0.50);
					altura = Math.floor(altura * 0.50);
					largura = Math.floor(largura * 0.66);
				}
			} else if (preferencias.gigsAbrirGigs) {
				// console.log("Extensão maisPJE (" + agora() + "):       |_ Check só no AbrirGigs");
				if (largura > altura) {
					largura = Math.floor(largura * 0.7);
				} else {
					altura = Math.floor(altura * 0.7);
				}
				
				//afinação
				largura = largura + 30;
				altura = altura + 5;
				posx = posx - 6;
				// console.log("Detalhes: " + largura + " : " + altura + " : " + posx + " : " + posy);
			} else if (preferencias.gigsAbrirDetalhes) {
				// console.log("Extensão maisPJE (" + agora() + "):       |_ Check só no abrirDetalhes");
				if (largura > altura) {
					posx = posx + Math.floor(largura * 0.50);
					largura = Math.floor(largura * 0.50);
					//afinação
					largura = largura + 12;
					altura = altura + 76;
					posx = posx - 5;
					posy = posy;
				} else {
					posy = posy + Math.floor(altura * 0.50);
					altura = Math.floor(altura * 0.50);
				}				
			} else if (preferencias.gigsAbrirTarefas) {
				// console.log("Extensão maisPJE (" + agora() + "):       |_ Check só no abrirTarefas");
				if (largura > altura) {
					posx = posx + Math.floor(largura * 0.50);
					largura = Math.floor(largura * 0.50);
					//afinação
					largura = largura + 12;
					altura = altura + 76;
					posx = posx - 5;
					posy = posy;
				} else {
					posy = posy + Math.floor(altura * 0.50);
					altura = Math.floor(altura * 0.50);
				}
			}
		} else if (preferencias.gigsMonitorDetalhes == preferencias.gigsMonitorGigs) {
			// console.log("Extensão maisPJE (" + agora() + "):    |_ MONITOR: DETALHES junto com de GIGS");
			if (preferencias.gigsAbrirGigs) {
				// console.log('      |_ Check só no abrirGigs');
				if (largura > altura) {
					largura = Math.floor(largura * 0.7);
				} else {
					altura = Math.floor(altura * 0.7);
				}
				//afinação
				largura = largura + 23;
				altura = altura + 5;
				posx = posx - 6;
			}
		} else if (preferencias.gigsMonitorDetalhes == preferencias.gigsMonitorTarefas) {
			// console.log("Extensão maisPJE (" + agora() + "):    |_ MONITOR: DETALHES junto com TAREFAS");
			if (preferencias.gigsAbrirTarefas) {
				// console.log("Extensão maisPJE (" + agora() + "):       |_ Check só no AbrirTarefas");
				if (largura > altura) {
					posx = posx + Math.floor(largura * 0.50);
					largura = Math.floor(largura * 0.50);
				} else {
					posy = posy + Math.floor(altura * 0.50);
					altura = Math.floor(altura * 0.50);
				}
			}
		}
		// console.log("            |____largura: " + largura);
		// console.log("            |____altura: " + altura);
		// console.log("            |____posx: " + posx);
		// console.log("            |____posy: " + posy);
		
		// console.log("Detalhes: " + largura + " : " + altura + " : " + posx + " : " + posy);

		return browser.runtime.sendMessage({
			tipo: 'posicionarJanela',
			left: posx,
			top: posy,
			width: largura,
			height: altura
		})
	}
}

//FUNÇÃO RESPONSÁVEL PELO POSICIONAMENTO DA JANELA GIGS DE ACORDO COM AS PREFERÊNCIAS DO USUÁRIO
//ELA É ACIONADA DE DENTRO DA FUNÇÃO ABRIRGIGS()
function posicionarJanelaGigs(desativado) {
	if (!desativado) {
		// console.log("Extensão maisPJE (" + agora() + "): posicionarJanelaGigs()");
		let largura = preferencias.gigsGigsWidth;
		let altura = preferencias.gigsGigsHeight;
		let posx = preferencias.gigsGigsLeft;
		let posy = preferencias.gigsGigsTop;
		
		if (preferencias.gigsMonitorGigs == preferencias.gigsMonitorDetalhes && preferencias.gigsMonitorGigs == preferencias.gigsMonitorTarefas) {
			// console.log("Extensão maisPJE (" + agora() + "):    |_ GIGS no mesmo monitor de DETALHES e TAREFAS");
			if (preferencias.gigsAbrirDetalhes || preferencias.gigsAbrirTarefas) {
				// console.log("Extensão maisPJE (" + agora() + "):       |_ Check no AbrirDetalhes ou AbrirTarefas");
				if (largura > altura) {				
					posx = posx + Math.floor(largura * 0.50);
					posy = posy + Math.floor(altura * 0.66);
					largura = Math.floor(largura * 0.50);
					altura = Math.floor(altura * 0.33);
					//afinação
					largura = largura + 15;
					altura = altura + 83;
					posx = posx - 5;
					posy = posy - 65;	
				}		
			} else {
				// console.log("Extensão maisPJE (" + agora() + "):    |_ Nenhum Check");
				if (largura > altura) {
					posx = posx + Math.floor(largura * 0.67);
					largura = Math.floor(largura * 0.33);
				} else {
					posy = posy + Math.floor(altura * 0.67);
					largura = Math.floor(altura * 0.33);
				}
				//afinação
				altura = altura + 8;
				posx = posx + 10;
				// console.log("GIGS " + largura + " : " + altura + " : " + posx + " : " + posy);
			}
		} else if (preferencias.gigsMonitorGigs == preferencias.gigsMonitorDetalhes) {
			// console.log("Extensão maisPJE (" + agora() + "):    |_ GIGS no mesmo monitor de DETALHES");
			
			if (largura > altura) {
				posx = posx + Math.floor(largura * 0.7);
				largura = Math.floor(largura * 0.3);
			} else {
				posy = posy + Math.floor(altura * 0.7);
				altura = Math.floor(altura * 0.3);
			}
			//afinação
			altura = altura + 5;
			posx = posx + 6;
			
		} else if (preferencias.gigsMonitorGigs == preferencias.gigsMonitorTarefas) {
			// console.log("Extensão maisPJE (" + agora() + "):    |_ GIGS no mesmo monitor de TAREFAS");
			
			if (largura > altura) {
				posx = posx + Math.floor(largura * 0.66);
				largura = Math.floor(largura * 0.33);
			} else {
				posy = posy + Math.floor(altura * 0.66);
				altura = Math.floor(altura * 0.33);
			}		
		}
		// console.log("            |____largura: " + largura);
		// console.log("            |____altura: " + altura);
		// console.log("            |____posx: " + posx);
		// console.log("            |____posy: " + posy);
		return browser.runtime.sendMessage({
			tipo: 'posicionarJanela',
			left: posx,
			top: posy,
			width: largura,
			height: altura
		})
	}
}

//FUNÇÃO RESPONSÁVEL PELO POSICIONAMENTO DA JANELA TAREFAS DE ACORDO COM AS PREFERÊNCIAS DO USUÁRIO
//ELA É ACIONADA DE DENTRO DA FUNÇÃO EXECUTAR()
function posicionarJanelaTarefas(desativado) {
	if (!desativado) {
		// console.log("Extensão maisPJE (" + agora() + "): posicionarJanelaTarefas()");
		
		let largura = preferencias.gigsTarefaWidth; //esse valor adicional é o ajuste fino
		let altura = preferencias.gigsTarefaHeight;
		let posx = preferencias.gigsTarefaLeft;
		let posy = preferencias.gigsTarefaTop;
		
		if (preferencias.gigsMonitorTarefas == preferencias.gigsMonitorGigs && preferencias.gigsMonitorTarefas == preferencias.gigsMonitorDetalhes) {
			// console.log("Extensão maisPJE (" + agora() + "):    |_ TAREFAS no mesmo monitor de GIGS e DETALHES");
			if (preferencias.gigsAbrirGigs && preferencias.gigsAbrirDetalhes == false && preferencias.gigsAbrirTarefas == false) {
				// console.log("Extensão maisPJE (" + agora() + "):       |_ Check só no abrirGigs");
				if (largura > altura) {
					largura = Math.floor(largura * 0.66);				
				} else {
					altura = Math.floor(altura * 0.66);
				}
				//afinação
				largura = largura + 38;
				altura = altura + 7;
				posx = posx - 12;
				posy = posy;
			} else {
				// console.log("Extensão maisPJE (" + agora() + "):       |_ Regra geral");
				if (largura > altura) {
					largura = Math.floor(largura * 0.5);
					
					//afinação
					largura = largura + 12;
					altura = altura + 5;
					posx = posx - 6;
					posy = posy;
				} else {
					altura = Math.floor(altura * 0.5);
				}
			}
		} else if (preferencias.gigsMonitorTarefas == preferencias.gigsMonitorGigs) {
			// console.log("Extensão maisPJE (" + agora() + "):    |_ TAREFAS no mesmo monitor de GIGS");
			if (preferencias.gigsAbrirGigs) {
				// console.log("Extensão maisPJE (" + agora() + "):       |_ Check só no abrirGigs");
				if (largura > altura) {
					largura = Math.floor(largura * 0.66);
				} else {
					altura = Math.floor(altura * 0.66);
				}
			}
		} else if (preferencias.gigsMonitorTarefas == preferencias.gigsMonitorDetalhes) {
			// console.log("Extensão maisPJE (" + agora() + "):    |_ TAREFAS no mesmo monitor de DETALHES");
			if (preferencias.gigsAbrirDetalhes) {
				// console.log("Extensão maisPJE (" + agora() + "):       |_ Check só no abrirDetalhes");
				if (largura > altura) {
					posx = posx + Math.floor(largura * 0.50);
					largura = Math.floor(largura * 0.50);
				} else {
					posy = posy + Math.floor(altura * 0.50);
					altura = Math.floor(altura * 0.50);
				}
			}
		}
		// console.log("            |____largura: " + largura);
		// console.log("            |____altura: " + altura);
		// console.log("            |____posx: " + posx);
		// console.log("            |____posy: " + posy);
		return browser.runtime.sendMessage({
			tipo: 'posicionarJanela',
			left: posx,
			top: posy,
			width: largura,
			height: altura
		})
	}
}

//FUNÇÃO RESPONSÁVEL PELA ABERTURA DA JANELA DETALHES DE ACORDO COM AS PREFERÊNCIAS DO USUÁRIO
//ELA É ACIONADA DE DENTRO DA FUNÇÃO EXECUTAR()
async function abrirDetalhesProcesso() {
	await clicarBotao(seletorDetalhesNumeroProcesso);
}

//FUNÇÃO RESPONSÁVEL PELA ABERTURA DA JANELA TAREFAS DE ACORDO COM AS PREFERÊNCIAS DO USUÁRIO
//ELA É ACIONADA DE DENTRO DA FUNÇÃO EXECUTAR()	
async function abrirTarefasProcesso() {
	await clicarBotao('button[aria-label*="Abrir a tarefa"]');
}

//FUNÇÃO RESPONSÁVEL PELA ABERTURA DA JANELA GIGS DE ACORDO COM AS PREFERÊNCIAS DO USUÁRIO
//ELA É ACIONADA DE DENTRO DA FUNÇÃO EXECUTAR()
function abrirGigs(idProcesso) {
	let prefixo = document.location.href.substring(0, document.location.href.search("/pjekz/"));
	let gigsURL = 'https://' + preferencias.trt + '/pjekz/gigs/abrir-gigs/' + idProcesso;
	console.log(preferencias.trt)
	console.log(gigsURL)
	let winGigs = window.open(gigsURL, '_blank');
	posicionarJanelaGigs(preferencias.desativarAjusteJanelas);
	//fecha a janela auxiliar quando a principal é fechada
	window.onunload = function() {
		winGigs.close();
	};
}

//FUNÇÃO RESPONSÁVEL POR MONITORAR O GIGS AS ALTERAÇÕES NO GIGS PRAZO/PREPARO NO CASO DE LANÇAMENTO NA JANELA DETALHES
function iniciarMonitorGigs() {
	console.log("Extensão maisPJE (" + agora() + "): iniciarMonitorGigs() : (" + window.location.href + ")");
	
	monitor_Janela_Gigs_Separada();
	
	//INICIA O MONITOR PARA a janela GIGS aberta em separado
	var tt = [];
	let v = true;
	let check = setInterval(function() {		
		
		browser.storage.local.get('monitorGIGS', function(result){
			tt = result.monitorGIGS;			
		});
		
		if (typeof(tt) != "undefined" && tt.length > 0) {
			if (tt[0] == "acao_bt_aaAutogigs" || tt[0] == "acao_bt_aaChecklist") {
				if (v) {
					// clearInterval(check);
					v = false;
					let var1 = browser.storage.local.set({'monitorGIGS': []});
					Promise.all([var1]).then(values => {
						acao();						
					});
				} else {
					v = true;
				}
			}
		}
	}, 1000);
	
	function acao() {
		
		// window.location.reload();
		//clica no botão novo e cancela para atualizar os campos
		querySelectorByText('button', 'Nova atividade').click();
		let check = setInterval(function() {
			if (querySelectorByText('button', 'Cancelar')) {
				clearInterval(check);
				querySelectorByText('button', 'Cancelar').click();
				setTimeout(function() {
					querySelectorByText('button', 'Novo Comentário').click();
					let check2 = setInterval(function() {
						if (querySelectorByText('button', 'Cancelar')) {
							clearInterval(check2);
							querySelectorByText('button', 'Cancelar').click();
						}
					}, 10);
				}, 200);	
			}
		}, 10);
	}
}

//FUNÇÃO RESPONSÁVEL PELA MUDANÇA DO PERFIL DO USUÁRIO DE ACORDO COM AS PREFERÊNCIAS GRAVADAS
//ELA É ACIONADA DE DENTRO DA FUNÇÃO EXECUTAR()
async function mudarPerfil() {
	console.log('maisPJe: mudarPerfil');
	console.debug('preferencias.perfilUsuario: ' + preferencias.perfilUsuario);
	console.debug('preferencias.modulo4PaginaInicial: ' + preferencias.modulo4PaginaInicial);
	
	//DESCRIÇÃO: Identifica se o usuário deu refresh na página. Neste caso não acionar a troca do perfil	
	if (window.performance) {
		if (performance.navigation.type == 1) {
			return;
		}
	}
	
	
	if (preferencias.perfilUsuario != null) {
		if (preferencias.perfilUsuario != "nenhum" && preferencias.perfilUsuario != "") {			
			let precisa = await precisaTrocar();			
			if (precisa) {
				//DESCRIÇÃO: Aguarda o carregamento do botão "PAPEL DO USUÁRIO" e clica nele
				let check = setInterval(function() {			
					if (document.querySelector('button[class*="perfil-button"]')) {
						clearInterval(check);
						document.querySelector('button[class*="perfil-button"]').click();
						acao1();
					}				
				}, 500);
			} else {
				acao3();
			}
		} else {
			acao2();
		}
	}
	
	//DESCRIÇÃO: Aguarda o carregamento do menu "PAPEL DO USUÁRIO" e clica no menu das preferências
	function acao1() {
		let check = setInterval(function() {
			let contador = 0;
			if (document.querySelector('button[aria-label="' + preferencias.perfilUsuario + '"]')) {
				clearInterval(check);
				document.querySelector('button[aria-label="' + preferencias.perfilUsuario + '"]').click();
				acao2();
			} else {
				if (contador = 5000) { //se não encontrar em cinco segundos desliga a função
					clearInterval(check);
					document.querySelector('div[class*="info-usuario"]').click();
					acao2();
				}
				contador = contador + 100;
			}
		}, 100);
	}
	
	//DESCRIÇÃO: Guarda as preferências de nome, oj
	function acao2() {
		let nm_usuario, oj_usuario;
		let check = setInterval(function() {
			if (document.querySelector('span[class="nome-usuario"]')) {
				clearInterval(check);
				nm_usuario = document.querySelector('span[class="nome-usuario"]').innerText;
				oj_usuario = document.querySelector('span[class="papel-usuario"]').innerText;
				browser.storage.local.set({'nm_usuario': nm_usuario, 'oj_usuario': oj_usuario});
				preferencias.nm_usuario = nm_usuario;
				preferencias.oj_usuario = oj_usuario;
				acao3();
			}
		}, 100);
	}
	
	//muda a tela inicial
	async function acao3() {
		if (!preferencias.modulo4PaginaInicial) { return }
		if (preferencias.modulo4PaginaInicial.includes('nenhum')) { return }
		let primeiroPasso = preferencias.modulo4PaginaInicial;
		let ultimoPasso = await extrairColchetes(preferencias.modulo4PaginaInicial);
		
		console.log('Primeiro passo: ' + primeiroPasso);
		console.log('Último passo: ' + ultimoPasso);
		
		if (ultimoPasso) {
			primeiroPasso = primeiroPasso.replace(ultimoPasso,'');
			primeiroPasso = primeiroPasso.replace('[','');
			primeiroPasso = primeiroPasso.replace(']','');
			
			// console.log('   |___Primeiro passo: ' + primeiroPasso);
			// console.log('   |___Último passo: ' + ultimoPasso);
			
			await clicarBotao('button[aria-label="' + primeiroPasso + '"]');
			
			let up = await esperarElemento('div[aria-label="' + ultimoPasso + '"] mat-card, button[id*="maisPje_filtrofavorito_' + ultimoPasso + '"]',null,1000);
			
			if (up) { 
				await clicarBotao(up); //regras: clicar nas opções do painel global, clicar nos filtros criados do relatório gigs
			} else {
				await clicarBotao('button',ultimoPasso); //exceção
			}			
			
		} else {
			await clicarBotao('button[aria-label="' + primeiroPasso + '"]');
		}
	}
	
	async function extrairColchetes(texto) {
		return new Promise(async resolve => {
			let padrao = /\[(.*?)\]/gm;
			let nmBT = ''
			if (padrao.test(texto)) {
				nmBT = texto.match(new RegExp(/\[(.*?)\]/gm)).join();
				nmBT = nmBT.replace('[','');
				nmBT = nmBT.replace(']','');
				return resolve(nmBT);
			} else {
				return resolve(null);
			}
		});
	}
	
	async function precisaTrocar() {
		return new Promise(async resolve => {
			
			let arrayPerfil = preferencias.perfilUsuario.split(' - ');
			let perfilOJ, perfilPAPEL;
			
			if (arrayPerfil.length <= 2) {  // eh a regra geral
				perfilOJ = preferencias.perfilUsuario.split(' - ')[0];
				perfilPAPEL = preferencias.perfilUsuario.split(' - ')[1];
			} else {  // existem casos que isso acontece. Por exemplo: 2ª Vara do Trabalho de São Paulo - Zona Leste - Diretor de Secretaria
				perfilPAPEL = arrayPerfil[arrayPerfil.length-1];
				perfilOJ = preferencias.perfilUsuario.replace(' - ' + perfilPAPEL,'');
			}
			
			let ancora = await esperarElemento('div[class*="info-usuario"][aria-label*="Trocar Órgão Julgador ou Papel"]');
			let papelAtual = ancora.getAttribute('aria-label');
			// console.log('**************************perfilOJ: ' + perfilOJ)
			// console.log('**************************perfilPAPEL: ' + perfilPAPEL)
			// console.log('**************************papelAtual: ' + papelAtual)
			if (papelAtual.includes(perfilOJ) && papelAtual.includes(perfilPAPEL)) {
				let padrao = /\[(.*?)\]/gm;
				if (padrao.test(preferencias.modulo4PaginaInicial)) { // console.log('**************************troca? SIM')
					return resolve(true);
				} else { // console.log('**************************troca? NÃO')
					return resolve(false);
				}
			} else {
				// console.log('**************************troca? sim')
				return resolve(true);
			}
		});
	}
}

//FUNÇÃO RESPONSÁVEL POR APRECIAR TODAS AS PETIÇÕES DO PROCESSO DE ACORDO COM AS PREFERÊNCIAS DO USUÁRIO
//ELA É ACIONADA DE DENTRO DA FUNÇÃO EXECUTAR()
async function apreciarPeticoes() {
	await esperarElemento('mat-card[style="background-color: khaki;"]');
	await clicarBotao('button[aria-label="Apreciar todos."]');
}

//FUNÇÃO RESPONSÁVEL POR ESCONDER O CHIPS DE ACORDO COM AS PREFERÊNCIAS DO USUÁRIO
//ELA É ACIONADA DE DENTRO DA FUNÇÃO EXECUTAR()
async function ocultarChips() {
	if (preferencias.AALote.length > 0) { return resolve(false) } //desativa quando vem das ações em lote	
	await clicarBotao('button[aria-label="Ocultar Chips"]');
}

async function ocultarLembretes() {
	if (preferencias.AALote.length > 0) { return resolve(false) } //desativa quando vem das ações em lote	
	let postIts = await esperarElemento('button[aria-label="Recolher Lembretes"]')
	if (postIts) { await clicarBotao('button[aria-label="Recolher Lembretes"]') }
}

async function ocultarCabecalho() {
	let el = await esperarElemento('button[aria-label="Esconder Cabeçalho"]');
	if (!el) { return }
	if (!el.parentElement) { return }
	if (el.parentElement.className.includes('cabecalho-colapsado')) { return }
	await clicarBotao(el);
}

async function exibirCabecalho() {
	let el = await esperarElemento('button[aria-label="Esconder Cabeçalho"]');
	if (!el) { return }
	if (!el.parentElement) { return }
	if (el.parentElement.className.includes('cabecalho-colapsado')) { await clicarBotao(el) }
}

//FUNÇÃO RESPONSÁVEL PELA CRIAÇÃO DO MENU COM OS DADOS DAS PARTES DO PROCESSO
async function gigsCriarMenu() {
	return new Promise(async resolve => {
		if (!preferencias.num_trt) { return }
		
		if (preferencias.tempAR == 'F5') {  //variavel para apagar da memoria - limpa a variavel ao atualizar a pagina
			preferencias.tempAR = '';
			let limparStorage = browser.storage.local.set({'tempAR': ''});
			Promise.all([limparStorage]).then(async values => {			
				await fundo(false);
				return;
			});
		}
		
		browser.storage.onChanged.addListener(storageChange);
		// await fundo(true);
		let processo = await aguardarCarregamento();

		// console.log("gigsCriarMenu " + processo)

		await menuStatus(true); //,muda icone para estrela ninja (carregando dados...)
		let id = document.location.href.substring(document.location.href.search('/processo/')+10, document.location.href.search('/detalhe'));
		// await exibir_mensagem("Criando menu");
		browser.runtime.sendMessage({tipo: 'obterPartesDoProcesso', trt: preferencias.trt, id: id, processo: processo}); //chama o background para carregar os dados
		resolve(true);
	});

	async function storageChange(changes) { //quando o processo_memoria for carregado no storage avisa para desligar a função
		if (Object.keys(changes)[0] == 'processo_memoria') { // background grava os dados aqui
			// fundo(false);
			await sleep(1000);
			menuStatus(false); // desliga a estrela ninja - guardou tudo!
		}
	}	

	async function aguardarCarregamento() {
		return new Promise(async resolve => {
			let ancora = await esperarElemento(seletorDetalhesNumeroProcesso);
			let padrao = /\d{7}\-\d{2}\.\d{4}\.\d{1}\.\d{2}\.\d{4}/g;
			if (ancora) {
				let check = setInterval(function() {
					if (padrao.test(ancora.innerText)) {
						clearInterval(check);
						return resolve(ancora.innerText.match(padrao));
					}
				}, 100);
			} else {
				return resolve(null);
			}
		});
	}
}

async function registrarObrigacaoDePagar() {
	await inserirBtInverterPolo();
	await selecionarAutorCredor();
	await selecionar1ReuDevedor();
	
	async function inserirBtInverterPolo() {
		return new Promise(async resolver => {
			let btExiste = await esperarElemento('div[id="maisPJe_OP_div"]',null, 500);
			
			if (!btExiste) {
				let ancora = await esperarElemento('div[class*="bloco-participante"]');
				
				//DESCRIÇÃO: REGRA DO TOOLTIP
				if (!document.getElementById('maisPje_tooltip_abaixo3')) {
					tooltip('abaixo3');
				}
				
				let div = document.createElement('div');
				div.id = 'maisPJe_OP_div';
				
				let b = document.createElement('button');
				b.id = 'maisPJe_OP_inverterPolo';
				b.setAttribute('maisPje-tooltip-abaixo3','Inverter Polos');
				b.className = 'mat-focus-indicator mat-tooltip-trigger mat-fab mat-button-base mat-accent';
				
				b.onclick = async function () {
					let linhas = document.querySelectorAll('div[class*="bloco-participante"] tbody tr');
					for (const [pos, linha] of linhas.entries()) {
						if (linha.querySelector('mat-checkbox[class*="mat-checkbox-checked"]')) {
							let opt = linha.querySelector('mat-select[role="combobox"]');							
							if (opt.textContent.includes('Credor')) {
								await clicarBotao(opt.firstElementChild);
								await clicarBotao('mat-option','Devedor');
							} else {
								await clicarBotao(opt.firstElementChild);
								await clicarBotao('mat-option','Credor');
							}
						}
						
					}
				};
				
				let s = document.createElement('span');
				s.className = 'mat-button-wrapper';
				
				let i = document.createElement('i');
				i.className = 'fa fa-retweet fa-2x';
				
				s.appendChild(i);
				b.appendChild(s);
				div.appendChild(b);
				ancora.parentElement.insertBefore(div, ancora);
				
			}
			resolver(true);
		});	
	}
	
	async function selecionarAutorCredor() {
		return new Promise(async resolve => {
			fundo(true);
			
			let linha = await esperarElemento('div[class*="bloco-participante"] tbody tr','Reclamante');
			linha.style.backgroundColor = 'rgb(173, 216, 230)';
			let ckb = linha.querySelector('mat-checkbox[aria-label="Marcar Parte"]');
			await clicarBotao(ckb.firstElementChild);
			
			fundo(false);
			resolve(true);
		});
	}
	
	async function selecionar1ReuDevedor() {
		return new Promise(async resolve => {
			fundo(true);
			
			let linha = await esperarElemento('div[class*="bloco-participante"] tbody tr','Reclamado');
			linha.style.backgroundColor = 'rgb(230, 200, 173)';
			let ckb = linha.querySelector('mat-checkbox[aria-label="Marcar Parte"]');
			await clicarBotao(ckb.firstElementChild);
			
			fundo(false);
			resolve(true);
		});
	}
}

//FUNÇÃO COMPLEMENTAR QUE RETORNA A HORA ATUAL AUXILIANDO NO LOG
function agora(){
	let dNow = new Date();
	return dNow.getDate() + '/' + (dNow.getMonth()+1) + '/' + dNow.getFullYear() + ' ' + dNow.getHours() + ':' + dNow.getMinutes() + ':' + dNow.getMilliseconds();
}

//FUNÇÃO RESPONSÁVEL POR ACIONAR OS BOTÕES DE MENU NA JANELA DETALHES DO PROCESSO
async function acaoBotaoDetalhes(bt1, bt2=null, monitor=true) {
	return new Promise(async resolve => {
		console.log("Extensão PJE (" + agora() + "): acaoBotaoDetalhes()");
		await clicarBotao('button[id="botao-menu"]');
		
		let bt3 = (bt1.includes('Gigs')) ? bt1.replace('Gigs','GIGS') : bt1;
		
		let btAncora = document.querySelector('button[aria-label="' + bt1 + '"]') || document.querySelector('button[aria-label="' + bt2 + '"]') || document.querySelector('button[aria-label*="' + bt3 + '"]');
		await clicarBotao(btAncora, null, monitor);
		
		resolve(true);
	});
}

//FUNÇÃO RESPONSÁVEL POR CONSULTAR O AR NO SITE DOS CORREIOS
function consultarAR() {
	fundo(true);
	console.log("Extensão maisPJE (" + agora() + "): consultar a existência de Registro(AR) nas atividades do GIGS");
	
	setTimeout(function(){
		//DESCRIÇÃO: retorna um array com todos os números dos ARs.
		let numAR;
		if (document.querySelector('table[name="Tabela de Atividades"]')) {
			numAR = document.querySelector('table[name="Tabela de Atividades"]').innerText.match(new RegExp("[A-Z]{2}[0-9]{9}[A-Z]{2}","g"));
		} else {
			numAR = document.body.innerText.match(new RegExp("[A-Z]{2}[0-9]{9}[A-Z]{2}","g"));
		}
		console.log("Extensão maisPJE (" + agora() + "):    |_ " + numAR);
		if (numAR != null) {
			let parametros = 'dependent=yes,';					
			parametros += 'left=' + ((preferencias.gigsGigsWidth)-(520)) + ',';
			parametros += 'top=' + ((preferencias.gigsGigsHeight)-(520)) + ',';
			parametros += 'width=520px,';
			parametros += 'height=520px';
			window.open('https://rastreamento.correios.com.br/app/index.php?Registros='+numAR, '_blank', parametros);
		} else {
			console.log("Extensão maisPJE (" + agora() + "): Registro(AR) não encontrado!");
			browser.runtime.sendMessage({tipo: 'criarAlerta', valor: 'Registro(AR) não encontrado!', icone: '1'});
		}
		fundo(false);
	}, 1000);
}

//FUNÇÃO RESPONSÁVEL POR FILTRAR APENAS OS PROCESSOS (PAINEL GLOBAL) CUJO RESPONSÁVEL É O USUÁRIO
function meusProcessosGlobal() {
	//verifica se o usuário está na tela principal
	if (document.body.contains(document.evaluate('//button[@aria-label="Meu Painel"]', document, null, XPathResult.ANY_TYPE, null).iterateNext())) {
		fundo(true);
		let usuario = document.getElementsByClassName('info-usuario ng-star-inserted')[0].getElementsByTagName('span')[0].textContent; //recupera o usuário do sistema
		usuario = usuario.toUpperCase();
		console.log("Extensão maisPJE (" + agora() + "): meusProcessosGlobal: " + usuario);
		document.evaluate('//button[@aria-label="Painel Global"]', document, null, XPathResult.ANY_TYPE, null).iterateNext().click(); // clica no botão MEUPAINEL
		setTimeout(function(){		
			document.getElementsByClassName('cabecalho')[0].getElementsByTagName('button')[0].click(); // clica no botão EXIBIR TODOS
			setTimeout(function(){
				document.evaluate('//mat-select[@aria-label="Filtro Usuário Responsável. "]', document, null, XPathResult.ANY_TYPE, null).iterateNext().click(); // clica na caixa de seleção FILTRO DO RESPONSÁVEL
				setTimeout(function(){
					if (document.evaluate('//mat-option[@name="' + usuario + '"]', document, null, XPathResult.ANY_TYPE, null).iterateNext() != null) {
						document.evaluate('//mat-option[@name="' + usuario + '"]', document, null, XPathResult.ANY_TYPE, null).iterateNext().click(); // clica no USUARIO RESPONSAVEL
						document.evaluate('//button[@aria-label="Filtrar"]', document, null, XPathResult.ANY_TYPE, null).iterateNext().click(); // clica no botão FILTRO						
						setTimeout(function(){
							document.getElementsByClassName('th-class cursor ng-star-inserted')[2].click();
							fundo(false);
						}, 500); // clica no botão "desde"
					} else {
						document.evaluate('//button[@aria-label="Filtrar"]', document, null, XPathResult.ANY_TYPE, null).iterateNext().click(); // clica no botão FILTRO					
						browser.runtime.sendMessage({tipo: 'criarAlerta', valor: 'Não existem processos vinculados para você!!', icone: '1'});
						setTimeout(function(){fundo(false);}, 500);
					}
				}, 1000);
			}, 200);
		}, 100);		
	}
}

//FUNÇÃO RESPONSÁVEL POR FILTRAR APENAS OS PROCESSOS (PAINEL GLOBAL) QUE EXIGEM ATENÇÃO DO USUÁRIO
function meusProcessosGlobal2() {
	fundo(true);
	var check = setInterval(function() {		
		if (document.querySelector('div[class="cabecalho"]').firstElementChild.innerText.search("Exibir todos") > -1) {
			clearInterval(check);
			document.querySelector('div[class="cabecalho"]').firstElementChild.click();
			aplicar();
		}
	}, 500);
	
	function aplicar() {
		let passo1, passo2, passo3 = false;
		if (document.querySelector('mat-select[aria-label="Filtro Tarefa do processo. "]')) {
			document.querySelector('mat-select[aria-label="Filtro Tarefa do processo. "]').click();
			let passo1 = true; //independentemente do tempo do check, passa apenas uma vez no 'for'
			let check1 = setInterval(function() {
				if ((document.querySelectorAll('mat-option[role="option"]').length > 5) && passo1) {
					clearInterval(check1);
					// console.log("passo1: OK");					
					passo1 = false;
					setTimeout(function(){
						for (let elem of document.querySelectorAll('mat-option[role="option"]')) {
							// console.log(elem.getAttribute("name"));
							switch (elem.getAttribute("name")) {
								case 'Aguardando apreciação pela instância superior':
									break
								case 'Aguardando audiência':
									break
								case 'Aguardando cumprimento de acordo':
									break
								case 'Aguardando final do sobrestamento':
									break
								case 'Aguardando prazo':
									break
								case 'Aguardando prazo recursal':
									break
								case 'Aguardando término dos prazos':
									break								
								case 'Assinar expedientes e comunicações - magistrado':
									break
								case 'Arquivo':
									break
								case 'Arquivo definitivo':
									break
								case 'Arquivo provisório':
									break
								case 'Assinar decisão':
									break
								case 'Assinar despacho':
									break
								case 'Assinar sentença':
									break
								case 'Cartas devolvidas':
									break
								// case 'Cumprimento de Providências':
									// break
								case 'Elaborar decisão':
									break
								case 'Elaborar sentença':
									break
								// case 'Triagem Inicial':
									// break
								case 'Aguardando pgto RPV Precatório':
									break
								case 'Arquivamento definitivo - PA':
									break
								default:
									elem.click();
							}
						}
						if (document.querySelector('button[aria-label="Filtrar"]')) {
							document.querySelector('button[aria-label="Filtrar"]').click();
							setTimeout(function(){
								passo2 = true;
							}, 1000);
						}						
					}, 1000);
				}
			}, 100);
		}
		
		// mostrar 100 itens por pagina
		let check2 = setInterval(function() {
			if (passo2) {
				clearInterval(check2);
				// console.log("passo2: OK");
				if (document.querySelector('pje-paginador')) {					
					if (document.querySelector('pje-paginador').getElementsByClassName('mat-select')) {
						let el = document.querySelector('pje-paginador').getElementsByClassName('mat-select')[1];
						el.click();
						passo3 = true;
					}
				}
			}
			if (passo3) {
				if (document.querySelectorAll('mat-option[role="option"]').length < 6 && passo3) {
					// console.log("passo3: OK");
					for (let elem of document.querySelectorAll('mat-option[role="option"]')) {
						if (elem.innerText == "100") {
							elem.click();
							fundo(false);
							setTimeout(function(){
								//devolve o foco para a parte superior da pagina
								document.querySelector('button[aria-label="Menu Completo"]').focus();
							}, 200);
							break;
						}
					}
				}
			}			
		}, 500);		
	}	
}

//FUNÇÃO RESPONSÁVEL POR FILTRAR APENAS OS PROCESSOS (RELATÓRIO GIGS) CUJO RESPONSÁVEL É O USUÁRIO
async function meusProcessosGigs() {
	//verifica se o usuário está na tela principal
	if (document.querySelector('button[aria-label="Meu Painel"]')) {
		fundo(true);
		let usuario = document.getElementsByClassName('info-usuario ng-star-inserted')[0].getElementsByTagName('span')[0].textContent; //recupera o usuário do sistema
		usuario = usuario.toUpperCase();
		console.log("Extensão maisPJE (" + agora() + "): meusProcessosGigs: " + usuario);
		await clicarBotao('button[aria-label="Relatórios do GIGS"]');
		await clicarBotao('button[aria-label="Limpar Filtro"]');
		await clicarBotao('i[aria-label="Atividades sem prazo"]');
		await escolherOpcaoTeste('mat-select[aria-label*="Filtro Responsáveis"]', usuario);		
		await clicarBotao('button[aria-label="Filtrar"]');
		await clicarBotao('th','Data Atividade');
		fundo(false);
	}
}

//FUNÇÃO RESPONSÁVEL POR FILTRAR OS PROCESSOS (PAINEL GLOBAL, RELATÓRIO GIGS e ESCANINHO) DE ACORDO COM O ÚLTIMO NÚMERO
async function filtrarPorMeuFiltro() {
	console.log("Extensão maisPJE (" + agora() + "): filtrarPorMeuFiltro()");
	let meuFiltro_temp = [];
	let meuFiltro_tempSTR = '';
	preferencias.meuFiltro.forEach((element, index, array) => {	return element ? meuFiltro_temp.push(index) : -1 });
	
	if (meuFiltro_temp.length > 0) {
		let ativar = document.querySelector('tbody').getAttribute('maisPje_filtro_ativado');
		if (!ativar || ativar == "false") {
			console.log(meuFiltro_temp.toString());
			if (meuFiltro_temp.toString().includes('10') || meuFiltro_temp.toString().includes('11')) {
				ativarFiltro(true);
			} else {
				ativarFiltro();
			}
		} else {
			desativarFiltro();
		}
	}
	
	async function ativarFiltro(porJuiz=false) {
		document.querySelector('tbody').setAttribute('maisPje_filtro_ativado',true);
		let el = document.querySelectorAll('tbody tr');
		if (!el) {
			return
		}
		
		for (const [pos, linha] of el.entries()) {
			let dados = linha.innerText;
			let processoNumero = dados.match(new RegExp('\\d{7}-\\d{2}\\.\\d{4}\\.\\d{1,2}\\.\\d{1,2}\\.\\d{4}','g')).join();
			
			if (porJuiz) {
				let ojc = await obterOrgaoJulgadorCargo(processoNumero);
				ojc = (ojc.toLowerCase().includes('titular')) ? '10' : '11';
				
				let filtroJuiz = meuFiltro_temp.toString().includes(ojc);
				
				(!filtroJuiz) ? linha.style.setProperty('display', 'none') : linha.style.setProperty('background-color', 'khaki');
				(!filtroJuiz) ? linha.setAttribute('maisPje_filtro',false): linha.setAttribute('maisPje_filtro',true);
			} else {
				
				let numero = processoNumero.substring(0, 7);
				let ano = processoNumero.substring(11, 15);
				let digito;							
				if (ano > 2009) {
					digito = processoNumero.substring(6, 7);					
				} else {
					digito = processoNumero.substring(4, 5);
				}
				let filtroNum = meuFiltro_temp.toString().includes(digito);
				console.log(processoNumero + " : " + numero + " : " + ano + " : " + digito + " : " + filtroNum);
				
				(!filtroNum) ? linha.style.setProperty('display', 'none') : linha.style.setProperty('background-color', 'khaki');
				(!filtroNum) ? linha.setAttribute('maisPje_filtro',false): linha.setAttribute('maisPje_filtro',true);
			}
		}
		
		// DESCRIÇÃO: Se o usuário clicar em qualquer item do cabeçalho o filtro será desativado
		document.querySelector('thead').addEventListener('click', function(event) {
			if (!event.target.className.includes('fa-check') && !event.target.className.includes('todas-marcadas')) {
				desativarFiltro();
			}
		});
		
		// DESCRIÇÃO: Se o usuário mudar a página da tabela, o filtro é desativado			
		document.querySelector('pje-paginador').addEventListener('click', function(event) {
			desativarFiltro();
		});
	}
	
	function desativarFiltro() {
		document.querySelector('tbody').setAttribute('maisPje_filtro_ativado',false);
		let el = document.querySelector('tbody').getElementsByTagName('tr');
		if (!el) { return }
		let cor = 'rgb(240, 240, 240)';
		let map1 = [].map.call(
			el, 
			function(linha) {
				linha.style.setProperty('display', '');
				linha.style.setProperty('background-color', cor);
				cor = (cor == "white") ? 'rgb(240, 240, 240)' : 'white';
			}
		);
		return true;
	}
}

//FUNÇÃO RESPONSÁVEL POR ABRIR O RELATÓRIO DE PROCESSOS NA FASE DE EXECUÇÃO
async function procurarExecucao() {
	console.log(preferencias.configURLs.urlSAOExecucao)
	if (preferencias.configURLs.urlSAOExecucao.includes('Nenhum')) { 
		fundo(true);		
		consultaRapidaPJE();
		let listareus = '';
		for (const [pos, reu] of preferencias.processo_memoria.reu.entries()) {
			listareus += reu.nome;
			if (pos<preferencias.processo_memoria.reu.length-1) { listareus += ';' }
		}

		await preencherInput('#maisPje_cxPergunta_inputTexto',listareus);
		await clicarBotao('#maisPje_caixa_de_pergunta_btOK');
		exibir_mensagem("Pesquisando processos na unidade em face de: " + listareus);
		await esperarElemento('#maisPje_caixa_de_selecao');
		await clicarBotao('#maisPje_bt_exportarAALote');
		fundo(false);
	} else {
		getAtalhosNovaAba().procurarExecucao.abrirAtalhoemNovaJanela();
	}
}

//FUNÇÃO RESPONSÁVEL POR ENCONTRAR A TAREFA DO PROCESSO INDEPENDENTEMENTE SE ALGUÉM O MOVEU
async function abrirTarefaDoProcesso(idProcesso='') {
	if (!idProcesso) {
		if (document.location.href.includes("/detalhe")) {
			let nome_tarefa_exibido = await esperarElemento('span[class="texto-tarefa-processo"]');
			nome_tarefa_exibido = nome_tarefa_exibido.textContent;
			if (nome_tarefa_exibido.includes('Arquivo provisório')) { //verificar se a tarefa pertence ao PJe antigo
				await clicarBotao('button', nome_tarefa_exibido);
				return
			} else {
				idProcesso = document.location.href.substring(document.location.href.search("/processo/")+10, document.location.href.search("/detalhe"));
			}
		} else if (document.location.href.includes("/tarefa")) {
			idProcesso = document.location.href.substring(document.location.href.search("/processo/")+10, document.location.href.search("/tarefa"));
		} else {
			console.log('maisPje: idProcesso não identificado');
			return
		}
	}
	
	//Obtem o idProcesso e o idTarefa da tarefa mais recente
	let url1 = 'https://' + preferencias.trt + '/pje-comum-api/api/processos/id/' + idProcesso + '/tarefas?maisRecente=true';	
	let resposta1 = await fetch(url1);
	let dados1 = await resposta1.json();	
	let tarefaIdProcesso = dados1[0].idProcesso;
	let tarefaIdTarefa = dados1[0].idTarefa;
	
	//Obtem o nome do recurso da tarefa obtida
	let url2 = 'https://' + preferencias.trt + '/pje-comum-api/api/tarefas/' + tarefaIdTarefa;	
	let resposta2 = await fetch(url2);
	let dados2 = await resposta2.json();	
	let tarefaNomeRecurso = dados2.nomeRecurso;
	
	//Obtem o restante da url da tarefa, de acordo com o recurso
	let url3 = 'https://' + preferencias.trt + '/pje-seguranca/api/token/permissoes/recursos/' + tarefaNomeRecurso;	
	let resposta3 = await fetch(url3);
	let dados3 = await resposta3.text();	
	let tarefaUrlCorreta = dados3;
	
	//substitui as variáveis para obter a url correta
	let tarefa = 'https://' + preferencias.trt + '/pjekz' + tarefaUrlCorreta;
	tarefa = tarefa.replace('{id}', tarefaIdProcesso);
	tarefa = tarefa.replace('{idTarefa}', tarefaIdTarefa);
	window.open(tarefa);
}

//FUNÇÃO RESPONSÁVEL POR ADICIONAR OS BOTÕES NA PÁGINA DETALHES
function addBotaoTarefas() {
	let check = setInterval(function() {
		let ancora = document.querySelector('section[aria-label="Ações da tarefa"]');
		if(ancora) {
			clearInterval(check);
			if (document.getElementById('pjextension_bt_detalhes_base')) { return }
			
			//DIV AGRUPADOR
			let div1 = document.createElement("div");
			div1.id = "pjextension_bt_detalhes_base";
			div1.style = "float: left";
			div1.setAttribute('role', 'toolbar');
			
			//BOTÃO GIGS
			let botao2 = document.createElement("a");
			let i2 = document.createElement("i");						
			botao2.title = "Abrir o Gigs"; //<--aria-label
			botao2.style = "cursor: pointer; position: relative; vertical-align: -moz-middle-with-baseline; padding: 5px; top: 5px; z-index: 1; opacity: 1; font-size: 1.5rem; margin: 5px;";
			botao2.onmouseover = function () {botao2.style.opacity = 0.5};
			botao2.onmouseleave = function () {botao2.style.opacity = 1};
			i2.className = "fa fa-tag";
			botao2.onclick = function () {
				let idProcesso = document.location.href.substring(document.location.href.search("/processo/")+10, document.location.href.search("/tarefa"));
				abrirGigs(idProcesso);
			};						
			botao2.appendChild(i2);
			div1.appendChild(botao2);
			
			//BOTÃO EXPEDIENTES
			let botao12 = document.createElement("a");
			let i12 = document.createElement("i");						
			botao12.title = "Expedientes"; //<--aria-label
			botao12.style = "cursor: pointer; position: relative; vertical-align: -moz-middle-with-baseline; padding: 5px; top: 5px; z-index: 1; opacity: 1; font-size: 1.5rem; margin: 5px;";
			botao12.onmouseover = function () {botao12.style.opacity = 0.5};
			botao12.onmouseleave = function () {botao12.style.opacity = 1};
			i12.className = "fa fa-envelope";
			botao12.onclick = function () {acaoBotaoDetalhes("Expedientes")};						
			botao12.appendChild(i12);
			div1.appendChild(botao12);
			
			//BOTÃO INSERIR LEMBRETES
			let botao14 = document.createElement("a");
			let i14 = document.createElement("i");						
			botao14.title = "Lembretes"; //<--aria-label
			botao14.style = "cursor: pointer; position: relative; vertical-align: -moz-middle-with-baseline; padding: 5px; top: 5px; z-index: 1; opacity: 1; font-size: 1.5rem; margin: 5px;";
			botao14.onmouseover = function () {botao14.style.opacity = 0.5};
			botao14.onmouseleave = function () {botao14.style.opacity = 1};
			i14.className = "fas fa-thumbtack";
			botao14.onclick = function () {acaoBotaoDetalhes("Lembretes")};						
			botao14.appendChild(i14);
			div1.appendChild(botao14);
			
			ancora.insertAdjacentElement('afterbegin',div1);
		}
	}, 100);	
}

function criarBotaoDetalhes({ tooltip, complementoStyle = '',
	role = 'link', id = '', iconClass = undefined,
	corMouseEnter = '#0006', corMouseLeave = 'rgba(0, 0, 0, 0.87)',
	}) {
	let botaoDetalhe = document.createElement("a");
	botaoDetalhe.id = id;
	botaoDetalhe.style = "cursor: pointer; position: relative; vertical-align: -moz-middle-with-baseline; padding: 5px; top: 5px; z-index: 6; opacity: 1; font-size: 1.5rem; margin: 5px; " + complementoStyle;
	botaoDetalhe.setAttribute('maisPje-tooltip-abaixo', tooltip);
	botaoDetalhe.setAttribute('aria-label', tooltip);
	botaoDetalhe.setAttribute('role', role);
	botaoDetalhe.onmouseenter = function () { this.style.color = corMouseEnter };
	botaoDetalhe.onmouseleave = function () { this.style.color = corMouseLeave };
	if (iconClass) {
		const icon = document.createElement("i");
		icon.className = iconClass;
		botaoDetalhe.appendChild(icon);
	}
	return botaoDetalhe;
}
//FUNÇÃO RESPONSÁVEL POR ADICIONAR OS BOTÕES NA PÁGINA DETALHES
async function addBotaoDetalhes() {
	let check = setInterval(async function() {	
		if(document.getElementsByClassName("fill-space")[1] && !document.getElementById('pjextension_bt_detalhes_base')) {
			clearInterval(check);
			let el = document.getElementsByClassName("fill-space")[1];
			//DESCRIÇÃO: limita a largura das informações de data da audiência, autuação, etc. O objetivo é aumentar o espaço para os ícones
			el.parentElement.firstElementChild.style.setProperty("width","50%");			
			
			//DESCRIÇÃO: REGRA DO TOOLTIP
			if (!document.getElementById('maisPje_tooltip_abaixo')) {
				tooltip('abaixo');
			}
			
			let base = document.createElement("div");
			base.id = "pjextension_bt_detalhes_base";
			base.style = "width: 100%;height: 100%; display: flex; align-items: center;";
			
			//DESCRIÇÃO: EVENTO QUE CONTROLA A SENSIBILIDADE DO CARREGAMENTO DOS BOTÕES REFERENTES AS AÇÕES AUTOMATIZADAS
			let elementoAtivo = "";
			base.onmouseover = function (event) {				
				event.preventDefault();
				if (!event.target.id) {
					if (event.target.tagName == "I") {
						elementoAtivo = event.target.parentElement.id;
					}
					return
				}
				elementoAtivo = event.target.id;
			};
			
			//ANEXAR DEPOIMENTOS - MÓDULO 10
			if (preferencias.modulo10_juntadaMidia[0]) {
				const botaoModulo10 = criarBotaoDetalhes({
					tooltip: 'Anexar Vídeos de Audiência',
					id: "maisPJe_bt_detalhes_anexarDepoimento",
					complementoStyle: ' color: rgb(149, 31, 31, 0.87);',
					corMouseLeave: 'rgba(149, 31, 31)',
				});

				botaoModulo10.onclick = function () {
					let var1 = browser.storage.local.set({'tempBt': ['acao_bt_aaAnexar', 997]});
					Promise.all([var1]).then(values => {
						acaoBotaoDetalhes("Anexar Documentos");
					});
				};
				
				let i1Modulo10 = document.createElement("i");
				i1Modulo10.className = "fas fa-video";
				
				let i2Modulo10 = document.createElement("i");
				i2Modulo10.className = "fas fa-plus";
				i2Modulo10.style = "position: absolute; color: lightgray; left: 0.7em; top: 1.3em; font-size: 0.5em;";
				
				botaoModulo10.appendChild(i1Modulo10);
				botaoModulo10.appendChild(i2Modulo10);
				base.appendChild(botaoModulo10);
			}
			
			//Concluso ao Magistrado
			if (preferencias.atalhosDetalhes[24]) {
				const botao24 = criarBotaoDetalhes({
					iconClass: "fas fa-gavel",
					id: "maisPJe_bt_detalhes_concluso",
					complementoStyle: ' color: rgb(149, 31, 31);',
					tooltip: 'Concluso ao Magistrado',
				})
				preferencias.aaDespacho = typeof(preferencias.aaDespacho) == "undefined" ? [] : preferencias.aaDespacho;
				if (preferencias.aaDespacho.length > 0) {
					botao24.onmouseenter = async function () {
						this.style.color = '#0006';
						await sleep(500);
						if (elementoAtivo == this.id) { addBotaoDespacho() }
					}
					botao24.onmouseleave = function () {this.style.color = 'rgba(149, 31, 31, 0.87)';elementoAtivo = "";};
				}
				botao24.onclick = async function () {
					let var1 = browser.storage.local.set({'tempBt': ['acao_bt_aaDespacho', 999]});
					Promise.all([var1]).then(values => {
						//DESCRIÇÃO: SE SELECIONADO NAS CONFIGURAÇÕES APRECIA AS PETIÇÕES ANTES DE FAZER CONCLUSO
						if (preferencias.gigsApreciarPeticoes2) {
							console.log("Extensão maisPJE (" + agora() + "): apreciarPeticoes() - a partir de DETALHES");
							apreciarPeticoes();					
							acao2();
						} else {
							acao2();
						}
						
						//DESCRIÇÃO: ABRE A JANELA PARA FAZER A CONCLUSÃO AO MAGISTRADO
						function acao2() {
							abrirTarefaDoProcesso();
						}
					});
				};				
				base.appendChild(botao24);
			}
			//Movimentar Processo
			if (preferencias.atalhosDetalhes[0]) {
				const botao0 = criarBotaoDetalhes({
					iconClass: "fas fa-hand-paper",
					id: "maisPJe_bt_detalhes_movimentar",
					complementoStyle: ' color: rgb(149, 31, 31);',
					tooltip: 'Movimentar Processo',
				});
				preferencias.aaMovimento = typeof(preferencias.aaMovimento) == "undefined" ? [] : preferencias.aaMovimento;
				if (preferencias.aaMovimento.length > 0) {
					botao0.onmouseenter = async function () {
						this.style.color = '#0006';
						await sleep(500);
						if (elementoAtivo == this.id) { addBotaoMovimento() }
					}
					botao0.onmouseleave = function () {this.style.color = 'rgba(149, 31, 31, 0.87)';elementoAtivo = "";};
				}
				botao0.onclick = function () {
					//DESCRIÇÃO: SE SELECIONADO NAS CONFIGURAÇÕES APRECIA AS PETIÇÕES ANTES DE MOVIMENTAR O PROCESSO
					if (preferencias.gigsApreciarPeticoes3) {
						console.log("Extensão maisPJE (" + agora() + "): apreciarPeticoes() - a partir de DETALHES");
						apreciarPeticoes();					
						acao2();
					} else {
						acao2();
					}
					
					//DESCRIÇÃO: ABRE A JANELA PARA FAZER A CONCLUSÃO AO MAGISTRADO
					function acao2() {
						abrirTarefaDoProcesso();
					}
				};				
				base.appendChild(botao0);
			}
			//Guardar dados das partes
			if (preferencias.atalhosDetalhes[1]) {
				const botao1 = criarBotaoDetalhes({
					iconClass: "fas fa-address-card",
					id: "maisPJe_bt_detalhes_guardarDados",
					complementoStyle: ' color: rgb(149, 31, 31);',
					tooltip: 'Guardar dados das partes',
					role: 'button',
					corMouseLeave: 'rgba(149, 31, 31, 0.87)',
				});
				botao1.onclick = function () {gigsCriarMenu()};						
				base.appendChild(botao1);
			}
			//Abrir o Gigs
			if (preferencias.atalhosDetalhes[2]) {
				const botao2 = criarBotaoDetalhes({
					id: "maisPJe_bt_detalhes_gigs",
					tooltip: 'Abrir o Gigs',
					iconClass: "fa fa-tag",
				});

				preferencias.aaAutogigs = typeof(preferencias.aaAutogigs) == "undefined" ? [] : preferencias.aaAutogigs;
				if (preferencias.aaAutogigs.length > 0) {
					botao2.onmouseenter = async function () {
						this.style.color = '#0006';
						await sleep(500);
						if (elementoAtivo == this.id) { addBotaoAutoGigs() }
					}
					botao2.onmouseleave = function () {this.style.color = 'rgba(0, 0, 0, 0.87)';elementoAtivo = "";};
				}
				botao2.onclick = function () {
					let idProcesso = document.location.href.substring(document.location.href.search("/processo/")+10, document.location.href.search("/detalhe"));
					abrirGigs(idProcesso);
				};						
				base.appendChild(botao2);
			}
			//Acesso a Terceiros
			if (preferencias.atalhosDetalhes[3]) {
				const botao3 = criarBotaoDetalhes({
					id: "maisPJe_bt_detalhes_acessoATerceiros",
					tooltip: 'Acesso a Terceiros',
					iconClass: "fas fa-street-view"
				});
				botao3.onclick = function () {acaoBotaoDetalhes("Acesso a Terceiros")};						
				base.appendChild(botao3);
			}
			//Anexar Documentos
			if (preferencias.atalhosDetalhes[4]) {
				let botao4 = criarBotaoDetalhes({
					id: "maisPJe_bt_detalhes_anexarDocumentos",
					id: "pjextension_bt_detalhes_4",
					tooltip: 'Anexar Documentos',
					iconClass: "fa fa-paperclip",
				});

				preferencias.aaAnexar = typeof(preferencias.aaAnexar) == "undefined" ? [] : preferencias.aaAnexar;
				if (preferencias.aaAnexar.length > 0) {
					botao4.onmouseenter = async function () {
						this.style.color = '#0006';
						await sleep(500);
						if (elementoAtivo == this.id) { addBotaoTelaAnexar() }
					}
					botao4.onmouseleave = function () {this.style.color = 'rgba(0, 0, 0, 0.87)';elementoAtivo = "";}
				}
				botao4.onclick = function () {acaoBotaoDetalhes("Anexar Documentos")};						
				base.appendChild(botao4);
			}
			//Audiências e Sessões
			if (preferencias.atalhosDetalhes[5]) {
				const botao5 = criarBotaoDetalhes({
					id: "maisPJe_bt_detalhes_audienciasESessoes",
					tooltip: 'Audiências e Sessões',
					iconClass: "fas fa-users",
				});						
				botao5.onclick = function () {acaoBotaoDetalhes("Audiências e Sessões")};						
				base.appendChild(botao5);
			}
			//Download do processo completo
			if (preferencias.atalhosDetalhes[6]) {
				const botao6 = criarBotaoDetalhes({
					id: "maisPJe_bt_detalhes_downloadProcessoCompleto",
					tooltip: 'Baixar processo completo',
					iconClass: "far fa-file-pdf",
					role: 'button',
				});				
				botao6.onmouseenter = async function () {
					this.style.color = '#0006';
					await sleep(500);
					if (elementoAtivo == this.id) { addBotaoBaixarProcessoLegado() }
				}
				botao6.onmouseleave = function () {this.style.color = 'rgba(0, 0, 0, 0.87)';elementoAtivo = "";}
				botao6.onclick = function () {acaoBotaoDetalhes("Download do processo completo", "Baixar processo completo")}; //existe a situação "Download do processo completo" e "Baixar processo completo"				
				base.appendChild(botao6);
			}
			//BNDT
			if (preferencias.atalhosDetalhes[7]) {
				const botao7 = criarBotaoDetalhes({
					id: "maisPJe_bt_detalhes_bndt",
					tooltip: 'BNDT',
					iconClass: "fas fa-money-check-alt",
				});						
				botao7.onclick = function () {acaoBotaoDetalhes("BNDT")};						
				base.appendChild(botao7);
			}
			//Abrir cálculos do processo
			if (preferencias.atalhosDetalhes[8]) {
				const botao8 = criarBotaoDetalhes({
					id: "maisPJe_bt_detalhes_abrirCalculos",
					tooltip: 'Abrir cálculos do processo',
					iconClass: "fa fa-calculator",
				});						

				botao8.onmouseenter = async function () {
					this.style.color = '#0006';
					await sleep(500);
					if (elementoAtivo == this.id) { addBotaoAtualizacaoRapida() }
				}
				botao8.onmouseleave = function () {this.style.color = 'rgba(0, 0, 0, 0.87)';elementoAtivo = "";};
				botao8.onclick = function () {acaoBotaoDetalhes("Abrir cálculos do processo")};						
				base.appendChild(botao8);
			}
			//Abre a tela de Comunicações e Expedientes
			if (preferencias.atalhosDetalhes[9]) {
				const botao9 = criarBotaoDetalhes({
					id: "maisPJe_bt_detalhes_intimacaoEExpediente",
					tooltip: 'Criar Intimação/Expediente',
					iconClass: "fa fa-envelope",
				});
				preferencias.aaComunicacao = typeof(preferencias.aaComunicacao) == "undefined" ? [] : preferencias.aaComunicacao;
				if (preferencias.aaComunicacao.length > 0) {
					botao9.onmouseenter = async function () {
						this.style.color = '#0006';
						await sleep(500);
						if (elementoAtivo == this.id) { addBotaoTelaComunicacoes() }
					}
					botao9.onmouseleave = function () {this.style.color = 'rgba(0, 0, 0, 0.87)';elementoAtivo = "";}
				}
				botao9.onclick = function () {acaoBotaoDetalhes("Abre a tela de Comunicações e Expedientes")};						
				base.appendChild(botao9);
			}
			//Controle de Segredo
			if (preferencias.atalhosDetalhes[10]) {
				const botao10 = criarBotaoDetalhes({
					id: "maisPJe_bt_detalhes_controleDeSegredo",
					tooltip: 'Controle de Segredo',
					iconClass: "fas fa-book-open",
					role: 'button',
				});
				botao10.onclick = function () {acaoBotaoDetalhes("Controle de Segredo")};						
				base.appendChild(botao10);
			}
			//Cópia
			if (preferencias.atalhosDetalhes[25]) {
				const botao25 = criarBotaoDetalhes({
					id: "maisPJe_bt_detalhes_copiarDocumentos",
					tooltip: 'Copiar documentos',
					iconClass: "fas fa-clone",
					role: 'button'
				});
				botao25.onclick = function () {acaoBotaoDetalhes("Cópia")};						
				base.appendChild(botao25);
			}			
			//Abre a tela com os dados financeiros
			if (preferencias.atalhosDetalhes[11]) {
				const botao11 = criarBotaoDetalhes({
					id: "maisPJe_bt_detalhes_dadosFinanceiros",
					tooltip: 'Abre a tela com os dados financeiros',
					iconClass: "fas fa-file-invoice-dollar",
				});
				botao11.onmouseenter = async function () {
					this.style.color = '#0006';
					await sleep(500);
					if (elementoAtivo == this.id) { addInformacoesSIF() }
				}
				botao11.onmouseleave = function () {this.style.color = 'rgba(0, 0, 0, 0.87)';elementoAtivo = "";}
				botao11.onclick = function () {acaoBotaoDetalhes("Abre a tela com os dados financeiros")}				
				base.appendChild(botao11);
			}
			//Expedientes
			if (preferencias.atalhosDetalhes[12]) {
				const botao12 = criarBotaoDetalhes({
					id: "maisPJe_bt_detalhes_Expedientes",
					tooltip: 'Visualizar intimações/expedientes do processo',
					role: 'button',
					iconClass: "fas fa-mail-bulk",
				});						
				botao12.onclick = function () {acaoBotaoDetalhes("Expedientes")}					
				base.appendChild(botao12);
			}
			//Histórico de Retificação da Autuação
			if (preferencias.atalhosDetalhes[27]) {
				const botao27 = criarBotaoDetalhes({
					id: "maisPJe_bt_detalhes_retificacaoDeAutuacao",
					tooltip: 'Histórico de Retificação da Autuação',
					iconClass: "fas fa-history"
				});
				botao27.onclick = function () {acaoBotaoDetalhes("Histórico de Retificação da Autuação")}						
				base.appendChild(botao27);
			}
			//Histórico de Sigilo
			if (preferencias.atalhosDetalhes[13]) {
				const botao13 = criarBotaoDetalhes({
					id: "maisPJe_bt_detalhes_historicoDeSigilo",
					tooltip: 'Histórico de Sigilo',
					iconClass: "fab fa-wpexplorer",
				});						
				botao13.onclick = function () {acaoBotaoDetalhes("Histórico de Sigilo")}					
				base.appendChild(botao13);
			}
			//Lembretes
			if (preferencias.atalhosDetalhes[14]) {
				const botao14 = criarBotaoDetalhes({
					id: "maisPJe_bt_detalhes_Lembretes",
					tooltip: 'Lembretes',
					iconClass: "fas fa-thumbtack",
					role: 'button',
				});
				botao14.onclick = function () {acaoBotaoDetalhes("Lembretes")}						
				base.appendChild(botao14);
			}
			//Lançar movimentos
			if (preferencias.atalhosDetalhes[15]) {
				const botao15 = criarBotaoDetalhes({
					id: "maisPJe_bt_detalhes_lancarMovimento",
					role: 'button',
					tooltip: 'Lançar movimentos',
					iconClass: "far fa-plus-square",
				});
				botao15.onmouseenter = async function () {
					this.style.color = '#0006';
					await sleep(500);
					if (elementoAtivo == this.id) { addBotaoLancarMovimentos() }
				}
				botao15.onmouseleave = function () {this.style.color = 'rgba(0, 0, 0, 0.87)';elementoAtivo = "";}
				botao15.onclick = function () {acaoBotaoDetalhes("Lançar movimentos")}
				base.appendChild(botao15);
			}
			//Obrigação de Pagar
			if (preferencias.atalhosDetalhes[16]) {
				const botao16 = criarBotaoDetalhes({
					id: "maisPJe_bt_detalhes_obrigacaoDePagar",
					tooltip: 'Obrigação de Pagar',
					iconClass: "fas fa-dollar-sign",
					role: 'button',
				});
				botao16.onclick = function () {acaoBotaoDetalhes("Obrigação de Pagar")}						
				base.appendChild(botao16);
			}
			//Pagamento
			if (preferencias.atalhosDetalhes[17]) {
				const botao17 = criarBotaoDetalhes({
					id: "maisPJe_bt_detalhes_pagamento",
					tooltip: 'Pagamento',
					iconClass: "fas fa-money-bill"
				});
				botao17.onclick = function () {acaoBotaoDetalhes("Pagamento")}				
				base.appendChild(botao17);
			}
			//Abre o PDPJ
			if (preferencias.atalhosDetalhes[26]) {
				const botao26 = criarBotaoDetalhes({ 					
					id: "maisPJe_bt_detalhes_pdpj",
					tooltip: 'Abre o PDPJ' 
				});
				const i26 = document.createElement("img");
				i26.style = "max-width: 25px;max-height: 25px;";
				i26.src = "assets/images/Pdpj_preto.png";
				botao26.onclick = function () {acaoBotaoDetalhes("PDPJ")}					
				botao26.appendChild(i26);
				base.appendChild(botao26);
			}			
			//Perícias
			if (preferencias.atalhosDetalhes[18]) {
				const botao18 = criarBotaoDetalhes({
					id: "maisPJe_bt_detalhes_pericias",
					tooltip: 'Perícias',
					iconClass: "fas fa-user-md"
				});
				botao18.onclick = function () {acaoBotaoDetalhes("Perícias")}				
				base.appendChild(botao18);
			}
			//Quadro de recursos
			if (preferencias.atalhosDetalhes[19]) {
				const botao19 = criarBotaoDetalhes({
					id: "maisPJe_bt_detalhes_quadroDeRecursos",
					tooltip: 'Quadro de recursos',
					iconClass: "fas fa-stopwatch",
				});
				botao19.onclick = function () {acaoBotaoDetalhes("Quadro de recursos")}					
				base.appendChild(botao19);
			}
			//Redistribuições
			if (preferencias.atalhosDetalhes[28]) {
				const botao28 = criarBotaoDetalhes({
					id: "maisPJe_bt_detalhes_redistribuicoes",
					tooltip: 'Redistribuições',
					iconClass: "fa fa-route",
				});
				botao28.onclick = function () {acaoBotaoDetalhes("Redistribuições")}				
				base.appendChild(botao28);
			}
			//Reprocessar chips do processo
			if (preferencias.atalhosDetalhes[20]) {
				const botao20 = criarBotaoDetalhes({
					id: "maisPJe_bt_detalhes_reprocessarChip",
					tooltip: 'Reprocessar chips do processo',
					iconClass: "fas fa-sync",
					role: 'button',
				});
				botao20.onclick = async function () { acaoBotaoDetalhes("Reprocessar chips do processo") }		
				base.appendChild(botao20);
			}
			//Retificar autuação
			if (preferencias.atalhosDetalhes[21]) {
				const botao21 = criarBotaoDetalhes({
					id: "maisPJe_bt_detalhes_retificarAutuacao",
					tooltip: 'Retificar autuação',
					iconClass: "fas fa-pencil-alt"
				});
				botao21.onmouseenter = async function () {
					this.style.color = '#0006';
					await sleep(500);
					if (elementoAtivo == this.id) { addBotaoRetificarAutuacao() }
				}
				botao21.onmouseleave = function () {this.style.color = 'rgba(0, 0, 0, 0.87)';elementoAtivo = "";}
				botao21.onclick = function () {
					let var1 = browser.storage.local.set({'tempBt': ['acao_bt_retificarAutuacao', [999]]});
					Promise.all([var1]).then(values => {
						acaoBotaoDetalhes("Retificar autuação");
					});					
				}
				base.appendChild(botao21);
			}
			//Retirar Valor Histórico
			if (preferencias.atalhosDetalhes[22]) {
				const botao22 = criarBotaoDetalhes({
					id: "maisPJe_bt_detalhes_valorHistorico",
					tooltip: 'Retirar Valor Histórico',
					iconClass: 'fab fa-first-order',
				});
				
				botao22.onclick = function () { acaoBotaoDetalhes("Retirar Valor Histórico") }
				base.appendChild(botao22);
			}
			//Verificar Impedimentos e Suspeições
			if (preferencias.atalhosDetalhes[23]) {
				const botao23 = criarBotaoDetalhes({
					id: "maisPJe_bt_detalhes_impedimentoESuspeicao",
					tooltip: 'Verificar Impedimentos e Suspeições',
					iconClass: 'far fa-thumbs-down'
				});
				
				botao23.onclick = function () { acaoBotaoDetalhes("Verificar Impedimentos e Suspeições") }
				base.appendChild(botao23);
			}
			//Abre o WikiVT
			if (preferencias.atalhosDetalhes[29]) {
				const botao29 = criarBotaoDetalhes({ 
					id: "maisPJe_bt_detalhes_wikivt",
					tooltip: 'Abre o WIKI VT' 
				});
				
				const i29 = document.createElement("img");
				i29.style = "max-width: 28px;max-height: 28px; filter:brightness(0);";
				i29.src = "assets/images/dock-menu/Wikivt.png";
				botao29.onclick = function () {acaoBotaoDetalhes("WIKI VT")}
				botao29.appendChild(i29);
				base.appendChild(botao29);
			}
			
			//*************************FUNÇÃO LIA TESTE
			if (preferencias.conciliajt.enabled || preferencias.conciliajt.ads_enabled) {
				let check2 = setInterval(function() {
					if (document.querySelector('span[class="texto-numero-processo"]')) {
						clearInterval(check2);
						let processoNumero = document.querySelector('span[class="texto-numero-processo"]').innerText.match(new RegExp('\\d{7}-\\d{2}\\.\\d{4}\\.\\d{1,2}\\.\\d{1,2}\\.\\d{4}','g')).join();
						const botao25 = criarLinkPotencialConciliaJT(processoNumero);
						botao25.style = "cursor: pointer; position: relative; vertical-align: -moz-middle-with-baseline; padding: 5px; top: 5px; z-index: 6; opacity: 0.87; font-size: 1.7rem; margin: 5px;";
						base.appendChild(botao25);
					}
				}, 1000);
			}
			//*************************
			
			el.appendChild(base);	

			//ajustar a altura ba barra de acordo com a extensão AVJT
			let btAVJT = await esperarElemento('botao[id="menu-do-processo-expandido-configuracoes"]',null,2000);
			document.getElementById('pjextension_bt_detalhes_base').style.marginTop = (!btAVJT) ? '-6px' : '15px';
		}
	}, 100);
	
	//DISPARA EVENTUAL AÇÃO AUTOMATIZADA CASO A PÁGINA SEJA ATUALIZADA E O LISTENER ABAIXO SEJA ENCERRADO
	// console.log('---------------------------------');
	// console.log('performance.navigation.type: ' + performance.navigation.type);
	// console.log('preferencias.tempAAEspecial.length: ' + preferencias.tempAAEspecial.length);
	// console.log('preferencias.tempAAEspecial: ' + preferencias.tempAAEspecial);
	// console.log('preferencias.tempBt: ' + preferencias.tempBt);
	// console.log('---------------------------------');
	// if (performance.navigation.type == 1 && preferencias.tempAAEspecial.length > 0) { await acionarAcaoAutomatizadaEmReload() }
	
	//MONITORA A AÇÃO AUTOMATIZADA. CASO ESTEJA VINCULADA A OUTRA, MANDA DISPARAR
	browser.storage.onChanged.addListener(logStorageChange);				
	async function logStorageChange(changes, area) {
		let changedItems = Object.keys(changes);
		for (let item of changedItems) {
			if (item == "tempBt") { //controla as AA e os vínculos (No caso aqui só nos interessa os vínculos
				// console.log('*********************************' + item + ' : ' +changes[item].newValue[0] + '(' + changes[item].newValue[1] + ')')
				
				if (typeof changes[item].newValue[1] === 'object') { //for passada como objeto é uma ação automatizada nova (via código)
					let limparStorage = browser.storage.local.set({'tempAAEspecial': []});
					Promise.all([limparStorage]).then(values => {
						switch (changes[item].newValue[0]) {
							case 'Anexar':
								acao_bt_aaAnexar(changes[item].newValue[1]);
								break
							case 'Comunicação':
								acao_bt_aaComunicacao(changes[item].newValue[1]);
								break
							case 'AutoGigs':									
								acao_bt_aaAutogigs(changes[item].newValue[1]);
								break
							case 'Despacho':
								acao_bt_aaDespacho(changes[item].newValue[1]);
								break
							case 'Movimento':
								acao_bt_aaMovimento(changes[item].newValue[1]);
								break
							case 'Checklist':
								acao_bt_aaChecklist(changes[item].newValue[1]);
								break
						}
					});
				
				} else if (changes[item].newValue[0] == "vinculo") {
					console.debug("JANELA DETALHES prosseguir pela AA: " + changes[item].newValue[1]);
					if (changes[item].newValue[1] != "Nenhum") {
						console.log('logStorageChange: ' + preferencias.tempAAEspecial)
						//sempre que o vínculo vem de dentro da própria janela DETALHES DO PROCESSO
						//é preciso recarregar a variável preferencias.tempAAEspecial pois ela sofre
						//alterações no background.js
						preferencias.tempAAEspecial = await getLocalStorage('tempAAEspecial');
						let velocidade = preferencias.maisPje_velocidade_interacao + 500;
						await sleep(velocidade);
						acao_vinculo(changes[item].newValue[1]);
						
					} else {
						//mando limpar o AALote para quando chegar ao fim dos vínculos, zerar a variável AALote fará com que Ações Automatizadas em Lote sigam em sequencia.
						// if (param == "Nenhum") { browser.runtime.sendMessage({tipo: 'storage_limpar', valor: 'AALote'}) }
						browser.runtime.sendMessage({tipo: 'storage_limpar', valor: 'tempBt,AALote'});
						fundo(false);
					}
				}
			} else if (item == "processo_memoria") {
				console.log(changes[item].newValue)
				preferencias.processo_memoria = changes[item].newValue;
			}
		}
	}
	
	// se a janela DETALHES DO PROCESSO nasceu de um refresh(F5) ou de um vinculo Atualizar|Atualizar
	// verificar se tem algum vínculo pendente de prosseguimento
	// console.log(performance.navigation.type + ' : ' + preferencias.tempBt + ' : ' + preferencias.tempAAEspecial);
	if (performance.navigation.type == 1 && (preferencias.tempBt != 'undefined' || preferencias.tempAAEspecial != '')) {
		console.log("JANELA DETALHES atualizou...");		
		
		//DESCRIÇÃO: Aplica visibilidade de sigilo às partes quando da juntada de documentos sigilosos
		if (preferencias.anexadoDoctoEmSigilo > 0) {			
			await aplicarVisibilidadeSigiloUltimoDocumentoJuntado();
			await documentoEmSigilo(-1);
		}
		
		if (preferencias.tempBt != 'undefined' || preferencias.tempAAEspecial != '') {
			browser.runtime.sendMessage({tipo: 'storage_vinculo', valor: preferencias.tempBt[1]});
		} else {
			browser.runtime.sendMessage({tipo: 'storage_limpar', valor: 'tempBt'});
		}
	}
}

//FUNÇÃO RESPONSÁVEL POR ADICIONAR OS BOTÕES NA PÁGINA GIGS
async function addBotaoGigs() {
	console.log('maisPJe: addBotaoGigs()');
	//desativa quando vem das ações em lote
	if (preferencias.AALote.length > 0) {
		if (!preferencias.AALote.includes('Checklist|')) { //vem do lote e vem com AA que exige os botões do checklist
			return; 
		}
	}
	
	let existeGIGS = await esperarElemento('pje-gigs-ficha-processo');
	if (!existeGIGS) { return }
	
	//botão "lupa" para consulta de AR
	let tabelaAtividades = await esperarElemento('table[name="Lista de Atividades"], article[aria-label="Atividade"], pje-gigs-atividades table');
	
	if (!tabelaAtividades) { return }
	if (!tabelaAtividades.getAttribute('maisPje')) {
		tabelaAtividades.setAttribute('maisPje','true');		
		let listaDeAtividades = await esperarColecao('table[name="Lista de Atividades"] span[class*="descricao"], article[aria-label="Atividade"] span[class*="descricao"], pje-gigs-atividades table span[class*="descricao"]');
		if (!listaDeAtividades) { return }
		
		for (const [pos, atividade] of listaDeAtividades.entries()) {
			if (atividade.innerText.search(new RegExp("[A-Z]{2}[0-9]{9}[A-Z]{2}","g")) > -1) {
				let bt = document.createElement("a");
				let ic = document.createElement("i");
				bt.id = "extensaoPje_bt_gigs_3_bt_" + pos;
				ic.id = "extensaoPje_bt_gigs_3_ic_" + pos;
				bt.title = "Consultar AR";
				ic.className = "fas fa-search";
				bt.style = "cursor: pointer; position: relative; padding: 5px; z-index: 100; opacity: 1;";
				bt.onmouseover = function () {bt.style.opacity = 0.5};
				bt.onmouseleave = function () {bt.style.opacity = 1};
				bt.onclick = function () {
					let var1 = atividade.innerText.match(new RegExp("[A-Z]{2}[0-9]{9}[A-Z]{2}","g"))[0]; //numero AR
					let var2 = atividade.innerText.substr(atividade.innerText.search(var1) + 16); //nome parte
					buscaARGigs(var1,var2);
				};				
				bt.appendChild(ic);
				atividade.parentElement.insertAdjacentElement('afterbegin', bt);
			}
		}
	}
	
	//botão "Consultar AR"
	let btConsultarAR = await esperarElemento('button[id="extensaoPje_bt_gigs_1"]', null, 500);
	if (!btConsultarAR) {
		let ancora1 = await esperarElemento('button[aria-label="Nova Atividade"]');
		if (!ancora1) { return }				
		let botao1 = document.createElement("button");
		botao1.id = "extensaoPje_bt_gigs_1";
		botao1.textContent = "Consultar AR";
		botao1.style = "cursor: pointer; position: relative; top: 20%;"
		botao1.onclick = function () {consultarAR()};		
		ancora1.parentElement.appendChild(botao1);
	}
	
	//botão "Procurar Execuções"
	let btProcurarExecucoes = await esperarElemento('button[id="extensaoPje_bt_gigs_2"]', null, 100);
	if (!btProcurarExecucoes) {
		// let ancora2 = await esperarElemento('button','Novo Executado');
		let ancora2 = await esperarElemento('div[id="checklist-exec"] mat-expansion-panel-header') 
		if (!ancora2) { return }				
		let botao2 = document.createElement("button");
		botao2.id = "extensaoPje_bt_gigs_2";
		botao2.textContent = "Procurar Execuções";
		botao2.style = "cursor: pointer; position: relative; margin-left: 10px;"
		botao2.onclick = function () {procurarExecucao()};		
		ancora2.appendChild(botao2);
	}
	
	//botões do Checklist da execução
	if (!document.getElementById("extensaoPje_barra_checklist")) {
		addBotaoChecklist();
	}
	
	function buscaARGigs(numAR, parte) {
		console.log("Extensão maisPJE (" + agora() + "):    |_ " + numAR + " : " + parte);		
		if (numAR != null) {
			let var1 = browser.storage.local.set({'tempAR': parte});
			Promise.all([var1]).then(values => {
				let parametros = 'dependent=yes,';					
				parametros += 'left=' + ((preferencias.gigsGigsWidth)-(520)) + ',';
				parametros += 'top=' + ((preferencias.gigsGigsHeight)-(520)) + ',';
				parametros += 'width=520px,';
				parametros += 'height=520px';
				window.open('https://rastreamento.correios.com.br/app/index.php?Registros='+numAR, '_blank', parametros);
			});
		} else {
			console.log("Extensão maisPJE (" + agora() + "): Registro(AR) não encontrado!");
			browser.runtime.sendMessage({tipo: 'criarAlerta', valor: 'Registro(AR) não encontrado!', icone: '1'});
		}
	}
}

function criarBotaoMenuLateral(element, id, texto, tooltip, onClick, img = undefined) {
	const elemento = document.createElement(element);
	elemento.id = id;
	elemento.textContent = texto;
	elemento.setAttribute('maisPje-tooltip-direita2',tooltip);
	elemento.setAttribute('aria-description',tooltip);
	elemento.style = "cursor: pointer; position: relative; top: 20%; width: 100%; padding: 5px; margin: 5px; height: 35px; z-index: 1; text-align: center;";
	elemento.onclick = onClick;
	if (img) {
		elemento.appendChild(img);
	}
	return elemento;
}
//FUNÇÃO RESPONSÁVEL POR ADICIONAR OS BOTÕES NA PÁGINA PRINCIPAL
async function addBotaoTelaPrincipal() {
	const urls = await obterUrlsConciliaJT();
	let check = setInterval(function() {
		if(document.getElementsByClassName("menu-lateral")[0]) {
			if (document.getElementById("maisPje_bt_principal_1")) {
				// console.log("já tem botao");
				clearInterval(check);
			} else {
				//DESCRIÇÃO: REGRA DO TOOLTIP
				if (!document.getElementById('maisPje_tooltip_direita2')) {
					tooltip('direita2');
				}
				// console.log("não tem botao");
				let el = document.getElementsByClassName("menu-lateral")[0];

				const powerbi = urls[preferencias.num_trt]?.powerbi;

				if (powerbi) {
					const abrirPowerBI = function () {  window.open(powerbi.url, '_blank'); };
					const illuminaImg = document.createElement("img");
					let texto = '';
					if (powerbi.img) {
						illuminaImg.src = browser.runtime.getURL(powerbi.img);
						illuminaImg.height = 40;
						illuminaImg.width = 40;
					} else {
						texto = powerbi.nome;
					}
					const botao0 = criarBotaoMenuLateral("a", "maisPje_bt_principal_0", texto, powerbi.nome, abrirPowerBI, illuminaImg);
					el.appendChild(botao0);
				}
				const botao1 = criarBotaoMenuLateral("button", "maisPje_bt_principal_1", 'Buscar AR', 'Atalho: Ctrl + 1', function () {consultarAR()});
				
				el.appendChild(botao1);

				const botao2 = criarBotaoMenuLateral("button", "maisPje_bt_principal_2", "PJe Antigo", 'Atalho: Ctrl + 2', function () { getAtalhosNovaAba().abrirPJeAntigo.abrirAtalhoemNovaJanela() });
				
				el.appendChild(botao2);

				const botao3 = criarBotaoMenuLateral("button", "maisPje_bt_principal_3", "Meu Filtro", 'Atalho: F2',
					function () {filtrarPorMeuFiltro()});

				el.appendChild(botao3);
				clearInterval(check);
			}
		}
	}, 100);	
}

//FUNÇÃO RESPONSÁVEL POR ADICIONAR O BOTÃO COPIAR NOS EXPEDIENTES/DESPACHOS/ANEXAR/ETC
async function addBotaoCopiarDocumento(id) {
	return new Promise(resolve => {
		//DESCRIÇÃO: REGRA DO TOOLTIP
		if (!document.getElementById('maisPje_tooltip_abaixo2')) {
			tooltip('abaixo2');
		}
		
		if (document.querySelector('div[class="cabecalho-direita"]')) {
			if (!document.getElementById("extensaoPje_bt_copiar_" + id)) {
				let ancora = document.querySelector("div[class*='cabecalho-direita']");
				let bt = document.createElement("button");
				bt.id = "extensaoPje_bt_copiar_" + id;
				bt.className = "mat-icon-button";
				bt.style="font-size: 1.1em;vertical-align: sub;"
				bt.setAttribute('maisPje-tooltip-abaixo2','Copiar');	
				bt.onclick = function () {copiarDocumentoProcesso(id)};
				let i = document.createElement("i");
				i.className = "fas fa-copy";
				bt.appendChild(i);
				ancora.appendChild(bt);
			}
		}
		resolve(true);
	});
}

async function addBotaoBotaoBuscaPersonalizada() {
	return new Promise(async resolve => {
		//Requisição de Pequeno Valor[Documentos]
		if (preferencias.AALote.length > 0) { return resolve(false) } //desativa quando vem das ações em lote
		let ancora = document.querySelector('pje-timeline-busca section');
		if (!ancora) {
			ancora = await esperarElemento('pje-timeline-busca section');
		}
		if (!ancora) { return resolve(false) }
		
		if (!document.getElementById('maisPje_busca_personalizada')) {
			let bt = document.createElement("button");
			bt.id = "maisPje_busca_personalizada";
			bt.title = "maisPJe: pesquisa personalizada";
			bt.className = "mat-icon-button";
			bt.style="font-size: 1.1em;vertical-align: sub;";
			bt.onclick = async function () {
				let doctosTimeline = await esperarColecao('ul[class="pje-timeline"] *',1,100);
				if (!doctosTimeline) { //se for nulo, busca todos os documentos
					let d = await esperarElemento('pje-timeline-busca mat-checkbox[aria-label="Documentos"]');
					d.firstElementChild.click();
					await preencherInput('input[name="Pesquisar movimentos e documentos da lista"]','');
					return;
				}
				
				if (this.style.color === 'orangered') {
					this.style.color = 'unset';
					this.title = 'maisPJe: pesquisa personalizada';
					
					doctosTimeline = await esperarColecao('ul[class="pje-timeline"] *[maisPje_PesquisaPersonalizada="true"]');
					if (!doctosTimeline) { 
						return;
					} //se for nulo
					for (const [pos, docto] of doctosTimeline.entries()) {
						docto.style.display = 'unset';
						if (docto.id == 'maisPje_PesquisaPersonalizada_dataDocumento') { docto.remove() }
					}
					
				} else {
					let opcoes = await criarCaixaCheckBox(['Documento','Conteúdo','Movimentos'], preferencias.timeline[1], 'Escolha o(s) filtro(s)');
					let expressao = await criarCaixaDePergunta('text', 'Pesquisa Personalizada:\n', preferencias.timeline[0], 'Experimente separando várias expressões com ";"(ponto e vírgula)');
					let guardarStorage = browser.storage.local.set({'timeline': [expressao,opcoes]});
					Promise.all([guardarStorage]).then(async values => {
						preferencias.timeline = [expressao,opcoes];
						// console.log(preferencias.timeline[1].toString());
						if (!preferencias.timeline[1].toString().includes('false,false,false')) {
							await filtrarOpcoes(preferencias.timeline[1]);
						}
						if (preferencias.timeline[0].length > 0) {
							await aplicarPesquisa(preferencias.timeline[0]) 
						}
					});
				}
				
			};
			let i = document.createElement("i");
			i.className = "fas fa-edit";
			bt.appendChild(i);
			ancora.appendChild(document.createElement("span"));
			ancora.appendChild(bt);
			
			if (!preferencias.timeline) { return resolve(false) }
			if (preferencias.gigsPesquisaDeDocumentos > 0) {
				// console.log(preferencias.timeline[1].toString());
				if (!preferencias.timeline[1].toString().includes('false,false,false')) {
					await filtrarOpcoes(preferencias.timeline[1]);
				}
				if (preferencias.timeline[0].length > 0) {
					await aplicarPesquisa(preferencias.timeline[0]) 
				}
			}			
		}
		resolve(true);
	});
	
	async function filtrarOpcoes(lista) {
		return new Promise(async resolve => {			
			await aguardarCarregamento();
			menuStatus(true);
			document.getElementById('maisPje_busca_personalizada').style.color = 'orangered';
			document.getElementById('maisPje_busca_personalizada').title = 'maisPJe: Desfazer Pesquisa Personalizada';
			
			let isPesquisarDocumento = lista[0];
			let isPesquisarConteudo = lista[1];
			let isPesquisarMovimentos = lista[2];
			
			//escolher apenas as opções que interessa
			await esperarElemento('pje-timeline-busca');
			
			let d = await esperarElemento('pje-timeline-busca mat-checkbox[aria-label="Documentos"]');
			// console.log('1: Pesquisar Documentos : É para marcar? ' + isPesquisarDocumento + " : veio marcado?" + d.className.includes('mat-checkbox-checked'));
			if (d.className.includes('mat-checkbox-checked')) { //já veio selecionado..
				if (!isPesquisarDocumento) { d.firstElementChild.click() }
			} else { //se não..
				if (isPesquisarDocumento) { d.firstElementChild.click() }
			}
			
			let c = await esperarElemento('pje-timeline-busca mat-checkbox[aria-label="Pesquisar Conteúdo"]');
			// console.log('2: Pesquisar Conteúdo : É para marcar? ' + isPesquisarConteudo + " : veio marcado?" + c.className.includes('mat-checkbox-checked'));
			if (c.className.includes('mat-checkbox-checked')) { //já veio selecionado..
				if (!isPesquisarConteudo) { c.firstElementChild.click() }
			} else { //se não..
				if (isPesquisarConteudo) { c.firstElementChild.click() }
			}
							
			let m = await esperarElemento('pje-timeline-busca mat-checkbox[aria-label="Movimentos"]');
			// console.log('3: Pesquisar Movimentos : É para marcar? ' + isPesquisarMovimentos + " : veio marcado?" + m.className.includes('mat-checkbox-checked'));
			if (m.className.includes('mat-checkbox-checked')) { //já veio selecionado..
				if (!isPesquisarMovimentos) { m.firstElementChild.click() }
			} else { //se não..
				if (isPesquisarMovimentos) { m.firstElementChild.click() }
			}
			
			await aguardarCarregamento(); //esperar o filtro ser aplicado e os documentos recarregados para depois prosseguir
			menuStatus(false);
			resolve(true);
		});
	}
	
	async function aplicarPesquisa(txt) {
		return new Promise(async resolve => {
			await aguardarCarregamento();
			menuStatus(true);
			document.getElementById('maisPje_busca_personalizada').style.color = 'orangered';
			document.getElementById('maisPje_busca_personalizada').title = 'maisPJe: Desfazer Pesquisa Personalizada';
			
			txt = txt.toLowerCase();
			let parametrosPesquisaMultipla = txt.split(';');
			// console.log(parametrosPesquisaMultipla.length)
			
			if (parametrosPesquisaMultipla.length > 1) {
				await preencherInput('input[name="Pesquisar movimentos e documentos da lista"]','');
				
				let doctosTimeline = await esperarColecao('ul[class="pje-timeline"] div[class="tl-item"]');
				for (const [pos, docto] of doctosTimeline.entries()) {
					
					//apaga Tudo
					docto.parentElement.style.display = 'none';
					docto.parentElement.setAttribute('maisPje_PesquisaPersonalizada','true');
					//apaga as datas
					let dataDocumento = docto.parentElement.querySelector('div[class*="tl-data"]');
					if (dataDocumento) {
						dataDocumento.style.display = 'none';
						dataDocumento.setAttribute('maisPje_PesquisaPersonalizada','true');
					}
					
					let map = [].map.call(
						parametrosPesquisaMultipla, 
						function(param) {
							
							if (removeAcento(docto.textContent.trim().toLowerCase()).includes(removeAcento(param.toLowerCase()))) {
								docto.parentElement.style.display = 'unset';
								//incluir a data
								let d = document.createElement('div');
								d.id = 'maisPje_PesquisaPersonalizada_dataDocumento';
								d.setAttribute('maisPje_PesquisaPersonalizada','true');
								d.style = 'background-color: #d6d6d6; border-radius: 10px; color: #444; font-size: .7em; margin-left: calc(50% - 35px); padding: 2px; position: static; text-align: center; width: 80px;';								
								let data = docto.querySelector('div[class="tl-item-hora"]').title;
								let padraoData = /\d{1,2}\/\d{1,2}\/\d{4}/gm;
								if (padraoData.test(data)) {
									data = data.match(padraoData).join();
									
									let x = data.split('/');
									let df = new Date(x[2],x[1]-1,x[0]);
									let year = new Intl.DateTimeFormat('pt', { year: 'numeric' }).format(df);
									let month = new Intl.DateTimeFormat('pt', { month: 'short' }).format(df);
									let day = new Intl.DateTimeFormat('pt', { day: '2-digit' }).format(df);
									data = day + ' ' + month + ' ' + year;
								}
								d.innerText = data;
								docto.parentElement.insertAdjacentElement('afterbegin', d);
							}
						}
					);
					
				}
				
				menuStatus(false);
				resolve(true);
				
				
			} else {
				
				await preencherInput('input[name="Pesquisar movimentos e documentos da lista"]',txt.trim());
				menuStatus(false);
				resolve(true);
			}
		});
	}
	
	async function aguardarCarregamento() {
		return new Promise(async resolve => {
			menuStatus(true);
			let doctosTimeline = await esperarColecao('ul[class="pje-timeline"] li[id*="doc_"]', 1);
			if (!doctosTimeline) { return resolve(true) } 
			let qtdeInicial = doctosTimeline.length;
			let qtdeFinal = -1;
			
			let check = setInterval(function() {
				doctosTimeline = document.querySelectorAll('ul[class="pje-timeline"] li[id*="doc_"]');
				qtdeFinal = doctosTimeline.length;
				// console.log('qtdeInicial(' + qtdeInicial + ') ::: qtdeFinal(' + qtdeFinal + ')');
				if (qtdeInicial == qtdeFinal) {
					clearInterval(check);
					menuStatus(false);
					return resolve(true);
				} else {
					qtdeInicial = qtdeFinal;
				}
			}, 1000);
		});
	}
}

//FUNÇÃO RESPONSÁVEL POR ADICIONAR O BOTÃO PRAZO EM LOTE NOS DESPACHOS/DECISÃO/SENTENÇA
async function addBotaoPrazoEmLote() {
	//INSERE O BOTÃO PARA INSERIR PRAZO EM LOTE
	if (!document.querySelector('pje-intimacao-automatica')) {
		return;
	} else {
		if (!document.getElementById('pjextension_prazoEmLote')) {
			var el = document.querySelector('div[class="controle-intimacao"]')
			var botao = document.createElement("button");
			botao.textContent = "Prazo em lote";
			botao.id = "pjextension_prazoEmLote";
			botao.style = "cursor: pointer; margin-left: 10px;"
			botao.onmouseenter = function () {
				if (!document.getElementById('maisPje_barra_bt_pzoLote')) {
					let barra_bt_pzoLote_temp = document.createElement("div");
					barra_bt_pzoLote_temp.id = "maisPje_barra_bt_pzoLote";
					barra_bt_pzoLote_temp.style = "z-index: 100; height: auto; position: absolute; background-color: rgb(255, 255, 255); text-align: center; border-radius: 3px; display: flex; flex-direction: column; align-items: center;margin-top: 5px;margin-left: -3px;";
					barra_bt_pzoLote_temp.onmouseleave = function (e) {
						barra_bt_pzoLote_temp.className = "maisPje-fade-out";
						setTimeout(function(){				
							document.getElementById('maisPje_barra_bt_pzoLote').remove();
						}, 250);
					};
					
					let bt0 = document.createElement("button");
					bt0.id = "maisPje_bt_pzoLote_0";
					bt0.textContent = "0 dias";
					bt0.className = "mat-raised-button mat-primary ng-star-inserted";
					bt0.style = "cursor: pointer; margin: 5px; min-width: 5vw; background-color: gray;";
					bt0.onclick = function () {
						document.getElementById('maisPje_barra_bt_pzoLote').remove();
						executar("0");
					};
					barra_bt_pzoLote_temp.appendChild(bt0);
					
					let bt2 = document.createElement("button");
					bt2.id = "maisPje_bt_pzoLote_2";
					bt2.textContent = "2 dias";
					bt2.className = "mat-raised-button mat-primary ng-star-inserted";
					bt2.style = "cursor: pointer; margin: 5px; min-width: 5vw; background-color: gray !important;";
					bt2.onclick = function () {
						document.getElementById('maisPje_barra_bt_pzoLote').remove();
						executar("2");
					};
					barra_bt_pzoLote_temp.appendChild(bt2);
					
					let bt5 = document.createElement("button");
					bt5.id = "maisPje_bt_pzoLote_5";
					bt5.textContent = "5 dias";
					bt5.className = "mat-raised-button mat-primary ng-star-inserted";
					bt5.style = "cursor: pointer; margin: 5px; min-width: 5vw; background-color: gray !important;";
					bt5.onclick = function () {
						document.getElementById('maisPje_barra_bt_pzoLote').remove();
						executar("5");
					};
					barra_bt_pzoLote_temp.appendChild(bt5);
					
					let bt8 = document.createElement("button");
					bt8.id = "maisPje_bt_pzoLote_8";
					bt8.textContent = "8 dias";
					bt8.className = "mat-raised-button mat-primary ng-star-inserted";
					bt8.style = "cursor: pointer; margin: 5px; min-width: 5vw; background-color: gray !important;";
					bt8.onclick = function () {
						document.getElementById('maisPje_barra_bt_pzoLote').remove();
						executar("8");
					};
					barra_bt_pzoLote_temp.appendChild(bt8);
					
					let bt10 = document.createElement("button");
					bt10.id = "maisPje_bt_pzoLote_10";
					bt10.textContent = "10 dias";
					bt10.className = "mat-raised-button mat-primary ng-star-inserted";
					bt10.style = "cursor: pointer; margin: 5px; min-width: 5vw; background-color: gray !important;";
					bt10.onclick = function () {
						document.getElementById('maisPje_barra_bt_pzoLote').remove();
						executar("10");
					};
					barra_bt_pzoLote_temp.appendChild(bt10);
					
					let bt15 = document.createElement("button");
					bt15.id = "maisPje_bt_pzoLote_15";
					bt15.textContent = "15 dias";
					bt15.className = "mat-raised-button mat-primary ng-star-inserted";
					bt15.style = "cursor: pointer; margin: 5px; min-width: 5vw; background-color: gray !important;";
					bt15.onclick = function () {
						document.getElementById('maisPje_barra_bt_pzoLote').remove();
						executar("15");
					};
					barra_bt_pzoLote_temp.appendChild(bt15);
					
					let bt_outro = document.createElement("button");
					bt_outro.id = "maisPje_bt_pzoLote_outros";
					bt_outro.textContent = "outro";
					bt_outro.className = "mat-raised-button mat-primary ng-star-inserted";
					bt_outro.style = "cursor: pointer; margin: 5px; min-width: 5vw; background-color: gray !important;";
					bt_outro.onclick = function () {
						document.getElementById('maisPje_barra_bt_pzoLote').remove();
						executar(prompt('Digite o prazo em dias Úteis:\n',''));
					};
					barra_bt_pzoLote_temp.appendChild(bt_outro);
					
					botao.appendChild(barra_bt_pzoLote_temp);
				}
			};			
			el.appendChild(botao);
		}
	}
	
	async function executar(prazoEmLote) {
		let el = document.querySelectorAll('mat-form-field[class*="prazo"]');
		if (!el) {
			return
		}
		fundo(true);
		
		let map = [].map.call(
			el, 
			function(elemento) {				
				let el2 = elemento.querySelector('input');
				el2.focus();
				el2.value = prazoEmLote;
				triggerEvent(el2, 'input');
			}
		);
		
		await clicarBotao('button', 'Gravar', true);
		fundo(false);
	}
}

//FUNÇÃO RESPONSÁVEL POR ADICIONAR O BOTÃO DE MARCAR/DESMARCAR TODOS OS CHECKBOXES
async function addBotaoMarcarDesmarcarTodos() {
	//INSERE O BOTÃO PARA INSERIR CHECK MARCAR/DESMARCAR TODOS
	let ancora = await esperarElemento('pje-intimacao-automatica');
	if (!ancora) {
		return;
	} else {
		let el = ancora.querySelector('div[class="cabecalho"]').nextSibling;
		
		if (!document.getElementById('maisPje_desmarcar')) {
			let ckbox1 = document.createElement("button");
			ckbox1.id = "maisPje_desmarcar";
			ckbox1.innerText = "Desmarcar Todos";
			ckbox1.style = 'cursor: pointer; padding: 10px; background-color: rgb(250, 250, 250); filter: brightness(1); font-size: 14px; color: gray; border: 0; border-radius: 25px;';
			ckbox1.onmouseenter  = function () { this.style.filter = 'brightness(0.95)' }
			ckbox1.onmouseleave  = function () { this.style.filter = 'brightness(1)' }
			ckbox1.onclick = function () { fundo(true);executar('1', ancora, ckbox1.checked); };
			el.appendChild(ckbox1);
		}
		
		if (!document.getElementById('maisPje_marcar')) {
			let ckbox2 = document.createElement("button");
			ckbox2.id = "maisPje_marcar";
			ckbox2.innerText = "Marcar Todos";
			ckbox2.style = 'cursor: pointer; padding: 10px; background-color: rgb(250, 250, 250); filter: brightness(1); font-size: 14px; color: gray; border: 0; border-radius: 25px; margin: 0px 14px 0px 14px;';
			ckbox2.onmouseenter  = function () { this.style.filter = 'brightness(0.95)' }
			ckbox2.onmouseleave  = function () { this.style.filter = 'brightness(1)' }
			ckbox2.onclick = function () { fundo(true); executar('2', ancora, ckbox2.checked); };
			el.appendChild(ckbox2);
		}
		
		if (!document.getElementById('maisPje_inverter')) {
			let ckbox3 = document.createElement("button");
			ckbox3.id = "maisPje_inverter";
			ckbox3.innerText = "Inverter Selecionados";
			ckbox3.style = 'cursor: pointer; padding: 10px; background-color: rgb(250, 250, 250); filter: brightness(1); font-size: 14px; color: gray; border: 0; border-radius: 25px;';
			ckbox3.onmouseenter  = function () { this.style.filter = 'brightness(0.95)' }
			ckbox3.onmouseleave  = function () { this.style.filter = 'brightness(1)' }
			ckbox3.onclick = function () { fundo(true); executar('3', ancora, ckbox3.checked); };
			el.appendChild(ckbox3);
		}
	}
	
	function executar(opcao, ancora, valor) {
		console.log(valor);
		if (!ancora) { return }
		let el = ancora.querySelectorAll('table input[aria-label="Intimar parte"]');
		if (!el) { return }
		
		let map = [].map.call(
			el, 
			function(elemento) {
				console.log(elemento.checked);
				if (opcao === '1') { // Desmarcar Todos
					if (elemento.checked) {
						elemento.click();
					}
				}
				
				if (opcao === '2') { // Marcar Todos
					if (!elemento.checked) {
						elemento.click();
					}
				}
				
				if (opcao === '3') { // Inverter selecionados
					elemento.click();
				}
			}
		);
		fundo(false);
	}
}

//FUNÇÃO RESPONSÁVEL POR ADICIONAR O BOTÃO TIPO EM LOTE NOS ANEXOS DA CERTIDÃO
function addBotaoTipoEmLote() {
	//INSERE O BOTÃO PARA INSERIR TIPO EM LOTE
	if (!preferencias.extrasSugerirTipoAoAnexar && !preferencias.extrasSugerirDescricaoAoAnexar) {
		return;
	}
	
	if (!document.querySelector('pje-anexar-pdfs')) {
		return;
	} else {
		if (!document.getElementById('pjextension_tipoEmLote')) {
			var el = document.querySelector('pje-anexar-pdfs')
			var botao = document.createElement("button");
			botao.textContent = "Tipo em lote";
			botao.id = "pjextension_tipoEmLote";
			botao.style = "cursor: pointer; margin-left: 10px;"
			botao.onclick = function () {executar()};
			el.insertBefore(botao, el.firstElementChild);
		}
	}
	
	async function executar() {
		let anexos = document.querySelectorAll('pje-item-lista-anexo-pdf');
		if (!anexos) {
			return
		}
		
		fundo(true);		
		for (const [pos, anexo] of anexos.entries()) {
			let apenasOsNovos = anexo.querySelectorAll('.status-anexo-nao-salvo');
			if (apenasOsNovos.length > 0) { await corrigirAnexos(anexo) }
		}
		fundo(false);
		
		if (preferencias.extrasSugerirTipoAoAnexar) {
			await clicarBotao('button[aria-label="Salvar"]', null, true);
		}
		
		async function corrigirAnexos(elemento) {
			return new Promise(async resolve => {
				if (elemento.querySelector('input[aria-label="Tipo de Documento"]').value == "") {
					let padraoEncontrado = await procuraPadrao(elemento.querySelector('input[aria-label="Descrição"]').value);
					// console.log(padraoEncontrado.tipo + " : " + padraoEncontrado.descricao);
					
					if (preferencias.extrasSugerirDescricaoAoAnexar) {
						if (padraoEncontrado.descricao != '') {
							let inputDescricao = elemento.querySelector('input[aria-label="Descrição"]');
							await preencherInput(inputDescricao,padraoEncontrado.descricao);
							let labelDescricao = elemento.querySelector('label[for="' + inputDescricao.id + '"] span');
							labelDescricao.innerText = labelDescricao.innerText + ' (sugestão pelo +PJe) - anterior:' + padraoEncontrado.anterior;
							
						}
					}
					
					if (preferencias.extrasSugerirTipoAoAnexar) {
						let inputTipo = elemento.querySelector('input[aria-label="Tipo de Documento"]');					
						await escolherOpcao(inputTipo,padraoEncontrado.tipo,5);
						let labelTipo = elemento.querySelector('label[for="' + inputTipo.id + '"] span');
						labelTipo.innerText = labelTipo.innerText + ' (sugestão pelo +PJe)';
					}
					
					return resolve(true);
				}
				return resolve(false);
			});
		}
		
		async function procuraPadrao(texto) {
			return new Promise(async resolve => {
				let padraoSISBAJUD = /\d{14}\_\d{8}/gm;
				let padraoCCS = /\d{17}\-\d{12}\-/gm;
				let padraoDossieMedico = /\DOSSIE\_\d{11,}/gm;
				let padraoEmail = /(e.?mail)/gmi;
				let padraoRegistroImoveis = /(registro\sde\sim.veis)|(\sCRI\sde\s)|(\d{1,2}\SRI\sde\s)/gmi;
				let padraoRegistroImoveis2 = /(mat.?\s?(?:\.|,|[0-9])*)/gmi;
				let padraoARISP = /[A-Za-z0-9]{32}/gm;
				let padraoContaSIF = /\d{4}\.\d{3}\.\d{8}\-\d{1}/gm;
				let padraoContaBB = /\d{4}\.\d{12,13}/gm;
				
				//OPÇÕES DE JUNTADA DE ENDEREÇO
				let campoDescricaoTexto = document.querySelector('div[class="metadados"] input[aria-label="Descrição"]').value;
				if (campoDescricaoTexto.toLowerCase().includes('endereço')) {
					
					if (texto.toLowerCase().includes('renajud')) {
						return resolve({tipo:'Renajud (consulta)',descricao:'endereço RENAJUD',anterior:texto});
					}
					
					if (padraoSISBAJUD.test(texto)) {
						return resolve({tipo:'Documento Diverso',descricao:'endereço SISBAJUD',anterior:texto});
					}
					
					if (texto.includes('carta-ordem-endereco')) {
						return resolve({tipo:'Documento Diverso',descricao:'endereço SERASAJUD',anterior:texto});		
					}
					
					if (texto.toLowerCase().includes('sniper')) {
						return resolve({tipo:'Documento Diverso',descricao:'endereço SNIPER',anterior:texto});		
					}
					
					if (texto.toLowerCase().includes('casan')) {
						return resolve({tipo:'Documento Diverso',descricao:'endereço CASAN',anterior:texto});		
					}
					
					if (texto.toLowerCase().includes('celesc')) {
						return resolve({tipo:'Documento Diverso',descricao:'endereço CELESC',anterior:texto});		
					}
					
					return resolve({tipo:'Documento Diverso',descricao:texto,anterior:texto});
				//OPÇÕES DE JUNTADA DIVERSO
				} else {
					
					if (texto.toLowerCase().includes('renajud')) {
						return resolve({tipo:'Renajud (consulta)',descricao:texto,anterior:texto});
					}
					
					if (padraoSISBAJUD.test(texto)) {
						return resolve({tipo:'Sisbajud (bloqueio)',descricao:texto,anterior:texto});
					}
					
					if (texto.toLowerCase().includes('carta-ordem-endereco')) {
						return resolve({tipo:'Documento Diverso',descricao:'Ordem SERASAJUD',anterior:texto});		
					}
					
					if (texto.toLowerCase().includes('Sniper')) {
						return resolve({tipo:'Documento Diverso',descricao:'Relatório SNIPER',anterior:texto});		
					}
					
					if (texto.toLowerCase().includes('censec')) {
						return resolve({tipo:'Documento Diverso',descricao:'Relatório CENSEC',anterior:texto});		
					}
					
					if (padraoCCS.test(texto)) {
						return resolve({tipo:'Documento Diverso',descricao:'Relatório CCS',anterior:texto});
					}
					
					if (padraoDossieMedico.test(texto)) {
						return resolve({tipo:'Documento Diverso',descricao:'DOSSIE_médico',anterior:texto});
					}
					
					if (padraoRegistroImoveis.test(texto)) {
						return resolve({tipo:'Certidão do Cartório de Registro de Imóveis',descricao:texto,anterior:texto});
					}
					
					if (padraoRegistroImoveis2.test(texto)) {
						return resolve({tipo:'Certidão do Cartório de Registro de Imóveis',descricao:texto,anterior:texto});
					}
					
					if (padraoEmail.test(texto)) {
						return resolve({tipo:'Correspondência ou Mensagem Eletrônica/E-mail',descricao:texto,anterior:texto});
					}
					
					if (padraoARISP.test(texto)) {
						return resolve({tipo:'Documento Diverso',descricao:'Cópia de Matrícula',anterior:texto});
					}					
					
					if (texto.toLowerCase().includes('extrato') && !texto.toLowerCase().includes('cnis')) {
						return resolve({tipo:'Extrato Bancário',descricao:texto,anterior:texto});
					}
					
					if (padraoContaSIF.test(texto)) {
						return resolve({tipo:'Extrato Bancário',descricao:texto,anterior:texto});
					}
					
					if (padraoContaBB.test(texto)) {
						return resolve({tipo:'Extrato Bancário',descricao:texto,anterior:texto});
					}
					
					if (texto.toLowerCase().includes('Cnpjreva_Comprovante.asp')) {
						return resolve({tipo:'Documento Diverso',descricao:'CNPJ - RFB Situação Cadastral',anterior:texto});
					}
					
					if (texto.toLowerCase().includes('ConsultaPublicaExibir.asp')) {
						return resolve({tipo:'Documento Diverso',descricao:'CPF - RFB Situação Cadastral',anterior:texto});
					}
					
					return resolve({tipo:'Documento Diverso',descricao:texto,anterior:texto});
				}
				
				
			});
		}
		
	}
	
}

//FUNÇÕES RESPONSÁVEIS POR CRIAR A ESTRUTURA DOS BOTÕES QUE REPRESENTAM AS AÇÕES AUTOMATIZADAS
async function criarContainer(idContainer='',btFecharOn=false) {
	return new Promise(
		async resolver => {
			window.focus();
			let barra = document.querySelector('maisPjeContainerAA');
			if (barra?.id == idContainer) { return }			
			if (barra) { barra.remove() }				
			let ancora = await esperarElemento('div[class*="painel-principal"]');
			ancora.lastElementChild.previousSibling.firstElementChild.style = "height: calc(100vh - 142px)";//corrige a altura da timeline
			barra = document.createElement("maisPjeContainerAA");
			barra.id = idContainer;
			barra.style = "height: auto; background-color: rgb(255, 255, 255); border-bottom: 1px solid lightgray; margin-top: 5px; padding-right: 2vw; box-shadow: none; text-align: center; overflow-y: auto; min-height: 50vh;";
			
			if (btFecharOn) {
				let btFecharContainer = document.createElement('button');
				btFecharContainer.style = "position: absolute;cursor: pointer;right: 0;border: none;border-radius: .3vw;width: 1.5vw;height: 1.5vw;background-color:#fdcbc2;--color1: #fdcbc2;--color2: tomato;color: white;font-size: 1.2em;margin: 0.1vw 0.2vw 0vw 0vw; opacity: .5;";
				btFecharContainer.title = 'Fechar';
				btFecharContainer.onmouseenter = function () { this.style.opacity = '1'; }
				btFecharContainer.onmouseleave = function () { this.style.opacity = '.5'; }
				btFecharContainer.onclick = function () { 
					barra.remove();
					corrigirPosicaoElementos();
				}
				let icone = document.createElement('i');
				icone.className = "fa-times fas";
				btFecharContainer.appendChild(icone);
				
				
				
				//aplica à barra o efeito de ao sair dela iniciar a contagem para encerrar o container
				let check;
				let mouseEmCima = false; 
				barra.onmouseleave = function (event) {				
					event.preventDefault();
					if (mouseEmCima) { return }
					// console.log('entrou')
					btFecharContainer.style.animation = 'trocarCorGeral .8s';
					mouseEmCima = true;
					let seg = 1;
					check = setInterval(function() {
						seg--;
						if (mouseEmCima && seg < 1) {
							clearInterval(check);
							mouseEmCima = false;
							window.focus();
							btFecharContainer.click();
						}			
						
					}, 800);
				};
				barra.onmouseenter = function (event) {				
					event.preventDefault();
					btFecharContainer.style.animation = 'unset';
					mouseEmCima = false;
					clearInterval(check);
				};
				
				
				
				barra.appendChild(btFecharContainer);
				
			} else {
				barra.onmouseleave = function () {
					this.remove();
					corrigirPosicaoElementos();
				}
			}
			
			ancora.insertBefore(barra, ancora.firstElementChild.nextSibling);
			resolver(true);
		}
	);
}

async function montarBotoes(lista, acao) {
	return new Promise(async resolve => {
		for (const [pos, aa] of lista.entries()) {
			await criarBotao('maisPjeContainerAA', pos, aa.nm_botao, aa.cor, aa.visibilidade, acao, aa.vinculo);
		}
		corrigirPosicaoElementos();
		resolve(true);
	});
}

async function criarBotao(container, id, nm_botao, cor, visivel, acao, v=['Nenhum']) {
	return new Promise(async resolve => {
		ancora = await esperarElemento(container);
		let bt = document.createElement("button");
		bt.id = id;
		bt.name = nm_botao;
		bt.className = "mat-raised-button mat-primary ng-star-inserted";
		if (visivel == "sim") {
			bt.style = "margin: 3px; z-index: 5;" + (cor != "" ? "background-color: " + cor + ";" : "");
		} else {
			bt.style = "display: none;";
		}
		bt.onclick = acao;
		bt.onmouseenter = function() { criarMapaDosVinculos(nm_botao,v,nm_botao) }
		bt.onmouseleave = function() { if (document.getElementById('maisPjeContainerMapaVinculos')) { document.getElementById('maisPjeContainerMapaVinculos').remove() }}
		
		
		let span = document.createElement("span");
		span.className = "mat-button-wrapper";
		span.innerText = nm_botao;
		bt.appendChild(span);
		
		//perfumaria
		if (v.length > 1 && v != "Nenhum") {
			let perfumaria = document.createElement("span");
			perfumaria.style = "position: absolute; width: 7px; height: 10px; background-color: white; clip-path: polygon(25% 0%, 70% 0%, 40% 35%, 95% 35%, 20% 100%, 40% 55%, 0% 55%); right: 8px; margin: 0.6em -0.3em;"
			bt.appendChild(perfumaria);
		}
		
		ancora.appendChild(bt);
		resolve(true);
	});
}

async function corrigirPosicaoElementos() {
	let ancora = await esperarElemento('button[aria-label="Filtrar"]');
	if (!ancora) { return }
	let altura = ancora.getBoundingClientRect().bottom + 29;
	//move o botão "Esconder Linha do Tempo" para cima
	if (document.querySelector('button[aria-label="Esconder Linha do Tempo"]')) {
		document.querySelector('button[aria-label="Esconder Linha do Tempo"]').style = "top: " + altura + "px;";
	}
	//move o botão "Esconder o GIGS" para cima
	if (document.querySelector('button[aria-label="Esconder o GIGS"]')) {
		document.querySelector('button[aria-label="Esconder o GIGS"]').style = "top: " + altura + "px;";
	}
	//move o botão "Mostrar o GIGS" para cima
	if (document.querySelector('button[aria-label="Mostrar o GIGS"]')) {
		document.querySelector('button[aria-label="Mostrar o GIGS"]').style = "top: " + altura + "px;";
	}
	
}
//*********************************************************************************************

//FUNÇÃO RESPONSÁVEL POR ADICIONAR OS BOTÕES DAS AÇÕES NA PÁGINA ANEXAR DOCUMENTOS
async function addBotaoTelaAnexar() {
	return new Promise(async resolve => {
		await criarContainer('addBotaoTelaAnexar',true);
		await montarBotoes(
			preferencias.aaAnexar,
			function() {
				let var1 = browser.storage.local.set({'tempBt': ['acao_bt_aaAnexar', this.id]});
				Promise.all([var1]).then(values => {
					acaoBotaoDetalhes("Anexar Documentos");
				});
			}
		);
		await sleep(500);
		resolve(true);
	});
}

//FUNÇÃO RESPONSÁVEL POR ADICIONAR OS BOTÕES NA PÁGINA DETALHES - COMUNICAÇÕES
async function addBotaoTelaComunicacoes() {	
	return new Promise(async resolve => {
		await criarContainer('addBotaoTelaComunicacoes',true);
		await montarBotoes(
			preferencias.aaComunicacao,
			function() {
				let expedientes_especiais = ['Alvará','Auto / carta','Carta','Certidão','Requisição', 'Certidão de Crédito para Habilitação no Juízo Falimentar', 'Certidão de Crédito Trabalhista', 'Certidão de Praça/Leilão'];
				let tipo = preferencias.aaComunicacao[this.id].tipo;
				let fluxo = (!preferencias.aaComunicacao[this.id].fluxo) ? 'não' : preferencias.aaComunicacao[this.id].fluxo;
				if (expedientes_especiais.indexOf(tipo) > -1 || fluxo.toLowerCase() == 'sim') {
					console.log("     |___expediente especial");
					let var1 = browser.storage.local.set({'temp_expediente_especial': this.id});
					Promise.all([var1]).then(values => {
						let var2 = browser.storage.local.set({'tempBt': ['acao_bt_aaMovimento', 999]});
						Promise.all([var2]).then(values => {
							abrirTarefaDoProcesso();
						});
					});
					
				} else {
					console.log("     |___expediente comum");
					let var1 = browser.storage.local.set({'tempBt': ['acao_bt_aaComunicacao', this.id]});
					Promise.all([var1]).then(values => {
						acaoBotaoDetalhes("Abre a tela de Comunicações e Expedientes");
					});
				}
			}
		);
		await sleep(500);
		resolve(true);
	});
}

//FUNÇÃO RESPONSÁVEL POR ADICIONAR OS BOTÕES NA PÁGINA DETALHES - AUTOGIGS
async function addBotaoAutoGigs() {
	return new Promise(async resolve => {
		await criarContainer('addBotaoAutoGigs',true);
		await montarBotoes(
			preferencias.aaAutogigs,
			function() {
				let var1 = browser.storage.local.set({'tempBt': ['acao_bt_aaAutogigs', 999]});
				Promise.all([var1]).then(values => {
					acao_bt_aaAutogigs(this.id);
					browser.runtime.sendMessage({tipo: 'storage_limpar', valor: 'tempBt'});
				});
			}
		);
		await sleep(500);
		resolve(true);
	});
}

//FUNÇÃO RESPONSÁVEL POR ADICIONAR OS BOTÕES NA PÁGINA DETALHES - DESPACHO
async function addBotaoDespacho() {
	return new Promise(async resolve => {
		await criarContainer('addBotaoDespacho',true);
		await montarBotoes(
			preferencias.aaDespacho,
			function() {
				let guardarStorage = browser.storage.local.set({'tempBt': ['acao_bt_aaDespacho', this.id]});
				Promise.all([guardarStorage]).then(values => {
					if (preferencias.gigsApreciarPeticoes2) {
						console.log("Extensão maisPJE (" + agora() + "): apreciarPeticoes() - a partir de DETALHES");
						apreciarPeticoes();
						abrirTarefaDoProcesso();
					} else {
						abrirTarefaDoProcesso();
					}
				});
			}
		);	
		await sleep(500);
		resolve(true);
	});
}

//FUNÇÃO RESPONSÁVEL POR ADICIONAR OS BOTÕES NA PÁGINA DETALHES - MOVIMENTOS
async function addBotaoMovimento() {
	return new Promise(async resolve => {
		await criarContainer('addBotaoMovimento',true);
		//CRIA O BOTÃO DE ATUALIZAR TAREFA. 
		//Ele joga o processo pAra análise e devolve para a tarefa que estava anteriormente. O objetivo é reiniciar a contagem do prazo "na tarefa desde"
		await criarBotaoAtualizar();
		await montarBotoes(
			preferencias.aaMovimento,
			function() {
				let var1 = browser.storage.local.set({'tempBt': ['acao_bt_aaMovimento', this.id]});
				Promise.all([var1]).then(values => {
					if (preferencias.gigsApreciarPeticoes3) {
						console.log("Extensão maisPJE (" + agora() + "): apreciarPeticoes() - a partir de DETALHES");
						apreciarPeticoes();
						abrirTarefaDoProcesso();
					} else {
						abrirTarefaDoProcesso();
					}
				});
			}
		);
		await sleep(500);
		resolve(true);
	});
	
	async function criarBotaoAtualizar() {
		return new Promise(async resolve => {
			ancora = await esperarElemento('maisPjeContainerAA');
			let bt = document.createElement("button");
			bt.id = 998;
			bt.name = 'bt_atualizar_tarefa';
			bt.className = "mat-raised-button mat-primary ng-star-inserted";
			bt.style = "margin: 3px; z-index: 5; background-color: rgb(55, 71, 79);";
			bt.onclick = function() {
				let var1 = browser.storage.local.set({'tempBt': ['acao_bt_aaMovimento', 998]});
				Promise.all([var1]).then(values => {
					abrirTarefaDoProcesso();
				});
			}
			let i = document.createElement("i");
			i.className = "fa fa-sync fa-lg";
			bt.appendChild(i);
			ancora.appendChild(bt);
			resolve(true);
		});
	}
}

//FUNÇÃO RESPONSÁVEL POR ADICIONAR OS BOTÕES NA PÁGINA GIGS - CHECKLIST
async function addBotaoChecklist() {
	let ancora = await esperarElemento('pje-gigs-checklist-execucao mat-expansion-panel')
	if (!ancora) { return }
	if (!document.getElementById("extensaoPje_barra_checklist")) {				
		let barra = document.createElement("div");
		barra.id = "extensaoPje_barra_checklist";
		barra.style = "height: auto; background-color: rgb(255, 255, 255); margin-top: 5px; padding: 0px; box-shadow: none; text-align: center;display: unset;";
		ancora.insertBefore(barra, ancora.firstElementChild.nextSibling);
		
		
		let barraOcultar = document.createElement('div');
		barraOcultar.id = "extensaoPje_barra_checklist_ocultar";
		barraOcultar.style = "text-align: center;font-size: 1.3vh;height: 2vh;border: 2px solid #e0e0e0;border-radius: 5px;border-top-color: #e0e0e0;background-color: #f7f7f7;position: relative;top: -5px;cursor: pointer;color: dimgray;";
		barraOcultar.setAttribute('maisPJe_exibir','true');
		barraOcultar.innerText = "Ocultar Ações Automatizadas";
		
		barraOcultar.onclick = function () {
			// console.log(this.hasAttribute('maisPJe_exibir'));
			if (this.hasAttribute('maisPJe_exibir')) {
				document.getElementById('extensaoPje_barra_checklist').style.display = 'none';
				this.removeAttribute('maisPJe_exibir');
				this.innerText = "Mostrar Ações Automatizadas";
			} else {
				document.getElementById('extensaoPje_barra_checklist').style.display = 'unset';
				this.setAttribute('maisPJe_exibir','true');
				this.innerText = "Ocultar Ações Automatizadas";
			}
		}
		
		ancora.insertBefore(barraOcultar, ancora.firstElementChild.nextSibling);
		
		await montarBotoes();
		
		
	}
	
	function montarBotoes() {
		let aaChecklist_temp = preferencias.aaChecklist;
		
		// console.log(aaChecklist_temp.length)
		if (aaChecklist_temp.length > 0) {
			
			for (let i = 0; i < aaChecklist_temp.length; i++) {		
				let aa = aaChecklist_temp[i];
				criaBotao(i, aa.nm_botao, aa.cor, aa.visibilidade, aa.vinculo);
			}
			
			document.getElementById("extensaoPje_barra_checklist_ocultar").click();
		} else {
			document.getElementById("extensaoPje_barra_checklist_ocultar").style.display = 'none';
		}
		
		
	}
	
	function criaBotao(id, nm_botao, cor, visivel, vinculo) {
		let el = document.getElementById("extensaoPje_barra_checklist");
		let bt = document.createElement("button");
		bt.id = "botao_checklist_" + id;
		bt.name = "botao_checklist_" + nm_botao;
		bt.className = "mat-raised-button mat-primary ng-star-inserted";
		
		if (visivel == "sim") {
			bt.style = "margin: 3px; z-index: 3;" + (cor != "" ? "background-color: " + cor + ";" : "");
		} else {
			bt.style = "display: none;";
		}
		
		bt.onclick = function () {
			acao_bt_aaChecklist(id);
		};
		let span = document.createElement("span");
		span.className = "mat-button-wrapper";
		span.innerText = nm_botao;
		bt.appendChild(span);
		
		//perfumaria
		// console.log(vinculo + " : " + vinculo.length);
		if (vinculo.length > 1 && vinculo != "Nenhum") {
			let perfumaria = document.createElement("span");
			perfumaria.style = "position: absolute; width: 7px; height: 10px; background-color: white; clip-path: polygon(25% 0%, 70% 0%, 40% 35%, 95% 35%, 20% 100%, 40% 55%, 0% 55%); right: 8px; margin: 0.6em -0.3em;"
			bt.appendChild(perfumaria);
		}
		
		el.appendChild(bt);
	}	
}

//FUNÇÃO RESPONSÁVEL POR ADICIONAR OS BOTÕES NA PÁGINA DETALHES - RETIFICAR AUTUAÇÃO
async function addBotaoRetificarAutuacao() {
	return new Promise(async resolve => {
		await criarContainer('addBotaoRetificarAutuacao',true);
		await montarBotoes();
		await sleep(500);
		resolve(true);
	});
	
	function montarBotoes() {
		return new Promise(async resolve => {
			criaBotao();
			corrigirPosicaoElementos();
			resolve(true);
		});
	}
	
	function criaBotao() {
		let el = document.querySelector('maisPjeContainerAA');
		
		//DESCRIÇÃO: BOTÃO ADICIONAR ADVOGADO À PARTE
		let bt3 = document.createElement("button");
		bt3.id = "botao_retificar_autuacao_2";
		bt3.name = "botao_retificar_autuacao_CadastrarAdv";
		bt3.className = "mat-raised-button mat-primary ng-star-inserted";
		bt3.style = "margin: 3px; z-index: 5;";
		bt3.onmouseenter  = function () {
			if (!document.getElementById('maisPje_barra_bt_RAAdv')) {
				let barra_atalhos_temp = document.createElement("div");
				barra_atalhos_temp.id = "maisPje_barra_bt_RAAdv";
				barra_atalhos_temp.style = "z-index: 100; width: 100%; height: auto; position: absolute; background-color: rgb(255, 255, 255); text-align: center; border-radius: 3px; display: flex; flex-direction: column-reverse; align-items: center;margin-top: 5px;";
				barra_atalhos_temp.onmouseleave = function (e) {
					barra_atalhos_temp.className = "maisPje-fade-out";
					setTimeout(function(){				
						document.getElementById('maisPje_barra_bt_RAAdv').remove();
					}, 250);
				};
				
				let bt3a = document.createElement("button");
				bt3a.id = "maisPje_bt_autor";
				bt3a.textContent = "Polo Ativo";
				bt3a.className = "mat-raised-button mat-primary ng-star-inserted";
				bt3a.style = "cursor: pointer; margin: 5px; min-width: 5vw; background-color: gray;";
				bt3a.onclick = function () {
					document.getElementById('maisPje_barra_bt_RAAdv').remove();
					let resp = prompt('Digite o CPF ou o NOME do advogado:','');
					if (resp) {
						let var1 = browser.storage.local.set({'tempBt': ['acao_bt_retificarAutuacao', [2, resp]]}); //2 - autor
						Promise.all([var1]).then(values => {
							acaoBotaoDetalhes("Retificar autuação");
						});
					}
				};
				barra_atalhos_temp.appendChild(bt3a);
				
				let bt3b = document.createElement("button");
				bt3b.id = "maisPje_bt_reu";
				bt3b.textContent = "Polo Passivo";
				bt3b.className = "mat-raised-button mat-primary ng-star-inserted";
				bt3b.style = "cursor: pointer; margin: 5px; min-width: 5vw; background-color: gray !important;";
				bt3b.onclick = function () {
					document.getElementById('maisPje_barra_bt_RAAdv').remove();
					let resp = prompt('Digite o CPF ou o NOME do advogado:','');
					if (resp) {
						let var1 = browser.storage.local.set({'tempBt': ['acao_bt_retificarAutuacao', [3, resp]]}); // 3 - reu
						Promise.all([var1]).then(values => {
							acaoBotaoDetalhes("Retificar autuação");
						});
					}
				};
				barra_atalhos_temp.appendChild(bt3b);

				let bt3c = document.createElement("button");
				bt3c.id = "maisPje_bt_terceiro";
				bt3c.textContent = "Terceiro Interessado";
				bt3c.className = "mat-raised-button mat-primary ng-star-inserted";
				bt3c.style = "cursor: pointer; margin: 5px; min-width: 5vw; background-color: gray !important;";
				bt3c.onclick = function () {
					document.getElementById('maisPje_barra_bt_RAAdv').remove();
					let resp = prompt('Digite o CPF ou o NOME do advogado:','');
					if (resp) {
						let var1 = browser.storage.local.set({'tempBt': ['acao_bt_retificarAutuacao', [14, resp]]}); // 14 - terceiro interessado
						Promise.all([var1]).then(values => {
							acaoBotaoDetalhes("Retificar autuação");
						});
					}
				};
				barra_atalhos_temp.appendChild(bt3c);
				
				bt3.appendChild(barra_atalhos_temp);
			}
		};
		let span3 = document.createElement("span");
		span3.className = "mat-button-wrapper";
		span3.innerText = "Cadastrar Advogado";
		bt3.appendChild(span3);
		el.appendChild(bt3);
		
		//DESCRIÇÃO: BOTÃO AUTUAR PARTE COMO AUTOR
		let bt7 = document.createElement("button");
		bt7.id = "botao_retificar_autuacao_7";
		bt7.name = "botao_retificar_autuacao_addAutor";
		bt7.className = "mat-raised-button mat-primary ng-star-inserted";
		bt7.style = "margin: 3px; z-index: 5; background-color: #1eb159;";
		bt7.onclick = function () {
			let resp = prompt('Digite o CPF/CNPJ do(a) autor(a). Se não tiver, digite o nome:','');
			if (resp) {
				let var1 = browser.storage.local.set({'tempBt': ['acao_bt_retificarAutuacao', [7, resp]]}); //7 - parte autor
				Promise.all([var1]).then(values => {
					acaoBotaoDetalhes("Retificar autuação");
				});
			}
		};
		let span7 = document.createElement("span");
		span7.className = "mat-button-wrapper";
		span7.innerText = "Cadastrar Polo Ativo";
		bt7.appendChild(span7);
		el.appendChild(bt7);
		
		//DESCRIÇÃO: BOTÃO AUTUAR PARTE COMO RÉU
		let bt8 = document.createElement("button");
		bt8.id = "botao_retificar_autuacao_8";
		bt8.name = "botao_retificar_autuacao_addReu";
		bt8.className = "mat-raised-button mat-primary ng-star-inserted";
		bt8.style = "margin: 3px; z-index: 5; background-color: #f0845a;";
		bt8.onclick = function () {
			let resp = prompt('Digite o CPF/CNPJ do réu. Se não tiver, digite o nome:','');
			if (resp) {
				let var1 = browser.storage.local.set({'tempBt': ['acao_bt_retificarAutuacao', [8, resp]]}); // 8 - parte reu
				Promise.all([var1]).then(values => {
					acaoBotaoDetalhes("Retificar autuação");
				});
			}
		};
		let span8 = document.createElement("span");
		span8.className = "mat-button-wrapper";
		span8.innerText = "Cadastrar Polo Passivo";
		bt8.appendChild(span8);
		el.appendChild(bt8);		
		
		//DESCRIÇÃO: BOTÃO AUTUAR UNIÃO COMO TERCEIRO INTERESSADO
		let bt1 = document.createElement("button");
		bt1.id = "botao_retificar_autuacao_0";
		bt1.name = "botao_retificar_autuacao_addTerceiro_Uniao";
		bt1.className = "mat-raised-button mat-primary ng-star-inserted";
		bt1.style = "margin: 3px; z-index: 5; background-color: purple;";
		bt1.onclick = function () {
			let var1 = browser.storage.local.set({'tempBt': ['acao_bt_retificarAutuacao', [0]]});
			Promise.all([var1]).then(values => {
				acaoBotaoDetalhes("Retificar autuação");
			});
		};
		let span1 = document.createElement("span");
		span1.className = "mat-button-wrapper";
		span1.innerText = "Terceiro Interessado > UNIÃO";
		bt1.appendChild(span1);
		el.appendChild(bt1);
		
		//DESCRIÇÃO: BOTÃO AUTUAR TERCEIRO INTERESSADO MPT - CUSTOS LEGIS
		let bt11 = document.createElement("button");
		bt11.id = "botao_retificar_autuacao_10";
		bt11.name = "botao_retificar_autuacao_addTerceiroMPT";
		bt11.className = "mat-raised-button mat-primary ng-star-inserted";
		bt11.style = "margin: 3px; z-index: 5; background-color: purple;";
		bt11.onclick = function () {
			let var1 = browser.storage.local.set({'tempBt': ['acao_bt_retificarAutuacao', [11]]});
			Promise.all([var1]).then(values => {
				acaoBotaoDetalhes("Retificar autuação");
			});
		};
		let span11 = document.createElement("span");
		span11.className = "mat-button-wrapper";
		span11.innerText = "Terceiro Interessado > MPT";
		bt11.appendChild(span11);
		el.appendChild(bt11);
		
		//DESCRIÇÃO: BOTÃO AUTUAR TERCEIRO INTERESSADO
		let bt10 = document.createElement("button");
		bt10.id = "botao_retificar_autuacao_11";
		bt10.name = "botao_retificar_autuacao_addTerceiroTerceiro";
		bt10.className = "mat-raised-button mat-primary ng-star-inserted";
		bt10.style = "margin: 3px; z-index: 5; background-color: purple;";
		bt10.onclick = function () {
			let resp = prompt('Digite o CPF/CNPJ do Terceiro Interessado. Se não tiver, digite o nome:','');
			if (resp) {
				let var1 = browser.storage.local.set({'tempBt': ['acao_bt_retificarAutuacao', [10, resp]]}); // 10 - parte TERCEIRO INTERESSADO
				Promise.all([var1]).then(values => {
					acaoBotaoDetalhes("Retificar autuação");
				});
			}
		};
		let span10 = document.createElement("span");
		span10.className = "mat-button-wrapper";
		span10.innerText = "Terceiro Interessado > Terceiro Interessado";
		bt10.appendChild(span10);
		el.appendChild(bt10);
		
		//DESCRIÇÃO: BOTÃO ADICIONAR LEILOEIRO
		let bt4 = document.createElement("button");
		bt4.id = "botao_retificar_autuacao_3";
		bt4.name = "botao_retificar_autuacao_addTerceiroLeiloeiro";
		bt4.className = "mat-raised-button mat-primary ng-star-inserted";
		bt4.style = "margin: 3px; z-index: 5; background-color: purple;";
		bt4.onclick = function () {
			let var1 = browser.storage.local.set({'tempBt': ['acao_bt_retificarAutuacao', [4]]});
			Promise.all([var1]).then(values => {
				acaoBotaoDetalhes("Retificar autuação");
			});
		};
		let span4 = document.createElement("span");
		span4.className = "mat-button-wrapper";
		span4.innerText = "Terceiro Interessado > Leiloeiro";
		bt4.appendChild(span4);
		el.appendChild(bt4);
		
		//DESCRIÇÃO: BOTÃO ADICIONAR PERITO
		let bt5 = document.createElement("button");
		bt5.id = "botao_retificar_autuacao_4";
		bt5.name = "botao_retificar_autuacao_addTerceiroPerito";
		bt5.className = "mat-raised-button mat-primary ng-star-inserted";
		bt5.style = "margin: 3px; z-index: 5; background-color: purple;";
		bt5.onclick = function () {
			let var1 = browser.storage.local.set({'tempBt': ['acao_bt_retificarAutuacao', [5]]});
			Promise.all([var1]).then(values => {
				acaoBotaoDetalhes("Retificar autuação");
			});
		};
		let span5 = document.createElement("span");
		span5.className = "mat-button-wrapper";
		span5.innerText = "Terceiro Interessado > Perito";
		bt5.appendChild(span5);
		el.appendChild(bt5);
				
		//DESCRIÇÃO: BOTÃO RETIFICAR PROCESSO PRA JUÍZO 100% DIGITAL
		let bt2 = document.createElement("button");
		bt2.id = "botao_retificar_autuacao_2";
		bt2.name = "botao_retificar_autuacao_100Digital";
		bt2.className = "mat-raised-button mat-primary ng-star-inserted";
		bt2.style = "margin: 3px; z-index: 5;";
		bt2.onclick = function () {
			let var1 = browser.storage.local.set({'tempBt': ['acao_bt_retificarAutuacao', [1]]});
			Promise.all([var1]).then(values => {
				acaoBotaoDetalhes("Retificar autuação");
			});
		};
		let span2 = document.createElement("span");
		span2.className = "mat-button-wrapper";
		span2.innerText = "Juízo 100% Digital";
		bt2.appendChild(span2);
		el.appendChild(bt2);
		
		//DESCRIÇÃO: BOTÃO RETIFICAR PROCESSO PRA RECUPERAÇÃO JUDICIAL OU FALÊNCIA
		let bt6 = document.createElement("button");
		bt6.id = "botao_retificar_autuacao_6";
		bt6.name = "botao_retificar_autuacao_Falencia";
		bt6.className = "mat-raised-button mat-primary ng-star-inserted";
		bt6.style = "margin: 3px; z-index: 5;";
		bt6.onclick = function () {
			let var1 = browser.storage.local.set({'tempBt': ['acao_bt_retificarAutuacao', [6]]});
			Promise.all([var1]).then(values => {
				acaoBotaoDetalhes("Retificar autuação");
			});
		};
		let span6 = document.createElement("span");
		span6.className = "mat-button-wrapper";
		span6.innerText = "Falência/Rec.Judicial";
		bt6.appendChild(span6);
		el.appendChild(bt6);
		
		//DESCRIÇÃO: BOTÃO RETIFICAR PROCESSO PRA INCLUIR ASSUNTO
		let bt9 = document.createElement("button");
		bt9.id = "botao_retificar_autuacao_9";
		bt9.name = "botao_retificar_autuacao_assunto";
		bt9.className = "mat-raised-button mat-primary ng-star-inserted";
		bt9.style = "margin: 3px; z-index: 5;";
		bt9.onclick = function () {
			//oriundo da Ação em Lote. Uso essa variável para passar o código do assunto
			browser.storage.local.get('tempAR', function(result){
				preferencias.tempAR = result.tempAR;
			});
			
			let texto = preferencias.tempAR || prompt('Código Assunto:','');
			let var1 = browser.storage.local.set({'tempBt': ['acao_bt_retificarAutuacao', [9,texto]]});
			Promise.all([var1]).then(values => {
				acaoBotaoDetalhes("Retificar autuação");
			});
		};
		let span9 = document.createElement("span");
		span9.className = "mat-button-wrapper";
		span9.innerText = "Assunto";
		bt9.appendChild(span9);
		el.appendChild(bt9);
		
		//DESCRIÇÃO: BOTÃO RETIFICAR PROCESSO PRA TUTELA LIMINAR
		let bt12 = document.createElement("button");
		bt12.id = "botao_retificar_autuacao_12";
		bt12.name = "botao_retificar_autuacao_tutelaLiminar";
		bt12.className = "mat-raised-button mat-primary ng-star-inserted";
		bt12.style = "margin: 3px; z-index: 5;";
		bt12.onclick = function () {
			let var1 = browser.storage.local.set({'tempBt': ['acao_bt_retificarAutuacao', [12]]});
			Promise.all([var1]).then(values => {
				acaoBotaoDetalhes("Retificar autuação");
			});
		};
		let span12 = document.createElement("span");
		span12.className = "mat-button-wrapper";
		span12.innerText = "Pedido de Tutela";
		bt12.appendChild(span12);
		el.appendChild(bt12);
		
		//DESCRIÇÃO: BOTÃO RETIFICAR JUSTIÇA GRATUITA
		let bt13 = document.createElement("button");
		bt13.id = "botao_retificar_autuacao_13";
		bt13.name = "botao_retificar_autuacao_justicaGratuita";
		bt13.className = "mat-raised-button mat-primary ng-star-inserted";
		bt13.style = "margin: 3px; z-index: 5;";
		bt13.onclick = function () {
			let var1 = browser.storage.local.set({'tempBt': ['acao_bt_retificarAutuacao', [13]]});
			Promise.all([var1]).then(values => {
				acaoBotaoDetalhes("Retificar autuação");
			});
		};
		let span13 = document.createElement("span");
		span13.className = "mat-button-wrapper";
		span13.innerText = "Justiça Gratuita";
		bt13.appendChild(span13);
		el.appendChild(bt13);
		
	}
	
	function corrigirPosicaoElementos() {
		let altura = document.querySelector('button[aria-label="Filtrar"]').getBoundingClientRect().bottom + 29;
		//move o botão "Esconder Linha do Tempo" para cima
		if (document.querySelector('button[aria-label="Esconder Linha do Tempo"]')) {
			document.querySelector('button[aria-label="Esconder Linha do Tempo"]').style = "top: " + altura + "px;";
		}
		//move o botão "Esconder o GIGS" para cima
		if (document.querySelector('button[aria-label="Esconder o GIGS"]')) {
			document.querySelector('button[aria-label="Esconder o GIGS"]').style = "top: " + altura + "px;";
		}
		//move o botão "Mostrar o GIGS" para cima
		if (document.querySelector('button[aria-label="Mostrar o GIGS"]')) {
			document.querySelector('button[aria-label="Mostrar o GIGS"]').style = "top: " + altura + "px;";
		}
	}
}

//FUNÇÃO RESPONSÁVEL POR ADICIONAR OS BOTÕES NA PÁGINA DETALHES - RETIFICAR AUTUAÇÃO
async function addBotaoLancarMovimentos() {
	return new Promise(async resolve => {
		await criarContainer('addBotaoLancarMovimentos',true);
		await montarBotoes();
		await sleep(500);
		resolve(true);
	});
	
	async function montarBotoes() {
		return new Promise(async resolve => {
			await criaBotao();
			await corrigirPosicaoElementos();
			resolve(true);
		});
	}
	
	async function criaBotao() {	
		return new Promise(async resolve => {
			let ancora = document.querySelector('maisPjeContainerAA');
			
			let contadoriaAtualizacao = await criar_botao(
				"botao_lancar_movimento_0",
				"Contadoria:atualização",
				"orangered",
				async function () {
					fundo(true);
					acaoBotaoDetalhes("Lançar movimentos");
					await sleep(500);
					let opcao = await esperarElemento('pje-lancador-de-movimentos pje-movimento', '123');
					await clicarBotao(opcao.querySelector('label'));
					await sleep(1000);
					await escolherOpcao(opcao.querySelectorAll('mat-select')[0],'7044');
					await escolherOpcao(opcao.querySelectorAll('mat-select')[1],'7574');
					await clicarBotao('pje-lancador-movimentos-dialogo button[aria-label="Gravar os movimentos a serem lançados"]');
					
					let caixaDePergunta = await esperarElemento('mat-dialog-container div[class="div-container"]', 'Deseja realmente incluir estes movimentos?');
					await clicarBotao(caixaDePergunta.querySelectorAll('button')[0]);
					fundo(false);
					monitorFim();
				}
			);
			ancora.appendChild(contadoriaAtualizacao);
			
			let contadoriaLiquidacao = await criar_botao(
				"botao_lancar_movimento_1",
				"Contadoria:liquidação",
				"orangered",
				async function () {
					fundo(true);
					acaoBotaoDetalhes("Lançar movimentos");
					await sleep(500);
					let opcao = await esperarElemento('pje-lancador-de-movimentos pje-movimento', '123');
					await clicarBotao(opcao.querySelector('label'));
					await sleep(1000);
					await escolherOpcao(opcao.querySelectorAll('mat-select')[0],'7044');
					await escolherOpcao(opcao.querySelectorAll('mat-select')[1],'7087');
					await clicarBotao('pje-lancador-movimentos-dialogo button[aria-label="Gravar os movimentos a serem lançados"]');
					
					let caixaDePergunta = await esperarElemento('mat-dialog-container div[class="div-container"]', 'Deseja realmente incluir estes movimentos?');
					await clicarBotao(caixaDePergunta.querySelectorAll('button')[0]);
					fundo(false);
					monitorFim();
				}
			);
			ancora.appendChild(contadoriaLiquidacao);
			
			let contadoriaRetificacao = await criar_botao(
				"botao_lancar_movimento_2",
				"Contadoria:retificação",
				"orangered",
				async function () {
					fundo(true);
					acaoBotaoDetalhes("Lançar movimentos");
					await sleep(500);
					let opcao = await esperarElemento('pje-lancador-de-movimentos pje-movimento', '123');
					await clicarBotao(opcao.querySelector('label'));
					await sleep(800);
					await escolherOpcao(opcao.querySelectorAll('mat-select')[0],'7044');
					await escolherOpcao(opcao.querySelectorAll('mat-select')[1],'7575');
					await clicarBotao('pje-lancador-movimentos-dialogo button[aria-label="Gravar os movimentos a serem lançados"]');
					
					let caixaDePergunta = await esperarElemento('mat-dialog-container div[class="div-container"]', 'Deseja realmente incluir estes movimentos?');
					await clicarBotao(caixaDePergunta.querySelectorAll('button')[0]);
					fundo(false);
					monitorFim();
				}
			);
			ancora.appendChild(contadoriaRetificacao);
			
			let contadoriaDeterminacaoJudicial = await criar_botao(
				"botao_lancar_movimento_3",
				"Contadoria:DeterminaçãoJudicial",
				"orangered",
				async function () {
					fundo(true);
					acaoBotaoDetalhes("Lançar movimentos");
					await sleep(500);
					let opcao = await esperarElemento('pje-lancador-de-movimentos pje-movimento', '123');
					await clicarBotao(opcao.querySelector('label'));
					await sleep(800);
					await escolherOpcao(opcao.querySelectorAll('mat-select')[0],'7044');
					await escolherOpcao(opcao.querySelectorAll('mat-select')[1],'7084');
					await clicarBotao('pje-lancador-movimentos-dialogo button[aria-label="Gravar os movimentos a serem lançados"]');
					
					let caixaDePergunta = await esperarElemento('mat-dialog-container div[class="div-container"]', 'Deseja realmente incluir estes movimentos?');
					await clicarBotao(caixaDePergunta.querySelectorAll('button')[0]);
					fundo(false);
					monitorFim();
				}
			);
			ancora.appendChild(contadoriaDeterminacaoJudicial);
			
			let trtRecurso = await criar_botao(
				"botao_lancar_movimento_4",
				"TRT:recurso",
				"#bd522a",
				async function () {
					fundo(true);
					acaoBotaoDetalhes("Lançar movimentos");
					await sleep(500);
					let opcao = await esperarElemento('pje-lancador-de-movimentos pje-movimento', '123');
					await clicarBotao(opcao.querySelector('label'));
					await sleep(1000);
					await escolherOpcao(opcao.querySelectorAll('mat-select')[0],'7499');
					await escolherOpcao(opcao.querySelectorAll('mat-select')[1],'38');			
					await clicarBotao('pje-lancador-movimentos-dialogo button[aria-label="Gravar os movimentos a serem lançados"]');
					
					let caixaDePergunta = await esperarElemento('mat-dialog-container div[class="div-container"]', 'Deseja realmente incluir estes movimentos?');
					await clicarBotao(caixaDePergunta.querySelectorAll('button')[0]);
					fundo(false);
					monitorFim();
				}
			);
			ancora.appendChild(trtRecurso);
			
			let recebidoOsAutos = await criar_botao(
				"botao_lancar_movimento_6",
				"Recebido: para Prosseguir",
				"orange",
				async function () {
					fundo(true);
					acaoBotaoDetalhes("Lançar movimentos");
					await sleep(500);
					let opcao = await esperarElemento('pje-lancador-de-movimentos pje-movimento', '132');
					await clicarBotao(opcao.querySelector('label'));
					await sleep(1000);
					await escolherOpcao(opcao.querySelectorAll('mat-select')[0],'40');
					await clicarBotao('pje-lancador-movimentos-dialogo button[aria-label="Gravar os movimentos a serem lançados"]');
					
					let caixaDePergunta = await esperarElemento('mat-dialog-container div[class="div-container"]', 'Deseja realmente incluir estes movimentos?');
					await clicarBotao(caixaDePergunta.querySelectorAll('button')[0]);
					fundo(false);
					monitorFim();
				}
			);
			ancora.appendChild(recebidoOsAutos);
			
			if (preferencias.grau_usuario == 'segundograu' || preferencias.grau_usuario == '' || preferencias.grau_usuario == 'não identificado') {
				
				let publicacaoDePauta = await criar_botao(
					"botao_lancar_movimento_5",
					"Publicação de Pauta",
					"orangered",
					async function () {
						fundo(true);
						acaoBotaoDetalhes("Lançar movimentos");
						await sleep(500);
						let opcao = await esperarElemento('pje-lancador-de-movimentos pje-movimento', '(92)');
						await clicarBotao(opcao.querySelector('label'));
						await sleep(1000);
						await escolherOpcao(opcao.querySelectorAll('mat-select')[0],'7006');
						
						let dataDaPublicacao = (!preferencias.tempAR) ? prompt('Data da Publicação: ','') : preferencias.tempAR;
						let dt = new Date(dataDaPublicacao);
						let dtFormatada = dt.getFullYear() + '-' + ("0" + dt.getDate()).slice(-2) + '-' + ("0" + (dt.getMonth()+1)).slice(-2);
										
						await preencherInput('input[data-placeholder="Data da publicação"]',dtFormatada);
						await clicarBotao('pje-lancador-movimentos-dialogo button[aria-label="Gravar os movimentos a serem lançados"]');
					
						let caixaDePergunta = await esperarElemento('mat-dialog-container div[class="div-container"]', 'Deseja realmente incluir estes movimentos?');
						await clicarBotao(caixaDePergunta.querySelectorAll('button')[0]);
						fundo(false);
						monitorFim();
					}
				);			
				ancora.appendChild(publicacaoDePauta);
				
			}
		
			resolve(true);
		});
	}
	
	async function criar_botao(id, aria, cor_de_fundo, funcao) {
		return new Promise(resolve => {
			let bt = document.createElement("button");
			bt.id = id;
			bt.name = aria;
			bt.className = 'mat-raised-button mat-primary ng-star-inserted';
			bt.style = 'margin: 3px; z-index: 5; background-color:' + cor_de_fundo + ';';
			bt.onclick = funcao;		
			let span = document.createElement("span");
			span.className = 'mat-button-wrapper';
			span.innerText = aria;
			bt.appendChild(span);
			resolve(bt);
		});
	}
	
	async function monitorFim() {		
		let param = (!preferencias.tempAAEspecial) ? 'Nenhum' : preferencias.tempAAEspecial;
		console.log('monitorFim(' + param + ')');
		
		if (param && param != "nenhum") { //se tem vínculo continua
			
			browser.runtime.sendMessage({tipo: 'storage_vinculo', valor: param});

		} else {

			if (preferencias.AALote.length > 0) { //vem do AA em Lote
				let guardarStorage = browser.storage.local.set({'AALote': ''});
				Promise.all([guardarStorage]).then(values => { window.close() });
			}
		}		
		
	}
	
}

//FUNÇÃO RESPONSÁVEL POR INFORMAR A EXISTÊNCIA DE CONTAS COM SALDO NO SIF
async function addInformacoesSIF() {
	return new Promise(async resolve => {
		await criarContainer('addInformacoesSIF',true); //com botão de fechar
		await montarBotoesContasBB();
		await montarBotoesNovoBoletoSIF();
		await montarBotoesNovoBoletoSISCONDJ();
		
		let spanAlerta = document.createElement('maisPjeContainerAA_Alerta');
		spanAlerta.innerText = "Consultando contas no SIF...";
		document.querySelector('maisPjeContainerAA').appendChild(spanAlerta);
		
		await montarBotoesContasCEF();
		await sleep(500);
		resolve(true);
	});
		
	async function montarBotoesContasCEF() {
		return new Promise(async resolve => {
		
			corrigirPosicaoElementos();
			//consulta api
			let processo = document.querySelector('span[class="texto-numero-processo"]').innerText.match(new RegExp('\\d{7}-\\d{2}\\.\\d{4}\\.\\d{1,2}\\.\\d{1,2}\\.\\d{4}','g')).join();
			processo = processo.replace(/(\.|\-)/gm, "");
			let dados = await obterContasSIF(processo);
			if (!document.querySelector('maisPjeContainerAA')) { return }
			
			let respostaConsultaSif = 'MaisPJe: Consulta efetuada com sucesso!';
			
			if (dados == '') {
				if (dados) {
					respostaConsultaSif = dados.mensagem;
					document.querySelector('maisPjeContainerAA_Alerta').innerText = respostaConsultaSif;
					return;
				} else {
					document.querySelector('maisPjeContainerAA_Alerta').innerText = 'Não foi possível conectar ao SIF..';
					return;
				}
			} else {
				if (!dados[0]) { respostaConsultaSif = 'MaisPJe: API do SIF não encontrada! #erro' }
				respostaConsultaSif = dados[0].mensagemRetorno;
				if (!dados[0].codigoRetorno) { respostaConsultaSif = 'MaisPJe: Não foi possível consultar as contas judiciais nesta Instituição Financeira. #erro' }
				if (dados[0].codigoRetorno == 'null') { respostaConsultaSif = 'MaisPJe: Não foi possível consultar as contas judiciais nesta Instituição Financeira. #erro' }
				if (dados[0].codigoRetorno == '1') { respostaConsultaSif = 'MaisPJe: Não existe conta SIF para este processo! #erro' }
				if (dados[0].codigoRetorno == '99') { respostaConsultaSif = 'MaisPJe: Não existe conta SIF para este processo! #erro' }
				
				//Não é permitido acesso ao SIF através de Login e Senha. Utilize o Certificado Digital para fazer login!
				document.querySelector('maisPjeContainerAA_Alerta').innerText = respostaConsultaSif;
				if (respostaConsultaSif.includes('#erro')) { return }
				if (dados[0].contas.length > 0) {
					document.querySelector('maisPjeContainerAA_Alerta').innerText = '';
					for (const [pos, conta] of dados[0].contas.entries()) {
						let cor = conta.saldo.total == 0 ? "darkseagreen" : "darkgreen";
						criaBotao(processo, conta.contaJudicial.unidade, conta.contaJudicial.produto, conta.contaJudicial.conta, conta.contaJudicial.dv, conta.saldo.total, cor);
					}
				}
			}
			
			resolve(true);
		});
	}
	
	async function montarBotoesContasBB() {
		return new Promise(async resolve => {
			let el = document.querySelector('maisPjeContainerAA');
			let bt = document.createElement("button");
			bt.id = "botao_checklist_BB";
			bt.name = "botao_checklist_BB";
			bt.className = "mat-raised-button mat-primary ng-star-inserted";
			bt.style = "margin: 3px 8px 3px 8px; z-index: 3; background-color: #feeb37; color: #8b7300;";
			bt.title = 'Consultar Contas no Siscondj';
			bt.onclick = async function () {
				let processo = document.querySelector('span[class="texto-numero-processo"]').innerText.match(new RegExp('\\d{7}-\\d{2}\\.\\d{4}\\.\\d{1,2}\\.\\d{1,2}\\.\\d{4}','g')).join();
				let var1 = browser.storage.local.get('processo_memoria', async function(result){
					if (!result.processo_memoria.numero) { return }
					if (!result.processo_memoria.numero.includes(processo)) { return }
					getAtalhosNovaAba().abrirSiscondj.abrirAtalhoemNovaJanela();					
				});
			};
			let span = document.createElement("span");
			span.className = "mat-button-wrapper";
			span.innerText = 'SISCONDJ';
			bt.appendChild(span);
			el.appendChild(bt);
			resolve(true);
		});
	}
	
	async function montarBotoesNovoBoletoSIF() {
		return new Promise(async resolve => {
			let el = document.querySelector('maisPjeContainerAA');
			let bt = document.createElement("button");
			bt.id = "botao_checklist_Novo_SIF";
			bt.name = "botao_checklist_Novo_SIF";
			bt.className = "mat-raised-button mat-primary ng-star-inserted";
			bt.style = "margin: 3px 8px 3px 8px; z-index: 3; background-color: #009cdd; color: #8b7300;";
			bt.title = 'Novo Boleto no CEF';
			bt.onclick = async function () {
				let processo = document.querySelector('span[class="texto-numero-processo"]').innerText.match(new RegExp('\\d{7}-\\d{2}\\.\\d{4}\\.\\d{1,2}\\.\\d{1,2}\\.\\d{4}','g')).join();
				await gigsCriarMenu();
				let var1 = browser.storage.local.get('processo_memoria', async function(result){
					if (!result.processo_memoria.numero) { return }
					if (!result.processo_memoria.numero.includes(processo)) { return }				
					getAtalhosNovaAba().abrirSIFNovoBoleto.abrirAtalhoemNovaJanela();
				});
			};
			let span = document.createElement("span");
			span.className = "mat-button-wrapper";
			span.innerText = 'SIF - Novo Boleto';
			bt.appendChild(span);
			el.appendChild(bt);
			resolve(true);
		});
	}
	
	async function montarBotoesNovoBoletoSISCONDJ() {
		return new Promise(async resolve => {
			let el = document.querySelector('maisPjeContainerAA');
			let bt = document.createElement("button");
			bt.id = "botao_checklist_Novo_BB";
			bt.name = "botao_checklist_Novo_BB";
			bt.className = "mat-raised-button mat-primary ng-star-inserted";
			bt.style = "margin: 3px 8px 3px 8px; z-index: 3; background-color: #009cdd; color: #8b7300;";
			bt.title = 'Novo Boleto no BB';
			bt.onclick = async function () {
				let processo = document.querySelector('span[class="texto-numero-processo"]').innerText.match(new RegExp('\\d{7}-\\d{2}\\.\\d{4}\\.\\d{1,2}\\.\\d{1,2}\\.\\d{4}','g')).join();
				await gigsCriarMenu();
				let var1 = browser.storage.local.get('processo_memoria', async function(result){
					if (!result.processo_memoria.numero) { return }
					if (!result.processo_memoria.numero.includes(processo)) { return }				
					getAtalhosNovaAba().abrirSISCONDJNovoBoleto.abrirAtalhoemNovaJanela();
				});
			};
			let span = document.createElement("span");
			span.className = "mat-button-wrapper";
			span.innerText = 'SISCONDJ - Novo Boleto';
			bt.appendChild(span);
			el.appendChild(bt);
			el.appendChild(document.createElement("br"));
			resolve(true);
		});
	}
	
	function criaBotao(processo, agencia, operacao, conta, dv, saldo, cor) {
		let el = document.querySelector('maisPjeContainerAA');
		let bt = document.createElement("button");
		
		agencia = ("0000" + agencia).slice(-4); //ajusta o numero da agencia
		operacao = ("000" + operacao).slice(-3); //ajusta o numero da operacao
		conta = ("00000000" + conta).slice(-8); //ajusta o numero da conta
		let idconta = agencia + "" + operacao + "" + conta + "" + dv;
		let idconta_formatada = agencia + "." + operacao + "." + conta + "-" + dv;
		
		bt.id = "botao_checklist_" + idconta;
		bt.name = "botao_checklist_" + idconta;
		bt.className = "mat-raised-button mat-primary ng-star-inserted";
		bt.style = "margin: 3px; z-index: 3; background-color: " + cor + ";";
		bt.title = 'Consultar Extrato';
		bt.onclick = function () {
			let idProcesso = document.location.href.substring(document.location.href.search("/processo/")+10, document.location.href.search("/detalhe"));
			getAtalhosNovaAba().consultarExtrato.abrirAtalhoemNovaJanela(idProcesso, idconta, processo);
		};
		let span = document.createElement("span");
		span.className = "mat-button-wrapper";
		let valor_formatado_para_uso = Intl.NumberFormat('pt-br', {style: 'currency', currency: 'BRL'}).format(saldo);
		span.innerText = idconta_formatada + ": " + valor_formatado_para_uso;
		bt.appendChild(span);
		el.appendChild(bt);
	}
	
	function corrigirPosicaoElementos() {
		let altura = document.querySelector('button[aria-label="Filtrar"]').getBoundingClientRect().bottom + 29;
		//move o botão "Esconder Linha do Tempo" para cima
		if (document.querySelector('button[aria-label="Esconder Linha do Tempo"]')) {
			document.querySelector('button[aria-label="Esconder Linha do Tempo"]').style = "top: " + altura + "px;";
		}
		//move o botão "Esconder o GIGS" para cima
		if (document.querySelector('button[aria-label="Esconder o GIGS"]')) {
			document.querySelector('button[aria-label="Esconder o GIGS"]').style = "top: " + altura + "px;";
		}
		//move o botão "Mostrar o GIGS" para cima
		if (document.querySelector('button[aria-label="Mostrar o GIGS"]')) {
			document.querySelector('button[aria-label="Mostrar o GIGS"]').style = "top: " + altura + "px;";
		}
	}
}

//FUNÇÃO RESPONSÁVEL POR ADICIONAR OS BOTÕES NA PÁGINA DETALHES - BAIXAR PROCESSO PJE ANTIGO
async function addBotaoBaixarProcessoLegado() {
	return new Promise(async resolve => {
		
		if (preferencias.trt.includes('trt1.')) { return resolve(true) } //desativar a funcionalidade para o TRT1 (ISSUE Nacional)
			await criarContainer('addBotaoBaixarProcessoLegado',true);
			await montarBotoes();
			resolve(true);
		});
		
		async function montarBotoes() {
			return new Promise(async resolve => {
				await criaBotao();
				await corrigirPosicaoElementos();
				resolve(true);
			});
		}
		
		function criaBotao() {
			return new Promise(resolve => {
				let el = document.querySelector('maisPjeContainerAA');
				let bt = document.createElement("button");
				bt.id = "botao_baixarProcessoLegado_0";
				bt.name = "botao_baixarProcessoLegado_addBt";
				bt.className = "mat-raised-button mat-primary ng-star-inserted";
				bt.style = "margin: 3px; z-index: 5;";
				bt.onclick = function () {
					let idProcesso = document.location.href.substring(document.location.href.search("/processo/")+10, document.location.href.search("/detalhe"));
					let prefixo = document.location.href.substring(0, document.location.href.search("/pjekz/"));
					let parametros = 'dependent=yes,';
					parametros += 'width=520px,';
					parametros += 'height=520px';
					let gigsURL = prefixo + '/' + preferencias.grau_usuario + '/Processo/ConsultaProcesso/Detalhe/list.seam?id=' + idProcesso + '&baixar=true';
					let winGigs = window.open(gigsURL, '_blank', parametros);
				};
				let span = document.createElement("span");
				span.className = "mat-button-wrapper";
				span.innerText = "Baixar Processo no PJe Antigo";
				bt.appendChild(span);
				el.appendChild(bt);
				resolve(true);
			});
		}	
		
		function corrigirPosicaoElementos() {
			return new Promise(resolve => {
				let altura = document.querySelector('button[aria-label="Filtrar"]').getBoundingClientRect().bottom + 29;
				//move o botão "Esconder Linha do Tempo" para cima
				if (document.querySelector('button[aria-label="Esconder Linha do Tempo"]')) {
					document.querySelector('button[aria-label="Esconder Linha do Tempo"]').style = "top: " + altura + "px;";
				}
				//move o botão "Esconder o GIGS" para cima
				if (document.querySelector('button[aria-label="Esconder o GIGS"]')) {
					document.querySelector('button[aria-label="Esconder o GIGS"]').style = "top: " + altura + "px;";
				}
				//move o botão "Mostrar o GIGS" para cima
				if (document.querySelector('button[aria-label="Mostrar o GIGS"]')) {
					document.querySelector('button[aria-label="Mostrar o GIGS"]').style = "top: " + altura + "px;";
				}
				resolve(true);
			});
		}
}

//FUNÇÃO RESPONSÁVEL POR ADICIONAR OS BOTÕES NA PÁGINA DETALHES - CÁLCULOS DO PROCESSO
async function addBotaoAtualizacaoRapida() {
	return new Promise(async resolve => {
		await criarContainer('addBotaoAtualizacaoRapida',true);
		await montarBotoes();
		resolve(true);
		
		async function montarBotoes() {
			return new Promise(async resolve => {
				await criaBotao();
				await corrigirPosicaoElementos();
				resolve(true);
			});
		}
		
		function criaBotao() {
			return new Promise(resolve => {
				let el = document.querySelector('maisPjeContainerAA');
				let bt0 = document.createElement("button");
				bt0.id = "botao_abrirPjeCalc";
				bt0.name = "botao_abrirPjeCalc";
				bt0.className = "mat-raised-button mat-primary ng-star-inserted";
				bt0.style = "margin: 3px; z-index: 5;";
				bt0.onclick = function () {
					getAtalhosNovaAba().abrirPJeCalc.abrirAtalhoemNovaJanela('');
				};
				let span0 = document.createElement("span");
				span0.className = "mat-button-wrapper";
				span0.innerText = "Abrir PJeCalc";
				bt0.appendChild(span0);
				el.appendChild(bt0);
				
				let bt = document.createElement("button");
				bt.id = "botao_atualizacaoRapida";
				bt.name = "botao_atualizacaoRapida";
				bt.className = "mat-raised-button mat-primary ng-star-inserted";
				bt.style = "margin: 3px; z-index: 5;";
				bt.onclick = async function () {
					console.log(preferencias.processo_memoria.numero)
					if (!preferencias.processo_memoria.numero) {
						await gigsCriarMenu();
					}
					getAtalhosNovaAba().abrirPJeCalc.abrirAtalhoemNovaJanela('?maisPje=atualizacaorapida')
				};
				let span = document.createElement("span");
				span.className = "mat-button-wrapper";
				span.innerText = "Atualização Rápida";
				bt.appendChild(span);
				el.appendChild(bt);
				resolve(true);
			});
		}	
		
		function corrigirPosicaoElementos() {
			return new Promise(resolve => {
				let altura = document.querySelector('button[aria-label="Filtrar"]').getBoundingClientRect().bottom + 29;
				//move o botão "Esconder Linha do Tempo" para cima
				if (document.querySelector('button[aria-label="Esconder Linha do Tempo"]')) {
					document.querySelector('button[aria-label="Esconder Linha do Tempo"]').style = "top: " + altura + "px;";
				}
				//move o botão "Esconder o GIGS" para cima
				if (document.querySelector('button[aria-label="Esconder o GIGS"]')) {
					document.querySelector('button[aria-label="Esconder o GIGS"]').style = "top: " + altura + "px;";
				}
				//move o botão "Mostrar o GIGS" para cima
				if (document.querySelector('button[aria-label="Mostrar o GIGS"]')) {
					document.querySelector('button[aria-label="Mostrar o GIGS"]').style = "top: " + altura + "px;";
				}
				resolve(true);
			});
		}
	});
}

//FUNÇÃO RESPONSÁVEL POR ADICIONAR OS CHECKBOX NA OPÇÃO DE ESCOLHER PERFIL
function addCheckPerfil() {
	let check = setInterval(function() {
		if(document.querySelector('div[class*="menu-selecao-perfil-usuario"]')) {
			clearInterval(check);
			//DESCRIÇÃO: CARREGA O PERFIL ESCOLHIDO
			browser.storage.local.get('perfilUsuario', function(result){
				preferencias.perfilUsuario = result.perfilUsuario;
			});
			if (!document.getElementById("extensaoPje_ck_menu_0")) {
				let opcoes = document.querySelectorAll('button[class*="menu-entrada-perfil"]');
				for (const [pos, opcao] of opcoes.entries()) {
					let ck = document.createElement("input");
					ck.type = "checkbox";
					ck.id = "extensaoPje_ck_menu_" + pos;
					if (preferencias.perfilUsuario == "nenhum" || preferencias.perfilUsuario == "" || preferencias.perfilUsuario == null) {
						ck.checked = false;
					} else {
						ck.checked = (opcao.getAttribute('aria-label') == preferencias.perfilUsuario) ? true : false;
					}
					ck.onclick = function (event) {
						let temp;
						if (event.target.checked) {
							document.querySelectorAll('input[id*="extensaoPje_ck_menu_"]').forEach( cada => cada.checked = false);
							event.target.checked = true;
							temp = event.target.parentElement.getAttribute('aria-label');
						} else {
							temp = "nenhum";
						}
						
						browser.storage.local.set({'perfilUsuario': temp});
						browser.runtime.sendMessage({tipo: 'criarAlerta', valor: '\n Papel preferido guardado com sucesso!', icone: '3'});
					};
					opcao.appendChild(ck);
				}
			}
		}
	}, 100);
}

//FUNÇÃO RESPONSÁVEL POR ADICIONAR O BOTÃO FECHAR ALERTAS EM LOTE
async function addBotaoFecharAlertasEmLote() {
	
	if (preferencias.AALote.length > 0) { return } //desativa quando vem das ações em lote
	
	let ancora = await esperarElemento('mat-card-title','Alertas do processo');
	if (!ancora) { return }
	let botao1 = document.createElement("button");
	botao1.id = "maisPje_bt_fechar_alertas_lote";
	botao1.textContent = "Fechar todos";
	botao1.style = "cursor: pointer; position: relative; top: 20%; width: 100%; padding: 5px; margin: 5px; height: 35px; z-index: 1;";
	botao1.onclick = function () {fecharTodos()};
	ancora.parentElement.appendChild(botao1);
	function fecharTodos() {
		let el = document.querySelectorAll('pje-alerta-processo-dialogo mat-checkbox');
		if (!el) {
			return
		}
		let map = [].map.call(
			el, 
			function(elemento) {
				elemento.click()
			}
		);
	}
}

//FUNÇÃO RESPONSÁVEL POR CRIAR O FUNDO ESCURO QUANDO A EXTENSÃO ESTÁ OPERANDO
async function fundo(ligar, mensagem, altura) {
	return new Promise(async resolve => {
		if (ligar) {
			if (!document.getElementById('extensaoPje_fundo')) {
				//DESCRIÇÃO: REGRA DO TOOLTIP
				if (!document.getElementById('maisPje_tooltip_fundo')) {
					tooltip('fundo', true);
				}
				
				mensagem = !mensagem ? "" : mensagem + "\n";
				altura = !altura ? '100%' : altura + 'px';
				
				let elemento1 = document.createElement("div");
				elemento1.id = 'extensaoPje_fundo';
				elemento1.style = 'position: fixed; width: 100%; height: ' + altura + '; top: 0; inset: 0px; background: #000000a1 none repeat scroll 0% 0%; z-index: 10000; display: flex; align-items: center; justify-content: center; color: rgb(81, 81, 81); font-size: 80px; font-weight: bold; text-align: center;  text-shadow: rgb(0, 0, 0) 1px 1px;flex-direction: column;';
				
				let span = document.createElement("span");
				span.className = 'pjextension_executando';
				let img = document.createElement("img");
				img.src = browser.runtime.getURL("icons/ico_32.png");
				span.appendChild(img);
				elemento1.appendChild(span);
				
				let msg = document.createElement("span");
				msg.id = 'maisPJe_mensagem_fundo';
				msg.style = 'position: absolute; font-size: .2em;align-self: center;margin-top: 15vh; color: white;';
				msg.innerText = mensagem + '"ESC" para fechar a tela de bloqueio!';
				elemento1.appendChild(msg);
				
				document.body.appendChild(elemento1);
			}
			return resolve(true);
		} else {
			let fundo = await esperarElemento('div[id="extensaoPje_fundo"]');
			if (fundo) { fundo.remove() }			
			return resolve(true);
		}
	});
}

async function menuStatus(ligar) {
	return new Promise(async resolve => {
		let menuStatus = document.getElementById('menuMaisPje_status');
		if (!menuStatus) { return }
		if (ligar) {
			menuStatus.style.display = 'contents';
		} else {
			menuStatus.style.display = 'none';
		}
		return resolve(true);
	});
}

async function exibir_mensagem(msg) {
	return new Promise(async resolve => {
		let expositor = document.getElementById('maisPJe_mensagem_fundo');
		if (!expositor) {
			fundo(true);
			return resolve(exibir_mensagem(msg));
		} else {
			expositor.innerText = "maisPje: " + msg;
			resolve(true);
		}
	});
}

//FUNÇÃO RESPONSÁVEL POR COPIAR O TEXTO DE UM DOCUMENTO DO PROCESSO
async function copiarDocumentoProcesso(id) {
	fundo(true, 'Elaborando a transcrição do documento..');
	
	let conteudo = "";
	let tipoDocumento, idDocumento;
	if (!id) { //sistema de exibição de documentos antigo - atualmente presente no minutar despacho, intimação, anexar documentos, etc..
		// console.log(id);
		let tituloDocumento = document.getElementsByClassName('mat-card-title')[0].innerText;
		tipoDocumento = tituloDocumento.substring(tituloDocumento.search(" - ")+3, tituloDocumento.search(".pdf") > -1 ? tituloDocumento.search(".pdf") : tituloDocumento.length);
		idDocumento = tituloDocumento.substring(tituloDocumento.search("Id ")+3, tituloDocumento.search(" - "));
			
		conteudo += 'Transcrição do(a) ' + tipoDocumento + ' (ID ' + idDocumento + '): \n"';
			
		if (document.getElementsByClassName('container-html')[0]) {
			// console.log("documento padrão antigo");
			conteudo += document.getElementsByClassName('container-html')[0].firstChild.firstChild.innerText.replace(/(\r\n|\n|\r)/gm, "") + '"'
		} else {
			// console.log("documento padrão novo");
			await clicarBotao('pje-documento-visualizador button[mattooltip="Visualizar HTML original"]');
			let resposta = await esperarTransicao();
			
			if (resposta) {
				let ancora = await esperarElemento('mat-dialog-container pje-documento-original');				
				let ancoraTexto = ancora.querySelector('div[id="previewModeloDocumento"] div');
				conteudo += ancoraTexto.textContent;
				await clicarBotao('pje-documento-original button[aria-label="Fechar"]');
				criarCaixaDeAlerta("ALERTA","Trancrição concluída com sucesso!\n\nUse o CTRL+V para colar o texto.", 3);
			} else {
				criarCaixaDeAlerta("ALERTA","Não foi possível concluir a trancrição.\n\nEste documento não possui um HTML original que permita a cópia dos dados.", 5);
			}
			
			let overlay = await esperarElemento('div[class="cdk-overlay-container"][style*="hidden"]',null,100);
			if (overlay) { overlay.style.visibility = 'revert' }
		}
		
		conteudo += '"';
	} else { // sistema de exibição de documentos novo, atualmente presente na Janela Detalhes do Processo 
		let ancora = document.querySelector('pje-historico-scroll-titulo');
		let tituloDocumento = ancora.getElementsByClassName('mat-card-title')[0].innerText;
		tipoDocumento = tituloDocumento.substring(tituloDocumento.search(" - ")+3, tituloDocumento.search(".pdf") > -1 ? tituloDocumento.search(".pdf") : tituloDocumento.length);
		idDocumento = tituloDocumento.substring(tituloDocumento.search("Id ")+3, tituloDocumento.search(" - "));
		conteudo += 'Transcrição do(a) ' + tipoDocumento + ' (ID ' + idDocumento + '): \n"';
		
		if (document.getElementsByClassName('container-html')[0]) {
			// console.log("documento padrão antigo");
			conteudo += document.getElementsByClassName('container-html')[0].firstChild.firstChild.innerText.replace(/(\r\n|\n|\r)/gm, "") + '"'
		} else {
			
			// console.log("documento padrão novo");
			await clicarBotao('pje-historico-scroll-titulo button[mattooltip="Visualizar HTML original"]');
			let resposta = await esperarTransicao();
			
			if (resposta) {
				let ancora = await esperarElemento('mat-dialog-container pje-documento-original');				
				let ancoraTexto = ancora.querySelector('div[id="previewModeloDocumento"] div');
				conteudo += ancoraTexto.textContent;
				await clicarBotao('pje-documento-original button[aria-label="Fechar"]');
				criarCaixaDeAlerta("ALERTA","Pressione CTRL+V para colar a transcrição.", 3);
			} else {
				criarCaixaDeAlerta("ALERTA","Não foi possível concluir a trancrição, o documento não permite a cópia dos dados.", 3);
			}
			
			let overlay = await esperarElemento('div[class="cdk-overlay-container"][style*="hidden"]',null,100);
			if (overlay) { overlay.style.visibility = 'revert' }
		}
		conteudo += '"';
	}
	
	// let textarea = document.createElement("textarea");
	// textarea.textContent = conteudo.replace(/\s{2,}/g, ' '); //tira os espaços em branco duplicados
	// document.body.appendChild(textarea);
	// textarea.select();
	// document.execCommand("copy");
	// document.body.removeChild(textarea);
	let textocopiado = conteudo.replace(/\s{2,}/g, ' ');
	navigator.clipboard.writeText(textocopiado);
	
	fundo(false);
	// browser.runtime.sendMessage({tipo: 'criarAlerta', valor: '\n Conteúdo copiado com sucesso!', icone: '3'});
	
	
	async function esperarTransicao() {
		return new Promise(async resolve => {
			let targetDocumento = document.body;
			let observerDocumento = new MutationObserver(async function(mutationsDocumento) {
				mutationsDocumento.forEach(async function(mutation) {
					if (!mutation.addedNodes[0]) { return }
					if (!mutation.addedNodes[0].tagName) { return }
					// console.log(mutation.addedNodes[0].tagName + " : " + mutation.addedNodes[0].className);
					
					if (mutation.addedNodes[0].tagName == 'DIV' && mutation.addedNodes[0].className == 'cdk-global-overlay-wrapper') {
						overlay = mutation.addedNodes[0].parentElement;
						overlay.style.visibility = 'hidden';
					}
					
					if (mutation.addedNodes[0].tagName == 'PJE-DOCUMENTO-ORIGINAL') {
						observerDocumento.disconnect();
						resolve(true);
					}
					if (mutation.addedNodes[0].tagName == 'NG-COMPONENT') {
						observerDocumento.disconnect();
						await clicarBotao('ng-component button', 'OK');
						resolve(false);
					}
				});
			});
			let configDocumento = { childList: true, subtree:true }
			observerDocumento.observe(targetDocumento, configDocumento); //inicia o MutationObserver
			
			setTimeout(function() {
				observerDocumento.disconnect();				
				resolve(false);
			}, 2000); //aguarda 2 segundos
		});
	}
}

//FUNÇÃO RESPONSÁVEL PELAS AÇÕES DOS BOTÕES AÇÕES_AUTOMATIZADAS_ANEXAR
async function acao_bt_aaAnexar(id) {
	let aa;	
	if (typeof id === 'object') {
		await sleep(1000);
		aa = id;
	} else {
		if (id == 997) {
			//criaBotao_aaAnexar(aaAnexar_temp.length, temp.nm_botao, temp.tipo, temp.descricao, temp.sigilo, temp.modelo, temp.assinar, temp.cor, temp.vinculo, temp.visibilidade);
			aa = {"nm_botao":"ID997_Anexar Depoimento","tipo":"Certidão","descricao":"Registro Audiovisual da Audiência","sigilo":"não","modelo":preferencias.modulo10_juntadaMidia[1],"assinar":"nao","cor":"","vinculo":"Nenhum","visibilidade":"sim"}; //movimentar para expedientes nos casos de tipos especiais
		} else {
			aa = preferencias.aaAnexar[id];
		}
	}	
	
	exibir_mensagem("Executando a Ação Automatizada " + aa.nm_botao + "\nPróximo vínculo: " + (!preferencias.tempAAEspecial ? aa.vinculo : preferencias.tempAAEspecial));
		
	//escolhe PDF
	if (aa.modelo.toLowerCase() === "pdf") {
		await clicarBotao('input[role="switch"]');
	}
	
	//preenche o tipo
	aa.tipo = (aa.tipo != "") ? aa.tipo : "Certidão"; //se não tiver tipo definido será "Certidão"
	await escolherOpcaoTeste('input[aria-label="Tipo de Documento"]', aa.tipo);
	
	//preenche a descrição
	if (aa.descricao != "") {
		await preencherInput('input[aria-label="Descrição"]', aa.descricao);
	}
	
	//sigilo
	aa.sigilo = (aa.sigilo != "") ? aa.sigilo : "nao"; //se não tiver sigilo definido será "Não"
	if (aa.sigilo.toLowerCase().includes("sim")) {
		await clicarBotao('input[name="sigiloso"]');
		if (aa.sigilo.toLowerCase().includes("ativo") && aa.sigilo.toLowerCase().includes("passivo")) {
			await documentoEmSigilo(1);
		} else if (aa.sigilo.toLowerCase().includes("ativo")) {
			await documentoEmSigilo(2);
		} else if (aa.sigilo.toLowerCase().includes("passivo")) {
			await documentoEmSigilo(3);
		} else {
			await documentoEmSigilo(4);
		}
		
	}
	
	//escolha do modelo
	if (aa.modelo != "") {
		if (aa.modelo.toLowerCase() == "pdf") {
			await aguardarEscolherPDF();
		} else {
			//elimina o carregamento eterno
			let bt_limpar = await esperarElemento('button[aria-label="Limpa o filtro aplicado pela busca"]');
			triggerEvent(document.getElementById('inputFiltro'), 'input');
			triggerEvent(document.getElementById('inputFiltro'), 'keyup');
			
			await preencherInput('input[id="inputFiltro"]', aa.modelo, true);
			let buscandoModelo = await buscandoModeloNaArvore();
			if (!buscandoModelo) {
				await criarCaixaDeAlerta('ATENÇÃO','O modelo ' + aa.modelo + ' não foi encontrado!',3);			
			} else {
				let elementoModelo = await esperarElemento('div[role="treeitem"]', aa.modelo)
				await inserirModeloNoDocumento(elementoModelo);
			}
		}
	}
	
	//juntada de depoimentos
	if (aa.nm_botao.toLowerCase().includes('[anexos]') || aa.nm_botao == "ID997_Anexar Depoimento") {
		await clicarBotao('button[aria-label="Salvar"]', null, true);
		await clicarBotao('pje-editor-lateral div[aria-posinset="2"]','Anexos');
		await clicarBotao('label[class="upload-button"]');
		await esperarSalvamentoDoDocumento();
		
		if (aa.nm_botao == "ID997_Anexar Depoimento") {
			await clicarBotao('pje-editor-lateral div[aria-posinset="2"]','Anexos');
			fundo(false);
			return;
		}
	}
	
	//assinar?
	if (aa.assinar.toLowerCase() == "sim") {
		await clicarBotao('button[aria-label="Assinar documento e juntar ao processo"]', null, true);
		fundo(false);
		monitorFim(aa.vinculo);				
	} else {
		await clicarBotao('button[aria-label="Salvar"]', null, true);
		fundo(false);
		monitorFim(aa.vinculo);
	}
	
	async function aguardarEscolherPDF() {
		return new Promise(async resolve => {
			let btUpload = await esperarElemento('label[class="upload-button"]');
			await clicarBotao(btUpload);
			await btUpload.dispatchEvent(simularTecla('keydown',13)); //TESTE: confirmar pq está dando erro no MAC
			let el_pdf = await esperarElemento('span[class="nome-arquivo-pdf"]', null, 60000);
			if (aa.descricao == "") { //clica na descrição para pegar o nome do documento upado
				let nova_descricao = el_pdf.innerText.replace(new RegExp('.pdf', 'g'), '');
				await preencherInput('input[aria-label="Descrição"]', nova_descricao);
				resolve(true);
			} else {
				resolve(true);
			}
		});
	}
	
	async function inserirModeloNoDocumento(modeloEscolhido) {
		return new Promise(async resolve => {
			
			//***cria o observer
			let observer = new MutationObserver(async function(mutationsDocumento) {
				mutationsDocumento.forEach(async function(mutation) {
					if (!mutation.addedNodes[0]) { return }
					if (!mutation.addedNodes[0].tagName) { return }
					// console.log(mutation.addedNodes[0].tagName + " : " + mutation.addedNodes[0].className + " : " + mutation.addedNodes[0].innerText.length); //excluir após os testes
					
					if (mutation.addedNodes[0].tagName == 'PJE-DIALOGO-VISUALIZAR-MODELO') {
						// console.log("       |___Pje carregando o teor do modelo para visualização...");
						await sleep(500);
						// console.log('       |___clicando sobre o botão "Inserir Modelo".');
						await clicarBotao('button[aria-label="Inserir modelo de documento"]');
						// console.log("       |___Inserindo o conteúdo no editor...");
					}
					
					if (mutation.addedNodes[0].tagName.includes("SIMPLE-SNACK-BAR")) { //avisos de salvamento
														
						if (mutation.addedNodes[0].innerText.includes('inserido com sucesso no editor')) {
							mutation.addedNodes[0].querySelector('button').click(); //fecha o aviso
							observer.disconnect();
							// console.log("       |___Conteúdo inserido no editor.");
							return resolve(true);
						}
						
					}
					
					if (mutation.addedNodes[0].tagName == 'P' && (mutation.addedNodes[0].className.includes('corpo') || mutation.addedNodes[0].className.includes('ck_')) && mutation.addedNodes[0].innerText.length > 1) {
						observer.disconnect();
						// console.log("       |___Conteúdo inserido no editor.");
						return resolve(true);
					}
					
				});
			});
			observer.observe(document.body, { childList: true, subtree: true });
			//********************
			
			// console.log("       |___clicando sobre o modelo encontrado.");
			await clicarBotao(modeloEscolhido);
			
		});
	}
	
	function monitorFim(param) {
		window.opener.focus(''); //devolve o foco para a janela detalhes
		//vamos lá.. ação automatizada em lote: se tiver vínculo/param resolver primeiro. 
		//Depois que encerrar todos os vínculos é que iremos partir para verificar se é uma AA decorrente de Lote
		if (param && param != "nenhum") { //se tem vínculo continua
			window.addEventListener("beforeunload", function (e) {			
				console.log("JANELA ANEXAR fechou...");
				console.log("     |___avisa a janela DETALHES para executar a AA: " + param);
				browser.runtime.sendMessage({tipo: 'storage_vinculo', valor: param});
			});
		} else {
			if (preferencias.AALote.length > 0) { //vem do AA em Lote
				let guardarStorage = browser.storage.local.set({'AALote': ''});
				Promise.all([guardarStorage]).then(values => { window.close() });
			}
		}
		
	}
	
	async function esperarSalvamentoDoDocumento() {
		return new Promise(async resolve => {
			let targetDocumento = document.body;
			let observerSalvamento = new MutationObserver(async function(mutationsDocumento) {
				mutationsDocumento.forEach(async function(mutation) {
					if (!mutation.addedNodes[0]) { return }
					if (!mutation.addedNodes[0].tagName) { return }
					if (mutation.addedNodes[0].tagName.includes("SIMPLE-SNACK-BAR")) { //avisos de salvamento
														
						if (mutation.addedNodes[0].innerText.includes('Minuta salva')) {
							mutation.addedNodes[0].querySelector('button').click(); //fecha o aviso
							observerSalvamento.disconnect();
							resolve(true);
						}
						
					}
					
				});
			});
			let configDocumento = { childList: true, subtree:true }
			observerSalvamento.observe(targetDocumento, configDocumento); //inicia o MutationObserver
		});
	}
}

//FUNÇÃO RESPONSÁVEL PELAS AÇÕES DOS BOTÕES AÇÕES_AUTOMATIZADAS_COMUNICAÇÕES
async function acao_bt_aaComunicacao(id) {
	
	let aa;	
	if (typeof id === 'object') {
		await sleep(1000);
		aa = id;
	} else {
		aa = preferencias.aaComunicacao[id];
	}
	
	exibir_mensagem("Executando a Ação Automatizada " + aa.nm_botao + "\nPróximo vínculo: " + (!preferencias.tempAAEspecial ? aa.vinculo : preferencias.tempAAEspecial))
	
	console.log("***acao_bt_aaComunicacao***");
	inserirParte_BB_CEF();
	
	//preenche o tipo de expediente
	aa.tipo = (aa.tipo != "") ? aa.tipo : "Intimação"; //se não tiver tipo definido será "Intimação"
	await escolherOpcaoTeste2('mat-select[placeholder="Tipo de Expediente"]', aa.tipo + '[exato]');
	
	//tipo de prazo
	if (aa.prazo === "0") { aa.tipo_prazo = "sem prazo" }
	let ancora = await esperarElemento('mat-radio-button', removeAcento(aa.tipo_prazo.toLowerCase()))
	await clicarBotao(ancora.querySelector('input'));
	
	//preenche o prazo de acordo com o tipo
	if (removeAcento(aa.tipo_prazo.toLowerCase()) == "dias uteis") {
		await preencherInput('input[aria-label="Prazo em dias úteis"]', aa.prazo);
	} else if (removeAcento(aa.tipo_prazo.toLowerCase()) == "sem prazo") {
	} else if (removeAcento(aa.tipo_prazo.toLowerCase()) == "data certa") {
		await preencherInput('input[aria-label="Prazo em data certa"]', aa.prazo);
	}
	
	//clicar no botão de confeccionar
	await clicarBotao('button[aria-label="Confeccionar ato agrupado"]');
	
	//escolher o subtipo do expediente
	if (aa.subtipo) {		
		await escolherOpcaoTeste2('input[data-placeholder="Tipo de Documento"]', aa.subtipo + '[exato]');
	}
	
	//preencher a descrição
	if (aa.descricao) {
		await preencherInput('input[aria-label="Descrição"]', aa.descricao);
	}
	
	//sigilo
	aa.sigilo = (aa.sigilo != "") ? aa.sigilo : "nao"; //se não tiver sigilo definido será "Não"
	if (aa.sigilo.toLowerCase().includes("sim")) {
		await clicarBotao('input[name="sigiloso"]');
	}	
	
	//escolha do modelo
	if (aa.modelo != "") {
		//elimina o carregamento eterno
		let bt_limpar = await esperarElemento('button[aria-label="Limpa o filtro aplicado pela busca"]');
		triggerEvent(document.getElementById('inputFiltro'), 'input');
		triggerEvent(document.getElementById('inputFiltro'), 'keyup');
		
		await preencherInput('input[id="inputFiltro"]', aa.modelo, true);
		let buscandoModelo = await buscandoModeloNaArvore();
		if (!buscandoModelo) {
			await criarCaixaDeAlerta('ATENÇÃO','O modelo ' + aa.modelo + ' não foi encontrado!',3);			
		} else {
			let elementoModelo = await esperarElemento('div[role="treeitem"]', aa.modelo)
			await inserirModeloNoDocumento(elementoModelo);
		}
		
	}
	
	//salvar?
	if (aa.salvar.toLowerCase() == "sim") {
		await clicarBotao('button[aria-label="Salvar"]', null);
		await sleep(1000);
		await clicarBotao('button[aria-label="Finalizar minuta"]', null);
		await segueParaOsParametros()
		fundo(false);
		monitorFim(aa.vinculo);
	} else {
		fundo(false);
		let btfinalizarminuta = await esperarElemento('button[aria-label="Finalizar minuta"]');
		btfinalizarminuta.addEventListener('click', async function(event) {
			await sleep(1000);
			await segueParaOsParametros();
			fundo(false);
			monitorFim(aa.vinculo);
		});
	}
	
	//função de teste**** a ideia é escolher o polo que quer intimar [ativo,passivo,terceiros] e se quer clicar em assinar[assinar]
	async function segueParaOsParametros() {
		let parametros = await obterParametros();
		if (parametros.length > 0) {
			fundo(true)
			let condicao = 0;
			if (parametros.includes('ativo')) {
				console.debug('clicou no polo ativo')
				
				let menosDeDezAutores = await esperarElemento('pje-pec-partes-processo button[aria-label*="somente polo ativo"]');
				
				if (menosDeDezAutores) {
					await clicarBotao('pje-pec-partes-processo button[aria-label*="somente polo ativo"]', null, true);			
					condicao = 1;
				} else {
					await clicarBotao('mat-expansion-panel-header[id="mat-expansion-panel-header-0"]');
					await linhasPorPagina('100');
					await clicarBotao('pje-pec-partes-processo button[aria-label="Intimar somente partes exibidas no polo ativo"', null, true);
					await clicarBotao('mat-expansion-panel-header[id="mat-expansion-panel-header-0"]');
					condicao = 1;
				}
				await esperarElemento('pje-pec-tabela-destinatarios i[aria-label="Ato confeccionado"]');
				await sleep(1000); //espera carregar todas as novas configurações do documento
			}
			
			if (parametros.includes('passivo')) {
				console.debug('clicou no polo passivo')

				let menosDeDezReus = await esperarElemento('pje-pec-partes-processo button[aria-label*="somente polo passivo"]');
				
				if (menosDeDezReus) {
					await clicarBotao('pje-pec-partes-processo button[aria-label*="somente polo passivo"]', null, true);			
					condicao = 2;
				} else {
					await clicarBotao('mat-expansion-panel-header[id="mat-expansion-panel-header-1"]');
					await linhasPorPagina('100');
					await clicarBotao('pje-pec-partes-processo button[aria-label="Intimar somente partes exibidas no polo passivo"', null, true);
					await clicarBotao('mat-expansion-panel-header[id="mat-expansion-panel-header-1"]');
					condicao = 2;
				}
				await esperarElemento('pje-pec-tabela-destinatarios i[aria-label="Ato confeccionado"]');
				await sleep(1000); //espera carregar todas as novas configurações do documento
			}
			
			if (parametros.includes('terceiros')) {
				console.debug('clicou em terceiros')
				await clicarBotao('pje-pec-partes-processo button[aria-label*="somente terceiros interessados"]', null, true);
				condicao = 3;
				await sleep(1000); //espera carregar todas as novas configurações do documento
			}

			if (parametros.includes('trt')) {

				if (parametros.includes(':')) {
					// let trt = parametros.split(';');
					let trt = Array.from(parametros.split(';')).find(i => i.includes('trt'));
					let vara = trt.split(':')[1];
					document.querySelector('#maisPje_bt_invisivel_outrosDestinatarios_TRT_Vara').setAttribute('maisPjeNomeDestinatario',vara);
					await clicarBotao('#maisPje_bt_invisivel_outrosDestinatarios_TRT_Vara');
					let enderecoDesconhecido = await esperarElemento('pje-pec-tabela-destinatarios i[aria-label="Endereço desconhecido"]',null,2000);
					if (enderecoDesconhecido) {
						await clicarBotao('pje-pec-tabela-destinatarios button[aria-label="Alterar endereço"]');
						await clicarBotao('pje-pec-dialogo-endereco button[aria-label="Selecionar endereço"]');
						await clicarBotao('pje-pec-dialogo-endereco a[mattooltip="Fechar"]');
						await clicarBotao('pje-pec-coluna-confeccionar-ato button[aria-label="Confeccionar ato"]');
						await clicarBotao('pje-pec-dialogo-ato button[aria-label="Finalizar minuta"]');
					}
				} else {
					await clicarBotao('#maisPje_bt_invisivel_outrosDestinatarios_TRT');
				}
				
				condicao = 4;
				await sleep(1000); //espera carregar todas as novas configurações do documento
			}

			let prontoParaAssinar = await esperarElemento('pje-pec-tabela-destinatarios i[aria-label="Ato confeccionado"]'); //aguarda o ato estar pronto para assinatura. ao menos um ato deve estar pronto para tentar a assinatura
			if (prontoParaAssinar) {
				await sleep(1000); //ajuste fino
				let btSalvar = await esperarElemento('pje-pec-tabela-destinatarios button[aria-label="Salva os expedientes"]'); //esperar a transição já que a função "esperarTransicao()" não funciona nesta tarefa
				await clicarBotao(btSalvar, null, true);
				if (parametros.includes('assinar') && condicao > 0) {
					console.debug('assinando')
					let btAssinar = await esperarElemento('pje-pec-tabela-destinatarios button[aria-label="Assinar ato(s)"]'); //esperar a transição já que a função "esperarTransicao()" não funciona nesta tarefa
					await clicarBotao(btAssinar, null, true);
				}
			}
			
			fundo(false)
		}
		fundo(false)
	}
	
	async function inserirModeloNoDocumento(modeloEscolhido) {
		return new Promise(async resolve => {
			
			//***cria o observer
			let observer = new MutationObserver(async function(mutationsDocumento) {
				mutationsDocumento.forEach(async function(mutation) {
					if (!mutation.addedNodes[0]) { return }
					if (!mutation.addedNodes[0].tagName) { return }
					// console.log(mutation.addedNodes[0].tagName + " : " + mutation.addedNodes[0].className + " : " + mutation.addedNodes[0].innerText.length); //excluir após os testes
					
					if (mutation.addedNodes[0].tagName == 'PJE-DIALOGO-VISUALIZAR-MODELO') {
						console.log("       |___Pje carregando o teor do modelo para visualização...");
						await sleep(500);
						console.log('       |___clicando sobre o botão "Inserir Modelo".');
						await clicarBotao('button[aria-label="Inserir modelo de documento"]');
						console.log("       |___Inserindo o conteúdo no editor...");
					}
					
					if (mutation.addedNodes[0].tagName == 'P' && mutation.addedNodes[0].className == 'corpo' && mutation.addedNodes[0].innerText.length > 1) {
						observer.disconnect();
						console.log("       |___Conteúdo inserido no editor.");
						return resolve(true);
					}
				});
			});
			observer.observe(document.body, { childList: true, subtree: true });
			//********************
			
			console.log("       |___clicando sobre o modelo encontrado.");
			await clicarBotao(modeloEscolhido);
			
		});
	}
	
	async function obterParametros() {
		return new Promise(async resolve => {
			let padrao = /\[(.*?)\]/gm;
			let param = ''
			if (padrao.test(aa.nm_botao)) {				
				param = aa.nm_botao.match(new RegExp(/\[(.*?)\]/gm)).join();
				param = param.replace('[','');
				param = param.replace(']','');
				console.debug('Parametros: ' + param);
				return resolve(param);
			} else {
				return resolve('');
			}
		});
	}
	
	async function linhasPorPagina(qtde) {
		return new Promise(async resolver => {
			let ancora = await esperarElemento('pje-paginador');
			let itensPorPagina = ancora.querySelectorAll('div[class*="mat-select-trigger"]');
			await escolherOpcaoTeste(itensPorPagina[1],qtde);
			resolver(true);
		});
	}
	
	function monitorFim(param) {
		window.opener.focus(''); //devolve o foco para a janela detalhes

		//vamos lá.. ação automatizada em lote: se tiver vínculo/param resolver primeiro. 
		//Depois que encerrar todos os vínculos é que iremos partir para verificar se é uma AA decorrente de Lote
		if (param && param != "nenhum") { //se tem vínculo continua
			window.addEventListener("beforeunload", function (e) {			
				console.log("JANELA COMUNICAÇÃO fechou...");
				console.log("     |___avisa a janela DETALHES para executar a AA: " + param);
				browser.runtime.sendMessage({tipo: 'storage_vinculo', valor: param});
			});
		} else {
			if (preferencias.AALote.length > 0) { //vem do AA em Lote
				let guardarStorage = browser.storage.local.set({'AALote': ''});
				Promise.all([guardarStorage]).then(values => { window.close() });
			}
		}

	}

}

//FUNÇÃO RESPONSÁVEL PELAS AÇÕES DOS BOTÕES AÇÕES_AUTOMATIZADAS_GIGS
async function acao_bt_aaAutogigs(id) {
	fundo(true);	
	let observer_AA_autogigs;
	let aa;	
	if (typeof id === 'object') {
		await sleep(1000);
		aa = id;
	} else {
		aa = preferencias.aaAutogigs[id];
	}
	
	console.log("***acao_bt_aaAutogigs***: " + aa.nm_botao);
	
	exibir_mensagem("Executando a Ação Automatizada " + aa.nm_botao + "\nPróximo vínculo: " + (preferencias.tempAAEspecial.length < 1 ? aa.vinculo : preferencias.tempAAEspecial))
	let gigs_fechado_em_detalhes = document.querySelector('button[aria-label="Mostrar o GIGS"]') ? true : false;
	ligar_mutation_observer(); //sempre que um lançamento ocorre (concluir não) chama o próximo vínculo
	switch (aa.tipo) {
		case 'chip':
			lancarChip()
			break
		case 'comentario':
			lancarComentario();
			break
		case 'lembrete':
			lancarLembrete();
			break
		default: //gigs
			//o GIGS está aberto na janela detalhes?
			if(gigs_fechado_em_detalhes) { await clicarBotao('button[aria-label="Mostrar o GIGS"]') }
			//ação automatizada de apenas abrir o GIGS
			if (id == 999) { 
				browser.runtime.sendMessage({tipo: 'storage_limpar', valor: 'tempBt'}); 
				fundo(false); 
				return; 
			}
			lancarGigs();
			break
	}
	
	async function lancarChip() {
		
		if (aa.nm_botao.includes('[concluir]')) {
			
			let tabelaChips = await esperarElemento('pje-lista-etiquetas');
			if (!tabelaChips) { return }
			
			if (document.querySelector('pje-lista-etiquetas button[aria-label="Expandir Chips"]')) {
				await clicarBotao('pje-lista-etiquetas button[aria-label="Expandir Chips"]');
			}
			
			let listaDeChipsNoProcesso = await esperarColecao('pje-lista-etiquetas mat-chip',1,1000);
			if (!listaDeChipsNoProcesso) { 
			} else {
				let chips = aa.tipo_atividade.split(',');			
				for (const [pos, chip] of chips.entries()) {
					let ancora = await esperarElemento('pje-lista-etiquetas mat-chip button[aria-label*="' + chip + '"]', null, 500);
					if (ancora) {
						await clicarBotao('pje-lista-etiquetas mat-chip button[aria-label*="' + chip + '"]');
						await sleep(preferencias.maisPje_velocidade_interacao);
						let aviso = await esperarElemento('mat-dialog-container','Deseja realmente excluir esse chip do processo?');
						if (aviso) { await clicarBotao(aviso.querySelector('button')) }
					}
				}
			}
			observer_AA_autogigs.disconnect();
			fundo(false);
			monitorFim(aa.vinculo);
			
		} else {
			await clicarBotao('button[aria-label="Incluir Chip Amarelo"]');
			
			if (aa.tipo_atividade.includes("[perguntar]")) {
				let chips = aa.tipo_atividade.replace('[perguntar]','');
				let carregarInput = await esperarElemento('input[data-placeholder="Nome do chip"]');
				if (carregarInput) {
					await preencherInput('input[data-placeholder="Nome do chip"]', chips);
					let bt_salvar = await esperarElemento('button', 'Salvar');
					let bt_cancelar = await esperarElemento('button', 'Cancelar');
					let fundo_cancelar = await esperarElemento('div[class*="cdk-overlay-backdrop cdk-overlay-dark-backdrop"]');
					fundo(false);
					bt_salvar.addEventListener('click', function(event) {
						console.log('clique bt salvar');
						monitorFim(aa.vinculo);	
					});
					bt_cancelar.addEventListener('click', function(event) {
						console.log('clique bt cancelar');
						monitorFim(aa.vinculo);	
					});
					fundo_cancelar.addEventListener('click', function(event) {
						console.log('clique fundo cancelar');
						monitorFim(aa.vinculo);	
					});
					return;
				}			
			}			
				
			let chips = aa.tipo_atividade.split(',');
			for (const [pos, chip] of chips.entries()) {
				let ancora = await esperarElemento('table[name="Etiquetas"] tr', chip + '[MMA]', 500);
				if (ancora) {
					await clicarBotao(ancora.querySelector('input[aria-label="Marcar chip"]'));
				}
			}
			
			//salvar
			if (aa.salvar) {
				if (aa.salvar.toLowerCase() == "sim") {
					await clicarBotao('button', 'Salvar', true);
					fundo(false);
					monitorFim(aa.vinculo);
				} else {
					fundo(false);
					monitorFim(aa.vinculo);
				}
			}
		}
	}
	
	async function lancarComentario() {
		//o GIGS está aberto na janela detalhes?
		if(gigs_fechado_em_detalhes) { await clicarBotao('button[aria-label="Mostrar o GIGS"]') }
		
		//responsavel do processo
		if (aa.responsavel_processo.length > 0) {
			await escolherOpcao('input[aria-label*="Responsável"]', aa.responsavel_processo, 2);
		}
		
		if (aa.nm_botao.includes('[concluir]')) {
			let tabelaComentarios = await esperarElemento('table[name="Lista de Comentários"], div[id="comentarios"]');
			
			if (tabelaComentarios) {
				let listaDeComentarios = await esperarElemento('table[name="Lista de Comentários"] tbody tr, div[id="comentarios"] mat-card',null,500);
				if (listaDeComentarios) {
					listaDeComentarios = await esperarColecao('table[name="Lista de Comentários"] tbody tr, div[id="comentarios"] mat-card');
					if (listaDeComentarios) {
						for (const [pos, comentario] of listaDeComentarios.entries()) {
							if (comentario.innerText.toLowerCase().includes(aa.observacao.toLowerCase())) {
								comentario.querySelector('i[aria-label="Arquivar Comentário"]').click();
								await sleep(preferencias.maisPje_velocidade_interacao);
								let aviso = await esperarElemento('mat-dialog-container','Arquivar comentário');
								if (aviso) { await clicarBotao(aviso.querySelector('button'), null, true) }
								await sleep(1000);
							}
						}
					}
					//aqui dispara o monitorGigs para atualização
					if (preferencias.gigsAbrirGigs) {
						let var1 = browser.storage.local.set({'monitorGIGS': ['acao_bt_aaAutogigs', 999]});
						Promise.all([var1]).then(values => {
							if (preferencias.gigsAbrirGigs) {
								if(gigs_fechado_em_detalhes) {
									document.querySelector('button[aria-label="Esconder o GIGS"]').click();
								}
							}
						});
					}
				}
			}
			
			observer_AA_autogigs.disconnect();
			fundo(false);
			monitorFim(aa.vinculo);
			
			// console.log("          |___Próxima AA: " + aa.vinculo);
			// if (aa.vinculo != "Nenhum") { monitorFim(aa.vinculo) } //dispara o próximo vínculo
			// if (aa.vinculo == "Nenhum") { browser.runtime.sendMessage({tipo: 'storage_limpar', valor: 'AALote'}) }
			// fundo((aa.vinculo != "Nenhum") ? true : false);
			// observer_AA_autogigs.disconnect();
			
		} else {
			//inserir comentário
			await clicarBotao('pje-gigs-comentarios-lista button', 'Novo Comentário')
			let observacao = await getObservacao(aa.observacao);			
			await preencherTextArea('textarea[name="descricao"], textarea[formcontrolname="descricao"]', aa.observacao);
			
			//preencher visibilidade === prazo			
			let ancora = await esperarColecao('pje-gigs-comentarios-cadastro mat-radio-button', 3);
			console.log('          |___aa.prazo: ' + aa.prazo)
			switch (aa.prazo) {
				case 'LOCAL':
					ancora[0].querySelector('input').click();
					break
				case 'RESTRITA':
					ancora[1].querySelector('input').click();
					await escolherComentarioRestrito();
					break
				case 'GLOBAL':
					ancora[2].querySelector('input').click();
					break
			}
			
			
			//salvar
			if (aa.salvar) {
				if (aa.salvar.toLowerCase() == "sim") {
					await clicarBotao('button', 'Salvar', true);
					///****comentário não dá aviso de inclusão com sucesso
					
					//aqui dispara o monitorGigs para atualização
					if (preferencias.gigsAbrirGigs) {
						let var1 = browser.storage.local.set({'monitorGIGS': ['acao_bt_aaAutogigs', 999]});
						Promise.all([var1]).then(values => {
							if (preferencias.gigsAbrirGigs) {
								if(gigs_fechado_em_detalhes) {
									document.querySelector('button[aria-label="Esconder o GIGS"]').click();
								}
							}
						});
					}
					
					fundo(false);
					monitorFim(aa.vinculo);	
					
				} else {
					fundo(false);
					monitorFim(aa.vinculo);	
				}
			}
			
		}
		
	}
	
	async function lancarLembrete() {
		
		if (aa.nm_botao.includes('[concluir]')) {
			
			let aguardarPostits = await esperarElemento('pje-visualizador-post-its div[class*="post-it-set"]');
			if (!aguardarPostits) { return }
			if (aguardarPostits.children.length > 0) { //existem postits
				let postits = await esperarColecao('div[class*="post-it-set"] mat-expansion-panel');
				
				for (const [pos, postit] of postits.entries()) {
					let titulo = postit.querySelector('div[class="post-it-div-titulo"]');
					let conteudo = postit.querySelector('div[aria-label="Conteúdo do Lembrete"]');
					
					if (titulo.innerText.toLowerCase().includes(aa.tipo_atividade.toLowerCase()) && conteudo.innerText.toLowerCase().includes(aa.observacao.toLowerCase())) {
						await clicarBotao('button[aria-label="Remover Lembrete"]');
						await sleep(preferencias.maisPje_velocidade_interacao);
						let aviso = await esperarElemento('mat-dialog-container','Excluir Lembrete');
						if (aviso) { await clicarBotao(aviso.querySelector('button'), null, true) }
						await esperarSalvamento();
					}
				}
			}
			
			fundo(false);
			monitorFim(aa.vinculo);	
			
		} else {
			
			await clicarBotao('button[id="botao-menu"]');			
			await clicarBotao('button[aria-label="Lembretes"]');
			
			//preencher titulo === tipo_atividade
			await preencherInput('input[id="tituloPostit"]', aa.tipo_atividade);
						
			//preencher visibilidade === prazo			
			await escolherOpcaoTeste('mat-select[id="visibilidadePostit"]', aa.prazo);
			
			if (aa.prazo == 'PRIVADO') {
				await esperarTransicao();
				await escolherLembreteRestrito();
			}
			
			//prencher descricao === observacao
			let observacao = await getObservacao(aa.observacao);
			await preencherTextArea('textarea[id="conteudoPostit"]', observacao); //observacao
			
			//salvar
			if (aa.salvar) {
				if (aa.salvar.toLowerCase() == "sim") { await clicarBotao('button', 'Salvar') }
				await esperarSalvamento();
				
			}
			
			// fundo(false); //desliga o fundo
			// if (aa.vinculo != "Nenhum") { monitorFim(aa.vinculo) } //dispara o próximo vínculo
			
			fundo(false);
			monitorFim(aa.vinculo);	
			
		}
	}
	
	async function lancarGigs() {
		//o GIGS está aberto na janela detalhes?
		if(!document.querySelector('pje-gigs-ficha-processo')) { await clicarBotao('button[aria-label="Mostrar o GIGS"]') }
		
		//responsavel do processo
		if (aa.responsavel_processo.length > 0) {
			await escolherOpcaoTeste('input[aria-label*="Responsável"]', aa.responsavel_processo);
		}
		
		if (aa.nm_botao.includes('[concluir]')) {
						
			let listaDeAtividades = await esperarColecao('table[name="Lista de Atividades"] tbody tr', 1 , 100);
			if (listaDeAtividades) {

				let condicao1 = false; //condição 1: testar se a atividade corresponde
				let condicao2 = false; //condição 2: testar se o responsável corresponde
				let condicao3 = false; //condição 3: testar se a observação corresponde
				
				// console.log("*************REGRA " + "responsável: " + aa.responsavel.toLowerCase() + "\n" + aa.tipo_atividade.toLowerCase() + "\n" + aa.observacao.toLowerCase());
				for (const [pos, atividade] of listaDeAtividades.entries()) {
					
					//separando o joio do trigo
					let responsavelTemp = atividade.querySelector('span[class*="texto-responsavel"]')?.textContent.toLowerCase();
					responsavelTemp =  typeof(responsavelTemp) == "undefined" ? "" : responsavelTemp;
					let tipoDeAtividadeTemp = atividade.querySelector('span[class*="descricao"]')?.textContent.toLowerCase();
					tipoDeAtividadeTemp = tipoDeAtividadeTemp.split(':')[0];
					let observacaoTemp = atividade.textContent.toLowerCase().replace(tipoDeAtividadeTemp + ':','');
					observacaoTemp = observacaoTemp.replace(responsavelTemp,'');					
					// console.log('---->Linha ' + pos);
					
					
					
					//SE O CAMPO ESTIVER EM BRANCO.. ELE NÃO SERÁ UTILIZADO COMO CRITÉRIO DE ESCOLHA
					if (!aa.tipo_atividade) {
						condicao1 = true;
					} else {
						// console.log('      |---->Tipo de Atividade: ' + tipoDeAtividadeTemp);
						condicao1 = await atividadeEstaNaLista(aa.tipo_atividade.toLowerCase().split(';'), tipoDeAtividadeTemp);						
					}
					
					await sleep(preferencias.maisPje_velocidade_interacao);
					
					if (!aa.responsavel) {
						condicao2 = true;
					} else {
						// console.log('      |---->Responsável: ' + responsavelTemp);
						condicao2 = await atividadeEstaNaLista(aa.responsavel.toLowerCase().split(';'), responsavelTemp);						
					}
					
					await sleep(preferencias.maisPje_velocidade_interacao);
					
					if (!aa.observacao) {
						condicao3 = true;
					} else {
						// console.log('      |---->Observação: ' + observacaoTemp);
						condicao3 = await atividadeEstaNaLista(aa.observacao.toLowerCase().split(';'), observacaoTemp);
					}
					
					await sleep(preferencias.maisPje_velocidade_interacao);
					
					// console.log("*************Atividade " + pos + ": " + atividade.textContent.toLowerCase());
					// console.log('condicao1 (Atividade): ' +  condicao1);
					// console.log('condicao2 (Responsável pelo GIGS): ' +  condicao2);
					// console.log('condicao3 (Observação): ' +  condicao3);					
					// console.log(condicao1 + " : " + condicao2 + " : " + condicao3)
					
					if (condicao1 && condicao2 && condicao3) {
						
						await concluirAtividade(atividade.textContent.toLowerCase());
						await sleep(preferencias.maisPje_velocidade_interacao);
						await clicarBotao('button', 'Salvar');
						await esperarSalvamento();
						
					}
					
					await sleep(preferencias.maisPje_velocidade_interacao);
				}
				//aqui dispara o monitorGigs para atualização
				if (preferencias.gigsAbrirGigs) {
					let var1 = browser.storage.local.set({'monitorGIGS': ['acao_bt_aaAutogigs', 999]});
					Promise.all([var1]).then(values => {
						if (preferencias.gigsAbrirGigs) {
							if(gigs_fechado_em_detalhes) { document.querySelector('button[aria-label="Esconder o GIGS"]').click() }
						}
					});
				}
			
			}
			
			fundo(false);
			monitorFim(aa.vinculo);			
			
		} else {
			await clicarBotao('pje-gigs-lista-atividades button', 'Nova atividade');
			await esperarTransicaoMatBar('pje-gigs-cadastro-atividades mat-progress-bar');
			
			//tipo de atividade
			if (aa.tipo_atividade.length > 0) {
				await escolherOpcaoGIGS('input[formcontrolname="tipoAtividade"]', aa.tipo_atividade+'[exato]');
			}
			
			//responsável da atividade
			if (aa.responsavel.length > 0) {
				await escolherOpcaoGIGS('input[formcontrolname="responsavel"]', aa.responsavel);
			} else {
				await gigsAtribuirResponsavel();
			}
			
			//preenche o campo observação
			if (aa.observacao.length > 0) {
				let observacao = await getObservacao(aa.observacao);
				await preencherTextArea('textarea[formcontrolname="observacao"]', observacao); //observacao
			}
			
			//escolhe a quantidade de dias úteis, se for prazo
			if (aa.prazo) {
				if (aa.prazo.length < 5) {
					await preencherInput('input[formcontrolname="dias"]', aa.prazo);
					
				} else {
					await preencherInput('input[data-placeholder="Data Prazo"]', aa.prazo);
				}
				await sleep(1000); //espera o gigs realizar o cálculo dos prazos
			}
			
			
			//salvar
			if (aa.salvar) {
				if (aa.salvar.toLowerCase() == "sim") {
					await clicarBotao('button', 'Salvar');
					await esperarSalvamento();
					
					//aqui dispara o monitorGigs para atualização
					if (preferencias.gigsAbrirGigs) {
						let var1 = browser.storage.local.set({'monitorGIGS': ['acao_bt_aaAutogigs', 999]});
						Promise.all([var1]).then(values => {
							if (preferencias.gigsAbrirGigs) {
								if(gigs_fechado_em_detalhes) {
									document.querySelector('button[aria-label="Esconder o GIGS"]').click();
								}
							}
						});
					}
					
					//NÃO PRECISA CHAMAR POIS A FUNÇÃO ligar_mutation_observer VERIFICA SE A JANELA DE LANÇAMENTO DA ATIVIDADE É FECHADA
					// fundo(false);
					// monitorFim(aa.vinculo);	
					
				} else {
					fundo(false);
					await esperarSalvamento();
					monitorFim(aa.vinculo);	
				}
			}
			
		}
	}
	
	async function getObservacao(observacao) {
		return new Promise(async resolve => {
			if (observacao != "") {
				if (observacao.includes("perguntar")) {
					let msg = "";
					let txt = observacao;
					txt = txt.replace('perguntar','');
					msg = "Observação:" + msg;
					
					// observacao = prompt(msg,txt);
					observacao = await criarCaixaDePergunta('text', msg, txt);
					resolve(observacao);
				} else if (observacao.includes("corrigir data")) {
					let msg = "";
					observacao = observacao.replace('corrigir data','');
					
					msg = "Escolha o prazo (data fixa ou dias úteis):" + msg;
					aa.prazo = await criarCaixaDePergunta('text', msg, '');
					
					resolve(observacao);
				} else {
					resolve(observacao);
				}
			} else {
				resolve("");
			}
		});
	}
	
	
	async function escolherComentarioRestrito() {
		return new Promise(async resolve => {
			let ancora = document.querySelector('pje-gigs-comentarios-cadastro mat-select[placeholder="Usuários concedidos"]')
			ancora.firstElementChild.click(); //clica para abrir as opções
			fundo(false); //desliga o fundo para o usuario escolher
			let fundoFalso = await esperarElemento('div[class="cdk-overlay-container"] div[class="cdk-overlay-connected-position-bounding-box"]');
			fundoFalso.style.backgroundColor = '#000000b5';
			
			// criar mutation para descobrir quando ele termina de escolher os usuarios
			console.log("          |___Extensão maisPJE (" + agora() + "): monitor_AA_Comentário_restrito");
			let targetDocumento = document.body;
			let observerDocumento = new MutationObserver(async function(mutationsDocumento) {
				mutationsDocumento.forEach(async function(mutation) {
					if (!mutation.removedNodes[0]) { return }

					if (mutation.removedNodes[0]) {
						if (!mutation.removedNodes[0].tagName) { return }
						// console.log("          |___----------REMOVEDNODES: " + mutation.removedNodes[0].tagName + " : " + mutation.removedNodes[0].className + " : " + mutation.removedNodes[0].innerText);
						if (mutation.removedNodes[0].tagName == 'DIV' && mutation.removedNodes[0].className.includes('cdk-overlay-backdrop')) {
							observerDocumento.disconnect();
							fundoFalso.style.backgroundColor = 'revert';
							fundo(true);
							resolve(true);
						}
					}

				});
			});
			let configDocumento = { childList: true, subtree:true }
			observerDocumento.observe(targetDocumento, configDocumento); //inicia o MutationObserver
		});
	}
	
	async function escolherOpcaoGIGS(seletor, valor, possuiBarraProgresso) {
		return new Promise(async resolve => {
			//NOVOS TESTES PARA QUE A FUNÇÃO FUNCIONE EM ABAS(GUIAS) DESATIVADAS
			await sleep(preferencias.maisPje_velocidade_interacao);
			if (seletor instanceof HTMLElement) {
			} else {
				seletor = await esperarElemento(seletor);
			}		
			
			seletor.focus();
			seletor.dispatchEvent(simularTecla('keydown',40)); //SETA PRA BAIXO
			
			//teste1 : o carregamento muito rápido da página por vezes não permite ao menu de opções abrir para selecionar a opção desejada
			let teste = await esperarColecao('mat-option[role="option"], option', 5, 1000);			
			if (!teste) {
				seletor.focus();
				seletor.dispatchEvent(simularTecla('keydown',40)); //SETA PRA BAIXO
				//teste2
				teste = await esperarColecao('mat-option[role="option"], option', 5, 1000);			
				if (!teste) {
					seletor.focus();
					seletor.dispatchEvent(simularTecla('keydown',40)); //SETA PRA BAIXO
					//teste3
					teste = await esperarColecao('mat-option[role="option"], option', 5, 1000);			
					if (!teste) {
						seletor.focus();
						seletor.dispatchEvent(simularTecla('keydown',40)); //SETA PRA BAIXO
					}
				}
			}
			
			await clicarBotao('mat-option[role="option"], option', valor); //aciona a opção
			if (possuiBarraProgresso) {
				await observar_mat_progress_bar();
			}
			return resolve(true);
		});

		async function observar_mat_progress_bar() {
			return new Promise(resolve => {
				let observer = new MutationObserver(function(mutationsDocumento) {
					mutationsDocumento.forEach(function(mutation) {
						if (!mutation.removedNodes[0]) { return }
						if (!mutation.removedNodes[0].tagName) { return }
						if (!mutation.removedNodes[0].tagName.includes("MAT-PROGRESS-BAR")) { return }
						resolve(true);
						observer.disconnect();
					});
				});
				let configDocumento = { childList: true, subtree:true }
				observer.observe(document.body, configDocumento);
			});
		}
	}
	
	async function esperarTransicao() {
		return new Promise(async resolve => {
			let targetDocumento = document.body;
			let observerDocumento = new MutationObserver(async function(mutationsDocumento) {
				mutationsDocumento.forEach(async function(mutation) {
					if (!mutation.removedNodes[0]) { return }
					if (mutation.removedNodes[0]) {
						if (!mutation.removedNodes[0].tagName) { return }
						if (mutation.removedNodes[0].tagName == 'DIV' && mutation.removedNodes[0].className.includes('cdk-overlay-backdrop')) {
							observerDocumento.disconnect();
							resolve(true);
						}
					}

				});
			});
			let configDocumento = { childList: true, subtree:true }
			observerDocumento.observe(targetDocumento, configDocumento); //inicia o MutationObserver
		});
	}
	
	function atividadeEstaNaLista(lista, atividade) {
		return new Promise(resolve => {
			let resposta = false;
			for (const [pos, itemDaLista] of lista.entries()) {
				console.log('               |---->' + atividade + ' (' + itemDaLista + '): ' + atividade.includes(itemDaLista));
				if (atividade.includes(itemDaLista)) {
					resposta = true;
				}
			}
			resolve(resposta);
		});
	}
	
	function concluirAtividade(referencia) {
		return new Promise(resolve => {
			let listaDeAtividadesAtualizada = document.querySelectorAll('table[name="Lista de Atividades"] tbody tr');
			
			for (const [pos, linha] of listaDeAtividadesAtualizada.entries()) {
				
				// console.log('      |____' + linha.textContent.toLowerCase() + "-->" + (linha.textContent.toLowerCase().includes(referencia)));
				
				if (linha.textContent.toLowerCase().includes(referencia)) {
					linha.scrollIntoView({behavior: 'auto',block: 'center',inline: 'center'});
					linha.querySelector('i[aria-label="Concluir Atividade"]').click();
					return resolve(true);					
				}
			}
		});
	}
	
	async function esperarSalvamento() {
		return new Promise(async resolve => {
			let target = document.body;
			let observer = new MutationObserver(async function(mutations) {
				mutations.forEach(async function(mutation) {
					if (!mutation.addedNodes[0]) { return }					
					if (!mutation.addedNodes[0].tagName) { return }
					if (mutation.addedNodes[0].tagName.includes("SIMPLE-SNACK-BAR")) { //avisos de erro
						if (mutation.addedNodes[0].innerText.includes('com sucesso!')) {
							mutation.addedNodes[0].querySelector('button').click(); //fecha o aviso de erro
							observer.disconnect();
							// console.log('---Atividade concluída com sucesso"')
							resolve(true);
						}
						
						if (mutation.addedNodes[0].innerText.includes('Tipo de argumento inválido')) {
							mutation.addedNodes[0].querySelector('button').click(); //fecha o aviso de erro
							await sleep(preferencias.maisPje_velocidade_interacao);
							await clicarBotao('button', 'Salvar');
						}
					}
				});
			});
			let config = { childList: true, subtree:true }
			observer.observe(target, config); //inicia o MutationObserver
		});
	}
	
	function esperarTransicaoMatBar(seletor) {
		return new Promise(resolve => {
			let check = setInterval(function() {
				// console.log(document.querySelector(seletor)?.className.includes('invisivel'));
				if (document.querySelector(seletor)?.className.includes('invisivel')) {
					clearInterval(check);					
					resolve(true);
				}				
			}, 10);
		});
	}
	
	async function escolherLembreteRestrito() {
		return new Promise(async resolve => {
			let ancora = await esperarElemento('pje-dialogo-post-it mat-select[id="destinatarioPostit"]');
			ancora.firstElementChild.click(); //clica para abrir as opções
			
			fundo(false); //desliga o fundo para o usuario escolher
			let fundoFalso = await esperarElemento('div[class="cdk-overlay-container"] div[class="cdk-overlay-connected-position-bounding-box"]');
			fundoFalso.style.backgroundColor = '#000000b5';
			
			await esperarTransicao();
			
			fundoFalso.style.backgroundColor = 'revert';
			fundo(true);
			resolve(true);
		});
	}
		
	function monitorFim(param) {
		observer_AA_autogigs.disconnect();
		
		console.log("          |___monitor Fim: " + param);
		if (param && param != "nenhum") { //se tem vínculo continua
			
			browser.runtime.sendMessage({tipo: 'storage_vinculo', valor: param});

		} else {

			if (preferencias.AALote.length > 0) { //vem do AA em Lote
				let guardarStorage = browser.storage.local.set({'AALote': ''});
				Promise.all([guardarStorage]).then(values => { window.close() });
			}
		}

	}
	
	function ligar_mutation_observer() {
		return new Promise(resolve => {
			observer_AA_autogigs = new MutationObserver(function(mutationsDocumento) {
				mutationsDocumento.forEach(function(mutation) {
					if (!mutation.removedNodes[0]) { return }
					if (!mutation.removedNodes[0].tagName) { return }
					// console.log("***[DEL] " + mutation.removedNodes[0].tagName);
					
					//ATIVIDADES
					if (mutation.removedNodes[0].tagName.includes('PJE-GIGS-CADASTRO-ATIVIDADES')) {
						// console.log('MUTATION ATIVIDADES')
						observer_AA_autogigs.disconnect();
						fundo(false);
						monitorFim(aa.vinculo);	
					}
					
					//COMENTÁRIOS
					if (mutation.removedNodes[0].tagName.includes('PJE-GIGS-COMENTARIOS-CADASTRO')) {
						// console.log('MUTATION COMENTÁRIOS')
						observer_AA_autogigs.disconnect();
						fundo(false);
						monitorFim(aa.vinculo);	
					}
					
					//CHIP 
					if (mutation.removedNodes[0].tagName.includes('PJE-INCLUI-ETIQUETAS-DIALOGO')) {
						// console.log('MUTATION CHIP')
						observer_AA_autogigs.disconnect();
						fundo(false);
						monitorFim(aa.vinculo);	
					}
					
					//LEMBRETES
					if (mutation.removedNodes[0].tagName.includes('PJE-DIALOGO-POST-IT')) {
						// console.log('MUTATION LEMBRETES')
						observer_AA_autogigs.disconnect();
						fundo(false);
						monitorFim(aa.vinculo);	
					}
				});
			});
			let configDocumento = { childList: true, subtree:true }
			observer_AA_autogigs.observe(document.body, configDocumento); //inicia o MutationObserver
		});
	}

}

//FUNÇÃO RESPONSÁVEL PELAS AÇÕES DOS BOTÕES AÇÕES_AUTOMATIZADAS_DESPACHO
async function acao_bt_aaDespacho(id) {
	let aa;	
	if (typeof id === 'object') {
		await sleep(1000);
		aa = id;
	} else {
		if (id == 999) {
			console.log("id 999");
			aa = {nm_botao:"",tipo:"",descricao:"",sigilo:"",modelo:"",juiz:"",responsavel:"",cor:"",vinculo:""};
		} else {
			aa = preferencias.aaDespacho[id];
		}
	}
	
	exibir_mensagem("Executando a Ação Automatizada " + aa.nm_botao + "\nPróximo vínculo: " + (!preferencias.tempAAEspecial ? aa.vinculo : preferencias.tempAAEspecial))
	
	await movimentar_destino();
	
	async function movimentar_destino() {
		return new Promise(async resolve => {
			console.log("movimentar_destino()");
			let tarefa = await obter_tarefa();
			tarefa = removeAcento(tarefa.toLowerCase()); //tira os acentos e deixa tudo minusculo
			let destino = "conclusao ao magistrado";
			console.log("Tarefa atual: " + tarefa + " >>> " + destino);
			if (tarefa.includes(destino)) { //chegou no destino
				conclusao_do_processo();
			} else {
				//procura se tem o botão com o nome do destino
				if (tarefa.includes('analise')) {
					await esperarColecao('pje-botoes-transicao button', 15); // 1grau: 17 botoes 2grau: 18
					await clicarBotao('button', destino, true);
					conclusao_do_processo();
				} else if (tarefa.includes('elaborar')) { //exceção: cancelar a AA nas tarefas Elaborar despacho/decisão/sentença
					console.log("     |___processo na tarefa Elaborar despacho/decisão/sentença: AA cancelada!" );
					verificarMinutaPreenchida();
					// fundo(false);
					// return resolve(false);
				} else {
					await movimentar_analise(tarefa);
					await movimentar_destino();
				}
			}
		});
	}
	
	async function movimentar_analise(tarefa) {
		return new Promise(async resolve => {
			console.log("movimentar_analise(" + tarefa + ")");
			if (tarefa.includes('conclusao ao magistrado')) {
				await clicarBotao('button', 'cancelar Conclusao', true);
			} else if (tarefa.includes('preparar expedientes e comunicacoes')) {
				await clicarBotao('button', 'cancelar expedientes', true);
			} else if (tarefa.includes('arquivo')) {
				await clicarBotao('button', 'desarquivar', true);
			} else if (tarefa.includes('aguardando final do sobrestamento')) {
				await clicarBotao('button', 'encerrar');
				await clicarBotao('button', 'Sim', true);
			} else if (tarefa.includes('iniciar Execucao')) {
				await clicarBotao('button', 'iniciar', true);
			} else if (tarefa.includes('iniciar liquidacao')) {
				await clicarBotao('button', 'iniciar', true);
			} else if (tarefa.includes('remeter')) {
				await clicarBotao('button', 'cancelar', true);
			} else { //movimentar para o Análise
				await clicarBotao('button', 'analise', true);
			}
			
			await esperarTransicao();
			resolve(true);
		});
	}
	
	async function obter_tarefa() {
		return new Promise(async resolve => {
			let url = document.location.href;
			let codigo_tarefa = url.substr(url.search('/tarefa/') + 8, 3);
			let nome_tarefa = await obterNomeTarefaViaApi(codigo_tarefa);
			return resolve(nome_tarefa);
		});
	}
	
	async function conclusao_do_processo() {
		if (id == 999) { //apenas a conclusao (clique no martelo) ou sem juiz definido
			filtroMagistrado();
			fundo(false);
			return;
		}
		
		//escolhe o magistrado
		if (aa.juiz != "") { 
			await escolherOpcao('mat-select[placeholder="Magistrado"]', aa.juiz, 2);
		} else {
			await filtroMagistrado();
		}
		
		//espera por dois segundos pela regra de impedimento ou suspeição, bem como para recarregar os botões (eles mudam sempre que troca o juiz)
		let impedimento_suspeição = await esperarElemento('i[mattooltip="Existe impedimento ou suspeição para este Magistrado"]', null, 2000);
		
		if (impedimento_suspeição) {
			fundo(false);
			criarCaixaDeAlerta("ALERTA",'Atenção, o(a) Magistrado(a) possui regra de suspeição/impedimento ativa para este processo!');			
			return;
		}
		
		//escolhe o tipo de conclusão
		aa.tipo = (aa.tipo != "") ? aa.tipo : "Despacho"; //se não tiver tipo definido será "Despacho"
		let ancora = await esperarElemento('pje-concluso-tarefa-botao', aa.tipo);
		
		//se o usuário estiver no segundo grau, ao clicar no botão a ação seguirá para o PJe1 e interromperá o script
		//neste caso levarei o vínculo para a tempAR para executar no recarregamento
		//contudo apenas as conclusões de julgamento levam para o PJe1, as outras decisão e despacho levam para o PJeKZ
		let conclusaoEhJulgamento = ancora.querySelector('button[class*="-JULGAMENTO"]');
		// console.log('aguardando: ' + preferencias.grau_usuario)
		// console.log('aguardando: ' + conclusaoEhJulgamento)
		if (preferencias.grau_usuario == 'segundograu' && conclusaoEhJulgamento) {			
			let guardarStorage = browser.storage.local.set({'tempAR': aa.vinculo});
			Promise.all([guardarStorage]).then(values => { 
				let botao_ativado = clicarBotao(ancora.firstElementChild);
				if (!botao_ativado) { //verifica se o botão está habilitado
					fundo(false);
					return;
				}
			});			
			
		} else {
		
			let botao_ativado = await clicarBotao(ancora.firstElementChild);
			if (!botao_ativado) { //verifica se o botão está habilitado
				fundo(false);
				return;
			}
			
			//esperar a transição da página para elaborar despacho/decisão/sentença
			await esperarElemento('PJE-ARVORE-MODELO-DOCUMENTO');
			
			//preenche a descrição
			if (aa.descricao != "") {
				await preencherInput('input[aria-label="Descrição"]', aa.descricao);
			}
			
			//sigilo
			aa.sigilo = (aa.sigilo != "") ? aa.sigilo : "nao"; //se não tiver sigilo definido será "Não"
			if (aa.sigilo.toLowerCase() == "sim") {
				await clicarBotao('input[name="sigiloso"]');
			}
			
			//escolha do modelo
			if (aa.modelo != "") {
				let foco = await esperarElemento('div[class="area-conteudo"] div[class="placeholder-conteudo"]');
				let ehSentenca = Array.from(document.querySelectorAll('div[class="area-conteudo"] div[class="placeholder-conteudo"]')).find(el => el.innerText.toLowerCase().includes('dispositivo'));
				// console.log('   |___________________________________' + ehSentenca?.innerText.toLowerCase() + '      : ' + ehSentenca)				
				
				if (ehSentenca) {
					ehSentenca.previousSibling.focus(); //se for sentença. insere o modelo no dispositivo				
				} else {
					foco.previousSibling.focus(); // feitoassim porque o TRT15 deixa o título do documento como documento editável
				}
				
				await preencherInput('input[id="inputFiltro"]', aa.modelo, true);
				let buscandoModelo = await buscandoModeloNaArvore();
				if (!buscandoModelo) {
					await criarCaixaDeAlerta('ATENÇÃO','O modelo ' + aa.modelo + ' não foi encontrado!',3);			
				} else {
					let elementoModelo = await esperarElemento('div[role="treeitem"]', aa.modelo)
					await inserirModeloNoDocumento(elementoModelo);
				}
				
			} else {
				let bt_limpar = await esperarElemento('button[aria-label="Limpa o filtro aplicado pela busca"]');
			}
			
			//salva as modificações
			await clicarBotao('button[aria-label="Salvar"]', null, true);
			
			//preencher movimentos
			const comandos = await extrairComandosComuns(aa.nm_botao);
			console.log('comandos: ' + comandos);
			if (comandos.length > 0) {				
				await clicarBotao('button[aria-label="Salvar"]', null, true);
				
				for (const [pos,comando] of comandos.entries()) {					
					console.log('pos,comando: ' + pos + ',' + comando)
	
					if (comando.includes('prazo:')) { //prazo:5 ou prazo:2 ou prazo:0 etc.. 
						await clicarBotao('pje-editor-lateral div[aria-posinset="1"]');
						await sleep(500);
						let prazoDias = comando.replace('prazo:','');
						console.log(prazoDias);
						await definirPrazoEmLote(prazoDias);
						await sleep(500);
						await clicarBotao('pje-intimacao-automatica button[aria-label*="Gravar"]', null, true);
	
					} else if (comando.includes('intimar:')) { //intimar:sim ou intimar:não
						await clicarBotao('pje-editor-lateral div[aria-posinset="1"]');
						if (comando.toLowerCase().includes('sim')) {
							await clicarBotao('button[id="maisPje_marcar"]');
						} else {
							await clicarBotao('pje-intimacao-automatica label[class="mat-slide-toggle-label"]');
						}
						await sleep(500);
						await clicarBotao('pje-intimacao-automatica button[aria-label*="Gravar"]', null, true);
					} else if (comando.includes('movimento:')) { //movimento:(196),(7639)
						await clicarBotao('pje-editor-lateral div[aria-posinset="2"]');
						await sleep(500);
						let movimentos = comando.replace('movimento:','');
						movimentos = movimentos.split(',')
						for (const [i,mo] of movimentos.entries()) {
							if (i == 0) { //tipo de movimento
								let chk = await esperarElemento('pje-movimento mat-checkbox', mo);
								if (!chk.className.includes('checked')) {
									await clicarBotao('pje-movimento mat-checkbox label',mo);
									await sleep(500);
								}
							} else { //complementos do tipo
								await sleep(500);
								let complementosDoTipo = await esperarColecao('pje-complemento');
								await sleep(500);
								let comboBox = complementosDoTipo[i-1].querySelector('mat-select');
								await escolherOpcaoTeste2(comboBox,mo)
								await sleep(500);
							}
						}
						await clicarBotao('pje-lancador-de-movimentos button[aria-label*="Gravar"]');
						await clicarBotao('mat-dialog-container button', 'Sim', true);
					}
				}
			}
			
			//enviar para assinatura
			aa.assinar = typeof(aa.assinar) == "undefined" ? "não" : aa.assinar;
			await clicarBotao('button[aria-label="Salvar"]', null, true);
			if (aa.assinar.toLowerCase() == "sim") {
				await clicarBotao('button[aria-label="Enviar para assinatura"]');
				await esperarTransicao(true);
			}
			
			//responsavel
			if (aa.responsavel.length > 0) {
				await inserirResponsavel();
			}
			
			fundo(false);
			monitorFim(aa.vinculo);
		}
	}
	
	async function verificarMinutaPreenchida() {
		let editorContainer = await esperarColecao('div[class*="editor-container"] div[contenteditable="true"]');
		console.log("editorContainer (qtde): " + editorContainer.length);
		let conteudoEscrito = 0;
		
		for (const [pos, item] of editorContainer.entries()) {
			console.log("Tamanho do texto: " + item.innerText.length);
			conteudoEscrito = conteudoEscrito + item.innerText.length;
		}
		
		console.log("conteudoEscrito: " + conteudoEscrito);
		
		if (conteudoEscrito > editorContainer.length) { //cada editorContainer responde 1 caracter
			//cancelar pois possui despacho elaborado
			criarCaixaDeAlerta("ALERTA",'Identificada minuta em elaboração. Ação automatizada CANCELADA!', 3);
			fundo(false);
			monitorFim(aa.vinculo);
		} else {
			//preenche a descrição
			if (aa.descricao != "") {
				await preencherInput('input[aria-label="Descrição"]', aa.descricao);
			}
			
			//sigilo
			aa.sigilo = (aa.sigilo != "") ? aa.sigilo : "nao"; //se não tiver sigilo definido será "Não"
			if (aa.sigilo.toLowerCase() == "sim") {
				await clicarBotao('input[name="sigiloso"]');
			}
			
			//clica na opção de inserir modelo
			await clicarBotao('div[role="tab"]','Modelos');
			
			//escolha do modelo
			if (aa.modelo != "") {
				let elementoModelo = await buscarModeloNaArvoreDeModelos(aa.modelo);
				await inserirModeloNoDocumento(elementoModelo);
			} else {
				let bt_limpar = await esperarElemento('button[aria-label="Limpa o filtro aplicado pela busca"]');
			}
			
			//responsavel
			if (aa.responsavel.length > 0) {
				await inserirResponsavel();
			}
			
			fundo(false);
			monitorFim(aa.vinculo);
		}
	}
	
	async function inserirResponsavel() {
		await acaoBotaoDetalhes("Abrir o GIGS");
		await escolherOpcaoTeste('pje-gigs-cadastro-responsavel input[aria-label*="Responsável"]', aa.responsavel.toUpperCase());
		await clicarBotao('div[class*="cdk-overlay-backdrop"'); //fecha o gigs
		let span_responsavel = await esperarElemento('span[class*="nome-responsavel"');
		span_responsavel.innerText = aa.responsavel.toUpperCase();
	}
	
	async function buscarModeloNaArvoreDeModelos(nomeModelo) {
		return new Promise(async resolve => {
			//***cria o observer
			let observer = new MutationObserver(async function(mutationsDocumento) {
				mutationsDocumento.forEach(async function(mutation) {
					if (!mutation.addedNodes[0]) { return }
					if (!mutation.addedNodes[0].tagName) { return }
					// console.log("Buscar: " +mutation.addedNodes[0].tagName + " : " + mutation.addedNodes[0].className + " : " + mutation.addedNodes[0].innerText); //excluir após os testes
					
					if (mutation.addedNodes[0].tagName == 'TREE-NODE-COLLECTION') { //entrou nos despachos
						observer.disconnect();
						console.log("       |___Modelo " + nomeModelo + " encontrado.");
						
						
						let buscandoModelo = await preencherInput('input[id="inputFiltro"]', nomeModelo, true);
						await esperarColecao('pje-arvore-modelo-documento div[aria-expanded="true"]',2,2000); //aguardar nova arvore de modelo carregar após a pesquisa
						if (!buscandoModelo) {
							await criarCaixaDeAlerta('ATENÇÃO','O modelo ' + nomeModelo + ' não foi encontrado!', 3);
							return resolve(null);							
						} else {
							// await sleep(500);
							let elementoModelo = await esperarElemento('div[role="treeitem"]', nomeModelo);
							return resolve(elementoModelo)
						}
					}
				});
			});			
			observer.observe(document.body, { childList: true, subtree: true });
			//********************
			
			
			//código para eliminar o carregamento eterno dos modelos gerais
			console.log('maisPje: previne o carregamento eterno..');
			let bt_limpar = await esperarElemento('button[aria-label="Limpa o filtro aplicado pela busca"]');
			triggerEvent(document.getElementById('inputFiltro'), 'input');
			triggerEvent(document.getElementById('inputFiltro'), 'keyup');
			
			console.log("MaisPje: buscar modelo " + nomeModelo + " na árvore de modelos.");
		});
	}
	
	async function inserirModeloNoDocumento(modeloEscolhido) {
		return new Promise(async resolve => {
			
			//MÉTODO ANTIGO PARA AVERIGUAR SE O MODELO FOI INSERIDO NO EDITOR. AGORA EXISTE UMA AVISO CONFIRMANDO
			//***cria o observer
			let observer = new MutationObserver(async function(mutationsDocumento) {
				mutationsDocumento.forEach(async function(mutation) {
					if (!mutation.addedNodes[0]) { return }
					if (!mutation.addedNodes[0].tagName) { return }
					
					if (mutation.addedNodes[0].tagName == 'PJE-DIALOGO-VISUALIZAR-MODELO') {
						
						console.log("       |___Pje carregando o teor do modelo para visualização...");
						await sleep(1000 + parseInt(preferencias.maisPje_velocidade_interacao));
						console.log('       |___clicando sobre o botão "Inserir Modelo".');
						await clicarBotao('button[aria-label="Inserir modelo de documento"]');
						console.log("       |___Inserindo o conteúdo no editor...");
						// observer.disconnect();
					}
					
					if (mutation.addedNodes[0].tagName.includes("SIMPLE-SNACK-BAR")) {
						//Modelo de documento inserido com sucesso no editor
						if (mutation.addedNodes[0].innerText.includes('Modelo de documento inserido com sucesso no editor')) {
							mutation.addedNodes[0].querySelector('button').click(); //fecha o aviso
							observer.disconnect();
							console.log("       |___Conteúdo inserido no editor. <aviso>");
							return resolve(true);
						}
					}
					
					if (mutation.addedNodes[0].tagName == 'P' && mutation.addedNodes[0].className == 'corpo' && mutation.addedNodes[0].innerText.length > 1) {
						observer.disconnect();
						console.log("       |___Conteúdo inserido no editor. <p class='corpo'>");
						return resolve(true);
					}
					
					if (mutation.addedNodes[0].tagName == 'OL' && mutation.addedNodes[0].parentElement.tagName == 'DIV' && mutation.addedNodes[0].parentElement.className.includes('area-conteudo') && mutation.addedNodes[0].innerText.length > 1) {
						observer.disconnect();
						console.log("       |___Conteúdo inserido no editor. <ol>");
						return resolve(true);
					}
				});
			});
			observer.observe(document.body, { childList: true, subtree: true });
			//********************
			
			console.log("       |___clicando sobre o modelo encontrado.");
			await clicarBotao(modeloEscolhido);
			
		});
	}
	
	async function esperarTransicao(esperar=true, tempo=10000) {
		return new Promise(async resolve => {
			if (!esperar) { return resolve(true) }
			
			//condição de transição entre as tarefas
			let check0 = setInterval(function() {
				if (document.location.href.includes('/transicao')) {
					clearInterval(check0);
					console.log('maisPje : esperarTransicao() : transição finalizada!');
					resolve(true);
				}				
			}, 10);
			
			let passoUm = false;
			
			//condições de transição entre elaborar despacho/decisão/sentença e assinar despacho/decisão/sentença
			let erro = setInterval(async function() {
				
				//erro pendência de movimento
				let aviso = document.querySelector('SIMPLE-SNACK-BAR');
				if (aviso?.innerText?.includes('as movimentações processuais que serão lançadas quando a minuta for assinada')) {
					clearInterval(erro);
					clearInterval(check1);
					clearInterval(check2);
					console.log('maisPje : esperarTransicao() : Erro: Exigência de Movimento!');
					let num = await extrairNumeroProcesso(document.querySelector('pje-cabecalho-processo').innerText);
					let guardarStorage = browser.storage.local.set({'erros': num + ' : AA exige movimento para enviar para assinatura!'});
					Promise.all([guardarStorage]).then(values => {
						resolve(true);
					});
					
					
					resolve(true);
				}
				
				//pendência no documento - marca-texto
				let aviso2 = document.querySelector('div[class="cdk-overlay-container"] mat-dialog-container');
				if (aviso2?.innerText?.includes('Deseja continuar mesmo assim?')) {
					await clicarBotao('div[class="cdk-overlay-container"] mat-dialog-container button','sim');					
				}
				
			}, 100);			
			
			let check1 = setInterval(async function() {
				if (document.location.href.includes('/assinar')) {
					clearInterval(check1);
					passoUm = true;					
				}				
			}, 200);
			
			let check2 = setInterval(async function() {
				if (document.location.href.includes('/assinar') && passoUm) {
					clearInterval(check2);
					clearInterval(check0);
					clearInterval(erro);
					await clicarBotao('button[aria-label="Salvar"]',null, true);
					console.log('maisPje : esperarTransicao() : transição finalizada!');
					resolve(true);
				}				
			}, 500);
			
			setTimeout(async function() {
				clearInterval(erro);
				clearInterval(check0);
				clearInterval(check1);
				clearInterval(check2);
				console.log('maisPje : esperarTransicao() : tempo esgotado!');
				let num = await extrairNumeroProcesso(document.querySelector('pje-cabecalho-processo').innerText);
				let guardarStorage = browser.storage.local.set({'erros': num + ' : PJe lento... tempo esgotado!'});
				Promise.all([guardarStorage]).then(values => {
					resolve(true);
				});
			}, tempo); //aguarda 10 segundos
		});
		
		async function extrairNumeroProcesso(texto) {
			let padrao = /\d{7}\-\d{2}\.\d{4}\.\d{1}\.\d{2}\.\d{4}/g;
			let n = '';
			if (padrao.test(texto)) {
				n = texto.match(padrao).join();
			}	
			return n;
		}
		
	}
	
	async function extrairComandosComuns(texto) {
		console.log(texto)

		let padrao = /\[.+\]/gm;
		let txt = '';
		if (padrao.test(texto)) {
			txt = texto.match(padrao).join();
			txt = txt.replace('[','');
			txt = txt.replace(']','');
			return txt.split(';');
		} else {
			return '';
		}
	}

	async function definirPrazoEmLote(prazoEmLote) {
		let el = document.querySelectorAll('mat-form-field[class*="prazo"]');
		if (!el) {
			return
		}		
		let map = [].map.call(
			el, 
			function(elemento) {				
				let el2 = elemento.querySelector('input');
				el2.focus();
				el2.value = prazoEmLote;
				triggerEvent(el2, 'input');
			}
		);	
		await sleep(500);	
		await clicarBotao('button', 'Gravar', true);
	}

	function monitorFim(param) {
		window.opener.focus(''); //devolve o foco para a janela detalhes

		//vamos lá.. ação automatizada em lote: se tiver vínculo/param resolver primeiro. 
		//Depois que encerrar todos os vínculos é que iremos partir para verificar se é uma AA decorrente de Lote
		if (param && param != "nenhum") { //se tem vínculo continua
			window.addEventListener("beforeunload", function (e) {			
				console.log("JANELA DESPACHO fechou...");
				console.log("     |___avisa a janela DETALHES para executar a AA: " + param);
				browser.runtime.sendMessage({tipo: 'storage_vinculo', valor: param});
			});
		} else {
			if (preferencias.AALote.length > 0) { //vem do AA em Lote
				let guardarStorage = browser.storage.local.set({'AALote': ''});
				Promise.all([guardarStorage]).then(values => { window.close() });
			}
		}

	}
}

//FUNÇÃO RESPONSÁVEL PELAS AÇÕES DOS BOTÕES AÇÕES_AUTOMATIZADAS_MOVIMENTO
async function acao_bt_aaMovimento(id) {
	let aa;	
	if (typeof id === 'object') {
		await sleep(1000);
		aa = id;
	} else {
		if (id == 999) {
			// console.log("id 999");
			aa = {"nm_botao":"","destino":"Comunicações e expedientes","chip":"","responsavel":"","cor":"","vinculo":"Nenhum"}; //movimentar para expedientes nos casos de tipos especiais
			
		} else if (id == 998) {
			// console.log("id 998");
			aa = {"nm_botao":"","destino":"?","chip":"","responsavel":"","cor":"","vinculo":"Nenhum"}; //movimentar para análise e devolver para a tarefa de origem
		} else {
			aa = preferencias.aaMovimento[id];
		}
	}
	
	
	exibir_mensagem("Executando a Ação Automatizada " + aa.nm_botao + "\nPróximo vínculo: " + (!preferencias.tempAAEspecial ? aa.vinculo : preferencias.tempAAEspecial))
	
	await movimentar_destino();
	
	async function movimentar_destino() {
		return new Promise(async resolve => {
			let tarefa = await obter_tarefa();
			tarefa = removeAcento(tarefa.toLowerCase()); //tira os acentos e deixa tudo minusculo
			tarefa = tarefa.includes('preparar expedientes e comunicacoes') ? 'comunicacoes e expedientes' : tarefa; //corrige a tarefa preparar expedientes e comunicacoes
			tarefa = tarefa.includes('aguardando cumprimento de acordo') ? 'controle de acordo' : tarefa; //corrige a tarefa controle de acordo
			aa.ultimoLance = await ultimoLance();
			let destino = aa.destino;
			destino = destino.replace(aa.ultimoLance,''); //corrige o destino retirando a expressão entre colchetes
			destino = destino.replace('[','');
			destino = destino.replace(']','');
			destino = removeAcento(destino.toLowerCase()); //tira os acentos e deixa tudo minusculo
			
			console.log("   <___tarefa: " + tarefa);
			console.log("   <___destino: " + destino);
			if (aa.ultimoLance) { console.log("      |___último lance: " + aa.ultimoLance) }
			
			if (destino.includes('?')) { aa.destino = aa.destino + tarefa } //a tarefaAtual é armazenada para depois. Server para a ação de movimento que tire de devolve para a mesma tarefa
			
			//O PROCESSO JÁ SE ENCONTRA NA TAREFA DESTINO
			if (tarefa.includes(destino)) {
				console.log("      |___O PROCESSO JÁ SE ENCONTRA NA TAREFA DESTINO");
				
				if (id == 999) {
					await fundo(false);
					return acao_bt_aaComunicacao(preferencias.temp_expediente_especial);					
				}
				
				if (aa.ultimoLance) {
					if (!aa.ultimoLance.includes('parar')) {
						await clicarUltimoLance(destino);
					}
				}
				
				console.log(aa.chip)
				await chip_responsável();
				fundo(false);
				monitorFim(aa.vinculo);
				
			//INTERROMPER MOVIMENTOS QUANDO A TAREFA DO PROCESSO FOR ELABORAR OU ASSINAR
			} else if (tarefa.includes('elaborar') || tarefa.includes('assinar')) { //exceção: cancelar a AA Movimento nas tarefas Elaborar despacho/decisão/sentença
				console.log("      |___O PROCESSO SE ENCONTRA EM TAREFA DE ELABORAR OU ASSINAR... AA INTERROMPIDA!!");
				fundo(false);
				monitorFim(aa.vinculo);
			
			//INTERROMPER MOVIMENTOS QUANDO A TAREFA DO PROCESSO FOR AGUARDANDO ACORDO
			} else if (tarefa.includes('controle de acordo')) {
				await criarCaixaDeAlerta("ATENÇÃO","Para evitar problemas estatísticos, este processo não será movido automaticamente.. Movimente-o de forma manual.", 5);
				fundo(false);
				monitorFim(aa.vinculo);
							
			//REGRA GERAL
			} else {
				console.log("      |___REGRAL GERAL");
				
				if (tarefa.includes('analise de recurso interno')) {
					console.log("                |___MOVIDO PARA A TAREFA ANÁLISE DE GABINETE..");
					await movimentar_analise(tarefa);
					await movimentar_destino();
				
				} else if (tarefa.includes('analise')) {
					console.log("           |___JÁ ESTÁ NA TAREFA ANÁLISE");
					
					//AGUARDA O CARREGAMENTO DOS BOTÕES DA TAREFA ANÁLISE
					if (tarefa.includes('de secretaria')) {
						await esperarColecao('pje-botoes-transicao button', 10); //segundo grau só tem 10 botoes
					} else {
						await esperarColecao('pje-botoes-transicao button', 15); // 1grau: 17 botoes 2grau: 18
					}
					
					//AGUARDA O CARREGAMENTO DO BOTÃO DA TAREFA DESTINO
					let bt_destino = await esperarElemento('button', destino);
					
					if (!bt_destino.getAttribute('disabled')) {
						console.log("                |___MOVIDO PARA A TAREFA DESTINO..");
						
						if (id == 999) {
							await clicarBotao('button', destino, true);
							await fundo(false);
							acao_bt_aaComunicacao(preferencias.temp_expediente_especial);
							return;
						}
						
						await clicarBotao('button', destino, true);
						
						
						if (aa.ultimoLance) {
							if (!aa.ultimoLance.includes('parar')) {
								await clicarUltimoLance(destino);
							}
						}
						
						console.log('************finalizando')
						
						await chip_responsável();
						fundo(false);
						monitorFim(aa.vinculo);
						
					} else {
						// console.log("                |___DESTINO DESABILITADO.. AA INTERROMPIDA!!");
						console.log("Destino encontrado porém o botão está desabilitado.");
						await criarCaixaDeAlerta("ALERTA",'A tarefa ' + destino + ' está desativada!',3);
						
						if (aa.ultimoLance) {
							if (!aa.ultimoLance.includes('parar')) {
								await clicarUltimoLance(destino);
							}
						}
						await chip_responsável();
						fundo(false);
						monitorFim(aa.vinculo);
						
					}
					
				//DESTINO É ASSINAR EXPEDIENTES E A TAREFA É O PREPARAR COMUNICAÇÃO, ENTÃO ELE CONSIDERA QUE JÁ ESTÁ NO DESTINO
				} else if (tarefa.includes('comunicacoes e expedientes') && destino.includes('assinar expedientes e comunicacoes')) {
					console.log("           |___CONSIDERO JÁ ESTAR NO DESTINO");
					if (aa.ultimoLance) {
						if (!aa.ultimoLance.includes('parar')) {
							await clicarUltimoLance(destino);
						}
					}
					await chip_responsável();
					fundo(false);
					monitorFim(aa.vinculo);
				
				// SENÃO MOVIMENTA O PROCESSO ATÉ A TAREFA ANÁLISE
				} else {
					console.log("           |___MOVIMENTA PARA A TAREFA ANÁLISE");
					
					await movimentar_analise(tarefa);
					await movimentar_destino();
				}
			}
		});
	}
	
	async function movimentar_analise(tarefa) {
		return new Promise(async resolve => {
			console.log("maisPJe: movimentando o processo da tarefa " + tarefa.toUpperCase() + " para a tarefa ANÁLISE");
			if (tarefa.includes('conclusao ao magistrado')) {
				await clicarBotao('button', 'cancelar Conclusao', true);
				await esperarTransicao();
				
			} else if (tarefa.includes('preparar expedientes e comunicacoes') || tarefa.includes('comunicacoes e expedientes')) {
				await clicarBotao('button', 'cancelar expedientes', true);
				await esperarTransicao(false);
				
			} else if (tarefa.includes('arquivo provisorio')) {
				await clicarBotao('input[value="Arquivo"]');
				await esperarTransicao();
				//interrompe qualquer ação vinculada
				let guardarStorage = browser.storage.local.set({'AALote': ''});
				Promise.all([guardarStorage]).then(values => {
					window.close();
				});
				
			} else if (tarefa.includes('arquivo')) {
				await clicarBotao('button', 'desarquivar', true);
				await esperarTransicao();
				
			} else if (tarefa.includes('aguardando final do sobrestamento')) {
				await clicarBotao('button', 'encerrar');
				await clicarBotao('button', 'Sim', true);
				await esperarTransicao();
				
			} else if (tarefa.includes('iniciar Execucao')) {
				await clicarBotao('button', 'iniciar', true);
				await esperarTransicao();
				
			} else if (tarefa.includes('iniciar liquidacao')) {
				await clicarBotao('button', 'iniciar', true);
				await esperarTransicao();
				
			} else if (tarefa.includes('remeter')) {
				let aviso = await esperarElemento('pje-validacao-remessa mat-card');
				await esperarDesaparecer(aviso, 500);
				await clicarBotao('button[aria-label="Cancelar Remessa"]', null, true);
				await esperarTransicao();
				
			} else if (tarefa.includes('prazos vencidos - secretaria')) {
				await clicarBotao('button', 'analise de secretaria', true);
				await esperarTransicao();
				
			} else if (tarefa.includes('prazos vencidos - gabinete')) {
				await clicarBotao('button', 'analise de gabinete', true);
				await esperarTransicao();
				
			} else if (tarefa.includes('analise de recurso interno')) {
				await clicarBotao('button', 'analise de gabinete', true);
				await esperarTransicao();
				
			} else { //movimentar para o Análise
				
				if (aa.destino.includes('?')) { aa.destino = aa.destino.replace('?','') } //a tarefa de origem é alocada como destino
				await clicarBotao('button', 'analise', true);
				await esperarTransicao();
			}
			
			resolve(true);
		});
	}
	
	async function esperarTransicao(esperar=true, tempo=5000) {
		return new Promise(async resolve => {
			if (!esperar) { return resolve(true) }
			let check;
			check = setInterval(function() {
				if (document.location.href.includes('/transicao')) {
					clearInterval(check);
					console.log('maisPje : esperarTransicao() : transição finalizada!');
					resolve(true);
				}				
			}, 10);
			//ATENÇÃO!! A troca de órgão Julgador dispara uma requisição [POST - pjedes.trt12.jus.br/pje-comum-api/api/processos/id/????/bloqueiotarefas] que interrompe o Javascript			
			setTimeout(async function() {
				clearInterval(check);
				console.log('maisPje : esperarTransicao() : tempo esgotado!');
				let num = await extrairNumeroProcesso(document.querySelector('pje-cabecalho-processo').innerText);
				let guardarStorage = browser.storage.local.set({'erros': num + ' : '});
				Promise.all([guardarStorage]).then(values => {
					fundo(true, '!!!!!!!!!!!!!!ERRO!!!!!!!!!!!!!!');
					resolve(true);
				});
			}, tempo); //aguarda 5 segundos
		});
	}
	
	async function obter_tarefa() {
		return new Promise(async resolve => {
			let url = document.location.href;
			let codigo_tarefa = url.substr(url.search('/tarefa/') + 8);
			// console.debug(codigo_tarefa);
			codigo_tarefa = extrairNumeros(codigo_tarefa);
			// console.debug(codigo_tarefa);
			// extrair numeros apenas
			// codigo_tarefa = codigo_tarefa.replace('/transicao','');
			let nome_tarefa = await obterNomeTarefaViaApi(codigo_tarefa);
			// console.debug(nome_tarefa);
			if (!nome_tarefa) {
				if (document.location.href.includes('nomeTarefa=Arquivo+provis')) {
					return resolve('Arquivo provisório');
				} else if (document.location.href.includes('nomeTarefa=Arquivo+definitivo')) {
					return resolve('Arquivo definitivo');
				} else {
					console.log('maisPje: Erro tarefa.. PJe antigo!!!');
					return resolve('Análise');
				}
			} else {
				return resolve(nome_tarefa);
			}
		});
	}
	
	async function chip_responsável() {
		return new Promise(async resolve => {
			console.log("aa.chip: " + aa.chip);
			if (aa.chip != "") {
				
				if (aa.chip.includes('[concluir]')) {
					aa.chip = aa.chip.replace('[concluir]','');
					let tabelaChips = await esperarElemento('pje-lista-etiquetas');
					if (!tabelaChips) { return }
					
					if (document.querySelector('pje-lista-etiquetas button[aria-label="Expandir Chips"]')) {
						await clicarBotao('pje-lista-etiquetas button[aria-label="Expandir Chips"]');
					}
					
					let listaDeChipsNoProcesso = await esperarColecao('pje-lista-etiquetas mat-chip');
					if (!listaDeChipsNoProcesso) { return }
					let chips = aa.chip.split(',');
					
					for (const [pos, chip] of chips.entries()) {
						let ancora = await esperarElemento('pje-lista-etiquetas mat-chip button[aria-label*="' + chip + '"]', null, 500);
						if (ancora) {
							await clicarBotao('pje-lista-etiquetas mat-chip button[aria-label*="' + chip + '"]');
							let aviso = await esperarElemento('mat-dialog-container','Deseja realmente excluir esse chip do processo?');
							if (aviso) { await clicarBotao(aviso.querySelector('button')) }
						}
					}
					
				} else {
				
					await clicarBotao('button[aria-label="Incluir Chip Amarelo"]');
					let ancora = await esperarElemento('table[name="Etiquetas"] tr', aa.chip);
					if (ancora) {
						await clicarBotao(ancora.querySelector('input[aria-label="Marcar chip"]'));
						await clicarBotao('pje-inclui-etiquetas-dialogo button', 'Salvar');
					} else {
						await clicarBotao('pje-inclui-etiquetas-dialogo button', 'Cancelar');
					}
				}
				
			}
			
			//responsavel
			console.log("aa.responsavel: " + aa.responsavel);
			if (aa.responsavel.length > 0) {
				await acaoBotaoDetalhes("Abrir o GIGS",null,false);				
				await escolherOpcaoTeste('input[aria-label*="Responsável"]', aa.responsavel.toUpperCase(), false);
				await sleep(1000);
				await clicarBotao('div[class*="cdk-overlay-backdrop"'); //fecha o gigs
				let span_responsavel = await esperarElemento('span[class*="nome-responsavel"');
				span_responsavel.innerText = aa.responsavel.toUpperCase();
			}
			
			return resolve(true);
		});
	}
	
	async function ultimoLance() {
		return new Promise(async resolve => {
			console.debug('ultimoLance: ' + aa.destino);
			let padrao = /\[(.*?)\]/gm;
			let nmBT = ''
			if (padrao.test(aa.destino)) {
				nmBT = aa.destino.match(new RegExp(/\[(.*?)\]/gm)).join();
				nmBT = nmBT.replace('[','');
				nmBT = nmBT.replace(']','');
				return resolve(nmBT);
			} else {
				return resolve('');
			}
		});
	}

	async function preencherFormularioRedistribuicao(opcoes) {
		return new Promise(async resolve => {
			await esperarElemento('mat-select[aria-label="Motivo de redistribuicao"]')
			var formulario = await esperarElemento('#redistribuicaoPrincipal')
			console.info('formulario', formulario)
			
			// Verifica se o formulário foi encontrado
			if (formulario) {    
				for (let index = 0; index < opcoes.length; index++) {
					//TODO: alguns modais abrem de acordo com as opcoes escolhidas, mas nao vi como fazer de maneira opcional
					// await clicarBotao('pje-modal-redistribuir-processo button', 'Fechar');
					// sempre busca novamente os itens, pois o formulario de redistribuicao eh dinamico, novos campos vao aparecendo a medida que se preenche.
					const elementos = getMatFormFieldsDoFormulario(formulario);
					if (index <= elementos.length) {
						const elemento = elementos[index]
						if (!elemento.disabled && !elemento.readOnly) {
							await preencherCampoPeloTipo(elemento, opcoes[index]);
							await sleep(preferencias.maisPje_velocidade_interacao)
						}
					} else {
						//TODO: houve erro de configuracao (ou o campo esperado nao foi carregado). como tratar?
					}
				}
			}
			return resolve(true);
		});
	}
	
	async function preencherFormularioSobrestamento() {
		return new Promise(async resolve => {
			let tarefa = await obter_tarefa();
			let tempoDaTransicao = preferencias.maisPje_velocidade_interacao + 1000;
			const comandos = await extrairComandosComuns(aa.ultimoLance);
			let comandoEspecial = await extrairComandoEspecial(aa.ultimoLance);
			
			console.debug('tarefa: ' + tarefa);
			console.debug('comandos: ' + comandos);
			console.debug('comandoEspecial: ' + comandoEspecial);
			
			if (tarefa.includes('Escolher tipo')) {
				console.log('preencherFormularioSobrestamento > Escolher tipo');
				let posicaoDoComplemento = 0;
				for (const [pos,comando] of comandos.entries()) {
					console.log('pos,comando: ' + pos + ',' + comando)
					
					if (!comando.includes('corrigir data') && !comando.includes('AtualizarDataPerguntar')  && !comando.includes('Atualizar1ano')  && !comando.includes('Atualizar2anos')  && !comando.includes('AtualizarDataEspecifica')) {
						let complementos = document.querySelectorAll('pje-complemento'); //opçoes de escolha após selecionar o movimento
						console.log('complementos ' + complementos.length)
						if (complementos.length > 0) {
							complementos[posicaoDoComplemento].scrollIntoView({behavior: 'auto',block: 'center',inline: 'center'});
							let elementoLista = complementos[posicaoDoComplemento].querySelectorAll('mat-select, textarea, input'); //tipos de elementos-filho que interessam para a interação..
							let elemento = elementoLista[0] ? elementoLista[0] : elementoLista;
							console.log('elemento: ' + elemento);
							posicaoDoComplemento++;												
							if (!elemento.disabled && !elemento.readOnly) {
								let comandoPerguntar = await extrairPerguntar(comando);
								console.log('comandoPerguntar: ' + comandoPerguntar);
								let c = (comandoPerguntar) ? comandoPerguntar : comando;
								await preencherCampoPeloTipo2(elemento, c);
							}						
						} else {
							await clicarBotao('label', comando);
						}
						await sleep(tempoDaTransicao);
					}
					
				}
				
				await sleep(tempoDaTransicao);
				await clicarBotao('button[aria-label*="Gravar os movimentos"]', false, true);
				await sleep(tempoDaTransicao);
				let definirPrazoSobrestamento = await esperarElemento('pje-motivos-sobrestamento button[aria-label="Definir prazo para este motivo de sobrestamento"]');
				
				if (comandoEspecial == 'Atualizar1ano') { //comando especial para quando o processo já estiver na janela Aguardando prazo sobrestamento
				
					await clicarBotao(definirPrazoSobrestamento);
					let ancora = await esperarElemento('pje-dialog-prazo-sobrestamento');
					// await sleep(tempoDaTransicao);
					await preencherInput('pje-dialog-prazo-sobrestamento input[data-placeholder*="Prazo em meses"]', '24');
					await sleep(tempoDaTransicao);
					let erro = await clicarBotao('pje-dialog-prazo-sobrestamento button','Prosseguir', true);
					await sleep(tempoDaTransicao);
					
					if (!erro) { //não foi possível cadastrar
						let numeroProcesso = await esperarElemento(seletorDetalhesNumeroProcesso);
						preferencias.erros += numeroProcesso.innerText + ';';
						let guardarErros = browser.storage.local.set({'erros': preferencias.erros}); //uso para levar o código do assunto da AA de Retificar Autuação
						Promise.all([guardarErros]).then(async values => {
							console.debug('maisPje: erro ao atualizar o prazo de sobrestamento do processo ' + numeroProcesso.innerText);
						});
					}

				} else if (comandoEspecial == 'Atualizar2anos') { //comando especial para quando o processo já estiver na janela Aguardando prazo sobrestamento
					
					await clicarBotao(definirPrazoSobrestamento);
					let ancora = await esperarElemento('pje-dialog-prazo-sobrestamento');
					// await sleep(tempoDaTransicao);
					await preencherInput('pje-dialog-prazo-sobrestamento input[data-placeholder*="Prazo em meses"]', '24');
					await sleep(tempoDaTransicao);
					let erro = await clicarBotao('pje-dialog-prazo-sobrestamento button','Prosseguir', true);
					await sleep(tempoDaTransicao);
					
					if (!erro) { //não foi possível cadastrar
						let numeroProcesso = await esperarElemento(seletorDetalhesNumeroProcesso);
						preferencias.erros += numeroProcesso.innerText + ';';
						let guardarErros = browser.storage.local.set({'erros': preferencias.erros}); //uso para levar o código do assunto da AA de Retificar Autuação
						Promise.all([guardarErros]).then(async values => {
							console.debug('maisPje: erro ao atualizar o prazo de sobrestamento do processo ' + numeroProcesso.innerText);
						});
					}
				
				} else if (comandoEspecial == 'AtualizarDataEspecifica') { //comando especial para quando o processo já estiver na janela Aguardando prazo sobrestamento
					
					await clicarBotao(definirPrazoSobrestamento);
					let ancora = await esperarElemento('pje-dialog-prazo-sobrestamento');
					// await sleep(tempoDaTransicao);
					let novadata = await extrairData(aa.ultimoLance);
					if (novadata.length <= 2) { //é em meses
						await preencherInput('pje-dialog-prazo-sobrestamento input[data-placeholder*="Prazo em meses"]', novadata+'');
					} else {
						await preencherInput('pje-dialog-prazo-sobrestamento input[data-placeholder*="Data limite"]', novadata+'');
					}					
					await sleep(tempoDaTransicao);
					let erro = await clicarBotao('pje-dialog-prazo-sobrestamento button','Prosseguir', true);
					await sleep(tempoDaTransicao);
					
					if (!erro) { //não foi possível cadastrar
						let numeroProcesso = await esperarElemento(seletorDetalhesNumeroProcesso);
						preferencias.erros += numeroProcesso.innerText + ';';
						let guardarErros = browser.storage.local.set({'erros': preferencias.erros}); //uso para levar o código do assunto da AA de Retificar Autuação
						Promise.all([guardarErros]).then(async values => {
							console.debug('maisPje: erro ao atualizar o prazo de sobrestamento do processo ' + numeroProcesso.innerText);
						});
					}
					
				} else if (comandoEspecial == 'AtualizarDataPerguntar') { //comando especial para quando o processo já estiver na janela Aguardando prazo sobrestamento
					
					await clicarBotao(definirPrazoSobrestamento);
					let ancora = await esperarElemento('pje-dialog-prazo-sobrestamento');
					// await sleep(tempoDaTransicao);
					let novadata = await criarCaixaDePergunta('text','Digite a nova Data:','');
					if (novadata.length <= 2) { //é em meses
						novadata = ('0' + novadata).slice(-2);
						await preencherInput('pje-dialog-prazo-sobrestamento input[data-placeholder*="Prazo em meses"]', novadata+'');
					} else {
						await preencherInput('pje-dialog-prazo-sobrestamento input[data-placeholder*="Data limite"]', novadata+'');
					}
					
					await sleep(tempoDaTransicao);
					let erro = await clicarBotao('pje-dialog-prazo-sobrestamento button','Prosseguir', true);
					await sleep(tempoDaTransicao);
					
					if (!erro) { //não foi possível cadastrar
						let numeroProcesso = await esperarElemento(seletorDetalhesNumeroProcesso);
						preferencias.erros += numeroProcesso.innerText + ';';
						let guardarErros = browser.storage.local.set({'erros': preferencias.erros}); //uso para levar o código do assunto da AA de Retificar Autuação
						Promise.all([guardarErros]).then(async values => {
							console.debug('maisPje: erro ao atualizar o prazo de sobrestamento do processo ' + numeroProcesso.innerText);
						});
					}
					
				}

				return resolve(true);
				
			} else if (tarefa.includes('Aguardando final')) {
				console.log('preencherFormularioSobrestamento > Aguardando final')
				let definirPrazoSobrestamento = await esperarElemento('pje-motivos-sobrestamento button[aria-label="Definir prazo para este motivo de sobrestamento"]');
				
				if (comandoEspecial == 'Atualizar1ano') { //comando especial para quando o processo já estiver na janela Aguardando prazo sobrestamento
				
					await clicarBotao(definirPrazoSobrestamento);
					let ancora = await esperarElemento('pje-dialog-prazo-sobrestamento');
					// await sleep(tempoDaTransicao);
					await preencherInput('pje-dialog-prazo-sobrestamento input[data-placeholder*="Prazo em meses"]', '12');
					await sleep(tempoDaTransicao);
					let erro = await clicarBotao('pje-dialog-prazo-sobrestamento button','Prosseguir', true);
					await sleep(tempoDaTransicao);
					
					if (!erro) { //não foi possível cadastrar
						let numeroProcesso = await esperarElemento(seletorDetalhesNumeroProcesso);
						preferencias.erros += numeroProcesso.innerText + ';';
						let guardarErros = browser.storage.local.set({'erros': preferencias.erros}); //uso para levar o código do assunto da AA de Retificar Autuação
						Promise.all([guardarErros]).then(async values => {
							console.debug('maisPje: erro ao atualizar o prazo de sobrestamento do processo ' + numeroProcesso.innerText);
						});
					}
				} else if (comandoEspecial == 'Atualizar2anos') { //comando especial para quando o processo já estiver na janela Aguardando prazo sobrestamento
					
					await clicarBotao(definirPrazoSobrestamento);
					let ancora = await esperarElemento('pje-dialog-prazo-sobrestamento');
					// await sleep(tempoDaTransicao);
					await preencherInput('pje-dialog-prazo-sobrestamento input[data-placeholder*="Prazo em meses"]', '24');
					await sleep(tempoDaTransicao);
					let erro = await clicarBotao('pje-dialog-prazo-sobrestamento button','Prosseguir', true);
					await sleep(tempoDaTransicao);
					
					if (!erro) { //não foi possível cadastrar
						let numeroProcesso = await esperarElemento(seletorDetalhesNumeroProcesso);
						preferencias.erros += numeroProcesso.innerText + ';';
						let guardarErros = browser.storage.local.set({'erros': preferencias.erros}); //uso para levar o código do assunto da AA de Retificar Autuação
						Promise.all([guardarErros]).then(async values => {
							console.debug('maisPje: erro ao atualizar o prazo de sobrestamento do processo ' + numeroProcesso.innerText);
						});
					}
				
				} else if (comandoEspecial == 'AtualizarDataEspecifica') { //comando especial para quando o processo já estiver na janela Aguardando prazo sobrestamento
					
					await clicarBotao(definirPrazoSobrestamento);
					let ancora = await esperarElemento('pje-dialog-prazo-sobrestamento');
					// await sleep(tempoDaTransicao);
					let novadata = await extrairData(aa.ultimoLance);
					console.log(novadata + ' - ' + novadata.length)
					if (novadata.length < 3) { //é em meses
						await preencherInput('pje-dialog-prazo-sobrestamento input[data-placeholder*="Prazo em meses"]', novadata+'');
					} else {
						await preencherInput('pje-dialog-prazo-sobrestamento input[data-placeholder*="Data limite"]', novadata+'');
					}					
					await sleep(tempoDaTransicao);
					let erro = await clicarBotao('pje-dialog-prazo-sobrestamento button','Prosseguir', true);
					await sleep(tempoDaTransicao);
					
					if (!erro) { //não foi possível cadastrar
						let numeroProcesso = await esperarElemento(seletorDetalhesNumeroProcesso);
						preferencias.erros += numeroProcesso.innerText + ';';
						let guardarErros = browser.storage.local.set({'erros': preferencias.erros}); //uso para levar o código do assunto da AA de Retificar Autuação
						Promise.all([guardarErros]).then(async values => {
							console.debug('maisPje: erro ao atualizar o prazo de sobrestamento do processo ' + numeroProcesso.innerText);
						});
					}
					
				} else if (comandoEspecial == 'AtualizarDataPerguntar') { //comando especial para quando o processo já estiver na janela Aguardando prazo sobrestamento
					
					await clicarBotao(definirPrazoSobrestamento);
					let ancora = await esperarElemento('pje-dialog-prazo-sobrestamento');
					// await sleep(tempoDaTransicao);
					let novadata = await criarCaixaDePergunta('text','Digite a nova Data:','');
					if (novadata.length <= 2) { //é em meses
						novadata = ('0' + novadata).slice(-2);
						await preencherInput('pje-dialog-prazo-sobrestamento input[data-placeholder*="Prazo em meses"]', novadata+'');
					} else {
						await preencherInput('pje-dialog-prazo-sobrestamento input[data-placeholder*="Data limite"]', novadata+'');
					}
					
					await sleep(tempoDaTransicao);
					let erro = await clicarBotao('pje-dialog-prazo-sobrestamento button','Prosseguir', true);
					await sleep(tempoDaTransicao);
					
					if (!erro) { //não foi possível cadastrar
						let numeroProcesso = await esperarElemento(seletorDetalhesNumeroProcesso);
						preferencias.erros += numeroProcesso.innerText + ';';
						let guardarErros = browser.storage.local.set({'erros': preferencias.erros}); //uso para levar o código do assunto da AA de Retificar Autuação
						Promise.all([guardarErros]).then(async values => {
							console.debug('maisPje: erro ao atualizar o prazo de sobrestamento do processo ' + numeroProcesso.innerText);
						});
					}
				}
				
				//verifica se existe algum lançamento ativo
				let registro = await esperarElemento('tr[class="mensagem-vazio"]',null,1000);
				if (registro) {
					// console.debug('está vazio') ... se está vazio (bug) exibe mensagem para o usuário corrigir manualmente
					let bt = await esperarElemento('button[aria-label="Incluir motivo de sobrestamento"]');
					if (bt.hasAttribute('disabled')) {
						await criarCaixaDeAlerta("Erro","Considerando que não existe movimento lançado, ajuste este processo manualmente.",3); 
					}
				}
				return resolve(true);
			}
			
			async function preencherCampoPeloTipo2(campo, valor) {
				return new Promise(async resolve => {
					console.info(campo, valor)
					var tagName = campo.nodeName.toLowerCase();

					switch (tagName) {
						case 'input':
							await preencherInput(campo, valor)
							break;
						case 'mat-select':
							await clicarBotao(campo);
							const optionSelect = Array.from(document.querySelectorAll('mat-option, option'))
								.find(el => removeAcento(el.innerText.trim().toLowerCase()).includes(removeAcento(valor.toLowerCase())));
							console.log('|___' + optionSelect.innerText.trim().toLowerCase())
							await clicarBotao(optionSelect);
							break;
						case 'mat-radio-group':
							//TODO: isso eh uma simplificacao do metodo querySelectorByText. Falar com Fernando sobre criar um novo parametro com o campo a partir do qual se quer procurar (valor default seria document, para manter compatibilidade)
							const radioButton = Array.from(campo.querySelectorAll('mat-radio-button label'))
								.find(el => removeAcento(el.textContent.trim().toLowerCase()).includes(removeAcento(valor.toLowerCase())));
							await clicarBotao(radioButton, valor); 
							break;
						case 'textarea':
							await preencherTextArea(campo, valor)
							break;
						default:
					}
					return resolve(true);
				});
			}
			
		});
	}
	
	async function clicarUltimoLance(tipo='',opcao=false) {		
		return new Promise(async resolve => {
			console.debug("clicarUltimoLance: " + aa.ultimoLance);
			console.debug("Destino: " + tipo);
			if (tipo.includes('sobrestamento')) {
				
				await esperarDesaparecer('PJE-DIALOGO-STATUS-PROGRESSO');
				await preencherFormularioSobrestamento();
				fundo(false);
				return resolve(true);
				
			} else if (tipo === 'redistribuir') {
				//Redistribuir[Criação de unidade judiciária,Por competência exclusiva,São José,2ª VARA DO TRABALHO SÃO JOSÉ], onde as opções são separadas por vírgula na sequencia em que devem ser preenchidas
				const comandos = await extrairComandosComuns(aa.ultimoLance);
				preencherFormularioRedistribuicao(comandos)
				
				await clicarBotao('pje-redistribuicao button','Redistribuir',true);
				let aviso = await esperarElemento('pje-modal-redistribuir-processo', 'Confirmação redistribuição');
				console.log(aviso)
				if (aviso) {
					return resolve(true);
				}
				
				await esperarElemento('button','Fechar',1000)
				
				
				let numeroProcesso = await esperarElemento(seletorDetalhesNumeroProcesso);
				preferencias.erros += numeroProcesso.innerText + ';';
				let guardarErros = browser.storage.local.set({'erros': preferencias.erros}); //uso para levar o código do assunto da AA de Retificar Autuação
				Promise.all([guardarErros]).then(async values => {
					console.debug('maisPje: erro ao redistribuir processo: ' + numeroProcesso.innerText);
					return resolve(true);
				});
				
				return resolve(true);
				
			} else if (aa.ultimoLance === 'Arquivo definitivo') {
				await clicarBotao('button', aa.ultimoLance);					
				await clicarBotao('pje-dialogo-assinatura button', 'Assinar', true);
				await esperarTransicao();
				return resolve(true);
			} else if (aa.ultimoLance.includes('Assinar')) {
				await clicarBotao('button', aa.ultimoLance);
				await esperarElemento('button[aria-label="Análise"]'); //esperar a transição já que a função "esperarTransicao()" não funciona nesta tarefa
				return resolve(true);
			} else if (aa.ultimoLance.includes('Enviar para assinatura') || aa.ultimoLance.includes('Cancelar conclusão')) {
				await sleep(1000);
				await clicarBotao('button', 'Salvar', true);
				await clicarBotao('button[aria-label="' + aa.ultimoLance + '"]');
				let questionamento = await esperarElemento('div[class="cdk-overlay-container"] mat-dialog-container','deseja continuar', 500);
				if (questionamento) { await clicarBotao('div[class="cdk-overlay-container"] mat-dialog-container button', 'Sim') }
				let confirmar = await esperarElemento('SIMPLE-SNACK-BAR','Minuta Salva');
				if (confirmar) { confirmar.querySelector('button').click() }
				await esperarElemento('h1[class="titulo-tarefa"]','Assinar'); //esperar a transição já que a função "esperarTransicao()" não funciona nesta tarefa
				return resolve(true);
			
			} else if (tipo.includes('assinar expedientes') && aa.ultimoLance.toLowerCase().includes('trocar signatário')) {
				
				let btRetornar = await esperarElemento('button', 'Retornar para editar expediente');
				if (btRetornar) {
					await clicarBotao('button', 'Retornar para editar expediente');
					await esperarElemento('h1[class="titulo-tarefa"]','Preparar expedientes e comunicações'); //esperar a transição já que a função "esperarTransicao()" não funciona nesta tarefa
				}
				
				await sleep(2000);
				let novoSignatario = aa.ultimoLance.replace('trocar signatário', '').trim();
				console.log('novoSignatario: ' + novoSignatario)
				await escolherOpcao('mat-select[placeholder="Pessoas que assinam"]', novoSignatario.toUpperCase(), 1);
				await sleep(preferencias.maisPje_velocidade_interacao);
				
				let erro = await clicarBotao('button', 'Salvar', true);
				await sleep(preferencias.maisPje_velocidade_interacao + 1000);
				console.log(erro)
				if (!erro) { //não foi possível cadastrar
					let numeroProcesso = await esperarElemento(seletorDetalhesNumeroProcesso);
					
					console.debug('maisPje: erro ao salvar o expediente com um novo signatario: ' + numeroProcesso.innerText);
					preferencias.erros += numeroProcesso.innerText + ';';
					return resolve(true);
				} else {				
					await clicarBotao('button', 'Enviar para assinatura');
					let btAssinatura = await esperarElemento('button[aria-label="Assinar selecionado(s)"]'); //esperar a transição já que a função "esperarTransicao()" não funciona nesta tarefa
					await clicarBotao(btAssinatura);
					await esperarElemento('button[aria-label="Análise"]'); //esperar a transição já que a função "esperarTransicao()" não funciona nesta tarefa
					return resolve(true);				
				}
				
			} else if (tipo.includes('analise de recurso para o tst') || tipo.includes('encaminhar ao')) {
				//ATENÇÃO!! A troca de órgão Julgador dispara uma requisição [POST - pjedes.trt12.jus.br/pje-comum-api/api/processos/id/????/bloqueiotarefas] que interrompe o Javascript
				//neste caso terei que passar o vinculo antes de acionar o clique derradeiro
				console.log("      |___ATENÇÃO! Haverá troca de Orgao Julgador...");
				console.log("          |___Próxima AA: " + aa.vinculo);
				let guardarStorage1 = browser.storage.local.set({'tempBt': ['vinculo', aa.vinculo]});
				Promise.all([guardarStorage1]).then(async values => {
					await clicarBotao('button', aa.ultimoLance);
					// window.close(); //não precisa, a janela fecha sozinha
				});
				
			} else {
				console.log('sem tarefa mapeada')
				await clicarBotao('button', aa.ultimoLance);
				await esperarTransicao();
				return resolve(true);
			}
		});
	}
	
	async function extrairNumeroProcesso(texto) {
		let padrao = /\d{7}\-\d{2}\.\d{4}\.\d{1}\.\d{2}\.\d{4}/g;
		let n = '';
		if (padrao.test(texto)) {
			n = texto.match(padrao).join();
			aa.ultimoLance = aa.ultimoLance.replace(n, '').trim();
		}	
		return n;
	}
	
	async function extrairData(texto) {
		let padrao1 = /(0?[1-9]|[12][0-9]|3[01])\/(0?[1-9]|1[012])*\/\d{4}/g;
		let padrao2 = /(\d{1,2})/g;
		let d = '';
		if (padrao1.test(texto)) {
			d = texto.match(padrao1).join();
			aa.ultimoLance = aa.ultimoLance.replace(d, '').trim();
		} else if (padrao2.test(texto)) {
			d = texto.match(padrao2).join();
			aa.ultimoLance = aa.ultimoLance.replace(d, '').trim();
		} 
		return d;
	}
	
	async function extrairPerguntar(texto) {
		let padrao = /(?:perguntar){1}/g;
		let resposta = "";
		
		if (padrao.test(texto)) {
			aa.ultimoLance = aa.ultimoLance.replace('perguntar', '').trim();
			resposta = await criarCaixaDePergunta('text','','');
		}
		
		return resposta;
	}
	
	async function extrairComandoEspecial(texto) {
		let padrao1 = /(?:Atualizar1ano){1}/g;
		let padrao2 = /(?:Atualizar2anos){1}/g;
		let padrao3 = /(?:AtualizarDataEspecifica){1}/g;
		let padrao4 = /(?:AtualizarDataPerguntar){1}/g;
		let padrao5 = /(?:corrigir data){1}/g;
		let resposta = "";

		if (padrao1.test(texto)) {
			aa.ultimoLance = aa.ultimoLance.replace('Atualizar1ano', '').trim();
			resposta = 'Atualizar1ano';
		}
		
		if (padrao2.test(texto)) {
			aa.ultimoLance = aa.ultimoLance.replace('Atualizar2anos', '').trim();
			resposta = 'Atualizar2anos';
		}
		
		if (padrao3.test(texto)) {
			aa.ultimoLance = aa.ultimoLance.replace('AtualizarDataEspecifica', '').trim();
			resposta = 'AtualizarDataEspecifica';
		}
		
		if (padrao4.test(texto)) {
			aa.ultimoLance = aa.ultimoLance.replace('AtualizarDataPerguntar', '').trim();
			resposta = 'AtualizarDataPerguntar';
		}

		if (padrao5.test(texto)) {
			aa.ultimoLance = aa.ultimoLance.replace('corrigir data', '').trim();
			resposta = 'AtualizarDataPerguntar';
		}
		
		return resposta;
	}
	
	async function extrairComandosComuns(texto) {		
		return texto.split(',');
	}
	
	async function monitorFim(param) {
		window.opener.focus(''); //devolve o foco para a janela detalhes

		console.log('monitorFim(' + param + ')');

		if (aa.ultimoLance.includes('parar')) {

			console.log('maisPJe: usuário quis interromper o fechamento da janela..')
			window.addEventListener("beforeunload", function (e) {			
								
				console.log("JANELA TAREFA fechou...");
				console.log("     |___avisa a janela DETALHES para executar a AA: " + param);
				browser.runtime.sendMessage({tipo: 'storage_vinculo', valor: param});

			});

		} else if (param && param != "nenhum") { //se tem vínculo continua
			
			browser.runtime.sendMessage({tipo: 'storage_vinculo', valor: param});
			setTimeout(function(){window.close()}, 1000);			

		} else {

			if (preferencias.AALote.length > 0) { //vem do AA em Lote
				let guardarStorage = browser.storage.local.set({'AALote': ''});
				Promise.all([guardarStorage]).then(values => { window.close() });
			}

			

		}				
		
	}
}

//FUNÇÃO RESPONSÁVEL PELAS AÇÕES DOS BOTÕES AÇÕES_AUTOMATIZADAS_CHECKLIST
async function acao_bt_aaChecklist(id) {
	fundo(true);
	
	let aa;	
	if (typeof id === 'object') {
		await sleep(1000);
		aa = id;
	} else {
		aa = preferencias.aaChecklist[id];
	}
	
	
	exibir_mensagem("Executando a Ação Automatizada " + aa.nm_botao + "\nPróximo vínculo: " + (!preferencias.tempAAEspecial ? aa.vinculo : preferencias.tempAAEspecial))
	
	console.log("***acao_bt_aaChecklist***");
	
	//INICIO DA AA
	let nomeExecutados = await recuperaExecutados();
	
	if (nomeExecutados.length < 1) { //tentar mais uma vez depois de dois segundo
		await sleep(2000);
		nomeExecutados = await recuperaExecutados();
	}
	
	//CASO NÃO EXISTA EXECUTADO LANÇADO NO Checklist
	if (nomeExecutados.length < 1) {
		await criarCaixaDeAlerta(titulo='ALERTA', mensagem='Não existe Executado cadastrado no Checklist.\n\nEste é um requisito indispensável para o lançamento deste tipo de Ação Automatizada.', 5);
		fundo(false);
		monitorFim(aa.vinculo);
		return; 
	}
	
	//ELABORA A LISTA DE EXECUTADOS PARA O USUARIO ESCOLHER
	let executado = '1';
	if (nomeExecutados.length > 1) {
		let msg = "";
		for (let i = 0; i < nomeExecutados.length; i++) {
			msg = msg + (i + 1) + " - " + nomeExecutados[i] + "\n";
		}
		msg = (0) + " - Todos\n" + msg + "\n";
		msg = "Escolha o executado da ordem (Digite o número correspondente):|\nPara escolher mais de um executado, separe-os com vírgula. Por exemplo: 1,2|\n" + msg;
		// executado = prompt(msg,'');
		executado = await criarCaixaDePergunta('text', msg, '');
	}
	
	//se cancelado
	if (!executado) {
		fundo(false);
		monitorFim(aa.vinculo);
		return; 
	}
	
	let executadosEscolhidos = (executado.length > 1) ? executado.split(',') : executado;
	
	//se 1
	if (executadosEscolhidos.length == 1) {
		let posExecutado = parseInt(executadosEscolhidos[0])-1;
		//todos
		if (posExecutado == -1) {
			for (const [pos] of nomeExecutados.entries()) {
				await acao(pos);
			}
			fundo(false)
			monitorFim(aa.vinculo);
			return;
		} else {
			await acao(parseInt(executadosEscolhidos[0])-1);
			fundo(false)
			monitorFim(aa.vinculo);
			return;
		}
	
	//se 1,2
	} else {
		for (const [pos, item] of executadosEscolhidos.entries()) {
			console.log(item);
			await acao(parseInt(item)-1);
		}
		fundo(false)
		monitorFim(aa.vinculo);
		return;
	}
	
	async function acao(pos) {
		return new Promise(async resolve => {
			await sleep(preferencias.maisPje_velocidade_interacao);
			console.log(pos + "-" + nomeExecutados[pos] + ": " + preferencias.maisPje_velocidade_interacao);
			let colecaoNovaAtividade = await esperarColecao('div[id="grupo-executados"] button');
			clicarBotao(colecaoNovaAtividade[pos]); //Nova Atividade
			
			await sleep(500);
			await escolherOpcaoGIGS('mat-select[placeholder="Tipo"]', aa.tipo+'[exato]');
			
			// let opcoes = await escolherOpcao('mat-select[placeholder="Tipo"]', aa.tipo, 15);
			// if (!opcoes) { //se não carregar as opcoes, esperar dois segundos e tentar novamente
				// await sleep(2000); 
				// opcoes = await escolherOpcao('mat-select[placeholder="Tipo"]', aa.tipo, 15);
			// }
			// await escolherOpcaoTeste('mat-select[placeholder="Tipo"]', aa.tipo);
			
			let aaObservacaotemporario = aa.observacao;
			let inputData = await getCorrigirData(aaObservacaotemporario);
			if (inputData != "") {
				await preencherInput('input[data-placeholder="Data Prazo"]', inputData); //inserir data
				aaObservacaotemporario = aaObservacaotemporario.replace('corrigir data', '');
			}
			
			let observacao = await getObservacao(aaObservacaotemporario);
			if (observacao != "") {
				await preencherTextArea('textarea[data-placeholder="Observação"]', observacao); //observacao
			}
			let estado = await getStatus(aa.estado); 
			await clicarBotao('label', estado); //status
			if (aa.alerta.toLowerCase() === "sim") {
				let alerta = await esperarElemento('mat-checkbox[formcontrolname="alerta"]');
				await clicarBotao(alerta.firstElementChild);
			}
			await clicarBotao('button[aria-label="Salva as alterações"]');
			await sleep(500);
			resolve(true)
		});
	}
	
	function monitorFim(param) {	

		console.log("          |___monitor Fim: " + param);

		if (param && param != "nenhum") { //se tem vínculo continua
			
			browser.runtime.sendMessage({tipo: 'storage_vinculo', valor: param});

		} else {

			if (preferencias.AALote.length > 0) { //vem do AA em Lote
				let guardarStorage = browser.storage.local.set({'AALote': ''});
				Promise.all([guardarStorage]).then(values => { window.close() });
			}
		}

	}
	
	function recuperaExecutados() {
		return new Promise(resolve => {
			let executados = [];
			let el = document.querySelectorAll('span[class="font-label-executado"]');
			if (!el) {
				return resolve(null);
			}
			let map = [].map.call(
				el, 
				function(elemento) {
					let nome = elemento.innerText;
					nome = nome.replace(new RegExp('Executado:', 'g'), '');
					executados.push(nome.trim());
				}
			);
			resolve(executados);
		});
	}
	
	async function getStatus(estado) {
		return new Promise(async resolve => {
			if (estado != "") {
				estado = removeAcento(estado.toLowerCase());
				estado = estado[0].toUpperCase() + estado.substring(1); //deixa apenas a primeira letra maiuscula
				if (estado === "Perguntar") {
					let msg = "";
					msg = "Escolha o resultado da ordem (Digite o número correspondente): \n\n" + msg;
					msg = msg + "1 - Nenhum\n2 - Negativo\n3 - Parcial\n4 - Positivo\n";
					// estado = prompt(msg,'');
					estado = await criarCaixaDePergunta('text', msg, '');
					
					switch (estado) {
						case '1':
							resolve("Nenhum");
							break
						case '2':
							resolve("Negativo");
							break
						case '3':
							resolve("Parcial");
							break
						case '4':
							resolve("Positivo");
							break
						default:
							resolve("Nenhum");
					}
				} else {
					resolve(estado);
				}
			} else {
				resolve("Nenhum");
			}
		});
	}
	
	async function getObservacao(observacao) {
		return new Promise(async resolve => {
			if (observacao != "") {
				if (observacao.includes("perguntar")) {
					let msg = "";
					let txt = observacao;
					txt = txt.replace('perguntar','');
					msg = "Observação:" + msg;
					
					// observacao = prompt(msg,txt);
					observacao = await criarCaixaDePergunta('textarea', 'Observação:\n', txt);
					resolve(observacao);
				} else {
					resolve(observacao);
				}
			} else {
				resolve("");
			}
		});
	}
	
	async function getCorrigirData(texto) {
		return new Promise(async resolve => {
			if (texto != "") {
				if (texto.includes("corrigir data")) {
					let msg = "";
					msg = "Corrigir Data:" + msg;
					// texto = prompt(msg,'');
					texto = await criarCaixaDePergunta('text', msg, '');
					resolve( !texto ? new Date().toLocaleDateString() : texto );
				} else {
					resolve(new Date().toLocaleDateString());
				}
			} else {
				resolve(new Date().toLocaleDateString());
			}
		});
	}
	
	async function escolherOpcaoGIGS(seletor, valor, possuiBarraProgresso) {
		return new Promise(async resolve => {
			//NOVOS TESTES PARA QUE A FUNÇÃO FUNCIONE EM ABAS(GUIAS) DESATIVADAS
			await sleep(preferencias.maisPje_velocidade_interacao);
			if (seletor instanceof HTMLElement) {
			} else {
				seletor = await esperarElemento(seletor);
			}
			
			seletor.parentElement.parentElement.focus();
			seletor.parentElement.parentElement.click();			
			
			//teste1 : o carregamento muito rápido da página por vezes não permite ao menu de opções abrir para selecionar a opção desejada
			let teste = await esperarColecao('mat-option[role="option"], option', 5, 1000);			
			if (!teste) {
				seletor.parentElement.parentElement.focus();
				seletor.parentElement.parentElement.click();
				//teste2
				teste = await esperarColecao('mat-option[role="option"], option', 5, 1000);			
				if (!teste) {
					seletor.parentElement.parentElement.focus();
					seletor.parentElement.parentElement.click();
					//teste3
					teste = await esperarColecao('mat-option[role="option"], option', 5, 1000);			
					if (!teste) {
						seletor.parentElement.parentElement.focus();
						seletor.parentElement.parentElement.click();
					}
				}
			}
			
			await clicarBotao('mat-option[role="option"], option', valor);
			
			if (possuiBarraProgresso) {
				await observar_mat_progress_bar();
			}
			return resolve(true);
			
		});

		async function observar_mat_progress_bar() {
			return new Promise(resolve => {
				let observer = new MutationObserver(function(mutationsDocumento) {
					mutationsDocumento.forEach(function(mutation) {
						if (!mutation.removedNodes[0]) { return }
						if (!mutation.removedNodes[0].tagName) { return }
						if (!mutation.removedNodes[0].tagName.includes("MAT-PROGRESS-BAR")) { return }
						resolve(true);
						observer.disconnect();
					});
				});
				let configDocumento = { childList: true, subtree:true }
				observer.observe(document.body, configDocumento);
			});
		}
	}
	
}

//FUNÇÃO RESPONSÁVEL PELA AÇÃO DE VÍNCULO DOS BOTÕES AÇÕES_AUTOMATIZADAS
async function acao_vinculo(v) {
	console.log('++++++++++++++++++++++++++++++');
	console.log('++++++++++++++++++++++++++++++');	
	console.debug("maisPJe: acao_vinculo(v): " + v);
	console.log('++++++++++++++++++++++++++++++');
	console.log('++++++++++++++++++++++++++++++');
	if (typeof(v) == 'undefined') {
		fundo(false);
		return;
	} else if (v == 'Fechar Pagina|Fechar Pagina') {
		fundo(false);
	} else {
		exibir_mensagem("Executando a Ação Automatizada " + v);
	}
	v = (typeof(v) == "undefined" || v == "undefined") ? "Nenhum" : v;
	v = (!v) ? "Nenhum" : v;
	
	let arr = v.split("|");
	
	if (arr[0] == 'Anexar') {
		await addBotaoTelaAnexar();
		await clicarBotao('button[name="' + arr[1] +'"]');
		document.querySelector('maisPjeContainerAA').remove(); //é o painel de botões.. sempre que clicar removê-lo
		
	} else if (arr[0] == 'Comunicação') {
		await addBotaoTelaComunicacoes();
		await clicarBotao('button[name="' + arr[1] +'"]');
		document.querySelector('maisPjeContainerAA').remove();
			
	} else if (arr[0] == 'AutoGigs') {
		await addBotaoAutoGigs();
		await clicarBotao('button[name="' + arr[1] +'"]');
		document.querySelector('maisPjeContainerAA').remove();
			
	} else if (arr[0] == 'Despacho') {
		await addBotaoDespacho();
		await clicarBotao('button[name="' + arr[1] +'"]');
		document.querySelector('maisPjeContainerAA').remove();
		
	} else if (arr[0] == 'Movimento') {
		await addBotaoMovimento();
		await clicarBotao('button[name="' + arr[1] +'"]');
		document.querySelector('maisPjeContainerAA').remove();
		
	} else if (arr[0] == 'Checklist') {
		let aaChecklist_temp = preferencias.aaChecklist;		
		if (aaChecklist_temp.length > 0) {
			for (let i = 0; i < aaChecklist_temp.length; i++) {
				if (aaChecklist_temp[i].nm_botao == arr[1]) {
					// await sleep(velocidade);
					await acao_bt_aaChecklist(i);
					break;
				}
			}
		}
		
	} else if (arr[0] == 'RetificarAutuação') {
		await addBotaoRetificarAutuacao();
		await clicarBotao('button[id="' + arr[1] + '"], button[name="' + arr[1] +'"]');
		document.querySelector('maisPjeContainerAA').remove();
		
	} else if (arr[0] == 'LançarMovimento') {
		await addBotaoLancarMovimentos();
		// await clicarBotao('button', arr[1]);
		await clicarBotao('button[id="' + arr[1] + '"], button[name="' + arr[1] +'"]');
		document.querySelector('maisPjeContainerAA').remove();
		
	} else if (arr[0] == 'Clicar em') {
		fundo(false);
		await acaoBotaoDetalhes(arr[1]);
		//AALOTE
		if (arr[1] == 'Reprocessar chips do processo') {
			let barraProgresso = await esperarElemento('pje-reprocessa-etiquetas-dialogo mat-progress-bar', null, 1000);
			if (barraProgresso) { 
				// console.log('-*-*-*-*-*-*-*-*-*-*-*-*-*-existe barra de progresso');
				await esperarDesaparecer(barraProgresso, 500) }
				
			let bt_salvar = await esperarElemento('pje-reprocessa-etiquetas-dialogo button', 'Salvar', 2000);
			if (bt_salvar) {
				// console.log('-*-*-*-*-*-*-*-*-*-*-*-*-*-existe bt salvar');
				await clicarBotao(bt_salvar, null, true);
				
			} else {
				// console.log('-*-*-*-*-*-*-*-*-*-*-*-*-*-NÃO existe bt salvar');
				await clicarBotao('div[class*="cdk-overlay-backdrop-showing"]');
				
			}
			
			if (preferencias.AALote != "") { browser.runtime.sendMessage({tipo: 'storage_limpar', valor: 'AALote'}) }
			
			
		} else if (arr[1] == 'Download do processo completo') {
			await esperarElemento('SIMPLE-SNACK-BAR', 'Download realizado com sucesso');
			await clicarBotao('SIMPLE-SNACK-BAR button');
			// await sleep(500);
			
			if (preferencias.AALote != "") { browser.runtime.sendMessage({tipo: 'storage_limpar', valor: 'AALote'}) }
		}		
		
	} else if (arr[0] == 'Atualizar Pagina') {
		if (preferencias.AALote != "") {  //Não atualiza a página se vier do AALote
			browser.runtime.sendMessage({tipo: 'storage_limpar', valor: 'AALote'}) 
		} else {
			console.log('**************************************************************************************************************');
			console.log('*********************************************ATUALIZANDO A PÁGINA*********************************************');
			console.log('**************************************************************************************************************');
			
			let cont = parseInt(preferencias.aaVariados[0].temporizador);
			if (cont <= 0) {				
				// browser.runtime.sendMessage({tipo: 'atualizarJanela'})
				window.location.reload();   //NÃO FUNCIONA DIREITO
			}
			
			let divIco = document.createElement('div');
			divIco.style = "position: absolute;left: 50vw;top: 50vh;width: 120px;height: 120px;display: flex;align-items: center; animation: pulse 1s infinite !important; border-radius: 100px; z-index: 999999;";
			divIco.id = "maisPje_icoAtualizarPagina";
			let ico1 = document.createElement('span');
			ico1.style = "position: absolute; width: 100%;height: 100%;background-color: #e9e8ea;z-index: 99998;border-radius: 100%;";
			let ico2 = document.createElement('span');
			ico2.id = "maisPje_icoAvisoAtualizarPagina"
			ico2.style = "position: absolute; width: 70%; height: 70%; background-color: black; z-index: 99998; border-radius: 100%; margin-left: 15%;color: #00c0fe;text-align: center;align-items: center;display: grid;font-size: 3em;font-weight: bold;font-family: 'Orbitron', sans-serif;";
			ico2.innerText = cont;
			divIco.appendChild(ico1);
			divIco.appendChild(ico2);
			document.body.appendChild(divIco);
			
			let check = setInterval(function() { 
				cont--;
				ico2.innerText = cont;
				if (cont <= 0) { 
					clearInterval(check);	
					// browser.runtime.sendMessage({tipo: 'atualizarJanela'})
					window.location.reload();   //NÃO FUNCIONA DIREITO
				}
			}, 1000);
		}
		
	} else if (arr[0] == 'Fechar Pagina') {
		if (preferencias.AALote != "") { 
			browser.runtime.sendMessage({tipo: 'storage_limpar', valor: 'AALote'}) 
		} else {
			let guardarStorage1 = browser.storage.local.set({'tempAR': 'F5'}); //F5 inibe a execução de algumas funções automaticamente
			let guardarStorage2 = browser.storage.local.set({'tempBt': []});
			let guardarStorage3 = browser.storage.local.set({'tempAAEspecial': []});
			Promise.all([guardarStorage1,guardarStorage2,guardarStorage3]).then(values => {
				
				let cont = parseInt(preferencias.aaVariados[1].temporizador);
				if (cont <= 0) { window.close() }
				
				let divIco = document.createElement('div');
				divIco.style = "position: absolute;left: 50vw;top: 50vh;width: 120px;height: 120px;display: flex;align-items: center; animation: pulse 1s infinite !important; border-radius: 100px; z-index: 999999;";
				divIco.id = "maisPje_icoFecharPagina";
				let ico1 = document.createElement('span');
				ico1.style = "position: absolute; width: 100%;height: 100%;background-color: #e9e8ea;z-index: 99998;border-radius: 100%;";
				let ico2 = document.createElement('span');
				ico2.id = "maisPje_icoAvisoFecharPagina"
				ico2.style = "position: absolute; width: 70%; height: 70%; background-color: black; z-index: 99998; border-radius: 100%; margin-left: 15%;color: #00c0fe;text-align: center;align-items: center;display: grid;font-size: 3em;font-weight: bold;font-family: 'Orbitron', sans-serif;";
				ico2.innerText = cont;
				
				browser.runtime.sendMessage({tipo: 'insertCSS', file: 'maisPje_icones.css'});
				let fundoBranco = document.createElement('div');
				fundoBranco.style = "width: 100%;height: 100%;position: absolute;top: 0;left: 0;background-color: white;z-index: 999998; opacity: 0; animation: esmaecer " + preferencias.aaVariados[1].temporizador + "s;";
				
				divIco.appendChild(ico1);
				divIco.appendChild(ico2);
				document.body.appendChild(divIco);
				document.body.appendChild(fundoBranco);
				
				let check = setInterval(function() { 
					cont--;
					ico2.innerText = cont;
					if (cont <= 0) { 
						clearInterval(check);
						window.close();
					}
				}, 1000);
				
			});
		}
	
	} else if (arr[0] == 'Variados') {
		
		if (arr[1] == 'Apreciar Peticoes') {
			console.log('maisPJe: Executando a Ação Automatizada Variados| Apreciar Petições pelo vínculo..' + preferencias.tempAAEspecial);
			exibir_mensagem("Executando a Ação Automatizada Variados| Apreciar Petições\nPróximo vínculo: " + preferencias.tempAAEspecial);
			await clicarBotao('button[aria-label="Apreciar todos."]',null, true);
			fundo(false);
			browser.runtime.sendMessage({tipo: 'storage_vinculo', valor: preferencias.tempAAEspecial});
		} else if (arr[1] == 'SISBAJUD:F2') {
			fundo(false);
			browser.runtime.sendMessage({tipo: 'storage_guardar', chave: 'tempAR', valor: 'F2'}); 			
		}

		//comando para prosseguir as AA em LOTE caso exista
		if (preferencias.AALote != "") { browser.runtime.sendMessage({tipo: 'storage_limpar', valor: 'AALote'}) }
		
	} else {
		console.debug('default');
		return;
	}
	
}

//FUNÇÃO RESPONSÁVEL POR ADICIONAR O BOTÃO INSERIR PGF NA TELA DE RETIFICAR AUTUAÇÃO
async function acao_bt_retificarAutuacao(id) {
	console.log("***acao_bt_retificarAutuacao***");
	
	switch (id[0]) {
		case 0:
			await acao1(); //UNIÃO COMO TERCEIRO INTERESSADO
			fundo(false);
			break;
		case 1:
			await acao4(); //JUÍZO 100% DIGITAL			
			fundo(false);
			await monitorFim();
			break;
		case 2:
			await acao5('autor', id[1]); //CADASTRAR ADVOGADO DO AUTOR
			fundo(false);
			break;
		case 3:
			await acao5('reu', id[1]); //CADASTRAR ADVOGADO DO REU
			fundo(false);
			break;
		case 4:
			await acao2(); //CADASTRAR LEILOEIRO
			fundo(false);
			break;
		case 5:
			await acao3(); //CADASTRAR PERITO
			fundo(false);
			break;
		case 6:
			await acao6(); //RECUPERAÇÃO JUDICIAL/FALÊNCIA
			fundo(false);
			await monitorFim();
			break;
		case 7:
			await acao7('autor', id[1]); //CADASTRAR PARTE: AUTOR
			fundo(false);
			break;
		case 8:
			await acao7('reu', id[1]); //CADASTRAR PARTE: REU
			fundo(false);
			break;
		case 9:
			await acao8(id[1]); //CADASTRAR ASSUNTO 12468
			fundo(false);
			await monitorFim();
			break;
		case 10:
			await acao7('terceiro', id[1]); //CADASTRAR TERCEIRO > TERCEIRO
			fundo(false);
			await monitorFim();
			break;
		case 11:
			await acao9(); //CADASTRAR TERCEIRO MPT
			fundo(false);
			await monitorFim();
			break;
		case 12:
			await acao10(); //PEDIDO DE TUTELA
			fundo(false);
			await monitorFim();
			break;
		case 13:
			await acao11(); //JUSTIÇA GRATUITA
			fundo(false);
			await monitorFim();
			window.close();			
			break;
		case 14:
			await acao5('terceiro', id[1]); //CADASTRAR ADVOGADO DO TERCEIRO INTERESSADO
			fundo(false);
			break;
		default:
			console.log('PADRAO')
			await clicarBotao('mat-step-header[aria-posinset="3"]'); //apenas leva às partes
			fundo(false);
	}
	
	async function acao1() {
		return new Promise(async resolve => {
			fundo(true);
			console.log("     |___acao1");
			await clicarBotao('mat-step-header[aria-posinset="3"]');
			let grid = await esperarElemento('pje-autuacao-grid-partes[titulogrid="Outros participantes"]');
			await clicarBotao(grid.querySelector('button[aria-label="Adicionar parte ao processo"]'));
			await escolherOpcao('mat-select[aria-label="Tipo de participação"]', 'TERCEIRO INTERESSADO', 5);
			await clicarBotao('div[role="tab"]','Pessoa jurídica de direito público');
			await sleep(500);
			await clicarBotao('label','Federal');
			await clicarBotao('label','Órgão');
			resolve(true);
			console.log("     |___fim acao1");
			// deixarei para o usuário escolher qual o tipo de União
			// afinal ela pode ter sido cadastrada de diferentes formas 
			// em outros regionais
		});
	}
	
	async function acao2() {
		return new Promise(async resolve => {
			fundo(true);
			console.log("     |___acao2");
			await clicarBotao('mat-step-header[aria-posinset="3"]');
			let grid = await esperarElemento('pje-autuacao-grid-partes[titulogrid="Outros participantes"]');
			await clicarBotao(grid.querySelector('button[aria-label="Adicionar parte ao processo"]'));
			await escolherOpcao('mat-select[aria-label="Tipo de participação"]', 'LEILOEIRO', 5);
			await clicarBotao('div[role="tab"]','Pessoa física');
			await sleep(500);
			let pergunta = 'Digite o NOME do leiloeiro:';
			let codigo_especialidade = '50103';
			let documento = await Promise.all([consultaPeritos(prompt(pergunta,''), codigo_especialidade)]).then(values => {
				return values[0];
			});
			await preencherInput('input[id="inputCPF"]', documento);
			await clicarBotao('button[aria-label="Pesquisar CPF"]', null, true); //***** demorando
			await clicarBotao('button[aria-label="Confirmar"]');
			let erro = await clicarBotao('button','Inserir', true);
			if (erro) { //endereço desconhecido
				console.log("   |___Corrigindo erro de Endereço desconhecido!");
				let opcao_marcada = await esperarElemento('i[class*="check"]');
				if (opcao_marcada) {
					opcao_marcada.parentElement.parentElement.click();
				} else {
					await clicarBotao('mat-expansion-panel-header','Endereços');
					await clicarBotao('button','Endereço desconhecido');
					await clicarBotao('button','Sim');
				}
				await clicarBotao('button','Inserir');
			}
			resolve(true);
			console.log("     |___fim acao2");
		});
	}
	
	async function acao3() {
		return new Promise(async resolve => {
			fundo(true);
			console.log("     |___acao3");
			await clicarBotao('mat-step-header[aria-posinset="3"]');
			let grid = await esperarElemento('pje-autuacao-grid-partes[titulogrid="Outros participantes"]');
			await clicarBotao(grid.querySelector('button[aria-label="Adicionar parte ao processo"]'));
			await escolherOpcao('mat-select[aria-label="Tipo de participação"]', 'PERITO', 5);
			await clicarBotao('div[role="tab"]','Pessoa física');
			await sleep(500);
			let pergunta = 'Digite o NOME do perito:';
			let codigo_especialidade = null;
			let documento = await Promise.all([consultaPeritos(prompt(pergunta,''), codigo_especialidade)]).then(values => {
				return values[0];
			});
			await preencherInput('input[id="inputCPF"]', documento);
			await clicarBotao('button[aria-label="Pesquisar CPF"]', null, true); //***** demorando
			await clicarBotao('button[aria-label="Confirmar"]');
			let erro = await clicarBotao('button','Inserir', true);
			if (erro) { //endereço desconhecido
				console.log("   |___Corrigindo erro de Endereço desconhecido!");
				let opcao_marcada = await esperarElemento('i[class*="check"]');
				if (opcao_marcada) {
					opcao_marcada.parentElement.parentElement.click();
				} else {
					await clicarBotao('mat-expansion-panel-header','Endereços');
					await clicarBotao('button','Endereço desconhecido');
					await clicarBotao('button','Sim');
				}
				await clicarBotao('button','Inserir');
			}
			resolve(true);
			console.log("     |___fim acao3");
		});
	}
	
	async function acao4() {
		return new Promise(async resolve => {
			fundo(true);
			console.log("     |___acao4");
			await clicarBotao('mat-step-header[aria-posinset="4"]');
			let mat_slide_toggle = await esperarElemento('mat-slide-toggle[formcontrolname="juizoDigital"]');
			if (mat_slide_toggle.className.includes('mat-checked')) { //marcado
				await sleep(2000); //tem que esperar pq senão ele aciona o botão mas não grava
				await clicarBotao(mat_slide_toggle.firstElementChild, null);
				await clicarBotao('mat-dialog-container button', 'Sim');
				await esperarElemento('mat-slide-toggle[formcontrolname="juizoDigital"]:not(.mat-checked)');
				let esperarmensagem = await esperarElemento('pje-modal-juizo-digital');
				if (esperarmensagem.innerText.includes('Juízo 100% digital')) {
						esperarmensagem.querySelectorAll('button')[3].click(); //bug do pje.. não exclusao, carrega 2 botoes Sim e 2 botões não
				}
				await sleep(1000);
				console.log("     |___fim acao4");
				resolve(true);
			} else {
				await sleep(2000); //tem que esperar pq senão ele aciona o botão mas não grava
				await clicarBotao(mat_slide_toggle.firstElementChild, null);
				await esperarElemento('mat-slide-toggle[formcontrolname="juizoDigital"][class*="mat-checked"]');
				let esperarmensagem = await esperarElemento('pje-modal-juizo-digital');
				if (esperarmensagem.innerText.includes('Juízo 100% digital')) {
						esperarmensagem.querySelectorAll('button')[0].click();
				}
				await sleep(1000);
				console.log("     |___fim acao4");
				resolve(true);
			}
		});
	}
	
	async function acao5(parte, info) {
		return new Promise(async resolve => {
			fundo(true);
			console.log("     |___acao5");
			let ancora;
			await clicarBotao('mat-step-header[aria-posinset="3"]');

			let polo = "";
			switch (parte) {
				case "autor":
					polo = "Polo ativo";
					break;
				case "reu":
					polo = "Polo passivo";
					break;
				case "terceiro":
					polo = "Outros participantes";
					break;
			}

			//document.querySelector('div[id="myDIV"]>a[target="_top"]').style.border = "10px solid red";
			await clicarBotao('pje-autuacao-grid-partes[titulogrid="' + polo + '"] button[aria-label*="Adicionar procurador"]');
			await escolherOpcao('mat-select[aria-label="Tipo de vínculo"]', "ADVOGADO", 5);
			
			// testa o info para descobrir se é nome ou cpf
			let padrao = /[A-Za-z]/gmi;
			
			if (padrao.test(info)) {
				await preencherInput('input[id="inputParteId"]', info);
			} else {
				await preencherInput('input[id="inputCPFParteId"]', info);
			}
			await clicarBotao('pje-filtros button[aria-label="Filtrar"]', null, true);
			let lista_de_advogados = await esperarColecao('table[name="Advogados"] button[aria-label="Selecionar"]', 1);
			if (lista_de_advogados.length == 1) {
				await clicarBotao(lista_de_advogados[0]);
				let partes_a_vincular = await esperarColecao('pje-autuacao-partes-vinculadas mat-list-option', 1);
				console.log(partes_a_vincular.length);
				if (partes_a_vincular.length == 1) {
					await clicarBotao(partes_a_vincular[0]);
					let erro = await clicarBotao('button','Inserir', true);
					if (erro) { //endereço desconhecido
						console.log("   |___Corrigindo erro de Endereço desconhecido!");
						let opcao_marcada = await esperarElemento('i[class*="check"]');
						if (opcao_marcada) {
							opcao_marcada.parentElement.parentElement.click();
						} else {
							await clicarBotao('mat-expansion-panel-header','Endereços');
							await clicarBotao('button','Endereço desconhecido');
							await clicarBotao('button','Sim');
						}
						await clicarBotao('button','Inserir');
					}
				}
			}
			resolve(true);
			console.log("     |___fim acao5");
		});
	}
	
	async function acao6() {
		return new Promise(async resolve => {
			fundo(true);
			console.log("     |___acao6");
			await clicarBotao('mat-step-header[aria-posinset="5"]');
			await sleep(2000); //tem que esperar pq senão ele aciona o botão mas não grava
			if (!document.querySelector('button[aria-label*="Remover prioridade Falência ou Recuperação Judicial"]')) {
				await clicarBotao('button[aria-label*="Adicionar prioridade Falência ou Recuperação Judicial"]', null, true);
			}
			resolve(true);
			console.log("     |___fim acao6");
		});
	}
	
	async function acao7(tipo_parte, nomeOUdocumento) {
		return new Promise(async resolve => {
			fundo(true);
			console.log("     |___acao7");
			let ancora;
			let nome, documento, tipoDocumento, polo;			
			await clicarBotao('mat-step-header[aria-posinset="3"]');
			
			if (tipo_parte == "autor") {
				polo = "Polo ativo";
			} else if (tipo_parte == "reu") {
				polo = "Polo passivo";
			} else if (tipo_parte == "terceiro") {
				polo = "Outros participantes";
			}
			
			await clicarBotao('pje-autuacao-grid-partes[titulogrid="' + polo + '"] button[aria-label*="Adicionar parte"]');
			
			if (tipo_parte == "terceiro") {
				await escolherOpcao('mat-select[aria-label="Tipo de participação"]', 'TERCEIRO INTERESSADO', 5);
			}
			
			//padrão CPF
			let padraoCPF = /[0-9]{3}[\.]?[0-9]{3}[\.]?[0-9]{3}[-]?[0-9]{2}/gmi;
			if (padraoCPF.test(nomeOUdocumento)) {
				nome = "";
				tipoDocumento = "CPF";
				documento = (nomeOUdocumento.length < 14) ? nomeOUdocumento.replace(/^(\d{3})(\d{3})(\d{3})(\d{2})/, "$1.$2.$3-$4") : nomeOUdocumento;
			}
			
			//padrão CNPJ
			let padraoCNPJ = /[0-9]{2}[\.]?[0-9]{3}[\.]?[0-9]{3}[\/]?[0-9]{4}[-]?[0-9]{2}/gmi;
			if (padraoCNPJ.test(nomeOUdocumento)) {
				nome = "";
				tipoDocumento = "CNPJ";
				documento = (nomeOUdocumento.length < 18) ? nomeOUdocumento.replace(/^(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})/, "$1.$2.$3/$4-$5") : nomeOUdocumento;
			}
			
			//nome
			if (tipoDocumento != "CPF" && tipoDocumento != "CNPJ") {
				nome = nomeOUdocumento;
				documento = "";
				
				if (nomeOUdocumento.toUpperCase().includes('PGF') && nomeOUdocumento.length == 3) {
					documento = '05.489.410/0001-61';
				}
				
				if (nomeOUdocumento.toUpperCase().includes('PGFN') && nomeOUdocumento.length == 4) {
					documento = '00.394.460/0001-41';
				}
				
				if (nomeOUdocumento.toUpperCase().includes('AGU') && nomeOUdocumento.length == 3) {
					documento = '26.994.558/0001-23';
				}
				
				if (documento == "") {
					let msg = "(1) - Pessoa Física\n";
					msg = msg + "(2) - Pessoa Jurídica\n";
					msg = "Escolha o Tipo de pessoa (Digite o número correspondente): \n\n" + msg;
					let escolha = parseInt(prompt(msg,''));
					tipoDocumento = (escolha == '1') ? "CPF" : "CNPJ";
				}
			}
			await cadastrarPessoa(nome, documento, tipoDocumento, tipo_parte);
			console.log("     |___fim acao7");
			resolve(true);
		});
	}
	
	async function acao8(assunto) {
		return new Promise(async resolve => {
			fundo(true);
			console.log("     |___acao8");
			await clicarBotao('mat-step-header[aria-posinset="2"]');
			await sleep(2000); //tem que esperar pq senão ele aciona o botão mas não grava
			let jaPossui = await esperarElemento('pje-data-table[aria-label="Assuntos Adicionados ao Processo"] tr', assunto, 1000);
			if (!jaPossui) {
				await clicarBotao('pje-autuacao-assuntos button[aria-label="Mostrar Filtros"]');
				await preencherInput('input[formcontrolname="codigoAssuntoFiltro"]', assunto);
				await clicarBotao('pje-autuacao-assuntos button[aria-label="Filtrar"]');
				await clicarBotao('pje-autuacao-assuntos button[aria-label*="Adicionar assunto ' + assunto + '"]');
				await esperarElemento('pje-data-table[aria-label="Assuntos Adicionados ao Processo"] tr', assunto);
			}
			resolve(true);
			console.log("     |___fim acao8");
		});
	}

	async function acao9() {
		return new Promise(async resolve => {
			fundo(true);
			console.log("     |___acao1");
			await clicarBotao('mat-step-header[aria-posinset="3"]');
			let grid = await esperarElemento('pje-autuacao-grid-partes[titulogrid="Outros participantes"]');
			await clicarBotao(grid.querySelector('button[aria-label="Adicionar parte ao processo"]'));
			await escolherOpcao('mat-select[aria-label="Tipo de participação"]', 'CUSTOS LEGIS', 5);
			await clicarBotao('div[role="tab"]','Ministério público do trabalho');
			await sleep(500);
			await clicarBotao('button[aria-label="Selecionar"]');
			await clicarBotao('button','Inserir');
			console.log("     |___fim acao9");
			resolve(true);
		});
	}
	
	async function acao10() {
		return new Promise(async resolve => {
			fundo(true);
			console.log("     |___acao10");
			await clicarBotao('mat-step-header[aria-posinset="4"]');
			let mat_slide_toggle = await esperarElemento('mat-slide-toggle[formcontrolname="liminarOuTutela"]');
			await sleep(2000); //tem que esperar pq senão ele aciona o botão mas não grava
			await clicarBotao(mat_slide_toggle.firstElementChild, null);
			await sleep(500);
			console.log("     |___fim acao10");
			resolve(true);
			
		});
	}
	
	async function acao11() {
		return new Promise(async resolve => {
			fundo(true);
			console.log("     |___acao11");
			await clicarBotao('mat-step-header[aria-posinset="4"]');
			let mat_slide_toggle = await esperarElemento('mat-slide-toggle[formcontrolname="justicaGratuita"]');
			await sleep(2000); //tem que esperar pq senão ele aciona o botão mas não grava
			await clicarBotao(mat_slide_toggle.firstElementChild, null);
			await sleep(500);
			console.log("     |___fim acao11");
			resolve(true);
			
		});
	}
	
	async function monitorFim() {		
		let param = preferencias.tempAAEspecial;
		console.log('monitorFim(' + param + ')');
		
		//vamos lá.. ação automatizada em lote: se tiver vínculo/param resolver primeiro. 
		//Depois que encerrar todos os vínculos é que iremos partir para verificar se é uma AA decorrente de Lote
		if (param && param != "nenhum") { //se tem vínculo continua
			window.addEventListener("beforeunload", function (e) {			
				console.log("JANELA ANEXAR fechou...");
				console.log("     |___avisa a janela DETALHES para executar a AA: " + param);
				browser.runtime.sendMessage({tipo: 'storage_vinculo', valor: param});
			});
		} else {
			if (preferencias.AALote.length > 0) { //vem do AA em Lote
				let guardarStorage = browser.storage.local.set({'AALote': ''});
				Promise.all([guardarStorage]).then(values => { window.close() });
			}
		}
	}
}

async function cadastrarPessoa(nome, documento, tipoDocumento, tipo_parte) {
	console.log("MaisPJe: cadastrando Pessoa no processo");
	console.log("     |___(" + tipo_parte + ") " + nome + " " + tipoDocumento + " n. " + documento);
	if (tipoDocumento == "CPF") {
		let tipoPessoa = await obterDadosPessoaPublica(documento);
		console.log("     |___" + tipoPessoa);
		if (tipoPessoa == "vazio") {
			await clicarBotao('div[role="tab"]','Pessoa física');
			await sleep(preferencias.maisPje_velocidade_interacao + 500); //necessário para permitir o preenchimento do CPF
			if (documento == "") { //situações sem cpf/cnpj
				let mat_slide_toggle1 = await esperarElemento('mat-slide-toggle[formcontrolname="naoPossuiCpf"]');
				await clicarBotao(mat_slide_toggle1.firstElementChild);
				let mat_slide_toggle2 = await esperarElemento('mat-slide-toggle[formcontrolname*="possuiOutroDocumento"]');
				if (mat_slide_toggle2.className.includes('mat-checked')) {
					await clicarBotao(mat_slide_toggle2.firstElementChild);
				}
				await preencherInput('input[id="inputNomeOuAlcunha"]', nome);
			} else {
				await preencherInput('input[id="inputCPF"]', documento);
				await clicarBotao('pje-selecao-parte-pf button[aria-label="Pesquisar CPF"]', null, true);
				if (erro) {
					erro = false;
					console.log('     |___Erro ao cadastrar ' + nome);
					return;
				}
			}
			await clicarBotao('button[aria-label="Confirmar"]');
			await sleep(preferencias.maisPje_velocidade_interacao + 500);
			if (erro) {
				erro = false;
				console.log('     |___Erro ao cadastrar ' + nome);
				return;
			}
			await clicarBotao('button','Inserir');
			if (erro) {
				erro = false;
				console.log("   |___Corrigindo erro de Endereço desconhecido!");
				await clicarBotao('mat-expansion-panel-header','Endereços');
				await clicarBotao('button[aria-label="Usar esse endereço no processo"]');
				if (querySelectorByText('button','Sim')) { //aviso de confirmação de endereço cadastrado
					await clicarBotao('button','Sim');
				}
				await clicarBotao('button','Inserir');
				await sleep(preferencias.maisPje_velocidade_interacao + 500);
			}
			return;
		} else { //União, Estado, Municípios, autarquias, etc
			await clicarBotao('div[role="tab"]','Pessoa jurídica de direito público');
			await sleep(preferencias.maisPje_velocidade_interacao + 500);
			if (tipoPessoa.includes('Federal')) {
				await clicarBotao('label','Federal');
			} else if (tipoPessoa.includes('Estadual')) {
				await clicarBotao('label','Estadual');
			} else if (tipoPessoa.includes('Municipal')) {
				await clicarBotao('label','Municipal');
			}
			if (tipoPessoa.includes('Orgao')) {
				await sleep(preferencias.maisPje_velocidade_interacao + 500);
				await clicarBotao('label','Órgão');
			} else if (tipoPessoa.includes('Autarquia')) {
				await sleep(preferencias.maisPje_velocidade_interacao + 500);
				await clicarBotao('label','Autarquias');
			}
			if (tipoPessoa.includes('MPT')) {
				await clicarBotao('div[role="tab"]','Ministério público do trabalho');
				await sleep(preferencias.maisPje_velocidade_interacao + 500);
			}
			await sleep(preferencias.maisPje_velocidade_interacao + 500); //espera se vai aparecer a caixa de pesquisa
			if (document.querySelector('input[formcontrolname="cnpj"]')) {
				await preencherInput('input[formcontrolname="cnpj"]', documento);
				let bt_filtrar = await esperarColecao('button[aria-label="Filtrar"]', 1);
				await clicarBotao(bt_filtrar[1]);
			}
			let bt = await esperarElemento('tr', nome);
			await clicarBotao(bt.querySelector('button[aria-label="Selecionar"]'));
			await sleep(preferencias.maisPje_velocidade_interacao + 500);
			await clicarBotao('button','Inserir');
			await sleep(preferencias.maisPje_velocidade_interacao + 500);
			return;
		}
	} else {
		let tipoPessoa = await obterDadosPessoaPublica(documento);
		console.log("     |___" + tipoPessoa);
		if (tipoPessoa == "vazio") {
			await clicarBotao('div[role="tab"]','Pessoa jurídica de direito privado');
			await sleep(preferencias.maisPje_velocidade_interacao + 500); //necessário para permitir o preenchimento do CNPJ
			if (documento == "") { //situações sem cpf/cnpj
				let mat_slide_toggle1 = await esperarElemento('mat-slide-toggle[formcontrolname="naoPossuiCnpj"]');
				await clicarBotao(mat_slide_toggle1.firstElementChild);
				let mat_slide_toggle2 = await esperarElemento('mat-slide-toggle[formcontrolname*="possuiOutroDocumentoJPri"]');
				if (mat_slide_toggle2.className.includes('mat-checked')) {
					await clicarBotao(mat_slide_toggle2.firstElementChild);
				}								
				await preencherInput('input[id="inputNomeOuAlcunhaJPri"]', nome);
			} else {
				await preencherInput('input[id="inputCNPJ"]', documento);
				await clicarBotao('pje-selecao-parte-pj button[aria-label="Pesquisar CNPJ"]', null, true);
				if (erro) {
					erro = false;
					console.log('     |___Erro ao cadastrar ' + nome);
					return;
				}
			}
			await clicarBotao('button[aria-label="Confirmar"]');
			await sleep(preferencias.maisPje_velocidade_interacao + 500);
			if (erro) {
				erro = false;
				console.log('     |___Erro ao cadastrar ' + nome);
				return;
			}
			await clicarBotao('button','Inserir');
			if (erro) {
				erro = false;
				console.log("   |___Corrigindo erro de Endereço desconhecido!");
				await clicarBotao('mat-expansion-panel-header','Endereços');
				await clicarBotao('button[aria-label="Usar esse endereço no processo"]');
				if (querySelectorByText('button','Sim')) { //aviso de confirmação de endereço cadastrado
					await clicarBotao('button','Sim');
				}
				await clicarBotao('button','Inserir');
				await sleep(preferencias.maisPje_velocidade_interacao + 500);
			}
			return;
		} else { //União, Estado, Municípios, autarquias, etc
			await clicarBotao('div[role="tab"]','Pessoa jurídica de direito público');
			await sleep(preferencias.maisPje_velocidade_interacao + 500);
			if (tipoPessoa.includes('Federal')) {
				await clicarBotao('label','Federal');
			} else if (tipoPessoa.includes('Estadual')) {
				await clicarBotao('label','Estadual');
			} else if (tipoPessoa.includes('Municipal')) {
				await clicarBotao('label','Municipal');
			}
			if (tipoPessoa.includes('Orgao')) {
				await sleep(preferencias.maisPje_velocidade_interacao + 500);
				await clicarBotao('label','Órgão');
			} else if (tipoPessoa.includes('Autarquia')) {
				await sleep(preferencias.maisPje_velocidade_interacao + 500);
				await clicarBotao('label','Autarquias');
			}
			if (tipoPessoa.includes('MPT')) {
				await clicarBotao('div[role="tab"]','Ministério público do trabalho');
				await sleep(preferencias.maisPje_velocidade_interacao + 500);
			}
			await sleep(preferencias.maisPje_velocidade_interacao + 500); //espera se vai aparecer a caixa de pesquisa
			if (document.querySelector('input[formcontrolname="cnpj"]')) {
				await preencherInput('input[formcontrolname="cnpj"]', documento);
				let bt_filtrar = await esperarColecao('button[aria-label="Filtrar"]', 1);
				await clicarBotao(bt_filtrar[1]);
			}
			let bt = await esperarElemento('tr', documento);
			await clicarBotao(bt.querySelector('button[aria-label="Selecionar"]'));
			await sleep(preferencias.maisPje_velocidade_interacao + 500);
			await clicarBotao('button','Inserir');
			await sleep(preferencias.maisPje_velocidade_interacao + 500);
			return;
		}
	}
}

//FUNÇÃO EXCLUSIVA DA BUSCA DA ARVORE DE Modelos
async function buscandoModeloNaArvore() {
	return new Promise(async resolve => {
		console.debug('maisPJe: buscandoModeloNaArvore')
		let check = setInterval(function() {
			if (document.querySelector('span[class="nodo-filtrado"]')) {
				clearInterval(check);
				return resolve(true);
			} else {
				document.querySelector('pje-arvore-modelo-documento div[aria-expanded="false"]').click();
			}
		}, 500);
	});
}

//OBTER O ID DA JURISDIÇÃO
async function obterIdJurisdicao() {
	let idProcesso = document.location.href.substring(document.location.href.search("/processo/")+10, document.location.href.search("/retificar"));
	let url = 'https://' + preferencias.trt + '/pje-comum-api/api/processos/id/' + idProcesso;
	let resposta = await fetch(url);
	let dados = await resposta.json();
	return dados.jurisdicao.id;
}

//IDENTIFICAR SE O CNPJ PERTENCE À PESSOA JURÍDICAPÚBLICA
async function obterDadosPessoaPublica(cpfcnpj) {
	let idJurisdicao = await obterIdJurisdicao();
	console.log(idJurisdicao);
	const urls = [
		'https://' + preferencias.trt + '/pje-comum-api/api/pessoas/juridicas?esfera=F&tipoEntidade=O&idJurisdicao=' + idJurisdicao,
		'https://' + preferencias.trt + '/pje-comum-api/api/pessoas/juridicas?esfera=F&tipoEntidade=A&idJurisdicao=' + idJurisdicao,
		'https://' + preferencias.trt + '/pje-comum-api/api/pessoas/juridicas?esfera=E&tipoEntidade=O&idJurisdicao=' + idJurisdicao,
		'https://' + preferencias.trt + '/pje-comum-api/api/pessoas/juridicas?esfera=E&tipoEntidade=A&idJurisdicao=' + idJurisdicao,
		'https://' + preferencias.trt + '/pje-comum-api/api/pessoas/juridicas?esfera=M&tipoEntidade=O&idJurisdicao=' + idJurisdicao,
		'https://' + preferencias.trt + '/pje-comum-api/api/pessoas/juridicas?esfera=M&tipoEntidade=A&idJurisdicao=' + idJurisdicao,
		'https://' + preferencias.trt + '/pje-comum-api/api/pessoas/juridicas?apenasMPT=true'
	];
	var tipo = "vazio";
	
	for (const [pos, url] of urls.entries()) {
		if (tipo == 'vazio') {
			tipo = await fetch(url,
			{				
				headers: {
					"X-Grau-Instancia": 1
				},
				credentials: "include",
				method: "GET",
				mode: "cors",
			}).then(function (response) {
				return response.json();
			})
			.then(data=>{			
				for (i=0; i <= data.length; i++) {
					if (data[i].cnpj === cpfcnpj) {
						return pos;
						break;
					}
				}
				return 'vazio';
			})
			.catch(function (err) {
				return 'vazio';
			});
		}
	}
	
	switch (tipo) {
		case 0:
			return 'FederalOrgao'
			break
		case 1:
			return 'FederalAutarquia'
			break
		case 2:
			return 'EstadualOrgao'
			break
		case 3:
			return 'EstadualAutarquia'
			break
		case 4:
			return 'MunicipalOrgao'
			break
		case 5:
			return 'MunicipalAutarquia'
			break
		case 6:
			return 'MPT'
			break
		default:
			return 'vazio'
	}
}

//FUNÇÃO RESPONSÁVEL PELA CONSULTA RÁPIDA DE PROCESSO NO PJE
async function consultaRapidaPJE(processo) {
	if(!processo){
		processo = await criarCaixaDePergunta('text','Digite o número do processo ou o nome da parte:\n');
	}
	
	if(!preferencias.trt){
		return;
	}
	
	let api = [];
	let soNumeros = processo.replace(/[^0-9]+/g, '');
	if (soNumeros === '') {
		if (processo.length < 7) { criarCaixaDeAlerta("Consulta Rápida de Processo",'Informe pelo menos 7 caracteres nas pesquisas por nome.'); fundo(false); return; }
		exibir_mensagem("Pesquisando processos em nome da parte " + processo + "\n\n Essa consulta costuma demorar um pouco mais..");

		let maisDeUmNome = processo.split(';');
		if (maisDeUmNome.length > 1) {
			for (const [pos, nome] of maisDeUmNome.entries()) {
				console.debug('maisPJe: pesquisando processos em nome de ' + nome);
				let lista = await obterIdProcessoViaApiPublica(nome);
				if (lista.resultado) { api.push(...lista.resultado) }
			}
		} else {
			api = await obterIdProcessoViaApiPublica(processo);
			api = api.resultado;
		}
		
	} else if (!new RegExp('\\d{7}-\\d{2}\\.\\d{4}\\.\\d{1,2}\\.\\d{1,2}\\.\\d{4}','g').test(processo)) { //se o número não estiver completo
		let var1 = processo;
		if (var1.length >= 20) {
			if (var1.length == 20) {
				var1 = var1.substring(0,7) + "-" + var1.substring(7,9) + "." + var1.substring(9,13) + "." + var1.substring(13,14) + "." + var1.substring(14,16) + "." + var1.substring(16,20);
			}
			processo = var1;
		} else {
			// a separação somente será feita se tiver digito verificador
			if (var1.search('-') > 0) {
				let n = ''; //numero
				let d = ''; //digito
				let a = ''; //ano
				n = var1.substring(0, var1.search('-'));
				n = (n.length < 7) ? ('0000000' + n).slice(-7) : n;
				if (var1.match(new RegExp('\\-\\d{2}','g'))) {
					d = var1.match(new RegExp('\\-\\d{2}','g')).join();
					d = d.replace(/-/g, '');
					console.log('Dígito: ' + d);
				}
				if (var1.match(new RegExp('\\.\\d{4}','g'))) {
					a = var1.match(new RegExp('\\.\\d{4}','g')).join();
					console.log('Ano: ' + a);
				}
				processo = n + '-' + d + a;
			} else {
				var1 = (var1.length < 7) ? ('0000000' + var1).slice(-7) : var1;
				processo = var1;
			}		
		}
		api = await obterIdProcessoViaApi(processo);
	} else {
		api = await obterIdProcessoViaApiPublica(processo);
	}
	
	if (typeof(api) == "undefined") { criarCaixaDeAlerta("Consulta Rápida de Processo","Processo não encontrado.",3); fundo(false); return; }
	if (typeof(api[0]) == "undefined") { criarCaixaDeAlerta("Consulta Rápida de Processo","Processo não encontrado.",3); fundo(false); return; }
	if (api.length > 1) { criarCaixaDeSelecao(api) }
	if (api.length == 1) {
		let url = 'https://' + preferencias.trt + '/pjekz/processo/' + (api[0].id ? api[0].id : api[0].idProcesso) + '/detalhe'
		window.open(url, '_blank');
	}
	fundo(false);
	
	
	function criarCaixaDeSelecao(dados) {
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
				console.log(e.target.id);
				if (e.target.id.includes('_copiarLista')) {
					let textocopiado = elemento1.innerText.match(new RegExp('\\d{7}-\\d{2}\\.\\d{4}\\.\\d{1,2}\\.\\d{1,2}\\.\\d{4}','gm')).join();
					// let ta = document.createElement("textarea");
					// ta.textContent = textocopiado;
					// document.body.appendChild(ta);
					// ta.select();
					// document.execCommand("copy");
					navigator.clipboard.writeText(textocopiado);
					browser.runtime.sendMessage({tipo: 'criarAlerta', valor: '\n Conteúdo copiado com sucesso!', icone: '3'});
				} else if (e.target.id.includes('_exportarAALote')) {
					let textocopiado = elemento1.innerText.match(new RegExp('\\d{7}-\\d{2}\\.\\d{4}\\.\\d{1,2}\\.\\d{1,2}\\.\\d{4}','gm')).join();
					elemento1.remove();
					acoesEmLote(textocopiado);
				} else {
					elemento1.remove()
				}
			}; //se clicar fora fecha a janela
			
			let div = document.createElement("div");
			div.style="height: auto;display: inline-grid;background-color: white;padding: 15px;border-radius: 4px;box-shadow: 0 2px 1px -1px rgba(0,0,0,.2),0 1px 1px 0 rgba(0,0,0,.14),0 1px 3px 0 rgba(0,0,0,.12); overflow: auto; max-height: 90%; min-width: 15vw;";
			let titulo = document.createElement("span");
			titulo.style = "color: grey; border-bottom: 1px solid lightgrey;";
			titulo.innerText = "Selecione o Processo";
			div.appendChild(titulo);
			
			let btCopiarLista = document.createElement("span");
			btCopiarLista.id = 'maisPje_bt_copiarLista';
			btCopiarLista.style = "position: absolute;";
			btCopiarLista.title = "Copiar lista";
			btCopiarLista.onmouseenter = function () {document.getElementById('maisPje_i_copiarLista').style.filter = 'brightness(0.5)'};
			btCopiarLista.onmouseleave = function () {document.getElementById('maisPje_i_copiarLista').style.filter = 'brightness(1)'};			
			
			let iCopiarLista = document.createElement("i");
			iCopiarLista.id = 'maisPje_i_copiarLista';
			iCopiarLista.className = 'icone copy-solid t18';
			iCopiarLista.style.backgroundColor = "lightgray";		
			btCopiarLista.appendChild(iCopiarLista);
			div.appendChild(btCopiarLista);
			
			let btExportarAALote = document.createElement("span");
			btExportarAALote.id = 'maisPje_bt_exportarAALote';
			btExportarAALote.style = "position: absolute;margin-left:25px;margin: 3px 0 0 23px;";
			btExportarAALote.title = "AA Lote";
			btExportarAALote.onmouseenter = function () {document.getElementById('maisPje_i_exportarAALote').style.filter = 'brightness(0.5)'};
			btExportarAALote.onmouseleave = function () {document.getElementById('maisPje_i_exportarAALote').style.filter = 'brightness(1)'};			
			
			let iExportarAALote = document.createElement("i");
			iExportarAALote.id = 'maisPje_i_exportarAALote';
			iExportarAALote.className = 'icone box-open t20';
			iExportarAALote.style.backgroundColor = "lightgray";		
			btExportarAALote.appendChild(iExportarAALote);
			div.appendChild(btExportarAALote);
			
			let map = [].map.call(
				dados, 
				function(dado) {
					let nrCompleto = dado.numeroProcessoCompleto || dado.numero;
					let idP = dado.idProcesso || dado.id;
					let nmAutor = dado.autor || null;
					let nmReu = dado.reu || null;
					let span = document.createElement("span");
					span.className = "mat-option";
					span.innerText = nrCompleto;	
					span.style = 'padding: 10px 25px 10px 10px; border-radius: 5px 0px 0px 5px; filter: saturate(3) brightness(1);margin-top: 5px;color: rgb(81,81,81);font-weight: bold;text-align: center;';
					
					obterFaseIdProcessoViaApi(idP).then(resultado => {
						switch(resultado) {
							case 'CONHECIMENTO':
								span.style.borderRight = '15px solid rgba(179, 229, 252, .5)';
								span.style.backgroundImage = 'linear-gradient(to right, white, rgba(179, 229, 252, .2))';
								span.title = (nmAutor) ? ("(" + nmAutor + " X " + nmReu + ") - Fase de Conhecimento") : "Fase de Conhecimento";
								break;
							case 'LIQUIDACAO':
								span.style.borderRight = '15px solid rgba(174, 213, 129, .5)';
								span.style.backgroundImage = 'linear-gradient(to right, white, rgba(174, 213, 129, .2))';
								span.title = (nmAutor) ? ("(" + nmAutor + " X " + nmReu + ") - Fase de Liquidação") : "Fase de Liquidação";
								break;
							case 'EXECUCAO':
								span.style.borderRight = '15px solid rgba(138, 138, 138, .5)';
								span.style.backgroundImage = 'linear-gradient(to right, white, rgba(138, 138, 138, .2))';
								span.title = (nmAutor) ? ("(" + nmAutor + " X " + nmReu + ") - Fase de Execução") : "Fase de Execução";
								break;
							case 'ARQUIVADO':
								span.style.borderRight = '15px solid rgba(186, 104, 200, .5)';
								span.style.backgroundImage = 'linear-gradient(to right, white, rgba(186, 104, 200, .2))';
								span.title = (nmAutor) ? ("(" + nmAutor + " X " + nmReu + ") - Arquivado") : "Arquivado";
								break;
						}
					});
					
					span.onmouseenter = function () {span.style.filter = 'saturate(3) brightness(.9)'};
					span.onmouseleave = function () {span.style.filter = 'saturate(3) brightness(1)'};
					span.onclick = function () {
						let url = 'https://' + preferencias.trt + '/pjekz/processo/' + idP + '/detalhe'
						window.open(url, '_blank');
						document.getElementById('maisPje_caixa_de_selecao').remove();
					};
										
					
					
					div.appendChild(span);
				}
			);
			elemento1.appendChild(div);
			document.body.appendChild(elemento1);
		}
	}
}

//FUNÇÃO RESPONSÁVEL POR ADICIONAR UM BOTÃO DE ACESSO AO PJE NA PÁGINA GOOGLE - PLANILHAS
function addBotaoPlanilhasGoogle(){
	if (document.getElementById("docs-toolbar")) {
		if (!document.getElementById("pjextension_botao_buscarProcesso")) {
			let el = document.getElementById("docs-toolbar");
			let bt = document.createElement("a");
			let ic = document.createElement("span");
			bt.id = "pjextension_botao_buscarProcesso";
			bt.title = "Buscar Processo"; //<--aria-label
			ic.innerText = "PJe (F1)";
			bt.style = "cursor: pointer; position: relative; padding: 5px; z-index: 100; opacity: 1;background-color: #dd4b39;border-radius: 5px;font-weight: bold;color: white;";
			bt.onmouseover = function () {bt.style.opacity = 0.5};
			bt.onmouseleave = function () {bt.style.opacity = 1};
			bt.onclick = function () {
				if(window.location.href.includes('docs.google.com/spreadsheets')) {
					consultaRapidaPJE(identificarNumeroDoProcessoDaPlanilhaGoogle());
				}
			};				
			bt.appendChild(ic);
			el.insertBefore(bt, el.firstChild);
		}
	}
}

function identificarNumeroDoProcessoDaPlanilhaGoogle(){
	let erro = 'Conteúdo não é um número de processo!\n\nPadrão de busca: 0000000-00.0000.0.00.0000';
	let np = document.querySelector('div[id="t-formula-bar-input"]').innerText;	
	if(!np.match(new RegExp('\\d{7}-\\d{2}\\.\\d{4}\\.\\d{1,2}\\.\\d{1,2}\\.\\d{4}','g'))){
		if(!np.match(new RegExp('\\d{20}','g'))){
			alert(erro);
			return;
		} else {
			np = np.match(new RegExp('\\d{20}','g')).join();
			np = np.substr(0,7) + "-" + np.substr(7,2) + "." + np.substr(9,4) + "." + np.substr(13,1) + "." + np.substr(14,2) + "." + np.substr(16,4);
		}		
	} else {
		np = np.match(new RegExp('\\d{7}-\\d{2}\\.\\d{4}\\.\\d{1,2}\\.\\d{1,2}\\.\\d{4}','g')).join();
	}
	return np;
}

//FUNÇÃO RESPONSÁVEL POR CRIAR O KAIZEN COM ATALHOS
function kaizen(nome_janela) {
	if (!document.getElementById('maisPje_menuKaizen')) {
		//CARREGA O PACOTE DE ÍCONES PARA A PÁGINA E O CSS DO MENU
		browser.runtime.sendMessage({tipo: 'insertCSS', file: 'maisPje_icones.css'});
		browser.runtime.sendMessage({tipo: 'insertCSS', file: 'maisPje_menu.css'});
		
		//criar estrutura do menuConvenios
		let menuMaisPje = document.createElement("menumaispje");
		menuMaisPje.setAttribute('aria-live','polite'); //***
		menuMaisPje.id = "maisPje_menuKaizen";
		menuMaisPje.draggable = true;
		
		let menuMaisPje_content = document.createElement("div");
		menuMaisPje_content.id = "maisPje_menuKaizen_content";
		menuMaisPje_content.style = "border-radius: 100px;";
		menuMaisPje_content.className = "menuMaisPje-content";
		
		let toggle_btn = document.createElement("div");
		toggle_btn.className = "toggle-btn";
		
		let img = document.createElement("img");
		img.title = 'maisPje: menu kaizen'; //***
		img.draggable = false;
		img.className = "maisPje-img";
		img.src = browser.runtime.getURL("icons/ico_32.png");
		toggle_btn.appendChild(img);
		
		let divStatus = document.createElement("i");
		divStatus.id = 'menuMaisPje_status';
		divStatus.style.display = "none";
		
		let infoStatus1 = document.createElement("i");
		infoStatus1.style = 'position: absolute;width: 55%;height: 55%;background-color: #0e2431;border-radius: 25px;';
		divStatus.appendChild(infoStatus1);
		
		let infoStatus2 = document.createElement("i");
		infoStatus2.className = 'fan-solid spin';
		infoStatus2.style = 'position: absolute;width: 55%;height: 55%;background-color: #00c1ff;';
		divStatus.appendChild(infoStatus2);
		
		toggle_btn.appendChild(divStatus);		
		
		menuMaisPje_content.appendChild(toggle_btn);
		menuMaisPje.appendChild(menuMaisPje_content);
		
		bt_atalhos();
		
		//posição inicial do menu
		browser.storage.local.get('menu_kaizen', function(result){
			let temp = result.menu_kaizen;
			if (!temp) { return }			
			switch(nome_janela) {
				case "PRINCIPAL":
					menuMaisPje.style.left = result.menu_kaizen.principal.posx;
					menuMaisPje.style.top = result.menu_kaizen.principal.posy;
					break;
				case "DETALHES":
					menuMaisPje.style.left = result.menu_kaizen.detalhes.posx;
					menuMaisPje.style.top = result.menu_kaizen.detalhes.posy;
					break;
				case "TAREFAS":
					menuMaisPje.style.left = result.menu_kaizen.tarefas.posx;
					menuMaisPje.style.top = result.menu_kaizen.tarefas.posy;
					break;
			}
			setTimeout(function() {direcaoItensMenu()}, 500);
		});
		
		document.body.appendChild(menuMaisPje);
		
		//cria o eventlistener
		let posx,posy;
		
		//área de drop
		let area_da_tela = document.createElement('div');
		area_da_tela.id = "maisPje_menuKaizen_area_da_tela";
		area_da_tela.style="width: 100%;height: 100%;z-index: 999;position: absolute; display: none;top: 0px;"
		area_da_tela.ondragover = function(e) { 
			e.preventDefault();  
			e.dataTransfer.dropEffect = "move";
			posx = e.clientX;
			posy = e.clientY;
		}
		area_da_tela.ondrop = function(e) {  e.preventDefault();}		
		document.body.appendChild(area_da_tela);
		
		menuMaisPje.ondragstart = function() {
			area_da_tela.style.display = "flex";
		}
		
		menuMaisPje.ondragend = function(e) {
			area_da_tela.style.display = "none";
			menuMaisPje.style.top = (posy - 12) + "px";
			menuMaisPje.style.left = (posx - 12) + "px";
			direcaoItensMenu();
			let posmenu = window.getComputedStyle(document.querySelector("menumaispje"));
			browser.storage.local.get('menu_kaizen', function(result){
				let temp = result.menu_kaizen;
				if (!temp) { return }
				switch(nome_janela) {
					case "PRINCIPAL":
						temp.principal.posx = parseInt(posmenu.left) + 'px';
						temp.principal.posy = parseInt(posmenu.top) + 'px';
						break;
					case "DETALHES":
						temp.detalhes.posx = parseInt(posmenu.left) + 'px';
						temp.detalhes.posy = parseInt(posmenu.top) + 'px';
						break;
					case "TAREFAS":
						temp.tarefas.posx = parseInt(posmenu.left) + 'px';
						temp.tarefas.posy = parseInt(posmenu.top) + 'px';
						break;
				}
				browser.storage.local.set({'menu_kaizen': temp});
			});
		}
		
		function direcaoItensMenu() {
			//DESCRIÇÃO: REGRA DO TOOLTIP
			let faixaLimiteDaTela,posicaoDoMenuEmPixels;
			if (preferencias.kaizenNaHorizontal) {
				faixaLimiteDaTela = parseInt(window.innerHeight) * 0.04; //left 4vw... distancia convertida em pixels
				posicaoDoMenuEmPixels = menuMaisPje.style.top.replace('px',''); 
				// console.log(posicaoDoMenuEmPixels + " > " + faixaLimiteDaTela);
				if (parseInt(posicaoDoMenuEmPixels) > parseInt(faixaLimiteDaTela)) {
					if (!document.getElementById('maisPje_tooltip_menuAcima')) { tooltip('menuAcima') }
				} else {
					if (!document.getElementById('maisPje_tooltip_menuAbaixo')) { tooltip('menuAbaixo') }
				}			
			} else {
				faixaLimiteDaTela = parseInt(window.innerWidth) * 0.05; //top 5vh... distancia convertida em pixels
				posicaoDoMenuEmPixels = menuMaisPje.style.left.replace('px',''); 
				// console.log(posicaoDoMenuEmPixels + " > " + faixaLimiteDaTela);
				if (parseInt(posicaoDoMenuEmPixels) > parseInt(faixaLimiteDaTela)) {
					if (!document.getElementById('maisPje_tooltip_menuEsquerda')) { tooltip('menuEsquerda') }
				} else {
					if (!document.getElementById('maisPje_tooltip_menuDireita')) { tooltip('menuDireita') }
				}
				
			}
			
			
			if (preferencias.kaizenNaHorizontal) {
				//o menu possui 390px de altura (30px por atalho)
				if (parseInt(window.getComputedStyle(menuMaisPje).left) < parseInt(window.innerWidth/2)) {//menu estiver na metade superior
					let itensmenu = document.querySelectorAll('span[id*="maisPje_menuKaizen_itemmenu_"]');
					if (!itensmenu) { return }
					let map = [].map.call(
						itensmenu, 
						function(itemmenu) {
							itemmenu.style.setProperty("--d","1")
						}
					);
				} else {//menu estiver na metade horizontal
					let itensmenu = document.querySelectorAll('span[id*="maisPje_menuKaizen_itemmenu_"]');
					if (!itensmenu) { return }
					let map = [].map.call(
						itensmenu, 
						function(itemmenu) {
							itemmenu.style.setProperty("--d","-1")
						}
					);
				}
			} else {
				//o menu possui 390px de altura (30px por atalho)
				if (parseInt(window.getComputedStyle(menuMaisPje).top) < parseInt(window.innerHeight/2)) {//menu estiver na metade superior
					//menu abre para baixo
					let itensmenu = document.querySelectorAll('span[id*="maisPje_menuKaizen_itemmenu_"]');
					if (!itensmenu) { return }
					let map = [].map.call(
						itensmenu, 
						function(itemmenu) {
							itemmenu.style.setProperty("--d","1")
						}
					);
				} else {//menu estiver na metade superior
					//menu abre para cima
					let itensmenu = document.querySelectorAll('span[id*="maisPje_menuKaizen_itemmenu_"]');
					if (!itensmenu) { return }
					let map = [].map.call(
						itensmenu, 
						function(itemmenu) {
							itemmenu.style.setProperty("--d","-1")
						}
					);
				}
			}
			
		}
		
		// console.log("preferencias.acionarKaizenComClique: " + preferencias.acionarKaizenComClique);
		let metodoAcionamento = (preferencias.acionarKaizenComClique) ? "click" : "mouseenter";
		toggle_btn.addEventListener(metodoAcionamento, () =>{
			
			if (preferencias.kaizenNaHorizontal) {
				menuMaisPje.classList.toggle("openh");
			} else {
				menuMaisPje.classList.toggle("openv");
			}
			
		});
				
		function bt_atalhos() {
			let posicao_itemmenu = 1;

			const atalhos = getAtalhosNovaAba();

			Object.values(atalhos).forEach(atalho => {
				if (atalho.condicao_adicionar()) {
					const botao = atalho.criar_botao(posicao_itemmenu++);
					menuMaisPje_content.appendChild(botao);
				}
			});
		}
		
		//Se existir atalho na função F2 criar uma área de ação no canto inferior esquerdo da tela
		//se o usuário repousar o mouse ali em cima por 3 segundos, acionará a função F2 sem precisar usar o teclado
		criarAreaDoPreferenciasF2();
		criarAreaDoPreferenciasF3();		
	}
}

//criar area do preferencias.F2
function criarAreaDoPreferenciasF2() {
	if (!preferencias.tempF2) { return }
	if (!(document.location.href.includes('.jus.br/pjekz/') && document.location.href.includes("/detalhe"))) { return }	
	if (!preferencias.aaVariados[3].ativar) { return }
	if (document.getElementById('maisPje_areaDeAtalhoF2')) { return }
	if (preferencias.tempF2 == 'Nenhum') { return }
	
	let areaDeAtalhoF2 = document.createElement('a');
	areaDeAtalhoF2.id = 'maisPje_areaDeAtalhoF2';
	areaDeAtalhoF2.style = 'position: fixed; left: -1vw; top: 82vh; width: 10vw; height: 20vh; background-color: black; z-index: 10000; border-radius: 100%; opacity: 1; font-weight: bold; outline: white solid 0.3em; cursor: pointer; scale: 0.5; animation: unset; font-size: 6em; text-align: center; line-height: 19vh; color: #3cb371a6;box-shadow: rgb(0, 0, 0) 0px 0px 80px, rgb(0, 0, 0) 0px 0px 60px, rgb(0, 0, 0) 0px 0px 0px, rgba(4, 4, 4, 0) 0px 0px 100px;';
	areaDeAtalhoF2.setAttribute('aria-label', preferencias.tempF2);
	areaDeAtalhoF2.innerText = "F2";
	areaDeAtalhoF2.onclick = function() {
		acao_vinculo(preferencias.tempF2);
	}
	acionarSemCliqueGenerico(areaDeAtalhoF2,'black','#1c5536');
	
	document.body.appendChild(areaDeAtalhoF2);
}

//criar area do preferencias.F3
function criarAreaDoPreferenciasF3() {
	if (!preferencias.tempF3) { return }
	if (!(document.location.href.includes('.jus.br/pjekz/') && document.location.href.includes("/detalhe"))) { return }
	console.log(preferencias.aaVariados[4].ativar)
	if (!preferencias.aaVariados[4].ativar) { return }
	if (document.getElementById('maisPje_areaDeAtalhoF3')) { return }
	if (preferencias.tempF3 == 'Nenhum') { return }
	
	let areaDeAtalhoF3 = document.createElement('a');
	areaDeAtalhoF3.id = 'maisPje_areaDeAtalhoF3';
	areaDeAtalhoF3.style = 'position: fixed; left: 6vw; top: 82vh; width: 10vw; height: 20vh; background-color: black; z-index: 10000; border-radius: 100%; opacity: 1; font-weight: bold; outline: white solid 0.3em; cursor: pointer; scale: 0.5; animation: unset; font-size: 6em; text-align: center; line-height: 19vh; color: #ff6347a6; box-shadow: rgb(0, 0, 0) 0px 0px 80px, rgb(0, 0, 0) 0px 0px 60px, rgb(0, 0, 0) 0px 0px 0px, rgba(4, 4, 4, 0) 0px 0px 100px;';
	areaDeAtalhoF3.setAttribute('aria-label', preferencias.tempF3);	
	areaDeAtalhoF3.innerText = "F3";
	areaDeAtalhoF3.onclick = function() {
		acao_vinculo(preferencias.tempF3);
	}
	acionarSemCliqueGenerico(areaDeAtalhoF3,'black','#681d01');
	
	document.body.appendChild(areaDeAtalhoF3);
}

//FUNÇÃO RESPONSÁVEL POR ADICIONAR O BOTÃO DE ZOOM NA JANELA DETALHES
async function addBotoesDocumentoCarregado(id) {
	return new Promise(resolve => {
		addBotao();
		resolve(true);
	});
	
	async function addBotao() {
		if (!document.getElementById('extensaoPje_barra_botoes_' + id)) {
			
			if (preferencias.gigsOcultarCabecalho) { ocultarCabecalho() }
			
			//DESCRIÇÃO: REGRA DO TOOLTIP
			if (!document.getElementById('maisPje_tooltip_direita')) {
				tooltip('direita');
			}
			
			console.log('addBotoesDocumentoCarregado()');
			//pega o elemento que servirá de ancora para a barra de botões
			let ancora = document.querySelector('pje-historico-scroll-documento');
			
			//criar estrutura da barra_zoom
			let barra_zoom = document.createElement("div");
			barra_zoom.id = "extensaoPje_barra_botoes_" + id;
			// barra_zoom.style = 'position: absolute; z-index: 100; width: 2.5vw; height: auto; top: 100%; left: 0px;';
			barra_zoom.style = 'position: absolute; z-index: 100; width: 2.5vw; height: auto; top: 60vh; display: flex; flex-direction: column;';
			ancora.appendChild(barra_zoom);
			
			
			//cria o botão imprimir documento
			let printDocto = document.createElement('button');
			printDocto.id = 'extensaoPje_printDocto';
			printDocto.setAttribute('maisPje-tooltip-direita','Imprimir Documento');
			printDocto.className = 'mat-icon-button';		
			printDocto.style = 'font-size: 1.5em; color: orangered; opacity: 0.4; margin-top: 5px;';
			
			if (!document.getElementById('obj' + id)) {
				
				printDocto.style.color = 'lightgrey';
				printDocto.setAttribute('maisPje-tooltip-direita','modo de impressão desativado (modelo de documento antigo)');
				
			} else {
				
				printDocto.onmouseenter = function () {printDocto.style.opacity  = '1'};
				printDocto.onmouseleave = function () {printDocto.style.opacity  = '0.4'};
				printDocto.onclick = function () { 
				
					let el_docto = document.getElementById('obj' + id); //antes era doc + id
					let el_docto_conteudo = el_docto.contentDocument || el_docto.contentWindow.document;
					if (!el_docto_conteudo) { return }					
					let pagina = el_docto_conteudo.querySelector('html');
					pagina.dispatchEvent(simularTecla('keydown',80, true));
					 
				};
			}			
			
			let i_printDocto = document.createElement("i");
			i_printDocto.className = "fas fa-print";
			printDocto.appendChild(i_printDocto);
			barra_zoom.appendChild(printDocto);
			
			
			//cria o botão miniaturas
			let miniatura = document.createElement('button');
			miniatura.id = 'maisPje_miniaturas';
			miniatura.setAttribute('maisPje-tooltip-direita','Exibir miniaturas');
			miniatura.className = 'mat-icon-button';
			miniatura.style = 'font-size: 1.5em; color: orangered; opacity: 0.4; margin-top: 5px;';
			
			if (!document.getElementById('obj' + id)) {
				
				miniatura.style.color = 'lightgrey';
				miniatura.setAttribute('maisPje-tooltip-direita','modo de miniatura desativado (modelo de documento antigo)');
				
			} else {
				
				miniatura.onmouseenter = function () {miniatura.style.opacity  = '1'};
				miniatura.onmouseleave = function () {miniatura.style.opacity  = '0.4'};
				miniatura.onmousedown = function () { 
					
					let el_docto = document.getElementById('obj' + id); //antes era doc + id
					let el_docto_conteudo = el_docto.contentDocument || el_docto.contentWindow.document;
					if (!el_docto_conteudo) { return }					
					let pagina = el_docto_conteudo.querySelector('html');
					pagina.dispatchEvent(simularTecla('keydown',115));
					iniciaMonitorDeCarregamentoDoDocto(id, null, true); //mapear ids
					pagina.querySelector('div[id="sidebarContainer"]').onmouseleave = function () {
						pagina.dispatchEvent(simularTecla('keydown',115))
						iniciaMonitorDeCarregamentoDoDocto(id, null, true); //mapear ids
					};
					 
				};
			}
			
			let i_miniatura = document.createElement("i");
			i_miniatura.className = "fas fa-layer-group";
			miniatura.appendChild(i_miniatura);
			barra_zoom.appendChild(miniatura);
			
			//cria o botão zoom +
			let zoomMais = document.createElement('button');
			zoomMais.id = 'maisPje_zoomMais';
			zoomMais.setAttribute('maisPje-tooltip-direita','Aumentar zoom');
			zoomMais.className = 'mat-icon-button';
			zoomMais.style = 'font-size: 1.5em; color: orangered; opacity: 0.4; margin-top: 5px;';
			zoomMais.onmouseenter = function () {zoomMais.style.opacity  = '1'};
			zoomMais.onmouseleave = function () {zoomMais.style.opacity  = '0.4'};
			zoomMais.onmousedown = function () {
				
				let el_docto = document.getElementById('obj' + id); //antes era doc + id
				if (el_docto) { //MODELO DE DOCUMENTO ATUAL
				
					let el_docto_conteudo = el_docto.contentDocument || el_docto.contentWindow.document;
					if (!el_docto_conteudo) { return }					
					let pagina = el_docto_conteudo.querySelector('html');
					pagina.dispatchEvent(simularTecla('keydown',107, true));
					
					let check = setInterval(function() { pagina.dispatchEvent(simularTecla('keydown',107, true)) }, 100);
					this.onmouseup = function (e) { clearInterval(check); this.onmouseup = null; }
					this.onmouseleave = function (e) { 
						clearInterval(check); 
						this.style.opacity  = '0.4'; 
						this.onmouseleave = function () {this.style.opacity  = '0.4'}
					}
					
				} else { //MODELO DE DOCUMENTO ANTIGO
					let check = setInterval(function() { zoom(document.getElementById('obj' + id), true, '0.05') }, 100);
					this.onmouseup = function (e) { clearInterval(check); this.onmouseup = null; }
					this.onmouseleave = function (e) { 
						clearInterval(check); 
						this.style.opacity  = '0.4'; 
						this.onmouseleave = function () {this.style.opacity  = '0.4'}
					}
				}
				
			};			
			let i_zoomMais = document.createElement("i");
			i_zoomMais.className = "fa fa-search-plus";
			zoomMais.appendChild(i_zoomMais);
			barra_zoom.appendChild(zoomMais);
			
			//cria o botão zoom -
			let zoomMenos = document.createElement('button');
			zoomMenos.id = 'maisPje_zoomMenos';
			zoomMenos.setAttribute('maisPje-tooltip-direita','Diminuir zoom');
			zoomMenos.className = 'mat-icon-button';		
			zoomMenos.style = 'font-size: 1.5em; color: orangered; opacity: 0.4; margin-top: 5px;';
			zoomMenos.onmouseenter = function () {zoomMenos.style.opacity  = '1'};
			zoomMenos.onmouseleave = function () {zoomMenos.style.opacity  = '0.4'};
			zoomMenos.onmousedown = function () {
				
				let el_docto = document.getElementById('obj' + id); //antes era doc + id
				if (el_docto) { //MODELO DE DOCUMENTO ATUAL
				
					let el_docto = document.getElementById('obj' + id); //antes era doc + id
					let el_docto_conteudo = el_docto.contentDocument || el_docto.contentWindow.document;
					if (!el_docto_conteudo) { return }					
					let pagina = el_docto_conteudo.querySelector('html');
					
					let check = setInterval(function() { pagina.dispatchEvent(simularTecla('keydown',109, true)) }, 100);
					this.onmouseup = function (e) { clearInterval(check); this.onmouseup = null; }
					this.onmouseleave = function (e) { 
						clearInterval(check); 
						this.style.opacity  = '0.4'; 
						this.onmouseleave = function () {this.style.opacity  = '0.4'}
					}
					
				} else { //MODELO DE DOCUMENTO ANTIGO
					let check = setInterval(function() { zoom(document.getElementById('obj' + id), false, '0.05') }, 100);
					this.onmouseup = function (e) { clearInterval(check); this.onmouseup = null; }
					this.onmouseleave = function (e) { 
						clearInterval(check); 
						this.style.opacity  = '0.4'; 
						this.onmouseleave = function () {this.style.opacity  = '0.4'}
					}
				}
				
			};
			let i_zoomMenos = document.createElement("i");
			i_zoomMenos.className = "fa fa-search-minus";
			zoomMenos.appendChild(i_zoomMenos);
			barra_zoom.appendChild(zoomMenos);
			
			//cria o botão enviar email
			let sendMail = document.createElement('button');
			sendMail.id = 'extensaoPje_enviarEmail';
			sendMail.setAttribute('maisPje-tooltip-direita','Enviar por email');
			sendMail.className = 'mat-icon-button';		
			sendMail.style = 'font-size: 1.5em; color: orangered; opacity: 0.4; margin-top: 5px;';
			sendMail.onmouseenter = function () {sendMail.style.opacity  = '1'};
			sendMail.onmouseleave = function () {sendMail.style.opacity  = '0.4'};
			sendMail.onclick = function () {mailto(document.querySelector('pje-historico-scroll-titulo'))};
			let i_sendMail = document.createElement("i");
			i_sendMail.className = "fas fa-envelope";
			sendMail.appendChild(i_sendMail);
			barra_zoom.appendChild(sendMail);
			
			//cria o botão enviar whatsapp
			let sendWA = document.createElement('button');
			sendWA.id = 'extensaoPje_enviarWA';
			sendWA.setAttribute('maisPje-tooltip-direita','Enviar por Whattsapp');
			sendWA.className = 'mat-icon-button';		
			sendWA.style = 'font-size: 1.5em; color: orangered; opacity: 0.4; margin-top: 5px;';
			sendWA.onmouseenter = function () {sendWA.style.opacity  = '1'};
			sendWA.onmouseleave = function () {sendWA.style.opacity  = '0.4'};
			sendWA.onclick = function () {wato(document.querySelector('pje-historico-scroll-titulo'))};
			let i_sendWA = document.createElement("i");
			i_sendWA.className = "fab fa-whatsapp-square";
			sendWA.appendChild(i_sendWA);
			barra_zoom.appendChild(sendWA);
			
			if (preferencias.mapeamentoDeIDs) {
				//cria o botão para mapear os ids
				let mapearIds = document.createElement('button');
				mapearIds.id = 'extensaoPje_mapearIds';
				mapearIds.setAttribute('maisPje-tooltip-direita','Mapear Ids');
				mapearIds.className = 'mat-icon-button';		
				mapearIds.style = 'font-size: 1.5em; color: orangered; opacity: 0.4; margin-top: 5px;';
				mapearIds.onmouseenter = function () {mapearIds.style.opacity  = '1'};
				mapearIds.onmouseleave = function () {mapearIds.style.opacity  = '0.4'};
				mapearIds.onclick = function () {
					//CONVERTER IDS EM LINKS
					let el_docto = document.getElementById('obj' + id); //antes era doc + id
					//MODELO DE DOCUMENTO ATUAL
					if (el_docto) {					
						let el_docto_conteudo = el_docto.contentDocument || el_docto.contentWindow.document;
						if (!el_docto_conteudo) { return }
						
						//cria o onkeydow listener para o documento do processo pois o listener tradicional "desaparece" no iframe
						el_docto_conteudo.addEventListener('keydown', async function(event) {
							if (event.code === "F1") {
								event.preventDefault();
								event.stopPropagation();
								consultaRapidaPJE();	
							} else if (event.code === "F2") {
								event.preventDefault();
								event.stopPropagation();
								if (!preferencias.tempF2 || preferencias.tempF2 == "Nenhum") {
									await clicarBotao('menumaispje span[id="maisPje_menuKaizen_itemmenu_preferencia_f2"] a', null, 1000);
								} else {
									acao_vinculo(preferencias.tempF2);
								}
							} else if (event.code === "F3") {
								event.preventDefault();
								event.stopPropagation();
								if (!preferencias.tempF3 || preferencias.tempF3 == "Nenhum") {
									await clicarBotao('menumaispje span[id="maisPje_menuKaizen_itemmenu_preferencia_f3"] a', null, 1000);
								} else {
									acao_vinculo(preferencias.tempF3);
								}
							
							}
						});
						
						
						let qtdePaginas = el_docto_conteudo.querySelectorAll('div[class="page"]').length;
						console.log("Extensão maisPJE (" + agora() + "): Mapeando Ids do Documento Id " + getId() + ": " + qtdePaginas + " página(s)");
						console.log("    |___Modelo de Documento: padrão atual");
						
						//CONSULTA AS PAGINAS DO DOCUMENTO PARA CONVERSÃO. SE EXISTEM PÁGINAS PENDENTES DE CARREGAMENTO INICIA O MONITOR.
						let elem = el_docto_conteudo.querySelectorAll('div[class="page"]');
						for (let i = 0; i < qtdePaginas; i++) {
							if (elem[i].getAttribute('data-loaded')) { //a página está carregada?
								if (!elem[i].getAttribute('converterIdsEmLinks')) { //a página já foi convertida?
									console.log("    |___Página " + (i+1) + " mapeada.")
									converterIdsEmLinks(elem[i], id, false);
								}
							} else { //identificado que existe página que ainda não foi carregada
								console.log("   |___Existem páginas com carregamento pendente. Iniciar monitoramento.");
								iniciaMonitorDeCarregamentoDoDocto(id, qtdePaginas);
								break;
							}
							
							//remove os links do sentença digital
							let linksSentençaDigital = el_docto_conteudo.querySelectorAll('div[class="annotationLayer"] section');
							if (linksSentençaDigital) {
								let map = [].map.call(
									linksSentençaDigital, 
									function(item) {
										item.remove();
									}
								);
							}

							//informa ao ícone que a funcionalidade foi ativada
							mapearIds.style.color = "green";
							mapearIds.setAttribute('maisPje-tooltip-direita','Ids mapeados');
						}
						
						//CRIA O LISTENER DE CLIQUE PARA O DOCUMENTO (IFRAME)
						el_docto_conteudo.body.addEventListener('click', function(event) {
							//DESCRIÇÃO: CASO O LINK DO ID (FUNÇÃO converterIdsEmLinks()) SEJA CLICADO	
							listenerClickIdConvertido(event);
						});
						
					//MODELO DE DOCUMENTO ANTIGO
					} else {					
						console.log("Extensão maisPJE (" + agora() + "): Mapeando Ids do Documento Id " + getId());
						console.log("    |___Modelo de Documento: padrão antigo");
						converterIdsEmLinks(document.querySelector('mat-card-content[class*="conteudo-html"]'), id, true);
						
						//informa ao ícone que a funcionalidade foi ativada
						mapearIds.style.color = "green";
						mapearIds.setAttribute('maisPje-tooltip-direita','Ids mapeados');
						
						document.querySelector('pje-historico-scroll-documento').addEventListener('click', function(event) {
							//DESCRIÇÃO: CASO O LINK DO ID (FUNÇÃO converterIdsEmLinks()) SEJA CLICADO
							listenerClickIdConvertido(event);
						});
					}
					
					function listenerClickIdConvertido(event) {
						if (event.target.tagName == "BUTTON" || event.target.tagName == "A") {
							if (!event.target.id) {
								return
							}
							let codigoId = event.target.id;
							if (codigoId.search("extensaoPje_documento_linkId_") > -1) {
								codigoId = codigoId.replace("extensaoPje_documento_linkId_","")
								let idProcesso = document.location.href.substring(document.location.href.search("/processo/")+10, document.location.href.search("/detalhe"));
								abrirDocumentoPeloId(idProcesso, codigoId);
							}
						}
					}
				};
				let i_mapearIds = document.createElement("i");
				i_mapearIds.className = "fas fa-square";
				let span_mapearIds = document.createElement("span");
				span_mapearIds.innerText = "#id";
				span_mapearIds.style = 'font-size: .5em; color: white; margin-top: 5px; position: absolute; top: 0.3em; left: 1em;';
				i_mapearIds.appendChild(span_mapearIds);
				mapearIds.appendChild(i_mapearIds);
				barra_zoom.appendChild(mapearIds);
				


				await sleep(2000); 
				await clicarBotao('button[id="extensaoPje_mapearIds"]');
			}
			
			function getId() {
				let el = document.querySelector('pje-historico-scroll-titulo');
				if (!el) {return}
				let cabecalho = el.querySelector('mat-card-title').innerText;//FIXME: da erro qdo a opcao de recolher cabecalho eh true.
				let idDocumento = cabecalho.substring(cabecalho.search("Id ")+3, cabecalho.search(" - "));
				return idDocumento;
			}
			
		}
	}
}

//FUNÇÃO RESPONSÁVEL POR MONITORAR O CARREGAMENTO DO DOCUMENTO (IFRAME) E A CADA PÁGINA CONVERTER OS IDS ENCONTRADOS
function iniciaMonitorDeCarregamentoDoDocto(id, qtdePaginas, miniatura=false) {
	let el_docto = document.getElementById('obj' + id); // antes era doc + id
	let el_docto_conteudo = el_docto.contentDocument || el_docto.contentWindow.document;
	let totalPaginas = (qtdePaginas) ? qtdePaginas : el_docto_conteudo.querySelectorAll('div[class="page"]').length;
	console.log('totalPaginas: ' + totalPaginas);
	let targetDocumento = el_docto_conteudo.body;
	let observerDocumento = new MutationObserver(function(mutationsDocumento) {
		mutationsDocumento.forEach(function(mutation) {
			if (!mutation.target.tagName) { return }
			// console.log("*****************************[ADD] " + mutation.target.tagName);
			// console.log("*****************************[ADD] " + mutation.target.className);
			// console.log("-----------------Aviso: " + mutation.target.innerText);
			
			if (mutation.target.tagName == "DIV" && mutation.target.className == "textLayer") {
				if (!mutation.addedNodes[0]) {
					return;
				}				
				if (!mutation.addedNodes[0].className) {
					return;
				} else if (mutation.addedNodes[0].className == "endOfContent") { //fim do carregamento da página
					let pagina = parseInt(mutation.target.parentElement.getAttribute('data-page-number'));
					
					if (miniatura) {
						if (mutation.target.parentElement.getAttribute('data-loaded')) {
							converterIdsEmLinks(mutation.target.parentElement, id, false);
							console.log("    |___Página " + pagina + " mapeada.")
						}
					} else {
						if (mutation.target.parentElement.getAttribute('data-loaded') && !mutation.target.parentElement.getAttribute('converterIdsEmLinks')) {
							converterIdsEmLinks(mutation.target.parentElement, id, false);
							console.log("    |___Página " + pagina + " mapeada.")
						}
					}
					
					if (pagina >= qtdePaginas) {
						observerDocumento.disconnect();
					}					
				}
			}
		});
	});		
	let configDocumento = { childList: true, characterData: true, subtree:true }
	observerDocumento.observe(targetDocumento, configDocumento); //inicia o MutationObserver
	
}

//FUNÇÃO RESPONSÁVEL POR CONVERTER OS IDS ENCONTRADOS NO TEOR DO DOCUMENTO EM LINKS
function converterIdsEmLinks(el, id_documento, antigo) {
	// console.log("    |___Extensão maisPJE (" + agora() + "): converterIdsEmLinks(" + id_documento + ")");
	if (!el) {
		return
	}
	
	let texto, codigo, el_docto_conteudo;
	let listaIds = [];
	let listaIds_Novo = [];
	
	if (antigo) {
		texto = el.innerText;
		codigo = el.innerHTML;

		Promise.all([buscaIds(texto)]).then(values => {
			gerarLinksDosIds(el, listaIds_Novo, '#da70d66e')
		// 	listaIds_Novo.forEach(function (item, indice) {
		// 		let regexId = new RegExp(item,"g");
		// 		codigo = codigo.replace(regexId,'<a title="Abrir documento" id="extensaoPje_documento_linkId_' + item + '" style="background-color: #da70d66e;cursor: pointer;">' +  item + '</a>');
		// 	});
			
			// el.innerHTML = codigo;
		});
	} else {
		let elemento = el.getElementsByClassName('textLayer')[0];
		texto = elemento.innerText.replace(/\s{2,}/g, ' '); //tira os espaços em branco duplicados
		texto = texto.replace(/(\r\n|\n|\r)/gm, " "); //substitui as quebras de linha
		Promise.all([buscaIds(texto)]).then(values => {
			gerarLinksDosIds(elemento, listaIds_Novo, '#d236c9')

			// codigo = elemento.innerHTML;
			// listaIds_Novo.forEach(function (item, indice) {
			// 	let regexId = new RegExp(item,"g");
			// 	codigo = codigo.replace(regexId,'<a title="Abrir documento" id="extensaoPje_documento_linkId_' + item + '" style="background-color: #d236c9;cursor: pointer;">' +  item + '</a>');
			// });
			elemento.parentElement.setAttribute('converterIdsEmLinks', true);
			// elemento.innerHTML = codigo;
		});
	}
	
	function buscaIds(txt) {
		//PRIMEIRO PADRÃO (ID.XXXXXXX ou ID:XXXXXXX ou ID XXXXXXX ou ID. XXXXXXX ou ID: XXXXXXX)
		let padrao = /i{1}d{1}[.| |:]{1,}[A-Za-z0-9]{7}/gmi;
		while ((myArray = padrao.exec(txt)) !== null) {
			let id = myArray[0].match(new RegExp('[A-Za-z0-9]{7}','gmi')).join();
			// console.log('Encontrado1: ' + myArray[0] + " - " + id);
			listaIds.push(id);
		}
		
		//SEGUNDO PADRÃO (ID do mandado. XXXXXXX ou ID do mandado: XXXXXXX ou ID do mandado XXXXXXX)
		padrao = /ID do mandado[.| |:]{1,}[A-Za-z0-9]{7}/gmi;
		while ((myArray = padrao.exec(txt)) !== null) {
			let id = myArray[0].match(new RegExp('[A-Za-z0-9]{7}','gmi')).join();
			// console.log('Encontrado2: ' + myArray[0] + " - " + id);
			let idFiltrado = id.split(',').filter(filtro => filtro != 'mandado');
			listaIds.push(idFiltrado);
		}
		
		//MÉTODO PARA EXCLUIR OS IDs DUPLICADOS
		listaIds_Novo = listaIds.filter((id, i) => listaIds.indexOf(id) === i);
	}
}

//FUNÇÃO RESPONSÁVEL POR APLICAR O ZOOM NO DOCUMENTO
function zoom(documento, aumentar, percentual) {
	//DESCRIÇÃO: aplica zoom no documento que está no padrão antigo
	if (!documento) {
		if (document.querySelector('mat-card-content[class*="conteudo-html"')) {
			documento = document.querySelector('mat-card-content[class*="conteudo-html"');
			let tamanho = !documento.style.getPropertyValue('font-size-adjust') ? '0.54' : documento.style.getPropertyValue('font-size-adjust');
			if (aumentar) {
				tamanho = parseFloat(tamanho) + (parseFloat(tamanho) * parseFloat(percentual));
			} else {
				tamanho = parseFloat(tamanho) - (parseFloat(tamanho) * parseFloat(percentual));
			}
			documento.style.setProperty('font-size-adjust', tamanho, 'important');
		}
		return;
	
	//DESCRIÇÃO: aplica zoom no documento que está no padrão novo
	} else {
		let ancora = documento.contentDocument || documento.contentWindow.document;
		let el_docto_conteudo = ancora.getElementById('viewer'); //document.querySelector('pdf-viewer')
		if (!el_docto_conteudo) { return }		
		let tamanhoAtual = !el_docto_conteudo.style.scale ? 1 : el_docto_conteudo.style.scale;
		el_docto_conteudo.style.transformOrigin = "left top";
		if (aumentar) {
			el_docto_conteudo.style.scale = parseFloat(tamanhoAtual) + parseFloat(percentual);
		} else {
			el_docto_conteudo.style.scale = parseFloat(tamanhoAtual) - parseFloat(percentual);
		}
	}
}

//FUNÇÃO RESPONSÁVEL POR ENVIAR O DOCUMENTO ATIVO POR EMAIL
async function mailto(el) {	
	//verifica se o cabeçalho está escondido (colapsado). Se sim, tem que exibi-lo para montar o documento
	if (!el.querySelector('mat-card-title')) { 
		await exibirCabecalho();
		el = await esperarElemento('pje-historico-scroll-titulo');
	}

	//RECUPERA VARIÁVEIS
	let proc = await obterNumeroDoProcessoNaTela();
	if (!proc) { return }
	
	let cabecalho, tipoDocumento, idDocumento, autenticacao, chave;
	let nomePartes = document.querySelector('section[class*="partes"]').innerText;
	nomePartes = nomePartes.replace(new RegExp('&', 'g'), '%26');
	let dt_audi = document.querySelector('pje-resumo-processo').innerText;
	
	if (dt_audi.search("Audiência:") > -1) {
		dt_audi = dt_audi.substring(dt_audi.search("Audiência:")+11,dt_audi.search("Distribuído:"));
	} else {
		dt_audi = "Não há audiência marcada neste processo";
	}
	
	if (!preferencias.versaoPje) { preferencias.versaoPje = await obterVersaoPjeNaTela() }

	if (preferencias.versaoPje.includes('2.1')) {
		
		cabecalho = el.innerText.split("\n");
		
		// let teste = cabecalho.split("\n");
		// console.log("linha1: " + teste[0])
		// console.log("linha2: " + teste[1])
		// console.log("linha3: " + teste[2])
		
		
		//linha 1:  Id 786bbdc - Despacho
		let padraoID = /i{1}d{1}[.| |:]{1,}[A-Za-z0-9]{7}/gmi;
		idDocumento = cabecalho[0].match(padraoID).join();
		tipoDocumento = cabecalho[0].substring(cabecalho[0].search(" - ")+3, cabecalho[0].length);
		
		//linha 2: Juntado por FERNANDO DE MEDEIROS MARCON em 27/11/2023 10:56
				
		//linha 3: Número do documento: 23112416585043800000060186505      ///link de autenticação: https://pje.trt12.jus.br/pjekz/validacao/23112416585043800000060186505?instancia=1
		chave = cabecalho[2].match(new RegExp('\\d{29}','g'))[0];                                // https://pje.trt12.jus.br/pjekz/processo/678393/detalhe
		autenticacao = 'https://' + preferencias.trt + '/pjekz/validacao/' + chave + ((preferencias.grau_usuario == "primeirograu") ? '?instancia=1' :  '?instancia=2');
		
	} else {
		
		cabecalho = el.querySelector('mat-card-title').innerText;
		tipoDocumento = cabecalho.substring(cabecalho.search(" - ")+3, cabecalho.search(".pdf") > -1 ? cabecalho.search(".pdf") : cabecalho.length);
		idDocumento = cabecalho.substring(cabecalho.search("Id ")+3, cabecalho.search(" - "));
		cabecalho = el.querySelector('div[class*="cabecalho-central"]').innerText;
		autenticacao = cabecalho.substring(cabecalho.search("https://"));
		chave = cabecalho.match(new RegExp('\\d{29}','g'))[0];
		
	}
	
	// console.log('cabecalho: ' + cabecalho);
	// console.log('tipoDocumento: ' + tipoDocumento);
	// console.log('idDocumento: ' + idDocumento);
	// console.log('autenticacao: ' + autenticacao);
	// console.log('chave: ' + chave);
	
	//CRIAR TITULO
	let titulo = preferencias.emailAutomatizado.titulo;
	titulo = titulo.replace(new RegExp('#{processo}', 'g'), proc);
	titulo = titulo.replace(new RegExp('#{tipoDocumento}', 'g'), tipoDocumento);
	titulo = titulo.replace(new RegExp('#{idDocumento}', 'g'), idDocumento);
	titulo = titulo.replace(new RegExp('#{autenticacao}', 'g'), autenticacao);
	titulo = titulo.replace(new RegExp('#{servidor}', 'g'), preferencias.nm_usuario);
	titulo = titulo.replace(new RegExp('#{OJServidor}', 'g'), preferencias.oj_usuario);
	titulo = titulo.replace(new RegExp('#{partes}', 'g'), nomePartes);
	titulo = titulo.replace(new RegExp('#{dados_audi}', 'g'), dt_audi);
	titulo = titulo.replace(new RegExp('#{chave}', 'g'), chave);
	
	//CRIAR CORPO
	let corpo = preferencias.emailAutomatizado.corpo;
	corpo = corpo.replace(new RegExp('#{processo}', 'g'), proc);
	corpo = corpo.replace(new RegExp('#{tipoDocumento}', 'g'), tipoDocumento);
	corpo = corpo.replace(new RegExp('#{idDocumento}', 'g'), idDocumento);
	corpo = corpo.replace(new RegExp('#{autenticacao}', 'g'), autenticacao);
	corpo = corpo.replace(new RegExp('#{servidor}', 'g'), preferencias.nm_usuario);
	corpo = corpo.replace(new RegExp('#{OJServidor}', 'g'), preferencias.oj_usuario);
	corpo = corpo.replace(new RegExp('#{partes}', 'g'), nomePartes);
	corpo = corpo.replace(new RegExp('#{dados_audi}', 'g'), dt_audi);
	corpo = corpo.replace(new RegExp('#{chave}', 'g'), chave);
	
	//CRIAR ASSINATURA
	let assinatura = preferencias.emailAutomatizado.assinatura;
	assinatura = assinatura.replace(new RegExp('#{processo}', 'g'), proc);
	assinatura = assinatura.replace(new RegExp('#{tipoDocumento}', 'g'), tipoDocumento);
	assinatura = assinatura.replace(new RegExp('#{idDocumento}', 'g'), idDocumento);
	assinatura = assinatura.replace(new RegExp('#{autenticacao}', 'g'), autenticacao);
	assinatura = assinatura.replace(new RegExp('#{servidor}', 'g'), preferencias.nm_usuario);
	assinatura = assinatura.replace(new RegExp('#{OJServidor}', 'g'), preferencias.oj_usuario);
	assinatura = assinatura.replace(new RegExp('#{partes}', 'g'), nomePartes);
	assinatura = assinatura.replace(new RegExp('#{dados_audi}', 'g'), dt_audi);
	assinatura = assinatura.replace(new RegExp('#{chave}', 'g'), chave);
	
	corpo += escape('\r\n\r\n') + assinatura;
	corpo = corpo.replace(/(\r\n|\n|\r)/gm, "%0D%0A");
	
	// iframe.src = "mailto:?subject=" + titulo + "&body=" + corpo;
	// document.body.appendChild(iframe);
	
	browser.runtime.sendMessage({tipo: 'criarJanela', url: 'mailto:?subject=' + titulo + '&body=' + corpo});
}

//FUNÇÃO RESPONSÁVEL POR ENVIAR O DOCUMENTO ATIVO POR WHATTSAPPWEB
async function wato(el) {	
	//verifica se o cabeçalho está escondido (colapsado). Se sim, tem que exibi-lo para montar o documento
	if (!el.querySelector('mat-card-title')) { 
		await exibirCabecalho();
		el = await esperarElemento('pje-historico-scroll-titulo');
	}
	
	//RECUPERA VARIÁVEIS
	let proc = await obterNumeroDoProcessoNaTela();
	if (!proc) { return }
	
	let cabecalho, tipoDocumento, idDocumento, autenticacao, chave;
	let nomePartes = document.querySelector('section[class*="partes"]').innerText;
	nomePartes = nomePartes.replace(new RegExp('&', 'g'), '%26');
	let dt_audi = document.querySelector('pje-resumo-processo').innerText;
	
	if (dt_audi.search("Audiência:") > -1) {
		dt_audi = dt_audi.substring(dt_audi.search("Audiência:")+11,dt_audi.search("Distribuído:"));
	} else {
		dt_audi = "Não há audiência marcada neste processo";
	}
	
	if (!preferencias.versaoPje) { preferencias.versaoPje = await obterVersaoPjeNaTela() }

	if (preferencias.versaoPje.includes('2.1')) {
		
		cabecalho = el.innerText.split("\n");
		
		// let teste = cabecalho.split("\n");
		// console.log("linha1: " + teste[0])
		// console.log("linha2: " + teste[1])
		// console.log("linha3: " + teste[2])
		
		
		//linha 1:  Id 786bbdc - Despacho
		let padraoID = /i{1}d{1}[.| |:]{1,}[A-Za-z0-9]{7}/gmi;
		idDocumento = cabecalho[0].match(padraoID).join();
		tipoDocumento = cabecalho[0].substring(cabecalho[0].search(" - ")+3, cabecalho[0].length);
		
		//linha 2: Juntado por FERNANDO DE MEDEIROS MARCON em 27/11/2023 10:56
				
		//linha 3: Número do documento: 23112416585043800000060186505      ///link de autenticação: https://pje.trt12.jus.br/pjekz/validacao/23112416585043800000060186505?instancia=1
		chave = cabecalho[2].match(new RegExp('\\d{29}','g'))[0];                                // https://pje.trt12.jus.br/pjekz/processo/678393/detalhe
		autenticacao = 'https://' + preferencias.trt + '/pjekz/validacao/' + chave + ((preferencias.grau_usuario == "primeirograu") ? '?instancia=1' :  '?instancia=2');
		
	} else {
		
		cabecalho = el.querySelector('mat-card-title').innerText;
		tipoDocumento = cabecalho.substring(cabecalho.search(" - ")+3, cabecalho.search(".pdf") > -1 ? cabecalho.search(".pdf") : cabecalho.length);
		idDocumento = cabecalho.substring(cabecalho.search("Id ")+3, cabecalho.search(" - "));
		cabecalho = el.querySelector('div[class*="cabecalho-central"]').innerText;
		autenticacao = cabecalho.substring(cabecalho.search("https://"));
		chave = cabecalho.match(new RegExp('\\d{29}','g'))[0];
		
	}
	
	// console.log('cabecalho: ' + cabecalho);
	// console.log('tipoDocumento: ' + tipoDocumento);
	// console.log('idDocumento: ' + idDocumento);
	// console.log('autenticacao: ' + autenticacao);
	// console.log('chave: ' + chave);	
	
	//CRIAR CORPO
	let corpo = preferencias.emailAutomatizado.corpo;
	corpo = corpo.replace(new RegExp('#{processo}', 'g'), proc);
	corpo = corpo.replace(new RegExp('#{tipoDocumento}', 'g'), tipoDocumento);
	corpo = corpo.replace(new RegExp('#{idDocumento}', 'g'), idDocumento);
	corpo = corpo.replace(new RegExp('#{autenticacao}', 'g'), autenticacao);
	corpo = corpo.replace(new RegExp('#{servidor}', 'g'), preferencias.nm_usuario);
	corpo = corpo.replace(new RegExp('#{OJServidor}', 'g'), preferencias.oj_usuario);
	corpo = corpo.replace(new RegExp('#{partes}', 'g'), nomePartes);
	corpo = corpo.replace(new RegExp('#{dados_audi}', 'g'), dt_audi);
	corpo = corpo.replace(new RegExp('#{chave}', 'g'), chave);
	
	//CRIAR ASSINATURA
	let assinatura = preferencias.emailAutomatizado.assinatura;
	assinatura = assinatura.replace(new RegExp('#{processo}', 'g'), proc);
	assinatura = assinatura.replace(new RegExp('#{tipoDocumento}', 'g'), tipoDocumento);
	assinatura = assinatura.replace(new RegExp('#{idDocumento}', 'g'), idDocumento);
	assinatura = assinatura.replace(new RegExp('#{autenticacao}', 'g'), autenticacao);
	assinatura = assinatura.replace(new RegExp('#{servidor}', 'g'), preferencias.nm_usuario);
	assinatura = assinatura.replace(new RegExp('#{OJServidor}', 'g'), preferencias.oj_usuario);
	assinatura = assinatura.replace(new RegExp('#{partes}', 'g'), nomePartes);
	assinatura = assinatura.replace(new RegExp('#{dados_audi}', 'g'), dt_audi);
	assinatura = assinatura.replace(new RegExp('#{chave}', 'g'), chave);
	
	corpo += escape('\r\n\r\n') + assinatura;
	corpo = corpo.replace(/(\r\n|\n|\r)/gm, "%0D%0A");
	let fone = "";
	// fone = prompt("Informe o telefone do destinatário observando o padrão 550DDDTELEFONE\nPor exemplo: Telefone +55 (48) 12345-6789 = 55048123456789\n", fone);
	fone = await criarCaixaDePergunta('text', "Informe o telefone do destinatário observando o padrão 550DDDTELEFONE\nPor exemplo: Telefone +55 (48) 12345-6789 = 55048123456789\n", fone);
	if (!fone) {
		return
	}
	// let winGigs = window.open("https://web.whatsapp.com/send?phone=" + fone + "&text=" + corpo + "&app_absent=0", '_blank');
	browser.runtime.sendMessage({tipo: 'criarJanela', url: "https://web.whatsapp.com/send?phone=" + fone + "&text=" + corpo + "&app_absent=0"});
}

//FUNÇÃO RESPONSÁVEL POR ABRIR UM MENU PARA ASSISTENCIA NA TELA DO SISBAJUD
function menuConvenios(nome_convenio,executar_funcao='') {
	if (!document.getElementById('maisPje_menuKaizen')) {
		//CARREGA O PACOTE DE ÍCONES PARA A PÁGINA E O CSS DO MENU
		browser.runtime.sendMessage({tipo: 'insertCSS', file: 'maisPje_icones.css'});
		browser.runtime.sendMessage({tipo: 'insertCSS', file: 'maisPje_menu.css'});
		
		//DESCRIÇÃO: REGRA DO TOOLTIP
		if (!document.getElementById('maisPje_tooltip_esquerda')) {
			tooltip('esquerda');
		}
		
		//criar estrutura do menuConvenios
		let menuMaisPje = document.createElement("menumaispje");
		menuMaisPje.id = "maisPje_menuKaizen";
		menuMaisPje.className = 'maisPje-no-print';
		menuMaisPje.draggable = true;
		
		let menuMaisPje_content = document.createElement("div");
		menuMaisPje_content.id = "maisPje_menuKaizen_content";
		menuMaisPje_content.className = "menuMaisPje-content";
		
		let toggle_btn = document.createElement("div");
		toggle_btn.className = "toggle-btn";
		
		let img = document.createElement("img");
		img.draggable = false;
		img.className = "maisPje-img";
		img.src = browser.runtime.getURL("icons/ico_32.png");
		
		toggle_btn.appendChild(img);
		menuMaisPje_content.appendChild(toggle_btn);
		menuMaisPje.appendChild(menuMaisPje_content);
		
		bt_atalhos();
		
		//posição inicial do menu
		browser.storage.local.get('menu_kaizen', function(result){
			let temp = result.menu_kaizen;
			if (!temp) { return }
			switch(nome_convenio) {
				case "SISBAJUD":
					menuMaisPje.style.left = !result.menu_kaizen.sisbajud ? '93%' : result.menu_kaizen.sisbajud.posx;
					menuMaisPje.style.top = !result.menu_kaizen.sisbajud ? '80%' : result.menu_kaizen.sisbajud.posy;
					break;
				case "SERASAJUD":
					menuMaisPje.style.left = !result.menu_kaizen.serasajud ? '93%' : result.menu_kaizen.serasajud.posx;
					menuMaisPje.style.top = !result.menu_kaizen.serasajud ? '80%' : result.menu_kaizen.serasajud.posy;
					break;
				case "RENAJUD" || "RENAJUDNOVO":
					menuMaisPje.style.left = !result.menu_kaizen.renajud ? '93%' : result.menu_kaizen.renajud.posx;
					menuMaisPje.style.top = !result.menu_kaizen.renajud ? '80%' : result.menu_kaizen.renajud.posy;
					break;
				case "RENAJUDNOVO":
					menuMaisPje.style.left = !result.menu_kaizen.renajud ? '93%' : result.menu_kaizen.renajud.posx;
					menuMaisPje.style.top = !result.menu_kaizen.renajud ? '80%' : result.menu_kaizen.renajud.posy;
					break;
				case "CNIB":
					menuMaisPje.style.left = !result.menu_kaizen.cnib ? '93%' : result.menu_kaizen.cnib.posx;
					menuMaisPje.style.top = !result.menu_kaizen.cnib ? '80%' : result.menu_kaizen.cnib.posy;
					break;
				case "CCS":
					menuMaisPje.style.left = !result.menu_kaizen.ccs ? '93%' : result.menu_kaizen.ccs.posx;
					menuMaisPje.style.top = !result.menu_kaizen.ccs ? '80%' : result.menu_kaizen.ccs.posy;
					break;
				case "PREVJUD":
					menuMaisPje.style.left = !result.menu_kaizen.prevjud ? '93%' : result.menu_kaizen.prevjud.posx;
					menuMaisPje.style.top = !result.menu_kaizen.prevjud ? '80%' : result.menu_kaizen.prevjud.posy;
					break;
				case "PROTESTOJUD":
					menuMaisPje.style.left = !result.menu_kaizen.protestojud ? '93%' : result.menu_kaizen.protestojud.posx;
					menuMaisPje.style.top = !result.menu_kaizen.protestojud ? '80%' : result.menu_kaizen.protestojud.posy;
					break;
				case "SNIPER":
					menuMaisPje.style.left = !result.menu_kaizen.sniper ? '93%' : result.menu_kaizen.sniper.posx;
					menuMaisPje.style.top = !result.menu_kaizen.sniper ? '80%' : result.menu_kaizen.sniper.posy;
					break;
				case "CENSEC":
					menuMaisPje.style.left = !result.menu_kaizen.censec ? '93%' : result.menu_kaizen.censec.posx;
					menuMaisPje.style.top = !result.menu_kaizen.censec ? '80%' : result.menu_kaizen.censec.posy;
					break;
				case "CELESC":
					menuMaisPje.style.left = !result.menu_kaizen.celesc ? '93%' : result.menu_kaizen.celesc.posx;
					menuMaisPje.style.top = !result.menu_kaizen.celesc ? '80%' : result.menu_kaizen.celesc.posy;
					break;
				case "CASAN":
					menuMaisPje.style.left = !result.menu_kaizen.casan ? '93%' : result.menu_kaizen.casan.posx;
					menuMaisPje.style.top = !result.menu_kaizen.casan ? '80%' : result.menu_kaizen.casan.posy;
					break;
				case "SIGEF":
					menuMaisPje.style.left = !result.menu_kaizen.sigef ? '93%' : result.menu_kaizen.sigef.posx;
					menuMaisPje.style.top = !result.menu_kaizen.sigef ? '80%' : result.menu_kaizen.sigef.posy;
					break;
				case "INFOSEG":
					menuMaisPje.style.left = !result.menu_kaizen.infoseg ? '93%' : result.menu_kaizen.infoseg.posx;
					menuMaisPje.style.top = !result.menu_kaizen.infoseg ? '80%' : result.menu_kaizen.infoseg.posy;
					break;
				case "AJJT":
					menuMaisPje.style.left = !result.menu_kaizen.ajjt ? '93%' : result.menu_kaizen.ajjt.posx;
					menuMaisPje.style.top = !result.menu_kaizen.ajjt ? '80%' : result.menu_kaizen.ajjt.posy;
					break;
			}
			setTimeout(function() {direcaoItensMenu()}, 500);
		});
		
		document.body.appendChild(menuMaisPje);
		
		//cria o eventlistener
		let posx,posy;
		//área de drop
		let area_da_tela = document.createElement('div');
		area_da_tela.id = "maisPje_menuKaizen_area_da_tela";
		area_da_tela.style="width: 100%;height: 100%;z-index: 999;position: absolute; display: none;top: 0px;"
		area_da_tela.ondragover = function(e) { 
			e.preventDefault();  
			e.dataTransfer.dropEffect = "move";
			posx = e.clientX;
			posy = e.clientY;
		}
		area_da_tela.ondrop = function(e) {  e.preventDefault();}		
		document.body.appendChild(area_da_tela);
		
		menuMaisPje.ondragstart = function() {
			area_da_tela.style.display = "flex";
		}
		
		menuMaisPje.ondragend = function() {
			area_da_tela.style.display = "none";
			menuMaisPje.style.top = (posy - 12) + "px";
			menuMaisPje.style.left = (posx - 12) + "px";
			direcaoItensMenu();
			let posmenu = window.getComputedStyle(document.querySelector("menumaispje"));
			browser.storage.local.get('menu_kaizen', function(result){
				let temp = result.menu_kaizen;
				if (!temp) { return }
				switch(nome_convenio) {
					case "SISBAJUD":
						temp.sisbajud.posx = parseInt(posmenu.left) + 'px';
						temp.sisbajud.posy = parseInt(posmenu.top) + 'px';
						break;
					case "SERASAJUD":
						temp.serasajud.posx = parseInt(posmenu.left) + 'px';
						temp.serasajud.posy = parseInt(posmenu.top) + 'px';
						break;
					case "RENAJUD":
						temp.renajud.posx = parseInt(posmenu.left) + 'px';
						temp.renajud.posy = parseInt(posmenu.top) + 'px';
						break;
					case "RENAJUDNOVO":
						temp.renajud.posx = parseInt(posmenu.left) + 'px';
						temp.renajud.posy = parseInt(posmenu.top) + 'px';
						break;
					case "CNIB":
						temp.cnib.posx = parseInt(posmenu.left) + 'px';
						temp.cnib.posy = parseInt(posmenu.top) + 'px';
						break;
					case "CCS":
						temp.ccs.posx = parseInt(posmenu.left) + 'px';
						temp.ccs.posy = parseInt(posmenu.top) + 'px';
						break;
					case "PREVJUD":
						temp.prevjud.posx = parseInt(posmenu.left) + 'px';
						temp.prevjud.posy = parseInt(posmenu.top) + 'px';
						break;
					case "SNIPER":
						temp.sniper.posx = parseInt(posmenu.left) + 'px';
						temp.sniper.posy = parseInt(posmenu.top) + 'px';
						break;
					case "CENSEC":
						temp.censec.posx = parseInt(posmenu.left) + 'px';
						temp.censec.posy = parseInt(posmenu.top) + 'px';
						break;
					case "CELESC":
						temp.celesc.posx = parseInt(posmenu.left) + 'px';
						temp.celesc.posy = parseInt(posmenu.top) + 'px';
						break;
					case "CASAN":
						temp.casan.posx = parseInt(posmenu.left) + 'px';
						temp.casan.posy = parseInt(posmenu.top) + 'px';
						break;
					case "SIGEF":
						temp.sigef.posx = parseInt(posmenu.left) + 'px';
						temp.sigef.posy = parseInt(posmenu.top) + 'px';
						break;
					case "INFOSEG":
						temp.infoseg.posx = parseInt(posmenu.left) + 'px';
						temp.infoseg.posy = parseInt(posmenu.top) + 'px';
						break;
					case "AJJT":
						temp.ajjt.posx = parseInt(posmenu.left) + 'px';
						temp.ajjt.posy = parseInt(posmenu.top) + 'px';
						break;
				}
				browser.storage.local.set({'menu_kaizen': temp});
			});
		}
		
		function direcaoItensMenu() {
			//o menu possui 390px de altura (30px por atalho)
			if (parseInt(window.getComputedStyle(menuMaisPje).top) < parseInt(window.innerHeight/2)) {//menu estiver na metade superior
				//menu abre para baixo
				let itensmenu = document.querySelectorAll('span[id*="maisPje_menuKaizen_itemmenu_"]');
				if (!itensmenu) { return }
				let map = [].map.call(
					itensmenu, 
					function(itemmenu) {
						itemmenu.style.setProperty("--d","1")
					}
				);
			} else {//menu estiver na metade superior
				//menu abre para cima
				let itensmenu = document.querySelectorAll('span[id*="maisPje_menuKaizen_itemmenu_"]');
				if (!itensmenu) { return }
				let map = [].map.call(
					itensmenu, 
					function(itemmenu) {
						itemmenu.style.setProperty("--d","-1")
					}
				);
			}
		}
		
		// console.log("preferencias.acionarKaizenComClique: " + preferencias.acionarKaizenComClique);
		let metodoAcionamento = (preferencias.acionarKaizenComClique) ? "click" : "mouseenter";
		toggle_btn.addEventListener(metodoAcionamento, () =>{
			menuMaisPje.classList.toggle("openv");
		});
		
		function bt_atalhos() {
			
			//BOTÃO CONSULTA RAPIDA DE PROCESSOS
			let atalho_consulta_rapida = criar_botao(
				"maisPje_menuKaizen_itemmenu_consulta_rapida",
				"1",
				"icone bolt t100 tamanho40",
				"Consultar Processo no PJe",
				"orangered",
				function () {consultaRapidaPJE()},
				"acionarMouseEmCima"
			)
			
			//BOTÃO NOVA MINUTA
			let atalho_nova_minuta = criar_botao(
				"maisPje_menuKaizen_itemmenu_nova_minuta",
				"2",
				"icone menuConvenio_add t100 tamanho70",
				"Nova Minuta",
				"orangered",
				function () { 
					switch(nome_convenio) {
						case "SISBAJUD":
							novaMinutaSisbajud();
							break;
						case "RENAJUDNOVO":
							novaMinutaRenajudNovo();
							break;
						case "SERASAJUD":
							novaMinutaSerasajud();
							break;
						case "AJJT":
							novaMinutaAJJT();
							break;
					}
				}
			)
			
			//BOTÃO PREENCHER CAMPOS
			let atalho_preencher_campos = criar_botao(
				"maisPje_menuKaizen_itemmenu_preencher_campos",
				"3",
				"icone menuConvenio_magic t100 tamanho70",
				"Preencher Campos com Polo Passivo",
				"orangered",
				function () {
					switch(nome_convenio) {
						case "SISBAJUD":
							preenchercamposSisbajud(0);
							break;
						case "SERASAJUD":
							preenchercamposSerasajud();
							break;
						case "RENAJUD":
							preenchercamposRenajud();
							break;
						case "RENAJUDNOVO":
							preenchercamposRenajudNovo();
							break;
						case "CNIB":
							preenchercamposCnib();
							break;
						case "CCS":
							preenchercamposCCS();
							break;
						case "PREVJUD":
							preenchercamposPREVJUD();
							break;
						case "PROTESTOJUD":
							preenchercamposPROTESTOJUD();
							break;
						case "SNIPER":
							preenchercamposSNIPER();
							break;
						case "CENSEC":
							preenchercamposCENSEC();
							break;
						case "CELESC":
							preenchercamposCELESC();
							break;
						case "CASAN":
							preenchercamposCASAN();
							break;
						case "SIGEF":
							preenchercamposSIGEF();
							break;
						case "INFOSEG":
							preenchercamposINFOSEG();
							break;
					}
				},
				"acionarMouseEmCima"
			)
			
			//BOTÃO PREENCHER CAMPOS INVERTIDO
			let atalho_preencher_campos_invertido = criar_botao(
				"maisPje_menuKaizen_itemmenu_preencher_camposinvertido",
				"3",
				"icone menuConvenio_magic t100 tamanho70",
				"Preencher Campos com Polo Ativo",
				"darkcyan",
				function () {
					switch(nome_convenio) {
						case "SISBAJUD":
							preenchercamposSisbajud(1);
							break;
						case "PREVJUD":
							preenchercamposPREVJUD(1);
							break;
					}
				},
				"acionarMouseEmCima"
			)
			
			//BOTÃO CONSULTAR MINUTA
			let atalho_consultar_minuta = criar_botao(
				"maisPje_menuKaizen_itemmenu_consultar_minuta",
				"5",
				"icone menuConvenio_search t100 tamanho70",
				"Consultar Minuta",
				"orangered",
				function () {
					switch(nome_convenio) {
						case "SISBAJUD":
							consultarMinutaSisbajud();
							break;
						case "SERASAJUD":
							consultarMinutaSerasajud();
							break;
						case "AJJT":
							consultarMinutaAJJT();
							break;
					}
				},
				"acionarMouseEmCima"
			)
			
			//BOTÃO CONSULTAR TEIMOSINHA
			let atalho_consultar_teimosinha = criar_botao(
				"maisPje_menuKaizen_itemmenu_consultar_TEIMOSINHA",
				"5",
				"icone menuConvenio_history t100 tamanho70",
				"Consultar Teimosinha",
				"orangered",
				function () { consultarTeimosinhaSisbajud() },
				"acionarMouseEmCima"
			)
			
			//BOTÃO NOVA MINUTA ENDEREÇO
			let atalho_nova_minutaEnd = criar_botao(
				"maisPje_menuKaizen_itemmenu_nova_minuta_end",
				"2",
				"icone menuConvenio_add t100 tamanho70",
				"Nova Minuta Endereço",
				"darkcyan",
				function () { 
					switch(nome_convenio) {
						case "SISBAJUD":
							novaMinutaEndSisbajud();
							break;
						case "SERASAJUD":
							novaMinutaEndSerasajud();
							break;
					}
				}
			)
			
			//BOTÃO NOVA MINUTA ENDEREÇO
			let atalho_guardar_senha = criar_botao(
				"maisPje_menuKaizen_itemmenu_guardar_senha",
				"2",
				"icone menuConvenio_senha t100 tamanho70",
				"Guardar Senha",
				"orangered",
				async function () { 
					switch(nome_convenio) {
						case "SISBAJUD":
							let s = await criarCaixaDePergunta('password', 'Guardar Senha:');
							if (document.getElementById('maisPje_menuKaizen_itemmenu_guardar_senha')) {
								if (s) { 
									document.getElementById('maisPje_menuKaizen_itemmenu_guardar_senha').setAttribute('chave',btoa(s));
									document.querySelector('span[id="maisPje_menuKaizen_itemmenu_guardar_senha"] a').style.filter = "hue-rotate(190deg)"; //sinal visual de que possui senha guardada							
								} else {
									document.querySelector('span[id="maisPje_menuKaizen_itemmenu_guardar_senha"] a').style.filter = "unset"; //apaga o sinal visual
								}
							}
							break;
					}
				}
			)
			
			//BOTÃO EXCLUIR RESTRIÇÃO
			let atalho_excluir_restricao = criar_botao(
				"maisPje_menuKaizen_itemmenu_excluir_minuta",
				"4",
				"icone menuConvenio_remove t100",
				"Excluir Restrição",
				"orangered",
				function () { 
					switch(nome_convenio) {
						case "RENAJUDNOVO":
							excluirRestricaoRenajudNovo();
							break;
						case "CNIB":
							excluirRestricaoCNIB();
							break;
					}
				}
			)
			
			
			function criar_botao(id, posicao, icone, aria, cor_de_fundo, funcao, acionarMouseEmCima='') {
				let span = document.createElement("span");
				span.id = id;
				span.style = "--p:" + posicao + ";--d:-1;--c:0;--color:" + cor_de_fundo + ";";
				let atalho = document.createElement("a");
				atalho.setAttribute('maisPje-tooltip-esquerda', aria);
				atalho.style.backgroundColor  = cor_de_fundo
				
				if (acionarMouseEmCima) {
					let check;
					let mouseEmCima = false; 
					atalho.onmouseenter = function (event) {				
						event.preventDefault();
						if (mouseEmCima) { return }
						// console.log('entrou')
						this.style.animation = 'trocarCorConvenios .75s';
						mouseEmCima = true;
						let seg = 1;
						check = setInterval(function() {
							seg--;
							if (mouseEmCima && seg < 1) {
								clearInterval(check);
								mouseEmCima = false;
								window.focus();
								atalho.click();
								atalho.style.visibility = 'hidden'; //desaparece para não ficar acionando caso o usuário fique com o mouse parado. volta apenas após 4 segundos
								setTimeout(function() {atalho.style.visibility = 'visible';}, 4000); //retorna após 4 segundos
							}			
							
						}, 750);
					};
					atalho.onmouseleave = function (event) {				
						event.preventDefault();
						this.style.animation = 'unset';
						mouseEmCima = false;
						clearInterval(check);
					};
				} else {
					atalho.onmouseenter = function () {atalho.style.backgroundColor  = 'dimgray'};
					atalho.onmouseleave = function () {atalho.style.backgroundColor  = cor_de_fundo};
				}
				
				atalho.onclick = funcao;
				let i = document.createElement("i");
				i.className = icone;
				atalho.appendChild(i);
				span.appendChild(atalho);
				return span;
			}
			
			//inserir botões no menu
			switch(nome_convenio) {
				case "SISBAJUD":
					atalho_consulta_rapida.style.setProperty("--p","1");					
					atalho_consultar_minuta.style.setProperty("--p","2");
					atalho_consultar_teimosinha.style.setProperty("--p","3");
					atalho_nova_minuta.style.setProperty("--p","4");
					atalho_nova_minutaEnd.style.setProperty("--p","4");
					atalho_nova_minutaEnd.style.setProperty("--c","1");
					atalho_preencher_campos.style.setProperty("--p","5");
					atalho_preencher_campos_invertido.style.setProperty("--p","5");
					atalho_preencher_campos_invertido.style.setProperty("--c","1");					
					atalho_guardar_senha.style.setProperty("--p","6");
					atalho_guardar_senha.style.display = 'none'; //deixar oculto!!! irá aparecer apenas se for pressionado F2.
					menuMaisPje_content.appendChild(atalho_guardar_senha);
					menuMaisPje_content.appendChild(atalho_preencher_campos_invertido);
					menuMaisPje_content.appendChild(atalho_preencher_campos);
					menuMaisPje_content.appendChild(atalho_nova_minutaEnd);
					menuMaisPje_content.appendChild(atalho_nova_minuta);
					menuMaisPje_content.appendChild(atalho_consultar_teimosinha);
					menuMaisPje_content.appendChild(atalho_consultar_minuta);
					menuMaisPje_content.appendChild(atalho_consulta_rapida);
					
					browser.storage.local.get('menu_kaizen', function(result){
						if (!result.menu_kaizen) { return }
						menuMaisPje.style.left = result.menu_kaizen.sisbajud.posx;
						menuMaisPje.style.top = result.menu_kaizen.sisbajud.posy;
					});
					break;
				case "SERASAJUD":
					atalho_consulta_rapida.style.setProperty("--p","1");
					atalho_consultar_minuta.style.setProperty("--p","2");
					atalho_nova_minuta.style.setProperty("--p","3");
					atalho_nova_minutaEnd.style.setProperty("--p","3");
					atalho_nova_minutaEnd.style.setProperty("--c","1");
					atalho_preencher_campos.style.setProperty("--p","4");
					menuMaisPje_content.appendChild(atalho_preencher_campos);
					menuMaisPje_content.appendChild(atalho_consultar_minuta);
					menuMaisPje_content.appendChild(atalho_nova_minutaEnd);
					menuMaisPje_content.appendChild(atalho_nova_minuta);
					menuMaisPje_content.appendChild(atalho_consulta_rapida);
					
					browser.storage.local.get('menu_kaizen', function(result){
						if (!result.menu_kaizen) { return }
						menuMaisPje.style.left = result.menu_kaizen.serasajud.posx;
						menuMaisPje.style.top = result.menu_kaizen.serasajud.posy;
					});
					break;
				case "RENAJUD":
					atalho_consulta_rapida.style.setProperty("--p","1");
					atalho_preencher_campos.style.setProperty("--p","2");
					menuMaisPje_content.appendChild(atalho_preencher_campos);
					menuMaisPje_content.appendChild(atalho_consulta_rapida);
					
					browser.storage.local.get('menu_kaizen', function(result){
						if (!result.menu_kaizen) { return }
						menuMaisPje.style.left = result.menu_kaizen.renajud.posx;
						menuMaisPje.style.top = result.menu_kaizen.renajud.posy;
					});
					break;
				case "RENAJUDNOVO":
					atalho_consulta_rapida.style.setProperty("--p","1");
					atalho_nova_minuta.style.setProperty("--p","2");
					atalho_preencher_campos.style.setProperty("--p","3");
					atalho_excluir_restricao.style.setProperty("--p","4");
					menuMaisPje_content.appendChild(atalho_excluir_restricao);
					menuMaisPje_content.appendChild(atalho_preencher_campos);
					menuMaisPje_content.appendChild(atalho_nova_minuta);
					menuMaisPje_content.appendChild(atalho_consulta_rapida);
					
					browser.storage.local.get('menu_kaizen', function(result){
						if (!result.menu_kaizen) { return }
						menuMaisPje.style.left = result.menu_kaizen.renajud.posx;
						menuMaisPje.style.top = result.menu_kaizen.renajud.posy;
					});
					break;
				case "CNIB":
					atalho_consulta_rapida.style.setProperty("--p","1");
					atalho_preencher_campos.style.setProperty("--p","2");
					atalho_excluir_restricao.style.setProperty("--p","3");
					menuMaisPje_content.appendChild(atalho_excluir_restricao);
					menuMaisPje_content.appendChild(atalho_preencher_campos);
					menuMaisPje_content.appendChild(atalho_consulta_rapida);
					
					browser.storage.local.get('menu_kaizen', function(result){
						if (!result.menu_kaizen) { return }
						menuMaisPje.style.left = result.menu_kaizen.cnib.posx;
						menuMaisPje.style.top = result.menu_kaizen.cnib.posy;
					});
					break;
				case "CCS":
					atalho_consulta_rapida.style.setProperty("--p","1");
					atalho_preencher_campos.style.setProperty("--p","2");
					menuMaisPje_content.appendChild(atalho_preencher_campos);
					menuMaisPje_content.appendChild(atalho_consulta_rapida);
					
					browser.storage.local.get('menu_kaizen', function(result){
						if (!result.menu_kaizen) { return }
						menuMaisPje.style.left = result.menu_kaizen.ccs.posx;
						menuMaisPje.style.top = result.menu_kaizen.ccs.posy;
					});
					break;
				case "PREVJUD":
					atalho_preencher_campos_invertido.style.setProperty("--p","1");
					atalho_preencher_campos.style.setProperty("--p","2");
					menuMaisPje_content.appendChild(atalho_preencher_campos_invertido);
					menuMaisPje_content.appendChild(atalho_preencher_campos);
					
					browser.storage.local.get('menu_kaizen', function(result){
						if (!result.menu_kaizen) { return }
						menuMaisPje.style.left = result.menu_kaizen.prevjud.posx;
						menuMaisPje.style.top = result.menu_kaizen.prevjud.posy;
					});
					break;
				case "PROTESTOJUD":
					atalho_preencher_campos.style.setProperty("--p","1");
					menuMaisPje_content.appendChild(atalho_preencher_campos);
					
					browser.storage.local.get('menu_kaizen', function(result){
						if (!result.menu_kaizen) { return }
						menuMaisPje.style.left = result.menu_kaizen.protestojud.posx;
						menuMaisPje.style.top = result.menu_kaizen.protestojud.posy;
					});
					break;
				case "SNIPER":
					atalho_preencher_campos.style.setProperty("--p","1");
					menuMaisPje_content.appendChild(atalho_preencher_campos);
					
					browser.storage.local.get('menu_kaizen', function(result){
						if (!result.menu_kaizen) { return }
						menuMaisPje.style.left = result.menu_kaizen.sniper.posx;
						menuMaisPje.style.top = result.menu_kaizen.sniper.posy;
					});
					break;
				case "CENSEC":
					atalho_preencher_campos.style.setProperty("--p","1");
					menuMaisPje_content.appendChild(atalho_preencher_campos);
					
					browser.storage.local.get('menu_kaizen', function(result){
						if (!result.menu_kaizen) { return }
						menuMaisPje.style.left = result.menu_kaizen.censec.posx;
						menuMaisPje.style.top = result.menu_kaizen.censec.posy;
					});
					break;
				case "CELESC":
					atalho_preencher_campos.style.setProperty("--p","1");
					menuMaisPje_content.appendChild(atalho_preencher_campos);
					
					browser.storage.local.get('menu_kaizen', function(result){
						if (!result.menu_kaizen) { return }
						menuMaisPje.style.left = result.menu_kaizen.celesc.posx;
						menuMaisPje.style.top = result.menu_kaizen.celesc.posy;
					});
					break;
				case "CASAN":
					atalho_preencher_campos.style.setProperty("--p","1");
					menuMaisPje_content.appendChild(atalho_preencher_campos);
					
					browser.storage.local.get('menu_kaizen', function(result){
						if (!result.menu_kaizen) { return }
						menuMaisPje.style.left = result.menu_kaizen.casan.posx;
						menuMaisPje.style.top = result.menu_kaizen.casan.posy;
					});
					break;
				case "SIGEF":
					atalho_preencher_campos.style.setProperty("--p","1");
					menuMaisPje_content.appendChild(atalho_preencher_campos);
					
					browser.storage.local.get('menu_kaizen', function(result){
						if (!result.menu_kaizen) { return }
						menuMaisPje.style.left = result.menu_kaizen.sigef.posx;
						menuMaisPje.style.top = result.menu_kaizen.sigef.posy;
					});
					break;
				case "INFOSEG":
					atalho_preencher_campos.style.setProperty("--p","1");
					menuMaisPje_content.appendChild(atalho_preencher_campos);
					
					browser.storage.local.get('menu_kaizen', function(result){
						if (!result.menu_kaizen) { return }
						menuMaisPje.style.left = result.menu_kaizen.infoseg.posx;
						menuMaisPje.style.top = result.menu_kaizen.infoseg.posy;
					});
					break;
				case "AJJT":
					atalho_nova_minuta.style.setProperty("--p","1");
					atalho_consultar_minuta.style.setProperty("--p","2");
					
					atalho_nova_minuta.querySelector('a').setAttribute('maispje-tooltip-esquerda','Solicitar RHP');
					atalho_consultar_minuta.querySelector('a').setAttribute('maispje-tooltip-esquerda','Pesquisar RHP (Atalho: F2)');
					
					menuMaisPje_content.appendChild(atalho_nova_minuta);
					menuMaisPje_content.appendChild(atalho_consultar_minuta);
					
					browser.storage.local.get('menu_kaizen', function(result){
						if (!result.menu_kaizen) { return }
						menuMaisPje.style.left = result.menu_kaizen.ajjt.posx;
						menuMaisPje.style.top = result.menu_kaizen.ajjt.posy;
						
					});
					break;
			}
		}
	
		//cria o monitor da tela do convênio na criação do menu
		if (nome_convenio == "SISBAJUD") {
			monitor_janela_sisbajud();
		}
		
		if (nome_convenio == "RENAJUD") {
			if (preferencias.renajud.tipo_restricao) {
				monitor_janela_renajud();
			}
		}
		
		if (nome_convenio == "RENAJUDNOVO") {
			if (preferencias.renajud.tipo_restricao) {
				monitor_janela_renajudNovo();
			}
		}
		
		if (nome_convenio == "CENSEC") {
			monitor_janela_censec();
		}
		
		if (nome_convenio == "CCS") {
			if (executar_funcao == "preencherCampos") {
				preenchercamposCCS();
			}
		}
		
		async function novaMinutaSisbajud() {
			await clicarBotao('button[aria-label*="menu de navegação"]');
			await clicarBotao('a[aria-label*="Ir para Minuta"]');
			await clicarBotao('button', 'Nova');
		}
		
		async function novaMinutaEndSisbajud() {
			await clicarBotao('button[aria-label*="menu de navegação"]');
			await clicarBotao('a[aria-label*="Ir para Minuta"]');
			await clicarBotao('button', 'Nova');
			await clicarBotao('label', 'Requisição de informações');
		}
		
		async function consultarMinutaSisbajud() {
			await clicarBotao('button[aria-label*="menu de navegação"]');
			await clicarBotao('a[aria-label*="Ir para Ordem judicial"]');
			await clicarBotao('div[role="tab"]', 'Busca por filtros de pesquisa');
			let var1 = browser.storage.local.get('processo_memoria', async function(result){
				if (!result.processo_memoria.numero) { return }
				await preencherInput('input[placeholder="Número do Processo"]',result.processo_memoria.numero,false);
				await clicarBotao('button', 'Consultar');
			});			
		}
		
		async function consultarTeimosinhaSisbajud() {
			await clicarBotao('button[aria-label*="menu de navegação"]');
			await clicarBotao('a[aria-label*="Ir para Teimosinha"]');
			let var1 = browser.storage.local.get('processo_memoria', async function(result){
				if (!result.processo_memoria.numero) { return }
				await preencherInput('input[placeholder="Número do Processo"]',result.processo_memoria.numero,false);
				await clicarBotao('button', 'Consultar');
			});			
		}
		
		async function preenchercamposSisbajud(inverterPolo) {
			if (!document.location.href.includes("/minuta/cadastrar")) {
				await clicarBotao('span[id="maisPje_menuKaizen_itemmenu_nova_minuta"] a');
				await esperarElemento('sisbajud-cadastro-minuta input[placeholder="Juiz Solicitante"]');
				await sleep(1000);
				await preenchercamposSisbajud(inverterPolo);
			} else if (document.location.href.includes("/minuta/cadastrar")) {
				console.log("   |___PREENCHER CAMPOS");
				
				let interromper = false;
				window.addEventListener('keydown', async function(event) {
					if (event.code === "Escape") { interromper = true }
				});
				
				let lista_de_executados;
				if (inverterPolo) {
					lista_de_executados = await criarCaixaDeSelecaoComReclamantes();
				} else {
					lista_de_executados = await criarCaixaDeSelecaoComReclamados();
				}
				
				fundo(true);
				if (!lista_de_executados) { return }
				let ancora = querySelectorByText('mat-card-title','Réus/executados') || querySelectorByText('mat-card-title','Pessoas físicas/jurídicas pesquisadas');
				ancora = ancora.parentElement.parentElement;
				ancora.id = "maisPje_sisbajud_monitor";
				let req_endereco = (document.querySelector('mat-radio-button[class*="mat-radio-checked"]').innerText == "Requisição de informações") ? true : false;
				let contador = 0;
				let target = document.getElementById("maisPje_sisbajud_monitor");	
				let observer = new MutationObserver(function(mutations) {
					let erro = false;
					mutations.forEach(function(mutation) {
						if (mutation.target.tagName != "TD") { return }
						if (mutation.target.tagName == "TD") {
							if (mutation.target.className.includes("cdk-column-identificacao")) { cadastro() }
						}
					});
				});		
				let config = { childList: true, characterData: true, subtree:true }
				let target_erros = document.body;
				let observer_erros = new MutationObserver(function(mutations) {
					mutations.forEach(function(mutation) {
						if (mutation.target.tagName != "DIV") { return }
						if (mutation.target.className != "cdk-overlay-container") { return }
						if (!mutation.target.innerText) { return }
						
						if (mutation.target.innerText.includes('CPF ou CNPJ inválidos.')) {
							console.log("            |___CPF/CNPJ com erro (1)");
							erro = true;
							triggerEvent(document.querySelector('button[class*="snack-messenger-close-button"]'), 'click');
							setTimeout(function() { cadastro(erro) }, 800);
						} else if (mutation.target.innerText.includes('O Réu/Executado já foi incluído.')) {
							console.log("            |___CPF/CNPJ com erro (2)");
							triggerEvent(document.querySelector('button[class*="snack-messenger-close-button"]'), 'click');
							setTimeout(function() { cadastro() }, 800);
						} else if (mutation.target.innerText.includes('O CPF/CNPJ informado não está com situação cadastral regular/ativo na Receita Federal.')) {
							console.log("            |___CPF/CNPJ com alerta (1)");
							triggerEvent(document.querySelector('button[class*="snack-messenger-close-button"]'), 'click');
							
						} else if (mutation.target.innerText.includes('Campo "CPF/CNPJ') && mutation.target.innerText.includes('é obrigatório.')) {
							console.log("            |___CPF/CNPJ com erro (2)");
							triggerEvent(document.querySelector('button[class*="snack-messenger-close-button"]'), 'click');
							setTimeout(function() { cadastro() }, 800);
						} else if (mutation.target.innerText.includes('Falha ao obter retorno do sistema CCS.')) {
							console.log("            |___CPF/CNPJ com erro (3)");
							triggerEvent(document.querySelector('button[class*="snack-messenger-close-button"]'), 'click');
							setTimeout(function() { cadastro() }, 800);
						}
					});
				});
				let config_erros = { childList: true, characterData: true, subtree:true }
				
				let var1 = browser.storage.local.get('processo_memoria', function(result){
					preferencias.processo_memoria = result.processo_memoria;
					acao1();
				});
				
				
				//JUIZ SOLICITANTE
				async function acao1() {
					if (interromper) { return fundo(false) }

					console.log("      |___JUIZ SOLICITANTE: " + preferencias.sisbajud.juiz);
					if (preferencias.sisbajud.juiz && document.querySelector('input[placeholder*="Juiz"]')) {
						let magistrado = preferencias.sisbajud.juiz;
						if (magistrado.toLowerCase().includes('modulo8')) {
							let processoNumero = preferencias.processo_memoria.numero.toString().match(new RegExp('\\d{7}-\\d{2}\\.\\d{4}\\.\\d{1,2}\\.\\d{1,2}\\.\\d{4}','g')).join();
							magistrado = await filtroMagistrado(processoNumero);
						}								
						// await escolherOpcao('input[placeholder*="Juiz"]',magistrado,0,false);								
						await escolherOpcaoSISBAJUD('input[placeholder*="Juiz"]',magistrado);
					}
					
					acao2();
					
				}
				
				//VARA/JUÍZO
				function acao2() {
					if (interromper) { return fundo(false) }

					console.log("      |___VARA/JUÍZO: " + preferencias.sisbajud.vara);
					if (preferencias.sisbajud.vara) {
						let el = document.querySelector('mat-select[name*="varaJuizoSelect"]');
						el.focus();
						el.click();
						
						let check = setInterval(function() {
							if (document.querySelectorAll('mat-option[role="option"]')) {
								clearInterval(check)
								let el2 = document.querySelectorAll('mat-option[role="option"]');
								if (!el2) {
									return
								}
								let map = [].map.call(
									el2, 
									function(elemento) {
										if (elemento.innerText.search(preferencias.sisbajud.vara) > -1) {
											elemento.click();
											acao3();
										}
									}
								);
							}
						}, 100); //dar tempo de popular o checklist
					} else {
						acao3();
					}
				}
				
				//NUMERO PROCESSO
				function acao3() {
					if (interromper) { return fundo(false) }

					console.log("      |___NUMERO PROCESSO");
					let el = document.querySelector('input[placeholder="Número do Processo"]');
					el.focus();
					
					el.value = preferencias.processo_memoria.numero;
					triggerEvent(el, 'input');
					el.blur();
					acao4();
				}

				//TIPO AÇÃO
				function acao4() {
					if (interromper) { return fundo(false) }

					console.log("      |___TIPO AÇÃO");
					let el = document.querySelector('mat-select[name*="acao"]');
					el.focus();
					el.click();
					
					let check = setInterval(function() {
						if (document.querySelectorAll('mat-option[role="option"]')) {
							clearInterval(check);
							let el2 = document.querySelectorAll('mat-option[role="option"]');
							if (!el2) {
								return
							}
							let map = [].map.call(
								el2, 
								function(elemento) {
									if (elemento.innerText == 'Ação Trabalhista') {									
										elemento.click();
										acao5();
									}
								}
							);
						}
					}, 100); //dar tempo de popular o checklist
				}
				
				//CPF/CNPJ AUTOR
				function acao5() {
					if (interromper) { return fundo(false) }

					console.log("      |___CPF/CNPJ AUTOR");
					let el = document.querySelector('input[placeholder*="CPF"]');
					el.focus();
					
					let n = preferencias.processo_memoria.autor[0].cpfcnpj;
					if (lista_de_executados.length == 0) { n = preferencias.processo_memoria.reu[0].cpfcnpj } // se não tiver ninguém na lista de executados quer dizer que o executado é o autor
					if (inverterPolo) {
						n = preferencias.processo_memoria.reu[0].cpfcnpj;
					}
					n = n.replace(/\./g,'');
					n = n.replace(/\-/g,'');		
					setTimeout(function() {
						el.value = n;
						triggerEvent(el, 'input');
						el.blur();
						acao6();
					}, 250);
					
				}
				
				//NOME AUTOR
				function acao6() {
					if (interromper) { return fundo(false) }

					console.log("      |___NOME AUTOR");
					let el = document.querySelector('input[placeholder="Nome do autor/exequente da ação"]');
					el.focus();
					
					let n = preferencias.processo_memoria.autor[0].nome;
					if (lista_de_executados.length == 0) { n = preferencias.processo_memoria.reu[0].nome } // se não tiver ninguém na lista de executados quer dizer que o executado é o autor
					if (inverterPolo) {
						n = preferencias.processo_memoria.reu[0].nome;
					}
					
					setTimeout(function() {
						el.value = n;
						triggerEvent(el, 'input');
						el.blur();
						// console.log("      |___FIM");
						acao7()
					}, 250);
				}
				
				//TEIMOSINHA
				function acao7() {
					if (interromper) { return fundo(false) }

					console.log("      |___TEIMOSINHA");
					
					//esse primeiro if serve para ignorar a teimosinha nos casos de requisição de informações
					if (req_endereco) {
						acao7_1();
					} else {
						
						if (preferencias.sisbajud.teimosinha.toLowerCase() != "nao") {
							let el = document.querySelectorAll('mat-radio-button');
						
							if (!el) {
								return
							}
							let map = [].map.call(
								el, 
								function(elemento) {
									if (elemento.innerText.search("Repetir a ordem") > -1) {
										elemento.querySelector('label').click();
										acao8();
									}
								}
							);
						
						
						} else {
							acao10();
						}
					}
				}
				
				//ENDEREÇO
				function acao7_1() {
					if (interromper) { return fundo(false) }

					console.log("      |___ENDEREÇO");
					
					if (document.querySelectorAll('span[class*="mat-checkbox-label"]')) {
						let el = document.querySelectorAll('span[class*="mat-checkbox-label"]');
					
						if (!el) {
							return;
						}
						
						let map = [].map.call(
							el, 
							function(elemento) {
								if (elemento.innerText == "Endereços") {
									elemento.parentElement.firstElementChild.firstElementChild.click();
									acao7_2();
								}
							}
						)
					}
				}
				
				//ENDEREÇO
				function acao7_2() {
					if (interromper) { return fundo(false) }

					console.log("      |___DESMARCAR OPÇÃO INCLUIR DADOS SOBRE CONTAS");
					
					let el = document.getElementById('maisPje_sisbajud_monitor').querySelectorAll('mat-radio-button');
						
					if (!el) {
						return
					}
					let map = [].map.call(
						el, 
						function(elemento) {
							if (elemento.innerText.includes("Não")) {
								elemento.querySelector('label').click();
								acao10();
							}
						}
					);
				}
				
				//CALENDARIO
				async function acao8() {
					if (interromper) { return fundo(false) }

					
					console.log("      |___ABRE CALENDARIO: " + preferencias.sisbajud.teimosinha.toLowerCase() + " dias");
					await clicarBotao('button[aria-label="Open calendar"]');
					
					if (preferencias.sisbajud.teimosinha.toLowerCase().includes('30')) {
						console.log("         |___30 dias");
						//pega o "dia de hoje", passa um mês no calendário e clica no "dia de hoje" do mês seguinte
						let diaDeHoje = await esperarElemento('div[class*="mat-calendar-body-today"]');
						await clicarBotao('button[aria-label="Next month"]');
						await clicarBotao('mat-calendar td[class*="mat-calendar-body-cell"]', diaDeHoje.innerText);
						acao10();
						
					// atualmente não existe mais a configuração "sim", porém caso aconteça "configurações muito antigas" será definido como 60 dias
					} else if (preferencias.sisbajud.teimosinha.toLowerCase().includes('60') || preferencias.sisbajud.teimosinha.toLowerCase().includes('sim')) {
						console.log("         |___60 dias");
						//passa dois meses no calendário e pega o último dia ativo no calendário
						
						let botaoProximoMes = await esperarElemento('mat-calendar button[aria-label="Next month"]');						
						if (!botaoProximoMes?.hasAttribute('disabled')) { await botaoProximoMes.click() }
						
						botaoProximoMes = await esperarElemento('mat-calendar button[aria-label="Next month"]');						
						if (!botaoProximoMes?.hasAttribute('disabled')) { await botaoProximoMes.click() }
						
						
						//analisa célula a célula, quando encontrar a primeira desativada, pega o dia anterior
						let diasDoMes = await esperarColecao('mat-datepicker-content tbody[class="mat-calendar-body"] td',28);
						let dataLimiteDaTeimosinha, mes;
						for (const [pos, dia] of diasDoMes.entries()) {
							if (pos == 0) { 
								mes = dia.innerText 
							} else {
								// console.log(pos + ": " + dia.innerText + "/" + mes);
								let celulaDesativada = dia.getAttribute('aria-disabled');
								
								if (celulaDesativada && !dataLimiteDaTeimosinha) { 
									dataLimiteDaTeimosinha = diasDoMes[pos-1];
								}
								
								//se chegar no ultimo dia do mes e não existir dataLimiteDaTeimosinha definida, usar o último dia como dataLimiteDaTeimosinha
								// console.log(pos + " ==  + (" + diasDoMes.length + "-1) : " + (pos == (diasDoMes.length-1)) + "         ------         " + dataLimiteDaTeimosinha);
								if (pos == (diasDoMes.length-1) && !dataLimiteDaTeimosinha) {
									dataLimiteDaTeimosinha = dia;
								}
							}
							
						}
						
						console.log("            |___ultimo dia da teimosinha: " + dataLimiteDaTeimosinha.innerText + "/" + mes);
						await clicarBotao(dataLimiteDaTeimosinha);
						acao10();
					}
				}
				
				//INSERÇÃO DOS RÉUS
				function acao10() {
					if (interromper) { return fundo(false) }

					console.log("      |___INSERÇÃO DOS RÉUS");				
					observer.observe(target, config); //inicia o MutationObserver
					observer_erros.observe(target_erros, config_erros); //inicia o MutationObserver
					cadastro();
				}
				
				//Informa o valor da última atualização
				async function acao11() {
					if (interromper) { return fundo(false) }

					if (req_endereco) {
						acao13();
						// fundo(false);
						// console.log("      |___FIM");
					} else {
						if (preferencias.processo_memoria.divida.valor) {
							let valor_formatado_para_exibir_sem_data = Intl.NumberFormat('pt-br', {style: 'currency', currency: 'BRL'}).format(preferencias.processo_memoria.divida.valor);
							let valor_formatado_para_exibir_com_data = valor_formatado_para_exibir_sem_data + " em " + preferencias.processo_memoria.divida.data;
							
							ancora = document.querySelector('div[class="label-valor-extenso"]');
							let span = document.createElement('span');
							span.id = 'maisPJe_valor_execucao';
							span.innerText = "Última atualização do processo: " + valor_formatado_para_exibir_com_data;
							span.style="color: white;background-color: slategray;padding: 10px;border-radius: 10px; cursor: pointer;";
							span.onclick = async function() {
								await preencherInput('input[placeholder*="Valor aplicado a todos"]', valor_formatado_para_exibir_sem_data)
							}
							ancora.appendChild(document.createElement('br'));
							ancora.appendChild(document.createElement('br'));
							ancora.appendChild(span);
							
							if (preferencias.sisbajud.preencherValor.toLowerCase() == "sim") {
								await clicarBotao('span[id="maisPJe_valor_execucao"]');
								let btAdicionar = await esperarElemento('div[id="maisPje_sisbajud_monitor"] mat-icon[class*="fa-check-square"]');
								await clicarBotao(btAdicionar.parentElement.parentElement);
							}
						}
						acao12();
					}
				}
				
				//CONTA SALÁRIO
				async function acao12() {
					if (interromper) { return fundo(false) }

					if (preferencias.sisbajud.contasalario.toLowerCase() == "sim") {
						console.log("      |___CONTA-SALÁRIO");
						let el = document.querySelectorAll('mat-slide-toggle label');
					
						if (!el) { return }
						
						for (const [pos, matSlide] of el.entries()) {
							matSlide.click();
						}
					}
					
					acao13();
				}
				
				//SALVAR E PROTOCOLAR
				async function acao13() {
					if (interromper) { return fundo(false) }

					observer.disconnect(); //finaliza o MutationObserver
					observer_erros.disconnect(); //finaliza o MutationObserver
					
					if (preferencias.sisbajud.salvarEprotocolar.toLowerCase() == "sim") {
						console.log("      |___SALVAR E PROTOCOLAR");
						
						let btSalvar = await esperarElemento('sisbajud-cadastro-minuta button','Salvar');
						await clicarBotao(btSalvar);
						
						let mensagem = await esperarElemento('SISBAJUD-SNACK-MESSENGER');
						if (mensagem.innerText.includes('incluída com sucesso')) {
							let btProtocolar = await esperarElemento('sisbajud-detalhamento-minuta button','Protocolar');
							await sleep(1000);
							btProtocolar.onmouseenter = function (event) {	event.stopPropagation() }
							await clicarBotao(btProtocolar);
							
							fundo(false);
							console.log("      |___FIM");
						} else {
							// if (mensagem.innerText.innerText.includes('que não possui Instituição Financeira associada')) {
							
							fundo(false);
							console.log("      |___FIM");
						}
						
						
					} else {
						fundo(false);
						console.log("      |___FIM");
					}
				}
				
				function cadastro(erro) {
					if (interromper) { return fundo(false) }

					let el = document.querySelector('input[placeholder="CPF/CNPJ do réu/executado"]') || document.querySelector('input[placeholder="CPF/CNPJ da pessoa pesquisada"]');
					let bt = document.querySelector('button[class*="btn-adicionar"]');
					
					if (erro) { //se teve erro no cnpj raiz, lança cnpj inteiro
						contador--;
					}
					
					if (contador < lista_de_executados.length) {
						el.focus();
						
						//CNPJ raiz?
						let var1 = lista_de_executados[contador].cpfcnpj;
						
						if (!erro) {
							if (var1.length > 14) {
								if (preferencias.sisbajud.cnpjRaiz) {
									if (preferencias.sisbajud.cnpjRaiz.toLowerCase() == "sim") {
										var1 = var1.substring(0, 10);						
									} else {
										erro = true; //corrige o bug do SISBAJUD (primeira inserção sem cnpjRaiz)
									}
								}
							}
						}
						
						console.log("      |___" + contador + ": " + lista_de_executados[contador].nome + " ( " + var1 + ")");
						
						el.value = var1;
						triggerEvent(el, 'input');
						
						//verificar se é um cpf e não permitir que o sisbajud confunda cpf com cnpj raiz. E também verificar se o CNPJ raiz deu erro na busca 
						let corrigeBug = false
						setTimeout(function() {
							if ((var1.length < 15 && el.value.length == 10) || erro) { //É CNPJ RAIZ
								// console.log('1');
								el.value = var1;
								triggerEvent(el, 'input');
								corrigeBug = true;
							} else { //É CPF
								// console.log('2');
								corrigeBug = true;
							}
						}, 800);
						//*******************************************************************************
						
						let check = setInterval(function() {
							if (corrigeBug) {
								// console.log('3');
								clearInterval(check);
								triggerEvent(bt, 'click');
								contador++;
							}
						}, 800);
					} else {
						acao11();
					}
				}

				async function escolherOpcaoSISBAJUD(seletor, valor) {
					return new Promise(async resolve => {
						//NOVOS TESTES PARA QUE A FUNÇÃO FUNCIONE EM ABAS(GUIAS) DESATIVADAS
						await sleep(preferencias.maisPje_velocidade_interacao);
						if (seletor instanceof HTMLElement) {
						} else {
							seletor = await esperarElemento(seletor);
						}		
						
						seletor.focus();
						seletor.dispatchEvent(simularTecla('keydown',40)); //SETA PRA BAIXO
						
						//teste1 : o carregamento muito rápido da página por vezes não permite ao menu de opções abrir para selecionar a opção desejada
						let teste = await esperarColecao('mat-option[role="option"], option', 5, 1000);			
						if (!teste) {
							seletor.focus();
							seletor.dispatchEvent(simularTecla('keydown',40)); //SETA PRA BAIXO
							//teste2
							teste = await esperarColecao('mat-option[role="option"], option', 5, 1000);			
							if (!teste) {
								seletor.focus();
								seletor.dispatchEvent(simularTecla('keydown',40)); //SETA PRA BAIXO
								//teste3
								teste = await esperarColecao('mat-option[role="option"], option', 5, 1000);			
								if (!teste) {
									seletor.focus();
									seletor.dispatchEvent(simularTecla('keydown',40)); //SETA PRA BAIXO
								}
							}
						}
						
						await clicarBotao('mat-option[role="option"], option', valor); //aciona a opção
						return resolve(true);
					});
				}
			}
		}
		
		async function preenchercamposSerasajud() {
			if (document.location.href.includes("serasa") && document.location.href.includes("cadastrar-ordem")) {
				console.log("   |___PREENCHER CAMPOS");
				let lista_de_executados = await criarCaixaDeSelecaoComReclamados();
				fundo(true);
				if (!lista_de_executados) { return }
				let contador = 0;
				let target = document.querySelector('app-incluir-acao-form') || document.querySelector('app-atualizar-acao-form') || document.querySelector('app-consultar-endereco');
				let observer = new MutationObserver(function(mutations) {
					mutations.forEach(function(mutation) {
						if(mutation.target.tagName == "MAT-TOOLBAR") {
							cadastro();
						}
					});
				});		
				let config = { childList: true, characterData: true, subtree:true }
				browser.storage.local.get('processo_memoria', async function(result){
					preferencias.processo_memoria = result.processo_memoria;
					
					let jaExisteOrdemAnterior = await esperarElemento('app-atualizar-acao-form',null,1000);
					if (jaExisteOrdemAnterior) {
						console.log("      |___INSERÇÃO DOS RÉUS");
						observer.observe(target, config); //inicia o MutationObserver
						await cadastro();
					} else {
						iniciar_acoes_serasajud();
					}
				});
				
				
				//FORO
				async function iniciar_acoes_serasajud() {
					console.log("      |___FORO");
					await escolherOpcaoTeste('mat-select[formcontrolname="foro"]', preferencias.serasajud.foro);
					console.log("      |___VARA");
					await escolherOpcaoTeste('mat-select[formcontrolname="vara"]', preferencias.serasajud.vara);
					console.log("      |___MAGISTRADO");
					await escolherOpcaoTeste('mat-select[formcontrolname="varaMagistrado"]', preferencias.serasajud.juiz);
					
					if (document.querySelector('div[role="tab"]').className.includes('mat-tab-label-active')) { // "Inclusão de Dívida"
						console.log("      |___PRAZO DE ATENDIMENTO");
						await esperarColecao('mat-radio-button', 1, 500).then(matoption=>{ //alterações de cadastro não tem a opção de prazo de atendimento
							if (!matoption) { return }
							for (const [pos, opt] of matoption.entries()) {
								if (opt.innerText.includes(preferencias.serasajud.prazo_atendimento)) {
									opt.querySelector('label').click();
									break;
								}
							}
						});
						console.log("      |___TIPO DE AÇÃO");
						await preencherInput('input[data-placeholder="Tipo Ação"]', 'Execução Judicial Trabalhista');
						await esperarColecao('mat-option[role="option"]', 1, 500).then(matoption=>{ //precisa escolher depois de preencher o input senão dá erro quando protocola a ordem
							if (!matoption) { return }
							for (const [pos, opt] of matoption.entries()) {
								if (opt.innerText.includes('Execução Judicial Trabalhista')) {
									opt.click();
									break;
								}
							}
						});
						
						console.log("      |___VALOR DA ANOTAÇÃO");
						let valor_formatado_para_uso = Intl.NumberFormat('pt-br', {style: 'decimal', currency: 'BRL'}).format(preferencias.processo_memoria.divida.valor);
						let inputVlrAcao = await esperarElemento('input[formcontrolname="vlrAcao"]');
						await preencherInput(inputVlrAcao, valor_formatado_para_uso);
						inputVlrAcao.focus();
						inputVlrAcao.dispatchEvent(simularTecla('keypress',32)); //dispara um spacebar para validar o campo						
						
						console.log("      |___NOME AUTOR");
						await preencherInput('input[formcontrolname="autor"]', preferencias.processo_memoria.autor[0].nome);
						console.log("      |___NOME RÉU");
						await preencherInput('input[formcontrolname="reu"]', preferencias.processo_memoria.reu[0].nome);
						
					} else { // "Requisição de informações"
						console.log("      |___NÚMERO PROCESSO");
						await preencherInput('input[formcontrolname="nroProcesso"]', preferencias.processo_memoria.numero);
					}
					
					console.log("      |___INSERÇÃO DOS RÉUS");
					observer.observe(target, config); //inicia o MutationObserver
					await cadastro();
				}
				
				async function cadastro() {
					return new Promise(async resolve => {
						let el1 = document.querySelector('input[formcontrolname="nome"]') || document.querySelector('input[data-placeholder="Inclusão em nome de"]');
						let el2 = document.querySelector('input[formcontrolname="nroDocumento"]') || document.querySelector('input[data-placeholder="CPF/CNPJ"]');
						let el3;
						if (document.querySelector('input[placeholder="Valor da Anotação"]')) {
							el3 = await querySelectorByText('button','Adicionar');
						} else {
							el3 = await querySelectorByText('div[class*="btn"]','Adicionar');							
						}
						// console.log(contador + " < " + lista_de_executados.length + " : " + (contador < lista_de_executados.length))
						if (contador < lista_de_executados.length) {
							console.log("      |___" + contador + ": " + lista_de_executados[contador].nome + " (" + lista_de_executados[contador].cpfcnpj + ")");
							await preencherInput(el1, lista_de_executados[contador].nome);
							await preencherInput(el2, lista_de_executados[contador].cpfcnpj);
							contador++;
							await clicarBotao(el3);
							return resolve(true);
						} else { // final da lista de executados
							observer.disconnect(); //finaliza o MutationObserver
							fundo(false);
							contador = 0;
							console.log("      |___FIM");
							
							let ancora = await esperarElemento('button','Incluir Dívida', 500);
							if (ancora) { await clicarBotao(ancora) }
							
							ancora = await esperarElemento('button','Consultar Endereço', 500);
							if (ancora) { ancora.focus() }
							
							ancora = await esperarElemento('button','Atualizar Ação', 500);
							if (ancora) { await clicarBotao(ancora) }
							
							
							return resolve(true);
						}
					});
				}
			}
		}
		
		async function novaMinutaSerasajud() {
			await clicarBotao('button[routerlink="/ordem"]');
			await clicarBotao('button[routerlink="/cadastrar-ordem"]');
			await sleep(500);
			await clicarBotao('button','Verificar');
			await sleep(500);
			let jaExiste = esperarElemento('app-dialog-atualizar-baixar-acao',null,1000);
					
			if (jaExiste) {
				await clicarBotao('app-dialog-atualizar-baixar-acao button','Atualizar') 
			}
			
			await clicarBotao('span[id="maisPje_menuKaizen_itemmenu_preencher_campos"] a'); //preencher campos
		}
		
		async function novaMinutaEndSerasajud() {
			await clicarBotao('button[routerlink="/ordem"]');
			await clicarBotao('button[routerlink="/cadastrar-ordem"]');
			await sleep(500);
			await clicarBotao('div[aria-posinset="2"]');
			await sleep(500);
			await clicarBotao('span[id="maisPje_menuKaizen_itemmenu_preencher_campos"] a'); //preencher campos
		}
		
		async function consultarMinutaSerasajud() {
			await clicarBotao('button[routerlink="/listar-ordem"]');
			let var1 = browser.storage.local.get('processo_memoria', async function(result){
				await preencherInput('input[formcontrolname="nroProcesso"]', result.processo_memoria.numero);
				await sleep(500);
				await clicarBotao('button','Buscar');
			});
			
		}		
		
		async function preenchercamposRenajud() {
			if (document.location.href.includes("renajud.denatran.serpro.gov.br") && document.location.href.includes("renajud/restrito/restricoes-insercao")) {
				let contador = 0;
				let qtde_veiculos = 0;
				let target = document.body;
				let observer = new MutationObserver(function(mutations) {
					mutations.forEach(function(mutation) {
						if (!mutation.addedNodes[0]) { return }
						if (!mutation.addedNodes[0].id) { return }
						// console.log(mutation.addedNodes[0].id + " : " + mutation.addedNodes[0].tagName + " : " + mutation.addedNodes[0].innerText);
						if (mutation.addedNodes[0].id == "messages") {
							if (mutation.addedNodes[0].innerText == "A pesquisa não retornou resultados.") { // resultado negativo
								document.querySelector('a[class="ui-messages-close"]').click();//clicar no botão fechar mensagem
								setTimeout(function() {cadastro()}, 1000);
							} else if (mutation.addedNodes[0].innerText == "") {
								let painel_de_veiculos = document.getElementById('form-incluir-restricao:panel-lista-veiculo');
								if (painel_de_veiculos.innerText.substring(0, 30) != qtde_veiculos) { //resultado positivo
									qtde_veiculos = painel_de_veiculos.innerText.substring(0, 30);
									setTimeout(function() {cadastro()}, 1000);
								}
							}
						}
					});
				});		
				var config = { childList: true, characterData: true, subtree:true }
				
				//limpar avisos anteriores
				let btLimparLista = await esperarElemento('button[id*="form-incluir-restricao:"]','Limpar lista',100);
				if (btLimparLista) { btLimparLista.click() }
				if (document.getElementById('maisPje_renajud_div_pai')) { document.getElementById('maisPje_renajud_div_pai').remove(); }
				if (document.getElementById('maisPje_renajud_span2')) { document.getElementById('maisPje_renajud_span2').remove(); }
			
				console.log("   |___PREENCHER CAMPOS");
				let lista_de_executados = await criarCaixaDeSelecaoComReclamados();
				fundo(true);
				if (!lista_de_executados) { return }
				acao1();
				
				//INSERÇÃO DOS RÉUS
				function acao1() {
					console.log("      |___INSERÇÃO DOS RÉUS");
					
					observer.observe(target, config); //inicia o MutationObserver
					
					//inclui a lista de executados pesquisados no RENAJUD
					if (document.getElementById('form-incluir-restricao')) {
						let ancora = document.getElementById('form-incluir-restricao');
						let div_pai = document.createElement('div');
						div_pai.id = "maisPje_renajud_div_pai";
						
						let span_titulo = document.createElement('span');
						span_titulo.id = "maisPje_renajud_span_titulo";
						span_titulo.style = "font-size: 12px;color: #737373;padding-left: 2%;";
						span_titulo.innerText = "Executados pesquisados:";
						div_pai.appendChild(span_titulo);
						
						ancora.insertBefore(div_pai, ancora.firstChild);
					}
					
					cadastro();
				}
				
				function cadastro() {
					if (contador < lista_de_executados.length) {
						console.log("      |___" + contador + ": " + lista_de_executados[contador].nome + " ( " + lista_de_executados[contador].cpfcnpj + ")");
						
						//inclui executado na lista de executados pesquisados
						let div = document.createElement('div');
						div.id = "maisPje_renajud_div_" + contador;
						div.style = "font-size: 12px; color: rgb(115, 115, 115); padding-left: 20%;"
						let span = document.createElement('span');
						span.id = "maisPje_renajud_span_" + contador;
						span.innerText = lista_de_executados[contador].nome + " ( " + lista_de_executados[contador].cpfcnpj + ")";
						div.appendChild(span);
						document.getElementById('maisPje_renajud_div_pai').appendChild(div);
						
						let el = document.getElementById('form-incluir-restricao:campo-cpf-cnpj');
						el.value = lista_de_executados[contador].cpfcnpj;
						triggerEvent(el, 'input');
						contador++;
						
						document.getElementById('form-incluir-restricao:botao-pesquisar').click();
					} else { // final da lista de executados
						//inclui mensagens na tela do renajud
						if (!document.getElementById('form-incluir-restricao:lista-veiculo')) {
							let ancora2 = document.getElementById('form-incluir-restricao:panel-lista-veiculo');
							let span2 = document.createElement('span');
							span2.id = "maisPje_renajud_span2";
							span2.style = "text-align: center;width: 100%;display: inline-block;font-size: 12px;color: red;font-weight: bold;";
							span2.innerText = "Não foram encontrados veículos para os CNPJs pesquisados."
							ancora2.appendChild(span2);
						}
						
						// inclui evento no botão "limpar lista" para excluir a lista de veiculos encontrados e mensagens
						let bt_restringir = querySelectorByText('button', 'Restringir');
						if (bt_restringir) {
							bt_restringir.addEventListener('click', function(event) {
								document.getElementById('maisPje_renajud_div_pai').remove();
								document.getElementById('form-incluir-restricao:campo-cpf-cnpj').value = "";
							});
						}
						
						let bt_limpar_lista = querySelectorByText('button', 'Limpar lista');
						if (bt_limpar_lista) {
							bt_limpar_lista.addEventListener('click', function(event) {
								document.getElementById('maisPje_renajud_div_pai').remove();
								document.getElementById('form-incluir-restricao:campo-cpf-cnpj').value = "";
							});
						}
						
						let bt_limpar = querySelectorByText('button', 'Limpar');
						if (bt_limpar) {
							bt_limpar.addEventListener('click', function(event) {
								document.getElementById('maisPje_renajud_div_pai').remove();
								document.getElementById('form-incluir-restricao:campo-cpf-cnpj').value = "";
							});
						}
						
						observer.disconnect(); //finaliza o MutationObserver
						fundo(false);
						console.log("      |___FIM");
						document.getElementById('form-incluir-restricao:campo-cpf-cnpj').value = "";
						contador = 0;
						qtde_veiculos = 0;
					}
				}
			}
		}
		
		async function novaMinutaRenajudNovo() {
			await clicarBotao('a[routerlink="/veiculo/pesquisa"]');
		}
		
		async function excluirRestricaoRenajudNovo() {
			await clicarBotao('a[routerlink="/veiculo/restricao/pesquisa"]');
		}
		
		async function preenchercamposRenajudNovo() {
			//cria mutation observer
			await sleep(400); //dar tempo do listener anterior se encerrar
			let capturaAutomatica = true;
			let target = document.body;
			if (target.hasAttribute('maisPJe')) { return }
			target.setAttribute('maisPje','true');
			let observer = new MutationObserver(async function(mutations) {
				mutations.forEach(async function(mutation) {
					if (!mutation.addedNodes[0] && !mutation.removedNodes[0]) { return }
					
					if (mutation.addedNodes[0]) {
						if (!mutation.addedNodes[0].tagName) { return }
						
						//ignorar inclusões no assistente de impressão
						if (mutation.addedNodes[0].id.includes('maisPje_assistenteImpressao')) { return }
						
						// console.log('   |___ADDEDNODES: ' + mutation.addedNodes[0].tagName);
						// console.log('             |___ID    : ' + mutation.addedNodes[0].id);
						// console.log('             |___CLASSE: ' + mutation.addedNodes[0].className);
						// console.log('             |___NAME  : ' + mutation.addedNodes[0].name);
						// console.log('             |___PARENT: ' + mutation.target.tagName + ' : ' + mutation.target.className);
						// console.log('             |___CHILDS: ' + mutation.addedNodes.length);
						
						if (mutation.addedNodes[0].tagName != 'DIV' && mutation.addedNodes[0].tagName != 'APP-VEIUCLO-RESTRICAO-INCLUSAO' && mutation.addedNodes[0].tagName != 'TR') { return }
						
						if (mutation.addedNodes[0].tagName == "DIV" && mutation.addedNodes[0].className.includes('modal-backdrop fade show')) {
							if (capturaAutomatica) {
								await aguardarCarregamento();
								await clicarBotao(document.querySelector('button[id="maisPje_assistenteImpressao_bt_copiar"]'));
								await clicarBotao('div[id="dadosVeiculoModal"] button[aria-label="Close"]');
							}
						}
						
						if (mutation.addedNodes[0].tagName == "APP-VEIUCLO-RESTRICAO-INCLUSAO") {
							await inserirRestricao();
							observer.disconnect();
						}
						
						if (mutation.addedNodes[0].tagName == "TR") {
							mutation.addedNodes[0].addEventListener('click', function(event) {
								this.style.backgroundColor = (this.style.backgroundColor.includes('lightblue')) ? 'revert' : 'lightblue';
							});
						}
					}
				});
			});		
			var config = { childList: true, characterData: true, subtree:true }
			
			console.log("   |___PREENCHER CAMPOS");
			let lista_de_executados = await criarCaixaDeSelecaoComReclamados(false);
			fundo(true);
			if (!lista_de_executados) { return }			
			console.log("      |___INSERÇÃO DOS RÉUS");
			await cadastro();
			
			//listener que encerrar o mutationObserver ao se realizar nova pesquisa
			document.getElementById('maisPje_menuKaizen_itemmenu_preencher_campos').addEventListener('click', function(event) {
				document.body.removeAttribute('maisPje');
				observer.disconnect();
			});
			
			//SÓ PERMITE CADASTRAR UM POR VEZ
			async function cadastro() {	
				console.log("      |___" + lista_de_executados[0].nome + " ( " + lista_de_executados[0].cpfcnpj + ")");
				
				observer.observe(target, config); //inicia o MutationObserver				
				await preencherInput('input[id="documentoIdentificacao"]', lista_de_executados[0].cpfcnpj);
				await clicarBotao('button', 'Pesquisar');
				await aguardarCarregamento();
				await clicarBotao(document.querySelector('button[id="maisPje_assistenteImpressao_bt_copiar"]'));
				fundo(false);
				if (!document.getElementById("maisPje_Renajud_Ativar_Captura")) {
					await btDetalhesVeiculos();
				}
			}
			
			async function inserirRestricao() {
				return new Promise(async resolve => {
					let var1 = browser.storage.local.get('processo_memoria', async function(result){
						if (!result.processo_memoria.numero) {return resolve(false)}
						console.log("      |___PROCESSO: " + result.processo_memoria.numero);
						fundo(true);
						console.log("  |___preencherRestricoes > INICIO");
						console.log(preferencias.renajud.tipo_restricao);
						console.log(preferencias.renajud.orgao);
						console.log(preferencias.renajud.juiz2);
						let opt = await esperarElemento('label',preferencias.renajud.tipo_restricao);
						await clicarBotao(opt.parentElement.firstElementChild);
						
						let ramoJustica = await esperarElemento('select[id="ramoJustica"]');
						await escolherOpcao(ramoJustica, 'JUSTICA DO TRABALHO',9);
						let selecao1 = await esperarElemento('OPTION','JUSTICA DO TRABALHO');
						selecao1.selected = true;
						triggerEvent(ramoJustica,'change');
						
						let tribunal = await esperarElemento('select[id="tribunal"]');
						await escolherOpcao(tribunal, preferencias.renajud.tribunal,26);
						let selecao2 = await esperarElemento('OPTION',preferencias.renajud.tribunal);
						selecao2.selected = true;
						triggerEvent(tribunal,'change');
						
						let orgao = await esperarElemento('select[id="orgao"]');
						await escolherOpcao(orgao, preferencias.renajud.orgao,26);
						let selecao3 = await esperarElemento('OPTION',preferencias.renajud.orgao);
						selecao3.selected = true;
						triggerEvent(orgao,'change');
						
						let magistrado = await esperarElemento('select[id="magistrado"]');
						await escolherOpcao(magistrado, preferencias.renajud.juiz2,26);
						let selecao4 = await esperarElemento('OPTION',preferencias.renajud.juiz2);
						selecao4.selected = true;
						triggerEvent(magistrado,'change');
						
						await preencherInput('input[id="numeroProcesso"]', result.processo_memoria.numero);
						await clicarBotao('button', 'Inserir');
						
						let btConfirmar = await esperarElemento('button', 'Confirmar');
						btConfirmar.addEventListener('click', async function(event) {
							// await sleep(1000);
							await aguardarCarregamento();
							await clicarBotao(document.querySelector('button[id="maisPje_assistenteImpressao_bt_copiar"]'));
						});
						fundo(false);
						resolve(true);
					});
				});
				
			}
			
			//botao ativar captura automatica detalhes
			async function btDetalhesVeiculos() {
				return new Promise(async resolve => {
					let ancora = await esperarElemento('button','Limpar');
					let atalho1 = document.createElement("button");
					atalho1.id = "maisPje_Renajud_Ativar_Captura";
					atalho1.className = "btn";
					atalho1.style = "color: #fff;background-color: #0d6efd;border-color: #0d6efd;margin-left: 10px;";
					atalho1.innerText = "Captura Automática";
					atalho1.title = "Ativa/desativa a captura automática da tela de detalhes do veículo";
					atalho1.setAttribute('maisPje','ativado');
					capturaAutomatica = true;
					atalho1.onclick = async function () {						
						if (this.getAttribute('maisPje') == 'desativado') { //desativado
							this.style = "color: #fff;background-color: #0d6efd;border-color: #0d6efd;margin-left: 10px;";
							this.setAttribute('maisPje','ativado');
							capturaAutomatica = true;
						} else {
							this.style = "color: #c1c1c1;background-color: #e3e3e3;border-color: #6c757d;margin-left: 10px;";
							this.setAttribute('maisPje','desativado');
							capturaAutomatica = false;
						}
						this.blur();
					};
					ancora.parentElement.appendChild(atalho1);
					return resolve(true);
				});
			}
		
			async function aguardarCarregamento() {
				return new Promise(async resolve => {					
					let spinner = await esperarElemento('i[class*="fa-spin"]',null,1000);
					// console.log('spinner')
					if (spinner) {
						let check = setInterval(function() {
							// console.log('**spinner ')
							if (!document.querySelector('i[class*="fa-spin"]')) {
							 clearInterval(check);
							return resolve(true);
						  }
						}, 100);
					} else {
						return resolve(false);
					}
				});
			}
		}
		
		async function excluirRestricaoCNIB() {
			if (document.location.href.includes("indisponibilidade.org.br")) {
				fundo(true);
				preferencias.tempAR = 'excluir CNIB';
				let guardarStorage = browser.storage.local.set({'tempAR': preferencias.tempAR}); //uso para levar o código do assunto da AA de Retificar Autuação
				Promise.all([guardarStorage]).then(async values => {
					let bt1 = await esperarElemento('div[class="caixa-flutuante-home"] a','Cancelar Indisponibilidade',100);
					if (bt1) { await clicarBotao(bt1) }
					
					let bt2 = await esperarElemento('ul[class="subMenu"] a','Cancelamento de Indisponibilidade',100);
					if (bt2) { await clicarBotao(bt2) }
					
					fundo(false);
				});
			}
		}
		
		async function preenchercamposCnib() {
			if (document.location.href.includes("indisponibilidade.org.br") && document.location.href.includes("ordem/indisponibilidade/")) {
				console.log("   |___PREENCHER CAMPOS");
				let lista_de_executados = await criarCaixaDeSelecaoComReclamados();
				fundo(true);
				if (!lista_de_executados) { return }
				let contador = 0;
				let target = document.getElementById('content');
				let observer = new MutationObserver(function(mutations) {
					mutations.forEach(function(mutation) {
						if (!mutation.target.tagName) { return }
						if (!mutation.target.innerText) { return }
						// console.log("[ADD] " + mutation.target.tagName + " : " + mutation.target.innerText);
						
						if (mutation.target.tagName == "SPAN") { //busca o executado
							let bt_inserir = querySelectorByText('button','Inserir');
							if (bt_inserir) { bt_inserir.click() }
						}
						
						if (mutation.target.tagName == "DIV") { //incluiu o executado
							cadastro();
						}
					});
				});		
				var config = { childList: true, characterData: true, subtree:true }
				var eventoCopiarNumeroOrdem;
				
				acao1();
				
				//NUMERO DO PROCESSO
				function acao1() {
					console.log("      |___NUMERO DO PROCESSO");
					let el = document.getElementById('ordem-processo-numero');
					el.focus();
					
					let var1 = browser.storage.local.get('processo_memoria', function(result){
						el.value = result.processo_memoria.numero;
						triggerEvent(el, 'input');
						el.blur();
						acao2();
					});
				}
				
				//NOME DO PROCESSO
				function acao2() {
					console.log("      |___NOME DO PROCESSO");
					let el = document.getElementById('ordem-processo-nome');
					el.focus();
					
					let var1 = browser.storage.local.get('processo_memoria', function(result){
						let informacao = (result.processo_memoria.justicaGratuita) ? "(Justiça Gratuita) " : "";
						el.value = informacao + result.processo_memoria.autor[0].nome;
						triggerEvent(el, 'input');
						el.blur();
						acao3();
					});
				}
				
				//CLICAR EM CONTINUAR
				function acao3() {
					console.log("      |___CLICAR EM CONTINUAR");
					let el = querySelectorByText('BUTTON','Continuar');
					el.focus();
					el.click();
					
					let check = setInterval(function() {
						if (document.getElementById('resumo-ordem')) {
							clearInterval(check);
							acao4();
						}
					}, 100);
				}
				
				//INSERÇÃO DOS RÉUS
				function acao4() {
					console.log("      |___INSERÇÃO DOS RÉUS");
					observer.observe(target, config); //inicia o MutationObserver
					cadastro();
				}
				
				//CLICAR EM CONTINUAR NOVAMENTE
				function acao5() {
					console.log("      |___CLICAR EM CONTINUAR NOVAMENTE");
					let el = document.getElementById('ordem-indisponibilidade-passo-b').querySelector('button[onclick="cni.ordem.indisponibilidade.finalizar()"]');
					el.focus();
					el.click();
					acao6();
				}
				
				//CLICAR EM FINALIZAR
				function acao6() {
					console.log("      |___CLICAR EM FINALIZAR");
					let check = setInterval(function() {
						let el = document.getElementById('ordem-indisponibilidade-passo-c').querySelector('button[onclick="cni.ordem.indisponibilidade.confirmar()"]')
						if (el) {
							clearInterval(check);
							el.focus();
							el.click();
							acao7();
						}
					}, 500);					
				}
				
				//ADICIONAR EVENTO AO CLICAR EM SIM
				async function acao7() {
					console.log("      |___ADICIONA EVENTO LISTENER");
					let el = await esperarElemento('div[id="resumo-ordem"]');
					console.log("      |___FIM");
					fundo(false);
					eventoCopiarNumeroOrdem = async function(event) {
						await clicarBotao('button','OK');
						let el2 = await esperarElemento('div[id="resumo-ordem"]');
						await copiarNumeroOrdem(el2);
					}					
					
					document.body.addEventListener('click', eventoCopiarNumeroOrdem);
				}
				
				function cadastro() {
					if (contador < lista_de_executados.length) {
						let cpf_cnpj = lista_de_executados[contador].cpfcnpj;				
						console.log("      |___" + contador + ": " + lista_de_executados[contador].nome + " ( " + lista_de_executados[contador].cpfcnpj + ")");
						
						let el = document.getElementById('ordem-processo-documento');
						if (cpf_cnpj.length > 14) { //CPF ou CNPJ?
							document.getElementById('ordem-processo-cnpj').click();
						} else {
							document.getElementById('ordem-processo-cpf').click();
						}
						contador++;
						el.value = cpf_cnpj;
						triggerEvent(el, 'input');
						querySelectorByText('button','Buscar').click();
					} else { // final da lista de executados
						observer.disconnect(); //finaliza o MutationObserver					
						contador = 0;
						setTimeout(function() {acao5()}, 1000);
						
					}
				}
				
				async function copiarNumeroOrdem(el) {
					return new Promise(
						async resolver => {
							if (!el || el.length == 0) { return }
							if (new RegExp('\\d{6}\\.\\d{4}\\.\\d{8}\\-\\D{2}\\-\\d{3}','g').test(el.innerText)) {
								el.classList.add('maisPje_destaque_elemento_on');
								el.classList.remove('maisPje_destaque_elemento_off');
								let textocopiado = el.innerText.match(new RegExp('\\d{6}\\.\\d{4}\\.\\d{8}\\-\\D{2}\\-\\d{3}','g')).join();
								// let ta = document.createElement("textarea");
								// ta.textContent = textocopiado;
								// document.body.appendChild(ta);
								// ta.select();
								// document.execCommand("copy");
								// document.body.removeChild(ta);
								navigator.clipboard.writeText(textocopiado);
								browser.runtime.sendMessage({tipo: 'criarAlerta', valor: 'Número da ordem CNIB (' + textocopiado + ') copiada para a memória (CTRL + C)!!\n Use apenas CTRL + V para guardar essa informação..', icone: '5'});								
								setTimeout(async function() { 
									el.classList.add('maisPje_destaque_elemento_off');
									el.classList.remove('maisPje_destaque_elemento_on');
									document.body.removeEventListener("click", eventoCopiarNumeroOrdem);
									await sleep(1000);
									await clicarBotao('button','Imprimir');
								}, 1000);				
							}
							resolver(true);
							return;
						}
					);
				}
			}
		}
		
		async function preenchercamposCCS() {
			if (document.location.href.includes("bcb.gov.br/ccs")) {
				
				if (!document.querySelector('input[name="numeroProcesso"]')) {
					document.location.href = 'https://www3.bcb.gov.br/ccs/requisitarConsultaCpfCnpj.do?method=iniciar&maisPje=preencherCampos';
					return;
				}
				
				console.log("   |___PREENCHER CAMPOS");
				let lista_de_executados = await criarCaixaDeSelecaoComReclamados();
				fundo(true);
				if (!lista_de_executados) { return }
				acao1();
				
				//NUMERO DO PROCESSO
				function acao1() {
					console.log("      |___NUMERO DO PROCESSO");
					let el = document.querySelector('input[name="numeroProcesso"]');
					el.focus();
					
					let var1 = browser.storage.local.get('processo_memoria', function(result){
						el.value = result.processo_memoria.numero;
						triggerEvent(el, 'input');
						el.blur();
						acao2();
					});
				}
				
				//MOTIVO DA CONSULTA
				function acao2() {
					console.log("      |___MOTIVO DA CONSULTA");
					let el = document.querySelector('textarea[name="motivoConsulta"]');
					el.focus();
					el.value = 'Execução trabalhista';
					triggerEvent(el, 'input');
					el.blur();
					acao3();
				}
				
				//DATA DE INÍCIO
				function acao3() {
					console.log("      |___DATA DE INÍCIO");
					let el = document.querySelector('input[name="dataInicio"]');
					let hoje = new Date();
					let dt_inicio = new Date(parseInt(hoje.getFullYear()) - 1, hoje.getMonth(), 1).toLocaleDateString(); // período da consulta: um ano
					el.focus();
					el.value = dt_inicio;
					triggerEvent(el, 'input');
					el.blur();
					acao4();
				}
				
				//DATA DE FIM
				function acao4() {
					console.log("      |___DATA DE FIM");
					let el = document.querySelector('input[name="dataFim"]');
					let hoje = new Date().toLocaleDateString();
					el.focus();
					el.value = hoje;
					triggerEvent(el, 'input');
					el.blur();
					acao5();
				}
				
				//INSERÇÃO DOS RÉUS
				async function acao5() {
					console.log("      |___INSERÇÃO DOS RÉUS");
					let cpf_cnpj = "";
					let map = [].map.call(
						lista_de_executados, 
						function(reu) {
							console.log("      |___" + reu.nome + " ( " + reu.cpfcnpj + ")");
							cpf_cnpj = cpf_cnpj + reu.cpfcnpj + "\n"
						}
					);
					let el = document.querySelector('textarea[name="cpfCnpj"]');
					el.value = cpf_cnpj;
					triggerEvent(el, 'input');
					console.log("      |___FIM");
					fundo(false);
					
					//REQUISITAR DE CONSULTA
					let bt_continuar = await esperarElemento('input[value="Continuar"]');
					bt_continuar.focus();
					if (preferencias.modulo9.ccs[1]) { await timer(bt_continuar, preferencias.modulo9.ccs[5], 'orangered') }
				}
			}
		}
		
		async function preenchercamposPREVJUD(inverterPolo) {
			console.log("   |___PREENCHER CAMPOS");
			let lista_de_reclamantes;
			if (inverterPolo) {
				lista_de_reclamantes = await criarCaixaDeSelecaoComReclamantes();				
			} else {
				lista_de_reclamantes = await criarCaixaDeSelecaoComReclamados();
			}
			fundo(true);
			if (!lista_de_reclamantes) { return }
			
			acao1();
			
			//INSERÇÃO DOS RÉUS
			function acao1() {
				let var1 = browser.storage.local.get('processo_memoria', async function(result){			
					if (!result.processo_memoria.numero) {return}
					console.log(     '|___' + result.processo_memoria.numero.toString());
					fundo(true);
					//preenche os campos, mas o usuário tem que clicar em solicitar
					
					let el1 = await esperarElemento('MAT-CARD','SOLICITAR DOSSIÊ');
					await preencherInput('input[id="solicitacaoCpf"]', lista_de_reclamantes[0].cpfcnpj);
					await preencherInput('input[id="solicitacaoProcesso"]', result.processo_memoria.numero);
					
					let el2 = await esperarElemento('MAT-CARD','PESQUISA');
					await escolherOpcao('mat-select[id="pesquisaTipoChave"]', 'Processo', 2);
					await preencherInput('input[id="pesquisaChaveTexto"]', result.processo_memoria.numero);
					await clicarBotao('BUTTON','APLICAR');
					fundo(false);
				})
			}
		}
		
		async function preenchercamposPROTESTOJUD() {
			console.log("   |___PREENCHER CAMPOS");
			await esperarElemento('div[id="divPpal"]');
			await preencherCampos();
			
			async function preencherCampos() {
				browser.storage.local.get('processo_memoria', async function(result){
					if (!result.processo_memoria) { return }
					preferencias.processo_memoria = result.processo_memoria;
					
					let numeroProcessoDecomposto = await decomporNumeroProcesso(preferencias.processo_memoria.numero.toString());
					console.log("     |_____" + preferencias.processo_memoria.numero);
					let numeroestilizado = ("000000" + numeroProcessoDecomposto.numero).slice(-6) + "-" + numeroProcessoDecomposto.ano; // 00000000-00
					console.log("     |_____" + numeroestilizado);
					
					let erro = false;
					
					let campo1 = await esperarElemento('div','Número:[MMA]');
					await preencherInput(campo1,numeroestilizado);
					campo1.style.backgroundColor = '#00640073'; //#8b000052 erro
					console.log("     |_____preenchido o campo [Número:]");
								
					let campo2 = await esperarElemento('div','Nosso Número:[MMA]');
					await preencherInput(campo2,numeroestilizado);
					campo2.style.backgroundColor = '#00640073';
					console.log("     |_____preenchido o campo [Nosso Número:]");
								
					// let observacao = prompt("Recomenda-se colocar a data do decurso do prazo para pagamento (formato: dd/mm/yyyy):","");
					let observacao = new Date().toLocaleDateString();
					let campo3 = await esperarElemento('div','Data Emissão:[MMA]');
					await preencherInput(campo3,observacao);
					campo3.style.backgroundColor = '#00640073';
					console.log("     |_____preenchido o campo [Data Emissão:]");
								
					let campo4 = await esperarElemento('label','Espécie:[MMA]');
					campo4 = campo4.parentElement;
					let jg = (preferencias.processo_memoria.justicaGratuita) ? "SJG" : "SJ";
					erro = await selecionar(campo4,jg);
					campo4.style.backgroundColor = (erro) ? '#8b000052' : '#00640073';
					console.log("     |_____preenchido o campo [Espécie:] " + jg);
								
					let campo5 = await esperarElemento('span[id="vencimentoAvista"]');
					erro = await selecionar(campo5.querySelector('select').parentElement,'Vencimento à Vista');
					campo5.style.backgroundColor = (erro) ? '#8b000052' : '#00640073';
					console.log("     |_____preenchido o campo [Vencimento:]");
								
					let campo6 = await esperarElemento('label','Endosso:[MMA]');
					campo6 = campo6.parentElement;
					erro = await selecionar(campo6.querySelector('select').parentElement,'Mandato');
					campo6.style.backgroundColor = (erro) ? '#8b000052' : '#00640073';
					console.log("     |_____preenchido o campo [Endosso:]");
								
					let campo7 = await esperarElemento('label','Valor:[MMA]');
					campo7 = campo7.parentElement;
					let valorDevido = '';
					if (preferencias.processo_memoria.divida.valor) {
						valorDevido = Intl.NumberFormat('pt-br', {style: 'decimal', currency: 'BRL'}).format(preferencias.processo_memoria.divida.valor);
					}
					await preencherInput(campo7,valorDevido);
					campo7.style.backgroundColor = '#00640073';
					console.log("     |_____preenchido o campo [Valor:]");
								
					let campo8 = await esperarElemento('label','Saldo:[MMA]');
					campo8 = campo8.parentElement;
					let saldoDevido = '';
					if (preferencias.processo_memoria.divida.valor) {
						saldoDevido = Intl.NumberFormat('pt-br', {style: 'decimal', currency: 'BRL'}).format(preferencias.processo_memoria.divida.valor);
					}
					await preencherInput(campo8,saldoDevido);
					campo8.style.backgroundColor = '#00640073';
					console.log("     |_____preenchido o campo [Saldo:]");
								
					alert('maisPJe: Inserir o devedor e anexar a cópia dos cálculos do processo..');
				});		
				
			}
			
			async function preencherInput(elemento, valor) {
				if (!elemento) {return}
				if (valor == "") {return}
				
				let elInput = elemento.querySelector('input');
				elInput.focus();
				elInput.value = valor;
				
				triggerEvent(elInput, 'input');
				triggerEvent(elInput, 'change');
				triggerEvent(elInput, 'keyup');
			}
			
			async function selecionar(elemento, valor) {
				return new Promise(async resolve => {
					// console.log('entrou: ' + elemento + " : " + valor);
					ligar_mutation_observer();
					if (!elemento) {return}
					if (valor == "") {return}
					
					await clicarBotao(elemento.querySelector('button'));
					
					
					async function ligar_mutation_observer() {
						let observer_select = new MutationObserver(async function(mutationsDocumento) {
							mutationsDocumento.forEach( async function(mutation) {
								if (!mutation.addedNodes) { return }
								if (mutation.addedNodes.length > 1) {
									// let mutacao = Array.from(mutation.addedNodes).find(function(el){console.log(el.tagName + ":" + el.className + ":" + el.innerText)});
									let mutacao = Array.from(mutation.addedNodes).find(function(el){if(el.innerText.includes(valor)){return el}});
									if (mutacao) {
										console.log(mutacao.innerText);
										await clicarBotao('a[class="dropdown-item"]',valor);
										await sleep(1000);
										observer_select.disconnect();
										resolve(false);
									}
								}
							});
						});
						let configDocumento = { childList: true, subtree:true, characterData: true }
						observer_select.observe(document.body, configDocumento); //inicia o MutationObserver
						setTimeout(function() {
							observer_select.disconnect();
							resolve(true);
						}, 5000);  //Tem 5 segundos para preencher os campos e ir para o próximo. Se der erro, passa para o próximo campo e desliga o mutation depois de 5 segundos
					}
				});
			}
		}
		
		async function preenchercamposSNIPER() {
			console.log("   |___PREENCHER CAMPOS");
			let lista_de_executados = await criarCaixaDeSelecaoComReclamados(false);
			fundo(true);
			if (!lista_de_executados) { return }			
			console.log("      |___INSERÇÃO DOS RÉUS");
			await cadastro();
			
			//POR SEGURANÇA E DIANTE DA COMPLEXIDADE SÓ PERMITE CADASTRAR UM POR VEZ
			async function cadastro() {				
				console.log("      |___" + lista_de_executados[0].nome + " ( " + lista_de_executados[0].cpfcnpj + ")");
				
				let el = await esperarElemento('div[class="graph-search"] input[name="search"]');
				await preencherInput('div[class="graph-search"] input[name="search"]', lista_de_executados[0].cpfcnpj);
				el.blur(); //tirar o foco para quando for pressionar p
				await esperarElemento('div[class="graph-search"] ul[class="autocomplete-result"] li');
				await clicarBotao('div[class="graph-search"] span[type="submit"]');
				await aguardarCarregamento(); //aguardar preencher no canvas
				await clicarBotao(document.querySelector('button[id="maisPje_assistenteImpressao_bt_copiar"]'));
				fundo(false);
			}
			
			async function aguardarCarregamento() {
				return new Promise(async resolve => {					
					let spinner = await esperarElemento('div[class="spinner-element"][style*="display: block"]',null,3000);
					console.log('aguardando carregamento...')
					if (spinner) {
						let check = setInterval(function() {
							if (spinner.style.display == 'none') {
								console.log('carregado...')
								clearInterval(check);
								return resolve(true);
							}
						}, 100);
					} else {
						return resolve(false);
					}
				});
			}
		}
		
		async function preenchercamposCENSEC() {
			console.log("   |___PREENCHER CAMPOS");
			let lista_de_executados = await criarCaixaDeSelecaoComReclamados(false);
			fundo(true);
			if (!lista_de_executados) { return }			
			console.log("      |___INSERÇÃO DOS RÉUS");
			await cadastro();
			
			//POR SEGURANÇA E DIANTE DA COMPLEXIDADE SÓ PERMITE CADASTRAR UM POR VEZ
			async function cadastro() {				
				console.log("      |___" + lista_de_executados[0].nome + " ( " + lista_de_executados[0].cpfcnpj + ")");
				let el = await esperarElemento('app-public-query input[formcontrolname="cpfCnpj"]');
				let cpfCnpjSoNumeros = lista_de_executados[0].cpfcnpj.replace(/\D/g,"");
				await preencherInput('app-public-query input[formcontrolname="cpfCnpj"]', cpfCnpjSoNumeros);
				el.blur(); //tirar o foco para quando for pressionar p
				await clicarBotao('app-public-query button','Buscar');
				await sleep(1000);
				await clicarBotao(document.querySelector('button[id="maisPje_assistenteImpressao_bt_copiar"]'));
				fundo(false);
			}
		}
		
		async function preenchercamposCELESC() {
			console.log("   |___PREENCHER CAMPOS");
			let lista_de_executados = await criarCaixaDeSelecaoComReclamados(false);
			fundo(true);
			if (!lista_de_executados) { return }			
			console.log("      |___INSERÇÃO DOS RÉUS");
			await cadastro();
			
			//SÓ PERMITE CADASTRAR UM POR VEZ
			async function cadastro() {				
				console.log("      |___" + lista_de_executados[0].nome + " ( " + lista_de_executados[0].cpfcnpj + ")");
				let cpfCnpjSoNumeros = lista_de_executados[0].cpfcnpj.replace(/\D/g,"");
				await preencherInput('input[id="id_cpf_cnpj"]', cpfCnpjSoNumeros);
				await clicarBotao('button','Pesquisar');
				fundo(false);
			}
		}
		
		async function preenchercamposCASAN() {
			console.log("   |___PREENCHER CAMPOS");
			let lista_de_executados = await criarCaixaDeSelecaoComReclamados(false);
			fundo(true);
			if (!lista_de_executados) { return }			
			console.log("      |___INSERÇÃO DOS RÉUS");
			await cadastro();
			
			//SÓ PERMITE CADASTRAR UM POR VEZ
			async function cadastro() {				
				console.log("      |___" + lista_de_executados[0].nome + " ( " + lista_de_executados[0].cpfcnpj + ")");
				
				let el = document.querySelector('input[class="form-control"]');
				el.value = lista_de_executados[0].cpfcnpj;
				el.focus();
				triggerEvent(el,'input');
				
				let el2 = document.querySelector('input[value="Consultar"]');
				triggerEvent(el2,'click');				
				
				await sleep(1000);
				triggerEvent(document.querySelector('form[method="post"]'), 'submit');
				fundo(false);
			}
		}
		
		async function preenchercamposSIGEF() {
			console.log("   |___PREENCHER CAMPOS");
			let lista_de_executados = await criarCaixaDeSelecaoComReclamados(false);
			fundo(true);
			if (!lista_de_executados) { return }			
			console.log("      |___INSERÇÃO DOS RÉUS");
			await cadastro();
			
			//POR SEGURANÇA E DIANTE DA COMPLEXIDADE SÓ PERMITE CADASTRAR UM POR VEZ
			async function cadastro() {				
				console.log("      |___" + lista_de_executados[0].nome + " ( " + lista_de_executados[0].cpfcnpj + ")");
				await preencherInput('input[id="id_cpf_cnpj"]', lista_de_executados[0].cpfcnpj);
				await preencherInput('input[id="id_proprietario"]', lista_de_executados[0].nome);				
				fundo(false);
			}			
		}
		
		async function preenchercamposINFOSEG() {
			console.log("   |___PREENCHER CAMPOS");
			let lista_de_executados = await criarCaixaDeSelecaoComReclamados(false);
			fundo(true);
			if (!lista_de_executados) { return }			
			console.log("      |___INSERÇÃO DO EXECUTADO");
			await cadastro();
			
			//POR SEGURANÇA E DIANTE DA COMPLEXIDADE SÓ PERMITE CADASTRAR UM POR VEZ
			async function cadastro() {				
				console.log("      |___" + lista_de_executados[0].nome + " ( " + lista_de_executados[0].cpfcnpj + ")");
				await preencherInput('input[id="q"]', lista_de_executados[0].cpfcnpj);
				await clicarBotao('button[id="salvar"]');
				await sleep(2000)
				for (const [pos, el] of document.querySelectorAll('div[id="mainContainer"] input[type="checkbox"]').entries()) {
					if (!el.checked) {
						el.click();
						await sleep(250);
					}
				}
				fundo(false);
			}			
		}
		
		async function novaMinutaAJJT() {
			console.log('novaMinutaAJJT')
			document.location.href = 'https://aj.sigeo.jt.jus.br/aj/nomeacao/nomearprofissionais/nomearprofissionais_index.jsf?prosseguirMinuta=true';
			
		}
		
		async function consultarMinutaAJJT() {
			console.log('consultarMinutaAJJT')
			document.location.href = 'https://aj.sigeo.jt.jus.br/aj/pagamento/mantersolicitacaopagamento/mantersolicitacaopagamento_principal.jsf?prosseguirPesquisa=true';
		}		
	
		async function registrarPagamentoGPREC() {
			let prefixo = document.location.href.substring(0, document.location.href.search("/gprec/"));
			document.location.href = prefixo + '/gprec/view/private/rpv/rpv_pagamento_lista.xhtml';
		}
		
		async function consultarRpvGprec() {
			document.location.href = prefixo + '/gprec/view/private/rpv/rpv_lista.xhtml';
		}
	}
}

//MONITORES MUTATION OBSERVER

async function monitor_janela_tarefa() {
	console.log("Extensão maisPJE (" + agora() + "): monitor_janela_tarefa");
	let elParaCorrigirOCabecalho, posicaoAnterior, posicaoAtual;
	let observerDocumento = new MutationObserver(async function(mutationsDocumento) {
		mutationsDocumento.forEach(async function(mutation) {
			if (!mutation.addedNodes[0]) { return }
			if (!mutation.addedNodes[0].tagName) { return }
			
			if (!elParaCorrigirOCabecalho) { 
				elParaCorrigirOCabecalho = document.querySelector('pje-cabecalho-tarefa');
				posicaoAnterior = elParaCorrigirOCabecalho?.getBoundingClientRect().bottom;
			}
			
			posicaoAtual = elParaCorrigirOCabecalho?.getBoundingClientRect().bottom;
			// console.log('***************' + posicaoAnterior + ' : ' + posicaoAtual)
			if (posicaoAtual < posicaoAnterior) {
				console.debug('maisPJe: corrigindo o cabeçalho da Janela Detalhes do Processo')
				corrigeCabecalho();
			}
			
			if (document.location.href.includes("/minutar") || document.location.href.includes("/assinar")) { //tela minutar ou assinar DESPACHO/DECISÃO/SENTENÇA
				// console.log('mutation.target.tagName: ' + mutation.target.tagName + ' class=' + mutation.target.className);
				// console.log('   |___mutation.addedNodes[0].tagName: ' + mutation.addedNodes[0].tagName + ' class=' + mutation.addedNodes[0].className);				
				
				if (mutation.addedNodes[0].tagName == "DIV") { //INCLUI O BOTÃO DE ZOOM NO EDITOR DE TEXTOS
					if (mutation.addedNodes[0].getAttribute('aria-label')) {
						if (mutation.addedNodes[0].getAttribute('aria-label').includes('Ferramentas do Editor') && !document.getElementById('extensaoPje_barra_zoom_editor')) {
							addZoom_Editor();
						}
					}
				}
				
				//
				if (mutation.addedNodes[0].tagName == "PJE-INTIMACAO-AUTOMATICA") { //INCLUI OS BOTÕES 
					let controleIntimacao = await esperarElemento('div[class="controle-intimacao"]');
					if (controleIntimacao) {
						addBotaoPrazoEmLote();
						addBotaoMarcarDesmarcarTodos();
					}
				}
				
				if (mutation.addedNodes[0].tagName == "CANVAS") { //INCLUI O BOTÃO COPIAR TRANSCRIÇÃO
					let cabecalhoDireita = await esperarElemento('div[class="cabecalho-direita"]');
					if (cabecalhoDireita) {
						addBotaoCopiarDocumento();
					}
				}
				
				
				if (mutation.addedNodes[0].tagName == "UL") { //INCLUI A OPÇÃO DE INVERTER IDS
					if (mutation.addedNodes[0].className.includes("ck-list")) {
						if (preferencias.extrasEditorInverterOrdem) {
							mutation.addedNodes[0].style = "display: flex;flex-direction: column;";
						}
						let lista = mutation.addedNodes[0].querySelectorAll('li');
						for (let [pos, linha] of lista.entries()) {
							let span = linha.querySelector('span');
							if (span.innerText.length <= 0) {
								if (preferencias.extrasEditorOcultarAutotexto) {
									linha.remove();
								} else {
									linha.style = 'order: ' + (10000 + lista.length - pos) + ";";
								}
							} else {
								linha.style = 'order: ' + (lista.length - pos) + ";";
							}							
						}
					}
				}
			}
		});
	});		
	let configDocumento = { childList: true, subtree:true }
	observerDocumento.observe(document.body, configDocumento); //inicia o MutationObserver
}

async function monitor_documento_JanelaDetalhes() {
	console.log("Extensão maisPJE (" + agora() + "): iniciarMonitorDeDocumentos");
	
	let elParaCorrigirOCabecalho, posicaoAnterior, posicaoAtual;	
	let observerDocumento = new MutationObserver(async function(mutationsDocumento) {
		mutationsDocumento.forEach(async function(mutation) {
			
				if (!mutation.addedNodes[0]) { return }
				
				if (!elParaCorrigirOCabecalho) { 
					elParaCorrigirOCabecalho = document.querySelector('pje-resumo-processo');
					posicaoAnterior = elParaCorrigirOCabecalho?.getBoundingClientRect().bottom;
				}
				
				posicaoAtual = elParaCorrigirOCabecalho?.getBoundingClientRect().bottom;
				// console.log('***************' + posicaoAnterior + ' : ' + posicaoAtual)
				if (posicaoAtual < posicaoAnterior) {
					console.debug('maisPJe: corrigindo o cabeçalho da Janela Detalhes do Processo')
					corrigeCabecalho();
				}
				
				
				// console.log('************' + mutation.target.tagName + "    :    " + mutation.target.className)
				// console.log(mutation.target.tagName + " : " + mutation.target.getAttribute('aria-label') + " : " + mutation.addedNodes[0].tagName + " : " + mutation.addedNodes[0].className)
				
				if (mutation.target.tagName == 'PJE-CABECALHO-PROCESSO') {
					let ojCargo = await esperarElemento('pje-cabecalho-processo section[class="oj-cargo"]');
					
					if (preferencias.meuFiltro[10] && ojCargo.innerText.toLowerCase().includes('titular')) {
						ojCargo.classList.add('efeitoMarcaTexto');
					}
					
					if (preferencias.meuFiltro[11] && ojCargo.innerText.toLowerCase().includes('substituto')) {
						ojCargo.classList.add('efeitoMarcaTexto');
					}
				}
				
				if (mutation.addedNodes[0].tagName == 'PJE-HISTORICO-SCROLL-DOCUMENTO') { // conteudo-documento
					if (mutation.target.getElementsByTagName('object')[0]) { //modelo novo
						let id_div_documento_principal = mutation.target.getElementsByTagName('object')[0].id.replace("obj", "");
						await addBotoesDocumentoCarregado(id_div_documento_principal);
						await addBotaoCopiarDocumento(id_div_documento_principal);
						
					} else { //modelo antigo
						if (!document.getElementsByTagName('pje-historico-scroll-titulo')[0]) { return }
						if (!document.getElementsByTagName('pje-historico-scroll-titulo')[0].querySelector('button[aria-label="Certidão"]')) { return }
						if (!document.getElementsByTagName('pje-historico-scroll-titulo')[0].querySelector('button[aria-label="Certidão"]').parentElement) { return }
						let el = document.getElementsByTagName('pje-historico-scroll-titulo')[0].querySelector('button[aria-label="Certidão"]').parentElement;
						let id_div_documento_principal = el.href.substring(el.href.search('documento/') + 10);
						id_div_documento_principal = id_div_documento_principal.replace('/certidao','');
						await addBotoesDocumentoCarregado(id_div_documento_principal);
						await addBotaoCopiarDocumento(id_div_documento_principal);
					}
				}
				
				if (mutation.addedNodes[0].tagName == 'PJE-GIGS-CADASTRO-ATIVIDADES') {
					gigsInserirBorrachaResponsavel();
				}
				
				
				//atualização do checklist de execução.
				if (mutation.target.tagName == 'MAT-EXPANSION-PANEL-HEADER' &&  mutation.addedNodes[0].tagName == 'SPAN' && mutation.addedNodes[0].className.includes('ng-animating')) {
					let ancora = mutation.target.parentElement.parentElement;
					if (ancora && ancora.id.includes('grupo-executados')) {
						mutation.target.addEventListener('click', async function () {
							await mapearChecklistExecucao(mutation.target);
						});
					}
				}
				
				if (mutation.target.tagName == 'DIV' && mutation.target.className.includes('cabecalho-direita') && mutation.addedNodes[0].tagName == 'BUTTON') {
					if (!mutation.addedNodes[0].getAttribute('aria-label')) { return }
					if (mutation.addedNodes[0].getAttribute('aria-label').includes('Histórico de versões')) {
						if (mutation.target.getElementsByTagName('object')[0]) { //modelo novo
							let id_div_documento_principal = mutation.target.getElementsByTagName('object')[0].id.replace("obj", "");
							await addBotaoCopiarDocumento(id_div_documento_principal);
						} else { //modelo antigo
							if (!document.getElementsByTagName('pje-historico-scroll-titulo')[0]) { return }
							if (!document.getElementsByTagName('pje-historico-scroll-titulo')[0].querySelector('button[aria-label="Certidão"]')) { return }
							if (!document.getElementsByTagName('pje-historico-scroll-titulo')[0].querySelector('button[aria-label="Certidão"]').parentElement) { return }
							let el = document.getElementsByTagName('pje-historico-scroll-titulo')[0].querySelector('button[aria-label="Certidão"]').parentElement;
							let id_div_documento_principal = el.href.substring(el.href.search('documento/') + 10);
							id_div_documento_principal = id_div_documento_principal.replace('/certidao','');
							await addBotaoCopiarDocumento(id_div_documento_principal);
						}
					}
					
				}
				
				if (mutation.target.tagName == 'DIV' && mutation.addedNodes[0].tagName == 'MAT-CHECKBOX') {
					let ancora = mutation.addedNodes[0].firstElementChild;
					let elementoPai = mutation.target.parentElement;
					if (elementoPai.id.includes('doc_')) {
						ancora.addEventListener('click', async function () {
						selecaoEmLote(this.parentElement.parentElement.parentElement);
						});
					}
				}
		});
	});		
	let configDocumento = { childList: true, characterData: true, subtree:true }
	observerDocumento.observe(document.body, configDocumento); //inicia o MutationObserver
	
	
	async function mapearChecklistExecucao(executado) {
		return new Promise(async resolve => {
			
			if (executado) {
				if (!executado.getAttribute('maisPje')) {
					if (!executado.parentElement.querySelector('table[name="Lista de Atividades de Execução"]')) { return resolve(true);}					
					executado.setAttribute('maisPje',true);
					executado.classList.add("maisPje_checklist_cabecalho");					
					let linhas = executado.parentElement.querySelectorAll('table[name="Lista de Atividades de Execução"] tr');
					for (const [pos, linha] of linhas.entries()) {
						linha.classList.add("maisPje_checklist_linha");
						linha.onclick = async function () {
							if (new RegExp('\\d{2}\\/\\d{2}\\/\\d{4}').test(linha.innerText)) {
								let data = linha.innerText.match(new RegExp('\\d{2}\\/\\d{2}\\/\\d{4}')).join();
								let dataConvertida = await converterDataTimeline(data);
								console.log('Data encontrada: ' + dataConvertida);								
								let naTimeLine = await esperarElemento('div[name="dataItemTimeline"]',dataConvertida);
								naTimeLine.scrollIntoView({behavior: 'smooth',block: 'start'});
								naTimeLine.parentElement.querySelector('a[class="tl-documento"]').click();
								
								//corrige cabeçalho da janela detalhes
								let cabecalho = document.querySelector('mat-sidenav-container[class*="mat-drawer-container"]');							
								if (!cabecalho) { return }
								cabecalho.style.setProperty("position", "relative", "important");
								cabecalho.style.setProperty("height", "auto", "important");
							}
						}
					}
				}
				resolve(true);
			} else {
				let ancora = await esperarElemento('div[id="grupo-executados"]',false,2000);
				if (!ancora) { return resolve(false)}
				await sleep(2000); //dar tempo de carregar toda timeline do processo.. aqui não tem pressa
				let executados = ancora.querySelectorAll('mat-expansion-panel mat-expansion-panel-header');
				for (const [pos, executado] of executados.entries()) {
					if (!executado.getAttribute('maisPje')) {
						executado.setAttribute('maisPje',true);
						executado.classList.add("maisPje_checklist_cabecalho");						
						let linhas = executado.parentElement.querySelectorAll('table[name="Lista de Atividades de Execução"] tr');
						for (const [pos, linha] of linhas.entries()) {
							linha.classList.add("maisPje_checklist_linha");
							linha.onclick = async function () {
								if (new RegExp('\\d{2}\\/\\d{2}\\/\\d{4}').test(linha.innerText)) {
									let data = linha.innerText.match(new RegExp('\\d{2}\\/\\d{2}\\/\\d{4}')).join();
									let dataConvertida = await converterDataTimeline(data);
									console.log('Data encontrada: ' + dataConvertida);								
									let naTimeLine = await esperarElemento('div[name="dataItemTimeline"]',dataConvertida);
									naTimeLine.scrollIntoView({behavior: 'smooth',block: 'start'});
									naTimeLine.parentElement.querySelector('a[class="tl-documento"]').click();

									//corrige cabeçalho da janela detalhes
									let cabecalho = document.querySelector('mat-sidenav-container[class*="mat-drawer-container"]');							
									if (!cabecalho) { return }
									cabecalho.style.setProperty("position", "relative", "important");
									cabecalho.style.setProperty("height", "auto", "important");
								}
							}
						}
					}
				}
				resolve(true);
			}
		});
	}
	
	async function converterDataTimeline(inputFormat) {
		console.log("Inicio: " + inputFormat);
		inputFormat = inputFormat.replace("\/01\/" , " jan. ");
		inputFormat = inputFormat.replace("\/02\/" , " fev. ");
		inputFormat = inputFormat.replace("\/03\/" , " mar. ");
		inputFormat = inputFormat.replace("\/04\/" , " abr. ");
		inputFormat = inputFormat.replace("\/05\/" , " mai. ");
		inputFormat = inputFormat.replace("\/06\/" , " jun. ");
		inputFormat = inputFormat.replace("\/07\/" , " jul. ");
		inputFormat = inputFormat.replace("\/08\/" , " ago. ");
		inputFormat = inputFormat.replace("\/09\/" , " set. ");
		inputFormat = inputFormat.replace("\/10\/" , " out. ");
		inputFormat = inputFormat.replace("\/11\/" , " nov. ");
		inputFormat = inputFormat.replace("\/12\/" , " dez. ");
		console.log("Fim: " + inputFormat);
		return inputFormat;
	}

	//FUNÇÃO RESPONSÁVEL POR SELECIONAR OS ANEXOS DO DOCUMENTO PRINCIPAL NOS CASOS DE SELEÇÃO EM LOTE DO PJE
	async function selecaoEmLote(pai) {
		let ancora = pai.querySelectorAll('input[aria-label="Selecionar anexo"]');
		for (const [pos, anexo] of ancora.entries()) {
			anexo.click();
		}
	}

}

async function monitor_Janela_Principal() {
	let janelaPrincipal = await esperarElemento('button[aria-label="Menu Completo"]', null, 500); //esperar por 0.5 segundo
	if (janelaPrincipal) {
		let existeMonitor = await criar_elemento_monitor('MAISPJEMONITORJANELAPRINCIPAL');
		if (!existeMonitor) {
			console.log("Extensão maisPJE (" + agora() + "): monitor_janela_principal");
			let observerJanelaPrincipal = new MutationObserver(async function(mutationsDocumento) {
				mutationsDocumento.forEach(async function(mutation) {
					// console.log(mutation.target.tagName + " : " + mutation.target.className);
					//PAINEL DE PERÍCIAS
					if (mutation.target.tagName == 'PJE-DATA-TABLE') {				
						let menuAtivo = mutation.target.getAttribute('nametabela');
						
						switch(menuAtivo) {
							case "Tabela de Processos": //o GIGS processos de Gabinete também cai aqui
								await montarFiltrosFavoritos();
								await inserirBotaoGuardarFiltroFavorito();
								await inserirBotaoCopiarListaDeProcessos();
							case "Tabela de Atividades":
								await montarFiltrosFavoritos();
								await inserirBotaoGuardarFiltroFavorito();
								await inserirBotaoCopiarListaDeProcessos();
							case "Tabela de Comentários":
								await montarFiltrosFavoritos();
								await inserirBotaoGuardarFiltroFavorito();
								await inserirBotaoCopiarListaDeProcessos();
							case "Tabela de Perícias":
								console.log('Janela Principal - Painel de Perícias');
								console.log('maisPje: Identificada a tabela: ' + mutation.target.getAttribute('nametabela'));
								
								let el = document.querySelector('pje-data-table[nametabela*="Tabela de Perícias"]');
								if (!el) { return }
								
								if (!document.getElementById('maisPje_pauta_pericia')) {
									let ancora = document.querySelector('div[class="secao-filtros"]');
									let botao = document.createElement("button");
									botao.id = "maisPje_pauta_pericia";
									botao.textContent = "Exibir a Localização dos Processos";
									botao.style = "cursor: pointer; position: relative; top: 20%; padding: 5px; margin: 5px; height: 35px; z-index: 1;";
									botao.onclick = function () {painelPericiaTarefaProcesso()};
									ancora.appendChild(botao);
								}
							default:
								return;
						}
					}
					
					if (!mutation.removedNodes[0] && !mutation.addedNodes[0]) { return }
					
					if (mutation.addedNodes[0]) {
						if (!mutation.addedNodes[0].tagName) { return }
						
						// console.log('ADD: ' + mutation.addedNodes[0].tagName + " : " + mutation.addedNodes[0].className + " : " + mutation.addedNodes[0].innerText);
						
						if (mutation.addedNodes[0].tagName == 'PJE-HOME') {
							console.log('Janela Principal - Troca de Perfil');
							await obterOJdoUsuario();
						}
						
						// if (mutation.addedNodes[0].tagName == 'PJE-GIGS-MEU-PAINEL') {
							// console.log('Janela Principal - Meu Painel');
						// }
						
						if (mutation.addedNodes[0].tagName == 'PJE-PAINEL-GLOBAL') {
							console.log('Janela Principal - Painel Global');
							if (mutation.addedNodes[0].innerText.includes('Exibir todos')) {
								await montarFiltrosFavoritos();
							}

						}
						
						// if (mutation.addedNodes[0].tagName == 'PJE-PETICOES-JUNTADAS') {
							// console.log('Janela Principal - Escaninho');					
						// }
						
						if (mutation.addedNodes[0].tagName == 'PJE-ATA-AUDIENCIAS') {
							console.log('Janela Principal - Verificar Atas de Audiência');
						}
						
						if (mutation.addedNodes[0].tagName == 'MAT-PROGRESS-SPINNER' && document.location.href.includes('/pauta-inteligente')) {
							console.log('Janela Principal - Pauta Inteligente');
							conciLIAnaPauta();
						}
						
						// if (mutation.addedNodes[0].tagName == 'PJE-PAUTA-AUDIENCIAS') {
							// console.log('Janela Principal - Pauta de Audiência');
						// }
						
						// if (mutation.addedNodes[0].tagName == 'PJE-DESIGNACAO-AUTOMATICA') {
							// console.log('Janela Principal - Designação Automática de Responsável');
						// }
						
						//TRIAGEM INICIAL
						if (document.querySelector('span[aria-level="1"]')) {
							//TRIAGEM INICIAL
							if (document.querySelector('span[aria-level="1"]').innerText.includes('Novos Processos')) {
								if (!document.querySelector('span[aria-level="1"]').hasAttribute('maisPje')) {
									console.log('**************CONCILIAJT NA TRIAGEM INICIAL');
									document.querySelector('span[aria-level="1"]').setAttribute('maisPje','true');
									conciLIAnaTriagemInicial();
									
									//adiciona os listener de troca de página
									document.querySelectorAll('pje-paginador mat-select div[class*="mat-select-trigger"]')[0].addEventListener('click', async function(event) {
										await aguardarCarregamentoTabela();
										await sleep(1000);
										conciLIAnaTriagemInicial();
									});
									
									document.querySelectorAll('pje-paginador mat-select div[class*="mat-select-trigger"]')[1].addEventListener('click', async function(event) {
										await aguardarCarregamentoTabela();
										await sleep(1000);
										conciLIAnaTriagemInicial();
									});
									
									document.querySelector('button[aria-label="Primeiro"]').addEventListener('click', async function(event) {
										await aguardarCarregamentoTabela();
										await sleep(1000);
										conciLIAnaTriagemInicial();
									});
									
									document.querySelector('button[aria-label="Anterior"]').addEventListener('click', async function(event) {
										await aguardarCarregamentoTabela();
										await sleep(1000);
										conciLIAnaTriagemInicial();
									});
									
									document.querySelector('button[aria-label="Próximo"]').addEventListener('click', async function(event) {
										await aguardarCarregamentoTabela();
										await sleep(1000);
										conciLIAnaTriagemInicial();
									});
									
									document.querySelector('button[aria-label="Último"]').addEventListener('click', async function(event) {
										await aguardarCarregamentoTabela();
										await sleep(1000);
										conciLIAnaTriagemInicial();
									});
								}
							
							//AGUARDANDO AUDIÊNCIA
							} else if (document.querySelector('span[aria-level="1"]').innerText.includes('Audiência')) {
								if (!document.querySelector('span[aria-level="1"]').hasAttribute('maisPje')) {
									console.log('**************função aguardando audiência - processos sem audiência designada');
									document.querySelector('span[aria-level="1"]').setAttribute('maisPje','true');
									processosSemAudienciaDesignada();
									
									//adiciona os listener de troca de página
									document.querySelectorAll('pje-paginador mat-select div[class*="mat-select-trigger"]')[0].addEventListener('click', async function(event) {
										await aguardarCarregamentoTabela();
										await sleep(1000);
										processosSemAudienciaDesignada();
									});
									
									document.querySelectorAll('pje-paginador mat-select div[class*="mat-select-trigger"]')[1].addEventListener('click', async function(event) {
										await aguardarCarregamentoTabela();
										await sleep(1000);
										processosSemAudienciaDesignada();
									});
									
									document.querySelector('button[aria-label="Primeiro"]').addEventListener('click', async function(event) {
										await aguardarCarregamentoTabela();
										await sleep(1000);
										processosSemAudienciaDesignada();
									});
									
									document.querySelector('button[aria-label="Anterior"]').addEventListener('click', async function(event) {
										await aguardarCarregamentoTabela();
										await sleep(1000);
										processosSemAudienciaDesignada();
									});
									
									document.querySelector('button[aria-label="Próximo"]').addEventListener('click', async function(event) {
										await aguardarCarregamentoTabela();
										await sleep(1000);
										processosSemAudienciaDesignada();
									});
									
									document.querySelector('button[aria-label="Último"]').addEventListener('click', async function(event) {
										await aguardarCarregamentoTabela();
										await sleep(1000);
										processosSemAudienciaDesignada();
									});
								}
							}
						}
						
						if (mutation.addedNodes[0].tagName == 'PJE-GIGS-FICHA-PROCESSO') {
							addBotaoGigs();
						}
						
						if (mutation.addedNodes[0].tagName == 'PJE-GIGS-CADASTRO-ATIVIDADES') {
							gigsInserirBorrachaResponsavel();
						}
						
						//opções do gigs Tipos de atividade. Aciona apenas a primeira vez que o elemento aparece
						if (mutation.addedNodes[0].tagName == 'LABEL' && mutation.addedNodes[0].innerText.includes('Tipo de Atividade')) {
							if (document.querySelector('pje-gigs-cadastro-atividades')) {
								let ListaDetiposDeAtividade = await esperarElemento('div[role="listbox"]', null, 60000); //espera por um minuto
								if (!ListaDetiposDeAtividade) { return }
								ListaDetiposDeAtividade.addEventListener('click', async function(event) {
									gigsAtribuirResponsavel(event.target);
								});
							}
						}
						
						//TELA RELATÓRIO GIGS				
						if (mutation.addedNodes[0].tagName == 'PJE-GIGS-RELATORIO-ATIVIDADES' || mutation.addedNodes[0].tagName == 'PJE-GIGS-RELATORIO-COMENTARIOS' || mutation.addedNodes[0].tagName == 'PJE-GIGS-RELATORIO-PROCESSOS') {
							console.log('Janela Principal - ' + mutation.addedNodes[0].tagName);
							monitorRelatorioGigs();
							
							//botão exportarLista
							let btExportarLista = await esperarElemento('button[id="maisPje_bt_principal_5"]', null, 100);
							if (!btExportarLista) {
								console.log('MaisPJe: inserir botão exportarLista')
								
								let ancora = await esperarElemento('button[aria-label="Limpar Filtro"]');
								if (!ancora) { return }
								if (!document.getElementById('maisPje_tooltip_abaixo3')) {
									tooltip('abaixo3');
								}
								
								let botao = document.createElement("button");
								botao.id = "maisPje_bt_principal_5";
								botao.classList.add("mat-focus-indicator", "mat-tooltip-trigger", "mat-icon-button", "mat-button-base");
								botao.setAttribute("maispje-tooltip-abaixo3", "maisPje: Exportar lista");
								botao.onclick = function () {recuperarListaRelatorioGigs()};
								
								let botao_span = document.createElement("span");
								botao_span.classList.add("mat-button-wrapper");
								
								let botao_icone = document.createElement("i");
								botao_icone.setAttribute('aria-hidden','true'); //faz com que o NVDA ignore o elemento
								botao_icone.classList.add("mat-tooltip-trigger", "fa", "fa-download", "icone-clicavel");
								botao_icone.style.cssText += 'font-size: 20px; line-height: 44px; color: orangered;';
								
								botao_span.appendChild(botao_icone);						
								botao.appendChild(botao_span);
								ancora.parentElement.appendChild(botao);
							}
						}
						
						//TELA ESCANINHO > SITUAÇÃO DO ALVARÁ
						if (mutation.addedNodes[0].tagName == 'NG-COMPONENT') {
							if (!preferencias.modulo9.sif) { return }
							let el = document.querySelector('pje-data-table[nametabela*="Tabela de situação do alvará"]');
							if (!el) { return }							
							let ancora = await esperarElemento('div[class="div-estatisticas"]');
							if (!document.querySelector('button[id="maisPje_bt_alvarás_conferencia"]')) {
								let botao = document.createElement("button");
								botao.id = "maisPje_bt_alvarás_conferencia";
								botao.textContent = "Exibir Alvarás para Conferência";
								botao.style = "cursor: pointer; position: relative; padding: 5px; margin: 5px; height: auto; z-index: 1;";
								botao.onclick = function () { janelaAlvarasSIF('AGUARDANDO_CONFERENCIA') };
								ancora.appendChild(botao);
							}
						}
					
						//TELA PAUTA MENSAL DE AUDIÊNCIAS
						if (document.querySelector('pje-pauta-audiencias') && document.querySelector('table[name*="Horários do"]') && preferencias.modulo10_juntadaMidia[0]) {
							if (mutation.addedNodes[0].tagName != 'TR') { return }
							let padrao = /\d{7}\-\d{2}\.\d{4}\.\d{1}\.\d{2}\.\d{4}/g;				
							if (padrao.test(mutation.addedNodes[0].innerText)) {
								let numeroProcesso = mutation.addedNodes[0].innerText.match(padrao).join();							
							
								if (numeroProcesso) {
									let ancora = mutation.addedNodes[0].querySelector('a[aria-label="Abrir processo"]') || mutation.addedNodes[0].querySelector('a[aria-label="Abrir Processo"]');
									
									let botaoModulo10 = document.createElement("a");										
									botaoModulo10.style = "cursor: pointer; position: relative; vertical-align: -moz-middle-with-baseline; padding: 5px; top: -1px; z-index: 6; opacity: 1; font-size: 1.5rem; margin: 0; color: rgb(66, 63, 71);";
									botaoModulo10.title = '+PJe: Anexar Vídeos de Audiência';
									botaoModulo10.onmouseenter = function () {this.style.color = 'rgb(66, 63, 71,0.5)'};
									botaoModulo10.onmouseleave = function () {this.style.color = 'rgb(66, 63, 71)'};
									botaoModulo10.onclick = function () {
										let var1 = browser.storage.local.set({'tempBt': ['acao_bt_aaAnexar', 997]});
										Promise.all([var1]).then(values => {
											getAtalhosNovaAba().anexarDocumentos.abrirAtalhoemNovaJanela(false, false, numeroProcesso);
										});
									};
									
									let i1Modulo10 = document.createElement("i");
									i1Modulo10.className = "fas fa-video";
									
									let i2Modulo10 = document.createElement("i");
									i2Modulo10.className = "fas fa-plus";
									i2Modulo10.style = "position: absolute; color: white; left: 0.7em; top: 1.3em; font-size: 0.5em;";
									
									botaoModulo10.appendChild(i1Modulo10);
									botaoModulo10.appendChild(i2Modulo10);
									// base.appendChild(botaoModulo10);
									ancora.parentElement.parentElement.insertBefore(botaoModulo10, ancora.parentElement);
									
								}
							}
						}
					
					}
					
					if (mutation.removedNodes[0]) {
						if (!mutation.removedNodes[0].tagName) { return }
						
						// console.log('DEL: ' + mutation.removedNodes[0].tagName + " : " + mutation.removedNodes[0].className + " : " + mutation.removedNodes[0].innerText);
						
						if (mutation.removedNodes[0].tagName == 'DIV' && mutation.removedNodes[0].className.includes('menu-selecao-perfil-usuario')) {
							let el = document.querySelector('div[class*="menu-selecao-perfil-usuario"]');
							if (!el) { return }
							el.addEventListener('click', function(event) {
								if (event.target.checked) {
									let temp = event.target.getAttribute('aria-label') || event.target.parentElement.getAttribute('aria-label');
									browser.storage.local.set({'perfilUsuario': temp});
								}
							});						
						}
					}
					
				});
			});
			observerJanelaPrincipal.observe(document.body, { childList: true, subtree:true }); //inicia o MutationObserver
			await obterOJdoUsuario();
		}
		
		//atualiza o grau do usuario
		await apiObterGraudeJurisdicaoDoPerfil();
	}
	
	async function monitorRelatorioGigs() {
		console.log("Extensão maisPJE (" + agora() + "): monitorRelatorioGigs");
		let target = document.querySelector('pje-data-table');
		let observerRelatorioGigs = new MutationObserver(async function(mutationsDocumento) {
			mutationsDocumento.forEach(async function(mutation) {
				if (!mutation.addedNodes[0]) { return }
				if (!mutation.addedNodes[0].tagName) { return }
				if (mutation.addedNodes[0].tagName == 'PJE-GIGS-ABRIR-TAREFA') {
					let numeroProcesso = mutation.addedNodes[0].innerText.match(new RegExp('\\d{7}-\\d{2}\\.\\d{4}\\.\\d{1,2}\\.\\d{1,2}\\.\\d{4}','g')).join();
					let idProcesso = await obterIdProcessoViaApi(numeroProcesso);
					if (!idProcesso[0]) { return }
					let prioridadeProcesso = await obterPrioridadeProcessoViaApi(idProcesso[0].idProcesso);
					
					if (prioridadeProcesso.length > 0) {
						inserirIconePrioridadeProcessual(mutation.addedNodes[0].parentElement, prioridadeProcesso.toString());
					}
				}				
			});
		});
		observerRelatorioGigs.observe(target, { childList: true, subtree:true }); //inicia o MutationObserver
		
		function inserirIconePrioridadeProcessual(ancora, prioridade) {
			ancora.style.position = 'relative';
			let span = document.createElement('span');
			span.style = 'position: absolute;top: 35%;left: -20px;font-size: 20px;';
			span.title = prioridade;
			let i = document.createElement('i');
			i.className = 'fa fa-exclamation-triangle icone-tamanho-18';
			span.appendChild(i);
			ancora.appendChild(span);
		}
	}
	
	async function criar_elemento_monitor(nome_do_monitor) {
		return new Promise(async resolver => {
			if (!document.querySelector(nome_do_monitor)) { //se não tem ele cria
				let el = document.createElement(nome_do_monitor);
				el.style = "display:none;";
				document.body.appendChild(el);
				return resolver(false);
			} else {
				return resolver(true);
			}
		})
	}

	async function obterOJdoUsuario() {
		return new Promise(async resolve => {
			let oju = await esperarElemento('pje-cabecalho-perfil span[class*="papel-usuario"]');
			preferencias.oj_usuario = oju.innerText;
			console.log('preferencias.oj_usuario: ' + preferencias.oj_usuario)
			let var0 = browser.storage.local.set({'oj_usuario': preferencias.oj_usuario});
			Promise.all([var0]).then(values => { return resolve(preferencias.oj_usuario) });
		});
	}

	function aguardarCarregamentoTabela() {
		return new Promise(resolve => {
			let desapareceu = false;
			let apareceu = false;
			let check = setInterval(function() {
				let barraIdentificadora = document.querySelector('tr mat-progress-bar');
				if (barraIdentificadora) {
					apareceu = true;
				} else {
					desapareceu = true;
				}
				
				if (apareceu && desapareceu) {
					clearInterval(check);			
					return resolve(true);
				}
			}, 100);
		});		
	}
}

async function monitor_Janela_Gigs_Separada() {
	console.log("Extensão maisPJE (" + agora() + "): monitor_Janela_Gigs_Separada");
	let observerDocumento = new MutationObserver(function(mutationsDocumento) {
		mutationsDocumento.forEach(function(mutation) {
				if (!mutation.addedNodes[0]) { return }
				if (mutation.addedNodes[0].tagName == 'PJE-GIGS-CADASTRO-ATIVIDADES') {
					gigsInserirBorrachaResponsavel();
				}			
		});
	});		
	let configDocumento = { childList: true, characterData: true, subtree:true }
	observerDocumento.observe(document.body, configDocumento); //inicia o MutationObserver
}

async function monitor_janela_retificar_autuacao() {
	console.log("Extensão maisPJE (" + agora() + "): monitor_janela_retificar_autuacao");
	let observerJanelaRetificarAutuacao = new MutationObserver(async function(mutationsDocumento) {
		mutationsDocumento.forEach(async function(mutation) {
			if (!mutation.addedNodes[0]) { return }
			if (!mutation.addedNodes[0].tagName) { return }
			// console.log(mutation.addedNodes[0].tagName + " : " + mutation.addedNodes[0].className + " : " + mutation.addedNodes[0].innerText);
			
			if (mutation.addedNodes[0].tagName == 'PJE-DATA-TABLE') {
				let ancora = await esperarElemento('pje-endereco-grid');
				inserirbotao(ancora.parentElement);
			}
			
			if (!mutation.addedNodes[0].tagName.includes("SIMPLE-SNACK-BAR")) { return }			
			if (mutation.addedNodes[0].innerText.includes('Não foi possível acessar a Receita Federal')) { erro = true }
			if (mutation.addedNodes[0].innerText.includes('Este cpf não está cadastrado como um advogado ativo no sistema PJe')) { erro = true }
			if (mutation.addedNodes[0].innerText.includes('Informe um endereço ou marque a opção endereço desconhecido')) { erro = true	}
			if (mutation.addedNodes[0].innerText.includes('Erro de permissão ao acessar o recurso')) { erro = true }
			if (mutation.addedNodes[0].innerText.includes('Pessoa jurídica não encontrada ou não é uma pessoa jurídica de direito privado.')) { erro = true }
			if (mutation.addedNodes[0].innerText.includes('A pessoa informada já pertence a este polo')) { erro = true }
			if (mutation.addedNodes[0].innerText.includes('Tipo de argumento inválido')) { erro = true }			
			
		});
	});
	observerJanelaRetificarAutuacao.observe(document.body, { childList: true, subtree:true }); //inicia o MutationObserver
	
	async function inserirbotao(elemento) {
		if (!document.getElementById("maisPje_bt_buscarEndereco")) {
			let botao1 = document.createElement("button");
			botao1.id = "maisPje_bt_buscarEndereco";
			botao1.textContent = "Buscar Endereço";
			botao1.style = "cursor: pointer; position: relative; top: 20%; width: 100%; padding: 5px; margin: 5px; height: 35px; z-index: 1;";
			botao1.onclick = async function () {
				let pergunta = prompt("Digite alguma informação constante no endereço\nPor exemplo: CEP, parte do nome da rua, bairro, etc.\n O primeiro encontrado será selecionado:\n");
				let posicao = await obterListaDeEnderecosDaParte(pergunta);
				if (isNaN(posicao)) {
					criarCaixaDeAlerta("ALERTA","Endereço não encontrado.",3)	
					
				} else {
					let pagina = Math.floor(parseInt(posicao)/50) + 1;
					let paginador = elemento.parentElement.querySelector('mat-form-field mat-select');
					await clicarBotao(paginador);
					await clicarBotao('mat-option[role="option"]',pagina + '');
					let linhaEncontrada = await esperarElemento('TR', pergunta);
					// linhaEncontrada.querySelector('button[aria-label="Usar esse endereço no processo"]').click(); //não vou clicar pois pode ser o endereço errado
					linhaEncontrada.style = 'background-color: palegoldenrod !important; font-weight: bold;';
					linhaEncontrada.scrollIntoView({behavior: 'auto',block: 'center',inline: 'center'});					
				}
			};
			elemento.insertBefore(botao1, elemento.lastChild);
		}
	}
	
	async function obterListaDeEnderecosDaParte(pesquisa) {
		
		let url = await captureLastNetworkRequest();
		let resposta = await fetch(url);
		let dados = await resposta.json();
		
		for (const [pos, endereco] of dados.entries()) {
			let linha = JSON.stringify(endereco);
			// console.log("(" + pesquisa + ") " + pos + ". " + linha);
			if (removeAcento(linha.toLowerCase()).includes(removeAcento(pesquisa.toLowerCase()))) {
				// console.log("*************Achou: " + pos + ". " + linha);
				return pos;
				break;
			}
		}
		
		async function captureLastNetworkRequest(e) {
			let capture_network_request = [];
			let capture_resource = performance.getEntriesByType("resource");
			for (const [pos, capture] of capture_resource.entries()) {
				if (capture.name.includes('/pje-comum-api/api/pessoas/') && capture.name.includes('/enderecos')) {
					capture_network_request.push(capture.name);
				}
			}
			return capture_network_request[capture_network_request.length - 1];
		}
	}
}

async function monitor_janela_sisbajud() {
	console.log("Extensão maisPJE (" + agora() + "): monitor_janela_sisbajud");
	let targetDocumento = document.body;
	let observerDocumento = new MutationObserver(function(mutationsDocumento) {
		mutationsDocumento.forEach(function(mutation) {			
			if (!mutation.addedNodes[0]) { return }
			if (!mutation.addedNodes[0].tagName) { return }
			// console.log(mutation.addedNodes[0].tagName + " : " + mutation.addedNodes[0].className + " : " + mutation.addedNodes[0].innerText);
			
			//aplicar estilos nas linhas de tabelas onmouseenter onmouseleave
				if (document.querySelector('SISBAJUD-PESQUISA-TEIMOSINHA') && mutation.addedNodes[0].tagName == "TR" && mutation.target.tagName == "TBODY") {
					mutation.addedNodes[0].onmouseenter = function () {
						this.style.cursor = 'pointer';
						this.style.outline = '2px solid #3e3f3f';
						this.style.filter = 'drop-shadow(0 0 0.03rem #e9581c)';
					};
					mutation.addedNodes[0].onmouseleave = function () {
						this.style.cursor = 'revert';
						this.style.outline = 'unset';
						this.style.filter = 'revert';
					};
					mutation.addedNodes[0].onclick = function () {
						clicar_detalhes(this);
					};
				}
				
				if (document.querySelector('SISBAJUD-DETALHES-TEIMOSINHA') && mutation.addedNodes[0].tagName == "TR" && mutation.target.tagName == "TBODY") {
					mutation.addedNodes[0].onmouseenter = function () {
						this.style.cursor = 'pointer';
						this.style.outline = '2px solid #3e3f3f';
						this.style.filter = 'drop-shadow(0 0 0.03rem #e9581c)';
					};
					mutation.addedNodes[0].onmouseleave = function () {
						this.style.cursor = 'revert';
						this.style.outline = 'unset';
						this.style.filter = 'revert';
					};
					mutation.addedNodes[0].onclick = function () {
						clicar_detalhes(this);
					};
				}
				
				if (document.querySelector('SISBAJUD-PESQUISA-ORDEM-JUDICIAL') && mutation.addedNodes[0].tagName == "TR" && mutation.target.tagName == "TBODY") {
					mutation.addedNodes[0].onmouseenter = function () {
						this.style.cursor = 'pointer';
						this.style.outline = '2px solid #3e3f3f';
						this.style.filter = 'drop-shadow(0 0 0.03rem #e9581c)';
					};
					mutation.addedNodes[0].onmouseleave = function () {
						this.style.cursor = 'revert';
						this.style.outline = 'unset';
						this.style.filter = 'revert';
					};
					mutation.addedNodes[0].onclick = function () {
						clicar_detalhes(this);
					};
				}
			//-------------------
			
			if (mutation.addedNodes[0].tagName == "SISBAJUD-PESQUISA-TEIMOSINHA") {
				if (preferencias.AALote?.includes('sisbajud.marcarComoLidaEmLote')) { return true }//LEITURA DAS NÃO LIDAS EM LOTE
				let var1 = browser.storage.local.get('processo_memoria', function(result){			
					if (!result.processo_memoria.numero) {return}
					let check = setInterval(function() {
						if (document.querySelector('input[placeholder="Número do Processo"]')) {
							clearInterval(check);
							let el = document.querySelector('input[placeholder="Número do Processo"]');
							el.value = result.processo_memoria.numero;
							triggerEvent(el, 'input');
						}
					}, 200);
				});
			}
			
			if (mutation.addedNodes[0].tagName == "SISBAJUD-PESQUISA-ORDEM-JUDICIAL") {
				if (preferencias.AALote?.includes('sisbajud.marcarComoLidaEmLote')) { return true }//LEITURA DAS NÃO LIDAS EM LOTE
				consultaPJe(document.querySelectorAll('span[class*="sisbajud-label-valor"]'));
				let check = setInterval(function() {
					if (document.querySelector('button[title="Limpar"]')) {
						if (document.querySelector('div[class="uikit-actions"]')) {
							clearInterval(check);
							inserirBotoes();
						}
					}
				}, 250);
			}
			
			if (mutation.addedNodes[0].tagName == "SISBAJUD-DETALHES-TEIMOSINHA") {
				if (preferencias.AALote?.includes('sisbajud.marcarComoLidaEmLote')) { return true }//LEITURA DAS NÃO LIDAS EM LOTE
				consultaPJe(document.querySelectorAll('span[class*="sisbajud-label-valor"]'));
				
				//destaca as respostas com bloqueio
				tratarRespostasEmGrupo();
				
			}
			
			if (mutation.addedNodes[0].tagName == "SISBAJUD-INCLUSAO-DESDOBRAMENTO") {
				if (preferencias.AALote?.includes('sisbajud.marcarComoLidaEmLote')) { return true }//LEITURA DAS NÃO LIDAS EM LOTE	
				let check = setInterval(function() {
					if (document.querySelector('div[class="mat-expansion-panel-body"]')) {
						if (document.querySelector('div[class="mat-expansion-panel-body"]').children.length > 0) {
							clearInterval(check);
							aplicar_estilos();
						}
					}
				}, 100);
				
				//verificar se a resposta é de endereço... se sim, mandar exportar pdf.
				let tempominimo = 5000; //depois de cinco segundos encerra a verificação.. motivo: economia de recursos
				let check2= setInterval(function() {
					tempominimo = tempominimo - 100;
					let barraTitulo = document.querySelector('SISBAJUD-INCLUSAO-DESDOBRAMENTO MAT-CARD-TITLE');
					let ordemInfo = barraTitulo?.innerText.includes('Dados da Ordem Judicial de Requisição de Informações');
					let resposta = document.querySelector('SISBAJUD-INCLUSAO-DESDOBRAMENTO SISBAJUD-LIST-PESSOAS-PESQUISADAS-COM-RESPOSTA-E-ACOES');
					let btExportarResposta = document.querySelector('SISBAJUD-INCLUSAO-DESDOBRAMENTO DIV[class="uikit-actions"] MAT-ICON[class*="fa-file-pdf"]');
					
					// console.log(ordemInfo + ":" + resposta + ":" + btExportarResposta);
					if (ordemInfo && resposta && btExportarResposta) {
						clearInterval(check2);
						btExportarResposta.parentElement.parentElement.click();
					}
					
					if (tempominimo <= 0) { console.log('saiu');clearInterval(check2) }
				}, 100);
			}
			
			if (mutation.addedNodes[0].tagName == "SISBAJUD-DETALHAMENTO-ORDEM-JUDICIAL") {
				console.log('SISBAJUD-DETALHAMENTO-ORDEM-JUDICIAL')
				if (preferencias.AALote?.includes('sisbajud.marcarComoLidaEmLote')) { return true }//LEITURA DAS NÃO LIDAS EM LOTE
				
				let check1 = setInterval(function() {
					if (document.querySelector('span[class*="sisbajud-label-valor"]').innerText != "") { //esperar carregar os valores
						clearInterval(check1);
						consultaPJe(document.querySelectorAll('span[class*="sisbajud-label-valor"]'));
						if (!document.querySelector('sisbajud-list-reus-com-resposta')) {
							copiarNumeroOrdem(document.querySelectorAll('span[class*="sisbajud-label-valor"]'));
							let ancora = document.querySelector('sisbajud-detalhamento-ordem-judicial mat-card');
							let tituloDaOrdem = ancora.querySelector('mat-card-title');
							let situacaoOrdem = ancora.querySelector('mat-card-content span[class="sisbajud-label-valor"]');
							
							console.log('***************************************' + tituloDaOrdem.innerText);
							console.log('***************************************' + situacaoOrdem.innerText);
							
							if (!tituloDaOrdem.innerText.includes('Dados da Ordem Judicial de Requisição de Informações')) {
								if (preferencias.sisbajud.executarAAaoFinal != 'Nenhum') {
									if (situacaoOrdem.innerText.includes('Aguardando respostas das instituições financeiras')) { 
										// browser.runtime.sendMessage({tipo: 'storage_vinculo', valor: preferencias.sisbajud.executarAAaoFinal});
									}
									if (situacaoOrdem.innerText.includes('Ordem judicial ainda não disponibilizada para as instituições financeiras')) { 
										clicarBotao('button[title="Gerar Recibo"]');
										setTimeout(function() { 
											browser.runtime.sendMessage({tipo: 'storage_vinculo', valor: preferencias.sisbajud.executarAAaoFinal});
										}, 500);
									}
								}
							}
						}
					}
				}, 100);
				
				let check2 = setInterval(function() {
					if (document.querySelector('div[class="mat-expansion-panel-body"]')) {
						if (document.querySelector('div[class="mat-expansion-panel-body"]').children.length > 0) {
							clearInterval(check2);
							aplicar_estilos();
						}
					}
				}, 100);
			}
			
			if (mutation.addedNodes[0].tagName == "SISBAJUD-DIALOG-DADOS-DEPOSITO-JUDICIAL") {
				if (preferencias.AALote?.includes('sisbajud.marcarComoLidaEmLote')) { return true }//LEITURA DAS NÃO LIDAS EM LOTE
				let check = setInterval(function() {
					if (document.querySelector('mat-select[formcontrolname="tipoCredito"]')) { //esperar carregar o elemento
						clearInterval(check);
						dados_deposito();
					}
				}, 500);
			}
			
			if (mutation.addedNodes[0].tagName == "SISBAJUD-DIALOG-PROTOCOLIZACAO-MINUTA" || mutation.addedNodes[0].tagName == "SISBAJUD-DIALOG-PROTOCOLIZACAO-DESDOBRAMENTO") {
				if (document.getElementById('maisPje_menuKaizen_itemmenu_guardar_senha')?.getAttribute('chave')) {
					let s = document.getElementById('maisPje_menuKaizen_itemmenu_guardar_senha').getAttribute('chave');
					fundo(true);
					let check = setInterval(async function() {
						if (document.querySelector('input[placeholder="Senha"]')) { //esperar carregar o elemento

							clearInterval(check);
							let ancora = await esperarElemento('input[placeholder="Senha"]');
							ancora.focus();
							ancora.value = atob(s);
							triggerEvent(ancora, 'input');
							ancora.blur();
							await sleep(800);
							ancora = await esperarElemento('button','Confirmar');
							ancora.focus();
							ancora.click();
							ancora.blur();
							fundo(false);
						}
					}, 500);
				}
			}
			
			if (mutation.addedNodes[0].tagName == "SISBAJUD-SNACK-MESSENGER") {
				
				// console.log("SISBAJUD-SNACK-MESSENGER: " + mutation.addedNodes[0].innerText.includes('Desdobramento(s) protocolizada(s) com sucesso.'))
				if (mutation.addedNodes[0].innerText.includes('Desdobramento(s) protocolizada(s) com sucesso.')) {
					verificarTransferenciaDeValor();
				}
				
				if (mutation.addedNodes[0].innerText.includes('Desdobramento(s) incluído(s) com sucesso.')) {
					// botão gerar recibo
					let ancora = mutation.addedNodes[0].querySelector('button');
					ancora.focus();
					ancora.click();
					ancora.blur();
				}
			}

			
			if (document.querySelector('SISBAJUD-INCLUSAO-DESDOBRAMENTO')) {
				if (mutation.addedNodes[0].tagName == "MAT-FORM-FIELD" && mutation.addedNodes[0].innerText.includes('Vara/Juízo: *')) {
					//PREENCHER VARA
					if (document.querySelector('input[placeholder*="Vara"]')) {
						vara_juizo();
					}
				}
			}
			
			if (document.querySelector('SISBAJUD-INCLUSAO-DESDOBRAMENTO div[class="uikit-actions"] button')) {
				//atribui acionamento sem clique ao botão Salvar
				let btSalvar = querySelectorByText('div[class="uikit-actions"] button','Salvar');
				if (btSalvar) { acionarSemCliqueGenerico(btSalvar,'#005efc','#ff3d00') }

				let btProtocolar = querySelectorByText('div[class="uikit-actions"] button','Protocolar');
				if (btProtocolar) { acionarSemCliqueGenerico(btProtocolar,'#005efc','#ff3d00') }
			}

			
		});
	});		
	let configDocumento = { childList: true, subtree:true }
	observerDocumento.observe(targetDocumento, configDocumento); //inicia o MutationObserver
	
	//mutation do storage para disparar a inclusão de nova minuta de bloqueio
	browser.storage.onChanged.addListener(logStorageChange);				
	async function logStorageChange(changes, area) {
		let changedItems = Object.keys(changes);
		for (let item of changedItems) {
			// browser.runtime.sendMessage({tipo: 'storage_guardar', chave: 'tempAR', valor: 'F2'});
			console.log('*********************************' + item + ' : ' +changes[item].newValue)
			if (item == "tempAR") { //controla as AA e os vínculos (No caso aqui só nos interessa os vínculos
				if (changes[item].newValue == 'F2') {
					clicarBotao('span[id="maisPje_menuKaizen_itemmenu_preencher_campos"] a');
				}
			}
		}
	}

	//**********************FUNÇÕES COMPLEMENTARES*************************************
	//clicar no botão Gerar Recibo quando do tratamento de uma ordemd e bloqueio do sisbajud
	async function verificarTransferenciaDeValor() {
		let linhasDeTratamento = await esperarColecao('sisbajud-list-reus-com-resposta tbody tr');
		let imprimir = false;
		for (const [pos, linha] of linhasDeTratamento.entries()) {
			linha.scrollIntoView({behavior: 'smooth',block: 'start'});
			if (linha.querySelector('td[data-label="tipoOrdem"]').innerText.includes('Transferência de Valor')) {
				if (linha.querySelector('td[data-label="resultado"]').innerText.includes('Não enviada')) {
					imprimir = true;
				}
			}
		}
		
		if (imprimir) {
			await clicarBotao('button[title="Gerar Recibo"]');
		}
	}
	
	//clicar em Detalhar Série
	async function clicar_detalhes(elemento) {
		return new Promise(async resolve => {
			await clicarBotao(elemento.querySelector('td[class*="cdk-column-acoes"] button'));
			await clicarBotao('div[id*="cdk-overlay-"] button[role="menuitem"]','Detalhar')
			resolve(true);
		});
	}
	
	//APLICAR ESTILOS NAS RESPOSTAS
	async function aplicar_estilos() {
		let check = setInterval(async function() {
			if (document.querySelector('sisbajud-list-reus-com-resposta-e-acoes') || document.querySelector('sisbajud-list-reus-com-resposta') || document.querySelector('sisbajud-list-pessoas-pesquisadas-com-resposta-e-acoes') || document.querySelector('sisbajud-list-pessoas-pesquisadas-com-resposta')) {
				if (document.querySelector('mat-panel-description')) {
					clearInterval(check);
					console.log("   |___DESDOBRAR MINUTAS");
					
					//PREENCHER JUIZ
					if (document.querySelector('input[placeholder*="Juiz"]')) {
						await juiz();
					}					
					
					//ESTILO DA PAGINA
					if (document.querySelectorAll('mat-panel-description')) {
						let el1 = document.querySelectorAll('mat-panel-description');
						if (!el1) {
							return
						}
						let map = [].map.call(
							el1, 
							function(elemento) {												
								let total_bloqueado = elemento.innerText.substring(elemento.innerText.search(": R") + 5, elemento.innerText.length);
								total_bloqueado = total_bloqueado.replace(',','.');
								
								if (parseFloat(total_bloqueado) < 0.01) {
									elemento.parentElement.parentElement.parentElement.style = 'background-color: #ff270080; padding: 5px;';
								} else {
									elemento.parentElement.parentElement.parentElement.style = 'background-color: #32cd3280; padding: 5px;';
								}
							}
						);
					}								
					
					//ORDENS
					if (document.querySelectorAll('mat-select[role="listbox"]')) {
						let el2 = document.querySelectorAll('mat-select[role="listbox"]');
						if (!el2) {
							return
						}
						for (const [pos, item] of el2.entries()) {
							item.style = 'font-size: 1.2em;font-weight: bold;color: black;background-color: yellow;border: dashed 1px black;padding: 5px;';
							await escolher_Opcao(item);
						}
					}
					
					//ADICIONAR LINK PARA O PJE
					let ancora = await esperarColecao('span[class="sisbajud-label-valor"]', 5, 60000)				
					consultaPJe(ancora);
				}
			}
		}, 100); //esperar o carregamento da página
	}
	
	//preenche o campo JUIZ SOLICITANTE
	async function juiz() {
		console.log("      |___Juiz");
		return new Promise(async resolve => {
			if (preferencias.sisbajud.juiz) {
				let magistrado = preferencias.sisbajud.juiz;
				if (magistrado.toLowerCase().includes('modulo8')) {
					let processoNumero = document.querySelector('sisbajud-inclusao-desdobramento mat-card-content').innerText.match(new RegExp('\\d{7}-\\d{2}\\.\\d{4}\\.\\d{1,2}\\.\\d{1,2}\\.\\d{4}','g')).join();
					magistrado = await filtroMagistrado(processoNumero);
				}
				
				await escolherOpcao('input[placeholder*="Juiz"]',magistrado,0,false);
			}
			resolve(true);
		});
	}
	
	//preenche o campo VARA/JUÍZO
	async function vara_juizo() {
		console.log("      |___vara_juizo");
		return new Promise(async resolve => {
			if (preferencias.sisbajud.vara) {
				await escolherOpcao('input[placeholder*="Vara"]',preferencias.sisbajud.vara,0,false);
			}
			resolve(true);
		});
	}
	
	//preenche não-respostas e desbloqueio de valores mínimos
	async function escolher_Opcao(el) {
		return new Promise(resolve => {
			if (preferencias.sisbajud.naorespostas && preferencias.sisbajud.valor_desbloqueio) {						
				console.log("      |___NÃO-RESPOSTAS (" + preferencias.sisbajud.naorespostas + ") e DESBLOQUEIO DE VALORES MÍNIMOS (" + preferencias.sisbajud.valor_desbloqueio + ")");
				el.click();
				let check = setInterval(async function() {
					if (document.querySelectorAll('mat-option[role="option"]')) {
						clearInterval(check)
						let el2 = document.querySelectorAll('mat-option[role="option"]');
						if (!el2) {
							resolve(true);
						}
						let desbloquear = null;
						for (const [pos, item] of el2.entries()) {
							// console.log("pos: " + pos + " - item: " + item.innerText)
							
							if (item.innerText.includes('Desbloquear valor')) {
								desbloquear = item;
							}
							
							if (item.innerText === 'Transferir valor') {
								item.click();
								let ancora_valor = el.parentElement.parentElement.parentElement.parentElement.parentElement;
								let valor = ancora_valor.querySelector('input').value;
								valor = valor.replace(new RegExp('[^0-9\,]', 'g'), ""); //tira o R$
								valor = valor.replace(',', '.'); //substitui a virgula por ponto
								if (parseFloat(valor) < parseFloat(preferencias.sisbajud.valor_desbloqueio)) { //manda desbloquear
									desbloquear.click();
								}
								resolve(true);
								return;
							}
							
							if (item.innerText.includes(preferencias.sisbajud.naorespostas)) {
								item.click();
								resolve(true);
								return;
							}
						}
						
						//Se chegou até aqui é porquê são casos de tratamento na requisição de endereço. Lá não tem a opção "CANCELAR", apenas "REITERAR". Nesses casos, se o usuário escolheu cancelar a opção será deixada em branco.
						document.querySelector('mat-option').click(); //a primeira opção é sempre "em branco"
						resolve(true);
					}
				}, 250); //dar tempo de popular o checklist
			} else {
				resolve(true);
			}
		});
		
	}
	
	async function dados_deposito() {
		console.log("      |___TIPO DE CRÉDITO: Geral");
		fundo(true);
		let ancora = await esperarElemento('mat-select[formcontrolname="tipoCredito"]');
		await escolherOpcao(ancora.firstElementChild, 'Geral', 3, false);
		
		if (preferencias.sisbajud.banco_preferido) {
			console.log("      |___BANCO PREFERIDO: " + preferencias.sisbajud.banco_preferido);
			ancora = await esperarElemento('input[formcontrolname="instituicaoFinanceiraPorCategoria"]');
			await clicarBotao(ancora.parentElement.parentElement);
			await clicarBotao('mat-option[role="option"]', preferencias.sisbajud.banco_preferido);
		}
		
		if (preferencias.sisbajud.agencia_preferida) {
			console.log("      |___AGENCIA PREFERIDA: " + preferencias.sisbajud.agencia_preferida);
			ancora = await esperarElemento('input[formcontrolname="agencia"]');
			ancora.focus();
			ancora.value = preferencias.sisbajud.agencia_preferida;
			triggerEvent(ancora, 'input');
			ancora.blur();
		}
		
		if (preferencias.sisbajud.confirmar) {
			console.log("      |___CONFIRMAR: " + preferencias.sisbajud.confirmar);
			if (preferencias.sisbajud.confirmar.toLowerCase() == "sim") {
				ancora = await esperarElemento('button','Confirmar');
				ancora.focus();
				ancora.click();
				ancora.blur();
				
				//botão protocolar
				ancora = await esperarElemento('button','Protocolar');
				ancora.focus();
				ancora.click();
				ancora.blur();
			}
		}
		
		fundo(false);
	}
	
	//INSERIR BOTÕES DE CONSULTA
	async function inserirBotoes() {
		if (!document.getElementById('extensaoPje_sisbajud_atalho1')) {
			let el = document.querySelector('div[class="uikit-actions"]');
			//BOTÃO CONSULTAR BLOQUEIOS SEM DESDOBRAMENTO
			let atalho1 = document.createElement("button");
			atalho1.id = "extensaoPje_sisbajud_atalho1";
			atalho1.className = "mat-fab mat-button-base";
			atalho1.style = "background-color: white; margin-right: 3px; vertical-align: middle;";
			atalho1.innerText = "Bloqueios Pendentes";
			atalho1.onmouseenter = function () {atalho1.style.backgroundColor = '#32cd3280'};
			atalho1.onmouseleave = function () {atalho1.style.backgroundColor = 'white'};
			atalho1.onclick = function () {acaoBloqueiosPendentes()};
			el.appendChild(atalho1);
			
			//BOTÃO CONSULTAR NÃO RESPOSTAS
			let atalho2 = document.createElement("button");
			atalho2.id = "extensaoPje_sisbajud_atalho2";
			atalho2.className = "mat-fab mat-button-base";
			atalho2.style = "background-color: white; margin-right: 3px; vertical-align: middle;"
			atalho2.innerText = "Não Respostas";
			atalho2.onmouseenter = function () {atalho2.style.backgroundColor = '#ff270080'};
			atalho2.onmouseleave = function () {atalho2.style.backgroundColor = 'white'};
			atalho2.onclick = async function () {acaoNaoRespostas()};
			el.appendChild(atalho2);
			
			//BOTÃO LER ORDENS NÃO LIDAS
			let atalho3 = document.createElement("button");
			atalho3.id = "extensaoPje_sisbajud_atalho3";
			atalho3.className = "mat-fab mat-button-base";
			atalho3.style = "background-color: white; margin-right: 3px; vertical-align: middle;"
			atalho3.innerText = "Não Lidas";
			atalho3.onmouseenter = function () { this.style.backgroundColor = 'goldenrod' };
			atalho3.onmouseleave = function () { this.style.backgroundColor = 'white' };
			atalho3.onclick = async function () { acaoNaoLidas() };
			el.appendChild(atalho3);
			
			//*******************AÇÕES DOS BOTÕES*********************
			async function acaoBloqueiosPendentes() {
				await clicarBotao('button[title*="Limpar"]');
				await clicarBotao('div[role="tab"]', 'Busca por filtros de pesquisa');
				await vara_juizo();
				await clicarBotao('button', 'Exibir mais filtros');
				let ckbox = await esperarElemento('span[class*="mat-checkbox-label"]','Bloqueios efetivados sem qualquer desdobramento');
				await clicarBotao(ckbox.parentElement.firstElementChild.firstElementChild);
				await clicarBotao('button', 'Consultar');
			}
			
			async function acaoNaoRespostas() {
				await clicarBotao('button[title*="Limpar"]');
				await clicarBotao('div[role="tab"]', 'Busca por filtros de pesquisa');
				await vara_juizo();
				await clicarBotao('button', 'Exibir mais filtros');
				let ckbox1 = await esperarElemento('span[class*="mat-checkbox-label"]','Não-respostas pendentes de providência pelo juízo');
				await clicarBotao(ckbox1.parentElement.firstElementChild.firstElementChild);
				let ckbox2 = await esperarElemento('span[class*="mat-checkbox-label"]','Apenas ordens judiciais não-lidas');
				await clicarBotao(ckbox2.parentElement.firstElementChild.firstElementChild);
				await clicarBotao('button', 'Consultar');
			}

			async function acaoNaoLidas() {
				await clicarBotao('button[title*="Limpar"]');
				await clicarBotao('div[role="tab"]', 'Busca por filtros de pesquisa');
				await vara_juizo();
				await clicarBotao('button', 'Exibir mais filtros');
				let ckbox2 = await esperarElemento('span[class*="mat-checkbox-label"]','Apenas ordens judiciais não-lidas');
				await clicarBotao(ckbox2.parentElement.firstElementChild.firstElementChild);
				await clicarBotao('button', 'Consultar');

				//BOTÃO LER ORDENS NÃO LIDAS
				if (!document.getElementById('extensaoPje_sisbajud_lerEmLote')) {
					let ancora = document.querySelector('th[class*="cdk-column-acoes"]');
					let atalho4 = document.createElement("button");
					atalho4.id = "extensaoPje_sisbajud_lerEmLote";
					atalho4.className = "mat-fab mat-button-base";
					atalho4.style = "background-color: white; margin-left: 18px; vertical-align: middle; height: 4vh; width: 5vw; border-radius: 0px;"
					atalho4.innerText = "Ler em Lote";
					atalho4.onmouseenter = function () { this.style.backgroundColor = 'gold' };
					atalho4.onmouseleave = function () { this.style.backgroundColor = 'white' };
					atalho4.onclick = async function () { acaoLerEmLote() };
					ancora.appendChild(atalho4);
				}
			}
			
			async function acaoLerEmLote() {
				fundo(true);
				preferencias.AALote = 'sisbajud.marcarComoLidaEmLote';
				preferencias.erros = '';
				let i = 1;
				let fim;
				while(true) {
					if (preferencias.AALote == '') { break } //pressionar esc
					fim = await esperarElemento('sisbajud-snack-messenger','Não existe ordem judicial',1000);
					if (fim) { break }					
					let nProc = await esperarElemento('td[class*="mat-column-numeroProcesso"]');
					console.log(i + '.' + nProc.innerText);				
					preferencias.erros += nProc.innerText + "\n";					
					await clicarBotao('td[class*="cdk-column-acoes"] button');
					let ancora = await esperarElemento('div[class="cdk-overlay-pane"] mat-icon[class*="fa-search-plus"]');
					await clicarBotao(ancora.parentElement);
					let ancora2 = await esperarElemento('div[class*="breadcrumb"] mat-icon[class*="fa-chevron-left"]');
					await clicarBotao(ancora2.parentElement.parentElement);
					i++;
				}
				fundo(false);
				criarCaixaDeAlerta("ATENÇÃO",'Lista de processos Lidos: \n' + preferencias.erros);
				preferencias.erros = '';
				preferencias.AALote = '';				
				
			}
			//***********************************************************
		}
	}
	
	async function tratarRespostasEmGrupo() {
		let valor_a_bloquear = 0;
		let total_bloqueado = 0;
		
		await sleep(1000);
		
		//OBTER INFORMAÇÕES BÁSICAS
		let el1 = document.querySelectorAll('mat-card-content span[class="sisbajud-label-valor"]');
		if (!el1) {
			return
		}
		for (const [pos, item] of el1.entries()) {
			// console.log(item.innerText);
			if (item.innerText.includes('R$')) {
				// console.log(pos)
				if (valor_a_bloquear == 0) {
					let vb = item.innerText.substring(item.innerText.search("R$ ") + 3, item.innerText.length);
					vb = vb.replace('.','');
					valor_a_bloquear = parseFloat(vb.replace(',','.'));
				} else {
					let tb = item.innerText.substring(item.innerText.search("R$ ") + 3, item.innerText.length);
					tb = tb.replace('.','');
					total_bloqueado = parseFloat(tb.replace(',','.'));
				}
				
			}
		}
		//*****************************		
		
		//LER LINHA A LINHA
		let el2 = await esperarColecao('td[data-label="valorBloquear:"]');
		for (const [pos, item] of el2.entries()) {			
			if (el2[pos+1]) {
				let valorPosterior = el2[pos+1].innerText;
				let valorAtual = item.innerText;
				if (valorPosterior != valorAtual) {
					item.parentElement.style = 'background-color: #32cd3280 !important;';
				} else {
					item.parentElement.style = 'background-color: #ff270080 !important;';
				}
			}
			
			//último
			if (pos == (el2.length - 1)) {
				// console.log('Valor a bloquear: ' + valor_a_bloquear);
				// console.log('Total bloqueado: ' + total_bloqueado);
				//valor_a_bloquear - total_bloqueado tem que ser igual ao VALOR A BLOQUEAR da última linha
				let uvab = item.innerText.substring(item.innerText.search("R$ ") + 3, item.innerText.length);
				uvab = uvab.replace('.','');
				uvab = uvab.replace(',','.');
				// console.log(valor_a_bloquear - total_bloqueado)
				// console.log(parseFloat(uvab));
				let dif = (valor_a_bloquear - total_bloqueado) - parseFloat(uvab);
				// console.log('Diferença para a última tentativa de bloqueio: ' + dif.toFixed(2));
				if (dif.toFixed(2) != 0) {
					item.parentElement.style = 'background-color: #32cd3280 !important;';
				} else {
					item.parentElement.style = 'background-color: #ff270080 !important;';
				}
				
			}
		}
		
	}
	
	function copiarNumeroOrdem(el) {
		if (!el || el.length == 0) { return }
	
		let map = [].map.call(
			el, 
			function(elemento) {
				if (new RegExp('\\d{14}','g').test(elemento.innerText)) {
					elemento.classList.add('maisPje_destaque_elemento');
					// let ta = document.createElement("textarea");
					// ta.textContent = elemento.innerText;
					// document.body.appendChild(ta);
					// ta.select();
					// document.execCommand("copy");
					// document.body.removeChild(ta);
					navigator.clipboard.writeText(elemento.innerText);
					browser.runtime.sendMessage({tipo: 'criarAlerta', valor: 'Número da ordem SISBAJUD (' + elemento.innerText + ') copiada para a memória (CTRL + C)!!\n Use apenas CTRL + V para guardar essa informação..', icone: '5'});
				}
			}
		);
	}
	
	//**********************************************************************************
}

async function monitor_janela_renajud() {
	console.log("Extensão maisPJE (" + agora() + "): monitor_janela_renajud");
	let targetDocumento = document.body;
	let observerDocumento = new MutationObserver(async function(mutationsDocumento) {
		mutationsDocumento.forEach(async function(mutation) {
			// console.log("TARGET> " + mutation.target.tagName + " id=" + mutation.target.id + " class=" + mutation.target.className);
			// console.log("     |___" + mutation.addedNodes.length);
			if (!mutation.addedNodes[0]) { return }
			if (!mutation.addedNodes[0].tagName) { return }
			// console.log("ADDNODES> " + mutation.addedNodes[0].tagName + " id=" + mutation.addedNodes[0].id + " class=" + mutation.addedNodes[0].className);
			
			//********INCLUSÃO
			//PASSO1
			if (mutation.addedNodes[0].tagName == "FIELDSET") {
				fundo(true);
				console.log("  |___preencherRestricoes > INICIO");
				await acao1();
				await escolherOpcaoRenajud('form-incluir-restricao:campo-municipio', preferencias.renajud.comarca);
				await escolherOpcaoRenajud('form-incluir-restricao:campo-orgao', preferencias.renajud.orgao);
				await escolherOpcaoRenajud('form-incluir-restricao:campo-magistrado', preferencias.renajud.juiz);
				await acao2();
				console.log("  |___preencherRestricoes > FIM");
			}
			
			//********EXCLUSÃO
			//PASSO1
			if (mutation.addedNodes.length > 1) {
				let mutacao = Array.from(mutation.addedNodes).find(function(el){if(el.id){return el.id.includes('panel-usuario-botoes')}});
				if (mutacao) {
					fundo(true);
					console.log("  |___excluirRestricoes > INICIO");
					await escolherVeiculos();
					await escolherOpcaoRenajud('campo-select-municipio', preferencias.renajud.comarca);
					await escolherOpcaoRenajud('campo-select-orgao', preferencias.renajud.orgao);
					await escolherOpcaoRenajud('campo-select-magistrado', preferencias.renajud.juiz);
					await acao3();
					console.log("  |___excluirRestricoes > FIM");
				}
			}
			
			//renajud novo
			if (mutation.addedNodes[0].tagName == "APP-VEICULO-RESTRICAO-EXCLUSAO") {
				await retirarRestricao();
				observer.disconnect();
			}
		});
	});		
	let configDocumento = { childList: true, subtree:true }
	observerDocumento.observe(targetDocumento, configDocumento); //inicia o MutationObserver
	
	//**********************FUNÇÕES COMPLEMENTARES*************************************
	async function acao1() {
		return new Promise(async resolve => {
			if (preferencias.renajud.tipo_restricao) {
				console.log("      |___TIPO: " + preferencias.renajud.tipo_restricao);
				let el = await esperarColecao('div[class*="ui-radiobutton-box"]', 3);
				switch(preferencias.renajud.tipo_restricao) {
					case "Transferência":
						await clicarBotao(el[0]);
						return resolve(true);
					case "Licenciamento":
						await clicarBotao(el[1]);
						return resolve(true);
					case "Circulação":
						await clicarBotao(el[2]);
						return resolve(true);
				}
			}
		});
	}
	
	async function escolherOpcaoRenajud(ancora, valor) {
		return new Promise(async resolve => {
			console.log("      |___Escolher Opção Renajud: " + valor);
			let el = await esperarElemento('label[id="' + ancora + '_label"]');
			await clicarBotao(el);
			let encontrou = await esperarColecao('div[id="' + ancora + '_panel"] li[class*="ui-selectonemenu-item"]').then(opcoes=>{
				let encontrou = false;
				for (const [pos, opcao] of opcoes.entries()) {
					// console.log(removeAcento(opcao.innerText.toLowerCase()) + " includes " + removeAcento(valor.toLowerCase()) + " == " + removeAcento(opcao.innerText.toLowerCase()).includes(removeAcento(valor.toLowerCase())));
					if (removeAcento(opcao.innerText.toLowerCase()).includes(removeAcento(valor.toLowerCase()))) {
						// console.log("                       |--->OPTION " + valor);
						opcao.click();
						encontrou = true;
					};
				}
				// console.log("encontrou? " + encontrou);
				if (encontrou) {
					return true;
				} else {
					return escolherOpcaoRenajud(ancora, valor);
				}
			});
			resolve(encontrou);
		});
	}
	
	async function acao2() {
		return new Promise(async resolve => {
			// await sleep(1000);
			let numero = await preencherNumero();
			if (numero) {
				await clicarBotao('BUTTON', 'Inserir');
				observerDocumento.disconnect();
				fundo(false);
				console.log('fim acao2');
				resolve(true);
			} else {
				observerDocumento.disconnect();
				fundo(false);
				console.log('fim acao2');
				resolve(true);
			}
		});
	}
	
	async function acao3() {
		return new Promise(async resolve => {
			// await sleep(1000);
			await clicarBotao('BUTTON', 'Retirar');
			observerDocumento.disconnect();
			fundo(false);
			console.log('fim acao3');
			resolve(true);
		});
	}
	
	async function preencherNumero() {
		return new Promise(async resolve => {
			let var1 = browser.storage.local.get('processo_memoria', async function(result){			
				if (!result.processo_memoria.numero) {return resolve(false)}
				console.log("      |___PROCESSO: " + result.processo_memoria.numero);
				let el = await esperarElemento('input[id="form-incluir-restricao:campo-numero-processo"]');
				el.focus();
				Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set.call(el, result.processo_memoria.numero);
				triggerEvent(el, 'input');
				el.blur();
				resolve(true);
			});
		});
	}
	
	async function escolherVeiculos() {
		return new Promise(async resolve => {
			console.log("      |___ESCOLHE VEICULOS");
			await esperarColecao('div[class*="ui-chkbox-all"]', 1).then(chkbox=>{
				for (const [pos, item] of chkbox.entries()) {
					item.children[1].click();
				}
				resolve(true)
			}).catch(function (err) {
				escolherVeiculos();
			});
		});
	}
	
	function esperarElemento(seletor) {
		return new Promise(resolve => {
			let elemento = (seletor instanceof HTMLElement) ? seletor : document.querySelector(seletor);
			let disabled = (elemento.disabled === undefined) ? false : elemento.disabled;
			if (elemento && !disabled) {
				resolve(elemento);
				return;
			} else {
				let observer = new MutationObserver(mutations => {
					// console.log('esperando elemento');
					let elemento_esperado = (seletor instanceof HTMLElement) ? seletor : document.querySelector(seletor);
					let disabled = (elemento_esperado.disabled === undefined) ? false : elemento_esperado.disabled;
					if (elemento_esperado && !disabled) {
						observer.disconnect();
						resolve(elemento_esperado);
						return;
					}
				});
				
				observer.observe(document.body, { childList: true, subtree: true });
				setTimeout(function() { 
					observer.disconnect(); 
					resolve(null); 
				}, 5000);  //se não tiver qualquer mudança em 5 segundos, significa que o elemento não aparecerá
			}
		});
	}
	
	function esperarColecao(seletor) {
		return new Promise(resolve => {
			let elemento = (seletor instanceof NodeList) ? seletor : document.querySelectorAll(seletor);
			if (elemento) {
				resolve(elemento);
				return;
			} else {
				let observer = new MutationObserver(mutations => {
					// console.log('esperando coleção');
					let elemento_esperado = (seletor instanceof NodeList) ? seletor : document.querySelectorAll(seletor);
					if (elemento_esperado) {
						observer.disconnect();
						resolve(elemento_esperado);
						return;
					}
				});
				
				observer.observe(document.body, { childList: true, subtree: true });
				setTimeout(function() { 
					observer.disconnect(); 
					resolve(null); 
				}, 5000);  //se não tiver qualquer mudança em 5 segundos, significa que o elemento não aparecerá
			}
		});
	}
	
	function sleep(ms) {
		return new Promise(resolve => setTimeout(resolve, ms));
	}
	
	async function retirarRestricao() {
		return new Promise(async resolve => {
			let var1 = browser.storage.local.get('processo_memoria', async function(result){
				if (!result.processo_memoria.numero) {return resolve(false)}
				console.log("      |___PROCESSO: " + result.processo_memoria.numero);
				fundo(true);
				console.log("  |___retirarRestricoes > INICIO");
				console.log(preferencias.renajud.tipo_restricao);
				console.log(preferencias.renajud.orgao);
				console.log(preferencias.renajud.juiz);
				
				let ramoJustica = await esperarElemento('select[id="ramoJustica"]');
				await escolherOpcao(ramoJustica, 'JUSTICA DO TRABALHO',9);
				let selecao1 = await esperarElemento('OPTION','JUSTICA DO TRABALHO');
				selecao1.selected = true;
				triggerEvent(ramoJustica,'change');
				
				let tribunal = await esperarElemento('select[id="tribunal"]');
				await escolherOpcao(tribunal, preferencias.renajud.tribunal,26);
				let selecao2 = await esperarElemento('OPTION',preferencias.renajud.tribunal);
				selecao2.selected = true;
				triggerEvent(tribunal,'change');
				
				let orgao = await esperarElemento('select[id="orgao"]');
				await escolherOpcao(orgao, preferencias.renajud.orgao,26);
				let selecao3 = await esperarElemento('OPTION',preferencias.renajud.orgao);
				selecao3.selected = true;
				triggerEvent(orgao,'change');
				
				let magistrado = await esperarElemento('select[id="magistrado"]');
				await escolherOpcao(magistrado, preferencias.renajud.juiz,26);
				let selecao4 = await esperarElemento('OPTION',preferencias.renajud.juiz);
				selecao4.selected = true;
				triggerEvent(magistrado,'change');
				
				await preencherInput('input[id="numeroProcesso"]', result.processo_memoria.numero);
				await clicarBotao('button', 'Retirar');
				
				let btConfirmar = await esperarElemento('button', 'Confirmar');
				btConfirmar.addEventListener('click', async function(event) {
					await sleep(1000);
					await clicarBotao(document.querySelector('button[id="maisPje_assistenteImpressao_bt_copiar"]'));
				});
				fundo(false);
				resolve(true);
			});
		});				
	}
}

async function monitor_janela_renajudNovo() {
	console.log("Extensão maisPJE (" + agora() + "): monitor_janela_renajudNovo");
	let targetDocumento = document.body;
	let observerDocumento = new MutationObserver(async function(mutationsDocumento) {
		mutationsDocumento.forEach(async function(mutation) {
			if (!mutation.addedNodes[0]) { return }
			if (!mutation.addedNodes[0].tagName) { return }
			
			// console.log('*************' + mutation.addedNodes[0].tagName)
			if (mutation.addedNodes[0].tagName == "APP-VEICULO-RESTRICAO-PESQUISA") {
				await pesquisarRestricao();
			}
			
			if (mutation.addedNodes[0].tagName == "APP-VEICULO-RESTRICAO-EXCLUSAO") {
				console.log('EXCLUSÃO DE RESTRIÇÃO');
				await retirarRestricao();
				observer.disconnect();
			}
		});
	});		
	let configDocumento = { childList: true, subtree:true }
	observerDocumento.observe(targetDocumento, configDocumento); //inicia o MutationObserver
	
	//**********************FUNÇÕES COMPLEMENTARES*************************************
	async function pesquisarRestricao() {
		return new Promise(async resolve => {
			let var1 = browser.storage.local.get('processo_memoria', async function(result){
				if (!result.processo_memoria.numero) {return resolve(false)}
				fundo(true);
				console.log(result.processo_memoria.numero)
				await preencherInput('input[id="numeroProcesso"]', result.processo_memoria.numero);
				await clicarBotao('button', 'Pesquisar');
				fundo(false);
				resolve(true);
			});
		});
	}
	
	async function retirarRestricao() {
		return new Promise(async resolve => {
			let var1 = browser.storage.local.get('processo_memoria', async function(result){
				if (!result.processo_memoria.numero) {return resolve(false)}
				console.log("      |___PROCESSO: " + result.processo_memoria.numero);
				fundo(true);
				console.log("  |___retirarRestricoes > INICIO");
				console.log(preferencias.renajud.tipo_restricao);
				console.log(preferencias.renajud.orgao);
				console.log(preferencias.renajud.juiz);
				
				let ramoJustica = await esperarElemento('select[id="ramoJustica"]');
				await escolherOpcao(ramoJustica, 'JUSTICA DO TRABALHO',9);
				let selecao1 = await esperarElemento('OPTION','JUSTICA DO TRABALHO');
				selecao1.selected = true;
				triggerEvent(ramoJustica,'change');
				
				let tribunal = await esperarElemento('select[id="tribunal"]');
				await escolherOpcao(tribunal, preferencias.renajud.tribunal,26);
				let selecao2 = await esperarElemento('OPTION',preferencias.renajud.tribunal);
				selecao2.selected = true;
				triggerEvent(tribunal,'change');
				
				let orgao = await esperarElemento('select[id="orgao"]');
				await escolherOpcao(orgao, preferencias.renajud.orgao,26);
				let selecao3 = await esperarElemento('OPTION',preferencias.renajud.orgao);
				selecao3.selected = true;
				triggerEvent(orgao,'change');
				
				console.log(preferencias.renajud.juiz + " : " + preferencias.renajud.juiz2)
				let magistrado = await esperarElemento('select[id="magistrado"]');
				await escolherOpcao(magistrado, preferencias.renajud.juiz2,1);
				let selecao4 = await esperarElemento('OPTION',preferencias.renajud.juiz2);
				selecao4.selected = true;
				triggerEvent(magistrado,'change');
				
				console.log(result.processo_memoria.numero)
				await preencherInput('input[id="numeroProcesso"]', result.processo_memoria.numero);
				await clicarBotao('button', 'Retirar');
				
				let btConfirmar = await esperarElemento('div[class="modal-footer"] button', 'Sim'); //MODAL-CONTAINER button
				btConfirmar.addEventListener('click', async function(event) {
					await sleep(1000);
					await clicarBotao(document.querySelector('button[id="maisPje_assistenteImpressao_bt_copiar"]'));
				});
				fundo(false);
				resolve(true);
			});
		});				
	}
}

async function monitor_janela_crcjud() {
	console.log("Extensão maisPJE (" + agora() + "): monitor_janela_crcjud");
	let targetDocumento = document.body;
	let observerDocumento = new MutationObserver(async function(mutationsDocumento) {
		mutationsDocumento.forEach(async function(mutation) {
			// console.log("TARGET> " + mutation.target.tagName + " id=" + mutation.target.id + " class=" + mutation.target.className);
			// console.log("     |___" + mutation.addedNodes.length);
			if (!mutation.addedNodes[0]) { return }
			
			if (mutation.addedNodes.length > 0) {
				for (const [pos, node] of mutation.addedNodes.entries()) {
					// console.log("NODES[" + pos + "]: " + node.tagName + " id=" + node.id + " class=" + node.className);
					if (node.tagName == "DIV" && node.className == "redondo container") { //EH O DIV CENTRAL DA TELA
						let var1 = browser.storage.local.get('processo_memoria', async function(result){
							preferencias.processo_memoria = result.processo_memoria;
							if (!result.processo_memoria.numero) {return}
							let titulo = node.querySelector('H1').innerText;
							
							if (titulo.includes('Busca de Registros')) {
								await preencherInput('input[name="numero_processo"]', result.processo_memoria.numero); //preenche o numero do processo
								await escolherSelect('select[name="vara_juiz_id"]', 'VARA DO TRABALHO', 3); //escolhe a vara - a primeira que tiver
								let lista_de_executados = await criarCaixaDeSelecaoComReclamados(false);
								if (!lista_de_executados) { return }
								await preencherInput('input[name="nome_registrado"]', lista_de_executados[0].nome); //preenche o numero do processo
								await preencherInput('input[name="cpf_registrado"]', lista_de_executados[0].cpfcnpj); //preenche o numero do processo
								await clicarBotao('input[value="C,TC"]');								
								incluirBT();

							} else if (titulo.includes('Pedido de 2')) {
								await preencherInput('input[name="numero_processo"]', result.processo_memoria.numero); //preenche o numero do processo
								await escolherSelect('select[name="vara_juiz_id"]', 'VARA DO TRABALHO', 3); //escolhe a vara - a primeira que tiver
								let lista_de_executados = await criarCaixaDeSelecaoComReclamados(false);
								if (!lista_de_executados) { return }
								await preencherInput('input[name="nome_registrado"]', lista_de_executados[0].nome); //preenche o numero do processo
							} else if (titulo.includes('Pesquisa de Certidões')) {
								await preencherInput('input[name="num_processo"]', result.processo_memoria.numero); //preenche o numero do processo
							}
						});
					}
				}
			}
		});
	});		
	let configDocumento = { childList: true, subtree:true }
	observerDocumento.observe(targetDocumento, configDocumento); //inicia o MutationObserver
	
	//FUNÇÕES COMPLEMENTARES
	async function escolherSelect(ancora, valor) {
		return new Promise(async resolve => {
			console.log("      |___escolheropção: " + valor);
			let sel = await esperarElemento(ancora);
			let opcao = Array.from(sel.querySelectorAll('option')).find(el => el.textContent.toUpperCase().includes(valor));
			sel.value = opcao.value;	
			triggerEvent(sel, 'change');
			resolve(true);
		});
	}
	
	async function incluirBT() {
		if (!document.getElementById('maisPje_bt_imprimir')) {
			let ancora1 = document.getElementById('btn_pesquisar').parentElement;
			let bt1 = document.createElement("input");
			bt1.id = "maisPje_bt_imprimir";
			bt1.className = "botao";
			bt1.style = 'style="margin-right: 10px;margin-left: 5px;"';
			bt1.type = "submit";
			bt1.value = "Imprimir";
			bt1.onclick = function () {
				document.querySelector('input[name="nome_pai"]').parentElement.parentElement.style.display = "none";
				document.querySelector('input[name="nome_mae"]').parentElement.parentElement.style.display = "none";
				document.querySelector('select[name="uf"]').parentElement.parentElement.style.display = "none";
				document.querySelector('select[name="cidade_id"]').parentElement.parentElement.style.display = "none";
				document.querySelector('select[name="cartorio_id"]').parentElement.parentElement.style.display = "none";
				document.querySelector('input[name="data_ocorrido_ini"]').parentElement.parentElement.style.display = "none";
				document.querySelector('input[name="data_registro_ini"]').parentElement.parentElement.style.display = "none";
				document.querySelector('input[name="num_livro"]').parentElement.parentElement.style.display = "none";
				document.querySelector('input[name="num_folha"]').parentElement.parentElement.style.display = "none";
				document.querySelector('input[name="num_registro"]').parentElement.parentElement.style.display = "none";
				document.querySelector('h4').style.display = "none";
				
				// inserir o css de impressão
				let style = document.createElement("style");
				style.textContent = '@media print { body * { visibility: hidden; } #principal, #principal * { visibility: visible; } }';
				document.body.appendChild(style);
				
				window.print();
			};
			ancora1.appendChild(bt1);
		}
		
		if (!document.getElementById('maisPje_bt_incluir_reu')) {
			let ancora2 = document.getElementById('btn_pesquisar').parentElement;
			let bt2 = document.createElement("input");
			bt2.id = "maisPje_bt_incluir_reu";
			bt2.className = "botao";
			bt2.type = "submit";
			bt2.value = "Incluir Executado";
			bt2.onclick = async function () {
				let lista_de_executados = await criarCaixaDeSelecaoComReclamados(false);
				if (!lista_de_executados) { return }
				await preencherInput('input[name="nome_registrado"]', lista_de_executados[0].nome); //preenche o numero do processo
				await preencherInput('input[name="cpf_registrado"]', lista_de_executados[0].cpfcnpj); //preenche o numero do processo
			};
			ancora2.appendChild(bt2);
		}
		
	}
}

async function monitor_janela_expedientes() {
	console.log("Extensão maisPJE (" + agora() + "): monitor_janela_expedientes");
	let contadorFecharAutomatico = 0;
	let targetDocumento = document.body;
	let observerDocumento = new MutationObserver(async function(mutationsDocumento) {
		mutationsDocumento.forEach(async function(mutation) {
			if (!mutation.removedNodes[0] && !mutation.addedNodes[0]) { return }
			
			if (mutation.addedNodes[0]) {
				if (!mutation.addedNodes[0].tagName) { return }
				// console.log("ADDNODES: " + mutation.addedNodes[0].tagName + " : " + mutation.addedNodes[0].className + " : " + mutation.addedNodes[0].innerText);
				
				if (!mutation.addedNodes[0].tagName.includes("MAT-FORM-FIELD") && !mutation.addedNodes[0].tagName.includes("UL") && !mutation.addedNodes[0].tagName.includes("PJE-DATA-TABLE")) { return }
				
				if (mutation.addedNodes[0].className.includes('pec-signatarios-ato-individual')) {
					let campo = mutation.addedNodes[0].querySelector('mat-select[placeholder*="Pessoas que assinam"]');
					if (!campo.getAttribute('maisPJe')) { // verifica se campo tem a tag 'maisPje' que permite ao usuario mudar manualmente o juiz
						// DESCRIÇÃO: seleciona o magistrado se houver configuração no módulo 8
						if (preferencias.modulo8) {
							if (preferencias.modulo8.length > 0) {
								let el = await esperarElemento('mat-radio-button[id*="PapelAssinaturaMAGISTRADO"]', null, 5000);
								if (el) {
									if (el.className.includes('mat-radio-checked')) {
										let processoNumero = document.querySelector('span[class="texto-numero-processo"]').innerText.match(new RegExp('\\d{7}-\\d{2}\\.\\d{4}\\.\\d{1,2}\\.\\d{1,2}\\.\\d{4}','g')).join();
										let magistrado = await filtroMagistrado(processoNumero);
										await escolherOpcao('mat-select[placeholder="Pessoas que assinam"]', magistrado.toUpperCase(), 1);
										campo.setAttribute('maisPJe', true);
										fundo(false);
									}
								}
							}
						}
					}
				}
				
				if (mutation.addedNodes[0].tagName.includes("UL")) {				
					if (mutation.addedNodes[0].className.includes("ck-list")) {
						if (preferencias.extrasEditorInverterOrdem) {
							mutation.addedNodes[0].style = "display: flex;flex-direction: column;";
						}
						let lista = mutation.addedNodes[0].querySelectorAll('li');
						for (let [pos, linha] of lista.entries()) {
							let span = linha.querySelector('span');
							if (span.innerText.length <= 0) {
								if (preferencias.extrasEditorOcultarAutotexto) {
									linha.remove();
								} else {
									linha.style = 'order: ' + (10000 + lista.length - pos) + ";";
								}
							} else {
								linha.style = 'order: ' + (lista.length - pos) + ";";
							}							
						}
					}
				}
				
				if (mutation.addedNodes[0].tagName == 'PJE-DATA-TABLE') {
					if (mutation.addedNodes[0].getAttribute('aria-label').includes("Endereços do destinatário no sistema")) {
						inserirbotao(mutation.addedNodes[0]);
					}
				}
				
			}
			
			//fecha a janela automaticamente ao assinar o documento
			if (mutation.removedNodes[0] && preferencias.extrasFecharJanelaExpediente) {
				if (!mutation.removedNodes[0].tagName) { return }
				// console.log("REMOVEDNODES: " + mutation.removedNodes[0].tagName + " : " + mutation.removedNodes[0].className + " : " + mutation.removedNodes[0].innerText);
				
				if (document.location.href.includes("/tarefa/")) { //intimação pela TAREFA
					
					if (!mutation.removedNodes[0].tagName.includes("PJE-DIALOGO-STATUS-PROGRESSO") && !mutation.removedNodes[0].tagName.includes("PJE-PEC")) { return }
					
					if (contadorFecharAutomatico == 0 && mutation.removedNodes[0].tagName.includes("PJE-DIALOGO-STATUS-PROGRESSO")) {
						if (mutation.removedNodes[0].innerText.includes("Solicitando assinaturas")) {
							console.log('contadorFecharAutomatico: ' + contadorFecharAutomatico);
							contadorFecharAutomatico = 1;
						}
					}
					
					if (contadorFecharAutomatico == 1 && mutation.removedNodes[0].tagName.includes("PJE-PEC")) {
						console.log('contadorFecharAutomatico: ' + contadorFecharAutomatico);
						contadorFecharAutomatico = 2;
					}
					
					if (contadorFecharAutomatico == 2 && mutation.removedNodes[0].tagName.includes("PJE-DIALOGO-STATUS-PROGRESSO")) {
						if (mutation.removedNodes[0].innerText.includes("Iniciando a tarefa")) {
							console.log('contadorFecharAutomatico: ' + contadorFecharAutomatico);
							console.log('=====================entrou agora')
							await sleep(1000);
							window.close();
						}
					}
					
				} else { //intimação pela janela DETALHES DO PROCESSO
					if (mutation.removedNodes[0].tagName.includes("DIV") && mutation.removedNodes[0].innerText.includes('Expediente(s) assinado(s) com sucesso.')) {
						await sleep(1000);
						window.close();
					}
				}
			}
			
			
		});
	});		
	let configDocumento = { childList: true, subtree:true }
	observerDocumento.observe(targetDocumento, configDocumento); //inicia o MutationObserver
	
	async function inserirbotao(elemento) {
		if (!document.getElementById("maisPje_bt_buscarEndereco")) {
			let botao1 = document.createElement("button");
			botao1.id = "maisPje_bt_buscarEndereco";
			botao1.textContent = "Buscar Endereço";
			botao1.style = "cursor: pointer; position: relative; top: 20%; width: 100%; padding: 5px; margin: 5px; height: 35px; z-index: 1;";
			botao1.onclick = async function () {
				let pergunta = prompt("Digite alguma informação constante no endereço\nPor exemplo: CEP, parte do nome da rua, bairro, etc.\n O primeiro encontrado será selecionado:\n");
				let posicao = await obterListaDeEnderecosDaParte(pergunta);
				if (isNaN(posicao)) {
					criarCaixaDeAlerta("ALERTA","Endereço não encontrado.");
				} else {
					let pagina = Math.floor(parseInt(posicao)/5) + 1;
					let paginador = elemento.querySelector('mat-form-field mat-select');
					await clicarBotao(paginador);
					await clicarBotao('mat-option[role="option"]',pagina + '');
					let linhaEncontrada = await esperarElemento('TR', pergunta);
					// linhaEncontrada.querySelector('button[aria-label="Usar esse endereço no processo"]').click(); //não vou clicar pois pode ser o endereço errado
					linhaEncontrada.style = 'background-color: palegoldenrod !important; font-weight: bold;';
					linhaEncontrada.scrollIntoView({behavior: 'auto',block: 'center',inline: 'center'});
					await clicarBotao('button[aria-label="Selecionar endereço"]');
					await clicarBotao('pje-pec-dialogo-endereco a[mattooltip="Fechar"]');
				}
			};
			elemento.insertBefore(botao1, elemento.lastChild);
		}
	}
	
	async function obterListaDeEnderecosDaParte(pesquisa) {
		
		let url = await captureLastNetworkRequest();
		url = url.replace('tamanhoPagina=5','tamanhoPagina=10000');
		let resposta = await fetch(url);
		let dados = await resposta.json();
		
		for (const [pos, endereco] of dados.resultado.entries()) {
			let linha = JSON.stringify(endereco);
			// console.log("(" + pesquisa + ") " + pos + ". " + linha);
			if (removeAcento(linha.toLowerCase()).includes(removeAcento(pesquisa.toLowerCase()))) {
				// console.log("*************Achou: " + pos + ". " + linha);
				return pos;
				break;
			}
		}
		
		async function captureLastNetworkRequest(e) {
			let capture_network_request = [];
			let capture_resource = performance.getEntriesByType("resource");
			for (const [pos, capture] of capture_resource.entries()) {
				if (capture.name.includes('/pje-comum-api/api/pessoas/') && capture.name.includes('/enderecos')) {
					capture_network_request.push(capture.name);
				}
			}
			return capture_network_request[capture_network_request.length - 1];
		}
	}
}

async function monitor_janela_anexar() {
	console.log("Extensão maisPJE (" + agora() + "): monitor_janela_anexar");
	let targetDocumento = document.body;
	let observerDocumento = new MutationObserver(async function(mutationsDocumento) {
		mutationsDocumento.forEach(async function(mutation) {
			if (!mutation.addedNodes[0]) { return }
			if (!mutation.addedNodes[0].tagName) { return }			
			// console.log("ADDNODES: " + mutation.addedNodes[0].tagName + " : " + mutation.addedNodes[0].className + " : " + mutation.addedNodes[0].innerText);
			
			if (mutation.addedNodes[0].tagName != "PJE-ANEXAR-PDFS" && mutation.addedNodes[0].tagName != "PJE-RESPOSTA-ASSINATURA" && mutation.addedNodes[0].tagName != "UL" && mutation.addedNodes[0].tagName != "SIMPLE-SNACK-BAR") { return }
			
			
			if (mutation.addedNodes[0].tagName == "PJE-ANEXAR-PDFS") {
				addBotaoTipoEmLote();
			}
			
			if (mutation.addedNodes[0].tagName == "SIMPLE-SNACK-BAR") {				
				if (mutation.addedNodes[0].innerText.includes("arquivo") && mutation.addedNodes[0].innerText.includes("enviado")) {
					mutation.addedNodes[0].querySelector('button').click(); //fecha o aviso
					await clicarBotao('button[id*="_tipoEmLote"]');
				}

				if (mutation.addedNodes[0].innerText.includes("Minuta") && mutation.addedNodes[0].innerText.includes("salva")) {
					mutation.addedNodes[0].querySelector('button').click(); //fecha o aviso
				}
			}
			
			if (mutation.addedNodes[0].tagName == "PJE-RESPOSTA-ASSINATURA") {
				if (mutation.addedNodes[0].innerText.includes("Fechar")) {
					document.querySelector('button[aria-label="Fechar"]').click(); //fecha a janela
				}
			}
			
			if (mutation.addedNodes[0].tagName == "UL") {				
				if (mutation.addedNodes[0].className.includes("ck-list")) {
					if (preferencias.extrasEditorInverterOrdem) {
						mutation.addedNodes[0].style = "display: flex;flex-direction: column;";
					}
					let lista = mutation.addedNodes[0].querySelectorAll('li');
					for (let [pos, linha] of lista.entries()) {
						let span = linha.querySelector('span');
						if (span.innerText.length <= 0) {
							if (preferencias.extrasEditorOcultarAutotexto) {
								linha.remove();
							} else {
								linha.style = 'order: ' + (10000 + lista.length - pos) + ";";
							}
						} else {
							linha.style = 'order: ' + (lista.length - pos) + ";";
						}							
					}
				}
			}
			
		});
	});		
	let configDocumento = { childList: true, subtree:true }
	observerDocumento.observe(targetDocumento, configDocumento); //inicia o MutationObserver
}

async function monitor_janela_PJeCalc() {
	console.log("Extensão maisPJE (" + agora() + "): monitor_janela_PJeCalc");
	
	let tempo_espera = 2000;
	// console.log(preferencias.tempAR)
	if (preferencias.tempAR.includes('atualizacaorapida')) { 
		fundo(true,'maisPJe: atualização rápida..');
	}
	
	document.body.addEventListener('keydown', async function(event) {
		if (event.code === "ESC") {	
			let guardarStorage = browser.storage.local.set({'tempAR': ''});
			Promise.all([guardarStorage]).then(values => { 
				fundo(false);
			});
		}
	});
	
	let barraTitulo = await esperarElemento('div[id="barraTitulo"]');
	// console.log(barraTitulo?.innerText)
	
	if (barraTitulo.innerText.includes('Cálculo > Buscar')) {
		
		let processo_memoria = await getLocalStorage('processo_memoria');
		if (!processo_memoria.numero) {return}
		
		let numeroProcessoDecomposto = await decomporNumeroProcesso(processo_memoria.numero.toString());
		await preencherInput('input[id*="numeroProcessoBusca"]',numeroProcessoDecomposto.numero);
		await preencherInput('input[id*="digitoProcessoBusca"]',numeroProcessoDecomposto.digito);
		await preencherInput('input[id*="anoProcessoBusca"]',numeroProcessoDecomposto.ano);
		await preencherInput('input[id*="justicaBusca"]',numeroProcessoDecomposto.jurisdicao);
		await preencherInput('input[id*="regiaoBusca"]',numeroProcessoDecomposto.regiao);
		await preencherInput('input[id*="varaProcessoBusca"]',numeroProcessoDecomposto.vara);
		await clicarBotao('input[id*="formulario:buscar"]');
		
		if (preferencias.tempAR.includes('atualizacaorapida') && !preferencias.tempAR.includes(':passo')) {
				
			let guardarStorage = browser.storage.local.set({'tempAR':'atualizacaorapida:passo1'});
			Promise.all([guardarStorage]).then(async values => { 
				
				let msgSemCalculo = await esperarElemento('span[class="box-msg-livre"]',null,1000);
				if (msgSemCalculo?.innerText.includes('Não existem resultados para a pesquisa solicitada.')) {
					await criarCaixaDeAlerta('ALERTA','Processo sem cálculo registrado no PJeCalc!!',5);
					let guardarStorage = browser.storage.local.set({'tempAR': ''});
					Promise.all([guardarStorage]).then(values => { 
						fundo(false);
					});
					
				} else {
					let bt = await esperarElemento('a[class="linkSelecionar"][title="Abrir"]')
					await ativarElemento(bt, tempo_espera);
					await clicarBotao(bt) 
				}

			});
		
		}
	
	} else if (barraTitulo.innerText.includes('Cálculo > Dados do Cálculo') && preferencias.tempAR.includes('atualizacaorapida') && preferencias.tempAR.includes(':passo1')) {
		console.log('entrou2');
		let guardarStorage = browser.storage.local.set({'tempAR':'atualizacaorapida:passo2'});
		Promise.all([guardarStorage]).then(async values => {
			let bt = await esperarElemento('li a','Liquidar Atualização')
			await ativarElemento(bt, tempo_espera);
			await clicarBotao(bt);
		});
		
	} else if (barraTitulo.innerText.includes('Atualização > Liquidar Atualização') && preferencias.tempAR.includes('atualizacaorapida') && preferencias.tempAR.includes(':passo2')) {
		console.log('entrou3');
		let guardarStorage = browser.storage.local.set({'tempAR':'atualizacaorapida:passo3'});
		Promise.all([guardarStorage]).then(async values => {
			
			let observacao = await esperarElemento('textarea[id="formulario:comentarios"]');			
			await preencherTextArea(observacao,'maisPJe: Atualização Rápida');
			
			//antes de clicar no botão liquidar conferir se o PJeCalc está abrindo o cálculo do processo correto... isso é um bug do PJeCalc
			let processoNumero = document.querySelector('span[id="formulario:panelDadosCalculo"]').innerText.match(new RegExp('\\d{7}-\\d{2}\\.\\d{4}\\.\\d{1,2}\\.\\d{1,2}\\.\\d{4}','g')).join();
			if (processoNumero == preferencias.processo_memoria.numero.toString()) {
				
				let frameAtualizacao = barraTitulo.parentElement.parentElement;
				let bt = frameAtualizacao.querySelector('input[id="formulario:liquidar"]'); //** tem que ser assim, senão ele pega o botão liquidar do menu operações
				await ativarElemento(bt, tempo_espera);
				await clicarBotao(bt);
				
				let aviso = await esperarElemento('div[id="divMensagem"]',null,30000);
				if (aviso.innerText.includes('Operação realizada com sucesso.')) {
					let bt2 = await esperarElemento('li[id="li_operacoes_validar_atualizacao"] a','Enviar para o PJe')
					await ativarElemento(bt2, tempo_espera);
					await clicarBotao(bt2);
				} else if (aviso.innerText.includes('Erro.')) {
					await criarCaixaDeAlerta('ALERTA','Não foi possível atualizar automaticamente.',3);
					let guardarStorage = browser.storage.local.set({'tempAR': ''});
					Promise.all([guardarStorage]).then(values => { 
						fundo(false);
					});
				}
			
			} else {
				
				let var1 = browser.storage.local.set({'tempAR': ''});
				Promise.all([var1]).then(async values => {
					fundo(false);
					await criarCaixaDeAlerta('ALERTA','Erro do PJeCalc.. Processo Incorreto. Refazer o procedimento',3);
					
					await clicarBotao('li[id="li_operacoes_fechar"] a','Fechar');
					window.close();
				});
				
				
			}
		});
		
	} else if (barraTitulo.innerText.includes('Enviar para o PJe') && preferencias.tempAR.includes('atualizacaorapida') && preferencias.tempAR.includes(':passo3')) {
		console.log('entrou4');
		let guardarStorage = browser.storage.local.set({'tempAR':'atualizacaorapida:passo4'});
		Promise.all([guardarStorage]).then(async values => {
				
			let consolidarDados = await esperarElemento('input[value="Consolidar Dados"]')
			if (consolidarDados) { await clicarBotao(consolidarDados) }
			
			await esperarElemento('span[class="rich-messages-label"]','Os dados estão prontos para serem enviados para o PJe',30000); //espera até trinta segundos
			//o botão enviar ao pje somente aparece após consolidar os dados
			let btEnviarPJe = await esperarElemento('input[value="Enviar para o PJe"]')
			if (btEnviarPJe) { 
				await clicarBotao(btEnviarPJe) 
				await sleep(tempo_espera + 2000);
				await clicarBotao('input[id="popup_ok"]');
				
			}
				
		});
		
	} else if (barraTitulo.innerText.includes('Enviar para o PJe') && preferencias.tempAR.includes('atualizacaorapida') && preferencias.tempAR.includes(':passo4')) {
		console.log('entrou5');	
		let guardarStorage = browser.storage.local.set({'tempAR':'atualizacaorapida:passo4'});
		Promise.all([guardarStorage]).then(async values => {
			
			let avisoSucesso = await esperarElemento('div[class="sweet-alert showSweetAlert visible"]'); // o aviso de sucesso/fracasso dispara novo reload da página. por isso tem que verificar antes
			if (avisoSucesso) {
				
				let var1 = browser.storage.local.set({'tempAR': ''});
				Promise.all([var1]).then(async values => {
					if (avisoSucesso?.innerText.toLowerCase().includes('sucesso')) { 
						await clicarBotao('li[class*="header"]','Operações');
						await sleep(tempo_espera);
						await clicarBotao('a[class="menuImageClose"]');
						window.close();
					}
					fundo(false);
				});
				
			}
		});
			
	} else if (document.querySelector('a[id="formulario:linkModalPPJE"]')) {
		console.log('entrou6');
		let calculoAberto = await esperarElemento('input[id="formulario:numero"]');
		if (calculoAberto.value) { return }
		await clicarBotao('a[id="formulario:linkModalPPJE"]');
		pesquisarProcesso();
		
	}
	
	async function pesquisarProcesso() {
		
		console.log(document.location.href)
		
		let var1 = browser.storage.local.get('processo_memoria', async function(result){
			if (!result.processo_memoria.numero) {return}
			console.log(result.processo_memoria.numero.toString());
			await esperarElemento('span[id="formularioModalPPJE:panelModalBusca"]');			
			let numeroProcessoDecomposto = await decomporNumeroProcesso(result.processo_memoria.numero.toString());
			console.log("     |_____" + numeroProcessoDecomposto.numero);
			await preencherInput('input[id*="formularioModalPPJE:numero"]',numeroProcessoDecomposto.numero);
			await preencherInput('input[id*="formularioModalPPJE:digito"]',numeroProcessoDecomposto.digito);
			await preencherInput('input[id*="formularioModalPPJE:ano"]',numeroProcessoDecomposto.ano);
			await preencherInput('input[id*="formularioModalPPJE:justica"]',numeroProcessoDecomposto.jurisdicao);
			await preencherInput('input[id*="formularioModalPPJE:regiao"]',numeroProcessoDecomposto.regiao);
			await preencherInput('input[id*="formularioModalPPJE:vara"]',numeroProcessoDecomposto.vara);
			await clicarBotao('a[title*="Pesquisar"]');
			await sleep(1000);
			await clicarBotao('input[value="Confirmar"]');
		});
	}
	
	async function ativarElemento(el, s) {
		return new Promise(async resolve => {
			el.focus();
			el.style.outline = '4px solid red';
			await sleep(s);
			el.style.outline = 'revert';
			resolve(true);
		});
	}
	
	
}

async function monitor_janela_sif() {
	console.log("Extensão maisPJE (" + agora() + "): monitor_janela_sif");
	
	let nomeBeneficiarioSelecionado = 'nenhum';
	let representacaoBeneficiarioSelecionado = 'nenhum';
	
	browser.storage.local.get('processo_memoria', function(result){
		preferencias.processo_memoria = result.processo_memoria;
	});
	
	let target = document.body;
	let observer = new MutationObserver(async function(mutationsDocumento) {
		mutationsDocumento.forEach(async function(mutation) {
			if (!mutation.removedNodes[0] && !mutation.addedNodes[0]) { return }
			
			if (preferencias.processo_memoria) {
				if (mutation.removedNodes[0]) {
					if (!mutation.removedNodes[0].tagName) { return }
					
					
					// console.log('REMOVEDNODES : ' + mutation.removedNodes[0].tagName + " : " + mutation.removedNodes[0].className + " : " + mutation.removedNodes[0].innerText);
					
					if (mutation.removedNodes[0].tagName == 'DIV' && mutation.removedNodes[0].className.includes('cdk-overlay-backdrop')) {
						
						//somente funciona na opção "NOVO ALVARÁ"
						if (!document.querySelector('pje-novo-alvara-dialog')) { return }
						
						if (!document.querySelector('pje-novo-alvara-dialog h2')) { return }
						
						if (!document.querySelector('pje-novo-alvara-dialog h2').innerText.includes('Incluir Alvará')) { //somente ativa nos casos de novos alvarás
							return;
						}
						
						
						//no caso de edição desligar a extensão
						if (!document.querySelector('pje-novo-alvara-dialog button[class*="botao-incluir-alterar"]')) { return }
						
						if (document.querySelector('pje-novo-alvara-dialog button[class*="botao-incluir-alterar"]').innerText.includes('Alterar')) { return }
						
						
						//ignorar na primeira vez
						let ancora = document.querySelector('mat-select[placeholder="Beneficiário"]');
						if (!ancora) { return }
						if (ancora.innerText.includes('Beneficiário')) { return }
						
						if (!document.querySelector('mat-select[placeholder="Beneficiário"]').innerText.includes(nomeBeneficiarioSelecionado)) { //preenche de acordo com o beneficiário
							if (ancora.getAttribute('maisPje') == 'true') { return }
							mudancaInfo()
						} else if (!document.querySelector('mat-select[placeholder="Representação Processual"]').innerText.includes(representacaoBeneficiarioSelecionado)) { //preenche de acordo com a representação processual
							ancora = document.querySelector('mat-select[placeholder="Representação Processual"]');
							if (ancora.getAttribute('maisPje') == 'true') { return }
							mudancaInfo()
						}
					}
				}
			}
			
			if (mutation.addedNodes[0]) {
				if (!mutation.addedNodes[0].tagName) { return }
				
				// console.log('ADDNODES : ' + mutation.addedNodes[0].tagName + " : " + mutation.addedNodes[0].className + " : " + mutation.addedNodes[0].innerText);
				
				if (mutation.addedNodes[0].tagName == 'LABEL' && mutation.addedNodes[0].innerText == 'Código do Banco') {
					let ancora = await esperarElemento('pje-form-conta-cred mat-form-field');
					inserirbotao(ancora);
				}
				
				if (mutation.addedNodes[0].tagName == 'MAT-ERROR' && mutation.addedNodes[0].innerText.includes('selecionado um magistrado')) {
					if (preferencias.modulo8) {
						if (preferencias.modulo8.length > 0) {
							let processoNumero = document.querySelector('mat-card-title[class*="dadosProcesso"]').innerText.match(new RegExp('\\d{7}-\\d{2}\\.\\d{4}\\.\\d{1,2}\\.\\d{1,2}\\.\\d{4}','g')).join();
							let magistrado = await filtroMagistrado(processoNumero);
							await clicarBotao('pje-selecionar-magistrado mat-expansion-panel-header');
							await clicarBotao('mat-list-item', magistrado);
						}
					}
				}
				
			}
		});
	});		
	let configDocumento = { childList: true, characterData: true, subtree:true }
	observer.observe(target, configDocumento); //inicia o MutationObserver
	
	function inserirbotao(elemento) {
		//insere o pacote de ícones
		browser.runtime.sendMessage({tipo: 'insertCSS', file: 'maisPje_icones.css'});
		
		//CRIA BOTÃO CONSULTA RAPIDA DE PROCESSOS
		let container = document.createElement("mat-form-field");
		container.style = 'align-self: center;margin-right: 10px;';
		let atalho = document.createElement("a");
		atalho.id = "maisPJe_atalhoConsultaBancos";
		atalho.style = 'display: flex; position: relative; z-index: 100; text-align: left; color: black;';
		atalho.setAttribute('title','MaisPJe: Consultar Código dos Bancos');
		atalho.onmouseenter = function () {atalho.style.color  = 'orangered'};
		atalho.onmouseleave = function () {atalho.style.color  = 'black'};
		atalho.onclick = function () {
			let nome_banco = prompt('Digite o nome do banco, ou parte dele:\n','');
			if (!nome_banco) { return }
			let url = "https://www.google.com/search?q=codigo+de+transferencia+banco+" + nome_banco + "&client=firefox-b-e";
			window.open(url);
		};
		let i = document.createElement("i");
		i.className = "search";
		i.style = "display: inline-block; font-style: normal; font-variant: normal; text-rendering: auto; line-height: 1; cursor: pointer; width: 2vh; height: 2vh; background-color: gray;";
		atalho.appendChild(i);						
		container.appendChild(atalho);
		elemento.insertAdjacentElement('beforebegin',container);
	}
	
	async function obterDoctoParte(nome) {
		return new Promise(
			resolve => {
				if (!preferencias.processo_memoria) { return resolve(null) } //se vazio
					
				for (const [pos, parte] of preferencias.processo_memoria.autor.entries()) {
					if (parte.nome.includes(nome)) {
						return resolve(parte.cpfcnpj);
						break;
					}
				}
				
				for (const [pos, parte] of preferencias.processo_memoria.reu.entries()) {
					if (parte.nome.includes(nome)) {
						return resolve(parte.cpfcnpj);
						break;
					}
				}
				
				for (const [pos, parte] of preferencias.processo_memoria.terceiro.entries()) {
					if (parte.nome.includes(nome)) {
						return resolve(parte.cpfcnpj);
						break;
					}
				}
				
				for (const [pos, parte] of preferencias.processo_memoria.autor.entries()) {
					for (const [pos2, adv] of parte.representantes.entries()) {
						if (adv.nome.includes(nome)) {
							return resolve(adv.cpfcnpj);
							break;
						}
					}
				}
				
				for (const [pos, parte] of preferencias.processo_memoria.reu.entries()) {
					for (const [pos2, adv] of parte.representantes.entries()) {
						if (adv.nome.includes(nome)) {
							return resolve(adv.cpfcnpj);
							break;
						}
					}
				}
				
				for (const [pos, parte] of preferencias.processo_memoria.terceiro.entries()) {
					for (const [pos2, adv] of parte.representantes.entries()) {
						if (adv.nome.includes(nome)) {
							return resolve(adv.cpfcnpj);
							break;
						}
					}
				}
			}
		);
	}
	
	async function mudancaBeneficiario(ancora) {
		fundo(true);
		ancora.setAttribute('maisPje',true);
		nomeBeneficiarioSelecionado = ancora.innerText;
		let tipoBeneficiarioSelecionado = nomeBeneficiarioSelecionado.match(new RegExp(/(\([^\)]+\))/gm)).join();
		nomeBeneficiarioSelecionado = nomeBeneficiarioSelecionado.replace(tipoBeneficiarioSelecionado,'').trim();
		let doctoBeneficiarioSelecionado = await obterDoctoParte(nomeBeneficiarioSelecionado);
		if (!doctoBeneficiarioSelecionado) { return }
		
		await clicarBotao('mat-select[placeholder="Representação Processual"]');
		await clicarBotao('mat-option[value="Jus Postulandi"]');
		representacaoBeneficiarioSelecionado = document.querySelector('mat-select[placeholder="Representação Processual"]').innerText;					
		
		if (doctoBeneficiarioSelecionado.length > 14) {
			await clicarBotao('mat-radio-button[value="juridica"] input');
		} else {
			await clicarBotao('mat-radio-button[value="fisica"] input');
		}
		await sleep(500);
		await preencherInput('input[data-placeholder="Nome do Titular"]',nomeBeneficiarioSelecionado)
		await preencherInput('input[formcontrolname="numeroDocumento"]',doctoBeneficiarioSelecionado)
		ancora.setAttribute('maisPje',false);
		guardarInfo(nomeBeneficiarioSelecionado, representacaoBeneficiarioSelecionado, nomeBeneficiarioSelecionado + doctoBeneficiarioSelecionado);
		fundo(false);
	}
	
	async function mudancaRepresentacao(ancora) {
		fundo(true);
		ancora.setAttribute('maisPje',true);
		let representacaoBeneficiarioSelecionado = ancora.innerText;
		let tipoRepresentanteSelecionado = representacaoBeneficiarioSelecionado.match(new RegExp(/(\([^\)]+\))/gm)).join();
		representacaoBeneficiarioSelecionado = representacaoBeneficiarioSelecionado.replace(tipoRepresentanteSelecionado,'').trim();
		let doctoRepresentanteSelecionado = await obterDoctoParte(representacaoBeneficiarioSelecionado);
		if (!doctoRepresentanteSelecionado) { return }
		
		if (doctoRepresentanteSelecionado.length > 14) {
			await clicarBotao('mat-radio-button[value="juridica"] input');
		} else {
			await clicarBotao('mat-radio-button[value="fisica"] input');
		}
		await sleep(500);
		await preencherInput('input[data-placeholder="Nome do Titular"]',representacaoBeneficiarioSelecionado)
		await preencherInput('input[formcontrolname="numeroDocumento"]',doctoRepresentanteSelecionado)
		ancora.setAttribute('maisPje',false);
		guardarInfo(null, representacaoBeneficiarioSelecionado, representacaoBeneficiarioSelecionado + doctoRepresentanteSelecionado);
		fundo(false);
	}
	
	async function guardarInfo(beneficiario, representante, informacoes) {
		if (beneficiario) { document.querySelector('pje-form-beneficiario').setAttribute('maisPje', beneficiario) }
		if (representante) { document.querySelector('pje-form-representacao').setAttribute('maisPje', representante) }
		if (informacoes) { document.querySelector('pje-form-conta-cred').setAttribute('maisPje', informacoes) }
	}
	
	async function mudancaInfo() {
		let beneficiarioAtual = document.querySelector('mat-select[placeholder="Beneficiário"]').innerText;
		let representanteAtual = document.querySelector('mat-select[placeholder="Representação Processual"]').innerText;
		let info1 = (!document.querySelector('input[data-placeholder="Nome do Titular"]')) ? 'nenhum' : document.querySelector('input[data-placeholder="Nome do Titular"]').value;
		let info2 = (!document.querySelector('input[formcontrolname="numeroDocumento"]')) ? 'nenhum' : document.querySelector('input[formcontrolname="numeroDocumento"]').value;
		let informacoesAtual = info1 + info2;
		
		let beneficiarioAnterior = document.querySelector('pje-form-beneficiario').getAttribute('maisPje');
		let representanteAnterior = document.querySelector('pje-form-representacao').getAttribute('maisPje');
		let informacoesAnterior = document.querySelector('pje-form-conta-cred').getAttribute('maisPje');
		
		// console.log(beneficiarioAtual + " : " + beneficiarioAnterior);
		// console.log(representanteAtual + " : " + representanteAnterior);
		// console.log(informacoesAtual + " : " + informacoesAnterior);
		
		if (!beneficiarioAtual.includes(beneficiarioAnterior)) {
			// console.log('************************ mudou o beneficiario');
			mudancaBeneficiario(document.querySelector('mat-select[placeholder="Beneficiário"]'));
		} else if (!representanteAtual.includes(representanteAnterior)) {
			// console.log('************************ mudou o representante');
			mudancaRepresentacao(document.querySelector('mat-select[placeholder="Representação Processual"]'));
		} else if (!informacoesAtual.includes(informacoesAnterior)) {
			// console.log('************************ mudou a informação');
			guardarInfo(null,null,informacoesAtual);
		} else {
			return;
		}		
	}
}

async function monitor_janela_siscondj() {
	console.log("Extensão maisPJE (" + agora() + "): monitor_janela_siscondj");
	
	browser.storage.local.get('processo_memoria', function(result){
		preferencias.processo_memoria = result.processo_memoria;
	});

	let target = document.body;
	let observer = new MutationObserver(async function(mutationsDocumento) {
		mutationsDocumento.forEach(async function(mutation) {
			if (!mutation.addedNodes[0]) { return }
			if (!mutation.addedNodes[0].tagName) { return }
				
			// console.log('ADDNODES : ' + mutation.addedNodes[0].tagName + " : " + mutation.addedNodes[0].className + " : " + mutation.addedNodes[0].innerText);
			
			if (mutation.addedNodes[0].tagName == "DIV" && mutation.addedNodes[0].className.includes('ui-dialog-buttonpane') && mutation.addedNodes[0].innerText.includes('Emitir') && mutation.addedNodes[0].innerText.includes('Cancelar')) {
				obterExtrato();
			}

			if (mutation.addedNodes[0].tagName == "PRE" && mutation.addedNodes[0].innerText.includes('CONTA JUDICIAL') ) {
				let padrao = /\d{1,}/g;
				let ocorrencias = mutation.addedNodes[0].innerText + '';
				ocorrencias = ocorrencias.match(padrao).join().split(',');
				let textocopiado = ocorrencias[0] + '-' + ocorrencias[1];
				navigator.clipboard.writeText(textocopiado);
			}
		});
	});		
	let configDocumento = { childList: true, characterData: true, subtree:true }
	observer.observe(target, configDocumento); //inicia o MutationObserver
	
	await abrirSaldoAtualizadoDasContas();
	await abrirSaldoAtualizadoDasParcelasdaConta();
	
	criarBotaoImprimirEmLote();

	async function obterExtrato() {
		return new Promise(async resolve => {
			let inicio = preferencias.processo_memoria.dtAutuacao;
			let dNow = new Date();
			let fim = ("0" + dNow.getDate()).slice(-2) + '/' + ("0" + (dNow.getMonth()+1)).slice(-2) + '/' + dNow.getFullYear();
			await acao1(inicio, fim);
		});
	}
	
	async function abrirSaldoAtualizadoDasContas() {
		return new Promise(async resolve => {
			console.log('    |___abrirSaldoAtualizadoDasContas');
			let contas = await esperarColecao('img[alt="Parcelas"]',1,preferencias.maisPje_velocidade_interacao);
			if (!contas) { return resolve(false); }
			for (const [pos, conta] of contas.entries()) {
				
				//gravar o numero da conta pra pegar depois
				let elNumConta = conta.closest('tr[id*="linhaConta_"]');
				let numConta = elNumConta.innerText.match(/\d{4,}/gm).join();				
				elNumConta.setAttribute('maisPJeNumConta',numConta);
				
				conta.scrollIntoView({behavior: 'auto',block: 'center',inline: 'center'});
				await clicarBotao(conta);

				if (await aguardarCarregamento()) { break }
				// await sleep(1000);
			}
			// console.log('saiu 1')
			return resolve(true);
		});
	}
	
	async function abrirSaldoAtualizadoDasParcelasdaConta() {
		return new Promise(async resolve => {
			console.log('    |___abrirSaldoAtualizadoDasParcelasdaConta');
			let parcelasDaConta = await esperarColecao('td[id*="td_saldo_parcela_saldo"] img[alt="Atualizar"]',1,preferencias.maisPje_velocidade_interacao);
			if (!parcelasDaConta) { return resolve(false); }	
			//este for torna visível todas as tabelas de parcelas
			for (const [pos, parcela] of parcelasDaConta.entries()) {
				await sleep(preferencias.maisPje_velocidade_interacao);
				
				let elementoAncora = parcela.closest('tr').querySelector('img[src*="advanced.gif"]');
				let identificacaoDaConta = parcela.closest('tr[id*="contaId_"]').previousElementSibling.getAttribute('maispjenumconta');				
				
				parcela.scrollIntoView({behavior: 'auto',block: 'center',inline: 'center'});
				if (parcela.style.display === 'none') { parcela.style.display = 'table-row' }
				await clicarBotao(parcela);
				if (await aguardarCarregamento()) { break }
				
				await criarBotaoImprimirIndividual(elementoAncora,identificacaoDaConta);
			}
			// console.log('saiu 2')
			return resolve(true);
		});
	}

	async function criarBotaoImprimirEmLote() {
		let bt = criarElemento('span', ' width: 80px; height: auto; background-color: rgb(204, 204, 204); border: 1px solid gray; border-radius: 3px; cursor: pointer;   padding: 10px;', 'Baixar TODOS os Extratos');
		bt.onclick = async function () {
			let extratosDaConta = await esperarColecao('span[id*="maisPje_bt_download_extrato_"]',1,preferencias.maisPje_velocidade_interacao);
			if (!extratosDaConta) { return resolve(false); }

			for (const [pos, item] of extratosDaConta.entries()) {
				if (item.checkVisibility()) {
					item.closest('tr').style.backgroundColor = 'orange';
					item.closest('tr').style.border = '1px solid orangered'
					
					item.click();
					await sleep(1000);

					item.closest('tr').style.backgroundColor = 'unset';
					item.closest('tr').style.border = 'unset'
				}
			}

			await criarCaixaDeAlerta('AVISO', 'Download concluído com sucesso! Foram baixados ' + (extratosDaConta.length) + ' extratos.', temporizador=1);
		}
		document.getElementById('divAcao').appendChild(bt);
	}

	async function criarBotaoImprimirIndividual(elementoAncora,nomeArquivo) {
		return new Promise(async resolve => {
			let bt = criarElemento('span', ' width: 80px; height: auto; background-color: rgb(204, 204, 204); border: 1px solid gray; border-radius: 3px; cursor: pointer;   padding: 10px;', '');
			let cdConta = extrairNumeros(elementoAncora.getAttribute('onclick'));
			let numConta = extrairNumeros(elementoAncora.getAttribute('onclick'));
			bt.id = 'maisPje_bt_download_extrato_' + nomeArquivo;			
			bt.className = "botaoPDF_all";
			bt.style = "top: -2px;position: relative;";
			bt.title = 'maisPJe: baixar extrato'
			bt.setAttribute('maisPje_posConta', getPosConta(nomeArquivo));
			bt.onclick = async function () {

				let dtInicio = preferencias.processo_memoria.dtAutuacao.replace(/\//g,'-');
				let dNow = new Date();
				let dtFim = ("0" + dNow.getDate()).slice(-2) + '-' + ("0" + (dNow.getMonth()+1)).slice(-2) + '-' + dNow.getFullYear();
				let url = getUrlBaseSiscondj() + '/pages/movimentacao/conta/downloadPdf/extrato/' + dtInicio + '/' + dtFim + '/' + cdConta + '?tipo=download';
				await fetch(url)
					.then(async res => res.blob())
					.then(async blob => {
						let blobURL = window.URL.createObjectURL(blob);
						let linkTemporario = document.createElement('a');
						linkTemporario.style.display = 'none';
						linkTemporario.href = blobURL;
						linkTemporario.setAttribute('download', nomeArquivo + '-' + this.getAttribute('maisPje_posConta') + '.pdf');
						linkTemporario.setAttribute('target', '_blank');
						linkTemporario.click();
						await sleep(1000);
						window.URL.revokeObjectURL(blobURL);
					});

				await criarCaixaDeAlerta('AVISO', 'Download concluído com sucesso!', temporizador=1);
			}
			elementoAncora.parentElement.parentElement.appendChild(bt);
			return resolve(true);
		});
	}

	function getPosConta(id) {
		let qtde = document.querySelectorAll('span[id*="maisPje_bt_download_extrato_' + id + '"]').length;
		return (qtde + 1);
	}
	
	async function aguardarCarregamento() {
		return new Promise(resolve => {
			let estado = true;
			let telaDeBloqueio;
			let x = 0;
			let check = setInterval(function() {
				// console.log(x);
				telaDeBloqueio = document.querySelector('.escurecer#bloqueio');
				if (telaDeBloqueio && estado) {
					// console.log('***********bloqueado');
					estado = false;
				}
				
				if (!telaDeBloqueio && !estado) {
					// console.log('***********desbloqueado')
					clearInterval(check);
					return resolve(false);
				}
				
				if (x > 20) { //limitador 2 segundos
					clearInterval(check);
					// console.log('sai com erro')
					return resolve(true); //true == deu erro
				}
				x++;				
			}, 100);
		});
	}
	
	async function acao1(dt_inicio, dt_fim) {
		console.log('               acao1')
		if (!dt_inicio) { acao2(dt_inicio, dt_fim) }

		let el = await esperarElemento('div[class*="ui-dialog"][aria-describedby="dialog_data_extrato"] input[id="dataInicial"]:not([type="hidden"]):not([disabled]');
		el.value = dt_inicio;
		triggerEvent(el, 'input');
		acao2(dt_inicio, dt_fim);
	}
	
	async function acao2(dt_inicio, dt_fim) {
		console.log('               acao2')
		let el = await esperarElemento('div[class*="ui-dialog"][aria-describedby="dialog_data_extrato"] input[id="dataFinal"]:not([type="hidden"]):not([disabled]');
		el.value = dt_fim;
		triggerEvent(el, 'input');

		if (dt_inicio) { acao3() }
	}
	
	async function acao3() {
		console.log('               acao3')
		let botoesDialog = await esperarColecao('div[class*="ui-dialog"][aria-describedby="dialog_data_extrato"] button',3) //tem o botão fechar [0], emitir [1] e cancelar [2]
		await clicarBotao(botoesDialog[1]);		
		if (await aguardarCarregamento()) { return }
	}

}

async function monitor_janela_protestojud() {
	console.log("Extensão maisPJE (" + agora() + "): monitor_janela_protestojud");
	
}

async function monitor_janela_censec() {
	console.log("Extensão maisPJE (" + agora() + "): monitor_janela_censec");
	let targetDocumento = document.body;
	let observerDocumento = new MutationObserver(async function(mutationsDocumento) {
		mutationsDocumento.forEach(async function(mutation) {
		if (!mutation.removedNodes[0] && !mutation.addedNodes[0]) { return }

		if (mutation.addedNodes[0]) {
			if (!mutation.addedNodes[0].tagName) { return }
			// console.log("+++++++++ADDNODES: " + mutation.addedNodes[0].tagName + " : " + mutation.addedNodes[0].className + " : " + mutation.addedNodes[0].innerText);

			if (mutation.addedNodes[0].tagName == 'DIV' && mutation.addedNodes[0].innerText.includes('Exportar resultados')) {
				if (document.getElementById('maisPje_imprimirEmLote')) { return }
				let ancora = mutation.addedNodes[0].querySelector('button');
				inserirBotoes(ancora.parentElement);
			}
		}

		if (mutation.removedNodes[0]) {
			if (!mutation.removedNodes[0].tagName) { return }
			// console.log("----------REMOVEDNODES: " + mutation.removedNodes[0].tagName + " : " + mutation.removedNodes[0].className + " : " + mutation.removedNodes[0].innerText);
			if (mutation.removedNodes[0].tagName == 'DIV' && mutation.removedNodes[0].className.includes('cdk-overlay-backdrop')) {
				if (document.querySelector('ngx-loading')) { document.querySelector('ngx-loading').setAttribute('maisPje','true') }
			}
		}

		});
	});
	let configDocumento = { childList: true, subtree:true }
	observerDocumento.observe(targetDocumento, configDocumento); //inicia o MutationObserver

	function inserirBotoes(ancora) {
		let atalho1 = document.createElement("button");
		atalho1.id = "maisPje_imprimirEmLote";
		atalho1.className = "mat-button mat-button-base";
		atalho1.style = "background-color: #e7e7e7; color: #009bb3; margin-right: 3px; vertical-align: middle;";
		atalho1.innerText = "Imprimir em Lote";
		atalho1.onmouseenter = function () {atalho1.style.backgroundColor = '#d2d2d2'};
		atalho1.onmouseleave = function () {atalho1.style.backgroundColor = '#e7e7e7'};
		atalho1.onclick = function () {imprimirEmLote()};
		ancora.appendChild(atalho1);
	}

	async function imprimirEmLote() {
		let linhas = await esperarColecao('div[class="material-table"] mat-row');
		for (const [pos, linha] of linhas.entries()) {
			// console.log('linha ' + pos + ': ' + linha.innerText);
			console.log('*******' + linha.children.length)
			linha.scrollIntoView({behavior: 'smooth',block: 'start'});
			linha.style.backgroundColor = (linha.children.length > 5) ? '#c3d336' : 'unset';
			await clicarBotao(linha.querySelector('a'));
			await escolherOpcaoTeste('mat-select[aria-label="Items per page:"]','100');
			await esperarElemento('ngx-loading[maisPje="true"]');
			await clicarBotao('button[id="maisPje_assistenteImpressao_bt_copiar"]');
			await clicarBotao('button','arrow_back_ios');
			await sleep(1000);
		}
	}
}

async function monitor_janela_onr() {
	
	teste_mutation_observer();
}

function corrigeCabecalho() {
	let cabecalho = document.querySelector('mat-sidenav-container[class*="mat-drawer-container"]');							
	if (!cabecalho) { return }
	cabecalho.style.setProperty("position", "relative", "important");
	cabecalho.style.setProperty("height", "auto", "important");
}
	
//FUNÇÃO RESPONSÁVEL POR ADICIONAR A OPÇÃO DE ZOOM NO EDITOR DE TEXTOS
async function addZoom_Editor() {
	return new Promise(async resolve => {
		let jaExiste = await esperarElemento('div[id="extensaoPje_barra_zoom_editor"]',null,1000);
		if (jaExiste) { return resolve(true) }
		
		let toolbar_editor = await esperarElemento('div[class*="ck-toolbar__items"]');
		
		if (!toolbar_editor) { return }
		
		let componente_negrito_editor = await esperarElemento('div[class*="ck-toolbar__items"] span','Negrito');
		
		if (!componente_negrito_editor) { return }	
		
		let ancora = document.querySelector('div[class*="ck-toolbar__items"]');
		let opcoes = [0.5, 0.75, 0.9, 1, 1.25, 1.5, 2, 3, 4];
		
		//criar estrutura da barra_zoom
		let barra_zoom = document.createElement("div");
		barra_zoom.id = "extensaoPje_barra_zoom_editor";
		
		//cria o combobox do zoom
		let combobox = document.createElement('select');
		opcoes.forEach(function(item){
		   let opt = document.createElement('option');
		   opt.value = item;
		   opt.innerText = isNaN(item) ? item : (parseFloat(item) * 100) + '%';
		   combobox.appendChild(opt);
		});
		
		combobox.onchange = function () {					
			//gravar na memoria
			let var1 = browser.storage.local.set({'zoom_editor': this.value});
			Promise.all([var1]).then(values => {
				zoom_editor(this.value);
			});
		};
		
		barra_zoom.appendChild(combobox);
		
		if (ancora.firstElementChild.nextSibling) {
			ancora.insertBefore(barra_zoom, ancora.firstElementChild.nextSibling);
		}
		
		//carrega o zoom favorito do storage				
		let var1 = browser.storage.local.get('zoom_editor', function(result){
			if (!result.zoom_editor) {
				result.zoom_editor = 1;
			}
			let preferido = document.querySelector('div[id="extensaoPje_barra_zoom_editor"] option[value="' + result.zoom_editor + '"]')
			preferido.setAttribute('selected', true);
			zoom_editor(result.zoom_editor);
		});
		
		return resolve(true);
	});
}

function zoom_editor(percentual) {
	let el = document.querySelector('div[class*="editor-container"]');
	
	if (!el) {
		return
	}
	
	//AJUSTA A LARGURA DO PAPEL
	let papel = document.querySelector('div[class*="layout-papel"]');
	papel.style.setProperty('max-width', '90%');
	
	//APLICA O ZOOM NO DOCUMENTO
	let tamanho100porcento = 0.54;	
	tamanho100porcento = parseFloat(tamanho100porcento) * parseFloat(percentual);
	el.style.setProperty('font-size-adjust', tamanho100porcento, 'important'); 
	
	//CORRIGE O LINE-HEIGHT
	let corpo = el.getElementsByTagName('P');
	if (!corpo) {
		return
	}	
	let map = [].map.call(
		corpo, 
		function(elemento) {
			elemento.style.setProperty('line-height', 'normal');
		}
	);
}

async function editarCalendarioGigs(consultaAPI) {
	// console.log("editarCalendarioGigs()");
	if (!consultaAPI) {
		let check = setInterval(function() {
			if (document.querySelector('mat-datepicker-content')) {
				clearInterval(check);
				iniciar();
				iniciarMonitorDoCalendario(); //monitora as mudanças de mês do calendário
			}
		}, 100);
		
		function iniciar() {
			let meseano = document.querySelector('button[aria-label="Choose month and year"]').innerText;
			let mes = mesEmNumero(meseano.match(new RegExp("[A-Z]{3}","g")).join());
			let ano = meseano.match(new RegExp("\\d{4}","g")).join();
			console.log("Consultar API Calendário: " + mes + "/" + ano);
			buscarFeriados(mes, ano);
			
			//inserir legenda
			if (!document.getElementById('maisPje_editor_calendario_div_legenda')) {
				let ancora = document.querySelector('mat-datepicker-content');
				let div = document.createElement("div");
				div.id = "maisPje_editor_calendario_div_legenda";
				div.style = "width: " + ancora.offsetWidth + "px;height: auto;display: flex; text-align: center;font-size: .87em;background-color: white;color: rgba(0, 0, 0, 0.87); border-radius: 0 0 4px 4px;padding: 0 2vh 2vh 0";
				
				let legendaMunicipal = document.createElement("div");
				legendaMunicipal.style = "width: 1.4em; height: 1.4em; background-color: rgba(235, 164, 16, 0.6); border-radius: 999px; margin-left: 1vw;";
				div.appendChild(legendaMunicipal);
				let legendaMunicipal_span = document.createElement("span");
				legendaMunicipal_span.textContent = "Municipal";
				div.appendChild(legendaMunicipal);				
				div.appendChild(legendaMunicipal_span);
				
				let legendaEstadual = document.createElement("div");
				legendaEstadual.style = "width: 1.4em; height: 1.4em; background-color: rgba(0, 128, 0, 0.6); border-radius: 999px; margin-left: 1vw;";
				div.appendChild(legendaEstadual);
				let legendaEstadual_span = document.createElement("span");
				legendaEstadual_span.textContent = "Estadual";
				div.appendChild(legendaEstadual);
				div.appendChild(legendaEstadual_span);
				
				let legendaNacional = document.createElement("div");
				legendaNacional.style = "width: 1.4em; height: 1.4em; background-color: rgba(30, 144, 255, 0.6); border-radius: 999px; margin-left: 1vw;";
				div.appendChild(legendaNacional);
				let legendaNacional_span = document.createElement("span");
				legendaNacional_span.textContent = "Nacional";
				div.appendChild(legendaNacional);
				div.appendChild(legendaNacional_span);
				
				ancora.appendChild(div);
			}
			
			//inserir rodapé para tooltip
			if (!document.getElementById('maisPje_editor_calendario_div_tooltip')) {
				let ancora = document.querySelector('mat-datepicker-content');
				let div = document.createElement("div");
				div.id = "maisPje_editor_calendario_div_tooltip";
				div.style = "width: " + ancora.offsetWidth + "px;height: auto;text-align: center;font-size: .87em;background-color: #fff0;color: rgba(0,0,0,.54); border-radius: 0 0 4px 4px;padding-top: .4em; padding-bottom: .4em; position: absolute;";
				let span = document.createElement("span");
				span.id = "maisPje_editor_calendario_span_tooltip"
				span.style="background-color: #666565;display: block;color: white;border-radius: 0 0 4px 4px;";
				div.appendChild(span);
				ancora.appendChild(div);
			}
		}
	} else {
		let arrayDiasdoMes = [  //um array com 30/31 dias, um para cada dia do mes
			["1","",""],
			["2","",""],
			["3","",""],
			["4","",""],
			["5","",""],
			["6","",""],
			["7","",""],
			["8","",""],
			["9","",""],
			["10","",""],
			["11","",""],
			["12","",""],
			["13","",""],
			["14","",""],
			["15","",""],
			["16","",""],
			["17","",""],
			["18","",""],
			["19","",""],
			["20","",""],
			["21","",""],
			["22","",""],
			["23","",""],
			["24","",""],
			["25","",""],
			["26","",""],
			["27","",""],
			["28","",""],
			["29","",""],
			["30","",""],
			["31","",""]
		];
		
		//fazer um map com o resulta dos feriados. Pega os feriados em continuação e os feriados isolados e salva no arrayDiasdoMes
		let meseano = document.querySelector('button[aria-label="Choose month and year"]').innerText;
		let mes = mesEmNumero(meseano.match(new RegExp("[A-Z]{3}","g")).join());
		let ano = meseano.match(new RegExp("\\d{4}","g")).join();
		let map = [].map.call(
			consultaAPI, 
			function(feriado) {
				if (feriado.dataFinal) { //é um feriado em continuação
					let dia_temp_inicial = parseInt(feriado.dtDia)
					let mes_temp_inicial = parseInt(feriado.dtMes)
					let ano_temp_inicial = parseInt(feriado.dtAno)
					let dia_temp_final = parseInt(feriado.dtDiaFinal)
					let mes_temp_final = parseInt(feriado.dtMesFinal)
					let ano_temp_final = parseInt(feriado.dtAnoFinal)
					let primeiro_dia_do_mes = 1;
					let ultimo_dia_do_mes = new Date(ano, mes, 0).getDate();
					
					// console.log("mês: " + mes + " - dia " + primeiro_dia_do_mes + " até " + ultimo_dia_do_mes);
					
					if (mes_temp_final > mes) {
						dia_temp_final = ultimo_dia_do_mes;
					} else if (mes_temp_final < mes) {
						dia_temp_final = ultimo_dia_do_mes;
					} else {
						if (mes_temp_inicial != mes_temp_final) {
							dia_temp_inicial = primeiro_dia_do_mes;
						}
					}
					
					// console.log("dia_temp_ continuo: " + dia_temp_inicial + " até " + dia_temp_final);
					for (i = dia_temp_inicial; i <= dia_temp_final; i++) {
						let descricao_temp = arrayDiasdoMes[i - 1][1] == "" ? feriado.descricao : arrayDiasdoMes[i - 1][1] + "|" + feriado.descricao;
						let tipo_temp = arrayDiasdoMes[i - 1][2] == "" ? feriado.abrangencia : arrayDiasdoMes[i - 1][2] + "|" + feriado.abrangencia;
						arrayDiasdoMes[i - 1] = [i, descricao_temp, tipo_temp];
					}
					
				} else {
					let dia_temp = parseInt(feriado.dtDia);
					// console.log("dia_temp_isolado: " + dia_temp);
					// console.log("     |_____ descrição: " + feriado.descricao);
					let descricao_temp = arrayDiasdoMes[dia_temp - 1][1] == "" ? feriado.descricao : arrayDiasdoMes[dia_temp - 1][1] + "|" + feriado.descricao;
					let tipo_temp = arrayDiasdoMes[dia_temp - 1][2] == "" ? feriado.abrangencia : arrayDiasdoMes[dia_temp - 1][2] + "|" + feriado.abrangencia;
					arrayDiasdoMes[dia_temp - 1] = [dia_temp, descricao_temp, tipo_temp];
				}
			}
		);
		
		for (i = 0; i < 31; i++) {
			console.log(arrayDiasdoMes[i][0] + " : " + arrayDiasdoMes[i][1]);
			let feriado_dia = arrayDiasdoMes[i][0];
			let feriado_descricao = arrayDiasdoMes[i][1];
			let feriado_tipo = arrayDiasdoMes[i][2];
			
			if (feriado_descricao != "") {
				let aria = feriado_dia + " ";			
				let componente_dia = document.querySelector('td[aria-label*="' + aria + '"], button[aria-label*="' + aria + '"]');
				if (!componente_dia) { return }
				//VERIFICA SE JÁ EXISTE UM FERIADO NACIONAL OU ESTADUAL NO MESMO DIA. PREVALECE SEMPRE O NACIONAL, DEPOIS O ESTADUAL E POR FIM O MUNICIPAL
				if (feriado_tipo.toUpperCase().includes('NACIONAL')) {
					componente_dia.style.setProperty('background-color', 'rgba(30, 144, 255, 0.3)');
				} else if (feriado_tipo.toUpperCase().includes('ESTADO')) {
					componente_dia.style.setProperty('background-color', 'rgba(0, 128, 0, 0.3)');
				} else if (feriado_tipo.toUpperCase().includes('MUNICIPIO')) {
					componente_dia.style.setProperty('background-color', 'rgba(235, 164, 16, 0.3)');
				} else {
					componente_dia.style.setProperty('background-color', 'rgba(147, 147, 147, 0.3)');
				}				
				componente_dia.style.setProperty('border-radius', '999px');
				componente_dia.setAttribute('maisPje_editor_tooltip', feriado_descricao);
				componente_dia.onmouseenter = function (event) {
					let linha = event.target.getAttribute('maisPje_editor_tooltip');
					let caracter = '|';
					let elemento = document.getElementById('maisPje_editor_calendario_span_tooltip');
					elemento.textContent = "";
					let arr = typeof(linha) == "undefined" ? "" : linha.split(caracter);	
					for(let i = 0; i < arr.length; i++ ){
						if (arr[i] != "") {
							if (i > 0) {
								elemento.appendChild(document.createElement("br"));
							}
							elemento.appendChild(document.createTextNode(arr[i]));
						}
					}
				};
				componente_dia.onmouseleave = function (event) {					
					document.getElementById('maisPje_editor_calendario_span_tooltip').textContent = "";					
				};
			}			
		}
	}
	
	function iniciarMonitorDoCalendario() {		
		console.log("Extensão maisPJE (" + agora() + "): iniciarMonitorDoCalendario");
		let targetDocumento = document.querySelector('button[aria-label="Choose month and year"]');
		let observerDocumento = new MutationObserver(function(mutationsDocumento) {
			mutationsDocumento.forEach(function(mutation) {
				if (Object.prototype.toString.call(mutation.target) === "[object Text]") {
					if (document.querySelector('mat-month-view')) {
						iniciar();
					}
				}
			});
		});		
		let configDocumento = { childList: true, characterData: true, subtree:true }
		observerDocumento.observe(targetDocumento, configDocumento); //inicia o MutationObserver
	}
	
	function mesEmNumero(param) {
		switch(param) {
			case "JAN":
				return 1;
			case "FEV":
				return 2;
			case "MAR":
				return 3;
			case "ABR":
				return 4;
			case "MAI":
				return 5;
			case "JUN":
				return 6;
			case "JUL":
				return 7;
			case "AGO":
				return 8;
			case "SET":
				return 9;
			case "OUT":
				return 10;
			case "NOV":
				return 11;
			case "DEZ":
				return 12;
		}
	}
}

async function buscarFeriados(mes, ano) {
	let url = 'https://' + preferencias.trt + '/pje-administracao-api/api/calendarioseventos/?pagina=1&ativo=true&tamanhoPagina=1000&ano=' + ano + '&mes=' + mes;
	let resposta = await fetch(url);
	let dados = await resposta.json();
	
	if (!dados.resultado) {
		return;
	}
	if (dados.resultado.length < 1) {
		return;
	}
	editarCalendarioGigs(dados.resultado);
}

//INSERE A BORRACHA NO CAMPO RESPONSÁVEL PELA ATIVIDADE
async function gigsInserirBorrachaResponsavel() {
	if (preferencias.AALote.length > 0) { return } //desativa quando vem das ações em lote
	if (!document.getElementById('maisPje_borracha_responsavel')) {
		let base = await esperarElemento('pje-gigs-cadastro-atividades');
		if (!base) { return }
		let ancora = await esperarElemento('pje-gigs-cadastro-atividades input[formcontrolname="responsavel"]');
		if (!ancora) { return }
		let span = document.createElement("span");
		span.style = "position: absolute;top: 10px;right: 10px; cursor: pointer; color: lightgray;";
		span.onmouseenter = function () {span.style.color  = 'gray'};
		span.onmouseleave = function () {span.style.color  = 'lightgray'};
		span.onclick = async function () {
			await preencherInput('input[formcontrolname="responsavel"]','SEM DESTINATÁRIO');
			await clicarBotao('mat-option','SEM DESTINATÁRIO');
		};
		let i = document.createElement("i");
		i.id = 'maisPje_borracha_responsavel';
		i.className = "fas fa-eraser fa-lg";
		span.appendChild(i);
		ancora.parentElement.appendChild(span);
	}
}

//FUNÇÃO: IDENTIFICA AÇÃO DENTRO DO GRUPO "ATIVIDADES" PARA ATRIBUIR O RESPONSAVEL AUTOMATICAMENTE
async function gigsAtribuirResponsavel(el) {
	return new Promise(async resolver => {
		// console.log('gigsAtribuirResponsavel');
		if (preferencias.modulo2.length <= 0) { return resolver(false) }
		if (!document.querySelector('input[formcontrolname="responsavel"]')) { return resolver(false) }
		if (document.querySelector('input[formcontrolname="responsavel"]').value != "") { return resolver(false) }
		if (!el || el.parentElement.tagName == "MAT-OPTION") {
			let pessoa = "";
			let ancora = await esperarElemento('input[formcontrolname="tipoAtividade"]', false, 100);
			let tipoAtividade = ancora.value;		
			
			let rol = preferencias.modulo2;			
			let processoNumero = document.getElementById('dados-processo').innerText.match(new RegExp('\\d{7}-\\d{2}\\.\\d{4}\\.\\d{1,2}\\.\\d{1,2}\\.\\d{4}','g')).join();
			let ano = processoNumero.substring(11, 15);
			let digito;							
			if (ano > 2009) {
				digito = processoNumero.substring(6, 7);					
			} else {
				digito = processoNumero.substring(4, 5);
			}
			let idProcesso = await obterIdProcessoViaApi(processoNumero);
			let fase = await obterDadosProcessoViaApi(idProcesso[0].idProcesso);
			fase = fase.labelFaseProcessual;
			let listaFiltro1, listaFiltro2, listaFiltro3;
			
			//aplica a lista temporária filtro para deixar apenas as regras da condição "dígito final"
			listaFiltro1 = rol.filter(item => item.split('|').toString().includes(digito));
			//aplica a lista temporária filtro para deixar apenas as regras da condição "fase"
			listaFiltro2 = listaFiltro1.filter(item => item.split('|')[2] == fase || item.split('|')[2] == 'Todas');
			//aplica a lista temporária filtro para deixar apenas as regras da condição "tipoAtividade"
			listaFiltro3 = listaFiltro2.filter(item => item.split('|')[0] == tipoAtividade || item.split('|')[0] == ' ');
			
			// console.log('listaFiltro1: ' + listaFiltro1.toString());
			// console.log('listaFiltro2: ' + listaFiltro2.toString());
			// console.log('listaFiltro3: ' + listaFiltro3.toString());
			
			if (listaFiltro3.length <= 0) { return resolver(false) }
			
			if (listaFiltro3.toString().includes(tipoAtividade)) {
				let regra = listaFiltro3.find(item => item.split('|')[0] == tipoAtividade);
				if (regra) { await acao(regra.split('|')[1]) }
			} else {
				let regra = listaFiltro3.find(item => item.split('|')[0] == " ");
				if (regra) { await acao(regra.split('|')[1]) }
			}
		}
		
		async function acao(nome) {
			console.log('gigsAtribuirResponsavel para : ' + nome);			
			await escolherOpcaoGIGS('input[formcontrolname="responsavel"]', nome+'[exato]');
			return resolver(true);
		}
	});
	
	async function escolherOpcaoGIGS(seletor, valor, possuiBarraProgresso) {
		return new Promise(async resolve => {
			//NOVOS TESTES PARA QUE A FUNÇÃO FUNCIONE EM ABAS(GUIAS) DESATIVADAS
			await sleep(preferencias.maisPje_velocidade_interacao);
			if (seletor instanceof HTMLElement) {
			} else {
				seletor = await esperarElemento(seletor);
			}		
			
			seletor.focus();
			seletor.dispatchEvent(simularTecla('keydown',40)); //SETA PRA BAIXO
			
			//teste1 : o carregamento muito rápido da página por vezes não permite ao menu de opções abrir para selecionar a opção desejada
			let teste = await esperarColecao('mat-option[role="option"], option', 5, 1000);			
			if (!teste) {
				seletor.focus();
				seletor.dispatchEvent(simularTecla('keydown',40)); //SETA PRA BAIXO
				//teste2
				teste = await esperarColecao('mat-option[role="option"], option', 5, 1000);			
				if (!teste) {
					seletor.focus();
					seletor.dispatchEvent(simularTecla('keydown',40)); //SETA PRA BAIXO
					//teste3
					teste = await esperarColecao('mat-option[role="option"], option', 5, 1000);			
					if (!teste) {
						seletor.focus();
						seletor.dispatchEvent(simularTecla('keydown',40)); //SETA PRA BAIXO
					}
				}
			}
			
			await clicarBotao('mat-option[role="option"], option', valor); //aciona a opção
			if (possuiBarraProgresso) {
				await observar_mat_progress_bar();
			}
			return resolve(true);
		});

		async function observar_mat_progress_bar() {
			return new Promise(resolve => {
				let observer = new MutationObserver(function(mutationsDocumento) {
					mutationsDocumento.forEach(function(mutation) {
						if (!mutation.removedNodes[0]) { return }
						if (!mutation.removedNodes[0].tagName) { return }
						if (!mutation.removedNodes[0].tagName.includes("MAT-PROGRESS-BAR")) { return }
						resolve(true);
						observer.disconnect();
					});
				});
				let configDocumento = { childList: true, subtree:true }
				observer.observe(document.body, configDocumento);
			});
		}
	}
}

//FUNÇÃO RESPONSÁVEL POR ABRIR UM DETERMINADO DOCUMENTO DO PROCESSO
async function abrirDocumentoPeloId(idProcesso, IdDocumento) {
	let url = 'https://' + preferencias.trt + '/pje-comum-api/api/processos/id/' + idProcesso + '/timeline?somenteDocumentosAssinados=false&buscarMovimentos=false&buscarDocumentos=true'; 
	console.log(url);
	let resposta = await fetch(url);
	let dados = await resposta.json();
	for (i = 0; i <= dados.length-1; i++) {
		let documento = dados[i];
		// console.log("..." + documento.idUnicoDocumento);
		if (documento.idUnicoDocumento == IdDocumento) {
			// console.log("abrir documento Id " + documento.idUnicoDocumento);
			getAtalhosNovaAba().abrirDocumento.abrirAtalhoemNovaJanela(idProcesso, documento.id);
			break;
		} else if (documento.anexos) {
			// console.log("     |___Analisando Anexos");
			let idAnexo = analisarAnexos(documento.anexos)
			if (idAnexo != "0") {
				// console.log("abrir documento Id " + idAnexo);
				getAtalhosNovaAba().abrirDocumento.abrirAtalhoemNovaJanela(idProcesso, idAnexo);
				break;
			}
		}
		
	}
	
	function analisarAnexos(arrayAnexos) {
		let idAnexo = "0";
		for (j = 0; j <= arrayAnexos.length-1; j++) {
			let anexo = arrayAnexos[j];
			// console.log("     |___..." + anexo.idUnicoDocumento);
			if (anexo.idUnicoDocumento == IdDocumento) {				
				idAnexo = anexo.id;
				break;
			}
		}		
		return idAnexo;
	}
}

//FUNÇÃO DE EXIBIÇÃO DA LOCALIZAÇÃO DO PROCESSO NA PAUTA DE PERÍCIAS
async function painelPericiaTarefaProcesso() {
	fundo(true)
	let listaNum = document.querySelector('table[name="Tabela de Perícias"]').innerText.match(new RegExp('\\d{7}-\\d{2}\\.\\d{4}\\.\\d{1,2}\\.\\d{1,2}\\.\\d{4}','g')).join().split(",");
	let listaId = [];
	let listaPerito = [];
	let listaTarefa = [];
	let listaLaudoEntregue = [];
	
	for (const [pos, processo] of listaNum.entries()) {
		let data1 = await obterIdProcessoViaApiPublica(processo);
		listaId.push(data1[0].id);
		let data3 = await fetchTarefaProcessoJSON(data1[0].id);
		listaTarefa.push(data3);
	}
	
	montarInformações();
	fundo(false);
	
	async function fetchListaPericiasJSON(idProcesso) {
		let resposta = await fetch('https://' + preferencias.trt + '/pje-comum-api/api/pericias?situacao=D&situacao=L&situacao=P&situacao=S&idProcesso=' + idProcesso + '&ordenar=prazoEntrega&ascendente=true');
		let dados = await resposta.json();
		return dados.resultado;
	}
	
	async function fetchTarefaProcessoJSON(idProcesso) {
		let resposta = await fetch('https://' + preferencias.trt + '/pje-comum-api/api/processos/id/' + idProcesso + '/tarefas?maisRecente=true');
		let dados = await resposta.json();
		return dados[0].nomeTarefa;
	}
	
	function fetchListaDocumentosJSON(idProcesso, idPerito) {
		let url = 'https://' + preferencias.trt + '/pje-comum-api/api/processos/id/' + idProcesso + '/timeline?somenteDocumentosAssinados=false&buscarMovimentos=false&buscarDocumentos=true';
		return fetch(url,
		{
			method: "GET",
			mode: "cors",
			credentials: "include",
			headers: {
				"Content-Type": "application/json",
				"X-Grau-Instancia": 1
			}
		})
		.then(function (response) {
			return response.json();
		})
		.then(function (data) {
			let entregou = false;
			for (const [pos, documento] of data.entries()) {
				if (documento.idUsuario === idPerito) {
					if (documento.idTipo === 822 || documento.titulo.includes('laudo')) { //laudo pericial
						entregou = true;
						break;
					}
				}
			}
			console.log(entregou);
			return entregou;
		})
		.catch(function (err) {
			return false;
		});
	}
	
	async function montarInformações() {
		console.log("montar informações");
		let el = document.querySelectorAll('a[aria-label*="Abrir tarefa do processo"]');
		if (!el) {
			return
		}
		for (const [pos, linha] of el.entries()) {
			let numeroProcesso = linha.innerText.match(new RegExp('\\d{7}-\\d{2}\\.\\d{4}\\.\\d{1,2}\\.\\d{1,2}\\.\\d{4}','g')).join();
			let posicao = listaNum.indexOf(numeroProcesso);
			let idProcesso = listaId[posicao];
			let div = document.createElement("div");
			div.textContent = "Tarefa: ";
			div.style = "font-weight: normal;font-size: 1em;background-color:#00800061;";
			let i = document.createElement("i");
			i.style = "font-style: normal;";
			let tarefa = listaTarefa[posicao];
			i.textContent = tarefa;
			if (tarefa.toLowerCase().includes('arquivo')) {
				div.style.backgroundColor = "#ff00004f";
			} else if (tarefa.toLowerCase().includes('sobrestamento')) {
				div.style.backgroundColor = "#ffa50063";
			}
			div.appendChild(i);
			linha.parentElement.appendChild(div);
		}
	}
}

//FUNÇÃO QUE ATRIBUI AUTOMATICAMENTE O MAGISTRADO RESPONSAVEL PELA MINUTA DESPACHO/DECISÃO/SENTENÇA
//DE ACORDO COM O NÚMERO FINAL DO PROCESSO - MÓDULO 8
async function filtroMagistrado(processoNumero) {
	return new Promise(async resolve => {
		if (!preferencias.modulo8) {return resolve("")}
		if (preferencias.modulo8.length < 1) {return resolve("")}
		
		//se informar o numero do processo a função retorna o nome do magistrado
		if (processoNumero) {
			let numero = processoNumero.substring(0, 7);
			let ano = processoNumero.substring(11, 15);
			let ultimo;
			if (ano > 2009) {
				ultimo = processoNumero.substring(6, 7);					
			} else {
				ultimo = processoNumero.substring(4, 5);
			}
			
			if (!ultimo) {
				return resolve("")
			}
			//encontra a regra
			let magistrado = "";
			for (const [pos, item] of preferencias.modulo8.entries()) {
			// for (i = 0; i <= preferencias.modulo8.length; i++) {
				let regra = item.split('|');
				console.log(regra[ultimo] + " - " + regra[10] + " - " + regra[11] + "(" + preferencias.oj_usuario + ")");
				if (regra[11] == "TODOS" || preferencias.oj_usuario.toUpperCase().includes(regra[11].toUpperCase())) {
					if (regra[ultimo] === 'true') {
						magistrado = regra[10];
						break;
					}
				}
			}
			
			// console.log(numero + "/" + ano + " - " + ultimo + " - " + magistrado);
			return resolve(magistrado);
		} else { //caso contrário ela escolhe o magistrado no campo 
			await esperarElemento('span[class="texto-numero-processo"]');
			//recupera o numero final do processo
			processoNumero = document.querySelector('span[class="texto-numero-processo"]').innerText.match(new RegExp('\\d{7}-\\d{2}\\.\\d{4}\\.\\d{1,2}\\.\\d{1,2}\\.\\d{4}','g')).join();
			let numero = processoNumero.substring(0, 7);
			let ano = processoNumero.substring(11, 15);
			let ultimo;
			if (ano > 2009) {
				ultimo = processoNumero.substring(6, 7);					
			} else {
				ultimo = processoNumero.substring(4, 5);
			}
			
			if (!ultimo) {
				return resolve(false);
			}
			//encontra a regra
			let magistrado = "";
			for (const [pos, item] of preferencias.modulo8.entries()) {
			// for (i = 0; i <= preferencias.modulo8.length; i++) {
				let regra = item.split('|');
				console.log(regra[ultimo] + " - " + regra[10] + " - " + regra[11] + "(" + preferencias.oj_usuario + ")");
				if (regra[11] == "TODOS" || preferencias.oj_usuario.toUpperCase().includes(regra[11])) {
					if (regra[ultimo] === 'true') {
						magistrado = regra[10];
						break;
					}
				}
			}
			// console.log(numero + "/" + ano + " - " + ultimo + " - " + magistrado);
			
			//escolhe o magistrado
			await escolherOpcao('mat-select[placeholder="Magistrado"]', magistrado, 2);
			await sleep(preferencias.maisPje_velocidade_interacao + 500);
			//espera por dois segundos pela regra de impedimento ou suspeição, bem como para recarregar os botões (eles mudam sempre que troca o juiz)
			let impedimento_suspeição = await esperarElemento('i[mattooltip="Existe impedimento ou suspeição para este Magistrado"]', null, 2000);
			if (impedimento_suspeição) {
				fundo(false);
				criarCaixaDeAlerta("ALERTA","Atenção, o(a) Magistrado(a) possui regra de suspeição/impedimento ativa para este processo!");
				return;
			}
			return resolve(true);
		}
	});
}

//FUNÇÃO QUE ADICIONA OS ATALHOS PARA INCLUIR DESTINATÁRIOS CEF E BB NO PREPARAR EXPEDIENTES E COMUNICAÇÕES
function inserirParte_BB_CEF() {
	console.log('inserirParte_BB_CEF()');
	monitor_janela_expedientes(); //insere o monitor na tarefa PREPARAR EXPEDIENTES E COMUNICAÇÕES
	let check = setInterval(function() {
		if (document.querySelector('button[mattooltip="Adicionar outros destinatários"]')) {
			clearInterval(check);
			addBotoes_BB_CEF();
			incluirBotoesInvisiveis();
		}
	}, 100);
	
	function addBotoes_BB_CEF() {
		let el = document.querySelector('button[mattooltip="Adicionar outros destinatários"]');
		//os botões serão inseridos apenas quando o usuário colocar o mouse por cima do "Adicionar outros destinatários"
		el.addEventListener('mouseover', function(event) {
			if (!document.getElementById('maisPje_barra_bt_BB_CEF')) {
				//só inclui a opção se o tipo de expediente for Alvará ou Ofício
				if (!querySelectorByText('mat-select', 'Alvará') && !querySelectorByText('mat-select', 'Ofício') && !querySelectorByText('mat-select', 'Requisição')  && !querySelectorByText('mat-select', 'Mandado')) {
					return;
				}
				
				//DESCRIÇÃO: REGRA DO TOOLTIP
				if (!document.getElementById('maisPje_tooltip_direita2')) {
					tooltip('direita2');
				}
				
				let barra_atalhos = document.createElement("div");
				barra_atalhos.id = "maisPje_barra_bt_BB_CEF";
				barra_atalhos.style = "z-index: 100; width: 40px; height: auto; position: absolute; background-color: #fff; text-align: center; border-radius: 3px; display: flex; flex-direction: column-reverse; align-items: end;";
				barra_atalhos.onmouseleave = function (e) {
					barra_atalhos.className = "maisPje-fade-out";
					setTimeout(function(){				
						document.getElementById('maisPje_barra_bt_BB_CEF').remove();
					}, 250);
				};
				
				if (querySelectorByText('mat-select', 'Alvará')) {
					let botaoBB = document.createElement("button");
					botaoBB.id = "maisPje_bt_BB";
					botaoBB.textContent = "BB";
					botaoBB.setAttribute('maisPje-tooltip-direita2','Banco do Brasil');
					botaoBB.style = "cursor: pointer; position: relative; top: 20%; width: 100%; padding: 5px; margin: 5px; height: 35px; z-index: 1;";
					botaoBB.onclick = function () {acao_botao('bb','0')};
					barra_atalhos.appendChild(botaoBB);
					
					let botaoCEF = document.createElement("button");
					botaoCEF.id = "maisPje_bt_CEF";
					botaoCEF.textContent = "CEF";
					botaoCEF.setAttribute('maisPje-tooltip-direita2','Caixa Econômica Federal');
					botaoCEF.style = "cursor: pointer; position: relative; top: 20%; width: 100%; padding: 5px; margin: 5px; height: 35px; z-index: 1;";
					botaoCEF.onclick = function () {acao_botao('cef','0')};
					barra_atalhos.appendChild(botaoCEF);
				}
				
				if (querySelectorByText('mat-select', 'Ofício')) {
					let botaoBB = document.createElement("button");
					botaoBB.id = "maisPje_bt_BB";
					botaoBB.textContent = "BB";
					botaoBB.setAttribute('maisPje-tooltip-direita2','Banco do Brasil');
					botaoBB.style = "cursor: pointer; position: relative; top: 20%; width: 100%; padding: 5px; margin: 5px; height: 35px; z-index: 1;";
					botaoBB.onclick = function () {acao_botao('bb','0')};
					barra_atalhos.appendChild(botaoBB);
					
					let botaoCEF = document.createElement("button");
					botaoCEF.id = "maisPje_bt_CEF";
					botaoCEF.textContent = "CEF";
					botaoCEF.setAttribute('maisPje-tooltip-direita2','Caixa Econômica Federal');
					botaoCEF.style = "cursor: pointer; position: relative; top: 20%; width: 100%; padding: 5px; margin: 5px; height: 35px; z-index: 1;";
					botaoCEF.onclick = function () {acao_botao('cef','0')};
					barra_atalhos.appendChild(botaoCEF);
					
					let botaoMTE = document.createElement("button");
					botaoMTE.id = "maisPje_bt_MTE";
					botaoMTE.textContent = "MTE";
					botaoMTE.setAttribute('maisPje-tooltip-direita2','Ministério do Trabalho e Emprego');
					botaoMTE.style = "cursor: pointer; position: relative; top: 20%; width: 100%; padding: 5px; margin: 5px; height: 35px; z-index: 1;";
					botaoMTE.onclick = function () {acao_botao('mte','0')};
					barra_atalhos.appendChild(botaoMTE);
				}
				
				let num_trt = preferencias.trt.substring(preferencias.trt.search(".trt")+4,preferencias.trt.search(".jus.br"));
				if (querySelectorByText('mat-select', 'Requisição')) {
					let botaoTRT = document.createElement("button");
					botaoTRT.id = "maisPje_bt_TRT" + num_trt;
					botaoTRT.textContent = "TRT" + num_trt;
					botaoTRT.setAttribute('maisPje-tooltip-direita2','Tribunal Regional do Trabalho da ' + num_trt + '');
					botaoTRT.style = "cursor: pointer; position: relative; top: 20%; width: 100%; padding: 5px; margin: 5px; height: 35px; z-index: 1; font-size: 10px;";
					botaoTRT.onclick = function () {acao_botao('trt', num_trt)};
					barra_atalhos.appendChild(botaoTRT);
				}
				
				if (num_trt == "2" || num_trt == "12") {
					if (querySelectorByText('mat-select', 'Mandado')) {
						let botaoTRT = document.createElement("button");
						botaoTRT.id = "maisPje_bt_TRT" + num_trt;
						botaoTRT.textContent = "TRT" + num_trt;
						botaoTRT.setAttribute('maisPje-tooltip-direita2','Tribunal Regional do Trabalho da ' + num_trt + '');
						botaoTRT.style = "cursor: pointer; position: relative; top: 20%; width: 100%; padding: 5px; margin: 5px; height: 35px; z-index: 1; font-size: 10px;";
						botaoTRT.onclick = function () {acao_botao('trt', num_trt)};
						barra_atalhos.appendChild(botaoTRT);
					}
				}
				
				el.appendChild(barra_atalhos);
			}
		});
	}

	async function incluirBotoesInvisiveis() {
		if (!document.querySelector('#maisPje_bt_invisivel_outrosDestinatarios_TRT')) {
			let botao0 = document.createElement("button");
			botao0.id = "maisPje_bt_invisivel_outrosDestinatarios_TRT";
			botao0.textContent = "maisPje_bt_invisivel_outrosDestinatarios_TRT";		
			botao0.onclick = function () {
				document.querySelector('button[mattooltip="Adicionar outros destinatários"]').click();
				acao_botao('trt', preferencias.num_trt)
			};
			// botao0.style.visibility = 'hidden';
			document.body.appendChild(botao0);
		}
		
		if (!document.querySelector('#maisPje_bt_invisivel_outrosDestinatarios_TRT_Vara')) {
			let botao1 = document.createElement("button");
			botao1.id = "maisPje_bt_invisivel_outrosDestinatarios_TRT_Vara";
			botao1.textContent = "maisPje_bt_invisivel_outrosDestinatarios_TRT_Vara";		
			botao1.onclick = function () {
				
				let nm = this.getAttribute('maisPjeNomeDestinatario');
				console.log(nm);
				
				document.querySelector('button[mattooltip="Adicionar outros destinatários"]').click();
				acao_botao('vara',nm);
			};
			// botao1.style.visibility = 'hidden';
			document.body.appendChild(botao1);
		}
	}
	
	
	function acao_botao(banco, num_trt) {
		fundo(true);
		let cnpj = "";
		if (banco.includes('bb')) { //Banco do Brasil
			cnpj = "00.000.000/0001-91";
			acao1();
		} else if (banco.includes('cef')) { // Caixa Economica Federal
			cnpj = "00.360.305/0001-04";
			acao1();
		} else if (banco.includes('mte')) { // Ministério do Trabalho e Emprego
			cnpj = "37.115.367/0001-60";
			acao1();
		} else if (banco.includes('trt')) { // TRIBUNAL DO TRABALHO
			console.log(num_trt);
			switch(num_trt) {
				case '1':
					cnpj = "02.578.421/0001-20";
					acao1();
					break;
				case '2':
					cnpj = "03.241.738/0001-39";
					acao1();
					break;
				case '3':
					cnpj = "01.298.583/0001-41";
					acao1();
					break;
				case '4':
					cnpj = "02.520.619/0001-52";
					acao1();
					break;
				case '5':
					cnpj = "02.839.639/0001-90";
					acao1();
					break;
				case '6':
					cnpj = "02.566.224/0001-90";
					acao1();
					break;
				case '7':
					cnpj = "03.235.270/0001-70";
					acao1();
					break;
				case '8':
					cnpj = "01.547.343/0001-33";
					acao1();
					break;
				case '9':
					cnpj = "03.141.166/0001-16";
					acao1();
					break;
				case '10':
					cnpj = "02.011.574/0001-90";
					acao1();
					break;
				case '11':
					cnpj = "01.671.187/0001-18";
					acao1();
					break;
				case '12':
					cnpj = "02.482.005/0001-23";
					acao1();
					break;
				case '13':
					cnpj = "02.658.544/0001-70";
					acao1();
					break;
				case '14':
					cnpj = "03.326.815/0001-53";
					acao1();
					break;
				case '15':
					cnpj = "03.773.524/0001-03 ";
					acao1();
					break;
				case '16':
					cnpj = "23.608.631/0001-93";
					acao1();
					break;
				case '17':
					cnpj = "02.488.507/0001-61";
					acao1();
					break;
				case '18':
					cnpj = "02.395.868/0001-63";
					acao1();
					break;
				case '19':
					cnpj = "35.734.318/0001-80"; //cnpj não cadastrado
					acao1();
					break;
				case '20':
					cnpj = "01.445.033/0001-08"; //cnpj não cadastrado
					acao1();
					break;
				case '21':
					cnpj = "02.544.593/0001-82";
					acao1();
					break;
				case '22':
					cnpj = "03.458.141/0001-40"; //cnpj não cadastrado
					acao1();
					break;
				case '23':
					cnpj = "37.115.425/0001-56";
					acao1();
					break;
				case '24':
					cnpj = "37.115.409/0001-63";
					acao1();
					break;
				default:
					criarCaixaDeAlerta("ERRO","Tribunal não encontrado.");
					fundo(false);
					return;
			}
		} else if (banco.includes('vara')) { // TRIBUNAL DO TRABALHO
			acao9(num_trt);
		} else {
			return;
		}
		
		function acao1() {
			console.log("acao1()");
			let check = setInterval(function() {
				if (document.getElementById('tipoCPJ')) {
					clearInterval(check);
					document.getElementById('tipoCPJ').firstElementChild.click();
					acao2();
				}
			}, 100);
		}
		
		function acao2() {
			console.log("acao2()");
			let check = setInterval(function() {
				if (document.getElementById('cnpj')) {
					clearInterval(check);
					let input = document.getElementById('cnpj');
					input.focus();
					input.value = cnpj;
					//DESCRIÇÃO: Aciona a busca de elementos
					triggerEvent(input, 'input');
					triggerEvent(input, 'keyup');
					acao3();
				}
			}, 100);
		}
		
		function acao3() {
			console.log("acao3()");
			let bt_consulta = document.querySelector('button[aria-label="Consultar"]');
			bt_consulta.click();
			acao4();
		}
		
		function acao4() {
			console.log("acao4()");
			let check = setInterval(function() {
				if (document.querySelector('button[aria-label="Adicionar destinatário"]')) {
					clearInterval(check);
					document.querySelector('button[aria-label="Adicionar destinatário"]').click();
					acao5();
				}
			}, 100);
		}
		
		function acao5() {
			console.log("acao5()");
			let check = setInterval(function() {
				if (querySelectorByText('simple-snack-bar','Adicionado com sucesso.')) {
					clearInterval(check);
					document.querySelector('pje-pec-dialogo-outros-destinatarios a[mattooltip="Fechar"]').click();
					fundo(false);
					let num_trt = preferencias.trt.substring(preferencias.trt.search(".trt")+4,preferencias.trt.search(".jus.br"));
					if (num_trt == "2") {
						acao6();
					}
				}
			}, 100);
		}
		
		function acao6() {
			console.log("acao6()");
			let check = setInterval(function() {
				if (document.querySelector('button[aria-label="Alterar endereço"]')) {
					clearInterval(check);
					document.querySelector('button[aria-label="Alterar endereço"]').click();
					acao7();
				}
			}, 100);
		}
		
		function acao7() {
			console.log("acao7()");
			let ancora;
			let check = setInterval(function() {
				ancora = document.querySelectorAll('table[name="Endereços do destinatário no sistema"] tr:not(.tr-th-class)')
				console.log(ancora.length)
				if (ancora.length > 0) {
					clearInterval(check);
					let botao = [...ancora].filter(linha => linha.innerText.includes('01302-906'))
					botao[0].querySelector('button[aria-label="Selecionar endereço"]').click();
					acao8();
				}
			}, 100);
		}
		
		function acao8() {
			console.log("acao8()");
			let check = setInterval(function() {
				if (document.querySelector('table[name="Endereço cadastrado no expediente"]')) {
					clearInterval(check);
					document.querySelector('a[mattooltip="Fechar"]').click();
				}
			}, 100);
		}

		async function acao9(nome) {
			console.log("acao9()");
			await clicarBotao(document.getElementById('tipoAUTORIDADE').firstElementChild);
			// await sleep(500);
			await preencherInput('input[aria-label="Autoridade"]',nome.substring(0,3));
			// await sleep(500);
			await preencherInput('input[aria-label="Autoridade"]',nome);
			// await sleep(500);
			await clicarBotao('div[class="cdk-overlay-pane"] mat-option');
			// await sleep(500);
			await clicarBotao('button[aria-label="Acrescentar"]');
			// await sleep(500);
			await clicarBotao('a[mattooltip="Fechar"]');			
		}
	}
}

//FUNÇÃO RESPONSÁVEL POR PESQUISAR PERITOS/LEILOEIROS DE ACORDO COM A ESPECIALIDADE
async function consultaPeritos(nome, especialidade) {
	console.log(especialidade);
	let url;
	if (!especialidade) {
		url = 'https://' + preferencias.trt + '/pje-comum-api/api/peritos?parametroPesquisa=' + nome + '&somenteAtivos=true'
	} else {
		url = 'https://' + preferencias.trt + '/pje-comum-api/api/peritos?parametroPesquisa=' + nome + '&idEspecialidade=' + especialidade + '&somenteAtivos=true'
	}
	let resposta = await fetch(url);
	let dados = await resposta.json();
	return dados[0].documento;
}

//GARIMPO
async function garimpo(target) {
	// console.log("garimpo : " + target.id + " : " + target.TagName + " : " + target.className);
	
	if (target.parentElement.title.includes('Bloquear conta') || target.title.includes('Bloquear conta')) {
		let check = setInterval(function() {
			if (querySelectorByText('button','Confirmar')) {
				clearInterval(check);
				querySelectorByText('button','Confirmar').click();
			}
		}, 100);		
	}
	
	if (target.parentElement.title.includes('Desbloquear conta') || target.title.includes('Desbloquear conta')) {
		let check = setInterval(function() {
			if (querySelectorByText('button','Confirmar')) {
				clearInterval(check);
				querySelectorByText('button','Confirmar').click();
			}
		}, 100);
	}
	
	if (target.parentElement.title.includes('Associar processo') || target.title.includes('Associar processo')) {
		let check = setInterval(function() {
			if (querySelectorByText('button','Buscar Processos')) {
				clearInterval(check);
				let var0 = document.getElementById('formCadastro').children[0].innerText;
				let var1 = document.getElementById('formCadastro').children[1].innerText;
				let var2 = document.getElementById('formCadastro').children[2].innerText;
				// console.log(var1);
				var1 = var1.split('(Doc');
				// console.log(var1[0]);
				let nomeautor = var1[0].trim().substring(12);
				// console.log(nomeautor);
				let gigsURL = 'https://' + preferencias.trt + '/' + preferencias.grau_usuario + '/Processo/ConsultaProcesso/listView.seam?nomeautor=' + nomeautor + '&garimpo';
				
				browser.runtime.sendMessage({tipo: 'criarJanela', url: gigsURL, posx: 10, posy: 100, width: 1200, height: 400});
				
				querySelectorByText('button','Buscar Processos').click();
				setTimeout(function() {
					let ancora = querySelectorByText('H4', 'Busca de processos').parentElement;
					let span0 = document.createElement('span');
					span0.textContent = var0;
					let span1 = document.createElement('span');
					span1.textContent = var1;
					let span2 = document.createElement('span');
					span2.textContent = var2;
					span0.appendChild(document.createElement('br'));
					span1.appendChild(document.createElement('br'));
					span2.appendChild(document.createElement('br'));
					ancora.appendChild(span0);
					ancora.appendChild(span1);
					ancora.appendChild(span2);
				}, 1000);
			}
		}, 1000);
	}
	
	let ancora = await esperarElemento('div[id="tabelaContas"] div[class*="ui-grid-render-container-body"]');
	
	if (ancora.hasAttribute('maisPJe_MO')) { return }
	
	await ligarMO(ancora);
	
	async function ligarMO(alvo) {
		return new Promise(async resolve => {
			// console.log('ligarMO')
			ancora.setAttribute('maisPJe_MO','true');
			let observer_cabecalho = new MutationObserver(function(mutationsDocumento) {
				mutationsDocumento.forEach(function(mutation) {
					if (!mutation.addedNodes[0]) { return }
					if (!mutation.addedNodes[0].tagName) { return }
					// console.log("***[ADD] tagName(" + mutation.addedNodes[0].tagName + ") role(" + mutation.addedNodes[0].getAttribute('role') + ")");					
					if (mutation.addedNodes[0].tagName == "DIV" && mutation.addedNodes[0].getAttribute('role') == "gridcell") { //nova celula
						if (new RegExp('\\d{7}-\\d{2}\\.\\d{4}\\.\\d{1,2}\\.\\d{1,2}\\.\\d{4}','g').test(mutation.addedNodes[0].innerText)) {//verificar se a celula é um numero de processo
							inserirbotao(mutation.addedNodes[0], mutation.addedNodes[0].innerText.match(new RegExp('\\d{7}-\\d{2}\\.\\d{4}\\.\\d{1,2}\\.\\d{1,2}\\.\\d{4}','g')).join());
						}
					}
				});
			});
			let configDocumento = { childList: true, subtree:true }
			observer_cabecalho.observe(alvo, configDocumento);
		});
	}
	
	function inserirbotao(elemento, processo) {
		//limpa o conteudo
		// elemento.innerText = "";
		//CRIA BOTÃO CONSULTA RAPIDA DE PROCESSOS
		let atalho = document.createElement("button");
		atalho.id = "extensaoPje_garimpo_atalhoConsultaPJe";
		atalho.className = "btn btn-success btn-xs ng-scope";
		atalho.style = 'background-color: rgba(0, 0, 0, 0); border-color: rgba(0, 0, 0, 0); font-size: 16px; color: black; margin: 0px; padding: 0px;';		
		atalho.onmouseenter = function () {atalho.style.color  = 'orangered'};
		atalho.onmouseleave = function () {atalho.style.color  = 'black'};
		atalho.onclick = function () { consultaRapidaPJE(processo) };
		atalho.title = 'MaisPje: Consultar Processo no PJe';
		
		let atalho_span = document.createElement("span");
		atalho_span.className = "glyphicon glyphicon-search";
		
		atalho.appendChild(atalho_span);
		elemento.appendChild(atalho);
		
		//CRIA BOTÃO REGISTRO NO GIGS
		let btRGIGS = document.createElement("button");
		btRGIGS.id = "extensaoPje_garimpo_registrarGIGS";
		btRGIGS.className = "btn btn-success btn-xs ng-scope";
		btRGIGS.style = 'background-color: rgba(0, 0, 0, 0); border-color: rgba(0, 0, 0, 0); font-size: 16px; color: black; margin: 0px; padding: 0px;';
		btRGIGS.onmouseenter = function () {btRGIGS.style.color  = 'orangered'};
		btRGIGS.onmouseleave = function () {btRGIGS.style.color  = 'black'};
		btRGIGS.onclick = function () {
			let linha = elemento.parentElement;
			let banco = linha.children[0].innerText;
			let conta = linha.children[1].innerText;
			let saldo = linha.children[7].innerText;
			
			let isCheckBoxGarimpoMarcado = document.querySelector('input[ng-model="paginacao.recursais"]').checked;
			console.log('isCheckBoxGarimpoMarcado: ' + isCheckBoxGarimpoMarcado)
			let obs = (isCheckBoxGarimpoMarcado) ? "(Garimpo) Depósito Recursal - " + banco + " : " + conta + " : " + saldo : "(Garimpo) Alvará - zerar a conta (" + banco + " : " + conta + " : " + saldo + ")";
			
			let var1 = browser.storage.local.set({'tempBt': ['AutoGigs',{"id":999,"nm_botao":"garimpo_inclusao_automatica","tipo":"preparo","tipo_atividade":"Calculista","prazo":"","responsavel":"","responsavel_processo":"","observacao":obs,"salvar":"Sim","cor":"#008b8b","vinculo":["Fechar Pagina|Fechar Pagina","Nenhum"],"visibilidade":"sim"}]});
			Promise.all([var1]).then(values => {
				linha.querySelector('button[title="Bloquear conta para edição"]').click();
				criarCaixaDeAlerta("Atenção","Para lançar a Atividade no GIGS o processo deverá estar aberto em uma janela ou aba.",3)
			});
			
		};
		btRGIGS.title = 'Se assegure do processo estar aberto';
		
		let btRGIGS_span = document.createElement("span");
		btRGIGS_span.className = "glyphicon glyphicon-tag";
		
		btRGIGS.appendChild(btRGIGS_span);
		elemento.appendChild(btRGIGS);
	}
}

//FUNÇÃO PARA BAIXAR TODOS OS DOCUMENTOS DO PROCESSO INDIVIDUALMENTE, POR DOCUMENTO
async function baixarTodosDoctosIndividualmente() {	
	console.log("MaisPJe: consultar API");
	let ancora = await esperarElemento('ul[class*="pje-timeline"]');
	let chkboxes_selecionados = ancora.querySelectorAll('mat-checkbox[class*="mat-checkbox-checked"]');
	let idProcesso = document.location.href.substring(document.location.href.search("/processo/")+10, document.location.href.search("/detalhe"));
	let processoNumero = document.querySelector('span[class*="texto-numero-processo"]').innerText.match(new RegExp('\\d{7}-\\d{2}\\.\\d{4}\\.\\d{1,2}\\.\\d{1,2}\\.\\d{4}','g')).join();
	let listaDocumentos = [];
	console.log(chkboxes_selecionados + " : " + chkboxes_selecionados.length);
	//apenas os selecionados
	if (chkboxes_selecionados.length > 0) {
		for (i = 0; i <= chkboxes_selecionados.length-1; i++) {
			let el_titulo, el_id;
			if (chkboxes_selecionados[i].parentElement.className.includes('tl-botao')) { //é anexo
				el_titulo = chkboxes_selecionados[i].parentElement.nextSibling.getAttribute('aria-label');
				el_titulo = el_titulo.substring(el_titulo.indexOf(' (') + 2, el_titulo.indexOf(') - '));
				el_id = chkboxes_selecionados[i].parentElement.nextSibling.nextSibling.getAttribute('href');
				el_id = el_id.substring(el_id.indexOf('/documento/') + 11, el_id.indexOf('/conteudo'));
				console.log("**************" + el_id)
			} else {
				el_titulo = chkboxes_selecionados[i].parentElement.lastElementChild.getAttribute('aria-label');
				el_titulo = el_titulo.substring(el_titulo.indexOf('Título: (') + 9, el_titulo.indexOf(') - Id'));
				el_id = chkboxes_selecionados[i].parentElement.lastElementChild.getAttribute('href');
				el_id = el_id.substring(el_id.indexOf('/documento/') + 11, el_id.indexOf('/conteudo'));
			}
			listaDocumentos.push([el_titulo, el_id]);
		}
		
	} else {
		let url = 'https://' + preferencias.trt + '/pje-comum-api/api/processos/id/' + idProcesso + '/timeline?somenteDocumentosAssinados=false&buscarMovimentos=false&buscarDocumentos=true'; 
		let resposta = await fetch(url);
		let dados = await resposta.json();
		for (i = 0; i <= dados.length-1; i++) {
			let documento = dados[i];
			listaDocumentos.push([documento.titulo, documento.id]);
			if (documento.anexos) {
				for (j = 0; j <= documento.anexos.length-1; j++) {
					let anexo = documento.anexos[j];
					console.log("     |___" + anexo.id);
					listaDocumentos.push([anexo.titulo, anexo.id]);
				}
			}
		}
		console.log("MaisPJe: consulta API finalizada");
	}
	
	let var1 = window.confirm("MaisPJe: Foram encontrados " + listaDocumentos.length + " documentos. Deseja baixá-los de forma individual?");
	if (var1) {
		let altura = window.innerHeight || document.documentElement.clientHeight || document.body.clientHeight;
		fundo(true, "Baixando documentos", (altura - 200));
		let div = document.createElement("div");
		div.id = "maisPje_baixarTodosDoctos_div";
		div.style = "position: fixed; bottom: 0; display: block; z-index: 1000; width: 100%; height: 200px;";
		document.body.appendChild(div);
		let textoarea = document.createElement("textarea");
		textoarea.id = "maisPje_baixarTodosDoctos_textarea";
		textoarea.style = "width: 100%;height: 100%;"
		textoarea.textContent = 'Baixando documentos (Total: ' + listaDocumentos.length +')';
		div.appendChild(textoarea);
		let botao = document.createElement("button");
		botao.id = "maisPje_baixarTodosDoctos_bt_fechar";
		botao.style = "position: absolute; right: 0px;"
		botao.textContent = "Fechar"
		botao.onclick = function () {div.remove();fundo(false);};	
		div.appendChild(botao);
		baixarDocumentos();
	}
	
	async function baixarDocumentos() {
		for (i = 0; i <= listaDocumentos.length-1; i++) {
			let url = 'https://' + preferencias.trt + '/pje-comum-api/api/processos/id/' + idProcesso + '/documentos/id/' + listaDocumentos[i][1] + '/conteudo?incluirCapa=false&incluirAssinatura=true';
			
			let el = document.getElementById('maisPje_baixarTodosDoctos_textarea');
			el.textContent = el.textContent + "\n" + "Documento " + (i+1) + ": " + listaDocumentos[i][0];
			el.scrollTop = el.scrollHeight;
			
			//comando para baixar os documentos
			await fetch(url)
				.then(async res => res.blob())
				.then(async blob => {
					let blobURL = window.URL.createObjectURL(blob);
					let linkTemporario = document.createElement('a');
					linkTemporario.style.display = 'none';
					linkTemporario.href = blobURL;
					linkTemporario.setAttribute('download', "[" + processoNumero + "] " + (i+1) + ". " + listaDocumentos[i][0] + '.pdf');
					if (typeof linkTemporario.download === 'undefined') {
						linkTemporario.setAttribute('target', '_blank');
					}
					linkTemporario.click();
					await sleep(1000);
					// setTimeout(() => {
						// For Firefox it is necessary to delay revoking the ObjectURL
						window.URL.revokeObjectURL(blobURL);
					// }, 200);
					
					if (i == listaDocumentos.length-1) {
						el.textContent = el.textContent + "\nFim!";
						el.scrollTop = el.scrollHeight;
						listaDocumentos = [];
						fundo(false);
						document.getElementById('maisPje_baixarTodosDoctos_bt_fechar').click();
					}
				});
			
			await sleep(1000);
		}
	}
}

//FUNÇÃO PARA RECUPERAR A LISTA DE TODOS OS PROCESSOS LISTADOS NO RELATÓRIOS DE ATIVIDADES DE ACORDO COM O FILTRO
async function recuperarListaRelatorioGigs() {
	mapTratarDados = {
		"Atividades": (result) => tratarDadosAtividades(result),
		"Comentários": (result) => tratarDadosComentarios(result),
		"Processos do Gabinete": (result) => tratarProcessosDoGabinete(result),
	}
	
    let api = captureLastNetworkRequest();
    let regPagina = /pagina=\d+/;
    let regTamPagina = /tamanhoPagina=\d+/;
    api = api.replace(regPagina, "pagina=1")
             .replace(regTamPagina, "tamanhoPagina=" + getTotalRegistros()); //TODO: capturar total na listagem.
    return fetch(api,
        {
            headers: {
                'Accept': '*/*',
                'Content-Type': 'application/json'
            },
            credentials: "include",
            method: "GET",
        })
        .then(function (response) {
			fundo(true);
            return response.json();
        })
        .then(data=>{
            let titulo = getTitulo();
            let result = data.resultado;
			// se nao tiver uma funcao especifica, envia todos os dados.
            result = mapTratarDados[titulo] && mapTratarDados[titulo](result) || result;
			console.log(result)
			return createTable(result, titulo);
        })
        .then(function (html) {
			fundo(false);
            return prepararEAbrirArquivo("GIGS - " + getTitulo() + " - Total: " + getTotalRegistros(), html.outerHTML);
        })
        .catch(function (err) {
			fundo(false);
			criarCaixaDeAlerta("ERRO","Algo deu errado ao gerar a lista.")
            console.warn('Something went wrong.', err);
        });
		
	
	function captureLastNetworkRequest(e) {
		let capture_network_request = [];
		let capture_resource = performance.getEntriesByType("resource");
		for (let i = 0; i < capture_resource.length; i++) {
			if (
				capture_resource[i].name.indexOf('/relatorioatividades/?') > -1 ||
				capture_resource[i].name.indexOf('/relatorioatividades?') > -1 ||
				capture_resource[i].name.indexOf('/relatoriocomentarios/?') > -1 ||
				capture_resource[i].name.indexOf('/relatoriocomentarios?') > -1 ||
				capture_resource[i].name.indexOf('/pje-gigs-api/api/processo/relatorio?') > -1 ||
				capture_resource[i].name.indexOf('/pje-gigs-api/api/tiposatividades/tiposunidaderegionalcomtotalizador?') > -1
			) {
				capture_network_request.push(capture_resource[i].name);
			}
		}
		return capture_network_request[capture_network_request.length - 1];
	}
	
	function getTotalRegistros() {
		let textoTotal = document.querySelector('.total-registros').textContent;
		let regTotal = /.* de /;
		let total = textoTotal.trim().replace(regTotal, '');
		return total;
	}
	
	function getTitulo() {
		return document.querySelector('.titulo-relatorio').textContent;
	}
	
	function tratarDadosAtividades(result) {
		return result.map(({processo, dataPrazo, tipoAtividade, dataCriacao,
							   nomeUsuarioDestinatario, observacao, statusAtividade,
								 ...rest}) => {
			return {
				"Classe": processo.classeJudicial?.descricao,
				"Processo": processo.numero,
				"Fase": processo.faseProcessual,
				"Tarefa": processo.nomeTarefa,
				"Data Atividade": simpleDate(dataPrazo ?? dataCriacao),
				"Tipo": tipoAtividade.descricao,
				"Descrição": observacao ?? '',
				"Responsável": nomeUsuarioDestinatario,
				"Status": statusAtividade,
				}
		});

	}

	function tratarDadosComentarios( result ) {
		return result.map(({processo, usuarioCriacao, dataCriacao, descricao,
							   ...rest}) => {
			let colunaProcesso = processo.classeJudicial?.descricao + ' ' + processo.numero;
			// console.log(colunaProcesso + " , " + descricao + " , " + simpleDate(dataCriacao) + " , " + usuarioCriacao);
			return { "Processo": colunaProcesso,
				"Descrição": descricao,
				"Data de Criação": simpleDate(dataCriacao),
				"Autor(a)": usuarioCriacao,
				 }
		});
	}
	
	function tratarProcessosDoGabinete(result) {
		return result.map(({processo}) => {
			
			//,numero, classeJudicial, nomeTarefa, dataInicioPrazo, dataTerminoPrazo, nomeRelator, nomeResponsavel,
			
			let colunaProcesso = processo.classeJudicial?.descricao + ' ' + processo.numero;
			console.log(colunaProcesso + " , " + simpleDate(processo.dataInicioPrazo) + " , " + simpleDate(processo.dataTerminoPrazo) + " , " + processo.nomeRelator + " , " + processo.nomeResponsavel);
			return { 
				"Processo": colunaProcesso,
				"Tarefa": processo.nomeTarefa,
				"Início do Prazo": simpleDate(processo.dataInicioPrazo),
				"Fim do Prazo": simpleDate(processo.dataTerminoPrazo),
				"Relator": processo.nomeRelator ?? '',
				"Responsável": processo.nomeResponsavel ?? ''
				}
		});
	}
	
	function simpleDate(inputFormat) {
		let d = new Date(inputFormat);
		return d.toISOString().match(/^[0-9]{4}\-[0-9]{2}\-[0-9]{2}/)[0].split('-').reverse().join('/');
	}
	
	function convertDate(inputFormat) {
		let d = new Date(inputFormat)
		return [d.getFullYear(), d.getMonth(), d.getDate(), d.getHours(), d.getMinutes(), d.getSeconds()].join('')
	}
	
	function createTable(children, titulo) {
		let tabela = document.createElement('table');
		
		//cria o cabeçalho
		let chaves_cabecalho = Object.keys(children[0]);
		criarCabecalho(titulo);
		//cria o tbody
		let tbody = tabela.createTBody();
		//insere as linhas no tbody
		for(let i = 0; i < children.length; i++) {
			let child = children[i];
			let linha = tbody.insertRow();			
			chaves_cabecalho.forEach(function(k) {
				linha.insertCell().appendChild(document.createTextNode(child[k] ?? ''));
			})
		}
		return tabela;
		
		function criarCabecalho(titulo) {
			let cabecalho = tabela.createTHead();
			let linha_cabecalho = cabecalho.insertRow();
			for( let i = 0; i < chaves_cabecalho.length; i++ ) {
				let celula_cabecalho = document.createElement('th');
				celula_cabecalho.style.width = "auto";//definir a largura das colunas
				celula_cabecalho.appendChild(document.createTextNode(chaves_cabecalho[i]));
				linha_cabecalho.appendChild(celula_cabecalho);				
			}
		}
	}
	
	function prepararEAbrirArquivo(titulo, tabela) {
		let arquivoFinal = "";
		let comecoArquivo =
			`<html lang='pt-BR'><head><meta charset="utf-8"><style>img { display: none;}
				body {
				font-family: Open Sans,Arial,Verdana,sans-serif;
				}
				
				table {
				border-collapse: collapse;
				border-spacing: 0;
				width: 100%;
				border: 1px solid #ddd;
				font-size: 13px;
			}
				th {
				background-color: #f0f0f0;
				padding: 0 10px;
				vertical-align: middle;
				text-align: left;
				border-bottom: 0 solid;
				border-color: #d7d7d7;
				min-width: -moz-fit-content;
				}

				td {
				padding: 0 10px;
				border-top: 1px solid rgba(0,0,0,.12);
				text-align: left;
				vertical-align: middle;
				white-space: nowrap;
			}

				tr:nth-child(even) {
				background-color: #f0f0f0;
			}
				.titulo {
				font-size: 24px;
				color: #373a3c;
				text-align: center;
			}
			.subtitulo {
				font-size: 14px;
				color: #888;
				text-align: center;
			}
			</style>` + "<title> Relatório " + titulo + "</title></head><body>";

		arquivoFinal += tabela + "</body></html>";
		arquivoFinal =
			comecoArquivo +
			"<span class='titulo'>Relatório " +
			titulo + " registros</span><br><br><span class='subtitulo'>" +
			"Gerado em: " +
			agora() +
			"</span><br><br>" +
			arquivoFinal;
		
		let novaJanela = URL.createObjectURL(
			new Blob([arquivoFinal], { type: "text/html" })
		);
		
		window.open(novaJanela, convertDate(new Date()) + " - Relatorio " + titulo + ".html");
	}
}

//FILTROS FAVORITOS
async function inserirBotaoGuardarFiltroFavorito() {
	return new Promise(async resolver => {
		let btInserirFiltro = await esperarElemento('button[id="maisPje_bt_principal_6"]', null, 100);
		if (!btInserirFiltro) {
			console.log('MaisPJe: inserir filtros favoritos')
			let ancora = await esperarElemento('button[aria-label="Limpar Filtro"]') ;
			
			if (!document.getElementById('maisPje_tooltip_abaixo4')) {
				tooltip('abaixo4');
			}
			
			let botao = document.createElement("button");
			botao.id = "maisPje_bt_principal_6";
			botao.classList.add("mat-focus-indicator", "mat-tooltip-trigger", "mat-icon-button", "mat-button-base");
			botao.setAttribute("maispje-tooltip-abaixo4", "maisPje: Guardar filtro favorito");
			botao.onclick = function () { guardarFiltrosFavoritos() };
			
			let botao_span = document.createElement("span");
			botao_span.classList.add("mat-button-wrapper");
			
			let botao_icone = document.createElement("i");
			botao_icone.setAttribute('aria-hidden','true'); //faz com que o NVDA ignore o elemento
			botao_icone.classList.add("mat-tooltip-trigger", "fas", "fa-plus-circle", "icone-clicavel");
			botao_icone.style.cssText += 'font-size: 20px; line-height: 44px; color: orangered;';
			
			botao_span.appendChild(botao_icone);						
			botao.appendChild(botao_span);
			
			if (ancora.hasAttribute('aria-label')) {
				ancora.parentElement.appendChild(botao);
			} else {
				ancora.insertAdjacentElement('afterbegin', botao);
			}
			resolver(true);
		} else { resolver(true) }		
	});
}

async function guardarFiltrosFavoritos() {
	let filtros_storage = [];
	
	browser.storage.local.get('filtros_Favoritos', function(result){
		if (result.filtros_Favoritos) {
			filtros_storage = result.filtros_Favoritos;
		} else {
			console.log("filtros_storage: vazio");
		}
	});
	
	let tabela = getTitulo();
	let camposFixos, camposDinamicos, qtde;
	let nome_filtro = prompt('Digite um nome para o filtro:\n','');	
	camposFixos = capturarCamposFixos(tabela);
	camposDinamicos = capturarCamposDinamicos(tabela);
	
	let elementoQtde = document.querySelectorAll('pje-data-table pje-paginador span[class*="mat-select-min-line"]')[1]
	qtde = elementoQtde.innerText
	filtros_storage.push({"tabela": tabela,"nome" : nome_filtro,"camposFixos": camposFixos,"camposDinamicos": camposDinamicos, "qtde": qtde});
	salvarFiltro();
	
	
	function salvarFiltro() {
		let var0 = browser.storage.local.set({'filtros_Favoritos': filtros_storage});
		Promise.all([var0]).then(values => {
			browser.runtime.sendMessage({tipo: 'criarAlerta', valor: 'Filtro ' + nome_filtro + ' salvo com sucesso!', icone: '6'});
			montarFiltrosFavoritos();
		});
	}
	
	function capturarCamposFixos(tabela) {
		let capture_network_request = [];
		let capture_resource = performance.getEntriesByType("resource");
		for (let i = 0; i < capture_resource.length; i++) {
			if (
				capture_resource[i].name.indexOf('/relatorioatividades/?') > -1 ||
				capture_resource[i].name.indexOf('/relatorioatividades?') > -1 ||
				capture_resource[i].name.indexOf('/relatoriocomentarios/?') > -1 ||
				capture_resource[i].name.indexOf('/relatoriocomentarios?') > -1 ||				
				capture_resource[i].name.indexOf('/pje-gigs-api/api/processo/relatorio?') > -1 ||
				capture_resource[i].name.indexOf('/pje-gigs-api/api/tiposatividades/tiposunidaderegionalcomtotalizador?') > -1 ||
				capture_resource[i].name.indexOf('/pje-comum-api/api/agrupamentotarefas/processos/todos') > -1
			) {
				capture_network_request.push(capture_resource[i].name);
			}
		}
		
		let api = capture_network_request[capture_network_request.length - 1];
		if (!api) { api = "nada" }
		
		switch (tabela) {
			case 'Painel_global':
				return { 
					"filtrarSegredoDeJustica": (document.querySelector('mat-chip[aria-label="FiltroSegredo de Justiça"]') ? true : false),
					"filtrarDocumentosNaoApreciados": (document.querySelector('mat-chip[aria-label="FiltroDocumentos Não Apreciados"]') ? true : false),
					"filtrarPrioridadeProcessual": (document.querySelector('mat-chip[aria-label="FiltroPrioridade Processual"]') ? true : false),
					"filtrarAssociados": (document.querySelector('mat-chip[aria-label="FiltroProcessos Associados"]') ? true : false),
					"filtrarAlertaProcessual": (document.querySelector('mat-chip[aria-label="FiltroAlerta Processual"]') ? true : false),
					"filtrarPrazosVencidos": (document.querySelector('mat-chip[aria-label="FiltroPrazos vencidos"]') ? true : false)
				}
				break;
			case 'Atividades':
				
				return { 
					"filtrarNoPrazo": api.includes("filtrarNoPrazo"),
					"filtrarVencidas": api.includes("filtrarVencidas"),
					"filtrarConcluidas": api.includes("filtrarConcluidas"),
					"filtrarAtividadesSemPrazo": api.includes("filtrarAtividadesSemPrazo"),
					"filtrarAtividadesSemPrazoConcluidas": api.includes("filtrarAtividadesSemPrazoConcluidas"),
					"filtrarSemDestinatario": api.includes("filtrarSemDestinatario"),
					"filtrarMinhasAtividades": api.includes("filtrarMinhasAtividades")
				}
				break;
			case 'Comentários':
				return { 
					"meusComentarios": api.includes("meusComentarios"),
					"comentariosArquivados": api.includes("comentariosArquivados")
				}
				break;
			case 'Processos do Gabinete':
				return { 
					"filtrarPorPrazo": api.includes("filtrarPorPrazo"),
					"filtrarAVencer": api.includes("filtrarAVencer"),
					"filtrarVencidos": api.includes("filtrarVencidos"),
					"filtrarProcessosSemResponsavel": api.includes("filtrarProcessosSemResponsavel"),
					"filtrarED": api.includes("filtrarED"),
					"filtrarSumarissimo": api.includes("filtrarSumarissimo")
				}
				break;
		}
	}
	
	function capturarCamposDinamicos(tabela) {
		let temp;
		switch (tabela) {
			case 'Painel_global':
				temp = document.querySelector('mat-select[aria-label*="Classe Judicial"]').innerText.trim();
				temp = temp.replace(new RegExp('Classe Judicial', 'g'), '');
				let fpglobal_classeJudicial = temp.split(',');
				
				temp = document.querySelector('mat-select[aria-label*="Chips"]').innerText.trim();
				temp = temp.replace(new RegExp('Chips', 'g'), '');
				let fpglobal_chips = temp.split(',');
				
				temp = document.querySelector('mat-select[aria-label*="Concluso para"]').innerText.trim();
				temp = temp.replace(new RegExp('Concluso para', 'g'), '');
				let fpglobal_conclusoPara = temp.split(',');
				
				temp = document.querySelector('mat-select[aria-label*="Tarefa do processo"]').innerText.trim();
				temp = temp.replace(new RegExp('Tarefa do processo', 'g'), '');
				let fpglobal_tarefaProcesso = temp.split(',');
				
				temp = document.querySelector('mat-select[aria-label*="Sub-caixa"]').innerText.trim();
				temp = temp.replace(new RegExp('Sub-caixa', 'g'), '');
				let fpglobal_subCaixa = temp.split(',');
				
				temp = document.querySelector('mat-select[aria-label*="Tipo de Atividade"]').innerText.trim();
				temp = temp.replace(new RegExp('Tipo de Atividade', 'g'), '');
				let fpglobal_tipoAtividade = temp.split(',');
				
				temp = document.querySelector('mat-select[aria-label*="Usuário Responsável"]').innerText.trim();
				temp = temp.replace(new RegExp('Usuário Responsável', 'g'), '');
				let fpglobal_usuarioResponsavel = temp.split(',');
				
				//somente primeiro grau
				let fpglobal_faseProcessual = [];
				if (preferencias.grau_usuario == "primeirograu") {
					temp = document.querySelector('mat-select[aria-label*="Fase processual"]').innerText.trim();
					temp = temp.replace(new RegExp('Fase processual', 'g'), '');
					fpglobal_faseProcessual = temp.split(',');
				}
				
				//somente segundo grau
				let fpglobal_relatorProcesso = [];
				let fpglobal_OJC = [];
				console.log('***************' + preferencias.grau_usuario)
				if (preferencias.grau_usuario == "segundograu") {
					temp = document.querySelector('mat-select[aria-label*="Filtro Relator do processo"]').innerText.trim();
					temp = temp.replace(new RegExp('Relator do Processo', 'g'), '');
					fpglobal_relatorProcesso = temp.split(',');
					
					temp = document.querySelector('mat-select[aria-label*="Filtro Órgãos Julgadores do OJC"]').innerText.trim();
					temp = temp.replace(new RegExp('Órgãos Julgadores do OJC', 'g'), '');
					fpglobal_OJC = temp.split(',');
				}
				
				let fpglobal_naTarefaDesde = document.querySelector('input[aria-label*="tarefa desde"]').value;
				
				let fpglobal_naTarefaate = document.querySelector('input[aria-label*="tarefa até"]').value;
				
				return {
					"fpglobal_classeJudicial": fpglobal_classeJudicial,
					"fpglobal_chips": fpglobal_chips,
					"fpglobal_conclusoPara": fpglobal_conclusoPara,
					"fpglobal_tarefaProcesso": fpglobal_tarefaProcesso,
					"fpglobal_subCaixa": fpglobal_subCaixa,
					"fpglobal_tipoAtividade": fpglobal_tipoAtividade,
					"fpglobal_usuarioResponsavel": fpglobal_usuarioResponsavel,
					"fpglobal_faseProcessual": fpglobal_faseProcessual,
					"fpglobal_relatorProcesso": fpglobal_relatorProcesso,
					"fpglobal_OJC": fpglobal_OJC,
					"fpglobal_naTarefaDesde": fpglobal_naTarefaDesde,
					"fpglobal_naTarefaate": fpglobal_naTarefaate,
				}
				break;
			case 'Atividades':
				temp = document.querySelector('mat-select[aria-label*="Classe Judicial"]').innerText.trim();
				temp = temp.replace(new RegExp('Classe Judicial', 'g'), '');
				let fa_classeJudicial = temp.split(',');
				
				let fa_data_de = document.querySelector('input[aria-label*="data de"]').value;
				
				let fa_data_ate = document.querySelector('input[aria-label*="data até"]').value;
				
				temp = document.querySelector('mat-select[aria-label*="Tipo da Atividade"]').innerText.trim();
				temp = temp.replace(new RegExp('Tipo da Atividade', 'g'), '');
				let fa_tipo = temp.split(',');
				
				let fa_descricao = document.querySelector('input[aria-label*="Descrição"]').value;
				
				temp = document.querySelector('mat-select[aria-label*="Responsáveis"]').innerText.trim();
				temp = temp.replace(new RegExp('Responsáveis', 'g'), '');
				let fa_responsaveis = temp.split(',');
				
				return {
					"fa_classeJudicial": fa_classeJudicial,
					"fa_data_de": fa_data_de,
					"fa_data_ate": fa_data_ate,
					"fa_tipo": fa_tipo,
					"fa_descricao": fa_descricao,
					"fa_responsaveis": fa_responsaveis,
				}
				break;
			case 'Comentários':
				temp = document.querySelector('mat-select[aria-label*="Classe Judicial"]').innerText.trim();
				temp = temp.replace(new RegExp('Classe Judicial', 'g'), '');
				let fc_classeJudicial = temp.split(',');
				
				let fc_descricao = document.querySelector('input[aria-label*="Descrição"]').value;
				
				let fc_data_de = document.querySelector('input[aria-label*="data de"]').value;
				
				let fc_data_ate = document.querySelector('input[aria-label*="data até"]').value;
				
				temp = document.querySelector('mat-select[aria-label*="Autores"]').innerText.trim();
				temp = temp.replace(new RegExp('Autores', 'g'), '');
				let fc_autores = temp.split(',');
				
				return {
					"fc_classeJudicial": fc_classeJudicial,
					"fc_descricao": fc_descricao,
					"fc_data_de": fc_data_de,
					"fc_data_ate": fc_data_ate,
					"fc_autores": fc_autores
				}
				break;
			case 'Processos do Gabinete':
				let fpg_inicio_data_de = document.querySelector('input[aria-label*="De (Início"]').value;
				
				let fpg_inicio_data_ate = document.querySelector('input[aria-label*="Até (Início"]').value;
				
				let fpg_fim_data_de = document.querySelector('input[aria-label*="De (Fim"]').value;
				
				let fpg_fim_data_ate = document.querySelector('input[aria-label*="Até (Fim"]').value;
				
				temp = document.querySelector('mat-select[aria-label*="Classe Judicial"]').innerText.trim();
				temp = temp.replace(new RegExp('Classe Judicial', 'g'), '');
				let fpg_classeJudicial = temp.split(',');
				
				temp = document.querySelector('mat-select[aria-label*="Filtro Relator. "]').innerText.trim();
				temp = temp.replace(new RegExp('Relator', 'g'), '');
				let fpg_relator = temp.split(',');
				
				temp = document.querySelector('mat-select[aria-label*="Filtro Responsáveis. "]').innerText.trim();
				temp = temp.replace(new RegExp('Responsáveis', 'g'), '');
				let fpg_responsavel = temp.split(',');
				
				return {
					"fpg_inicio_data_de": fpg_inicio_data_de,
					"fpg_inicio_data_ate": fpg_inicio_data_ate,
					"fpg_fim_data_de": fpg_fim_data_de,
					"fpg_fim_data_ate": fpg_fim_data_ate,
					"fpg_classeJudicial": fpg_classeJudicial,
					"fpg_relator": fpg_relator,
					"fpg_responsavel": fpg_responsavel
				}
				
				break;
		}
	}
	
	function getTitulo() {
		if (document.location.href.includes("/pjekz/painel/global/")) {
			return "Painel_global";
		} else {
			return document.querySelector('.titulo-relatorio').textContent;
		}
	}
}

async function montarFiltrosFavoritos() {
	//campos fixos são aqueles representados pelos ícones relógio, caneta, etc.. 
	//campos dinâmicos são aqueles representados pelos campos de formulário
	let filtros_storage = [];
	let tabela_atual = getTitulo();
	var observer, monitor;
	
	browser.storage.local.get('filtros_Favoritos', function(result){
		if (result.filtros_Favoritos) {
			
			//cria a estrutura para receber os botões caso seja o painel Global sem tabela
			if (!document.querySelector('span[class="cabecalho-icones"]')) {
				let ancora = document.querySelector('div[class="filtro"]');
				ancora = ancora.parentElement;
				let span = document.createElement('span');
				span.id = 'maisPje_span_filtros_favoritos';
				span.className = 'cabecalho-icones';
				span.style = 'margin-right: 20px;';
				span.setAttribute('role','toolbar');
				ancora.insertBefore(span, ancora.children[1]);
			}
			
			filtros_storage = result.filtros_Favoritos;
			filtros_storage.map(({tabela,nome,camposFixos,camposDinamicos,qtde}) => {
				if (tabela_atual == tabela) {
					montarBotao(tabela, nome, camposFixos, camposDinamicos,qtde);
				}
			});
		} else {
			console.log("filtros_storage: vazio");
		}
	});
	
	function getTitulo() {
		if (document.location.href.includes("/pjekz/painel/global")) {
			return "Painel_global";
		} else {
			return document.querySelector('.titulo-relatorio')?.textContent;
		}
	}
	
	function montarBotao(tabela, nome, camposFixos, camposDinamicos,qtde) {
		let ancora = document.querySelector('span[class="cabecalho-icones"]') || document.querySelector('span[id="maisPje_span_filtros_favoritos"]');
		
		if (!document.getElementById("maisPje_filtrofavorito_" + nome)) {
			//divisor
			// let divisor = document.createElement("span");
			// divisor.innerText = '|';
			// ancora.appendChild(divisor);
			
			//atalho
			let botao = document.createElement("button");
			botao.id = "maisPje_filtrofavorito_" + nome;
			botao.style = "margin: 0 5px 0 5px;";
			botao.onclick = function () {acao(tabela, camposFixos, camposDinamicos,qtde)};
			let botao_span = document.createElement("span");
			botao_span.innerText = nome;
			
			botao.appendChild(botao_span);
			ancora.appendChild(botao);
		}
	}
	
	async function acao(tabela, camposFixos, camposDinamicos,qtde='20') {
		fundo(true);
		
		let bt_exibirTodos = await esperarElemento('span','Exibir todos',200);
		if (bt_exibirTodos) { await clicarBotao(bt_exibirTodos) }
		
		await clicarBotao('button[aria-label="Limpar Filtro"]');
		await preencherCamposFixos(tabela, camposFixos);
		await preencherCamposDinamicos(tabela, camposDinamicos);
		
		if (qtde != '20') {
			await linhasPorPagina(qtde);
		}
		fundo(false);
	}
	
	async function preencherCamposFixos(tabela, camposFixos) {
		return new Promise(async resolver => {
			// console.log("maisPJe: preencherCamposFixos - " + camposFixos);
			if (tabela == 'Painel_global') {
				if (camposFixos.filtrarSegredoDeJustica) {
					await filtroClicarBotao('i[aria-label="Processos em Segredo de Justiça"]');
				}
				
				if (camposFixos.filtrarDocumentosNaoApreciados) {
					await filtroClicarBotao('i[aria-label="Processos com documento não apreciado"]');
				} 
				
				if (camposFixos.filtrarPrioridadeProcessual) {
					await filtroClicarBotao('i[aria-label="Processos com Prioridade Processual"]');
				} 
				
				if (camposFixos.filtrarAssociados) {
					await filtroClicarBotao('i[aria-label="Processos com Associação"]');
				} 
				
				if (camposFixos.filtrarAlertaProcessual) {
					await filtroClicarBotao('i[aria-label="Processos com Alerta"]');
				} 
				
				if (camposFixos.filtrarPrazosVencidos) {
					await filtroClicarBotao('i[aria-label="Processos com prazos vencidos"]');
				} 
				
			} else if (tabela == 'Atividades') {
				if (camposFixos.filtrarNoPrazo) {
					await filtroClicarBotao('i[aria-label="No Prazo"]');
				} 
				
				if (camposFixos.filtrarVencidas) {
					await filtroClicarBotao('i[aria-label="Prazos Vencidos"]');
				} 
				
				if (camposFixos.filtrarConcluidas) {
					await filtroClicarBotao('i[aria-label="Prazos Concluídos"]');
				} 
				
				if (camposFixos.filtrarAtividadesSemPrazo) {
					await filtroClicarBotao('i[aria-label="Atividades sem prazo"]');
				} 
				
				if (camposFixos.filtrarAtividadesSemPrazoConcluidas) {
					await filtroClicarBotao('i[aria-label="Atividades sem prazo concluídas"]');
				} 
				
				if (camposFixos.filtrarSemDestinatario) {
					await filtroClicarBotao('i[aria-label="Sem Responsável"]');
				} 
				
				if (camposFixos.filtrarMinhasAtividades) {
					await filtroClicarBotao('i[aria-label="Minhas Atividades"]');
				}
				
			} else if (tabela == 'Comentários') {
				if (camposFixos.meusComentarios) {
					await filtroClicarBotao('i[aria-label="Meus Comentários"]');
				} 
				
				if (camposFixos.comentariosArquivados) {
					await filtroClicarBotao('i[aria-label="Comentários Arquivados"]');
				}
				
			} else if (tabela == 'Processos do Gabinete') {
				if (camposFixos.filtrarPorPrazo) {
					await filtroClicarBotao('i[aria-label="No Prazo"]');
				} 
				
				if (camposFixos.filtrarAVencer) {
					await filtroClicarBotao('i[aria-label="A Vencer"]');
				} 
				
				if (camposFixos.filtrarVencidos) {
					await filtroClicarBotao('i[aria-label="Vencidos"]');
				} 
				
				if (camposFixos.filtrarProcessosSemResponsavel) {
					await filtroClicarBotao('i[aria-label="Sem Responsável"]');
				} 
				
				if (camposFixos.filtrarED) {
					await filtroClicarBotao('span[aria-label="ED"]');
				} 
				
				if (camposFixos.filtrarSumarissimo) {
					await filtroClicarBotao('span[aria-label="Sumaríssimo"]');
				}
				
			}
			resolver();
		});
	}
	
	async function preencherCamposDinamicos(tabela, camposDinamicos) {
		return new Promise(async resolver => {
			// console.log("maisPJe: preencherCamposDinamicos - " + camposDinamicos);
			if (tabela == 'Painel_global') {
				if (camposDinamicos.fpglobal_classeJudicial.toString() != "") {
					await escolherSelect('mat-select[aria-label*="Filtro Classe Judicial"]', camposDinamicos.fpglobal_classeJudicial);
				} 
				
				if (camposDinamicos.fpglobal_chips.toString() != "") {
					await escolherSelect('mat-select[aria-label*="Filtro Chips"]', camposDinamicos.fpglobal_chips);
				} 
				
				if (camposDinamicos.fpglobal_conclusoPara.toString() != "") {
					await escolherSelect('mat-select[aria-label*="Filtro Concluso para"]', camposDinamicos.fpglobal_conclusoPara);
				} 
				
				if (camposDinamicos.fpglobal_tarefaProcesso.toString() != "") {
					await escolherSelect('mat-select[aria-label*="Filtro Tarefa do processo"]', camposDinamicos.fpglobal_tarefaProcesso);
				} 
				
				if (camposDinamicos.fpglobal_subCaixa.toString() != "") {
					await escolherSelect('mat-select[aria-label*="Filtro Sub-caixa"]', camposDinamicos.fpglobal_subCaixa);
				} 
				
				if (camposDinamicos.fpglobal_tipoAtividade.toString() != "") {
					await escolherSelect('mat-select[aria-label*="Filtro Tipo de Atividade"]', camposDinamicos.fpglobal_tipoAtividade);
				} 
				
				if (camposDinamicos.fpglobal_usuarioResponsavel.toString() != "") {
					await escolherSelect('mat-select[aria-label*="Filtro Usuário Responsável"]', camposDinamicos.fpglobal_usuarioResponsavel);
				} 
				
				//somente primeiro grau
				if (preferencias.grau_usuario == "primeirograu") {
					if (camposDinamicos.fpglobal_faseProcessual.toString() != "") {
						await escolherSelect('mat-select[aria-label*="Filtro Fase processual"]', camposDinamicos.fpglobal_faseProcessual);					
					}
				}
				
				//somente segundo Grau
				if (preferencias.grau_usuario == "segundograu") {
					if (camposDinamicos.fpglobal_relatorProcesso.toString() != "") {
						await escolherSelect('mat-select[aria-label*="Filtro Relator do processo"]', camposDinamicos.fpglobal_relatorProcesso);					
					} 
					
					if (camposDinamicos.fpglobal_OJC.toString() != "") {
						await escolherSelect('mat-select[aria-label*="Filtro Órgãos Julgadores do OJC"]', camposDinamicos.fpglobal_OJC);					
					}
				}
				
				if (camposDinamicos.fpglobal_naTarefaDesde != "") {
					await filtroPreencherInput('input[aria-label*="Filtro Na tarefa desde"]', camposDinamicos.fpglobal_naTarefaDesde);
				} 
				
				if (camposDinamicos.fpglobal_naTarefaate != "") {
					await filtroPreencherInput('input[aria-label*="Filtro Na tarefa até"]', camposDinamicos.fpglobal_naTarefaate);
				}
				
			} else if (tabela == 'Atividades') {
				if (camposDinamicos.fa_classeJudicial.toString() != "") {
					await escolherSelect('mat-select[aria-label*="Filtro Classe Judicial"]', camposDinamicos.fa_classeJudicial);
				} 
				
				if (camposDinamicos.fa_data_de != "") {
					await filtroPreencherInput('input[aria-label*="Filtro data de"]', camposDinamicos.fa_data_de);
				} 
				
				if (camposDinamicos.fa_data_ate != "") {
					await filtroPreencherInput('input[aria-label*="Filtro data até"]', camposDinamicos.fa_data_ate);
				} 
				
				if (camposDinamicos.fa_tipo.toString() != "") {
					await escolherSelect('mat-select[aria-label*="Filtro Tipo da Atividade"]', camposDinamicos.fa_tipo);
				} 
				
				if (camposDinamicos.fa_descricao != "") {
					await filtroPreencherInput('input[aria-label*="Descrição da Atividade"]', camposDinamicos.fa_descricao);
				} 
				
				if (camposDinamicos.fa_responsaveis.toString() != "") {
					await escolherSelect('mat-select[aria-label*="Filtro Responsáveis"]', camposDinamicos.fa_responsaveis);
				}
				
			} else if (tabela == 'Comentários') {
				if (camposDinamicos.fc_classeJudicial.toString() != "") {
					await escolherSelect('mat-select[aria-label*="Filtro Classe Judicial"]', camposDinamicos.fc_autores);
				} 
				
				if (camposDinamicos.fc_descricao != "") {
					await filtroPreencherInput('input[aria-label*="Descrição do Comentário"]', camposDinamicos.fc_descricao);
				} 
				
				if (camposDinamicos.fc_data_de != "") {
					await filtroPreencherInput('input[aria-label*="Filtro data de"]', camposDinamicos.fc_data_de);
				} 
				
				if (camposDinamicos.fc_data_ate != "") {
					await filtroPreencherInput('input[aria-label*="Filtro data até"]', camposDinamicos.fc_data_ate);
				} 
				
				if (camposDinamicos.fc_autores.toString() != "") {
					await escolherSelect('mat-select[aria-label*="Filtro Autores"]', camposDinamicos.fc_autores);
				}
				
			} else if (tabela == 'Processos do Gabinete') {
				if (camposDinamicos.fpg_inicio_data_de != "") {
					await filtroPreencherInput('input[aria-label*="De (Início"]', camposDinamicos.fpg_inicio_data_de);
				} 
				
				if (camposDinamicos.fpg_inicio_data_ate != "") {
					await filtroPreencherInput('input[aria-label*="Até (Início"]', camposDinamicos.fpg_inicio_data_ate);
				} 
				
				if (camposDinamicos.fpg_fim_data_de != "") {
					await filtroPreencherInput('input[aria-label*="De (Fim"]', camposDinamicos.fpg_fim_data_de);
				} 
				
				if (camposDinamicos.fpg_fim_data_ate != "") {
					await filtroPreencherInput('input[aria-label*="Até (Fim"]', camposDinamicos.fpg_fim_data_ate);
				} 
				
				if (camposDinamicos.fpg_classeJudicial.toString() != "") {
					await escolherSelect('mat-select[aria-label*="Filtro Classe Judicial"]', camposDinamicos.fpg_classeJudicial);
				} 
				
				if (camposDinamicos.fpg_relator.toString() != "") {
					await escolherSelect('mat-select[aria-label*="Filtro Relator"]', camposDinamicos.fpg_relator);
				} 
				
				if (camposDinamicos.fpg_responsavel.toString() != "") {
					await escolherSelect('mat-select[aria-label*="Filtro Responsáveis"]', camposDinamicos.fpg_responsavel);
				}
							
			}
			resolver();
		});
	}
	
	async function linhasPorPagina(qtde) {
		return new Promise(async resolver => {
			let ancora = await esperarElemento('pje-paginador');
			let itensPorPagina = ancora.querySelectorAll('div[class*="mat-select-trigger"]');
			await escolherOpcaoTeste(itensPorPagina[1],qtde);
			resolver(true);
		});
	}
	
	async function filtroClicarBotao(seletor) {
		return new Promise(async resolve => {
			await clicarBotao(seletor);
			await capturarUltimoNetworkRequest();
			resolve(true);
		});
	}
	
	async function filtroPreencherInput(seletor, value) {
		return new Promise(async resolve => {
			await preencherInput(seletor, value);
			await capturarUltimoNetworkRequest();
			resolve(true);
		});
	}
	
	async function escolherSelect(seletor, valor) {
		return new Promise(async resolve => {
			await sleep(preferencias.maisPje_velocidade_interacao);
			let elemento = await esperarElemento(seletor);
			await clicarBotao(elemento.firstElementChild);
			await sleep(1000);
			let dados = await esperarColecao('mat-option[role="option"]', 1);
			
			// console.log(dados[1]?.innerText?.includes('Carregando itens'));
			
			while(dados[1]?.innerText?.includes('Carregando itens')) {
				await sleep(200);
				dados = await esperarColecao('mat-option[role="option"]', 1);
			}
			
			// console.log(dados[1]?.innerText?.includes('Carregando itens'));
			
			for (const [pos, item] of dados.entries()) {
				if (valor.toString().includes(item.innerText)) {
					await clicarBotao(item);
				};
			}
			
			await clicarBotao('button[aria-label="Filtrar"]');
			await capturarUltimoNetworkRequest();
			resolve(true);
		});
	}
	
	async function capturarUltimoNetworkRequest() {
		//436.677.599-91 cpf segundo grau
		return new Promise(async resolve => {
			let capture_network_request = [];
			let capture_resource = performance.getEntriesByType("resource");
			let startTimeUltimoNR = capture_resource[capture_resource.length - 1].startTime;
			
			//obtém a lista de NR's do ultimo segundo e confere se ela é um dos request's de filtro
			for (let i = 0; i < capture_resource.length; i++) {
				// console.log(i + " : " + capture_resource[i].name + " : " + capture_resource[i].startTime);
				if (capture_resource[i].startTime > (startTimeUltimoNR-1000))  {
					if (
						capture_resource[i].name.includes('/relatorioatividades/?') ||    //atividades GIGS
						capture_resource[i].name.includes('/relatoriocomentarios/?') ||   //comentários GIGS
						capture_resource[i].name.includes('api/agrupamentotarefas/') ||   //Painel Global
						capture_resource[i].name.includes('api/processo/relatorio?')      //Processos de Gabinete GIGS
					) {
						// console.log("     |_____" + capture_resource[i].name + " : " + capture_resource[i].startTime);
						return resolve(true);
					}
				}				
			}
			
			return resolve(true);
			
		});
	}
}

//FUNÇÃO QUE INSERE O BOTÃO COPIAR LISTA DE PROCESSOS NAS TABELAS DA PÁGINA PRINCIPAL DO PJE-ANEXAR-PDFS
async function inserirBotaoCopiarListaDeProcessos() {
	return new Promise(async resolver => {
		let btCopiarLista = await esperarElemento('button[id="maisPje_bt_copiar_lista"]', null, 100);
		if (!btCopiarLista) {
			console.log('MaisPJe: inserir copiar lista')
			let ancora = await esperarElemento('pje-data-table div[role=column]') ;
			
			if (!document.getElementById('maisPje_tooltip_abaixo5')) {
				tooltip('abaixo5');
			}
			
			let botao = document.createElement("button");
			botao.id = "maisPje_bt_copiar_lista";
			botao.classList.add("mat-focus-indicator", "mat-tooltip-trigger", "mat-icon-button", "mat-button-base");
			botao.setAttribute("maispje-tooltip-abaixo5", "maisPje: Copiar Lista de Processos");
			botao.onclick = async function () {
				let tabela = await esperarElemento('pje-data-table tbody');
				let textocopiado = tabela.innerText.match(new RegExp('\\d{7}-\\d{2}\\.\\d{4}\\.\\d{1,2}\\.\\d{1,2}\\.\\d{4}','gm')).join();
				// let ta = document.createElement("textarea");
				// ta.textContent = textocopiado;
				// document.body.appendChild(ta);
				// ta.select();
				// document.execCommand("copy");
				navigator.clipboard.writeText(textocopiado);
				criarCaixaDeAlerta("ALERTA","Lista de Processos copiada com sucesso!\n\nUse o CTRL+V para colar.", 3);
			};
			
			let botao_span = document.createElement("span");
			botao_span.classList.add("mat-button-wrapper");
			
			let botao_icone = document.createElement("i");
			botao_icone.setAttribute('aria-hidden','true'); //faz com que o NVDA ignore o elemento
			botao_icone.classList.add("mat-tooltip-trigger", "fas", "fa-copy", "fa-lg", "icone-clicavel");
			botao_icone.style.cssText += 'font-size: 20px; line-height: 44px; color: orangered;';
			
			botao_span.appendChild(botao_icone);						
			botao.appendChild(botao_span);
			
			if (ancora.hasAttribute('aria-label')) {
				ancora.parentElement.appendChild(botao);
			} else {
				ancora.insertAdjacentElement('beforebegin', botao);
			}
			resolver(true);
		} else { resolver(true) }		
	});
}

//FUNÇÃO QUE RETORNA O ID DO PROCESSO PARA ABERTURA DE NOVAS PÁGINAS
async function obterIdProcessoViaApi(numero) {
	let urlBase = preferencias.trt;
	if (preferencias.trt.includes('dev015')) { urlBase = preferencias.trt.replace('dev015','pje') }
	
	let url = 'https://' + urlBase + '/pje-comum-api/api/agrupamentotarefas/processos?numero=' + numero;
	let grau_usuario = preferencias.grau_usuario == "segundograu" ? 2 : 1;
	
	return fetch(url,
        {
			method: "GET",
			mode: "cors",
			credentials: "include",
            headers: {
				"Content-Type": "application/json",
                "X-Grau-Instancia": grau_usuario || 1
            }
        })
        .then(function (response) {
			return response.json();
        })
        .then(data=>{
            return data || '';
        })
        .catch(function (err) {
			return '';
        });
}

async function obterIdProcessoViaApiPublica(numero) {
	let soNumeros = numero.trim().replace(/[^0-9]+/g, '');
	// console.log(soNumeros +  " : " + (soNumeros === ''));
	
	let urlBase = preferencias.trt;
	if (preferencias.trt.includes('dev015')) { urlBase = preferencias.trt.replace('dev015','pje') }
	
	
	let url = (soNumeros === '') ? 'https://' + urlBase + '/pje-administracao-api/api/consultaprocessosadm?pagina=1&nomeParte=' + numero + '&tamanhoPagina=1000' : 'https://' + urlBase + '/pje-consulta-api/api/processos/dadosbasicos/' + numero;

	let grau_usuario = preferencias.grau_usuario == "segundograu" ? 2 : 1;
	
	return fetch(url,
        {
			method: "GET",
			mode: "cors",
			credentials: "include",
            headers: {
				"Content-Type": "application/json",
                "X-Grau-Instancia": grau_usuario || 1
            }
        })
        .then(function (response) {
			return response.json();
        })
        .then(data=>{
            return data || '';
        })
        .catch(function (err) {
			return '';
        });
}

//FUNÇÃO QUE RETORNA O ORGAO JULGADOR CARGO
async function obterOrgaoJulgadorCargo(numero) {
	let urlBase = preferencias.trt;
	if (preferencias.trt.includes('dev015')) { urlBase = preferencias.trt.replace('dev015','pje') }
	
	let url = 'https://' + urlBase + '/pje-comum-api/api/agrupamentotarefas/processos?numero=' + numero;
	let resposta = await fetch(url);
	let dados = await resposta.json();
	console.log(dados);
	let idProcesso = dados[0].idProcesso;
	
	if (idProcesso) {
		let ojc = await obterDadosProcessoViaApi(idProcesso);
		return ojc.orgaoJulgadorCargo.descricao;
	} else {
		console.log('maisPje: idProcesso inexistente!')
		return 'erro';
	}
}

//FUNÇÃO QUE RETORNA O NOME DA TAREFA DE ACORDO COM O CODIGO
async function obterNomeTarefaViaApi(codigo) {
	let urlBase = preferencias.trt;
	if (preferencias.trt.includes('dev015')) { urlBase = preferencias.trt.replace('dev015','pje') }
		
	let url = 'https://' + urlBase + '/pje-comum-api/api/tarefas/' + codigo;
	let grau_usuario = preferencias.grau_usuario == "segundograu" ? 2 : 1;
	
	return fetch(url,
        {
			method: "GET",
			mode: "cors",
			credentials: "include",
            headers: {
				"Content-Type": "application/json",
                "X-Grau-Instancia": grau_usuario || 1
            }
        })
        .then(function (response) {
			return response.json();
        })
        .then(data=>{
            return data.nome || '';
        })
        .catch(function (err) {
			return '';
        });
}

//FUNÇÃO QUE RETORNA O NOME DA TAREFA DE ACORDO COM O ID DO PROCESSO
async function obterTarefaIdProcessoViaApi(idProcesso) {
	let urlBase = preferencias.trt;
	// if (preferencias.trt.includes('dev015')) { urlBase = preferencias.trt.replace('dev015','pje') }
	
	let resposta = await fetch('https://' + urlBase + '/pje-comum-api/api/processos/id/' + idProcesso + '/tarefas?maisRecente=true');
	let dados = await resposta.json();
	return dados[0].nomeTarefa;
}


//FUNÇÃO QUE OBTEM O MOTIVO DO SOBRESTAMENTO
async function obterMotivoSobrestamentoViaApi(idProcesso) {
	let urlBase = preferencias.trt;
	let resposta = await fetch('https://' + urlBase + '/pje-comum-api/api/processos/id/' + idProcesso + '/sobrestamentos');
	let dados = await resposta.json();
	return dados[0].textoFinalExternoSobrestamento;
}


//FUNÇÃO QUE RETORNA OS GIGS ATIVOS LANÇADOS NO Processo
async function obterGIGSIdProcessoViaApi(idProcesso) {
	let urlBase = preferencias.trt;
	let resposta = await fetch('https://' + urlBase + '/pje-gigs-api/api/atividade/processo/' + idProcesso);
	let dados = await resposta.json();
	let lista = [];	
	if (dados[0]) {
		for (const [pos, atividade] of dados.entries()) {
			// 2025-05-19T00:00:00
			let data = atividade.dataPrazo;
			let padraoData = /\d{4}\-\d{2}-\d{2}/gm;
			if (padraoData.test(data)) {
				data = data.match(padraoData).join();
				let x = data.split('-');
				data = x[2] + '/' + x[1] + '/' + x[0];
			}
			lista.push({tipoAtividade: atividade.tipoAtividade.descricao, dataPrazo: data, statusAtividade: atividade.statusAtividade, observacao: atividade.observacao});
		}
	}
	return lista;
}

//FUNÇÃO QUE RETORNA O NOME DA FASE DE ACORDO COM O ID DO PROCESSO
async function obterFaseIdProcessoViaApi(idProcesso) {
	let urlBase = preferencias.trt;
	if (preferencias.trt.includes('dev015')) { urlBase = preferencias.trt.replace('dev015','pje') }
	
	let resposta = await fetch('https://' + urlBase + '/pje-comum-api/api/processos/id/' + idProcesso);
	let dados = await resposta.json();
	return dados.faseProcessual;
}

//FUNÇÃO QUE RETORNA AS PRIORIDADES DO PROCESSO
async function obterPrioridadeProcessoViaApi(idProcesso) {
	let urlBase = preferencias.trt;
	if (preferencias.trt.includes('dev015')) { urlBase = preferencias.trt.replace('dev015','pje') }
	
	let url = 'https://' + urlBase + '/pje-comum-api/api/processos/id/' + idProcesso + '/prioridades';
	let resposta = await fetch(url);
	let dados = await resposta.json();
	
	if (!dados) { return '' }
	
	let listaPrioridades = [];
	for (const [pos, prioridade] of dados.entries()) {
		if (prioridade.prioridadeProcessual.ativo) {
			listaPrioridades.push(prioridade.prioridadeProcessual.descricao);
		}
	}
	return listaPrioridades;
}

//FUNÇÃO QUE RETORNA A INSTANCIA DO USUARIO
async function apiObterGraudeJurisdicaoDoPerfil() {
	return new Promise(async resolve => {
		let api = captureLastNetworkRequest();
		if (!api) {
			browser.runtime.sendMessage({tipo: 'storage_guardar', chave: 'grau_usuario', valor: 'primeirograu'}); 
		} else {
			let resposta = await fetch(api);
			let dados = await resposta.json();
			// console.log('*********' + dados.instancia)
			if (dados.instancia == '3') {
				browser.runtime.sendMessage({tipo: 'storage_guardar', chave: 'grau_usuario', valor: 'outros'});
				
			} else if (dados.instancia == '2') {
				browser.runtime.sendMessage({tipo: 'storage_guardar', chave: 'grau_usuario', valor: 'segundograu'});
			} else {
				browser.runtime.sendMessage({tipo: 'storage_guardar', chave: 'grau_usuario', valor: 'primeirograu'});
			}
		}
		return resolve(true);
	});
	
	function captureLastNetworkRequest(e) {
		let capture_network_request = [];
		let capture_resource = performance.getEntriesByType("resource");
		for (let i = 0; i < capture_resource.length; i++) {
			if (capture_resource[i].name.includes('/pje-comum-api/api/orgaosjulgadores/')) {
				capture_network_request.push(capture_resource[i].name);
			}
		}
		return capture_network_request[capture_network_request.length - 1];
	}
	
}

//FUNÇÃO QUE RETORNA DADOS DO PROCESSO
async function obterDadosProcessoViaApi(idProcesso) {
	let urlBase = preferencias.trt;
	if (preferencias.trt.includes('dev015')) { urlBase = preferencias.trt.replace('dev015','pje') }
	
	let url = 'https://' + urlBase + '/pje-comum-api/api/processos/id/' + idProcesso;
	let resposta = await fetch(url);
	let dados = await resposta.json();
	return dados;
}

//FUNÇÃO QUE RETORNA AS CONTAS COM SALDO NO SIF
async function obterContasSIF(numero) {
	let urlBase = preferencias.trt;
	if (preferencias.trt.includes('dev015')) { urlBase = preferencias.trt.replace('dev015','pje') }
	
	let url = 'https://' + urlBase + '/sif-financeiro-api/api/listas/contas/' + numero;	
	return fetch(url)
        .then(function (response) {
			return response.json();
        })
        .then(data=>{
            return data || '';
        })
        .catch(function (err) {
			return '';
        });
}

//FUNÇÃO QUE ANALISA O MOTIVO DO SOBRESTAMENTO
async function analisarMotivosSobrestamento() {
	console.log('maisPje: analisarMotivosSobrestamento');
	await ligar_mutation_observer();
	let motivos = await esperarColecao('pje-motivos-sobrestamento td');
	
	//converte o número do processo em link para o pje
	for (const [pos, motivo] of motivos.entries()) {
		if (new RegExp('\\d{7}-\\d{2}\\.\\d{4}\\.\\d{1,2}\\.\\d{1,2}\\.\\d{4}','g').test(motivo.innerText)) {
			inserirbotao(motivo, motivo.innerText.match(new RegExp('\\d{7}-\\d{2}\\.\\d{4}\\.\\d{1,2}\\.\\d{1,2}\\.\\d{4}','g')).join());
		}
	}
	
	function inserirbotao(elemento, processo) {
		//limpa o conteudo
		elemento.innerText = elemento.innerText.replace(new RegExp('\\d{7}-\\d{2}\\.\\d{4}\\.\\d{1,2}\\.\\d{1,2}\\.\\d{4}','g'), ' ');
		elemento.innerText = elemento.innerText.replace("(Processo principal nº )","");
		//CRIA BOTÃO CONSULTA RAPIDA DE PROCESSOS
		let atalho = document.createElement("a");
		atalho.id = "extensaoPje_sobrestamento_atalhoConsultaPJe";
		atalho.style = 'z-index: 100; width: 28px; height: 28px; text-align: center; text-decoration-line: underline; color: blue; cursor: pointer;';
		atalho.onmouseenter = function () {atalho.style.color  = 'orangered'};
		atalho.onmouseleave = function () {atalho.style.color  = 'black'};
		atalho.onclick = function () {
			consultaRapidaPJE(processo);
		};
		atalho.title = 'MaisPje: Consultar Processo';
		atalho.innerText = "(Processo principal nº " + processo + ")";					
		elemento.appendChild(atalho);
	}
	
	function ligar_mutation_observer() {
		return new Promise(resolve => {
			let monitor = false;
			let observer_motivos_sobrestamento = new MutationObserver(function(mutationsDocumento) {
				mutationsDocumento.forEach(function(mutation) {
					if (!mutation.removedNodes[0]) { return }
					if (!mutation.removedNodes[0].tagName) { return }
					// console.log("***[DEL] " + mutation.removedNodes[0].tagName);
					if (mutation.removedNodes[0].tagName.includes("MAT-PROGRESS-")) { //elementos de botões com progress (mat-progress-bar e mat-progress-spinner)
						observer_motivos_sobrestamento.disconnect();
						resolve(false);
					}
				});
			});
			let configDocumento = { childList: true, subtree:true }
			observer_motivos_sobrestamento.observe(document.body, configDocumento); //inicia o MutationObserver
			setTimeout(function() {
				observer_motivos_sobrestamento.disconnect();
				resolve(false); //sem erros
			}, 5000);  //desliga o mutation depois de 5 segundos
		});
	}
}

//FUNÇÃO QUE VERIFICA SE O USUARIO É SERVIDOR
async function verificarSeServidor() {
	let url = 'https://' + preferencias.trt + '/pje-seguranca/api/token/perfis';
	let resposta = await fetch(url);
	let dados = await resposta.json();
	let papeis = [];
	let retorno = true;
	if (dados.mensagem) { return true } //sem autenticação
	dados.forEach(function(item) {
		if (item.papel == 'Advogado' || item.papel == 'Perito') {
			retorno = false;
		}
	});
	return retorno;
}

//FUNÇÃO QUE INSERE A FUNCIONALIDADE DE VERIFICAR IMPEDIMENTO E SUSPEIÇÃO NA PAUTA DO SEGUNDO GRAU
async function obterImpedimentosSuspeicoesPautaSegundoGrau() {
	console.log('obterImpedimentosSuspeicoesPautaSegundoGrau');
	let filtroIeSPauta2grau;
	await guardarFiltroStorage('');
	monitor_janela_pauta();
	iniciar();
	
	async function iniciar() {
		incluirBotaoVerificarIeS();
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
						
						let bt_continuar = document.createElement("span");
						bt_continuar.style = "color: white; margin-top: 10px; padding: 10px; border-bottom: 1px solid lightgrey; background-color: #7a9ec8; border-radius: 3px; cursor: pointer;";
						bt_continuar.innerText = "Verificar";
						bt_continuar.onmouseenter = function () {
							bt_continuar.style.backgroundColor  = '#5077a4';
						};
						bt_continuar.onmouseleave = function () {
							bt_continuar.style.backgroundColor  = '#7a9ec8';
						};
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
		listaDeMagistradosParaVerificarIeS.forEach( item => {
			let ancora = document.getElementById('abaPautaJulgamentoListPanel') || document.querySelector('div[id*="votacaoAntecipadaListPanel"]');
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
			ancora.insertBefore(container, ancora.children[1]);
		});
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
		let listaNum = tabela.innerText.match(new RegExp('\\d{7}-\\d{2}\\.\\d{4}\\.\\d{1,2}\\.\\d{1,2}\\.\\d{4}','g')).join().split(",");
		browser.runtime.sendMessage({tipo: 'insertCSS', file: 'maisPje_icones.css'});
		for (const [pos, processo] of listaNum.entries()) {
			let idProcesso = await obterIdProcessoViaApiPublica(processo);
			let listaDeIeSPorMagistrados = [];
			for (const [pos, magistrado] of listaDeMagistradosParaVerificarIeS.entries()) {
				let ies = await fetchObterRegrasImpedimentoESuspeicao(idProcesso[0].id,magistrado.idMagistrado)
				//retorna true ou false
				listaDeIeSPorMagistrados.push({idMagistrado:magistrado.idMagistrado,nomeMagistrado:magistrado.nomeMagistrado,regrasIeS:ies});
			}
			
			let mensagem = '---MaisPJe: IMPEDIMENTO E/OU SUSPEIÇÃO---\n\n';
			listaDeIeSPorMagistrados.forEach( item => {
				// console.log('RegraIeS ( ' + item.nomeMagistrado + '): ' + item.regrasIeS)
				if (item.regrasIeS) {
					mensagem += item.nomeMagistrado + ': Encontrado Impedimento/suspeição\n';
				} else {
					mensagem += item.nomeMagistrado + ': OK\n';
				}
			})
			
			let ancora = querySelectorByText('td[id*="abaPautaJulgamentoList:',processo);
			if (!ancora) { ancora = querySelectorByText('td[id*="votacaoAntecipadaList:',processo) }
			if (!ancora) { return }
			let div = document.createElement('div');
			div.id = "maisPje_icone_IeS_" + processo;
			div.style = 'width: 5%; float: right;';
			div.title = mensagem;
			let i = document.createElement('i');
			i.className = 'icone thumbs-down';
			let estilo  = 'width:15px;height:15px;';
			i.style =  estilo + ((mensagem.includes('Encontrado')) ? 'background-color:red;' : 'background-color: green;transform: scaleX(-1) rotate(180deg);');
			div.appendChild(i);		
			ancora.appendChild(div);
		}
	}
	
	async function fetchObterRegrasImpedimentoESuspeicao(idProcesso, idMagistrado) {
		let resposta = await fetch('https://' + preferencias.trt + '/pje-comum-api/api/regrasimpedimentomagistrado/regrasimpedimento?idMagistrado=' + idMagistrado + '&idProcesso=' + idProcesso);
		let dados = await resposta.json();
		if (dados.length > 0) {
			// console.log(JSON.stringify(dados))
			return true;
		} else {
			return false;
		}
	}
	
	function monitor_janela_pauta() {
		console.log("Extensão maisPJE (" + agora() + "): monitor_janela_pauta");
		let targetDocumento = document.body;
		let observerDocumento = new MutationObserver(function(mutationsDocumento) {
			mutationsDocumento.forEach(function(mutation) {
				if (!mutation.addedNodes[0]) { return }
				if (!mutation.addedNodes[0].tagName) { return }
				if (!mutation.addedNodes[0].tagName.includes("DIV") && !mutation.addedNodes[0].tagName.includes("TABLE")) { return }
				if (mutation.addedNodes[0].className.includes('rich-panel')) {
					// console.log(mutation.addedNodes[0].tagName + " : " + mutation.addedNodes[0].className + " : " + mutation.addedNodes[0].innerText);
					if (guardarFiltroStorage(filtroIeSPauta2grau)) {
						iniciar();
					}
				}
				
				if (mutation.addedNodes[0].className.includes('rich-tabpanel')) {
					iniciar();
				}
				
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

//FUNÇÃO QUE INSERE A FUNCIONALIDADE DE VERIFICAR SEGREDO DE JUSTIÇA NO SEGUNDO GRAU
async function obterSegredoDeJustica() {
	console.log('obterSegredoDeJustica');
	if (document.location.href.includes("/PautaJulgamento/pautaPopUp.seam")) {
		iniciar1();
	} else {
		iniciar2();
	}
	
	async function iniciar1() {
		let tabela = await esperarElemento('table[id="abaPautaJulgamentoList"],table[id="votacaoAntecipadaList"]');
		if (!tabela) { return }
		monitor_janela_pauta_segredo();
		mapearProcessos(tabela);
	}
	
	async function iniciar2() {
		let tabela = await esperarElemento('table[id="formPainelSecretario:dataTableFiltros"]');
		if (!tabela) { return }
		mapearProcessos(tabela);
	}
	
	async function mapearProcessos(tabela) {		
		if (!tabela) { return }
		let listaNum = tabela.innerText.match(new RegExp('\\d{7}-\\d{2}\\.\\d{4}\\.\\d{1,2}\\.\\d{1,2}\\.\\d{4}','g')).join().split(",");
		
		for (const [pos, processo] of listaNum.entries()) {
			let idProcesso = await obterIdProcessoViaApiPublica(processo);
			let segredoDeJustica = await fetchObterSegredoDeJustica(idProcesso[0].id);
			
			if (segredoDeJustica) {
				let linha = querySelectorByText('span[role="presentation"],td[id*="abaPautaJulgamentoList"],td[id*="votacaoAntecipadaList"]', processo);
				linha.style.color = 'red';
				linha.style.fontWeight = 'bold';
				
				let img = document.createElement('img');
				img.src = '/segundograu/img/al/secred.png';
				img.width = '18';
				img.height = '18';
				img.title="MaisPJe: Segredo de Justiça";
				linha.insertBefore(img, linha.firstElementChild);
			}
		}
	}
	
	async function fetchObterSegredoDeJustica(idProcesso) {
		let resposta = await fetch('https://' + preferencias.trt + '/pje-comum-api/api/processos/id/' + idProcesso);
		let dados = await resposta.json();
		return dados.segredoDeJustica;
	}
	
	async function monitor_janela_pauta_segredo() {
		let targetDocumento = document.body;
		let observerDocumento = new MutationObserver(async function(mutationsDocumento) {
			mutationsDocumento.forEach(async function(mutation) {
				if (!mutation.addedNodes[0]) { return }
				if (!mutation.addedNodes[0].tagName) { return }
				if (!mutation.addedNodes[0].tagName.includes("DIV") && !mutation.addedNodes[0].tagName.includes("TABLE")) { return }
				if (mutation.addedNodes[0].className.includes('rich-panel')) {
					// console.log(mutation.addedNodes[0].tagName + " : " + mutation.addedNodes[0].className + " : " + mutation.addedNodes[0].innerText);
					let tabela = await esperarElemento('table[id="abaPautaJulgamentoList"],table[id="votacaoAntecipadaList"]');
					if (!tabela) { return }
					mapearProcessos(tabela);
				}
				
				if (mutation.addedNodes[0].className.includes('rich-tabpanel')) {
					let tabela = await esperarElemento('table[id="abaPautaJulgamentoList"],table[id="votacaoAntecipadaList"]');
					if (!tabela) { return }
					mapearProcessos(tabela);
				}
				
			});
		});		
		let configDocumento = { childList: true, subtree:true }
		observerDocumento.observe(targetDocumento, configDocumento); //inicia o MutationObserver
	}
	
}

async function obterNumeroDoProcessoNaTela() {
	return new Promise(async resolve => {
		let ancora = await esperarElemento(seletorDetalhesNumeroProcesso);
		let padrao = /\d{7}\-\d{2}\.\d{4}\.\d{1}\.\d{2}\.\d{4}/g;
		if (ancora) {
			let check = setInterval(function() {
				if (padrao.test(ancora.innerText)) {
					clearInterval(check);
					return resolve(ancora.innerText.match(padrao));
				}
			}, 100);
		} else {
			return resolve(null);
		}
	});
}

async function obterVersaoPjeNaTela() {
	return new Promise(async resolve => {
		let ancora = await esperarElemento('div[class*="versaoSistema"],*[id="modulo-versao"]');
		if (ancora) {
			return resolve(ancora.innerText);
		} else {
			return resolve(null);
		}
	});
}

//FUNÇÃO QUE ATIVA O MODULO 10 NAS AUDIENCIAS
async function ativarModulo10() {
	if (!document.getElementById('maisPje_modulo10')) {
		if (preferencias.modulo10.length == 0) {
			return;
		} else if (preferencias.modulo10.length == 1) {
			await preencherInput('input[name="url"]',preferencias.modulo10[0].url, false);
		} else {
			let el = await esperarElemento('input[name="url"]');
			let ancora = el.parentElement
			ancora.style.position = 'relative';
			let span = document.createElement('span');
			span.id = 'maisPje_modulo10';
			span.style = 'position: absolute;top: 35%;right: -30px;font-size: 20px; cursor: pointer; color: gray;';
			span.title = 'MaisPje: Ver Links';
			
			span.onclick = async function () {
				let valor = await criarCaixaDeSelecao(preferencias.modulo10);
				if (document.querySelector('input[name="url"]')) {
					await preencherInput('input[name="url"]',valor.url, false);
				}
				if (document.querySelector('input[name="horario"]')) {
					await preencherInput('input[name="horario"]',valor.horario, false);
				}
			}
			
			let i = document.createElement('i');
			i.className = 'fa fa-link icone-tamanho-18';
			span.appendChild(i);
			ancora.appendChild(span);
			
			//escolhe automaticamente de acordo com o horário
			if (document.querySelector('span[name="dataHora"]')) {
				let dataHora = document.querySelector('span[name="dataHora"]').innerText;
				for (const [pos, item] of preferencias.modulo10.entries()) {
					if (dataHora.includes(item.horario)) {
						await preencherInput('input[name="url"]',item.url, false);
					}
				}
			}
		}
	}
	
	function criarCaixaDeSelecao(dados) {
		return new Promise(
			resolver => {
				if (!document.getElementById('maisPje_caixa_de_selecao')) {
					let altura = window.innerHeight || document.documentElement.clientHeight || document.body.clientHeight;
					
					let elemento1 = document.createElement("div");
					elemento1.id = 'maisPje_caixa_de_selecao';
					elemento1.style = 'position: fixed; width: 100%; height: ' + altura + 'px; top: 0; inset: 0px; background: #00000080; z-index: 10000; display: flex; align-items: center; justify-content: center; color: rgb(81, 81, 81); font-weight: bold; font-family: Open Sans,Arial,Verdana,sans-serif; text-align: center; flex-direction: column;';
					elemento1.onclick = function () {elemento1.remove()}; //se clicar fora fecha a janela
					
					let div = document.createElement("div");
					div.style="height: auto;display: inline-grid;background-color: white;padding: 15px;border-radius: 4px;box-shadow: 0 2px 1px -1px rgba(0,0,0,.2),0 1px 1px 0 rgba(0,0,0,.14),0 1px 3px 0 rgba(0,0,0,.12); overflow-y: scroll;";
					let titulo = document.createElement("span");
					titulo.style = "color: grey; border-bottom: 1px solid lightgrey;";
					titulo.innerText = "Selecione o Link da Audiência";
					div.appendChild(titulo);
					
					let map = [].map.call(
						dados, 
						function(dado) {
							if (dado.url) {
								let span = document.createElement("span");
								span.className = "mat-option";
								span.innerText = dado.horario + " - " + dado.url;
								span.onmouseenter = function () {span.style.backgroundColor  = 'lightgray'};
								span.onmouseleave = function () {span.style.backgroundColor  = 'white'};
								span.onclick = function () {
									resolver(dado);
									document.getElementById('maisPje_caixa_de_selecao').remove();
								};
								div.appendChild(span);
							}
						}
					);
					elemento1.appendChild(div);
					document.body.appendChild(elemento1);
				} else {
					resolver(null);
				}
			}
		);
	}
}

async function incluirPrazoRelator() {
	console.log('maisPJe: incluirPrazoRelator(): ' + preferencias.grau_usuario)
	
	if (preferencias.grau_usuario == "segundograu") {
		if (document.location.href.includes('nomeTarefa=Minutar+voto')) { //pje antigo
			let numeroProcesso = document.getElementById('normalProcessoDiv').innerText.match(new RegExp('\\d{7}-\\d{2}\\.\\d{4}\\.\\d{1,2}\\.\\d{1,2}\\.\\d{4}','g'));
			let dadosProcesso = await obterIdProcessoViaApi(numeroProcesso);
			let prazoRelator = await obterPrazoRelator(dadosProcesso[0].idProcesso);
			let ancora = await esperarElemento('div[id="bannerMovimentar"]');
			let info = await esperarElemento('div[id="maisPje_prazoRelator"]', null, 10);		
			if (!info) {
				let div = document.createElement('div');
				div.id = "maisPje_prazoRelator";
				div.style = "margin: 0; padding: 0; margin-left: 60px;color: white;"
				if (prazoRelator) {
					let dtInicio = await converteData(prazoRelator.dataInicioPrazo);					
					let dtFim = await converteData(prazoRelator.dataTerminoPrazo);
					div.innerText = "Prazo Relator: " + dtInicio + " - " + dtFim;
				} else {
					div.innerText = "Prazo Relator: não registrado";
				}
				ancora.appendChild(div);
			}
		} else {
			let idProcesso = document.location.href.substring(document.location.href.search("/processo/")+10, document.location.href.search("/tarefa"));
			let prazoRelator = await obterPrazoRelator(idProcesso);
			let ancora = await esperarElemento('div[id="responsavelprocesso"]');
			let info = await esperarElemento('span[id="maisPje_prazoRelator"]', null, 10);		
			if (!info) {			
				ancora.style.display = "grid";
				ancora.style.justifyContent = "left";
				let span = document.createElement('span');
				span.id = "maisPje_prazoRelator";
				span.style = "margin-top: 5px;";
				if (prazoRelator) {
					let dtInicio = await converteData(prazoRelator.dataInicioPrazo);					
					let dtFim = await converteData(prazoRelator.dataTerminoPrazo);
					span.innerText = "Prazo Relator: " + dtInicio + " - " + dtFim;
				} else {
					span.innerText = "Prazo Relator: não registrado";
				}
				ancora.appendChild(span);
			}
		}
	}
	
	async function converteData(texto) { //YYYY-MM-DD
		return new Promise(
			resolver => {
				let eData = /\d{2,4}\D{1}\d{2,4}\D{1}\d{2,4}/;
				let eAno = /\d{4}/;
				
				if (!eData.test(texto)) { return null }
				
				let dia,mes,ano;
				texto = texto.replace(/\D/g,'.');
				let campos = texto.split('.');
				
				//formato YYYY-MM-DD
				ano = campos[0]
				mes = campos[1];	
				dia = campos[2];
				
				console.log('**************************DATA CONVERTIDA: ' + dia + '/' + mes + '/' + ano)
				return resolver(dia + '/' + mes + '/' + ano);
			}
		);
		let parte1, parte2, parte3, separador;
		let padraoSeparador = /\D{1,}/;	
		
		if (!padrao.test(texto)) { return null }	
		separador = texto.match(padrao).join();
		
		return 
		parte1 = valor.split(separador)[0];
		parte2 = valor.split(separador)[1];
		parte3 = valor.split(separador)[2];
	}
}

async function obterPrazoRelator(idProcesso) {
	let urlBase = preferencias.trt;
	if (preferencias.trt.includes('dev015')) { urlBase = preferencias.trt.replace('dev015','pje') }
	
	let url = 'https://' + urlBase + '/pje-gigs-api/api/processo/' + idProcesso + '/prazoRelator';	
	return fetch(url)
        .then(function (response) {
			return response.json();
        })
        .then(data=>{
            return data || '';
        })
        .catch(function (err) {
			return '';
        });
}

//ATIVAR LGPD
async function ativarLGPD() {
	console.log('ativarLGPD');
	browser.runtime.sendMessage({tipo: 'insertCSS', file: 'maisPje_LGPD.css'});
}

//BOTAO PARA ACHAR PROCESSOS SEM AUDIÊNCIA DESIGNADA NA TAREFA AGUARDANDO AUDIÊNCIA
async function processosSemAudienciaDesignada() {
	console.log('processosSemAudienciaDesignada()');
	if (!document.getElementById('maisPje_processosSemAudienciaDesignada')) {
		let ancora = await esperarElemento('span[class="cabecalho-icones"]');
		let botao = document.createElement("button");
		botao.id = "maisPje_processosSemAudienciaDesignada";
		botao.innerText = "Processos sem audiência Designada";
		botao.style = "cursor: pointer; position: relative; top: 20%; margin: 0 5px 0 5px; z-index: 1;";
		botao.onclick = function () {
			
			console.log("Extensão maisPJE (" + agora() + "): filtrarProcessosSemAudienciaDesignada");
			let ativar = document.querySelector('tbody').getAttribute('maisPje_processosSemAudienciaDesignada_ativado');
			if (!ativar || ativar == "false") {
				ativarFiltro();
			} else {
				desativarFiltro();
			}
			
			async function ativarFiltro() {
				document.querySelector('tbody').setAttribute('maisPje_processosSemAudienciaDesignada_ativado',true);
				let el = document.querySelectorAll('tbody tr');
				if (!el) {
					return
				}
				
				for (const [pos, linha] of el.entries()) {
					//****demonstração ao usuário de que está passando na linha
					linha.scrollIntoView({behavior: 'auto',block: 'center',inline: 'center'});
					linha.style.setProperty('filter', 'brightness(0.5)');
					linha.style.setProperty('outline', '2px dashed yellow');
					await sleep(1);
					//**********

					let dados = linha.innerText;										
					let padrao = /(Audiência em:)/;
					// let padrao = /(ncia em:)/;
					if (padrao.test(dados)) {
						linha.style.display = 'none';
						linha.style.setProperty('filter', 'revert');
						linha.style.setProperty('outline', 'revert');
					} else {
						linha.style.setProperty('filter', 'revert');
						linha.style.setProperty('outline', 'revert');
						linha.style.setProperty('background-color', 'khaki');
						linha.setAttribute('maisPje_processosSemAudienciaDesignada_ativado',true);
					}
					
				}
				
				// DESCRIÇÃO: Se o usuário clicar em qualquer item do cabeçalho o filtro será desativado
				document.querySelector('thead').addEventListener('click', function(event) {
					if (!event.target.className.includes('fa-check') && !event.target.className.includes('todas-marcadas')) {
						desativarFiltro();
					}
				});
				
				// DESCRIÇÃO: Se o usuário mudar a página da tabela, o filtro é desativado			
				document.querySelector('pje-paginador').addEventListener('click', function(event) {
					desativarFiltro();
				});
			}
			
			function desativarFiltro() {
				document.querySelector('tbody').setAttribute('maisPje_processosSemAudienciaDesignada_ativado',false);
				let el = document.querySelector('tbody').getElementsByTagName('tr');
				if (!el) { return }
				let cor = 'rgb(240, 240, 240)';
				let map1 = [].map.call(
					el, 
					function(linha) {
						linha.style.setProperty('display', '');
						linha.style.setProperty('background-color', cor);
						cor = (cor == "white") ? 'rgb(240, 240, 240)' : 'white';
					}
				);
				return true;
			}
			
			
		};

		ancora.appendChild(botao);
	}
	
}

//RELATÓRIOS
//TESTE: FUNÇÃO DE TESTE RESPONSÁVEL POR CONTAR QUANTOS PROCESSOS EXISTEM DE ACORDO COM O ÚLTIMO NÚMERO
function relatorioGerencialSecretaria() {
	fundo(true);
	console.log("Extensão maisPJE (" + agora() + "): Relatório Gerencial da Secretaria");	
	var cont01 = 0, cont23 = 0, cont45 = 0, cont67 = 0, cont89 = 0;
	var nomeTabela = "";
	//VERIFICA SE EXISTE TABELA NA PAGINA
	if (document.body.contains(document.getElementsByName('Tabela de Processos')[0]) || document.body.contains(document.getElementsByName('Tabela de Atividades')[0]) || document.body.contains(document.getElementsByName('Tabela Petições')[0])) {
		if (document.body.contains(document.getElementsByName('Tabela de Processos')[0])) {
			nomeTabela = 'Tabela de Processos';
		}
		if (document.body.contains(document.getElementsByName('Tabela de Atividades')[0])) {
			nomeTabela = 'Tabela de Atividades';
		}
		if (document.body.contains(document.getElementsByName('Tabela Petições')[0])) {
			nomeTabela = 'Tabela Petições';
		}
	}
	
	if (nomeTabela != "") {
		if (document.querySelectorAll('th[class="th-class cursor ng-star-inserted"]')) {
			//cria o observador da página para prosseguir apenas após a ordenação pretendida
			let observador1 = new MutationObserver(function(mutations) {
				// console.log(mutations.length); //se a tabela tem 20 linhas, ele contará 40 mutações pq conta quando as linhas removidas, e as linhas adicionadas
				if (mutations.length > 0) {
					monitor();
					observador1.disconnect();
				}
			});		
			observador1.observe(document.querySelector('tbody'), { childList: true });	
			
			//clica no ordenamento por Processo
			setTimeout(function(){document.querySelectorAll('th[class="th-class cursor ng-star-inserted"]')[0].click()}, 500);
		}
		
		// CRIA O MONITOR DA TABELA
		function monitor() {			
			var target = document.getElementsByClassName('total-registros')[0];
			var observer = new MutationObserver(function(mutations) {
				mutations.forEach(function(mutation) {
					if (mutation.type == 'characterData') {
						setTimeout(function(){BuscaLinhas();}, 1000);
					}
				});
			});
			
			var config = { characterData: true, subtree:true };			
			observer.observe(target, config);			
			BuscaLinhas();
			
			function BuscaLinhas() {
				let el = document.getElementsByName(nomeTabela)[0].getElementsByTagName("tbody")[0].rows;
				if (!el) {
					return
				}
				let processoNumero, ano, numero;
				let map = [].map.call(
					el, 
					function(elemento) {
						processoNumero = elemento.cells[1].innerText.match(new RegExp('\\d{7}-\\d{2}\\.\\d{4}\\.\\d{1,2}\\.\\d{1,2}\\.\\d{4}','g')).join();
						numero = processoNumero.substring(0, 7);
						ano = processoNumero.substring(11, 15);
						// console.log(processoNumero + " : " + numero + " : " + ano);
						filtragem(processoNumero, ano, numero);
					}
				);
				
				function filtragem(processoNumero, ano, numero) {
					let filtro;
					if (ano > 2009) {
						filtro =  processoNumero.substring(6, 7);
						if (filtro == 0 || filtro == 1) {
							cont01++;
						} else if (filtro == 2 || filtro == 3) {
							cont23++;
						} else if (filtro == 4 || filtro == 5) {
							cont45++;
						} else if (filtro == 6 || filtro == 7) {
							cont67++;
						} else if (filtro == 8 || filtro == 9) {
							cont89++;
						}
						
					} else {
						filtro =  processoNumero.substring(4, 5);
						if (filtro == 0 || filtro == 1) {
							cont01++;
						} else if (filtro == 2 || filtro == 3) {
							cont23++;
						} else if (filtro == 4 || filtro == 5) {
							cont45++;
						} else if (filtro == 6 || filtro == 7) {
							cont67++;
						} else if (filtro == 8 || filtro == 9) {
							cont89++;
						}
					}
				}
				
				if (document.querySelector('button[aria-label="Próximo"]')) {
					if (document.querySelector('button[aria-label="Próximo"]').getAttribute('disabled')) {
						fundo(false);
						let div = document.createElement("div");
						div.id = "extensaoPje_div";
						div.style = "position: fixed; bottom: 0; display: block; z-index: 1000; width: 100%";
						document.body.appendChild(div);
						let textoarea = document.createElement("textarea");
						textoarea.id = "extensaoPje_textarea";
						textoarea.style = "width: 100%;height: 150px;"
						textoarea.textContent = 'Relatório Gerencial da Secretaria\nTotal: ' + (cont01+cont23+cont45+cont67+cont89) + ' processos\nFinal (0 e 1): ' + cont01 + '\nFinal (2 e 3): ' + cont23 + '\nFinal (4 e 5): ' + cont45 + '\nFinal (6 e 7): ' + cont67 + '\nFinal (8 e 9): ' + cont89;
						div.appendChild(textoarea);
						let botao = document.createElement("button");
						botao.id = "extensaoPje_bt_fechar";
						botao.style = "position: absolute; right: 0px;"
						botao.textContent = "Fechar"
						botao.onclick = function () {div.remove();};	
						div.appendChild(botao);
						
						observer.disconnect();
						
					} else {
						document.querySelector('button[aria-label="Próximo"]').click();											
					}
				}
			}
		}
	}
}

//TESTE: FUNÇÃO DE TESTE RESPONSÁVEL POR CONTAR QUANTOS PROCESSOS EXISTEM DE ACORDO COM A TAREFA DO PROCESSO NO GIGS
function relatorioGerencialExecucao() {
	fundo(true);
	console.log("Extensão maisPJE (" + agora() + "): Relatório Gerencial da Execução");	
	var cont1 = 0, cont2 = 0, cont3 = 0, cont4 = 0, cont5 = 0, cont6 = 0, cont7 = 0, cont8 = 0, cont9 = 0, cont10 = 0, cont11 = 0, cont12 = 0, cont13 = 0;
	
	var nomeTabela = "";
	//VERIFICA SE EXISTE TABELA NA PAGINA
	if (document.body.contains(document.getElementsByName('Tabela de Atividades')[0])) {
		nomeTabela = 'Tabela de Atividades';
	}
	
	if (nomeTabela != "") {
		document.getElementsByClassName('total-registros')[0].setAttribute("id","teta");
		var target = document.getElementById('teta');		
		
		var observer = new MutationObserver(function(mutations) {
			mutations.forEach(function(mutation) {
				setTimeout(function(){
					//console.log(mutation.type);
					BuscaLinhas();
				}, 1000);
			});
		});
		
		var config = { childList: true, characterData: true, subtree:true }
		
		observer.observe(target, config);
		
		//aciona o busca linha
		BuscaLinhas();
	}
	
	function BuscaLinhas() {
		let linhas = document.getElementsByName(nomeTabela)[0].getElementsByTagName("tbody")[0].rows;
		let linhasQuantidade = linhas.length;		
		let tipo, descricao, filtro, linha;
		for(let i=0;i<=linhasQuantidade-1;i++){
			linha = linhas[i];
			tipo = linha.cells[3].innerText;		
			tipo = tipo.split('\n');
			descricao = linha.cells[4].innerText;		
			descricao = descricao.split('\n');	
			filtro = tipo + " : " + descricao;
			filtro = removeAcento(filtro);			
			filtro = filtro.toLowerCase();
			// cont1 = Bacen
			// cont12 = CCS
			// cont2 = Renajud
			// cont3 = Cnib
			// cont4 = Buscar endereço
			// cont5 = serasa			
			// cont6 = RPV/Precatório
			// cont7 = Certidão
			// cont8 = Devolução de GRU			
			// cont9 = Requisição de Honorários
			// cont10 = Outros casos
			// cont11 = Arisp
			// cont13 = Serpro
			
			if (filtro.search("endereco") > -1) {
				cont4++
				// console.log("4: " + filtro);
			} else if (filtro.search("bacen") > -1 || filtro.search("sabb") > -1 || filtro.search("sisbajud") > -1) {
				cont1++
				// console.log("1: " + filtro);
			} else if (filtro.search("ccs") > -1 || filtro.search("css") > -1) {
				cont12++
				// console.log("12: " + filtro);
			} else if (filtro.search("renajud") > -1 || filtro.search("veículo") > -1) {
				cont2++
				// console.log("2: " + filtro);
			} else if (filtro.search("cnib") > -1 || filtro.search("indisponibilidade") > -1) {
				cont3++
				// console.log("3: " + filtro);
			} else if (filtro.search("arisp") > -1 || filtro.search("matricula") > -1) {
				cont11++
				// console.log("11: " + filtro);
			} else if (filtro.search("serpro") > -1) {
				cont13++
				// console.log("13: " + filtro);
			} else if (filtro.search("serasa") > -1) {
				cont5++
				// console.log("5: " + filtro);
			} else if (filtro.search("rpv") > -1 || filtro.search("precatorio") > -1) {
				cont6++
				// console.log("6: " + filtro);
			} else if (filtro.search("certidao") > -1 || filtro.search("protesto") > -1  || filtro.search("habilitacao") > -1) {
				cont7++
				// console.log("7: " + filtro);
			} else if (filtro.search("gru") > -1 || filtro.search("devolucao") > -1 || filtro.search("custas") > -1 || filtro.search("restituicao") > -1) {
				cont8++
				// console.log("8: " + filtro);
			} else if (filtro.search("requisicao") > -1 || filtro.search("honorario") > -1) {
				cont9++
				// console.log("9: " + filtro);
			} else {
				cont10++
				// console.log("10: " + filtro);
			}
		}
		
		if (document.body.contains(document.evaluate('//button[@aria-label="Próximo"]', document, null, XPathResult.ANY_TYPE, null).iterateNext())) {
			if (document.evaluate('//button[@aria-label="Próximo"]', document, null, XPathResult.ANY_TYPE, null).iterateNext().getAttribute('disabled')) {
				// browser.runtime.sendMessage({tipo: 'criarAlerta', valor: 'Relatório Gerencial da Execução\nTotal: ' + (cont1+cont2+cont3+cont4+cont5+cont6+cont7+cont8+cont9+cont10+cont11+cont12) + ' processos\nBacen: ' + cont1 + '\nCCS: ' + cont12 + '\nRenajud: ' + cont2 + '\nCnib: ' + cont3 + '\nArisp: ' + cont11 + '\nEndereço: ' + cont4 + '\nSerasa: ' + cont5 + '\nRPV/Prec: ' + cont6 + '\nCertidão: ' + cont7 + '\nGRU: ' + cont8 + '\nHonorários: ' + cont9 + '\nOutros: ' + cont10, icone: '5'});
				
				//Exibe na tela os resultados
				fundo(false);
				var elemento = document.createElement("div");
				elemento.id = "extensaoPje_div";
				elemento.style = "position: fixed; bottom: 0; display: block; z-index: 1000; width: 100%";
				document.body.appendChild(elemento);
				var elemento2 = document.createElement("textarea");
				elemento2.id = "extensaoPje_textarea";
				elemento2.style = "width: 100%;height: 225px;"
				elemento2.textContent = 'Relatório Gerencial da Execução\nTotal: ' + (cont1+cont2+cont3+cont4+cont5+cont6+cont7+cont8+cont9+cont10+cont11+cont12+cont13) + ' processos\nBacen: ' + cont1 + '\nCCS: ' + cont12 + '\nRenajud: ' + cont2 + '\nCnib: ' + cont3 + '\nArisp: ' + cont11 + '\nEndereço: ' + cont4 + '\nSerpro: ' + cont13 + '\nSerasa: ' + cont5 + '\nRPV/Prec: ' + cont6 + '\nCertidão: ' + cont7 + '\nGRU: ' + cont8 + '\nHonorários: ' + cont9 + '\nOutros: ' + cont10;
				elemento.appendChild(elemento2);
				var elemento3 = document.createElement("button");
				elemento3.id = "extensaoPje_bt_fechar";
				elemento3.style = "position: absolute; right: 0px;"
				elemento3.textContent = "Fechar"
				elemento3.onclick = function () {elemento.remove();};	
				elemento.appendChild(elemento3);
				
				observer.disconnect();
			} else {					
				// console.log(document.getElementsByClassName('total-registros')[0].innerText);
				document.evaluate('//button[@aria-label="Próximo"]', document, null, XPathResult.ANY_TYPE, null).iterateNext().click();											
			}
		}
	}
}

//TESTE: FUNÇÃO DE TESTE RESPONSÁVEL POR CONTAR QUANTOS PROCESSOS EXISTEM DE ACORDO COM A TAREFA DO PROCESSO NO GIGS
function relatorioGerencialContadoria() {
	fundo(true);
	console.log("Extensão maisPJE (" + agora() + "): Relatório Gerencial da Contadoria");	
	var cont1 = 0, cont2 = 0, cont3 = 0, cont4 = 0, cont5 = 0;
	
	var nomeTabela = "";
	//VERIFICA SE EXISTE TABELA NA PAGINA
	if (document.body.contains(document.getElementsByName('Tabela de Atividades')[0])) {
		nomeTabela = 'Tabela de Atividades';
	}
	
	if (nomeTabela != "") {
		document.getElementsByClassName('total-registros')[0].setAttribute("id","teta");
		var target = document.getElementById('teta');		
		
		var observer = new MutationObserver(function(mutations) {
			mutations.forEach(function(mutation) {
				setTimeout(function(){
					//console.log(mutation.type);
					BuscaLinhas();
				}, 1000);
			});
		});
		
		var config = { childList: true, characterData: true, subtree:true }
		
		observer.observe(target, config);
		
		//aciona o busca linha
		BuscaLinhas();
	}
	
	function BuscaLinhas() {		
		let linhas = document.getElementsByName(nomeTabela)[0].getElementsByTagName("tbody")[0].rows;
		let linhasQuantidade = linhas.length;		
		let tipo, descricao, filtro, linha;				
		
		for(let i=0;i<=linhasQuantidade-1;i++){
			linha = linhas[i];
			tipo = linha.cells[3].innerText;		
			tipo = tipo.split('\n');
			descricao = linha.cells[4].innerText;		
			descricao = descricao.split('\n');	
			filtro = tipo + " : " + descricao;
			filtro = removeAcento(filtro);			
			filtro = filtro.toLowerCase();
			
			// cont1 = Alvará
			// cont2 = Atualização
			// cont3 = Análise
			// cont4 = Reunião
			// cont5 = Outros casos
			
			
			if (filtro.search("alvara") > -1 || filtro.search("liberacao") > -1 || filtro.search("liberar") > -1) {
				cont1++
				// console.log("1: " + filtro);
			} else if (filtro.search("atualiza") > -1 || filtro.search("calculo") > -1 || filtro.search("incluir") > -1 || filtro.search("apura") > -1) {
				cont2++
				// console.log("2: " + filtro);
			} else if (filtro.search("analis") > -1 || filtro.search("verifi") > -1 || filtro.search("confer") > -1) {
				cont3++
				// console.log("3: " + filtro);
			} else if (filtro.search("reuni") > -1) {
				cont4++
				// console.log("4: " + filtro);
			} else {
				cont5++
				// console.log("5: " + filtro);
			}
		}
		
		if (document.body.contains(document.evaluate('//button[@aria-label="Próximo"]', document, null, XPathResult.ANY_TYPE, null).iterateNext())) {
			if (document.evaluate('//button[@aria-label="Próximo"]', document, null, XPathResult.ANY_TYPE, null).iterateNext().getAttribute('disabled')) {
				// browser.runtime.sendMessage({tipo: 'criarAlerta', valor: 'Total: ' + (cont1+cont2+cont3+cont4+cont5) + '\nAlvará: ' + cont1 + '\nAtualização: ' + cont2 + '\nAnálise: ' + cont3 + '\nReunião: ' + cont4 + '\nOutros: ' + cont5, icone: '5'});
				
				//Exibe na tela os resultados
				fundo(false);				
				var elemento = document.createElement("div");
				elemento.id = "extensaoPje_div";
				elemento.style = "position: fixed; bottom: 0; display: block; z-index: 1000; width: 100%";
				document.body.appendChild(elemento);
				var elemento2 = document.createElement("textarea");
				elemento2.id = "extensaoPje_textarea";
				elemento2.style = "width: 100%;height: 150px;"
				elemento2.textContent = 'Relatório Gerencial da Contadoria\nTotal: ' + (cont1+cont2+cont3+cont4+cont5) + ' processos\nAlvará: ' + cont1 + '\nAtualização: ' + cont2 + '\nAnálise: ' + cont3 + '\nReunião: ' + cont4 + '\nOutros: ' + cont5;
				elemento.appendChild(elemento2);
				var elemento3 = document.createElement("button");
				elemento3.id = "extensaoPje_bt_fechar";
				elemento3.style = "position: absolute; right: 0px;"
				elemento3.textContent = "Fechar"
				elemento3.onclick = function () {elemento.remove();};	
				elemento.appendChild(elemento3);					
				
				observer.disconnect();
			} else {					
				// console.log(document.getElementsByClassName('total-registros')[0].innerText);
				document.evaluate('//button[@aria-label="Próximo"]', document, null, XPathResult.ANY_TYPE, null).iterateNext().click();											
			}
		}
	}
}

async function verificarVersoesPjeTRTs() {
	let pjeTRTs = {
		'trt1':'',
		'trt2':'',
		'trt3':'',
		'trt4':'',
		'trt5':'',
		'trt6':'',
		'trt7':'',
		'trt8':'',
		'trt9':'',
		'trt10':'',
		'trt11':'',
		'trt12':'',
		'trt13':'',
		'trt14':'',
		'trt15':'',
		'trt16':'',
		'trt17':'',
		'trt18':'',
		'trt19':'',
		'trt20':'',
		'trt21':'',
		'trt22':'',
		'trt23':'',
		'trt24':'',		
	}
	
	let v = '';
	browser.storage.onChanged.addListener(logStorageChange);
	
	for (const [key, value] of Object.entries(pjeTRTs)) {
		let winGigs = window.open('https://pje.' + key + '.jus.br/primeirograu/login.seam', '_blank');
		let versaoDaqueleTRT = await aguardandoVersao();
		v = '';
		pjeTRTs[key] = versaoDaqueleTRT;
		winGigs.close();
	}
	
	
	let mensagem = '';
	for (const [key, value] of Object.entries(pjeTRTs)) {
		mensagem = mensagem + key + " : " + value + "\n";
	}
	
	criarCaixaDeAlerta("ERRO",mensagem);
	
	function logStorageChange(changes, area) {
		let changedItems = Object.keys(changes);
		for (let item of changedItems) {
			if (item == "versaoPje") {
				v = changes[item].newValue;
			}
		}
	}
	
	function aguardandoVersao() {
		return new Promise(resolve => {
			let check = setInterval(function() {
				if (v) {
					clearInterval(check);
					return resolve(v);
				}
			}, 100);
		});
	}
}

async function listaProcessoParaAcoesEmLote(listaPronta) {
	return new Promise(
		resolver => {
			console.log("      |___maisPJe: acoesacoesEmLoteContainer");
			
			if (document.querySelector('maisPje_aaLote_lista_processos')) { return }
			
			let altura = window.innerHeight || document.documentElement.clientHeight || document.body.clientHeight;
			let elemento1 = document.createElement("div");
			elemento1.id = 'maisPje_aaLote_lista_processos';
			elemento1.style = 'position: fixed; width: 100%; height: ' + altura + 'px; top: 0; inset: 0px; background: #00000080; z-index: 10000; display: flex; align-items: center; justify-content: center; color: rgb(81, 81, 81); font-weight: bold; font-family: Open Sans,Arial,Verdana,sans-serif; text-align: center; flex-direction: column;';
			
			elemento1.onclick = function (e) {
				if (e.target.id == "maisPje_aaLote_lista_processos") {
					elemento1.remove();
				}
			}; //se clicar fora fecha a janela
			
			let container = document.createElement("div");
			container.style="height: auto; min-width: 35vw; display: inline-grid; background-color: white;padding: 15px;border-radius: 4px;box-shadow: 0 2px 1px -1px rgba(0,0,0,.2),0 1px 1px 0 rgba(0,0,0,.14),0 1px 3px 0 rgba(0,0,0,.12);";
			
			let titulo = document.createElement("span");
			titulo.style = "color: grey; border-bottom: 1px solid lightgrey;";
			titulo.innerText = "Lista de Processos para Ação Automatizada em lote";
			container.appendChild(titulo);
			
			let lista_processos = document.createElement('textarea');
			lista_processos.id = '';
			lista_processos.placeholder = '\n\nDigite ou cole a sua lista de processos aqui.\n\nOs números devem estar no padrão CNJ.\n\nNão importa se eles estão sozinhos ou misturados com outras palavras de texto.\n\nAo clicar em "CONTINUAR" a extensão irá encontrar os números dos processos no texto e criará uma lista.\n\nApenas os processos que fazem parte dessa nova lista é que serão utilizados para a ação automatizada em lote.\n\nBom proveito!'
			// lista_processos.value = (listaPronta) ? listaPronta : '';
			lista_processos.value = (listaPronta) ? listaPronta : '';
			lista_processos.style = 'width: 100%; height: 80vh;';
			container.appendChild(lista_processos);
			
			let bt_continuar = document.createElement("span");
			bt_continuar.style = "color: white; margin-top: 10px; padding: 10px; border-bottom: 1px solid lightgrey; background-color: #7a9ec8; border-radius: 3px; cursor: pointer;";
			bt_continuar.innerText = "Continuar";
			bt_continuar.onmouseenter = function () {
				bt_continuar.style.backgroundColor  = '#5077a4';
			};
			bt_continuar.onmouseleave = function () {
				bt_continuar.style.backgroundColor  = '#7a9ec8';
			};
			bt_continuar.onclick = function () {
				let lista = lista_processos.value.match(new RegExp('\\d{7}-\\d{2}\\.\\d{4}\\.\\d{1,2}\\.\\d{1,2}\\.\\d{4}','gm')).join();
				resolver(lista.split(','));
				document.getElementById('maisPje_aaLote_lista_processos').remove();
			};
			container.appendChild(bt_continuar);
			elemento1.appendChild(container);
			document.body.appendChild(elemento1);
			lista_processos.focus();
			if (listaPronta) { bt_continuar.click() }
		}
	);
}

async function acoesEmLote(listaPronta) {
	console.debug("      |___maisPJe: acoesEmLote");
	let guardarStorage1 = browser.storage.local.set({'AALote': ''});
	let guardarStorage2 = browser.storage.local.set({'erros': ''});
	Promise.all([guardarStorage1,guardarStorage2]).then(values => {
		if (!document.getElementById('maisPje_caixa_de_selecao_AALote')) { iniciar(listaPronta) }
	});
	
	async function iniciar(listaPronta) {
		let lista = await listaProcessoParaAcoesEmLote(listaPronta);
		if (!lista || lista.length == 0) { return }
		
		let listaDeProcessos = [];
		
		fundo(true);
		for (const [pos, numeroProcesso] of lista.entries()) {
			let idProcesso = await obterIdProcessoViaApiPublica(numeroProcesso);
			if (!idProcesso) { 	idProcesso = await obterIdProcessoViaApi(numeroProcesso) }
			listaDeProcessos.push({id:idProcesso[0]?.id,numero:numeroProcesso});
		}
		fundo(false);
		
		if (listaDeProcessos.length == 0) { return }
		
		let listaDeProcessosTemp = [];
		
		// DESCRIÇÃO: REGRA DO TOOLTIP
		if (!document.getElementById('maisPje_tooltip_fundo')) {
			tooltip('fundo', true);
		}
		
		let altura = window.innerHeight || document.documentElement.clientHeight || document.body.clientHeight;
		
		let elemento1 = document.createElement("div");
		elemento1.id = 'maisPje_caixa_de_selecao_AALote';
		elemento1.style = 'position: fixed; width: 100%; height: ' + altura + 'px; top: 0; inset: 0px; background: #00000080; z-index: 10000; display: flex; align-items: center; justify-content: center; color: rgb(81, 81, 81); font-weight: bold; font-family: Open Sans,Arial,Verdana,sans-serif; text-align: center; flex-direction: column;';
		
		elemento1.onclick = function (e) {
			if (e.target.id == "maisPje_caixa_de_selecao_AALote") {
				elemento1.remove();
			} else if (e.target.id.includes('_copiarLista')) {
				let textocopiado = elemento1.innerText.match(new RegExp('\\d{7}-\\d{2}\\.\\d{4}\\.\\d{1,2}\\.\\d{1,2}\\.\\d{4}','gm')).join();
				// let ta = document.createElement("textarea");
				// ta.textContent = textocopiado;
				// document.body.appendChild(ta);
				// ta.select();
				// document.execCommand("copy");
				navigator.clipboard.writeText(textocopiado);
				browser.runtime.sendMessage({tipo: 'criarAlerta', valor: '\n Conteúdo copiado com sucesso!', icone: '3'});
			}
		}; //se clicar fora fecha a janela
		
		let container = document.createElement("div");
		container.style="max-height: 90%; min-width: 35vw; display: inline-grid; background-color: white;padding: 15px;border-radius: 4px;box-shadow: 0 2px 1px -1px rgba(0,0,0,.2),0 1px 1px 0 rgba(0,0,0,.14),0 1px 3px 0 rgba(0,0,0,.12); overflow: auto;";
		
		//BOTAO COPIAR LISTA PARA A MEMORIA
		let btCopiarLista = document.createElement("span");
		btCopiarLista.id = 'maisPje_bt_copiarLista';
		btCopiarLista.style = "position: absolute;";
		btCopiarLista.title = "Copiar lista";
		btCopiarLista.onmouseenter = function () {document.getElementById('maisPje_i_copiarLista').style.filter = 'brightness(0.5)'};
		btCopiarLista.onmouseleave = function () {document.getElementById('maisPje_i_copiarLista').style.filter = 'brightness(1)'};			
		
		let iCopiarLista = document.createElement("i");
		iCopiarLista.id = 'maisPje_i_copiarLista';
		iCopiarLista.className = 'icone copy-solid t18';
		iCopiarLista.style.backgroundColor = "lightgray";		
		btCopiarLista.appendChild(iCopiarLista);
		container.appendChild(btCopiarLista);
		
		
		let titulo = document.createElement("span");
		titulo.id = "maisPje_caixa_de_selecao_titulo";
		titulo.style = "color: grey; border-bottom: 1px solid lightgrey;";
		titulo.innerText = "maisPje: Ações Automatizadas em lote (" + listaDeProcessos.length + ")";
		container.appendChild(titulo);
		
		let selectAcaoAutomatizada = document.createElement("select");
		selectAcaoAutomatizada.style = 'cursor: pointer; margin-top: 10px; padding: 10px; background-color: cornsilk; color: rgb(81, 81, 81); min-height: 40px;';
		
		//OPÇÃO NENHUM
		let optionSelecione = document.createElement("option");
		optionSelecione.innerText = 'Selecione uma Ação Automatizada';
		optionSelecione.value = '';
		selectAcaoAutomatizada.appendChild(optionSelecione);
		
		//monta as acoes automatizadas de Anexar Documentos
		for (const [pos, item] of preferencias.aaAnexar.entries()) {
			let optionAAA = document.createElement("option");
			optionAAA.style.backgroundColor = 'white';			
			optionAAA.value = 'Anexar|' + item.nm_botao;
			optionAAA.innerText = 'Anexar|' + item.nm_botao;
			selectAcaoAutomatizada.appendChild(optionAAA);
		}
		//monta as acoes automatizadas de Comunicação
		for (const [pos, item] of preferencias.aaComunicacao.entries()) {
			let optionAAC = document.createElement("option");
			optionAAC.style.backgroundColor = 'rgba(122, 158, 200, 0.44)';
			optionAAC.value = 'Comunicação|' + item.nm_botao;
			optionAAC.innerText = 'Comunicação|' + item.nm_botao;
			selectAcaoAutomatizada.appendChild(optionAAC);
		}
		//monta as acoes automatizadas de Autogigs
		for (const [pos, item] of preferencias.aaAutogigs.entries()) {
			let optionAAG = document.createElement("option");
			optionAAG.style.backgroundColor = 'white';
			optionAAG.value = 'AutoGigs|' + item.nm_botao;
			optionAAG.innerText = 'AutoGigs|' + item.nm_botao;
			selectAcaoAutomatizada.appendChild(optionAAG);
		}
		//monta as acoes automatizadas de Despacho
		for (const [pos, item] of preferencias.aaDespacho.entries()) {
			let optionAAD = document.createElement("option");
			optionAAD.style.backgroundColor = 'rgba(122, 158, 200, 0.44)';
			optionAAD.value = 'Despacho|' + item.nm_botao;
			optionAAD.innerText = 'Despacho|' + item.nm_botao;
			selectAcaoAutomatizada.appendChild(optionAAD);
		}

		//AA de Movimento > atualizar data DESDE na tarefa		
		let optionAAM = document.createElement("option");
		optionAAM.style.backgroundColor = 'white';
		optionAAM.value = 'Movimento|bt_atualizar_tarefa';
		optionAAM.innerText = '>>>Movimento|Renovar a Data na Tarefa';
		selectAcaoAutomatizada.appendChild(optionAAM);

		//monta as acoes automatizadas de Movimento
		for (const [pos, item] of preferencias.aaMovimento.entries()) {
			optionAAM = document.createElement("option");
			optionAAM.style.backgroundColor = 'white';
			optionAAM.value = 'Movimento|' + item.nm_botao;
			optionAAM.innerText = 'Movimento|' + item.nm_botao;
			selectAcaoAutomatizada.appendChild(optionAAM);
		}
		
		//monta as acoes automatizadas de Checklist
		for (const [pos, item] of preferencias.aaChecklist.entries()) {
			let optionAACh = document.createElement("option");			
			optionAACh.style.backgroundColor = 'white';
			optionAACh.value = 'Checklist|' + item.nm_botao;
			optionAACh.innerText = 'Checklist|' + item.nm_botao;
			selectAcaoAutomatizada.appendChild(optionAACh);
		}
				
		let aaItemRetificarAutuacao = [['botao_retificar_autuacao_7','addAutor'],['botao_retificar_autuacao_8','addRéu'],['botao_retificar_autuacao_0','addUnião'],['botao_retificar_autuacao_10','addMPT'],['botao_retificar_autuacao_3','addLeiloeiro'],['botao_retificar_autuacao_4','addPerito'],['botao_retificar_autuacao_addTerceiroTerceiro','Terceiro>Terceiro'],['botao_retificar_autuacao_100Digital','Juízo 100% Digital'],['botao_retificar_autuacao_tutelaLiminar','Pedido de Tutela'],['botao_retificar_autuacao_Falencia','Falência/Rec.Judicial'],['botao_retificar_autuacao_assunto','Assunto'],['botao_retificar_autuacao_justicaGratuita','Justiça Gratuita']];

		[].map.call(aaItemRetificarAutuacao,function(item) {
			let optionIRA = document.createElement("option");
			optionIRA.style.backgroundColor = 'white';
			optionIRA.value = 'RetificarAutuação|' + item[0];
			optionIRA.innerText = 'RetificarAutuação|' + item[1];
			selectAcaoAutomatizada.appendChild(optionIRA);
		});

		let aaItemLancarMovimentos = [['botao_lancar_movimento_0','Contadoria:atualização'],['botao_lancar_movimento_1','Contadoria:liquidação'],['botao_lancar_movimento_2','Contadoria:retificação'],['botao_lancar_movimento_3','Contadoria:DeterminaçãoJudicial'],['botao_lancar_movimento_4','TRT:recurso'],['botao_lancar_movimento_5','Publicação de Pauta']];
			[].map.call(aaItemLancarMovimentos,function(item) {
			let optionILM = document.createElement("option");
			optionILM.style.backgroundColor = 'rgba(122, 158, 200, 0.44)';
			optionILM.value = 'LançarMovimento|' + item[0];
			optionILM.innerText = 'LançarMovimento|' + item[1];
			selectAcaoAutomatizada.appendChild(optionILM);
		});

		let aaItemMenuDetalhes = ['Reprocessar chips do processo','Download do processo completo'];
			[].map.call(aaItemMenuDetalhes,function(item) {
			let optionIMD = document.createElement("option");
			optionIMD.style.backgroundColor = 'white';
			optionIMD.value = 'Clicar em|' + item;
			optionIMD.innerText = 'Clicar em|' + item;
			selectAcaoAutomatizada.appendChild(optionIMD);
		});
		
		let aaVariados = ['Atualizar Pagina|Atualizar Pagina','Fechar Pagina|Fechar Pagina','Variados|Apreciar Peticoes'];
			[].map.call(aaVariados,function(item) {
			let optionVar = document.createElement("option");
			optionVar.style.backgroundColor = 'rgba(122, 158, 200, 0.44)';
			optionVar.value = item;
			optionVar.innerText = item;
			selectAcaoAutomatizada.appendChild(optionVar);
		});
		
		let bt_executar = document.createElement("span");
		bt_executar.style = "color: white; margin-top: 10px; padding: 10px; border-bottom: 1px solid lightgrey; background-color: #7a9ec8; border-radius: 3px; cursor: pointer;";
		bt_executar.id = "maisPje_bt_executar";
		bt_executar.innerText = "Executar";
		bt_executar.onmouseenter = function () {
			bt_executar.style.backgroundColor  = '#5077a4';
		};
		bt_executar.onmouseleave = function () {
			bt_executar.style.backgroundColor  = '#7a9ec8';
		};
		bt_executar.onclick = function () {
			if (this.innerText == "Executar") {
				let guardarStorage = browser.storage.local.set({'erros': ''});
				Promise.all([guardarStorage]).then(values => {
					if (selectAcaoAutomatizada.value == "RetificarAutuação|botao_retificar_autuacao_assunto") {
						preferencias.tempAR = prompt('Código Assunto:','');
					} else if (selectAcaoAutomatizada.value == "LançarMovimento|botao_lancar_movimento_4") {
						preferencias.tempAR = prompt('Data da Publicação:','');
					}
					executarAAEmLote([listaDeProcessosTemp,selectAcaoAutomatizada.value]);
				});				
			} else if (this.innerText.includes("Continuar"))  {
				[].map.call(document.querySelectorAll('span[id*="maisPje_AALote_"]'),function(item) {
					item.style.textDecoration = 'none';
					item.innerText = item.innerText.replace(' [erro]','');
				});
				this.innerText = "Executar";
			}
		};
		
		container.appendChild(selectAcaoAutomatizada);
		container.appendChild(bt_executar);
		
		for (const [pos, processo] of listaDeProcessos.entries()) {
			// if (pos == 5) { break } //testes
			let span = document.createElement("span");
			span.id = 'maisPje_AALote_' + processo.id;
			span.style = "cursor: pointer; margin-top: 10px; padding: 10px; color:rgb(81, 81, 81); border-radius: 3px;  display: grid; grid-template-columns: 1fr;}";
			span.innerText = processo.numero;
			span.setAttribute('labelAnterior','');
			span.onmouseenter = async function () {
				this.style.setProperty('grid-template-columns','2fr 2fr 2fr 1fr');
				this.style.filter = 'brightness(.5)';
				this.setAttribute('labelAnterior',span.innerText)
				this.innerText = '';
				let atalho1 = document.createElement("a");
				atalho1.innerText = 'Excluir da Lista';
				atalho1.onmouseenter = function () { this.style.color = 'white'; this.style.outline = '1px dashed silver'; }
				atalho1.onmouseleave = function () { this.style.color = 'rgb(81, 81, 81)'; this.style.outline = 'unset'; }
				atalho1.onclick = function () {
					this.parentElement.remove();
					listaDeProcessosTemp.splice(listaDeProcessosTemp.findIndex(e => e.id === processo.id), 1);					
					let tituloTotal = document.getElementById('maisPje_caixa_de_selecao_titulo');
					tituloTotal.innerText = titulo.innerText.replace(new RegExp(/\d{1,}/gm), listaDeProcessosTemp.length);
				};
				let atalho2 = document.createElement("a");
				atalho2.style = 'padding-left:20px;padding-right:20px;';
				atalho2.innerText = 'Abrir Detalhes';
				atalho2.onmouseenter = function () { this.style.color = 'white'; this.style.outline = '1px dashed silver'; }
				atalho2.onmouseleave = function () { this.style.color = 'rgb(81, 81, 81)'; this.style.outline = 'unset';  }
				atalho2.onclick = function () {
					this.parentElement.style.outline = '1px dashed black';
					consultaRapidaPJE(processo.numero);
				};
				let atalho3 = document.createElement("a");
				atalho3.style = 'padding-right:20px;';
				atalho3.innerText = 'Abrir Tarefa';
				obterTarefaIdProcessoViaApi(processo.id).then(async resultado => {
					if (resultado == "Aguardando final do sobrestamento") {
						let motivo = await obterMotivoSobrestamentoViaApi(processo.id);
						atalho3.title = resultado + '(' + motivo + ')';;
					} else {
						atalho3.title = resultado;
					}
				});
				atalho3.onmouseenter = function () { this.style.color = 'white'; this.style.outline = '1px dashed silver'; }
				atalho3.onmouseleave = function () { this.style.color = 'rgb(81, 81, 81)'; this.style.outline = 'unset';  }
				atalho3.onclick = function () {
					this.parentElement.style.outline = '1px dashed black';
					abrirTarefaDoProcesso(processo.id);
				};
				
				let atalho4 = document.createElement("span");
				let atalho4_i = document.createElement("i");
				atalho4_i.className = 'fa fa-tag icone-padrao';				
				obterGIGSIdProcessoViaApi(processo.id).then(resultado => {
					let msg = '';
					let statusVencimento = false;
					for (const [pos, item] of resultado.entries()) {
						if (pos > 0) { msg += '\n\n' }						
						msg += String.fromCharCode(187) + '';
						if (item.statusAtividade == 'Vencido') { 
							msg += '[vencido] : ' + item.dataPrazo;
							// atalho4_i.style.color = '#ff0f31';
							statusVencimento = true
						}
						if ((item.statusAtividade == 'No Prazo' || item.statusAtividade == 'A Vencer') && item.dataPrazo) {	
							msg += '[no prazo] : ' + item.dataPrazo + ' ' + item.tipoAtividade;
							atalho4_i.style.color = 'lime';	
						}
						
						if (item.statusAtividade == 'No Prazo' && !item.dataPrazo) {
							 msg += '[atividade] : ' + item.tipoAtividade 
							 atalho4_i.style.color = '#0087ff';
						}

						msg += item.observacao ? ' - ' + item.observacao : '';
					}

					if (statusVencimento) { //a cor do prazo vencido (vermelho) prevalece sobre as demais caso exista um gigs com prazo vencido
						atalho4_i.style.color = '#ff0f31';
					}

					atalho4.title = msg;				
				});
				atalho4.onmouseenter = function () { this.style.outline = '1px dashed silver'; }
				atalho4.onmouseleave = function () { this.style.outline = 'unset'; }
				atalho4.appendChild(atalho4_i);
				
				span.appendChild(atalho1);
				span.appendChild(atalho2);
				span.appendChild(atalho3);
				span.appendChild(atalho4);
			};
			span.onmouseleave = function () {
				this.style.filter = 'brightness(1)';
				this.style.setProperty('grid-template-columns','1fr');
				this.innerText = this.getAttribute('labelAnterior');
			};
			
			obterFaseIdProcessoViaApi(processo.id).then(resultado => {
				switch(resultado) {
					case 'CONHECIMENTO':
						span.style.borderRight = '35px solid rgba(179, 229, 252)';
						span.style.backgroundColor = 'rgba(179, 229, 252, .3)';
						span.title = 'Conhecimento';
						break;
					case 'LIQUIDACAO':
						span.style.borderRight = '35px solid rgba(174, 213, 129)';
						span.style.backgroundColor = 'rgba(174, 213, 129, .3)';
						span.title = 'Liquidação';
						break;
					case 'EXECUCAO':
						span.style.borderRight = '35px solid rgba(138, 138, 138)';
						span.style.backgroundColor = 'rgba(138, 138, 138, .3)';
						span.title = 'Execução';
						break;
					case 'ARQUIVADO':
						span.style.borderRight = '35px solid rgba(186, 104, 200)';
						span.style.backgroundColor = 'rgba(186, 104, 200, .3)';
						span.title = 'Arquivado';
						break;
				}
			});
			
			container.appendChild(span);			
			listaDeProcessosTemp.push({ id: processo.id, numero: processo.numero });
		}
		
		elemento1.appendChild(container);
		document.body.appendChild(elemento1);		
	}
	
	async function executarAAEmLote(listaDeProcessosParaAcaoAutomatizadaEmLote) {
		
		for (const [pos, processo] of listaDeProcessosParaAcaoAutomatizadaEmLote[0].entries()) {
			// console.log(processo.numero + " (" + processo.id + ")");
			await sleep(preferencias.maisPje_velocidade_interacao);
			await lancarNovoProcesso(listaDeProcessosParaAcaoAutomatizadaEmLote[1], processo.id);
		}
		console.debug("      |___maisPJe: FIM de acoesEmLote");
		
		let guardarStorage = browser.storage.local.set({'tempAR': ''});
		Promise.all([guardarStorage]).then(values => {
			let var1 = browser.storage.local.get('erros', function(result){
				if ((result.erros.length > 0)) {
					console.log('result.erros: ' + result.erros.toString());
					criarCaixaDeAlerta("ERRO",'Identificado erro durante o Lote. Verifique a lista');
				}
			});
		});
		
		
		
		
	}
	
	function aguardandoFimAAEmLote() {
		return new Promise(resolve => {
			// console.log('--------------------aguardandoFimAAEmLote');
			let verificador = false;
			browser.storage.onChanged.addListener(logStorageChange);
			let check = setInterval(function() {
				// console.log('--------------------verificador: ' + verificador);
				if (verificador) {
					clearInterval(check);
					browser.storage.onChanged.removeListener(logStorageChange);
					return resolve(true);
				}
			}, 1000);
			
			function logStorageChange(changes, area) {
				let changedItems = Object.keys(changes);
				for (let item of changedItems) {
					// console.log('-------------------' + item + ' : ' + changes[item].newValue)
					if (item == "AALote") {
						verificador = true;
					}
				}
			}
			
		});
	}
	
	async function lancarNovoProcesso(AALote, idProcesso) {
		return new Promise(resolve => {
			let guardarStorage1 = browser.storage.local.set({'AALote': AALote});
			let guardarStorage2 = browser.storage.local.set({'tempAR': preferencias.tempAR}); //uso para levar o código do assunto da AA de Retificar Autuação
			Promise.all([guardarStorage1,guardarStorage2]).then(async values => {
				let url = 'https://' + preferencias.trt + '/pjekz/processo/' + idProcesso + '/detalhe'
				let winGigs = window.open(url, '_blank');
				let aguardandoFimDaAA = await aguardandoFimAAEmLote();
				winGigs.close();
				let el = await esperarElemento('span[id*="maisPje_AALote_' + idProcesso + '"]');
				
				let var1 = browser.storage.local.get('erros', function(result){
					let errosEncontrados = result.erros;
					errosEncontrados = (errosEncontrados.length > 0) ? errosEncontrados : '';
					if (errosEncontrados.includes(el.innerText)) {
						el.style.color = 'red';
						el.innerText = el.innerText + " [erro]";	
					} else {
						el.style.textDecoration = 'line-through';
					}
					el.scrollIntoView({behavior: 'auto',block: 'center',inline: 'center'});
					return resolve(true);
				});
			});
		});
	}

}

//FUNÇÃO PARA CRIAR A JANELA COM NÚMERO DE PROCESSOS DE ACORDO COM UMA LISTA
async function janelaAlvarasSIF(tipo) {
	fundo(true,'PESQUISANDO ALVARÁS ' + tipo);
	let listaTemporaria = await obterAlvarasTipo(tipo);
	if (listaTemporaria.length < 1) { 
		fundo(false);
		criarCaixaDeAlerta("ALERTA",'Nenhum alvará encontrado na situação ' + tipo);
		return;
	}
	let result = await mapTratarDados(listaTemporaria);
	let html = await createTable(result);
	prepararEAbrirArquivo('ALVARÁS ' + tipo + ' - Total: ' + listaTemporaria.length, html.outerHTML);
	fundo(false);	
	
	async function createTable(children, titulo) {
		let tabela = document.createElement('table');
		
		//cria o cabeçalho
		let chaves_cabecalho = Object.keys(children[0]);
		criarCabecalho();
		
		//cria o tbody
		let tbody = tabela.createTBody();
		// insere as linhas no tbody
		
		for(let i = 0; i < children.length; i++) {
			let child = children[i];
			let linha = tbody.insertRow();
			let processo = child.processo || '';
			let processoFormatado = numeroProcessoFormatado(processo);			
			let banco = child.banco || '';
			let beneficiario = child.beneficiario || '';
			let conteudoComprovante = child.conteudoComprovante || '';
			let tipo = child.tipo || '';
			let valor = child.valor || '';
			let situacao = child.situacao || '';
			let data = child.data || '';
			let conta = child.conta || '';
			let identificador = await obterIdProcessoViaApi(processoFormatado);
			
			linha.insertCell().appendChild(document.createTextNode(banco)); //coluna 0
			linha.insertCell().appendChild(document.createTextNode(beneficiario)); //coluna 1
			
			let tp = document.createElement('span');
			tp.style = "font-size: 1em;padding: .5em;border-radius: .5em;font-weight: bold;";
			if (tipo == 'TRANSFERENCIA_BENEFICIARIO') {
				tp.innerText = 'TED'
				tp.style.backgroundColor = 'gold';				
			} else if (tipo == 'RECOLHIMENTO_DARF') {
				tp.innerText = 'DARF'
				tp.style.backgroundColor = 'cadetblue';
			} else if (tipo == 'RECOLHIMENTO_GRU') {
				tp.innerText = 'GRU'
				tp.style.backgroundColor = 'darkorange';
			} else if (tipo == 'RECOLHIMENTO_GPS') {
				tp.innerText = 'GPS'
				tp.style.backgroundColor = 'burlywood';
			} else {
				tp.innerText = 'OUTROS'
				tp.style.backgroundColor = 'plum';
			}
			linha.insertCell().appendChild(tp); //coluna 2
			linha.insertCell().appendChild(document.createTextNode(data)); //coluna 3
			linha.insertCell().appendChild(document.createTextNode(valor)); //coluna 4	
						
			let a2 = document.createElement('a');
			a2.href = 'https://' + preferencias.trt + '/sif/alvara/incluir/' + processo + '/104/' + conta + '?conferir';			
			a2.setAttribute('onclick','this.parentElement.parentElement.style.backgroundColor = "skyblue";this.style.textDecoration = "line-through";');
			a2.setAttribute('target', '_blank');
			a2.innerText = conta;
			
			if (conteudoComprovante) {
				let linkfr = document.createElement('div');
				linkfr.style.display = 'none';
				let fr = document.createElement('iframe');
				fr.style = 'position: fixed; background-color: white; border: medium none;  width: 34vw; height: 90vh; transform: scale(0.8); top: 7vh;left: 5vw;outline: rgba(0, 0, 0, 0.5) solid 12vw;';
				fr.srcdoc = conteudoComprovante;
				linkfr.appendChild(fr);					
				a2.appendChild(linkfr);
				
				a2.setAttribute('onmouseover','this.firstElementChild.style.display = "unset";');
				a2.setAttribute('onmouseout','this.firstElementChild.style.display = "none";');
			}
			
			linha.insertCell().appendChild(a2); //coluna 4
			
			let a1 = document.createElement('a');			
			if (identificador[0]?.idProcesso) {
				a1.id = identificador[0].idProcesso;
				a1.href = 'https://' + preferencias.trt + '/pjekz/processo/' + identificador[0].idProcesso + '/detalhe';
				a1.setAttribute('target', '_blank');
			} else {
				a1.id = 'numeroProcesso:' + processoFormatado;
				a1.style.cursor = 'pointer';
				linha.style.backgroundColor = '#f009';
				linha.style.backgroundImage = 'repeating-linear-gradient(45deg, rgba(0,0,0,0.1) 0px, rgba(0,0,0,0.1) 5px, transparent 5px, transparent 10px)';
				linha.style.cursor = 'no-drop';
				linha.setAttribute('title','Processo em outro Órgão Julgador');
			}
			a1.innerText = processoFormatado;
			linha.insertCell().appendChild(a1); //coluna 5
			
			linha.style.setProperty('line-height','3em');
		}
		return tabela;
		
		function criarCabecalho() {
			let cabecalho = tabela.createTHead();
			let linha_cabecalho = cabecalho.insertRow();
			let celula_cabecalho0 = document.createElement('th');
			celula_cabecalho0.style = "width: auto;";
			celula_cabecalho0.appendChild(document.createTextNode('BANCO'));
			
			let celula_cabecalho1a = document.createElement('th');
			celula_cabecalho1a.style = "width: auto;";
			celula_cabecalho1a.appendChild(document.createTextNode('BENEFICIÁRIO'));
			
			let celula_cabecalho1b = document.createElement('th');
			celula_cabecalho1b.style = "width: auto;";
			celula_cabecalho1b.appendChild(document.createTextNode('TIPO'));
						
			let celula_cabecalho2 = document.createElement('th');
			celula_cabecalho2.style = "width: auto;";
			celula_cabecalho2.appendChild(document.createTextNode('DATA DA ORDEM'));
			
			let celula_cabecalho3 = document.createElement('th');
			celula_cabecalho3.style = "width: auto;";
			celula_cabecalho3.appendChild(document.createTextNode('VALOR'));
			
			let celula_cabecalho4 = document.createElement('th');
			celula_cabecalho4.style = "width: auto;";
			celula_cabecalho4.appendChild(document.createTextNode('CONTA JUDICIAL'));
			
			let celula_cabecalho5 = document.createElement('th');
			celula_cabecalho5.style = "width: auto;";
			celula_cabecalho5.appendChild(document.createTextNode('NÚMERO DO PROCESSO'));
			
			linha_cabecalho.appendChild(celula_cabecalho0);
			linha_cabecalho.appendChild(celula_cabecalho1a);
			linha_cabecalho.appendChild(celula_cabecalho1b);
			linha_cabecalho.appendChild(celula_cabecalho2);
			linha_cabecalho.appendChild(celula_cabecalho3);
			linha_cabecalho.appendChild(celula_cabecalho4);
			linha_cabecalho.appendChild(celula_cabecalho5);
		}
	}
	
	async function mapTratarDados(result) {
		return result.map(({processo, banco, nomeBeneficiario, tipo,
							   valor, situacao, dataSituacao, idConta, conteudoComprovante,
								 ...rest}) => {
			
			return {
				"processo": processo,
				"banco": banco,
				"beneficiario": nomeBeneficiario,
				"tipo": tipo,
				"valor": convertValor(valor),
				"situacao": situacao,
				"data": simpleDate(dataSituacao),
				"conta": idConta,
				"conteudoComprovante": conteudoComprovante,
				}
		});

	}
		
	function prepararEAbrirArquivo(titulo, tabela) {
		let arquivoFinal = "";
		let comecoArquivo =
			`<html lang='pt-BR'><head><meta charset="utf-8"><style>img { display: none;}
				body {
					font-family: Open Sans,Arial,Verdana,sans-serif;
				}
				
				table {
					border-collapse: collapse;
					border-spacing: 0;
					width: 100%;
					border: 1px solid #ddd;
					font-size: 13px;
				}
				th {
					background-color: #f0f0f0;
					padding: 0 10px;
					vertical-align: middle;
					text-align: left;
					border-bottom: 0 solid;
					border-color: #d7d7d7;
					min-width: -moz-fit-content;
				}

				td {
					padding: 0 10px;
					border-top: 2px solid rgba(0,0,0,.12);
					text-align: left;
					vertical-align: middle;
				}

				tr:nth-child(even) {
					background-color: #f0f0f0;
				}
				
				tr:hover {
					background-color: #daa52075;
					border: 2px solid goldenrod;
				}
				
				.titulo {
					font-size: 24px;
					color: #373a3c;
					text-align: center;
				}
				.subtitulo {
					font-size: 14px;
					color: #888;
					text-align: center;
				}
				
				a:link {
					color: unset;
					text-decoration: none;
				}
				
				a:visited {
					color: unset;
					text-decoration: none;
				}
				
				a:active  {
					color: unset;
					text-decoration: none;
				}

			</style>` + "<title> maisPJe - " + titulo + "</title></head><body id='maisPje_Janela_Conferencia_alvaras'>";

		arquivoFinal += tabela + "</body></html>";
		arquivoFinal =
			comecoArquivo +
			"<span class='titulo'>Relatório " +
			titulo + " registros</span><br><br><span class='subtitulo'>" +
			"Gerado em: " +
			agora() +
			"</span>" +
			"<br><br>" +
			"<span style='position: absolute;right: 0;top: 0;color: #e1b6b6;'>Pressione F2 para ajustar o temporizador da conferência automática de alvarás SIF &nbsp;</span>" +
			"<br><br>" +
			arquivoFinal;
		
		let novaJanela = URL.createObjectURL(
			new Blob([arquivoFinal], { type: "text/html" })
		);
		
		window.open(novaJanela, convertDate(new Date()) + " - Relatorio " + titulo + ".html");
	}
	
	function convertDate(texto) {
		let d = new Date(texto)
		return [d.getFullYear(), d.getMonth(), d.getDate(), d.getHours(), d.getMinutes(), d.getSeconds()].join('')
	}
	
	function convertValor(texto) {
		return Intl.NumberFormat('pt-br', {style: 'decimal', currency: 'BRL'}).format(texto)
	}
	
	function simpleDate(texto) {
		return new Date(texto).toLocaleDateString();
	}
	
	function numeroProcessoFormatado(texto) {
		return texto.replace(/(\d{7})(\d{2})(\d{4})(\d{1})(\d{2})(\d{4})/,"$1-$2.$3.$4.$5.$6");
	}
}

//FUNÇÃO QUE RETORNA os alvarás pendentes de conferência
async function obterAlvarasTipo(tipo) {
	return new Promise(
		async resolver => {
			let url = 'https://' + preferencias.trt + '/sif-financeiro-api/api/prestacaocontas/agrupador/alvaras?situacoesAlvara=AGUARDANDO_CONFERENCIA&pagina=1&tamanhoPagina=50';
			fetch(url).then(async function (response) {
				return response.json();
			})
			.then(async data=>{
				if (!data.totalRegistros) { return null }
				return data.totalRegistros;
			})
			.then(async data2=>{
				if (!data2) { return resolver([]) }
				let resultadoFinal = await consultarOrdensPendentesDeConferencia(data2);
				return resolver(resultadoFinal);
			})
			.catch(async function (err) {
				return resolver([]);
			});
		}
	);
		
	async function consultarOrdensPendentesDeConferencia(paginas) {
		return new Promise(
			async resolver => {
				let url2 = 'https://' + preferencias.trt + '/sif-financeiro-api/api/prestacaocontas/agrupador/alvaras?situacoesAlvara=AGUARDANDO_CONFERENCIA&pagina=1&tamanhoPagina=' + paginas +'&ordenacaoCrescente=true';
				let listaAlvaras = [];
				let resposta = await fetch(url2);
				let dados = await resposta.json();
				
				if (!dados) { return resolver('') }
				if (!dados.resultado) { return resolver('') }
				if (dados.resultado.length < 1) { return resolver('') }
				
				let listaDeAlvaras = [];
				for (const [pos, alvara] of dados.resultado.entries()) {
					if (alvara.situacao.includes(tipo)) {
						listaAlvaras.push(alvara);
					}
				}
				return  resolver(listaAlvaras);
			}
		);
	}
}

//FUNÇÃO QUE AGUARDA O CONDÃO DA CONFERENCIA DO ALVARÁ PARA IR PRO PRÓXIMO
async function esperarConferenciaAlvaraSif(descricaoBotao) {
	return new Promise(async resolver => {
		let cont = (preferencias.tempAuto) ? preferencias.tempAuto : 10;  //aguarda 10 segundos
		let elemento1 = await esperarElemento('button', descricaoBotao);
		elemento1.scrollIntoView({behavior: 'smooth',block: 'end'});
		elemento1.onclick = function (e) { resolver(true) }
		// elemento1.style.outline = '5px solid #ff00005e';
		elemento1.style.animation = 'pulse 1s infinite';
		elemento1.firstElementChild.innerText = descricaoBotao + ' ( ' + cont + ' )';
		
		let check = setInterval(function() {
			cont--;
			elemento1.firstElementChild.innerText = descricaoBotao + ' ( ' + cont + ' )';
			if (cont < 1) {
				clearInterval(check);
				elemento1.click();
			}
		}, 1000);
	});
}

//FUNÇÃO QUE AGUARDA O CARREGAMENTO DA LISTA DE ALVARÁS PARA CONFERIR
async function esperarTransicaoSIF(tempoLimite=60000) { //um minuto
	return new Promise(async resolve => {
		let targetDocumento = document.body;
		let observerDocumento = new MutationObserver(async function(mutationsDocumento) {
			mutationsDocumento.forEach(async function(mutation) {
				if (!mutation.removedNodes[0]) { return }
				if (!mutation.removedNodes[0].tagName) { return }
				// console.log("***[DEL] tag " + mutation.removedNodes[0].tagName);
				// console.log("***[DEL] class " + mutation.removedNodes[0].className);
				if (mutation.removedNodes[0].tagName == 'DIV' && mutation.removedNodes[0].className == 'cdk-overlay-backdrop') {
					observerDocumento.disconnect();
					resolve(true);
				}
			});
		});
		let configDocumento = { childList: true, subtree:true }
		observerDocumento.observe(targetDocumento, configDocumento); //inicia o MutationObserver

		setTimeout(function() {
			observerDocumento.disconnect();
			resolve(true); //sem erros
		}, tempoLimite);  //desliga o mutation depois de 'tempoLimite' segundos
	});
}

//FUNÇÃO QUE APLICA VISIBILIDADE DE SIGILO PARA O ÚLTIMO DOCUMENTO JUNTADO NO PROCESSO
async function aplicarVisibilidadeSigiloUltimoDocumentoJuntado() {
	return new Promise(async resolver => {
		console.log('maisPJe: aplicarVisibilidadeSigiloUltimoDocumentoJuntado: ' + preferencias.anexadoDoctoEmSigilo);
		
		if (preferencias.anexadoDoctoEmSigilo == 4) { return resolver(false); } //nenhum
		
		let primeiroSigilosoEncontrado = await esperarElemento('ul[class="pje-timeline"] a[class="tl-documento is-sigiloso"]');
		let ancora = primeiroSigilosoEncontrado.parentElement.parentElement;
		
		if (!ancora.id) {
			criarCaixaDeAlerta("ALERTA",'documento sem id',5);
			return resolver(false);
		}
		
		fundo(true);
		await sleep(500);
		exibir_mensagem("atribuindo visibilidade do documento às partes");
		await sleep(500);
		await clicarBotao('button[aria-label="Exibir múltipla seleção."]');
		await sleep(1000);
		await clicarBotao('mat-card[id="' + ancora.id + '"] mat-checkbox label');
		await sleep(1000);
		await clicarBotao('div[class="div-todas-atividades-em-lote"] button[mattooltip="Visibilidade para Sigilo"]');
		let ancora2 = await esperarElemento('div[class="cdk-overlay-container"] pje-doc-visibilidade-sigilo pje-paginador');
		let itensPorPagina = ancora2.querySelectorAll('div[class*="mat-select-trigger"]');
		await escolherOpcaoTeste(itensPorPagina[1],'100');
		await sleep(1000);
		
		if (preferencias.anexadoDoctoEmSigilo == 1) { await clicarBotao('th button') }
		if (preferencias.anexadoDoctoEmSigilo == 2) { await selecionarPoloAtivo() }
		if (preferencias.anexadoDoctoEmSigilo == 3) { await selecionarPoloPassivo() }
		
		fundo(false);
		await clicarBotao('button','Salvar');	
		await sleep(1000);
		await clicarBotao('button[aria-label="Ocultar múltipla seleção."]');
		return resolver(true);
	});
	
	async function selecionarPoloAtivo() {
		return new Promise(async resolver => {
			let listaPoloAtivo = await esperarColecao('pje-data-table[nametabela="Tabela de Controle de Sigilo"] i[class*="icone-polo-ativo"]')
			
			for (const [pos, item] of listaPoloAtivo.entries()) {
				let linha = item.parentElement.parentElement.parentElement;
				await clicarBotao(linha.querySelector('label'));
			}
			
			return resolver(true);
		});
	}
	
	async function selecionarPoloPassivo() {
		return new Promise(async resolver => {
			let listaPoloPassivo = await esperarColecao('pje-data-table[nametabela="Tabela de Controle de Sigilo"] i[class*="icone-polo-passivo"]')
			
			for (const [pos, item] of listaPoloPassivo.entries()) {
				let linha = item.parentElement.parentElement.parentElement;
				await clicarBotao(linha.querySelector('label'));
			}
			
			return resolver(true);
		});
	}
}

//****************************************************
//FUNÇÃO RESPONSÁVEL POR COPIAR E COLAR OS ITENS DO MENU
//ESTÁ LIGADA COM O ARQUIVO "BACKGROUND.JS"
browser.runtime.onMessage.addListener(request => {
	//Corrige o menuItemId
	let texto = request.greeting;
	
	//erro na justiça gratuita
	if (texto.includes('(cd-mnjg)')) {
		if (document.location.href.includes(".jus.br/pjekz/") && document.location.href.includes("/detalhe")) {
			criarCaixaDeAlerta(titulo='ATENÇÃO', mensagem=texto, temporizador=15, tipoBotao=2)
		}
		return;
	}
	
	texto = texto.substring(texto.search("#R#")+1); //representantes (evita erros de id duplicado.. por exemplo, a genitora ser advogada da parte)
	texto = texto.substring(texto.search("#")+1); //outras partes (evita erros de id duplicado.. por exemplo, a genitora ser advogada da parte)
	
	let padrao = /(extenso)/;	
	if (texto.includes('@extenso')) {
		if (texto.includes('somente@extenso')) {
			texto = texto.replace('somente@extensoR$ ','');
			texto = porExtenso(texto);
		} else {
			texto = texto.replace('@extenso','');
			let valor = texto;
			texto = texto.replace('R$ ','');
			texto = porExtenso(texto);
			texto = valor + ' (' + texto + ')';
		}
	} else if (texto.includes('Transito em Julgado: ')) { 
		texto = texto.replace('Transito em Julgado: ','');
	} else if (texto.includes('Justica Gratuita: ')) { 
		texto = texto.replace('Justica Gratuita: ','');
	}
	
	
	let e = document.activeElement;
	let elementoInicialdaSelecao = window.getSelection().anchorNode;
	let posInicialdaSelecao = window.getSelection().anchorOffset;
	let elementoFinaldaSelecao = window.getSelection().focusNode;
	let posFinaldaSelecao = window.getSelection().focusOffset;
	copiarClipboard();
	
	e.focus();
	
	//DESCRIÇÃO: Essa condição serve para identificar elementos ativos dentro de iFrames, muito utilizado no PJe
	//Sem ela fica impossível identificar qual o elemento ativo (que é selecionado) da página.	
	//console.log(document.activeElement + " : " + document.activeElement.tagName + " : " + document.activeElement.className + " : " + document.activeElement.id);
	
	if(document.body === e || e.tagName == 'IFRAME'){
		let iframe1 = document.getElementsByTagName('iframe');
		for(let i = 0; i<iframe1.length; i++ ){
			
			//DESCRIÇÃO: usado para pegar o elemento ativo na tela de "minuta de despachos" (por exemplo) uma vez que se trata de um iframe dentro de outro iframe.
			if (iframe1[i].contentWindow.document.activeElement.tagName == 'IFRAME') {
				let iframe2 = iframe1[i].contentWindow.document.getElementsByTagName('iframe');
				for(let j = 0; j<iframe2.length; j++ ){
					if (iframe2[j].contentWindow.getSelection().rangeCount) {				
						let range = iframe2[j].contentWindow.getSelection().getRangeAt(0);				
						range.deleteContents();
						range.insertNode(iframe2[j].contentWindow.document.createTextNode(texto));				
					}
				}
			}
			
			//DESCRIÇÃO: usado para pegar o elemento ativo da tela de "anexar documentos" (por exemplo) - versão Jacarandá.
			if (iframe1[i].contentWindow.getSelection() != null) {
				if (iframe1[i].contentWindow.getSelection().rangeCount) {
					let range = iframe1[i].contentWindow.getSelection().getRangeAt(0);
					range.deleteContents();
					range.insertNode(iframe1[i].contentWindow.document.createTextNode(texto));
				}
			} 
		}
	//DESCRIÇÃO: usado para pegar o elemento ativo da tela de "anexar documentos" (por exemplo) - Versão Aroeira.
	} else if (e.tagName == 'DIV') {
		let range = document.createRange();
		range.setStart(elementoInicialdaSelecao, posInicialdaSelecao);
		range.setEnd(elementoFinaldaSelecao, posFinaldaSelecao);
		range.deleteContents();
		let clipboard = window.document.createTextNode(texto);
		range.insertNode(clipboard);
		window.getSelection().removeAllRanges();
		window.getSelection().addRange(range);
		
	//DESCRIÇÃO: Essa condição serve para pegar o elemento ativo da página quando se tratar de formulários.
	} else {
		if (e.id == 'cpfCnpj') { //clica no botão incluir CNPJ			
			e.blur();			
			setTimeout(function(){
				document.getElementById('botaoIncluirCpfCnpj').disabled = false;
				document.getElementById('botaoIncluirCpfCnpj').click();				
			}, 200);
		}
		
		// DESCRIÇÃO: Adiciona o texto no elemento ativo da página substituindo apenas o texto selecionado se for o caso		
		if (e.selectionStart != null) {			
			e.value = e.value.slice(0, e.selectionStart) + texto + e.value.slice(e.selectionEnd, e.length);
			
			//dispara evento para mostrar ao formulário que o input foi preenchido. Sem isso, quando gravar o texto inserido desaparece
			let evt = new Event('input', {bubbles: true,cancelable: true});
			e.dispatchEvent(evt);
		}
	}
	
	//DESCRIÇÃO: Esse trecho de código serve para quando houver seleção de item no MENU, este item seja copiado para o clipboard (memória), assim é possível utilizado em 
	//outros navegadores através do "CTRL + V".
	//Porém, para copiar para a memória é necessário criar um elemento falso na página uma vez que o comando "document.execCommand("copy")" só aceita textos selecionados.
	//***Atualização de comando.. 
	function copiarClipboard() {
		// var textarea = document.createElement("textarea");
		// textarea.textContent = texto;
		// document.body.appendChild(textarea);
		// textarea.select();
		// document.execCommand("copy");
		// document.body.removeChild(textarea)
		navigator.clipboard.writeText(texto);
	}

});

////LISTENERS

//FUNÇÃO RESPONSÁVEL POR ESCUTAR EVENTOS DE DUPLO CLIQUE
document.body.addEventListener('dblclick', function(event) {
	if (!preferencias.extensaoAtiva) { return }
	if (document.location.href.search(".jus.br/pjekz/") > -1) {
		let botao;
		if (event.target.tagName == "BUTTON") {
			botao = event.target.getAttribute('aria-label') == null ? "" : event.target.getAttribute('aria-label');
		} else {
			botao = event.target.parentElement.parentElement.getAttribute('aria-label') == null ? "" : event.target.parentElement.parentElement.getAttribute('aria-label');
		}
		if(botao == "Painel Global"){			
			if (event.ctrlKey) {
				meusProcessosGlobal2();
			} else {
				meusProcessosGlobal();
			}
		}
		if(botao == "Relatórios do GIGS"){
			meusProcessosGigs();
		}
		
		//se o gigs estiver aberto atribui o responsável automaticamente		
		let check = setInterval(function() {
			if (document.querySelector('pje-gigs-ficha-processo')) {
				clearInterval(check);
				gigsAtribuirResponsavel();
			}
		}, 100);
	}
});

//FUNÇÃO RESPONSÁVEL POR ESCUTAR EVENTOS DE CLIQUE
document.body.addEventListener('click', function(event) {
	if (!preferencias.extensaoAtiva) { return }
	// console.log(document.referrer + " >>>> " + document.location.href);
	// console.log(event.target.id + " : " + event.target.name + " : " + event.target.tagName + " : " + event.target.className + " : " + event.target.innerText);
	
	
	if (document.location.href.includes(".jus.br/pjekz/") || document.location.href.includes("/administracao") || document.location.href.includes(".jus.br/centralmandados/")) {
		kaizen();
		
		//DESCRIÇÃO: coloca barra de rolagem na consulta de expedientes, quando tem muito o botão de "fechar expediente" some da tela
		if (document.getElementsByTagName("pje-expedientes-dialogo")[0]) {
			document.getElementsByTagName("pje-expedientes-dialogo")[0].parentElement.parentElement.style = "max-width: 80vw; pointer-events: auto; position: static; overflow: auto;";
		}
		
		if (document.querySelector('div[class*="menu-selecao-perfil-usuario"]')) {
			addCheckPerfil();
		}
		
		// DESCRIÇÃO: Permite usar a opção MARCAR TODOS apenas para os processos filtrados
		if (event.target.className.includes('fa-check') && event.target.className.includes('todas-marcadas')) {
			if (nextParent(event.target,'button').getAttribute('aria-label') == 'Desmarcar todos') {
				let meuFiltro_temp = [];
				preferencias.meuFiltro.forEach((element, index, array) => {	return element ? meuFiltro_temp.push(index) : -1 });
				
				if (meuFiltro_temp.length > 0) { //tem filtro?
					if (document.querySelector('tbody').getAttribute('maisPje_filtro_ativado') == "true") { //filtro está ativado?
						let el = document.querySelectorAll('input[aria-label="Marcar processo"]');
						if (!el) {return}
						let map = [].map.call(
							el, 
							function(elemento) {
								if (nextParent(elemento,'tr').getAttribute('maisPje_filtro') == "false") {
									elemento.click();
								}
							}
						);
					}
				}
			}
		}

//DESCRIÇÃO: BOTÕES NA PAUTA DE PERICIAS
		if (document.location.href.includes("/pauta-pericias")) {
			let check = setInterval(function() {
				if (document.querySelector('mat-chip-list')) {
					clearInterval(check);
					if (!document.getElementById('maisPje_pauta_pericia')) {
						let ancora = document.querySelector('mat-chip-list').firstElementChild.lastElementChild;
						let botao = document.createElement("button");
						botao.id = "maisPje_pauta_pericia";
						botao.textContent = "Exibir a Localização dos Processos";
						botao.style = "cursor: pointer; position: relative; top: 20%; width: 100%; padding: 5px; margin: 5px; height: 35px; z-index: 1;";
						botao.onclick = function () {painelPericiaTarefaProcesso()};
						ancora.appendChild(botao);
					}
				}
			}, 100);
		
//DESCRIÇÃO: BOTÕES NA TELA COMUNICAÇÕES
		} else if (document.location.href.search("/comunicacoesprocessuais/") > -1) {
			//DESCRIÇÃO: adiciona o botao copiar para copiar o conteudo do documento nas intimações
			if (document.querySelector('pje-anexar-documento')) {
				let check = setInterval(function() {
					if (document.querySelector('pje-documento-visualizador')) {
						clearInterval(check);
						addBotaoCopiarDocumento();
					}
				}, 100);
			}
			
			if (document.querySelector('div[class="pec-item-formulario-tabela-destinatarios"]')) {
				document.querySelector('div[class="pec-item-formulario-tabela-destinatarios"]').style.width = '95vw';
				document.querySelector('div[class="pec-item-formulario-tabela-destinatarios"]').style.setProperty('justify-self', 'auto');
			}
			
			if (document.querySelector('div[class="pec-botoes-acoes-expedientes"]')) {
				document.querySelector('div[class="pec-botoes-acoes-expedientes"]').style.width = '95vw';
			}
			
			let botao;
			if (event.target.tagName == "BUTTON") {				
				botao = event.target.getAttribute('aria-label') == null ? "" : event.target.getAttribute('aria-label');
			} else {
				if (event.target.parentElement.parentElement) {
					botao = event.target.parentElement.parentElement.getAttribute('aria-label') == null ? "" : event.target.parentElement.parentElement.getAttribute('aria-label');
				} else {
					botao = "";
				}				
			}
			if(botao.search("Confeccionar ato") >= 0) {
				let expediente1 = document.getElementsByClassName("mat-select-value")[0] == null ? "Tipo de Expediente" : document.getElementsByClassName("mat-select-value")[0].innerText;
				let expediente2 = document.getElementsByClassName("mat-select-value")[1] == null ? "Tipos de Expediente" : document.getElementsByClassName("mat-select-value")[1].innerText;
				if(expediente1 != "Tipo de Expediente" || expediente2 != "Tipos de Expediente") {
					let check1 = setInterval(function() {					
						if(document.body.contains(document.getElementsByTagName("mat-dialog-container")[0])) {
							document.getElementsByTagName("mat-dialog-container")[0].parentElement.style.setProperty('max-width', '100vw');
							document.getElementsByTagName("mat-dialog-container")[0].parentElement.style.setProperty('width', '98%');
							document.getElementsByTagName("mat-dialog-container")[0].parentElement.style.setProperty('height', '98%');					
							setTimeout(function(){
								if(document.body.contains(document.getElementsByClassName("pec-dialogo-ato wrapper")[0])) {
									document.getElementsByClassName("pec-dialogo-ato wrapper")[0].style.setProperty('max-width', '100vw');
									document.getElementsByClassName("pec-dialogo-ato wrapper")[0].style.setProperty('max-height', '100vh');
									document.getElementsByClassName("pec-dialogo-ato wrapper")[0].style.setProperty('padding', '0px');
									document.getElementsByClassName("pec-dialogo-ato wrapper")[0].style.setProperty('margin', '0px');
									document.getElementsByClassName("pec-dialogo-ato wrapper")[0].className = "pec-dialogo-ato";
									// ajustarColuna("70%");
									//INCLUI O BOTÃO DE ZOOM NO EDITOR DE TEXTOS
									addZoom_Editor();
								}							
							}, 800);						
							clearInterval(check1);
						}
					}, 100);
				}
			} else if(botao.search("endereço") >= 0) {
				let check2 = setInterval(function() {
					if(document.body.contains(document.getElementsByClassName("cdk-overlay-pane")[0])) {
						document.getElementsByTagName("mat-dialog-container")[0].parentElement.style.setProperty('max-width', 'none');
						document.getElementsByTagName("mat-dialog-container")[0].parentElement.style.setProperty('width', '98%');
						document.getElementsByTagName("mat-dialog-container")[0].parentElement.style.setProperty('height', '98%');							
						clearInterval(check2);
					}
				}, 100);
			}
			
			//DESCRIÇÃO: Se a janela for redimensionada o elemento acompanha o tamanho da janela
			window.onresize = function() {
				x = document.getElementsByTagName("pje-cabecalho")[0].offsetWidth * 0.95;
				document.getElementsByClassName("pec-item-formulario-tabela-destinatarios")[0].style.setProperty('width', x + "px");
				document.getElementsByClassName("pec-item-formulario-tabela-destinatarios")[0].style.setProperty('justify-self', 'auto');
				// ajustarColuna("70%");
			};
			
//DESCRIÇÃO: BOTÕES NA TELA ANEXAR DOCUMENTOS
		} else if (document.location.href.search("/documento/anexar") > -1) {
			// ajustarColuna("70%");
			//DESCRIÇÃO: cria o botao copiar para copiar o conteudo do documento 
			if (event.target.innerText == "Documentos") {
				let check = setInterval(function() {
					if (document.querySelector('pje-documento-visualizador')) {
						clearInterval(check);
						addBotaoCopiarDocumento();
					}
				}, 100);
			}
			
//DESCRIÇÃO: BOTÕES NA TELA AUTUAÇÃO DE NOVO PROCESSO
		} else if (document.location.href.search("/autuacao/") > -1) {
			
			//DESCRIÇÃO: escolhe o tipo documento diverso para todos os documentos anexados
			if (event.target.innerText.search("selecione arquivos") > -1) {
				
				let check2 = setInterval(function() {
					if (document.querySelector('pje-item-lista-anexo-pdf')) {
						clearInterval(check2);
						addBotaoTipoEmLote();
					}
				}, 100);
			}		
		
//DESCRIÇÃO: AJUSTE NA TELA PERÍCIAS
		} else if (document.location.href.search("/pericias") > -1) {
			let check = setInterval(function() {
				if(document.getElementsByTagName("pje-documento-designacao-pericia")[0]) {
					clearInterval(check);
					let el = document.getElementsByTagName("pje-documento-designacao-pericia")[0];
					el.parentElement.parentElement.style.setProperty('max-width', 'none');
					el.parentElement.parentElement.style.setProperty('max-height', 'none');
					el.parentElement.parentElement.style.setProperty('width', '98%');
					el.parentElement.parentElement.style.setProperty('height', '98%');
					// ajustarColuna("70%");
					addZoom_Editor();
				}
				if(document.getElementsByTagName("pje-documento-solicitar-esclarecimentos")[0]) {
					clearInterval(check);
					let el = document.getElementsByTagName("pje-documento-solicitar-esclarecimentos")[0];
					el.parentElement.parentElement.style.setProperty('max-width', 'none');
					el.parentElement.parentElement.style.setProperty('max-height', 'none');
					el.parentElement.parentElement.style.setProperty('width', '98%');
					el.parentElement.parentElement.style.setProperty('height', '98%');
					// ajustarColuna("70%");
					addZoom_Editor();
				}
			}, 1000);	

//DESCRIÇÃO: BOTÕES NA TELA GIGS
		} else if (document.location.href.search("pjekz/gigs/abrir-gigs") > -1) {
			addBotaoGigs();
			gigsAtribuirResponsavel(event.target);			
			// gigsInserirBorrachaResponsavel()

//DESCRIÇÃO: BOTÕES NA TELA DETALHES DO PROCESSO
		} else if (document.location.href.search("/detalhe") > -1) {
			//GIGS na tela detalhes
			setTimeout(function(){addBotaoGigs()}, 500);
			gigsAtribuirResponsavel(event.target);
			// gigsInserirBorrachaResponsavel()
			
		}
	} else if (document.location.href.search("sisbajud.cnj.jus.br") > -1 || document.location.href.search("sisbajud.cloud.pje.jus.br") > -1) {
		if (!document.getElementById('maisPje_menuConvenios')) {
			// console.log("SISBAJUD");
			menuConvenios();
		}
	
	} else if (document.location.href.includes(preferencias.trt + "/deposito/#/conta") || document.location.href.includes("garimpo.")) {
		if (!preferencias.modulo9.garimpo) { return }
		garimpo(event.target);
	
	} else if (document.location.href.includes("serasa") && document.location.href.includes("cadastrar-ordem")) {
		if (!preferencias.modulo9.renajud) { return }
		if (event.target.innerText.includes("Cadastrar")) {
			if (document.querySelector('input[formcontrolname="nroDocumentoDevedor"]')) {
				let el = document.querySelector('input[formcontrolname="nroDocumentoDevedor"]');
				el.focus();
				let var1 = browser.storage.local.get('processo_memoria', function(result){
					el.value = result.processo_memoria.reu[0].cpfcnpj;
					triggerEvent(el, 'input');
					el.blur();
				});
			}
			if (document.querySelector('input[formcontrolname="nroProcesso"]')) {
				let el = document.querySelector('input[formcontrolname="nroProcesso"]');
				el.focus();
				
				let var1 = browser.storage.local.get('processo_memoria', function(result){
					el.value = result.processo_memoria.numero;
					triggerEvent(el, 'input');
					el.blur();
				});
			}
		}
	
	}
});

//FUNÇÃO RESPONSÁVEL POR ESCUTAR EVENTOS DE saída de formulários
document.body.addEventListener('focusout', async function(event) {
	if (!preferencias.extensaoAtiva) { return }
	// console.log(event.target.id);	
	//DESCRIÇÃO: CAMPO RESPONSÁVEL > INCLUIR PRAZO > GIGS
	if (document.getElementsByTagName('pje-gigs-ficha-processo')[0]) {
		// console.log(event.target.getAttribute('formcontrolname'));
		if (event.target.getAttribute('formcontrolname') == "dias") {
			let selecao = preferencias.prazoResponsavel;
			if (!selecao) { return }
			let atividade = "";
			let pessoa = "";
			if (document.querySelector('input[formcontrolname="tipoAtividade"]').value != "") {
				let tipoAtividade = document.querySelector('input[formcontrolname="tipoAtividade"]').value;
				//preenche o responsável pela atividade automaticamente conforme pré-definido
				if (document.querySelector('input[formcontrolname="responsavel"]').value.length == 0) {
					let rol = selecao.split('|');							
					let processoNumero = document.getElementById('dados-processo').innerText.match(new RegExp('\\d{7}-\\d{2}\\.\\d{4}\\.\\d{1,2}\\.\\d{1,2}\\.\\d{4}','g')).join();
					let ano = processoNumero.substring(11, 15);
					let digito;							
					if (ano > 2009) {
						digito = processoNumero.substring(6, 7);					
					} else {
						digito = processoNumero.substring(4, 5);
					}
					if (selecao.includes(tipoAtividade) > -1 || selecao.search(digito) > -1) {
						for (let i = 0; i < rol.length; ++i) {
							let item = rol[i].split(':');
							if (item[0] == tipoAtividade || item[0] == digito) {									
								if (document.querySelector('input[formcontrolname="responsavel"]').value.length == 0) {
									document.querySelector('input[formcontrolname="responsavel"]').click();
									for (let j = 0; j < document.querySelectorAll('mat-option').length; ++j) {
										let responsavel = document.querySelectorAll('mat-option')[j].getElementsByTagName('span')[0].textContent;
										if (responsavel.search(item[1]) > - 1) {
											document.querySelectorAll('mat-option')[j].click();
											break;
										}
									}
									break;
								}									
							}
						}							
					}
				}
			}
		}
	}
	
	//Editar calendários (datepicker) do PJe para inserir os feriados.. GIGS, perícias, etc..
	if ((document.location.href.includes(".jus.br/pjekz/") && !document.location.href.includes("sif")) || document.location.href.includes("aud.trt")) {
		if (document.querySelector('button[aria-label="Open calendar"]')) {
			if (event.target.getAttribute('aria-label') == "Open calendar") {
				editarCalendarioGigs();
			}
		}
	}
	
	if (document.location.href.includes("/tarefa/") && event.target.tagName == "BUTTON" && event.target.getAttribute('aria-label') == "Conclusão ao magistrado") {
		let check = setInterval(function() {
			if(document.querySelector('mat-select[placeholder="Magistrado"]')) {
				clearInterval(check);
				filtroMagistrado();
			}					
		}, 100);
		
	}
	
	//DESCRIÇÃO: RENAJUD
	if (document.location.href.includes("serpro.gov.br/renajud/")) {
		if (event.target.name == "form-incluir-restricao:campo-cpf-cnpj") {
			if (event.target.value != "") {
				setTimeout(function(){document.getElementById('form-incluir-restricao:botao-pesquisar').click()}, 100);
			}
		}
		
	//DESCRIÇÃO: CNIB
	} else if (document.location.href.search("/indisponibilidade/") > -1) {
		if (event.target.id == "ordem-processo-numero" || event.target.id == "ordem-processo-nome") {
			if (document.getElementById('ordem-processo-numero').value != "" && document.getElementById('ordem-processo-nome').value != "") {
				setTimeout(function(){document.getElementsByClassName('combo-bot')[0].click()}, 100);				
			}			
		} else if (event.target.id == "ordem-processo-documento") {
			if (document.getElementById('ordem-processo-documento').value != "") {
				document.getElementsByClassName('combo-bot p1')[0].click();
				let x = document.getElementsByClassName('combo-bot p2')[0];				
				let check1 = setInterval(function() {
					if(window.getComputedStyle(x).display == "inline") {
						document.getElementsByClassName('combo-bot p2')[0].click()
						clearInterval(check1);
					}					
				}, 100);
			}
		}
	}
});

//FUNÇÃO RESPONSÁVEL POR ESCUTAR EVENTOS DE entrada de clique
//só existe porque a transição de datas na pauta a primeira vez não registra como clique (vai entender)
document.body.addEventListener('mousedown', function(event) {
	if (!preferencias.extensaoAtiva) { return }
	//DESCRIÇÃO: CONCILIAJT NA PAUTA DE AUDIÊNCIA
	if (document.location.href.includes("/pauta-audiencias") || document.location.href.includes("/pauta-inteligente")) {
		// console.log('ativando conciLIAnaPauta')
		setTimeout(function() { //pauta tradicional
			if (document.querySelector('pje-data-table[nametabela="Horários do dia"]')) {
				if (!document.querySelector('td[id="pjextension_coluna_lia"]')) {
					conciLIAnaPauta();
				}
			}
		},1000);
		
		//DESCRIÇÃO: SE VINDO DA JANELA DETALHES PREENCHER CONSIDERANDO OS DADOS DO PROCESSO
		if (document.location.href.includes("maisPje")) {
			setTimeout(function() {
				if (document.querySelector('form[name="frmDesignarAudiencia"]')) {
					let parametros = new URLSearchParams(document.location.href);
					let numero = parametros.get('numero') || '';
					let rito = parametros.get('rito') || '';
					let fase = parametros.get('fase') || '';
					let exibir = [];
					
					if (rito.includes('ATSum')) {
						if (fase.includes('Execução')) {
							exibir.push('Conciliação em Execução por videoconferência');
							exibir.push('Conciliação em Execução por videoconferência - Semana Nacional de Conciliação');
							exibir.push('Conciliação em Execução por videoconferência - Semana Nacional de Execução');
							exibir.push('Conciliação em Execução');
							exibir.push('Conciliação em Execução - Semana Nacional de Conciliação');
							exibir.push('Conciliação em Execução - Semana Nacional de Execução');
						}
						
						if (fase.includes('Conhecimento')) {
							exibir.push('Conciliação em Conhecimento por videoconferência');
							exibir.push('Conciliação em Conhecimento por videoconferência - Semana Nacional de Conciliação');
							exibir.push('Conciliação em Conhecimento');
							exibir.push('Conciliação em Conhecimento - Semana Nacional de Conciliação');
							exibir.push('Inicial por videoconferência (rito sumaríssimo)');
							exibir.push('Instrução por videoconferência (rito sumaríssimo)');
							exibir.push('Una por videoconferência (rito sumaríssimo)');
							exibir.push('Una (rito sumaríssimo)');
							exibir.push('Inicial (rito sumaríssimo)');
							exibir.push('Instrução (rito sumaríssimo)');
							exibir.push('Encerramento de instrução');
							exibir.push('Encerramento de instrução por videoconferência');
						}
					} else if (rito.includes('CartPrec')) {
						exibir.push('Inquirição de testemunha por videoconferência (juízo deprecado)');
						exibir.push('Inquirição de testemunha (juízo deprecado)');
					} else {
						if (fase.includes('Execução')) {
							exibir.push('Conciliação em Execução por videoconferência');
							exibir.push('Conciliação em Execução por videoconferência - Semana Nacional de Conciliação');
							exibir.push('Conciliação em Execução por videoconferência - Semana Nacional de Execução');
							exibir.push('Conciliação em Execução');
							exibir.push('Conciliação em Execução - Semana Nacional de Conciliação');
							exibir.push('Conciliação em Execução - Semana Nacional de Execução');
						}
						
						if (fase.includes('Conhecimento')) {
							exibir.push('Conciliação em Conhecimento por videoconferência');
							exibir.push('Conciliação em Conhecimento por videoconferência - Semana Nacional de Conciliação');
							exibir.push('Conciliação em Conhecimento');
							exibir.push('Conciliação em Conhecimento - Semana Nacional de Conciliação');
							exibir.push('Inicial');
							exibir.push('Instrução');
							exibir.push('Inicial por videoconferência');
							exibir.push('Instrução por videoconferência');
							exibir.push('Encerramento de instrução');
							exibir.push('Encerramento de instrução por videoconferência');
							exibir.push('Julgamento');
							exibir.push('Una');
							exibir.push('Una por videoconferência');
						}
					}
					
					let check = setInterval(function() {
						if (document.querySelector('input[aria-label="Número do Processo"]')) {
							clearInterval(check);
							let el = document.querySelector('input[aria-label="Número do Processo"]');
							if (!el.getAttribute('maispje')) {
								el.value = numero;
								el.setAttribute('maispje','true');
								triggerEvent(el, 'input');
								
								//cria eventlistener para o elemento de tipo de audiência
								let el1 = document.querySelector('mat-select[name="Filtro Tipo da audiência"]').parentElement.parentElement;
								el1.addEventListener('click', exibirOpcoes);
								
								el.addEventListener('click', function(event) { 
									el.value = ""; 
									exibir = [];  
									el1.removeEventListener('click', exibirOpcoes);
								});
								
								function exibirOpcoes() {
									Array.from(document.querySelectorAll('mat-option')).find(function(opcao){if(!exibir.includes(opcao.innerText)){opcao.style.display = "none"}});
								}
							}
						}
					}, 100);
				}
			},500);
		}
		
		setTimeout(function() {
			if (document.querySelector('form[name="frmDesignarAudiencia"]')) {
				if (document.querySelector('input[name="url"]')) {
					if (document.querySelector('input[name="url"]').value == "") {
						ativarModulo10();
					}
				}
			}
		},500);
	}
});

////FUNÇÃO RESPONSÁVEL POR ATRIBUIR TECLAS DE ATALHO AO PJE
window.addEventListener('keydown', async function(event) {
	// event.preventDefault();
	if (!preferencias.extensaoAtiva) { return }
	//pagina para obter os event.codes : https://keycode.info/
	
	
	if (preferencias.concordo) {
		if (event.code === "F1") {
			if (document.location.href.search("docs.google.com/spreadsheets") > -1) {
				consultaRapidaPJE(identificarNumeroDoProcessoDaPlanilhaGoogle());				
			} else {
				consultaRapidaPJE();				
			}		
		} else if (event.code === "F2") {
			event.preventDefault();
			event.stopPropagation();
			// console.log(preferencias.oj_usuario)
			// acao_vinculo('Fechar Pagina|Fechar Pagina');
			// acao_vinculo('Atualizar Pagina|Atualizar Pagina');
			// return;
			// await criarCaixaDeAlerta('ALERTA','Não foi possível obter o ID do processo através do número encontrado (0001245-45.2023.5.12.0059).',15)
			// await criarMapaDosVinculos('Despacho|Teta','AutoGigs|Prazo:Incluir em pauta,Movimento|Cump. Providências,Atualizar Pagina|Atualizar Pagina,Atualizar Pagina|Atualizar Pagina,Atualizar Pagina|Atualizar Pagina,Atualizar Pagina|Atualizar Pagina,Atualizar Pagina|Atualizar Pagina,Atualizar Pagina|Atualizar Pagina,Nenhum',"Esta Ação automatizada foi criada para a juntada das respostas do SISBAJUD quando for positiva ou parcial.");			
			// teste_mutation_observer();
			// aplicarVisibilidadeSigiloUltimoDocumento();
			
			if (document.getElementById('maisPje_menuKaizen_itemmenu_guardar_senha')) {
				
				if (document.getElementById('maisPje_menuKaizen_itemmenu_guardar_senha').style.display == 'unset') { //ou seja, se já estiver visível o F2 funcionará como atalho para minutar um novo bloqueio
					await clicarBotao('span[id="maisPje_menuKaizen_itemmenu_preencher_campos"] a');
				}
				
				document.getElementById('maisPje_menuKaizen_itemmenu_guardar_senha').style.display = 'unset';				
			} else if (document.location.href.includes(".jus.br/pjekz/") && document.location.href.includes("/detalhe")) {
				if (!preferencias.tempF2 || preferencias.tempF2 == 'Nenhum') {
					await clicarBotao('menumaispje span[id="maisPje_menuKaizen_itemmenu_preferencia_f2"] a', null, 1000);
				} else {
					acao_vinculo(preferencias.tempF2);
				}
			} else if (document.location.href.includes("siscondj") && document.getElementById('maisPJe_atalhoConsultaPJe')) {
				await clicarBotao('a[id="maisPJe_atalhoConsultaPJe"]', null, 1000);
			} else if (document.location.href.includes("blob:") && document.getElementById('maisPje_Janela_Conferencia_alvaras')) {
				
				browser.storage.local.get('tempAuto', async function(result){
					preferencias.tempAuto = result.tempAuto;
					let valor = await criarCaixaDePergunta('text','Digite a velocidade (em segundos) de conferência dos alvarás SIF:\n', preferencias.tempAuto);
					let guardarStorage = browser.storage.local.set({'tempAuto': valor}); //uso para levar o código do assunto da AA de Retificar Autuação
					Promise.all([guardarStorage]).then(async values => {
						browser.runtime.sendMessage({tipo: 'criarAlerta', valor: '\n \n A velocidade de interação na conferência dos alvarás SIF ficou designada para ' + valor + ' segundos...'});
						
					});
				});
				
				
			} else if (document.location.href.includes("aj.sigeo.jt.jus.br") && document.getElementById('maisPje_menuKaizen_itemmenu_consultar_minuta')) {
				await clicarBotao('span[id="maisPje_menuKaizen_itemmenu_consultar_minuta"] a', null, 1000);
			} else {
				filtrarPorMeuFiltro();				
			}
			
			
		} else if (event.code === "F3") {
			event.preventDefault();
			event.stopPropagation();

			if (document.location.href.includes(".jus.br/pjekz/") && document.location.href.includes("/detalhe")) {
				if (!preferencias.tempF3 || preferencias.tempF3 == 'Nenhum') {
					await clicarBotao('menumaispje span[id="maisPje_menuKaizen_itemmenu_preferencia_f3"] a', null, 1000);
				} else {
					acao_vinculo(preferencias.tempF3);
				}
			} else {
				gerarRelatorioGerencialSecretaria();
			}
			// verificarVersoesPjeTRTs();
			
		} else if (event.code === "Escape") {
			if (event.getModifierState("ScrollLock")) { //desliga a tela do fundo sem desativar as AA
				console.log('entrou')
				//Cancela o fundo que bloqueia a página
				fundo(false);
			} else {
				//Cancela o fundo que bloqueia a página
				fundo(false);
				console.log('maisPJe: ESC pressionado...')
				//limpa a memória da ação automatizada em lote
				browser.runtime.sendMessage({tipo: 'storage_limpar', valor: 'tempBt,tempAR,AALote,tempAAEspecial,anexadoDoctoEmSigilo'}); //preferencias.anexadoDoctoEmSigilo
				preferencias.tempBT = [];
				preferencias.tempAR = '';
				preferencias.tempAAEspecial = [];
				preferencias.AALote = '';
				preferencias.anexadoDoctoEmSigilo = -1;
			}
		}
		
		if (event.getModifierState("Control")) {	
			if (event.code === "Digit1" || event.code === "Numpad1") {
				//CONSULTAR AR
				// consultarAR();
			} else if (event.code === "Digit2" || event.code === "Numpad2") {
				if (document.location.href.search("/detalhe") > -1) {
					//DETALHES > CRIAR MENU
					gigsCriarMenu(document.location.href.search("/detalhe") > -1);
				} else if (document.body.contains(document.evaluate('//button[@aria-label="Meu Painel"]', document, null, XPathResult.ANY_TYPE, null).iterateNext())) {				
					//PRINCIPAL > PAINEL ANTIGO
					getAtalhosNovaAba().abrirPJeAntigo.abrirAtalhoemNovaJanela();
				}			
			} else if (event.code === "Digit3" || event.code === "Numpad3") {			
				if (document.location.href.search("/detalhe") > -1) {
					//DETALHES > FAZER DOWNLOAD
					acaoBotaoDetalhes("Baixar processo completo");
				} else if (document.body.contains(document.evaluate('//button[@aria-label="Meu Painel"]', document, null, XPathResult.ANY_TYPE, null).iterateNext())) {				
					//PRINCIPAL > CONSULTAR PROCESSO
					getAtalhosNovaAba().consultarProcessos.abrirAtalhoemNovaJanela();
				}
			} else if (event.code === "Digit4" || event.code === "Numpad4") {		
				if (document.location.href.search("/detalhe") > -1) {
					//DETALHES > ANEXAR DOCUMENTOS				
					acaoBotaoDetalhes("Anexar Documentos");				
				} else if (document.body.contains(document.evaluate('//button[@aria-label="Meu Painel"]', document, null, XPathResult.ANY_TYPE, null).iterateNext())) {				
					//PRINCIPAL > CONSULTAR ADVOGADO
					let prefixo = document.location.href.substring(0, document.location.href.search("/pjekz/"));
					let gigsURL = prefixo + '/' + preferencias.grau_usuario + '/PessoaAdvogado/ConfirmarCadastro/listView.seam';
					let winGigs = window.open(gigsURL, '_blank');
				}
			} else if (event.code === "Digit5" || event.code === "Numpad5") {
				
			}
		}
		
		if (event.getModifierState("Alt")) {
			if (event.code === "Digit1" || event.code === "Numpad1") {
				// relatorioGerencialSecretaria();
			} else if (event.code === "Digit2" || event.code === "Numpad2") {
				// relatorioGerencialExecucao();			
			} else if (event.code === "Digit3" || event.code === "Numpad3") {
				// relatorioGerencialContadoria();
				// verificarVersoesPjeTRTs();
				// acoesEmLote();
				
			} else if (event.code === "ArrowUp") {
				inverterCaixaAlta("ArrowUp");
			} else if (event.code === "ArrowDown") {
				inverterCaixaAlta("ArrowDown");
			}
			 else if (event.code === "KeyP") {
				assistenteDeImpressao();
			}
		}
		
		if (document.querySelector('button[id="maisPje_assistenteImpressao_bt_copiar"]')) {
			if (event.code === "KeyP") {
				document.querySelector('button[id="maisPje_assistenteImpressao_bt_copiar"]').click();
			}
		}
		
		function inverterCaixaAlta(tecla) {
			let e = document.activeElement;
			if (e.tagName == 'DIV') {
				let range = document.createRange();
				let elementoInicialdaSelecao = window.getSelection().anchorNode;
				let posInicialdaSelecao = window.getSelection().anchorOffset;
				let elementoFinaldaSelecao = window.getSelection().focusNode;
				let posFinaldaSelecao = window.getSelection().focusOffset;
				
				if (posFinaldaSelecao < posInicialdaSelecao) {
					range.setStart(elementoFinaldaSelecao, posFinaldaSelecao);
					range.setEnd(elementoInicialdaSelecao, posInicialdaSelecao);
				} else {
					range.setStart(elementoInicialdaSelecao, posInicialdaSelecao);
					range.setEnd(elementoFinaldaSelecao, posFinaldaSelecao);
				}
				
				let selecao = tecla == "ArrowUp" ? range.toString().toUpperCase() : range.toString().toLowerCase();
				console.log(selecao);
				range.deleteContents();
				range.insertNode(window.document.createTextNode(selecao));
				
				
			//DESCRIÇÃO: Essa condição serve para formulários.
			} else {
				// console.log("teste")		
				if (e.selectionStart != null) {			
					let inicio = e.selectionStart;
					let fim = e.selectionEnd;
					let selecao = e.value.substring(inicio, fim);
					selecao = tecla == "ArrowUp" ? selecao.toUpperCase() : selecao.toLowerCase();
					e.value = e.value.slice(0, inicio) + selecao + e.value.slice(fim, e.length);
					e.setSelectionRange(inicio,fim);
				}
			}
			
		}

	}
});

async function teste_mutation_observer() {
	console.log('teste_mutation_observer()');
	let primeiraCamada = await ObterCamadaUm();
	
	
	async function ObterCamadaUm() {
		return new Promise(async resolve => {
			// let el_docto = await esperarElemento('frame[name="contents"]');
			// let el_docto_conteudo = el_docto.contentDocument || el_docto.contentWindow.document;
			await ligarMOCamadaUm(document.body);
			return resolve(el_docto_conteudo);
		});
	}
	
	// async function ObterCamadaDois() {
		
		// let cabecalho = primeiraCamada.getElementById('menupenhora');
		// let corpo = primeiraCamada.getElementById('mainpenhora');
		// let conteudoCabecalho = cabecalho.contentDocument || cabecalho.contentWindow.document;		
		// let conteudoCorpo = corpo.contentDocument || corpo.contentWindow.document;
	// }
	
	
	function ligarMOCamadaUm(alvo) {
		return new Promise(async resolve => {
			console.log('ligarMOCamadaUm')
			let observer_cabecalho = new MutationObserver(function(mutationsDocumento) {
				mutationsDocumento.forEach(function(mutation) {
					if (!mutation.removedNodes[0] && !mutation.addedNodes[0]) { return }
					
					if (mutation.removedNodes[0]) {
						if (!mutation.removedNodes[0].tagName) { return }
						console.log("***[DEL] tagName(" + mutation.removedNodes[0].tagName + ") id(" + mutation.removedNodes[0].id + ") className(" + mutation.removedNodes[0].className + ")");
					}
					
					if (mutation.addedNodes[0]) {
						if (!mutation.addedNodes[0].tagName) { return }
						console.log("***[ADD] tagName(" + mutation.addedNodes[0].tagName + ") id(" + mutation.addedNodes[0].id + ") className(" + mutation.addedNodes[0].className + ")");
					}
				});
			});
			let configDocumento = { childList: true, subtree:true }
			observer_cabecalho.observe(alvo, configDocumento);
			
			
		});
	}
}

//CLASSES
function Processo(numero, autor, reu) {
  this.numero = numero;
  this.autor = autor;
  this.reu = reu;
}

function Pessoa(nome, cpfcnpj, polo) {
  this.nome = nome;
  this.cpfcnpj = cpfcnpj;
  this.polo = polo;
}

function EmailAutomatizado(titulo, corpo, assinatura) {
	this.titulo = titulo;
	this.corpo = corpo;
	this.assinatura = assinatura;
}

function Deposito(processo, valor, data, depositante, banco) {
	this.processo = processo;
	this.valor = valor;
	this.data = data;
	this.depositante = depositante;
	this.banco = banco;
}

//FUNÇÕES COMUNS
function decomporNumeroProcesso(numero) {
	return new Promise(
		resolver => {
			let campos = numero.replace(/\D/g,'.').split('.')
			return resolver({
				'numero':campos[0],
				'digito':campos[1],
				'ano':campos[2],
				'jurisdicao':campos[3],
				'regiao':campos[4],
				'vara':campos[5],
			});
		}
	);
}

function extrairNumeros(texto) {
	let padrao = /\d{1,}/;	
	if (padrao.test(texto)) {
		return texto.match(padrao).join();
	} else {
		return texto;
	}
}

function porExtenso(valor){
	console.debug('------------------------------------------------')
	let listaDeExcecoes = {
		"010":"dez",
		"011":"onze",
		"012":"doze",
		"013":"treze",
		"014":"catorze",
		"015":"quinze",
		"016":"dezesseis",
		"017":"dezessete",
		"018":"dezoito",
		"019":"dezenove",
		"020":"vinte",
		"030":"trinta",
		"040":"quarenta",
		"050":"cinquenta",
		"060":"sessenta",
		"070":"setenta",
		"080":"oitenta",
		"090":"noventa",
		"100":"cem",
		"200":"duzentos",
		"300":"trezentos",
		"400":"quatrocentos",
		"500":"quinhentos",
		"600":"seiscentos",
		"700":"setecentos",
		"800":"oitocentos",
		"900":"novecentos",
	};

	let arrayDeReferencia = {
		"unidade":["", "um", "dois", "três", "quatro", "cinco", "seis", "sete", "oito", "nove"],
		"dezena":["","", "vinte e ", "trinta e ", " quarenta e ", " cinquenta e ", " sessenta e ", " setenta e ", " oitenta e ", " noventa e "],
		"centena":["", "cento e ", "duzentos e ", "trezentos e ", "quatrocentos e ", "quinhentos e ", "seiscentos e ", "setecentos e ", "oitocentos e ", "novecentos e "]
	};
	
	let soNumero = valor.replace(/\D/g, "");	
	soNumero = soNumero.padStart(14,"0"); //999 bilhão possui 14 zeros, incluindo os centavos	
	let nCentavos = soNumero.slice(soNumero.length-2, soNumero.length);
	let nReais = soNumero.slice(soNumero.length-5, soNumero.length-2);
	let nMilhar = soNumero.slice(soNumero.length-8, soNumero.length-5);
	let nMilhao = soNumero.slice(soNumero.length-11, soNumero.length-8);
	let nBilhao = soNumero.slice(soNumero.length-14, soNumero.length-11);
	
	//regras do centavos	
	let centavos = '';
	nCentavos = nCentavos.padStart(3,"0"); //acrescena mais um zero nos centavos para não ficar criando exceções repetidas na listaDeExcecoes
	if (nCentavos == '000') {
		centavos = '';
	} else if (nCentavos == '001') {
		centavos = 'um centavo'
	} else if (listaDeExcecoes.hasOwnProperty(nCentavos)) { //se está na lista de exceções
		centavos = listaDeExcecoes[nCentavos] + ' centavos';
	} else {
		centavos = arrayDeReferencia.centena[parseInt(nCentavos[0])] + arrayDeReferencia.dezena[parseInt(nCentavos[1])] + arrayDeReferencia.unidade[parseInt(nCentavos[2])] + ' centavos';
	}
	
	//regras do reais
	let reais = '';
	if (nReais == '000') {
		reais = '';
	} else if (nReais == '001') {
		reais = 'um real';
	} else if (listaDeExcecoes.hasOwnProperty(nReais)) { //se está na lista de exceções
		reais = listaDeExcecoes[nReais] + ' reais';
	} else {
		let x = '0' + nReais[1] + nReais[2]; //exceção da dezena
		x = (listaDeExcecoes.hasOwnProperty(x)) ? listaDeExcecoes[x] : arrayDeReferencia.dezena[parseInt(nReais[1])] + arrayDeReferencia.unidade[parseInt(nReais[2])];
		reais = arrayDeReferencia.centena[parseInt(nReais[0])] + x + ' reais';
	}
	
	//regras do milhar	
	let milhar = '';
	if (nMilhar == '000') {
		milhar = '';
	} else if (listaDeExcecoes.hasOwnProperty(nMilhar)) { //se está na lista de exceções
		milhar = listaDeExcecoes[nMilhar] + ' mil';
	} else {
		let x = '0' + nMilhar[1] + nMilhar[2]; //exceção da dezena
		x = (listaDeExcecoes.hasOwnProperty(x)) ? listaDeExcecoes[x] : arrayDeReferencia.dezena[parseInt(nMilhar[1])] + arrayDeReferencia.unidade[parseInt(nMilhar[2])];
		milhar = arrayDeReferencia.centena[parseInt(nMilhar[0])] + x + ' mil';
	}
	
	//regras do milhao
	let milhao = '';
	if (nMilhao == '000') {
		milhao = '';
	} else if (nMilhao == '001') {
		milhao = 'um milhão';
	} else if (listaDeExcecoes.hasOwnProperty(nMilhao)) { //se está na lista de exceções
		milhao = listaDeExcecoes[nMilhao] + ' milhões';
	} else {
		let x = '0' + nMilhao[1] + nMilhao[2]; //exceção da dezena
		x = (listaDeExcecoes.hasOwnProperty(x)) ? listaDeExcecoes[x] : arrayDeReferencia.dezena[parseInt(nMilhao[1])] + arrayDeReferencia.unidade[parseInt(nMilhao[2])];
		milhao = arrayDeReferencia.centena[parseInt(nMilhao[0])] + x + ' milhões';
	}
	
	//regras do bilhao
	let bilhao = '';
	if (nBilhao == '000') {
		bilhao = '';
	} else if (nBilhao == '001') {
		bilhao = 'um bilhão';
	} else if (listaDeExcecoes.hasOwnProperty(nBilhao)) { //se está na lista de exceções
		bilhao = listaDeExcecoes[nBilhao] + ' bilhões';
	} else {
		let x = '0' + nBilhao[1] + nBilhao[2]; //exceção da dezena
		x = (listaDeExcecoes.hasOwnProperty(x)) ? listaDeExcecoes[x] : arrayDeReferencia.dezena[parseInt(nBilhao[1])] + arrayDeReferencia.unidade[parseInt(nBilhao[2])];
		bilhao = arrayDeReferencia.centena[parseInt(nBilhao[0])] + x + ' bilhões';
	}
	
	//montando a frase
	if (centavos) {
		if (reais || milhar || milhao || bilhao) {
			centavos = ' e ' + centavos;
		}
	}
	
	if (reais) {
		if (milhar || milhao || bilhao) {
			reais = (centavos ? ', ' : ' e ') + reais;
		}
	}
	
	if (milhar) {
		if (!reais) {
			milhar += ' reais';
		}
	}
	
	if (milhao) {
		if (!reais && !milhar) {
			milhao += ' de reais';
		}
	}
	
	if (bilhao) {
		if (!reais && !milhar && !milhao) {
			bilhao += ' de reais';
		}
	}
	
	console.debug('regras do bilhao: ' +  bilhao)
	console.debug('regras do milhao: ' + milhao)
	console.debug('regras do milhar: ' + milhar)
	console.debug('regras dos reais: ' + reais)
	console.debug('regras dos centavos: ' + centavos)
	
	let frase = bilhao + milhao + milhar + reais + centavos;
	frase = frase.replace(/\s{2,}/gm,' '); //exclui os espaços duplicados
	console.debug(valor + ": " + frase.trim());
	return frase.trim();
}

function consultaPJe(el) {
	console.log("      |___criado link para consulta no PJe");
	if (document.getElementById('maisPJe_atalhoConsultaPJe')) { return }
	if (!el || el.length == 0) { return }
	
	let map = [].map.call(
		el, 
		function(elemento) {
			if (new RegExp('\\d{7}-\\d{2}\\.\\d{4}\\.\\d{1,2}\\.\\d{1,2}\\.\\d{4}','g').test(elemento.innerText)) {
				inserirbotao(elemento, elemento.innerText.match(new RegExp('\\d{7}-\\d{2}\\.\\d{4}\\.\\d{1,2}\\.\\d{1,2}\\.\\d{4}','g')).join());
			}
		}
	);
	
	function inserirbotao(elemento, processo) {
		//insere o pacote de ícones
		browser.runtime.sendMessage({tipo: 'insertCSS', file: 'maisPje_icones.css'});
		
		//CRIA BOTÃO CONSULTA RAPIDA DE PROCESSOS
		let atalho = document.createElement("a");
		atalho.id = "maisPJe_atalhoConsultaPJe";
		atalho.style = 'display: inline-block; position: absolute; z-index: 100; width: 28px; height: 28px; text-align: center; color: black;';
		atalho.setAttribute('title','Consultar Processo no PJe');
		
		let check;
		let mouseEmCima = false; 
		atalho.onmouseenter = function (event) {				
			event.preventDefault();
			if (mouseEmCima) { return }
			// console.log('entrou')
			this.firstElementChild.style.animation = 'trocarCor 1s';
			mouseEmCima = true;
			let seg = 1;
			check = setInterval(function() {
				seg--;
				if (mouseEmCima && seg < 1) {
					clearInterval(check);
					console.log('acionou')
					mouseEmCima = false;
					consultaRapidaPJE(processo)
				}			
				
			}, 1000);
		};
		atalho.onmouseleave = function (event) {				
			event.preventDefault();
			// console.log('saiu')
			this.firstElementChild.style.animation = 'unset';
			mouseEmCima = false;
			clearInterval(check);
		};
		
		
		
		atalho.onclick = function () { 
			clearInterval(check);
			consultaRapidaPJE(processo) 
		};
		let i = document.createElement("i");
		i.className = "search";
		i.style = "display: inline-block; font-style: normal; font-variant: normal; text-rendering: auto; line-height: 1; cursor: pointer; width: 2vh; height: 2vh; background-color: black;";
		atalho.appendChild(i);						
		elemento.appendChild(atalho);
	}
}

async function triggerEvent(el, type) {
	if (type == 'click') {
		el.click();
	} else {
		if ('createEvent' in document) {        
			let e = document.createEvent('HTMLEvents');
			e.initEvent(type, true, true); //false, true
			el.dispatchEvent(e);
		}
	}
}

async function mouseTriggerEvent(el,evento) {
	return new Promise(resolve => {
		let e = new MouseEvent(evento, {
			view: window,
			bubbles: true,
			cancelable: true,
			clientX: 100,
			clientY: 100
		});
		if (!el) { el = documento.body }
		el.dispatchEvent(e);
		resolve(true);
	});
}

function simularTecla(tipo,keycode,ctrl=false,alt=false,shift=false) {
	console.log('maisPJe: simulada a(s) tecla(s) ' + (ctrl ? 'Ctrl + ' : '') + (alt ? 'Alt + ' : '') + (shift ? 'Shift + ' : '')  + 'keycode: ' + keycode)
	let e = document.createEvent("KeyboardEvent");
	// initKeyEvent (1.type,2.bubbles,3.cancelable,4.view,5.ctrlKey,6.altKey,7.shiftKey,8.metaKey,9.keyCode,10.charCode)
	e.initKeyEvent(tipo, true, true, document.defaultView, ctrl, alt, shift, false, keycode, 0);
	return e;
}

function acionarSemCliqueGenerico(elemento,cor1,cor2) {
	if (elemento) {
		let mouseEmCima = false;
		let check99;
		elemento.style.setProperty('--color1',cor1);
		elemento.style.setProperty('--color2',cor2);
		
		elemento.addEventListener("click", function (event) { 
			clearInterval(check99);					
			mouseEmCima = false;
			elemento.style.visibility = 'hidden'; //desaparece para não ficar acionando caso o usuário fique com o mouse parado. volta apenas após 4 segundos
			setTimeout(function() {elemento.style.visibility = 'visible';}, 4000); //retorna após 4 segundos
		});
		
		elemento.onmouseenter = function (event) {				
			event.preventDefault();
			if (mouseEmCima) { return }
			this.style.animation = 'trocarCorGeral .80s';
			mouseEmCima = true;
			let seg = 1;
			check99 = setInterval(function() {
				seg--;
				if (mouseEmCima && seg < 1) {
					clearInterval(check99);					
					mouseEmCima = false;
					
					elemento.style.visibility = 'hidden'; //desaparece para não ficar acionando caso o usuário fique com o mouse parado. volta apenas após 4 segundos
					setTimeout(function() {elemento.style.visibility = 'visible';}, 4000); //retorna após 4 segundos
					
					window.focus();					
					elemento.click();
				}			
				
			}, 750);
		};
		elemento.onmouseleave = function (event) {				
			event.preventDefault();
			this.style.animation = 'unset';
			mouseEmCima = false;
			clearInterval(check99);
		};

	}
}

function criarCaixaDeSelecaoComReclamados(excluir=true) {
	//excluir=true cria uma caixa de seleção de reclamados que você deixa apenas aqueles que quer utilizar
	//excluir=false cria uma caixa de seleção de reclamados que vc escolhe apenas um dentre aqueles que aparecem
	return new Promise(
		resolver => {
			if (!document.getElementById('maisPje_caixa_de_selecao')) {
				browser.storage.local.get('processo_memoria', function(result){
					preferencias.processo_memoria = result.processo_memoria;
					
					if (!preferencias.processo_memoria) { resolver(null); return; } //se vazio
					
					if (preferencias.processo_memoria.reu.length == 1) { resolver([{ cpfcnpj: preferencias.processo_memoria.reu[0].cpfcnpj, nome: preferencias.processo_memoria.reu[0].nome }]); return; } //se só possui 1 reclamado
					
					//se possui mais de um reclamado
					let lista_de_executados_temp = [];
					// DESCRIÇÃO: REGRA DO TOOLTIP
					if (!document.getElementById('maisPje_tooltip_fundo')) {
						tooltip('fundo', true);
					}
					
					let altura = window.innerHeight || document.documentElement.clientHeight || document.body.clientHeight;
					
					let elemento1 = document.createElement("div");
					elemento1.id = 'maisPje_caixa_de_selecao';
					elemento1.style = 'position: fixed; width: 100%; height: ' + altura + 'px; top: 0; inset: 0px; background: #00000080; z-index: 100000; display: flex; align-items: center; justify-content: center; color: rgb(81, 81, 81); font-weight: bold; font-family: Open Sans,Arial,Verdana,sans-serif; font-size: 16px; text-align: center; flex-direction: column;';
					
					elemento1.onclick = function (e) {
						if (e.target.id == "maisPje_caixa_de_selecao") {
							elemento1.remove();
						}
					}; //se clicar fora fecha a janela
					
					let container = document.createElement("div");
					container.style="height: auto; min-width: 35vw; display: inline-grid; background-color: white;padding: 15px;border-radius: 4px;box-shadow: 0 2px 1px -1px rgba(0,0,0,.2),0 1px 1px 0 rgba(0,0,0,.14),0 1px 3px 0 rgba(0,0,0,.12);overflow-y: auto;";
					
					let titulo = document.createElement("span");
					titulo.style = "color: grey; border-bottom: 1px solid lightgrey;";
					titulo.innerText = "Lista de Executados";
					titulo.innerText += (excluir) ? " - clique para EXCLUIR" : " - clique para ESCOLHER";
					container.appendChild(titulo);
					
					for (const [pos, executado] of preferencias.processo_memoria.reu.entries()) {
						let span = document.createElement("span");
						span.style = "cursor: pointer; margin-top: 10px; padding: 10px; font-weight: bold; font-size: 16px;";
						span.innerText = executado.nome + " (" + executado.cpfcnpj + ")";
						span.onmouseenter = function () {
							span.style.backgroundColor  = 'lightgrey';
							if (excluir) {
								span.style.color  = 'red';
								span.innerText = "Excluir";
							}
						};
						span.onmouseleave = function () {
							span.style.backgroundColor  = 'white';
							span.style.color  = 'rgb(81, 81, 81)';
							if (excluir) {
								span.innerText = executado.nome + " (" + executado.cpfcnpj + ")";
							}
						};
						span.onclick = function () {
							if (excluir) {
								this.remove();
								lista_de_executados_temp.splice(lista_de_executados_temp.findIndex(e => e.cpfcnpj === executado.cpfcnpj), 1);
							} else {
								resolver([{cpfcnpj: executado.cpfcnpj, nome: executado.nome}]);
								document.getElementById('maisPje_caixa_de_selecao').remove();
							}
						};
						container.appendChild(span);
						lista_de_executados_temp.push({ cpfcnpj: executado.cpfcnpj, nome: executado.nome });
					}
					
					if (excluir) {
						let bt_continuar = document.createElement("span");
						bt_continuar.style = "color: white; margin-top: 10px; padding: 10px; border-bottom: 1px solid lightgrey; background-color: #7a9ec8; border-radius: 3px; cursor: pointer;";
						bt_continuar.innerText = "Continuar";
						bt_continuar.onmouseenter = function () {
							bt_continuar.style.backgroundColor  = '#5077a4';
						};
						bt_continuar.onmouseleave = function () {
							bt_continuar.style.backgroundColor  = '#7a9ec8';
						};
						bt_continuar.onclick = function () {
							resolver(lista_de_executados_temp);
							document.getElementById('maisPje_caixa_de_selecao').remove();
						};
						container.appendChild(bt_continuar);
					}
					
					elemento1.appendChild(container);
					document.body.appendChild(elemento1);
				});
			} else {
				resolver(null);
			}
		}
	);
}

function criarCaixaDeSelecaoComReclamantes() {
	return new Promise(
		resolver => {
			if (!document.getElementById('maisPje_caixa_de_selecao')) {
				browser.storage.local.get('processo_memoria', function(result){
					preferencias.processo_memoria = result.processo_memoria;
					
					if (!preferencias.processo_memoria) { resolver(null); return; } //se vazio
					
					if (preferencias.processo_memoria.autor.length == 1) { resolver([{ cpfcnpj: preferencias.processo_memoria.autor[0].cpfcnpj, nome: preferencias.processo_memoria.autor[0].nome }]); return; } //se só possui 1 reclamado
					
					//se possui mais de um reclamado
					let lista_de_reclamantes_temp = [];
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
						}
					}; //se clicar fora fecha a janela					
					
					let container = document.createElement("div");
					container.style="height: auto; min-width: 35vw; display: inline-grid; background-color: white;padding: 15px;border-radius: 4px;box-shadow: 0 2px 1px -1px rgba(0,0,0,.2),0 1px 1px 0 rgba(0,0,0,.14),0 1px 3px 0 rgba(0,0,0,.12);";
					
					let titulo = document.createElement("span");
					titulo.style = "color: grey; border-bottom: 1px solid lightgrey;";
					titulo.innerText = "Lista de Reclamantes";
					container.appendChild(titulo);
					
					let map = [].map.call(
						preferencias.processo_memoria.autor, 
						function(autor) {
							let executado = autor.nome + " (" + autor.cpfcnpj + ")";
							let span = document.createElement("span");
							span.style = "cursor: pointer; margin-top: 10px; padding: 10px;";
							span.innerText = executado;
							span.onmouseenter = function () {
								span.style.backgroundColor  = 'lightgrey';
								span.style.color  = 'red';
								span.innerText = "Excluir";
							};
							span.onmouseleave = function () {
								span.style.backgroundColor  = 'white';
								span.style.color  = 'rgb(81, 81, 81)';
								span.innerText = executado;
							};
							span.onclick = function () {
								this.remove();
								lista_de_reclamantes_temp.splice(lista_de_reclamantes_temp.findIndex(e => e.cpfcnpj === autor.cpfcnpj), 1);
							};
							container.appendChild(span);
							lista_de_reclamantes_temp.push({ cpfcnpj: autor.cpfcnpj, nome: autor.nome });
						}
						//
					);
					
					let bt_continuar = document.createElement("span");
					bt_continuar.style = "color: white; margin-top: 10px; padding: 10px; border-bottom: 1px solid lightgrey; background-color: #7a9ec8; border-radius: 3px; cursor: pointer;";
					bt_continuar.innerText = "Continuar";
					bt_continuar.onmouseenter = function () {
						bt_continuar.style.backgroundColor  = '#5077a4';
					};
					bt_continuar.onmouseleave = function () {
						bt_continuar.style.backgroundColor  = '#7a9ec8';
					};
					bt_continuar.onclick = function () {
						resolver(lista_de_reclamantes_temp);
						document.getElementById('maisPje_caixa_de_selecao').remove();
					};
					container.appendChild(bt_continuar);
					elemento1.appendChild(container);
					document.body.appendChild(elemento1);
				});
			} else {
				resolver(null);
			}
		}
	);
}

async function criarCaixaDeSelecaoComAAs(label) {
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
					}
				}; //se clicar fora fecha a janela					
				
				let container = document.createElement("div");
				container.style="height: auto; min-width: 35vw; display: inline-grid; background-color: white;padding: 15px;border-radius: 4px;box-shadow: 0 2px 1px -1px rgba(0,0,0,.2),0 1px 1px 0 rgba(0,0,0,.14),0 1px 3px 0 rgba(0,0,0,.12);";
				
				let titulo = document.createElement("span");
				titulo.style = "color: grey; border-bottom: 1px solid lightgrey;";
				titulo.innerText = label;
				container.appendChild(titulo);
				
				let selectAcaoAutomatizada = document.createElement("select");
				selectAcaoAutomatizada.style = 'cursor: pointer; margin-top: 10px; padding: 10px; background-color: white; color: rgb(81, 81, 81); min-height: 40px; font-size:1.125em;';
								
				//Nenhuma
				let optionAA = document.createElement("option");
				optionAA.value = 'Nenhum';
				optionAA.style = 'background-color: coral;';
				optionAA.innerText = 'Nenhum';
				selectAcaoAutomatizada.appendChild(optionAA);
				
				//monta as acoes automatizadas de Anexar Documentos
				let optionGR1 = document.createElement("optgroup");
				optionGR1.label = 'ANEXAR DOCUMENTOS';
				optionGR1.style = 'background-color: lightgray;';
				for (const [pos, item] of preferencias.aaAnexar.entries()) {
					let optionAAA = document.createElement("option");
					optionAAA.value = 'Anexar|' + item.nm_botao;
					optionAAA.innerText = 'Anexar|' + item.nm_botao;
					optionAAA.style = 'background-color: #d3d3d35e;';
					optionGR1.appendChild(optionAAA);
				}
				selectAcaoAutomatizada.appendChild(optionGR1)
				
				//monta as acoes automatizadas de Comunicação
				let optionGR2 = document.createElement("optgroup");
				optionGR2.label = 'INTIMAÇÃO/EXPEDIENTE';
				optionGR2.style = 'background-color: coral;';
				for (const [pos, item] of preferencias.aaComunicacao.entries()) {
					let optionAAC = document.createElement("option");
					optionAAC.value = 'Comunicação|' + item.nm_botao;
					optionAAC.innerText = 'Comunicação|' + item.nm_botao;
					optionAAC.style = 'background-color: #ff7f5021;';
					optionGR2.appendChild(optionAAC);
				}
				selectAcaoAutomatizada.appendChild(optionGR2)
				
				//monta as acoes automatizadas de Autogigs
				let optionGR3 = document.createElement("optgroup");
				optionGR3.label = 'AUTOGIGS';
				optionGR3.style = 'background-color: lightgray;';
				for (const [pos, item] of preferencias.aaAutogigs.entries()) {
					let optionAAG = document.createElement("option");
					optionAAG.value = 'AutoGigs|' + item.nm_botao;
					optionAAG.innerText = 'AutoGigs|' + item.nm_botao;
					optionAAG.style = 'background-color: #d3d3d35e;';
					if (item.nm_botao.includes('[concluir]')) {
						optionAAG.style.color = 'coral';
					}
					optionGR3.appendChild(optionAAG);
				}
				selectAcaoAutomatizada.appendChild(optionGR3)
				
				//monta as acoes automatizadas de Despacho
				let optionGR4 = document.createElement("optgroup");
				optionGR4.label = 'DESPACHO';
				optionGR4.style = 'background-color: coral;';
				for (const [pos, item] of preferencias.aaDespacho.entries()) {
					let optionAAD = document.createElement("option");
					optionAAD.value = 'Despacho|' + item.nm_botao;
					optionAAD.innerText = 'Despacho|' + item.nm_botao;
					optionAAD.style = 'background-color: #ff7f5021;';
					optionGR4.appendChild(optionAAD);
				}
				selectAcaoAutomatizada.appendChild(optionGR4)
				
				//monta as acoes automatizadas de Movimento
				let optionGR5 = document.createElement("optgroup");
				optionGR5.label = 'MOVIMENTOS';
				optionGR5.style = 'background-color: lightgray;';

				let optionAAM = document.createElement("option");
				optionAAM.value = 'Movimento|bt_atualizar_tarefa';
				optionAAM.innerText = '>>>Movimento|Renovar a Data na Tarefa';
				optionAAM.style = 'background-color: #d3d3d35e;';
				optionGR5.appendChild(optionAAM);

				for (const [pos, item] of preferencias.aaMovimento.entries()) {
					optionAAM = document.createElement("option");
					optionAAM.value = 'Movimento|' + item.nm_botao;
					optionAAM.innerText = 'Movimento|' + item.nm_botao;
					optionAAM.style = 'background-color: #d3d3d35e;';
					optionGR5.appendChild(optionAAM);
				}
				selectAcaoAutomatizada.appendChild(optionGR5)
				
				//monta as acoes automatizadas de Checklist
				let optionGR6 = document.createElement("optgroup");
				optionGR6.label = 'CHECKLIST';
				optionGR6.style = 'background-color: coral;';
				for (const [pos, item] of preferencias.aaChecklist.entries()) {
					let optionAAE = document.createElement("option");
					optionAAE.value = 'Checklist|' + item.nm_botao;
					optionAAE.innerText = 'Checklist|' + item.nm_botao;
					optionAAE.style = 'background-color: #ff7f5021;';
					optionGR6.appendChild(optionAAE);
				}
				selectAcaoAutomatizada.appendChild(optionGR6)
				
				
				//monta as acoes automatizadas de Retificar Autuação
				let optionGR7 = document.createElement("optgroup");
				optionGR7.label = 'RETIFICAR AUTUAÇÃO';
				optionGR7.style = 'background-color: lightgray;';
				let aaItemRetificarAutuacao = [['botao_retificar_autuacao_7','addAutor'],['botao_retificar_autuacao_8','addRéu'],['botao_retificar_autuacao_0','addUnião'],['botao_retificar_autuacao_10','addMPT'],['botao_retificar_autuacao_3','addLeiloeiro'],['botao_retificar_autuacao_4','addPerito'],['botao_retificar_autuacao_addTerceiroTerceiro','Terceiro>Terceiro'],['botao_retificar_autuacao_100Digital','Juízo 100% Digital'],['botao_retificar_autuacao_tutelaLiminar','Pedido de Tutela'],['botao_retificar_autuacao_Falencia','Falência/Rec.Judicial'],['botao_retificar_autuacao_assunto','Assunto'],['botao_retificar_autuacao_justicaGratuita','Justiça Gratuita']];

				[].map.call(aaItemRetificarAutuacao,function(item) {
					let optionIRA = document.createElement("option");
					optionIRA.value = 'RetificarAutuação|' + item[0];
					optionIRA.innerText = 'RetificarAutuação|' + item[1];
					optionIRA.style = 'background-color: #d3d3d35e;';
					optionGR7.appendChild(optionIRA);
				});
				selectAcaoAutomatizada.appendChild(optionGR7)
				
				//monta as acoes automatizadas de Lançar Movimentos
				let optionGR8 = document.createElement("optgroup");
				optionGR8.label = 'LANÇAR MOVIMENTOS';
				optionGR8.style = 'background-color: coral;';
				let aaItemLancarMovimentos = [['botao_lancar_movimento_0','Contadoria:atualização'],['botao_lancar_movimento_1','Contadoria:liquidação'],['botao_lancar_movimento_2','Contadoria:retificação'],['botao_lancar_movimento_3','Contadoria:DeterminaçãoJudicial'],['botao_lancar_movimento_4','TRT:recurso'],['botao_lancar_movimento_5','Publicação de Pauta']];
				[].map.call(aaItemLancarMovimentos,function(item) {
					let optionILM = document.createElement("option");
					optionILM.value = 'LançarMovimento|' + item[0];
					optionILM.innerText = 'LançarMovimento|' + item[1];
					optionILM.style = 'background-color: #ff7f5021;';
					optionGR8.appendChild(optionILM);
				});
				selectAcaoAutomatizada.appendChild(optionGR8)
				
				let optionGR9 = document.createElement("optgroup");
				optionGR9.label = 'CLICAR EM';
				optionGR9.style = 'background-color: lightgray;';
				let aaItemMenuDetalhes = ['Abrir o Gigs','Acesso a Terceiros','Anexar documentos','Audiências e Sessões','Download do processo completo','BNDT','Abrir cálculos do processo','Criar Intimação/Expediente','Controle de Segredo','Abre a tela com os dados financeiros','Visualizar intimações/expedientes do processo','Histórico de Sigilo','Lembretes','Lançar movimentos','Obrigação de Pagar','Pagamento','Perícias','Quadro de recursos','Reprocessar chips do processo','Retificar autuação','Retirar Valor Histórico','Verificar Impedimentos e Suspeições'];
				
				[].map.call(aaItemMenuDetalhes,function(item) {
					let optionIMD = document.createElement("option");
					optionIMD.value = 'Clicar em|' + item;
					optionIMD.innerText = 'Clicar em|' + item;
					optionIMD.style = 'background-color: #d3d3d35e;';
					optionGR9.appendChild(optionIMD);
				});
				selectAcaoAutomatizada.appendChild(optionGR9)
				
				let optionGR10 = document.createElement("optgroup");
				optionGR10.label = 'VARIADOS';
				optionGR10.style = 'background-color: coral;';
				let aaItemVariados = ['Atualizar Pagina|Atualizar Pagina','Fechar Pagina|Fechar Pagina','Variados|Apreciar Peticoes','Variados|SISBAJUD:F2'];
				[].map.call(aaItemVariados,function(item) {
					let optionVAR = document.createElement("option");
					optionVAR.value = item;
					optionVAR.innerText = item;
					optionVAR.style = 'background-color: #ff7f5021;';
					optionGR10.appendChild(optionVAR);
				});
				selectAcaoAutomatizada.appendChild(optionGR10)
				
				container.appendChild(selectAcaoAutomatizada);
				
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
					resolver(selectAcaoAutomatizada.value);
					document.getElementById('maisPje_caixa_de_selecao').remove();
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

function criarCaixaDePergunta(tipo, titulo, valorAnterior='', placeholder='') {
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
			container.style="height: auto; min-width: 35vw; display: inline-grid; background-color: white;padding: 15px;border-radius: 4px;box-shadow: 0 2px 1px -1px rgba(0,0,0,.2),0 1px 1px 0 rgba(0,0,0,.14),0 1px 3px 0 rgba(0,0,0,.12);";

			let logo = document.createElement("span");
			logo.style = "color: grey; display: flex;justify-self: end; opacity:50%;";
			logo.innerText = "+PJ";
			let logoi = document.createElement("i");
			logoi.style = "color:#e8571e;font-style: normal;";
			logoi.innerText = "e";
			logo.appendChild(logoi)
			container.appendChild(logo);

			
			let t = titulo.split('|');
			
			let spanTitulo = document.createElement("span");
			spanTitulo.style = "color: grey; border-bottom: 1px solid lightgrey;text-align: justify;";
			spanTitulo.innerText = t[0];
			container.appendChild(spanTitulo);
			
			if (t[1]) { //subtitulo
				let spanSubTitulo = document.createElement("span");
				spanSubTitulo.style = "color: lightcoral;font-style: italic;font-weight: normal;";
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
			btOk.style = "color: white; margin-top: 10px; padding: 10px; border-bottom: 1px solid lightgrey; background-color: #7a9ec8; border-radius: 3px; cursor: pointer;";
			btOk.innerText = "OK";
			btOk.onmouseenter = function () { btOk.style.backgroundColor  = '#5077a4' };
			btOk.onmouseleave = function () { btOk.style.backgroundColor  = '#7a9ec8' };
			btOk.onclick = function () {
				elemento1.remove();
				resolver(inputTexto.value);
			};
			container.appendChild(btOk);

			elemento1.appendChild(container);
			document.body.appendChild(elemento1);

			//atribui o foco ao input
			let check1 = setInterval(async function() {
				if (document.activeElement === inputTexto) { 
					clearInterval(check1);
				} else {
					inputTexto.focus();
				}
			}, 100);
		} else {
			resolver(null);
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
				elemento1.style = 'position: fixed; width: 100%; height: ' + altura + 'px; top: 0; inset: 0px; background: #00000080; z-index: 10000; display: flex; align-items: center; justify-content: center; color: rgb(81, 81, 81); font-weight: bold; font-family: Open Sans,Arial,Verdana,sans-serif; text-align: center; flex-direction: column;';
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
					div.style = "color: rgba(0, 0, 0, 0.87); margin: 1vh 0px 1vh 40%; text-align: left;display: grid;grid-template-columns: 1fr 10fr;align-items: center;min-height: 5vh;";
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

async function criarCaixaDeAlerta(titulo='ALERTA', mensagem='Erro padrão', temporizador=0, tipoBotao=1) { //em segundos não milissegundos
	return new Promise(async resolver => {
			if (!document.getElementById('maisPje_caixa_de_alerta')) {
										
				// DESCRIÇÃO: REGRA DO TOOLTIP
				if (!document.getElementById('maisPje_tooltip_fundo')) {
					tooltip('fundo', true);
				}
				
				let altura = window.innerHeight || document.documentElement.clientHeight || document.body.clientHeight;
				
				let elemento1 = document.createElement("div");
				elemento1.id = 'maisPje_caixa_de_alerta';
				elemento1.style = 'position: fixed; width: 100%; height: ' + altura + 'px; top: 0; inset: 0px; background: #00000080; z-index: 10000; display: flex; align-items: center; justify-content: center; color: rgb(81, 81, 81); font-weight: bold; font-family: Open Sans,Arial,Verdana,sans-serif; text-align: center; flex-direction: column;';
				// elemento1.onclick = function (e) {
					// if (e.target.id == "maisPje_caixa_de_alerta") {
						// elemento1.remove();
					// }
				// }; //se clicar fora fecha a janela					
				
				let container = document.createElement("div");
				container.style="font-family: Open Sans,Arial,Verdana,sans-serif; height: auto; min-width: 35vw; display: inline-grid; background-color: white;padding: 15px;border-radius: 4px;box-shadow: 0 2px 1px -1px rgba(0,0,0,.2),0 1px 1px 0 rgba(0,0,0,.14),0 1px 3px 0 rgba(0,0,0,.12);";

				let logo = document.createElement("span");
				logo.style = "font-family: Open Sans,Arial,Verdana,sans-serif; font-size: 1.4em; color: grey; display: flex;justify-self: end; opacity:50%;";
				logo.innerText = "+PJ";
				let logoi = document.createElement("i");
				logoi.style = "color:#e8571e;font-style: normal;font-size: 1em;";
				logoi.innerText = "e";
				logo.appendChild(logoi)
				container.appendChild(logo);
				
				let t = document.createElement("span");
				t.style = "font-family: Open Sans,Arial,Verdana,sans-serif; font-size: 1.5em; color: grey; border-bottom: 1px solid lightgrey;";
				t.innerText = titulo;
				container.appendChild(t);
				
				let div = document.createElement("div");
				div.style = 'font-family: Open Sans,Arial,Verdana,sans-serif; display: grid; grid-template-columns: 64px auto;min-height: 85px;align-content: center;';
				
				let img = document.createElement("img");
				// img.className = "maisPje-img";
				img.src = browser.runtime.getURL("icons/ico_64_alerta2.png");
				div.appendChild(img);
				
				
				let m = document.createElement("span");
				m.style = "font-family: Open Sans,Arial,Verdana,sans-serif; font-size: 1.5em; color: chocolate; font-style: normal; font-weight: normal;text-align: center;margin: auto auto auto 20px;";
				m.innerText = mensagem;
				div.appendChild(m);
				
				container.appendChild(div);
				
				let bt_continuar = document.createElement("span");
				bt_continuar.id = 'maisPje_caixa_de_alerta_bt_continuar';
				bt_continuar.style = "font-family: Open Sans,Arial,Verdana,sans-serif;  font-size: 1.5em; color: white; margin-top: 10px; padding: 10px; border-bottom: 1px solid lightgrey; background-color: rgba(80, 119, 164); border-radius: 3px; cursor: pointer;";
				bt_continuar.innerText = "Entendi";
				bt_continuar.onmouseenter = function () {
					bt_continuar.style.backgroundColor  = 'rgba(80, 119, 164, .3)';
				};
				bt_continuar.onmouseleave = function () {
					bt_continuar.style.backgroundColor  = 'rgba(80, 119, 164)';
				};
				bt_continuar.onclick = function () { 
					document.getElementById('maisPje_caixa_de_alerta')?.remove();
					resolver(true);
				};
				
				
				
				
				if (tipoBotao == 2) {
					// Na timeline do processo, no dia 23/07/2018, existe um movimento
					//obtém a data da mensagem e cria o link para a timeline do processo
					let data = mensagem;
					let padraoData = /\d{1,2}\/\d{1,2}\/\d{4}/gm;
					if (padraoData.test(data)) {
						data = data.match(padraoData).join();
						let dataConvertida = await converterDataTimeline(data);
						console.log('Data encontrada: ' + dataConvertida);
						
						let bt_corrigir = document.createElement("span");
						bt_corrigir.id = 'maisPje_caixa_de_alerta_bt_corrigir';
						bt_corrigir.style = "color: white; margin-top: 10px; padding: 10px; border-bottom: 1px solid lightgrey; background-color: darkseagreen; border-radius: 3px; cursor: pointer;";
						bt_corrigir.innerText = "Ir para " + data;
						bt_corrigir.onmouseenter = function () {
							bt_corrigir.style.backgroundColor  = '#4b954b';
						};
						bt_corrigir.onmouseleave = function () {
							bt_corrigir.style.backgroundColor  = 'darkseagreen';
						};
						bt_corrigir.onclick = async function () {
							
							container.style.filter = "brightness(0.5)";
							
							if (!document.querySelector('button[aria-label="Ocultar movimentos."]')) {
								await clicarBotao('button[aria-label="Exibir movimentos."]',null, true);
							}
							
							let naTimeLine = await esperarElemento('div[name="dataItemTimeline"]',dataConvertida);
							naTimeLine.scrollIntoView({behavior: 'smooth',block: 'start'});
							
							//arruma o cabeçalho
							let cabecalho = document.querySelector('mat-sidenav-container[class*="mat-drawer-container"]');							
							if (!cabecalho) { return }
							cabecalho.style.setProperty("position", "relative", "important");
							cabecalho.style.setProperty("height", "auto", "important");
							
							document.getElementById('maisPje_caixa_de_alerta')?.remove();
							resolver(true);
						};
						container.appendChild(bt_corrigir);
						bt_continuar.innerText = "Ignorar";
					}
				}
				
				container.appendChild(bt_continuar);
				elemento1.appendChild(container);
				document.body.appendChild(elemento1);
				
				//criar listener para tecla pressionada
				let eventoOuvirTecla = function(evt) {
					// console.log("---> " + evt.key)
					if (evt.key === "Enter") {
						document.getElementById('maisPje_caixa_de_alerta')?.remove();
						window.removeEventListener("keydown", eventoOuvirTecla);
						resolver(true);
					}
				}			
				window.addEventListener('keydown', eventoOuvirTecla);				
				
				if (temporizador > 0) {	await timer(bt_continuar, temporizador) }
				
			} else {
				resolver(null);
			}
		}
	);
	
	async function converterDataTimeline(inputFormat) {
		console.log("Inicio: " + inputFormat);
		inputFormat = inputFormat.replace("\/01\/" , " jan. ");
		inputFormat = inputFormat.replace("\/02\/" , " fev. ");
		inputFormat = inputFormat.replace("\/03\/" , " mar. ");
		inputFormat = inputFormat.replace("\/04\/" , " abr. ");
		inputFormat = inputFormat.replace("\/05\/" , " mai. ");
		inputFormat = inputFormat.replace("\/06\/" , " jun. ");
		inputFormat = inputFormat.replace("\/07\/" , " jul. ");
		inputFormat = inputFormat.replace("\/08\/" , " ago. ");
		inputFormat = inputFormat.replace("\/09\/" , " set. ");
		inputFormat = inputFormat.replace("\/10\/" , " out. ");
		inputFormat = inputFormat.replace("\/11\/" , " nov. ");
		inputFormat = inputFormat.replace("\/12\/" , " dez. ");
		console.log("Fim: " + inputFormat);
		return inputFormat;
	}
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
		fundo.style = "position: fixed; width: 100%; height: 100%; inset: 0px; background: #000000c4; z-index: 10000; display: flex; align-items: center; color: rgb(81, 81, 81); font-size: 80px; font-weight: bold; text-align: center; text-shadow: rgb(0, 0, 0) 1px 1px; flex-direction: column; top: 62vh;";
		
		let barra_descricao = document.createElement("div");
		barra_descricao.style = "overflow-y: auto; opacity: 0.98; text-align: center; color: white; font-size: 14px; height: auto;padding: 28px;text-shadow: none;";
		barra_descricao.innerText = descricao + '\n\n\nMapeamento dos Vínculos:';
		
		let barra_mapaVinculos = document.createElement("div");
		barra_mapaVinculos.style = "overflow-y: auto; opacity: 0.98; text-align: center; color: white;font-size: 14px;";
		
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
					separador.className = 'botao-menu-texto fa fa-arrow-right';
					separador.style = 'color: white;height: 4vh;margin: 3px;display: inline-block;padding: 0 16px;vertical-align: -moz-middle-with-baseline;';
					barra_mapaVinculos.appendChild(separador);
				}
			}
		}
		
		fundo.appendChild(barra_descricao);
		fundo.appendChild(barra_mapaVinculos);
		container.appendChild(fundo);
		document.body.appendChild(container);
		resolver(true);
	});
}

async function assistenteDeImpressao() {

	if (document.querySelector('assistenteimpressaomaispje')) { return }

	console.log("Extensão maisPJE (" + agora() + "): assistenteDeImpressao");
	//CARREGA O PACOTE DE ÍCONES PARA A PÁGINA E O CSS DO MENU
	browser.runtime.sendMessage({tipo: 'insertCSS', file: 'maisPje_icones.css'});
	var listapaginasTemp = await carregarPaginasStorage();
	var convenio = await getConvenio();
	if (!convenio) { return }
	
	//cria os listeners para o alvo
	var listenerclick = async function(e) {
		e.preventDefault();
		
		//sniper
		if (convenio.nome == 'sniper' && document.body?.hasAttribute('maisPje-impressao')) { //janela de impressão do Convênio
			convenio.alvo = 'body[maisPje-impressao]';
		}
		
		let alvo = document.querySelector(convenio.alvo2) || document.querySelector(convenio.alvo);
		// console.log('***************************** <' + alvo.tagName + ' class=' + alvo.className);
		if (alvo) {
			alvo.style.filter = 'brightness(50%)';
			alvo.style.backgroundColor = 'gray';
			document.querySelector('assistenteImpressaoMaisPje').style.backgroundColor = 'rgb(154, 217, 141)';
			await novaPagina();
			await sleep(100);
			document.querySelector('assistenteImpressaoMaisPje').style.backgroundColor = '#dadada';
			alvo.style.filter = 'revert';
			alvo.style.backgroundColor = 'revert';
		} else {
			document.querySelector('assistenteImpressaoMaisPje').style.backgroundColor = 'rgb(217, 141, 141)';
			await sleep(100);
			document.querySelector('assistenteImpressaoMaisPje').style.backgroundColor = '#dadada';
		}
	}
	
	await criarJanela();
	
	async function criarJanela() {
		return new Promise(
			async resolver => {
				//criar estrutura de elementos da janela do assistente
				let assistenteImpressaoMaisPje = document.createElement("assistenteImpressaoMaisPje");
				assistenteImpressaoMaisPje.id = "maisPje_assistenteImpressao_" + convenio.nome;
				assistenteImpressaoMaisPje.className = 'maisPje-no-print';
				assistenteImpressaoMaisPje.style = "position: fixed;" + convenio.posy + convenio.posx + "width: 220px; opacity: 1; min-width: 220px; height: 11vh; min-height: 11vh; display: grid; align-items: center;justify-content: center;z-index: 1000; grid-template-rows: 1fr 1fr auto;background-color: #dadada; padding: 15px; border-radius: 4px;box-shadow: 0 3px 3px -2px rgba(0,0,0,.3),0 3px 4px 0 rgba(0,0,0,.3),0 1px 8px 0 rgba(0,0,0,.3);cursor: move;";
				assistenteImpressaoMaisPje.draggable = true;
				
				let container = document.createElement("div");
				container.id = "maisPje_assistenteImpressao_container";
				container.style="display: grid; grid-template-rows: 1fr 1fr auto; justify-content: center;width: 100%;"
				
				let titulo = document.createElement("span");
				titulo.id = "maisPje_assistenteImpressao_titulo";
				titulo.style = "margin-bottom: 5px; height: 25px; color: grey; border-bottom: 1px solid grey; font-size:14px;";
				titulo.innerText = "Assistente de Impressão";
				container.appendChild(titulo);
				
				let i_paginas = document.createElement("i");
				i_paginas.id = "maisPje_assistenteImpressao_info_paginas";
				i_paginas.innerText = '0';
				i_paginas.style = "font-size: 16px; font-style: normal; font-weight: bold; margin-left: 15px;";
				titulo.appendChild(i_paginas);
				
				let barra_botoes = document.createElement("span");
				barra_botoes.id = "maisPje_assistenteImpressao_barra_botoes";
				barra_botoes.style = "height: 25px; display: grid; grid-template-columns: repeat(5, 1fr); gap: 6px; direction: rtl; align-items: center; cursor: pointer;";
				
				let bt_fechar = document.createElement("button");
				bt_fechar.id = "maisPje_assistenteImpressao_bt_fechar";
				bt_fechar.style = "display: flex; width: 25px; height: 25px; background-color: #ccc; border: 0; border-radius: 3px; cursor: pointer; justify-content: center; align-items: center; padding: 0;";
				bt_fechar.title = "Fechar";
				bt_fechar.onmouseenter = function () {
					this.firstElementChild.style.backgroundColor  = '#ccc';
					this.style.backgroundColor  = 'darkred';
				};
				bt_fechar.onmouseleave = function () {
					this.firstElementChild.style.backgroundColor  = 'gray';
					this.style.backgroundColor  = '#ccc';
				};
				bt_fechar.onclick = async function () {
					document.querySelector('assistenteImpressaoMaisPje').remove();
				};
				let i_fechar = document.createElement("i");
				i_fechar.className = "icone fechar t18";
				bt_fechar.appendChild(i_fechar);
				barra_botoes.appendChild(bt_fechar);
				container.appendChild(barra_botoes);
				
				let bt_maximizar = document.createElement("button");
				bt_maximizar.style = "display: flex; width: 25px; height: 25px; background-color: #ccc; border: 0; border-radius: 3px; cursor: pointer; justify-content: center; align-items: center; padding: 0;";
				bt_maximizar.title = "Maximizar";
				bt_maximizar.onmouseenter = function () {
					this.firstElementChild.style.backgroundColor  = '#ccc';
					this.style.backgroundColor  = 'gray';
				};
				bt_maximizar.onmouseleave = function () {
					this.firstElementChild.style.backgroundColor  = 'gray';
					this.style.backgroundColor  = '#ccc';
				};
				bt_maximizar.onclick = function () {
					if (this.querySelector('i[class*="minimize"]')) { // minimizar
						document.querySelector('assistenteImpressaoMaisPje').style.setProperty('min-height', '11vh');
						document.querySelector('assistenteImpressaoMaisPje').style.setProperty('height', '11vh');
						document.getElementById('maisPje_assistenteImpressao_div_body').style.display = 'none';
						
						this.setAttribute('title','Maximizar');
						this.querySelector('i').className = "icone maximize t18";	
						
						
					} else if (this.querySelector('i[class*="maximize"]')) { // maximizar
						document.querySelector('assistenteImpressaoMaisPje').style.setProperty('min-height', '74vh');
						document.querySelector('assistenteImpressaoMaisPje').style.setProperty('height', '74vh');
						document.getElementById('maisPje_assistenteImpressao_div_body').style.display = 'inherit';
						
						this.setAttribute('title','Minimizar');
						this.querySelector('i').className = "icone minimize t18";						
					}
					
				};
				let i_maximizar = document.createElement("i");
				i_maximizar.className = "icone maximize t18";
				bt_maximizar.appendChild(i_maximizar);
				barra_botoes.appendChild(bt_maximizar);
				
				let bt_limpar = document.createElement("button");
				bt_limpar.style = "display: flex; width: 25px; height: 25px; background-color: #ccc; border: 0; border-radius: 3px; cursor: pointer; justify-content: center; align-items: center; padding: 0;";
				bt_limpar.title = "Excluir tudo";
				bt_limpar.onmouseenter = function () {
					this.firstElementChild.style.backgroundColor  = '#ccc';
					this.style.backgroundColor  = 'gray';
				};
				bt_limpar.onmouseleave = function () {
					this.firstElementChild.style.backgroundColor  = 'gray';
					this.style.backgroundColor  = '#ccc';
				};
				bt_limpar.onclick = async function () {
					limparImpressora();
				};
				let i_limpar = document.createElement("i");
				i_limpar.className = "icone lixeira t18";
				bt_limpar.appendChild(i_limpar);
				barra_botoes.appendChild(bt_limpar);
				
				let bt_print = document.createElement("button");
				bt_print.style = "display: flex; width: 25px; height: 25px; background-color: #ccc; border: 0; border-radius: 3px; cursor: pointer; justify-content: center; align-items: center; padding: 0;";
				bt_print.title = "Imprimir";
				bt_print.onmouseenter = function () {
					this.firstElementChild.style.backgroundColor  = '#ccc';
					this.style.backgroundColor  = 'gray';
				};
				bt_print.onmouseleave = function () {
					this.firstElementChild.style.backgroundColor  = 'gray';
					this.style.backgroundColor  = '#ccc';
				};
				bt_print.onclick = function () {
					abrirPaginaImpressao();
				};
				let i_print = document.createElement("i");
				i_print.className = "icone impressora t18";
				bt_print.appendChild(i_print);
				barra_botoes.appendChild(bt_print);
				
				let bt_copiar = document.createElement("button");
				bt_copiar.id = "maisPje_assistenteImpressao_bt_copiar";
				bt_copiar.style = "display: flex; width: 25px; height: 25px; background-color: #ccc; border: 0; border-radius: 3px; cursor: pointer; justify-content: center; align-items: center; padding: 0;";
				bt_copiar.title = "Copiar (Atalho: p)";
				bt_copiar.onmouseenter = function () {
					this.firstElementChild.style.backgroundColor  = '#ccc';
					this.style.backgroundColor  = 'darkgreen';
				};
				bt_copiar.onmouseleave = function () {
					this.firstElementChild.style.backgroundColor  = 'gray';
					this.style.backgroundColor  = '#ccc';
				};
				bt_copiar.onclick = listenerclick;
				let i_copiar = document.createElement("i");
				i_copiar.className = "icone adicionar t18";
				bt_copiar.appendChild(i_copiar);
				barra_botoes.appendChild(bt_copiar);
				
				let div_body = document.createElement("div");
				div_body.id = "maisPje_assistenteImpressao_div_body";
				div_body.style = "display: inline; width: 100%;height: 61vh;overflow-y: auto;margin-top: 8px; display: none;"
				
				container.appendChild(div_body);	
				assistenteImpressaoMaisPje.appendChild(container);				
				document.body.appendChild(assistenteImpressaoMaisPje);
				maisPjeTornarArrastavel(assistenteImpressaoMaisPje);				
				
				// recupera paginas do Storage
				for (const [pos, paginaStorage] of listapaginasTemp.entries()) {
					await novaPagina(paginaStorage);
				}
			}
		);
	}

	async function novaPagina(p) {
		return new Promise(
			async resolver => {
				let qtdePaginas = parseInt(document.getElementById('maisPje_assistenteImpressao_info_paginas').innerText) + 1;
				let moldura = document.createElement("div");
				moldura.id = "maisPje_assistenteImpressao_moldura_" + qtdePaginas;
				moldura.style="display: flex;height: 36vh; min-height: 36vh; background-color: white; margin-bottom: 10px; border-radius: 0px;box-shadow: 0 2px 1px -1px rgba(0,0,0,.2),0 1px 1px 0 rgba(0,0,0,.14),0 1px 3px 0 rgba(0,0,0,.12);overflow: hidden;text-overflow: clip;cursor: pointer;";
				moldura.onmouseenter = function () {
					if (document.getElementById(this.id + "_excluir")) { return }
					this.style.filter = 'brightness(35%) invert(0)';
					let aviso = document.createElement('i');
					aviso.id = this.id + "_excluir";
					aviso.className = 'icone trash-alt t32';
					aviso.style = 'position: absolute;  height: 36vh; background-color: #353535; left: 35%; width: 3em;pointer-events: none; z-index:9999;';
					this.appendChild(aviso);
				}
				moldura.onmouseleave = function () {
					this.style.filter = 'revert';
					document.getElementById(this.id + "_excluir").remove();
				}
				moldura.onclick = async function () {
					let paginaExcluida = parseInt(this.id.replace('maisPje_assistenteImpressao_moldura_','')) - 1;
					listapaginasTemp.splice(paginaExcluida, 1);
					let var1 = await browser.storage.local.set({'impressoraVirtual': listapaginasTemp});
					Promise.all([var1]).then(values => { 
						this.remove();
						document.getElementById('maisPje_assistenteImpressao_info_paginas').innerText = parseInt(document.getElementById('maisPje_assistenteImpressao_info_paginas').innerText) - 1;
					});
				}
				
				let pagina = document.createElement("div");
				pagina.id = "maisPje_assistenteImpressao_pagina_" + qtdePaginas;
				pagina.style="transform: scale(50%);transform-origin: top left;";
				let informacoes_adicionais_titulo = '';
				
				if (p) {
					//TODO: nao faco ideia do que fazer com isso! poderia ser visto como brecha de seguranca, ja que vem do storage e o usuario poderia alterar
					// pagina.innerHTML = p; //repõe pagina do storage
					addPaginaFromStorage(p, pagina)
					moldura.appendChild(pagina);
					document.getElementById('maisPje_assistenteImpressao_div_body').appendChild(moldura);
					document.getElementById('maisPje_assistenteImpressao_info_paginas').innerText = qtdePaginas;
					resolver(true);
				} else {
					let ancora = document.querySelector(convenio.alvo);
					
					if (convenio.nome == 'renajud') {
						//verifica se existe o alvo2 e se ele está ativo
						let el_ref_alvo2 = document.querySelector(convenio.alvo2);						
						if (el_ref_alvo2) {
							let oculto = el_ref_alvo2.parentElement.parentElement.parentElement.hasAttribute('aria-hidden');
							ancora = (!oculto) ? el_ref_alvo2 : ancora.parentElement;
						} else {
							ancora = ancora.parentElement;
						}
						// console.log('***************************** <' + ancora.tagName + ' class=' + ancora.className);
					}
					
					if (convenio.nome == 'censec') {
						//verifica se existe o alvo2 e se ele está ativo
						let el_ref_alvo2 = document.querySelector(convenio.alvo2);						
						if (el_ref_alvo2) {
							let oculto = el_ref_alvo2.parentElement.parentElement.parentElement.hasAttribute('hidden');
							console.log('oculto: ' + oculto)
							ancora = (!oculto) ? el_ref_alvo2 : ancora;
						}
						
						if (!ancora) {
							ancora = document.querySelector('div[class="material-table"] mat-table'); //ngx-loading
						}
						ancora = ancora.parentElement;
					}
					
					if (convenio.nome == 'casan') {
						ancora = ancora.parentElement;
					}
					
					if (convenio.nome == 'sniper') {
						//verifica se existe o alvo2 e se ele está ativo
						let el_ref_alvo2 = document.querySelector(convenio.alvo2);						
						if (el_ref_alvo2) {
							ancora = el_ref_alvo2;
							informacoes_adicionais_titulo = ' (Lista de processos DATAJUD)';
						}						
						ancora = ancora.parentElement;
					}
					
					if (convenio.nome == 'crcjud') {
						//verifica se existe o alvo2 e se ele está ativo
						let el_ref_alvo2 = document.querySelector(convenio.alvo2);						
						if (el_ref_alvo2) {
							ancora = el_ref_alvo2;
						}
					}
					
					// pagina.innerHTML = ancora.innerHTML;
					addPaginaFromStorage(ancora.innerHTML, pagina)
					// pagina.replaceChildren(...ancora); 
					// // alternativa
					// pagina.replaceChildren();
					// pagina.insertAdjacentElement('beforebegin', ancora);
					// // alternativa 2:
					// pagina.insertAdjacentHTML('beforebegin', ancora.innerHTML);


					
					if (pagina.firstElementChild) {
						pagina.firstElementChild.style.filter = "reverse"; //retira o efeito do copiar
						pagina.firstElementChild.style.backgroundColor = "unset"; //retira o efeito do copiar
					} else {
						pagina.style.filter = "reverse"; //retira o efeito do copiar
						pagina.style.backgroundColor = "unset"; //retira o efeito do copiar						
					}
					
					
					let partePesquisada;
					//ajuste de elementos na impressão
					
					if (pagina.querySelector('assistenteimpressaomaispje')) { pagina.querySelector('assistenteimpressaomaispje').remove() } //remove qualquer resquício do assistente de impressão
					switch (convenio.nome) {
						case 'crcjud':
							await sleep(250);						
							
							partePesquisada = (document.querySelector(convenio.alvo2)) ? '' : document.querySelector('input[name="nome_registrado"]').value + ' (CPF n. ' + document.querySelector('input[name="cpf_registrado"]').value + ')';
							
							// if (pagina.querySelector('h1')) {
							// 	pagina.innerHTML = '<h1 style="font-size: 22px;background-color: #425B4A;color: white;margin-top: 20px;">' + partePesquisada + '</h1>' + pagina.innerHTML;
							// } else {
							// 	pagina.innerHTML = '<h1 style="font-size: 22px;background-color: #425B4A;color: white;margin-top: 20px;">' + partePesquisada + '</h1>' + pagina.innerHTML;
							// }
							const cabecalhoImpressao = criarElemento('h1', "font-size: 22px;background-color: #425B4A;color: white;margin-top: 20px;", partePesquisada)
							pagina.insertAdjacentElement('afterbegin', cabecalhoImpressao);

						
							if (pagina.querySelector('div[class="links"]')) { pagina.querySelector('div[class="links"]').remove() }
							if (pagina.querySelector('br')) { pagina.querySelector('br').remove() }
							
							for (const [pos, el] of pagina.querySelectorAll('div[class*="ui-widget-header"]').entries()) {
								el.remove();
							}
							for (const [pos, el] of pagina.querySelectorAll('table thead').entries()) {
								el.remove();
							}
							if (pagina.querySelector('textarea[id="obs_solicitacao"]')) { pagina.querySelector('textarea[id="obs_solicitacao"]').parentElement.remove() }
							if (pagina.querySelector('input[id="btn_certidao"]')) { pagina.querySelector('input[id="btn_certidao"]').remove() }
							break;
						case 'censec':
							await sleep(250);
							
							//INFORMAÇÕES ADICIONAIS
							if (document.querySelector('mat-sidenav-content')) {
								if (document.querySelector('mat-sidenav-content').innerText.includes('CESDI')) {
									informacoes_adicionais_titulo = " (CESDI)";
								} else if (document.querySelector('mat-sidenav-content').innerText.includes('CEP')) {
									informacoes_adicionais_titulo = " (CEP)";
								}
							}
							
							if (document.querySelector('input[formcontrolname="cpfCnpj"')) {
								partePesquisada = await getExecutado(document.querySelector('input[formcontrolname="cpfCnpj"]').value);
								// pagina.innerHTML = '<h1 style="font-size: 17px;background-color: #6c757d;color: white;margin-top: 20px;padding: 3px;">' + partePesquisada.nome + ' (CPF/CNPJ n. ' + partePesquisada.cpfcnpj + ')' + '</h1>' + pagina.innerHTML;
								const cabecalhoImpressao = criarCabecalhoNome(partePesquisada.nome, partePesquisada.cpfcnpj)
								pagina.insertAdjacentElement('afterbegin', cabecalhoImpressao);
							}
							
							if (pagina.querySelector('h1[class="component-title"]')) { pagina.querySelector('h1[class="component-title"]').remove() }
							for (const [pos, el] of pagina.querySelectorAll('mat-divider').entries()) {
								el.remove();
							}
							for (const [pos, el] of pagina.querySelectorAll('mat-paginator').entries()) {
								el.remove();
							}
							for (const [pos, el] of pagina.querySelectorAll('ngx-loading').entries()) {
								el.remove();
							}
							for (const [pos, el] of pagina.querySelectorAll('mat-header-cell[class*="mat-column-botaoDetalhes"]').entries()) {
								el.remove();
							}
							for (const [pos, el] of pagina.querySelectorAll('mat-cell[class*="mat-column-botaoDetalhes"]').entries()) {
								el.remove();
							}
							for (const [pos, el] of pagina.querySelectorAll('*[class*="d-none"]').entries()) {
								el.classList.remove("d-none");
							}
							for (const [pos, el] of pagina.querySelectorAll('mat-table[class*="mat-table"]').entries()) {
								el.style.display = 'grid';
							}						
							for (const [pos, el] of pagina.querySelectorAll('mat-header-row[class*="mat-header-row"]').entries()) {
								if (el.children.length > 9) {
									el.style="display: grid;grid-template-columns: repeat(10,1fr);";
								} else {
									el.style="display: grid;grid-template-columns: 1fr 1fr;";
								}								
							}
							for (const [pos, el] of pagina.querySelectorAll('mat-row[class*="mat-row"]').entries()) {
								if (el.children.length > 9) {
									el.style="display: grid;grid-template-columns: repeat(10,1fr);";
								} else {
									el.style="display: grid;grid-template-columns: 1fr 1fr;";
								}
							}
							//tirar o class column						
							for (const [pos, el] of pagina.querySelectorAll('div[class="row"]').entries()) {
								el.style="display: grid;grid-template-columns: repeat(3,1fr);";
							}
							for (const [pos, el] of pagina.querySelectorAll('div[class="col-12"]').entries()) {
								el.className = '';
							}
							for (const [pos, el] of pagina.querySelectorAll('lac-table[matsortactive="telefone"] *[role="row"]').entries()) {
								el.style="display: grid;grid-template-columns: repeat(4,1fr);";
							}
							//tabela referentes
							for (const [pos, el] of pagina.querySelectorAll('mat-header-cell[class*="mat-column-viewReferente"]').entries()) {
								el.parentElement.style = "display: grid; grid-template-columns: repeat(4,1fr)";
								el.remove();
							}
							for (const [pos, el] of pagina.querySelectorAll('mat-cell[class*="mat-column-viewReferente"]').entries()) {
								el.parentElement.style = "display: grid; grid-template-columns: repeat(4,1fr)";
								el.remove();
							}
							for (const [pos, el] of pagina.querySelectorAll('mat-cell').entries()) {
								el.style.fontSize = '.7rem';
							}

							break;
						case 'sniper':
							await sleep(250);
							if (pagina.querySelector('div[class="graph-icon"]')) {	pagina.querySelector('div[class="graph-icon"]').remove() }
							if (pagina.querySelector('div[class="graph-info-buttons"]')) {	pagina.querySelector('div[class="graph-info-buttons"]').remove() }
							if (pagina.querySelector('div[class="graph-info-search"]')) {	pagina.querySelector('div[class="graph-info-search"]').remove() }
							if (pagina.querySelector('div[class="links"]')) {	pagina.querySelector('div[class="links"]').remove() }
							if (pagina.querySelector('h1')) { pagina.querySelector('h1').style.fontSize = '22px'}
							if (pagina.querySelector('div[class="graph-info-content"]')) {	pagina.querySelector('div[class="graph-info-content"]').style = '' }
							
							for (const [pos, el] of pagina.querySelectorAll('button').entries()) {
								el.remove();
							}
							
							for (const [pos, el] of pagina.querySelectorAll('h2[class="data-title"]').entries()) {
								if (el.innerText.includes('Dados')) {
									el.remove();
								}
							}
							
							for (const [pos, el] of pagina.querySelectorAll('div[class="key"]').entries()) {
								el.style = 'background-color: rgb(0, 105, 91); color: white;padding-left: 5px;';
							}
							
							if (pagina.querySelector('div[class="graph"]')) {
								pagina.querySelector('div[class="graph"]').style = "display: flex;justify-content: center;margin: 25px 0;";
							}
							
							if (pagina.querySelector('div[class="graph"]')) {
								pagina.querySelector('img[id="graph-image"]').style = "width: 70%; border: 1px solid rgb(245, 245, 245); background-color: #f5f5f5;";
							}							
							
							//datajud
							let nomeDatajud = '';
							let cpfCnpjDatajud = '';
							if (pagina.querySelector(convenio.alvo2)) {
								pagina.querySelector(convenio.alvo2).style.filter = "reverse"; //retira o efeito do copiar
								pagina.querySelector(convenio.alvo2).style.backgroundColor = "unset"; //retira o efeito do copiar
							}
							
							for (const [pos, el] of document.querySelectorAll('section div[class="details-cell"]').entries()) {
								console.log('***  ' + el.innerText);
								if (el.innerText.includes('CNPJ')) {
									cpfCnpjDatajud = el.querySelector('div[class="details-value"]').innerText;
								}
								if (el.innerText.includes('Razão social')) {
									nomeDatajud = el.querySelector('div[class="details-value"]').innerText;
									break;
								}
								if (el.innerText.includes('CPF')) {
									cpfCnpjDatajud = el.querySelector('div[class="details-value"]').innerText;
									break;
								}
								if (el.innerText.includes('Nome')) {
									nomeDatajud = el.querySelector('div[class="details-value"]').innerText;
								}
							}
							
							for (const [pos, el] of pagina.querySelectorAll('table[class="generic-table "] tr').entries()) {
								el.style = 'background-color: white; border-bottom: 3px solid #b8b8b8; display: grid; grid-template-columns: 2fr 1fr 1fr 1fr 1fr 1fr 1fr;';
							}
							
							for (const [pos, el] of pagina.querySelectorAll('table[class="generic-table "] td, table[class="generic-table "] th').entries()) {
								el.style = 'border: .02rem solid #cfcfcf; text-align: left;';
							}
							
							for (const [pos, el] of pagina.querySelectorAll('table[class="generic-table "]').entries()) {
								el.style = 'border-spacing: 0;font-size: 1vw;width: 100%;';
								el.className = '';
								//TODO: isso ta dentro de um loop, eh isso mesmo?
								// pagina.innerHTML = '<h1 style="font-size: 17px;background-color: rgb(0, 53, 46);color: white;margin-top: 20px;padding: 3px;">' + nomeDatajud + ' (CPF/CNPJ n. ' + cpfCnpjDatajud + ')' + '</h1>' + pagina.innerHTML;
								const estiloCabecalho = "font-size: 17px;background-color: rgb(0, 53, 46);color: white;margin-top: 20px;padding: 3px;"
								//TODO: ver com Fernando a questao da cor distinta rgb(0, 53, 46) vs #6c757d (verde escuro vs verde meio cinza)
								const cabecalhoImpressao = criarCabecalhoNome(nomeDatajud, cpfCnpjDatajud, estiloCabecalho); 

								pagina.insertAdjacentElement('afterbegin', cabecalhoImpressao);
							}
							
							break;
						case 'casan':
							await sleep(250);						
							if(pagina.querySelector('table')) { pagina.querySelector('table').style.filter = 'unset' }
							break;
						case 'celesc':
							for (const [pos, el] of pagina.querySelectorAll('a[type="button"]').entries()) {
								el.remove();
							}
							break;
						case 'renajud':
							if (document.querySelector('input[id="documentoIdentificacao"]')) {
								partePesquisada = await getExecutado(document.querySelector('input[id="documentoIdentificacao"]').value);
								// pagina.innerHTML = '<h1 style="font-size: 17px;background-color: #6c757d;color: white;margin-top: 20px;padding: 3px;">' + partePesquisada.nome + ' (CPF/CNPJ n. ' + partePesquisada.cpfcnpj + ')' + '</h1>' + pagina.innerHTML;
								const cabecalhoImpressao = criarCabecalhoNome(partePesquisada.nome, partePesquisada.cpfcnpj);
								pagina.insertAdjacentElement('afterbegin', cabecalhoImpressao);
							}
						
							for (const [pos, el] of pagina.querySelectorAll('input[type="checkbox"]').entries()) {
								el.remove();
							}
							for (const [pos, el] of pagina.querySelectorAll('button[type="button"]').entries()) {
								el.remove();
							}
							for (const [pos, el] of pagina.querySelectorAll('link').entries()) {
								el.remove();
							}
							for (const [pos, el] of pagina.querySelectorAll('hr').entries()) {
								el.remove();
							}
							
							if (pagina.querySelector('table')) { pagina.querySelector('table').style = 'filter: revert; background-color: white; margin-top: 3rem !important; margin-bottom: 3rem !important; width: 100%; color: rgb(33, 37, 41); font-size: 1rem; font-weight: 400; line-height: 1.5;border-color: rgb(33, 37, 41) !important;margin-bottom: 1rem !important;position: relative;display: flex;flex-direction: column;min-width: 0px;overflow-wrap: break-word;background-color: rgb(255, 255, 255);background-clip: border-box;border-style: solid;border-width: 1px;border-image: none 100% / 1 / 0 stretch;border-radius: 0.25rem;' }
							
							for (const [pos, el] of pagina.querySelectorAll('tr').entries()) {
								el.style="display: grid;grid-template-columns: .5fr 1fr 1fr 1fr 2fr 1fr 1fr 4fr 1fr .5fr; grid-gap: 5px;";
							}
							
							for (const [pos, el] of pagina.querySelectorAll('dt').entries()) {
								el.style="font-weight: bold;";
							}
							
							for (const [pos, el] of pagina.querySelectorAll('div[class="card border-dark mb-3"]').entries()) {
								el.style="border-color: #212529 !important;margin-bottom: 1rem !important;position: relative;display: flex;flex-direction: column;min-width: 0;word-wrap: break-word;background-color: #fff;background-clip: border-box;border: 1px solid rgba(0,0,0,.125); border-radius: .25rem;";
							}
							
							for (const [pos, el] of pagina.querySelectorAll('div[class="card-header"], thead').entries()) {
								el.style="border-radius: calc(.25rem - 1px) calc(.25rem - 1px) 0 0;padding: .5rem 1rem; margin-bottom: 0; background-color: #00000008; border-bottom: 1px solid rgba(0,0,0,.125);";
							}
							
							for (const [pos, el] of pagina.querySelectorAll('div[class="card-body"]').entries()) {
								el.style="flex: 1 1 auto;padding: 1rem;";
							}
							
							for (const [pos, el] of pagina.querySelectorAll('div[class="row"]').entries()) {
								el.style="display: grid;grid-template-columns: 1fr 1fr 1fr; grid-gap: 5px; text-align: left;";
								if (el.innerText.includes('Tribunal')) {
									el.style.borderBottom = '2px solid lightgray';
								}
							}
							
							for (const [pos, el] of pagina.querySelectorAll('div[id="printSection"] div[class="row"]').entries()) {
								el.style="";
							}
							
							for (const [pos, el] of pagina.querySelectorAll('div[class="col"]').entries()) {
								el.style.width = '100vw';
							}
							
							if (pagina.querySelector('h5')) {
								if (pagina.querySelector('h5').innerText.includes('Exclusão') || pagina.querySelector('h5').innerText.includes('Inclusão')) {
									pagina.querySelector('h5').style="background-color: steelblue;color: white;font-size: x-large;border-radius: 4px;text-align: center;padding: 20px 0 20px 0;";
									for (const [pos, el] of pagina.querySelectorAll('thead tr').entries()) {
										el.style="display: grid;grid-template-columns: .1fr 1fr 1fr 1fr 1fr 1fr 1fr; grid-gap: 5px; text-align: left;";
									}
									for (const [pos, el] of pagina.querySelectorAll('tbody tr').entries()) {
										el.style="display: grid;grid-template-columns: .1fr 1fr 1fr 1fr 1fr 1fr 1fr; grid-gap: 5px;";
									}
								}
							}
							
							break;
						default:
							break;
					}
					
					
					// pagina.innerHTML = cabecalhoImpressao + pagina.innerHTML;
					const textoCabecalho = 'Convênio ' + convenio.nome.toUpperCase() + informacoes_adicionais_titulo + ' - consulta realizada no dia ' + new Date().toLocaleDateString();
					const estiloCabecalho = ""
					const cabecalhoImpressao = criarElemento('span', estiloCabecalho, textoCabecalho)
					pagina.insertAdjacentElement('afterbegin', cabecalhoImpressao)
					
					
					// pagina.insertAdjacentElement('beforebegin', cabecalhoImpressao)
					moldura.appendChild(pagina);
					document.getElementById('maisPje_assistenteImpressao_div_body').appendChild(moldura);
					document.getElementById('maisPje_assistenteImpressao_info_paginas').innerText = qtdePaginas;
					
					listapaginasTemp.push(pagina.innerHTML);
					
					let var1 = await browser.storage.local.set({'impressoraVirtual': listapaginasTemp});
					Promise.all([var1]).then(async values => {
						resolver(true) 
					});
				}
				
				
			}
		);
	}

	async function abrirPaginaImpressao() {
		let areaDeImpressao = '';
		let cssEstilos = '';
		let cssPagina = document.querySelectorAll("link[rel='stylesheet']");
		for(i=0;i<cssPagina.length;i++){
			cssEstilos += '<link rel="stylesheet" href="'+cssPagina[i].href+'">';
		}

		areaDeImpressao += '<html><head><meta name="viewport" content="width=device-width, initial-scale=1" charset="utf-8"><title>' + convenio.nome.toUpperCase() + '</title>';
		areaDeImpressao += '<style>@media print { @page { size: A4; orphans: 0 !important; widows: 0 !important;}.quebradepagina { page-break-before: always; } body{ font-family: "Segoe UI", Roboto, "Helvetica Neue", Arial, "Noto Sans", "Liberation Sans", sans-serif, "Apple Color Emoji", "Segoe UI Emoji", "Segoe UI Symbol", "Noto Color Emoji"; margin: 10px; width: 21cm; height: 29.7cm; background-color: unset; } .maisPje-no-print { display: none !important; }</style>';
		
		if (convenio.nome == 'sniper') {
			areaDeImpressao += '</head><body style="font-size: 16px; line-height: 1.5em; color: #212121; -webkit-font-smoothing: antialiased; padding: 0; margin: 0; min-height: 100%;" onload="window.print();window.close();">';
		} else if (convenio.nome == 'renajud') {
			areaDeImpressao += '</head><body onload="window.print(); window.close();">';
			
		} else {
			areaDeImpressao += cssEstilos+'</head><body onload="window.print(); window.close();">';
		}
		
		let paginas = await esperarColecao('div[id*="maisPje_assistenteImpressao_pagina_"]');
		if (paginas.length == 0) { return }
		for (const [pos, pagina] of paginas.entries()) {
			areaDeImpressao += '<div style="text-align: right;">' + (pos+1) + ' de ' + paginas.length + '</div><br>';
			areaDeImpressao += '<div style="margin-bottom: 10px;">';
			areaDeImpressao += pagina.innerHTML;
			areaDeImpressao += '</div><hr><h2 class="quebradepagina"></h2>';
		}
		
		areaDeImpressao += '</body></html>';

		let novaJanela = URL.createObjectURL(new Blob([areaDeImpressao], { type: "text/html" }));
		await limparImpressora();
		window.open(novaJanela, convertDate(new Date()) + " - Consulta " + convenio.nome.toUpperCase() + ".html");
	}
	
	function convertDate(inputFormat) {
		let d = new Date(inputFormat)
		return [d.getFullYear(), d.getMonth(), d.getDate(), d.getHours(), d.getMinutes(), d.getSeconds()].join('')
	}

	function maisPjeTornarArrastavel(el) {
		var pos1 = 0, pos2 = 0, pos3 = 0, pos4 = 0;
		el.onmousedown = dragMouseDown;

		function dragMouseDown(e) {
			e = e || window.event;
			e.preventDefault();
			pos3 = e.clientX;
			pos4 = e.clientY;
			document.onmouseup = closeDragElement;
			document.onmousemove = elementDrag;
		}

		function elementDrag(e) {
			e = e || window.event;
			e.preventDefault();
			pos1 = pos3 - e.clientX;
			pos2 = pos4 - e.clientY;
			pos3 = e.clientX;
			pos4 = e.clientY;			
			el.style.top = ((el.offsetTop - pos2) <= 0) ? "0px" : (el.offsetTop - pos2) + "px";
			el.style.left = ((el.offsetLeft - pos1) <= 0) ? "0px" : (el.offsetLeft - pos1) + "px";
		}

		function closeDragElement() {
			document.onmouseup = null;
			document.onmousemove = null;
		}
	}
	
	async function carregarPaginasStorage() {
		return new Promise(
			async resolver => {
				//recupera as páginas salvas no storage
				let var1 = await browser.storage.local.get('impressoraVirtual', async function(result){
					resolver(result.impressoraVirtual);	
				});
			}
		);
	}
	
	async function limparImpressora() {
		return new Promise(
			async resolver => {
				browser.runtime.sendMessage({tipo: 'storage_limpar', valor: 'impressoraVirtual'});
				listapaginasTemp = [];
				let paginas = await esperarColecao('div[id*="maisPje_assistenteImpressao_moldura_"]');
				if (!paginas) { return }
				if (paginas.length == 0) { return }
				for (const [pos, pagina] of paginas.entries()) {
					pagina.remove();
				}
				document.getElementById('maisPje_assistenteImpressao_info_paginas').innerText = '0';

				if (document.location.href.includes('sniper.pdpj.jus.br')) {
					if (document.querySelector('button[title="Limpar grafo"]')) {
						await clicarBotao('button[title="Limpar grafo"]');
						await clicarBotao('div[class="ma-modal__footer"] button[data-answer="yes"]');
					}
				}

				return resolver(true);
			}
		);
	}
	
	async function getConvenio() {
		return new Promise(
			resolver => {
				if (document.location.href.includes("sistema.registrocivil.org.br/crcjud")) {
					return resolver({nome:'crcjud',alvo:'div[id="pesq_registros"]',alvo2:'form[action="javascript:pedido2aViaBusca();"]',posx:'right:1.5vw;',posy:'top:1vh;'});
				} else if (document.location.href.includes("censec.org.br/private")) {
					return resolver({nome:'censec',alvo:'app-public-query-details div[class*="box-light"]',alvo2:'app-public-query h3',posx:'right:1.5vw;',posy:'top:16vh;'});
				} else if (document.location.href.includes("sniper.pdpj.jus.br")) {
					return resolver({nome:'sniper',alvo:'div[class*="graph-info-content"]',alvo2:'app-graph table[class*="generic-table"]',posx:'right:28vw;',posy:'top:10vh;'});
				} else if (document.location.href.includes("casan-ws")) {
					return resolver({nome:'casan',alvo:'div[class="box-body"] table',alvo2:null,posx:'right:1vw;',posy:'top:40vh;'});
				} else if (document.location.href.includes("celesc.com.br/consulta")) {
					return resolver({nome:'celesc',alvo:'div[class="x_content"]',alvo2:null,posx:'right:1vw;',posy:'top:34vh;'});
				} else if (document.location.href.includes("renajud.pdpj.jus.br")) {
					return resolver({nome:'renajud',alvo:'app-veiculo-pesquisa table, app-veiculo-pesquisa div[class*="alert"]',alvo2:'div[class="modal-body"]',posx:'left:66vw;',posy:'top:0vh;'});
				} else if (document.location.href.includes(preferencias.configURLs.idSiscondj)) {
					return resolver({nome:'siscondj',alvo:'div[id="dados_pesquisados"]',alvo2:'object[id="data_pdf"]',posx:'left:66vw;',posy:'top:0vh;'});
				}
			}
		);
	}
	
	async function getExecutado(documento) {
		return new Promise(resolver => {
			if (!preferencias.processo_memoria) { return resolver({nome:'',cpfcnpj:documento}) }
			for (const [pos, executado] of preferencias.processo_memoria.reu.entries()) {
				if (documento == executado.cpfcnpj) {
					return resolver({nome:executado.nome,cpfcnpj:executado.cpfcnpj});
				}
			}
			return resolver({nome:'',cpfcnpj:documento});
		});
	}
}

async function documentoEmSigilo(valor) {
	return new Promise(async (resolve, reject) => {
		browser.storage.local.set({'anexadoDoctoEmSigilo':valor});
		preferencias.anexadoDoctoEmSigilo = await getLocalStorage('anexadoDoctoEmSigilo');
		console.log('preferencias.anexadoDoctoEmSigilo: ' + preferencias.anexadoDoctoEmSigilo)
		resolve(true);
    });
}

//FUNÇÕES ASSINCRONAS
function timer(botao, tempo_para_click, corDeFundo='rgba(80, 119, 164, .7)') {
	return new Promise(resolve => {
		let textoDoBotao;
		let check;
		if (botao.tagName == "INPUT") {
			textoDoBotao = botao.value;
			botao.value = textoDoBotao + ' ( ' + tempo_para_click + ' )';
			botao.style.animation = 'pulseLeve 1s infinite';
			botao.style.backgroundColor = corDeFundo;
			botao.addEventListener('click', function(event) { tempo_para_click = 0 });
			
			tempo_para_click--;
			check = setInterval(function() {
				botao.value = textoDoBotao + ' ( ' + tempo_para_click + ' )';
				if (tempo_para_click < 0) {
					clearInterval(check);
					botao.click();
					resolve(true)
				}
				tempo_para_click--;
			}, 1000);
		} else {
			textoDoBotao = botao.innerText;
			botao.innerText = textoDoBotao + ' ( ' + tempo_para_click + ' )';
			botao.style.animation = 'pulseLeve 1s infinite';
			botao.style.backgroundColor = corDeFundo;
			botao.addEventListener('click', function(event) { tempo_para_click = 0 }); //estar interromper a contagem com o pressionar do ESC			
			
			tempo_para_click--; //o check inicia já descontando 1 segundo
			check = setInterval(function() {
				botao.innerText = textoDoBotao + ' ( ' + tempo_para_click + ' )';
				if (tempo_para_click < 0) {
					clearInterval(check);
					botao.click();
					resolve(true)
				}
				tempo_para_click--;
			}, 1000);
		}
		
		
	
	});
}

async function escolherOpcao(seletor, valor, qtde_minima=1, possuiBarraProgresso) {
	await sleep(preferencias.maisPje_velocidade_interacao);
	//quando for passar um elemento HTML para esta função tem que ter certeza que ele já existe na tela
	if (seletor instanceof HTMLElement) {
		seletor.parentElement.parentElement.click();
	} else {
		await esperarElemento(seletor).then(elemento=>{
			elemento.parentElement.parentElement.click();
		});
	}
	// console.log("                   |---> SELECT " + seletor + " ---> Mínimo: " + qtde_minima);
	
	let colecao = await esperarColecao('mat-option[role="option"], option', qtde_minima, 500);
	let encontrou = false;
	for (const [pos, opcao] of colecao.entries()) {
		if (valor.includes('[exato]')) {
			let valorExato = valor.replace('[exato]','');
			if (removeAcento(opcao.innerText.toLowerCase()) == removeAcento(valorExato.toLowerCase())) {
				// console.log("                       |--->OPTION " + valorExato);
				opcao.click();
				encontrou = true;
			};
		} else {
			if (removeAcento(opcao.innerText.toLowerCase()).includes(removeAcento(valor.toLowerCase()))) {
				// console.log("                       |--->OPTION " + valor);
				opcao.click();
				encontrou = true;
			};
		}
	}
	
	if (encontrou) {
		if (seletor instanceof HTMLElement) { 
			seletor.blur() 
		} else { 
			document.querySelector(seletor).blur() 
		}
	} else {
		await sleep(1000);
		await escolherOpcao(seletor, valor, qtde_minima, possuiBarraProgresso);
	}
	
	if (possuiBarraProgresso) {
		return await observar_mat_progress_bar();
	} else {
		return;
	}
	
	async function observar_mat_progress_bar() {
		return new Promise(resolve => {
			let observer = new MutationObserver(function(mutationsDocumento) {
				mutationsDocumento.forEach(function(mutation) {
					if (!mutation.removedNodes[0]) { return }
					if (!mutation.removedNodes[0].tagName) { return }
					// console.log("[DEL] " + mutation.removedNodes[0].tagName);
					if (!mutation.removedNodes[0].tagName.includes("MAT-PROGRESS-BAR")) { return }
					
					// console.log("***[DEL] " + mutation.removedNodes[0].tagName);
					// console.log("              |___MAT-PROGRESS-BAR FINALIZADO");
					resolve(true);
					observer.disconnect();
				});
			});
			let configDocumento = { childList: true, subtree:true }
			observer.observe(document.body, configDocumento); //inicia o MutationObserver
		});
	}
}

async function escolherOpcaoTeste(seletor, valor, possuiBarraProgresso) {
	return new Promise(async resolve => {
		await sleep(preferencias.maisPje_velocidade_interacao);
		if (seletor instanceof HTMLElement) { //aciona o listbox
			await clicarBotao(seletor.parentElement.parentElement);
		} else {
			let el = await esperarElemento(seletor);
			await clicarBotao(el.parentElement.parentElement);
		}
		
		await clicarBotao('mat-option[role="option"], option', valor); //aciona a opção
		if (possuiBarraProgresso) {
			await observar_mat_progress_bar();
		}
		return resolve(true);
	});

	async function observar_mat_progress_bar() {
		return new Promise(resolve => {
			let observer = new MutationObserver(function(mutationsDocumento) {
				mutationsDocumento.forEach(function(mutation) {
					if (!mutation.removedNodes[0]) { return }
					if (!mutation.removedNodes[0].tagName) { return }
					if (!mutation.removedNodes[0].tagName.includes("MAT-PROGRESS-BAR")) { return }
					resolve(true);
					observer.disconnect();
				});
			});
			let configDocumento = { childList: true, subtree:true }
			observer.observe(document.body, configDocumento);
		});
	}
}

//eh um teste para verificar se a escolha do item no select funciona mesmo se a janela não estiver ativa.. isso permitirá ao usuário continuar trabalhando em outra janela
async function escolherOpcaoTeste2(seletor, valor, possuiBarraProgresso) {
	return new Promise(async resolve => {
		//NOVOS TESTES PARA QUE A FUNÇÃO FUNCIONE EM ABAS(GUIAS) DESATIVADAS
		await sleep(preferencias.maisPje_velocidade_interacao);
		if (seletor instanceof HTMLElement) {
		} else {
			seletor = await esperarElemento(seletor);
		}		
		
		seletor.focus();
		seletor.dispatchEvent(simularTecla('keydown',13));
		//Code 13 == igual a enter
		//Code 40 == seta pra baixo
		//teste1 : o carregamento muito rápido da página por vezes não permite ao menu de opções abrir para selecionar a opção desejada
		let teste = await esperarColecao('mat-option[role="option"], option', 5, 1000);			
		if (!teste) {
			seletor.focus();
			seletor.dispatchEvent(simularTecla('keydown',40));
			//teste2
			teste = await esperarColecao('mat-option[role="option"], option', 5, 1000);			
			if (!teste) {
				seletor.focus();
				seletor.dispatchEvent(simularTecla('keydown',13));
				//teste3
				teste = await esperarColecao('mat-option[role="option"], option', 5, 1000);			
				if (!teste) {
					seletor.focus();
					seletor.dispatchEvent(simularTecla('keydown',40));
					//teste4 
					teste = await esperarColecao('mat-option[role="option"], option', 5, 1000);			
					if (!teste) {
						seletor.focus();
						seletor.dispatchEvent(simularTecla('keydown',13));
						//teste5
						teste = await esperarColecao('mat-option[role="option"], option', 5, 1000);			
						if (!teste) {
							seletor.focus();
							seletor.dispatchEvent(simularTecla('keydown',40));
							//teste6
							teste = await esperarColecao('mat-option[role="option"], option', 5, 1000);			
							if (!teste) {
								seletor.focus();
								seletor.dispatchEvent(simularTecla('keydown',13));
							}
						}
					}
				}
			}
		}
		await sleep(500); //espera um tempo ,ínimo para carregar as opções
		await clicarBotao('mat-option[role="option"], option', valor); //aciona a opção
		if (possuiBarraProgresso) {
			await observar_mat_progress_bar();
		}
		return resolve(true);
	});

	async function observar_mat_progress_bar() {
		return new Promise(resolve => {
			let observer = new MutationObserver(function(mutationsDocumento) {
				mutationsDocumento.forEach(function(mutation) {
					if (!mutation.removedNodes[0]) { return }
					if (!mutation.removedNodes[0].tagName) { return }
					if (!mutation.removedNodes[0].tagName.includes("MAT-PROGRESS-BAR")) { return }
					resolve(true);
					observer.disconnect();
				});
			});
			let configDocumento = { childList: true, subtree:true }
			observer.observe(document.body, configDocumento);
		});
	}
}

async function preencherInput(seletor, valor, monitorar=false) {
	await sleep(preferencias.maisPje_velocidade_interacao);
	let elemento;
	if (seletor instanceof HTMLElement) {
		elemento = seletor;
	} else {
		elemento = await esperarElemento(seletor)
	}
	elemento.focus();
	Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set.call(elemento, valor);
	
	triggerEvent(elemento, 'input');
	triggerEvent(elemento, 'change');
	triggerEvent(elemento, 'dateChange');
	triggerEvent(elemento, 'keyup');
	
	elemento.blur();
	// console.log("                   |---> INPUT " + seletor + ">" + valor);
	if (monitorar) {
		return await ligar_mutation_observer2();
	} else {
		return true;
	}
	
	function ligar_mutation_observer2() {
		return new Promise(resolve => {
			let monitor = false;
			let observer_preencherInput = new MutationObserver(function(mutationsDocumento) {
				mutationsDocumento.forEach(function(mutation) {
					if (!mutation.removedNodes[0] && !mutation.addedNodes[0]) { return }
					
					if (mutation.addedNodes[0]) {
						if (!mutation.addedNodes[0].tagName) { return }
						// console.log("***[ADD] " + mutation.addedNodes[0].tagName);
						
						//TREE-NODE-DROP-SLOT
						if (mutation.addedNodes[0].tagName.includes("TREE-NODE-DROP-SLOT")) { // abre o primeiro nivel da árvore de modelos
							// console.log(document.querySelector('span[class="nodo-filtrado"]')); ---->isso era para quando o filtro funcionava direito
							// if (document.querySelector('span[class="nodo-filtrado"]')) {
								observer_preencherInput.disconnect();
								// console.log('        |___encontrou o modelo pesquisado...')
								console.log('        |___carregou nova arvore de modelos...')
								resolve(true);
							// }
						}
					}
					
					if (mutation.removedNodes[0]) {
						if (!mutation.removedNodes[0].tagName) { return }
						// console.log("***[DEL] " + mutation.removedNodes[0].tagName);
						// console.log("              |___MAT-PROGRESS- FINALIZADO");
						
						if (mutation.removedNodes[0].tagName.includes("MAT-PROGRESS-")) { //elementos de botões com progress (mat-progress-bar e mat-progress-spinner)
							observer_preencherInput.disconnect();
							resolve(false);
						}
						
						if (mutation.removedNodes[0].tagName.includes("PJE-DIALOGO-STATUS-PROGRESSO")) {  //movimentar processos
							if (monitor) {
								observer_preencherInput.disconnect();
								resolve(false);
							}
						}
					}
					
				});
			});
			let configDocumento = { childList: true, subtree:true }
			observer_preencherInput.observe(document.body, configDocumento); //inicia o MutationObserver
			setTimeout(function() {
				observer_preencherInput.disconnect();
				resolve(false); //sem erros
			}, 5000);  //desliga o mutation depois de 5 segundos
		});
	}
}

async function clicarBotao(seletor, texto, monitorar=false) {
	await sleep(preferencias.maisPje_velocidade_interacao);
	let elemento, cont;
	if (seletor instanceof HTMLElement) {
		elemento = seletor;
	} else {
		elemento = await esperarElemento(seletor, texto)
	}
	
	if (!elemento?.hasAttribute('disabled')) {
		// console.log("                   |---> CLIQUE " + seletor + (texto ? ">" + texto : ""));
		await elemento.click();
		if (monitorar) {
			let resultado = await ligar_mutation_observer();
			return resultado;
		} else {
			return true;
		}
	} else {
		// console.log("                        o botão está desativado... tentar novamente...");
		return clicarBotao(seletor, texto, monitorar);
	}
	
	function ligar_mutation_observer() {
		return new Promise(resolve => {
			let monitor = false;
			let observer_clicarBotao = new MutationObserver(function(mutationsDocumento) {
				mutationsDocumento.forEach(function(mutation) {
					if (!mutation.removedNodes[0] && !mutation.addedNodes[0]) { return }
					
					if (mutation.removedNodes[0]) {
						if (!mutation.removedNodes[0].tagName) { return }
						// console.log("***[DEL] " + mutation.removedNodes[0].tagName);
						// console.log("***[DEL] " + mutation.removedNodes[0].className);
						// console.log("              |___MAT-PROGRESS- FINALIZADO");
						
						if (mutation.removedNodes[0].tagName.includes("MAT-PROGRESS-")) { //elementos de botões com progress (mat-progress-bar e mat-progress-spinner)
							observer_clicarBotao.disconnect();
							resolve(false);
						}
						
						if (mutation.removedNodes[0].tagName.includes("PJE-DIALOGO-STATUS-PROGRESSO")) {  //movimentar processos
							if (monitor) {
								observer_clicarBotao.disconnect();
								resolve(false);
							}
						}
					}
					
					if (mutation.addedNodes[0]) {
						if (!mutation.addedNodes[0].tagName) { return }
						// console.log("*****************************[ADD] " + mutation.addedNodes[0].tagName);
						// console.log("*****************************[ADD] " + mutation.addedNodes[0].className);
						// console.log("-----------------Aviso: " + mutation.addedNodes[0].innerText + " (" + mutation.addedNodes[0].tagName + ")");
						
						if (mutation.addedNodes[0].tagName.includes("SIMPLE-SNACK-BAR")) { //avisos de erro
							if (mutation.addedNodes[0].innerText.includes('Informe um endereço ou marque a opção endereço desconhecido')) {
								mutation.addedNodes[0].querySelector('button').click(); //fecha o aviso de erro
								observer_clicarBotao.disconnect();
								resolve(true);
							}
							
							if (mutation.addedNodes[0].innerText.includes('com sucesso')) {
								mutation.addedNodes[0].querySelector('button').click(); //fecha o aviso de erro
								observer_clicarBotao.disconnect();
								resolve(true);
							}
							
							if (mutation.addedNodes[0].innerText.includes('Minuta salva')) {
								mutation.addedNodes[0].querySelector('button').click(); //fecha o aviso
								observer_clicarBotao.disconnect();
								resolve(true);
							}
							
							
							if (mutation.addedNodes[0].innerText.includes('Erro ao persistir o expediente.')) {
								// mutation.addedNodes[0].querySelector('button').click(); //fecha o aviso de erro
								observer_clicarBotao.disconnect();
								resolve(false);
							}
							
							if (mutation.addedNodes[0].innerText.includes('Falha ao tentar registrar o prazo do sobrestamento')) {
								mutation.addedNodes[0].querySelector('button').click(); //fecha o aviso de erro
								observer_clicarBotao.disconnect();
								resolve(false);
							}
							
							if (mutation.addedNodes[0].innerText.includes('Sobrestamento(s) registrado(s) com sucesso')) {
								mutation.addedNodes[0].querySelector('button').click(); //fecha o aviso de erro
								observer_clicarBotao.disconnect();
								resolve(true);
							}

						}
						
						if (mutation.addedNodes[0].tagName.includes("DIV")) { 
							if (mutation.addedNodes[0].innerText.includes('Ato elaborado com sucesso')) { //anexar modelos
								mutation.addedNodes[0].querySelector('button').click(); //fecha o aviso de salvamento
								observer_clicarBotao.disconnect();
								resolve(true);
							}
						}
						
						if (mutation.addedNodes[0].tagName.includes("TABLE")) { 
							if (mutation.addedNodes[0].innerText.includes('N° do Processo*')) { //Renajud escolher comarca/órgão
								observer_clicarBotao.disconnect();
								resolve(true);
							}
						}
						
						if (mutation.addedNodes[0].tagName.includes("PJE-DIALOGO-STATUS-PROGRESSO")) { //movimentar processos
							monitor = true;
						}							
					}
				});
			});
			let configDocumento = { childList: true, subtree:true }
			observer_clicarBotao.observe(document.body, configDocumento); //inicia o MutationObserver
			setTimeout(function() {
				observer_clicarBotao.disconnect();
				resolve(false); //sem erros
			}, 5000);  //desliga o mutation depois de 5 segundos
		});
	}

}

async function preencherCampoPeloTipo(campo, valor) {
	return new Promise(async resolve => {
        console.info(campo, valor)
        var tagName = campo.nodeName.toLowerCase();

        switch (tagName) {
            case 'input':
                await preencherInput(campo, valor)
                break;
            case 'mat-select':
                const ariaLabel = campo.getAttribute('aria-label');
                await escolherOpcaoTeste('mat-select[aria-label="' + ariaLabel + '"]', valor + '[exato]')
                break;
            case 'mat-radio-group':
                //TODO: isso eh uma simplificacao do metodo querySelectorByText. Falar com Fernando sobre criar um novo parametro com o campo a partir do qual se quer procurar (valor default seria document, para manter compatibilidade)
                const radioButton = Array.from(campo.querySelectorAll('mat-radio-button label'))
                    .find(el => removeAcento(el.textContent.trim().toLowerCase()).includes(removeAcento(valor.toLowerCase())));
                await clicarBotao(radioButton, valor); 
                break;
            case 'textarea':
                await preencherTextArea(campo, valor)
                break;
            default:
        }
        return resolve(true);
    });
}


function criarCabecalhoNome(nome, cpfCnpj = '', tag = 'h1', estilo = "font-size: 17px;background-color: #6c757d;color: white;margin-top: 20px;padding: 3px;") {
    let textoCabecalho = nome;
    
    if (cpfCnpj) {
        textoCabecalho += ' (CPF/CNPJ n. ' + cpfCnpj + ')';
    }
    
    const cabecalhoImpressao = criarElemento(tag, estilo, textoCabecalho);
    return cabecalhoImpressao;
}

function gerarLinksDosIds(elemento, listaIds_Novo, backgroundColor='#d236c9') {
    // Função para criar o link
    function criarLink(item) {
        const link = document.createElement('a');
        link.title = "Abrir documento";
        link.id = `extensaoPje_documento_linkId_${item}`;
        link.style.backgroundColor = backgroundColor;
        link.style.cursor = "pointer";
        link.textContent = item;
        return link;
    }

    // Função para percorrer os nós de texto e substituir IDs por links
    function processarNos(node) {
        if (node.nodeType === Node.TEXT_NODE) {
            let textContent = node.textContent;
            let parentNode = node.parentNode;

            listaIds_Novo.forEach(item => {
                let regexId = new RegExp(`\\b${item}\\b`, "g");
                if (regexId.test(textContent)) {
                    let parts = textContent.split(regexId);
                    for (let i = 0; i < parts.length - 1; i++) {
                        parentNode.insertBefore(document.createTextNode(parts[i]), node);
                        parentNode.insertBefore(criarLink(item), node);
                    }
                    parentNode.insertBefore(document.createTextNode(parts[parts.length - 1]), node);
                    parentNode.removeChild(node);
                }
            });
        } else if (node.nodeType === Node.ELEMENT_NODE) {
            Array.from(node.childNodes).forEach(child => processarNos(child));
        }
    }

    // Processa todos os nós filhos do elemento
    Array.from(elemento.childNodes).forEach(child => processarNos(child));
}
