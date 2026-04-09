//ATIVAR LGPD
async function ativarLGPD() {
  console.log("ativarLGPD");
  //font-family: "Libre Barcode 39", serif;
  let link1 = document.createElement("link");
  link1.rel = "preconnect";
  link1.href = "https://fonts.googleapis.com";

  let link2 = document.createElement("link");
  link2.rel = "preconnect";
  link2.href = "https://fonts.gstatic.com";
  link2.setAttribute("crossorigin", "");

  let link3 = document.createElement("link");
  link3.rel = "stylesheet";
  link3.href =
    "https://fonts.googleapis.com/css2?family=Redacted+Script:wght@300;400;700&display=swap";

  document.body.appendChild(link1);
  document.body.appendChild(link2);
  document.body.appendChild(link3);
  browser.runtime.sendMessage({ tipo: "insertCSS", file: "maisPje_lgpd.css" });
}

//ATIVAR MODO NOITE
/**
 *
 * @param {boolean} ligar
 */
async function ativarModoNoite(ligar) {
  let filtro = "";
  ligarMOModoNoite();

  if (ligar) {
    console.log("ativarModoNoite");
    filtro = "invert(.93) hue-rotate(180deg) brightness(.8)";
    document.querySelector("html").style.filter = filtro;

    if (document.location.href.includes(".jus.br/pjekz/")) {
      //elementos excluídos do modo noturno
      inverterCor("pje-cabecalho", filtro);
      inverterCor("pje-resumo-processo", filtro);
      inverterCor("menumaispje", filtro);
      inverterCor("#brasao-republica", "revert");
      inverterCor('img[alt="Foto do perfil do usuário"]', "revert");
    }
  } else {
    console.log("desativarModoNoite");
    filtro = "revert";
    document.querySelector("html").style.filter = filtro;

    if (document.location.href.includes(".jus.br/pjekz/")) {
      //elementos excluídos do modo noturno
      inverterCor("pje-cabecalho", "revert");
      inverterCor("pje-resumo-processo", "revert");
      inverterCor("menumaispje", "revert");
      inverterCor("#brasao-republica", "revert");
      inverterCor('img[alt="Foto do perfil do usuário"]', "revert");

      let icos = document.querySelectorAll('img[src*="icone-KZ"]');
      let limparIcos = [].map.call(icos, function (ico) {
        ico.style.filter = "revert";
      });
    }
  }

  async function inverterCor(seletor, filtro) {
    return new Promise(async (resolve) => {
      // console.log(seletor + ': ' + filtro)
      let elemento = await esperarElemento(seletor);
      if (elemento) {
        elemento.style.filter = filtro;
      }
      return resolve(true);
    });
  }

  function ligarMOModoNoite() {
    return new Promise(async (resolve) => {
      if (!document.body) {
        return null;
      }
      let observer = new MutationObserver(function (mutationsDocumento) {
        mutationsDocumento.forEach(function (mutation) {
          const primeiroItem = mutation.addedNodes[0];
          if (primeiroItem && primeiroItem instanceof HTMLElement) {
            // console.log("***[ADD] tagName(" + primeiroItem.tagName + ") id(" + primeiroItem.id + ") className(" + primeiroItem.className + ")");

            if (primeiroItem.tagName == "PJE-CABECALHO") {
              primeiroItem.style.filter = filtro;
              const brasao = primeiroItem.querySelector("#brasao-republica");
              if (brasao && brasao instanceof HTMLElement) {
                brasao.style.filter = "revert";
              }
            }

            if (primeiroItem.tagName == "PJE-RESUMO-PROCESSO") {
              primeiroItem.style.filter = filtro;
            }

            if (primeiroItem.tagName == "MENUMAISPJE") {
              primeiroItem.style.filter = filtro;
            }

            if (primeiroItem.tagName == "IMG") {
              if (primeiroItem.className.includes("foto-perfil")) {
                primeiroItem.style.filter = "revert";
              }
            }

            if (primeiroItem.tagName == "TR") {
              const icone = primeiroItem.querySelector('img[src*="icone-KZ"]');
              if (icone && icone instanceof HTMLElement) {
                icone.style.filter = filtro;
              }
            }
          }
        });
      });
      let configDocumento = { childList: true, subtree: true };
      observer.observe(document.body, configDocumento);
    });
  }
}
