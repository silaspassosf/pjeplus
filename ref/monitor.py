"""Ferramentas de monitoramento e otimização para scripts de automação PJe.

Este módulo oferece uma ``MonitorSession`` que integra:

* coleta de seletores efetivamente utilizados;
* medições de tempo e identificação de chamadas lentas;
* contagem e análise de uso de funções externas (principalmente `Fix.py`);
* filtragem de logs para exibir apenas falhas críticas (sem ícones ou emojis);
* geração de relatórios detalhados a cada execução (JSON individual + histórico).

Além disso, expõe ``run_with_monitor`` para executar uma função sob monitoramento
com instrumentação automática das rotinas relevantes.
"""
from __future__ import annotations

import builtins
import json
import logging
import os
import sys
import time
from collections import defaultdict
from datetime import datetime
from functools import wraps
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence


# =============================================================================
# Estruturas básicas de coleta
# =============================================================================


class MonitorData:
    """Registra métricas coletadas durante a sessão."""

    def __init__(self, slow_threshold: float = 1.0, suppressed_sample_limit: int = 40) -> None:
        self.slow_threshold = slow_threshold
        self.selector_usage: Dict[str, set[str]] = defaultdict(set)
        self.call_stats: Dict[str, Dict[str, float]] = defaultdict(lambda: {"count": 0, "total": 0.0, "max": 0.0})
        self.call_details: List[Dict[str, Any]] = []
        self.external_stats: Dict[str, Dict[str, float]] = defaultdict(lambda: {"count": 0, "total": 0.0, "max": 0.0})
        self.errors: List[Dict[str, Any]] = []
        self.suppressed_total = 0
        self.suppressed_logs: List[str] = []
        self.suppressed_sample_limit = suppressed_sample_limit
        self.selector_results: Dict[str, List[Dict[str, Any]]] = defaultdict(list)  # ✨ NOVO: rastrear resultados

    def record_call(
        self,
        name: str,
        duration: float,
        metadata: Optional[Dict[str, Any]] = None,
        external: bool = False,
    ) -> None:
        stats = self.call_stats[name]
        stats["count"] += 1
        stats["total"] += duration
        stats["max"] = max(stats["max"], duration)

        detail: Dict[str, Any] = {
            "name": name,
            "duration_ms": round(duration * 1000, 3),
        }
        if metadata:
            detail["metadata"] = metadata
        if duration >= self.slow_threshold:
            detail["slow"] = True
        self.call_details.append(detail)
        if len(self.call_details) > 600:
            self.call_details.pop(0)

        if external:
            ext = self.external_stats[name]
            ext["count"] += 1
            ext["total"] += duration
            ext["max"] = max(ext["max"], duration)

    def record_selector(self, name: str, selector: str) -> None:
        if selector:
            self.selector_usage[name].add(selector)

    def record_error(self, source: str, message: Any, driver=None) -> None:
        """Registra erro e opcionalmente pausa para debug interativo"""
        erro_msg = str(message)
        self.errors.append(
            {
                "source": source,
                "message": erro_msg,
                "timestamp": datetime.now().isoformat(timespec="seconds"),
            }
        )
        
        # ✨ NOVO: Debug interativo
        if driver:
            try:
                from Fix.debug_interativo import on_erro_critico
                acao = on_erro_critico(driver, erro_msg, {"source": source})
                
                if acao == 'a':  # Abortar
                    raise KeyboardInterrupt("Debug interativo: Execução abortada pelo usuário")
                elif acao == 's':  # Skip
                    # Marcar para skip (pode ser tratado pelo caller)
                    self.errors[-1]['skip_requested'] = True
            except ImportError:
                pass  # Debug interativo não disponível

    def record_suppressed(self, message: str) -> None:
        self.suppressed_total += 1
        clean = message.strip()
        if clean and len(self.suppressed_logs) < self.suppressed_sample_limit:
            self.suppressed_logs.append(clean[:280])


