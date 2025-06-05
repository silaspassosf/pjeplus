// automacao.js - Fluxos MaisPJe em JavaScript puro para uso com bookmarklet
// Cada função recebe o objeto do botão (config) extraído de botoes_maispje.json
// Vínculos são ignorados

// Helper para querySelector com :contains() (não suportado nativamente em JS)
function findElementByText(selector, text) {
  var elements = document.querySelectorAll(selector);
  for (var i = 0; i < elements.length; i++) {
    if (elements[i].textContent.includes(text)) {
      return elements[i];
    }
  }
  return null;
}

// Helper para querySelectorAll com :contains()
function findElementsByText(selector, text) {
  var elements = document.querySelectorAll(selector);
  var result = [];
  for (var i = 0; i < elements.length; i++) {
    if (elements[i].textContent.includes(text)) {
      result.push(elements[i]);
    }
  }
  return result;
}

// Dispatcher principal
window.executarFluxoMaisPje = function(config) {
  if (!config || !config.grupo || !config.nome) {
    alert('Configuração de botão inválida!');
    return;
  }
  if (config.grupo === 'Despacho') return fluxoDespacho(config);
  if (config.grupo === 'Gigs') return fluxoGigs(config);
  if (config.grupo === 'Anexar') return fluxoAnexar(config);
  alert('Grupo não suportado: ' + config.grupo);
};

// Fluxo completo de Despacho baseado na função Python acao_bt_aaDespacho_selenium
function fluxoDespacho(config) {
  console.log('[DESPACHO] Iniciando ação automatizada:', config.nm_botao || config.nome, '(vínculo:', config.vinculo || 'Nenhum', ')');
  
  try {
    // Aguardar carregamento da página
    setTimeout(function() {
        // 1. Movimentar para tarefa correta (Análise → Conclusão ao Magistrado)
      try {
        var btnAnalise = findElementByText('button', 'Análise') ||
                         findElementByText('button', 'análise') ||
                         document.querySelector('button[title*="Análise"], button[aria-label*="Análise"]');
        if (btnAnalise) {
          btnAnalise.click();
          console.log('[DESPACHO] Movimentado para Análise.');
        }
      } catch(e) {
        console.log('[DESPACHO] Botão Análise não encontrado ou já na tarefa correta.');
      }
      
      setTimeout(function() {
        try {
          var btnConclusao = findElementByText('button', 'Conclusão ao Magistrado') ||
                            findElementByText('button', 'conclusão ao magistrado') ||
                            document.querySelector('button[title*="Conclusão"], button[aria-label*="Conclusão"]');
          if (btnConclusao) {
            btnConclusao.click();
            console.log('[DESPACHO] Movimentado para Conclusão ao Magistrado.');
          }
        } catch(e) {
          console.log('[DESPACHO] Botão Conclusão ao Magistrado não encontrado ou já na tarefa correta.');
        }
        
        // 2. Aguardar e continuar fluxo
        setTimeout(function() { continuarFluxoDespacho(config); }, 1000);
      }, 1000);
    }, 500);
    
  } catch(e) {
    console.error('[DESPACHO] Erro geral:', e);
    alert('Erro no fluxo Despacho: ' + e.message);
  }
}

