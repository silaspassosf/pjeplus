window.addEventListener('load',configuracoes)

async function configuracoes(){

	let armazenamento = await browser.storage.local.get()

	CONFIGURACAO = armazenamento
	console.debug('CONFIGURACAO:',CONFIGURACAO)

	let instalacao = obterUrlParametro('instalacao')

	definicoesGlobais()
	criarCabecalhoDePaginaDaExtensao()
	criarRodapeDePaginaDaExtensao()
	obterConfiguracoesDaExtensao()
	exportarConfiguracoesDaExtensao()
	importarConfiguracoesDaExtensao()
	aoInstalar()
	
	selecionar('#salvar').addEventListener(
		'click',
		evento => {
			evento.preventDefault()
			salvarConfiguracoesDaExtensao()
			if(instalacao)
				setTimeout(
					() => {
						abrirPaginaTermosDeUso()
						fechar()
					},
					500
				)
		}
	)

	function aoInstalar(){
		if(!instalacao) return
		let dados = selecionar('#exportacao-importacao')
		if(dados) dados.style.display = 'none'	
	}
}


function exportarConfiguracoesDaExtensao(){
	let campoTexto = selecionar('.exportar')
	let texto = JSON.stringify(CONFIGURACAO)
	campoTexto.value = texto
	campoTexto.addEventListener(
		'click',
		() => {
			campoTexto.select()
			copiar(campoTexto.value)
		}
	)
}

async function importarConfiguracoesDaExtensao(){
	let botao = selecionar('#importar')
	botao.addEventListener(
		'click',
		async () => {
			let campoTexto = selecionar('.importar')
			let texto = campoTexto.value
			if(!texto) return
			let armazenamento = JSON.parse(texto) || ''
			if(!armazenamento) return
			await browser.storage.local.set(armazenamento)
			setTimeout(recarregar,250)
		}
	)
}