class MonitorLogHandler(logging.Handler):
    """Handler que captura logs de erro e encaminha para o coletor."""

    def __init__(self, data: MonitorData) -> None:
        super().__init__(level=logging.ERROR)
        self._data = data

    def emit(self, record: logging.LogRecord) -> None:  # noqa: D401
        try:
            message = self.format(record)
        except Exception:  # pragma: no cover
            message = record.getMessage()
        self._data.record_error(record.name, message)


# =============================================================================
# Sessão de monitoramento
# =============================================================================


class MonitorSession:
    """Contexto que aplica instrumentação, coleta e gera relatório."""
    
    # ✨ NOVO: Referência ao driver para debug interativo
    _driver_ref: Optional[Any] = None

    FIX_FUNCTION_SPECS: Sequence[Dict[str, Any]] = (
        {"name": "esperar_elemento", "selector_index": 1, "external": True},
        {"name": "wait", "selector_index": 1, "external": True},
        {"name": "wait_for_visible", "selector_index": 1, "external": True},
        {"name": "wait_for_clickable", "selector_index": 1, "external": True},
        {"name": "safe_click", "selector_index": 1, "external": True},
        {"name": "buscar_seletor_robusto", "selector_index": 1, "external": True},
        {"name": "aplicar_filtro_100", "external": True},
        {"name": "criar_gigs", "external": True},
    )

    P2B_FUNCTION_SPECS: Sequence[Dict[str, Any]] = tuple(
        {"name": name}
        for name in (
            "executar_fluxo fluxo_prazo processar_processo_p2b_individual processar_processo_especifico_p2b "
            "iniciar_fluxo_robusto aplicar_filtro_xs_p2b obter_lista_processos_p2b"
        ).split()
    )

    ATOS_FUNCTION_SPECS: Sequence[Dict[str, Any]] = tuple(
        {"name": name}
        for name in (
            "selecionar_opcao_select fluxo_cls ato_judicial executar_visibilidade_sigilosos_se_necessario "
            "make_ato_wrapper ato_pesquisas idpj verificar_bloqueio_recente comunicacao_judicial "
            "make_comunicacao_wrapper mov mov_arquivar mov_exec mov_prazo mov_sob mov_fimsob "
            "visibilidade_sigilosos fluxo_principal callback_ato iniciar_fluxo_pec fluxo_sincrono_processo "
            "main debug_editor_completo substituir_link_por_clipboard_debug preencher_prazos_destinatarios "
            "selecionar_subtipo def_chip aplicar_visibilidade_ultimo_documento_sigiloso _selecionar_polo_ativo_atos "
            "_selecionar_polo_passivo_atos ato_meios ato_crda ato_crte ato_bloq ato_idpj ato_termoE ato_termoS "
            "ato_edital ato_sobrestamento ato_prov ato_180 ato_x90 ato_pesqliq_original ato_pesqliq ato_calc2 "
            "ato_meiosub ato_presc ato_fal ato_parcela ato_prev pec_bloqueio pec_decisao pec_idpj pec_editalidpj "
            "pec_editaldec pec_cpgeral pec_excluiargos pec_mddgeral pec_mddaud pec_editalaud"
        ).split()
    )

    def __init__(
        self,
        driver: Optional[Any] = None,  # ✨ NOVO: driver para debug
    ) -> None:
        self.script_name = script_name
        self.report_dir = report_dir
        self.data = MonitorData(slow_threshold)
        self.slow_threshold = slow_threshold
        self._driver_ref = driver  # ✨ NOVO
        self.report_dir = report_dir
        self.data = MonitorData(slow_threshold)
        self.slow_threshold = slow_threshold

        self._patched: List[tuple[Any, str, Callable[..., Any]]] = []
        self._logger_levels: List[tuple[logging.Logger, int]] = []
        self._log_handler: Optional[MonitorLogHandler] = None
        self._root_level: Optional[int] = None
        self._original_print: Optional[Callable[..., Any]] = None
        self._start_perf: Optional[float] = None
        self._end_perf: Optional[float] = None
        self._start_dt: Optional[datetime] = None
        self._end_dt: Optional[datetime] = None
        self._fix_module: Any = None

        self._emoji_tokens = ("✅", "❌", "⚠️", "⚠", "", "", "", "", "", "⏱️", "", "", "")
        self._critical_tokens = ("ERRO", "ERROR", "FALHA", "CRITICAL", "EXCEPTION", "TRACEBACK")

    def __enter__(self) -> "MonitorSession":
        self._start_perf = time.perf_counter()
        self._start_dt = datetime.now()
        self._configure_logging()
        self._filter_prints()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # noqa: D401
        self._restore()
        self._end_perf = time.perf_counter()
        self._end_dt = datetime.now()
        self._generate_report(exc_type, exc)

    def _configure_logging(self) -> None:
        root_logger = logging.getLogger()
        self._root_level = root_logger.level
        root_logger.setLevel(logging.ERROR)

        handler = MonitorLogHandler(self.data)
        handler.setFormatter(logging.Formatter("%(name)s - %(levelname)s - %(message)s"))
        root_logger.addHandler(handler)
        self._log_handler = handler

    def _filter_prints(self) -> None:
        if self._original_print is not None:
            return

        original_print = builtins.print
        critical_tokens = self._critical_tokens
        emoji_tokens = self._emoji_tokens
        data = self.data

        def filtered_print(*args: Any, **kwargs: Any) -> None:
            target_stream = kwargs.get("file") or sys.stdout
            message = " ".join(str(arg) for arg in args)
            normalized = message.upper()

            should_emit = target_stream is sys.stderr or any(token in normalized for token in critical_tokens)
            if should_emit:
                sanitized_args = [MonitorSession._strip_emojis(str(arg), emoji_tokens) for arg in args]
                original_print(*sanitized_args, **kwargs)
            else:
                data.record_suppressed(message)

        builtins.print = filtered_print
        self._original_print = original_print

    @staticmethod
    def _strip_emojis(text: str, tokens: Sequence[str]) -> str:
        result = text
        for token in tokens:
            result = result.replace(token, "")
        return result

    def patch_fix_module(self) -> Any:
        if self._fix_module is not None:
            return self._fix_module

        import Fix

        self._fix_module = Fix
        self._patch_module_functions(Fix, self.FIX_FUNCTION_SPECS)
        return Fix

    def attach_p2b(self, p2b_module: Any) -> None:
        fix_module = self.patch_fix_module()
        self._sync_fix_bindings(p2b_module, fix_module)
        self._patch_module_functions(p2b_module, self.P2B_FUNCTION_SPECS, module_label=p2b_module.__name__)

        logger = getattr(p2b_module, "logger", None)
        if isinstance(logger, logging.Logger):
            self._logger_levels.append((logger, logger.level))
            logger.setLevel(logging.ERROR)
            logger.propagate = True

    def attach_atos(self, atos_module: Any) -> None:
        fix_module = self.patch_fix_module()
        self._sync_fix_bindings(atos_module, fix_module)
        self._patch_module_functions(atos_module, self.ATOS_FUNCTION_SPECS, module_label=atos_module.__name__)

        logger = getattr(atos_module, "logger", None)
        if isinstance(logger, logging.Logger):
            self._logger_levels.append((logger, logger.level))
            logger.setLevel(logging.ERROR)
            logger.propagate = True

    def _sync_fix_bindings(self, target_module: Any, fix_module: Any) -> None:
        for spec in self.FIX_FUNCTION_SPECS:
            name = spec["name"]
            if hasattr(target_module, name) and hasattr(fix_module, name):
                original = getattr(target_module, name)
                patched = getattr(fix_module, name)
                if original is patched:
                    continue
                setattr(target_module, name, patched)
                self._patched.append((target_module, name, original))

    def _patch_module_functions(
        self,
        module: Any,
        specs: Sequence[Dict[str, Any]],
        module_label: Optional[str] = None,
    ) -> None:
        label_prefix = module_label or getattr(module, "__name__", "module")
        for spec in specs:
            name = spec.get("name")
            if not name or not hasattr(module, name):
                continue

            original = getattr(module, name)
            if getattr(original, "__monitor_wrapped__", False):
                continue

            label = spec.get("label") or f"{label_prefix}.{name}"
            wrapper = self._create_wrapper(
                original,
                label=label,
                selector_index=spec.get("selector_index"),
                selector_kw=spec.get("selector_kw"),
                external=spec.get("external", False),
            )
            setattr(module, name, wrapper)
            self._patched.append((module, name, original))

    def _create_wrapper(
        self,
        func: Callable[..., Any],
        *,
        label: str,
        selector_index: Optional[int] = None,
        selector_kw: Optional[str] = None,
        external: bool = False,
    ) -> Callable[..., Any]:
        data = self.data
        slow_threshold = self.slow_threshold

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            selector_value = self._extract_selector(args, kwargs, selector_index, selector_kw)
            start = time.perf_counter()
            success = False  # ✨ NOVO
            result = None
            try:
                result = func(*args, **kwargs)
                success = True  # ✨ NOVO
                return result
            exce# ✨ NOVO: Passar driver para debug interativo
                driver_ref = getattr(args[0] if args else None, '__class__', None)
                driver_obj = args[0] if args and hasattr(args[0], 'find_element') else None
                data.record_error(label, exc, driver=driver_obj
                success = False  # ✨ NOVO
                data.record_error(label, exc)
                raise
            finally:
                duration = time.perf_counter() - start
                metadata: Dict[str, Any] = {}
                if selector_value:
                    data.record_selector(label, selector_value)
                    metadata["selector"] = selector_value
                    # ✨ NOVO: Registrar resultado do seletor
                    data.selector_results[label].append({
                        "selector": selector_value,
                        "success": success,
                        "duration_ms": duration * 1000,
                        "timestamp": time.time()
                    })
                if duration >= slow_threshold:
                    metadata.setdefault("flags", []).append("slow")
                data.record_call(label, duration, metadata if metadata else None, external)

        wrapper.__monitor_wrapped__ = True  # type: ignore[attr-defined]
        wrapper.__monitor_original__ = func  # type: ignore[attr-defined]
        return wrapper

    @staticmethod
    def _extract_selector(
        args: Sequence[Any],
        kwargs: Dict[str, Any],
        selector_index: Optional[int],
        selector_kw: Optional[str],
    ) -> Optional[str]:
        candidate: Optional[Any] = None
        if selector_index is not None and selector_index < len(args):
            candidate = args[selector_index]
        if selector_kw and selector_kw in kwargs:
            candidate = kwargs[selector_kw]
        return candidate if isinstance(candidate, str) else None

    def wrap_callable(self, func: Callable[..., Any], label: Optional[str] = None) -> Callable[..., Any]:
        name = label or f"{func.__module__}.{func.__name__}"
        return self._create_wrapper(func, label=name)

    def _restore(self) -> None:
        for module, name, original in reversed(self._patched):
            try:
                setattr(module, name, original)
            except Exception:  # pragma: no cover
                pass
        self._patched.clear()

        for logger, level in self._logger_levels:
            logger.setLevel(level)
        self._logger_levels.clear()

        if self._log_handler:
            root_logger = logging.getLogger()
            root_logger.removeHandler(self._log_handler)
            self._log_handler = None
        if self._root_level is not None:
            logging.getLogger().setLevel(self._root_level)
            self._root_level = None

        if self._original_print is not None:
            builtins.print = self._original_print
            self._original_print = None

    def _generate_report(self, exc_type: Optional[type], exc: Optional[BaseException]) -> None:
        os.makedirs(self.report_dir, exist_ok=True)

        total_duration = 0.0
        if self._start_perf is not None and self._end_perf is not None:
            total_duration = self._end_perf - self._start_perf

        call_summary = {
            name: {
                "count": int(stats["count"]),
                "avg_ms": round((stats["total"] / stats["count"]) * 1000, 3) if stats["count"] else 0.0,
                "max_ms": round(stats["max"] * 1000, 3),
            }
            for name, stats in sorted(self.data.call_stats.items(), key=lambda item: item[0])
        }

        external_summary = {
            name: {
                "count": int(stats["count"]),
                "avg_ms": round((stats["total"] / stats["count"]) * 1000, 3) if stats["count"] else 0.0,
                "max_ms": round(stats["max"] * 1000, 3),
            }
            for name, stats in sorted(self.data.external_stats.items(), key=lambda item: item[0])
        }

        selectors = {
            name: sorted(values)
            for name, values in sorted(self.data.selector_usage.items(), key=lambda item: item[0])
        }

        slow_calls = [detail for detail in self.data.call_details if detail.get("slow")]
        slow_calls.sort(key=lambda detail: detail.get("duration_ms", 0.0), reverse=True)
        slow_calls = slow_calls[:25]

        report = {
            "script": self.script_name,
            "started_at": self._start_dt.isoformat() if self._start_dt else None,
            "finished_at": self._end_dt.isoformat() if self._end_dt else None,
            "duration_seconds": round(total_duration, 3),
            "summary": {
                "total_calls": sum(int(stats["count"]) for stats in self.data.call_stats.values()),
                "slow_calls": len(slow_calls),
                "suppressed_logs": self.data.suppressed_total,
                "errors": len(self.data.errors),
            },
            "calls": call_summary,
            "slow_calls": slow_calls,
            "selectors": selectors,
            "external_functions": external_summary,
            "errors": self.data.errors,
            "suppressed_log_samples": self.data.suppressed_logs,
            "selector_results": dict(self.data.selector_results),  # ✨ NOVO: incluir resultados
        }

        if exc_type:
            report["exception"] = {
                "type": exc_type.__name__,
                "message": str(exc) if exc else "",
            }

        filename = (
            f"{self.script_name}_{self._start_dt.strftime('%Y%m%d_%H%M%S')}.json"
            if self._start_dt
            else f"{self.script_name}.json"
        )
        report_path = os.path.join(self.report_dir, filename)

        with open(report_path, "w", encoding="utf-8") as fp:
            json.dump(report, fp, ensure_ascii=False, indent=2)

        self._update_history(report)
        self._feed_learning_system(report)  # ✨ NOVO: alimentar sistema de aprendizado

    def _feed_learning_system(self, report: Dict[str, Any]) -> None:
        """Alimenta sistema de aprendizado com resultados dos seletores"""
        try:
            from selector_learning import report_selector_result
            
            selector_results = report.get("selector_results", {})
            for label, results in selector_results.items():
                # Extrair contexto do label (ex: "prazo.loop_prazo" -> "prazo")
                parts = label.split(".")
                context = parts[0] if parts else "unknown"
                operation = ".".join(parts[1:]) if len(parts) > 1 else label
                
                for result in results:
                    report_selector_result(
                        context=context,
                        operation=operation,
                        selector=result.get("selector", ""),
                        success=result.get("success", False),
                        duration_ms=result.get("duration_ms")
                    )
        except ImportError:
            pass  # Sistema de aprendizado não disponível
        except Exception:
            pass  # Falha silenciosa para não quebrar monitor

    def _update_history(self, report: Dict[str, Any]) -> None:
        history_path = os.path.join(self.report_dir, "history.json")
        history: List[Dict[str, Any]] = []
        if os.path.exists(history_path):
            try:
                with open(history_path, "r", encoding="utf-8") as fp:
                    history = json.load(fp)
            except Exception:
                history = []

        history.append(
            {
                "script": report.get("script"),
                "started_at": report.get("started_at"),
                "duration_seconds": report.get("duration_seconds"),
                "slow_calls": report.get("summary", {}).get("slow_calls"),
                "errors": report.get("summary", {}).get("errors"),
            }
        )

        with open(history_path, "w", encoding="utf-8") as fp:
            json.dump(history[-120:], fp, ensure_ascii=False, indent=2)


def run_with_monitor(
    script_name: str,
    entry_callable: Callable[..., Any],
    *args: Any,
    monitor_targets: Optional[Iterable[Any]] = None,
    slow_threshold: float = 1.0,
    **kwargs: Any,
) -> Any:
    """Executa ``entry_callable`` sob monitoramento, aplicando instrumentação automática."""

    with MonitorSession(script_name, slow_threshold=slow_threshold) as session:
        targets = list(monitor_targets or [])
        for target in targets:
            name = getattr(target, "__name__", "")
            if name == "p2b":
                session.attach_p2b(target)
            elif name == "atos":
                session.attach_atos(target)

        monitored = session.wrap_callable(entry_callable)
        return monitored(*args, **kwargs)