# FLUXOGRAMA DO FLUXO PRINCIPAL (2025-04-23)

```
1. LOGIN AUTOMÁTICO
   └── login_automatico(), verificar_login_ativo()

2. CONTROLE DE ABAS E NAVEGAÇÃO INTELIGENTE
   └── injetar_botoes_interface()

3. CAMINHO 1: PRAZOS VENCIDOS
   └── acessar_prazos_vencidos(), selecionar_processos_livres_e_aplicar_atividade()

4. CAMINHO 2: ANÁLISE DE PRAZO
   ├── processar_lista()
   ├── analisar_e_criar_gigs(), analisar_prazo_detalhe()
   └── minuta_apos_gigs()   (placeholder ao final do caminho)

5. CAMINHO 3: MANDADOS (DOCUMENTOS INTERNOS)
   ├── Navegação até documentos internos
   ├── Hipótese 1: Botão Argos (placeholder) na URL /peticao*
   └── Hipótese 2: Botão Intimação (placeholder) na mesma URL

6. FUNÇÕES AUXILIARES
   └── esperar_elemento(), safe_click(), ...

7. LIMPEZA TEMPORÁRIA
   └── limpar_temp_selenium()
```

---

Cada bloco do fluxo está documentado no código-fonte (pje.py) com comentários/separadores claros, facilitando manutenção e expansão.

- Placeholders para ações futuras (minuta após GIGS, botões Argos/Intimação) já estão definidos.
- Funções auxiliares agrupadas ao final para futura modularização.
- Backup persistente salvo em Basefluxo.py.

> Atualize este fluxograma sempre que houver mudança estrutural relevante no fluxo principal.

---

Aqui está um resumo detalhado do nosso chat para você salvar no projeto e transferir para qualquer computador:

HISTÓRICO E APRENDIZADOS DO PROJETO PjePlus (Cascade)
1. Objetivo do Projeto
Automatizar tarefas no sistema PJe TRT2 usando Selenium, mantendo a sessão ativa via perfil do Firefox, otimizando filtros e manipulação de processos.

2. Principais Decisões e Aprendizados
Selenium + Firefox Profile
Utilização de perfil dedicado do Firefox para automação, evitando conflitos com perfil pessoal.
Login automático implementado para contornar restrições do Selenium com senhas salvas.
Recomenda-se sempre fechar o Firefox antes de rodar o Selenium para evitar erros de perfil em uso.
Seletores Dinâmicos e Robustez
Uso de bookmarklet para extrair seletores CSS/XPath reais do DOM do PJe.
Preferência por selecionar elementos pelo texto visível (ex: “Análises”, “Liquidação”, “Execução”) para maior robustez frente a mudanças no DOM.
Funções utilitárias para esperar e clicar com segurança (wait, safe_click).
Fluxo Automatizado
Login automático na tela do PJe TRT2.
Navegação até painel global e clique em “Análises”.
Aplicação do filtro de fase processual para “Liquidação” e “Execução” (busca por texto).
Definição de 100 itens por página.
Seleção automática de processos “livres” (sem prazo, comentário, campo preenchido ou lupa).
Aplicação em lote do chip “Analisado” nos processos selecionados.
Git e Organização do Projeto
Projeto versionado no GitHub para facilitar backup e colaboração.
Instruções para mover, renomear e clonar o projeto em outros computadores.
Recomenda-se criar um arquivo .gitignore para evitar subir arquivos desnecessários.
Dicas e Troubleshooting
Bookmarklet para extrair seletores e DOM: usar sempre no Firefox manual, nunca na janela do Selenium.
Seletor de perfil do Firefox deve ser exclusivo para automação.
Para transferir o histórico do chat, salve este arquivo no repositório.
3. Comandos Git Úteis
sh
CopyInsert
# Inicializar repositório
git init

# Adicionar todos os arquivos
git add .

# Commitar mudanças
git commit -m "Mensagem"

# Conectar ao GitHub
git remote add origin https://github.com/seuusuario/seurepo.git

# Enviar para o GitHub
git push -u origin main

