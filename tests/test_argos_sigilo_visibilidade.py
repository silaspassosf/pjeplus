import sys
import types
import pytest


class _FakeLink:
    def __init__(self, sigiloso: bool = False):
        self.sigiloso = sigiloso

    def get_attribute(self, name: str):
        if name == 'class':
            return 'tl-documento is-sigiloso' if self.sigiloso else 'tl-documento'
        if name == 'role':
            return 'button'
        return ''


class _FakeBtn:
    def __init__(self, on_click):
        self._on_click = on_click
        self.clicks = 0

    def is_displayed(self):
        return True

    def click(self):
        self.clicks += 1
        self._on_click(self.clicks)


class _FakeDocElem:
    def __init__(self, text: str, sigiloso: bool = False, clear_on_click: int = 1, via_icon_only: bool = False):
        self.text = text
        self.sigiloso = sigiloso
        self.via_icon_only = via_icon_only
        self.link = _FakeLink(sigiloso=sigiloso and not via_icon_only)
        self.clear_on_click = clear_on_click
        self.clicks = 0

        def _on_click(n):
            self.clicks += 1
            if self.clicks >= self.clear_on_click:
                self.sigiloso = False
                self.link.sigiloso = False

        self.btn = _FakeBtn(_on_click)

    def query_selector(self, selector: str):
        if 'tl-sigiloso' in selector or 'Retirar sigilo' in selector or 'is-sigiloso' in selector:
            return object() if self.sigiloso else None
        return None


def test_buscar_documentos_sequenciais_usa_devolucao_mais_recente(monkeypatch):
    from Fix import documentos_cp

    # Timeline PJe: idx=0 mais recente (Nov 2026), idx=6 mais antigo (Dez 2025)
    elems = [
        _FakeDocElem('Certidão de devolução de ordem de pesquisa patrimonial - 18/11/2026'),
        _FakeDocElem('Certidão de pesquisa patrimonial - 18/11/2026'),
        _FakeDocElem('Certidão de expedição - 17/11/2026'),
        _FakeDocElem('Planilha de atualização - 16/11/2026'),
        _FakeDocElem('Intimação(123) - 15/11/2026'),
        _FakeDocElem('Decisão(456) - 10/11/2026'),
        _FakeDocElem('Certidão de devolução de ordem de pesquisa patrimonial - 01/12/2025'),
        _FakeDocElem('Decisão(111) - 01/11/2025'),
    ]

    monkeypatch.setattr(documentos_cp, 'aguardar_renderizacao_nativa', lambda driver, timeout=10: True)
    monkeypatch.setattr(documentos_cp.espera, 'elementos', lambda driver, sel, teto=8: elems)

    res = documentos_cp.buscar_documentos_sequenciais(driver=object(), log=False)

    assert len(res) == 6
    assert res[0] is elems[0]  # 2026-11-18, NAO 2025-12-01
    assert elems[1] in res     # Certidão de pesquisa patrimonial de 2026
    assert elems[5] is res[-1] # Decisão de 2026
    assert elems[6] not in res # Bloco antigo de 2025 ignorado
    assert elems[7] not in res


