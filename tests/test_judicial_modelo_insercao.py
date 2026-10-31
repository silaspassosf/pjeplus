# -*- coding: utf-8 -*-
"""Testes da confirmação de conteúdo em inserir_modelo_no_editor.

Critério adotado — porte de gigs-plugin.js verificarSeExisteTextoNoEditor()
(linha ~10771):

    if (areaConteudo?.innerText.length > 1) { resposta = true }
    if (areaConteudo.querySelector('figure')) { resposta = true }

Duas propriedades que os testes travam:
  1. ESCOPADO  — só o editor-alvo decide (não a página inteira).
  2. ABSOLUTO  — "tem texto", não "cresceu desde um baseline".

O caso real por trás disso: processo 1000845-63.2020.5.02.0703, editor-alvo
vazio, outra área da página com texto herdado, log dizendo "inserido e
confirmado", e minuta salva em branco.
"""
import importlib.util
import json
import os
import re
import sys
import types

_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

TXTBOX = 'div[class*="area-conteudo"][contenteditable="true"][role="textbox"]'
OUTRA = 'div[class*="area-conteudo"] div[contenteditable="true"]'


def _carregar_isolado():
    espera = types.ModuleType('Fix.espera')
    espera.ate_js = lambda *a, **k: False
    espera.assentar = lambda *a, **k: None
    espera.elemento = lambda *a, **k: None
    espera.elementos = lambda *a, **k: []
    espera.ate_texto = lambda *a, **k: False
    fix = types.ModuleType('Fix')
    fix.espera = espera
    fix_core = types.ModuleType('Fix.core')
    for nome in ('aguardar_e_clicar', 'wait_for_clickable', 'safe_click_no_scroll',
                 'aguardar_renderizacao_nativa', 'preencher_campo'):
        setattr(fix_core, nome, lambda *a, **k: None)
    navegacao = types.ModuleType('atos.judicial_navegacao')
    for nome in ('verificar_estado_atual', 'escolher_tipo_conclusao',
                 'aguardar_transicao_minutar', 'focar_campo_minutar_se_necessario'):
        setattr(navegacao, nome, lambda *a, **k: None)

    pacote_atos = types.ModuleType('atos')
    pacote_atos.__path__ = [os.path.join(_RAIZ, 'atos')]

    sys.modules.update({
        'Fix': fix, 'Fix.espera': espera, 'Fix.core': fix_core,
        'atos': pacote_atos, 'atos.judicial_navegacao': navegacao,
    })

    caminho = os.path.join(_RAIZ, 'atos', 'judicial_modelos.py')
    spec = importlib.util.spec_from_file_location('atos.judicial_modelos', caminho)
    modulo = importlib.util.module_from_spec(spec)
    sys.modules['atos.judicial_modelos'] = modulo
    spec.loader.exec_module(modulo)
    return modulo


jm = _carregar_isolado()


class PageFalsa:
    """Executa o JS de confirmação contra um DOM falso.

    areas: {seletor: {'texto': str, 'figure': bool}}; seletor ausente = None.
    """

    def __init__(self, areas):
        self.areas = areas
        self.chamadas = 0

    def evaluate(self, script):
        self.chamadas += 1
        m = re.search(r'\("(.*)"\)\s*$', script)
        if not m:
            raise AssertionError('script inesperado: %s' % script[:120])
        sel = json.loads('"%s"' % m.group(1))
        area = self.areas.get(sel)

        if 'trim()).length' in script:          # _JS_MEDIR (diagnóstico)
            return -1 if area is None else len(area['texto'].strip())

        # _JS_EDITOR_COM_CONTEUDO
        if area is None:
            return False
        if len(area['texto'].strip()) > 1:
            return True
        return bool(area['figure'])


class DriverFalso:
    def __init__(self, areas):
        self.page = PageFalsa(areas)


def _avaliar(areas, sel):
    expr = "(%s)(%s)" % (jm._JS_EDITOR_COM_CONTEUDO, json.dumps(sel))
    return DriverFalso(areas).page.evaluate(expr)


def test_falso_positivo_antigo_nao_passa():
    """Cenário do 1000845-63: alvo VAZIO, outra área com texto herdado.

    A varredura antiga (todas as áreas) devolvia True aqui — foi o que fez a
    minuta em branco passar como sucesso. O critério escopado reprova.
    """
    areas = {
        TXTBOX: {'texto': '', 'figure': False},
        OUTRA: {'texto': 'Preâmbulo herdado do processo anterior', 'figure': False},
    }
    assert _avaliar(areas, TXTBOX) is False


def test_insercao_no_alvo_confirma():
    areas = {TXTBOX: {'texto': 'Concedo o prazo de oito dias.', 'figure': False}}
    assert _avaliar(areas, TXTBOX) is True


def test_figure_sem_texto_confirma():
    """Padrão gigs: imagem anexada sem texto conta como conteúdo."""
    areas = {TXTBOX: {'texto': '', 'figure': True}}
    assert _avaliar(areas, TXTBOX) is True


def test_editor_ausente_nao_confirma():
    assert _avaliar({}, TXTBOX) is False


def test_pouco_texto_nao_confirma():
    """gigs exige innerText.length > 1."""
    areas = {TXTBOX: {'texto': ' ', 'figure': False}}
    assert _avaliar(areas, TXTBOX) is False


def test_retomada_de_minuta_ja_preenchida_confirma():
    """Sem baseline: minuta já preenchida conta (mesmo critério do gigs)."""
    areas = {TXTBOX: {'texto': 'Minuta anterior já elaborada.', 'figure': False}}
    assert _avaliar(areas, TXTBOX) is True


def test_seletor_canonico_e_o_do_gigs():
    """Mesmo seletor de +pje/comum/seletores.js:8 (SELETORES.editor.areaConteudo)."""
    assert jm._SEL_EDITOR_TEXTOBOX == TXTBOX


def test_js_editor_alvo_prioriza_textbox():
    js = jm._JS_EDITOR_ALVO
    pos_textbox = js.index('[role="textbox"][aria-label*="Dispositivo"]')
    pos_generico = js.index(
        'div[class*="area-conteudo"] div[contenteditable="true"][aria-label*="Dispositivo"]')
    assert pos_textbox < pos_generico, 'role=textbox deve ser tentado antes do seletor genérico'


def test_medir_conteudo_editor_nao_decide_sucesso():
    """_medir_conteudo_editor é diagnóstico; não deve ser usada como prova."""
    fonte = open(os.path.join(_RAIZ, 'atos', 'judicial_modelos.py'), encoding='utf-8').read()
    corpo = fonte[fonte.index('def inserir_modelo_no_editor'):]
    assert '_medir_conteudo_editor(' not in corpo, (
        'a confirmação não pode depender de medida comparativa/absoluta via helper'
    )


if __name__ == '__main__':
    testes = [v for k, v in sorted(globals().items()) if k.startswith('test_')]
    falhas = 0
    for t in testes:
        try:
            t()
            print('OK  %s' % t.__name__)
        except AssertionError as e:
            falhas += 1
            print('FALHOU  %s: %s' % (t.__name__, e))
    print('\n%d testes passaram%s' % (
        len(testes) - falhas, ', %d falharam' % falhas if falhas else ''))
    sys.exit(1 if falhas else 0)
