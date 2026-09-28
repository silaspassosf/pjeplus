async function pje(){
	if(!JANELA.includes(LINK.pje.raiz)) return
	pjePaginaInicialAcionarBotaoCertificadoDigital()
	pjeRedirecionarPaginaAcessoNegado()
	pjePesquisarProcesso()
	pjeOtimizarLegado()
	pjeOtimizarPaginaConsultaPublica()
	pjeOtimizarPaginaRetificarAutuacao()
	pjeOtimizarPaginaSif()
	pjeOtimizarPaginaComunicacoes()
	pjeOtimizarPaginaDocumento()
	pjeOtimizarPaginaEditor()
	pjeOtimizarPaginaVersao1()
	pjeOtimizarPainelConsultaProcessos()
	pjeOtimizarPainelInicial()
	pjeOtimizarPainelAvisos()
	pjeOtimizarPainelGlobal()
	pjeOtimizarPerfilUsuario()
	pjeOtimizarPerfilOficialDeJustica()
	pjeGigsFecharMensagensDeConclusao()
	pjeGigsFecharMensagensDeExclusao()
	pjePericiasFecharMensagensDeConclusao()
	pjeModalIncluirChipsOtimizarlayout()

	function pjePesquisarProcesso(){
		let processo =  obterParametroDeUrl('processo')
		if(!processo) return
		esperar('#inputNumeroProcesso',true).then(campo => {
			preencher(campo,processo)
			campo.click()
		})
	}
}

async function pjePaginaInicialAcionarBotaoCertificadoDigital(){
	if(!CONFIGURACAO?.pje?.paginaInicialAcionarBotaoCertificadoDigital) return
	let botao = await esperar('#loginAplicacaoButton',true,true)
	clicar(botao)
}

function pjeRedirecionarPaginaAcessoNegado(){
	esperar('pje-acesso-negado').then(redirecionar)
	esforcosPoupados(2,2,2)

	function redirecionar(){
		window.location = LINK.pje.raiz
	}
}

function pjeOtimizarPainelInicial(){
	esperar('pje-menu-acesso-rapido').then(pjeListarProcessos)
}

function pjeOtimizarPainelConsultaProcessos(){
	if(JANELA.includes('administracao/consulta/processo')) pjeListarProcessos()
}

async function pjeOtimizarPainelAvisos(){
	if(!JANELA.match(LINK.pje.painel.avisos)) return
	let botaoSeletor = '[aria-label="Trocar Órgão Julgador ou Perfil"]'
	await esperar(botaoSeletor,true,true)
	await aguardar(500)
	alterarPerfil()
	
	async function alterarPerfil(){
		let texto = await navigator.clipboard.readText()
		if(!texto) return ''
		let json = JSON.parse(texto) || ''
		console.log('json',json)
		if(json?.avjt === 'AlterarPerfil'){
			let origem = json?.orgao || ''
			if(!origem) return
			let processo = json?.processo || ''
			if(!processo) return
			let id = json?.id || ''
			if(!id) return
			let url = LINK.pje.processo + id + '/detalhe?janela=destacada'
			let papel = selecionar('span.papel-usuario')
			if(!papel) return
			let orgao = papel.innerText.trim() || ''
			let manterPerfil = ''
			console.log('orgao',orgao)
			
			if(maiusculas(orgao) === maiusculas(origem))
				manterPerfil = true
			if(!manterPerfil){
				clicar(botaoSeletor)
				let menu = await esperar('.menu-selecao-perfil-usuario')
				await aguardar(500)
				console.log('menu',menu)
				let item = selecionarPorTexto(origem,'span')
				if(!item) return
				let botao = item.nextElementSibling.querySelector('button')
				if(!botao) return
				botao.click()
				await aguardar(500)
			}
				abrirPagina(url,'','','','','pjeDetalhes')
				await aguardar(1000)
				fechar()

			//	window.location.href = LINK.pje.painel.global + encodeURI(processo)
			
		}
	}
}

