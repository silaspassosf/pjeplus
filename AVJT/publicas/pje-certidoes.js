function pjeCertidaoCriarBotoes(){
	let painel = selecionar('#avjt-painel-superior-corpo')
	let configuracoes = selecionar('#avjt-painel-superior-controles')
	criarTitulo('titulo-certidao','','Certidões Automáticas',painel,configuracoes.previousElementSibling)
	let botoes = criar('botoes','avjt-painel-superior-botoes-certidoes','',painel,configuracoes.previousElementSibling)
	criarBotaoAdicionar()
	CONFIGURACAO.certidoes.forEach((botao,indice) => {criarBotaoAutoCertidao(indice,botao.e,botao.f,botao.t,botao.d,botao.p,botao.s,botao.c,botao.a)})

	function 	criarBotaoAdicionar(){
		criarBotao('avjt-certidao-adicionar','botao-automacao',configuracoes,'Adicionar Botão de Certidão Automática','',() => abrirPagina(caminho('navegador/pje-certidoes/pagina.htm'),'','','',''))
	}

	function criarBotaoAutoCertidao(
		indice = '',
		rotulo = '',
		cor = '#000',
		tipo = '',
		descricao = '',
		pdf = false,
		sigiloso = false,
		certidao = '',
		assinar = false
	){
		let posicao = Number(indice) + 1
		let botao = criarBotao('botao-automacao-certidao'+posicao,'botao-automacao',botoes,posicao+'. '+rotulo)
		botao.style = 'background:linear-gradient(to bottom,rgba(0,0,0,0.1) 0%,rgba(0,0,0,0.3) 100%),'+cor+';'
		botao.title = obterTituloDoBotao()
		botao.addEventListener('click',evento => {
			evento.stopPropagation()
			let certificar = pjeCertificar(descricao,tipo,certidao,pdf,sigiloso,assinar)
			pjeAbrirAnexar(certificar)
		})
		botao.addEventListener('contextmenu',elemento => {
			elemento.preventDefault()
			criarMenu(elemento)
		})

		function obterTituloDoBotao(){
			let titulo = tipo + '\n'
			if(descricao) titulo += 'Descrição: ' + descricao  + '\n'
			if(certidao) titulo += 'Certidão: ' + certidao
			return titulo
		}

		function criarMenu(referencia){
			referencia.preventDefault()
			let localizacao = referencia.target.getBoundingClientRect()
			let menu = criar('menu-de-contexto','avjt-certidoes-menu-de-contexto')
			menu.style.left = (localizacao.left + 25) + 'px'
			menu.style.top = (localizacao.top + 25) + 'px'
			menu.addEventListener('click',evento => evento.stopPropagation())
			let botaoEditar = criarBotao('menu-de-contexto-botao-editar','',menu,'EDITAR')
			let botaoExcluir = criarBotao('menu-de-contexto-botao-excluir','',menu,'EXCLUIR')
			let botaoFechar = criarBotao('menu-de-contexto-botao-fechar','',menu,'FECHAR')
			let posicao = (Number(numeros(referencia.target.id))) || 0
			botaoEditar.addEventListener('click',() => abrirPagina(caminho('navegador/pje-certidoes/pagina.htm?editar='+posicao),'','','',''))
			botaoExcluir.addEventListener('click',() => {
				let certidoes = CONFIGURACAO?.certidoes || ''
				if(!certidoes) return
				certidoes.splice((posicao - 1),1)
				browser.storage.local.set({certidoes}).then(pjeCertidaoCriarBotoes)
				pjePainelSuperiorMenuDeContextoFechar()
			})
			botaoFechar.addEventListener('click',pjePainelSuperiorMenuDeContextoFechar)
		}
	}
}