function continuarFluxoDespacho(config) {
  try {
    // 2. Selecionar magistrado (se necessário)
    if (config.juiz) {
      try {
        var selectJuiz = document.querySelector('mat-select[placeholder="Magistrado"]');
        if (selectJuiz) {
          selectJuiz.click();
          setTimeout(function() {
            var opcoes = document.querySelectorAll('mat-option');
            for (var i = 0; i < opcoes.length; i++) {
              if (opcoes[i].textContent.toLowerCase().includes(config.juiz.toLowerCase())) {
                opcoes[i].click();
                console.log('[DESPACHO] Magistrado selecionado:', config.juiz);
                break;
              }
            }
          }, 500);
        }
      } catch(e) {
        console.log('[DESPACHO] Não foi possível selecionar magistrado.');
      }
    }
      // 3. Selecionar tipo de conclusão (Despacho)
    setTimeout(function() {
      try {
        var btnTipo = findElementByText('button', 'Despacho') ||
                     document.querySelector('button[title*="Despacho"], button[aria-label*="Despacho"]');
        if (btnTipo) {
          btnTipo.click();
          console.log('[DESPACHO] Tipo de conclusão selecionado: Despacho.');
        }
      } catch(e) {
        console.log('[DESPACHO] Botão de tipo Despacho não encontrado ou já selecionado.');
      }
      
      // 4. Preencher descrição
      setTimeout(function() {
        if (config.descricao) {
          try {
            var inputDesc = document.querySelector('input[aria-label="Descrição"]');
            if (inputDesc) {
              inputDesc.value = '';
              inputDesc.value = config.descricao;
              inputDesc.dispatchEvent(new Event('input', { bubbles: true }));
              inputDesc.dispatchEvent(new Event('change', { bubbles: true }));
              console.log('[DESPACHO] Descrição preenchida:', config.descricao);
            }
          } catch(e) {
            console.log('[DESPACHO] Campo de descrição não encontrado.');
          }
        }
        
        // 5. Sigilo
        if (config.sigilo && config.sigilo.toLowerCase() === 'sim') {
          try {
            var chkSigilo = document.querySelector('input[name="sigiloso"]');
            if (chkSigilo && !chkSigilo.checked) {
              chkSigilo.click();
              console.log('[DESPACHO] Sigilo ativado.');
            }
          } catch(e) {
            console.log('[DESPACHO] Campo de sigilo não encontrado.');
          }
        }
        
        // 6. Escolher modelo
        setTimeout(function() {
          if (config.modelo) {
            try {
              var campoModelo = document.querySelector('input[id="inputFiltro"]');
              if (campoModelo) {
                campoModelo.value = '';
                campoModelo.value = config.modelo;
                campoModelo.dispatchEvent(new Event('input', { bubbles: true }));
                
                // Simular Enter
                var enterEvent = new KeyboardEvent('keydown', {
                  key: 'Enter',
                  code: 'Enter',
                  keyCode: 13,
                  which: 13,
                  bubbles: true
                });
                campoModelo.dispatchEvent(enterEvent);
                
                console.log('[DESPACHO] Modelo selecionado:', config.modelo);
                  // Aguardar e clicar no modelo na árvore
                setTimeout(function() {
                  try {
                    var modeloItem = findElementByText('div[role="treeitem"]', config.modelo) ||
                                   findElementByText('div[role="treeitem"] span', config.modelo);
                    if (modeloItem) {
                      modeloItem.click();
                      console.log('[DESPACHO] Modelo inserido no editor.');
                    }
                  } catch(e) {
                    console.log('[DESPACHO] Erro ao inserir modelo na árvore.');
                  }
                }, 1000);
              }
            } catch(e) {
              console.log('[DESPACHO] Não foi possível selecionar/inserir modelo.');
            }
          }
          
          // 7. Salvar documento
          setTimeout(function() {
            try {
              var btnSalvar = document.querySelector('button[aria-label="Salvar"]');
              if (btnSalvar) {
                btnSalvar.click();
                console.log('[DESPACHO] Documento salvo.');
              }
            } catch(e) {
              console.log('[DESPACHO] Botão Salvar não encontrado.');
            }
            
            // 8. Continuar com ações extras (PEC, prazos, movimentos, assinatura)
            setTimeout(function() { finalizarFluxoDespacho(config); }, 1000);
          }, 1000);
        }, 1000);
      }, 1000);
    }, 1000);
    
  } catch(e) {
    console.error('[DESPACHO] Erro na continuação do fluxo:', e);
    alert('Erro na continuação do fluxo Despacho: ' + e.message);
  }
}

