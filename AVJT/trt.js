function trtConsultarProcesso(numeroDoProcesso=''){
	if(!numeroDoProcesso) return
	copiar(numeroDoProcesso)
	let numero = obterDadosDoNumeroDoProcesso(numeroDoProcesso)
	let url = LINK.tribunal.portal
	if(CONFIGURACAO.instituicao.tribunal === '15') url = LINK.trt15.consultarProcesso + `pArgumento1=${numero.ordenador}&pArgumento2=${numero.digito}&pArgumento3=${numero.ano}&pArgumento4=${numero.origem}`
	abrirPagina(url,'','','','','trt')
	esforcosPoupados(1,1,contarCaracteres(numeroDoProcesso))
}