def test_buscar_documentos_sequenciais_via_api_usa_devolucao_mais_recente(monkeypatch):
    from Mandado import apoio_fluxos

    api_timeline = [
        {'idUnicoDocumento': 'uid_2026_dev', 'tipo': 'Certidão', 'titulo': 'Certidão de devolução de ordem de pesquisa patrimonial'},
        {'idUnicoDocumento': 'uid_2026_pesq', 'tipo': 'Certidão', 'titulo': 'Certidão de pesquisa patrimonial'},
        {'idUnicoDocumento': 'uid_2026_exp', 'tipo': 'Certidão', 'titulo': 'Certidão de expedição'},
        {'idUnicoDocumento': 'uid_2026_dec', 'tipo': 'Decisão', 'titulo': 'Decisão'},
        {'idUnicoDocumento': 'uid_2025_dev', 'tipo': 'Certidão', 'titulo': 'Certidão de devolução de ordem de pesquisa patrimonial'},
        {'idUnicoDocumento': 'uid_2025_dec', 'tipo': 'Decisão', 'titulo': 'Decisão'},
    ]

    dom_elems = [
        _FakeDocElem('Certidão de devolução de ordem de pesquisa patrimonial - 2026'),
        _FakeDocElem('Certidão de pesquisa patrimonial - 2026'),
        _FakeDocElem('Certidão de expedição - 2026'),
        _FakeDocElem('Decisão(2026)'),
        _FakeDocElem('Certidão de devolução de ordem de pesquisa patrimonial - 2025'),
        _FakeDocElem('Decisão(2025)'),
    ]

    class _FakeClient:
        def timeline(self, id_proc, buscarDocumentos=True, buscarMovimentos=False):
            return api_timeline

    monkeypatch.setattr(apoio_fluxos, '_extrair_id_processo_da_url', lambda d: '12345')
    monkeypatch.setattr(apoio_fluxos, '_criar_api_client_local', lambda d: _FakeClient())
    monkeypatch.setattr(apoio_fluxos.espera, 'elemento', lambda d, sel, teto=5, visivel=False: dom_elems[0])
    monkeypatch.setattr(apoio_fluxos.espera, 'elementos', lambda d, sel, teto=5: dom_elems)

    res, _uids = apoio_fluxos.buscar_documentos_sequenciais_via_api(driver=object(), log=False)

    assert len(res) == 4
    assert res[0] is dom_elems[0]
    assert res[1] is dom_elems[1]
    assert res[2] is dom_elems[2]
    assert res[3] is dom_elems[3]
    assert dom_elems[4] not in res


def test_buscar_documentos_sequenciais_para_no_despacho_recente_sem_invadir_decisao_antiga(monkeypatch):
    from Fix import documentos_cp
    from Mandado import apoio_fluxos

    # Timeline decrescente: decisão posterior no topo (idx=0) + bloco atual com Despacho (idx=1..3)
    # + bloco antigo com Decisão (idx=4..5). Não pode puxar bloco antigo.
    api_timeline = [
        {'idUnicoDocumento': 'uid_dec_pos', 'tipo': 'Decisão', 'titulo': 'Decisão'},
        {'idUnicoDocumento': 'uid_2026_dev', 'tipo': 'Certidão', 'titulo': 'Certidão de devolução de ordem de pesquisa patrimonial', 'sigiloso': True},
        {'idUnicoDocumento': 'uid_2026_pesq', 'tipo': 'Certidão', 'titulo': 'Certidão de pesquisa patrimonial', 'sigiloso': True},
        {'idUnicoDocumento': 'uid_2026_desp', 'tipo': 'Despacho', 'titulo': 'Despacho', 'sigiloso': True},
        {'idUnicoDocumento': 'uid_2025_dev', 'tipo': 'Certidão', 'titulo': 'Certidão de devolução PJE'},
        {'idUnicoDocumento': 'uid_2025_dec', 'tipo': 'Decisão', 'titulo': 'Decisão'},
    ]
    dom_elems = [
        _FakeDocElem('Decisão(pos) - 19/11/2026'),
        _FakeDocElem('Certidão de devolução de ordem de pesquisa patrimonial - 18/11/2026'),
        _FakeDocElem('Certidão de pesquisa patrimonial - 18/11/2026'),
        _FakeDocElem('Despacho(2026) - 10/11/2026'),
        _FakeDocElem('Certidão de devolução PJE - 01/12/2025'),
        _FakeDocElem('Decisão(2025) - 01/11/2025'),
    ]

    class _FakeClient:
        def timeline(self, id_proc, buscarDocumentos=True, buscarMovimentos=False):
            return api_timeline

    monkeypatch.setattr(documentos_cp, 'aguardar_renderizacao_nativa', lambda driver, timeout=10: True)
    monkeypatch.setattr(documentos_cp.espera, 'elementos', lambda driver, sel, teto=8: dom_elems)
    res_dom = documentos_cp.buscar_documentos_sequenciais(driver=object(), log=False)
    assert res_dom == [dom_elems[1], dom_elems[2], dom_elems[3]]

    monkeypatch.setattr(apoio_fluxos, '_extrair_id_processo_da_url', lambda d: '6811582')
    monkeypatch.setattr(apoio_fluxos, '_criar_api_client_local', lambda d: _FakeClient())
    monkeypatch.setattr(apoio_fluxos.espera, 'elemento', lambda d, sel, teto=5, visivel=False: dom_elems[0])
    monkeypatch.setattr(apoio_fluxos.espera, 'elementos', lambda d, sel, teto=5: dom_elems)
    res_api, uids_sig = apoio_fluxos.buscar_documentos_sequenciais_via_api(driver=object(), log=False)
    assert res_api == [dom_elems[1], dom_elems[2], dom_elems[3]]
    assert uids_sig == ['uid_2026_dev', 'uid_2026_pesq', 'uid_2026_desp']


