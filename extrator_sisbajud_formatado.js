
(function() {
    console.log("Iniciando extração de dados SISBAJUD...");

    try {
        // Função para extrair texto limpo de um elemento
        function getCleanText(selector) {
            const element = document.querySelector(selector);
            if (element) {
                return element.textContent.trim();
            }
            return null;
        }

        // Função para extrair texto usando o texto do label
        function getValueByLabel(labelText) {
            const labels = Array.from(document.querySelectorAll('.sisbajud-label'));
            const targetLabel = labels.find(label => label.textContent.trim().includes(labelText));

            if (targetLabel) {
                const valueElement = targetLabel.parentElement.querySelector('.sisbajud-label-valor');
                if (valueElement) {
                    return valueElement.textContent.trim();
                }
            }
            return null;
        }

        // Extrair dados básicos
        const numeroProcesso = getValueByLabel('Número do Processo:');
        const numeroProtocolo = getValueByLabel('Número do Protocolo:');
        const repeticaoProgramada = getValueByLabel('Repetição programada?');
        const limiteRepeticao = getValueByLabel('Data limite da repetição:');

        // Extrair valor do bloqueio (pega do primeiro executado)
        const valorBloqueio = getCleanText('td[data-label="valorBloquear:"]');

        // Extrair partes (executados)
        const executados = [];
        const rowsExecutados = document.querySelectorAll('tr.element-row');

        rowsExecutados.forEach(row => {
            const nomeElement = row.querySelector('.col-reu-dados-nome-pessoa');
            const documentoElement = row.querySelector('.col-reu-dados a');

            if (nomeElement && documentoElement) {
                const nome = nomeElement.textContent.trim();
                const documento = documentoElement.textContent.trim();
                executados.push(`${nome} - [${documento}]`);
            }
        });

        // Montar o resultado formatado com espaçamento e destaques
        let resultado = "Dados da Teimosinha protocolada:\n\n";

        resultado += `Número do processo: **${numeroProcesso || 'Não encontrado'}**\n\n`;
        resultado += `Número do protocolo: **${numeroProtocolo || 'Não encontrado'}**\n\n`;
        resultado += `Repetição programada? **${repeticaoProgramada || 'Não encontrado'}**\n\n`;
        resultado += `Limite da repetição: **${limiteRepeticao || 'Não encontrado'}**\n\n`;
        resultado += `Valor do bloqueio: **${valorBloqueio ? valorBloqueio.split('\n')[0] : 'Não encontrado'}**\n\n`;

        resultado += "Partes alvo do bloqueio:\n\n";
        if (executados.length > 0) {
            executados.forEach(executado => {
                resultado += `**${executado}**\n\n`;
            });
        } else {
            resultado += "**Nenhum executado encontrado**\n\n";
        }

        resultado += "-Por padrão é consultado CNPJ raiz.\n\n";
        resultado += "-Eventuais partes faltantes se referem a CPF ou CNPJ sem relacionamento bancário.";

        // Versão sem markdown para clipboard (texto simples)
        let resultadoSimples = "Dados da Teimosinha protocolada:\n\n";

        resultadoSimples += `Número do processo: ${numeroProcesso || 'Não encontrado'}\n\n`;
        resultadoSimples += `Número do protocolo: ${numeroProtocolo || 'Não encontrado'}\n\n`;
        resultadoSimples += `Repetição programada? ${repeticaoProgramada || 'Não encontrado'}\n\n`;
        resultadoSimples += `Limite da repetição: ${limiteRepeticao || 'Não encontrado'}\n\n`;
        resultadoSimples += `Valor do bloqueio: ${valorBloqueio ? valorBloqueio.split('\n')[0] : 'Não encontrado'}\n\n`;

        resultadoSimples += "Partes alvo do bloqueio:\n\n";
        if (executados.length > 0) {
            executados.forEach(executado => {
                resultadoSimples += `${executado}\n\n`;
            });
        } else {
            resultadoSimples += "Nenhum executado encontrado\n\n";
        }

        resultadoSimples += "-Por padrão é consultado CNPJ raiz.\n\n";
        resultadoSimples += "-Eventuais partes faltantes se referem a CPF ou CNPJ sem relacionamento bancário.";

        // Tentar copiar como HTML primeiro (com formatação), depois fallback para texto simples
        async function copyToClipboard() {
            try {
                // Converte quebras de linha e markdown para HTML
                const htmlContent = resultado
                    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                    .replace(/\n/g, '<br>');

                const item = new ClipboardItem({
                    'text/html': new Blob([htmlContent], { type: 'text/html' }),
                    'text/plain': new Blob([resultadoSimples], { type: 'text/plain' })
                });

                await navigator.clipboard.write([item]);
                console.log("✅ Dados extraídos e copiados para área de transferência COM FORMATAÇÃO!");

            } catch (htmlError) {
                // Fallback para texto simples
                try {
                    await navigator.clipboard.writeText(resultadoSimples);
                    console.log("✅ Dados extraídos e copiados para área de transferência (texto simples)");
                } catch (textError) {
                    throw textError;
                }
            }
        }

        // Copiar para área de transferência
        copyToClipboard().then(() => {
            console.log("\n" + "=".repeat(60));
            console.log("DADOS EXTRAÍDOS E FORMATADOS:");
            console.log("=".repeat(60));
            console.log(resultado.replace(/\*\*(.*?)\*\*/g, '$1')); // Remove markdown para exibição no console
            console.log("=".repeat(60));

            // Mostrar resumo
            console.log(`\n📊 RESUMO DA EXTRAÇÃO:`);
            console.log(`• Processo: ${numeroProcesso || 'Não encontrado'}`);
            console.log(`• Protocolo: ${numeroProtocolo || 'Não encontrado'}`);
            console.log(`• Repetição: ${repeticaoProgramada || 'Não encontrado'}`);
            console.log(`• Limite: ${limiteRepeticao || 'Não encontrado'}`);
            console.log(`• Valor: ${valorBloqueio ? valorBloqueio.split('\n')[0] : 'Não encontrado'}`);
            console.log(`• Executados encontrados: ${executados.length}`);
            console.log(`\n💡 DICA: Cole em um editor que suporte formatação (Word, Google Docs, etc.) para ver os destaques em negrito!`);

        }).catch(err => {
            console.error('❌ Erro ao copiar para área de transferência:', err);
            console.log("\n📋 DADOS EXTRAÍDOS (cole manualmente):");
            console.log("=".repeat(60));
            console.log(resultadoSimples);
            console.log("=".repeat(60));
        });

    } catch (error) {
        console.error('❌ Erro na extração:', error);
        console.log('\n🔍 Diagnóstico:');

        // Verificações de diagnóstico
        const labels = document.querySelectorAll('.sisbajud-label');
        const valores = document.querySelectorAll('.sisbajud-label-valor');
        const executadosRows = document.querySelectorAll('tr.element-row');

        console.log(`• Labels encontrados: ${labels.length}`);
        console.log(`• Valores encontrados: ${valores.length}`);
        console.log(`• Linhas de executados: ${executadosRows.length}`);

        if (labels.length > 0) {
            console.log('\n📝 Labels disponíveis:');
            labels.forEach((label, index) => {
                console.log(`  ${index + 1}. "${label.textContent.trim()}"`);
            });
        }

        if (executadosRows.length > 0) {
            console.log('\n👥 Executados encontrados:');
            executadosRows.forEach((row, index) => {
                const nome = row.querySelector('.col-reu-dados-nome-pessoa');
                const doc = row.querySelector('.col-reu-dados a');
                console.log(`  ${index + 1}. ${nome ? nome.textContent.trim() : 'Nome não encontrado'} - ${doc ? doc.textContent.trim() : 'Documento não encontrado'}`);
            });
        }
    }
})();
