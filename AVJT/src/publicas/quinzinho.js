function criarQuinzinhoInformativo(
	id = '',
	ancestral = '',
	texto = ''
){
	return criar('quinzinho',id,'',ancestral,'',texto,'QUINZINHO INFORMA')
}

function obterContexto(){
	if(JANELA.match(/processo[/]\d+[/]tarefa/i)){
		if(JANELA.includes('tarefa/545')) return 'pje-comunicacoes'
		if(JANELA.match(/processo[/]\d+[/]tarefa[/]\d+[/]registrar.transito.julgado/i)) return 'pje-tarefa-registrar-transito-julgado'
		return 'pje-tarefa'
	}
	return ''
}


async function pjePainelCriarMenuArrastavel() {

	let armazenamento = await browser.storage.local.get(['menuMovel'])
	let posicaoHorizontal = Number(armazenamento.menuMovel.h) || 0
	let posicaoVertical = Number(armazenamento.menuMovel.v) || 0
	let tela = criar('area-de-arrasto','quinzinho-area-de-arrasto')
	let menu = criar('menu-arrastavel','quinzinho-menu-arrastavel-base')
	let conteudo = criar('conteudo','quinzinho-menu-arrastavel-conteudo','',menu)
	let alternador = criar('alternador','quinzinho-alternador','',conteudo,'','','Quinzinho')

	if((posicaoHorizontal + posicaoVertical) > 0)
		posicionarMenu(posicaoHorizontal,posicaoVertical)

	tela.addEventListener(
		'dragover',
		evento => {
			evento.preventDefault()
			evento.dataTransfer.dropEffect = 'move'
			posicaoHorizontal = evento.clientX
			posicaoVertical = evento.clientY
		}
	)
	tela.addEventListener(
		'drop',
		evento => evento.preventDefault()
	)

	menu.draggable = true
	menu.addEventListener(
		'dragstart',
		() => {
			tela.style.display = 'flex'
		}
	)
	menu.addEventListener(
		'dragend',
		async () => {
			let horizontal = (posicaoHorizontal - 12)
			let vertical = (posicaoVertical - 12)
			tela.style.display = 'none'
			posicionarMenu(horizontal,vertical)
			definirDirecaoDoMenu()
			await browser.storage.local.set({menuMovel:{h:horizontal,v:vertical}})
		}
	)

	criarBotoes()

	let eventos = ['click','mouseenter']
	eventos.forEach(
		item => {
			alternador.addEventListener(
				item,
				() => {menu.classList.toggle('aberto')}
			)
		}
	)

	function criarBotoes(){

		let posicao = 0

		menuMovelCriarBotao('exe15','Consultar dado selecionado no Exe15',exe15DiligenciaConsultar)

		function menuMovelCriarBotao(
			id = '',
			titulo = '',
			aoClicar = ''
		){
			let botao = criarBotao('quinzinho-menu-arrastavel-botao-'+id,id,conteudo,'',titulo,aoClicar)
			botao.title = titulo
			botao.style = '--posicao:' + (++posicao) + ';--direcao:-1;'
			return botao
		}

	}

	function definirDirecaoDoMenu() {
		let posicaoVertical = parseInt(window.getComputedStyle(menu).top)
		let meiaAltura = parseInt(window.innerHeight / 2)
		let itens = todos('menu-arrastavel quinzinho-botao')
		let direcao = '1'
		if(posicaoVertical > meiaAltura) direcao = '-1'
		itens.forEach(item => item.style.setProperty('--direcao',direcao))
	}

	function posicionarMenu(posicaoHorizontal=0,posicaoVertical=0){
		menu.style.left = posicaoHorizontal + 'px'
		menu.style.top = posicaoVertical + 'px'
	}

}


async function obterSelecao(){
	let selecao = document.getSelection() || ''
	if(!selecao) return ''
	let conteudo = ''
	if(selecao && selecao.rangeCount > 0) conteudo = selecao?.getRangeAt(0) || ''
	if(!conteudo) return ''
	let retangulo = conteudo.getBoundingClientRect()
	let posicao = {}
	posicao.horizontal = Math.ceil(retangulo.left)
	posicao.vertical = Math.ceil(retangulo.top)
	let texto = selecao.toString() || ''
	if(!texto) return ''
	selecao = {}
	selecao.textoAparado = texto.trim()
	selecao.caracteres = contarCaracteres(texto)
	selecao.chassi = obterChassi(texto)
	selecao.cnpj = obterCNPJ(texto)
	selecao.contexto = obterContexto()
	selecao.cpf = obterCPF(texto)
	selecao.correiosObjeto = obterCorreiosObjeto(texto)
	selecao.data = obterData(texto)
	selecao.hora = obterHora(texto)
	selecao.documento = obterDocumento(texto)
	selecao.email = obterEmail(texto.replace(/(.*?mail[:]|[()<>{}]|\s|\t|\[|\])/gi,'').trim())
	selecao.letra = texto.match(/[A-Za-zÀ-ȕ]/)
	selecao.nomeCompleto = selecao.textoAparado.includes(' ')
	selecao.numero = numeros(texto)
	selecao.pjeNumeroDoProcessoParcial = obterNumeroDoProcessoParcial(texto)
	selecao.pjeNumeroDoProcessoCompleto = obterNumeroDoProcessoPadraoCNJ(texto)
	selecao.placa = obterPlacaDeVeiculoAutomotor(texto)
	selecao.valor = obterValorMonetario(texto)
	selecao.uri = encodeURI(selecao.textoAparado)
	return selecao
}
