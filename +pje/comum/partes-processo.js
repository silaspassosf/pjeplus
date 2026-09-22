//FUNÇÃO QUE RETORNA PARTES DO PROCESSO
async function obterPartesDoProcesso(idProcesso, comPosicao=true) { //comPosicao trará um numeral na frente do nome da parte caso exista mais de uma no mesmo polo
	return new Promise(async resolve => {
		
		if (!idProcesso) {
			alert("maisPje: " + idProcesso + " não encontrado [ERRO1].");
			return resolve('ERRO1');
		}

		const dados = await apis.partesProcesso.executar(preferencias.trt, {idProcesso});

		let poloAtivo = [];
		let poloPassivo = [];
		let poloOutros = [];

		for (const [pos, parte] of dados.ATIVO.entries()) {
			let nome = parte.nome.trim();
			if (dados.ATIVO.length > 1) { nome = (comPosicao) ? (pos+1) + '. ' + nome : nome }
			let cpfcnpj = (parte.documento) ? parte.documento : "desconhecido";

			//primeiro pega o celular depois o numero residencial e por fim o comercial
			let telefone = 'desconhecido';
			if (parte?.pessoaFisica) {
				telefone = (parte.pessoaFisica.dddCelular) ? '(' + parte.pessoaFisica.dddCelular + ') ' + parte.pessoaFisica.numeroCelular : "";
				telefone += (parte.pessoaFisica.dddResidencial) ? ' (' + parte.pessoaFisica.dddResidencial + ') ' + parte.pessoaFisica.numeroResidencial : "";
				telefone += (parte.pessoaFisica.dddComercial) ? ' (' + parte.pessoaFisica.dddComercial + ') ' + parte.pessoaFisica.numeroComercial : "";
			}

			poloAtivo.push({'nome':nome,'cpfcnpj':cpfcnpj,'tipo':'AUTOR','telefone':telefone});

			//obter advogados
			if (parte.representantes) {
				[].map.call(
					parte.representantes,
					function(representante) {
						let cpfcnpj = (representante.documento) ? representante.documento : "desconhecido"
						poloOutros.push({'nome':representante.nome.trim(),'cpfcnpj':cpfcnpj,'tipo':representante.tipo + ' do AUTOR'});
					}
				);
			}
		}

		for (const [pos, parte] of dados.PASSIVO.entries()) {
			let nome = parte.nome.trim();
			if (dados.PASSIVO.length > 1) { nome = (comPosicao) ? (pos+1) + '. ' + nome : nome }
			let cpfcnpj = (parte.documento) ? parte.documento : "desconhecido"
			poloPassivo.push({'nome':nome,'cpfcnpj':cpfcnpj,'tipo':'RÉU'});
			//obter advogados
			if (parte.representantes) {
				[].map.call(
					parte.representantes,
					function(representante) {
						let cpfcnpj = (representante.documento) ? representante.documento : "desconhecido"
						poloOutros.push({'nome':representante.nome.trim(),'cpfcnpj':cpfcnpj,'tipo':representante.tipo + ' do RÉU'});
					}
				);
			}
		}

		if (dados.TERCEIROS) {
			for (const [pos, parte] of dados.TERCEIROS.entries()) {
				let nome = parte.nome.trim();
				if (dados.TERCEIROS.length > 1) { nome = (comPosicao) ? (pos+1) + '. ' + nome : nome }
				let cpfcnpj = (parte.documento) ? parte.documento : "desconhecido";
				poloOutros.push({'nome':nome,'cpfcnpj':cpfcnpj,'tipo':parte.tipo});
				//obter advogados
				if (parte.representantes) {
					[].map.call(
						parte.representantes,
						function(representante) {
							let cpfcnpj = (representante.documento) ? representante.documento : "desconhecido"
							poloOutros.push({'nome':representante.nome.trim(),'cpfcnpj':cpfcnpj,'tipo':representante.tipo + ' de ' + parte.nome.trim()});
						}
					);
				}
			}
		}

		return resolve({"poloAtivo":poloAtivo,"poloPassivo":poloPassivo,"poloOutros":poloOutros});
	});
}
