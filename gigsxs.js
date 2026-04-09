// ==UserScript==
// @name         GIGS XSXS Overlay - Carrega Gigs da Tabela de Atividades
// @namespace    http://tampermonkey.net/
// @version      1.0
// @description  Carrega dados de GIGS para todos os processos em xsxs (tabela de Atividades) e mostra como overlay
// @author       PJePlus
// @match        https://pje.trt2.jus.br/pjekz/gigs/relatorios/atividades*
// @grant        GM_addStyle
// @run-at       document-idle
// ==/UserScript==

(async function() {
  'use strict';

  // ============================================
  // BLOCO 1: Regex e Helpers
  // ============================================
  const padraoData = /\d{2,4}\D{1}\d{2,4}\D{1}\d{2,4}/g;
  
  function extrairIdDoProcessoBruto(texto) {
    const match = String(texto || '').match(/\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}/);
    return match ? match[0] : null;
  }

  function getUrlBase() {
    const url = document.location.origin;
    return url.replace('https://', '').replace('http://', '');
  }

  // ============================================
  // BLOCO 2: Buscar ID Processo por Número
  // ============================================
  async function obterIdProcessoPorNumero(numeroProcesso) {
    try {
      const urlBase = getUrlBase();
      const url = `https://${urlBase}/pje-comum-api/api/processos?numero=${encodeURIComponent(numeroProcesso)}`;
      const resp = await fetch(url, {
        method: 'GET',
        credentials: 'include',
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json'
        }
      });
      
      if (!resp.ok) {
        console.warn(`[gigs-xsxs] Status ${resp.status} ao buscar ID do processo ${numeroProcesso}`);
        return null;
      }
      
      const dados = await resp.json();
      if (typeof dados === 'number') return String(dados);
      if (Array.isArray(dados) && dados[0] && dados[0].id) return String(dados[0].id);
      if (dados && dados.id) return String(dados.id);
      return null;
    } catch (e) {
      console.error(`[gigs-xsxs] Erro ao buscar ID do processo ${numeroProcesso}:`, e);
      return null;
    }
  }

  // ============================================
  // BLOCO 3: Obter GIGs de um Processo
  // ============================================
  async function obterGigsDoProcesso(idProcesso) {
    try {
      const urlBase = getUrlBase();
      const url = `https://${urlBase}/pje-gigs-api/api/atividade/processo/${idProcesso}`;
      const resp = await fetch(url, {
        method: 'GET',
        credentials: 'include',
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json'
        }
      });
      
      if (!resp.ok) {
        console.warn(`[gigs-xsxs] Status ${resp.status} ao buscar GIGS do processo ${idProcesso}`);
        return [];
      }
      
      const dados = await resp.json();
      if (!Array.isArray(dados)) {
        console.warn(`[gigs-xsxs] Resposta de GIGS não é array para processo ${idProcesso}`);
        return [];
      }
      
      const lista = [];
      for (const atividade of dados) {
        let data = atividade.dataPrazo || '';
        if (padraoData.test(data)) {
          const match = data.match(padraoData)[0];
          const [ano, mes, dia] = match.split('-');
          data = `${dia}/${mes}/${ano}`;
        }
        
        lista.push({
          tipoAtividade: atividade.tipoAtividade?.descricao || atividade.tipoAtividade || '',
          dataPrazo: data,
          statusAtividade: atividade.statusAtividade || '',
          observacao: atividade.observacao || '',
          responsavel: atividade.responsavel || ''
        });
      }
      
      return lista;
    } catch (e) {
      console.error(`[gigs-xsxs] Erro ao buscar GIGS do processo ${idProcesso}:`, e);
      return [];
    }
  }

  // ============================================
  // BLOCO 4: Aplica Filtros Iniciais
  // ============================================
  async function aplicarFiltrosIniciais() {
    console.log('[gigs-xsxs] Aplicando filtros iniciais...');
    
      // Ação inicial: clicar no botão "Remover filtro" se existir
      const btnRemoverFiltro = document.querySelector('button.chips-icone-fechar[aria-label*="Remover Filtro"]');
      if (btnRemoverFiltro) btnRemoverFiltro.click();
    
    try {
      // 1. Clica no ícone "Atividades sem prazo"
      const iconoAtividadesSemPrazo = document.querySelector('i.fa.fa-pen.atividade-sem-prazo.icone-clicavel');
      if (iconoAtividadesSemPrazo) {
        console.log('[gigs-xsxs] Clicando em "Atividades sem prazo"...');
        iconoAtividadesSemPrazo.click();
        await new Promise(resolve => setTimeout(resolve, 500));
      } else {
        console.warn('[gigs-xsxs] Ícone "Atividades sem prazo" não encontrado');
      }
      
      // 2. Localiza e preenche o input de descrição
      const inputDescricao = document.querySelector('input[aria-label="Descrição da Atividade"]');
      if (inputDescricao) {
        console.log('[gigs-xsxs] Preenchendo filtro com "xs"...');
        inputDescricao.focus();
        await new Promise(resolve => setTimeout(resolve, 200));
        inputDescricao.value = 'xs';
        
        // Dispara evento de input para Angular reconhecer
        const event = new Event('input', { bubbles: true });
        inputDescricao.dispatchEvent(event);
        
        await new Promise(resolve => setTimeout(resolve, 300));
        
        // 3. Pressiona Enter
        console.log('[gigs-xsxs] Pressionando Enter...');
        const enterEvent = new KeyboardEvent('keydown', {
          key: 'Enter',
          code: 'Enter',
          keyCode: 13,
          which: 13,
          bubbles: true,
          cancelable: true
        });
        inputDescricao.dispatchEvent(enterEvent);
        
        await new Promise(resolve => setTimeout(resolve, 800));
      } else {
        console.warn('[gigs-xsxs] Input de Descrição não encontrado');
      }
      
      // 4. Aguarda a tabela renderizar
      console.log('[gigs-xsxs] Aguardando tabela renderizar...');
      await new Promise(resolve => setTimeout(resolve, 1500));
      
      console.log('[gigs-xsxs] Filtros iniciais aplicados com sucesso');
      return true;
    } catch (e) {
      console.error('[gigs-xsxs] Erro ao aplicar filtros iniciais:', e);
      return false;
    }
  }

  // ============================================
  // BLOCO 4.1: Lê Tabela e Extrai Processos
  // ============================================
  function lerProcessosDaTabelaXsxs() {
    const processos = [];
    const linhas = document.querySelectorAll('pje-gigs-relatorio-atividades table.t-class tbody tr');
    
    for (const linha of linhas) {
      const link = linha.querySelector('a.link.processo');
      if (!link) continue;
      
      const numero = extrairIdDoProcessoBruto(link.innerText || '');
      if (numero) {
        processos.push({ numero, linha });
      }
    }
    
    return processos;
  }

  // ============================================
  // BLOCO 5: Renderiza Overlay
  // ============================================
  function renderizarOverlay(tdResponsavel, gigs) {
    let html = '<div style="font-size: 1.2em; color: #222; background: rgba(255, 255, 255, 0.98); border: 2px solid #0066cc; border-radius: 6px; padding: 12px 16px; min-width: 400px; line-height: 1.6;">';
    
    if (!gigs || gigs.length === 0) {
      html += '<strong style="color: #666;">Sem observações</strong>';
    } else {
      const observacoes = gigs
        .map(item => item.observacao || '')
        .filter(obs => obs.trim() !== '')
        .map((obs, idx) => `<strong>${idx + 1}.</strong> ${obs.replace(/</g, '&lt;').replace(/>/g, '&gt;')}`)
        .join(' | ');
      
      if (observacoes) {
        html += observacoes;
      } else {
        html += '<strong style="color: #999;">Nenhuma observação registrada</strong>';
      }
    }
    
    html += '</div>';
    tdResponsavel.innerHTML = html;
  }

  // ============================================
  // BLOCO 6: Orquestrador Principal
  // ============================================
  async function executarXsxsOverlay() {
    console.log('[gigs-xsxs] Iniciando leitura de GIGS para tabela XSXS...');
    
    const processosComLinha = lerProcessosDaTabelaXsxs();
    console.log(`[gigs-xsxs] Encontrados ${processosComLinha.length} processos na tabela`);
    
    if (!processosComLinha.length) {
      console.warn('[gigs-xsxs] Nenhum processo encontrado na tabela');
      return;
    }
    
    for (const { numero, linha } of processosComLinha) {
      try {
        console.log(`[gigs-xsxs] Processando ${numero}...`);
        
        let idProcesso = await obterIdProcessoPorNumero(numero);
        if (!idProcesso) {
          console.warn(`[gigs-xsxs] ID não encontrado para ${numero}`);
          continue;
        }
        
        const gigs = await obterGigsDoProcesso(idProcesso);
        
        // Localiza TD de Responsável: último TD com div vazio que contém tooltip
        // Estrutura: <td class="td-class"><div class="mat-tooltip-trigger">  </div></td>
        const tdsTodos = linha.querySelectorAll('td.td-class');
        let tdResponsavel = null;
        
        for (let i = tdsTodos.length - 3; i < tdsTodos.length - 1; i++) {
          if (i >= 0 && i < tdsTodos.length) {
            const div = tdsTodos[i].querySelector('div.mat-tooltip-trigger');
            if (div && div.innerText.trim() === '') {
              tdResponsavel = tdsTodos[i];
              break;
            }
          }
        }
        
        if (!tdResponsavel) {
          tdResponsavel = linha.querySelector('td:nth-child(7)');
        }
        
        if (tdResponsavel) {
          renderizarOverlay(tdResponsavel, gigs);
          console.log(`[gigs-xsxs] ✓ ${numero} atualizado com ${gigs.length} GIGS`);
        } else {
          console.warn(`[gigs-xsxs] TD de Responsável não encontrado para ${numero}`);
        }
        
        // Pequena pausa entre requisições
        await new Promise(resolve => setTimeout(resolve, 200));
        
      } catch (e) {
        console.error(`[gigs-xsxs] Erro ao processar ${numero}:`, e);
      }
    }
    
    console.log('[gigs-xsxs] Conclusão: Overlay renderizado para todos os processos');
  }

  // ============================================
  // BLOCO 6.5: Executar Fluxo Completo (Filtros + GIGS)
  // ============================================
  async function executarFluxoCompleto() {
    const filtrosAplicados = await aplicarFiltrosIniciais();
    if (filtrosAplicados) {
      await executarXsxsOverlay();
    } else {
      console.warn('[gigs-xsxs] Fluxo abortado: falha ao aplicar filtros iniciais');
    }
  }

  // ============================================
  // BLOCO 7: Criar Botão de Ativação
  // ============================================
  function criarBotaoLerGigs() {
    // CSS para o botão
    const estilo = `
      #gigs-xsxs-btn {
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 12px 20px;
        background-color: #1976d2;
        color: white;
        border: none;
        border-radius: 4px;
        cursor: pointer;
        font-weight: bold;
        font-size: 14px;
        z-index: 10000;
        box-shadow: 0 2px 8px rgba(0,0,0,0.2);
        transition: background-color 0.3s ease;
      }
      #gigs-xsxs-btn:hover {
        background-color: #1565c0;
      }
      #gigs-xsxs-btn:active {
        transform: scale(0.95);
      }
    `;
    
    // Injeta CSS
    const styleEl = document.createElement('style');
    styleEl.textContent = estilo;
    document.head.appendChild(styleEl);
    
    // Cria botão
    const botao = document.createElement('button');
    botao.id = 'gigs-xsxs-btn';
    botao.textContent = '🔄 Ler gigs';
    botao.onclick = async function(e) {
      e.preventDefault();
      botao.disabled = true;
      botao.textContent = '⏳ Carregando...';
      try {
        await executarFluxoCompleto();
        botao.textContent = '✓ Concluído';
        setTimeout(() => {
          botao.textContent = '🔄 Ler gigs';
          botao.disabled = false;
        }, 2000);
      } catch (e) {
        console.error('[gigs-xsxs] Erro ao carregar:', e);
        botao.textContent = '✗ Erro';
        setTimeout(() => {
          botao.textContent = '🔄 Ler gigs';
          botao.disabled = false;
        }, 2000);
      }
    };
    
    document.body.appendChild(botao);
    console.log('[gigs-xsxs] Botão "Ler gigs" injetado no canto superior direito');
  }

  // ============================================
  // BLOCO 8: Ativa o Script
  // ============================================
  // Injeta botão de ativação
  criarBotaoLerGigs();
  
  // Também expõe funções globais para execução manual
  window.gigsXsxsOverlayFluxoCompleto = executarFluxoCompleto;
  window.gigsXsxsOverlayRecarregar = executarXsxsOverlay;
  console.log('[gigs-xsxs] Script carregado. Clique no botão "🔄 Ler gigs" ou execute window.gigsXsxsOverlayFluxoCompleto()');
})();
