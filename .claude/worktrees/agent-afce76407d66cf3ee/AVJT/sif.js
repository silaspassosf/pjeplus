async function sif(){
	if(!JANELA.includes('jus.br/sif')) return
	PROCESSO = await pjeObterDadosDoProcessoPorNumeroSemSeparadores()
	PROCESSO.partes = await pjeApiObterProcessoPartes(PROCESSO.id)
	let DEPOSITO = {}

	criarBotaoMagistradoConfiguracoes()

	criarBotaoCertificarNaConferencia()
	let intervalo = setInterval(() => {
		let dadosDaConta = selecionar('pje-dado-conta')
		if(dadosDaConta){
			clearInterval(intervalo)
			deposito = obterDadosDoDeposito()
			console.info('Dados do Depósito',deposito)
			esperar('[placeholder="Confeccionar Alvará"]',true,true).then(selecionarTransferenciaAoBeneficiario)
			esperar('pje-selecionar-magistrado mat-expansion-panel-header',true,true).then(selecionarMagistradoPorFinadlDoProcesso)
			preencherDadosDoBeneficiario()
			let conta = window.location.href.replace(/^.*\d{20}./,'')
			pjeApiSifObterContaDados(PROCESSO.numeros,conta).then(dados => {
				let data = new Date(dados.dtDeposito)
				dados.data = data?.toLocaleDateString() || ''
				dados.valor = dados.vlDeposito?.toLocaleString('pt-BR',{minimumFractionDigits:2}) || ''
				DEPOSITO = dados
				console.info('Depósito:',DEPOSITO)
				preencherValorOriginario()
				preencherValorDisponivel()
				preencherDataDaCorrecaoBancariaComDataOriginaria()
				preencherDataDaCorrecaoBancariaComDataHoje()
			})
		}
	},1000)

	async function selecionarTransferenciaAoBeneficiario(){
		if(!CONFIGURACAO?.sif?.selecionarTransferencia) return
		clicar('[placeholder="Confeccionar Alvará"]')
		await esperar('[aria-label="Selecione o Tipo de Alvará"] mat-option',true,true)
		pjeSelecionarOpcaoPorTexto('Transferência ao Beneficiário')
	}

	async function selecionarMagistradoPorFinadlDoProcesso(){
		if(!CONFIGURACAO?.sif?.selecionarMagistrado) return
		let magistrado = CONFIGURACAO?.pjeMagistrados[PROCESSO.digitoFinal] || ''
		clicar('pje-selecionar-magistrado mat-expansion-panel-header')
		await esperar('mat-list.lista-magistrados mat-list-item button',true,true)
		setTimeout(() => selecionarMagistrado(magistrado),200)
	}

	async function selecionarMagistrado(magistrado=''){
		if(!magistrado) return ''
		await esperar('mat-list-item',true,true)
		let opcao = [...document.querySelectorAll('mat-list-item')].filter(opcao => opcao.innerText == magistrado)[0] || ''
		clicar(opcao)
	}

	async function preencherValorOriginario(){
		if(!CONFIGURACAO?.sif?.preencherValorOriginario) return
		let campo = await esperar('[formcontrolname="valor"]',true,true)
		setTimeout(() => preencher(campo,DEPOSITO.valor,false,true,'cut'),500)
	}

	async function preencherValorDisponivel(){
		if(!CONFIGURACAO?.sif?.preencherValorDisponivel) return
		let valor = selecionar('.saldoDisponivel')
		if(!valor) return
		let saldo = obterValorMonetario(valor.innerText)
		let campo = await esperar('[formcontrolname="valor"]',true,true)
		setTimeout(() => preencher(campo,saldo,false,true,'cut'),550)
	}

	async function preencherDataDaCorrecaoBancariaComDataOriginaria(){
		if(!CONFIGURACAO?.sif?.preencherDataOriginaria) return
		let campo = await esperar('[formcontrolname="dataAtualizacao"]',true,true)
		setTimeout(() => preencher(campo,DEPOSITO.data),600)
	}

	async function preencherDataDaCorrecaoBancariaComDataHoje(){
		if(!CONFIGURACAO?.sif?.preencherDataHoje) return
		let campo = await esperar('[formcontrolname="dataAtualizacao"]',true,true)
		setTimeout(() => preencher(campo,DATA.hoje.curta),650)
	}

	async function obterDadosDoDeposito(){
		let conta = JANELA.replace(/^.*\d{20}./,'')
		let dados = await pjeApiSifObterContaDados(PROCESSO.numeros,conta)
		let data = new Date(dados.dtDeposito)
		dados.data = data?.toLocaleDateString() || ''
		dados.valor = dados.vlDeposito?.toLocaleString('pt-BR',{minimumFractionDigits:2}) || ''
		return dados
	}

	async function preencherDadosDoBeneficiario(){
		let campo = await esperar('[formcontrolname="beneficiario"]',true,true)
		let observador = new MutationObserver(() => {
			let beneficiario = obterDadosDoBeneficiario(campo.innerText)
			preencherNomeDoTitular(beneficiario.nome)
		})
		observador.observe(campo,{
			childList:true,
			subtree:true,
			attributes:true,
			characterData:false
		})

		function preencherNomeDoTitular(nome){
			if(!CONFIGURACAO?.sif?.preencherNomeTitular) return
			preencher('[formcontrolname="titular"]',nome)
			setTimeout(clicarEmRepresentacaoProcessual,500)
			function clicarEmRepresentacaoProcessual(){
				let titular = selecionar('[label*="Reclama"],[label*="Advogad"],[label*="Terceir"]')
				if(!titular) selecionarRepresentacaoProcessual()
			}
		}

		function selecionarRepresentacaoProcessual(){
			if(!CONFIGURACAO?.sif?.selecionarRepresentacao) return
			clicar('[aria-label="Selecione o Representante Processual"]')
		}

		function obterDadosDoBeneficiario(texto){
			let beneficiario = {}
			beneficiario.nome = texto.trim().replace(/\s[(].*?[)]$/,'') || ''
			beneficiario.tipo = obterTipo(texto) || ''
			return beneficiario

			function obterTipo(texto){
				let tipo = texto.trim().match(/[(].*?[)]$/) || ''
				if(!tipo) return ''
				return tipo[0].replace(/[()]/g,'') || ''
			}
		}
	}

	function criarBotaoMagistradoConfiguracoes(){
		let destino = selecionar('.conteudo')
		let configuracoes = criarBotao(
			'conclusao-ao-magistrado-configuracoes',
			'configuracoes informacoes',
			destino,
			'',
			'Configuracões de Seleção Automática de Magistrad(a)os',
			abrirPaginaConfiguracoesMagistrado
		)
		estilizar(configuracoes,
			`#conclusao-ao-magistrado-configuracoes{
				position:fixed !important;
			}`
		)
	}
/*
	async function criarBotaoCertificarNasLinhas(){

		if(!JANELA.includes('sif/alvara/incluir/')) return
		await esperar('pje-novo-alvara')
		await esperar('tbody tr')
		let linhas = selecionar('tbody tr','',true)
		console.info('linhas:', linhas)
		estilizarBotaoCertificarNoPje()
		Array.from(linhas).forEach((linha,indice) => {
			let destino = linha.cells[8] || ''
				if(!destino) return
				criarBotao(
					'avjt-certificar-sif+'+indice,
					'informacoes avjt-azul',
					destino,
					'CERTIFICAR',
					'Abre a Tarefa "Anexar Documento" e minuta o texto',
					async () => {
						let botaoDetalhar = destino.querySelector('[mattooltip="Detalhar Alvará"]')
						console.info('botaoDetalhar:', botaoDetalhar)
						clicar(botaoDetalhar)
						let beneficiario = await esperar('pje-detalhe-beneficiario mat-label')
						let nome = beneficiario?.innerText || ''

						let tipo = 'Certidão'
						let descricao = 'Alvará Expedido em favor de ' + nome
						let texto = pjeCertidaoTextoAlvaraExpedidoSIF(nome)
						let certidao = pjeCertificar(descricao,tipo,texto)
						LINK.pje.anexar = LINK.pje.processo + PROCESSO.id + '/documento/anexar?certificar='+encodeURIComponent(JSON.stringify(certidao))
						pjeAbrirAnexar()

					}
				)

		})
		
	}
*/
	async function criarBotaoCertificarNaConferencia(){

		if(!JANELA.includes('sif/alvara/incluir/')) return
		estilizarBotaoCertificarNoPje()
		let botao = await esperar('[mattooltip^="Altera o status para Aguardando Assinatura"], pje-detalhe-alvara-dialog button')

		let botoes = selecionar('.mat-dialog-actions button','',1)
		botoes.forEach(elemento => {
			elemento.addEventListener(
				'click',
				async () => {
					await aguardar(1000)
					criarBotaoCertificarNaConferencia()
				}
			)
		})

		let destino = botao.parentElement || ''
		if(!destino) return
		criarBotao(
			'avjt-certificar-sif-conferencia',
			'avjt-azul',
			destino,
			'CERTIFICAR',
			'Abre a Tarefa "Anexar Documento" e minuta o texto',
			async () => {
				let beneficiario = await esperar('[aria-label="Selecione o Beneficiário"], pje-detalhe-beneficiario mat-label')
				let nome = beneficiario?.innerText?.trim() || ''
				let tipo = 'Certidão'
				let descricao = 'Alvará - SIF - em favor de ' + nome
				let texto = pjeCertidaoTextoAlvaraExpedidoSIF(nome)
				let certidao = pjeCertificar(descricao,tipo,texto)
				LINK.pje.anexar = LINK.pje.processo + PROCESSO.id + '/documento/anexar?certificar='+encodeURIComponent(JSON.stringify(certidao))
				pjeAbrirAnexar()
			}
		)

		
	}

}


function pjeCertidaoTextoAlvaraExpedidoSIF(beneficiario=''){

return texto = `CERTIFICO a expedição de alvará eletrônico por meio do sistema SIF (Caixa Econômica Federal) em favor de ${beneficiario}.

Após a conferência e assinatura pelo Juízo, o alvará será automaticamente encaminhado à instituição financeira para o devido pagamento.

Oportunamente, de forma automática, o cumprimento do alvará será certificado nestes autos com os dados da transferência (valor, data do cumprimento, beneficiário, dados bancários, número de processo).

O comprovante da operação também poderá ser acessado pelo número da conta judicial na seguinte página da Internet:
https://depositojudicial.caixa.gov.br/sigsj_internet/levantamento-deposito-judicial/`

}
