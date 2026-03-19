async function pjeSelecionarOpcao(
	texto = '',
	seletor = '.mat-autocomplete-visible'
){
	await esperar(seletor,true)
	let opcao = [...document.querySelectorAll('mat-option')].filter(opcao => opcao.innerText == texto)[0] || ''
	clicar(opcao)
}

async function pjeSelecionarOpcaoPorTexto(
	texto='',
	parcial=false
){
	if(!texto) return ''
	await esperar('mat-option',true,true)
	let opcao = [...document.querySelectorAll('mat-option')].filter(opcao => opcao.innerText == texto)[0] || ''
	if(!opcao){
		if(parcial) opcao = [...document.querySelectorAll('mat-option')].filter(opcao => opcao.innerText.includes(texto))[0] || ''
	}
	clicar(opcao)
	return opcao
}

function pjeObterProcessoId(){
	EXPRESSAO.processoId = new RegExp(/(processo.*?[/](audiencias|detalhe|documento|pericias|tarefa)|pjekz.gigs.abrir.gigs.*)/,'gi')
	let caminho = window.location.pathname.match(EXPRESSAO.processoId) || ''
	let id = ''
	if(!caminho) return id
	id = numeros(caminho.join()) || ''
	return id
}

function pjeObterProcessoDocumentoId(){
	EXPRESSAO.documentoId = new RegExp(/documento[/]\d+/,'gi')
	let caminho = window.location.pathname.match(EXPRESSAO.documentoId) || ''
	let id = ''
	if(!caminho) return id
	id = numeros(caminho.join()) || ''
	return id
}

function pjeObterMandadoId(){
	EXPRESSAO.mandadoId = new RegExp(/(centralmandados[/]mandados[/]\d+$)/,'gi')
	let caminho = window.location.pathname.match(EXPRESSAO.mandadoId) || ''
	let id = ''
	if(!caminho) return id
	id = numeros(caminho.join()) || ''
	return id
}

function obterDadosDoNumeroDoProcesso(numero){
	if(!numero) return ''
	let processo = {}
	processo.numeros = numeros(numero)
	if(numero.length === 25){
		let campos = numero.replace(/\D/g,'.').split('.')
		processo.ordenador = campos[0]
		processo.digito = campos[1]
		processo.ano = campos[2]
		processo.jurisdicao = campos[3]
		processo.tribunal = campos[4]
		processo.origem = campos[5]
	}
	if(processo.ordenador){
		let	paridade = Number(processo.ordenador) % 2
		if(paridade === 1) processo.paridade = 'ímpar'
		if(paridade === 0) processo.paridade = 'par'
	}
	if(processo.ordenador){
		let	final = processo.ordenador.substr(-1)
		processo.digitoFinal = final
	}
	return processo
}

function pjeSalvarDadosDoProcesso(){
	let id = 'json-dados-do-processo'
	let elemento = criar('meta',id,'',document.head)
	elemento.name = id
	elemento.content = JSON.stringify(PROCESSO)
}

async function pjeConsultarDetalhesDoProcesso(numero=''){
	if(!numero) return
	let dados = await pjeApiConsultaPublicaObterProcessoId(numero) || ''
	let id = dados[0]?.id || ''
	if(!id || !dados || dados?.codigoErro){
		pjeAbrirPaginaDeConsultProcessual(numero)
		return
	}
	let url = LINK.pje.processo + id + '/detalhe?janela=destacada'
	abrirPagina(url,'','','','','pjeDetalhes')
	esforcosPoupados(4,4,contarCaracteres(numero))
}

function pjeAbrirPainelDeConsultaProcessual(consulta = {}){
	if(vazio(consulta)) return
	let campo = Object.keys(consulta)[0]
	let conteudo = consulta[campo]
	let url = LINK.pje.consulta.processos + '?' + campo + '=' + conteudo
	abrirPagina(url,'','','','','pjePainel')
	esforcosPoupados(3,3,contarCaracteres(conteudo))
}

