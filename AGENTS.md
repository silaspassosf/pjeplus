# Regras de fluxo de trabalho (PjePlus)

Objetivo: entregar edições reais rápido, sem loop de exploração.

## Editar cedo
1. Faça no máximo 2 leituras e 2 buscas antes da **primeira edição**. Se já tem contexto
   suficiente para o primeiro passo, edite agora.
2. Não releia arquivo que você acabou de ler e não mudou.
3. `search_files` só para localizar; ao achar o alvo, leia o trecho e edite — não varra o repo.
4. Cada turno deve terminar com algo concreto: arquivo editado, comando rodado ou pergunta
   objetiva. Turno só com leitura é turno perdido.
5. Antes de editar, diga em uma linha o que vai mudar e onde. Sem plano longo.

## Não repetir
- Se uma ferramenta falhar 2x com o mesmo erro, mude a abordagem (outro caminho, outro comando).
- Se a mesma leitura se repetir, pare e edite com o que tem.

## Verificação
- **Não criar arquivo `tests/test_*.py` novo** por alteração (só quando o usuário pedir explicitamente).
- **Checagem mínima por tipo de arquivo:**
  - Python: `py -m py_compile <arquivo>` + `py tools/check_pw.py` (quando mexer em automação) + rodar apenas teste já existente do mesmo módulo, se houver.
  - JavaScript (`Script/`): apenas `node --check <arquivo>`.
- **Ambiente de teste real (Firefox Developer Edition headless + `+PJe` + `Tampermonkey`):** para testes mais complexos, validação de comportamento/UI/`Script/` e leitura de HTML/DOM real do PJe, usar sempre o driver de teste via `py tools/cdp_lab.py` (WebDriver BiDi na porta `9222` com login automático por CPF/senha + TOTP do Windows Credential Manager) em vez de escrever mocks extensos.
  - **Checagem inicial:** rodar `py tools/cdp_lab.py status`; se estiver inativo na porta `9222`, subir com `py tools/cdp_lab.py abrir --headless` (ou pedir ao usuário para executar `PJePlus_CDP_Lab.bat` no Desktop) antes de consultar `goto` / `dom --html` / `eval` / `inject`.
- Só considere concluído quando o efeito estiver comprovado na saída do comando.

## Pasta `Script/` (Tampermonkey — publicação obrigatória)
- Sempre que alterar qualquer arquivo dentro de `Script/`:
  1. Validar com `node --check <arquivo>`.
  2. Commitar e dar `git push` dos arquivos editados em `Script/` (para publicar no GitHub e gerar o novo SHA quando o módulo estiver pinado por commit).
  3. Atualizar o orquestrador respectivo (ex.: `Script/pjetools.user.js`): fazer bump do `@version` (e do log de versão), subir o `?v=` do `@require` do módulo alterado e, se o `@require` estiver preso a um SHA de commit, trocar pelo novo SHA (12 caracteres).
  4. Validar o orquestrador com `node --check`, commitar e dar `git push` do orquestrador também.
  - Não considerar a alteração em `Script/` concluída sem o bump + commit + push do módulo e do orquestrador.

## Estilo
- Português do Brasil, direto, sem preâmbulo.
- Nada de "vou analisar" sem ação na sequência.
