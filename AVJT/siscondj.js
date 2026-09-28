async function siscondj(){
	if(!JANELA.includes(LINK.siscondj.raiz)) return
	otimizarLayout()
	otimizarUsabilidade()
	if(CONFIGURACAO?.usuario?.email?.includes('sisenandosousa@trt15.jus.br')) preencherConta()

	async function preencherConta(){
		let campoBancoDestino = await esperar('#cb_tipoFinalidade_chosen',true,true)
		let campoBeneficiario = await esperar('#comboBeneficiario_chosen',true,true)
		let campoDocumento = await esperar('#solicitacaoTransiente_beneficiario_pessoa_cpfCnpj',true,true)
		let bancoDestino = campoBancoDestino.textContent

		campoBancoDestino.addEventListener('click',() => bancoDestino = campoBancoDestino.textContent)

		campoDocumento.addEventListener('change',() => {
			let documento = campoDocumento.value
			if(bancoDestino.includes('Crédito em Conta para Outros Bancos')){
				if(documento.includes('085.778.308-45')) contaOutrosBancos('3330','01000689','9','Conta Corrente','033')
				if(documento.includes('159.511.158-17')) contaOutrosBancos('2741','00025267','3','Conta Corrente')
				if(documento.includes('613.111.706-34')) contaOutrosBancos('2730','00003770','9','Conta Poupança','104')
			}
			if(bancoDestino.includes('Crédito em Conta no Banco do Brasil')){
				if(documento.includes('042.513.668-08')) contaBancoDoBrasil('1606','138340','X')
				if(documento.includes('101.463.248-03')) contaBancoDoBrasil('4852','805016','3')
			}
		})

		campoBeneficiario.addEventListener('click',() => {
			let beneficiario = campoBeneficiario.textContent
			if(bancoDestino.includes('Crédito em Conta no Banco do Brasil')){
				if(beneficiario.includes('VOLKSWAGEN DO BRASIL INDUSTRIA DE VEICULOS AUTOMOTORES LTDA')) contaBancoDoBrasil('2659','2000','1')
				if(beneficiario.includes('FORD MOTOR COMPANY BRASIL LTDA')) contaBancoDoBrasil('2659','20000','X')
			}
		})

		async function contaOutrosBancos(
			agencia='',
			conta='',
			digito='',
			tipo='Conta Corrente',
			banco=''
		){
			preencher('[id$=agencia]',agencia)
			preencher('[id$=conta]',conta)
			preencher('[id$=digitoVerificadorBB]',digito)
			//let tipoDeCredito = selecionar('#cb_tipoCreditoOutrosBancos_chosen .chosen-single span')
			//await aguardar(500)
			//tipoDeCredito.innerText = tipo
			//dispararEvento('change',tipoDeCredito)
		}

		function contaBancoDoBrasil(
			agencia='',
			conta='',
			digito='',
			tipo='Conta Corrente'
		){
			preencher('[id$=agencia]',agencia)
			preencher('[id$=conta]',conta)
			preencher('[id$=digitoVerificadorBB]',digito)
			let tipoDeCredito = selecionar('#cb_tipoCredito_chosen')
			dispararEvento('mousedown',tipoDeCredito)
		}
	}

	function otimizarLayout(){
		if(!CONFIGURACAO?.siscondj?.otimizarLayout) return
		estilizarSiscondj()
		alterarPosicaoDeBotoesDeAcao()

		async function alterarPosicaoDeBotoesDeAcao(){
			await esperar('[onclick="editarAlvara(this)"]',true,true)
			let alvaras = document.querySelectorAll('th[abbr="id"],td[onclick="editarAlvara(this)"]:last-child')
			alvaras.forEach(alvara => {
				let pai = alvara.parentElement || ''
				let primeiro = pai.querySelector('th[abbr]:first-child,td[onclick="editarAlvara(this)"]:first-child')
				pai.insertBefore(alvara,primeiro)
				let data = pai.querySelector('th[abbr="dataAcaoAlvara"],td[onclick="editarAlvara(this)"]:last-child')
				pai.insertBefore(data,primeiro)
				let situacao = pai.querySelector('th[abbr="acaoUsuario"],td[onclick="editarAlvara(this)"]:last-child').previousElementSibling
				pai.insertBefore(situacao,primeiro)
				let valor = pai.querySelector('th[abbr="acaoUsuario"],td[onclick="editarAlvara(this)"]:last-child').previousElementSibling
				pai.insertBefore(valor,primeiro.previousElementSibling)
				let usuario = pai.querySelector('th[abbr="acaoUsuario"],td[onclick="editarAlvara(this)"]:last-child')
				pai.insertBefore(usuario,primeiro.previousElementSibling)
				let orgao = pai.querySelector('th[abbr]:last-child,td[onclick="editarAlvara(this)"]:last-child').previousElementSibling
				pai.insertBefore(orgao,primeiro.nextElementSibling)
			})
		}
	}

	function otimizarUsabilidade(){
		buscarAlvaras()
		buscarNumeroDoProcesso()
		colarDadoAoClicar()
		expandirDepositos()
		siscondjPrepararCertidao()
		abrirAnexarDocumentosAoClicarNoPDF()
	}

	async function expandirDepositos(){
		let texto = await obterMemoriaTexto()
		if(texto.includes('avjtSiscondjConsultarAlvaras')) return
		if(!CONFIGURACAO?.siscondj?.expandirDepositos) return
		let depositos = document.querySelectorAll('[src*="/images/refresh.png"]')
		depositos.forEach(deposito => clicar(deposito))
		if(JANELA.includes('pages/mandado/pagamento/new/')){
			let parcelas = document.querySelectorAll('[alt="Parcelas"]')
			parcelas.forEach(deposito => clicar(deposito))
		}
	}

	function colarDadoAoClicar(){
		return
	}

	async function abrirAnexarDocumentosAoClicarNoPDF(){
		if(!JANELA.includes('mandado/acompanhamento') || !CONFIGURACAO?.siscondj?.certificarAoAbrirAlvara) return
		let pdfs = document.querySelectorAll('img[src*="icon_pdf.png"]')
		pdfs.forEach(async pdf => {
			pdf.addEventListener('click',async evento => {
				if(!PROCESSO?.id){
					let linha = evento.target.parentElement.parentElement.parentElement.parentElement || ''
					if(!linha) return
					let texto = linha.innerText || ''
					let numero = obterNumeroDoProcessoSemSeparadores(texto)
					if(!numero) return ''
					let processo = converterNumeroDoProcessoSemSeparadoresParaPadraoCNJ(numero)
					if(!processo) return ''
					let dados = await pjeApiConsultaPublicaObterProcessoId(processo)
					PROCESSO = dados[0]
				}
				let certidao = pjeCertificar('Alvará Eletrônico de Pagamento - SISCONDJ-JT','Certidão',false,true)
				LINK.pje.anexar = LINK.pje.processo + PROCESSO.id + '/documento/anexar?certificar='+encodeURIComponent(JSON.stringify(certidao))
				let link = await esperar('#link_pdf',true,true)
				clicar(link)
				setTimeout(pjeAbrirAnexar,1000)
			})
		})
	}

	function buscarNumeroDoProcesso(){
		if(!JANELA.includes('?numeroDoProcesso=')) return
		let numero = obterParametroDeUrl('numeroDoProcesso')
		if(!numero) return
		let campo = selecionar('#numeroProcesso')
		if(!campo) return
		preencher(campo,numeros(numero))
		clicar('#bt_buscar')
	}

	async function buscarAlvaras(){
		let texto = await obterMemoriaTexto()
		if(!texto.includes('avjtSiscondjConsultarAlvaras')) return
		let botaoBuscar = await esperar('#bt_pesquisar_mandado',true,true)
		copiar('')
		await aguardar(250)
		clicar(botaoBuscar)
	}
}


