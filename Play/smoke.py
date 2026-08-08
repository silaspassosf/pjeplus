# -*- coding: utf-8 -*-
"""Smoke test real do backend Playwright — exercita a superficie WebDriver.

Roda offline (fixture HTML injetada, sem rede). Uso:

    py play/smoke.py            # so a camada de compatibilidade
    py play/smoke.py --projeto  # + carga real de Fix/ e dos modulos de negocio
"""
import os
import sys
import traceback

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
for caminho in (AQUI, RAIZ):
    if caminho not in sys.path:
        sys.path.insert(0, caminho)

FIXTURE = """
<!doctype html><html><body>
  <h1 id="titulo">PJe Fixture</h1>
  <button id="btn" onclick="document.getElementById('saida').textContent='clicado'">Ir</button>
  <span id="saida"></span>
  <input id="campo" type="text" value="inicial">
  <div class="linha" data-id="1">alpha</div>
  <div class="linha" data-id="2">beta</div>
  <div id="oculto" style="display:none">invisivel</div>
  <select id="sel"><option value="a">Um</option><option value="b">Dois</option></select>
  <a id="link" href="https://exemplo.test/destino">abrir</a>
  <button id="lento" style="display:none">tardio</button>
  <script>setTimeout(() => document.getElementById('lento').style.display='block', 400);</script>
</body></html>
"""

FIXTURE_MATERIAL = """
<!doctype html><html><head><style>
  mat-select { display:block; width:240px; height:28px; border:1px solid #999; }
  mat-option { display:block; height:24px; cursor:pointer; }
  mat-row    { display:block; height:20px; }
  .cdk-overlay-pane { position:absolute; top:60px; left:0; width:240px;
                      background:#fff; z-index:1000; }
</style></head><body>
  <mat-select id="destinos"><span class="valor"></span></mat-select>
  <mat-spinner id="spin"></mat-spinner>
  <input id="dt" matdatepicker>
  <mat-checkbox id="chk"><input type="checkbox"></mat-checkbox>
  <mat-table><mat-row>proc 111</mat-row><mat-row>proc 222</mat-row></mat-table>
  <button id="abrir">nova aba</button>
  <div class="ck-editor__editable"></div>
<script>
  // mat-select com overlay CDK, como o Angular Material faz
  document.getElementById('destinos').onclick = () => {
    const pane = document.createElement('div');
    pane.className = 'cdk-overlay-pane';
    ['Analise','Execucao','Execucao Fiscal'].forEach(t => {
      const o = document.createElement('mat-option');
      o.textContent = t;
      o.onclick = () => {
        document.querySelector('#destinos .valor').textContent = t;
        pane.remove();
      };
      pane.appendChild(o);
    });
    setTimeout(() => document.body.appendChild(pane), 120);  // R2: render atrasado
  };
  setTimeout(() => document.getElementById('spin').style.display = 'none', 300);
  document.getElementById('abrir').onclick = () => window.open('about:blank');
  // CKEditor 5: instância pendurada no elemento
  const ed = document.querySelector('.ck-editor__editable');
  let dados = '';
  ed.ckeditorInstance = { setData: h => { dados = h; }, getData: () => dados };
</script>
</body></html>
"""

resultados = []


def montar(page, html):
    """Carrega a fixture num documento novo.

    `set_content` repetido no mesmo documento vira innerHTML, e <script>
    inserido por innerHTML não executa (spec do HTML). Navegar antes garante
    que os handlers da fixture existam em toda chamada.
    """
    page.goto("about:blank")
    page.set_content(html)


def checar(nome, fn):
    try:
        fn()
        resultados.append((True, nome, ""))
    except Exception as e:
        detalhe = f"{type(e).__name__}: {e}"
        resultados.append((False, nome, detalhe))
        if os.environ.get("PJEPLAY_TRACE"):
            traceback.print_exc()


def afirmar(condicao, msg="condicao falsa"):
    if not condicao:
        raise AssertionError(msg)


