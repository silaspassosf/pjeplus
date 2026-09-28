async function cef(){
	if(!JANELA.includes(LINK.cef.dominio)) return
	autenticacao()
	cefConsultarDepositosRecursais()
	cefConsultarDepositosJudiciais()

	function autenticacao(){
		if(JANELA.includes('https://depositojudicial.caixa.gov.br/sigsj_internet/principal.xhtml')) window.location.href = LINK.cef.depositos.login
		let indisponibilidade = document.body.innerText.match(/Sistema Temporariamente Indisponível/gi) || ''
		if(indisponibilidade) window.location.href = LINK.cef.depositos.login
	}

}


async function cefConsultarDepositosRecursais(){
	if(JANELA.includes('conectividadesocialv2.caixa.gov.br')) caixaEconomicaFederalConectividade()
	if(JANELA.includes('sicse.caixa.gov.br')) caixaEconomicaFederalConectividadeSICSE()

	async function caixaEconomicaFederalConectividade(){
		clicar('Magistrado',true)
		let outorgante = await esperar('app-trocar-outorga div.row:nth-child(3) > button:nth-child(1)',true,true)
		clicar(outorgante)
		let cpf = await esperar('app-trocar-outorga #mat-radio-4 input',true,true)
		clicar(cpf)
		let inscricao = await esperar('[formcontrolname="inscricao"]',true,true)
		clicar(inscricao)
		let delegante = CONFIGURACAO.delegacoes.cefDepositosRecursais || ''
		preencher(inscricao,numeros(delegante))
		let buscar = await esperar('app-trocar-outorga .btnOK',true,true)
		clicar(buscar)
	}

	function caixaEconomicaFederalConectividadeSICSE(){
		if(JANELA.includes('sicse/ControladorPrincipalServlet')) selecionarOpcao('[name="sltOpcao"]','Extrato FGTS Trabalhador-Conta Recursal')
		if(document.body.textContent.includes('Extrato FGTS Trabalhador − Conta Recursal')){
			navigator.clipboard.readText().then(
				texto => {
					if(!texto) return
					let numero = numeros(texto)
					let campoTrabalhador = selecionar('[name="txtNomeTrabalhador"]')
					let campoProcesso = selecionar('[name="txtNumProcesso"]')
					let campoOrgao = selecionar('[name="txtJuntaTrabalhista"]')
					let botao = selecionar('[href="javascript:subm_localizar_conta_recursal();"]')
					if(numero){
						let processo = numero.substring(15,0)
						let orgao = numero.substring(15)
						preencher(campoProcesso,processo)
						preencher(campoOrgao,orgao)
						clicar(botao)
						copiar('')
					}
					else{
						preencher(campoTrabalhador,texto.replace(EXPRESSAO.processoNumero,'').replace(/DepositosJudiciais.*?ConsultaRealizada/gi,''))
						focar(campoTrabalhador)
					}
				}
			)
			estilizarConectividadeSocial()
		}
	}

}


