function criarCabecalhoDePaginaDaExtensao(){
  let cabecalho = selecionar('header')  || ''
	if(!cabecalho) return
	let titulo = selecionar('h1',cabecalho)
	if(titulo) titulo.innerText = EXTENSAO.name
	estilizar(cabecalho,`
	header{
		background:rgba(var(--extensao-cor-primaria),1);
		height:auto;
		position:fixed;
		top:0;
		width:100%;
		z-index:2;
	}
	h1{
		background:
			var(--extensao-gradiente-branco-preto),
			var(--extensao-icone-branco) no-repeat 7px center,
			rgba(var(--extensao-cor-preto),0.8)
		;
		background-size:30px;
		color:rgba(var(--extensao-cor-branco),0.9);
		font-size:18px;
		line-height:40px;
		text-align:center;
	}
	`)
}