def test_casa_regra_argos_identifica_regras_e_ignora_atos_intermediarios():
    from Mandado.regras import casa_regra_argos

    assert casa_regra_argos('Decisão', 'Defiro a instauração de incidente de desconsideração...') == 'idpj'
    assert casa_regra_argos('Decisão', 'Tendo em vista que a reclamada permanece inerte...') == 'decisao+tendo_em_vista'
    assert casa_regra_argos('Decisão', 'Intime-se o autor, devendo se manifestar em 5 dias.') == 'decisao+manifestar'
    assert casa_regra_argos('Despacho', 'Expeça-se ordem pelo sistema ARGOS.') == 'despacho+argos'
    assert casa_regra_argos('Despacho', 'Realize-se a pesquisa INFOJUD dos executados.') == 'despacho+infojud'
    assert casa_regra_argos('Despacho', 'Junte-se aos autos e aguarde-se o retorno do mandado.') is None
    assert casa_regra_argos('Decisão', 'Homologo a renúncia de poderes apresentada.') is None


def test_ancora_real_atravessa_despacho_intermediario_e_para_na_primeira_regra_argos(monkeypatch):
    from Mandado import apoio_fluxos

    api_timeline = [
        {'id': '1', 'idUnicoDocumento': 'dev2026', 'tipo': 'Certidão', 'titulo': 'Certidão de devolução de ordem de pesquisa patrimonial', 'sigiloso': True},
        {'id': '2', 'idUnicoDocumento': 'desp_mid', 'tipo': 'Despacho', 'titulo': 'Despacho', 'sigiloso': False},
        {'id': '3', 'idUnicoDocumento': 'pesq2026', 'tipo': 'Certidão', 'titulo': 'Certidão de pesquisa patrimonial', 'sigiloso': True},
        {'id': '4', 'idUnicoDocumento': 'exp2026', 'tipo': 'Certidão', 'titulo': 'Certidão de expedição', 'sigiloso': True},
        {'id': '5', 'idUnicoDocumento': 'int2026', 'tipo': 'Intimação', 'titulo': 'Intimação(decisão sigilosa)', 'sigiloso': True},
        {'id': '6', 'idUnicoDocumento': 'dec999', 'tipo': 'Decisão', 'titulo': 'Decisão', 'sigiloso': True},
        {'id': '7', 'idUnicoDocumento': 'dev2025', 'tipo': 'Certidão', 'titulo': 'Certidão de devolução PJE', 'sigiloso': False},
        {'id': '8', 'idUnicoDocumento': 'dec2025', 'tipo': 'Decisão', 'titulo': 'Decisão', 'sigiloso': False},
    ]
    textos_por_id = {
        '2': 'Junte-se a petição e aguarde-se a devolução das pesquisas.',
        '6': 'Defiro a instauração do IDPJ em face dos sócios.',
        '8': 'Tendo em vista que a execução restou infrutífera...',
    }
    dom_elems = [
        _FakeDocElem('18 nov. 2026\nCertidão de devolução de ordem de pesquisa patrimonial - dev2026', sigiloso=True),
        _FakeDocElem('15 nov. 2026\nDespacho(intermediario) - desp_mid', sigiloso=False),
        _FakeDocElem('10 nov. 2026\nCertidão de pesquisa patrimonial - pesq2026', sigiloso=True),
        _FakeDocElem('Certidão de expedição - exp2026', sigiloso=True),
        _FakeDocElem('05 nov. 2026\nIntimação(decisão sigilosa) - int2026', sigiloso=True),
        _FakeDocElem('Decisão(Pesquisas para execução) - dec999', sigiloso=True),
        _FakeDocElem('01 dez. 2025\nCertidão de devolução PJE - dev2025', sigiloso=False),
        _FakeDocElem('01 nov. 2025\nDecisão(antiga) - dec2025', sigiloso=False),
    ]

    class _FakeClient:
        def timeline(self, id_proc, buscarDocumentos=True, buscarMovimentos=False):
            return api_timeline

    def _fake_elementos(ctx, sel, teto=5):
        if isinstance(ctx, _FakeDocElem):
            return [ctx.link] if sel == 'a.tl-documento' else []
        return dom_elems

    monkeypatch.setattr(apoio_fluxos, '_extrair_id_processo_da_url', lambda d: '6811582')
    monkeypatch.setattr(apoio_fluxos, '_criar_api_client_local', lambda d: _FakeClient())
    monkeypatch.setattr(apoio_fluxos, '_baixar_texto_doc_api', lambda c, p, doc, log=False: textos_por_id.get(doc.get('id')))
    monkeypatch.setattr(apoio_fluxos.espera, 'elemento', lambda d, sel, teto=5, visivel=False: dom_elems[0])
    monkeypatch.setattr(apoio_fluxos.espera, 'elementos', _fake_elementos)

    res_api, uids_sig = apoio_fluxos.buscar_documentos_sequenciais_via_api(driver=object(), log=False)

    # Atravessa desp_mid (não bate regra Argos, não sigiloso), ancora em dec999 e ignora bloco de 2025
    assert res_api == [dom_elems[0], dom_elems[2], dom_elems[3], dom_elems[4], dom_elems[5]]
    assert uids_sig == ['dev2026', 'pesq2026', 'exp2026', 'int2026', 'dec999']
    assert dom_elems[6] not in res_api
    assert dom_elems[7] not in res_api


