"""Instrumentação para comparar os dois backends de forma honesta.

O ponto cego de uma migração é atribuir ao motor novo um ganho que veio de ter
reescrito o código. Este módulo mede as duas coisas separadamente:

- `tempo_morto`: soma dos `time.sleep()` — some ao reescrever, em qualquer motor;
- `tempo_helper`: tempo dentro dos helpers de `Fix/` — esse sim é do motor.

Funciona idêntico no Selenium e no Playwright, porque instrumenta os mesmos
helpers que os dois backends atravessam.

    from pjeplay import medicao

    with medicao.sessao("p2b-selenium") as m:
        with m.etapa("abrir lista"):
            ...
    m.salvar("baseline-selenium.json")

    medicao.comparar("baseline-selenium.json", "baseline-playwright.json")
"""
import contextlib
import json
import logging
import time

logger = logging.getLogger("pjeplay")

HELPERS = {
    "Fix.core": [
        "aguardar_renderizacao_nativa", "esperar_elemento", "aguardar_e_clicar",
        "safe_click", "preencher_campo", "selecionar_opcao", "esperar_url_conter",
        "wait_for_page_load", "wait_for_visible", "wait_for_clickable",
    ],
    "Fix.browser_suporte": [
        "click_headless_safe", "trocar_para_nova_aba", "aguardar_nova_aba",
        "forcar_fechamento_abas_extras", "validar_conexao_driver",
    ],
    # As esperas que substituíram os sleeps: é onde se vê o ganho por motor.
    "Fix.espera": [
        "assentar", "ate_aparecer", "ate_sumir", "ate_habilitar",
        "ate_desabilitar", "ate_texto", "ate_js", "pausa",
    ],
}

# Em Selenium `assentar` dorme o teto inteiro; em Playwright retorna quando a
# tela aquieta. A diferença entre as duas medições é o ganho atribuível ao
# motor — não à reescrita.
ESPERAS = ("assentar", "ate_aparecer", "ate_sumir", "ate_habilitar",
           "ate_desabilitar", "ate_texto", "ate_js", "pausa")


class Medicao:
    def __init__(self, nome, backend="desconhecido"):
        self.nome = nome
        self.backend = backend
        self.inicio = None
        self.total = 0.0
        self.etapas = []
        self.chamadas = {}
        self.tempo_morto = 0.0
        self.qtd_sleeps = 0
        self._restaurar = []
        self._sleep_original = None

    # -- coleta -----------------------------------------------------------

    @contextlib.contextmanager
    def etapa(self, nome):
        t0 = time.perf_counter()
        erro = None
        try:
            yield
        except Exception as e:
            erro = f"{type(e).__name__}: {e}"
            raise
        finally:
            self.etapas.append({
                "nome": nome,
                "segundos": round(time.perf_counter() - t0, 3),
                "erro": erro,
            })

    def _contar(self, chave, segundos, ok):
        reg = self.chamadas.setdefault(
            chave, {"n": 0, "segundos": 0.0, "falhas": 0})
        reg["n"] += 1
        reg["segundos"] = round(reg["segundos"] + segundos, 3)
        if not ok:
            reg["falhas"] += 1

    # -- instrumentação ---------------------------------------------------

    def observar_sleeps(self):
        """Contabiliza todo `time.sleep()` como tempo morto."""
        if self._sleep_original is not None:
            return
        self._sleep_original = time.sleep

        def sleep_medido(segundos):
            self.tempo_morto = round(self.tempo_morto + float(segundos), 3)
            self.qtd_sleeps += 1
            self._sleep_original(segundos)

        time.sleep = sleep_medido

    def observar_helpers(self):
        """Envolve os helpers de `Fix/` para medir tempo e chamadas.

        Os dois backends passam por estes mesmos nomes, então a comparação é
        maçã com maçã.
        """
        import importlib

        for modulo, nomes in HELPERS.items():
            try:
                mod = importlib.import_module(modulo)
            except Exception:
                continue
            for nome in nomes:
                alvo = getattr(mod, nome, None)
                if alvo is None or getattr(alvo, "_medido", False):
                    continue
                setattr(mod, nome, self._envolver(f"{modulo}.{nome}", alvo))
                self._restaurar.append((mod, nome, alvo))

    def _envolver(self, chave, fn):
        def medido(*args, **kwargs):
            t0 = time.perf_counter()
            ok = True
            try:
                resultado = fn(*args, **kwargs)
                ok = resultado is not False and resultado is not None
                return resultado
            except Exception:
                ok = False
                raise
            finally:
                self._contar(chave, time.perf_counter() - t0, ok)
        medido._medido = True
        medido.__name__ = getattr(fn, "__name__", "medido")
        return medido

    def restaurar(self):
        if self._sleep_original is not None:
            time.sleep = self._sleep_original
            self._sleep_original = None
        for mod, nome, original in self._restaurar:
            setattr(mod, nome, original)
        self._restaurar.clear()

    # -- saída ------------------------------------------------------------

    def relatorio(self):
        tempo_helper = round(sum(c["segundos"] for c in self.chamadas.values()), 3)
        espera = {k: v for k, v in self.chamadas.items()
                  if k.rsplit(".", 1)[-1] in ESPERAS}
        return {
            "nome": self.nome,
            "backend": self.backend,
            "total": round(self.total, 3),
            "tempo_morto": self.tempo_morto,
            "qtd_sleeps": self.qtd_sleeps,
            "tempo_helper": tempo_helper,
            "chamadas_helper": sum(c["n"] for c in self.chamadas.values()),
            "tempo_espera": round(sum(c["segundos"] for c in espera.values()), 3),
            "chamadas_espera": sum(c["n"] for c in espera.values()),
            "etapas": self.etapas,
            "por_helper": dict(sorted(
                self.chamadas.items(), key=lambda kv: -kv[1]["segundos"])),
        }

    def salvar(self, caminho):
        with open(caminho, "w", encoding="utf-8") as f:
            json.dump(self.relatorio(), f, indent=2, ensure_ascii=False)
        return caminho

    def imprimir(self):
        r = self.relatorio()
        print(f"\n=== {r['nome']} ({r['backend']}) ===")
        print(f"  total          {r['total']:8.2f}s")
        print(f"  em helpers     {r['tempo_helper']:8.2f}s  "
              f"({r['chamadas_helper']} chamadas)")
        print(f"  tempo morto    {r['tempo_morto']:8.2f}s  "
              f"({r['qtd_sleeps']} sleeps)  <- some ao reescrever, nao e do motor")
        if r["etapas"]:
            print("  etapas:")
            for e in r["etapas"]:
                marca = "  " if not e["erro"] else " X"
                print(f"   {marca} {e['segundos']:7.2f}s  {e['nome']}")
        if r["por_helper"]:
            print("  helpers mais caros:")
            for nome, c in list(r["por_helper"].items())[:8]:
                print(f"      {c['segundos']:7.2f}s  {c['n']:4d}x  "
                      f"{nome.split('.')[-1]}  ({c['falhas']} falhas)")