function finalizarFluxoDespacho(config) {
  try {
    // 8. Intimação/PEC
    if (config.marcar_pec) {
      try {
        var btnPec = document.querySelector('button[aria-label*="PEC"], input[type="checkbox"][aria-label*="PEC"]');
        if (btnPec) {
          if (btnPec.tagName === 'INPUT' && !btnPec.checked) {
            btnPec.click();
          } else if (btnPec.tagName === 'BUTTON') {
            btnPec.click();
          }
          console.log('[DESPACHO] PEC marcada.');
        }
      } catch(e) {
        console.log('[DESPACHO] Não foi possível marcar PEC.');
      }
    }
    
    // 9. Prazo
    if (config.prazo !== undefined && config.prazo !== null) {
      try {
        var linhas = document.querySelectorAll('table.t-class tr.ng-star-inserted');
        if (linhas.length === 0) {
          console.log('[DESPACHO][PRAZO][ERRO] Nenhuma linha de destinatário encontrada!');
        } else {
          for (var i = 0; i < linhas.length; i++) {
            try {
              var inputPrazo = linhas[i].querySelector('mat-form-field.prazo input[type="text"].mat-input-element');
              if (inputPrazo) {
                inputPrazo.value = '';
                inputPrazo.value = String(config.prazo);
                inputPrazo.dispatchEvent(new Event('input', { bubbles: true }));
                inputPrazo.dispatchEvent(new Event('change', { bubbles: true }));
                console.log('[DESPACHO][PRAZO][OK] Preenchido prazo', config.prazo, 'para destinatário.');
              }
            } catch(e) {
              console.log('[DESPACHO][PRAZO][WARN] Erro ao preencher prazo:', e);
            }
          }
        }
      } catch(e) {
        console.log('[DESPACHO][PRAZO][ERRO]', e);
      }
    }
    
    // 10. Movimento
    setTimeout(function() {
      if (config.movimento) {
        try {
          var guiaMov = document.querySelector('pje-editor-lateral div[aria-posinset="2"]');
          if (guiaMov && guiaMov.getAttribute('aria-selected') === 'false') {
            guiaMov.click();
          }
          
          setTimeout(function() {
            var movimentos = String(config.movimento).split(',');
              // Processar primeiro movimento (checkbox)
            if (movimentos.length > 0) {
              var mov1 = movimentos[0].trim();
              var chk = findElementByText('pje-movimento mat-checkbox', mov1);
              if (chk && !chk.classList.contains('mat-checkbox-checked')) {
                var label = chk.querySelector('label');
                if (label) label.click();
              }
            }
            
            // Processar movimentos complementares
            setTimeout(function() {
              for (var i = 1; i < movimentos.length; i++) {
                var complementos = document.querySelectorAll('pje-complemento');
                if (complementos.length > i - 1) {
                  var combo = complementos[i - 1].querySelector('mat-select');
                  if (combo) {
                    combo.click();
                    
                    setTimeout(function(movIndex) {
                      var opcoes = document.querySelectorAll('mat-option');
                      var movTexto = movimentos[movIndex].toLowerCase().trim();
                      
                      for (var j = 0; j < opcoes.length; j++) {
                        if (opcoes[j].textContent.toLowerCase().includes(movTexto)) {
                          opcoes[j].click();
                          break;
                        }
                      }
                    }.bind(null, i), 300);
                  }
                }
              }
              
              // Gravar movimento
              setTimeout(function() {
                try {
                  var btnGravar = document.querySelector('pje-lancador-de-movimentos button[aria-label*="Gravar"]');
                  if (btnGravar) {
                    btnGravar.click();
                      setTimeout(function() {
                      var btnSim = findElementByText('mat-dialog-container button', 'Sim');
                      if (btnSim) {
                        btnSim.click();
                        console.log('[DESPACHO] Movimento(s) lançado(s).');
                      }
                    }, 500);
                  }
                } catch(e) {
                  console.log('[DESPACHO][MOVIMENTO][ERRO]', e);
                }
              }, 1000);
            }, 500);
          }, 500);
        } catch(e) {
          console.log('[DESPACHO][MOVIMENTO][ERRO]', e);
        }
      }
      
      // 11. Enviar para assinatura
      setTimeout(function() {
        if (config.assinar && config.assinar.toLowerCase() === 'sim') {
          try {
            var btnAssinar = document.querySelector('button[aria-label="Enviar para assinatura"]');
            if (btnAssinar) {
              btnAssinar.click();
              console.log('[DESPACHO] Documento enviado para assinatura.');
            }
          } catch(e) {
            console.log('[DESPACHO] Botão Enviar para assinatura não encontrado.');
          }
        }
        
        // 12. Responsável (se necessário)
        if (config.responsavel) {
          console.log('[DESPACHO] Responsável:', config.responsavel, '(implementar fluxo se necessário)');
        }
        
        console.log('[DESPACHO] Fluxo de despacho automatizado finalizado.');
        alert('Fluxo Despacho executado com sucesso para: ' + (config.nm_botao || config.nome));
      }, 2000);
    }, 1000);
    
  } catch(e) {
    console.error('[DESPACHO] Erro na finalização:', e);
    alert('Erro na finalização do fluxo Despacho: ' + e.message);
  }
}

// Fluxo completo de Gigs/AutoGigs baseado na função Python acao_bt_aaAutogigs_selenium
function fluxoGigs(config) {
  console.log('[AUTOGIGS] Iniciando:', config.nm_botao || config.nome, '- Tipo:', config.tipo);
  
  try {
    var nmBotao = config.nm_botao || config.nome || '';
    var tipo = config.tipo || '';
    var concluir = nmBotao.includes('[concluir]');
    
    // Verificar se GIGS está aberto
    var gigsFechado = verificarGigsFechado();
    if (gigsFechado) {
      abrirGigs();
    }
    
    // Aguardar carregamento
    setTimeout(function() {
      // Executar ação baseada no tipo
      if (tipo === 'chip') {
        executarChip(config, concluir);
      } else if (tipo === 'comentario') {
        executarComentario(config, concluir, gigsFechado);
      } else if (tipo === 'lembrete') {
        executarLembrete(config, concluir);
      } else {
        // prazo ou preparo (default)
        executarGigsAtividade(config, concluir, gigsFechado);
      }
    }, 1000);
    
  } catch(e) {
    console.error('[AUTOGIGS] Erro geral:', e);
    alert('Erro no fluxo AutoGigs: ' + e.message);
  }
}

function verificarGigsFechado() {
  try {
    document.querySelector('button[aria-label="Mostrar o GIGS"]');
    return true;
  } catch(e) {
    return false;
  }
}

function abrirGigs() {
  try {
    var btnMostrar = document.querySelector('button[aria-label="Mostrar o GIGS"]');
    if (btnMostrar) {
      btnMostrar.click();
      console.log("[AUTOGIGS] GIGS aberto");
    }
  } catch(e) {
    console.log("[AUTOGIGS][ERRO] Falha ao abrir GIGS:", e);
  }
}

function fecharGigs() {
  try {
    var btnEsconder = document.querySelector('button[aria-label="Esconder o GIGS"]');
    if (btnEsconder) {
      btnEsconder.click();
      console.log("[AUTOGIGS] GIGS fechado");
    }
  } catch(e) {
    // Ignora erro se não conseguir fechar
  }
}

