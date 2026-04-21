imports = [
"import x",
"from Fix.core import finalizar_driver",
"from Mandado.processamento_api import processar_mandados_devolvidos_api",
"from PEC.orquestrador import executar_fluxo_novo_simplificado",
"from Prazo.fluxo_api import processar_gigs_sem_prazo_p2b",
"from Triagem.runner import run_triagem",
"from Peticao.pet import run_pet",
]
import sys
for stmt in imports:
    try:
        exec(stmt)
        print("OK", stmt)
    except Exception as e:
        print("FAIL", stmt, e)
        sys.exit(1)
print('ALL_OK')
