/*
 * ============================================================================
 *  PJe — Trocar Meio de Expedição para Correios + Restabelecer Prazo 5 dias
 * ============================================================================
 *
 *  Replica em JS puro a lógica de `atos/comunicacao_finalizacao.py`:
 *      alterar_meio_expedicao(...) + _restabelecer_prazo_da_linha(...)
 *
 *  Para CADA linha da tabela de expedientes:
 *      1. lê o meio atual
 *      2. se já é Correios, pula
 *      3. troca para Correios (dropdown mat-select -> mat-option)
 *      4. AGUARDA o Angular reavaliar (enderecovalido / expedientesmateria)
 *      5. restabelece prazo: rádio "dias úteis" + input = 5
 *      6. CONFIRMA 6.1 meio == Correios, 6.2 rádio dias úteis, 6.3 input == 5
 *      7. só então passa para a próxima linha
 *
 *  Uso: cole no console do PJe, na tela
 *       /pjekz/processo/<id>/comunicacoesprocessuais/minutas
 *  NÃO clica em Salvar/Assinar. Só altera os campos na tela.
 * ============================================================================
 */
(async function pjeTrocarCorreiosPrazo5() {
  'use strict';

  // ── Configuração ────────────────────────────────────────────────────────
  const PRAZO_DIAS = 5;          // dias úteis a restabelecer
  const MAX_TENTATIVAS = 3;      // tentativas por linha (a tabela re-renderiza)
  const ESPERA_RENDER_MS = 700;  // espera base após trocar o meio
  const ESPERA_PRAZO_MS = 400;   // espera base após preencher o prazo

  // ── Utilitários ─────────────────────────────────────────────────────────
  const log = (msg) => console.log('%c[PET-CORREIOS]', 'color:#0a84ff;font-weight:bold', msg);
  const warn = (msg) => console.warn('%c[PET-CORREIOS]', 'color:#ff9f0a;font-weight:bold', msg);
  const err = (msg) => console.error('%c[PET-CORREIOS]', 'color:#ff453a;font-weight:bold', msg);

  const dormir = (ms) => new Promise((r) => setTimeout(r, ms));

  const norm = (t) =>
    String(t || '')
      .normalize('NFD').replace(/[\u0300-\u036f]/g, '')
      .toLowerCase().trim();

  /** Aguarda `fn()` retornar truthy, até `ms` (poll a cada 100ms). */
  async function esperarPor(fn, ms, descricao) {
    const fim = Date.now() + ms;
    while (Date.now() < fim) {
      try { const v = fn(); if (v) return v; } catch (e) { /* DOM instável */ }
      await dormir(100);
    }
    if (descricao) warn('timeout esperando: ' + descricao);
    return null;
  }

  /** Dispara input/change/blur como o usuário faria (Angular escuta isso). */
  function escreverValor(inp, valor) {
    const setter = Object.getOwnPropertyDescriptor(
      window.HTMLInputElement.prototype, 'value'
    ).set;
    setter.call(inp, String(valor));
    inp.dispatchEvent(new Event('input', { bubbles: true }));
    inp.dispatchEvent(new Event('change', { bubbles: true }));
    inp.dispatchEvent(new Event('blur', { bubbles: true }));
  }

  // ── Leitura do DOM ──────────────────────────────────────────────────────
  /** Linhas de destinatário da tabela de expedientes. */
  const linhas = () =>
    Array.from(document.querySelectorAll('tbody.cdk-drop-list tr.cdk-drag'));

  /** Texto do meio de expedição da linha. */
  function meioAtual(tr) {
    const sel = tr.querySelector(
      'mat-select[id*="MeioExpedicao"], pje-pec-coluna-meio-expedicao mat-select'
    );
    if (!sel) return '';
    const alvo = sel.querySelector('.mat-select-value-text, .mat-select-min-line');
    return (alvo ? alvo.textContent : sel.textContent) || '';
  }

  /** Nome da parte (para o relatório). */
  function nomeParte(tr) {
    const el = tr.querySelector('.pec-nome-parte-tabela-destinatarios');
    return el ? el.textContent.trim().replace(/\s+/g, ' ').slice(0, 60) : '(sem nome)';
  }

  /** Hash da linha: `destinatario_<hash>` derivado do id do select de meio. */
  function hashLinha(tr) {
    const sel = tr.querySelector('mat-select[id*="MeioExpedicao"]');
    if (!sel) return null;
    const id = sel.id || '';
    if (!id.endsWith('MeioExpedicao')) return null;
    return id.slice(0, -'MeioExpedicao'.length); // ex.: destinatario_rxzf2dnuu
  }

  /** Rádio de tipo de prazo marcado na linha: 'dias_uteis' | 'sem_prazo' | ... */
  function tipoPrazoAtual(tr) {
    // IMPORTANTE: restringir à coluna de prazo. A linha tem outro mat-radio-group
    // (signatário: "Usuário"), que também usa .mat-radio-checked e seria pego
    // por um seletor amplo — foi o que devolvia '' antes.
    const marcado = tr.querySelector(
      'pje-pec-coluna-tipo-prazo mat-radio-button.mat-radio-checked'
    ) || tr.querySelector('mat-radio-button[id*="TipoPrazo"][class*="mat-radio-checked"]');
    if (!marcado) return '';
    const t = norm(marcado.textContent);
    if (t.includes('sem prazo')) return 'sem_prazo';
    if (t.includes('data certa')) return 'data_certa';
    if (t.includes('corridos')) return 'dias_corridos';
    if (t.includes('uteis')) return 'dias_uteis';
    return '';
  }

  /** Valor atual do input de prazo em dias úteis (string) ou ''. */
  function valorPrazoAtual(tr) {
    if (!tr) return '';
    const hash = hashLinha(tr);
    const inp = (hash && document.getElementById(hash + 'PrazoDiasUteis')) ||
      tr.querySelector('input[id$="PrazoDiasUteis"]');
    return inp ? String(inp.value ?? '') : '';
  }

  /** Opção Correios visível no overlay do Angular Material. */
  function opcaoCorreiosVisivel() {
    const opcoes = Array.from(
      document.querySelectorAll('.cdk-overlay-pane mat-option, mat-option')
    );
    return opcoes.find((o) => {
      const nome = norm(o.getAttribute('name'));
      const txt = norm(o.textContent);
      if (!(nome === 'correios' || txt.includes('correio'))) return false;
      // visível de fato (o Material mantém opções antigas no DOM)
      const r = o.getBoundingClientRect();
      return r.width > 0 && r.height > 0;
    });
  }

  // ── Ações ───────────────────────────────────────────────────────────────

  /**
   * Abre o mat-select da linha e clica em Correios.
   * Retorna true se a linha passou a exibir "Correios".
   */
  async function trocarParaCorreios(idx, tr) {
    for (let tentativa = 1; tentativa <= MAX_TENTATIVAS; tentativa++) {
      // Re-consulta: o Angular re-renderiza a linha a cada troca.
      const atual = linhas()[idx - 1];
      if (!atual) { err(`Linha ${idx}: sumiu do DOM`); return false; }

      if (norm(meioAtual(atual)).includes('correio')) {
        return true;
      }

      const sel = atual.querySelector(
        'mat-select[id*="MeioExpedicao"], pje-pec-coluna-meio-expedicao mat-select'
      );
      if (!sel) { warn(`Linha ${idx}: select de meio não encontrado (tentativa ${tentativa})`); await dormir(ESPERA_RENDER_MS); continue; }

      // 1. abre o dropdown
      sel.click();
      sel.dispatchEvent(new MouseEvent('mousedown', { bubbles: true }));
      await dormir(250);

      // 2. espera a opção Correios ficar VISÍVEL (não basta existir no DOM)
      const opt = await esperarPor(opcaoCorreiosVisivel, 2000, `linha ${idx}: opção Correios visível`);
      if (!opt) {
        document.body.click(); // fecha overlay
        await dormir(200);
        continue;
      }

      // 3. clica
      opt.click();
      opt.dispatchEvent(new MouseEvent('mousedown', { bubbles: true }));
      opt.dispatchEvent(new MouseEvent('mouseup', { bubbles: true }));

      // 4. o PJe reavalia o expediente (expedientesmateria) e pode re-renderizar
      await dormir(ESPERA_RENDER_MS);

      const ok = await esperarPor(
        () => {
          const l = linhas()[idx - 1];
          return l && norm(meioAtual(l)).includes('correio');
        },
        2500,
        `linha ${idx}: confirmação Correios`
      );
      if (ok) return true;

      warn(`Linha ${idx}: clique em Correios não registrou (tentativa ${tentativa}/${MAX_TENTATIVAS})`);
      await dormir(300);
    }
    return false;
  }

  /**
   * Restabelece o prazo em dias úteis.
   * Marca o rádio "dias úteis" e escreve PRAZO_DIAS no input.
   * Retorna {ok, motivo}.
   */
  async function restabelecerPrazo(idx) {
    // Re-consulta após a re-renderização da troca de meio.
    const tr = await esperarPor(() => linhas()[idx - 1], 1500, `linha ${idx}: existe`);
    if (!tr) return { ok: false, motivo: 'linha ausente' };

    const hash = hashLinha(tr);

    // 1. marcar o rádio "dias úteis"
    const radioDiasUteis =
      (hash && document.getElementById(hash + 'TipoPrazoD-input')) ||
      tr.querySelector('pje-pec-coluna-tipo-prazo mat-radio-button[id$="TipoPrazoD"] input[type="radio"]') ||
      tr.querySelector('mat-radio-button[id$="TipoPrazoD"] input[type="radio"]');

    if (!radioDiasUteis) {
      return { ok: false, motivo: 'rádio "dias úteis" não encontrado' };
    }
    if (!radioDiasUteis.checked) {
      radioDiasUteis.click();
      await dormir(250);
    }

    // 2. preencher o input de dias
    const inputDias =
      (hash && document.getElementById(hash + 'PrazoDiasUteis')) ||
      tr.querySelector('input[id$="PrazoDiasUteis"]');

    if (!inputDias) {
      return { ok: false, motivo: 'input de prazo não encontrado' };
    }

    escreverValor(inputDias, PRAZO_DIAS);
    await dormir(ESPERA_PRAZO_MS);

    // 3. confirmar: rádio dias úteis + valor
    const conf = await esperarPor(
      () => {
        const l = linhas()[idx - 1];
        if (!l) return null;
        if (tipoPrazoAtual(l) !== 'dias_uteis') return null;
        if (valorPrazoAtual(l).trim() !== String(PRAZO_DIAS)) return null;
        return { valor: valorPrazoAtual(l) };
      },
      2500,
      `linha ${idx}: confirmação do prazo`
    );

    if (!conf) {
      // Uma segunda tentativa: alguns casos só pegam no segundo blur.
      const l = linhas()[idx - 1];
      const hash2 = l && hashLinha(l);
      const i2 = l && ((hash2 && document.getElementById(hash2 + 'PrazoDiasUteis')) ||
        l.querySelector('input[id$="PrazoDiasUteis"]'));
      if (i2) { escreverValor(i2, PRAZO_DIAS); await dormir(600); }
      const l3 = linhas()[idx - 1];
      const ok3 = l3 && tipoPrazoAtual(l3) === 'dias_uteis' &&
        valorPrazoAtual(l3).trim() === String(PRAZO_DIAS);
      if (!ok3) {
        return {
          ok: false,
          motivo: `não confirmou (tipo=${l3 ? tipoPrazoAtual(l3) : '?'}, valor=${valorPrazoAtual(l3) || '?'})`,
        };
      }
    }

    return { ok: true, motivo: 'ok', valor: valorPrazoAtual(linhas()[idx - 1]) };
  }

  // ── Execução principal ──────────────────────────────────────────────────
  log('iniciando — prazo alvo:', PRAZO_DIAS, 'dias úteis');

  const total = linhas().length;
  if (!total) {
    err('Nenhuma linha de expediente encontrada (tbody.cdk-drop-list tr.cdk-drag).');
    return { erro: 'sem linhas' };
  }
  log(`encontradas ${total} linha(s) de expediente`);

  const resultado = [];

  for (let i = 1; i <= total; i++) {
    const tr = linhas()[i - 1];
    if (!tr) { warn(`Linha ${i}: não existe mais`); continue; }

    const parte = nomeParte(tr);
    const meioAntes = meioAtual(tr).trim();
    const prazoAntes = tipoPrazoAtual(tr);
    const valorAntes = valorPrazoAtual(tr);

    log(`── Linha ${i}/${total} — ${parte}`);
    log(`   antes: meio="${meioAntes}" prazo="${prazoAntes || '(?)'}" dias="${valorAntes || '(vazio)'}"`);

    // Já está em Correios: não toca no meio, mas garante o prazo.
    const jaCorreios = norm(meioAntes).includes('correio');

    if (!jaCorreios) {
      const okTroca = await trocarParaCorreios(i, tr);
      if (!okTroca) {
        err(`   ✗ FALHOU a troca para Correios — linha não será alterada no prazo`);
        resultado.push({ linha: i, parte, meioAntes, status: 'ERRO_TROCA' });
        continue; // NÃO segue para o prazo: sem Correios não faz sentido
      }
      log(`   ✓ meio → Correios`);
    } else {
      log(`   (já estava em Correios — só garante o prazo)`);
    }

    // Só agora, e antes de ir para a próxima linha:
    const rp = await restabelecerPrazo(i);
    if (rp.ok) {
      log(`   ✓ prazo → ${rp.valor || PRAZO_DIAS} dias úteis`);
      resultado.push({ linha: i, parte, meioAntes, status: 'OK', valorFinal: rp.valor });
    } else {
      err(`   ✗ prazo NÃO restabelecido: ${rp.motivo}`);
      resultado.push({ linha: i, parte, meioAntes, status: 'ERRO_PRAZO', motivo: rp.motivo });
    }
  }

  // ── Relatório final ─────────────────────────────────────────────────────
  console.log('%c' + '═'.repeat(70), 'color:#0a84ff');
  const ok = resultado.filter((r) => r.status === 'OK').length;
  const falhas = resultado.filter((r) => r.status !== 'OK');

  console.log(
    `%cRESULTADO: ${ok}/${resultado.length} ok`,
    `color:${falhas.length ? '#ff9f0a' : '#30d158'};font-weight:bold;font-size:13px`
  );

  if (falhas.length) {
    console.table(falhas.map((f) => ({
      Linha: f.linha, Parte: f.parte, 'Meio antes': f.meioAntes,
      Status: f.status, Motivo: f.motivo || '',
    })));
    warn('Linhas com problema NÃO foram confirmadas. Revise manualmente antes de Salvar.');
  } else {
    log('Todas as linhas em Correios com prazo de ' + PRAZO_DIAS + ' dias úteis. Confira na tela antes de Salvar.');
  }

  return resultado;
})();
