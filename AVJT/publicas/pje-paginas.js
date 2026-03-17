function pjeAbrirAnexar(certidao=''){
	let url = LINK.pje.anexar
	if(certidao) url += '?certificar='+encodeURIComponent(JSON.stringify(certidao))
	abrirPagina(url,'','','','','pjeAnexar')
	esforcosPoupados(1,1)
}

function pjeAbrirAudienciasSessoes(){
	abrirPagina(LINK.pje.audiencias,'','','','','pjeAudiencias')
	esforcosPoupados(1,1)
}

function pjeAbrirBndt(){
	abrirPagina(LINK.pje.bndt,'','','','','pjeTarefa')
	esforcosPoupados(1,1)
}

function pjeAbrirCalculos(){
	abrirPagina(LINK.pje.calculos,'','','','','pjeTarefa')
	esforcosPoupados(1,1)
}

function pjeAbrirComunicacoes(intimar=''){
	abrirPagina(LINK.pje.comunicacoes+'?intimar='+intimar,'','','','','pjeTarefa')
	esforcosPoupados(1,1)
}

function pjeAbrirCopiarDocumentos(){
	abrirPagina(LINK.pje.copiarDocumentos,'','','','','pjeTarefa')
	esforcosPoupados(1,1)
}

function pjeAbrirGigsEmNovaPagina(){
	abrirPagina(LINK.pje.gigs,'','','','','pjeGigs')
	esforcosPoupados(1,1)
}

function pjeAbrirHistoricoDeTarefas(){
	abrirPagina(LINK.pje.historico,'','','','','pjeTarefa')
	esforcosPoupados(1,1)
}

function pjeAbrirSif(){
	abrirPagina(LINK.pje.sif,'','','','','sif')
	esforcosPoupados(1,1)
}

function pjeAbrirObrigacaoDePagar(dados=''){
	abrirPagina(LINK.pje.pagar,'','','','','pjeTarefa')
	esforcosPoupados(1,1)
}

function pjeAbrirPagamento(dados=''){
	abrirPagina(LINK.pje.pagamento,'','','','','pjeTarefa')
	esforcosPoupados(1,1)
}

function pjeAbrirRetificarAutuacao(
	nome='',
	inserir=''
){
	let url = LINK.pje.retificarAutuacao
	if(nome || inserir) url += encodeURI('?nome='+nome+'&inserir='+inserir)
	abrirPagina(url,'','','','','pjeTarefa')
	esforcosPoupados(1,1)
}

function pjeCalcRaiz(){
	let url = LINK.pje.calc + '/pages/principal.jsf'
	abrirPagina(url,'','','','','pjeCalc')
	esforcosPoupados(1,1)
}

function pjeCalcBuscarProcesso(){
	copiar('avjtBuscarCalculo'+PROCESSO.numero)
	pjeCalcRaiz()
}

function pjeCalcNovo(){
	copiar('avjtNovoCalculo'+PROCESSO.numero)
	pjeCalcRaiz()
}

function pjeAbrirPautaDeAudiencias(){
	copiar(PROCESSO.numero)
	abrirPagina(LINK.pje.pauta,'','','','','pjeTarefa')
	esforcosPoupados(1,1)
}

function pjeAbrirPericias(){
	abrirPagina(LINK.pje.pericias,'','','','','pjePericias')
	esforcosPoupados(1,1)
}

function pjeAbrirVersao1(){
	abrirPagina(LINK.pje.legado.processo,'','','','','pjeLegado')
	esforcosPoupados(1,1)
}

function pjeAbrirRecursos(){
	abrirPagina(LINK.pje.recursos,'','','','','pjeTarefa')
	esforcosPoupados(1,1)
}

function abrirPaginaConfiguracoesMenuExpandido(){
	abrirPagina(caminho('navegador/pje-menu-expandido/pagina.htm'),'','','','')
	esforcosPoupados(1,1)
}

function abrirPaginaConfiguracoesMagistrado(){
	abrirPagina(caminho('navegador/pje-magistrado/pagina.htm'),'','','','')
	esforcosPoupados(1,1)
}

function pjeAbrirMenu(){
	setTimeout(() => {
		clicar('[aria-label="Menu do processo"]')
		clicar('[aria-label="Menu da tarefa"]')
	},1)
}

function pjeProcessoDetalhesBaixarProcessoCompleto(){
	setTimeout(pjeAbrirMenu,5)
	esperar('button[aria-label="Download do processo completo"]',true).then(botao => clicar(botao))
}

function pjeProcessoDetalhesInserirLembrete(){
	setTimeout(pjeAbrirMenu,10)
	esperar('button[aria-label="Lembretes"]',true).then(botao => clicar(botao))
}

function pjeProcessoDetalhesExpedientes(){
	setTimeout(pjeAbrirMenu,15)
	esperar('button[aria-label="Expedientes"]',true).then(botao => clicar(botao))
}

function pjeProcessoDetalhesLancarMovimentos(){
	setTimeout(pjeAbrirMenu,20)
	esperar('button[aria-label="Lançar movimentos"]',true).then(botao => clicar(botao))
}

function pjeProcessoReprocessarChips(){
	setTimeout(pjeAbrirMenu,25)
	esperar('button[aria-label="Reprocessar chips do processo"]',true).then(botao => clicar(botao))
}

function pjeRemoverTodosOsChips(){
	let chips = document.querySelectorAll('button[name*="Remover Chip"]')
	for(var indice=0,espera=0;indice<=chips.length;indice++){
		setTimeout(remover,espera += 500)
	}

	function remover(){
		clicar('button[name*="Remover Chip"]')
		let botao = selecionar('ng-component button')
		if(!botao) return
		clicar(botao)
	}
}