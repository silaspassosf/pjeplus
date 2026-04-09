## TRX Serializado

### Objetivo
Serializar a aplicação completa do `tr2.md` em fases ordenadas, para que cada passo seja aplicado sem ambiguidade, com compatibilidade preservada e sem perda funcional. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/58600029/a3a3702d-7b9b-4c0c-b333-b72a3922502b/tr2.md)

### Regra Central
Cada fase abaixo deve ser executada **integralmente** antes da próxima. Não resumir, não fundir fases, não reescrever a estrutura por conta própria, e não pular blocos temáticos. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/collection_92083c6e-fc4e-43c7-a629-54a34ec21a3e/d03f20fc-df01-4bf1-9178-e26e4b24202a/idx.md)

### Ordem de Aplicação

#### Fase 0 — Conferência inicial
- Confirmar o conteúdo atual de `tr.py`, a presença do import legado em `aud.py`, e o escopo real da refatoração. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/58600029/729f661b-fd38-4bae-a7de-f7cb7bcc84c7/tr.py)
- Validar que o objetivo é quebrar um módulo único e grande em partes temáticas menores, mantendo `triagem_peticao(driver) -> str`. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/58600029/a3a3702d-7b9b-4c0c-b333-b72a3922502b/tr2.md)
- Registrar duplicações existentes e blocos que precisam ser migrados sem alteração semântica. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/58600029/729f661b-fd38-4bae-a7de-f7cb7bcc84c7/tr.py)

#### Fase 1 — Fachada de compatibilidade
- Criar o pacote `triagem/` com exportação única em `__init__.py`. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/58600029/a3a3702d-7b9b-4c0c-b333-b72a3922502b/tr2.md)
- Manter `tr.py` como wrapper compatível que reexporta `triagem_peticao`. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/58600029/a3a3702d-7b9b-4c0c-b333-b72a3922502b/tr2.md)
- Não tocar em `aud.py` nesta etapa; a compatibilidade legada precisa continuar funcionando. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/58600029/f8ecf323-37bb-4c80-b8c3-9ac41641050d/aud.py)

#### Fase 2 — Base estável
- Extrair constantes, regexes, listas de termos, limites e `norm` para `triagem/constants.py`. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/58600029/a3a3702d-7b9b-4c0c-b333-b72a3922502b/tr2.md)
- Extrair utilitários puros e de formatação para `triagem/utils.py`. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/58600029/a3a3702d-7b9b-4c0c-b333-b72a3922502b/tr2.md)
- Garantir que nenhum helper genérico relevante permaneça preso ao módulo principal. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/58600029/a3a3702d-7b9b-4c0c-b333-b72a3922502b/tr2.md)

#### Fase 3 — Limpeza textual
- Isolar a remoção de artefatos PJe e o fingerprint de cabeçalho em `triagem/preprocess.py`. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/58600029/a3a3702d-7b9b-4c0c-b333-b72a3922502b/tr2.md)
- Preservar exatamente a semântica atual do strip de cabeçalho/rodapé. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/58600029/a3a3702d-7b9b-4c0c-b333-b72a3922502b/tr2.md)
- Manter o módulo de pré-processamento sem regras de negócio. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/58600029/a3a3702d-7b9b-4c0c-b333-b72a3922502b/tr2.md)

#### Fase 4 — Coleta e enriquecimento
- Mover toda a camada de API/PDF/OCR para `triagem/coleta.py`. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/58600029/a3a3702d-7b9b-4c0c-b333-b72a3922502b/tr2.md)
- Preservar reauth única em 401, timeout da timeline, extração de documentos e enriquecimento de `capadados`. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/58600029/a3a3702d-7b9b-4c0c-b333-b72a3922502b/tr2.md)
- Preservar também o ajuste de logging que reduz ruído operacional do parser de PDF. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/58600029/729f661b-fd38-4bae-a7de-f7cb7bcc84c7/tr.py)

