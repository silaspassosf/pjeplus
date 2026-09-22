async function sigeo(){
	if(!JANELA.includes(LINK.sigeo.dominio)) return
	sigeoInjetarVideoYoutube()
	sigeoPesquisarProcesso()
	sigeoClicarEmCampos()
	sigeoColarData('[id*=id_dataNomeacao]')
	sigeoColarData('[id*=dataPrestacao]')
	sigeoColarData('[id*=dataArbitramento]')
	sigeoColarProcesso('[id*=id_NumeroProcessoJudicial]')
	sigeoColarDocumento('[id*=id_cpfCnpjProfissionalGuiaIndividual]')
	sigeoSelecionarProfissional()
	sigeoSelecionarTodosOsMotivos()
	sigeoSelecionarAcordoJudicial()
	sigeoDefinirValor()
	sigeoDefinirBeneficiados()
	sigeoPrepararCertidao()
}

function sigeoInjetarVideoYoutube(){
	if(JANELA.includes('comum/menu_sistema.jsf') || JANELA.includes('nomearprofissionais/nomearprofissionais') || JANELA.includes('pagamento/mantersolicitacaopagamento/manter')){
		let destino = selecionar('#div_conteudo')
		youtubeCriarQuadro(destino,'SO9ciwl9CZQ','Tutorial do Assistente de Requição de Honorários Periciais no SIGEO do AVJT')
	}
}

async function sigeoPrepararCertidao(){
	let processo = sigeoObterProcessoNumero() || ''
	if(!processo) return
	let dados = await pjeApiConsultaPublicaObterProcessoId(processo)
	PROCESSO = dados[0]
	sigeoCriarBotaoCertificar()
}

function sigeoObterProcessoNumero(){
	let texto = sigeoObterTexto('Número do processo judicial')
	let numero = obterNumeroDoProcessoSemSeparadores(texto)
	if(!numero) return ''
	let processo = converterNumeroDoProcessoSemSeparadoresParaPadraoCNJ(numero)
	if(!processo) return ''
	return processo
}

function sigeoObterTexto(titulo){
	let linhas = document.querySelectorAll('tr')
	let linha = [...linhas].filter(linha => linha.innerText.includes(titulo))
	if(vazio(linha)) return ''
	let celulas = linha[0].querySelectorAll('td')
	if(vazio(celulas)) return ''
	if(!celulas[1]) return ''
	let texto = celulas[1].innerText || ''
	return texto.trim() || ''
}

function sigeoPesquisarProcesso(){
	let processo = obterParametroDeUrl('processo')
	if(!processo) return
	selecionarOpcao('[id*=atributo]','PROCESSO JUDICIAL')
	preencher('[id*=palavra]',processo)
	clicar('[id*=botaoPesquisarPorPalavraChave]')
}

function sigeoClicarEmCampos(){
	window.addEventListener('focus',() => {
		clicarSeVazio('[id*=id_dataNomeacao]')
		clicarSeVazio('[id*=id_NumeroProcessoJudicial]')
		clicarSeVazio('[id*=id_cpfCnpjProfissionalGuiaIndividual]')
	})

	function clicarSeVazio(seletor){
		let campo = selecionar(seletor)
		if(!campo) return
		if(!campo.value || campo.value.includes(' ')) clicar(campo)
	}
}

function sigeoSelecionarProfissional(){
	sigeoSelecionarOpcao('PERITO')
	sigeoCriarSelecao('ENGENHEIRO')
	sigeoCriarSelecao('MÉDICO')
	selecionarResultado()

	function selecionarResultado(){
		if(!JANELA.includes('nomearprofissionais_popup_1_pesquisarprofissionais')) return
		clicar('[name*=profissional]')
	}
}

function sigeoSelecionarTodosOsMotivos(){
	clicar('#idSelecionaTodosmotivos')
}

function sigeoSelecionarAcordoJudicial(){
	let opcao = document.querySelectorAll('[name*=selectAcordoJudicial]') || ''
	if(vazio(opcao)) return
	if(opcao[0]?.checked) return
	if(opcao[1]?.checked) return
	if(opcao[1]) clicar(opcao[1])
}

