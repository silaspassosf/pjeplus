async function pjeCalc(){
	if(!JANELA.includes(LINK.pje.calc)) return
	pjeCalcCriarBotaoLimparMemoria()
	let texto = await obterMemoriaTexto()
	if(texto.includes('avjtBuscarCalculo')) clicar('[title="Buscar Cálculo"]')
	if(texto.includes('avjtNovoCalculo')) clicar('[title="Criar Novo Cálculo"]')
	if(CONFIGURACAO.usuario.unidade.includes('Taubaté')){
		pjeCalcOtimizarLayout()
	}
	pjeCalcBuscarCalculo()
	pjeCalcNovoCalculo()
	pjeCalcOtimizarCampos()
}

function pjeCalcObterProcesso(texto){
	let processo = obterNumeroDoProcessoPadraoCNJ(texto)
	if(!processo) return ''
	return obterDadosDoNumeroDoProcesso(processo)
}

function pjeCalcCriarBotaoLimparMemoria(){
	estilizarBotaoCertificarNoPje()
	estilizarBotaoPjeCalcLimparMemoria()
	criarBotao('avjt-limpar-memoria','informacoes avjt-vermelho','','LIMPAR MEMÓRIA','Limpa a Memória do PJe Calc, evitando o bug que exibe o último cálculo feito',() => {
		copiar('')
		clicar('.menuImageClose')
	})
}

async function pjeCalcBuscarCalculo(){
	let texto = await obterMemoriaTexto()
	if(!texto.includes('avjtBuscarCalculo')) return
	clicar('[title="Buscar Cálculo"]')
	PROCESSO = pjeCalcObterProcesso(texto)
	let campoOrdenador = await esperar('[id="formulario:numeroProcessoBusca"]',true,true)
	preencher(campoOrdenador,PROCESSO.ordenador)
	preencher('[id="formulario:digitoProcessoBusca"]',PROCESSO.digito)
	preencher('[id="formulario:anoProcessoBusca"]',PROCESSO.ano)
	preencher('[id="formulario:justicaBusca"]',PROCESSO.jurisdicao)
	preencher('[id="formulario:regiaoBusca"]',PROCESSO.tribunal)
	preencher('[id="formulario:varaProcessoBusca"]',PROCESSO.origem)
	clicar('[id="formulario:setor"]')
	clicar('[id="formulario:buscar"]')
}

async function pjeCalcNovoCalculo(){
	let texto = await obterMemoriaTexto()
	if(!texto.includes('avjtNovoCalculo')) return
	clicar('[title="Criar Novo Cálculo"]')
	PROCESSO = pjeCalcObterProcesso(texto)
	clicar('[title="Selecionar Processo do PJe"]')
	if(CONFIGURACAO.instituicao.tribunal === '15'){
		parametrosDoCalculo()
		preencherVerbas()
		preencherLancamentoExpresso()
	}
	let campoOrdenador = await esperar('[id="formularioModalPPJE:numero"]',true,true)
	await pjeCalcColarNoCampo(campoOrdenador,PROCESSO.ordenador)
	await pjeCalcColarNoCampo('[id="formularioModalPPJE:digito"]',PROCESSO.digito)
	await pjeCalcColarNoCampo('[id="formularioModalPPJE:ano"]',PROCESSO.ano)
	await pjeCalcColarNoCampo('[id="formularioModalPPJE:regiao"]',PROCESSO.tribunal)
	await pjeCalcColarNoCampo('[id="formularioModalPPJE:vara"]',PROCESSO.origem)
	clicar('[id="formularioModalPPJE:cmdVisualizarPPJE"]')
	copiar('avjtNovoCalculo')

	async function parametrosDoCalculo(){
		let parametros = await esperar('[id="formulario:tabParametrosCalculo_lbl"]',true,true)
		parametros.addEventListener('click',alterarParemetros)
		let botaoConfirmar = await esperar('[value="Confirmar"]:not([disabled]',true,true)
		botaoConfirmar.addEventListener('click',ativarParemetros)
		await aguardar(250)

		async function ativarParemetros(){
			await aguardar(500)
			clicar(parametros)
		}

		async function alterarParemetros(){
			await esperar('[id="formulario:estado"]',true,true)
			selecionarOpcao('[id="formulario:estado"]','SP')
			await aguardar(750)
			if(!CONFIGURACAO.usuario.unidade.includes('Taubaté')) return
			await esperar('[id="formulario:municipio"]',true,true)
			selecionarOpcao('[id="formulario:municipio"]','TAUBATE')
			preencherDataDoCalculo()
		}

		function preencherDataDoCalculo(){
			let campoAdmissao = focar('[id="formulario:dataAdmissaoInputDate"]')
			campoAdmissao.addEventListener('keyup',() => {
				let data = campoAdmissao.value
				selecionar('[id="formulario:dataAjuizamentoInputDate"]').value = data
				selecionar('[id="formulario:dataInicioCalculoInputDate"]').value = data
				selecionar('[id="formulario:dataTerminoCalculoInputDate"]').value = data
				copiar('avjtNovoCalculo')
			})
		}
	}

	async function preencherVerbas(){
		if(!JANELA.includes('calculo/verba/verba-calculo')) return
		let descricao = await esperar('[id="formulario:descricao"]',true,true)
		preencher(descricao,'PRINCIPAL')
		await aguardar(500)
		focar('[id="formulario:valorInformadoDoDevido"]')
	}

	async function preencherLancamentoExpresso(){
		if(!JANELA.includes('calculo/verba/verbas-para-calculo')) return
		let botaoSalvar = await esperar('[id="formulario:panelBotoes"] [id="formulario:salvar"]',true,true)
		let verba = selecionarPorTexto('ACORDO (VERBAS INDENIZATÓRIAS)','span')
		clicar(verba.previousElementSibling)
		await aguardar(500)
		clicar(botaoSalvar)
	}


}

