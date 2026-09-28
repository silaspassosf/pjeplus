/**
 * Monta um caminho absoluto para um arquivo de uma string com um caminho partindo do manifest.json:
 * @param {string}	arquivo
 */
function caminho(arquivo=''){
	if(!arquivo) return ''
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
	relatar('-> CONFIGURACAO.janela:',janela)
	relatar('Verificando se as configurações estão definiodas para a janela',chave)
	if(janela[chave]){
		relatar('Coniguração encontrada:',janela[chave])
		let valor = janela[chave]
		if(valor?.largura) largura = valor.largura
		if(valor?.l) largura = valor.l
		if(valor?.altura) altura = valor.altura
		if(valor?.a) altura = valor.a
		if(valor?.horizontal) horizontal = valor.horizontal
		if(valor?.h) horizontal = valor.h
		if(valor?.vertical) vertical = valor.vertical
		if(valor?.v) vertical = valor.v
	}
	relatar('Definindo opções...')
	let opcoes = JSON.parse(`\{"url":"${url}","height":${altura},"left":${horizontal},"top":${vertical},"width":${largura},"type":"${tipo}"\}`)
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
			browser.runtime.sendMessage({
				mensagem:mensagem,
				largura:largura,
				altura:altura,
				horizontal:horizontal,
				vertical:vertical
			})
			CONFIGURACAO.janela.nova = true
		}
	}
	esforcosPoupados(2,4)
}

function abrirPaginaOpcoesDaExtensao(){
	browser.runtime.openOptionsPage()
}

function abrirPaginaTermosDeUso(){
	criarJanela(caminho('navegador/termos/pagina.htm'),'',700,600,0,0,'detached_panel')
}

function abrirPaginaContribuir(){
	criarJanela(caminho('navegador/contribuir/pagina.htm'),'',700,600,0,0,'detached_panel')
}

function abrirPaginaContadorDeEsforcosRepetitivos(){
	criarJanela(caminho('navegador/esforcos/pagina.htm'),'',700,400,0,0,'detached_panel')
}

function abrirPaginaConfiguracaoDeLink(
	editar = '',
	descricao = ''
){
	criarJanela(caminho(`navegador/link/pagina.htm?editar=${editar}&descricao=${descricao}`),'',800,600,0,0,'detached_panel')
}

function abrirPaginaConfiguracaoDoTribunal(){
	criarJanela(caminho('navegador/tribunal/pagina.htm'),'',700,500,0,0,'detached_panel')
}

async function reiniciarContadorDeEsforcosRepetitivos(){
	await browser.storage.local.remove('esforcos')
	window.location.reload()
}

function definirIconeDaExtensaoPeloEstado(ativada){
	if(ativada != true && ativada != false){
		ativada = false
		browser.storage.local.set({ativada:ativada})
	}
	if(ativada) browser.browserAction.setIcon({path:'/imagens/icones/extensao/azul.svg'})
	else browser.browserAction.setIcon({path:'/imagens/icones/extensao/vermelho.svg'})
}

function definirEstadoDaExtensao(){
	EXTENSAO.ativador = selecionar('#ativador')
	if(!EXTENSAO.ativador) return
	EXTENSAO.ativador.addEventListener('change',salvarEstadoDaExtensao)
	browser.storage.local.get('ativada',armazenamento => {
		EXTENSAO.ativador.checked = armazenamento.ativada
	})

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
	document.querySelectorAll('configuracoes').forEach(configuracoes => {
		let destino = definirDestinoDasConfiguracoes(configuracoes)
		configuracoes.querySelectorAll('input,textarea').forEach(configuracao => {
			let chave = configuracao.className
			if(!chave) return
			if(chave === 'exportar' || chave === 'importar') return
			let dados = CONFIGURACAO[destino]
			if(configuracao.type === 'textarea') configuracao.value = dados[chave] || ''
			if(chave === 'assinatura') configuracao.value = dados[chave] || configuracoesDaExtensaoAssinatura() || ''
			if(chave === 'emailDocumentos' || chave === 'whatsapp') configuracao.value = dados[chave] || configuracoesDaExtensaoTextoPadraoEmailDocumentos() || ''
			if(configuracao.type === 'checkbox') configuracao.checked = dados[chave] || false
			if(configuracao.type === 'email') configuracao.value = dados[chave] || ('@' + obterDominioTribunal()) || configuracao.value || ''
			if(configuracao.type === 'number') configuracao.value = dados[chave] || configuracao.value || 0
			if(configuracao.type === 'text') configuracao.value = dados[chave] || configuracao.value || ''
		})
	})
}

