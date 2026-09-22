/**
 * Contabiliza as propriedades da variável global ${ESFORCOS} e armazena em ${browser.storage.local.esforcos}
 */
 async function contarEsforcosRepetitivosPoupados(){
	let total = ESFORCOS.cliques + ESFORCOS.movimentos + ESFORCOS.teclas
	if(total < 1) return
	let armazenamento = await browser.storage.local.get(['esforcos'])
	let cliques = armazenamento?.esforcos?.cliques || 0
	let movimentos = armazenamento?.esforcos?.movimentos || 0
	let teclas = armazenamento?.esforcos?.teclas || 0
	let data = armazenamento?.esforcos?.data || DATA.hoje.curta
	let esforcos = {}
	esforcos.cliques = Number(ESFORCOS.cliques)		+ Number(cliques)
	esforcos.movimentos = Number(ESFORCOS.movimentos)	+ Number(movimentos)
	esforcos.teclas = Number(ESFORCOS.teclas)			+ Number(teclas)
	esforcos.data = data
	await browser.storage.local.set({esforcos})
	ESFORCOS.cliques = 0
	ESFORCOS.movimentos = 0
	ESFORCOS.teclas = 0
}

function esforcosPoupados(
	cliques = 0,
	movimentos = 0,
	teclas = 0
){
	if(cliques > 0) ESFORCOS.cliques = cliques
	if(movimentos > 0) ESFORCOS.movimentos = movimentos
	if(teclas > 0) ESFORCOS.teclas = teclas
}