# Clonar em outro PC
git clone https://github.com/seuusuario/seurepo.git
4. Recomendações Finais
Sempre documente aprendizados e decisões importantes neste arquivo.
Atualize o README.md com instruções de uso e configuração.
Nunca suba arquivos sensíveis (senhas, certificados).
Use variáveis de ambiente ou arquivos .env para credenciais.
Este arquivo foi gerado com apoio do assistente Cascade e reflete todo o aprendizado, decisões técnicas e dicas do projeto até o momento.

Salve este arquivo no seu projeto (ex: HISTORICO_CHAT_CASCADE.md) e ele estará sempre disponível em qualquer computador via GitHub!


---

## Funções Desenvolvidas para Automação PJe TRT2 (Sessão Cascade)

### Função Geral de GIGS (Criação e Fluxo Silvia - Argos)
- **Descrição:** Automatiza a criação de GIGS Silvia - Argos e executa o fluxo completo de movimentação do processo.
- **Passos:**
  1. Abrir tarefa do processo (detecta e troca para nova aba automaticamente).
  2. Clicar em "Conclusão ao magistrado" (com busca robusta por ícone, aria-label e logs detalhados).
  3. Clicar em "BACEN / BNDT / Sigilo Fiscal / Indisponibilidade de Bens" (busca por texto visível).
  4. Após a URL mudar para `/minutar`, realiza o ajuste de minuta:
      - Busca campo `#inputFiltro[aria-label]`, clica, limpa e digita `xsbacen`.
      - Seleciona o modelo destacado `.nodo-filtrado > span:nth-child(1)`.
      - Clica no botão Inserir (busca por texto/aria "inserir").
- **Destaques:**
  - Toda movimentação ocorre na aba correta, trocando contexto conforme necessário.
  - Logs detalhados para cada etapa e alertas para URLs inesperadas.
  - Não há mais referências a tipos de GIGS antigos (ex: Pesq, Homol, Pec, etc).

### Função Geral de Criação de GIGS (detalhamento dos campos)
- **Descrição:** Responsável por criar uma nova GIGS no PJe, preenchendo corretamente os campos obrigatórios e opcionais.
- **Campos e Cuidados:**
  - **Dias Úteis:**
    - O campo de dias úteis é preenchido sempre com valor numérico (ex: `1`).
    - O script garante que o campo esteja limpo antes de digitar, evitando concatenação ou erro de digitação.
    - Caso o campo não esteja habilitado ou visível, o log alerta e interrompe o fluxo para evitar inconsistências.
  - **Observação:**
    - O campo de observação é preenchido conforme o tipo de GIGS (ex: `Silvia - Argos`).
    - O valor é passado como parâmetro para garantir flexibilidade e reuso da função.
    - O script verifica se o campo está presente e editável antes de preencher.
    - Se o campo não for encontrado, emite alerta detalhado para depuração.
- **Fluxo Resumido:**
  1. Clica no botão "Nova atividade" para iniciar a criação da GIGS.
  2. Preenche o campo de dias úteis.
  3. Preenche o campo de observação.
  4. Clica em "Salvar" e confirma a criação.
- **Robustez:**
  - Todos os campos são buscados por seletores robustos e logs detalhados são emitidos em caso de falha.
  - O fluxo só prossegue se todos os campos forem preenchidos com sucesso.
  - Logs informam cada etapa, facilitando o acompanhamento e a depuração.

### Função `click_button_conclusao_ao_magistrado`
- **Descrição:** Clica no botão de conclusão ao magistrado usando, em ordem:
  1. Ícone `.fa-clipboard-check` (subindo no DOM até achar `<button>`).
  2. `<button>` com `aria-label="Conclusão ao magistrado"`.
- **Logs:** Lista todos os candidatos encontrados, visibilidade, classes e atributos relevantes se não encontrar o botão.
- **Robustez:** Evita falhas comuns em DOM dinâmico do PJe.

### Função `click_element_by_visible_text`
- **Descrição:** Clica em elementos (ex: botão) pelo texto visível, com fallback para diferentes tags.
- **Usos:** Utilizada para BACEN/BNDT e outros botões críticos.
- **Logs:** Detalha candidatos e falhas, facilitando ajuste de seletores.

