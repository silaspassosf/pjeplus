/**
 * Verifica se um objeto está vazio:
 * @param {object}	objeto
 */
function vazio(objeto){
	relatar('Verificando se o parametro existe:',objeto)
	if(!objeto) return true
	relatar('Verificando o tipo do parametro:',(typeof objeto))
	if(typeof objeto != 'object') return false
	relatar('Verificando se o objeto contém alguma chave:',objeto)
	for(let chave in objeto){
		if(objeto.hasOwnProperty(chave)) return false
	}
	relatar('-> objeto:',objeto)
	return true
}

/**
 * Retorna apenas os números de uma string:
 * @param {string}	texto
 */
function numeros(texto){
	relatar('-> Obtendo números de:',texto)
	if(!texto) return ''
	let resultado = texto.replace(/\D/g,'').toString() || ''
	relatar('-> resultado:',resultado)
	return resultado
}

function maiusculas(texto){
	if(!texto) return ''
	return texto?.toUpperCase() || ''
}

function minusculas(texto){
	if(!texto) return ''
	return texto?.toLowerCase() || ''
}

function titularizar(texto){
	if(!texto) return ''
	let textoEmMinusculas = minusculas(texto)
	let titulo = textoEmMinusculas.split(' ').map(palavra => {
		if(palavra) return palavra.replace(palavra[0],maiusculas(palavra[0]))
	}).join(' ')
	return titulo.replace(/\s(E|(A|O)(s)|D(e|a|as|o|os))\s/g,correspondencia => minusculas(correspondencia))
}

function removerAcentuacao(texto){
	if(!texto) return ''
	let acentos = {
		a:/[\xE0-\xE6]/g,
		e:/[\xE8-\xEB]/g,
		i:/[\xEC-\xEF]/g,
		o:/[\xF2-\xF6]/g,
		u:/[\xF9-\xFC]/g,
		c:/\xE7/g,
		n:/\xF1/g
	}
	for(let letra in acentos){
		let expressao = acentos[letra]
		texto = texto.replace(expressao,letra)
	}
	return texto
}

/**
 * Retorna o valor de um parametro de URL:
 * @param {string}	parametro
 */
function obterParametroDeUrl(parametro){
	relatar('Instanciando objeto...')
	let url = new URL(window.location.href)
	if(!url) return
	relatar('-> url:',url)
	let parametros = new URLSearchParams(url.search)
	relatar('-> parametros:',parametros)
	let valor = parametros.get(parametro) || ''
	relatar('-> valor:',valor)
	return valor
}

/**
 * Abre uma URL, por meio do ${browser.runtime} (navegador/navegador.js), utilizando o método ${criarJanela()} (publicas/navegador.js).
 * É preferível ao ${window.open}, pois permite configurar opções da janela a nível de navegador.
 * @param  {string}		url
 * @param  {string}		chave				Será usada para extrair configurações de ${CONFIGURACAO.janela[chave]}
 * @param  {integer}	largura
 * @param  {integer}	altura
 * @param  {integer}	horizontal	Distância da esquerda
 * @param  {integer}	vertical		Distância do topo
 * @param  {string} 	tipo				Ver https://developer.mozilla.org/en-US/docs/Mozilla/Add-ons/WebExtensions/API/windows/CreateType
 */
function abrirPagina(
	url,
	largura = '',
	altura = '',
	horizontal = '',
	vertical = '',
	chave = '_blank',
	tipo = 'normal'
){
	let opcoes = {}
	opcoes.chave = chave
	opcoes.url = url
	opcoes.largura = largura || 1000
	opcoes.altura = altura || 700
	opcoes.horizontal = horizontal || 0
	opcoes.vertical = vertical || 0
	opcoes.tipo = tipo
	relatar('Mensagem para o navegador:',opcoes)
	browser.runtime.sendMessage(opcoes)
}

async function obterMemoriaTexto(){
	let texto = await navigator.clipboard.readText()
	return texto || ''
}