function cefConsultarDepositosJudiciais(){
	if(!JANELA.includes('depositojudicial') || !JANELA.includes('consulta-avancada') || JANELA.includes('login') || JANELA.includes('Autenticacao')) return
	navigator.clipboard.readText().then(
		texto => {
			if(!texto) return
			consultarProcesso(texto)
			consultarDocumento(texto)
			consultarNome(texto)
		}
	)

	function consultarProcesso(texto=''){
		let processo = obterNumeroDoProcessoPadraoCNJ(texto)
		if(!processo) return
		let campo = selecionar('[id*="nuProcesso"')
		if(!campo) return
		if(texto.includes('DepositosJudiciaisCaixaEconomicaFederalConsultaRealizada')) return
		preencher(campo,numeros(processo))
		copiar(texto+'DepositosJudiciaisCaixaEconomicaFederalConsultaRealizada')
		continuar()
	}

	function consultarDocumento(texto=''){
		let cnpj = obterCNPJ(texto)
		let cpf = obterCPF(texto)
		let documento = obterDocumento(texto)
		if(!documento) return
		let selecaoPoloAtivo = selecionar('[id*="tipoDocPesquisa"]')
		let campoPoloAtivo = selecionar('[id*="codDocPesquisa"]')
		let selecaoPoloPassivo = selecionar('[id*="tipoDocReu"]')
		let campoPoloPassivo = selecionar('[id*="codDocReu"]')
		if(texto.includes('DepositosJudiciaisCaixaEconomicaFederalConsultaRealizada')) return
		copiar(texto+'DepositosJudiciaisCaixaEconomicaFederalConsultaRealizada')
		if(texto.includes('documentoPoloAtivo')){
			if(cpf) selecaoPoloAtivo.selectedIndex = 1
			if(cnpj) selecaoPoloAtivo.selectedIndex = 2
			dispararEvento('change',selecaoPoloAtivo)
			preencher(campoPoloAtivo,documento)
		}
		if(texto.includes('documentoPoloPassivo')){
			if(cpf) selecaoPoloPassivo.selectedIndex = 1
			if(cnpj) selecaoPoloPassivo.selectedIndex = 2
			dispararEvento('change',selecaoPoloPassivo)
			preencher(campoPoloPassivo,documento)
		}
		continuar()
	}

	function consultarNome(texto=''){
		let nome = maiusculas(texto.replace(/nomePolo(Ativo|Passivo)./,''))
		if(!nome) return
		let numero = numeros(nome)
		if(numero) return
		let campoPoloAtivo = selecionar('[id*="noAutor"]')
		let campoPoloPassivo = selecionar('[id*="noReu"]')
		if(texto.includes('DepositosJudiciaisCaixaEconomicaFederalConsultaRealizada')) return
		copiar(texto+'DepositosJudiciaisCaixaEconomicaFederalConsultaRealizada')
		if(texto.includes('nomePoloAtivo')) preencher(campoPoloAtivo,nome)
		if(texto.includes('nomePoloPassivo')) preencher(campoPoloPassivo,nome)
		continuar()
	}

	function continuar(){
		clicar('[title="Consultar"]')
	}

}


function cefConsultarDepositosJudiciaisProcesso(processo=''){
	let pje = pjeObterContexto()
	if(pje) processo = PROCESSO?.numero || ''
	copiar(processo)
	let url = LINK.cef.depositos.judiciais
	abrirPagina(url,'','','','','cefJudiciais')
	esforcosPoupados(1,1)
}

function cefConsultarDepositosRecursaisPorNomeDoPoloAtivo(nome=''){
	let pje = pjeObterContexto()
	if(pje){
		if(!nome || nome.match(EXPRESSAO.processoNumero)) nome += PROCESSO?.partes?.ATIVO[0]?.nome || ''
	}
	copiar(nome)
	let url = LINK.cef.depositos.recursais
	abrirPagina(url,'','','','','cefRecursais')
	esforcosPoupados(1,1)
}

function cefConsultarDocumentoPoloAtivo(documento=''){
	copiar('documentoPoloAtivo:'+documento)
	let url = LINK.cef.depositos.judiciais
	abrirPagina(url,'','','','','cefRecursais')
	esforcosPoupados(1,1)
}

function cefConsultarDocumentoPoloPassivo(documento=''){
	copiar('documentoPoloPassivo:'+documento)
	let url = LINK.cef.depositos.judiciais
	abrirPagina(url,'','','','','cefJudiciais')
	esforcosPoupados(1,1)
}

function cefConsultarNomePoloAtivo(nome=''){
	copiar('nomePoloAtivo:'+nome)
	let url = LINK.cef.depositos.judiciais
	abrirPagina(url,'','','','','cefRecursais')
	esforcosPoupados(1,1)
}

function cefConsultarNomePoloPassivo(nome=''){
	copiar('nomePoloPassivo:'+nome)
	let url = LINK.cef.depositos.judiciais
	abrirPagina(url,'','','','','cefJudiciais')
	esforcosPoupados(1,1)
}