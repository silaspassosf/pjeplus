function bb(){
	if(!JANELA.includes(LINK.bb.dominio)) return
	bbConsultar()
}


function bbConsultar(){
	if(!JANELA.includes('magistrado')) return
	navigator.clipboard.readText().then(
		texto => {
			if(!texto) return
			consultarProcesso(texto)
			consultarDocumento(texto)
			consultarNome(texto)
			consultarContaJudicial(texto)
		}
	)

	function consultarProcesso(texto=''){
		let processo = obterNumeroDoProcessoPadraoCNJ(texto)
		if(!processo) return
		let campo = selecionar('[id*="numeroProcesso"]')
		let conteudo = campo?.value || ''
		let processoComDigitos = conteudo?.includes('-')
		let depositoNaoLocalizado = document.body.textContent.includes('Não foi localizado nenhum depósito') || ''
		if(depositoNaoLocalizado){
			clicar('[id*="botaoVoltar"]')
			return
		}
		if(processoComDigitos){
			preencher(campo,numeros(processo))
			continuar()
			return
		}
		if(texto.includes('DepositosJudiciaisBancoDoBrasilConsultaRealizada')) return
		copiar(texto+'DepositosJudiciaisBancoDoBrasilConsultaRealizada')
		preencher(campo,processo)
		continuar()
	}

	function consultarDocumento(texto=''){
		if(!texto.includes('documentoPolo')) return
		let documento = numeros(obterDocumento(texto))
		if(!documento) return
		let campoPoloAtivo = selecionar('[id*="cpfCgcAutor"]')
		let campoPoloPassivo = selecionar('[id*="cpfCgcReu"]')
		if(texto.includes('DepositosJudiciaisBancoDoBrasilConsultaRealizada')) return
		copiar(texto+'DepositosJudiciaisBancoDoBrasilConsultaRealizada')
		if(texto.includes('documentoPoloAtivo')) preencher(campoPoloAtivo,documento)
		if(texto.includes('documentoPoloPassivo')) preencher(campoPoloPassivo,documento)
		continuar()
	}

	function consultarContaJudicial(texto=''){
		if(!texto.includes('bbContaJudicial')) return
		let conta = numeros(texto.replace(/[-].*/,''))
		if(!conta) return
		let campo = selecionar('[id*="numeroDeposito"]')
		if(texto.includes('DepositosJudiciaisBancoDoBrasilConsultaRealizada')) return
		copiar(texto+'DepositosJudiciaisBancoDoBrasilConsultaRealizada')
		preencher(campo,conta)
		continuar()
	}

	function consultarNome(texto=''){
		if(!texto.includes('nomePolo')) return
		let nome = maiusculas(texto.replace(/nomePolo(Ativo|Passivo)./,''))
		if(!nome) return
		let campoPoloAtivo = selecionar('[id*="nomeAutor"]')
		let campoPoloPassivo = selecionar('[id*="nomeReu"]')
		if(texto.includes('DepositosJudiciaisBancoDoBrasilConsultaRealizada')) return
		copiar(texto+'DepositosJudiciaisBancoDoBrasilConsultaRealizada')
		if(texto.includes('nomePoloAtivo')) preencher(campoPoloAtivo,nome)
		if(texto.includes('nomePoloPassivo')) preencher(campoPoloPassivo,nome)
		continuar()
	}

	function continuar(){
		clicar('[id*="botaoContinuar"]')
	}

}


function bbConsultarProcesso(processo=''){
	let pje = pjeObterContexto()
	if(pje) processo = PROCESSO?.numero || ''
	copiar(processo)
	let url = LINK.bb.depositos.magistrados
	abrirPagina(url,'','','','','bancoDoBrasil')
	esforcosPoupados(1,1)
}

function bbConsultarDocumentoPoloAtivo(documento=''){
	copiar('documentoPoloAtivo:'+documento)
	let url = LINK.bb.depositos.magistrados
	abrirPagina(url,'','','','','bancoDoBrasil')
	esforcosPoupados(1,1)
}

function bbConsultarDocumentoPoloPassivo(documento=''){
	copiar('documentoPoloPassivo:'+documento)
	let url = LINK.bb.depositos.magistrados
	abrirPagina(url,'','','','','bancoDoBrasil')
	esforcosPoupados(1,1)
}

function bbConsultarNomePoloAtivo(nome=''){
	copiar('nomePoloAtivo:'+nome)
	let url = LINK.bb.depositos.magistrados
	abrirPagina(url,'','','','','bancoDoBrasil')
	esforcosPoupados(1,1)
}

function bbConsultarNomePoloPassivo(nome=''){
	copiar('nomePoloPassivo:'+nome)
	let url = LINK.bb.depositos.magistrados
	abrirPagina(url,'','','','','bancoDoBrasil')
	esforcosPoupados(1,1)
}

function bbConsultarContaJudicial(conta=''){
	copiar('bbContaJudicial:'+conta)
	let url = LINK.bb.depositos.magistrados
	abrirPagina(url,'','','','','bancoDoBrasil')
	esforcosPoupados(1,1)
}