async function pjeOtimizarPainelGlobal(){
	if(!JANELA.match(/global.todos.lista.processos/gi)) return
	if(JANELA.match(EXPRESSAO.processoNumero)) return
}

async function pjeOtimizarPerfilUsuario(){
	let id = pjeObterProcessoId()
	relatar('id',id)
	if(!id) return
	PROCESSO = await pjeObterDadosPrincipaisDoProcesso(id)
	console.info('PROCESSO:',PROCESSO)
	pjeOtimizarPaginaAnexarDocumento()
	pjeOtimizarPaginaAudiencias()
	pjeOtimizarPaginaDetalhesDoProcesso()
	pjeOtimizarPaginaGigs()
	pjeOtimizarPaginaPericias()
	pjeOtimizarPaginaTarefaDoProcesso()
}

async function pjeOtimizarPerfilOficialDeJustica(){
	let id = pjeObterMandadoId()
	if(!id) return
	let mandado = await pjeApiCentralDeMandadosObterMandadoDadosPrimarios(id)
	if(!mandado?.idProcessoExterno) return
	PROCESSO = await pjeObterDadosPrincipaisDoProcesso(mandado.idProcessoExterno)
	pjeOtimizarDetalhesDoMandado()
}

function pjeOtimizarDetalhesDoMandado(){
	let contexto = pjeObterContexto()
	if(!contexto.includes('mandados')) return
	pjeCriarBotaoFixoDestacarDadosDoProcesso()
}

function pjeOtimizarPaginaAnexarDocumento(){
	let contexto = pjeObterContexto()
	if(!contexto.includes('pje-anexar')) return
	pjeCriarBotoesFixos()
	aoAbrir()

	function aoAbrir(){
		pjeAnexarDocumentoPreencherCertidao()
	}
}

function pjeOtimizarPaginaAudiencias(){
	let contexto = pjeObterContexto()
	if(!contexto.includes('pje-audiencias')) return
	pjeCriarBotoesFixos()
	aoAbrir()

	function aoAbrir(){
		return
	}
}

async function pjeOtimizarPaginaConsultaPublica(){
	let contexto = pjeObterContexto()
	if(!contexto.includes('pje-consulta-publica')) return
	pjeCriarBotaoFixoConfigurarDimensoesDaJanela()
	setTimeout(aoAbrir,500)

	async function aoAbrir(){
		pjeDocumentoOtimizarRolagem()
		setTimeout(copiarDataDeTransitoEmJulgado,500)
	}

	async function copiarDataDeTransitoEmJulgado(){
		window.focus()
		let movimentos = document.querySelectorAll('pje-timeline-item mat-card')
		let movimento = [...movimentos].filter(movimento => movimento.textContent.match(/Decorrido o prazo de .*?\d{2}\/\d{2}\/\d{4}/))[0] || ''
		if(!movimento) return
		let data = obterData(movimento.textContent)
		copiar(data)
		setTimeout(tstEsperarDocumentos,1500)
		setTimeout(tstAbrirCertidao,2000)
		setTimeout(tstAbrirCertidao,3000)
		setTimeout(tstAbrirCertidao,4000)
		setTimeout(tstAbrirCertidao,5000)

		async function tstEsperarDocumentos(){
			let tst = await esperar('a[aria-label*="TST - Certidão de Trânsito em Julgado"]',true,true)
			if(!tst) return
			clicar(tst)
			setTimeout(tstAbrirCertidao,2000)
		}

		async function tstAbrirCertidao(){
			let pdf = await esperar('.textLayer',true,true)
			let texto = pdf.textContent || ''
			let transito = texto.match(/não  houve  interposição  de  recurso  contra/gi) || ''
			if(transito) copiar(obterData(texto))
		}
	}
}

