class PainelSuperior{
	constructor(classe=''){
		this.elemento = criar('painel-superior','avjt-painel-superior',classe)
		this.conteudo = criar('conteudo','avjt-painel-superior-conteudo','',this.elemento)
		this.cabecalho = criar('cabecalho','avjt-painel-superior-cabecalho','',this.conteudo)
		this.corpo = criar('corpo','avjt-painel-superior-corpo','',this.conteudo)
		this.acionador = criar('acionador','avjt-painel-superior-acionador','',this.elemento)
	}
}