async function pjeOtimizarPaginaTarefaDoProcesso(){
	let contexto = pjeObterContexto()
	if(!contexto.includes('pje-tarefa')) return
	pjeCriarBotoesFixos()
	pjeCriarPainelSuperior()
	otimizarTarefas()
	setTimeout(aoAbrirTarefa,750)

	async function aoAbrirTarefa(){
		pjeProcessoTarefaEnviarParaRemeterAoSegundoGrau()
		pjeProcessoTarefaEnviarParaTranstoEmJulgado()
		pjeProcessoTarefaEnviarParaConclusaoAMagistrado()
		pjeProcessoTarefaEnviarChipAudienciaDesignadaParaAguardandoAudiencia()
		pjeProcessoTarefaEnviarParaAnalise()
		pjeProcessoTarefaEnviarParaSobrestamento()
	}

	async function otimizarTarefas(){
		pjeOtimizarConclusaoAMagistrado()
		pjeOtimizarRegistrarTransitoEmJulgado()
		pjeOtimizarRemeterAoSegundoGrau()
	}
}

async function pjeProcessoTarefaEnviarParaAnalise(){
	let contexto = pjeObterContexto()
	if(!contexto.includes('pje-tarefa')) return
	let botao = await esperar('[aria-label="Análise"]',true,true)
	if(CONFIGURACAO?.pjeAoAbrirTarefaDoProcesso?.enviarParaAnalise){
		setTimeout(() => clicar(botao),500)
		return
	}
	if(pjeMomentoAdmissibilidadeRecursal() || pjeMomentoDespachar() || pjeMomentoTutelaLiminar()){
		let configuracao = CONFIGURACAO?.pjeAoAbrirTarefaDoProcesso?.admissibilidadeRecursalParaConclusaoMagistrado || CONFIGURACAO?.pjeAoAbrirTarefaDoProcesso?.peticoesParaDespacho || CONFIGURACAO?.pjeAoAbrirTarefaDoProcesso?.tutelaLiminarParaDecisao || ''
		if(configuracao) return
	}
	let chips = PROCESSO?.chips || ''
	let tarefa = PROCESSO?.tarefa?.nomeTarefa || ''
	if(CONFIGURACAO?.pjeAoAbrirTarefaDoProcesso?.enviarParaAnaliseRecebidoParaProsseguir){
		if(tarefa?.includes('Recebimento de instância superior')){
			if(chips.includes('Recebido - para prosseguir')) irParaAnalise()
		}
	}
	if(CONFIGURACAO?.pjeAoAbrirTarefaDoProcesso?.enviarParaAnalisePrazosVencidos){
		if(tarefa?.includes('Prazos Vencidos')) irParaAnalise()
	}

	function irParaAnalise(){
		setTimeout(() => clicar(botao),600)
	}
}

async function pjeProcessoTarefaEnviarParaSobrestamento(){
	let contexto = pjeObterContexto()
	if(!contexto.includes('pje-tarefa')) return
	let botao = await esperar('[aria-label="Sobrestamento"]',true,true)
	if(CONFIGURACAO?.pjeAoAbrirTarefaDoProcesso?.enviarParaSobrestamento) clicar(botao)
}

async function pjeProcessoTarefaEnviarParaConclusaoAMagistrado(){
	let contexto = pjeObterContexto()
	if(!contexto.includes('pje-tarefa')) return
	let botao = await esperar('[aria-label="Conclusão ao magistrado"],[aria-label="Análise"]',true,true)
	if(CONFIGURACAO?.pjeAoAbrirTarefaDoProcesso?.admissibilidadeRecursalParaConclusaoMagistrado){
		if(pjeMomentoAdmissibilidadeRecursal()) clicar(botao)
	}
	if(CONFIGURACAO?.pjeAoAbrirTarefaDoProcesso?.tutelaLiminarParaDecisao){
		if(pjeMomentoTutelaLiminar()) clicar(botao)
	}
	if(CONFIGURACAO?.pjeAoAbrirTarefaDoProcesso?.peticoesParaDespacho){
		if(pjeMomentoDespachar()) clicar(botao)
	}
}

async function pjeProcessoTarefaEnviarParaRemeterAoSegundoGrau(){
	let contexto = pjeObterContexto()
	if(!contexto.includes('pje-tarefa')) return
	let botao = await esperar('[aria-label="Remeter ao 2o Grau"]',true,true)
	let chips = PROCESSO.chips
	if(CONFIGURACAO?.pjeAoAbrirTarefaDoProcesso?.remeterRecursoParaRemeterAoSegundoGrau){
		if(chips.includes('Remeter Recurso')){
			if(pjeMomentoAdmissibilidadeRecursal()) return
			enviar()
		}
	}

	function enviar(){
		setTimeout(() => clicar(botao),500)
	}
}

