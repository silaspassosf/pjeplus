Entendi! O problema é que o layout flex do CSS estava tentando acomodar todos os elementos numa mesma linha ou empurrá-los de forma estranha quando a checkbox "FGTS apurado separado?" estava marcada, quebrando o alinhamento com a linha de cima.

Para resolver isso, vamos reorganizar o HTML da seção do FGTS no arquivo `hcalc-overlay.js` usando a mesma estrutura de grid que você já usava nas linhas de cima (as colunas `col`), garantindo que o checkbox e o valor fiquem bem alinhados.

No arquivo **`hcalc-overlay.js`**, localize a seção do HTML que desenha a parte do FGTS (por volta da linha **366** até **388**).

**Substitua todo este bloco:**

```html
                    <div class="row row-fgts-block" style="align-items: flex-end; gap: 20px; flex-wrap: wrap; margin-top: 6px;">
                        <div class="col col-fgts-chk" style="flex: 0 0 auto;">
                            <label class="fgts-label" style="font-size: 12px; margin-bottom: 4px; display: block;">FGTS</label>
                            <label style="display: flex; align-items: center; gap: 6px; margin: 0; font-size: 12px;"><input type="checkbox" id="calc-fgts" checked> FGTS apurado separado?</label>
                        </div>
                        <div class="col" id="row-fgts-valor" style="flex: 0 0 auto; display: flex; align-items: flex-end; gap: 16px;">
                            <div class="col" id="col-fgts-val" style="flex: 0 0 auto;">
                                <label class="fgts-label" style="font-size: 12px; margin-bottom: 4px; display: block;">Valor FGTS Separado</label>
                                <input type="text" id="val-fgts" class="coleta-input" placeholder="R$ FGTS" style="width: 140px; box-sizing: border-box;">
                            </div>
                            <div class="col" id="fgts-radios" style="flex: 0 0 auto;">
                                <label class="fgts-label" style="font-size: 12px; margin-bottom: 4px; display: block;">Situação</label>
                                <div style="display: flex; gap: 12px; align-items: center; min-height: 28px;">
                                    <label style="display: flex; align-items: center; gap: 6px; margin: 0; font-size: 12px;"><input type="radio" name="fgts-tipo" value="devido" checked> Devido</label>
                                    <label style="display: flex; align-items: center; gap: 6px; margin: 0; font-size: 12px;"><input type="radio" name="fgts-tipo" value="depositado"> Depositado</label>
                                </div>
                            </div>
                        </div>
                        <div class="col" style="flex: 0 0 auto;">
                            <label class="fgts-label" style="font-size: 12px; margin-bottom: 4px; display: block;">&nbsp;</label>
                            <label style="display: flex; align-items: center; gap: 6px; margin: 0; font-size: 12px;"><input type="checkbox" id="calc-fgts-alvara"> Dispensa imotivada? (Alvará pela Secretaria)</label>
                        </div>
                    </div>

```

**Pelo seguinte bloco:**

```html
                    <div class="row row-fgts-block" style="margin-top: 6px;">
                        <div class="col" style="flex: 0 0 140px;">
                            <label class="fgts-label">FGTS</label>
                            <label style="display: flex; align-items: center; gap: 6px; margin: 0; font-size: 12px; min-height: 28px;"><input type="checkbox" id="calc-fgts" checked> FGTS apurado separado?</label>
                            
                            <div id="row-fgts-valor" style="margin-top: 6px;">
                                <label class="fgts-label">Valor FGTS Separado</label>
                                <input type="text" id="val-fgts" class="coleta-input" placeholder="R$ FGTS">
                            </div>
                        </div>

                        <div class="col" id="fgts-opcoes" style="flex: 1; align-self: flex-start; margin-top: 19px;">
                             <div style="display: flex; align-items: center; gap: 15px; flex-wrap: wrap; min-height: 28px;">
                                 <div id="fgts-radios" style="display: flex; align-items: center; gap: 12px;">
                                     <label style="font-size: 11px; font-weight: bold; margin: 0;">Situação:</label>
                                     <label style="display: flex; align-items: center; gap: 6px; margin: 0; font-size: 12px;"><input type="radio" name="fgts-tipo" value="devido" checked> Devido</label>
                                     <label style="display: flex; align-items: center; gap: 6px; margin: 0; font-size: 12px;"><input type="radio" name="fgts-tipo" value="depositado"> Depositado</label>
                                 </div>
                                 <div style="width: 1px; height: 20px; background: #ddd;"></div>
                                 <label style="display: flex; align-items: center; gap: 6px; margin: 0; font-size: 12px;"><input type="checkbox" id="calc-fgts-alvara"> Dispensa imotivada? (Alvará)</label>
                             </div>
                        </div>
                    </div>

```

**E depois, precisamos ajustar o listener do Javascript** para que ele não esconda o bloco todo de opções (já que agora o alvará fica ao lado do checkbox).

No mesmo arquivo (`hcalc-overlay.js`), vá para a linha **~662** (dentro do `$('calc-fgts').onchange`).

**Altere esta parte:**

```javascript
        $('calc-fgts').onchange = (e) => {
            const isChecked = e.target.checked;
            $('fgts-radios').classList.toggle('hidden', !isChecked);
            $('row-fgts-valor').classList.toggle('hidden', !isChecked);
            updateHighlight();

```

**Para isto:**

```javascript
        $('calc-fgts').onchange = (e) => {
            const isChecked = e.target.checked;
            $('fgts-radios').classList.toggle('hidden', !isChecked);
            $('row-fgts-valor').classList.toggle('hidden', !isChecked);
            $('calc-fgts-alvara').parentElement.classList.toggle('hidden', !isChecked);
            updateHighlight();

```

### O que essa alteração faz:

1. **Alinhamento do Checkbox**: A `div` da coluna esquerda (`flex: 0 0 140px;`) garante que o "FGTS apurado separado?" fique perfeitamente alinhado abaixo do "Id da Planilha".
2. **Valor Embaixo**: O `row-fgts-valor` foi colocado dentro da mesma coluna esquerda, logo abaixo do checkbox.
3. **Opções na Horizontal**: Os radios de Situação e o checkbox de Alvará foram colocados em um contêiner flexível ao lado direito. A margem `margin-top: 19px` empurra eles exatamente para a mesma linha horizontal do checkbox principal. Uma pequena barra vertical (`|`) foi adicionada para separar os botões de radio do checkbox de dispensa.

Atualize o código e não esqueça do `t=` do `@require` no seu loader para ver a mágica acontecer!