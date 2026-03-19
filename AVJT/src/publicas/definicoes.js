/**
 * VARIÁVEIS GLOBAIS, DISPONÍVEIS PARA TODAS AS FUNÇÕES:
 */


var
	CONFIGURACAO = {},
	DATA = definirDatas(),
	EXPRESSAO = definirExpressoesRegulares(),
	EXTENSAO = browser.runtime.getManifest(),
	INFORMACOES = {},
	JANELA = window.location.href || '',
	LINK = {},
	MODO = definirModo(),
	PROCESSO = {},
	TAREFA = {},
	TEXTO = definirTextos(),
	TRIBUNAL = definirTRT(),
	VARAS = definirVaras()

function definirTRT(){
	let tribunal = {}
	tribunal.regiao = '15'
	tribunal.nome = 'Tribunal Regional do Trabalho da ' + tribunal.regiao + 'ª Região'
	return tribunal
}

async function definicoesGlobais(){

	definirChavesPrimariasDoArmazenamento()

	//	MODO.relatar = true
	LINK = definirLinks()

	relatar('CONFIGURACAO:',CONFIGURACAO) //CONTÉM TODO O STORAGE
	relatar('DATA:',DATA) //CONTÉM A DATA ATUAL
	relatar('EXTENSAO:',EXTENSAO) // CONTÉM TODAS AS VARIÁVEIS DO MANIFEST.JSON
	relatar('LINK:',LINK) //CONTÉM TODOS OS LINKS PADRÕES DA EXTENSÃO
	relatar('MODO:', MODO) //CONTÉM A CONFIGURAÇÃO PARA MUDANÇA DE MODO TESTE

	async function definirChavesPrimariasDoArmazenamento(){
		if(!CONFIGURACAO?.janela) await browser.storage.local.set({janela:{}})
		if(!CONFIGURACAO?.menuMovel) await browser.storage.local.set({menuMovel:{h:0,v:0}})
		if(!CONFIGURACAO?.usuario) await browser.storage.local.set({usuario:{}})
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
	data.agora = agora
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
	expressao.quebraDeLinha = new RegExp(/(\r\n|\n|\r)/gi)
	expressao.valorMonetario = new RegExp(/\d.*?[,]\d{2}/gi)

	return expressao

}


function definirLinks(){

	let link = {}

	link.egestao = 'https://novoegestao.tst.jus.br/'
	link.extensao = obterLinkExtensao()
	link.eCarta = obterLinkEcarta()
	link.eSincor = 'http://10.15.214.220/jasperserver'
	link.github = 'https://github.com/SisenandoCalixto/quinzinho/'
	link.google = obterLinkGoogle()
	link.pje = obterLinkPje()
	link.pjecor = 'https://corregedoria.pje.jus.br'
	link.tribunal = obterLinkTribunal()
	link.wikivt = 'https://fluxonacional.jt.jus.br/'

	return link

	function obterLinkExtensao(){
		let url = {}
		//url.lista = caminho('navegador/pje-lista/pagina.htm?lista=')
		return url
	}

	function obterLinkTribunal(){
		let url = {}
		url.dominio = obterDominioTribunal()
		url.cnc = montarUrl(url,'','institucional/corregedoria/consolidacao-das-normas-da-corregedoria')
		url.designacoes = montarUrl(url,'satelites','designacoes/index.jsp?tipoConsulta=21')
		url.exe15 = obterLinkExe15()
		url.intranet = montarUrl(url,'satelites','aplicacoesExtranet')
		url.portal = montarUrl(url)
		url.proad = montarUrl(url,'proad')
		url.sig = montarUrl(url,'sig')
		url.raiz = montarUrl(url)
		return url
	}
	
	function obterLinkExe15(){
		let url = {}
		url.dominio = 'trt15.jus.br'
		url.raiz = montarUrl(url,'satelites','nucleo_execucao')
		url.diligencias = montarUrl(url,'satelites','nucleo_execucao/f/t/consultardiligenciascon')
		return url
	}

	function obterLinkGoogle(){
		let usuario = CONFIGURACAO?.usuario?.email || '0'
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

	function obterLinkEcarta(){
		let url = {}
		url.dominio = obterDominioTribunal()
		url.instalacao = 'eCarta-web'
		url.subdominio = 'ecarta'
		url.raiz = montarUrl(url,url.subdominio,url.instalacao)
		url.consultarProcesso = url.raiz + '/consultarProcesso.xhtml?codigo='
		return url
	}

	function montarUrl(
		url = '',
		subdominio = '',
		caminho = '',
		protocolo = 'https'
	){
		if(subdominio) subdominio = subdominio + '.'
		return encodeURI(protocolo + '://' + subdominio + url.dominio + '/' + caminho)
	}


	function obterLinkPje(){

		let url = {}
		url.api = {}
		url.consulta = {}
		url.painel = {}

		url.dominio = 'pje.' + obterDominioTribunal()
		url.raiz = 'https://' + url.dominio + '/'
		url.kz = url.raiz + 'pjekz/'
		url.calc = url.raiz + 'pjecalc'
		url.legado = {}
		url.primeirograu = url.raiz + 'primeirograu/'
		url.segundograu = url.raiz + 'segundograu/'
		url.legado.painel = url.primeirograu + 'Painel/painel_usuario/list.seam'
		url.consulta.advogado = url.primeirograu + 'PessoaAdvogado/ConfirmarCadastro/listView.seam'
		url.consulta.pessoa = url.primeirograu + 'ConsultaPessoa/listView.seam'
		url.consulta.instancia2 = url.raiz + 'consultaprocessual/detalhe-processo/'
		url.consulta.processos = url.raiz + 'administracao/consulta/processo/index?pagina=1&tamanhoPagina=50000'
		url.consulta.processosTodos = url.consulta.processos + '?pagina=1&tamanhoPagina=50000&'
		url.painel.audiencias = url.kz + 'pauta-audiencias'
		url.painel.gigs = url.kz + 'gigs/relatorios/atividades'
		url.painel.global = url.kz + 'painel/global/'
		url.painel.pericias = url.kz + 'painel/pauta-pericias?situacao=D&situacao=M&situacao=A&situacao=L&situacao=P&situacao=S'
		url.pauta = url.kz + 'pauta-audiencias'
		url.modelos = url.kz + 'configuracao/modelos-documentos'
		url.processo = url.kz + 'processo/'
		url.api.administracao = url.raiz + 'pje-administracao-api/api/'
		url.api.comum = url.raiz + 'pje-comum-api/api/'
		url.api.consulta = url.raiz + 'pje-consulta-api/api/'
		url.api.etiquetas = url.raiz + 'pje-etiquetas-api/api/processos/'
		url.api.mandados = url.raiz + 'pje-centralmandados-api/api/'
		url.api.seguranca = url.raiz + 'pje-seguranca/api/'
		url.api.sif = url.raiz + 'sif-financeiro-api/api/'
		url.api.gigs = url.raiz + 'pje-gigs-api/api/'

		return url

	}

}


function definirTextos(){
	let texto = {}
	texto.autentique = 'Autentique-se no PJe para poder executar esta funcionalidade.'
	texto.permissoes = 'Verifique se o sistema está online e se as permissões de acesso a URLs foram concedidas.'
	return texto
}


function obterDominioTribunal(){
	return 'trt' + TRIBUNAL.regiao + '.jus.br'
}


function apiGooglePlanilhas(){
	return decodificar('065073122097083121068122090108069076085073107051120097050099108049101097067085056072052114079072104071083109099086111')
}


function definirVaras(){
	return [
		{
			"id": 37,
			"descricao": "Vara do Trabalho de Piedade",
			"sigla": "VT078",
			"unidade": "0078"
		},
		{
			"id": 39,
			"descricao": "Vara do Trabalho de Santa Bárbara D'Oeste",
			"sigla": "VT086",
			"unidade": "0086"
		},
		{
			"id": 40,
			"descricao": "Vara do Trabalho de Itatiba",
			"sigla": "VT145",
			"unidade": "0145"
		},
		{
			"id": 41,
			"descricao": "Vara do Trabalho de Capivari",
			"sigla": "VT039",
			"unidade": "0039"
		},
		{
			"id": 42,
			"descricao": "Vara do Trabalho de Hortolândia",
			"sigla": "VT152",
			"unidade": "0152"
		},
		{
			"id": 43,
			"descricao": "Vara do Trabalho de Campo Limpo Paulista",
			"sigla": "VT105",
			"unidade": "0105"
		},
		{
			"id": 44,
			"descricao": "Vara do Trabalho de Avaré",
			"sigla": "VT031",
			"unidade": "0031"
		},
		{
			"id": 45,
			"descricao": "Vara do Trabalho de Matão",
			"sigla": "VT081",
			"unidade": "0081"
		},
		{
			"id": 46,
			"descricao": "Vara do Trabalho de Araras",
			"sigla": "VT046",
			"unidade": "0046"
		},
		{
			"id": 47,
			"descricao": "Vara do Trabalho de Taquaritinga",
			"sigla": "VT142",
			"unidade": "0142"
		},
		{
			"id": 48,
			"descricao": "Vara do Trabalho de Leme",
			"sigla": "VT134",
			"unidade": "0134"
		},
		{
			"id": 49,
			"descricao": "Vara do Trabalho de Aparecida",
			"sigla": "VT147",
			"unidade": "0147"
		},
		{
			"id": 50,
			"descricao": "Vara do Trabalho de Itapira",
			"sigla": "VT118",
			"unidade": "0118"
		},
		{
			"id": 51,
			"descricao": "1ª Vara do Trabalho de Americana",
			"sigla": "VT007",
			"unidade": "0007"
		},
		{
			"id": 52,
			"descricao": "2ª Vara do Trabalho de Americana",
			"sigla": "VT099",
			"unidade": "0099"
		},
		{
			"id": 53,
			"descricao": "Vara do Trabalho de Adamantina",
			"sigla": "VT068",
			"unidade": "0068"
		},
		{
			"id": 54,
			"descricao": "Vara do Trabalho de Batatais",
			"sigla": "VT075",
			"unidade": "0075"
		},
		{
			"id": 55,
			"descricao": "Vara do Trabalho de Cajuru",
			"sigla": "VT112",
			"unidade": "0112"
		},
		{
			"id": 56,
			"descricao": "Vara do Trabalho de José Bonifácio",
			"sigla": "VT110",
			"unidade": "0110"
		},
		{
			"id": 57,
			"descricao": "1ª Vara do Trabalho de Lençóis Paulista",
			"sigla": "VT074",
			"unidade": "0074"
		},
		{
			"id": 58,
			"descricao": "2ª Vara do Trabalho de Lençóis Paulista",
			"sigla": "VT149",
			"unidade": "0149"
		},
		{
			"id": 59,
			"descricao": "Vara do Trabalho de São José do Rio Pardo",
			"sigla": "VT035",
			"unidade": "0035"
		},
		{
			"id": 60,
			"descricao": "1ª Vara do Trabalho de Piracicaba",
			"sigla": "VT012",
			"unidade": "0012"
		},
		{
			"id": 61,
			"descricao": "2ª Vara do Trabalho de Piracicaba",
			"sigla": "VT051",
			"unidade": "0051"
		},
		{
			"id": 62,
			"descricao": "3ª Vara do Trabalho de Piracicaba",
			"sigla": "VT137",
			"unidade": "0137"
		},
		{
			"id": 63,
			"descricao": "Vara do Trabalho de Amparo",
			"sigla": "VT060",
			"unidade": "0060"
		},
		{
			"id": 64,
			"descricao": "Vara do Trabalho de Andradina",
			"sigla": "VT056",
			"unidade": "0056"
		},
		{
			"id": 65,
			"descricao": "1ª Vara do Trabalho de Araçatuba",
			"sigla": "VT019",
			"unidade": "0019"
		},
		{
			"id": 66,
			"descricao": "2ª Vara do Trabalho de Araçatuba",
			"sigla": "VT061",
			"unidade": "0061"
		},
		{
			"id": 67,
			"descricao": "3ª Vara do Trabalho de Araçatuba",
			"sigla": "VT103",
			"unidade": "0103"
		},
		{
			"id": 68,
			"descricao": "1ª Vara do Trabalho de Araraquara",
			"sigla": "VT006",
			"unidade": "0006"
		},
		{
			"id": 69,
			"descricao": "2ª Vara do Trabalho de Araraquara",
			"sigla": "VT079",
			"unidade": "0079"
		},
		{
			"id": 70,
			"descricao": "3ª Vara do Trabalho de Araraquara",
			"sigla": "VT151",
			"unidade": "0151"
		},
		{
			"id": 71,
			"descricao": "1ª Vara do Trabalho de Assis",
			"sigla": "VT036",
			"unidade": "0036"
		},
		{
			"id": 72,
			"descricao": "2ª Vara do Trabalho de Assis",
			"sigla": "VT100",
			"unidade": "0100"
		},
		{
			"id": 73,
			"descricao": "Vara do Trabalho de Atibaia",
			"sigla": "VT140",
			"unidade": "0140"
		},
		{
			"id": 74,
			"descricao": "Vara do Trabalho de Barretos",
			"sigla": "VT011",
			"unidade": "0011"
		},
		{
			"id": 75,
			"descricao": "1ª Vara do Trabalho de Bauru",
			"sigla": "VT005",
			"unidade": "0005"
		},
		{
			"id": 76,
			"descricao": "2ª Vara do Trabalho de Bauru",
			"sigla": "VT089",
			"unidade": "0089"
		},
		{
			"id": 77,
			"descricao": "3ª Vara do Trabalho de Bauru",
			"sigla": "VT090",
			"unidade": "0090"
		},
		{
			"id": 78,
			"descricao": "4ª Vara do Trabalho de Bauru",
			"sigla": "VT091",
			"unidade": "0091"
		},
		{
			"id": 79,
			"descricao": "Vara do Trabalho de Bebedouro",
			"sigla": "VT058",
			"unidade": "0058"
		},
		{
			"id": 80,
			"descricao": "Vara do Trabalho de Birigui",
			"sigla": "VT073",
			"unidade": "0073"
		},
		{
			"id": 81,
			"descricao": "Vara do Trabalho de Botucatu",
			"sigla": "VT025",
			"unidade": "0025"
		},
		{
			"id": 82,
			"descricao": "Vara do Trabalho de Bragança Paulista",
			"sigla": "VT038",
			"unidade": "0038"
		},
		{
			"id": 83,
			"descricao": "Vara do Trabalho de Caçapava",
			"sigla": "VT119",
			"unidade": "0119"
		},
		{
			"id": 84,
			"descricao": "1ª Vara do Trabalho de Campinas",
			"sigla": "VT001",
			"unidade": "0001"
		},
		{
			"id": 85,
			"descricao": "2ª Vara do Trabalho de Campinas",
			"sigla": "VT032",
			"unidade": "0032"
		},
		{
			"id": 86,
			"descricao": "3ª Vara do Trabalho de Campinas",
			"sigla": "VT043",
			"unidade": "0043"
		},
		{
			"id": 87,
			"descricao": "4ª Vara do Trabalho de Campinas",
			"sigla": "VT053",
			"unidade": "0053"
		},
		{
			"id": 88,
			"descricao": "5ª Vara do Trabalho de Campinas",
			"sigla": "VT092",
			"unidade": "0092"
		},
		{
			"id": 89,
			"descricao": "6ª Vara do Trabalho de Campinas",
			"sigla": "VT093",
			"unidade": "0093"
		},
		{
			"id": 90,
			"descricao": "7ª Vara do Trabalho de Campinas",
			"sigla": "VT094",
			"unidade": "0094"
		},
		{
			"id": 91,
			"descricao": "8ª Vara do Trabalho de Campinas",
			"sigla": "VT095",
			"unidade": "0095"
		},
		{
			"id": 92,
			"descricao": "9ª Vara do Trabalho de Campinas",
			"sigla": "VT114",
			"unidade": "0114"
		},
		{
			"id": 93,
			"descricao": "10ª Vara do Trabalho de Campinas",
			"sigla": "VT129",
			"unidade": "0129"
		},
		{
			"id": 94,
			"descricao": "11ª Vara do Trabalho de Campinas",
			"sigla": "VT130",
			"unidade": "0130"
		},
		{
			"id": 95,
			"descricao": "12ª Vara do Trabalho de Campinas",
			"sigla": "VT131",
			"unidade": "0131"
		},
		{
			"id": 96,
			"descricao": "Vara do Trabalho de Capão Bonito",
			"sigla": "VT123",
			"unidade": "0123"
		},
		{
			"id": 97,
			"descricao": "Vara do Trabalho de Caraguatatuba",
			"sigla": "VT063",
			"unidade": "0063"
		},
		{
			"id": 98,
			"descricao": "1ª Vara do Trabalho de Catanduva",
			"sigla": "VT028",
			"unidade": "0028"
		},
		{
			"id": 99,
			"descricao": "2ª Vara do Trabalho de Catanduva",
			"sigla": "VT070",
			"unidade": "0070"
		},
		{
			"id": 100,
			"descricao": "Vara do Trabalho de Cravinhos",
			"sigla": "VT150",
			"unidade": "0150"
		},
		{
			"id": 101,
			"descricao": "Vara do Trabalho de Cruzeiro",
			"sigla": "VT040",
			"unidade": "0040"
		},
		{
			"id": 102,
			"descricao": "Vara do Trabalho de Dracena",
			"sigla": "VT050",
			"unidade": "0050"
		},
		{
			"id": 103,
			"descricao": "Vara do Trabalho de Fernandópolis",
			"sigla": "VT037",
			"unidade": "0037"
		},
		{
			"id": 104,
			"descricao": "1ª Vara do Trabalho de Franca",
			"sigla": "VT015",
			"unidade": "0015"
		},
		{
			"id": 105,
			"descricao": "2ª Vara do Trabalho de Franca",
			"sigla": "VT076",
			"unidade": "0076"
		},
		{
			"id": 106,
			"descricao": "Vara do Trabalho de Garça",
			"sigla": "VT098",
			"unidade": "0098"
		},
		{
			"id": 107,
			"descricao": "Vara do Trabalho de Guaratinguetá",
			"sigla": "VT020",
			"unidade": "0020"
		},
		{
			"id": 108,
			"descricao": "Vara do Trabalho de Indaiatuba",
			"sigla": "VT077",
			"unidade": "0077"
		},
		{
			"id": 109,
			"descricao": "Vara do Trabalho de Itanhaém",
			"sigla": "VT064",
			"unidade": "0064"
		},
		{
			"id": 110,
			"descricao": "Vara do Trabalho de Itapetininga",
			"sigla": "VT041",
			"unidade": "0041"
		},
		{
			"id": 111,
			"descricao": "Vara do Trabalho de Itapeva",
			"sigla": "VT047",
			"unidade": "0047"
		},
		{
			"id": 112,
			"descricao": "Vara do Trabalho de Itápolis",
			"sigla": "VT049",
			"unidade": "0049"
		},
		{
			"id": 113,
			"descricao": "Vara do Trabalho de Itararé",
			"sigla": "VT148",
			"unidade": "0148"
		},
		{
			"id": 114,
			"descricao": "Vara do Trabalho de Itu",
			"sigla": "VT018",
			"unidade": "0018"
		},
		{
			"id": 115,
			"descricao": "Vara do Trabalho de Ituverava",
			"sigla": "VT052",
			"unidade": "0052"
		},
		{
			"id": 116,
			"descricao": "1ª Vara do Trabalho de Jaboticabal",
			"sigla": "VT029",
			"unidade": "0029"
		},
		{
			"id": 117,
			"descricao": "2ª Vara do Trabalho de Jaboticabal",
			"sigla": "VT120",
			"unidade": "0120"
		},
		{
			"id": 118,
			"descricao": "1ª Vara do Trabalho de Jacareí",
			"sigla": "VT023",
			"unidade": "0023"
		},
		{
			"id": 119,
			"descricao": "2ª Vara do Trabalho de Jacareí",
			"sigla": "VT138",
			"unidade": "0138"
		},
		{
			"id": 120,
			"descricao": "Vara do Trabalho de Jales",
			"sigla": "VT080",
			"unidade": "0080"
		},
		{
			"id": 121,
			"descricao": "1ª Vara do Trabalho de Jaú",
			"sigla": "VT024",
			"unidade": "0024"
		},
		{
			"id": 122,
			"descricao": "2ª Vara do Trabalho de Jaú",
			"sigla": "VT055",
			"unidade": "0055"
		},
		{
			"id": 123,
			"descricao": "1ª Vara do Trabalho de Jundiaí",
			"sigla": "VT002",
			"unidade": "0002"
		},
		{
			"id": 124,
			"descricao": "2ª Vara do Trabalho de Jundiaí",
			"sigla": "VT021",
			"unidade": "0021"
		},
		{
			"id": 125,
			"descricao": "3ª Vara do Trabalho de Jundiaí",
			"sigla": "VT096",
			"unidade": "0096"
		},
		{
			"id": 126,
			"descricao": "4ª Vara do Trabalho de Jundiaí",
			"sigla": "VT097",
			"unidade": "0097"
		},
		{
			"id": 127,
			"descricao": "1ª Vara do Trabalho de Limeira",
			"sigla": "VT014",
			"unidade": "0014"
		},
		{
			"id": 128,
			"descricao": "2ª Vara do Trabalho de Limeira",
			"sigla": "VT128",
			"unidade": "0128"
		},
		{
			"id": 129,
			"descricao": "Vara do Trabalho de Lins",
			"sigla": "VT062",
			"unidade": "0062"
		},
		{
			"id": 130,
			"descricao": "Vara do Trabalho de Lorena",
			"sigla": "VT088",
			"unidade": "0088"
		},
		{
			"id": 131,
			"descricao": "1ª Vara do Trabalho de Marília",
			"sigla": "VT033",
			"unidade": "0033"
		},
		{
			"id": 132,
			"descricao": "2ª Vara do Trabalho de Marília",
			"sigla": "VT101",
			"unidade": "0101"
		},
		{
			"id": 133,
			"descricao": "Vara do Trabalho de Mococa",
			"sigla": "VT141",
			"unidade": "0141"
		},
		{
			"id": 134,
			"descricao": "Vara do Trabalho de Mogi Guaçu",
			"sigla": "VT071",
			"unidade": "0071"
		},
		{
			"id": 135,
			"descricao": "Vara do Trabalho de Mogi Mirim",
			"sigla": "VT022",
			"unidade": "0022"
		},
		{
			"id": 136,
			"descricao": "Vara do Trabalho de Olímpia",
			"sigla": "VT107",
			"unidade": "0107"
		},
		{
			"id": 137,
			"descricao": "Vara do Trabalho de Orlândia",
			"sigla": "VT146",
			"unidade": "0146"
		},
		{
			"id": 138,
			"descricao": "Vara do Trabalho de Ourinhos",
			"sigla": "VT030",
			"unidade": "0030"
		},
		{
			"id": 139,
			"descricao": "1ª Vara do Trabalho de Paulínia",
			"sigla": "VT087",
			"unidade": "0087"
		},
		{
			"id": 140,
			"descricao": "2ª Vara do Trabalho de Paulínia",
			"sigla": "VT126",
			"unidade": "0126"
		},
		{
			"id": 141,
			"descricao": "Vara do Trabalho de Pederneiras",
			"sigla": "VT144",
			"unidade": "0144"
		},
		{
			"id": 142,
			"descricao": "Vara do Trabalho de Penápolis",
			"sigla": "VT124",
			"unidade": "0124"
		},
		{
			"id": 143,
			"descricao": "Vara do Trabalho de Pindamonhangaba",
			"sigla": "VT059",
			"unidade": "0059"
		},
		{
			"id": 144,
			"descricao": "Vara do Trabalho de Pirassununga",
			"sigla": "VT136",
			"unidade": "0136"
		},
		{
			"id": 145,
			"descricao": "Vara do Trabalho de Porto Ferreira",
			"sigla": "VT048",
			"unidade": "0048"
		},
		{
			"id": 146,
			"descricao": "1ª Vara do Trabalho de Presidente Prudente",
			"sigla": "VT026",
			"unidade": "0026"
		},
		{
			"id": 147,
			"descricao": "2ª Vara do Trabalho de Presidente Prudente",
			"sigla": "VT115",
			"unidade": "0115"
		},
		{
			"id": 148,
			"descricao": "Vara do Trabalho de Presidente Venceslau",
			"sigla": "VT057",
			"unidade": "0057"
		},
		{
			"id": 149,
			"descricao": "Vara do Trabalho de Rancharia",
			"sigla": "VT072",
			"unidade": "0072"
		},
		{
			"id": 150,
			"descricao": "Vara do Trabalho de Registro",
			"sigla": "VT069",
			"unidade": "0069"
		},
		{
			"id": 151,
			"descricao": "1ª Vara do Trabalho de Ribeirão Preto",
			"sigla": "VT004",
			"unidade": "0004"
		},
		{
			"id": 152,
			"descricao": "2ª Vara do Trabalho de Ribeirão Preto",
			"sigla": "VT042",
			"unidade": "0042"
		},
		{
			"id": 153,
			"descricao": "3ª Vara do Trabalho de Ribeirão Preto",
			"sigla": "VT066",
			"unidade": "0066"
		},
		{
			"id": 154,
			"descricao": "4ª Vara do Trabalho de Ribeirão Preto",
			"sigla": "VT067",
			"unidade": "0067"
		},
		{
			"id": 155,
			"descricao": "5ª Vara do Trabalho de Ribeirão Preto",
			"sigla": "VT113",
			"unidade": "0113"
		},
		{
			"id": 156,
			"descricao": "6ª Vara do Trabalho de Ribeirão Preto",
			"sigla": "VT153",
			"unidade": "0153"
		},
		{
			"id": 157,
			"descricao": "Vara do Trabalho de Rio Claro",
			"sigla": "VT010",
			"unidade": "0010"
		},
		{
			"id": 158,
			"descricao": "Vara do Trabalho de Salto",
			"sigla": "VT085",
			"unidade": "0085"
		},
		{
			"id": 159,
			"descricao": "Vara do Trabalho de Santa Cruz do Rio Pardo",
			"sigla": "VT143",
			"unidade": "0143"
		},
		{
			"id": 160,
			"descricao": "1ª Vara do Trabalho de São Carlos",
			"sigla": "VT008",
			"unidade": "0008"
		},
		{
			"id": 161,
			"descricao": "2ª Vara do Trabalho de São Carlos",
			"sigla": "VT106",
			"unidade": "0106"
		},
		{
			"id": 162,
			"descricao": "Vara do Trabalho de São João da Boa Vista",
			"sigla": "VT034",
			"unidade": "0034"
		},
		{
			"id": 163,
			"descricao": "Vara do Trabalho de São Joaquim da Barra",
			"sigla": "VT117",
			"unidade": "0117"
		},
		{
			"id": 164,
			"descricao": "1ª Vara do Trabalho de São José do Rio Preto",
			"sigla": "VT017",
			"unidade": "0017"
		},
		{
			"id": 165,
			"descricao": "2ª Vara do Trabalho de São José do Rio Preto",
			"sigla": "VT044",
			"unidade": "0044"
		},
		{
			"id": 166,
			"descricao": "3ª Vara do Trabalho de São José do Rio Preto",
			"sigla": "VT082",
			"unidade": "0082"
		},
		{
			"id": 167,
			"descricao": "4ª Vara do Trabalho de São José do Rio Preto",
			"sigla": "VT133",
			"unidade": "0133"
		},
		{
			"id": 168,
			"descricao": "1ª Vara do Trabalho de São José dos Campos",
			"sigla": "VT013",
			"unidade": "0013"
		},
		{
			"id": 169,
			"descricao": "2ª Vara do Trabalho de São José dos Campos",
			"sigla": "VT045",
			"unidade": "0045"
		},
		{
			"id": 170,
			"descricao": "3ª Vara do Trabalho de São José dos Campos",
			"sigla": "VT083",
			"unidade": "0083"
		},
		{
			"id": 171,
			"descricao": "4ª Vara do Trabalho de São José dos Campos",
			"sigla": "VT084",
			"unidade": "0084"
		},
		{
			"id": 172,
			"descricao": "5ª Vara do Trabalho de São José dos Campos",
			"sigla": "VT132",
			"unidade": "0132"
		},
		{
			"id": 173,
			"descricao": "Vara do Trabalho de São Roque",
			"sigla": "VT108",
			"unidade": "0108"
		},
		{
			"id": 174,
			"descricao": "Vara do Trabalho de São Sebastião",
			"sigla": "VT121",
			"unidade": "0121"
		},
		{
			"id": 175,
			"descricao": "1ª Vara do Trabalho de Sertãozinho",
			"sigla": "VT054",
			"unidade": "0054"
		},
		{
			"id": 176,
			"descricao": "2ª Vara do Trabalho de Sertãozinho",
			"sigla": "VT125",
			"unidade": "0125"
		},
		{
			"id": 177,
			"descricao": "1ª Vara do Trabalho de Sorocaba",
			"sigla": "VT003",
			"unidade": "0003"
		},
		{
			"id": 178,
			"descricao": "2ª Vara do Trabalho de Sorocaba",
			"sigla": "VT016",
			"unidade": "0016"
		},
		{
			"id": 179,
			"descricao": "3ª Vara do Trabalho de Sorocaba",
			"sigla": "VT109",
			"unidade": "0109"
		},
		{
			"id": 180,
			"descricao": "4ª Vara do Trabalho de Sorocaba",
			"sigla": "VT135",
			"unidade": "0135"
		},
		{
			"id": 181,
			"descricao": "Vara do Trabalho de Sumaré",
			"sigla": "VT122",
			"unidade": "0122"
		},
		{
			"id": 182,
			"descricao": "Vara do Trabalho de Tanabi",
			"sigla": "VT104",
			"unidade": "0104"
		},
		{
			"id": 183,
			"descricao": "Vara do Trabalho de Tatuí",
			"sigla": "VT116",
			"unidade": "0116"
		},
		{
			"id": 184,
			"descricao": "1ª Vara do Trabalho de Taubaté",
			"sigla": "VT009",
			"unidade": "0009"
		},
		{
			"id": 185,
			"descricao": "2ª Vara do Trabalho de Taubaté",
			"sigla": "VT102",
			"unidade": "0102"
		},
		{
			"id": 186,
			"descricao": "Vara do Trabalho de Teodoro Sampaio",
			"sigla": "VT127",
			"unidade": "0127"
		},
		{
			"id": 187,
			"descricao": "Vara do Trabalho de Tietê",
			"sigla": "VT111",
			"unidade": "0111"
		},
		{
			"id": 188,
			"descricao": "Vara do Trabalho de Tupã",
			"sigla": "VT065",
			"unidade": "0065"
		},
		{
			"id": 189,
			"descricao": "Vara do Trabalho de Ubatuba",
			"sigla": "VT139",
			"unidade": "0139"
		},
		{
			"id": 190,
			"descricao": "Vara do Trabalho de Votuporanga",
			"sigla": "VT027",
			"unidade": "0027"
		},
		{
			"id": 316,
			"descricao": "5ª Vara do Trabalho de Jundiaí",
			"sigla": "VT188",
			"unidade": "0188"
		}
	]
}