function sigeoDefinirValor(){
	let linhas = document.querySelectorAll('tr')
	let linha = [...linhas].filter(linha => linha.innerText.includes('Valor Máximo do Regional'))
	if(vazio(linha)) return
	let texto = linha[0].innerText || ''
	if(!texto) return
	let valor = obterValorMonetario(texto)
	if(!valor) return
	preencher('[id*=valorInfSo]',valor)
}

function sigeoDefinirBeneficiados(){
	preencher('[id*=quantidadeBeneficiados]',1)
}

function sigeoColarData(seletor){
	let campo = selecionar(seletor)
	if(!campo) return
	campo.addEventListener('click',() => {
		navigator.clipboard.readText().then(
			texto => {
				if(!texto) return
				let data = obterData(texto)
				if(!data) return
				preencher(campo,data)
			}
		)
	})
}


function sigeoColarDocumento(seletor){
	let campo = selecionar(seletor)
	if(!campo) return
	campo.addEventListener('click',() => {
		navigator.clipboard.readText().then(
			texto => {
				if(!texto) return
				let documento = obterDocumento(texto)
				if(!documento) return
				preencher(campo,numeros(documento))
			}
		)
	})
}

function sigeoColarProcesso(seletor){
	let campo = selecionar(seletor)
	if(!campo) return
	campo.addEventListener('click',() => {
		navigator.clipboard.readText().then(
			texto => {
				if(!texto) return
				let processo = obterNumeroDoProcessoPadraoCNJ(texto)
				if(!processo) return
				preencher(campo,numeros(processo))
				clicar('[id*=pesquisarProcesso]')
			}
		)
	})
}

function sigeoCriarSelecao(texto){
	let selecao = selecionar('[id*=id_profissoes]')
	if(!selecao) return
	let ancestral = selecao.parentNode || ''
	if(!ancestral) return
	estilizarBotaoCertificarNoPje()
	estilizar(ancestral,'span{display:flex;}')
	criarBotao(
		'avjt-sigeo-'+removerAcentuacao(minusculas(texto)),
		'avjt-preto sigeo-especialidades informacoes',
		ancestral,
		texto,
		'Selecionar '+texto,
		() => sigeoSelecionarOpcao(texto,true)
	)
}

function sigeoCriarBotaoCertificar(){
	let ancestral = selecionar('#h1_gaveta_01')
	if(!ancestral) return
	estilizarBotaoCertificarNoPje()
	criarBotao(
		'avjt-certificar-sigeo',
		'informacoes avjt-azul',
		ancestral,
		'CERTIFICAR NO PJE',
		'Abre a Tarefa Anexar Documento',
		() => {
			let protocolo = sigeoObterTexto('Número da Nomeação')
			let tipo = 'Requisição de Honorários Periciais'
			let descricao = sigeoObterTexto('Nome do profissional')
			let corpo = 'CERTIFICO que protocolei, sob o número '+protocolo+', '+tipo+' em favor de '+descricao+'.'
			let certidao = pjeCertificar(descricao,tipo,corpo)
			LINK.pje.anexar = LINK.pje.processo + PROCESSO.id + '/documento/anexar?certificar='+encodeURIComponent(JSON.stringify(certidao))
			pjeAbrirAnexar()
		}
	)
}

function sigeoSelecionarOpcao(
	texto,
	repetir=false
){
	if(!texto) return
	let opcao = document.evaluate('//option[text()="'+texto+'"]',document,null,XPathResult.FIRST_ORDERED_NODE_TYPE,null).singleNodeValue || ''
	if(!opcao) return
	let selecao = opcao.parentNode
	if(repetir || selecao.selectedIndex == 0){
		opcao.parentNode.selectedIndex = opcao.index
		dispararEvento('change',selecao)
		esforcosPoupados(2,2)
	}
}

function sigeoPesquisarRequisicaoDeHonorariosPericiais(){
	let url = LINK.sigeo.processo + PROCESSO.numero
	abrirPagina(url,'','','','','sigeo')
}