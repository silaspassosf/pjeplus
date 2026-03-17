function pjeApiRequisicaoConfiguracoes(){
	let instancia = CONFIGURACAO?.instituicao?.instancia || '1'
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

/*
function pjeApiRequisicaoConfiguracoes(){
	let instancia = CONFIGURACAO?.instituicao?.instancia || '1'
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

*/

async function pjeApiConsultaPublicaObterProcessoId(numero){
	let url = LINK.pje.api.consulta + 'processos/dadosbasicos/' + numero
	let resposta = 	await fetch(url,pjeApiRequisicaoConfiguracoes())
	let dados = await resposta.json()
	return dados || ''
}

async function pjeApiConsultaPublicaObterProcessoDados(id){
	let url = LINK.pje.api.consulta + 'processos/' + id
	let resposta = 	await fetch(url,pjeApiRequisicaoConfiguracoes())
	let dados = await resposta.json()
	return dados || ''
}

async function pjeApiObterProcessoId(numero){
	//https://pje.trt15.jus.br/pje-comum-api/api/agrupamentotarefas/processos?numero=0011441-40.2022.5.15.0009
	let url = LINK.pje.api.administracao + 'consultaprocessosadm?numero=' + numero
	let resposta = 	await fetch(url,pjeApiRequisicaoConfiguracoes())
	let dados = await resposta.json()
	let processo = dados[0] || ''
	if(!processo) return ''
	return processo?.id || ''
}

async function pjeApiObterProcessoDadosPrimarios(id){
	let url = LINK.pje.api.comum + 'processos/id/' + id
	relatar('Consultando API do PJe:',url)
	let resposta = await fetch(url)
	let dados = await resposta.json()
	return dados
}

async function pjeApiObterProcessoTarefa(id){
	let url = LINK.pje.api.comum + 'processos/id/' + id + '/tarefas'
	relatar('Consultando API do PJe:',url)
	let resposta = await fetch(url)
	let dados = await resposta.json()
	relatar('Tarefa:',dados)
	return dados[0]
}

async function pjeApiObterProcessoAudiencia(id){
	let url = LINK.pje.api.comum + 'processos/id/' + id + '/audiencias?status=M'
	relatar('Consultando API do PJe:',url)
	let resposta = await fetch(url)
	let dados = await resposta.json()
	relatar('Tarefa:',dados)
	let audiencia = dados[0] || ''
	if(audiencia?.dataInicio) audiencia.data = dataLocalCurta(audiencia.dataInicio)
	return audiencia
}

async function pjeApiObterProcessoTarefaMaisRecente(id){
	let url = LINK.pje.api.comum + 'processos/id/' + id + '/tarefas?maisRecente=true'
	relatar('Consultando API do PJe:',url)
	let resposta = await fetch(url)
	let dados = await resposta.json()
	relatar('Tarefa Mais Recente:',dados)
	return dados[0]
}

async function pjeApiObterProcessoPartes(id){
	let url = LINK.pje.api.comum + 'processos/id/' + id + '/partes'
	relatar('Consultando API do PJe:',url)
	let resposta = await fetch(url)
	let dados = await resposta.json()
	relatar('Partes:',dados)
	return dados
}

async function pjeApiObterProcessoEtiquetas(id){
	let url = LINK.pje.api.etiquetas + id + '/etiquetas'
	relatar('Consultando API do PJe:',url)
	let resposta = await fetch(url)
	let dados = await resposta.json()
	relatar('Etiquetas:',dados)
	return dados
}

async function pjeApiObterProcessoPericias(id){
	let url = LINK.pje.api.comum + 'processos/id/' + id + '/pericias?situacao=ATIVAS'
	relatar('Consultando API do PJe:',url)
	let resposta = await fetch(url)
	let dados = await resposta.json()
	relatar('Partes:',dados)
	return dados
}

async function pjeApiObterProcessoMovimentos(id){
	let url = LINK.pje.api.comum + 'processos/id/' + id + '/timeline?buscarMovimentos=true&buscarDocumentos=false'
	relatar('Consultando API do PJe:',url)
	let resposta = await fetch(url)
	let dados = await resposta.json()
	relatar('Movimentos:',dados)
	return dados
}

async function pjeApiObterProcessoDocumentos(id){
	let url = LINK.pje.api.comum + 'processos/id/' + id + '/timeline?somenteDocumentosAssinados=true&buscarMovimentos=false&buscarDocumentos=true'
	relatar('Consultando API do PJe:',url)
	let resposta = await fetch(url)
	let dados = await resposta.json()
	relatar('Documentos:',dados)
	return dados
}

async function pjeApiObterProcessoDocumento(processoId,documentoId){
	let url = LINK.pje.api.comum + 'processos/id/' + processoId + '/documentos/id/' + documentoId
	relatar('Consultando API do PJe:',url)
	let resposta = await fetch(url)
	let dados = await resposta.json()
	relatar('Documento:',dados)
	return dados
}

async function pjeApiCentralDeMandadosObterMandadoDadosPrimarios(id){
	let url = LINK.pje.api.mandados + 'mandados/' + id + '/detalhamentos'
	relatar('Consultando API do PJe:',url)
	let resposta = await fetch(url)
	let dados = await resposta.json()
	return dados
}

async function pjeApiCentralDeMandadosObterProcessoId(id){
	let url = LINK.pje.api.comum + 'processos/id/' + id + '/partes'
	relatar('Consultando API do PJe:',url)
	let resposta = await fetch(url)
	let dados = await resposta.json()
	return dados
}

async function pjeApiSifObterContaDados(processo,conta){
	let url = LINK.pje.api.sif + 'contas/' + processo + '/' + conta + '/detalhes'
	relatar('Consultando API do SIF:',url)
	let resposta = await fetch(url)
	let dados = await resposta.json()
	return dados[0]
}

async function pjeApiObterProcessoUltimoAcordo(
	idProcesso ='',
	tentativas = 5
){
	let url = LINK.pje.api.comum + 'processos/id/' + idProcesso + '/acordos?ultimoAcordo=true'
	relatar('Consultando API:',url)
	try{
		let resposta = await fetch(url)
		let erro = pjeApiVerificarErro(resposta)
		if(erro) throw new Error(erro)
		let dados = await resposta.json() || ''
		dados = dados[0] || ''
		let vencimento = dados?.dataVencimento || ''
		if(vencimento){
			let data = new Date(vencimento)
			dados.vencimento = data?.toLocaleDateString() || ''
		}
		relatar('Dados:',dados)
		return dados || ''
	}
	catch(erro){
		console.error('-> erro:' + erro)
		console.error('-> tentativas:' + tentativas)
		if(tentativas < 1) return 'Erro: não foi possível verificar.'
		tentativas--
		pjeApiObterProcessoUltimoAcordo(idProcesso,tentativas)
	}
}

function pjeApiVerificarErro(resposta = {}){
	let erro = ''
	if(!resposta?.ok) erro = resposta?.statusText || 'Erro: não foi possível obter uma resposta à requisição.'
	if(minusculas(erro).includes('not found')) erro = 'Erro: URL não encontrada.'
	if(erro) console.error(erro)
	return erro
}

async function pjeApiObterUsuario(){
	let url = LINK.pje.api.seguranca + 'usuarios'
	let resposta = await fetch(url)
	let dados = await resposta.json() || ''
	console.debug('dados',dados)
	
	relatar('Dados:',dados)
	return dados
}