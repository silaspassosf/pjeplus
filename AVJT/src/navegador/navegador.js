browser.storage.local.get(
	null,
	armazenamento => {

		//publicas/definicoes.js

		CONFIGURACAO = armazenamento
		EXTENSAO.ativada = CONFIGURACAO.ativada

		if(CONFIGURACAO?.extensaoAtiva){
			browser.storage.local.clear().then(definicoes)
		}

		definicoes()

		function definicoes(){

			definicoesGlobais()

			if(!CONFIGURACAO?.usuario?.instancia) abrirPaginaConfiguracaoDoUsuario()

			definirIconeDaExtensaoPeloEstado(EXTENSAO.ativada)

		}

	}

)


browser.runtime.onMessage.addListener(
	acao => {

		if(acao?.url){
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

		browser.windows.getCurrent().then(
			janela => {
				browser.tabs.query({}).then(
					abas => {
						abas.forEach(
							aba => {

								if(aba.url.includes('janela=destacada'))
									return

								if(
										(aba.url.includes('detalhe') && acao.mensagem == 'separarAbaDetalhesDoProcesso')
									)
									browser.windows.create({
										tabId:aba.id,
										width:Number(acao.largura),
										height:Number(acao.altura),
										left:Number(acao.horizontal),
										top:Number(acao.vertical)
									})

							}
						)
					},
					null
				)
			},
			null
		)

	}

)