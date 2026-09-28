async function pjeOtimizarPaginaEditor(){
	//pjeEditorFocarAoCarregar()
	fecharMensagensDeGravacao()
	fecharMensagensSobreImagens()
	fecharMensagensDeConfirmacao()
	alterarTextoDoEditor()
	inserirLinkNoTextoDoDocumento()
	alterarPrazoPeloTextoDoDocumento()
	lancarMovimentosRecursoRecebido()
	esperar('tree-node',true,false,true).then(otimizarLayout())
	esperar('Meus Modelos',true,false,true).then(() => {
		expandirArvoreDeDocumentos()
		alterarDescricaoDoDocumento().then(escolherModelos)
	})

	function inserirLinkNoTextoDoDocumento(){
		esperar('.area-conteudo mark',true).then(async elemento => {
			let link = await obterLinkDaMemoria()
			if(link) pjeEditorInserirLink(elemento,link)
		})
	}

	async function pjeEditorInserirLink(elemento,link){
		if(!CONFIGURACAO?.pjeAssistentesDocumentosNotificacoes?.inserirLink) return
		if(minusculas(elemento.innerText).includes('link')) elemento.innerText = link
	}

	async function obterLinkDaMemoria(){
		let texto = await navigator.clipboard.readText()
		if(!texto) return ''
		let link = texto.match(/http.*/) || ''
		if(!link) return ''
		return link.join().trim() || ''
	}

	function otimizarLayout(){
		if(!CONFIGURACAO?.pjeAssistentesDocumentosNotificacoes?.otimizarLayout) return
		estilizar('',
		`
		[pjeassinatura]{
			bottom:unset !important;
			top:20% !important;
			z-index:unset !important;
		}
		pje-duas-colunas .handler {
			width:5px !important;
			border-left:1px dotted #666 !important;
			margin-left:5px;
		}
		.arvore-container{
			font-size:12.5px !important;
		}
		.node-content-wrapper{
			padding:1px 0px !important;
		}
		.tree-children{
			padding-left:5px !important;
		}`)
	}

	function alterarPrazoPeloTextoDoDocumento(){
		if(!CONFIGURACAO?.pjeAssistentesDocumentosNotificacoes?.alterarPrazo) return
		esperar('pje-intimacao-automatica input[type="text"]',true).then(() => {
			setTimeout(desativarEnviarParaPec,1000)
			let texto = obterTextoDoEditor()
			let prazo = obterPrazoEmDias(texto)
			pjeEditorIntimacoesAlterarPrazo(prazo)
		})
	}

	async function lancarMovimentosRecursoRecebido(){
		
		if(!CONFIGURACAO?.pjeAssistentesDocumentosNotificacoes?.movimentosRecurso) return
		if(JANELA.includes('detalhe')) return
		await esperar('pje-lancador-de-movimentos input[type="search"]',true,true)
		let RECURSOS = PROCESSO.recursos || []
		console.debug('RECURSOS',RECURSOS)
		setTimeout(lancar,500)

		async function lancar(){
			if(vazio(RECURSOS)) return
			let texto = minusculas(obterTextoDoEditor())
			//console.debug('texto',texto)
			let RECURSO = texto.includes('recurso adesivo') || texto.includes('recurso ordinário')
			if(!RECURSO) return
			console.debug('RECURSO',RECURSO)
			let movimento = [...document.querySelectorAll("pje-movimento")].filter(movimento => movimento.innerText.includes('suspensivo'))[0] || ''
			if(!movimento) return
			let recebido = movimento.querySelector('input') || ''
			if(!recebido) return
			let POLOS = PROCESSO?.partes || ''
			console.debug('POLOS',POLOS)
			let REPRESENTANTES = obterRepresentantes()
			console.debug('REPRESENTANTES',REPRESENTANTES)
			
			clicar(recebido)

			function obterRepresentantes(){
				//let representantes = {}
				let representantes = []
				for(let polo in POLOS){
	
					if(POLOS[polo][0].hasOwnProperty('representantes')){
						let parte = POLOS[polo][0]
						console.log(parte.nome)
						for(let representante of POLOS[polo][0].representantes){
							representante.representado = parte.nome
							representantes.push(representante)
							console.log(representante)
					
						}
					}
					
					
				}
				
				return representantes
				
			}

			for(let recurso of RECURSOS){
				let tipo = ''
				let titulo = recurso.tipo || ''

				console.debug('recurso',recurso)
				let responsavel = recurso?.nomeSignatario || recurso?.nomeResponsavel || ''
				if(!responsavel) return
				console.debug('responsavel',responsavel)
				
				let pessoa = REPRESENTANTES.filter(p => p.nome === responsavel)[0] || ''
				if(pessoa) pessoa = pessoa?.representado || ''
				console.debug('pessoa',pessoa)
				//console.debug('PARTES',PARTES)
				console.debug('tipo',tipo)
				console.debug('titulo',titulo)
				
				
				
				switch(true){
					case(titulo == 'Recurso Adesivo'):
						tipo = titulo + ' (63)'
						break
					case(titulo == 'Recurso Ordinário'):
						tipo = titulo + ' (69)'
						break
					default:
						return
				}
				await esperar('pje-complemento',true,true)
				let complementos = document.querySelectorAll('pje-complemento')
				if(vazio(complementos)) return
				for(let complemento of complementos){
					pjeRecursoSelecionarTipo(complemento,tipo)
					if(complemento.textContent.includes('Nome da parte')){
						clicar(complemento.getElementsByTagName('mat-select')[0])
						await esperar('mat-option',true,true)
						let partes = document.querySelectorAll('mat-option')
						let parte = [...partes].filter(p => p.textContent.includes(pessoa))[0] || ''
						clicar(parte)
					}
				}
			}
			gravar()

			async function gravar(){
				setTimeout(() => clicar('[aria-label="Gravar os movimentos a serem lançados"]'),500)
			}

			function pjeRecursoSelecionarTipo(complemento,tipo){
				if(complemento.textContent.includes('Nome do recurso')){
				clicar(complemento.getElementsByTagName('mat-select')[0])
				let recurso = [...document.querySelectorAll("mat-option")].filter(e => e.innerText.includes(tipo))[0] || ''
				if(recurso) clicar(recurso)
				}
			}
		}
	}

	function fecharMensagensSobreImagens(){
		if(!CONFIGURACAO?.pjeAssistentesDocumentosNotificacoes?.fecharMensagensSobreImagens) return
		esperar('mat-dialog-container',false,false,false,false).then(async elemento => {
			if(!elemento.textContent.includes('Se documentos com imagens forem publicados, as imagens não aparecerão')) return
			let botao = elemento.querySelector('button') || ''
			if(botao) clicar(botao)
		})
	}

	function fecharMensagensDeGravacao(){
		if(!CONFIGURACAO?.pjeAssistentesDocumentosNotificacoes?.fecharMensagensAcaoConcluida) return
		let observador = new MutationObserver(() => {
			let observado = selecionar('snack-bar-container.success button')
			if(!observado) return
			setTimeout(() => clicar(observado),100)
		})
		observador.observe(document.body,{subtree:true,childList:true,attributes:true,characterData:false})
	}

	function fecharMensagensDeConfirmacao(){
		if(!CONFIGURACAO?.pjeAssistentesDocumentosNotificacoes?.fecharMensagensDeConfirmacao) return
		let observador = new MutationObserver(() => {
			let observado = selecionar('mat-dialog-container')
			if(!observado) return
			if(!observado.textContent.includes('Lançador de movimentos')) return
			let botao = selecionar('mat-dialog-container button')
			setTimeout(() =>	clicar(botao),100)
			setTimeout(() =>	clicar('[mattablabelwrapper]'),500)
		})
		observador.observe(document.body,{subtree:true,childList:true,attributes:true,characterData:false})
	}

	async function desativarEnviarParaPec(){
		if(!CONFIGURACAO?.pjeAssistentesDocumentosNotificacoes?.desmarcarPec) return
		let caixa = await esperar('input[aria-label="Enviar para PEC"]',true,true)
		let ativada = caixa?.getAttribute('aria-checked')
		if(ativada.includes('true')){
			clicar(caixa)
			clicar('[aria-label="Gravar a intimação/notificação"]')
		}
	}

	function obterTextoDoEditor(){
		let editor = selecionar('.conteudo')
		if(!editor) return ''
		let texto = editor.textContent || ''
		return texto
	}

	function alterarTextoDoEditor(){
		esperar('.area-conteudo mark',true).then(async elemento => {
			let texto = obterTextoDoEditor()
			let editor = selecionar('.conteudo')
			if(!editor) return ''
			let sobrestamentoAcordo = texto.includes('Nos termos do Comunicado CR 2/2023*, sobreste-se o feito até a data de')
			if(sobrestamentoAcordo) elemento.innerText = PROCESSO.acordo.vencimento
		})
	}

	function obterPrazoEmDias(texto=''){
		let titulo = pjeEditorObterTitulo()
		let quantidade = '5'
		let prazo = texto.match(/prazo de \d{1,3} (dia|hora)(s)/i) || ''
		let alvara = texto.includes('ag4106sp01@caixa.gov.br')
		let sobrestamentoAcordo = texto.includes('Nos termos do Comunicado CR 2/2023*, sobreste-se o feito até a data de')
		let apolice = texto.includes('Libero todas as apólices de seguro garantia')
		let razoesFinais = texto.includes('Nos 5 dias subsequentes ao prazo acima assinalado')
		let liquidacao = texto.includes('Após, venham conclusos para a homologação dos cálculos')
		let sentenca = titulo.includes('Elaborar sentença')
		let tutela = titulo.includes('Pedido de Tutela')
		if(alvara || apolice || sobrestamentoAcordo || tutela) return 'zero'
		if(sentenca) return '8'
		if(razoesFinais) return '10'
		if(liquidacao) return '21'
		if(!prazo && !alvara) return quantidade
		prazo = minusculas(prazo[0])
		quantidade = numeros(prazo)
		if(prazo.includes('hora')) quantidade = quantidade / 24
		return quantidade
	}



	async function expandirArvoreDeDocumentos(){
		if(!CONFIGURACAO?.pjeAssistentesDocumentosNotificacoes?.expandirModelos) return
		clicar('Meus Modelos',true)
		let titulo = pjeEditorObterTitulo()
		switch(true){
			case(titulo.includes('Elaborar sentença')):
				clicar('Sentenças',true)
				if(titulo.includes('Homologação de Acordo')) preencher('[aria-label="Descrição"]','Homologação de Acordo')
				if(titulo.includes('Embargos de Declaração')) preencher('[aria-label="Descrição"]','Embargos de Declaração')
				break
			case(titulo.includes('Elaborar despacho')):
				clicar('Despachos',true)
				if(PROCESSO?.labelFaseProcessual == 'Liquidação'){
					clicar('04. Liquidação',true)
					return
				}
				if(PROCESSO?.chips?.includes('Novo Processo')) clicar('01. Triagem Inicial',true)
				if(PROCESSO?.instrucao){
					if(vazio(PROCESSO?.sentencas)) clicar('02. Instrução',true)
				}
				if(!vazio(PROCESSO?.sentencas)) clicar('03. Pós-Sentença',true)
				break
			case(titulo.includes('Elaborar decisão')):
				clicar('Decisões',true)
				if(titulo.includes('Pedido de Tutela')) preencher('[aria-label="Descrição"]','Pedido de Antecipação de Tutela')
				if(PROCESSO?.labelFaseProcessual == 'Liquidação'){
					clicar('04. Liquidação',true)
				}
				clicar('Processamento de Recursos',true)
				selecionarMovimentos()
				break
			case(titulo.includes('Anexar Documentos')):
				clicar('Certidões',true)
				break
			default:
				clicar('Audiências',true)
				clicar('E-CARTA TRT 15 1.3',true)
				clicar('Notificações',true)
				return
		}
	}

	async function selecionarMovimentos(){
		await esperar('.mat-tab-header-pagination-controls-enabled .mat-tab-header-pagination',true,true)
		setTimeout(() => clicar('.mat-tab-labels div:nth-child(2)'),500)
	}

	function escolherModelos(){
		let modelo = {
			replica:"002. Apresentar Réplica",
			razoesFinais:"002. Réplica Juntada; Especificar Provas ou Apresentar Razões Finais",
			conhecimentoLaudoApresentado:"003 - Perícia - Laudo Juntado. Apresentação de Quesitos Complementares e Enventuais Impugnações",
			conhecimentoPericiaConcluida:"003 - Perícia Concluída - Sem Audiência. Apresentar Razões Finais ou Especificar Provas a Produzir",
			liquidacaoLaudoApresentado:"003. Manifestação Sobre o Laudo Pericial",
		}

		let ultimoDocumento = PROCESSO?.ultimoDocumento || ''
		if(!ultimoDocumento) return
		let tipo = ultimoDocumento?.tipo || ''
		if(!tipo) return
		if(tipo.includes('Contestação')) clicar(modelo.replica,true)
		if(tipo.includes('Réplica')) clicar(modelo.razoesFinais,true)
		if(tipo.includes('Apresentação de Laudo Pericial')){
			if(PROCESSO?.labelFaseProcessual == 'Liquidação') clicar(modelo.liquidacaoLaudoApresentado,true)
			else clicar(modelo.conhecimentoLaudoApresentado,true)
		}
		if(tipo.includes('Apresentação de Esclarecimentos ao Laudo Pericial')){
			if(PROCESSO?.labelFaseProcessual == 'Liquidação') return
			clicar(modelo.conhecimentoPericiaConcluida,true)
		}
	}

	async function alterarDescricaoDoDocumento(){
		if(!CONFIGURACAO?.pjeAssistentesDocumentosNotificacoes?.descrever) return
		let arvore = await esperar('tree-node',true)
		if(!arvore) return
		arvore.addEventListener('click',evento => {
			let elemento = evento.target.parentElement.parentElement || ''
			if(!elemento) return
			let texto = elemento.textContent || ''
			if(!texto) return
			texto = texto.replace(/^(.*?[.])/g,'').trim()
			preencher('[aria-label="Descrição"]',texto)
		})
	}
}

function pjeEditorObterTitulo(){
	let titulo = selecionar('h1') || ''
	if(titulo) titulo = titulo?.textContent
	return titulo
}

async function pjeEditorIntimacoesAlterarPrazo(prazo='5'){
	if(!prazo) return
	if(prazo.includes('zero')) prazo = '0'
	let campos = document.querySelectorAll('pje-intimacao-automatica input[type="text"]')
	campos.forEach(campo => preencher(campo,prazo))
	await aguardar(250)
	clicar('[aria-label="Gravar a intimação/notificação"]')
}

async function pjeEditorFocarAoCarregar(texto=''){
	let corpo = await esperar('.corpo',true)
	focar(corpo.parentElement)
	/*
	corpo.parentElement.addEventListener('keydown',evento => {
		if(evento.code.includes('Space')){
			evento.preventDefault()
			inserirEspaco()
		}
	})
	*/
	if(texto) corpo.innerText = texto
	return corpo

	async	function inserirEspaco(){
    if(window.getSelection && window.getSelection().getRangeAt){
			let range = window.getSelection().getRangeAt(0)
			let node = range.createContextualFragment('&nbsp;')
			range.insertNode(node)
    }
	}
}