async function pjeAnexarDocumentoPreencherCertidao(){

	let certificar = obterParametroDeUrl('certificar')

	let tipo = await esperar('[aria-label="Tipo de Documento"]',true)
	clicar(tipo)

	if(!certificar){
		if(!CONFIGURACAO?.pjeAssistentesDocumentosNotificacoes?.selecionarCertidao) return
		await pjeSelecionarOpcao('Certidão')
		return
	}

	window.onfocus = () => {
		clicar('[aria-label="Tipo de Documento"]')
	}

	let certidao = JSON.parse(decodeURIComponent(certificar))

	let colarImagem = ''

	if(certidao?.colarImagem){
		esperar('mat-dialog-container',false,false,false,false).then(async elemento => {
			if(!elemento.textContent.includes('Se documentos com imagens forem publicados, as imagens não aparecerão')) return
			let botao = elemento.querySelector('button') || ''
			if(botao) clicar(botao)
		})
		certidao.texto += "\r\n\r\n"
    try {
			let itens = await navigator.clipboard.read()
			for (let item of itens) {
				for (let tipo of item.types) {
					if (tipo.startsWith('image/')) {
						let blob = await item.getType(tipo)
						colarImagem = await blobParaArrayBuffer(blob) || ''
						console.log('Imagem salva do clipboard')
					}
				}
			}
			if(!colarImagem)
				console.log('Nenhuma imagem encontrada no clipboard')  
    }
		catch (erro) {
      console.log('Não foi possível acessar o clipboard:', erro)
    }
	}

	await pjeSelecionarOpcao(certidao.tipo)

	let descricao = await esperar('[aria-label="Descrição"]',true)

	if(certidao.descricao) preencher(descricao,certidao.descricao)
		if(certidao?.texto){
		await pjeEditorFocarAoCarregar()
		console.log('certidao.texto',certidao.texto)
		copiar(certidao.texto)
		await aguardar(500)
		colar()
		await aguardar(500)
		
		if(certidao?.colarImagem){
			if(colarImagem){
				try{
					let blob = arrayBufferParaBlob(colarImagem, 'image/png')
					await navigator.clipboard.write([
						new ClipboardItem({
							'image/png': blob
						})
					])
					console.log('Imagem restaurada para o clipboard')
					await aguardar(500)
					colar()  
					await aguardar(500)
					clicar('[data-cke-tooltip-text="Centralizar"]')
					
				}
				catch(erro){
					console.error('Erro ao restaurar imagem:', erro)
				}
			}
		}
	}

	if(certidao.sigiloso) clicar('input[name="sigiloso"]')
		if(certidao.pdf){
		let pdf = await esperar('mat-slide-toggle .mat-slide-toggle-label',true)
		clicar(pdf)
		let anexar = await esperar('#upload-anexo-0',true)
		clicar(anexar)
		return
	}

	if(certidao.assinar) clicar('[aria-label="Assinar documento e juntar ao processo"]')

}

function pjeCertificar(
	descricao = '',
	tipo = 'Certidão',
	texto = '',
	pdf = false,
	sigiloso = false,
	assinar = false,
	colarImagem = false
){
	let certidao = {}
	certidao.tipo = tipo
	certidao.descricao = descricao
	certidao.texto = texto
	certidao.pdf = pdf
	certidao.sigiloso = sigiloso
	certidao.assinar = assinar
	certidao.colarImagem = colarImagem
	return certidao
}

function pjeCertificarEmailEnviado(){
	let tipo = 'Correspondência ou Mensagem Eletrônica/E-mail'
	let descricao = 'Enviado ao Destinatário'
	let certidao = pjeCertificar(descricao,tipo)
	pjeAbrirAnexar(certidao)
}

function pjeCertificarCitacaoPorEmail(){
	let tipo = 'Correspondência ou Mensagem Eletrônica/E-mail'
	let descricao = 'Citação Para Apresentar Contestação'
	let certidao = pjeCertificar(descricao,tipo)
	pjeAbrirAnexar(certidao)
}

function pjeCertificarNotificacaoDeAudienciaPorEmail(){
	let tipo = 'Correspondência ou Mensagem Eletrônica/E-mail'
	let descricao = 'Audiência Designada'
	let certidao = pjeCertificar(descricao,tipo)
	pjeAbrirAnexar(certidao)
}

function pjeCertificarNotificacaoInicialPorEmail(){
	let tipo = 'Correspondência ou Mensagem Eletrônica/E-mail'
	let descricao = 'Notificação Inicial'
	let certidao = pjeCertificar(descricao,tipo)
	pjeAbrirAnexar(certidao)
}

function pjeCertificarNotificacaoSentencaPorEmail(){
	let tipo = 'Correspondência ou Mensagem Eletrônica/E-mail'
	let descricao = 'Sentença'
	let certidao = pjeCertificar(descricao,tipo)
	pjeAbrirAnexar(certidao)
}