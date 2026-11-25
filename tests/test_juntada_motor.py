"""Testes unitários do motor de juntada (atos/anexos) após revisão baseada em gigs-plugin aaAnexar."""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from atos.anexos import anexos_juntador_helpers as helpers
from atos.anexos import anexos_juntador_metodos as metodos


# ─────────────────────────────────────────────────────────────────────────────
# 1. Seleção de opções (escolherOpcaoTeste2 / normalização e prioridade exata)
# ─────────────────────────────────────────────────────────────────────────────

def test_escolher_melhor_opcao_prioriza_match_exato_sem_acento():
    op_longa = SimpleNamespace(text='Certidão de devolução de mandado')
    op_exata = SimpleNamespace(text='Certidão')
    op_outra = SimpleNamespace(text='Despacho')

    escolhida = metodos._escolher_melhor_opcao(
        [op_longa, op_exata, op_outra],
        metodos._normalizar_texto('Certidao'),
    )
    assert escolhida is op_exata


def test_escolher_melhor_opcao_fallback_prefixo_e_substring():
    op1 = SimpleNamespace(text='Auto de Penhora')
    op2 = SimpleNamespace(text='Certidão de Trânsito')

    assert metodos._escolher_melhor_opcao([op1, op2], metodos._normalizar_texto('Certidao')) is op2
    assert metodos._escolher_melhor_opcao([op1, op2], metodos._normalizar_texto('penhora')) is op1


# ─────────────────────────────────────────────────────────────────────────────
# 2. Botão Inserir no diálogo de preview (nunca seleciona botão Fechar/X)
# ─────────────────────────────────────────────────────────────────────────────

def test_js_encontrar_botao_inserir_nunca_usa_seletor_generico_button():
    js = metodos._JS_ENCONTRAR_BOTAO_INSERIR
    # Garante que o seletor assassino 'pje-dialogo-visualizar-modelo button' não existe mais
    assert "'pje-dialogo-visualizar-modelo button'" not in js
    assert '"pje-dialogo-visualizar-modelo button"' not in js
    assert 'button[aria-label="Inserir modelo de documento"]' in js
    assert "info.includes('fechar')" in js
    assert "info.includes('inserir')" in js


def test_js_encontrar_editor_principal_prioriza_conteudo_principal_e_exclui_dialogs():
    js = helpers._JS_ENCONTRAR_EDITOR_PRINCIPAL
    assert 'Conteúdo principal' in js
    assert 'pje-dialogo-visualizar-modelo' in js
    assert 'pje-pec-dialogo-ato' in js
    assert 'cabecalho' in js
    assert 'rodape' in js


