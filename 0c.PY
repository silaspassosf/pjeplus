CONFIG = {
    'cor_bloqueio_positivo': '#32cd3280',  # Verde gigs-plugin
    'cor_bloqueio_negativo': '#ff270080'   # Vermelho gigs-plugin
}

def _aplicar_cores_status_bloqueio(driver):
    """
    Aplica cores nas linhas da tabela baseado no status de bloqueio,
    exatamente como no gigs-plugin.js: verde se valor bloqueado > 0, vermelho se zero.
    """
    print('[BACEN] Aplicando cores nas linhas da tabela (lógica gigs-plugin.js)...')
    try:
        cor_positivo = CONFIG['cor_bloqueio_positivo']
        cor_negativo = CONFIG['cor_bloqueio_negativo']
        print(f'[BACEN] Cores configuradas: Positivo={cor_positivo}, Negativo={cor_negativo}')

        # Lógica de comparação de linhas adjacentes, fiel ao gigs-plugin.js
        js_aplicar_cores = rf"""
            let linhas_afetadas = 0;
            let el2 = document.querySelectorAll('td[data-label="valorBloquear:"]');
            if (el2.length === 0) {
                // Fallback para a lógica de valor positivo/negativo se a célula específica não for encontrada
                console.log('[BACEN] Fallback: td[data-label="valorBloquear:"] não encontrado. Usando lógica de valor R$.');
                let linhas = Array.from(document.querySelectorAll('table tbody tr'));
                linhas.forEach(function(linha) {{
                    let celulas = Array.from(linha.querySelectorAll('td,th'));
                    for (let cel of celulas) {{
                        let texto = (cel.innerText || '').replace(/\s/g, '');
                        if (texto.includes('R$')) {{
                            let match = texto.match(/R\$([\d\.,]+)/);
                            if (match) {{
                                let valor = match[1].replace(/\./g, '').replace(',', '.');
                                let valorNum = parseFloat(valor);
                                if (!isNaN(valorNum)) {{
                                    if (valorNum < 0.01) {{
                                        linha.style.backgroundColor = '{cor_negativo}';
                                    }} else {{
                                        linha.style.backgroundColor = '{cor_positivo}';
                                    }}
                                    linhas_afetadas++;
                                    break; // Pinta a linha e vai para a próxima
                                }}
                            }}
                        }}
                    }}
                }});
                return {{afetadas: linhas_afetadas, logica: 'fallback'}};
            }}

            // Lógica principal (gigs-plugin.js)
            console.log('[BACEN] Lógica principal: Comparando linhas adjacentes.');
            for (const [pos, item] of el2.entries()) {{
                if (el2[pos+1]) {{ // Se existe um próximo item para comparar
                    let valorPosterior = el2[pos+1].innerText;
                    let valorAtual = item.innerText;
                    if (valorPosterior !== valorAtual) {{
                        item.parentElement.style.backgroundColor = '{cor_positivo}';
                    }} else {{
                        item.parentElement.style.backgroundColor = '{cor_negativo}';
                    }}
                    linhas_afetadas++;
                }} else {{ // Último item da lista, sem próximo para comparar
                    // A lógica original do plugin para o último item é complexa e depende de variáveis externas.
                    // Como comportamento padrão, vamos pintá-lo de verde.
                    item.parentElement.style.backgroundColor = '{cor_positivo}';
                    linhas_afetadas++;
                }}
            }}
            return {{afetadas: linhas_afetadas, logica: 'principal'}};
        """
        resultado = driver.execute_script(js_aplicar_cores)
        if resultado:
            print(f'[BACEN] ✅ Cores aplicadas com sucesso!')
            print(f'[BACEN] Lógica utilizada: {resultado.get("logica", "N/A")}')
            print(f'[BACEN] Total de linhas afetadas: {resultado.get("afetadas", 0)}')
        else:
            print('[BACEN] ⚠️ Nenhum resultado retornado do JavaScript')
    except Exception as e:
        print(f'[BACEN][ERRO] Falha ao aplicar cores nas linhas: {e}')
        import traceback
        traceback.print_exc()