def testar_compatibilidade(driver):
    from selenium.common.exceptions import NoSuchElementException, TimeoutException
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.ui import Select, WebDriverWait

    montar(driver.page, FIXTURE)

    checar("find_element por CSS", lambda: afirmar(
        driver.find_element(By.CSS_SELECTOR, "#titulo").text == "PJe Fixture"))

    checar("find_element por XPATH", lambda: afirmar(
        driver.find_element(By.XPATH, "//h1[@id='titulo']").text == "PJe Fixture"))

    checar("find_element por ID", lambda: afirmar(
        driver.find_element(By.ID, "titulo").tag_name == "h1"))

    checar("find_elements retorna lista", lambda: afirmar(
        len(driver.find_elements(By.CSS_SELECTOR, ".linha")) == 2))

    checar("find_elements vazio nao explode", lambda: afirmar(
        driver.find_elements(By.CSS_SELECTOR, ".inexistente") == []))

    def _ausente():
        try:
            driver.find_element(By.CSS_SELECTOR, "#nao-existe")
        except NoSuchElementException:
            return
        raise AssertionError("deveria ter levantado NoSuchElementException")
    checar("NoSuchElementException", _ausente)

    checar("get_attribute (atributo)", lambda: afirmar(
        driver.find_element(By.CSS_SELECTOR, ".linha").get_attribute("data-id") == "1"))

    checar("get_attribute (propriedade value)", lambda: afirmar(
        driver.find_element(By.ID, "campo").get_attribute("value") == "inicial"))

    checar("is_displayed falso em oculto", lambda: afirmar(
        not driver.find_element(By.ID, "oculto").is_displayed()))

    checar("click dispara handler", lambda: (
        driver.find_element(By.ID, "btn").click(),
        afirmar(driver.find_element(By.ID, "saida").text == "clicado"),
    ))

    def _digitar():
        campo = driver.find_element(By.ID, "campo")
        campo.clear()
        campo.send_keys("teste" + Keys.TAB)
        afirmar(campo.get_attribute("value") == "teste",
                f"valor={campo.get_attribute('value')!r}")
    checar("clear + send_keys + Keys.TAB", _digitar)

    checar("execute_script com argumentos", lambda: afirmar(
        driver.execute_script("return arguments[0] + arguments[1];", 20, 22) == 42))

    checar("execute_script recebe elemento", lambda: afirmar(
        driver.execute_script(
            "return arguments[0].id;", driver.find_element(By.ID, "titulo")) == "titulo"))

    checar("execute_script devolve elemento", lambda: afirmar(
        driver.execute_script("return document.getElementById('titulo');")
        .get_attribute("id") == "titulo"))

    checar("execute_async_script", lambda: afirmar(
        driver.execute_async_script(
            "const cb = arguments[arguments.length-1];"
            "setTimeout(() => cb(arguments[0] * 2), 50);", 21) == 42))

    checar("WebDriverWait + EC.presence", lambda: afirmar(
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#titulo"))) is not None))

    checar("WebDriverWait + EC.visibility em elemento tardio", lambda: afirmar(
        WebDriverWait(driver, 5).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "#lento"))) is not None))

    checar("EC.invisibility em oculto", lambda: afirmar(
        WebDriverWait(driver, 3).until(
            EC.invisibility_of_element_located((By.CSS_SELECTOR, "#oculto")))))

    def _timeout():
        try:
            WebDriverWait(driver, 0.4).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "#jamais")))
        except TimeoutException:
            return
        raise AssertionError("deveria ter levantado TimeoutException")
    checar("TimeoutException do WebDriverWait", _timeout)

    def _select():
        sel = Select(driver.find_element(By.ID, "sel"))
        sel.select_by_visible_text("Dois")
        afirmar(sel.first_selected_option.get_attribute("value") == "b")
    checar("Select por texto visivel", _select)

    checar("current_url acessivel", lambda: afirmar(
        isinstance(driver.current_url, str)))

    checar("page_source contem fixture", lambda: afirmar(
        "PJe Fixture" in driver.page_source))

    def _janelas():
        originais = driver.window_handles
        afirmar(len(originais) == 1, f"handles={originais}")
        driver.switch_to.new_window("tab")
        afirmar(len(driver.window_handles) == 2)
        driver.close()
        driver.switch_to.window(originais[0])
        afirmar(len(driver.window_handles) == 1)
    checar("window_handles + switch_to + close", _janelas)

    def _cookies():
        driver.context.add_cookies([
            {"name": "sessao", "value": "abc", "url": "https://exemplo.test"}])
        afirmar(any(c["name"] == "sessao" for c in driver.get_cookies()))
    checar("get_cookies no formato Selenium", _cookies)

    def _alerta_automatico():
        driver.execute_script("alert('auto'); document.title = 'seguiu';")
        afirmar(driver.title == "seguiu", "dialogo travou a pagina")
        afirmar(driver.ultimo_dialogo == "auto")
    checar("alert auto-aceito nao trava a pagina", _alerta_automatico)

    def _alerta_manual():
        driver.auto_dialogo = None
        try:
            driver.execute_script("setTimeout(() => alert('oi'), 10);")
            WebDriverWait(driver, 3).until(EC.alert_is_present())
            alerta = driver.switch_to.alert
            afirmar(alerta.text == "oi")
            alerta.accept()
        finally:
            driver.auto_dialogo = "accept"
    checar("alert manual via switch_to", _alerta_manual)

    checar("implicitly_wait aceito", lambda: driver.implicitly_wait(5))


