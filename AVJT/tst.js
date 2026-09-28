function tst(){
	otimizarConsultaProcessual()
	consultarJurisprudencia()

	function otimizarConsultaProcessual(){
		let andamentos = document.querySelectorAll('td.historicoProcesso')
		let transitado = [...andamentos].filter(linha => linha.textContent.includes('Transitado em Julgado em'))[0] || ''
		if(!transitado) return
		transitado.style.fontSize = '20px'
		let texto = transitado.textContent || ''
		let data = obterData(texto)
		if(!data) return
		copiar(data)
	}

	function consultarJurisprudencia(){
		if(!JANELA.includes(LINK.tst.dominio)) return
		let consulta = obterParametroDeUrl('avjtConsulta')
		if(!consulta) return
		esperar('#standard-with-placeholder',true).then(campo => {
			preencher(campo,consulta)
			let botaoPesquisar = [...document.querySelectorAll('button')].filter(botao => botao.textContent.includes('Pesquisar')) || ''
			if(!botaoPesquisar || botaoPesquisar.length < 1) return
			botaoPesquisar[0].click()
		})
	}
}

function tstConsultarProcesso(processo){
	let numero = obterDadosDoNumeroDoProcesso(processo)
	let url = LINK.tst.consultarProcesso + `&numeroTst=${numero.ordenador}&digitoTst=${numero.digito}&anoTst=${numero.ano}&orgaoTst=${numero.jurisdicao}&tribunalTst=${numero.tribunal}&varaTst=${numero.origem}&submit=Consultar`
	abrirPagina(url,'','','','','tst')
	esforcosPoupados(1,1,contarCaracteres(processo))
}

function tstConsultarJurisprudencia(texto){
	let url = LINK.tst.consultarJurisprudencia + encodeURI(texto)
	abrirPagina(url,'','','','','tst')
	esforcosPoupados(1,1,contarCaracteres(texto))
}