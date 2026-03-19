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
	atributos = false,
	caracteres = false,
	texto = false,
	desconectar = true
){
	return new Promise(
		resolver => {
			let elemento = selecionar(seletor)
			if(texto)
				elemento = selecionarPorTexto(seletor)
			if(elemento){
				relatar('-> Elemento encontrado: ',elemento)
				resolver(elemento)
				return
			}
			let observador = new MutationObserver(
				mudanca => {
					relatar('-> Mudança: ',mudanca)
					relatar('-> Aguardando elemento "'+seletor+'"...',)
					let observado = selecionar(seletor)
					if(texto)
						observado = selecionarPorTexto(seletor)
					if(observado){
						relatar('-> Elemento encontrado: ',observado)
						if(desconectar)
							observador.disconnect()
						resolver(observado)
					}
				}
			)
			observador.observe(
				document.body,
				{
					childList:			true,
					subtree:				true,
					attributes:			atributos,
					characterData:	caracteres
				}
			)

		}
	)
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

	if(vazio(ancestral))
		ancestral = document

	if(todos){
		elemento = ancestral.querySelectorAll(seletor)
		if(elemento.lenght){
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


/**
 * Retorna todos os elementos com base no seletor CSS:
 * @param {string}	seletor		Seletor  CSS
 * @return elemento
 */
function todos(seletor=''){

	relatar('Procurando elemento:',seletor)

	if(!seletor){
		relatar('Seletor vazio:',seletor)
		return []
	}

	let elementos = document.querySelectorAll(seletor)

	relatar('-> elementos: ',elementos)

	return elementos

}


function selecionarPorTexto(texto){

	let elemento = document.evaluate(
		"//*[contains(text(),'"+texto+"')]",
		document,
		null,
		XPathResult.FIRST_ORDERED_NODE_TYPE,
		null
	).singleNodeValue	|| ''

	return elemento

}


function remover(id=''){

	if(!id) return

	let elemento = document.getElementById(id) || ''
	if(!elemento){
		relatar('Elemento não encontrado:',id)
		return
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
	texto = '',
	titulo = ''
){

	remover(id)

	if(!tag) tag = 'quinzinho'

	let elemento = document.createElement(tag)

	if(!ancestral) ancestral = document.body
	if(id) elemento.id = id
	if(classe) elemento.className = classe
	if(texto) elemento.innerText = texto
	if(titulo) elemento.title = titulo

	relatar('Elemento criado:',elemento)

	if(antesDe) ancestral.insertBefore(elemento,antesDe)
	else ancestral.appendChild(elemento)

	relatar('Elemento inserido:',elemento)

	return elemento || ''

}


/**
 * Cria um <style scoped> e insere em ${document.head} ou em um ancestral específico:
 * @param {string} id
 * @param {object} ancestral
 * @param {string} css
 * @return elemento
 * @example
 * const estilo = estilizar(
 *  '',
 *  document.querySelector('#id'),
 *  `
 *   #id{
 *    color:black;
 *   }
 *  `
 * )
 */
function estilizar(
	ancestral = '',
	css = '',
	id = ''
){

	let escopo = ancestral || ''

	if(!ancestral) ancestral = document.head

	let elemento = criar(
		'style',
		id,
		'',
		ancestral
	)

	if(escopo) elemento.setAttribute('scoped',true)

	elemento.textContent = css

	return elemento || ''

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

	itens.forEach(
		item => {
			let dt = criar('dt','','',dl)
			dt.innerText = item.dt
			let dd = criar('dd','','',dl)
			dd.innerText = item.dd
		}
	)

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

	let elemento = criar('quinzinho-botao',id,classe,ancestral)

	if(texto) elemento.innerText = texto
	if(!titulo) titulo = texto
	if(aoClicar) elemento.addEventListener('click',aoClicar)
	if(estilo) estilizar(elemento,estilo)

	elemento.setAttribute('aria-label',titulo)
	elemento.addEventListener('contextmenu',elemento => elemento.preventDefault())

	return elemento

}


function dispararEvento(
	tipo = '',
	elemento = ''
){

	if(!elemento) return

	let evento = new Event(
		tipo,
		{
			bubbles:true
		}
	)

	elemento.dispatchEvent(evento)

}


function selecionarOpcao(
	seletor = '',
	texto = ''
){

	if(
		!seletor
		||
		!texto
	) return ''

	let selecao = selecionar(seletor)
	if(!selecao) return ''

	let lista = selecao?.children
	if(vazio(lista)) return ''

	let opcoes = [...lista].filter(opcoes => opcoes.innerText.includes(texto))
	let opcao = opcoes[0] || ''
	if(!opcao) return ''

	selecao.selectedIndex = opcao.index

	dispararEvento('change',selecao)

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

	return elemento

}


function focar(seletor){

	let elemento = ''

	if(typeof seletor == 'object') elemento = seletor
	if(typeof seletor == 'string') elemento = selecionar(seletor)
	if(!elemento) return ''

	elemento.focus()

	return elemento

}


async function aguardar(milissegundos){
	return new Promise(
		resolver => setTimeout(resolver,milissegundos)
	)
}