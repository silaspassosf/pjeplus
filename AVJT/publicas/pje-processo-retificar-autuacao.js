async function pjeOtimizarPaginaRetificarAutuacao(){
	let contexto = pjeObterContexto()
	if(!contexto.includes('pje-retificar')) return
	let inserir = obterParametroDeUrl('inserir')
	let nome = obterParametroDeUrl('nome')
	aoAbrir()

	async function aoAbrir(){
		await esperar('[aria-label="Classe judicial"]')
		retificarParte()
		if(!inserir) return
		inserirMinisterioPublicoDoTrabalho()
	}

	async function inserirMinisterioPublicoDoTrabalho(){
		await esperar('[mattooltip="Inativar parte"]',true,true)
		await ativarAbaPartes()
		let botao = await esperar('[name="Outros participantes"] [mattooltip="Adicionar parte ao processo"]',true,true)
		clicar(botao)
		let participacao = await esperar('[aria-label="Tipo de participação"]',true,true)
		await aguardar(500)
		clicar(participacao)
		await pjeSelecionarOpcaoPorTexto('CUSTOS LEGIS')
		let mpt = await esperar('pje-selecao-parte-principal [aria-posinset="4"]',true,true)
		await aguardar(500)
		clicar(mpt)
		let adicionar = await esperar('[mattooltip="Selecionar"]')
		clicar(adicionar)
	}

	async function ativarAbaPartes(){
		await aguardar(500)
		let abas = document.querySelectorAll('mat-step-header')
		if(vazio(abas))
			return
		clicar(abas[2])
	}

	async function retificarParte(){
		if(!nome) return
		await ativarAbaPartes()
		executarAposCarregamentoDeTexto(minusculas(nome),ativarAbaPartes)
		esperar('[aria-label="Selecionar"]').then(editarParte)

		async function executarAposCarregamentoDeTexto(texto,funcao){
			let observador = new MutationObserver(() => {
				if(document.body.textContent.includes(texto)){
					observador.disconnect()
					funcao()
				}
			})
			observador.observe(document.body,{childList:true,subtree:true})
		}

		async function editarParte(){
			setTimeout(() => {
				let pessoa = [...document.querySelectorAll("tr")].filter(linha => linha.textContent.includes(minusculas(nome)))[0] || ''
				let editar = pessoa.querySelector('[aria-label="Selecionar"]') || ''
				if(!editar) return
				clicar(editar)
				esperar('mat-panel-title').then(selecionarEnderecos)
				esperar('[aria-label="Usar esse endereço no processo"]').then(selecionarEnderecoDesconhecido)
			},250)
		}
	}

	function selecionarEnderecos(){
		setTimeout(() => {
			let paineis = document.querySelectorAll('mat-panel-title')
			if(vazio(paineis)) return
			clicar(paineis[2])
		},250)
	}

	function selecionarEnderecoDesconhecido(){
		setTimeout(() => clicar('pje-data-table [aria-label="Usar esse endereço no processo"]'),500)
		setTimeout(pjeAcionarBotaoConfirmar,1000)
	}

	function pjeAcionarBotaoConfirmar(){
		setTimeout(confirmar,225)
		function confirmar(){
			let botao = selecionar('ng-component button')
			if(!botao) return
			clicar(botao)
		}
	}
}