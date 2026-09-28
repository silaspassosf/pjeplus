async function simples(){
	if(!JANELA.includes(LINK.receitaFederal.dominio)) return
	simplesConsultar()
}


async function simplesConsultar(){
	if(!JANELA.includes(LINK.receitaFederal.consultarSimplesOptante)) return
	console.log('JANELA',JANELA)
	
	let cnpj = obterParametroDeUrl('avjtConsultar')
	preencher('#Cnpj',cnpj)
	await aguardar(100)
	clicar('button.h-captcha')
	clicar('#btnMaisInfo')
}


function simplesConsultarPessoa(cnpj=''){
	copiar(cnpj)
	let url = LINK.receitaFederal.consultarSimplesOptante + '?avjtConsultar=' + numeros(cnpj)
	abrirPagina(url,'','','','','simples')
	esforcosPoupados(1,1)
}