function copiar(texto){
	relatar('Copiando texto... ',texto)
	navigator.clipboard.writeText(texto).then(() => {
		esforcosPoupados(1,2,2)
		relatar('Conteúdo copiado:',texto)
		return
	},erro => {
		relatar('x Não foi possível copiar: ',erro)
		return
	})
}

function selecionarConteudo(){
	this.select()
}

function copiarConteudo(){
	selecionarConteudo()
	copiar(this.value)
	esforcosPoupados(0,0,2)
}

function colar(){
	document.execCommand('paste')
}

function quebrarLinha(){
	document.execCommand('insertLineBreak')
}

function fechar(){
	window.close()
}

function saudacao(){
	let data = new Date()
	let hora = data.getHours()
	let texto = 'Bo'
	switch(true){
		case(hora < 12):
			texto += 'm dia!'
			break
		case(hora >= 12 && hora < 18):
			texto += 'a tarde!'
			break
		case(hora >= 18 && hora < 24):
			texto += 'a noite!'
			break
	}
	return texto
}

function obterData(texto){
	let data = texto.match(EXPRESSAO.data) || ''
	if(!data) return ''
	return data[0]
}

function obterHora(texto){
	let hora = texto.match(EXPRESSAO.hora) || ''
	if(!hora) return ''
	return hora[0]
}

function obterValorMonetario(texto){
	let valor = texto.match(EXPRESSAO.valorMonetario) || ''
	if(!valor) return ''
	return valor[0]
}

function obterCPF(texto){
	let cpf = texto.match(EXPRESSAO.cpf) || ''
	if(!cpf) return ''
	return cpf[0]
}

function obterCNPJ(texto){
	let cnpj = texto.match(EXPRESSAO.cnpj) || ''
	if(!cnpj) return ''
	return cnpj[0]
}

function obterRaizCNPJ(texto){
	return texto.replace(/[/].*/gi,'') || ''
}

function obterDocumento(texto){
	let cnpj = obterCNPJ(texto)
	let cpf = obterCPF(texto)
	return cnpj+cpf
}

function obterNumeroDoProcessoPadraoCNJ(texto){
	let numero = texto.match(EXPRESSAO.processoNumero) || ''
	if(!numero) return ''
	return numero[0] || ''
}

function obterNumeroDoProcessoSemSeparadores(texto){
	let numero = texto.match(EXPRESSAO.processoNumeroSemSeparadores) || ''
	if(!numero) return ''
	return numero[0] || ''
}

function converterNumeroDoProcessoSemSeparadoresParaPadraoCNJ(numero){
	if(obterNumeroDoProcessoSemSeparadores(numero)){
		numero = numero.
			replace(/^(\d{7})(\d+)/g,"$1-$2").
			replace(/^(\d{7}[-]\d{2})(\d+)/g,"$1.$2").
			replace(/^(\d{7}[-]\d{2}[.]\d{4})(\d+)/g,"$1.$2").
			replace(/^(\d{7}[-]\d{2}[.]\d{4}[.]\d)(\d+)/g,"$1.$2").
			replace(/^(\d{7}[-]\d{2}[.]\d{4}[.]\d[.]\d{2})(\d+)/g,"$1.$2")
	}
	return numero || ''
}

function obterNumeroDoProcessoParcial(texto){
	let numero = texto.match(EXPRESSAO.processoNumeroParcial) || ''
	if(!numero) return ''
	return String(numero[0])?.padStart(15,'0') || ''
}

function obterContaJudicialBancoDoBrasil(texto){
	let conta = texto.match(EXPRESSAO.bbContaJudicial) || ''
	if(!conta) return ''
	return conta[0]
}

function obterChassi(texto){
	let chassi = texto.match(EXPRESSAO.chassi) || ''
	if(!chassi) return ''
	return chassi[0]
}

function obterCorreiosObjeto(texto){
	let objeto = texto.match(EXPRESSAO.correiosObjeto) || ''
	if(!objeto) return ''
	return objeto[0]
}

