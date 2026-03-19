browser.storage.local.get(null,armazenamento => {
	CONFIGURACAO = armazenamento
	EXTENSAO.ativada = CONFIGURACAO.ativada
	definicoes()
	criarMenuDeContexto()

	function definicoes(){
		definicoesGlobais()
		if(!CONFIGURACAO?.instituicao?.tribunal) abrirPaginaConfiguracaoDoTribunal()
		definirIconeDaExtensaoPeloEstado(EXTENSAO.ativada)
	}
})


browser.runtime.onMessage.addListener(acao => {
	if(acao?.url){
		if(acao?.tipo === 'aba')
			criarAba(
				acao.url
			)
		else
			criarJanela(
				acao.url,
				acao.chave,
				acao.largura,
				acao.altura,
				acao.horizontal,
				acao.vertical,
				acao.tipo
			)
		return
	}
	if(acao?.capturar){
		navegadorCapturarImagem(acao)
	}
	browser.windows.getCurrent().then(janela => {
		browser.tabs.query({}).then(abas => {
			abas.forEach(aba => {
				if(aba.url.includes('janela=destacada')) return
				if((aba.url.includes('detalhe') && acao.mensagem == 'separarAbaDetalhesDoProcesso')) browser.windows.create({tabId:aba.id,width:Number(acao.largura),height:Number(acao.altura),left:Number(acao.horizontal),top:Number(acao.vertical)})
			})
		},null)
	},null)
})

function criarMenuDeContexto(){
	browser.contextMenus.create({
		'id': 'CapturarImagem',
		'title': 'Capturar Imagem da Página',
		'contexts': ['all'],
		'icons': {
			'16': './imagens/icones/dimensoes.svg',
			'32': './imagens/icones/dimensoes.svg'
		}
	})
}

browser.contextMenus.onClicked.addListener(contexto => {
	switch(contexto.menuItemId){
		case "CapturarImagem":
			navegadorCapturarImagem()
			break
	}
})