async function pjeCalcOtimizarCampos(){
	
	let observador = new MutationObserver(async () => {
		let observado = selecionar('[id="formulario:descricao"]')
		console.debug('observado',observado)
		if(!observado) return
		let contexto = await pjeCalcObterContexto()
		if(contexto.includes('Cálculo > Multas e Indenizações > Novo')){
			console.debug('JANELA',JANELA)
			otimizarCamposMultasIndenizacoes()
		}
		//observador.disconnect()
	})
	observador.observe(document.body,{childList:true,subtree:true,attributes:true,characterData:true})

	async function otimizarCamposMultasIndenizacoes(){
		let campoDescricao = selecionar('[id="formulario:descricao"]')
		if(!campoDescricao) return
		if(campoDescricao?.list) return
		criarDataList(campoDescricao,'pje-calc-campo-descricao-multas-indenizacoes',['FGTS','INSS - PARTE EXECUTADA','INSS - PARTE EXEQUENTE','JUROS DE MORA','MULTA'])
		campoDescricao.addEventListener('input',async () => {
			let descricao = campoDescricao.value || ''
			let seletor = '[id="formulario:credorDevedor"]'
			let campo = selecionar(seletor)
			if(descricao) clicar('[name="formulario:valor"]')
			if(descricao.includes('INSS - PARTE EXECUTADA')) alterarCampo('Terceiro e Reclamado')
			if(descricao.includes('INSS - PARTE EXEQUENTE')){
				alterarCampo('Terceiro e Reclamante')
				await aguardar(100)
				clicar('[value="DESCONTAR_CREDITO"]')
			}
			await aguardar(100)
			otimizarCampoTerceiro()
		
			async function alterarCampo(valor=''){
				let opcao = campo.options[campo.selectedIndex].text || ''
				if(opcao.includes(valor)) return
				selecionarOpcao(seletor,valor)
			}

			async function otimizarCampoTerceiro(){
				let campo = selecionar('[id="formulario:terceiro"]')
				if(!campo) return
				let terceiro = descricao.match(/fgts|inss/gi) || ''	
				if(terceiro){
					if(campo.value) return
					campo.value = terceiro[0]
				} 
				if(campo?.list) return
				criarDataList(campo,'pje-calc-campo-terceiro',['FGTS','INSS'])
			}
		})
	}
}

async function pjeCalcOtimizarLayout(){
	estilizar('',`
	.menu-item li:not(
		#li_calculo_verbas,
		#li_calculo_multas_e_indenizacoes,
		#li_calculo_honorarios,
		#li_calculo_custas_judiciais,
		#li_calculo_correcao_juros_multa,
		#li_operacoes_liquidar,
		#li_calculo_relatorios,
		#li_operacoes_validar
	){
		opacity:0.5;
	}
	`,
	'avjt-estilo-pje-calc')
}

async function pjeCalcColarNoCampo(
	campo='',
	texto=''
){
	if(typeof campo == 'string') campo = selecionar(campo)
	if(!campo || !texto) return
	focar(campo)
	copiar(texto)
	await aguardar(500)
	colar()
}

async function pjeCalcObterContexto(){
	let titulo = await esperar('#barraTitulo',true,true)
	if(!titulo) return ''
	let contexto = titulo?.innerText?.trim() || ''
	console.debug('Contexto - PJeCalc:',contexto)
	return contexto
}