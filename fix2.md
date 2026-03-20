# Refatoração: `extracao_documento.py`

## Contexto

O arquivo `extracao_documento.py` precisa ser reescrito mantendo **exatamente a mesma assinatura** da função pública `extrair_direto`. Nenhuma outra parte do código precisa ser alterada.

Descobrimos via testes no browser que:
- Documentos HTML e PDF no PJe são renderizados pelo mesmo elemento: `object.conteudo-pdf`
- O `contentDocument` desse objeto contém o `#viewer` com o conteúdo
- A detecção do tipo é feita por `typeof pdfjsLib` no `contentDocument`
- Para **PDF**: usa `pdfjsLib.getDocument(blobUrl)` — sem scroll, todas as páginas
- Para **HTML**: usa `#viewer innerText` — sem scroll, tudo disponível
- Worker confirmado em: `/pjekz/assets/pdf/build/pdf.worker.js`

---

## Resultado esperado

Um único arquivo Python limpo com:
1. `extrair_direto` — função pública, mesma assinatura de sempre
2. `_extrair_objeto_pje` — detecta HTML ou PDF e extrai via JS
3. `_formatar_texto` — formata saída para ambos os tipos, preservando estrutura de tabelas
4. Funções auxiliares mínimas necessárias

---

## Assinatura pública — NÃO ALTERAR

