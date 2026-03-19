/**
 * Monta um caminho absoluto para um arquivo de uma string com um caminho partindo do manifest.json:
 * @param {string}	arquivo
 */
function caminho(arquivo=''){

	if(!arquivo)
		return ''
	return browser.runtime.getURL(arquivo)

}


/**
 * Cria uma janela com os parâmetros determinados:
 * @param  {string}		url
 * @param  {string}		chave				Será usada para extrair configurações de ${CONFIGURACAO.janela[chave]}
 * @param  {integer}	largura
 * @param  {integer}	altura
 * @param  {integer}	horizontal
 * @param  {integer}	vertical
 * @param  {string} 	tipo				Ver https://developer.mozilla.org/en-US/docs/Mozilla/Add-ons/WebExtensions/API/windows/CreateType
 */
 function criarJanela(
	url,
	chave = 'nova',
	largura = 1200,
	altura = 900,
	horizontal = 0,
	vertical = 0,
	tipo = 'normal'
){

	relatar('Obtendo configurações...')
	let janela = CONFIGURACAO?.janela || {}

	MODO.relatar = true
	relatar('-> CONFIGURACAO.janela:',janela)

	relatar('Verificando se as configurações estão definiodas para a janela',chave)
	if(janela[chave]){

		relatar('Coniguração encontrada:',janela[chave])
		MODO.relatar = false
		let valor = janela[chave]

		if(valor?.largura)
			largura = valor.largura
		if(valor?.l)
			largura = valor.l

		if(valor?.altura)
			altura = valor.altura
		if(valor?.a)
			altura = valor.a

		if(valor?.horizontal)
			horizontal = valor.horizontal
		if(valor?.h)
			horizontal = valor.h

		if(valor?.vertical)
			vertical = valor.vertical
		if(valor?.v)
			vertical = valor.v

	}

	relatar('Definindo opções...')

	let opcoes = JSON.parse(
		`
		\{
			"url":		"${url}",
			"height":	${altura},
			"left":		${horizontal},
			"top":		${vertical},
			"width":	${largura},
			"type":		"${tipo}"
		\}
		`
	)

	relatar('Opções definidas:',opcoes)

	relatar('Criando janela:')
	browser.windows.create(opcoes)
	relatar('Janela criada!',chave)

}


function destacarJanela(
	separar = false,
	mensagem = '',
	largura = 1200,
	altura = 900,
	horizontal = 0,
	vertical = 0
){

	if(separar){
		if(!CONFIGURACAO?.janela?.nova){
			browser.runtime.sendMessage(
				{
					mensagem:mensagem,
					largura:largura,
					altura:altura,
					horizontal:horizontal,
					vertical:vertical
				}
			)
			CONFIGURACAO.janela.nova = true
		}
	}

}


function abrirPaginaOpcoesDaExtensao(){

	browser.runtime.openOptionsPage()

}


function abrirPaginaTermosDeUso(){

	criarJanela(
		caminho('navegador/termos/pagina.htm'),
		'',
		700,
		600,
		0,
		0,
		'detached_panel'
	)

}


function abrirPaginaConfiguracaoDoUsuario(){

	criarJanela(
		caminho('navegador/configuracoes/pagina.htm?instalacao=1'),
		'',
		700,
		400,
		0,
		0,
		'detached_panel'
	)

}


function abrirPaginaConfiguracoesJuizo(){

	criarJanela(
		caminho(LINK.google.planilhas + '/d/1yiFpchE501er1aAAsjGCSums9zhD1IoIO3vlWyWREhI'),
		'',
		700,
		900,
		0,
		0,
		'detached_panel'
	)

}


function abrirPaginaConfiguracaoJuizo(
	vara='',
	nome=''
){

	criarJanela(
		caminho('navegador/pje-juizo/pagina.htm?vara='+vara+'&nome='+nome),
		'',
		750,
		750,
		0,
		0,
		'panel'
	)

}


function definirIconeDaExtensaoPeloEstado(ativada){

	let navegador = browser.browserAction

	if(
		ativada != true
		&&
		ativada != false
	){
		ativada = false
		browser.storage.local.set({ativada:ativada})
	}

	if(ativada) navegador.setIcon({path:'/imagens/icones/extensao/ativo.svg'})
	else navegador.setIcon({path:'/imagens/icones/extensao/inativo.svg'})

}


function definirEstadoDaExtensao(){

	EXTENSAO.ativador = selecionar('#ativador')
	if(!EXTENSAO.ativador)
		return

	EXTENSAO.ativador.addEventListener('change',salvarEstadoDaExtensao)

	browser.storage.local.get(
		'ativada',
		armazenamento => {
			EXTENSAO.ativador.checked = armazenamento.ativada
		}
	)

	function salvarEstadoDaExtensao(){

		let ativado = EXTENSAO.ativador.checked || false
		browser.storage.local.set({ativada:ativado})
		definirIconeDaExtensaoPeloEstado(ativado)

	}

}


function recarregar(){

	relatar('Recarregando a extensão...')
	browser.runtime.reload()

}


function obterConfiguracoesDaExtensao(){

	document.querySelectorAll('configuracoes').forEach(
		configuracoes => {

			let destino = definirDestinoDasConfiguracoes(configuracoes)

			configuracoes.querySelectorAll('input,select,textarea').forEach(
				configuracao => {
					let chave = configuracao.className
					if(!chave || chave.includes('exportar') || chave.includes('importar')) return
					let dados = CONFIGURACAO[destino]
					let dado = dados[chave]
					let tag = configuracao.tagName
					let tipo = configuracao.type
					let valor = configuracao.value
					if(tag.includes('SELECT')) configuracao.value = dado || ''
					if(tag.includes('TEXTAREA')) configuracao.value = dado || ''
					if(tipo === 'checkbox') configuracao.checked = dado || false
					if(tipo === 'email') configuracao.value = dado || ('@' + obterDominioTribunal()) || valor || ''
					if(tipo === 'number') configuracao.value = dado || valor || 0
					if(tipo === 'text') configuracao.value = dado || valor || ''
					if(chave === 'fase') configuracao.value = dado || valor || 'TODAS'
				}
			)
		}
	)

}


