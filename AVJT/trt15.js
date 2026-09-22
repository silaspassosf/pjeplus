async function trt15(){
	if(!CONFIGURACAO.instituicao.tribunal === '15') return
	trt15Jurisprudencia()
}

async function trt15ApiConsultaPlanilhaPessoas(){
	if(!CONFIGURACAO.instituicao.tribunal === '15') return ''
	return apiGooglePlanilhaConsultar('15a_QPX_iCItndRnerU_tlDGzeQfPezRMBeYzoYQS2E0')
}

async function trt15ApiConsultaPlanilhaPessoas0009(){
	if(!CONFIGURACAO.instituicao.tribunal === '15') return ''
	if(!CONFIGURACAO.instituicao.unidade === '1ª Vara do Trabalho de Taubaté') return ''
	return apiGooglePlanilhaConsultar('1Nn-g9B3gRvahSVh3p9thBC_TXxmjS5U3ofcS6cXm9lI')
}

async function trt15Jurisprudencia(){
	if(!JANELA.includes(LINK.trt15.consultarJurisprudencia)) return ''
	let campo = await esperar('[formcontrolname="buscarPalavrasTodas"]',true,true)
	let texto = obterParametroDeUrl('avjtConsulta')
	preencher(campo,texto)
}

function trt15ConsultarJurisprudencia(texto){
	let url = LINK.trt15.consultarJurisprudencia + encodeURI(texto)
	abrirPagina(url,'','','','','trt')
	esforcosPoupados(1,1,contarCaracteres(texto))
}