def test_retirar_sigilo_fluxo_argos_remove_todos_sem_caps_e_com_retry(monkeypatch):
    from Mandado import apoio_fluxos

    docs = [
        _FakeDocElem('Certidão de devolução de ordem de pesquisa patrimonial', sigiloso=True, clear_on_click=1),
        _FakeDocElem('Certidão de pesquisa patrimonial 1', sigiloso=True, clear_on_click=2),  # exige retry
        _FakeDocElem('Certidão de pesquisa patrimonial 2', sigiloso=True, via_icon_only=True),  # detectado via icone
        _FakeDocElem('Certidão de expedição', sigiloso=False),
        _FakeDocElem('Planilha de atualização', sigiloso=True),
        _FakeDocElem('Planilha de cálculo', sigiloso=True),
        _FakeDocElem('Decisão(999)', sigiloso=True),
    ]

    def _fake_elementos(ctx, sel, teto=0.5):
        if isinstance(ctx, _FakeDocElem):
            if sel == 'a.tl-documento':
                return [ctx.link]
            if 'tl-sigiloso' in sel or 'Retirar sigilo' in sel:
                return [object()] if ctx.sigiloso else []
        return []

    def _fake_elemento(ctx, sel, teto=0.4):
        if isinstance(ctx, _FakeDocElem) and ('Retirar sigilo' in sel or 'pje-doc-sigiloso' in sel):
            return ctx.btn
        return None

    monkeypatch.setattr(apoio_fluxos.espera, 'elementos', _fake_elementos)
    monkeypatch.setattr(apoio_fluxos.espera, 'elemento', _fake_elemento)
    monkeypatch.setattr(apoio_fluxos.espera, 'assentar', lambda d, t=0.25: None)
    monkeypatch.setattr(apoio_fluxos, 'safe_click_no_scroll', lambda d, el: el.click())

    # Mesmo passando uids_sigilosos_hint parcial, TODOS os docs sigilosos do DOM devem ser limpos
    res = apoio_fluxos.retirar_sigilo_fluxo_argos(
        driver=object(),
        documentos_sequenciais=docs,
        log=False,
        uids_sigilosos_hint=['uid_parcial'],
    )

    assert res['sucesso'] is True
    assert res['certidao_devolucao']['status'] == 'removido'
    assert res['total_processados'] == 6
    assert all(not d.sigiloso for d in docs)
    assert docs[1].clicks == 2  # retry aplicado


