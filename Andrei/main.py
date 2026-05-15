"""Andrei - Entry point for the petition processing module.
Usage: py -m Andrei.main   or   py Andrei/main.py
"""
import sys
import logging
from datetime import datetime
from pathlib import Path

from Andrei.config import LOG_DIR
from Andrei.driver import criar_driver_e_logar, fechar_driver


def main():
    """Create driver, wait for manual login, execute pipeline, close driver."""
    # Setup logging to file + console
    log_path = Path(LOG_DIR)
    log_path.mkdir(parents=True, exist_ok=True)
    log_file = log_path / f"andrei_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(str(log_file), encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )
    logger = logging.getLogger(__name__)

    print(
        "Firefox will open. Please log in manually to PJe. "
        "The system will wait up to 5 minutes."
    )

    driver = None
    try:
        driver = criar_driver_e_logar()
        if driver is None:
            logger.error("Login failed or was cancelled. Exiting.")
            sys.exit(1)

        from Andrei.pipeline import run_pet

        resultado = run_pet(driver)
        logger.info("Pipeline finished. Result: %s", resultado)

    except KeyboardInterrupt:
        print("\nInterrupted by user. Exiting...")

    except Exception:
        logger.exception("Unexpected error during execution")
        sys.exit(1)

    finally:
        if driver is not None:
            fechar_driver(driver)


if __name__ == "__main__":
    main()