### Fluxo de Movimentação do Processo (Mudança de Aba)
- **Descrição:** Sempre que o fluxo exige interação após clicar em tarefa do processo:
  - Detecta as abas abertas antes e depois do clique.
  - Troca automaticamente para a nova aba usando `driver.switch_to.window`.
  - Garante que toda automação subsequente (conclusão, minuta, etc) ocorra no contexto correto.
- **Logs:** Mostra troca de aba e URL ativa.

### Função `ajuste_minuta_silvia_argos`
- **Descrição:** Realiza o ajuste de minuta específico para Silvia - Argos (modelo xsbacen).
- **Passos:**
  1. Seleciona campo de busca do modelo e digita `xsbacen`.
  2. Seleciona o modelo destacado.
  3. Clica no botão Inserir.
- **Observação:** Executada apenas após a URL `/minutar` ser carregada.

---

#### Seletores Gerais Utilizados nas Funções Validadas
- **Botão de tarefa do processo:** `span.texto-tarefa-processo` (subida via `../../..` para obter o `<button>` real)
- **Conclusão ao magistrado:**
  - Ícone: `.fa-clipboard-check` (busca ascendente até `<button>`)
  - Botão: `button[aria-label="Conclusão ao magistrado"]`
- **Botão BACEN / BNDT / Sigilo Fiscal / Indisponibilidade de Bens:** Busca por texto visível no elemento `<button>`
- **Campo de dias úteis:** (Exemplo) `input[formcontrolname="diasUteis"]` (ajustar conforme DOM real)
- **Campo de observação:** (Exemplo) `textarea[formcontrolname="observacao"]` (ajustar conforme DOM real)
- **Botão Nova atividade:** Busca por texto visível "Nova atividade" ou seletor específico do botão, se disponível
- **Campo de busca de modelo (minuta):** `#inputFiltro[aria-label]`
- **Modelo destacado:** `.nodo-filtrado > span:nth-child(1)`
- **Botão Inserir na minuta:** `button.mat-primary > span` (valida texto/aria "inserir")

> **Observação:** Os seletores são validados e testados em cada função. Se não encontrados, logs detalhados são emitidos para facilitar ajuste futuro. Recomenda-se sempre revisar os seletores em caso de mudança no DOM do PJe.

---

## [2025-04-22] Observação para ajuste futuro do fluxo Mandados Argos

- É necessário receber a função correta para processar a timeline dos documentos na função Mandados Argos.
- Assim que o usuário fornecer a função/estrutura exata da timeline, ajustar o fluxo para garantir o tratamento correto dos documentos.
- Registrar e revisar este ponto na próxima sessão.

---

## [2025-04-25 02:24] Mudança de organização do projeto

- A estrutura do projeto foi reorganizada para separar os fluxos de automação de Mandados e de Prazos em scripts distintos.
- Criados arquivos `mandados_main.py` (contendo Mandado 1 e Mandado 2, pois ambos partem da mesma lista) e `prazos_main.py`.
- Cada script inclui todas as funções auxiliares e o fluxo de processamento de lista, para facilitar manutenção e futura execução simultânea em navegadores/headless diferentes.
- O arquivo principal antigo (`pje.py`) permanece como referência, mas os novos desenvolvimentos e ajustes serão feitos nos scripts separados.
- A separação visa facilitar o aperfeiçoamento individual dos fluxos e garantir maior robustez e escalabilidade.

---

**Notas Gerais:**
- Todos os fluxos e funções possuem logs detalhados para facilitar depuração.
- O fluxo Silvia - Argos é o único automatizado integralmente neste módulo, sem referências a tipos de GIGS antigos.
- Recomenda-se sempre atualizar este arquivo ao evoluir funções críticas de automação.

FLUXO PRINCIPAL
1. Login automático
2. Controle de abas e navegação inteligente
3. Caminho 1: Prazos vencidos
4. Caminho 2: Análise de Prazo
5. Inclui análise, criação de GIGS, e ao final: “minuta após GIGS” (placeholder)
6. Caminho 3: Mandados (até navegação para documentos internos)
7. Hipótese 1: Botão Argos (placeholder) na URL correta de petição
  8. Hipótese 2: Botão Intimação (placeholder) na mesma URL
9. Funções auxiliares
10. Limpeza temporária
11. Vou ajustar os comentários/separadores e inserir os placeholders para os botões Argos e Intimação conforme solicitado, sem alterar lógica.