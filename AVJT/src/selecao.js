async function assistenteDeSelecao(){

	document.addEventListener('selectionchange',aoSelecionar)

	async function aoSelecionar(){
		let selecao = document.getSelection() || ''
		if(!selecao) return
		let conteudo = ''
		if(selecao && selecao.rangeCount > 0) conteudo = selecao?.getRangeAt(0)
		if(!conteudo) return

		let dimensao = conteudo.getBoundingClientRect()
		dimensao.topo			= (dimensao.top + dimensao.height)+'px'
		dimensao.esquerda	= dimensao.left+'px'
		dimensao.largura	= dimensao.width || 0


		let texto = selecao.toString() || ''
		if(!texto){
			fecharMenu()
			return
		}
		let textoAparado = texto.trim()
		let caracteres = contarCaracteres(texto)
		let cnpj = obterCNPJ(texto)
		let cpf = obterCPF(texto)
		let documento = obterDocumento(texto)
		let pjeNumeroDoProcessoParcial = obterNumeroDoProcessoParcial(texto)
		let pjeNumeroDoProcessoCompleto = obterNumeroDoProcessoPadraoCNJ(texto)
		let uri = encodeURI(textoAparado)

		let menu = criarMenu()
				
		if(documento || pjeNumeroDoProcessoCompleto){
			criarBotao('exe15-consultar','','Consultar dado selecionado no Exe15',() => exe15DiligenciaConsultar(pjeNumeroDoProcessoCompleto,documento))
		}


		function exe15DiligenciaConsultar(processo,documento){
			let url = encodeURI(LINK.tribunal.exe15.diligencias+'?processo='+processo+'&documento='+documento)
			abrirPagina(url)
		}

		function criarMenu(){
			let elemento = criar('quinzinho-assistente-de-selecao','quinzinho-assistente-de-selecao')
			elemento.style = `left:${dimensao.esquerda};top:${dimensao.topo};opacity:1`
			elemento.addEventListener('click',fecharMenu)
			return elemento
		}

		function criarBotao(
			id = '',
			classe = '',
			titulo = '',
			aoClicar = ''
		){
			let botao = criar('botao',id,'link',menu)
			if(id){
				botao.id = id
				botao.classList.add(id)
			}
			if(classe) botao.classList.add(classe)
			if(titulo) botao.setAttribute('aria-label',titulo)
			if(aoClicar) botao.addEventListener('click',aoClicar)
			botao.addEventListener('click',evento => evento.stopPropagation())
			if(id.includes('copiar')){
				botao.addEventListener('click',() => {
					botao.classList.toggle('copiado')
					setTimeout(
						() => botao.classList.toggle('copiado'),
						1000
					)
				})
			}
		}

		function fecharMenu(){
			remover('quinzinho-assistente-de-selecao')
		}
	}
}