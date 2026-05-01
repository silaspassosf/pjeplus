const idVisualizadorDocumentos = "maisPJE_visualizadorDocumentos";

/**
 * @param {string} pdfUrl
 * @param {boolean} ajustarJanela
 */
function abrirFecharVisualizador(pdfUrl, ajustarJanela) {
    const container = document.querySelector("#" + idVisualizadorDocumentos);
    const iframe = container.querySelector("iframe");
    if (iframe.src !== pdfUrl) {
        iframe.src = pdfUrl;
        if (!container.classList.contains("visible")) {
            container.classList.toggle("visible");
        }
    } else {
        //se for o mesmo botão, apenas alterna a visualização
        container.classList.toggle("visible");
    }
    ajustarTamanhoJanelaVisualizadorDocumentos(ajustarJanela);
}

function ajustarTamanhoJanelaVisualizadorDocumentos(ajustarJanela) {
    if (ajustarJanela) {
        const container = document.querySelector(
            "#" + idVisualizadorDocumentos
        );
        if (!container.classList.contains("visible")) {
            document.body.style.width = "auto";
        } else {
            document.body.style.width = `calc(100vw - ${container.style.width})`;
        }
    }
}

function criarContainerVisualizadorDocumentos(ajustarJanela) {
    let container = document.querySelector("#" + idVisualizadorDocumentos);
    // se ja criou, ja retorna ele.
    if (container) {
        return container;
    }
    browser.runtime.sendMessage({
        tipo: "insertCSS",
        file: "comum/visualizador-documentos.css",
    });
    // Criar o container
    container = document.createElement("section");
    container.id = idVisualizadorDocumentos;
    const titulo = document.createElement("h2");
    titulo.innerText = "Visualizador de documentos maisPJE";
    titulo.classList = "sr-only";
    container.appendChild(titulo);
    // Criar o iframe
    const iframe = document.createElement("iframe");
    iframe.id = "iframe-documentos";
    iframe.title = "Visualizador de documentos";
    iframe.sandbox = "allow-scripts allow-same-origin allow-forms";

    const resizer = document.createElement("div");
    resizer.id = "pdf-resizer";
    resizer.innerText = "⋮";
    resizer.setAttribute("aria-hidden", true);

    container.appendChild(resizer);
    container.appendChild(iframe);

    browser.storage.local.get(["larguraVisualizadorDocumentos"], (result) => {
        const width = result.larguraVisualizadorDocumentos || 550;
        container.style.width = width + "px";
        ajustarTamanhoJanelaVisualizadorDocumentos(ajustarJanela);
    });

    const fecharVisualizador = () => {
        container.classList.toggle("visible");
        ajustarTamanhoJanelaVisualizadorDocumentos(ajustarJanela);
    };

    if (preferencias.extrasExibirPreviaDocumentoMouseOver) {
        container.addEventListener("mouseleave", fecharVisualizador);
    } else {
        const closeBtn = document.createElement("button");
        closeBtn.id = "close-pdf-btn";
        closeBtn.innerText = "🡲";
        closeBtn.addEventListener('click', fecharVisualizador);
        vincularTooltipAcessivel(
            closeBtn,
            "Recolher visualizador de documentos maisPJE"
        );
        container.appendChild(closeBtn);
    }

    // 3. Redimensionamento (Resizer)
    let isResizing;

    resizer.addEventListener("mousedown", (e) => {
        isResizing = true;
        document.body.style.cursor = "ew-resize";
        // Desativa pointer-events no iframe para o mouse não "sumir" dentro dele ao arrastar
        iframe.style.pointerEvents = "none";
    });

    document.addEventListener("mousemove", (e) => {
        if (!isResizing) return;

        // Calcula a nova largura baseada na posição do mouse em relação à direita da tela
        const newWidth = window.innerWidth - e.clientX;

        if (newWidth > 200 && newWidth < window.innerWidth * 0.8) {
            // Limites min/max
            container.style.width = newWidth + 50 + "px"; //se eu não der o +50px o mouse escapa do listener e ocorre um bug no redimensionamento da largura da janela
            ajustarTamanhoJanelaVisualizadorDocumentos(ajustarJanela);
        }
    });

    document.addEventListener("mouseup", () => {
        if (isResizing) {
            isResizing = false;
            document.body.style.cursor = "default";
            iframe.style.pointerEvents = "auto";

            // Salvar no Storage
            browser.storage.local.set({
                larguraVisualizadorDocumentos: parseInt(container.style.width),
            });
            ajustarTamanhoJanelaVisualizadorDocumentos(ajustarJanela);
        }
    });

    document.body.appendChild(container);
    return container;
}
