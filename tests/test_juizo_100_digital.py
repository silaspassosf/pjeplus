"""Testes das ações de Juízo 100% digital (desmarcar_100 / remarcar_100_pos_aud).

O fake abaixo simula o comportamento do PJe na aba /retificar, conforme o probe:

  - toggle mat-slide-toggle[formcontrolname='juizoDigital'] com classe .mat-checked
  - confirmação em mat-expansion-panel com título + botões "Sim"/"Não"
  - clique no label inverte o estado SÓ depois da confirmação correta

Roda com:  python -m unittest tests.test_juizo_100_digital
"""
import io
import sys
import unittest
from unittest.mock import MagicMock, patch

from bianca.triagem import acoes

# O código imprime ✅/⚠️/❌; o console do Windows usa cp1252 e quebraria o teste.
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass


class Toggle100:
    """Estado do Juízo 100% digital + painéis de confirmação."""

    def __init__(self, marcado=True):
        self.marcado = marcado
        self.painel1_aberto = False   # "Tem certeza de que deseja retirar"
        self.painel2_aberto = False   # "Confirma a inclusão do movimento"
        self.confirmacao_aberta = False  # diálogo de Sim ao remarcar
        self.cliques_label = 0
        self.botoes_clicados = []

    @property
    def classe(self):
        return 'mat-slide-toggle mat-checked' if self.marcado else 'mat-slide-toggle'


class FakeDriver100:
    """Interpreta os scripts JS reais usados por acoes.py."""

    def __init__(self, toggle):
        self.t = toggle
        self.scripts = []
        self.current_window_handle = 'aba_detalhe'
        self.current_url = 'https://pje.trt2.jus.br/pjekz/processo/9028907/retificar'

    # --- _executar_js ---------------------------------------------------
    def executar_js(self, driver, script, *args):
        self.scripts.append(script)
        s = ' '.join(script.split())

        # _estado_toggle_100
        if "classList.contains('mat-checked') ? 'marcado'" in s:
            return 'marcado' if self.t.marcado else 'desmarcado'

        # _gatilho_toggle_100
        if 'label.mat-slide-toggle-label' in s and 'label.click()' in s:
            self.t.cliques_label += 1
            if self.t.marcado:
                self.t.painel1_aberto = True      # desmarcar -> painel 1
            else:
                self.t.confirmacao_aberta = True  # remarcar -> confirmação Sim
            return True

        # _clicar_botao_em_painel(titulo, botao)
        if 'mat-panel-title[contains' in s:
            titulo, alvo = args[0], args[1]
            if 'Tem certeza' in titulo:
                if not self.t.painel1_aberto:
                    return {'ok': False, 'erro': 'painel_ausente'}
                self.t.botoes_clicados.append((titulo, alvo))
                if alvo == 'Sim':
                    self.t.painel1_aberto = False
                    self.t.painel2_aberto = True
                return {'ok': True}
            if 'Confirma a inclus' in titulo:
                if not self.t.painel2_aberto:
                    return {'ok': False, 'erro': 'painel_ausente'}
                self.t.botoes_clicados.append((titulo, alvo))
                if alvo == 'Não':
                    self.t.painel2_aberto = False
                    self.t.marcado = False    # só agora desmarca
                return {'ok': True}
            return {'ok': False, 'erro': 'painel_ausente'}

        # _clicar_sim_confirmacao
        if 'pje-modal-juizo-digital' in s and 'btns.filter' in s:
            if getattr(self.t, 'confirmacao_aberta', False):
                self.t.botoes_clicados.append(('confirmacao', 'Sim'))
                self.t.confirmacao_aberta = False
                self.t.marcado = True
                return {'ok': True, 'tipo': 'mat-expansion-panel'}
            return {'ok': False}

        # _ir_para_step_caracteristicas
        if "aria-posinset='4'" in s:
            return True

        return True

    # --- API de driver usada por _abrir_nova_aba -------------------------
    def close(self):
        pass

    def switch_to(self):
        return MagicMock()


def _patch_ambiente(fake):
    return [
        patch.object(acoes, '_executar_js', side_effect=fake.executar_js),
        patch.object(acoes, '_abrir_nova_aba', return_value='aba_retificar'),
        patch.object(acoes.espera, 'assentar', return_value=None),
        # ate_js recebe a expressão pronta; avaliamos o estado real do toggle.
        patch.object(acoes.espera, 'ate_js', side_effect=lambda *a, **k: _ate_js_fake(fake, a)),
    ]


