window.addEventListener('load',programa)

async function programa(){
	let armazenamento = await browser.storage.local.get()
	CONFIGURACAO = armazenamento
	let configuracoes = document.querySelectorAll('.configuracao')
	definicoesGlobais()
	criarCabecalhoDePaginaDaExtensao()
	criarRodapeDePaginaDaExtensao()
	obterConfiguracoes()
	selecionar('#salvar').addEventListener('click',evento => {
		evento.preventDefault()
		salvarConfiguracoes()
	})

	function obterConfiguracoes(){
		configuracoes.forEach((configuracao,indice) => {
			let chave = CONFIGURACAO.pjeMagistrados[indice]
			configuracao.value = chave || ''
			configuracao.addEventListener('click',selecionarConteudo)
		})

	}

	async function salvarConfiguracoes(){
		let pjeMagistrados = []
		configuracoes.forEach(configuracao => {
			let magistrado = configuracao.value || ''
			let nome = magistrado.trim()
			pjeMagistrados.push(nome)
		})
		await browser.storage.local.set({pjeMagistrados})
		recarregar()
	}
}