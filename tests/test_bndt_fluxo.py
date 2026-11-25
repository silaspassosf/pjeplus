import pytest


HTML_BNDT_PROBE = """
<!doctype html>
<html>
<body>
  <div id="selecao-polo">
    <mat-radio-group name="mat-radio-group-0">
      <mat-radio-button value="Ativo">
        <label class="mat-radio-label">
          <span class="mat-radio-container">
            <span class="mat-radio-outer-circle"></span>
            <span class="mat-radio-inner-circle"></span>
            <input type="radio" name="mat-radio-group-0" value="Ativo">
          </span>
          <span class="mat-radio-label-content">Ativo</span>
        </label>
      </mat-radio-button>
      <mat-radio-button value="Passivo">
        <label class="mat-radio-label">
          <span class="mat-radio-container">
            <span class="mat-radio-outer-circle"></span>
            <span class="mat-radio-inner-circle"></span>
            <input type="radio" name="mat-radio-group-0" value="Passivo">
          </span>
          <span class="mat-radio-label-content">Passivo</span>
        </label>
      </mat-radio-button>
    </mat-radio-group>
  </div>

  <div id="selecao-tipo-determinacao">
    <mat-radio-group name="mat-radio-group-1">
      <mat-radio-button value="INCLUSAO">
        <label class="mat-radio-label">
          <span class="mat-radio-container">
            <span class="mat-radio-outer-circle"></span>
            <span class="mat-radio-inner-circle"></span>
            <input type="radio" name="mat-radio-group-1" value="INCLUSAO">
          </span>
          <span class="mat-radio-label-content">Inclusão</span>
        </label>
      </mat-radio-button>
      <mat-radio-button value="EXCLUSAO">
        <label class="mat-radio-label">
          <span class="mat-radio-container">
            <span class="mat-radio-outer-circle"></span>
            <span class="mat-radio-inner-circle"></span>
            <input type="radio" name="mat-radio-group-1" value="EXCLUSAO">
          </span>
          <span class="mat-radio-label-content">Exclusão</span>
        </label>
      </mat-radio-button>
    </mat-radio-group>
  </div>

  <div id="conteudo-bndt"></div>
  <div id="overlays" class="cdk-overlay-container"></div>

  <script>
    window.__bndtLog = {
      polo: null,
      operacao: null,
      gravado: false,
      confirmadoSim: false,
      fechouSnack: false,
    };

    // Comportamento fiel ao Angular Material:
    // clicar no host <mat-radio-button> NÃO muda estado; apenas clicar no <label> ou <input> muda.
    document.querySelectorAll('mat-radio-button label.mat-radio-label').forEach(lbl => {
      lbl.addEventListener('click', () => {
        const mat = lbl.closest('mat-radio-button');
        const inp = mat.querySelector('input[type="radio"]');
        const grp = mat.closest('mat-radio-group');
        grp.querySelectorAll('mat-radio-button').forEach(r => {
          r.classList.remove('mat-radio-checked');
          const ri = r.querySelector('input[type="radio"]');
          if (ri) ri.checked = false;
        });
        mat.classList.add('mat-radio-checked');
        inp.checked = true;
        if (grp.getAttribute('name') === 'mat-radio-group-0') {
          window.__bndtLog.polo = inp.value;
        } else {
          window.__bndtLog.operacao = inp.value;
          carregarLista(inp.value);
        }
      });
    });

    function carregarLista(tipo) {
      const container = document.getElementById('conteudo-bndt');
      container.innerHTML = '<div class="container-loading"><mat-progress-spinner>loading</mat-progress-spinner></div>';
      setTimeout(() => {
        if (tipo === 'INCLUSAO') {
          container.innerHTML = `
            <pje-bndt-partes-sem-registro>
              <mat-checkbox id="parte35105807">
                <label class="mat-checkbox-layout" for="parte35105807-input">
                  <input type="checkbox" id="parte35105807-input">
                  <span class="mat-checkbox-label">EL CAMINO FOODS S.A. - 10.291.637/0001-3</span>
                </label>
              </mat-checkbox>
            </pje-bndt-partes-sem-registro>
            <button id="btn-gravar" class="mat-raised-button mat-button-base mat-primary mat-button-disabled" disabled>
              <span>Gravar</span>
            </button>
          `;
        } else {
          container.innerHTML = `
            <pje-bndt-exclusao>
              <mat-checkbox id="debito101">
                <label class="mat-checkbox-layout" for="debito101-input">
                  <input type="checkbox" id="debito101-input">
                  <span class="mat-checkbox-label">EL CAMINO FOODS S.A.</span>
                </label>
              </mat-checkbox>
              <mat-checkbox id="debito102">
                <label class="mat-checkbox-layout" for="debito102-input">
                  <input type="checkbox" id="debito102-input">
                  <span class="mat-checkbox-label">SOCIO TESTE</span>
                </label>
              </mat-checkbox>
            </pje-bndt-exclusao>
            <button id="btn-gravar" class="mat-raised-button mat-button-base mat-primary mat-button-disabled" disabled>
              <span>Gravar</span>
            </button>
          `;
        }
        container.querySelectorAll('mat-checkbox input[type="checkbox"]').forEach(chk => {
          chk.addEventListener('change', () => {
            const mat = chk.closest('mat-checkbox');
            mat.classList.toggle('mat-checkbox-checked', chk.checked);
            const algumMarcado = Array.from(container.querySelectorAll('input[type="checkbox"]')).some(c => c.checked);
            const btn = document.getElementById('btn-gravar');
            btn.disabled = !algumMarcado;
            btn.classList.toggle('mat-button-disabled', !algumMarcado);
          });
        });
        document.getElementById('btn-gravar').addEventListener('click', () => {
          window.__bndtLog.gravado = true;
          const overlays = document.getElementById('overlays');
          overlays.innerHTML = `
            <div class="cdk-overlay-pane">
              <mat-dialog-container role="dialog" class="mat-dialog-container">
                <h2 class="mat-dialog-title">Decisão não encontrada</h2>
                <button id="btn-sim" class="mat-button mat-button-base mat-primary"><span>Sim</span></button>
                <button class="mat-button mat-button-base"><span>Não</span></button>
              </mat-dialog-container>
            </div>
          `;
          document.getElementById('btn-sim').addEventListener('click', () => {
            window.__bndtLog.confirmadoSim = true;
            overlays.innerHTML = `
              <div class="cdk-overlay-pane">
                <mat-dialog-container role="dialog" class="mat-dialog-container">
                  ${tipo === 'INCLUSAO' ? 'Incluindo registro(s) no BNDT...' : 'Excluindo registro(s) no BNDT...'}
                </mat-dialog-container>
              </div>
            `;
            setTimeout(() => {
              overlays.innerHTML = `
                <simple-snack-bar>
                  <span>${tipo === 'INCLUSAO' ? 'Incluído registro de EL CAMINO FOODS S.A.' : 'Excluído registro de EL CAMINO FOODS S.A.'}</span>
                  <button id="btn-fechar-snack" class="mat-button mat-button-base">X</button>
                </simple-snack-bar>
              `;
              document.getElementById('btn-fechar-snack').addEventListener('click', () => {
                window.__bndtLog.fechouSnack = true;
                overlays.innerHTML = '';
              });
            }, 120);
          });
        });
      }, 120);
    }
  </script>
</body>
</html>
"""