def testar_nativo(driver):
    from pjeplay import nativo

    montar(driver.page, FIXTURE)

    checar("nativo: aguardar_renderizacao_nativa (aparecer)", lambda: afirmar(
        nativo.aguardar_renderizacao_nativa(driver, "#titulo", timeout=3)))

    checar("nativo: aguardar_renderizacao_nativa (tardio)", lambda: afirmar(
        nativo.aguardar_renderizacao_nativa(driver, "#lento", timeout=3)))

    checar("nativo: aguardar_renderizacao_nativa (sumir)", lambda: afirmar(
        nativo.aguardar_renderizacao_nativa(driver, "#oculto", modo="sumir", timeout=3)))

    checar("nativo: modo habilitado", lambda: afirmar(
        nativo.aguardar_renderizacao_nativa(driver, "#btn", modo="habilitado", timeout=3)))

    checar("nativo: timeout devolve False", lambda: afirmar(
        not nativo.aguardar_renderizacao_nativa(driver, "#jamais", timeout=0.4)))

    checar("nativo: esperar_elemento", lambda: afirmar(
        nativo.esperar_elemento(driver, "#titulo", timeout=3) is not None))

    checar("nativo: esperar_elemento com texto", lambda: afirmar(
        nativo.esperar_elemento(driver, ".linha", texto="beta", timeout=3) is not None))

    checar("nativo: aguardar_e_clicar", lambda: (
        afirmar(nativo.aguardar_e_clicar(driver, "#btn", timeout=3)),
        afirmar(driver.find_element("css selector", "#saida").text == "clicado"),
    ))

    checar("nativo: aguardar_e_clicar inexistente -> False", lambda: afirmar(
        not nativo.aguardar_e_clicar(driver, "#jamais", timeout=0.4)))

    checar("nativo: preencher_campo", lambda: (
        afirmar(nativo.preencher_campo(driver, "#campo", "PJe", log=True)),
        afirmar(driver.find_element("css selector", "#campo").get_attribute("value") == "PJe"),
    ))

    checar("nativo: preencher_multiplos_campos", lambda: afirmar(
        nativo.preencher_multiplos_campos(driver, {"#campo": "X"}) == {"#campo": True}))

    checar("nativo: selecionar_opcao em <select>", lambda: afirmar(
        nativo.selecionar_opcao(driver, "#sel", "Dois", timeout=3)))

    checar("nativo: is_headless_mode", lambda: afirmar(
        nativo.is_headless_mode(driver) is True))