function pjeAbrirPaginaDeConsultaProcessual(numero=''){
	if(!numero) return
	let url = LINK.pje.painel.global + '?processo=' + numero
	abrirPagina(url,'','','','','pjePainel')
	esforcosPoupados(3,3,contarCaracteres(conteudo))
}

function pjeObterContexto(){
	if(JANELA.match(/processo[/]\d+[/]tarefa/i)){
		if(JANELA.includes('tarefa/545')) return 'pje-comunicacoes'
		if(JANELA.match(/processo[/]\d+[/]tarefa[/]\d+[/]registrar.transito.julgado/i)) return 'pje-tarefa-registrar-transito-julgado'
		return 'pje-tarefa'
	}
	if(JANELA.match(/processo[/]\d+[/]documento[/]anexar/i)) return 'pje-anexar'
	if(JANELA.match(/processo[/]\d+[/]audiencias/i)) return 'pje-audiencias'
	if(JANELA.includes('comunicacoesprocessuais')) return 'pje-comunicacoes'
	if(JANELA.match(/jus.br.consultaprocessual.detalhe.processo/i)) return 'pje-consulta-publica'
	if(JANELA.match(/navegador[/]processo[/]pagina[.]htm/i)) return 'pje-dados-do-processo'
	if(JANELA.match(/processo[/]\d+[/]detalhe/i)){
		if(JANELA.match(/[/]detalhe[/]calculo$/i)) return 'pje-calculo'
		return 'pje-detalhes'
	}
	if(JANELA.match(/processo[/]\d+[/]documento[/]\d+[/]conteudo/i)) return 'pje-documento'
	if(JANELA.includes('pjekz/assets/pdf/web/viewer.html?file=blob')) return 'pje-pdf'
	if(JANELA.match(/processo.*?tarefa.*?minutar/i)) return 'pje-editor'
	if(JANELA.match(/pjekz.gigs.abrir-gigs/i)) return 'pje-gigs'
	if(JANELA.match(/centralmandados[/]mandados[/]\d+$/i)) return 'pje-mandados'
	if(JANELA.match(/processo[/]\d+[/]pericias/i)) return 'pje-pericias'
	if(JANELA.match(/processo[/]\d+[/]retificar/i)) return 'pje-retificar'
	if(JANELA.match(/sif[/]consultar[/]\d+[/]saldo/i)) return 'pje-sif'
	if(JANELA.match(/primeirograu.Processo.ConsultaProcesso.Detalhe.list.seam/i)) return 'pje-versao1'
	return ''
}

function pjeObterDocumentoCabecalhoTexto(){
	let cabecalho = selecionar('.cabecalho-conteudo')
	if(!cabecalho) return ''
	return cabecalho.innerText || ''
}

function pjeObterDocumentoTitulo(){
	let titulo = selecionar('.cabecalho-conteudo mat-card-title')
	if(!titulo) return ''
	return titulo.innerText.trim() || ''
}

function pjeObterDocumentoId(){
	let texto = pjeObterDocumentoCabecalhoTexto()
	if(!texto) return ''
	let id = texto.match(/^Id\s.*?\s/g)
	if(!id) return ''
	return id.join().replace(/Id/g,'').trim() || ''
}

function pjeObterDocumentoLink(){
	let texto = pjeObterDocumentoCabecalhoTexto()
	if(!texto) return ''
	let link = texto.match(/http.*/gi)
	if(!link) return ''
	return link.join().trim() || ''
}

function pjeObterDocumentoData(){
	let texto = pjeObterDocumentoCabecalhoTexto()
	if(!texto) return ''
	return obterData(texto) || ''
}

function copiarDadosDoProcesso(){
	copiar(JSON.stringify(PROCESSO))
}