#### Fase 5 — Regras de triagem
- Migrar as regras B1–B14 para `triagem/regras.py`. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/58600029/a3a3702d-7b9b-4c0c-b333-b72a3922502b/tr2.md)
- Consolidar a lógica de `checar_procuracao_e_identidade`, `checar_cep`, `checar_partes`, `checar_segredo`, `checar_reclamadas`, `checar_tutela`, `checar_digital`, `checar_pedidos_liquidados`, `checar_pessoa_fisica`, `checar_litispendencia`, `checar_responsabilidade`, `checar_endereco_reclamante`, `checar_rito`, `checar_art611b`. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/58600029/729f661b-fd38-4bae-a7de-f7cb7bcc84c7/tr.py)
- Eliminar duplicações reais de blocos concorrentes, não apenas distribuí-las em arquivos separados. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/58600029/729f661b-fd38-4bae-a7de-f7cb7bcc84c7/tr.py)

#### Fase 6 — Consolidação da saída
- Centralizar formatação final em utilitários únicos, preservando `[COMPETENCIA]`, `[Alertas]` e `[ITENS OK]`. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/58600029/a3a3702d-7b9b-4c0c-b333-b72a3922502b/tr2.md)
- Garantir limite final de 8000 caracteres. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/58600029/729f661b-fd38-4bae-a7de-f7cb7bcc84c7/tr.py)
- Manter a ordenação da saída e a normalização de rótulos e itens. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/58600029/a3a3702d-7b9b-4c0c-b333-b72a3922502b/tr2.md)

#### Fase 7 — Orquestrador principal
- Criar `triagem/service.py` com a função pública `triagem_peticao(driver) -> str`. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/58600029/a3a3702d-7b9b-4c0c-b333-b72a3922502b/tr2.md)
- Esse arquivo deve apenas orquestrar coleta, regras e saída, sem carregar lógica pesada adicional. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/58600029/a3a3702d-7b9b-4c0c-b333-b72a3922502b/tr2.md)
- Ao final da fase, `tr.py` deve continuar existindo apenas como fachada fina. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/58600029/a3a3702d-7b9b-4c0c-b333-b72a3922502b/tr2.md)

#### Fase 8 — Ajuste opcional de consumo
- Só depois da estabilização completa, trocar `aud.py` para importar de `triagem` diretamente, se essa migração for desejada. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/58600029/f8ecf323-37bb-4c80-b8c3-9ac41641050d/aud.py)
- Esse passo é opcional e não define a conclusão da refatoração, porque o wrapper em `tr.py` já garante o contrato legado. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/58600029/f8ecf323-37bb-4c80-b8c3-9ac41641050d/aud.py)

## Critérios de Validação
- `from tr import triagem_peticao` continua funcionando durante toda a transição. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/58600029/f8ecf323-37bb-4c80-b8c3-9ac41641050d/aud.py)
- `from triagem import triagem_peticao` também funciona após a fase de fachada. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/58600029/a3a3702d-7b9b-4c0c-b333-b72a3922502b/tr2.md)
- Cada módulo novo fica tematicamente coeso e, quando possível, abaixo de 600 linhas. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/58600029/a3a3702d-7b9b-4c0c-b333-b72a3922502b/tr2.md)
- Não pode haver duplicação funcional sobrevivente em múltiplos módulos. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/58600029/729f661b-fd38-4bae-a7de-f7cb7bcc84c7/tr.py)
- A semântica do fluxo principal, da coleta e da saída final permanece equivalente ao arquivo original. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/58600029/729f661b-fd38-4bae-a7de-f7cb7bcc84c7/tr.py)

## Progresso Atual

- [x] Fase 0 — Conferência inicial: escopo confirmado, `tr.py` tratado como legado.
- [x] Fase 1 — Fachada de compatibilidade: `triagem/__init__.py` existe e preserva o contrato público.
- [x] Fase 2 — Base estável: `triagem/constants.py`, `triagem/utils.py` implementados.
- [x] Fase 3 — Limpeza textual: `triagem/preprocess.py` implementado.
- [x] Fase 4 — Coleta e enriquecimento: `triagem/coleta.py` implementado.
- [x] Fase 5 — Regras de triagem: `triagem/regras.py` implementado.
- [x] Fase 6 — Consolidação da saída: `triagem/service.py` implementado e saída final formatada.
- [x] Fase 7 — Orquestrador principal: `triagem/service.py` expõe `triagem_peticao(driver) -> str` e orquestra coleta, regras e saída.
- [x] Fase 8 — Ajuste opcional de consumo: `aud.py` atualizado para `from triagem import triagem_peticao`.

> Nota: `tr.py` permanece como legado e não deve ser modificado nesta etapa. O novo núcleo de triagem é construído em `triagem/`.