def test_aguardar_visibilidade_concluida_exige_ausencia_e_estabilidade(monkeypatch):
    from atos import anexos_sigilo

    # Simula: dialog aberto -> 1 frame livre (gap de transição) -> dialogo de progresso -> livre estável
    sequencia = [
        {'dialogs': ['pje-doc-visibilidade-sigilo'], 'backdrop': True, 'loading': False, 'livre': False},
        {'dialogs': [], 'backdrop': False, 'loading': False, 'livre': True},  # gap curto!
        {'dialogs': ['pje-dialogo-status-progresso'], 'backdrop': True, 'loading': True, 'livre': False},
        {'dialogs': [], 'backdrop': False, 'loading': False, 'livre': True},
        {'dialogs': [], 'backdrop': False, 'loading': False, 'livre': True},
        {'dialogs': [], 'backdrop': False, 'loading': False, 'livre': True},
    ]
    idx = {'i': 0}

    def _fake_exec_js(driver, body):
        i = idx['i']
        if i < len(sequencia):
            idx['i'] += 1
            return sequencia[i]
        return sequencia[-1]

    class _FakeClock:
        def __init__(self):
            self.t = 0.0

        def monotonic(self):
            return self.t

        def sleep(self, dt):
            self.t += dt

    clock = _FakeClock()
    monkeypatch.setattr(anexos_sigilo, '_exec_js', _fake_exec_js)
    monkeypatch.setattr(anexos_sigilo.time, 'monotonic', clock.monotonic)
    monkeypatch.setattr(anexos_sigilo.time, 'sleep', clock.sleep)

    ok = anexos_sigilo.aguardar_visibilidade_concluida(driver=object(), timeout=10.0, estabilidade=0.5, log=False)
    assert ok is True
    # Deve ter atravessado o gap curto (idx 1) e esperado o pje-dialogo-status-progresso (idx 2)
    assert idx['i'] >= 4


def test_aguardar_visibilidade_concluida_retorna_false_no_timeout(monkeypatch):
    from atos import anexos_sigilo

    class _FakeClock:
        def __init__(self):
            self.t = 0.0

        def monotonic(self):
            return self.t

        def sleep(self, dt):
            self.t += dt

    clock = _FakeClock()
    monkeypatch.setattr(
        anexos_sigilo,
        '_exec_js',
        lambda d, body: {'dialogs': ['pje-doc-visibilidade-sigilo'], 'backdrop': True, 'loading': False, 'livre': False},
    )
    monkeypatch.setattr(anexos_sigilo.time, 'monotonic', clock.monotonic)
    monkeypatch.setattr(anexos_sigilo.time, 'sleep', clock.sleep)

    ok = anexos_sigilo.aguardar_visibilidade_concluida(driver=object(), timeout=1.0, estabilidade=0.3, log=False)
    assert ok is False


