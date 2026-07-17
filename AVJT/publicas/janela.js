function janela(){
	if(!CONTEXTO) return
	criarBotaoMemorizarDimensoesDaJanela()
}

async function criarBotaoMemorizarDimensoesDaJanela(){
	let botao = criarBotao('avjt-janela-salvar-dimensoes','informacoes avjt-informacoes-direita avjt-informacoes-inferior ','','','Salvar Dimensões da Janela')
	botao.addEventListener(
		'click',
		async () => {
			botao.classList.remove('informacoes')
			botao.classList.add('encolher-crescer')
			await aguardar()
			botao.classList.remove('encolher-crescer')
			botao.classList.add('informacoes')
			definirDimensoes(CONTEXTO)
		}
	)
	async function definirDimensoes(chave=''){
		if(!chave) return
		let janela = CONFIGURACAO?.janela || {}
		let altura = window.outerHeight || 900
		let largura = window.outerWidth || 1600
		let horizontal = window.screenLeft || 0
		let vertical = window.screenTop || 0
		let dimensoes = {a:altura,l:largura,h:horizontal,v:vertical}
		janela[chave] = dimensoes
		await browser.storage.local.set({janela})
	}	
}