def _ate_js_fake(fake, args):
    """`espera.ate_js(driver, expressao, teto=...)` — sem args extras."""
    expr = args[1] if len(args) > 1 else ''
    expr = ' '.join(str(expr).split())
    if "!t.classList.contains('mat-checked')" in expr:
        return not fake.t.marcado
    if "t.classList.contains('mat-checked')" in expr:
        return fake.t.marcado
    return True


class TestDesmarcar100(unittest.TestCase):
    def _rodar(self, marcado=True):
        t = Toggle100(marcado=marcado)
        fake = FakeDriver100(t)
        patches = _patch_ambiente(fake)
        for p in patches:
            p.start()
        try:
            resultado = acoes.desmarcar_100(MagicMock(), '9028907')
        finally:
            for p in patches:
                p.stop()
        return t, resultado

    def test_desmarca_quando_marcado(self):
        """Fluxo completo: toggle -> Sim (painel 1) -> Não (painel 2)."""
        t, res = self._rodar(marcado=True)
        self.assertEqual(res, 'aba_retificar')
        self.assertFalse(t.marcado, 'toggle deveria ter terminado desmarcado')
        self.assertEqual(t.cliques_label, 1)
        titulos = [b[0] for b in t.botoes_clicados]
        self.assertTrue(any('Tem certeza' in x for x in titulos))
        self.assertTrue(any('Confirma a inclus' in x for x in titulos))

    def test_clica_sim_e_nao_nos_paineis_certos(self):
        """O painel 'Tem certeza' leva Sim; o de 'Confirma a inclusão' leva Não."""
        t, _ = self._rodar(marcado=True)
        por_titulo = {titulo: alvo for titulo, alvo in t.botoes_clicados}
        chave1 = [k for k in por_titulo if 'Tem certeza' in k][0]
        chave2 = [k for k in por_titulo if 'Confirma a inclus' in k][0]
        self.assertEqual(por_titulo[chave1], 'Sim')
        self.assertEqual(por_titulo[chave2], 'Não')

    def test_nao_mexe_quando_ja_desmarcado(self):
        """Já desmarcado: não clica no toggle nem abre painéis."""
        t, res = self._rodar(marcado=False)
        self.assertEqual(res, 'aba_retificar')
        self.assertEqual(t.cliques_label, 0)
        self.assertEqual(t.botoes_clicados, [])


class TestRemarcar100(unittest.TestCase):
    def _rodar(self, marcado=False):
        t = Toggle100(marcado=marcado)
        fake = FakeDriver100(t)
        patches = _patch_ambiente(fake)
        for p in patches:
            p.start()
        try:
            resultado = acoes.remarcar_100_pos_aud(MagicMock())
        finally:
            for p in patches:
                p.stop()
        return t, resultado

    def test_remarca_quando_desmarcado(self):
        t, res = self._rodar(marcado=False)
        self.assertTrue(res)
        self.assertTrue(t.marcado, 'toggle deveria ter terminado marcado')
        self.assertEqual(t.cliques_label, 1)

    def test_nao_mexe_quando_ja_marcado(self):
        t, res = self._rodar(marcado=True)
        self.assertTrue(res)
        self.assertEqual(t.cliques_label, 0)


class TestSequencia(unittest.TestCase):
    def test_desmarcar_e_remarcar_em_sequencia(self):
        """Desmarcar e depois remarcar deixa o toggle marcado (ida e volta)."""
        t = Toggle100(marcado=True)
        fake = FakeDriver100(t)
        patches = _patch_ambiente(fake)
        for p in patches:
            p.start()
        try:
            acoes.desmarcar_100(MagicMock(), '9028907')
            self.assertFalse(t.marcado, 'após desmarcar deveria estar desmarcado')
            ok = acoes.remarcar_100_pos_aud(MagicMock())
        finally:
            for p in patches:
                p.stop()
        self.assertTrue(ok)
        self.assertTrue(t.marcado, 'após remarcar deveria voltar a marcado')


if __name__ == '__main__':
    unittest.main()
