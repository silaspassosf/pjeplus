window.addEventListener('load',programa)

async function programa(){
	let objeto = obterParametroDeUrl('objeto')
	let armazenamento = await browser.storage.local.get()
	CONFIGURACAO = armazenamento
	document.title = 'eCarta - ' + objeto
	definicoesGlobais()
	await obterCorpo(objeto)
	objetoCapturarTela()
}

async function obterCorpo(objeto=''){
	let resposta = await fetch(LINK.eCarta.detalhesObjeto + objeto)
	let texto = await resposta.text()
	let html = new DOMParser()
	let documento = html.parseFromString(texto, "text/html")
	for(let [indice, script] of documento.querySelectorAll('script').entries()){
		script.remove()
	}
	document.body = documento.body
	let processo = obterNumeroDoProcessoPadraoCNJ(document?.body?.textContent)
	let dados = await pjeApiConsultaPublicaObterProcessoId(processo)
	PROCESSO = dados[0]
	PROCESSO.destinatario = obterDestinatario()
	PROCESSO.objeto = objeto
}

function objetoCapturarTela(){
	capturarImagemDeElemento()
	setTimeout(otimizarPagina,100)
}

function obterDestinatario(){
	let texto = document?.body?.textContent.match(/Destinatário.*/i) || ''
	let destinatario = texto[0].replace(/Destinat.rio../,'')
	return limparEspacamentos(destinatario)
}

function otimizarPagina(){
	document.body.classList.add('aparecer')
	criarBotoesCertificar()
}

function criarBotoesCertificar(){
	estilizarBotaoCertificarNoPje()
	criarBotaoCertificar('entregue','azul')
	criarBotaoCertificar('devolvido','vermelho')

	function criarBotaoCertificar(
		texto = '',
		classe = ''
	){
		criarBotao(
			'avjt-certificar-'+texto,
			'avjt-'+classe,
			'',
			'CERTIFICAR "OBJETO "' + maiusculas(texto) + '" NO PJE',
			'Abre a Tarefa Anexar Documento',
			() => {
				let tipo = 'Certidão'
				let descricao = 'E-Carta - Objeto ' + titularizar(texto) + ' - ' + PROCESSO.destinatario
				let corpo = 'Certifico que, em consulta ao sistema E-Carta, o objeto ' + PROCESSO.objeto + ' retornou o seguinte relatório:'
				let certidao = pjeCertificar(descricao,tipo,corpo,'','','',true)
				LINK.pje.anexar = LINK.pje.processo + PROCESSO.id + '/documento/anexar?certificar='+encodeURIComponent(JSON.stringify(certidao))
				pjeAbrirAnexar()
			}
		)
	}
}