async function pjeOtimizarPaginaComunicacoes(){
	let intimar =  obterParametroDeUrl('intimar')
	if(intimar){
		intimarMinisterioPublicoDoTrabalho()
		return
	}
	esperar('[name="btnIntimarSomentePoloPassivo"]',true).then(aoAbrir)

	async function aoAbrir(){
		let contexto = pjeObterContexto()
		if(!contexto.includes('pje-comunicacoes')) return
		filtrarModelosDeComunicacao()
		esperar('.pec-item-botoes-acoes-expedientes',true,true).then(otimizarLayout)
		if(CONFIGURACAO?.pjeAssistentesDocumentosNotificacoes?.expandirPartes) await expandirPartes()
		if(CONFIGURACAO?.pjeAssistentesDocumentosNotificacoes?.comunicacaoTipoDeDocumento) await selecionarTipoDeDocumento(CONFIGURACAO?.pjeAssistentesDocumentosNotificacoes?.comunicacaoTipoDeDocumento)
		if(CONFIGURACAO?.pjeAssistentesDocumentosNotificacoes?.comunicacaoPrazo) await selecionarPrazo()
		if(CONFIGURACAO?.pjeAssistentesDocumentosNotificacoes?.confeccionar){
			if(!JANELA.includes('tarefa')) setTimeout(confeccionarAtoAgrupado,500)
		}
	}

	function otimizarLayout(){
		estilizar('',
		`
			pje-pec-botoes-acoes-expedientes{
				display:inline-block !important;
			}
		`)
	}

	async function intimarMinisterioPublicoDoTrabalho(){
		if(intimar != 'mpt') return
		expandirPartes()
		selecionarTipoDeDocumento()
		setTimeout(confeccionarAtoAgrupado,1000)
		let descricao = await esperar('[aria-label="Descrição"]',true,true)
		preencher(descricao,'Custos Legis - Ministério Público do Trabalho')
		await pjeEditorFocarAoCarregar('Intimação expedida para fins de intervenção do Ministério Público, nos termos do artigo 178 do Código de Processo Civil.')
	}

	async function expandirPartes(){
		await esperar('[name="btnIntimarSomentePoloPassivo"]',true)
		let partes = document.querySelectorAll('mat-expansion-panel-header')
		partes.forEach(item => clicar(item))
	}

	async function selecionarTipoDeDocumento(configuracao='Intimação'){
		await esperar('[name="btnIntimarSomentePoloPassivo"]',true)
		clicar('[placeholder="Tipo de Expediente"]')
		await pjeSelecionarOpcaoPorTexto(configuracao)
	}

	async function selecionarPrazo(){
		let configuracao = CONFIGURACAO?.pjeAssistentesDocumentosNotificacoes?.comunicacaoPrazo || ''
		if(!configuracao) return
		await esperar('[name="btnIntimarSomentePoloPassivo"]',true)
		let opcoes = [...document.querySelectorAll('mat-radio-button')].filter(opcao => opcao.textContent.includes(minusculas(configuracao)))[0] || ''
		if(!opcoes) return
		let opcao = opcoes.querySelector('input') || ''
		clicar(opcao)
		if(configuracao.includes(('Dias Úteis'))) await definirDias()
		if(configuracao.includes(('Data Certa'))) await definirData()
	}

	async function definirDias(){
		let configuracao = CONFIGURACAO?.pjeAssistentesDocumentosNotificacoes?.comunicacaoDias || ''
		if(!configuracao) return
		let campo = await esperar('[aria-label="Prazo em dias úteis"]',true)
		preencher(campo,configuracao)
	}

	async function definirData(){
		let configuracao = CONFIGURACAO?.pjeAssistentesDocumentosNotificacoes?.comunicacaoData || ''
		if(!configuracao) return
		let campo = await esperar('[aria-label="Prazo em data certa"]',true)
		preencher(campo,configuracao)
	}

	async function confeccionarAtoAgrupado(){
		clicar('[aria-label="Confeccionar ato agrupado"]')
		esperar('[aria-label="Finalizar minuta"]',true,true).then(botao => {
			botao.addEventListener('mouseenter',
				() => clicar('[aria-label="Salvar"]')
			)
		})
	}

	async function filtrarModelosDeComunicacao(){
		let configuracao = CONFIGURACAO?.pjeAssistentesDocumentosNotificacoes?.filtrarModelosComunicacao || ''
		if(!configuracao) return
		esperar('[aria-label="Buscar pelo nome da pasta ou modelo ao digitar"]',true,true).then(campo => {
			preencher(campo,configuracao,true,true,'keyup')
			setTimeout(() => focar(campo),1000)
		})
	}
}