def test_processar_argos_trata_anexos_de_todas_as_certidoes_de_pesquisa(monkeypatch):
    from Mandado import fluxo_argos
    from atos import anexos_sigilo
    from core.resultado_execucao import ResultadoExecucao

    cert_dev = _FakeDocElem('Certidão de devolução de ordem de pesquisa patrimonial - dev01')
    cert_exp = _FakeDocElem('Certidão de expedição - exp01')
    certs_pesq = [
        _FakeDocElem(f'Certidão(Certidão de pesquisa patrimonial) - pesq{i}')
        for i in range(1, 7)
    ]
    desp = _FakeDocElem('Despacho(Despacho) - 217c1af')
    bloco = [cert_dev, cert_exp, *certs_pesq, desp]

    chamadas_anexos = []
    regras_recebidas = []

    def _fake_tratar_anexos(driver, docs, log=False, escopo_doc=False):
        chamadas_anexos.append((docs[0], escopo_doc))
        if docs[0] is cert_dev:
            return ResultadoExecucao(
                sucesso=True,
                status='OK',
                detalhes={'tem_anexos': True, 'sigilo_anexos': {'infojud': 'nao'}, 'sigiloso': False},
            )
        if docs[0] is certs_pesq[3]:
            raise RuntimeError('falha simulada na certidao 4')
        if docs[0] in (certs_pesq[0], certs_pesq[4], certs_pesq[5]):
            return ResultadoExecucao(
                sucesso=True,
                status='OK',
                detalhes={'tem_anexos': True, 'sigilo_anexos': {'infojud': 'sim'}, 'sigiloso': True},
            )
        return ResultadoExecucao(
            sucesso=True,
            status='OK',
            detalhes={'tem_anexos': True, 'sigilo_anexos': {'infojud': 'nao'}, 'sigiloso': False},
        )

    def _fake_aplicar_regras(driver, res_sisb, sig_anexos, doc_tipo, doc_txt, debug=False):
        regras_recebidas.append((res_sisb, dict(sig_anexos), doc_tipo))
        return True

    class _FakeDriver:
        current_url = 'https://pje.trt2.jus.br/pjekz/processo/5720200/detalhe'

    monkeypatch.setattr(fluxo_argos, 'fechar_intimacao', lambda d, log=False: True)
    monkeypatch.setattr(fluxo_argos, 'buscar_documentos_sequenciais_via_api', lambda d, log=False: (bloco, []))
    monkeypatch.setattr(fluxo_argos, 'retirar_sigilo_fluxo_argos', lambda d, docs, log=False, uids_sigilosos_hint=None: {'total_processados': 0})
    monkeypatch.setattr(fluxo_argos, 'tratar_anexos_argos', _fake_tratar_anexos)
    monkeypatch.setattr(anexos_sigilo, 'aguardar_visibilidade_concluida', lambda d, timeout=30.0, estabilidade=0.5, log=False: True)
    monkeypatch.setattr(fluxo_argos, '_extrair_texto_certidao_via_api', lambda d, log=False: 'texto certidao')
    monkeypatch.setattr(fluxo_argos, 'processar_sisbajud', lambda txt, log=False: ('negativo', 'ok', []))
    monkeypatch.setattr(fluxo_argos, '_extrair_documentos_decisao_despacho_api', lambda d, log=False: [('Expeça-se ordem ARGOS', 'Despacho', 11)])
    monkeypatch.setattr(fluxo_argos, 'extrair_dados_processo', lambda d, debug=False: {})
    monkeypatch.setattr(fluxo_argos, 'extrair_numero_processo', lambda d: '1001680-46.2023.5.02.0703')
    monkeypatch.setattr(fluxo_argos, 'extrair_destinatarios_decisao', lambda txt, dados_processo=None, debug=False: [])
    monkeypatch.setattr(fluxo_argos, 'aplicar_regras_argos', _fake_aplicar_regras)
    monkeypatch.setattr('Fix.variaveis.cliente_para', lambda d: None)
    monkeypatch.setattr('Fix.variaveis.obter_gigs_com_fase', lambda c, p: {'fase': 'execucao'})

    ok = fluxo_argos.processar_argos(_FakeDriver(), log=False)
    assert ok is True

    # 1 chamada para certidao de devolucao (escopo_doc=False) + 6 para cada certidao de pesquisa (escopo_doc=True)
    assert len(chamadas_anexos) == 7
    assert chamadas_anexos[0] == (cert_dev, False)
    assert chamadas_anexos[1:] == [(c, True) for c in certs_pesq]

    # sigilo_anexos mesclado das certidoes de pesquisa chega na ETAPA 4
    assert len(regras_recebidas) == 1
    assert regras_recebidas[0][1].get('infojud') == 'sim'