def testar_vocabulario(driver):
    """E1 — primitivas PJe nativas contra uma fixture Angular Material."""
    from pjeplay import pje

    page = driver.page
    montar(page, FIXTURE_MATERIAL)

    checar("pje: aguardar_angular sem testabilities (R4)", lambda: afirmar(
        pje.aguardar_angular(page, timeout=3)))

    checar("pje: esperar_spinner", lambda: afirmar(
        pje.esperar_spinner(page, timeout=3)))

    # R2: as mat-option só entram no DOM 120ms depois do clique
    checar("pje: mat_select com overlay CDK atrasado (R2)", lambda: (
        afirmar(pje.mat_select(page, "#destinos", "Analise", timeout=3)),
        afirmar(page.locator("#destinos .valor").inner_text() == "Analise"),
    ))

    def _exato():
        montar(page, FIXTURE_MATERIAL)
        # "Execucao" é prefixo de "Execucao Fiscal": exato tem que pegar o certo
        afirmar(pje.mat_select(page, "#destinos", "Execucao", exato=True, timeout=3))
        afirmar(page.locator("#destinos .valor").inner_text() == "Execucao")
    checar("pje: mat_select exato nao pega o prefixo", _exato)

    checar("pje: mat_checkbox marca", lambda: (
        afirmar(pje.mat_checkbox(page, "#chk", marcar=True, timeout=3)),
        afirmar(page.locator("#chk input").is_checked()),
    ))

    checar("pje: mat_checkbox nao faz toggle indevido", lambda: (
        afirmar(pje.mat_checkbox(page, "#chk", marcar=True, timeout=3)),
        afirmar(page.locator("#chk input").is_checked()),
    ))

    checar("pje: mat_data preenche e fecha", lambda: (
        afirmar(pje.mat_data(page, "#dt", "15/01/2025", timeout=3)),
        afirmar(page.locator("#dt").input_value() == "15/01/2025"),
    ))

    checar("pje: linha_tabela filtra", lambda: afirmar(
        pje.linha_tabela(page, "222").count() == 1))

    checar("pje: esperar_tabela", lambda: afirmar(
        pje.esperar_tabela(page, timeout=3)))

    checar("pje: ckeditor_versao detecta ck5 (R3)", lambda: afirmar(
        pje.ckeditor_versao(page, timeout=3) == "ck5"))

    checar("pje: ckeditor set/get", lambda: (
        afirmar(pje.ckeditor_definir(page, "<p>minuta</p>", timeout=3)),
        afirmar(pje.ckeditor_obter(page, timeout=3) == "<p>minuta</p>"),
    ))

    def _nova_aba():
        antes = len(page.context.pages)
        nova = pje.abrir_em_nova_aba(
            page, lambda: page.locator("#abrir").click(), timeout=5)
        afirmar(nova is not None and len(page.context.pages) == antes + 1)
        nova.close()
    checar("pje: abrir_em_nova_aba (expect_page, sem race)", _nova_aba)

    def _fechar_extras():
        page.context.new_page()
        page.context.new_page()
        pje.fechar_abas_extras(page, manter=page)
        afirmar(len(page.context.pages) == 1, f"sobraram {len(page.context.pages)}")
    checar("pje: fechar_abas_extras", _fechar_extras)

    checar("pje: sessao_expirada falso na fixture", lambda: afirmar(
        not pje.sessao_expirada(page)))