async function pjeOtimizarPaginaDocumento(){
	let contexto = pjeObterContexto()
	if(!contexto.includes('pje-documento')) return
	let id = pjeObterProcessoId()
	let documento = pjeObterProcessoDocumentoId()
	let DOCUMENTO = {}
	if(id){
		PROCESSO = await pjeObterDadosPrincipaisDoProcesso(id)
		console.info('PROCESSO:',PROCESSO)
		DOCUMENTO = await pjeApiObterProcessoDocumento(id,documento)
		aoAbrir()
	}

	function aoAbrir(){
		pjeCriarBotaoFixoConfigurarDimensoesDaJanela()
		pjeCriarPainelSuperior(false)
		pjeCriarBotaoFixoCopiarIdDoDocumento()
		pjeCriarBotaoFixoCopiarDataDoDocumento()
		pjeCriarBotaoFixoCopiarIdDoDocumento()
		pjeCriarBotaoFixoCopiarLinkDoDocumento()
		pjeCriarBotaoFixoDestacarDadosDoProcesso()
		pjeCriarBotaoFixoEnviarDocumentoPorEmail()
		pjeCriarBotaoFixoEnviarDocumentoPorWhatsapp()
		pjeCriarBotaoFixoNotificar()
		pjeDocumentoOtimizarRolagem()
		pjeDocumentoOtimizarExibicao()
	}

	function pjeDocumentoOtimizarExibicao(){
		console.info('DOCUMENTO:',DOCUMENTO)
		let cabecalho = selecionar('mat-card-header')
		let tipo = DOCUMENTO?.tipo || ''
		let cor = ''
		let opacidade = ''
		if(tipo == 'Ata da Audiência'){
			cor = 'indigo'
			opacidade = '0.5'
		}
		if(tipo == 'Agravo de Petição'){
			cor = 'amarelo'
			opacidade = '0.5'
		}
		if(tipo == 'Sentença'){
			cor = 'preto'
			opacidade = '0.3'
		}
		if(tipo == 'Recurso Ordinário'){
			cor = 'verde'
			opacidade = '0.3'
		}
		if(tipo == 'Recurso Adesivo'){
			cor = 'laranja'
			opacidade = '0.3'
		}
		if(tipo == 'Agravo de Instrumento'){
			cor = 'azul'
			opacidade = '0.3'
		}
		if(tipo == 'Acórdão'){
			cor = 'vermelho'
			opacidade = '0.3'
		}
		estilizar(cabecalho,
			`mat-card-header{
				background:rgba(var(--extensao-cor-${cor}),${opacidade});
			}`
		)
		document.title = tipo + ' - ' + PROCESSO.numero
	}
}

function pjeOtimizarPaginaGigs(){
	let contexto = pjeObterContexto()
	if(!contexto.includes('pje-gigs')) return
	pjeCriarBotaoFixoConfigurarDimensoesDaJanela()
	pjeOtimizarGigs()
	aoAbrir()

	function aoAbrir(){
		return
	}
}

