"""bianca - Triagem + DOM Standalone.
Entry point for the bianca module. Provides terminal menu and orchestrates
Triagem Inicial and Dom Eletronico flows.
"""
import sys
import logging
import traceback
from datetime import datetime
from pathlib import Path

# Add parent to path so 'bianca' package is importable
# (when running as 'py bianca/main.py' from project root)
_bianca_dir = Path(__file__).resolve().parent
_parent = _bianca_dir.parent
if str(_parent) not in sys.path:
    sys.path.insert(0, str(_parent))

from bianca.driver import criar_driver_e_fazer_login
from bianca.utils import logger


class TeeOutput:
    """Duplicates stdout to a log file while preserving terminal output."""

    def __init__(self, log_path: str) -> None:
        self.terminal = sys.stdout
        self.log_file = open(log_path, "a", encoding="utf-8")

    def write(self, data: str) -> None:
        self.terminal.write(data)
        self.log_file.write(data)
        self.log_file.flush()

    def flush(self) -> None:
        self.terminal.flush()
        self.log_file.flush()

    def close(self) -> None:
        self.log_file.close()
        sys.stdout = self.terminal


def _setup_logging(log_path: str) -> tuple:
    """Configure bianca logger with file and console handlers."""
    bianca_logger = logging.getLogger("bianca")
    bianca_logger.setLevel(logging.DEBUG)

    # Remove pre-existing handlers
    for h in bianca_logger.handlers[:]:
        bianca_logger.removeHandler(h)

    fh = logging.FileHandler(log_path, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(
        "[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    ))
    bianca_logger.addHandler(fh)

    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter("[%(name)s] %(message)s"))
    bianca_logger.addHandler(ch)

    # Suppress noisy third-party loggers
    logging.getLogger("urllib3.connectionpool").disabled = True
    return fh, ch


def executar_triagem(driver):
    """Wrapper that calls triagem_engine.run_triagem and prints results."""
    from bianca.triagem_engine import run_triagem

    print("\n--- Executando Triagem Inicial ---")
    resultado = run_triagem(driver)

    if resultado is None:
        print("run_triagem retornou None. Fluxo nao concluido.")
        return {"sucesso": False}

    processados = resultado.get("processados", 0)
    total = resultado.get("total", "?")
    sucesso = resultado.get("sucesso_count", "?")
    print(f"Triagem: {processados} processados / {total} total / {sucesso} sucesso")
    return resultado


def executar_dom(driver):
    """Wrapper that calls dom_engine.run_dom and prints results."""
    from bianca.dom_engine import run_dom

    print("\n--- Executando DOM Eletronico ---")
    resultado = run_dom(driver)

    if resultado is None:
        print("run_dom retornou None. Fluxo nao concluido.")
        return {"sucesso": False}

    total = resultado.get("total", "?")
    print(f"DOM: {total} processos analisados")
    return resultado


def main():
    """Main entry point. Shows menu, creates driver, dispatches flow."""
    # Setup log directory and TeeOutput
    log_dir = Path(__file__).resolve().parent / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = log_dir / f"bianca_{timestamp}.log"

    tee = TeeOutput(str(log_path))
    sys.stdout = tee
    fh, ch = _setup_logging(str(log_path))

    logger.info("Bianca iniciado. Log: %s", log_path)
    print()

    # Estatisticas acumuladas da sessao
    stats = {
        "triagem": {"processados": 0, "sucesso": 0, "falha": 0},
        "dom": {"processados": 0},
    }
    inicio_global = datetime.now()

    try:
        while True:
            print("=" * 60)
            print("BIANCA -- TRIAGEM + DOM")
            print("=" * 60)
            print("T - Triagem Inicial")
            print("D - Dom Eletronico")
            print("X - Sair")
            print("=" * 60)

            opcao = input("\nEscolha uma opcao (T/D/X): ").strip().upper()

            if opcao == "X":
                print("Saindo...")
                break

            if opcao not in ("T", "D"):
                print("Opcao invalida!")
                continue

            nome_fluxo = "Triagem Inicial" if opcao == "T" else "Dom Eletronico"
            logger.info("Fluxo selecionado: %s", nome_fluxo)
            inicio_fluxo = datetime.now()

            print("\nCriando driver e realizando login...")
            driver = criar_driver_e_fazer_login()
            if driver is None:
                print("Falha ao criar driver ou fazer login. Retornando ao menu.")
                continue

            try:
                if opcao == "T":
                    resultado = executar_triagem(driver)
                    if resultado:
                        processados = resultado.get("processados", 0)
                        sucesso_count = resultado.get("sucesso_count", 0)
                        stats["triagem"]["processados"] += processados
                        stats["triagem"]["sucesso"] += sucesso_count
                        stats["triagem"]["falha"] += processados - sucesso_count
                        sucesso = resultado.get("sucesso") or resultado.get("ok")
                        status = "OK" if sucesso else "FINALIZADO"
                        logger.info("Triagem concluida. Status: %s", status)
                    else:
                        logger.info("Triagem concluida.")
                else:
                    resultado = executar_dom(driver)
                    if resultado:
                        stats["dom"]["processados"] += resultado.get("total", 0)
                        sucesso = resultado.get("sucesso") or resultado.get("ok")
                        status = "OK" if sucesso else "FINALIZADO"
                        logger.info("DOM concluido. Status: %s", status)
                    else:
                        logger.info("DOM concluido.")

            except KeyboardInterrupt:
                print("\nInterrompido pelo usuario. Retornando ao menu...")
            except Exception as exc:
                logger.error(
                    "Erro durante execucao: %s: %s\n%s",
                    type(exc).__name__,
                    exc,
                    traceback.format_exc(),
                )
            finally:
                try:
                    driver.quit()
                except Exception:
                    pass
                logger.info("Driver finalizado.")

            duracao_fluxo = datetime.now() - inicio_fluxo
            logger.info("Duracao do fluxo: %s", duracao_fluxo)

    except KeyboardInterrupt:
        print("\nInterrompido pelo usuario. Encerrando...")
    finally:
        sys.stdout = tee.terminal
        try:
            tee.log_file.close()
        except Exception:
            pass
        bianca_logger = logging.getLogger("bianca")
        for h in (fh, ch):
            try:
                bianca_logger.removeHandler(h)
                h.close()
            except Exception:
                pass

        # Estatisticas finais
        duracao_total = datetime.now() - inicio_global
        print("\n" + "=" * 60)
        print("ESTATISTICAS FINAIS")
        print("=" * 60)
        print("Duracao total: %s" % duracao_total)
        print(
            "Triagem: %d processados / %d sucesso / %d falha"
            % (
                stats["triagem"]["processados"],
                stats["triagem"]["sucesso"],
                stats["triagem"]["falha"],
            )
        )
        print("DOM: %d processos analisados" % stats["dom"]["processados"])
        print("=" * 60)

        logger.info("Bianca encerrado.")


if __name__ == "__main__":
    main()
