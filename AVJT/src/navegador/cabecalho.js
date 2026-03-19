function criarCabecalhoDePaginaDaExtensao(){

  let cabecalho = selecionar('header')  || ''
	if(!cabecalho) return

	criarEstilo()

	let titulo = selecionar('h1',cabecalho)
	if(titulo) titulo.innerText = EXTENSAO.name


	function criarEstilo(){

		estilizar(
			cabecalho,
			`
				header{
					background:rgba(var(--quinzinho-cor-primaria),1);
					height:auto;
					position:fixed;
					top:0;
					width:100%;
					z-index:2;
				}
				h1{
					background:
						var(--quinzinho-gradiente-branco-preto),
						var(--quinzinho-icone-ativo) no-repeat 7px center,
						rgba(var(--quinzinho-cor-preto),0.8)
					;
					background-size:30px;
					color:rgba(var(--quinzinho-cor-branco),0.9);
					font-size:18px;
					line-height:40px;
					text-align:center;
				}

			`
		)

	}

}