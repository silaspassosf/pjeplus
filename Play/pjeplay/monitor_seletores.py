# -*- coding: utf-8 -*-
"""pjeplay.monitor_seletores — Monitor de assertividade de seletores e detector de fallbacks.

Intercepta helpers de busca, clique e formulário para registrar exatamente qual seletor
funcionou (HIT) ou falhou (MISS) em cada ação, o chamador exato (arquivo:linha) e o tempo
gasto. Gera estatísticas para guiar a faxina de fallbacks desnecessários.
"""
import inspect
import json
import os
import sys
import time
from collections import defaultdict

HELPERS_ALVO = {
    "Fix.core": [
        "esperar_elemento",
        "aguardar_e_clicar",
        "safe_click",
        "click_headless_safe",
        "preencher_campo",
        "selecionar_opcao",
        "wait_for_visible",
        "wait_for_clickable",
        "aguardar_renderizacao_nativa",
    ],
    "Fix.browser_suporte": [
        "click_headless_safe",
        "safe_click_no_scroll",
    ],
    "Fix.espera": [
        "elemento",
        "elementos",
        "ate_aparecer",
    ],
}

_MODULOS_IGNORADOS = (
    "pjeplay",
    "Fix" + os.sep + "core",
    "Fix/core",
    "Fix" + os.sep + "browser_suporte",
    "Fix/browser_suporte",
    "Fix" + os.sep + "espera",
    "Fix/espera",
    "Fix" + os.sep + "facade_publica",
    "Fix/facade_publica",
    "Fix" + os.sep + "utils",
    "Fix/utils",
    "contextlib",
)


