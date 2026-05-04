# Guia: OCR via API no Tampermonkey (PJe)

## Premissas do cenário

- PDF chega via endpoint (já implementado)
- Extração de texto nativo já funciona — OCR é o **fallback** para PDFs escaneados
- Normalmente **só a 1ª página resolve** — processar mais só se faltar dados
- Sem dependências pesadas locais, sem token LLM

***

## Estratégia: OCR por demanda, página a página

Em vez de enviar o PDF inteiro, a abordagem é:

1. Renderizar **apenas a página 1** como imagem via `pdf.js`
2. Enviar o base64 da imagem para o OCR.space
3. Validar se os dados necessários estão presentes
4. Se não, repetir para a página 2 — e assim por diante

Isso é mais rápido, respeita o limite de 1MB por requisição da tier gratuita, e evita processamento desnecessário.

***

## Implementação completa

```javascript
// ==UserScript==
// @name         PJe OCR Fallback
// @require      https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js
// @grant        GM_xmlhttpRequest
// ==/UserScript==

const OCR_API_KEY = 'SUA_CHAVE_AQUI'; // gratuita: 'helloworld' (25k req/mês)
const MAX_PAGINAS = 2; // raramente passa disso

// Renderiza uma página do PDF como base64 PNG
async function renderizarPaginaBase64(pdfBytes, numeroPagina) {
  const pdf = await pdfjsLib.getDocument({ data: pdfBytes }).promise;

  if (numeroPagina > pdf.numPages) return null;

  const page = await pdf.getPage(numeroPagina);
  const viewport = page.getViewport({ scale: 2.0 }); // scale 2x para melhor OCR

  const canvas = document.createElement('canvas');
  canvas.width = viewport.width;
  canvas.height = viewport.height;

  await page.render({
    canvasContext: canvas.getContext('2d'),
    viewport
  }).promise;

  // Remove o prefixo "data:image/png;base64," — OCR.space recebe só o base64
  return canvas.toDataURL('image/png').split(',')[1];
}

// Envia imagem base64 para OCR.space e retorna o texto
function ocr_pagina(base64PNG) {
  return new Promise((resolve, reject) => {
    GM_xmlhttpRequest({
      method: 'POST',
      url: 'https://api.ocr.space/parse/image',
      headers: {
        'apikey': OCR_API_KEY,
        'Content-Type': 'application/x-www-form-urlencoded'
      },
      // OCREngine=2 é mais preciso para documentos com tabelas
      data: `base64Image=data:image/png;base64,${base64PNG}&isOverlayRequired=false&OCREngine=2&language=por`,
      onload: (res) => {
        const json = JSON.parse(res.responseText);
        if (json.IsErroredOnProcessing) {
          reject(json.ErrorMessage);
        } else {
          resolve(json.ParsedResults[0]?.ParsedText || '');
        }
      },
      onerror: reject
    });
  });
}

// Verifica se o texto extraído tem os dados mínimos necessários
function temDadosSuficientes(texto) {
  // Adapte conforme o que você precisa extrair do cálculo PJe
  // Exemplo: considera suficiente se encontrar "Total" e pelo menos um valor monetário
  return /Total/i.test(texto) && /\d+\.\d{3},\d{2}/.test(texto);
}

// Função principal: OCR progressivo por página
async function extrairViaOCR(pdfBytes) {
  let textoAcumulado = '';

  for (let pagina = 1; pagina <= MAX_PAGINAS; pagina++) {
    console.log(`[OCR] Processando página ${pagina}...`);

    const base64 = await renderizarPaginaBase64(pdfBytes, pagina);

    if (!base64) {
      console.log(`[OCR] Página ${pagina} não existe. Encerrando.`);
      break;
    }

    const texto = await ocr_pagina(base64);
    textoAcumulado += texto + '\n';

    if (temDadosSuficientes(textoAcumulado)) {
      console.log(`[OCR] Dados suficientes encontrados na página ${pagina}.`);
      break;
    }

    console.log(`[OCR] Página ${pagina} insuficiente. Indo para próxima...`);
  }

  return textoAcumulado;
}

// Exemplo de uso: pdfBytes vem do fetch do seu endpoint já implementado
// const pdfBytes = await fetch(urlDoPdf).then(r => r.arrayBuffer());
// const texto = await extrairViaOCR(new Uint8Array(pdfBytes));
```

***

## Pontos de atenção

| Aspecto | Detalhe |
|---|---|
| **Scale do canvas** | `scale: 2.0` melhora muito a precisão do OCR em tabelas pequenas |
| **OCREngine=2** | Mais lento mas muito mais preciso que Engine=1 para documentos tabulares |
| **`language=por`** | Melhora reconhecimento de caracteres com acento |
| **Limite gratuito** | 25k req/mês, máx ~5MB por imagem — uma página renderizada em 2x fica ~800KB, tranquilo |
| **`temDadosSuficientes()`** | **Adapte essa função** para checar os campos que você realmente precisa extrair do cálculo |

***

## Fluxo de execução

```
pdfBytes (já tem) → renderiza pg 1 como PNG (canvas, scale 2x)
        │
        ▼
  POST OCR.space → texto da pg 1
        │
   tem dados? ──── SIM ──→ retorna texto
        │
       NÃO
        │
        ▼
  renderiza pg 2 → POST OCR.space → acumula texto → retorna
```