async function pjeOtimizarPaginaPericias(){
	let contexto = pjeObterContexto()
	if(!contexto.includes('pje-pericias')) return
	pjeCriarBotoesFixos()
	pjeCriarPainelSuperior()
	aoAbrir()

	function aoAbrir(){
		alterarTituloDaNotificacao()
		alterarPrazoDaNotificacao()
	}

	async function alterarPrazoDaNotificacao(){
		let configuracao = CONFIGURACAO?.pjeAssistentesDocumentosNotificacoes?.laudoEsclarecimentoDias || ''
		if(!configuracao) return
		let campo = await esperar('mat-form-field input[formcontrolname="prazoDias"]',true)
		preencher(campo,configuracao)
	}

	async function alterarTituloDaNotificacao(){
		if(!CONFIGURACAO?.pjeAssistentesDocumentosNotificacoes?.descreverEsclarecimentosLaudo) return
		let campo = await esperar('mat-form-field input[aria-label="Descrição"]',true,false,false,false)
		let solicitarEsclarecimentos = selecionar('pje-documento-solicitar-esclarecimentos')
		if(solicitarEsclarecimentos?.textContent?.includes('Solicitar Esclarecimentos')) preencher(campo,'Apresentar Esclarecimentos Sobre o Laudo Pericial')
	}
}

function pjeOtimizarPaginaSif(){
	let contexto = pjeObterContexto()
	if(!contexto.includes('pje-sif')) return
	pjeCriarBotaoFixoConfigurarDimensoesDaJanela()
	aoAbrir()

	function aoAbrir(){
		return
	}
}

function pjeOtimizarPaginaVersao1(){
	let contexto = pjeObterContexto()
	if(!contexto.includes('pje-versao1')) return
	setTimeout(pjeCriarBotaoFixoConfigurarDimensoesDaJanela,1000)
	aoAbrir()

	function aoAbrir(){
		return
	}
}