async function pjeProcessoTarefaEnviarChipAudienciaDesignadaParaAguardandoAudiencia(){
	let contexto = pjeObterContexto()
	if(!contexto.includes('pje-tarefa')) return
	if(!CONFIGURACAO?.pjeAoAbrirTarefaDoProcesso?.chipAudienciaDesignadaEnviarParaAguardandoAudiencia) return
	let botao = await esperar('[aria-label="Aguardando audiência"]',true,true)
	enviar()

	function enviar(){
		setTimeout(() => clicar(botao),600)
	}
}

async function pjeProcessoTarefaEnviarParaTranstoEmJulgado(){
	let contexto = pjeObterContexto()
	if(!contexto.includes('pje-tarefa')) return
	let botao = await esperar('[aria-label="Trânsito em Julgado"]',true,true)
	let chips = PROCESSO.chips
	if(CONFIGURACAO?.pjeAoAbrirTarefaDoProcesso?.enviarParaTranstoEmJulgadoRecebidoParaProsseguir){
		if(chips.includes('Recebido - para prosseguir')){
			setTimeout(() => clicar(botao),600)
		}
	}
}

async function pjeOtimizarRegistrarTransitoEmJulgado(){
	let contexto = pjeObterContexto()
	if(!contexto.includes('pje-tarefa')) return
	if(CONFIGURACAO?.pjeAoAbrirTarefaDoProcesso?.preencherDataDoTransito){
		document.addEventListener('click',preencherDataDeTransitoComDataCopiada)
		esperar('[aria-label="Devolver processo para vara de origem"]',true).then(preencherDataDeTransitoComDataCopiada)
	}

	async function preencherDataDeTransitoComDataCopiada(){
		let campo = selecionar('[name="dataTransitoJulgado"]')
		if(!campo) return
		if(campo.disabled) return
		let texto = await navigator.clipboard.readText()
		if(!texto) return
		let data = obterData(texto)
		if(!data) return
		preencher(campo,data)
	}
}

async function pjeOtimizarRemeterAoSegundoGrau(){
	await pjeRemeterRecursoSelecionarTipo()
	alterarPosicaoDosBotoesDasPartes()
	verificarNotificacoes()
	gravar()

	window.onfocus = () => {
		clicar('[aria-label="Refazer validação do processo"]')
		verificarNotificacoes()
	}

	async function gravar(){
		let gravar = await esperar('[aria-label="Gravar"]:not([disabled])')
		await aguardar(500)
		clicar(gravar)
	}

	async function verificarNotificacoes(){
		if(!CONFIGURACAO?.pjeAoAbrirTarefaDoProcesso?.parteSemEnderecoRetificarAutuacao) return ''
		esperar('.titulo-notificacao').then(() => {
			let retificar = document.querySelectorAll('pje-validacao-remessa a')
			retificar.forEach(elemento => {
				let nome = elemento.parentElement.previousElementSibling.textContent || ''
				if(!nome) return
				nome = nome.replace(/.*?[']/,'').replace(/['].*/,'')
				pjeAbrirRetificarAutuacao(nome)
			})
		})
	}

	async function pjeRemeterRecursoSelecionarTipo(){
		if(!CONFIGURACAO?.pjeAoAbrirTarefaDoProcesso?.remeterRecursoSelecionarTipo) return ''
		let fase = PROCESSO?.labelFaseProcessual || ''
		await esperar('#duplicarPolos',true)
		let campo = await esperar('[aria-label="Classe judicial"]',true,true)
		setTimeout(selecionarTipo,750)
		setTimeout(pjeRemeterRecursoExpandirSelecaoDeCompetencia,1000)

		function selecionarTipo(){
			clicar(campo)
			if(fase.includes('Conhecimento')){
				pjeSelecionarOpcao('Agravo de Petição','[aria-label="Classe judicial"]')
				pjeSelecionarOpcao('Recurso Ordinário Trabalhista','[aria-label="Classe judicial"]')
				pjeSelecionarOpcao('Recurso Ordinário - Rito Sumaríssimo','[aria-label="Classe judicial"]')
			}
			if(fase.includes('Execução')){
				pjeSelecionarOpcao('Agravo de Petição','[aria-label="Classe judicial"]')
			}
		}
		return ''
	}

	async function pjeRemeterRecursoExpandirSelecaoDeCompetencia(){
		clicar('[placeholder="Selecione uma competência"]')
		if(!CONFIGURACAO?.pjeAoAbrirTarefaDoProcesso?.remeterRecursoSelecionarCompetencia) return ''
		pjeSelecionarOpcao('TRT - Turmas','[aria-label="Selecione uma competência"]')
	}

	async function alterarPosicaoDosBotoesDasPartes(){
		if(!CONFIGURACAO?.pjeAoAbrirTarefaDoProcesso?.polosOtimizarBotoes) return ''
		esperar('#duplicarPolos').then(() => {
			let botoes = selecionar('.div-acoes-partes-remessa')
			if(!botoes) return
			botoes.style.cssFloat = 'none'
			botoes.style.margin = '0 auto'
			let polos = selecionar('pje-polo')
			if(!polos) return
			polos.parentElement.insertBefore(botoes,polos)
		})
	}
}