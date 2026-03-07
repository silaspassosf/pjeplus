function extenso(
	valor = '',
	moeda = false
){
	let termos = [
		['zero','um','dois','três','quatro','cinco','seis','sete','oito','nove','dez','onze','doze','treze','quatorze','quinze','dezesseis','dezessete','dezoito','dezenove'],
		['dez','vinte','trinta','quarenta','cinquenta','sessenta','setenta','oitenta','noventa'],
		['cem','cento','duzentos','trezentos','quatrocentos','quinhentos','seiscentos','setecentos','oitocentos','novecentos'],
		['mil','milhão','bilhão','trilhão','quatrilhão']
	]
	var
		inteiro,
		texto,
		numerico,
		centavo = 'centavo',
		e = ' e ',
		numero = valor.replace(moeda ? /[^,\d]/g : /\D/g,'').split(','),
		real = 'real'
	for(
		var
			largura,
			final = numero.length - 1,
			indice = -1,
			resultado = [],
			termo = '',
			textual = []
		;
		++indice <= final;
		textual = []
	){
		indice && (
			numero[indice] = (
				('.' + numero[indice]) * 1
			).toFixed(2).slice(2)
		)
		if(
			!(
				texto = (
					numerico = numero[indice]
				).slice(
					(largura = numerico.length) % 3
					).match(/\d{3}/g),
				numerico = largura % 3
					? [numerico.slice(0,largura % 3)]
					: [],
					numerico = texto
					? numerico.concat(texto)
					: numerico
				).length
			) continue
		for(
			texto = -1, largura = numerico.length;
			++ texto < largura;
			termo = ''
		){
			if(!(inteiro = numerico[texto] * 1)) continue
			inteiro % 100 < 20 && (termo += termos[0][inteiro % 100]) || inteiro % 100 + 1 && (
				termo += termos[1][(inteiro % 100 / 10 >> 0) - 1] + (
					inteiro % 10
					? e + termos[0][inteiro % 10]
					: ''
				)
			)
			textual.push(
				(
					inteiro < 100
					? termo
					: !(inteiro % 100)
						? termos[2][
						inteiro == 100
							? 0
							: inteiro / 100 >> 0
						]
						: (termos[2][inteiro / 100 >> 0] + e + termo)
				) + (
					(termo = largura - texto - 2) > -1
					? ' ' + (
						inteiro > 1 && termo > 0
						? termos[3][termo].replace('ão', 'ões')
						: termos[3][termo])
					: ''
				)
			)
    }
		texto = (
			(comprimento = textual.length) > 1
			? (texto = textual.pop(), textual.join(' ') + e + texto)
			: textual.join('') || (
				(! indice && (numero[indice + 1] * 1 > 0) || resultado.length)
				? ''
				: termos[0][0]
      )
		)
		texto && resultado.push(
			texto + (
				moeda
				? (
					' ' + (
						numerico.join('') * 1 > 1
						? indice
							? centavo + 's'
							: (
								/0{6,}$/.test(numero[0])
								? 'de '
								: ''
							) + real.replace('l', 'is')
						: indice
						? centavo
						: real
					)
				)
				: ''
			)
		)
  }
	return resultado.join(e);
}