def test_js_encontrar_editor_principal_aceita_pje_pec_dialogo_ato_e_ignora_preview():
    from playwright.sync_api import sync_playwright

    html = """
    <html><body>
      <mat-dialog-container>
        <pje-pec-dialogo-ato>
          <div id="ed-pec" class="ck-editor__editable area-conteudo" contenteditable="true"
               aria-label="Editor de texto rico, Conteúdo principal">
            <p>INTIMAÇÃO DE BLOQUEIO</p><p>--</p>
          </div>
        </pje-pec-dialogo-ato>
      </mat-dialog-container>
      <mat-dialog-container>
        <pje-dialogo-visualizar-modelo>
          <div id="ed-preview" class="ck-editor__editable" contenteditable="true"
               aria-label="Conteúdo principal">
            <p>PREVIEW --</p>
          </div>
        </pje-dialogo-visualizar-modelo>
      </mat-dialog-container>
    </body></html>
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            page.set_content(html)
            fn = f"function() {{ {helpers._JS_ENCONTRAR_EDITOR_PRINCIPAL} }}"
            el_id = page.evaluate(f"() => {{ const el = ({fn})('--'); return el ? el.id : null; }}")
            assert el_id == 'ed-pec'
        finally:
            browser.close()


# ─────────────────────────────────────────────────────────────────────────────
# 3. _selecionar_modelo_gigs: confirmação real no editor principal (sem falso positivo)
# ─────────────────────────────────────────────────────────────────────────────

def _patch_esperas_rapidas(monkeypatch):
    monkeypatch.setattr(metodos.espera, 'assentar', lambda *a, **k: None)
    monkeypatch.setattr(metodos.espera, 'ate_sumir', lambda *a, **k: True)
    monkeypatch.setattr(metodos.espera, 'ate_aparecer', lambda *a, **k: True)
    monkeypatch.setattr(metodos.espera, 'ate_js', lambda *a, **k: True)
    monkeypatch.setattr(metodos, 'aguardar_renderizacao_nativa', lambda *a, **k: True)
    monkeypatch.setattr(metodos, 'wait_for_clickable', lambda *a, **k: SimpleNamespace(tag='input'))


def test_selecionar_modelo_gigs_confirma_conteudo_no_editor_principal(monkeypatch):
    _patch_esperas_rapidas(monkeypatch)
    fake_editor = SimpleNamespace(id='editor-principal')
    fake_btn_inserir = SimpleNamespace(aria_label='Inserir modelo de documento')
    cliques = []
    estado = {'editor_texto': '', 'inserido': False}

    monkeypatch.setattr(metodos, '_obter_editor_principal', lambda *a, **k: fake_editor)
    monkeypatch.setattr(metodos, '_localizar_botao_inserir_modelo', lambda *a, **k: fake_btn_inserir)

    def fake_click(driver, el):
        cliques.append(el)
        if el is fake_btn_inserir:
            estado['inserido'] = True
            estado['editor_texto'] = 'CERTIDÃO DE RASTREAMENTO E-CARTA\n--\nSão Paulo'
        return True

    monkeypatch.setattr(metodos, 'safe_click_no_scroll', fake_click)

    def fake_exec_js(driver, script, *args):
        if script == metodos._JS_LER_ESTADO_EDITOR:
            txt = estado['editor_texto']
            return {'existe': True, 'ck': True, 'texto': txt, 'htmlLimpo': f'<p>{txt}</p>', 'len': len(txt), 'temMidia': False}
        if script == metodos._JS_SELECIONAR_NODO_FILTRADO:
            return {'status': 'encontrado', 'texto': 'xs carta', 'total': 1}
        if script == metodos._JS_TRECHO_PREVIEW:
            return 'certidao rastreamento e-carta'
        if script == metodos._JS_VERIFICAR_SNACKBAR_MODELO:
            return {'ok': estado['inserido'], 'msg': 'Modelo inserido com sucesso no editor.' if estado['inserido'] else ''}
        return True

    monkeypatch.setattr(metodos, '_executar_js', fake_exec_js)

    juntador = SimpleNamespace(driver=MagicMock())
    ok = metodos._selecionar_modelo_gigs(juntador, 'xs carta', timeout_teor=2, timeout_conteudo=1)

    assert ok is True
    assert cliques == [fake_btn_inserir]


def test_selecionar_modelo_gigs_nao_da_falso_positivo_quando_editor_continua_vazio(monkeypatch):
    _patch_esperas_rapidas(monkeypatch)
    fake_editor = SimpleNamespace(id='editor-principal')
    fake_btn_inserir = SimpleNamespace(aria_label='Inserir modelo de documento')

    monkeypatch.setattr(metodos, '_obter_editor_principal', lambda *a, **k: fake_editor)
    monkeypatch.setattr(metodos, '_localizar_botao_inserir_modelo', lambda *a, **k: fake_btn_inserir)
    monkeypatch.setattr(metodos, 'safe_click_no_scroll', lambda driver, el: True)

    # Simula bug antigo onde o diálogo fechou mas o editor principal continuou VAZIO
    def fake_exec_js(driver, script, *args):
        if script == metodos._JS_LER_ESTADO_EDITOR:
            return {'existe': True, 'ck': True, 'texto': '', 'htmlLimpo': '<p><br></p>', 'len': 0, 'temMidia': False}
        if script == metodos._JS_SELECIONAR_NODO_FILTRADO:
            return {'status': 'encontrado', 'texto': 'xs carta', 'total': 1}
        if script == metodos._JS_TRECHO_PREVIEW:
            return ''
        if script == metodos._JS_VERIFICAR_SNACKBAR_MODELO:
            return {'ok': False, 'msg': ''}
        return True

    monkeypatch.setattr(metodos, '_executar_js', fake_exec_js)

    juntador = SimpleNamespace(driver=MagicMock())
    # timeout_conteudo curto só para o teste executar rápido
    ok = metodos._selecionar_modelo_gigs(juntador, 'xs carta', timeout_teor=1, timeout_conteudo=0.1)

    assert ok is False


def test_selecionar_modelo_gigs_sem_unbound_local_error_quando_nodo_nao_existe(monkeypatch):
    _patch_esperas_rapidas(monkeypatch)
    monkeypatch.setattr(metodos, '_obter_editor_principal', lambda *a, **k: SimpleNamespace(id='ed'))
    monkeypatch.setattr(metodos, '_fechar_dialogo_preview', lambda *a, **k: None)

    # Avança o relógio monotonic para o loop de 6s terminar na primeira iteração
    t = {'val': 0.0}
    def fake_monotonic():
        t['val'] += 10.0
        return t['val']

    monkeypatch.setattr(metodos.time, 'monotonic', fake_monotonic)

    def fake_exec_js(driver, script, *args):
        if script == metodos._JS_LER_ESTADO_EDITOR:
            return {'existe': True, 'ck': True, 'texto': '', 'htmlLimpo': '', 'len': 0, 'temMidia': False}
        if script == metodos._JS_SELECIONAR_NODO_FILTRADO:
            return {'status': 'aguardando'}
        return True

    monkeypatch.setattr(metodos, '_executar_js', fake_exec_js)

    juntador = SimpleNamespace(driver=MagicMock())
    assert metodos._selecionar_modelo_gigs(juntador, 'modelo_inexistente') is False


# ─────────────────────────────────────────────────────────────────────────────
# 4. substituir_marcador_por_conteudo: ignora comentários HTML e valida inserção
# ─────────────────────────────────────────────────────────────────────────────

def test_substituir_marcador_aborta_quando_editor_principal_vazio(monkeypatch):
    monkeypatch.setattr(helpers.espera, 'assentar', lambda *a, **k: None)
    monkeypatch.setattr(helpers, '_obter_editor_principal', lambda *a, **k: SimpleNamespace(id='ed'))

    def fake_exec_js(driver, script, *args):
        if script == helpers._JS_LER_ESTADO_EDITOR:
            # Mesmo que houvesse <!-- comentario --> no HTML, texto limpo tem len 0
            return {'existe': True, 'ck': False, 'texto': '', 'htmlLimpo': '<p></p>', 'len': 0, 'temMidia': False}
        pytest.fail('Não deveria tentar substituir quando editor está vazio')

    monkeypatch.setattr(helpers, '_executar_js', fake_exec_js)

    ok = helpers.substituir_marcador_por_conteudo(
        driver=MagicMock(),
        conteudo_customizado='<table><tr><td>Objeto entregue</td></tr></table>',
        marcador='--',
    )
    assert ok is False


def test_substituir_marcador_confirma_assinatura_pos_insercao(monkeypatch):
    monkeypatch.setattr(helpers.espera, 'assentar', lambda *a, **k: None)
    monkeypatch.setattr(helpers, '_obter_editor_principal', lambda *a, **k: SimpleNamespace(id='ed'))
    estado = {'texto': 'CERTIDÃO E-CARTA\n--\nFim'}

    def fake_exec_js(driver, script, *args):
        if script == helpers._JS_LER_ESTADO_EDITOR:
            txt = estado['texto']
            return {'existe': True, 'ck': True, 'texto': txt, 'htmlLimpo': f'<p>{txt}</p>', 'len': len(txt), 'temMidia': False}
        if script == helpers._JS_SUBSTITUIR_NO_EDITOR:
            estado['texto'] = 'CERTIDÃO E-CARTA\nObjeto entregue ao destinatário em 10/11/2026\nFim'
            return {'sucesso': True, 'metodo': 'ckeditor_api_paragrafo', 'lenAntes': 22}
        return True

    monkeypatch.setattr(helpers, '_executar_js', fake_exec_js)

    ok = helpers.substituir_marcador_por_conteudo(
        driver=MagicMock(),
        conteudo_customizado='<table><tr><td>Objeto entregue ao destinatário em 10/11/2026</td></tr></table>',
        marcador='--',
    )
    assert ok is True


def test_substituir_marcador_reprova_se_editor_nao_refletir_conteudo(monkeypatch):
    monkeypatch.setattr(helpers.espera, 'assentar', lambda *a, **k: None)
    monkeypatch.setattr(helpers, '_obter_editor_principal', lambda *a, **k: SimpleNamespace(id='ed'))

    def fake_exec_js(driver, script, *args):
        if script == helpers._JS_LER_ESTADO_EDITOR:
            # Editor nunca muda após tentativa de inserção
            return {'existe': True, 'ck': False, 'texto': 'CERTIDÃO\n--', 'htmlLimpo': '<p>CERTIDÃO</p><p>--</p>', 'len': 11, 'temMidia': False}
        if script == helpers._JS_SUBSTITUIR_NO_EDITOR:
            return {'sucesso': True, 'metodo': 'ckeditor_paste_marcador', 'lenAntes': 11}
        return True

    monkeypatch.setattr(helpers, '_executar_js', fake_exec_js)

    ok = helpers.substituir_marcador_por_conteudo(
        driver=MagicMock(),
        conteudo_customizado='<p>Rastreamento confirmado dos Correios</p>',
        marcador='--',
    )
    assert ok is False


def test_js_substituir_remove_comentarios_html_e_suporta_en_dash():
    js = helpers._JS_SUBSTITUIR_NO_EDITOR
    assert r'<!--[\s\S]*?-->' in js
    assert 'ckInstance.setData(sub.html)' in js
    assert "new ClipboardEvent('paste'" in js
    assert r'\u2013' in js
    assert r'\u2014' in js


# ─────────────────────────────────────────────────────────────────────────────
# 5. Gate pré-colagem em _inserir_conteudo_customizado
# ─────────────────────────────────────────────────────────────────────────────

def test_gate_pre_colagem_aborta_quando_modelo_nao_chegou_ao_editor_principal(monkeypatch):
    monkeypatch.setattr(metodos.espera, 'assentar', lambda *a, **k: None)
    monkeypatch.setattr(metodos, '_obter_editor_principal', lambda *a, **k: SimpleNamespace(id='ed'))
    monkeypatch.setattr(
        metodos,
        '_ler_estado_editor_principal',
        lambda *a, **k: {'existe': True, 'ck': False, 'texto': '', 'htmlLimpo': '', 'len': 0, 'temMidia': False},
    )

    t = {'val': 0.0}
    def fake_monotonic():
        t['val'] += 5.0
        return t['val']
    monkeypatch.setattr(metodos.time, 'monotonic', fake_monotonic)

    chamou_inserir = []
    def fake_inserir(driver=None, numero_processo=None, debug=True):
        chamou_inserir.append(True)
        return True

    juntador = SimpleNamespace(driver=MagicMock())
    ok = metodos._inserir_conteudo_customizado(
        juntador,
        {'modelo': 'xs carta', 'inserir_conteudo': fake_inserir},
    )
    assert ok is False
    assert chamou_inserir == []


def test_gate_pre_colagem_libera_quando_editor_principal_tem_marcador(monkeypatch):
    monkeypatch.setattr(metodos.espera, 'assentar', lambda *a, **k: None)
    monkeypatch.setattr(metodos, '_obter_editor_principal', lambda *a, **k: SimpleNamespace(id='ed'))
    monkeypatch.setattr(metodos, '_executar_js', lambda *a, **k: True)
    monkeypatch.setattr(
        metodos,
        '_ler_estado_editor_principal',
        lambda *a, **k: {'existe': True, 'ck': True, 'texto': 'CERTIDÃO\n--', 'htmlLimpo': '<p>CERTIDÃO</p><p>--</p>', 'len': 11, 'temMidia': False},
    )

    chamou_inserir = []
    def fake_inserir(driver=None, numero_processo=None, debug=True):
        chamou_inserir.append((driver, numero_processo))
        return True

    juntador = SimpleNamespace(driver=MagicMock())
    ok = metodos._inserir_conteudo_customizado(
        juntador,
        {'modelo': 'xs carta', 'inserir_conteudo': fake_inserir},
    )
    assert ok is True
    assert len(chamou_inserir) == 1
