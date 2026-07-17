/**
 * VARIÁVEIS GLOBAIS, DISPONÍVEIS PARA TODAS AS FUNÇÕES:
 */
var
	CONFIGURACAO = {},
	CONTEXTO = '',
	DATA = definirDatas(),
	ESFORCOS = {},
	EXPRESSAO = definirExpressoesRegulares(),
	EXTENSAO = browser.runtime.getManifest(),
	JANELA = window.location.href || '',
	LINK = {},
	MODO = definirModo(),
	PCD = '',
	PROCESSO = {},
	TAREFA = {},
	TEXTO = document.body.textContent || ''

async function definicoesGlobais(){
	ESFORCOS = definirEsforcosRepetitivos()
	LINK = definirLinks()
	CONTEXTO = definirContexto()
	definirChavesPrimariasDoArmazenamento()
	//MODO.relatar = true
	relatar('CONFIGURACAO:',CONFIGURACAO)
	MODO.relatar = false
	relatar('DATA:',DATA)
	relatar('ESFORCOS:',ESFORCOS)
	relatar('EXTENSAO:',EXTENSAO)
	relatar('LINK:',LINK)
	relatar('MODO:', MODO)

	async function definirChavesPrimariasDoArmazenamento(){
		if(!CONFIGURACAO?.assistenteDeSelecao) await browser.storage.local.set({assistenteDeSelecao:{}})
		if(!CONFIGURACAO?.assistentesEspecializados) await browser.storage.local.set({assistentesEspecializados:{}})
		if(!CONFIGURACAO?.certidoes) await browser.storage.local.set({certidoes:[]})
		if(!CONFIGURACAO?.delegacoes)	await browser.storage.local.set({delegacoes:{}})
		if(!CONFIGURACAO?.diagnostico) await browser.storage.local.set({diagnosticar:false})
		if(!CONFIGURACAO?.esforcos) await browser.storage.local.set({esforcos:{}})
		if(!CONFIGURACAO?.gigs) await browser.storage.local.set({gigs:[]})
		if(!CONFIGURACAO?.instituicao) await browser.storage.local.set({instituicao:{}})
		if(!CONFIGURACAO?.janela) await browser.storage.local.set({janela:{}})
		if(!CONFIGURACAO?.lgpd) await browser.storage.local.set({lgpd:{}})
		if(!CONFIGURACAO?.pje) await browser.storage.local.set({pje:{}})
		if(!CONFIGURACAO?.pjeAoAbrirDetalhesDoProcesso) await browser.storage.local.set({pjeAoAbrirDetalhesDoProcesso:{}})
		if(!CONFIGURACAO?.pjeAoAbrirTarefaDoProcesso) await browser.storage.local.set({pjeAoAbrirTarefaDoProcesso:{}})
		if(!CONFIGURACAO?.pjeAssistentesDocumentosNotificacoes) await browser.storage.local.set({pjeAssistentesDocumentosNotificacoes:{}})
		if(!CONFIGURACAO?.pjeMagistrados) await browser.storage.local.set({pjeMagistrados:{}})
		if(!CONFIGURACAO?.pjeMenu) await browser.storage.local.set({pjeMenu:{}})
		if(!CONFIGURACAO?.sif) await browser.storage.local.set({sif:{}})
		if(!CONFIGURACAO?.siscondj) await browser.storage.local.set({siscondj:{}})
		if(!CONFIGURACAO?.texto) await browser.storage.local.set({texto:{}})
		if(!CONFIGURACAO?.usuario) await browser.storage.local.set({usuario:{}})
		if(!CONFIGURACAO?.pcd) await browser.storage.local.set({pcd:false})
	}
}

function definirModo(){
	let modo = {}
	modo.relatar = false
	return modo
}

