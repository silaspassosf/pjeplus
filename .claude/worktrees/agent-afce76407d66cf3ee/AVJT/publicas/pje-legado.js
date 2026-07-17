async function pjeOtimizarLegado(){
	pjeLegadoOtimizarArvoreDeTarefas()
	pjeLegadoDetalhesDoProcesso()
	pjeLegadoEnviarAoArquivo()
	let arvore = selecionar('#listaDeProcessosPanel_body')
	if(!arvore) return
	arvore.addEventListener('click',() => setTimeout(pjeLegadoOtimizarArvoreDeTarefas,1000))
}

async function pjeLegadoEnviarAoArquivo(){
	if(!JANELA.includes('.jus.br/primeirograu/Processo/movimentar.seam')) return
	let arquivo = await esperar('#pageBody #tabSaida [value="Arquivo"]',true,true)
	clicar(arquivo)
}

function pjeLegadoOtimizarArvoreDeTarefas(){
	if(!JANELA.includes('.jus.br/primeirograu/Painel/')) return
	let tarefas = document.querySelectorAll('table[id*="idTarefaTree"]')
	EXPRESSAO.tarefa								= {}
	EXPRESSAO.tarefa.aguardar				= new RegExp('Aguardando apreciação pela instância superior|Aguardando audiência|Aguardando cumprimento de acordo|Aguardando prazo|Aguardando prazo recursal|Aguardando término dos prazos|Analisar decisão - AR|Analisar Despacho|Analisar sentença|Analisar despacho ED|Cartas devolvidas|Analisar sentença ED|Assinar decisão|Assinar despacho|Assinar sentença|Elaborar decisão|Elaborar despacho|Elaborar sentença|Apreciar dependência|Minutar dependência|Minutar sentença|Minutar sentença ED|Minutar Decisão|Minutar Despacho - Conversão em diligência|Minutar expediente de secretaria|Minutar Despacho|Assinar expedientes e comunicações - magistrado|Concluso ao magistrado','gi')
	EXPRESSAO.tarefa.urgente				= new RegExp('Acordos vencidos|Análise|Iniciar|Apreciar admissibilidade de recursos|Escolher tipo de arquivamento|Prazos|Recebimento de instância superior|Reexame necessário|em julgado|Remeter ao 2o Grau|Triagem Inicial','gi')
	EXPRESSAO.tarefa.ordinaria			= new RegExp('Aguardando final do sobrestamento','gi')
	EXPRESSAO.tarefa.intermediaria	= new RegExp('Cumprimento de .rovidência|Preparar comunicação|Preparar expediente|Publicar|Intimações.*?pendências','gi')
	tarefas.forEach(tarefa => {
		if(tarefa.textContent.match(EXPRESSAO.tarefa.aguardar)) tarefa.style.color='#888'
		if(tarefa.textContent.match(EXPRESSAO.tarefa.urgente)) tarefa.style.color='#F00'
		if(tarefa.textContent.match(EXPRESSAO.tarefa.ordinaria)) tarefa.style.color='#00F'
		if(tarefa.textContent.match(EXPRESSAO.tarefa.intermediaria)) tarefa.style.color='#90F'
	})
}

async function pjeLegadoDetalhesDoProcesso(){
	if(!JANELA.includes('.jus.br/primeirograu/Processo/')) return
	sanitizar()

	function sanitizar(){
		if(!CONFIGURACAO?.pje?.pjeLegadoSanitizar) return
		desativarDestaques()
		irParaAbaAnexos()
		desativarAlertas()
		marcarTodosComoApreciados()
	}

	async function desativarAlertas(){
		let espera = 500
		let observador = new MutationObserver(() => {
			let observado = selecionar('input[value="Desativar"]')
			if(!observado) return
			if(observado) setTimeout(() =>	clicar(observado),espera += 1000)
		})
		observador.observe(document.body,{childList:true,subtree:true,attributes:true,characterData:false})
	}

	function desativarDestaques(){
		let links = document.querySelectorAll('a')
		links.forEach(link => {
			if(link?.innerText?.includes('clique aqui')) clicar(link)
		})
	}

	function irParaAbaAnexos(){
		if(JANELA.includes('segundograu')) return
		if(!JANELA.includes('tab=documentoAnexoId')){
			clicar('#documentoAnexoId_lbl')
			return
		}
	}

	async function marcarTodosComoApreciados(){
		let desmarcar = await esperar('[title="Marcar todos como não apreciados"]',true,true)
		clicar(desmarcar)
		let marcar = await esperar('[title="Marcar todos como apreciados"]',true,true)
		clicar(marcar)
		let botao = await esperar('[value="Confirmar"]',true,true)
		clicar(botao)
	}
}