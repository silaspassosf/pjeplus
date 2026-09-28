function renajud(){
	if(JANELA.includes('login')) return
	if(!JANELA.includes('restricoes-insercao.jsf')) return
	let chassi = obterParametroDeUrl('chassi')
	let documento = obterParametroDeUrl('documento')
	let placa = obterParametroDeUrl('placa')
	let processo = obterParametroDeUrl('processo')
	let campo = ''
	let conteudo = ''
	let formulario = selecionar('[id^="form-incluir-restricao"]')
	if(chassi){
		campo = selecionar('[id$="campo-chassi"]')
		conteudo = chassi
	}
	if(documento){
		campo = selecionar('[id$="campo-cpf-cnpj"]')
		conteudo = documento
	}
	if(placa){
		campo = selecionar('[id$="campo-placa"]')
		conteudo = placa
	}
	if(processo) preencherCampoNumeroDoProcessoSelecionarMagistrado()
	if(conteudo){
		preencher(campo,conteudo)
		clicar('[id$="botao-pesquisar"]')
		esforcosPoupados(4,7,4)
	}

	function preencherCampoNumeroDoProcessoSelecionarMagistrado(){
		let observador = new MutationObserver(() => {
			let observado = selecionar('[id$="campo-numero-processo"]')
			if(observado){
				let desabilitado = observado.disabled
				if(!desabilitado){
					observador.disconnect()
					clicar('[id$=fieldset-tipo-restricao] label')
					preencher(observado,numeros(processo))
					clicar('[id$="campo-magistrado_label"]')
					selecionarMagistrado()
				}
			}
		})
		observador.observe(formulario,{
			childList:	true,
			subtree:		true
		})
	}

	function selecionarMagistrado(){
		let selecao = selecionar('li[data-label="Selecione o magistrado"]')
		if(!selecao) return
		let lista = selecao?.parentElement
		if(!lista) return
		let observador = new MutationObserver(() => {
			let observado = lista.childNodes
			if(observado.length > 1){
				observado[1].click()
				observador.disconnect()
			}
		})
		observador.observe(formulario,{
			childList:true,
			subtree:true
		})
	}
}

function renajudInserirRestricao(consulta = {}){
	if(vazio(consulta)) return
	let campo = Object.keys(consulta)[0]
	let conteudo = consulta[campo]
	let processo = PROCESSO?.numero || ''
	let url = LINK.renajud.inserir + encodeURI('?' + campo + '=' + conteudo + '&processo=' + processo)
	abrirPagina(url,'','','','','renajud')
}