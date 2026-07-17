window.addEventListener('load',programa)

async function programa(){
	let armazenamento = await browser.storage.local.get()
	CONFIGURACAO = armazenamento
	let editar = obterParametroDeUrl('editar')
	let posicao = selecionar('#posicao')
	let cor = selecionar('#cor')
	let rotulo = selecionar('#rotulo')
	let tipo = selecionar('#tipo')
	let descricao = selecionar('#descricao')
	let pdf = selecionar('#pdf')
	let sigiloso = selecionar('#sigiloso')
	let assinar = selecionar('#assinar')
	let certidao = selecionar('#certidao')
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
		let quantidade = CONFIGURACAO?.certidoes?.length || 0
		if(!posicao) return
		posicao.max = (quantidade + 1)
	}

	function editarConfiguracoes(){
		if(!editar) return
		let chave = (Number(editar) - 1)
		let autocertidoes = CONFIGURACAO.certidoes[chave]
		posicao.value = editar
		cor.value = autocertidoes.f
		rotulo.value = autocertidoes.e
		tipo.value = autocertidoes.t
		descricao.value = autocertidoes.d
		pdf.checked = autocertidoes.p
		sigiloso.checked = autocertidoes.s
		assinar.checked = autocertidoes.a
		certidao.value = autocertidoes.c
	}

	async function salvarConfiguracoes(){
		let certidoes = CONFIGURACAO.certidoes
		let autocertidoes = {}
		autocertidoes.a = assinar.checked || false
		autocertidoes.c = certidao?.value?.trim() || ''
		autocertidoes.d = descricao?.value?.trim() || 'Prazo'
		autocertidoes.e = rotulo?.value?.trim() || ''
		autocertidoes.f = cor.value || '#000000'
		autocertidoes.p = pdf.checked || false
		autocertidoes.s = sigiloso.checked || false
		autocertidoes.t = tipo?.value?.trim() || 'Prazo'
		let posicaoAtual = posicao?.value?.trim() || 0
		let indice = Number(posicaoAtual) - 1
		if(editar){
			certidoes.splice((Number(editar) - 1),1)
		}
		certidoes.splice(indice, 0, autocertidoes)
		browser.storage.local.set({certidoes}).then(recarregar)
	}

	async function exportarConfiguracoes(){
		let exportar = selecionar('#exportar-configuracoes')
		if(!exportar) return
		let certidoes = CONFIGURACAO?.certidoes || ''
		if(!certidoes) return
		let json = JSON.stringify(certidoes)
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
			let autocertidoes = JSON.parse(texto)
			let certidoes = autocertidoes.concat(CONFIGURACAO.certidoes)
			browser.storage.local.set({certidoes}).then(recarregar)
		})
	}
}