function pjeCriarBotaoFixoConfigurarDimensoesDaJanela(){
	pjeCriarBotaoFixo(
		'botao-dimensoes',
		'Definir dimensões padrão para a janela',
		() => {
			let descricao = ''
			let editar = ''
			let contexto = pjeObterContexto()
			if(contexto.includes('pje-anexar')){
				descricao = 'Anexar Documento'
				editar = 'pjeAnexar'
			}
			if(contexto.includes('pje-audiencias')){
				descricao = 'Audiências do Processo'
				editar = 'pjeAudiencias'
			}
			if(contexto.includes('pje-consulta-publica')){
				descricao = 'Consulta Pública'
				editar = 'pjeConsultaPublica'
			}
			if(contexto.includes('pje-dados-do-processo')){
				descricao = 'Dados do Processo'
				editar = 'pjeDados'
			}
			if(contexto.includes('pje-detalhes')){
				descricao = 'Detalhes do Processo'
				editar = 'pjeDetalhes'
			}
			if(contexto.includes('pje-documento')){
				descricao = 'Documento do Processo'
				editar = 'pjeDocumento'
			}
			if(contexto.includes('pje-gigs')){
				descricao = 'GIGS'
				editar = 'pjeGigs'
			}
			if(contexto.includes('pje-pericias')){
				descricao = 'Perícias do Processo'
				editar = 'pjePericias'
			}
			if(contexto.includes('pje-sif')){
				descricao = 'SIF'
				editar = 'sif'
			}
			if(contexto.includes('pje-tarefa')){
				descricao = 'Tarefa do Processo'
				editar = 'pjeTarefa'
			}
			if(contexto.includes('pje-versao1')){
				descricao = 'Versão 1 do Processo'
				editar = 'pjeLegado'
			}
			abrirPagina(caminho(`navegador/link/pagina.htm?editar=${editar}&descricao=${descricao}`),800,500,0,0,'link','popup')
		}
	)
}

function pjeCriarBotaoFixoCopiarNumeroDoProcesso(){
	pjeCriarBotaoFixo(
		'botao-copiar-numero-do-processo',
		'Copiar Número do Processo',
		() => {
			if(PROCESSO?.numero){
				copiar(PROCESSO.numero)
				esforcosPoupados(2,3)
			}
		}
	)
}


async function pjeCriarBotaoFixoCopiarDadosTabuladosDoProcesso(){
	pjeCriarBotaoFixo(
		'botao-copiar-dados-tabulados-do-processo',
		'Copiar Dados Tabulados do Processo',
		() => {
			let contexto = pjeObterContexto()
			let data = DATA?.hoje?.curta || ''
			let responsavel = CONFIGURACAO?.usuario?.nome || ''
			let processo = PROCESSO?.numero || ''
			let tarefa = PROCESSO?.tarefa?.nomeTarefa || ''
			let desde = PROCESSO?.data?.ultimoMovimento || DATA.hoje.curta || ''
			let fase = PROCESSO?.faseProcessual.trim().replace(/cao$/gi,'ção') || ''
			let poloPassivo = PROCESSO?.partes?.PASSIVO[0]?.nome?.trim() || ''
			let id = PROCESSO?.id || ''
			if(contexto.includes('pje-tarefa')){
				tarefa = 'Análise'
				data = 'FEITO	' + data
				pjeApiObterProcessoTarefaMaisRecente(id).then(
					dados => {
						let tarefaFinal = dados?.nomeTarefa?.trim() || ''
						poloPassivo = poloPassivo + '		' + tarefaFinal
						copiarLinha()
					}
				)
			}
			else copiarLinha()

			function copiarLinha(){
				let linha = pjeTabularLinha(data,responsavel,processo,tarefa,desde,fase,'','',poloPassivo) || ''
				copiar(linha)
				esforcosPoupados(14,21,14)
			}
		}
	)
}

function pjeCriarBotaoFixoDestacarDadosDoProcesso(){
	pjeCriarBotaoFixo('botao-dados-do-processo','Destacar dados do processo em uma nova janela',pjeDestacarDadosDoProcessoEmNovaJanela)
}

