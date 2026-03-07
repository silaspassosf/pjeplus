window.addEventListener('load',programa)

async function programa(){
	let armazenamento = await browser.storage.local.get()
	CONFIGURACAO = armazenamento
	let editar = obterParametroDeUrl('editar')
	let posicao = selecionar('#posicao')
	let cor = selecionar('#cor')
	let rotulo = selecionar('#rotulo')
	let tipo = selecionar('#tipo')
	let prazo = selecionar('#prazo')
	let responsavel = selecionar('#responsavel')
	let destacar = selecionar('#destacar')
	let gravar = selecionar('#gravar')
	let observacao = selecionar('#observacao')
	let comentario = selecionar('#comentario')
	definicoesGlobais()
	criarCabecalhoDePaginaDaExtensao()
	criarRodapeDePaginaDaExtensao()
	limitarQuantidadeDePosicoes()
	editarConfiguracoes()
	importarConfiguracoes()
	exportarConfiguracoes()
	selecionar('#salvar').addEventListener('click',evento => {
		evento.preventDefault()
		salvarConfiguracoes()
	})
	function limitarQuantidadeDePosicoes(){
		let quantidade = CONFIGURACAO?.gigs?.length || 0
		if(!posicao) return
		posicao.max = (quantidade + 1)
	}

	function editarConfiguracoes(){
		if(!editar) return
		let chave = (Number(editar) - 1)
		let autogigs = CONFIGURACAO.gigs[chave]
		posicao.value = editar
		cor.value = autogigs.f
		rotulo.value = autogigs.e
		tipo.value = autogigs.t
		prazo.value = autogigs.p
		responsavel.value = autogigs.r
		destacar.checked = autogigs.d
		gravar.checked = autogigs.g
		observacao.value = autogigs.o
		comentario.value = autogigs.c
	}

	async function salvarConfiguracoes(){
		let gigs = CONFIGURACAO.gigs
		let autogigs = {}
		autogigs.f = cor.value || '#000000'
		autogigs.e = rotulo?.value?.trim() || ''
		autogigs.t = tipo?.value?.trim() || 'Prazo'
		autogigs.p = prazo?.value?.trim() || ''
		autogigs.r = responsavel?.value?.trim() || ''
		autogigs.d = destacar.checked || false
		autogigs.g = gravar.checked || false
		autogigs.o = observacao?.value?.trim() || ''
		autogigs.c = comentario?.value?.trim() || ''
		let posicaoAtual = posicao?.value?.trim() || 0
		let indice = Number(posicaoAtual) - 1
		if(editar) gigs.splice((Number(editar) - 1),1)
		gigs.splice(indice, 0, autogigs)
		browser.storage.local.set({gigs}).then(recarregar)
	}

	async function exportarConfiguracoes(){
		let exportar = selecionar('#exportar-configuracoes')
		if(!exportar) return
		let gigs = CONFIGURACAO?.gigs || ''
		if(!gigs) return
		let json = JSON.stringify(gigs)
		exportar.value = json
		exportar.addEventListener('click',() => {
			exportar.select()
			copiar(json)
		})
	}

	async function importarConfiguracoes(){
		let botao = selecionar('#importar')
		if(!botao) return
		botao.addEventListener('click',() => {
			let importar = selecionar('#importar-configuracoes')
			if(!importar) return
			let texto = importar.value || ''
			if(!texto) return
			let autogigs = JSON.parse(texto)
			let gigs = autogigs.concat(CONFIGURACAO.gigs)
			browser.storage.local.set({gigs}).then(recarregar)
		})
	}
}