class MonitorSeletores:
    """Monitor em tempo de execução para registrar assertividade de seletores."""

    def __init__(self, raiz_projeto=None, verbose=True):
        self.raiz = raiz_projeto or os.getcwd()
        self.verbose = verbose
        self.registros = []
        self._originais = []
        self.ativo = False

    def _obter_chamador(self):
        """Identifica o primeiro frame na stack fora dos shims e helpers internos."""
        frame = sys._getframe(2)
        while frame:
            caminho = frame.f_code.co_filename
            ignorar = any(mod in caminho for mod in _MODULOS_IGNORADOS)
            if not ignorar:
                try:
                    rel = os.path.relpath(caminho, self.raiz)
                except Exception:
                    rel = caminho
                return f"{rel}:{frame.f_lineno} ({frame.f_code.co_name})"
            frame = frame.f_back
        return "desconhecido"

    def _extrair_seletor(self, fn_nome, args, kwargs):
        """Extrai o seletor ou alvo a partir dos argumentos da chamada."""
        if "seletor" in kwargs:
            return str(kwargs["seletor"])
        if "selector" in kwargs:
            return str(kwargs["selector"])
        if "seletor_dropdown" in kwargs:
            opt = kwargs.get("texto_opcao", "")
            return f"{kwargs['seletor_dropdown']} -> '{opt}'"

        if len(args) > 1:
            val = args[1]
            if fn_nome == "selecionar_opcao" and len(args) > 2:
                return f"{val} -> '{args[2]}'"
            if isinstance(val, (str, list, tuple)):
                return str(val)
            # Pode ser um Elemento direto
            if hasattr(val, "tag_name") or hasattr(val, "_handle"):
                return "<ElementoDOM>"
        return None

    def ativar(self):
        """Instrumenta os helpers alvo substituindo-os por wrappers de monitoramento."""
        import importlib

        self.ativo = True
        for mod_nome, funcoes in HELPERS_ALVO.items():
            try:
                mod = sys.modules.get(mod_nome) or importlib.import_module(mod_nome)
            except Exception:
                continue
            for fn_nome in funcoes:
                fn_orig = getattr(mod, fn_nome, None)
                if fn_orig is None or getattr(fn_orig, "_monitorado_seletor", False):
                    continue
                envolvido = self._criar_wrapper(mod_nome, fn_nome, fn_orig)
                setattr(mod, fn_nome, envolvido)
                self._originais.append((mod, fn_nome, fn_orig))

    def desativar(self):
        """Restaura as funções originais."""
        self.ativo = False
        for mod, fn_nome, fn_orig in self._originais:
            setattr(mod, fn_nome, fn_orig)
        self._originais.clear()

    def _criar_wrapper(self, mod_nome, fn_nome, fn_orig):
        def wrapper(*args, **kwargs):
            if not self.ativo:
                return fn_orig(*args, **kwargs)

            seletor = self._extrair_seletor(fn_nome, args, kwargs)
            chamador = self._obter_chamador()
            t0 = time.perf_counter()
            sucesso = False
            erro = None

            try:
                res = fn_orig(*args, **kwargs)
                sucesso = res is not False and res is not None
                return res
            except Exception as e:
                sucesso = False
                erro = f"{type(e).__name__}: {e}"
                raise
            finally:
                duracao_ms = round((time.perf_counter() - t0) * 1000, 1)
                if seletor and seletor != "<ElementoDOM>":
                    status = "HIT" if sucesso else "MISS"
                    reg = {
                        "funcao": f"{mod_nome}.{fn_nome}",
                        "seletor": seletor,
                        "chamador": chamador,
                        "sucesso": sucesso,
                        "duracao_ms": duracao_ms,
                        "erro": erro,
                    }
                    self.registros.append(reg)

                    if self.verbose:
                        marcador = "[SEL OK]" if sucesso else "[SEL XX]"
                        # Encurta seletor se for muito longo no log do console
                        sel_disp = (seletor[:60] + "...") if len(seletor) > 63 else seletor
                        print(f"  {marcador} {chamador} | {fn_nome} -> {sel_disp} ({duracao_ms}ms)")

        wrapper._monitorado_seletor = True
        wrapper.__name__ = getattr(fn_orig, "__name__", fn_nome)
        return wrapper

    def relatorio(self):
        """Analisa os registros e gera diagnóstico completo de fallbacks."""
        por_chamador = defaultdict(list)
        for r in self.registros:
            por_chamador[r["chamador"]].append(r)

        candidatos_limpeza = []
        seletores_estaveis = []
        tempo_desperdicado_ms = 0.0

        for chamador, chamadas in por_chamador.items():
            seletores_vistos = list(dict.fromkeys(c["seletor"] for c in chamadas))
            tempo_miss_chamador = sum(c["duracao_ms"] for c in chamadas if not c["sucesso"])
            tempo_desperdicado_ms += tempo_miss_chamador

            if len(seletores_vistos) > 1:
                # O chamador tentou mais de um seletor -> evidência de fallback
                vencedores = list(dict.fromkeys(
                    c["seletor"] for c in chamadas if c["sucesso"]
                ))
                eliminaveis = [s for s in seletores_vistos if s not in vencedores]
                candidatos_limpeza.append({
                    "chamador": chamador,
                    "vencedores_efetivos": vencedores,
                    "eliminaveis_falharam": eliminaveis,
                    "total_tentativas": len(chamadas),
                    "tempo_perdido_ms": round(tempo_miss_chamador, 1),
                })
            else:
                sel = seletores_vistos[0]
                hits = sum(1 for c in chamadas if c["sucesso"])
                total = len(chamadas)
                seletores_estaveis.append({
                    "chamador": chamador,
                    "seletor": sel,
                    "acertos": hits,
                    "total": total,
                    "taxa": f"{round((hits / total) * 100, 1)}%",
                    "tempo_medio_ms": round(sum(c["duracao_ms"] for c in chamadas) / total, 1),
                })

        total_acoes = len(self.registros)
        total_hits = sum(1 for r in self.registros if r["sucesso"])
        total_miss = total_acoes - total_hits

        return {
            "resumo": {
                "total_acoes": total_acoes,
                "total_hits": total_hits,
                "total_miss": total_miss,
                "tempo_desperdicado_segundos": round(tempo_desperdicado_ms / 1000.0, 2),
                "locais_com_fallback": len(candidatos_limpeza),
                "locais_estaveis": len(seletores_estaveis),
            },
            "candidatos_limpeza_fallbacks": candidatos_limpeza,
            "seletores_estaveis": seletores_estaveis,
        }

    def imprimir_resumo(self):
        """Exibe o resumo consolidado de assertividade e fallbacks."""
        diag = self.relatorio()
        r = diag["resumo"]
        print("\n=== MONITOR DE SELETORES E FALLBACKS ===")
        print(f"  Total de ações:               {r['total_acoes']}")
        print(f"  Acertos (HIT):                {r['total_hits']}")
        print(f"  Falhas (MISS):                {r['total_miss']}")
        print(f"  Tempo perdido em MISS:        {r['tempo_desperdicado_segundos']}s")
        print(f"  Locais com Fallback:          {r['locais_com_fallback']}")

        if diag["candidatos_limpeza_fallbacks"]:
            print("\n  🚨 CANDIDATOS A FAXINA (Múltiplos seletores testados):")
            for c in diag["candidatos_limpeza_fallbacks"]:
                print(f"    - Chamador: {c['chamador']}")
                if c["vencedores_efetivos"]:
                    print(f"      ✓ VENCEDOR:   {', '.join(c['vencedores_efetivos'])}")
                if c["eliminaveis_falharam"]:
                    print(f"      ✗ ELIMINÁVEL: {', '.join(c['eliminaveis_falharam'])}")
                print(f"      (Tentativas: {c['total_tentativas']} | Tempo perdido: {c['tempo_perdido_ms']}ms)")

    def salvar(self, destino_json):
        """Salva o relatório em formato JSON."""
        dados = self.relatorio()
        with open(destino_json, "w", encoding="utf-8") as f:
            json.dump(dados, f, indent=2, ensure_ascii=False)
        return destino_json