function pjeDestacarDadosDoProcessoEmNovaJanela(){
	let dados = {}
	dados.mandado = {}
	dados.orgaoJulgador = {}
	dados.mandado.id = pjeObterDocumentoId()
	dados.mandado.data = pjeObterDocumentoData()
	dados.orgaoJulgador.descricao = PROCESSO?.orgaoJulgador?.descricao || ''
	dados.id = PROCESSO?.id || ''
	dados.numero = PROCESSO?.numero || ''
	dados.partes = PROCESSO?.partes || ''
	dados.valor = PROCESSO?.valor || ''
	if(PROCESSO?.autuadoEm) dados.autuadoEm = new Date(PROCESSO?.autuadoEm)?.toLocaleDateString() || ''
	abrirPagina(caminho('navegador/processo/pagina.htm')+'?processo='+encodeURIComponent(JSON.stringify(dados)),'','','','','pjeDados')
}

function pjeCriarBotaoFixoCopiarIdDoDocumento(){
	pjeCriarBotaoFixo('botao-copiar-id-do-documento','Copiar Id do Documento',
		() => {
			copiar(' (Id ' + pjeObterDocumentoId() + ')')
			esforcosPoupados(1,2)
		}
	)
}

function pjeCriarBotaoFixoCopiarDataDoDocumento(){
	pjeCriarBotaoFixo('botao-copiar-data-do-documento','Copiar Data do Documento',
		() => {
			copiar(pjeObterDocumentoData())
			esforcosPoupados(1,2)
		}
	)
}

function pjeCriarBotaoFixoCopiarLinkDoDocumento(){
	pjeCriarBotaoFixo(
		'botao-copiar-link-do-documento','Copiar Link do Documento',
		() => {
			copiar(pjeObterDocumentoLink())
			esforcosPoupados(1,2)
		}
	)
}

function pjeCriarBotaoFixoEnviarDocumentoPorEmail(){
	let botao = pjeCriarBotaoFixo('botao-enviar-documento-por-email','Enviar Documento por E-Mail',
		() => {
			emailEscreverBaixarDocumentoAtivo()
			setTimeout(pjeCertificarEmailEnviado,2000)
		}
	)
	botao.classList.add('webmail')
}

function pjeCriarBotaoFixoCitacaoPorEmail(rotulo){
	let botao = pjeCriarBotaoFixo('botao-enviar-documento-por-email-citacao','Citação por E-Mail de ' + rotulo,
		() => emailEscreverCitacaoBaixarDocumento(pjeCertificarCitacaoPorEmail)
	)
	botao.classList.add('webmail-citacao')
}

function pjeCriarBotaoFixoCitacaoEspecialPorEmail(rotulo){
	if(!CONFIGURACAO?.usuario?.email?.includes('sisenandosousa@trt15.jus.br')) return

	let botao = pjeCriarBotaoFixo('botao-enviar-documento-por-email-citacao-especial','Citação Especial por E-Mail de ' + rotulo,
		() => {
			pjeDocumentoEmailEscreverNotificacaoBaixarDocumento('Nos termos do Provimento GP-CR 4/2021 do Tribunal Regional do Trabalho da 15ª Região, Sua Pessoa está sendo citada para, no prazo de 30 dias, apresentar sua contestação à petição inicial no processo acima referenciado. No mesmo ato, deverá apresentar todos os documentos requisitados na petição inicial. A petição pode ser acessada pelo link acima informado.',pjeAbrirComunicacoes)
		}
	)
	botao.classList.add('webmail-citacao-especial')
}

function pjeCriarBotaoFixoNotificarAudienciaPorEmail(rotulo){
	let botao = pjeCriarBotaoFixo('botao-enviar-documento-por-email-audiencia','Notificação de Audiência por E-Mail de ' + rotulo,
		() => emailEscreverNotificacaoAudienciaBaixarDocumento(pjeCertificarNotificacaoDeAudienciaPorEmail)
	)
	botao.classList.add('webmail-audiencia')
}

function pjeCriarBotaoFixoNotificacaoInicialPorEmail(rotulo){
	let botao = pjeCriarBotaoFixo('botao-enviar-documento-por-email-notificacao-inicial','Notificação Inicial por E-Mail de ' + rotulo,
		() => emailEscreverNotificacaoInicialBaixarDocumento(pjeCertificarNotificacaoInicialPorEmail)
	)
	botao.classList.add('webmail-inicial')
}

