window.addEventListener('load',programa)

async function programa(){
	let armazenamento = await browser.storage.local.get()
	CONFIGURACAO = armazenamento
	EXTENSAO.ativada = CONFIGURACAO.ativada
	definicoesGlobais()
	criarCabecalhoDePaginaDaExtensao()
	criarRodapeDePaginaDaExtensao()
	selecionar('#salvar').addEventListener('click',() => {
		salvarConfiguracoesDaExtensao()
		setTimeout(() => {
			abrirPaginaTermosDeUso()
			fechar()
		},500	)
	})
}