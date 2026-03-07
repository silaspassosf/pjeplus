async function pjeOtimizarPaginaDetalhesDoProcesso(){
	let contexto = pjeObterContexto()
	if(!contexto.includes('pje-detalhes')) return
	let avjt = obterParametroDeUrl('avjt')
	if(avjt){
		if(avjt === 'AbrirPainelDoOrgaoJulgador'){
			let orgao = PROCESSO?.orgaoJulgador?.descricao || ''
			if(orgao){
				let dados = {}
				dados.avjt = 'AlterarPerfil'
				dados.orgao = orgao.trim()
				dados.processo = PROCESSO.numero
				dados.id = PROCESSO.id
				copiar(JSON.stringify(dados))
				//abrirPagina(LINK.pje.painel.avisos,'','','','','','aba')
				abrirPagina(LINK.pje.painel.avisos,'','','','','pjeDetalhes')
				await aguardar(1000)
				fechar()
			}
		}
	}
	pjeCriarBotoesFixos()
	pjeCriarPainelSuperior()
	aoAbrir()

	async function aoAbrir(){
		esperar('#botao-menu',true,true).then(exibirExpedientes)
		exibirMovimentos()
		redimensionarJanela()
		otimizarLayout()
		apreciarDocumentos()
		baixarDocumentos()
		fecharAlertas()
		abrirResumoDoProcesso()
		pesquisarTimeline()
		baixarProcessoCompleto()
		reprocessarChips()
		abrirTarefa()
		abrirDadosDoProcesso()
		abrirAnexar()
		abrirConsultaPublicaProcessoInstancia2()
		abrirConsultaTst()
		abrirAudienciasSessoes()
		abrirPericias()
		abrirVersao1()
		pjeDetalhesDoProcessoOtimizarRolagem()
		setTimeout(abrirGigsEmNovaPagina,50)
		setTimeout(pjeAoAbrirDetalhesDoProcessoConsultarDepositosJudiciais,100)
		setTimeout(excluirChips,150)
		function abrirDadosDoProcesso(){
			if(CONFIGURACAO?.pjeAoAbrirDetalhesDoProcesso?.abrirDados) pjeDestacarDadosDoProcessoEmNovaJanela()
		}
	}

	function otimizarLayout(){
		if(!CONFIGURACAO?.pjeAoAbrirDetalhesDoProcesso?.otimizarLayout) return
		estilizar(
		'',
		`
		pje-timeline .tl-data{
			margin-bottom:-3px;
		}
		pje-timeline ul mat-card{
			margin-left:-24px !important;
			position:relative;
			z-index:1;
		}
		pje-timeline mat-card > div{
			position:relative !important;
		}
		pje-timeline mat-card a[aria-label*="Abre em uma nova aba"]{
			top:-1.25em;
			display:block !important;
			position:absolute !important;
			left:30px;
			z-index:1 !important;
		}
		pje-timeline-icone i{
			font-size:14px !important;
		}
		.cdk-overlay-pane{
			max-width:unset !important;
			min-width:90% !important;
			margin-left:auto !important;
			margin-right:auto !important;
		}
		.tl-item-header{
			top:-10px !important;
			right:0 !important;
		}
		.tl-item-header .tl-item-hora{
			font-size:10px !important;
		}
		mat-card.tl-item-desc{
			padding:5px 5px 1px 5px !important;
		}
		[name="dataItemTimeline"]{
			font-size:9px !important;
			padding:1px !important;
		}
		td.pull-right{
			flex-direction:column !important;
			padding:0px !important;
			font-size:17px !important;
		}
		td.pull-right td span{
			padding:3px !important;
		}
		td.icone-tipo-atividade{
			display:flex !important;
		}
		pje-gigs-alerta-prazo span i{
			display:flex !important;
			flex-direction:column !important;
			text-align:center !important;
		}
		mat-dialog-container#mat-dialog-0,
		mat-dialog-container#mat-dialog-1,
		mat-dialog-container#mat-dialog-2,
		mat-dialog-container#mat-dialog-3
		{
			max-width:unset !important;
		}
		.mat-drawer-container[fullscreen]{
			position:relative !important;
		}
		a.tl-documento{
			line-height:1rem !important;
		}
		`,
		'avjt-pje-autuacao'
		)
	}

	function abrirAnexar(){
		if(!CONFIGURACAO?.pjeAoAbrirDetalhesDoProcesso?.abrirAnexar) return
		pjeAbrirAnexar()
	}

	function abrirAudienciasSessoes(){
		if(!CONFIGURACAO?.pjeAoAbrirDetalhesDoProcesso?.abrirAudiencias) return
		pjeAbrirAudienciasSessoes()
	}

	function abrirGigsEmNovaPagina(){
		if(!CONFIGURACAO?.pjeAoAbrirDetalhesDoProcesso?.abrirGigs) return
		pjeAbrirGigsEmNovaPagina()
	}

	function abrirConsultaTst(){
		if(!CONFIGURACAO?.pjeAoAbrirDetalhesDoProcesso?.abrirConsultaTst) return
		tstConsultarProcesso(PROCESSO.numero)
	}

	function abrirConsultaPublicaProcessoInstancia2(){
		if(!CONFIGURACAO?.pjeAoAbrirDetalhesDoProcesso?.abrirConsultaInstancia2) return
		pjeConsultaPublicaProcessoInstancia(PROCESSO.numero,2)
	}

	function abrirVersao1(){
		if(!CONFIGURACAO?.pjeAoAbrirDetalhesDoProcesso?.abrirVersao1) return
		pjeAbrirVersao1()
	}

	function abrirPericias(){
		if(!CONFIGURACAO?.pjeAoAbrirDetalhesDoProcesso?.abrirPericias) return
		pjeAbrirPericias()
	}

	function abrirTarefa(){
		if(!CONFIGURACAO?.pjeAoAbrirDetalhesDoProcesso?.abrirTarefa) return
		let contexto = pjeObterContexto()
		if(contexto.includes('pje-calculo')) return
		abrirPagina(LINK.pje.tarefa,'','','','','pjeTarefa')
		esforcosPoupados(1,1)
	}

	function pesquisarTimeline(){
		esperar('[name="Pesquisar movimentos e documentos da lista"]',true).then(campo => {
			let configuracao = CONFIGURACAO?.pjeAoAbrirDetalhesDoProcesso?.pesquisarTimeline || ''
			if(!configuracao) return
			focar('[name="Pesquisar movimentos e documentos da lista"]')
			preencher(campo,configuracao)
		})
	}

	async function abrirResumoDoProcesso(){
		if(!CONFIGURACAO?.pjeAoAbrirDetalhesDoProcesso?.abrirResumo) return
		pjeProcessoDetalhesAbrirResumoDoProcesso()
	}

	async function apreciarDocumentos(){
		if(!CONFIGURACAO?.pjeAoAbrirDetalhesDoProcesso?.apreciarDocumentos) return
		pjeProcessoDetalhesApreciarDocumentos()
	}

	async function baixarDocumentos(){
		if(!CONFIGURACAO?.pjeAoAbrirDetalhesDoProcesso?.baixarDocumentos) return
		pjeProcessoDetalhesBaixarDocumentos()
	}

	async function exibirMovimentos(){
		if(!CONFIGURACAO?.pjeAoAbrirDetalhesDoProcesso?.exibirMovimentos) return
		pjeProcessoDetalhesExibirMovimentos()
	}

	async function exibirExpedientes(){
		if(!CONFIGURACAO?.pjeAoAbrirDetalhesDoProcesso?.exibirExpedientes) return
		pjeProcessoDetalhesExpedientes()
	}

	function reprocessarChips(){
		if(!CONFIGURACAO?.pjeAoAbrirDetalhesDoProcesso?.reprocessarChips) return
		pjeProcessoReprocessarChips()
	}

	function baixarProcessoCompleto(){
		if(!CONFIGURACAO?.pjeAoAbrirDetalhesDoProcesso?.baixarProcesso) return
		esperar('[aria-label="Menu do processo"]',true).then(() => setTimeout(pjeProcessoDetalhesBaixarProcessoCompleto,1000))
	}

	function fecharAlertas(){
		esperar('pje-alerta-processo-dialogo button',true,true).then(elemento => {
			let configuracao = CONFIGURACAO?.pjeAoAbrirDetalhesDoProcesso?.fecharAlertas || ''
			if(!configuracao) return
			clicar(elemento)
			abrirResumoDoProcesso()
		})
	}

	async function excluirChips(){
		let configuracao = CONFIGURACAO?.pjeAoAbrirDetalhesDoProcesso?.removerChips || ''
		if(!configuracao) return
		esperar('mat-chip',true).then(excluir)

		async function excluir(){
			let chips = configuracao.split(';')
			for(var	indice=0,espera=0;indice <= chips.length;indice++){
				let chip = chips[indice] || ''
				if(!chip) return
				setTimeout(() => pjeRemoverChip(chip),espera += 500)
			}
		}
	}

	function redimensionarJanela(){
		if(!CONFIGURACAO?.pjeAoAbrirDetalhesDoProcesso?.redimensionar) return
		let janela = CONFIGURACAO?.janela?.pjeDetalhes || ''
		let largura =	janela?.l || 1200
		let altura = janela?.a || 900
		let horizontal = janela?.h || 0
		let vertical = janela?.v || 0
		destacarJanela(CONFIGURACAO.pjeAoAbrirDetalhesDoProcesso.redimensionar,'separarAbaDetalhesDoProcesso',largura,altura,horizontal,vertical)
	}
}

async function pjeProcessoDetalhesAbrirResumoDoProcesso(){
	let resumo = selecionar('pje-autuacao-dialogo')
	if(resumo) return
	let botao = await esperar('[aria-label="Abre o resumo do processo."]',true,true)
	clicar(botao)
}

async function pjeProcessoDetalhesApreciarDocumentos(){
	await esperar('a.tl-documento',true,true)
	clicar('[aria-label="Apreciar todos."]')
	return
}

async function pjeProcessoDetalhesBaixarDocumentos(){
	await esperar('a.tl-documento',true,true)
	clicar('[aria-label="Buscar documentos da instância de origem."]')
	return
}

async function pjeProcessoDetalhesExibirMovimentos(){
	await esperar('a.tl-documento',true,true)
	clicar('[aria-label="Exibir movimentos."]')
	return
}