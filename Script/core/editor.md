# Integração de Textos Copiados com o CKEditor do PJe

Ao injetar texto no editor rico (CKEditor) do PJe via scripts (Greasemonkey/Tampermonkey), se usarmos apenas `navigator.clipboard.writeText()`, o CKEditor colará texto plano, descartando alinhamentos, negritos, itálicos e recuos que são importantes para despachos e decisões.

Para que os documentos e as tabelas caiam perfeitamente na janela do editor (como se tivessem sido digitados no próprio sistema), devemos criar e injetar blocos HTML usando a API `execCommand('copy')` em um conteúdo de seleção HTML.

## A Estrutura do PJe (Classe `.corpo` e Estilos Embutidos)

O PJe formata seus despachos baseado nas tags de parágrafo `<p>` recebendo o estilo embutido e a classe `.corpo`. 

Ao gerar sua string HTML de saída no JS, use o padrão de parágrafo:

```html
<p class="corpo" style="font-size:12pt;line-height:1.5;margin-left:0 !important;text-align:justify;text-indent:4.5cm;">O seu texto formatado aqui.</p>
```

Variáveis que você pode controlar livremente no estilo do parágrafo:
- `text-align: center;` (Para títulos como **DESPACHO**, **CONCLUSÃO**, **Assinaturas**)
- `text-align: justify !important;` (Para o texto corrido padrão do documento)
- `text-indent: 4.5cm;` (Recuo padrão da primeira linha adotado pelas VTs)

### Tags Especiais
Ao compor a string HTML, as seguintes marcações simples funcionam bem por cima do `<p>`:
- Negrito: Use `<strong>Texto</strong>`
- Sublinhado: Use `<u>Texto</u>`
- Quebra de linha vazia oficial (Para saltar espaços no PJe sem o editor colapsar): `<br data-cke-filler="true">`

## Função Universal de Cópia (HTML to Clipboard)

O código abaixo deve ser usado em seus scripts ao invés de `writeText`. Ele renderiza o HTML no DOM de forma invisível, copia com a seleção de formatação e limpa o documento. O CTRL+V no PJe sairá idêntico:

```javascript
function copyHtmlToClipboard(htmlContent) {
    var container = document.createElement('div');
    container.innerHTML = htmlContent;
    
    // Oculta o div de renderização fora da tela
    container.style.position = 'absolute';
    container.style.left = '-9999px';
    document.body.appendChild(container);
    
    // Seleciona o conteúdo como se fosse o usuário
    var range = document.createRange();
    range.selectNodeContents(container);
    var selection = window.getSelection();
    selection.removeAllRanges();
    selection.addRange(range);
    
    try {
        // Envia o HTML rico para a área de transferência do Windows
        var success = document.execCommand('copy');
        
        // Faxina
        document.body.removeChild(container);
        selection.removeAllRanges();
        
        return success;
    } catch (err) {
        if (document.body.contains(container)) document.body.removeChild(container);
        console.error('Erro ao copiar html:', err);
        return false;
    }
}
```

Usando essa função, seu script passará as tabelas, negritos e o layout de petição intactos para a área de edição.
