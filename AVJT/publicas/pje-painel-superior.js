function pjeCriarPainelSuperior(
	autogigs = true,
	certidoes = true
){
	let painel = new PainelSuperior()
	criarTituloProcesso()
	criarTituloPartes()
	criarBotoesDoProcesso()
	pjeAutogigsCriarBotoes(painel)
	pjeCertidaoCriarBotoes()
	document.body.addEventListener('click',ocultarMenu)
	ocultarMenu()
	painel.acionador.addEventListener('click',evento => {
		evento.stopPropagation()
		exibirMenu()
	})
	painel.acionador.addEventListener('mouseover',exibirPainelSuperiorAoPassarCursorSobreAtivador)
	if(!autogigs){
		remover('titulo-autogigs')
		remover('avjt-painel-superior-botoes-autogigs')
		remover('avjt-autogigs-adicionar')
	}

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
		if(CONFIGURACAO?.pje?.clicarParaExpandirPainelSuperior) return
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

	function criarBotoesDoProcesso(){
		criarTitulo('titulo-processo','','Utilidades do Processo',painel.corpo)
		let botoes = criar('botoes','avjt-painel-superior-botoes-processo','',painel.corpo)
		criarBotaoDoProcesso('pje1','Abrir Processo na Versão 1 do PJe','',pjeAbrirVersao1)
		criarBotaoDoProcesso('pje-instancia-2','Consultar Processo na 2ª Instância','',() => pjeConsultaPublicaProcessoInstancia(PROCESSO.numero,2))
		criarBotaoDoProcesso('trt','Consultar Processo no Tribunal Regional do Trabalho','',() => trtConsultarProcesso(PROCESSO.numero))
		criarBotaoDoProcesso('tst','Consultar Processo no Tribunal Superior do Trabalho','',() => tstConsultarProcesso(PROCESSO.numero))
		criarBotaoDoProcesso('retificar-autuacao','Retificar Autuação','',() => pjeAbrirRetificarAutuacao('Partes'))
		criarBotaoDoProcesso('sisbajud','SISBAJUD - Abrir Minuta de Bloqueio','',() => sisbajudAbrirCadastroDeMinuta(PROCESSO.numero))
		criarBotaoDoProcesso('whatsapp','Baixar Documento Ativo do PJe e Escrever WhatsApp','',whatsappMontarMensagem)
		criarBotaoDoProcesso('webmail','Baixar Documento Ativo do PJe e Escrever E-mail','',emailEscreverBaixarDocumentoAtivo)
		criarBotaoDoProcesso('chamado','Copiar Dados do Processo e Abrir Página de Chamado','',chamadoAbrirPagina)
		criarBotaoDoProcesso('siscondj','Consultar Depósitos Judiciais no SISCONDJ-JT','',() => {
			TAREFA.nome = 'SISCONDJ'
			TAREFA.processo = PROCESSO.numero
			siscondjConsultarProcesso()
		})
		criarBotaoDoProcesso('siscondj-alvaras','Consultar Alvarás no SISCONDJ-JT','',() => {
			siscondjConsultarProcesso('avjtSiscondjConsultarAlvaras'+PROCESSO.numero)
		})
		criarBotaoDoProcesso('bb','Consultar Depósitos Judiciais no Banco do Brasil','',bbConsultarProcesso)
		criarBotaoDoProcesso('cefRecursais','Consultar Depósitos Recursais na Caixa Econômica Federal','',() => cefConsultarDepositosRecursaisPorNomeDoPoloAtivo(PROCESSO.numero))
		criarBotaoDoProcesso('cefJudiciais','Consultar Depósitos Judiciais na Caixa Econômica Federal','',cefConsultarDepositosJudiciaisProcesso)
		criarBotaoDoProcesso('sif','SIF - Sistema de Interoperabilidade Financeira','',() => {
			pjeAbrirSif()
			if(CONFIGURACAO?.sif?.abrirDados) pjeDestacarDadosDoProcessoEmNovaJanela()
		})
		criarBotaoDoProcesso('correios','E-Carta - Consultar Processo','',() => ecartaConsultarProcesso(PROCESSO.numero))
		criarBotaoDoProcesso('sigeo','SIGEO - Requisitar Honorários Periciais','',sigeoPesquisarRequisicaoDeHonorariosPericiais)
		criarBotaoDoProcesso('pjeCalc','PJe Calc','',pjeCalcBuscarProcesso)
		criarBotaoDoProcesso('pjeCalc novo','PJe Calc - Novo Cálculo','',pjeCalcNovo)
		criarBotaoDoProcesso('mpt-adicionar','Adicionar Ministério Público do Trabalho como Custos Legis','⚖️\nMPT',() => pjeAbrirRetificarAutuacao('','Ministério Público do Trabalho'))
		criarBotaoDoProcesso('mpt-intimar','Intimar Ministério Público do Trabalho como Custos Legis','✉️\nMPT',() => pjeAbrirComunicacoes('mpt'))

		function criarBotaoDoProcesso(
			id = '',
			titulo = '',
			texto = '',
			aoClicar = ''
		){
			let botao = criar('botao','botao-do-processo-'+id,id+' botao-do-processo informacoes',botoes)
			if(titulo) botao.setAttribute('aria-label',titulo)
			if(texto){
				botao.innerText = texto
				botao.classList.add('texto')
			}
			if(aoClicar){
				botao.addEventListener('click',evento => {
					evento.stopPropagation()
					aoClicar()
					esforcosPoupados(1)
				})
			}
		}
	}
}

function pjePainelSuperiorMenuDeContextoFechar(){
	let menu = selecionar('menu-de-contexto')
	if(menu) menu.remove()
}