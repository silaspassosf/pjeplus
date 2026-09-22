/**
 * @param {string} data 'dd/mm/aaaa'
 */
 function dataLocalParaISO(data=''){
	let local = data.replace(/(\d{2}).(\d{2}).(\d{4})/,'$3-$2-$1')
	return local
}

/**
 * @param {string} data 'aaaa-mm-ddThh:mm:ss.sss'
 */
function dataLocalCurta(data=''){
	let dataNova = new Date(data)
	let dataLocal = dataNova.toLocaleDateString() || ''
	return dataLocal || ''
}