function executarChip(config, concluir) {
  try {
    var tipoAtividade = config.tipo_atividade || '';
    var salvar = (config.salvar || '').toLowerCase() === 'sim';
    
    if (concluir) {
      removerChips(tipoAtividade);
    } else {
      adicionarChips(tipoAtividade, salvar);
    }
  } catch(e) {
    console.error("[AUTOGIGS][CHIP][ERRO]", e);
    alert('Erro no fluxo de Chips: ' + e.message);
  }
}

function removerChips(chipsParaRemover) {
  try {
    // Expandir lista de chips se necessário
    try {
      var btnExpandir = document.querySelector('pje-lista-etiquetas button[aria-label="Expandir Chips"]');
      if (btnExpandir) btnExpandir.click();
    } catch(e) {}
    
    // Buscar chips para remover
    var chips = chipsParaRemover.split(',');
    chips.forEach(function(chip) {
      chip = chip.trim();
      try {
        // Buscar botão de remoção do chip específico
        var btnRemover = document.querySelector('pje-lista-etiquetas mat-chip button[aria-label*="' + chip + '"]');
        if (btnRemover) {
          btnRemover.click();
            // Confirmar remoção se aparecer diálogo
          setTimeout(function() {
            try {
              var btnConfirmar = findElementByText('mat-dialog-container button', 'Sim') ||
                               findElementByText('mat-dialog-container button', 'Confirmar');
              if (btnConfirmar) btnConfirmar.click();
              console.log("[AUTOGIGS][CHIP] Chip removido:", chip);
            } catch(e) {}
          }, 500);
        }
      } catch(e) {
        console.log("[AUTOGIGS][CHIP][AVISO] Chip não encontrado para remoção:", chip);
      }
    });
    
    alert('Chips removidos com sucesso!');
  } catch(e) {
    console.error("[AUTOGIGS][CHIP][ERRO] Falha ao remover chips:", e);
    alert('Erro ao remover chips: ' + e.message);
  }
}

function adicionarChips(chipsParaAdicionar, salvar) {
  try {
    // Clicar no botão de adicionar chip
    var btnChip = document.querySelector('button[aria-label="Incluir Chip Amarelo"]');
    if (btnChip) {
      btnChip.click();
      
      setTimeout(function() {
        // Preencher nome do chip
        var campoChip = document.querySelector('input[placeholder*="chip"], input[formcontrolname="nome"]');
        if (campoChip) {
          campoChip.value = chipsParaAdicionar;
          campoChip.dispatchEvent(new Event('input', { bubbles: true }));
          
          if (salvar) {
            setTimeout(function() {
              var btnSalvar = document.querySelector('button:contains("Salvar"), button[aria-label*="Salvar"]');
              if (btnSalvar) {
                btnSalvar.click();
                console.log("[AUTOGIGS][CHIP] Chip adicionado:", chipsParaAdicionar);
                alert('Chip adicionado com sucesso: ' + chipsParaAdicionar);
              }
            }, 500);
          }
        }
      }, 1000);
    }
  } catch(e) {
    console.error("[AUTOGIGS][CHIP][ERRO] Falha ao adicionar chips:", e);
    alert('Erro ao adicionar chips: ' + e.message);
  }
}

function executarComentario(config, concluir, gigsFechado) {
  try {
    var observacao = config.observacao || '';
    var prazo = config.prazo || ''; // visibilidade para comentários
    
    if (concluir) {
      // Lógica para concluir comentários (se necessário)
      console.log("[AUTOGIGS][COMENTARIO] Concluir comentários não implementado");
    } else {
      // Adicionar novo comentário
      var btnComentario = document.querySelector('button[aria-label*="comentário"], button:contains("Comentário")');
      if (btnComentario) {
        btnComentario.click();
        
        setTimeout(function() {
          var campoTexto = document.querySelector('textarea[formcontrolname="texto"], textarea[placeholder*="comentário"]');
          if (campoTexto && observacao) {
            campoTexto.value = observacao;
            campoTexto.dispatchEvent(new Event('input', { bubbles: true }));
          }
            // Configurar visibilidade se especificada
          if (prazo) {
            var selectVisibilidade = document.querySelector('mat-select[formcontrolname="visibilidade"]');
            if (selectVisibilidade) {
              selectVisibilidade.click();
              setTimeout(function() {
                var opcaoVis = findElementByText('mat-option', prazo);
                if (opcaoVis) opcaoVis.click();
              }, 300);
            }
          }
            // Salvar comentário
          setTimeout(function() {
            var btnSalvar = findElementByText('button', 'Salvar');
            if (btnSalvar) {
              btnSalvar.click();
              console.log("[AUTOGIGS][COMENTARIO] Comentário adicionado");
              
              if (gigsFechado) {
                setTimeout(fecharGigs, 1000);
              }
              alert('Comentário adicionado com sucesso!');
            }
          }, 500);
        }, 1000);
      }
    }
  } catch(e) {
    console.error("[AUTOGIGS][COMENTARIO][ERRO]", e);
    alert('Erro no fluxo de Comentários: ' + e.message);
  }
}

