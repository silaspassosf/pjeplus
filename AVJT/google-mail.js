async function googleMail(){
	if(!JANELA.includes(LINK.google.mail)) return
	googleMailExibirMensagemAposEnvio()
	googleMailCriarBotaoCertificar()
}

async function googleMailExibirMensagemAposEnvio(){
	let botao = await esperar('#link_vsm',true,true)
	clicar(botao)
}

async function googleMailCriarBotaoCertificar(){
	if(!JANELA.includes('search=sent')) return
	let seletor = '[data-message-id] div+div'
	let mensagem = await esperar(seletor,true,true)
	googleMailOtimizarPagina()
	capturarImagemDeElemento(seletor)
	let texto = mensagem.textContent || ''
	let processo = obterNumeroDoProcessoPadraoCNJ(texto)
	let dados = await pjeApiConsultaPublicaObterProcessoId(processo)
	PROCESSO = dados[0]
	let destinatario = ''
	if(texto.includes('@bb.com.br')) destinatario = 'Ofício Ao Banco do Brasil'
	if(texto.includes('@caixa.gov.br')) destinatario = 'Ofício À Caixa Econômica Federal'
	estilizarBotaoCertificarNoPje()
	criarBotao(
		'avjt-certificar-email',
		'avjt-azul',
		'',
		'CERTIFICAR "E-MAIL ENVIADO" NO PJE',
		'Abre a Tarefa Anexar Documento',
		() => {
			let tipo = 'Correspondência ou Mensagem Eletrônica/E-mail'
			let descricao = 'Envio Realizado'
			let corpo = 'Certifico o envio de e-mail conforme imagem a seguir:'
			if(destinatario) descricao = destinatario
			let certidao = pjeCertificar(descricao,tipo,corpo,'','','',true)
			botaoCertificarOcultarAoClicar()
			capturarImagemDeElemento(seletor)
			LINK.pje.anexar = LINK.pje.processo + PROCESSO.id + '/documento/anexar?certificar='+encodeURIComponent(JSON.stringify(certidao))
			pjeAbrirAnexar()
		}
	)
}

async function googleMailOtimizarPagina(){
	let emails = selecionar('[email]',document,true)
	emails.forEach(
		elemento => {
			let email = elemento.getAttribute('email')
			elemento.innerText = email
		}
	)
}