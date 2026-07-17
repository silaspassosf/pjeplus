async function pjeOtimizarConclusaoAMagistrado(){
	let selecao = await esperar('[placeholder="Magistrado"]',true)
	criarBotaoMagistradoConfiguracoes()
	selecionarMagistradoPorFinadlDoProcesso()

	async function selecionarMagistradoPorFinadlDoProcesso(){
		await esperar('pje-concluso-tarefa-botao',true,true)
		let magistrado = CONFIGURACAO?.pjeMagistrados[PROCESSO.digitoFinal] || ''
		if(!magistrado) return
		if(selecao.textContent.includes(magistrado)){
			concluir()
			return
		}
		clicar('[placeholder="Magistrado"]')
		pjeSelecionarOpcaoPorTexto(magistrado).then(concluir)
	}

	async function concluir(){
		let contexto = pjeObterContexto()
		if(!contexto.includes('pje-tarefa')) return
		await esperar('pje-concluso-tarefa-botao',true,true)
		setTimeout(() => {
			if(CONFIGURACAO?.pjeAoAbrirTarefaDoProcesso?.tutelaLiminarParaDecisao)
				if(pjeMomentoTutelaLiminar()) clicar('Pedido de Tutela',true)
			if(CONFIGURACAO?.pjeAoAbrirTarefaDoProcesso?.admissibilidadeRecursalParaDecisao)
				if(pjeMomentoAdmissibilidadeRecursal()) clicar('Admissibilidade de Recursos',true)
			if(CONFIGURACAO?.pjeAoAbrirTarefaDoProcesso?.peticoesParaDespacho)
				if(pjeMomentoDespachar()) clicar('Despacho',true)
		},1000)
	}

	function criarBotaoMagistradoConfiguracoes(){
		let destino = selecionar('pje-concluso-tarefa-magistrado')
		let configuracoes = criarBotao(
			'conclusao-ao-magistrado-configuracoes',
			'configuracoes informacoes',
			selecao.parentElement,
			'',
			'Configuracões de Seleção Automática de Magistrad(a)os',
			abrirPaginaConfiguracoesMagistrado
		)
		destino.parentElement.insertBefore(configuracoes,destino)
	}
}