function salvarConfiguracoesDaExtensao(){

	setTimeout(salvar,50)

	function salvar(){
		console.debug('CONFIGURACAO',CONFIGURACAO)


		document.querySelectorAll('configuracoes').forEach(
			configuracoes => {

				let destino = definirDestinoDasConfiguracoes(configuracoes)
				let dados = CONFIGURACAO[destino]

				configuracoes.querySelectorAll('input,select,textarea').forEach(
					configuracao => {
						let chave = configuracao.className || ''
						if(!chave || chave.includes('exportar') || chave.includes('importar')) return
						let tag = configuracao.tagName
						let tipo = configuracao.type
						let valor = configuracao.value
						let marcado = configuracao.checked
						if(tag.includes('SELECT'))	dados[chave] = valor || ''
						if(tag.includes('TEXTAREA')) dados[chave] = valor || ''
						if(tipo === 'checkbox') dados[chave] = marcado || false
						if(tipo === 'number') dados[chave] = valor || 0
						if(tipo === 'email') dados[chave] = valor.trim() || ''
						if(tipo === 'text') dados[chave] = valor.trim() || ''

					}
				)

				browser.storage.local.set({[destino]:dados})

			}
		)

	}

}


function definirDestinoDasConfiguracoes(configuracoes){

	let destino = configuracoes.className || ''
	if(!destino)
		return

	if(CONFIGURACAO[destino] == undefined)
		CONFIGURACAO[destino] = {}

	return destino

}


/**
 * REMOVE CHAVES ESPECÍFICAS DO ${browser.storage.local}, QUE ESTEJAM PRESENTES NA GLOBAL ${CONFIGURACAO}:
 * @param {Array}	chaves
 */
 async function removerChavesDaMemoria(chaves = []){

	chaves.forEach(
		chave => {
			if(chave in CONFIGURACAO)
				browser.storage.local.remove(chave).then(
					() => aoFuncionar(chave),
					aoFalhar
				)
		}
	)

	function aoFuncionar(chave){
		relatar('Chave removida: ',chave)
	}

	function aoFalhar(erro){
		relatar('Erro:',erro)
	}

}


async function abrirPaginaListaDeProcessosPorTarefa(
	tarefa='',
	diagnosticar=false
){
	let sessao = await pjeApiVerificarSessaoAtiva()
	if(!sessao) return
	let	lista = new Lista
	lista.tarefaNome = tarefa
	lista.diagnosticar = diagnosticar
	await lista.processosPorTarefa()
	await browser.storage.local.set({lista})
	criarJanela(LINK.extensao.lista,'lista')
}


async function abrirPaginaListaDeProcessosPorTarefaDesde(
	titulo='',
	tarefa='',
	desde='',
	diagnosticar=false
){
	let sessao = await pjeApiVerificarSessaoAtiva()
	if(!sessao) return
	let	lista = new Lista
	lista.desde = desde
	lista.titulo = titulo
	lista.tarefaNome = tarefa
	lista.diagnosticar = diagnosticar
	lista.numeros = true
	await lista.processosPorTarefa()
	await browser.storage.local.set({lista})
	criarJanela(LINK.extensao.lista,'lista')
}


async function abrirPaginaListaDeProcessosDoPainelDePericia(
	tarefa='',
	diagnosticar=false
){
	let sessao = await pjeApiVerificarSessaoAtiva()
	if(!sessao) return
	let	lista = new Lista
	lista.tarefaNome = tarefa
	lista.diagnosticar = diagnosticar
	await lista.processosPainelPericia()
	await browser.storage.local.set({lista})
	criarJanela(LINK.extensao.lista,'lista')
}




async function abrirPaginaListaDeProcessosParaRelatorio(
	titulo='',
	processos=''
){
	let	lista = new Lista
	lista.processos = processos
	lista.titulo = titulo
	await browser.storage.local.set({lista})
	criarJanela(LINK.extensao.lista,'lista')
}


async function janelaObterDimensoes(nome=''){
	let janela = CONFIGURACAO?.janela || {}
	let dimensao = janela[nome] || {}
	let altura = dimensao.a || 900
	let largura = dimensao.l || 1600
	let horizontal = dimensao.h || 0
	let vertical = dimensao.v || 0
	let dimensoes = {a:altura,l:largura,h:horizontal,v:vertical}
	return dimensoes
}


async function janelaDefinirDimensoes(chave=''){

	let botao = selecionar('.dimensoes')

	botao.addEventListener(
		'click',
		() => {
			botao.classList.add('encolher-crescer')
			setTimeout(
				() => botao.classList.remove('encolher-crescer'),
				1001
			)
			definirDimensoes(chave)
		}
	)

	async function definirDimensoes(){
		let janela = CONFIGURACAO?.janela || {}
		let altura = window.outerHeight || 900
		let largura = window.outerWidth || 1600
		let horizontal = window.screenLeft || 0
		let vertical = window.screenTop || 0
		let dimensoes = {a:altura,l:largura,h:horizontal,v:vertical}
		janela[chave] = dimensoes
		await browser.storage.local.set({janela})
	}

}


async function janelaImprimir(){

	let botao = selecionar('.imprimir')

	botao.addEventListener(
		'click',
		() => window.print()
	)

}