function definirDatas(){
	let agora = new Date()
	let data = {}
	data.hoje = {}
	data.mesAnterior = {}
	data.hoje.curta = agora.toLocaleDateString()
	data.hoje.dia = agora.getDate()
	data.hoje.ano = agora.getFullYear()
	data.hoje.mes = Number(agora.getMonth()) + 1
	data.hoje.mais30dias = somarDias(agora,30)
	data.mesAnterior.primeiroDia = mesAnteriorPrimeiroDia(agora)
	data.mesAnterior.ultimoDia = mesAnteriorUltimoDia(agora)
	return data

	function somarDias(data,dias){
		let resultado = new Date(data)
		resultado.setDate(resultado.getDate() + dias)
		return resultado?.toLocaleDateString() || ''
	}

	function mesAnteriorPrimeiroDia(data=''){
		if(!data) data = new Date()
		let resultado = new Date(data)
		resultado.setDate(0)
		resultado.setDate(1)
		return resultado?.toLocaleDateString() || ''
	}

	function mesAnteriorUltimoDia(data=''){
		if(!data) data = new Date()
		let resultado = new Date(data)
		resultado.setDate(0)
		return resultado?.toLocaleDateString() || ''
	}
}

function definirEsforcosRepetitivos(){
	let esforcos = {}
	esforcos.cliques = Number(0)
	esforcos.movimentos = Number(0)
	esforcos.teclas = Number(0)
	browser.storage.local.get(
		['esforcos'],
		armazenamento => {
			if(vazio(armazenamento)){
				esforcos.data = DATA.hoje.curta
				browser.storage.local.set({esforcos})
			}
		}
	)
	return esforcos
}

function definirExpressoesRegulares(){
	let expressao = {}
	expressao.bbContaJudicial = new RegExp(/\d{9,19}[-]0/g)
	expressao.chassi = new RegExp(/(?![IOQ])[A-Za-z0-9]{17}/g)
	expressao.cnpj = new RegExp(/\d{2}[.]\d{3}[.]\d{3}[/]\d{4}[-]\d{2}/g)
	expressao.cpf = new RegExp(/\d{3}[.]\d{3}[.]\d{3}[-]\d{2}/g)
	expressao.data = new RegExp(/\d{2}[/]\d{2}[/]\d{4}/g)
	expressao.hora = new RegExp(/\d{2}[:]\d{2}/g)
	expressao.correiosObjeto = new RegExp(/[A-Za-z]{2}\d{9}[A-Za-z]{2}/gi)
	expressao.email = new RegExp(/^(([^<>()\[\]\\.,;:\s@"]+(\.[^<>()\[\]\\.,;:\s@"]+)*)|(".+"))@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}])|(([a-zA-Z\-0-9]+\.)+[a-zA-Z]{2,}))$/gi)
	expressao.nomeCompleto = new RegExp(/\b\w+\b\s.*/g)
	expressao.pje = new RegExp(/pje[.].*?[.]jus[.]br/gi)
	expressao.prazo = new RegExp(/(prazo).*?(de).*?((dia|hora)(s))/gi)
	expressao.processoNumero = new RegExp(/\d{7}\D\d{2}\D\d{4}\D\d{1}\D\d{2}\D\d{4}/)
	expressao.processoNumeroParcial = new RegExp(/\d{1,7}\D\d{2}\D\d{4}/)
	expressao.processoNumeroSemSeparadores = new RegExp(/\d{20}/g)
	expressao.processoVariavel = new RegExp(/PROCESSO[.].*/)
	expressao.quebraDeLinha = new RegExp(/(\r\n|\n|\r)/gi)
	expressao.valorMonetario = new RegExp(/\d.*?[,]\d{2}/gi)
	return expressao
}