@contextlib.contextmanager
def sessao(nome, backend=None, sleeps=True, helpers=True):
    """Mede um bloco inteiro, instrumentando sleeps e helpers de `Fix/`."""
    if backend is None:
        backend = "playwright" if _tem_playwright() else "selenium"
    m = Medicao(nome, backend)
    if sleeps:
        m.observar_sleeps()
    if helpers:
        m.observar_helpers()
    m.inicio = time.perf_counter()
    try:
        yield m
    finally:
        m.total = time.perf_counter() - m.inicio
        m.restaurar()


def _tem_playwright():
    import sys
    mod = sys.modules.get("selenium.webdriver.remote.webdriver")
    return bool(mod and getattr(mod.WebDriver, "__module__", "").startswith("pjeplay"))


# -- tracing ----------------------------------------------------------------

def iniciar_trace(driver, nome="pjeplay"):
    """Liga o tracing do Playwright (snapshot de DOM, rede e console por ação)."""
    contexto = getattr(driver, "context", None)
    tracing = getattr(contexto, "tracing", None)
    if tracing is None:
        return False
    tracing.start(name=nome, screenshots=True, snapshots=True, sources=True)
    return True


def finalizar_trace(driver, caminho="trace.zip"):
    contexto = getattr(driver, "context", None)
    tracing = getattr(contexto, "tracing", None)
    if tracing is None:
        return None
    try:
        tracing.stop(path=caminho)
        logger.info("trace salvo em %s (abra com: playwright show-trace %s)",
                    caminho, caminho)
        return caminho
    except Exception as e:
        logger.warning("finalizar_trace: %s", e)
        return None


# -- comparação -------------------------------------------------------------

def comparar(caminho_a, caminho_b):
    """Compara dois relatórios e separa o ganho do motor do ganho da reescrita."""
    with open(caminho_a, encoding="utf-8") as f:
        a = json.load(f)
    with open(caminho_b, encoding="utf-8") as f:
        b = json.load(f)

    def linha(rotulo, va, vb):
        delta = vb - va
        pct = (delta / va * 100) if va else 0.0
        print(f"  {rotulo:<16}{va:8.2f}s -> {vb:8.2f}s   {delta:+8.2f}s ({pct:+.0f}%)")

    print(f"\n=== {a['nome']} ({a['backend']})  vs  {b['nome']} ({b['backend']}) ===")
    linha("total", a["total"], b["total"])
    linha("em helpers", a["tempo_helper"], b["tempo_helper"])
    linha("em esperas", a.get("tempo_espera", 0), b.get("tempo_espera", 0))
    linha("tempo morto", a["tempo_morto"], b["tempo_morto"])

    # As esperas rodam o mesmo código nos dois lados — a diferença ali é só do
    # motor. Os sleeps crus que sobraram somem em qualquer motor: é reescrita.
    ganho_espera = a.get("tempo_espera", 0) - b.get("tempo_espera", 0)
    ganho_outros = ((a["tempo_helper"] - a.get("tempo_espera", 0))
                    - (b["tempo_helper"] - b.get("tempo_espera", 0)))
    ganho_motor = ganho_espera + ganho_outros
    ganho_reescrita = a["tempo_morto"] - b["tempo_morto"]
    total = ganho_motor + ganho_reescrita

    print("\n  atribuicao do ganho:")
    print(f"    motor: esperas      {ganho_espera:+8.2f}s")
    print(f"    motor: demais       {ganho_outros:+8.2f}s")
    print(f"    reescrita (sleeps)  {ganho_reescrita:+8.2f}s")
    if abs(total) > 0.01:
        print(f"    -> {ganho_motor / total * 100:.0f}% do ganho e do Playwright")
    return {"motor": round(ganho_motor, 3), "reescrita": round(ganho_reescrita, 3),
            "esperas": round(ganho_espera, 3)}
