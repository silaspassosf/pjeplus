"""Testes da telemetria de seletores (base para consolidar o catálogo do PJe).

Objetivo: garantir que a execução real REGISTRE qual seletor venceu, por fluxo,
para que a consolidação do catálogo seja empírica e não adivinhação.

Cobre:
  - registrar_resolucao grava JSONL com os campos canônicos
  - resolver() testa candidatos em ordem e registra o vencedor
  - Fix.espera.elemento/elementos emitem telemetria com o fluxo do chamador
  - desligar por ambiente (PJEPLUS_TELEMETRIA_SELETORES=0)
  - telemetria nunca derruba o fluxo (falha de escrita é engolida)
"""
import importlib
import json
import os
import shutil
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)


class BaseTel(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self._env = patch.dict(os.environ, {
            "PJEPLUS_LOG_DIR": self.tmp,
            "PJEPLUS_TELEMETRIA_SELETORES": "1",
        })
        self._env.start()
        import Fix.telemetria_seletores as tel
        importlib.reload(tel)
        self.tel = tel

    def tearDown(self):
        self._env.stop()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def registros(self):
        out = []
        for f in os.listdir(self.tmp):
            if f.endswith(".jsonl"):
                with open(os.path.join(self.tmp, f), encoding="utf-8") as fp:
                    out += [json.loads(l) for l in fp if l.strip()]
        return out


class TestRegistro(BaseTel):
    def test_grava_campos_canonicos(self):
        self.tel.registrar_resolucao("abrir_timeline", "pje-timeline", fluxo="mandado",
                                     origem="catalogo", ok=True, tentativas=2, ms=12.5)
        regs = self.registros()
        self.assertEqual(len(regs), 1)
        r = regs[0]
        self.assertEqual(r["acao"], "abrir_timeline")
        self.assertEqual(r["seletor"], "pje-timeline")
        self.assertEqual(r["fluxo"], "mandado")
        self.assertEqual(r["origem"], "catalogo")
        self.assertTrue(r["ok"])

    def test_tentativas_limitadas(self):
        self.tel.registrar_resolucao("x", "y", tentativas=50000)
        self.assertEqual(self.registros()[0]["tentativas"], 99)

    def test_desligado_nao_grava(self):
        with patch.dict(os.environ, {"PJEPLUS_TELEMETRIA_SELETORES": "0"}):
            importlib.reload(self.tel)
            self.tel.registrar_resolucao("a", "sel")
        self.assertEqual(self.registros(), [])

    def test_nunca_levanta_com_caminho_invalido(self):
        self.tel._DIR = "\x00invalido"
        self.tel.registrar_resolucao("a", "sel")  # não deve levantar


class TestResolver(BaseTel):
    def test_registra_vencedor(self):
        el = self.tel.resolver(None, "mandado", "abrir_timeline",
                               ["pje-timeline", "//pje-timeline", ".outro"],
                               testar=lambda s: object() if s == "//pje-timeline" else None)
        self.assertIsNotNone(el)
        r = self.registros()[0]
        self.assertEqual(r["seletor"], "//pje-timeline")
        self.assertEqual(r["tentativas"], 2)
        self.assertTrue(r["ok"])

    def test_falha_registra_candidatos(self):
        el = self.tel.resolver(None, "pec", "campo", [".a", ".b"], testar=lambda s: None)
        self.assertIsNone(el)
        r = self.registros()[0]
        self.assertFalse(r["ok"])
        self.assertEqual(r["candidatos"], [".a", ".b"])

    def test_aceita_testador_com_driver(self):
        def testar(driver, sel):
            return object() if sel == ".ok" else None
        el = self.tel.resolver(object(), "p2b", "acao", [".nao", ".ok"], testar=testar)
        self.assertIsNotNone(el)

    def test_resumo_vencedores(self):
        self.tel.registrar_resolucao("a", "sel_a", ok=True)
        self.tel.registrar_resolucao("b", "sel_b", ok=False)
        self.assertEqual(self.tel.resumo_vencedores(), {"a": "sel_a"})


class TestEsperaInstrumentada(BaseTel):
    def setUp(self):
        super().setUp()
        import Fix.espera as espera
        importlib.reload(espera)
        self.espera = espera

        class El:
            def is_displayed(self):
                return True

        espera._find_elements = lambda d, by, s: [El()]
        espera._dormir = lambda s: None

    def _rodar_de(self, modulo, seletor="a.tl-documento"):
        mod = types.ModuleType(modulo)
        mod.__dict__["espera"] = self.espera
        exec(compile(f"def rodar(d):\n    return espera.elemento(d, {seletor!r})\n",
                     f"<{modulo}>", "exec"), mod.__dict__)
        return mod.rodar(object())

    def test_captura_fluxo_mandado(self):
        self.assertIsNotNone(self._rodar_de("Mandado.apoio_fluxos"))
        r = self.registros()[0]
        self.assertEqual(r["fluxo"], "mandado")
        self.assertEqual(r["seletor"], "a.tl-documento")
        self.assertEqual(r["origem"], "espera")

    def test_captura_fluxo_p2b_e_pec(self):
        self._rodar_de("Prazo.loop_lote", "span.total-registros")
        self._rodar_de("PEC.carta_execucao", "li.tl-item-container")
        fluxos = {r["fluxo"] for r in self.registros()}
        self.assertIn("p2b", fluxos)
        self.assertIn("pec", fluxos)

    def test_deduplica_repeticao(self):
        for _ in range(5):
            self._rodar_de("Mandado.apoio_fluxos", "a.tl-documento")
        self.assertEqual(len(self.registros()), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
