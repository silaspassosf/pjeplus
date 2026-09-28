async function googleDocs(){
	if(!JANELA.includes(LINK.google.documents)) return
	criarBotao('google-docs-consultar-processo-no-pje','pje-instancia-2 informacoes','','','Consultar Processo no PJe',googleDocsTituloConsultarProcessoNoPje)
}


async function googleDocsTituloConsultarProcessoNoPje(){
	let numero = identificarNumeroDoProcesso()
	if(numero) pjeConsultarDetalhesDoProcesso(numero)

	function identificarNumeroDoProcesso(){
		let erro = 'Não foi possível identificar número de processo no conteúdo do título deste documento.'
		let dado = selecionar('[data-tooltip="Renomear"]')
		let numero = dado?.value?.match(EXPRESSAO.processoNumero) || ''
		if(!numero) alert(erro)
		return numero[0] || ''
	}
}


async function apiGooglePlanilhaConsultar(id){
	let url = 'https://sheets.googleapis.com/v4/spreadsheets/' + id + '/values/Pessoas?key=' + apiGooglePlanilhas()
	let resposta = 	await fetch(url,{
		"credentials":"include",
		"method":"GET",
		"mode":"cors"
	})
	let json = await resposta.json()
	let linhas = []
	let valores = json.values || []
	let cabecalho = valores.shift()
	valores.forEach(linha => {
		let dados = {}
		linha.forEach((item,indice) => {
			dados[cabecalho[indice]] = item
		})
		linhas.push(dados)
	})
	return linhas || ''
}