function pjeOtimizarGigs(){
	let painel = new PainelSuperior('avjt-autogigs')
	criarTituloProcesso()
	criarTituloPartes()
	pjeAutogigsCriarBotoes(painel)
	document.body.addEventListener('click',ocultarMenu)
	ocultarMenu()
	painel.acionador.addEventListener('mouseover',exibirPainelSuperiorAoPassarCursorSobreAtivador)

	function ocultarMenu(){
		painel.acionador.removeEventListener('mouseover',exibirPainelSuperiorAoPassarCursorSobreAtivador)
		painel.conteudo.style.margin = '-' + painel.conteudo.offsetHeight + 'px 0px 0px 0px'
		setTimeout(() => painel.acionador.addEventListener('mouseover',exibirPainelSuperiorAoPassarCursorSobreAtivador),500)
		pjePainelSuperiorMenuDeContextoFechar()
	}

	function exibirMenu(){
		painel.conteudo.style.marginTop = '0px'
	}

	function exibirPainelSuperiorAoPassarCursorSobreAtivador(){
		exibirMenu()
	}

	function criarTituloProcesso(){
		if(!PROCESSO?.numero) return
		let processo = criar('processo','avjt-painel-superior-processo','avjt-titulo',painel.cabecalho)
		processo.innerText = PROCESSO?.numero
	}

	function criarTituloPartes(){
		if(!PROCESSO?.partes) return
		let poloAtivo = PROCESSO?.partes?.ATIVO[0]?.nome + obterQuantidadeDePartesAdicionais(PROCESSO.partes.ATIVO)
		let poloPassivo = PROCESSO?.partes?.PASSIVO[0]?.nome + obterQuantidadeDePartesAdicionais(PROCESSO.partes.PASSIVO)
		let partes = criar('partes','avjt-painel-superior-partes','avjt-titulo',painel.cabecalho)
		partes.innerText = poloAtivo + ' x ' + poloPassivo

		function obterQuantidadeDePartesAdicionais(polo={}){
			if(!polo) return ''
			if(vazio(polo)) return ''
			let quantidade = polo?.length || ''
			if(quantidade > 1) return ' e outros (+' + (quantidade - 1) + ')'
			return ''
		}
	}
}

async function autogigsLancarAtividade(
	tipo = 'Prazo',
	prazo = '0',
	responsavel = '',
	observacao = '',
	comentario = '',
	destaque = false,
	salvar = false
){
	if(tipo.includes('Comentário')){
		await autogigsLancarComentario(comentario,salvar)
		return
	}
	if(prazo === '0') prazo = DATA.hoje.curta
	lancarNovaAtividade()

	async function lancarNovaAtividade(){
		let botao = novaAtividade()
		if(!botao){
			gigsAbrirPainel()
			await esperar('pje-gigs-comentarios-lista',true)
			novaAtividade()
		}
		esperar('pje-gigs-cadastro-atividades').then(preencherFormulario)

		function novaAtividade(){
			let botoes = document.querySelectorAll('button')
			let botao = [...botoes].filter(botao => botao.innerText.includes('Nova atividade'))
			if(vazio(botao)) return ''
			clicar(botao[0])
			return botao[0]
		}
	}

	async function preencherFormulario(){
		if(!responsavel) responsavel = 'SEM DESTINATÁRIO'
		await selecionarDestaque()
		await preencherPrazo()
		await autogigsSelecionarOpcao('tipoAtividade',tipo)
		await autogigsSelecionarOpcao('responsavel',responsavel)
		autogigsPreencherCampo('observacao',observacao)
		await salvarLancamento()
	}

	async function selecionarDestaque(){
		let caixa = await esperar('[formcontrolname="destaque"] input',true,true)
		if(!destaque) return
		clicar(caixa)
	}

	async function preencherPrazo(){
		// Verifica se o dado foi passado na forma de uma variável no campo do formulário de AutoGIGS em ./navegador/gigs/pagina.htm#[datalist id="prazos"]:
		let variavel = obterProcessoVariavel(prazo)
		if(variavel) prazo = processoObterVariavel(variavel)

		if(obterData(prazo)) await autogigsPreencherCampo('dataPrazo',prazo)
		else await autogigsPreencherCampo('dias',prazo)
	}

	async function salvarLancamento(){
		if(salvar) {
			await aguardar(1000)
			clicar('[aria-label="Salva as alterações"]')
			if(comentario) await autogigsLancarComentario(comentario)
		}
	}
}


async function autogigsLancarComentario(
	comentario = '',
	salvar = true
){
	if(!comentario) return
	lancarNovoComentario()

	async function lancarNovoComentario(){
		let botoes = document.querySelectorAll('button')
		let botao = [...botoes].filter(botao => botao.innerText.includes('Novo Comentário'))
		if(vazio(botao)) return
		botao[0].click()
		esforcosPoupados(1,1)
		esperar('[formcontrolname="descricao"]').then(preencherFormulario)
	}

	async function preencherFormulario(){
		autogigsPreencherCampo('descricao',comentario.replace(/\t/gi,''))
		salvarLancamento()
	}

	async function salvarLancamento(){
		if(salvar){
			await aguardar(1000)
			clicar('[aria-label="Salva as alterações"]')
		}
	}
}


