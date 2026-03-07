window.addEventListener('load',programa)

async function programa(){
	let armazenamento = await browser.storage.local.get()
	CONFIGURACAO = armazenamento
	definicoesGlobais()
	criarCabecalhoDePaginaDaExtensao()
	criarRodapeDePaginaDaExtensao()
	obterConfiguracoes()
	selecionar('#salvar').addEventListener('click',evento => {
		evento.preventDefault()
		salvarConfiguracoes()
	})

	function obterConfiguracoes(){
		let configuracoes = document.querySelectorAll('.configuracao')
		let configuracao = CONFIGURACAO?.pjeMenu || ''
		if(!configuracao) return
		configuracoes.forEach(elemento => {
			if(configuracao[elemento.id]) elemento.checked = configuracao[elemento.id]
		})
	}

	async function salvarConfiguracoes(){
		let configuracoes = document.querySelectorAll('.configuracao')
		let pjeMenu = {}
		configuracoes.forEach(elemento => pjeMenu[elemento.id] = elemento.checked)
		await browser.storage.local.set({pjeMenu})
		recarregar()
	}
}