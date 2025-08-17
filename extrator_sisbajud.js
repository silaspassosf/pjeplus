
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

        // Montar o resultado formatado
        let resultado = "Dados da Teimosinha protocolada:\n";
        resultado += `Número do processo: ${numeroProcesso || 'Não encontrado'}\n`;
        resultado += `Número do protocolo: ${numeroProtocolo || 'Não encontrado'}\n`;
        resultado += `Repetição programada? ${repeticaoProgramada || 'Não encontrado'}\n`;
        resultado += `Limite da repetição: ${limiteRepeticao || 'Não encontrado'}\n`;
        resultado += `Valor do bloqueio: ${valorBloqueio ? valorBloqueio.split('\n')[0] : 'Não encontrado'}\n\n`;

        resultado += "Partes alvo do bloqueio:\n";
        if (executados.length > 0) {
            executados.forEach(executado => {
                resultado += `${executado}\n`;
            });
        } else {
            resultado += "Nenhum executado encontrado\n";
        }

        resultado += "\n-Por padrão é consultado CNPJ raiz.\n";
        resultado += "-Eventuais partes faltantes se referem a CPF ou CNPJ sem relacionamento bancário.";

        // Copiar para área de transferência
        navigator.clipboard.writeText(resultado).then(() => {
            console.log("✅ Dados extraídos e copiados para área de transferência!");
            console.log("\n" + "=".repeat(50));
            console.log("DADOS EXTRAÍDOS:");
            console.log("=".repeat(50));
            console.log(resultado);
            console.log("=".repeat(50));

            // Mostrar resumo
            console.log(`\n📊 RESUMO DA EXTRAÇÃO:`);
            console.log(`• Processo: ${numeroProcesso || 'Não encontrado'}`);
            console.log(`• Protocolo: ${numeroProtocolo || 'Não encontrado'}`);
            console.log(`• Repetição: ${repeticaoProgramada || 'Não encontrado'}`);
            console.log(`• Limite: ${limiteRepeticao || 'Não encontrado'}`);
            console.log(`• Valor: ${valorBloqueio ? valorBloqueio.split('\n')[0] : 'Não encontrado'}`);
            console.log(`• Executados encontrados: ${executados.length}`);

        }).catch(err => {
            console.error('❌ Erro ao copiar para área de transferência:', err);
            console.log("\n📋 DADOS EXTRAÍDOS (cole manualmente):");
            console.log("=".repeat(50));
            console.log(resultado);
            console.log("=".repeat(50));
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
