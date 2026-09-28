function whatsappMontarMensagem(numero=''){
	let resposta = prompt('Informe o número do telefone do destinatário observando o padrão internacional (Código do País Código de Área Telefone).'+"\n\n"+'Por exemplo, se o número do telefone for +55 (12) 98765-4321, utilize 5512987654321'+"\n\n",'55'+numero) || ''
	if(!resposta) return
	let telefone = numeros(resposta)
	let texto = saudacao() + "\n\n"
	whatsappEscreverMensagem(telefone,texto)
	esforcosPoupados(9,2,(3 + contarCaracteres(telefone)))
}

function whatsappEscreverMensagem(
  telefone = '',
  texto = ''
){
  let pje = pjeObterContexto()
  if(pje){
		let processo = PROCESSO?.numero || ''
		let textoPadrao = CONFIGURACAO?.texto?.emailDocumentos || ''
		let assinatura = CONFIGURACAO?.texto?.assinatura || ''
		let documentoTitulo = pjeObterDocumentoTitulo()
		let documentoLink = pjeObterDocumentoLink()
		let link = ''
		let titulo = ''
		if(documentoLink) link = 'Link:\n' + documentoLink
		if(documentoTitulo) titulo = 'Documento:\n' + documentoTitulo
		assunto = 'Processo ' + processo
		texto =	texto + 'Referente ao ' + assunto + '\n\n' + titulo + '\n\n' + link + '\n\n' + textoPadrao + '\n\n' + assinatura
		setTimeout(() => clicar('[aria-label="Baixar documento com capa (sem assinatura)"]'),1000)
	}
  let url = LINK.whatsapp.protocolo + numeros(telefone) + '&text=' + encodeURI(texto)
  window.location.href = url
	esforcosPoupados(0,0,contarCaracteres(texto))
}