function planilha(){
	if(!JANELA.includes(LINK.google.planilhas)) return
	document.onkeyup = soltando => {
		if(soltando.key.includes('F8')) planilhaConsultarDetalhesDoProcesso()
	}
	criarBotao(
		'planilha-consultar-processo',
		'informacoes',
		'',
		'Consultar PJe [F8]',
		'Selecione uma célula da planilha contendo um número de processo no padrão CNJ e clique neste botão para consultar o processo. Se preferir, utilize a tecla de atalho [F8].',
		planilhaConsultarDetalhesDoProcesso
	)
}

function identificarNumeroDoProcessoDaPlanilhaGoogle(){
	let erro = 'Não foi possível identificar número de processo no conteúdo da célula.\n\nCertifique-se de que haja um número de processo, no padrão CNJ, selecionado para usar um botão de consulta.'
	let dado = selecionar('#t-formula-bar-input div')
	let numero = dado?.innerText?.trim()?.match(EXPRESSAO.processoNumero) || ''
	if(!numero){
		alert(erro)
		return ''
	}
	return numero?.join() || ''
}

function planilhaConsultarDetalhesDoProcesso(){
	let numero = identificarNumeroDoProcessoDaPlanilhaGoogle()
	if(numero) pjeConsultarDetalhesDoProcesso(numero)
}