function executarLembrete(config, concluir) {
  try {
    var titulo = config.tipo_atividade || '';
    var observacao = config.observacao || '';
    var prazo = config.prazo || '';
    
    if (concluir) {
      // Lógica para concluir lembretes (se necessário)
      console.log("[AUTOGIGS][LEMBRETE] Concluir lembretes não implementado");
    } else {
      // Adicionar novo lembrete
      var btnLembrete = document.querySelector('button[aria-label*="lembrete"], button:contains("Lembrete")');
      if (btnLembrete) {
        btnLembrete.click();
        
        setTimeout(function() {
          // Preencher título
          if (titulo) {
            var campoTitulo = document.querySelector('input[formcontrolname="titulo"]');
            if (campoTitulo) {
              campoTitulo.value = titulo;
              campoTitulo.dispatchEvent(new Event('input', { bubbles: true }));
            }
          }
          
          // Preencher observação
          if (observacao) {
            var campoObs = document.querySelector('textarea[formcontrolname="observacao"]');
            if (campoObs) {
              campoObs.value = observacao;
              campoObs.dispatchEvent(new Event('input', { bubbles: true }));
            }
          }
          
          // Preencher prazo
          if (prazo) {
            var campoPrazo = document.querySelector('input[formcontrolname="prazo"]');
            if (campoPrazo) {
              campoPrazo.value = prazo;
              campoPrazo.dispatchEvent(new Event('input', { bubbles: true }));
            }
          }
            // Salvar lembrete
          setTimeout(function() {
            var btnSalvar = findElementByText('button', 'Salvar');
            if (btnSalvar) {
              btnSalvar.click();
              console.log("[AUTOGIGS][LEMBRETE] Lembrete adicionado");
              alert('Lembrete adicionado com sucesso!');
            }
          }, 500);
        }, 1000);
      }
    }
  } catch(e) {
    console.error("[AUTOGIGS][LEMBRETE][ERRO]", e);
    alert('Erro no fluxo de Lembretes: ' + e.message);
  }
}

function executarGigsAtividade(config, concluir, gigsFechado) {
  try {
    var responsavelProcesso = config.responsavel_processo || '';
    
    // Definir responsável do processo se especificado
    if (responsavelProcesso) {
      definirResponsavelProcesso(responsavelProcesso);
    }
    
    if (concluir) {
      concluirAtividadesGigs(config, gigsFechado);
    } else {
      adicionarAtividadeGigs(config, gigsFechado);
    }
  } catch(e) {
    console.error("[AUTOGIGS][GIGS][ERRO]", e);
    alert('Erro no fluxo de Atividades GIGS: ' + e.message);
  }
}

function definirResponsavelProcesso(responsavel) {
  try {
    var campoResp = document.querySelector('input[formcontrolname="responsavelProcesso"]');
    if (campoResp) {
      campoResp.value = responsavel;
      campoResp.dispatchEvent(new Event('input', { bubbles: true }));
      console.log("[AUTOGIGS] Responsável do processo definido:", responsavel);
    }
  } catch(e) {
    console.log("[AUTOGIGS] Erro ao definir responsável do processo:", e);
  }
}

function concluirAtividadesGigs(config, gigsFechado) {
  try {
    // Aguardar carregamento da lista de atividades
    setTimeout(function() {
      var atividades = document.querySelectorAll('div[id="tabela-atividades"] table tbody tr');
      
      if (atividades.length === 0) {
        console.log("[AUTOGIGS][GIGS] Nenhuma atividade encontrada");
        alert('Nenhuma atividade encontrada para concluir.');
        return;
      }
      
      var tipoAtividadeFiltro = (config.tipo_atividade || '').toLowerCase().split(';');
      var responsavelFiltro = (config.responsavel || '').toLowerCase().split(';');
      var observacaoFiltro = (config.observacao || '').toLowerCase().split(';');
      var concluidas = 0;
      
      atividades.forEach(function(atividade) {
        try {
          // Extrair informações da atividade
          var responsavelElem = atividade.querySelector('span[class*="texto-responsavel"]');
          var responsavelTexto = responsavelElem ? responsavelElem.textContent.toLowerCase() : "";
          
          var descricaoElem = atividade.querySelector('span[class*="descricao"]');
          var descricaoTexto = descricaoElem ? descricaoElem.textContent.toLowerCase().split(':')[0] : "";
          
          var textoCompleto = atividade.textContent.toLowerCase();
          var observacaoTexto = textoCompleto.replace(descricaoTexto + ':', '').replace(responsavelTexto, '');
          
          // Verificar critérios de filtro
          var condicao1 = !tipoAtividadeFiltro[0] || tipoAtividadeFiltro.some(function(t) { return t && descricaoTexto.includes(t); });
          var condicao2 = !responsavelFiltro[0] || responsavelFiltro.some(function(r) { return r && responsavelTexto.includes(r); });
          var condicao3 = !observacaoFiltro[0] || observacaoFiltro.some(function(o) { return o && observacaoTexto.includes(o); });
          
          if (condicao1 && condicao2 && condicao3) {
            // Concluir atividade
            var btnConcluir = atividade.querySelector('button[aria-label="Concluir Atividade"]');
            if (btnConcluir) {
              atividade.scrollIntoView();
              btnConcluir.click();
                // Confirmar conclusão
              setTimeout(function() {
                try {
                  var btnSim = findElementByText('mat-dialog-container button', 'Sim');
                  if (btnSim) {
                    btnSim.click();
                    concluidas++;
                    console.log("[AUTOGIGS][GIGS] Atividade concluída:", descricaoTexto);
                  }
                } catch(e) {}
              }, 500);
            }
          }
        } catch(e) {
          console.log("[AUTOGIGS][GIGS][ERRO] Falha ao processar atividade:", e);
        }
      });
      
      setTimeout(function() {
        if (gigsFechado) {
          fecharGigs();
        }
        console.log("[AUTOGIGS][GIGS] Total de atividades concluídas:", concluidas);
        alert('Total de atividades concluídas: ' + concluidas);
      }, 2000);
    }, 1000);
    
  } catch(e) {
    console.error("[AUTOGIGS][GIGS][ERRO] Falha ao concluir atividades:", e);
    alert('Erro ao concluir atividades: ' + e.message);
  }
}

