async function getLocalStorage(key) {
	return new Promise((resolve, reject) => {
		browser.storage.local.get([key], function (result) {
			if (result[key] === undefined) {
				reject();
			} else {
				resolve(result[key]);
			}
		});
	});
}

function addPaginaFromStorage(pagina, container) {
	const documentoTratado = new DOMParser().parseFromString(pagina, 'text/html');
	Array.from(documentoTratado.body.children).forEach((node, index, array) => {
		container.appendChild(node);
		// console.log('length:', array.length, 'index: ', index, 'node: ', node);    
	})
}