function ativarConfiguracao(chave,configuracao){
	let ativar = {
		assistenteDeSelecao:['ativado'],
		pje:['expandirArvoreDocumentos','criarAreasDeRolagemDaPaginaDeDocumento'],
		pjeMenu:['anexarDocumento','audiencias','bndt','calculos','comunicacoes','expedientes','gigs','lembrete','pagar','pagamento','pauta','pdf','retificarAutuacao'],
		pjeAoAbrirDetalhesDoProcesso:['expandirMenu','criarAreasDeRolagemDaTimeline','criarAreasDeRolagemDoDocumento'],
		pjeAoAbrirTarefaDoProcesso:['expandirMenu','preencherDataDoTransito']
	}
	let destino = ativar[chave]
	if(destino.includes(configuracao)) return true
	return false
}

function salvarConfiguracoesDaExtensao(){
	setTimeout(salvar,50)
	function salvar(){
		document.querySelectorAll('configuracoes').forEach(configuracoes => {
			let destino = definirDestinoDasConfiguracoes(configuracoes)
			let dados = CONFIGURACAO[destino]
			configuracoes.querySelectorAll('input,textarea').forEach(configuracao => {
				let chave = configuracao.className || ''
				if(!chave) return
				if(chave === 'exportar' || chave === 'importar') return
				if(configuracao.type === 'textarea') dados[chave] = configuracao.value || ''
				if(chave === 'assinatura') dados[chave] = configuracao.value || configuracoesDaExtensaoAssinatura() || ''
				if(chave === 'emailDocumentos' || chave === 'whatsapp') dados[chave] = configuracao.value || configuracoesDaExtensaoTextoPadraoEmailDocumentos() || ''
				if(configuracao.type === 'checkbox') dados[chave] = configuracao.checked || false
				if(configuracao.type === 'number') dados[chave] = configuracao.value || 0
				if(configuracao.type === 'email' || configuracao.type === 'text') dados[chave] = configuracao.value.trim() || ''
			})
			browser.storage.local.set({[destino]:dados})
		})
	}
}

function definirDestinoDasConfiguracoes(configuracoes){
	let destino = configuracoes.className || ''
	if(!destino) return
	if(CONFIGURACAO[destino] == undefined) CONFIGURACAO[destino] = {}
	return destino
}

function configuracoesDaExtensaoTextoPadraoEmailDocumentos(){
	return 'Para ciência e cumprimento, no que couber, por parte de Vossa Senhoria, foi expedido o documento referenciado no início desta mensagem, que pode ser acessado pelo link acima informado.\n\nAgradeço pela atenção.\n\nSaudações,'
}

function configuracoesDaExtensaoAssinatura(){
	let nome = CONFIGURACAO?.usuario?.nome || ''
	let cargo = CONFIGURACAO?.usuario?.cargo || ''
	let unidade = CONFIGURACAO?.usuario?.unidade || ''
	if(nome) nome += '\n'
	if(cargo) cargo += '\n'
	if(unidade) unidade += '\n'
	return nome + cargo + unidade
}

function obterJanelaId(){
	return browser.windows.WINDOW_ID_CURRENT
}

function navegadorCapturarImagem(opcoes={}){
	let capturando = browser.tabs.captureVisibleTab(obterJanelaId(),obterDefinicoes())
	capturando.then(aoCapturar,seErro)

	function obterDefinicoes(){
		let definicoes = {}
		if(opcoes?.retangulo){
			let rect = {}
			let retangulo = opcoes.retangulo
			rect = {}
			rect.x = retangulo.x
			rect.y = retangulo.y
			rect.width = retangulo.width
			rect.height = retangulo.height
			definicoes.rect = rect
		}
		return definicoes
	}

	function aoCapturar(uri){
		fetch(uri).then(
			resposta => resposta.arrayBuffer()
		).then(
			imagem => {
				browser.clipboard.setImageData(imagem, "png")
				let audio = new Audio(caminho('audios/captura.mp3'))
				audio.play()
			}
		)
	}
	function seErro(erro){
		console.error(`Erro: ${erro}`)
	}
}


function criarAba(
	url = 'about:blank'
){

	relatar('Definindo opções...')

	let opcoes = {
		url: url,
		active: true
	}

	relatar('Opções definidas:', opcoes)

	relatar('Criando nova aba:');
	browser.tabs.create(opcoes)
		.then(() => relatar('Aba criada com sucesso!'))
		.catch(erro => console.error('Erro ao criar aba:', erro))
}