function adicionarAtividadeGigs(config, gigsFechado) {
  try {
    // Verificar se o painel GIGS está visível
    try {
      document.querySelector('pje-gigs-ficha-processo');
    } catch(e) {
      abrirGigs();
    }
      // Clicar em Nova atividade
    setTimeout(function() {
      var btnNova = findElementByText('pje-gigs-lista-atividades button', 'Nova atividade') ||
                   document.querySelector('button[aria-label*="Nova atividade"]');
      if (btnNova) {
        btnNova.click();
        
        // Aguardar carregamento do formulário
        setTimeout(function() {
          preencherFormularioAtividade(config, gigsFechado);
        }, 1000);
      }
    }, 500);
    
  } catch(e) {
    console.error("[AUTOGIGS][GIGS][ERRO] Falha ao adicionar atividade:", e);
    alert('Erro ao adicionar atividade: ' + e.message);
  }
}

function preencherFormularioAtividade(config, gigsFechado) {
  try {
    // Preencher tipo de atividade
    var tipoAtividade = config.tipo_atividade || '';
    if (tipoAtividade) {
      var campoTipo = document.querySelector('input[formcontrolname="tipoAtividade"]');
      if (campoTipo) {
        campoTipo.focus();
        
        // Simular tecla para baixo para abrir dropdown
        var event = new KeyboardEvent('keydown', {
          key: 'ArrowDown',
          code: 'ArrowDown',
          keyCode: 40,
          bubbles: true
        });
        campoTipo.dispatchEvent(event);
          setTimeout(function() {
          var opcao = findElementByText('mat-option', tipoAtividade);
          if (opcao) {
            opcao.click();
          }
        }, 500);
      }
    }
    
    // Preencher responsável
    setTimeout(function() {
      var responsavel = config.responsavel || '';
      if (responsavel) {
        var campoResp = document.querySelector('input[formcontrolname="responsavel"]');
        if (campoResp) {
          campoResp.value = responsavel;
          campoResp.dispatchEvent(new Event('input', { bubbles: true }));
        }
      }
      
      // Preencher observação
      var observacao = config.observacao || '';
      if (observacao) {
        var campoObs = document.querySelector('textarea[formcontrolname="observacao"]');
        if (campoObs) {
          campoObs.value = observacao;
          campoObs.dispatchEvent(new Event('input', { bubbles: true }));
        }
      }
      
      // Preencher prazo
      var prazo = config.prazo || '';
      if (prazo) {
        var campoPrazo = document.querySelector('input[formcontrolname="prazo"]');
        if (campoPrazo) {
          campoPrazo.value = prazo;
          campoPrazo.dispatchEvent(new Event('input', { bubbles: true }));
        }
      }
      
      // Salvar se configurado
      var salvar = (config.salvar || '').toLowerCase() === 'sim';
      if (salvar) {        setTimeout(function() {
          var btnSalvar = findElementByText('button', 'Salvar');
          if (btnSalvar) {
            btnSalvar.click();
            
            setTimeout(function() {
              if (gigsFechado) {
                fecharGigs();
              }
              console.log("[AUTOGIGS][GIGS] Atividade GIGS criada com sucesso");
              alert('Atividade GIGS criada com sucesso!');
            }, 1000);
          }
        }, 1000);
      } else {
        alert('Formulário preenchido. Clique em Salvar manualmente para finalizar.');
      }
    }, 1000);
    
  } catch(e) {
    console.error("[AUTOGIGS][GIGS][ERRO] Falha ao preencher formulário:", e);
    alert('Erro ao preencher formulário: ' + e.message);
  }
}