function siscondjConsultarProcesso(processo=''){
	let pje = pjeObterContexto()
	if(!processo){
		if(pje) processo = PROCESSO?.numero || ''
	}
	copiar(processo)
	let url = LINK.siscondj.consultarProcesso + encodeURI(processo)
	abrirPagina(url,'','','','','siscondj')
	esforcosPoupados(1,1)
}

async function siscondjPrepararCertidao(){
	let formulario = selecionar('#form_alvara')
	if(!formulario) return
	let texto = formulario.textContent || ''
	let processo = obterNumeroDoProcessoPadraoCNJ(texto)
	if(!processo) return
	let dados = await pjeApiConsultaPublicaObterProcessoId(processo)
	PROCESSO = dados[0]
	siscondjCriarBotaoCertificar()
}

function siscondjCriarBotaoCertificar(){
	if(!JANELA.includes('/mandado/pagamento/exibir')) return
	let destino = selecionar('#form_alvara h2')
	if(!destino) return
	let titulo = maiusculas(destino.innerText)
	estilizarBotaoCertificarNoPje()
	let protocolo = numeros(destino.innerText)
	let tipo = 'Mandado de Pagamento'
	let beneficiario = obterDadoDaCelula('4')
	let valor = obterDadoDaCelula('5')

	criarBotao(
		'avjt-certificar-siscondj-protocolo',
		'informacoes avjt-siscondj avjt-azul',
		destino,
		'CERTIFICAR PROTOCOLO',
		'Abre a Tarefa "Anexar Documento" e minuta o texto',
		() => {
			let descricao = 'Alvará - SISCONDJ-JT - '+beneficiario+' (R$ '+valor+')'
			let texto = 'CERTIFICO que protocolei, sob o número '+protocolo+', Alvará Eletrônico de Pagamento - SISCONDJ-JT, no valor de R$ '+valor+', em favor de '+beneficiario+'.'
			let certidao = pjeCertificar(descricao,tipo,texto)
			LINK.pje.anexar = LINK.pje.processo + PROCESSO.id + '/documento/anexar?certificar='+encodeURIComponent(JSON.stringify(certidao))
			pjeAbrirAnexar()
		}
	)

	criarBotao(
		'avjt-certificar-siscondj-conferencia',
		'informacoes avjt-siscondj avjt-preto',
		destino,
		'CERTIFICAR CONFERÊNCIA',
		'Abre a Tarefa "Anexar Documento" e minuta o texto',
		() => {
			let descricao = 'Alvará - SISCONDJ-JT - ' + beneficiario
			let texto = pjeCertidaoTextoAlvaraExpedidoSISICONDJ(beneficiario)
			let certidao = pjeCertificar(descricao,tipo,texto)
			LINK.pje.anexar = LINK.pje.processo + PROCESSO.id + '/documento/anexar?certificar='+encodeURIComponent(JSON.stringify(certidao))
			pjeAbrirAnexar()
		}
	)

	function obterDadoDaCelula(indice=''){
		if(!indice) return ''
		let elemento = selecionar('#dados_solicitacao tr td:nth-child('+indice+')')
		if(!elemento) return ''
		let valor = elemento?.textContent?.trim() || ''
		if(!valor) return ''
		return valor
	}
}

function pjeCertidaoTextoAlvaraExpedidoSISICONDJ(beneficiario=''){

return texto = `CERTIFICO a expedição de alvará eletrônico por meio do sistema SISCONDJ (Banco do Brasil) em favor de ${beneficiario}.

Após a conferência e assinatura pelo Juízo, o alvará será automaticamente encaminhado à instituição financeira para o devido pagamento.

O comprovante da operação poderá ser acessado pela parte beneficiária na seguinte página da Internet:
https://www63.bb.com.br/portalbb/djo/id/resgate/dadosResgate.bbx`

}