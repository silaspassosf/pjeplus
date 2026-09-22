//FUNÇÃO QUE RETORNA O(S) PROCESSO(S) VIA API PÚBLICA DO PJE
//  - se "numero" contiver dígitos, consulta por número de processo (consultaProcessosBasicos)
//  - caso contrário, trata "numero" como nome de parte (consultaProcessosAdm)
//Dependências (globais carregadas antes deste arquivo no manifest.json):
//  preferencias (comum/preferencias.js), apis (comum/apis.js), getGrauAsNumber (comum/mini-selenium.js)
async function obterIdProcessoViaApiPublica(numero, funcaoGuia) {
	let soNumeros = numero.toString().trim().replace(/[^0-9]+/g, '');
	// console.log(soNumeros +  " : " + (soNumeros === ''));

	let urlBase = preferencias.trt;
	if (preferencias.trt.includes('dev015')) { urlBase = preferencias.trt.replace('dev015', 'pje') }

	let url = (soNumeros === '') ? apis.consultaProcessosAdm.montarUrl(urlBase, { 'nomeParte': numero, 'guia': funcaoGuia }) : apis.consultaProcessosBasicos.montarUrl(urlBase, { 'numero': numero, 'guia': funcaoGuia });

	const grau_usuario = getGrauAsNumber(preferencias.grau_usuario);

	return fetch(url,
		{
			method: "GET",
			mode: "cors",
			credentials: "include",
			headers: {
				"Content-Type": "application/json",
				"X-Grau-Instancia": grau_usuario || 1
			}
		})
		.then(function (response) {
			return response.json();
		})
		.then(data => {
			// {
			// 	"id": 489839,
			// 	"numeroIdentificacaoJustica": 512,
			// 	"numero": "0048000-20.2007.5.12.0004",
			// 	"classe": "ATOrd",
			// 	"codigoOrgaoJulgador": "0600",
			// 	"juizoDigital": false
			//   }

			// {
			// 	"id": 427609,
			// 	"numeroIdentificacaoJustica": 512,
			// 	"numero": "0000202-09.2018.5.12.0059",
			// 	"classe": "ATOrd",
			// 	"codigoOrgaoJulgador": "0059",
			// 	"juizoDigital": false
			//   }
			return data || '';
		})
		.catch(function (err) {
			console.error(err);
			return '';
		});
}