// Fluxo completo de Anexar baseado na função Python acao_bt_anexar_selenium
function fluxoAnexar(config) {
  console.log('[ANEXAR] Iniciando ação automatizada de anexar:', config.tipo || '', '-', config.modelo || '');
  
  try {
    // 1. Clicar no botão de anexar documentos (fa-paperclip)
    setTimeout(function() {
      try {
        var btnAnexar = document.querySelector('#pjextension_bt_detalhes_4') ||
                       document.querySelector('button[aria-label*="anexar"], button[title*="anexar"]') ||
                       document.querySelector('button i.fa-paperclip').closest('button');
        if (btnAnexar) {
          btnAnexar.click();
          console.log('[ANEXAR] Botão de anexar documentos clicado.');
        }
      } catch(e) {
        console.log('[ANEXAR] Botão de anexar documentos não encontrado ou já clicado.');
      }
      
      // Aguardar carregamento da tela de anexação
      setTimeout(function() { continuarFluxoAnexar(config); }, 1000);
    }, 500);
    
  } catch(e) {
    console.error('[ANEXAR] Erro geral:', e);
    alert('Erro no fluxo Anexar: ' + e.message);
  }
}

function continuarFluxoAnexar(config) {
  try {
    // 2. PDF?
    if (config.modelo && config.modelo.toLowerCase() === 'pdf') {
      try {
        var switchPdf = document.querySelector('input[role="switch"]');
        if (switchPdf && !switchPdf.checked) {
          switchPdf.click();
          console.log('[ANEXAR] Switch PDF ativado.');
        }
      } catch(e) {
        console.log('[ANEXAR] Switch PDF não encontrado.');
      }
    }
    
    // 3. Preencher tipo
    setTimeout(function() {
      var tipo = config.tipo || 'Certidão';
      try {
        var campoTipo = document.querySelector('input[aria-label="Tipo de Documento"]');
        if (campoTipo) {
          campoTipo.value = '';
          campoTipo.value = tipo;
          campoTipo.dispatchEvent(new Event('input', { bubbles: true }));
          
          // Simular Enter
          var enterEvent = new KeyboardEvent('keydown', {
            key: 'Enter',
            code: 'Enter',
            keyCode: 13,
            which: 13,
            bubbles: true
          });
          campoTipo.dispatchEvent(enterEvent);
          
          console.log('[ANEXAR] Tipo de documento selecionado:', tipo);
        }
      } catch(e) {
        console.log('[ANEXAR][ERRO] Falha ao selecionar tipo:', e);
      }
      
      // 4. Preencher descrição
      setTimeout(function() {
        if (config.descricao) {
          try {
            var campoDesc = document.querySelector('input[aria-label="Descrição"]');
            if (campoDesc) {
              campoDesc.value = '';
              campoDesc.value = config.descricao;
              campoDesc.dispatchEvent(new Event('input', { bubbles: true }));
              campoDesc.dispatchEvent(new Event('change', { bubbles: true }));
              console.log('[ANEXAR] Descrição preenchida:', config.descricao);
            }
          } catch(e) {
            console.log('[ANEXAR] Campo de descrição não encontrado.');
          }
        }
        
        // 5. Sigilo
        var sigilo = (config.sigilo || 'nao').toLowerCase();
        if (sigilo.includes('sim')) {
          try {
            var chkSigilo = document.querySelector('input[name="sigiloso"]');
            if (chkSigilo && !chkSigilo.checked) {
              chkSigilo.click();
              console.log('[ANEXAR] Sigilo ativado.');
            }
          } catch(e) {
            console.log('[ANEXAR] Campo de sigilo não encontrado.');
          }
        }
        
        // 6. Escolha do modelo
        setTimeout(function() {
          if (config.modelo && config.modelo.toLowerCase() !== 'pdf') {
            try {
              var campoModelo = document.querySelector('input[id="inputFiltro"]');
              if (campoModelo) {
                campoModelo.value = '';
                campoModelo.value = config.modelo;
                campoModelo.dispatchEvent(new Event('input', { bubbles: true }));
                
                // Simular Enter
                var enterEvent = new KeyboardEvent('keydown', {
                  key: 'Enter',
                  code: 'Enter',
                  keyCode: 13,
                  which: 13,
                  bubbles: true
                });
                campoModelo.dispatchEvent(enterEvent);
                
                console.log('[ANEXAR] Modelo selecionado:', config.modelo);
                  // Aguardar e clicar no modelo na árvore
                setTimeout(function() {
                  try {
                    var modeloItem = findElementByText('div[role="treeitem"]', config.modelo) ||
                                   findElementByText('div[role="treeitem"] span', config.modelo);
                    if (modeloItem) {
                      modeloItem.click();
                      console.log('[ANEXAR] Modelo inserido no editor.');
                    }
                  } catch(e) {
                    console.log('[ANEXAR] Erro ao inserir modelo na árvore.');
                  }
                }, 1000);
              }
            } catch(e) {
              console.log('[ANEXAR][ERRO] Não foi possível selecionar/inserir modelo:', e);
            }
          }
          
          // 7. Upload de PDF (se modelo for PDF)
          if (config.modelo && config.modelo.toLowerCase() === 'pdf') {
            setTimeout(function() {
              try {
                var btnUpload = document.querySelector('label.upload-button') ||
                               document.querySelector('input[type="file"]').closest('label');
                if (btnUpload) {
                  btnUpload.click();
                  console.log('[ANEXAR] Botão de upload de PDF clicado. Aguarde seleção manual do arquivo.');
                  alert('Selecione o arquivo PDF para upload e aguarde o carregamento antes de continuar.');
                  
                  // Aguardar upload e preencher descrição com nome do PDF se não especificada
                  if (!config.descricao) {
                    setTimeout(function() {
                      verificarUploadPdf();
                    }, 2000);
                  }
                }
              } catch(e) {
                console.log('[ANEXAR][ERRO] Upload de PDF:', e);
              }
            }, 1000);
          }
          
          // 8. Processar extras e finalizar
          setTimeout(function() { finalizarFluxoAnexar(config); }, 2000);
        }, 1000);
      }, 1000);
    }, 500);
    
  } catch(e) {
    console.error('[ANEXAR] Erro na continuação do fluxo:', e);
    alert('Erro na continuação do fluxo Anexar: ' + e.message);
  }
}