```python
def extrair_direto(
    driver: WebDriver,
    timeout: int = 10,
    debug: bool = False,
    formatar: bool = True
) -> Dict[str, Any]:
    """
    Extrai o conteúdo do documento ativo na tela do processo PJe.
    SEM CLIQUES, SEM SCROLL, SEM INTERAÇÃO — HTML ou PDF.
    Retorna dict com: sucesso, metodo, tipo_doc, conteudo, conteudo_bruto, chars, info
    """
JavaScript confirmado e testado — usar exatamente este
javascript
// _JS_EXTRAIR_OBJECT — detecta tipo e extrai
var callback = arguments[arguments.length - 1];
try {
    var obj = document.querySelector("object.conteudo-pdf");
    if (!obj) { callback({tipo: null, texto: null}); return; }

    var inner = obj.contentDocument;
    if (!inner) { callback({tipo: null, texto: null}); return; }

    if (typeof inner.defaultView.pdfjsLib !== 'undefined') {
        // PDF: API interna do PDF.js — sem scroll, todas as páginas
        var pdfjsLib = inner.defaultView.pdfjsLib;
        var blobUrl  = new inner.defaultView.URLSearchParams(
                           inner.defaultView.location.search
                       ).get("file");

        pdfjsLib.GlobalWorkerOptions.workerSrc = "/pjekz/assets/pdf/build/pdf.worker.js";
        pdfjsLib.getDocument(blobUrl).promise.then(function(pdf) {
            var promises = [];
            for (var i = 1; i <= pdf.numPages; i++) {
                promises.push(
                    pdf.getPage(i).then(function(p) {
                        return p.getTextContent();
                    }).then(function(c) {
                        // Reconstrói linhas por coordenada Y (tolerância 4px)
                        var linhas = {};
                        c.items
                         .filter(function(it) { return it.str.trim(); })
                         .forEach(function(it) {
                             var y = Math.round(it.transform);
                             var k = Object.keys(linhas).find(function(k) {
                                 return Math.abs(parseInt(k) - y) <= 4;
                             }) || String(y);
                             if (!linhas[k]) linhas[k] = [];
                             linhas[k].push({str: it.str, x: Math.round(it.transform)});[1]
                         });
                        return Object.keys(linhas)
                            .map(Number).sort(function(a,b){ return b - a; })
                            .map(function(y) {
                                return linhas[y]
                                    .sort(function(a,b){ return a.x - b.x; })
                                    .map(function(i){ return i.str.trim(); })
                                    .filter(Boolean).join(" | ");
                            }).join("\n");
                    })
                );
            }
            return Promise.all(promises);
        }).then(function(paginas) {
            callback({tipo: "pdf", texto: paginas.join("\n\n--- PÁGINA ---\n\n")});
        }).catch(function(e) {
            callback({tipo: "pdf_erro", texto: null, erro: e.message});
        });

    } else {
        // HTML: innerText do #viewer — sem scroll
        var viewer = inner.querySelector("#viewer");
        if (!viewer) { callback({tipo: null, texto: null}); return; }
        var texto = (viewer.innerText || viewer.textContent || "").trim();
        callback({tipo: "html", texto: texto.length > 50 ? texto : null});
    }

} catch(e) { callback({tipo: null, texto: null, erro: e.message}); }
Regras de formatação — _formatar_texto(texto, tipo_doc)
Para HTML (tipo_doc == "html"):
Normalizar espaços e quebras de linha excessivas

Detectar e marcar títulos (linhas curtas em maiúsculo ou com palavras-chave: DECISÃO, DESPACHO, SENTENÇA, CONCLUSÃO, VISTOS) → \n=== TÍTULO ===\n

Detectar decisões (linhas começando com DEFIRO, INDEFIRO, DETERMINO, HOMOLOGO) → \n>>> DECISÃO

Detectar assinaturas → \n--- assinatura ---

Detectar datas isoladas → \n[data]

Para PDF (tipo_doc == "pdf"):
Preservar separadores --- PÁGINA --- entre páginas

Detectar linhas de tabela: se a linha contém | com 3 ou mais colunas, é uma linha de tabela — alinhar colunas com espaçamento fixo usando str.ljust()

Detectar cabeçalho de tabela: primeira linha de tabela de cada bloco → \n=== TABELA ===\n antes dela

Detectar totais/subtotais: linhas com palavras "Total", "Subtotal", "Líquido", "Bruto" → negrito simulado com ** texto **

Preservar valores monetários intactos (R$ X.XXX,XX)

Estrutura completa do arquivo
python
"""
Fix.extracao_documento - Extração direta de documentos PJe.
Suporta HTML e PDF via object.conteudo-pdf — sem scroll, headless-safe.
"""
import re
import logging
from typing import Optional, Dict, Any

from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from Fix.log import logger

# 1. _JS_EXTRAIR_OBJECT  → constante com o JS acima
# 2. _extrair_objeto_pje(driver, timeout, debug) → executa o JS, retorna dict {tipo, texto}
# 3. _formatar_html(texto) → formatação específica HTML
# 4. _formatar_pdf(texto)  → formatação específica PDF com tabelas
# 5. _formatar_texto(texto, tipo_doc) → dispatcher para _formatar_html ou _formatar_pdf
# 6. _extrair_info_documento(driver, debug) → extrai metadados (mat-card-title, id do doc)
# 7. extrair_direto(driver, timeout, debug, formatar) → função pública principal
Comportamento esperado do retorno de extrair_direto
python
{
    'sucesso': True,
    'metodo': 'objeto_pje',        # fixo para ambos os tipos
    'tipo_doc': 'pdf',             # 'pdf' | 'html' | 'desconhecido'
    'conteudo': '...',             # texto formatado
    'conteudo_bruto': '...',       # texto sem formatação
    'chars': 2336,
    'info': {
        'titulo': 'Id 5b7b799 - Liberação despacho',
        'subtitulos': [...],
        'documento_id': '5b7b799'
    }
}
O que NÃO deve estar no arquivo
extrair_documento — removida (usa clique no botão HTML, fluxo separado)

extrair_pdf — removida (usa modal de exportação, fluxo separado)

_normalizar_texto_decisao — absorvida pela _formatar_html

_extrair_linha_tipo — absorvida pela _formatar_html

Qualquer uso de switch_to.frame, scrollIntoView, time.sleep, scrollTo

Estratégias de iframe externo e DOM que se provaram incorretas nos testes

Imports necessários
python
import re
import logging
from typing import Optional, Dict, Any
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from Fix.log import logger