function pjeCriarBotaoFixoNotificacaoSentencaPorEmail(rotulo){
	let botao = pjeCriarBotaoFixo('botao-enviar-documento-por-email-notificacao-sentenca','Notificação de Sentença por E-Mail de ' + rotulo,
		() => emailEscreverNotificacaoSentencaBaixarDocumento(pjeCertificarNotificacaoSentencaPorEmail)
	)
	botao.classList.add('webmail-sentenca')
}

function pjeCriarBotaoFixoEnviarDocumentoPorWhatsapp(){
	let botao = pjeCriarBotaoFixo('botao-enviar-documento-por-whatsapp','Enviar Documento por WhatsApp',whatsappMontarMensagem)
	botao.classList.add('whatsapp')
}

function pjeCriarBotaoFixoNotificar(){
	let botao = pjeCriarBotaoFixo('botao-documento-notificar','Notificar',
		() => {
			clicar('#avjt-botao-copiar-link-do-documento')
			pjeAbrirComunicacoes('')
		}
	)
	botao.classList.add('comunicacoes')
}

function pjeCriarBotaoFixo(
	id = '',
	legenda = '',
	aoClicar = ''
){
	let botao = criarBotao('avjt-'+id,'avjt-botao-fixo informacoes','','',legenda,aoClicar)
	if(id.includes('documento')) botao.classList.add('avjt-botao-documento')
	if(id.includes('copiar')){
		botao.addEventListener('click',() => {
			botao.classList.toggle('copiado')
			setTimeout(() => botao.classList.toggle('copiado'),1000)
		})
	}
	return botao
}

function obterPoloAtivo(texto){
	let polo = texto.replace(/\s+x\s+.*/gi,'') || ''
	if(polo) polo = maiusculas(polo)
	return polo.trim()
}

function obterPoloPassivo(texto){
	let polo = texto.replace(/^.*?\s+x\s+/gi,'') || ''
	if(polo) polo = maiusculas(polo)
	return polo.trim()
}

function pjeConsultaPublicaProcessoInstancia(
	processo = '',
	instancia = '1'
){
	if(!processo) return
	let url = LINK.pje.consulta.instancia2 + encodeURI(processo) + '/' + instancia
	abrirPagina(url,'','','','','pjeConsultaPublica')
	esforcosPoupados(1,1,contarCaracteres(processo))
}

function pjeFiltrarDocumentosDoProcessoPorTipo(tipo){
	if(!PROCESSO.documentos) return []
	let lista = PROCESSO.documentos.reverse() || ''
	if(!lista) return []
	let documentos = lista.filter(item => item.tipo.includes(tipo))
	return documentos || []
}

function pjeAbrirDocumentoEmNovaPagina(
	id,
	largura,
	altura,
	horizontal,
	vertical
){
	let url = LINK.pje.processo + PROCESSO.id + '/documento/' + id + '/conteudo'
	esforcosPoupados(1,3)
	abrirPagina(url,largura,altura,horizontal,vertical)
}

function pjeAoAbrirDetalhesDoProcessoConsultarDepositosJudiciais(){
	if(CONFIGURACAO?.pjeAoAbrirDetalhesDoProcesso?.sifConsultar) pjeAbrirSif()
	if(CONFIGURACAO?.pjeAoAbrirDetalhesDoProcesso?.siscondjConsultar) siscondjConsultarProcesso(PROCESSO.numero)
	if(CONFIGURACAO?.pjeAoAbrirDetalhesDoProcesso?.bbConsultar) bbConsultarProcesso(PROCESSO.numero)
	if(CONFIGURACAO?.pjeAoAbrirDetalhesDoProcesso?.cefDepositosJudiciaisConsultar) cefConsultarDepositosJudiciaisProcesso(PROCESSO.numero)
	if(CONFIGURACAO?.pjeAoAbrirDetalhesDoProcesso?.cefDepositosRecursaisConsultar) cefConsultarDepositosRecursaisPorNomeDoPoloAtivo(PROCESSO.numero)
}

