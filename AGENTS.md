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
- Para validar DOM/comportamento real no PJe sob demanda, usar o utilitário CDP (`py tools/cdp_lab.py`) conectado ao Chrome já logado em vez de escrever mocks extensos.
- **Checagem inicial do ambiente CDP:** ao iniciar trabalho que envolva DOM, seletores, UI do PJe ou `Script/`, rodar `py tools/cdp_lab.py status`; se o CDP estiver inativo na porta 9222, pedir ao usuário para executar `PJePlus_CDP_Lab.bat` no Desktop (ou `py tools/cdp_lab.py abrir`) e informar o OTP antes de tentar validar no PJe real.
- Só considere concluído quando o efeito estiver comprovado na saída do comando.

## Estilo
- Português do Brasil, direto, sem preâmbulo.
- Nada de "vou analisar" sem ação na sequência.
