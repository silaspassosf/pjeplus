"""Baseline gate: verifies all critical import contracts survive cleanup.
WARN items (SISB) are pre-existing issues in active-agent zones not covered by this pass."""
import sys
import traceback

# Checks that MUST pass (hard gate)
HARD_CHECKS = [
    # Root
    ("x.py importable", "import x"),
    # Fix core
    ("Fix core", "from Fix.core import criar_driver_pc, criar_driver_vt, finalizar_driver"),
    ("Fix utils", "from Fix.utils import login_cpf"),
    ("Fix log", "from Fix.log import logger"),
    ("Fix otimizacao", "from Fix.otimizacao_wrapper import inicializar_otimizacoes, finalizar_otimizacoes"),
    # Mandado
    ("Mandado entrada_api", "from Mandado.entrada_api import processar_mandados_devolvidos_api"),
    # Prazo
    ("Prazo loop", "from Prazo import loop_prazo"),
    ("Prazo fluxo_api", "from Prazo.p2b_gateway import processar_gigs_sem_prazo_p2b, testar_gigs_sem_prazo"),
    ("Prazo p2b_core", "from Prazo.p2b_core import checar_prox"),
    # PEC
    ("PEC orquestrador", "from PEC.orquestrador import executar_fluxo_novo_simplificado"),
    # Triagem
    ("Triagem runner", "from Triagem.runtime_triagem import run_triagem"),
    # Peticao
    ("Peticao pet", "from Peticao.runtime_pet import run_pet"),
    # atos
    ("atos", "import atos"),
]

# WARN-only checks (pre-existing issues in active-agent zones)
WARN_CHECKS = [
    ("SISB core (WARN-only)", "from SISB.core import processar_ordem_sisbajud"),
]

failed = 0
warned = 0
for name, stmt in HARD_CHECKS:
    try:
        exec(stmt)
        print(f"  OK  {name}")
    except Exception as e:
        failed += 1
        print(f"  FAIL {name}: {e}")

for name, stmt in WARN_CHECKS:
    try:
        exec(stmt)
        print(f"  OK  {name}")
    except Exception as e:
        warned += 1
        print(f"  WARN {name}: {e} (pre-existing, SISB is active-agent zone)")

print(f"\n{failed}/{len(HARD_CHECKS)} failed, {warned}/{len(WARN_CHECKS)} warned")
sys.exit(0 if failed == 0 else 1)