function pjeAoAbrirDetalhesDoProcessoAbrirDocumentos(){
	let contexto = pjeObterContexto()
	if(!contexto.includes('pje-detalhes')) return
	let largura 		=	obterDimensao(CONFIGURACAO?.janela?.pjeDocumento?.l,850)
	let altura			=	obterDimensao(CONFIGURACAO?.janela?.pjeDocumento?.a,850)
	let horizontal	=	obterDimensao(CONFIGURACAO?.janela?.pjeDocumento?.h,50)
	let vertical		=	obterDimensao(CONFIGURACAO?.janela?.pjeDocumento?.v,0)
	abrirPeticaoInicial()
	abrirUltimaAtaDeAudiencia()
	abrirAtasDeAudiencia()
	abrirSentencas()
	abrirAcordaos()
	abrirRecursosOrdinarios()
	abrirAgravosDePeticao()
	abrirAgravosDeInstrumento()

	function obterDimensao(dado,padrao){
		if(dado) return Number(dado.trim())
		return Number(padrao)
	}

	function abrirPeticaoInicial(){
		if(!CONFIGURACAO?.pjeAoAbrirDetalhesDoProcesso?.abrirPeticaoInicial) return
		if(!PROCESSO?.peticaoInicial) return
		PROCESSO.peticaoInicial.forEach(documento => {
			pjeAbrirDocumentoEmNovaPagina(documento.id,largura,altura,horizontal,vertical)
			horizontal	+= 100
			vertical		+= 50
		})
	}

	function abrirUltimaAtaDeAudiencia(){
		if(!CONFIGURACAO?.pjeAoAbrirDetalhesDoProcesso?.abrirUltimaAtaDeAudiencia) return
		if(!PROCESSO?.atas) return
		let atas = PROCESSO.atas.reverse()
		let ultimaAta = atas[0] || ''
		if(!ultimaAta) return
		horizontal += 100
		vertical = 0
		pjeAbrirDocumentoEmNovaPagina(atas[0].id,largura,altura,horizontal,vertical)
	}

	function abrirAtasDeAudiencia(){
		if(!CONFIGURACAO?.pjeAoAbrirDetalhesDoProcesso?.abrirAtasDeAudiencia) return
		if(!PROCESSO?.atas) return
		horizontal += 100
		vertical = 0
		PROCESSO.sentencas.forEach(documento => {
			pjeAbrirDocumentoEmNovaPagina(documento.id,largura,altura,horizontal,vertical)
			horizontal	+= 100
			vertical		+= 50
		})
	}

	function abrirSentencas(){
		if(!CONFIGURACAO?.pjeAoAbrirDetalhesDoProcesso?.abrirSentencas) return
		if(!PROCESSO?.sentencas) return
		horizontal += 100
		vertical = 0
		PROCESSO.sentencas.forEach(documento => {
			pjeAbrirDocumentoEmNovaPagina(documento.id,largura,altura,horizontal,vertical)
			horizontal	+= 100
			vertical		+= 50
		})
	}

	function abrirAcordaos(){
		if(!CONFIGURACAO?.pjeAoAbrirDetalhesDoProcesso?.abrirAcordaos) return
		if(!PROCESSO?.acordaos) return
		horizontal += 100
		vertical = 0
		PROCESSO.acordaos.forEach(documento => {
			pjeAbrirDocumentoEmNovaPagina(documento.id,largura,altura,horizontal,vertical)
			horizontal	+= 100
			vertical		+= 50
		})
	}

	function abrirRecursosOrdinarios(){
		if(!CONFIGURACAO?.pjeAoAbrirDetalhesDoProcesso?.abrirRecursosOrdinarios) return
		if(!PROCESSO?.recursos) return
		horizontal += 100
		vertical = 0
		PROCESSO.recursos.forEach(documento => {
			pjeAbrirDocumentoEmNovaPagina(documento.id,largura,altura,horizontal,vertical)
			horizontal	+= 100
			vertical		+= 50
		})
	}

	function abrirAgravosDePeticao(){
		if(!CONFIGURACAO?.pjeAoAbrirDetalhesDoProcesso?.abrirAgravosDePeticao) return
		if(!PROCESSO?.agravos) return
		horizontal += 100
		vertical = 0
		PROCESSO.agravos.forEach(documento => {
			if(!documento.tipo.includes('Petição')) return
			pjeAbrirDocumentoEmNovaPagina(documento.id,largura,altura,horizontal,vertical)
			horizontal	+= 100
			vertical		+= 50
		})
	}

	function abrirAgravosDeInstrumento(){
		if(!CONFIGURACAO?.pjeAoAbrirDetalhesDoProcesso?.abrirAgravosDeInstrumento) return
		if(!PROCESSO?.agravos) return
		horizontal += 100
		vertical = 0
		PROCESSO.agravos.forEach(documento => {
			if(!documento.tipo.includes('Instrumento')) return
			pjeAbrirDocumentoEmNovaPagina(documento.id,largura,altura,horizontal,vertical)
			horizontal	+= 100
			vertical		+= 50
		})
	}
}