def test_tratar_anexos_argos_escopo_doc_espera_no_doc_e_pula_multi_sem_especiais(monkeypatch):
    from Mandado import anexos_argos
    from atos import anexos_sigilo

    doc = _FakeDocElem('Certidão de pesquisa patrimonial - pesq2')
    anexo_comum = types.SimpleNamespace(text='RENAJUD_negativo.pdf')
    btn_anexos = _FakeBtn(lambda _n: setattr(doc, 'expandido', True))
    doc.expandido = False

    chamou_global_render = []
    chamou_multi = []

    def _fake_elementos(ctx, sel, teto=2):
        if ctx is doc and sel == 'button.botao-anexos':
            return [btn_anexos]
        if ctx is doc and sel == '.tl-item-anexo':
            return [anexo_comum] if doc.expandido else []
        return []

    monkeypatch.setattr(anexos_sigilo, 'aguardar_visibilidade_concluida', lambda d, timeout=25.0, estabilidade=0.4, log=False: True)
    monkeypatch.setattr(anexos_argos.espera, 'elementos', _fake_elementos)
    monkeypatch.setattr(anexos_argos, 'safe_click_no_scroll', lambda d, el: el.click())
    monkeypatch.setattr(anexos_argos, 'aguardar_renderizacao_nativa', lambda *a, **k: chamou_global_render.append(True))
    monkeypatch.setattr(anexos_argos.espera, 'ate_habilitar', lambda *a, **k: chamou_multi.append(True) or False)

    res = anexos_argos.tratar_anexos_argos(driver=object(), documentos_sequenciais=[doc], log=False, escopo_doc=True)

    assert res is not None
    assert res.detalhes['tem_anexos'] is True
    assert res.detalhes['sigiloso'] is False
    assert btn_anexos.clicks == 1
    assert chamou_global_render == []
    assert chamou_multi == []


def test_tratar_anexos_argos_escopo_doc_aplica_sigilo_e_visibilidade_em_infojud(monkeypatch):
    from Mandado import anexos_argos
    from atos import anexos_sigilo

    doc = _FakeDocElem('Certidão de pesquisa patrimonial - pesq3')
    anexo_infojud = types.SimpleNamespace(text='INFOJUD_socio.pdf')
    btn_anexos = _FakeBtn(lambda _n: setattr(doc, 'expandido', True))
    doc.expandido = False
    btn_multi = _FakeBtn(lambda _n: None)
    chk_anexo = _FakeBtn(lambda _n: None)

    sigilos_inseridos = []
    visibilidades = []

    def _fake_elementos(ctx, sel, teto=2):
        if ctx is doc and sel == 'button.botao-anexos':
            return [btn_anexos]
        if ctx is doc and sel == '.tl-item-anexo':
            return [anexo_infojud] if doc.expandido else []
        return []

    def _fake_elemento(ctx, sel, teto=1):
        if sel == 'button[aria-label="Ocultar múltipla seleção."]':
            return None
        if sel == 'button[aria-label="Exibir múltipla seleção."]':
            return btn_multi
        if ctx is anexo_infojud and sel == 'mat-checkbox':
            return chk_anexo
        if ctx is anexo_infojud and sel == 'mat-checkbox input[type="checkbox"]':
            return types.SimpleNamespace(is_selected=lambda: False, is_checked=lambda: False)
        if ctx is anexo_infojud and sel == 'span.mat-checkbox-inner-container':
            return chk_anexo
        return None

    monkeypatch.setattr(anexos_sigilo, 'aguardar_visibilidade_concluida', lambda d, timeout=25.0, estabilidade=0.4, log=False: True)
    monkeypatch.setattr(anexos_sigilo, 'inserir_sigilo_individual', lambda el, d, debug=False: sigilos_inseridos.append(el) or True)
    monkeypatch.setattr(anexos_sigilo, 'visibilidade_sigilosos_lote_apenas', lambda d, polo='ativo', log=False: visibilidades.append(polo) or True)
    monkeypatch.setattr(anexos_argos.espera, 'elementos', _fake_elementos)
    monkeypatch.setattr(anexos_argos.espera, 'elemento', _fake_elemento)
    monkeypatch.setattr(anexos_argos.espera, 'ate_habilitar', lambda d, sel, teto=10: True)
    monkeypatch.setattr(anexos_argos.espera, 'assentar', lambda d, t=0.1: None)
    monkeypatch.setattr(anexos_argos, 'safe_click_no_scroll', lambda d, el: el.click())

    res = anexos_argos.tratar_anexos_argos(driver=object(), documentos_sequenciais=[doc], log=False, escopo_doc=True)

    assert res is not None
    assert res.detalhes['tem_anexos'] is True
    assert res.detalhes['sigiloso'] is True
    assert res.detalhes['sigilo_anexos']['infojud'] == 'sim'
    assert sigilos_inseridos == [anexo_infojud]
    assert chk_anexo.clicks == 1
    assert visibilidades == ['ativo']