function verificarUploadPdf() {
  try {
    var spanPdf = document.querySelector('span.nome-arquivo-pdf');
    if (spanPdf) {
      var nomePdf = spanPdf.textContent.replace('.pdf', '');
      var campoDesc = document.querySelector('input[aria-label="Descrição"]');
      if (campoDesc && !campoDesc.value) {
        campoDesc.value = nomePdf;
        campoDesc.dispatchEvent(new Event('input', { bubbles: true }));
        campoDesc.dispatchEvent(new Event('change', { bubbles: true }));
        console.log('[ANEXAR] Descrição preenchida com nome do PDF:', nomePdf);
      }
    }
  } catch(e) {
    console.log('[ANEXAR] Não foi possível preencher descrição com nome do PDF.');
  }
}

function finalizarFluxoAnexar(config) {
  try {
    // 8. Juntada de depoimentos/anexos
    var extras = config.extras || '';
    var nmBotao = config.nm_botao || config.nome || '';
    
    if (extras.toLowerCase().includes('[anexos]') || extras === 'ID997_Anexar Depoimento') {
      try {
        // Salvar documento primeiro
        var btnSalvar = document.querySelector('button[aria-label="Salvar"]');
        if (btnSalvar) {
          btnSalvar.click();
          console.log('[ANEXAR] Documento salvo para anexos.');
        }
        
        setTimeout(function() {
          // Abrir guia de anexos
          var guiaAnexos = document.querySelector('div[aria-posinset="2"]');
          if (guiaAnexos) {
            guiaAnexos.click();
            console.log('[ANEXAR] Guia Anexos aberta.');
            
            setTimeout(function() {
              // Botão de upload de anexo
              var btnUploadAnexo = document.querySelector('label.upload-button') ||
                                  document.querySelector('input[type="file"]').closest('label');
              if (btnUploadAnexo) {
                btnUploadAnexo.click();
                console.log('[ANEXAR] Botão de upload de anexo clicado.');
                alert('Selecione os arquivos de anexo para upload.');
                
                if (extras === 'ID997_Anexar Depoimento') {
                  setTimeout(function() {
                    if (guiaAnexos) guiaAnexos.click();
                    console.log('[ANEXAR] Fluxo de depoimento finalizado.');
                    alert('Fluxo de anexação de depoimento finalizado.');
                  }, 2000);
                  return;
                }
              }
            }, 1000);
          }
        }, 1000);
        
        return; // Sair aqui para fluxos de anexos
      } catch(e) {
        console.log('[ANEXAR][ERRO] Juntada de anexos:', e);
      }
    }
    
    // 9. Assinar ou salvar (fluxo normal)
    setTimeout(function() {
      var assinar = (config.assinar || 'nao').toLowerCase();
      if (assinar === 'sim') {
        try {
          var btnAssinar = document.querySelector('button[aria-label="Assinar documento e juntar ao processo"]');
          if (btnAssinar) {
            btnAssinar.click();
            console.log('[ANEXAR] Documento assinado e juntado ao processo.');
            alert('Documento assinado e juntado ao processo com sucesso!');
          }
        } catch(e) {
          console.log('[ANEXAR][ERRO] Assinar documento:', e);
          // Fallback para salvar
          try {
            var btnSalvar = document.querySelector('button[aria-label="Salvar"]');
            if (btnSalvar) {
              btnSalvar.click();
              console.log('[ANEXAR] Documento salvo (fallback).');
              alert('Documento salvo com sucesso!');
            }
          } catch(e2) {
            console.log('[ANEXAR][ERRO] Salvar documento (fallback):', e2);
          }
        }
      } else {
        try {
          var btnSalvar = document.querySelector('button[aria-label="Salvar"]');
          if (btnSalvar) {
            btnSalvar.click();
            console.log('[ANEXAR] Documento salvo.');
            alert('Documento salvo com sucesso!');
          }
        } catch(e) {
          console.log('[ANEXAR][ERRO] Salvar documento:', e);
        }
      }
      
      console.log('[ANEXAR] Fluxo de anexar documento automatizado finalizado.');
    }, 1000);
    
  } catch(e) {
    console.error('[ANEXAR] Erro na finalização:', e);
    alert('Erro na finalização do fluxo Anexar: ' + e.message);
  }
}

// Exporte para uso global
window.fluxoDespacho = fluxoDespacho;
window.fluxoGigs = fluxoGigs;
window.fluxoAnexar = fluxoAnexar;
