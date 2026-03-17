function sisbajudAbrirCadastroDeMinuta(processo=''){
	if(!processo) return
	let url = LINK.sisbajud + encodeURI('cadastrar?numeroDoProcesso='+processo)
	abrirPagina(url,'','','','','sisbajud')
	setTimeout(() => clicar('#avjt-botao-dados-do-processo'),1000)
	esforcosPoupados(1,1)
}