function definirLinks(){
	let link = {}
	link.extensao = 'https://addons.mozilla.org/pt-BR/firefox/addon/assistentevirtual-justrabalho'
	link.github = EXTENSAO.homepage_url
	link.cndt = 'https://cndt-certidao.tst.jus.br/inicio.faces?'
	link.egestao = 'https://novoegestao.tst.jus.br/'
	link.maloteDigital = 'https://malotedigital.jt.jus.br/'
	link.roadmap = 'https://docs.google.com/spreadsheets/d/1dfHbdPGj2RxxtJJZnQiiZKTZw5HHRJPxvTSz_2vUPFM/'
	link.sisbajud = 'https://sisbajud.cnj.jus.br/'
	link.telegram = 'https://t.me/+MHR4lGArgvM1NDYx'
	link.transparencia = 'https://portaldatransparencia.gov.br/busca?termo='
	link.wikivt = 'https://fluxonacional.jt.jus.br/'
	link.youtube = 'https://www.youtube.com/channel/UCG0r5f3lk6AqDsEaZqzFzxQ'
	link.zoom = 'https://zoom.us'
	link.bb = obterLinkBancoDoBasil()
	link.cef = obterLinkCaixaEconomicaFederal()
	link.correios = obterLinkCorreios()
	link.google = obterLinkGoogle()
	link.infojud = obterLinkInfojud()
	link.penhora = obterLinkPenhoraOnline()
	link.receitaFederal = obterLinkReceitaFederal()
	link.renajud = obterLinkRenajud()
	link.sigeo = obterLinkSigeo()
	link.sinesp = obterLinkSinesp()
	link.trt15 = obterLinkTrt15()
	link.tst = obterLinkTst()
	link.whatsapp = obterLinkWhatsapp()
	link.balcao = CONFIGURACAO?.janela?.balcao?.url		|| obterLinkDaMemoria('balcao',		'https://meet.google.com')
	link.planilha = CONFIGURACAO?.janela?.planilha?.url	|| obterLinkDaMemoria('planilha',	'https://docs.google.com/spreadsheets')
	link.webmail = CONFIGURACAO?.janela?.webmail?.url	|| obterLinkDaMemoria('webmail',	'https://mail.google.com')
	let dominioTribunal = obterDominioTribunal()
	if(dominioTribunal){
		link.chamado = CONFIGURACAO?.janela?.chamado?.url	|| obterLinkDaMemoria('chamado',	'https://assyst.'			+ dominioTribunal + '/assystnet/#services/314')
		link.garimpo = CONFIGURACAO?.janela?.garimpo?.url	|| obterLinkDaMemoria('garimpo',	'https://deposito.'		+ dominioTribunal)
		link.intranet = CONFIGURACAO?.janela?.intranet?.url	|| obterLinkDaMemoria('intranet',	'https://satelites.'	+ dominioTribunal + '/aplicacoesExtranet')
		link.tribunal = dominioTribunal
		link.pje = obterLinkPje()
		link.eCarta = obterLinkEcarta()
		link.siscondj = obterLinkSiscondj()
		link.tribunal = obterLinkTribunal()
	}
	return link

	function obterLinkTribunal(){
		let url = {}
		url.dominio = obterDominioTribunal()
		url.portal = montarUrl(url,'www')
		url.raiz = montarUrl(url)
		return url
	}

	function obterLinkEcarta(){
		let url = {}
		let tribunal = CONFIGURACAO?.instituicao?.tribunal || 15
		if(tribunal == '3') tribunal = 'mg'
		if(tribunal == '24') tribunal = 'ms'
		url.dominio = obterDominioTribunal()
		url.instalacao = 'eCarta-web'
		url.subdominio = 'ecarta'
		if(tribunal == '2') url.subdominio = 'aplicacoes1'
		if(tribunal == '13') url.subdominio = 'www'
		if(tribunal == '8' || tribunal == '12' || tribunal == '16' || tribunal == '21' || tribunal == '23') url.subdominio = 'pje'
		if(tribunal == '4' || tribunal == '5' || tribunal == '15') url.instalacao = ''
		url.raiz = montarUrl(url,url.subdominio,url.instalacao)
		url.consultarProcesso = url.raiz + '/consultarProcesso.xhtml?codigo='
		url.detalhesObjeto = url.raiz + '/impressaoDetalhesObjeto.xhtml?codigo='
		return url
	}

	function obterLinkSiscondj(){
		let url = {}
		let tribunal = CONFIGURACAO?.instituicao?.tribunal || 15
		if(tribunal == '3') tribunal = 'mg'
		if(tribunal == '24') tribunal = 'ms'
		url.dominio = obterDominioTribunal()
		url.instalacao = 'portaltrt' + tribunal
		url.subdominio = 'siscondj'
		if(tribunal == '1' || tribunal == '8' || tribunal == '11' || tribunal == '16' || tribunal == '21'){
			url.subdominio = 'pje'
			url.instalacao = 'siscondj'
		}
		if(tribunal == '2'){
			url.subdominio = 'alvaraeletronico'
			url.instalacao = 'portaltrtsp'
		}
		if(tribunal == '4'){
			url.subdominio = 'siscondj'
			url.instalacao = 'portaltrtrs'
		}
		if(tribunal == '6'){
			url.subdominio = 'pje'
			url.instalacao = 'siscondj'
		}
		if(tribunal == '7'){
			url.subdominio = 'pje'
			url.instalacao = 'siscondj'
		}
		if(tribunal == '5' || tribunal == '12' || tribunal == '23' || tribunal == '24'){
			url.subdominio = 'siscondj'
			url.instalacao = 'siscondj'
		}
		if(tribunal == '13'){
			url.subdominio = 'www'
			url.instalacao = 'siscondj'
		}
		if(tribunal == '14'){
			url.subdominio = 'pje'
			url.instalacao = 'siscondj'
		}
		if(tribunal == '18'){
			url.subdominio = 'sistemas'
			url.instalacao = 'siscondj'
		}
		if(tribunal == '22'){
			url.subdominio = 'aplicacoes'
			url.instalacao = 'siscondj'
		}
		url.raiz = montarUrl(url,url.subdominio,url.instalacao)
		url.consultarProcesso = url.raiz + '/pages/movimentacao/conta/new?numeroDoProcesso='
		return url
	}

	function obterLinkTrt15(){
		let url = {}
		url.dominio = 'trt15.jus.br'
		url.raiz = montarUrl(url)
		url.consultarProcesso = montarUrl(url,'consulta','consulta/owa/pProcesso.wFormProcessoNovoPortal?')
		url.consultarJurisprudencia = montarUrl(url,'jurisprudencia','?avjtConsulta=')
		return url
	}

	function montarUrl(
		url = '',
		subdominio = '',
		caminho = '',
		protocolo = 'https'
	){
		let endereco = ''
		if(subdominio) subdominio = subdominio + '.'
		if(caminho) caminho = '/' + caminho
		if(!subdominio) endereco = protocolo + '://' + url.dominio + caminho
		else endereco = protocolo + '://' + subdominio + url.dominio + caminho
		return endereco
	}

	function obterLinkWhatsapp(){
		let url = {}
		url.protocolo = 'whatsapp://send?phone='
		url.dominio = 'whatsapp.com'
		url.raiz = montarUrl(url)
		url.api = montarUrl(url,'api')
		url.chat = montarUrl(url,'chat')
		url.grupo = montarUrl(url,'chat')
		if(CONFIGURACAO?.instituicao?.tribunal?.includes('15')) url.grupo += '/DKcc9eecyAXBwzfgxOe1AI'
		else url.grupo += '/FSBJFsBEX8y2YmGGIqM35A'
		return url
	}

	function obterLinkGoogle(){
		let url = {}
		url.dominio = 'google.com'
		url.raiz = montarUrl(url)
		url.agenda = montarUrl(url,'calendar')
		url.drive = montarUrl(url,'drive')
		url.mail = montarUrl(url,'mail')
		url.meet = montarUrl(url,'meet')
		url.documents = montarUrl(url,'docs','document')
		url.planilhas = montarUrl(url,'docs','spreadsheets')
		url.tradutor = montarUrl(url,'translate','?sl=en&tl=pt&text=')
		return url
	}

	function obterLinkPenhoraOnline(){
		let url = {}
		url.dominio = 'penhoraonline.org.br'
		url.raiz = montarUrl(url)
		url.solicitar = montarUrl(url,'','frmHomeSolicitarCertidoes.aspx')
		url.respostas = montarUrl(url,'','Penhora/frmListaRespostasPenhora.aspx?ModuloChamado=consultarpedidosdepenhora&processo=')
		url.certidoes = montarUrl(url,'','Penhora/frmListaRespostasCertidoes.aspx?ModuloChamado=consultarpedidosdecertidao&processo=')
		return url
	}

	function obterLinkSinesp(){
		let url = {}
		url.dominio = 'sinesp.gov.br'
		url.raiz = montarUrl(url)
		url.infoseg = montarUrl(url,'infoseg','infoseg2/?q=')
		url.seguranca = montarUrl(url,'seguranca')
		return url
	}

	function obterLinkTst(){
		let url = {}
		url.dominio = 'tst.jus.br'
		url.raiz = montarUrl(url)
		url.consultarProcesso = montarUrl(url,'aplicacao4','consultaProcessual/consultaTstNumUnica.do?consulta=Consultar&conscsjt=','http')
		url.consultarJurisprudencia = montarUrl(url,'jurisprudencia','?avjtConsulta=')
		return url
	}

	function obterLinkDaMemoria(
		chave = '',
		url = ''
	){
		if(!chave || !url) return ''

		browser.storage.local.get('janela',armazenamento => {
			let objeto = armazenamento?.janela[chave] || {}
			let valor = objeto?.url || ''
			let link = valor || url
			if(!valor){
				let janela = armazenamento.janela
				janela[chave] = {url:link}
				browser.storage.local.set({janela})
				setTimeout(definicoesGlobais,100)
			}
		})
	}

	function obterLinkInfojud(){
		let url = {}
		url.dominio = 'receita.fazenda.gov.br'
		url.raiz = montarUrl(url)
		url.consultarDocumento = montarUrl(url,'cav','Servicos/ATSDR/Decjuiz/')
		url.consultarNomePessoaFisica = montarUrl(url,'cav','Servicos/ATSDR/Decjuiz/listaNICPF.asp?nome=')
		url.consultarNomePessoaJuridica = montarUrl(url,'cav','Servicos/ATSDR/Decjuiz/listaNICNPJ.asp?nomeEmpresarial=')
		url.servicos = montarUrl(url,'cav','ecac/Aplicacao.aspx?id=5032')
		url.solicitar = montarUrl(url,'cav','Servicos/ATSDR/Decjuiz/solicitacao.asp')
		url.sim = montarUrl(url,'servicos','Servicos/cnpjreva/cnpjreva_solicitacao.asp?cnpj=')
		return url
	}

	function obterLinkReceitaFederal(){
		let url = {}
		url.dominio = 'receita.fazenda.gov.br'
		url.raiz = montarUrl(url)
		url.consultarSimplesOptante = montarUrl(url,'consopt.www8','consultaoptantes')
		return url
	}

	function obterLinkRenajud(){
		let url = {}
		url.dominio = 'renajud.denatran.serpro.gov.br'
		url.raiz = montarUrl(url)
		url.inserir = montarUrl(url,'','renajud/restrito/restricoes-insercao.jsf')
		return url
	}

	function obterLinkSigeo(){
		let url = {}
		url.dominio = 'sigeo.jt.jus.br'
		url.raiz = montarUrl(url)
		url.portal = montarUrl(url,'portal')
		url.processo = montarUrl(url,'aj','aj/nomeacao/nomearprofissionais/nomearprofissionais_index.jsf?processo=')
		return url
	}

	function obterLinkBancoDoBasil(){
		let url = {}
		url.dominio = 'bb.com.br'
		url.depositos = {}
		url.depositos.magistrados = montarUrl(url,'www63','portalbb/djo/rdo/magistrado/RD02.bbx?')
		return url
	}

	function obterLinkCaixaEconomicaFederal(){
		let url = {}
		url.dominio = 'caixa.gov.br'
		url.depositos = {}
		url.depositos.login = montarUrl(url,'depositojudicial','sigsj_internet/login.xhtml?')
		url.depositos.judiciais = montarUrl(url,'depositojudicial','sigsj_internet/acesso-restrito/contas/consulta/consulta-avancada/index.xhtml?')
		url.depositos.recursais = montarUrl(url,'conectividadesocialv2','sicns')
		return url
	}

	function obterLinkCorreios(){
		let url = {}
		url.dominio = 'correios.com.br'
		url.rastrear = montarUrl(url,'rastreamento','app/index.php?avjtConsultarObjetoNosCorreios=')
		url.api = montarUrl(url,'rastreamento','app/dataMaxima.php?objeto=')
		return url
	}

	function obterLinkPje(){
		if(!CONFIGURACAO?.instituicao?.tribunal) return ''
		let raiz = CONFIGURACAO?.diagnostico?.pjeUrlRaiz || ''
		let url = {}
		url.api = {}
		url.consulta = {}
		url.painel = {}
		url.dominio = 'pje.' + obterDominioTribunal()
		url.raiz = 'https://' + url.dominio + '/'
		if(raiz) url.raiz = raiz + '/'
		url.kz = url.raiz + 'pjekz/'
		url.calc = url.raiz + 'pjecalc'
		url.legado = {}
		url.primeirograu = url.raiz + 'primeirograu/'
		url.segundograu = url.raiz + 'segundograu/'
		url.legado.painel = url.primeirograu + 'Painel/painel_usuario/list.seam'
		url.legado.processo = url.primeirograu + 'Processo/ConsultaProcesso/Detalhe/list.seam?id='
		url.consulta.advogado = url.primeirograu + 'PessoaAdvogado/ConfirmarCadastro/listView.seam'
		url.consulta.pessoa = url.primeirograu + 'ConsultaPessoa/listView.seam'
		url.consulta.instancia2 = url.raiz + 'consultaprocessual/detalhe-processo/'
		url.consulta.processos = url.raiz + 'administracao/consulta/processo/index'
		url.painel.gigs = url.kz + 'gigs/relatorios/atividades'
		url.painel.avisos = url.kz + 'quadro-avisos/visualizar'
		url.painel.global = url.kz + 'painel/global/todos/lista-processos/'
		url.pauta = url.kz + 'pauta-audiencias'
		url.modelos = url.kz + 'configuracao/modelos-documentos'
		url.processo = url.kz + 'processo/'
		url.api.administracao = url.raiz + 'pje-administracao-api/api/'
		url.api.comum = url.raiz + 'pje-comum-api/api/'
		url.api.consulta = url.raiz + 'pje-consulta-api/api/'
		url.api.etiquetas = url.raiz + 'pje-etiquetas-api/api/processos/'
		url.api.gigs = url.raiz + 'pje-gigs-api/api/'
		url.api.mandados = url.raiz + 'pje-centralmandados-api/api/'
		url.api.seguranca = url.raiz + 'pje-seguranca/api/'
		url.api.sif = url.raiz + 'sif-financeiro-api/api/'
		url.api.orgaoJulgadorAutenticado = url.api.comum + 'agrupamentotarefas/orgaojulgadores/todos'
		return url
	}
}


