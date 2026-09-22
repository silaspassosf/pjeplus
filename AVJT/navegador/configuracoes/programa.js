window.addEventListener('load',programa)

async function programa(){
	let armazenamento = await browser.storage.local.get()
	CONFIGURACAO = armazenamento
	definicoesGlobais()
	criarCabecalhoDePaginaDaExtensao()
	criarRodapeDePaginaDaExtensao()
	obterConfiguracoesDaExtensao()
	exportarConfiguracoesDaExtensao()
	importarConfiguracoesDaExtensao()
	selecionar('#salvar').addEventListener('click',evento => {
		evento.preventDefault()
		salvarConfiguracoesDaExtensao()
	})
	lgpd()
}

function exportarConfiguracoesDaExtensao(){
	let campoTexto = selecionar('.exportar')
	let texto = JSON.stringify(CONFIGURACAO)
	campoTexto.value = texto
	campoTexto.addEventListener('click',() => {
		campoTexto.select()
		copiar(campoTexto.value)
	})
}

async function importarConfiguracoesDaExtensao(){
	let botao = selecionar('#importar')
	botao.addEventListener('click',async () => {
		let campoTexto = selecionar('.importar')
		let texto = campoTexto.value
		if(!texto) return
		let armazenamento = JSON.parse(texto) || ''
		if(!armazenamento) return
		await browser.storage.local.set(armazenamento)
		aguardar(500)
		recarregar()
	})
}