async function pjeObterDadosPrincipaisDoProcesso(id){
	PROCESSO = await pjeApiObterProcessoDadosPrimarios(id)
	if(!PROCESSO?.numero) return
	Object.assign(PROCESSO,obterDadosDoNumeroDoProcesso(PROCESSO.numero))
	PROCESSO.data = {}
	PROCESSO.valor = pjeObterValoresDoProcesso()
	PROCESSO.tarefa = await pjeApiObterProcessoTarefa(id)
	PROCESSO.audiencia = await pjeApiObterProcessoAudiencia(id)
	PROCESSO.partes = await pjeApiObterProcessoPartes(id)
	PROCESSO.etiquetas = await pjeApiObterProcessoEtiquetas(id)
	PROCESSO.acordo = await pjeApiObterProcessoUltimoAcordo(id)
	PROCESSO.chips = []
	PROCESSO.emails = ''
	pjeProcessoObterChips()
	pjeProcessoObterLinks()
	trt15ObterEmailsParaCitacao()
	pjeSalvarDadosDoProcesso()
	pjeApiObterProcessoMovimentos(id).then(movimentos => {
		PROCESSO.movimentos = movimentos
		pjeObterDatas()
	})
	pjeApiObterProcessoDocumentos(id).then(documentos => {
		PROCESSO.documentos = documentos || ''
		PROCESSO.acordaos = pjeFiltrarDocumentosDoProcessoPorTipo('Acórdão')
		PROCESSO.agravos = pjeFiltrarDocumentosDoProcessoPorTipo('Agravo de Petição').concat(pjeFiltrarDocumentosDoProcessoPorTipo('Agravo de Instrumento'))
		PROCESSO.atas = pjeFiltrarDocumentosDoProcessoPorTipo('Ata da Audiência')
		PROCESSO.decisoes = pjeFiltrarDocumentosDoProcessoPorTipo('Decisão')
		PROCESSO.despachos = pjeFiltrarDocumentosDoProcessoPorTipo('Despacho')
		PROCESSO.recursos = pjeFiltrarDocumentosDoProcessoPorTipo('Recurso Ordinário').concat(pjeFiltrarDocumentosDoProcessoPorTipo('Recurso Adesivo'))
		PROCESSO.sentencas = pjeFiltrarDocumentosDoProcessoPorTipo('Sentença')
		PROCESSO.peticaoInicial = pjeFiltrarDocumentosDoProcessoPorTipo('Petição Inicial')
		PROCESSO.instrucao = pjeProcessoObterInstrucao()
		PROCESSO.ultimoDocumento = pjeProcessoObterUltimoDocumento()
		pjeProcessoObterInstrucao()
		pjeSalvarDadosDoProcesso()
		pjeAoAbrirDetalhesDoProcessoAbrirDocumentos()
	})
	console.log('PROCESSO',PROCESSO)
	
	return PROCESSO

	async function trt15ObterEmailsParaCitacao(){
		let contexto = pjeObterContexto()
		if(!contexto.includes('pje-documento')) return ''
		//if(!CONFIGURACAO.instituicao.unidade === '1ª Vara do Trabalho de Taubaté') return ''
		let pessoas = await trt15ApiConsultaPlanilhaPessoas()
		let pessoas0009 = await trt15ApiConsultaPlanilhaPessoas0009()
		if(pessoas0009) pessoas = pessoas.concat(pessoas0009)
		let partes = PROCESSO?.partes || ''
		if(!partes) return
		let poloPassivo = partes?.PASSIVO || ''
		if(!poloPassivo) return
		let emails = ''
		let nomes = ''
		let rotulo = 'Parte(s) com e-mail(s) cadastrado(s) para notificação '
		let contador = 0
		poloPassivo.forEach(parte => {
			let documento = parte?.documento || ''
			let nome = parte?.nome || ''
			if(!documento) return ''
			let pessoa = pessoas.filter(dados => dados.d.includes(documento))[0] || ''
			if(!pessoa) return ''
			let email = pessoa?.e?.replace(/\s/gi,'')?.trim() || ''
			if(!email) return ''
			emails += minusculas(email) + ';'
			nomes += nome + ', '
			contador++
		})

		PROCESSO.emails = emails.replace(/[;]$/gi,'')
		nomes = nomes.replace(/[,]\s$/gi,'')
		rotulo = rotulo + '(' + contador  + '): ' + nomes
		console.info(rotulo)
		console.info(PROCESSO.emails.replace(/[;]$/gi,''))
		if(!PROCESSO.emails) return ''
		pjeCriarBotaoFixoNotificacaoInicialPorEmail(rotulo)
		pjeCriarBotaoFixoCitacaoPorEmail(rotulo)
		pjeCriarBotaoFixoNotificarAudienciaPorEmail(rotulo)
		pjeCriarBotaoFixoNotificacaoSentencaPorEmail(rotulo)
		pjeCriarBotaoFixoCitacaoEspecialPorEmail(rotulo)
	}

	function pjeProcessoObterChips(){
		PROCESSO.etiquetas.forEach(etiqueta => {
			let chip = etiqueta?.etiquetaInstancia?.etiqueta?.nome || ''
			if(chip) PROCESSO.chips.push(chip)
		})
	}

	function pjeProcessoObterLinks(){
		LINK.pje.anexar = LINK.pje.processo + id + '/documento/anexar'
		LINK.pje.audiencias = LINK.pje.processo + id + '/audiencias-sessoes'
		LINK.pje.bndt = LINK.pje.processo + id + '/bndt'
		LINK.pje.calculos = LINK.pje.processo + id + '/detalhe/calculo'
		LINK.pje.comunicacoes = LINK.pje.processo + id + '/comunicacoesprocessuais/minutas'
		LINK.pje.copiarDocumentos = LINK.pje.processo + id + '/copiar-documento'
		LINK.pje.gigs = LINK.pje.kz + 'gigs/abrir-gigs/' + id
		LINK.pje.historico = LINK.pje.processo + id + '/historicotarefa'
		LINK.pje.legado.processo = LINK.pje.legado.processo + id
		LINK.pje.pagar = LINK.pje.kz + 'obrigacao-pagar/' + id
		LINK.pje.pagamento = LINK.pje.kz + 'pagamento/' + id
		LINK.pje.pericias = LINK.pje.processo + id + '/pericias'
		LINK.pje.recursos = LINK.pje.processo + id + '/quadro-recursos'
		LINK.pje.retificarAutuacao = LINK.pje.processo + id + '/retificar'
		LINK.pje.sif = LINK.pje.raiz + 'sif/consultar/' + PROCESSO.numeros + '/saldo'
		LINK.pje.tarefa = LINK.pje.processo + id + '/tarefa/' //+ PROCESSO.tarefa.idTarefa
	}

	function pjeProcessoObterInstrucao(){
		let sentencas = PROCESSO?.sentecas || ''
		if(!sentencas) return true
		if(vazio(sentencas)) return true
		return false
	}

	function pjeProcessoObterUltimoDocumento(){
		let documentos = PROCESSO?.documentos || ''
		if(!documentos) return ''
		if(vazio(documentos)) return ''
		let ultimo = documentos[0] || ''
		return ultimo
	}
}