function obterPlacaDeVeiculoAutomotor(texto){
	let placa = texto.match(/[A-Za-z]{3}\d{4}/gi) || texto.match(/[A-Za-z]{3}(-|–|\s|[.])\d{4}/gi) || texto.match(/[A-Za-z]{3}\d{1}[A-Za-z]\d{2}/gi) || ''
	if(!placa) return ''
	return placa[0].replace(/(-|–|\s|[.])/,'')
}

function obterNomeCompleto(texto){
	let nome = texto.match(EXPRESSAO.nomeCompleto) || ''
	if(!nome) return ''
	return nome[0].trim()
}

function obterEmail(texto){
	let email = texto.match(EXPRESSAO.email) || ''
	if(!email) return ''
	return email[0].trim()
}

function contarCaracteres(texto){
	if(!texto) return 0
	if(texto?.length){
		let caracteres = texto.length || 0
		if(caracteres > 0) return caracteres
	}
	else return 0
}

function usuariosEspeciais(){
	return '067065077073076065032077085077073067032077065082067079078073032068065032067079083084065' + ';065076069088032072069078082073081085069032068069032076073077065032069032083073076086065' + ';065078065032067065082079076073078065032083073076086065032067079082082069065032083065076071065068079' + ';067065082079076073078069032068079083032083065078084079083032080069083083065078072065' + ';067072082073083084073065078032071065078068072073032068069032083079085090065032076065067069082068065' + ';071073079086065078078065032090065067072065082065032068079083032083065078084079083' + ';074069083083073067065032083069082069074079032076085071076073079032068069032079076073086069073082065' + ';074079065081085073077032080069068082079032070073078079067072073079032068065032083073076086065032067065083083073065078079' + ';076069073076065032067065077065082071079032066079084069076072079032076079085082069078067079' + ';077065082067069076079032069068085065082068079032068069032076073077065' + ';082079078065078032070069082082069073082065032068065032067079083084065'
	//return '067065077073076065032077085077073067032077065082067079078073032068065032067079083084065' + ';083073083069078065078068079032071079077069083032067065076073088084079032068069032083079085083065'
}

async function pcd(){
	let dados = await pjeApiObterUsuario()
	let usuarios = usuariosEspeciais()
	if(dados?.nome){
		let nome = codificar(maiusculas(dados.nome).trim())
		if(usuarios.includes(nome)) await browser.storage.local.set({pcd:true})
	}
}

function limparEspacamentos(texto=''){
	if(!texto) return ''
	return texto.replace(/(\s|\t)+/,' ').replace(/(\r|\n)+/,'').trim()
}

function inteiroAleatorio(
	menor = 0,
	maior = 1
){
	return Math.floor(Math.random() * maior) + menor
}

function codificar(texto){
	let resultado = []
	for (let indice=0;indice<texto.length;indice++){
		let caractere = texto.charCodeAt(indice)
		caractere = String("000" + caractere).slice(-3)
		resultado.push(caractere)
	}
	return resultado.join('') || ''
}

function decodificar(texto){
	let resultado = ''
	let partes = texto.match(/.{1,3}/g)
	for (let indice=0;indice<partes.length;indice++){
		resultado += String.fromCharCode(parseInt(partes[indice], 10))
	}
	return resultado || ''
}

function capturarImagemDeElemento(seletor=''){
	if(!seletor) seletor = 'body'
	let elemento = selecionar(seletor)
	if(!elemento) elemento = document.body
	let retangulo = obterRetangulo(elemento)
	browser.runtime.sendMessage({
		capturar:"capturar",
		retangulo:retangulo
	})
}

async function blobParaArrayBuffer(blob){
	return new Promise((resolve, reject) => {
		let leitor = new FileReader()
		leitor.onload = () => resolve(leitor.result)
		leitor.onerror = reject
		leitor.readAsArrayBuffer(blob)
	})
}

function arrayBufferParaBlob(
	buffer = '',
	tipo = 'image/png'
){
	return new Blob(
		[buffer],
		{type:tipo}
	)
}