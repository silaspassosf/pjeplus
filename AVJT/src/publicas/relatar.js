/**
 * Verifica se a variável global ${MODO} contém chaves (relatar, diagnostico) ativadas, caso em que executará console.debug em todos os escopos em que esta função foi chamada - isso permite fazer debug tanto em ambiente de desenvolvimento (MODO.relatar = true/false), quanto em ambiente de produção (MODO.diagnosticar = true), onde o valor da chave poderá ser modificado por acionamento de imput na intyerface de usuário:
 * @param  {string} texto
 * @param  {object} objeto
 * @example
 * MODO.relatar = true
 * relatar('Rótulo 1:',objeto1)
 * relatar('Rótulo 2:',objeto2)
 * MODO.relatar = false
 */
 function relatar(
	texto = '',
	objeto = false
){

	MODO.diagnosticar = CONFIGURACAO?.diagnostico?.diagnosticar || false

	if(
		MODO.diagnosticar
		||
		MODO.relatar
	){
		if(!objeto)
			console.debug(texto)
		else
			console.debug(texto,objeto)
	}

}