/**
 * REMOVE CHAVES ESPECÍFICAS DO ${browser.storage.local}, QUE ESTEJAM PRESENTES NA GLOBAL ${CONFIGURACAO}:
 * @param {Array}	chaves
 */
 function removerChavesDaMemoria(chaves = []){
	chaves.forEach(chave => {
		if(chave in CONFIGURACAO) browser.storage.local.remove(chave).then(() => aoFuncionar(chave),aoFalhar)
	})

	function aoFuncionar(chave){
		relatar('Chave removida: ',chave)
	}

	function aoFalhar(erro){
		relatar('Erro:',erro)
	}
}

function obterDominioTribunal(){
	if(CONFIGURACAO?.instituicao?.tribunal == undefined) return ''
	let sigla = obterSiglaTribunal()
	return minusculas(sigla) + '.jus.br'
}

function obterSiglaTribunal(){
	if(CONFIGURACAO?.instituicao?.tribunal == undefined) return ''
	let sigla = 'T'
	if(CONFIGURACAO.instituicao?.tribunal == '0') sigla += 'ST'
	else sigla += 'RT' + CONFIGURACAO.instituicao?.tribunal
	return sigla
}

function apiGooglePlanilhas(){
	return decodificar('065073122097083121065113117053078104088100068050087068108089095110066080116087055119057121071111105084069055107084052')
}

function definirContexto(){
	let contexto = ''
	if(JANELA.includes(LINK.bb.dominio)) contexto = 'bancoDoBrasil'
	console.info('CONTEXTO:',contexto)
	return contexto
}