async function pjeObterDatas(){
	let ultimoMovimento = PROCESSO?.movimentos[0]?.data || ''
	if(ultimoMovimento) PROCESSO.data.ultimoMovimento = new Date(ultimoMovimento)?.toLocaleDateString() || DATA.hoje.curta || ''
}

function pjeObterValoresDoProcesso(){
	let valor = {}
	if(PROCESSO?.valorDaCausa) valor.causa = Number(PROCESSO.valorDaCausa).toLocaleString('pt-BR',{minimumFractionDigits:2}) || ''
	return valor
}

function pjeCriarBotoesFixos(){
	let contexto = pjeObterContexto()
	pjeCriarBotaoFixoConfigurarDimensoesDaJanela()
	pjeCriarBotaoFixoDestacarDadosDoProcesso()
	pjeCriarBotaoFixoCopiarNumeroDoProcesso()
	pjeCriarBotaoFixoCopiarDadosTabuladosDoProcesso()
	pjeExpandirMenuDoProcessoso()

	function pjeExpandirMenuDoProcessoso(){
		remover('menu-do-processo-expandido')
		if(contexto.includes('pje-anexar')){
			if(!CONFIGURACAO?.pjeAssistentesDocumentosNotificacoes?.expandirMenu) return
			estilizar('',`
				pje-anexar-documento h1{
					padding:20px 0 0 0 !important;
				}
			`)
		}
		if(contexto.includes('pje-detalhes') || contexto.includes('pje-pericias')){
			if(!CONFIGURACAO?.pjeAoAbrirDetalhesDoProcesso?.expandirMenu) return
			estilizar('',`
				.resumo-processo dl{
					padding:30px 0 0 0 !important;
				}
			`)
		}
		if(contexto.includes('pje-tarefa')){
			if(!CONFIGURACAO?.pjeAoAbrirTarefaDoProcesso?.expandirMenu) return
			estilizar('',`
				pje-cabecalho-tarefa h1.titulo-tarefa{
					margin:25px 0 0 0 !important;
				}
			`)
		}
		let menu = criar('menu-do-processo-expandido','menu-do-processo-expandido')
		criarBotao('menu-do-processo-expandido-configuracoes','configuracoes informacoes',menu,'','Configuracões de Menu',abrirPaginaConfiguracoesMenuExpandido)
		if(CONFIGURACAO?.pjeMenu?.anexarDocumento){
			if(!contexto.includes('pje-anexar')) criarBotao('menu-do-processo-expandido-anexar','anexar informacoes',menu,'','Anexar Documento',pjeAbrirAnexar)
		}
		if(CONFIGURACAO?.pjeMenu?.retificarAutuacao) criarBotao('menu-do-processo-expandido-retificar-autuacao','processo-retificar informacoes',menu,'','Retificar Autuação',pjeAbrirRetificarAutuacao)
		if(CONFIGURACAO?.pjeMenu?.reprocessarChips){
			if(!contexto.includes('pje-anexar')) criarBotao('menu-do-processo-expandido-reprocessar','reprocessar informacoes',menu,'','Reprocessar Chips',pjeProcessoReprocessarChips)
		}
		if(CONFIGURACAO?.pjeMenu?.movimentos){
			if(!contexto.includes('pje-anexar') && !contexto.includes('pje-tarefa')) criarBotao('menu-do-processo-expandido-movimentos','movimentos informacoes',menu,'','Lançar Movimentos',pjeProcessoDetalhesLancarMovimentos)
		}
		if(CONFIGURACAO?.pjeMenu?.gigs) criarBotao('menu-do-processo-expandido-gigs','gigs informacoes',menu,'','Abrir GIGS em Nova Janela',pjeAbrirGigsEmNovaPagina)
		if(CONFIGURACAO?.pjeMenu?.lembrete){
			if(!contexto.includes('pje-anexar')) criarBotao('menu-do-processo-expandido-lembrete','lembrete informacoes',menu,'','Criar Lembrete',pjeProcessoDetalhesInserirLembrete)
		}
		if(CONFIGURACAO?.pjeMenu?.expedientes){
			if(!contexto.includes('pje-anexar')) criarBotao('menu-do-processo-expandido-expedientes','expedientes informacoes',menu,'','Expedientes do Processo',pjeProcessoDetalhesExpedientes)
		}
		if(CONFIGURACAO?.pjeMenu?.comunicacoes) criarBotao('menu-do-processo-expandido-comunicacoes','comunicacoes informacoes',menu,'','Notificar',pjeAbrirComunicacoes)
		if(CONFIGURACAO?.pjeMenu?.pagar) criarBotao('menu-do-processo-expandido-pagar','pagar informacoes',menu,'','Obrigação de Pagar',pjeAbrirObrigacaoDePagar)
		if(CONFIGURACAO?.pjeMenu?.pagamento) criarBotao('menu-do-processo-expandido-receber','receber informacoes',menu,'','Pagamento',pjeAbrirPagamento)
		if(CONFIGURACAO?.pjeMenu?.audiencias) criarBotao('menu-do-processo-expandido-audiencias','audiencia informacoes',menu,'','Audiências do Processo',pjeAbrirAudienciasSessoes)
		if(CONFIGURACAO?.pjeMenu?.pauta) criarBotao('menu-do-processo-expandido-pauta','pauta informacoes',menu,'','Pauta de Audiências',pjeAbrirPautaDeAudiencias)
		if(CONFIGURACAO?.pjeMenu?.pericias) criarBotao('menu-do-processo-expandido-pericias','pericias informacoes',menu,'','Perícias',pjeAbrirPericias)
		if(CONFIGURACAO?.pjeMenu?.calculos) criarBotao('menu-do-processo-expandido-calculos','calculos informacoes',menu,'','Cálculos do Processo',pjeAbrirCalculos)
		if(CONFIGURACAO?.pjeMenu?.bndt) criarBotao('menu-do-processo-expandido-bndt','bndt informacoes',menu,'','BNDT',pjeAbrirBndt)
		if(CONFIGURACAO?.pjeMenu?.recursos) criarBotao('menu-do-processo-expandido-recurso','recurso informacoes',menu,'','Controle de Recursos',pjeAbrirRecursos)
		if(CONFIGURACAO?.pjeMenu?.historico) criarBotao('menu-do-processo-expandido-historico','historico informacoes',menu,'','Histórico de Tarefas',pjeAbrirHistoricoDeTarefas)
		if(CONFIGURACAO?.pjeMenu?.copiarDocumentos) criarBotao('menu-do-processo-expandido-clonar','clonar informacoes',menu,'','Copiar Documentos',pjeAbrirCopiarDocumentos)
		if(CONFIGURACAO?.pjeMenu?.removerChips) criarBotao('menu-do-processo-expandido-remover-chips','remover-chips informacoes',menu,'','Remover Todos os Chips',pjeRemoverTodosOsChips)
		if(CONFIGURACAO?.pjeMenu?.pdf){
			if(!contexto.includes('pje-anexar') && !contexto.includes('pje-tarefa')) criarBotao('menu-do-processo-expandido-pdf','pdf informacoes',menu,'','Baixar Processo Completo',pjeProcessoDetalhesBaixarProcessoCompleto)
		}
	}
}