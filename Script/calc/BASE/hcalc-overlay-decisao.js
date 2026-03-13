(function () {
    'use strict';

    function createController(deps) {
        const {
            $,
            dbg,
            logError,
            parseMoney,
            formatMoney,
            normalizeMoneyInput,
            bold,
            u,
            isNomeRogerio,
            responsabilidadesTextoApi
        } = deps;

        function handleGravar() {
            dbg('Clique em Gravar Decisao detectado.');
            let text = `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Vistos.</p>`;
            let houveDepositoDireto = false;
            let houveLibecaoDetalhada = false;
            const passivoTotal = (window.hcalcPartesData?.passivo || []).length;

            const autoria = $('calc-autor').options[$('calc-autor').selectedIndex].text;
            const idPlanilha = $('val-id').value || '[ID DA PLANILHA]';
            const valData = $('val-data').value || '[DATA]';
            const valCredito = $('val-credito').value || '[VALOR]';
            const valFgts = $('val-fgts').value || '[VALOR FGTS]';
            const isPerito = $('calc-autor').value === 'perito';
            const peritoEsclareceu = $('calc-esclarecimentos').checked;
            const pecaPerito = $('calc-peca-perito').value || '[ID PEÇA]';
            const indice = $('calc-indice').value;
            const isFgtsSep = $('calc-fgts').checked;
            const ignorarInss = $('ignorar-inss').checked;

            const xxx = () => u(bold('XXX'));

            const appendBaseAteAntesPericiais = ({
                idCalculo,
                usarPlaceholder = false,
                reclamadaLabel = '',
                dadosOverride = null,
                textoResponsabilidade = ''
            }) => {
                let introTxt = '';
                const vCredito = usarPlaceholder ? 'R$XXX' :
                    (dadosOverride ? `R$${dadosOverride.verbas}` : `R$${valCredito}`);
                const vFgts = usarPlaceholder ? 'R$XXX' :
                    (dadosOverride ? `R$${dadosOverride.fgts || '0,00'}` : `R$${valFgts}`);
                const vData = usarPlaceholder ? 'XXX' :
                    (dadosOverride ? dadosOverride.dataAtualizacao : valData);
                const fgtsSeparado = dadosOverride
                    ? (dadosOverride.fgts && dadosOverride.fgts !== '0,00')
                    : isFgtsSep;
                const fgtsDepositadoFlag = false; // Depositado não será mais usado

                if (isPerito && peritoEsclareceu) {
                    introTxt += `As impugnações apresentadas já foram objeto de esclarecimentos pelo Sr. Perito sob o #${bold(pecaPerito)}, nada havendo a ser reparado no laudo. Portanto, HOMOLOGO os cálculos do expert (#${bold(idCalculo)}), `;
                } else {
                    introTxt += `Tendo em vista a concordância das partes, HOMOLOGO os cálculos apresentados pelo(a) ${u(autoria)} (#${bold(idCalculo)}), `;
                }

                if (fgtsSeparado) {
                    introTxt += `fixando o crédito do autor em ${bold(vCredito)} relativo ao principal, e ${bold(vFgts)} relativo ao ${bold('FGTS')} a ser recolhido em conta vinculada, para ${bold(vData)}. `;
                    introTxt += `Atualização na forma da Lei 14.905/2024 e da decisão proferida pela SDI-1 do C. TST, ou seja, a correção monetária será feita pelo IPCA-E até a distribuição da ação; taxa Selic do ajuizamento até 29/08/2024, e, a partir de 30/08/2024, atualização pelo IPCA, com juros de mora correspondentes à diferença entre a SELIC e o IPCA, conforme o artigo 406 do Código Civil.`;
                } else {
                    introTxt += `fixando o crédito em ${bold(vCredito)}, referente ao valor principal, atualizado para ${bold(vData)}. `;
                    if (indice === 'adc58') {
                        introTxt += `Atualização: pelo IPCA-E na fase pré-judicial e, a partir do ajuizamento da ação, pela taxa SELIC (art. 406 do Código Civil), conforme decisão do E. Supremo Tribunal Federal nas ADCs 58 e 59 e ADI 5867, de 18/12/2020.`;
                    } else {
                        const dtIngresso = usarPlaceholder ? 'XXX' : ($('data-ingresso').value || '[DATA INGRESSO]');
                        introTxt += `Atualização: pela TR/IPCA-E, conforme sentença transitado em julgado. Juros legais a partir de ${bold(dtIngresso)}.`;
                    }
                }

                if (reclamadaLabel) {
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;"><strong>${reclamadaLabel}</strong></p>`;
                }
                text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">${introTxt}</p>`;

                if (textoResponsabilidade) {
                    text += textoResponsabilidade;
                }

                if (fgtsSeparado) {
                    // Apenas adicionar liberação automática se o usuário marcar a checkbox de dispensa imotivada
                    if ($('calc-fgts-alvara') && $('calc-fgts-alvara').checked) {
                        text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Após o recolhimento do FGTS pela reclamada, deverá a Secretaria providenciar a liberação ao autor, por meio de expedição de alvará, ante o término do contrato de forma imotivada.</p>`;
                    }
                }

                if (!usarPlaceholder && $('calc-origem').value === 'pjecalc' && !$('calc-pjc').checked) {
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Considerando a ausência do arquivo de origem, <u>deverá a parte apresentar novamente a planilha ora homologada, acompanhada obrigatoriamente do respectivo arquivo ${bold('.PJC')} no prazo de 05 dias</u>.</p>`;
                }

                if (usarPlaceholder) {
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Desde já, ficam autorizados os descontos previdenciários (cota do reclamante) ora fixados em ${xxx()}, para ${xxx()}, devendo, para as retenções, serem observados os termos da Súmula 368, C. TST e da Instrução Normativa RFB nº 1.500, de 29/10/2014.</p>`;
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Os valores relativos às contribuições previdenciárias devidas em decorrência de decisões proferidas pela Justiça do Trabalho a partir de 1º de outubro de 2023, inclusive acordos homologados, devem ser recolhidos pelo(a) reclamado(a) por meio da DCTF-Web, depois de serem informados os dados da reclamatória trabalhista no e-Social. Atente-se que os registros no e-Social serão feitos por meio dos eventos: \"S-2500 - Processos Trabalhistas\" e \"S-2501 - Informações de Tributos Decorrentes de Processo Trabalhista\".</p>`;
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Nos casos em que os recolhimentos forem efetuados diretamente pela Justiça do Trabalho, o reclamado deverá enviar através do e-Social somente o evento \"S-2500 – Processos Trabalhistas\".</p>`;
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">A reclamada, ainda, deverá pagar o valor de sua cota-parte no INSS, a saber, ${xxx()}, para ${xxx()}.</p>`;
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Para as deduções fiscais de Imposto de Renda, fixadas em ${xxx()} para ${xxx()}, observem-se a Súmula 368 do TST e IN RFB 1500/2014.</p>`;
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Honorários advocatícios sucumbenciais pela reclamada, no importe de ${xxx()}, para ${xxx()}.</p>`;
                    if ($('chk-hon-reu').checked) {
                        text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Não foram arbitrados honorários ao advogado do réu.</p>`;
                    } else {
                        const tipoHonReuPlaceholder = document.querySelector('input[name="rad-hon-reu-tipo"]:checked')?.value || 'percentual';
                        const temSuspensivaPlaceholder = $('chk-hon-reu-suspensiva').checked;
                        if (tipoHonReuPlaceholder === 'percentual') {
                            const percentualPlaceholder = $('val-hon-reu-perc').value || 'XXX%';
                            if (temSuspensivaPlaceholder) {
                                text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Honorários advocatícios pela reclamante sob condição suspensiva, na ordem de ${bold(percentualPlaceholder)}, diante da gratuidade deferida.</p>`;
                            } else {
                                text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Honorários advocatícios sucumbenciais em favor da reclamada na ordem de ${bold(percentualPlaceholder)}.</p>`;
                            }
                        } else if (temSuspensivaPlaceholder) {
                            text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Honorários advocatícios pela reclamante sob condição suspensiva, no importe de ${xxx()}, para ${xxx()}, diante da gratuidade deferida.</p>`;
                        } else {
                            text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Honorários advocatícios sucumbenciais em favor da reclamada na ordem de ${xxx()}.</p>`;
                        }
                    }
                    return;
                }

                if (ignorarInss) {
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Pela natureza do crédito, não há contribuições previdenciárias devidas.</p>`;
                } else {
                    const valInssRecStr = dadosOverride && dadosOverride.inssAutor ? dadosOverride.inssAutor : ($('val-inss-rec').value || '0');
                    const valInssTotalStr = dadosOverride && dadosOverride.inssTotal ? dadosOverride.inssTotal : ($('val-inss-total').value || '0');
                    const valInssRec = parseMoney(valInssRecStr);
                    const valInssTotal = parseMoney(valInssTotalStr);
                    let valInssReclamadaStr = valInssTotalStr;
                    if ($('calc-origem').value === 'pjecalc') {
                        const recResult = valInssTotal - valInssRec;
                        valInssReclamadaStr = formatMoney(recResult);
                    }
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">A reclamada deverá pagar o valor de sua cota-parte no INSS, a saber, ${bold(valInssReclamadaStr)}, para ${bold(valData)}.</p>`;
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Desde já, ficam autorizados os descontos previdenciários (cota do reclamante) ora fixados em ${bold('R$' + valInssRecStr)}, para ${bold(valData)}, devendo, para as retenções, serem observados os termos da Súmula 368, C. TST e da Instrução Normativa RFB nº 1.500, de 29/10/2014.</p>`;
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Os valores relativos às contribuições previdenciárias devidas em decorrência de decisões proferidas pela Justiça do Trabalho a partir de 1º de outubro de 2023, inclusive acordos homologados, devem ser recolhidos pelo(a) reclamado(a) por meio da DCTF-Web, depois de serem informados os dados da reclamatória trabalhista no e-Social. Atente-se que os registros no e-Social serão feitos por meio dos eventos: \"S-2500 - Processos Trabalhistas\" e \"S-2501 - Informações de Tributos Decorrentes de Processo Trabalhista\".</p>`;
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Nos casos em que os recolhimentos forem efetuados diretamente pela Justiça do Trabalho, o reclamado deverá enviar através do e-Social somente o evento \"S-2500 – Processos Trabalhistas\".</p>`;
                }

                const irpfIsentoFlag = dadosOverride !== null && dadosOverride.irpfIsento !== undefined ? dadosOverride.irpfIsento : ($('irpf-tipo').value === 'isento');
                if (irpfIsentoFlag) {
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Não há deduções fiscais cabíveis.</p>`;
                } else {
                    const vBase = dadosOverride ? '[VALOR BASE IRPF NA PLANILHA]' : ($('val-irpf-base').value || '[VALOR]');
                    if ($('calc-origem').value === 'pjecalc') {
                        const vMes = $('val-irpf-meses').value || '[X]';
                        text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Ficam autorizados os descontos fiscais, calculados sobre as verbas tributáveis (${bold('R$' + vBase)}), pelo período de ${bold(vMes + ' meses')}.</p>`;
                    } else {
                        text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Para as deduções fiscais de Imposto de Renda, fixadas em ${bold('R$' + vBase)} para ${bold(valData)}, observem-se a Súmula 368 do TST e IN RFB 1500/2014.</p>`;
                    }
                }

                if (!$('ignorar-hon-autor').checked) {
                    const honAVal = dadosOverride && dadosOverride.honAutor ? dadosOverride.honAutor : ($('val-hon-autor').value || '[VALOR]');
                    const vHonA = normalizeMoneyInput(honAVal);
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Honorários advocatícios sucumbenciais pela reclamada, no importe de ${bold(vHonA)}, para ${bold(valData)}.</p>`;
                }

                if ($('chk-hon-reu').checked) {
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Não foram arbitrados honorários ao advogado do réu.</p>`;
                } else {
                    const tipoHonReu = document.querySelector('input[name="rad-hon-reu-tipo"]:checked').value;
                    const temSuspensiva = $('chk-hon-reu-suspensiva').checked;

                    if (tipoHonReu === 'percentual') {
                        const p = $('val-hon-reu-perc').value;
                        if (temSuspensiva) {
                            text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Honorários advocatícios pela reclamante sob condição suspensiva, na ordem de ${bold(p)}, diante da gratuidade deferida.</p>`;
                        } else {
                            text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Honorários advocatícios sucumbenciais em favor da reclamada na ordem de ${bold(p)}, a serem descontados do crédito do autor.</p>`;
                        }
                    } else {
                        const honRVal = dadosOverride && dadosOverride.honReu ? dadosOverride.honReu : ($('val-hon-reu').value || '[VALOR]');
                        const vHonR = normalizeMoneyInput(honRVal);
                        if (temSuspensiva) {
                            text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Honorários advocatícios pela reclamante sob condição suspensiva, no importe de ${bold(vHonR)}, para ${bold(valData)}, diante da gratuidade deferida.</p>`;
                        } else {
                            text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Honorários advocatícios sucumbenciais em favor da reclamada, no importe de ${bold(vHonR)}, para ${bold(valData)}, a serem descontados do crédito do autor.</p>`;
                        }
                    }
                }
            };

            const gerarLiberacaoDetalhada = (contexto) => {
                const { depositoInfo = '' } = contexto;

                text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Passo à liberação de valores conforme planilha #${bold(idPlanilha)}:</p>`;

                let numLiberacao = 1;

                if (depositoInfo) {
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">${numLiberacao}) Libere-se ao reclamante ${depositoInfo}, no valor de ${bold('R$' + valCredito)}, expedindo-se alvará eletrônico.</p>`;
                } else {
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">${numLiberacao}) Libere-se ao reclamante seu crédito, no valor de ${bold('R$' + valCredito)}, expedindo-se alvará eletrônico.</p>`;
                }
                numLiberacao++;

                if (!ignorarInss) {
                    const valInssRec = normalizeMoneyInput($('val-inss-rec').value || '0,00');
                    const valInssTotal = normalizeMoneyInput($('val-inss-total').value || '0,00');
                    const isPjeCalc = $('calc-pjc').checked;
                    let inssEmpregado = valInssRec;
                    let inssPatronal = valInssTotal;

                    if (isPjeCalc && valInssTotal && valInssRec) {
                        const totalNum = parseMoney(valInssTotal);
                        const recNum = parseMoney(valInssRec);
                        const patronalNum = totalNum - recNum;
                        inssPatronal = formatMoney(patronalNum);
                    }

                    const totalInss = valInssTotal;
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">${numLiberacao}) Proceda a Secretaria à transferência de valores ao órgão competente, via Siscondj, sendo: ${bold('R$ ' + inssEmpregado)} referente às contribuições previdenciárias parte empregado e ${bold('R$ ' + inssPatronal)} no que concernem às contribuições patronais (total de ${bold('R$ ' + totalInss)}).</p>`;
                    numLiberacao++;
                }

                const peritoContabilDetectado = (window.hcalcPeritosDetectados || []).find((nome) => isNomeRogerio(nome));
                const valorPeritoContabil = $('val-perito-contabil-valor')?.value || '';
                if (peritoContabilDetectado && valorPeritoContabil) {
                    const vContabil = normalizeMoneyInput(valorPeritoContabil);
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">${numLiberacao}) Libere-se ao perito ${bold(peritoContabilDetectado)} seus honorários, no valor de ${bold('R$' + vContabil)}.</p>`;
                    numLiberacao++;
                }

                const peritosConhecimentoDetectados = window.hcalcPeritosConhecimentoDetectados || [];
                const nomesInputConhecimento = ($('val-perito-nome').value || '')
                    .split(/\||,|;|\n/g)
                    .map((nome) => nome.trim())
                    .filter(Boolean);
                const nomesConhecimento = peritosConhecimentoDetectados.length
                    ? peritosConhecimentoDetectados
                    : nomesInputConhecimento;

                const valorPeritoConh = $('val-perito-valor')?.value || '';
                const tipoPagPericia = $('perito-tipo-pag')?.value || 'reclamada';

                if ($('chk-perito-conh').checked && nomesConhecimento.length > 0 && valorPeritoConh) {
                    nomesConhecimento.forEach((nomePerito) => {
                        if (tipoPagPericia !== 'trt') {
                            const vP = normalizeMoneyInput(valorPeritoConh);
                            text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">${numLiberacao}) Libere-se ao perito ${bold(nomePerito)} seus honorários, no valor de ${bold('R$' + vP)}.</p>`;
                            numLiberacao++;
                        }
                    });
                }

                if (!$('ignorar-hon-autor').checked) {
                    const vHonA = normalizeMoneyInput($('val-hon-autor').value || '[VALOR]');
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">${numLiberacao}) Libere-se ao patrono da parte autora seus honorários, no valor de ${bold('R$' + vHonA)}.</p>`;
                    numLiberacao++;
                }

                return numLiberacao;
            };

            const appendDisposicoesFinais = () => {
                text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;"><strong>Disposições finais:</strong></p>`;

                const peritoContabilDetectado = (window.hcalcPeritosDetectados || []).find((nome) => isNomeRogerio(nome));
                const valorPeritoContabil = $('val-perito-contabil-valor')?.value || '';
                if (peritoContabilDetectado && valorPeritoContabil) {
                    const vContabil = normalizeMoneyInput(valorPeritoContabil);
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Honorários contábeis em favor de ${bold(peritoContabilDetectado)}, ora arbitrados em ${bold(vContabil)}.</p>`;
                }

                const peritosConhecimentoDetectados = window.hcalcPeritosConhecimentoDetectados || [];
                const nomesInputConhecimento = ($('val-perito-nome').value || '')
                    .split(/\||,|;|\n/g)
                    .map((nome) => nome.trim())
                    .filter(Boolean);
                const nomesConhecimento = peritosConhecimentoDetectados.length
                    ? peritosConhecimentoDetectados
                    : nomesInputConhecimento;

                if ($('chk-perito-conh').checked && nomesConhecimento.length > 0) {
                    const vP = $('val-perito-valor').value || '[VALOR/ID]';
                    const dtP = $('val-perito-data').value || $('val-data').value || '[DATA]';
                    const tipoPagPericia = $('perito-tipo-pag').value;

                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Honorários periciais da fase de conhecimento assim estabelecidos:</p>`;

                    nomesConhecimento.forEach((nomePerito) => {
                        if (tipoPagPericia === 'trt') {
                            text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">- Em favor de ${bold(nomePerito)}, pagos pelo TRT, considerando a sucumbência do autor no objeto da perícia (#${bold(vP)}).</p>`;
                        } else {
                            text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">- Em favor de ${bold(nomePerito)}, pagamento de ${bold('R$' + vP)} pela reclamada, para ${bold(dtP)}.</p>`;
                        }
                    });
                }

                if ($('custas-status').value === 'pagas') {
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Custas pagas em razão de recurso.</p>`;
                } else {
                    const valC = $('val-custas').value || '[VALOR]';
                    const origemCustas = $('custas-origem').value;

                    if (valC && valC !== '0,00' && valC !== '0') {
                        if (origemCustas === 'acordao') {
                            const acordaoSel = $('custas-acordao-select').selectedOptions[0];
                            const dataAcordao = acordaoSel?.dataset?.data || '[DATA ACÓRDÃO]';
                            const idAcordao = acordaoSel?.dataset?.id || '';
                            const idTexto = idAcordao ? ` #${bold(idAcordao)}` : '';
                            text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Custas definidas em acórdão${idTexto}, pela reclamada, no valor de ${bold('R$' + valC)} para ${bold(dataAcordao)}.</p>`;
                        } else {
                            const dataCustas = $('custas-data-origem').value || valData;
                            text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Custas de ${bold('R$' + valC)} pela reclamada, para ${bold(dataCustas)}.</p>`;
                        }
                    }
                }

                const passivoCount = (window.hcalcPartesData?.passivo || []).length;
                const temRecJudicial = document.querySelector('#resp-principais-dinamico-container .chk-principal-rec:checked') !== null
                    || (passivoCount === 1 && document.getElementById('resp-rec-judicial-unica')?.checked)
                    || document.querySelector('#resp-subsidiarias-integral-dinamico-container .chk-subs-int-rec:checked') !== null;
                if (temRecJudicial) {
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Considerando o notório estado de insolvência da devedora principal, direciono a execução neste ato.</p>`;
                }

                if ($('chk-deposito').checked) {
                    const passivoDetectado = (window.hcalcPartesData?.passivo || []).map((parte) => parte?.nome).filter(Boolean);
                    const primeiraReclamada = passivoDetectado[0] || '';
                    let tipoRespAtual = 'unica';
                    if ($('resp-subsidiarias')?.checked) tipoRespAtual = 'subsidiarias';
                    if ($('resp-solidarias')?.checked) tipoRespAtual = 'solidarias';
                    if ($('resp-unica-flag')?.value === 'true') tipoRespAtual = 'unica';

                    const depositosValidos = window.hcalcState.depositosRecursais
                        .filter((deposito) => !deposito.removed)
                        .map((deposito) => {
                            const idx = deposito.idx;
                            const tDep = $(`dep-tipo-${idx}`)?.value || 'bb';
                            const dNome = $(`dep-depositante-${idx}`)?.value || '[RECLAMADA]';
                            const dId = $(`dep-id-${idx}`)?.value || '[ID]';
                            let isPrin = $(`dep-principal-${idx}`)?.checked ?? true;
                            const liberacao = document.querySelector(`input[name="rad-dep-lib-${idx}"]:checked`)?.value || 'reclamante';

                            const isDepositoJudicial = tDep !== 'garantia';
                            let criterioLiberacaoDeposito = 'manual';
                            let depositanteResolvida = dNome;

                            if (passivoDetectado.length === 1) {
                                depositanteResolvida = passivoDetectado[0];
                                isPrin = true;
                                criterioLiberacaoDeposito = 'reclamada-unica';
                            } else if (tipoRespAtual === 'subsidiarias' && primeiraReclamada && isPrin) {
                                depositanteResolvida = primeiraReclamada;
                                criterioLiberacaoDeposito = 'subsidiaria-principal';
                            } else if (tipoRespAtual === 'solidarias') {
                                depositanteResolvida = depositanteResolvida || primeiraReclamada || '[RECLAMADA]';
                                isPrin = true;
                                criterioLiberacaoDeposito = 'solidaria';
                            } else if (temRecJudicial && !isPrin) {
                                criterioLiberacaoDeposito = 'rec-judicial-subsidiaria';
                            }

                            const deveLiberarDeposito = isDepositoJudicial && (
                                criterioLiberacaoDeposito === 'reclamada-unica' ||
                                criterioLiberacaoDeposito === 'subsidiaria-principal' ||
                                criterioLiberacaoDeposito === 'solidaria' ||
                                criterioLiberacaoDeposito === 'rec-judicial-subsidiaria' ||
                                (criterioLiberacaoDeposito === 'manual' && isPrin)
                            );

                            const naturezaDevedora = criterioLiberacaoDeposito === 'solidaria'
                                ? 'solidária'
                                : (isPrin ? 'principal' : 'subsidiária');

                            const bancoTxt = tDep === 'bb' ? 'Banco do Brasil' : (tDep === 'sif' ? 'Caixa Econômica Federal (SIF)' : 'seguro garantia regular');

                            return {
                                idx,
                                tDep,
                                depositanteResolvida,
                                dId,
                                isPrin,
                                liberacao,
                                isDepositoJudicial,
                                naturezaDevedora,
                                bancoTxt,
                                deveLiberarDeposito
                            };
                        });

                    if (depositosValidos.length === 0) {
                        text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Há depósito recursal. (Configure os dados)</p>`;
                    } else {
                        const grupos = {};
                        depositosValidos.forEach((dep) => {
                            const chave = `${dep.depositanteResolvida}|${dep.naturezaDevedora}|${dep.bancoTxt}`;
                            if (!grupos[chave]) {
                                grupos[chave] = {
                                    depositante: dep.depositanteResolvida,
                                    natureza: dep.naturezaDevedora,
                                    banco: dep.bancoTxt,
                                    depositos: [],
                                    todosGarantia: true,
                                    todosLiberacaoDireta: true
                                };
                            }
                            grupos[chave].depositos.push(dep);
                            if (dep.isDepositoJudicial) grupos[chave].todosGarantia = false;
                            if (dep.liberacao !== 'reclamante') grupos[chave].todosLiberacaoDireta = false;
                        });

                        const formatarLista = (itens) => {
                            if (!itens || itens.length === 0) { return ''; }
                            if (itens.length === 1) { return itens[0]; }
                            if (itens.length === 2) { return `${itens[0]} e ${itens[1]}`; }
                            return `${itens.slice(0, -1).join(', ')} e ${itens[itens.length - 1]}`;
                        };

                        Object.values(grupos).forEach((grupo) => {
                            const ids = grupo.depositos.map((deposito) => `${bold(deposito.dId)}`);
                            const idsTexto = ids.length > 1 ? `Ids ${formatarLista(ids)}` : `Id ${ids[0]}`;

                            text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">${grupo.depositos.length > 1 ? 'Há depósitos recursais' : 'Há depósito recursal'} da devedora ${grupo.natureza} (${grupo.depositante} ${idsTexto}) via ${grupo.banco}.</p>`;

                            if (grupo.todosGarantia && grupo.natureza === 'principal') {
                                // Seguro garantia: apenas mencionado acima, sem frase adicional sobre liberação
                            } else if (!grupo.todosGarantia) {
                                const depsLiberaveis = grupo.depositos.filter((deposito) => deposito.deveLiberarDeposito && deposito.isDepositoJudicial);

                                if (depsLiberaveis.length > 0) {
                                    const depsDiretos = depsLiberaveis.filter((deposito) => deposito.liberacao === 'reclamante');
                                    const depsDetalhados = depsLiberaveis.filter((deposito) => deposito.liberacao === 'detalhada');

                                    if (depsDiretos.length > 0) {
                                        houveDepositoDireto = true;
                                        const txtPlural = depsDiretos.length > 1 ? 'os depósitos recursais' : 'o depósito recursal';
                                        text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Libere-se ${txtPlural} em favor do reclamante. Após, apure-se o remanescente devido.</p>`;
                                    }

                                    if (depsDetalhados.length > 0) {
                                        const idsDetalhados = depsDetalhados.map((deposito) => `${grupo.depositante} #${bold(deposito.dId)}`);
                                        const listaDeps = formatarLista(idsDetalhados);

                                        houveLibecaoDetalhada = true;
                                        gerarLiberacaoDetalhada({
                                            depositoInfo: `${depsDetalhados.length > 1 ? 'os depósitos recursais' : 'o depósito recursal'} (${listaDeps} via ${grupo.banco})`
                                        });
                                    }
                                } else {
                                    // Não imprimir frase sobre liberação automática — apenas mencionar o depósito (já impresso acima)
                                }
                            }
                        });
                    }
                }

                const isPagamentoAntecipado = $('chk-pag-antecipado').checked;
                if (isPagamentoAntecipado) {
                    const pagamentosValidos = window.hcalcState.pagamentosAntecipados
                        .filter((pagamento) => !pagamento.removed)
                        .map((pagamento) => {
                            const idx = pagamento.idx;
                            return {
                                idx,
                                id: $(`pag-id-${idx}`)?.value || '[ID]',
                                tipoLib: document.querySelector(`input[name="lib-tipo-${idx}"]:checked`)?.value || 'nenhum',
                                remValor: $(`lib-rem-valor-${idx}`)?.value || '',
                                remTitulo: $(`lib-rem-titulo-${idx}`)?.value || '',
                                devValor: $(`lib-dev-valor-${idx}`)?.value || ''
                            };
                        });

                    if (pagamentosValidos.length === 0) {
                        text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Realizado depósito pela reclamada. (Configure os dados)</p>`;
                    } else {
                        pagamentosValidos.forEach((pag) => {
                            text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Realizado depósito pela reclamada, #${bold(pag.id)}.</p>`;

                            houveLibecaoDetalhada = true;
                            const proximoNum = gerarLiberacaoDetalhada({});

                            if (pag.tipoLib === 'devolucao') {
                                text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">${proximoNum}) Devolva-se à reclamada o valor pago a maior, no montante de ${bold('R$ ' + (pag.devValor || '[VALOR]'))}, expedindo-se o competente alvará.</p>`;
                                text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Concede-se 05 dias para manifestação das partes.</p>`;
                                text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Após, tornem conclusos para extinção da execução.</p>`;
                            } else if (pag.tipoLib === 'remanescente') {
                                text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Sem prejuízo, fica a reclamada intimada a pagar o valor remanescente de ${bold('R$ ' + (pag.remValor || '[VALOR]'))} devidos a título de ${bold(pag.remTitulo || '[TÍTULO]')}, em 15 dias, sob pena de execução.</p>`;
                                text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Cientes as partes.</p>`;
                            } else {
                                text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Concede-se 05 dias para manifestações. Silentes, cumpra-se e, após, tornem conclusos para extinção da execução.</p>`;
                            }
                        });
                    }
                }

                if (!isPagamentoAntecipado) {
                    const formatarListaPartes = (nomes) => {
                        if (!nomes || nomes.length === 0) { return ''; }
                        if (nomes.length === 1) { return nomes[0]; }
                        if (nomes.length === 2) { return `${nomes[0]} e ${nomes[1]}`; }
                        return `${nomes.slice(0, -1).join(', ')} e ${nomes[nomes.length - 1]}`;
                    };

                    const elsOpcoes = document.querySelectorAll('.sel-modo-intimacao');
                    const grpDiario = [];
                    const grpMandado = [];
                    const grpEdital = [];
                    const isSubsidiaria = $('resp-subsidiarias')?.checked;
                    const principaisSet = new Set();

                    if (isSubsidiaria) {
                        // Ler do container oficial de principais para não conflitar com intimações
                        document.querySelectorAll('#resp-principais-dinamico-container .principal-item').forEach((item) => {
                            const nome = item.getAttribute('data-nome');
                            if (nome) principaisSet.add(nome);
                        });
                    }

                    if (elsOpcoes.length > 0) {
                        elsOpcoes.forEach((sel) => {
                            const nome = sel.getAttribute('data-nome');
                            const v = sel.value;

                            if (isSubsidiaria && !principaisSet.has(nome)) {
                                return;
                            }

                            if (temRecJudicial && principaisSet.has(nome)) {
                                return;
                            }

                            if (v === 'diario') grpDiario.push(nome);
                            else if (v === 'mandado') grpMandado.push(nome);
                            else if (v === 'edital') grpEdital.push(nome);
                        });
                    } else {
                        const valManual = $('sel-intimacao-manual')?.value || 'diario';
                        const nomeManual = $('int-nome-parte-manual')?.value || '[RECLAMADA]';
                        if (valManual === 'diario') grpDiario.push(nomeManual);
                        else if (valManual === 'mandado') grpMandado.push(nomeManual);
                        else if (valManual === 'edital') grpEdital.push(nomeManual);
                    }

                    if (grpDiario.length > 0) {
                        const alvoComAdv = formatarListaPartes(grpDiario);
                        const verboComAdv = grpDiario.length > 1 ? 'Intimem-se as reclamadas' : 'Intime-se a reclamada';
                        const patronoTxt = grpDiario.length > 1 ? 'seus patronos' : 'seu patrono';
                        const tipoValores = houveDepositoDireto ? 'valores remanescentes' : 'valores acima indicados';
                        text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">${houveDepositoDireto ? 'Após referida atualização, ' : ''}${verboComAdv} ${bold(alvoComAdv)}, na pessoa de ${patronoTxt}, para que pague(m) os ${tipoValores} em 15 dias, na forma do art. 523, caput, do CPC, sob pena de penhora.</p>`;
                    }

                    if (grpMandado.length > 0) {
                        const alvoMand = formatarListaPartes(grpMandado);
                        const verboMand = grpMandado.length > 1 ? 'Intimem-se as reclamadas' : 'Intime-se a reclamada';
                        text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">${verboMand} ${bold(alvoMand)} para pagamento dos valores acima em 48 (quarenta e oito) horas, sob pena de penhora, expedindo-se o competente ${bold('mandado')}.</p>`;
                    }

                    if (grpEdital.length > 0) {
                        const alvoEdit = formatarListaPartes(grpEdital);
                        const verboEdit = grpEdital.length > 1 ? 'Citem-se as reclamadas' : 'Cite-se a reclamada';
                        text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">${verboEdit} ${bold(alvoEdit)}, por ${bold('edital')}, para pagamento dos valores acima em 48 (quarenta e oito) horas, sob pena de penhora.</p>`;
                    }
                }
            };

            // Validação robusta: se o array de períodos tiver dados, força a exibição do bloco, ignorando bugs visuais do DOM
            const usarDuplicacao = (subsidiariasComPeriodo.length > 0 || principaisParciais.length > 0);

            if (usarDuplicacao && passivoTotal > 1) {
                const dadosResp = responsabilidadesTextoApi.gerarTextoResponsabilidades();

                if (dadosResp) {
                    const { textoIntro, todasPrincipais, subsidiariasComPeriodo } = dadosResp;

                    appendBaseAteAntesPericiais({
                        idCalculo: idPlanilha,
                        usarPlaceholder: false,
                        reclamadaLabel: '',
                        textoResponsabilidade: textoIntro
                    });

                    if (todasPrincipais.length > 1) {
                        todasPrincipais.slice(1).forEach((prin) => {
                            const idParaUsar = prin.usarMesmaPlanilha || !prin.idPlanilha ? idPlanilha : prin.idPlanilha;
                            const usarPlaceholder = !prin.usarMesmaPlanilha && !prin.idPlanilha;

                            appendBaseAteAntesPericiais({
                                idCalculo: idParaUsar,
                                usarPlaceholder,
                                reclamadaLabel: `Reclamada ${bold(prin.nome)} (${prin.periodo}):`
                            });
                        });
                    }

                    if (subsidiariasComPeriodo.length > 0) {
                        // Agrupar subsidiárias apenas pelo idPlanilha exato (agora gerado de forma única na API de texto)
                        const grupos = {};
                        subsidiariasComPeriodo.forEach((sub) => {
                            const chave = sub.idPlanilha;
                            if (!grupos[chave]) {
                                grupos[chave] = { idPlanilha: sub.idPlanilha, usarMesmaPlanilha: false, nomes: [], periodo: sub.periodo || '', entradas: [] };
                            }
                            grupos[chave].nomes.push(sub.nome);
                            grupos[chave].entradas.push(sub);
                        });

                        const formatarListaSimples = (itens) => {
                            if (!itens || itens.length === 0) return '';
                            if (itens.length === 1) return itens[0];
                            if (itens.length === 2) return `${itens[0]} e ${itens[1]}`;
                            return `${itens.slice(0, -1).join(', ')} e ${itens[itens.length - 1]}`;
                        };

                        const chaves = Object.keys(grupos);
                        chaves.forEach((chave, gidx) => {
                            const grupo = grupos[chave];
                            const letra = String.fromCharCode(65 + gidx);
                            const periodoLabel = grupo.periodo === 'integral' || !grupo.periodo ? 'Cálculo Específico' : grupo.periodo;
                            const nomesLabel = formatarListaSimples(grupo.nomes.map(n => n));

                            let dadosExtra = null;
                            const idSubPlanilha = (grupo.entradas.find(e => e.idPlanilha && e.idPlanilha.length) || {}).idPlanilha || (grupo.usarMesmaPlanilha ? idPlanilha : '');
                            if (idSubPlanilha && window.hcalcState?.planilhasDisponiveis) {
                                const planilhaEncontrada = window.hcalcState.planilhasDisponiveis.find((planilha) => {
                                    if (planilha.id && planilha.id === idSubPlanilha) return true;
                                    if (planilha.idPlanilha && planilha.idPlanilha === idSubPlanilha) return true;
                                    if (planilha.dados && planilha.dados.idPlanilha && planilha.dados.idPlanilha === idSubPlanilha) return true;
                                    return false;
                                });
                                if (planilhaEncontrada) dadosExtra = planilhaEncontrada.dados || planilhaEncontrada;
                            }

                            const comPlaceholder = !idSubPlanilha;
                            const label = `${letra} - (${bold(nomesLabel)}) - Responsável subsidiária pelo período (${periodoLabel}):`;

                            appendBaseAteAntesPericiais({
                                idCalculo: idSubPlanilha || idPlanilha,
                                usarPlaceholder: comPlaceholder,
                                reclamadaLabel: label,
                                dadosOverride: dadosExtra
                            });
                        });
                    }
                }

                appendDisposicoesFinais();
            } else {
                let introTxt = '';
                if (isPerito && peritoEsclareceu) {
                    introTxt += `As impugnações apresentadas já foram objeto de esclarecimentos pelo Sr. Perito sob o #${bold(pecaPerito)}, nada havendo a ser reparado no laudo. Portanto, HOMOLOGO os cálculos do expert (#${bold(idPlanilha)}), `;
                } else {
                    introTxt += `Tendo em vista a concordância das partes, HOMOLOGO os cálculos apresentados pelo(a) ${u(autoria)} (#${bold(idPlanilha)}), `;
                }

                if (isFgtsSep) {
                    introTxt += `fixando o crédito do autor em ${bold('R$' + valCredito)} relativo ao principal, e ${bold('R$' + valFgts)} relativo ao ${bold('FGTS')} a ser recolhido em conta vinculada, atualizados para ${bold(valData)}. `;
                } else {
                    introTxt += `fixando o crédito em ${bold('R$' + valCredito)}, referente ao valor principal, atualizado para ${bold(valData)}. `;
                }
                if (indice === 'adc58') {
                    if (isFgtsSep) {
                        introTxt += `A atualização foi feita na forma da Lei 14.905/2024 e da decisão da SDI-1 do C. TST (IPCA-E até a distribuição; taxa Selic até 29/08/2024, e IPCA + juros de mora a partir de 30/08/2024).`;
                    } else {
                        introTxt += `A correção monetária foi realizada pelo IPCA-E na fase pré-judicial e, a partir do ajuizamento, pela taxa SELIC (ADC 58).`;
                    }
                } else {
                    const valJuros = $('val-juros').value || '[JUROS]';
                    const dtIngresso = $('data-ingresso').value || '[DATA INGRESSO]';
                    introTxt += `Atualizáveis pela TR/IPCA-E, conforme sentença. Juros legais de ${bold('R$' + valJuros)} a partir de ${bold(dtIngresso)}.`;
                }
                text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">${introTxt}</p>`;

                if (passivoTotal > 1) {
                    let tipoRespDecisao = 'unica';
                    if ($('resp-subsidiarias')?.checked) tipoRespDecisao = 'subsidiarias';
                    if ($('resp-solidarias')?.checked) tipoRespDecisao = 'solidarias';

                    if (tipoRespDecisao === 'solidarias') {
                        text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Declaro que as reclamadas respondem de forma solidária pela presente execução.</p>`;
                    } else if (tipoRespDecisao === 'subsidiarias' && $('resp-sub-integral')?.checked) {
                        const principais = [];
                        const subsidiarias = [];

                        document.querySelectorAll('#resp-principais-dinamico-container .principal-item').forEach((item) => {
                            const nome = item.getAttribute('data-nome');
                            if (nome) principais.push(nome);
                        });

                        document.querySelectorAll('#resp-subsidiarias-integral-dinamico-container .subs-item').forEach((item) => {
                            const nome = item.getAttribute('data-nome');
                            if (nome) subsidiarias.push(nome);
                        });

                        if (principais.length > 0 && subsidiarias.length > 0) {
                            const formatarLista = (nomes) => {
                                if (nomes.length === 1) return bold(nomes[0]);
                                if (nomes.length === 2) return `${bold(nomes[0])} e ${bold(nomes[1])}`;
                                return nomes.slice(0, -1).map((nome) => bold(nome)).join(', ') + ' e ' + bold(nomes[nomes.length - 1]);
                            };

                            const txtPrincipais = formatarLista(principais);
                            const txtSubsidiarias = formatarLista(subsidiarias);
                            const verboPrin = principais.length > 1 ? 'são devedoras principais' : 'é devedora principal';
                            const verboSub = subsidiarias.length > 1 ? 'são subsidiárias' : 'é subsidiária';

                            text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">${txtPrincipais} ${verboPrin}, ${txtSubsidiarias} ${verboSub} pelo período integral do contrato, portanto, os valores neste momento são devidos apenas pelas principais.</p>`;
                        } else {
                            text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">A primeira reclamada é devedora principal, as demais são subsidiárias pelo período integral do contrato, portanto, os valores neste momento são devidos apenas pela primeira.</p>`;
                        }
                    }
                }

                if ($('calc-origem').value === 'pjecalc' && !$('calc-pjc').checked) {
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Considerando a ausência do arquivo de origem, <u>deverá a parte apresentar novamente a planilha ora homologada, acompanhada obrigatoriamente do respectivo arquivo ${bold('.PJC')} no prazo de 05 dias</u>.</p>`;
                }
                if (ignorarInss) {
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Pela natureza do crédito, não há contribuições previdenciárias devidas.</p>`;
                } else {
                    const valInssRecStr = $('val-inss-rec').value || '0';
                    const valInssTotalStr = $('val-inss-total').value || '0';
                    const valInssRec = parseMoney(valInssRecStr);
                    const valInssTotal = parseMoney(valInssTotalStr);
                    let valInssReclamadaStr = valInssTotalStr;
                    if ($('calc-origem').value === 'pjecalc') {
                        const recResult = valInssTotal - valInssRec;
                        valInssReclamadaStr = formatMoney(recResult);
                    }
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">A reclamada deverá pagar o valor de sua cota-parte no INSS, a saber, ${bold(valInssReclamadaStr)}, para ${bold(valData)}.</p>`;
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Desde já, ficam autorizados os descontos previdenciários (cota do reclamante) ora fixados em ${bold('R$' + valInssRecStr)}, para ${bold(valData)}, devendo, para as retenções, serem observados os termos da Súmula 368, C. TST e da Instrução Normativa RFB nº 1.500, de 29/10/2014.</p>`;
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Os valores relativos às contribuições previdenciárias devidas em decorrência de decisões proferidas pela Justiça do Trabalho a partir de 1º de outubro de 2023, inclusive acordos homologados, devem ser recolhidos pelo(a) reclamado(a) por meio da DCTF-Web, depois de serem informados os dados da reclamatória trabalhista no e-Social. Atente-se que os registros no e-Social serão feitos por meio dos eventos: \"S-2500 - Processos Trabalhistas\" e \"S-2501 - Informações de Tributos Decorrentes de Processo Trabalhista\".</p>`;
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Nos casos em que os recolhimentos forem efetuados diretamente pela Justiça do Trabalho, o reclamado deverá enviar através do e-Social somente o evento \"S-2500 – Processos Trabalhistas\".</p>`;
                }
                if ($('irpf-tipo').value === 'isento') {
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Não há deduções fiscais cabíveis.</p>`;
                } else {
                    const vBase = $('val-irpf-base').value || '[VALOR]';
                    if ($('calc-origem').value === 'pjecalc') {
                        const vMes = $('val-irpf-meses').value || '[X]';
                        text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Ficam autorizados os descontos fiscais, calculados sobre as verbas tributáveis (${bold('R$' + vBase)}), pelo período de ${bold(vMes + ' meses')}.</p>`;
                    } else {
                        text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Para as deduções fiscais de Imposto de Renda, fixadas em ${bold('R$' + vBase)} para ${bold(valData)}, observem-se a Súmula 368 do TST e IN RFB 1500/2014.</p>`;
                    }
                }
                if (!$('ignorar-hon-autor').checked) {
                    const vHonA = normalizeMoneyInput($('val-hon-autor').value || '[VALOR]');
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Honorários advocatícios sucumbenciais pela reclamada, no importe de ${bold(vHonA)}, para ${bold(valData)}.</p>`;
                }
                if ($('chk-hon-reu').checked) {
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Não foram arbitrados honorários ao advogado do réu.</p>`;
                } else {
                    const tipoHonReu = document.querySelector('input[name="rad-hon-reu-tipo"]:checked').value;
                    const temSuspensiva = $('chk-hon-reu-suspensiva').checked;

                    if (tipoHonReu === 'percentual') {
                        const p = $('val-hon-reu-perc').value;
                        if (temSuspensiva) {
                            text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Honorários advocatícios pela reclamante sob condição suspensiva, na ordem de ${bold(p)}, diante da gratuidade deferida.</p>`;
                        } else {
                            text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Honorários advocatícios sucumbenciais em favor da reclamada na ordem de ${bold(p)}, a serem descontados do crédito do autor.</p>`;
                        }
                    } else {
                        const vHonR = normalizeMoneyInput($('val-hon-reu').value || '[VALOR]');
                        if (temSuspensiva) {
                            text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Honorários advocatícios pela reclamante sob condição suspensiva, no importe de ${bold(vHonR)}, para ${bold(valData)}, diante da gratuidade deferida.</p>`;
                        } else {
                            text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Honorários advocatícios sucumbenciais em favor da reclamada, no importe de ${bold(vHonR)}, para ${bold(valData)}, a serem descontados do crédito do autor.</p>`;
                        }
                    }
                }
                appendDisposicoesFinais();
            }

            if (!houveLibecaoDetalhada) {
                text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">${u('Ficam as partes cientes de que qualquer questionamento acerca desta decisão, salvo erro material, será apreciado após a garantia do juízo.')}</p>`;
            }
            const blob = new Blob([text], { type: 'text/html' });
            const clipboardItem = new window.ClipboardItem({ 'text/html': blob });
            navigator.clipboard.write([clipboardItem]).then(() => {
                alert('Decisão copiada com sucesso! Vá ao editor do PJe e cole (Ctrl+V).');
                $('homologacao-overlay').style.display = 'none';
                dbg('Decisao copiada para area de transferencia com sucesso.');
            }).catch((copyError) => {
                alert('Erro ao copiar. O navegador pode ter bloqueado.');
                console.error(copyError);
                logError('Falha ao copiar decisao para clipboard:', copyError);
            });
        }

        return { handleGravar };
    }

    window.hcalcOverlayDecisao = { createController };
})();