def testar_medicao():
    """E0 — a instrumentação separa tempo morto de tempo de motor."""
    import time as _t

    from pjeplay import medicao

    def _sessao():
        with medicao.sessao("teste", backend="fake", helpers=False) as m:
            with m.etapa("passo lento"):
                _t.sleep(0.05)
            with m.etapa("passo rapido"):
                pass
        r = m.relatorio()
        afirmar(r["qtd_sleeps"] == 1, f"sleeps={r['qtd_sleeps']}")
        afirmar(abs(r["tempo_morto"] - 0.05) < 0.001, f"morto={r['tempo_morto']}")
        afirmar(len(r["etapas"]) == 2)
        afirmar(_t.sleep.__name__ != "sleep_medido", "time.sleep nao foi restaurado")
    checar("medicao: contabiliza sleeps e restaura time.sleep", _sessao)

    def _helpers():
        import Fix.core as core
        original = core.esperar_elemento
        with medicao.sessao("h", backend="fake", sleeps=False) as m:
            afirmar(core.esperar_elemento is not original, "helper nao envolvido")
            core.esperar_elemento(None, "#x", timeout=0.01)
        afirmar(core.esperar_elemento is original, "helper nao restaurado")
        r = m.relatorio()
        afirmar(r["chamadas_helper"] == 1, f"chamadas={r['chamadas_helper']}")
    checar("medicao: envolve e restaura helpers de Fix", _helpers)

    def _atribuicao():
        m = medicao.Medicao("x", "fake")
        m.tempo_morto = 10.0
        m._contar("Fix.core.esperar_elemento", 5.0, True)
        r = m.relatorio()
        afirmar(r["tempo_helper"] == 5.0 and r["tempo_morto"] == 10.0)
    checar("medicao: separa tempo_helper de tempo_morto", _atribuicao)


def testar_espera(driver):
    """A troca dos sleeps: nunca mais lenta que o sleep, bem mais rápida quando dá."""
    import time as _t

    from Fix import espera

    montar(driver.page, FIXTURE_MATERIAL)

    def _rapido():
        driver.page.wait_for_selector("#spin", state="hidden")  # já assentado
        t0 = _t.perf_counter()
        ok = espera.assentar(driver, 2)
        gasto = _t.perf_counter() - t0
        afirmar(ok, "assentar devolveu False com a tela parada")
        afirmar(gasto < 0.8, f"assentar gastou {gasto:.2f}s onde o sleep gastaria 2s")
    checar("espera: assentar retorna cedo com a tela parada", _rapido)

    def _nao_antecipa():
        # Spinner aparece 200ms DEPOIS da ação, como um XHR que ainda não saiu.
        # Sem exigir quiescência sustentada, assentar retornaria antes disso.
        montar(driver.page, FIXTURE_MATERIAL)
        driver.page.wait_for_selector("#spin", state="hidden")
        driver.page.evaluate(
            "() => setTimeout(() => {"
            " const s = document.getElementById('spin');"
            " s.style.display = 'block';"
            " setTimeout(() => s.style.display = 'none', 250); }, 200)")
        espera.assentar(driver, 3)
        afirmar(not driver.page.locator("#spin").is_visible(),
                "assentar devolveu antes do spinner tardio aparecer")
    checar("espera: assentar nao antecipa trabalho que ainda vai comecar",
           _nao_antecipa)

    def _teto():
        # Spinner novo com tamanho explícito: preso de verdade, sem depender dos
        # timers da fixture. A condição nunca ocorre, então vale o teto —
        # exatamente o que o sleep original custava.
        driver.page.evaluate(
            "() => { const s = document.createElement('mat-spinner');"
            " s.style.cssText = 'display:block;width:40px;height:40px';"
            " document.body.appendChild(s); }")
        t0 = _t.perf_counter()
        ok = espera.assentar(driver, 0.5)
        gasto = _t.perf_counter() - t0
        afirmar(not ok, "deveria falhar: spinner preso")
        afirmar(0.4 < gasto < 1.2, f"teto nao respeitado: {gasto:.2f}s")
    checar("espera: assentar nunca excede o teto do sleep original", _teto)

    montar(driver.page, FIXTURE_MATERIAL)

    checar("espera: ate_sumir", lambda: afirmar(
        espera.ate_sumir(driver, "#spin", teto=2)))

    checar("espera: ate_desabilitar em botao ativo devolve False", lambda: afirmar(
        not espera.ate_desabilitar(driver, "#abrir", teto=0.3)))

    def _desabilitar():
        driver.page.evaluate("() => document.getElementById('abrir').disabled = true")
        afirmar(espera.ate_desabilitar(driver, "#abrir", teto=1))
    checar("espera: ate_desabilitar detecta botao desabilitado", _desabilitar)

    checar("espera: ate_texto", lambda: afirmar(
        espera.ate_texto(driver, "mat-row", "222", teto=1)))

    checar("espera: ate_js", lambda: afirmar(
        espera.ate_js(driver, "document.querySelectorAll('mat-row').length === 2", teto=1)))

    # XPath: o projeto usa By.XPATH em ~117 pontos. Sem suporte, um XPath
    # passado a ate_* faria querySelectorAll estourar e devolver False na hora.
    checar("espera: ate_aparecer aceita XPath", lambda: afirmar(
        espera.ate_aparecer(driver, "//mat-row[contains(., '222')]", teto=1)))

    checar("espera: ate_sumir aceita XPath", lambda: afirmar(
        espera.ate_sumir(driver, "//mat-row[contains(., 'inexistente')]", teto=1)))

    checar("espera: XPath falso devolve False, nao estoura", lambda: afirmar(
        not espera.ate_aparecer(driver, "//mat-row[contains(., 'zzz')]", teto=0.3)))

    checar("espera: e_xpath distingue CSS de XPath", lambda: afirmar(
        espera.e_xpath("//div") and espera.e_xpath("./span")
        and not espera.e_xpath("div.classe")))


