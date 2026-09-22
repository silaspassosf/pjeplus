async function eCarta(){
	if(!JANELA.includes(LINK.eCarta.raiz)) return
	ecartaOtimizarConsultarProcesso()
}

async function ecartaOtimizarConsultarProcesso(){
	if(!JANELA.includes('consultarProcesso.xhtml')) return
	let tabela = await esperar('[action="/eCarta-web/consultarProcesso.xhtml"]  div table',true,true)
	let linhas = tabela.querySelectorAll('tr')
	for(let [indice, linha] of linhas.entries()){
		let texto = linha.textContent || ''
		let objeto = obterCorreiosObjeto(texto)
		if(!objeto) continue
		let celula = linha.cells[5] || ''
		if(!celula) continue
		otimizarCelula(celula)
		celula.addEventListener(
			'click',
			() => abrirPagina(caminho('navegador/ecarta/pagina.htm?objeto='+objeto),'800','900','','')
		)
	}

	estilizar(
		'',
		`
		body{
			line-height:1 !important;
		}
		.avjt-certificar{
			background:
				var(--extensao-icone-branco) no-repeat 5px 50% / 20px 20px,
				var(--extensao-gradiente-branco-preto),
				rgba(var(--extensao-cor-azul),1)
			;
			color:rgba(var(--extensao-cor-branco),1);
			cursor:pointer;
		}
		br{
			display:none;
		}
		.breadcrumb,
		.content
		{
			padding:0 !important;
		}
		.nav,
		.section
		{
			margin:0 !important;
		}
		.section h3{
			padding:0.5rem 0 0 0;
		}
		th:nth-child(7){
			width:200px !important;
		}
		`,
		'avjt-certificar'
	)

	function otimizarCelula(celula=''){
		if(!celula) return
		celula.classList.add('avjt-certificar')
		celula.title = 'Abrir Histórico e Certificar no PJe'
	}

}


function ecartaConsultarProcesso(processo=''){
	let pje = pjeObterContexto()
	if(!processo){
		if(pje) processo = PROCESSO?.numero || ''
	}
	copiar(processo)
	let url = LINK.eCarta.consultarProcesso + encodeURI(processo)
	abrirPagina(url,'','','','','eCarta')
	esforcosPoupados(1,1)
}