/**
 * Verifica a existência de um elemento no momento da chamada; se não existir, inicia um ${MutationObserver} no ${document.body}:
 * @param {string}	seletor			Seletor  CSS
 * @param {boolean}	atributos		Verifica os atributos dos elementos
 * @param {boolean}	caracteres	Verifica mudança nos caracteres
 * @return elemento
 * @example
 * esperar('#id').then(elemento => console.log(elemento))
 */
async function esperar(
	seletor = '',
	atributos = true,
	caracteres = true,
	texto = false,
	desconectar = true
){
	return new Promise(resolver => {
		let elemento = selecionar(seletor)
		if(texto) elemento = selecionarPorTexto(seletor)
		if(elemento){
			relatar('-> Elemento encontrado: ',elemento)
			resolver(elemento)
			return
		}
		let observador = new MutationObserver(mudanca => {
			relatar('-> Mudança: ',mudanca)
			relatar('-> Aguardando elemento "'+seletor+'"...',)
			let observado = selecionar(seletor)
			if(texto) observado = selecionarPorTexto(seletor)
			if(observado){
				relatar('-> Elemento encontrado: ',observado)
				if(desconectar) observador.disconnect()
				resolver(observado)
			}
		})
		observador.observe(document.body,{childList:true,subtree:true,attributes:atributos,characterData:caracteres})
	})
}

/**
 * Retorna elemento(s) com base no seletor CSS:
 * @param {string}	seletor		Seletor  CSS
 * @param {object}	ancestral	Elemento ancestral (se vazio, utilizará ${document.body})
 * @param {boolean}	todos			Se true, executará querySelectotAll
 * @return elemento
 */
function selecionar(
	seletor = '',
	ancestral = {},
	todos = false
){
	relatar('Procurando elemento:',seletor)
	if(!seletor){
		relatar('Seletor vazio:',seletor)
		return ''
	}
	let elemento = null
	if(vazio(ancestral)) ancestral = document
	if(todos){
		elemento = ancestral.querySelectorAll(seletor)
		if(vazio(elemento)){
			relatar('Não encontrado:',seletor)
			return ''
		}
	}
	else{
		elemento = ancestral.querySelector(seletor) || ''
		if(!elemento){
			relatar('Não encontrado:',seletor)
			return ''
		}
	}
	relatar('-> elemento: ',elemento)
	return elemento
}

function selecionarPorTexto(
	texto='',
	tag='*'
){
	return document.evaluate("//"+tag+"[contains(text(),'"+texto+"')]",document,null,XPathResult.FIRST_ORDERED_NODE_TYPE,null).singleNodeValue || ''
}

function remover(id=''){
	if(!id) return
	let elemento = document.getElementById(id) || ''
	if(!elemento){
		relatar('Elemento não encontrado:',id)
		return ''
	}
	relatar('Removendo:',elemento)
	elemento.remove()
}

/**
 * Cria um elemento HTML básico e insere em ${document.body} ou em um ancestral específico:
 * @param {string} tag
 * @param {string} id
 * @param {string} classe
 * @param {object} ancestral
 * @param {object} antesDe
 * @param {object} depoisDe
 * @return elemento
 * @example
 * const elemento = criar('div','id')
 */
function criar(
	tag = '',
	id = '',
	classe = '',
	ancestral = false,
	antesDe = false,
	depoisDe = false
){
	remover(id)
	if(!tag) tag = 'div'
	if(!ancestral) ancestral = document.body
	let elemento = document.createElement(tag)
	if(id) elemento.id = id
	if(classe) elemento.className = classe
	relatar('Elemento criado:',elemento)
	if(antesDe) ancestral.insertBefore(elemento,antesDe)
	else if(depoisDe) ancestral.insertBefore(elemento,depoisDe.nextSibling)
	else ancestral.appendChild(elemento)
	relatar('Elemento inserido:',elemento)
	return elemento || ''
}

/**
 * Cria um <style scoped> e insere em ${document.head} ou em um ancestral específico:
 * @param {object} ancestral
 * @param {string} css
 * @param {string} id
 * @return elemento
 * @example
 * const estilo = estilizar(
 *  document.querySelector('#id'),
 *  `
 *   #id{
 *    color:black;
 *   }
 *  `,
 *  ''
 * )
 */
function estilizar(
	ancestral = '',
	css = '',
	id = ''
){
	let escopo = ancestral || ''
	if(!ancestral) ancestral = document.head
	let elemento = criar('style',id,'',ancestral)
	if(escopo) elemento.setAttribute('scoped',true)
	elemento.textContent = css
	return elemento || ''
}

function criarTitulo(
	id = '',
	classe = '',
	texto = '',
	ancestral = false,
	antesDe = false,
	depoisDe = false,
	estilo = ''
){
	if(!ancestral) ancestral = document.body
	let elemento = criar('titulo',id,classe,ancestral,antesDe,depoisDe)
	elemento.innerText = texto
	if(estilo) estilizar(elemento,estilo)
	return elemento
}

