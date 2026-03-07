async function cndt(){
	if(!JANELA.includes(LINK.cndt)) return
	let texto = await obterMemoriaTexto()
	if(!texto.includes('avjtConsultarCNDT')) return ''
	let documento = obterDocumento(texto)
	copiar(documento)
	let acao = obterParametroDeUrl('avjtConsultarCNDT')
	if(acao) clicar('[value="Emitir Certidão"]')
}