async function autogigsPreencherCampo(
	formcontrolname = '',
	conteudo = ''
){
	if(!formcontrolname || !conteudo) return
	let campo = selecionar('[formcontrolname="'+formcontrolname+'"]')
	if(!campo) return
	campo.click()
	campo.value = conteudo
	dispararEvento('input',campo)
	if(
		formcontrolname === 'dias'
		||
		formcontrolname === 'dataPrazo'
	){
		await new Promise(resolve => requestAnimationFrame(resolve))
		await aguardar(100)
	}
	dispararEvento('change',campo)
	esforcosPoupados(1,1,contarCaracteres(conteudo))
}


async function autogigsSelecionarOpcao(
	seletor,
	conteudo
){
	return new Promise(resolver => {
		autogigsPreencherCampo(seletor,conteudo)
		let observador = new MutationObserver(() => {
			let observado = selecionar('.mat-autocomplete-visible')
			if(observado){
				let opcoes = document.querySelectorAll('mat-option')
				let opcao = [...opcoes].filter(opcao => opcao.innerText == conteudo)[0] || ''
				if(!opcao) return ''
				opcao.click()
				esforcosPoupados(2,2)
				observador.disconnect()
				resolver(observado)
			}
		})
		observador.observe(document.body,{childList:true,subtree:true,attributes:true,characterData:false})
	})
}

function pjeAutogigsCriarBotoes(painel=''){
	if(!painel) return
	criarTitulo('titulo-autogigs','','AutoGIGS',painel.corpo)
	let botoes = criar('botoes','avjt-painel-superior-botoes-autogigs','',painel.corpo)
	criarBotaoAdicionar()
	function 	criarBotaoAdicionar(){
		criarTitulo('titulo-controles','','Configurações',painel.corpo)
		let controles = criar('botoes','avjt-painel-superior-controles','',painel.corpo)
		criarBotao('avjt-autogigs-adicionar','botao-automacao',controles,'Adicionar Botão de AutoGIGS','',() => abrirPagina(caminho('navegador/gigs/pagina.htm'),'','','','','pjeGigs'))
	}

	CONFIGURACAO.gigs.forEach((botao,indice) => {
		criarBotaoAutogigs(indice,botao.e,botao.f,botao.t,botao.p,botao.r,botao.o,botao.c,botao.d,botao.g)
	})

	setTimeout(() => painel.corpo.click(),1000)

	function criarBotaoAutogigs(
		indice = '',
		rotulo = '',
		cor = '#000',
		tipo = '',
		prazo = '',
		responsavel = '',
		observacao = '',
		comentario = '',
		destacar = false,
		gravar = false
	){
		let posicao = Number(indice) + 1
		let botao = criarBotao('botao-automacao-gigs'+posicao,'botao-automacao',botoes,posicao+'. '+rotulo)
		botao.style = 'background:linear-gradient(to bottom,rgba(0,0,0,0.1) 0%,rgba(0,0,0,0.3) 100%),'+cor+';'
		botao.title = obterTituloDoBotao()
		botao.addEventListener('click',evento => {
			evento.stopPropagation()
			autogigsLancarAtividade(tipo,prazo,responsavel,observacao,comentario,destacar,gravar)
		})
		botao.addEventListener('contextmenu',elemento => {
			elemento.preventDefault()
			criarMenu(elemento)
		})

		function obterTituloDoBotao(){
			let titulo = 'Lançamento do tipo ' + tipo + '\n'
			if(prazo) titulo += 'Prazo: ' + prazo  + '\n'
			if(responsavel) titulo += 'Responsável: ' + responsavel  + '\n'
			if(observacao) titulo += 'Observação: ' + observacao  + '\n'
			if(comentario) titulo += 'Comentário: ' + comentario  + '\n'
			return titulo
		}

		function criarMenu(referencia){
			referencia.preventDefault()
			let localizacao = referencia.target.getBoundingClientRect()
			let menu = criar('menu-de-contexto','avjt-autogigs-menu-de-contexto')
			menu.style.left = (localizacao.left + 25) + 'px'
			menu.style.top = (localizacao.top + 25) + 'px'
			menu.addEventListener('click',evento => evento.stopPropagation())
			let botaoEditar = criarBotao('menu-de-contexto-botao-editar','',menu,'EDITAR')
			let botaoExcluir = criarBotao('menu-de-contexto-botao-excluir','',menu,'EXCLUIR')
			let botaoFechar = criarBotao('menu-de-contexto-botao-fechar','',menu,'FECHAR')
			let posicao = (Number(numeros(referencia.target.id))) || 0
			botaoEditar.addEventListener('click',() => abrirPagina(caminho('navegador/gigs/pagina.htm?editar='+posicao),'','','','','pjeGigs'))
			botaoExcluir.addEventListener('click',() => {
				let gigs = CONFIGURACAO?.gigs || ''
				if(!gigs) return
				gigs.splice((posicao - 1),1)
				browser.storage.local.set({gigs}).then(() => pjeAutogigsCriarBotoes(painel))
				pjePainelSuperiorMenuDeContextoFechar()
			})
			botaoFechar.addEventListener('click',pjePainelSuperiorMenuDeContextoFechar)
		}
	}
}

async function gigsAbrirPainel(){
	clicar('[aria-label="Menu do processo"]')
	clicar('[aria-label="Menu da tarefa"]')
	let gigs = await esperar('[aria-label*="Abrir o GIGS para o processo"]')
	clicar(gigs)
}