def _servidor_local():
    """Servidor mínimo em 127.0.0.1 que devolve JSON e ecoa o Cookie recebido.

    O `APIRequestContext` faz a requisição fora da aba, então `page.route` não o
    alcança — precisa de um servidor de verdade. E é ele que permite provar a
    afirmação central da E3: a chamada de API leva os cookies do browser.
    """
    import json
    import threading
    from http.server import BaseHTTPRequestHandler, HTTPServer

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            corpo = json.dumps({
                "id": 42, "nome": "processo",
                "cookie": self.headers.get("Cookie", ""),
            }).encode()
            self.send_response(200 if "/pje-comum-api/" in self.path else 404)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(corpo)))
            self.end_headers()
            self.wfile.write(corpo)

        def log_message(self, *_a):
            return

    servidor = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=servidor.serve_forever, daemon=True).start()
    return servidor, f"http://127.0.0.1:{servidor.server_port}"


def testar_api(driver):
    """E3 — acesso à API pelo contexto do browser, contra servidor local."""
    from pjeplay import api

    servidor, base = _servidor_local()
    try:
        driver.page.goto(f"{base}/pje-comum-api/inicio")

        checar("api: requisicao usa o contexto do browser", lambda: afirmar(
            api.requisicao(driver) is driver.context.request))

        checar("api: obter_json pelo contexto", lambda: afirmar(
            (api.obter_json(driver, f"{base}/pje-comum-api/processo/42") or {})
            .get("id") == 42))

        checar("api: obter_json devolve None em rota inexistente", lambda: afirmar(
            api.obter_json(driver, f"{base}/inexistente/x") is None))

        def _auth_compartilhada():
            # O ponto da E3: sem copiar cookie nenhum, a chamada de API sai
            # autenticada porque usa a sessão do próprio browser.
            driver.context.add_cookies(
                [{"name": "JSESSIONID", "value": "xyz", "url": base}])
            dados = api.obter_json(driver, f"{base}/pje-comum-api/quem")
            afirmar("JSESSIONID=xyz" in (dados or {}).get("cookie", ""),
                    f"cookie nao acompanhou: {dados}")
        checar("api: requisicao herda a sessao do browser (sem copiar cookie)",
               _auth_compartilhada)

        def _esperar():
            # A escuta é armada antes da ação — sem janela de corrida.
            resposta = api.esperar_resposta(
                driver, "**/pje-comum-api/**",
                lambda: driver.page.evaluate(
                    f"() => fetch('{base}/pje-comum-api/timeline')"),
                timeout=5)
            afirmar(resposta.ok)
            afirmar(api.corpo(resposta)["id"] == 42)
        checar("api: esperar_resposta captura o XHR da acao", _esperar)

        checar("api: esperar_conclusao confirma a requisicao", lambda: afirmar(
            api.esperar_conclusao(
                driver, "**/pje-comum-api/**",
                lambda: driver.page.evaluate(
                    f"() => fetch('{base}/pje-comum-api/salvar')"),
                timeout=5)))

        def _trafego():
            with api.registrar_trafego(driver, "pje-comum-api") as visto:
                driver.page.evaluate(
                    f"() => fetch('{base}/pje-comum-api/a')"
                    f".then(() => fetch('{base}/pje-comum-api/b'))")
                driver.page.wait_for_timeout(400)
            afirmar(len(visto) >= 2, f"capturou {len(visto)} respostas")
        checar("api: registrar_trafego coleta as chamadas", _trafego)

        def _sessao_compat():
            # A ponte do doc 05 nao precisou ser escrita: session_from_driver
            # usa get_cookies() e current_url, que o PWDriver ja implementa.
            sess, host = api.sessao(driver)
            afirmar(sess.cookies.get("JSESSIONID") == "xyz",
                    "cookie nao atravessou para a requests.Session")
            afirmar("127.0.0.1" in host, f"host={host}")
        checar("api: session_from_driver funciona sem alteracao", _sessao_compat)
    finally:
        servidor.shutdown()


