async function apiGooglePlanilhaConsultar(id){
	let url = encodeURI('https://sheets.googleapis.com/v4/spreadsheets/' + id + '/values/Juízos por Final do Processo!A4:C?key=' + apiGooglePlanilhas())
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