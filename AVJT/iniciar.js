// Desenvolvido por:	Sisenando Gomes Calixto de Sousa
// E-mail:						sisenandosousa@trt15.jus.br
// Telefone:					(12) 9.8804-3003

browser.storage.local.get(
	null,
	armazenamento => {
		EXTENSAO.ativada = armazenamento.ativada
		CONFIGURACAO = armazenamento
		//MODO.relatar = true
		relatar('CONFIGURAÇÃO: ', CONFIGURACAO)
		console.debug('CONFIGURAÇÃO: ', CONFIGURACAO)
		MODO.relatar = false
		otimizar()
	}
)

async function otimizar(){
	if(!EXTENSAO.ativada) return
	if(CONFIGURACAO.pcd) return	
	definicoesGlobais()
	janela()
	pcd()
	adHoc()
	apiGooglePlanilhas()
	assistenteDeSelecao()
	bb()
	cef()
	chamado()
	cndt()
	correios()
	eCarta()
	googleDocs()
	googleMail()
	infojud()
	lgpd()
	penhora()
	pje()
	pjeCalc()
	planilha()
	renajud()
	resolverCaptchas()
	sif()
	sigeo()
	sinesp()
	simples()
	siscondj()
	trt15()
	tst()
	setInterval(contarEsforcosRepetitivosPoupados,500)
}