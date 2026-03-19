async function pje(){

	console.info('JANELA:',JANELA)
	console.info('CONFIGURACAO:',CONFIGURACAO)

	if(!JANELA.includes(LINK.pje.raiz)) return

	let id = pjeObterProcessoId()
	PROCESSO = await new Processo(id)

	console.info('VARAS:',VARAS)
	console.info('PROCESSO',PROCESSO)

	pjeOtimizarConclusaoAMagistrado()

}


function pjeObterProcessoId(){
	let id = ''
	EXPRESSAO.processoId = new RegExp(/(processo.*?[/](audiencias|detalhe|documento|pericias|tarefa)|pjekz.gigs.abrir.gigs.*)/,'gi')
	let caminho = JANELA.match(EXPRESSAO.processoId) || ''
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
		if(Number(processo.ano) <= 2009) processo.ordenador = processo.ordenador.substring(4,5)
		processo.final = processo.ordenador.substr(-1)
		let	paridade = Number(processo.ordenador) % 2
		if(paridade === 1) processo.paridade = 'ímpar'
		if(paridade === 0)processo.paridade = 'par'
	}

	return processo

}


async function pjeOtimizarConclusaoAMagistrado(){

	let selecao = await esperar('[placeholder="Magistrado"]',true)
	let juizosPorFinalDoProcesso = await trt15ApiConsultaPlanilhaJuizosPorFinalDoProcesso()
	await esperar('pje-concluso-tarefa-botao',true,true)
	let orgaoJulgador = PROCESSO?.origem || ''
	let juizos = juizosPorFinalDoProcesso.filter(juizo => juizo.v.includes(orgaoJulgador)) || ''
	let juizo = juizos.filter(juizo => juizo.f.includes(PROCESSO.final))[0] || ''
	let magistrado = juizo.j || ''
	let vara = VARAS.filter(vara => vara.unidade.includes(orgaoJulgador))[0] || ''
	clicar('[placeholder="Magistrado"]')
	let ancestral = await esperar('div.dados-conclusao',true,true)
	let texto = 'Recomendo o nome ' + magistrado + ' porque, em minhas configurações, ele está associado ao final do processo "' + PROCESSO.final + '", para a ' + vara.descricao + ' (' + orgaoJulgador + ')'
	if(!magistrado) texto = 'Ainda não foram definidas configurações para o final do processo "' + PROCESSO.final + '" da ' + vara.descricao + ' (' + orgaoJulgador + ')'
	if(PROCESSO?.redistribuicoes){
		texto = "PROCESSO COM REDISTRIBUIÇÃO\n"
		PROCESSO.redistribuicoes.forEach(redistribuicao => {
			let data = new Date(redistribuicao.dataHoraRedistribuicao)
			let tipo = redistribuicao?.tipoRedistribuicao || ''
			let orgao = redistribuicao?.orgaoJulgadorAnterior?.descricao || ''
			let informacao = "\n" + 'Em ' + data.toLocaleDateString() + ', por ' + tipo + ', de ' + orgao
			texto += informacao
		})
	}
	let quinzinho = criarQuinzinhoInformativo('quinzinho-informacoes-conclusao-ao-magistrado',ancestral,texto)
	//criarBotao('configuracoes-de-juizo-por-final-de-processo','',quinzinho,'Configurações de Juízo por Final de Processo','',abrirPaginaConfiguracoesJuizo)
	if(!magistrado) return
	if(selecao.textContent.includes(magistrado)) return
	pjeSelecionarOpcaoPorTexto(magistrado,true)
}

async function pjeSelecionarOpcaoPorTexto(
	texto='',
	parcial=false
){
	if(!texto) return ''
	await esperar('mat-option',true,true)
	await aguardar(500)
	let opcao = [...document.querySelectorAll('mat-option')].filter(opcao => opcao.innerText == texto)[0] || ''
	if(!opcao){
		if(parcial) opcao = [...document.querySelectorAll('mat-option')].filter(opcao => opcao.innerText.includes(texto))[0] || ''
	}	
	clicar(opcao)
	return opcao
}

async function obterOrgaosJulgadores(){

	let orgaosJulgadores = await pjeApiObterOrgaosJulgadores()
	
	let orgaos = []

	for(let [indice, item] of [...orgaosJulgadores].entries()){
		let id = item?.id || ''
		if(!id) continue
		let orgaoJulgador = await pjeApiObterOrgaosJulgadores(id)
		let orgao = {}
		let tipo = orgaoJulgador?.codigoTipo || ''
		if(tipo.includes('VARA')){
			orgao.id = orgaoJulgador?.id || ''
			orgao.descricao = limparEspacamentos(orgaoJulgador.descricao) || ''
			orgao.sigla = limparEspacamentos(orgaoJulgador.sigla) || ''
			orgao.unidade = limparEspacamentos(preencherTextoPeloInicio(numeros(orgaoJulgador.sigla),4))
			orgaos.push(orgao)
		}
	}
	orgaos = orgaos.sort((a, b) => {
    return (a.id - b.id)
	})

}

class Processo {
  constructor(id){
    return this.processo(id)
  }
  async processo(id){
    let processo = await pjeApiObterProcessoDadosPrimarios(id)
		Object.assign(processo,obterDadosDoNumeroDoProcesso(processo.numero))
		processo.redistribuicoes = await pjeApiObterProcessoRedistribuicoes(id)
    return processo 
  }
}