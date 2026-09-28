window.addEventListener('load',programa)

async function programa(){
	let armazenamento = await browser.storage.local.get()
	CONFIGURACAO = armazenamento
	EXTENSAO.ativada = CONFIGURACAO.ativada
	if(!CONFIGURACAO?.instituicao?.tribunal) abrirPaginaConfiguracaoDoTribunal()
	definicoesGlobais()
	criarCabecalhoDePaginaDaExtensao()
	definirEstadoDaExtensao()
	criarRodapeDePaginaDaExtensao()
	criarLinksUteis()
	inserirLegendaNosLinksDoYoutube()
	assistentesEspecializados()
	criarBotaoFixo('contribuir','Se o ' + EXTENSAO.short_name + ' faz diferença na sua vida, clique aqui para contribuir com o seu desenvolvimento.',abrirPaginaContribuir)
	criarBotaoFixo('recarregar','Recarregar Extensão',evento => {
		evento.target.classList.toggle('recarregar')
		setTimeout(recarregar,500)
	})
	obterConfiguracoesDaExtensao()
	window.addEventListener('input',salvarConfiguracoesDaExtensao)
	window.addEventListener('click',evento => {
		let tag = evento.target.tagName
		let id = evento.target.id
		if(id === 'ativador') return
		if(tag.includes('INPUT')) salvarConfiguracoesDaExtensao()
	})
	setInterval(contarEsforcosRepetitivosPoupados,100)

	function criarBotaoFixo(
		id = '',
		legenda = '',
		aoClicar = ''
	){
		let botao = criar('botao-fixo',id)
		botao.setAttribute('aria-label',legenda)
		botao.addEventListener('click',aoClicar)
	}

	function inserirLegendaNosLinksDoYoutube(){
		let informacoes = document.querySelectorAll('.youtube')
		informacoes.forEach(youtube => {
			youtube.setAttribute('aria-label',"Acesse vídeo(s) sobre esta seção no Canal do Youtube do " + EXTENSAO.name)
		})
	}

	function criarLinksUteis(){
		if(CONFIGURACAO.pcd) return
		let secao = selecionar('#links-uteis')
		if(!secao) return
		document.addEventListener('click',fecharMenu)
		criarBotaoDoMenu('pje-instancia-1','PJe - Painel -  1º Grau',() => criarJanela(LINK.pje.raiz,'pjePainel'))
		criarBotaoDoMenu('pje1','PJe - Versão 1.x - Painel',() => criarJanela(LINK.pje.legado.painel,'pjeLegadoPainel'),'pjeLegadoPainel')
		criarBotaoDoMenu('pje-instancia-2','PJe - Painel - 2º Grau',() => criarJanela(LINK.pje.segundograu,'pjePainel'))
		criarBotaoDoMenu('pje-painel-global','PJe - Painel Global - Todos os Processos',() => criarJanela(LINK.pje.painel.global,'pjePainel'))
		criarBotaoDoMenu('pje-painel-gigs','PJe - Painel - Relatórios GIGS',() => criarJanela(LINK.pje.painel.gigs,'pjePainel'))
		criarBotaoDoMenu('pje-consulta-processos','PJe - Painel - Consultar Processos',() => criarJanela(LINK.pje.consulta.processos,'pjePainel'))
		criarBotaoDoMenu('pje-consulta-pessoa','PJe - Painel - Consutar Pessoa',() => criarJanela(LINK.pje.consulta.pessoa,'pjePainel'))
		criarBotaoDoMenu('pje-consulta-advogado','PJe - Painel - Consutar Advogado(a)',() => criarJanela(LINK.pje.consulta.advogado,'pjePainel'))
		criarBotaoDoMenu('pje-modelos-de-documentos','PJe - Painel - Modelos de Documentos',() => criarJanela(LINK.pje.modelos,'pjePainel'))
		criarBotaoDoMenu('garimpo','Sistema Garimpo',() => criarJanela(LINK.garimpo,'garimpo'))
		criarBotaoDoMenu('intranet','Intranet',() => criarJanela(LINK.intranet,'intranet'))
		criarBotaoDoMenu('zoom','Zoom',() => criarJanela(LINK.zoom,''),false)
		criarBotaoDoMenu('meet','Meet',() => criarJanela(LINK.google.meet,''),false)
		criarBotaoDoMenu('drive','Drive',() => criarJanela(LINK.google.drive,''),false)
		criarBotaoDoMenu('agenda','Agenda',() => criarJanela(LINK.google.agenda,''),false)
		criarBotaoDoMenu('webmail','Webmail',() => criarJanela(LINK.webmail,''))
		criarBotaoDoMenu('chamado','Abertura de Chamado',() => criarJanela(LINK.chamado,'chamado'))
		criarBotaoDoMenu('balcao','Balcão Virtual',() => criarJanela(LINK.balcao,'balcao'))
		criarBotaoDoMenu('planilha','Planilha de Trabalho',() => criarJanela(LINK.planilha,'planilha'))
		criarBotaoDoMenu('eCarta','Sistema E-Carta',() => criarJanela(LINK.eCarta.raiz,'eCarta'))
		criarBotaoDoMenu('malote','Malote Digital',() => criarJanela(LINK.maloteDigital),false)
		criarBotaoDoMenu('sigeo','SIGEO',() => criarJanela(LINK.sigeo.portal,'sigeo'))
		criarBotaoDoMenu('tst','TST - Tribunal Superior do Trabalho',() => criarJanela(LINK.tst.raiz,'tst'))
		criarBotaoDoMenu('wikivt','WikiVT',() => criarJanela(LINK.wikivt),false)
		criarBotaoDoMenu('egestao','E-Gestão',() => criarJanela(LINK.egestao),false)
		criarBotaoDoMenu('sisbajud','SISBAJUD',() => criarJanela(LINK.sisbajud,'sisbajud'))
		criarBotaoDoMenu('infojud','INFOJUD',() => criarJanela(LINK.infojud.servicos,'infojud'))
		criarBotaoDoMenu('siscondj','SISCONDJ-JT',() => criarJanela(LINK.siscondj.raiz,'siscondj'))
		criarBotaoDoMenu('bb','BB - Depósitos Judiciais',() => criarJanela(LINK.bb.depositos.magistrados,'bancoDoBrasil'))
		criarBotaoDoMenu('cefRecursais','CEF - Depósitos Recursais',() => criarJanela(LINK.cef.depositos.recursais,'cefRecursais'))
		criarBotaoDoMenu('cefJudiciais','CEF - Depósitos Judiciais',() => criarJanela(LINK.cef.depositos.judiciais,'cefJudiciais'))
		criarBotaoDoMenu('renajud','RENAJUD',() => criarJanela(LINK.renajud.raiz,'renajud'))
		criarBotaoDoMenu('pjeCalc','PJe Calc',() => criarJanela(LINK.pje.calc,'pjeCalc'))
		criarBotaoDoMenu('trt','TRT - Tribunal Regional do Trabalho',() => criarJanela(LINK.tribunal.portal,'trt'))
		criarBotaoDoMenu('sinesp','SINESP',() => criarJanela(LINK.sinesp.seguranca,'sinesp'))
		criarBotaoDoMenu('penhora','Penhora Online',() => criarJanela(LINK.penhora.raiz,'penhora'))
		criarBotaoDoMenu('infoseg','INFOSEG',() => criarJanela(LINK.sinesp.infoseg,'infoseg'))

		function fecharMenu(){
			remover('menu-de-contexto')
		}

		function criarBotaoDoMenu(
			id = '',
			titulo = '',
			aoClicar = '',
			editavel = true
		){
			let botao = criar('botao',id,'link legenda',secao)
			let editar = id
			if(id){
				botao.id = id
				botao.classList.add(id)
			}
			if(titulo) botao.setAttribute('aria-label',titulo)
			if(aoClicar) botao.addEventListener('click',() => {
				aoClicar()
				esforcosPoupados(1)
			})
			if(editavel){
				if(titulo.includes('PJe - Painel')) editar = 'pjePainel'
				if(typeof editavel === 'string') editar = editavel
				botao.dataset.editar = editar
			}
			criarMenuDeContexto()

			function criarMenuDeContexto(){
				botao.addEventListener('contextmenu',elemento => criarMenu(elemento))
				function criarMenu(referencia){
					referencia.preventDefault()
					let posicao = referencia.target.getBoundingClientRect()
					let menu = criar('nav','menu-de-contexto')
					menu.style.left = (posicao.left - 45) + 'px'
					menu.style.top = (posicao.top + 55) + 'px'
					menu.addEventListener('click',evento => evento.stopPropagation())
					let botaoEditar = criar('input','menu-de-contexto-botao-editar','menu-de-contexto-botao',menu)
					botaoEditar.type = 'button'
					botaoEditar.value = 'Editar Opções'
					if(!editavel){
						botaoEditar.remove()
						let texto = criar('p','','',menu)
						texto.innerText = 'Sem opções para este botão'
						return
					}
					let editar = referencia.target.dataset.editar || ''
					let descricao = referencia.target.getAttribute('aria-label') || ''
					botaoEditar.addEventListener('click',() => abrirPaginaConfiguracaoDeLink(editar,descricao))
				}
			}
		}
	}

	function assistentesEspecializados(){
		consultaDepositos()
		recebimentoInstanciaSuperior()
		triagemInicial()

		function triagemInicial(){
			alternar('.triagemInicial',[
				'.pjeAoAbrirDetalhesDoProcesso .abrirPeticaoInicial',
				'.pjeAoAbrirDetalhesDoProcesso .abrirResumo'
			])
			ativar('.triagemInicial',[
				'.pjeAoAbrirDetalhesDoProcesso .abrirTarefa',
				'.pje .criarAreasDeRolagemDaPaginaDeDocumento',
				'.pje .expandirArvoreDocumentos'
			])
		}

		function consultaDepositos(){
			alternar('.consultaDepositos',[
				'.pjeAoAbrirDetalhesDoProcesso .siscondjConsultar',
				'.pjeAoAbrirDetalhesDoProcesso .sifConsultar',
				'.pjeAoAbrirDetalhesDoProcesso .bbConsultar',
				'.pjeAoAbrirDetalhesDoProcesso .cefDepositosJudiciaisConsultar',
				'.pjeAoAbrirDetalhesDoProcesso .cefDepositosRecursaisConsultar'
			])
		}

		function recebimentoInstanciaSuperior(){
			alternar('.recebimentoInstanciaSuperior',[
				'.assistenteDeSelecao .copiarData',
				'.assistenteDeSelecao .copiarDocumento',
				'.pjeAoAbrirDetalhesDoProcesso .abrirSentencas',
				'.pjeAoAbrirDetalhesDoProcesso .abrirAcordaos',
				'.pjeAoAbrirDetalhesDoProcesso .abrirConsultaInstancia2',
				'.pjeAoAbrirDetalhesDoProcesso .abrirConsultaTst'
			])
			ativar('.recebimentoInstanciaSuperior',[
				'.pjeAoAbrirDetalhesDoProcesso .abrirTarefa',
				'.pjeAoAbrirDetalhesDoProcesso .fecharAlertas',
				'.pje .criarAreasDeRolagemDaPaginaDeDocumento',
				'.pjeAoAbrirTarefaDoProcesso .enviarParaAnaliseRecebidoParaProsseguir',
				'.pjeAoAbrirTarefaDoProcesso .enviarParaTranstoEmJulgadoRecebidoParaProsseguir',
				'.pjeAoAbrirTarefaDoProcesso .preencherDataDoTransito',
				'.pje .expandirArvoreDocumentos'
			])
		}

		function alternar(
			classe = '',
			alternar = []
		){
			let assistente = selecionar(classe)
			if(!assistente) return
			assistente.addEventListener('click',() => {
				alternar.forEach(alternador => {
					let elemento = selecionar(alternador)
					if(elemento) elemento.checked = assistente.checked
				})
			})
		}

		function ativar(
			classe = '',
			ativar = []
		){
			let assistente = selecionar(classe)
			if(!assistente) return
			assistente.addEventListener('click',() => {
				ativar.forEach(alternador => {
					let elemento = selecionar(alternador)
					if(elemento){
						if(assistente.checked) elemento.checked = true
					}
				})
			})
		}

		function desativar(
			classe = '',
			desativar = []
		){
			let assistente = selecionar(classe)
			if(!assistente) return
			assistente.addEventListener('click',() => {
				desativar.forEach(alternador => {
					let elemento = selecionar(alternador)
					if(elemento) elemento.checked = false
				})
			})
		}
	}
}