def testar_guarda():
    """A fronteira que impede o fork de crescer de novo."""
    import guarda

    def _limpo():
        duplicados, violacoes = guarda.verificar()
        afirmar(not violacoes, f"violacoes: {violacoes}")
    checar("guarda: fronteira intacta", _limpo)


def testar_projeto():
    """Carrega o projeto real sobre o backend e confere os helpers trocados."""
    import Fix.core as core
    from pjeplay import nativo

    checar("Fix.core importa sob o backend", lambda: afirmar(
        hasattr(core, "criar_driver_PC")))

    checar("helpers de Fix.core foram trocados", lambda: afirmar(
        core.aguardar_renderizacao_nativa is nativo.aguardar_renderizacao_nativa,
        "aguardar_renderizacao_nativa nao foi trocado"))

    for modulo in ("Fix.variaveis", "Fix.extracao", "Fix.utils",
                   "atos.judicial_fluxo", "atos.comunicacao",
                   "PEC.runtime_pec", "Prazo.loop_orquestrador",
                   "Mandado.entrada_api", "SISB.core", "Peticao.runtime_pet",
                   "bianca.triagem_engine"):
        def _importa(m=modulo):
            __import__(m)
        checar(f"import {modulo}", _importa)


def main():
    com_projeto = "--projeto" in sys.argv

    try:
        import playwright  # noqa: F401
    except ImportError:
        print("playwright nao instalado. Rode:  pip install -r play/requirements.txt")
        return 2

    import pjeplay

    if com_projeto:
        pjeplay.iniciar(raiz_projeto=RAIZ, silencioso=True)
    else:
        pjeplay.instalar(silencioso=True)

    driver = pjeplay.criar_driver_PC(headless=True, implicito=2)
    if driver is None:
        print("nao foi possivel iniciar o Firefox do Playwright.")
        print("Rode:  playwright install firefox")
        return 2

    try:
        testar_compatibilidade(driver)
        testar_nativo(driver)
        testar_vocabulario(driver)
        testar_guarda()
        if com_projeto:
            testar_espera(driver)
            testar_api(driver)
            testar_medicao()
            testar_projeto()
    finally:
        pjeplay.finalizar_driver(driver)

    falhas = [r for r in resultados if not r[0]]
    print("\n=== pjeplay smoke ===")
    for ok, nome, detalhe in resultados:
        print(f"  [{'OK ' if ok else 'X  '}] {nome}" + (f"  -> {detalhe}" if detalhe else ""))
    print(f"\n{len(resultados) - len(falhas)}/{len(resultados)} verificacoes passaram")
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
