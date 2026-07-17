function email(){
	return
}

function emailEscreverBaixarDocumentoAtivo(
	email='',
	assunto='',
	texto=''
){
	let pje = pjeObterContexto()
	if(pje){
		let processo = PROCESSO?.numero || ''
		let textoPadrao = CONFIGURACAO?.texto?.emailDocumentos || ''
		let assinatura = CONFIGURACAO?.texto?.assinatura || ''
		let documentoTitulo = pjeObterDocumentoTitulo()
		let documentoLink = pjeObterDocumentoLink()
		let link = ''
		let titulo = ''
		if(documentoLink) link = 'Link:\n' + documentoLink
		if(documentoTitulo) titulo = 'Documento:\n' + documentoTitulo
		assunto = 'Processo ' + processo
		texto =	'Referente ao ' + assunto + '\n\n' + titulo + '\n\n' + link + '\n\n' + textoPadrao + '\n\n' + assinatura
		setTimeout(() => clicar('[mattooltip="Baixar documento com capa (sem assinatura digital válida)"]'),1000)
	}
	let url = 'mailto:'+encodeURI(minusculas(email)+'?subject='+assunto+'&body='+texto)
	abrirPagina(url,'','','','','webmail')
	esforcosPoupados(3,3,contarCaracteres(texto))
}

function emailEscreverOficioCaixaEconomicaFederalBaixarDocumento(
	email='',
	assunto='',
	texto=''
){
	setTimeout(() => clicar('[mattooltip="Baixar documento com capa (sem assinatura digital válida)"]'),1000)
	let processo = PROCESSO?.numero || ''
	let textoPadrao = 'Encaminho o ofício expedido no processo referenciado no início desta mensagem, que pode ser acessado pelo link acima informado.\n\nAgradeço pela atenção.\n\nSaudações,'
	let assinatura = CONFIGURACAO?.texto?.assinatura || ''
	let documentoTitulo = pjeObterDocumentoTitulo()
	let documentoLink = pjeObterDocumentoLink()
	let link = ''
	let titulo = ''
	if(documentoLink) link = 'Link:\n' + documentoLink
	if(documentoTitulo) titulo = 'Documento:\n' + documentoTitulo
	assunto = 'Ofício de Transferência de Valores - Processo ' + processo
	texto =	'Referente ao ' + assunto + '\n\n' + titulo + '\n\n' + link + '\n\n' + textoPadrao + '\n\n' + assinatura
	let url = 'mailto:'+encodeURI(email+'?subject='+assunto+'&body='+texto)
	abrirPagina(url,'','','','','webmail')
	esforcosPoupados(3,3,contarCaracteres(texto))
}

function emailEscreverNotificacaoInicialBaixarDocumento(funcao=''){
	pjeDocumentoEmailEscreverNotificacaoBaixarDocumento('Sua Pessoa está sendo notificada para tomar ciência do processo acima citado e para, se desejar, no prazo de 15 dias, apresentar sua defesa. Caso se faça representar por escritório de advocacia, é importante, dentro do mesmo prazo, que seja feita a habilitação nos autos para fins de se evitar prejuízos pela falta de defesa e para que Sua Pessoa tenha ciência efetiva de todos os atos processuais, em especial, da data da audiência.',funcao)
}

function emailEscreverCitacaoBaixarDocumento(funcao=''){
	pjeDocumentoEmailEscreverNotificacaoBaixarDocumento('Nos termos do Provimento GP-CR 4/2021 do Tribunal Regional do Trabalho da 15ª Região, Sua Pessoa está sendo citada para, no prazo de 15 dias, apresentar sua contestação à petição inicial no processo acima referenciado, sob pena de revelia e confissão ficta. No mesmo ato, deverá apresentar todos os documentos requisitados na petição inicial, sob pena de se reputarem verdadeiros os fatos que o polo ativo pretendia por meio deles provar (artigos 396 e 400 do Código de Processo Civil). A petição pode ser acessada pelo link acima informado.',funcao)
}

function emailEscreverNotificacaoAudienciaBaixarDocumento(funcao=''){
	pjeDocumentoEmailEscreverNotificacaoBaixarDocumento('Nos termos do Provimento GP-CR 4/2021 do Tribunal Regional do Trabalho da 15ª Região, Sua Pessoa está sendo notificada para tomar ciência da audiência designada no processo referenciado no início desta mensagem.',funcao)
}

function emailEscreverNotificacaoSentencaBaixarDocumento(funcao=''){
	pjeDocumentoEmailEscreverNotificacaoBaixarDocumento('Fica Vossa Senhoria notificada para tomar ciência da SENTENÇA proferida no processo acima identificado, bem como dos demais documentos produzidos nos autos do mesmo processo, tais como decisões de Embargos de Declaração, recursos interpostos, e todos os demais até a presente data.',funcao)
}

function pjeDocumentoEmailEscreverNotificacaoBaixarDocumento(
	mensagem='',
	funcao=''
){
	let pje = pjeObterContexto()
	if(!pje) return
	let processo = PROCESSO?.numero || ''
	let textoPadrao = mensagem + '\n\nO teor do documento pode ser visualizado pelo acesso ao link referenciado no início desta mensagem.\n\nAgradeço pela atenção.\n\nSaudações,'
	let assinatura = CONFIGURACAO?.texto?.assinatura || ''
	let assunto = 'Processo ' + processo
	let link = 'Link:\n' + pjeObterDocumentoLink()
	let titulo = 'Documento:\n' + pjeObterDocumentoTitulo()
	let texto = 'Referente ao ' + assunto + '\n\n' + titulo + '\n\n' + link + '\n\n' + textoPadrao + '\n\n' + assinatura
	let url = 'mailto:'+encodeURI(PROCESSO.emails+'?subject='+assunto+'&body='+texto)
	setTimeout(() => clicar('[aria-label="Baixar documento com capa (sem assinatura)"]'),1000)
	if(funcao) setTimeout(funcao,2000)
	abrirPagina(url,'','','','','webmail')
	esforcosPoupados(3,3,contarCaracteres(texto))
}