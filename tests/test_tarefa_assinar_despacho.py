"""Regressão: caminho definido pela tarefa lida em /detalhe.

Caso real (log x_PC_Visible_20261023_160419.log): em /detalhe o botão de tarefa
mostrava "Assinar despacho". abrir_tarefa_processo devolvia (True, True), mas o
chamador só encerrava se a URL tivesse mudado — como seguia em /detalhe, o CLS
ia para "Navegação para Conclusão ao Magistrado" e ficava ~28s tentando clicar
em telas que não abriram.

REGRA DO PROJETO (o gigs-plugin é só referência de leitura, não a regra):
  tarefa "Assinar <ato>"  -> FINALIZA. Não movimenta, não minuta.
  tarefa "Elaborar <ato>" -> PROSSEGUE a partir das ações da URL /minutar:
                             modelo, descrição, sigilo... sem movimentar.
  outra tarefa            -> caminho normal (abrir e concluir).

Tarefa é o nome do botão em /detalhe; /minutar e /assinar são URLs.
Não existe tarefa chamada "Minutar" — em /detalhe ela nunca seria detectada.

Para o wrapper (atos/judicial_fluxo.py:356), ja_estava_estado_final=True
encerra o ato; False faz seguir para descrição e modelo.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import atos.judicial_navegacao as navegacao
import atos.judicial_fluxo as fluxo


class El:
    def __init__(self, texto="", attrs=None):
        self.text = texto
        self._attrs = attrs or {}

    def get_attribute(self, nome):
        return self._attrs.get(nome)

    def click(self):
        return True


class Driver:
    def __init__(self, url="https://pje.trt2.jus.br/pjekz/processo/1/detalhe"):
        self.current_url = url
        self.current_window_handle = "h1"

    def switch_to(self):
        class S:
            def window(self, h):
                pass
        return S()


class BaseTarefa(unittest.TestCase):
    def setUp(self):
        self._orig = (navegacao.aguardar_e_clicar, navegacao.espera.elemento,
                      navegacao.safe_click)
        self._cliques = []

    def tearDown(self):
        (navegacao.aguardar_e_clicar, navegacao.espera.elemento,
         navegacao.safe_click) = self._orig

    def _montar(self, nome_tarefa, url_apos_clique=None):
        botao = El("abrir")

        def fake_aguardar(driver, seletor, **kw):
            return botao

        def fake_elemento(driver, seletor, **kw):
            return El(nome_tarefa)

        def fake_click(driver, el):
            self._cliques.append(el)
            if url_apos_clique:
                driver.current_url = url_apos_clique
            return True

        navegacao.aguardar_e_clicar = fake_aguardar
        navegacao.espera.elemento = fake_elemento
        navegacao.safe_click = fake_click


class TestTarefaAssinar(BaseTarefa):
    """Assinar = finaliza."""

    def test_assinar_finaliza_sem_clicar(self):
        self._montar("Assinar despacho")
        d = Driver()
        sucesso, estado_final = navegacao.abrir_tarefa_processo(d)
        self.assertTrue(sucesso)
        self.assertTrue(estado_final)
        self.assertEqual(d.pje_tarefa_pronta, "assinar")
        self.assertEqual(self._cliques, [], "não deveria clicar em tarefa já assinada")

    def test_assinar_variantes(self):
        for nome in ("Assinar decisão", "Assinar sentença",
                     "Assinar expedientes e comunicações - magistrado"):
            self._montar(nome)
            d = Driver()
            navegacao.abrir_tarefa_processo(d)
            self.assertEqual(d.pje_tarefa_pronta, "assinar", nome)
            self.assertEqual(self._cliques, [], nome)

    def test_assinar_nao_movimenta(self):
        self._montar("Assinar despacho")
        d = Driver()
        navegacao.abrir_tarefa_processo(d)
        self.assertIn("/detalhe", d.current_url, "URL não deveria mudar")


class TestTarefaElaborar(BaseTarefa):
    """Elaborar = prossegue nas ações da URL /minutar, sem movimentar."""

    def test_elaborar_marca_sem_finalizar(self):
        self._montar("Elaborar decisão",
                     url_apos_clique="https://pje.trt2.jus.br/pjekz/processo/1/minutar")
        d = Driver()
        sucesso, estado_final = navegacao.abrir_tarefa_processo(d)
        self.assertTrue(sucesso)
        self.assertEqual(d.pje_tarefa_pronta, "elaborar",
                         "elaborar NÃO é estado final: precisa seguir para modelo/descrição")
        self.assertIn("/minutar", d.current_url)

    def test_elaborar_variantes(self):
        for nome in ("Elaborar sentença", "Elaborar despacho"):
            self._montar(nome)
            d = Driver()
            navegacao.abrir_tarefa_processo(d)
            self.assertEqual(d.pje_tarefa_pronta, "elaborar", nome)


class TestTarefaComum(BaseTarefa):
    def test_tarefa_comum_nao_marca(self):
        self._montar("Analisar", url_apos_clique="https://x/conclusao")
        d = Driver()
        navegacao.abrir_tarefa_processo(d)
        self.assertIsNone(d.pje_tarefa_pronta)
        self.assertEqual(len(self._cliques), 1)

    def test_flag_reseta_entre_processos(self):
        """Processo assinado não pode contaminar o próximo."""
        self._montar("Assinar despacho")
        d = Driver()
        navegacao.abrir_tarefa_processo(d)
        self.assertEqual(d.pje_tarefa_pronta, "assinar")

        self._montar("Analisar", url_apos_clique="https://x/conclusao")
        navegacao.abrir_tarefa_processo(d)
        self.assertIsNone(d.pje_tarefa_pronta)

    def test_nao_existe_tarefa_minutar(self):
        """'Minutar' é URL, não tarefa: não deve ser tratado como ato pronto."""
        self._montar("Minutar despacho")  # nome inexistente no PJe
        d = Driver()
        navegacao.abrir_tarefa_processo(d)
        self.assertIsNone(d.pje_tarefa_pronta,
                          "'minutar' não é tarefa — não deve marcar ato pronto")


class TestEstadoUrlMinutar(unittest.TestCase):
    """Em /minutar o CLS deve SEGUIR para as ações de minuta, não encerrar."""

    def test_estado_minutar_nao_finaliza(self):
        orig = fluxo.verificar_estado_atual
        try:
            fluxo.verificar_estado_atual = lambda drv: 'minutar'
            d = Driver("https://pje.trt2.jus.br/pjekz/processo/1/minutar")
            res = fluxo.fluxo_cls(d, 'Despacho')
            sucesso, ja_final = res if isinstance(res, tuple) else (res, None)
            self.assertTrue(sucesso)
            self.assertFalse(ja_final,
                             "/minutar não é estado final: o wrapper precisa "
                             "preencher descrição e modelo")
        finally:
            fluxo.verificar_estado_atual = orig

    def test_estado_assinar_finaliza(self):
        orig = fluxo.verificar_estado_atual
        try:
            fluxo.verificar_estado_atual = lambda drv: 'assinar'
            d = Driver("https://pje.trt2.jus.br/pjekz/processo/1/assinar")
            res = fluxo.fluxo_cls(d, 'Despacho')
            sucesso, ja_final = res if isinstance(res, tuple) else (res, None)
            self.assertTrue(sucesso)
            self.assertTrue(ja_final, "/assinar encerra o ato")
        finally:
            fluxo.verificar_estado_atual = orig


if __name__ == "__main__":
    unittest.main(verbosity=2)