class _PWPageDriver:
    """Wrapper mínimo em torno de uma `Page` real do Playwright para exercitar `Fix.extracao.bndt`."""

    def __init__(self, page):
        self.page = page
        self._handles = ['main', 'bndt']
        self.current_window_handle = 'bndt'
        self.closed = False

    @property
    def window_handles(self):
        return list(self._handles)

    @property
    def current_url(self):
        return 'https://pje.trt2.jus.br/pjekz/processo/7759417/bndt'

    def execute_script(self, script, *args):
        return self.page.evaluate(f"() => {{ {script} }}")

    def close(self):
        self.closed = True

    @property
    def switch_to(self):
        driver = self
        class _Switch:
            def window(self, handle):
                driver.current_window_handle = handle
        return _Switch()


@pytest.mark.parametrize('inclusao', [True, False])
def test_bndt_fluxo_completo_probe_real_playwright(monkeypatch, inclusao):
    from playwright.sync_api import sync_playwright
    from Fix import extracao

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            page.set_content(HTML_BNDT_PROBE)
            driver = _PWPageDriver(page)

            monkeypatch.setattr(extracao, '_bndt_abrir_nova_aba', lambda d: ('main', 'bndt'))

            # Compatibiliza espera.elemento para localizar simple-snack-bar na Page real
            class _MiniEl:
                def __init__(self, loc):
                    self._loc = loc
                @property
                def text(self):
                    return self._loc.inner_text()
                def click(self):
                    self._loc.click()

            orig_elemento = extracao.espera.elemento
            def _fake_elemento(d, sel, teto=5, visivel=False):
                if sel in ('simple-snack-bar', 'simple-snack-bar button'):
                    loc = d.page.locator(sel).first
                    try:
                        loc.wait_for(state='attached', timeout=int(teto * 1000))
                        return _MiniEl(loc)
                    except Exception:
                        return None
                return orig_elemento(d, sel, teto=teto, visivel=visivel)

            monkeypatch.setattr(extracao.espera, 'elemento', _fake_elemento)
            monkeypatch.setattr(extracao, 'safe_click_no_scroll', lambda d, el: el.click())
            monkeypatch.setattr(extracao.espera, 'ate_sumir', lambda d, sel, teto=10: True)

            ok = extracao.bndt(driver, inclusao=inclusao)
            estado = page.evaluate("() => window.__bndtLog")

            assert ok is True
            assert estado['polo'] == 'Passivo'
            assert estado['operacao'] == ('INCLUSAO' if inclusao else 'EXCLUSAO')
            assert estado['gravado'] is True
            assert estado['confirmadoSim'] is True
            assert estado['fechouSnack'] is True
            assert driver.closed is True
            assert driver.current_window_handle == 'main'
        finally:
            browser.close()
