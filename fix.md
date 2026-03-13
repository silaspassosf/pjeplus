O que falta integrar / verificar
=================================

- Restaurar checkboxes e disparar `change` durante o restore do draft
  - Ao restaurar o rascunho (`hcalc-overlay-draft.js -> restore`) deve-se setar o estado `checked` nos checkboxes de responsabilidade e disparar `el.dispatchEvent(new Event('change', { bubbles: true }))` para garantir que os blocos visíveis/ocultos sejam atualizados.
  - IDs/checkboxes a considerar: `resp-subsidiarias`, `resp-solidarias`, `resp-sub-integral`, `resp-sub-diversos`, `resp-sol-integral`, `resp-sol-diversos`, `chk-nao-ha-subs-int`, `chk-nao-ha-sol-int`, `resp-rec-judicial-unica`.

- Garantir que o comportamento padrão esteja consistente
  - A primeira reclamada deve já vir marcada como principal (implementado).
  - Por padrão, quando existir apenas "devedora subsidiária", o checkbox `resp-subsidiarias` deve estar marcado e `resp-sub-integral` marcado; os campos de período diverso devem permanecer ocultos até o usuário marcar `resp-sub-diversos`.
  - Se um checkbox estiver desmarcado, NENHUMA entrada relacionada deve estar visível nem persistida no draft.

- Persistência/restore dos flags auxiliares
  - As flags `chk-nao-ha-subs-int` e `chk-nao-ha-sol-int` devem ser salvas e restauradas com o draft e, ao restaurar, devem esconder/exibir corretamente os containers correspondentes.

- Sincronizar seleção/visibilidade após restore
  - Depois de restaurar dados dinâmicos (principais, subsidiárias, periodos diversos), forçar `updateVisibility()` e `aplicarEstiloRecuperacaoJudicial()` para garantir que o DOM reflita o estado salvo.

- Testes manuais recomendados
  1. Abrir overlay com PASSIVO contendo 1 reclamada: verificar a primeira vem marcada como principal; outros blocos invisíveis.
  2. Marcar `resp-subsidiarias` + `resp-sub-integral` -> verificar container de Subs. Integral visível e persistido após fechar/abrir overlay.
  3. Marcar `resp-sub-diversos`, adicionar reclamadas a um período, salvar draft; fechar e restaurar -> verificar itens reaparecem e containers aparecem somente se checkboxes estiverem marcados.
  4. Desmarcar `resp-subsidiarias` e salvar -> abrir novamente e garantir que não há valores escondidos (containers vazios).

- Observações de implementação já feitas
  - Geração de ID virtual para planilhas sem id (`SemID-xxxxx`) implementada para evitar agrupamentos indevidos.
  - `queueOverlayDraftSave()` já é chamado nos handlers de add/remove das reclamadas por período.

- Próximos passos sugeridos
  - Implementar dispatch `change` no restore para os checkboxes listados acima (pequena alteração em `hcalc-overlay-draft.js`).
  - Adicionar testes manuais / automatizados de smoke para as combinações principais (principal única, subsidiária integral, período diverso).

Data: 2026-03-13
Gerado por: assistente (fix list)