async function pjeRemoverChip(texto){
	let chip = texto.trim() || ''
	if(!chip) return
	clicar('button[name="Remover Chip '+chip+'"]')
	let botao = await esperar('ng-component button')
	if(!botao) return
	clicar(botao)
}

async function pjeGigsFecharMensagensDeConclusao(){
	if(!CONFIGURACAO?.pje?.gigsFecharMensagensConclusao) return
	let observador = new MutationObserver(() => {
		let observado = selecionar('mat-dialog-container')
		if(!observado) return
		if(observado.textContent.includes('Tem certeza que deseja concluir a atividade')){
			esperar('[mattooltip="Salva as alterações"]',true,true).then(botao => {
				setTimeout(() => clicar(botao),250)
			})
		}
	})
	observador.observe(document.body,{childList:true,subtree:true,attributes:true,characterData:false})
}

async function pjeGigsFecharMensagensDeExclusao(){
	if(!CONFIGURACAO?.pje?.gigsFecharMensagensExclusao) return
	let observador = new MutationObserver(() => {
		let observado = selecionar('mat-dialog-container')
		if(!observado) return
		let texto = observado.textContent || ''
		if(texto.includes('Deseja realmente excluir a atividade')	|| texto.includes('Deseja realmente excluir este Lembrete') || texto.includes('Tem certeza que deseja remover o comentário')){
			esperar('mat-dialog-container button',true,true).then(botao => {
				setTimeout(() => clicar(botao),250)
			})
		}
	})
	observador.observe(document.body,{childList:true,subtree:true,attributes:true,characterData:false})
}

function pjeModalIncluirChipsOtimizarlayout(){
	if(!CONFIGURACAO?.pje?.chipsCentralizarBotoes) return
	estilizar('',
	`pje-inclui-etiquetas-dialogo .container-botoes {
		position:fixed;
		top:calc(50vh - 0.5em);
		right:calc(50vw - 200px);
		margin:0;
		width: auto !important;
	}`,
	'avjt-estilo-modal-incluir-chips')
}

async function pjePericiasFecharMensagensDeConclusao(){
	if(!CONFIGURACAO?.pje?.gigsFecharMensagensConclusao) return
	let observador = new MutationObserver(() => {
		let observado = selecionar('mat-dialog-container .icone-sucesso')
		if(!observado) return
		if(observado.parentElement.textContent.includes('Documento assinado com sucesso')){
			let botao = observado.parentElement.parentElement.parentElement.querySelector('button') || ''
			if(!botao) return
			clicar(botao)
		}
	})
	observador.observe(document.body,{childList:true,subtree:true,attributes:true,characterData:false})
}

