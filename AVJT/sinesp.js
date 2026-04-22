function sinesp(){
	if(!JANELA.includes(LINK.sinesp.dominio)) return
	autenticacao()

	function autenticacao(){
		if(!JANELA.includes('sinesp-seguranca/login.jsf')) return
		let cpf = CONFIGURACAO?.usuario?.cpf || ''
		let campoUsuario = selecionar('[id$="identificacao"]')
		if(!campoUsuario || !cpf) return
		preencher(campoUsuario,cpf)
	}
}

function infosegPesquisarDocumento(documento=''){
	if(!documento) return
	let url = LINK.sinesp.infoseg + encodeURI(documento)
	abrirPagina(url,'','','','','infoseg')
	esforcosPoupados(1,1,contarCaracteres(documento))
}