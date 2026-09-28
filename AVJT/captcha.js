async function resolverCaptchas(){
	if(!JANELA.includes('google.com/recaptcha')) return
	if(!CONFIGURACAO.assistenteDeSelecao.resolverCaptchas) return
	let captcha = await esperar('#recaptcha-anchor div.recaptcha-checkbox-checkmark',true,true)
	if(!captcha) return
	if(captcha.offsetWidth > 0 || captcha.offsetHeight > 0){
		let resolver = true
		if(sessionStorage.getItem('avjt')){
			if (new Date().getTime() - sessionStorage.getItem('avjt') < 7000) resolver = false
		}
		if(resolver){
			sessionStorage.setItem('avjt', new Date().getTime())
			let espera = inteiroAleatorio(250,1100)
			await aguardar(espera)
			clicar(captcha)
		}
	}
}