window.addEventListener('load',termosDeUso)

async function termosDeUso(){

	let armazenamento = await browser.storage.local.get()

	CONFIGURACAO = armazenamento
	EXTENSAO.ativada = CONFIGURACAO.ativada

	definicoesGlobais()
	criarCabecalhoDePaginaDaExtensao()
	definirEstadoDaExtensao()
	criarRodapeDePaginaDaExtensao()

}