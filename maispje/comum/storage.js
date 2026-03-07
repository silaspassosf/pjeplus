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
	return new Promise(async resolver => {
		const documentoTratado = new DOMParser().parseFromString(pagina, 'text/html');
		for (const [pos, node] of Object.entries(documentoTratado.body.children)) {
			container.appendChild(node);
		}
		return resolver(true)
	});
}