function criarLink(
	id = '',
	classe = '',
	ancestral = '',
	endereco = '',
	texto = '',
	titulo = '',
	aoClicar = '',
	estilo = ''
){
	let a = criar('a',id,classe,ancestral)
	a.target = '_blank'
	if(endereco) a.href = endereco
	if(texto) a.innerText = texto
	if(titulo) a.setAttribute('aria-label',titulo)
	if(aoClicar) a.addEventListener('click',aoClicar)
	if(estilo) estilizar(a,estilo)
	return a
}

/**
 * Cria um <dl> e insere no ${document.body} ou em um ancestral específico:
 * @param  {string}	id
 * @param  {string}	classe
 * @param  {object}	ancestral
 * @param  {array}	itens
 * @param  {string}	estilo
 * @return dl
 * @example
 *
 * const elemento = criarListaDeDefinicoes(
 *   '',
 *   '',
 *   ancestral,
 *   [
 *    {
 *     dt:"Titulo 1",
 *     dd:"Texto 1"
 *    },
 *    {
 *     dt:"Titulo 2",
 *     dd:"Texto 2"
 *    }
 *   ]
 * )
 */
function criarListaDeDefinicoes(
	id = '',
	classe = '',
	ancestral = '',
	itens = [],
	estilo = ''
){
	let dl = criar('dl',id,classe,ancestral)
	itens.forEach(item => {
		let dt = criar('dt','','',dl)
		dt.innerText = item.dt
		let dd = criar('dd','','',dl)
		dd.innerText = item.dd
	})
	if(estilo) estilizar(dl,estilo)
	return dl
}

function criarBotao(
	id = '',
	classe = '',
	ancestral = '',
	texto = '',
	titulo = '',
	aoClicar = '',
	estilo = ''
){
	let elemento = criar('botao',id,classe,ancestral)
	if(texto) elemento.innerText = texto
	if(!titulo) titulo = texto
	elemento.setAttribute('aria-label',titulo)
	if(aoClicar) elemento.addEventListener('click',aoClicar)
	if(estilo) estilizar(elemento,estilo)
	return elemento
}

function criarDataList(
	destino = '',
	id = '',
	valores = []
){
	id = 'avjt-lista-'+id
	destino.setAttribute('list',id)
	let lista = criar('datalist',id)
	valores.forEach(valor => {
		let item = criar('option','','',lista)
		item.value = valor
	})
}

function dispararEvento(
	tipo = '',
	elemento = ''
){
	if(!elemento) return
	let evento = new Event(tipo,{"bubbles":true,"cancelable":false})
	elemento.dispatchEvent(evento)
}

function selecionarOpcao(
	seletor = '',
	texto = ''
){
	if(!seletor || !texto) return ''
	let selecao = selecionar(seletor)
	if(!selecao) return ''
	let lista = selecao?.children
	if(vazio(lista)) return ''
	let opcoes = [...lista].filter(opcoes => opcoes.innerText.includes(texto))
	let opcao = opcoes[0] || ''
	if(!opcao) return ''
	selecao.selectedIndex = opcao.index
	dispararEvento('change',selecao)
	esforcosPoupados(2,2,0)
	return selecao
}

function clicar(
	seletor = '',
	texto = false
){
	let elemento = ''
	if(typeof seletor == 'object') elemento = seletor
	if(typeof seletor == 'string'){
		if(texto) elemento = selecionarPorTexto(seletor)
		else elemento = selecionar(seletor)
	}
	if(!elemento) return ''
	elemento.click()
	esforcosPoupados(1,1)
	return elemento
}

function focar(seletor){
	let elemento = ''
	if(typeof seletor == 'object') elemento = seletor
	if(typeof seletor == 'string') elemento = selecionar(seletor)
	if(!elemento) return ''
	elemento.focus()
	esforcosPoupados(1,1)
	return elemento
}

function obterRetangulo(elemento=''){
	if(!elemento) elemento = document.body
	return elemento.getBoundingClientRect()
}

function aguardar(tempo=1000){
	return new Promise(resolver => setTimeout(resolver,tempo))
}

function preencher(
	campo = '',
	texto = '',
	change = false,
	input = true,
	evento = ''
){
	//Aplicável a campos gerados por React e Ajax
	if(!campo) return
	if(typeof campo == 'string') campo = selecionar(campo)
	if(!campo) return
	campo.focus()
	let propriedade = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set
	propriedade.call(campo,texto)
	if(change) dispararEvento('change',campo)
	if(input) dispararEvento('input',campo)
	
	if(evento) dispararEvento(evento,campo)
	esforcosPoupados(1,1,contarCaracteres(texto))
}