Leia e siga todas as instruções em ./idx.md para contexto arquitetural completo do projeto pjeplus.

Regras always-on deste workspace estão em .agents/rules/ e são carregadas automaticamente — não precisam ser relidas manualmente.

Agentes especializados disponíveis em .agents/agents/ (invocar pelo nome quando a tarefa se encaixar no escopo dele):
- pjeplus-analyst — análise e geração de patches (bugs, features, refatoração cirúrgica)
- pjeplus-debug — diagnóstico cross-module leve, produz diagnóstico + correção pontual sem editar
- pjeplus-surgical — aplicação de patch mínimo a partir de bloco pjeplus:apply já pronto
- pjeplus-script — especialista exclusivo na pasta Script/ (Tampermonkey, console, bookmarklets)

Antes de qualquer busca exploratória (grep/glob) fora do escopo já mapeado, consulte .agents/rules/idx-core.md (Quick Reference + Árvore de Decisão). Se a tarefa não estiver coberta lá, leia ./idx.md para o índice completo (palavras-chave, cadeias de chamada, catálogo de atos/, API obrigatória).
