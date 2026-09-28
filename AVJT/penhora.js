function penhora(){
	if(!JANELA.includes(LINK.penhora.dominio)) return
	consultarRespostasDeCertidao()
	consultarRespostasDePenhora()
	cadastrarMandado()
	cadastrarProcesso()
	cadastrarPartes()
	selecionarComarcas()
	marcarTermoDeAceite()

	function marcarTermoDeAceite(){
		if(!JANELA.includes('frmEscolhaCidadePenhora')) return
		let caixa = selecionar('#chkHabilitar')
		if(!caixa.checked) clicar('#chkHabilitar')
	}

	function selecionarComarcas(){
		if(!JANELA.includes('frmEscolhaCidadePenhora')) return
		let checar = selecionar('[name$="chkCidade"]')
		if(checar.checked) return
		clicar('a[href*="javascript:"]')
	}

	function consultarRespostasDeCertidao(){
		if(!JANELA.includes('consultarpedidosdecertidao')) return
		let processo = obterParametroDeUrl('processo')
		let campo = selecionar('#txtProcesso')
		preencher(campo,processo)
		if(campo && processo) focar('#filtrar')
	}

	function consultarRespostasDePenhora(){
		if(!JANELA.includes('consultarpedidosdepenhora')) return
		let processo = obterParametroDeUrl('processo')
		let campo = selecionar('#txtProcesso')
		preencher(campo,processo)
		if(campo && processo) focar('#filtrar')
	}

	function cadastrarPartes(){
		if(!JANELA.includes('Penhora/frmCadastroPartes.aspx')) return
		navigator.clipboard.readText().then(texto => {
			if(!texto) return
			PROCESSO = JSON.parse(texto)
			let poloAtivo = PROCESSO?.partes?.ATIVO || {}
			let poloPassivo = PROCESSO?.partes?.PASSIVO || {}
			cadastrarParte(poloAtivo)
			cadastrarParte(poloPassivo)

			function cadastrarParte(polo={}){
				if(vazio(polo)) return
				polo.forEach((parte,indice,partes) => {
					let documento = parte?.documento || ''
					let polo = parte?.polo?.trim() || ''
					let parteAnterior = partes[indice-1] || ''
					if(!documento || verificaParteCadastrada(documento)) return
					if(polo.includes('passivo')){
						if(!verificaParteCadastrada(poloAtivo[poloAtivo.length -1].documento)) return
					}
					if(parteAnterior){
						if(!verificaParteCadastrada(parteAnterior.documento)) return
					}
				})
			}
		})

		function verificaParteCadastrada(expressao=''){
			if(!expressao) return ''
			let partes = document.querySelectorAll('tr')
			if(vazio(partes)) return ''
			let parte = [...partes].filter(parte => parte.innerText.match(expressao))
			if(vazio(parte)) return ''
			return true
		}
	}

	function cadastrarProcesso(){
		if(!JANELA.includes('Penhora/frmCadastroProcesso.aspx')) return
		selecionarOpcao('#dplNomeAcaoPenhora','EXECUÇÃO TRABALHISTA')
		navigator.clipboard.readText().then(texto => {
			if(!texto) return
			let campo = selecionar('#msgNumeroPenhora')
			let processo = obterNumeroDoProcessoPadraoCNJ(texto)
			if(processo) preencher(campo,processo)
			focar('#btnGerarPenhora')
		})
	}

	function cadastrarMandado(){
		if(!JANELA.includes(LINK.penhora.solicitar)) return
		let mandadoId = obterParametroDeUrl('mandadoId')
		let mandadoData = obterParametroDeUrl('mandadoData')
		let campoId = selecionar('#txtFolhas')
		let campoData = selecionar('#txtDataDecisao')
		if(campoData && mandadoData) preencher(campoData,mandadoData)
		if(campoId && mandadoId) preencher(campoId,'Id ' + mandadoId)
		focar('#btnProsseguir')
	}
}

function penhoraOnlineRegistrar(consulta = {}){
	if(vazio(consulta)) return
	let valor = consulta?.valor || ''
	let mandadoId = consulta?.mandado?.id || ''
	let mandadoData = consulta?.mandado?.data || ''
	let url = LINK.penhora.solicitar + encodeURI('?' + 'valor=' + valor + '&mandadoId=' + mandadoId + '&mandadoData=' + mandadoData)
	abrirPagina(url,'','','','','penhora')
}

function penhoraOnlineConsultarRespostasDePenhora(processo=''){
	if(!processo) return
	let url = LINK.penhora.respostas + encodeURI(processo)
	abrirPagina(url,'','','','','penhora')
}

function penhoraOnlineConsultarRespostasDeCertidoes(processo=''){
	if(!processo) return
	let url = LINK.penhora.certidoes + encodeURI(processo)
	abrirPagina(url,'','','','','penhora')
}