async function pjeObterDadosDoProcessoPorNumeroSemSeparadores(){
	let numeroDoProcessoSemSeparadores = obterNumeroDoProcessoSemSeparadores(JANELA)
	let numeroDoProcessoPadraoCNJ = converterNumeroDoProcessoSemSeparadoresParaPadraoCNJ(numeroDoProcessoSemSeparadores)
	let dados = await pjeApiConsultaPublicaObterProcessoId(numeroDoProcessoPadraoCNJ)
	let processo = dados[0]
	Object.assign(processo,obterDadosDoNumeroDoProcesso(processo.numero))
	return processo
}

function pjeMomentoAdmissibilidadeRecursal(){
	let chips = PROCESSO.chips || ''
	if(!chips) return false
	if(vazio(chips)) return false
	if(chips.includes('Admissibilidade - RO') || chips.includes('Admissibilidade - RAd') || chips.includes('Admissibilidade - AP')) return true
	return false
}

function pjeMomentoTutelaLiminar(){
	let chips = PROCESSO.chips || ''
	if(!chips) return false
	if(vazio(chips)) return false
	if(chips.includes('Tutela/ Liminar')) return true
	return false
}

function pjeMomentoDespachar(){
	let ultimoDocumento = PROCESSO?.ultimoDocumento || ''
	if(!ultimoDocumento) return false
	let tipo = ultimoDocumento?.tipo || ''
	if(!tipo) return false
	if(tipo.includes('Contestação') || tipo.includes('Réplica') || tipo.includes('Apresentação de Laudo Pericial') || tipo.includes('Apresentação de Esclarecimentos ao Laudo Pericial')){
		let contexto = pjeObterContexto()
		if(contexto.includes('pje-calculo')) return false
		return true
	}
	return false
}

function processoObterVariavel(variavel=''){
	let partes = variavel.split('.')
	let objeto = PROCESSO || window
	for(var i=0;i<partes.length;i+=1){
		if(objeto[partes[i]]) objeto = objeto[partes[i]]
		else if(i >= partes.length - 1) return ''
	}
	return objeto
}

function obterProcessoVariavel(texto=''){
	let variavel = texto.match(EXPRESSAO.processoVariavel) || ''
	if(!variavel) return ''
	return variavel[0].trim() || ''
}

//Secretarias Conjuntas:

async function pjeConsultarProcesso(
	numero='',
	evento=''
){
	if(!numero) return
	if(evento.ctrlKey)
		pjeConsultarProcessoNoPainel(numero)
	else
		pjeConsultarDetalhesDoProcesso(numero)
}


async function pjeConsultarProcessoNoPainel(numero=''){
	if(!numero) return
	let dados = await pjeApiConsultaPublicaObterProcessoId(numero) || ''
	let id = dados[0]?.id || ''
	if(!id || !dados || dados?.codigoErro){
		pjeAbrirPaginaDeConsultProcessual(numero)
		return
	}
	let url = LINK.pje.processo + id + '/detalhe?janela=destacada&avjt=AbrirPainelDoOrgaoJulgador'
	abrirPagina(url,'','','','','pjeDetalhes')
	esforcosPoupados(4,4,contarCaracteres(numero))
	
}


//	await fetch("https://pje.trt15.jus.br/pje-seguranca/api/token/perfis/favoritos", {
//	    "credentials": "include",
//	    "headers": {
//	        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0",
//	        "Accept": "application/json, text/plain, */*",
//	        "Accept-Language": "pt-BR",
//	        "X-XSRF-TOKEN": "F7E45D8B10E994F588F2BC6505C719DA744FF49D6EE3A6477E55D9D080C21D9F8A79618A8A8D03B8E39D0AE5B08EF54F5214",
//	        "Content-Type": "application/json",
//	        "Sec-Fetch-Dest": "empty",
//	        "Sec-Fetch-Mode": "cors",
//	        "Sec-Fetch-Site": "same-origin",
//	        "Priority": "u=0"
//	    },
//	    "referrer": "https://pje.trt15.jus.br/pjekz/painel/global/todos/lista-processos/0011667-02.2023.5.15.0012?orgaoJulgador=345",
//	    "body": "{\"id_perfil\":472411}",
//	    "method": "PATCH",
//	    "mode": "cors"
//	});
