function pjeApiRequisicaoConfiguracoes(){
	let instancia = CONFIGURACAO?.usuario?.instancia || '1'
	return {
		"method": "GET",
		"mode": "cors",
		"credentials": "include",
		"headers": {
			"Content-Type": "application/json",
			"X-Grau-Instancia": instancia
		}
	}
}


async function pjeApiObterProcessoDadosPrimarios(id){
	let url = LINK.pje.api.comum + 'processos/id/' + id
	relatar('Consultando API:',url)
	let resposta = await fetch(url,pjeApiRequisicaoConfiguracoes)
	let dados = await resposta.json()
	relatar('Dados:',dados)
	return dados
}

async function pjeApiObterProcessoRedistribuicoes(id){
	let url = LINK.pje.api.comum + 'processos/redistribuicao?idProcesso=' + id
	relatar('Consultando API:',url)
	let resposta = await fetch(url,pjeApiRequisicaoConfiguracoes)
	let dados = await resposta.json()
	console.debug('dados',dados)
	if(vazio(dados)) return ''
	relatar('Dados:',dados)
	if(Array.isArray(dados)){
		dados = dados?.sort((a, b) => {
			return (a.dataHoraRedistribuicao - b.dataHoraRedistribuicao)
		})
	}
	return dados
}

async function pjeApiObterOrgaosJulgadores(id=''){
	let url = LINK.pje.api.comum + 'orgaosjulgadores/' + id
	relatar('Consultando API:',url)
	let resposta = await fetch(url,pjeApiRequisicaoConfiguracoes)
	let dados = await resposta.json()
	relatar('Dados:',dados)
	return dados
}


function pjeApiVerificarErro(resposta = {}){
	let erro = ''
	if(!resposta?.ok) erro = resposta?.statusText || 'Erro: não foi possível obter uma resposta à requisição.'
	if(minusculas(erro).includes('not found')) erro = 'Erro: URL não encontrada.'
	if(erro) console.error(erro)
	return erro
}